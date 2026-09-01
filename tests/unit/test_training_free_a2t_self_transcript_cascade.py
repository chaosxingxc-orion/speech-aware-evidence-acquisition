"""Capability tests for the registered self-transcript cascade."""

from __future__ import annotations

from dataclasses import asdict

import pytest

from speech_aware_evidence_acquisition.analysis import (
    training_free_a2t_self_transcript_cascade as cascade,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import ItemScore


def _snapshot(*, reverse: bool = False, n_extra: int = 0) -> KnowledgeSnapshot:
    rows = [
        (
            "facet-light",
            "dim the kitchen lights to eighty percent",
            "value-light",
            "setLightBrightness",
        ),
        (
            "facet-weather",
            "weather forecast in Boston tomorrow",
            "value-weather",
            "getWeatherForecast",
        ),
        (
            "facet-alarm",
            "set an alarm for seven in the morning",
            "value-alarm",
            "setAlarm",
        ),
    ]
    rows.extend(
        (
            f"facet-extra-{index}",
            f"turn device number {index} on",
            f"value-extra-{index}",
            f"turnDevice{index}",
        )
        for index in range(n_extra)
    )
    if reverse:
        rows.reverse()
    source_ids = tuple(f"train:{index}" for index in range(len(rows)))
    facets = tuple(
        KeyFacet(
            facet_id=facet_id,
            dimension="content",
            representation_kind="text",
            representation=text,
            source_sample_ids=(source_ids[index],),
        ).validate()
        for index, (facet_id, text, _value_id, _target) in enumerate(rows)
    )
    values = tuple(
        ValueBundle(
            value_id=value_id,
            content=(
                f'{{"name":"{target}","arguments":{{"source":"train"}}}}'
            ),
            associated_facet_ids=(facet_id,),
            source_sample_ids=(source_ids[index],),
            provenance_refs=(f"fixture:{value_id}",),
            task_target=target,
        ).validate()
        for index, (facet_id, _text, value_id, target) in enumerate(rows)
    )
    return KnowledgeSnapshot(
        snapshot_id="fixture-self-transcript",
        source_split_identity_hash="a" * 64,
        source_sample_ids=source_ids,
        builder_policy_id="fixture-builder",
        facets=facets,
        values=values,
        source_partition_role="train",
    ).validate()


def _score(exact: int, tool: int | None = None) -> ItemScore:
    return ItemScore(
        tool_accuracy=float(exact if tool is None else tool),
        exact_match=float(exact),
        slot_true_positives=exact,
        slot_expected_total=1,
        slot_predicted_total=1,
    )


def _state(*, relation: str = "intersects") -> cascade.SelfTranscriptState:
    return cascade.SelfTranscriptState(
        m0_relation=relation,
        top1_margin="at-least-0.15",
        positive_facet_count="six-or-more",
        transcript_word_count="five-to-eight",
        supplied_target_count="two-to-three",
    )


def _outcome(
    index: int,
    *,
    stop: int = 0,
    matched: int = 0,
    group_id: str | None = None,
    state: cascade.SelfTranscriptState | None = None,
) -> cascade.SelfTranscriptOutcome:
    return cascade.SelfTranscriptOutcome(
        sample_id=f"tier1:{index:06d}",
        group_id=group_id or f"query-{index:03d}",
        state=state or _state(),
        route_available=True,
        top5_gold_tool_correct=True,
        stop_score=_score(stop),
        matched_score=_score(matched),
        shuffled_score=_score(0),
    )


def test_self_transcript_validator_accepts_only_frozen_english_shape() -> None:
    parsed = cascade.validate_self_transcript(
        "  Turn   the kitchen lights to eighty percent.  "
    )
    assert parsed.valid is True
    assert parsed.text == "Turn the kitchen lights to eighty percent."
    assert parsed.word_count == 7

    rejected = {
        "": "empty",
        "café weather": "ASCII",
        '{"name":"setAlarm","arguments":{}}': "JSON",
        "```text\nset an alarm\n```": "code fence",
        "Assistant: set an alarm": "role prefix",
        "I cannot transcribe this audio": "refusal",
        "word " * 161: "160",
        "1234 -- ???": "letter",
    }
    for text, reason in rejected.items():
        result = cascade.validate_self_transcript(text)
        assert result.valid is False
        assert reason.casefold() in result.reason.casefold()


def test_bm25_route_is_deterministic_order_invariant_and_budgeted() -> None:
    query = "Please dim the kitchen light to eighty percent"
    route = cascade.retrieve_evidence(query, _snapshot(n_extra=8))
    reordered = cascade.retrieve_evidence(query, _snapshot(reverse=True, n_extra=8))
    whitespace = cascade.retrieve_evidence(
        "Please   dim the kitchen\tlight to eighty percent",
        _snapshot(n_extra=8),
    )
    assert route.available is True
    assert route.task_targets[0] == "setLightBrightness"
    assert route.facet_ids == reordered.facet_ids == whitespace.facet_ids
    assert route.value_ids == reordered.value_ids == whitespace.value_ids
    assert len(route.facet_ids) <= 5
    assert len(route.value_ids) <= 6
    assert len(set(route.task_targets)) <= 5
    assert route.positive_facet_count >= len(route.facet_ids)
    assert 0.0 <= route.top1_margin <= 1.0


def test_frozen_retriever_builds_once_and_matches_the_reference_function() -> None:
    snapshot = _snapshot(n_extra=8)
    retriever = cascade.EvidenceRetriever(snapshot)
    first = retriever.route("dim the kitchen light to eighty percent")
    second = retriever.route("weather forecast in Boston tomorrow")
    assert first == cascade.retrieve_evidence(
        "dim the kitchen light to eighty percent", snapshot
    )
    assert second.task_targets[0] == "getWeatherForecast"
    assert retriever.snapshot_sha256 == snapshot.content_hash()


def test_label_free_liveness_barrier_passes_only_the_complete_live_batch() -> None:
    rows = tuple(
        cascade.ObservationRecord(
            sample_id=f"tier{index % 8}:{index:06d}",
            tier=f"tier{index % 8}",
            response_received=True,
            transcript=cascade.validate_self_transcript(
                f"turn device number {index} on"
            ),
            positive_route=True,
        )
        for index in range(104)
    )
    receipt = cascade.authorize_use_phase(rows)
    assert receipt.passed is True
    assert receipt.row_count == 104
    assert receipt.gates == {
        "response_count": True,
        "valid_transcript_count": True,
        "positive_route_count": True,
        "transcript_diversity": True,
        "mode_count": True,
        "prohibited_structure": True,
        "same_tier_derangement": True,
    }

    broken = list(rows)
    for index in range(12):
        broken[index] = cascade.ObservationRecord(
            sample_id=broken[index].sample_id,
            tier=broken[index].tier,
            response_received=True,
            transcript=cascade.validate_self_transcript("same repeated transcript"),
            positive_route=True,
        )
    with pytest.raises(cascade.SelfTranscriptCascadeError, match="liveness"):
        cascade.authorize_use_phase(tuple(broken))


def test_same_tier_derangement_is_deterministic_bijective_and_total() -> None:
    tiers = {
        f"tier{tier}:{index:06d}": f"tier{tier}"
        for tier in range(2)
        for index in range(5)
    }
    mapping = cascade.build_same_tier_derangement(tiers)
    reordered = cascade.build_same_tier_derangement(dict(reversed(tuple(tiers.items()))))
    assert mapping == reordered
    assert set(mapping) == set(mapping.values()) == set(tiers)
    assert all(sample_id != donor_id for sample_id, donor_id in mapping.items())
    assert all(tiers[sample_id] == tiers[donor_id] for sample_id, donor_id in mapping.items())

    with pytest.raises(cascade.SelfTranscriptCascadeError, match="at least two"):
        cascade.build_same_tier_derangement({"tier0:000001": "tier0"})


def test_runtime_state_contains_only_frozen_structural_categories() -> None:
    route = cascade.retrieve_evidence(
        "dim the kitchen light to eighty percent", _snapshot()
    )
    state = cascade.extract_runtime_state(
        transcript=cascade.validate_self_transcript(
            "dim the kitchen light to eighty percent"
        ),
        route=route,
        m0_response='[{"name":"setLightBrightness","arguments":{}}]',
    )
    assert state.m0_relation == "intersects"
    serialized = repr(asdict(state))
    for forbidden in (
        "setLightBrightness",
        "kitchen",
        "facet-light",
        "value-light",
    ):
        assert forbidden not in serialized
    assert state.coarse_key == (
        "intersects",
        state.top1_margin,
        state.positive_facet_count,
    )


def test_reward_memory_uses_only_supported_other_fold_zero_harm_cells() -> None:
    memory = tuple(
        _outcome(index, matched=1 if index < 2 else 0)
        for index in range(4)
    )
    decision = cascade.decide(
        _state(), memory, route_available=True
    )
    assert decision.action == cascade.USE_MATCHED
    assert decision.support == 4
    assert decision.saves == 2
    assert decision.harms == 0

    harmed = memory + (_outcome(9, stop=1, matched=0),)
    assert (
        cascade.decide(_state(), harmed, route_available=True).action
        == cascade.STOP_M0
    )
    assert (
        cascade.decide(_state(), memory[:3], route_available=True).action
        == cascade.STOP_M0
    )


def test_whole_query_groups_never_cross_fold_boundaries() -> None:
    outcomes = tuple(
        _outcome(
            index,
            group_id=f"query-{index // 2}",
            matched=int(index % 3 == 0),
        )
        for index in range(20)
    )
    folds = cascade.assign_folds(outcomes, seed=20260901, n_folds=5)
    group_to_folds: dict[str, set[int]] = {}
    for fold_index, fold in enumerate(folds):
        for item in fold:
            group_to_folds.setdefault(item.group_id, set()).add(fold_index)
    assert set(map(len, group_to_folds.values())) == {1}
    assert {item.sample_id for fold in folds for item in fold} == {
        item.sample_id for item in outcomes
    }


def test_policy_report_keeps_crossfit_and_information_gates_conjunctive() -> None:
    states = (_state(), _state(relation="known-disjoint"))
    outcomes = tuple(
        _outcome(
            index,
            matched=int(index in {0, 1, 5, 6, 10, 11}),
            state=states[index % 2],
        )
        for index in range(20)
    )
    report = cascade.evaluate_policy(
        outcomes,
        liveness_passed=True,
        resend_absolute_exact_count_difference=0,
        seed=20260901,
        n_folds=5,
        n_replicates=200,
    )
    assert len(report.decisions) == 20
    assert report.metrics.observation_contacts == 20
    assert report.metrics.final_contacts == report.metrics.used
    assert report.promotion_passed == all(report.gates.values())
    assert "matched_vs_shuffled_exact" in report.gates
    assert "policy_positive_ci90_lower" in report.gates
