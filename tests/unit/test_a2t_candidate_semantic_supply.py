"""Compiled parameter guidance follows ordered native action candidates."""
from dataclasses import replace
import csv
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (
    CandidateSemanticSupplyError,
)
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply, load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.knowledge_provider import (
    Audio2ToolCandidateSemanticProvider,
)
from test_candidate_semantic_supply import _context, _latest_context, _program
from test_compiled_knowledge_store_preparation import _prepared


def _action(index, names):
    return {"action_id": f"action:{index}", "candidate_tools": list(names),
            "evidence": "Evidence from the bound speech.", "uncertain_arguments": []}


def _state(actions, sample_id="s1", *, state_id=None, source_query=None):
    content = json.dumps({"actions": actions, "global_constraints": ["Keep order."]})
    return AgentStateArtifact(
        state_id=state_id or f"perception:{sample_id}", state_kind="phase:perception",
        content=content, source_query_state_sha256=source_query or "b" * 64,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="synthetic-native-perception", cited_value_ids=(),
    ).validate()


def _route(tmp_path, *, view="parameter-meaning", overrides=None,
           phase="solve", program=None):
    repo, prepared, path, _ = _prepared(tmp_path, view)
    result = prepare_semantic_knowledge_store(
        path, repo_root=repo, data_root=prepared.data_root,
    )
    completion = result["completion"]
    spec = {
        "provider": "audio2tool-candidate-semantic-v1",
        "rank_policy": "saea-ranked-candidate-round-robin-v1",
        "fuse_policy": "saea-candidate-semantic-passthrough-v1",
        "candidate_state_phase": "perception", "compact_source_phase": "perception",
        "max_actions": 7, "max_candidates_per_action": 4,
        "max_values_per_candidate": 1, "max_total_values": 28,
    }
    spec.update(overrides or {})
    values = {"knowledge_stores": {view: {
        "store_role": view, "snapshot": completion["snapshot"],
        "release": completion["release"], "candidate_supply": {phase: spec},
    }}}
    binding = load_knowledge_store_binding(values, data_root=prepared.data_root)
    with prepared.tool_registry_path.open() as handle:
        legal = tuple(row["tool_name"] for row in csv.DictReader(handle))
    router = build_knowledge_store_supply(
        binding, program=program or _program("perception"), data_root=prepared.data_root,
        legal_candidate_ids=legal,
        candidate_inventory_authority="audio2tool-public-tool-registry",
        candidate_inventory_source_sha256=hashlib.sha256(
            prepared.tool_registry_path.read_bytes()
        ).hexdigest(),
    )
    return binding, router


def test_ordered_repeated_actions_select_distinct_parameter_values_and_real_keys(tmp_path):
    binding, router = _route(tmp_path)
    actions = [_action(i, ("syntheticTool003", "syntheticTool001",
                           "syntheticTool003", "syntheticTool002")) for i in range(5)]
    artifact = _state(actions)
    before = artifact.content
    supply = router.automatic_for_phase("solve", _context(binding, artifact))
    assert supply.fusion_decision.selected_value_ids == tuple(
        f"parameter-meaning::a2t-native-card:{name}:value"
        for name in ("syntheticTool003", "syntheticTool001", "syntheticTool002")
    )
    assert supply.fusion_decision.supporting_facet_ids == tuple(
        value.replace(":value", ":content")
        for value in supply.fusion_decision.selected_value_ids
    )
    assert {entry.facet_id for entry in supply.rank_result.candidates} == set(
        supply.fusion_decision.supporting_facet_ids
    )
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["candidate_occurrences"] == [
        {"action_id": row["action_id"], "candidate_tools": row["candidate_tools"]}
        for row in actions
    ]
    assert audit["candidate_ids"] == [
        "syntheticTool003", "syntheticTool001", "syntheticTool002"
    ]
    assert audit["max_actions"] == 7 and audit["max_candidates_per_action"] == 4
    assert artifact.content == before
    assert len(binding.composite_snapshot.values) == 152


def test_action_occurrence_capacity_may_exceed_distinct_tool_inventory():
    legal = ("toolAlpha", "toolBeta")
    provider = Audio2ToolCandidateSemanticProvider(
        candidate_values={
            "toolAlpha": ("value-alpha",),
            "toolBeta": ("value-beta",),
        },
        legal_candidate_ids=legal,
        max_actions=3,
        max_candidates_per_action=2,
        max_values_per_candidate=1,
        max_total_values=6,
        compact_source_phase="perception",
    )
    actions = [
        _action(0, legal),
        _action(1, tuple(reversed(legal))),
        _action(2, legal),
    ]
    candidate_ids, audit = provider._candidate_state(
        _state(actions), sample_id="s1"
    )
    assert candidate_ids == legal
    assert audit["candidate_occurrences"] == [
        {"action_id": row["action_id"], "candidate_tools": row["candidate_tools"]}
        for row in actions
    ]


def test_no_action_state_supplies_no_parameter_card_without_filling_candidates(tmp_path):
    binding, router = _route(tmp_path)
    assert router.automatic_for_phase("solve", _context(binding, _state([]))) is None
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["candidate_ids"] == [] and audit["selected_value_ids"] == []
    assert audit["supply_disposition"] == "no-mapping"


def test_latest_state_adds_only_new_values_with_their_actual_associated_facets(tmp_path):
    binding, router = _route(tmp_path, overrides={"candidate_state_selection": "latest"})
    old = _state([_action(0, ("syntheticTool001",))], state_id="old:perception:s1")
    new = _state([_action(0, ("syntheticTool001", "syntheticTool002"))],
                 state_id="new:perception:s1")
    context = _latest_context(
        binding, (old, new),
        retrieved_value_ids=("parameter-meaning::a2t-native-card:syntheticTool001:value",),
    )
    supply = router.automatic_for_phase("solve", context)
    assert supply.fusion_decision.selected_value_ids == (
        "parameter-meaning::a2t-native-card:syntheticTool002:value",
    )
    assert supply.fusion_decision.supporting_facet_ids == (
        "parameter-meaning::a2t-native-card:syntheticTool002:content",
    )
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert len(audit["selected_value_ids"]) == 2
    assert len(audit["added_value_ids"]) == 1


@pytest.mark.parametrize("defect", ["unknown-tool", "wrong-sample", "wrong-content",
                                   "duplicate-occurrence", "too-many-alternatives"])
def test_native_candidate_supply_rejects_invalid_state_without_repair(tmp_path, defect):
    binding, router = _route(tmp_path)
    actions = [_action(0, ("syntheticTool001",))]
    if defect == "unknown-tool":
        actions = [_action(0, ("unregisteredTool",))]
    elif defect == "duplicate-occurrence":
        actions.append(actions[0])
    elif defect == "too-many-alternatives":
        actions = [_action(0, tuple(f"syntheticTool{i:03d}" for i in range(5)))]
    artifact = _state(actions)
    if defect == "wrong-sample":
        artifact = replace(artifact, state_id="perception:another-sample")
    elif defect == "wrong-content":
        artifact = replace(artifact, content=artifact.content + " ")
    with pytest.raises(CandidateSemanticSupplyError):
        router.automatic_for_phase("solve", _context(binding, artifact))


@pytest.mark.parametrize("overrides", [
    {"max_actions": 0}, {"max_candidates_per_action": True},
    {"max_candidates": 3}, {"compact_source_phase": None},
    {"projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"},
])
def test_native_route_refuses_implicit_slurp_bounds_and_projection(tmp_path, overrides):
    with pytest.raises(CandidateSemanticSupplyError):
        _route(tmp_path, overrides=overrides)


def test_activation_values_cannot_masquerade_as_parameter_guidance(tmp_path):
    with pytest.raises(CandidateSemanticSupplyError, match="parameter-meaning"):
        _route(tmp_path, view="tool-activation")


@pytest.mark.parametrize("defect", ["absent", "foreign-source", "foreign-authority", "partial"])
def test_runtime_refuses_missing_or_mismatched_inventory_before_any_request(tmp_path, defect):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntime, FlightRuntimeError,
    )
    from speech_aware_evidence_acquisition.rails.task_adapter import CandidateInventory

    binding, _ = _route(tmp_path)
    source_path = tmp_path / "data/datasets/audio2tool/tools_registry.csv"
    with source_path.open() as handle:
        ids = tuple(row["tool_name"] for row in csv.DictReader(handle))
    inventory = CandidateInventory(
        candidate_ids=ids[:-1] if defect == "partial" else ids,
        source_sha256=(
            "0" * 64 if defect == "foreign-source"
            else hashlib.sha256(source_path.read_bytes()).hexdigest()
        ),
        source_authority=(
            "another-source" if defect == "foreign-authority"
            else "audio2tool-public-tool-registry"
        ),
    )
    runtime = object.__new__(FlightRuntime)
    runtime._adapter = SimpleNamespace(
        candidate_inventory=lambda: None if defect == "absent" else inventory,
    )
    runtime._composed = SimpleNamespace(values={})
    runtime._knowledge_store_binding = binding
    runtime._data_root = tmp_path / "data"
    with pytest.raises(FlightRuntimeError, match="inventory|source|authority|cover"):
        runtime._resolve_phase_supply(_program("perception"), binding.composite_snapshot)
    assert not hasattr(runtime, "_knowledge_store_supply")
