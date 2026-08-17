"""core.flight_lock: the PYTHON read side of the E0-prime flight lock
(2026-08-16 flight-protection fix). Advisory-read semantics only -- never
raises, always ``None`` for anything short of a genuinely parseable JSON
object."""

from __future__ import annotations

import json
from pathlib import Path

from speech_aware_evidence_acquisition.core.flight_lock import (
    FLIGHT_LOCK_RELPATH,
    flight_lock_path,
    read_flight_lock,
)


def test_flight_lock_path_is_relative_to_data_root(tmp_path):
    assert flight_lock_path(tmp_path) == tmp_path / FLIGHT_LOCK_RELPATH
    assert flight_lock_path(tmp_path) == tmp_path / "locks" / "flight.lock"


def test_read_flight_lock_returns_none_when_missing(tmp_path):
    assert read_flight_lock(tmp_path) is None


def test_read_flight_lock_returns_none_for_malformed_json(tmp_path):
    path = flight_lock_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text("{not json", encoding="utf-8")
    assert read_flight_lock(tmp_path) is None


def test_read_flight_lock_returns_none_for_a_non_object_json_value(tmp_path):
    path = flight_lock_path(tmp_path)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(["run-1", "run-2"]), encoding="utf-8")
    assert read_flight_lock(tmp_path) is None


def test_read_flight_lock_returns_the_document_for_a_genuine_object(tmp_path):
    path = flight_lock_path(tmp_path)
    path.parent.mkdir(parents=True)
    document = {
        "run_ids": ["SAEA-E-002-r4-nocontext"],
        "pid": 4242,
        "started_at": "2026-08-16T00:00:00Z",
        "study_head": "a" * 40,
    }
    path.write_text(json.dumps(document), encoding="utf-8")
    read_back = read_flight_lock(tmp_path)
    assert read_back == document


def test_read_flight_lock_returns_none_for_unreadable_bytes(tmp_path):
    # A directory in place of the expected file is unreadable as text --
    # exercises the OSError branch distinctly from the JSONDecodeError one.
    path = flight_lock_path(tmp_path)
    path.mkdir(parents=True)
    assert read_flight_lock(tmp_path) is None
