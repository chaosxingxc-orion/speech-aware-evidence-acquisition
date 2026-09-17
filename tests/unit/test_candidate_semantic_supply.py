"""Candidate-conditioned semantic supply stays bounded and source-bound."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (
    CandidateSemanticSupplyError,
    CandidateSemanticSupplySpec,
)
from speech_aware_evidence_acquisition.rails.controllers import (
    EvidenceAgentController,
    PhaseProgram,
    PhaseSpec,
    advance_phase_response_state,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    AgentStateArtifact,
    QueryState,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.knowledge_provider import (
    CandidateSemanticProvider,
    select_candidate_semantic_values,
)
from speech_aware_evidence_acquisition.rails.slurp_intent_hypotheses import (
    FALLBACK_CANDIDATE_SOURCE,
    MODEL_CANDIDATE_SOURCE,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.material import PhaseMaterial
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)


SHA_A = "a" * 64
SHA_B = "b" * 64


def test_shared_candidate_selection_helper_preserves_provider_cap_semantics():
    candidate_ids = ("alpha", "beta")
    candidate_values = {
        "alpha": ("alpha-one", "shared", "zz-alpha-three"),
        "beta": ("beta-one", "shared", "zz-beta-three"),
    }
    expected = select_candidate_semantic_values(
        candidate_ids,
        candidate_values,
        max_values_per_candidate=2,
        max_total_values=3,
    )
    provider = object.__new__(CandidateSemanticProvider)
    provider._candidate_values = candidate_values
    provider._max_values_per_candidate = 2
    provider._max_total_values = 3

    assert provider._select(candidate_ids) == expected
    selected, mappings = expected
    assert selected == ("alpha-one", "beta-one", "shared")
    assert mappings[0]["ignored_mappings"] == [
        {"value_id": "zz-alpha-three", "reason": "per-candidate-limit"}
    ]
    assert mappings[1]["ignored_mappings"] == [
        {"value_id": "shared", "reason": "shared-value-already-selected"},
        {"value_id": "zz-beta-three", "reason": "total-limit"},
    ]


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


def _program(candidate_state_phase="hypotheses"):
    return PhaseProgram(
        program_id="synthetic-hypotheses-then-solve-v1",
        phases=(
            PhaseSpec(candidate_state_phase, "propose", "none", None, False),
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


def _config(
    tmp_path,
    *,
    rows=None,
    inventory=("alpha", "beta", "gamma", "delta"),
    max_candidates=3,
):
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
            "max_candidates": max_candidates,
            "max_values_per_candidate": 1,
            "max_total_values": max_candidates,
        }
    }
    return {"knowledge_stores": stores}, inventory


def _artifact(
    sample_id,
    intents,
    *,
    state_id=None,
    state_kind="phase:hypotheses",
    source_query_state_sha256=SHA_B,
):
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
        state_id=state_id or f"hypotheses:{sample_id}",
        state_kind=state_kind,
        content=content,
        source_query_state_sha256=source_query_state_sha256,
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


def _latest_context(binding, artifacts, *, retrieved_value_ids=(), sample_id="s1"):
    context = _context(binding, artifacts[-1], sample_id=sample_id)
    query_state = replace(
        context.query_state,
        agent_state_ids=tuple(artifact.state_id for artifact in artifacts),
        retrieved_value_ids=tuple(retrieved_value_ids),
    ).validate()
    return replace(
        context,
        query_state=query_state,
        agent_states=tuple(artifacts),
        prior_response_sha256s=tuple(
            artifact.source_response_sha256 for artifact in artifacts
        ),
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


def test_five_candidates_flow_through_shared_supply_without_catalog_dump(tmp_path):
    inventory = ("alpha", "beta", "gamma", "delta", "epsilon")
    rows = tuple(_slot_row(f"{intent}_one", (intent,)) for intent in inventory)
    config, legal = _config(
        tmp_path,
        rows=rows,
        inventory=inventory,
        max_candidates=5,
    )
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding,
        program=_program(),
        data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    supply = router.automatic_for_phase(
        "solve", _context(binding, _artifact("s1", inventory))
    )
    assert supply.fusion_decision.selected_value_ids == tuple(
        f"slot-contracts::slot-contract:{intent}_one" for intent in inventory
    )

    config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"][
        "max_candidates"
    ] = 6
    invalid_binding = load_knowledge_store_binding(config, data_root=tmp_path)
    with pytest.raises(CandidateSemanticSupplyError, match="legal candidate"):
        build_knowledge_store_supply(
            invalid_binding,
            program=_program(),
            data_root=tmp_path,
            legal_candidate_ids=legal,
        )
    assert supply.rank_result.snapshot_sha256 == binding.binding_sha256


# ---------------------------------------------------------------------------
# FIX-1 standing fallback candidate
# (docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md)
# ---------------------------------------------------------------------------


def _fallback_config(tmp_path, *, fallback_candidates, extra_rows=()):
    rows = (
        _slot_row("shared", ("alpha", "beta")),
        _slot_row("alpha_one", ("alpha",)),
        _slot_row("alpha_two", ("alpha",)),
        _slot_row("beta_one", ("beta",)),
        _slot_row("gamma_one", ("gamma",)),
        *extra_rows,
    )
    config, legal = _config(
        tmp_path, rows=rows, inventory=("alpha", "beta", "gamma", "delta"),
        max_candidates=3,
    )
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    if fallback_candidates is not None:
        spec["fallback_candidates"] = list(fallback_candidates)
    return config, legal


def test_fallback_candidate_appends_last_and_binds_no_cards_when_unmapped(tmp_path):
    """``delta`` is a legal id with no authored slot row -- the "few or none"
    case the audit expected of ``general_quirky`` (the module docstring on
    ``SlurpCandidateSemanticProvider`` records that the real released source
    binds it 16, not 0 -- this test proves the ZERO-card case is still
    handled, not that ``general_quirky`` itself is empty)."""

    config, legal = _fallback_config(tmp_path, fallback_candidates=["delta"])
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    supply = router.automatic_for_phase(
        "solve", _context(binding, _artifact("s1", ("beta", "alpha")))
    )
    # The model's own two candidates keep their exact cards and order; the
    # appended fallback contributes nothing because it binds no card.
    assert supply.fusion_decision.selected_value_ids == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
    )
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["candidate_ids"] == ["beta", "alpha", "delta"]
    assert audit["candidate_ids_without_fallback"] == ("beta", "alpha")
    assert audit["candidate_sources"] == {
        "beta": MODEL_CANDIDATE_SOURCE,
        "alpha": MODEL_CANDIDATE_SOURCE,
        "delta": FALLBACK_CANDIDATE_SOURCE,
    }
    assert audit["fallback_candidates"] == ["delta"]
    mapping = {row["candidate_id"]: row for row in audit["mappings"]}
    assert mapping["delta"]["status"] == "absent"
    assert mapping["delta"]["selected_value_ids"] == []


def test_fallback_candidate_is_capped_and_visited_last_in_the_round_robin(tmp_path):
    config, legal = _fallback_config(
        tmp_path, fallback_candidates=["delta"],
        extra_rows=(_slot_row("delta_one", ("delta",)), _slot_row("delta_two", ("delta",))),
    )
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    supply = router.automatic_for_phase(
        "solve", _context(binding, _artifact("s1", ("beta", "alpha")))
    )
    # max_values_per_candidate=1 and max_total_values=3 (the fixture's
    # defaults): beta and alpha each take their one round-robin turn first,
    # then delta (LAST, appended) takes the one remaining slot -- never more
    # than the pre-existing per-candidate/total caps, never reordering beta
    # or alpha.
    assert supply.fusion_decision.selected_value_ids == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
        "slot-contracts::slot-contract:delta_one",
    )
    assert len(supply.fusion_decision.selected_value_ids) == 3


def test_fallback_candidate_is_a_noop_when_already_among_model_candidates(tmp_path):
    config, legal = _fallback_config(tmp_path, fallback_candidates=["gamma"])
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    router.automatic_for_phase(
        "solve", _context(binding, _artifact("s1", ("beta", "alpha", "gamma")))
    )
    audit = next(iter(router.receipt["candidate_selections"].values()))
    # gamma was already a model candidate: the fallback appends nothing, so
    # the with/without lists agree and every source is "model" -- but the
    # option is configured, so both coverage fields are still reported (a
    # downstream diagnostic tabulates every row uniformly, never only the
    # rows where the fallback actually fired).
    assert audit["candidate_ids"] == ["beta", "alpha", "gamma"]
    assert audit["candidate_ids_without_fallback"] == ("beta", "alpha", "gamma")
    assert audit["candidate_sources"] == {
        "beta": MODEL_CANDIDATE_SOURCE,
        "alpha": MODEL_CANDIDATE_SOURCE,
        "gamma": MODEL_CANDIDATE_SOURCE,
    }


def test_fallback_candidates_absent_or_empty_is_byte_identical(tmp_path):
    absent_config, legal = _fallback_config(tmp_path, fallback_candidates=None)
    absent_binding = load_knowledge_store_binding(absent_config, data_root=tmp_path)
    absent_router = build_knowledge_store_supply(
        absent_binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    absent_supply = absent_router.automatic_for_phase(
        "solve", _context(absent_binding, _artifact("s1", ("beta", "alpha", "gamma")))
    )

    empty_config, legal2 = _fallback_config(tmp_path, fallback_candidates=[])
    empty_binding = load_knowledge_store_binding(empty_config, data_root=tmp_path)
    empty_router = build_knowledge_store_supply(
        empty_binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal2,
    )
    empty_supply = empty_router.automatic_for_phase(
        "solve", _context(empty_binding, _artifact("s1", ("beta", "alpha", "gamma")))
    )

    assert absent_supply.fusion_decision.selected_value_ids == (
        empty_supply.fusion_decision.selected_value_ids
    )
    absent_audit = next(iter(absent_router.receipt["candidate_selections"].values()))
    empty_audit = next(iter(empty_router.receipt["candidate_selections"].values()))
    assert absent_audit == empty_audit
    assert "candidate_ids_without_fallback" not in absent_audit
    assert "fallback_candidates" not in absent_audit


def test_fallback_candidates_is_a_slurp_only_option():
    spec = CandidateSemanticSupplySpec(
        phase="solve", store_id="slot-contracts",
        provider="audio2tool-candidate-semantic-v1",
        rank_policy="saea-ranked-candidate-round-robin-v1",
        fuse_policy="saea-candidate-semantic-passthrough-v1",
        candidate_state_phase="hypotheses",
        max_candidates=1,
        max_values_per_candidate=1,
        max_total_values=1,
        fallback_candidates=("delta",),
    )
    with pytest.raises(CandidateSemanticSupplyError, match="SLURP-only"):
        spec.validate(_program())


def test_fallback_distinction_without_fallback_candidates_is_refused():
    spec = CandidateSemanticSupplySpec(
        phase="solve", store_id="slot-contracts",
        provider="slurp-candidate-semantic-v1",
        rank_policy="saea-ranked-candidate-round-robin-v1",
        fuse_policy="saea-candidate-semantic-passthrough-v1",
        candidate_state_phase="hypotheses",
        max_candidates=1,
        max_values_per_candidate=1,
        max_total_values=1,
        fallback_distinction="A distinction with no configured fallback id.",
    )
    with pytest.raises(CandidateSemanticSupplyError, match="fallback_distinction"):
        spec.validate(_program())


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_fallback_quirky_baseline_differs_from_the_anchor_only_by_the_option():
    anchor = json.loads(
        (REPO_ROOT / "configs" / "baseline"
         / "slurp-native-dual-store-train-fold-a-anchor-v1.json").read_text(encoding="utf-8")
    )
    fallback = json.loads(
        (REPO_ROOT / "configs" / "baseline"
         / "slurp-native-dual-store-train-fold-a-fallback-quirky-v1.json").read_text(
            encoding="utf-8"
        )
    )
    anchor_solve_spec = dict(
        anchor["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
    )
    fallback_solve_spec = dict(
        fallback["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solver"]
    )
    added = fallback_solve_spec.pop("fallback_candidates")
    assert added == ["general_quirky"]
    assert anchor_solve_spec == fallback_solve_spec

    anchor_fill_params = dict(anchor["phase_material"]["perception"]["fill_params"])
    fallback_fill_params = dict(fallback["phase_material"]["perception"]["fill_params"])
    added_fill = fallback_fill_params.pop("fallback_candidates")
    assert added_fill == ["general_quirky"]
    assert anchor_fill_params == fallback_fill_params

    # Every other top-level key, including every prepared/sealed asset
    # pointer and hash, is byte-identical -- unique identity fields and the
    # narrative note excepted.
    identity_keys = {"native_contact_fit", "what_this_is"}
    for key in set(anchor) - identity_keys - {"knowledge_stores", "phase_material"}:
        assert fallback[key] == anchor[key], key
    for phase in ("planner", "reviewer", "solver"):
        assert fallback["phase_material"][phase] == anchor["phase_material"][phase]
    for store in ("intent-boundaries",):
        assert fallback["knowledge_stores"][store] == anchor["knowledge_stores"][store]
    for key in ("release", "snapshot", "store_role"):
        assert (
            fallback["knowledge_stores"]["slot-contracts"][key]
            == anchor["knowledge_stores"]["slot-contracts"][key]
        )


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


def test_candidate_state_selection_default_is_single_and_not_serialized(tmp_path):
    config, legal = _config(tmp_path)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )

    serialized = router.receipt["candidate_supply"]["specs"][0]
    assert "candidate_state_selection" not in serialized
    duplicate = replace(
        _context(binding, _artifact("s1", ("alpha",))),
        agent_states=(
            _artifact("s1", ("alpha",), state_id="hypotheses:s1:first"),
            _artifact("s1", ("beta",), state_id="hypotheses:s1:second"),
        ),
    )
    with pytest.raises(CandidateSemanticSupplyError, match="exactly one source-bound"):
        router.automatic_for_phase("solve", duplicate)


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


def test_latest_candidate_state_supplies_only_new_cards_after_full_selection(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["candidate_state_selection"] = "latest"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    prior = _artifact(
        "s1", ("gamma",), state_id="z-hypotheses:s1:initial"
    )
    refreshed = _artifact(
        "s1", ("beta", "alpha"), state_id="a-hypotheses:s1:refresh"
    )
    visible = ("slot-contracts::slot-contract:alpha_one",)

    context = _latest_context(
        binding, (prior, refreshed), retrieved_value_ids=visible
    )
    supply = router.automatic_for_phase("solve", context)

    assert tuple(item.facet_id for item in supply.rank_result.candidates) == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
    )
    assert supply.fusion_decision.selected_value_ids == (
        "slot-contracts::slot-contract:beta_one",
    )
    next_state, transition = advance_phase_response_state(
        context=context,
        added_states=(),
        action_target_ref="synthetic-refresh",
        supply=supply,
    )
    assert next_state.retrieved_value_ids == (
        "slot-contracts::slot-contract:alpha_one",
        "slot-contracts::slot-contract:beta_one",
    )
    assert transition.new_value_ids == (
        "slot-contracts::slot-contract:beta_one",
    )
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["qualified_selected_value_ids"] == [
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
    ]
    assert audit["already_visible_value_ids"] == list(visible)
    assert audit["added_value_ids"] == [
        "slot-contracts::slot-contract:beta_one"
    ]
    assert audit["selected_source_state_id"] == refreshed.state_id
    assert audit["selected_source_state_sha256"] == refreshed.content_hash()
    assert audit["source_selection_policy"] == (
        "last-matching-state-in-query-order-v1"
    )
    assert router.receipt["candidate_supply"]["specs"][0][
        "candidate_state_selection"
    ] == "latest"


def test_latest_same_source_repeat_adds_no_cards(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["candidate_state_selection"] = "latest"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    state = _artifact("s1", ("beta",), state_id="hypotheses:s1:refresh")
    selected = ("slot-contracts::slot-contract:beta_one",)

    result = router.automatic_for_phase(
        "solve",
        _latest_context(binding, (state,), retrieved_value_ids=selected),
    )

    assert result is None
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["supply_disposition"] == "already-visible"
    assert audit["already_visible_value_ids"] == list(selected)
    assert audit["added_value_ids"] == []


def test_latest_accepts_one_fresh_staged_perception_state(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec.update(
        candidate_state_phase="perception", candidate_state_selection="latest"
    )
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding,
        program=_program("perception"),
        data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    context = _context(binding, _artifact("s1", ("beta",)))
    staged = _artifact(
        "s1",
        ("beta",),
        state_id="perception:s1:refresh",
        state_kind="phase:perception",
        source_query_state_sha256=context.query_state.content_hash(),
    )
    context = replace(
        context,
        agent_states=(staged,),
        prior_response_sha256s=(staged.source_response_sha256,),
    )

    supply = router.automatic_for_phase("solve", context)

    assert supply.fusion_decision.selected_value_ids == (
        "slot-contracts::slot-contract:beta_one",
    )
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["selected_source_state_id"] == staged.state_id


@pytest.mark.parametrize("failure", ["stale-query", "wrong-response"])
def test_latest_refuses_stale_or_wrong_response_staged_perception_state(
    tmp_path, failure
):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec.update(
        candidate_state_phase="perception", candidate_state_selection="latest"
    )
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding,
        program=_program("perception"),
        data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    context = _context(binding, _artifact("s1", ("alpha",)))
    source_query_hash = (
        SHA_B if failure == "stale-query" else context.query_state.content_hash()
    )
    staged = _artifact(
        "s1",
        ("alpha",),
        state_id="perception:s1:refresh",
        state_kind="phase:perception",
        source_query_state_sha256=source_query_hash,
    )
    final_response_hash = (
        SHA_A
        if failure == "wrong-response"
        else staged.source_response_sha256
    )
    context = replace(
        context,
        agent_states=(staged,),
        prior_response_sha256s=(final_response_hash,),
    )
    expected = "another QueryState" if failure == "stale-query" else "another final response"

    with pytest.raises(CandidateSemanticSupplyError, match=expected):
        router.automatic_for_phase("solve", context)


@pytest.mark.parametrize(
    "declared_ids",
    [
        ("a-hypotheses:s1:refresh", "z-hypotheses:s1:initial"),
        (),
    ],
)
def test_latest_candidate_state_refuses_out_of_order_or_missing_query_binding(
    tmp_path, declared_ids
):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["candidate_state_selection"] = "latest"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    states = (
        _artifact("s1", ("gamma",), state_id="z-hypotheses:s1:initial"),
        _artifact("s1", ("alpha",), state_id="a-hypotheses:s1:refresh"),
    )
    context = _latest_context(binding, states)
    context = replace(
        context,
        query_state=replace(context.query_state, agent_state_ids=declared_ids).validate(),
    )

    with pytest.raises(CandidateSemanticSupplyError, match="exactly match.*in order"):
        router.automatic_for_phase("solve", context)


def test_latest_candidate_state_refuses_duplicate_context_ids(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["candidate_state_selection"] = "latest"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    state = _artifact("s1", ("alpha",), state_id="hypotheses:s1:repeat")
    context = _latest_context(binding, (state,))
    context = replace(context, agent_states=(state, state))

    with pytest.raises(CandidateSemanticSupplyError, match="unique context state IDs"):
        router.automatic_for_phase("solve", context)


def test_latest_withhold_refuses_visible_selected_values(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec.update(candidate_state_selection="latest", supply_mode="withhold")
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    state = _artifact("s1", ("beta",), state_id="hypotheses:s1:refresh")
    context = _latest_context(
        binding,
        (state,),
        retrieved_value_ids=("slot-contracts::slot-contract:beta_one",),
    )

    with pytest.raises(CandidateSemanticSupplyError, match="contaminated control"):
        router.automatic_for_phase("solve", context)


def test_withheld_control_validates_and_ranks_without_exposing_knowledge(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["supply_mode"] = "withhold"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    context = _context(binding, _artifact("s1", ("beta", "alpha")))
    before = context.query_state.content_hash()
    assert router.automatic_for_phase("solve", context) is None
    assert context.query_state.content_hash() == before
    assert context.query_state.retrieved_value_ids == ()
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["candidate_ids"] == ["beta", "alpha"]
    assert audit["qualified_selected_value_ids"] == [
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
    ]
    assert audit["supply_disposition"] == "withheld"
    assert router.receipt["candidate_supply"]["specs"][0]["supply_mode"] == "withhold"
    with pytest.raises(CandidateSemanticSupplyError):
        router.automatic_for_phase("solve", _context(binding, _artifact("s2", ("illegal",)), "s2"))
    missing = replace(context, agent_states=())
    with pytest.raises(CandidateSemanticSupplyError, match="exactly one"):
        router.automatic_for_phase("solve", missing)


def test_withheld_control_refuses_already_visible_candidate_values(tmp_path):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec["supply_mode"] = "withhold"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
    )
    context = _context(binding, _artifact("s1", ("beta",)))
    context = replace(context, query_state=replace(
        context.query_state,
        retrieved_value_ids=("slot-contracts::slot-contract:beta_one",),
    ))
    with pytest.raises(CandidateSemanticSupplyError, match="contaminated control"):
        router.automatic_for_phase("solve", context)


@pytest.mark.parametrize("mode", [None, True, "", "unvalidated"])
def test_candidate_supply_refuses_unknown_mode(tmp_path, mode):
    config, legal = _config(tmp_path)
    config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]["supply_mode"] = mode
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    with pytest.raises(CandidateSemanticSupplyError, match="supply_mode"):
        build_knowledge_store_supply(
            binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
        )


@pytest.mark.parametrize("selection", [None, True, "", "first", "unvalidated"])
def test_candidate_supply_refuses_unknown_candidate_state_selection(
    tmp_path, selection
):
    config, legal = _config(tmp_path)
    config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"][
        "candidate_state_selection"
    ] = selection
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    with pytest.raises(CandidateSemanticSupplyError, match="candidate_state_selection"):
        build_knowledge_store_supply(
            binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal
        )


@pytest.mark.parametrize("mode", ["withhold", "provide"])
def test_bounded_projection_is_shared_by_treatment_and_control(tmp_path, mode):
    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec.update(
        compact_source_phase="hypotheses", supply_mode=mode,
        projection_policy="bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1",
    )
    source = _artifact("s1", ("beta", "alpha", "beta"))
    raw = json.dumps({"candidates": json.loads(source.content)["candidates"]})
    source = replace(
        source, content=raw,
        source_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
    )
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    supply = router.automatic_for_phase("solve", _context(binding, source))
    assert (supply is None) == (mode == "withhold")
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["candidate_ids"] == ["beta", "alpha"]
    assert audit["candidate_projection"]["original_text_sha256"] == source.source_response_sha256
    assert len(audit["candidate_projection"]["raw_positions"]) == 3
    assert source.content == raw
    assert router.receipt["candidate_supply"]["specs"][0]["projection_policy"] == spec["projection_policy"]


def test_configurable_projection_flows_five_raw_candidates_through_supply(tmp_path):
    inventory = ("alpha", "beta", "gamma", "delta", "epsilon")
    rows = tuple(_slot_row(f"{intent}_one", (intent,)) for intent in inventory)
    config, legal = _config(
        tmp_path, rows=rows, inventory=inventory, max_candidates=5
    )
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    spec.update(
        compact_source_phase="hypotheses",
        projection_policy=(
            "configurable-bounded-first-occurrence-distinct-"
            "slurp-intent-hypotheses-v1"
        ),
    )
    source = _artifact(
        "s1", ("alpha", "beta", "gamma", "delta", "epsilon")
    )
    raw = json.dumps({"candidates": json.loads(source.content)["candidates"]})
    source = replace(
        source,
        content=raw,
        source_response_sha256=hashlib.sha256(raw.encode()).hexdigest(),
    )
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path,
        legal_candidate_ids=legal,
    )
    supply = router.automatic_for_phase("solve", _context(binding, source))
    assert len(supply.fusion_decision.selected_value_ids) == 5
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["candidate_ids"] == list(inventory)
    assert audit["candidate_projection"]["projection_policy_id"] == (
        spec["projection_policy"]
    )

    spec["projection_policy"] = (
        "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
    )
    with pytest.raises(CandidateSemanticSupplyError, match="projection_policy"):
        build_knowledge_store_supply(
            load_knowledge_store_binding(config, data_root=tmp_path),
            program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
        )


@pytest.mark.parametrize("mode,expected", [
    ("single", "bdcc8387f6181d96ff4f3bba2a1591362bb2cca7fc1f06721068ceced9a1f7e7"),
    ("withhold", "0983a13f259df05a597895e3e86a52419299dfa6523ae5a8431f890447c62bde"),
    ("latest", "49d48c6fa82a2ce6dcc464b73a51fb01ddee56e5293bde68afb247bea3908925"),
])
def test_existing_slurp_receipt_identity_survives_shared_provider_extraction(tmp_path, mode, expected):
    # Golden hashes were measured from the unchanged a66aa023 source before
    # extracting the shared provider, including the existing synthetic sources.
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    config, legal = _config(tmp_path)
    spec = config["knowledge_stores"]["slot-contracts"]["candidate_supply"]["solve"]
    if mode == "withhold":
        spec["supply_mode"] = "withhold"
    elif mode == "latest":
        spec["candidate_state_selection"] = "latest"
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(
        binding, program=_program(), data_root=tmp_path, legal_candidate_ids=legal,
    )
    artifact = _artifact("s1", ("beta", "alpha", "gamma"))
    context = _context(binding, artifact)
    if mode == "latest":
        context = _latest_context(
            binding, (
                _artifact("s1", ("alpha",), state_id="old:hypotheses:s1"), artifact,
            ), retrieved_value_ids=("slot-contracts::slot-contract:alpha_one",),
        )
    router.automatic_for_phase("solve", context)
    assert content_hash(router.receipt) == expected
