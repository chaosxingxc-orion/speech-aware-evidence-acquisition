"""Numeric process feedback from complete pinned diagnostics; never grants READ authority."""
from copy import deepcopy
from .slurp_process_metrics import aggregate_process_metrics, rate, _transitions
from ..rails.hashing import content_hash
from ..rails.system_text_policy import require


def _stage_rows(report, rows):
    stages = report["delivery_stages"]["rows"]
    require(len(stages) == len(rows), "complete delivery stages required")
    keys = {f"{end}_{axis}_correct" for end in ("draft", "final") for axis in ("entity", "full")}
    for stage, row in zip(stages, rows, strict=True):
        require(set(stage) == {"sample_id", "model_revision_completed", "model", "postprocessing"}
                and stage["sample_id"] == row["sample_id"]
                and type(stage["model_revision_completed"]) is bool
                and stage["model_revision_completed"] == row["revised"], "stage identity or revision differs")
        for name in ("model", "postprocessing"):
            require(set(stage[name]) == keys and all(v is None or type(v) is bool for v in stage[name].values()),
                    "only abstract stage correctness permitted")
        for axis in ("entity", "full"):
            d, f = "draft_"+axis+"_correct", "final_"+axis+"_correct"
            require(stage["model"][d] == row[d] and stage["model"][f] == stage["postprocessing"][d]
                    and stage["postprocessing"][f] == row[f], "stage endpoint custody differs")
    return stages


def _support(report, ids):
    source = report["intent_support"]
    rows = source["samples"]
    require([r["sample_id"] for r in rows] == ids, "complete ordered support roster required")
    rebuilt = {
        "gold_intent_card_in_initial_request": rate(r["gold_intent_value_supplied"] for r in rows),
        "gold_intent_in_initial_candidates": rate(r["c0_gold_covered"] for r in rows),
        "candidate_coverage_given_card": rate(r["c0_gold_covered"] for r in rows if r["gold_intent_value_supplied"] is True),
    }
    require(source["metrics"] == rebuilt, "support metrics differ from bound observations")
    return rebuilt


def project_process_feedback(report, *, config, bindings):
    """Recompute aggregates, retain every member and anonymize stratum labels.

    The caller must bind the input file to its qualified root completion receipt.
    Do not export rows, custody, references, task text, source lists or scenario names.
    Verify each original ordered source hash, then join exact unique sample identities
    to the configured roster. Aggregate statistics are order invariant; no
    cross-cohort pooling occurs.
    """
    cohorts = config["cohorts"]
    require(set(report["families"]) == {c["cohort_id"] for c in cohorts} == set(bindings),
            "all exact process cohorts required")
    output = {}
    for cohort in cohorts:
        tag, ids = cohort["cohort_id"], cohort["sample_ids"]
        members = cohort["candidate_ids"] + cohort["control_ids"]
        family = report["families"][tag]
        require(set(family) == set(members) == set(bindings[tag]), "every candidate and comparator required")
        reference_scenarios = {r["sample_id"]:r["scenario"] for r in family[members[0]]["rows"]}
        strata = {label: f"stratum-{i+1:02d}" for i, label in enumerate(sorted(set(reference_scenarios.values())))}
        projected = {}
        for mid in members:
            source = family[mid]
            rows = source["rows"]
            require(source.get("schema") == "saea-slurp-process-metrics-v1"
                    and source.get("learner_export_allowed") is not False,
                    "architecture process learner export is not admitted")
            native_ids = [r["sample_id"] for r in rows]
            require(len(native_ids) == len(set(native_ids)) == len(ids) and set(native_ids) == set(ids)
                    and {r["sample_id"]:r["scenario"] for r in rows} == reference_scenarios
                    and source["source"]["ordered_sample_ids_sha256"] == content_hash(native_ids)
                    and source["source"]["official_score_result_sha256"] == bindings[tag][mid]["score_result"]["sha256"],
                    "ordered roster, strata or official score custody differs")
            rebuilt = aggregate_process_metrics(rows)
            require(all(source.get(k) == v for k, v in rebuilt.items()), "process metrics differ from bound observations")
            stages = _stage_rows(source, rows)
            value = {"sample_count": len(ids), "is_control": mid in cohort["control_ids"],
                     "rates": rebuilt["metrics"], "transitions": rebuilt["transitions"],
                     "conditioning_unavailable": rebuilt["conditioning_unavailable"],
                     "support": _support(source, native_ids),
                     "strata": {strata[k]: v for k, v in rebuilt["by_scenario"].items()}}
            for name in ("model", "postprocessing"):
                stage_rows = [s[name] for s in stages]
                value[name+"_transitions"] = {a: _transitions(stage_rows, a) for a in ("entity", "full")}
            projected[mid] = value
        output[tag] = {"sample_count": len(ids), "members": projected}
    return deepcopy({"schema": "saea-abstract-process-feedback-v1", "cohorts": output,
        "semantics": {"causal_credit": False, "criticism_semantic_accuracy_measured": False,
                      "raw_pool_coverage_measured": False, "slot_value_support_measured": False,
                      "independent_unit": "original input, not policy trajectory or role visit",
                      "intervals": "descriptive Wilson; not paired treatment-effect intervals",
                      "priority": "business quality and reliability, then process diagnosis, then resource costs"}})


def compact_process_feedback(projected):
    """Losslessly encode repeated statistic keys once; omit no observations or rates."""
    require(projected.get("schema") == "saea-abstract-process-feedback-v1", "verified process projection required")
    result = deepcopy(projected)
    first = next(iter(next(iter(result["cohorts"].values()))["members"].values()))
    fields = list(next(iter(first["rates"].values())))
    metrics, support = list(first["rates"]), list(first["support"])
    def encode(rows, names):
        require(list(rows) == names and all(set(v) == set(fields) for v in rows.values()),
                "compact process columns must be identical")
        return [[rows[name][field] for field in fields] for name in names]
    for cohort in result["cohorts"].values():
        for member in cohort["members"].values():
            member["rates"] = encode(member["rates"], metrics)
            member["support"] = encode(member["support"], support)
            for stratum in member["strata"].values():
                stratum["metrics"] = encode(stratum["metrics"], metrics)
    result.update(schema="saea-abstract-process-feedback-compact-v1", encoding={
        "rate_fields":fields,"metric_order":metrics,"support_order":support})
    return result
