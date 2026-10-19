"""Deterministic MERGE policies for a Perception branch's k sampled notes.

Decision 338 (2026-10-19), lever L2: a ``native_episode.roles.perception.
sampling_variants`` branch that declares ``perception_samples`` makes k
Perception contacts over the same packet (sample 0 greedy, samples 1..k-1 at the
arm's sampling parameters) and merges the k candidate lists into the ONE
shortlist its branch Solver contact reads. Design:
``docs/superpowers/specs/2026-10-19-slurp-338-lever-column-design.md`` section 3.

This module is the canonical registration site for
``core.base.PERCEPTION_MERGE_POLICIES``, mirroring ``rails.commit_policies``
for ``COMMIT_POLICIES``: the registry lives in ``core.base``, the concrete entry
lives beside its implementation, and a caller resolves the registered id
through a function-local deferred import.

Every policy here is a pure function of its inputs: no model, tool or network
contact, no randomness; the same input always produces the same
:class:`MergeOutcome`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..core.base import PERCEPTION_MERGE_POLICIES

#: The one policy this module registers. A ``perception_samples.merge_policy``
#: value resolves to this id in ``core.base.PERCEPTION_MERGE_POLICIES``.
CANDIDATE_UNION_V1 = "saea-perception-candidate-union-v1"


class MergePolicyError(ValueError):
    """A merge policy refuses malformed note lists or parameters."""


@dataclass(frozen=True)
class MergeOutcome:
    """The merged shortlist plus the custody a receipt keeps."""

    policy_id: str
    merged_candidate_ids: tuple[str, ...]
    #: Candidates appended after sample 0's own list, in appended order.
    appended_candidate_ids: tuple[str, ...]
    #: ``(intent_id, samples listing it)`` for EVERY candidate any sample listed,
    #: in the order the union ranks them (sample 0's list first, then by support
    #: desc, best rank asc, intent id asc).
    support_counts: tuple[tuple[str, int], ...]
    #: ``(intent_id, best 1-based rank over the samples listing it)``, same order.
    best_ranks: tuple[tuple[str, int], ...]
    cap: int
    #: Samples that carried a usable (non-None) list.
    usable_samples: int
    #: True when the cap cut at least one ranked candidate.
    truncated: bool


def _check_lists(note_lists: Sequence[Sequence[str] | None]) -> list[tuple[str, ...] | None]:
    if (
        not isinstance(note_lists, Sequence) or isinstance(note_lists, (str, bytes))
        or not note_lists
    ):
        raise MergePolicyError("a merge policy requires a nonempty ordered sequence of note lists")
    out: list[tuple[str, ...] | None] = []
    for position, entry in enumerate(note_lists):
        if entry is None:
            out.append(None)
            continue
        if (
            not isinstance(entry, Sequence) or isinstance(entry, (str, bytes))
            or any(not isinstance(value, str) or not value for value in entry)
        ):
            raise MergePolicyError(
                f"note list {position} must be None or an ordered sequence of non-empty strings"
            )
        out.append(tuple(dict.fromkeys(entry)))     # first occurrence kept, as the note parser does
    return out


def merge_candidate_union_v1(
    note_lists: Sequence[Sequence[str] | None], *, cap: int,
) -> MergeOutcome:
    """Ordered union of k notes' candidate lists, truncated to ``cap``.

    1. Sample 0's list comes first, verbatim (rank 1 is never displaced).
    2. Every candidate sample 0 lacks follows, ordered by the number of samples
       listing it (descending), then its best 1-based rank over the samples
       (ascending), then its intent id (ascending).
    3. The result is truncated to ``cap`` (the Solver's own
       ``candidate_supply.max_candidates``).

    A ``None`` list (a sample whose note was malformed or absent) casts no vote.
    When sample 0 is unusable the union is ordered by rules 2 and 3 alone.
    """

    if isinstance(cap, bool) or not isinstance(cap, int) or cap < 1:
        raise MergePolicyError("cap must be a positive integer")
    lists = _check_lists(note_lists)
    support: dict[str, int] = {}
    best: dict[str, int] = {}
    for entry in lists:
        if entry is None:
            continue
        for rank, intent_id in enumerate(entry, start=1):
            support[intent_id] = support.get(intent_id, 0) + 1
            best[intent_id] = min(best.get(intent_id, rank), rank)
    first = lists[0] if lists[0] is not None else ()
    rest = sorted(
        (intent_id for intent_id in support if intent_id not in first),
        key=lambda intent_id: (-support[intent_id], best[intent_id], intent_id),
    )
    ranked = [*first, *rest]
    merged = tuple(ranked[:cap])
    appended = tuple(intent_id for intent_id in merged if intent_id not in first)
    return MergeOutcome(
        policy_id=CANDIDATE_UNION_V1,
        merged_candidate_ids=merged,
        appended_candidate_ids=appended,
        support_counts=tuple((intent_id, support[intent_id]) for intent_id in ranked),
        best_ranks=tuple((intent_id, best[intent_id]) for intent_id in ranked),
        cap=cap,
        usable_samples=sum(1 for entry in lists if entry is not None),
        truncated=len(ranked) > cap,
    )


PERCEPTION_MERGE_POLICIES.register(CANDIDATE_UNION_V1, merge_candidate_union_v1)


__all__ = [
    "CANDIDATE_UNION_V1",
    "MergeOutcome",
    "MergePolicyError",
    "merge_candidate_union_v1",
]
