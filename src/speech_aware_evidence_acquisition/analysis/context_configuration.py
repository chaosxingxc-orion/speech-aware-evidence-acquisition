"""Describe complete context configurations without choosing or updating a policy.

These numeric helpers grant no read authority. The source reader must qualify the
whole registered family before supplying official counts and original timing.
Reuse the shared pooled metric and paired resampler; repetitions remain distinct.
"""
from collections import Counter
from itertools import combinations
import math

from .null_calibration import pooled_f1, pooled_totals
from .paired import resampled_statistic
from ..rails.hashing import content_hash
from ..rails.system_text_policy import require

FIELDS = (("tp",), ("fp",), ("fn",))


def _number(value):
    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "matrix values must be finite nonnegative numbers")
    return value


def describe_configurations(members, *, comparisons, roster, bootstrap_draws, seed):
    """Retain every repeat and objective; pair by utterance, never by contact.

First-sample exclusion is exactly the common original admission-index-zero ID.
Latency is not reconstructed from model contacts or batch wall/count. Missing
token usage remains unknown. Report point estimates and uncertainty without a
formal promotion, no-harm or learning verdict.
    """
    require(type(bootstrap_draws) is int and bootstrap_draws > 0 and type(seed) is int,
            "valid prospectively registered resampling is required")
    require(isinstance(comparisons, list) and len(comparisons) >= 2,
            "multiple complete configurations are required")
    layouts = [pair["layout"] for pair in comparisons]
    expected = [pair[key] for pair in comparisons for key in ("primary", "aa")]
    require(len(set(layouts)) == len(layouts) and len(set(expected)) == len(expected)
            and set(members) == set(expected), "all exact configuration repeats are required")
    ids = list(roster)
    require(len(ids) >= 2 and all(sid.startswith("slurp:train:") for sid in ids),
            "complete TRAIN roster is required")
    clusters = {}
    for sid, row in roster.items():
        require(row.get("sample_id") == sid and all(isinstance(row.get(key), str) and row[key]
                for key in ("utterance_id", "stratum")), "complete stratum and utterance identity is required")
        require(clusters.setdefault(row["utterance_id"], row["stratum"]) == row["stratum"],
                "utterance crosses strata")
    times, descriptions, admission_ids = {}, {}, None
    for run, member in members.items():
        rows = member["rows"]
        require(set(rows) == set(ids), "complete member rows differ")
        for row in rows.values():
            for field in ("tp", "fp", "fn", "intent"):
                _number(row[field])
            require(row["intent"] in (0, 1), "intent must be binary")
            require(all(type(row[key]) is bool for key in ("reliable_completion", "abstained")),
                    "terminal dispositions must be boolean")
            require(isinstance(row["delivery_kind"], str) and row["delivery_kind"],
                    "terminal kind is required")
        timing = member["sample_timing"]
        require(timing.get("available") is True and type(timing.get("eligible_for_efficiency_comparison")) is bool,
                "complete original timing is required")
        samples = timing["samples"]
        ordered = [row["sample_id"] for row in samples]
        require(len(ordered) == len(ids) and set(ordered) == set(ids)
                and [row["admission_index"] for row in samples] == list(range(len(ids))),
                "timing identity or admission order differs")
        if admission_ids is None:
            admission_ids = ordered
        require(ordered == admission_ids, "first-sample identity differs across repeats")
        times[run] = {row["sample_id"]: _number(row["elapsed_seconds"]) for row in samples}
        observed = {"slu_f1": pooled_f1(rows, ids, FIELDS),
                    "intent": math.fsum(row["intent"] for row in rows.values()) / len(ids)}
        for key, value in observed.items():
            require(math.isclose(value, _number(member["official"][key]), abs_tol=1e-6, rel_tol=0),
                    "official aggregate differs from complete pooled counts")
        costs = {}
        for key in ("model_calls", "tool_calls", "prompt_tokens", "completion_tokens"):
            values = [row[key] for row in rows.values()]
            require(all(value is None or type(value) is int and value >= 0 for value in values),
                    "cost must be a nonnegative integer or explicitly unknown")
            require(key not in ("model_calls", "tool_calls") or None not in values,
                    "attributed contacts are required")
            costs[key] = None if None in values else sum(values)
        descriptions[run] = {
            **observed, **costs,
            "official_counts": dict(zip(("tp", "fp", "fn"), pooled_totals(rows, ids, FIELDS), strict=True)),
            "reliable_completion_rate": sum(row["reliable_completion"] for row in rows.values()) / len(ids),
            "abstention_rate": sum(row["abstained"] for row in rows.values()) / len(ids),
            "terminal_kinds": dict(Counter(row["delivery_kind"] for row in rows.values())),
            "all_samples_mean_seconds": math.fsum(times[run].values()) / len(ids),
            "first_admitted_sample_id": ordered[0], "first_admitted_seconds": times[run][ordered[0]],
            "remaining_samples_mean_seconds": math.fsum(times[run][sid] for sid in ordered[1:]) / (len(ids) - 1),
            "sample_timing": timing, "node_timing": member["node_timing"],
        }

    def metric(run, selected, name):
        rows = members[run]["rows"]
        if name == "slu_f1":
            return pooled_f1(rows, selected, FIELDS)
        if name == "intent":
            return math.fsum(rows[sid]["intent"] for sid in selected) / len(selected)
        return math.fsum(times[run][sid] for sid in selected) / len(selected)

    strata = []
    for label in sorted({row["stratum"] for row in roster.values()}):
        selected = [sid for sid in ids if roster[sid]["stratum"] == label]
        strata.append({"stratum": label, "n": len(selected), "members": {
            run: {"slu_f1": metric(run, selected, "slu_f1"), "intent": metric(run, selected, "intent"),
                  "official_counts": dict(zip(("tp", "fp", "fn"),
                                              pooled_totals(member["rows"], selected, FIELDS), strict=True)),
                  "reliable_completion_rate": sum(member["rows"][sid]["reliable_completion"] for sid in selected) / len(selected)}
            for run, member in members.items()}})
    pairs = [("own-repeat", pair["primary"], pair["aa"]) for pair in comparisons]
    pairs.extend((f"configuration-{repeat}", left[repeat], right[repeat])
                 for left, right in combinations(comparisons, 2) for repeat in ("primary", "aa"))
    contrasts = []
    for kind, left, right in pairs:
        metrics = {}
        for name in ("slu_f1", "intent", "all_samples_mean_seconds", "remaining_samples_mean_seconds"):
            selected = admission_ids[1:] if name == "remaining_samples_mean_seconds" else ids
            metrics[name] = resampled_statistic(
                sample_ids=selected,
                statistic=lambda chosen, name=name, left=left, right=right: (
                    metric(right, chosen, name) - metric(left, chosen, name)),
                cluster_of=lambda sid: roster[sid]["utterance_id"],
                seed=seed, n_replicates=bootstrap_draws, ci_level=0.95,
            ).as_json()
        contrasts.append({"kind": kind, "left": left, "right": right, "metrics": metrics,
                          "delta_convention": "right minus left; positive quality is better, negative seconds is faster"})
    report = {
        "schema": "saea-context-configuration-description-v1",
        "sample_count": len(ids), "cluster_count": len(clusters),
        "members": descriptions, "comparisons": contrasts, "per_stratum": strata,
        "equal_stratum": {run: {key: math.fsum(s["members"][run][key] for s in strata) / len(strata)
                                for key in ("slu_f1", "intent", "reliable_completion_rate")}
                          for run in members},
        "resampling": {"seed": seed, "bootstrap_draws": bootstrap_draws, "confidence": 0.95,
                       "unit": "Paired utterance; keep recording variants together; each repeat reported separately"},
        "efficiency_eligible": all(m["sample_timing"]["eligible_for_efficiency_comparison"] for m in members.values()),
        "selection": None, "optimizer_export": False,
        "interpretation": "Descriptive engineering comparison with inherited cache/order effects. Sampling intervals and own repeats do not prove stable benefit, formal no-harm, a global optimum or learning. Root jointly reviews business quality, reliability and sample latency. Cache reuse does not restrict node contexts.",
    }
    report["content_sha256"] = content_hash(report)
    return report
