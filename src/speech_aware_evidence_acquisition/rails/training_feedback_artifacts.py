"""Typed, source-bound provisional guidance proposed from TRAIN feedback.

Semantic conditions belong in the natural-language guidance. Applicability
contains only structural tags that the shared runtime can actually project;
this artifact is never an admitted experience-memory record.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from ..core.preparation import SCHEMA as PREPARED_ARTIFACT_SCHEMA, digest, hash_stable_file
from .experience_memory import Applicability, ExperienceMemoryError
from .experience_memory_runtime import COMPONENT_TAGS, PROJECTED_CONDITION_TAGS
from .prepared_feedback import PreparedFeedbackError, reject_non_latin_scripts
from .training_proposal_context import TRAINING_PROPOSAL_CONTEXT_SCHEMA

TRAINING_FEEDBACK_CONTENT_ID = "training-feedback-proposal-v1"
TRAINING_FEEDBACK_STATUS = "provisional"
_KINDS = frozenset({"corrective-experience", "conditional-rule"})
_DEFAULT_MAX_PROPOSALS = 2
_MAX_PROPOSALS = 4
# Compact character ceilings for proposal records. They constrain structure;
# the shared per-wave request fitter must still prove the prospective model's
# actual token/output envelope before any contact.
_DEFAULT_DIAGNOSIS_CHARS = 300
_DEFAULT_GUIDANCE_CHARS = 600
_DEFAULT_LIMITATION_CHARS = 160
_DEFAULT_LIMITATIONS = 3


class TrainingFeedbackArtifactError(ValueError):
    """A provisional TRAIN guidance contract or response is invalid."""


def _positive_bound(value: object, field: str, *, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise TrainingFeedbackArtifactError(
            f"{field} must be an integer from 1 to {maximum}"
        )
    return value


def _string_set(value: object, field: str) -> frozenset[str]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item for item in value)
        or len(value) != len(set(value))
    ):
        raise TrainingFeedbackArtifactError(f"{field} must be a non-empty unique text list")
    return frozenset(value)


def _prepared_contexts(
    contract: Mapping[str, object], data_root: Path
) -> tuple[dict[str, frozenset[str]], str]:
    pin = contract.get("prepared_contexts")
    if not isinstance(pin, Mapping) or set(pin) != {
        "data_relpath", "sha256", "output_sha256"
    }:
        raise TrainingFeedbackArtifactError(
            "prepared_contexts must pin data_relpath, sha256 and output_sha256"
        )
    relpath = pin.get("data_relpath")
    if not isinstance(relpath, str) or not relpath:
        raise TrainingFeedbackArtifactError("prepared_contexts data_relpath must be text")
    pure = PurePosixPath(relpath)
    if pure.is_absolute() or "\\" in relpath or ":" in relpath or any(
        part in {"", ".", ".."} for part in relpath.split("/")
    ):
        raise TrainingFeedbackArtifactError(
            "prepared_contexts data_relpath must be canonical relative POSIX"
        )
    root = Path(data_root).resolve()
    path = (root / relpath).resolve()
    if not path.is_relative_to(root):
        raise TrainingFeedbackArtifactError("prepared_contexts escapes data root")
    try:
        _size, actual_sha, fingerprint = hash_stable_file(path, "prepared contexts")
        raw = path.read_bytes()
        _size, after_sha, after_fingerprint = hash_stable_file(
            path, "prepared contexts after read"
        )
        document = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise TrainingFeedbackArtifactError(f"cannot read prepared_contexts: {error}") from error
    expected_sha = pin.get("sha256")
    expected_output_sha = pin.get("output_sha256")
    if (
        not isinstance(expected_sha, str)
        or hashlib.sha256(raw).hexdigest() != expected_sha
        or actual_sha != expected_sha
        or after_sha != actual_sha
        or after_fingerprint != fingerprint
    ):
        raise TrainingFeedbackArtifactError("prepared_contexts file SHA mismatch")
    if (
        not isinstance(document, Mapping)
        or set(document) != {
            "schema", "kind", "inputs", "contact_class", "output", "output_sha256"
        }
        or document.get("schema") != PREPARED_ARTIFACT_SCHEMA
        or document.get("kind") != "training-proposal-contexts"
        or document.get("contact_class") != "model-free"
        or document.get("output_sha256") != expected_output_sha
        or digest(document.get("output")) != expected_output_sha
    ):
        raise TrainingFeedbackArtifactError("prepared_contexts artifact identity differs")
    output = document.get("output")
    if (
        not isinstance(output, Mapping)
        or output.get("schema") != TRAINING_PROPOSAL_CONTEXT_SCHEMA
        or output.get("status") != "source-verified"
        or output.get("role") != "training-feedback-proposal"
        or not isinstance(output.get("contexts"), list)
    ):
        raise TrainingFeedbackArtifactError("prepared_contexts output authority differs")
    options: dict[str, frozenset[str]] = {}
    for context in output["contexts"]:
        if not isinstance(context, Mapping):
            raise TrainingFeedbackArtifactError("prepared context is malformed")
        sample_id = context.get("source_sample_id")
        bindings = context.get("candidate_bindings")
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or sample_id in options
            or not isinstance(bindings, list)
            or not bindings
        ):
            raise TrainingFeedbackArtifactError("prepared context sample binding is malformed")
        labels = []
        for index, binding in enumerate(bindings, 1):
            if not isinstance(binding, Mapping) or binding.get("label") != f"option-{index}":
                raise TrainingFeedbackArtifactError(
                    "prepared context option labels are not canonical"
                )
            labels.append(binding["label"])
        options[sample_id] = frozenset(labels)
    if not options:
        raise TrainingFeedbackArtifactError("prepared_contexts contains no samples")
    return options, expected_sha


@dataclass(frozen=True)
class TrainingFeedbackArtifactValidator:
    options_by_sample: Mapping[str, frozenset[str]]
    source_sha256: str
    max_proposals: int
    max_diagnosis_chars: int
    max_guidance_chars: int
    max_limitation_chars: int
    max_limitations: int
    max_option_refs: int
    allowed_task_ids: frozenset[str]
    allowed_roles: frozenset[str]
    allowed_component_tags: frozenset[str]

    def _text(self, value: object, field: str, maximum: int) -> str:
        if not isinstance(value, str) or not value.strip() or len(value) > maximum:
            raise TrainingFeedbackArtifactError(
                f"{field} must be non-empty text of at most {maximum} characters"
            )
        return value

    def _options(
        self, value: object, field: str, legal: frozenset[str], *, required: bool = False
    ) -> tuple[str, ...]:
        if (
            not isinstance(value, list)
            or len(value) > self.max_option_refs
            or any(not isinstance(item, str) or item not in legal for item in value)
            or len(value) != len(set(value))
            or (required and not value)
        ):
            raise TrainingFeedbackArtifactError(
                f"{field} must contain unique options from this sample"
            )
        return tuple(value)

    def canonicalize(self, raw_response: str, *, sample_id: str) -> str:
        try:
            document = json.loads(raw_response)
        except (TypeError, json.JSONDecodeError) as error:
            raise TrainingFeedbackArtifactError("TRAIN proposal response must be JSON") from error
        if not isinstance(document, Mapping) or set(document) != {"status", "proposals"}:
            raise TrainingFeedbackArtifactError(
                "TRAIN proposal response must contain exactly status and proposals"
            )
        if document.get("status") != TRAINING_FEEDBACK_STATUS:
            raise TrainingFeedbackArtifactError("TRAIN proposal status must be provisional")
        proposals = document.get("proposals")
        if not isinstance(proposals, list) or len(proposals) > self.max_proposals:
            raise TrainingFeedbackArtifactError(
                f"proposals must contain from 0 to {self.max_proposals} items"
            )
        legal = self.options_by_sample.get(sample_id)
        if legal is None:
            raise TrainingFeedbackArtifactError("sample is absent from prepared_contexts")
        canonical_proposals = []
        keys = {
            "kind", "diagnosis", "guidance", "limitations", "applicability",
            "primary_option", "supporting_options", "contradicting_options",
        }
        for index, proposal in enumerate(proposals):
            if not isinstance(proposal, Mapping) or set(proposal) != keys:
                raise TrainingFeedbackArtifactError(f"proposal {index} has wrong fields")
            kind = proposal.get("kind")
            if kind not in _KINDS:
                raise TrainingFeedbackArtifactError(f"proposal {index} kind is invalid")
            diagnosis = self._text(
                proposal.get("diagnosis"), f"proposal {index} diagnosis", self.max_diagnosis_chars
            )
            guidance = self._text(
                proposal.get("guidance"), f"proposal {index} guidance", self.max_guidance_chars
            )
            limitations_raw = proposal.get("limitations")
            if not isinstance(limitations_raw, list) or len(limitations_raw) > self.max_limitations:
                raise TrainingFeedbackArtifactError(f"proposal {index} limitations exceed bounds")
            limitations = [
                self._text(item, f"proposal {index} limitation", self.max_limitation_chars)
                for item in limitations_raw
            ]
            if len(limitations) != len(set(limitations)):
                raise TrainingFeedbackArtifactError(f"proposal {index} limitations must be unique")
            try:
                applicability = Applicability.from_json(proposal.get("applicability"))
            except ExperienceMemoryError as error:
                raise TrainingFeedbackArtifactError(str(error)) from error
            if (
                not set(applicability.task_ids) <= self.allowed_task_ids
                or not set(applicability.phases) <= self.allowed_roles
                or not set(applicability.component_tags) <= self.allowed_component_tags
                or not set(applicability.component_tags) <= COMPONENT_TAGS
                or not set(applicability.required_conditions) <= PROJECTED_CONDITION_TAGS
                or not set(applicability.excluded_conditions) <= PROJECTED_CONDITION_TAGS
            ):
                raise TrainingFeedbackArtifactError(
                    "applicability exceeds configured executable runtime scope"
                )
            primary = proposal.get("primary_option")
            if not isinstance(primary, str) or primary not in legal:
                raise TrainingFeedbackArtifactError(
                    f"proposal {index} primary_option is not an option for this sample"
                )
            supporting = self._options(
                proposal.get("supporting_options"),
                f"proposal {index} supporting_options", legal, required=True,
            )
            contradicting = self._options(
                proposal.get("contradicting_options"),
                f"proposal {index} contradicting_options", legal,
            )
            if primary not in supporting or set(supporting) & set(contradicting):
                raise TrainingFeedbackArtifactError(
                    f"proposal {index} option roles are inconsistent"
                )
            try:
                reject_non_latin_scripts(proposal)
            except PreparedFeedbackError as error:
                raise TrainingFeedbackArtifactError(str(error)) from error
            if sample_id in json.dumps(proposal, ensure_ascii=False):
                raise TrainingFeedbackArtifactError(
                    f"proposal {index} exposes the current sample ID"
                )
            canonical_proposals.append({
                "kind": kind,
                "diagnosis": diagnosis,
                "guidance": guidance,
                "limitations": limitations,
                "applicability": applicability.as_json(),
                "primary_option": primary,
                "supporting_options": list(supporting),
                "contradicting_options": list(contradicting),
            })
        return json.dumps(
            {"status": TRAINING_FEEDBACK_STATUS, "proposals": canonical_proposals},
            ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False,
        )


def build_training_feedback_artifact_validator(
    contract: Mapping[str, object], *, data_root: Path
) -> TrainingFeedbackArtifactValidator:
    required = {"id", "prepared_contexts", "applicability"}
    optional = {
        "max_proposals", "max_diagnosis_chars", "max_guidance_chars",
        "max_limitation_chars", "max_limitations", "max_option_refs",
    }
    if not isinstance(contract, Mapping) or not required <= set(contract) or not set(contract) <= required | optional:
        raise TrainingFeedbackArtifactError("TRAIN proposal content contract has wrong fields")
    if contract.get("id") != TRAINING_FEEDBACK_CONTENT_ID:
        raise TrainingFeedbackArtifactError("TRAIN proposal content contract id is invalid")
    options, source_sha = _prepared_contexts(contract, Path(data_root))
    return training_feedback_validator_for_options(contract, options, source_sha)


def training_feedback_validator_for_options(contract, options, source_sha):
    """Use the same typed-guidance rules after an authenticated source reader binds labels."""
    scope = contract.get("applicability")
    if not isinstance(scope, Mapping) or set(scope) != {
        "allowed_task_ids", "allowed_roles", "allowed_component_tags"
    }:
        raise TrainingFeedbackArtifactError("configured applicability has wrong fields")
    max_proposals = _positive_bound(
        contract.get("max_proposals", _DEFAULT_MAX_PROPOSALS),
        "max_proposals", maximum=_MAX_PROPOSALS,
    )
    allowed_components = _string_set(scope["allowed_component_tags"], "allowed_component_tags")
    if not allowed_components <= COMPONENT_TAGS:
        raise TrainingFeedbackArtifactError("allowed_component_tags contains an unknown component")
    return TrainingFeedbackArtifactValidator(
        options_by_sample=options,
        source_sha256=source_sha,
        max_proposals=max_proposals,
        max_diagnosis_chars=_positive_bound(contract.get("max_diagnosis_chars", _DEFAULT_DIAGNOSIS_CHARS), "max_diagnosis_chars", maximum=8000),
        max_guidance_chars=_positive_bound(contract.get("max_guidance_chars", _DEFAULT_GUIDANCE_CHARS), "max_guidance_chars", maximum=12000),
        max_limitation_chars=_positive_bound(contract.get("max_limitation_chars", _DEFAULT_LIMITATION_CHARS), "max_limitation_chars", maximum=4000),
        max_limitations=_positive_bound(contract.get("max_limitations", _DEFAULT_LIMITATIONS), "max_limitations", maximum=16),
        max_option_refs=_positive_bound(contract.get("max_option_refs", 4), "max_option_refs", maximum=16),
        allowed_task_ids=_string_set(scope["allowed_task_ids"], "allowed_task_ids"),
        allowed_roles=_string_set(scope["allowed_roles"], "allowed_roles"),
        allowed_component_tags=allowed_components,
    )


def training_feedback_proposal_schema(validator):
    """Share exact typed guidance constraints across proposal and batch formats."""
    legal_options = sorted(
        set().union(*(set(labels) for labels in validator.options_by_sample.values()))
    )
    option = {"type": "string", "enum": legal_options}
    applicability = {
        "type": "object", "additionalProperties": False,
        "required": ["task_ids", "phases", "component_tags", "required_conditions", "excluded_conditions"],
        "properties": {
            "task_ids": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "enum": sorted(validator.allowed_task_ids)}},
            "phases": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "enum": sorted(validator.allowed_roles)}},
            "component_tags": {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "enum": sorted(validator.allowed_component_tags)}},
            "required_conditions": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": sorted(PROJECTED_CONDITION_TAGS)}},
            "excluded_conditions": {"type": "array", "uniqueItems": True, "items": {"type": "string", "enum": sorted(PROJECTED_CONDITION_TAGS)}},
        },
    }
    proposal = {
        "type": "object", "additionalProperties": False,
        "required": ["kind", "diagnosis", "guidance", "limitations", "applicability", "primary_option", "supporting_options", "contradicting_options"],
        "properties": {
            "kind": {"type": "string", "enum": sorted(_KINDS)},
            "diagnosis": {"type": "string", "minLength": 1, "maxLength": validator.max_diagnosis_chars},
            "guidance": {"type": "string", "minLength": 1, "maxLength": validator.max_guidance_chars},
            "limitations": {"type": "array", "uniqueItems": True, "maxItems": validator.max_limitations, "items": {"type": "string", "minLength": 1, "maxLength": validator.max_limitation_chars}},
            "applicability": applicability,
            "primary_option": option,
            "supporting_options": {"type": "array", "minItems": 1, "maxItems": validator.max_option_refs, "uniqueItems": True, "items": option},
            "contradicting_options": {"type": "array", "maxItems": validator.max_option_refs, "uniqueItems": True, "items": option},
        },
    }
    return proposal


def training_feedback_response_format(
    _lock: Mapping[str, object], root: Path, **params: object
) -> Mapping[str, object]:
    validator = build_training_feedback_artifact_validator(params, data_root=root)
    proposal = training_feedback_proposal_schema(validator)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "training_feedback_proposals", "strict": True,
            "schema": {
                "type": "object", "additionalProperties": False,
                "required": ["status", "proposals"],
                "properties": {
                    "status": {"type": "string", "const": TRAINING_FEEDBACK_STATUS},
                    "proposals": {"type": "array", "maxItems": validator.max_proposals, "items": proposal},
                },
            },
        },
    }


def artifact_content_source_pin(contract: Mapping[str, object]) -> Mapping[str, object]:
    """Return the registered content source pin without carrier-specific branching."""

    content_id = contract.get("id")
    if content_id == TRAINING_FEEDBACK_CONTENT_ID:
        pin = contract.get("prepared_contexts")
    elif content_id == "slurp-intent-hypotheses-v1":
        pin = contract.get("source_catalog")
    else:
        raise TrainingFeedbackArtifactError("unknown artifact content contract id")
    if not isinstance(pin, Mapping):
        raise TrainingFeedbackArtifactError("artifact content source pin is malformed")
    return pin


__all__ = [
    "TRAINING_FEEDBACK_CONTENT_ID",
    "TRAINING_FEEDBACK_STATUS",
    "TrainingFeedbackArtifactError",
    "TrainingFeedbackArtifactValidator",
    "artifact_content_source_pin",
    "build_training_feedback_artifact_validator",
    "training_feedback_response_format",
]
