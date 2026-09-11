"""Immutable corrective experiences and rules for runtime guidance.

Raw TRAIN facts and examples remain knowledge. This module holds analyzed
failure/correction records. Validation hashes are provenance pointers, not
proof of statistical quality; an offline admission process must approve each
record before runtime use. Applicability is limited to runtime-observable
task-family, phase, component, state, signal, tool, and configuration tags.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from .errors import RailsError
from .hashing import content_hash

EXPERIENCE_RECORD_SCHEMA = "saea-experience-memory-record-v1"
EXPERIENCE_MANIFEST_SCHEMA = "saea-experience-memory-manifest-v1"
EXPERIENCE_GUIDANCE_SCHEMA = "saea-experience-guidance-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_KINDS = frozenset({"corrective-experience", "conditional-rule"})
_STATUSES = frozenset({"admitted", "provisional", "rejected", "superseded"})
_CONDITION_PREFIXES = ("state:", "signal:", "tool:", "config:")


class ExperienceMemoryError(RailsError):
    """Corrective-memory bytes or runtime applicability are invalid."""


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExperienceMemoryError(f"{field} must be a non-empty string")
    return value


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ExperienceMemoryError(f"{field} must be a lowercase SHA-256")
    return value


def _positive_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ExperienceMemoryError(f"{field} must be a positive integer")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ExperienceMemoryError(f"{field} must be a sequence")
    return value


def _texts(value: object, field: str, *, required: bool = False) -> tuple[str, ...]:
    result = tuple(
        _text(item, f"{field}[{index}]")
        for index, item in enumerate(_sequence(value, field))
    )
    if required and not result:
        raise ExperienceMemoryError(f"{field} must not be empty")
    if len(result) != len(set(result)):
        raise ExperienceMemoryError(f"{field} values must be unique")
    return result


def _conditions(value: object, field: str) -> tuple[str, ...]:
    result = _texts(value, field)
    if any(not item.startswith(_CONDITION_PREFIXES) for item in result):
        raise ExperienceMemoryError(
            f"{field} must contain only runtime-observable state:, signal:, "
            "tool:, or config: tags"
        )
    return result


def _mapping(value: object, field: str, keys: frozenset[str]) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise ExperienceMemoryError(f"{field} must have exact keys {sorted(keys)}")
    return value


def _optional_text(value: object, field: str) -> str | None:
    return None if value is None else _text(value, field)


@dataclass(frozen=True)
class SourceRef:
    """Offline archive pointer whose hash requires separate admission verification."""

    ref_id: str
    sha256: str
    partition_role: str = "train"

    def validate(self) -> None:
        _text(self.ref_id, "source reference ID")
        _sha(self.sha256, "source reference SHA-256")
        _text(self.partition_role, "source reference partition role")

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "ref_id": self.ref_id,
            "sha256": self.sha256,
            "partition_role": self.partition_role,
        }

    @classmethod
    def from_json(cls, value: object) -> "SourceRef":
        row = _mapping(
            value, "source reference", frozenset({"ref_id", "sha256", "partition_role"})
        )
        result = cls(row["ref_id"], row["sha256"], row["partition_role"])
        result.validate()
        return result


@dataclass(frozen=True)
class ExperienceSource:
    partition_role: str
    source_sample_id: str
    trajectory_sha256: str
    action_sha256: str
    response_sha256: str
    outcome_sha256: str

    def validate(self) -> None:
        _text(self.partition_role, "source partition role")
        _text(self.source_sample_id, "source sample ID")
        for field in (
            "trajectory_sha256",
            "action_sha256",
            "response_sha256",
            "outcome_sha256",
        ):
            _sha(getattr(self, field), field)

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "partition_role": self.partition_role,
            "source_sample_id": self.source_sample_id,
            "trajectory_sha256": self.trajectory_sha256,
            "action_sha256": self.action_sha256,
            "response_sha256": self.response_sha256,
            "outcome_sha256": self.outcome_sha256,
        }

    @classmethod
    def from_json(cls, value: object) -> "ExperienceSource":
        keys = frozenset(
            {
                "partition_role",
                "source_sample_id",
                "trajectory_sha256",
                "action_sha256",
                "response_sha256",
                "outcome_sha256",
            }
        )
        row = _mapping(value, "experience source", keys)
        result = cls(
            *(
                row[key]
                for key in (
                    "partition_role",
                    "source_sample_id",
                    "trajectory_sha256",
                    "action_sha256",
                    "response_sha256",
                    "outcome_sha256",
                )
            )
        )
        result.validate()
        return result


@dataclass(frozen=True)
class ValidationBinding:
    status: str
    decision_sha256: str
    protocol_sha256: str
    roster_sha256: str
    result_sha256: str

    def validate(self) -> None:
        if self.status not in _STATUSES:
            raise ExperienceMemoryError(
                f"validation status must be one of {sorted(_STATUSES)}"
            )
        for field in (
            "decision_sha256",
            "protocol_sha256",
            "roster_sha256",
            "result_sha256",
        ):
            _sha(getattr(self, field), field)

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "status": self.status,
            "decision_sha256": self.decision_sha256,
            "protocol_sha256": self.protocol_sha256,
            "roster_sha256": self.roster_sha256,
            "result_sha256": self.result_sha256,
        }

    @classmethod
    def from_json(cls, value: object) -> "ValidationBinding":
        keys = frozenset(
            {
                "status",
                "decision_sha256",
                "protocol_sha256",
                "roster_sha256",
                "result_sha256",
            }
        )
        row = _mapping(value, "validation binding", keys)
        result = cls(
            *(
                row[key]
                for key in (
                    "status",
                    "decision_sha256",
                    "protocol_sha256",
                    "roster_sha256",
                    "result_sha256",
                )
            )
        )
        result.validate()
        return result


@dataclass(frozen=True)
class Applicability:
    """Observable scope; task IDs name task families, never samples or gold."""

    task_ids: tuple[str, ...]
    phases: tuple[str, ...]
    component_tags: tuple[str, ...]
    required_conditions: tuple[str, ...]
    excluded_conditions: tuple[str, ...]

    def validate(self) -> None:
        normalized = (
            _texts(self.task_ids, "applicability task IDs", required=True),
            _texts(self.phases, "applicability phases", required=True),
            _texts(
                self.component_tags,
                "applicability component tags",
                required=True,
            ),
            _conditions(self.required_conditions, "required conditions"),
            _conditions(self.excluded_conditions, "excluded conditions"),
        )
        if normalized != (
            self.task_ids,
            self.phases,
            self.component_tags,
            self.required_conditions,
            self.excluded_conditions,
        ):
            raise ExperienceMemoryError("applicability fields must be tuples")
        if set(self.required_conditions) & set(self.excluded_conditions):
            raise ExperienceMemoryError(
                "required and excluded conditions must not overlap"
            )

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "task_ids": list(self.task_ids),
            "phases": list(self.phases),
            "component_tags": list(self.component_tags),
            "required_conditions": list(self.required_conditions),
            "excluded_conditions": list(self.excluded_conditions),
        }

    @classmethod
    def from_json(cls, value: object) -> "Applicability":
        keys = frozenset(
            {
                "task_ids",
                "phases",
                "component_tags",
                "required_conditions",
                "excluded_conditions",
            }
        )
        row = _mapping(value, "applicability", keys)
        result = cls(
            _texts(row["task_ids"], "applicability task IDs", required=True),
            _texts(row["phases"], "applicability phases", required=True),
            _texts(
                row["component_tags"],
                "applicability component tags",
                required=True,
            ),
            _conditions(row["required_conditions"], "required conditions"),
            _conditions(row["excluded_conditions"], "excluded conditions"),
        )
        result.validate()
        return result

    def matches(
        self,
        *,
        task_id: str,
        phase: str,
        component_tags: frozenset[str],
        condition_tags: frozenset[str],
    ) -> bool:
        return (
            task_id in self.task_ids
            and phase in self.phases
            and set(self.component_tags) <= component_tags
            and set(self.required_conditions) <= condition_tags
            and not set(self.excluded_conditions) & condition_tags
        )


_UNSIGNED_KEYS = frozenset(
    {
        "schema",
        "record_id",
        "revision",
        "kind",
        "train_construction_sha256",
        "source",
        "applicability",
        "diagnosis",
        "guidance",
        "limitations",
        "supporting_source_refs",
        "contradicting_source_refs",
        "validation",
        "supersedes_record_id",
        "superseded_by_record_id",
    }
)
_RECORD_KEYS = _UNSIGNED_KEYS | {"record_sha256"}


@dataclass(frozen=True)
class ExperienceRecord:
    record_id: str
    revision: int
    kind: str
    train_construction_sha256: str
    source: ExperienceSource
    applicability: Applicability
    diagnosis: str
    guidance: str
    limitations: tuple[str, ...]
    supporting_source_refs: tuple[SourceRef, ...]
    contradicting_source_refs: tuple[SourceRef, ...]
    validation: ValidationBinding
    supersedes_record_id: str | None
    superseded_by_record_id: str | None
    record_sha256: str
    schema: str = EXPERIENCE_RECORD_SCHEMA

    @classmethod
    def create(
        cls,
        *,
        record_id: str,
        revision: int,
        kind: str,
        train_construction_sha256: str,
        source: ExperienceSource,
        applicability: Applicability,
        diagnosis: str,
        guidance: str,
        limitations: Sequence[str],
        supporting_source_refs: Sequence[SourceRef],
        contradicting_source_refs: Sequence[SourceRef] = (),
        validation: ValidationBinding,
        supersedes_record_id: str | None = None,
        superseded_by_record_id: str | None = None,
    ) -> "ExperienceRecord":
        result = cls(
            record_id,
            revision,
            kind,
            train_construction_sha256,
            source,
            applicability,
            diagnosis,
            guidance,
            _texts(limitations, "limitations"),
            tuple(supporting_source_refs),
            tuple(contradicting_source_refs),
            validation,
            supersedes_record_id,
            superseded_by_record_id,
            "0" * 64,
        )
        result._validate_content()
        result = replace(result, record_sha256=content_hash(result.unsigned_json()))
        result.validate()
        return result

    def _validate_content(self) -> None:
        if self.schema != EXPERIENCE_RECORD_SCHEMA:
            raise ExperienceMemoryError("experience record schema mismatch")
        _text(self.record_id, "record ID")
        _positive_int(self.revision, "record revision")
        if self.kind not in _KINDS:
            raise ExperienceMemoryError(f"record kind must be one of {sorted(_KINDS)}")
        _sha(self.train_construction_sha256, "record TRAIN construction SHA-256")
        self.source.validate()
        self.applicability.validate()
        _text(self.diagnosis, "diagnosis")
        _text(self.guidance, "guidance")
        if not isinstance(self.limitations, tuple):
            raise ExperienceMemoryError("limitations must be a tuple")
        if not isinstance(self.supporting_source_refs, tuple):
            raise ExperienceMemoryError("supporting source references must be a tuple")
        if not isinstance(self.contradicting_source_refs, tuple):
            raise ExperienceMemoryError(
                "contradicting source references must be a tuple"
            )
        _texts(self.limitations, "limitations")
        if not self.supporting_source_refs:
            raise ExperienceMemoryError(
                "supporting source references must not be empty"
            )
        for ref in self.supporting_source_refs + self.contradicting_source_refs:
            if not isinstance(ref, SourceRef):
                raise ExperienceMemoryError(
                    "source references must be SourceRef values"
                )
            ref.validate()
        supporting = {ref.ref_id for ref in self.supporting_source_refs}
        contradicting = {ref.ref_id for ref in self.contradicting_source_refs}
        if len(supporting) != len(self.supporting_source_refs) or len(
            contradicting
        ) != len(self.contradicting_source_refs):
            raise ExperienceMemoryError("source references must be unique")
        if supporting & contradicting:
            raise ExperienceMemoryError(
                "supporting and contradicting source references must not overlap"
            )
        self.validation.validate()
        supersedes = _optional_text(self.supersedes_record_id, "supersedes record ID")
        superseded_by = _optional_text(
            self.superseded_by_record_id, "superseded-by record ID"
        )
        if self.record_id in {supersedes, superseded_by}:
            raise ExperienceMemoryError("a record cannot supersede itself")
        if self.revision == 1 and supersedes is not None:
            raise ExperienceMemoryError(
                "record revision 1 cannot declare a superseded predecessor"
            )
        if self.revision > 1 and supersedes is None:
            raise ExperienceMemoryError(
                "record revision greater than 1 requires a supersedes record ID"
            )
        if self.validation.status == "admitted" and superseded_by is not None:
            raise ExperienceMemoryError(
                "an admitted record cannot already be superseded"
            )

    def validate(self) -> None:
        self._validate_content()
        _sha(self.record_sha256, "record hash")
        if self.record_sha256 != content_hash(self.unsigned_json()):
            raise ExperienceMemoryError("experience record hash mismatch")

    def unsigned_json(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "record_id": self.record_id,
            "revision": self.revision,
            "kind": self.kind,
            "train_construction_sha256": self.train_construction_sha256,
            "source": self.source.as_json(),
            "applicability": self.applicability.as_json(),
            "diagnosis": self.diagnosis,
            "guidance": self.guidance,
            "limitations": list(self.limitations),
            "supporting_source_refs": [
                ref.as_json() for ref in self.supporting_source_refs
            ],
            "contradicting_source_refs": [
                ref.as_json() for ref in self.contradicting_source_refs
            ],
            "validation": self.validation.as_json(),
            "supersedes_record_id": self.supersedes_record_id,
            "superseded_by_record_id": self.superseded_by_record_id,
        }

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {**self.unsigned_json(), "record_sha256": self.record_sha256}

    @classmethod
    def from_unsigned_json(cls, value: object) -> "ExperienceRecord":
        row = _mapping(value, "unsigned experience record", _UNSIGNED_KEYS)
        if row["schema"] != EXPERIENCE_RECORD_SCHEMA:
            raise ExperienceMemoryError("experience record schema mismatch")
        result = cls(
            row["record_id"],
            row["revision"],
            row["kind"],
            row["train_construction_sha256"],
            ExperienceSource.from_json(row["source"]),
            Applicability.from_json(row["applicability"]),
            row["diagnosis"],
            row["guidance"],
            _texts(row["limitations"], "limitations"),
            tuple(
                SourceRef.from_json(item)
                for item in _sequence(
                    row["supporting_source_refs"], "supporting source references"
                )
            ),
            tuple(
                SourceRef.from_json(item)
                for item in _sequence(
                    row["contradicting_source_refs"],
                    "contradicting source references",
                )
            ),
            ValidationBinding.from_json(row["validation"]),
            _optional_text(row["supersedes_record_id"], "supersedes record ID"),
            _optional_text(row["superseded_by_record_id"], "superseded-by record ID"),
            "0" * 64,
        )
        result._validate_content()
        result = replace(result, record_sha256=content_hash(result.unsigned_json()))
        result.validate()
        return result

    @classmethod
    def from_json(cls, value: object) -> "ExperienceRecord":
        row = _mapping(value, "experience record", _RECORD_KEYS)
        result = cls.from_unsigned_json({key: row[key] for key in _UNSIGNED_KEYS})
        claimed = _sha(row["record_sha256"], "record hash")
        if claimed != result.record_sha256:
            raise ExperienceMemoryError("experience record hash mismatch")
        return replace(result, record_sha256=claimed)

    def semantic_hash(self) -> str:
        value = self.unsigned_json()
        for key in (
            "record_id",
            "revision",
            "supersedes_record_id",
            "superseded_by_record_id",
        ):
            value.pop(key)
        return content_hash(value)


@dataclass(frozen=True)
class ExperienceGuidance:
    """Compact guidance retaining its complete lineage."""

    memory_id: str
    memory_version: int
    manifest_sha256: str
    record_id: str
    revision: int
    kind: str
    diagnosis: str
    guidance: str
    limitations: tuple[str, ...]
    applicability: Applicability
    record_sha256: str
    source: ExperienceSource
    supporting_source_refs: tuple[SourceRef, ...]
    contradicting_source_refs: tuple[SourceRef, ...]
    validation: ValidationBinding
    supersedes_record_id: str | None
    schema: str = EXPERIENCE_GUIDANCE_SCHEMA

    def as_json(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "memory_id": self.memory_id,
            "memory_version": self.memory_version,
            "manifest_sha256": self.manifest_sha256,
            "record_id": self.record_id,
            "revision": self.revision,
            "kind": self.kind,
            "diagnosis": self.diagnosis,
            "guidance": self.guidance,
            "limitations": list(self.limitations),
            "applicability": self.applicability.as_json(),
            "record_sha256": self.record_sha256,
            "source": self.source.as_json(),
            "supporting_source_refs": [
                ref.as_json() for ref in self.supporting_source_refs
            ],
            "contradicting_source_refs": [
                ref.as_json() for ref in self.contradicting_source_refs
            ],
            "validation": self.validation.as_json(),
            "supersedes_record_id": self.supersedes_record_id,
        }


@dataclass(frozen=True)
class ExperienceMemoryCatalog:
    """Pinned TRAIN records for one construction; not universal cross-carrier admission."""

    memory_id: str
    memory_version: int
    manifest_sha256: str
    train_construction_sha256: str
    expected_train_sample_ids: frozenset[str]
    records: tuple[ExperienceRecord, ...]

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        _text(self.memory_id, "memory ID")
        _positive_int(self.memory_version, "memory version")
        _sha(self.manifest_sha256, "manifest SHA-256")
        _sha(self.train_construction_sha256, "TRAIN construction identity")
        if not isinstance(self.expected_train_sample_ids, frozenset):
            raise ExperienceMemoryError(
                "expected TRAIN sample IDs must be an immutable frozenset"
            )
        _texts(
            tuple(sorted(self.expected_train_sample_ids)),
            "expected TRAIN sample IDs",
            required=True,
        )
        if not isinstance(self.records, tuple) or not self.records:
            raise ExperienceMemoryError(
                "experience memory records must be a non-empty tuple"
            )
        for record in self.records:
            if not isinstance(record, ExperienceRecord):
                raise ExperienceMemoryError(
                    "experience memory records must be ExperienceRecord values"
                )
            record.validate()
            if record.train_construction_sha256 != self.train_construction_sha256:
                raise ExperienceMemoryError(
                    "record TRAIN construction identity mismatch"
                )
            if record.source.partition_role != "train":
                raise ExperienceMemoryError(
                    "runtime experience memory must derive only from TRAIN sources"
                )
            if record.source.source_sample_id not in self.expected_train_sample_ids:
                raise ExperienceMemoryError(
                    "record source sample is outside the pinned TRAIN roster"
                )
            references = (
                record.supporting_source_refs + record.contradicting_source_refs
            )
            if any(ref.partition_role != "train" for ref in references):
                raise ExperienceMemoryError(
                    "runtime experience memory evidence must derive only from TRAIN sources"
                )
            if record.validation.status != "admitted":
                raise ExperienceMemoryError(
                    "runtime experience memory requires every record to be admitted"
                )
        record_ids = [record.record_id for record in self.records]
        if len(record_ids) != len(set(record_ids)):
            raise ExperienceMemoryError("experience memory record IDs must be unique")
        semantic_hashes = [record.semantic_hash() for record in self.records]
        if len(semantic_hashes) != len(set(semantic_hashes)):
            raise ExperienceMemoryError(
                "experience memory duplicate content is not allowed"
            )

    def select(
        self,
        *,
        task_id: str,
        phase: str,
        component_tags: Sequence[str],
        condition_tags: Sequence[str],
    ) -> tuple[ExperienceGuidance, ...]:
        task_id = _text(task_id, "task-family ID")
        phase = _text(phase, "phase")
        components = frozenset(_texts(component_tags, "runtime component tags"))
        conditions = frozenset(_conditions(condition_tags, "runtime condition tags"))
        selected = sorted(
            (
                record
                for record in self.records
                if record.applicability.matches(
                    task_id=task_id,
                    phase=phase,
                    component_tags=components,
                    condition_tags=conditions,
                )
            ),
            key=lambda record: (record.record_id, record.revision),
        )
        return tuple(
            ExperienceGuidance(
                self.memory_id,
                self.memory_version,
                self.manifest_sha256,
                record.record_id,
                record.revision,
                record.kind,
                record.diagnosis,
                record.guidance,
                record.limitations,
                record.applicability,
                record.record_sha256,
                record.source,
                record.supporting_source_refs,
                record.contradicting_source_refs,
                record.validation,
                record.supersedes_record_id,
            )
            for record in selected
        )


_MANIFEST_KEYS = frozenset(
    {
        "schema",
        "memory_id",
        "memory_version",
        "construction_partition_role",
        "train_construction_sha256",
        "records",
    }
)


def load_experience_memory_manifest(
    path: Path,
    *,
    expected_sha256: str,
    expected_train_construction_sha256: str,
    expected_train_sample_ids: Sequence[str],
) -> ExperienceMemoryCatalog:
    """Load a pinned catalog containing only offline-admitted TRAIN records."""

    expected = _sha(expected_sha256, "expected manifest SHA-256")
    expected_construction = _sha(
        expected_train_construction_sha256,
        "expected TRAIN construction identity",
    )
    train_sample_ids = frozenset(
        _texts(
            expected_train_sample_ids,
            "expected TRAIN sample IDs",
            required=True,
        )
    )
    try:
        raw = Path(path).read_bytes()
    except OSError as error:
        raise ExperienceMemoryError(
            f"cannot read experience memory manifest {path}: {error}"
        ) from error
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected:
        raise ExperienceMemoryError("experience memory manifest SHA mismatch")
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ExperienceMemoryError(
            f"experience memory manifest is not valid JSON: {error}"
        ) from error
    row = _mapping(document, "experience memory manifest", _MANIFEST_KEYS)
    if row["schema"] != EXPERIENCE_MANIFEST_SCHEMA:
        raise ExperienceMemoryError("experience memory manifest schema mismatch")
    memory_id = _text(row["memory_id"], "memory ID")
    memory_version = _positive_int(row["memory_version"], "memory version")
    if row["construction_partition_role"] != "train":
        raise ExperienceMemoryError(
            "runtime experience memory must derive only from TRAIN sources"
        )
    construction = _sha(
        row["train_construction_sha256"],
        "manifest TRAIN construction identity",
    )
    if construction != expected_construction:
        raise ExperienceMemoryError(
            "experience memory TRAIN construction identity mismatch"
        )
    records = tuple(
        ExperienceRecord.from_json(item)
        for item in _sequence(row["records"], "experience records")
    )
    return ExperienceMemoryCatalog(
        memory_id,
        memory_version,
        actual,
        construction,
        train_sample_ids,
        records,
    )
