"""Offline/deferred entity-class WER scoring (owner decision D-3).

B-2a's own precedent (``docs/readiness/2026-08-09-exploration-plan.md`` /
``2026-08-11-validation-plan-wa-wd.md``): "entity-class WER pre-registered as
deferred computation -- outputs are persisted, the adapter version is pinned
before any deferred read." This module is that deferred read.

Model-free, read-only: locates an already-produced, FINALIZED attempt's
``<run_id>.run-manifest.json`` + ``<run_id>.outputs.jsonl`` under a stable
``run_dir`` (the SAME ``<run_dir>/attempt-*/`` convention
``analysis.context_dose``/``core.driver.smoke.fresh_attempt_id`` already
established -- :func:`~speech_aware_evidence_acquisition.analysis.context_dose.find_completed_attempt`
is reused directly rather than re-implemented, since that attempt-selection
logic is carrier/metric-agnostic), then scores the outputs through the SAME
``entity-wer`` scorer (``core.scorers.score_entity_wer_outputs``) the in-run
path registers under ``core.base.SCORERS`` -- so the offline and in-run
paths are bit-identical, never a second, drifting implementation.

NEVER modifies the attempt directory: that tree is finalized and hash-bound
(``core.bundle.finalize_bundle`` already proved its bytes internally
consistent; this tool only reads them). The verdict this tool produces is
written to a SEPARATE location this module owns exclusively,
``$SPEECHRL_DATA_DIR/derived/entity-wer/<run_id>/<run_id>.<attempt_id>.entity-wer.json``
-- carrying ``core.scorers.ENTITY_WER_ADAPTER_VERSION`` so a later deferred
read against a different adapter version is auditable (the B-2a precedent's
own "the adapter version is pinned before any deferred read").

Deliberately does NOT go through ``core.bundle.score_bundle``/
``verify_bundle`` (that full I7 chain additionally requires a clean git tree
-- wrong for a read-only analysis tool a reviewer might run against a dirty
working tree) nor ``contracts.FrozenCoreGate`` (the D3/scope/model-touch
machinery a pure post-hoc, model-free read has no need to re-litigate --
exactly the same design choice ``analysis.context_dose`` already made; see
its own module docstring). This module's own integrity floor, narrower than
I7 but real: only a manifest whose OWN durable attempt-state file (re-read
fresh from ``core.attempts``, never trusted from the manifest's self-reported
``status`` alone) reads ``state == FINALIZED`` is eligible, and the outputs
bytes are re-hashed against the manifest's own recorded sha256 before
scoring.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from ..core.attempts import STATE_FINALIZED
from ..core.bundle import STATUS_COMPLETED
from ..core.scorers import ENTITY_WER_ADAPTER_VERSION, ScoringPhaseError, score_entity_wer_outputs
from ..e0.artifacts import sha256_file, write_json_artifact
from .context_dose import ComparisonError, find_completed_attempt

REPORT_SCHEMA = "saea-entity-wer-offline-verdict-v1"


class EntityWerOfflineError(RuntimeError):
    """No usable FINALIZED attempt exists for the requested run, or its
    outputs cannot be resolved/verified/scored; refuse rather than emit a
    verdict over a non-finalized, missing, or tampered artifact."""


def _resolve_and_verify_outputs_path(manifest: Mapping[str, object], manifest_path: Path) -> Path:
    """Same light integrity check ``analysis.context_dose`` already applies
    to its own three arms: re-hash the outputs bytes against the manifest's
    OWN recorded sha256 before trusting them -- narrower than full I7
    verification, but real, and enough for a read-only offline tool."""

    outputs_meta = manifest.get("outputs")
    if not isinstance(outputs_meta, Mapping) or not outputs_meta.get("path"):
        raise EntityWerOfflineError(f"manifest {manifest_path} carries no outputs artifact to score")
    outputs_path = Path(str(outputs_meta["path"]))
    if not outputs_path.is_file():
        raise EntityWerOfflineError(
            f"outputs artifact recorded in {manifest_path} does not exist: {outputs_path}"
        )
    recorded_sha256 = outputs_meta.get("sha256")
    if isinstance(recorded_sha256, str) and recorded_sha256:
        actual_sha256 = sha256_file(outputs_path)
        if actual_sha256 != recorded_sha256:
            raise EntityWerOfflineError(
                f"outputs artifact {outputs_path} sha256 {actual_sha256} does not match the "
                f"manifest's recorded {recorded_sha256}; refusing to score a mismatched artifact"
            )
    return outputs_path


def _read_attempt_state(manifest: Mapping[str, object], manifest_path: Path) -> tuple[str, str]:
    """Re-read the attempt's OWN durable state file fresh (``core.attempts``)
    -- never trust the manifest's self-reported ``status`` alone for whether
    an attempt is genuinely FINALIZED (mirrors ``core.bundle.verify_bundle``'s
    own "the attempt's OWN durable state file is re-read fresh, never trusted
    from the manifest" discipline, module docstring). Returns
    ``(attempt_id, state)``."""

    attempt_meta = manifest.get("attempt")
    if not isinstance(attempt_meta, Mapping):
        raise EntityWerOfflineError(f"manifest {manifest_path} carries no usable 'attempt' block")
    attempt_id = attempt_meta.get("attempt_id")
    state_path_raw = attempt_meta.get("state_path")
    if not isinstance(attempt_id, str) or not attempt_id:
        raise EntityWerOfflineError(f"manifest {manifest_path} attempt.attempt_id is missing/empty")
    if not isinstance(state_path_raw, str) or not state_path_raw:
        raise EntityWerOfflineError(f"manifest {manifest_path} attempt.state_path is missing/empty")
    state_path = Path(state_path_raw)
    if not state_path.is_file():
        raise EntityWerOfflineError(
            f"attempt state file recorded in {manifest_path} does not exist: {state_path}"
        )
    try:
        document = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EntityWerOfflineError(f"cannot read attempt state {state_path}: {error}") from error
    state = document.get("state") if isinstance(document, dict) else None
    if not isinstance(state, str) or not state:
        raise EntityWerOfflineError(f"attempt state {state_path} carries no usable 'state'")
    return attempt_id, state


@dataclass(frozen=True)
class FinalizedAttempt:
    run_id: str
    attempt_id: str
    manifest_path: Path
    manifest: Mapping[str, object]
    outputs_path: Path
    outputs_sha256: str


def find_finalized_attempt(
    run_dir: Path, run_id: str, *, attempt_id: str | None = None
) -> FinalizedAttempt:
    """Locate the FINALIZED attempt to score for ``run_id`` under ``run_dir``
    (the stable parent whose children are ``attempt-*/`` subdirectories).

    Default selection: the most recently created ``COMPLETED`` manifest
    (:func:`~speech_aware_evidence_acquisition.analysis.context_dose.find_completed_attempt`'s
    own selection rule, reused unchanged), additionally required here to be
    genuinely FINALIZED -- "an already-finalized attempt's persisted
    outputs", this tool's own remit, not merely completed-but-not-yet-
    finalized. ``attempt_id``, when given, pins ONE specific attempt
    directory (``run_dir/attempt_id``) instead -- for reproducibility/audit
    and for deterministic tests.

    Fails closed (:class:`EntityWerOfflineError`) for an unknown run
    (``run_dir`` missing/empty), no COMPLETED manifest, or a COMPLETED
    manifest whose attempt state is not FINALIZED.
    """

    run_dir = Path(run_dir)
    if attempt_id is not None:
        attempt_dir = run_dir / attempt_id
        manifest_paths = sorted(attempt_dir.glob("*.run-manifest.json")) if attempt_dir.is_dir() else []
        if not manifest_paths:
            raise EntityWerOfflineError(
                f"no run-manifest.json found under {attempt_dir} for --attempt-id {attempt_id!r}"
            )
        manifest_path = manifest_paths[0]
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise EntityWerOfflineError(f"cannot read manifest {manifest_path}: {error}") from error
        status = manifest.get("status") if isinstance(manifest, dict) else None
        if status != STATUS_COMPLETED:
            raise EntityWerOfflineError(
                f"attempt {attempt_id!r} manifest {manifest_path} status is {status!r}, not "
                f"{STATUS_COMPLETED!r}"
            )
    else:
        if not run_dir.is_dir():
            raise EntityWerOfflineError(
                f"unknown run: no run directory at {run_dir} for run_id {run_id!r}"
            )
        try:
            selection = find_completed_attempt(run_dir)
        except ComparisonError as error:
            raise EntityWerOfflineError(
                f"no usable COMPLETED attempt for run_id {run_id!r} under {run_dir}: {error}"
            ) from error
        manifest_path, manifest = selection.manifest_path, selection.manifest

    manifest_run_id = manifest.get("run_id")
    if manifest_run_id != run_id:
        raise EntityWerOfflineError(
            f"manifest {manifest_path} carries run_id {manifest_run_id!r}, expected {run_id!r}"
        )
    resolved_attempt_id, state = _read_attempt_state(manifest, manifest_path)
    if state != STATE_FINALIZED:
        raise EntityWerOfflineError(
            f"attempt {resolved_attempt_id!r} for run {run_id!r} (manifest {manifest_path}) is "
            f"{state!r}, not {STATE_FINALIZED!r}; only an already-finalized attempt's persisted "
            "outputs may be read here"
        )
    outputs_path = _resolve_and_verify_outputs_path(manifest, manifest_path)
    outputs_meta = manifest.get("outputs")
    outputs_sha256 = (
        str(outputs_meta.get("sha256", "")) if isinstance(outputs_meta, Mapping) else ""
    )
    return FinalizedAttempt(
        run_id=run_id,
        attempt_id=resolved_attempt_id,
        manifest_path=manifest_path,
        manifest=manifest,
        outputs_path=outputs_path,
        outputs_sha256=outputs_sha256,
    )


def score_finalized_attempt(
    attempt: FinalizedAttempt, lock: Mapping[str, object], root: Path
) -> dict[str, object]:
    """Score ``attempt``'s persisted outputs through the SAME registered
    ``entity-wer`` scorer the in-run path uses -- bit-identical to
    ``SCORERS.resolve("entity-wer")(attempt.outputs_path, lock, root)``."""

    try:
        return score_entity_wer_outputs(attempt.outputs_path, lock, root)
    except ScoringPhaseError as error:
        raise EntityWerOfflineError(str(error)) from error


def verdict_document(
    attempt: FinalizedAttempt, scores: Mapping[str, object], *, generated_at: str
) -> dict[str, object]:
    """The JSON verdict this tool persists -- never written into the attempt
    directory itself (that tree stays finalized and untouched)."""

    return {
        "schema": REPORT_SCHEMA,
        "adapter_version": ENTITY_WER_ADAPTER_VERSION,
        "scorer": "entity-wer",
        "generated_at": generated_at,
        "run_id": attempt.run_id,
        "attempt_id": attempt.attempt_id,
        "source_manifest_path": str(attempt.manifest_path),
        "source_outputs_path": str(attempt.outputs_path),
        "source_outputs_sha256": attempt.outputs_sha256,
        "per_sample": scores["per_sample"],
        "aggregate": scores["aggregate"],
    }


def verdict_output_path(data_root_path: Path, run_id: str, attempt_id: str) -> Path:
    """``$SPEECHRL_DATA_DIR/derived/entity-wer/<run_id>/<run_id>.<attempt_id>.entity-wer.json``
    -- a directory this offline tool owns exclusively, distinct from
    ``runs/``/``attempts/`` (never written to by any in-run/finalize path)."""

    return (
        Path(data_root_path)
        / "derived"
        / "entity-wer"
        / run_id
        / f"{run_id}.{attempt_id}.entity-wer.json"
    )


# ---------------------------------------------------------------------------
# CLI entry point (scripts/score_entity_wer.py is a thin wrapper).
# ---------------------------------------------------------------------------


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="score-entity-wer",
        description=(
            "Owner decision D-3: offline/deferred entity-class WER over an already-"
            "finalized attempt's persisted outputs. Model-free, read-only; never "
            "modifies the attempt directory; writes its own verdict under "
            "$SPEECHRL_DATA_DIR/derived/entity-wer/<run_id>/."
        ),
    )
    parser.add_argument("--run", required=True, dest="run_id", help="run_id to score")
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help=(
            "stable run_dir (parent of attempt-*/ subdirectories); default "
            "$SPEECHRL_DATA_DIR/runs/<run_id>"
        ),
    )
    parser.add_argument(
        "--attempt-id",
        default=None,
        help="pin a specific attempt_id instead of the newest FINALIZED one",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    from ..data.lock import data_root, load_lock, umbrella_lock_path

    args = _cli_parser().parse_args(argv)
    root = data_root()
    run_dir = Path(args.run_dir) if args.run_dir is not None else root / "runs" / args.run_id
    lock = load_lock(umbrella_lock_path(args.repo_root))

    try:
        attempt = find_finalized_attempt(run_dir, args.run_id, attempt_id=args.attempt_id)
        scores = score_finalized_attempt(attempt, lock, root)
    except EntityWerOfflineError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    generated_at = datetime.now(timezone.utc).isoformat()
    document = verdict_document(attempt, scores, generated_at=generated_at)
    output_path = verdict_output_path(root, attempt.run_id, attempt.attempt_id)
    write_json_artifact(output_path, document)
    print(
        json.dumps(
            {
                "run_id": attempt.run_id,
                "attempt_id": attempt.attempt_id,
                "verdict": str(output_path),
                "aggregate": scores["aggregate"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
