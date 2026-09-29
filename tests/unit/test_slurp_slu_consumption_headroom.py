"""scripts/analysis/slurp_slu_consumption_headroom.py -- pure parts on fakes.

All synthetic: no sealed run, no gold, no utterance or model text. Placeholder
tokens (``tok-a`` ...) and placeholder slot types only. Covers the pooled-F1
conversion arithmetic, the target solver, the scope n-gram statistics, the
evidence-class precedence, the vocabulary-class rule and the counterfactual
re-scorer with a fake per-row counter.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_slu_consumption_headroom.py"

_spec = importlib.util.spec_from_file_location("slurp_slu_consumption_headroom", DRIVER_PATH)
H = importlib.util.module_from_spec(_spec)
sys.modules["slurp_slu_consumption_headroom"] = H
_spec.loader.exec_module(H)

TOTALS = (1434.0, 846.821078, 686.821078)  # shape of a real pooled total; values only exercise the arithmetic


def test_pooled_f1_is_twice_tp_over_the_denominator():
    tp, fp, fn = TOTALS
    assert H.pooled_f1(TOTALS) == pytest.approx(100 * 2 * tp / (2 * tp + fp + fn))


def test_one_item_moves_both_channels():
    assert H.moved((10.0, 5.0, 5.0), fp_removed=1) == (10.0, 3.0, 5.0)
    assert H.moved((10.0, 5.0, 5.0), fn_recovered=1) == (12.0, 5.0, 3.0)


def test_recovering_a_miss_is_worth_more_than_removing_a_false_positive():
    for row in H.conversion_table(TOTALS, ks=(1, 10, 50)):
        assert row["recover_k_fn_pp"] > row["remove_k_fp_pp"] > 0
        assert row["both_k_each_pp"] > row["recover_k_fn_pp"]


def test_conversion_table_is_monotone_in_k():
    rows = H.conversion_table(TOTALS, ks=(10, 20, 35))
    for a, b in zip(rows, rows[1:]):
        for key in ("remove_k_fp_pp", "recover_k_fn_pp", "both_k_each_pp"):
            assert b[key] > a[key]


@pytest.mark.parametrize("mode", ["fp", "fn", "both"])
def test_items_for_target_hits_the_target(mode):
    k = H.items_for_target(TOTALS, 1.5, mode)
    fp = k if mode in ("fp", "both") else 0.0
    fn = k if mode in ("fn", "both") else 0.0
    assert H.gain_pp(TOTALS, fp_removed=fp, fn_recovered=fn) == pytest.approx(1.5, abs=1e-6)


def test_items_for_target_is_infinite_when_unreachable():
    assert math.isinf(H.items_for_target((1.0, 0.1, 0.1), 50.0, "fp"))


def test_minimum_items_scales_by_conversion_and_rounds_up():
    conv = (("oracle", 1.0, ""), ("half", 0.5, ""))
    out = H.minimum_items(TOTALS, 1.5, conversions=conv)
    for mode, row in out.items():
        k = row["converted_items_continuous"]
        assert row["addressable_items_at_oracle"] == math.ceil(k - 1e-9)
        assert row["addressable_items_at_half"] >= 2 * k - 1e-6


def test_trade_is_negative_when_harm_dominates():
    assert H.trade_pp(TOTALS, fp_removed=1, exact_lost=0) == pytest.approx(H.gain_pp(TOTALS, fp_removed=1))
    assert H.trade_pp(TOTALS, fp_removed=1, exact_lost=5) < 0


def test_ngrams_and_scope_counts_count_once_per_exemplar():
    ex = [(["tok-a", "tok-b", "tok-a"], [["tok-b"]]),
          (["tok-a", "tok-c"], []),
          (["tok-c"], [["tok-c"]])]
    occ, tagged = H.scope_counts(ex)
    assert occ[("tok-a",)] == 2          # twice in exemplar 1 counts once
    assert tagged[("tok-b",)] == 1
    assert H.untagged_share(("tok-a",), occ, tagged) == (2, 1.0)
    assert H.untagged_share(("tok-c",), occ, tagged) == (2, 0.5)
    assert H.untagged_share(("tok-z",), occ, tagged) == (0, None)


def test_row_untagged_needs_an_untagged_occurrence():
    tagged_only = [(["tok-a", "tok-b"], [["tok-a", "tok-b"]])]
    assert not H.row_untagged(("tok-a",), tagged_only)
    assert H.row_untagged(("tok-a",), tagged_only + [(["tok-a"], [])])


def test_evidence_class_precedence():
    assert H.evidence_class(True, True, True, True).startswith("E1")
    assert H.evidence_class(False, True, True, True).startswith("E2")
    assert H.evidence_class(False, False, True, True).startswith("E3")
    assert H.evidence_class(False, False, False, True).startswith("E4")
    assert H.evidence_class(False, False, False, False).startswith("E5")
    assert len(H.EVIDENCE_CLASSES) == 5


def test_vocab_classes_rule():
    values = {"type-closed": Counter({"v1": 9, "v2": 1}),     # 9 of 10 covered -> 0.9
              "type-semi": Counter({"v1": 3, "v2": 1, "v3": 1}),  # 3 of 5 -> 0.6
              "type-open": Counter({"v1": 1, "v2": 1})}
    assert H.vocab_classes(values) == {"type-closed": "closed", "type-semi": "semi-closed", "type-open": "open"}


def _fake_counts(gold, pred):
    tp = len(set(gold) & set(pred))
    return (2.0 * tp, 2.0 * (len(pred) - tp), 2.0 * (len(gold) - tp))


def test_rescorer_gain_matches_the_analytic_conversion():
    gold = {"r1": ("g1",), "r2": (), "r3": ("g3",)}
    pred = {"r1": ["g1", "x1"], "r2": ["x2"], "r3": []}
    rs = H.Rescorer(gold, pred, _fake_counts, ["r1", "r2", "r3"])
    assert rs.base == (2.0, 4.0, 2.0)
    drop = H.drop_preds({"r1": {1}, "r2": {0}}, pred)
    assert drop == {"r1": ["g1"], "r2": []}
    assert rs.gain(drop) == pytest.approx(H.gain_pp(rs.base, fp_removed=2))
    repaired = H.repair_preds({"r3": [{"kind": "MISSING", "gold_index": 0}]}, gold, pred,
                              lambda g, p, items: list(p) + [g[it["gold_index"]] for it in items])
    assert rs.gain(repaired) == pytest.approx(H.gain_pp(rs.base, fn_recovered=1))
    edited = rs.edited_rows(drop)
    assert edited["r3"] == rs.base_rows["r3"] and edited["r2"] == (0.0, 0.0, 0.0)


def test_group_items_groups_by_row():
    items = [{"sample_id": "r1", "entity_item": 1}, {"sample_id": "r1", "entity_item": 2},
             {"sample_id": "r2", "entity_item": 3}]
    assert dict(H.group_items(items)) == {"r1": [1, 2], "r2": [3]}
