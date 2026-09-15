"""Descriptive alignment of expected tool occurrences to candidate actions.

This module performs no source reads. It preserves repeated reference
occurrences and treats each observed action as capacity for at most one
reference occurrence. The returned loss terms describe set, capacity, order,
and position differences; they do not assign a causal mechanism.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping, Sequence


class CandidateActionAlignmentError(ValueError):
    """The expected occurrences or candidate action state is malformed."""


def _ordered_sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise CandidateActionAlignmentError(f"{label} must be an ordered sequence")
    return value


def _tool_name(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or not value.isascii()
    ):
        raise CandidateActionAlignmentError(
            f"{label} must contain nonempty trimmed ASCII tool names"
        )
    return value


def _expected_occurrences(values: object) -> tuple[str, ...]:
    sequence = _ordered_sequence(values, "expected tool names")
    return tuple(_tool_name(value, "expected tool names") for value in sequence)


def _candidate_actions(values: object) -> tuple[frozenset[str], ...] | None:
    if values is None:
        return None
    sequence = _ordered_sequence(values, "candidate actions")
    actions: list[frozenset[str]] = []
    for raw_action in sequence:
        if (
            isinstance(raw_action, (str, bytes, Mapping))
            or not isinstance(raw_action, Collection)
        ):
            raise CandidateActionAlignmentError(
                "candidate actions must contain candidate-name collections"
            )
        names = tuple(
            _tool_name(value, "candidate tool names") for value in raw_action
        )
        if len(names) != len(set(names)):
            raise CandidateActionAlignmentError(
                "candidate actions must contain unique tool names"
            )
        actions.append(frozenset(names))
    return tuple(actions)


def _maximum_unordered_matching(
    expected: tuple[str, ...], actions: tuple[frozenset[str], ...]
) -> int:
    """Return maximum bipartite cardinality over occurrences and actions."""

    reference_by_action = [-1] * len(actions)

    def augment(reference: int, seen_actions: set[int]) -> bool:
        for action, candidates in enumerate(actions):
            if action in seen_actions or expected[reference] not in candidates:
                continue
            seen_actions.add(action)
            prior = reference_by_action[action]
            if prior < 0 or augment(prior, seen_actions):
                reference_by_action[action] = reference
                return True
        return False

    return sum(augment(reference, set()) for reference in range(len(expected)))


def _maximum_ordered_matching(
    expected: tuple[str, ...], actions: tuple[frozenset[str], ...]
) -> int:
    """Return LCS cardinality where membership defines compatibility."""

    previous = [0] * (len(actions) + 1)
    for name in expected:
        current = [0]
        for action_index, candidates in enumerate(actions, start=1):
            compatible = previous[action_index - 1] + int(name in candidates)
            current.append(max(previous[action_index], current[-1], compatible))
        previous = current
    return previous[-1]


def candidate_action_alignment(
    expected_tool_occurrences: Sequence[str],
    candidate_actions: Sequence[Collection[str]] | None,
) -> dict[str, object]:
    """Measure coverage and one-to-one alignment at four strengths.

    ``None`` denotes an unavailable candidate state. An empty sequence denotes
    an available state containing zero candidate actions. Union coverage counts
    reference occurrences whose names appear anywhere. Unordered and ordered
    counts enforce one candidate action per matched reference occurrence;
    ordered matching additionally preserves both sequences. Strict matching
    compares equal indices, while its full-coverage flag also requires equal
    reference and candidate-action counts.
    """

    expected = _expected_occurrences(expected_tool_occurrences)
    parsed_actions = _candidate_actions(candidate_actions)
    available = parsed_actions is not None
    actions = parsed_actions or ()
    reference_count = len(expected)

    if available:
        vocabulary = frozenset(name for action in actions for name in action)
        union_count = sum(name in vocabulary for name in expected)
        unavailable_count = 0
        absent_count = reference_count - union_count
        unordered_count = _maximum_unordered_matching(expected, actions)
        ordered_count = _maximum_ordered_matching(expected, actions)
        strict_count = sum(
            expected[index] in actions[index]
            for index in range(min(reference_count, len(actions)))
        )
    else:
        vocabulary = frozenset()
        union_count = unordered_count = ordered_count = strict_count = 0
        unavailable_count = reference_count
        # Keep unavailable references separate from observed vocabulary misses.
        absent_count = 0

    losses = {
        "unavailable": unavailable_count,
        "absent_from_union": absent_count,
        "action_capacity_or_grouping": union_count - unordered_count,
        "order_incompatibility": unordered_count - ordered_count,
        "strict_position": ordered_count - strict_count,
    }
    losses["total"] = sum(losses.values())

    if reference_count == 0:
        coverage: dict[str, bool | None] = {
            "union": None,
            "unordered_one_to_one": None,
            "ordered_one_to_one": None,
            "strict_one_for_one": None,
        }
    elif not available:
        coverage = {
            "union": False,
            "unordered_one_to_one": False,
            "ordered_one_to_one": False,
            "strict_one_for_one": False,
        }
    else:
        coverage = {
            "union": union_count == reference_count,
            "unordered_one_to_one": unordered_count == reference_count,
            "ordered_one_to_one": ordered_count == reference_count,
            "strict_one_for_one": (
                len(actions) == reference_count
                and strict_count == reference_count
            ),
        }

    return {
        "candidate_state_available": available,
        "reference_occurrence_count": reference_count,
        "candidate_action_count": len(actions),
        "candidate_vocabulary_size": len(vocabulary),
        "unavailable_reference_count": unavailable_count,
        "absent_from_union_count": absent_count,
        "union_coverage_count": union_count,
        "unordered_one_to_one_match_count": unordered_count,
        "ordered_one_to_one_match_count": ordered_count,
        "strict_same_position_match_count": strict_count,
        "full_coverage": coverage,
        "descriptive_losses": losses,
    }
