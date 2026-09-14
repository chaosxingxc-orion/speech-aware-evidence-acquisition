"""Audio2Tool uses the actual bounded role graph without answering-model contact.

Only speech bytes/packets, service responses and contact admission are synthetic.
This proves routing and source custody, not acoustic accuracy, capacity or scoring.
"""
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.adapters import audio2tool as task_module
from speech_aware_evidence_acquisition.rails.adapters.audio2tool_runtime import (
    Audio2ToolRuntimeAdapter, build_runtime_adapter,
)
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeRunBinding, load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
from speech_aware_evidence_acquisition.rails.phase_tools import TASK_CONTRACT_TOOL, build_phase_tools
from test_native_episode_runner import _ActualEpisodeHarness
from test_rails_frozen_core_client import _plan
from test_rails_runner import _knowledge_snapshot
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401

CONTRACT = (
    "Return all requested tool calls in request order as call strings. "
    "Repeated calls are distinct actions. Apply the latest explicit correction. "
    "Available tools: setLight(deviceId: string, state: string); "
    "setVolume(deviceId: string, level: number)."
)
FINAL = (
    'setLight(deviceId="desk", state="on"); '
    'setVolume(deviceId="speaker", level=20); '
    'setLight(deviceId="hall", state="off"); '
    'setLight(deviceId="desk", state="off"); '
    'setLight(deviceId="porch", state="on")'
)
STATE = json.dumps({
    "requested_actions": [
        {"tool": "setLight", "deviceId": "desk", "state": "on"},
        {"tool": "setVolume", "deviceId": "speaker", "level": 20},
        {"tool": "setLight", "deviceId": "hall", "state": "off"},
        {"tool": "setLight", "deviceId": "desk", "state": "off"},
        {"tool": "setLight", "deviceId": "porch", "state": "on"},
    ],
    "active_correction": {"field": "level", "superseded": 50, "active": 20},
}, sort_keys=True)


def _write(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _real_adapter(harness, tmp_path, policy):
    repo = tmp_path / "adapter-repo"
    rows = [
        {"sample_id": sample.sample_id, "key": "audio2tool:" + sample.sample_id,
         "media_relpath": sample.audio_ref.path, "audio_sha256": sample.audio_ref.sha256,
         "audio_seconds": sample.audio_seconds}
        for sample in harness.samples
    ]
    roster = {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "carrier": "audio2tool", "split_name": "all", "split_role": "discovery",
        "count": len(rows), "items": rows,
        "split_identity_hash": split_identity_hash(row["key"] for row in rows),
        "flight_split_identity_hash": harness.plan.split_identity_hash,
    }
    rel = "docs/receipts/synthetic-native-a2t.json"
    digest = _write(repo / rel, roster)
    dataset = {
        "carrier_lock_key": "audio2tool", "split_id": "all",
        "a2t_calibration_subset_receipt": rel,
        "a2t_calibration_subset_receipt_sha256": digest,
        "a2t_calibration_split_name": "all",
        "a2t_calibration_split_role": "discovery",
        "a2t_calibration_split_identity_hash": roster["split_identity_hash"],
        "a2t_calibration_flight_split_identity_hash": roster["flight_split_identity_hash"],
        "a2t_calibration_count": len(rows),
    }
    _write(repo / "configs/dataset/d.json", dataset)
    values = {
        **dataset, "policy": policy, "task_contract_source": "active-instruction",
        "task_instruction": CONTRACT,
        "serving_geometry": {"slots": 1, "slot_tokens": 8192, "max_tokens": 256},
        "server_args": ["-np", "1", "-c", "8192"],
        "decoding_params": {"max_tokens": 256},
    }
    return build_runtime_adapter(
        values, {}, harness.world.data_root, repo, dataset_fragment="d",
    )


@pytest.mark.parametrize("revise", [False, True])
def test_real_a2t_adapter_preserves_multi_action_state_and_solver_authority(
    tmp_path, monkeypatch, revise,
):
    def forbidden(*args, **kwargs):
        raise AssertionError("No target, raw task manifest or scorer may enter this proof.")

    from speech_aware_evidence_acquisition.data import audio2tool as raw_loader
    for name in ("load_expected_calls", "load_audio2tool", "audio2tool_receipts"):
        monkeypatch.setattr(task_module, name, forbidden)
    monkeypatch.setattr(raw_loader, "load_query_rows", forbidden)
    monkeypatch.setattr(Audio2ToolRuntimeAdapter, "gold", forbidden)
    monkeypatch.setattr(Audio2ToolRuntimeAdapter, "score_response", forbidden)

    sample_id = "tier3_multi_intent:000001"
    identity = split_identity_hash(prefixed("audio2tool", [sample_id]))
    plan = _plan(
        carrier_lock_key="audio2tool", split_identity_hash=identity,
        run_id="SAEA-A2T-SYNTHETIC-NATIVE", attempt_id="attempt-a2t-synthetic-native",
        planned_model_calls=11,
    )
    harness = _ActualEpisodeHarness(
        tmp_path, sample_count=1, sample_ids=(sample_id,), max_revisions=1,
        max_contacts=11, planner_actions=("REVISE", "ACCEPT") if revise else ("ACCEPT",),
        reviewer_task_tool=revise,
        arm="speech-feature-query-native-tools" if revise else "speech-feature-query",
        execution_plan=plan,
    )
    program = default_phase_program("phase-native-review-revise-v1")
    harness.program = program
    adapter = _real_adapter(harness, tmp_path, program.program_id)
    direct_adapter = _real_adapter(harness, tmp_path, "phase-direct-only-v1")
    assert isinstance(adapter, Audio2ToolRuntimeAdapter)
    assert adapter.load_split("all") == direct_adapter.load_split("all")
    assert adapter.build_task_contract(harness.samples[0], None) == CONTRACT
    assert direct_adapter.build_task_contract(harness.samples[0], None) == CONTRACT

    values = {
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "a2t-synthetic-native", "max_revisions": 1,
            "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
            "roles": {
                phase: {"phase_id": phase, "max_iterations": 3 if phase == "reviewer" else 1}
                for phase in ("perception", "solver", "reviewer", "planner")
            },
        },
    }
    if revise:
        values["phase_tools"] = {
            "reviewer": {
                "mode": "native-tools", "allowed_tools": [TASK_CONTRACT_TOOL],
                "knowledge_views": ["text"], "source_authority_role": "reviewer",
            },
        }
    config = load_native_episode_config(values, program)
    if revise:
        harness.tools_for_phase = build_phase_tools(
            values, program, snapshot=_knowledge_snapshot(),
            tool_contact=harness.tools_for_phase.tool_contact,
        )

    def output(key):
        _sample_id, role, visit, turn = key
        if role == "perception":
            return STATE
        if role == "solver":
            return FINAL.replace("level=20", "level=50") if revise and visit == 1 else FINAL
        if role == "reviewer":
            if revise and visit == turn == 1:
                return None
            return "Use the active volume correction of 20." if revise else "No revision needed."
        return harness.planner_actions[visit - 1]

    harness._output = output
    material = harness.material_for_phase
    binding = NativeEpisodeRunBinding(
        config=config, program=program, material_for_phase=material,
        render_request=harness.transport.render_request,
        request_gate=harness.request_gate, tools_for_phase=harness.tools_for_phase,
    )
    try:
        summary = run_continuous_program(
            program=program, adapter=adapter, plan=plan,
            data_root=harness.world.data_root, core_client=harness.client,
            split_id="all", knowledge_snapshot=_knowledge_snapshot(),
            speech_packet_bindings=harness.speech_bindings, trace_sink=harness.trace,
            decoding_params={"max_tokens": 256, "temperature": 0},
            material_for_phase=material, tools_for_phase=harness.tools_for_phase,
            slot_count=1, queue_depth=1, native_episode_binding=binding,
        )
    finally:
        closed = harness.close()

    result = summary.results[0]
    assert result.final_response_text == FINAL
    assert result.final_response_text.count("setLight(") == 4
    assert len(result.final_response_text.split("; ")) == 5
    assert len(result.contacts) == closed["request_count"] == (8 if revise else 4)
    episode = result.native_episode_receipt
    accepted = episode["accepted_solver_receipt"]["final_contact"]
    assert ":solver:" in accepted["agent_contact_id"]
    assert accepted["response_text_sha256"] == hashlib.sha256(FINAL.encode()).hexdigest()
    assert [row["action"] for row in episode["planner_routes"]] == (
        ["REVISE", "ACCEPT"] if revise else ["ACCEPT"]
    )
    bodies = [entry["rendered"] for entry in harness.prepared.values()]
    assert all(body["messages"][0]["content"] == CONTRACT for body in bodies)
    solver = harness.prepared[(sample_id, "solver", 2 if revise else 1, 1)]["rendered"]
    assert STATE in json.dumps(solver, ensure_ascii=False).replace("\\\"", "\"")
    # All roles retain the same source packet; task-target tools never become
    # executable analytical abilities.
    def content_blocks(value):
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from content_blocks(child)
        elif isinstance(value, list):
            for child in value:
                yield from content_blocks(child)

    for key, entry in harness.prepared.items():
        body = entry["rendered"]
        packets = [
            block["speech_features"]
            for block in content_blocks(body)
            if block.get("type") == "input_speech_features"
        ]
        assert packets
        assert all(
            packet["packet_id"] == harness.speech_bindings[sample_id]["packet_id"]
            and packet["sha256"] == harness.speech_bindings[sample_id]["sha256"]
            for packet in packets
        )
        executable = {tool["function"]["name"] for tool in body.get("tools", [])}
        assert executable <= ({TASK_CONTRACT_TOOL} if key[1] == "reviewer" and revise else set())
    assert closed["cost"]["tool_calls"] == int(revise)
    if revise:
        for key in [(sample_id, "reviewer", 1, 2), (sample_id, "solver", 2, 1)]:
            messages = harness.prepared[key]["rendered"]["messages"]
            tool_messages = [message for message in messages if message["role"] == "tool"]
            assert len(tool_messages) == 1
            assert json.loads(tool_messages[0]["content"])["result"] == {"task_contract": CONTRACT}
