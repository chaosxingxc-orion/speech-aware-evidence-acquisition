"""Root-only offline process diagnostics over already qualified complete SLURP sources.

The caller must first qualify its entire family and exact root READ. No runtime,
model, scoring job, policy selection, or optimizer export is performed here.
"""
from __future__ import annotations

import math
from collections.abc import Set

from .review_findings import analyze_slot_review_episode
from .slurp_solver_stage_attribution import build_slurp_solver_stage_attribution


BOOL_FIELDS = frozenset({
    "gold_empty", "draft_entity_correct", "final_entity_correct",
    "draft_full_correct", "final_full_correct", "review_alarm", "review_valid",
    "handoff_visible", "revised",
})
OPTIONAL_FIELDS = frozenset({"empty_false_fill", "draft_parsed", "final_parsed"})


def rate(observations):
    """Describe one binary observation per input, retaining unavailable evidence.

    Wilson intervals are descriptive single-input intervals, not paired treatment
    effects or correction for repeated adaptive selection. Missing bounds assign
    every unknown outcome to failure or success; they are not confidence bounds.
    """
    values = list(observations)
    if any(v is not None and type(v) is not bool for v in values):
        raise ValueError("binary observations must be bool or None")
    yes = sum(v is True for v in values)
    known = sum(v is not None for v in values)
    unknown = len(values) - known
    interval = None
    if known:
        z = 1.959963984540054
        p = yes / known
        scale = 1 + z*z/known
        center = (p + z*z/(2*known))/scale
        half = z*math.sqrt(p*(1-p)/known + z*z/(4*known*known))/scale
        interval = [max(0., center-half), min(1., center+half)]
    return {"numerator": yes, "denominator": known, "eligible": len(values),
            "unknown": unknown, "value": yes/known if known else None,
            "ci95_wilson": interval,
            "lower_missing_bound": yes/len(values) if values else None,
            "upper_missing_bound": (yes+unknown)/len(values) if values else None}


def measure_support(gold, *, retrieved, delivered):
    """Count exact set coverage without returning any labels or values.

    This arithmetic helper does not attest source custody. Inputs must come from
    separately verified actual retrieval and request projections, never reretrieval.
    Use independently for intent IDs, slot types and exact (type, value) pairs.
    Empty gold has no recall denominator. An absent source is None, not an empty set.
    """
    if not isinstance(gold, Set) or any(
        x is not None and not isinstance(x, Set) for x in (retrieved, delivered)
    ):
        raise ValueError("support inputs must be sets or missing source None")
    result = {"gold_count": len(gold)}
    for name, values in (("retrieved", retrieved), ("delivered", delivered)):
        hits = None if values is None else len(gold & values)
        result[name+"_hits"] = hits
        result[name+"_all"] = None if not gold or values is None else gold <= values
        result[name+"_fraction"] = hits/len(gold) if gold and hits is not None else None
    result["lost_all_support"] = (
        result["retrieved_all"] and not result["delivered_all"]
        if all(result[n+"_all"] is not None for n in ("retrieved", "delivered")) else None
    )
    return result


def _metrics(rows):
    def metric(key, condition=lambda r: True):
        # Eligibility is explicit; unknown conditioning variables are separately
        # counted below rather than silently treated as positive/negative cases.
        return rate(r.get(key) for r in rows if condition(r))

    result = {key: metric(key) for key in (
        "review_valid", "draft_parsed", "final_parsed",
        "draft_entity_correct", "final_entity_correct",
        "draft_full_correct", "final_full_correct",
    )}
    result.update({
        "review_error_detection": metric("review_alarm", lambda r: r["draft_entity_correct"] is False),
        "review_miss": rate(None if r["review_alarm"] is None else not r["review_alarm"]
                            for r in rows if r["draft_entity_correct"] is False),
        "review_alarm_precision": rate(None if r["draft_entity_correct"] is None else not r["draft_entity_correct"]
                                       for r in rows if r["review_alarm"] is True),
        "review_false_alarm": metric("review_alarm", lambda r: r["draft_entity_correct"] is True),
        "handoff_visibility_given_valid_review": metric("handoff_visible", lambda r: r["review_valid"] is True),
        "revision_after_alarm": metric("revised", lambda r: r["review_alarm"] is True),
        "entity_repair_given_revision": metric("final_entity_correct", lambda r: r["draft_entity_correct"] is False and r["revised"] is True),
        "entity_repair_after_alarm": metric("final_entity_correct", lambda r: r["draft_entity_correct"] is False and r["review_alarm"] is True),
        "entity_harm_given_revision": rate(None if r["final_entity_correct"] is None else not r["final_entity_correct"]
                                          for r in rows if r["draft_entity_correct"] is True and r["revised"] is True),
        "revision_of_correct_draft": metric("revised", lambda r: r["draft_full_correct"] is True),
        "full_repair_given_revision": metric("final_full_correct", lambda r: r["draft_full_correct"] is False and r["revised"] is True),
        "full_harm_given_revision": rate(None if r["final_full_correct"] is None else not r["final_full_correct"]
                                        for r in rows if r["draft_full_correct"] is True and r["revised"] is True),
        "empty_gold_false_fill": metric("empty_false_fill", lambda r: r["gold_empty"] is True),
    })
    return result


def _transitions(rows, axis):
    pairs = [(r["draft_"+axis+"_correct"],r["final_"+axis+"_correct"]) for r in rows]
    result = {"wrong_to_correct": pairs.count((False,True)),
              "correct_to_wrong": pairs.count((True,False)),
              "stable_correct": pairs.count((True,True)),
              "stable_wrong": pairs.count((False,False)),
              "unknown": sum(a is None or b is None for a,b in pairs)}
    result["net_repairs"] = result["wrong_to_correct"] - result["correct_to_wrong"]
    return result


def aggregate_process_metrics(rows):
    """Reduce abstract input-level rows; this reducer alone grants no read authority."""
    rows = list(rows)
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or not BOOL_FIELDS <= row.keys() or not set(row) <= BOOL_FIELDS | OPTIONAL_FIELDS | {"sample_id", "scenario"}:
            raise ValueError("unexpected or missing abstract diagnostic fields")
        for key in ("sample_id", "scenario"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise ValueError("sample identity and scenario must be nonempty")
        if row["sample_id"] in seen:
            raise ValueError("one observation per unique input is required")
        seen.add(row["sample_id"])
        for key in BOOL_FIELDS | (OPTIONAL_FIELDS & row.keys()):
            if row[key] is not None and type(row[key]) is not bool:
                raise ValueError("diagnostic flags must be bool or None")
        if row["review_valid"] is not True and row["review_alarm"] is not None:
            raise ValueError("invalid or missing review is not a positive or negative alarm")
    return {
        "schema": "saea-slurp-process-metrics-v1", "sample_count": len(rows),
        "metrics": _metrics(rows),
        "transitions": {axis: _transitions(rows,axis) for axis in ("entity","full")},
        "conditioning_unavailable": {k: sum(r[k] is None for r in rows) for k in BOOL_FIELDS},
        "by_scenario": {s: {"sample_count": sum(r["scenario"] == s for r in rows),
                            "metrics": _metrics([r for r in rows if r["scenario"] == s])}
                        for s in sorted({r["scenario"] for r in rows})},
        "claims_causal_node_credit": False,
        "claims_semantically_correct_criticism": False,
        "statistical_scope": "descriptive single-input Wilson intervals; adaptive reused-roster evidence",
    }


def build_slurp_process_metrics(source, *, reference_records, official_final_rows,
                               reference_binding_sha256, official_score_result_sha256,
                               legal_slot_types, intent_support_configuration=None):
    """Join first-draft review and final delivery with verified saved source custody.

    Count at most one review per input: the first completed Reviewer between the
    initial Solver and its next Solver visit. Never evaluate a later review against
    the initial draft. Review detection concerns entities, the slot contract's scope.
    A finding on an erroneous draft is an episode alarm, not validated criticism.
    """
    references = tuple(reference_records)
    stage = build_slurp_solver_stage_attribution(
        source, reference_records=references, official_final_rows=official_final_rows,
        reference_binding_sha256=reference_binding_sha256,
        official_score_result_sha256=official_score_result_sha256,
    )
    audit = analyze_slot_review_episode(source, legal_slot_types=legal_slot_types)
    rows, custody = [], []
    for ref, scored, reviewed in zip(references, stage["samples"], audit["rows"], strict=True):
        visits = source.phase_results[ref.sample_id]["native_episode_receipt"]["role_visits"]
        first = scored["source"]["initial_solver"].get("visit_index")
        next_solver = next((i for i, v in enumerate(visits)
                            if first is not None and i > first and v["role_id"] == "solver"), len(visits))
        review = next((r for r in reviewed["reviews"]
                       if first is not None and r["source"].get("visit_index") is not None
                       and first < r["source"]["visit_index"] < next_solver), None)
        valid = None if review is None else review["status"] == "valid" and not review["non_slot_identifiers"]
        draft, final = scored["metrics"]["draft"], scored["metrics"]["final"]
        rows.append({
            "sample_id": ref.sample_id, "scenario": ref.scenario,
            "gold_empty": not ref.entities,
            "draft_parsed": None if draft is None else draft["parsed"],
            "final_parsed": final["parsed"],
            "draft_entity_correct": bool(draft["entity_exact"]) if draft and draft["parsed"] else None,
            "final_entity_correct": bool(final["entity_exact"]) if final["parsed"] else None,
            "draft_full_correct": bool(draft["full_exact"]) if draft else None,
            "final_full_correct": bool(final["full_exact"]),
            "empty_false_fill": (not bool(final["entity_exact"])) if not ref.entities and final["parsed"] else None,
            "review_valid": valid,
            "review_alarm": review["finding_count"] > 0 if valid else None,
            "handoff_visible": review.get("handoff_in_next_planner_context") if review else None,
            "revised": scored["revision"]["completed_solver_revision"],
        })
        custody.append({"sample_id": ref.sample_id, **scored["source"],
                        "first_draft_review": review["source"] if review else None})
    report = aggregate_process_metrics(rows)
    report.update(source=stage["source"], inventory_sha256=audit["inventory_sha256"],
                  rows=rows, custody=custody,
                  recall_status="unavailable-until-actual-source-projection",
                  contacts_added={"model": 0, "official_scorer": 0},
                  authorization="caller-qualified complete family and exact root READ required",
                  distribution="root-only; no automatic learner export")
    if intent_support_configuration is not None:
        report["intent_support"] = _intent_support(source, references, intent_support_configuration)
        report["recall_status"] = "initial-request-card-and-candidate-projection-only"
    return report


def _intent_support(source, references, configuration):
    """Reuse the actual request/state/supply custody joins, never rerun retrieval."""
    from .native_candidate_stage_projections import project_verified_native_candidate_stages
    from .native_intent_support import build_initial_intent_support_diagnostics
    from .slurp_topn_diagnostics import ReferenceIntentRow

    required = {"legal_candidate_ids", "max_candidates", "specification"}
    if not isinstance(configuration, dict) or not required <= configuration.keys() or not set(configuration) <= required | {"projection_policy"}:
        raise ValueError("intent support requires its exact declared source mapping")
    pairs = project_verified_native_candidate_stages(
        source, **{k: v for k, v in configuration.items() if k != "specification"})
    support = build_initial_intent_support_diagnostics(
        source=source, stage_pairs=pairs,
        reference_rows=tuple(ReferenceIntentRow(r.sample_id, r.intent) for r in references),
        legal_candidate_ids=configuration["legal_candidate_ids"],
        specification=configuration["specification"],
    )
    rows = support["samples"]
    return {
        "store_source": support["store_source"],
        "semantics": support["semantics"],
        "metrics": {
            "gold_intent_card_in_initial_request": rate(r["gold_intent_value_supplied"] for r in rows),
            "gold_intent_in_initial_candidates": rate(r["c0_gold_covered"] for r in rows),
            "candidate_coverage_given_card": rate(r["c0_gold_covered"] for r in rows if r["gold_intent_value_supplied"] is True),
        },
        "raw_retrieval_pool_status": "unavailable",
        "entity_type_value_support_status": "requires-separately-verified-actual-content-projection",
        "samples": rows,
    }
