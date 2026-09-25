"""Pinned local snapshot and schedule admission for the finite action policy.

These checks establish local byte identity and assignment arithmetic. They do
not verify that external trajectory or score artifacts were sealed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from ..core.preparation import PreparationError, hash_stable_file
from .finite_action_policy import (
    FinitePolicyError, PolicyDecision, PolicySnapshot, _balanced_quotas,
    _list, _name, _number, _object, _sha, sample_action,
    sample_balanced_action, sample_balanced_round,
)
from .hashing import content_hash


class PolicyArtifactError(FinitePolicyError):
    """A pinned snapshot or schedule has invalid bytes or bindings."""


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise PolicyArtifactError(f"JSON repeats key {key!r}")
        result[key] = value
    return result


def _confined_file(data_root: Path, relative: object) -> Path:
    if (not isinstance(relative, str) or not relative or "\\" in relative
            or relative.startswith("/") or any(part in ("", ".", "..") for part in relative.split("/"))):
        raise PolicyArtifactError("policy artifact path must be confined and relative")
    try:
        root = Path(data_root).resolve(strict=True)
        path = (root / relative).resolve(strict=True)
    except OSError as error:
        raise PolicyArtifactError(f"cannot resolve policy artifact path: {error}") from error
    if not path.is_relative_to(root) or not path.is_file():
        raise PolicyArtifactError("policy artifact path escapes data root or is not a file")
    return path


def _pinned_json(data_root: Path, pin: Mapping[str, object], label: str) -> tuple[object, str]:
    spec = _object(pin, f"{label} pin", frozenset({"relpath", "sha256"}))
    expected = _sha(spec["sha256"], f"{label} file hash")
    path = _confined_file(data_root, spec["relpath"])
    try:
        _size, before_sha, before_fingerprint = hash_stable_file(path, label)
        if before_sha != expected:
            raise PolicyArtifactError(f"{label} file SHA disagrees")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise PolicyArtifactError(f"{label} parsed bytes SHA disagrees")
        _size, after_sha, after_fingerprint = hash_stable_file(path, label)
        if after_sha != expected or after_fingerprint != before_fingerprint:
            raise PolicyArtifactError(f"{label} changed across parsed read")
        document = json.loads(raw, object_pairs_hook=_unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError, PreparationError) as error:
        raise PolicyArtifactError(f"cannot load pinned {label}: {error}") from error
    return document, expected


def load_policy_snapshot(data_root: Path, pin: Mapping[str, object], *,
                         expected_content_sha256: str | None = None) -> PolicySnapshot:
    """Read one confined raw-SHA-pinned snapshot, then validate canonical content."""
    document, _raw_sha = _pinned_json(data_root, pin, "policy snapshot")
    snapshot = PolicySnapshot.from_json(document)
    if expected_content_sha256 is not None:
        if snapshot.sha256 != _sha(expected_content_sha256, "snapshot content hash"):
            raise PolicyArtifactError("snapshot content hash disagrees")
    return snapshot


@dataclass(frozen=True)
class PolicySchedule:
    round_id: str
    mode: str
    snapshot_sha256: str
    roster_ids: tuple[str, ...]
    roster_identity_sha256: str
    split_identity_hash: str
    seed: int
    allocation_kind: str
    epsilon: float | None
    initial_quotas: tuple[int, ...]
    _bound_actions: tuple[str, ...] = field(default=(), repr=False, compare=False)
    _draws: tuple[float, ...] = field(default=(), repr=False, compare=False)
    _remaining_before: tuple[tuple[int, ...], ...] = field(default=(), repr=False, compare=False)
    _assigned_actions: tuple[str, ...] = field(default=(), repr=False, compare=False)

    def __post_init__(self) -> None:
        _name(self.round_id, "schedule round id")
        if self.mode not in ("construction", "evaluation"):
            raise PolicyArtifactError("schedule mode must be construction or evaluation")
        _sha(self.snapshot_sha256, "schedule snapshot hash")
        _sha(self.roster_identity_sha256, "schedule roster identity")
        _sha(self.split_identity_hash, "schedule split identity")
        if not isinstance(self.roster_ids, tuple) or not self.roster_ids:
            raise PolicyArtifactError("schedule roster must be a nonempty ordered tuple")
        for sid in self.roster_ids:
            _name(sid, "schedule sample id")
        if len(set(self.roster_ids)) != len(self.roster_ids):
            raise PolicyArtifactError("schedule roster repeats a sample id")
        if self.roster_identity_sha256 != content_hash(list(self.roster_ids)):
            raise PolicyArtifactError("schedule roster identity hash disagrees")
        if isinstance(self.seed, bool) or not isinstance(self.seed, int) or self.seed < 0:
            raise PolicyArtifactError("schedule seed must be a nonnegative integer")
        if self.allocation_kind == "epsilon-greedy":
            if _number(self.epsilon, "schedule epsilon", minimum=0) > 1 or self.initial_quotas:
                raise PolicyArtifactError("epsilon schedule has invalid epsilon or quotas")
        elif self.allocation_kind == "balanced-without-replacement":
            if self.mode != "construction" or self.epsilon is not None:
                raise PolicyArtifactError("balanced allocation is only for construction without epsilon")
        else:
            raise PolicyArtifactError("unknown schedule allocation kind")
        if not isinstance(self.initial_quotas, tuple):
            raise PolicyArtifactError("schedule quotas must be an immutable tuple")
        if self.allocation_kind == "balanced-without-replacement":
            if (not self.initial_quotas
                    or any(isinstance(value, bool) or not isinstance(value, int) or value < 0
                           for value in self.initial_quotas)
                    or sum(self.initial_quotas) != len(self.roster_ids)
                    or max(self.initial_quotas) - min(self.initial_quotas) > 1):
                raise PolicyArtifactError("balanced quotas must be near-equal and cover roster")
        if self.mode == "evaluation" and (self.allocation_kind != "epsilon-greedy" or self.epsilon != 0):
            raise PolicyArtifactError("evaluation schedule requires epsilon zero")
        if (not isinstance(self._bound_actions, tuple) or not isinstance(self._draws, tuple)
                or not isinstance(self._remaining_before, tuple)
                or any(not isinstance(row, tuple) for row in self._remaining_before)
                or not isinstance(self._assigned_actions, tuple)):
            raise PolicyArtifactError("derived schedule assignments must be immutable tuples")

    @classmethod
    def from_json(cls, value: object) -> "PolicySchedule":
        row = _object(value, "policy schedule", frozenset({
            "schema", "round_id", "mode", "snapshot_sha256", "roster_ids",
            "roster_identity_sha256", "split_identity_hash", "seed",
            "allocation_kind", "epsilon", "initial_quotas",
        }))
        if row["schema"] != "saea-finite-action-policy-schedule-v1":
            raise PolicyArtifactError("policy schedule schema disagrees")
        return cls(
            row["round_id"], row["mode"], row["snapshot_sha256"],
            tuple(_list(row["roster_ids"], "schedule roster")), row["roster_identity_sha256"],
            row["split_identity_hash"], row["seed"], row["allocation_kind"], row["epsilon"],
            tuple(_list(row["initial_quotas"], "schedule quotas")),
        )

    def as_json(self) -> dict[str, object]:
        return {
            "schema": "saea-finite-action-policy-schedule-v1",
            "round_id": self.round_id, "mode": self.mode,
            "snapshot_sha256": self.snapshot_sha256,
            "roster_ids": list(self.roster_ids),
            "roster_identity_sha256": self.roster_identity_sha256,
            "split_identity_hash": self.split_identity_hash,
            "seed": self.seed, "allocation_kind": self.allocation_kind,
            "epsilon": self.epsilon, "initial_quotas": list(self.initial_quotas),
        }

    @property
    def sha256(self) -> str:
        return content_hash(self.as_json())

    def bind(self, snapshot: PolicySnapshot) -> "PolicySchedule":
        if snapshot.sha256 != self.snapshot_sha256:
            raise PolicyArtifactError("schedule snapshot hash disagrees")
        draws = tuple(self._draw_for(sid) for sid in self.roster_ids)
        if self.allocation_kind == "epsilon-greedy":
            return replace(self, _bound_actions=snapshot.actions, _draws=draws)
        _balanced_quotas(snapshot, self.initial_quotas, len(self.roster_ids))
        placeholder = snapshot.states[0]
        decisions = sample_balanced_round(
            snapshot, roster_states=tuple((sid, placeholder) for sid in self.roster_ids),
            initial_quotas=self.initial_quotas, draws=draws,
        )
        remaining = list(self.initial_quotas)
        before = []
        for decision in decisions:
            before.append(tuple(remaining))
            remaining[snapshot.actions.index(decision.action)] -= 1
        return replace(self, _bound_actions=snapshot.actions, _draws=draws,
                       _remaining_before=tuple(before),
                       _assigned_actions=tuple(item.action for item in decisions))

    def _draw_for(self, sample_id: str) -> float:
        digest = content_hash({
            "schema": "saea-policy-draw-u52-v1", "seed": self.seed,
            "round_id": self.round_id, "sample_id": sample_id,
        })
        return int(digest[:13], 16) / 2 ** 52

    def decision_for(self, sample_id: str, state_id: str,
                     snapshot: PolicySnapshot) -> tuple[PolicyDecision, int]:
        """Return the frozen roster-position assignment for the actual pre-action state."""
        if snapshot.sha256 != self.snapshot_sha256 or snapshot.actions != self._bound_actions:
            raise PolicyArtifactError("decision snapshot differs from bound schedule")
        try:
            index = self.roster_ids.index(sample_id)
        except ValueError as error:
            raise PolicyArtifactError("sample is outside policy schedule roster") from error
        if len(self._draws) != len(self.roster_ids):
            raise PolicyArtifactError("schedule is not bound to a snapshot")
        draw = self._draws[index]
        if self.allocation_kind == "epsilon-greedy":
            decision = sample_action(snapshot, state_id=state_id, epsilon=self.epsilon, draw=draw)
        else:
            decision = sample_balanced_action(
                snapshot, state_id=state_id, remaining_quotas=self._remaining_before[index], draw=draw,
            )
            if decision.action != self._assigned_actions[index]:
                raise PolicyArtifactError("balanced assignment disagrees with frozen roster order")
        return decision, index


def load_policy_schedule(data_root: Path, pin: Mapping[str, object], *, snapshot: PolicySnapshot,
                         expected_roster_ids: Sequence[str],
                         expected_split_identity_hash: str) -> PolicySchedule:
    """Read a pinned schedule and bind its immutable decisions to one snapshot."""
    document, _raw_sha = _pinned_json(data_root, pin, "policy schedule")
    schedule = PolicySchedule.from_json(document)
    if (schedule.roster_ids != tuple(expected_roster_ids)
            or schedule.split_identity_hash != _sha(expected_split_identity_hash, "expected split identity")):
        raise PolicyArtifactError("schedule roster or split identity differs from expected flight")
    return schedule.bind(snapshot)
