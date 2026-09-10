"""Outer-process parallelism for complete official-scorer jobs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.scoring_batch import (
    ScoreBatchError,
    ScoreJob,
    ScoreProcessOutcome,
    load_score_jobs,
    run_official_finalize_job,
    run_official_score_job,
    run_score_batch,
)


def _manifest(path: Path) -> Path:
    path.write_text("{}", encoding="utf-8")
    return path


def _ledger_cells(path: Path) -> Path:
    path.write_text("{}", encoding="utf-8")
    return path


def _verified(job: ScoreJob) -> ScoreProcessOutcome:
    return ScoreProcessOutcome(
        returncode=0,
        stdout=json.dumps(
            {
                "manifest": str(job.manifest),
                "verified": True,
                "scores": {"official": {"samples": 10}},
            }
        ),
        stderr="",
    )


def _finalized(job: ScoreJob) -> ScoreProcessOutcome:
    return ScoreProcessOutcome(
        returncode=0,
        stdout=json.dumps(
            {
                "manifest": str(job.manifest),
                "verified": True,
                "scores": str(job.manifest.with_suffix(".scores.json")),
                "attempt_state": "FINALIZED",
            }
        ),
        stderr="",
    )


def test_load_score_jobs_resolves_paths_relative_to_the_job_file(tmp_path):
    first = _manifest(tmp_path / "first.run-manifest.json")
    second = _manifest(tmp_path / "second.run-manifest.json")
    jobs_path = tmp_path / "jobs.jsonl"
    jobs_path.write_text(
        "\n".join(
            (
                json.dumps({"job_id": "m0", "manifest": first.name}),
                json.dumps({"job_id": "blend", "manifest": second.name}),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    assert load_score_jobs(jobs_path) == (
        ScoreJob(job_id="m0", manifest=first.resolve()),
        ScoreJob(job_id="blend", manifest=second.resolve()),
    )


def test_load_score_jobs_accepts_explicit_per_job_operations(tmp_path):
    first = _manifest(tmp_path / "first.run-manifest.json")
    second = _manifest(tmp_path / "second.run-manifest.json")
    ledger_cells = _ledger_cells(tmp_path / "second.ledger-cells.json")
    jobs_path = tmp_path / "jobs.jsonl"
    jobs_path.write_text(
        "\n".join(
            (
                json.dumps(
                    {"job_id": "observation", "manifest": first.name, "operation": "score"}
                ),
                json.dumps(
                    {
                        "job_id": "supply",
                        "manifest": second.name,
                        "operation": "finalize",
                        "ledger_cells": ledger_cells.name,
                    }
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    assert load_score_jobs(jobs_path, require_operation=True) == (
        ScoreJob(job_id="observation", manifest=first.resolve(), operation="score"),
        ScoreJob(
            job_id="supply",
            manifest=second.resolve(),
            operation="finalize",
            ledger_cells=ledger_cells.resolve(),
        ),
    )


@pytest.mark.parametrize(
    "rows,match",
    [
        (
            [
                {"job_id": "same", "manifest": "first.run-manifest.json"},
                {"job_id": "same", "manifest": "second.run-manifest.json"},
            ],
            "duplicate job_id",
        ),
        (
            [
                {"job_id": "first", "manifest": "first.run-manifest.json"},
                {"job_id": "second", "manifest": "first.run-manifest.json"},
            ],
            "duplicate manifest",
        ),
        (
            [
                {"job_id": "Arm", "manifest": "first.run-manifest.json"},
                {"job_id": "arm", "manifest": "second.run-manifest.json"},
            ],
            "duplicate job_id",
        ),
    ],
)
def test_load_score_jobs_rejects_duplicate_work(tmp_path, rows, match):
    _manifest(tmp_path / "first.run-manifest.json")
    _manifest(tmp_path / "second.run-manifest.json")
    jobs_path = tmp_path / "jobs.jsonl"
    jobs_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8"
    )

    with pytest.raises(ScoreBatchError, match=match):
        load_score_jobs(jobs_path)


def test_run_score_batch_parallelizes_whole_manifests_and_bounds_workers(tmp_path):
    jobs = tuple(
        ScoreJob(
            job_id=f"job-{index}",
            manifest=_manifest(tmp_path / f"job-{index}.run-manifest.json").resolve(),
        )
        for index in range(6)
    )
    lock = threading.Lock()
    active = 0
    peak = 0
    seen: list[Path] = []

    def runner(job: ScoreJob) -> ScoreProcessOutcome:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            seen.append(job.manifest)
        time.sleep(0.04)
        with lock:
            active -= 1
        return _verified(job)

    summary = run_score_batch(
        jobs, output_dir=tmp_path / "scores", max_workers=2, runner=runner
    )

    assert peak == 2
    assert seen.count(jobs[0].manifest) == 1
    assert sorted(seen) == sorted(job.manifest for job in jobs)
    assert summary["job_count"] == 6
    assert summary["succeeded"] == 6
    assert summary["failed"] == 0
    assert [row["job_id"] for row in summary["jobs"]] == [
        job.job_id for job in jobs
    ]
    for job in jobs:
        result = json.loads(
            (tmp_path / "scores" / f"{job.job_id}.score.json").read_text(
                encoding="utf-8"
            )
        )
        assert result["manifest"] == str(job.manifest)
        assert result["verified"] is True


def test_official_job_runner_uses_an_argument_vector_and_the_existing_manifest_cli(
    tmp_path, monkeypatch
):
    manifest = _manifest(tmp_path / "one.run-manifest.json").resolve()
    captured = {}

    def fake_run(arguments, **kwargs):
        captured["arguments"] = arguments
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="verified", stderr="diagnostic")

    monkeypatch.setattr(subprocess, "run", fake_run)
    outcome = run_official_score_job(ScoreJob(job_id="one", manifest=manifest))

    assert captured["arguments"][-3:] == ["score", "--manifest", str(manifest)]
    assert captured["kwargs"]["check"] is False
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True
    assert "shell" not in captured["kwargs"]
    assert captured["kwargs"]["env"]["PYTHONDONTWRITEBYTECODE"] == "1"
    assert outcome == ScoreProcessOutcome(0, "verified", "diagnostic")


def test_official_finalize_runner_uses_the_existing_finalize_cli(tmp_path, monkeypatch):
    manifest = _manifest(tmp_path / "one.run-manifest.json").resolve()
    ledger_cells = _ledger_cells(tmp_path / "one.ledger-cells.json").resolve()
    captured = {}

    def fake_run(arguments, **kwargs):
        captured["arguments"] = arguments
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="finalized", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    outcome = run_official_finalize_job(
        ScoreJob(job_id="one", manifest=manifest, ledger_cells=ledger_cells)
    )

    assert captured["arguments"][-5:] == [
        "finalize",
        "--manifest",
        str(manifest),
        "--ledger-cells",
        str(ledger_cells),
    ]
    assert captured["kwargs"]["check"] is False
    assert "shell" not in captured["kwargs"]
    assert outcome == ScoreProcessOutcome(0, "finalized", "")


def test_run_score_batch_can_finalize_complete_manifests_concurrently(tmp_path):
    jobs = tuple(
        ScoreJob(
            job_id=name,
            manifest=_manifest(tmp_path / f"{name}.run-manifest.json").resolve(),
            ledger_cells=_ledger_cells(
                tmp_path / f"{name}.ledger-cells.json"
            ).resolve(),
        )
        for name in ("observation", "supply")
    )

    summary = run_score_batch(
        jobs,
        output_dir=tmp_path / "scores",
        max_workers=2,
        runner=_finalized,
        operation="finalize",
    )

    assert summary["operation"] == "finalize"
    assert summary["succeeded"] == 2
    assert all(row["status"] == "succeeded" for row in summary["jobs"])


def test_run_score_batch_can_mix_score_and_finalize_jobs(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import scoring_batch

    observation = ScoreJob(
        job_id="observation",
        manifest=_manifest(tmp_path / "observation.run-manifest.json").resolve(),
        operation="score",
    )
    supply = ScoreJob(
        job_id="supply",
        manifest=_manifest(tmp_path / "supply.run-manifest.json").resolve(),
        operation="finalize",
        ledger_cells=_ledger_cells(tmp_path / "supply.ledger-cells.json").resolve(),
    )
    monkeypatch.setattr(scoring_batch, "run_official_score_job", _verified)
    monkeypatch.setattr(scoring_batch, "run_official_finalize_job", _finalized)

    summary = run_score_batch(
        (observation, supply),
        output_dir=tmp_path / "scores",
        max_workers=2,
        operation="per-job",
    )

    assert summary["operation"] == "per-job"
    assert summary["succeeded"] == 2
    assert [row["operation"] for row in summary["jobs"]] == ["score", "finalize"]


def test_run_score_batch_refuses_finalize_without_ledger_cells(tmp_path):
    job = ScoreJob(
        job_id="supply",
        manifest=_manifest(tmp_path / "supply.run-manifest.json").resolve(),
        operation="finalize",
    )

    with pytest.raises(ScoreBatchError, match="ledger_cells"):
        run_score_batch(
            (job,),
            output_dir=tmp_path / "scores",
            max_workers=1,
            operation="per-job",
        )


def test_run_score_batch_finishes_other_jobs_and_fails_overall(tmp_path):
    jobs = tuple(
        ScoreJob(
            job_id=name,
            manifest=_manifest(tmp_path / f"{name}.run-manifest.json").resolve(),
        )
        for name in ("good-a", "bad", "good-b")
    )
    seen: list[str] = []

    def runner(job: ScoreJob) -> ScoreProcessOutcome:
        seen.append(job.job_id)
        if job.job_id == "bad":
            return ScoreProcessOutcome(returncode=7, stdout="partial", stderr="boom")
        return _verified(job)

    summary = run_score_batch(
        jobs, output_dir=tmp_path / "scores", max_workers=3, runner=runner
    )

    assert sorted(seen) == ["bad", "good-a", "good-b"]
    assert summary["succeeded"] == 2
    assert summary["failed"] == 1
    bad = next(row for row in summary["jobs"] if row["job_id"] == "bad")
    assert bad["status"] == "failed"
    assert bad["returncode"] == 7
    assert bad["complete_receipt_file"] is None
    assert bad["complete_receipt_sha256"] is None
    assert (tmp_path / "scores" / "bad.stdout.log").read_text(
        encoding="utf-8"
    ) == "partial"
    assert (tmp_path / "scores" / "bad.stderr.log").read_text(
        encoding="utf-8"
    ) == "boom"
    assert not (tmp_path / "scores" / "bad.score.json").exists()


@pytest.mark.parametrize(
    "payload,match",
    [
        ("not-json", "valid JSON"),
        (json.dumps({"verified": False}), "verified result"),
        (
            json.dumps(
                {
                    "verified": True,
                    "manifest": "/a/different/run-manifest.json",
                }
            ),
            "manifest identity",
        ),
    ],
)
def test_run_score_batch_rejects_a_false_success_payload(tmp_path, payload, match):
    manifest = _manifest(tmp_path / "one.run-manifest.json").resolve()
    job = ScoreJob(job_id="one", manifest=manifest)

    summary = run_score_batch(
        (job,),
        output_dir=tmp_path / "scores",
        max_workers=1,
        runner=lambda _: ScoreProcessOutcome(0, payload, ""),
    )

    assert summary["failed"] == 1
    assert match in summary["jobs"][0]["error"]


def test_run_score_batch_refuses_to_overwrite_a_nonempty_output_directory(tmp_path):
    output_dir = tmp_path / "scores"
    output_dir.mkdir()
    (output_dir / "existing.score.json").write_text("keep", encoding="utf-8")
    job = ScoreJob(
        job_id="one",
        manifest=_manifest(tmp_path / "one.run-manifest.json").resolve(),
    )

    with pytest.raises(ScoreBatchError, match="not empty"):
        run_score_batch((job,), output_dir=output_dir, max_workers=1, runner=_verified)

    assert (output_dir / "existing.score.json").read_text(encoding="utf-8") == "keep"


def test_driver_score_batch_command_runs_the_outer_scheduler(
    tmp_path, monkeypatch, capsys
):
    from speech_aware_evidence_acquisition.core import scoring_batch
    from speech_aware_evidence_acquisition.core.driver.cli import main

    manifest = _manifest(tmp_path / "one.run-manifest.json")
    jobs_path = tmp_path / "jobs.jsonl"
    jobs_path.write_text(
        json.dumps({"job_id": "one", "manifest": manifest.name}) + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scoring_batch, "run_official_score_job", _verified)

    returncode = main(
        [
            "score-batch",
            "--jobs",
            str(jobs_path),
            "--output-dir",
            str(tmp_path / "scores"),
            "--workers",
            "3",
        ]
    )

    assert returncode == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["effective_max_workers"] == 1
    assert summary["failed"] == 0


def test_driver_score_batch_finalize_mode_runs_the_outer_scheduler(
    tmp_path, monkeypatch, capsys
):
    from speech_aware_evidence_acquisition.core import scoring_batch
    from speech_aware_evidence_acquisition.core.driver.cli import main

    manifest = _manifest(tmp_path / "one.run-manifest.json")
    ledger_cells = _ledger_cells(tmp_path / "one.ledger-cells.json")
    jobs_path = tmp_path / "jobs.jsonl"
    jobs_path.write_text(
        json.dumps(
            {
                "job_id": "one",
                "manifest": manifest.name,
                "ledger_cells": ledger_cells.name,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scoring_batch, "run_official_finalize_job", _finalized)

    returncode = main(
        [
            "score-batch",
            "--jobs",
            str(jobs_path),
            "--output-dir",
            str(tmp_path / "scores"),
            "--workers",
            "2",
            "--finalize",
        ]
    )

    assert returncode == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["operation"] == "finalize"
    assert summary["failed"] == 0


def test_driver_score_batch_per_job_mode_runs_the_outer_scheduler(
    tmp_path, monkeypatch, capsys
):
    from speech_aware_evidence_acquisition.core import scoring_batch
    from speech_aware_evidence_acquisition.core.driver.cli import main

    observation = _manifest(tmp_path / "observation.run-manifest.json")
    supply = _manifest(tmp_path / "supply.run-manifest.json")
    supply_ledger = _ledger_cells(tmp_path / "supply.ledger-cells.json")
    jobs_path = tmp_path / "jobs.jsonl"
    jobs_path.write_text(
        "\n".join(
            (
                json.dumps(
                    {
                        "job_id": "observation",
                        "manifest": observation.name,
                        "operation": "score",
                    }
                ),
                json.dumps(
                    {
                        "job_id": "supply",
                        "manifest": supply.name,
                        "operation": "finalize",
                        "ledger_cells": supply_ledger.name,
                    }
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(scoring_batch, "run_official_score_job", _verified)
    monkeypatch.setattr(scoring_batch, "run_official_finalize_job", _finalized)

    returncode = main(
        [
            "score-batch",
            "--jobs",
            str(jobs_path),
            "--output-dir",
            str(tmp_path / "scores"),
            "--workers",
            "2",
            "--per-job-operation",
        ]
    )

    assert returncode == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["operation"] == "per-job"
    assert summary["failed"] == 0


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="the committed wrapper is a POSIX runtime entry point",
)
def test_parallel_evaluate_script_exposes_the_batch_command_help():
    repo_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        ["bash", str(repo_root / "scripts" / "evaluate_parallel.sh"), "--help"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "score-batch" in completed.stdout
    assert "--workers" in completed.stdout


# Complete score receipts are emitted only for full per-sample score jobs.

def _complete_bundle(tmp_path, job_id="complete"):
    import hashlib
    from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle

    outputs = tmp_path / f"{job_id}.outputs.jsonl"
    outputs.write_text('{"sample_id":"s1"}\n{"sample_id":"s2"}\n')
    manifest = tmp_path / f"{job_id}.run-manifest.json"
    document = {
        "schema": "saea-derived-delivery-v1",
        "run_id": f"parent--delivery-{job_id}",
        "declaration": {"cell_id": job_id},
        "parent": {"path": str(tmp_path / "parent"), "sha256": "c" * 64},
        "config": {"config_hash": "a" * 64},
        "split": {"identity_hash": "b" * 64, "count": 2, "ids": ["s1", "s2"]},
        "scorers": ["official", "cost"],
        "outputs": {
            "path": str(outputs),
            "sha256": hashlib.sha256(outputs.read_bytes()).hexdigest(),
        },
    }
    manifest.write_text(json.dumps(document, sort_keys=True))
    return VerifiedBundle(
        manifest.resolve(), document, outputs.resolve(),
        ({"sample_id": "s1"}, {"sample_id": "s2"}), {},
        frozenset({"s1", "s2"}), "DERIVED",
    )


def _complete_outcome(job, ids=("s1", "s2")):
    return ScoreProcessOutcome(0, json.dumps({
        "manifest": str(job.manifest),
        "verified": True,
        "scores": {
            "official": {
                "aggregate": {"score": 1},
                "per_sample": [{"sample_id": sample_id} for sample_id in ids],
            },
            "cost": {"aggregate": {"calls": 0}, "per_sample": []},
        },
    }), "")


def test_complete_per_sample_score_emits_independently_verifiable_receipt(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import scoring_batch
    from speech_aware_evidence_acquisition.core.scoring_receipt import (
        SavedScoreReceiptRef, verify_complete_score_receipt,
    )

    bundle = _complete_bundle(tmp_path, "paired")
    monkeypatch.setattr(scoring_batch, "verify_bundle", lambda path: bundle)
    output = tmp_path / "score-output"
    summary = run_score_batch(
        (ScoreJob("paired", bundle.manifest_path),),
        output_dir=output, max_workers=1, runner=_complete_outcome,
        include_per_sample=True,
    )

    row = summary["jobs"][0]
    assert row["status"] == "succeeded"
    assert row["complete_receipt_file"] == "paired.complete-score-receipt.json"
    receipt = output / row["complete_receipt_file"]
    verified = verify_complete_score_receipt(
        SavedScoreReceiptRef("paired", receipt, row["complete_receipt_sha256"]),
        bundle,
    )
    assert verified["manifest"]["sha256"] == hashlib.sha256(
        bundle.manifest_path.read_bytes()
    ).hexdigest()


def test_aggregate_only_success_remains_allowed_without_complete_receipt(tmp_path):
    manifest = _manifest(tmp_path / "one.run-manifest.json").resolve()
    summary = run_score_batch(
        (ScoreJob("one", manifest),), output_dir=tmp_path / "scores",
        max_workers=1, runner=_verified, include_per_sample=False,
    )
    row = summary["jobs"][0]
    assert row["status"] == "succeeded"
    assert row["complete_receipt_file"] is None
    assert row["complete_receipt_sha256"] is None


def test_incomplete_per_sample_success_is_failed_without_receipt(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import scoring_batch

    bundle = _complete_bundle(tmp_path, "paired")
    monkeypatch.setattr(scoring_batch, "verify_bundle", lambda path: bundle)
    summary = run_score_batch(
        (ScoreJob("paired", bundle.manifest_path),),
        output_dir=tmp_path / "scores", max_workers=1,
        runner=lambda job: _complete_outcome(job, ids=("s1",)),
        include_per_sample=True,
    )
    row = summary["jobs"][0]
    assert row["status"] == "failed"
    assert "complete roster" in row["error"]
    assert row["complete_receipt_file"] is None


def test_changed_manifest_during_score_refuses_complete_receipt(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import scoring_batch

    bundle = _complete_bundle(tmp_path, "paired")
    monkeypatch.setattr(scoring_batch, "verify_bundle", lambda path: bundle)

    def changed(job):
        job.manifest.write_text(job.manifest.read_text() + " ")
        return _complete_outcome(job)

    summary = run_score_batch(
        (ScoreJob("paired", bundle.manifest_path),),
        output_dir=tmp_path / "scores", max_workers=1, runner=changed,
        include_per_sample=True,
    )
    row = summary["jobs"][0]
    assert row["status"] == "failed"
    assert "manifest hash mismatch" in row["error"]
    assert row["complete_receipt_file"] is None


def test_concurrent_batches_cannot_share_an_output_directory(tmp_path):
    entered = threading.Event()
    release = threading.Event()
    output = tmp_path / "scores"
    manifest = _manifest(tmp_path / "one.run-manifest.json").resolve()
    outcomes = []

    def slow(job):
        entered.set()
        release.wait(timeout=2)
        return _verified(job)

    def first():
        try:
            outcomes.append(run_score_batch(
                (ScoreJob("one", manifest),), output_dir=output,
                max_workers=1, runner=slow,
            ))
        except Exception as error:
            outcomes.append(error)

    thread = threading.Thread(target=first)
    thread.start()
    assert entered.wait(timeout=2)
    with pytest.raises(ScoreBatchError, match="busy"):
        run_score_batch(
            (ScoreJob("one", manifest),), output_dir=output,
            max_workers=1, runner=_verified,
        )
    release.set()
    thread.join(timeout=2)
    assert outcomes[0]["succeeded"] == 1
