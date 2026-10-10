"""VER-1 offline composer on SYNTHETIC pools: model-free and data-free.

The pure cores of ``scripts/analysis/slurp_ver1_offline.py`` are exercised on a seeded generator of ROLL-form sample records
(no sealed run, no gold file, no scorer subprocess, no normaliser that needs the data root). The real-data loaders only feed
these cores; their reproduction of the documented numbers is the driver's ``--mode controls``.
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

import slurp_ver1_offline as V  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity  # noqa: E402

SECRET = "zqxjv"  # a filler token that must never reach a persisted report


def _ans(scenario, action, *entities):
    return {"scenario": scenario, "action": action,
            "entities": [{"type": t, "filler": f} for t, f in entities]}


def _record(*answers):
    """A ROLL-form custody record; ``None`` = a malformed sample."""
    return {"samples": [{"sample_index": i, "parse_status": "ok" if a is not None else "malformed", "parsed_answer": a,
                         "seed": 100 + i, "temperature": 0.7} for i, a in enumerate(answers)],
            "delivered_text": "", "contacts_by_stage": {}}


# ---------------------------------------------------------------------------
# rule rendering


def test_support_filter_keeps_only_supported_entities_and_intent_forms():
    a = _ans("alarm", "set", ("time", "five pm"), ("date", f"{SECRET} friday"))
    b = _ans("alarm", "set", ("time", "five pm"))
    c = _ans("alarm", "query", ("time", "five pm"))
    d = _ans("alarm", "query")
    e = _ans("alarm", "query")
    rec = _record(a, b, c, d, e)
    sealed = {"r0": rec}
    t = V.build_rule_texts(sealed, ["r0"], 5, [1, 2, 3, 4], V.FORMS)
    ents = lambda key: json.loads(t[key]["r0"])["entities"]  # noqa: E731
    assert [x["type"] for x in ents("n5-s1-first-first")] == ["time", "date"]
    assert [x["type"] for x in ents("n5-s2-first-first")] == ["time"]        # the date has support 1
    assert [x["type"] for x in ents("n5-s3-first-first")] == ["time"]        # time is in samples 0, 1, 2
    assert ents("n5-s4-first-first") == []
    # intent forms: sample 0's labels vs the plurality over the five samples
    assert json.loads(t["n5-s2-first-first"]["r0"])["action"] == "set"
    assert json.loads(t["n5-s2-first-plurality"]["r0"])["action"] == "query"
    # the support of an entity counts the base sample itself: s = 1 never drops anything
    assert len(ents("n5-s1-medoid-base")) >= 0


def test_n_subset_uses_only_the_first_samples():
    rec = _record(_ans("a", "b", ("t", "x")), _ans("a", "b"), _ans("a", "b", ("t", "x")), _ans("a", "b", ("t", "x")),
                  _ans("a", "b", ("t", "x")))
    sealed = {"r0": rec}
    t3 = V.build_rule_texts(sealed, ["r0"], 3, [2], [("first", "first")])
    t5 = V.build_rule_texts(sealed, ["r0"], 5, [2], [("first", "first")])
    assert len(json.loads(t3["n3-s2-first-first"]["r0"])["entities"]) == 1      # samples 0 and 2 support it
    assert len(json.loads(t5["n5-s2-first-first"]["r0"])["entities"]) == 1
    t2 = V.build_rule_texts(sealed, ["r0"], 2, [2], [("first", "first")])
    assert json.loads(t2["n2-s2-first-first"]["r0"])["entities"] == []           # only sample 0 carries it


def test_malformed_first_sample_falls_back_to_the_lowest_valid_and_all_malformed_is_empty():
    rec = _record(None, _ans("a", "b", ("t", "x")), _ans("a", "b", ("t", "x")))
    assert V.single_text(rec, 0) == V.AG.EMPTY_ANSWER
    out = V.build_rule_texts({"r0": rec, "r1": _record(None, None, None)}, ["r0", "r1"], 3, [2], [("first", "first")])
    assert len(json.loads(out["n3-s2-first-first"]["r0"])["entities"]) == 1     # base = sample 1
    assert out["n3-s2-first-first"]["r1"] == V.AG.EMPTY_ANSWER


def test_registered_commit_policy_matches_the_aggregation_read_at_all_samples():
    rec = _record(_ans("a", "b", ("t", "five pm")), _ans("a", "b", ("t", "five pm")), _ans("a", "c", ("u", "mum")),
                  _ans("a", "b", ("t", "five pm"), ("u", "mum")), _ans("a", "b"))
    sealed = {"r0": rec}
    mine = V.build_registered_texts(sealed, ["r0"], 5, [2, 3])
    theirs = V.AG.build_registered_commit_arms(sealed, ["r0"], [2, 3], V.SIMILARITY)
    for s in (2, 3):
        assert mine[f"n5-registered-s{s}"]["r0"] == theirs[f"PS-registered-support-{s}"]["r0"]


# ---------------------------------------------------------------------------
# gate, contrasts, oracles, cross-fit (matrix level)


def _counts(rows):
    """rows: list of (tp, fp, fn, intent) -> a ten-column count matrix (slot columns mirror the word columns)."""
    m = np.zeros((len(rows), 10))
    for k, (tp, fp, fn, intent) in enumerate(rows):
        m[k] = [tp, fp, fn, tp, fp, fn, tp, fp, fn, intent]
    return m


def test_gate_fires_on_verdict_and_n1_and_empties_the_entity_list():
    m = _counts([(0, 2, 0, 1), (2, 0, 0, 1), (0, 1, 0, 1)])
    e = _counts([(0, 0, 0, 1), (0, 0, 2, 1), (0, 0, 0, 1)])
    verdict = [True, True, False]
    n1 = [0.5, 0.1, 0.9]
    assert V.gate_fired(verdict, n1, 0.2) == [True, False, False]
    assert V.gate_fired(verdict, n1, 0.05) == [True, True, False]
    out = V.apply_gate(V.Col(m, e), [True, False, False])
    assert (out.m[0] == e[0]).all() and (out.m[1] == m[1]).all() and (out.m[2] == m[2]).all()
    assert V.verdict_flags(_counts([(0, 0, 0, 1), (1, 0, 0, 1), (0, 1, 0, 1)])) == [True, False, False]


def test_contrast_block_counts_false_fills_nonempty_exact_and_exchange():
    boot = V.DRV.Bootstrap(["a", "b", "c", "d"], {"a": "a", "b": "b", "c": "c", "d": "d"}, draws=200, seed=1)
    gold_empty = [True, True, False, False]
    comp = _counts([(0, 2, 0, 1), (0, 1, 0, 1), (2, 0, 0, 1), (1, 1, 1, 1)])
    new = _counts([(0, 0, 0, 1), (0, 1, 0, 1), (1, 0, 1, 1), (2, 0, 0, 1)])
    b = V.contrast_block(boot, comp, new, gold_empty=gold_empty)
    assert b["false_fills_removed_net"] == 1 and b["false_fill_rows_comparator"] == 2 and b["false_fill_rows_new"] == 1
    assert b["nonempty_exact_lost"] == 1 and b["nonempty_exact_gained"] == 1
    assert b["intent_rows_moved"] == 0
    assert b["exchange"]["predicted_pp_false_fill_x0.033_plus_nonempty_exact_x0.070"] == pytest.approx(0.033)
    assert b["delta_slu_pp"] == pytest.approx(
        V.DRV.pooled(new)["slu_f1_pp"] - V.DRV.pooled(comp)["slu_f1_pp"], abs=1e-3)
    # a non-integer comparator (the mean of singles) gets no indicator block
    assert "false_fills_removed_net" not in V.contrast_block(boot, comp * 0.5, new, integer=False)


def test_oracle_is_an_upper_bound_and_crossfit_picks_per_half():
    good = _counts([(2, 0, 0, 1)] * 8)
    bad = _counts([(0, 2, 2, 0)] * 8)
    best = V.oracle_best_of([bad, good])
    assert (best == good).all()
    halves = [0, 1, 0, 1, 0, 1, 0, 1]
    picked, chosen = V.crossfit_pick({"bad": bad, "good": good}, bad, halves)
    assert chosen == {"half_0": "good", "half_1": "good"} and (picked == good).all()
    # a candidate that wins only on the held-out half is not chosen for it
    half_win = np.where(np.array(halves)[:, None] == 0, good, bad)
    picked, chosen = V.crossfit_pick({"half_win": half_win, "bad": bad}, bad, halves)
    assert chosen["half_0"] == "half_win" and chosen["half_1"] == "half_win"
    assert (picked[np.array(halves) == 1] == bad[np.array(halves) == 1]).all()


# ---------------------------------------------------------------------------
# end to end on a synthetic pool (real SLURP port, no normaliser that needs the data root)


def _world(n=40, seed=5):
    rng = np.random.default_rng(seed)
    ids, gold, sealed = [], {}, {}
    for k in range(n):
        sid = f"slurp:train:{k}:a"
        ids.append(sid)
        empty = k % 2 == 0
        ents = () if empty else (SlotEntity(type="time", filler="five pm"),)
        gold[sid] = {"scenario": "alarm", "action": "set", "utterance_id": f"slurp:train:{k}", "entities": ents}
        good = _ans("alarm", "set", ("time", "five pm"))
        # an empty-gold row: sample 0 hallucinates an entity that only it carries (the false fill the filter removes)
        spurious = _ans("alarm", "set", ("date", f"{SECRET} {int(rng.integers(100))}"))
        if empty:
            samples = [spurious, _ans("alarm", "set"), _ans("alarm", "set"), _ans("alarm", "set"), _ans("alarm", "set")]
        else:
            samples = [good, good, good, good, _ans("alarm", "set")]
        sealed[sid] = _record(*samples)
        sealed[sid]["delivered_text"] = V.AG.render_answer(samples[0])
    return ids, gold, sealed


def _flags(ids, gold):
    # a perfect-on-empty verdict: "answered no entity" exactly on the empty-gold rows
    return [not gold[s]["entities"] for s in ids]


def test_evaluate_pool_removes_planted_false_fills_and_leaks_nothing():
    ids, gold, sealed = _world()
    boot = V.make_boot(ids, gold, "utterance")
    norms = {"none": V.make_normaliser("none")}
    n1 = [0.6 if not gold[s]["entities"] else 0.05 for s in ids]
    s0_col = V.score_col(ids, {s: V.single_text(sealed[s], 0) for s in ids}, gold, norms["none"])
    zeros = V.Col(s0_col.m, s0_col.e)
    verdicts = {"i1": {"flags": _flags(ids, gold), "cols": {"none": {"lock": zeros, "aa": zeros}}}}
    rep = V.evaluate_pool(ids=ids, gold=gold, sealed=sealed, n_samples=5, norm_names=["none"], ns=[5], ss=[2, 3],
                          forms=list(V.FORMS), thetas=V.THETAS, similarity=V.SIMILARITY, boot=boot, verdicts=verdicts,
                          n1=n1, delivered={s: sealed[s]["delivered_text"] for s in ids}, normalisers=norms)
    block = rep["norms"]["none"]
    f2 = block["variants"]["n5-s2-first-first"]["vs"]["S0"]
    assert f2["false_fills_removed_net"] == 20 and f2["nonempty_exact_lost"] == 0 and f2["intent_rows_moved"] == 0
    assert f2["delta_slu_pp"] > 0
    # the gate over the bare first sample also removes them, and fires only where N1 >= theta
    g = block["variants"]["S0+gate[i1,0.2]"]
    assert g["gate"]["fired"] == 20 and g["gate"]["fired_empty_gold"] == 20
    assert g["vs"]["S0"]["false_fills_removed_net"] == 20
    quiet = block["variants"]["S0+gate[i1,0.9]"]
    assert quiet["gate"]["fired"] == 0 and quiet["vs"]["S0"]["delta_slu_pp"] == 0.0
    # the filter's gain plus the gate on top of an already-filtered column adds nothing here
    both = block["variants"]["n5-s2-first-first+gate[i1,0.2]"]["vs"]["S0"]
    assert both["delta_slu_pp"] == pytest.approx(f2["delta_slu_pp"], abs=1e-6)
    # cross-fit, oracle, strata and exchange blocks exist; the oracle bounds the rules
    assert "s-theta::i1::n5-first-first" in block["crossfit"]
    assert block["oracles"]["n5"]["best_of_rules_n5"]["delta_vs_S0_pp"] >= f2["delta_slu_pp"] - 1e-9
    assert "per_scenario" in block["variants"]["n5-s2-first-first"]["strata_vs_S0"]
    assert f2["exchange"]["predicted_pp_false_fill_x0.033_plus_nonempty_exact_x0.070"] == pytest.approx(0.66)
    # nothing but counts, labels and pp reach the report: no filler token, no sample id, no utterance id
    text = json.dumps(rep, default=str)
    assert SECRET not in text and "slurp:train" not in text and "five pm" not in text


def test_registered_and_medoid_forms_are_reported_and_n_subset_is_honoured():
    ids, gold, sealed = _world(n=20)
    boot = V.make_boot(ids, gold, "row")
    rep = V.evaluate_pool(ids=ids, gold=gold, sealed=sealed, n_samples=5, norm_names=["none"], ns=[3, 5], ss=[2, 3],
                          forms=list(V.FORMS), thetas=(0.2,), similarity=V.SIMILARITY, boot=boot, detail=False,
                          normalisers={"none": V.make_normaliser("none")})
    keys = set(rep["norms"]["none"]["variants"])
    assert {"n3-s2-first-first", "n5-s3-medoid-base", "n5-registered-s3", "n3-s1-medoid-base", "single4"} <= keys
    assert "n3-s3-first-first" in keys and "n5-s4-first-first" not in keys     # s <= n, only the requested thresholds
    assert rep["norms"]["none"]["variants"]["n3-s2-first-first"]["vs"].keys() >= {"S0", "MEAN3"}


# ---------------------------------------------------------------------------
# loaders, controls tolerance, outputs, guards


def _write_run(root: Path, run_id: str, attempt: str, rows):
    d = root / "runs" / run_id / attempt
    d.mkdir(parents=True)
    with (d / f"{run_id}.outputs.jsonl").open("w", encoding="utf-8") as fh:
        for sid, samples in rows:
            fh.write(json.dumps({"sample_id": sid, "text": "{}", "solver_group": {
                "commit_policy_id": "x", "commit_params": {}, "samples": [
                    {"sample_index": i, "parse_status": "ok" if s is not None else "malformed",
                     "parsed_answer": s, "seed": i, "temperature": 0.7} for i, s in enumerate(samples)]}}) + "\n")


def test_pool_loader_is_generic_over_the_run_id(tmp_path):
    a = _ans("alarm", "set", ("time", "five pm"))
    _write_run(tmp_path, "RUN-X", "att-1", [("slurp:train:1:a", [a, a, None]), ("slurp:train:2:a", [a, a, a])])
    spec = {"run_id": "RUN-X", "attempt": "att-1", "rows": 2}
    pool = V.load_sample_pool(tmp_path, spec)
    assert pool["ids"] == ["slurp:train:1:a", "slurp:train:2:a"] and pool["n_samples"] == 3
    assert V.single_text(pool["sealed"]["slurp:train:1:a"], 2) == V.AG.EMPTY_ANSWER
    with pytest.raises(V.ComposerError):
        V.load_sample_pool(tmp_path, {**spec, "rows": 3})
    with pytest.raises(V.ComposerError):
        V.load_sample_pool(tmp_path, {**spec, "attempt": "missing"})
    _write_run(tmp_path, "RUN-Y", "att-1", [("slurp:train:1:a", [a, a]), ("slurp:train:2:a", [a, a, a])])
    with pytest.raises(V.ComposerError):
        V.load_sample_pool(tmp_path, {"run_id": "RUN-Y", "attempt": "att-1", "rows": 2})


def test_control_tolerance_is_two_decimal_rounding():
    assert V.control_matches(1.4049, [0.5549, 2.2949], 1.40, (0.55, 2.29))
    assert not V.control_matches(1.42, [0.55, 2.29], 1.40, (0.55, 2.29))
    assert not V.control_matches(1.40, [0.55, 2.31], 1.40, (0.55, 2.29))


def test_outputs_are_write_once_and_the_test_split_is_refused(tmp_path):
    report = {"mode": "controls", "read_id": "X", "controls": [], "all_reproduced": True}
    out = V.write_once(tmp_path, "T1", report)
    assert (out / "report.json").is_file() and (out / "report.md").is_file()
    with pytest.raises(V.ComposerError):
        V.write_once(tmp_path, "T1", report)
    with pytest.raises(V.ComposerError):
        V.load_gold({}, tmp_path, "test")
    with pytest.raises(V.ComposerError):
        V.make_normaliser("v9")
    assert V.make_normaliser("none")("abc") == "abc"


def test_gate_needs_the_n1_signature():
    ids, gold, sealed = _world(n=6)
    boot = V.make_boot(ids, gold, "row")
    with pytest.raises(V.ComposerError):
        V.evaluate_pool(ids=ids, gold=gold, sealed=sealed, n_samples=5, norm_names=["none"], ns=[5], ss=[2],
                        forms=[("first", "first")], thetas=(0.2,), similarity=V.SIMILARITY, boot=boot,
                        verdicts={"i1": {"flags": [True] * 6, "cols": {}}}, n1=None,
                        normalisers={"none": V.make_normaliser("none")})


def test_driver_declares_zero_contacts_and_reads_no_test_run():
    src = (_REPO / "scripts" / "analysis" / "slurp_ver1_offline.py").read_text(encoding="utf-8")
    assert all(v == 0 for v in V.CONTACTS.values())
    assert "TEST-SAMPLE" not in src.replace("test-sample runs are never opened", "")


def test_markdown_render_carries_tables_without_text(tmp_path):
    ids, gold, sealed = _world(n=20)
    boot = V.make_boot(ids, gold, "utterance")
    norms = {"none": V.make_normaliser("none")}
    n1 = [0.6 if not gold[s]["entities"] else 0.05 for s in ids]
    col = V.score_col(ids, {s: V.single_text(sealed[s], 0) for s in ids}, gold, norms["none"])
    verdicts = {"i1": {"flags": _flags(ids, gold), "cols": {"none": {"lock": col, "aa": col}}}}
    rep = V.evaluate_pool(ids=ids, gold=gold, sealed=sealed, n_samples=5, norm_names=["none"], ns=[3, 5], ss=[2, 3],
                          forms=[V.PRIMARY_FORM], thetas=(0.2,), similarity=V.SIMILARITY, boot=boot, verdicts=verdicts,
                          n1=n1, normalisers=norms)
    rep.update({"mode": "read", "read_id": "X", "inputs": {"label": "synthetic"},
                "bootstrap": {"unit": "utterance", "clusters": 20, "draws": V.BOOT_DRAWS, "seed": V.BOOT_SEED}})
    text = V.render(rep)
    assert "Filter-only rules" in text and "Gated rules" in text and "Cross-fitted thresholds" in text
    assert "Strata vs S0" in text and "Per-row oracle ceilings" in text
    assert SECRET not in text and "five pm" not in text
    out = V.write_once(tmp_path, "SYN", rep)
    assert json.loads((out / "report.json").read_text(encoding="utf-8"))["read_id"] == "X"


def test_empty_gold_contribution_carries_the_delta_not_a_zero_subset_f1():
    ids, gold, sealed = _world(n=40)
    boot = V.make_boot(ids, gold, "utterance")
    norms = {"none": V.make_normaliser("none")}
    rep = V.evaluate_pool(ids=ids, gold=gold, sealed=sealed, n_samples=5, norm_names=["none"], ns=[5], ss=[2],
                          forms=[V.PRIMARY_FORM], thetas=(0.2,), similarity=V.SIMILARITY, boot=boot, extras=False,
                          registered=False, normalisers=norms)
    v = rep["norms"]["none"]["variants"]["n5-s2-first-first"]
    split = v["strata_vs_S0"]["empty_vs_non_empty"]
    assert split["empty_gold"]["contribution_to_pooled_delta_pp"] == pytest.approx(v["vs"]["S0"]["delta_slu_pp"], abs=1e-3)
    assert split["empty_gold"]["contribution_to_pooled_delta_pp"] > 0
    assert split["non_empty_gold"]["contribution_to_pooled_delta_pp"] == pytest.approx(0.0, abs=1e-9)
    assert split["empty_gold"]["changed_rows"] == 20 and split["non_empty_gold"]["changed_rows"] == 0


# ---------------------------------------------------------------------------
# --verdict-run: a sealed same-flight column other than the NX R1 iterations as a verdict source


def test_verdict_run_parses_run_attempt_arm_and_an_optional_key(monkeypatch):
    monkeypatch.setattr(V, "VERDICT_RUNS", {})
    key, spec = V.parse_verdict_run("SAEA-RUN-V1:attempt-x-generation-v1:r1-c3", rows=1080)
    assert key == "r1-c3"                                    # default key = the arm id
    assert spec == {"run_id": "SAEA-RUN-V1", "attempt": "attempt-x-generation-v1", "scorer": "slurp-slu-official-train",
                    "split": "train", "rows": 1080, "arms": ("lock", "aa", "r1-c3"), "aggressive": "r1-c3"}
    key, _ = V.parse_verdict_run("SAEA-RUN-V1:attempt-x-generation-v1:r1-c3:c3foldA", rows=1080)
    assert key == "c3foldA"
    for bad in ("only:two", "a:b:c:d:e", "a:b:", "a/b:c:d", "a:..:d", "a:b:lock", "a:b:aa", "SAEA RUN:b:c"):
        with pytest.raises(V.ComposerError):
            V.parse_verdict_run(bad, rows=10)


def test_verdict_run_keys_never_shadow_the_builtin_iterations_or_each_other(monkeypatch):
    monkeypatch.setattr(V, "VERDICT_RUNS", {})
    with pytest.raises(V.ComposerError):
        V.parse_verdict_run("RUN:ATT:r1-c3:i1", rows=10)      # i1 / i2 stay the NX R1 iterations
    key, spec = V.parse_verdict_run("RUN:ATT:r1-c3", rows=10)
    V.VERDICT_RUNS[key] = spec
    with pytest.raises(V.ComposerError):
        V.parse_verdict_run("RUN2:ATT2:r1-c3", rows=10)       # the same default key twice needs an explicit 4th field
    assert V.verdict_run_ids("r1-c3") == ("RUN", "ATT")
    assert V.verdict_run_ids("i1") == (V.R6.FOLD_B["i1"]["run_id"], V.R6.FOLD_B["i1"]["attempt"])
    with pytest.raises(V.ComposerError):
        V.verdict_run_ids("nope")


def _fake_pool(ids, arm_has_entity):
    """A minimal SCR.load_pool result: ten count columns per row, items = columns 6 and 7."""
    def counts(has_entity):
        m = np.zeros((len(ids), 10))
        m[:, 6] = np.asarray(has_entity, dtype=float)
        return m

    lock = counts([1] * len(ids))
    arm = counts(arm_has_entity)
    zeros = np.zeros_like(lock)
    return {"ids": list(ids), "v3": {"lock": lock, "aa": lock, "r1-c3": arm}, "v3_empty": {"lock": zeros, "aa": zeros, "r1-c3": zeros},
            "v4g": {"lock": lock, "aa": lock, "r1-c3": arm}, "v4g_empty": {"lock": zeros, "aa": zeros, "r1-c3": zeros},
            "meta": {"stub": True}}


def test_a_verdict_run_loads_through_the_scr_pool_loader_with_its_own_spec(monkeypatch):
    monkeypatch.setattr(V, "VERDICT_RUNS", {})
    ids = ["s0", "s1", "s2"]
    seen = {}

    def fake_load_pool(key, spec, data_root, gold_all, arms):
        seen.update(key=key, spec=spec, arms=tuple(arms))
        return _fake_pool(ids, [1, 0, 0])

    monkeypatch.setattr(V.SCR, "load_pool", fake_load_pool)
    key, spec = V.parse_verdict_run("RUN-C3:ATT-C3:r1-c3", rows=3)
    V.VERDICT_RUNS[key] = spec
    source = V.load_verdict_source(Path("/nonexistent"), {}, key, ids)
    assert seen["spec"] is spec and seen["arms"] == ("lock", "aa", "r1-c3")
    assert source["arm"] == "r1-c3" and source["run"] == ["RUN-C3", "ATT-C3"]
    assert source["flags"] == [False, True, True]            # verdict = the arm answered no entity (after v4g)
    assert set(source["cols"]["v4g"]) == {"lock", "aa"} and set(source["cols"]["v3"]) == {"lock", "aa"}
    with pytest.raises(V.ComposerError):                       # rows must be the pool's rows
        V.load_verdict_source(Path("/nonexistent"), {}, key, ["s0", "s1", "other"])


def test_the_builtin_iterations_still_resolve_through_their_own_scr_pool(monkeypatch):
    monkeypatch.setattr(V, "VERDICT_RUNS", {})
    ids = ["s0", "s1"]
    seen = {}

    def fake_load_pool(key, spec, data_root, gold_all, arms):
        seen.update(key=key, spec=spec, arms=tuple(arms))
        pool = _fake_pool(ids, [0, 1])
        agg = V.R6.FOLD_B[key]["aggressive"]
        for table in ("v3", "v3_empty", "v4g", "v4g_empty"):
            pool[table][agg] = pool[table].pop("r1-c3")
        return pool

    monkeypatch.setattr(V.SCR, "load_pool", fake_load_pool)
    for key in ("i1", "i2"):
        source = V.load_verdict_source(Path("/nonexistent"), {}, key, ids)
        assert seen["spec"] is V.SCR.POOLS[key] and seen["arms"] == ("lock", "aa", V.R6.FOLD_B[key]["aggressive"])
        assert source["arm"] == V.R6.FOLD_B[key]["aggressive"] and source["flags"] == [True, False]
    with pytest.raises(V.ComposerError):
        V.load_verdict_source(Path("/nonexistent"), {}, "i3", ids)


def test_main_threads_verdict_run_beside_the_builtin_verdicts_into_the_read(monkeypatch):
    import speech_aware_evidence_acquisition.data.lock as lock_module

    monkeypatch.setattr(V, "VERDICT_RUNS", {})
    monkeypatch.setattr(lock_module, "load_lock", lambda path: object())
    monkeypatch.setattr(V, "load_sample_pool", lambda root, spec: {"n_samples": 3})
    monkeypatch.setattr(V, "render", lambda report: "")
    seen = {}

    def fake_read_pool(args, spec, **kwargs):
        seen.update(kwargs, spec=spec)
        return {}

    monkeypatch.setattr(V, "read_pool", fake_read_pool)
    argv = ["--mode", "read", "--run-id", "POOL", "--attempt", "att", "--split", "train", "--rows", "1080", "--n", "3", "--s", "2",
            "--thetas", "0.2", "--label", "SYN", "--no-write", "--data-root", "/nonexistent", "--lock", "/nonexistent"]
    assert V.main(argv + ["--verdict", "i1", "--verdict-run", "RUN-C3:ATT-C3:r1-c3", "--signature", "r1-c3"]) == 0
    assert seen["verdict_keys"] == ["i1", "r1-c3"] and seen["signature"] == "r1-c3"
    assert V.VERDICT_RUNS["r1-c3"]["rows"] == 1080 and V.VERDICT_RUNS["r1-c3"]["run_id"] == "RUN-C3"
    # without the option the behaviour is unchanged: i1,i2 only, nothing registered
    monkeypatch.setattr(V, "VERDICT_RUNS", {})
    assert V.main(argv + ["--verdict", "i1,i2"]) == 0
    assert seen["verdict_keys"] == ["i1", "i2"] and V.VERDICT_RUNS == {}
