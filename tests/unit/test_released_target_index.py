"""Released authored relations reach native tool requests without reauthoring."""
from dataclasses import replace
import json

import pytest

from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding, build_knowledge_store_supply,
)
from speech_aware_evidence_acquisition.rails.knowledge_target_lookup import lookup_knowledge_targets
from speech_aware_evidence_acquisition.rails.phase_tools import build_phase_tools
from speech_aware_evidence_acquisition.rails.released_target_index import build_released_target_index
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    build_intent_boundary_snapshot, build_slot_contract_snapshot,
)
from test_candidate_semantic_supply import _store
from test_semantic_knowledge_build import _spec, _intent, _slot
from test_knowledge_target_lookup import _query
from test_native_target_knowledge_tools import _config, _context
from test_phase_native_tools import Custody
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program

LEGAL = ("calendar_set", "calendar_query")


def _binding(tmp_path):
    stores = {}
    for store_id, builder, row, sample in (
        ("intent-boundaries", build_intent_boundary_snapshot, _intent(), "train-1"),
        ("slot-contracts", build_slot_contract_snapshot, _slot(), "train-2"),
    ):
        snapshot = builder(_spec(permitted_source_sample_ids=(sample,)), rows=(row,))
        source = {
            "schema": "saea-authored-semantic-knowledge-source-v1",
            "builder_policy_id": snapshot.builder_policy_id,
            "source_split_identity_hash": snapshot.source_split_identity_hash,
            "rows": [row],
        }
        stores[store_id] = _store(tmp_path, store_id, store_id, snapshot, source)
    return load_knowledge_store_binding({"knowledge_stores": stores}, data_root=tmp_path)


@pytest.mark.parametrize("store_id,target,value", [
    ("intent-boundaries", "calendar_set", "intent-boundary:calendar_set"),
    ("slot-contracts", "calendar_set", "slot-contract:event_time"),
    ("slot-contracts", "calendar_query", "slot-contract:event_time"),
])
def test_exact_authored_relation_supports_shared_slot_values(tmp_path, store_id, target, value):
    store = _binding(tmp_path).store(store_id)
    before = store.snapshot.frozen_json()
    index = build_released_target_index(store, data_root=tmp_path, legal_candidate_ids=LEGAL)
    result = lookup_knowledge_targets(
        store.snapshot, _query(), (target,), target_index=index,
        max_values_per_candidate=4, max_total_values=4,
    )
    assert result.selected_value_ids == (value,)
    assert result.audit["target_index"] == dict(index.receipt)
    assert store.snapshot.frozen_json() == before
    assert all(value.task_target is None for value in store.snapshot.values)
    repeated = lookup_knowledge_targets(
        store.snapshot, _query(), (target,), target_index=index,
        max_values_per_candidate=4, max_total_values=4,
        already_visible_value_ids=result.selected_value_ids,
    )
    assert repeated.supply is None
    assert repeated.audit["supply_disposition"] == "already-visible"


@pytest.mark.parametrize("store_id", ["intent-boundaries", "slot-contracts"])
def test_source_mutation_is_refused(tmp_path, store_id):
    store = _binding(tmp_path).store(store_id)
    source = tmp_path / store.source_pin["relpath"]
    source.write_bytes(source.read_bytes() + b" ")
    with pytest.raises(RailsError, match="SHA-256"):
        build_released_target_index(store, data_root=tmp_path, legal_candidate_ids=LEGAL)


@pytest.mark.parametrize("store_id", ["intent-boundaries", "slot-contracts"])
def test_rebuilt_bytes_must_match_snapshot(tmp_path, store_id):
    store = _binding(tmp_path).store(store_id)
    changed = replace(store.snapshot.values[0], content="Changed knowledge.")
    store = replace(store, snapshot=replace(store.snapshot, values=(changed,)))
    with pytest.raises(RailsError, match="differs"):
        build_released_target_index(store, data_root=tmp_path, legal_candidate_ids=LEGAL)


@pytest.mark.parametrize("store_id", ["intent-boundaries", "slot-contracts"])
def test_unknown_candidate_binding_is_refused(tmp_path, store_id):
    store = _binding(tmp_path).store(store_id)
    with pytest.raises(RailsError, match="inventory"):
        build_released_target_index(store, data_root=tmp_path, legal_candidate_ids=("unknown",))


def test_index_cannot_be_reused_with_another_snapshot(tmp_path):
    binding = _binding(tmp_path)
    index = build_released_target_index(
        binding.store("intent-boundaries"), data_root=tmp_path, legal_candidate_ids=LEGAL,
    )
    with pytest.raises(RailsError, match="another snapshot"):
        lookup_knowledge_targets(
            binding.snapshot_for("slot-contracts"), _query(), LEGAL,
            target_index=index, max_values_per_candidate=4, max_total_values=4,
        )


def test_native_tool_routes_authored_values_and_records_source(tmp_path):
    binding = _binding(tmp_path)
    program = default_phase_program("phase-native-candidates-review-revise-v1")
    router = build_knowledge_store_supply(
        binding, program=program, data_root=tmp_path,
        legal_candidate_ids=LEGAL, on_demand_store_ids=binding.store_ids,
    )
    config = _config()
    config["phase_tools"]["reviewer"]["knowledge_store_ids"] = list(binding.store_ids)
    custody = Custody()
    tool = build_phase_tools(
        config, program, snapshot=binding.composite_snapshot,
        knowledge_stores=binding, supply_for_store=router, tool_contact=custody,
    )
    args = {
        "store_id": "slot-contracts", "view": "text",
        "candidate_ids": list(LEGAL), "distinction": "Check the meaning of the time field.",
    }
    context = _context(tool, binding, args)
    step = tool("reviewer", "reviewer", context)
    assert step.supply.fusion_decision.selected_value_ids == ("slot-contracts::slot-contract:event_time",)
    document = json.loads(step.state.content)
    assert document["result"]["supply_disposition"] == "acquired"
    assert len(custody.calls) == 1
    assert "Role for" not in json.dumps(document["native_result_content"])
    assert "The time assigned" in json.dumps(document["native_result_content"])
    assert router.receipt["stores"]["slot-contracts"]["target_index"]["source_sha256"] == (
        binding.store("slot-contracts").source_pin["sha256"]
    )


def test_slot_axis_reuses_exact_authored_identity_without_intent_whitelist(tmp_path):
    store = _binding(tmp_path).store("slot-contracts")
    index = build_released_target_index(store, data_root=tmp_path,
                                       legal_candidate_ids=LEGAL, target_axis="slot-type")
    assert dict(index.mappings) == {"event_time": ("slot-contract:event_time",)}
    selected = lookup_knowledge_targets(store.snapshot, _query(), ("event_time",),
        target_index=index, max_values_per_candidate=1, max_total_values=2)
    assert selected.selected_value_ids == ("slot-contract:event_time",)
    assert selected.audit["target_index"]["relation_policy_id"] == "authored-slot-id-v1"
    with pytest.raises(RailsError, match="slot"):
        build_released_target_index(_binding(tmp_path).store("intent-boundaries"),
            data_root=tmp_path, legal_candidate_ids=LEGAL, target_axis="slot-type")


@pytest.mark.parametrize("mode,expected", [("targeted", 1), ("reread", 0)])
def test_planner_slot_axis_uses_mode_and_authored_source(tmp_path, mode, expected):
    binding = _binding(tmp_path)
    program = default_phase_program("phase-native-candidates-review-revise-v1")
    router = build_knowledge_store_supply(binding, program=program, data_root=tmp_path,
        legal_candidate_ids=LEGAL, on_demand_store_ids=binding.store_ids)
    config = _config("planner")
    config["phase_tools"]["planner"].update(knowledge_store_ids=["slot-contracts"],
        knowledge_target_axis="slot-type", knowledge_selection_mode=mode,
        candidate_limit=2, knowledge_value_limit=2, max_calls_per_sample=1)
    tool = build_phase_tools(config, program, snapshot=binding.composite_snapshot,
        knowledge_stores=binding, supply_for_store=router, tool_contact=Custody())
    args = {"store_id": "slot-contracts", "view": "text", "candidate_ids": ["event_time"],
            "distinction": "Check the type meaning of the current time field."}
    step = tool("planner", "planner", _context(tool, binding, args, role="planner"))
    assert len(step.state.cited_value_ids) == expected
    assert "slot type identifiers" in tool.native_tool_schemas()[0]["function"]["description"]
    assert json.loads(step.state.content)["source_authority"]["role_id"] == "planner"
