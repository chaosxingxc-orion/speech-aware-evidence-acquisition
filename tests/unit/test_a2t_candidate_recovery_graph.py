"""Synthetic CPU proof of bounded Audio2Tool candidate recovery.

The actual OpenJiuwen workflow and shared runner are exercised. Speech packets,
transport responses, and knowledge sources are synthetic; no task rows, gold,
scoring, network service, or model are used.
"""

from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_candidate_supply import (
    analyze_a2t_candidate_supply,
)
from speech_aware_evidence_acquisition.analysis.native_episode_source import (
    VerifiedNativeEpisodeSource,
)
from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle
from speech_aware_evidence_acquisition.core.config import ComposedConfig
from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.data.audio2tool import load_tool_registry
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails.adapters import audio2tool as task_module
from speech_aware_evidence_acquisition.rails.adapters.audio2tool_runtime import (
    Audio2ToolRuntimeAdapter,
)
from speech_aware_evidence_acquisition.rails.a2t_response_schema import (
    audio2tool_perception_state_response_format,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    load_phase_program,
    native_planner_action_response_format,
)
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeRunBinding,
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    validate_native_candidate_refresh_receipt,
)
from speech_aware_evidence_acquisition.rails.phase_runner import run_continuous_program
from speech_aware_evidence_acquisition.rails.phase_tools import build_phase_tools
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)

import test_knowledge_stores as store_fixtures
import test_native_episode_runner as episode_runner
from test_audio2tool_native_episode_integration import _real_adapter
from test_compiled_knowledge_store_preparation import _prepared
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_target_knowledge_tools import TARGET, _args
from test_rails_frozen_core_client import _plan


ALPHA = "syntheticTool001"
BETA = "syntheticTool002"
POLICY = "phase-audio2tool-native-candidate-recovery-tools-v1"
REFRESH = "REFRESH_CANDIDATES"


def _visible(content, rendered):
    return json.dumps(content, ensure_ascii=False)[1:-1] in rendered


def _refresh_count(receipt):
    return validate_native_candidate_refresh_receipt(
        receipt,
        refresh_action=REFRESH,
        max_refreshes=1,
        max_revisions=1,
        accept_action="ACCEPT",
        revise_action="REVISE",
    )


def _perception_state(candidates):
    return json.dumps(
        {
            "actions": [
                {
                    "action_id": "action:0",
                    "candidate_tools": list(candidates),
                    "evidence": "The bound speech supports this action occurrence.",
                    "uncertain_arguments": [],
                }
            ],
            "global_constraints": ["Preserve the action identity and order."],
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def _activation_snapshot(store_id, original):
    base = original(store_id)
    template = base.values[0]
    return replace(
        base,
        source_partition_role="external-governed",
        values=tuple(
            replace(
                template,
                value_id=f"activation:{target}",
                task_target=target,
                content=f"activation evidence for {target}",
            )
            for target in (ALPHA, BETA)
        ),
    ).validate()


def _knowledge_binding(tmp_path, monkeypatch):
    repo, prepared, registration_path, _registration = _prepared(
        tmp_path / "compiled", "parameter-meaning"
    )
    completion = prepare_semantic_knowledge_store(
        registration_path,
        repo_root=repo,
        data_root=prepared.data_root,
    )["completion"]
    original = store_fixtures._store_snapshot
    monkeypatch.setattr(
        store_fixtures,
        "_store_snapshot",
        lambda store_id: _activation_snapshot(store_id, original),
    )
    activation, _snapshots = store_fixtures._config(
        prepared.data_root, ("tool-activation",)
    )
    activation_store = activation["knowledge_stores"]["tool-activation"]
    activation_store.pop("phase_supply")
    parameter_store = {
        "store_role": "parameter-meaning",
        "snapshot": completion["snapshot"],
        "release": completion["release"],
        "candidate_supply": {
            "solver": {
                "provider": "audio2tool-candidate-semantic-v1",
                "rank_policy": "saea-ranked-candidate-round-robin-v1",
                "fuse_policy": "saea-candidate-semantic-passthrough-v1",
                "candidate_state_phase": "perception",
                "candidate_state_selection": "latest",
                "compact_source_phase": "perception",
                "max_actions": 8,
                "max_candidates_per_action": 4,
                "max_values_per_candidate": 1,
                "max_total_values": 32,
            }
        },
    }
    values = {
        "knowledge_stores": {
            "tool-activation": activation_store,
            "parameter-meaning": parameter_store,
        }
    }
    return (
        load_knowledge_store_binding(values, data_root=prepared.data_root),
        prepared,
        values,
    )


def _phase_tool_config():
    role = {
        "mode": "native-tools",
        "allowed_tools": [TARGET],
        "knowledge_views": ["text"],
        "knowledge_store_ids": ["tool-activation", "parameter-meaning"],
        "candidate_limit": 4,
        "knowledge_values_per_candidate": 1,
        "knowledge_value_limit": 4,
    }
    return {
        "phase_tools": {
            name: {**role, "source_authority_role": name}
            for name in ("reviewer", "planner")
        }
    }


def _native_values(store_values):
    return {
        **store_values,
        **_phase_tool_config(),
        "native_episode": {
            "schema": "saea-native-episode-config-v1",
            "episode_id": "a2t-candidate-recovery-cpu-proof-v1",
            "max_revisions": 1,
            "actions": {
                "accept": "ACCEPT",
                "revise": "REVISE",
                "acquire": "ACQUIRE",
            },
            "candidate_refresh": {"action": REFRESH, "max_refreshes": 1},
            "roles": {
                "perception": {"phase_id": "perception", "max_iterations": 1},
                "solver": {"phase_id": "solver", "max_iterations": 1},
                "reviewer": {"phase_id": "reviewer", "max_iterations": 3},
                "planner": {"phase_id": "planner", "max_iterations": 2},
            },
            "tool_iteration_policy": "reserve-final-report",
            "exhaustion_policy": "deliver-latest-solver",
            "finite_completion_policy": "deliver-latest-or-abstain",
            "planner_output_format": "json-action-v1",
        },
    }


def _target_wire(_tool_id):
    arguments = _args(store="tool-activation", ids=(BETA,))
    return json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Inspect the competing activation target.",
                        "tool_calls": [
                            {
                                "id": "call-target-beta",
                                "type": "function",
                                "function": {
                                    "name": TARGET,
                                    "arguments": json.dumps(
                                        arguments, sort_keys=True, separators=(",", ":")
                                    ),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        },
        separators=(",", ":"),
    ).encode()


def _material_builder(harness, perception_format):
    planner_format = native_planner_action_response_format(
        ("ACCEPT", "REVISE", REFRESH)
    )

    def material_for_phase(phase, context, _sealed):
        key = (context.sample_id, phase)
        harness.material_visits[key] += 1
        visit = harness.material_visits[key]
        marker = f"native-role:{phase}:sample:{context.sample_id}:visit:{visit}"
        harness.markers[(context.sample_id, phase, visit)] = marker
        return PhaseMaterial(
            instruction=marker,
            response_format=(
                perception_format
                if phase == "perception"
                else planner_format
                if phase == "planner"
                else None
            ),
            contact_id=marker,
            purpose=phase,
        ).validate()

    return material_for_phase


def _run(tmp_path, monkeypatch, *, refresh):
    policy_path = (
        task_module.REPO_ROOT
        / "configs/policy/phase-audio2tool-native-candidate-recovery-tools-v1.json"
    )
    program = load_phase_program(policy_path)
    assert program.program_id == POLICY and program.max_contacts == 14
    binding, prepared, store_values = _knowledge_binding(tmp_path, monkeypatch)
    values = _native_values(store_values)

    monkeypatch.setattr(
        episode_runner, "_knowledge_snapshot", lambda: binding.composite_snapshot
    )
    monkeypatch.setattr(episode_runner, "TASK_CONTRACT_TOOL", TARGET)
    monkeypatch.setattr(episode_runner, "_wire_tool_call", _target_wire)
    original_builder = episode_runner.build_phase_tools

    def target_tools(_config, active_program, *args, **kwargs):
        return original_builder(
            _phase_tool_config(),
            active_program,
            *args,
            **kwargs,
            knowledge_stores=binding,
        )

    monkeypatch.setattr(episode_runner, "build_phase_tools", target_tools)
    sample_id = "tier3_multi_intent:000001"
    identity = split_identity_hash(prefixed("audio2tool", [sample_id]))
    plan = _plan(
        carrier_lock_key="audio2tool",
        split_identity_hash=identity,
        run_id=f"SAEA-A2T-CANDIDATE-RECOVERY-CPU-{'REFRESH' if refresh else 'ACCEPT'}",
        attempt_id=f"attempt-a2t-candidate-recovery-{'refresh' if refresh else 'accept'}",
        planned_model_calls=14,
    )
    harness = episode_runner._ActualEpisodeHarness(
        tmp_path / "episode",
        data_root=prepared.data_root,
        sample_count=1,
        sample_ids=(sample_id,),
        max_revisions=1,
        max_contacts=14,
        planner_actions=(),
        reviewer_task_tool=True,
        arm="speech-feature-query-native-tools",
        execution_plan=plan,
    )
    harness.program = program
    config = load_native_episode_config(values, program)
    harness.config = config
    custody = harness.tools_for_phase.tool_contact
    harness.tools_for_phase = build_phase_tools(
        values,
        program,
        snapshot=binding.composite_snapshot,
        knowledge_stores=binding,
        tool_contact=custody,
    )
    lock = json.loads((tmp_path / "compiled/datasets.lock.json").read_text())
    adapter = _real_adapter(
        harness,
        tmp_path,
        program.program_id,
        lock=lock,
        contract="Synthetic Audio2Tool contract for alpha and beta.",
    )
    runtime = object.__new__(FlightRuntime)
    runtime._adapter = adapter
    runtime._composed = SimpleNamespace(values=values)
    runtime._knowledge_store_binding = binding
    runtime._data_root = prepared.data_root
    supply_for_phase, specs = runtime._resolve_phase_supply(
        program, binding.composite_snapshot
    )
    assert specs["solver"].candidate_state_selection == "latest"
    receipt = runtime._phase_supply_receipt["candidate_supply"]
    inventory = adapter.candidate_inventory()
    routing_receipt = runtime._phase_supply_receipt
    routes = runtime._knowledge_store_supply.specs_by_store
    rows = load_tool_registry(lock, prepared.data_root)
    perception_format = audio2tool_perception_state_response_format(
        rows, max_actions=8, max_candidates_per_action=4
    )
    material = _material_builder(harness, perception_format)
    harness.material_for_phase = material

    initial = _perception_state((ALPHA,))
    recovered = _perception_state((ALPHA, BETA))
    final = json.dumps([{"name": BETA, "arguments": {}}], separators=(",", ":"))

    def output(key):
        _sample, phase, visit, turn = key
        if phase == "perception":
            return recovered if visit == 2 else initial
        if phase == "solver":
            return (
                final
                if visit == 2
                else json.dumps(
                    [{"name": ALPHA, "arguments": {}}], separators=(",", ":")
                )
            )
        if phase == "reviewer":
            if refresh and visit == turn == 1:
                return None
            return "Review complete."
        if phase == "planner":
            action = REFRESH if refresh and visit == 1 else "ACCEPT"
            return json.dumps({"action": action}, separators=(",", ":"))
        raise AssertionError(key)

    harness._output = output
    native_binding = NativeEpisodeRunBinding(
        config=config,
        program=program,
        material_for_phase=material,
        render_request=harness.transport.render_request,
        request_gate=harness.request_gate,
        tools_for_phase=harness.tools_for_phase,
        supply_for_phase=supply_for_phase,
    )

    def forbidden(*_args, **_kwargs):
        raise AssertionError("No task row, gold, or scorer may enter this proof.")

    from speech_aware_evidence_acquisition.data import audio2tool as raw_loader

    for name in ("load_expected_calls", "load_audio2tool", "audio2tool_receipts"):
        monkeypatch.setattr(task_module, name, forbidden)
    monkeypatch.setattr(raw_loader, "load_query_rows", forbidden)
    monkeypatch.setattr(Audio2ToolRuntimeAdapter, "gold", forbidden)
    monkeypatch.setattr(Audio2ToolRuntimeAdapter, "score_response", forbidden)
    try:
        summary = run_continuous_program(
            program=program,
            adapter=adapter,
            plan=plan,
            data_root=prepared.data_root,
            core_client=harness.client,
            split_id="all",
            knowledge_snapshot=binding.composite_snapshot,
            speech_packet_bindings=harness.speech_bindings,
            trace_sink=harness.trace,
            decoding_params={"max_tokens": 256, "temperature": 0},
            material_for_phase=material,
            supply_for_phase=supply_for_phase,
            tools_for_phase=harness.tools_for_phase,
            slot_count=1,
            queue_depth=1,
            native_episode_binding=native_binding,
        )
    finally:
        closed = harness.close()
    result = summary.results[0]
    trace_records = {
        record_id: payload for _channel, record_id, payload in harness.trace.records
    }
    source = VerifiedNativeEpisodeSource(
        bundle=VerifiedBundle(
            manifest_path=Path("synthetic-manifest.json"),
            manifest={},
            outputs_path=None,
            outputs_rows=(),
            trace_records=trace_records,
            split_ids=frozenset({sample_id}),
            attempt_state="FINALIZED",
        ),
        composed=ComposedConfig(values=values, config_hash="0" * 64, fragments={}),
        plan=plan,
        sample_ids=(sample_id,),
        phase_results={sample_id: result.as_json()},
        output_rows={},
        phase_artifact_sha256="0" * 64,
        diagnostics={},
    )
    flight_receipts = FlightReceipts(plan.run_id, plan.attempt_id)
    for stage, payload in (
        ("preflight", {}),
        ("preprocess", {}),
        ("serve", {}),
        ("run_phases", {"phase_supply": routing_receipt}),
    ):
        flight_receipts.record(stage, payload)
    return SimpleNamespace(
        result=result,
        harness=harness,
        closed=closed,
        binding=binding,
        routing_receipt=routing_receipt,
        routes=routes,
        receipt=receipt,
        source=source,
        flight_receipts=flight_receipts.as_json(),
        inventory=inventory,
        data_root=prepared.data_root,
        initial=initial,
        recovered=recovered,
        final=final,
    )


def _candidate_report(run):
    return analyze_a2t_candidate_supply(
        run.source,
        flight_receipts=run.flight_receipts,
        candidate_inventory=run.inventory,
        data_root=run.data_root,
    )


@pytest.mark.usefixtures("_spawn_live_matching_process")
def test_refresh_adds_targeted_activation_then_latest_candidate_parameter_evidence(
    tmp_path, monkeypatch
):
    run = _run(tmp_path, monkeypatch, refresh=True)
    candidate_report = _candidate_report(run)
    candidate_row = candidate_report["samples"][0]

    assert candidate_report["schema"] == "saea-a2t-candidate-supply-attribution-v2"
    assert candidate_row["initial"]["unique_candidate_ids"] == [ALPHA]
    assert candidate_row["last_attempted"]["unique_candidate_ids"] == [ALPHA, BETA]
    assert candidate_row["operative"]["candidate_source"]["unique_candidate_ids"] == [
        ALPHA,
        BETA,
    ]
    assert (
        candidate_row["operative"]["candidate_source"]["perception"]["agent_state_id"]
        == candidate_row["last_attempted"]["perception"]["agent_state_id"]
    )
    analyzed_latest = candidate_row["perception_visits"][1]["selections"][0]
    assert analyzed_latest["already_visible_value_ids"] == [
        f"parameter-meaning::a2t-native-card:{ALPHA}:value"
    ]
    assert analyzed_latest["added_value_ids"] == [
        f"parameter-meaning::a2t-native-card:{BETA}:value"
    ]
    assert run.result.final_response_text == run.final
    assert len(run.result.contacts) == run.closed["request_count"] == 9
    assert run.closed["cost"]["tool_calls"] == 1
    assert [key[1] for key in run.harness.prepared] == [
        "perception",
        "solver",
        "reviewer",
        "reviewer",
        "planner",
        "perception",
        "solver",
        "reviewer",
        "planner",
    ]
    episode = run.result.native_episode_receipt
    assert [route["action"] for route in episode["planner_routes"]] == [
        REFRESH,
        "ACCEPT",
    ]
    perceptions = [
        visit for visit in episode["role_visits"] if visit["stage"] == "perception"
    ]
    assert len(perceptions) == 2
    assert _refresh_count(episode) == 1
    assert (
        ":solver:"
        in episode["accepted_solver_receipt"]["final_contact"]["agent_contact_id"]
    )

    first_perception = json.dumps(
        run.harness.prepared[("tier3_multi_intent:000001", "perception", 1, 1)][
            "rendered"
        ],
        ensure_ascii=False,
    )
    first_solver = json.dumps(
        run.harness.prepared[("tier3_multi_intent:000001", "solver", 1, 1)]["rendered"],
        ensure_ascii=False,
    )
    next_reviewer = json.dumps(
        run.harness.prepared[("tier3_multi_intent:000001", "reviewer", 1, 2)][
            "rendered"
        ],
        ensure_ascii=False,
    )
    second_solver = json.dumps(
        run.harness.prepared[("tier3_multi_intent:000001", "solver", 2, 1)]["rendered"],
        ensure_ascii=False,
    )
    activation = run.binding.snapshot_for("tool-activation")
    beta_activation = next(
        value.content for value in activation.values if value.task_target == BETA
    )
    alpha_activation = next(
        value.content for value in activation.values if value.task_target == ALPHA
    )
    parameters = run.binding.snapshot_for("parameter-meaning")
    alpha_parameter = next(
        value.content for value in parameters.values if value.task_target == ALPHA
    )
    beta_parameter = next(
        value.content for value in parameters.values if value.task_target == BETA
    )
    assert all(
        not _visible(value.content, first_perception) for value in activation.values
    )
    assert all(not _visible(value.content, first_solver) for value in activation.values)
    assert (
        json.loads(run.initial)["actions"][0]["action_id"]
        == json.loads(run.recovered)["actions"][0]["action_id"]
    )
    assert _visible(alpha_parameter, first_solver)
    assert not _visible(beta_parameter, first_solver) and not _visible(
        beta_activation, first_solver
    )
    assert _visible(beta_activation, next_reviewer) and not _visible(
        alpha_activation, next_reviewer
    )
    assert _visible(run.recovered, second_solver)
    assert _visible(beta_activation, second_solver) and _visible(
        beta_parameter, second_solver
    )
    assert not _visible(alpha_activation, second_solver)
    for value in parameters.values:
        expected = value.task_target in {ALPHA, BETA}
        assert _visible(value.content, second_solver) is expected

    audits = list(run.receipt["candidate_selections"].values())
    assert len(audits) == 2
    first, latest = audits
    assert first["candidate_ids"] == [ALPHA]
    assert latest["candidate_ids"] == [ALPHA, BETA]
    assert latest["selected_source_state_id"] != first["selected_source_state_id"]
    assert latest["already_visible_value_ids"] == [
        f"parameter-meaning::a2t-native-card:{ALPHA}:value"
    ]
    assert latest["added_value_ids"] == [
        f"parameter-meaning::a2t-native-card:{BETA}:value"
    ]
    activation_route = run.routing_receipt["stores"]["tool-activation"]
    assert activation_route["phase_supply"] is None
    assert activation_route["on_demand_target_lookup"] is True
    assert run.routes["tool-activation"] == {}
    assert len(run.harness.tool_contacts) == 1
    assert run.harness.tool_contacts[0]["phase"] == "reviewer"
    schemas = {
        phase: {
            tool["function"]["name"]
            for tool in run.harness.prepared[
                ("tier3_multi_intent:000001", phase, 1, 1)
            ]["rendered"].get("tools", [])
        }
        for phase in ("perception", "solver", "reviewer", "planner")
    }
    assert schemas == {
        "perception": set(),
        "solver": set(),
        "reviewer": {TARGET},
        "planner": {TARGET},
    }


@pytest.mark.usefixtures("_spawn_live_matching_process")
def test_accept_without_refresh_issues_no_lookup_or_extra_perception(
    tmp_path, monkeypatch
):
    run = _run(tmp_path, monkeypatch, refresh=False)
    candidate_report = _candidate_report(run)
    candidate_row = candidate_report["samples"][0]

    assert candidate_report["schema"] == "saea-a2t-candidate-supply-attribution-v2"
    assert candidate_row["initial"]["unique_candidate_ids"] == [ALPHA]
    assert candidate_row["last_attempted"]["unique_candidate_ids"] == [ALPHA]
    assert candidate_row["operative"]["candidate_source"]["unique_candidate_ids"] == [
        ALPHA
    ]
    assert (
        candidate_row["operative"]["candidate_source"]["perception"]["agent_state_id"]
        == candidate_row["initial"]["perception"]["agent_state_id"]
    )
    assert len(candidate_row["perception_visits"]) == 1
    assert len(run.result.contacts) == run.closed["request_count"] == 4
    assert run.closed["cost"]["tool_calls"] == 0
    assert run.harness.tool_contacts == []
    assert [key[1] for key in run.harness.prepared] == [
        "perception",
        "solver",
        "reviewer",
        "planner",
    ]
    episode = run.result.native_episode_receipt
    assert [route["action"] for route in episode["planner_routes"]] == ["ACCEPT"]
    assert _refresh_count(episode) == 0
    assert (
        len(
            [
                visit
                for visit in episode["role_visits"]
                if visit["stage"] == "perception"
            ]
        )
        == 1
    )
    assert len(run.receipt["candidate_selections"]) == 1
    only_audit = next(iter(run.receipt["candidate_selections"].values()))
    assert only_audit["candidate_ids"] == [ALPHA]
    all_requests = json.dumps(
        [entry["rendered"] for entry in run.harness.prepared.values()],
        ensure_ascii=False,
    )
    activation = run.binding.snapshot_for("tool-activation")
    assert all(not _visible(value.content, all_requests) for value in activation.values)
