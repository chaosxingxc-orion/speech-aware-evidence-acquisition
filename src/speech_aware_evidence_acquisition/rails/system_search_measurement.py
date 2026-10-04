"""Opt-in measured latency selection; historical call-count frontiers stay unchanged."""
import math

from .hashing import content_hash
from .system_text_policy import require, sha

SCHEMA = "saea-system-search-measurement-v2"
OBJECTIVES = {"slu_f1": 1, "intent": 1, "reliable_completion_rate": 1,
              "mean_sample_seconds": -1, "non_first_mean_seconds": -1}


def finite(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "finite nonnegative measured values are required")
    return value


def validate_profile(profile):
    require(isinstance(profile, dict) and set(profile) == {
        "schema", "latency_scope", "schedule", "slot_count", "queue_depth",
        "minimum_reliable_completion_rate"}, "measurement profile fields differ")
    require(profile["schema"] == SCHEMA
            and profile["latency_scope"] == "sample-admission-to-settled-workflow-v1"
            and profile["schedule"] == "sequential-trajectory",
            "measurement scope or schedule is not implemented")
    require(all(type(profile[k]) is int and profile[k] > 0 for k in ("slot_count", "queue_depth")),
            "measurement geometry must be explicit")
    require(finite(profile["minimum_reliable_completion_rate"]) <= 1,
            "reliability floor must be on zero-to-one scale")
    return profile


def runtime_options(values, *, slot_count):
    """Bind opt-in measurement to the existing trajectory runner's real queue.

    Keep legacy calls unchanged when absent. The experiment owns this envelope;
    candidates cannot change it through editable policy fields.
    """
    if "system_search_measurement" not in values:
        return {}
    profile = validate_profile(values["system_search_measurement"])
    require(type(slot_count) is int and slot_count > 0
            and profile["slot_count"] == slot_count,
            "measured slot count differs from runtime geometry")
    require(profile["queue_depth"] >= slot_count,
            "measured queue depth must cover every serving slot")
    require(isinstance(values.get("native_episode"), dict),
            "measured schedule requires a native episode")
    require(not any(key in values for key in (
        "native_node_batch", "native_node_pipeline", "native_prefix_slots", "dispatch")),
        "measured sequential schedule cannot mix scheduling overrides")
    return {"slot_count": slot_count, "queue_depth": profile["queue_depth"]}


def measured_rows(document, candidate_ids, bindings, *, profile):
    """Join complete qualified feedback; never accept hand-entered latency scores.

    Source/read qualification belongs to the existing complete-family reader.
    Validate all admitted members before projecting the requested branch.
    """
    validate_profile(profile)
    require(document.get("measurement_profile") == profile,
            "feedback measurement profile differs from the prospective protocol")
    ids = [g["sample_id"] for g in document["feedback"]["groups"]]
    require(len(ids) >= 2 and len(set(ids)) == len(ids), "latency comparison needs a complete ordered cohort")
    summaries = document["summaries"]
    require(set(summaries) == set(bindings) and len(set(candidate_ids)) == len(candidate_ids)
            and set(candidate_ids) <= set(summaries), "latency family bindings differ")
    sessions, reports = set(), {}
    admission_order = None
    for cid, summary in summaries.items():
        report = summary.get("sample_timing")
        require(isinstance(report, dict) and report.get("schema") == "saea-system-sample-timing-v1"
                and report.get("content_sha256") == content_hash({
                    k: v for k, v in report.items() if k != "content_sha256"}),
                "complete pinned sample timing report required")
        require(report.get("available") is True
                and all(report.get(k) == profile[k] for k in ("slot_count", "queue_depth"))
                and len(report["samples"]) == len(ids)
                and {s["sample_id"] for s in report["samples"]} == set(ids),
                "timing cohort or scheduling envelope differs")
        current_order = [s["sample_id"] for s in report["samples"]]
        require(admission_order is None or current_order == admission_order,
                "measured family admission order differs")
        admission_order = current_order
        require(report.get("first_admitted_sample") == report["samples"][0],
                "first sample must be the actual first admission")
        values = [finite(s["elapsed_seconds"]) for s in report["samples"]]
        require([s.get("admission_index") for s in report["samples"]] == list(range(len(ids)))
                and all(s.get("status") in {"completed", "failed"} for s in report["samples"]),
                "sample timing admission or completion identities differ")
        failed = sum(s["status"] == "failed" for s in report["samples"])
        require(report.get("failed_samples") == failed
                and report.get("completed_samples") == len(ids) - failed
                and report.get("eligible_for_efficiency_comparison") is (failed == 0),
                "timing report omits failed workflows")
        for name, selected in (("all_samples", values), ("excluding_first", values[1:])):
            require(report[name]["count"] == len(selected)
                    and math.isclose(finite(report[name]["mean_seconds"]),
                        math.fsum(selected) / len(selected), abs_tol=1e-10, rel_tol=1e-12),
                    "timing aggregation does not reproduce the complete sample costs")
        session = summary.get("timing_session_sha256")
        sha(session)
        sessions.add(session)
        reports[cid] = report
    require(len(sessions) == 1, "latency comparison cannot mix serving session receipts")
    identity_fields = {"profile": profile, "sample_ids": ids, "session": next(iter(sessions))}
    if admission_order != ids:
        identity_fields["admission_order"] = admission_order
    identity = content_hash(identity_fields)
    result = []
    for cid in candidate_ids:
        summary, report = summaries[cid], reports[cid]
        row = {"candidate_id": cid, "bundle_id": bindings[cid]["bundle_id"],
               "cohort_id": content_hash(ids), "measurement_id": identity,
               "measurement_profile_sha256": content_hash(profile),
               **{k: finite(summary[k]) for k in ("slu_f1", "intent", "reliable_completion_rate")},
               "mean_sample_seconds": report["all_samples"]["mean_seconds"],
               "non_first_mean_seconds": report["excluding_first"]["mean_seconds"],
               "model_calls": summary["model_calls"], "tool_calls": summary["tool_calls"],
               "timing_report_sha256": report["content_sha256"],
               "eligible": report["eligible_for_efficiency_comparison"] is True
                    and report["failed_samples"] == 0
                    and summary["reliable_completion_rate"] >= profile["minimum_reliable_completion_rate"]}
        require(all(row[k] <= 1 for k in ("slu_f1", "intent", "reliable_completion_rate")),
                "official quality and reliability must be on zero-to-one scale")
        result.append(row)
    return result


def measured_frontier(rows, *, profile):
    validate_profile(profile)
    require(rows and len({r["measurement_id"] for r in rows}) == 1
            and len({r["cohort_id"] for r in rows}) == 1,
            "frontier needs one measured cohort and profile")
    require(len({r["bundle_id"] for r in rows}) == len(rows), "duplicate measured policy")
    for row in rows:
        require(type(row["eligible"]) is bool, "measurement eligibility must be explicit")
        require(row.get("measurement_profile_sha256") == content_hash(profile),
                "frontier measurement profile differs")
        require(all(finite(row[k]) <= 1 for k in ("slu_f1", "intent", "reliable_completion_rate")),
                "quality and reliability must be on zero-to-one scale")
        for key in OBJECTIVES:
            finite(row[key])
    eligible = [r for r in rows if r["eligible"]
                and r["reliable_completion_rate"] >= profile["minimum_reliable_completion_rate"]]
    def dominates(a, b):
        differences = [sign * (a[key] - b[key]) for key, sign in OBJECTIVES.items()]
        return all(v >= 0 for v in differences) and any(v > 0 for v in differences)
    return [dict(row) for row in eligible if not any(dominates(other, row) for other in eligible)]
