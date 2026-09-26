"""Prepare semantic comparison through shared source readers and immutable contexts.

Source verification and official scorer readers are substituted here; grouping,
whole-episode materialization, joins, roster checks and preparation are real.
"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from test_system_summary_preparation import summary_world, pin  # noqa: F401
from speech_aware_evidence_acquisition.analysis.system_rollout_groups import normalized_answer_hash
from speech_aware_evidence_acquisition.analysis.system_semantic_trajectory import materialize_semantic_trajectories
from speech_aware_evidence_acquisition.analysis.system_summary_source import VerifiedSystemSummaries
from speech_aware_evidence_acquisition.rails import system_comparison_context as module
from speech_aware_evidence_acquisition.rails.prepared_feedback import PreparedFeedbackError, load_prepared_feedback


@pytest.fixture
def comparison_world(summary_world, monkeypatch):  # noqa: F811
    data, actor, base_binding, _, _ = summary_world
    members, summaries, feedbacks, actors, groups, calls = [], {}, {}, {}, {}, []
    for i in range(2):
        value = copy.deepcopy(actor)
        value.plan.run_id = f"actor-{i}"
        value.plan.protocol_hash = "a"*64
        value.bundle.manifest["study_commit"] = "b"*40
        report = materialize_semantic_trajectories(value, round_id="round-1")
        episode = report["episodes"][0]
        sid = value.sample_ids[0]
        trajectory = episode["trajectory"]
        binding = copy.deepcopy(base_binding)
        binding["manifest"] = pin(data, f"actor-{i}/manifest.json", {"fixture": i})
        binding["phases"] = pin(data, f"actor-{i}/phases.json", {"fixture": i})
        export = {"source_bindings": {"manifest": binding["manifest"], "phases": binding["phases"]},
                  "fixture_feedback": i}
        feedback_pin = pin(data, f"actor-{i}/feedback.json", export)
        text = f"Complete episode {i}: Perception, Solver, Reviewer and Planner."
        summary_pin = pin(data, f"summary-{i}/manifest.json", {"fixture_summary": i})
        row = {"sample_id": sid, "summary": text, "status": "usable",
               "episode_sha256": episode["content_sha256"], "summary_manifest_sha256": summary_pin["sha256"],
               "summary_request_id": f"summary-{i}", "summary_response_sha256": hashlib.sha256(text.encode()).hexdigest()}
        summaries[summary_pin["relpath"]] = VerifiedSystemSummaries(
            {"config": {"fragments": {"model": "frozen-model"}}, "session_receipt": {"sha256": "a"*64}},
            summary_pin["sha256"], binding,
            {"contexts": [{"source_sample_id": sid, "model_context": {"trajectory": episode}}]}, {sid: row})
        visits = trajectory["role_visits"]
        groups[feedback_pin["relpath"]] = {
            "label": f"arm-{i}", "run_id": value.plan.run_id, "attempt_id": value.plan.attempt_id,
            "feedback_sha256": feedback_pin["sha256"], "split_identity_hash": value.plan.split_identity_hash,
            "model_fragment": "frozen-model", "session_receipt_sha256": "a"*64,
            "config_hash": value.composed.config_hash, "feedback_role": "construction",
            "ordered_sample_ids": [sid], "rows": [{
                "sample_id": sid, "trajectory_sha256": trajectory["trajectory_sha256"],
                "input_sha256": episode["input_sha256"],
                "normalized_answer_sha256": normalized_answer_hash(episode["delivered_text"]),
                "tp": 0, "fp": 2*i, "fn": 0, "intent_exact": 1, "format_ok": True,
                "fallback_flags": [], "role_visits": [v["stage"] for v in visits],
                "revision_reached": sum(v["stage"] == "solver" for v in visits) > 1,
                "delivery_kind": trajectory["delivery"]["kind"],
                "model_contacts": sum(len(v["contacts"]) for v in visits), "tool_events": len(trajectory["tool_events"]),
            }],
        }
        actors[binding["manifest"]["relpath"]] = value
        feedbacks[binding["manifest"]["relpath"]] = export
        members.append({"label": f"arm-{i}", "summary_manifest": summary_pin,
                        "summary_repo_root": str(data.parent / f"summary-repo-{i}"), "feedback_export": feedback_pin})

    def summary_verified(pin, **_kwargs):
        calls.append(("summary", pin["relpath"]))
        return summaries[pin["relpath"]]
    def feedback_verified(*, binding, **_kwargs):
        calls.append(("feedback", binding["manifest"]["relpath"]))
        return feedbacks[binding["manifest"]["relpath"]]
    def actor_verified(*, manifest_path, **_kwargs):
        return actors[str(manifest_path.relative_to(data))]
    monkeypatch.setattr(module, "verify_system_summaries", summary_verified)
    monkeypatch.setattr(module, "load_system_feedback", feedback_verified)
    monkeypatch.setattr(module, "verify_native_episode_source", actor_verified)
    monkeypatch.setattr(module, "load_group_source",
                        lambda *, feedback_pin, **_kwargs: groups[feedback_pin["relpath"]])
    binding = {"schema": module.SOURCE_SCHEMA, "round_id": "round-1", "frozen_f0": 0.5,
               "members": members, "comparison_roster": base_binding["construction_roster"]}
    source_pin = pin(data, "comparison-source.json", binding)
    return dict(data=data, actor=actor, binding=binding, source_pin=source_pin, summaries=summaries,
                feedbacks=feedbacks, groups=groups, calls=calls, actors=actors)


def prepared(world):
    receipt = module.prepare_system_comparison_contexts(
        world["source_pin"], world["data"] / "prepared/comparison.json", data_root=world["data"])
    spec = {"schema": module.PREPARED_COMPARISON_SCHEMA,
            "artifact": {"relpath": "prepared/comparison.json", "sha256": receipt["sha256"]},
            "source_bindings": world["source_pin"], "language": "en", "max_context_bytes": 2000000}
    return spec, receipt


def load(world, spec, **changes):
    options = dict(repo_root=Path(__file__).parents[2], data_root=world["data"],
                   sample_ids=world["actor"].sample_ids,
                   construction_roster_sha256=world["binding"]["comparison_roster"]["sha256"],
                   result_kind="artifact", artifact_role="training-feedback-proposal")
    options.update(changes)
    return load_prepared_feedback(spec, **options)


def test_cold_warm_preparation_and_public_loader_rebuild_all_sources(comparison_world):
    world = comparison_world
    spec, cold = prepared(world)
    states, receipt = load(world, spec)
    sid = world["actor"].sample_ids[0]
    context = json.loads(states[sid].content)
    assert context["stage"] == "complete-system-semantic-comparison"
    assert [a["terminal_feedback"]["fp"] for a in context["attempts"]] == [0, 2]
    assert len(world["calls"]) == 8
    before = (world["data"] / spec["artifact"]["relpath"]).read_bytes()
    _, warm = prepared(world)
    assert cold["cache"] == "cold" and warm["cache"] == "warm"
    assert cold["sha256"] == warm["sha256"]
    assert len(world["calls"]) == 12
    assert (world["data"] / spec["artifact"]["relpath"]).read_bytes() == before
    assert receipt["input_stage"] == "complete-system-semantic-comparison"
    assert receipt["full_group_count"] == receipt["ready_group_count"] == 1
    assert receipt["runtime_input_contract"] == "shared-prepared-text-artifact"
    assert "reference_answer" not in states[sid].content


@pytest.mark.parametrize("change", ["summary", "feedback", "round", "model", "session", "roster", "partial"])
def test_source_substitutions_and_warm_failure_precede_cache(comparison_world, monkeypatch, change):
    world = comparison_world
    spec, _ = prepared(world)
    if change in ("summary", "feedback"):
        def failed(*_args, **_kwargs):
            raise ValueError("source verification failed")
        monkeypatch.setattr(module, "verify_system_summaries" if change == "summary" else "load_system_feedback", failed)
    elif change == "round":
        next(iter(world["summaries"].values())).actor_binding["round_id"] = "other"
    elif change in ("model", "session"):
        manifest = next(iter(world["summaries"].values())).manifest
        if change == "model":
            manifest["config"]["fragments"]["model"] = "other"
        else:
            manifest["session_receipt"]["sha256"] = "b"*64
    elif change == "roster":
        diagnostic = dict(world["binding"], comparison_roster=None)
        spec["source_bindings"] = pin(world["data"], "diagnostic-source.json", diagnostic)
    else:
        next(iter(world["summaries"].values())).rows.clear()
    with pytest.raises(PreparedFeedbackError):
        load(world, spec)


@pytest.mark.parametrize("kind", ["tie", "unusable"])
def test_no_update_groups_remain_in_full_report_but_not_execution_context(comparison_world, kind):
    world = comparison_world
    if kind == "tie":
        for group in world["groups"].values():
            group["rows"][0]["fp"] = 0
    else:
        next(iter(world["summaries"].values())).rows[world["actor"].sample_ids[0]]["status"] = "output-limit"
    with pytest.raises(PreparedFeedbackError, match="ordered ready"):
        module.build_system_comparison_contexts(world["source_pin"], data_root=world["data"])
    world["binding"]["comparison_roster"] = None
    source_pin = pin(world["data"], "diagnostic-source.json", world["binding"])
    result = module.build_system_comparison_contexts(source_pin, data_root=world["data"])
    assert result["contexts"] == [] and len(result["comparison"]["groups"]) == 1
    expected = "no-update-terminal-tie" if kind == "tie" else "blocked-unusable-summary"
    assert result["comparison"]["groups"][0]["disposition"] == expected
    assert result["model_contacts_added"] == result["scorer_contacts_added"] == 0


@pytest.mark.parametrize("change", ["role", "cohort", "limit", "artifact"])
def test_active_context_binding_is_exact(comparison_world, change):
    world = comparison_world
    spec, _ = prepared(world)
    kwargs = {}
    if change == "role":
        kwargs["result_kind"] = "task-answer"
    elif change == "cohort":
        kwargs["sample_ids"] = ("slurp:train:other",)
    elif change == "limit":
        spec["max_context_bytes"] = 5
    else:
        spec["artifact"]["sha256"] = "f"*64
    with pytest.raises((PreparedFeedbackError, ValueError)):
        load(world, spec, **kwargs)


def test_public_preparation_cli_uses_shared_cached_artifact(comparison_world, capsys):
    world = comparison_world
    args = ["--data-root", str(world["data"]), "--source-relpath", world["source_pin"]["relpath"],
            "--source-sha256", world["source_pin"]["sha256"], "--output-relpath", "prepared/cli.json"]
    assert module.main(args) == 0
    cold = json.loads(capsys.readouterr().out)
    assert module.main(args) == 0
    warm = json.loads(capsys.readouterr().out)
    assert cold["sha256"] == warm["sha256"] and warm["cache"] == "warm"


def test_comparison_reaches_shared_runtime_fit_send_and_raw_artifact(comparison_world, tmp_path):
    from test_system_summary_preparation import exercise_shared_fit_and_send
    world = comparison_world
    spec, _ = prepared(world)
    world_inputs = (world["data"], world["actor"],
                    {"construction_roster": world["binding"]["comparison_roster"]},
                    world["source_pin"], world["calls"])
    exercise_shared_fit_and_send(
        world_inputs, tmp_path, True, prepared_spec=spec,
        baseline="system-semantic-comparison-text-v1", comparison=True)


def test_comparison_cannot_switch_to_fresh_speech_arm(tmp_path):
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntimeError, validate_artifact_result_binding,
    )
    values = {"prepared_training_feedback": {"schema": module.PREPARED_COMPARISON_SCHEMA},
              "arm": "speech-supplied-feature"}
    with pytest.raises(FlightRuntimeError, match="prepared text arm"):
        validate_artifact_result_binding(values, plan=None, repo_root=tmp_path, sample_ids=())


def test_text_summary_prompt_has_accurate_input_contract():
    repo = Path(__file__).parents[2]
    values = json.loads((repo / "configs/baseline/system-trajectory-summary-text-v1.json").read_text())
    text = (repo / "configs" / values["phase_material"]["direct"]["instruction_template"]).read_text()
    assert "No fresh speech" in text
    assert "original speech is attached" not in text
    old_values = json.loads((repo / "configs/baseline/system-trajectory-summary-v1.json").read_text())
    assert old_values["phase_material"]["direct"] != values["phase_material"]["direct"]
