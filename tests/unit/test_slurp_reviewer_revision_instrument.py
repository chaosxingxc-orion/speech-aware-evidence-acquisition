"""scripts/analysis/slurp_reviewer_revision_instrument.py -- pure parts on fakes.

All synthetic: no sealed run, no gold, no utterance or model text. Placeholder intent ids (``s1_a`` ...)
and placeholder sample ids only. Covers the row-state reader, the revision record (built on the oracle's
``classify``), reach, conversion / harm, the cluster bootstrap of the net, the flag operating point, the
cross-fitted threshold and the leave-pool-out switching propensity.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "analysis" / "slurp_reviewer_revision_instrument.py"

_spec = importlib.util.spec_from_file_location("slurp_reviewer_revision_instrument", DRIVER_PATH)
M = importlib.util.module_from_spec(_spec)
sys.modules["slurp_reviewer_revision_instrument"] = M
_spec.loader.exec_module(M)


def _pick(text):
    return None if text in (None, "", "garbled") else text


def _result(note, answers, routes, ex=(), block=()):
    states = [{"state_kind": "phase:perception",
               "content": json.dumps({"candidates": [{"intent_id": c} for c in note]})}]
    for a in answers:
        states.append({"state_kind": "phase:solver", "content": a})
        states.append({"state_kind": "phase:reviewer", "content": "x"})
    return {"sample_id": "s", "agent_states": states,
            "native_episode_receipt": {"planner_routes": [{"action": r} for r in routes]},
            "waves": [{"fusion_decision": {"selected_value_ids": [M.OR.EX_PREFIX + k for k in ex]}}],
            "initial_query_state": {"retrieved_value_ids": ["intent-boundaries::" + M.OR.IB_FACET_MARK + b for b in block]}}


def test_row_state_reads_note_answers_routes():
    st = M.row_state(_result(["s1_a", "s1_a", "s1_b"], ["s1_a", "s1_b"], ["REVISE", "ACCEPT"], ex=["k1"], block=["s1_a"]), _pick)
    assert st["note"] == ["s1_a", "s1_b"]  # deduplicated in order
    assert st["answers"] == ["s1_a", "s1_b"]
    assert st["routes"] == ["REVISE", "ACCEPT"]
    assert st["ex"] == ["k1"] and st["block"] == ["s1_a"]


def test_revision_record_positive_converted():
    st = {"note": ["s1_a", "s1_b", "s2_c"], "answers": ["s1_a", "s1_b"], "routes": ["REVISE", "ACCEPT"]}
    r = M.revision_record(st, "s1_b")
    assert r["label"] == 1 and r["revise"] and r["executed"]
    assert r["revised_correct"] and r["final_correct"] and not r["first_correct"]
    assert r["revised_rank"] == 2 and r["revised_changed"]


def test_revision_record_harm_and_accept():
    st = {"note": ["s1_a", "s1_b"], "answers": ["s1_a", "s1_b"], "routes": ["REVISE", "ACCEPT"]}
    r = M.revision_record(st, "s1_a")
    assert r["label"] == 0 and r["first_correct"] and not r["final_correct"]
    acc = M.revision_record({"note": ["s1_a", "s1_b"], "answers": ["s1_a"], "routes": ["ACCEPT"]}, "s1_b")
    assert acc["label"] == 1 and not acc["revise"] and not acc["executed"] and not acc["final_correct"]
    late = M.revision_record({"note": ["s1_a", "s1_b"], "answers": ["s1_a", "s1_a"], "routes": ["ACCEPT", "REVISE"]}, "s1_a")
    assert late["later_revise"] and not late["revise"]
    sw = M.revision_record({"note": ["s1_a", "s1_b"], "answers": ["s1_b"], "routes": ["ACCEPT"]}, "s1_b")
    assert sw["switched"] and not sw["decision"]


def _rec(label, revise, final, gold_rank, first_correct=None, decision=True, sid="x", half=0):
    return {"label": label, "revise": revise, "final_correct": final, "revised_correct": final,
            "gold_rank": gold_rank, "first_correct": (label == 0) if first_correct is None else first_correct,
            "decision": decision, "switched": False, "later_revise": False, "sid": sid, "half": half}


def test_reach_and_conversion():
    rows = [_rec(1, True, True, 2), _rec(1, True, False, 3), _rec(1, False, False, 2),
            _rec(0, True, False, 1), _rec(0, False, True, 1), _rec(None, True, False, None, first_correct=False)]
    rc = M.reach(rows)
    assert rc["positives"] == 3 and rc["revise_rows"] == 4 and rc["revise_on_positive"] == 2
    assert rc["recall"] == round(2 / 3, 4) and rc["precision"] == 0.5
    cv = M.conversion(rows)
    assert cv["gold_rank_2"] == [1, 1] and cv["gold_rank_3"] == [0, 1] and cv["conversion"] == 0.5
    assert cv["first_right"] == [1, 1] and cv["harm"] == 1.0
    assert cv["first_wrong_gold_off_note"] == [0, 1]


def test_paired_net_deterministic():
    d = {f"s{i}": [0] for i in range(96)}
    d.update({"s96": [1], "s97": [1], "s98": [-1], "s99": [0]})
    a = M.paired_net(d, 100, draws=500, seed=1)
    b = M.paired_net(d, 100, draws=500, seed=1)
    assert a == b and a["net_rows"] == 1 and a["pp"] == 1.0 and a["saves"] == 2 and a["harms"] == 1
    assert a["ci95_pp"][0] <= 1.0 <= a["ci95_pp"][1]


def test_flag_eval_arithmetic():
    rows = [_rec(1, 0, 0, 2), _rec(0, 0, 0, 1), _rec(None, 0, 0, None)]
    e = M.flag_eval(rows, [True, True, True], c=0.5, h=0.1)
    assert e["tp"] == 1 and e["fp"] == 1 and e["cost"] == 1 and e["precision"] == round(1 / 3, 4)
    assert e["implied_net_rows"] == 0.4 and e["recall"] == 1.0


def test_crossfit_threshold_uses_other_half():
    rows = []
    for h in (0, 1):
        rows += [dict(_rec(1, 0, 0, 2, half=h), s=0.9), dict(_rec(0, 0, 0, 1, half=h), s=0.1),
                 dict(_rec(0, 0, 0, 1, half=h), s=0.2)]
    flags, thr = M.crossfit_flags(rows, "s", "net", c=0.5, h=0.1)
    assert thr == {"0": 0.9, "1": 0.9}
    assert flags == [True, False, False, True, False, False]
    f1, _ = M.crossfit_flags(rows, "s", "f1")
    assert f1 == flags


def test_switch_propensity_leave_pool_out():
    ranks = {"p": {"a": 2}, "q": {"a": 1}, "r": {"a": 3}, "t": {"a": None}}
    assert M.switch_propensity(ranks, "p", "a") == 0.5
    assert M.switch_propensity(ranks, "q", "a") == 1.0
    assert M.switch_propensity({"p": {"a": 1}}, "p", "a") is None


def test_wilson_bounds():
    lo, hi = M.wilson(10, 54)
    assert 0.09 < lo < 0.185 < hi < 0.32
    assert M.wilson(0, 0) == [None, None]
