"""Bounded outer parallelism for complete authoritative scoring jobs.

Each worker launches the existing ``core.driver score --manifest`` command in
its own process. A job verifies and scores one complete run bundle. A narrow
derived-column entry verifies a sealed parent and one whole-roster copy before
calling the same registered scorer, with an exclusive source-bound receipt.
This module never shards a corpus, reimplements a scorer, or averages
per-shard aggregates.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterator, Literal, Mapping, Sequence, cast

from .bundle import BundleError
from .bundle.verify import verify_bundle
from .scoring_receipt import (
    ScoreReceiptError, ScoreSourceSnapshot, capture_score_source,
    write_complete_score_receipt,
)


class ScoreBatchError(RuntimeError):
    """The batch description or its output boundary is unsafe."""


ScoreOperation = Literal["score", "finalize"]
BatchOperation = Literal["score", "finalize", "per-job"]


@dataclass(frozen=True)
class ScoringContext:
    """Explicit source checkout, data root and umbrella lock for isolated workers."""

    repo_root: Path
    data_root: Path
    lock_path: Path


@dataclass(frozen=True)
class ScoreJob:
    """One complete, independently verifiable official-scorer invocation."""

    job_id: str
    manifest: Path
    operation: ScoreOperation | None = None
    ledger_cells: Path | None = None


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
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{time.monotonic_ns()}"
    )
    try:
        temporary.write_text(value, encoding="utf-8", newline="\n")
        temporary.replace(path)
    finally:
        try:
            temporary.unlink()
        except OSError:
            pass


@contextmanager
def _claim_output_directory(path: Path) -> Iterator[None]:
    """Exclude concurrent batches while preserving the legacy directory contents."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.score-batch.lock")
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ScoreBatchError(f"score output directory is busy: {path}") from error
        if path.exists() and any(path.iterdir()):
            raise ScoreBatchError(f"score output directory is not empty: {path}")
        path.mkdir(parents=True, exist_ok=True)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    _write_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def load_score_jobs(
    path: Path,
    *,
    require_operation: bool = False,
    require_ledger_cells: bool = False,
) -> tuple[ScoreJob, ...]:
    """Load an exact-field JSONL job table and resolve manifests beside it."""

    if require_operation and require_ledger_cells:
        raise ScoreBatchError(
            "job loading cannot require both per-job operations and uniform ledger cells"
        )
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
        operation_value = row.get("operation") if isinstance(row, Mapping) else None
        if require_operation and operation_value == "finalize":
            expected_fields = {"job_id", "manifest", "operation", "ledger_cells"}
        elif require_operation:
            expected_fields = {"job_id", "manifest", "operation"}
        elif require_ledger_cells:
            expected_fields = {"job_id", "manifest", "ledger_cells"}
        else:
            expected_fields = {"job_id", "manifest"}
        if not isinstance(row, Mapping) or set(row) != expected_fields:
            raise ScoreBatchError(
                f"score job file {path} line {line_number} must contain exactly "
                f"{sorted(expected_fields)}"
            )
        job_id = row.get("job_id")
        manifest_value = row.get("manifest")
        job_operation = row.get("operation") if require_operation else None
        ledger_cells_value = row.get("ledger_cells") if "ledger_cells" in row else None
        if not isinstance(job_id, str) or not _JOB_ID.fullmatch(job_id):
            raise ScoreBatchError(
                f"score job file {path} line {line_number} has an unsafe job_id"
            )
        if not isinstance(manifest_value, str) or not manifest_value:
            raise ScoreBatchError(
                f"score job file {path} line {line_number} has no manifest path"
            )
        if require_operation and job_operation not in {"score", "finalize"}:
            raise ScoreBatchError(
                f"score job file {path} line {line_number} operation must be "
                "'score' or 'finalize'"
            )
        if ledger_cells_value is not None and (
            not isinstance(ledger_cells_value, str) or not ledger_cells_value
        ):
            raise ScoreBatchError(
                f"score job file {path} line {line_number} has no ledger_cells path"
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
        ledger_cells = None
        if isinstance(ledger_cells_value, str):
            ledger_cells = Path(ledger_cells_value)
            if not ledger_cells.is_absolute():
                ledger_cells = path.parent / ledger_cells
            ledger_cells = ledger_cells.resolve()
            if not ledger_cells.is_file():
                raise ScoreBatchError(
                    f"score job {job_id!r} ledger_cells does not exist: {ledger_cells}"
                )
        job_id_key = job_id.casefold()
        if job_id_key in seen_ids:
            raise ScoreBatchError(f"duplicate job_id {job_id!r} in {path}")
        if manifest in seen_manifests:
            raise ScoreBatchError(f"duplicate manifest {manifest} in {path}")
        seen_ids.add(job_id_key)
        seen_manifests.add(manifest)
        jobs.append(
            ScoreJob(
                job_id=job_id,
                manifest=manifest,
                operation=(
                    cast(ScoreOperation, job_operation)
                    if job_operation is not None
                    else None
                ),
                ledger_cells=ledger_cells,
            )
        )
    return tuple(jobs)


def _official_job_process(
    job: ScoreJob, *, operation: str, include_per_sample: bool,
    context: ScoringContext | None,
) -> ScoreProcessOutcome:
    if operation == "finalize" and job.ledger_cells is None:
        raise ScoreBatchError(f"finalize job {job.job_id!r} requires a ledger_cells file")
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    arguments = [
        sys.executable, "-B", "-m", _DRIVER_MODULE, operation,
        "--manifest", str(job.manifest),
    ]
    if operation == "finalize":
        arguments.extend(("--ledger-cells", str(job.ledger_cells)))
    if include_per_sample:
        arguments.append("--include-per-sample")
    cwd = _REPO_ROOT
    if context is not None:
        cwd = Path(context.repo_root)
        for key in ("repo_root", "data_root", "lock_path"):
            arguments.extend(("--" + key.replace("_", "-"), str(getattr(context, key))))
        environment["PYTHONPATH"] = os.pathsep.join(filter(None, (
            str(cwd / "src"), environment.get("PYTHONPATH", ""),
        )))
        environment["SPEECHRL_DATA_DIR"] = str(context.data_root)
    completed = subprocess.run(
        arguments, cwd=cwd, env=environment, check=False, capture_output=True, text=True,
    )
    return ScoreProcessOutcome(
        returncode=completed.returncode, stdout=completed.stdout, stderr=completed.stderr,
    )


def run_official_score_job(
    job: ScoreJob, *, include_per_sample: bool = False, context: ScoringContext | None = None,
) -> ScoreProcessOutcome:
    """Launch the authoritative scorer once for one complete manifest."""
    return _official_job_process(
        job, operation="score", include_per_sample=include_per_sample, context=context,
    )


def run_official_finalize_job(
    job: ScoreJob, *, include_per_sample: bool = False, context: ScoringContext | None = None,
) -> ScoreProcessOutcome:
    """Score and finalize one complete manifest in one authoritative worker."""
    return _official_job_process(
        job, operation="finalize", include_per_sample=include_per_sample, context=context,
    )


def _verified_payload(
    job: ScoreJob,
    outcome: ScoreProcessOutcome,
    *,
    operation: ScoreOperation,
) -> Mapping[str, object]:
    try:
        payload = json.loads(outcome.stdout)
    except json.JSONDecodeError as error:
        raise ScoreBatchError("scorer returned success without valid JSON") from error
    if not isinstance(payload, Mapping) or payload.get("verified") is not True:
        raise ScoreBatchError("scorer returned success without a verified result")
    manifest = payload.get("manifest")
    if not isinstance(manifest, str) or Path(manifest).resolve() != job.manifest:
        raise ScoreBatchError("scorer result manifest identity does not match its job")
    scores = payload.get("scores")
    if operation == "score" and not isinstance(scores, Mapping):
        raise ScoreBatchError("scorer returned a verified result without scores")
    if operation == "finalize" and (
        not isinstance(scores, str)
        or not scores
        or payload.get("attempt_state") != "FINALIZED"
    ):
        raise ScoreBatchError(
            "finalizer returned success without scores or FINALIZED attempt state"
        )
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
    operation: BatchOperation = "score",
    include_per_sample: bool = False,
    context: ScoringContext | None = None,
) -> dict[str, object]:
    """Run every complete job with bounded outer process concurrency.

    All submitted jobs are allowed to settle.  Results are reported in input
    order, independent of completion order.  A non-empty output directory is
    refused so an earlier score record is never overwritten.
    """

    frozen_jobs = tuple(
        ScoreJob(
            job_id=job.job_id,
            manifest=Path(job.manifest).resolve(),
            operation=job.operation,
            ledger_cells=(
                Path(job.ledger_cells).resolve()
                if job.ledger_cells is not None
                else None
            ),
        )
        for job in jobs
    )
    if not frozen_jobs:
        raise ScoreBatchError("parallel scoring requires at least one job")
    if operation not in {"score", "finalize", "per-job"}:
        raise ScoreBatchError("operation must be 'score', 'finalize', or 'per-job'")
    if operation == "per-job":
        if any(job.operation not in {"score", "finalize"} for job in frozen_jobs):
            raise ScoreBatchError(
                "per-job scoring requires every job to declare score or finalize"
            )
    elif any(job.operation is not None for job in frozen_jobs):
        raise ScoreBatchError(
            "uniform score/finalize mode refuses per-job operation fields"
        )
    for job in frozen_jobs:
        job_operation = job.operation if operation == "per-job" else operation
        if job_operation == "finalize" and job.ledger_cells is None:
            raise ScoreBatchError(
                f"finalize job {job.job_id!r} requires ledger_cells"
            )
        if job_operation == "score" and job.ledger_cells is not None:
            raise ScoreBatchError(
                f"score job {job.job_id!r} must not declare ledger_cells"
            )
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
        if job.ledger_cells is not None and not job.ledger_cells.is_file():
            raise ScoreBatchError(
                f"score job {job.job_id!r} ledger_cells does not exist: "
                f"{job.ledger_cells}"
            )

    output_dir = Path(output_dir)
    with _claim_output_directory(output_dir):
        def selected_runner(job: ScoreJob) -> ScoreProcessOutcome:
            if runner is not None:
                return runner(job)
            job_operation = job.operation if operation == "per-job" else operation
            selected = (
                run_official_finalize_job
                if job_operation == "finalize"
                else run_official_score_job
            )
            kwargs = {}
            if include_per_sample:
                kwargs["include_per_sample"] = True
            if context is not None:
                kwargs["context"] = context
            return selected(job, **kwargs)

        started = time.perf_counter()
        completed_by_index: dict[
            int, tuple[ScoreProcessOutcome, float, str | None]
        ] = {}
        score_sources: dict[int, ScoreSourceSnapshot] = {}
        runnable: list[tuple[int, ScoreJob]] = []
        for index, job in enumerate(frozen_jobs):
            job_operation = job.operation if operation == "per-job" else operation
            if include_per_sample and job_operation == "score":
                try:
                    score_sources[index] = capture_score_source(
                        verify_bundle(job.manifest)
                    )
                except (BundleError, ScoreReceiptError) as error:
                    completed_by_index[index] = (
                        ScoreProcessOutcome(returncode=1, stdout="", stderr=""),
                        0.0,
                        f"complete score source verification failed: "
                        f"{type(error).__name__}: {error}",
                    )
                    continue
            runnable.append((index, job))

        worker_count = min(max_workers, len(frozen_jobs))
        if runnable:
            with ThreadPoolExecutor(
                max_workers=min(worker_count, len(runnable))
            ) as executor:
                futures = {
                    executor.submit(_run_timed, job, selected_runner): index
                    for index, job in runnable
                }
                for future in as_completed(futures):
                    completed_by_index[futures[future]] = future.result()

        rows: list[dict[str, object]] = []
        succeeded = 0
        for index, job in enumerate(frozen_jobs):
            outcome, elapsed_seconds, runner_error = completed_by_index[index]
            job_operation = job.operation if operation == "per-job" else operation
            stderr_name = f"{job.job_id}.stderr.log"
            _write_text(output_dir / stderr_name, outcome.stderr)
            error = runner_error
            if error is None and outcome.returncode != 0:
                error = f"official scorer exited with status {outcome.returncode}"
            if error is None:
                try:
                    _verified_payload(job, outcome, operation=job_operation)
                except ScoreBatchError as payload_error:
                    error = str(payload_error)

            result_name: str | None = None
            result_sha256: str | None = None
            complete_receipt_file: str | None = None
            complete_receipt_sha256: str | None = None
            if error is None:
                candidate_result = f"{job.job_id}.score.json"
                _write_text(output_dir / candidate_result, outcome.stdout)
                if include_per_sample and job_operation == "score":
                    try:
                        receipt_name = f"{job.job_id}.complete-score-receipt.json"
                        receipt = write_complete_score_receipt(
                            output_dir / receipt_name,
                            job_id=job.job_id,
                            result_path=output_dir / candidate_result,
                            source=score_sources[index],
                            verified_bundle=verify_bundle(job.manifest),
                        )
                        complete_receipt_file = receipt_name
                        complete_receipt_sha256 = receipt.sha256
                    except (BundleError, ScoreReceiptError) as receipt_error:
                        error = (
                            "complete score receipt refused: "
                            f"{type(receipt_error).__name__}: {receipt_error}"
                        )
                        try:
                            (output_dir / candidate_result).unlink()
                        except OSError:
                            pass
                if error is None:
                    result_name = candidate_result
                    result_sha256 = _sha256_text(outcome.stdout)

            if error is None:
                status = "succeeded"
                stdout_name: str | None = None
                succeeded += 1
            else:
                status = "failed"
                stdout_name = f"{job.job_id}.stdout.log"
                _write_text(output_dir / stdout_name, outcome.stdout)

            rows.append(
                {
                    "index": index,
                    "job_id": job.job_id,
                    "operation": job_operation,
                    "manifest": str(job.manifest),
                    "ledger_cells": (
                        str(job.ledger_cells)
                        if job.ledger_cells is not None
                        else None
                    ),
                    "status": status,
                    "returncode": outcome.returncode,
                    "elapsed_seconds": elapsed_seconds,
                    "result_file": result_name,
                    "result_sha256": result_sha256,
                    "complete_receipt_file": complete_receipt_file,
                    "complete_receipt_sha256": complete_receipt_sha256,
                    "stdout_log": stdout_name,
                    "stderr_log": stderr_name,
                    "stderr_sha256": _sha256_text(outcome.stderr),
                    "error": error,
                }
            )

        summary: dict[str, object] = {
            "schema": _SCHEMA,
            "operation": operation,
            "include_per_sample": bool(include_per_sample),
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
    "run_official_finalize_job",
    "run_official_score_job",
    "run_score_batch",
    "score_complete_derived_copy",
    "score_paired_strata",
]

# The official-scoring path's optional ``--strata-inside-scorer`` mode (coordinator ruling
# 2026-09-30): post-stratification by gold intent INSIDE the scoring step, aggregates only. It
# consumes the complete, single-process official score results this module produces (a sealed
# ``<run>.scores.json`` or a ``score_complete_derived_copy`` result) and never shards or re-scores.
from .scoring_strata import score_paired_strata  # noqa: E402


def score_complete_derived_copy(
    *, parent_manifest: Path, outputs_copy: Path, expected_copy_sha256: str,
    scorer_id: str, result_path: Path, lock: Mapping[str, object], data_root: Path,
    column_binding: Mapping[str, object],
) -> Mapping[str, object]:
    """Score one full-roster derived column, bound to a verified parent bundle.

    The derived copy is not a new run. Its own exclusive receipt binds the
    parent, roster, scorer, input bytes and result bytes. A durable start marker
    precedes the official scorer invocation. A successful retry reads the
    complete receipt; an incomplete prior invocation refuses automatic replay.
    """
    from .base import SCORERS
    from . import scorers as _scorers  # noqa: F401

    if not isinstance(column_binding, Mapping) or not column_binding:
        raise ScoreBatchError("derived scorer requires a nonempty column binding")
    parent_manifest = Path(parent_manifest)
    outputs_copy = Path(outputs_copy)
    result_path = Path(result_path)
    receipt_path = result_path.with_name(result_path.name + ".receipt.json")
    started_path = result_path.with_name(result_path.name + ".started.json")
    lock_path = result_path.with_name(result_path.name + ".lock")
    bundle = verify_bundle(parent_manifest)
    if bundle.manifest.get("status") != "COMPLETED" or bundle.attempt_state != "FINALIZED":
        raise ScoreBatchError("derived scorer parent is not a finalized complete bundle")
    raw = outputs_copy.read_bytes()
    copy_hash = hashlib.sha256(raw).hexdigest()
    if copy_hash != expected_copy_sha256:
        raise ScoreBatchError("derived copy hash differs from registered render")
    try:
        lines = raw.decode("utf-8").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        rows = [json.loads(line) for line in lines]
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ScoreBatchError(f"derived copy is not valid JSONL: {error}") from error
    ids = [row.get("sample_id") for row in rows if isinstance(row, Mapping)]
    if (len(ids) != len(rows) or len(ids) != len(bundle.split_ids)
            or len(set(ids)) != len(ids) or set(ids) != set(bundle.split_ids)
            or any(set(row) != {"sample_id", "text"}
                   or not isinstance(row["text"], str) for row in rows)):
        raise ScoreBatchError("derived copy is not one complete parent roster column")
    binding = {
        "schema": "saea-derived-complete-score-receipt-v1",
        "parent_manifest": str(parent_manifest.resolve()),
        "parent_manifest_sha256": hashlib.sha256(parent_manifest.read_bytes()).hexdigest(),
        "parent_run_id": bundle.manifest.get("run_id"),
        "parent_attempt_id": parent_manifest.parent.name,
        "parent_outputs_sha256": bundle.manifest["outputs"]["sha256"],
        "roster_count": len(ids),
        "roster_ids_sha256": hashlib.sha256(
            json.dumps(sorted(ids), separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "outputs_copy": str(outputs_copy.resolve()),
        "outputs_copy_sha256": copy_hash,
        "scorer_id": scorer_id,
        "column_binding": dict(column_binding),
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        if result_path.exists() or receipt_path.exists():
            if not result_path.is_file() or not receipt_path.is_file():
                raise ScoreBatchError("partial derived score or receipt; scorer will not rerun")
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if any(receipt.get(key) != value for key, value in binding.items()):
                raise ScoreBatchError("derived score receipt differs from source binding")
            result_bytes = result_path.read_bytes()
            if hashlib.sha256(result_bytes).hexdigest() != receipt.get("result_sha256"):
                raise ScoreBatchError("derived score result hash differs from receipt")
            result = json.loads(result_bytes)
            if set(result) != {scorer_id}:
                raise ScoreBatchError("derived score result names another scorer")
            return result[scorer_id]
        if started_path.exists():
            try:
                started = json.loads(started_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as error:
                raise ScoreBatchError("prior derived score invocation marker is unreadable") from error
            if (not isinstance(started, Mapping)
                    or started.get("attempt_state") != "STARTED"
                    or any(started.get(key) != value for key, value in binding.items())):
                raise ScoreBatchError("prior derived score invocation marker differs from source")
            raise ScoreBatchError(
                "prior derived score invocation is incomplete; scorer will not rerun"
            )
        scorer = SCORERS.resolve(scorer_id)
        # The exclusive, source-bound marker is durable BEFORE scorer contact.
        # A scorer exception or process death leaves it behind, so a retry
        # cannot silently spend a second official scoring job.
        with started_path.open("x", encoding="utf-8") as stream:
            json.dump({**binding, "attempt_state": "STARTED"}, stream,
                      sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        directory_fd = os.open(result_path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        result = scorer(outputs_copy, lock, data_root)
        aggregate = result.get("aggregate") if isinstance(result, Mapping) else None
        per_sample = result.get("per_sample") if isinstance(result, Mapping) else None
        if (not isinstance(aggregate, Mapping)
                or aggregate.get("identity_check", {}).get("passed") is not True
                or not isinstance(per_sample, list)
                or len(per_sample) != len(ids)
                or {row.get("sample_id") for row in per_sample} != set(ids)):
            raise ScoreBatchError("derived official scorer did not return complete identities")
        result_bytes = (json.dumps({scorer_id: result}, ensure_ascii=False,
                                   sort_keys=True, indent=2) + "\n").encode("utf-8")
        with result_path.open("xb") as stream:
            stream.write(result_bytes)
        receipt = {**binding, "result_sha256": hashlib.sha256(result_bytes).hexdigest()}
        with receipt_path.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, sort_keys=True, indent=2)
            stream.write("\n")
        return result
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
