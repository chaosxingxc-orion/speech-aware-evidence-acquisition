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


def validate_operation_format_binding(values, program):
    """Reject a format whose target pool differs from the actual model context."""
    phases = [phase for phase in program.phases if phase.response_format_id == FORMAT_ID]
    if not phases:
        return
    spec = values.get("prepared_training_feedback")
    if (len(program.phases) != 1 or values.get("arm") != "prepared-context-text"
            or not isinstance(spec, Mapping) or spec.get("schema") != INPUT_SCHEMA
            or not isinstance(spec.get("artifact"), Mapping)):
        raise PreparedFeedbackError("group operation format requires its prepared group input")
    material = values.get("phase_material", {}).get(phases[0].name, {})
    if (material.get("response_format_id") != FORMAT_ID
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
