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
    ContextBudgetLimits,
    ContextBudgetRefusal,
    assess_context_budget,
    serving_bound_reserve_tokens,
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


# Configuration-bound limits preserve legacy bytes while allowing a wider
# serving slot only when the composed geometry says exactly the same thing.
def test_legacy_context_budget_receipt_identity_is_unchanged() -> None:
    receipt = assess_context_budget(_candidate(15_090))

    assert receipt.receipt_sha256() == (
        "1507f91e6938b9b3852cd618ecd4a2fd0bf6f4302b30a91464a556abe9fa0daf"
    )
    assert receipt.slot_limit_tokens == 32_768
    assert receipt.operational_reserve_tokens == 8_192


def test_configured_wider_slot_admits_registered_scope_tools_envelope() -> None:
    limits = ContextBudgetLimits.from_config(
        {"slot_limit_tokens": 49_152, "operational_reserve_tokens": 8_192},
        serving_slot_limit_tokens=49_152,
    )

    receipt = assess_context_budget(_candidate(34_868), limits=limits)

    assert receipt.decision is ContextBudgetDecision.ALLOW
    assert receipt.slot_limit_tokens == 49_152
    assert receipt.physical_margin_tokens == 14_284
    assert receipt.operational_margin_tokens == 6_092


def test_configured_legacy_slot_refuses_scope_tools_envelope() -> None:
    limits = ContextBudgetLimits.from_config(
        {"slot_limit_tokens": 32_768, "operational_reserve_tokens": 8_192},
        serving_slot_limit_tokens=32_768,
    )

    assert (
        assess_context_budget(_candidate(34_868), limits=limits).decision
        is ContextBudgetDecision.COMPACT_REQUIRED
    )


def test_configured_limit_keeps_four_thirds_headroom_mandatory() -> None:
    limits = ContextBudgetLimits.from_config(
        {"slot_limit_tokens": 49_152, "operational_reserve_tokens": 8_192},
        serving_slot_limit_tokens=49_152,
    )

    # The fixed reserve alone would allow this request (49,152 - 37,000 -
    # 8,192 = 3,960), but 37,000 * 4 exceeds 49,152 * 3.
    assert (
        assess_context_budget(_candidate(37_000), limits=limits).decision
        is ContextBudgetDecision.COMPACT_REQUIRED
    )


@pytest.mark.parametrize(
    ("config", "serving_slot_limit_tokens", "message"),
    [
        (None, 49_152, "mapping"),
        ({"slot_limit_tokens": 49_152}, 49_152, "exact fields"),
        (
            {
                "slot_limit_tokens": 49_152,
                "operational_reserve_tokens": 8_192,
                "extra": 1,
            },
            49_152,
            "exact fields",
        ),
        (
            {"slot_limit_tokens": 49_152, "operational_reserve_tokens": 8_191},
            49_152,
            "reserve",
        ),
        (
            {"slot_limit_tokens": 65_537, "operational_reserve_tokens": 8_192},
            65_537,
            "GGUF",
        ),
        (
            {"slot_limit_tokens": 49_152, "operational_reserve_tokens": 8_192},
            32_768,
            "serving geometry",
        ),
        (
            {"slot_limit_tokens": True, "operational_reserve_tokens": 8_192},
            49_152,
            "slot_limit_tokens",
        ),
    ],
)
def test_invalid_configured_context_budget_limits_refuse(
    config: object,
    serving_slot_limit_tokens: int,
    message: str,
) -> None:
    with pytest.raises(ContextBudgetRefusal, match=message):
        ContextBudgetLimits.from_config(
            config,
            serving_slot_limit_tokens=serving_slot_limit_tokens,
        )


# ---------------------------------------------------------------------------
# E17 (2026-09-19): the live-slot fit gate.
#
# Before E17, a caller with no declared ``context_budget_limits`` block was
# budgeted against PER_SLOT_LIMIT_TOKENS whatever the served geometry really
# was. Every committed SLURP fragment is such a caller and every one of them
# serves 24,576-token slots, so the preflight gate reasoned against a slot
# 33 % wider than the one it guards
# (docs/results/2026-09-19-slurp-throughput-root-cause-v1.md section 4).
# ---------------------------------------------------------------------------


def test_a_live_slot_of_the_registered_size_is_byte_identical_to_the_default() -> None:
    """The bit-for-bit clause: at a 32,768-token live slot the serving-bound
    receipt is the legacy receipt, down to its pinned digest."""

    legacy = assess_context_budget(_candidate(15_090))
    serving = assess_context_budget(
        _candidate(15_090), serving_slot_limit_tokens=PER_SLOT_LIMIT_TOKENS
    )

    assert serving.to_dict() == legacy.to_dict()
    assert serving.receipt_sha256() == legacy.receipt_sha256()
    assert serving.receipt_sha256() == (
        "1507f91e6938b9b3852cd618ecd4a2fd0bf6f4302b30a91464a556abe9fa0daf"
    )
    assert serving.slot_limit_tokens == 32_768
    assert serving.operational_reserve_tokens == 8_192
    assert serving.decision is ContextBudgetDecision.ALLOW


def test_the_live_slurp_slot_budgets_against_24576_not_32768() -> None:
    """The defect, repaired. 24,576 - 3,072 = 21,504 tokens of budget (one
    eighth of the live slot reserved), not the 32,768 - 8,192 = 24,576 the
    same request used to be granted -- and not 16,384, which refused prompts
    the physical slot holds (the EFF-1 re-pin of 2026-09-19)."""

    required = 22_000
    legacy = assess_context_budget(_candidate(required))
    serving = assess_context_budget(
        _candidate(required), serving_slot_limit_tokens=24_576
    )

    assert legacy.slot_limit_tokens == 32_768
    assert legacy.decision is ContextBudgetDecision.ALLOW
    assert serving.slot_limit_tokens == 24_576
    assert serving.operational_reserve_tokens == 3_072
    assert serving.physical_margin_tokens == 2_576
    assert serving.operational_margin_tokens == -496
    assert serving.decision is ContextBudgetDecision.COMPACT_REQUIRED
    # The real Perception requirement of the sealed SLURP cells (19,183
    # tokens, physical margin +5,393) fits, as it did under the legacy gate.
    assert (
        assess_context_budget(
            _candidate(19_183), serving_slot_limit_tokens=24_576
        ).decision
        is ContextBudgetDecision.ALLOW
    )
    # An 8,192-token np8 slot reserves one eighth, never the absolute reserve.
    assert serving_bound_reserve_tokens(8_192) == 1_024


def test_the_live_slot_never_raises_an_undeclared_budget() -> None:
    """A wider live slot is not a licence: the registered per-slot limit stays
    the ceiling on an UNDECLARED budget, because raising it is exactly what the
    explicit context_budget_limits block (and its extra three-quarter
    occupancy rule) exists for."""

    serving = assess_context_budget(_candidate(15_090), serving_slot_limit_tokens=49_152)

    assert serving.slot_limit_tokens == PER_SLOT_LIMIT_TOKENS
    assert serving.to_dict() == assess_context_budget(_candidate(15_090)).to_dict()


def test_a_narrow_live_slot_keeps_a_proportionate_reserve() -> None:
    """The registered 8,192-token reserve is a quarter of the registered slot.
    On the np8 geometry this study has actually flown (8,192-token slots) an
    absolute reserve would leave no budget at all, so it is clamped to half
    the slot and never more."""

    assert serving_bound_reserve_tokens(32_768) == 8_192
    assert serving_bound_reserve_tokens(24_576) == 3_072
    assert serving_bound_reserve_tokens(16_384) == 2_048
    assert serving_bound_reserve_tokens(8_192) == 1_024
    assert serving_bound_reserve_tokens(4_096) == 512

    receipt = assess_context_budget(_candidate(3_050), serving_slot_limit_tokens=8_192)
    assert receipt.slot_limit_tokens == 8_192
    assert receipt.operational_reserve_tokens == 1_024
    assert receipt.decision is ContextBudgetDecision.ALLOW


def test_a_declared_block_must_agree_with_the_live_slot() -> None:
    limits = ContextBudgetLimits.from_config(
        {"slot_limit_tokens": 49_152, "operational_reserve_tokens": 8_192},
        serving_slot_limit_tokens=49_152,
    )

    # Agreeing: the declared block wins, three-quarter rule and all.
    agreed = assess_context_budget(
        _candidate(34_868), limits=limits, serving_slot_limit_tokens=49_152
    )
    assert agreed.to_dict() == assess_context_budget(
        _candidate(34_868), limits=limits
    ).to_dict()

    with pytest.raises(ContextBudgetRefusal, match="live serving geometry"):
        assess_context_budget(
            _candidate(34_868), limits=limits, serving_slot_limit_tokens=24_576
        )


@pytest.mark.parametrize("value", [0, -1, True, "24576", 1.0])
def test_an_invalid_live_slot_limit_refuses(value: object) -> None:
    with pytest.raises(ContextBudgetRefusal, match="serving geometry slot limit"):
        assess_context_budget(_candidate(15_090), serving_slot_limit_tokens=value)


def test_a_forged_serving_bound_receipt_refuses() -> None:
    receipt = assess_context_budget(_candidate(15_090), serving_slot_limit_tokens=24_576)

    assert receipt.slot_limit_tokens == 24_576
    with pytest.raises(ContextBudgetRefusal, match="live-slot reserve"):
        replace(receipt, operational_reserve_tokens=4_096)
    with pytest.raises(ContextBudgetRefusal, match="registered per-slot limit"):
        replace(receipt, slot_limit_tokens=49_152)
