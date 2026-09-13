"""Finalize: verify -> score -> write scores -> re-verify -> upload -> ledger
-> mark FINALIZED. The only path that ever transitions an attempt to
FINALIZED.

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ...e0.artifacts import REPO_ROOT, write_json_artifact
from ..attempts import (
    AttemptError,
    AttemptHandle,
    AttemptStore,
    STATE_FINALIZED,
    STATE_OPENED,
)
from ..scorers import score_bundle
from ..tracking import ledger_row_for_bundle, log_bundle
from . import STATUS_COMPLETED, BundleError, _confine_child_path, _refuse_if_inside_repo
from .git_commit import require_clean_load_bearing_surface
from .manifest import _attach_scores
from .verify import verify_bundle


@dataclass(frozen=True)
class FinalizeResult:
    manifest_path: Path
    scores_path: Path | None
    ledger_markdown_path: Path
    ledger_json_path: Path
    ledger_row_markdown: str
    ledger_cells: Mapping[str, str]
    mlflow_run_id: str | None
    attempt_state: str


def _validate_artifact_finalization_binding(
    bundle, repo_root: Path, data_root: Path
) -> None:
    """Rebuild an artifact flight's frozen config and bind its proposal rows."""
    from ...contracts import ExecutionPlan
    from ..config import compose
    from ..flight.runtime import validate_artifact_result_binding

    require_clean_load_bearing_surface(Path(repo_root))
    manifest = bundle.manifest
    config = manifest.get("config")
    fragments = config.get("fragments") if isinstance(config, Mapping) else None
    if not isinstance(fragments, Mapping) or set(fragments) != {
        "model",
        "dataset",
        "baseline",
        "experiment",
    }:
        raise BundleError(
            "artifact finalization requires exact frozen config fragments"
        )
    try:
        composed = compose(Path(repo_root), **dict(fragments))
        plan = ExecutionPlan(**manifest["plan"]).validate()
        binding = validate_artifact_result_binding(
            composed.values,
            plan=plan,
            repo_root=Path(repo_root),
            sample_ids=tuple(sorted(bundle.split_ids)),
            data_root=Path(data_root),
        )
    except (KeyError, TypeError, ValueError, RuntimeError, OSError) as error:
        raise BundleError(
            f"artifact finalization binding is invalid: {error}"
        ) from error
    if (
        composed.config_hash != config.get("config_hash")
        or binding != manifest.get("artifact_result")
        or manifest.get("result_kind") != "artifact"
    ):
        raise BundleError(
            "artifact manifest differs from its frozen composed configuration"
        )
    if any(
        row.get("result_kind") != "artifact"
        or row.get("artifact_role") != binding.get("role")
        for row in bundle.outputs_rows
    ):
        raise BundleError("artifact outputs do not carry the registered proposal role")


def finalize_bundle(
    manifest_path: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path = REPO_ROOT,
    ledger_cells: Mapping[str, str] | None = None,
    tracking_uri: str | None = None,
    mlflow_metrics: Mapping[str, float] | None = None,
) -> FinalizeResult:
    """Verify, score, write scores, re-verify, (optionally) upload to
    MLflow, emit a machine-derived ledger row, and mark the attempt
    FINALIZED. Refuses (``BundleError``) unless the manifest's own status is
    COMPLETED AND the attempt's durable state file (re-read fresh, never
    trusted from the manifest) is OPENED -- the latter is the authoritative
    check: a hand-edited manifest claiming COMPLETED cannot finalize an
    attempt whose actual on-disk state is ABORTED.

    ``repo_root`` (CRITICAL fix, round-2 external-threat-model review) is
    threaded straight into :func:`core.scorers.score_bundle`, which re-verifies
    the D3 scoring-source freeze, this study's speech-only carrier scope, and
    a clean study tree BEFORE any scorer runs or anything is written -- see
    ``core.scorers._assert_scoring_entry_gate``'s docstring. Default
    ``REPO_ROOT`` matches every other real-run entry point (e.g.
    ``run_experiment_bundled``'s own ``repo_root`` parameter); tests may
    override it to point at an isolated synthetic repo."""

    # Repo confinement (IMPORTANT fix, T6 fix round), checked independently
    # here too -- defense in depth mirroring build_manifest's own check,
    # in case a manifest ever reaches this function by some path other than
    # build_manifest (a hand-placed file, a future caller). Scores and
    # ledger rows are written under the SAME directory as manifest_path, so
    # one check here covers all of this function's writes.
    _refuse_if_inside_repo(Path(manifest_path).parent, "run bundle directory")

    bundle = verify_bundle(manifest_path)
    from .delivery import DELIVERY_MANIFEST_SCHEMA

    if bundle.manifest.get("schema") == DELIVERY_MANIFEST_SCHEMA:
        raise BundleError(
            "cannot finalize a delivery derivative: score it without an independent attempt"
        )
    if bundle.manifest.get("status") != STATUS_COMPLETED:
        raise BundleError(
            f"cannot finalize {manifest_path}: manifest status is "
            f"{bundle.manifest.get('status')!r}, not {STATUS_COMPLETED!r}"
        )
    if bundle.manifest.get("result_kind", "task-answer") == "artifact":
        _validate_artifact_finalization_binding(bundle, Path(repo_root), Path(root))
    if bundle.attempt_state != STATE_OPENED:
        raise BundleError(
            f"cannot finalize {manifest_path}: the attempt's durable state on disk is "
            f"{bundle.attempt_state!r}, not {STATE_OPENED!r} -- the attempt file, not the "
            "manifest's self-reported status, is authoritative (I7)"
        )

    cells = dict(ledger_cells or {})
    if "artifact hashes" in cells:
        raise ValueError(
            "artifact hashes is machine-derived after scoring and must not be "
            "hand-supplied to finalize_bundle"
        )
    validation_cells = dict(cells)
    if tracking_uri is not None and "MLflow run" not in validation_cells:
        validation_cells["MLflow run"] = "pending runtime assignment"
    # Validate the complete human-ledger surface before the scorer can write
    # scores or mutate the manifest.  The machine-derived artifact-hash cell
    # is recomputed again after scores attach.
    ledger_row_for_bundle(bundle, validation_cells)

    run_dir = Path(manifest_path).resolve().parent
    run_id = str(bundle.manifest["run_id"])
    scores_path = None
    if bundle.manifest.get("result_kind", "task-answer") == "artifact":
        # Proposal artifacts are auditable model outputs, not task answers.
        # Their empty scorer declaration closes without entering a task scorer.
        bundle = verify_bundle(manifest_path)
    else:
        scores = score_bundle(bundle, lock, root, repo_root=repo_root)
        scores_path = _confine_child_path(
            run_dir, f"{run_id}.scores.json", "run scores path"
        )
        write_json_artifact(scores_path, scores)
        _attach_scores(Path(manifest_path), scores_path)

        # Re-verify over the now-complete bundle and its score attachment.
        bundle = verify_bundle(manifest_path)

    mlflow_run_id = None
    if tracking_uri is not None:
        mlflow_run_id = log_bundle(bundle, tracking_uri, metrics=mlflow_metrics)

    if mlflow_run_id is not None:
        # Overwrite (not setdefault): the caller cannot have known the real
        # mlflow_run_id before this call returned it, so any hand-supplied
        # placeholder here is necessarily stale, not an intentional override.
        cells["MLflow run"] = mlflow_run_id
    row_markdown, merged_cells = ledger_row_for_bundle(bundle, cells)
    ledger_markdown_path = _confine_child_path(
        run_dir, f"{run_id}.ledger-row.md", "ledger markdown path"
    )
    ledger_json_path = _confine_child_path(
        run_dir, f"{run_id}.ledger-row.json", "ledger json path"
    )
    ledger_markdown_path.write_text(row_markdown + "\n", encoding="utf-8", newline="\n")
    write_json_artifact(ledger_json_path, merged_cells)

    attempt_meta = bundle.manifest["attempt"]
    handle = AttemptHandle(
        path=Path(str(attempt_meta["state_path"])),
        run_id=str(attempt_meta["run_id"]),
        attempt_id=str(attempt_meta["attempt_id"]),
    )
    handle.mark_finalized()

    return FinalizeResult(
        manifest_path=Path(manifest_path),
        scores_path=scores_path,
        ledger_markdown_path=ledger_markdown_path,
        ledger_json_path=ledger_json_path,
        ledger_row_markdown=row_markdown,
        ledger_cells=merged_cells,
        mlflow_run_id=mlflow_run_id,
        attempt_state=STATE_FINALIZED,
    )


def abort_attempt_if_opened(data_root: Path, run_id: str, attempt_id: str | None, *, reason: str) -> bool:
    """Thin convenience wrapper so ``core.driver`` doesn't need to know the
    attempts-root layout: mark the attempt ABORTED if it was ever opened.
    A ``None``/malformed ``attempt_id`` is a no-op (False) -- there was never
    anything to abort at the store layer in that case."""

    if not isinstance(attempt_id, str) or not attempt_id.strip():
        return False
    store = AttemptStore(Path(data_root) / "attempts")
    try:
        return store.abort_if_opened(run_id, attempt_id, reason=reason)
    except AttemptError:
        return False
