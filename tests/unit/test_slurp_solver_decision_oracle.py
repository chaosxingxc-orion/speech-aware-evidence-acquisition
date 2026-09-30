"""scripts/analysis/slurp_solver_decision_oracle.py -- pure parts on fakes.

All synthetic: no sealed run, no gold, no utterance or model text. Placeholder intent ids
(``s1_a`` ...) and placeholder sample ids only. Covers the row classifier, the score margin, the
AUC and its bootstrap, the utterance half split, both target encoders, the logistic fit, the F1
threshold, the cross-fitted two-signal rule (including cost rows), the evidence-follow
counterfactual and the expected-rows arithmetic.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_solver_decision_oracle.py"

_spec = importlib.util.spec_from_file_location("slurp_solver_decision_oracle", DRIVER_PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules["slurp_solver_decision_oracle"] = M
_spec.loader.exec_module(M)


def test_classify_decision_classes():
    note = ["s1_a", "s1_b", "s2_c"]
    pos = M.classify(note, "s1_a", "s1_b")
    assert pos == {"gold_rank": 2, "pick_rank": 1, "decision": True, "label": 1, "correct": False, "ceiling": True}
    neg = M.classify(note, "s1_a", "s1_a")
    assert neg["label"] == 0 and neg["correct"] and not neg["ceiling"]
    absent = M.classify(note, "s1_a", "s9_z")
    assert absent["decision"] and absent["label"] is None and not absent["ceiling"]
    # Solver left rank 1: not in the decision population, still in the ceiling when wrong
    left = M.classify(note, "s2_c", "s1_b")
    assert not left["decision"] and left["ceiling"]
    # a one-candidate note has no runner-up
    assert not M.classify(["s1_a"], "s1_a", "s1_a")["decision"]
    # unparsed pick
    unp = M.classify(note, None, "s1_b")
    assert unp["pick_rank"] is None and not unp["correct"] and unp["ceiling"]


def test_score_margin_and_missing():
    order, scores = ["a", "b", "c"], [0.9, 0.5, 0.1]
    assert M.score_margin(order, scores, "a", "b") == pytest.approx(0.4)
    assert M.score_margin(order, scores, "b", "z") == pytest.approx(0.4)  # missing takes the last score
    assert M.score_margin([], [], "a", "b") is None


def test_auc_and_boot():
    assert M.auc([0.1, 0.2, 0.8, 0.9], [0, 0, 1, 1]) == pytest.approx(1.0)
    assert M.auc([0.1, 0.5, 0.5], [0, 0, 1]) == pytest.approx(0.75)
    assert M.auc([1, 1], [1, 1]) is None
    lo, hi = M.boot_auc([0.1, 0.2, 0.3, 0.8, 0.9, 0.7], [0, 0, 0, 1, 1, 1], draws=200, seed=1)
    assert lo <= hi and hi == pytest.approx(1.0)


def test_split_half_is_stable():
    assert M.split_half("utt-1") == M.split_half("utt-1")
    assert {M.split_half(f"utt-{i}") for i in range(20)} == {0, 1}


def test_target_encoders_use_the_other_half_only():
    rows = [{"half": 0, "k": "x", "label": 1}, {"half": 0, "k": "x", "label": 1},
            {"half": 1, "k": "x", "label": 0}, {"half": 1, "k": "x", "label": 0}]
    enc = M.target_encode(rows, "k", prior_n=0.0)
    # half-0 rows see half 1 (rate 0); half-1 rows see half 0 (rate 1)
    assert enc == [0.0, 0.0, 1.0, 1.0]
    other = M.target_encode_apply(rows, [{"half": 0, "scen": None, "k": "x"}], "k", prior_n=0.0)
    assert other == [0.0]


def test_logistic_and_f1_threshold():
    X = [[0.0], [0.1], [0.2], [0.8], [0.9], [1.0]]
    y = [0, 0, 0, 1, 1, 1]
    model = M.fit_logistic(X, y)
    p = list(M.predict_logistic(model, X))
    assert p[0] < 0.5 < p[-1]
    t = M.f1_threshold(p, y)
    assert all((pi >= t) == bool(yi) for pi, yi in zip(p, y))


def _fake_rows(n=400, seed=7):
    rng = random.Random(seed)
    rows = []
    for i in range(n):
        y = 1 if rng.random() < 0.2 else 0
        rows.append({"half": i % 2, "label": y,
                     "sig_a": rng.gauss(1.0 if y else 0.0, 0.5),   # informative
                     "sig_b": rng.gauss(0.0, 1.0),                  # noise
                     "sig_c": rng.gauss(0.5 if y else 0.0, 0.5)})   # weaker
    return rows


def test_crossfit_pair_rule_picks_informative_pair_and_counts_cost_rows():
    rows = _fake_rows()
    cost = [{"half": i % 2, "label": None, "sig_a": 5.0, "sig_b": 0.0, "sig_c": 5.0} for i in range(10)]
    out = M.crossfit_pair_rule(rows, ["sig_a", "sig_b", "sig_c"], cost)
    for h in out["halves"].values():
        assert "sig_a" in h["pair"]
    assert out["out_of_half_auc_pooled_scores"] > 0.8
    f1 = out["operating"]["f1_threshold"]
    assert f1["called_cost_rows"] == 10  # extreme cost rows are always called
    assert f1["called"] == f1["tp"] + f1["fp"] + f1["called_cost_rows"]
    assert f1["precision"] <= f1["precision_excl_cost_rows"]
    assert out["positives"] == sum(r["label"] for r in rows)


def test_evidence_follow_counterfactual():
    rows = [
        # evidence (votes) favours r2 and r2 is gold -> gain
        {"gold": "b", "gold_rank": 2, "cand_ex": [("a", 1, 1), ("b", 5, 2)]},
        # evidence favours r2 but r1 is gold -> loss
        {"gold": "a", "gold_rank": 1, "cand_ex": [("a", 1, 1), ("b", 5, 2)]},
        # evidence agrees with r1 -> not counted
        {"gold": "a", "gold_rank": 1, "cand_ex": [("a", 5, 1), ("b", 1, 2)]},
        # tie keeps r1 -> not counted
        {"gold": "b", "gold_rank": 2, "cand_ex": [("a", 3, 1), ("b", 3, 2)]},
        # evidence favours r3, gold is elsewhere -> neither
        {"gold": "z", "gold_rank": None, "cand_ex": [("a", 0, 1), ("b", 0, 2), ("c", 2, 3)]},
    ]
    out = M.evidence_follow(rows, "ex")
    assert out == {"evidence_disagrees_with_r1": 3, "evidence_pick_is_gold": 1, "neither": 1,
                   "net_rows_if_followed": 0, "r1_is_gold": 1}


def test_expected_rows_and_floor_rows():
    assert M.expected_rows(20, 60, 0.5, 0.05) == pytest.approx(7.0)
    assert M.expected_rows(20, 60, None, 0.1) is None
    assert M.rows_for_pp(0.65) == pytest.approx(7.02)
    assert M.scenario_of("audio_volume_mute") == "audio"
    assert M.rank_of(["a", "b"], "b") == 2 and M.dedupe(["a", "a", "", None, "b"]) == ["a", "b"]


def test_precision_needed():
    # 40 TP x 0.25 = 10 rows; need 7 -> FP may cost 3 rows at harm 0.05 -> FP <= 60 -> p >= 40/100
    assert M.precision_needed(80, 0.5, 0.25, 0.05, 7.0) == pytest.approx(0.4)
    assert M.precision_needed(80, 0.5, 0.1, 0.05, 7.0) is None
    assert M.precision_needed(80, 0.5, 0.25, 0.0, 7.0) == 0.0
