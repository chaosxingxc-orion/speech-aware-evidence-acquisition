from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.experience_memory import (
    Applicability,
    ExperienceMemoryError,
    ExperienceRecord,
    ExperienceSource,
    SourceRef,
    ValidationBinding,
    load_experience_memory_manifest,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(*, role: str = "train", sample_id: str = "train-001") -> ExperienceSource:
    return ExperienceSource(
        partition_role=role,
        source_sample_id=sample_id,
        trajectory_sha256="1" * 64,
        action_sha256="2" * 64,
        response_sha256="3" * 64,
        outcome_sha256="4" * 64,
    )


def _validation(*, status: str = "admitted") -> ValidationBinding:
    return ValidationBinding(
        status=status,
        decision_sha256="5" * 64,
        protocol_sha256="6" * 64,
        roster_sha256="7" * 64,
        result_sha256="8" * 64,
    )


def _record(
    record_id: str = "repair-after-conflict",
    *,
    kind: str = "conditional-rule",
    source: ExperienceSource | None = None,
    task_ids: tuple[str, ...] = ("slurp-slot-slu",),
    phases: tuple[str, ...] = ("slots",),
    components: tuple[str, ...] = ("supply", "use"),
    required: tuple[str, ...] = ("signal:evidence-conflict",),
    excluded: tuple[str, ...] = ("signal:audio-corrupt",),
    supporting: tuple[SourceRef, ...] = (SourceRef("train-case-helpful", "9" * 64),),
    contradicting: tuple[SourceRef, ...] = (SourceRef("train-case-harmful", "a" * 64),),
    validation: ValidationBinding | None = None,
    revision: int = 1,
    supersedes: str | None = None,
    superseded_by: str | None = None,
) -> ExperienceRecord:
    return ExperienceRecord.create(
        record_id=record_id,
        revision=revision,
        kind=kind,
        train_construction_sha256="b" * 64,
        source=source or _source(),
        applicability=Applicability(
            task_ids=task_ids,
            phases=phases,
            component_tags=components,
            required_conditions=required,
            excluded_conditions=excluded,
        ),
        diagnosis="Retrieved evidence conflicts with the current hypothesis.",
        guidance="Inspect the conflicting source before revising the answer.",
        limitations=("Do not copy a value unsupported by the query.",),
        supporting_source_refs=supporting,
        contradicting_source_refs=contradicting,
        validation=validation or _validation(),
        supersedes_record_id=supersedes,
        superseded_by_record_id=superseded_by,
    )


def _manifest(
    tmp_path: Path,
    records: tuple[ExperienceRecord, ...],
    *,
    role: str = "train",
    construction_sha256: str = "b" * 64,
) -> Path:
    path = tmp_path / "experience-memory.json"
    document = {
        "schema": "saea-experience-memory-manifest-v1",
        "memory_id": "slurp-corrective-memory",
        "memory_version": 3,
        "construction_partition_role": role,
        "train_construction_sha256": construction_sha256,
        "records": [record.as_json() for record in records],
    }
    path.write_text(json.dumps(document, sort_keys=True, indent=2) + "\n")
    return path


def _load(path: Path):
    return load_experience_memory_manifest(
        path,
        expected_sha256=_sha256(path),
        expected_train_construction_sha256="b" * 64,
        expected_train_sample_ids=("train-001", "train-002"),
    )


def test_record_roundtrip_hash_pin_and_immutability(tmp_path):
    record = _record()
    restored = ExperienceRecord.from_json(record.as_json())
    assert restored == record
    assert restored.record_sha256 == record.record_sha256
    with pytest.raises(FrozenInstanceError):
        restored.guidance = "changed"

    path = _manifest(tmp_path, (record,))
    catalog = _load(path)
    assert catalog.manifest_sha256 == _sha256(path)
    assert catalog.records == (record,)
    with pytest.raises(FrozenInstanceError):
        catalog.memory_version = 4

    document = json.loads(path.read_text())
    document["records"][0]["guidance"] = "tampered"
    path.write_text(json.dumps(document, sort_keys=True) + "\n")
    with pytest.raises(ExperienceMemoryError, match="record hash"):
        _load(path)


@pytest.mark.parametrize("role", ["dev", "test", "external-governed"])
def test_runtime_manifest_refuses_non_train_sources(tmp_path, role):
    record = _record(source=_source(role=role))
    path = _manifest(tmp_path, (record,))
    with pytest.raises(ExperienceMemoryError, match="TRAIN"):
        _load(path)


def test_catalog_construction_enforces_admission_and_train_roster(tmp_path):
    path = _manifest(tmp_path, (_record(),))
    admitted = _load(path)
    with pytest.raises(ExperienceMemoryError, match="admitted"):
        replace(
            admitted,
            records=(_record(validation=_validation(status="rejected")),),
        )
    mislabeled = _record(source=_source(sample_id="dev-held-out"))
    with pytest.raises(ExperienceMemoryError, match="pinned TRAIN roster"):
        replace(admitted, records=(mislabeled,))


def test_runtime_manifest_refuses_non_train_supporting_or_contradicting_sources(
    tmp_path,
):
    for field in ("supporting", "contradicting"):
        reference = SourceRef("held-out-case", "c" * 64, partition_role="dev")
        kwargs = {field: (reference,)}
        path = _manifest(tmp_path, (_record(**kwargs),))
        with pytest.raises(ExperienceMemoryError, match="TRAIN"):
            _load(path)


def test_runtime_manifest_refuses_wrong_construction_identity_and_raw_pin(tmp_path):
    path = _manifest(tmp_path, (_record(),), construction_sha256="c" * 64)
    with pytest.raises(ExperienceMemoryError, match="construction identity"):
        _load(path)
    with pytest.raises(ExperienceMemoryError, match="manifest SHA"):
        load_experience_memory_manifest(
            path,
            expected_sha256="0" * 64,
            expected_train_construction_sha256="c" * 64,
            expected_train_sample_ids=("train-001",),
        )


@pytest.mark.parametrize("status", ["provisional", "rejected", "superseded"])
def test_runtime_manifest_refuses_records_not_admitted(tmp_path, status):
    record = _record(validation=_validation(status=status))
    path = _manifest(tmp_path, (record,))
    with pytest.raises(ExperienceMemoryError, match="admitted"):
        _load(path)


def test_selector_is_exact_deterministic_and_returns_compact_provenance(tmp_path):
    later = _record("z-later")
    earlier = _record(
        "a-earlier",
        kind="corrective-experience",
        required=("signal:evidence-conflict", "tool:knowledge-opened"),
        excluded=(),
    )
    wrong_phase = _record("wrong-phase", phases=("review",))
    contradicted_scope = _record(
        "excluded-corrupt",
        source=_source(sample_id="train-002"),
        excluded=("signal:audio-corrupt",),
    )
    path = _manifest(
        tmp_path,
        (later, wrong_phase, contradicted_scope, earlier),
    )
    catalog = _load(path)

    selected = catalog.select(
        task_id="slurp-slot-slu",
        phase="slots",
        component_tags=("use", "supply"),
        condition_tags=(
            "tool:knowledge-opened",
            "signal:evidence-conflict",
            "signal:audio-corrupt",
        ),
    )
    assert [item.record_id for item in selected] == ["a-earlier"]
    item = selected[0]
    assert item.kind == "corrective-experience"
    assert item.guidance == earlier.guidance
    assert item.memory_id == "slurp-corrective-memory"
    assert item.memory_version == 3
    assert item.manifest_sha256 == _sha256(path)
    assert item.record_sha256 == earlier.record_sha256
    assert item.source == earlier.source
    assert item.validation == earlier.validation
    assert item.supporting_source_refs == earlier.supporting_source_refs
    assert item.contradicting_source_refs == earlier.contradicting_source_refs
    assert json.loads(json.dumps(item.as_json()))["schema"] == (
        "saea-experience-guidance-v1"
    )

    ordinary = catalog.select(
        task_id="slurp-slot-slu",
        phase="slots",
        component_tags=("supply", "use"),
        condition_tags=("signal:evidence-conflict", "tool:knowledge-opened"),
    )
    assert [item.record_id for item in ordinary] == [
        "a-earlier",
        "excluded-corrupt",
        "z-later",
    ]


def test_selector_returns_empty_for_not_applicable_and_validates_runtime_tags(tmp_path):
    catalog = _load(_manifest(tmp_path, (_record(),)))
    assert (
        catalog.select(
            task_id="another-task",
            phase="slots",
            component_tags=("supply", "use"),
            condition_tags=("signal:evidence-conflict",),
        )
        == ()
    )
    assert (
        catalog.select(
            task_id="slurp-slot-slu",
            phase="slots",
            component_tags=("supply",),
            condition_tags=("signal:evidence-conflict",),
        )
        == ()
    )
    with pytest.raises(ExperienceMemoryError, match="unique"):
        catalog.select(
            task_id="slurp-slot-slu",
            phase="slots",
            component_tags=("use", "use"),
            condition_tags=("signal:evidence-conflict",),
        )
    with pytest.raises(ExperienceMemoryError, match="runtime-observable"):
        catalog.select(
            task_id="slurp-slot-slu",
            phase="slots",
            component_tags=("supply", "use"),
            condition_tags=("offline-outcome:correct",),
        )


def test_contradicting_cases_are_provenance_not_an_automatic_runtime_veto(tmp_path):
    record = _record(excluded=())
    catalog = _load(_manifest(tmp_path, (record,)))
    selected = catalog.select(
        task_id="slurp-slot-slu",
        phase="slots",
        component_tags=("supply", "use"),
        condition_tags=("signal:evidence-conflict",),
    )
    assert len(selected) == 1
    assert selected[0].contradicting_source_refs == record.contradicting_source_refs


def test_loader_refuses_duplicate_ids_and_duplicate_content(tmp_path):
    first = _record("first")
    duplicate_id = replace(
        _record("second"),
        record_id="first",
    )
    # Rebuild the self-hash after changing the identity.
    duplicate_id = ExperienceRecord.from_unsigned_json(duplicate_id.unsigned_json())
    path = _manifest(tmp_path, (first, duplicate_id))
    with pytest.raises(ExperienceMemoryError, match="record IDs"):
        _load(path)

    same_content = _record("another-id")
    path = _manifest(tmp_path, (first, same_content))
    with pytest.raises(ExperienceMemoryError, match="duplicate content"):
        _load(path)


def test_record_refuses_overlapping_evidence_and_invalid_lineage():
    shared = SourceRef("same-case", "9" * 64)
    with pytest.raises(ExperienceMemoryError, match="supporting and contradicting"):
        _record(supporting=(shared,), contradicting=(shared,))
    with pytest.raises(ExperienceMemoryError, match="superseded"):
        _record(superseded_by="new-rule")
    with pytest.raises(ExperienceMemoryError, match="revision"):
        _record(revision=2)
    revised = _record(revision=2, supersedes="old-rule")
    assert revised.supersedes_record_id == "old-rule"


def test_direct_record_construction_refuses_mutable_nested_sequences():
    record = _record()
    mutable_limitations = replace(
        record,
        limitations=["mutable limitation"],
    )
    with pytest.raises(ExperienceMemoryError, match="limitations must be a tuple"):
        mutable_limitations.validate()

    mutable_supporting = replace(
        record,
        supporting_source_refs=list(record.supporting_source_refs),
    )
    with pytest.raises(
        ExperienceMemoryError,
        match="supporting source references must be a tuple",
    ):
        mutable_supporting.validate()

    mutable_contradicting = replace(
        record,
        contradicting_source_refs=list(record.contradicting_source_refs),
    )
    with pytest.raises(
        ExperienceMemoryError,
        match="contradicting source references must be a tuple",
    ):
        mutable_contradicting.validate()
