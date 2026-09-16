"""Compare complete native SLURP candidate arms through shared offline APIs.

Preserve unavailable Perception and malformed final deliveries on the full roster.
Consume saved official scores; never invoke a scorer, model, tool, or runtime.
This diagnostic sidecar does not replace the registered full-task comparison.
"""
from __future__ import annotations

import argparse
import math
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..core.preparation import hash_stable_file, prepare_artifact
from ..core.scoring_receipt import SavedScoreReceiptRef, verify_complete_score_receipt
from ..data.slurp import load_slurp_split
from ..rails.hashing import content_hash
from ..rails.slurp_candidate_contracts import build_slurp_candidate_contract_provider
from ..reproduction.slurp_scoring import parse_slu_response
from .native_candidate_stage_projections import project_verified_native_candidate_stages
from .native_episode_source import verify_native_episode_source
from .null_calibration_cli import pinned_json
from .pooled_ratio_compare import compare_pooled_ratios
from .slurp_topn_diagnostics_cli import (
    load_authoritative_slurp_candidate_ids,
    load_verified_slurp_reference_records,
)

CONFIG_SCHEMA = "saea-native-candidate-comparison-config-v1"
RELEASE_SCHEMA = "saea-native-candidate-comparison-quality-release-v1"
OUTPUT_SCHEMA = "saea-native-candidate-comparison-v1"


class NativeCandidateComparisonError(ValueError):
    """The complete paired sources or their offline joins are inconsistent."""


def _read(pin: object, label: str):
    if (
        not isinstance(pin, Mapping) or set(pin) != {"path", "sha256"}
        or not isinstance(pin["path"], str) or not Path(pin["path"]).is_absolute()
        or not isinstance(pin["sha256"], str) or len(pin["sha256"]) != 64
    ):
        raise NativeCandidateComparisonError(f"{label} requires an absolute path/hash pin")
    try:
        return pinned_json(pin)
    except (OSError, TypeError, ValueError, KeyError) as error:
        raise NativeCandidateComparisonError(f"cannot read {label}: {error}") from error


def _projection_limits(source, legal_ids, projection_policy):
    try:
        values = source.composed.values
        maximum = values["phase_material"]["perception"]["fill_params"]["max_candidates"]
        supplies = [
            store["candidate_supply"]["solver"]
            for store in values["knowledge_stores"].values()
            if "solver" in store.get("candidate_supply", {})
        ]
        policies = {supply["projection_policy"] for supply in supplies}
    except (KeyError, TypeError, AttributeError) as error:
        raise NativeCandidateComparisonError("candidate projection config is incomplete") from error
    if (
        type(maximum) is not int or not 1 <= maximum <= len(legal_ids)
        or not isinstance(projection_policy, str) or policies != {projection_policy}
    ):
        raise NativeCandidateComparisonError("candidate projection differs from actual supply")
    return maximum


def project_candidate_decision_rows(
    source, *, reference_records, official_rows, legal_ids, projection_policy,
):
    """Project verified initial candidates and actual final delivery without gold export."""
    maximum = _projection_limits(source, legal_ids, projection_policy)
    ids = tuple(source.sample_ids)
    refs, scores = tuple(reference_records), tuple(official_rows)
    if (
        not ids or len(ids) != len(set(ids))
        or tuple(ref.sample_id for ref in refs) != ids
        or tuple(row.get("sample_id") for row in scores) != ids
        or set(source.output_rows) != set(ids)
    ):
        raise NativeCandidateComparisonError("source/reference/score ordered roster differs")
    try:
        pairs = project_verified_native_candidate_stages(
            source, legal_candidate_ids=legal_ids,
            max_candidates=maximum, projection_policy=projection_policy,
        )
    except (TypeError, ValueError) as error:
        raise NativeCandidateComparisonError(f"cannot project initial candidates: {error}") from error
    if tuple(pair.sample_id for pair in pairs) != ids:
        raise NativeCandidateComparisonError("candidate-stage ordered roster differs")
    rows = []
    for sid, pair, ref, saved in zip(ids, pairs, refs, scores, strict=True):
        output = source.output_rows[sid]
        if output.get("sample_id") != sid or not isinstance(output.get("text"), str):
            raise NativeCandidateComparisonError("final delivery row lacks exact sample/text")
        scenario, action, _, parsed = parse_slu_response(output["text"])
        final_id = (
            f"{scenario}_{action}"
            if parsed and scenario and action else None
        )
        exact = saved.get("scenario_action_exact")
        measured = bool(scenario == ref.scenario and action == ref.action)
        if (
            isinstance(exact, bool) or not isinstance(exact, (float, int))
            or not math.isfinite(exact) or exact not in (0, 1)
            or bool(exact) != measured
        ):
            raise NativeCandidateComparisonError("saved official intent differs from final delivery")
        candidates = () if pair.c0 is None else tuple(pair.c0.candidate_ids)
        available = pair.c0 is not None
        rows.append({
            "sample_id": sid,
            "candidate_available": available,
            "candidate_width": len(candidates) if available else None,
            "gold_covered": available and ref.intent in candidates,
            "final_correct": bool(exact),
            "final_in_candidates": (
                final_id in candidates if available and final_id is not None else None
            ),
        })
    return tuple(rows)


def _ordered_score_rows(document, ids):
    try:
        rows = document["scores"]["slurp-slu-official-train"]["per_sample"]
        by_id = {row["sample_id"]: row for row in rows}
    except (KeyError, TypeError) as error:
        raise NativeCandidateComparisonError("saved official per-sample rows are unavailable") from error
    if len(by_id) != len(rows) or set(by_id) != set(ids):
        raise NativeCandidateComparisonError("saved official score roster differs")
    return tuple(by_id[sid] for sid in ids)


def _load_arm(binding, reference_source):
    manifest = _read(binding["manifest"], "finalized manifest")
    if not isinstance(manifest, Mapping) or manifest.get("status") != "COMPLETED":
        raise NativeCandidateComparisonError("only complete manifests may be inspected")
    source = verify_native_episode_source(
        manifest_path=Path(binding["manifest"]["path"]),
        expected_manifest_sha256=binding["manifest"]["sha256"],
        phase_artifact_path=Path(binding["phase_artifact"]["path"]),
        expected_phase_sha256=binding["phase_artifact"]["sha256"],
        repo_root=Path(binding["source_repo_root"]),
    )
    if (
        source.plan.carrier_lock_key != "slurp" or source.plan.split_role != "discovery"
        or any(not sid.startswith("slurp:train:") for sid in source.sample_ids)
    ):
        raise NativeCandidateComparisonError("comparison requires SLURP TRAIN discovery sources")
    receipt_pin = binding["complete_score_receipt"]
    receipt = verify_complete_score_receipt(SavedScoreReceiptRef(
        cell_id=source.plan.attempt_id,
        path=Path(receipt_pin["path"]), sha256=receipt_pin["sha256"],
    ), source.bundle)
    score_document = _read(receipt["score_result"], "saved official score")
    refs = load_verified_slurp_reference_records(
        reference_source, source.sample_ids, loader=load_slurp_split,
    )
    legal = load_authoritative_slurp_candidate_ids(
        reference_source, loader=build_slurp_candidate_contract_provider,
    )
    rows = project_candidate_decision_rows(
        source, reference_records=refs,
        official_rows=_ordered_score_rows(score_document, source.sample_ids),
        legal_ids=legal, projection_policy=binding["projection_policy"],
    )
    return rows, {
        **dict(binding),
        "official_score_result": dict(receipt["score_result"]),
        "run_id": source.plan.run_id,
        "attempt_id": source.plan.attempt_id,
        "config_hash": source.composed.config_hash,
        "protocol_hash": source.plan.protocol_hash,
        "split_identity_hash": source.plan.split_identity_hash,
        "initial_candidate_maximum": _projection_limits(source, legal, binding["projection_policy"]),
    }


def _configuration(config, release):
    fields = {
        "schema", "execution_profile", "quality_release", "arms",
        "reference_source", "metadata", "bootstrap",
    }
    if (
        not isinstance(config, Mapping) or set(config) != fields
        or config["schema"] != CONFIG_SCHEMA
        or config["execution_profile"] != "model-free-check"
    ):
        raise NativeCandidateComparisonError("comparison config fields/profile/schema are invalid")
    arms = config["arms"]
    if not isinstance(arms, Mapping) or set(arms) != {"left", "right"}:
        raise NativeCandidateComparisonError("exact left/right arms are required")
    arm_fields = {
        "manifest", "phase_artifact", "source_repo_root",
        "projection_policy", "complete_score_receipt",
    }
    for binding in arms.values():
        if not isinstance(binding, Mapping) or set(binding) != arm_fields:
            raise NativeCandidateComparisonError("arm binding fields are invalid")
    if (
        not isinstance(release, Mapping) or release.get("schema") != RELEASE_SCHEMA
        or release.get("status") != "COMPLETE_SOURCES_RELEASED_FOR_REGISTERED_ANALYSIS"
        or release.get("manifests") != {
            side: arms[side]["manifest"] for side in ("left", "right")
        }
    ):
        raise NativeCandidateComparisonError("quality release does not bind the exact paired manifests")
    bootstrap = config["bootstrap"]
    if (
        not isinstance(bootstrap, Mapping)
        or set(bootstrap) != {"seed", "n_replicates", "ci_level"}
        or type(bootstrap["seed"]) is not int
        or type(bootstrap["n_replicates"]) is not int
        or bootstrap["n_replicates"] < 1
        or isinstance(bootstrap["ci_level"], bool)
        or not isinstance(bootstrap["ci_level"], (float, int))
        or not 0 < bootstrap["ci_level"] < 1
    ):
        raise NativeCandidateComparisonError("bootstrap settings are invalid")


def run(config_path: Path, *, expected_config_sha256: str, output_path: Path):
    config_pin = {"path": str(Path(config_path).resolve()), "sha256": expected_config_sha256}
    config = _read(config_pin, "comparison config")
    if not isinstance(config, Mapping):
        raise NativeCandidateComparisonError("comparison config must be an object")
    release = _read(config.get("quality_release"), "quality release")
    _configuration(config, release)
    # Validate release before any task-output or reference access.
    left, left_source = _load_arm(config["arms"]["left"], config["reference_source"])
    right, right_source = _load_arm(config["arms"]["right"], config["reference_source"])
    ids = tuple(row["sample_id"] for row in left)
    metadata_document = _read(config["metadata"], "released speaker/scenario metadata")
    try:
        metadata_rows = metadata_document["rows"]
        by_id = {row["sample_id"]: row for row in metadata_rows}
    except (KeyError, TypeError) as error:
        raise NativeCandidateComparisonError("metadata rows are unavailable") from error
    if len(by_id) != len(metadata_rows) or set(by_id) != set(ids):
        raise NativeCandidateComparisonError("metadata roster differs")
    from .candidate_decision_comparison import CandidateDecisionRow, compare_candidate_decisions

    report = compare_candidate_decisions(
        tuple(CandidateDecisionRow(**row) for row in left),
        tuple(CandidateDecisionRow(**row) for row in right),
        metadata=tuple(by_id[sid] for sid in ids),
    )
    metrics = {
        name: {
            "numerator_field": f"{name}_numerator",
            "denominator_field": f"{name}_denominator",
            "direction": "higher", "zero_denominator": "unavailable",
        }
        for name in ("coverage", "own_covered_final", "common_covered_final", "final_accuracy")
    }
    uncertainty = compare_pooled_ratios(
        report["ratio_rows"]["left"], report["ratio_rows"]["right"], by_id,
        metrics, groupings={"scenario": "scenario"}, cluster_field="speaker",
        grouping_resampling="whole-cluster", **config["bootstrap"],
    )
    document = {
        "schema": OUTPUT_SCHEMA,
        "source": {"config": config_pin, "quality_release": config["quality_release"],
                   "metadata": config["metadata"], "reference_binding_sha256": content_hash(config["reference_source"]),
                   "left": left_source, "right": right_source},
        "semantics": {
            "candidate_stage": "initial Perception; membership is against this initial set",
            "unavailable": "retain every row; unavailable candidate coverage is false",
            "official_scoring": "reuse saved official intent fields; no scorer invocation",
            "decision": "diagnostic only; use registered complete-task comparison for advancement",
            "new_model_tool_scorer_contacts": 0,
        },
        "comparison": report,
        "uncertainty": uncertainty,
        "bootstrap": {**config["bootstrap"], "cluster_field": "speaker",
                      "grouping_resampling": "whole-cluster"},
    }
    return prepare_artifact(
        Path(output_path), kind="native-candidate-comparison",
        inputs={
            "config_sha256": expected_config_sha256,
            "document_sha256": content_hash(document),
            "implementation_sha256": hash_stable_file(Path(__file__), "candidate comparison orchestration")[1],
            "comparison_implementation_sha256": hash_stable_file(
                Path(__file__).with_name("candidate_decision_comparison.py"), "candidate comparison"
            )[1],
        },
        producer=lambda: document, contact_class="model-free",
    )


def main(argv: Sequence[str] | None = None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = run(args.config, expected_config_sha256=args.config_sha256, output_path=args.output)
    import json
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
