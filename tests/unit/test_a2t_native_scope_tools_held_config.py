"""Held Audio2Tool scope-tools configuration and synthetic graph proof.

The graph tests use the shared OpenJiuwen workflow with synthetic speech,
knowledge, and an in-process transport. They do not read task rows or gold,
run scorers, open a socket, or contact a model.
"""

from __future__ import annotations

import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.config import compose
from speech_aware_evidence_acquisition.core.flight.campaign import (
    CampaignError,
    EXECUTION_STAGES,
    declared_readiness,
    load_campaign_cells,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    default_phase_program,
    native_planner_action_response_format,
)
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    load_native_episode_config,
)
from speech_aware_evidence_acquisition.rails.phase_tools import TASK_CONTRACT_TOOL

import test_a2t_candidate_recovery_graph as recovery_graph
import test_native_episode_runner as episode_runner


REPO = Path(__file__).resolve().parents[2]
EXPERIMENT = "a2t-native-role-scope-tools-union4000-held-v1"
DIRECT_POLICY = "phase-direct-only-v1"
SYSTEM_POLICY = "phase-audio2tool-native-candidate-recovery-tools-v1"
TARGET = recovery_graph.TARGET
SCORERS = (
    "a2t-toolcall-official",
    "a2t-toolcall-v2",
    "a2t-toolcall",
    "cost",
)
PROMPT_SHA256 = {
    "perception": "ad36ea01188af4d2af42fd90f964085fbe25883a3505392db942d4c4c9da0506",
    "planner": "28bd352c9259b081acd3e7182f0e263c0c2afb0f1e05e10ccc2b411c20040849",
    "reviewer": "80aa5c69addf976cb14417322d2c6325454e7aa08f9c98f7e6f636f59a63af46",
    "solver": "e8c41dcbc1175cc725f45c2969b5a0b0edf427d9967956aeec98a782715d2806",
}


def _document(relpath: str) -> dict[str, object]:
    return json.loads((REPO / relpath).read_text(encoding="utf-8"))


def _composed_cells():
    cells = load_campaign_cells(REPO, EXPERIMENT)
    return {
        cell.document["cell_id"]: (
            cell,
            compose(
                REPO,
                model=cell.document["model_fragment"],
                dataset=cell.document["dataset_fragment"],
                baseline=cell.document["baseline_fragment"],
                experiment=EXPERIMENT,
            ).values,
        )
        for cell in cells
    }


def test_campaign_is_check_only_and_has_no_live_authority(tmp_path):
    resolved = _composed_cells()
    assert set(resolved) == {"direct", "system"}

    for cell, values in resolved.values():
        assert cell.document["allowed_execution_stages"] == ["check"]
        cell.assert_mode("check")
        for mode in EXECUTION_STAGES - {"check"}:
            with pytest.raises(CampaignError, match="does not permit execution stage"):
                cell.assert_mode(mode)
        readiness = declared_readiness(cell, tmp_path)
        assert readiness.state == "held"
        assert "no launch authority" in readiness.reason
        assert values["execution_profile"] == "model-free-check"
        assert values["service_session"] == "HELD-NO-SERVICE"
        assert {
            "execution_plan",
            "live_phase_fit",
            "native_contact_fit",
            "whole_roster_wave_barrier",
            "prepared_phase_supply",
        }.isdisjoint(values)


def test_cells_share_roster_registry_packets_geometry_and_registered_programs():
    resolved = _composed_cells()
    direct_cell, direct = resolved["direct"]
    system_cell, system = resolved["system"]

    for name in ("model_fragment", "dataset_fragment"):
        assert direct_cell.document[name] == system_cell.document[name]
    for name in (
        "carrier_lock_key",
        "split_id",
        "a2t_calibration_count",
        "a2t_calibration_flight_split_identity_hash",
        "task_instruction_fill",
        "task_instruction_template",
        "task_instruction_template_active",
        "task_contract_source",
        "speech_feature_matcher_policy_id",
        "speech_feature_key_representation_id",
        "speech_packet_promotion_receipt",
        "speech_packet_promotion_receipt_sha256",
        "serving_geometry",
        "profile_slot_count",
        "prompt_order",
        "runtime_receipt",
        "speech_feature_root",
    ):
        assert direct[name] == system[name]
    assert direct["carrier_lock_key"] == "audio2tool"
    assert direct["split_id"] == "A2T-ORG1-UNION-4000"
    assert direct["a2t_calibration_count"] == 4000
    assert direct["a2t_calibration_flight_split_identity_hash"] == (
        "ed8946ddf99f9e898af1c8cb94932c538165cd591c2cff3021321749e52103d6"
    )
    assert direct["task_instruction_fill"] == "audio2tool-registry-compact"
    assert direct["speech_feature_matcher_policy_id"] == "saea-a2t-native-system-v1"
    assert direct["speech_packet_promotion_receipt_sha256"] == (
        "720d81f63a1923f19893c0ee171e1ab7b47f9a946c1e62a06bdddd839243de8a"
    )
    assert direct["serving_geometry"] == {
        "max_tokens": 2048,
        "slot_tokens": 32768,
        "slots": 3,
    }
    assert direct["profile_slot_count"] == 3
    assert direct["server_args"][1:4] == ["98304", "-np", "3"]
    assert tuple(direct["scorers"]) == tuple(system["scorers"]) == SCORERS

    direct_program = default_phase_program(direct["policy"])
    system_program = default_phase_program(system["policy"])
    assert direct_program.program_id == DIRECT_POLICY
    assert direct_program.max_contacts == 1
    assert [(phase.name, phase.knowledge) for phase in direct_program.phases] == [
        ("direct", "none")
    ]
    assert direct_program.stop_rule == "always-run-full-program"
    assert system_program.program_id == SYSTEM_POLICY
    assert system_program.max_contacts == 14
    assert system_program.stop_rule == "native-role-episode"


def test_system_binds_bounded_roles_target_tools_and_dormant_activation():
    system = _composed_cells()["system"][1]
    program = default_phase_program(system["policy"])
    native = load_native_episode_config(system, program)

    assert native.max_contacts == 14
    assert native.max_revisions == 1
    assert native.refresh_action == recovery_graph.REFRESH
    assert native.max_candidate_refreshes == 1
    assert {
        role: native.role(role).max_iterations
        for role in ("perception", "solver", "reviewer", "planner")
    } == {"perception": 1, "solver": 1, "reviewer": 3, "planner": 2}

    assert set(system["phase_tools"]) == {"reviewer", "planner"}
    assert system["phase_tools"]["planner"]["allowed_tools"] == [TARGET]
    assert system["phase_tools"]["reviewer"]["allowed_tools"] == [
        TARGET,
        TASK_CONTRACT_TOOL,
    ]
    for role, config in system["phase_tools"].items():
        assert config["source_authority_role"] == role
        assert config["knowledge_store_ids"] == [
            "tool-activation",
            "parameter-meaning",
        ]
        assert config["candidate_limit"] == config["knowledge_value_limit"] == 4
        assert config["knowledge_values_per_candidate"] == 1

    stores = system["knowledge_stores"]
    activation = stores["tool-activation"]
    assert activation["store_role"] == "tool-activation"
    assert "phase_supply" not in activation
    assert "candidate_supply" not in activation
    assert activation["snapshot"] == {
        "relpath": (
            "prepared/SAEA-A2T-ACTIVATION-SCOPE-KNOWLEDGE-V1/"
            "knowledge-snapshot.json"
        ),
        "sha256": "17d22d2f77e0916527f4662d93c335d191e0f87504e68d1e735b0f79f5934f73",
    }
    parameter = stores["parameter-meaning"]
    assert parameter["store_role"] == "parameter-meaning"
    assert parameter["snapshot"]["sha256"] == (
        "7084f9c56b361ab8f38d2e0a6864ccb2d05bcc053dc70441de263b410ca6041f"
    )
    assert set(parameter["candidate_supply"]) == {"solver"}
    solver = parameter["candidate_supply"]["solver"]
    assert solver == {
        "candidate_state_phase": "perception",
        "candidate_state_selection": "latest",
        "compact_source_phase": "perception",
        "fuse_policy": "saea-candidate-semantic-passthrough-v1",
        "max_actions": 8,
        "max_candidates_per_action": 4,
        "max_total_values": 32,
        "max_values_per_candidate": 1,
        "provider": "audio2tool-candidate-semantic-v1",
        "rank_policy": "saea-ranked-candidate-round-robin-v1",
    }


def test_role_prompts_and_analysis_recipe_are_byte_pinned():
    experiment = _document(f"configs/experiment/{EXPERIMENT}.json")
    system = _composed_cells()["system"][1]
    for role, expected in PROMPT_SHA256.items():
        relpath = system["phase_material"][role]["instruction_template"]
        assert relpath == f"probes/a2t_native_role_{role}_scope_tools_v1.txt"
        prompt = REPO / "configs" / relpath
        assert hashlib.sha256(prompt.read_bytes()).hexdigest() == expected
        assert prompt.read_text(encoding="utf-8").isascii()

    binding = experiment["analysis_recipe"]
    recipe_path = REPO / binding["repo_relpath"]
    assert hashlib.sha256(recipe_path.read_bytes()).hexdigest() == binding["sha256"]
    assert binding["sha256"] == (
        "a2b9514bb0b09c6af7fe0160a5a07ca2e9a3a991df03a209020ab9ca0293f904"
    )
    recipe = json.loads(recipe_path.read_text(encoding="utf-8"))
    assert recipe["execution_profile"] == "model-free-check"
    assert recipe["status"].startswith("CPU-prepared; GPU hold active")
    assert recipe["shared_entry"] == (
        "speech_aware_evidence_acquisition.analysis.score_compare_cli"
    )
    assert recipe["analysis"]["expected_ids_count"] == 4000
    decision = recipe["decision_rule"]
    decision_path = REPO / decision["path"]
    assert hashlib.sha256(decision_path.read_bytes()).hexdigest() == decision["sha256"]
    assert decision["sha256"] == (
        "9afe24e006f4d76616e2d2488e66cc44c418a765eb82f40b17b14bf0c00e0143"
    )


class _InProcessRenderedTransport:
    """Minimal request renderer and responder with no socket or service."""

    def __init__(self, post):
        self._post = post
        closure = dict(zip(post.__code__.co_freevars, post.__closure__, strict=True))
        self._harness = closure["self"].cell_contents

    def render_request(self, request_bytes: bytes) -> dict[str, object]:
        rendered = json.loads(request_bytes.decode("utf-8"))
        # The real llama-server renderer does not put this trace-routing ID
        # into model-visible request bytes. Prepared and dispatched payloads
        # therefore render identically even though dispatch assigns the ID.
        rendered.pop("request_id", None)
        return rendered

    def __call__(self, request_bytes: bytes) -> bytes:
        rendered = self.render_request(request_bytes)
        material_key = self._harness._material_key(rendered)
        matches = [
            prepared["rendered"]
            for key, prepared in self._harness.prepared.items()
            if key[:3] == material_key and key not in self._harness.dispatched
        ]
        assert len(matches) == 1
        wire = self._post(
            "in-process://synthetic",
            json.dumps(matches[0], ensure_ascii=False, sort_keys=True).encode("utf-8"),
        )
        response = json.loads(wire)
        choice = response["choices"][0]
        message = choice["message"]
        tool_calls = message.get("tool_calls")
        if tool_calls:
            text = json.dumps(
                [
                    {
                        "name": call["function"]["name"],
                        "arguments": json.loads(call["function"]["arguments"]),
                    }
                    for call in tool_calls
                ]
            )
        else:
            text = message["content"]
        envelope = {
            "text": text,
            "usage": response["usage"],
            "wire_response_b64": base64.b64encode(wire).decode("ascii"),
            "wire_response_sha256": hashlib.sha256(wire).hexdigest(),
            "wire_finish_reason": choice.get("finish_reason"),
        }
        if tool_calls:
            envelope["tool_calls"] = tool_calls
        return json.dumps(envelope, separators=(",", ":")).encode("utf-8")


def _actual_prompt_builder(prompts):
    planner_format = native_planner_action_response_format(
        ("ACCEPT", "REVISE", recovery_graph.REFRESH)
    )

    def builder(harness, perception_format):
        def material_for_phase(phase, context, _sealed):
            key = (context.sample_id, phase)
            harness.material_visits[key] += 1
            visit = harness.material_visits[key]
            marker = f"native-role:{phase}:sample:{context.sample_id}:visit:{visit}"
            harness.markers[(context.sample_id, phase, visit)] = marker
            return PhaseMaterial(
                # _ActualEpisodeHarness locates a prepared contact by a unique
                # marker in its instruction. Keep the complete held prompt and
                # append only that synthetic routing marker; the independent
                # hash assertions above pin the exact source prompt bytes.
                instruction=f"{prompts[phase]}\n\n{marker}",
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

    return builder


def _run_actual_held_graph(tmp_path, monkeypatch, *, refresh):
    system = _composed_cells()["system"][1]
    prompts = {
        phase: (
            REPO / "configs" / material["instruction_template"]
        ).read_text(encoding="utf-8")
        for phase, material in system["phase_material"].items()
    }

    monkeypatch.setattr(
        episode_runner,
        "_transport",
        lambda _base_url, _data_root, *, post, **_kwargs: (
            _InProcessRenderedTransport(post)
        ),
    )
    monkeypatch.setattr(episode_runner, "_base_url", lambda: "in-process://synthetic")
    monkeypatch.setattr(episode_runner, "_fake_inference_session", object)
    monkeypatch.setattr(
        recovery_graph,
        "load_phase_program",
        lambda _path: default_phase_program(SYSTEM_POLICY),
    )
    monkeypatch.setattr(
        recovery_graph,
        "_phase_tool_config",
        lambda: {"phase_tools": deepcopy(system["phase_tools"])},
    )
    monkeypatch.setattr(
        recovery_graph,
        "_native_values",
        lambda store_values: {
            **store_values,
            "phase_tools": deepcopy(system["phase_tools"]),
            "native_episode": deepcopy(system["native_episode"]),
        },
    )
    monkeypatch.setattr(
        recovery_graph,
        "_material_builder",
        _actual_prompt_builder(prompts),
    )
    run = recovery_graph._run(tmp_path, monkeypatch, refresh=refresh)
    return run, prompts


@pytest.mark.skipif(
    not episode_runner.openjiuwen_available(), reason="OpenJiuwen unavailable"
)
def test_actual_held_graph_refreshes_once_and_accepts_recovered_candidate(
    tmp_path, monkeypatch
):
    run, prompts = _run_actual_held_graph(tmp_path, monkeypatch, refresh=True)
    report = recovery_graph._candidate_report(run)["samples"][0]

    assert run.harness.program is default_phase_program(SYSTEM_POLICY)
    assert run.harness.config.episode_id == "a2t-native-role-scope-tools-union4000-v1"
    assert run.harness.config.max_contacts == 14
    assert [route["action"] for route in run.result.native_episode_receipt["planner_routes"]] == [
        recovery_graph.REFRESH,
        "ACCEPT",
    ]
    assert recovery_graph._refresh_count(run.result.native_episode_receipt) == 1
    assert len(run.result.contacts) == run.closed["request_count"] == 9
    assert run.closed["cost"]["tool_calls"] == 1
    assert run.harness.tool_contacts[0]["phase"] == "reviewer"
    assert run.harness.tool_contacts[0]["tool_id"] == TARGET
    assert report["initial"]["unique_candidate_ids"] == [recovery_graph.ALPHA]
    assert report["operative"]["candidate_source"]["unique_candidate_ids"] == [
        recovery_graph.ALPHA,
        recovery_graph.BETA,
    ]
    assert run.result.final_response_text == run.final
    activation_route = run.routing_receipt["stores"]["tool-activation"]
    assert activation_route.get("candidate_supply") is None
    assert activation_route.get("phase_supply") is None
    assert activation_route["on_demand_target_lookup"] is True
    assert activation_route["store_role"] == "tool-activation"
    for phase, prompt in prompts.items():
        rendered = json.dumps(
            run.harness.prepared[
                ("tier3_multi_intent:000001", phase, 1, 1)
            ]["rendered"],
            ensure_ascii=False,
        )
        # The in-process renderer preserves the complete instruction as an
        # internal payload rather than reproducing llama-server chat escaping.
        # Check a distinctive rendered line here; the exact complete files are
        # independently SHA-256 pinned above.
        assert prompt.splitlines()[0] in rendered


@pytest.mark.skipif(
    not episode_runner.openjiuwen_available(), reason="OpenJiuwen unavailable"
)
def test_actual_held_graph_accept_path_uses_no_lookup_or_refresh(tmp_path, monkeypatch):
    run, _prompts = _run_actual_held_graph(tmp_path, monkeypatch, refresh=False)

    assert [route["action"] for route in run.result.native_episode_receipt["planner_routes"]] == [
        "ACCEPT"
    ]
    assert recovery_graph._refresh_count(run.result.native_episode_receipt) == 0
    assert len(run.result.contacts) == run.closed["request_count"] == 4
    assert run.closed["cost"]["tool_calls"] == 0
    assert run.harness.tool_contacts == []
    assert [key[1] for key in run.harness.prepared] == [
        "perception",
        "solver",
        "reviewer",
        "planner",
    ]
    schemas = {
        phase: {
            schema["function"]["name"]
            for schema in run.harness.prepared[
                ("tier3_multi_intent:000001", phase, 1, 1)
            ]["rendered"].get("tool_schemas", [])
        }
        for phase in ("perception", "solver", "reviewer", "planner")
    }
    assert schemas == {
        "perception": set(),
        "solver": set(),
        "reviewer": {TARGET, TASK_CONTRACT_TOOL},
        "planner": {TARGET},
    }
    all_requests = json.dumps(
        [entry["rendered"] for entry in run.harness.prepared.values()],
        ensure_ascii=False,
    )
    activation = run.binding.snapshot_for("tool-activation")
    assert all(
        not recovery_graph._visible(value.content, all_requests)
        for value in activation.values
    )
