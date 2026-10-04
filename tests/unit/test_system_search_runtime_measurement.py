"""Measured search binds the declared schedule before any model contact."""

import copy
import json
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails import (
    system_search_measurement as measurement,
)
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from test_system_search_measurement import profile
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


def test_profile_resolves_explicit_queue_without_mutating_policy():
    values = {
        "system_search_measurement": profile(),
        "native_episode": {"schema": "native"},
    }
    before = copy.deepcopy(values)
    assert measurement.runtime_options(values, slot_count=4) == {
        "slot_count": 4,
        "queue_depth": 4,
    }
    assert values == before
    assert measurement.runtime_options({}, slot_count=None) == {}


@pytest.mark.parametrize(
    "fault",
    [
        "null",
        "slots",
        "queue",
        "node_batch",
        "node_pipeline",
        "prefix",
        "dispatch",
        "non-native",
        "bad-slots",
    ],
)
def test_runtime_measurement_refuses_incompatible_envelope(fault):
    values = {
        "system_search_measurement": profile(),
        "native_episode": {"schema": "native"},
    }
    slots = 4
    if fault == "null":
        values["system_search_measurement"] = None
    elif fault == "slots":
        slots = 8
    elif fault == "bad-slots":
        slots = True
    elif fault == "queue":
        values["system_search_measurement"]["queue_depth"] = 2
    elif fault == "non-native":
        del values["native_episode"]
    else:
        values[
            {
                "node_batch": "native_node_batch",
                "node_pipeline": "native_node_pipeline",
                "prefix": "native_prefix_slots",
                "dispatch": "dispatch",
            }[fault]
        ] = {}
    with pytest.raises(PolicyError):
        measurement.runtime_options(values, slot_count=slots)


def test_flight_refuses_non_native_profile_before_preparation():
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(
        values={"policy": "fixed", "system_search_measurement": profile()}
    )
    runtime._adapter = SimpleNamespace(serving_geometry=lambda: {"slots": 4})
    with pytest.raises(FlightRuntimeError):
        runtime._system_search_measurement_options()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("armed", [False, True])
def test_real_shared_flight_emits_declared_queue_and_complete_timing(
    tmp_path, monkeypatch, armed
):
    from test_flight_resume_recovery import _harness, _skeleton

    h = _harness(
        tmp_path, "measured" if armed else "legacy", ("s1", "s2"), max_revisions=1
    )
    geometry = h.adapter.serving_geometry()
    monkeypatch.setattr(h.adapter, "serving_geometry", lambda: {**geometry, "slots": 1})
    runtime = _skeleton(h, monkeypatch)
    if armed:
        runtime._composed.values["system_search_measurement"] = {
            **profile(),
            "slot_count": 1,
            "queue_depth": 1,
        }
    try:
        rows, calls, *_ = runtime._dispatch_phase_program(
            h.client, h.plan, h.program.program_id
        )
    finally:
        h.close()
    assert len(rows) == 2 and calls == 14
    records = [
        json.loads(line)
        for line in (h.world.run_dir / f"{h.plan.run_id}.trace.jsonl")
        .read_text()
        .splitlines()
    ]
    timing = [
        r["payload"]["use_sample_execution_timing"]
        for r in records
        if "use_sample_execution_timing" in r["payload"]
    ]
    assert len(timing) == 2
    assert all(
        t["slot_count"] == 1 and t["queue_depth"] == (1 if armed else 4) for t in timing
    )
    assert all(t["status"] == "completed" for t in timing)
    assert all(
        h.events.index(("fit", k)) < h.events.index(("dispatch", k)) for k in h.prepared
    )


@pytest.mark.parametrize("fault", ["missing-native", "workflow-panel"])
def test_flight_refuses_non_trajectory_execution(monkeypatch, fault):
    from speech_aware_evidence_acquisition.rails import native_episode_config

    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(
        values={
            "policy": "native",
            "system_search_measurement": profile(),
            "native_episode": {},
        }
    )
    runtime._adapter = SimpleNamespace(serving_geometry=lambda: {"slots": 4})
    monkeypatch.setattr(runtime, "_obs_policy_names", lambda: ())
    if fault == "missing-native":
        monkeypatch.setattr(
            native_episode_config, "load_native_episode_config", lambda *args: None
        )
        monkeypatch.setattr(
            "speech_aware_evidence_acquisition.core.flight.runtime.default_phase_program",
            lambda policy: "test",
        )
        config = None
    else:
        runtime._native_workflow_panel = object()
        config = object()
    with pytest.raises(FlightRuntimeError):
        runtime._system_search_measurement_options(config)
