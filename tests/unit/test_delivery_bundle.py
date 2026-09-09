"""Synthetic parent-flight/replay parity and fail-closed provenance tests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
import test_e21_repair_loop as fixtures


from speech_aware_evidence_acquisition.core.bundle import BundleError, verify_bundle
from speech_aware_evidence_acquisition.core.bundle.delivery import build_delivery_bundle
from speech_aware_evidence_acquisition.core.config import compose

repair_repo = fixtures.repair_repo

FREE = "e21-free-refresh-delivery-v1"
CONSTRAINED = "e21-entity-repair-substitutions-v1"


@pytest.fixture
def generation(synthetic_world, tmp_path, repair_repo, monkeypatch):
    def run(*, policy="obs-repair-loop", transport=None, **overrides):
        _, repo, digest = repair_repo
        values = dict(fixtures._composed(digest, policy=policy, **overrides).values)
        experiment = {
            "experiment_id": values.pop("experiment_id"),
            "cells": [
                {
                    "cell_id": "generation",
                    "model_fragment": "m",
                    "dataset_fragment": "d",
                    "baseline_fragment": "b",
                }
            ],
            "delivery_derivatives": [
                {
                    "cell_id": "constrained",
                    "parent_cell_id": "generation",
                    "response_postprocessor": CONSTRAINED,
                    "response_postprocessor_params": {"max_substituted_fraction": 0.25},
                },
                {
                    "cell_id": "free",
                    "parent_cell_id": "generation",
                    "response_postprocessor": FREE,
                    "response_postprocessor_params": {},
                },
            ],
        }
        for kind, name, document in (
            ("model", "m", {}),
            ("dataset", "d", {}),
            ("baseline", "b", values),
            ("experiment", "e", experiment),
        ):
            path = repo / "configs" / kind / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(document), encoding="utf-8")
        fixtures._git(repo, "add", "configs")
        fixtures._git(repo, "commit", "-q", "-m", "predeclare both delivery rules")
        composed = compose(repo, "m", "d", "b", "e")
        monkeypatch.setattr(fixtures, "_composed", lambda *_args, **_kw: composed)
        if transport is None:
            transport = fixtures._transport_factory(
                lambda text: "  " + text.replace("Ponton", "Pontone") + " "
            )
        parent, _ = fixtures._run(synthetic_world, tmp_path, repair_repo, transport)
        kwargs = dict(
            parent_manifest=parent,
            repo_root=repo,
            experiment_path=repo / "configs/experiment/e.json",
            data_root=synthetic_world.data_root,
        )
        return parent, kwargs

    return run


def _build(tmp_path, kwargs, cell="constrained"):
    return build_delivery_bundle(
        **kwargs, derivative_cell_id=cell, output_dir=tmp_path / f"derived-{cell}"
    )


@pytest.mark.parametrize("policy", ["obs-repair-loop", "obs-repair-loop-ojw"])
def test_live_and_replay_share_identical_window_delivery(generation, tmp_path, policy):
    parent, kwargs = generation(policy=policy)
    parent_before = parent.read_bytes()
    derived = verify_bundle(_build(tmp_path, kwargs))
    original = verify_bundle(parent)
    assert [row["text"] for row in derived.outputs_rows] == [
        row["text"] for row in original.outputs_rows
    ]
    assert len(derived.manifest["windows"]) == 6
    assert derived.trace_records == original.trace_records
    assert derived.manifest["cost"]["calls_used"] == 0
    assert derived.manifest["cost"]["parent_generation_cost"]["calls_used"] == 6
    assert parent.read_bytes() == parent_before
    assert all("response_sha256" not in row for row in derived.outputs_rows)


def test_free_rule_can_replay_shared_response_without_new_contact(generation, tmp_path):
    parent, kwargs = generation(
        transport=fixtures._transport_factory(lambda text: text + " added words")
    )
    original = verify_bundle(parent)
    constrained = verify_bundle(_build(tmp_path, kwargs))
    free = verify_bundle(_build(tmp_path, kwargs, "free"))
    assert [row["text"] for row in constrained.outputs_rows] == [
        row["text"] for row in original.outputs_rows
    ]
    assert all(row["text"].count("added words") == 2 for row in free.outputs_rows)
    assert free.manifest["parent"]["sha256"] == constrained.manifest["parent"]["sha256"]


@pytest.mark.parametrize("failure", ["retry", "skip", "saturated"])
def test_terminal_identity_and_fallback_include_every_window(
    generation, tmp_path, failure
):
    def transport(raw):
        payload = json.loads(raw)
        rid = payload["request_id"]
        first = "-i0000" in rid
        if first and (
            failure == "skip" or (failure == "retry" and not rid.endswith("-r1"))
        ):
            raise TimeoutError("synthetic retry")
        return json.dumps(
            {
                "text": "  "
                + fixtures._predecessor_of(payload).replace("Ponton", "Pontone")
                + " ",
                "usage": {
                    "completion_tokens": 10 if first and failure == "saturated" else 1
                },
            }
        ).encode()

    parent, kwargs = generation(
        transport=transport,
        obs_slice_retry_max=1,
        decoding_params={"temperature": 0, "max_tokens": 10},
    )
    original = verify_bundle(parent)
    derived = verify_bundle(_build(tmp_path, kwargs))
    assert [r["text"] for r in derived.outputs_rows] == [
        r["text"] for r in original.outputs_rows
    ]
    assert len(derived.manifest["windows"]) == 6
    first_windows = [w for w in derived.manifest["windows"] if w["window_index"] == 1]
    for window in first_windows:
        assert window["terminal_request_id"].endswith("-r1") == (failure != "saturated")
        assert window["skipped"] == (failure == "skip")
        if failure in ("skip", "saturated"):
            assert window["normalized_input_sha256"] == hashlib.sha256(b"").hexdigest()
            assert window["delivered_text_sha256"] == window["predecessor_text_sha256"]
        if failure == "skip":
            assert window["response_record_sha256"] is None


@pytest.mark.parametrize(
    "field", ["parent", "rule_sources", "windows", "outputs", "cost", "scorers"]
)
def test_verifier_refuses_provenance_or_output_tampering(generation, tmp_path, field):
    _, kwargs = generation()
    path = _build(tmp_path, kwargs)
    document = json.loads(path.read_text())
    if field in ("parent", "outputs"):
        document[field]["sha256"] = "0" * 64
    elif field == "rule_sources":
        document[field]["core/delivery.py"] = "0" * 64
    elif field == "windows":
        document[field][0]["terminal_request_id"] += "-r99"
    elif field == "cost":
        document[field]["calls_used"] = 6
    else:
        document[field] = ["cost"]
    path.write_text(json.dumps(document))
    with pytest.raises(BundleError):
        verify_bundle(path)


def test_declared_rule_must_precede_generation_and_output_directory_is_new(
    generation, tmp_path
):
    _, kwargs = generation()
    _build(tmp_path, kwargs)
    with pytest.raises(BundleError, match="exist"):
        _build(tmp_path, kwargs)
    experiment = kwargs["experiment_path"]
    document = json.loads(experiment.read_text())
    document["delivery_derivatives"][0]["response_postprocessor_params"] = {}
    experiment.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="config"):
        build_delivery_bundle(
            **kwargs, derivative_cell_id="constrained", output_dir=tmp_path / "late"
        )


def test_registered_scorers_receive_one_complete_derived_manifest(
    generation, tmp_path, monkeypatch, synthetic_world
):
    from speech_aware_evidence_acquisition.core import scorers
    from speech_aware_evidence_acquisition.core.scoring_batch import load_score_jobs

    _, kwargs = generation(scorers=["asr-wer", "cost"])
    path = _build(tmp_path, kwargs)
    bundle = verify_bundle(path)
    gate_calls = []
    monkeypatch.setattr(
        scorers, "_assert_scoring_entry_gate", lambda *args: gate_calls.append(args)
    )
    from speech_aware_evidence_acquisition.data.lock import load_lock

    lock = load_lock(synthetic_world.lock_path)
    result = scorers.score_bundle(
        bundle, lock, kwargs["data_root"], repo_root=kwargs["repo_root"]
    )
    assert len(gate_calls) == 1
    assert len(result["asr-wer"]["per_sample"]) == 3
    assert result["cost"]["aggregate"]["calls_used"] == 0
    assert result["cost"]["aggregate"]["parent_generation_cost"]["calls_used"] == 6
    jobs = tmp_path / "score-jobs.jsonl"
    jobs.write_text(json.dumps({"job_id": "derived", "manifest": str(path)}) + "\n")
    assert load_score_jobs(jobs)[0].manifest == path


def test_derived_artifact_cannot_finalize_or_change_parent_attempt(
    generation, tmp_path
):
    from speech_aware_evidence_acquisition.core.bundle import finalize_bundle

    parent, kwargs = generation()
    path = _build(tmp_path, kwargs)
    parent_doc = json.loads(parent.read_text())
    attempt = Path(parent_doc["attempt"]["state_path"])
    before = attempt.read_bytes()
    with pytest.raises(BundleError, match="derivative.*finalize|finalize.*derivative"):
        finalize_bundle(path, {}, kwargs["data_root"], repo_root=kwargs["repo_root"])
    assert attempt.read_bytes() == before


def test_recomputed_outer_output_hash_cannot_hide_modified_delivery(
    generation, tmp_path
):
    _, kwargs = generation()
    path = _build(tmp_path, kwargs)
    document = json.loads(path.read_text())
    outputs = Path(document["outputs"]["path"])
    rows = [json.loads(line) for line in outputs.read_text().splitlines()]
    rows[0]["text"] = "invented delivery"
    raw = b"".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        for row in rows
    )
    outputs.write_bytes(raw)
    document["outputs"]["sha256"] = document["outputs_sha256"] = hashlib.sha256(
        raw
    ).hexdigest()
    path.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="recomputation|replay"):
        verify_bundle(path)


def _attach_synthetic_scores(parent, document):
    from speech_aware_evidence_acquisition.core.bundle.manifest import _attach_scores

    scores = parent.parent / "synthetic.scores.json"
    scores.write_text(json.dumps(document))
    _attach_scores(parent, scores)
    return scores


def test_identical_view_reuses_complete_source_scores_without_rescoring(
    generation, tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core import scorers

    parent, kwargs = generation(scorers=["asr-wer", "cost"])
    expected = {
        "asr-wer": {
            "aggregate": {"samples": 3},
            "per_sample": [
                {"sample_id": sample_id, "wer": 0.123} for sample_id in fixtures.E21_IDS
            ],
        },
        "cost": {"aggregate": {"calls_used": 6}, "per_sample": []},
    }
    _attach_synthetic_scores(parent, expected)
    derived = verify_bundle(_build(tmp_path, kwargs))
    assert (
        derived.manifest["score_reuse"]["source_run_id"]
        == verify_bundle(parent).manifest["run_id"]
    )
    monkeypatch.setattr(scorers, "_assert_scoring_entry_gate", lambda *args: None)

    def forbid(*args):
        pytest.fail("identical source scores must not invoke a scorer again")

    monkeypatch.setattr(scorers.SCORERS, "resolve", forbid)
    result = scorers.score_bundle(
        derived, {}, kwargs["data_root"], repo_root=kwargs["repo_root"]
    )
    assert result["asr-wer"] == expected["asr-wer"]
    assert result["cost"]["aggregate"]["calls_used"] == 0


def test_changed_free_output_does_not_reuse_source_scores(generation, tmp_path):
    parent, kwargs = generation(
        transport=fixtures._transport_factory(lambda text: text + " added words")
    )
    _attach_synthetic_scores(parent, {"asr-wer": {"aggregate": {}, "per_sample": []}})
    free = verify_bundle(_build(tmp_path, kwargs, "free"))
    assert free.manifest["score_reuse"] is None


@pytest.mark.parametrize(
    "scores",
    [
        {"asr-wer": {"aggregate": {}}},
        {"asr-wer": {"aggregate": {}, "per_sample": [{"sample_id": "wrong"}]}},
        {"other-scorer": {"aggregate": {}, "per_sample": []}},
    ],
)
def test_score_reuse_refuses_incomplete_or_unpaired_source_scores(
    generation, tmp_path, monkeypatch, scores
):
    from speech_aware_evidence_acquisition.core import scorers

    parent, kwargs = generation()
    _attach_synthetic_scores(parent, scores)
    bundle = verify_bundle(_build(tmp_path, kwargs))
    monkeypatch.setattr(scorers, "_assert_scoring_entry_gate", lambda *args: None)
    with pytest.raises(scorers.ScoringPhaseError, match="reus"):
        scorers.score_bundle(
            bundle, {}, kwargs["data_root"], repo_root=kwargs["repo_root"]
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-window",
        "duplicate-window",
        "predecessor",
        "bounds",
        "request-hash",
        "response-hash",
        "saturation",
        "fabricated-skip",
        "retry",
        "stitch-order",
        "selective",
    ],
)
def test_replay_cross_checks_terminal_evidence_even_after_outer_trace_verification(
    generation, tmp_path, mutation
):
    from dataclasses import replace
    from speech_aware_evidence_acquisition.core.bundle.delivery_replay import (
        replay_delivery,
    )
    from speech_aware_evidence_acquisition.core.predecessor_snapshot import (
        load_predecessor_binding,
    )

    parent_path, kwargs = generation()
    parent = verify_bundle(parent_path)
    values = compose(kwargs["repo_root"], "m", "d", "b", "e").values
    snapshot = load_predecessor_binding(
        kwargs["repo_root"] / "docs" / fixtures.BINDING_RELPATH, kwargs["data_root"]
    )
    records = json.loads(json.dumps(parent.trace_records))
    rid = next(
        rid[:-4]
        for rid in records
        if rid.endswith("/obs") and records[rid].get("obs_repair")
    )
    obs = records[f"{rid}/obs"]
    if mutation == "missing-window":
        del records[f"{rid}/obs"]
    elif mutation == "duplicate-window":
        records[f"{rid}-r1/obs"] = dict(obs)
    elif mutation == "predecessor":
        obs["obs_repair_predecessor_text_sha256"] = "0" * 64
    elif mutation == "bounds":
        obs["obs_window_end_seconds"] += 1
    elif mutation == "request-hash":
        records[f"{rid}/request"]["payload_sha256"] = "0" * 64
    elif mutation == "response-hash":
        records[f"{rid}/response"]["text"] += " corrupt"
    elif mutation == "saturation":
        obs["obs_saturated"] = True
    elif mutation == "fabricated-skip":
        obs["obs_skipped"] = True
    elif mutation == "retry":
        obs["obs_retry_of"] = "wrong"
    elif mutation == "stitch-order":
        root = parent.outputs_rows[0]["request_id"]
        records[f"{root}/request"]["stitched_request_ids"].reverse()
    else:
        obs["obs_relisten"] = True
    with pytest.raises(BundleError):
        replay_delivery(
            replace(parent, trace_records=records),
            snapshot,
            values["delivery_derivatives"][0],
            values,
        )


def test_parent_score_tamper_and_output_path_escape_are_refused(generation, tmp_path):
    parent, kwargs = generation()
    scores = _attach_synthetic_scores(
        parent, {"asr-wer": {"aggregate": {}, "per_sample": []}}
    )
    path = _build(tmp_path, kwargs)
    document = json.loads(path.read_text())
    original = scores.read_bytes()
    scores.write_bytes(b"{}")
    with pytest.raises(BundleError, match="hash"):
        verify_bundle(path)
    scores.write_bytes(original)
    outside = tmp_path / "outside.outputs.jsonl"
    outside.write_bytes(Path(document["outputs"]["path"]).read_bytes())
    document["outputs"]["path"] = str(outside)
    path.write_text(json.dumps(document))
    with pytest.raises(BundleError, match="directory"):
        verify_bundle(path)


def test_derivative_cannot_be_used_as_generation_parent(generation, tmp_path):
    _, kwargs = generation()
    derivative = _build(tmp_path, kwargs)
    kwargs["parent_manifest"] = derivative
    with pytest.raises(BundleError, match="ordinary generation"):
        build_delivery_bundle(
            **kwargs, derivative_cell_id="free", output_dir=tmp_path / "recursive"
        )


def test_unregistered_cell_and_repository_output_refuse_before_writes(
    generation, tmp_path
):
    _, kwargs = generation()
    with pytest.raises(BundleError, match="uniquely declared"):
        build_delivery_bundle(
            **kwargs, derivative_cell_id="unknown", output_dir=tmp_path / "unknown"
        )
    assert not (tmp_path / "unknown").exists()
    with pytest.raises(BundleError, match="outside repository"):
        build_delivery_bundle(
            **kwargs,
            derivative_cell_id="free",
            output_dir=kwargs["repo_root"] / "derived",
        )


def test_current_controller_generation_replays_without_replacing_its_trace(
    generation, tmp_path
):
    parent, kwargs = generation(
        policy="obs-repair-loop-ojw", obs_controller_program="phase-direct-only-v1"
    )
    original = verify_bundle(parent)
    assert (
        sum(rid.endswith("/window-controller") for rid in original.trace_records) == 6
    )
    derived = verify_bundle(_build(tmp_path, kwargs))
    assert derived.trace_records == original.trace_records
    assert [row["text"] for row in derived.outputs_rows] == [
        row["text"] for row in original.outputs_rows
    ]
