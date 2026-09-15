"""Root integration evidence for independent native windows of one parent."""
import hashlib
import json
import threading

from speech_aware_evidence_acquisition.rails import build_slice_registry
from speech_aware_evidence_acquisition.core.model.slices import SliceRecord
from speech_aware_evidence_acquisition.rails.execution_units import ExecutionUnit, ExecutionUnitRoster, execution_unit_scope
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import NativeEpisodeRunBinding
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import _ActualEpisodeHarness, _plan, _wire_response
from test_rails_runner import _knowledge_snapshot

def _windows(harness):
    sample = harness.samples[0]
    registry = build_slice_registry(data_root=harness.world.data_root, run_id=harness.plan.run_id, samples=harness.samples)
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

def test_two_raw_windows_have_independent_native_histories_contacts_and_budgets(tmp_path):
    harness = _ActualEpisodeHarness(tmp_path, sample_count=1,max_revisions=0,max_contacts=4,
        planner_actions=("ACCEPT",),arm="raw-speech-agent-native-tools",query_source="speech_audio",
        execution_plan=_plan(planned_model_calls=8))
    roster = _windows(harness)
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
    binding = NativeEpisodeRunBinding(config=harness.config,program=harness.program,
        material_for_phase=material,render_request=harness.transport.render_request,request_gate=fit)
    try:
        summary = run_continuous_program(program=harness.program,adapter=harness.adapter,
            plan=harness.plan,data_root=harness.world.data_root,core_client=harness.client,
            split_id="all",knowledge_snapshot=_knowledge_snapshot(),speech_packet_bindings=harness.speech_bindings,
            query_source="speech_audio",execution_units=roster,trace_sink=harness.trace,
            decoding_params={"temperature":0,"max_tokens":64},material_for_phase=material,
            native_episode_binding=binding, slot_count=2)
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
    records = harness.trace.records
    ids = [row[1] for row in records]
    assert len(ids) == len(set(ids))
