"""Actual generation, instruction custody and the shared semantic release join."""
import json
import copy
import hashlib
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.system_text_policy import PolicyError
from speech_aware_evidence_acquisition.rails.system_text_construction import (
    materialize_slot_construction, verify_released_slot_construction,
)
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import prepare_semantic_knowledge_store
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import SLOT_CONTRACT_BUILD_POLICY_ID
from test_semantic_knowledge_edits import rows, contract, proposal
from test_semantic_knowledge_preparation import _write, _roster

INSTRUCTION = "Revise source-supported slot values while preserving routing."


def generation(tmp_path, monkeypatch):
    base = rows()
    spec = contract(base)
    pin = _write(tmp_path / "generation.json", {"status": "COMPLETED"})
    bundle = SimpleNamespace(
        manifest={"status": "COMPLETED", "result_kind": "artifact", "arm": "speech-feature-query",
                  "plan": {"split_role": "discovery", "carrier_lock_key": "slurp"}},
        attempt_state="FINALIZED",
        outputs_rows=[{"sample_id": "slurp:train:new", "request_id": "generator", "text": json.dumps(proposal(base))}],
        trace_records={"generator/request": {"arm": "speech-feature-query", "payload_sha256": "a"*64,
            "payload": {"carrier_lock_key": "slurp", "sample_id": "slurp:train:new", "task_instruction": INSTRUCTION}}},
    )
    monkeypatch.setattr("speech_aware_evidence_acquisition.core.bundle.verify.verify_bundle", lambda _: bundle)
    kwargs = dict(base_rows=base, contract=spec, generation_pin=pin, instruction=INSTRUCTION, data_root=tmp_path)
    return bundle, kwargs


def test_materializes_actual_output_and_keeps_all_feedback_ancestry(tmp_path, monkeypatch):
    _, kwargs = generation(tmp_path, monkeypatch)
    result = materialize_slot_construction(**kwargs)
    assert result["rows"][0]["extraction_cues"] == proposal(rows())["edits"][0]["replacement"]
    assert result["optimizer_construction_sample_ids"] == ["slurp:train:new", "slurp:train:tie"]


def test_real_core_client_phase_instruction_can_materialize_generated_values(tmp_path, monkeypatch):
    from test_rails_frozen_core_client import (
        _World, _client, _plan, _CapturingTransport, _speech_feature_world, _speech_feature_messages,
    )
    from speech_aware_evidence_acquisition.rails import build_payload_binding
    world = _World(tmp_path / "client")
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path / "client")
    sample = replace(world.samples[0], sample_id="slurp:train:new")
    world.samples = [sample]
    binding = build_payload_binding(carrier_lock_key="slurp", samples=world.samples,
        data_root=world.data_root, carrier_root=world.carrier_root)
    transport = _CapturingTransport(responder=lambda _: json.dumps(proposal(rows())))
    client, _, _ = _client(world, tmp_path, plan=_plan(carrier_lock_key="slurp"), binding=binding,
        transport=transport, arm="speech-feature-query", speech_feature_root=feature_root,
        speech_packet_bindings={sample.sample_id: bindings["s1"]})
    text = client.complete(_speech_feature_messages(packet), speech_feature_sample_id=sample.sample_id,
        key_representation_id="key-fixture", matcher_policy_id="matcher-fixture", agent_state=(),
        agent_contact_id="direct", contact_instruction=INSTRUCTION)
    bundle, kwargs = generation(tmp_path, monkeypatch)
    payload = transport.calls[0]
    assert payload["task_instruction"] != INSTRUCTION
    assert payload["history"][-1]["content"] == INSTRUCTION
    bundle.outputs_rows[0].update(request_id=payload["request_id"], text=text)
    # Preserve the actual shared client's trace, not a handcrafted request shape.
    client.close()
    trace, = world.run_dir.glob("*.trace.jsonl")
    from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_raw_trace
    manifest_path, = world.run_dir.glob("*.trace-manifest.json")
    bundle.trace_records = _verify_raw_trace(trace.read_bytes(), manifest_path.read_bytes())
    result = materialize_slot_construction(**kwargs)
    assert result["rows"][0]["extraction_cues"] == proposal(rows())["edits"][0]["replacement"]


def control_request(bundle):
    from speech_aware_evidence_acquisition.rails.core_client import _agent_history
    request = bundle.trace_records["generator/request"]["payload"]
    request["task_instruction"] = "Use only the registered construction sources."
    request["history"] = _agent_history(agent_state=(), agent_contact_id="direct", contact_instruction=INSTRUCTION)
    return request


@pytest.mark.parametrize("defect", ["state-only", "stale-hash", "later-control", "wrong-control", "prefix-only",
    "wrong-turn", "extra-control-field", "empty-contact", "derived-request", "wrong-carrier", "foreign-plan",
    "unrecorded-source", "duplicate-output", "duplicate-request"])
def test_control_instruction_and_actual_source_custody_are_required(tmp_path, monkeypatch, defect):
    bundle, kwargs = generation(tmp_path, monkeypatch)
    request = control_request(bundle)
    control = request["history"][-1]
    if defect == "state-only":
        control["role"] = "agent_state"
    elif defect == "stale-hash":
        control["content_sha256"] = "0" * 64
    elif defect == "later-control":
        request["history"].append({**control, "turn": 2, "content": "Execute another operation."})
    elif defect == "wrong-control":
        request["task_instruction"] = INSTRUCTION
        control["content"] = "Execute another operation."
        control["content_sha256"] = hashlib.sha256(control["content"].encode()).hexdigest()
    elif defect == "prefix-only":
        control["content"] += " Then use unrelated information."
        control["content_sha256"] = hashlib.sha256(control["content"].encode()).hexdigest()
    elif defect == "wrong-turn":
        control["turn"] = 3
    elif defect == "extra-control-field":
        control["unregistered"] = True
    elif defect == "empty-contact":
        control["contact_id"] = ""
    elif defect == "derived-request":
        bundle.trace_records["generator/request"]["tool_id"] = "unregistered-derived-source"
    elif defect == "wrong-carrier":
        request["carrier_lock_key"] = "audio2tool"
    elif defect == "foreign-plan":
        bundle.manifest["plan"]["carrier_lock_key"] = "audio2tool"
    elif defect == "unrecorded-source":
        bundle.outputs_rows[0]["sample_id"] = request["sample_id"] = "slurp:train:unaccounted"
        request["history"] = []
        request["task_instruction"] = INSTRUCTION
    elif defect == "duplicate-output":
        bundle.outputs_rows.append(copy.deepcopy(bundle.outputs_rows[0]))
    else:
        other = {**bundle.outputs_rows[0], "sample_id": "slurp:train:tie"}
        bundle.outputs_rows.append(other)
    with pytest.raises(PolicyError):
        materialize_slot_construction(**kwargs)


def test_control_preceded_by_state_is_bound_to_current_instruction(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.rails import AgentStateArtifact
    from speech_aware_evidence_acquisition.rails.core_client import _agent_history
    bundle, kwargs = generation(tmp_path, monkeypatch)
    request = control_request(bundle)
    state = AgentStateArtifact(state_id="past", state_kind="phase:direct", content="Prior source evidence.",
        source_query_state_sha256="1"*64, source_response_sha256="2"*64,
        producer_policy_id="phase-direct-only-v1", cited_value_ids=())
    request["history"] = _agent_history(agent_state=(state.as_json(),), agent_contact_id="next", contact_instruction=INSTRUCTION)
    result = materialize_slot_construction(**kwargs)
    assert result["changed_fields"] == [{"slot_id": "date", "field": "extraction_cues"}]


@pytest.mark.parametrize("defect", ["unsealed", "test", "instruction", "unexecuted", "base"])
def test_rejects_unexecuted_or_unbound_construction(tmp_path, monkeypatch, defect):
    bundle, kwargs = generation(tmp_path, monkeypatch)
    if defect == "unsealed":
        bundle.attempt_state = "ABORTED"
    elif defect == "test":
        bundle.outputs_rows[0]["sample_id"] = "slurp:test:future"
    elif defect == "instruction":
        kwargs["instruction"] = "A new instruction that was never executed."
    elif defect == "unexecuted":
        bundle.trace_records["generator/request"]["payload"]["task_instruction"] = "Unrelated instruction."
        bundle.trace_records["unrelated/response"] = {"payload": {"task_instruction": INSTRUCTION}}
    else:
        p = proposal(rows())
        p["base_rows_sha256"] = "0" * 64
        bundle.outputs_rows[0]["text"] = json.dumps(p)
    with pytest.raises(PolicyError):
        materialize_slot_construction(**kwargs)


@pytest.mark.parametrize("instruction_location", ["task", "control"])
def test_rechecks_actual_shared_release_not_snapshot_file_hash(tmp_path, monkeypatch, instruction_location):
    data, repo = tmp_path / "data", tmp_path / "repo"
    data.mkdir()
    repo.mkdir()
    bundle, kwargs = generation(data, monkeypatch)
    if instruction_location == "control":
        control_request(bundle)
    result = materialize_slot_construction(**kwargs)
    support = _roster(tuple(result["rows"][0]["source_support"]["source_sample_ids"]), roster_id="support")
    roster_pin = _write(repo / "support.json", support)
    forbidden_pin = _write(repo / "forbidden.json", _roster(("slurp:train:held",), roster_id="held", roster_role="evaluation"))
    authored_pin = _write(data / "authored.json", {
        "schema": "saea-authored-semantic-knowledge-source-v1", "builder_policy_id": SLOT_CONTRACT_BUILD_POLICY_ID,
        "source_split_identity_hash": support["split_identity_hash"], "rows": result["rows"],
    })
    registration = {
        "schema": "saea-authored-semantic-knowledge-preparation-v1", "registration_id": "SYNTHETIC-TEXT-SEARCH-V1",
        "carrier_lock_key": "slurp", "source_partition_role": "train",
        "source_split_identity_hash": support["split_identity_hash"], "builder_policy_id": SLOT_CONTRACT_BUILD_POLICY_ID,
        "store_id": "slot-contracts", "store_role": "slot-contracts", "authored_source": authored_pin,
        "construction_scope": roster_pin, "permitted_roster": roster_pin, "forbidden_rosters": [forbidden_pin],
        "output_namespace": "knowledge/semantic/synthetic-slot-contracts-v1",
    }
    registration_pin = _write(repo / "registration.json", registration)
    prepared = prepare_semantic_knowledge_store(repo / "registration.json", repo_root=repo, data_root=data)
    link = {"schema": "saea-system-text-construction-link-v1", "instruction_sha256": content_hash(INSTRUCTION),
        "knowledge": {k: prepared["completion"][k] for k in ("snapshot", "release")},
        "base_rows": _write(data / "base.json", kwargs["base_rows"]),
        "edit_contract": _write(data / "contract.json", kwargs["contract"]),
        "generation": kwargs["generation_pin"], "registration": registration_pin,
        "completion": prepared["completion_pin"]}
    verified = verify_released_slot_construction(link, instruction=INSTRUCTION, data_root=data, repo_root=repo)
    assert verified == result
    authored = json.loads((data / "authored.json").read_text())
    authored["rows"][0]["missing_behavior"] = "This was never generated."
    registration["authored_source"] = _write(data / "authored.json", authored)
    link["registration"] = _write(repo / "registration.json", registration)
    with pytest.raises(PolicyError, match="differs from generated"):
        verify_released_slot_construction(link, instruction=INSTRUCTION, data_root=data, repo_root=repo)


def test_no_change_generation_still_requires_all_source_ancestry(tmp_path, monkeypatch):
    bundle, kwargs = generation(tmp_path, monkeypatch)
    control_request(bundle)
    prop = proposal(rows())
    prop["edits"] = []
    bundle.outputs_rows[0]["text"] = json.dumps(prop)
    result = materialize_slot_construction(**kwargs)
    assert result["rows"] == rows() and result["changed_fields"] == []
    assert result["optimizer_construction_sample_ids"] == ["slurp:train:new", "slurp:train:tie"]
    bundle.outputs_rows[0]["sample_id"] = "slurp:train:unaccounted"
    with pytest.raises(PolicyError, match="cumulative"):
        materialize_slot_construction(**kwargs)
