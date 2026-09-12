"""Source-bound runtime access to offline-admitted corrective memory.

The loader reads only pinned local receipts. Selection is deterministic and
uses a finite projection of state already visible to the runtime. It neither
updates memory nor treats an offline validation hash as proof of quality.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from ..core.preparation import PreparationError, hash_stable_file
from ..core.roster import CONSTRUCTION_ROSTER_ROLE, RosterError, read_roster
from .errors import RailsError
from .experience_memory import (
    ExperienceGuidance,
    ExperienceMemoryCatalog,
    ExperienceMemoryError,
    load_experience_memory_manifest,
)

CORRECTIVE_MEMORY_TOOL = "saea-tool-corrective-memory-v1"
EXPERIENCE_MEMORY_ADMISSION_SCHEMA = "saea-experience-memory-admission-v2"
EXPERIENCE_MEMORY_SELECTION_SCHEMA = "saea-experience-memory-selection-v1"
COMPONENT_TAGS = frozenset({"obs", "org", "supply", "use"})
PROJECTED_CONDITION_TAGS = frozenset(
    {
        "state:prior-response-present",
        "state:prior-response-absent",
        "state:knowledge-present",
        "state:knowledge-absent",
        "state:tool-result-present",
        "state:tool-result-absent",
    }
)
MAX_RUNTIME_RECORDS = 32
_SHA = re.compile(r"[0-9a-f]{64}")
_ENGLISH_ID = re.compile(r"[A-Za-z][A-Za-z0-9._:/ -]*")
_BINDING_KEYS = frozenset(
    {
        "manifest",
        "construction_roster",
        "admission",
        "source_verification",
        "task_id",
        "component_tags",
        "max_records",
    }
)


class ExperienceMemoryBindingError(RailsError):
    """A runtime memory declaration or its pinned evidence is invalid."""


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise ExperienceMemoryBindingError(f"{field} must be a lowercase SHA-256")
    return value


def _confined(root: Path, relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise ExperienceMemoryBindingError(f"{field} must be a non-empty relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or "\\" in relative or any(
        part in ("", ".", "..") for part in pure.parts
    ):
        raise ExperienceMemoryBindingError(f"{field} must be a confined relative path")
    try:
        resolved_root = Path(root).resolve(strict=True)
        result = (resolved_root / relative).resolve(strict=True)
    except OSError as error:
        raise ExperienceMemoryBindingError(f"cannot resolve {field}: {error}") from error
    if not result.is_relative_to(resolved_root):
        raise ExperienceMemoryBindingError(f"{field} escapes its confined root")
    return result


def _pinned_file(root: Path, spec: object, *, path_key: str, field: str) -> tuple[Path, str]:
    if not isinstance(spec, Mapping) or set(spec) != {path_key, "sha256"}:
        raise ExperienceMemoryBindingError(
            f"{field} must contain exactly {path_key!r} and 'sha256'"
        )
    expected = _sha(spec["sha256"], f"{field} SHA")
    path = _confined(root, spec[path_key], f"{field} path")
    try:
        _size, actual, _fingerprint = hash_stable_file(path, field)
    except PreparationError as error:
        raise ExperienceMemoryBindingError(str(error)) from error
    if actual != expected:
        raise ExperienceMemoryBindingError(f"{field} SHA mismatch")
    return path, actual


def _project_conditions(context: object) -> tuple[str, ...]:
    prior = bool(getattr(context, "prior_response_sha256s", ()))
    query_state = getattr(context, "query_state", None)
    knowledge = bool(getattr(query_state, "retrieved_value_ids", ()))
    agent_states = getattr(context, "agent_states", ())
    tool_result = any(
        getattr(state, "state_kind", None) == "tool-result" for state in agent_states
    )
    return tuple(
        sorted(
            (
                f"state:prior-response-{'present' if prior else 'absent'}",
                f"state:knowledge-{'present' if knowledge else 'absent'}",
                f"state:tool-result-{'present' if tool_result else 'absent'}",
            )
        )
    )


def _visible_guidance(item: ExperienceGuidance) -> dict[str, object]:
    source = item.source
    validation = item.validation
    return {
        "record_id": item.record_id,
        "record_sha256": item.record_sha256,
        "revision": item.revision,
        "kind": item.kind,
        "diagnosis": item.diagnosis,
        "guidance": item.guidance,
        "limitations": list(item.limitations),
        "applicability": item.applicability.as_json(),
        "source_hashes": {
            "trajectory_sha256": source.trajectory_sha256,
            "action_sha256": source.action_sha256,
            "response_sha256": source.response_sha256,
            "outcome_sha256": source.outcome_sha256,
        },
        "supporting_source_hashes": [ref.sha256 for ref in item.supporting_source_refs],
        "contradicting_source_hashes": [
            ref.sha256 for ref in item.contradicting_source_refs
        ],
        "validation": {
            "status": validation.status,
            "decision_sha256": validation.decision_sha256,
            "protocol_sha256": validation.protocol_sha256,
            "roster_sha256": validation.roster_sha256,
            "result_sha256": validation.result_sha256,
        },
        "supersedes_record_id": item.supersedes_record_id,
    }


@dataclass(frozen=True)
class ExperienceMemorySelection:
    """Model-visible guidance beside complete internal provenance."""

    visible: Mapping[str, object]
    lineage: Mapping[str, object]


@dataclass(frozen=True)
class LoadedExperienceMemoryBinding:
    catalog: ExperienceMemoryCatalog
    manifest_sha256: str
    construction_roster_sha256: str
    admission_sha256: str
    source_verification_sha256: str
    task_id: str
    component_tags: tuple[str, ...]
    max_records: int

    def select(self, *, next_phase: str, context: object) -> ExperienceMemorySelection:
        if not isinstance(next_phase, str) or not next_phase:
            raise ExperienceMemoryBindingError("successor phase must be non-empty text")
        condition_tags = _project_conditions(context)
        selected = self.catalog.select(
            task_id=self.task_id,
            phase=next_phase,
            component_tags=self.component_tags,
            condition_tags=condition_tags,
        )[: self.max_records]
        visible = {
            "schema": EXPERIENCE_MEMORY_SELECTION_SCHEMA,
            "memory_id": self.catalog.memory_id,
            "memory_version": self.catalog.memory_version,
            "manifest_sha256": self.manifest_sha256,
            "admission_sha256": self.admission_sha256,
            "task_id": self.task_id,
            "next_phase": next_phase,
            "component_tags": list(self.component_tags),
            "condition_tags": list(condition_tags),
            "selected_records": [_visible_guidance(item) for item in selected],
        }
        lineage = {
            **visible,
            "construction_roster_sha256": self.construction_roster_sha256,
            "source_verification_sha256": self.source_verification_sha256,
            "selected_records": [item.as_json() for item in selected],
        }
        return ExperienceMemorySelection(visible=visible, lineage=lineage)


def load_experience_memory_binding(
    config: Mapping[str, object],
    *,
    repo_root: Path,
    data_root: Path,
    carrier_lock_key: str,
) -> LoadedExperienceMemoryBinding | None:
    """Load and validate the opt-in binding once, before any model contact."""

    raw = config.get("experience_memory")
    if raw is None:
        return None
    if carrier_lock_key != "slurp":
        raise ExperienceMemoryBindingError(
            "initial corrective-memory runtime admission supports only SLURP"
        )
    if not isinstance(raw, Mapping) or set(raw) != _BINDING_KEYS:
        raise ExperienceMemoryBindingError(
            f"experience_memory must contain exactly {sorted(_BINDING_KEYS)}"
        )
    task_id = raw["task_id"]
    if not isinstance(task_id, str) or _ENGLISH_ID.fullmatch(task_id) is None:
        raise ExperienceMemoryBindingError("experience_memory task_id must be an English identifier")
    components = raw["component_tags"]
    if (
        not isinstance(components, list)
        or not components
        or any(item not in COMPONENT_TAGS for item in components)
        or len(components) != len(set(components))
    ):
        raise ExperienceMemoryBindingError(
            "experience_memory component_tags must be a unique non-empty subset of obs/org/supply/use"
        )
    max_records = raw["max_records"]
    if (
        isinstance(max_records, bool)
        or not isinstance(max_records, int)
        or not 1 <= max_records <= MAX_RUNTIME_RECORDS
    ):
        raise ExperienceMemoryBindingError(
            f"experience_memory max_records must be an integer from 1 to {MAX_RUNTIME_RECORDS}"
        )

    manifest_path, manifest_sha = _pinned_file(
        Path(data_root), raw["manifest"], path_key="relpath", field="experience manifest"
    )
    roster_path, roster_sha = _pinned_file(
        Path(repo_root),
        raw["construction_roster"],
        path_key="repo_relpath",
        field="construction roster",
    )
    admission_path, admission_sha = _pinned_file(
        Path(data_root), raw["admission"], path_key="relpath", field="memory admission"
    )
    source_path, source_sha = _pinned_file(
        Path(data_root), raw["source_verification"],
        path_key="relpath", field="memory source verification",
    )
    try:
        roster = read_roster(roster_path)
    except (OSError, ValueError, json.JSONDecodeError, RosterError) as error:
        raise ExperienceMemoryBindingError(f"invalid construction roster: {error}") from error
    if roster.get("roster_role") != CONSTRUCTION_ROSTER_ROLE:
        raise ExperienceMemoryBindingError("memory roster must have construction role")
    if roster.get("carrier_lock_key") != carrier_lock_key:
        raise ExperienceMemoryBindingError("memory roster carrier differs from the flight")
    sample_ids = tuple(item["sample_id"] for item in roster["items"])
    if any(not sample_id.startswith("slurp:train:") for sample_id in sample_ids):
        raise ExperienceMemoryBindingError(
            "SLURP memory construction roster must contain only slurp:train: samples"
        )
    try:
        catalog = load_experience_memory_manifest(
            manifest_path,
            expected_sha256=manifest_sha,
            expected_train_construction_sha256=roster_sha,
            expected_train_sample_ids=sample_ids,
        )
    except ExperienceMemoryError as error:
        raise ExperienceMemoryBindingError(str(error)) from error
    for record in catalog.records:
        declared = set(record.applicability.required_conditions) | set(
            record.applicability.excluded_conditions
        )
        unsupported = declared - PROJECTED_CONDITION_TAGS
        if unsupported:
            raise ExperienceMemoryBindingError(
                f"experience record {record.record_id!r} uses unsupported condition tags: {sorted(unsupported)}"
            )
    try:
        admission = json.loads(admission_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ExperienceMemoryBindingError(f"cannot read memory admission: {error}") from error
    admission_keys = {
        "schema",
        "status",
        "manifest_sha256",
        "construction_roster_sha256",
        "admitted_record_sha256s",
        "source_verification_sha256",
    }
    if not isinstance(admission, Mapping) or set(admission) != admission_keys:
        raise ExperienceMemoryBindingError("memory admission has wrong fields")
    if admission["schema"] != EXPERIENCE_MEMORY_ADMISSION_SCHEMA or admission["status"] != "admitted":
        raise ExperienceMemoryBindingError("memory admission is not admitted")
    if admission["manifest_sha256"] != manifest_sha or admission["construction_roster_sha256"] != roster_sha:
        raise ExperienceMemoryBindingError("memory admission identity mismatch")
    if admission["source_verification_sha256"] != source_sha:
        raise ExperienceMemoryBindingError("memory admission source verification mismatch")
    from .experience_memory_sources import (
        MemorySourceVerificationError, load_verified_memory_sources,
    )
    try:
        load_verified_memory_sources(catalog, source_path, expected_sha256=source_sha)
    except MemorySourceVerificationError as error:
        raise ExperienceMemoryBindingError(str(error)) from error
    admitted = admission["admitted_record_sha256s"]
    if (
        not isinstance(admitted, list)
        or any(not isinstance(item, str) or _SHA.fullmatch(item) is None for item in admitted)
        or len(admitted) != len(set(admitted))
        or set(admitted) != {record.record_sha256 for record in catalog.records}
    ):
        raise ExperienceMemoryBindingError("memory admission record set mismatch")
    return LoadedExperienceMemoryBinding(
        catalog=catalog,
        manifest_sha256=manifest_sha,
        construction_roster_sha256=roster_sha,
        admission_sha256=admission_sha,
        source_verification_sha256=source_sha,
        task_id=task_id,
        component_tags=tuple(components),
        max_records=max_records,
    )
