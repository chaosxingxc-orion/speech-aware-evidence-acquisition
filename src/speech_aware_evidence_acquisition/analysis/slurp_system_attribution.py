"""Offline, full-population SLURP trajectory diagnostics, never a runtime policy.

Exact label/entity diagnostics at intermediate stages are not official SLU-F1.
No raw answer, filler or gold text leaves these projections.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import mean

from ..reproduction.slurp_scoring import parse_slu_response


def answer_view(text, gold):
    """Project one answer to strict diagnostics using the shared parser."""
    scenario, action, entities, parsed = parse_slu_response(text)
    wanted = Counter((item.type, item.filler) for item in gold.entities)
    observed = Counter((item.type, item.filler) for item in entities)
    tp = sum((wanted & observed).values())
    fp, fn = sum(observed.values()) - tp, sum(wanted.values()) - tp
    intent = bool(parsed and scenario == gold.scenario and action == gold.action)
    return {
        "format_ok": bool(parsed), "intent_correct": intent,
        "entity_tp": tp, "entity_fp": fp, "entity_fn": fn,
        "entity_exact": bool(parsed and fp == 0 and fn == 0),
        "task_exact": bool(intent and fp == 0 and fn == 0),
        "empty_target_emission": bool(not wanted and observed),
        "entity_types": sorted(item.type for item in entities),
        "predicted_intent": f"{scenario}_{action}" if parsed else None,
    }


def _transition(before, after, key):
    if before is None or after is None:
        return "unavailable"
    left, right = bool(before[key]), bool(after[key])
    if left == right:
        return "unchanged_correct" if left else "unchanged_wrong"
    return "repair" if right else "harm"


def describe_changes(first, last, delivered):
    """Separate reasoning revisions from deterministic delivery edits."""
    output = {}
    for label, before, after in (
        ("revision", first, last), ("delivery", last, delivered),
        ("end_to_end", first, delivered),
    ):
        for metric, key in (("intent", "intent_correct"), ("entity", "entity_exact"), ("task", "task_exact")):
            output[f"{label}_{metric}_transition"] = _transition(before, after, key)
    return output


def _summary(rows):
    count = len(rows)
    result = {
        "rows": count,
        "solver_not_reached": sum(row["solver_visits"] == 0 for row in rows),
        "revised_rows": sum(row["solver_visits"] > 1 for row in rows),
        "planner_action_counts": dict(Counter(action for row in rows for action in row["planner_actions"])),
        "candidate_coverage_rate": mean(row["candidate_covered"] for row in rows) if count else None,
        "final_intent_accuracy": mean(row["delivered"]["intent_correct"] for row in rows) if count else None,
        "final_task_exact_rate": mean(row["delivered"]["task_exact"] for row in rows) if count else None,
        "empty_target_rows": sum(row["empty_target"] for row in rows),
        "empty_target_emitting_rows": sum(row["delivered"].get("empty_target_emission", False) for row in rows),
    }
    for prefix in ("revision", "delivery", "end_to_end"):
        for kind in ("task", "intent", "entity"):
            field = f"{prefix}_{kind}_transition"
            result[field] = dict(Counter(row.get(field, "unavailable") for row in rows))
    result["final_error_groups"] = dict(Counter(row.get("final_error_group", "unavailable") for row in rows))
    return result


def summarize_rows(rows):
    """Retain terminal failures and report natural/equal-scenario diagnostics."""
    if not rows or len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("trajectory diagnostics require a nonempty unique population")
    groups = defaultdict(list)
    for row in rows:
        groups[row["scenario"]].append(row)
    summary = _summary(rows)
    summary["per_scenario"] = {key: _summary(value) for key, value in sorted(groups.items())}
    summary["equal_scenario_final_task_exact_rate"] = mean(
        item["final_task_exact_rate"] for item in summary["per_scenario"].values())
    summary["equal_scenario_final_intent_accuracy"] = mean(
        item["final_intent_accuracy"] for item in summary["per_scenario"].values())
    return summary


def cross_node_summary(rows):
    """Summarize repair reach, retained repairs and actual information delivery."""
    totals, review = Counter(), Counter()
    for row in rows:
        first, last, final = row["first"], row["last"], row["delivered"]
        revised = row["solver_visits"] > 1
        if first is not None:
            totals["first_wrong"] += not first["task_exact"]
            totals["revised_first_wrong"] += revised and not first["task_exact"]
            totals["revised_first_correct"] += revised and first["task_exact"]
        totals["final_wrong_unrevised"] += not revised and not final["task_exact"]
        for group in ("covered_intent_wrong", "uncovered_intent_wrong"):
            totals[group + "_unrevised"] += not revised and row["final_error_group"] == group
        totals["empty_fp_unrevised"] += not revised and final["empty_target_emission"]
        if first is not None and last is not None:
            for metric in ("fp", "fn"):
                before, after = first["entity_" + metric], last["entity_" + metric]
                totals["revision_entity_" + metric + "_drop"] += after < before
                totals["revision_entity_" + metric + "_rise"] += after > before
        if row["revision_task_transition"] == "repair":
            totals["revision_task_repairs"] += 1
            totals["revision_task_repairs_retained"] += final["task_exact"]
            totals["revision_task_repairs_lost"] += not final["task_exact"]
        contexts = row["role_context"]
        solver = next((item for item in contexts if item["stage"] == "solver"), None)
        reviewer = next((item for item in contexts if item["stage"] == "review"), None)
        if solver and reviewer:
            left, right = solver["contacts"][0], reviewer["contacts"][0]
            totals["review_solver_same_evidence_ids"] += left["evidence_ids"] == right["evidence_ids"]
            totals["review_solver_same_speech"] += left["speech_packet_sha256"] == right["speech_packet_sha256"]
        for visit in contexts:
            if visit["stage"] != "review":
                continue
            for contact in visit["contacts"]:
                review["review_contacts"] += 1
                review["required_task_contract_without_schema"] += contact["task_contract_call_required_without_schema"]
                review["tool_schema_exposed"] += bool(contact["tool_schema_count"])
    return {"rows": len(rows), "transitions": dict(totals), "review_context": dict(review),
            "interpretation": "Descriptive within-trajectory changes, not counterfactual effects; supplied evidence identity does not prove semantic use."}


def tool_activity_summary(rows):
    """Count verified events without mistaking attempts/results for separate calls."""
    tools = [event for row in rows for event in row["tool_events"]]
    known_calls = {(row["sample_id"], event["request_id"], event["tool_call_id"])
                   for row in rows for event in row["tool_events"]
                   if event["contact_receipt_available"]}
    return {
        "event_counts": dict(Counter(event["event"] for event in tools)),
        "rows_with_events": sum(bool(row["tool_events"]) for row in rows),
        "contacted_calls": len(known_calls),
        "rows_without_tool_events": sum(not row["tool_events"] for row in rows),
        "interpretation": "Recorded attempts/results/rejections, not inferred information gain or semantic use.",
    }


def candidate_recovery_view(trajectory, *, gold_intent, first, last, delivered):
    """Join a verified proposal to offline choices, never infer semantic use.

    Gold only classifies diagnostic coverage. It must not enter a runtime
    state, action selector, proposal or model request.
    """
    if "candidate_proposal" not in trajectory:
        return None
    projection = trajectory["candidate_proposal"]
    block = projection["receipt"]
    documents = block["proposals"]
    proposal = next(iter(documents.values())) if documents else None
    original = set(proposal["original_candidate_ids"]) if proposal else set()
    proposed = set(proposal["candidate_ids"]) if proposal else set()

    def origin(answer):
        if answer is None:
            return "unavailable"
        if proposal is None:
            return "proposal_unavailable"
        if not answer["format_ok"]:
            return "malformed"
        label = answer["predicted_intent"]
        return "original" if label in original else "added" if label in proposed else "outside"

    return {
        "receipt_sha256": projection["receipt_sha256"],
        "proposal_sha256": next(iter(documents)) if documents else None,
        "status": ("supplied" if block["contacts"] else
                   "prepared_without_response" if proposal else "not_reached"),
        "original_count": len(original) if proposal else None,
        "proposed_count": len(proposed) if proposal else None,
        "original_covered": gold_intent in original if proposal else None,
        "proposed_covered": gold_intent in proposed if proposal else None,
        "coverage_group": ("not_reached" if proposal is None else
                           "originally_covered" if gold_intent in original else
                           "newly_covered" if gold_intent in proposed else "uncovered"),
        "selected_exemplar_target_counts": dict(sorted(Counter(
            item["task_target"] for item in proposal["selected_exemplars"]
        ).items())) if proposal else None,
        "contact_counts_by_role": dict(Counter(item["role_kind"] for item in block["contacts"])),
        "prepared_without_response_count": len(block["prepared_without_response"]),
        "selection_origin": {name: origin(answer) for name, answer in
                             (("first", first), ("last", last), ("delivered", delivered))},
    }


def _candidate_summary(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["candidate_recovery"]["coverage_group"]].append(row)
    result = {
        "rows": len(rows),
        "status_counts": dict(Counter(row["candidate_recovery"]["status"] for row in rows)),
        "supplied_rows": sum(row["candidate_recovery"]["status"] == "supplied" for row in rows),
        "original_covered_rows": sum(row["candidate_recovery"]["original_covered"] is True for row in rows),
        "proposed_covered_rows": sum(row["candidate_recovery"]["proposed_covered"] is True for row in rows),
        "supplied_proposed_covered_rows": sum(
            row["candidate_recovery"]["status"] == "supplied" and
            row["candidate_recovery"]["proposed_covered"] is True for row in rows),
        "selection_origin_counts": {
            stage: dict(Counter(row["candidate_recovery"]["selection_origin"][stage] for row in rows))
            for stage in ("first", "last", "delivered")
        },
        "coverage_groups": {},
    }
    for name, group in sorted(groups.items()):
        repaired = [row for row in group if row["revision_task_transition"] == "repair"]
        result["coverage_groups"][name] = {
            "rows": len(group),
            "final_intent_correct_rows": sum(row["delivered"]["intent_correct"] for row in group),
            "final_task_exact_rows": sum(row["delivered"]["task_exact"] for row in group),
            "revised_rows": sum(row["solver_visits"] > 1 for row in group),
            "task_repairs_retained": sum(row["delivered"]["task_exact"] for row in repaired),
            "task_repairs_lost": sum(not row["delivered"]["task_exact"] for row in repaired),
            "task_harms_during_revision": sum(row["revision_task_transition"] == "harm" for row in group),
        }
    return result


def candidate_recovery_summary(rows):
    """Retain all registered rows, including unreached and prepared-only continuations."""
    if not rows or len({row["sample_id"] for row in rows}) != len(rows):
        raise ValueError("candidate diagnostics require a nonempty unique population")
    if not any("candidate_recovery" in row for row in rows):
        return None
    if not all(isinstance(row.get("candidate_recovery"), dict) for row in rows):
        raise ValueError("candidate diagnostics must cover every trajectory")
    result = _candidate_summary(rows)
    scenarios = defaultdict(list)
    for row in rows:
        scenarios[row["scenario"]].append(row)
    result["per_scenario"] = {name: _candidate_summary(group) for name, group in sorted(scenarios.items())}
    result["interpretation"] = (
        "Observed supply and within-trajectory associations, not counterfactual effects or semantic use. "
        "Coverage groups use offline labels and cannot be policy states. Counts retain prepared-only and "
        "unreached rows; preparation without a response does not prove dispatch or supply. Exact task diagnostics "
        "do not replace the official pooled terminal SLU-F1 verdict."
    )
    return result
