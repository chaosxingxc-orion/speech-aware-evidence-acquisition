"""Opt-in preservation of authoritative scorer detail rows."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from speech_aware_evidence_acquisition.core.scoring_batch import (
    ScoreJob,
    ScoreProcessOutcome,
    run_official_score_job,
    run_score_batch,
)


def _manifest(path: Path) -> Path:
    path.write_text("{}", encoding="utf-8")
    return path.resolve()


def _registered_scorer_results() -> dict[str, object]:
    return {
        "asr-wer": {
            "per_sample": [{"sample_id": "sample-1", "wer": 0.25}],
            "aggregate": {"mean_wer": 0.25, "samples": 1},
            "views": {
                "normalized": {
                    "aggregate": {"mean_wer": 0.2, "samples": 1},
                    "per_sample": [{"sample_id": "sample-1", "wer": 0.2}],
                }
            },
        },
        "cost": {
            "per_sample": [],
            "aggregate": {"calls_used": 1},
        },
    }


def _patch_authoritative_score(monkeypatch, manifest: Path):
    from speech_aware_evidence_acquisition.core.driver import cli

    bundle = object()
    score_calls: list[object] = []
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.load_lock",
        lambda _: {"locked": True},
    )
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.data_root", lambda: manifest.parent
    )
    monkeypatch.setattr(cli, "verify_bundle", lambda actual: bundle)

    def score(actual_bundle, actual_lock, actual_root):
        assert actual_bundle is bundle
        assert actual_lock == {"locked": True}
        assert actual_root == manifest.parent
        score_calls.append(actual_bundle)
        return _registered_scorer_results()

    monkeypatch.setattr(cli, "score_bundle", score)
    return score_calls


def test_authoritative_score_defaults_to_the_existing_aggregate_only_bytes(
    tmp_path, monkeypatch, capsys
):
    from speech_aware_evidence_acquisition.core.driver.cli import main

    manifest = _manifest(tmp_path / "one.run-manifest.json")
    score_calls = _patch_authoritative_score(monkeypatch, manifest)

    assert main(["score", "--manifest", str(manifest)]) == 0

    assert capsys.readouterr().out == json.dumps(
        {
            "manifest": str(manifest),
            "verified": True,
            "scores": {
                "asr-wer": {"mean_wer": 0.25, "samples": 1},
                "cost": {"calls_used": 1},
            },
        },
        indent=2,
        sort_keys=True,
    ) + "\n"
    assert len(score_calls) == 1


def test_authoritative_score_can_include_registered_per_sample_rows_in_one_pass(
    tmp_path, monkeypatch, capsys
):
    from speech_aware_evidence_acquisition.core.driver.cli import main

    manifest = _manifest(tmp_path / "one.run-manifest.json")
    score_calls = _patch_authoritative_score(monkeypatch, manifest)

    assert (
        main(["score", "--manifest", str(manifest), "--include-per-sample"]) == 0
    )

    assert json.loads(capsys.readouterr().out) == {
        "manifest": str(manifest),
        "verified": True,
        "scores": _registered_scorer_results(),
    }
    assert len(score_calls) == 1


def test_official_score_job_appends_detail_flag_to_one_manifest_cli_invocation(
    tmp_path, monkeypatch
):
    manifest = _manifest(tmp_path / "one.run-manifest.json")
    captured: dict[str, object] = {}

    def fake_run(arguments, **kwargs):
        captured["arguments"] = arguments
        captured["kwargs"] = kwargs
        return SimpleNamespace(returncode=0, stdout="verified", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert run_official_score_job(
        ScoreJob(job_id="one", manifest=manifest), include_per_sample=True
    ) == ScoreProcessOutcome(0, "verified", "")

    assert captured["arguments"][-4:] == [
        "score",
        "--manifest",
        str(manifest),
        "--include-per-sample",
    ]
    assert captured["arguments"].count("score") == 1


def test_score_batch_passes_detail_mode_once_to_each_complete_score_job(
    tmp_path, monkeypatch
):
    from speech_aware_evidence_acquisition.core import scoring_batch

    jobs = tuple(
        ScoreJob(job_id=name, manifest=_manifest(tmp_path / f"{name}.run-manifest.json"))
        for name in ("observation", "supply")
    )
    calls: list[tuple[ScoreJob, bool]] = []

    def official(job: ScoreJob, *, include_per_sample: bool = False):
        calls.append((job, include_per_sample))
        return ScoreProcessOutcome(
            returncode=0,
            stdout=json.dumps(
                {
                    "manifest": str(job.manifest),
                    "verified": True,
                    "scores": {
                        "official": {
                            "aggregate": {"samples": 1},
                            "per_sample": [{"sample_id": "sample-1"}],
                            "views": {
                                "normalized": {
                                    "aggregate": {"samples": 1},
                                    "per_sample": [{"sample_id": "sample-1"}],
                                }
                            },
                        }
                    },
                }
            ),
            stderr="",
        )

    monkeypatch.setattr(scoring_batch, "run_official_score_job", official)
    from speech_aware_evidence_acquisition.core.bundle.artifacts import VerifiedBundle

    bundles = {}
    for job in jobs:
        outputs = tmp_path / f"{job.job_id}.outputs.jsonl"
        outputs.write_text('{"sample_id":"sample-1"}\n')
        document = {
            "run_id": job.job_id,
            "config": {"config_hash": "a" * 64},
            "split": {
                "identity_hash": "b" * 64,
                "count": 1,
                "ids": ["sample-1"],
            },
            "scorers": ["official"],
        }
        bundles[job.manifest] = VerifiedBundle(
            job.manifest, document, outputs,
            ({"sample_id": "sample-1"},), {}, frozenset({"sample-1"}), "DERIVED",
        )
    monkeypatch.setattr(
        scoring_batch, "verify_bundle", lambda path: bundles[Path(path).resolve()]
    )

    summary = run_score_batch(
        jobs,
        output_dir=tmp_path / "scores",
        max_workers=2,
        include_per_sample=True,
    )

    assert summary["succeeded"] == 2
    assert sorted(calls, key=lambda call: call[0].job_id) == [
        (jobs[0], True),
        (jobs[1], True),
    ]
    first = json.loads((tmp_path / "scores" / "observation.score.json").read_text())
    assert first["scores"]["official"]["views"]["normalized"]["per_sample"] == [
        {"sample_id": "sample-1"}
    ]


def test_score_batch_cli_forwards_detail_mode_to_the_outer_scheduler(
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
    captured: dict[str, object] = {}

    def batch(jobs, **kwargs):
        captured["jobs"] = jobs
        captured.update(kwargs)
        return {"failed": 0}

    monkeypatch.setattr(scoring_batch, "run_score_batch", batch)

    assert (
        main(
            [
                "score-batch",
                "--jobs",
                str(jobs_path),
                "--output-dir",
                str(tmp_path / "scores"),
                "--include-per-sample",
            ]
        )
        == 0
    )

    assert captured["include_per_sample"] is True
    assert captured["jobs"] == (ScoreJob(job_id="one", manifest=manifest),)
    assert json.loads(capsys.readouterr().out) == {"failed": 0}
