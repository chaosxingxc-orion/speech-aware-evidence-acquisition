"""E10d (2026-09-29): multi-predecessor, SEAL-ONLY resume completion.

A run whose rows were all flown across several aborted attempts can be
sealed with ZERO new model contacts: no server, no slot, no client. These
tests drive the ACTUAL ``FlightRuntime`` stage sequence
(``preflight -> preprocess -> serve -> run_phases -> seal``) over a
synthetic, fully-faked adapter/session/client (``test_flight_runtime``'s own
happy-path harness) so a seal-only completion is proven end to end without
any model, server, tokenizer or network contact anywhere in this file.

The fixed roster every test here resumes over is ``_FakeAdapter``'s own
``("s1", "s2")`` (see ``test_flight_runtime.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.attempts import STATE_OPENED
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError

from test_flight_resume_recovery import _harness, _fly, _trace_lines, _values, _write_predecessor
from test_flight_runtime import _make_runtime
# Module-scoped fixture the harness's transport identity needs (mirrors
# test_flight_resume_recovery.py's own import of it): copies the python
# interpreter to a llama-server-shaped path and has it hold an ephemeral
# socket. No model, no resident service, no request ever leaves this process.
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


def _predecessor_dir(tmp_path: Path, attempt_id: str, run_id: str = "SAEA-TEST-RUN-001") -> Path:
    return tmp_path / "data" / "runs" / run_id / attempt_id


def _register_predecessor(
    tmp_path, monkeypatch, name: str, sample_ids, *,
    attempt_id: str, run_id: str = "SAEA-TEST-RUN-001",
):
    """Fly one real native episode over ``sample_ids`` and drop its trace
    where ``_predecessor_attempt_dir`` will look for ``attempt_id`` UNDER the
    CONSUMING runtime's own ``run_id`` (never the harness's own plan.run_id --
    a predecessor trace is named after the run it belongs to, not the id its
    own throwaway harness plan happened to carry). Returns
    ``(source_harness, predecessor_trace_path, trace_sha256)``."""

    import hashlib

    source = _harness(tmp_path, name, sample_ids)
    _runtime, _canonical, trace_path = _fly(source, monkeypatch)
    predecessor_path = _write_predecessor(
        _trace_lines(trace_path), _predecessor_dir(tmp_path, attempt_id, run_id),
        run_id, keep=set(sample_ids),
    )
    digest = hashlib.sha256(predecessor_path.read_bytes()).hexdigest()
    return source, predecessor_path, digest


def _two_predecessor_runtime(tmp_path, monkeypatch, **runtime_kwargs):
    """Two predecessors, each COMPLETE for one of ``_FakeAdapter``'s two
    fixed roster samples -- their union covers the whole roster."""

    source_a, _path_a, digest_a = _register_predecessor(
        tmp_path, monkeypatch, "pred-a", ("s1",), attempt_id="attempt-aborted-a",
    )
    _source_b, _path_b, digest_b = _register_predecessor(
        tmp_path, monkeypatch, "pred-b", ("s2",), attempt_id="attempt-aborted-b",
    )
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "policy": source_a.program.program_id,
            "baseline_extra": {"native_episode": _values(source_a)["native_episode"]},
        },
        resume_from=[
            {"attempt_id": "attempt-aborted-a", "trace_sha256": digest_a},
            {"attempt_id": "attempt-aborted-b", "trace_sha256": digest_b},
        ],
        **runtime_kwargs,
    )
    return runtime


# ---------------------------------------------------------------------------
# preflight(): classification, conflict refusal, partial coverage.
# ---------------------------------------------------------------------------


def test_preflight_marks_seal_only_when_two_predecessors_cover_the_whole_roster(
    tmp_path, monkeypatch
):
    runtime = _two_predecessor_runtime(tmp_path, monkeypatch)

    receipt = runtime.preflight()

    assert runtime.is_seal_only is True
    assert runtime._flight_roster_sample_ids() == ()
    assert runtime.resume_predecessor.complete_sample_ids == ("s1", "s2")
    assert {predecessor.attempt_id for predecessor in runtime.resume_predecessors} == {
        "attempt-aborted-a", "attempt-aborted-b",
    }
    assert receipt["resume"]["seal_only"] is True
    assert receipt["resume"]["counts"] == {
        "roster": 2, "kept": 2, "flown": 0, "partial": 0, "unstarted": 0,
    }
    assert receipt["resume"]["worst_case_contacts"] == 0
    assert {p["attempt_id"] for p in receipt["resume"]["predecessors"]} == {
        "attempt-aborted-a", "attempt-aborted-b",
    }
    # No singular top-level fields for a multi-predecessor resume.
    assert "attempt_id" not in receipt["resume"]


def test_preflight_refuses_two_predecessors_that_overlap(tmp_path, monkeypatch):
    """Both predecessors flew s1 to completion -- a conflict, refused before
    any contact rather than silently keeping the first-declared one."""

    _source_a, _path_a, digest_a = _register_predecessor(
        tmp_path, monkeypatch, "pred-a", ("s1", "s2"), attempt_id="attempt-aborted-a",
    )
    source_b, _path_b, digest_b = _register_predecessor(
        tmp_path, monkeypatch, "pred-b", ("s1",), attempt_id="attempt-aborted-b",
    )
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "policy": source_b.program.program_id,
            "baseline_extra": {"native_episode": _values(source_b)["native_episode"]},
        },
        resume_from=[
            {"attempt_id": "attempt-aborted-a", "trace_sha256": digest_a},
            {"attempt_id": "attempt-aborted-b", "trace_sha256": digest_b},
        ],
    )
    with pytest.raises(FlightRuntimeError, match="attempt-aborted-a.*attempt-aborted-b|attempt-aborted-b.*attempt-aborted-a"):
        runtime.preflight()


def test_preflight_reports_an_incomplete_predecessor_row_and_stays_partial(
    tmp_path, monkeypatch
):
    """One predecessor completes s1; the other STARTED s2 but never settled
    it -- the union does not cover the roster, so this is an ordinary
    (non-seal-only) multi-predecessor resume with one row still to fly."""

    source_a, _path_a, digest_a = _register_predecessor(
        tmp_path, monkeypatch, "pred-a", ("s1",), attempt_id="attempt-aborted-a",
    )
    source_b = _harness(tmp_path, "pred-b", ("s2",))
    _runtime_b, _canonical_b, trace_path_b = _fly(source_b, monkeypatch)
    predecessor_b_path = _write_predecessor(
        _trace_lines(trace_path_b),
        _predecessor_dir(tmp_path, "attempt-aborted-b"),
        "SAEA-TEST-RUN-001", keep=set(), truncate={"s2"},
    )
    import hashlib

    digest_b = hashlib.sha256(predecessor_b_path.read_bytes()).hexdigest()
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "policy": source_a.program.program_id,
            "baseline_extra": {"native_episode": _values(source_a)["native_episode"]},
        },
        resume_from=[
            {"attempt_id": "attempt-aborted-a", "trace_sha256": digest_a},
            {"attempt_id": "attempt-aborted-b", "trace_sha256": digest_b},
        ],
    )

    receipt = runtime.preflight()

    assert runtime.is_seal_only is False
    assert runtime._flight_roster_sample_ids() == ("s2",)
    assert receipt["resume"]["seal_only"] is False
    assert receipt["resume"]["counts"] == {
        "roster": 2, "kept": 1, "flown": 1, "partial": 1, "unstarted": 0,
    }
    assert receipt["resume"]["partial_sample_ids"] == ["s2"]
    assert "terminal receipt" in receipt["resume"]["partial_reasons"]["s2"]


# ---------------------------------------------------------------------------
# The full stage sequence: no server, zero contacts, a COMPLETED manifest.
# ---------------------------------------------------------------------------


def test_seal_only_stages_do_zero_work_and_open_no_session(tmp_path, monkeypatch):
    runtime = _two_predecessor_runtime(tmp_path, monkeypatch)
    runtime.preflight()

    preprocess_receipt = runtime.preprocess()
    serve_receipt = runtime.serve()
    run_phases_receipt = runtime.run_phases()

    assert preprocess_receipt["seal_only"] is True
    assert serve_receipt["seal_only"] is True
    assert run_phases_receipt["seal_only"] is True
    # No session/transport was ever opened.
    assert runtime._session is None
    assert runtime._transport is None
    assert runtime._client is None


def test_seal_only_completion_opens_the_attempt_with_zero_actual_and_an_empty_trace(
    tmp_path, monkeypatch
):
    runtime = _two_predecessor_runtime(tmp_path, monkeypatch)
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()

    seal_result = runtime.seal()

    # This attempt itself flew zero rows; the TOTAL sealed (every row kept
    # from a predecessor) is reported under resume.sealed_row_count instead.
    assert seal_result["outputs_row_count"] == 0
    assert seal_result["resume"]["sealed_row_count"] == 2
    rows = [
        json.loads(line)
        for line in Path(seal_result["outputs_path"]).read_text(encoding="utf-8").splitlines()
    ]
    assert {row["sample_id"] for row in rows} == {"s1", "s2"}

    attempt_path = tmp_path / "data" / "attempts" / "SAEA-TEST-RUN-001" / "attempt-001.json"
    attempt_document = json.loads(attempt_path.read_text(encoding="utf-8"))
    assert attempt_document["state"] == STATE_OPENED
    assert attempt_document["actual"] == {"calls": 0, "audio_seconds": 0.0}
    assert attempt_document["reserved"]["calls"] > 0

    run_dir = tmp_path / "data" / "runs" / "SAEA-TEST-RUN-001" / "attempt-001"
    trace_path = run_dir / "SAEA-TEST-RUN-001.trace.jsonl"
    trace_manifest_path = run_dir / "SAEA-TEST-RUN-001.trace-manifest.json"
    assert trace_path.is_file()
    assert trace_path.read_bytes() == b""
    trace_manifest = json.loads(trace_manifest_path.read_text(encoding="utf-8"))
    assert trace_manifest["records"] == {}


def test_seal_only_manifest_declares_every_predecessor(tmp_path, monkeypatch):
    """The manifest_builder seam receives ``predecessor_attempts`` (plural,
    two entries) for a two-predecessor resume, and the RunResult it built
    from carries a zero-contact cost block."""

    captured: dict[str, object] = {}
    from test_flight_runtime import _fake_manifest_builder

    def _capturing_manifest_builder(**kwargs):
        captured.update(kwargs)
        return _fake_manifest_builder(**kwargs)

    runtime = _two_predecessor_runtime(
        tmp_path, monkeypatch, manifest_builder=_capturing_manifest_builder,
    )
    runtime.preflight()
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    runtime.seal()

    assert captured["status"] == "COMPLETED"
    assert "predecessor_attempt" not in captured
    blocks = captured["predecessor_attempts"]
    assert {block["attempt_id"] for block in blocks} == {
        "attempt-aborted-a", "attempt-aborted-b",
    }
    result = captured["result"]
    assert result.cost == {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
        "tool_calls": 0,
        "umbrella_lock_sha256": None,
    }


def test_seal_only_manifest_uses_the_singular_field_for_one_predecessor(
    tmp_path, monkeypatch
):
    """A seal-only completion is not exclusive to N>1: ONE predecessor whose
    COMPLETE rows already cover the whole roster also seals with zero
    contacts, and keeps the byte-identical singular manifest field."""

    source_a, _path_a, digest_a = _register_predecessor(
        tmp_path, monkeypatch, "pred-solo", ("s1", "s2"), attempt_id="attempt-aborted-solo",
    )
    captured: dict[str, object] = {}
    from test_flight_runtime import _fake_manifest_builder

    def _capturing_manifest_builder(**kwargs):
        captured.update(kwargs)
        return _fake_manifest_builder(**kwargs)

    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={
            "policy": source_a.program.program_id,
            "baseline_extra": {"native_episode": _values(source_a)["native_episode"]},
        },
        resume_from={"attempt_id": "attempt-aborted-solo", "trace_sha256": digest_a},
        manifest_builder=_capturing_manifest_builder,
    )
    runtime.preflight()
    assert runtime.is_seal_only is True
    runtime.preprocess()
    runtime.serve()
    runtime.run_phases()
    runtime.seal()

    assert captured["predecessor_attempt"]["attempt_id"] == "attempt-aborted-solo"
    assert "predecessor_attempts" not in captured
