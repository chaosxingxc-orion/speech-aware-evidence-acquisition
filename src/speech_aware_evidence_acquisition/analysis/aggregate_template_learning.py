"""Prospective K-record learning view over already qualified private feedback.

Aggregate locally, never summarize task contents with another model. This boundary
neither reads raw artifacts nor qualifies a family or authorizes model contacts.
"""
from copy import deepcopy
import math
import statistics
from .abstract_node_feedback import ROLES, METRICS, FEEDBACK_SCHEMA
from ..rails.system_text_policy import require

PROFILE = "aggregate-template-records-v1"
BUSINESS = {"candidate_id", "bundle_id", "eligible", "is_control", "slu_f1", "intent",
    "reliable_completion_rate", "mean_sample_seconds", "non_first_mean_seconds",
    "first_sample_seconds", "model_calls", "tool_calls"}


def _stats(values):
    xs = [int(x) if type(x) is bool else x for x in values if x is not None]
    require(all(type(x) in (int, float) and math.isfinite(x) for x in xs), "finite numeric observations required")
    return [len(xs), len(values)-len(xs), math.fsum(xs) if xs else None,
            statistics.fmean(xs) if xs else None, min(xs) if xs else None, max(xs) if xs else None,
            statistics.stdev(xs) if len(xs) > 1 else None]


def _node_stats(members):
    result = {}
    for index, role in enumerate(ROLES):
        ns = [n for m in members for n in m["nodes"] if n[0] == index]
        outputs = FEEDBACK_SCHEMA["output_columns"][role]
        row = {"visits":len(ns), "samples_missing_role":sum(index in m["missing_roles"] for m in members),
            "interrupted":sum(n[2] for n in ns),
            "output_features":{key:_stats([n[3][i] for n in ns]) for i,key in enumerate(outputs) if key != "action_index"},
            "performance":{key:_stats([n[4][i] for n in ns]) for i,key in enumerate(METRICS)}}
        if role == "planner":
            row["actions"] = {name:sum(n[3][1] == i for n in ns) for i,name in enumerate(FEEDBACK_SCHEMA["planner_actions"])}
        result[role] = row
    return result


def _process(process, tag, mid, *, count, control):
    if process is None:
        return None
    require(process["schema"] == "saea-abstract-process-feedback-compact-v1", "qualified compact process feedback required")
    source = process["cohorts"][tag]["members"]
    require(mid in source, "complete process membership required")
    row = source[mid]
    require(row["sample_count"] == count and row["is_control"] is control, "process population binding differs")
    # Stratum diagnostics stay in the root report. No per-input text or records pass.
    return {k:deepcopy(row[k]) for k in ("rates", "support", "transitions", "conditioning_unavailable",
                                      "model_transitions", "postprocessing_transitions")}


def _round(view, *, iteration, disposition, process, ids, active, records, comparators, selection=None):
    cohorts = view["population"]["cohorts"]
    require(set(cohorts) == set(view["templates"]) == set(view["business_measurements"]), "exact cohort membership required")
    if process is not None:
        require(set(process["cohorts"]) == set(cohorts), "complete process cohorts required")
    observed = []
    for tag, cohort in cohorts.items():
        templates = view["templates"][tag]
        cids = [r["candidate_id"] for r in cohort["templates"]]
        require(list(templates) == cids, "complete ordered templates required")
        observed += cids
        groups = cohort["groups"]
        require(bool(groups) and all([m["candidate_id"] for m in g["members"]] == cids for g in groups),
                "complete paired inputs required")
        business = view["business_measurements"][tag]
        require(all(set(b) == BUSINESS for b in business), "only allowlisted business statistics permitted")
        by_id = {b["candidate_id"]:b for b in business}
        require(len(by_id) == len(business) and {b["candidate_id"] for b in business if not b["is_control"]} == set(cids),
                "business candidates differ")
        controls = [b for b in business if b["is_control"]]
        require(bool(controls), "source cohort comparators required")
        if process is not None:
            require(set(process["cohorts"][tag]["members"]) == set(by_id), "all process candidates and controls required")
        refs = []
        for b in controls:
            ref = f"{iteration}:{tag}:{b['candidate_id']}"
            refs.append(ref)
            comparators.append({"id":ref, "business":deepcopy(b),
                "process":_process(process, tag, b["candidate_id"], count=len(groups), control=True)})
        for pos, cid in enumerate(cids):
            template, b = templates[cid], by_id[cid]
            require(template["bundle_id"] == b["bundle_id"] == cohort["templates"][pos]["bundle_id"], "policy binding differs")
            ms = [g["members"][pos] for g in groups]
            terminals = [m["terminal"] for m in ms]
            count_keys = set().union(*(t["official_counts"] for t in terminals))
            records.append({"evaluated_iteration":iteration, "candidate_id":cid, "cohort":tag,
                "source_batch":cohort["source_batch"], "sample_order_sha256":cohort["sample_order_sha256"],
                "sample_count":len(ms), "disposition":disposition,
                "is_active_parent":template["bundle_id"] == active[cid], "template":deepcopy(template),
                "selection":deepcopy(selection),
                "business":deepcopy(b), "comparators":refs,
                "terminal":{**{key:_stats([t[key] for t in terminals]) for key in
                               ("utility", "reliable", "abstained", "intent_correct", "sample_seconds")},
                    "relative_return":_stats([m["relative_return"] for m in ms]),
                    "official_counts":{key:_stats([t["official_counts"].get(key) for t in terminals]) for key in sorted(count_keys)}},
                "node_statistics":_node_stats(ms),
                "process":_process(process, tag, cid, count=len(ms), control=False)})
    require(observed == ids, "every configured candidate must occur exactly once per round")


def aggregate_actor_view(actor):
    """Replace all per-input learning/history views with K records per observation.

    Called only after shared immutable packet validation. Earlier views remain
    unchanged unless a new prospective registration explicitly opts into PROFILE.
    N counts complete evaluated populations available in this validated lineage,
    including the initial observed population. Missing historical rounds are not
    invented. Rejected/no-change populations remain distinct even with equal bytes.
    """
    require(actor["schema"] in ("saea-partitioned-context-actor-view-v1", "saea-partitioned-context-actor-view-v2"),
            "validated partitioned actor required")
    ids = actor["candidate_order"]
    require(bool(ids) and len(ids) == len(set(ids)), "unique configured population required")
    prior = actor.get("prior_continuations", [])
    histories = list(prior)
    if "rejected_history" in actor:
        histories.append({"iteration":actor["iteration"], "rejected_history":actor["rejected_history"],
                          "process_feedback":actor["process_feedback"]})
    first = actor["iteration"]-len(histories)-1
    require(first >= 0 and [h["iteration"] for h in histories] == list(range(first+2,actor["iteration"]+1)),
            "sequential observation history required")
    result = {k:deepcopy(actor[k]) for k in ("optimizer_input_sha256", "algorithm", "iteration", "model",
        "reasoning_effort", "candidate_order", "source_budget", "runtime_admission")}
    result.update(schema="saea-aggregate-template-actor-view-v1", learner_profile=PROFILE,
        population_size=len(ids), observed_rounds=len(histories)+1, records=[], comparators=[],
        statistic_columns=["observed", "unknown", "sum", "mean", "min", "max", "sample_stddev"],
        process_encoding=deepcopy(actor["process_feedback"]["encoding"]) if histories else None,
        instructions="Propose one ordered complete template-system update per configured candidate. "
            "Each record describes one complete system over its source roster, never one input or role visit. "
            "Use only active parent templates as parents; rejected populations remain learning evidence. "
            "Prioritize official quality and reliability, then error detection/precision, repair/harm and "
            "knowledge consumption, then costs. Compare only matched source cohorts and comparators. "
            "Relative returns are descriptive, not causal credit or policy gradients. "
            "Keep fixed knowledge, data, tools, scoring and deterministic sampling. Do not request cases or sources.",
        limitations={"node_causal_credit":False, "criticism_semantic_accuracy_measured":False,
            "per_input_feedback_exported":False, "strata_retained_in_root_audit_only":True,
            "process_null_means":"not measured for that historical population",
            "dispersion":"node visits are dependent; sample_stddev is descriptive, not an uncertainty interval",
            "history_count":"N complete observed populations times configured K; no fabricated missing rounds"})
    active = {cid:t["bundle_id"] for ts in actor["templates"].values() for cid,t in ts.items()}
    base = {"templates":actor["templates"], "population":actor["feedback"], "business_measurements":actor["business_measurements"]}
    _round(base, iteration=first, disposition="active-parent-observation", process=None, ids=ids, active=active,
           records=result["records"], comparators=result["comparators"])
    for h in histories:
        require(h["process_feedback"]["encoding"] == result["process_encoding"], "process encoding changed across history")
        _round(h["rejected_history"]["observation"], iteration=h["iteration"]-1,
               disposition=h["rejected_history"]["disposition"], process=h["process_feedback"],
               ids=ids, active=active, records=result["records"], comparators=result["comparators"],
               selection={k:h["rejected_history"][k] for k in ("criterion", "utility_before", "utility_after")})
    require(len(result["records"]) == result["population_size"]*result["observed_rounds"], "N times K records required")
    return result
