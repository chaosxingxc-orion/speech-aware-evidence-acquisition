"""Present complete root-read quality, process diagnostics and cost together.

This pure presentation layer neither grants READ authority nor changes learning
selection. Its caller must verify pinned files and exact complete root authority.
"""
from copy import deepcopy


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def build_process_comparison(*, recipe, business, process, timing):
    """Keep every same-cohort member and descriptive uncertainty, without cases."""
    expected = recipe["expected_members"]
    ids = recipe["sample_ids"]
    _require(ids and len(set(ids)) == len(ids), "complete unique input roster required")
    _require(business["family_id"] == recipe["family_id"], "business family differs")
    _require(process["read_id"] == business["read_authority"]["read_run_id"]
             == recipe["run_ids"]["read"], "exact complete root READ differs")
    _require(expected and set(expected) == set(business["official_summaries"])
             == set(process["members"]) == set(timing), "complete member sets differ")
    schemas = {source["schema"] for source in process["members"].values()}
    prospective = "saea-slurp-process-metrics-v2" in schemas
    _require(not prospective or schemas == {"saea-slurp-process-metrics-v2"},
             "complete prospective applicability coverage required")
    diagnostic, resources = {}, {}
    for member in expected:
        source = process["members"][member]
        rows = source["rows"]
        _require(source["sample_count"] == len(ids) == len(rows)
                 and {r["sample_id"] for r in rows} == set(ids),
                 "process roster identity or count differs")
        _require(source["claims_causal_node_credit"] is False
                 and source["claims_semantically_correct_criticism"] is False,
                 "unverified causal or criticism correctness claim")
        diagnostic[member] = {
            k: source[k] for k in (
                "metrics", "transitions", "conditioning_unavailable",
                "by_scenario", "recall_status", "statistical_scope",
            )
        }
        if prospective:
            _require(source.get("learner_export_allowed") is False,
                     "prospective architecture learner export must remain disabled")
            diagnostic[member].update({k: source[k] for k in (
                "review_applicability", "role_counts", "conditioning_not_applicable")})
        support = source.get("intent_support", {})
        diagnostic[member]["intent_support"] = {
            "metrics": support.get("metrics", {}),
            "raw_retrieval_pool_status": support.get("raw_retrieval_pool_status", "unavailable"),
            "entity_type_value_support_status": support.get("entity_type_value_support_status", "unavailable"),
        }
        diagnostic[member]["delivery_stages"] = {
            k: v for k, v in source["delivery_stages"].items() if k != "rows"
        }
        clock = timing[member]
        completed, failed = clock["completed_samples"], clock["failed_samples"]
        _require(type(completed) is int and type(failed) is int
                 and completed >= 0 and failed >= 0
                 and completed + failed == len(ids), "timing member count differs")
        resources[member] = {
            "all_mean_seconds": (clock.get("all_samples") or {}).get("mean_seconds"),
            "first_seconds": (clock.get("first_admitted_sample") or {}).get("elapsed_seconds"),
            "non_first_mean_seconds": (clock.get("excluding_first") or {}).get("mean_seconds"),
            "completed_samples": completed, "failed_samples": failed,
            "by_role": clock.get("by_role"),
            "scope": clock.get("timing_scope"),
            "cold_start_limit": clock.get("cold_start_limit"),
        }
    return deepcopy({
        "schema": "saea-business-process-cost-comparison-v2" if prospective else "saea-business-process-cost-comparison-v1",
        "family_id": recipe["family_id"], "read_id": process["read_id"],
        "members": list(expected), "unique_inputs": len(ids),
        "trajectories": len(ids) * len(expected),
        "business": {
            "official_summaries": business["official_summaries"],
            "paired_comparisons": business["branches"],
            "per_stratum": business["per_stratum"],
            "equal_stratum_macro": business["equal_stratum_macro"],
            "execution": business["execution"],
        },
        "process": diagnostic, "resources": resources,
        "adoption_decided": False, "learner_exported": False,
        "statistical_scope": "Reused paired inputs; trajectories are not independent inputs. "
        "Process Wilson intervals are descriptive, not paired policy effects. "
        "Keep registered business comparisons and A/A variability unchanged.",
    })


def _number(value, scale=1):
    return "unavailable" if value is None else f"{scale * value:.2f}"


def _rate(value):
    if not value:
        return "unavailable"
    if value.get("applicability") == "not-applicable-by-design":
        return f'not applicable by design; excluded {value["excluded_by_design"]}; unknown {value["unknown"]}'
    interval = value["ci95_wilson"]
    ci = "unavailable" if interval is None else "-".join(_number(x, 100) for x in interval) + "%"
    return (f'{value["numerator"]}/{value["denominator"]}; unknown {value["unknown"]}; '
            f'eligible {value["eligible"]}; Wilson95 {ci}')


def render_process_comparison(report):
    """Render summaries; the JSON retains full paired contrasts and strata."""
    lines = [
        "# Whole-system quality, process and cost",
        "", f'Family: {report["family_id"]}. READ: {report["read_id"]}.',
        f'{report["unique_inputs"]} unique reused inputs; {report["trajectories"]} trajectories.',
        "", "## Official business outcomes", "",
        "| Member | SLU-F1 % | Intent % | Reliable completion % |",
        "|---|---:|---:|---:|",
    ]
    for member in report["members"]:
        row = report["business"]["official_summaries"][member]
        lines.append("| " + member + " | " + " | ".join(
            _number(row[k], 100) for k in ("slu_f1", "intent", "reliable_completion_rate")
        ) + " |")
    lines += [
        "", "The JSON retains all official paired contrasts, own A/A, scenario strata",
        "and equal-stratum descriptions. This view makes no adoption decision.",
        "", "## Support and extraction", "",
        "| Member | Delivered intent card | Initial candidate coverage |",
        "|---|---|---|",
    ]
    for member in report["members"]:
        m = report["process"][member]["intent_support"]["metrics"]
        lines.append(f'| {member} | {_rate(m.get("gold_intent_card_in_initial_request"))} | '
                     f'{_rate(m.get("gold_intent_in_initial_candidates"))} |')
    lines += [
        "", "Raw retrieval pool and semantic slot support remain unavailable unless",
        "separately verified. Delivered card presence is not semantic consumption.",
        "", "## Review and revision", "",
        "| Member | Measure | Rate, missingness and uncertainty |",
        "|---|---|---|",
    ]
    for member in report["members"]:
        m = report["process"][member]["metrics"]
        for key in (
            "review_valid", "review_error_detection", "review_alarm_precision",
            "review_false_alarm", "review_miss", "handoff_visibility_given_valid_review",
            "revision_after_alarm", "entity_repair_given_revision", "entity_harm_given_revision",
        ):
            lines.append(f"| {member} | {key} | {_rate(m.get(key))} |")
    lines += ["", "The repair/harm rates above use final delivery; the stages below",
              "separate raw model changes from deterministic postprocessing.",
              "", ("## First raw answer to selected raw answer and Postprocessing"
                     if report["schema"] == "saea-business-process-cost-comparison-v2"
                     else "## Model revision and Postprocessing"), "",
              "| Member | Stage | Endpoint | Repairs | Harms | Unknown |",
              "|---|---|---|---:|---:|---:|"]
    for member in report["members"]:
        stages = report["process"][member]["delivery_stages"]
        if stages.get("model_revision_applicability") == "not-applicable-by-design":
            lines.append(f'| {member} | model revision: not applicable by design | -- | -- | -- | -- |')
        for stage in ("model_revision", "postprocessing"):
            label = ("first_raw_to_selected_raw" if stage == "model_revision"
                     and report["schema"] == "saea-business-process-cost-comparison-v2" else stage)
            for axis, values in stages[stage].items():
                lines.append(f'| {member} | {label} | {axis} | '
                             f'{values.get("wrong_to_correct", "unavailable")} | '
                             f'{values.get("correct_to_wrong", "unavailable")} | '
                             f'{values.get("unknown", "unavailable")} |')
    lines += ["", "## Latency and cost", "",
              "| Member | Mean s | First s | Non-first mean s | Model calls | Tool calls |",
              "|---|---:|---:|---:|---:|---:|"]
    for member in report["members"]:
        t, b = report["resources"][member], report["business"]["official_summaries"][member]
        lines.append(f'| {member} | {_number(t["all_mean_seconds"])} | '
                     f'{_number(t["first_seconds"])} | {_number(t["non_first_mean_seconds"])} | '
                     f'{b["model_calls"]} | {b["tool_calls"]} |')
    lines += ["", "Non-first inputs are not guaranteed warm-cache inputs. Executor completion",
              "does not establish business correctness. No causal node credit or verified",
              "semantic criticism is inferred from alarm and transition statistics.",
              "", report["statistical_scope"], ""]
    return "\n".join(lines)
