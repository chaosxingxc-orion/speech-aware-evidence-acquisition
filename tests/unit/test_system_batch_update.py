"""Exercise complete group feedback to batch synthesis without research contacts."""
import copy
import json
from pathlib import Path

import pytest
from test_system_summary_preparation import summary_world, pin, exercise_shared_fit_and_send  # noqa: F401
from test_system_comparison_preparation import comparison_world  # noqa: F401
from test_system_group_update import update_world, prepared as update_prepared, response  # noqa: F401
from test_system_summary_source import make_text_stage_source

from speech_aware_evidence_acquisition.rails import system_batch_update_context as module
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError, load_prepared_feedback


@pytest.fixture
def batch_world(update_world, tmp_path, monkeypatch):  # noqa: F811
    w = update_world
    spec, _ = update_prepared(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["update_roster"]}, w["source_pin"], [])
    stage = make_text_stage_source(inputs, tmp_path, monkeypatch, prepared_spec=spec,
                                  baseline="system-group-update-text-v1", stage_name="group-update")
    response({"stage": stage}, json.dumps([{"operation": "ADD", "id": None,
        "content": "A repair must survive all subsequent roles and final delivery."}]))
    binding = {"schema": module.SOURCE_SCHEMA, "group_update_manifest": stage["pin"],
               "group_update_repo_root": str(stage["repo"]),
               "batch_roster": w["binding"]["update_roster"], "max_operations": 8,
               "proposal_contract": {
                   "applicability": {"allowed_task_ids": ["slurp"], "allowed_roles": ["reviewer"],
                                     "allowed_component_tags": ["org"]},
                   "max_diagnosis_chars": 800, "max_guidance_chars": 1200,
                   "max_limitation_chars": 400, "max_limitations": 4, "max_option_refs": 8}}
    return {"data": w["data"], "actor": w["actor"], "stage": stage, "binding": binding,
            "source_pin": pin(w["data"], "batch-source.json", binding), "upstream": w}


def prepared(world):
    receipt = module.prepare_system_batch_update_contexts(
        world["source_pin"], world["data"] / "prepared/batch.json", data_root=world["data"])
    return {"schema": module.PREPARED_SCHEMA,
            "artifact": {"relpath": "prepared/batch.json", "sha256": receipt["sha256"]},
            "source_bindings": world["source_pin"], "language": "en",
            "max_context_bytes": 2000000}, receipt


def load(world, spec, **changes):
    kwargs = dict(repo_root=Path(__file__).parents[2], data_root=world["data"],
                  sample_ids=world["actor"].sample_ids,
                  construction_roster_sha256=world["binding"]["batch_roster"]["sha256"],
                  result_kind="artifact", artifact_role="training-feedback-proposal")
    kwargs.update(changes)
    return load_prepared_feedback(spec, **kwargs)


def test_real_sealed_group_operations_reach_one_shared_batch(batch_world):
    w = batch_world
    before = copy.deepcopy(w["stage"]["response"])
    spec, cold = prepared(w)
    states, receipt = load(w, spec)
    context = json.loads(next(iter(states.values())).content)
    assert context["existing_experiences"] == []
    assert context["group_operations"][0]["operations"] == json.loads(before["text"])
    assert context["group_operations"][0]["label"] == "group-1"
    assert "terminal_feedback" not in json.dumps(context)
    document = module.build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    bound = document["source_groups"][0]
    assert len(bound["group"]["members"]) == 2
    assert [m["outcome"]["fp"] for m in bound["group"]["members"]] == [0, 2]
    assert bound["source_ref"]["ref_id"] == "complete-system-group:" + content_hash(bound["group"])
    assert receipt["full_group_count"] == 1 and w["stage"]["response"] == before
    _, warm = prepared(w)
    assert cold["cache"] == "cold" and warm["cache"] == "warm" and cold["sha256"] == warm["sha256"]


def test_composite_source_tracks_each_complete_actor_action_and_terminal_outcome(batch_world):
    doc = module.build_system_batch_update_contexts(batch_world["source_pin"], data_root=batch_world["data"])
    group = doc["source_groups"][0]["group"]
    original = module.experience_group_binding(group)
    for field in ("trajectory_sha256", "action_sha256", "response_sha256", "official_feedback_sha256"):
        changed = copy.deepcopy(group)
        changed["members"][1][field] = "f"*64
        updated = module.experience_group_binding(changed)
        assert updated["group_sha256"] != original["group_sha256"]
        assert updated["source"] != original["source"]
    changed = copy.deepcopy(group)
    changed["members"][1]["outcome"]["fp"] += 1
    assert module.experience_group_binding(changed)["source"] != original["source"]
    with pytest.raises(PreparedFeedbackError, match="repeats"):
        module.experience_group_binding(dict(group, members=[group["members"][0]]*2))


def test_batch_uses_shared_fit_send_and_raw_synthesized_response(batch_world, tmp_path):
    w = batch_world
    spec, _ = prepared(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["batch_roster"]}, w["source_pin"], [])
    exercise_shared_fit_and_send(inputs, tmp_path / "consumer", True, prepared_spec=spec,
        baseline="system-batch-update-text-v1", batch_update=True, output_text='{"operations":[]}')


@pytest.mark.parametrize("mutation", ["phase", "request", "source", "size", "roster", "role"])
def test_warm_loader_rejects_changed_sources_or_runtime_scope(batch_world, mutation):
    w = batch_world
    spec, _ = prepared(w)
    kwargs = {}
    if mutation == "phase":
        (w["stage"]["repo"] / "configs/probes/system_group_update_v1.txt").write_text("Substituted phase.")
    elif mutation == "request":
        stage = w["stage"]
        stage["payload"]["history"][0]["content"] += " changed"
        stage["bundle"].trace_records[stage["request_id"] + "/request"]["payload_sha256"] = content_hash(stage["payload"])
    elif mutation == "source":
        spec["source_bindings"]["sha256"] = "f"*64
    elif mutation == "size":
        spec["max_context_bytes"] = 10
    elif mutation == "roster":
        kwargs["construction_roster_sha256"] = "f"*64
    else:
        kwargs["result_kind"] = "task-answer"
    with pytest.raises(PreparedFeedbackError):
        load(w, spec, **kwargs)


@pytest.mark.parametrize("text", ["[]", '[{"operation":"NONE","id":null,"content":""}]', "invalid"])
def test_no_usable_group_operations_retains_population_and_requires_no_contact(batch_world, text):
    w = batch_world
    response({"stage": w["stage"]}, text)
    with pytest.raises(PreparedFeedbackError, match="anchor"):
        module.build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    binding = dict(w["binding"], batch_roster=None)
    doc = module.build_system_batch_update_contexts(pin(w["data"], "no-contact.json", binding), data_root=w["data"])
    assert doc["contexts"] == [] and doc["disposition"] == "no-change-no-operation"
    assert doc["group_operation_report"]["population"][0]["update_response"]["text"] == text


def test_whole_population_is_retained_even_when_only_one_group_proposes(batch_world, monkeypatch):
    w = batch_world
    report = module.read_system_group_operations(w["stage"]["pin"], repo_root=w["stage"]["repo"], data_root=w["data"])
    report = copy.deepcopy(report)
    sid = "slurp:train:extra"
    report["full_construction_sample_ids"].append(sid)
    report["population"].append({"sample_id": sid, "disposition": "no-update-terminal-tie",
                                "experience_source": {}, "parsed": None})
    report["base_snapshot"]["train_sample_ids"] = sorted(report["full_construction_sample_ids"])
    report["source_construction_roster_sha256"] = "f"*64
    report["base_snapshot"]["train_construction_sha256"] = "f"*64
    monkeypatch.setattr(module, "read_system_group_operations", lambda *a, **k: report)
    doc = module.build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    assert len(doc["full_construction_sample_ids"]) == 2
    assert len(doc["contexts"]) == len(doc["source_groups"]) == 1
    assert doc["source_construction_roster_sha256"] != doc["construction_roster_sha256"]
    assert doc["group_operation_report"]["population"][1]["sample_id"] == sid


def test_public_batch_preparation_entrypoint_is_immutable(batch_world, capsys):
    w = batch_world
    args = ["--data-root", str(w["data"]), "--source-relpath", w["source_pin"]["relpath"],
            "--source-sha256", w["source_pin"]["sha256"], "--output-relpath", "prepared/cli-batch.json"]
    assert module.main(args) == 0
    first = json.loads(capsys.readouterr().out)
    assert module.main(args) == 0
    second = json.loads(capsys.readouterr().out)
    assert first["sha256"] == second["sha256"] and second["cache"] == "warm"

def widen_group_report(world, monkeypatch):
    """Substitute only verified upstream reporting; keep downstream stages real."""
    from speech_aware_evidence_acquisition.core.roster import split_identity_hash
    from speech_aware_evidence_acquisition.data.splits import prefixed
    from speech_aware_evidence_acquisition.rails.experience_consolidation import initialize_candidate_snapshot
    report = copy.deepcopy(module.read_system_group_operations(
        world["stage"]["pin"], repo_root=world["stage"]["repo"], data_root=world["data"]))
    first = report["population"][0]
    second = copy.deepcopy(first)
    second["sample_id"] = "slurp:train:extra"
    second["experience_source"]["sample_id"] = second["sample_id"]
    second["parsed"]["operations"][0]["content"] = "Inspect unsupported entity insertions before final delivery."
    report["population"].append(second)
    report["full_construction_sample_ids"].append(second["sample_id"])
    roster = json.loads((world["data"] / world["binding"]["batch_roster"]["relpath"]).read_text())
    roster["items"].append({"sample_id": second["sample_id"], "stratum": "all"})
    roster["split_identity_hash"] = split_identity_hash(prefixed("slurp", report["full_construction_sample_ids"]))
    full_pin = pin(world["data"], "full-source-roster.json", roster)
    report["source_construction_roster_sha256"] = full_pin["sha256"]
    report["base_snapshot"] = initialize_candidate_snapshot(
        memory_id=report["base_snapshot"]["memory_id"], train_construction_sha256=full_pin["sha256"],
        expected_train_sample_ids=report["full_construction_sample_ids"])
    report.pop("content_sha256")
    report["content_sha256"] = content_hash(report)
    monkeypatch.setattr(module, "read_system_group_operations", lambda *a, **k: copy.deepcopy(report))
    return report, full_pin


def test_every_valid_group_proposal_is_in_one_batch_without_top_k_truncation(batch_world, monkeypatch):
    w = batch_world
    report, full_pin = widen_group_report(w, monkeypatch)
    doc = module.build_system_batch_update_contexts(w["source_pin"], data_root=w["data"])
    context = doc["contexts"][0]["model_context"]
    assert [row["operations"] for row in context["group_operations"]] == [row["parsed"]["operations"] for row in report["population"]]
    assert len(doc["contexts"]) == 1 and len(doc["source_groups"]) == 2
    assert doc["source_construction_roster_sha256"] == full_pin["sha256"]
