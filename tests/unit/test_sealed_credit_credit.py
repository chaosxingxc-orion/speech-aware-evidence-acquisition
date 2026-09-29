"""The credit table on synthetic pool row-states (a known conversion rate;
determinism; order independence)."""

from __future__ import annotations

from speech_aware_evidence_acquisition.analysis.sealed_credit import credit


def _synthetic_pool(label, run_id, kind, rows, items=(), reviewer=True):
    return {
        "label": label, "run_id": run_id, "kind": kind, "roster": "TEST-ROSTER", "use": "tuning",
        "rows": rows, "items": list(items),
        "provenance": {"phases": ["x", "0"], "scores": ["y", "0"], "outputs": ["z", "0"]},
    }


def _row(**overrides):
    base = {
        "block_n": 8, "block_pos": 1, "perc_n": 2, "perc_rank": 1, "perc_rank_bucket": "1",
        "s1_ok": True, "s1_intent_in_perc": True, "s_last_ok": True, "revised": False,
        "reviewer_visited": True, "normaliser_changed": False, "d_ok": True, "d_parsed": True,
        "d_slu_f1": 1.0, "samples_ok": [True], "samples_n": 1,
    }
    base.update(overrides)
    return base


def test_perception_rank_conversion_known_rate():
    rows = {}
    # 8 rows at rank "1", 6 correct -> 75.0 %
    for i in range(8):
        rows[f"s{i}"] = _row(perc_rank_bucket="1", s1_ok=(i < 6))
    pool = _synthetic_pool("p", "RUN", "single-sample-arm", rows)
    table = credit.perception_rank_conversion(pool)
    assert table["1"]["n"] == 8
    assert table["1"]["hits"] == 6
    assert table["1"]["rate_pct"] == 75.0


def test_block_position_bucket():
    assert credit.block_position_bucket(1) == "1"
    assert credit.block_position_bucket(2) == "2-3"
    assert credit.block_position_bucket(3) == "2-3"
    assert credit.block_position_bucket(4) == "4-8"
    assert credit.block_position_bucket(8) == "4-8"
    assert credit.block_position_bucket(9) == "9+"
    assert credit.block_position_bucket(None) == "none"


def test_reviewer_toggle_effect_only_for_single_sample_arm():
    rows = {"s0": _row(d_ok=True, s1_ok=False)}
    grouped = _synthetic_pool("g", "RUN-G", "grouped-multi-sample", rows)
    assert credit.reviewer_toggle_effect(grouped) is None
    single = _synthetic_pool("s", "RUN-S", "single-sample-arm", rows)
    effect = credit.reviewer_toggle_effect(single)
    assert effect is not None
    # "off" delivers s1 (False) instead of d_ok (True): a harmful toggle, delta < 0
    assert effect["intent_delta_pp"]["delta_pp"] < 0


def test_pool_pair_delta_known_delta():
    ids = [f"s{i}" for i in range(10)]
    rows_a = {sid: _row(d_ok=(i < 5), d_slu_f1=0.5) for i, sid in enumerate(ids)}
    rows_b = {sid: _row(d_ok=(i < 8), d_slu_f1=0.8) for i, sid in enumerate(ids)}
    pool_a = _synthetic_pool("a", "RUN-A", "single-sample-arm", rows_a)
    pool_b = _synthetic_pool("b", "RUN-B", "single-sample-arm", rows_b)
    result = credit.pool_pair_delta(pool_b, pool_a)
    assert result["n"] == 10
    assert result["intent_delta_pp"]["delta_pp"] == 30.0  # 80% - 50%
    assert abs(result["slu_f1_mean_delta_pp"]["delta_pp"] - 30.0) < 1e-6


def test_credit_table_is_deterministic_and_order_independent():
    rows = {f"s{i}": _row(d_ok=(i % 2 == 0)) for i in range(20)}
    pool_a = _synthetic_pool("agree", "RUN-A", "single-sample-arm", rows)
    pool_b = _synthetic_pool("wave-aa", "RUN-B", "single-sample-arm", dict(rows))
    table1 = credit.build_credit_table([pool_a, pool_b])
    table2 = credit.build_credit_table([pool_b, pool_a])  # reversed input order
    assert table1["table_sha256"] == table2["table_sha256"]
    table3 = credit.build_credit_table([pool_a, pool_b])
    assert table1["table_sha256"] == table3["table_sha256"]
