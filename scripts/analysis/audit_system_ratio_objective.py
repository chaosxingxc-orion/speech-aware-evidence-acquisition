#!/usr/bin/env python3
"""Synthetic whole-policy objective audit; no research data or runtime selector."""
from __future__ import annotations

import argparse
from fractions import Fraction
from itertools import product
import json
import math
from pathlib import Path
import random
import sys

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.official_metric_feedback import OfficialFeedback, pooled_f1
from speech_aware_evidence_acquisition.analysis.system_feedback import write_system_feedback
from speech_aware_evidence_acquisition.analysis.system_rollout_groups import group_complete_system_sources
from speech_aware_evidence_acquisition.rails.finite_action_policy import official_utility
from speech_aware_evidence_acquisition.rails.hashing import content_hash


F0 = Fraction(3, 5)  # Synthetic reference, never the registered study baseline.


def totals(states, weights, policy):
    counts = [sum((weight * state[action][i] for state, weight, action in zip(states, weights, policy)), Fraction(0))
              for i in range(3)]
    tp, fp, fn = counts
    return 2*tp, 2*tp + fp + fn


def pooled(states, weights, policy):
    numerator, denominator = totals(states, weights, policy)
    return numerator / denominator if denominator else Fraction(0)


def choose_residual(states, reference):
    return tuple(max(range(len(state)), key=lambda i:
                     2*state[i][0] - reference*(2*state[i][0] + state[i][1] + state[i][2]))
                 for state in states)


def policies(states):
    return product(*(range(len(state)) for state in states))


def solve_ratio(states, weights, *, initial):
    """Exact finite-table fractional optimization, not estimation from trajectories."""
    if not states or len(states) != len(weights) or any(w <= 0 for w in weights) or sum(weights) != 1:
        raise ValueError("states need aligned positive population weights summing to one")
    if any(not state or any(type(x) is not int or x < 0 for counts in state for x in counts)
           or any(len(counts) != 3 for counts in state) for state in states):
        raise ValueError("synthetic actions need integer nonnegative TP/FP/FN")
    if any(len({tp+fn for tp, fp, fn in state}) != 1 for state in states):
        raise ValueError("synthetic actions must retain the same target count within state")
    min_den = sum(w*min(2*tp+fp+fn for tp, fp, fn in state) for w, state in zip(weights, states))
    if min_den <= 0:
        raise ValueError("fractional optimization requires a positive pooled denominator for every policy")
    if not 0 <= initial <= 1:
        raise ValueError("initial ratio must be between zero and one")
    reference, trace = initial, []
    limit = math.prod(len(state) for state in states) + 2
    for _ in range(limit):
        selected = choose_residual(states, reference)
        numerator, denominator = totals(states, weights, selected)
        residual = numerator - reference*denominator
        trace.append({"reference": str(reference), "policy": list(selected),
                      "numerator": str(numerator), "denominator": str(denominator),
                      "residual": str(residual), "ratio": str(numerator/denominator)})
        if residual == 0:
            return selected, trace
        reference = numerator/denominator
    raise AssertionError("exact finite policy iteration did not terminate")


def verify_shared_metric(states, weights, policy):
    rows = [OfficialFeedback(f"synthetic-{i}", float(w*tp), float(w*fp), float(w*fn), 1)
            for i, (state, w, a) in enumerate(zip(states, weights, policy))
            for tp, fp, fn in [state[a]]]
    n, d = totals(states, weights, policy)
    assert math.isclose(pooled_f1(rows), float(n/d), rel_tol=0, abs_tol=1e-12)
    score = sum(float(w)*official_utility(tp=tp, fp=fp, fn=fn, f0=float(F0))
                for state, w, a in zip(states, weights, policy) for tp, fp, fn in [state[a]])
    assert math.isclose(score, float(n-F0*d), rel_tol=0, abs_tol=1e-10)


def describe_case(states, weights):
    selected, trace = solve_ratio(states, weights, initial=F0)
    fixed = choose_residual(states, F0)
    oracle = max(policies(states), key=lambda p: pooled(states, weights, p))
    assert pooled(states, weights, selected) == pooled(states, weights, oracle)
    outcomes = []
    for policy in policies(states):
        verify_shared_metric(states, weights, policy)
        n, d = totals(states, weights, policy)
        outcomes.append({"policy": list(policy), "pooled_f1": float(n/d),
                         "exact_ratio": str(n/d), "frozen_reference_utility": float(n-F0*d)})
    return {"states": states, "population_weights": [str(w) for w in weights],
            "frozen_reference_selected_policy": list(fixed),
            "ratio_selected_policy": list(selected), "policies": outcomes,
            "iteration_trace": trace}


def group_normalization_example():
    """Exercise the existing diagnostic grouper on explicitly synthetic episodes."""
    arms = [[(0, 0, 1), (0, 0, 1), (10, 0, 0)],
            [(1, 0, 0), (1, 0, 0), (0, 0, 10)]]
    sources = []
    for action, counts in enumerate(arms):
        rows = []
        for index, (tp, fp, fn) in enumerate(counts):
            rows.append({
                "sample_id": f"synthetic-{index}",
                "trajectory_sha256": content_hash(["synthetic-episode", action, index]),
                "input_sha256": content_hash(["synthetic-input", index]),
                "normalized_answer_sha256": content_hash(["synthetic-answer", action, index]),
                "tp": tp, "fp": fp, "fn": fn, "intent_exact": 1, "format_ok": True,
                "fallback_flags": [], "role_visits": ["perception", "solver", "review", "planner"],
                "revision_reached": False, "delivery_kind": "synthetic-accepted",
                "model_contacts": 0, "tool_events": 0,
            })
        sources.append({
            "label": f"synthetic-action-{action}", "run_id": f"synthetic-run-{action}",
            "attempt_id": "synthetic-only", "feedback_sha256": content_hash(["synthetic-feedback", action]),
            "feedback_role": "construction", "split_identity_hash": content_hash("synthetic-split"),
            "model_fragment": "no-model", "session_receipt_sha256": content_hash("no-session"),
            "config_hash": content_hash(["synthetic-policy", action]),
            "ordered_sample_ids": [r["sample_id"] for r in rows], "rows": rows,
        })
    grouped = group_complete_system_sources(sources, f0=float(F0))
    result = []
    for action, counts in enumerate(arms):
        feedback = [OfficialFeedback(f"synthetic-{i}", *values, 1) for i, values in enumerate(counts)]
        members = [g["members"][action] for g in grouped["groups"]]
        result.append({"action": action, "counts": counts, "pooled_f1": pooled_f1(feedback),
                       "mean_standardized_advantage": sum(m["advantage"] for m in members)/len(members),
                       "summed_raw_utility": sum(m["utility"] for m in members)})
    return {
        "policies": result,
        "mean_advantage_selected_action": max(range(2), key=lambda a: result[a]["mean_standardized_advantage"]),
        "pooled_f1_selected_action": max(range(2), key=lambda a: result[a]["pooled_f1"]),
        "interpretation": "A hypothetical mean-of-normalized-advantages policy rule, not the upstream semantic update rule.",
    }


def run_audit():
    fixed_reference = describe_case([[(5, 0, 5), (10, 11, 0)]], [Fraction(1)])
    coupled_states = describe_case([[(5, 0, 5), (10, 11, 0)], [(0, 0, 2), (0, 1, 2)]],
                                   [Fraction(1, 2)]*2)
    empty_target = describe_case([[(0, 0, 0), (0, 2, 0)], [(2, 0, 0), (2, 0, 0)]],
                                [Fraction(1, 2)]*2)
    rng = random.Random(20260925)
    checked, disagreements, max_iterations = 0, 0, 0
    for index in range(192):
        state_count, action_count = 1+index%3, 2+index%2
        states = []
        for _ in range(state_count):
            target = rng.randint(1, 12)
            state = []
            for _ in range(action_count):
                tp = rng.randint(0, target)
                state.append((tp, rng.randint(0, 15), target-tp))
            states.append(state)
        weights = [Fraction(1, state_count)]*state_count
        selected, trace = solve_ratio(states, weights, initial=F0)
        optimum = max(pooled(states, weights, p) for p in policies(states))
        assert pooled(states, weights, selected) == optimum
        fixed = choose_residual(states, F0)
        disagreements += pooled(states, weights, fixed) < optimum
        max_iterations = max(max_iterations, len(trace))
        for policy in policies(states):
            verify_shared_metric(states, weights, policy)
            checked += 1
    report = {
        "schema": "saea-system-ratio-objective-synthetic-audit-v1",
        "source": "synthetic terminal count tables only",
        "execution_profile": "model-free-check",
        "synthetic_reference_f0": str(F0),
        "study_frozen_reward_changed": False, "runtime_application_authorized": False,
        "model_contacts_added": 0, "scorer_contacts_added": 0, "research_outcomes_read": False,
        "fixed_reference_counterexample": fixed_reference,
        "coupled_population_counterexample": coupled_states,
        "empty_target_case": empty_target,
        "group_normalization_counterexample": group_normalization_example(),
        "sweep": {"seed": 20260925, "tables": 192, "policies_checked": checked,
                  "all_ratio_optima_matched": True, "fixed_reference_nonoptimal_tables": disagreements,
                  "max_iteration_count": max_iterations,
                  "interpretation": "Synthetic sanity coverage, not a task-performance frequency or statistical estimate."},
        "method_reference": "https://pubsonline.informs.org/doi/10.1287/mnsc.13.7.492",
        "limitations": [
            "Exact known counts and fixed state occupancy, not noisy learned conditional estimates.",
            "All synthetic actions retain the same reference count and identical intent correctness.",
            "No intent-constrained policy optimization or exploration estimator is implemented.",
            "This fractional optimizer is a classical method, not a claimed algorithm invention.",
            "No dataset, model, generation, scoring or current family result is opened.",
        ],
    }
    report["content_sha256"] = content_hash(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_audit()
    digest = write_system_feedback(args.output, report)
    print(json.dumps({"output": str(args.output), "sha256": digest, "sweep": report["sweep"],
                      "runtime_application_authorized": False}))


if __name__ == "__main__":
    main()
