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


def _real_adapter(harness, tmp_path, policy, *, lock=None, contract=CONTRACT):
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
        "task_instruction": contract,
        "serving_geometry": {"slots": 1, "slot_tokens": 8192, "max_tokens": 256},
        "server_args": ["-np", "1", "-c", "8192"],
        "decoding_params": {"max_tokens": 256},
    }
    return build_runtime_adapter(
        values, lock or {}, harness.world.data_root, repo, dataset_fragment="d",
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


def test_live_candidate_parameter_route_reaches_real_solver_request(tmp_path, monkeypatch):
    """Exercise the adapter, runtime resolver and OpenJiuwen episode together."""
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    from speech_aware_evidence_acquisition.data.audio2tool import render_tool_schemas
    from speech_aware_evidence_acquisition.rails.controllers import register_response_formats_v1
    from test_a2t_candidate_semantic_supply import _action, _route, _state

    program = default_phase_program("phase-audio2tool-native-candidates-review-revise-v1")
    store_binding, _ = _route(tmp_path, phase="solver", program=program)
    data_root = tmp_path / "data"
    lock = json.loads((tmp_path / "datasets.lock.json").read_text())
    task_contract = task_module.render_audio2tool_instruction(render_tool_schemas(lock, data_root))

    def forbidden(*args, **kwargs):
        raise AssertionError("Runtime may not read task rows, gold or invoke scoring.")

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
        run_id="SAEA-A2T-SYNTHETIC-CANDIDATE-SUPPLY",
        attempt_id="attempt-a2t-synthetic-candidate-supply", planned_model_calls=11,
    )
    harness = _ActualEpisodeHarness(
        tmp_path / "episode", data_root=data_root,
        sample_count=1, sample_ids=(sample_id,), max_revisions=1,
        max_contacts=11, planner_actions=("ACCEPT",),
        arm="speech-feature-query", execution_plan=plan,
    )
    harness.program = program
    adapter = _real_adapter(
        harness, tmp_path, program.program_id, lock=lock, contract=task_contract,
    )
    runtime = object.__new__(FlightRuntime)
    runtime._adapter = adapter
    runtime._composed = SimpleNamespace(values={})
    runtime._knowledge_store_binding = store_binding
    runtime._data_root = data_root
    supply_for_phase, specs = runtime._resolve_phase_supply(
        program, store_binding.composite_snapshot,
    )
    assert "solver" in specs
    receipt = runtime._phase_supply_receipt["candidate_supply"]
    assert receipt["candidate_inventory_authority"] == "audio2tool-public-tool-registry"
    assert receipt["candidate_inventory_source_sha256"] == adapter.candidate_inventory().source_sha256

    actions = [
        _action(0, ("syntheticTool003", "syntheticTool001", "syntheticTool003")),
        _action(1, ("syntheticTool001", "syntheticTool002")),
        _action(2, ("syntheticTool003",)),
        _action(3, ("syntheticTool001",)),
        _action(4, ("syntheticTool003",)),
    ]
    state_text = _state(actions, sample_id=sample_id).content
    final = json.dumps([
        {"name": "syntheticTool003", "arguments": {}},
        {"name": "syntheticTool149", "arguments": {}},
    ])
    # The final out-of-candidate choice is deliberate: candidates select
    # evidence, while the Solver retains the complete legal answer space.
    def output(key):
        return {
            "perception": state_text, "solver": final,
            "reviewer": "The final response is ready.", "planner": "ACCEPT",
        }[key[1]]

    harness._output = output
    register_response_formats_v1()
    from speech_aware_evidence_acquisition.rails.phase_material import (
        build_material_for_phase, load_phase_material_specs,
        render_static_instruction, resolve_response_formats,
    )
    material_config = {"phase_material": {}}
    for phase in program.phases:
        marker = f"native-role:{phase.name}:sample:{sample_id}:visit:1"
        harness.markers[(sample_id, phase.name, 1)] = marker
        relative = f"probes/synthetic-{phase.name}.txt"
        template = adapter._repo_root / "configs" / relative
        template.parent.mkdir(parents=True, exist_ok=True)
        template.write_text(marker)
        entry = {"instruction_template": relative,
                 "response_format_id": phase.response_format_id}
        if phase.name == "perception":
            entry["fill_params"] = {"max_actions": 7, "max_candidates_per_action": 4}
        material_config["phase_material"][phase.name] = entry
    material_specs = load_phase_material_specs(material_config, program)
    response_formats = resolve_response_formats(material_specs, lock, data_root)
    response_format = response_formats["perception"]
    material = build_material_for_phase(
        material_specs, program_id=program.program_id,
        static_text_by_phase={
            name: render_static_instruction(spec, adapter._repo_root, lock, data_root)
            for name, spec in material_specs.items()
        },
        response_format_by_phase=response_formats,
    )

    config = load_native_episode_config({
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "a2t-candidate-supply-proof", "max_revisions": 1,
            "actions": {"accept": "ACCEPT", "revise": "REVISE", "acquire": "ACQUIRE"},
            "roles": {
                role: {"phase_id": role, "max_iterations": 3 if role == "reviewer" else 1}
                for role in ("perception", "solver", "reviewer", "planner")
            },
        },
    }, program)
    native_binding = NativeEpisodeRunBinding(
        config=config, program=program, material_for_phase=material,
        render_request=harness.transport.render_request,
        request_gate=harness.request_gate, supply_for_phase=supply_for_phase,
    )
    try:
        summary = run_continuous_program(
            program=program, adapter=adapter, plan=plan, data_root=data_root,
            core_client=harness.client, split_id="all",
            knowledge_snapshot=store_binding.composite_snapshot,
            speech_packet_bindings=harness.speech_bindings, trace_sink=harness.trace,
            decoding_params={"max_tokens": 256, "temperature": 0},
            material_for_phase=material, supply_for_phase=supply_for_phase,
            slot_count=1, queue_depth=1, native_episode_binding=native_binding,
        )
    finally:
        closed = harness.close()

    result = summary.results[0]
    assert result.final_response_text == final
    assert len(result.contacts) == closed["request_count"] == 4
    assert closed["cost"]["tool_calls"] == 0
    solver = harness.prepared[(sample_id, "solver", 1, 1)]["rendered"]
    perception = harness.prepared[(sample_id, "perception", 1, 1)]["rendered"]
    assert perception["response_format"] == response_format
    assert solver["messages"][0]["content"] == task_contract
    assert "syntheticTool149" in task_contract
    solver_text = json.dumps(solver, ensure_ascii=False)
    perception_text = json.dumps(perception, ensure_ascii=False)
    snapshot = store_binding.snapshot_for("parameter-meaning")
    selected = {"syntheticTool003", "syntheticTool001", "syntheticTool002"}
    for value in snapshot.values:
        escaped_content = json.dumps(value.content, ensure_ascii=False)[1:-1]
        if value.task_target in selected:
            assert escaped_content in solver_text
            assert escaped_content not in perception_text
        else:
            assert escaped_content not in solver_text
    audits = list(receipt["candidate_selections"].values())
    assert len(audits) == 1
    assert audits[0]["candidate_occurrences"] == [
        {"action_id": row["action_id"], "candidate_tools": row["candidate_tools"]}
        for row in actions
    ]
    assert audits[0]["candidate_source_response_sha256"] == hashlib.sha256(state_text.encode()).hexdigest()
    assert audits[0]["candidate_inventory_source_sha256"] == adapter.candidate_inventory().source_sha256
    assert len(audits[0]["qualified_selected_value_ids"]) == 3
    assert ":solver:" in result.native_episode_receipt["accepted_solver_receipt"]["final_contact"]["agent_contact_id"]
