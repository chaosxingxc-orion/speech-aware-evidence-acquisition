"""Root-only offline process diagnostics over already qualified complete SLURP sources.

The caller must first qualify its entire family and exact root READ. No runtime,
model, scoring job, policy selection, or optimizer export is performed here.
"""
from __future__ import annotations

import math
from collections.abc import Set
from copy import deepcopy
import re

from ..rails.hashing import content_hash
from ..rails.reward_links import SLURP_NATIVE_FIELDS

from .review_findings import analyze_slot_review_episode
from .slurp_solver_stage_attribution import build_slurp_solver_stage_attribution


BOOL_FIELDS = frozenset({
    "gold_empty", "draft_entity_correct", "final_entity_correct",
    "draft_full_correct", "final_full_correct", "review_alarm", "review_valid",
    "handoff_visible", "revised",
})
OPTIONAL_FIELDS = frozenset({"empty_false_fill", "draft_parsed", "final_parsed"})
REVIEW_FIELDS = frozenset({"review_valid", "review_alarm", "handoff_visible"})
REVIEW_METRICS = frozenset({
    "review_valid", "review_error_detection", "review_miss", "review_alarm_precision",
    "review_false_alarm", "handoff_visibility_given_valid_review", "revision_after_alarm",
    "entity_repair_given_revision", "entity_repair_after_alarm", "entity_harm_given_revision",
    "full_repair_given_revision", "full_harm_given_revision",
})


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
    if rows and "review_applicable" in rows[0]:
        # Reuse historical arithmetic only on applicable observations. Inactivity
        # is not missing instrumentation, a no-error judgment or a measured miss.
        legacy = [{k: v for k, v in r.items() if k != "review_applicable"} for r in rows]
        applicable = [r for r, original in zip(legacy, rows) if original["review_applicable"]]
        result = _metrics(legacy)
        result.update({k: v for k, v in _metrics(applicable).items() if k in REVIEW_METRICS})
        for key, value in result.items():
            included = len(applicable) if key in REVIEW_METRICS else len(rows)
            value.update(applicability="applicable" if included else "not-applicable-by-design",
                         excluded_by_design=len(rows) - included)
        return result
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
    prospective = any("review_applicable" in row for row in rows if isinstance(row, dict))
    seen = set()
    for row in rows:
        required = BOOL_FIELDS | ({"review_applicable"} if prospective else set())
        if not isinstance(row, dict) or not required <= row.keys() or not set(row) <= required | OPTIONAL_FIELDS | {"sample_id", "scenario"}:
            raise ValueError("unexpected or missing abstract diagnostic fields")
        for key in ("sample_id", "scenario"):
            if not isinstance(row.get(key), str) or not row[key]:
                raise ValueError("sample identity and scenario must be nonempty")
        if row["sample_id"] in seen:
            raise ValueError("one observation per unique input is required")
        seen.add(row["sample_id"])
        for key in required | (OPTIONAL_FIELDS & row.keys()):
            if row[key] is not None and type(row[key]) is not bool:
                raise ValueError("diagnostic flags must be bool or None")
        if prospective and (type(row["review_applicable"]) is not bool or
                (not row["review_applicable"] and
                 (any(row[k] is not None for k in REVIEW_FIELDS) or row["revised"] is not False))):
            raise ValueError("disabled review requires absent review evidence and no Solver revision")
        if row["review_valid"] is not True and row["review_alarm"] is not None:
            raise ValueError("invalid or missing review is not a positive or negative alarm")
    result = {
        "schema": "saea-slurp-process-metrics-v1", "sample_count": len(rows),
        "metrics": _metrics(rows),
        "transitions": {axis: _transitions(rows,axis) for axis in ("entity","full")},
        "conditioning_unavailable": {k: sum(r[k] is None for r in rows
            if not prospective or k not in REVIEW_FIELDS or r["review_applicable"]) for k in BOOL_FIELDS},
        "by_scenario": {s: {"sample_count": sum(r["scenario"] == s for r in rows),
                            "metrics": _metrics([r for r in rows if r["scenario"] == s])}
                        for s in sorted({r["scenario"] for r in rows})},
        "claims_causal_node_credit": False,
        "claims_semantically_correct_criticism": False,
        "statistical_scope": "descriptive single-input Wilson intervals; adaptive reused-roster evidence",
    }
    if prospective:
        result.update(schema="saea-slurp-process-metrics-v2", learner_export_allowed=False,
            conditioning_not_applicable={k: sum(not r["review_applicable"] for r in rows)
                                         if k in REVIEW_FIELDS else 0 for k in BOOL_FIELDS})
    return result


def build_slurp_process_metrics(source, *, reference_records, official_final_rows,
                               reference_binding_sha256, official_score_result_sha256,
                               legal_slot_types, intent_support_configuration=None,
                               review_applicability=None, solver_stage_statistics=False):
    """Join first-draft review and final delivery with verified saved source custody.

    Count at most one review per input: the first completed Reviewer between the
    initial Solver and its next Solver visit. Never evaluate a later review against
    the initial draft. Review detection concerns entities, the slot contract's scope.
    A finding on an erroneous draft is an episode alarm, not validated criticism.
    A registered review_applicability binding opts into v2, including on controls.
    It excludes disabled review from review denominators, retains actual activity
    counts, and disables learner export. Omission preserves the historical v1 view.
    """
    if type(solver_stage_statistics) is not bool:
        raise ValueError("solver stage persistence requires an explicit boolean")
    references = tuple(reference_records)
    audit = analyze_slot_review_episode(source, legal_slot_types=legal_slot_types,
                                       review_applicability=review_applicability)
    stage = build_slurp_solver_stage_attribution(
        source, reference_records=references, official_final_rows=official_final_rows,
        reference_binding_sha256=reference_binding_sha256,
        official_score_result_sha256=official_score_result_sha256,
    )
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
        if review_applicability is not None:
            rows[-1]["review_applicable"] = reviewed["review_applicable"]
        custody.append({"sample_id": ref.sample_id, **scored["source"],
                        "first_draft_review": review["source"] if review else None})
    report = aggregate_process_metrics(rows)
    report["delivery_stages"] = _delivery_stages(stage["samples"])
    if review_applicability is not None:
        report.update(review_applicability=audit["review_applicability"],
            role_counts={k: v for k, v in audit["counts"].items() if k.endswith(("_visits", "_contacts"))})
        report["delivery_stages"].update(
            model_revision_applicability=("applicable" if review_applicability["review_loop"] == "on"
                                          else "not-applicable-by-design"),
            model_endpoint="First raw answer to selected raw answer; the first answer is after any within-visit tools.")
    report.update(source=stage["source"], inventory_sha256=audit["inventory_sha256"],
                  rows=rows, custody=custody,
                  recall_status="unavailable-until-actual-source-projection",
                  contacts_added={"model": 0, "official_scorer": 0},
                  authorization="caller-qualified complete family and exact root READ required",
                  distribution="root-only; no automatic learner export")
    if solver_stage_statistics:
        report["solver_stage_statistics"] = project_solver_stage_statistics(stage, rows, custody)
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


def _delivery_stages(samples):
    """Separate descriptive raw-model transitions from deterministic postprocessing."""
    model_rows, post_rows, rows = [], [], []
    for sample in samples:
        metrics = sample["metrics"]
        draft, raw, final = (metrics[key] for key in ("draft", "pre_delivery", "final"))
        def correctness(value, axis):
            if value is None or (axis == "entity" and not value["parsed"]):
                return None
            return bool(value[axis+"_exact"]) if value["parsed"] else False
        model, post = {}, {}
        for axis in ("entity", "full"):
            model["draft_"+axis+"_correct"] = correctness(draft, axis)
            model["final_"+axis+"_correct"] = correctness(raw, axis)
            post["draft_"+axis+"_correct"] = correctness(raw, axis)
            post["final_"+axis+"_correct"] = correctness(final, axis)
        model_rows.append(model)
        post_rows.append(post)
        rows.append({"sample_id": sample["sample_id"],
                     "model_revision_completed": sample["revision"]["completed_solver_revision"],
                     "model": model, "postprocessing": post})
    return {
        "model_revision": {axis: _transitions(model_rows, axis) for axis in ("entity", "full")},
        "postprocessing": {axis: _transitions(post_rows, axis) for axis in ("entity", "full")},
        "postprocessing_repair_rate": rate(r["final_entity_correct"] for r in post_rows
                                            if r["draft_entity_correct"] is False),
        "postprocessing_harm_rate": rate(None if r["final_entity_correct"] is None else
                                          not r["final_entity_correct"] for r in post_rows
                                          if r["draft_entity_correct"] is True),
        "rows": rows,
        "semantics": "Initial raw Solver to selected raw Solver, then selected raw Solver to final delivery; associations, not causal credit. Unparsed entity states stay unknown.",
    }


SOLVER_STAGE_STATISTICS_DECLARATION = {
    "schema": "saea-root-solver-stage-statistics-v1",
    "root_only": True,
    "learner_export": False,
}
SOLVER_STAGE_STATISTICS_SEMANTICS = 'Diagnostic first raw Solver after within-visit tools, selected raw Solver before postprocessing, and final delivery; not all intermediate visits or causal credit. Unknown states remain explicit; fixed-N rates count unknown as zero. Saved complete official scores retain corpus authority.'
STAGE_NAMES = ("draft", "pre_delivery", "final")
STAGE_AXES = ("intent", "entity", "full")
_STAGE_METRIC_FIELDS = {"parsed", "intent_exact", "entity_exact", "full_exact",
                        "slot_f1_exact_f1", "slu_f1_diagnostic_f1", "native_fields"}
_STAGE_SOURCE_HASHES = {"phase_artifact_sha256", "reference_binding_sha256",
    "official_score_result_sha256", "config_hash", "protocol_hash",
    "split_identity_hash", "ordered_sample_ids_sha256"}
_STAGE_REVISION_FIELDS = {"solver_attempt_count", "completed_solver_visits",
    "attempted_solver_revision", "completed_solver_revision",
    "delivered_solver_revision", "response_changed"}


def validate_solver_stage_statistics_declaration(value):
    """Opt in only through an exact prospective root-only declaration."""
    if value is None:
        return False
    if (not isinstance(value, dict) or value != SOLVER_STAGE_STATISTICS_DECLARATION
            or type(value.get("root_only")) is not bool
            or type(value.get("learner_export")) is not bool):
        raise ValueError("exact root-only solver stage declaration required")
    return True


def _stage_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _stage_metrics(value, *, final=False):
    if value is None and not final:
        return
    if not isinstance(value, dict) or set(value) != _STAGE_METRIC_FIELDS:
        raise ValueError("exact numeric stage metric fields required")
    if type(value["parsed"]) is not bool or any(type(value[k+"_exact"]) is not int
            or value[k+"_exact"] not in (0, 1) for k in STAGE_AXES):
        raise ValueError("typed parse and exactness states required")
    counts = value["native_fields"]
    if not isinstance(counts, dict) or set(counts) != set(SLURP_NATIVE_FIELDS):
        raise ValueError("complete diagnostic native stage fields required")
    for number in list(counts.values()) + [value["slot_f1_exact_f1"], value["slu_f1_diagnostic_f1"]]:
        if type(number) not in (int, float) or not math.isfinite(number) or number < 0:
            raise ValueError("finite nonnegative diagnostic stage numbers required")
    if (any(counts[k] not in (0, 1) for k in ("scenario_action_exact", "scenario_exact", "action_exact"))
            or any(value[k] > 1 for k in ("slot_f1_exact_f1", "slu_f1_diagnostic_f1"))
            or value["intent_exact"] != counts["scenario_action_exact"]
            or value["entity_exact"] != int(counts["slot_f1_exact_fp"] == counts["slot_f1_exact_fn"] == 0)
            or value["full_exact"] != int(value["intent_exact"] == value["entity_exact"] == 1)):
        raise ValueError("diagnostic exactness and native counts differ")
    from ..reproduction.slurp_scoring import _prf
    for metric, prefixes in (("slot_f1_exact_f1", ("slot_f1_exact",)),
                             ("slu_f1_diagnostic_f1", ("slu_f1_word", "slu_f1_char"))):
        totals = [sum(counts[p+"_"+axis] for p in prefixes) for axis in ("tp", "fp", "fn")]
        if value[metric] != _prf(*totals)[2]:
            raise ValueError("diagnostic stage F1 differs from native counts")


def _stage_correctness(value, axis):
    if value is None or (axis == "entity" and not value["parsed"]):
        return None
    return bool(value[axis+"_exact"]) if value["parsed"] else False


def _stage_custody(custody):
    if not isinstance(custody, dict) or set(custody) != {"initial_solver", "final_delivery"}:
        raise ValueError("exact first and delivered response custody required")
    role_fields = {"status", "role_id", "visit_index", "contact_index", "agent_contact_id",
                   "request_id", "request_sha256", "response_sha256", "response_text_sha256"}
    for name, value in custody.items():
        if name == "initial_solver" and value == {"status": "missing"}:
            continue
        if not isinstance(value, dict):
            raise ValueError("stage response custody must be a mapping")
        if name == "final_delivery" and value.get("status") == "abstention":
            expected = {"status", "delivery_kind", "request_id", "request_sha256",
                        "response_sha256", "response_text_sha256"}
            if set(value) != expected or value["delivery_kind"] != "abstention":
                raise ValueError("exact abstention custody required")
        else:
            expected = role_fields | ({"delivery_kind", "delivered_text_sha256"} if name == "final_delivery" else set())
            if (not expected <= set(value) or not set(value) <= expected | ({"normalisation"} if name == "final_delivery" else set())
                    or value["status"] != "completed" or value["role_id"] != "solver"
                    or any(type(value[k]) is not int or value[k] < 0 for k in ("visit_index", "contact_index"))):
                raise ValueError("exact completed Solver custody required")
            if "normalisation" in value:
                norm = value["normalisation"]
                if (not isinstance(norm, dict) or set(norm) != {"normaliser_id", "carrier_lock_key", "input_sha256", "output_sha256"}
                        or norm["carrier_lock_key"] != "slurp"
                        or not isinstance(norm["normaliser_id"], str) or not norm["normaliser_id"]
                        or not all(_stage_hash(norm[k]) for k in ("input_sha256", "output_sha256"))):
                    raise ValueError("exact normalisation hash custody required")
                if (norm["input_sha256"] != value["response_text_sha256"]
                        or norm["output_sha256"] != value["delivered_text_sha256"]):
                    raise ValueError("normalisation input/output differs from raw/delivered hashes")
            elif name == "final_delivery" and value["response_text_sha256"] != value["delivered_text_sha256"]:
                raise ValueError("unmodified delivery must retain selected raw text hash")
        if any(not _stage_hash(v) for k, v in value.items() if k.endswith("sha256")):
            raise ValueError("exact response hashes required")
        if not isinstance(value.get("request_id"), str) or not value["request_id"]:
            raise ValueError("exact response request identity required")


def aggregate_solver_stage_statistics(observations, rows):
    """Rebuild diagnostic sufficient counts; retain fixed N and unknown states."""
    def group(selected):
        summary = {}
        for name in STAGE_NAMES:
            values = [r["metrics"][name] for r in selected]
            summary[name] = {
                "sample_count": len(selected),
                "parse": {"parsed": sum(v is not None and v["parsed"] for v in values),
                          "unparsed": sum(v is not None and not v["parsed"] for v in values),
                          "unavailable": sum(v is None for v in values)},
                "exactness": {},
                "diagnostic_native_totals": {k: math.fsum(v["native_fields"][k] for v in values if v is not None)
                                             for k in SLURP_NATIVE_FIELDS},
            }
            for axis in STAGE_AXES:
                states = [_stage_correctness(v, axis) for v in values]
                correct = sum(v is True for v in states)
                summary[name]["exactness"][axis] = {
                    "correct": correct, "known": sum(v is not None for v in states),
                    "unknown": sum(v is None for v in states), "fixed_n": len(states),
                    "fixed_n_value": correct / len(states) if states else None,
                }
        transitions = {}
        for transition, start, end in (("raw_model", "draft", "pre_delivery"),
                                        ("postprocessing", "pre_delivery", "final")):
            transitions[transition] = {}
            for axis in STAGE_AXES:
                paired = [{"draft_"+axis+"_correct": _stage_correctness(r["metrics"][start], axis),
                           "final_"+axis+"_correct": _stage_correctness(r["metrics"][end], axis)} for r in selected]
                transitions[transition][axis] = _transitions(paired, axis) | {"fixed_n": len(selected)}
        return {"sample_count": len(selected), "stages": summary, "transitions": transitions,
                "model_revision_completed": sum(r["revision"]["completed_solver_revision"] for r in selected)}
    return group(observations) | {
        "by_scenario": {scenario: group([v for v, r in zip(observations, rows, strict=True) if r["scenario"] == scenario])
                        for scenario in sorted({r["scenario"] for r in rows})},
        "review_applicability": {"applicable": sum(r.get("review_applicable") is True for r in rows),
                                 "not_applicable": sum(r.get("review_applicable") is False for r in rows),
                                 "undeclared": sum("review_applicable" not in r for r in rows)},
    }


def project_solver_stage_statistics(stage, rows, custody):
    """Persist verified numeric endpoints and hashes, never answer/reference text."""
    observations = [{"sample_id": sample["sample_id"], "metrics": deepcopy(sample["metrics"]),
                     "revision": deepcopy(sample["revision"]), "custody": deepcopy(sample["source"])}
                    for sample in stage["samples"]]
    result = {"schema": "saea-slurp-root-solver-stage-statistics-v1", "root_only": True,
              "learner_export_allowed": False, "source": deepcopy(stage["source"]),
              "rows": observations, "rows_sha256": content_hash(observations),
              "semantics": SOLVER_STAGE_STATISTICS_SEMANTICS}
    result["aggregate"] = aggregate_solver_stage_statistics(observations, rows)
    validate_solver_stage_statistics(result, rows=rows, custody=custody, source=stage["source"])
    return result


def validate_solver_stage_statistics(value, *, rows, custody, source):
    """Reject partial/tampered persisted stages before complete-family presentation."""
    fields = {"schema", "root_only", "learner_export_allowed", "source", "rows", "rows_sha256", "semantics", "aggregate"}
    if (not isinstance(value, dict) or set(value) != fields
            or value["schema"] != "saea-slurp-root-solver-stage-statistics-v1"
            or value["root_only"] is not True or value["learner_export_allowed"] is not False
            or value["semantics"] != SOLVER_STAGE_STATISTICS_SEMANTICS
            or value["source"] != source or set(source) != _STAGE_SOURCE_HASHES | {"run_id", "attempt_id"}
            or not all(_stage_hash(source[k]) for k in _STAGE_SOURCE_HASHES)
            or any(not isinstance(source[k], str) or not source[k] for k in ("run_id", "attempt_id"))):
        raise ValueError("exact root-only stage source and fields required")
    observations = value["rows"]
    ids = [r["sample_id"] for r in rows]
    if (not isinstance(observations, list) or not ids or len(set(ids)) != len(ids)
            or len(custody) != len(ids) or any(not isinstance(r, dict) for r in observations)
            or [r.get("sample_id") for r in observations] != ids
            or [r.get("sample_id") for r in custody] != ids
            or source["ordered_sample_ids_sha256"] != content_hash(ids)
            or value["rows_sha256"] != content_hash(observations)):
        raise ValueError("complete exact ordered stage roster and raw row digest required")
    for observed, row, original in zip(observations, rows, custody, strict=True):
        if not isinstance(observed, dict) or set(observed) != {"sample_id", "metrics", "revision", "custody"}:
            raise ValueError("exact numeric stage observation required")
        if (observed["custody"] != {k: original[k] for k in ("initial_solver", "final_delivery")}
                or not isinstance(observed["metrics"], dict) or set(observed["metrics"]) != set(STAGE_NAMES)):
            raise ValueError("stage endpoint custody or metric vector differs")
        _stage_custody(observed["custody"])
        for name, metrics in observed["metrics"].items():
            _stage_metrics(metrics, final=name == "final")
        revision = observed["revision"]
        if (not isinstance(revision, dict) or set(revision) != _STAGE_REVISION_FIELDS
                or any(type(revision[k]) is not int or revision[k] < 0 for k in ("solver_attempt_count", "completed_solver_visits"))
                or any(type(revision[k]) is not bool for k in ("attempted_solver_revision", "completed_solver_revision"))
                or any(revision[k] is not None and type(revision[k]) is not bool for k in ("delivered_solver_revision", "response_changed"))
                or revision["attempted_solver_revision"] != (revision["solver_attempt_count"] > 1)
                or revision["completed_solver_revision"] != (revision["completed_solver_visits"] > 1)
                or revision["completed_solver_revision"] is not row["revised"]):
            raise ValueError("typed original Solver revision states required")
        initial, delivered = (observed["custody"][k] for k in ("initial_solver", "final_delivery"))
        endpoint_hashes = {
            "draft": initial.get("response_text_sha256"),
            "pre_delivery": (delivered.get("response_text_sha256")
                             if delivered["status"] != "abstention" else None),
            "final": delivered.get("delivered_text_sha256", delivered.get("response_text_sha256")),
        }
        for start, end in (("draft", "pre_delivery"), ("pre_delivery", "final"), ("draft", "final")):
            if (endpoint_hashes[start] is not None and endpoint_hashes[start] == endpoint_hashes[end]
                    and observed["metrics"][start] != observed["metrics"][end]):
                raise ValueError("identical stage text hashes require identical numeric endpoints")
        unavailable = initial["status"] == "missing" or delivered["status"] == "abstention"
        if ((observed["metrics"]["draft"] is None) != (initial["status"] == "missing")
                or (observed["metrics"]["pre_delivery"] is None) != (delivered["status"] == "abstention")
                or revision["solver_attempt_count"] < revision["completed_solver_visits"]
                or revision["delivered_solver_revision"] != (None if unavailable else initial["visit_index"] != delivered["visit_index"])
                or revision["response_changed"] != (None if unavailable else initial["response_text_sha256"] != delivered["response_text_sha256"])):
            raise ValueError("stage availability/revision differs from exact response custody")
        for name, prefix in (("draft", "draft"), ("final", "final")):
            metrics = observed["metrics"][name]
            parsed = None if metrics is None else metrics["parsed"]
            if parsed is not row.get(prefix+"_parsed"):
                raise ValueError("stage parse state differs from bound process row")
            for axis in ("entity", "full"):
                if _stage_correctness(metrics, axis) is not row[prefix+"_"+axis+"_correct"]:
                    raise ValueError("stage correctness differs from bound process row")
    rebuilt = aggregate_solver_stage_statistics(observations, rows)
    if value["aggregate"] != rebuilt or content_hash(value["aggregate"]) != content_hash(rebuilt):
        raise ValueError("stage aggregates differ from complete numeric observations")
    return value["aggregate"]
