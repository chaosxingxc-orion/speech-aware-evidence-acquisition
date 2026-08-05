"""Trace sink: append-only JSONL, hash manifest, repo-refusal, close semantics."""

import json

import pytest

from speech_aware_evidence_acquisition.contracts import TraceContractError
from speech_aware_evidence_acquisition.e0.artifacts import REPO_ROOT
from speech_aware_evidence_acquisition.core.tracing import TraceSink, TraceSinkError


def test_emit_appends_validated_lines_and_manifest(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    assert sink.run_id == "SAEA-E-000-test"
    h1 = sink.emit("OBS", "s1/obs", {"obs_speech_ref": "earnings21-original/1"})
    h2 = sink.emit("COST", "s1/cost", {"calls": 1, "latency_seconds": 0.5})
    lines = (tmp_path / "run" / "SAEA-E-000-test.trace.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["channel"] == "OBS"
    assert sink.manifest() == {"s1/obs": h1, "s1/cost": h2}


def test_axis_prefix_violations_propagate(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    with pytest.raises(TraceContractError):
        sink.emit("OBS", "bad", {"supply_evidence": "smuggled"})


def test_duplicate_record_id_refused(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    sink.emit("OBS", "dup", {"obs_x": 1})
    with pytest.raises(TraceSinkError, match="duplicate"):
        sink.emit("OBS", "dup", {"obs_x": 2})


def test_run_dir_inside_repo_refused():
    with pytest.raises(TraceSinkError, match="repository"):
        TraceSink(REPO_ROOT / "docs" / "sneaky-run", "SAEA-E-000-test")


def test_close_writes_manifest_and_freezes(tmp_path):
    sink = TraceSink(tmp_path / "run", "SAEA-E-000-test")
    sink.emit("OBS", "s1/obs", {"obs_x": 1})
    manifest_hash = sink.close()
    assert len(manifest_hash) == 64
    document = json.loads(
        (tmp_path / "run" / "SAEA-E-000-test.trace-manifest.json").read_text("utf-8")
    )
    assert document["records"] == sink.manifest()
    with pytest.raises(TraceSinkError, match="closed"):
        sink.emit("OBS", "s2/obs", {"obs_x": 2})
