"""scripts/analysis/slurp_supply_abstention_headroom.py -- pure parts on fakes.

All synthetic: no sealed run, no gold, no utterance, exemplar or model text.
Placeholder tokens (``tok-a`` ...) and placeholder exemplar ids only. Covers the
AUC (ties, direction, degenerate labels), the bootstrap interval shape, the row
and boundary features, the quantile helper, the four abstention rules, the
three support definitions, the support-loss rule, the utterance half split, the
pooled pp delta, the bootstrap pp interval and the deterministic argmax.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_supply_abstention_headroom.py"

_spec = importlib.util.spec_from_file_location("slurp_supply_abstention_headroom", DRIVER_PATH)
A = importlib.util.module_from_spec(_spec)
sys.modules["slurp_supply_abstention_headroom"] = A
_spec.loader.exec_module(A)


def test_auc_perfect_inverse_and_ties():
    assert A.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == pytest.approx(1.0)
    assert A.auc([0.1, 0.2, 0.8, 0.9], [1, 1, 0, 0]) == pytest.approx(0.0)
    assert A.auc([0.5, 0.5, 0.5, 0.5], [0, 1, 0, 1]) == pytest.approx(0.5)
    # one tie across classes counts one half: pairs (pos 0.5 vs neg 0.5)=0.5, (pos 0.5 vs neg 0.1)=1
    assert A.auc([0.1, 0.5, 0.5], [0, 0, 1]) == pytest.approx(0.75)
    assert A.auc([0.1, 0.2], [1, 1]) is None


def test_boot_auc_is_an_ordered_interval_around_a_clean_split():
    xs = [i / 100 for i in range(100)]
    ys = [x > 0.5 for x in xs]
    lo, hi = A.boot_auc(xs, ys, draws=200, seed=1)
    assert 0.99 <= lo <= hi <= 1.0


def test_row_features():
    f = A.row_features([0.5, 0.4, 0.3, 0.3, 0.2, 0.1], [True, False, False, True, False, False])
    assert f["top1"] == 0.5
    assert f["mean_top5"] == pytest.approx((0.5 + 0.4 + 0.3 + 0.3 + 0.2) / 5)
    assert f["margin_1_2"] == pytest.approx(0.1)
    assert f["spread_1_20"] == pytest.approx(0.4)
    assert f["none_share"] == pytest.approx(2 / 6)


def test_boundary_features_pad_unrecalled_facets_with_zero():
    f = A.boundary_features([1.0, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.15], k=8)
    assert f["score_at_k"] == 0.15 and f["gap_k_k1"] == pytest.approx(0.15)
    assert f["margin_1_2"] == pytest.approx(0.3)


def test_quantile_zero_is_minus_infinity_and_interpolates():
    assert A.quantile([3, 1, 2], 0.0) == -math.inf
    assert A.quantile([0.0, 1.0], 0.5) == pytest.approx(0.5)
    assert A.quantile([1, 2, 3, 4, 5], 1.0) == 5


RANKED = [("e1", 0.40), ("e2", 0.30), ("e3", 0.29), ("e4", 0.20), ("e5", 0.10), ("e6", 0.05)]


def test_rules():
    assert A.retained(RANKED, "R1", 0.5) == []
    assert A.retained(RANKED, "R1", 0.4) == ["e1", "e2", "e3", "e4", "e5", "e6"]
    assert A.retained(RANKED, "R1m", 0.3) == []  # mean top-5 = 0.258
    assert A.retained(RANKED, "R2", 0.29) == ["e1", "e2", "e3"]
    assert A.retained(RANKED, "R3", 0.2, m=1) == ["e1"]           # margin 0.10 < 0.20
    assert A.retained(RANKED, "R3", 0.05, m=1) == [i for i, _ in RANKED]
    none = frozenset({"e2", "e5", "e6"})                          # none share 0.5
    assert A.retained(RANKED, "R4", 0.5, none_ids=none) == ["e2", "e5", "e6"]
    assert A.retained(RANKED, "R4", 0.6, none_ids=none) == [i for i, _ in RANKED]
    with pytest.raises(ValueError):
        A.retained(RANKED, "R9", 0.0)


def _view(utt, fillers):
    fill = set()
    for f in fillers:
        fill |= A.HR.ngrams(f.split())
    return (A.HR.ngrams(utt.split()), fill)


def test_support_definitions():
    exs = {"x": _view("tok-a tok-b tok-c", ["tok-b"]),       # phrase tok-b tagged
           "y": _view("tok-b tok-d", []),                     # tok-b untagged
           "z": _view("tok-e", ["tok-e"])}
    assert A.supporters(("tok-b",), exs, "anywhere") == {"x", "y"}
    assert A.supporters(("tok-b",), exs, "tagged") == {"x"}
    assert A.supporters(("tok-b",), exs, "untagged") == {"y"}
    assert A.supporters(("tok-a", "tok-b"), exs, "anywhere") == {"x"}
    assert A.supporters((), exs, "anywhere") == set()


def test_support_lost_only_when_supported_and_no_supporter_kept():
    assert A.support_lost({"x"}, set()) is True
    assert A.support_lost({"x", "y"}, {"y"}) is False
    assert A.support_lost(set(), set()) is False


def test_split_half_is_deterministic_and_binary():
    assert A.split_half("12345") == A.split_half("12345")
    assert {A.split_half(str(i)) for i in range(50)} == {0, 1}


def test_pooled_delta_and_boot_pp():
    base = {"r1": (4.0, 2.0, 0.0), "r2": (2.0, 0.0, 2.0)}
    edited = {"r1": (4.0, 0.0, 0.0), "r2": (2.0, 0.0, 2.0)}
    # base F1 = 2*6/(12+2+2) = 75 ; edited = 12/14 = 85.714...
    assert A.pooled_delta(base, edited, ["r1", "r2"]) == pytest.approx(100 * 12 / 14 - 75.0)
    lo, hi = A.boot_pp(base, edited, ["r1", "r2"], draws=100, seed=3)
    assert lo <= hi and hi >= 0


def test_best_setting_prefers_the_earlier_entry_on_ties():
    rows = [{"q": 0.0, "oracle_net_pp": 0.1}, {"q": 0.1, "oracle_net_pp": 0.3}, {"q": 0.2, "oracle_net_pp": 0.3}]
    assert A.best_setting(rows)["q"] == 0.1
