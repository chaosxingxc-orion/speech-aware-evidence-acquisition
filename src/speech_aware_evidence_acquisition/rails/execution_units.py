"""Immutable execution units for multiple registered slices of one parent.

An execution unit is an execution identity, never a replacement dataset
sample identity.  The runner keeps ``parent_sample_id`` as the TaskSample and
uses ``request_key`` only to isolate histories, budgets, and trace records.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from collections.abc import Mapping, Sequence
import hashlib
import json

from ..core.model import SliceRecord
from ..core.preparation import PreparationError
from ..core.preparation_window_packets import PreparedWindowFeaturePackets
from .errors import RailsError


@dataclass(frozen=True)
class ExecutionUnit:
    """One declared request key and its immutable registered raw slice."""

    parent_sample_id: str
    request_key: str
    slice_record: SliceRecord
    speech_packet_id: str | None = None
    speech_packet_sha256: str | None = None

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
        if (self.speech_packet_id is None) != (self.speech_packet_sha256 is None):
            raise RailsError("execution unit speech packet ID and SHA256 must appear together")
        if self.speech_packet_id is not None and (
            not isinstance(self.speech_packet_id, str)
            or not self.speech_packet_id
            or not isinstance(self.speech_packet_sha256, str)
            or len(self.speech_packet_sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.speech_packet_sha256)
        ):
            raise RailsError("execution unit speech packet identity is malformed")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        document = {
            "parent_sample_id": self.parent_sample_id,
            "request_key": self.request_key,
            "slice_record": self.slice_record.trace_view(),
        }
        if self.speech_packet_id is not None:
            document.update(
                speech_packet_id=self.speech_packet_id,
                speech_packet_sha256=self.speech_packet_sha256,
            )
        return document

    def query_descriptor(self, query_source: str) -> dict[str, str]:
        """Return the source identity in the existing request representation."""
        self.validate()
        if query_source == "speech_audio":
            return {
                "media_relpath": self.slice_record.media_relpath,
                "sha256": self.slice_record.sha256,
            }
        if query_source == "speech_features":
            if self.speech_packet_id is None or self.speech_packet_sha256 is None:
                raise RailsError("feature execution unit has no bound speech packet")
            return {
                "packet_id": self.speech_packet_id,
                "sha256": self.speech_packet_sha256,
                "role": "query",
            }
        raise RailsError("execution unit query source must be speech_audio or speech_features")


@dataclass(frozen=True)
class ExecutionUnitRoster:
    """The one public optional inventory form accepted by runner APIs."""

    units: tuple[ExecutionUnit, ...]

    def validate(
        self, *, parent_sample_ids: Sequence[str], max_contacts: int
    ) -> "ExecutionUnitRoster":
        if not isinstance(self.units, tuple):
            raise RailsError("execution unit roster units must be an immutable tuple")
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

    def with_speech_packets(self, prepared: PreparedWindowFeaturePackets) -> "ExecutionUnitRoster":
        """Attach already prepared formal packets to this exact ordered roster."""
        if not isinstance(prepared, PreparedWindowFeaturePackets):
            raise RailsError("prepared speech packets have the wrong type")
        bindings = prepared.by_request_key
        request_count = prepared.request_count
        expected = tuple(unit.request_key for unit in self.units)
        if (
            not isinstance(bindings, Mapping)
            or request_count != len(self.units)
            or len(set(expected)) != len(expected)
            or set(bindings) != set(expected)
            or tuple(binding.request_key for binding in prepared.bindings) != expected
        ):
            raise RailsError("prepared speech packets must cover the exact execution unit roster")
        attached = []
        try:
            for unit in self.units:
                binding = prepared.binding_for(
                    unit.request_key, unit.slice_record.trace_view()
                )
                if binding.audio_sha256 != unit.slice_record.sha256:
                    raise RailsError("speech packet audio differs from its execution unit slice")
                current = (
                    None
                    if unit.speech_packet_id is None
                    else (unit.speech_packet_id, unit.speech_packet_sha256)
                )
                selected = (binding.packet_id, binding.packet_sha256)
                if current not in (None, selected):
                    raise RailsError(
                        "execution unit already carries a different speech packet"
                    )
                attached.append(
                    replace(
                        unit,
                        speech_packet_id=binding.packet_id,
                        speech_packet_sha256=binding.packet_sha256,
                    ).validate()
                )
        except RailsError:
            raise
        except PreparationError as error:
            raise RailsError(f"cannot bind prepared speech packets: {error}") from error
        return ExecutionUnitRoster(tuple(attached))


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


def execution_unit_scope(execution_unit_id: str) -> str:
    """Return a collision-resistant non-model-visible namespace for one unit."""
    if not isinstance(execution_unit_id, str) or not execution_unit_id:
        raise RailsError("execution unit ID must be a nonempty string")
    return "unit-" + hashlib.sha256(execution_unit_id.encode("utf-8")).hexdigest()


def scoped_execution_contact_id(contact_id: str, execution_unit_id: str | None) -> str:
    """Preserve legacy contact IDs unless an explicit unit is bound."""
    if execution_unit_id is None:
        return contact_id
    return execution_unit_scope(execution_unit_id) + "/" + contact_id


def unscoped_execution_contact_id(contact_id: str, execution_unit_id: str | None) -> str:
    """Validate the exact immutable unit before reading its role authority."""
    if execution_unit_id is None:
        return contact_id
    prefix = execution_unit_scope(execution_unit_id) + "/"
    if not isinstance(contact_id, str) or not contact_id.startswith(prefix):
        raise RailsError("contact differs from its immutable execution unit")
    return contact_id[len(prefix):]
