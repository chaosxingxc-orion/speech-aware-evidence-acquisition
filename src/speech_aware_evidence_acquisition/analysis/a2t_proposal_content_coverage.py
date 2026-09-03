"""Pure post-seal proposal-content coverage for ordered Audio2Tool calls.

The caller supplies both the already-sealed, occurrence-preserving proposal
pools and the post-seal gold calls.  This module performs no file access,
network access, model contact, scorer contact, or gold loading.  Its result is
only a content-coverage diagnostic; it does not establish that any runtime or
model can consume, select, or reach the covered proposal content.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Mapping, Sequence


RESULT_SCHEMA = "saea-a2t-postseal-proposal-content-coverage-v1"
SCOPE_NOTE = (
    "This audit establishes occurrence-preserving proposal-content coverage only; "
    "it does not establish model-consumable reachability or achievable task accuracy."
)


class ProposalContentCoverageError(ValueError):
    """A sealed-pool, occurrence, family-order, or call invariant failed."""


@dataclass(frozen=True)
class ProposalOccurrence:
    """One call occurrence retained from one response in a proposal family."""

    occurrence_id: str
    response_index: int
    occurrence_index: int
    call: Mapping[str, object]


@dataclass(frozen=True)
class SealedProposalPool:
    """One occurrence-preserving proposal pool whose collection phase is sealed."""

    family_id: str
    sealed: bool
    occurrences: Sequence[ProposalOccurrence]


@dataclass(frozen=True)
class ProposalContentCoverage:
    """Coverage diagnostics and a candidate copied only from sealed occurrences."""

    chosen_occurrence_ids: tuple[str, ...]
    chosen_gold_indexes: tuple[int, ...]
    exact_call_coverage: bool
    correct_tool_coverage: bool
    canonical_output_json: str
    gold_call_count: int
    exact_call_count: int
    correct_tool_call_count: int
    missing_exact_gold_indexes: tuple[int, ...]
    missing_tool_gold_indexes: tuple[int, ...]
    schema: str = RESULT_SCHEMA
    runtime_or_model_consumability_claimed: bool = False
    scope_note: str = SCOPE_NOTE

    def as_json(self) -> dict[str, object]:
        """Return a JSON-compatible diagnostic record."""

        return {
            "schema": self.schema,
            "scope_note": self.scope_note,
            "runtime_or_model_consumability_claimed": (
                self.runtime_or_model_consumability_claimed
            ),
            "gold_call_count": self.gold_call_count,
            "exact_call_count": self.exact_call_count,
            "correct_tool_call_count": self.correct_tool_call_count,
            "exact_call_coverage": self.exact_call_coverage,
            "correct_tool_coverage": self.correct_tool_coverage,
            "chosen_occurrence_ids": list(self.chosen_occurrence_ids),
            "chosen_gold_indexes": list(self.chosen_gold_indexes),
            "missing_exact_gold_indexes": list(self.missing_exact_gold_indexes),
            "missing_tool_gold_indexes": list(self.missing_tool_gold_indexes),
            "canonical_output_json": self.canonical_output_json,
        }


@dataclass(frozen=True)
class _RankedOccurrence:
    family_rank: int
    family_id: str
    occurrence: ProposalOccurrence

    @property
    def sort_key(self) -> tuple[int, int, int]:
        return (
            self.family_rank,
            self.occurrence.response_index,
            self.occurrence.occurrence_index,
        )


def _validate_json_value(value: object, label: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if type(value) is int:
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ProposalContentCoverageError(
                f"{label} contains a non-finite JSON number"
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{label}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ProposalContentCoverageError(
                    f"{label} contains a non-text JSON object key"
                )
            _validate_json_value(item, f"{label}.{key}")
        return
    raise ProposalContentCoverageError(
        f"{label} contains a value outside the JSON type system"
    )


def _validate_call(call: object, label: str) -> Mapping[str, object]:
    if not isinstance(call, Mapping) or set(call) != {"name", "arguments"}:
        raise ProposalContentCoverageError(
            f"{label} must be an object with exact keys name and arguments"
        )
    name = call["name"]
    arguments = call["arguments"]
    if not isinstance(name, str) or not name:
        raise ProposalContentCoverageError(f"{label}.name must be non-empty text")
    if not isinstance(arguments, Mapping):
        raise ProposalContentCoverageError(f"{label}.arguments must be a JSON object")
    _validate_json_value(arguments, f"{label}.arguments")
    return call


def _json_identity(value: object) -> object:
    """Represent JSON identity without Python's bool/int/float coercions."""

    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("boolean", value)
    if type(value) is int:
        return ("integer", value)
    if type(value) is float:
        return ("number", value.hex())
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(_json_identity(item) for item in value))
    if isinstance(value, Mapping):
        return (
            "object",
            tuple(sorted((key, _json_identity(item)) for key, item in value.items())),
        )
    raise AssertionError("JSON values are validated before identity construction")


def _call_identity(call: Mapping[str, object]) -> object:
    return (
        call["name"],
        _json_identity(call["arguments"]),
    )


def _json_copy(value: object) -> object:
    """Copy a validated JSON value while preserving its types and key order."""

    if isinstance(value, Mapping):
        return {key: _json_copy(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_copy(item) for item in value]
    return value


def _family_ranks(frozen_family_order: Sequence[str]) -> Mapping[str, int]:
    if isinstance(frozen_family_order, (str, bytes)):
        raise ProposalContentCoverageError(
            "frozen family order must be a non-empty sequence of unique family ids"
        )
    order = tuple(frozen_family_order)
    if (
        not order
        or any(not isinstance(family_id, str) or not family_id for family_id in order)
        or len(set(order)) != len(order)
    ):
        raise ProposalContentCoverageError(
            "frozen family order must be a non-empty sequence of unique family ids"
        )
    return {family_id: index for index, family_id in enumerate(order)}


def _ordered_occurrences(
    sealed_pools: Sequence[SealedProposalPool],
    family_ranks: Mapping[str, int],
) -> tuple[_RankedOccurrence, ...]:
    if isinstance(sealed_pools, (str, bytes)):
        raise ProposalContentCoverageError("sealed pools must be a sequence")
    ranked: list[_RankedOccurrence] = []
    occurrence_ids: set[str] = set()
    coordinates: set[tuple[str, int, int]] = set()
    pool_families: set[str] = set()
    for pool_index, pool in enumerate(sealed_pools):
        if not isinstance(pool, SealedProposalPool):
            raise ProposalContentCoverageError(
                f"sealed_pools[{pool_index}] must be a SealedProposalPool"
            )
        if not isinstance(pool.family_id, str) or not pool.family_id:
            raise ProposalContentCoverageError(
                f"sealed_pools[{pool_index}] has a malformed family id"
            )
        if pool.family_id in pool_families:
            raise ProposalContentCoverageError(
                f"sealed pools repeat family {pool.family_id!r}"
            )
        pool_families.add(pool.family_id)
        if pool.family_id not in family_ranks:
            raise ProposalContentCoverageError(
                f"sealed pool has unknown family {pool.family_id!r} in frozen family order"
            )
        if pool.sealed is not True:
            raise ProposalContentCoverageError(
                f"proposal pool {pool.family_id!r} is not sealed"
            )
        if isinstance(pool.occurrences, (str, bytes)):
            raise ProposalContentCoverageError(
                f"proposal pool {pool.family_id!r} occurrences must be a sequence"
            )
        for item_index, occurrence in enumerate(pool.occurrences):
            if not isinstance(occurrence, ProposalOccurrence):
                raise ProposalContentCoverageError(
                    f"proposal pool {pool.family_id!r} occurrence {item_index} is malformed"
                )
            if (
                not isinstance(occurrence.occurrence_id, str)
                or not occurrence.occurrence_id
            ):
                raise ProposalContentCoverageError(
                    "occurrence id must be non-empty text"
                )
            if occurrence.occurrence_id in occurrence_ids:
                raise ProposalContentCoverageError(
                    f"duplicate occurrence id {occurrence.occurrence_id!r}"
                )
            occurrence_ids.add(occurrence.occurrence_id)
            if (
                type(occurrence.response_index) is not int
                or occurrence.response_index < 0
                or type(occurrence.occurrence_index) is not int
                or occurrence.occurrence_index < 0
            ):
                raise ProposalContentCoverageError(
                    f"occurrence {occurrence.occurrence_id!r} indexes must be non-negative integers"
                )
            coordinate = (
                pool.family_id,
                occurrence.response_index,
                occurrence.occurrence_index,
            )
            if coordinate in coordinates:
                raise ProposalContentCoverageError(
                    f"proposal pool {pool.family_id!r} has duplicate occurrence coordinates"
                )
            coordinates.add(coordinate)
            _validate_call(
                occurrence.call,
                f"occurrence {occurrence.occurrence_id!r} call",
            )
            ranked.append(
                _RankedOccurrence(
                    family_rank=family_ranks[pool.family_id],
                    family_id=pool.family_id,
                    occurrence=occurrence,
                )
            )
    return tuple(sorted(ranked, key=lambda item: item.sort_key))


def audit_proposal_content_coverage(
    *,
    sealed_pools: Sequence[SealedProposalPool],
    gold_calls: Sequence[Mapping[str, object]],
    frozen_family_order: Sequence[str],
) -> ProposalContentCoverage:
    """Audit whether sealed proposal occurrences cover an ordered gold call list.

    Exact coverage requires one distinct occurrence per gold position with the
    same exact tool name, argument keys, JSON value types, and JSON values.
    Duplicate calls therefore require duplicate proposal occurrences.  Chosen
    occurrences are emitted in gold order; ties between identical occurrences
    use frozen family order, then response index, then occurrence index.

    The first pass reserves all exact matches.  A second pass fills still-open
    positions with unused same-tool occurrences, producing a deterministic
    correct-tool diagnostic without editing any proposal call.  Missing
    positions are omitted rather than invented.
    """

    family_ranks = _family_ranks(frozen_family_order)
    occurrences = _ordered_occurrences(sealed_pools, family_ranks)
    if isinstance(gold_calls, (str, bytes)):
        raise ProposalContentCoverageError("gold_calls must be a sequence")
    gold = tuple(
        _validate_call(call, f"gold_calls[{index}]")
        for index, call in enumerate(gold_calls)
    )

    chosen: list[_RankedOccurrence | None] = [None] * len(gold)
    unused = set(range(len(occurrences)))
    missing_exact: list[int] = []
    for gold_index, gold_call in enumerate(gold):
        identity = _call_identity(gold_call)
        match_index = next(
            (
                index
                for index in range(len(occurrences))
                if index in unused
                and _call_identity(occurrences[index].occurrence.call) == identity
            ),
            None,
        )
        if match_index is None:
            missing_exact.append(gold_index)
            continue
        chosen[gold_index] = occurrences[match_index]
        unused.remove(match_index)

    missing_tool: list[int] = []
    for gold_index in missing_exact:
        gold_name = gold[gold_index]["name"]
        match_index = next(
            (
                index
                for index in range(len(occurrences))
                if index in unused
                and occurrences[index].occurrence.call["name"] == gold_name
            ),
            None,
        )
        if match_index is None:
            missing_tool.append(gold_index)
            continue
        chosen[gold_index] = occurrences[match_index]
        unused.remove(match_index)

    chosen_pairs = tuple(
        (gold_index, item) for gold_index, item in enumerate(chosen) if item is not None
    )
    chosen_calls = [
        _json_copy(item.occurrence.call) for _gold_index, item in chosen_pairs
    ]
    return ProposalContentCoverage(
        chosen_occurrence_ids=tuple(
            item.occurrence.occurrence_id for _gold_index, item in chosen_pairs
        ),
        chosen_gold_indexes=tuple(gold_index for gold_index, _item in chosen_pairs),
        exact_call_coverage=not missing_exact,
        correct_tool_coverage=not missing_tool,
        canonical_output_json=json.dumps(
            chosen_calls,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        gold_call_count=len(gold),
        exact_call_count=len(gold) - len(missing_exact),
        correct_tool_call_count=len(gold) - len(missing_tool),
        missing_exact_gold_indexes=tuple(missing_exact),
        missing_tool_gold_indexes=tuple(missing_tool),
    )


__all__ = [
    "ProposalContentCoverage",
    "ProposalContentCoverageError",
    "ProposalOccurrence",
    "RESULT_SCHEMA",
    "SCOPE_NOTE",
    "SealedProposalPool",
    "audit_proposal_content_coverage",
]
