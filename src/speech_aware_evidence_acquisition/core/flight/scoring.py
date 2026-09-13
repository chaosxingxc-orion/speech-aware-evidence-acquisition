"""Immutable generation seal inputs for one deferred official finalization job."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..scoring_batch import ScoreJob, load_score_jobs


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
    ledger_cells: Mapping[str, object], delivery_cells: Sequence[str] = (),
) -> dict[str, object]:
    """Pin raw generation and route it to finalization or declared derivatives."""
    manifest_path = Path(manifest_path).resolve()
    directory = manifest_path.parent
    generation = directory / f"{run_id}.generation-manifest.json"
    ledger = directory / "score-ledger-cells.json"
    jobs = directory / "score-jobs.jsonl"
    _write_once(generation, manifest_path.read_bytes())
    if delivery_cells:
        return {
            "finalize": {"status": "deferred-to-declared-deliveries"},
            "delivery_required": True,
            "declared_delivery_cells": list(delivery_cells),
            "generation_manifest_path": str(generation),
            "generation_manifest_sha256": _hash(generation),
        }
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

_DELIVERY_CELL = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")


@dataclass(frozen=True)
class PreparedDeliveryScoreJobs:
    """Verified derivative manifests and their one-complete-bundle score jobs."""

    jobs: tuple[ScoreJob, ...]
    jobs_path: Path
    derivatives: tuple[Mapping[str, str], ...]
    parent_sha256: str


def prepare_declared_delivery_score_jobs(
    *,
    parent_manifest: Path,
    generation_manifest: Path,
    generation_manifest_sha256: str,
    repo_root: Path,
    data_root: Path,
    experiment_path: Path,
    delivery_cells: Sequence[str],
    output_root: Path,
    jobs_path: Path,
    delivery_builder: Callable[..., Path],
) -> PreparedDeliveryScoreJobs:
    """Build exactly the sealed declarations after rechecking the raw parent."""

    parent_manifest = Path(parent_manifest).resolve()
    generation_manifest = Path(generation_manifest).resolve()
    repo_root = Path(repo_root).resolve()
    experiment_path = Path(experiment_path).resolve()
    output_root = Path(output_root)
    jobs_path = Path(jobs_path)
    cells = tuple(delivery_cells)
    if (
        not cells
        or any(not isinstance(cell, str) or not _DELIVERY_CELL.fullmatch(cell) for cell in cells)
        or len(set(cells)) != len(cells)
    ):
        raise DeferredScoringError("declared delivery cells must be unique safe identifiers")
    if not isinstance(generation_manifest_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", generation_manifest_sha256
    ):
        raise DeferredScoringError("sealed generation manifest SHA-256 is invalid")
    if not parent_manifest.is_file() or not generation_manifest.is_file():
        raise DeferredScoringError("sealed generation manifest is missing")
    if _hash(generation_manifest) != generation_manifest_sha256:
        raise DeferredScoringError("sealed generation manifest hash mismatch")
    if _hash(parent_manifest) != generation_manifest_sha256:
        raise DeferredScoringError("raw generation manifest changed after generation seal")
    expected_experiment_root = (repo_root / "configs" / "experiment").resolve()
    if (
        not experiment_path.is_file()
        or experiment_path.parent != expected_experiment_root
        or experiment_path.suffix != ".json"
    ):
        raise DeferredScoringError("declared delivery experiment path is not registered")
    from ..config import read_fragment

    experiment = read_fragment(repo_root, "experiment", experiment_path.stem)
    declarations = experiment.get("delivery_derivatives")
    if not isinstance(declarations, list):
        raise DeferredScoringError("recorded experiment lacks declared deliveries")
    selected = []
    for cell in cells:
        matches = [
            item for item in declarations
            if isinstance(item, Mapping) and item.get("cell_id") == cell
        ]
        if len(matches) != 1:
            raise DeferredScoringError(
                "sealed delivery cells differ from the recorded experiment"
            )
        selected.append(matches[0])
    allowed_selectors = {
        "saea-phase-response-pair-v1",
        "saea-sealed-state-response-pair-v1",
    }
    if any(
        not isinstance(item.get("source_selector"), Mapping)
        or item["source_selector"].get("schema") not in allowed_selectors
        for item in selected
    ):
        raise DeferredScoringError(
            "runtime delivery scoring requires a registered phase selector; "
            "legacy delivery parents retain the explicit build-delivery path"
        )
    if os.path.lexists(output_root) or os.path.lexists(jobs_path):
        raise DeferredScoringError("declared delivery scoring output already exists")
    output_root.mkdir(parents=True, exist_ok=False)
    derivatives = []
    rows = []
    for cell in cells:
        manifest = Path(delivery_builder(
            parent_manifest=parent_manifest,
            repo_root=repo_root,
            experiment_path=experiment_path,
            data_root=Path(data_root),
            derivative_cell_id=cell,
            output_dir=output_root / cell,
        )).resolve()
        digest = _hash(manifest)
        derivatives.append({"cell_id": cell, "manifest_path": str(manifest), "manifest_sha256": digest})
        rows.append(json.dumps({"job_id": cell, "manifest": str(manifest)}, sort_keys=True))
    _write_once(jobs_path, (("\n".join(rows)) + "\n").encode())
    jobs = tuple(load_score_jobs(jobs_path))
    if tuple(job.job_id for job in jobs) != cells:
        raise DeferredScoringError("delivery score jobs differ from sealed declarations")
    return PreparedDeliveryScoreJobs(
        jobs=jobs,
        jobs_path=jobs_path.resolve(),
        derivatives=tuple(derivatives),
        parent_sha256=generation_manifest_sha256,
    )
