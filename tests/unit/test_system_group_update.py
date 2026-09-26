"""Verify comparison-to-update input and frozen memory without research contacts."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from test_system_summary_preparation import summary_world, pin, exercise_shared_fit_and_send  # noqa: F401
from test_system_comparison_preparation import comparison_world, prepared as comparison_prepared  # noqa: F401
from test_system_summary_source import make_text_stage_source
from speech_aware_evidence_acquisition.analysis.prepared_text_source import VerifiedPreparedTextSource
from speech_aware_evidence_acquisition.rails import system_group_update_context as module
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError, load_prepared_feedback


def response(world, text, count=30):
    stage = world["stage"]
    sha = hashlib.sha256(text.encode()).hexdigest()
    stage["response"].update(text=text, response_text_sha256=sha, usage={"completion_tokens": count})
    stage["output"].update(text=text, response_text_sha256=sha)


@pytest.fixture
def update_world(comparison_world, tmp_path, monkeypatch):  # noqa: F811
    w = comparison_world
    spec, _ = comparison_prepared(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["comparison_roster"]},
              w["source_pin"], w["calls"])
    stage = make_text_stage_source(inputs, tmp_path, monkeypatch, prepared_spec=spec,
                                  baseline="system-semantic-comparison-text-v1")
    binding = {"schema": module.SOURCE_SCHEMA, "comparison_manifest": stage["pin"],
               "comparison_repo_root": str(stage["repo"]),
               "source_construction_roster": w["binding"]["comparison_roster"],
               "update_roster": w["binding"]["comparison_roster"],
               "memory_id": "whole-system-memory", "base_memory": None}
    world = {"data": w["data"], "actor": w["actor"], "stage": stage, "binding": binding}
    response(world, "A later role undid a repair. <Experiences>When evidence conflicts, preserve "
                    "supported changes through final delivery; the causal explanation remains untested.</Experiences>")
    world["source_pin"] = pin(w["data"], "group-update-source.json", binding)
    return world


def prepared(world):
    receipt = module.prepare_system_group_update_contexts(
        world["source_pin"], world["data"] / "prepared/group-update.json", data_root=world["data"])
    spec = {"schema": module.PREPARED_SCHEMA,
            "artifact": {"relpath": "prepared/group-update.json", "sha256": receipt["sha256"]},
            "source_bindings": world["source_pin"], "language": "en", "max_context_bytes": 2000000}
    return spec, receipt


def load(world, spec, **changes):
    kwargs = dict(repo_root=Path(__file__).parents[2], data_root=world["data"],
                  sample_ids=world["actor"].sample_ids,
                  construction_roster_sha256=world["binding"]["update_roster"]["sha256"],
                  result_kind="artifact", artifact_role="training-feedback-proposal")
    kwargs.update(changes)
    return load_prepared_feedback(spec, **kwargs)


def test_sealed_comparison_and_empty_frozen_memory_reach_shared_preparation(update_world):
    w = update_world
    before = copy.deepcopy(w["stage"]["response"])
    spec, cold = prepared(w)
    states, receipt = load(w, spec)
    context = json.loads(next(iter(states.values())).content)
    assert context["existing_experiences"] == []
    assert "causal explanation remains untested" in context["new_experiences"]
    assert context["comparison_analysis"] == before["text"]
    assert [a["terminal_feedback"]["fp"] for a in context["observed_comparison"]["attempts"]] == [0, 2]
    assert w["stage"]["response"] == before
    _, warm = prepared(w)
    assert cold["cache"] == "cold" and warm["cache"] == "warm" and cold["sha256"] == warm["sha256"]
    assert receipt["full_group_count"] == receipt["ready_group_count"] == 1
    assert receipt["source_construction_roster_sha256"] == w["binding"]["source_construction_roster"]["sha256"]


@pytest.mark.parametrize("text,status", [
    ("<Experiences> rule </Experiences>", "ready"),
    ("<eXpErIeNcEs> rule </EXPERIENCES>", "ready"),
    ("<Experiences> </Experiences>", "empty-block"),
    ("There is no supported experience.", "missing-block"),
    ("<Experiences>a</Experiences><Experiences>b</Experiences>", "ambiguous-block"),
    ("<Experiences><Experiences>a</Experiences></Experiences>", "ambiguous-block"),
])
def test_experience_extraction_preserves_upstream_tags_and_marks_ambiguity(text, status):
    result = module.extract_experiences(text)
    assert result["status"] == status
    if status == "ready":
        assert result["text"] == "rule"


@pytest.mark.parametrize("text,count,disposition", [
    ("<Experiences></Experiences>", 5, "no-update-no-experience"),
    ("Missing an experience block.", 5, "no-update-no-experience"),
    ("<Experiences>a</Experiences><Experiences>b</Experiences>", 5, "blocked-ambiguous-experience"),
    ("<Experiences>partial rule</Experiences>", 128, "blocked-unusable-comparison"),
])
def test_unusable_or_empty_comparison_stays_in_population_without_contact(update_world, text, count, disposition):
    w = update_world
    response(w, text, count)
    with pytest.raises(PreparedFeedbackError, match="ordered ready"):
        module.build_system_group_update_contexts(w["source_pin"], data_root=w["data"])
    binding = dict(w["binding"], update_roster=None)
    source_pin = pin(w["data"], "diagnostic-group-source.json", binding)
    document = module.build_system_group_update_contexts(source_pin, data_root=w["data"])
    assert document["contexts"] == []
    assert document["population"][0]["disposition"] == disposition
    assert document["population"][0]["comparison"]["text"] == text
    assert document["full_construction_sample_ids"] == list(w["actor"].sample_ids)
    assert document["model_contacts_added"] == document["scorer_contacts_added"] == 0


@pytest.mark.parametrize("change", ["phase", "source", "roster", "bound-context", "limit", "role"])
def test_source_and_runtime_refusals_precede_cached_states(update_world, change):
    w = update_world
    spec, _ = prepared(w)
    kwargs = {}
    if change == "phase":
        (w["stage"]["repo"] / "configs/probes/system_semantic_comparison_v1.txt").write_text("Substituted phase.")
    elif change == "source":
        spec["source_bindings"]["sha256"] = "f"*64
    elif change == "roster":
        kwargs["construction_roster_sha256"] = "f"*64
    elif change == "bound-context":
        w["stage"]["payload"]["history"][0]["content"] += " changed"
        w["stage"]["bundle"].trace_records["summary:1/request"]["payload_sha256"] = content_hash(w["stage"]["payload"])
    elif change == "limit":
        spec["max_context_bytes"] = 5
    else:
        kwargs["result_kind"] = "task-answer"
    with pytest.raises(PreparedFeedbackError):
        load(w, spec, **kwargs)


def test_full_population_includes_groups_that_never_reached_comparison(update_world, monkeypatch):
    w = update_world
    source = module.verify_system_comparisons(w["stage"]["pin"], repo_root=w["stage"]["repo"], data_root=w["data"])
    document = copy.deepcopy(source.prepared_document)
    sid = "slurp:train:2"
    document["comparison"]["groups"].append({"sample_id": sid, "disposition": "no-update-terminal-tie", "experience_source": {"fixture": True}})
    roster = json.loads((w["data"] / "roster.json").read_text())
    roster["items"].append({"sample_id": sid, "stratum": "all"})
    from speech_aware_evidence_acquisition.core.roster import split_identity_hash
    from speech_aware_evidence_acquisition.data.splits import prefixed
    roster["split_identity_hash"] = split_identity_hash(prefixed("slurp", [i["sample_id"] for i in roster["items"]]))
    full_pin = pin(w["data"], "full-construction.json", roster)
    document["source_construction_roster_sha256"] = full_pin["sha256"]
    synthetic = VerifiedPreparedTextSource(source.manifest, source.manifest_sha256,
                                          source.source_binding, document, source.rows)
    monkeypatch.setattr(module, "verify_system_comparisons", lambda *_args, **_kwargs: synthetic)
    binding = dict(w["binding"], source_construction_roster=full_pin)
    out = module.build_system_group_update_contexts(pin(w["data"], "full-source.json", binding), data_root=w["data"])
    assert len(out["contexts"]) == 1 and len(out["population"]) == 2
    assert out["source_construction_roster_sha256"] != out["construction_roster_sha256"]
    assert sid in out["base_snapshot"]["train_sample_ids"]
    assert out["population"][1]["comparison"] is None


def test_update_stage_uses_shared_fit_send_and_preserves_raw_operation_response(update_world, tmp_path):
    w = update_world
    spec, _ = prepared(w)
    inputs = (w["data"], w["actor"], {"construction_roster": w["binding"]["update_roster"]},
              w["source_pin"], [])
    output = '[{"operation":"ADD","id":null,"content":"When evidence conflicts, retain supported repairs."}]'
    exercise_shared_fit_and_send(inputs, tmp_path / "consumer-stage", True, prepared_spec=spec,
                                baseline="system-group-update-text-v1", group_update=True, output_text=output)


@pytest.mark.parametrize("consolidated", [False, True])
def test_nonempty_memory_is_replayed_and_passed_whole_with_frozen_ids(update_world, monkeypatch, consolidated):
    from dataclasses import replace
    from test_experience_consolidation import record
    from speech_aware_evidence_acquisition.core.preparation import prepare_artifact
    from speech_aware_evidence_acquisition.rails.experience_memory import ExperienceRecord
    w = update_world
    sid = w["actor"].sample_ids[0]
    sha = w["binding"]["source_construction_roster"]["sha256"]
    original = record(sample=sid)
    value = replace(original, train_construction_sha256=sha,
                    validation=replace(original.validation, roster_sha256=sha))
    value = replace(value, record_sha256=content_hash(value.unsigned_json()))
    ExperienceRecord.from_json(value.as_json())
    base = module.initialize_candidate_snapshot(memory_id=w["binding"]["memory_id"],
        train_construction_sha256=sha, expected_train_sample_ids=[sid], records=(value,))
    output = {"provenance": {"construction_roster_sha256": sha},
              "samples": [{"source_sample_id": sid, "records": [value.as_json()]}]}
    if consolidated:
        base = dict(base, issued_record_ids=sorted([value.record_id, "retired-record"]),
                    parent_snapshot_sha256="a"*64)
        base.pop("content_sha256")
        base["content_sha256"] = content_hash(base)
        output["candidate_snapshot"] = base
    artifact_path = w["data"] / "base-candidates.json"
    receipt = prepare_artifact(artifact_path, kind=module.ARTIFACT_KIND,
                              inputs={"fixture": "source-bound-base"}, producer=lambda: output,
                              contact_class="model-free")
    calls = []
    def replay(**kwargs):
        calls.append(kwargs)
        return receipt
    monkeypatch.setattr(module, "prepare_provisional_candidates", replay)
    base_pin = {"materialization_config": pin(w["data"], "base-config.json", {"fixture": True}),
                "candidate_artifact": {"relpath": "base-candidates.json", "sha256": receipt["sha256"]},
                "snapshot_sha256": base["content_sha256"]}
    binding = dict(w["binding"], base_memory=base_pin)
    source_pin = pin(w["data"], "source-with-base.json", binding)
    result = module.build_system_group_update_contexts(source_pin, data_root=w["data"])
    assert len(calls) == 1
    assert result["base_snapshot"] == base
    visible = result["contexts"][0]["model_context"]["existing_experiences"][0]
    assert visible["record_id"] == value.record_id and visible["guidance"] == value.guidance
    assert "validation" not in visible and "source" not in visible
    if consolidated:
        assert "retired-record" in result["base_snapshot"]["issued_record_ids"]
    base_pin["snapshot_sha256"] = "f"*64
    with pytest.raises(PreparedFeedbackError, match="snapshot"):
        module.build_system_group_update_contexts(pin(w["data"], "wrong-base.json", binding), data_root=w["data"])


def test_public_update_preparation_cli_is_cached(update_world, capsys):
    w = update_world
    args = ["--data-root", str(w["data"]), "--source-relpath", w["source_pin"]["relpath"],
            "--source-sha256", w["source_pin"]["sha256"], "--output-relpath", "prepared/cli-update.json"]
    assert module.main(args) == 0
    cold = json.loads(capsys.readouterr().out)
    assert module.main(args) == 0
    warm = json.loads(capsys.readouterr().out)
    assert cold["sha256"] == warm["sha256"] and warm["cache"] == "warm"
