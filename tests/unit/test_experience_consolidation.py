"""Exercise multi-round consolidation using the existing experience records."""
from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.rails.experience_memory import (
    Applicability, ExperienceRecord, ExperienceSource, SourceRef, ValidationBinding,
)
from speech_aware_evidence_acquisition.rails.experience_consolidation import (
    ConsolidationError, consolidate_experience_candidates, initialize_candidate_snapshot,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def record(record_id="proposal-a", guidance="Preserve supported repairs through delivery.",
           status="provisional", sample="train-001", support_role="train"):
    return ExperienceRecord.create(
        record_id=record_id, revision=1, kind="conditional-rule",
        train_construction_sha256="b"*64,
        source=ExperienceSource("train", sample, "1"*64, "2"*64, "3"*64, "4"*64),
        applicability=Applicability(
            ("slurp-slot-slu",), ("slots",), ("supply", "use"),
            ("signal:evidence-conflict",), (),
        ),
        diagnosis="A later role can undo a supported correction.",
        guidance=guidance, limitations=("Do not infer node-level causal credit.",),
        supporting_source_refs=(SourceRef("whole-system-terminal", "9"*64, support_role),),
        validation=ValidationBinding(status, "5"*64, "6"*64, "b"*64, "8"*64),
    )


def snapshot(records=()):
    return initialize_candidate_snapshot(
        memory_id="system-experience", train_construction_sha256="b"*64,
        expected_train_sample_ids=("train-001", "train-002"), records=records,
    )


def run(base, operations, proposals=None, round_id="round-1"):
    plan={"base_snapshot_sha256": base["content_sha256"], "operations": operations}
    return consolidate_experience_candidates(
        base, plan, proposals or {"p": record()}, round_id=round_id,
        source_bindings={
            "complete_system_feedback_sha256": "a"*64,
            "proposal_artifact_sha256": "c"*64,
            "consolidation_response_sha256": "d"*64,
        },
    )


def test_sparse_ids_and_delete_then_add_never_overwrite_or_reuse():
    original=snapshot((record("0", "Guidance zero"), record("2", "Guidance two")))
    old=copy.deepcopy(original)
    first=run(original, [{"operation":"ADD", "proposal_id":"p"}])
    assert first["status"] == "applied"
    candidate=first["snapshot"]
    added=first["applied_operations"][0]["new_record_id"]
    by_id={r["record_id"]: r for r in candidate["records"]}
    assert by_id["0"] == original["records"][0]
    assert by_id["2"] == original["records"][1]
    assert added not in {"0","2"}
    removed=run(candidate, [{"operation":"DELETE", "record_id":added}], round_id="round-2")
    final=run(removed["snapshot"], [{"operation":"ADD", "proposal_id":"p"}], round_id="round-3")
    second_id=final["applied_operations"][0]["new_record_id"]
    assert second_id != added
    assert {added, second_id, "0", "2"} == set(final["snapshot"]["issued_record_ids"])
    assert original == old
    assert first == run(original, [{"operation":"ADD", "proposal_id":"p"}])


def test_update_reuses_record_contract_and_retains_parent_bytes_and_source():
    base=snapshot((record("old"),))
    proposal=record("model-proposal", "Check conflicting evidence before final acceptance.")
    result=run(base, [{"operation":"UPDATE", "record_id":"old", "proposal_id":"p"}],
               {"p":proposal})
    assert result["status"] == "applied"
    restored=ExperienceRecord.from_json(result["snapshot"]["records"][0])
    assert restored.revision == 2 and restored.supersedes_record_id == "old"
    assert restored.record_id != "old"
    assert restored.validation == proposal.validation
    assert restored.validation.status == "provisional"
    assert restored.source == proposal.source
    assert restored.applicability == proposal.applicability
    assert base["records"][0] == record("old").as_json()
    assert result["snapshot"]["parent_snapshot_sha256"] == base["content_sha256"]
    assert result["runtime_authorized"] is False


@pytest.mark.parametrize("invalid", [
    {"operation":"UPDATE", "record_id":"missing", "proposal_id":"p"},
    {"operation":"DELETE", "record_id":"missing"},
    {"operation":"MERGE", "proposal_id":"p"},
    {"operation":"ADD", "proposal_id":"unknown"},
    {"operation":"ADD", "proposal_id":"p", "record_id":"model-assigned-id"},
    {"operation":"DELETE", "record_id":"old", "content":"not-needed"},
])
def test_bad_tail_rejects_whole_batch_and_preserves_raw_plan(invalid):
    base=snapshot((record("old", "Original"),))
    before=copy.deepcopy(base)
    operations=[{"operation":"ADD", "proposal_id":"p"}, invalid]
    result=run(base, operations)
    assert result["status"] == "rejected"
    assert result["snapshot"] is None and result["applied_operations"] == []
    assert result["plan"]["operations"] == operations
    assert result["error"] and result["failed_operation_index"] == 1
    assert base == before


def test_target_conflicts_and_duplicate_active_content_are_not_silently_resolved():
    base=snapshot((record("old", "Original"),))
    result=run(base, [
        {"operation":"UPDATE", "record_id":"old", "proposal_id":"p"},
        {"operation":"DELETE", "record_id":"old"},
    ])
    assert result["status"] == "rejected"
    result=run(base, [
        {"operation":"ADD", "proposal_id":"p"}, {"operation":"ADD", "proposal_id":"p"},
    ])
    assert result["status"] == "rejected" and "duplicate" in result["error"]


@pytest.mark.parametrize("proposal", [
    record(status="admitted"), record(sample="outside-roster"), record(support_role="test"),
])
def test_proposals_cannot_change_admission_or_construction_population(proposal):
    result=run(snapshot(), [{"operation":"ADD", "proposal_id":"p"}], {"p":proposal})
    assert result["status"] == "rejected" and result["snapshot"] is None


def test_empty_plan_is_explicit_unchanged_and_delete_all_is_allowed():
    base=snapshot((record("old"),))
    result=run(base, [])
    assert result["status"] == "unchanged" and result["snapshot"] == base
    assert result["applied_operations"] == []
    deleted=run(base, [{"operation":"DELETE", "record_id":"old"}])
    assert deleted["status"] == "applied" and deleted["snapshot"]["records"] == []
    assert deleted["snapshot"]["issued_record_ids"] == ["old"]
    result["snapshot"]["records"].clear()
    assert len(base["records"]) == 1


def test_stale_plan_and_corrupt_snapshot_fail_without_mutation():
    base=snapshot()
    bad=copy.deepcopy(base)
    bad["issued_record_ids"].append("tampered")
    with pytest.raises(ConsolidationError, match="fingerprint"):
        run(bad, [])
    result=consolidate_experience_candidates(
        base, {"base_snapshot_sha256":"0"*64, "operations":[]}, {},
        round_id="round-1",
        source_bindings={"complete_system_feedback_sha256":"a"*64,
                         "proposal_artifact_sha256":"c"*64,
                         "consolidation_response_sha256":"d"*64},
    )
    assert result["status"] == "rejected" and "snapshot" in result["error"]


def test_receipt_hash_binds_failed_plan_and_every_candidate():
    base=snapshot()
    result=run(base, [{"operation":"UNKNOWN"}])
    unsigned={k:v for k,v in result.items() if k != "content_sha256"}
    assert content_hash(unsigned) == result["content_sha256"]
    assert result["proposal_record_sha256s"] == {"p":record().record_sha256}
    assert result["source_bindings"]["complete_system_feedback_sha256"] == "a"*64


def test_revisions_keep_all_issued_ids_and_cannot_be_reimported_as_new_roots():
    base=snapshot((record("root"),))
    first=run(base, [{"operation":"UPDATE", "record_id":"root", "proposal_id":"p"}],
              {"p":record("draft-one", "First revised guidance")})
    record_one=ExperienceRecord.from_json(first["snapshot"]["records"][0])
    second=run(first["snapshot"],
               [{"operation":"UPDATE", "record_id":record_one.record_id, "proposal_id":"p"}],
               {"p":record("draft-two", "Second revised guidance")}, round_id="round-2")
    record_two=ExperienceRecord.from_json(second["snapshot"]["records"][0])
    assert record_two.revision == 3
    assert record_two.supersedes_record_id == record_one.record_id
    assert set(second["snapshot"]["issued_record_ids"]) == {
        "root", record_one.record_id, record_two.record_id,
    }
    with pytest.raises(ConsolidationError, match="initialize only root"):
        snapshot((record_two,))


def test_existing_runtime_catalog_does_not_admit_consolidated_candidates():
    from speech_aware_evidence_acquisition.rails.experience_memory import (
        ExperienceMemoryCatalog, ExperienceMemoryError,
    )
    result=run(snapshot(), [{"operation":"ADD", "proposal_id":"p"}])
    candidate=ExperienceRecord.from_json(result["snapshot"]["records"][0])
    with pytest.raises(ExperienceMemoryError, match="admitted"):
        ExperienceMemoryCatalog(
            "system-experience", 1, result["snapshot"]["content_sha256"],
            "b"*64, frozenset({"train-001","train-002"}), (candidate,),
        )


def test_unused_invalid_proposal_is_not_silently_dropped():
    result=run(snapshot(), [], {"p":record(), "bad":record(status="admitted")})
    assert result["status"] == "rejected"
    assert result["snapshot"] is None
    assert set(result["proposal_record_sha256s"]) == {"p", "bad"}


@pytest.mark.parametrize("operations", [None, ["invalid"], [{"operation":[]}], [{}]])
def test_malformed_model_plan_is_retained(operations):
    result=run(snapshot(), operations)
    assert result["status"] == "rejected"
    assert result["plan"]["operations"] == operations
