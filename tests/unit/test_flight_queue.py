"""Unit tests for ``core.flight.queue.FlightQueue`` (C4c).

Drives real ``FlightRuntime`` instances (their own model/GPU/network-facing
seams all faked -- see ``test_flight_runtime.py``'s own module docstring for
the same discipline) through a real ``FlightQueue`` to prove: ready-first,
same-geometry-preferring scheduling; a ``dry_run`` flag that stops every
flight after ``preflight()``; and that official scoring is handed to a
background pool rather than blocking the next flight's own stages.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Mapping

import pytest

from speech_aware_evidence_acquisition.core.flight.queue import FlightQueue, FlightQueueError
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter

# ---------------------------------------------------------------------------
# Fakes (module-local copies -- see test_flight_runtime.py for the same
# shapes with more extensive commentary).
# ---------------------------------------------------------------------------


class _FakeAudioRef:
    def __init__(self, path: str, sha256: str) -> None:
        self.path = path
        self.sha256 = sha256


class _FakeSample:
    def __init__(self, sample_id: str, audio_seconds: float = 2.0) -> None:
        self.sample_id = sample_id
        self.audio_ref = _FakeAudioRef(f"{sample_id}.wav", "0" * 64)
        self.audio_seconds = audio_seconds
        self.media_relpath = f"{sample_id}.wav"


class _FakeAdapter(TaskAdapter):
    SERVING_SLOTS = 2
    SERVING_SLOT_TOKENS = 4096
    SERVING_MAX_TOKENS = 64

    def __init__(self, lock: Mapping[str, object], root: Path) -> None:
        self._lock = lock
        self._root = Path(root)
        self.samples = (_FakeSample("s1"), _FakeSample("s2"))

    def load_split(self, split_id: str):
        return self.samples

    def build_task_contract(self, sample, obs) -> str:
        return "contract"

    def instruction(self, sample) -> str:
        return "instruction"

    def gold(self, sample) -> object:
        return "gold"

    def score_response(self, gold, response: str) -> Mapping[str, object]:
        return {"ok": True}


class _WideFakeAdapter(_FakeAdapter):
    SERVING_SLOTS = 4
    SERVING_SLOT_TOKENS = 2048
    SERVING_MAX_TOKENS = 32


class _FakeGate:
    def assert_model_touch_allowed(self, plan) -> None:
        pass


class _FakeSession:
    def __init__(self, session_id: str, host: str = "127.0.0.1", port: int = 8080, pid: int = 4242) -> None:
        self.session_id = session_id
        self.host = host
        self.port = port
        self.pid = pid


class _FakeTiming:
    """Mirrors rails.core_client.RequestTiming, including the per-request
    identity hashes core.bundle.verify_bundle requires an outputs row to
    carry (2026-09-04)."""

    def __init__(
        self,
        latency_seconds: float = 0.01,
        sample_id: str = "s1",
        request_id: str = "req-0001",
    ) -> None:
        self.latency_seconds = latency_seconds
        self.sample_id = sample_id
        self.request_id = request_id
        self.request_sha256 = "a" * 64
        self.response_sha256 = "b" * 64
        self.response_text_sha256 = hashlib.sha256(b"resp").hexdigest()


class _FakeClient:
    def complete(self, messages, **kwargs):
        """A client that cannot complete is not a client: the concurrent
        dispatcher (default workers = slots) calls this directly."""

        return "resp"

    def __init__(self, **kwargs: object) -> None:
        self.arm = kwargs.get("arm", "test-arm")
        self.timings = (
            _FakeTiming(sample_id="s1", request_id="req-0001"),
            _FakeTiming(sample_id="s2", request_id="req-0002"),
        )
        self.closed = False

    def close(self) -> Mapping[str, object]:
        self.closed = True
        return {"trace_manifest_hash": "trace-hash", "cost": {"calls_used": 1}, "arm": self.arm}


class _FakeArmResult:
    def __init__(self, sample_id: str) -> None:
        self.sample_id = sample_id
        self.arm = "test-arm"
        self.messages = []
        self.response_text = "resp"
        self.metrics = {}
        self.consumption = None


class _FakeRunSummary:
    def __init__(self, results) -> None:
        self.results = tuple(results)


class _FakeVerified:
    attempt_state = "OPENED"


class _FakeFinalizeResult:
    scores_path = Path("fake-scores.json")
    ledger_markdown_path = Path("fake-ledger.md")
    ledger_json_path = Path("fake-ledger.json")
    attempt_state = "FINALIZED"


def _fake_session_starter(**kwargs: object) -> _FakeSession:
    return _FakeSession(str(kwargs["session_id"]))


def _fake_session_stopper(session, **kwargs) -> Mapping[str, object]:
    # The session_stopper seam is faked here for the same reason every other
    # seam is (module docstring): the real core.session.stop_session
    # re-verifies a live process image and socket ownership, which a
    # _FakeSession has none of.
    return {"termination_signal": "SIGTERM", "forced": False}


def _fake_transport_factory(values, root, *, session, runtime_receipt, runtime_root):
    return object()


def _fake_runtime_receipt_loader(path: Path) -> Mapping[str, object]:
    return {"schema": "fake-runtime-receipt", "gguf_files": []}


def _fake_packet_promoter(*, adapter, data_root, samples, workers):
    return (["packet-1"], {"note": "fake"})


def _fake_payload_binding_factory(**kwargs: object) -> object:
    return object()


def _fake_manifest_builder(**kwargs: object) -> Path:
    run_dir = Path(kwargs["run_dir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    plan = kwargs["plan"]
    path = run_dir / f"{plan.run_id}.run-manifest.json"
    path.write_text(json.dumps({"schema": "fake"}), encoding="utf-8")
    return path


def _fake_bundle_verifier(manifest_path: Path) -> _FakeVerified:
    return _FakeVerified()


def _fake_ledger_validator(bundle, cells):
    """core.tracking.ledger_row_for_bundle reads a REAL VerifiedBundle; this
    double asserts the same contract the real one enforces -- every
    caller-owned column present -- without needing one."""

    missing = [
        column
        for column in FlightRuntime.CALLER_LEDGER_COLUMNS
        if column not in dict(cells or {})
    ]
    assert not missing, f"ledger row is missing {missing}"
    return ({}, dict(cells))


def _fake_bundle_finalizer(
    manifest_path, lock, root, *, repo_root, ledger_cells=None
) -> _FakeFinalizeResult:
    """The real core.bundle.finalize_bundle validates the COMPLETE 21-column
    ledger surface before it will score, so a caller supplying none of the
    twelve caller-owned columns is refused. This double asserts the same
    contract rather than ignoring the argument."""

    missing = [
        column
        for column in FlightRuntime.CALLER_LEDGER_COLUMNS
        if column not in dict(ledger_cells or {})
    ]
    assert not missing, f"finalize_bundle was given no value for {missing}"
    return _FakeFinalizeResult()


def _fake_score_batch(jobs, *, output_dir, max_workers, **_kwargs) -> Mapping[str, object]:
    """Mirrors core.scoring_batch.run_score_batch's own success shape: it
    reports per-job outcomes in the RESULT rather than raising, so a caller
    that only watches for exceptions cannot tell a green batch from a red
    one."""

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    return {
        "job_count": len(jobs),
        "succeeded": len(jobs),
        "failed": 0,
        "jobs": [
            {"job_id": getattr(job, "job_id", "j"), "status": "succeeded"}
            for job in jobs
        ],
    }


def _fake_rails_runner(**kwargs: object) -> _FakeRunSummary:
    return _FakeRunSummary((_FakeArmResult("s1"), _FakeArmResult("s2")))


# ---------------------------------------------------------------------------
# Synthetic repo/config plumbing (same shape as test_flight_runtime.py).
# ---------------------------------------------------------------------------


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True)


def _git_init_commit(repo_root: Path) -> None:
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "test snapshot")


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _write_configs(repo_root: Path, *, carrier_lock_key: str = "fake-carrier") -> None:
    _write_json(
        repo_root / "configs" / "model" / "m.json",
        {"model_lock_key": "fake-lock", "transport": "fake"},
    )
    _write_json(
        repo_root / "configs" / "dataset" / "d.json",
        {"carrier_lock_key": carrier_lock_key, "split_id": "fake-split"},
    )
    _write_json(repo_root / "configs" / "baseline" / "b.json", {"arm": "test-arm", "policy": "fixed"})
    _write_json(
        repo_root / "configs" / "experiment" / "e.json",
        {
            "execution_plan": {
                "execution_profile": "bounded-discovery-probe",
                "split_role": "discovery",
                "planned_model_calls": 10,
                "planned_gpu_hours": 1.0,
                "planned_speech_audio_seconds": 100,
            }
        },
    )


def _write_exposure_ledger(repo_root: Path, run_id: str) -> None:
    content = (
        "| run/experiment id | consumed |\n"
        "| --- | --- |\n"
        f"| {run_id} | no |\n"
    )
    path = repo_root / "docs" / "exposure-ledger.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _make_repo(tmp_path: Path, run_id: str) -> Path:
    _write_configs(tmp_path)
    _write_exposure_ledger(tmp_path, run_id)
    _git_init_commit(tmp_path)
    return tmp_path


def _make_flight(
    tmp_path: Path,
    *,
    run_id: str,
    attempt_id: str,
    adapter_cls: type = _FakeAdapter,
    **runtime_kwargs: object,
) -> FlightRuntime:
    repo_root = _make_repo(tmp_path / run_id, run_id)
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    merged: dict[str, object] = {
        "session_starter": _fake_session_starter,
        "session_stopper": _fake_session_stopper,
        "transport_factory": _fake_transport_factory,
        "runtime_receipt_loader": _fake_runtime_receipt_loader,
        "packet_promoter": _fake_packet_promoter,
        "payload_binding_factory": _fake_payload_binding_factory,
        "carrier_root_resolver": lambda lock, carrier_lock_key, data_root: Path(data_root) / carrier_lock_key,
        "client_factory": _FakeClient,
        "manifest_builder": _fake_manifest_builder,
        "bundle_verifier": _fake_bundle_verifier,
        "bundle_finalizer": _fake_bundle_finalizer,
        "ledger_validator": _fake_ledger_validator,
        "score_batch": _fake_score_batch,
        "rails_runner": _fake_rails_runner,
    }
    merged.update(runtime_kwargs)
    return FlightRuntime(
        repo_root,
        data_root,
        model="m",
        dataset="d",
        baseline="b",
        experiment="e",
        run_id=run_id,
        attempt_id=attempt_id,
        runtime_root=tmp_path / "runtime",
        adapter_factory=lambda lock, root: adapter_cls(lock, root),
        gate_factory=lambda *a, **kw: _FakeGate(),
        lock={},
        **merged,
    )


def _open_attempt_for_failure(flight: FlightRuntime) -> None:
    """Model the one-time reservation made by the real core client.

    The queue fakes intentionally avoid the real request path, so they need
    this explicit reservation before they can prove that failure cleanup
    aborts an OPENED attempt.
    """

    from speech_aware_evidence_acquisition.core.attempts.store import AttemptStore

    plan = flight._plan
    assert plan is not None
    AttemptStore(flight._data_root / "attempts").open_attempt(
        plan.run_id,
        plan.attempt_id,
        carrier_lock_key="fake-carrier",
        reserved_calls=10,
        reserved_audio_seconds=100.0,
    )


# ---------------------------------------------------------------------------
# Tests.
# ---------------------------------------------------------------------------


def test_queue_prefers_same_geometry_flights_over_earlier_arrivals(tmp_path):
    order: list[str] = []

    def _tracking_client_factory(**kwargs):
        # Dispatch order is tracked at client construction, not at the
        # rails_runner seam: with the default concurrent dispatch
        # (workers = slots) a fixed-policy flight never reaches that seam.
        order.append(kwargs["plan"].run_id)
        return _FakeClient(**kwargs)

    starts = {"count": 0}

    def _counting_session_starter(**kwargs):
        starts["count"] += 1
        return _FakeSession(str(kwargs["session_id"]))

    flight_a = _make_flight(
        tmp_path, run_id="SAEA-Q-NARROW-A", attempt_id="attempt-a", adapter_cls=_FakeAdapter,
        client_factory=_tracking_client_factory, session_starter=_counting_session_starter,
    )
    flight_b = _make_flight(
        tmp_path, run_id="SAEA-Q-WIDE-B", attempt_id="attempt-b", adapter_cls=_WideFakeAdapter,
        client_factory=_tracking_client_factory, session_starter=_counting_session_starter,
    )
    flight_c = _make_flight(
        tmp_path, run_id="SAEA-Q-NARROW-C", attempt_id="attempt-c", adapter_cls=_FakeAdapter,
        client_factory=_tracking_client_factory, session_starter=_counting_session_starter,
    )

    queue = FlightQueue([flight_a, flight_b, flight_c])
    entries = queue.run()

    assert [entry.flight.run_id for entry in entries] == [
        "SAEA-Q-NARROW-A",
        "SAEA-Q-NARROW-C",
        "SAEA-Q-WIDE-B",
    ]
    assert order == ["SAEA-Q-NARROW-A", "SAEA-Q-NARROW-C", "SAEA-Q-WIDE-B"]
    # Only two real server starts: A's narrow geometry, then B's wide one --
    # C reuses A's still-resident narrow server.
    assert starts["count"] == 2
    queue.drain_scores()
    queue.shutdown()


def test_queue_dry_run_stops_every_flight_after_preflight(tmp_path):
    flight_a = _make_flight(tmp_path, run_id="SAEA-Q-DRY-A", attempt_id="attempt-a")
    flight_b = _make_flight(tmp_path, run_id="SAEA-Q-DRY-B", attempt_id="attempt-b")

    queue = FlightQueue([flight_a, flight_b], dry_run=True)
    entries = queue.run()

    assert len(entries) == 2
    assert all(entry.dry_run for entry in entries)
    assert flight_a.receipts.completed_stages() == ("preflight",)
    assert flight_b.receipts.completed_stages() == ("preflight",)
    queue.shutdown()


def test_queue_overlaps_scoring_with_the_next_flights_generation(tmp_path):
    score_started = threading.Event()
    score_release = threading.Event()

    def _blocking_score_batch(jobs, *, output_dir, max_workers, **_kwargs):
        score_started.set()
        assert score_release.wait(timeout=5), "score_release was never set by the test"
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        return {"job_count": len(jobs)}

    flight_a = _make_flight(
        tmp_path, run_id="SAEA-Q-OVERLAP-A", attempt_id="attempt-a", score_batch=_blocking_score_batch
    )
    flight_b = _make_flight(tmp_path, run_id="SAEA-Q-OVERLAP-B", attempt_id="attempt-b")

    queue = FlightQueue([flight_a, flight_b])
    entries = queue.run()

    # run() must not have blocked on flight A's still-running background
    # score: both flights' own stages (serve/run_phases/seal) completed
    # (proven by run() having already returned) while flight A's score is
    # either still pending or only just starting in the background pool
    # thread -- wait (bounded) for it to actually start rather than racing
    # against thread-pool scheduling.
    assert score_started.wait(timeout=5)
    assert len(entries) == 2
    assert entries[0].flight.run_id == "SAEA-Q-OVERLAP-A"
    assert entries[0].score_future is not None
    assert not entries[0].score_future.done()
    assert entries[1].flight.receipts.has("seal")
    assert entries[1].score_future is not None and not entries[1].score_future.done()

    score_release.set()
    results = queue.drain_scores()
    assert len(results) == 2
    assert all(result is not None for result in results)
    queue.shutdown()


# ---------------------------------------------------------------------------
# Phase 2b: one resident server at a time, per geometry.
# ---------------------------------------------------------------------------


def test_queue_stops_the_resident_server_before_a_geometry_change(tmp_path):
    events: list[str] = []

    def _tracking_session_starter(**kwargs):
        events.append("start:%s" % kwargs["session_id"])
        return _FakeSession(str(kwargs["session_id"]))

    def _tracking_stopper(session, **kwargs):
        events.append("stop:%s" % session.session_id)
        return {"termination_signal": "SIGTERM", "forced": False}

    narrow = _make_flight(
        tmp_path,
        run_id="SAEA-TEST-NARROW",
        attempt_id="attempt-narrow",
        adapter_cls=_FakeAdapter,
        session_starter=_tracking_session_starter,
        session_stopper=_tracking_stopper,
    )
    wide = _make_flight(
        tmp_path,
        run_id="SAEA-TEST-WIDE",
        attempt_id="attempt-wide",
        adapter_cls=_WideFakeAdapter,
        session_starter=_tracking_session_starter,
        session_stopper=_tracking_stopper,
    )
    queue = FlightQueue([narrow, wide])
    queue.run()
    queue.drain_scores()
    queue.shutdown()

    starts = [event for event in events if event.startswith("start:")]
    stops = [event for event in events if event.startswith("stop:")]
    assert len(starts) == 2
    assert len(stops) == 2
    # The first server is stopped BEFORE the second geometry's server starts:
    # two 18.5 GB servers do not fit in this host's VRAM.
    assert events.index(stops[0]) < events.index(starts[1])
    assert stops[0].endswith("attempt-narrow")


def test_queue_does_not_stop_a_server_it_keeps_reusing(tmp_path):
    events: list[str] = []

    def _tracking_session_starter(**kwargs):
        events.append("start")
        return _FakeSession(str(kwargs["session_id"]))

    def _tracking_stopper(session, **kwargs):
        events.append("stop")
        return {"termination_signal": "SIGTERM"}

    flights = [
        _make_flight(
            tmp_path,
            run_id="SAEA-TEST-%d" % index,
            attempt_id="attempt-%d" % index,
            session_starter=_tracking_session_starter,
            session_stopper=_tracking_stopper,
        )
        for index in (1, 2)
    ]
    queue = FlightQueue(flights)
    queue.run()
    queue.drain_scores()

    # Same geometry: one start, and nothing stopped while flights remain.
    assert events == ["start"]
    queue.shutdown()
    assert events == ["start", "stop"]


def test_queue_shutdown_stops_the_last_resident_server(tmp_path):
    stops: list[str] = []

    def _tracking_stopper(session, **kwargs):
        stops.append(session.session_id)
        return {"termination_signal": "SIGTERM"}

    flight = _make_flight(
        tmp_path,
        run_id="SAEA-TEST-ONLY",
        attempt_id="attempt-only",
        session_stopper=_tracking_stopper,
    )
    queue = FlightQueue([flight])
    queue.run()
    queue.drain_scores()
    assert stops == []
    queue.shutdown()
    assert len(stops) == 1
    # Idempotent.
    queue.shutdown()
    assert len(stops) == 1


def test_dry_run_queue_starts_and_stops_nothing(tmp_path):
    events: list[str] = []

    def _tracking_session_starter(**kwargs):
        events.append("start")
        return _FakeSession(str(kwargs["session_id"]))

    def _tracking_stopper(session, **kwargs):
        events.append("stop")
        return {}

    flight = _make_flight(
        tmp_path,
        run_id="SAEA-TEST-DRY",
        attempt_id="attempt-dry",
        session_starter=_tracking_session_starter,
        session_stopper=_tracking_stopper,
    )
    queue = FlightQueue([flight], dry_run=True)
    queue.run()
    queue.shutdown()
    assert events == []


def test_queue_aborts_generation_failure_before_releasing_execution_context(tmp_path):
    events: list[str] = []
    active: list[bool] = []
    stops: list[str] = []
    abort_results: list[bool] = []

    def tracking_stopper(session, **kwargs):
        stops.append(session.session_id)
        return {"termination_signal": "SIGTERM"}

    flight = _make_flight(
        tmp_path,
        run_id="SAEA-Q-ABORT-ORDER",
        attempt_id="attempt-abort-order",
        session_stopper=tracking_stopper,
    )

    @contextmanager
    def context(_flight):
        events.append("context-enter")
        active.append(True)
        try:
            yield
        except Exception:
            events.append("context-exit-error")
            raise
        finally:
            active.pop()

    original_run_phases = flight.run_phases

    def fail_after_opening_attempt():
        original_run_phases()
        _open_attempt_for_failure(flight)
        events.append("run-phases-failed")
        raise RuntimeError("generation failed")

    original_abort = flight.abort

    def abort(reason: str):
        assert active
        events.append("abort")
        result = original_abort(reason)
        abort_results.append(result)
        return result

    flight.run_phases = fail_after_opening_attempt
    flight.abort = abort
    queue = FlightQueue([flight], execution_context_factory=context)

    with pytest.raises(RuntimeError, match="generation failed"):
        queue.run()

    assert events == [
        "context-enter",
        "run-phases-failed",
        "abort",
        "context-exit-error",
    ]
    assert abort_results == [True]
    assert queue.states[flight.run_id].state == "failed"
    queue.shutdown()
    assert stops == []


def test_queue_aborts_seal_failure_before_releasing_execution_context(tmp_path):
    events: list[str] = []
    active: list[bool] = []
    flight = _make_flight(tmp_path, run_id="SAEA-Q-ABORT-SEAL", attempt_id="attempt-abort-seal")

    @contextmanager
    def context(_flight):
        events.append("context-enter")
        active.append(True)
        try:
            yield
        except Exception:
            events.append("context-exit-error")
            raise
        finally:
            active.pop()

    def fail_finalization(*args, **kwargs):
        _open_attempt_for_failure(flight)
        events.append("seal-failed")
        raise RuntimeError("seal failed")

    original_abort = flight.abort

    def abort(reason: str):
        assert active
        events.append("abort")
        return original_abort(reason)

    flight._bundle_finalizer = fail_finalization
    flight.abort = abort
    queue = FlightQueue([flight], execution_context_factory=context)

    with pytest.raises(RuntimeError, match="seal failed"):
        queue.run()

    assert events == ["context-enter", "seal-failed", "abort", "context-exit-error"]
    assert queue.states[flight.run_id].state == "failed"


def test_queue_preserves_generation_error_when_abort_fails(tmp_path):
    flight = _make_flight(tmp_path, run_id="SAEA-Q-ABORT-PRIMARY", attempt_id="attempt-abort-primary")
    original_run_phases = flight.run_phases

    def fail_after_opening_attempt():
        original_run_phases()
        _open_attempt_for_failure(flight)
        raise ValueError("primary generation failure")

    def fail_abort(reason: str):
        assert "ValueError" in reason
        raise RuntimeError("abort failure")

    flight.run_phases = fail_after_opening_attempt
    flight.abort = fail_abort
    queue = FlightQueue([flight])

    with pytest.raises(ValueError, match="primary generation failure") as raised:
        queue.run()

    assert any("abort failure" in note for note in raised.value.__notes__)
    assert queue.states[flight.run_id].state == "failed"


def test_queue_does_not_abort_or_stop_coordinator_service_after_scoring_failure(tmp_path):
    stops: list[str] = []
    aborts: list[str] = []

    @contextmanager
    def coordinator_context(_flight):
        yield

    def tracking_stopper(session, **kwargs):
        stops.append(session.session_id)
        return {"termination_signal": "SIGTERM"}

    flight = _make_flight(
        tmp_path,
        run_id="SAEA-Q-SCORE-FAILURE",
        attempt_id="attempt-score-failure",
        session_stopper=tracking_stopper,
    )

    def abort(reason: str):
        aborts.append(reason)
        return False

    def fail_score(**kwargs):
        raise RuntimeError("scoring failed")

    flight.abort = abort
    flight.score = fail_score
    queue = FlightQueue([flight], execution_context_factory=coordinator_context)
    entry = queue.run()[0]

    with pytest.raises(RuntimeError, match="scoring failed"):
        entry.score_future.result()
    queue.shutdown()

    assert aborts == []
    assert stops == []


def test_completed_score_failure_refuses_next_admission(tmp_path):
    def fail_score(jobs, **kwargs):
        raise RuntimeError("synthetic official score failure")
    first=_make_flight(tmp_path,run_id="SAEA-SCORE-FAIL-A",attempt_id="a",score_batch=fail_score)
    second=_make_flight(tmp_path,run_id="SAEA-SCORE-FAIL-B",attempt_id="b")
    queue=FlightQueue([first,second])
    try:
        (completed,)=queue.run(max_flights=1)
        with pytest.raises(RuntimeError):completed.score_future.result(timeout=5)
        with pytest.raises(FlightQueueError,match="official scoring failed"):
            queue.run()
        assert first.receipts.has("seal") and not second.receipts.has("seal")
        assert queue.states[first.run_id].state=="failed"
    finally:queue.shutdown()


def test_delayed_score_failure_stops_after_current_generation_settles(tmp_path):
    started,release=threading.Event(),threading.Event()
    def fail_score(jobs, **kwargs):
        started.set()
        assert release.wait(timeout=5)
        raise RuntimeError("delayed synthetic official score failure")
    first=_make_flight(tmp_path,run_id="SAEA-DELAYED-FAIL-A",attempt_id="a",score_batch=fail_score)
    second=_make_flight(tmp_path,run_id="SAEA-DELAYED-FAIL-B",attempt_id="b")
    third=_make_flight(tmp_path,run_id="SAEA-DELAYED-FAIL-C",attempt_id="c")
    queue=FlightQueue([first,second,third])
    original=second.seal
    def settle_then_release():
        result=original()
        assert started.wait(timeout=5)
        release.set()
        with pytest.raises(RuntimeError):queue.completed[0].score_future.result(timeout=5)
        return result
    second.seal=settle_then_release
    try:
        with pytest.raises(FlightQueueError,match="official scoring failed"):
            queue.run()
        assert first.receipts.has("seal") and second.receipts.has("seal")
        assert not third.receipts.has("seal")
        assert len(queue.completed)==2
        assert queue.states[first.run_id].state=="failed"
    finally:
        release.set()
        queue.shutdown()
    assert second.receipts.has("score")
