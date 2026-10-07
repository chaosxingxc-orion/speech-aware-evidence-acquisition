"""Resource safety is operational; no model, CUDA or Windows contact in tests."""

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.session import resource_guard as guard

LIMITS = {
    "schema": "saea-serving-resource-limits-v1",
    "windows_start_gib": 32.0,
    "windows_admit_gib": 12.0,
    "windows_stop_gib": 10.0,
    "gpu_admit_free_mib": 2048.0,
    "gpu_stop_free_mib": 1024.0,
    "max_sample_age_seconds": 15.0,
}
SESSION = SimpleNamespace(
    session_id="serving-fixture", pid=123, started_at="2026-09-26T00:00:00Z"
)


def sample(tmp_path, *, host=20, gpu=4000, now=100):
    doc = guard.publish_sample(
        tmp_path,
        SESSION,
        LIMITS,
        now=lambda: now,
        host_reader=lambda: {"host_free_gb": host, "vm_available_gb": 35},
        gpu_reader=lambda: {
            "memory_free_mib": gpu,
            "memory_used_mib": 20000,
            "memory_total_mib": 24463,
        },
    )
    # Preserve the historical v1 receipt cases; v2 boot-clock cases live in
    # test_serving_resource_clock.py and use the current publisher unchanged.
    doc["schema"] = guard.LEGACY_SCHEMA
    doc.pop("elapsed_clock")
    (tmp_path / guard.SNAPSHOT_NAME).write_text(json.dumps(doc))
    return doc


@pytest.mark.parametrize(
    "host,gpu,decision",
    [
        (20, 4000, "admit"),
        (12, 2048, "admit"),
        (11.9, 4000, "drain"),
        (10, 4000, "drain"),
        (9.9, 4000, "stop"),
        (20, 1500, "drain"),
        (20, 999, "stop"),
        (None, 4000, "stop"),
        (True, 4000, "stop"),
        (float("nan"), 4000, "stop"),
        (20, None, "stop"),
    ],
)
def test_observation_drives_admission(tmp_path, host, gpu, decision):
    doc = sample(tmp_path, host=host, gpu=gpu)
    assert doc["decision"] == decision
    if decision == "admit":
        guard.assert_admission(tmp_path, SESSION, LIMITS, now=lambda: 102)
    else:
        with pytest.raises(guard.ResourceAdmissionError):
            guard.assert_admission(tmp_path, SESSION, LIMITS, now=lambda: 102)


@pytest.mark.parametrize(
    "change", ["stale", "future", "pid", "start", "policy", "missing", "corrupt"]
)
def test_stale_or_wrong_resource_receipt_cannot_admit(tmp_path, change):
    sample(tmp_path)
    path = tmp_path / guard.SNAPSHOT_NAME
    doc = json.loads(path.read_text())
    now = 100
    if change == "stale":
        now = 116
    elif change == "future":
        now = 99
    elif change == "pid":
        doc["session"]["pid"] += 1
    elif change == "start":
        doc["session"]["started_at"] = "another"
    elif change == "policy":
        doc["policy_sha256"] = "0" * 64
    elif change == "missing":
        path.unlink()
    elif change == "corrupt":
        path.write_text("{")
    if change not in {"missing", "corrupt"}:
        path.write_text(json.dumps(doc))
    with pytest.raises(guard.ResourceAdmissionError):
        guard.assert_admission(tmp_path, SESSION, LIMITS, now=lambda: now)


def test_policy_is_opt_in_and_strict():
    assert guard.resource_limits({}) is None
    assert guard.resource_limits({"serving_resource_limits": LIMITS}) == LIMITS
    for field, value in [
        ("windows_stop_gib", 3.99),
        ("windows_admit_gib", 9),
        ("windows_start_gib", 11),
        ("gpu_admit_free_mib", 999),
        ("max_sample_age_seconds", float("inf")),
        ("windows_stop_gib", True),
    ]:
        with pytest.raises(guard.ResourceAdmissionError):
            guard.resource_limits({"serving_resource_limits": {**LIMITS, field: value}})
    with pytest.raises(guard.ResourceAdmissionError):
        guard.resource_limits({"serving_resource_limits": {**LIMITS, "unknown": 1}})


def test_cold_start_requires_loading_headroom_and_readable_windows():
    for free in [None, 31.9]:
        with pytest.raises(guard.ResourceAdmissionError):
            guard.assert_start(LIMITS, host_reader=lambda: {"host_free_gb": free})
    guard.assert_start(LIMITS, host_reader=lambda: {"host_free_gb": 32})


def test_pressure_latches_until_a_new_service_identity(tmp_path):
    sample(tmp_path, host=11)
    doc = sample(tmp_path, host=20, now=102)
    assert doc["decision"] == "drain"
    assert doc["observed_decision"] == "admit"
    with pytest.raises(guard.ResourceAdmissionError):
        guard.assert_admission(tmp_path, SESSION, LIMITS, now=lambda: 102)
    assert len((tmp_path / guard.LOG_NAME).read_text().splitlines()) == 2


def test_sampling_latency_is_included_in_freshness(tmp_path):
    times = iter([100, 117])
    doc = guard.publish_sample(
        tmp_path,
        SESSION,
        LIMITS,
        now=lambda: 100,
        elapsed_clock=lambda: next(times),
        host_reader=lambda: {"host_free_gb": 30},
        gpu_reader=lambda: {"memory_free_mib": 5000},
    )
    assert doc["decision"] == "stop"
    assert "observation-too-old" in doc["reasons"]


def test_guarded_transport_has_zero_post_when_receipt_is_bad(tmp_path):
    calls = []

    class Transport:
        def __call__(self, raw):
            calls.append(raw)
            return b"response"

        def render_request(self, raw):
            return {"unchanged": raw.decode()}

    wrapped = guard.ResourceCheckedTransport(
        Transport(), tmp_path, SESSION, LIMITS, now=lambda: 100
    )
    assert wrapped.render_request(b"request") == {"unchanged": "request"}
    with pytest.raises(guard.ResourceAdmissionError):
        wrapped(b"request")
    assert calls == []
    sample(tmp_path)
    assert wrapped(b"request") == b"response"
    assert calls == [b"request"]


def test_configured_transport_enforces_real_dispatch_boundary(tmp_path):
    from speech_aware_evidence_acquisition.core.configured_transport import (
        build_configured_transport,
    )
    from speech_aware_evidence_acquisition.core.session.serving import (
        serving_session_dir,
    )

    calls = []
    transport = build_configured_transport(
        {"transport": "llama-server", "serving_resource_limits": LIMITS},
        tmp_path,
        repo_root=tmp_path,
        session=SESSION,
        runtime_receipt={},
        runtime_root=tmp_path,
        transport_factory=lambda *a, **k: lambda raw: calls.append(raw) or b"ok",
    )
    with pytest.raises(guard.ResourceAdmissionError):
        transport(b"same-request")
    assert not calls
    import time

    sample(serving_session_dir(tmp_path, SESSION.session_id), now=time.time())
    assert transport(b"same-request") == b"ok"


def test_runtime_tokenizer_guard_shares_resource_admission(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.core.preparation_fit import GuardedTokenizer

    state = SimpleNamespace(
        _execution_policy=None,
        _composed=SimpleNamespace(values={"serving_resource_limits": LIMITS}),
        _session=SESSION,
        _serving_session_dir=tmp_path,
        _data_root=tmp_path,
    )
    calls = []
    tokenizer = GuardedTokenizer(
        SimpleNamespace(request_json=lambda *a: calls.append(a)),
        guard=lambda: FlightRuntime.assert_generation_lease(state),
        contact_cap=4,
    )
    with pytest.raises(guard.ResourceAdmissionError):
        tokenizer.request_json("POST", "/tokenize", {"content": "same"})
    assert calls == [] and tokenizer.counts.total() == 0


def test_service_owner_stops_on_hard_floor_without_restarting(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.session import serving, lifecycle
    import speech_aware_evidence_acquisition.core.session as session_api

    monkeypatch.setattr(lifecycle, "reap_child", lambda pid: (False, None))
    states = iter(["running", "gone"])
    monkeypatch.setattr(serving, "process_state", lambda pid: next(states, "gone"))
    monkeypatch.setattr(guard, "_host", lambda: {"host_free_gb": 9})
    monkeypatch.setattr(guard, "_gpu", lambda: {"memory_free_mib": 4000})
    monkeypatch.setattr(serving, "_read_explicit_stop_document", lambda *a, **k: None)
    stops = []
    monkeypatch.setattr(
        session_api, "stop_session", lambda s, **k: stops.append(s.pid) or {}
    )
    result = serving._hold_session_open(
        SimpleNamespace(runtime_root=tmp_path),
        profile={"runtime_receipt": {}, "values": {"serving_resource_limits": LIMITS}},
        session=SESSION,
        session_id=SESSION.session_id,
        session_dir=tmp_path,
        monitor_path=tmp_path / "monitor.jsonl",
    )
    assert result == 1 and stops == [SESSION.pid]
    doc = json.loads((tmp_path / serving.SESSION_STOP_NAME).read_text())
    assert doc["server_exit"]["reason"] == "resource-guard"
    assert doc["server_exit"]["resource"]["decision"] == "stop"


def test_capacity_telemetry_extends_legacy_without_changing_it():
    from speech_aware_evidence_acquisition.core.session.telemetry import read_gpu

    seen = []

    def run(argv, **kwargs):
        seen.append(argv)
        return SimpleNamespace(
            returncode=0, stdout="90, 20000, 95, P2, 180, 24463, 4000"
        )

    doc = read_gpu(run, include_capacity=True)
    assert doc["memory_free_mib"] == 4000 and doc["memory_total_mib"] == 24463
    assert "memory.total,memory.free" in seen[0][1]


def test_cold_prepared_fit_refuses_before_first_endpoint(tmp_path):
    from test_preparation_fit import fit_fixture
    from speech_aware_evidence_acquisition.core.preparation_fit import fit_phase_runtime

    runtime, _, attach, client, kwargs = fit_fixture(tmp_path)
    runtime.preparation_context()["values"].update(
        transport="llama-server", serving_resource_limits=LIMITS
    )
    session = attach.return_value[2]
    session.session_id, session.pid, session.started_at = (
        SESSION.session_id,
        SESSION.pid,
        SESSION.started_at,
    )
    with pytest.raises(guard.ResourceAdmissionError):
        fit_phase_runtime(runtime, tmp_path / "fit.json", **kwargs)
    assert client.calls == []


def test_batch_prelaunch_log_is_json_without_extra_cuda_warmup():
    import subprocess
    from pathlib import Path

    text = (
        Path(__file__).parents[2] / "scripts/flights/batch/batch_driver.sh"
    ).read_text()
    fn = text.split("prelaunch() {", 1)[1].split("\n}", 1)[0]
    assert "gpu_warm.sh" not in fn and "gpu_ramp_test.sh" not in fn
    line = next(x for x in fn.splitlines() if 'log "prelaunch-ok"' in x)
    result = subprocess.run(
        ["bash", "-c", 'log() { printf "%s\\n" "$2"; }; set -- 2; ' + line],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout) == {
        "step": 2,
        "warmup": "registered-model-work-only",
    }


def test_guarded_profile_cannot_fallback_spawn_without_resident(tmp_path):
    from test_flight_runtime import _make_runtime
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError

    calls = []
    runtime = _make_runtime(
        tmp_path,
        happy_path=True,
        config_kwargs={"model_extra": {"serving_resource_limits": LIMITS}},
        session_starter=lambda **kw: calls.append(kw),
        serving_session_finder=lambda *a, **kw: None,
    )
    runtime.preflight()
    runtime.preprocess()
    with pytest.raises(FlightRuntimeError, match="coordinator-owned"):
        runtime.serve()
    assert calls == []


def test_new_model_keeps_request_width_with_half_total_kv():
    from pathlib import Path
    from speech_aware_evidence_acquisition.core.session.serving import (
        resolve_serving_profile,
    )

    repo = Path(__file__).parents[2]
    profile = resolve_serving_profile(
        repo, "q4km-mmproj-free-system-np2-ctx24k-resource-guard-v1"
    )
    assert profile["serving_geometry"] == {
        "slots": 2,
        "slot_tokens": 24576,
        "max_tokens": 512,
    }
    assert resource_policy(profile) == LIMITS


def resource_policy(profile):
    return guard.resource_limits(profile["values"])


def test_new_service_identity_does_not_inherit_an_old_drain(tmp_path):
    sample(tmp_path, host=11)
    new = SimpleNamespace(session_id=SESSION.session_id, pid=124, started_at="new")
    doc = guard.publish_sample(
        tmp_path,
        new,
        LIMITS,
        now=lambda: 102,
        host_reader=lambda: {"host_free_gb": 20},
        gpu_reader=lambda: {"memory_free_mib": 4000},
    )
    assert doc["decision"] == "admit"
    guard.assert_admission(tmp_path, new, LIMITS, now=lambda: 102)


def test_unreadable_resource_observer_stops_the_owned_service(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.session import serving, lifecycle
    import speech_aware_evidence_acquisition.core.session as session_api

    monkeypatch.setattr(lifecycle, "reap_child", lambda pid: (False, None))
    states = iter(["running", "gone"])
    monkeypatch.setattr(serving, "process_state", lambda pid: next(states, "gone"))
    monkeypatch.setattr(
        guard,
        "publish_sample",
        lambda *a, **k: (_ for _ in ()).throw(OSError("sample failed")),
    )
    monkeypatch.setattr(serving, "_read_explicit_stop_document", lambda *a, **k: None)
    stops = []
    monkeypatch.setattr(
        session_api, "stop_session", lambda s, **k: stops.append(s.pid) or {}
    )
    result = serving._hold_session_open(
        SimpleNamespace(runtime_root=tmp_path),
        profile={"runtime_receipt": {}, "values": {"serving_resource_limits": LIMITS}},
        session=SESSION,
        session_id=SESSION.session_id,
        session_dir=tmp_path,
        monitor_path=tmp_path / "monitor.jsonl",
    )
    assert result == 1 and stops == [SESSION.pid]
    doc = json.loads((tmp_path / serving.SESSION_STOP_NAME).read_text())
    assert doc["server_exit"]["resource"]["error_type"] == "OSError"


def test_transient_snapshot_replacement_dispatches_original_request_once(
    tmp_path, monkeypatch, caplog
):
    from pathlib import Path

    sample(tmp_path)
    real_read = Path.read_text
    opens = []

    def transient_read(path, *args, **kwargs):
        if path.name == guard.SNAPSHOT_NAME:
            opens.append(path)
            if len(opens) <= 2:
                raise FileNotFoundError(2, "snapshot replacement gap", str(path))
        return real_read(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", transient_read)
    monkeypatch.setattr(guard.time, "sleep", lambda seconds: None)
    calls = []
    transport = guard.ResourceCheckedTransport(
        lambda raw: calls.append(raw) or b"ok",
        tmp_path, SESSION, LIMITS, now=lambda: 102,
    )
    assert transport(b"unchanged bytes") == b"ok"
    assert calls == [b"unchanged bytes"]
    assert len(opens) == 3
    assert "replacement gap" in caplog.text


@pytest.mark.parametrize(
    "recovered", ["stale", "wrong-session", "pressure", "latched", "corrupt"]
)
def test_reopened_receipt_still_must_pass_every_admission_gate(
    tmp_path, monkeypatch, recovered
):
    from pathlib import Path

    doc = sample(tmp_path)
    path = tmp_path / guard.SNAPSHOT_NAME
    if recovered == "wrong-session":
        doc["session"]["pid"] += 1
    elif recovered == "pressure":
        doc["host_memory"]["host_free_gb"] = 9
    elif recovered == "latched":
        doc["decision"], doc["reasons"] = "drain", ["windows-admission-floor"]
    path.write_text("{" if recovered == "corrupt" else json.dumps(doc))
    original = Path.read_text
    opens = []

    def read_snapshot(path, *args, **kwargs):
        opens.append(path)
        if len(opens) == 1:
            raise FileNotFoundError(2, "replacement gap", str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_snapshot)
    monkeypatch.setattr(guard.time, "sleep", lambda seconds: None)
    calls = []
    transport = guard.ResourceCheckedTransport(
        lambda raw: calls.append(raw),
        tmp_path, SESSION, LIMITS,
        now=lambda: 116 if recovered == "stale" else 102,
    )
    with pytest.raises(guard.ResourceAdmissionError):
        transport(b"must not post")
    assert len(opens) == 2
    assert not calls


def test_permanently_missing_receipt_has_bounded_wait_and_no_dispatch(
    tmp_path, monkeypatch
):
    from pathlib import Path

    opens, waits, calls = [], [], []

    def missing(path, *args, **kwargs):
        opens.append(path)
        raise FileNotFoundError(2, "permanently absent", str(path))

    monkeypatch.setattr(Path, "read_text", missing)
    monkeypatch.setattr(guard.time, "sleep", waits.append)
    transport = guard.ResourceCheckedTransport(
        lambda raw: calls.append(raw), tmp_path, SESSION, LIMITS, now=lambda: 100,
    )
    with pytest.raises(guard.ResourceAdmissionError) as caught:
        transport(b"must not post")
    assert 1 < len(opens) <= 5
    assert len(waits) == len(opens) - 1
    assert sum(waits) <= 0.1
    assert isinstance(caught.value.__cause__, FileNotFoundError)
    assert not calls


@pytest.mark.parametrize("error", [PermissionError("denied"), ValueError("bad JSON")])
def test_non_missing_read_errors_fail_without_wait(tmp_path, monkeypatch, error):
    from pathlib import Path

    waits = []

    def broken(*args, **kwargs):
        raise error

    monkeypatch.setattr(Path, "read_text", broken)
    monkeypatch.setattr(guard.time, "sleep", waits.append)
    with pytest.raises(guard.ResourceAdmissionError) as caught:
        guard.assert_admission(tmp_path, SESSION, LIMITS)
    assert caught.value.__cause__ is error
    assert not waits
