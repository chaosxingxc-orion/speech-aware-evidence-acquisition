# ruff: noqa: F811  # imported pytest fixture shares its requested name
"""Offline own-trajectory projection for TRAIN feedback proposal, with no gold reads."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_group_relative_feedback import native_source_pair, source_pair  # noqa: F401

from speech_aware_evidence_acquisition.rails.training_proposal_context import (
    TrainingProposalContextError, build_training_proposal_contexts,
    prepare_training_proposal_contexts,
)

pytest_plugins = ("test_bundle",)


def test_verified_context_preserves_own_answers_feedback_and_source_pins(source_pair):  # noqa: F811
    document = build_training_proposal_contexts(source_pair)
    assert len(document["contexts"]) == 2
    for row in document["contexts"]:
        model = row["model_context"]
        assert len(model["candidates"]) == 2
        for candidate in model["candidates"]:
            assert len(candidate["trajectory"]) in {3, 4}
            assert all(
                step["response"] is None or "synthetic-answer" in step["response"]
                for step in candidate["trajectory"]
            )
            assert sum(step["selected_final"] for step in candidate["trajectory"]) == 1
            assert len(candidate["quality"]) == 7
        text = json.dumps(model)
        assert "slurp:train:" not in text
        assert "reference" not in text
        assert "source_sample_id" not in text
        assert all(isinstance(v, (int, float)) for c in model["candidates"]
                   for v in c["native_counts"].values())
        assert row["source_sample_id"].startswith("slurp:train:")
        assert len(row["source_feedback_sha256"]) == 64


def test_context_projection_never_opens_dataset_references(source_pair, monkeypatch):  # noqa: F811
    original = Path.read_bytes
    def guarded(path, *args, **kwargs):
        assert "datasets" not in str(path)
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_bytes", guarded)
    assert build_training_proposal_contexts(source_pair)["status"] == "source-verified"


def test_prepared_context_is_stable_and_warm_source_tamper_is_refused(source_pair, tmp_path):  # noqa: F811
    path = tmp_path / "contexts.json"
    first = prepare_training_proposal_contexts(source_pair, path)
    second = prepare_training_proposal_contexts(source_pair, path)
    assert first["sha256"] == second["sha256"]
    source = Path(source_pair[0]["config"]["manifest"]["path"])
    source.write_text("{}")
    with pytest.raises(TrainingProposalContextError):
        prepare_training_proposal_contexts(source_pair, path)



def test_real_supplied_evidence_is_deduplicated_and_private_metadata_stays_hidden(source_pair):
    document = build_training_proposal_contexts(source_pair)
    for row in document["contexts"]:
        model = row["model_context"]
        serialized = json.dumps(model)
        assert "/private/cache/" not in serialized
        assert "private-evidence:" not in serialized
        for candidate in model["candidates"]:
            assert candidate["evidence"] == [{
                "label": "evidence-1",
                "content": "independent observation",
                "kind": "observation",
            }]
            uses = [
                step["evidence_labels"]
                for step in candidate["trajectory"]
                if step["evidence_labels"]
            ]
            assert uses == [["evidence-1"], ["evidence-1"]]


def test_failed_contact_is_retained_without_fabricating_a_response(source_pair):
    document = build_training_proposal_contexts(source_pair)
    first = document["contexts"][0]["model_context"]["candidates"]
    for candidate in first:
        failed = [step for step in candidate["trajectory"] if step["action"].startswith("synthetic-program:failed")]
        assert failed == [{
            "action": "synthetic-program:failed",
            "instruction": "Inspect the available evidence.",
            "response": None,
            "response_observed": False,
            "selected_final": False,
            "evidence_labels": [],
        }]


def test_model_context_is_label_free_and_hides_all_source_identities(source_pair):
    document = build_training_proposal_contexts(source_pair)
    hidden = set()
    for source in document["sources"]:
        hidden.update((source["candidate_id"], source["run_id"], source["attempt_id"]))
        hidden.add(source["manifest"]["path"])
        hidden.add(source["reward_artifact"]["path"])
    hidden.update(row["source_sample_id"] for row in document["contexts"])
    for row in document["contexts"]:
        serialized = json.dumps(row["model_context"])
        assert not any(value in serialized for value in hidden)
        assert all(word not in serialized.lower() for word in ("gold_call", "reference_text", "construction_targets"))


def test_selected_response_must_match_verified_reward_lineage(source_pair, monkeypatch):
    import speech_aware_evidence_acquisition.rails.training_proposal_context as module

    original = module._source_trajectories

    def wrong_final(*args, **kwargs):
        result = original(*args, **kwargs)
        first = next(iter(result))
        result[first]["final_response_sha256"] = "f" * 64
        return result

    monkeypatch.setattr(module, "_source_trajectories", wrong_final)
    with pytest.raises(TrainingProposalContextError, match="response lineage"):
        build_training_proposal_contexts(source_pair)


def test_native_train_context_keeps_role_revisits_and_selected_solver(native_source_pair):
    document = build_training_proposal_contexts(native_source_pair)
    assert document["status"] == "source-verified"
    assert len(document["contexts"]) == 2
    for row in document["contexts"]:
        model = row["model_context"]
        assert "slurp:train:" not in json.dumps(model)
        for candidate in model["candidates"]:
            trajectory = candidate["trajectory"]
            assert len(trajectory) == 9
            assert sum(step["action"].startswith("synthetic-program:reviewer:")
                       for step in trajectory) == 4
            selected = [step for step in trajectory if step["selected_final"]]
            assert len(selected) == 1
            assert selected[0]["action"] == "synthetic-program:solver:1"
            assert selected[0]["response"].endswith("-solver-1")
            assert trajectory[-1]["action"] == "synthetic-program:planner:1"
            assert not trajectory[-1]["selected_final"]
            assert len(candidate["quality"]) == 7
