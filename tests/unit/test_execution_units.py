"""Model-free custody tests for runner execution-unit inventories."""

import hashlib
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.core.model import SliceRecord
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.execution_units import (
    ExecutionUnit,
    ExecutionUnitRoster,
)


def _unit(key: str, *, parent="call", payload=b"slice"):
    return ExecutionUnit(
        parent_sample_id=parent,
        request_key=key,
        slice_record=SliceRecord(
            sample_id=parent,
            parent_media_relpath=f"media/{parent}.wav",
            parent_sha256="a" * 64,
            start_seconds=0.0,
            end_seconds=1.0,
            audio_seconds=1.0,
            sample_rate_hz=16000,
            media_relpath=f"derived/{key}.wav",
            sha256=hashlib.sha256(payload).hexdigest(),
            bytes=len(payload),
            iteration=0,
        ),
    )


def test_two_windows_of_one_parent_have_distinct_full_source_bindings():
    roster = ExecutionUnitRoster((_unit("call#w0001", payload=b"one"), _unit("call#w0002", payload=b"two")))

    assert roster.validate(parent_sample_ids=("call",), max_contacts=2) is roster
    assert roster.content_hash() != ExecutionUnitRoster((roster.units[1], roster.units[0])).content_hash()
    assert [unit.request_key for unit in roster.units] == ["call#w0001", "call#w0002"]


@pytest.mark.parametrize("units", [(), (_unit("call#w0001"), _unit("call#w0001"))])
def test_roster_refuses_empty_or_duplicate_unit_keys(units):
    with pytest.raises(RailsError):
        ExecutionUnitRoster(units).validate(parent_sample_ids=("call",), max_contacts=1)


def test_roster_refuses_missing_parent_or_mismatched_slice_parent():
    with pytest.raises(RailsError, match="cover every"):
        ExecutionUnitRoster((_unit("other#w0001", parent="other"),)).validate(
            parent_sample_ids=("call", "other"), max_contacts=1
        )
    bad = _unit("call#w0001")
    bad = replace(bad, slice_record=replace(bad.slice_record, sample_id="other"))
    with pytest.raises(RailsError, match="matching SliceRecord"):
        ExecutionUnitRoster((bad,)).validate(parent_sample_ids=("call",), max_contacts=1)
