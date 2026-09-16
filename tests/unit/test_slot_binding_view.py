"""Pure candidate-bound slot-card projection tests and integration fixture."""

from __future__ import annotations
from dataclasses import FrozenInstanceError, replace
import copy
import hashlib
import json
from types import MappingProxyType
import pytest

from speech_aware_evidence_acquisition.core.model.native_framework_history import (
    framework_contact_instruction,
)
from speech_aware_evidence_acquisition.rails.candidate_contract_lookup import (
    canonical_sha256,
)
from speech_aware_evidence_acquisition.rails.core_client import _agent_history
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)
from speech_aware_evidence_acquisition.rails.slot_binding_view import (
    POLICY_ID,
    SlotBindingViewError,
    bind_slot_view_context,
    project_slot_value,
    scope_for_payload,
    validate_slot_view_context,
)

A, B, SAMPLE = "a" * 64, "b" * 64, "sample-1"
LEGAL = ("alpha_one", "beta_two", "gamma_three")


def _write(path, value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _row(slot, bindings):
    return {
        "slot_id": slot,
        "intent_bindings": [{"intent_id": i, "semantic_role": r} for i, r in bindings],
        "extraction_cues": ["Keep this cue exactly; punctuation: yes."],
        "admissible_formats": ["Keep the spoken form."],
        "missing_behavior": "Omit when speech supplies no value.",
        "ambiguity_behavior": "Retain supported ambiguity.",
        "limitations": ["Observed bindings are guidance, not required fields."],
        "source_support": {
            "source_sample_ids": ["train-1"],
            "provenance_refs": [f"prepared://{slot}"],
        },
    }


def _config(root):
    rows = (
        _row(
            "shared",
            (
                ("alpha_one", "Alpha role."),
                ("beta_two", "Beta role."),
                ("gamma_three", "Gamma role."),
            ),
        ),
        _row("alpha_only", (("alpha_one", "Only alpha role."),)),
    )
    snapshot = build_slot_contract_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp",
            source_split_identity_hash=A,
            permitted_source_sample_ids=("train-1",),
        ),
        rows=rows,
    )
    source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": snapshot.builder_policy_id,
        "source_split_identity_hash": A,
        "rows": list(rows),
    }
    source_rel = "knowledge/slot/source.json"
    source_sha = _write(root / source_rel, source)
    snapshot_rel = "knowledge/slot/snapshot.json"
    (root / snapshot_rel).parent.mkdir(parents=True, exist_ok=True)
    (root / snapshot_rel).write_text(json.dumps(snapshot.frozen_json()))
    release_rel = "knowledge/slot/release.json"
    release_sha = _write(
        root / release_rel,
        {
            "schema": "saea-knowledge-store-release-v1",
            "store_id": "slot-contracts",
            "store_role": "slot-contracts",
            "snapshot_sha256": snapshot.content_hash(),
            "source_split_identity_hash": A,
            "builder_policy_id": snapshot.builder_policy_id,
            "source": {"relpath": source_rel, "sha256": source_sha},
        },
    )
    catalog = {
        "schema": "saea-slurp-candidate-contract-catalog-v1",
        "profiles": [{"candidate_id": x} for x in LEGAL],
    }
    catalog_rel = "prepared/catalog.json"
    catalog_sha = _write(root / catalog_rel, catalog)
    material = {
        k: {"response_format_id": None, "fill_params": {}}
        for k in ("perception", "solver", "reviewer", "planner")
    }
    material["perception"] = {
        "response_format_id": "slurp-intent-hypotheses-v1",
        "fill_params": {
            "id": "slurp-intent-hypotheses-v1",
            "min_candidates": 1,
            "max_candidates": 3,
            "source_catalog": {
                "data_relpath": catalog_rel,
                "sha256": catalog_sha,
                "source_sha256": canonical_sha256(catalog),
            },
        },
    }
    return {
        "native_evidence_projection_params": {
            "store_id": "slot-contracts",
            "consumer_roles": ["solver", "reviewer"],
        },
        "native_episode": {
            "roles": {
                k: {"phase_id": k, "max_iterations": 1}
                for k in ("perception", "solver", "reviewer", "planner")
            }
        },
        "phase_material": material,
        "knowledge_stores": {
            "slot-contracts": {
                "store_role": "slot-contracts",
                "snapshot": {
                    "relpath": snapshot_rel,
                    "sha256": snapshot.content_hash(),
                },
                "release": {"relpath": release_rel, "sha256": release_sha},
                "candidate_supply": {
                    "solver": {
                        "provider": "slurp-candidate-semantic-v1",
                        "rank_policy": "saea-ranked-candidate-round-robin-v1",
                        "fuse_policy": "saea-candidate-semantic-passthrough-v1",
                        "candidate_state_phase": "perception",
                        "compact_source_phase": "perception",
                        "projection_policy": "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
                        "max_candidates": 3,
                        "max_values_per_candidate": 2,
                        "max_total_values": 6,
                    }
                },
            }
        },
    }


def _state(phase, content, state_id=None):
    return AgentStateArtifact(
        state_id=state_id or f"{phase}:{SAMPLE}",
        state_kind=f"phase:{phase}",
        content=content,
        source_query_state_sha256=B,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="synthetic-native-v1",
        cited_value_ids=(),
    ).validate()


def _perception(*ids, raw=None):
    return _state(
        "perception",
        raw
        or json.dumps(
            {
                "candidates": [
                    {
                        "intent_id": x,
                        "distinction": f"Distinguish {x}.",
                        "evidence_refs": [],
                        "unresolved_fields": [],
                    }
                    for x in ids
                ]
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def _solver(intent, state_id=None, raw=None):
    scenario, action = intent.split("_", 1)
    return _state(
        "solver",
        raw
        or json.dumps(
            {"scenario": scenario, "action": action, "entities": []},
            sort_keys=True,
            separators=(",", ":"),
        ),
        state_id,
    )


def _payload(config, states=(), role="solver"):
    framework = [
        {"role": "system", "content": "Solve."},
        {"role": "user", "content": "Interpret speech."},
    ]
    instruction = framework_contact_instruction(
        role_id=role,
        sample_id=SAMPLE,
        contact_id=f"{role}-contact",
        messages=framework,
        local_tool_result_ids=(),
    )
    return {
        "sample_id": SAMPLE,
        "task_instruction": "Solve.",
        "history": _agent_history(
            agent_state=[x.as_json() for x in states],
            agent_contact_id=f"{role}-contact",
            contact_instruction=instruction,
        ),
    }


def context_world(tmp_path):
    """Reusable pinned miniature context/config/payload for transport tests."""
    config = _config(tmp_path)
    context = bind_slot_view_context(config, tmp_path)
    return context, config, _payload(config, (_perception("alpha_one", "beta_two"),))


def _target(context, local="slot-contract:shared"):
    evidence_id = f"slot-contracts::{local}"
    value = next(
        v
        for v in context.knowledge_binding.composite_snapshot.values
        if v.value_id == evidence_id
    )
    text = context.knowledge_binding.model_evidence_block(
        "slot-contracts", local_evidence_id=local, content=value.content
    )["text"]
    uri = (
        f"knowledge-snapshot://{context.knowledge_binding.binding_sha256}/{evidence_id}"
    )
    return evidence_id, uri, text


def _tool(
    context, source, candidates, selected=("slot-contracts::slot-contract:shared",)
):
    result = {
        "store_id": "slot-contracts",
        "store_role": "slot-contracts",
        "selected_value_ids": list(selected),
        "supporting_facet_ids": list(selected),
        "knowledge_view": "text",
        "candidate_ids": list(candidates),
        "missing_candidate_ids": [],
        "supply_disposition": "already-visible",
    }
    doc = {
        "schema": "saea-phase-tool-result-v2",
        "tool_id": "saea-tool-knowledge-target-lookup-v1",
        "phase": source.state_kind[6:],
        "sample_id": SAMPLE,
        "snapshot_sha256": context.knowledge_binding.binding_sha256,
        "native_source_state_id": source.state_id,
        "result": result,
        "result_sha256": content_hash(result),
    }
    return AgentStateArtifact(
        state_id=f"tool-result:{source.state_id}",
        state_kind="tool-result",
        content=json.dumps(doc, sort_keys=True, separators=(",", ":")),
        source_query_state_sha256=B,
        source_response_sha256=source.source_response_sha256,
        producer_policy_id="synthetic-native-v1",
        cited_value_ids=tuple(selected),
    ).validate()


def test_context_is_source_bound_and_immutable(tmp_path):
    context, _, _ = context_world(tmp_path)
    validate_slot_view_context(context)
    assert context.policy_id == POLICY_ID
    assert context.value_ids == (
        "slot-contracts::slot-contract:alpha_only",
        "slot-contracts::slot-contract:shared",
    )
    assert json.loads(context.rows[1].canonical_json)["slot_id"] == "shared"
    with pytest.raises(FrozenInstanceError):
        context.context_sha256 = "x"
    with pytest.raises(TypeError):
        context.rows_by_value_id[context.value_ids[0]] = context.rows[0]
    with pytest.raises(SlotBindingViewError, match="context"):
        validate_slot_view_context(replace(context, context_sha256="0" * 64))
    swapped = MappingProxyType(
        dict(zip(context.value_ids, reversed(context.rows), strict=True))
    )
    with pytest.raises(SlotBindingViewError, match="row index"):
        validate_slot_view_context(replace(context, rows_by_value_id=swapped))


def test_initial_solver_projects_only_binding_rows_and_keeps_global_fields(tmp_path):
    context, _, payload = context_world(tmp_path)
    scope = scope_for_payload(payload, context)
    assert scope["candidate_ids"] == ["alpha_one", "beta_two"]
    evidence_id, uri, full = _target(context)
    projected, receipt = project_slot_value(
        context, evidence_id=evidence_id, source_uri=uri, content=full, scope=scope
    )
    assert "alpha_one: Alpha role." in projected and "beta_two: Beta role." in projected
    assert "gamma_three: Gamma role." not in projected
    for text in (
        "Keep this cue exactly; punctuation: yes.",
        "Keep the spoken form.",
        "Omit when speech supplies no value.",
        "Retain supported ambiguity.",
        "Observed bindings are guidance, not required fields.",
    ):
        assert text in projected
    assert receipt["disposition"] == "projected"


def test_reviewer_unions_candidate_draft_and_explicit_tool_target(tmp_path):
    context, config, _ = context_world(tmp_path)
    old = _solver("alpha_one", f"old:solver:{SAMPLE}")
    latest = _solver("gamma_three", f"new:solver:{SAMPLE}")
    reviewer = _state("reviewer", "Inspect.")
    tool = _tool(context, reviewer, ("beta_two",))
    scope = scope_for_payload(
        _payload(
            config, (_perception("alpha_one"), old, latest, reviewer, tool), "reviewer"
        ),
        context,
    )
    assert scope["candidate_ids"] == ["alpha_one", "gamma_three", "beta_two"]
    assert scope["sources"]["solver_state_id"] == latest.state_id
    assert scope["sources"]["target_tool_state_ids"] == [tool.state_id]


def test_tool_source_excluded_and_latest_bad_draft_forces_fallback(tmp_path):
    context, config, _ = context_world(tmp_path)
    valid = _solver("gamma_three", f"valid:solver:{SAMPLE}")
    source = _state("solver", "not draft", f"tool-source:solver:{SAMPLE}")
    scope = scope_for_payload(
        _payload(
            config,
            (
                _perception("alpha_one"),
                valid,
                source,
                _tool(context, source, ("beta_two",), ()),
            ),
            "reviewer",
        ),
        context,
    )
    assert scope["sources"]["solver_state_id"] == valid.state_id
    bad = _state("solver", "not json", f"bad:solver:{SAMPLE}")
    scope = scope_for_payload(
        _payload(config, (_perception("alpha_one"), valid, bad), "reviewer"), context
    )
    assert scope["candidate_ids"] == []
    assert scope["fallback_reason"] == "malformed-latest-solver-draft"


def test_fallback_full_body_no_binding_and_nonconsumer(tmp_path):
    context, config, _ = context_world(tmp_path)
    assert (
        scope_for_payload(_payload(config), context)["fallback_reason"]
        == "missing-perception-candidates"
    )
    assert (
        scope_for_payload(
            _payload(config, (_perception("alpha_one"),), "reviewer"), context
        )["fallback_reason"]
        == "missing-latest-solver-draft"
    )
    planner = scope_for_payload(
        _payload(config, (_perception("alpha_one"),), "planner"), context
    )
    assert not planner["eligible"]
    assert project_slot_value(
        context, evidence_id="foreign", source_uri="x", content="same", scope=planner
    ) == ("same", None)
    gamma = scope_for_payload(_payload(config, (_perception("gamma_three"),)), context)
    evidence_id, uri, full = _target(context, "slot-contract:alpha_only")
    value, receipt = project_slot_value(
        context, evidence_id=evidence_id, source_uri=uri, content=full, scope=gamma
    )
    assert value == full and receipt["fallback_reason"] == "no-applicable-binding"
    assert receipt["binding_content_disposition"] == "full-card-retained"
    assert receipt["omitted_binding_addresses"] == []
    assert receipt["retained_binding_addresses"] == ["intent_bindings/0"]


def test_full_card_and_conflict_guards(tmp_path):
    context, config, payload = context_world(tmp_path)
    scope = scope_for_payload(_payload(config, (_perception(*LEGAL),)), context)
    evidence_id, uri, full = _target(context)
    value, receipt = project_slot_value(
        context, evidence_id=evidence_id, source_uri=uri, content=full, scope=scope
    )
    assert value == full and receipt["disposition"] == "full-body-no-excluded-bindings"
    for field in ("source_uri", "content"):
        args = {"evidence_id": evidence_id, "source_uri": uri, "content": full}
        args[field] += "-changed"
        with pytest.raises(SlotBindingViewError, match="differs"):
            project_slot_value(
                context, scope=scope_for_payload(payload, context), **args
            )


def test_closed_params_duplicate_json_and_state_hash(tmp_path):
    context, config, _ = context_world(tmp_path)
    changed = copy.deepcopy(config)
    changed["native_evidence_projection_params"]["extra"] = True
    with pytest.raises(SlotBindingViewError, match="params"):
        bind_slot_view_context(changed, tmp_path)
    duplicate = _perception(raw='{"candidates":[],"candidates":[]}')
    assert (
        scope_for_payload(_payload(config, (duplicate,)), context)["fallback_reason"]
        == "malformed-perception-candidates"
    )
    payload = _payload(config, (_perception("alpha_one"),))
    payload["history"][0]["content_sha256"] = "0" * 64
    with pytest.raises(SlotBindingViewError, match="content hash"):
        scope_for_payload(payload, context)
