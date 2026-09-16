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

    def __post_init__(self) -> None:
        _validate_sha256(self.payload_sha256, field="payload_sha256")
        if not isinstance(self.breakdown, ContextBudgetBreakdown):
            raise ContextBudgetRefusal("breakdown must be a ContextBudgetBreakdown")
        if not isinstance(self.decision, ContextBudgetDecision):
            raise ContextBudgetRefusal("decision must be a ContextBudgetDecision")
        _validate_compaction(self.compaction_pass, self.dropped_identifiers)
        if type(self._configuration_bound) is not bool:
            raise ContextBudgetRefusal("configuration-bound marker must be boolean")
        if self._configuration_bound:
            ContextBudgetLimits(
                slot_limit_tokens=self.slot_limit_tokens,
                operational_reserve_tokens=self.operational_reserve_tokens,
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
) -> ContextBudgetDecisionReceipt:
    """Apply legacy limits or an explicit serving-geometry-bound limit."""

    if not isinstance(candidate, ContextBudgetInput):
        raise ContextBudgetRefusal("candidate must be a ContextBudgetInput")
    if limits is not None and not isinstance(limits, ContextBudgetLimits):
        raise ContextBudgetRefusal("limits must be ContextBudgetLimits or None")
    slot_limit = (
        PER_SLOT_LIMIT_TOKENS if limits is None else limits.slot_limit_tokens
    )
    reserve = (
        OPERATIONAL_RESERVE_TOKENS
        if limits is None
        else limits.operational_reserve_tokens
    )
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
    )
