"""Pure post-seal proposal-content coverage tests for Audio2Tool calls."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_proposal_content_coverage import (
    ProposalContentCoverageError,
    ProposalOccurrence,
    SealedProposalPool,
    audit_proposal_content_coverage,
)


def _occurrence(
    occurrence_id: str,
    name: str,
    arguments: dict[str, object],
    *,
    response_index: int = 0,
    occurrence_index: int = 0,
) -> ProposalOccurrence:
    return ProposalOccurrence(
        occurrence_id=occurrence_id,
        response_index=response_index,
        occurrence_index=occurrence_index,
        call={"name": name, "arguments": arguments},
    )


def _pool(
    family_id: str,
    *occurrences: ProposalOccurrence,
    sealed: bool = True,
) -> SealedProposalPool:
    return SealedProposalPool(
        family_id=family_id,
        sealed=sealed,
        occurrences=occurrences,
    )


def test_exact_coverage_reorders_occurrences_and_preserves_duplicate_multiplicity() -> (
    None
):
    pools = (
        _pool(
            "secondary",
            _occurrence("s-ping", "ping", {"value": 7}, response_index=0),
        ),
        _pool(
            "primary",
            _occurrence(
                "p-configure",
                "configure",
                {"enabled": True, "levels": [1, 1.0, None]},
                response_index=9,
            ),
            _occurrence("p-ping-1", "ping", {"value": 7}, response_index=2),
            _occurrence("p-ping-0", "ping", {"value": 7}, response_index=1),
        ),
    )
    gold_calls = (
        {
            "name": "configure",
            "arguments": {"enabled": True, "levels": [1, 1.0, None]},
        },
        {"name": "ping", "arguments": {"value": 7}},
        {"name": "ping", "arguments": {"value": 7}},
    )
    original_pools = deepcopy(pools)
    original_gold = deepcopy(gold_calls)

    result = audit_proposal_content_coverage(
        sealed_pools=pools,
        gold_calls=gold_calls,
        frozen_family_order=("primary", "secondary"),
    )

    assert result.exact_call_coverage is True
    assert result.correct_tool_coverage is True
    assert result.chosen_occurrence_ids == (
        "p-configure",
        "p-ping-0",
        "p-ping-1",
    )
    assert result.chosen_gold_indexes == (0, 1, 2)
    assert result.canonical_output_json == (
        '[{"name":"configure","arguments":{"enabled":true,'
        '"levels":[1,1.0,null]}},{"name":"ping","arguments":{"value":7}},'
        '{"name":"ping","arguments":{"value":7}}]'
    )
    assert pools == original_pools
    assert gold_calls == original_gold


def test_family_precedence_wins_before_response_and_occurrence_indexes() -> None:
    pools = (
        _pool(
            "later-family",
            _occurrence(
                "later-family-low-index",
                "ping",
                {},
                response_index=0,
                occurrence_index=0,
            ),
        ),
        _pool(
            "first-family",
            _occurrence(
                "first-family-high-index",
                "ping",
                {},
                response_index=20,
                occurrence_index=4,
            ),
        ),
    )

    result = audit_proposal_content_coverage(
        sealed_pools=pools,
        gold_calls=({"name": "ping", "arguments": {}},),
        frozen_family_order=("first-family", "later-family"),
    )

    assert result.chosen_occurrence_ids == ("first-family-high-index",)


def test_exact_pass_reserves_a_later_gold_match_before_same_tool_fallback() -> None:
    pools = (
        _pool(
            "family",
            _occurrence("matches-second", "setMode", {"mode": "night"}),
            _occurrence(
                "fallback-first",
                "setMode",
                {"mode": "away"},
                occurrence_index=1,
            ),
        ),
    )

    result = audit_proposal_content_coverage(
        sealed_pools=pools,
        gold_calls=(
            {"name": "setMode", "arguments": {"mode": "home"}},
            {"name": "setMode", "arguments": {"mode": "night"}},
        ),
        frozen_family_order=("family",),
    )

    assert result.exact_call_coverage is False
    assert result.correct_tool_coverage is True
    assert result.exact_call_count == 1
    assert result.chosen_occurrence_ids == ("fallback-first", "matches-second")
    assert json.loads(result.canonical_output_json) == [
        {"name": "setMode", "arguments": {"mode": "away"}},
        {"name": "setMode", "arguments": {"mode": "night"}},
    ]


@pytest.mark.parametrize(
    ("proposal_value", "gold_value"),
    ((True, 1), (1, 1.0), (0.0, -0.0)),
)
def test_exact_coverage_does_not_coerce_json_value_types_or_values(
    proposal_value: object,
    gold_value: object,
) -> None:
    result = audit_proposal_content_coverage(
        sealed_pools=(
            _pool("family", _occurrence("same-tool", "set", {"value": proposal_value})),
        ),
        gold_calls=({"name": "set", "arguments": {"value": gold_value}},),
        frozen_family_order=("family",),
    )

    assert result.exact_call_coverage is False
    assert result.correct_tool_coverage is True
    assert (
        json.loads(result.canonical_output_json)[0]["arguments"]["value"]
        == proposal_value
    )


def test_missing_duplicate_occurrence_is_reported_without_inventing_a_call() -> None:
    result = audit_proposal_content_coverage(
        sealed_pools=(_pool("family", _occurrence("only-one", "ping", {})),),
        gold_calls=(
            {"name": "ping", "arguments": {}},
            {"name": "ping", "arguments": {}},
        ),
        frozen_family_order=("family",),
    )

    assert result.exact_call_coverage is False
    assert result.correct_tool_coverage is False
    assert result.chosen_occurrence_ids == ("only-one",)
    assert result.chosen_gold_indexes == (0,)
    assert result.missing_exact_gold_indexes == (1,)
    assert result.missing_tool_gold_indexes == (1,)
    assert result.canonical_output_json == '[{"name":"ping","arguments":{}}]'


def test_result_explicitly_limits_itself_to_content_coverage() -> None:
    result = audit_proposal_content_coverage(
        sealed_pools=(_pool("family", _occurrence("one", "ping", {})),),
        gold_calls=({"name": "ping", "arguments": {}},),
        frozen_family_order=("family",),
    )

    payload = result.as_json()
    assert payload["schema"] == "saea-a2t-postseal-proposal-content-coverage-v1"
    assert payload["runtime_or_model_consumability_claimed"] is False
    assert "does not establish model-consumable reachability" in payload["scope_note"]


@pytest.mark.parametrize(
    "bad_call",
    (
        {"name": "ping"},
        {"name": "ping", "arguments": {}, "extra": None},
        {"name": "", "arguments": {}},
        {"name": "ping", "arguments": []},
        {"name": "ping", "arguments": {1: "not-a-JSON-key"}},
        {"name": "ping", "arguments": {"bad": ("not", "a", "JSON array")}},
        {"name": "ping", "arguments": {"bad": float("nan")}},
    ),
)
def test_rejects_malformed_gold_and_proposal_calls(
    bad_call: dict[object, object],
) -> None:
    valid = {"name": "ping", "arguments": {}}
    with pytest.raises(ProposalContentCoverageError, match=r"gold_calls\[0\]"):
        audit_proposal_content_coverage(
            sealed_pools=(_pool("family", _occurrence("one", "ping", {})),),
            gold_calls=(bad_call,),
            frozen_family_order=("family",),
        )
    bad_occurrence = ProposalOccurrence("bad", 0, 0, bad_call)  # type: ignore[arg-type]
    with pytest.raises(ProposalContentCoverageError, match="occurrence 'bad' call"):
        audit_proposal_content_coverage(
            sealed_pools=(_pool("family", bad_occurrence),),
            gold_calls=(valid,),
            frozen_family_order=("family",),
        )


def test_rejects_duplicate_occurrence_ids_before_selection() -> None:
    pools = (
        _pool("first", _occurrence("duplicate", "ping", {})),
        _pool("second", _occurrence("duplicate", "ping", {})),
    )

    with pytest.raises(ProposalContentCoverageError, match="duplicate occurrence id"):
        audit_proposal_content_coverage(
            sealed_pools=pools,
            gold_calls=({"name": "ping", "arguments": {}},),
            frozen_family_order=("first", "second"),
        )


@pytest.mark.parametrize(
    ("pools", "family_order", "message"),
    (
        (
            (_pool("unknown", _occurrence("one", "ping", {})),),
            ("known",),
            "unknown family",
        ),
        (
            (_pool("family", _occurrence("one", "ping", {}), sealed=False),),
            ("family",),
            "not sealed",
        ),
        (
            (_pool("family", _occurrence("one", "ping", {})),),
            ("family", "family"),
            "family order",
        ),
    ),
)
def test_rejects_unknown_family_order_and_unsealed_inputs(
    pools: tuple[SealedProposalPool, ...],
    family_order: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(ProposalContentCoverageError, match=message):
        audit_proposal_content_coverage(
            sealed_pools=pools,
            gold_calls=({"name": "ping", "arguments": {}},),
            frozen_family_order=family_order,
        )


@pytest.mark.parametrize(
    "bad_occurrence",
    (
        ProposalOccurrence("", 0, 0, {"name": "ping", "arguments": {}}),
        ProposalOccurrence("one", True, 0, {"name": "ping", "arguments": {}}),
        ProposalOccurrence("one", -1, 0, {"name": "ping", "arguments": {}}),
        ProposalOccurrence("one", 0, -1, {"name": "ping", "arguments": {}}),
    ),
)
def test_rejects_malformed_occurrence_metadata(
    bad_occurrence: ProposalOccurrence,
) -> None:
    with pytest.raises(ProposalContentCoverageError, match="occurrence"):
        audit_proposal_content_coverage(
            sealed_pools=(_pool("family", bad_occurrence),),
            gold_calls=({"name": "ping", "arguments": {}},),
            frozen_family_order=("family",),
        )
