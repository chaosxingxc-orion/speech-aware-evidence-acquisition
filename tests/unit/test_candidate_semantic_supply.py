"""Candidate-conditioned semantic supply stays bounded and source-bound."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (
    CandidateSemanticSupplyError,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    EvidenceAgentController,
    PhaseProgram,
    PhaseSpec,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def _write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _slot_row(slot_id, intents):
    return {
        "slot_id": slot_id,
        "intent_bindings": [
            {"intent_id": intent, "semantic_role": f"Role for {intent}."}
            for intent in intents
        ],
        "extraction_cues": ["Extract only an explicitly supported mention."],
        "admissible_formats": ["Keep the spoken form."],
        "missing_behavior": "Omit the slot when speech provides no value.",
        "ambiguity_behavior": "Retain ambiguity supported by the speech.",
        "limitations": [
            "Observed intent bindings index guidance; they are not required fields."
        ],
        "source_support": {
            "source_sample_ids": ["train-1"],
            "provenance_refs": [f"prepared-support://synthetic/{slot_id}"],
        },
    }


def _program():
    return PhaseProgram(
        program_id="synthetic-hypotheses-then-solve-v1",
        phases=(
            PhaseSpec("hypotheses", "propose", "none", None, False),
            PhaseSpec("solve", "solve", "supplied", None, False),
        ),
        max_contacts=2,
        stop_rule="always-run-full-program",
    ).validate()


def _store(tmp_path, store_id, role, snapshot, source):
    source_relpath = f"knowledge/{store_id}/source.json"
    source_sha = _write(tmp_path / source_relpath, source)
    snapshot_relpath = f"knowledge/{store_id}/snapshot.json"
    snapshot_path = tmp_path / snapshot_relpath
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps(snapshot.frozen_json()), encoding="utf-8")
    release_relpath = f"knowledge/{store_id}/release.json"
    release_sha = _write(
        tmp_path / release_relpath,
        {
            "schema": "saea-knowledge-store-release-v1",
            "store_id": store_id,
            "store_role": role,
            "snapshot_sha256": snapshot.content_hash(),
            "source_split_identity_hash": snapshot.source_split_identity_hash,
            "builder_policy_id": snapshot.builder_policy_id,
            "source": {"relpath": source_relpath, "sha256": source_sha},
        },
    )
    return {
        "store_role": role,
        "snapshot": {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()},
        "release": {"relpath": release_relpath, "sha256": release_sha},
    }


def _config(tmp_path, *, rows=None, inventory=("alpha", "beta", "gamma", "delta")):
    rows = rows or (
        _slot_row("shared", ("alpha", "beta")),
        _slot_row("alpha_one", ("alpha",)),
        _slot_row("alpha_two", ("alpha",)),
        _slot_row("beta_one", ("beta",)),
        _slot_row("gamma_one", ("gamma",)),
        _slot_row("unused", ("gamma",)),
    )
    slot_snapshot = build_slot_contract_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp",
            source_split_identity_hash=SHA_A,
            permitted_source_sample_ids=("train-1",),
        ),
        rows=rows,
    )
    slot_source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": slot_snapshot.builder_policy_id,
        "source_split_identity_hash": SHA_A,
        "rows": list(rows),
    }
    stores = {
        "slot-contracts": _store(
            tmp_path, "slot-contracts", "slot-contracts", slot_snapshot, slot_source
        ),
    }
    stores["slot-contracts"]["candidate_supply"] = {
        "solve": {
            "provider": "slurp-candidate-semantic-v1",
            "rank_policy": "saea-ranked-candidate-round-robin-v1",
            "fuse_policy": "saea-candidate-semantic-passthrough-v1",
            "candidate_state_phase": "hypotheses",
            "max_candidates": 3,
            "max_values_per_candidate": 1,
            "max_total_values": 3,
        }
    }
    return {"knowledge_stores": stores}, inventory


def _artifact(sample_id, intents):
    content = json.dumps(
        {
            "schema": "saea-slurp-intent-hypotheses-v1",
            "semantics": "ranked-mutually-exclusive-intent-alternatives",
            "sample_id": sample_id,
            "candidates": [
                {
                    "intent_id": intent,
                    "distinction": f"Evidence for {intent}.",
                    "evidence_refs": ["speech"],
                    "unresolved_fields": [],
                }
                for intent in intents
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return AgentStateArtifact(
        state_id=f"hypotheses:{sample_id}",
        state_kind="phase:hypotheses",
        content=content,
        source_query_state_sha256=SHA_B,
        source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="synthetic-hypothesis-proposer-v1",
        cited_value_ids=(),
    ).validate()


def _context(binding, artifact, sample_id="s1"):
    query = QueryState(
        query_id=f"query:{sample_id}",
        query_sample_id=sample_id,
        speech_packet_id=f"packet:{sample_id}",
        speech_packet_sha256=SHA_B,
        use_split_identity_hash=SHA_A,
        query_source="speech_features",
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id,
        knowledge_snapshot_sha256=binding.binding_sha256,
        catalog_facet_ids=tuple(f.facet_id for f in binding.composite_snapshot.facets),
        catalog_value_ids=tuple(v.value_id for v in binding.composite_snapshot.values),
        query_state=query,
        task_contract="synthetic full legal label and type inventory",
        agent_states=(artifact,),
        prior_response_sha256s=(artifact.source_response_sha256,),
        contact_index=1,
    )


def test_ranked_candidates_select_released_cards_round_robin_without_dumping_catalog(
    tmp_path,
):
    config, legal = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )

    supply = router.automatic_for_phase(
        "solve", _context(binding, _artifact("s1", ("beta", "alpha", "gamma")))
    )

    assert supply.fusion_decision.selected_value_ids == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
        "slot-contracts::slot-contract:gamma_one",
    )
    assert len(supply.fusion_decision.selected_value_ids) == 3
    assert (
        "slot-contracts::slot-contract:unused"
        not in supply.fusion_decision.selected_value_ids
    )
    assert supply.rank_result.snapshot_sha256 == binding.binding_sha256


def test_shared_controller_supplies_selected_cards_to_solver_without_tools(tmp_path):
    config, legal = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    source_context = _context(binding, _artifact("s1", ("beta", "alpha")))
    initial_context = AgentRuntimeContext(
        sample_id=source_context.sample_id,
        knowledge_snapshot_sha256=source_context.knowledge_snapshot_sha256,
        catalog_facet_ids=source_context.catalog_facet_ids,
        catalog_value_ids=source_context.catalog_value_ids,
        query_state=source_context.query_state,
        task_contract=source_context.task_contract,
        agent_states=(),
        prior_response_sha256s=(),
        contact_index=0,
    )
    controller = EvidenceAgentController(
        program=_program(),
        material_for_phase=lambda phase, context: PhaseMaterial(
            instruction=f"Complete {phase} for {context.sample_id}.",
            response_format=None,
            contact_id=f"{phase}:{context.sample_id}",
            purpose=phase,
        ),
        supply_for_phase=router.automatic_for_phase,
    )

    propose = controller.initial_contact(initial_context)
    advance = controller.advance(
        initial_context, propose, _artifact("s1", ("beta", "alpha")).content
    )

    assert advance.next_contact is not None
    assert advance.next_contact.purpose == "solve"
    assert advance.next_query_state.retrieved_value_ids == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
    )
    assert advance.transition.action_kind == "acquire"
    assert controller._tools_for_phase is None


def test_selection_receipt_logs_candidate_state_selected_ignored_and_absent_mappings(
    tmp_path,
):
    config, legal = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    artifact = _artifact("s1", ("alpha", "delta"))

    supply = router.automatic_for_phase("solve", _context(binding, artifact))
    audit = next(
        audit for key, audit in router.receipt["candidate_selections"].items()
        if key.startswith("solve:s1:")
    )

    assert audit["candidate_ids"] == ["alpha", "delta"]
    assert audit["candidate_state_id"] == artifact.state_id
    assert (
        audit["candidate_state_sha256"]
        == hashlib.sha256(artifact.content.encode()).hexdigest()
    )
    assert audit["selected_value_ids"] == ["slot-contract:alpha_one"]
    assert audit["qualified_selected_value_ids"] == list(
        supply.fusion_decision.selected_value_ids
    )
    assert audit["mappings"][0]["ignored_mappings"] == [
        {"reason": "per-candidate-limit", "value_id": "slot-contract:alpha_two"},
        {"reason": "per-candidate-limit", "value_id": "slot-contract:shared"},
    ]
    assert audit["mappings"][1] == {
        "candidate_id": "delta",
        "mapped_value_ids": [],
        "selected_value_ids": [],
        "ignored_mappings": [],
        "status": "absent",
    }
    assert len(audit["selection_sha256"]) == 64


def test_one_candidate_stays_one_candidate_and_missing_source_state_is_refused(
    tmp_path,
):
    config, legal = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    supply = router.automatic_for_phase(
        "solve", _context(binding, _artifact("s1", ("gamma",)))
    )
    audit = next(
        audit for key, audit in router.receipt["candidate_selections"].items()
        if key.startswith("solve:s1:")
    )
    assert audit["candidate_ids"] == ["gamma"]
    assert len(supply.fusion_decision.selected_value_ids) == 1

    absent = router.automatic_for_phase(
        "solve", _context(binding, _artifact("s2", ("delta",)), sample_id="s2")
    )
    assert absent is None
    absent_audit = next(
        audit for key, audit in router.receipt["candidate_selections"].items()
        if key.startswith("solve:s2:")
    )
    assert absent_audit["selected_value_ids"] == []
    assert absent_audit["mappings"][0]["status"] == "absent"

    missing = _context(binding, _artifact("s1", ("gamma",)))
    missing = AgentRuntimeContext(**{**missing.__dict__, "agent_states": ()})
    with pytest.raises(CandidateSemanticSupplyError, match="exactly one source-bound"):
        router.automatic_for_phase("solve", missing)


def test_candidate_index_refuses_values_or_candidates_outside_released_stores(tmp_path):
    unknown_value_config, legal = _config(tmp_path / "unknown-value")
    slot_source = unknown_value_config["knowledge_stores"]["slot-contracts"]
    source_path = (
        tmp_path
        / "unknown-value"
        / json.loads(
            (tmp_path / "unknown-value" / slot_source["release"]["relpath"]).read_text()
        )["source"]["relpath"]
    )
    source = json.loads(source_path.read_text())
    source["rows"].append(_slot_row("not_released", ("alpha",)))
    source_sha = _write(source_path, source)
    release_path = tmp_path / "unknown-value" / slot_source["release"]["relpath"]
    release = json.loads(release_path.read_text())
    release["source"]["sha256"] = source_sha
    slot_source["release"]["sha256"] = _write(release_path, release)
    binding = load_knowledge_store_binding(
        unknown_value_config, data_root=tmp_path / "unknown-value"
    )
    with pytest.raises(
        CandidateSemanticSupplyError, match="differs from the released snapshot"
    ):
        build_knowledge_store_supply(
            binding,
            program=_program(),
            data_root=tmp_path / "unknown-value",
            legal_candidate_ids=legal,
        )

    unknown_candidate_config, legal = _config(
        tmp_path / "unknown-candidate",
        rows=(_slot_row("only", ("not_legal",)),),
    )
    binding = load_knowledge_store_binding(
        unknown_candidate_config, data_root=tmp_path / "unknown-candidate"
    )
    with pytest.raises(
        CandidateSemanticSupplyError, match="outside the full released inventory"
    ):
        build_knowledge_store_supply(
            binding,
            program=_program(),
            data_root=tmp_path / "unknown-candidate",
            legal_candidate_ids=legal,
        )


def test_candidate_supply_requires_a_later_supplied_phase_and_exact_known_fields(
    tmp_path,
):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["gold_intent"] = "alpha"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    with pytest.raises(CandidateSemanticSupplyError, match="wrong fields"):
        build_knowledge_store_supply(
            binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
        )

    config, legal = _config(tmp_path / "wrong-phase")
    config["knowledge_stores"]["slot-contracts"]["candidate_supply"] = {
        "hypotheses": config["knowledge_stores"]["slot-contracts"]["candidate_supply"][
            "solve"
        ]
    }
    binding = load_knowledge_store_binding(config, data_root=tmp_path / "wrong-phase")
    with pytest.raises(
        CandidateSemanticSupplyError, match="later than candidate_state_phase"
    ):
        build_knowledge_store_supply(
            binding,
            program=_program(),
            data_root=tmp_path / "wrong-phase",
            legal_candidate_ids=legal,
        )


def test_native_compact_candidates_reach_released_cards_only_when_configured(tmp_path):
    config, legal = _config(tmp_path)
    source = _artifact("s1", ("beta", "alpha"))
    raw = json.dumps({"candidates": json.loads(source.content)["candidates"]})
    source = replace(
        source, content=raw,
        source_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
    )
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    strict = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    with pytest.raises(CandidateSemanticSupplyError, match="exactly"):
        strict.automatic_for_phase("solve", _context(binding, source))
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["compact_source_phase"] = "hypotheses"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    supply = router.automatic_for_phase("solve", _context(binding, source))
    assert supply is not None
    assert len(supply.fusion_decision.selected_value_ids) == 2
    assert source.content == raw


def test_compact_source_phase_cannot_change_the_configured_candidate_source(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["compact_source_phase"] = "solve"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    with pytest.raises(CandidateSemanticSupplyError, match="compact_source_phase"):
        build_knowledge_store_supply(
            binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
        )


def test_solver_revision_retains_bounded_cards_and_records_each_query(tmp_path):
    config, legal = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    initial = _context(binding, _artifact("s1", ("alpha", "beta")))
    first = router.automatic_for_phase("solve", initial)
    selected = first.fusion_decision.selected_value_ids
    revised = replace(
        initial,
        query_state=replace(
            initial.query_state, loop_step=2,
            retrieved_value_ids=selected,
            visible_facet_ids=first.fusion_decision.supporting_facet_ids,
        ).validate(),
    )
    assert router.automatic_for_phase("solve", revised) is None
    audits = list(router.receipt["candidate_selections"].values())
    assert len(audits) == 2
    assert {a["supply_disposition"] for a in audits} == {"acquired", "already-visible"}
    assert len({a["query_state_sha256"] for a in audits}) == 2
    assert all(a["qualified_selected_value_ids"] == list(selected) for a in audits)
    assert router.automatic_for_phase("solve", revised) is None
    assert len(router.receipt["candidate_selections"]) == 2


def test_revision_cannot_partially_overlap_or_reveal_next_cards(tmp_path):
    config, legal = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    initial = _context(binding, _artifact("s1", ("alpha", "beta")))
    first = router.automatic_for_phase("solve", initial)
    changed = replace(
        initial,
        query_state=replace(
            initial.query_state, loop_step=1,
            retrieved_value_ids=first.fusion_decision.selected_value_ids[:1],
        ).validate(),
    )
    with pytest.raises(CandidateSemanticSupplyError, match="partially overlaps"):
        router.automatic_for_phase("solve", changed)
