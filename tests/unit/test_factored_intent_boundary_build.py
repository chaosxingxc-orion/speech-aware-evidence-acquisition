from __future__ import annotations

import hashlib

import pytest

from speech_aware_evidence_acquisition.core.base import KNOWLEDGE_BUILDERS
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.semantic_knowledge_preparation import (
    prepare_semantic_knowledge_store,
)
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash
from speech_aware_evidence_acquisition.rails import knowledge_build as _registrations  # noqa: F401
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.kb_policy import (
    FuseKnobs,
    fuse_associated_values_factory,
)
from speech_aware_evidence_acquisition.rails.knowledge import (
    QueryState,
    RankedFacet,
    RankResult,
)
from speech_aware_evidence_acquisition.rails.knowledge_stores import (
    load_knowledge_store_binding,
)
from speech_aware_evidence_acquisition.rails.semantic_knowledge_build import (
    FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID,
    SHARED_INTENT_GUIDANCE_VALUE_ID,
    AuthoredSemanticKnowledgeSpec,
    build_factored_intent_boundary_snapshot,
    build_intent_boundary_snapshot,
)

SPLIT_SHA256 = "1" * 64
SPEECH_SHA256 = "2" * 64
COMMON_UNCERTAINTY = "Preserve both candidates when the operation is unclear."
COMMON_LIMITATION = "This guidance does not determine slot values."


def _row(intent_id: str, sample_id: str, neighbor: str, *, special: str | None = None):
    limitations = [COMMON_LIMITATION]
    if special is not None:
        limitations.append(special)
    return {
        "intent_id": intent_id,
        "activation_boundary": [f"The request activates {intent_id}."],
        "confusable_exclusions": [{
            "neighboring_intent_id": neighbor,
            "distinction": "The requested operation differs.",
        }],
        "uncertainty_behavior": COMMON_UNCERTAINTY,
        "limitations": limitations,
        "source_support": {
            "source_sample_ids": [sample_id],
            "provenance_refs": [f"synthetic:{sample_id}"],
        },
    }


def _rows():
    return (
        _row("intent_one", "train-1", "intent_two"),
        _row(
            "intent_two",
            "train-2",
            "intent_one",
            special="This intent retains one special limitation.",
        ),
    )


def _spec(split_sha256: str = SPLIT_SHA256):
    return AuthoredSemanticKnowledgeSpec(
        carrier_lock_key="slurp",
        source_split_identity_hash=split_sha256,
        permitted_source_sample_ids=("train-1", "train-2"),
    )


def test_factored_builder_preserves_original_bindings_and_is_order_invariant():
    rows = _rows()
    original = build_intent_boundary_snapshot(_spec(), rows=rows)
    factored = build_factored_intent_boundary_snapshot(_spec(), rows=rows)
    reversed_factored = build_factored_intent_boundary_snapshot(
        _spec(), rows=tuple(reversed(rows))
    )

    assert factored.builder_policy_id == FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID
    assert factored.content_hash() != original.content_hash()
    assert factored.facets == original.facets
    assert reversed_factored.frozen_json() == factored.frozen_json()
    originals = {value.value_id: value for value in original.values}
    values = {value.value_id: value for value in factored.values}
    for value_id, before in originals.items():
        after = values[value_id]
        assert after.associated_facet_ids == before.associated_facet_ids
        assert after.source_sample_ids == before.source_sample_ids
        assert after.provenance_refs == before.provenance_refs
        assert after.task_target == before.task_target
        assert after.prior_score == before.prior_score
        assert COMMON_UNCERTAINTY not in after.content
        assert COMMON_LIMITATION not in after.content
    assert "Limitations:" not in values["intent-boundary:intent_one"].content
    assert values["intent-boundary:intent_two"].content.endswith(
        "Limitations:\n- This intent retains one special limitation."
    )
    shared = values[SHARED_INTENT_GUIDANCE_VALUE_ID]
    assert shared.content == (
        "Shared guidance for all intent-boundary values in this store.\n"
        f"Uncertainty behavior: {COMMON_UNCERTAINTY}\n"
        f"Limitations:\n- {COMMON_LIMITATION}"
    )
    assert shared.associated_facet_ids == tuple(
        facet.facet_id for facet in original.facets
    )
    assert shared.source_sample_ids == original.source_sample_ids
    assert shared.provenance_refs == ("synthetic:train-1", "synthetic:train-2")
    assert shared.task_target is None and shared.prior_score is None
    assert build_intent_boundary_snapshot(_spec(), rows=rows) == original
    assert (
        KNOWLEDGE_BUILDERS.resolve(FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID)
        is build_factored_intent_boundary_snapshot
    )


@pytest.mark.parametrize(
    "defect", ["one-row", "uncertainty", "limitation", "collision", "ambiguous"]
)
def test_factored_builder_refuses_invalid_or_ambiguous_factoring(defect):
    rows = list(_rows())
    spec = _spec()
    if defect == "one-row":
        rows = rows[:1]
        spec = AuthoredSemanticKnowledgeSpec(
            "slurp", SPLIT_SHA256, ("train-1",)
        )
    elif defect == "uncertainty":
        rows[1]["uncertainty_behavior"] = "Use a different uncertainty rule."
    elif defect == "limitation":
        rows[1]["limitations"] = ["Use a different leading limitation."]
    elif defect == "collision":
        rows[1]["intent_id"] = "shared-guidance"
    else:
        rows[0]["activation_boundary"][0] += (
            f"\nUncertainty behavior: {COMMON_UNCERTAINTY}"
            f"\nLimitations:\n- {COMMON_LIMITATION}"
        )

    with pytest.raises(RailsError, match="factored intent"):
        build_factored_intent_boundary_snapshot(spec, rows=rows)


def test_associated_fuser_returns_each_intent_with_one_shared_value_or_empty():
    snapshot = build_factored_intent_boundary_snapshot(_spec(), rows=_rows())
    query = QueryState(
        query_id="query-factored",
        query_sample_id="dev:factored",
        speech_packet_id="packet-factored",
        speech_packet_sha256=SPEECH_SHA256,
        use_split_identity_hash=SPLIT_SHA256,
    ).validate()
    fuser = fuse_associated_values_factory(
        FuseKnobs(tau=0.0, m=2, c=2, top_l=3)
    )
    for intent_id in ("intent_one", "intent_two"):
        facet_id = f"intent-boundary:{intent_id}"
        rank = RankResult(
            snapshot.content_hash(),
            query.content_hash(),
            "synthetic-rank-v1",
            (RankedFacet(facet_id, 0.9),),
        ).validate()
        selected = fuser(
            snapshot=snapshot,
            snapshot_sha256=snapshot.content_hash(),
            query_state=query,
            rank_result=rank,
            recall_scores={facet_id: {"intent-boundary": 0.9}},
        )
        assert selected.selected_value_ids == (
            facet_id,
            SHARED_INTENT_GUIDANCE_VALUE_ID,
        )
        assert selected.supporting_facet_ids == (facet_id,)
        empty = fuser(
            snapshot=snapshot,
            snapshot_sha256=snapshot.content_hash(),
            query_state=query,
            rank_result=rank,
            recall_scores={},
        )
        assert empty.selected_value_ids == ()
        assert empty.supporting_facet_ids == ()


def _write(path, document, root):
    raw = canonical_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return {
        "relpath": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _roster(ids, roster_id):
    return {
        "schema": "saea-roster-receipt-v1",
        "roster_id": roster_id,
        "carrier_lock_key": "slurp",
        "split_role": "discovery",
        "roster_role": "construction",
        "items": [{"sample_id": item, "stratum": "synthetic"} for item in ids],
        "split_identity_hash": split_identity_hash(prefixed("slurp", ids)),
    }


def test_factored_policy_prepares_releases_and_loads_through_shared_entry(tmp_path):
    repo_root, data_root = tmp_path / "repo", tmp_path / "data"
    repo_root.mkdir()
    data_root.mkdir()
    ids = ("train-1", "train-2")
    identity = split_identity_hash(prefixed("slurp", ids))
    source = {
        "schema": "saea-authored-semantic-knowledge-source-v1",
        "builder_policy_id": FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID,
        "source_split_identity_hash": identity,
        "rows": _rows(),
    }
    registration = {
        "schema": "saea-authored-semantic-knowledge-preparation-v1",
        "registration_id": "SYNTHETIC-FACTORED-INTENT-PREP-V1",
        "carrier_lock_key": "slurp",
        "source_partition_role": "train",
        "source_split_identity_hash": identity,
        "builder_policy_id": FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID,
        "store_id": "intent-boundaries",
        "store_role": "intent-boundaries",
        "authored_source": _write(data_root / "authored.json", source, data_root),
        "construction_scope": _write(
            repo_root / "scope.json", _roster(ids, "scope"), repo_root
        ),
        "permitted_roster": _write(
            repo_root / "support.json", _roster(ids, "support"), repo_root
        ),
        "forbidden_rosters": [
            _write(
                repo_root / "forbidden.json",
                _roster(("forbidden-1",), "forbidden"),
                repo_root,
            )
        ],
        "output_namespace": "knowledge/semantic/intent-boundaries-factored-v1",
    }
    registration_path = repo_root / "registration.json"
    registration_path.write_bytes(canonical_bytes(registration))

    result = prepare_semantic_knowledge_store(
        registration_path, repo_root=repo_root, data_root=data_root
    )

    assert result["cache"] == "cold"
    assert result["completion"]["contacts"] == {"model": 0, "tool": 0, "scorer": 0}
    binding = load_knowledge_store_binding(
        {"knowledge_stores": {"intent-boundaries": {
            "store_role": "intent-boundaries",
            "snapshot": result["completion"]["snapshot"],
            "release": result["completion"]["release"],
        }}},
        data_root=data_root,
    )
    snapshot = binding.snapshot_for("intent-boundaries")
    assert snapshot.builder_policy_id == FACTORED_INTENT_BOUNDARY_BUILD_POLICY_ID
    assert len(snapshot.facets) == 2 and len(snapshot.values) == 3
