"""Bind typed batch decoding to actual sources and preserve the common runtime."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from jsonschema.validators import validator_for

from test_system_summary_preparation import summary_world, exercise_shared_fit_and_send  # noqa: F401
from test_system_comparison_preparation import comparison_world  # noqa: F401
from test_system_group_update import update_world  # noqa: F401
from test_system_batch_update import batch_world, prepared  # noqa: F401
from test_system_semantic_memory import operation
from test_experience_consolidation import record, snapshot
from speech_aware_evidence_acquisition.core.preparation import prepare_artifact
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError
from speech_aware_evidence_acquisition.rails.system_operation_contract import (
    batch_operations_response_format, validate_operation_format_binding,
)


def bound_schema(w, **changes):
    spec, _ = prepared(w)
    doc = json.loads((w["data"] / spec["artifact"]["relpath"]).read_text())["output"]
    if changes:
        doc.update(changes)
        rec = prepare_artifact(w["data"] / "changed-format.json", kind="system-batch-update-contexts",
            inputs={"test": "known-source"}, producer=lambda: doc, contact_class="model-free")
        spec = dict(spec, artifact={"relpath": "changed-format.json", "sha256": rec["sha256"]})
    value = batch_operations_response_format({}, w["data"], prepared_contexts=spec["artifact"])
    schema = value["json_schema"]["schema"]
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema), spec


@pytest.mark.parametrize("mutation", [
    "missing-id", "extra", "unknown-target", "unknown-source", "wrong-role",
    "long-guidance", "unknown-condition", "too-many",
])
def test_decoder_rejects_unbound_or_malformed_batch_operations(batch_world, mutation):  # noqa: F811
    validator, _ = bound_schema(batch_world)
    value = {"operations": [operation()]}
    validator.validate(value)
    validator.validate({"operations": []})
    op = value["operations"][0]
    if mutation == "missing-id":
        del op["record_id"]
    elif mutation == "extra":
        op["admitted"] = True
    elif mutation == "unknown-target":
        op.update(operation="UPDATE", record_id="missing")
    elif mutation == "unknown-source":
        op["proposal"]["primary_option"] = "group-99"
    elif mutation == "wrong-role":
        op["proposal"]["applicability"]["phases"] = ["solver"]
    elif mutation == "long-guidance":
        op["proposal"]["guidance"] = "x" * 13000
    elif mutation == "unknown-condition":
        op["proposal"]["applicability"]["required_conditions"] = ["confidence:high"]
    else:
        value["operations"] *= 100
    with pytest.raises(ValidationError):
        validator.validate(value)


def test_only_active_frozen_targets_can_be_updated_or_deleted(batch_world):  # noqa: F811
    base = snapshot((record("2"), record("9", "Keep uncertainty visible.")))
    before = copy.deepcopy(base)
    validator, _ = bound_schema(batch_world, base_snapshot=base)
    for target in ["2", "9"]:
        validator.validate({"operations": [operation("UPDATE", target)]})
        validator.validate({"operations": [operation("DELETE", target)]})
    with pytest.raises(ValidationError):
        validator.validate({"operations": [operation("DELETE", "retired")]})
    assert base == before


def configured(spec):
    values = json.loads((Path(__file__).parents[2] /
        "configs/baseline/system-batch-update-constrained-text-v1.json").read_text())
    values["prepared_training_feedback"] = spec
    values["phase_material"]["direct"]["fill_params"] = {"prepared_contexts": spec["artifact"]}
    return values


def test_binding_and_tampering_fail_before_contact(batch_world):  # noqa: F811
    _, spec = bound_schema(batch_world)
    values = configured(spec)
    program = default_phase_program(values["policy"])
    validate_operation_format_binding(values, program)
    values["phase_material"]["direct"]["fill_params"]["prepared_contexts"] = {"relpath": "other.json", "sha256": "a"*64}
    with pytest.raises(PreparedFeedbackError, match="pool differs"):
        validate_operation_format_binding(values, program)
    (batch_world["data"] / spec["artifact"]["relpath"]).write_text("{}")
    with pytest.raises(PreparedFeedbackError, match="hash"):
        batch_operations_response_format({}, batch_world["data"], prepared_contexts=spec["artifact"])


def test_real_fit_and_send_keep_unchanged_model_context_and_instruction(batch_world, tmp_path):  # noqa: F811
    w = batch_world
    _, spec = bound_schema(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["batch_roster"]}, w["source_pin"], [])
    raw = json.dumps({"operations": [operation()]})
    old = exercise_shared_fit_and_send(inputs, tmp_path / "old", True, prepared_spec=spec,
        baseline="system-batch-update-bounded-text-v1", batch_update=True, output_text=raw)
    values = configured(spec)
    new = exercise_shared_fit_and_send(inputs, tmp_path / "new", True, prepared_spec=spec,
        baseline="system-batch-update-constrained-text-v1",
        baseline_overrides={"phase_material": values["phase_material"]},
        batch_update=True, output_text=raw)
    assert old["sent"]["history"] == new["sent"]["history"]
    assert old["sent"]["task_instruction"] == new["sent"]["task_instruction"]
    assert "response_format" not in old["sent"]["decoding_params"]
    fmt = new["sent"]["decoding_params"]["response_format"]
    assert fmt == new["fitted"]["decoding_params"]["response_format"]
    assert fmt["json_schema"]["name"] == "system_batch_operations_v1"
    assert new["canonical"][0]["text"] == raw
