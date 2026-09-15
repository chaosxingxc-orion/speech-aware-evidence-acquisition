"""Root integration evidence for independent native windows of one parent."""
import hashlib
import json
import threading
from functools import partial
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight import runtime as flight_module
from speech_aware_evidence_acquisition.core import preparation_fit
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding, _minimum_model_calls_from_trace

from speech_aware_evidence_acquisition.rails import build_slice_registry
from speech_aware_evidence_acquisition.core.model.slices import SliceRecord
from speech_aware_evidence_acquisition.rails.execution_units import ExecutionUnit, ExecutionUnitRoster, execution_unit_scope
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness, _plan, _wire_response
from test_rails_runner import _knowledge_snapshot

def _windows(harness):
    sample = harness.samples[0]
    registry = build_slice_registry(data_root=harness.world.data_root, run_id=harness.plan.run_id, samples=harness.samples)
    harness.unit_registry = registry
    if getattr(harness, "client", None) is not None:
        harness.client._slice_registry = registry
        harness.client._adapter._slice_registry = registry
    units = []
    for i in range(2):
        rel = registry.slice_relpath(sample.sample_id,i)
        path = harness.world.data_root/rel
        path.parent.mkdir(parents=True,exist_ok=True)
        raw = f"RIFF synthetic window{i}".encode()
        path.write_bytes(raw)
        record = SliceRecord(sample.sample_id,sample.audio_ref.path,sample.audio_ref.sha256,
            float(i),float(i+1),1.0,16000,rel,hashlib.sha256(raw).hexdigest(),len(raw),i)
        registry.register(record)
        units.append(ExecutionUnit(sample.sample_id,f"{sample.sample_id}#w{i+1:04d}",record))
    return ExecutionUnitRoster(tuple(units))

def _feature_windows(harness):
    from dataclasses import replace
    import struct
    from speech_aware_evidence_acquisition.core.model import (
        SpeechFeatureChunkData, materialize_speech_feature_packet,
    )
    from test_native_episode_runner import _MODEL_FILES

    raw = _windows(harness)
    units = []
    for index, unit in enumerate(raw.units):
        packet = materialize_speech_feature_packet(
            feature_root=harness.feature_root,
            packet_id=f"window/{index}",
            audio_sha256=unit.slice_record.sha256,
            encoder_receipt_sha256="e" * 64,
            decoder_gguf_sha256=_MODEL_FILES[0].sha256,
            mmproj_sha256=_MODEL_FILES[1].sha256,
            position_mode="mrope_1d", causal_attention=True,
            chunks=(SpeechFeatureChunkData(
                n_tokens=2, n_pos=2, n_embd=4,
                feature_bytes=struct.pack("<8f", *range(8)),
                position_bytes=struct.pack("<8i", 0,1,0,1,0,1,0,1),
            ),),
        )
        units.append(replace(
            unit, speech_packet_id=packet.packet_id,
            speech_packet_sha256=packet.packet_sha256,
        ))
    return ExecutionUnitRoster(tuple(units)), harness.unit_registry


def _runtime(harness, roster, material, values):
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values=values)
    runtime._model = runtime._dataset = runtime._baseline = {}
    runtime._adapter = harness.adapter
    runtime._samples = harness.samples
    runtime._data_root = harness.world.data_root
    runtime._split_id = "all"
    runtime._transport = harness.transport
    runtime._arm = lambda: harness.client.arm
    runtime._plan = harness.plan
    runtime.execution_unit_roster = lambda: roster
    runtime._phase_program_material = {
        "knowledge_snapshot": _knowledge_snapshot(),
        "speech_packet_bindings": harness.speech_bindings,
        "material_for_phase": material,
        "trace_sink": harness.trace,
        "query_source": harness.query_source, "execution_units": roster,
    }
    runtime._continuous_phase_runner = partial(run_continuous_program, slot_count=2)
    runtime._phase_planner_specs = lambda _policy: {}
    runtime._phase_decoding_params = lambda: {"temperature": 0, "max_tokens": 64}
    runtime._fit_base_plan = lambda plan: plan
    runtime._build_phase_tool_dispatcher = lambda *args, **kwargs: None
    return runtime

@pytest.mark.parametrize("features", [False, True])
def test_two_windows_have_independent_native_histories_contacts_and_budgets(tmp_path, monkeypatch, features):
    harness = _ActualEpisodeHarness(tmp_path, sample_count=1,max_revisions=0,max_contacts=4,
        planner_actions=("ACCEPT",),
        arm="speech-feature-query-native-tools" if features else "raw-speech-agent-native-tools",
        query_source="speech_features" if features else "speech_audio",
        execution_units_factory=_feature_windows if features else None,
        execution_plan=_plan(planned_model_calls=8))
    roster = harness.execution_units if features else _windows(harness)
    by_scope = {execution_unit_scope(u.request_key):u.request_key for u in roster.units}
    requests = {}
    lock = threading.Lock()
    first = threading.Barrier(2)
    def material(phase, context, sealed):
        return PhaseMaterial(instruction=f"Complete {phase} for {context.execution_unit_id}.",
            response_format=None,contact_id="material-"+phase,purpose=phase)
    def fit(request):
        body = harness.transport.render_request(request.payload_bytes)
        payload = request.as_payload()
        contact = payload["history"][-1]["contact_id"]
        scope, legacy = contact.split("/",1)
        unit = by_scope[scope]
        phase = legacy.split(":")[-3]
        with lock:
            requests[json.dumps(body,sort_keys=True)] = (unit,phase,contact,body)
    def post(url,body):
        with lock:
            unit,phase,contact,rendered = requests[json.dumps(json.loads(body),sort_keys=True)]
        if phase == "perception":
            first.wait(timeout=3)
        return _wire_response("ACCEPT" if phase == "planner" else f"{phase} answer for {unit}")
    harness.transport._post = post
    fit.receipts = []
    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": harness.config.episode_id,
            "max_revisions": 0,
            "actions": dict(zip(("accept", "revise", "acquire"), harness.config.actions)),
            "roles": {role.role_kind: {"phase_id": role.phase_id,
                      "max_iterations": role.max_iterations} for role in harness.config.roles},
        },
        "native_contact_fit": {"run_id": "SAEA-NATIVE-WINDOW-FIT",
            "attempt_id": "attempt-native-window-fit", "contact_cap": 8},
    }
    runtime = _runtime(harness, roster, material, values)
    monkeypatch.setattr(flight_module, "default_phase_program", lambda _policy: harness.program)
    monkeypatch.setattr(preparation_fit, "build_native_contact_fit_gate", lambda *_args: fit)
    try:
        rows, contacts, *_ = runtime._dispatch_phase_program(
            harness.client, harness.plan, harness.program.program_id)
        runtime._output_rows = rows
        summary = runtime._phase_summaries[0]
        canonical = runtime._canonical_output_rows(harness.client)
        assert contacts == 8
        assert len(canonical) == 1
        assert canonical[0]["text"] == "solver answer for s1#w0001 solver answer for s1#w0002"
        assert [row["execution_unit_id"] for row in canonical[0]["execution_unit_delivery"]["sources"]] == [
            "s1#w0001", "s1#w0002"]
        original = rows[0]["execution_unit_binding"]
        rows[0]["execution_unit_binding"] = rows[1]["execution_unit_binding"]
        with pytest.raises(FlightRuntimeError, match="changed its source binding"):
            runtime._canonical_output_rows(harness.client)
        rows[0]["execution_unit_binding"] = original
        runtime._trace_execution_unit_deliveries(harness.client, canonical)
    finally:
        closed = harness.close()
    assert closed["request_count"] == 8
    assert [len(result.contacts) for result in summary.results] == [4,4]
    assert len({contact.plan.contact_id for result in summary.results for contact in result.contacts}) == 8
    assert len({r.initial_query_state.query_id for r in summary.results}) == 2
    for result in summary.results:
        assert result.sample_id == "s1"
        assert result.metrics == {}
        assert result.final_response_text == f"solver answer for {result.execution_unit_id}"
        other = next(u.request_key for u in roster.units if u.request_key != result.execution_unit_id)
        for unit,phase,contact,body in requests.values():
            if unit == result.execution_unit_id:
                assert other not in json.dumps(body)
    records = [json.loads(line) for line in (
        harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl"
    ).read_text().splitlines()]
    ids = [row["record_id"] for row in records]
    assert len(ids) == len(set(ids))
    trace_payloads = {row["record_id"]: row["payload"] for row in records}
    _verify_outputs_trace_binding(tuple(canonical), trace_payloads)
    assert _minimum_model_calls_from_trace(trace_payloads) == 8


@pytest.mark.parametrize("reason, completion_tokens, second_text, expected", [
    ("stop", 3, "  second window  ", "first window second window"),
    ("length", 3, "truncated second window", "first window"),
    ("stop", 64, "cap reached", "first window"),
    ("stop", 3, "", "first window"),
])
@pytest.mark.parametrize("features", [False, True])
def test_direct_windows_share_dispatch_and_normalized_delivery(
    tmp_path, monkeypatch, reason, completion_tokens, second_text, expected, features,
):
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, max_revisions=0, max_contacts=4,
        planner_actions=("ACCEPT",),
        arm="speech-feature-query-native-tools" if features else "raw-speech-agent-native-tools",
        query_source="speech_features" if features else "speech_audio",
        execution_units_factory=_feature_windows if features else None,
        execution_plan=_plan(planned_model_calls=2),
    )
    roster = harness.execution_units if features else _windows(harness)
    program = default_phase_program("phase-direct-only-v1")
    def material(phase, context, sealed):
        return PhaseMaterial(
            instruction=f"Transcribe {context.execution_unit_id}.",
            response_format=None, contact_id="direct", purpose=phase,
        )
    runtime = _runtime(harness, roster, material, {})
    monkeypatch.setattr(flight_module, "default_phase_program", lambda _policy: program)
    raw_responses = []
    def post(url, body):
        first = "s1#w0001" in body.decode()
        text = "  first window  " if first else second_text
        response = json.loads(_wire_response(text))
        if not first:
            response["choices"][0]["finish_reason"] = reason
            response["usage"]["completion_tokens"] = completion_tokens
        raw_responses.append(text)
        return json.dumps(response).encode()
    harness.transport._post = post
    try:
        rows, contacts, *_ = runtime._dispatch_phase_program(harness.client, harness.plan, program.program_id)
        runtime._output_rows = rows
        canonical = runtime._canonical_output_rows(harness.client)
        assert contacts == 2
        assert canonical[0]["text"] == expected
        assert [row["final_response_text"] for row in rows] == ["  first window  ", second_text]
        runtime._trace_execution_unit_deliveries(harness.client, canonical)
    finally:
        closed = harness.close()
    assert closed["request_count"] == 2
    records = [json.loads(line) for line in (
        harness.world.run_dir / f"{harness.plan.run_id}.trace.jsonl"
    ).read_text().splitlines()]
    payloads = {row["record_id"]: row["payload"] for row in records}
    _verify_outputs_trace_binding(tuple(canonical), payloads)
    assert _minimum_model_calls_from_trace(payloads) == 2
    actual_responses = [row["payload"]["text"] for row in records
                       if row["channel"] == "MODEL_RESPONSE" and not row["payload"].get("stitch")]
    assert sorted(actual_responses) == sorted(raw_responses)
