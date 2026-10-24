"""Deterministic COMMIT policies for the SLURP v2 base program's grouped Solver.

E2 (2026-09-16, ``docs/superpowers/specs/2026-09-16-slurp-v2-base-program-
design.md`` section 4, item M2): the native Solver phase may be sampled N
times per request (temperature > 0, distinct pinned seeds); a registered,
deterministic COMMIT policy aggregates the N raw structured SLURP answers
into the ONE delivered answer, while every raw response stays in custody
elsewhere (``rails.native_group_solver``).

This module is the canonical registration site for
``core.base.COMMIT_POLICIES``, mirroring ``core/policies.py``'s own
registration convention for ``JUDGES`` / ``MAX_TOKENS_POLICIES`` / etc: the
registry lives in ``core.base``, the concrete entries live beside their
implementation, and a caller resolves the registered id through a
function-local deferred import (see
``rails.native_episode_config.NativeEpisodeRole.__post_init__``).

Every policy here is a pure function of its votes and parameters: no model,
tool or network contact, no randomness, and the same input always produces
the same :class:`CommitOutcome`.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from ..core.base import COMMIT_POLICIES
from ..reproduction.slurp_scoring import SlotEntity
from ..scoring.normalize import normalize_text_v1

#: The one policy this module registers (E2/M2). A ``native_episode.roles.
#: solver.commit.policy`` value resolves to this id in ``core.base.
#: COMMIT_POLICIES``.
PLURALITY_SUPPORT_V1 = "saea-commit-plurality-support-v1"


class CommitPolicyError(ValueError):
    """A commit policy refuses malformed votes or parameters."""


@dataclass(frozen=True)
class ParsedSlurpAnswer:
    """One structured SLURP answer: the shape ``reproduction.slurp_scoring.
    parse_slu_response`` returns and ``reproduction.slurp_delivery`` renders,
    carried as an immutable value so a commit policy can compare and combine
    samples without re-parsing raw text."""

    scenario: str
    action: str
    entities: tuple[SlotEntity, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, str) or not isinstance(self.action, str):
            raise CommitPolicyError(
                "a parsed SLURP answer requires string scenario and action"
            )
        if not isinstance(self.entities, tuple) or any(
            not isinstance(entity, SlotEntity) for entity in self.entities
        ):
            raise CommitPolicyError(
                "a parsed SLURP answer requires a tuple of SlotEntity"
            )

    @property
    def intent_id(self) -> tuple[str, str]:
        return (self.scenario, self.action)


@dataclass(frozen=True)
class SolverSampleVote:
    """One raw Solver sample of a grouped visit: its position in the group
    and its parsed answer, or ``None`` when the sample's raw text failed to
    parse. A malformed sample casts no vote in either race but stays visible
    to the caller for custody (``rails.native_group_solver`` records its
    parse status regardless of this policy's outcome)."""

    sample_index: int
    parsed: ParsedSlurpAnswer | None

    def __post_init__(self) -> None:
        if (
            isinstance(self.sample_index, bool)
            or not isinstance(self.sample_index, int)
            or self.sample_index < 0
        ):
            raise CommitPolicyError(
                "a solver sample vote requires a nonnegative sample_index"
            )
        if self.parsed is not None and not isinstance(self.parsed, ParsedSlurpAnswer):
            raise CommitPolicyError(
                "a solver sample vote's parsed answer must be a ParsedSlurpAnswer or None"
            )


@dataclass(frozen=True)
class EntityCommitOutcome:
    """One delivered entity plus the clustering custody behind it."""

    type: str
    filler: str
    support: int
    member_sample_indices: tuple[int, ...]
    tie_break_sample_index: int | None


@dataclass(frozen=True)
class CommitOutcome:
    """The ONE delivered SLURP answer plus the custody a receipt keeps."""

    policy_id: str
    answer: ParsedSlurpAnswer
    intent_support: int
    intent_member_sample_indices: tuple[int, ...]
    intent_tie_break_sample_index: int | None
    entities: tuple[EntityCommitOutcome, ...]
    #: Gate custody of a gated policy (decision 338); None for an ungated one.
    gate: dict[str, object] | None = None


def character_level_f1(a: str, b: str) -> float:
    """Bag-of-characters F1 between two strings.

    No dedicated character-level F1 helper exists in ``scoring/`` today:
    ``scoring.entity.score_entities`` scores whole normalized strings by
    multiset membership (entity-level, not character-level), and
    ``reproduction.slurp_scoring._char_distance`` is a normalized EDIT
    distance, not an F1. This is the small pure fallback function the E2
    spec names. It reuses ``scoring.normalize.normalize_text_v1`` for the
    normalisation half of that instruction (callers normalize before
    calling this).

    Symmetric: swapping ``a``/``b`` only swaps which side plays precision
    and which plays recall, and F1 is symmetric in precision and recall.
    Two empty strings are identical (1.0); one empty and one nonempty share
    no characters (0.0).
    """

    if not isinstance(a, str) or not isinstance(b, str):
        raise CommitPolicyError("character_level_f1 requires two strings")
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    counts_a, counts_b = Counter(a), Counter(b)
    overlap = sum((counts_a & counts_b).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(b)
    recall = overlap / len(a)
    return 2.0 * precision * recall / (precision + recall)


def _valid_votes(votes: Sequence[SolverSampleVote]) -> list[SolverSampleVote]:
    if not isinstance(votes, Sequence) or isinstance(votes, (str, bytes)) or not votes:
        raise CommitPolicyError(
            "a commit policy requires a nonempty ordered vote sequence"
        )
    if not all(isinstance(vote, SolverSampleVote) for vote in votes):
        raise CommitPolicyError("every vote must be a SolverSampleVote")
    indices = [vote.sample_index for vote in votes]
    if indices != sorted(indices) or len(set(indices)) != len(indices):
        raise CommitPolicyError(
            "votes must be ordered by distinct ascending sample_index"
        )
    return [vote for vote in votes if vote.parsed is not None]


def _plurality_intent(
    valid: Sequence[SolverSampleVote],
) -> tuple[tuple[str, str] | None, int, tuple[int, ...], int | None]:
    """Plurality over ``(scenario, action)``.

    Tie -> the lowest first-occurrence sample_index among the tied intents
    (the E2 spec's own tie-break rule, applied to greedy/sample_index 0
    first since callers order votes with sample_index ascending). Returns
    ``(intent, support, member_sample_indices, tie_break_sample_index)``;
    the tie-break field is ``None`` unless the winning count was actually
    shared by more than one intent.
    """

    counts: dict[tuple[str, str], int] = {}
    first_seen: dict[tuple[str, str], int] = {}
    members: dict[tuple[str, str], list[int]] = {}
    for vote in valid:
        intent = vote.parsed.intent_id
        counts[intent] = counts.get(intent, 0) + 1
        members.setdefault(intent, []).append(vote.sample_index)
        if intent not in first_seen:
            first_seen[intent] = vote.sample_index
    if not counts:
        return None, 0, (), None
    best_count = max(counts.values())
    tied = [intent for intent, count in counts.items() if count == best_count]
    winner = min(tied, key=lambda candidate: first_seen[candidate])
    tie_break = first_seen[winner] if len(tied) > 1 else None
    return winner, best_count, tuple(members[winner]), tie_break


def _cluster_entities(
    valid: Sequence[SolverSampleVote], entity_type: str, *, similarity_threshold: float,
) -> tuple[list[tuple[int, str, str]], dict[int, list[int]]]:
    """Connected components of the same-type mention graph.

    A mention is one ``(sample_index, filler)`` pair of type ``entity_type``
    from a valid (parsed) vote. An edge joins two mentions when the
    character-level F1 of their normalized fillers is
    ``>= similarity_threshold``. Connected components are deterministic
    given a fixed similarity function and a fixed mention order -- unlike a
    greedy single-linkage assignment, the result does not depend on which
    mention is visited first.
    """

    mentions: list[tuple[int, str, str]] = []
    for vote in valid:
        for entity in vote.parsed.entities:
            if entity.type == entity_type:
                mentions.append(
                    (vote.sample_index, entity.filler, normalize_text_v1(entity.filler))
                )
    parent = list(range(len(mentions)))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: int, right: int) -> None:
        root_left, root_right = find(left), find(right)
        if root_left != root_right:
            parent[max(root_left, root_right)] = min(root_left, root_right)

    for i in range(len(mentions)):
        for j in range(i + 1, len(mentions)):
            if character_level_f1(mentions[i][2], mentions[j][2]) >= similarity_threshold:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(len(mentions)):
        clusters.setdefault(find(i), []).append(i)
    return mentions, clusters


def _select_medoid(
    mentions: Sequence[tuple[int, str, str]], cluster: Sequence[int],
) -> tuple[str, int | None]:
    """The cluster member with the highest mean similarity to the other
    members; tie -> lowest sample_index. Returns ``(filler, tie_break)``."""

    if len(cluster) == 1:
        return mentions[cluster[0]][1], None
    scores = {}
    for i in cluster:
        total = sum(
            character_level_f1(mentions[i][2], mentions[j][2])
            for j in cluster
            if j != i
        )
        scores[i] = total / (len(cluster) - 1)
    best = max(scores.values())
    tied = sorted((i for i in cluster if scores[i] == best), key=lambda i: mentions[i][0])
    chosen = tied[0]
    tie_break = mentions[chosen][0] if len(tied) > 1 else None
    return mentions[chosen][1], tie_break


def commit_plurality_support_v1(
    votes: Sequence[SolverSampleVote],
    *,
    min_support: int,
    similarity_threshold: float,
) -> CommitOutcome:
    """Aggregate N Solver samples into one delivered SLURP answer.

    Intent: plurality over ``(scenario, action)`` among the parsed
    (non-malformed) votes, tie -> lowest first-occurrence sample_index.

    Entities: same-TYPE fillers are clustered across every valid sample by
    normalized character-level F1 (``>= similarity_threshold``); a cluster
    is kept only when its support (member count) is ``>= min_support``, and
    each kept cluster emits its medoid filler (the member with the highest
    mean similarity to the rest of the cluster, tie -> lowest sample_index).

    Malformed samples (``vote.parsed is None``) cast no vote in either race.
    If every sample is malformed the policy fails closed to an empty answer
    with zero support rather than raising -- the caller (``rails.
    native_group_solver``) records that every sample was malformed.
    """

    if (
        isinstance(min_support, bool)
        or not isinstance(min_support, int)
        or min_support < 1
    ):
        raise CommitPolicyError("min_support must be a positive integer")
    if (
        isinstance(similarity_threshold, bool)
        or not isinstance(similarity_threshold, (int, float))
        or not 0 < similarity_threshold <= 1
    ):
        raise CommitPolicyError("similarity_threshold must be in (0, 1]")
    valid = _valid_votes(votes)
    if not valid:
        return CommitOutcome(
            policy_id=PLURALITY_SUPPORT_V1,
            answer=ParsedSlurpAnswer(scenario="", action="", entities=()),
            intent_support=0,
            intent_member_sample_indices=(),
            intent_tie_break_sample_index=None,
            entities=(),
        )
    intent, support, member_indices, tie_break = _plurality_intent(valid)
    scenario, action = intent
    entity_types = sorted({entity.type for vote in valid for entity in vote.parsed.entities})
    delivered: list[EntityCommitOutcome] = []
    for entity_type in entity_types:
        mentions, clusters = _cluster_entities(
            valid, entity_type, similarity_threshold=similarity_threshold
        )
        ordered_clusters = sorted(
            clusters.values(), key=lambda members: min(mentions[i][0] for i in members)
        )
        for members in ordered_clusters:
            if len(members) < min_support:
                continue
            filler, entity_tie_break = _select_medoid(mentions, members)
            delivered.append(
                EntityCommitOutcome(
                    type=entity_type,
                    filler=filler,
                    support=len(members),
                    member_sample_indices=tuple(sorted(mentions[i][0] for i in members)),
                    tie_break_sample_index=entity_tie_break,
                )
            )
    return CommitOutcome(
        policy_id=PLURALITY_SUPPORT_V1,
        answer=ParsedSlurpAnswer(
            scenario=scenario,
            action=action,
            entities=tuple(SlotEntity(type=e.type, filler=e.filler) for e in delivered),
        ),
        intent_support=support,
        intent_member_sample_indices=member_indices,
        intent_tie_break_sample_index=tie_break,
        entities=tuple(delivered),
    )


COMMIT_POLICIES.register(PLURALITY_SUPPORT_V1, commit_plurality_support_v1)


FIRST_SUPPORT_V1 = "saea-commit-first-support-v1"


def commit_first_support_v1(
    votes: Sequence[SolverSampleVote],
    *,
    min_support: int,
    similarity_threshold: float,
    n1: float | None = None,
    n1_min: float | None = None,
    empty_votes_min: int | None = None,
) -> CommitOutcome:
    """First-first support filter with an optional N1-gated empty decision.

    Decision 338, lever L1. The base answer is the lowest-index VALID sample
    (sample 0 when it parsed): its labels (scenario, action) are kept verbatim,
    so intent never moves, and its entities are kept in order iff at least
    ``min_support`` valid samples (the base counts) carry a same-type entity
    whose normalised filler has character-level F1 >= ``similarity_threshold``
    (the aggregation read's ``support_of_entity`` rule).

    Optional gate (``n1_min`` and ``empty_votes_min`` given together): when
    ``n1 >= n1_min`` AND at least ``empty_votes_min`` of the valid samples
    OTHER than the base answered no entity, the delivered entity list is empty
    (the NX R6 ``c3verdict x N1`` rule, samples as verdict). A malformed sample
    casts no empty vote. ``n1`` is the entity-free share of the supplied
    exemplars; when the gate is configured but ``n1`` is None the gate does not
    fire and the outcome's ``gate`` records ``n1-unavailable``.
    """

    if isinstance(min_support, bool) or not isinstance(min_support, int) or min_support < 1:
        raise CommitPolicyError("min_support must be a positive integer")
    if (
        isinstance(similarity_threshold, bool)
        or not isinstance(similarity_threshold, (int, float))
        or not 0 < similarity_threshold <= 1
    ):
        raise CommitPolicyError("similarity_threshold must be in (0, 1]")
    gated = n1_min is not None or empty_votes_min is not None
    if gated:
        if (
            isinstance(n1_min, bool) or not isinstance(n1_min, (int, float)) or not 0 <= n1_min <= 1
            or isinstance(empty_votes_min, bool) or not isinstance(empty_votes_min, int)
            or empty_votes_min < 1
        ):
            raise CommitPolicyError(
                "the gate needs n1_min in [0, 1] and a positive integer empty_votes_min together"
            )
    if n1 is not None and (isinstance(n1, bool) or not isinstance(n1, (int, float)) or not 0 <= n1 <= 1):
        raise CommitPolicyError("n1 must be in [0, 1]")
    valid = _valid_votes(votes)
    if not valid:
        return CommitOutcome(
            policy_id=FIRST_SUPPORT_V1,
            answer=ParsedSlurpAnswer(scenario="", action="", entities=()),
            intent_support=0, intent_member_sample_indices=(),
            intent_tie_break_sample_index=None, entities=(),
            gate={"configured": gated, "status": "all-malformed"} if gated else None,
        )
    base = valid[0]
    target = base.parsed
    kept: list[EntityCommitOutcome] = []
    for entity in target.entities:
        normal = normalize_text_v1(entity.filler)
        members = []
        for vote in valid:
            if any(
                other.type == entity.type
                and character_level_f1(normal, normalize_text_v1(other.filler)) >= similarity_threshold
                for other in vote.parsed.entities
            ):
                members.append(vote.sample_index)
        if len(members) >= min_support:
            kept.append(EntityCommitOutcome(
                type=entity.type, filler=entity.filler, support=len(members),
                member_sample_indices=tuple(members), tie_break_sample_index=None,
            ))
    gate: dict[str, object] | None = None
    if gated:
        others = [vote for vote in valid if vote is not base]
        empty_votes = sum(1 for vote in others if not vote.parsed.entities)
        if n1 is None:
            status, fired = "n1-unavailable", False
        else:
            fired = n1 >= n1_min and empty_votes >= empty_votes_min
            status = "fired" if fired else "not-fired"
        gate = {
            "configured": True, "status": status, "n1": n1, "n1_min": n1_min,
            "empty_votes": empty_votes, "empty_votes_min": empty_votes_min,
        }
        if fired:
            kept = []
    return CommitOutcome(
        policy_id=FIRST_SUPPORT_V1,
        answer=ParsedSlurpAnswer(
            scenario=target.scenario, action=target.action,
            entities=tuple(SlotEntity(type=e.type, filler=e.filler) for e in kept),
        ),
        intent_support=1, intent_member_sample_indices=(base.sample_index,),
        intent_tie_break_sample_index=None, entities=tuple(kept), gate=gate,
    )


COMMIT_POLICIES.register(FIRST_SUPPORT_V1, commit_first_support_v1)


__all__ = [
    "FIRST_SUPPORT_V1",
    "PLURALITY_SUPPORT_V1",
    "CommitOutcome",
    "CommitPolicyError",
    "EntityCommitOutcome",
    "ParsedSlurpAnswer",
    "SolverSampleVote",
    "character_level_f1",
    "commit_first_support_v1",
    "commit_plurality_support_v1",
]
