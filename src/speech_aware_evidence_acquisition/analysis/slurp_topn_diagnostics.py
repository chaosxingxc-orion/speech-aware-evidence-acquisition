"""Pure Top-N candidate and final-intent diagnostic aggregation.

This module consumes already verified, caller supplied identities only. It does
not load a roster, infer a reference label, score an entity, or resample rows.
The current SLURP experiment fixes the caller's candidate_width at three; the
implementation remains width agnostic for reuse by another registered
comparison.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


class TopNDiagnosticError(ValueError):
    """Raised when diagnostic inputs are malformed or have different rosters."""


@dataclass(frozen=True)
class SourceCandidateRow:
    """One verified sample and its ordered candidate intent IDs.

    candidate_ids must be a non-string ordered sequence. The aggregator
    preserves order and never ranks or deduplicates it.
    """

    sample_id: str
    candidate_ids: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceIntentRow:
    """One verified sample and its separately supplied reference intent ID."""

    sample_id: str
    intent_id: str


@dataclass(frozen=True)
class BranchOutcomeRow:
    """One branch's final intent/refusal and optional official entity result.

    A refused row may retain a final_intent_id as an attempted intent for
    shortlist diagnostics. That attempted ID never counts as accepted final
    quality. A nonrefused delivery without an intent must explicitly declare
    missing_final_intent; it remains an incorrect all-roster outcome, not a
    refusal or a candidate-width exclusion.
    """

    sample_id: str
    final_intent_id: str | None
    refused: bool
    entity_correct: bool | None = None
    missing_final_intent: bool = False


@dataclass(frozen=True)
class BranchSampleDiagnostic:
    """Derived per-sample status for one final-delivery branch."""

    final_intent_id: str | None
    refused: bool
    final_intent_correct: bool
    rescue: bool
    harm: bool
    out_of_shortlist: bool
    candidate_present: bool
    candidate_present_final_correct: bool
    candidate_present_final_not_selected: bool
    final_intent_attempt_only: bool
    entity_correct: bool | None
    entity_partition: str
    missing_final_intent: bool = False


@dataclass(frozen=True)
class TopNSampleDiagnostic:
    """Derived source and branch diagnostics for one sample."""

    sample_id: str
    candidate_ids: tuple[str, ...]
    reference_intent_id: str
    top1_correct: bool
    topn_included: bool
    missing_true_candidate: bool
    present_not_selected: bool
    branches: Mapping[str, BranchSampleDiagnostic]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "branches", MappingProxyType(dict(self.branches))
        )

    def as_json(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "candidate_ids": list(self.candidate_ids),
            "reference_intent_id": self.reference_intent_id,
            "top1_correct": self.top1_correct,
            "topn_included": self.topn_included,
            "missing_true_candidate": self.missing_true_candidate,
            "present_not_selected": self.present_not_selected,
            "true_candidate_present_but_source_rank1_not_selected": (
                self.present_not_selected
            ),
            "branches": {
                name: {
                    "final_intent_id": value.final_intent_id,
                    "refused": value.refused,
                    "missing_final_intent": value.missing_final_intent,
                    "final_intent_correct": value.final_intent_correct,
                    "rescue": value.rescue,
                    "harm": value.harm,
                    "out_of_shortlist": value.out_of_shortlist,
                    "candidate_present": value.candidate_present,
                    "candidate_present_final_correct": (
                        value.candidate_present_final_correct
                    ),
                    "candidate_present_final_not_selected": (
                        value.candidate_present_final_not_selected
                    ),
                    "final_intent_attempt_only": value.final_intent_attempt_only,
                    "entity_correct": value.entity_correct,
                    "entity_partition": value.entity_partition,
                }
                for name, value in self.branches.items()
            },
        }


@dataclass(frozen=True)
class SourceCandidateSummary:
    """Aggregate source Top-1, Top-N and candidate-presence counts.

    present_not_selected means the reference intent is in the considered
    ordered Top-N but differs from source rank one. The explicit serialized
    alias names this coverage-versus-source-resolution distinction.
    """

    sample_count: int
    top1_correct: int
    topn_included: int
    missing_true_candidate: int
    present_not_selected: int

    @property
    def top1_accuracy(self) -> float:
        return self.top1_correct / self.sample_count

    @property
    def topn_inclusion(self) -> float:
        return self.topn_included / self.sample_count

    def as_json(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "top1_correct": self.top1_correct,
            "top1_accuracy": self.top1_accuracy,
            "topn_included": self.topn_included,
            "topn_inclusion": self.topn_inclusion,
            "missing_true_candidate": self.missing_true_candidate,
            "present_not_selected": self.present_not_selected,
            "true_candidate_present_but_source_rank1_not_selected": (
                self.present_not_selected
            ),
        }


@dataclass(frozen=True)
class BranchDiagnosticSummary:
    """Aggregate final, transition, refusal and optional entity partitions."""

    sample_count: int
    final_intent_correct: int
    refusals: int
    out_of_shortlist_attempts: int
    candidate_present: int
    candidate_present_final_correct: int
    candidate_present_final_not_selected: int
    refusal_attempts_with_intent: int
    rescues: int
    harms: int
    unchanged_correct: int
    unchanged_wrong: int
    entity_available: int
    entity_unavailable: int
    intent_correct_entity_correct: int
    intent_correct_entity_incorrect: int
    intent_incorrect_entity_correct: int
    intent_incorrect_entity_incorrect: int
    missing_final_intents: int = 0

    @property
    def final_intent_accuracy(self) -> float:
        return self.final_intent_correct / self.sample_count

    @property
    def candidate_present_final_correct_rate(self) -> float | None:
        if not self.candidate_present:
            return None
        return self.candidate_present_final_correct / self.candidate_present

    @property
    def candidate_present_final_not_selected_rate(self) -> float | None:
        if not self.candidate_present:
            return None
        return (
            self.candidate_present_final_not_selected / self.candidate_present
        )

    def as_json(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "final_intent_correct": self.final_intent_correct,
            "final_intent_accuracy": self.final_intent_accuracy,
            "refusals": self.refusals,
            "missing_final_intents": self.missing_final_intents,
            "out_of_shortlist_attempts": self.out_of_shortlist_attempts,
            "candidate_present": self.candidate_present,
            "candidate_present_final_correct": (
                self.candidate_present_final_correct
            ),
            "candidate_present_final_correct_rate": (
                self.candidate_present_final_correct_rate
            ),
            "candidate_present_final_not_selected": (
                self.candidate_present_final_not_selected
            ),
            "candidate_present_final_not_selected_rate": (
                self.candidate_present_final_not_selected_rate
            ),
            "refusal_attempts_with_intent": self.refusal_attempts_with_intent,
            "rescues": self.rescues,
            "harms": self.harms,
            "unchanged_correct": self.unchanged_correct,
            "unchanged_wrong": self.unchanged_wrong,
            "entity_available": self.entity_available,
            "entity_unavailable": self.entity_unavailable,
            "intent_correct_entity_correct": self.intent_correct_entity_correct,
            "intent_correct_entity_incorrect": self.intent_correct_entity_incorrect,
            "intent_incorrect_entity_correct": self.intent_incorrect_entity_correct,
            "intent_incorrect_entity_incorrect": self.intent_incorrect_entity_incorrect,
        }


@dataclass(frozen=True)
class TopNDiagnosticReport:
    """Complete source and branch diagnostic result for one exact roster."""

    candidate_width: int
    source: SourceCandidateSummary
    branches: Mapping[str, BranchDiagnosticSummary]
    per_sample: tuple[TopNSampleDiagnostic, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "branches", MappingProxyType(dict(self.branches))
        )

    def as_json(self) -> dict[str, Any]:
        return {
            "schema": "saea-slurp-topn-diagnostics-v1",
            "candidate_width": self.candidate_width,
            "source": self.source.as_json(),
            "branches": {
                name: value.as_json() for name, value in self.branches.items()
            },
            "per_sample": [row.as_json() for row in self.per_sample],
        }


def _rows(value: object, label: str) -> tuple[object, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TopNDiagnosticError(f"{label} must be a nonempty sequence")
    result = tuple(value)
    if not result:
        raise TopNDiagnosticError(f"{label} must be a nonempty sequence")
    return result


def _sample_id(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise TopNDiagnosticError(f"{label} sample_id must be a nonempty string")
    return value


def _index_source(
    value: object,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    rows = _rows(value, "source candidates")
    indexed: list[tuple[str, tuple[str, ...]]] = []
    seen: set[str] = set()
    for item in rows:
        if not isinstance(item, SourceCandidateRow):
            raise TopNDiagnosticError("source candidates must use SourceCandidateRow")
        sample_id = _sample_id(item.sample_id, "source candidate")
        if sample_id in seen:
            raise TopNDiagnosticError(f"duplicate source sample_id {sample_id!r}")
        if isinstance(item.candidate_ids, (str, bytes)) or not isinstance(
            item.candidate_ids, Sequence
        ):
            raise TopNDiagnosticError(
                f"source candidate row {sample_id!r} candidate_ids must be a "
                "non-string sequence"
            )
        candidates = tuple(item.candidate_ids)
        if not candidates:
            raise TopNDiagnosticError(
                f"source candidate row {sample_id!r} has no candidate IDs"
            )
        if any(not isinstance(candidate, str) or not candidate for candidate in candidates):
            raise TopNDiagnosticError(
                f"source candidate row {sample_id!r} has an invalid candidate ID"
            )
        if len(set(candidates)) != len(candidates):
            raise TopNDiagnosticError(
                f"source candidate row {sample_id!r} has duplicate candidate IDs"
            )
        seen.add(sample_id)
        indexed.append((sample_id, candidates))
    return tuple(indexed)


def _index_references(value: object) -> dict[str, str]:
    rows = _rows(value, "reference intents")
    indexed: dict[str, str] = {}
    for item in rows:
        if not isinstance(item, ReferenceIntentRow):
            raise TopNDiagnosticError("reference intents must use ReferenceIntentRow")
        sample_id = _sample_id(item.sample_id, "reference intent")
        if sample_id in indexed:
            raise TopNDiagnosticError(f"duplicate reference sample_id {sample_id!r}")
        if not isinstance(item.intent_id, str) or not item.intent_id:
            raise TopNDiagnosticError(
                f"reference intent for {sample_id!r} must be a nonempty string"
            )
        indexed[sample_id] = item.intent_id
    return indexed


def _index_branch(value: object, branch_name: str) -> dict[str, BranchOutcomeRow]:
    rows = _rows(value, f"branch {branch_name!r} outcomes")
    indexed: dict[str, BranchOutcomeRow] = {}
    for item in rows:
        if not isinstance(item, BranchOutcomeRow):
            raise TopNDiagnosticError(
                f"branch {branch_name!r} outcomes must use BranchOutcomeRow"
            )
        sample_id = _sample_id(item.sample_id, f"branch {branch_name!r} outcome")
        if sample_id in indexed:
            raise TopNDiagnosticError(
                f"branch {branch_name!r} has duplicate sample_id {sample_id!r}"
            )
        if item.final_intent_id is not None and (
            not isinstance(item.final_intent_id, str) or not item.final_intent_id
        ):
            raise TopNDiagnosticError(
                f"branch {branch_name!r} final_intent_id must be nonempty or null"
            )
        if not isinstance(item.refused, bool):
            raise TopNDiagnosticError(
                f"branch {branch_name!r} refused must be boolean"
            )
        if not isinstance(item.missing_final_intent, bool) or (
            item.missing_final_intent
            and (item.refused or item.final_intent_id is not None)
        ):
            raise TopNDiagnosticError(
                f"branch {branch_name!r} missing_final_intent is inconsistent"
            )
        if not item.refused and item.final_intent_id is None and not item.missing_final_intent:
            raise TopNDiagnosticError(
                f"branch {branch_name!r} nonrefused outcome has no final_intent_id"
            )
        if item.entity_correct is not None and not isinstance(item.entity_correct, bool):
            raise TopNDiagnosticError(
                f"branch {branch_name!r} entity_correct must be boolean or null"
            )
        indexed[sample_id] = item
    return indexed


def _check_roster(
    expected: set[str], actual: set[str], label: str
) -> None:
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise TopNDiagnosticError(
            f"{label} roster mismatch (missing={missing!r}, extra={extra!r})"
        )


def _entity_partition(
    final_correct: bool, entity_correct: bool | None
) -> str:
    if entity_correct is None:
        return "unavailable"
    if final_correct and entity_correct:
        return "intent_correct_entity_correct"
    if final_correct:
        return "intent_correct_entity_incorrect"
    if entity_correct:
        return "intent_incorrect_entity_correct"
    return "intent_incorrect_entity_incorrect"


def aggregate_topn_diagnostics(
    source_candidates: Sequence[SourceCandidateRow],
    reference_intents: Sequence[ReferenceIntentRow],
    branch_outcomes: Mapping[str, Sequence[BranchOutcomeRow]],
    *,
    candidate_width: int | None = None,
    allow_variable_width: bool = False,
) -> TopNDiagnosticReport:
    """Aggregate Top-N source and final-branch diagnostics on one exact roster.

    reference_intents are an independent caller supplied reference layer; no
    reference value is ever derived from candidates or branch predictions.
    candidate_width selects the leading ordered IDs to treat as the shortlist.
    When omitted, every source row must have the same width. Explicit
    allow_variable_width treats candidate_width as a maximum and never pads
    or drops candidates; the historical fixed-width contract remains default.
    """

    source_rows = _index_source(source_candidates)
    references = _index_references(reference_intents)
    source_ids = {sample_id for sample_id, _ in source_rows}
    _check_roster(source_ids, set(references), "reference")
    if not isinstance(branch_outcomes, Mapping) or not branch_outcomes:
        raise TopNDiagnosticError("branch_outcomes must be a nonempty mapping")

    branch_rows: dict[str, dict[str, BranchOutcomeRow]] = {}
    for name, value in branch_outcomes.items():
        if not isinstance(name, str) or not name:
            raise TopNDiagnosticError("branch names must be nonempty strings")
        if name in branch_rows:
            raise TopNDiagnosticError(f"duplicate branch name {name!r}")
        rows = _index_branch(value, name)
        _check_roster(source_ids, set(rows), f"branch {name!r}")
        branch_rows[name] = rows

    if not isinstance(allow_variable_width, bool):
        raise TopNDiagnosticError("allow_variable_width must be boolean")
    if allow_variable_width and candidate_width is None:
        raise TopNDiagnosticError("variable width requires an explicit maximum")
    source_widths = {len(candidates) for _, candidates in source_rows}
    if candidate_width is None:
        if len(source_widths) != 1:
            raise TopNDiagnosticError(
                "source candidate rows have inconsistent candidate widths"
            )
        width = source_widths.pop()
    else:
        if (
            isinstance(candidate_width, bool)
            or not isinstance(candidate_width, int)
            or candidate_width < 1
        ):
            raise TopNDiagnosticError("candidate_width must be a positive integer")
        width = candidate_width
        if allow_variable_width and any(len(candidates) > width for _, candidates in source_rows):
            raise TopNDiagnosticError("source row exceeds the registered maximum width")
        if not allow_variable_width and any(len(candidates) < width for _, candidates in source_rows):
            raise TopNDiagnosticError(
                "source candidate row is shorter than candidate_width"
            )

    ordered_names = tuple(sorted(branch_rows))
    source_top1 = 0
    source_topn = 0
    source_missing = 0
    source_present_not_selected = 0
    branch_counts: dict[str, dict[str, int]] = {
        name: {
            "final_intent_correct": 0,
            "refusals": 0,
            "missing_final_intents": 0,
            "out_of_shortlist_attempts": 0,
            "candidate_present": 0,
            "candidate_present_final_correct": 0,
            "candidate_present_final_not_selected": 0,
            "refusal_attempts_with_intent": 0,
            "rescues": 0,
            "harms": 0,
            "unchanged_correct": 0,
            "unchanged_wrong": 0,
            "entity_available": 0,
            "entity_unavailable": 0,
            "intent_correct_entity_correct": 0,
            "intent_correct_entity_incorrect": 0,
            "intent_incorrect_entity_correct": 0,
            "intent_incorrect_entity_incorrect": 0,
        }
        for name in ordered_names
    }
    samples: list[TopNSampleDiagnostic] = []

    for sample_id, candidates in source_rows:
        considered = candidates[:width]
        reference = references[sample_id]
        top1_correct = considered[0] == reference
        topn_included = reference in considered
        missing = not topn_included
        present_not_selected = topn_included and not top1_correct
        source_top1 += int(top1_correct)
        source_topn += int(topn_included)
        source_missing += int(missing)
        source_present_not_selected += int(present_not_selected)
        branch_diagnostics: dict[str, BranchSampleDiagnostic] = {}
        for name in ordered_names:
            outcome = branch_rows[name][sample_id]
            final_correct = (
                not outcome.refused and outcome.final_intent_id == reference
            )
            rescue = not top1_correct and final_correct
            harm = top1_correct and not final_correct
            out_of_shortlist = (
                outcome.final_intent_id is not None
                and outcome.final_intent_id not in considered
            )
            candidate_present = topn_included
            candidate_present_final_correct = candidate_present and final_correct
            candidate_present_final_not_selected = (
                candidate_present and not final_correct
            )
            final_intent_attempt_only = (
                outcome.refused and outcome.final_intent_id is not None
            )
            partition = _entity_partition(final_correct, outcome.entity_correct)
            counts = branch_counts[name]
            counts["final_intent_correct"] += int(final_correct)
            counts["refusals"] += int(outcome.refused)
            counts["missing_final_intents"] += int(outcome.missing_final_intent)
            counts["out_of_shortlist_attempts"] += int(out_of_shortlist)
            counts["candidate_present"] += int(candidate_present)
            counts["candidate_present_final_correct"] += int(
                candidate_present_final_correct
            )
            counts["candidate_present_final_not_selected"] += int(
                candidate_present_final_not_selected
            )
            counts["refusal_attempts_with_intent"] += int(
                final_intent_attempt_only
            )
            counts["rescues"] += int(rescue)
            counts["harms"] += int(harm)
            counts["unchanged_correct"] += int(top1_correct and final_correct)
            counts["unchanged_wrong"] += int(not top1_correct and not final_correct)
            if outcome.entity_correct is None:
                counts["entity_unavailable"] += 1
            else:
                counts["entity_available"] += 1
                counts[partition] += 1
            branch_diagnostics[name] = BranchSampleDiagnostic(
                final_intent_id=outcome.final_intent_id,
                refused=outcome.refused,
                missing_final_intent=outcome.missing_final_intent,
                final_intent_correct=final_correct,
                rescue=rescue,
                harm=harm,
                out_of_shortlist=out_of_shortlist,
                candidate_present=candidate_present,
                candidate_present_final_correct=candidate_present_final_correct,
                candidate_present_final_not_selected=(
                    candidate_present_final_not_selected
                ),
                final_intent_attempt_only=final_intent_attempt_only,
                entity_correct=outcome.entity_correct,
                entity_partition=partition,
            )
        samples.append(
            TopNSampleDiagnostic(
                sample_id=sample_id,
                candidate_ids=considered,
                reference_intent_id=reference,
                top1_correct=top1_correct,
                topn_included=topn_included,
                missing_true_candidate=missing,
                present_not_selected=present_not_selected,
                branches=branch_diagnostics,
            )
        )

    summaries = {
        name: BranchDiagnosticSummary(
            sample_count=len(source_rows),
            **counts,
        )
        for name, counts in branch_counts.items()
    }
    return TopNDiagnosticReport(
        candidate_width=width,
        source=SourceCandidateSummary(
            sample_count=len(source_rows),
            top1_correct=source_top1,
            topn_included=source_topn,
            missing_true_candidate=source_missing,
            present_not_selected=source_present_not_selected,
        ),
        branches=summaries,
        per_sample=tuple(samples),
    )


__all__ = [
    "BranchDiagnosticSummary",
    "BranchOutcomeRow",
    "BranchSampleDiagnostic",
    "ReferenceIntentRow",
    "SourceCandidateRow",
    "SourceCandidateSummary",
    "TopNDiagnosticError",
    "TopNDiagnosticReport",
    "TopNSampleDiagnostic",
    "aggregate_topn_diagnostics",
]
