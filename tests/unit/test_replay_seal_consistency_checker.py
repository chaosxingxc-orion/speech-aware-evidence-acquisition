"""E10d (2026-09-29): ``scripts/analysis/replay_seal_consistency.py``'s
predecessor-list extension -- ``--predecessor ATTEMPT_ID:SHA256`` pins a
declared attempt exactly as one entry of a multi-predecessor ``resume_from``
list would, and the union/conflict report (rows checked / failing /
sealed-twice) is a pure function of which attempt(s) completed which
samples, independent of any repo or composed config.

Model-free and read-only throughout: no model, server, tokenizer or network
contact anywhere in this file.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
_SRC = str(REPO / "src")
if _SRC not in os.environ.get("PYTHONPATH", "").split(":"):
    os.environ["PYTHONPATH"] = _SRC + (
        ":" + os.environ["PYTHONPATH"] if os.environ.get("PYTHONPATH") else ""
    )
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")


def _load(name: str, relpath: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checker = _load(
    "replay_seal_consistency_e10d", "scripts/analysis/replay_seal_consistency.py"
)

from speech_aware_evidence_acquisition.core.flight.resume import ResumeRecoveryError

from test_flight_resume_recovery import _harness, _fly, _trace_lines, _values, _write_predecessor
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


# ---------------------------------------------------------------------------
# _parse_predecessor_pin
# ---------------------------------------------------------------------------


def test_parse_predecessor_pin_accepts_attempt_id_and_sha256():
    digest = "a" * 64
    assert checker._parse_predecessor_pin(f"attempt-x:{digest}") == ("attempt-x", digest)


@pytest.mark.parametrize("value", ("no-colon", "attempt-x:short", ":" + "a" * 64, "attempt-x:"))
def test_parse_predecessor_pin_refuses_a_bad_shape(value):
    with pytest.raises(SystemExit):
        checker._parse_predecessor_pin(value)


# ---------------------------------------------------------------------------
# _union_report: pure function over {sample_id: [attempt_id, ...]}.
# ---------------------------------------------------------------------------


def test_union_report_over_disjoint_attempts_has_no_conflict():
    report = checker._union_report({"s1": ["attempt-a"], "s2": ["attempt-b"]})
    assert report == {"complete_rows": 2, "sealed_twice": 0, "sealed_twice_first_10": []}


def test_union_report_flags_a_sample_completed_by_two_attempts():
    report = checker._union_report({
        "s1": ["attempt-a"], "s2": ["attempt-a", "attempt-b"],
    })
    assert report["complete_rows"] == 2
    assert report["sealed_twice"] == 1
    assert report["sealed_twice_first_10"] == [checker._id_hash("s2")]


# ---------------------------------------------------------------------------
# _check_attempt: a real completed episode, scanned pinned and unpinned.
# ---------------------------------------------------------------------------


def _skeleton_for(harness):
    from speech_aware_evidence_acquisition.core.flight import runtime as flight_module
    from types import SimpleNamespace

    runtime = object.__new__(flight_module.FlightRuntime)
    runtime._composed = SimpleNamespace(
        values={**_values(harness), "arm": harness.client.arm},
    )
    runtime._plan = None
    runtime._resume = None
    runtime._resume_flown_sample_ids = ()
    runtime._identity_packet_bindings = None
    runtime._artifact_result_binding = None
    runtime._artifact_content_validator = None
    runtime._phase_summaries = ()
    runtime._output_rows = ()
    return runtime


def test_check_attempt_accepts_a_correctly_pinned_trace(tmp_path, monkeypatch):
    harness = _harness(tmp_path, "checker-pin", ("s1",))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    predecessor_path = _write_predecessor(
        _trace_lines(trace_path), tmp_path / "attempt-checked", harness.plan.run_id,
        keep={"s1"},
    )
    digest = hashlib.sha256(predecessor_path.read_bytes()).hexdigest()
    runtime = _skeleton_for(harness)

    scan, block = checker._check_attempt(
        runtime, tmp_path, harness.plan.run_id, "attempt-checked",
        harness.program.program_id, expected_trace_sha256=digest,
    )

    assert scan.complete_sample_ids == ("s1",)
    assert block["rows_checked"] == 1
    assert block["rows_failing"] == 0
    assert block["trace_sha256"] == digest


def test_check_attempt_refuses_a_trace_that_does_not_match_its_pin(tmp_path, monkeypatch):
    harness = _harness(tmp_path, "checker-wrong-pin", ("s1",))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    _write_predecessor(
        _trace_lines(trace_path), tmp_path / "attempt-checked", harness.plan.run_id,
        keep={"s1"},
    )
    runtime = _skeleton_for(harness)

    with pytest.raises(ResumeRecoveryError, match="hashes to"):
        checker._check_attempt(
            runtime, tmp_path, harness.plan.run_id, "attempt-checked",
            harness.program.program_id, expected_trace_sha256="0" * 64,
        )


def test_check_attempt_unpinned_measures_without_comparing(tmp_path, monkeypatch):
    """The ``--attempt`` (unpinned) form: no ``expected_trace_sha256`` is
    given, so an arbitrary trace hash is accepted -- the read-only audit of
    an attempt whose hash is not yet pinned this mode exists for."""

    harness = _harness(tmp_path, "checker-unpinned", ("s1",))
    _runtime, _canonical, trace_path = _fly(harness, monkeypatch)
    _write_predecessor(
        _trace_lines(trace_path), tmp_path / "attempt-checked", harness.plan.run_id,
        keep={"s1"},
    )
    runtime = _skeleton_for(harness)

    scan, block = checker._check_attempt(
        runtime, tmp_path, harness.plan.run_id, "attempt-checked",
        harness.program.program_id, expected_trace_sha256=None,
    )
    assert block["rows_failing"] == 0
