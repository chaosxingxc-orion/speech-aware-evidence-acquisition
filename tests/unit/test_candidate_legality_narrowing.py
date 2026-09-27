"""W1 (owner decision 164): a pinned intent -> slot-type legality table NARROWS the
slot-contract card route, never widens it, and changes nothing when absent."""

from __future__ import annotations

import hashlib
import itertools
import json

import pytest

from speech_aware_evidence_acquisition.rails.candidate_semantic_supply import (
    SLOT_LEGALITY_SCHEMA,
    CandidateSemanticSupplyError,
    load_sealed_slot_legality,
    max_candidate_selection_value_ids,
    narrow_candidate_index,
    validate_candidate_legality_source,
)
from speech_aware_evidence_acquisition.rails.controllers import PhaseProgram, PhaseSpec
from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact, QueryState
from speech_aware_evidence_acquisition.rails.knowledge_provider import select_candidate_semantic_values
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    build_knowledge_store_supply,
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.runner import AgentRuntimeContext
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    AuthoredSemanticKnowledgeSpec,
    build_slot_contract_snapshot,
)

SHA_A = "a" * 64
SHA_B = "b" * 64
INVENTORY = ("alpha", "beta", "gamma", "delta")


def _write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _slot_row(slot_id, intents):
    return {
        "slot_id": slot_id,
        "intent_bindings": [{"intent_id": i, "semantic_role": f"Role for {i}."} for i in intents],
        "extraction_cues": ["Extract only an explicitly supported mention."],
        "admissible_formats": ["Keep the spoken form."],
        "missing_behavior": "Omit the slot when speech provides no value.",
        "ambiguity_behavior": "Retain ambiguity supported by the speech.",
        "limitations": ["Observed intent bindings index guidance; they are not required fields."],
        "source_support": {"source_sample_ids": ["train-1"], "provenance_refs": [f"prepared-support://synthetic/{slot_id}"]},
    }


ROWS = (
    _slot_row("shared", ("alpha", "beta")),
    _slot_row("alpha_one", ("alpha",)),
    _slot_row("alpha_two", ("alpha",)),
    _slot_row("beta_one", ("beta",)),
    _slot_row("gamma_one", ("gamma",)),
)


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


def _legality(tmp_path, table, *, schema=SLOT_LEGALITY_SCHEMA):
    relpath = "prepared/LEGALITY/legality.json"
    sha = _write(tmp_path / relpath, {"schema": schema, "legal_slot_types": table})
    return {
        "kind": "sealed-intent-slot-legality",
        "relpath": relpath,
        "sha256": sha,
        "tool_contact_ledger_row": "SYNTHETIC-LEGALITY-ROW",
        "embedded_signal": "derived: synthetic",
    }


def _config(tmp_path, legality=None):
    snapshot = build_slot_contract_snapshot(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp", source_split_identity_hash=SHA_A, permitted_source_sample_ids=("train-1",),
        ),
        rows=ROWS,
    )
    source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": snapshot.builder_policy_id,
        "source_split_identity_hash": SHA_A,
        "rows": list(ROWS),
    }
    source_relpath = "knowledge/slot-contracts/source.json"
    source_sha = _write(tmp_path / source_relpath, source)
    snapshot_relpath = "knowledge/slot-contracts/snapshot.json"
    (tmp_path / snapshot_relpath).write_text(json.dumps(snapshot.frozen_json()), encoding="utf-8")
    release_relpath = "knowledge/slot-contracts/release.json"
    release_sha = _write(tmp_path / release_relpath, {
        "schema": "saea-knowledge-store-release-v1", "store_id": "slot-contracts", "store_role": "slot-contracts",
        "snapshot_sha256": snapshot.content_hash(), "source_split_identity_hash": SHA_A,
        "builder_policy_id": snapshot.builder_policy_id, "source": {"relpath": source_relpath, "sha256": source_sha},
    })
    spec = {
        "provider": "slurp-candidate-semantic-v1",
        "rank_policy": "saea-ranked-candidate-round-robin-v1",
        "fuse_policy": "saea-candidate-semantic-passthrough-v1",
        "candidate_state_phase": "hypotheses",
        "max_candidates": 3,
        "max_values_per_candidate": 2,
        "max_total_values": 6,
    }
    if legality is not None:
        spec["candidate_legality_source"] = legality
    return {"knowledge_stores": {"slot-contracts": {
        "store_role": "slot-contracts",
        "snapshot": {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()},
        "release": {"relpath": release_relpath, "sha256": release_sha},
        "candidate_supply": {"solve": spec},
    }}}


def _artifact(sample_id, intents):
    content = json.dumps({
        "schema": "saea-slurp-intent-hypotheses-v1",
        "semantics": "ranked-mutually-exclusive-intent-alternatives",
        "sample_id": sample_id,
        "candidates": [
            {"intent_id": i, "distinction": f"Evidence for {i}.", "evidence_refs": ["speech"], "unresolved_fields": []}
            for i in intents
        ],
    }, sort_keys=True, separators=(",", ":"))
    return AgentStateArtifact(
        state_id=f"hypotheses:{sample_id}", state_kind="phase:hypotheses", content=content,
        source_query_state_sha256=SHA_B, source_response_sha256=hashlib.sha256(content.encode()).hexdigest(),
        producer_policy_id="synthetic-hypothesis-proposer-v1", cited_value_ids=(),
    ).validate()


def _context(binding, artifact, sample_id="s1"):
    query = QueryState(
        query_id=f"query:{sample_id}", query_sample_id=sample_id, speech_packet_id=f"packet:{sample_id}",
        speech_packet_sha256=SHA_B, use_split_identity_hash=SHA_A, query_source="speech_features",
    ).validate()
    return AgentRuntimeContext(
        sample_id=sample_id, knowledge_snapshot_sha256=binding.binding_sha256,
        catalog_facet_ids=tuple(f.facet_id for f in binding.composite_snapshot.facets),
        catalog_value_ids=tuple(v.value_id for v in binding.composite_snapshot.values),
        query_state=query, task_contract="synthetic full legal label and type inventory",
        agent_states=(artifact,), prior_response_sha256s=(artifact.source_response_sha256,), contact_index=1,
    )


def _select(tmp_path, legality, intents):
    config = _config(tmp_path, legality)
    binding = load_knowledge_store_binding(config, data_root=tmp_path)
    router = build_knowledge_store_supply(binding, program=_program(), data_root=tmp_path, legal_candidate_ids=INVENTORY)
    supply = router.automatic_for_phase("solve", _context(binding, _artifact("s1", intents)))
    return supply, router


def test_absent_legality_keeps_the_authored_selection_and_receipt(tmp_path):
    supply, router = _select(tmp_path, None, ("beta", "alpha", "gamma"))
    assert supply.fusion_decision.selected_value_ids == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_one",
        "slot-contracts::slot-contract:gamma_one",
        "slot-contracts::slot-contract:shared",
        "slot-contracts::slot-contract:alpha_two",
    )
    assert all("candidate_legality_source" not in spec for spec in router.receipt["candidate_supply"]["specs"])


def test_legality_narrows_the_route_and_is_recorded(tmp_path):
    legality = _legality(tmp_path, {"alpha": ["alpha_two"], "beta": ["beta_one", "shared"]})
    supply, router = _select(tmp_path, legality, ("beta", "alpha", "gamma"))
    assert supply.fusion_decision.selected_value_ids == (
        "slot-contracts::slot-contract:beta_one",
        "slot-contracts::slot-contract:alpha_two",
        "slot-contracts::slot-contract:shared",
    )
    (spec,) = router.receipt["candidate_supply"]["specs"]
    assert spec["candidate_legality_source"] == legality


def test_a_row_whose_candidates_carry_no_legal_type_gets_no_card(tmp_path):
    legality = _legality(tmp_path, {"alpha": ["alpha_two"]})
    supply, router = _select(tmp_path, legality, ("gamma",))
    assert supply is None
    audit = next(iter(router.receipt["candidate_selections"].values()))
    assert audit["supply_disposition"] == "no-mapping"


def test_a_table_that_adds_a_binding_is_refused(tmp_path):
    legality = _legality(tmp_path, {"gamma": ["alpha_one"]})
    with pytest.raises(CandidateSemanticSupplyError, match="may only narrow"):
        _select(tmp_path, legality, ("gamma",))


def test_a_table_outside_the_inventory_is_refused():
    with pytest.raises(CandidateSemanticSupplyError, match="outside the legal inventory"):
        narrow_candidate_index({"alpha": ("slot-contract:a",)}, {"omega": frozenset({"a"})}, legal_candidate_ids=("alpha",))


def test_a_changed_table_is_refused_by_its_pin(tmp_path):
    legality = _legality(tmp_path, {"alpha": ["alpha_two"]})
    (tmp_path / legality["relpath"]).write_bytes(b'{"schema":"x"}')
    with pytest.raises(CandidateSemanticSupplyError, match="SHA-256 mismatch"):
        load_sealed_slot_legality(legality, tmp_path)


def test_the_table_schema_and_ordering_are_enforced(tmp_path):
    with pytest.raises(CandidateSemanticSupplyError, match="schema"):
        load_sealed_slot_legality(_legality(tmp_path, {"alpha": ["alpha_two"]}, schema="other"), tmp_path)
    with pytest.raises(CandidateSemanticSupplyError, match="sorted unique"):
        load_sealed_slot_legality(_legality(tmp_path, {"alpha": ["b", "a"]}), tmp_path)


@pytest.mark.parametrize("mutation", [
    {"kind": "sealed-agreement"},
    {"relpath": "../escape.json"},
    {"sha256": "A" * 64},
    {"tool_contact_ledger_row": " "},
])
def test_the_source_declaration_is_exact(mutation):
    source = {
        "kind": "sealed-intent-slot-legality", "relpath": "prepared/x/legality.json", "sha256": "a" * 64,
        "tool_contact_ledger_row": "ROW", "embedded_signal": "derived",
    }
    validate_candidate_legality_source(source)
    with pytest.raises(CandidateSemanticSupplyError):
        validate_candidate_legality_source({**source, **mutation})
    extra = {**source, "extra": 1}
    with pytest.raises(CandidateSemanticSupplyError):
        validate_candidate_legality_source(extra)


def test_the_static_bound_covers_every_real_selection():
    index = {
        "alpha": ("slot-contract:a", "slot-contract:b", "slot-contract:c"),
        "beta": ("slot-contract:b", "slot-contract:d"),
        "gamma": ("slot-contract:e",),
        "delta": ("slot-contract:f", "slot-contract:g"),
    }
    weight = {f"slot-contract:{c}": w for c, w in zip("abcdefg", (50, 40, 30, 90, 10, 70, 60), strict=True)}
    bound = max_candidate_selection_value_ids(index, weight=weight, max_candidates=3, max_total_values=4)
    bound_weight = sum(weight[v] for v in bound)
    assert len(bound) <= 4
    for width in (1, 2, 3):
        for ordered in itertools.permutations(sorted(index), width):
            selected, _ = select_candidate_semantic_values(ordered, index, max_values_per_candidate=2, max_total_values=4)
            assert sum(weight[v] for v in selected) <= bound_weight
