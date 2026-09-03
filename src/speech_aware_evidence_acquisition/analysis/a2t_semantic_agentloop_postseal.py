"""Pure post-seal analysis for a future 104-row Audio2Tool semantic flight.

This module accepts already-produced official scorer payloads and sealed
retrieval diagnostics.  It does not open a run bundle, call a scorer, contact
a model, make a network request, or perform runtime evidence selection.  The
only authorized scorer path remains ``core.scoring_batch``: one complete
manifest in one official scorer process.  OBS is a complete manifest for
auditability, but it is not a tool-call scoring job.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from math import comb, isfinite
from pathlib import Path
from typing import Mapping, Sequence

from ..core.scoring_batch import ScoreJob
from .bootstrap import paired_cluster_bootstrap


ROW_COUNT = 104
RESULT_SCHEMA = "saea-a2t-semantic-agentloop-postseal-104-v1"
OFFICIAL_SCORER = "a2t-toolcall"
DIRECT_M0 = "direct_m0"
OBS_SEMANTIC_RETRIEVAL = "obs_semantic_retrieval"
TRANSCRIPT_TOP16_USE = "transcript_top16_use"
MODEL_QUERY_TOP16_USE = "model_query_top16_use"
RRF_FUSED_TOP16_USE = "rrf_fused_top16_use"
SAME_STRATUM_SHUFFLED_FUSED_USE = "same_stratum_shuffled_fused_use"
ARM_ORDER = (
    DIRECT_M0,
    OBS_SEMANTIC_RETRIEVAL,
    TRANSCRIPT_TOP16_USE,
    MODEL_QUERY_TOP16_USE,
    RRF_FUSED_TOP16_USE,
    SAME_STRATUM_SHUFFLED_FUSED_USE,
)
SCORED_ARM_ORDER = (
    DIRECT_M0,
    TRANSCRIPT_TOP16_USE,
    MODEL_QUERY_TOP16_USE,
    RRF_FUSED_TOP16_USE,
    SAME_STRATUM_SHUFFLED_FUSED_USE,
)
RETRIEVAL_CONDITIONS = ("transcript", "retrieval_query", "fused")


class AnalysisError(ValueError):
    """A post-seal flight descriptor, score payload, or diagnostic is invalid."""


@dataclass(frozen=True)
class RetrievalDiagnosticSample:
    """One sealed OBS/retrieval result plus post-seal required identities.

    The three ranking maps are intentionally supplied together so that the
    transcript-only, main-model-query-only, and fused full-ranking ablation
    always has the same 104-row denominator. Ordered-call-skeleton and
    action-set fields are optional trace artifacts; the analysis marks their
    ceilings unavailable unless complete trace coverage is supplied.
    """

    sample_id: str
    tier: str
    retrieval_sealed: bool
    required_tool_ids: Sequence[str]
    ranked_tool_ids: Mapping[str, Sequence[str]]
    required_ordered_call_skeleton: Sequence[str] | None = None
    gold_calls: Sequence[Mapping[str, object]] | None = None
    ranked_ordered_call_skeletons: Mapping[str, Sequence[str]] | None = None
    proposed_action_sets: Mapping[str, Sequence[Mapping[str, object]]] | None = None


def _nonempty_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise AnalysisError(f"{label} must be non-empty text")
    return value


def _finite_unit(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AnalysisError(f"{label} must be a finite score")
    result = float(value)
    if not isfinite(result) or not 0.0 <= result <= 1.0:
        raise AnalysisError(f"{label} must be within [0, 1]")
    return result


def _sequence_of_unique_text(
    value: object, label: str, *, allow_empty: bool
) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise AnalysisError(f"{label} must be a sequence")
    result = tuple(value)
    if not allow_empty and not result:
        raise AnalysisError(f"{label} must be non-empty")
    if any(not isinstance(item, str) or not item for item in result):
        raise AnalysisError(f"{label} must contain non-empty text")
    if len(set(result)) != len(result):
        raise AnalysisError(f"{label} contains duplicate identities")
    return result


def _call_identity(call: Mapping[str, object], label: str) -> tuple[object, object]:
    if set(call) != {"name", "arguments"}:
        raise AnalysisError(f"{label} must have exactly name and arguments")
    name = _nonempty_text(call["name"], f"{label}.name")
    arguments = call["arguments"]
    if not isinstance(arguments, Mapping):
        raise AnalysisError(f"{label}.arguments must be an object")
    return (name, _json_identity(arguments, f"{label}.arguments"))


def _json_identity(value: object, label: str) -> object:
    if value is None:
        return ("null",)
    if isinstance(value, bool):
        return ("boolean", value)
    if type(value) is int:
        return ("integer", value)
    if type(value) is float:
        if not isfinite(value):
            raise AnalysisError(f"{label} contains a non-finite number")
        return ("number", value.hex())
    if isinstance(value, str):
        return ("string", value)
    if isinstance(value, list):
        return ("array", tuple(_json_identity(item, label) for item in value))
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise AnalysisError(f"{label} contains a non-text key")
        return (
            "object",
            tuple(
                sorted(
                    (key, _json_identity(item, f"{label}.{key}"))
                    for key, item in value.items()
                )
            ),
        )
    raise AnalysisError(f"{label} contains a value outside JSON")


def _validate_manifest_descriptors(
    manifests: Mapping[str, Mapping[str, object]],
) -> Mapping[str, Path]:
    if not isinstance(manifests, Mapping) or set(manifests) != set(ARM_ORDER):
        raise AnalysisError(
            "manifests must describe exactly the six future flight arms"
        )
    resolved: dict[str, Path] = {}
    for arm in ARM_ORDER:
        descriptor = manifests[arm]
        if not isinstance(descriptor, Mapping) or set(descriptor) != {
            "manifest",
            "complete_rows",
        }:
            raise AnalysisError(
                f"{arm} descriptor must contain only manifest and complete_rows"
            )
        manifest = _nonempty_text(descriptor["manifest"], f"{arm}.manifest")
        if not manifest.endswith(".run-manifest.json"):
            raise AnalysisError(f"{arm}.manifest must be a complete run-manifest.json")
        rows = descriptor["complete_rows"]
        if type(rows) is not int or rows != ROW_COUNT:
            raise AnalysisError(f"{arm} must contain exactly {ROW_COUNT} complete rows")
        resolved[arm] = Path(manifest).resolve()
    if len(set(resolved.values())) != len(resolved):
        raise AnalysisError("the six future flight manifests must be distinct")
    return resolved


def build_official_score_jobs(
    manifests: Mapping[str, Mapping[str, object]],
) -> tuple[ScoreJob, ...]:
    """Return five whole-manifest official scorer jobs, never OBS or shards.

    Callers submit this exact tuple to ``run_score_batch(..., max_workers=4,
    include_per_sample=True)``.  The core scheduler starts one process for
    each complete manifest and refuses shard aggregation independently.
    """

    paths = _validate_manifest_descriptors(manifests)
    return (
        ScoreJob("direct-m0", paths[DIRECT_M0]),
        ScoreJob("transcript-top16-use", paths[TRANSCRIPT_TOP16_USE]),
        ScoreJob("model-query-top16-use", paths[MODEL_QUERY_TOP16_USE]),
        ScoreJob("rrf-fused-top16-use", paths[RRF_FUSED_TOP16_USE]),
        ScoreJob(
            "same-stratum-shuffled-fused-use",
            paths[SAME_STRATUM_SHUFFLED_FUSED_USE],
        ),
    )


def _score_rows(
    *, arm: str, payload: Mapping[str, object], manifest: Path
) -> tuple[Mapping[str, Mapping[str, object]], Mapping[str, float]]:
    if not isinstance(payload, Mapping) or payload.get("verified") is not True:
        raise AnalysisError(f"{arm} official score payload is not verified")
    payload_manifest = _nonempty_text(payload.get("manifest"), f"{arm}.manifest")
    if Path(payload_manifest).resolve() != manifest:
        raise AnalysisError(f"{arm} score payload manifest identity drift")
    scores = payload.get("scores")
    if not isinstance(scores, Mapping) or set(scores) != {OFFICIAL_SCORER}:
        raise AnalysisError(
            f"{arm} must contain only the official {OFFICIAL_SCORER} score"
        )
    official = scores[OFFICIAL_SCORER]
    if not isinstance(official, Mapping):
        raise AnalysisError(f"{arm} official score is malformed")
    aggregate = official.get("aggregate")
    details = official.get("per_sample")
    if not isinstance(aggregate, Mapping) or aggregate.get("samples") != ROW_COUNT:
        raise AnalysisError(
            f"{arm} official aggregate must cover exactly {ROW_COUNT} rows"
        )
    if not isinstance(details, list) or len(details) != ROW_COUNT:
        raise AnalysisError(
            f"{arm} official per-sample detail must cover exactly {ROW_COUNT} rows"
        )
    metrics = {
        "exact_match": _finite_unit(aggregate.get("exact_match"), f"{arm}.exact_match"),
        "tool_accuracy": _finite_unit(
            aggregate.get("tool_accuracy"), f"{arm}.tool_accuracy"
        ),
        "slot_f1": _finite_unit(aggregate.get("slot_f1"), f"{arm}.slot_f1"),
    }
    failures = aggregate.get("parse_failures")
    if type(failures) is not int or not 0 <= failures <= ROW_COUNT:
        raise AnalysisError(
            f"{arm}.parse_failures must be an integer in [0, {ROW_COUNT}]"
        )
    metrics["parse_rate"] = (ROW_COUNT - failures) / ROW_COUNT
    rows: dict[str, Mapping[str, object]] = {}
    for index, detail in enumerate(details):
        if not isinstance(detail, Mapping):
            raise AnalysisError(f"{arm}.per_sample[{index}] is malformed")
        sample_id = _nonempty_text(
            detail.get("sample_id"), f"{arm}.per_sample[{index}].sample_id"
        )
        tier = _nonempty_text(detail.get("tier"), f"{arm}/{sample_id}.tier")
        if sample_id.rsplit(":", 1)[0] != tier:
            raise AnalysisError(
                f"{arm}/{sample_id} tier does not match the sample identity"
            )
        if sample_id in rows:
            raise AnalysisError(f"{arm} has duplicate sample identity {sample_id!r}")
        parsed = detail.get("parsed")
        if type(parsed) is not bool:
            raise AnalysisError(f"{arm}/{sample_id}.parsed must be boolean")
        rows[sample_id] = {
            "tier": tier,
            "exact_match": _finite_unit(
                detail.get("exact_match"), f"{arm}/{sample_id}.exact_match"
            ),
            "tool_accuracy": _finite_unit(
                detail.get("tool_accuracy"), f"{arm}/{sample_id}.tool_accuracy"
            ),
            "slot_f1": _finite_unit(
                detail.get("slot_f1"), f"{arm}/{sample_id}.slot_f1"
            ),
            "parsed": parsed,
        }
    if sum(not bool(row["parsed"]) for row in rows.values()) != failures:
        raise AnalysisError(
            f"{arm} parse failure count disagrees with its per-sample detail"
        )
    return rows, metrics


def _per_tier(
    rows: Mapping[str, Mapping[str, object]], official: object
) -> Mapping[str, Mapping[str, float | int]]:
    tiers: dict[str, list[Mapping[str, object]]] = {}
    for row in rows.values():
        tiers.setdefault(str(row["tier"]), []).append(row)
    if not isinstance(official, Mapping) or set(official) != set(tiers):
        raise AnalysisError(
            "official per_tier metrics must cover the exact scored tiers"
        )
    result: dict[str, Mapping[str, float | int]] = {}
    for tier, members in sorted(tiers.items()):
        score = official[tier]
        if not isinstance(score, Mapping) or score.get("samples") != len(members):
            raise AnalysisError(
                f"official per_tier metrics for {tier} have an invalid sample count"
            )
        failures = sum(not bool(member["parsed"]) for member in members)
        declared_failures = score.get("parse_failures")
        if declared_failures is not None and (
            type(declared_failures) is not int
            or declared_failures != failures
        ):
            raise AnalysisError(
                f"official per_tier metrics for {tier} disagree with per-sample parse status"
            )
        result[tier] = {
            "samples": len(members),
            "exact_match": _finite_unit(
                score.get("exact_match"), f"{tier}.exact_match"
            ),
            "tool_accuracy": _finite_unit(
                score.get("tool_accuracy"), f"{tier}.tool_accuracy"
            ),
            "slot_f1": _finite_unit(score.get("slot_f1"), f"{tier}.slot_f1"),
            "parse_rate": (len(members) - failures) / len(members),
        }
    return result


def _sign_test(
    left: Mapping[str, Mapping[str, object]],
    right: Mapping[str, Mapping[str, object]],
    metric: str,
) -> Mapping[str, float | int]:
    wins = sum(
        float(left[sample_id][metric]) > float(right[sample_id][metric])
        for sample_id in left
    )
    losses = sum(
        float(left[sample_id][metric]) < float(right[sample_id][metric])
        for sample_id in left
    )
    ties = ROW_COUNT - wins - losses
    non_ties = wins + losses
    tail = (
        sum(comb(non_ties, index) for index in range(0, min(wins, losses) + 1))
        / (2**non_ties)
        if non_ties
        else 1.0
    )
    return {
        "test": "exact-two-sided-paired-sign-test",
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "p_value": min(1.0, 2.0 * tail),
    }


def _paired_contrast(
    *,
    left: Mapping[str, Mapping[str, object]],
    right: Mapping[str, Mapping[str, object]],
    sample_ids: tuple[str, ...],
    bootstrap_replicates: int,
    bootstrap_seed: int,
) -> Mapping[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for offset, metric in enumerate(
        ("exact_match", "tool_accuracy", "slot_f1", "parse_rate")
    ):

        def statistic(ids: Sequence[str], metric_name: str = metric) -> float:
            if metric_name == "parse_rate":
                return sum(
                    bool(left[item]["parsed"]) - bool(right[item]["parsed"])
                    for item in ids
                ) / len(ids)
            return sum(
                float(left[item][metric_name]) - float(right[item][metric_name])
                for item in ids
            ) / len(ids)

        bootstrap = paired_cluster_bootstrap(
            sample_ids=sample_ids,
            statistic=statistic,
            n_replicates=bootstrap_replicates,
            seed=bootstrap_seed + offset,
        )
        metric_result: dict[str, object] = {
            "paired_bootstrap": bootstrap.as_json(),
            "point_estimate": bootstrap.point_estimate,
        }
        if metric in {"exact_match", "tool_accuracy"}:
            metric_result["sign_test"] = _sign_test(left, right, metric)
        result[metric] = metric_result
    return result


def _is_subsequence(needles: Sequence[str], haystack: Sequence[str]) -> bool:
    index = 0
    for item in haystack:
        if index < len(needles) and needles[index] == item:
            index += 1
    return index == len(needles)


def _validate_diagnostic(sample: RetrievalDiagnosticSample) -> None:
    _nonempty_text(sample.sample_id, "retrieval sample id")
    _nonempty_text(sample.tier, f"{sample.sample_id}.tier")
    if sample.sample_id.rsplit(":", 1)[0] != sample.tier:
        raise AnalysisError(f"{sample.sample_id} retrieval tier drift")
    if sample.retrieval_sealed is not True:
        raise AnalysisError(f"{sample.sample_id} retrieval is not sealed")
    _sequence_of_unique_text(
        sample.required_tool_ids,
        f"{sample.sample_id}.required_tool_ids",
        allow_empty=True,
    )
    for field_name, mapping in (("ranked_tool_ids", sample.ranked_tool_ids),):
        if not isinstance(mapping, Mapping) or set(mapping) != set(
            RETRIEVAL_CONDITIONS
        ):
            raise AnalysisError(
                f"{sample.sample_id}.{field_name} must provide the three ablation conditions"
            )
    for condition in RETRIEVAL_CONDITIONS:
        _sequence_of_unique_text(
            sample.ranked_tool_ids[condition],
            f"{sample.sample_id}/{condition}.ranked_tool_ids",
            allow_empty=True,
        )
    if sample.required_ordered_call_skeleton is not None:
        _sequence_of_unique_text(
            sample.required_ordered_call_skeleton,
            f"{sample.sample_id}.required_ordered_call_skeleton",
            allow_empty=True,
        )
    if sample.ranked_ordered_call_skeletons is not None:
        if set(sample.ranked_ordered_call_skeletons) != set(RETRIEVAL_CONDITIONS):
            raise AnalysisError(
                f"{sample.sample_id}.ranked_ordered_call_skeletons must provide the three ablation conditions"
            )
        for condition in RETRIEVAL_CONDITIONS:
            _sequence_of_unique_text(
                sample.ranked_ordered_call_skeletons[condition],
                f"{sample.sample_id}/{condition}.ranked_ordered_call_skeletons",
                allow_empty=True,
            )
    if sample.gold_calls is not None:
        if isinstance(sample.gold_calls, (str, bytes)) or not isinstance(
            sample.gold_calls, Sequence
        ):
            raise AnalysisError(f"{sample.sample_id}.gold_calls must be a sequence")
        for index, call in enumerate(sample.gold_calls):
            if not isinstance(call, Mapping):
                raise AnalysisError(
                    f"{sample.sample_id}.gold_calls[{index}] is malformed"
                )
            _call_identity(call, f"{sample.sample_id}.gold_calls[{index}]")
    if sample.proposed_action_sets is not None:
        if set(sample.proposed_action_sets) != set(RETRIEVAL_CONDITIONS):
            raise AnalysisError(
                f"{sample.sample_id}.proposed_action_sets must provide the three ablation conditions"
            )
        for condition in RETRIEVAL_CONDITIONS:
            proposed = sample.proposed_action_sets[condition]
            if isinstance(proposed, (str, bytes)) or not isinstance(proposed, Sequence):
                raise AnalysisError(
                    f"{sample.sample_id}/{condition}.proposed_action_sets must be a sequence"
                )
            for index, call in enumerate(proposed):
                if not isinstance(call, Mapping):
                    raise AnalysisError(
                        f"{sample.sample_id}/{condition}.proposed_action_sets[{index}] is malformed"
                    )
                _call_identity(
                    call,
                    f"{sample.sample_id}/{condition}.proposed_action_sets[{index}]",
                )


def _retrieval_upper_bounds(
    samples: Sequence[RetrievalDiagnosticSample], top_k: int
) -> Mapping[str, object]:
    if type(top_k) is not int or top_k <= 0:
        raise AnalysisError("retrieval top_k must be a positive integer")
    if isinstance(samples, (str, bytes)) or len(samples) != ROW_COUNT:
        raise AnalysisError(
            f"retrieval diagnostics must contain exactly {ROW_COUNT} rows"
        )
    ordered = tuple(sorted(samples, key=lambda item: item.sample_id))
    if len({item.sample_id for item in ordered}) != ROW_COUNT:
        raise AnalysisError("retrieval diagnostics contain duplicate sample identities")
    for item in ordered:
        if not isinstance(item, RetrievalDiagnosticSample):
            raise AnalysisError("retrieval diagnostics contain a malformed row")
        _validate_diagnostic(item)
    skeleton_available = all(
        item.required_ordered_call_skeleton is not None
        and item.ranked_ordered_call_skeletons is not None
        for item in ordered
    )
    action_set_available = all(
        item.gold_calls is not None and item.proposed_action_sets is not None
        for item in ordered
    )
    unavailable_skeleton: Mapping[str, str] = {
        "status": "unavailable",
        "reason": "no sealed ordered-call skeleton trace artifact was supplied",
    }
    unavailable_action_set: Mapping[str, str] = {
        "status": "unavailable",
        "reason": "no sealed proposal-content/action-set trace artifact was supplied",
    }
    conditions: dict[str, Mapping[str, object]] = {}
    for condition in RETRIEVAL_CONDITIONS:
        tool_hits = 0
        skeleton_hits = 0 if skeleton_available else None
        proposal_hits = 0 if action_set_available else None
        per_tier: dict[str, list[tuple[bool, bool | None, bool | None]]] = {}
        for item in ordered:
            tools = tuple(item.ranked_tool_ids[condition])[:top_k]
            tool_hit = set(item.required_tool_ids).issubset(set(tools))
            skeleton_hit = None
            if skeleton_available:
                assert item.ranked_ordered_call_skeletons is not None
                assert item.required_ordered_call_skeleton is not None
                skeleton_hit = _is_subsequence(
                    item.required_ordered_call_skeleton,
                    tuple(item.ranked_ordered_call_skeletons[condition])[:top_k],
                )
                assert skeleton_hits is not None
                skeleton_hits += skeleton_hit
            proposal_hit = None
            if action_set_available:
                assert item.proposed_action_sets is not None
                assert item.gold_calls is not None
                available = Counter(
                    _call_identity(call, f"{item.sample_id}/{condition}.action")
                    for call in item.proposed_action_sets[condition]
                )
                needed = Counter(
                    _call_identity(call, f"{item.sample_id}.gold")
                    for call in item.gold_calls
                )
                proposal_hit = all(
                    available[key] >= count for key, count in needed.items()
                )
                assert proposal_hits is not None
                proposal_hits += proposal_hit
            tool_hits += tool_hit
            per_tier.setdefault(item.tier, []).append(
                (tool_hit, skeleton_hit, proposal_hit)
            )
        tier_metrics: dict[str, Mapping[str, object]] = {}
        for tier, values in sorted(per_tier.items()):
            tier_metrics[tier] = {
                "samples": len(values),
                "top_k_tool_coverage": sum(value[0] for value in values)
                / len(values),
                "full_ordered_call_skeleton_coverage": (
                    sum(bool(value[1]) for value in values) / len(values)
                    if skeleton_available
                    else unavailable_skeleton
                ),
                "proposal_content_action_set_consumption_ceiling": (
                    sum(bool(value[2]) for value in values) / len(values)
                    if action_set_available
                    else unavailable_action_set
                ),
            }
        conditions[condition] = {
            "top_k_tool_coverage": tool_hits / ROW_COUNT,
            "full_ordered_call_skeleton_coverage": (
                skeleton_hits / ROW_COUNT
                if skeleton_available
                else unavailable_skeleton
            ),
            "proposal_content_action_set_consumption_ceiling": (
                proposal_hits / ROW_COUNT if action_set_available else unavailable_action_set
            ),
            "per_tier": tier_metrics,
        }
    return {
        "analysis_phase": "post-seal",
        "runtime_eligible": False,
        "top_k": top_k,
        "upper_bound_kind": "retrieval-tool-coverage-with-trace-gated-optional-ceilings",
        "scope_note": (
            "These are post-seal diagnostics over sealed rankings. Ordered-call "
            "skeleton and proposal-content/action-set ceilings remain unavailable "
            "unless their corresponding trace artifacts are supplied. No diagnostic "
            "establishes model consumption, achievable answer accuracy, or a runtime selection rule."
        ),
        "conditions": conditions,
    }


def analyze_semantic_agentloop_flight(
    *,
    manifests: Mapping[str, Mapping[str, object]],
    score_payloads: Mapping[str, Mapping[str, object]],
    retrieval_samples: Sequence[RetrievalDiagnosticSample],
    retrieval_top_k: int = 16,
    bootstrap_replicates: int = 10_000,
    bootstrap_seed: int = 20260903,
) -> Mapping[str, object]:
    """Build the complete model-free post-seal report for the future flight."""

    paths = _validate_manifest_descriptors(manifests)
    if not isinstance(score_payloads, Mapping) or set(score_payloads) != set(
        SCORED_ARM_ORDER
    ):
        raise AnalysisError(
            "score payloads must cover exactly the five scoreable complete manifests"
        )
    rows_by_arm: dict[str, Mapping[str, Mapping[str, object]]] = {}
    arm_metrics: dict[str, Mapping[str, object]] = {}
    for arm in SCORED_ARM_ORDER:
        rows, metrics = _score_rows(
            arm=arm, payload=score_payloads[arm], manifest=paths[arm]
        )
        rows_by_arm[arm] = rows
        official = score_payloads[arm]["scores"][OFFICIAL_SCORER]
        assert isinstance(official, Mapping)
        aggregate = official["aggregate"]
        assert isinstance(aggregate, Mapping)
        arm_metrics[arm] = {
            **metrics,
            "per_tier": _per_tier(rows, aggregate.get("per_tier")),
        }
    sample_ids = tuple(sorted(rows_by_arm[DIRECT_M0]))
    if len(sample_ids) != ROW_COUNT or any(
        set(rows_by_arm[arm]) != set(sample_ids) for arm in SCORED_ARM_ORDER
    ):
        raise AnalysisError(
            "all scoreable arms must have the same exact 104 sample identities"
        )
    diagnostics = tuple(retrieval_samples)
    if {
        item.sample_id
        for item in diagnostics
        if isinstance(item, RetrievalDiagnosticSample)
    } != set(sample_ids):
        raise AnalysisError(
            "retrieval diagnostic identities must match the three scoreable manifests"
        )
    return {
        "schema": RESULT_SCHEMA,
        "analysis_phase": "post-seal",
        "runtime_eligible": False,
        "row_count": ROW_COUNT,
        "manifest_roles": {arm: str(paths[arm]) for arm in ARM_ORDER},
        "official_scoring_boundary": {
            "scoreable_complete_manifests": list(SCORED_ARM_ORDER),
            "obs_manifest_is_diagnostic_only": True,
            "one_official_scorer_process_per_complete_manifest": True,
            "outer_parallel_workers_maximum": 4,
            "never_shard_a_manifest": True,
            "never_average_shard_metrics": True,
        },
        "arms": arm_metrics,
        "paired_contrasts": {
            "transcript_m0": _paired_contrast(
                left=rows_by_arm[TRANSCRIPT_TOP16_USE],
                right=rows_by_arm[DIRECT_M0],
                sample_ids=sample_ids,
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed + 50,
            ),
            "query_transcript": _paired_contrast(
                left=rows_by_arm[MODEL_QUERY_TOP16_USE],
                right=rows_by_arm[TRANSCRIPT_TOP16_USE],
                sample_ids=sample_ids,
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed,
            ),
            "fused_transcript": _paired_contrast(
                left=rows_by_arm[RRF_FUSED_TOP16_USE],
                right=rows_by_arm[TRANSCRIPT_TOP16_USE],
                sample_ids=sample_ids,
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed + 100,
            ),
            "fused_query": _paired_contrast(
                left=rows_by_arm[RRF_FUSED_TOP16_USE],
                right=rows_by_arm[MODEL_QUERY_TOP16_USE],
                sample_ids=sample_ids,
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed + 200,
            ),
            "fused_m0": _paired_contrast(
                left=rows_by_arm[RRF_FUSED_TOP16_USE],
                right=rows_by_arm[DIRECT_M0],
                sample_ids=sample_ids,
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed + 300,
            ),
            "fused_shuffled": _paired_contrast(
                left=rows_by_arm[RRF_FUSED_TOP16_USE],
                right=rows_by_arm[SAME_STRATUM_SHUFFLED_FUSED_USE],
                sample_ids=sample_ids,
                bootstrap_replicates=bootstrap_replicates,
                bootstrap_seed=bootstrap_seed + 400,
            ),
        },
        "retrieval_upper_bounds": _retrieval_upper_bounds(diagnostics, retrieval_top_k),
        "promotion_gates": {
            "scope": "104-row discovery qualification only; not a confirmatory or paper-scale claim",
            "require_complete_verified_five_call_manifests_and_complete_obs_manifest": True,
            "require_all_six_paired_retrieval_and_evidence_contrasts_reported": True,
            "require_transcript_query_fused_tool_ranking_reachability_reported": True,
            "optional_skeleton_and_action_set_ceilings_require_sealed_trace_artifacts": True,
            "require_no_network_jitter_claim": True,
            "future_tfrl_over_0_90_not_required": True,
            "future_tfrl_over_0_90_is_not_a_baseline_admission_requirement": True,
            "pass_opens_only_a_separately_preregistered_pinned_controller_decision": True,
        },
        "contextual_bandit_decision_record": {
            "status": "deferred; no training-free reinforcement learning is implemented by this analysis",
            "required_upstream_runtime": "vowpalwabbit==9.11.2 cb_explore_adf",
            "later_record_fields": [
                "context_hash",
                "action_set_hash",
                "chosen_action",
                "propensity",
                "observed_reward",
                "trajectory_hash",
                "split_identity_hash",
            ],
            "decision_rule": "A later owner-approved preregistration must bind the policy, propensities, rewards, and held-out evaluation before any fit.",
        },
        "conclusion_exclusions": "network jitter, retries, repair, resend behavior, and transport timing are excluded from scientific conclusions.",
    }


__all__ = [
    "ARM_ORDER",
    "AnalysisError",
    "DIRECT_M0",
    "MODEL_QUERY_TOP16_USE",
    "OBS_SEMANTIC_RETRIEVAL",
    "RETRIEVAL_CONDITIONS",
    "RESULT_SCHEMA",
    "RetrievalDiagnosticSample",
    "RRF_FUSED_TOP16_USE",
    "ROW_COUNT",
    "SAME_STRATUM_SHUFFLED_FUSED_USE",
    "TRANSCRIPT_TOP16_USE",
    "analyze_semantic_agentloop_flight",
    "build_official_score_jobs",
]
