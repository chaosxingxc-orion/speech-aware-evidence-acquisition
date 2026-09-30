"""scripts/analysis/slurp_retrieval_key_recall.py -- pure parts on fakes.

All synthetic: no sealed run, no gold, no vectors from disk, no utterance or model text. Placeholder
intent ids (``a_x`` ...) and placeholder sample ids only. Covers the utterance half split, the
scenario / catch-all helpers, score ordering with admission, the fuser block, ranks, spherical
k-means determinism, kNN shares, group max, reciprocal-rank fusion, the catch-all floor, the
scenario-first order, the CSLS and key-bias statistics, the rate tables and implied sums, the paired
comparison, the half cross-fit and the miss taxonomy.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_retrieval_key_recall.py"

_spec = importlib.util.spec_from_file_location("slurp_retrieval_key_recall", DRIVER_PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules["slurp_retrieval_key_recall"] = M
_spec.loader.exec_module(M)

INTENTS = ["a_x", "a_y", "b_x", "general_quirky"]


def test_half_scenario_and_catch_all():
    assert M.split_half("u-1") in (0, 1)
    assert M.split_half("u-1") == M.split_half("u-1")
    assert M.scenario_of("iot_hue_lightoff") == "iot"
    assert M.is_catch_all("general_quirky") and M.is_catch_all("qa_factoid")
    assert not M.is_catch_all("alarm_set")


def test_order_block_and_rank():
    scores = np.array([[0.2, 0.5, 0.5, -0.1]])
    order = M.order_from_scores(scores, INTENTS)[0]
    assert order == ["a_y", "b_x", "a_x", "general_quirky"]  # tie -> intent ascending
    admitted = scores > 0
    assert M.order_from_scores(scores, INTENTS, admitted)[0] == ["a_y", "b_x", "a_x"]
    assert M.block_of(order, None, d=2) == ["a_y", "b_x"]
    assert M.block_of(order, {"b_x", "a_x"}, d=2) == ["b_x"]
    assert M.rank_of(order, "a_x") == 3 and M.rank_of(order, "zz") is None
    assert M.in_block(8) and not M.in_block(9) and not M.in_block(None)


def test_spherical_kmeans_is_deterministic_and_unit():
    rng = np.random.default_rng(0)
    x = np.vstack([rng.normal([5, 0, 0], 0.1, (10, 3)), rng.normal([0, 5, 0], 0.1, (10, 3))])
    c1 = M.spherical_kmeans(x, 2, seed=7)
    c2 = M.spherical_kmeans(x, 2, seed=7)
    assert np.array_equal(c1, c2)
    assert c1.shape == (2, 3)
    assert np.allclose(np.linalg.norm(c1, axis=1), 1.0)
    assert sorted(int(np.argmax(r)) for r in c1) == [0, 1]
    assert M.spherical_kmeans(x[:1], 4, seed=1).shape == (1, 3)


def test_knn_shares_and_group_max():
    sims = np.array([[0.9, 0.8, 0.1, 0.7]])
    labels = np.array([0, 1, 1, 2])
    s = M.knn_shares(sims, labels, 3, 2, weighted=False)
    assert s.tolist() == [[0.5, 0.5, 0.0]]
    w = M.knn_shares(sims, labels, 3, 3, weighted=True)
    assert w[0].sum() == pytest.approx(1.0)
    assert w[0, 0] == pytest.approx(0.9 / 2.4)
    g = M.group_max(sims, labels, 4)
    assert g.tolist() == [[0.9, 0.8, 0.7, -1.0]]


def test_rrf_and_scenario_first():
    o1 = [["a_x", "a_y", "b_x", "general_quirky"]]
    o2 = [["b_x", "a_x", "a_y", "general_quirky"]]
    fused = M.rrf([o1, o2], INTENTS, c=0)
    assert fused[0][0] == "a_x"  # 1/1 + 1/2 beats b_x's 1/3 + 1/1
    assert M.scenario_first(["b_x", "a_x", "general_quirky", "a_y"], ["a", "b"], 1) == ["a_x", "a_y", "b_x", "general_quirky"]


def test_catch_all_floor():
    order = ["a_x", "a_y", "b_x", "general_quirky"]
    assert M.catch_all_floor(order, top_cos=0.5, theta=0.3, catch=("general_quirky",), d=2) == order
    moved = M.catch_all_floor(order, top_cos=0.2, theta=0.3, catch=("general_quirky",), d=2)
    assert moved[:2] == ["a_x", "general_quirky"] and sorted(moved) == sorted(order)
    assert M.catch_all_floor(order, 0.2, 0.3, ("a_x",), d=2) == order  # already in the block


def test_csls_and_key_bias():
    keys = np.array([[1.0, 0.0], [0.0, 1.0]])
    q = np.array([[1.0, 0.0], [0.6, 0.8], [0.8, 0.6]])
    pen = M.csls_penalty(keys, q, 2)
    assert pen.tolist() == pytest.approx([0.9, 0.7])
    mu, sd = M.key_bias(keys, q)
    assert mu.tolist() == pytest.approx([0.8, 1.4 / 3])
    assert sd[0] > 0


def test_rate_table_implied_and_compare():
    ids = ["s1", "s2", "s3", "s4"]
    br = {"s1": 1, "s2": 1, "s3": 2, "s4": None}
    out = {"s1": True, "s2": False, "s3": True, "s4": False}
    t = M.rate_table(br, out, ids)
    assert t["1"] == 0.5 and t["2"] == 1.0 and t["off"] == 0.0 and t["8"] == 0.0
    assert M.implied(br, t, ids) == pytest.approx(2.0)  # own table reproduces the count
    base = {"s1": 1, "s2": 9, "s3": 2, "s4": 3}
    alt = {"s1": 2, "s2": 4, "s3": 1, "s4": 12}
    correct = {"s1": True, "s2": False, "s3": True, "s4": True}
    tab = {str(r): 1.0 / r for r in range(1, 9)}
    tab["off"] = 0.0
    c = M.compare(base, alt, ids, correct, {"s2"}, tab, tab)
    assert (c["enters"], c["leaves"], c["net"]) == (1, 1, 0)
    assert c["leaves_delivered_correct"] == 1 and c["enters_intent_wrong"] == 1
    assert c["targets_recovered"] == 1 and c["rank1"] == 1 and c["rank1_base"] == 1
    assert c["moved_to_rank1"] == 1 and c["moved_off_rank1"] == 1
    assert c["implied_note_delta"] == pytest.approx((0.5 + 0.25 + 1.0 + 0.0) - (1.0 + 0.0 + 0.5 + 1 / 3), abs=1e-3)


def test_crossfit_choose_applies_other_half():
    half = {"s1": 0, "s2": 1}
    cands = {"p": {"s1": 1, "s2": 9}, "q": {"s1": 9, "s2": 1}}
    crit = lambda rk, own: sum(1 for s in own if rk[s] == 1)  # noqa: E731
    out = M.crossfit_choose(cands, half, crit)
    assert out["chosen_on_half"] == {"0": "p", "1": "q"}
    assert out["ranks"] == {"s1": 9, "s2": 9}  # half 0 gets half 1's choice and vice versa


def test_top_counts_ties_by_label():
    from collections import Counter

    assert M.top_counts(Counter({"b": 2, "a": 2, "c": 3}), 2) == [["c", 3], ["a", 2]]


def test_classify_miss_order():
    row = {"catch_all": True, "top1_cent_cos": 0.1, "rival_same_scenario": True, "rank_nn1": 3, "rank_cent_cos": 20}
    assert M.classify_miss(row, far_cut=0.2) == "a"
    row["catch_all"] = False
    assert M.classify_miss(row, far_cut=0.2) == "b"
    row["rival_same_scenario"] = False
    assert M.classify_miss(row, far_cut=0.2) == "c"
    row["rank_cent_cos"] = 5
    assert M.classify_miss(row, far_cut=0.2) == "d"
