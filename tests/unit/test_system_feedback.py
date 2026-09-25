"""Complete system/score joins; the shared native verifier has its own suite."""
import copy
import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis import system_feedback as module
from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts
from speech_aware_evidence_acquisition.rails.finite_policy_artifacts import PolicyArtifactError
from test_finite_policy_artifacts import write_pin
from test_system_trajectory import _source


@pytest.fixture
def world(tmp_path, monkeypatch, request):
    root = tmp_path / "data"
    (root / "run").mkdir(parents=True)
    if getattr(request, "param", None) == "system-policy":
        from test_system_trajectory import _source_with_policy_decision
        source, _ = _source_with_policy_decision()
    else:
        source = _source()
    source.plan.split_role = "discovery"
    source.plan.split_identity_hash = "d" * 64
    score_id = "slurp-slu-official-train"
    scores = {score_id: {
        "per_sample": [{"sample_id": "s1", "scenario_action_exact": 1,
                        **{f"slu_f1_{kind}_{metric}": 1
                           for kind in ("word", "char") for metric in ("tp", "fp", "fn")}}],
        "aggregate": {"official": {"slu_f1": 0.5}},
    }}
    scores_pin = write_pin(root, "run/scores.json", scores)
    outputs_pin = write_pin(root, "run/outputs.jsonl", source.output_rows["s1"])
    outputs_path = root / outputs_pin["relpath"]
    source.bundle.outputs_path = outputs_path
    source.bundle.manifest.update({
        "scorers": [score_id],
        "outputs": {"path": str(outputs_path), "sha256": outputs_pin["sha256"]},
        "scores": {"path": str(root / scores_pin["relpath"]), "sha256": scores_pin["sha256"]},
    })
    manifest_pin = write_pin(root, "run/manifest.json", source.bundle.manifest)
    phase_pin = write_pin(root, "run/phases.json", {"results": list(source.phase_results.values())})
    source = replace(source, phase_artifact_sha256=phase_pin["sha256"])
    jobs_pin = write_pin(root, "run/score-jobs.jsonl", {
        "job_id": "attempt", "manifest": str(root / manifest_pin["relpath"]),
        "ledger_cells": str(root / "run/score-ledger-cells.json"),
    })
    ledger_pin = write_pin(root, "run/score-ledger-cells.json", {"cell": "source-cell"})
    generation = copy.deepcopy(source.bundle.manifest)
    generation["scores"] = None
    generation_pin = write_pin(root, "run/generation-manifest.json", generation)
    ledger = FlightReceipts("run", "attempt")
    for stage in ("preflight", "preprocess", "serve", "run_phases"):
        ledger.record(stage, {})
    ledger.record("seal", {
        "manifest_path": str(root / manifest_pin["relpath"]), "manifest_sha256": generation_pin["sha256"],
        "phases_path": str(root / phase_pin["relpath"]), "phases_sha256": phase_pin["sha256"],
        "outputs_path": str(outputs_path), "outputs_row_count": 1, "phase_count": 1,
        "finalize": {"status": "deferred-to-score-worker"},
        "generation_manifest_path": str(root / generation_pin["relpath"]),
        "generation_manifest_sha256": generation_pin["sha256"],
        "score_jobs_path": str(root / jobs_pin["relpath"]), "score_jobs_sha256": jobs_pin["sha256"],
        "score_ledger_cells_path": str(root / ledger_pin["relpath"]),
        "score_ledger_cells_sha256": ledger_pin["sha256"],
    })
    ledger.record("score", {
        "jobs_path": str(root / jobs_pin["relpath"]), "operation": "finalize",
        "job_count": 1, "include_per_sample": True,
        "source_generation_manifest_sha256": generation_pin["sha256"],
        "finalized_manifest_sha256": manifest_pin["sha256"],
        "result": {"failed": 0, "succeeded": 1, "job_count": 1, "operation": "finalize",
                   "jobs": [{"job_id": "attempt", "manifest": str(root / manifest_pin["relpath"]),
                             "ledger_cells": str(root / ledger_pin["relpath"]),
                             "operation": "finalize", "status": "succeeded", "returncode": 0}]},
    })
    receipts_pin = write_pin(root, "run/flight-receipts.json", ledger.as_json())
    binding = {
        "schema": "saea-system-feedback-binding-v1", "execution_profile": "model-free-check",
        "feedback_role": "construction", "manifest": manifest_pin, "phases": phase_pin,
        "flight_receipts": receipts_pin, "score_jobs": jobs_pin, "scorer_id": score_id,
    }
    monkeypatch.setattr(module, "verify_native_episode_source", lambda **kwargs: source)
    return SimpleNamespace(root=root, source=source, binding=binding, scores=scores, scorer=score_id)


def load(world):
    return module.load_system_feedback(data_root=world.root, repo_root=world.root, binding=world.binding)


def repin_scores(world):
    pin = write_pin(world.root, "run/scores.json", world.scores)
    world.source.bundle.manifest["scores"]["sha256"] = pin["sha256"]
    world.binding["manifest"] = write_pin(world.root, "run/manifest.json", world.source.bundle.manifest)
    # Source completion is separately mocked; rehash the synthetic final score stage.
    rebind_receipts(world, lambda receipt: receipt["stages"]["score"].update(
        finalized_manifest_sha256=world.binding["manifest"]["sha256"]))


def rebind_receipts(world, mutation):
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    path = world.root / "run/flight-receipts.json"
    receipt = json.loads(path.read_text())
    mutation(receipt)
    for stage in receipt["stages"].values():
        stage.pop("stage_hash", None)
        stage["stage_hash"] = content_hash(stage)
    receipt.pop("receipts_hash", None)
    receipt["receipts_hash"] = content_hash(receipt)
    world.binding["flight_receipts"] = write_pin(world.root, "run/flight-receipts.json", receipt)


def test_terminal_feedback_binds_all_roles_without_putting_reward_in_role_context(world):
    result = load(world)
    row = result["system_trajectories"]["trajectories"][0]
    assert [v["stage"] for v in row["role_visits"]] == ["perception", "solver", "review", "planner"]
    feedback = result["terminal_feedback"][0]
    assert feedback["trajectory_sha256"] == row["trajectory_sha256"]
    assert (feedback["tp"], feedback["fp"], feedback["fn"]) == (2, 2, 2)
    assert feedback["intent_exact"] == 1
    assert "terminal_feedback" not in json.dumps(row)
    assert result["model_contacts_added"] == result["scorer_contacts_added"] == 0
    assert result["source_bindings"] == world.binding
    assert "generation_manifest" in result["resolved_auxiliary_sources"]
    assert feedback["episode_events"]["truncation_events"]["status"] == "unavailable_in_source"


@pytest.mark.parametrize("mutation", ("duplicate", "foreign", "boolean", "missing", "aggregate"))
def test_incomplete_or_invalid_official_feedback_is_refused(world, mutation):
    entry = world.scores[world.scorer]
    if mutation == "duplicate":
        entry["per_sample"].append(copy.deepcopy(entry["per_sample"][0]))
    elif mutation == "foreign":
        entry["per_sample"][0]["sample_id"] = "outside-roster"
    elif mutation == "boolean":
        entry["per_sample"][0]["slu_f1_word_fp"] = True
    elif mutation == "missing":
        entry["per_sample"][0].pop("slu_f1_char_fn")
    else:
        entry["aggregate"]["official"]["slu_f1"] = 0.75
    repin_scores(world)
    with pytest.raises(ValueError):
        load(world)


def test_empty_gold_hallucination_has_nonzero_false_positive_feedback(world):
    row = world.scores[world.scorer]["per_sample"][0]
    for kind in ("word", "char"):
        row[f"slu_f1_{kind}_tp"] = row[f"slu_f1_{kind}_fn"] = 0
    world.scores[world.scorer]["aggregate"]["official"]["slu_f1"] = 0
    repin_scores(world)
    feedback = load(world)["terminal_feedback"][0]
    assert (feedback["tp"], feedback["fp"], feedback["fn"]) == (0, 2, 0)


def test_official_metrics_are_not_silently_replaced_with_a_normalized_view(world):
    world.scores[world.scorer]["per_sample"][0]["normalized"] = {"slu_f1_word_fp": 100}
    repin_scores(world)
    assert load(world)["terminal_feedback"][0]["fp"] == 2


def test_wrong_score_job_and_source_hash_cannot_update_feedback(world):
    world.binding["score_jobs"] = write_pin(world.root, "run/score-jobs.jsonl", {
        "job_id": "foreign", "manifest": str(world.root / "run/manifest.json"),
    })
    with pytest.raises(module.SystemFeedbackError, match="attempt"):
        load(world)
    world.binding["manifest"]["sha256"] = "e" * 64
    with pytest.raises(PolicyArtifactError, match="SHA"):
        load(world)


def test_evaluation_feedback_is_never_admitted_to_construction(world):
    world.binding["feedback_role"] = "evaluation"
    with pytest.raises(module.SystemFeedbackError, match="TRAIN"):
        load(world)


def test_derived_report_is_repeatable_but_cannot_overwrite_another_source(world):
    report = load(world)
    path = world.root / "analysis" / "system.json"
    first = module.write_system_feedback(path, report)
    assert module.write_system_feedback(path, report) == first
    original = path.read_bytes()
    assert json.loads(original) == report
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    changed = dict(report, run_id="different-run")
    changed.pop("content_sha256")
    changed["content_sha256"] = content_hash(changed)
    with pytest.raises(module.SystemFeedbackError, match="overwrite"):
        module.write_system_feedback(path, changed)
    assert path.read_bytes() == original


@pytest.mark.parametrize("mutation", ("job-pin", "job-path", "failed", "missing-score",
                                    "wrong-operation", "wrong-generation", "wrong-final",
                                    "wrong-result-attempt", "missing-per-sample"))
def test_official_score_requires_the_complete_flight_scoring_custody(world, mutation):
    if mutation == "job-pin":
        job = json.loads((world.root / "run/score-jobs.jsonl").read_text())
        job["ledger_cells"] = str(world.root / "run/substituted-ledger.json")
        world.binding["score_jobs"] = write_pin(world.root, "run/score-jobs.jsonl", job)
    else:
        def change(receipt):
            stage = receipt["stages"]["score"]
            if mutation == "job-path":
                stage["jobs_path"] = str(world.root / "run/other-jobs.jsonl")
            elif mutation == "failed":
                stage["result"]["failed"] = 1
            elif mutation == "missing-score":
                receipt["stages"].pop("score")
            elif mutation == "wrong-operation":
                stage["operation"] = "score"
            elif mutation == "wrong-generation":
                stage["source_generation_manifest_sha256"] = "e" * 64
            elif mutation == "wrong-final":
                stage["finalized_manifest_sha256"] = "e" * 64
            elif mutation == "wrong-result-attempt":
                stage["result"]["jobs"][0]["job_id"] = "other-attempt"
            else:
                stage["include_per_sample"] = False
        rebind_receipts(world, change)
    with pytest.raises(ValueError):
        load(world)


def test_score_ledger_changed_after_generation_seal_is_refused(world):
    write_pin(world.root, "run/score-ledger-cells.json", {"cell": "different-cell"})
    with pytest.raises(PolicyArtifactError, match="SHA"):
        load(world)


@pytest.mark.parametrize("world", ["system-policy"], indirect=True)
def test_verified_whole_policy_choice_stays_joined_to_official_terminal_feedback(world):
    report = load(world)
    choice = report["policy_episode_decisions"]["s1"]
    episode = report["system_trajectories"]["trajectories"][0]
    final = report["terminal_feedback"][0]
    assert choice == episode["system_policy_decision"]
    assert final["trajectory_sha256"] == episode["trajectory_sha256"]
    assert choice["record"]["sample_id"] == final["sample_id"]
    assert choice["claim_scope"] == "recorded-choice-not-learning-admission"
    assert "terminal_feedback" not in str(choice)
