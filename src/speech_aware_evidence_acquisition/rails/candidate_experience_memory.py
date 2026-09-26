"""Source-attested provisional corrective memory for disjoint TRAIN evaluation."""
from __future__ import annotations
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from ..contracts import ExecutionPlan, ExecutionScopeError
from ..core.preparation import (
    PreparationError, digest, hash_stable_file, load_artifact, prepare_artifact,
)
from ..core.provisional_candidate_materialization import ARTIFACT_KIND, OUTPUT_SCHEMA
from ..core.roster import (
    CONSTRUCTION_ROSTER_ROLE, EVALUATION_ROSTER_ROLE, RosterError, read_roster,
)
from .errors import RailsError
from .experience_memory import ExperienceGuidance, ExperienceMemoryError, ExperienceRecord
from .experience_memory_runtime import (
    COMPONENT_TAGS, MAX_RUNTIME_RECORDS, PROJECTED_CONDITION_TAGS, ExperienceMemorySelection,
    _project_conditions, _visible_guidance,
)
from .experience_memory_sources import reward_link_hash_source_ref, system_group_hash_source_ref

SOURCE_ATTESTATION_SCHEMA = "saea-provisional-experience-source-attestation-v1"
SOURCE_ATTESTATION_KIND = "provisional-experience-source-attestation"
SELECTION_SCHEMA = "saea-provisional-experience-selection-v1"
DECISION_SCHEMA = "saea-candidate-experience-evaluation-decision-v1"
_SHA = re.compile(r"[0-9a-f]{64}")
_BINDING_KEYS = frozenset({
    "artifact", "source_attestation", "construction_roster", "evaluation_roster",
    "evaluation_decision", "ordered_record_sha256s", "task_id", "component_tags",
    "allowed_roles",
})


class CandidateExperienceMemoryError(RailsError):
    """A provisional TRAIN-evaluation source or binding is invalid."""


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA.fullmatch(value) is None:
        raise CandidateExperienceMemoryError(f"{field} must be a lowercase SHA-256")
    return value


def _confined(root: Path, relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CandidateExperienceMemoryError(f"{field} must be a non-empty relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or "\\" in relative or any(
        part in {"", ".", ".."} for part in pure.parts
    ):
        raise CandidateExperienceMemoryError(f"{field} must be a confined relative path")
    resolved_root = Path(root).resolve(strict=True)
    try:
        path = (resolved_root / relative).resolve(strict=True)
    except OSError as error:
        raise CandidateExperienceMemoryError(f"cannot resolve {field}: {error}") from error
    if not path.is_relative_to(resolved_root):
        raise CandidateExperienceMemoryError(f"{field} escapes its confined root")
    return path


def _pinned(root: Path, value: object, field: str, path_key: str) -> tuple[Path, str]:
    if not isinstance(value, Mapping) or set(value) != {path_key, "sha256"}:
        raise CandidateExperienceMemoryError(
            f"{field} must contain exactly {path_key!r} and 'sha256'"
        )
    path = _confined(root, value[path_key], field)
    expected = _sha(value["sha256"], f"{field} SHA-256")
    try:
        actual = hash_stable_file(path, field)[1]
    except PreparationError as error:
        raise CandidateExperienceMemoryError(str(error)) from error
    if actual != expected:
        raise CandidateExperienceMemoryError(f"{field} SHA mismatch")
    return path, actual


def _target(root: Path, relative: object, field: str) -> Path:
    if not isinstance(relative, str) or not relative:
        raise CandidateExperienceMemoryError(f"{field} must be a non-empty relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or "\\" in relative or any(
        part in {"", ".", ".."} for part in pure.parts
    ):
        raise CandidateExperienceMemoryError(f"{field} must be a confined relative path")
    resolved_root = Path(root).resolve(strict=True)
    path = (resolved_root / relative).resolve()
    if not path.is_relative_to(resolved_root):
        raise CandidateExperienceMemoryError(f"{field} escapes its confined root")
    return path


def _prepared(
    path: Path, expected_sha: str, kind: str,
) -> tuple[dict[str, object], str, dict[str, object]]:
    try:
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            raise CandidateExperienceMemoryError("prepared artifact file hash mismatch")
        wrapper = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CandidateExperienceMemoryError(f"cannot read prepared artifact: {error}") from error
    keys = {"schema", "kind", "inputs", "contact_class", "output", "output_sha256"}
    if (
        not isinstance(wrapper, dict) or set(wrapper) != keys
        or wrapper.get("schema") != "saea-prepared-artifact-v1"
        or wrapper.get("kind") != kind or wrapper.get("contact_class") != "model-free"
        or digest(wrapper.get("output")) != wrapper.get("output_sha256")
        or not isinstance(wrapper.get("output"), dict)
        or not isinstance(wrapper.get("inputs"), dict)
    ):
        raise CandidateExperienceMemoryError("prepared artifact identity mismatch")
    try:
        output = load_artifact(
            path, expected_sha256=expected_sha, kind=kind, inputs=wrapper["inputs"],
        )
    except PreparationError as error:
        raise CandidateExperienceMemoryError(str(error)) from error
    return output, _sha(wrapper["output_sha256"], "prepared output SHA-256"), wrapper["inputs"]


def _prepared_pinned(
    root: Path, value: object, field: str, kind: str
) -> tuple[Path, str, dict[str, object], str, dict[str, object]]:
    if not isinstance(value, Mapping) or set(value) != {
        "data_relpath", "sha256", "output_sha256"
    }:
        raise CandidateExperienceMemoryError(
            f"{field} must pin DATA path, file SHA-256 and output SHA-256"
        )
    path, file_sha = _pinned(
        root,
        {"data_relpath": value["data_relpath"], "sha256": value["sha256"]},
        field,
        "data_relpath",
    )
    output, output_sha, inputs = _prepared(path, file_sha, kind)
    if output_sha != _sha(value["output_sha256"], f"{field} output SHA-256"):
        raise CandidateExperienceMemoryError(f"{field} output SHA mismatch")
    return path, file_sha, output, output_sha, inputs


def _records(output: Mapping[str, object], construction_sha: str) -> tuple[ExperienceRecord, ...]:
    from ..core.provisional_candidate_consolidation import OUTPUT_SCHEMA as CONSOLIDATED_SCHEMA

    consolidated = output.get("schema") == CONSOLIDATED_SCHEMA
    if output.get("schema") not in {OUTPUT_SCHEMA, CONSOLIDATED_SCHEMA} or output.get("status") != "provisional":
        raise CandidateExperienceMemoryError("candidate artifact is not provisional experience")
    provenance = output.get("provenance")
    if not isinstance(provenance, Mapping) or provenance.get(
        "construction_roster_sha256"
    ) != construction_sha:
        raise CandidateExperienceMemoryError("candidate construction roster differs")
    samples = output.get("samples")
    if not isinstance(samples, list):
        raise CandidateExperienceMemoryError("candidate artifact samples must be a list")
    from .experience_consolidation import SCOPED_SNAPSHOT_SCHEMA, _load_snapshot
    snapshot = output.get("candidate_snapshot")
    scoped_records = None
    if isinstance(snapshot, Mapping) and snapshot.get("schema") == SCOPED_SNAPSHOT_SCHEMA:
        if (not consolidated or provenance.get("source_kind") != "sealed-system-semantic-batch"
                or snapshot.get("train_construction_sha256") != construction_sha):
            raise CandidateExperienceMemoryError("cumulative candidate source differs")
        try:
            scoped_records = _load_snapshot(snapshot)
        except ValueError as error:
            raise CandidateExperienceMemoryError(str(error)) from error
        if {row.get("source_sample_id") for row in samples} != set(snapshot["train_sample_ids"]):
            raise CandidateExperienceMemoryError("candidate lost cumulative construction exposure")
    found: list[ExperienceRecord] = []
    seen: set[str] = set()
    for row in samples:
        expected_keys = {"source_sample_id", "records"}
        if not consolidated:
            expected_keys.add("proposal_result_sha256")
        if not isinstance(row, Mapping) or set(row) != expected_keys:
            raise CandidateExperienceMemoryError("candidate sample row is malformed")
        sample_id = row["source_sample_id"]
        if (
            not isinstance(sample_id, str) or not sample_id.startswith("slurp:train:")
            or sample_id in seen
        ):
            raise CandidateExperienceMemoryError("candidate sample IDs must be unique")
        seen.add(sample_id)
        if not consolidated:
            _sha(row["proposal_result_sha256"], "proposal result SHA-256")
        if not isinstance(row["records"], list):
            raise CandidateExperienceMemoryError("candidate records must be a list")
        for value in row["records"]:
            try:
                record = ExperienceRecord.from_json(value)
            except (ExperienceMemoryError, TypeError, ValueError) as error:
                raise CandidateExperienceMemoryError(f"invalid candidate record: {error}") from error
            if (
                record.validation.status != "provisional"
                or (scoped_records is None and record.train_construction_sha256 != construction_sha)
                or record.source.partition_role != "train"
                or record.source.source_sample_id != sample_id
            ):
                raise CandidateExperienceMemoryError("candidate record source or status differs")
            refs = record.supporting_source_refs + record.contradicting_source_refs
            semantic = provenance.get("source_kind") == "sealed-system-semantic-batch"
            if any(ref != reward_link_hash_source_ref(ref.sha256)
                   and not (semantic and ref == system_group_hash_source_ref(ref.sha256)) for ref in refs):
                raise CandidateExperienceMemoryError("candidate source reference is not canonical")
            found.append(record)
    if scoped_records is not None and {r.record_sha256: r.as_json() for r in found} != {
            r.record_sha256: r.as_json() for r in scoped_records}:
        raise CandidateExperienceMemoryError("candidate records differ from cumulative snapshot")
    hashes = [record.record_sha256 for record in found]
    if len(hashes) != len(set(hashes)):
        raise CandidateExperienceMemoryError("candidate record hashes must be unique")
    return tuple(found)


def _source_rows(records: Sequence[ExperienceRecord]) -> list[dict[str, object]]:
    return [{
        "record_sha256": record.record_sha256,
        "source": record.source.as_json(),
        "supporting_source_refs": [ref.as_json() for ref in record.supporting_source_refs],
        "contradicting_source_refs": [ref.as_json() for ref in record.contradicting_source_refs],
    } for record in records]


def prepare_candidate_experience_source_attestation(
    *, config_path: Path, expected_config_sha256: str, data_root: Path,
    candidate_artifact_relpath: str, expected_candidate_sha256: str,
    output_relpath: str,
) -> dict[str, object]:
    """Replay the real materializer and persist compact source correspondence."""
    from ..core.provisional_candidate_materialization import (
        MaterializationError, prepare_provisional_candidates,
    )

    data_root = Path(data_root).resolve(strict=True)
    config_path = Path(config_path).resolve(strict=True)
    expected_config_sha256 = _sha(expected_config_sha256, "materialization config SHA-256")
    expected_candidate_sha256 = _sha(expected_candidate_sha256, "candidate artifact SHA-256")
    candidate_path = _confined(data_root, candidate_artifact_relpath, "candidate artifact")
    output_path = _target(data_root, output_relpath, "source attestation output")
    try:
        config_sha = hash_stable_file(config_path, "materialization config")[1]
        receipt = prepare_provisional_candidates(
            config_path=config_path,
            expected_config_sha256=expected_config_sha256,
            data_root=data_root,
        )
    except (PreparationError, MaterializationError, OSError, ValueError) as error:
        raise CandidateExperienceMemoryError(
            f"cannot reconstruct candidate authority: {error}"
        ) from error
    if config_sha != expected_config_sha256:
        raise CandidateExperienceMemoryError("materialization config SHA mismatch")
    if (
        Path(str(receipt.get("path"))).resolve() != candidate_path
        or receipt.get("sha256") != expected_candidate_sha256
    ):
        raise CandidateExperienceMemoryError("reconstructed candidate identity differs")
    output, output_sha, artifact_inputs = _prepared(
        candidate_path, expected_candidate_sha256, ARTIFACT_KIND,
    )
    provenance = output.get("provenance")
    if not isinstance(provenance, Mapping):
        raise CandidateExperienceMemoryError("candidate provenance is missing")
    construction_sha = _sha(
        provenance.get("construction_roster_sha256"), "construction roster SHA-256"
    )
    if (
        artifact_inputs.get("construction_roster_sha256") != construction_sha
        or artifact_inputs.get("materialization_config_sha256") != expected_config_sha256
    ):
        raise CandidateExperienceMemoryError("candidate preparation source inputs differ")
    records = _records(output, construction_sha)
    implementation_sha = hash_stable_file(
        Path(__file__), "source attestation implementation"
    )[1]
    inputs = {
        "candidate_artifact_sha256": expected_candidate_sha256,
        "candidate_output_sha256": output_sha,
        "materialization_config_sha256": expected_config_sha256,
        "construction_roster_sha256": construction_sha,
        "materializer_implementation_sha256": _sha(
            artifact_inputs.get("implementation_sha256"), "materializer implementation SHA-256",
        ),
        "implementation_sha256": implementation_sha,
    }
    attestation = {
        "schema": SOURCE_ATTESTATION_SCHEMA,
        "status": "source-attested",
        **inputs,
        "records": _source_rows(records),
        "interpretation": (
            "Model-free proposal source correspondence; this is not evaluation "
            "evidence or admission."
        ),
    }
    try:
        return prepare_artifact(
            output_path, kind=SOURCE_ATTESTATION_KIND, inputs=inputs,
            producer=lambda: attestation, contact_class="model-free",
        )
    except (PreparationError, OSError, TypeError, ValueError) as error:
        raise CandidateExperienceMemoryError(
            f"cannot persist source attestation: {error}"
        ) from error


def _guidance(record: ExperienceRecord, artifact_sha: str) -> ExperienceGuidance:
    return ExperienceGuidance(
        "provisional-evaluation-pack", 1, artifact_sha, record.record_id,
        record.revision, record.kind, record.diagnosis, record.guidance,
        record.limitations, record.applicability, record.record_sha256,
        record.source, record.supporting_source_refs,
        record.contradicting_source_refs, record.validation,
        record.supersedes_record_id,
    )


@dataclass(frozen=True)
class LoadedCandidateExperienceMemory:
    records: tuple[ExperienceRecord, ...]
    artifact_sha256: str
    artifact_output_sha256: str
    source_attestation_sha256: str
    evaluation_decision_sha256: str
    construction_roster_sha256: str
    evaluation_roster_sha256: str
    task_id: str
    component_tags: tuple[str, ...]
    allowed_roles: tuple[str, ...]

    def select(self, *, next_phase: str, context: object) -> ExperienceMemorySelection:
        if next_phase not in self.allowed_roles:
            raise CandidateExperienceMemoryError(
                "corrective memory called from an unauthorized role"
            )
        conditions = _project_conditions(context)
        selected = tuple(
            record for record in self.records
            if record.applicability.matches(
                task_id=self.task_id, phase=next_phase,
                component_tags=frozenset(self.component_tags),
                condition_tags=frozenset(conditions),
            )
        )
        guidance = tuple(_guidance(record, self.artifact_sha256) for record in selected)
        visible = {
            "schema": SELECTION_SCHEMA, "status": "provisional",
            "task_id": self.task_id, "next_phase": next_phase,
            "component_tags": list(self.component_tags),
            "condition_tags": list(conditions),
            "selected_records": [_visible_guidance(item) for item in guidance],
        }
        lineage = {
            **visible,
            "candidate_artifact_sha256": self.artifact_sha256,
            "candidate_output_sha256": self.artifact_output_sha256,
            "source_attestation_sha256": self.source_attestation_sha256,
            "evaluation_decision_sha256": self.evaluation_decision_sha256,
            "construction_roster_sha256": self.construction_roster_sha256,
            "evaluation_roster_sha256": self.evaluation_roster_sha256,
            "ordered_pack_record_sha256s": [
                record.record_sha256 for record in self.records
            ],
            "selected_records": [item.as_json() for item in guidance],
        }
        return ExperienceMemorySelection(visible=visible, lineage=lineage)


def _roster(
    repo_root: Path, pin: object, role: str, field: str
) -> tuple[dict[str, object], str]:
    path, sha = _pinned(repo_root, pin, field, "repo_relpath")
    try:
        value = read_roster(path)
    except (OSError, ValueError, RosterError) as error:
        raise CandidateExperienceMemoryError(f"cannot verify {field}: {error}") from error
    if (
        value.get("roster_role") != role
        or value.get("carrier_lock_key") != "slurp"
        or value.get("split_role") != "discovery"
        or any(
            not row["sample_id"].startswith("slurp:train:") for row in value["items"]
        )
    ):
        raise CandidateExperienceMemoryError(
            f"{field} must be a SLURP discovery {role} roster"
        )
    return value, sha


def load_candidate_experience_memory(
    config: Mapping[str, object], *, repo_root: Path, data_root: Path,
    carrier_lock_key: str, plan: ExecutionPlan, sample_ids: Sequence[str],
    program: object, tool_specs: Mapping[str, Mapping[str, object]],
) -> LoadedCandidateExperienceMemory | None:
    """Validate the actual plan and active roster before contact."""
    raw = config.get("candidate_experience_memory")
    if raw is None:
        return None
    if config.get("experience_memory") is not None:
        raise CandidateExperienceMemoryError(
            "candidate and admitted experience memory are mutually exclusive"
        )
    if (
        carrier_lock_key != "slurp"
        or not isinstance(raw, Mapping)
        or set(raw) != _BINDING_KEYS
    ):
        raise CandidateExperienceMemoryError(
            "candidate_experience_memory has wrong carrier or fields"
        )
    if not isinstance(plan, ExecutionPlan):
        raise CandidateExperienceMemoryError("candidate evaluation requires an actual ExecutionPlan")
    try:
        plan.validate()
    except ExecutionScopeError as error:
        raise CandidateExperienceMemoryError(str(error)) from error
    active_ids = tuple(sample_ids)
    if (
        plan.execution_profile != "bounded-discovery-probe"
        or plan.split_role != "discovery"
        or plan.carrier_lock_key != "slurp"
        or plan.attempt_id is None
        or len(active_ids) != len(set(active_ids))
        or not active_ids
        or any(
            not isinstance(item, str) or not item.startswith("slurp:train:")
            for item in active_ids
        )
        or config.get("result_kind", "task-answer") != "task-answer"
    ):
        raise CandidateExperienceMemoryError(
            "candidate evaluation requires one valid disjoint SLURP TRAIN plan"
        )
    construction, construction_sha = _roster(
        repo_root, raw["construction_roster"],
        CONSTRUCTION_ROSTER_ROLE, "construction roster",
    )
    evaluation, evaluation_sha = _roster(
        repo_root, raw["evaluation_roster"],
        EVALUATION_ROSTER_ROLE, "evaluation roster",
    )
    construction_ids = tuple(row["sample_id"] for row in construction["items"])
    evaluation_ids = tuple(row["sample_id"] for row in evaluation["items"])
    if set(construction_ids) & set(evaluation_ids):
        raise CandidateExperienceMemoryError(
            "construction and evaluation TRAIN rosters overlap"
        )
    if evaluation_ids != active_ids:
        raise CandidateExperienceMemoryError(
            "evaluation roster differs from the active sample roster"
        )
    if evaluation.get("split_identity_hash") != plan.split_identity_hash:
        raise CandidateExperienceMemoryError(
            "evaluation roster identity differs from the execution plan"
        )
    task_id = raw["task_id"]
    components = raw["component_tags"]
    roles = raw["allowed_roles"]
    if (
        not isinstance(task_id, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]*", task_id) is None
        or not isinstance(components, list) or not components
        or len(components) != len(set(components))
        or any(item not in COMPONENT_TAGS for item in components)
    ):
        raise CandidateExperienceMemoryError(
            "candidate task/component scope is invalid"
        )
    if (
        not isinstance(roles, list) or not roles
        or len(roles) != len(set(roles))
        or any(not isinstance(role, str) or not role for role in roles)
    ):
        raise CandidateExperienceMemoryError(
            "candidate memory roles must be a unique Reviewer/Planner subset"
        )
    if getattr(program, "stop_rule", None) != "native-role-episode":
        raise CandidateExperienceMemoryError(
            "candidate memory requires the native role episode"
        )
    from .native_episode_config import load_native_episode_config

    try:
        native = load_native_episode_config(config, program)
    except RailsError as error:
        raise CandidateExperienceMemoryError(str(error)) from error
    if native is None:
        raise CandidateExperienceMemoryError("candidate evaluation requires configured native roles")
    role_kinds = {role.phase_id: role.role_kind for role in native.roles}
    if any(role_kinds.get(role) not in {"reviewer", "planner"} for role in roles):
        raise CandidateExperienceMemoryError("candidate tools belong only to Reviewer or Planner")
    corrective_roles = {
        phase for phase, spec in tool_specs.items()
        if "saea-tool-corrective-memory-v1" in spec.get("allowed_tools", ())
    }
    if corrective_roles != set(roles):
        raise CandidateExperienceMemoryError(
            "candidate roles differ from corrective-memory tool authority"
        )
    artifact_path, artifact_sha, artifact_output, artifact_output_sha, artifact_inputs = (
        _prepared_pinned(
            data_root, raw["artifact"], "candidate artifact", ARTIFACT_KIND
        )
    )
    provenance = artifact_output.get("provenance")
    if not isinstance(provenance, Mapping):
        raise CandidateExperienceMemoryError("candidate provenance is missing")
    if _sha(
        provenance.get("construction_roster_sha256"),
        "candidate construction roster",
    ) != construction_sha:
        raise CandidateExperienceMemoryError(
            "candidate artifact names another construction roster"
        )
    if (
        artifact_inputs.get("construction_roster_sha256") != construction_sha
        or artifact_inputs.get("materialization_config_sha256")
        != provenance.get("materialization_config_sha256")
        or {row.get("source_sample_id") for row in artifact_output.get("samples", ())}
        != set(construction_ids)
    ):
        raise CandidateExperienceMemoryError("candidate preparation differs from its construction roster")
    all_records = _records(artifact_output, construction_sha)
    by_hash = {record.record_sha256: record for record in all_records}
    ordered = raw["ordered_record_sha256s"]
    if (
        not isinstance(ordered, list)
        or len(ordered) > MAX_RUNTIME_RECORDS
        or len(ordered) != len(set(ordered))
    ):
        raise CandidateExperienceMemoryError(
            "candidate pack must be unique, ordered and within the runtime bound"
        )
    ordered_hashes = tuple(
        _sha(value, "candidate pack record SHA-256") for value in ordered
    )
    if any(value not in by_hash for value in ordered_hashes):
        raise CandidateExperienceMemoryError("candidate pack names a foreign record")
    selected = tuple(by_hash[value] for value in ordered_hashes)
    construction_id_set = set(construction_ids)
    if any(
        record.source.source_sample_id not in construction_id_set
        for record in all_records
    ):
        raise CandidateExperienceMemoryError(
            "candidate pack contains a foreign construction source"
        )
    for record in selected:
        if (
            task_id not in record.applicability.task_ids
            or not set(record.applicability.component_tags) <= set(components)
            or not set(record.applicability.phases) <= set(roles)
            or not (
                set(record.applicability.required_conditions)
                | set(record.applicability.excluded_conditions)
            ) <= PROJECTED_CONDITION_TAGS
        ):
            raise CandidateExperienceMemoryError(
                "candidate applicability is outside the registered scope"
            )
    attestation_path, attestation_sha, attestation, _, attestation_inputs = _prepared_pinned(
        data_root,
        raw["source_attestation"],
        "source attestation",
        SOURCE_ATTESTATION_KIND,
    )
    expected_attestation = {
        "schema": SOURCE_ATTESTATION_SCHEMA,
        "status": "source-attested",
        "candidate_artifact_sha256": artifact_sha,
        "candidate_output_sha256": artifact_output_sha,
        "materialization_config_sha256":
            provenance["materialization_config_sha256"],
        "construction_roster_sha256": construction_sha,
        "materializer_implementation_sha256": _sha(
            artifact_inputs.get("implementation_sha256"), "materializer implementation SHA-256",
        ),
        "implementation_sha256": attestation.get("implementation_sha256"),
        "records": _source_rows(all_records),
        "interpretation": (
            "Model-free proposal source correspondence; this is not evaluation "
            "evidence or admission."
        ),
    }
    implementation_sha = _sha(
        expected_attestation["implementation_sha256"],
        "attestation implementation SHA-256",
    )
    if implementation_sha != hash_stable_file(
        Path(__file__), "source attestation implementation"
    )[1]:
        raise CandidateExperienceMemoryError(
            "source attestation implementation identity differs"
        )
    expected_inputs = {
        key: expected_attestation[key] for key in (
            "candidate_artifact_sha256", "candidate_output_sha256",
            "materialization_config_sha256", "construction_roster_sha256",
            "materializer_implementation_sha256", "implementation_sha256",
        )
    }
    if attestation != expected_attestation or attestation_inputs != expected_inputs:
        raise CandidateExperienceMemoryError(
            "source attestation does not correspond to the candidate artifact"
        )
    decision_path, decision_sha = _pinned(
        repo_root, raw["evaluation_decision"],
        "evaluation decision", "repo_relpath",
    )
    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CandidateExperienceMemoryError(
            f"cannot read evaluation decision: {error}"
        ) from error
    expected_decision = {
        "schema": DECISION_SCHEMA,
        "action": "evaluate-provisional-pack",
        "admission": "none",
        "run_id": plan.run_id,
        "attempt_id": plan.attempt_id,
        "candidate_artifact_sha256": artifact_sha,
        "candidate_output_sha256": artifact_output_sha,
        "source_attestation_sha256": attestation_sha,
        "construction_roster_sha256": construction_sha,
        "evaluation_roster_sha256": evaluation_sha,
        "ordered_record_sha256s": list(ordered_hashes),
        "task_id": task_id,
        "component_tags": list(components),
        "allowed_roles": list(roles),
    }
    if decision != expected_decision:
        raise CandidateExperienceMemoryError(
            "evaluation decision does not bind this actual plan and candidate pack"
        )
    return LoadedCandidateExperienceMemory(
        selected, artifact_sha, artifact_output_sha, attestation_sha,
        decision_sha, construction_sha, evaluation_sha, task_id,
        tuple(components), tuple(roles),
    )
