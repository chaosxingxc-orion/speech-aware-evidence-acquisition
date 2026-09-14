"""Export source-bound TRAIN candidate-stage diagnostics without gold text.

This sidecar runs only after a finalized native task-answer source and its first
complete official score have sealed. It does not score, contact a model, alter
reward vectors, estimate tool credit, or construct a counterfactual.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..core.bundle.artifacts import _verify_artifact
from ..core.preparation import hash_stable_file, prepare_artifact
from ..data.splits import prefixed, split_identity_hash
from ..rails.hashing import content_hash
from ..rails.reward_link_io import read_verified_reward_link_artifact
from ..rails.slurp_candidate_contracts import build_slurp_candidate_contract_provider
from .native_episode_source import verify_native_episode_source
from .slurp_topn_diagnostics import ReferenceIntentRow, SourceCandidateRow
from .slurp_topn_diagnostics_cli import (
    load_authoritative_slurp_candidate_ids,
    load_verified_native_system_candidate_rows,
    load_verified_slurp_reference_intents,
)

CONFIG_SCHEMA = "saea-native-train-stage-diagnostic-config-v1"
OUTPUT_SCHEMA = "saea-native-train-stage-diagnostics-v1"
ARTIFACT_KIND = "native-train-stage-diagnostics"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_SOURCE_KEYS = frozenset(
    {
        "manifest_sha256",
        "phase_artifact_sha256",
        "diagnostic_config_sha256",
        "reward_config_sha256",
        "reward_artifact_sha256",
        "complete_score_receipt_sha256",
        "reference_binding_sha256",
        "reference_lock_sha256",
        "config_hash",
        "run_id",
        "attempt_id",
        "protocol_hash",
        "split_identity_hash",
        "candidate_projection_policy",
        "legal_candidate_inventory_sha256",
    }
)


class NativeTrainStageDiagnosticError(ValueError):
    """A TRAIN stage diagnostic source or exact-cohort join is invalid."""


def _sha(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise NativeTrainStageDiagnosticError(f"{field} must be a lowercase SHA-256")
    return value


def _pin(value: object, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
        raise NativeTrainStageDiagnosticError(f"{field} must contain path and SHA-256")
    path = value.get("path")
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise NativeTrainStageDiagnosticError(f"{field} path must be absolute")
    return {"path": path, "sha256": _sha(value.get("sha256"), f"{field} SHA-256")}


def _read_json_pin(
    value: object, field: str
) -> tuple[dict[str, str], Mapping[str, object]]:
    pin = _pin(value, field)
    try:
        raw = _verify_artifact(pin, field)
        document = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise NativeTrainStageDiagnosticError(f"cannot verify {field}: {error}") from error
    if not isinstance(document, Mapping):
        raise NativeTrainStageDiagnosticError(f"{field} must contain a JSON object")
    return pin, document


def _ratio(numerator: int, denominator: int) -> dict[str, object]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def build_native_train_stage_diagnostics(
    *,
    candidate_rows: Sequence[SourceCandidateRow],
    reference_rows: Sequence[ReferenceIntentRow],
    reward_links: Sequence[object],
    source: Mapping[str, object],
) -> dict[str, object]:
    """Join exact-cohort candidates, references, and final native correctness.

    Reference intent strings are used only for the in-memory membership test and
    are never copied into the returned document.
    """

    candidates = tuple(candidate_rows)
    references = tuple(reference_rows)
    links = tuple(reward_links)
    if not candidates:
        raise NativeTrainStageDiagnosticError("diagnostic cohort must be nonempty")
    ids = tuple(row.sample_id for row in candidates)
    if len(ids) != len(set(ids)):
        raise NativeTrainStageDiagnosticError("candidate rows contain duplicate samples")
    for row in candidates:
        if (
            not isinstance(row, SourceCandidateRow)
            or not row.candidate_ids
            or len(row.candidate_ids) > 3
            or len(row.candidate_ids) != len(set(row.candidate_ids))
            or any(not isinstance(item, str) or not item for item in row.candidate_ids)
        ):
            raise NativeTrainStageDiagnosticError(
                "each initial candidate row must contain one to three distinct intent IDs"
            )
    if set(source) != _SOURCE_KEYS:
        raise NativeTrainStageDiagnosticError("diagnostic source binding has wrong fields")
    for field in (
        "manifest_sha256",
        "phase_artifact_sha256",
        "diagnostic_config_sha256",
        "reward_config_sha256",
        "reward_artifact_sha256",
        "complete_score_receipt_sha256",
        "reference_binding_sha256",
        "reference_lock_sha256",
        "config_hash",
        "protocol_hash",
        "split_identity_hash",
        "legal_candidate_inventory_sha256",
    ):
        _sha(source.get(field), f"source {field}")
    for field in ("run_id", "attempt_id", "candidate_projection_policy"):
        if not isinstance(source.get(field), str) or not source[field]:
            raise NativeTrainStageDiagnosticError(f"source {field} must be nonempty text")
    if source["split_identity_hash"] != split_identity_hash(prefixed("slurp", ids)):
        raise NativeTrainStageDiagnosticError(
            "diagnostic source split identity differs from the ordered cohort"
        )
    reference_ids = tuple(row.sample_id for row in references)
    if reference_ids != ids or any(
        not isinstance(row, ReferenceIntentRow)
        or not isinstance(row.intent_id, str)
        or not row.intent_id
        for row in references
    ):
        raise NativeTrainStageDiagnosticError(
            "reference rows must match the exact ordered candidate cohort"
        )
    link_ids = tuple(link.source.source_sample_id for link in links)
    if link_ids != ids:
        raise NativeTrainStageDiagnosticError(
            "reward links must match the exact ordered candidate cohort"
        )
    construction_hashes = {link.construction_roster_sha256 for link in links}
    if len(construction_hashes) != 1:
        raise NativeTrainStageDiagnosticError("reward links name different construction rosters")

    samples = []
    for candidate, reference, link in zip(candidates, references, links, strict=True):
        try:
            link.validate()
            counts = link.native_score_vector["per_sample"]
            if set(counts) != {candidate.sample_id}:
                raise NativeTrainStageDiagnosticError(
                    "reward link per-sample counts name a different sample"
                )
            exact = counts[candidate.sample_id]["scenario_action_exact"]
        except (AttributeError, KeyError, TypeError, ValueError) as error:
            if isinstance(error, NativeTrainStageDiagnosticError):
                raise
            raise NativeTrainStageDiagnosticError(f"invalid native reward link: {error}") from error
        if (
            isinstance(exact, bool)
            or not isinstance(exact, (int, float))
            or not math.isfinite(exact)
            or exact not in (0, 1)
        ):
            raise NativeTrainStageDiagnosticError(
                "final intent correctness must be a binary native score"
            )
        covered = reference.intent_id in set(candidate.candidate_ids)
        correct = bool(exact)
        samples.append(
            {
                "sample_id": candidate.sample_id,
                "initial_candidate_width": len(candidate.candidate_ids),
                "gold_covered": covered,
                "final_correct": correct,
                "covered_and_correct": covered and correct,
                "covered_and_wrong": covered and not correct,
                "uncovered": not covered,
            }
        )

    covered_count = sum(row["gold_covered"] for row in samples)
    correct_count = sum(row["final_correct"] for row in samples)
    covered_correct = sum(row["covered_and_correct"] for row in samples)
    covered_wrong = sum(row["covered_and_wrong"] for row in samples)
    uncovered_count = len(samples) - covered_count
    uncovered_correct = sum(row["uncovered"] and row["final_correct"] for row in samples)
    return {
        "schema": OUTPUT_SCHEMA,
        "status": "source-verified-diagnostic",
        "source": dict(source),
        "cohort": {
            "sample_count": len(ids),
            "ordered_sample_ids_sha256": content_hash(list(ids)),
            "construction_roster_sha256": next(iter(construction_hashes)),
        },
        "semantics": {
            "candidate_stage": "initial Perception output after configured distinct projection",
            "final_correct": "official per-sample scenario_action_exact",
            "gold_or_reference_strings_exported": False,
            "conditional_accuracy_scope": "covered samples only",
            "uncovered_conditional_reward": None,
            "causal_or_counterfactual_claim": None,
        },
        "aggregate": {
            "candidate_coverage": _ratio(covered_count, len(samples)),
            "final_accuracy": _ratio(correct_count, len(samples)),
            "conditional_accuracy_given_coverage": _ratio(covered_correct, covered_count),
            "covered_and_wrong": _ratio(covered_wrong, covered_count),
            "uncovered": _ratio(uncovered_count, len(samples)),
            "correct_outside_candidate_set": _ratio(uncovered_correct, uncovered_count),
        },
        "samples": samples,
    }


def prepare_native_train_stage_diagnostics(
    *,
    config_path: Path,
    expected_config_sha256: str,
    source_repo_root: Path,
    output_path: Path,
    reference_loader,
    candidate_contract_loader=build_slurp_candidate_contract_provider,
) -> dict[str, object]:
    """Verify all post-seal sources and persist one model-free sidecar."""

    config_pin = {
        "path": str(Path(config_path).resolve()),
        "sha256": _sha(expected_config_sha256, "config SHA-256"),
    }
    _, config = _read_json_pin(config_pin, "diagnostic config")
    if (
        set(config) != {"schema", "native_source", "reward_source", "reference_source"}
        or config.get("schema") != CONFIG_SCHEMA
    ):
        raise NativeTrainStageDiagnosticError("diagnostic config has wrong fields or schema")
    native = config.get("native_source")
    reward = config.get("reward_source")
    reference = config.get("reference_source")
    if not isinstance(native, Mapping) or set(native) != {"manifest", "phase_artifact"}:
        raise NativeTrainStageDiagnosticError("native_source has wrong fields")
    if not isinstance(reward, Mapping) or set(reward) != {"config", "artifact"}:
        raise NativeTrainStageDiagnosticError("reward_source has wrong fields")
    if not isinstance(reference, Mapping):
        raise NativeTrainStageDiagnosticError("reference_source must be a mapping")
    reference_lock_pin = _pin(reference.get("lock"), "reference lock")
    manifest_pin = _pin(native["manifest"], "native manifest")
    phase_pin = _pin(native["phase_artifact"], "native phase artifact")
    try:
        verified = verify_native_episode_source(
            manifest_path=Path(manifest_pin["path"]),
            expected_manifest_sha256=manifest_pin["sha256"],
            phase_artifact_path=Path(phase_pin["path"]),
            expected_phase_sha256=phase_pin["sha256"],
            repo_root=Path(source_repo_root),
        )
    except (OSError, TypeError, ValueError) as error:
        raise NativeTrainStageDiagnosticError(f"cannot verify native source: {error}") from error
    if (
        verified.plan.carrier_lock_key != "slurp"
        or verified.plan.split_role != "discovery"
        or any(not sample_id.startswith("slurp:train:") for sample_id in verified.sample_ids)
    ):
        raise NativeTrainStageDiagnosticError("diagnostic source must be SLURP TRAIN discovery")

    reward_config_pin, reward_config = _read_json_pin(reward["config"], "reward config")
    reward_artifact_pin = _pin(reward["artifact"], "reward artifact")
    if reward_config.get("manifest") != manifest_pin:
        raise NativeTrainStageDiagnosticError("reward source names a different native manifest")
    try:
        _verify_artifact(reward_artifact_pin, "reward artifact")
        reward_links = read_verified_reward_link_artifact(
            reward_config, Path(reward_artifact_pin["path"])
        )
        legal_ids = load_authoritative_slurp_candidate_ids(
            reference, loader=candidate_contract_loader
        )
        references = load_verified_slurp_reference_intents(
            reference, verified.sample_ids, loader=reference_loader
        )
    except (OSError, TypeError, ValueError) as error:
        raise NativeTrainStageDiagnosticError(
            f"cannot verify diagnostic score/reference source: {error}"
        ) from error

    values = verified.composed.values
    try:
        maximum = values["phase_material"]["perception"]["fill_params"]["max_candidates"]
    except (KeyError, TypeError) as error:
        raise NativeTrainStageDiagnosticError(
            "native source lacks Perception candidate bounds"
        ) from error
    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= 3:
        raise NativeTrainStageDiagnosticError(
            "native Perception max_candidates must be from one to three"
        )
    candidate_binding = {
        "manifest": manifest_pin,
        "phase_artifact": phase_pin,
        "split_identity_hash": verified.plan.split_identity_hash,
        "producer_policy_id": values["policy"],
        "compact_source_phase": "perception",
        "candidate_selection_phase": "solver",
        "candidate_count": maximum,
        "candidate_count_range": [1, maximum],
    }
    try:
        candidates, _branches, candidate_metadata = load_verified_native_system_candidate_rows(
            candidate_binding,
            verified.bundle,
            verified.sample_ids,
            legal_ids=legal_ids,
        )
    except (OSError, TypeError, ValueError) as error:
        raise NativeTrainStageDiagnosticError(
            f"cannot verify initial candidates: {error}"
        ) from error

    source = {
        "manifest_sha256": manifest_pin["sha256"],
        "phase_artifact_sha256": phase_pin["sha256"],
        "diagnostic_config_sha256": config_pin["sha256"],
        "reward_config_sha256": reward_config_pin["sha256"],
        "reward_artifact_sha256": reward_artifact_pin["sha256"],
        "complete_score_receipt_sha256": reward_config["complete_score_receipt"]["sha256"],
        "reference_binding_sha256": content_hash(reference),
        "reference_lock_sha256": reference_lock_pin["sha256"],
        "config_hash": verified.composed.config_hash,
        "run_id": verified.plan.run_id,
        "attempt_id": verified.plan.attempt_id,
        "protocol_hash": verified.plan.protocol_hash,
        "split_identity_hash": verified.plan.split_identity_hash,
        "candidate_projection_policy": candidate_metadata["projection_policy"],
        "legal_candidate_inventory_sha256": candidate_metadata[
            "legal_candidate_inventory_sha256"
        ],
    }
    document = build_native_train_stage_diagnostics(
        candidate_rows=candidates,
        reference_rows=references,
        reward_links=reward_links,
        source=source,
    )
    inputs = {
        "config_sha256": config_pin["sha256"],
        "manifest_sha256": manifest_pin["sha256"],
        "phase_artifact_sha256": phase_pin["sha256"],
        "reward_config_sha256": reward_config_pin["sha256"],
        "reward_artifact_sha256": reward_artifact_pin["sha256"],
        "document_sha256": content_hash(document),
        "implementation_sha256": hash_stable_file(
            Path(__file__), "stage diagnostic implementation"
        )[1],
    }
    try:
        return prepare_artifact(
            Path(output_path),
            kind=ARTIFACT_KIND,
            inputs=inputs,
            producer=lambda: document,
            contact_class="model-free",
        )
    except (OSError, TypeError, ValueError) as error:
        raise NativeTrainStageDiagnosticError(
            f"cannot persist stage diagnostics: {error}"
        ) from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Export source-bound native TRAIN stage diagnostics"
    )
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--source-repo-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    from ..data.slurp import load_slurp_split

    args = _parser().parse_args(argv)
    receipt = prepare_native_train_stage_diagnostics(
        config_path=args.config,
        expected_config_sha256=args.config_sha256,
        source_repo_root=args.source_repo_root,
        output_path=args.output,
        reference_loader=load_slurp_split,
    )
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
