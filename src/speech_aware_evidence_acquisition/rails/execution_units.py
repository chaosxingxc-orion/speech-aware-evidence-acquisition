"""Immutable execution units for multiple registered slices of one parent.

An execution unit is an execution identity, never a replacement dataset
sample identity.  The runner keeps ``parent_sample_id`` as the TaskSample and
uses ``request_key`` only to isolate histories, budgets, and trace records.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
import hashlib
import json

from ..core.model import SliceRecord
from .errors import RailsError


@dataclass(frozen=True)
class ExecutionUnit:
    """One declared request key and its immutable registered raw slice."""

    parent_sample_id: str
    request_key: str
    slice_record: SliceRecord

    def validate(self) -> "ExecutionUnit":
        if (
            not isinstance(self.parent_sample_id, str)
            or not self.parent_sample_id
            or not isinstance(self.request_key, str)
            or not self.request_key
            or not isinstance(self.slice_record, SliceRecord)
            or self.slice_record.sample_id != self.parent_sample_id
        ):
            raise RailsError("execution unit must bind one parent, key, and matching SliceRecord")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "parent_sample_id": self.parent_sample_id,
            "request_key": self.request_key,
            "slice_record": dict(self.slice_record.__dict__),
        }


@dataclass(frozen=True)
class ExecutionUnitRoster:
    """The one public optional inventory form accepted by runner APIs."""

    units: tuple[ExecutionUnit, ...]

    def validate(
        self, *, parent_sample_ids: Sequence[str], max_contacts: int
    ) -> "ExecutionUnitRoster":
        validate_execution_units(
            self.units, parent_sample_ids=parent_sample_ids, max_contacts=max_contacts
        )
        return self

    def content_hash(self) -> str:
        """Stable custody hash including every original slice source fact."""
        document = [unit.as_json() for unit in self.units]
        return hashlib.sha256(
            json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def validate_execution_units(
    units: Sequence[ExecutionUnit], *, parent_sample_ids: Sequence[str], max_contacts: int
) -> tuple[ExecutionUnit, ...]:
    """Validate a complete ordered unit inventory before runner preparation.

    The caller registers each returned record with the shared client before
    dispatch.  This function deliberately validates no later observation: a
    re-listen is a successor observation of an already-declared unit.
    """
    if isinstance(max_contacts, bool) or not isinstance(max_contacts, int) or max_contacts < 1:
        raise RailsError("execution unit max_contacts must be a positive integer")
    parents = tuple(parent_sample_ids)
    if not parents or len(set(parents)) != len(parents):
        raise RailsError("execution units require a unique non-empty parent roster")
    if not units or any(not isinstance(unit, ExecutionUnit) for unit in units):
        raise RailsError("execution_units must be non-empty ExecutionUnit entries")
    checked = tuple(unit.validate() for unit in units)
    keys = tuple(unit.request_key for unit in checked)
    if len(set(keys)) != len(keys):
        raise RailsError("execution units require unique ordered request_key values")
    grouped: dict[str, int] = {parent: 0 for parent in parents}
    for unit in checked:
        if unit.parent_sample_id not in grouped:
            raise RailsError("execution unit parent is outside the supplied roster")
        grouped[unit.parent_sample_id] += 1
    if any(count == 0 for count in grouped.values()):
        raise RailsError("execution units must cover every supplied parent exactly once or more")
    return checked


__all__ = ["ExecutionUnit", "ExecutionUnitRoster", "validate_execution_units"]
