"""Bind a finalized native episode to its frozen configuration and phase source."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..contracts import ExecutionPlan
from ..core.bundle.artifacts import VerifiedBundle, _verify_artifact
from ..core.bundle.git_commit import require_clean_study_repo
from ..core.bundle.verify import verify_bundle
from ..core.config import ComposedConfig, compose
from ..rails.controllers import default_phase_program
from ..rails.native_episode_config import load_native_episode_config
from .native_episode_diagnostics import analyze_verified_native_episode_statistics


class NativeEpisodeSourceError(ValueError):
    """A complete native source does not match its frozen execution authority."""


@dataclass(frozen=True)
class VerifiedNativeEpisodeSource:
    bundle: VerifiedBundle
    composed: ComposedConfig
    plan: ExecutionPlan
    sample_ids: tuple[str, ...]
    phase_results: Mapping[str, Mapping[str, object]]
    output_rows: Mapping[str, Mapping[str, object]]
    phase_artifact_sha256: str
    diagnostics: Mapping[str, object]


def verify_native_episode_source(
    *,
    manifest_path: Path,
    expected_manifest_sha256: str,
    phase_artifact_path: Path,
    expected_phase_sha256: str,
    repo_root: Path,
) -> VerifiedNativeEpisodeSource:
    """Verify source identities without scoring or touching a model service.

    The supplied checkout must retain the recorded commit. Do not silently
    substitute today's fragments for a historical run's configuration.
    """
    manifest_bytes = _verify_artifact(
        {"path": str(manifest_path), "sha256": expected_manifest_sha256},
        "native source manifest",
    )
    bundle = verify_bundle(Path(manifest_path))
    manifest = bundle.manifest
    if manifest != json.loads(manifest_bytes):
        raise NativeEpisodeSourceError("native manifest changed during verification")
    if (
        manifest.get("status") != "COMPLETED"
        or bundle.attempt_state != "FINALIZED"
        or manifest.get("result_kind", "task-answer") != "task-answer"
    ):
        raise NativeEpisodeSourceError("native source must be a finalized task answer")
    commit = require_clean_study_repo(Path(repo_root))
    if commit != manifest.get("study_commit"):
        raise NativeEpisodeSourceError("native source requires its recorded clean checkout")
    metadata = manifest.get("config")
    fragments = metadata.get("fragments") if isinstance(metadata, Mapping) else None
    kinds = ("model", "dataset", "baseline", "experiment")
    if (
        not isinstance(fragments, Mapping) or set(fragments) != set(kinds)
        or any(not isinstance(fragments[key], str) for key in kinds)
    ):
        raise NativeEpisodeSourceError("native source requires exactly four config fragments")
    composed = compose(Path(repo_root), *(fragments[key] for key in kinds))
    if composed.config_hash != metadata.get("config_hash"):
        raise NativeEpisodeSourceError("native source differs from its actual composed configuration")
    values = composed.values
    policy = values.get("policy")
    if (
        values.get("arm") != manifest.get("arm")
        or values.get("scorers", []) != manifest.get("scorers")
        or values.get("result_kind", "task-answer") != "task-answer"
        or not isinstance(policy, str)
    ):
        raise NativeEpisodeSourceError("native source declarations differ from its manifest")
    program = default_phase_program(policy)
    if program.stop_rule != "native-role-episode":
        raise NativeEpisodeSourceError("native source requires the shared native role program")
    native_config = load_native_episode_config(values, program)
    plan = ExecutionPlan(**manifest["plan"]).validate()
    sample_ids = tuple(row["sample_id"] for row in bundle.outputs_rows)
    if not sample_ids or len(sample_ids) != len(set(sample_ids)) or set(sample_ids) != bundle.split_ids:
        raise NativeEpisodeSourceError("native output order must cover the complete roster once")
    raw = _verify_artifact(
        {"path": str(phase_artifact_path), "sha256": expected_phase_sha256},
        "native phase artifact", confine_to=Path(bundle.manifest_path).resolve().parent,
    )
    phases = json.loads(raw)
    if (
        not isinstance(phases, Mapping)
        or phases.get("schema") != "saea-flight-phase-summaries-v1"
        or phases.get("run_id") != plan.run_id
        or phases.get("attempt_id") != plan.attempt_id
        or phases.get("policy") != policy
        or not isinstance(phases.get("phases"), list)
        or len(phases["phases"]) != 1
    ):
        raise NativeEpisodeSourceError("native phase artifact does not bind this one system")
    summary = phases["phases"][0]
    if (
        not isinstance(summary, Mapping)
        or summary.get("controller_policy_id") != policy
        or summary.get("run_id") != plan.run_id
        or summary.get("protocol_hash") != plan.protocol_hash
        or not isinstance(summary.get("results"), list)
        or any(not isinstance(row, Mapping) for row in summary["results"])
        or tuple(row.get("sample_id") for row in summary["results"]) != sample_ids
    ):
        raise NativeEpisodeSourceError("native phase results differ from the actual ordered outputs")
    results = {row["sample_id"]: row for row in summary["results"]}
    if native_config.refresh_action is not None:
        from ..rails.native_episode_receipt import validate_native_candidate_refresh_receipt

        for row in results.values():
            validate_native_candidate_refresh_receipt(
                row["native_episode_receipt"], refresh_action=native_config.refresh_action,
                max_refreshes=native_config.max_candidate_refreshes,
                max_revisions=native_config.max_revisions,
                accept_action=native_config.actions[0], revise_action=native_config.actions[1],
                error_type=NativeEpisodeSourceError,
            )
    outputs = {row["sample_id"]: row for row in bundle.outputs_rows}
    diagnostics = analyze_verified_native_episode_statistics(
        sample_ids=sample_ids, controller_policy_id=policy,
        phase_results=results, output_rows=outputs, trace_records=bundle.trace_records,
    )
    return VerifiedNativeEpisodeSource(
        bundle, composed, plan, sample_ids, results, outputs,
        expected_phase_sha256, diagnostics,
    )
