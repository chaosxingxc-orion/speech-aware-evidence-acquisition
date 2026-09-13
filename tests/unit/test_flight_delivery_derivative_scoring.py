"""Declared delivery parents build and score only their verified derivatives."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.receipts import FlightReceipts
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    FlightRuntimeError,
)
from speech_aware_evidence_acquisition.core.flight.scoring import (
    DeferredScoringError,
    prepare_declared_delivery_score_jobs,
)



def _write_experiment(path: Path, cells=("hard", "joint"), *, phase_selector=True):
    path.parent.mkdir(parents=True)
    derivatives = []
    for cell in cells:
        row = {"cell_id": cell, "parent_cell_id": "parent",
               "response_postprocessor": "synthetic", "response_postprocessor_params": {}}
        if phase_selector:
            row["source_selector"] = {"schema": "saea-phase-response-pair-v1"}
        derivatives.append(row)
    path.write_text(json.dumps({"delivery_derivatives": derivatives}) + "\n", encoding="utf-8")
def _sealed_parent(tmp_path: Path) -> tuple[Path, Path, str]:
    parent = tmp_path / "parent.run-manifest.json"
    parent.write_text('{"parent":true}\n', encoding="utf-8")
    generation = tmp_path / "parent.generation-manifest.json"
    generation.write_bytes(parent.read_bytes())
    return parent, generation, hashlib.sha256(parent.read_bytes()).hexdigest()


def _builder(calls: list[str]):
    def build(**kwargs):
        cell = kwargs["derivative_cell_id"]
        calls.append(cell)
        output = Path(kwargs["output_dir"])
        output.mkdir()
        manifest = output / f"derived--{cell}.run-manifest.json"
        manifest.write_text(json.dumps({"cell": cell}) + "\n", encoding="utf-8")
        return manifest

    return build


def test_preparation_builds_only_declared_cells_and_preserves_raw_parent(tmp_path):
    parent, generation, digest = _sealed_parent(tmp_path)
    experiment = tmp_path / "repo/configs/experiment/e.json"
    _write_experiment(experiment)
    raw = parent.read_bytes()
    calls: list[str] = []

    prepared = prepare_declared_delivery_score_jobs(
        parent_manifest=parent,
        generation_manifest=generation,
        generation_manifest_sha256=digest,
        repo_root=tmp_path / "repo",
        data_root=tmp_path,
        experiment_path=experiment,
        delivery_cells=("hard", "joint"),
        output_root=tmp_path / "deliveries",
        jobs_path=tmp_path / "delivery-score-jobs.jsonl",
        delivery_builder=_builder(calls),
    )

    assert calls == ["hard", "joint"]
    assert [job.job_id for job in prepared.jobs] == ["hard", "joint"]
    assert [row["cell_id"] for row in prepared.derivatives] == ["hard", "joint"]
    assert parent.read_bytes() == generation.read_bytes() == raw

@pytest.mark.parametrize("changed", ["parent", "generation", "missing-cell"])
def test_preparation_refuses_changed_or_invalid_inputs_before_builder(tmp_path, changed):
    parent, generation, digest = _sealed_parent(tmp_path)
    experiment = tmp_path / "repo/configs/experiment/e.json"
    _write_experiment(experiment)
    if changed == "parent":
        parent.write_text("changed\n", encoding="utf-8")
    elif changed == "generation":
        generation.write_text("changed\n", encoding="utf-8")
    cells = () if changed == "missing-cell" else ("hard",)
    calls: list[str] = []
    with pytest.raises(DeferredScoringError, match="generation|delivery cells"):
        prepare_declared_delivery_score_jobs(
            parent_manifest=parent,
            generation_manifest=generation,
            generation_manifest_sha256=digest,
            repo_root=tmp_path / "repo",
            data_root=tmp_path,
            experiment_path=experiment,
            delivery_cells=cells,
            output_root=tmp_path / "deliveries",
            jobs_path=tmp_path / "delivery-score-jobs.jsonl",
            delivery_builder=_builder(calls),
        )
    assert calls == []



def test_preparation_refuses_legacy_delivery_before_builder(tmp_path):
    parent, generation, digest = _sealed_parent(tmp_path)
    experiment = tmp_path / "repo/configs/experiment/e.json"
    _write_experiment(experiment, cells=("hard",), phase_selector=False)
    calls = []
    with pytest.raises(DeferredScoringError, match="phase selector"):
        prepare_declared_delivery_score_jobs(
            parent_manifest=parent,
            generation_manifest=generation,
            generation_manifest_sha256=digest,
            repo_root=tmp_path / "repo",
            data_root=tmp_path,
            experiment_path=experiment,
            delivery_cells=("hard",),
            output_root=tmp_path / "deliveries",
            jobs_path=tmp_path / "delivery-score-jobs.jsonl",
            delivery_builder=_builder(calls),
        )
    assert calls == []
def _runtime_for_score(tmp_path, *, score_batch, settler):
    parent, generation, digest = _sealed_parent(tmp_path)
    repo = tmp_path / "repo"
    experiment = repo / "configs/experiment/e.json"
    _write_experiment(experiment)
    runtime = object.__new__(FlightRuntime)
    runtime._require_prior_stages = lambda stage: None
    runtime._result_kind = lambda: "task"
    runtime._repo_root = repo
    runtime._data_root = tmp_path
    runtime._experiment = "e"
    runtime._run_id = "parent"
    runtime._attempt_id = "attempt-parent"
    runtime._plan = SimpleNamespace(attempt_id="attempt-parent")
    runtime._run_dir = lambda: tmp_path / "run"
    (tmp_path / "run").mkdir()
    runtime._clock = iter((10.0, 12.0)).__next__
    runtime._score_batch = score_batch
    runtime._delivery_builder = _builder([])
    runtime._delivery_settler = settler
    runtime.receipts = FlightReceipts("parent", "attempt-parent")
    runtime.receipts.record("seal", {
        "manifest_path": str(parent),
        "delivery_required": True,
        "declared_delivery_cells": ["hard", "joint"],
        "generation_manifest_path": str(generation),
        "generation_manifest_sha256": digest,
        "finalize": {"status": "deferred-to-declared-deliveries"},
    })
    return runtime, parent


def test_runtime_scores_each_derivative_once_and_settles_from_complete_receipts(tmp_path):
    seen = []
    settlements = []

    def score_batch(jobs, **kwargs):
        seen.extend(jobs)
        assert kwargs["max_workers"] == 1
        assert kwargs["include_per_sample"] is True
        output = Path(kwargs["output_dir"])
        output.mkdir()
        rows = []
        for job in jobs:
            name = f"{job.job_id}.complete-score-receipt.json"
            path = output / name
            path.write_text(json.dumps({"job": job.job_id}) + "\n")
            rows.append({"job_id": job.job_id, "status": "succeeded",
                         "complete_receipt_file": name,
                         "complete_receipt_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        return {"job_count": len(jobs), "failed": 0, "succeeded": len(jobs), "jobs": rows}

    def settle(parent_manifest, **kwargs):
        settlements.append((parent_manifest, kwargs))
        return SimpleNamespace(receipt_path=kwargs["settlement_path"],
                               receipt_sha256="a" * 64,
                               attempt_state="FINALIZED", reused=False)

    runtime, parent = _runtime_for_score(tmp_path, score_batch=score_batch, settler=settle)
    raw = parent.read_bytes()
    receipt = runtime.score(include_per_sample=True)

    assert [job.job_id for job in seen] == ["hard", "joint"]
    assert [ref.cell_id for ref in settlements[0][1]["score_receipts"]] == ["hard", "joint"]
    assert receipt["delivery_settlement"]["attempt_state"] == "FINALIZED"
    assert receipt["include_per_sample"] is True
    assert parent.read_bytes() == raw



def test_runtime_requires_complete_receipts_before_build_or_score(tmp_path):
    scored = []
    runtime, _ = _runtime_for_score(
        tmp_path,
        score_batch=lambda *args, **kwargs: scored.append((args, kwargs)),
        settler=lambda *args, **kwargs: None,
    )
    with pytest.raises(FlightRuntimeError, match="include_per_sample"):
        runtime.score(include_per_sample=False)
    assert scored == []
    assert not (tmp_path / "run/declared-deliveries").exists()
def test_runtime_scorer_failure_does_not_settle_or_score_raw_parent(tmp_path):
    settled = []

    def score_batch(jobs, **kwargs):
        assert all(job.manifest.resolve() != parent.resolve() for job in jobs)
        return {"job_count": len(jobs), "failed": 1, "succeeded": len(jobs) - 1,
                "jobs": []}

    runtime, parent = _runtime_for_score(
        tmp_path, score_batch=score_batch,
        settler=lambda *args, **kwargs: settled.append((args, kwargs)),
    )
    raw = parent.read_bytes()
    receipt = runtime.score(include_per_sample=True)
    assert receipt["result"]["failed"] == 1
    assert settled == []
    assert parent.read_bytes() == raw

