"""Pure, fail-closed context accounting for future AgentLoop contacts.

This module does not render payloads, tokenize content, or perform transport I/O.
Runtime integration must supply receipt-bound exact counts for an already rendered
payload immediately before each model contact.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re
from typing import Mapping

GGUF_DECLARED_CONTEXT_TOKENS = 65_536
SERVER_WIDE_CONTEXT_TOKENS = 65_536
REQUEST_SLOT_COUNT = 2
PER_SLOT_LIMIT_TOKENS = 32_768
OPERATIONAL_RESERVE_TOKENS = 8_192
#: E17 (2026-09-19): the largest share of a per-slot budget the operational
#: reserve may take when the budget is bound to the LIVE serving geometry
#: rather than to :data:`PER_SLOT_LIMIT_TOKENS`. The registered reserve is a
#: quarter of the registered slot, so at 32,768 tokens this bound is inert and
#: the live-slot budget is byte-identical to the legacy one; it binds only on
#: slots at or under 16,384 tokens, where an absolute 8,192-token reserve
#: would refuse geometries this study has actually flown (the np8 sessions run
#: 8,192-token slots).
MAX_RESERVE_SHARE_DENOMINATOR = 8
REGISTERED_SPECIAL_TOKEN_RESERVE = 2
MAX_COMPACTION_PASSES = 2
MAX_ACCOUNTED_TOKENS = (1 << 63) - 1

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}", flags=re.ASCII)
_DROPPABLE_IDENTIFIER_PREFIXES = ("agent-state:", "facet:", "value:")


class ContextBudgetRefusal(ValueError):
    """The rail refused malformed, incomplete, or inconsistent accounting."""


class ContextBudgetDecision(str, Enum):
    """Possible outcomes of exact context-budget accounting."""

    ALLOW = "ALLOW"
    COMPACT_REQUIRED = "COMPACT_REQUIRED"
    REFUSE = "REFUSE"


def _positive_integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ContextBudgetRefusal(f"{field} must be a positive integer")
    if value > MAX_ACCOUNTED_TOKENS:
        raise ContextBudgetRefusal(f"{field} causes accounting overflow")
    return value


def _checked_sum(values: tuple[int, ...], *, field: str) -> int:
    total = 0
    for value in values:
        if total > MAX_ACCOUNTED_TOKENS - value:
            raise ContextBudgetRefusal(f"{field} causes accounting overflow")
        total += value
    return total


@dataclass(frozen=True)
class ContextBudgetLimits:
    """Validated opt-in limits bound to one composed serving geometry."""

    slot_limit_tokens: int
    operational_reserve_tokens: int = OPERATIONAL_RESERVE_TOKENS

    def __post_init__(self) -> None:
        slot_limit = _positive_integer(
            self.slot_limit_tokens, field="slot_limit_tokens"
        )
        reserve = _positive_integer(
            self.operational_reserve_tokens,
            field="operational_reserve_tokens",
        )
        if slot_limit > GGUF_DECLARED_CONTEXT_TOKENS:
            raise ContextBudgetRefusal(
                "slot_limit_tokens exceeds the GGUF declared context limit"
            )
        if reserve < OPERATIONAL_RESERVE_TOKENS:
            raise ContextBudgetRefusal(
                "operational reserve cannot be lower than the registered reserve"
            )
        if reserve >= slot_limit:
            raise ContextBudgetRefusal(
                "operational reserve must be smaller than slot_limit_tokens"
            )

    @classmethod
    def from_config(
        cls,
        config: object,
        *,
        serving_slot_limit_tokens: int,
    ) -> "ContextBudgetLimits":
        """Parse an exact mapping and bind its slot limit to the adapter."""

        if not isinstance(config, Mapping):
            raise ContextBudgetRefusal(
                "context_budget_limits must be an explicit mapping"
            )
        expected = {"slot_limit_tokens", "operational_reserve_tokens"}
        if set(config) != expected:
            raise ContextBudgetRefusal(
                "context_budget_limits must contain exact fields "
                "slot_limit_tokens and operational_reserve_tokens"
            )
        serving_limit = _positive_integer(
            serving_slot_limit_tokens, field="serving geometry slot limit"
        )
        limits = cls(
            slot_limit_tokens=config["slot_limit_tokens"],
            operational_reserve_tokens=config["operational_reserve_tokens"],
        )
        if limits.slot_limit_tokens != serving_limit:
            raise ContextBudgetRefusal(
                "context budget slot_limit_tokens must equal the serving geometry "
                "slot limit"
            )
        return limits


def serving_bound_reserve_tokens(slot_limit_tokens: int) -> int:
    """The operational reserve for a budget bound to the live serving slot.

    At or above the registered :data:`PER_SLOT_LIMIT_TOKENS` the answer is the
    registered :data:`OPERATIONAL_RESERVE_TOKENS` itself, so the registered
    geometry's receipt stays byte-identical to the legacy one. Below it the
    reserve is one eighth of the live slot
    (:data:`MAX_RESERVE_SHARE_DENOMINATOR`), never more than the registered
    reserve: 3,072 tokens on the 24,576-token SLURP np4 slot, 1,024 on an
    8,192-token np8 slot. E17 first clamped at half the slot, which kept the
    absolute 8,192-token reserve on the 24,576 slot and refused prompts the
    physical slot holds with thousands of tokens to spare (the EFF-1 re-pin
    of 2026-09-19: 19,183 required, physical margin +5,393, refused at
    -2,799); the legacy gate had granted exactly the physical slot, so a
    reserve of one eighth is the smallest that leaves real headroom beyond
    the 512-token completion ceiling without refusing any sealed cell.
    """

    slot_limit = _positive_integer(slot_limit_tokens, field="serving geometry slot limit")
    if slot_limit >= PER_SLOT_LIMIT_TOKENS:
        return OPERATIONAL_RESERVE_TOKENS
    return min(OPERATIONAL_RESERVE_TOKENS, slot_limit // MAX_RESERVE_SHARE_DENOMINATOR)


def _validate_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise ContextBudgetRefusal(f"{field} must be a lowercase SHA-256 digest")
    return value


def _validate_compaction(
    compaction_pass: object,
    dropped_identifiers: object,
) -> tuple[int, tuple[str, ...]]:
    if (
        isinstance(compaction_pass, bool)
        or not isinstance(compaction_pass, int)
        or not 0 <= compaction_pass <= MAX_COMPACTION_PASSES
    ):
        raise ContextBudgetRefusal(
            f"compaction_pass must be an integer from 0 to {MAX_COMPACTION_PASSES}"
        )
    if not isinstance(dropped_identifiers, tuple):
        raise ContextBudgetRefusal("dropped_identifiers must be an immutable tuple")
    seen: set[str] = set()
    for identifier in dropped_identifiers:
        if (
            not isinstance(identifier, str)
            or not identifier.strip()
            or identifier != identifier.strip()
            or not identifier.startswith(_DROPPABLE_IDENTIFIER_PREFIXES)
            or identifier.endswith(":")
            or identifier in seen
        ):
            raise ContextBudgetRefusal(
                "dropped_identifiers must contain unique Agent-state, facet, or value identifiers"
            )
        seen.add(identifier)
    if compaction_pass == 0 and dropped_identifiers:
        raise ContextBudgetRefusal(
            "compaction_pass zero cannot report dropped identifiers"
        )
    if compaction_pass > 0 and not dropped_identifiers:
        raise ContextBudgetRefusal(
            "dropped_identifiers are required for every compaction pass"
        )
    return compaction_pass, dropped_identifiers


@dataclass(frozen=True)
class ContextBudgetBreakdown:
    """Exact, redundantly cross-checked token accounting for one payload."""

    rendered_text_tokens: int
    speech_feature_packet_tokens: tuple[tuple[str, int], ...]
    speech_feature_tokens: int
    special_token_reserve: int
    completion_token_ceiling: int
    required_window_tokens: int

    def __post_init__(self) -> None:
        rendered = _positive_integer(
            self.rendered_text_tokens,
            field="rendered_text_tokens",
        )
        special = _positive_integer(
            self.special_token_reserve,
            field="special_token_reserve",
        )
        completion = _positive_integer(
            self.completion_token_ceiling,
            field="completion_token_ceiling",
        )
        declared_speech = _positive_integer(
            self.speech_feature_tokens,
            field="speech_feature_tokens",
        )
        declared_required = _positive_integer(
            self.required_window_tokens,
            field="required_window_tokens",
        )
        if special != REGISTERED_SPECIAL_TOKEN_RESERVE:
            raise ContextBudgetRefusal(
                "special_token_reserve is inconsistent with the registered reserve"
            )

        packets = self.speech_feature_packet_tokens
        if not isinstance(packets, tuple):
            raise ContextBudgetRefusal(
                "speech_feature_packet_tokens must be an immutable tuple"
            )
        if not packets:
            raise ContextBudgetRefusal(
                "speech_feature_packet_tokens must contain at least one packet count"
            )
        packet_counts: list[int] = []
        packet_ids: set[str] = set()
        for packet in packets:
            if not isinstance(packet, tuple) or len(packet) != 2:
                raise ContextBudgetRefusal(
                    "speech_feature_packet_tokens entries must be identifier/count pairs"
                )
            packet_id, packet_count = packet
            if (
                not isinstance(packet_id, str)
                or not packet_id.strip()
                or packet_id != packet_id.strip()
                or packet_id in packet_ids
            ):
                raise ContextBudgetRefusal(
                    "speech_feature_packet_tokens require unique non-empty identifiers"
                )
            packet_ids.add(packet_id)
            packet_counts.append(
                _positive_integer(
                    packet_count,
                    field="speech_feature_packet_tokens count",
                )
            )

        actual_speech = _checked_sum(
            tuple(packet_counts),
            field="speech_feature_tokens",
        )
        if declared_speech != actual_speech:
            raise ContextBudgetRefusal(
                "speech_feature_tokens is inconsistent with packet counts"
            )
        actual_required = _checked_sum(
            (rendered, actual_speech, special, completion),
            field="required_window_tokens",
        )
        if declared_required != actual_required:
            raise ContextBudgetRefusal(
                "required_window_tokens is inconsistent with component counts"
            )

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe exact accounting representation."""

        return {
            "completion_token_ceiling": self.completion_token_ceiling,
            "rendered_text_tokens": self.rendered_text_tokens,
            "required_window_tokens": self.required_window_tokens,
            "special_token_reserve": self.special_token_reserve,
            "speech_feature_packet_tokens": [
                [packet_id, count]
                for packet_id, count in self.speech_feature_packet_tokens
            ],
            "speech_feature_tokens": self.speech_feature_tokens,
        }


@dataclass(frozen=True)
class ContextBudgetInput:
    """Validated accounting and payload identity for one proposed contact."""

    payload_sha256: str
    breakdown: ContextBudgetBreakdown
    compaction_pass: int = 0
    dropped_identifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_sha256(self.payload_sha256, field="payload_sha256")
        if not isinstance(self.breakdown, ContextBudgetBreakdown):
            raise ContextBudgetRefusal("breakdown must be a ContextBudgetBreakdown")
        _validate_compaction(self.compaction_pass, self.dropped_identifiers)

    @classmethod
    def from_payload(
        cls,
        payload: bytes,
        *,
        breakdown: ContextBudgetBreakdown,
        compaction_pass: int = 0,
        dropped_identifiers: tuple[str, ...] = (),
    ) -> ContextBudgetInput:
        """Bind accounting to exact immutable payload bytes without retaining them."""

        if type(payload) is not bytes:
            raise ContextBudgetRefusal("payload must be exact immutable bytes")
        return cls(
            payload_sha256=hashlib.sha256(payload).hexdigest(),
            breakdown=breakdown,
            compaction_pass=compaction_pass,
            dropped_identifiers=dropped_identifiers,
        )


def _expected_decision(
    *,
    operational_margin_tokens: int,
    compaction_pass: int,
    four_thirds_margin_numerator: int | None = None,
) -> ContextBudgetDecision:
    if operational_margin_tokens >= 0 and (
        four_thirds_margin_numerator is None
        or four_thirds_margin_numerator >= 0
    ):
        return ContextBudgetDecision.ALLOW
    if compaction_pass < MAX_COMPACTION_PASSES:
        return ContextBudgetDecision.COMPACT_REQUIRED
    return ContextBudgetDecision.REFUSE


@dataclass(frozen=True)
class ContextBudgetDecisionReceipt:
    """Immutable and canonically digestible admission-decision receipt."""

    payload_sha256: str
    breakdown: ContextBudgetBreakdown
    decision: ContextBudgetDecision
    physical_margin_tokens: int
    operational_margin_tokens: int
    compaction_pass: int
    dropped_identifiers: tuple[str, ...]
    slot_limit_tokens: int = PER_SLOT_LIMIT_TOKENS
    operational_reserve_tokens: int = OPERATIONAL_RESERVE_TOKENS
    _configuration_bound: bool = False
    # E17 (2026-09-19): this receipt was budgeted against the LIVE serving
    # geometry's per-slot limit rather than against the module-level
    # :data:`PER_SLOT_LIMIT_TOKENS` default, but WITHOUT the extra
    # three-quarter occupancy rule an explicit ``context_budget_limits``
    # block opts into. It exists because the two facts were conflated
    # before: a caller with no declared limits got 32,768 tokens of budget
    # whatever the session's slots really were, which on the SLURP np4
    # ctx24k geometry was 33 % permissive
    # (``docs/results/2026-09-19-slurp-throughput-root-cause-v1.md``
    # section 4). Mutually exclusive with ``_configuration_bound``; at a
    # live slot of exactly :data:`PER_SLOT_LIMIT_TOKENS` the two numbers
    # below are the registered defaults and this receipt is byte-identical
    # to the unbound one it replaces.
    _serving_bound: bool = False

    def __post_init__(self) -> None:
        _validate_sha256(self.payload_sha256, field="payload_sha256")
        if not isinstance(self.breakdown, ContextBudgetBreakdown):
            raise ContextBudgetRefusal("breakdown must be a ContextBudgetBreakdown")
        if not isinstance(self.decision, ContextBudgetDecision):
            raise ContextBudgetRefusal("decision must be a ContextBudgetDecision")
        _validate_compaction(self.compaction_pass, self.dropped_identifiers)
        if type(self._configuration_bound) is not bool:
            raise ContextBudgetRefusal("configuration-bound marker must be boolean")
        if type(self._serving_bound) is not bool:
            raise ContextBudgetRefusal("serving-bound marker must be boolean")
        if self._configuration_bound and self._serving_bound:
            raise ContextBudgetRefusal(
                "a receipt is bound to a declared context budget or to the live "
                "serving geometry, never to both"
            )
        if self._configuration_bound:
            ContextBudgetLimits(
                slot_limit_tokens=self.slot_limit_tokens,
                operational_reserve_tokens=self.operational_reserve_tokens,
            )
        elif self._serving_bound:
            # E17: a live-slot budget is not a declared one. Its slot limit
            # is whatever the served geometry actually is (never above the
            # registered default, which stays the ceiling on an UNDECLARED
            # budget), and its reserve is the registered reserve clamped by
            # :func:`serving_bound_reserve_tokens`.
            slot_limit = _positive_integer(
                self.slot_limit_tokens, field="slot_limit_tokens"
            )
            if slot_limit > PER_SLOT_LIMIT_TOKENS:
                raise ContextBudgetRefusal(
                    "an undeclared budget never exceeds the registered per-slot "
                    "limit; raising it requires an explicit context_budget_limits "
                    "block"
                )
            if self.operational_reserve_tokens != serving_bound_reserve_tokens(slot_limit):
                raise ContextBudgetRefusal(
                    "operational_reserve_tokens drifted from the live-slot reserve"
                )
        else:
            if self.slot_limit_tokens != PER_SLOT_LIMIT_TOKENS:
                raise ContextBudgetRefusal(
                    "slot_limit_tokens drifted from the registered limit"
                )
            if self.operational_reserve_tokens != OPERATIONAL_RESERVE_TOKENS:
                raise ContextBudgetRefusal(
                    "operational_reserve_tokens drifted from the registered floor"
                )
        physical = self.slot_limit_tokens - self.breakdown.required_window_tokens
        operational = physical - self.operational_reserve_tokens
        if self.physical_margin_tokens != physical:
            raise ContextBudgetRefusal("physical_margin_tokens is inconsistent")
        if self.operational_margin_tokens != operational:
            raise ContextBudgetRefusal("operational_margin_tokens is inconsistent")
        expected = _expected_decision(
            operational_margin_tokens=operational,
            compaction_pass=self.compaction_pass,
            four_thirds_margin_numerator=(
                self.slot_limit_tokens * 3
                - self.breakdown.required_window_tokens * 4
                if self._configuration_bound
                else None
            ),
        )
        if self.decision is not expected:
            raise ContextBudgetRefusal("decision is inconsistent with exact accounting")

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe representation containing every receipt field."""

        return {
            "breakdown": self.breakdown.to_dict(),
            "compaction_pass": self.compaction_pass,
            "decision": self.decision.value,
            "dropped_identifiers": list(self.dropped_identifiers),
            "operational_margin_tokens": self.operational_margin_tokens,
            "operational_reserve_tokens": self.operational_reserve_tokens,
            "payload_sha256": self.payload_sha256,
            "physical_margin_tokens": self.physical_margin_tokens,
            "slot_limit_tokens": self.slot_limit_tokens,
        }

    def receipt_sha256(self) -> str:
        """Return SHA-256 over the canonical JSON receipt."""

        encoded = json.dumps(
            self.to_dict(),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def assess_context_budget(
    candidate: ContextBudgetInput,
    *,
    limits: ContextBudgetLimits | None = None,
    serving_slot_limit_tokens: int | None = None,
) -> ContextBudgetDecisionReceipt:
    """Apply legacy limits, a live-slot limit, or the registered default.

    Three budgets, in decreasing order of specificity:

    ``limits`` -- an explicit, validated ``context_budget_limits`` block,
    already bound to the serving geometry by
    :meth:`ContextBudgetLimits.from_config`. Unchanged: it carries its own
    operational reserve and opts into the extra three-quarter occupancy
    rule.

    ``serving_slot_limit_tokens`` (E17, 2026-09-19) -- no declared block, but
    the LIVE per-slot token limit of the session this flight will run on.
    Before this argument existed such a caller silently got
    :data:`PER_SLOT_LIMIT_TOKENS`: a fixed 32,768 whatever the geometry, so
    the SLURP np4 ctx24k sessions (24,576-token slots) were budgeted 33 %
    permissively
    (``docs/results/2026-09-19-slurp-throughput-root-cause-v1.md`` section
    4). The live slot LOWERS the budget and never raises it -- the
    registered default stays the ceiling on an undeclared budget, because
    raising it is what the explicit block is for -- and the reserve is
    :func:`serving_bound_reserve_tokens`. The decision rule is the legacy
    one; only the limit moves. At a live slot of exactly
    :data:`PER_SLOT_LIMIT_TOKENS` this path therefore produces a receipt
    byte-identical to the default one below, down to
    :meth:`ContextBudgetDecisionReceipt.receipt_sha256`.

    Neither -- the module's registered default, unchanged.
    """

    if not isinstance(candidate, ContextBudgetInput):
        raise ContextBudgetRefusal("candidate must be a ContextBudgetInput")
    if limits is not None and not isinstance(limits, ContextBudgetLimits):
        raise ContextBudgetRefusal("limits must be ContextBudgetLimits or None")
    if serving_slot_limit_tokens is not None:
        live_limit = _positive_integer(
            serving_slot_limit_tokens, field="serving geometry slot limit"
        )
        if limits is not None and limits.slot_limit_tokens != live_limit:
            raise ContextBudgetRefusal(
                "declared context budget slot_limit_tokens must equal the live "
                "serving geometry slot limit"
            )
    serving_bound = limits is None and serving_slot_limit_tokens is not None
    if limits is not None:
        slot_limit = limits.slot_limit_tokens
        reserve = limits.operational_reserve_tokens
    elif serving_bound:
        slot_limit = min(live_limit, PER_SLOT_LIMIT_TOKENS)
        reserve = serving_bound_reserve_tokens(slot_limit)
    else:
        slot_limit = PER_SLOT_LIMIT_TOKENS
        reserve = OPERATIONAL_RESERVE_TOKENS
    physical_margin = slot_limit - candidate.breakdown.required_window_tokens
    operational_margin = physical_margin - reserve
    decision = _expected_decision(
        operational_margin_tokens=operational_margin,
        compaction_pass=candidate.compaction_pass,
        four_thirds_margin_numerator=(
            slot_limit * 3 - candidate.breakdown.required_window_tokens * 4
            if limits is not None
            else None
        ),
    )
    return ContextBudgetDecisionReceipt(
        payload_sha256=candidate.payload_sha256,
        breakdown=candidate.breakdown,
        decision=decision,
        physical_margin_tokens=physical_margin,
        operational_margin_tokens=operational_margin,
        compaction_pass=candidate.compaction_pass,
        dropped_identifiers=candidate.dropped_identifiers,
        slot_limit_tokens=slot_limit,
        operational_reserve_tokens=reserve,
        _configuration_bound=limits is not None,
        _serving_bound=serving_bound,
    )
