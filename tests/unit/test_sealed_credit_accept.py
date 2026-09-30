"""Acceptance / nomination: the SLU guard discard, a candidate that clears its
floor vs one that does not, a tie, and "no candidate nominated". Reuses the real
``scripts/checks/stage3_effect_floor_check.py`` FLOOR_TABLE (imported, not
copied) so the guard/floor numbers in these tests are the same ones a real run
would see.
"""

from __future__ import annotations

from pathlib import Path

from speech_aware_evidence_acquisition.analysis.sealed_credit import accept

REPO_ROOT = Path(__file__).resolve().parents[2]
DESIGN = "same-flight-supply-variant"
ROWS = 1080


def _estimate(knob_id, value, intent_pp, slu_pp, unobserved=False):
    return {
        "knob_id": knob_id, "node": "solver_supply", "value": value, "flown_value": "flown",
        "predicted_intent_pp": intent_pp, "predicted_slu_pp": slu_pp,
        "fold_intent_pp": [intent_pp, intent_pp], "fold_slu_pp": [slu_pp, slu_pp] if slu_pp is not None else None,
        "unobserved": unobserved, "evidence": {}, "caveats": [],
    }


def test_design_guard_and_floor_matches_floor_table():
    bounds = accept.design_guard_and_floor(DESIGN, ROWS, REPO_ROOT)
    # owner decision 190 (2026-09-29): per-metric anchors at n = 1,080 -- the guard reads the
    # SLU anchor (1.49 pp), the floor reads the intent anchor (0.65 pp); no admission bar for
    # this design either way.
    assert abs(bounds["guard_pp"] - 1.49) < 0.001
    assert abs(bounds["floor_pp"] - 0.65) < 0.001


def test_candidate_clears_floor_vs_does_not():
    clears = _estimate("k.clears", "v", 5.0, 0.0)
    misses = _estimate("k.misses", "v", 0.05, 0.0)
    ranked = accept.rank_candidates([clears, misses], DESIGN, ROWS, REPO_ROOT)
    by_id = {c["knob_id"]: c for c in ranked}
    assert by_id["k.clears"]["clears_floor"] is True
    assert by_id["k.misses"]["clears_floor"] is False
    assert ranked[0]["knob_id"] == "k.clears"  # ranked by predicted intent gain, descending


def test_slu_guard_discards_a_harmful_candidate():
    bounds = accept.design_guard_and_floor(DESIGN, ROWS, REPO_ROOT)
    guard = bounds["guard_pp"]
    harmful = _estimate("k.harmful", "v", 10.0, -(guard + 1.0))  # SLU well below -guard
    safe = _estimate("k.safe", "v", 1.0, 0.0)
    ranked = accept.rank_candidates([harmful, safe], DESIGN, ROWS, REPO_ROOT)
    by_id = {c["knob_id"]: c for c in ranked}
    assert by_id["k.harmful"]["guard_discarded"] is True
    # a guard-discarded candidate never outranks a non-discarded one, however large its intent gain
    assert ranked[0]["knob_id"] == "k.safe"
    nomination = accept.nominate(ranked)
    assert nomination["nominated"] is True
    assert nomination["candidate"]["knob_id"] == "k.safe"


def test_unmodelled_slu_is_never_guard_discarded():
    candidate = _estimate("k.nomodel", "v", 5.0, None)
    ranked = accept.rank_candidates([candidate], DESIGN, ROWS, REPO_ROOT)
    assert ranked[0]["guard_discarded"] is False


def test_no_candidate_nominated_when_none_clears():
    below_floor = _estimate("k.below", "v", 0.01, 0.0)
    ranked = accept.rank_candidates([below_floor], DESIGN, ROWS, REPO_ROOT)
    nomination = accept.nominate(ranked)
    assert nomination["nominated"] is False
    assert "floor" in nomination["reason"] or "guard" in nomination["reason"]


def test_tie_break_is_deterministic():
    a = _estimate("k.a", "v", 5.0, 0.0)
    b = _estimate("k.b", "v", 5.0, 0.0)
    ranked1 = accept.rank_candidates([a, b], DESIGN, ROWS, REPO_ROOT)
    ranked2 = accept.rank_candidates([b, a], DESIGN, ROWS, REPO_ROOT)
    assert [c["knob_id"] for c in ranked1] == [c["knob_id"] for c in ranked2] == ["k.a", "k.b"]


def test_claim_ceiling_is_always_nominated_never_admitted():
    clears = _estimate("k.clears", "v", 5.0, 0.0)
    ranked = accept.rank_candidates([clears], DESIGN, ROWS, REPO_ROOT)
    nomination = accept.nominate(ranked)
    assert nomination["claim_ceiling"] == "nominated"


def _node_estimate(knob_id, node, intent_pp, slu_pp, unobserved=False):
    e = _estimate(knob_id, "v", intent_pp, slu_pp, unobserved)
    e["node"] = node
    return e


def test_compositions_sum_distinct_nodes_and_score_against_cross_flight_bar():
    estimates = [
        _node_estimate("seed", "perception_seed", 2.0, 0.5),
        _node_estimate("scope", "delivery_scope", 0.0, 1.0),
        _node_estimate("contract", "solver_contract", 0.0, -3.0),
        _node_estimate("passenger", "perception_boundary_depth", 0.0, 0.0, unobserved=True),
    ]
    comps = [
        {"id": "c-ok", "components": [{"knob_id": "seed", "value": "v"}, {"knob_id": "scope", "value": "v"},
                                      {"knob_id": "passenger", "value": "v"}]},
        {"id": "c-harm", "components": [{"knob_id": "seed", "value": "v"}, {"knob_id": "contract", "value": "v"}]},
    ]
    out = {c["id"]: c for c in accept.score_compositions(
        estimates, comps, "cross-flight-with-in-chain-replicate", 1080, REPO_ROOT)}
    assert abs(out["c-ok"]["floor_pp"] - 2.5) < 1e-9
    assert out["c-ok"]["predicted_intent_pp"] == 2.0 and out["c-ok"]["predicted_slu_pp"] == 1.5
    assert out["c-ok"]["clears_floor"] is False  # 2.0 < 2.5 bar
    assert out["c-ok"]["unobserved_component"] is True
    assert out["c-harm"]["guard_discarded"] is True  # -2.5 below -1.2485


def test_composition_naming_unknown_value_is_refused():
    try:
        accept.score_compositions([], [{"id": "x", "components": [{"knob_id": "k", "value": 1}]}],
                                  DESIGN, ROWS, REPO_ROOT)
        assert False, "expected AcceptError"
    except accept.AcceptError:
        pass


def test_admitted_or_closed_lines_are_never_nominated():
    """run 3: a value status other than ``open`` keeps the candidate ranked but not nominated."""
    admitted = {**_estimate("k.admitted", "v", 5.0, 0.0), "status": "admitted"}
    closed = {**_estimate("k.closed", "v", 4.0, 0.0), "status": "closed"}
    open_one = {**_estimate("k.open", "v", 1.0, None), "status": "open"}
    ranked = accept.rank_candidates([admitted, closed, open_one], DESIGN, ROWS, REPO_ROOT)
    assert [c["knob_id"] for c in ranked] == ["k.admitted", "k.closed", "k.open"]
    nomination = accept.nominate(ranked)
    assert nomination["nominated"] is True
    assert nomination["candidate"]["knob_id"] == "k.open"
    assert [c["knob_id"] for c in nomination["cleared_but_not_open"]] == ["k.admitted", "k.closed"]
    none_open = accept.nominate(accept.rank_candidates([admitted], DESIGN, ROWS, REPO_ROOT))
    assert none_open["nominated"] is False
    assert none_open["reason"].startswith("no open candidate")
    # without any status the nomination carries no new key (run 2 bytes unchanged)
    plain = accept.nominate(accept.rank_candidates([_estimate("k.p", "v", 5.0, 0.0)], DESIGN, ROWS, REPO_ROOT))
    assert "cleared_but_not_open" not in plain
