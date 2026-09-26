"""Knowledge proposals retain full sampled systems and use existing input rails."""

import copy
import json
from pathlib import Path

import pytest

from test_system_summary_preparation import pin, summary_world  # noqa: F401
from test_system_comparison_preparation import comparison_world  # noqa: F401
from test_semantic_knowledge_edits import rows
from speech_aware_evidence_acquisition.rails import knowledge_edit_context as module
from speech_aware_evidence_acquisition.rails.semantic_knowledge_edits import (
    slot_value_edit_contract,
)
from speech_aware_evidence_acquisition.rails.prepared_feedback import (
    load_prepared_feedback,
    PreparedFeedbackError,
)
from speech_aware_evidence_acquisition.analysis.shared_json import restore_json


@pytest.fixture
def world(comparison_world, monkeypatch):  # noqa: F811
    w = comparison_world
    data = w["data"]
    monkeypatch.setattr(
        module,
        "load_system_feedback",
        lambda *, binding, **kw: w["feedbacks"][binding["manifest"]["relpath"]],
    )
    monkeypatch.setattr(
        module,
        "verify_native_episode_source",
        lambda *, manifest_path, **kw: w["actors"][
            str(manifest_path.relative_to(data))
        ],
    )
    monkeypatch.setattr(
        module,
        "load_group_source",
        lambda *, feedback_pin, **kw: w["groups"][feedback_pin["relpath"]],
    )
    sid = w["actor"].sample_ids[0]
    members = [
        {
            "label": m["label"],
            "source_repo_root": str(data.parent / "source"),
            "feedback_export": m["feedback_export"],
        }
        for m in w["binding"]["members"]
    ]
    contract = slot_value_edit_contract(
        rows(),
        slot_ids=["date"],
        fields=["missing_behavior"],
        evidence_groups={"g1": [sid]},
        max_edits=1,
        max_field_chars=300,
    )
    binding = {
        "schema": module.SOURCE_SCHEMA,
        "round_id": "round-1",
        "frozen_f0": 0.5,
        "members": members,
        "construction_roster": w["binding"]["comparison_roster"],
        "proposal_roster": w["binding"]["comparison_roster"],
        "base_authored": pin(
            data,
            "base.json",
            {
                "schema": "saea-authored-semantic-knowledge-source-v1",
                "builder_policy_id": "saea-authored-slot-contracts-v1",
                "source_split_identity_hash": "a" * 64,
                "rows": rows(),
            },
        ),
        "edit_contract": pin(data, "contract.json", contract),
    }
    return {
        **w,
        "binding": binding,
        "source_pin": pin(data, "knowledge-source.json", binding),
    }


def prepared(w):
    receipt = module.prepare_knowledge_edit_contexts(
        w["source_pin"], w["data"] / "context.json", data_root=w["data"]
    )
    return {
        "schema": module.PREPARED_SCHEMA,
        "source_bindings": w["source_pin"],
        "artifact": {"relpath": "context.json", "sha256": receipt["sha256"]},
        "language": "en",
        "max_context_bytes": 2000000,
    }


def test_complete_group_with_ties_and_actual_tools_survives_shared_preparation(world):
    w = world
    spec = prepared(w)
    states, receipt = load_prepared_feedback(
        spec,
        repo_root=Path(__file__).resolve().parents[2],
        data_root=w["data"],
        sample_ids=w["actor"].sample_ids,
        construction_roster_sha256=w["binding"]["proposal_roster"]["sha256"],
        result_kind="artifact",
        artifact_role="training-feedback-proposal",
    )
    context = json.loads(next(iter(states.values())).content)
    evidence = restore_json(context["evidence"])
    attempts = evidence["groups"][0]["attempts"]
    assert len(attempts) == 2
    assert attempts[0]["terminal_feedback"]["fp"] == 0
    assert attempts[1]["terminal_feedback"]["fp"] == 2
    assert len(attempts[0]["episode"]["contacts"]) == 5
    assert len(attempts[0]["episode"]["actual_tool_records"]) == 2
    assert (
        attempts[0]["episode"]["delivered_text"]
        == w["actor"].output_rows[w["actor"].sample_ids[0]]["text"]
    )
    assert evidence["base_slot_rows"] == rows()
    assert receipt["input_stage"] == "complete-system-knowledge-edit"
    assert (
        module.knowledge_edit_response_format(
            None, w["data"], prepared_contexts=spec["artifact"]
        )["type"]
        == "json_schema"
    )
    assert (
        module.prepare_knowledge_edit_contexts(
            w["source_pin"], w["data"] / "context.json", data_root=w["data"]
        )["cache"]
        == "warm"
    )


@pytest.mark.parametrize(
    "change", ["feedback", "population", "contract", "source-failure", "future-roster"]
)
def test_broken_source_or_changed_scope_cannot_use_prepared_cache(
    world, monkeypatch, change
):
    w = world
    prepared(w)
    binding = copy.deepcopy(w["binding"])
    if change == "feedback":
        w["feedbacks"][next(iter(w["feedbacks"]))] = {"wrong": "official feedback"}
    elif change == "population":
        binding["members"] = binding["members"][:1]
    elif change == "contract":
        binding["edit_contract"]["sha256"] = "f" * 64
    elif change == "source-failure":

        def closed(**kw):
            raise ValueError("source not complete")

        monkeypatch.setattr(module, "verify_native_episode_source", closed)
    else:
        r = json.loads(
            (w["data"] / binding["construction_roster"]["relpath"]).read_text()
        )
        r["items"][0]["sample_id"] = "slurp:devel:future"
        binding["construction_roster"] = pin(w["data"], "future.json", r)
    source = pin(w["data"], "changed.json", binding)
    with pytest.raises(PreparedFeedbackError):
        module.prepare_knowledge_edit_contexts(
            source, w["data"] / "context.json", data_root=w["data"]
        )


def test_terminal_ties_are_retained_without_generation_filter(world):
    w = world
    for group in w["groups"].values():
        group["rows"][0]["fp"] = 0
    result = module.build_knowledge_edit_contexts(w["source_pin"], data_root=w["data"])
    assert result["feedback_summary"]["ineligible_groups"] == 1
    assert len(result["contexts"]) == 1
    assert result["model_contacts_added"] == result["scorer_contacts_added"] == 0


def test_exact_fit_and_delivery_use_common_controller_and_openjiuwen(world, tmp_path):
    from test_system_summary_preparation import exercise_shared_fit_and_send
    from speech_aware_evidence_acquisition.rails.controllers import (
        default_phase_program,
    )
    from speech_aware_evidence_acquisition.rails.system_operation_contract import (
        validate_operation_format_binding,
    )

    w = world
    spec = prepared(w)
    project = Path(__file__).resolve().parents[2]
    values = json.loads(
        (project / "configs/baseline/knowledge-value-edit-text-v1.json").read_text()
    )
    values["prepared_training_feedback"] = spec
    values["phase_material"]["direct"]["fill_params"] = {
        "prepared_contexts": copy.deepcopy(spec["artifact"])
    }
    program = default_phase_program(values["policy"])
    validate_operation_format_binding(values, program)
    changed = copy.deepcopy(values)
    changed["phase_material"]["direct"]["fill_params"]["prepared_contexts"][
        "sha256"
    ] = "f" * 64
    with pytest.raises(PreparedFeedbackError):
        validate_operation_format_binding(changed, program)
    inputs = (
        w["data"],
        w["actor"],
        {"construction_roster": w["binding"]["proposal_roster"]},
        w["source_pin"],
        [],
    )
    from speech_aware_evidence_acquisition.rails.hashing import content_hash

    raw = json.dumps(
        {
            "schema": "saea-slot-value-edits-v1",
            "base_rows_sha256": content_hash(rows()),
            "edits": [],
        }
    )
    exercise_shared_fit_and_send(
        inputs,
        tmp_path / "shared",
        True,
        prepared_spec=spec,
        baseline_overrides=values,
        knowledge_edit=True,
        output_text=raw,
    )
