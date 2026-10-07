"""Paired descriptive process contrasts from root-qualified abstract input rows.

Report matched-known effects and full-roster missing-data bounds separately.
These observations neither isolate causal node effects nor alter trial selection.
"""
from .bootstrap import paired_cluster_bootstrap
from .slurp_process_metrics import aggregate_process_metrics


def _event(first, second, target):
    # Unknown endpoints remain unknown, even when a partial value could rule out
    # the event. Use the same fully observed transition population for both arms.
    return None if first is None or second is None else (first, second) == target


def _observations(row):
    draft, alarm = row["draft_entity_correct"], row["review_alarm"]
    result = {k: row.get(k) for k in ("draft_parsed", "final_parsed", "review_valid", "revised",
              "draft_entity_correct", "final_entity_correct", "draft_full_correct", "final_full_correct")}
    result.update(error_alarm_event=_event(draft, alarm, (False, True)),
                  false_alarm_event=_event(draft, alarm, (True, True)),
                  missed_error_event=_event(draft, alarm, (False, False)))
    for axis in ("entity", "full"):
        d, f = row["draft_"+axis+"_correct"], row["final_"+axis+"_correct"]
        repair, harm = _event(d, f, (False, True)), _event(d, f, (True, False))
        result[axis+"_repair_event"], result[axis+"_harm_event"] = repair, harm
        result[axis+"_net_transition"] = None if repair is None else int(repair)-int(harm)
    return result


def compare_process_rows(*, baseline, candidate, sample_ids, bootstrap):
    """Align exact unique inputs and reuse the shared paired bootstrap primitive.

    Event rates use input denominators, not policy-specific wrong-draft or revision
    denominators. Existing conditional detection/repair statistics remain separate.
    Bootstrap resampling targets the matched-known input subset for each metric;
    unknown pairs remain visible and bound its possible full-roster difference.
    No gold text, task text, sample identity or scenario labels leave this reducer.
    """
    if (not sample_ids or len(sample_ids) != len(set(sample_ids))
            or set(bootstrap) != {"n_replicates", "seed", "ci_level"}
            or type(bootstrap["seed"]) is not int
            or type(bootstrap["n_replicates"]) is not int or bootstrap["n_replicates"] <= 0
            or type(bootstrap["ci_level"]) not in (int, float) or not 0 < bootstrap["ci_level"] < 1):
        raise ValueError("unique nonempty roster and explicit bootstrap configuration required")
    maps, schemas = [], []
    for rows in (baseline, candidate):
        schemas.append(aggregate_process_metrics(rows)["schema"])
        mapping = {r["sample_id"]: r for r in rows}
        if set(mapping) != set(sample_ids):
            raise ValueError("both arms must contain every exact configured input")
        maps.append(mapping)
    if schemas[0] != schemas[1]:
        raise ValueError("paired process applicability versions must match")
    prospective = schemas[0] == "saea-slurp-process-metrics-v2"
    for sid in sample_ids:
        if any(maps[0][sid][k] != maps[1][sid][k] for k in ("scenario", "gold_empty")):
            raise ValueError("paired source strata or gold identity differ")
    observations = [{sid: _observations(m[sid]) for sid in sample_ids} for m in maps]
    metrics = {}
    for metric in observations[0][sample_ids[0]]:
        review_metric = metric in {"review_valid", "error_alarm_event", "false_alarm_event", "missed_error_event"}
        applicable = [sid for sid in sample_ids if not prospective or not review_metric
                      or all(m[sid]["review_applicable"] for m in maps)]
        known = [sid for sid in applicable if all(o[sid][metric] is not None for o in observations)]
        delta = {sid: int(observations[1][sid][metric])-int(observations[0][sid][metric]) for sid in known}
        total, unknown = sum(delta.values()), len(applicable)-len(known)
        bound = 2 if metric.endswith("_net_transition") else 1
        result = paired_cluster_bootstrap(sample_ids=known,
            statistic=lambda ids: sum(delta[sid] for sid in ids)/len(ids), **bootstrap) if known else None
        metrics[metric] = {
            "paired_known": len(known), "paired_unknown": unknown,
            "baseline_known": sum(observations[0][sid][metric] is not None for sid in applicable),
            "candidate_known": sum(observations[1][sid][metric] is not None for sid in applicable),
            "baseline_matched_mean": sum(int(observations[0][sid][metric]) for sid in known)/len(known) if known else None,
            "candidate_matched_mean": sum(int(observations[1][sid][metric]) for sid in known)/len(known) if known else None,
            "difference": result.point_estimate if result else None,
            "paired_bootstrap": result.as_json() if result else None,
            "population_missing_bounds": ([(total-bound*unknown)/len(applicable), (total+bound*unknown)/len(applicable)]
                                          if applicable else None),
        }
        if prospective:
            metrics[metric].update(applicability="applicable" if applicable else "not-applicable-by-design",
                                   excluded_by_design=len(sample_ids)-len(applicable))
    result = {"schema": "saea-paired-process-diagnostics-v1", "independent_inputs": len(sample_ids),
        "metrics": metrics, "bootstrap_config": dict(bootstrap), "causal_credit": False,
        "formal_efficacy": False, "selection_rule_changed": False,
        "semantics": {"difference": "candidate minus baseline; rates in fractions, net transitions per input",
            "denominator": "same matched-known original inputs in both arms, per metric",
            "missing_bounds": "full configured roster worst-case identification bounds, not confidence intervals",
            "intervals": "descriptive paired percentile bootstrap; no multiplicity or adaptive-selection correction",
            "limitations": "Small reused rosters and degenerate intervals do not prove stable benefit or zero uncertainty.",
            "scope": "Root-only descriptive diagnosis; caller must bind complete source READ and score custody."}}
    if prospective:
        result.update(schema="saea-paired-process-diagnostics-v2", learner_export_allowed=False)
        result["semantics"]["missing_bounds"] = (
            "Applicable paired-input worst-case bounds, not confidence intervals; intentionally absent review is excluded.")
    return result
