"""Tests for the prospective Audio2Tool self-consistency controller."""

from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_self_consistency as selfcon,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ItemScore


REGISTRY = (
    {
        "tool_id": "1",
        "domain": "home",
        "category": "lighting",
        "tool_name": "setLight",
        "signature": "setLight(room, state)",
        "description": "Set a room light.",
        "argument_defaults": "room=kitchen; state=on",
        "argument_constraints": "state in {on,off}",
    },
    {
        "tool_id": "2",
        "domain": "home",
        "category": "climate",
        "tool_name": "setTemp",
        "signature": "setTemp(room, degrees)",
        "description": "Set a room temperature.",
        "argument_defaults": "room=office; degrees=21",
        "argument_constraints": "degrees is numeric",
    },
)


def _response(calls: list[dict[str, object]]) -> str:
    import json

    return json.dumps(calls, separators=(",", ":"))


def _score(exact: int, tool: int | None = None) -> ItemScore:
    return ItemScore(
        tool_accuracy=float(exact if tool is None else tool),
        exact_match=float(exact),
        slot_true_positives=exact,
        slot_expected_total=1,
        slot_predicted_total=1,
    )


def _outcome(
    sample: int,
    state: selfcon.SelfConsistencyState,
    *,
    delta: int,
    group: str | None = None,
    supply_available: bool = True,
) -> selfcon.SelfConsistencyOutcome:
    stop = 0 if delta > 0 else 1
    supply = 1 if delta >= 0 else 0
    return selfcon.SelfConsistencyOutcome(
        sample_id=f"sample-{sample:03d}",
        group_id=group or f"group-{sample:03d}",
        state=state,
        supply_available=supply_available,
        stop_score=_score(stop),
        supply_score=_score(supply),
    )


def _state(
    tool_relation: str = "exact",
    *,
    value_relation: str = "different",
) -> selfcon.SelfConsistencyState:
    return selfcon.SelfConsistencyState(
        parse_pair="both",
        tool_relation=tool_relation,
        call_count_relation="equal",
        key_signature_relation="exact",
        argument_value_relation=value_relation,
    )


def test_union_renderer_is_registry_ordered_duplicate_invariant_and_strips_defaults() -> None:
    m0 = _response(
        [
            {"name": "setTemp", "arguments": {"room": "office", "degrees": 20}},
            {"name": "setTemp", "arguments": {"room": "office", "degrees": 20}},
        ]
    )
    repeat = _response(
        [
            {"name": "unknownTool", "arguments": {}},
            {"name": "setLight", "arguments": {"room": "kitchen", "state": "on"}},
        ]
    )

    rendered = selfcon.render_union_stripped_registry(m0, repeat, REGISTRY)
    reordered = selfcon.render_union_stripped_registry(
        _response(list(reversed(copy.deepcopy(__import__("json").loads(m0))))),
        _response(list(reversed(copy.deepcopy(__import__("json").loads(repeat))))),
        tuple(reversed(REGISTRY)),
    )

    assert rendered.tool_names == ("setLight", "setTemp")
    assert rendered.text == reordered.text
    assert rendered.text.count('"tool_name"') == 2
    assert "argument_defaults" not in rendered.text
    assert rendered.parsed_pair == (True, True)


def test_union_renderer_refuses_supply_when_no_predicted_tool_resolves() -> None:
    rendered = selfcon.render_union_stripped_registry(
        "not-json", _response([{"name": "unknown", "arguments": {}}]), REGISTRY
    )

    assert rendered.tool_names == ()
    assert rendered.text == ""
    assert rendered.supply_available is False


def test_build_scored_outcomes_keeps_gold_out_of_state_and_marks_availability() -> None:
    m0 = {
        "sample-a": _response(
            [{"name": "setTemp", "arguments": {"room": "office", "degrees": 20}}]
        ),
        "sample-b": "not-json",
    }
    observation = {
        "sample-a": _response(
            [{"name": "setTemp", "arguments": {"room": "office", "degrees": 21}}]
        ),
        "sample-b": _response([{"name": "unknown", "arguments": {}}]),
    }
    supply = {
        "sample-a": _response(
            [{"name": "setTemp", "arguments": {"room": "office", "degrees": 21}}]
        ),
        "sample-b": "[]",
    }
    expected = {
        "sample-a": (
            selfcon.ToolCall(
                "setTemp", {"room": "office", "degrees": 21}
            ),
        ),
        "sample-b": (selfcon.ToolCall("setLight", {"state": "on"}),),
    }

    outcomes = selfcon.build_scored_outcomes(
        m0_response_by_id=m0,
        observation_response_by_id=observation,
        supply_response_by_id=supply,
        query_group_by_id={"sample-a": "group-a", "sample-b": "group-b"},
        registry_rows=REGISTRY,
        expected_by_id=expected,
    )

    assert outcomes[0].sample_id == "sample-a"
    assert outcomes[0].state.argument_value_relation == "different"
    assert outcomes[0].supply_available is True
    assert outcomes[0].delta == 1
    assert outcomes[1].supply_available is False
    assert outcomes[1].delta == 0


def test_state_is_call_order_and_duplicate_invariant() -> None:
    first = _response(
        [
            {"name": "setLight", "arguments": {"state": "on", "room": "kitchen"}},
            {"name": "setTemp", "arguments": {"degrees": 20, "room": "office"}},
        ]
    )
    second = _response(
        [
            {"name": "setTemp", "arguments": {"room": "office", "degrees": 21}},
            {"name": "setLight", "arguments": {"room": "kitchen", "state": "on"}},
        ]
    )
    duplicate_first = _response(
        [
            *copy.deepcopy(__import__("json").loads(first)),
            copy.deepcopy(__import__("json").loads(first)[0]),
        ]
    )
    duplicate_second = _response(
        [
            *copy.deepcopy(__import__("json").loads(second)),
            copy.deepcopy(__import__("json").loads(second)[1]),
        ]
    )

    state = selfcon.extract_self_consistency_state(first, second)
    duplicate_state = selfcon.extract_self_consistency_state(
        duplicate_first, duplicate_second
    )

    assert state.tool_relation == "exact"
    assert state.key_signature_relation == "exact"
    assert state.argument_value_relation == "mixed"
    assert state == duplicate_state


def test_state_uses_official_numeric_equivalence_and_fails_closed_on_parse() -> None:
    integer = _response([{"name": "setTemp", "arguments": {"degrees": 21}}])
    floating = _response([{"name": "setTemp", "arguments": {"degrees": 21.0}}])

    exact = selfcon.extract_self_consistency_state(integer, floating)
    unresolved = selfcon.extract_self_consistency_state("not-json", floating)

    assert exact.argument_value_relation == "exact"
    assert unresolved.parse_pair == "one"
    assert unresolved.tool_relation == "unresolved"
    assert unresolved.argument_value_relation == "unresolved"


def test_hierarchical_memory_uses_detailed_positive_cell_first() -> None:
    target = _state(value_relation="different")
    memory = tuple(_outcome(index, target, delta=1) for index in range(4))

    decision = selfcon.decide(target, memory, supply_available=True, candidate_id="hierarchical-v1")

    assert decision.action == selfcon.SUPPLY_UNION_STRIPPED
    assert decision.level == "detailed"
    assert decision.support == 4
    assert decision.saves == 4
    assert decision.harms == 0


def test_hierarchical_memory_does_not_back_off_past_observed_detailed_harm() -> None:
    target = _state(value_relation="different")
    sibling = _state(value_relation="exact")
    memory = (
        _outcome(0, target, delta=1),
        _outcome(1, target, delta=1),
        _outcome(2, target, delta=-1),
        _outcome(3, target, delta=0),
        *tuple(_outcome(index + 10, sibling, delta=1) for index in range(5)),
    )

    decision = selfcon.decide(target, memory, supply_available=True, candidate_id="hierarchical-v1")

    assert decision.action == selfcon.STOP_M0
    assert decision.level == "detailed"
    assert decision.reason == "observed-harm"


def test_hierarchical_memory_backs_off_when_detailed_support_is_sparse() -> None:
    target = _state(value_relation="different")
    sibling = _state(value_relation="exact")
    memory = (
        _outcome(0, target, delta=1),
        _outcome(1, target, delta=1),
        *tuple(_outcome(index + 10, sibling, delta=1) for index in range(4)),
    )

    decision = selfcon.decide(target, memory, supply_available=True, candidate_id="hierarchical-v1")

    assert decision.action == selfcon.SUPPLY_UNION_STRIPPED
    assert decision.level == "coarse"
    assert decision.support == 6


def test_unavailable_supply_always_stops_before_memory_lookup() -> None:
    state = _state()
    memory = tuple(_outcome(index, state, delta=1) for index in range(5))

    decision = selfcon.decide(state, memory, supply_available=False, candidate_id="coarse-v1")

    assert decision.action == selfcon.STOP_M0
    assert decision.reason == "supply-unavailable"
    assert decision.support == 0


def test_reward_memory_excludes_unavailable_counterfactual_returns() -> None:
    state = _state()
    memory = (
        _outcome(0, state, delta=1),
        _outcome(1, state, delta=1),
        _outcome(2, state, delta=1, supply_available=False),
        _outcome(3, state, delta=1, supply_available=False),
    )

    decision = selfcon.decide(
        state, memory, supply_available=True, candidate_id="coarse-v1"
    )

    assert decision.action == selfcon.STOP_M0
    assert decision.support == 2
    assert decision.saves == 2


def test_crossfit_keeps_whole_groups_together_and_can_pass_all_gates() -> None:
    positive = _state("overlap")
    neutral = _state("exact", value_relation="exact")
    outcomes: list[selfcon.SelfConsistencyOutcome] = []
    for group_index in range(5):
        outcomes.extend(
            [
                _outcome(group_index * 10, positive, delta=1, group=f"positive-{group_index}"),
                _outcome(group_index * 10 + 1, positive, delta=1, group=f"positive-{group_index}"),
            ]
        )
    for index in range(15):
        outcomes.append(_outcome(100 + index, neutral, delta=0))
    outcomes.extend(
        _outcome(200 + index, neutral, delta=-1) for index in range(5)
    )

    folds = selfcon.assign_folds(outcomes, seed=20260901, n_folds=5)
    report = selfcon.evaluate_candidate(
        outcomes,
        candidate_id="hierarchical-v1",
        seed=20260901,
        n_folds=5,
        n_replicates=200,
    )

    fold_by_sample = {
        item.sample_id: fold_index
        for fold_index, fold in enumerate(folds)
        for item in fold
    }
    for group_index in range(5):
        assert fold_by_sample[f"sample-{group_index * 10:03d}"] == fold_by_sample[
            f"sample-{group_index * 10 + 1:03d}"
        ]
    assert report.metrics.supplied == 10
    assert report.metrics.saved == 10
    assert report.metrics.harmed == 0
    assert report.metrics.net_gain == 10
    assert report.metrics.tool_accuracy_net_gain == 10
    assert report.promotion_passed is True
    assert all(report.gates.values())


def test_always_supply_reference_excludes_unavailable_counterfactual_returns() -> None:
    positive = _state("overlap")
    neutral = _state("exact", value_relation="exact")
    outcomes: list[selfcon.SelfConsistencyOutcome] = []
    for group_index in range(5):
        outcomes.extend(
            [
                _outcome(
                    group_index * 10,
                    positive,
                    delta=1,
                    group=f"positive-{group_index}",
                ),
                _outcome(
                    group_index * 10 + 1,
                    positive,
                    delta=1,
                    group=f"positive-{group_index}",
                ),
            ]
        )
    outcomes.extend(_outcome(100 + index, neutral, delta=0) for index in range(15))
    outcomes.append(_outcome(200, positive, delta=1, supply_available=False))

    report = selfcon.evaluate_candidate(
        outcomes,
        candidate_id="hierarchical-v1",
        seed=20260901,
        n_folds=5,
        n_replicates=200,
    )

    assert report.metrics.saved == 10
    assert report.metrics.save_retention == 1.0


def test_screen_is_fail_closed_when_every_candidate_stops() -> None:
    outcomes = tuple(
        _outcome(
            index,
            _state(value_relation=f"value-{index}"),
            delta=1,
            supply_available=False,
        )
        for index in range(10)
    )

    screen = selfcon.screen_candidates(outcomes, n_replicates=100)

    assert screen.promotion_passed is False
    assert screen.selected_candidate is None
    assert all(report.metrics.supplied == 0 for report in screen.reports.values())


def test_policy_artifact_is_self_hashed_and_prospective_admission_is_fail_closed() -> None:
    positive = _state("overlap")
    neutral = _state("exact", value_relation="exact")
    outcomes = tuple(
        [
            *(
                _outcome(index, positive, delta=1, group=f"g-{index // 2}")
                for index in range(10)
            ),
            *(_outcome(20 + index, neutral, delta=0) for index in range(10)),
            *(_outcome(40 + index, neutral, delta=-1) for index in range(5)),
        ]
    )
    screen = selfcon.screen_candidates(outcomes, n_replicates=200)

    artifact = selfcon.build_policy_artifact(
        outcomes,
        screen,
        source_hashes={"m0": "a" * 64, "repeat": "b" * 64, "supply": "c" * 64},
        offline_attempts=0,
    )

    selfcon.assert_self_hash(artifact)
    selfcon.assert_policy_admits_support(artifact)
    broken = copy.deepcopy(artifact)
    broken["selected"]["metrics"]["supplied"] = 0
    broken = selfcon.with_self_hash(broken)
    with pytest.raises(selfcon.SelfConsistencyError, match="does not exercise supply"):
        selfcon.assert_policy_admits_support(broken)
