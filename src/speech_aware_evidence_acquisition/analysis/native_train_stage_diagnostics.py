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
from ..rails.slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS,
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
)
from .native_candidate_stage_projections import (
    PROJECTION_CONFIG_SCHEMA,
    PROJECTION_POLICY_ID,
    NativeCandidateStagePair,
    project_verified_native_candidate_stages,
)
from .native_episode_source import verify_native_episode_source
from .native_intent_support import (
    build_initial_intent_support_diagnostics,
    validate_initial_intent_support_spec,
)
from .slurp_topn_diagnostics import ReferenceIntentRow, SourceCandidateRow
from .slurp_topn_diagnostics_cli import (
    load_authoritative_slurp_candidate_ids,
    load_verified_native_system_candidate_rows,
    load_verified_slurp_reference_intents,
)

CONFIG_SCHEMA = "saea-native-train-stage-diagnostic-config-v1"
OUTPUT_SCHEMA = "saea-native-train-stage-diagnostics-v1"
STAGE_OUTPUT_SCHEMA = "saea-native-train-candidate-stage-diagnostics-v2"
ARTIFACT_KIND = "native-train-stage-diagnostics"
STAGE_ARTIFACT_KIND = "native-train-candidate-stage-diagnostics"
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
    max_candidates: int = 3,
    _availability: Sequence[bool] | None = None,
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
    if (
        isinstance(max_candidates, bool)
        or not isinstance(max_candidates, int)
        or max_candidates < 1
    ):
        raise NativeTrainStageDiagnosticError(
            "max_candidates must be a positive integer"
        )
    ids = tuple(row.sample_id for row in candidates)
    availability = (
        tuple(True for _ in candidates)
        if _availability is None else tuple(_availability)
    )
    if len(availability) != len(candidates) or any(
        not isinstance(item, bool) for item in availability
    ):
        raise NativeTrainStageDiagnosticError("candidate availability is malformed")
    if len(ids) != len(set(ids)):
        raise NativeTrainStageDiagnosticError("candidate rows contain duplicate samples")
    for row, available in zip(candidates, availability, strict=True):
        if (
            not isinstance(row, SourceCandidateRow)
            or (available and not row.candidate_ids)
            or (not available and bool(row.candidate_ids))
            or len(row.candidate_ids) > max_candidates
            or len(row.candidate_ids) != len(set(row.candidate_ids))
            or any(not isinstance(item, str) or not item for item in row.candidate_ids)
        ):
            raise NativeTrainStageDiagnosticError(
                "each initial candidate row must contain at most "
                f"{max_candidates} distinct intent IDs"
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
    for candidate, reference, link, available in zip(
        candidates, references, links, availability, strict=True
    ):
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
        covered = available and reference.intent_id in set(candidate.candidate_ids)
        correct = bool(exact)
        samples.append(
            {
                "sample_id": candidate.sample_id,
                "initial_candidate_width": (
                    len(candidate.candidate_ids) if available else None
                ),
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


def build_native_train_candidate_stage_diagnostics(
    *,
    stage_pairs: Sequence[NativeCandidateStagePair],
    reference_rows: Sequence[ReferenceIntentRow],
    reward_links: Sequence[object],
    source: Mapping[str, object],
    max_candidates: int = 3,
) -> dict[str, object]:
    """Build numeric C0/C1 coverage diagnostics from verified stage pairs."""

    pairs = tuple(stage_pairs)
    if not pairs or any(not isinstance(pair, NativeCandidateStagePair) for pair in pairs):
        raise NativeTrainStageDiagnosticError("candidate stage pairs are malformed or empty")
    pair_ids = tuple(pair.sample_id for pair in pairs)
    if len(pair_ids) != len(set(pair_ids)):
        raise NativeTrainStageDiagnosticError("candidate stage pairs contain duplicate samples")
    if any(
        pair.c0 is None and pair.c1 is not None
        or (
            pair.c0 is not None and pair.c1 is not None
            and pair.c0.visit_index > pair.c1.visit_index
        )
        or type(pair.refresh_executed) is not bool
        or type(pair.refresh_after_delivered_solver) is not bool
        or pair.refresh_executed != (
            pair.refresh_used_by_delivered_solver or pair.refresh_after_delivered_solver
        )
        or (
            pair.refresh_after_delivered_solver
            and (pair.c0 is None or pair.c1 is None)
        )
        or (
            not pair.refresh_used_by_delivered_solver
            and pair.c0 is not None and pair.c1 is not None
            and pair.c0 != pair.c1
        )
        for pair in pairs
    ):
        raise NativeTrainStageDiagnosticError(
            "candidate stage pairs have inconsistent visit or refresh semantics"
        )
    c0_document = build_native_train_stage_diagnostics(
        candidate_rows=tuple(
            SourceCandidateRow(
                pair.sample_id, () if pair.c0 is None else pair.c0.candidate_ids
            )
            for pair in pairs
        ),
        reference_rows=reference_rows,
        reward_links=reward_links,
        source=source,
        max_candidates=max_candidates,
        _availability=tuple(pair.c0 is not None for pair in pairs),
    )
    c1_document = build_native_train_stage_diagnostics(
        candidate_rows=tuple(
            SourceCandidateRow(
                pair.sample_id, () if pair.c1 is None else pair.c1.candidate_ids
            )
            for pair in pairs
        ),
        reference_rows=reference_rows,
        reward_links=reward_links,
        source=source,
        max_candidates=max_candidates,
        _availability=tuple(pair.c1 is not None for pair in pairs),
    )
    samples = []
    for pair, c0, c1 in zip(
        pairs, c0_document["samples"], c1_document["samples"], strict=True
    ):
        c0_available = pair.c0 is not None
        c1_available = pair.c1 is not None
        transition_available = c0_available and c1_available
        c0_covered = bool(c0["gold_covered"])
        c1_covered = bool(c1["gold_covered"])
        correct = bool(c1["final_correct"])
        samples.append(
            {
                "sample_id": pair.sample_id,
                "c0": None if pair.c0 is None else pair.c0.diagnostic_json(),
                "c1": None if pair.c1 is None else pair.c1.diagnostic_json(),
                "c0_available": c0_available,
                "c1_available": c1_available,
                "transition_available": transition_available,
                "refresh_executed": pair.refresh_executed,
                "refresh_used_by_delivered_solver": pair.refresh_used_by_delivered_solver,
                "refresh_after_delivered_solver": pair.refresh_after_delivered_solver,
                "initial_covered": c0_covered,
                "pre_final_covered": c1_covered,
                "recovered": (
                    not c0_covered and c1_covered if transition_available else None
                ),
                "lost": (
                    c0_covered and not c1_covered if transition_available else None
                ),
                "stable_covered": (
                    c0_covered and c1_covered if transition_available else None
                ),
                "stable_uncovered": (
                    not c0_covered and not c1_covered if transition_available else None
                ),
                "final_correct": correct,
                "correct_outside_c1": (
                    correct and not c1_covered if c1_available else None
                ),
            }
        )

    total = len(samples)
    c0_available = sum(row["c0_available"] for row in samples)
    c1_available = sum(row["c1_available"] for row in samples)
    transition_eligible = sum(row["transition_available"] for row in samples)
    initial_covered = sum(row["initial_covered"] for row in samples)
    pre_final_covered = sum(row["pre_final_covered"] for row in samples)
    stable_covered = sum(row["stable_covered"] is True for row in samples)
    final_correct = sum(row["final_correct"] for row in samples)
    return {
        "schema": STAGE_OUTPUT_SCHEMA,
        "status": "source-verified-diagnostic",
        "source": dict(source),
        "cohort": dict(c0_document["cohort"]),
        "stage_availability": {
            "c0_available_count": c0_available,
            "c0_unavailable_count": total - c0_available,
            "c1_available_count": c1_available,
            "c1_unavailable_count": total - c1_available,
            "transition_eligible_count": transition_eligible,
            "transition_unavailable_count": total - transition_eligible,
        },
        "projection": {
            "schema": PROJECTION_CONFIG_SCHEMA,
            "policy_id": PROJECTION_POLICY_ID,
            "candidate_projection_policy": source["candidate_projection_policy"],
            "legal_candidate_inventory_sha256": source[
                "legal_candidate_inventory_sha256"
            ],
        },
        "semantics": {
            "c0": "first actual Perception visit",
            "c1": "last actual Perception before the delivered final Solver visit",
            "unavailable_stage_coverage": (
                "Unconditional full-roster coverage counts an unavailable stage as not covered."
            ),
            "refresh_executed": "At least two Perception visits completed.",
            "refresh_used_by_delivered_solver": (
                "C1 differs from C0 by verified visit, before the delivered Solver."
            ),
            "refresh_after_delivered_solver": (
                "Later completed Perception is counted as work but supplies no C1 credit."
            ),
            "no_refresh": "C0 and C1 retain the same verified source when both exist",
            "final_correct": "official per-sample scenario_action_exact",
            "gold_or_reference_strings_exported": False,
            "conditional_accuracy_scope": "the named covered set only",
            "causal_or_counterfactual_claim": None,
        },
        "aggregate": {
            "completed_refreshes": _ratio(
                sum(row["refresh_executed"] for row in samples), total
            ),
            "refreshes_used_by_delivered_solver": _ratio(
                sum(row["refresh_used_by_delivered_solver"] for row in samples), total
            ),
            "refreshes_after_delivered_solver": _ratio(
                sum(row["refresh_after_delivered_solver"] for row in samples), total
            ),
            "initial_candidate_coverage": _ratio(initial_covered, total),
            "pre_final_candidate_coverage": _ratio(pre_final_covered, total),
            "initial_candidate_coverage_available_stage": _ratio(
                initial_covered, c0_available
            ),
            "pre_final_candidate_coverage_available_stage": _ratio(
                pre_final_covered, c1_available
            ),
            "recovered": _ratio(
                sum(row["recovered"] is True for row in samples), transition_eligible
            ),
            "lost": _ratio(
                sum(row["lost"] is True for row in samples), transition_eligible
            ),
            "stable_covered": _ratio(stable_covered, transition_eligible),
            "stable_uncovered": _ratio(
                sum(row["stable_uncovered"] is True for row in samples),
                transition_eligible,
            ),
            "final_accuracy": _ratio(final_correct, total),
            "conditional_accuracy_given_initial_coverage": _ratio(
                sum(row["initial_covered"] and row["final_correct"] for row in samples),
                initial_covered,
            ),
            "conditional_accuracy_given_pre_final_coverage": _ratio(
                sum(
                    row["pre_final_covered"] and row["final_correct"]
                    for row in samples
                ),
                pre_final_covered,
            ),
            "common_covered_final_accuracy": _ratio(
                sum(
                    row["stable_covered"] is True and row["final_correct"]
                    for row in samples
                ),
                stable_covered,
            ),
            "correct_answers_outside_c1": _ratio(
                sum(row["correct_outside_c1"] is True for row in samples),
                c1_available - pre_final_covered,
            ),
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
    legacy_fields = {"schema", "native_source", "reward_source", "reference_source"}
    optional_fields = {"candidate_stage_projection", "initial_intent_support_projection"}
    if not legacy_fields <= set(config) or set(config) - legacy_fields - optional_fields or (
        config.get("schema") != CONFIG_SCHEMA
    ):
        raise NativeTrainStageDiagnosticError("diagnostic config has wrong fields or schema")
    stage_projection_enabled = "candidate_stage_projection" in config
    stage_projection = config.get("candidate_stage_projection")
    if stage_projection_enabled and (
        not isinstance(stage_projection, Mapping)
        or set(stage_projection) != {
            "schema",
            "policy_id",
            "candidate_projection_policy",
        }
        or stage_projection.get("schema") != PROJECTION_CONFIG_SCHEMA
        or stage_projection.get("policy_id") != PROJECTION_POLICY_ID
        or stage_projection.get("candidate_projection_policy")
        not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS
    ):
        raise NativeTrainStageDiagnosticError(
            "candidate_stage_projection contract is invalid"
        )
    support_enabled = "initial_intent_support_projection" in config
    support_spec = config.get("initial_intent_support_projection")
    if support_enabled:
        if not stage_projection_enabled:
            raise NativeTrainStageDiagnosticError(
                "initial intent support requires candidate_stage_projection"
            )
        try:
            validate_initial_intent_support_spec(support_spec)
        except ValueError as error:
            raise NativeTrainStageDiagnosticError(str(error)) from error
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
    if (
        isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or maximum < 1
        or (
            maximum > 3
            and (
                maximum > len(legal_ids)
                or not stage_projection_enabled
                or stage_projection["candidate_projection_policy"]
                != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
            )
        )
    ):
        raise NativeTrainStageDiagnosticError(
            "native Perception max_candidates must fit the legal inventory and "
            "use the configurable projection above three"
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
    stage_pairs = None
    try:
        if not stage_projection_enabled:
            candidates, _branches, candidate_metadata = (
                load_verified_native_system_candidate_rows(
                    candidate_binding,
                    verified.bundle,
                    verified.sample_ids,
                    legal_ids=legal_ids,
                )
            )
        else:
            stage_pairs = project_verified_native_candidate_stages(
                verified,
                legal_candidate_ids=legal_ids,
                max_candidates=maximum,
                projection_policy=stage_projection["candidate_projection_policy"],
            )
            candidate_metadata = {
                "projection_policy": stage_projection[
                    "candidate_projection_policy"
                ],
                "legal_candidate_inventory_sha256": content_hash(
                    {"candidate_ids": sorted(legal_ids)}
                ),
            }
    except (OSError, TypeError, ValueError) as error:
        source_label = (
            "initial candidates" if not stage_projection_enabled else "candidate stages"
        )
        raise NativeTrainStageDiagnosticError(
            f"cannot verify {source_label}: {error}"
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
    document = (
        build_native_train_stage_diagnostics(
            candidate_rows=candidates,
            reference_rows=references,
            reward_links=reward_links,
            source=source,
            max_candidates=maximum,
        )
        if not stage_projection_enabled
        else build_native_train_candidate_stage_diagnostics(
            stage_pairs=stage_pairs,
            reference_rows=references,
            reward_links=reward_links,
            source=source,
            max_candidates=maximum,
        )
    )
    if support_enabled:
        try:
            document["initial_intent_support"] = build_initial_intent_support_diagnostics(
                source=verified, stage_pairs=stage_pairs, reference_rows=references,
                legal_candidate_ids=legal_ids, specification=support_spec,
            )
        except (TypeError, ValueError) as error:
            raise NativeTrainStageDiagnosticError(
                f"cannot verify initial intent support: {error}"
            ) from error
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
    if support_enabled:
        inputs["support_implementation_sha256"] = hash_stable_file(
            Path(__file__).with_name("native_intent_support.py"),
            "initial intent support implementation",
        )[1]
    try:
        return prepare_artifact(
            Path(output_path),
            kind=(
                ARTIFACT_KIND
                if not stage_projection_enabled
                else STAGE_ARTIFACT_KIND
            ),
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
