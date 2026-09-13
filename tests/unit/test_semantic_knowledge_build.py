from __future__ import annotations

from dataclasses import replace
import hashlib
import json

import pytest

from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_BUILDERS
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_provider import KbFacetProvider
from speech_aware_evidence_acquisition.rails import knowledge_build as _registrations  # noqa: F401
from speech_aware_evidence_acquisition.rails.knowledge_stores import load_knowledge_store_binding
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    INTENT_BOUNDARY_BUILD_POLICY_ID,
    SLOT_CONTRACT_BUILD_POLICY_ID,
    AuthoredSemanticKnowledgeSpec,
    build_intent_boundary_snapshot,
    build_slot_contract_snapshot,
)

SHA = "1" * 64


def _spec(**changes):
    return replace(
        AuthoredSemanticKnowledgeSpec(
            carrier_lock_key="slurp",
            source_split_identity_hash=SHA,
            permitted_source_sample_ids=("train-1", "train-2"),
        ),
        **changes,
    )


def _support(sample_id):
    return {
        "source_sample_ids": [sample_id],
        "provenance_refs": [f"governed-train:row={sample_id}", "author:review-v1"],
    }


def _intent(intent_id="calendar_set", sample_id="train-1"):
    return {
        "intent_id": intent_id,
        "activation_boundary": [
            "The speaker asks to create a new calendar entry.",
            "A future event and its scheduling action are both present.",
        ],
        "confusable_exclusions": [{
            "neighboring_intent_id": "calendar_query",
            "distinction": "A request to inspect an existing event is not creation.",
        }],
        "uncertainty_behavior": "Keep both candidates when the operation is unclear.",
        "limitations": ["This boundary does not determine any slot value."],
        "source_support": _support(sample_id),
    }


def _slot(slot_id="event_time", sample_id="train-2"):
    return {
        "slot_id": slot_id,
        "intent_bindings": [
            {"intent_id": "calendar_set", "semantic_role": "The time assigned to the new event."},
            {"intent_id": "calendar_query", "semantic_role": "The time constraint used to find an event."},
        ],
        "extraction_cues": ["Use the time expression attached to the event."],
        "admissible_formats": ["A normalized time or a bounded time interval."],
        "missing_behavior": "Leave the slot absent when no time is expressed.",
        "ambiguity_behavior": "Retain the ambiguity when two times have equal support.",
        "limitations": ["Do not invent a default time."],
        "source_support": _support(sample_id),
    }


def test_intent_builder_emits_source_bound_boundary_value_without_target_examples():
    snapshot = build_intent_boundary_snapshot(
        _spec(permitted_source_sample_ids=("train-1",)), rows=(_intent(),)
    )
    value = snapshot.values[0]
    assert snapshot.builder_policy_id == INTENT_BOUNDARY_BUILD_POLICY_ID
    assert snapshot.source_sample_ids == ("train-1",)
    assert snapshot.facets[0].dimension == "intent-boundary"
    assert value.value_id == "intent-boundary:calendar_set"
    assert value.task_target is None and value.prior_score is None
    assert "Activation boundary" in value.content and "calendar_query" in value.content
    assert "train-1" not in value.content
    assert value.provenance_refs == ("author:review-v1", "governed-train:row=train-1")


def test_slot_builder_preserves_roles_formats_and_missing_ambiguity_contracts():
    snapshot = build_slot_contract_snapshot(
        _spec(permitted_source_sample_ids=("train-2",)), rows=(_slot(),)
    )
    value = snapshot.values[0]
    assert snapshot.builder_policy_id == SLOT_CONTRACT_BUILD_POLICY_ID
    assert snapshot.facets[0].dimension == "slot-contract"
    assert value.value_id == "slot-contract:event_time"
    assert "calendar_set: The time assigned" in value.content
    assert "Admissible formats" in value.content
    assert "Leave the slot absent" in value.content
    assert "Retain the ambiguity" in value.content
    assert "train-2" not in value.content


@pytest.mark.parametrize(
    ("builder", "row", "missing"),
    [
        (build_intent_boundary_snapshot, _intent(), "activation_boundary"),
        (build_slot_contract_snapshot, _slot(), "missing_behavior"),
        (build_intent_boundary_snapshot, _intent(), "source_support"),
    ],
)
def test_builders_refuse_missing_authored_fields(builder, row, missing):
    with pytest.raises(RailsError, match="fields"):
        builder(_spec(), rows=({k: v for k, v in row.items() if k != missing},))


@pytest.mark.parametrize("field", ["raw_train_examples", "reference_text", "gold_label"])
def test_builders_refuse_unregistered_gold_or_example_fields(field):
    with pytest.raises(RailsError, match="fields"):
        build_intent_boundary_snapshot(_spec(), rows=({**_intent(), field: ["forbidden"]},))


def test_source_support_must_equal_permitted_roster_and_avoid_forbidden_ids():
    with pytest.raises(RailsError, match="permitted construction roster"):
        build_intent_boundary_snapshot(_spec(), rows=(_intent(),))
    with pytest.raises(RailsError, match="forbidden"):
        build_intent_boundary_snapshot(
            _spec(permitted_source_sample_ids=("train-1",)),
            rows=(_intent(),),
            forbidden_sample_ids=frozenset({"train-1"}),
        )


def test_non_build_partition_and_duplicate_semantic_ids_are_refused():
    with pytest.raises(RailsError, match="source_partition_role"):
        build_intent_boundary_snapshot(
            _spec(source_partition_role="dev", permitted_source_sample_ids=("train-1",)),
            rows=(_intent(),),
        )
    with pytest.raises(RailsError, match="duplicate intent_id"):
        build_intent_boundary_snapshot(
            _spec(permitted_source_sample_ids=("train-1",)), rows=(_intent(), _intent())
        )


def test_registered_provider_builds_both_snapshot_kinds():
    ip = KbFacetProvider(build_spec=_spec(permitted_source_sample_ids=("train-1",)))
    intent = ip.build((_intent(),), policy_id=INTENT_BOUNDARY_BUILD_POLICY_ID)
    sp = KbFacetProvider(build_spec=_spec(permitted_source_sample_ids=("train-2",)))
    slot = sp.build((_slot(),), policy_id=SLOT_CONTRACT_BUILD_POLICY_ID)
    assert KNOWLEDGE_BUILDERS.resolve(INTENT_BOUNDARY_BUILD_POLICY_ID) is build_intent_boundary_snapshot
    assert KNOWLEDGE_BUILDERS.resolve(SLOT_CONTRACT_BUILD_POLICY_ID) is build_slot_contract_snapshot
    assert ip.receipt()["snapshot_sha256"] == intent.content_hash()
    assert sp.receipt()["snapshot_sha256"] == slot.content_hash()


def _write(path, document):
    raw = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def test_snapshots_flow_through_existing_independent_release_loader(tmp_path):
    snapshots = {
        "intent-boundaries": build_intent_boundary_snapshot(
            _spec(permitted_source_sample_ids=("train-1",)), rows=(_intent(),)
        ),
        "slot-contracts": build_slot_contract_snapshot(
            _spec(permitted_source_sample_ids=("train-2",)), rows=(_slot(),)
        ),
    }
    stores = {}
    for store_id, snapshot in snapshots.items():
        source_relpath = f"knowledge/{store_id}/source.json"
        source_sha = _write(tmp_path / source_relpath, {"source_ids": snapshot.source_sample_ids})
        snapshot_relpath = f"knowledge/{store_id}/snapshot.json"
        snapshot_path = tmp_path / snapshot_relpath
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(json.dumps(snapshot.frozen_json()), encoding="utf-8")
        release_relpath = f"knowledge/{store_id}/release.json"
        release_sha = _write(tmp_path / release_relpath, {
            "schema": "saea-knowledge-store-release-v1",
            "store_id": store_id,
            "store_role": store_id,
            "snapshot_sha256": snapshot.content_hash(),
            "source_split_identity_hash": snapshot.source_split_identity_hash,
            "builder_policy_id": snapshot.builder_policy_id,
            "source": {"relpath": source_relpath, "sha256": source_sha},
        })
        stores[store_id] = {
            "store_role": store_id,
            "snapshot": {"relpath": snapshot_relpath, "sha256": snapshot.content_hash()},
            "release": {"relpath": release_relpath, "sha256": release_sha},
        }
    binding = load_knowledge_store_binding({"knowledge_stores": stores}, data_root=tmp_path)
    assert binding.store_ids == ("intent-boundaries", "slot-contracts")
    assert binding.snapshot_for("intent-boundaries").values[0].content == snapshots["intent-boundaries"].values[0].content
    assert binding.snapshot_for("slot-contracts").builder_policy_id == SLOT_CONTRACT_BUILD_POLICY_ID
