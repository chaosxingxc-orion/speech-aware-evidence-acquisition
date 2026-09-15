"""Synthetic shared-runtime custody for selected execution-unit speech spans."""
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError
from speech_aware_evidence_acquisition.core.preparation import digest
from speech_aware_evidence_acquisition.rails.execution_units import scoped_execution_contact_id
from speech_aware_evidence_acquisition.rails.live_speech_observation import (
    execution_unit_source_bindings, select_execution_unit_span,
)
from test_feature_execution_unit_client import _feature_unit_world
from test_flight_native_tool_runtime import _runtime
from test_live_speech_unit_spans import _arguments


def _unit_runtime(tmp_path):
    runtime = _runtime(tmp_path)
    world, parent, _, _, _, roster, _ = _feature_unit_world(tmp_path / "source")
    runtime._data_root = world.data_root
    runtime._composed = SimpleNamespace(values={"prepared_execution_units": {"relpath": "units"}})
    runtime.execution_unit_roster = lambda: roster
    runtime._samples = (parent,)
    runtime._live_speech_source_bindings = execution_unit_source_bindings(roster)
    runtime._live_speech_config = {
        "plan": ExecutionPlan(
            run_id="SAEA-LIVE-UNIT-SPANS", attempt_id="attempt-one",
            execution_profile="bounded-discovery-probe", carrier_lock_key="fake-carrier",
            split_role="discovery", split_identity_hash="c" * 64,
            planned_model_calls=2, planned_gpu_hours=1.0,
            planned_speech_audio_seconds=1, protocol_hash="d" * 64,
        ).validate(),
    }
    return runtime, roster


def _facts(unit):
    span, seconds = select_execution_unit_span(unit, _arguments())
    return dict(
        sample_id=unit.parent_sample_id, execution_unit_id=unit.request_key,
        execution_unit_binding_sha256=digest(unit.as_json()), audio_seconds=seconds,
        source={"audio_sha256": unit.slice_record.sha256, "span": span},
        arguments=_arguments(), source_response_sha256="e" * 64, cache_key="f" * 64,
    )


def test_runtime_live_sources_use_unit_keys_without_parent_packets(tmp_path):
    runtime, roster = _unit_runtime(tmp_path)
    runtime.source_audio_bindings = lambda **_kwargs: pytest.fail("parent source alias")
    assert runtime._live_speech_sources() == execution_unit_source_bindings(roster)
    assert list(runtime._live_speech_sources()) == [u.request_key for u in roster.units]


def test_runtime_debits_selected_duration_and_keeps_sibling_identity(tmp_path):
    runtime, roster = _unit_runtime(tmp_path)
    receipts = [runtime._record_live_speech_contact(**_facts(unit)) for unit in roster.units]
    assert runtime._live_speech_attempt_handle.actual_totals() == (2, 0.25)
    assert [r["execution_unit_id"] for r in receipts] == [u.request_key for u in roster.units]
    assert all(r["selected_span"]["end_frame"] == 2000 for r in receipts)


@pytest.mark.parametrize("field", ["unit", "source", "duration", "binding", "span"])
def test_runtime_refuses_cross_unit_span_before_reserving_contact(tmp_path, field):
    runtime, roster = _unit_runtime(tmp_path)
    facts = _facts(roster.units[0])
    if field == "unit":
        facts["execution_unit_id"] = roster.units[1].request_key
    elif field == "source":
        facts["source"] = {**facts["source"], "audio_sha256": "9" * 64}
    elif field == "duration":
        facts["audio_seconds"] = 0.25
    elif field == "binding":
        facts["execution_unit_binding_sha256"] = "0" * 64
    else:
        facts["source"] = {**facts["source"], "span": {}}
    with pytest.raises(FlightRuntimeError):
        runtime._record_live_speech_contact(**facts)
    assert runtime._live_speech_attempt_handle is None


def test_native_tool_action_binds_actual_source_request_unit_before_counting(tmp_path):
    runtime, roster = _unit_runtime(tmp_path)
    counted = []
    unit = roster.units[0]
    runtime._client = SimpleNamespace(
        record_tool_call=lambda **facts: counted.append(facts),
        timings=(SimpleNamespace(
            sample_id=unit.parent_sample_id, request_id="request-one",
            agent_contact_id=scoped_execution_contact_id("reviewer", unit.request_key),
        ),),
    )
    facts = dict(
        sample_id=unit.parent_sample_id, phase="reviewer", next_phase="reviewer",
        tool_id="saea-tool-live-speech-span-v1", arguments=_arguments(),
        source_response_sha256="e" * 64, request_id="request-one",
        tool_call_id="tool-one", tool_calls_sha256="f" * 64,
        execution_unit_id=unit.request_key,
        execution_unit_binding_sha256=digest(unit.as_json()),
    )
    receipt = runtime._record_phase_tool_contact(**facts)
    assert receipt["execution_unit_id"] == unit.request_key
    assert receipt["speech_packet_id"] == unit.speech_packet_id
    assert counted == [{"count": 1}]
    with pytest.raises(FlightRuntimeError, match="unit"):
        runtime._record_phase_tool_contact(**{
            **facts, "execution_unit_id": roster.units[1].request_key,
            "execution_unit_binding_sha256": digest(roster.units[1].as_json()),
        })
    assert counted == [{"count": 1}]


@pytest.mark.parametrize("span_tool,has_units", [(True, True), (False, False), (True, False), (False, True)])
def test_live_tool_schema_must_match_source_scope_before_contacts(tmp_path, span_tool, has_units):
    runtime = _runtime(tmp_path)
    tool = (
        "saea-tool-live-speech-span-v1" if span_tool
        else "saea-tool-live-speech-observation-v1"
    )
    values = {
        "arm": "speech-feature-query-native-tools",
        "live_speech_observations": {"synthetic": True},
        "phase_tools": {"reviewer": {
            "mode": "native-tools", "allowed_tools": [tool],
            "knowledge_views": ["text"], "source_authority_role": "reviewer",
        }},
    }
    if has_units:
        values["prepared_execution_units"] = {"synthetic": True}
    runtime._composed = SimpleNamespace(values=values)
    runtime._obs_policy_names = lambda: set()
    if span_tool == has_units:
        assert runtime._phase_tool_specs("phase-native-review-revise-v1")
    else:
        with pytest.raises(FlightRuntimeError, match="source scope"):
            runtime._phase_tool_specs("phase-native-review-revise-v1")
    assert runtime._live_speech_attempt_handle is None
