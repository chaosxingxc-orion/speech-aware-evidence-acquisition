"""E5-1 offline transcript-consistency oracle read (scripts/analysis/e5_transcript_consistency_read.py) on fakes.

Every metric and every rule is exercised on hand-built rows; the end-to-end tests build a synthetic data root
(a real prepared-artifact catalog written through core.preparation, fake sealed outputs, a fake E4-1 attempt)
and replace only the governed gold loader. No model, scorer subprocess, GPU or real corpus is touched.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity as E

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "analysis" / "e5_transcript_consistency_read.py"


def _module():
    spec = importlib.util.spec_from_file_location("e5_transcript_consistency_read_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def m():
    return _module()


def tx(m, text, status="ok"):
    return {"status": status, "text": text if status == "ok" else "", "canon": m.canon_tokens(text) if status == "ok" else []}


# ---------------------------------------------------------------------------- canonicaliser and containment


def test_containment_is_word_bounded_and_canonical(m):
    t = m.canon_tokens("Book a flight to Rome at Seven PM")
    assert m.consistent("rome", t) is True
    assert m.consistent("seven pm", t) is True
    assert m.consistent("rom", t) is False          # word-bounded: no substring match
    assert m.consistent("paris", t) is False
    assert m.consistent("", t) is None              # unverifiable, never acted on


def test_near_containment_needs_three_tokens_and_one_edit(m):
    t = m.canon_tokens("remind me about the quarterly budget review meeting")
    assert m.near_contained(m.canon_tokens("quarterly budget reviews meeting"), t) is True
    assert m.near_contained(m.canon_tokens("budget reviews"), t) is False      # fewer than three tokens
    assert m.consistent("quarterly budget reviews meeting", t) is False
    assert m.consistent("quarterly budget reviews meeting", t, near=True) is True


def test_swap_candidate_keeps_the_token_count_and_respects_theta(m):
    text = "wake me up at six thirty tomorrow in london"
    assert m.swap_candidate("londn", text, 0.6) == "london"
    assert m.swap_candidate("londn", text, 0.99) is None
    two = m.swap_candidate("tomorow in", text, 0.6)
    assert two is not None and len(two.split()) == 2
    assert m.swap_candidate("a b c d e f g h i j k", "short text", 0.1) is None


# ---------------------------------------------------------------------------- the three rules


def test_rules_flag_drop_swap_and_an_unusable_transcript(m):
    pred = (E("place_name", "londn"), E("date", "tomorrow"))
    t = tx(m, "wake me up tomorrow in london")
    flag, fa = m.apply_rule(pred, t, "R-FLAG")
    assert flag == pred and [a["action"] for a in fa] == ["flag", "keep"]
    drop, _ = m.apply_rule(pred, t, "R-DROP")
    assert drop == (E("date", "tomorrow"),)
    swap, sa = m.apply_rule(pred, t, "R-SWAP", theta=0.6)
    assert swap == (E("place_name", "london"), E("date", "tomorrow")) and sa[0]["action"] == "swap"
    nothing, na = m.apply_rule(pred, t, "R-SWAP", theta=0.99)
    assert nothing == pred and na[0]["action"] == "keep-no-candidate"
    for bad in (None, tx(m, "", status="empty")):
        same, acts = m.apply_rule(pred, bad, "R-DROP")
        assert same == pred and all(a["consistent"] is None for a in acts)


# ---------------------------------------------------------------------------- metrics


def _world(m):
    gold = {
        "s1": (E("place_name", "london"), E("date", "tomorrow")),
        "s2": (E("person", "john smith"),),
        "s3": (),
        "s4": (E("time", "seven pm"),),
    }
    pred = {
        "s1": (E("place_name", "londn"), E("date", "tomorrow")),     # NEAR fixable by swap; EXACT kept
        "s2": (E("person", "john smith"), E("person", "jane")),      # EXACT + SPURIOUS not in transcript
        "s3": (E("device_type", "lights"),),                         # SPURIOUS but in the transcript
        "s4": (E("time", "seven"),),                                 # BOUNDARY, value in transcript
    }
    transcripts = {
        "s1": tx(m, "wake me up tomorrow in london"),
        "s2": tx(m, "call john smith now"),
        "s3": tx(m, "turn off the lights"),
        "s4": tx(m, "set an alarm for seven pm"),
    }
    return sorted(gold), gold, pred, transcripts


def test_gold_span_containment_per_type(m):
    ids, gold, _pred, transcripts = _world(m)
    g = m.gold_span_containment(ids, gold, transcripts)
    assert (g["items"], g["contained"], g["rate"]) == (4, 4, 1.0)
    transcripts["s4"] = tx(m, "set an alarm for eight")
    g = m.gold_span_containment(ids, gold, transcripts)
    assert g["contained"] == 3 and g["by_type"]["time"] == {"items": 1, "contained": 0, "rate": 0.0}


def test_wrong_value_containment_by_kind(m):
    ids, gold, pred, transcripts = _world(m)
    w = m.wrong_value_containment(ids, gold, pred, transcripts)
    assert w["NEAR"] == {"items": 1, "contained": 0, "rate": 0.0}
    assert w["BOUNDARY"] == {"items": 1, "contained": 1, "rate": 1.0}
    assert w["SPURIOUS"] == {"items": 2, "contained": 1, "rate": 0.5}


def test_e4_broken_items_and_exact_preservation(m):
    gold = {"a": (E("time", "seven pm"),), "b": (E("place_name", "new york"),), "c": (E("date", "friday"),)}
    delivered = {"a": (E("time", "seven pm"),), "b": (E("place_name", "new york"),), "c": (E("date", "friday"),)}
    shadow = {"a": (E("time", "seven"),), "b": (E("place_name", "new york city"),), "c": (E("date", "friday"),)}
    items = m.e4_broken_items(sorted(gold), gold, delivered, shadow)
    assert items == [("a", 0), ("b", 0)]
    transcripts = {"a": tx(m, "alarm at seven pm"), "b": tx(m, "flights to newark")}
    keep = m.exact_preservation(items, gold, transcripts)
    assert (keep["items"], keep["kept"], keep["rate"]) == (2, 1, 0.5)
    assert keep["kept_by_type"] == {"place_name": 0, "time": 1}


def test_rule_report_scores_with_the_official_arithmetic_and_counts_transitions(m):
    ids, gold, pred, transcripts = _world(m)
    base = {s: m.slu_counts(gold[s], pred[s]) for s in ids}
    col, act = m.rule_column(ids, pred, transcripts, "R-SWAP", 0.6, False)
    r = m.rule_report(ids, gold, pred, col, act, base, draws=200)
    assert r["converted_to_exact"] == 1 and r["gold_transitions"]["NEAR->EXACT"] == 1
    assert r["exact_lost"] == 0 and r["delta_vs_delivered"]["point_pp"] > 0
    assert r["delta_vs_delivered"]["draws"] == 200 and r["delta_vs_delivered"]["seed"] == m.BOOT_SEED
    col, act = m.rule_column(ids, pred, transcripts, "R-DROP", 0.0, False)
    d = m.rule_report(ids, gold, pred, col, act, base, draws=200)
    assert d["gold_transitions"]["SPURIOUS removed"] == 1       # "jane" is not heard
    assert d["gold_transitions"]["NEAR->MISSING"] == 1          # the misheard value is dropped, not repaired
    col, act = m.rule_column(ids, pred, transcripts, "R-FLAG", 0.0, False)
    f = m.rule_report(ids, gold, pred, col, act, base, draws=200)
    assert f["delta_vs_delivered"]["point_pp"] == 0 and f["actions"]["flag"] == 2 and f["rows_changed"] == 0


def test_the_pooled_f1_and_paired_delta(m):
    gold = {"x": (E("a", "one"),), "y": (E("a", "two"),)}
    before = {"x": (E("a", "one"), E("b", "noise")), "y": (E("a", "two"),)}
    after = {"x": (E("a", "one"),), "y": (E("a", "two"),)}
    ca = {s: m.slu_counts(gold[s], before[s]) for s in gold}
    cb = {s: m.slu_counts(gold[s], after[s]) for s in gold}
    assert m.pooled_f1(m.totals(list(gold), cb)) == pytest.approx(100.0)
    d = m.paired_delta(sorted(gold), ca, cb, draws=300)
    assert d["point_pp"] > 0 and d["ci95"][0] <= d["point_pp"] <= d["ci95"][1]


# ---------------------------------------------------------------------------- the tool-call decision oracle


def test_decision_oracle_marks_rows_where_a_call_would_help(m):
    ids, gold, pred, transcripts = _world(m)
    o = m.decision_oracle(ids, gold, pred, transcripts)
    assert o["helpful_rows"] == ["s1"]
    c = o["counts"]
    assert c["helpful_entities"] == 1 and c["flagged_entities"] == 2 and c["flag_precision"] == 0.5
    assert o["entity_by_type"]["place_name"]["helpful"] == 1
    gold2 = {**gold, "s3": (E("device_type", "lights"), E("house_place", "kitchen"))}
    transcripts2 = {**transcripts, "s3": tx(m, "turn off the kitchen lights")}
    o2 = m.decision_oracle(ids, gold2, pred, transcripts2)
    assert o2["counts"]["helpful_missing_items"] == 1 and o2["counts"]["rows_with_helpful_missing"] == 1


def test_auc_and_signal_aucs(m):
    assert m.auc([3, 2, 1, 0], [1, 1, 0, 0]) == 1.0
    assert m.auc([0, 1, 2, 3], [1, 1, 0, 0]) == 0.0
    assert m.auc([1, 1], [1, 0]) == 0.5
    assert m.auc([1, 2], [1, 1]) is None
    rows = {"a": {"helpful": True}, "b": {"helpful": False}, "c": {"helpful": True}, "d": {"helpful": False}}
    s = m.signal_aucs(rows, {"len": {"a": 5, "b": 1, "c": 4, "d": None},
                             "status": {"a": "ok", "b": "malformed", "c": "ok", "d": "ok"}})
    assert s["len"] == {"kind": "numeric", "rows": 3, "positives": 2, "auc": 1.0}
    assert s["status"]["kind"] == "categorical" and s["status"]["levels"]["malformed"]["auc"] == 0.25


def test_tuning_picks_the_best_point_on_the_grid(m):
    ids, gold, pred, transcripts = _world(m)
    base = {s: m.slu_counts(gold[s], pred[s]) for s in ids}
    t = m.tune(ids, gold, pred, transcripts, base, thetas=(0.6, 0.99), nears=(False,))
    assert t["params"]["theta"] == 0.6 and t["params"]["schema"] == "saea-e5-1-params-v1"
    assert len(t["grid"]) == 2


# ---------------------------------------------------------------------------- catalog format round trip + end to end


def _catalog(m, data_root: Path, roster: str, texts: dict, statuses: dict | None = None) -> None:
    """A real prepared-speech-observation catalog (the producer's artifact wrapper and catalog schema)."""
    from speech_aware_evidence_acquisition.core.preparation import prepare_artifact
    from speech_aware_evidence_acquisition.rails.speech_observation import ARTIFACT_KIND, OUTPUT_SCHEMA, CATALOG_SCHEMA

    statuses = statuses or {}
    rows = []
    for n, (sid, text) in enumerate(sorted(texts.items())):
        rel = f"prepared/FAKE-RUN/attempt/observations/{n:06d}.json"
        status = statuses.get(sid, "ok")
        output = {"schema": OUTPUT_SCHEMA, "status": status, "transcript": text if status == "ok" else "",
                  "diagnostics": {}}
        receipt = prepare_artifact(data_root / rel, kind=ARTIFACT_KIND, inputs={"sample_id": sid},
                                   producer=lambda o=output: o, contact_class="speech-tool")
        wrapper = json.loads((data_root / rel).read_text())
        rows.append({"sample_id": sid, "artifact_relpath": rel, "artifact_sha256": receipt["sha256"],
                     "output_sha256": wrapper["output_sha256"]})
    catalog = {"schema": CATALOG_SCHEMA, "catalog_id": "fake", "use_split_identity_hash": m.FOLD_SPLITS[roster],
               "checkpoint_receipt": {}, "decoding_config_sha256": "0" * 64,
               "producer": {"run_id": "FAKE-RUN"}, "observations": rows}
    base = data_root / m.CATALOG_ROOT / roster
    base.mkdir(parents=True, exist_ok=True)
    (base / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")
    sha = hashlib.sha256((base / "catalog.json").read_bytes()).hexdigest()
    (base / "receipt.json").write_text(json.dumps({"catalog": {"sha256": sha}}), encoding="utf-8")


def test_the_catalog_round_trip_and_its_tamper_refusals(m, tmp_path):
    _catalog(m, tmp_path, "fold-a", {"s1": "hello london", "s2": "x"}, statuses={"s2": "empty"})
    transcripts, facts = m.load_catalog(tmp_path, "fold-a")
    assert transcripts["s1"]["canon"] == ["hello", "london"] and transcripts["s2"]["status"] == "empty"
    assert facts["rows"] == 2 and facts["status"] == {"empty": 1, "ok": 1}
    art = tmp_path / "prepared/FAKE-RUN/attempt/observations/000000.json"
    art.write_text(art.read_text().replace("london", "paris"))
    with pytest.raises(m.ReadError, match="artifact hash mismatch"):
        m.load_catalog(tmp_path, "fold-a")
    (tmp_path / m.CATALOG_ROOT / "fold-a" / "catalog.json").write_text("{}")
    with pytest.raises(m.ReadError, match="receipt pin"):
        m.load_catalog(tmp_path, "fold-a")
    _catalog(m, tmp_path / "b", "fold-a", {"s1": "a"})
    with pytest.raises(m.ReadError, match="not the fold-b roster"):
        (tmp_path / "b" / m.CATALOG_ROOT / "fold-b").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "b" / m.CATALOG_ROOT / "fold-a").rename(tmp_path / "b" / m.CATALOG_ROOT / "fold-b")
        m.load_catalog(tmp_path / "b", "fold-b")


def _run(data_root: Path, run_id: str, attempt: str, pred: dict, relisten: dict | None = None) -> None:
    d = data_root / "runs" / run_id / attempt
    d.mkdir(parents=True, exist_ok=True)
    with (d / f"{run_id}.outputs.jsonl").open("w") as h:
        for sid, ents in sorted(pred.items()):
            text = json.dumps({"scenario": "s", "action": "a",
                               "entities": [{"type": e.type, "filler": e.filler} for e in ents]})
            h.write(json.dumps({"sample_id": sid, "text": text, "relisten": (relisten or {}).get(sid)}) + "\n")


def test_end_to_end_tune_on_fold_b_then_read_on_fold_a(m, tmp_path, monkeypatch):
    ids, gold, pred, texts = _world(m)
    raw = {"s1": "wake me up tomorrow in london", "s2": "call john smith now", "s3": "turn off the lights",
           "s4": "set an alarm for seven pm"}
    monkeypatch.setattr(m, "load_gold", lambda lock, root, idset: {s: gold[s] for s in idset})
    for roster in ("fold-a", "fold-b"):
        _catalog(m, tmp_path, roster, raw)
    _run(tmp_path, "AGREE-B", "att", pred)
    rc = m.main(["--mode", "tune", "--roster", "fold-b", "--arm", "agree=AGREE-B/att", "--data-root", str(tmp_path),
                 "--draws", "50"])
    assert rc == 0
    out_b = tmp_path / "analysis" / m.READ_ID / "tune-fold-b"
    params = out_b / "params.json"
    content = json.loads((out_b / "content-sha256.json").read_text())
    assert content["params.json"] == hashlib.sha256(params.read_bytes()).hexdigest()
    # refused: tuning on Fold A, reading on Fold B, reading without params
    assert m.main(["--mode", "tune", "--roster", "fold-a", "--arm", "agree=AGREE-B/att", "--data-root",
                   str(tmp_path), "--label", "x"]) == 1
    _run(tmp_path, "AGREE-A", "att", pred)
    _run(tmp_path, "AA-A", "att", pred)
    e4_shadow = {**pred, "s4": (E("time", "seven"),)}
    e4_delivered = {**pred, "s4": (E("time", "seven pm"),)}
    _run(tmp_path, "E4", "seal", e4_delivered,
         relisten={"s4": {"entities": [{"blind": {"disposition": "value"}, "confirm": {"vote": "A"}}]}})
    sv = tmp_path / "runs/E4/seal/supply-variants"
    sv.mkdir()
    with (sv / f"arm-{m.E4_SHADOW}-shadow-outputs.jsonl").open("w") as h:
        for sid, ents in sorted(e4_shadow.items()):
            h.write(json.dumps({"sample_id": sid, "text": json.dumps(
                {"scenario": "s", "action": "a", "entities": [{"type": e.type, "filler": e.filler} for e in ents]})})
                    + "\n")
    sha = hashlib.sha256(params.read_bytes()).hexdigest()
    argv = ["--mode", "read", "--roster", "fold-a", "--arm", "agree=AGREE-A/att", "--arm", "wave_aa=AA-A/att",
            "--replicate", "wave_aa", "--e4", "E4/seal", "--expect-e4-broken", "1", "--params", str(params),
            "--params-sha256", sha, "--data-root", str(tmp_path), "--draws", "50"]
    assert m.main(argv) == 0
    out = tmp_path / "analysis" / m.READ_ID / "read-fold-a"
    report = json.loads((out / "report.json").read_text())
    assert report["e4_exact_preservation"]["items"] == 1 and report["e4_exact_preservation"]["rate"] == 1.0
    assert set(report["arms"]) == {"agree", "wave_aa"}
    keys = set(report["arms"]["agree"]["rules"])
    assert {"R-FLAG|tuned", "R-DROP|tuned", "R-DROP|preset", "R-SWAP|tuned", "R-SWAP|preset-theta-0.6",
            "R-SWAP|preset-theta-0.8"} == keys
    oracle = report["tool_call_decision_oracle"]
    assert oracle["counts"]["helpful_rows"] == 1 and "e4_relisten_disagreement" in oracle["signal_auc"]
    assert report["verdicts"]["precondition"]["gold_span_containment"]["pass"] is True
    assert "INSTRUMENT" in report["role"]
    # text discipline: no transcript, gold value or filler reaches the persisted files
    blob = (out / "report.json").read_text() + (out / "tables.md").read_text()
    for word in ("london", "john smith", "lights", "seven pm", "tomorrow", "jane", "londn"):
        assert word not in blob, word
    # a second read into the same directory is refused; a wrong params hash is refused
    assert m.main(argv) == 5
    bad = [a if a != sha else "0" * 64 for a in argv] + ["--label", "y"]
    assert m.main(bad) == 1
