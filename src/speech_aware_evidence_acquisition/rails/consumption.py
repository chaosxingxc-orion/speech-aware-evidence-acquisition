"""ConsumptionTrace: the USE-axis contract -- per-span, per-supplied-item
outcome records plus the corpus-level ``copy_rate``/``dose_realized`` summary.

Semantics reuse, not reinvention (B0 mission instruction: "align the
semantics with what p2_reads.py already computes; factor shared logic
rather than duplicating"). "Copy" is defined exactly the way
``analysis.p2_reads.copy_count_for_arm`` already defines it for the P2
R-ladder read suite: a verbatim, normalized-token SUBSEQUENCE of the
supplied item's text appearing in the response. :func:`classify_outcome`
below reuses that suite's own subsequence-occurrence primitive
(``analysis.p2_reads._count_subsequence``) directly, via a deferred
function-local import -- the SAME cross-module private-helper reuse pattern
``analysis.p2_reads.copy_count_for_arm`` itself already uses for
``reproduction.replay_loop._unsupported_reference_word`` -- rather than
re-implementing a second copy of the same algorithm.

Only the UNIT of analysis differs: ``p2_reads`` counts REPLAY WINDOWS (the
obs-replay-loop policy has no analog in this engineering-only rails layer);
this module counts SUPPLIED ITEMS. "USE" is a rails-layer addition
``p2_reads`` has no analog for (that suite only ever asks "copied or not"):
it names a weaker, non-verbatim overlap -- the supplied item's tokens appear
in the response, out of verbatim order or only partially, without being
echoed wholesale.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

from ..core.retrieval import normalize_term
from .errors import RailsError
from .hashing import content_hash
from .supply import SupplyPacket

CONSUMPTION_TRACE_VERSION = "consumption-trace-v1"


class ConsumptionOutcome(str, Enum):
    USE = "use"
    COPY = "copy"
    IGNORE = "ignore"


def _match_tokens(text: str) -> list[str]:
    return normalize_term(text).split()


def classify_outcome(response_tokens: Sequence[str], item_tokens: Sequence[str]) -> ConsumptionOutcome:
    """COPY iff the supplied item's normalized tokens occur as a verbatim,
    contiguous subsequence of the response's normalized tokens (the exact
    predicate ``analysis.p2_reads.copy_count_for_arm`` already uses for its
    own copy-occurrence count, reused here rather than reimplemented -- see
    module docstring). USE iff not copied but at least one item token still
    appears anywhere in the response (a non-verbatim overlap). IGNORE iff no
    supplied token appears at all, or the item carried no matchable tokens
    to begin with."""

    # Deferred, function-local import: mirrors analysis.p2_reads.copy_count_for_arm's
    # own reuse of reproduction.replay_loop._unsupported_reference_word (an identical
    # cross-module private-helper pattern already precedented in this repository),
    # and keeps rails' package top level free of analysis/scoring-stack imports for
    # any caller that never actually classifies a consumption outcome.
    from ..analysis.p2_reads import _count_subsequence

    if not item_tokens:
        return ConsumptionOutcome.IGNORE
    if _count_subsequence(list(response_tokens), list(item_tokens)) > 0:
        return ConsumptionOutcome.COPY
    if set(item_tokens) & set(response_tokens):
        return ConsumptionOutcome.USE
    return ConsumptionOutcome.IGNORE


@dataclass(frozen=True)
class ConsumptionRecord:
    span_id: str
    supplied_item_id: str | None
    outcome: ConsumptionOutcome
    evidence: str

    def validate(self) -> "ConsumptionRecord":
        if not isinstance(self.span_id, str) or not self.span_id:
            raise RailsError("ConsumptionRecord.span_id must be a non-empty string")
        if self.supplied_item_id is not None and not isinstance(self.supplied_item_id, str):
            raise RailsError("ConsumptionRecord.supplied_item_id must be a string or None")
        if not isinstance(self.outcome, ConsumptionOutcome):
            raise RailsError(
                f"ConsumptionRecord.outcome must be a ConsumptionOutcome, got {self.outcome!r}"
            )
        if not isinstance(self.evidence, str):
            raise RailsError("ConsumptionRecord.evidence must be a string")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "span_id": self.span_id,
            "supplied_item_id": self.supplied_item_id,
            "outcome": self.outcome.value,
            "evidence": self.evidence,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "ConsumptionRecord":
        return cls(
            span_id=document["span_id"],
            supplied_item_id=document.get("supplied_item_id"),
            outcome=ConsumptionOutcome(document["outcome"]),
            evidence=document["evidence"],
        ).validate()


@dataclass(frozen=True)
class ConsumptionTrace:
    records: tuple[ConsumptionRecord, ...]
    # windows-with-copy / called-windows in p2_reads; here items-with-copy /
    # total supplied items -- the item-level analog of the SAME rate
    # (CopyCountResult.copy_rate's own docstring), 0.0 when there was
    # nothing supplied to copy, never a bare ZeroDivisionError.
    copy_rate: float
    # Count of records whose outcome is USE or COPY (i.e. supply that
    # actually landed in some form) -- always <= len(records).
    dose_realized: int
    trace_version: str = CONSUMPTION_TRACE_VERSION

    def validate(self) -> "ConsumptionTrace":
        for record in self.records:
            if not isinstance(record, ConsumptionRecord):
                raise RailsError("ConsumptionTrace.records entries must be ConsumptionRecord instances")
            record.validate()
        if (
            isinstance(self.copy_rate, bool)
            or not isinstance(self.copy_rate, (int, float))
            or not (0.0 <= float(self.copy_rate) <= 1.0)
        ):
            raise RailsError(f"ConsumptionTrace.copy_rate must be a number in [0, 1], got {self.copy_rate!r}")
        if (
            isinstance(self.dose_realized, bool)
            or not isinstance(self.dose_realized, int)
            or self.dose_realized < 0
        ):
            raise RailsError(
                f"ConsumptionTrace.dose_realized must be a non-negative integer, got "
                f"{self.dose_realized!r}"
            )
        if self.dose_realized > len(self.records):
            raise RailsError("ConsumptionTrace.dose_realized cannot exceed len(records)")
        if not isinstance(self.trace_version, str) or not self.trace_version:
            raise RailsError("ConsumptionTrace.trace_version must be a non-empty string")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "records": [record.as_json() for record in self.records],
            "copy_rate": self.copy_rate,
            "dose_realized": self.dose_realized,
            "trace_version": self.trace_version,
        }

    def content_hash(self) -> str:
        return content_hash(self.validate().as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "ConsumptionTrace":
        return cls(
            records=tuple(ConsumptionRecord.from_json(r) for r in document.get("records", [])),
            copy_rate=document["copy_rate"],
            dose_realized=document["dose_realized"],
            trace_version=document.get("trace_version", CONSUMPTION_TRACE_VERSION),
        ).validate()


def build_consumption_trace(
    *, span_id: str, supply: SupplyPacket | None, response_text: str
) -> ConsumptionTrace:
    """Generic USE/COPY/IGNORE extraction any ``TaskAdapter`` can reuse from
    its own ``extract_consumption`` rather than reimplementing the
    classification rule: one record per ``supply.items`` entry against ONE
    response span. ``supply is None`` or carrying no items (a zero-supply
    arm, or a ``SupplyPacket`` that never populated ``items``) yields an
    empty, all-zero trace -- there is nothing to have used or copied."""

    if supply is None or not supply.items:
        return ConsumptionTrace(records=(), copy_rate=0.0, dose_realized=0)
    response_tokens = _match_tokens(response_text)
    records: list[ConsumptionRecord] = []
    copies = 0
    realized = 0
    for item in supply.items:
        outcome = classify_outcome(response_tokens, _match_tokens(item.text))
        if outcome is ConsumptionOutcome.COPY:
            copies += 1
        if outcome is not ConsumptionOutcome.IGNORE:
            realized += 1
        records.append(
            ConsumptionRecord(
                span_id=span_id,
                supplied_item_id=item.item_id,
                outcome=outcome,
                evidence=item.text,
            )
        )
    copy_rate = copies / len(supply.items)
    return ConsumptionTrace(records=tuple(records), copy_rate=copy_rate, dose_realized=realized).validate()
