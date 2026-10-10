"""NX R6-P1 information-gain driver: ``--verdict-source perception-arm:<arm>`` and ``--gain-baseline`` on SYNTHETIC columns.

Model-free and data-free. A synthetic Fold-B-like roster is built from a seeded generator: an N1-like supply feature
that separates empty-gold rows, an independent intent-prior feature, a Perception verdict (informative, or pure noise)
and a lock Solver column of ten count columns per row (the shape ``score_vector`` returns). The core function
``perception_gain_core`` is the whole computation; the real-data loader only feeds it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
for _extra in (_REPO / "scripts" / "analysis",):
    if str(_extra) not in sys.path:
        sys.path.insert(0, str(_extra))

import slurp_nx_r6_upstream_empty as driver  # noqa: E402

N = 240


def _roster(seed: int = 7, *, verdict: str = "informative"):
    rng = np.random.default_rng(seed)
    ids = [f"slurp:train:{i}:a" for i in range(N)]
    utt = [f"slurp:train:{i}" for i in range(N)]
    gold_empty = [bool(rng.random() < 0.36) for _ in ids]
    n1 = [float(np.clip((0.45 if e else 0.2) + rng.normal(0, 0.25), 0, 1)) for e in gold_empty]
    prior = [float(np.clip((0.6 if e else 0.8) + rng.normal(0, 0.1), 0, 1)) for e in gold_empty]
    signals = {s: {"b_n1_share": n1[k], "a_rate_rank1": 1.0 - prior[k],
                   "d_lock_items_neg": 0.0, "d_lock_intent_rate": 0.5} for k, s in enumerate(ids)}
    rank1, verdicts = {}, {}
    for k, s in enumerate(ids):
        if verdict == "informative":
            p_none = 0.8 if gold_empty[k] else 0.08
        elif verdict == "noise":
            p_none = 0.3
        else:
            raise AssertionError(verdict)
        value = "none" if rng.random() < p_none else "some"
        rank1[s] = value
        verdicts[s], _ = driver.verdict_row({"rank1": {"cls": "ok", "verdict": value}})
    # the lock column: ten count columns; false fill on 60 % of empty-gold rows; 75 % of non-empty rows exact
    base = np.zeros((N, 10))
    base_empty = np.zeros((N, 10))
    for k in range(N):
        base[k, 9] = base_empty[k, 9] = 1.0
        if gold_empty[k]:
            if rng.random() < 0.6:
                base[k, [1, 4, 7]] = 2.0          # word fp, char fp, entity fp: a false fill
        else:
            if rng.random() < 0.75:
                base[k, [0, 3, 6]] = 3.0          # exact: tp only
            else:
                base[k, [0, 3, 6]] = 1.0
                base[k, [1, 4, 7]] = 1.0
                base[k, [2, 5, 8]] = 2.0
            base_empty[k, [2, 5, 8]] = 3.0         # the emptied row misses every gold entity
    return dict(ids=ids, utt=utt, gold_empty=gold_empty, signals=signals, verdicts=verdicts, rank1_values=rank1,
                base=base, base_empty=base_empty)


def _core(roster, baseline="n1", **kwargs):
    kwargs.setdefault("auc_draws", 200)
    kwargs.setdefault("gate_draws", 300)
    return driver.perception_gain_core(
        **{**roster, "signals": {s: dict(v) for s, v in roster["signals"].items()}}, baseline=baseline, **kwargs)


def test_an_informative_verdict_adds_cross_fitted_auc_over_n1_with_a_positive_ci_lower_bound():
    result = _core(_roster())
    gain = result["gain"]
    assert gain["baseline"] == "n1" and gain["baseline_features"] == ["b_n1_share"]
    assert gain["rows"] == N and gain["rows_with_ok_rank1_tag"] == N
    assert gain["increment"] > 0.03 and gain["increment_ci95"][0] > 0.0 and gain["additional"] is True
    assert gain["auc_with_verdict"] == pytest.approx(gain["auc_baseline"] + gain["increment"], abs=2e-4)
    assert gain["auc_verdict_alone"] > 0.7 and gain["auc_verdict_alone_ci95"][0] < gain["auc_verdict_alone"]
    assert gain["bootstrap"] == {"unit": "whole utterance", "draws": 200, "seed": 20261010}
    assert set(gain["per_utterance_half"]) == {"half_0", "half_1"}
    assert sum(h["rows"] for h in gain["per_utterance_half"].values()) == N
    assert set(gain["rank1_verdict_counts"]) == {"none", "some"}


def test_a_verdict_that_is_noise_is_not_additional():
    gain = _core(_roster(verdict="noise"))["gain"]
    assert gain["increment_ci95"][0] <= 0.0 and gain["additional"] is False
    assert abs(gain["increment"]) < 0.04


@pytest.mark.parametrize("baseline", sorted(driver.GAIN_BASELINES))
def test_every_gain_baseline_runs_and_names_its_features(baseline):
    gain = _core(_roster(), baseline=baseline)["gain"]
    assert gain["baseline_features"] == driver.GAIN_BASELINES[baseline]
    assert gain["auc_baseline"] is not None and gain["increment_ci95"] is not None


def test_the_baselines_are_nested_and_the_last_one_adds_the_lock_answer():
    b = driver.GAIN_BASELINES
    assert b["n1"] == ["b_n1_share"]
    assert b["n1+prior"] == b["n1"] + ["a_rate_rank1"]
    assert b["n1+prior+lock"] == b["n1+prior"] + ["d_lock_items_neg", "d_lock_intent_rate"]


def test_unknown_baseline_and_a_missing_baseline_feature_are_refused():
    with pytest.raises(driver.ReadError, match="gain-baseline"):
        _core(_roster(), baseline="bogus")
    roster = _roster()
    roster["signals"][roster["ids"][3]]["a_rate_rank1"] = None
    with pytest.raises(driver.ReadError, match="not computable"):
        _core(roster, baseline="n1+prior")
    # the same row is fine for a baseline that does not use the feature
    assert _core(roster, baseline="n1")["gain"]["rows"] == N


def test_the_gate_estimate_is_the_verdict_and_n1_rule_on_the_lock_column():
    roster = _roster()
    gate = _core(roster)["gate"]
    p = gate["primary"]
    assert p["gate"] == "E=none and n1>=0.2"
    # recount the rule independently
    fired = [roster["rank1_values"][s] == "none" and roster["signals"][s]["b_n1_share"] >= 0.2 for s in roster["ids"]]
    base = roster["base"]
    ge = roster["gold_empty"]
    assert p["fired"] == sum(fired)
    assert p["fired_empty_gold"] == sum(f and e for f, e in zip(fired, ge))
    removed = sum(1 for k, f in enumerate(fired) if f and ge[k] and base[k, 6] + base[k, 7] > 0)
    lost = sum(1 for k, f in enumerate(fired)
               if f and not ge[k] and base[k, 7] == 0 and base[k, 8] == 0)
    assert p["false_fills_removed"] == removed > 0
    assert p["nonempty_exact_lost"] == lost
    assert p["false_fill_rows_base"] - p["false_fill_rows_new"] == removed
    assert p["intent_rows_moved"] == 0 and p["delta_intent_pp"] == 0.0
    # every fired row changes (empty-gold with a false fill, or a non-empty row emptied), nothing else does
    assert p["rows_changed"] == removed + sum(1 for k, f in enumerate(fired) if f and not ge[k])
    assert p["delta_slu_pp"] > 0.0 and p["ci95_slu_pp"][0] < p["delta_slu_pp"] < p["ci95_slu_pp"][1]
    assert gate["bootstrap"] == {"unit": "whole utterance", "draws": 300, "seed": 20260915}


def test_the_fixed_n1_grid_and_the_references_are_reported():
    gate = _core(_roster())["gate"]
    assert list(gate["grid_verdict_and_n1"]) == [f"n1>={t}" for t in driver.N1_THRESHOLDS]
    fired = [v["fired"] for v in gate["grid_verdict_and_n1"].values()]
    assert fired == sorted(fired, reverse=True)                      # a higher N1 cut never fires more rows
    assert gate["grid_verdict_and_n1"]["n1>=0.2"]["fired"] == gate["primary"]["fired"]
    assert gate["verdict_ungated"]["fired"] >= gate["primary"]["fired"]
    assert set(gate["n1_gate_alone"]) == {"n1>=0.2"}
    for key in ("crossfit_top_share_with_verdict", "crossfit_top_share_without_verdict"):
        entry = gate[key]
        assert {"picks", "fired", "delta_slu_pp", "ci95_slu_pp", "intent_rows_changed"} <= set(entry)
    assert gate["exchange_rates_pp_per_row"] == {"false_fill_removed": 0.033, "nonempty_exact_lost": -0.070}


def test_a_verdict_of_some_everywhere_fires_nothing_and_changes_nothing():
    roster = _roster()
    roster["rank1_values"] = {s: "some" for s in roster["ids"]}
    gate = _core(roster)["gate"]
    assert gate["primary"]["fired"] == 0 and gate["primary"]["delta_slu_pp"] == 0.0
    assert gate["primary"]["false_fills_removed"] == 0 and gate["primary"]["rows_changed"] == 0


def test_verdict_rows_encode_missing_verdicts_as_a_feature_not_a_median():
    ok = lambda value: {"rank1": {"cls": "ok", "verdict": value}}      # noqa: E731
    assert driver.verdict_row(ok("none")) == ({"p_none_score": 1.0, "p_tag_ok": 1.0}, "none")
    assert driver.verdict_row(ok("some")) == ({"p_none_score": 0.0, "p_tag_ok": 1.0}, "some")
    assert driver.verdict_row(ok("unsure")) == ({"p_none_score": 0.5, "p_tag_ok": 1.0}, "unsure")
    for cls in ("invalid", "absent"):
        assert driver.verdict_row({"rank1": {"cls": cls, "verdict": None}}) == (
            {"p_none_score": 0.5, "p_tag_ok": 0.0}, cls)


def test_verdict_source_parsing_keeps_the_original_read_the_default():
    assert driver.parse_verdict_source("solver") is None
    assert driver.parse_verdict_source("perception-arm:r6-p1") == "r6-p1"
    for bad in ("perception-arm:", "perception", "p1", "solver:p1", ""):
        with pytest.raises(driver.ReadError):
            driver.parse_verdict_source(bad)
    with pytest.raises(SystemExit):
        driver.main(["--verdict-source", "perception-arm:p1", "--check"])
    with pytest.raises(driver.ReadError):
        driver.main(["--verdict-source", "garbage"])
    assert driver.GAIN_BASELINES and (driver.GATE_N1, driver.GATE_DRAWS, driver.GATE_SEED) == (0.2, 10_000, 20260915)
    assert (driver.AUC_DRAWS, driver.AUC_SEED) == (2000, 20261010)


def test_the_auc_increment_bootstrap_is_paired_and_degenerate_safe():
    rng = np.random.default_rng(3)
    labels = rng.random(120) < 0.4
    score = rng.random(120)
    clusters = [f"c{i // 2}" for i in range(120)]
    assert driver.boot_auc_increment(score, score, labels, clusters, draws=50) == [0.0, 0.0]
    better = score + 2.0 * labels
    low, high = driver.boot_auc_increment(better, score, labels, clusters, draws=100)
    assert 0.0 < low <= high
    assert driver.boot_auc_increment(score, score, [True] * 120, clusters, draws=10) is None


def test_the_rendered_tables_and_report_carry_numbers_only():
    roster = _roster()
    core = _core(roster)
    report = {"read_id": driver.GAIN_READ_ID, "verdict_source": "perception-arm:r6-p1", **core}
    text = driver.render_gain(report)
    for heading in ("## Information gain", "## Gate estimate on the lock Solver column", "fixed N1 grid", "references:"):
        assert heading in text
    document = json.dumps(report, sort_keys=True) + text
    assert "slurp:train" not in document          # no sample ids reach the output
    assert "perception-arm:r6-p1" in text


# ---------------------------------------------------------------------------
# the real-data side, wired to the E2b reader's synthetic sealed records (no sealed bytes are read)


def test_the_perception_arm_loader_runs_end_to_end_on_synthetic_sealed_records(tmp_path, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import test_slurp_nx_perception_column_read as RT
    from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity

    RT._with_tags()
    try:
        rows, trace = RT._sealed()
    finally:
        RT.TAGS.clear()
    run, attempt = "RUN-X", "attempt-x"
    directory = tmp_path / "runs" / run / attempt
    directory.mkdir(parents=True)
    (directory / f"{run}.run-manifest.json").write_text("{}", encoding="utf-8")
    table = tmp_path / driver.RATE_TABLE
    table.parent.mkdir(parents=True)
    table.write_text(json.dumps({"intent_n": {"calendar_set": 10, "alarm_query": 10, "play_music": 10},
                                 "intent_with_entities": {"calendar_set": 9, "alarm_query": 1, "play_music": 8}}),
                     encoding="utf-8")
    gold = {sid: {"scenario": intent.split("_")[0], "action": intent.split("_")[1], "utterance_id": sid.rsplit(":", 1)[0],
                  "entities": tuple(SlotEntity(t, f) for t, f in entities)}
            for sid, (intent, entities) in RT.GOLD.items()}

    class Bundle:
        outputs_rows, trace_records = rows, trace

    import speech_aware_evidence_acquisition.core.bundle as bundle_module
    import speech_aware_evidence_acquisition.data.lock as lock_module
    monkeypatch.setattr(bundle_module, "verify_bundle", lambda manifest: Bundle)
    monkeypatch.setattr(lock_module, "load_lock", lambda path: object())
    monkeypatch.setattr(driver.DRV, "load_gold", lambda lock, root, split: gold)
    monkeypatch.setattr(driver, "apply_v4g", lambda ids, texts: (dict(texts), 0, "test"))
    monkeypatch.setattr(driver, "load_exemplar_annotations", lambda root: {
        "values": {"e1": {"intent": "calendar_set", "n_entities": 1}, "e2": {"intent": "alarm_query", "n_entities": 0}},
        "sha256": "0" * 64, "relpath": "pool"})
    note = {"ids": ["calendar_set"], "unresolved": [0], "slot_named": [0], "evidence_refs": [0], "distinction_tokens": [3]}
    monkeypatch.setattr(driver, "load_phase_signals", lambda path, slot_types: {
        "rows": {sid: {"boundary": [], "ex_ids": ["e1", "e2"] if k % 2 else ["e2", "e2"], "ex_scores": [0.9, 0.8],
                       "note": note} for k, sid in enumerate(gold)},
        "checks": {}, "sha256": "1" * 64})
    monkeypatch.setattr(driver, "load_perception_trace", lambda path, ids: {})

    class Args:
        data_root = str(tmp_path)
        lock = "unused"
        run_id, attempt_id, rows = run, attempt, len(gold)
        verdict_source = "perception-arm:p1"
        gain_baseline = "n1+prior+lock"
        tag_set = ["p2=none,some,unsure"]

    report = driver.build_perception_gain(Args)
    assert report["schema"] == driver.GAIN_SCHEMA and report["verdict_source"] == "perception-arm:p1"
    assert report["gain"]["rows"] == 6 and report["gain"]["baseline"] == "n1+prior+lock"
    assert report["gain"]["rank1_verdict_counts"] == {"absent": 1, "invalid": 1, "none": 2, "some": 2}
    assert report["gain"]["rows_with_ok_rank1_tag"] == 4
    assert report["gate"]["primary"]["gate"] == "E=none and n1>=0.2"
    assert report["inputs"]["tag_sets"]["p2"] == ["none", "some", "unsure"] and report["contacts"]["model"] == 0
    assert driver.render_gain(report).startswith("# ")
    # the delivering arm, the twin and an unknown arm are not verdict sources
    for arm in ("lock", "aa", "zz"):
        Args.verdict_source = f"perception-arm:{arm}"
        with pytest.raises(driver.ReadError, match="not a candidate arm"):
            driver.build_perception_gain(Args)
