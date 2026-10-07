"""Run the real four-GiB startup and worker guards without any model contact."""

from dataclasses import asdict
import json
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.process_guard import (
    FlightProcessGuardError,
    MemoryPolicy,
    run_guarded,
)
from speech_aware_evidence_acquisition.core.session import resource_guard
from speech_aware_evidence_acquisition.core.session import serving
from test_start_memory_wait import Clock, module


@pytest.mark.parametrize("stage", ["ready", "wait", "guard-start", "running", "stop"])
def test_actual_wait_then_owned_worker_respects_four_gib_at_each_boundary(
    tmp_path, stage
):
    waiter = module()
    clock = Clock()
    stop = tmp_path / "STOP"
    marker = tmp_path / "child-completed"
    calls = []

    def reader():
        calls.append(len(calls) + 1)
        if stage == "stop" and len(calls) == 3:
            stop.write_bytes(b"original owner stop")
        low_at = {"wait": 1, "guard-start": 4, "running": 5}.get(stage)
        return {
            "host_free_gb": 3.99 if low_at is not None and len(calls) >= low_at else 4.0
        }

    ready = waiter.wait_for_memory(
        tmp_path / "wait",
        stop,
        4,
        60,
        3,
        floor_gib=4,
        host_reader=reader,
        monotonic=clock.time,
        sleep=clock.sleep,
    )
    assert ready["start_gib"] == ready["running_floor_gib"] == 4
    assert ready["interval_seconds"] == 10 and ready["stable_samples"] == 3
    assert ready["worker_started"] is False
    if stage in {"wait", "stop"}:
        assert ready["status"] == (
            "resource-floor-violation" if stage == "wait" else "stop-present"
        )
        assert ready["exit_code"] == 125 and not marker.exists()
        if stage == "stop":
            assert stop.read_bytes() == b"original owner stop"
        return
    assert ready["status"] == "ready" and ready["elapsed_seconds"] == 20
    policy = MemoryPolicy(
        4, 4, interval_seconds=0.02, read_timeout_seconds=0.2, stop_grace_seconds=0.05
    )
    result = run_guarded(
        [
            sys.executable,
            "-B",
            "-c",
            f"import pathlib,time;time.sleep(.08);pathlib.Path({str(marker)!r}).write_text('finished')",
        ],
        tmp_path / "guard",
        policy,
        host_reader=reader,
    )
    assert (
        result.status
        == {
            "ready": "completed",
            "guard-start": "start-refused",
            "running": "resource-stop",
        }[stage]
    )
    assert result.exit_code == (0 if stage == "ready" else 125)
    assert (result.pid is None) is (stage == "guard-start")
    receipt = json.loads((tmp_path / "guard/finished.json").read_text())
    assert receipt["policy"] == asdict(policy)
    if stage == "ready":
        assert marker.read_text() == "finished"


@pytest.mark.parametrize("field", ["start_gib", "floor_gib"])
@pytest.mark.parametrize(
    "value", [3.99, 0, -1, True, False, float("nan"), float("inf"), "4"]
)
def test_actual_policy_rejects_invalid_or_sub_four_gib_floors(field, value):
    with pytest.raises(FlightProcessGuardError):
        MemoryPolicy(**dict(dict(start_gib=4, floor_gib=4), **{field: value}))


def test_prospective_defaults_are_four_but_higher_registered_policies_remain(tmp_path):
    policy = MemoryPolicy(start_gib=4)
    assert policy.floor_gib == 4
    assert (
        policy.interval_seconds,
        policy.read_timeout_seconds,
        policy.stop_grace_seconds,
    ) == (5, 10, 5)
    clock = Clock()
    result = module().wait_for_memory(
        tmp_path / "wait",
        tmp_path / "STOP",
        4,
        60,
        3,
        host_reader=lambda: {"host_free_gb": 4},
        monotonic=clock.time,
        sleep=clock.sleep,
    )
    assert result["status"] == "ready" and result["running_floor_gib"] == 4
    assert asdict(MemoryPolicy(20, 8)) == dict(
        start_gib=20,
        floor_gib=8,
        interval_seconds=5,
        read_timeout_seconds=10,
        stop_grace_seconds=5,
    )


def four_gib_limits():
    return dict(
        schema="saea-serving-resource-limits-v1",
        windows_start_gib=4,
        windows_admit_gib=4,
        windows_stop_gib=4,
        gpu_admit_free_mib=2048,
        gpu_stop_free_mib=1024,
        max_sample_age_seconds=15,
    )


@pytest.mark.parametrize(
    "field", ["windows_start_gib", "windows_admit_gib", "windows_stop_gib"]
)
@pytest.mark.parametrize("value", [3.99, True, float("nan"), float("inf")])
def test_service_configuration_also_rejects_invalid_or_sub_four_gib_floors(
    field, value
):
    with pytest.raises(resource_guard.ResourceAdmissionError):
        resource_guard.resource_limits(
            {"serving_resource_limits": dict(four_gib_limits(), **{field: value})}
        )


def test_actual_service_start_and_transport_accept_four_then_latch_below_four(tmp_path):
    limits = resource_guard.resource_limits(
        {"serving_resource_limits": four_gib_limits()}
    )
    session = SimpleNamespace(session_id="synthetic", pid=123, started_at="synthetic")
    resource_guard.assert_start(limits, host_reader=lambda: {"host_free_gb": 4})
    with pytest.raises(resource_guard.ResourceAdmissionError):
        resource_guard.assert_start(limits, host_reader=lambda: {"host_free_gb": 3.99})
    calls = []
    wrapped = resource_guard.ResourceCheckedTransport(
        lambda raw: calls.append(raw) or b"ok",
        tmp_path,
        session,
        limits,
        now=lambda: 100,
        elapsed_clock=lambda: 100,
        boot_id_reader=lambda: "boot",
    )

    def publish(host):
        return resource_guard.publish_sample(
            tmp_path,
            session,
            limits,
            now=lambda: 100,
            elapsed_clock=lambda: 100,
            boot_id_reader=lambda: "boot",
            host_reader=lambda: {"host_free_gb": host},
            gpu_reader=lambda: {"memory_free_mib": 2048},
        )

    assert publish(4)["decision"] == "admit"
    assert wrapped(b"unchanged request") == b"ok"
    assert publish(3.99)["decision"] == "stop"
    assert publish(4)["decision"] == "stop"
    with pytest.raises(resource_guard.ResourceAdmissionError):
        wrapped(b"must not dispatch")
    assert calls == [b"unchanged request"]


@pytest.mark.parametrize(
    "value", [3.99, 0, -1, True, False, float("nan"), float("inf"), "4"]
)
def test_legacy_serving_entry_rejects_invalid_policy_before_reading(monkeypatch, value):
    def forbidden_read():
        pytest.fail("invalid policy must be refused before observation")

    monkeypatch.setattr(serving, "read_host_memory", forbidden_read)
    with pytest.raises(serving.ServingSessionError):
        serving._refuse_low_host_memory(value)
    with pytest.raises(serving.ServingSessionError):
        serving.host_memory_verdict({"host_free_gb": 20}, min_host_free_gb=value)


@pytest.mark.parametrize("margin", [-1, True, float("nan"), float("inf"), "0"])
def test_legacy_serving_entry_cannot_bypass_minimum_with_invalid_margin(margin):
    with pytest.raises(serving.ServingSessionError):
        serving.host_memory_verdict(
            {"host_free_gb": 4}, min_host_free_gb=4, margin_gb=margin
        )


def test_legacy_serving_entry_rejects_overflowed_combined_minimum():
    with pytest.raises(serving.ServingSessionError):
        serving.host_memory_verdict(
            {"host_free_gb": 4}, min_host_free_gb=1e308, margin_gb=1e308
        )


def test_actual_serving_start_and_host_memory_entry_use_four_gib(monkeypatch, capsys):
    args = serving.build_parser().parse_args(["start", "synthetic-unused-fragment"])
    assert args.min_host_free_gb == 4
    monkeypatch.setattr(serving, "read_host_memory", lambda: {"host_free_gb": 4})
    serving._refuse_low_host_memory(args.min_host_free_gb)
    host_args = serving.build_parser().parse_args(["host-memory"])
    assert host_args.min_host_free_gb == 4 and host_args.margin_gb == 0
    assert host_args.handler(host_args) == 0
    assert json.loads(capsys.readouterr().out)["required_gb"] == 4
    monkeypatch.setattr(serving, "read_host_memory", lambda: {"host_free_gb": 3.99})
    with pytest.raises(serving.ServingSessionError, match="below"):
        serving._refuse_low_host_memory(args.min_host_free_gb)
    assert host_args.handler(host_args) == serving.HOST_MEMORY_SHORT_EXIT


def test_batch_serving_default_matches_four_and_preserves_explicit_override():
    from pathlib import Path
    import os
    import subprocess

    library = (
        Path(__file__).resolve().parents[2] / "scripts/flights/batch/serving_lib.sh"
    )
    base_env = dict(os.environ)
    base_env.pop("SAEA_MIN_HOST_FREE_GB", None)
    for override, expected in [(None, "4.0"), ("20", "20")]:
        env = dict(base_env)
        if override is not None:
            env["SAEA_MIN_HOST_FREE_GB"] = override
        # Sourcing the library defines functions only; no serving operation occurs.
        result = subprocess.run(
            [
                "bash",
                "-c",
                'source "$1"; printf "%s" "$SAEA_MIN_HOST_FREE_GB"',
                "bash",
                str(library),
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        assert result.stdout == expected
