"""Engineering tests for the OpenJiuwen self-consistency flight boundary."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.contracts.ledger import _parse_ledger_tables
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.rails.probes import (
    a2t_self_consistency_flight as flight,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY = (
    {
        "tool_id": "1",
        "domain": "home",
        "category": "lighting",
        "tool_name": "setLight",
        "signature": "setLight(room, state)",
        "description": "Set a room light.",
        "argument_defaults": "room=kitchen; state=on",
        "argument_constraints": "state in {on,off}",
    },
    {
        "tool_id": "2",
        "domain": "home",
        "category": "climate",
        "tool_name": "setTemp",
        "signature": "setTemp(room, degrees)",
        "description": "Set a room temperature.",
        "argument_defaults": "room=office; degrees=21",
        "argument_constraints": "degrees is numeric",
    },
)


def _response(name: str, arguments: dict[str, object]) -> str:
    return json.dumps([{"name": name, "arguments": arguments}])


def _receipt_items() -> tuple[dict[str, object], ...]:
    return (
        {
            "sample_id": "tier1_direct:000001",
            "media_relpath": "one.wav",
            "audio_sha256": "a" * 64,
        },
        {
            "sample_id": "tier2_parametric:000002",
            "media_relpath": "two.wav",
            "audio_sha256": "b" * 64,
        },
    )


def test_committed_plan_binds_composition_and_exposure_row() -> None:
    plan_path = (
        REPO_ROOT
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-self-consistency-104-v1/execution-plan-template.json"
    )
    document = json.loads(plan_path.read_text(encoding="utf-8"))
    fragments = document["config_composition"]
    composed = compose(
        REPO_ROOT,
        fragments["model"],
        fragments["dataset"],
        fragments["baseline"],
        fragments["experiment"],
    )
    plan = ExecutionPlan(**document["execution_plan"]).validate()
    rows = _parse_ledger_tables(
        (REPO_ROOT / "docs/exposure-ledger.md").read_text(encoding="utf-8")
    )
    matched = [row for row in rows if row["run/experiment id"] == plan.run_id]

    assert composed.config_hash == document["composed_config_sha256"]
    assert plan.protocol_hash == protocol_hash(
        composed.config_hash, composed.values["arm"], plan.split_identity_hash
    )
    assert composed.values["speech_native_agent_executor_id"] == flight.AGENT_EXECUTOR_ID
    assert composed.values["speech_native_contact_ceiling_per_task"] == 1
    assert composed.values["scorers"] == ["a2t-toolcall", "cost"]
    assert len(matched) == 1
    assert matched[0]["split identity hash"] == plan.split_identity_hash
    assert matched[0]["calls"] == str(plan.planned_model_calls)


def test_build_supply_material_is_identity_complete_and_gold_free() -> None:
    m0 = {
        "sample-a": _response("setTemp", {"room": "office", "degrees": 20}),
        "sample-b": _response("unknown", {}),
    }
    repeat = {
        "sample-a": _response("setLight", {"room": "office", "state": "on"}),
        "sample-b": _response("setTemp", {"room": "office", "degrees": 21}),
    }

    material = flight.build_supply_material(m0, repeat, REGISTRY)

    assert tuple(material) == ("sample-a", "sample-b")
    assert material["sample-a"].tool_names == ("setLight", "setTemp")
    assert material["sample-b"].tool_names == ("setTemp",)
    assert all("argument_defaults" not in row.prompt_block for row in material.values())
    assert material["sample-a"].state.tool_relation == "disjoint"


def test_build_supply_material_refuses_identity_mismatch() -> None:
    with pytest.raises(flight.A2TSelfConsistencyFlightError, match="identity mismatch"):
        flight.build_supply_material(
            {"a": _response("setLight", {})},
            {"b": _response("setLight", {})},
            REGISTRY,
        )


def test_build_supply_material_uses_non_evidentiary_sentinel_when_unresolved() -> None:
    material = flight.build_supply_material(
        {"sample-a": _response("unknownM0", {})},
        {"sample-a": _response("unknownRepeat", {})},
        REGISTRY,
    )

    assert material["sample-a"].tool_names == ()
    assert material["sample-a"].supply_available is False
    assert material["sample-a"].prompt_block == flight.UNRESOLVED_SUPPLY_SENTINEL
    assert "registry-resolved" in material["sample-a"].prompt_block


def test_supply_adapter_places_only_sample_union_in_system_contract() -> None:
    material = flight.build_supply_material(
        {"sample-a": _response("setTemp", {"room": "office", "degrees": 20})},
        {"sample-a": _response("setLight", {"room": "office", "state": "on"})},
        REGISTRY,
    )
    adapter = object.__new__(flight.A2TSelfConsistencyAdapter)
    adapter._phase = flight.SUPPLY_PHASE
    adapter._supply_material = material
    sample = SimpleNamespace(sample_id="sample-a", media_relpath="sample.wav")

    contract = adapter.build_task_contract(sample, object())
    messages = adapter.assemble_prompt(sample, None)

    assert contract == material["sample-a"].prompt_block
    assert material["sample-a"].prompt_block in messages[0]["content"]
    assert "argument_defaults" not in messages[0]["content"]
    assert messages[1] == {
        "role": "user",
        "content": [{"type": "input_audio", "media_relpath": "sample.wav"}],
    }


def test_supply_adapter_refuses_unknown_material_identity() -> None:
    adapter = object.__new__(flight.A2TSelfConsistencyAdapter)
    adapter._phase = flight.SUPPLY_PHASE
    adapter._supply_material = {}
    sample = SimpleNamespace(sample_id="unknown", media_relpath="sample.wav")

    with pytest.raises(flight.A2TSelfConsistencyFlightError, match="supply material"):
        adapter.assemble_prompt(sample, None)


def test_load_frozen_m0_outputs_is_strict_and_unique(tmp_path: Path) -> None:
    path = tmp_path / "m0.jsonl"
    rows = [
        {
            "arm": "M0",
            "sample_id": "b",
            "final_response_text": _response("setTemp", {}),
            "direct_response_text": _response("setTemp", {}),
            "contacts": 1,
            "slot_ids": [0],
            "winner_label": None,
        },
        {
            "arm": "M0",
            "sample_id": "a",
            "final_response_text": _response("setLight", {}),
            "direct_response_text": _response("setLight", {}),
            "contacts": 1,
            "slot_ids": [1],
            "winner_label": None,
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    loaded = flight.load_frozen_m0_outputs(path, expected_ids=("a", "b"))

    assert tuple(loaded) == ("a", "b")
    assert loaded["a"] == rows[1]["final_response_text"]
    path.write_text(path.read_text(encoding="utf-8") + json.dumps(rows[0]) + "\n")
    with pytest.raises(flight.A2TSelfConsistencyFlightError, match="duplicate"):
        flight.load_frozen_m0_outputs(path, expected_ids=("a", "b"))


def test_single_contact_controller_stops_on_its_own_response() -> None:
    controller = flight.SingleContactController(phase=flight.SUPPLY_PHASE)
    context = SimpleNamespace(
        query_state=SimpleNamespace(content_hash=lambda: "q"),
        knowledge_snapshot_sha256="s" * 64,
    )

    contact = controller.initial_contact(context)
    advance = controller.advance(context, contact, "answer")

    assert contact.contact_id == "supply-union-stripped"
    assert contact.purpose == "supply-union-stripped"
    assert advance.final_response_contact_id == contact.contact_id
    assert advance.next_contact is None
    assert advance.transition.action_kind == "stop"


def test_run_phase_hard_binds_openjiuwen_and_one_contact() -> None:
    captured: dict[str, object] = {}

    def fake_runner(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            results=(
                SimpleNamespace(sample_id="a", contacts=(object(),)),
                SimpleNamespace(sample_id="b", contacts=(object(),)),
            )
        )

    plan = SimpleNamespace(run_id="run")
    sink = SimpleNamespace(run_id="run")
    adapter = object()
    summary = flight.run_phase(
        phase=flight.OBSERVATION_PHASE,
        data_root=Path("/data"),
        plan=plan,
        adapter=adapter,
        core_client=object(),
        split_id=flight.SPLIT_ID,
        knowledge_snapshot=object(),
        speech_packet_bindings={"a": {}, "b": {}},
        trace_sink=sink,
        slot_count=2,
        queue_depth=4,
        decoding_params={"temperature": 0},
        agent_runner=fake_runner,
    )

    assert summary.results[0].sample_id == "a"
    assert captured["agent_executor_id"] == "openjiuwen-workflow-v1"
    assert captured["max_contacts"] == 1
    assert captured["controller_policy_id"] == flight.OBSERVATION_POLICY_ID
    assert captured["slot_count"] == 2


def test_run_phase_refuses_a_result_with_more_than_one_contact() -> None:
    def fake_runner(**_kwargs):
        return SimpleNamespace(
            results=(SimpleNamespace(sample_id="a", contacts=(object(), object())),)
        )

    with pytest.raises(flight.A2TSelfConsistencyFlightError, match="exactly one contact"):
        flight.run_phase(
            phase=flight.OBSERVATION_PHASE,
            data_root=Path("/data"),
            plan=SimpleNamespace(run_id="run"),
            adapter=object(),
            core_client=object(),
            split_id=flight.SPLIT_ID,
            knowledge_snapshot=object(),
            speech_packet_bindings={"a": {}},
            trace_sink=SimpleNamespace(run_id="run"),
            slot_count=1,
            queue_depth=1,
            decoding_params={},
            agent_runner=fake_runner,
        )


def test_build_phase_bundle_material_binds_trace_and_cost() -> None:
    answer = _response("setLight", {"room": "office", "state": "on"})
    text_hash = hashlib.sha256(answer.encode()).hexdigest()
    trace = (
        {
            "channel": "MODEL_REQUEST",
            "record_id": "obs-0001/request",
            "payload": {
                "arm": "speech-feature-query",
                "payload": {
                    "sample_id": "a",
                    "carrier_lock_key": "audio2tool",
                },
                "payload_sha256": "1" * 64,
            },
        },
        {
            "channel": "MODEL_RESPONSE",
            "record_id": "obs-0001/response",
            "payload": {
                "text": answer,
                "response_sha256": "2" * 64,
                "response_text_sha256": text_hash,
                "usage": {"prompt_tokens": 12, "completion_tokens": 7},
            },
        },
        {
            "channel": "COST",
            "record_id": "obs-0001/cost",
            "payload": {
                "calls": 1,
                "audio_seconds": 2.5,
                "latency_seconds": 3.0,
                "prompt_tokens": 12,
                "completion_tokens": 7,
            },
        },
    )
    summary = SimpleNamespace(
        results=(SimpleNamespace(sample_id="a", final_response_text=answer),)
    )

    rows, cost = flight.build_phase_bundle_material(
        summary,
        trace,
        phase=flight.OBSERVATION_PHASE,
        umbrella_lock_sha256="f" * 64,
    )

    assert rows == (
        {
            "request_id": "obs-0001",
            "sample_id": "a",
            "carrier_lock_key": "audio2tool",
            "arm": "speech-feature-query",
            "text": answer,
            "admitted": True,
            "request_sha256": "1" * 64,
            "response_sha256": "2" * 64,
            "response_text_sha256": text_hash,
            "phase": flight.OBSERVATION_PHASE,
        },
    )
    assert cost == {
        "calls_used": 1,
        "audio_seconds_used": 2.5,
        "latency_seconds_total": 3.0,
        "prompt_tokens_total": 12,
        "completion_tokens_total": 7,
        "tool_calls": 0,
        "umbrella_lock_sha256": "f" * 64,
    }


def test_build_phase_bundle_material_refuses_response_drift() -> None:
    trace = (
        {
            "channel": "MODEL_REQUEST",
            "record_id": "obs-0001/request",
            "payload": {
                "arm": "speech-feature-query",
                "payload": {
                    "sample_id": "a",
                    "carrier_lock_key": "audio2tool",
                },
                "payload_sha256": "1" * 64,
            },
        },
        {
            "channel": "MODEL_RESPONSE",
            "record_id": "obs-0001/response",
            "payload": {
                "text": "trace answer",
                "response_sha256": "2" * 64,
                "response_text_sha256": hashlib.sha256(b"trace answer").hexdigest(),
                "usage": {},
            },
        },
        {
            "channel": "COST",
            "record_id": "obs-0001/cost",
            "payload": {
                "calls": 1,
                "audio_seconds": 1.0,
                "latency_seconds": 1.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
            },
        },
    )
    summary = SimpleNamespace(
        results=(SimpleNamespace(sample_id="a", final_response_text="different"),)
    )

    with pytest.raises(flight.A2TSelfConsistencyFlightError, match="response drift"):
        flight.build_phase_bundle_material(
            summary,
            trace,
            phase=flight.OBSERVATION_PHASE,
            umbrella_lock_sha256="f" * 64,
        )
