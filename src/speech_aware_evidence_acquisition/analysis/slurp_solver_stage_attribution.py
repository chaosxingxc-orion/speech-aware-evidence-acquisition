"""Offline initial-Solver to delivered-final attribution for verified SLURP episodes.

Gold records are scoring-side inputs only. This module never writes them into
its report, contacts a model or tool, invokes the official evaluator, or
computes a replacement official corpus metric.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Mapping, Sequence

from ..data.slurp import SlurpRecord
from ..data.splits import prefixed, split_identity_hash
from ..rails.hashing import content_hash
from ..rails.native_episode_receipt import validate_native_episode_delivery_receipt
from ..rails.reward_links import SLURP_NATIVE_FIELDS
from ..reproduction.slurp_scoring import parse_slu_response, score_slu
from .native_episode_source import VerifiedNativeEpisodeSource
from .native_role_responses import (
    NativeRoleResponseSelection,
    NativeRoleResponseSelectionError,
    select_verified_native_role_response,
)

SCHEMA = "saea-slurp-solver-stage-attribution-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class SlurpSolverStageAttributionError(ValueError):
    """A scoring-side stage attribution input lacks exact source custody."""


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SlurpSolverStageAttributionError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SlurpSolverStageAttributionError(f"{label} must be an ordered sequence")
    return value


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise SlurpSolverStageAttributionError(f"{label} must be a lowercase SHA-256")
    return value


def _number(value: object, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
    ):
        raise SlurpSolverStageAttributionError(
            f"{label} must be a finite nonnegative number"
        )
    return float(value)


def _diagnostic_score(reference: SlurpRecord, text: str) -> dict[str, object]:
    scenario, action, entities, parsed = parse_slu_response(text)
    score = score_slu(
        gold_scenario=reference.scenario,
        gold_action=reference.action,
        gold_entities=reference.entities,
        predicted_scenario=scenario,
        predicted_action=action,
        predicted_entities=entities,
    )
    metrics = score.as_metrics_dict()
    entity_exact = (
        score.slot_f1_exact_fp == 0.0 and score.slot_f1_exact_fn == 0.0
    )
    intent_exact = score.scenario_action_exact == 1.0
    return {
        "parsed": parsed,
        "intent_exact": int(intent_exact),
        "entity_exact": int(entity_exact),
        "full_exact": int(intent_exact and entity_exact),
        "slot_f1_exact_f1": metrics["slot_f1_exact_f1"],
        "slu_f1_diagnostic_f1": metrics["slu_f1_f1"],
        "native_fields": {field: metrics[field] for field in SLURP_NATIVE_FIELDS},
    }


def _validate_saved_final(
    sample_id: str,
    saved: Mapping[str, object],
    deterministic: Mapping[str, object],
) -> None:
    parsed = saved.get("parsed")
    if type(parsed) is not bool or parsed != deterministic["parsed"]:
        raise SlurpSolverStageAttributionError(
            f"saved final score parse status differs for {sample_id!r}"
        )
    fields = _mapping(deterministic.get("native_fields"), "deterministic native fields")
    for field in SLURP_NATIVE_FIELDS:
        if field not in saved:
            raise SlurpSolverStageAttributionError(
                f"saved final score for {sample_id!r} lacks {field!r}"
            )
        actual = _number(saved[field], f"saved final score {sample_id!r} {field}")
        if abs(actual - float(fields[field])) > 1e-9:
            raise SlurpSolverStageAttributionError(
                f"saved final score {field!r} differs for {sample_id!r}"
            )


def _transition(draft: int | None, final: int) -> str:
    if draft is None:
        return "unavailable"
    if draft == 0 and final == 1:
        return "save"
    if draft == 1 and final == 0:
        return "harm"
    return "stable-correct" if final == 1 else "stable-wrong"


def _aggregate(samples: Sequence[Mapping[str, object]], field: str) -> dict[str, int]:
    transitions = [
        _mapping(row.get("transitions"), "sample transitions").get(field)
        for row in samples
    ]
    draft = [
        _mapping(row.get("metrics"), "sample metrics").get("draft") for row in samples
    ]
    final = [
        _mapping(_mapping(row.get("metrics"), "sample metrics").get("final"), "final metrics")
        for row in samples
    ]
    return {
        "n": len(samples),
        "draft_correct": sum(
            isinstance(value, Mapping) and value.get(field) == 1 for value in draft
        ),
        "final_correct": sum(value.get(field) == 1 for value in final),
        "saves": transitions.count("save"),
        "harms": transitions.count("harm"),
        "stable_correct": transitions.count("stable-correct"),
        "stable_wrong": transitions.count("stable-wrong"),
        "unavailable": transitions.count("unavailable"),
        "net": transitions.count("save") - transitions.count("harm"),
    }


def _exact_roster(
    source: VerifiedNativeEpisodeSource,
    references: Sequence[SlurpRecord],
    official_rows: Sequence[Mapping[str, object]],
) -> tuple[str, ...]:
    if (
        not isinstance(source, VerifiedNativeEpisodeSource)
        or any(not isinstance(record, SlurpRecord) for record in references)
        or any(not isinstance(row, Mapping) for row in official_rows)
    ):
        raise SlurpSolverStageAttributionError(
            "native, reference, and saved score inputs must share the full exact ordered roster"
        )
    ids = tuple(source.sample_ids)
    reference_ids = tuple(record.sample_id for record in references)
    official_ids = tuple(row.get("sample_id") for row in official_rows)
    if (
        not ids
        or len(ids) != len(set(ids))
        or reference_ids != ids
        or official_ids != ids
        or set(source.phase_results) != set(ids)
        or set(source.output_rows) != set(ids)
        or set(source.bundle.split_ids) != set(ids)
    ):
        raise SlurpSolverStageAttributionError(
            "native, reference, and saved score inputs must share the full exact ordered roster"
        )
    if (
        getattr(source.plan, "carrier_lock_key", None) != "slurp"
        or source.plan.split_identity_hash != split_identity_hash(prefixed("slurp", ids))
    ):
        raise SlurpSolverStageAttributionError(
            "verified source does not bind the exact ordered SLURP roster"
        )
    for sample_id in ids:
        if (
            source.phase_results[sample_id].get("sample_id") != sample_id
            or source.output_rows[sample_id].get("sample_id") != sample_id
        ):
            raise SlurpSolverStageAttributionError(
                "native, reference, and saved score inputs must share the full exact ordered roster"
            )
    return ids


def _delivery_selection(
    source: VerifiedNativeEpisodeSource,
    sample_id: str,
    episode: Mapping[str, object],
    visits: Sequence[object],
) -> tuple[str, NativeRoleResponseSelection | None, dict[str, object]]:
    routes = _sequence(episode.get("planner_routes"), "Planner routes")
    try:
        delivery = validate_native_episode_delivery_receipt(
            episode, visits, routes, error_type=SlurpSolverStageAttributionError
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, SlurpSolverStageAttributionError):
            raise
        raise SlurpSolverStageAttributionError(str(error)) from error
    output = _mapping(source.output_rows[sample_id], f"output row {sample_id!r}")
    final_text = output.get("text")
    if not isinstance(final_text, str):
        raise SlurpSolverStageAttributionError(f"output row {sample_id!r} lacks text")
    if delivery.kind == "abstention":
        if final_text != "":
            raise SlurpSolverStageAttributionError("abstention delivery must be empty")
        source_json = {
            "status": "abstention",
            "delivery_kind": delivery.kind,
            "request_id": output.get("request_id"),
            "request_sha256": output.get("request_sha256"),
            "response_sha256": output.get("response_sha256"),
            "response_text_sha256": output.get("response_text_sha256"),
        }
        for field in ("request_sha256", "response_sha256", "response_text_sha256"):
            _sha256(source_json[field], f"abstention {field}")
        return final_text, None, source_json

    receipt = _mapping(delivery.solver_receipt, "delivered Solver receipt")
    matching_indices = [
        index
        for index, raw_visit in enumerate(visits)
        if isinstance(raw_visit, Mapping)
        and raw_visit.get("execution_receipt") == receipt
    ]
    if len(matching_indices) != 1:
        raise SlurpSolverStageAttributionError(
            "delivered Solver receipt has no unique role visit"
        )
    index = matching_indices[0]
    visit = _mapping(visits[index], "delivered Solver visit")
    try:
        selected = select_verified_native_role_response(
            source,
            sample_id=sample_id,
            role_id=str(visit.get("role_id")),
            visit_index=index,
        )
    except NativeRoleResponseSelectionError as error:
        raise SlurpSolverStageAttributionError(str(error)) from error
    if (
        selected.status != "completed"
        or selected.request_id != delivery.final_contact.get("request_id")
    ):
        raise SlurpSolverStageAttributionError(
            "delivered Solver selection differs from shared delivery semantics"
        )
    source_json = selected.source_json()
    source_json["delivery_kind"] = delivery.kind
    normalisation = episode.get("deliver_normaliser")
    if normalisation is not None:
        from ..core.bundle import BundleError
        from ..core.bundle.outputs import _verify_delivery_normalisation

        block = _mapping(normalisation, "delivery normalisation")
        response = _mapping(source.bundle.trace_records.get(
            f"{selected.request_id}/response"), "delivered response")
        try:
            _verify_delivery_normalisation(output, block, response)
        except BundleError as error:
            raise SlurpSolverStageAttributionError(
                f"delivery normalisation custody failed: {error}"
            ) from error
        source_json["normalisation"] = {key: block[key] for key in (
            "normaliser_id", "carrier_lock_key", "input_sha256", "output_sha256")}
    elif (selected.response_text != final_text or
          selected.response_text_sha256 != hashlib.sha256(final_text.encode()).hexdigest()):
        raise SlurpSolverStageAttributionError(
            "delivered Solver selection differs from shared delivery semantics")
    source_json["delivered_text_sha256"] = hashlib.sha256(final_text.encode()).hexdigest()
    return final_text, selected, source_json


def build_slurp_solver_stage_attribution(
    source: VerifiedNativeEpisodeSource,
    *,
    reference_records: Sequence[SlurpRecord],
    official_final_rows: Sequence[Mapping[str, object]],
    reference_binding_sha256: str,
    official_score_result_sha256: str,
) -> dict[str, object]:
    """Build deterministic per-row draft/final diagnostics over one full roster.

    ``official_final_rows`` are saved per-sample fields from the already-run
    authoritative scorer. They are checked for identity; this function never
    invokes that scorer and deliberately omits a corpus-level micro-F1.
    """
    references = tuple(reference_records)
    official = tuple(official_final_rows)
    ids = _exact_roster(source, references, official)
    reference_binding_sha256 = _sha256(
        reference_binding_sha256, "reference binding SHA-256"
    )
    official_score_result_sha256 = _sha256(
        official_score_result_sha256, "official score result SHA-256"
    )
    _sha256(source.phase_artifact_sha256, "phase artifact SHA-256")
    _sha256(source.composed.config_hash, "composed config hash")
    _sha256(source.plan.protocol_hash, "protocol hash")
    _sha256(source.plan.split_identity_hash, "split identity hash")

    samples = []
    for sample_id, reference, saved in zip(ids, references, official, strict=True):
        phase_result = _mapping(
            source.phase_results[sample_id], f"phase result {sample_id!r}"
        )
        episode = _mapping(
            phase_result.get("native_episode_receipt"),
            f"native episode receipt {sample_id!r}",
        )
        visits = _sequence(episode.get("role_visits"), f"role visits {sample_id!r}")
        solver_indices = [
            index
            for index, visit in enumerate(visits)
            if isinstance(visit, Mapping) and visit.get("stage") == "solver"
        ]
        interrupted = episode.get("interrupted_role")
        interrupted_solver = (
            isinstance(interrupted, Mapping) and interrupted.get("stage") == "solver"
        )
        solver_attempt_count = len(solver_indices) + int(interrupted_solver)
        initial: NativeRoleResponseSelection | None = None
        if solver_indices:
            initial_visit = _mapping(visits[solver_indices[0]], "initial Solver visit")
            try:
                initial = select_verified_native_role_response(
                    source,
                    sample_id=sample_id,
                    role_id=str(initial_visit.get("role_id")),
                    visit_index=solver_indices[0],
                )
            except NativeRoleResponseSelectionError as error:
                raise SlurpSolverStageAttributionError(str(error)) from error
        final_text, delivered, final_source = _delivery_selection(
            source, sample_id, episode, visits
        )
        pre_delivery_metrics = (None if delivered is None else
                                _diagnostic_score(reference, str(delivered.response_text)))
        final_metrics = _diagnostic_score(reference, final_text)
        _validate_saved_final(sample_id, saved, final_metrics)
        draft_metrics = (
            None
            if initial is None or initial.status != "completed"
            else _diagnostic_score(reference, str(initial.response_text))
        )
        transitions = {
            field: _transition(
                None if draft_metrics is None else int(draft_metrics[field]),
                int(final_metrics[field]),
            )
            for field in ("intent_exact", "entity_exact", "full_exact")
        }
        delivered_solver_revision = (
            None
            if initial is None or delivered is None
            else initial.visit_index != delivered.visit_index
        )
        response_changed = (
            None
            if initial is None or delivered is None
            else initial.response_text_sha256 != delivered.response_text_sha256
        )
        samples.append(
            {
                "sample_id": sample_id,
                "source": {
                    "initial_solver": (
                        {"status": "missing"}
                        if initial is None else initial.source_json()
                    ),
                    "final_delivery": final_source,
                },
                "parse": {
                    "draft": None if draft_metrics is None else draft_metrics["parsed"],
                    "final": final_metrics["parsed"],
                },
                "revision": {
                    "solver_attempt_count": solver_attempt_count,
                    "completed_solver_visits": len(solver_indices),
                    "attempted_solver_revision": solver_attempt_count > 1,
                    "completed_solver_revision": len(solver_indices) > 1,
                    "delivered_solver_revision": delivered_solver_revision,
                    "response_changed": response_changed,
                },
                "metrics": {"draft": draft_metrics, "final": final_metrics,
                            "pre_delivery": pre_delivery_metrics},
                "postprocessing_transitions": {
                    field: _transition(None if pre_delivery_metrics is None else
                                       int(pre_delivery_metrics[field]), int(final_metrics[field]))
                    for field in ("intent_exact", "entity_exact", "full_exact")
                },
                "transitions": transitions,
            }
        )

    return {
        "schema": SCHEMA,
        "status": "source-verified-deterministic-diagnostic",
        "source": {
            "phase_artifact_sha256": source.phase_artifact_sha256,
            "reference_binding_sha256": reference_binding_sha256,
            "official_score_result_sha256": official_score_result_sha256,
            "config_hash": source.composed.config_hash,
            "protocol_hash": source.plan.protocol_hash,
            "split_identity_hash": source.plan.split_identity_hash,
            "ordered_sample_ids_sha256": content_hash(list(ids)),
            "run_id": source.plan.run_id,
            "attempt_id": source.plan.attempt_id,
        },
        "semantics": {
            "gold_runtime_access": False,
            "gold_exported": False,
            "scoring": "deterministic per-sample diagnostic",
            "official_final_fields_reused": True,
            "official_micro_f1_authority": "saved complete official score result",
            "official_micro_f1_recomputed": False,
            "entity_exact": "zero exact-slot false positives and false negatives",
            "full_exact": "intent exact and entity exact on the same row",
            "save_harm_direction": "initial Solver draft to shared delivered final",
            "attempted_solver_revision": (
                "A later completed or finite-interrupted Solver occurrence exists."
            ),
            "completed_solver_revision": "At least two Solver visits completed.",
            "delivered_solver_revision": (
                "The shared delivered Solver differs from the initial completed Solver; "
                "null when either endpoint is unavailable."
            ),
        },
        "cohort": {
            "sample_count": len(ids),
            "ordered_sample_ids_sha256": content_hash(list(ids)),
        },
        "aggregate": {
            "intent_exact": _aggregate(samples, "intent_exact"),
            "entity_exact": _aggregate(samples, "entity_exact"),
            "full_exact": _aggregate(samples, "full_exact"),
            "parse": {
                "draft_parsed": sum(row["parse"]["draft"] is True for row in samples),
                "final_parsed": sum(row["parse"]["final"] is True for row in samples),
                "draft_unparsed": sum(row["parse"]["draft"] is False for row in samples),
                "draft_unavailable": sum(row["parse"]["draft"] is None for row in samples),
                "final_unparsed": sum(row["parse"]["final"] is False for row in samples),
            },
            "solver_revision": {
                "attempted": sum(
                    row["revision"]["attempted_solver_revision"] is True for row in samples
                ),
                "not_attempted": sum(
                    row["revision"]["attempted_solver_revision"] is False for row in samples
                ),
                "completed": sum(
                    row["revision"]["completed_solver_revision"] is True for row in samples
                ),
                "not_completed": sum(
                    row["revision"]["completed_solver_revision"] is False for row in samples
                ),
                "delivered": sum(
                    row["revision"]["delivered_solver_revision"] is True for row in samples
                ),
                "not_delivered": sum(
                    row["revision"]["delivered_solver_revision"] is False for row in samples
                ),
                "delivery_unavailable": sum(
                    row["revision"]["delivered_solver_revision"] is None for row in samples
                ),
                "response_changed": sum(
                    row["revision"]["response_changed"] is True for row in samples
                ),
            },
        },
        "samples": samples,
    }


__all__ = [
    "SCHEMA",
    "SlurpSolverStageAttributionError",
    "build_slurp_solver_stage_attribution",
]
