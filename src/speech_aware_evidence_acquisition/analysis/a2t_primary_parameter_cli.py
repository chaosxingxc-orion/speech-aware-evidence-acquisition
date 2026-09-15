"""Analyze pinned primary-call parameter sources without running a scorer."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import io
import json
from pathlib import Path

from .a2t_ordered_action_cli import _json, _unique_rows, _verified_bytes
from .a2t_ordered_action_sources import _selected_manifest_entry
from .a2t_primary_parameter_errors import diagnose_primary_parameters
from ..reproduction.audio2tool_official.metrics import normalize_parameters, normalize_tool_name
from ..reproduction.audio2tool_official.parse import parse_tool_call
from ..reproduction.toolcall_scoring import parse_tool_calls_text
from ..reproduction.toolcall_scoring_v2 import build_registry_defaults

ERROR_FIELDS = ("missing_keys", "extra_keys", "wrong_value_keys")


def aggregate(rows):
    """Report overlapping error kinds with explicit sample/key denominators."""
    result = {"sample_count": len(rows), "arms": {}}
    for arm in ("direct", "system"):
        diagnostics = [row[arm]["diagnostics"] for row in rows]
        result["arms"][arm] = {
            "official_tool_correct": sum(row[arm]["saved"]["tool_correct"] for row in rows),
            "official_exact": sum(row[arm]["saved"]["exact_match"] for row in rows),
            "repo_exact": sum(row[arm]["repo_exact"] for row in rows),
            "errors": {
                field: {
                    "samples": sum(bool(d[field]) for d in diagnostics),
                    "keys": sum(len(d[field]) for d in diagnostics),
                } for field in ERROR_FIELDS
            },
            "error_combinations": dict(Counter(
                "+".join(field for field in ERROR_FIELDS if d[field]) or "none"
                for d in diagnostics
            )),
            "extra_keys_matching_declared_defaults": sum(
                len(d["extra_keys_matching_declared_defaults"]) for d in diagnostics
            ),
            "wrong_keys_equal_under_repo_coercion": sum(
                len(d["wrong_keys_equal_under_repo_coercion"]) for d in diagnostics
            ),
            "parser_comparable_samples": sum(row[arm]["parser_comparable"] for row in rows),
            "parser_parameter_disagreement_samples": sum(
                row[arm]["parser_parameter_disagreement"] for row in rows
            ),
            "official_wrong_keys_matching_repo_parse": sum(
                len(row[arm]["official_wrong_keys_matching_repo_parse"]) for row in rows
            ),
            "official_missing_keys_matching_repo_parse": sum(
                len(row[arm]["official_missing_keys_matching_repo_parse"]) for row in rows
            ),
            "predicted_keys": sum(row[arm]["saved"]["param_predicted_keys"] for row in rows),
            "reference_keys": sum(row[arm]["saved"]["param_gold_keys"] for row in rows),
            "correct_keys": sum(row[arm]["saved"]["param_correct_keys"] for row in rows),
            "saved_repo_extra_keys_stripped": sum(
                row[arm]["repo_extra_keys_stripped"] for row in rows
            ),
        }
    return result


def grouped(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return {label: aggregate(group) for label, group in sorted(groups.items())}


def report(rows):
    scopes = {
        "all": rows,
        "both_primary_tools_correct": [
            r for r in rows if r["direct"]["saved"]["tool_correct"]
            and r["system"]["saved"]["tool_correct"]
        ],
        "direct_primary_tool_correct": [r for r in rows if r["direct"]["saved"]["tool_correct"]],
        "system_primary_tool_correct": [r for r in rows if r["system"]["saved"]["tool_correct"]],
        "official_exact_saves": [
            r for r in rows if r["system"]["saved"]["exact_match"]
            and not r["direct"]["saved"]["exact_match"]
        ],
        "official_exact_harms": [
            r for r in rows if r["direct"]["saved"]["exact_match"]
            and not r["system"]["saved"]["exact_match"]
        ],
    }
    result = {
        "schema": "saea-primary-parameter-attribution-v1",
        "status": "POSTHOC_DESCRIPTIVE_NO_NEW_VERDICT",
        "scopes": {label: aggregate(group) for label, group in scopes.items()},
        "by_tier": grouped(rows, "tier"),
        "by_domain": grouped(rows, "domain"),
        "by_reference_empty": grouped(rows, "reference_empty"),
        "by_ordered_candidate_coverage": grouped(rows, "ordered_candidate_coverage"),
        "both_correct_by_tier": grouped(scopes["both_primary_tools_correct"], "tier"),
        "both_correct_by_domain": grouped(scopes["both_primary_tools_correct"], "domain"),
        "top_error_keys_when_primary_correct": {},
    }
    for arm in ("direct", "system"):
        counts = Counter(
            (row["primary_reference_tool"], key, field)
            for row in scopes[arm + "_primary_tool_correct"]
            for field in ERROR_FIELDS
            for key in row[arm]["diagnostics"][field]
        )
        result["top_error_keys_when_primary_correct"][arm] = [
            {"tool": tool, "parameter": key, "error": error, "count": count}
            for (tool, key, error), count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]
    result["equal_stratum_error_sample_rates"] = {}
    for group_name in ("by_tier", "by_domain", "both_correct_by_tier", "both_correct_by_domain"):
        strata = result[group_name]
        result["equal_stratum_error_sample_rates"][group_name] = {
            arm: {
                field: sum(
                    g["arms"][arm]["errors"][field]["samples"] / g["sample_count"]
                    for g in strata.values()
                ) / len(strata) if strata else None
                for field in ERROR_FIELDS
            } for arm in ("direct", "system")
        }
    return result


def analyze(config):
    if config["schema"] != "saea-primary-parameter-read-intent-v1":
        raise ValueError("unsupported registered primary parameter read binding")
    if any(config[key] for key in (
        "gpu_launch_allowed", "runtime_knowledge_mutation_allowed", "held_configuration_mutation_allowed"
    )):
        raise ValueError("analysis-only binding required")
    sources = config["sources"]
    for binding in [*sources.values(), *config["reference_manifests"], *config["source_code"]]:
        _verified_bytes(binding)
    roster = _unique_rows(_json(sources["roster"])["items"])
    if len(roster) != config["sample_count"]:
        raise ValueError("roster count mismatch")
    ids = set(roster)
    entries = {
        Path(binding["path"]).stem: _json(binding) for binding in config["reference_manifests"]
    }
    metadata = _unique_rows(_json(sources["metadata"])["rows"])
    ordered = _unique_rows(json.loads(line) for line in _verified_bytes(sources["ordered_rows"]).splitlines())
    scores = {}
    outputs = {}
    for arm in ("direct", "system"):
        scores[arm] = {
            name: _unique_rows(view["per_sample"])
            for name, view in _json(sources[arm + "_attached_score"]).items()
            if name in ("a2t-toolcall-official", "a2t-toolcall-v2")
        }
        outputs[arm] = _unique_rows(
            json.loads(line) for line in _verified_bytes(sources[arm + "_outputs"]).splitlines()
        )
    for source in [metadata, ordered, *outputs.values(), *(s for arm in scores.values() for s in arm.values())]:
        if set(source) != ids:
            raise ValueError("analysis cohort mismatch")
    registry_rows = list(csv.DictReader(io.StringIO(_verified_bytes(sources["registry"]).decode("utf-8-sig"))))
    defaults = build_registry_defaults(registry_rows)
    rows = []
    for sid in sorted(ids):
        rr = roster[sid]
        if sid != f"{rr['tier']}:{rr['id']:06d}":
            raise ValueError("roster ID association mismatch")
        entry = _selected_manifest_entry(
            entries, sample_id=sid, tier=rr["tier"], item_id=rr["id"], query_idx=rr["query_idx"]
        )
        params = entry.get("extracted_params") or {}
        if not isinstance(params, dict):
            raise ValueError("this pinned projection requires mapping extracted_params")
        tool = entry["tool_name"]
        if tool not in defaults:
            raise ValueError("reference tool missing from registry defaults")
        row = {
            "sample_id": sid, "tier": rr["tier"], "domain": metadata[sid]["domain"],
            "primary_reference_tool": tool,
            "reference_empty": not bool(normalize_parameters(params)),
            "ordered_candidate_coverage": ordered[sid]["alignment"]["full_coverage"]["ordered_one_to_one"],
        }
        for arm in ("direct", "system"):
            saved = scores[arm]["a2t-toolcall-official"][sid]
            text = outputs[arm][sid]["text"]
            pred_tool, pred_call, pred_params = parse_tool_call(text)
            diag = diagnose_primary_parameters(pred_params, params, defaults[tool])
            if (saved["gold_tool"] != tool or saved["predicted_tool"] != pred_tool
                    or saved["predicted_tool_call"] != pred_call or saved["parsed"] != bool(pred_tool)
                    or saved["tier"] != rr["tier"]):
                raise ValueError(f"primary source mismatch: {arm} {sid}")
            checks = {
                "param_correct_keys": diag["correct_normalized_key_count"],
                "param_predicted_keys": diag["predicted_normalized_key_count"],
                "param_gold_keys": diag["reference_normalized_key_count"],
                "param_exact_match": diag["param_exact"],
                "tool_correct": normalize_tool_name(pred_tool) == normalize_tool_name(tool),
            }
            checks["exact_match"] = checks["tool_correct"] and checks["param_exact_match"]
            if any(saved[key] != value for key, value in checks.items()):
                raise ValueError(f"saved parameter facts mismatch: {arm} {sid}")
            repo_calls, _ = parse_tool_calls_text(text)
            comparable = bool(repo_calls) and normalize_tool_name(repo_calls[0].name) == normalize_tool_name(pred_tool)
            repo_norm = normalize_parameters(repo_calls[0].arguments) if comparable else {}
            official_norm = normalize_parameters(pred_params)
            reference_norm = normalize_parameters(params)
            row[arm] = {
                "diagnostics": diag,
                "saved": {key: saved[key] for key in (
                    "tool_correct", "exact_match", "param_exact_match", "param_predicted_keys",
                    "param_gold_keys", "param_correct_keys", "param_f1",
                )},
                "repo_exact": scores[arm]["a2t-toolcall-v2"][sid]["exact_match"],
                "repo_extra_keys_stripped": scores[arm]["a2t-toolcall-v2"][sid]["extra_keys_stripped"],
                "parser_comparable": comparable,
                "parser_parameter_disagreement": comparable and repo_norm != official_norm,
                "official_wrong_keys_matching_repo_parse": [
                    key for key in diag["wrong_value_keys"]
                    if comparable and key in repo_norm and repo_norm[key] == reference_norm[key]
                ],
                "official_missing_keys_matching_repo_parse": [
                    key for key in diag["missing_keys"]
                    if comparable and key in repo_norm and repo_norm[key] == reference_norm[key]
                ],
            }
        rows.append(row)
    result = report(rows)
    result["analysis_id"] = config["analysis_id"]
    result["source_binding"] = config
    result["validation"] = {"sample_count": len(rows), "saved_primary_and_parameter_facts": "ALL_MATCHED"}
    return rows, result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    rows, result = analyze(json.loads(args.config.read_text()))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, text in (
        ("rows.jsonl", "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows)),
        ("report.json", json.dumps(result, sort_keys=True, indent=2) + "\n"),
    ):
        with (args.output / name).open("x") as stream:
            stream.write(text)
    print(json.dumps({"rows": len(rows), "status": "COMPLETE", "output": str(args.output)}))


if __name__ == "__main__":
    main()
