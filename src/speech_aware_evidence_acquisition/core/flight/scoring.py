"""Immutable generation seal inputs for one deferred official finalization job."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Mapping

from ..scoring_batch import load_score_jobs


class DeferredScoringError(ValueError):
    """A generation seal was replaced or its scoring inputs no longer match."""


def _hash(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _write_once(path: Path, payload: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


def seal_scoring_inputs(
    manifest_path: Path, *, run_id: str, attempt_id: str,
    ledger_cells: Mapping[str, object],
) -> dict[str, object]:
    """Keep the pre-score manifest addressable even when finalization attaches scores."""
    manifest_path = Path(manifest_path).resolve()
    directory = manifest_path.parent
    generation = directory / f"{run_id}.generation-manifest.json"
    ledger = directory / "score-ledger-cells.json"
    jobs = directory / "score-jobs.jsonl"
    _write_once(generation, manifest_path.read_bytes())
    _write_once(ledger, (json.dumps(dict(ledger_cells), sort_keys=True) + "\n").encode())
    _write_once(jobs, (json.dumps({
        "job_id": attempt_id, "manifest": str(manifest_path), "ledger_cells": str(ledger),
    }, sort_keys=True) + "\n").encode())
    result = {"finalize": {"status": "deferred-to-score-worker"}}
    for key, path in (
        ("generation_manifest", generation), ("score_ledger_cells", ledger), ("score_jobs", jobs),
    ):
        result[f"{key}_path"] = str(path)
        result[f"{key}_sha256"] = _hash(path)
    return result


def load_sealed_score_jobs(seal: Mapping[str, object]):
    """Refuse a changed source or job table before the official scorer starts."""
    for key in ("generation_manifest", "score_ledger_cells", "score_jobs"):
        path = Path(seal[f"{key}_path"])
        if _hash(path) != seal[f"{key}_sha256"]:
            raise DeferredScoringError(f"sealed {key} hash mismatch")
    manifest = Path(seal["manifest_path"])
    if _hash(manifest) != seal["generation_manifest_sha256"]:
        raise DeferredScoringError("unscored manifest changed after generation seal")
    return load_score_jobs(Path(seal["score_jobs_path"]), require_ledger_cells=True)
