"""Reproduce the zero-contact postflight decomposition of the G5 fixed16 screen.

This script reads only already-recorded G5/G1 outputs, the committed G5 PLAN
states and family corpus, and the frozen Audio2Tool scorer-side gold.  It does
not contact a model, tool service, tokenizer, network endpoint, or audio file.
It prints one JSON document to standard output and does not write files.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from speech_aware_evidence_acquisition.reproduction.toolcall_gold import (
    expected_tool_calls_for_entry,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (
    ToolCall,
    parse_tool_calls_text,
    score_item,
)


def jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def calls_json(calls: Iterable[ToolCall]) -> list[dict[str, Any]]:
    return [{"name": call.name, "arguments": dict(call.arguments)} for call in calls]


def load_gold(public_dir: Path, sample_ids: list[str]) -> dict[str, tuple[ToolCall, ...]]:
    wanted: dict[str, set[int]] = {}
    for sample_id in sample_ids:
        tier, item_id = sample_id.split(":", 1)
        wanted.setdefault(tier, set()).add(int(item_id))
    result: dict[str, tuple[ToolCall, ...]] = {}
    for tier, ids in wanted.items():
        manifest = public_dir / f"{tier}_data" / f"{tier}.json"
        entries = json.loads(manifest.read_text(encoding="utf-8"))
        for entry in entries:
            if entry.get("id") in ids:
                sample_id = f"{tier}:{int(entry['id']):06d}"
                result[sample_id] = expected_tool_calls_for_entry(entry)
    if set(result) != set(sample_ids):
        raise RuntimeError(f"gold coverage mismatch: missing {sorted(set(sample_ids) - set(result))}")
    return result


def score_view(expected: tuple[ToolCall, ...], text: str) -> dict[str, Any]:
    predicted, parsed = parse_tool_calls_text(text)
    score = score_item(expected, predicted)
    return {
        "predicted": calls_json(predicted),
        "parsed": parsed,
        "tool_accuracy": score.tool_accuracy,
        "exact_match": score.exact_match,
        "slot_true_positives": score.slot_true_positives,
        "slot_expected_total": score.slot_expected_total,
        "slot_predicted_total": score.slot_predicted_total,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g5-outputs", type=Path, required=True)
    parser.add_argument("--plan-states", type=Path, required=True)
    parser.add_argument("--agent-trace", type=Path, required=True)
    parser.add_argument("--g1-m0-outputs", type=Path, required=True)
    parser.add_argument("--family-corpus", type=Path, required=True)
    parser.add_argument("--audio2tool-public", type=Path, required=True)
    args = parser.parse_args()

    output_rows = jsonl(args.g5_outputs)
    sample_ids = [str(row["sample_id"]) for row in output_rows]
    output_by_id = {str(row["sample_id"]): row for row in output_rows}
    plan_by_id = {str(row["sample_id"]): row for row in jsonl(args.plan_states)}
    m0_by_id = {str(row["sample_id"]): row for row in jsonl(args.g1_m0_outputs)}
    if len(sample_ids) != 16 or len(set(sample_ids)) != 16:
        raise RuntimeError("G5 output stream must contain 16 unique sample IDs")
    if set(plan_by_id) != set(sample_ids):
        raise RuntimeError("PLAN state coverage does not exactly match G5 outputs")
    if not set(sample_ids).issubset(m0_by_id):
        raise RuntimeError("G1 M0 does not cover every G5 row")

    trace_records = jsonl(args.agent_trace)
    supplied_families_by_id: dict[str, list[str]] = {}
    plan_request_sample_by_base: dict[str, str] = {}
    for record in trace_records:
        if record.get("channel") != "MODEL_REQUEST":
            continue
        payload = record.get("payload", {}).get("payload", {})
        sample_id = payload.get("sample_id")
        history = payload.get("history", [])
        if sample_id in output_by_id and any(
            turn.get("contact_id") == "g5-plan" for turn in history if isinstance(turn, dict)
        ):
            plan_request_sample_by_base[str(record["record_id"]).removesuffix("/request")] = str(
                sample_id
            )
        if sample_id not in output_by_id or not any(
            turn.get("contact_id") == "g5-execute" for turn in history if isinstance(turn, dict)
        ):
            continue
        supplied_families: list[str] = []
        for evidence in payload.get("supplied_evidence", []):
            content = evidence.get("content") if isinstance(evidence, dict) else None
            if not isinstance(content, str) or not content.startswith("{"):
                continue
            try:
                bundle = json.loads(content)
            except json.JSONDecodeError:
                continue
            if bundle.get("schema") != "saea-exhaustive-action-family-bundle-v1":
                continue
            supplied_families.extend(str(family["tag"]) for family in bundle["families"])
        supplied_families_by_id[str(sample_id)] = supplied_families
    if set(supplied_families_by_id) != set(sample_ids):
        raise RuntimeError("execute-request family supply coverage does not match G5 outputs")
    raw_plan_response_by_id: dict[str, str] = {}
    for record in trace_records:
        if record.get("channel") != "MODEL_RESPONSE":
            continue
        base = str(record.get("record_id", "")).removesuffix("/response")
        sample_id = plan_request_sample_by_base.get(base)
        text = record.get("payload", {}).get("text")
        if sample_id is not None and isinstance(text, str):
            raw_plan_response_by_id[sample_id] = text
    if set(raw_plan_response_by_id) != set(sample_ids):
        raise RuntimeError("raw PLAN response coverage does not match G5 outputs")

    family_doc = json.loads(args.family_corpus.read_text(encoding="utf-8"))
    valid_families = {family["tag"] for family in family_doc["families"]}
    family_by_tool: dict[str, str] = {}
    tools_by_family: dict[str, set[str]] = {}
    for family in family_doc["families"]:
        tag = str(family["tag"])
        tools = {str(name) for name in family["tool_names"]}
        tools_by_family[tag] = tools
        for name in tools:
            if name in family_by_tool:
                raise RuntimeError(f"tool belongs to more than one family: {name}")
            family_by_tool[name] = tag

    gold_by_id = load_gold(args.audio2tool_public, sample_ids)
    rows: list[dict[str, Any]] = []
    structural_counts: Counter[str] = Counter()
    failure_counts: Counter[str] = Counter()
    for sample_id in sample_ids:
        expected = gold_by_id[sample_id]
        g5 = score_view(expected, str(output_by_id[sample_id]["text"]))
        m0_text = m0_by_id[sample_id].get("final_response_text")
        if not isinstance(m0_text, str):
            raise RuntimeError(f"G1 M0 row has no final_response_text: {sample_id}")
        m0 = score_view(expected, m0_text)

        plan_raw = plan_by_id[sample_id]["state"]["content"]
        plan = json.loads(plan_raw)
        operations = plan.get("operations")
        if not isinstance(operations, list):
            raise RuntimeError(f"PLAN operations malformed: {sample_id}")
        plan_families = [operation.get("family") for operation in operations]
        gold_families = [family_by_tool.get(call.name) for call in expected]
        raw_plan_text = raw_plan_response_by_id[sample_id]
        raw_plan_document: dict[str, Any] | None = None
        try:
            raw_surface = raw_plan_text.strip()
            if raw_surface.startswith("```json\n") and raw_surface.endswith("\n```"):
                raw_surface = raw_surface[len("```json\n") : -len("\n```")]
            candidate = json.loads(raw_surface)
            if isinstance(candidate, dict):
                raw_plan_document = candidate
        except json.JSONDecodeError:
            pass
        raw_operations = (
            raw_plan_document.get("operations", []) if raw_plan_document is not None else []
        )
        raw_plan_families = [
            operation.get("family")
            for operation in raw_operations
            if isinstance(operation, dict)
        ]
        raw_plan_operation_tags = [
            operation.get("operation")
            for operation in raw_operations
            if isinstance(operation, dict)
        ]
        raw_plan_family_coverage = [family in raw_plan_families for family in gold_families]
        supplied_families = supplied_families_by_id[sample_id]
        supplied_tools = set().union(
            *(tools_by_family.get(str(family), set()) for family in supplied_families)
        )
        gold_tool_family_supplied = [call.name in supplied_tools for call in expected]

        schema_issues: list[str] = []
        if not operations:
            schema_issues.append("empty-operations")
        required_operation_keys = {
            "family", "operation", "values", "correction", "supersedes", "turn_refs", "role"
        }
        required_value_keys = {"label", "span"}
        for index, operation in enumerate(operations):
            if set(operation) != required_operation_keys:
                schema_issues.append(f"operation-{index}-key-set")
            if operation.get("family") not in valid_families:
                schema_issues.append(f"operation-{index}-unknown-family")
            values = operation.get("values")
            if not isinstance(values, list):
                schema_issues.append(f"operation-{index}-values-not-list")
            else:
                for value_index, value in enumerate(values):
                    if not isinstance(value, dict) or set(value) != required_value_keys:
                        schema_issues.append(f"operation-{index}-value-{value_index}-shape")

        full_family_coverage = all(gold_tool_family_supplied)
        if g5["exact_match"]:
            failure_class = "exact"
        elif not full_family_coverage:
            failure_class = "family-routing-or-plan-coverage"
        elif not g5["tool_accuracy"]:
            failure_class = "selection-within-supplied-family"
        else:
            failure_class = "argument-realization"
        failure_counts[failure_class] += 1

        if len(expected) > 1 and len(operations) == 1:
            structural_counts["multi-call-gold-collapsed-to-one-plan-operation"] += 1
        if plan.get("status") == "INVALID_FALLBACK":
            structural_counts["invalid-plan-fallback"] += 1
            if raw_plan_operation_tags and any(tag != "execute" for tag in raw_plan_operation_tags):
                structural_counts["invalid-plan-invented-operation-tag"] += 1
            if all(raw_plan_family_coverage):
                structural_counts["invalid-plan-had-full-gold-family-coverage-before-fallback"] += 1
        if sample_id.startswith("tier6_correction:") and not any(
            operation.get("correction") is True for operation in operations
        ):
            structural_counts["correction-tier-without-correction-flag"] += 1
        if sample_id.startswith("tier6_correction:") and not any(
            operation.get("supersedes") for operation in operations
        ):
            structural_counts["correction-tier-without-supersedes"] += 1
        if sample_id.startswith("tier7_multiturn:") and not any(
            any(str(ref).startswith("prior:") for ref in operation.get("turn_refs", []))
            for operation in operations
        ):
            structural_counts["multiturn-tier-without-prior-turn-reference"] += 1

        rows.append(
            {
                "sample_id": sample_id,
                "tier": sample_id.split(":", 1)[0],
                "expected": calls_json(expected),
                "gold_families": gold_families,
                "plan": plan,
                "plan_families": plan_families,
                "raw_plan_response": raw_plan_text,
                "raw_plan_families": raw_plan_families,
                "raw_plan_operation_tags": raw_plan_operation_tags,
                "raw_plan_gold_family_coverage": raw_plan_family_coverage,
                "execute_supplied_families": supplied_families,
                "plan_schema_issues": schema_issues,
                "gold_tool_family_supplied": gold_tool_family_supplied,
                "full_gold_family_coverage": full_family_coverage,
                "g5": g5,
                "g1_m0": m0,
                "g5_unregistered_tool_names": [
                    call["name"]
                    for call in g5["predicted"]
                    if call["name"] not in family_by_tool
                ],
                "failure_class": failure_class,
            }
        )

    def aggregate(prefix: str, selected_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        source_rows = rows if selected_rows is None else selected_rows
        views = [row[prefix] for row in source_rows]
        tp = sum(view["slot_true_positives"] for view in views)
        exp = sum(view["slot_expected_total"] for view in views)
        pred = sum(view["slot_predicted_total"] for view in views)
        precision = tp / pred if pred else 0.0
        recall = tp / exp if exp else 0.0
        return {
            "samples": len(views),
            "tool_correct": sum(view["tool_accuracy"] for view in views),
            "exact": sum(view["exact_match"] for view in views),
            "slot_true_positives": tp,
            "slot_expected_total": exp,
            "slot_predicted_total": pred,
            "slot_precision": precision,
            "slot_recall": recall,
            "slot_f1": (2 * precision * recall / (precision + recall)) if precision + recall else 0.0,
            "parse_successes": sum(bool(view["parsed"]) for view in views),
        }

    per_tier: dict[str, Any] = {}
    for tier in sorted({row["tier"] for row in rows}):
        tier_rows = [row for row in rows if row["tier"] == tier]
        per_tier[tier] = {
            "samples": len(tier_rows),
            "g5": aggregate("g5", tier_rows),
            "g1_m0": aggregate("g1_m0", tier_rows),
            "full_gold_family_coverage": sum(row["full_gold_family_coverage"] for row in tier_rows),
        }

    result = {
        "schema": "saea-a2t-g5-fixed16-result-analysis-v1",
        "scope": {
            "model_contacts": 0,
            "tool_service_contacts": 0,
            "network_contacts": 0,
            "audio_reads": 0,
            "inputs": "recorded G5/G1 outputs, recorded PLAN states, committed family corpus, frozen scorer-side gold",
        },
        "aggregate": {
            "g5": aggregate("g5"),
            "g1_m0_same_16": aggregate("g1_m0"),
            "full_gold_family_coverage_rows": sum(row["full_gold_family_coverage"] for row in rows),
            "failure_classes": dict(sorted(failure_counts.items())),
            "structural_counts": dict(sorted(structural_counts.items())),
            "plan_schema_issue_rows": sum(bool(row["plan_schema_issues"]) for row in rows),
            "g5_unregistered_tool_name_rows": sum(
                bool(row["g5_unregistered_tool_names"]) for row in rows
            ),
            "tool_accuracy_transitions_vs_g1_m0": {
                "improved": sum(
                    row["g5"]["tool_accuracy"] > row["g1_m0"]["tool_accuracy"] for row in rows
                ),
                "unchanged": sum(
                    row["g5"]["tool_accuracy"] == row["g1_m0"]["tool_accuracy"] for row in rows
                ),
                "regressed": sum(
                    row["g5"]["tool_accuracy"] < row["g1_m0"]["tool_accuracy"] for row in rows
                ),
            },
            "per_tier": per_tier,
        },
        "rows": rows,
    }
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))


if __name__ == "__main__":
    main()
