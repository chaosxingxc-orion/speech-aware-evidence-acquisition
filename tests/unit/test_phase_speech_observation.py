"""Exercise cached OBS evidence through the shared controller and request builder."""

from dataclasses import replace
import hashlib
import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.phase_tools import build_phase_tools, PhaseToolError
from speech_aware_evidence_acquisition.rails.speech_observation import (
    PREPARED_SPEECH_OBSERVATION_TOOL as OBS,
    SpeechObservationSelection,
)
from speech_aware_evidence_acquisition.rails.runner import _agent_messages
from test_phase_tools import _context, staged
from test_phase_planner import _material
from test_rails_runner import _knowledge_snapshot


def config(mode="fixed", **arguments):
    args = {"span": "full-utterance", "representation": "asr-transcript",
            "distinction": "Check the spoken number."}
    args.update(arguments)
    entry = {"mode": mode, "allowed_tools": [OBS]}
    if mode == "fixed":
        entry["fixed_action"] = {"tool_id": OBS, "arguments": args}
    return {"phase_tools": {"draft": entry}}


class Catalog:
    def __init__(self, context, status="ok"):
        self.query = context.query_state
        self.status = status

    def select(self, *, context):
        q = context.query_state
        if (q.query_sample_id, q.use_split_identity_hash, q.speech_packet_id,
            q.speech_packet_sha256) != (
            self.query.query_sample_id, self.query.use_split_identity_hash,
            self.query.speech_packet_id, self.query.speech_packet_sha256,
        ):
            raise RailsError("foreign speech observation source")
        return SpeechObservationSelection(
            visible={"schema": "saea-prepared-speech-observation-v1",
                     "evidence_id": "obs-one", "artifact_sha256": "a" * 64,
                     "source_uri": "prepared-speech-observation://" + "a" * 64 + "/obs-one",
                     "status": self.status,
                     "transcript": "Set the timer for fifteen minutes." if self.status == "ok" else "",
                     "sample_id": q.query_sample_id,
                     "use_split_identity_hash": q.use_split_identity_hash,
                     "speech_packet_id": q.speech_packet_id,
                     "speech_packet_sha256": q.speech_packet_sha256},
            lineage={"producer_run_id": "PREP-ONE",
                     "ledger_row": {"relpath": "docs/exposure-ledger.md", "sha256": "b" * 64},
                     "preparation_contacts": {"calls": 1000, "audio_seconds": 4000},
                     "new_neural_contacts": 0},
        )

    def receipt(self):
        return {"prepared_count": 1000, "producer_contacts": {"calls": 1000},
                "new_neural_contacts": 0}


class Sink:
    def __init__(self):
        self.events = []

    def emit(self, axis, record_id, payload):
        self.events.append((axis, record_id, payload))


def dispatcher(ctx, *, cfg=None, status="ok", sink=None):
    return build_phase_tools(
        cfg or config(), rc.default_phase_program("phase-draft-revise-v1"),
        snapshot=_knowledge_snapshot(), speech_observations=Catalog(ctx, status),
        trace_sink=sink,
    )


def test_unbound_observation_action_is_rejected_before_dispatch():
    with pytest.raises(PhaseToolError, match="speech observation"):
        build_phase_tools(config(), rc.default_phase_program("phase-draft-revise-v1"),
                          snapshot=_knowledge_snapshot())


@pytest.mark.parametrize("bad", [
    {"span": "word-7"}, {"representation": "answer"}, {"distinction": ""},
    {"distinction": "x" * 513}, {"path": "/other.wav"},
])
def test_action_cannot_invent_a_span_or_answer_representation(bad):
    with pytest.raises(PhaseToolError):
        dispatcher(_context(), cfg=config(**bad))


@pytest.mark.parametrize("mode", ["fixed", "core-choice"])
def test_cached_obs_reaches_actual_solver_request_and_solver_owns_answer(mode):
    ctx = _context()
    sink = Sink()
    tool = dispatcher(ctx, cfg=config(mode), sink=sink)
    controller = rc.EvidenceAgentController(
        program=rc.default_phase_program("phase-draft-revise-v1"),
        material_for_phase=_material, tools_for_phase=tool,
    )
    contact = controller.initial_contact(ctx)
    draft = "Set a fifty minute timer."
    if mode == "core-choice":
        draft = json.dumps({"tool_id": OBS, "arguments": config()["phase_tools"]["draft"]["fixed_action"]["arguments"],
                            "query_state_sha256": ctx.query_state.content_hash()})
        assert OBS in contact.instruction
        assert "full-utterance" in contact.instruction
    move = controller.advance(ctx, contact, draft)
    assert "fifteen" not in move.new_agent_states[-1].content
    ctx2 = replace(ctx, query_state=move.next_query_state, agent_states=move.new_agent_states,
                   prior_response_sha256s=(hashlib.sha256(draft.encode()).hexdigest(),), contact_index=1)
    adapter = SimpleNamespace(assemble_prompt=lambda *_: (
        {"role": "system", "content": "Follow the task contract."},
        {"role": "user", "content": "Original speech"},
    ))
    messages = _agent_messages(
        adapter=adapter, sample=object(), task_contract=ctx.task_contract,
        snapshot=_knowledge_snapshot(), snapshot_sha256=ctx.knowledge_snapshot_sha256,
        query_state=ctx2.query_state, agent_states=ctx2.agent_states,
        knowledge_value_renderer=tool.render_values,
    )
    blocks = messages[1]["content"]
    assert blocks[0]["type"] == "input_speech_features"
    obs = [block for block in blocks if block.get("evidence_id") == "obs-one"]
    assert len(obs) == 1
    assert "fifteen" in obs[0]["text"]
    assert "knowledge_role" not in obs[0]
    assert obs[0]["source_uri"] == "prepared-speech-observation://" + "a" * 64 + "/obs-one"
    assert all(axis == "OBS" for axis, _, _ in sink.events)
    assert "obs_internal_observation_lineage" in sink.events[-1][2]
    receipt = tool.receipt()["speech_observations"]
    assert receipt["prepared_count"] == 1000
    assert receipt["supplied_samples"] == 1
    assert receipt["new_neural_contacts"] == 0
    final = controller.advance(ctx2, move.next_contact, "Final Solver answer")
    assert final.final_response_contact_id == move.next_contact.contact_id


@pytest.mark.parametrize("status", ["empty", "timeout", "unsupported"])
def test_unusable_asr_is_explicit_evidence_without_a_fabricated_transcript(status):
    ctx = _context()
    tool = dispatcher(ctx, status=status)
    result = tool("draft", "revise", staged("Draft", ctx))
    query = replace(ctx.query_state, agent_state_ids=(result.state.state_id,))
    blocks = tool.render_values(_knowledge_snapshot(), query, (result.state,))
    assert len(blocks) == 1
    assert status in blocks[0]["text"]
    assert "No usable transcription" in blocks[0]["text"]


def test_renderer_refuses_modified_or_cross_sample_observation():
    ctx = _context()
    tool = dispatcher(ctx)
    result = tool("draft", "revise", staged("Draft", ctx))
    query = replace(ctx.query_state, agent_state_ids=(result.state.state_id,))
    doc = json.loads(result.state.content)
    doc["result"]["transcript"] = "Injected answer."
    changed = replace(result.state, content=json.dumps(doc))
    with pytest.raises(PhaseToolError):
        tool.render_values(_knowledge_snapshot(), query, (changed,))
    foreign = replace(query, query_sample_id="other")
    with pytest.raises(RailsError):
        tool.render_values(_knowledge_snapshot(), foreign, (result.state,))


@pytest.mark.parametrize("extra", [
    {"prepared_speech_observations": {"relpath": "obs.json", "sha256": "a" * 64}},
    {"phase_tools": config()["phase_tools"]},
])
def test_runtime_refuses_inert_or_missing_observation_binding_before_gate(extra, tmp_path):
    from test_flight_runtime import _make_runtime, _FakeGate
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError
    gate = _FakeGate()
    runtime = _make_runtime(tmp_path, gate=gate,
                            config_kwargs={"policy": "phase-draft-revise-v1", "baseline_extra": extra})
    with pytest.raises(FlightRuntimeError, match="speech"):
        runtime.preflight()
    assert not gate.calls


def test_extended_audio_binding_preserves_legacy_shape_and_binds_full_duration(tmp_path):
    from test_prepared_phase_supply import setup_runtime
    runtime, _binding, _program = setup_runtime(tmp_path)
    runtime._samples = [SimpleNamespace(
        sample_id="s1", audio_ref=SimpleNamespace(path="speech/one.wav", sha256="c" * 64),
        audio_seconds=2.5,
    )]
    runtime.speech_packet_bindings = lambda: {"s1": {"packet_id": "packet-one", "sha256": "d" * 64}}
    legacy = runtime.source_audio_bindings()
    assert set(legacy["s1"]) == {"packet_id", "packet_sha256", "source_audio_sha256"}
    extended = runtime.source_audio_bindings(include_address=True)
    assert extended["s1"] == {**legacy["s1"], "source_audio_relpath": "speech/one.wav",
                             "source_audio_duration_seconds": 2.5}


@pytest.mark.parametrize("path,duration", [
    ("/outside.wav", 2.5), ("../outside.wav", 2.5), ("a//b.wav", 2.5),
    ("speech" + chr(92) + "one.wav", 2.5),
    ("a.wav", float("nan")), ("a.wav", True), ("a.wav", 0),
])
def test_extended_audio_binding_rejects_invalid_address_or_duration(tmp_path, path, duration):
    from test_prepared_phase_supply import setup_runtime
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError
    runtime, _binding, _program = setup_runtime(tmp_path)
    runtime._samples = [SimpleNamespace(
        sample_id="s1", audio_ref=SimpleNamespace(path=path, sha256="c" * 64),
        audio_seconds=duration,
    )]
    runtime.speech_packet_bindings = lambda: {"s1": {"packet_id": "packet-one", "sha256": "d" * 64}}
    with pytest.raises(FlightRuntimeError, match="source address or duration"):
        runtime.source_audio_bindings(include_address=True)
