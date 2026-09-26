"""Cumulative exposure grows without rebasing immutable experience provenance."""
import copy
from dataclasses import replace

import pytest
from test_experience_consolidation import record, snapshot
from speech_aware_evidence_acquisition.rails import experience_consolidation as module
from speech_aware_evidence_acquisition.rails.hashing import content_hash


def extend(base, ids=("train-003",), **changes):
    kwargs = dict(round_construction_sha256="c"*64, round_sample_ids=ids,
                  cumulative_construction_sha256="d"*64,
                  cumulative_sample_ids=sorted(set(base["train_sample_ids"]) | set(ids)))
    kwargs.update(changes)
    return module.extend_candidate_construction(base, **kwargs)


def test_new_cohort_extends_exposure_without_rewriting_old_experience():
    base = snapshot((record("old"),))
    before = copy.deepcopy(base)
    expanded = extend(base)
    assert base == before and expanded["records"] == base["records"]
    assert expanded["schema"] == module.SCOPED_SNAPSHOT_SCHEMA
    assert expanded["train_sample_ids"] == ["train-001", "train-002", "train-003"]
    assert expanded["construction_scopes"]["b"*64] == base["train_sample_ids"]
    assert expanded["parent_snapshot_sha256"] == base["content_sha256"]
    assert module._load_snapshot(expanded)[0] == record("old")


@pytest.mark.parametrize("change,match", [
    ({"round_sample_ids": ["train-001"]}, "overlap"),
    ({"cumulative_sample_ids": ["train-001", "train-003"]}, "union"),
    ({"cumulative_sample_ids": ["train-001", "train-002", "train-003", "unseen"]}, "union"),
    ({"cumulative_construction_sha256": "b"*64}, "scope"),
    ({"round_sample_ids": []}, "empty"),
    ({"round_sample_ids": ["train-003", "train-003"]}, "duplicat"),
])
def test_false_exposure_rebasing_is_rejected(change, match):
    with pytest.raises(module.ConsolidationError, match=match):
        extend(snapshot(), **change)


def test_old_and_new_sources_can_coexist_through_atomic_update():
    base = snapshot((record("old"),))
    expanded = extend(base)
    new = record("new", sample="train-003", guidance="Check evidence before retaining a correction.")
    new = replace(new, train_construction_sha256="d"*64,
                  validation=replace(new.validation, roster_sha256="d"*64))
    new = replace(new, record_sha256=content_hash(new.unsigned_json()))
    result = module.consolidate_experience_candidates(expanded,
        {"base_snapshot_sha256": expanded["content_sha256"],
         "operations": [{"operation": "ADD", "proposal_id": "new"}]}, {"new": new},
        round_id="round-two", source_bindings={"complete_system_feedback_sha256": "e"*64,
        "proposal_artifact_sha256": "f"*64, "consolidation_response_sha256": "a"*64})
    assert result["status"] == "applied"
    rows = module._load_snapshot(result["snapshot"])
    assert {r.train_construction_sha256 for r in rows} == {"b"*64, "d"*64}
    assert next(r for r in rows if r.record_id == "old") == record("old")
    third = extend(result["snapshot"], ("train-004",), round_construction_sha256="e"*64,
                   cumulative_construction_sha256="f"*64)
    assert len(third["train_sample_ids"]) == 4 and len(third["construction_scopes"]) == 5
    with pytest.raises(module.ConsolidationError, match="overlap"):
        extend(third, ("train-001",))


def test_unknown_record_scope_and_tampered_scope_membership_are_rejected():
    expanded = extend(snapshot((record("old"),)))
    expanded["construction_scopes"]["b"*64] = ["train-003"]
    expanded.pop("content_sha256")
    expanded["content_sha256"] = content_hash(expanded)
    with pytest.raises(module.ConsolidationError, match="source"):
        module._load_snapshot(expanded)
