"""Load verified TRAIN proposal contexts as initial, non-retrieval ORG state.

The loader rebuilds source authority before accepting a prepared artifact.  It
never writes, scores, calls a model, or converts this provisional material into
knowledge SUPPLY.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ..core.preparation import PreparationError, hash_stable_file, load_artifact
from .hashing import content_hash
from .training_proposal_context import (
    TrainingProposalContextError,
    build_training_proposal_contexts,
    training_proposal_context_preparation_inputs,
)

PREPARED_FEEDBACK_SCHEMA = "saea-prepared-training-feedback-v1"
PREPARED_FEEDBACK_STATE_VERSION = "saea-prepared-feedback-state-v1"
PREPARED_FEEDBACK_STATE_KIND = "prepared-training-feedback"
PREPARED_FEEDBACK_RECEIPT_SCHEMA = "saea-prepared-training-feedback-receipt-v1"


class PreparedFeedbackError(ValueError):
    """A prepared feedback seed is not an authorized artifact input."""


def _sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PreparedFeedbackError(f"{field} must be a lowercase SHA256")
    return value


def _canonical_context(model_context: Mapping[str, object]) -> str:
    _reject_non_latin_scripts(model_context)
    try:
        return json.dumps(
            model_context, ensure_ascii=True, sort_keys=True,
            separators=(",", ":"), allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise PreparedFeedbackError("model context is not canonical JSON") from error


def reject_non_latin_scripts(value: object) -> None:
    """Reject alphabetic non-Latin script; this is not language detection."""

    if isinstance(value, str):
        for character in value:
            if character.isalpha() and ord(character) > 127:
                if "LATIN" not in unicodedata.name(character, ""):
                    raise PreparedFeedbackError(
                        "declared English content has a non-Latin alphabetic script"
                    )
        return
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if not isinstance(key, str):
                raise PreparedFeedbackError("model context keys must be text")
            reject_non_latin_scripts(key)
            reject_non_latin_scripts(nested)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for nested in value:
            reject_non_latin_scripts(nested)
        return
    if value is None or isinstance(value, (bool, int, float)):
        return
    raise PreparedFeedbackError("model context contains a non-JSON value")


_reject_non_latin_scripts = reject_non_latin_scripts


@dataclass(frozen=True)
class PreparedFeedbackStateArtifact:
    """A verified prior-execution context for one initial ORG history turn."""

    state_id: str
    state_kind: str
    content: str
    cited_value_ids: tuple[str, ...]
    prepared_artifact_sha256: str
    source_feedback_sha256: str
    construction_roster_sha256: str
    model_context_sha256: str
    prepared_feedback_state_version: str = PREPARED_FEEDBACK_STATE_VERSION

    def validate(self) -> "PreparedFeedbackStateArtifact":
        if not isinstance(self.state_id, str) or not self.state_id:
            raise PreparedFeedbackError("state_id must be nonempty text")
        if self.state_kind != PREPARED_FEEDBACK_STATE_KIND:
            raise PreparedFeedbackError("state_kind must be prepared-training-feedback")
        if not isinstance(self.content, str) or not self.content:
            raise PreparedFeedbackError("content must be nonempty text")
        if self.cited_value_ids != ():
            raise PreparedFeedbackError("prepared feedback may not cite knowledge values")
        for field in (
            "prepared_artifact_sha256",
            "source_feedback_sha256",
            "construction_roster_sha256",
            "model_context_sha256",
        ):
            _sha256(getattr(self, field), field=field)
        if self.prepared_feedback_state_version != PREPARED_FEEDBACK_STATE_VERSION:
            raise PreparedFeedbackError("unexpected prepared feedback state version")
        if self.state_id != _state_id(
            prepared_artifact_sha256=self.prepared_artifact_sha256,
            source_feedback_sha256=self.source_feedback_sha256,
            construction_roster_sha256=self.construction_roster_sha256,
            model_context_sha256=self.model_context_sha256,
        ):
            raise PreparedFeedbackError("state_id differs from prepared feedback provenance")
        try:
            model_context = json.loads(self.content)
        except (TypeError, json.JSONDecodeError) as error:
            raise PreparedFeedbackError("content must be canonical model-context JSON") from error
        if not isinstance(model_context, Mapping):
            raise PreparedFeedbackError("content must encode a model-context object")
        if self.content != _canonical_context(model_context):
            raise PreparedFeedbackError("content is not canonical model-context JSON")
        if content_hash(model_context) != self.model_context_sha256:
            raise PreparedFeedbackError("model context content hash differs")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "prepared_feedback_state_version": self.prepared_feedback_state_version,
            "state_id": self.state_id,
            "state_kind": self.state_kind,
            "content": self.content,
            "cited_value_ids": [],
            "prepared_artifact_sha256": self.prepared_artifact_sha256,
            "source_feedback_sha256": self.source_feedback_sha256,
            "construction_roster_sha256": self.construction_roster_sha256,
            "model_context_sha256": self.model_context_sha256,
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())

    @classmethod
    def from_json(
        cls, document: Mapping[str, object]
    ) -> "PreparedFeedbackStateArtifact":
        required = {
            "prepared_feedback_state_version",
            "state_id",
            "state_kind",
            "content",
            "cited_value_ids",
            "prepared_artifact_sha256",
            "source_feedback_sha256",
            "construction_roster_sha256",
            "model_context_sha256",
        }
        if not isinstance(document, Mapping) or set(document) != required:
            raise PreparedFeedbackError("prepared feedback state has wrong fields")
        cited = document["cited_value_ids"]
        if cited != []:
            raise PreparedFeedbackError("prepared feedback may not cite knowledge values")
        return cls(
            state_id=document["state_id"],
            state_kind=document["state_kind"],
            content=document["content"],
            cited_value_ids=(),
            prepared_artifact_sha256=document["prepared_artifact_sha256"],
            source_feedback_sha256=document["source_feedback_sha256"],
            construction_roster_sha256=document["construction_roster_sha256"],
            model_context_sha256=document["model_context_sha256"],
            prepared_feedback_state_version=document["prepared_feedback_state_version"],
        ).validate()


def _resolve_data_path(value: object, *, data_root: Path, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise PreparedFeedbackError(f"{field} must be a nonempty DATA-relative path")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise PreparedFeedbackError(f"{field} must be a confined DATA-relative path")
    root = data_root.resolve()
    resolved = (root / relative).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise PreparedFeedbackError(f"{field} escapes DATA root") from error
    return resolved


def _read_pinned_json(pin: object, *, data_root: Path, field: str) -> tuple[object, str]:
    if not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}:
        raise PreparedFeedbackError(f"{field} pin has wrong fields")
    path = _resolve_data_path(pin["relpath"], data_root=data_root, field=field)
    expected = _sha256(pin["sha256"], field=f"{field}.sha256")
    try:
        _size, before, fingerprint = hash_stable_file(path, field)
        raw = path.read_bytes()
        _size, after, after_fingerprint = hash_stable_file(path, field + " after read")
    except (OSError, PreparationError) as error:
        raise PreparedFeedbackError(f"cannot read {field}: {error}") from error
    if (
        before != expected
        or hashlib.sha256(raw).hexdigest() != expected
        or after != before
        or after_fingerprint != fingerprint
    ):
        raise PreparedFeedbackError(f"{field} changed or has a wrong hash")
    try:
        return json.loads(raw), expected
    except (UnicodeError, json.JSONDecodeError) as error:
        raise PreparedFeedbackError(f"{field} is not JSON") from error


def _resolve_binding_paths(value: object, *, data_root: Path) -> object:
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, nested in value.items():
            if not isinstance(key, str):
                raise PreparedFeedbackError("source binding keys must be text")
            if key == "path":
                result[key] = str(
                    _resolve_data_path(nested, data_root=data_root, field="source binding path")
                )
            else:
                result[key] = _resolve_binding_paths(nested, data_root=data_root)
        return result
    if isinstance(value, list):
        return [_resolve_binding_paths(nested, data_root=data_root) for nested in value]
    return value


def _validate_spec(spec: object) -> tuple[Mapping[str, object], Mapping[str, object], int]:
    if not isinstance(spec, Mapping) or set(spec) != {
        "schema", "artifact", "source_bindings", "language", "max_context_bytes",
    }:
        raise PreparedFeedbackError("prepared feedback spec has wrong fields")
    if spec["schema"] != PREPARED_FEEDBACK_SCHEMA:
        raise PreparedFeedbackError("prepared feedback spec schema differs")
    if spec["language"] != "en":
        raise PreparedFeedbackError("prepared feedback must declare English")
    maximum = spec["max_context_bytes"]
    if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0:
        raise PreparedFeedbackError("max_context_bytes must be a positive integer")
    return spec["artifact"], spec["source_bindings"], maximum


def _state_id(
    *, prepared_artifact_sha256: str, source_feedback_sha256: str,
    construction_roster_sha256: str, model_context_sha256: str,
) -> str:
    identity = {
        "prepared_artifact_sha256": prepared_artifact_sha256,
        "source_feedback_sha256": source_feedback_sha256,
        "construction_roster_sha256": construction_roster_sha256,
        "model_context_sha256": model_context_sha256,
    }
    return "prepared-feedback:" + content_hash(identity)


def load_prepared_feedback(
    spec: object,
    *,
    repo_root: Path,
    data_root: Path,
    sample_ids: Sequence[str],
    construction_roster_sha256: str,
    result_kind: str,
    artifact_role: str,
) -> tuple[dict[str, PreparedFeedbackStateArtifact], dict[str, object]]:
    """Return ordered initial ORG states and a custody receipt without writing."""

    del repo_root  # The contract deliberately confines every configured file to DATA.
    if result_kind != "artifact" or artifact_role != "training-feedback-proposal":
        raise PreparedFeedbackError("prepared feedback is limited to its artifact role")
    active_ids = tuple(sample_ids)
    if (
        not active_ids
        or any(not isinstance(sample_id, str) or not sample_id for sample_id in active_ids)
        or len(set(active_ids)) != len(active_ids)
    ):
        raise PreparedFeedbackError("active construction cohort must have unique sample IDs")
    roster_sha = _sha256(construction_roster_sha256, field="construction_roster_sha256")
    if isinstance(spec, Mapping) and spec.get("schema") == "saea-prepared-system-summary-v1":
        from .system_summary_context import load_system_summary_feedback

        return load_system_summary_feedback(
            spec, data_root=Path(data_root), sample_ids=active_ids,
            construction_roster_sha256=roster_sha,
        )
    if isinstance(spec, Mapping) and spec.get("schema") == "saea-prepared-system-comparison-v1":
        from .system_comparison_context import load_system_comparison_feedback

        return load_system_comparison_feedback(
            spec, data_root=Path(data_root), sample_ids=active_ids,
            construction_roster_sha256=roster_sha,
        )
    if isinstance(spec, Mapping) and spec.get("schema") == "saea-prepared-system-group-update-v1":
        from .system_group_update_context import load_system_group_update
        return load_system_group_update(
            spec, data_root=Path(data_root), sample_ids=active_ids,
            construction_roster_sha256=roster_sha)
    if isinstance(spec, Mapping) and spec.get("schema") == "saea-prepared-system-batch-update-v1":
        from .system_batch_update_context import load_system_batch_update
        return load_system_batch_update(
            spec, data_root=Path(data_root), sample_ids=active_ids,
            construction_roster_sha256=roster_sha)
    if isinstance(spec, Mapping) and spec.get("schema") == "saea-prepared-knowledge-edit-v1":
        from .knowledge_edit_context import load_knowledge_edit_feedback
        return load_knowledge_edit_feedback(
            spec, data_root=Path(data_root), sample_ids=active_ids,
            construction_roster_sha256=roster_sha)
    artifact_pin, source_pin, maximum = _validate_spec(spec)
    source_bindings, source_bindings_sha256 = _read_pinned_json(
        source_pin, data_root=Path(data_root), field="source_bindings"
    )
    if not isinstance(source_bindings, list):
        raise PreparedFeedbackError("source_bindings must contain the original binding list")
    resolved_bindings = _resolve_binding_paths(source_bindings, data_root=Path(data_root))
    try:
        rebuilt = build_training_proposal_contexts(resolved_bindings)
        inputs = training_proposal_context_preparation_inputs(rebuilt)
        prepared, prepared_sha256 = _read_pinned_json(
            artifact_pin, data_root=Path(data_root), field="artifact"
        )
        if not isinstance(prepared, Mapping) or prepared.get("contact_class") != "model-free":
            raise PreparedFeedbackError("prepared proposal artifact must be model-free")
        artifact_path = _resolve_data_path(
            artifact_pin["relpath"], data_root=Path(data_root), field="artifact"
        )
        output = load_artifact(
            artifact_path,
            expected_sha256=prepared_sha256,
            kind="training-proposal-contexts",
            inputs=inputs,
        )
    except (TrainingProposalContextError, PreparationError, OSError, TypeError, ValueError) as error:
        if isinstance(error, PreparedFeedbackError):
            raise
        raise PreparedFeedbackError(f"cannot verify prepared feedback: {error}") from error
    if output != rebuilt:
        raise PreparedFeedbackError("prepared proposal output differs from rebuilt document")
    if (
        rebuilt.get("schema") != "saea-training-proposal-contexts-v2"
        or rebuilt.get("status") != "source-verified"
        or rebuilt.get("role") != "training-feedback-proposal"
        or rebuilt.get("construction_roster_sha256") != roster_sha
    ):
        raise PreparedFeedbackError("prepared proposal document has wrong authority")
    contexts = rebuilt.get("contexts")
    if not isinstance(contexts, list):
        raise PreparedFeedbackError("prepared proposal contexts are missing")
    by_sample: dict[str, Mapping[str, object]] = {}
    for context in contexts:
        if not isinstance(context, Mapping):
            raise PreparedFeedbackError("prepared proposal context is malformed")
        sample_id = context.get("source_sample_id")
        if not isinstance(sample_id, str) or sample_id in by_sample:
            raise PreparedFeedbackError("prepared proposal context has duplicate sample IDs")
        bindings = context.get("candidate_bindings")
        if not isinstance(bindings, list) or not bindings:
            raise PreparedFeedbackError("prepared proposal context has no candidate bindings")
        if any(
            not isinstance(binding, Mapping)
            or not isinstance(binding.get("source"), Mapping)
            or binding["source"].get("source_sample_id") != sample_id
            or binding["source"].get("partition_role") != "train"
            for binding in bindings
        ):
            raise PreparedFeedbackError("prepared proposal context is not TRAIN-only")
        by_sample[sample_id] = context
    if set(by_sample) != set(active_ids) or len(by_sample) != len(active_ids):
        raise PreparedFeedbackError("prepared proposal contexts differ from active cohort")
    return states_from_contexts(
        by_sample, active_ids=active_ids, prepared_sha256=prepared_sha256,
        source_bindings_sha256=source_bindings_sha256, roster_sha=roster_sha, maximum=maximum,
    )


def states_from_contexts(
    by_sample, *, active_ids, prepared_sha256, source_bindings_sha256, roster_sha, maximum,
):
    """Serialize already source-verified contexts through the common ORG state."""
    if set(by_sample) != set(active_ids) or len(by_sample) != len(active_ids):
        raise PreparedFeedbackError("prepared contexts differ from active cohort")
    states: dict[str, PreparedFeedbackStateArtifact] = {}
    for sample_id in active_ids:
        context = by_sample[sample_id]
        model_context = context.get("model_context")
        if not isinstance(model_context, Mapping):
            raise PreparedFeedbackError("prepared proposal model context is malformed")
        model_context_sha256 = _sha256(
            context.get("model_context_sha256"), field="model_context_sha256"
        )
        if content_hash(model_context) != model_context_sha256:
            raise PreparedFeedbackError("prepared proposal model context hash differs")
        content = _canonical_context(model_context)
        if len(content.encode("utf-8")) > maximum:
            raise PreparedFeedbackError("prepared proposal context exceeds max_context_bytes")
        feedback_sha256 = _sha256(
            context.get("source_feedback_sha256"), field="source_feedback_sha256"
        )
        states[sample_id] = PreparedFeedbackStateArtifact(
            state_id=_state_id(
                prepared_artifact_sha256=prepared_sha256,
                source_feedback_sha256=feedback_sha256,
                construction_roster_sha256=roster_sha,
                model_context_sha256=model_context_sha256,
            ),
            state_kind=PREPARED_FEEDBACK_STATE_KIND,
            content=content,
            cited_value_ids=(),
            prepared_artifact_sha256=prepared_sha256,
            source_feedback_sha256=feedback_sha256,
            construction_roster_sha256=roster_sha,
            model_context_sha256=model_context_sha256,
        ).validate()
    receipt = {
        "schema": PREPARED_FEEDBACK_RECEIPT_SCHEMA,
        "prepared_artifact_sha256": prepared_sha256,
        "source_bindings_sha256": source_bindings_sha256,
        "construction_roster_sha256": roster_sha,
        "state_bindings": [
            {
                "sample_id": sample_id,
                "state_id": states[sample_id].state_id,
                "model_context_sha256": states[sample_id].model_context_sha256,
            }
            for sample_id in active_ids
        ],
    }
    return states, receipt


def load_verified_prepared_contexts(
    spec, *, data_root, sample_ids, construction_roster_sha256, schema,
    build_contexts, preparation_inputs, artifact_kind, input_stage,
):
    """Load a verified scoreless stage through the shared immutable ORG-state path."""
    try:
        if spec.get("schema") != schema:
            raise PreparedFeedbackError("prepared stage schema differs")
        artifact_pin, source_pin, maximum = _validate_spec(dict(spec, schema=PREPARED_FEEDBACK_SCHEMA))
        rebuilt = build_contexts(source_pin, data_root=data_root)
        if rebuilt["construction_roster_sha256"] != construction_roster_sha256:
            raise PreparedFeedbackError("prepared stage requires its exact registered roster")
        envelope, prepared_sha = _read_pinned_json(artifact_pin, data_root=data_root, field="prepared stage")
        if not isinstance(envelope, Mapping) or envelope.get("contact_class") != "model-free":
            raise PreparedFeedbackError("prepared stage must be model-free")
        path = _resolve_data_path(artifact_pin["relpath"], data_root=data_root, field="prepared stage")
        output = load_artifact(path, expected_sha256=prepared_sha, kind=artifact_kind,
                               inputs=preparation_inputs(rebuilt))
        if output != rebuilt:
            raise PreparedFeedbackError("prepared stage differs from verified source")
        contexts = {c["source_sample_id"]: c for c in rebuilt["contexts"]}
        if len(contexts) != len(rebuilt["contexts"]):
            raise PreparedFeedbackError("prepared stage repeats a sample")
        states, receipt = states_from_contexts(
            contexts, active_ids=sample_ids, prepared_sha256=prepared_sha,
            source_bindings_sha256=rebuilt["source_bindings_sha256"],
            roster_sha=construction_roster_sha256, maximum=maximum)
        receipt.update(input_stage=input_stage, runtime_input_contract="shared-prepared-text-artifact")
        return states, receipt, rebuilt
    except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
        if isinstance(error, PreparedFeedbackError):
            raise
        raise PreparedFeedbackError(f"cannot load prepared stage: {error}") from error
