"""Estimator: a candidate that clears vs one that does not; determinism; the
formula per knob kind -- on synthetic pools and a synthetic policy space. Uses
the real repository root only to reuse ``slurp_reviewer_credit_table.fold_of``
(item D3's own two-fold utterance split) and ``stage3_effect_floor_check``'s
floor table -- both pure, model-free, already-tested repository code.
"""

from __future__ import annotations

from pathlib import Path

from speech_aware_evidence_acquisition.analysis.sealed_credit import estimate

REPO_ROOT = Path(__file__).resolve().parents[2]


def _row(**overrides):
    base = {
        "block_n": 8, "block_pos": 1, "perc_n": 2, "perc_rank": 1, "perc_rank_bucket": "1",
        "s1_ok": True, "s1_intent_in_perc": True, "s_last_ok": True, "revised": False,
        "reviewer_visited": True, "normaliser_changed": False, "d_ok": True, "d_parsed": True,
        "d_slu_f1": 1.0, "samples_ok": [True], "samples_n": 1,
    }
    base.update(overrides)
    return base


def _pool(label, run_id, rows):
    return {
        "label": label, "run_id": run_id, "kind": "single-sample-arm", "roster": "R", "use": "tuning",
        "rows": rows, "items": [],
        "provenance": {"phases": ["x", "0"], "scores": ["y", "0"], "outputs": ["z", "0"]},
    }


def _knob(id_, node, value, source, flown="flown"):
    return {"id": id_, "node": node, "estimator": "conversion_estimate", "flown_value": flown,
            "values": [{"value": value, "conversion_source": source}]}


def test_fold_of_is_two_valued_and_deterministic():
    ids = [f"slurp:train:{i:06d}:audio-{i}" for i in range(50)]
    folds = {estimate.fold_of(sid, REPO_ROOT) for sid in ids}
    assert folds <= {0, 1}
    assert estimate.fold_of(ids[0], REPO_ROOT) == estimate.fold_of(ids[0], REPO_ROOT)


def test_pool_pair_delta_candidate_clears_vs_does_not():
    ids = [f"s{i}" for i in range(40)]
    # a strong, clearly-positive variant (60 pp intent gain)
    rows_a = {sid: _row(d_ok=(i < 8)) for i, sid in enumerate(ids)}   # 20 %
    rows_b_strong = {sid: _row(d_ok=(i < 32)) for i, sid in enumerate(ids)}  # 80 %
    rows_b_weak = {sid: _row(d_ok=(i < 9)) for i, sid in enumerate(ids)}    # 22.5 %
    pool_a = _pool("a", "RUN-A", rows_a)
    pools = {
        "a": pool_a,
        "strong": _pool("strong", "RUN-STRONG", rows_b_strong),
        "weak": _pool("weak", "RUN-WEAK", rows_b_weak),
    }
    strong_knob = _knob("k.strong", "solver_supply", "v", {"type": "pool_pair_delta", "pools": ["strong", "a"]})
    weak_knob = _knob("k.weak", "solver_supply", "v", {"type": "pool_pair_delta", "pools": ["weak", "a"]})
    strong = estimate.estimate_knob_value(strong_knob, strong_knob["values"][0], pools, REPO_ROOT)
    weak = estimate.estimate_knob_value(weak_knob, weak_knob["values"][0], pools, REPO_ROOT)
    assert strong["predicted_intent_pp"] > weak["predicted_intent_pp"]
    assert strong["predicted_intent_pp"] == 60.0
    assert len(strong["fold_intent_pp"]) == 2


def test_unobserved_source_yields_zero_and_flag():
    knob = _knob("k.u", "perception_seed", "v", {"type": "unobserved", "reason": "no sealed source"})
    result = estimate.estimate_knob_value(knob, knob["values"][0], {}, REPO_ROOT)
    assert result["unobserved"] is True
    assert result["predicted_intent_pp"] == 0.0
    assert result["predicted_slu_pp"] == 0.0


def test_reviewer_toggle_formula_is_s1_minus_delivered():
    ids = [f"s{i}" for i in range(20)]
    rows = {sid: _row(d_ok=True, s1_ok=(i < 15)) for i, sid in enumerate(ids)}  # d 100%, s1 75%
    pool = _pool("agree", "RUN-AGREE", rows)
    knob = _knob("reviewer_planner", "review_loop", "off", {"type": "credit_table_reviewer_toggle", "pool": "agree"},
                 flown="on")
    result = estimate.estimate_knob_value(knob, knob["values"][0], {"agree": pool}, REPO_ROOT)
    assert result["predicted_intent_pp"] == -25.0  # s1 (75) - d (100)


def test_estimate_all_is_deterministic():
    ids = [f"s{i}" for i in range(20)]
    rows_a = {sid: _row(d_ok=(i % 2 == 0)) for i, sid in enumerate(ids)}
    rows_b = {sid: _row(d_ok=(i % 3 == 0)) for i, sid in enumerate(ids)}
    pools = {"a": _pool("a", "RUN-A", rows_a), "b": _pool("b", "RUN-B", rows_b)}
    policy = {"knobs": [_knob("k1", "solver_supply", "v", {"type": "pool_pair_delta", "pools": ["b", "a"]})]}
    first = estimate.estimate_all(policy, pools, REPO_ROOT)
    second = estimate.estimate_all(policy, pools, REPO_ROOT)
    assert first == second


def test_compose_refuses_same_node_twice():
    e1 = {"node": "solver_supply", "predicted_intent_pp": 1.0, "predicted_slu_pp": 0.0,
          "unobserved": False, "knob_id": "k1", "value": "x"}
    e2 = {"node": "solver_supply", "predicted_intent_pp": 2.0, "predicted_slu_pp": 0.0,
          "unobserved": False, "knob_id": "k2", "value": "y"}
    try:
        estimate.compose([e1, e2])
        assert False, "expected EstimateError"
    except estimate.EstimateError:
        pass


def test_compose_sums_distinct_nodes():
    e1 = {"node": "perception_seed", "predicted_intent_pp": 1.0, "predicted_slu_pp": 0.1,
          "unobserved": False, "knob_id": "k1", "value": "x"}
    e2 = {"node": "solver_supply", "predicted_intent_pp": 2.0, "predicted_slu_pp": 0.2,
          "unobserved": False, "knob_id": "k2", "value": "y"}
    composed = estimate.compose([e1, e2])
    assert composed["predicted_intent_pp"] == 3.0
    assert round(composed["predicted_slu_pp"], 4) == 0.3
