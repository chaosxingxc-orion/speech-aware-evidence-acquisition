"""Run-manifest construction: repo confinement, ``build_manifest``.

Split out of the former monolithic ``core/bundle.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). R0 repair refactor stage 2 (part C):
the git-commit resolution helpers (``_git``/``_study_commit``/
``require_clean_study_repo``/``_resolve_study_commit``) and the ABORTED-
manifest best-effort cost block (``_best_effort_cost_for_aborted_attempt``)
moved to ``git_commit.py``/``aborted_cost.py`` respectively, again purely for
file size -- both stay importable from exactly ``core.bundle`` (this
module re-exports ``require_clean_study_repo``, the one name
``core/bundle/__init__.py`` itself re-exports onward).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...contracts import STUDY_SLUG, ExecutionPlan
from ...e0.artifacts import sha256_file, write_json_artifact
from ..base import RunResult
from ..config import ComposedConfig
from ..legality import describe_legality_for_manifest
from ..split_receipt import VerifiedSplit
from . import (
    RUN_MANIFEST_SCHEMA,
    STATUS_ABORTED,
    STATUS_COMPLETED,
    _VALID_STATUSES,
    BundleError,
    _confine_child_path,
    _refuse_if_inside_repo,
)
from .aborted_cost import _best_effort_cost_for_aborted_attempt
from .git_commit import _resolve_study_commit, require_clean_study_repo  # noqa: F401 (re-export)


def _artifact_meta(path: Path) -> dict[str, str]:
    return {"path": str(Path(path).resolve()), "sha256": sha256_file(path)}


def _manifest_document(
    *,
    repo_root: Path,
    data_root: Path,
    composed: ComposedConfig,
    plan: ExecutionPlan,
    verified_split: VerifiedSplit,
    session_receipt_path: Path | None,
    run_dir: Path,
    status: str,
    failure_reason: str | None,
    result: RunResult | None,
    now: Callable[[], datetime],
    predecessor_attempt: Mapping[str, object] | None = None,
    predecessor_attempts: Sequence[Mapping[str, object]] | None = None,
    row_checkpoint: Mapping[str, object] | None = None,
) -> dict[str, object]:
    if row_checkpoint is not None:
        # Owner decision 309: the attempt's durable row checkpoint, pinned by
        # its whole-file sha256. Shape-checked here; the content (hash, chain,
        # counts, byte equality with the outputs rows) is re-derived from disk
        # by core.bundle.verify_bundle.
        from ..row_checkpoint import RowCheckpointError, is_sha256  # noqa: PLC0415

        expected = {
            "schema", "path", "sha256", "row_count", "complete_rows",
            "unrendered_rows", "last_sha",
        }
        if (
            status != STATUS_COMPLETED
            or not isinstance(row_checkpoint, Mapping)
            or set(row_checkpoint) != expected
            or not is_sha256(row_checkpoint.get("sha256"))
        ):
            raise BundleError(
                "row_checkpoint must be a COMPLETED manifest's block with exactly "
                f"{sorted(expected)} and a 64-hex sha256"
            )
    if status not in _VALID_STATUSES:
        raise BundleError(
            f"manifest status must be one of {_VALID_STATUSES}, got {status!r}"
        )
    if status == STATUS_COMPLETED:
        if failure_reason is not None:
            raise BundleError("a COMPLETED manifest must not carry a failure_reason")
        if result is None:
            raise BundleError("a COMPLETED manifest requires the run's RunResult")
    if status == STATUS_ABORTED and not (
        isinstance(failure_reason, str) and failure_reason.strip()
    ):
        raise BundleError("an ABORTED manifest requires a non-empty failure_reason")

    attempt_id = plan.attempt_id
    if not isinstance(attempt_id, str) or not attempt_id.strip():
        raise BundleError(
            "a run manifest requires a plan with a non-empty attempt_id (R0 repair T4/T6)"
        )
    # E10 (owner decision 22, 2026-09-18): a resume-recovery declares the
    # aborted attempt whose COMPLETE rows this manifest keeps. Shape-checked
    # here so a malformed block never reaches disk; the CONTENT (the trace
    # bytes, the kept-row hash, each kept row's custody) is re-derived from
    # disk by core.bundle.verify_bundle, which trusts none of it.
    if predecessor_attempt is not None and predecessor_attempts is not None:
        raise BundleError(
            "a run manifest declares predecessor_attempt or predecessor_attempts, "
            "never both"
        )
    if predecessor_attempt is not None:
        from .outputs import RESUME_PREDECESSOR_SCHEMA, _validate_predecessor_block

        if status != STATUS_COMPLETED:
            raise BundleError(
                f"only a {STATUS_COMPLETED} manifest declares a predecessor attempt"
            )
        predecessor_attempt = _validate_predecessor_block(
            predecessor_attempt, run_id=plan.run_id, attempt_id=attempt_id
        )
        if predecessor_attempt["schema"] != RESUME_PREDECESSOR_SCHEMA:
            raise BundleError("predecessor attempt block has the wrong schema")
    # E10d (2026-09-29): the multi-predecessor form -- one block per pinned
    # predecessor attempt whose COMPLETE rows this manifest keeps, validated
    # exactly as a single block is plus cross-block disjointness (defence in
    # depth; ``core.flight.resume.MergedPredecessors`` already refused an
    # overlap before this manifest was ever built).
    if predecessor_attempts is not None:
        from .outputs import _validate_predecessor_blocks_list

        if not predecessor_attempts:
            raise BundleError(
                "predecessor_attempts must be a non-empty list when given"
            )
        if status != STATUS_COMPLETED:
            raise BundleError(
                f"only a {STATUS_COMPLETED} manifest declares predecessor attempts"
            )
        predecessor_attempts = _validate_predecessor_blocks_list(
            list(predecessor_attempts), run_id=plan.run_id, attempt_id=attempt_id,
        )
    run_id = plan.run_id
    run_dir = Path(run_dir).resolve()

    outputs_meta = None
    raw_trace_meta = None
    trace_manifest_meta = None
    cost = None
    if result is not None:
        outputs_path = Path(result.outputs_path).resolve()
        if not outputs_path.is_file():
            raise BundleError(f"RunResult.outputs_path does not exist: {outputs_path}")
        outputs_meta = _artifact_meta(outputs_path)
        raw_trace_path = run_dir / f"{run_id}.trace.jsonl"
        trace_manifest_path = run_dir / f"{run_id}.trace-manifest.json"
        if raw_trace_path.is_file():
            raw_trace_meta = _artifact_meta(raw_trace_path)
        if trace_manifest_path.is_file():
            trace_manifest_meta = _artifact_meta(trace_manifest_path)
        cost = dict(result.cost)
    else:
        # Best-effort: an aborted attempt may still have left a partial trace
        # (never outputs -- run_experiment only writes outputs after every
        # sample succeeds) on disk; bind whatever genuinely exists so the
        # aborted bundle is still auditable, never pretend it is complete.
        raw_trace_path = run_dir / f"{run_id}.trace.jsonl"
        if raw_trace_path.is_file():
            raw_trace_meta = _artifact_meta(raw_trace_path)
        # R0 repair T7 (I8): an ABORTED manifest must not carry cost=None --
        # that would silently omit any failed-attempt cost this attempt (or a
        # prior sibling attempt on the same run_id) genuinely incurred.
        cost = _best_effort_cost_for_aborted_attempt(data_root, run_id, attempt_id)

    session_meta = None
    if session_receipt_path is not None:
        session_path = Path(session_receipt_path).resolve()
        if session_path.is_file():
            session_meta = _artifact_meta(session_path)

    attempts_root = Path(data_root) / "attempts"
    attempt_state_path = attempts_root / run_id / f"{attempt_id}.json"

    # E0-prime flight protection (2026-08-16): for a COMPLETED manifest, this
    # now tolerates dirt confined outside git_commit.LOAD_BEARING_SURFACE_
    # PREFIXES rather than refusing outright -- see git_commit.py's module
    # docstring for the incident this repairs. `study_repo_dirt` is an
    # ADDITIVE field: old manifests (built before this fix) simply lack it,
    # and nothing in verify_bundle requires its presence.
    study_commit, study_repo_dirt = _resolve_study_commit(
        Path(repo_root), Path(data_root), status
    )

    from .delivery_replay import (
        require_experiment_phase_declarations,
        validate_phase_delivery_sources,
    )

    delivery_fragments = {
        f"{kind}_fragment": composed.fragments.get(kind)
        for kind in ("model", "dataset", "baseline")
    }
    required_deliveries = validate_phase_delivery_sources(
        composed.values,
        parent_fragments=delivery_fragments,
    )
    require_experiment_phase_declarations(
        repo_root,
        composed.fragments.get("experiment"),
        required_deliveries,
        delivery_fragments,
    )
    delivery_metadata = (
        {"required_phase_deliveries": list(required_deliveries)}
        if required_deliveries
        else {}
    )
    artifact_content_source = None
    artifact_binding = composed.values.get("artifact_result")
    if (
        isinstance(artifact_binding, dict)
        and artifact_binding.get("schema") in {
            "saea-artifact-result-binding-v2",
            "saea-artifact-result-binding-v3",
        }
    ):
        from ...rails.training_feedback_artifacts import artifact_content_source_pin

        contract = artifact_binding.get("content_contract")
        try:
            source = artifact_content_source_pin(contract)
        except (AttributeError, ValueError) as error:
            raise BundleError(f"typed artifact content source is malformed: {error}") from error
        if not isinstance(source, dict) or not isinstance(source.get("data_relpath"), str):
            raise BundleError("typed artifact content source is malformed")
        source_path = Path(data_root) / source["data_relpath"]
        artifact_content_source = _artifact_meta(source_path)
    return {
        **delivery_metadata,
        "schema": RUN_MANIFEST_SCHEMA,
        "study": STUDY_SLUG,
        "run_id": run_id,
        "created_at": now().astimezone(timezone.utc).isoformat(),
        "status": status,
        "failure_reason": failure_reason,
        "study_commit": study_commit,
        # Non-load-bearing paths that were dirty when study_commit was
        # bound (always [] for a genuinely clean tree, and always [] for an
        # ABORTED manifest -- see _resolve_study_commit's docstring).
        # Auditability, not a claim of significance: a human reviewing this
        # manifest can see exactly what was tolerated, never silently.
        "study_repo_dirt": study_repo_dirt,
        # I-1 fix: the arm this attempt actually ran under -- needed so
        # verify_bundle can independently recompute protocol_hash from
        # (config_hash, arm, split_identity_hash) via the exact same
        # core.config.protocol_hash convention core.driver.run_experiment
        # itself checks at run time, rather than merely trusting the
        # manifest's own protocol_hash field.
        "arm": str(composed.values.get("arm", "")),
        # E1-prime (deliverable 3, docs/readiness/2026-08-15-legality-doctrine.md):
        # span_source/reference_source/legality_tier recorded VERBATIM, plus
        # the independently-recomputed oracle-lineage verdict and
        # grandfathering warning text -- computed fresh from composed.values
        # here (never threaded through RunResult) so this can never raise and
        # is identical whether this manifest is COMPLETED or ABORTED. See
        # core.legality.describe_legality_for_manifest's own docstring for
        # why this never duplicates core.driver.run.run_experiment's own
        # stderr warning.
        "legality": describe_legality_for_manifest(composed.values, data_root),
        "config": {
            "fragments": dict(composed.fragments),
            "config_hash": composed.config_hash,
        },
        "protocol_hash": plan.protocol_hash,
        "plan": {
            "schema": plan.schema,
            "study": plan.study,
            "run_id": plan.run_id,
            "execution_profile": plan.execution_profile,
            "carrier_lock_key": plan.carrier_lock_key,
            "split_role": plan.split_role,
            "split_identity_hash": plan.split_identity_hash,
            "planned_model_calls": plan.planned_model_calls,
            "planned_gpu_hours": plan.planned_gpu_hours,
            "planned_speech_audio_seconds": plan.planned_speech_audio_seconds,
            "protocol_hash": plan.protocol_hash,
            "attempt_id": plan.attempt_id,
            # The allowance is an InitVar and is absent from dataclasses.asdict.
            # Preserve its source binding for independent seal verification;
            # omit it entirely for historical discovery/dev manifests.
            **({"owner_allowance": {
                "path": plan.owner_allowance.path,
                "sha256": plan.owner_allowance.sha256,
            }} if plan.owner_allowance is not None else {}),
        },
        "exposure_run_id": plan.run_id,
        "split": {
            "name": str(composed.values.get("split_name", "")),
            "role": verified_split.split_role,
            "carrier_lock_key": verified_split.carrier_lock_key,
            "identity_hash": verified_split.identity_hash,
            # I-1 fix: verify_bundle now cross-checks this against len(ids) --
            # a manifest whose ids were edited without updating this count
            # (or vice versa) refuses rather than being silently accepted.
            "count": len(verified_split.ids),
            "ids": sorted(verified_split.ids),
        },
        **(
            {"predecessor_attempt": dict(predecessor_attempt)}
            if predecessor_attempt is not None
            else {}
        ),
        **(
            {"predecessor_attempts": [dict(block) for block in predecessor_attempts]}
            if predecessor_attempts is not None
            else {}
        ),
        **(
            {"row_checkpoint": dict(row_checkpoint)}
            if row_checkpoint is not None
            else {}
        ),
        "session_receipt": session_meta,
        "outputs": outputs_meta,
        "raw_trace": raw_trace_meta,
        "trace_manifest": trace_manifest_meta,
        "scores": None,
        **(
            {"artifact_content_source": artifact_content_source}
            if artifact_content_source is not None
            else {}
        ),
        "scorers": list(composed.values.get("scorers", [])),
        **(
            {
                "result_kind": "artifact",
                "artifact_result": dict(composed.values["artifact_result"]),
            }
            if composed.values.get("result_kind", "task-answer") == "artifact"
            else {}
        ),
        "cost": cost,
        "attempt": {
            "run_id": run_id,
            "attempt_id": attempt_id,
            "state_path": str(attempt_state_path),
        },
    }


def build_manifest(
    *,
    repo_root: Path,
    data_root: Path,
    composed: ComposedConfig,
    plan: ExecutionPlan,
    verified_split: VerifiedSplit,
    session_receipt_path: Path | None,
    run_dir: Path,
    status: str,
    failure_reason: str | None = None,
    result: RunResult | None = None,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    predecessor_attempt: Mapping[str, object] | None = None,
    predecessor_attempts: Sequence[Mapping[str, object]] | None = None,
    row_checkpoint: Mapping[str, object] | None = None,
) -> Path:
    """Build and durably write one attempt's run manifest; return its path.

    ``row_checkpoint`` (owner decision 309) is the attempt's durable row
    checkpoint block (``core.row_checkpoint.CheckpointDocument.manifest_block``).

    ``predecessor_attempt`` is passed only by a resume-recovery (E10, owner
    decision 22): the aborted attempt of this same run id whose COMPLETE rows
    this manifest keeps, with its trace sha256 and the sorted kept-row list.
    ``predecessor_attempts`` (E10d, 2026-09-29) is the plural form for a
    resume-recovery pinned to MULTIPLE predecessor attempts; exactly one of
    the two may be given, never both.
    """

    # Repo confinement FIRST (IMPORTANT fix, T6 fix round): the cheapest,
    # dependency-free check, before touching git or the filesystem for
    # anything else -- a manifest destined for inside the repository is
    # refused before any other work happens, on COMPLETED and ABORTED calls
    # alike (they share this one function).
    _refuse_if_inside_repo(run_dir, "run manifest run_dir")

    document = _manifest_document(
        repo_root=repo_root,
        data_root=data_root,
        composed=composed,
        plan=plan,
        verified_split=verified_split,
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=status,
        failure_reason=failure_reason,
        result=result,
        now=now,
        predecessor_attempt=predecessor_attempt,
        predecessor_attempts=predecessor_attempts,
        row_checkpoint=row_checkpoint,
    )
    manifest_path = _confine_child_path(
        run_dir, f"{plan.run_id}.run-manifest.json", "run manifest path"
    )
    write_json_artifact(manifest_path, document)
    return manifest_path


def _attach_scores(manifest_path: Path, scores_path: Path) -> None:
    try:
        document = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise BundleError(f"cannot read run manifest {manifest_path}: {error}") from error
    document["scores"] = _artifact_meta(scores_path)
    write_json_artifact(manifest_path, document)
