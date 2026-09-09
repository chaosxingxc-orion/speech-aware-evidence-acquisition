"""Coordinator capabilities guard the existing flight harness; no live endpoints."""
import pytest

from speech_aware_evidence_acquisition.core.flight.lease import (
    GenerationLease, GenerationLeaseError, WorkerExecutionPolicy,
)
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError
from test_flight_runtime import (
    _make_runtime, _serving_world, _serving_runtime, _write_serving_session,
    _SERVING_RUN_ID,
)


def _lease(data_root, session="serving-test"):
    return GenerationLease.acquire(
        data_root, owner="root", run_id=_SERVING_RUN_ID, attempt_id="attempt-serving",
        session_id=session, study_head="a" * 40,
    )


def test_worker_cannot_autostart_without_resident(tmp_path):
    repo, _, data = _serving_world(tmp_path)
    with _lease(data) as lease:
        runtime, starter, attached = _serving_runtime(
            tmp_path, repo,
            execution_policy=WorkerExecutionPolicy("serving-test", lease.token),
        )
        runtime.preflight()
        runtime.preprocess()
        with pytest.raises(GenerationLeaseError, match="resident"):
            runtime.serve()
    assert starter.calls == 0
    assert attached == []


def test_worker_rejects_different_session_before_attach(tmp_path):
    repo, runtime_root, data = _serving_world(tmp_path)
    _write_serving_session(repo, runtime_root, data, session_id="unexpected")
    with _lease(data) as lease:
        runtime, starter, attached = _serving_runtime(
            tmp_path, repo,
            execution_policy=WorkerExecutionPolicy("serving-test", lease.token),
        )
        runtime.preflight()
        runtime.preprocess()
        with pytest.raises(GenerationLeaseError, match="session"):
            runtime.serve()
    assert starter.calls == 0
    assert attached == []


def test_worker_attaches_but_cannot_generate_after_owner_releases(tmp_path):
    repo, runtime_root, data = _serving_world(tmp_path)
    _write_serving_session(repo, runtime_root, data)
    with _lease(data) as lease:
        runtime, starter, attached = _serving_runtime(
            tmp_path, repo,
            execution_policy=WorkerExecutionPolicy("serving-test", lease.token),
        )
        runtime.preflight()
        runtime.preprocess()
        runtime.serve()
        assert runtime.stop_serving() is None
    with pytest.raises(GenerationLeaseError):
        runtime.run_phases()
    assert starter.calls == 0
    assert len(attached) == 1
    assert runtime._client is None


def test_in_process_reuse_checks_full_profile_not_geometry_only(tmp_path):
    first = _make_runtime(tmp_path, happy_path=True)
    second = _make_runtime(
        tmp_path / "second", happy_path=True,
        config_kwargs={"model_extra": {"server_env": {"CACHE_MODE": "other"}}},
    )
    first.preflight()
    first.preprocess()
    first.serve()
    second.preflight()
    second.preprocess()
    with pytest.raises(FlightRuntimeError, match="identity"):
        second.serve(reuse=first)


def test_worker_transport_refuses_later_contact_after_lease_release(tmp_path):
    from speech_aware_evidence_acquisition.core.session.worker import LeaseCheckedTransport
    calls = []
    class Transport:
        base_url = "fake"
        def __call__(self, payload):
            calls.append(payload)
            return b"ok"
    with _lease(tmp_path) as lease:
        policy = WorkerExecutionPolicy("serving-test", lease.token)
        transport = LeaseCheckedTransport(
            Transport(), lambda: policy.assert_lease(
                tmp_path, run_id=_SERVING_RUN_ID, attempt_id="attempt-serving",
            ),
        )
        assert transport.base_url == "fake"
        assert transport(b"first") == b"ok"
    with pytest.raises(GenerationLeaseError):
        transport(b"second")
    assert calls == [b"first"]


def test_session_identity_can_be_prepared_before_preflight(tmp_path):
    repo, _, _ = _serving_world(tmp_path)
    runtime, starter, attached = _serving_runtime(tmp_path, repo)
    identity = runtime.session_required_identity()
    assert identity["model_fragment"] == "m"
    assert starter.calls == 0
    assert attached == []
