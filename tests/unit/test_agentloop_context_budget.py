"""Model-free capability tests for the AgentLoop context-budget rail."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace

import pytest

from speech_aware_evidence_acquisition.rails.context_budget import (
    GGUF_DECLARED_CONTEXT_TOKENS,
    MAX_ACCOUNTED_TOKENS,
    MAX_COMPACTION_PASSES,
    OPERATIONAL_RESERVE_TOKENS,
    PER_SLOT_LIMIT_TOKENS,
    REGISTERED_SPECIAL_TOKEN_RESERVE,
    REQUEST_SLOT_COUNT,
    SERVER_WIDE_CONTEXT_TOKENS,
    ContextBudgetBreakdown,
    ContextBudgetDecision,
    ContextBudgetInput,
    ContextBudgetRefusal,
    assess_context_budget,
)


def _breakdown(required_window_tokens: int) -> ContextBudgetBreakdown:
    rendered_text_tokens = required_window_tokens - 3_002
    return ContextBudgetBreakdown(
        rendered_text_tokens=rendered_text_tokens,
        speech_feature_packet_tokens=(("query-speech", 2_000),),
        speech_feature_tokens=2_000,
        special_token_reserve=REGISTERED_SPECIAL_TOKEN_RESERVE,
        completion_token_ceiling=1_000,
        required_window_tokens=required_window_tokens,
    )


def _candidate(
    required_window_tokens: int,
    *,
    compaction_pass: int = 0,
    dropped_identifiers: tuple[str, ...] = (),
) -> ContextBudgetInput:
    return ContextBudgetInput(
        payload_sha256="a" * 64,
        breakdown=_breakdown(required_window_tokens),
        compaction_pass=compaction_pass,
        dropped_identifiers=dropped_identifiers,
    )


def test_context_scopes_are_distinct_and_per_slot_is_enforced() -> None:
    assert GGUF_DECLARED_CONTEXT_TOKENS == 65_536
    assert SERVER_WIDE_CONTEXT_TOKENS == 65_536
    assert REQUEST_SLOT_COUNT == 2
    assert PER_SLOT_LIMIT_TOKENS == 32_768
    assert SERVER_WIDE_CONTEXT_TOKENS // REQUEST_SLOT_COUNT == PER_SLOT_LIMIT_TOKENS
    assert OPERATIONAL_RESERVE_TOKENS == 8_192


def test_ground_envelope_is_admitted_with_both_margins() -> None:
    receipt = assess_context_budget(_candidate(15_090))

    assert receipt.decision is ContextBudgetDecision.ALLOW
    assert receipt.physical_margin_tokens == 17_678
    assert receipt.operational_margin_tokens == 9_486


@pytest.mark.parametrize(
    ("required_window_tokens", "expected"),
    [
        (24_576, ContextBudgetDecision.ALLOW),
        (24_577, ContextBudgetDecision.COMPACT_REQUIRED),
    ],
)
def test_operational_reserve_boundary(
    required_window_tokens: int,
    expected: ContextBudgetDecision,
) -> None:
    assert assess_context_budget(_candidate(required_window_tokens)).decision is expected


def test_second_failed_compaction_pass_refuses() -> None:
    receipt = assess_context_budget(
        _candidate(
            24_577,
            compaction_pass=MAX_COMPACTION_PASSES,
            dropped_identifiers=("agent-state:plan-2", "facet:customer"),
        )
    )

    assert receipt.decision is ContextBudgetDecision.REFUSE
    assert receipt.compaction_pass == 2
    assert receipt.dropped_identifiers == (
        "agent-state:plan-2",
        "facet:customer",
    )


def test_second_compaction_pass_may_allow_a_payload_that_clears_the_floor() -> None:
    receipt = assess_context_budget(
        _candidate(
            24_576,
            compaction_pass=MAX_COMPACTION_PASSES,
            dropped_identifiers=("value:stale-account",),
        )
    )

    assert receipt.decision is ContextBudgetDecision.ALLOW


def test_admission_is_stateless_when_a_successor_payload_is_smaller() -> None:
    larger = assess_context_budget(_candidate(24_577))
    smaller = assess_context_budget(_candidate(15_090))

    assert larger.decision is ContextBudgetDecision.COMPACT_REQUIRED
    assert smaller.decision is ContextBudgetDecision.ALLOW


def test_factory_binds_exact_payload_bytes_without_retaining_them() -> None:
    candidate = ContextBudgetInput.from_payload(
        b'{"messages":[{"content":"exact"}]}',
        breakdown=_breakdown(15_090),
    )

    assert candidate.payload_sha256 == (
        "b33a8dbcd9bdd1762e94f06061bdd2c4931dca56ba2c43275b7cd05ab2054f19"
    )
    assert not hasattr(candidate, "payload")
    assert assess_context_budget(candidate).payload_sha256 == candidate.payload_sha256


def test_receipt_is_immutable_hashable_and_canonically_digestible() -> None:
    receipt = assess_context_budget(_candidate(15_090))

    assert isinstance(hash(receipt), int)
    assert len(receipt.receipt_sha256()) == 64
    assert receipt.receipt_sha256() == assess_context_budget(_candidate(15_090)).receipt_sha256()
    assert receipt.to_dict() == {
        "breakdown": {
            "completion_token_ceiling": 1_000,
            "rendered_text_tokens": 12_088,
            "required_window_tokens": 15_090,
            "special_token_reserve": 2,
            "speech_feature_packet_tokens": [["query-speech", 2_000]],
            "speech_feature_tokens": 2_000,
        },
        "compaction_pass": 0,
        "decision": "ALLOW",
        "dropped_identifiers": [],
        "operational_margin_tokens": 9_486,
        "operational_reserve_tokens": 8_192,
        "payload_sha256": "a" * 64,
        "physical_margin_tokens": 17_678,
        "slot_limit_tokens": 32_768,
    }
    with pytest.raises(FrozenInstanceError):
        receipt.compaction_pass = 1  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("rendered_text_tokens", True),
        ("rendered_text_tokens", 1.5),
        ("rendered_text_tokens", 0),
        ("speech_feature_tokens", False),
        ("speech_feature_tokens", -1),
        ("special_token_reserve", 0),
        ("special_token_reserve", True),
        ("completion_token_ceiling", 0),
        ("completion_token_ceiling", 2.5),
        ("required_window_tokens", -1),
        ("required_window_tokens", False),
    ],
)
def test_non_integral_boolean_and_nonpositive_components_refuse(
    field: str,
    bad_value: object,
) -> None:
    with pytest.raises(ContextBudgetRefusal, match=field):
        replace(_breakdown(15_090), **{field: bad_value})


@pytest.mark.parametrize("bad_count", [None, True, 1.25, 0, -1])
def test_missing_or_invalid_packet_counts_refuse(bad_count: object) -> None:
    with pytest.raises(ContextBudgetRefusal, match="speech_feature_packet_tokens"):
        replace(
            _breakdown(15_090),
            speech_feature_packet_tokens=(("query-speech", bad_count),),
        )


def test_missing_packet_accounting_refuses() -> None:
    with pytest.raises(ContextBudgetRefusal, match="at least one"):
        replace(
            _breakdown(15_090),
            speech_feature_packet_tokens=(),
            speech_feature_tokens=1,
        )


@pytest.mark.parametrize(
    "packets",
    [
        (("query-speech",),),
        (("", 2_000),),
        (("query-speech", 1_000), ("query-speech", 1_000)),
        [["query-speech", 2_000]],
    ],
)
def test_malformed_or_mutable_packet_accounting_refuses(packets: object) -> None:
    with pytest.raises(ContextBudgetRefusal, match="speech_feature_packet_tokens"):
        replace(_breakdown(15_090), speech_feature_packet_tokens=packets)


def test_inconsistent_component_totals_refuse() -> None:
    with pytest.raises(ContextBudgetRefusal, match="speech_feature_tokens"):
        replace(_breakdown(15_090), speech_feature_tokens=2_001)

    with pytest.raises(ContextBudgetRefusal, match="required_window_tokens"):
        replace(_breakdown(15_090), required_window_tokens=15_091)


def test_registered_special_token_reserve_drift_refuses() -> None:
    with pytest.raises(ContextBudgetRefusal, match="registered reserve"):
        replace(
            _breakdown(15_090),
            special_token_reserve=3,
            required_window_tokens=15_091,
        )


def test_accounting_overflow_refuses() -> None:
    with pytest.raises(ContextBudgetRefusal, match="overflow"):
        ContextBudgetBreakdown(
            rendered_text_tokens=MAX_ACCOUNTED_TOKENS,
            speech_feature_packet_tokens=(("query-speech", 1),),
            speech_feature_tokens=1,
            special_token_reserve=2,
            completion_token_ceiling=1,
            required_window_tokens=MAX_ACCOUNTED_TOKENS,
        )


@pytest.mark.parametrize("bad_hash", ["", "A" * 64, "g" * 64, "a" * 63, 123])
def test_invalid_payload_hash_refuses(bad_hash: object) -> None:
    with pytest.raises(ContextBudgetRefusal, match="payload_sha256"):
        replace(_candidate(15_090), payload_sha256=bad_hash)


@pytest.mark.parametrize("bad_payload", ["text", bytearray(b"bytes"), None])
def test_payload_binding_accepts_only_exact_immutable_bytes(bad_payload: object) -> None:
    with pytest.raises(ContextBudgetRefusal, match="payload"):
        ContextBudgetInput.from_payload(
            bad_payload,  # type: ignore[arg-type]
            breakdown=_breakdown(15_090),
        )


@pytest.mark.parametrize("bad_pass", [True, -1, 3, 1.0])
def test_invalid_compaction_pass_refuses(bad_pass: object) -> None:
    with pytest.raises(ContextBudgetRefusal, match="compaction_pass"):
        replace(_candidate(15_090), compaction_pass=bad_pass)


def test_compaction_passes_require_exact_immutable_drop_accounting() -> None:
    with pytest.raises(ContextBudgetRefusal, match="dropped_identifiers"):
        replace(_candidate(15_090), compaction_pass=1)
    with pytest.raises(ContextBudgetRefusal, match="compaction_pass zero"):
        replace(_candidate(15_090), dropped_identifiers=("facet:customer",))

    for dropped in (
        ["facet:customer"],
        ("",),
        ("facet:customer", "facet:customer"),
        (123,),
        ("task-contract",),
        ("speech-packet:query",),
        ("output-schema",),
        ("control-instruction",),
        ("completion-token-ceiling",),
    ):
        with pytest.raises(ContextBudgetRefusal, match="dropped_identifiers"):
            replace(
                _candidate(15_090),
                compaction_pass=1,
                dropped_identifiers=dropped,
            )


def test_assessment_rejects_unvalidated_input_objects() -> None:
    with pytest.raises(ContextBudgetRefusal, match="ContextBudgetInput"):
        assess_context_budget({"required_window_tokens": 15_090})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"decision": "ALLOW"}, "decision"),
        ({"slot_limit_tokens": 65_536}, "slot_limit_tokens"),
        ({"operational_reserve_tokens": 1}, "operational_reserve_tokens"),
        ({"physical_margin_tokens": 0}, "physical_margin_tokens"),
        ({"operational_margin_tokens": 0}, "operational_margin_tokens"),
        ({"decision": ContextBudgetDecision.REFUSE}, "decision"),
    ],
)
def test_forged_receipt_fields_refuse(
    changes: dict[str, object],
    message: str,
) -> None:
    receipt = assess_context_budget(_candidate(15_090))

    with pytest.raises(ContextBudgetRefusal, match=message):
        replace(receipt, **changes)
