"""Exercise source-bound operation grammar and the real common fit/send path."""
import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError
from jsonschema.validators import validator_for

from test_experience_consolidation import record, snapshot
from test_system_summary_preparation import summary_world, exercise_shared_fit_and_send  # noqa: F401
from test_system_comparison_preparation import comparison_world  # noqa: F401
from test_system_group_update import update_world, prepared  # noqa: F401

from speech_aware_evidence_acquisition.core.preparation import prepare_artifact
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError
from speech_aware_evidence_acquisition.rails.system_operation_contract import (
    FORMAT_ID, group_operations_response_format, validate_operation_format_binding,
)


def schema_for(tmp_path, base):
    result = prepare_artifact(tmp_path / "contexts.json", kind="system-group-update-contexts",
        inputs={"test": "verified-pool"}, contact_class="model-free",
        producer=lambda: {"schema": "saea-system-group-update-contexts-v1", "base_snapshot": base})
    pin = {"relpath": "contexts.json", "sha256": result["sha256"]}
    response_format = group_operations_response_format({}, tmp_path, prepared_contexts=pin)
    schema = response_format["json_schema"]["schema"]
    cls = validator_for(schema)
    cls.check_schema(schema)
    return cls(schema), pin


@pytest.mark.parametrize("operation,valid", [
    ([], True),
    ([{"operation": "ADD", "id": None, "content": "Preserve supported evidence."}], True),
    ([{"operation": "NONE", "id": None, "content": ""}], True),
    ([{"operation": "UPDATE", "id": "A proposed lesson is not a record", "content": "Rule"}], False),
    ([{"operation": "DELETE", "id": "missing", "content": ""}], False),
    ([{"operation": "ADD", "id": "invented", "content": "Rule"}], False),
    ([{"operation": "NONE", "id": None, "content": "Hidden guidance"}], False),
    ([{"operation": "ADD", "id": None, "content": "Rule", "extra": True}], False),
])
def test_empty_pool_only_accepts_add_or_no_change(tmp_path, operation, valid):
    validator, _ = schema_for(tmp_path, snapshot())
    if valid:
        validator.validate(operation)
    else:
        with pytest.raises(ValidationError):
            validator.validate(operation)


def test_nonempty_pool_exposes_exact_active_ids_and_preserves_all_records(tmp_path):
    base = snapshot((record("2"), record("9", "Keep uncertainty visible.")))
    before = copy.deepcopy(base)
    validator, _ = schema_for(tmp_path, base)
    for op in ["UPDATE", "DELETE"]:
        for target in ["2", "9"]:
            validator.validate([{"operation": op, "id": target, "content": "Rule" if op == "UPDATE" else ""}])
        with pytest.raises(ValidationError):
            validator.validate([{"operation": op, "id": "0", "content": "Rule"}])
    assert base == before


def test_changed_artifact_cannot_supply_grammar_targets(tmp_path):
    _, pin = schema_for(tmp_path, snapshot())
    (tmp_path / "contexts.json").write_text("{}")
    with pytest.raises(PreparedFeedbackError, match="hash"):
        group_operations_response_format({}, tmp_path, prepared_contexts=pin)


def configured(spec):
    project = Path(__file__).parents[2]
    values = json.loads((project / "configs/baseline/system-group-update-constrained-text-v1.json").read_text())
    values["prepared_training_feedback"] = spec
    values["phase_material"]["direct"]["fill_params"] = {"prepared_contexts": spec["artifact"]}
    return values


@pytest.mark.parametrize("mutation", ["different-pool", "missing-feedback", "wrong-stage", "wrong-arm", "extra-param"])
def test_source_mismatch_is_refused_before_any_request(mutation):
    spec = {"schema": "saea-prepared-system-group-update-v1",
            "artifact": {"relpath": "same.json", "sha256": "a"*64}}
    values = configured(spec)
    program = default_phase_program(values["policy"])
    validate_operation_format_binding(values, program)
    if mutation == "different-pool":
        values["phase_material"]["direct"]["fill_params"] = {"prepared_contexts": {"relpath": "other.json", "sha256": "b"*64}}
    elif mutation == "missing-feedback":
        values.pop("prepared_training_feedback")
    elif mutation == "wrong-stage":
        values["prepared_training_feedback"] = dict(spec, schema="saea-prepared-system-comparison-v1")
    elif mutation == "wrong-arm":
        values["arm"] = "raw-speech-agent-native-tools"
    else:
        values["phase_material"]["direct"]["fill_params"]["unbound_ids"] = []
    with pytest.raises(PreparedFeedbackError):
        validate_operation_format_binding(values, program)


def test_same_prompt_source_and_output_use_shared_executor_and_exact_fit(update_world, tmp_path):  # noqa: F811
    w = update_world
    spec, _ = prepared(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["update_roster"]}, w["source_pin"], [])
    raw = '[{"operation":"ADD","id":null,"content":"Retain supported changes through delivery."}]'
    old = exercise_shared_fit_and_send(inputs, tmp_path / "old", True, prepared_spec=spec,
        baseline="system-group-update-text-v1", group_update=True, output_text=raw)
    values = configured(spec)
    new = exercise_shared_fit_and_send(inputs, tmp_path / "new", True, prepared_spec=spec,
        baseline="system-group-update-constrained-text-v1",
        baseline_overrides={"phase_material": values["phase_material"]}, group_update=True, output_text=raw)
    assert old["sent"]["history"] == new["sent"]["history"]
    assert old["sent"]["task_instruction"] == new["sent"]["task_instruction"]
    assert "response_format" not in old["sent"]["decoding_params"]
    fmt = new["sent"]["decoding_params"]["response_format"]
    assert fmt == new["fitted"]["decoding_params"]["response_format"]
    assert fmt["json_schema"]["name"] == FORMAT_ID.replace("-", "_")
    assert new["canonical"][0]["text"] == raw


def test_legacy_prepared_program_does_not_acquire_new_constraints():
    values = {"prepared_training_feedback": {"schema": "historical-schema"}}
    validate_operation_format_binding(values, default_phase_program("phase-direct-only-v1"))


@pytest.mark.parametrize("namespace", ["", "bad name", "bad\\nname", 12, "../path"])
def test_control_namespace_refuses_unregistered_text(namespace):
    from speech_aware_evidence_acquisition.rails.prepared_text import prepared_text_control_namespace

    with pytest.raises(ValueError):
        prepared_text_control_namespace(
            {"arm": "prepared-context-text", "prepared_text_control_namespace": namespace},
            "phase-system-group-operations-v1")


def test_control_namespace_cannot_change_a_raw_speech_program():
    from speech_aware_evidence_acquisition.rails.prepared_text import prepared_text_control_namespace

    with pytest.raises(ValueError):
        prepared_text_control_namespace(
            {"arm": "raw-speech-agent-native-tools", "prepared_text_control_namespace": "alias"},
            "phase-direct-only-v1")
