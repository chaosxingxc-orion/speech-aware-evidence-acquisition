"""Bounded outer parallelism for complete authoritative scoring jobs.

Each worker launches the existing ``core.driver score --manifest`` command in
its own process.  A job therefore verifies and scores one complete run bundle;
this module never shards a corpus, reimplements a scorer, or averages
per-shard aggregates.  Corpus-level official metrics remain owned by the
registered scorer inside that single job process.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence


class ScoreBatchError(RuntimeError):
    """The batch description or its output boundary is unsafe."""


@dataclass(frozen=True)
class ScoreJob:
    """One complete, independently verifiable official-scorer invocation."""

    job_id: str
    manifest: Path


@dataclass(frozen=True)
class ScoreProcessOutcome:
    """Captured result of one isolated scorer process."""

    returncode: int
    stdout: str
    stderr: str


ScoreRunner = Callable[[ScoreJob], ScoreProcessOutcome]

_SCHEMA = "saea-parallel-score-batch-v1"
_JOB_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_DRIVER_MODULE = "speech_aware_evidence_acquisition.core.driver"
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _write_text(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    _write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_score_jobs(path: Path) -> tuple[ScoreJob, ...]:
    """Load an exact-field JSONL job table and resolve manifests beside it."""

    path = Path(path)
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ScoreBatchError(f"cannot read score job file {path}: {error}") from error
    lines = raw.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    if not lines:
        raise ScoreBatchError(f"score job file {path} is empty")

    jobs: list[ScoreJob] = []
    seen_ids: set[str] = set()
    seen_manifests: set[Path] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line:
            raise ScoreBatchError(
                f"score job file {path} line {line_number} is blank; remove it"
            )
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ScoreBatchError(
                f"score job file {path} line {line_number} is malformed JSON: {error}"
            ) from error
        if not isinstance(row, Mapping) or set(row) != {"job_id", "manifest"}:
            raise ScoreBatchError(
                f"score job file {path} line {line_number} must contain exactly "
                "job_id and manifest"
            )
        job_id = row.get("job_id")
        manifest_value = row.get("manifest")
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
            raise ScoreBatchError(
                f"score job file {path} line {line_number} has an unsafe job_id"
            )
        if not isinstance(manifest_value, str) or not manifest_value:
            raise ScoreBatchError(
                f"score job file {path} line {line_number} has no manifest path"
            )
        manifest = Path(manifest_value)
        if not manifest.is_absolute():
            manifest = path.parent / manifest
        manifest = manifest.resolve()
        if not manifest.is_file():
            raise ScoreBatchError(
                f"score job {job_id!r} manifest does not exist: {manifest}"
            )
        if not manifest.name.endswith(".run-manifest.json"):
            raise ScoreBatchError(
                f"score job {job_id!r} is not a run-manifest.json artifact: {manifest}"
            )
        job_id_key = job_id.casefold()
        if job_id_key in seen_ids:
            raise ScoreBatchError(f"duplicate job_id {job_id!r} in {path}")
        if manifest in seen_manifests:
            raise ScoreBatchError(f"duplicate manifest {manifest} in {path}")
        seen_ids.add(job_id_key)
        seen_manifests.add(manifest)
        jobs.append(ScoreJob(job_id=job_id, manifest=manifest))
    return tuple(jobs)


def run_official_score_job(job: ScoreJob) -> ScoreProcessOutcome:
    """Launch the existing authoritative scorer once for one whole manifest."""

    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            _DRIVER_MODULE,
            "score",
            "--manifest",
            str(job.manifest),
        ],
        cwd=_REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    return ScoreProcessOutcome(
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _verified_payload(job: ScoreJob, outcome: ScoreProcessOutcome) -> Mapping[str, object]:
    try:
        payload = json.loads(outcome.stdout)
    except json.JSONDecodeError as error:
        raise ScoreBatchError("scorer returned success without valid JSON") from error
    if not isinstance(payload, Mapping) or payload.get("verified") is not True:
        raise ScoreBatchError("scorer returned success without a verified result")
    manifest = payload.get("manifest")
    if not isinstance(manifest, str) or Path(manifest).resolve() != job.manifest:
        raise ScoreBatchError("scorer result manifest identity does not match its job")
    if not isinstance(payload.get("scores"), Mapping):
        raise ScoreBatchError("scorer returned a verified result without scores")
    return payload


def _run_timed(job: ScoreJob, runner: ScoreRunner) -> tuple[ScoreProcessOutcome, float, str | None]:
    started = time.perf_counter()
    try:
        outcome = runner(job)
        if not isinstance(outcome, ScoreProcessOutcome):
            raise ScoreBatchError("score runner returned an invalid outcome")
        return outcome, time.perf_counter() - started, None
    except Exception as error:
        return (
            ScoreProcessOutcome(returncode=1, stdout="", stderr=""),
            time.perf_counter() - started,
            f"score runner raised {type(error).__name__}: {error}",
        )


def run_score_batch(
    jobs: Sequence[ScoreJob],
    *,
    output_dir: Path,
    max_workers: int,
    runner: ScoreRunner | None = None,
) -> dict[str, object]:
    """Run every complete job with bounded outer process concurrency.

    All submitted jobs are allowed to settle.  Results are reported in input
    order, independent of completion order.  A non-empty output directory is
    refused so an earlier score record is never overwritten.
    """

    frozen_jobs = tuple(
        ScoreJob(job_id=job.job_id, manifest=Path(job.manifest).resolve())
        for job in jobs
    )
    if not frozen_jobs:
        raise ScoreBatchError("parallel scoring requires at least one job")
    if (
        not isinstance(max_workers, int)
        or isinstance(max_workers, bool)
        or max_workers <= 0
    ):
        raise ScoreBatchError("max_workers must be a positive integer")
    job_ids = [job.job_id for job in frozen_jobs]
    manifests = [job.manifest.resolve() for job in frozen_jobs]
    if len({job_id.casefold() for job_id in job_ids}) != len(job_ids):
        raise ScoreBatchError("parallel scoring received duplicate job ids")
    if len(set(manifests)) != len(manifests):
        raise ScoreBatchError("parallel scoring received duplicate manifests")
    if any(not _JOB_ID.fullmatch(job_id) for job_id in job_ids):
        raise ScoreBatchError("parallel scoring received an unsafe job id")
    for job in frozen_jobs:
        if not job.manifest.is_file():
            raise ScoreBatchError(
                f"score job {job.job_id!r} manifest does not exist: {job.manifest}"
            )
        if not job.manifest.name.endswith(".run-manifest.json"):
            raise ScoreBatchError(
                f"score job {job.job_id!r} is not a run-manifest.json artifact: "
                f"{job.manifest}"
            )

    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ScoreBatchError(f"score output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    selected_runner = runner if runner is not None else run_official_score_job
    started = time.perf_counter()
    completed_by_index: dict[
        int, tuple[ScoreProcessOutcome, float, str | None]
    ] = {}
    worker_count = min(max_workers, len(frozen_jobs))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {
            executor.submit(_run_timed, job, selected_runner): index
            for index, job in enumerate(frozen_jobs)
        }
        for future in as_completed(futures):
            completed_by_index[futures[future]] = future.result()

    rows: list[dict[str, object]] = []
    succeeded = 0
    for index, job in enumerate(frozen_jobs):
        outcome, elapsed_seconds, runner_error = completed_by_index[index]
        stderr_name = f"{job.job_id}.stderr.log"
        _write_text(output_dir / stderr_name, outcome.stderr)
        error = runner_error
        if error is None and outcome.returncode != 0:
            error = f"official scorer exited with status {outcome.returncode}"
        if error is None:
            try:
                _verified_payload(job, outcome)
            except ScoreBatchError as payload_error:
                error = str(payload_error)

        if error is None:
            result_name = f"{job.job_id}.score.json"
            _write_text(output_dir / result_name, outcome.stdout)
            result_sha256: str | None = _sha256_text(outcome.stdout)
            status = "succeeded"
            stdout_name: str | None = None
            succeeded += 1
        else:
            result_name = None
            result_sha256 = None
            status = "failed"
            stdout_name = f"{job.job_id}.stdout.log"
            _write_text(output_dir / stdout_name, outcome.stdout)

        rows.append(
            {
                "index": index,
                "job_id": job.job_id,
                "manifest": str(job.manifest),
                "status": status,
                "returncode": outcome.returncode,
                "elapsed_seconds": elapsed_seconds,
                "result_file": result_name,
                "result_sha256": result_sha256,
                "stdout_log": stdout_name,
                "stderr_log": stderr_name,
                "stderr_sha256": _sha256_text(outcome.stderr),
                "error": error,
            }
        )

    summary: dict[str, object] = {
        "schema": _SCHEMA,
        "parallelism_boundary": "one-complete-verified-manifest-per-process",
        "aggregation_rule": (
            "no dataset sharding and no averaging of shard-level official metrics"
        ),
        "requested_max_workers": max_workers,
        "effective_max_workers": worker_count,
        "job_count": len(frozen_jobs),
        "succeeded": succeeded,
        "failed": len(frozen_jobs) - succeeded,
        "elapsed_seconds": time.perf_counter() - started,
        "jobs": rows,
    }
    _write_json(output_dir / "batch-summary.json", summary)
    return summary


__all__ = [
    "ScoreBatchError",
    "ScoreJob",
    "ScoreProcessOutcome",
    "load_score_jobs",
    "run_official_score_job",
    "run_score_batch",
]
