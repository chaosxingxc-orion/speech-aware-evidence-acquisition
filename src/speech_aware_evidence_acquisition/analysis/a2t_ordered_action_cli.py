"""Project sealed Audio2Tool sources into descriptive candidate-action alignment.

This analysis entry point makes no model, tokenizer, encoder or scorer calls.
Reference names stay in external analysis artifacts, never runtime knowledge.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
from pathlib import Path

from .a2t_ordered_action_sources import project_ordered_action_sources
from .candidate_action_alignment import candidate_action_alignment

LEVELS = ("union", "unordered_one_to_one", "ordered_one_to_one", "strict_one_for_one")
COUNT_FIELDS = (
    "union_coverage_count", "unordered_one_to_one_match_count",
    "ordered_one_to_one_match_count", "strict_same_position_match_count",
)
QUALITY_FIELDS = (
    "official_tool", "official_exact", "repo_ordered_tool",
    "repo_multiset_tool", "repo_exact",
)


def _verified_bytes(binding):
    path = Path(binding["path"])
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != binding["sha256"]:
        raise ValueError(f"source hash mismatch: {path}")
    return data


def _json(binding):
    return json.loads(_verified_bytes(binding))


def _unique_rows(rows):
    result = {}
    for row in rows:
        sid = row["sample_id"]
        if sid in result:
            raise ValueError(f"duplicate sample: {sid}")
        result[sid] = row
    return result


def summarize(rows):
    """Retain sample and occurrence denominators, and saved-score quality."""
    if not rows:
        raise ValueError("cannot summarize an empty partition")
    n = len(rows)
    expected = sum(row["alignment"]["reference_occurrence_count"] for row in rows)
    counts = {
        key: sum(row["alignment"][key] for row in rows)
        for key in COUNT_FIELDS
    }
    applicable = sum(row["alignment"]["reference_occurrence_count"] > 0 for row in rows)
    full = {
        level: sum(row["alignment"]["full_coverage"][level] is True for row in rows)
        for level in LEVELS
    }
    losses = {
        key: sum(row["alignment"]["descriptive_losses"][key] for row in rows)
        for key in rows[0]["alignment"]["descriptive_losses"]
    }
    quality = {
        arm: {
            metric: {
                "count": sum(row["quality"][arm][metric] for row in rows),
                "rate": sum(row["quality"][arm][metric] for row in rows) / n,
            }
            for metric in QUALITY_FIELDS
        }
        for arm in ("direct", "system")
    }
    return {
        "sample_count": n,
        "coverage_applicable_sample_count": applicable,
        "candidate_state_unavailable_count": sum(
            not row["alignment"]["candidate_state_available"] for row in rows
        ),
        "reference_occurrence_count": expected,
        "candidate_action_count": sum(
            row["alignment"]["candidate_action_count"] for row in rows
        ),
        "full_coverage_counts": full,
        "full_coverage_rates": {
            key: value / applicable if applicable else None for key, value in full.items()
        },
        "occurrence_match_counts": counts,
        "occurrence_micro_rates": {
            key: value / expected if expected else None for key, value in counts.items()
        },
        "descriptive_occurrence_losses": losses,
        "quality": quality,
        "quality_delta": {
            metric: quality["system"][metric]["rate"] - quality["direct"][metric]["rate"]
            for metric in QUALITY_FIELDS
        },
        "official_expected_count_differs": sum(
            row["official_expected_count"] != row["expanded_expected_count"] for row in rows
        ),
        "repeated_reference_names_samples": sum(
            len(row["expected_tool_names"]) != len(set(row["expected_tool_names"]))
            for row in rows
        ),
        "unknown_reference_occurrences": sum(len(row["unknown_reference_names"]) for row in rows),
        "strict_position_reference_matches": counts["strict_same_position_match_count"],
    }


def _groups(rows, field):
    groups = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {key: summarize(value) for key, value in sorted(groups.items())}


def _defined_mean(values):
    defined = [value for value in values if value is not None]
    return sum(defined) / len(defined) if defined else None


def _equal_weight(groups):
    """Mean of stratum sample rates; do not conflate it with occurrence micro."""
    n = len(groups)
    return {
        "stratum_count": n,
        "coverage_applicable_strata": {
            level: sum(g["full_coverage_rates"][level] is not None for g in groups.values())
            for level in LEVELS
        },
        "full_coverage_rates": {
            level: _defined_mean(g["full_coverage_rates"][level] for g in groups.values())
            for level in LEVELS
        },
        "quality": {
            arm: {
                metric: sum(g["quality"][arm][metric]["rate"] for g in groups.values()) / n
                for metric in QUALITY_FIELDS
            }
            for arm in ("direct", "system")
        },
    }


def build_report(rows):
    """Summarize fixed descriptive partitions without inference or new gates."""
    tier = _groups(rows, "tier")
    domain = _groups(rows, "domain")
    return {
        "schema": "saea-ordered-action-attribution-v1",
        "status": "POSTHOC_DESCRIPTIVE_NO_NEW_VERDICT",
        "natural": summarize(rows),
        "equal_tier": _equal_weight(tier),
        "equal_domain_sensitivity": _equal_weight(domain),
        "by_tier": tier,
        "by_domain": domain,
        "by_reference_count": _groups(rows, "expanded_expected_count"),
        "by_candidate_action_count": _groups(rows, "candidate_action_count"),
        "by_reference_count_class": _groups(rows, "reference_count_class"),
        "by_first_compatibility_failure": _groups(rows, "first_compatibility_failure"),
        "conditional_full_coverage": {
            level: {
                str(flag): summarize(subset)
                for flag in (True, False, None)
                if (subset := [
                    row for row in rows
                    if row["alignment"]["full_coverage"][level] is flag
                ])
            }
            for level in LEVELS
        },
        "reference_candidate_count_matrix": {
            str(key): count for key, count in sorted(Counter(
                (row["expanded_expected_count"], str(row["candidate_action_count"])) for row in rows
            ).items())
        },
        "limitations": [
            "Reference-list order is the repository scorer convention, not verified speech chronology.",
            "Full coverage tests tool-name compatibility only, not arguments or output correctness.",
            "Official metrics score the primary parsed call; repo ordered-tool and multiset-call metrics differ.",
            "Conditional outcome partitions and additive compatibility losses are descriptive, not causal.",
            "No new hypothesis test, promotion decision, runtime knowledge or prompt change is authorized.",
        ],
    }


def analyze(config):
    """Verify pinned files, join exactly the cohort, and return rows/report."""
    if config["schema"] != "saea-ordered-action-reference-read-extension-v1":
        raise ValueError("unsupported registered read binding")
    if any(config[key] for key in (
        "gpu_launch_allowed", "runtime_knowledge_mutation_allowed",
        "scope_tools_configuration_mutation_allowed",
    )):
        raise ValueError("this entry point is analysis-only")
    sources = config["sources"]
    # Verify all custody bytes before reference projection.
    for binding in [
        config["parent_intent"], *sources.values(),
        *config["reference_manifests"], *config["source_code"],
    ]:
        _verified_bytes(binding)
    roster = _json(sources["roster"])["items"]
    if len(roster) != config["sample_count"]:
        raise ValueError("roster count mismatch")
    entries = {
        Path(binding["path"]).stem: json.loads(_verified_bytes(binding))
        for binding in config["reference_manifests"]
    }
    scores = {
        arm: _json(sources[arm + "_attached_score"])
        for arm in ("direct", "system")
    }
    outputs = {
        arm: [
            json.loads(line) for line in _verified_bytes(sources[arm + "_outputs"]).splitlines()
            if line.strip()
        ]
        for arm in ("direct", "system")
    }
    rows = project_ordered_action_sources(
        roster, entries, outputs["direct"], outputs["system"],
        scores["direct"]["a2t-toolcall-official"]["per_sample"],
        scores["system"]["a2t-toolcall-official"]["per_sample"],
        scores["direct"]["a2t-toolcall-v2"]["per_sample"],
        scores["system"]["a2t-toolcall-v2"]["per_sample"],
    )
    candidates = _unique_rows(_json(sources["candidate_audit"])["samples"])
    metadata = _unique_rows(_json(sources["metadata"])["rows"])
    ids = {row["sample_id"] for row in rows}
    if ids != set(candidates) or ids != set(metadata):
        raise ValueError("candidate/metadata cohort mismatch")
    registry = {
        row["tool_name"] for row in csv.DictReader(
            io.StringIO(_verified_bytes(sources["registry"]).decode("utf-8-sig"))
        )
    }
    by_arm = {
        arm: {
            scorer: _unique_rows(scores[arm][scorer]["per_sample"])
            for scorer in ("a2t-toolcall-official", "a2t-toolcall-v2")
        } for arm in ("direct", "system")
    }
    for row in rows:
        sid = row["sample_id"]
        candidate = candidates[sid]
        if candidate["candidate_state_status"] == "observed":
            actions = [action["candidate_tools"] for action in candidate["actions"]]
        elif candidate["candidate_state_status"] == "unavailable":
            actions = None
        else:
            raise ValueError(f"unsupported candidate status: {candidate['candidate_state_status']}")
        row["candidate_actions"] = actions
        row["alignment"] = candidate_action_alignment(row["expected_tool_names"], actions)
        row["domain"] = metadata[sid]["domain"]
        if metadata[sid]["tier"] != row["tier"]:
            raise ValueError("metadata tier mismatch")
        row["candidate_action_count"] = len(actions) if actions is not None else "unavailable"
        row["unknown_reference_names"] = [
            name for name in row["expected_tool_names"] if name not in registry
        ]
        row["reference_count_class"] = (
            "multiple" if row["expanded_expected_count"] > 1
            else "single" if row["expanded_expected_count"] == 1 else "none"
        )
        row["first_compatibility_failure"] = (
            "no_reference" if not row["expanded_expected_count"]
            else "state_unavailable" if actions is None
            else next(
                (level for level in LEVELS if not row["alignment"]["full_coverage"][level]),
                "all_compatible",
            )
        )
        row["quality"] = {}
        for arm in ("direct", "system"):
            official = by_arm[arm]["a2t-toolcall-official"][sid]
            v2 = by_arm[arm]["a2t-toolcall-v2"][sid]
            row["quality"][arm] = {
                "official_tool": float(official["tool_correct"]),
                "official_exact": float(official["exact_match"]),
                "repo_ordered_tool": float(v2["tool_accuracy"]),
                "repo_multiset_tool": float(v2["tool_accuracy_multiset"]),
                "repo_exact": float(v2["exact_match"]),
            }
    report = build_report(rows)
    report["analysis_id"] = config["analysis_id"]
    report["split_identity_hash"] = config["split_identity_hash"]
    report["reference_source_binding"] = config
    report["source_validation"] = {
        "sample_count": len(rows), "primary_and_v2_crosschecks": "all passed",
        "model_calls": 0, "tokenizer_calls": 0, "encoder_calls": 0, "scorer_invocations": 0,
    }
    return rows, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    rows, report = analyze(json.loads(args.config.read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    rows_bytes = "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows).encode()
    report["projected_rows"] = {
        "path": str(args.output / "rows.jsonl"),
        "sha256": hashlib.sha256(rows_bytes).hexdigest(),
    }
    for filename, content in [
        ("rows.jsonl", rows_bytes),
        ("report.json", (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()),
    ]:
        with (args.output / filename).open("xb") as stream:
            stream.write(content)
    print(json.dumps({
        "sample_count": len(rows), "output": str(args.output),
        "report_sha256": hashlib.sha256((args.output / "report.json").read_bytes()).hexdigest(),
    }))


if __name__ == "__main__":
    main()
