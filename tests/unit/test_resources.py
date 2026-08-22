"""Injectable GPU/CPU resource sampling seam (R0 repair T7, invariant I8).

Every test here injects a fake ``runner``/binary lookup -- none ever spawns a
real ``nvidia-smi`` process, per the task brief's "tests inject fakes, never
call nvidia-smi" requirement.
"""

from __future__ import annotations

import time

import pytest

from speech_aware_evidence_acquisition.core.resources import (
    NOT_AVAILABLE,
    NullSampler,
    NvidiaSmiSampler,
    cpu_seconds_snapshot,
    resolve_resource_sampler,
)


# ---------------------------------------------------------------------------
# NullSampler.
# ---------------------------------------------------------------------------


def test_null_sampler_reports_not_available_with_its_reason():
    sampler = NullSampler("nvidia-smi not found on PATH")
    summary = sampler.summary()
    assert summary["gpu_seconds"] == NOT_AVAILABLE
    assert summary["peak_vram_mib"] == NOT_AVAILABLE
    assert summary["gpu_sampling_reason"] == "nvidia-smi not found on PATH"
    assert summary["request_gpu_utilization_median_pct"] == NOT_AVAILABLE
    assert summary["request_gpu_utilization_p10_pct"] == NOT_AVAILABLE
    assert summary["request_gpu_sample_count"] == 0


def test_null_sampler_start_stop_are_safe_no_ops():
    sampler = NullSampler("no sampler configured")
    sampler.start()
    sampler.start()
    sampler.stop()
    sampler.stop()
    assert sampler.summary()["gpu_seconds"] == NOT_AVAILABLE


def test_null_sampler_refuses_a_blank_reason():
    with pytest.raises(ValueError):
        NullSampler("")
    with pytest.raises(ValueError):
        NullSampler("   ")


# ---------------------------------------------------------------------------
# NvidiaSmiSampler: happy path, injected runner.
# ---------------------------------------------------------------------------


def _fixed_runner(lines):
    """A runner that returns each of ``lines`` in turn, then repeats the last."""

    calls = {"n": 0}

    def runner(binary, timeout_seconds):
        index = min(calls["n"], len(lines) - 1)
        calls["n"] += 1
        return lines[index]

    runner.calls = calls
    return runner


def test_nvidia_smi_sampler_records_peak_vram_from_the_first_synchronous_poll():
    runner = _fixed_runner(["50, 1000"])
    sampler = NvidiaSmiSampler(interval_seconds=10.0, runner=runner)
    sampler.start()
    try:
        summary = sampler.summary()
        assert summary["peak_vram_mib"] == 1000.0
        assert summary["gpu_sampling_reason"] is None
        # The very first sample spans no prior interval -- 0 gpu_seconds
        # contributed by construction, not a bug.
        assert summary["gpu_seconds"] == 0.0
    finally:
        sampler.stop()


def test_nvidia_smi_sampler_accumulates_utilization_weighted_gpu_seconds_over_polls():
    # Tight interval so the background thread accumulates a few real polls
    # quickly; utilization is pinned at 100% so gpu_seconds tracks wall time.
    runner = _fixed_runner(["100, 500", "100, 2000", "100, 1500"])
    sampler = NvidiaSmiSampler(interval_seconds=0.02, runner=runner)
    sampler.start()
    try:
        time.sleep(0.12)
    finally:
        sampler.stop()
    summary = sampler.summary()
    assert summary["gpu_sampling_reason"] is None
    assert summary["gpu_seconds"] > 0.0
    # peak_vram_mib is the MAX across every sample taken (2000, from the
    # second canned line), never the latest or the first.
    assert summary["peak_vram_mib"] == 2000.0


def test_nvidia_smi_sampler_peak_vram_is_a_max_not_a_last_value():
    runner = _fixed_runner(["10, 4000", "10, 1000"])
    sampler = NvidiaSmiSampler(interval_seconds=0.02, runner=runner)
    sampler.start()
    try:
        time.sleep(0.08)
    finally:
        sampler.stop()
    assert sampler.summary()["peak_vram_mib"] == 4000.0


def test_nvidia_smi_sampler_reports_request_window_median_and_p10():
    sampler = NvidiaSmiSampler(interval_seconds=10.0, runner=_fixed_runner(["5, 100"]))
    sampler.start()
    try:
        sampler.begin_request_window()
        sampler._record(90.0, 1000.0, 1.0)
        sampler._record(40.0, 1200.0, 1.0)
        sampler._record(100.0, 1100.0, 1.0)
        sampler.end_request_window()
        sampler._record(1.0, 900.0, 1.0)
    finally:
        sampler.stop()

    summary = sampler.summary()
    assert summary["request_gpu_utilization_median_pct"] == 90.0
    assert summary["request_gpu_utilization_p10_pct"] == 40.0
    assert summary["request_gpu_sample_count"] == 3


def test_nvidia_smi_sampler_persists_auditable_request_sample_timeline(monkeypatch):
    import speech_aware_evidence_acquisition.core.resources as resources_module

    monkeypatch.setattr(resources_module.time, "time", lambda: 1_776_000_000.25)
    sampler = NvidiaSmiSampler(interval_seconds=10.0, runner=_fixed_runner(["5, 100"]))
    sampler.start()
    try:
        sampler.begin_request_window()
        sampler._record(96.0, 21000.0, 1.0)
        sampler._record(42.0, 21500.0, 1.0)
        sampler.end_request_window()
        sampler._record(1.0, 19000.0, 1.0)
    finally:
        sampler.stop()

    assert sampler.summary()["request_gpu_samples"] == [
        {
            "sampled_at_unix_seconds": 1_776_000_000.25,
            "utilization_pct": 96.0,
            "memory_used_mib": 21000.0,
        },
        {
            "sampled_at_unix_seconds": 1_776_000_000.25,
            "utilization_pct": 42.0,
            "memory_used_mib": 21500.0,
        },
    ]


def test_nvidia_smi_sampler_binds_llama_server_busy_slots_to_gpu_samples():
    slot_payload = (
        '[{"id": 0, "is_processing": true}, '
        '{"id": 1, "is_processing": false}]'
    )
    sampler = NvidiaSmiSampler(
        interval_seconds=10.0,
        runner=_fixed_runner(["96, 21000"]),
        slots_url="http://127.0.0.1:8080/slots",
        slot_runner=lambda url, timeout_seconds: slot_payload,
    )
    sampler.start()
    try:
        sampler.begin_request_window()
        slot_snapshot = sampler._poll_server_slots_once()
        sampler._record(
            96.0,
            21000.0,
            1.0,
            sampled_at_unix_seconds=1_776_000_000.25,
            server_slot_snapshot=slot_snapshot,
        )
    finally:
        sampler.stop()

    summary = sampler.summary()
    assert summary["server_slot_sampling_configured"] is True
    assert summary["server_slot_sampling_reason"] is None
    assert summary["server_slot_probe_failure_count"] == 0
    assert summary["server_slot_sample_count"] == 1
    sample = summary["request_gpu_samples"][0]
    assert sample["server_busy_slots"] == 1
    assert sample["server_total_slots"] == 2
    assert isinstance(sample["server_slot_sampled_at_unix_seconds"], float)
    assert isinstance(sample["server_slot_gpu_skew_milliseconds"], float)


def test_background_sampler_collects_server_slots_during_the_request_window():
    slot_payload = (
        '[{"id": 0, "is_processing": true}, '
        '{"id": 1, "is_processing": true}]'
    )
    sampler = NvidiaSmiSampler(
        interval_seconds=0.01,
        runner=_fixed_runner(["96, 21000"]),
        slots_url="http://127.0.0.1:8080/slots",
        slot_runner=lambda url, timeout_seconds: slot_payload,
    )
    sampler.start()
    try:
        sampler.begin_request_window()
        time.sleep(0.06)
        sampler.end_request_window()
    finally:
        sampler.stop()

    summary = sampler.summary()
    assert summary["request_gpu_sample_count"] >= 2
    assert summary["server_slot_sample_count"] == summary["request_gpu_sample_count"]
    assert all(
        sample["server_busy_slots"] == 2
        for sample in summary["request_gpu_samples"]
    )


def test_malformed_slot_response_does_not_disable_gpu_sampling():
    sampler = NvidiaSmiSampler(
        interval_seconds=10.0,
        runner=_fixed_runner(["96, 21000"]),
        slots_url="http://127.0.0.1:8080/slots",
        slot_runner=lambda url, timeout_seconds: "not-json",
    )
    sampler.start()
    try:
        sampler.begin_request_window()
        assert sampler._poll_server_slots_once() is None
        sampler._record(96.0, 21000.0, 1.0)
    finally:
        sampler.stop()

    summary = sampler.summary()
    assert summary["gpu_sampling_reason"] is None
    assert summary["gpu_seconds"] == 0.96
    assert summary["server_slot_sampling_configured"] is True
    assert summary["server_slot_probe_failure_count"] == 1
    assert "slot sampling failed" in summary["server_slot_sampling_reason"]
    assert summary["server_slot_sample_count"] == 0
    assert "server_busy_slots" not in summary["request_gpu_samples"][0]


# ---------------------------------------------------------------------------
# NvidiaSmiSampler: fail-safe degradation to NOT_AVAILABLE, never a crash.
# ---------------------------------------------------------------------------


def test_nvidia_smi_sampler_degrades_to_not_available_when_runner_raises_immediately():
    def _raising_runner(binary, timeout_seconds):
        raise FileNotFoundError("nvidia-smi: command not found")

    sampler = NvidiaSmiSampler(interval_seconds=1.0, runner=_raising_runner)
    sampler.start()  # must not raise
    sampler.stop()  # must not raise
    summary = sampler.summary()
    assert summary["gpu_seconds"] == NOT_AVAILABLE
    assert summary["peak_vram_mib"] == NOT_AVAILABLE
    assert "nvidia-smi" in summary["gpu_sampling_reason"] or "command not found" in summary["gpu_sampling_reason"]


def test_nvidia_smi_sampler_degrades_to_not_available_on_malformed_output():
    def _garbage_runner(binary, timeout_seconds):
        return "not,a,valid,csv,line,at,all,too,many,fields"

    sampler = NvidiaSmiSampler(interval_seconds=1.0, runner=_garbage_runner)
    sampler.start()
    sampler.stop()
    summary = sampler.summary()
    assert summary["gpu_seconds"] == NOT_AVAILABLE
    assert summary["peak_vram_mib"] == NOT_AVAILABLE
    assert summary["gpu_sampling_reason"]


def test_nvidia_smi_sampler_degrades_to_not_available_on_empty_output():
    def _empty_runner(binary, timeout_seconds):
        return ""

    sampler = NvidiaSmiSampler(interval_seconds=1.0, runner=_empty_runner)
    sampler.start()
    sampler.stop()
    summary = sampler.summary()
    assert summary["gpu_seconds"] == NOT_AVAILABLE
    assert summary["peak_vram_mib"] == NOT_AVAILABLE


def test_nvidia_smi_sampler_becomes_not_available_after_a_mid_run_failure():
    """Available on the first poll, then the runner starts failing -- the
    background thread must degrade the WHOLE sampler to NOT_AVAILABLE, not
    silently keep reporting the stale last-good numbers."""

    calls = {"n": 0}

    def runner(binary, timeout_seconds):
        calls["n"] += 1
        if calls["n"] == 1:
            return "20, 800"
        raise RuntimeError("nvidia-smi vanished mid-run")

    sampler = NvidiaSmiSampler(interval_seconds=0.02, runner=runner)
    sampler.start()
    try:
        time.sleep(0.1)
    finally:
        sampler.stop()
    summary = sampler.summary()
    assert summary["gpu_seconds"] == NOT_AVAILABLE
    assert summary["peak_vram_mib"] == NOT_AVAILABLE
    assert "vanished" in summary["gpu_sampling_reason"]


def test_nvidia_smi_sampler_never_polled_reports_not_available():
    """summary() called without ever calling start() -- samples_taken == 0."""

    sampler = NvidiaSmiSampler(interval_seconds=1.0, runner=_fixed_runner(["0, 0"]))
    summary = sampler.summary()
    assert summary["gpu_seconds"] == NOT_AVAILABLE
    assert summary["peak_vram_mib"] == NOT_AVAILABLE


def test_nvidia_smi_sampler_start_is_idempotent():
    runner = _fixed_runner(["10, 100"])
    sampler = NvidiaSmiSampler(interval_seconds=1.0, runner=runner)
    sampler.start()
    sampler.start()  # second call must not spin up a second thread / re-raise
    try:
        assert runner.calls["n"] == 1
    finally:
        sampler.stop()


def test_nvidia_smi_sampler_stop_is_idempotent():
    sampler = NvidiaSmiSampler(interval_seconds=1.0, runner=_fixed_runner(["10, 100"]))
    sampler.start()
    sampler.stop()
    sampler.stop()  # must not raise


@pytest.mark.parametrize("bad_interval", [0, -1, -0.5])
def test_nvidia_smi_sampler_refuses_a_non_positive_interval(bad_interval):
    with pytest.raises(ValueError):
        NvidiaSmiSampler(interval_seconds=bad_interval)


@pytest.mark.parametrize("bad_device_index", [-1, -5, "0", 1.5, True])
def test_nvidia_smi_sampler_refuses_a_negative_or_non_integer_device_index(bad_device_index):
    with pytest.raises(ValueError):
        NvidiaSmiSampler(device_index=bad_device_index)


# ---------------------------------------------------------------------------
# device_index: the DEFAULT runner pins which GPU is queried (T7 fix, MINOR
# 2). An injected TEST runner is unaffected -- pinning only changes the
# subprocess command line the default runner builds.
# ---------------------------------------------------------------------------


def test_default_runner_pins_the_configured_device_index(monkeypatch):
    import speech_aware_evidence_acquisition.core.resources as resources_module

    captured = {}

    class _FakeCompleted:
        stdout = "10, 500"

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompleted()

    monkeypatch.setattr(resources_module.subprocess, "run", fake_run)
    sampler = NvidiaSmiSampler(interval_seconds=1.0, device_index=2)
    sampler.start()
    try:
        assert "--id=2" in captured["cmd"]
    finally:
        sampler.stop()


def test_default_runner_defaults_to_device_index_zero(monkeypatch):
    import speech_aware_evidence_acquisition.core.resources as resources_module

    captured = {}

    class _FakeCompleted:
        stdout = "10, 500"

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return _FakeCompleted()

    monkeypatch.setattr(resources_module.subprocess, "run", fake_run)
    sampler = NvidiaSmiSampler(interval_seconds=1.0)
    sampler.start()
    try:
        assert "--id=0" in captured["cmd"]
    finally:
        sampler.stop()


def test_resolve_resource_sampler_passes_device_index_through(monkeypatch):
    import speech_aware_evidence_acquisition.core.resources as resources_module

    monkeypatch.setattr(
        resources_module.shutil, "which", lambda binary: f"/usr/bin/{binary}"
    )
    sampler = resolve_resource_sampler(binary="nvidia-smi", device_index=3)
    assert isinstance(sampler, NvidiaSmiSampler)
    assert sampler._device_index == 3  # never started -- no real nvidia-smi touched


def test_resolve_resource_sampler_passes_the_llama_server_slots_url(monkeypatch):
    import speech_aware_evidence_acquisition.core.resources as resources_module

    monkeypatch.setattr(
        resources_module.shutil, "which", lambda binary: f"/usr/bin/{binary}"
    )
    sampler = resolve_resource_sampler(
        binary="nvidia-smi",
        slots_url="http://127.0.0.1:8080/slots",
    )

    assert isinstance(sampler, NvidiaSmiSampler)
    assert sampler._slots_url == "http://127.0.0.1:8080/slots"


# ---------------------------------------------------------------------------
# resolve_resource_sampler: factory, never touches nvidia-smi in a test.
# ---------------------------------------------------------------------------


def test_resolve_resource_sampler_returns_null_sampler_when_binary_absent(monkeypatch):
    import speech_aware_evidence_acquisition.core.resources as resources_module

    monkeypatch.setattr(resources_module.shutil, "which", lambda binary: None)
    sampler = resolve_resource_sampler(binary="definitely-not-a-real-binary")
    assert isinstance(sampler, NullSampler)
    summary = sampler.summary()
    assert summary["gpu_seconds"] == NOT_AVAILABLE
    assert "PATH" in summary["gpu_sampling_reason"]


def test_resolve_resource_sampler_returns_real_sampler_when_binary_present(monkeypatch):
    import speech_aware_evidence_acquisition.core.resources as resources_module

    monkeypatch.setattr(
        resources_module.shutil, "which", lambda binary: f"/usr/bin/{binary}"
    )
    sampler = resolve_resource_sampler(binary="nvidia-smi")
    assert isinstance(sampler, NvidiaSmiSampler)
    # Deliberately never call start()/stop() here: this test proves the
    # FACTORY's binary-discovery branch, not the sampler's own polling
    # behavior (covered above with an injected runner) -- calling start()
    # on this instance would shell out to the real, injected-only-by-name
    # "nvidia-smi" and violate "never call nvidia-smi in tests".


def test_resolve_resource_sampler_uses_the_wsl_gpu_binary_when_path_is_minimal(monkeypatch):
    """WSL exposes ``nvidia-smi`` outside common fail-closed runtime PATHs."""

    import speech_aware_evidence_acquisition.core.resources as resources_module

    monkeypatch.setattr(resources_module.shutil, "which", lambda binary: None)
    monkeypatch.setattr(
        resources_module.os.path,
        "isfile",
        lambda path: path == "/usr/lib/wsl/lib/nvidia-smi",
    )
    monkeypatch.setattr(
        resources_module.os,
        "access",
        lambda path, mode: path == "/usr/lib/wsl/lib/nvidia-smi" and mode == resources_module.os.X_OK,
    )

    sampler = resolve_resource_sampler(binary="nvidia-smi")

    assert isinstance(sampler, NvidiaSmiSampler)
    assert sampler._binary == "/usr/lib/wsl/lib/nvidia-smi"


# ---------------------------------------------------------------------------
# cpu_seconds_snapshot: standard-library os.times() wrapper.
# ---------------------------------------------------------------------------


def test_cpu_seconds_snapshot_returns_a_non_negative_float():
    value = cpu_seconds_snapshot()
    assert isinstance(value, float)
    assert value >= 0.0


def test_cpu_seconds_snapshot_is_monotonic_non_decreasing_across_real_work():
    start = cpu_seconds_snapshot()
    total = 0
    for i in range(200_000):
        total += i * i
    end = cpu_seconds_snapshot()
    assert end >= start
