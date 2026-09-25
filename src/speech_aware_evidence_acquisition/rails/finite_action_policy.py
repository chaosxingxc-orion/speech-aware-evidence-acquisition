"""Pure, finite contextual action policy over complete-system official returns.

The caller verifies sealed artifacts and supplies a complete round. This module
checks the declared identities and arithmetic; it never opens a file or scores.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import re
from typing import Mapping, Sequence

from .hashing import content_hash


class FinitePolicyError(ValueError):
    """A policy snapshot, decision, or complete round is inconsistent."""


_SHA = re.compile(r"[0-9a-f]{64}\Z")
SPARSE_SUPPORT = 20


def _name(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise FinitePolicyError(f"{field} must be nonempty text")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise FinitePolicyError(f"{field} must be a lowercase SHA-256")
    return value


def _number(value: object, field: str, *, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FinitePolicyError(f"{field} must be finite numeric, never boolean")
    try:
        result = float(value)
    except OverflowError as error:
        raise FinitePolicyError(f"{field} must be finite numeric") from error
    if not math.isfinite(result):
        raise FinitePolicyError(f"{field} must be finite numeric")
    if minimum is not None and result < minimum:
        raise FinitePolicyError(f"{field} is below {minimum}")
    return result


def _object(value: object, field: str, keys: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise FinitePolicyError(f"{field} has missing or unknown keys")
    return value


def _list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise FinitePolicyError(f"{field} must be a JSON list")
    return value


@dataclass(frozen=True)
class CountSum:
    count: int = 0
    utility_sum: float = 0.0

    def __post_init__(self) -> None:
        if isinstance(self.count, bool) or not isinstance(self.count, int) or self.count < 0:
            raise FinitePolicyError("count must be a nonnegative integer")
        _number(self.utility_sum, "utility sum")

    @property
    def mean(self) -> float:
        return self.utility_sum / self.count if self.count else 0.0

    @classmethod
    def from_json(cls, value: object) -> "CountSum":
        row = _object(value, "count/sum", frozenset({"count", "utility_sum"}))
        return cls(row["count"], row["utility_sum"])


@dataclass(frozen=True)
class CreditedTrajectory:
    round_id: str
    round_descriptor_sha256: str
    sample_id: str
    trajectory_sha256: str
    source_hashes: tuple[tuple[str, str], ...]
    state_id: str
    action: str
    decision: PolicyDecision
    tp: float
    fp: float
    fn: float
    intent_exact: float
    format_ok: bool
    fallback_flags: tuple[str, ...]
    utility: float

    def __post_init__(self) -> None:
        _name(self.round_id, "round id")
        _sha(self.round_descriptor_sha256, "round descriptor hash")
        _name(self.sample_id, "sample id")
        _sha(self.trajectory_sha256, "trajectory fingerprint")
        if (not isinstance(self.source_hashes, tuple) or not self.source_hashes
                or any(not isinstance(pair, tuple) or len(pair) != 2 for pair in self.source_hashes)):
            raise FinitePolicyError("source hashes must be an immutable tuple of name/hash pairs")
        for key, value in self.source_hashes:
            _name(key, "source hash name")
            _sha(value, "source hash")
        if len({key for key, _ in self.source_hashes}) != len(self.source_hashes):
            raise FinitePolicyError("source hashes must name distinct sources")
        _name(self.state_id, "state id")
        _name(self.action, "action")
        if (not isinstance(self.decision, PolicyDecision)
                or self.decision.state_id != self.state_id or self.decision.action != self.action):
            raise FinitePolicyError("credited decision state or action disagrees")
        for field in ("tp", "fp", "fn"):
            _number(getattr(self, field), field, minimum=0)
        if _number(self.intent_exact, "intent exact") not in (0.0, 1.0):
            raise FinitePolicyError("intent exact must be numeric zero or one")
        if not isinstance(self.format_ok, bool):
            raise FinitePolicyError("format state must be boolean")
        if not isinstance(self.fallback_flags, tuple):
            raise FinitePolicyError("fallback flags must be an immutable tuple")
        for flag in self.fallback_flags:
            _name(flag, "fallback flag")
        if len(set(self.fallback_flags)) != len(self.fallback_flags):
            raise FinitePolicyError("fallback flags must be unique")
        _number(self.utility, "utility")

    def as_json(self) -> dict[str, object]:
        return {
            "round_id": self.round_id, "round_descriptor_sha256": self.round_descriptor_sha256,
            "sample_id": self.sample_id,
            "trajectory_sha256": self.trajectory_sha256,
            "source_hashes": [[key, value] for key, value in self.source_hashes],
            "state_id": self.state_id, "action": self.action,
            "decision": self.decision.as_json(),
            "tp": self.tp, "fp": self.fp, "fn": self.fn,
            "intent_exact": self.intent_exact, "format_ok": self.format_ok,
            "fallback_flags": list(self.fallback_flags), "utility": self.utility,
        }

    @classmethod
    def from_json(cls, value: object) -> "CreditedTrajectory":
        row = _object(value, "credited trajectory", frozenset({
            "round_id", "round_descriptor_sha256", "sample_id", "trajectory_sha256",
            "source_hashes", "state_id", "action", "decision", "tp", "fp", "fn",
            "intent_exact", "format_ok", "fallback_flags", "utility",
        }))
        sources = _list(row["source_hashes"], "credited source hashes")
        pairs = []
        for source in sources:
            pair = _list(source, "credited source pair")
            if len(pair) != 2:
                raise FinitePolicyError("credited source pair must have name and SHA")
            pairs.append(tuple(pair))
        return cls(
            row["round_id"], row["round_descriptor_sha256"], row["sample_id"],
            row["trajectory_sha256"], tuple(pairs), row["state_id"], row["action"],
            PolicyDecision.from_json(row["decision"]), row["tp"], row["fp"], row["fn"],
            row["intent_exact"], row["format_ok"],
            tuple(_list(row["fallback_flags"], "fallback flags")), row["utility"],
        )


@dataclass(frozen=True)
class PolicySnapshot:
    actions: tuple[str, ...]
    states: tuple[str, ...]
    f0: float
    cell_stats: tuple[CountSum, ...]
    global_stats: tuple[CountSum, ...]
    credited: tuple[CreditedTrajectory, ...] = ()
    parent_sha256: str | None = None

    @classmethod
    def create(cls, *, actions: Sequence[str], states: Sequence[str], f0: float) -> "PolicySnapshot":
        ordered_actions, ordered_states = tuple(actions), tuple(states)
        return cls(ordered_actions, ordered_states, f0,
                   tuple(CountSum() for _ in range(len(ordered_actions) * len(ordered_states))),
                   tuple(CountSum() for _ in ordered_actions))

    def __post_init__(self) -> None:
        for label, items in (("actions", self.actions), ("states", self.states)):
            if not isinstance(items, tuple) or not items:
                raise FinitePolicyError(f"{label} must be an ordered unique nonempty tuple")
            for item in items:
                _name(item, label)
            if len(set(items)) != len(items):
                raise FinitePolicyError(f"{label} must be unique")
        f0 = _number(self.f0, "frozen F0", minimum=0)
        if f0 > 1:
            raise FinitePolicyError("frozen F0 exceeds one")
        if (not isinstance(self.cell_stats, tuple) or len(self.cell_stats) != len(self.states) * len(self.actions)
                or not isinstance(self.global_stats, tuple) or len(self.global_stats) != len(self.actions)
                or any(not isinstance(item, CountSum) for item in self.cell_stats + self.global_stats)):
            raise FinitePolicyError("state-action/global count-sum shape disagrees")
        if not isinstance(self.credited, tuple) or any(not isinstance(item, CreditedTrajectory) for item in self.credited):
            raise FinitePolicyError("credited trajectories must be an immutable tuple")
        if self.parent_sha256 is not None:
            _sha(self.parent_sha256, "parent snapshot hash")
        fingerprints = [item.trajectory_sha256 for item in self.credited]
        if len(fingerprints) != len(set(fingerprints)):
            raise FinitePolicyError("snapshot credits a trajectory more than once")
        expected_cells = [CountSum() for _ in self.cell_stats]
        expected_global = [CountSum() for _ in self.global_stats]
        for item in self.credited:
            if item.state_id not in self.states or item.action not in self.actions:
                raise FinitePolicyError("credited state or action is outside fixed inventory")
            if item.utility != official_utility(tp=item.tp, fp=item.fp, fn=item.fn, f0=self.f0):
                raise FinitePolicyError("credited utility disagrees with frozen F0 and official counts")
            action_index = self.actions.index(item.action)
            cell_index = self.states.index(item.state_id) * len(self.actions) + action_index
            old_cell, old_global = expected_cells[cell_index], expected_global[action_index]
            expected_cells[cell_index] = CountSum(old_cell.count + 1, old_cell.utility_sum + item.utility)
            expected_global[action_index] = CountSum(old_global.count + 1, old_global.utility_sum + item.utility)
        if tuple(expected_cells) != self.cell_stats or tuple(expected_global) != self.global_stats:
            raise FinitePolicyError("snapshot count/sum fields disagree with credited trajectories")

    def as_json(self) -> dict[str, object]:
        return {
            "schema": "saea-finite-action-policy-snapshot-v1",
            "actions": list(self.actions), "states": list(self.states), "f0": self.f0,
            "sparse_support": SPARSE_SUPPORT,
            "cell_stats": [{"count": item.count, "utility_sum": item.utility_sum} for item in self.cell_stats],
            "global_stats": [{"count": item.count, "utility_sum": item.utility_sum} for item in self.global_stats],
            "credited": [item.as_json() for item in self.credited],
            "parent_sha256": self.parent_sha256,
        }

    @classmethod
    def from_json(cls, value: object) -> "PolicySnapshot":
        row = _object(value, "policy snapshot", frozenset({
            "schema", "actions", "states", "f0", "sparse_support",
            "cell_stats", "global_stats", "credited", "parent_sha256",
        }))
        if (row["schema"] != "saea-finite-action-policy-snapshot-v1"
                or type(row["sparse_support"]) is not int or row["sparse_support"] != SPARSE_SUPPORT):
            raise FinitePolicyError("snapshot schema or sparse support disagrees")
        return cls(
            tuple(_list(row["actions"], "snapshot actions")),
            tuple(_list(row["states"], "snapshot states")),
            row["f0"],
            tuple(CountSum.from_json(item) for item in _list(row["cell_stats"], "snapshot cell stats")),
            tuple(CountSum.from_json(item) for item in _list(row["global_stats"], "snapshot global stats")),
            tuple(CreditedTrajectory.from_json(item) for item in _list(row["credited"], "snapshot credits")),
            row["parent_sha256"],
        )

    @property
    def sha256(self) -> str:
        return content_hash(self.as_json())

    def preferred_action(self, state_id: str) -> str:
        """Cumulative means; zero-support global means are zero, ties use action order.

        Adaptive sampling can bias observed means; no IPW correction is implied.
        """
        if state_id not in self.states:
            raise FinitePolicyError("decision state is outside fixed inventory")
        offset = self.states.index(state_id) * len(self.actions)
        estimates = []
        for action_index in range(len(self.actions)):
            cell = self.cell_stats[offset + action_index]
            source = cell if cell.count >= SPARSE_SUPPORT else self.global_stats[action_index]
            estimates.append(source.mean)
        return self.actions[max(range(len(self.actions)), key=lambda index: estimates[index])]


@dataclass(frozen=True)
class PolicyDecision:
    snapshot_sha256: str
    state_id: str
    epsilon: float | None
    draw: float
    action: str
    probabilities: tuple[float, ...]
    propensity: float
    allocation_kind: str = "epsilon-greedy"

    def __post_init__(self) -> None:
        _sha(self.snapshot_sha256, "decision snapshot hash")
        _name(self.state_id, "decision state")
        _name(self.action, "decision action")
        _name(self.allocation_kind, "allocation kind")
        if self.allocation_kind == "epsilon-greedy":
            if _number(self.epsilon, "decision epsilon", minimum=0) > 1:
                raise FinitePolicyError("decision epsilon exceeds one")
        elif self.allocation_kind == "balanced-without-replacement":
            if self.epsilon is not None:
                raise FinitePolicyError("balanced decision cannot claim epsilon sampling")
        else:
            raise FinitePolicyError("unknown decision allocation kind")
        draw = _number(self.draw, "decision draw", minimum=0)
        if draw >= 1:
            raise FinitePolicyError("decision draw must be below one")
        if not isinstance(self.probabilities, tuple) or not self.probabilities:
            raise FinitePolicyError("decision probabilities must be an immutable nonempty tuple")
        values = tuple(_number(value, "decision probability", minimum=0) for value in self.probabilities)
        if not math.isclose(math.fsum(values), 1.0, rel_tol=0, abs_tol=1e-12):
            raise FinitePolicyError("decision probabilities must sum to one")
        propensity = _number(self.propensity, "decision propensity", minimum=0)
        if propensity <= 0 or propensity > 1 or propensity not in values:
            raise FinitePolicyError("selected action propensity must be positive")

    def as_json(self) -> dict[str, object]:
        return {
            "snapshot_sha256": self.snapshot_sha256, "state_id": self.state_id,
            "epsilon": self.epsilon, "draw": self.draw, "action": self.action,
            "probabilities": list(self.probabilities), "propensity": self.propensity,
            "allocation_kind": self.allocation_kind,
        }

    @classmethod
    def from_json(cls, value: object) -> "PolicyDecision":
        row = _object(value, "policy decision", frozenset({
            "snapshot_sha256", "state_id", "epsilon", "draw", "action",
            "probabilities", "propensity", "allocation_kind",
        }))
        return cls(
            row["snapshot_sha256"], row["state_id"], row["epsilon"], row["draw"],
            row["action"], tuple(_list(row["probabilities"], "decision probabilities")),
            row["propensity"], row["allocation_kind"],
        )


def _select_probability(probabilities: tuple[float, ...], draw: float) -> int:
    draw = _number(draw, "uniform draw", minimum=0)
    if draw >= 1:
        raise FinitePolicyError("uniform draw must be below one")
    cumulative = 0.0
    for index, probability in enumerate(probabilities):
        cumulative += probability
        if draw < cumulative:
            return index
    if 0 <= 1.0 - cumulative <= 1e-12:
        for index in range(len(probabilities) - 1, -1, -1):
            if probabilities[index] > 0:
                return index
    raise FinitePolicyError("probability vector failed to cover uniform draw")


def sample_action(snapshot: PolicySnapshot, *, state_id: str, epsilon: float, draw: float) -> PolicyDecision:
    """Use an externally supplied uniform draw; tie breaks follow ordered actions."""
    epsilon = _number(epsilon, "epsilon", minimum=0)
    draw = _number(draw, "uniform draw", minimum=0)
    if epsilon > 1 or draw >= 1:
        raise FinitePolicyError("epsilon must be at most one and draw below one")
    preferred = snapshot.preferred_action(state_id)
    count = len(snapshot.actions)
    probabilities = tuple(epsilon / count + (1 - epsilon if action == preferred else 0.0)
                          for action in snapshot.actions)
    index = _select_probability(probabilities, draw)
    return PolicyDecision(snapshot.sha256, state_id, epsilon, draw,
                          snapshot.actions[index], probabilities, probabilities[index])


def _balanced_quotas(snapshot: PolicySnapshot, quotas: Sequence[int], rows: int) -> tuple[int, ...]:
    values = tuple(quotas)
    if (len(values) != len(snapshot.actions)
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in values)
            or sum(values) != rows or max(values) - min(values) > 1):
        raise FinitePolicyError("initial action quotas must sum to roster size and differ by at most one")
    return values


def sample_balanced_action(snapshot: PolicySnapshot, *, state_id: str,
                           remaining_quotas: Sequence[int], draw: float) -> PolicyDecision:
    """Draw without replacement from caller-tracked remaining action quotas."""
    if state_id not in snapshot.states:
        raise FinitePolicyError("decision state is outside fixed inventory")
    remaining = tuple(remaining_quotas)
    if (len(remaining) != len(snapshot.actions)
            or any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in remaining)
            or sum(remaining) <= 0):
        raise FinitePolicyError("remaining action quotas are invalid or exhausted")
    probabilities = tuple(value / sum(remaining) for value in remaining)
    index = _select_probability(probabilities, draw)
    return PolicyDecision(snapshot.sha256, state_id, None, draw, snapshot.actions[index],
                          probabilities, probabilities[index], "balanced-without-replacement")


def sample_balanced_round(snapshot: PolicySnapshot, *, roster_states: Sequence[tuple[str, str]],
                          initial_quotas: Sequence[int], draws: Sequence[float]) -> tuple[PolicyDecision, ...]:
    """Assign in frozen roster order; caller owns the seed and uniform draws."""
    if len(roster_states) != len(draws) or not roster_states:
        raise FinitePolicyError("balanced roster and draws must have equal nonzero length")
    if len({sid for sid, _state in roster_states}) != len(roster_states):
        raise FinitePolicyError("balanced roster repeats a sample id")
    remaining = list(_balanced_quotas(snapshot, initial_quotas, len(roster_states)))
    result = []
    for sid, state_id in roster_states:
        _name(sid, "balanced roster sample id")
        decision = sample_balanced_action(snapshot, state_id=state_id,
                                          remaining_quotas=remaining, draw=draws[len(result)])
        remaining[snapshot.actions.index(decision.action)] -= 1
        result.append(decision)
    if any(remaining):
        raise FinitePolicyError("balanced round did not exhaust action quotas")
    return tuple(result)


@dataclass(frozen=True)
class RoundDescriptor:
    round_id: str
    roster_ids: tuple[str, ...]
    roster_sha256: str
    snapshot_sha256: str
    epsilon: float | None
    allocation_kind: str = "epsilon-greedy"
    initial_quotas: tuple[int, ...] = ()

    def as_json(self) -> dict[str, object]:
        return {
            "round_id": self.round_id, "roster_ids": list(self.roster_ids),
            "roster_sha256": self.roster_sha256, "snapshot_sha256": self.snapshot_sha256,
            "epsilon": self.epsilon, "allocation_kind": self.allocation_kind,
            "initial_quotas": list(self.initial_quotas),
        }

    @property
    def sha256(self) -> str:
        return content_hash(self.as_json())


@dataclass(frozen=True)
class TerminalFeedback:
    sample_id: str
    trajectory_sha256: str
    source_hashes: tuple[tuple[str, str], ...]
    decision: PolicyDecision
    action: str
    logged_propensity: float
    tp: float
    fp: float
    fn: float
    intent_exact: float
    format_ok: bool
    fallback_flags: tuple[str, ...]


def official_utility(*, tp: float, fp: float, fn: float, f0: float) -> float:
    """Official combined word/character count utility, never a success bit."""
    tp, fp, fn = (_number(value, name, minimum=0) for name, value in (("TP", tp), ("FP", fp), ("FN", fn)))
    f0 = _number(f0, "frozen F0", minimum=0)
    if f0 > 1:
        raise FinitePolicyError("frozen F0 exceeds one")
    return _number(2 * tp - f0 * (2 * tp + fp + fn), "computed utility")


def update_complete_round(snapshot: PolicySnapshot, descriptor: RoundDescriptor,
                          feedback: Sequence[TerminalFeedback]) -> PolicySnapshot:
    """Validate and credit every declared terminal row before returning a new snapshot.

    The descriptor is a caller assertion; this pure function cannot prove that
    roster, scorer, or trajectory artifacts were actually sealed.
    """
    _name(descriptor.round_id, "round id")
    _sha(descriptor.roster_sha256, "round roster hash")
    _sha(descriptor.snapshot_sha256, "round snapshot hash")
    if descriptor.snapshot_sha256 != snapshot.sha256:
        raise FinitePolicyError("round policy snapshot hash disagrees")
    if descriptor.allocation_kind == "epsilon-greedy":
        _number(descriptor.epsilon, "round epsilon", minimum=0)
        if descriptor.epsilon > 1 or descriptor.initial_quotas:
            raise FinitePolicyError("epsilon round has invalid exploration or quotas")
    elif descriptor.allocation_kind == "balanced-without-replacement":
        if descriptor.epsilon is not None:
            raise FinitePolicyError("balanced round cannot claim independent epsilon sampling")
    else:
        raise FinitePolicyError("unknown round allocation kind")
    roster = descriptor.roster_ids
    if not isinstance(roster, tuple) or not roster or len(set(roster)) != len(roster):
        raise FinitePolicyError("round roster must be a unique nonempty tuple")
    for sid in roster:
        _name(sid, "round roster sample id")
    remaining = (list(_balanced_quotas(snapshot, descriptor.initial_quotas, len(roster)))
                 if descriptor.allocation_kind == "balanced-without-replacement" else None)
    if not isinstance(feedback, (list, tuple)) or len(feedback) != len(roster):
        raise FinitePolicyError("terminal feedback does not cover complete round")
    if any(not isinstance(item, TerminalFeedback) for item in feedback):
        raise FinitePolicyError("terminal feedback has an invalid row")
    if len({item.sample_id for item in feedback}) != len(feedback) or {item.sample_id for item in feedback} != set(roster):
        raise FinitePolicyError("terminal feedback ids do not exactly match round roster")
    prior_fingerprints = {item.trajectory_sha256 for item in snapshot.credited}
    prior_rounds = {item.round_id for item in snapshot.credited}
    if descriptor.round_id in prior_rounds:
        raise FinitePolicyError("round id is already credited")
    new_credits = []
    seen_fingerprints = set()
    for item in sorted(feedback, key=lambda row: roster.index(row.sample_id)):
        _sha(item.trajectory_sha256, "trajectory fingerprint")
        if item.trajectory_sha256 in seen_fingerprints or item.trajectory_sha256 in prior_fingerprints:
            raise FinitePolicyError("duplicate or conflicting trajectory credit")
        seen_fingerprints.add(item.trajectory_sha256)
        decision = item.decision
        if not isinstance(decision, PolicyDecision) or decision.snapshot_sha256 != snapshot.sha256:
            raise FinitePolicyError("terminal feedback policy decision disagrees")
        if decision.allocation_kind != descriptor.allocation_kind or decision.epsilon != descriptor.epsilon:
            raise FinitePolicyError("terminal feedback allocation policy disagrees")
        if remaining is None:
            expected = sample_action(snapshot, state_id=decision.state_id,
                                     epsilon=descriptor.epsilon, draw=decision.draw)
        else:
            expected = sample_balanced_action(snapshot, state_id=decision.state_id,
                                              remaining_quotas=remaining, draw=decision.draw)
        if decision != expected or item.action != expected.action:
            raise FinitePolicyError("terminal feedback action/probability vector disagrees")
        if _number(item.logged_propensity, "logged propensity", minimum=0) != expected.propensity:
            raise FinitePolicyError("terminal feedback logged propensity disagrees")
        value = official_utility(tp=item.tp, fp=item.fp, fn=item.fn, f0=snapshot.f0)
        credit = CreditedTrajectory(descriptor.round_id, descriptor.sha256, item.sample_id,
                                    item.trajectory_sha256, item.source_hashes,
                                    decision.state_id, item.action, decision, item.tp, item.fp, item.fn,
                                    item.intent_exact, item.format_ok, item.fallback_flags, value)
        new_credits.append(credit)
        if remaining is not None:
            remaining[snapshot.actions.index(expected.action)] -= 1
    if remaining is not None and any(remaining):
        raise FinitePolicyError("balanced round did not exhaust action quotas")
    cells = list(snapshot.cell_stats)
    globals_ = list(snapshot.global_stats)
    for credit in new_credits:
        action_index = snapshot.actions.index(credit.action)
        cell_index = snapshot.states.index(credit.state_id) * len(snapshot.actions) + action_index
        cell, global_ = cells[cell_index], globals_[action_index]
        cells[cell_index] = CountSum(cell.count + 1, cell.utility_sum + credit.utility)
        globals_[action_index] = CountSum(global_.count + 1, global_.utility_sum + credit.utility)
    return replace(snapshot, cell_stats=tuple(cells), global_stats=tuple(globals_),
                   credited=snapshot.credited + tuple(new_credits), parent_sha256=snapshot.sha256)
