"""Constrain proposed memory operations to the exact frozen input pool.

This is an output interface, not a judge or a memory update. The ordinary
prepared-feedback path still verifies all source lineage and raw outputs.
"""
from collections.abc import Mapping
from pathlib import Path

from ..core.preparation import load_artifact
from .experience_consolidation import _load_snapshot
from .prepared_feedback import PreparedFeedbackError, _read_pinned_json, _resolve_data_path

FORMAT_ID = "system-group-operations-v1"
INPUT_SCHEMA = "saea-prepared-system-group-update-v1"
BATCH_FORMAT_ID = "system-batch-operations-v1"
FORMAT_INPUTS = {FORMAT_ID: INPUT_SCHEMA,
                 BATCH_FORMAT_ID: "saea-prepared-system-batch-update-v1",
                 "slot-value-edits-v1": "saea-prepared-knowledge-edit-v1"}


def knowledge_edit_response_format(lock, root, *, prepared_contexts):
    """Resolve after controller registration to avoid importing actor readers early."""
    from .knowledge_edit_context import knowledge_edit_response_format as render

    return render(lock, root, prepared_contexts=prepared_contexts)


def validate_operation_format_binding(values, program):
    """Reject a format whose target pool differs from the actual model context."""
    phases = [phase for phase in program.phases if phase.response_format_id in FORMAT_INPUTS]
    if not phases:
        return
    spec = values.get("prepared_training_feedback")
    if (len(program.phases) != 1 or values.get("arm") != "prepared-context-text"
            or not isinstance(spec, Mapping) or spec.get("schema") != FORMAT_INPUTS[phases[0].response_format_id]
            or not isinstance(spec.get("artifact"), Mapping)):
        raise PreparedFeedbackError("operation format requires its matching prepared input")
    material = values.get("phase_material", {}).get(phases[0].name, {})
    if (material.get("response_format_id") != phases[0].response_format_id
            or material.get("fill_params") != {"prepared_contexts": spec["artifact"]}):
        raise PreparedFeedbackError("operation format pool differs from prepared feedback")


def group_operations_response_format(_lock, root, *, prepared_contexts):
    """Build one format for the common frozen pool, without selecting guidance."""
    root = Path(root)
    wrapper, sha = _read_pinned_json(prepared_contexts, data_root=root, field="operation contexts")
    if not isinstance(wrapper, Mapping) or not isinstance(wrapper.get("inputs"), Mapping):
        raise PreparedFeedbackError("operation contexts lack a prepared artifact")
    path = _resolve_data_path(prepared_contexts["relpath"], data_root=root, field="operation contexts")
    document = load_artifact(path, expected_sha256=sha, kind="system-group-update-contexts",
                             inputs=wrapper["inputs"])
    if (not isinstance(document, Mapping)
            or document.get("schema") != "saea-system-group-update-contexts-v1"):
        raise PreparedFeedbackError("operation context schema differs")
    records = _load_snapshot(document["base_snapshot"])
    targets = sorted(record.record_id for record in records)

    def branch(operation, target, content):
        return {"type": "object", "additionalProperties": False,
                "required": ["operation", "id", "content"],
                "properties": {"operation": {"const": operation},
                               "id": target, "content": content}}

    text = {"type": "string", "minLength": 1}
    empty = {"const": ""}
    branches = [branch("ADD", {"type": "null"}, text),
                branch("NONE", {"type": "null"}, empty)]
    if targets:
        branches.extend([branch("UPDATE", {"type": "string", "enum": targets}, text),
                         branch("DELETE", {"type": "string", "enum": targets}, empty)])
    return {"type": "json_schema", "json_schema": {
        "name": "system_group_operations_v1", "strict": True,
        "schema": {"type": "array", "items": {"oneOf": branches}}}}


def batch_operations_response_format(_lock, root, *, prepared_contexts):
    """Bind typed batch operations to real source groups and the frozen target pool.

    The host still checks relationships, uniqueness and the atomic pool bound.
    Decoding constraints do not validate semantic credit or authorize memory use.
    """
    from .training_feedback_artifacts import (
        training_feedback_proposal_schema, training_feedback_validator_for_options,
    )

    root = Path(root)
    wrapper, sha = _read_pinned_json(prepared_contexts, data_root=root, field="batch operation contexts")
    if not isinstance(wrapper, Mapping) or not isinstance(wrapper.get("inputs"), Mapping):
        raise PreparedFeedbackError("batch operation contexts lack a prepared artifact")
    path = _resolve_data_path(prepared_contexts["relpath"], data_root=root, field="batch operation contexts")
    document = load_artifact(path, expected_sha256=sha, kind="system-batch-update-contexts",
                             inputs=wrapper["inputs"])
    if (not isinstance(document, Mapping)
            or document.get("schema") not in {"saea-system-batch-update-contexts-v1",
                                            "saea-system-batch-update-contexts-v2"}):
        raise PreparedFeedbackError("batch operation context schema differs")
    targets = sorted(record.record_id for record in _load_snapshot(document["base_snapshot"]))
    labels = frozenset(row["label"] for row in document["source_groups"])
    if not labels or type(document["max_operations"]) is not int or document["max_operations"] <= 0:
        raise PreparedFeedbackError("batch operation format requires a nonempty bounded source")
    anchor = document["full_construction_sample_ids"][0]
    validator = training_feedback_validator_for_options(
        {**document["proposal_contract"], "max_proposals": 1},
        {anchor: labels}, document["source_bindings_sha256"])
    proposal = training_feedback_proposal_schema(validator)

    def branch(operation, target, value):
        return {"type": "object", "additionalProperties": False,
                "required": ["operation", "record_id", "proposal"],
                "properties": {"operation": {"const": operation},
                               "record_id": target, "proposal": value}}

    branches = [branch("ADD", {"type": "null"}, proposal)]
    if targets:
        target = {"type": "string", "enum": targets}
        branches += [branch("UPDATE", target, proposal),
                     branch("DELETE", target, {"type": "null"})]
    return {"type": "json_schema", "json_schema": {
        "name": "system_batch_operations_v1", "strict": True,
        "schema": {"type": "object", "additionalProperties": False,
                   "required": ["operations"], "properties": {
                       "operations": {"type": "array", "maxItems": document["max_operations"],
                                      "items": {"oneOf": branches}}}}}}
