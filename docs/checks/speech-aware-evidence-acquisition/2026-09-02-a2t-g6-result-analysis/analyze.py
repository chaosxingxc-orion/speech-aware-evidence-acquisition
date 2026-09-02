"""Analyze sealed G6 fixed16 outputs without contacting any model or service.

The command is intentionally unusable without explicit sealed output and SCAN-state
paths.  Once invoked post-seal, it reads the frozen scorer-side gold in-process to
produce official-equivalent row scores; it does not run or mutate the official scorer.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_expected_calls,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    ToolCall,
    parse_tool_calls_text,
    score_item,
)


G6_IDS = (
    "tier1_direct:000077",
    "tier1_direct:004159",
    "tier2_parametric:001004",
    "tier2_parametric:002653",
    "tier3_multi_intent:001424",
    "tier3_multi_intent:003058",
    "tier4_implicit:000655",
    "tier4_implicit:001010",
    "tier5_needle:001458",
    "tier5_needle:004242",
    "tier6_correction:001764",
    "tier6_correction:002430",
    "tier7_multiturn:000440",
    "tier7_multiturn:001516",
    "tier8_intent_blending:000192",
    "tier8_intent_blending:000213",
)
FAMILY_COUNT = 28
SCAN_ROW_COUNT = len(G6_IDS) * FAMILY_COUNT
CONTACT_COUNT = len(G6_IDS) * (FAMILY_COUNT + 1)
TRANSPORT_ROW_COUNT = CONTACT_COUNT * 3
M0_RELPATH = Path(
    "runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/"
    "arm1-m0-outputs.jsonl"
)
M0_SHA256 = "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467"
CORPUS_RELPATH = Path(
    "knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json"
)
CORPUS_SHA256 = "92684a16e39985d3c4c6e7e6d62ac54feaa357eaa7c24c744df21950e51f95e5"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict) or not isinstance(row.get("sample_id"), str):
            raise RuntimeError(f"malformed output row {line_number} in {path}")
        sample_id = str(row["sample_id"])
        if sample_id in result:
            raise RuntimeError(f"duplicate sample {sample_id!r} in {path}")
        result[sample_id] = row
    return result


def read_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), start=1
    ):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise RuntimeError(f"malformed JSONL row {line_number} in {path}")
        rows.append(row)
    return rows


def score_row(
    row: Mapping[str, object], expected: Sequence[ToolCall]
) -> dict[str, object]:
    """Apply the unchanged parser and item scorer to one recorded response."""

    text = row.get("text", row.get("final_response_text"))
    if not isinstance(text, str):
        raise RuntimeError("output row lacks a scoreable response text field")
    predicted, parsed = parse_tool_calls_text(text)
    score = score_item(expected, predicted)
    return {
        "exact": int(score.exact_match),
        "tool": int(score.tool_accuracy),
        "slot_f1": score.slot_f1,
        "slot_true_positives": score.slot_true_positives,
        "slot_expected_total": score.slot_expected_total,
        "slot_predicted_total": score.slot_predicted_total,
        "parsed": int(parsed),
        "predicted_calls": len(predicted),
        "predicted": [
            {"name": call.name, "arguments": dict(call.arguments)}
            for call in predicted
        ],
    }


def aggregate_view(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    count = len(rows)
    exact_count = sum(int(row["exact"]) for row in rows)
    tool_count = sum(int(row["tool"]) for row in rows)
    parse_count = sum(int(row["parsed"]) for row in rows)
    true_positives = sum(int(row["slot_true_positives"]) for row in rows)
    expected_total = sum(int(row["slot_expected_total"]) for row in rows)
    predicted_total = sum(int(row["slot_predicted_total"]) for row in rows)
    precision = true_positives / predicted_total if predicted_total else 0.0
    recall = true_positives / expected_total if expected_total else 0.0
    slot_f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )
    return {
        "samples": count,
        "exact_count": exact_count,
        "exact_match": exact_count / count if count else 0.0,
        "tool_count": tool_count,
        "tool_accuracy": tool_count / count if count else 0.0,
        "parse_count": parse_count,
        "parse_failures": count - parse_count,
        "slot_true_positives": true_positives,
        "slot_expected_total": expected_total,
        "slot_predicted_total": predicted_total,
        "slot_precision": precision,
        "slot_recall": recall,
        "slot_f1": slot_f1,
    }


def paired_view(rows: Sequence[Mapping[str, object]], metric: str) -> dict[str, int]:
    values = [str(row["paired"][metric]) for row in rows]  # type: ignore[index]
    return {name: values.count(name) for name in ("win", "loss", "tie")}


def _contract_index(corpus_document: Mapping[str, object]) -> dict[str, object]:
    contracts = corpus_document.get("contracts")
    families = corpus_document.get("families")
    if not isinstance(contracts, list) or not isinstance(families, list):
        raise RuntimeError("family corpus lacks contracts or families")
    family_tags = tuple(str(family.get("tag")) for family in families if isinstance(family, dict))
    if len(family_tags) != FAMILY_COUNT or len(set(family_tags)) != FAMILY_COUNT:
        raise RuntimeError("family corpus must contain exactly 28 unique families")

    tool_to_contract: dict[str, str] = {}
    tool_to_family: dict[str, str] = {}
    legal_skeletons: dict[str, tuple[tuple[str, ...], ...]] = {}
    contract_to_tool: dict[str, str] = {}
    for contract in contracts:
        if not isinstance(contract, dict):
            raise RuntimeError("family corpus contains a malformed contract")
        contract_id = contract.get("contract_id")
        family = contract.get("family_tag")
        tool = contract.get("tool_name")
        skeletons = contract.get("legal_key_skeletons")
        if not all(isinstance(value, str) for value in (contract_id, family, tool)):
            raise RuntimeError("family contract identity is malformed")
        if family not in family_tags or tool in tool_to_contract or contract_id in contract_to_tool:
            raise RuntimeError("family contract identity is duplicate or out of family")
        if not isinstance(skeletons, list) or not all(
            isinstance(skeleton, list)
            and all(isinstance(key, str) for key in skeleton)
            for skeleton in skeletons
        ):
            raise RuntimeError(f"legal key skeletons are malformed for {tool}")
        tool_to_contract[tool] = contract_id
        contract_to_tool[contract_id] = tool
        tool_to_family[tool] = family
        legal_skeletons[tool] = tuple(tuple(skeleton) for skeleton in skeletons)
    return {
        "families": family_tags,
        "tool_to_contract": tool_to_contract,
        "tool_to_family": tool_to_family,
        "legal_skeletons": legal_skeletons,
    }


def validate_scan_rows(
    rows: Sequence[Mapping[str, object]], corpus_document: Mapping[str, object]
) -> dict[str, dict[str, dict[str, object]]]:
    """Validate the complete 448-row nonfinal SCAN seal and decode reports."""

    if len(rows) != SCAN_ROW_COUNT:
        raise RuntimeError(f"G6 scan-state stream must contain exactly {SCAN_ROW_COUNT} rows")
    index = _contract_index(corpus_document)
    family_tags = tuple(index["families"])
    tool_to_family: Mapping[str, str] = index["tool_to_family"]  # type: ignore[assignment]
    by_sample: dict[str, dict[str, dict[str, object]]] = {
        sample_id: {} for sample_id in G6_IDS
    }
    seen_contacts: set[tuple[str, str]] = set()
    for row in rows:
        sample_id = row.get("sample_id")
        contact = row.get("contact")
        report = row.get("report")
        if sample_id not in by_sample or not isinstance(contact, dict) or not isinstance(report, dict):
            raise RuntimeError("G6 scan-state row has an unknown sample or malformed payload")
        family = report.get("family_tag")
        contact_id = contact.get("contact_id")
        if not isinstance(family, str) or family not in family_tags:
            raise RuntimeError("G6 scan-state row has an unknown family")
        if not isinstance(contact_id, str):
            raise RuntimeError("G6 scan-state contact lacks an identity")
        contact_key = (str(sample_id), contact_id)
        if contact_key in seen_contacts:
            raise RuntimeError("duplicate G6 sample/contact pair")
        seen_contacts.add(contact_key)
        if family in by_sample[str(sample_id)]:
            raise RuntimeError("duplicate G6 sample/family scan")
        if (
            row.get("nonfinal") is not True
            or row.get("stage") != "SCAN"
            or contact.get("sample_id") != sample_id
            or contact.get("stage") != "SCAN"
            or contact.get("family_tag") != family
        ):
            raise RuntimeError("G6 scan-state contact binding drift")
        valid = report.get("valid")
        raw_canonical = report.get("canonical_json")
        if not isinstance(valid, bool) or not isinstance(raw_canonical, str):
            raise RuntimeError("G6 scan report seal is malformed")
        document = json.loads(raw_canonical)
        if not isinstance(document, dict):
            raise RuntimeError("G6 canonical scan report must be an object")
        applicable = document.get("applicable")
        candidates = document.get("candidates")
        if not isinstance(applicable, bool) or not isinstance(candidates, list):
            raise RuntimeError("G6 canonical scan report lacks applicability or candidates")
        nominations: list[str] = []
        for candidate in candidates:
            tool = candidate.get("tool_name") if isinstance(candidate, dict) else None
            if not isinstance(tool, str) or tool_to_family.get(tool) != family:
                raise RuntimeError("G6 scan report nominates an unregistered or cross-family tool")
            if tool in nominations:
                raise RuntimeError("G6 scan report repeats a nomination")
            nominations.append(tool)
        if (not valid and (applicable or nominations)) or (not applicable and nominations):
            raise RuntimeError("G6 scan validity, applicability, and nominations disagree")
        by_sample[str(sample_id)][family] = {
            "valid": valid,
            "status": report.get("status"),
            "applicable": applicable,
            "nominations": nominations,
            "contact_id": contact_id,
        }
    for sample_id, sample_reports in by_sample.items():
        if set(sample_reports) != set(family_tags):
            raise RuntimeError(f"G6 scan family coverage mismatch for {sample_id}")
    return by_sample


def classify_bottleneck(facts: Mapping[str, bool]) -> str:
    """Assign one preregistered-channel bottleneck using a fixed precedence."""

    if facts["exact"]:
        return "exact"
    if not facts["gold_family_valid"]:
        return "scan-invalid-gold-family"
    if not facts["gold_family_applicable"]:
        return "scan-missed-gold-family"
    if not facts["gold_tools_selected"]:
        return "scan-missed-gold-tool"
    if not facts["resolver_valid"]:
        return "resolver-invalid"
    if not facts["tool"]:
        return "resolver-selection"
    return "argument-realization"


def _transport_responses(
    rows: Sequence[Mapping[str, object]],
) -> dict[tuple[str, str], str]:
    if len(rows) != TRANSPORT_ROW_COUNT:
        raise RuntimeError(
            f"G6 transport traces must contain exactly {TRANSPORT_ROW_COUNT} rows"
        )
    by_channel: dict[str, dict[str, Mapping[str, object]]] = {
        channel: {} for channel in ("MODEL_REQUEST", "MODEL_RESPONSE", "COST")
    }
    suffixes = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "COST": "/cost",
    }
    for row in rows:
        channel = row.get("channel")
        record_id = row.get("record_id")
        if channel not in by_channel or not isinstance(record_id, str):
            raise RuntimeError("G6 transport row has an unknown channel or identity")
        suffix = suffixes[str(channel)]
        if not record_id.endswith(suffix):
            raise RuntimeError("G6 transport record suffix disagrees with its channel")
        base = record_id.removesuffix(suffix)
        if base in by_channel[str(channel)]:
            raise RuntimeError("duplicate G6 transport record")
        by_channel[str(channel)][base] = row
    bases = set(by_channel["MODEL_REQUEST"])
    if any(set(records) != bases for records in by_channel.values()) or len(bases) != CONTACT_COUNT:
        raise RuntimeError("G6 transport request/response/cost triples are incomplete")

    responses: dict[tuple[str, str], str] = {}
    for base in bases:
        request_payload = by_channel["MODEL_REQUEST"][base].get("payload")
        response_payload = by_channel["MODEL_RESPONSE"][base].get("payload")
        if not isinstance(request_payload, dict) or not isinstance(response_payload, dict):
            raise RuntimeError("G6 transport payload is malformed")
        payload = request_payload.get("payload")
        if not isinstance(payload, dict):
            raise RuntimeError("G6 transport request has no inner payload")
        sample_id = payload.get("sample_id")
        history = payload.get("history")
        if (
            sample_id not in G6_IDS
            or not isinstance(history, list)
            or not history
            or not isinstance(history[0], dict)
            or not isinstance(history[0].get("contact_id"), str)
        ):
            raise RuntimeError("G6 transport request lacks a frozen contact binding")
        contact_id = str(history[0]["contact_id"])
        text = response_payload.get("text")
        if not isinstance(text, str) or not text:
            raise RuntimeError("G6 transport response text must be nonempty")
        key = (str(sample_id), contact_id)
        if key in responses:
            raise RuntimeError("duplicate G6 sample/contact transport response")
        responses[key] = text

    expected_scan_contacts = {
        f"g6-scan-{family}" for family in _families_from_transport(responses)
    }
    for sample_id in G6_IDS:
        contacts = {contact for sample, contact in responses if sample == sample_id}
        if len(contacts) != FAMILY_COUNT + 1 or "g6-resolve" not in contacts:
            raise RuntimeError(f"G6 transport contact coverage mismatch for {sample_id}")
        if contacts - {"g6-resolve"} != expected_scan_contacts:
            raise RuntimeError(f"G6 transport family coverage mismatch for {sample_id}")
    return responses


def _families_from_transport(responses: Mapping[tuple[str, str], str]) -> tuple[str, ...]:
    prefix = "g6-scan-"
    return tuple(
        sorted(
            {
                contact.removeprefix(prefix)
                for _, contact in responses
                if contact.startswith(prefix)
            }
        )
    )


def _raw_json_document(raw: str) -> tuple[object | None, bool]:
    surface = raw.strip()
    fenced = surface.startswith("```json\n") and surface.endswith("\n```")
    diagnostic_surface = surface[len("```json\n") : -len("\n```")] if fenced else surface
    try:
        return json.loads(diagnostic_surface), fenced
    except json.JSONDecodeError:
        return None, fenced


def _raw_scan_category(
    *,
    raw: str,
    official_report: Mapping[str, object],
    family: str,
    tool_to_family: Mapping[str, str],
) -> str:
    if official_report["valid"]:
        return (
            "valid-applicable"
            if official_report["applicable"]
            else "valid-abstention"
        )
    document, fenced = _raw_json_document(raw)
    if fenced:
        return "json-code-fence"
    if not isinstance(document, dict):
        return "json-or-top-level-object-invalid"
    if document.get("ordering_evidence") == {}:
        return "ordering-evidence-object-not-list"
    required_keys = {
        "applicable",
        "candidates",
        "correction_evidence",
        "turn_evidence",
        "role_evidence",
        "ordering_evidence",
    }
    if set(document) != required_keys:
        return "scan-top-level-key-set-invalid"
    candidates = document.get("candidates")
    if not isinstance(document.get("applicable"), bool) or not isinstance(candidates, list):
        return "scan-top-level-field-type-invalid"
    evidence_fields = (
        "correction_evidence",
        "turn_evidence",
        "role_evidence",
        "ordering_evidence",
    )
    if any(not isinstance(document.get(field), list) for field in evidence_fields):
        return "scan-evidence-field-type-invalid"
    candidate_keys = {
        "tool_name",
        "speech_spans",
        "argument_bindings",
        "unresolved_required_arguments",
    }
    if any(not isinstance(candidate, dict) or set(candidate) != candidate_keys for candidate in candidates):
        return "candidate-key-set-invalid"
    names = [candidate.get("tool_name") for candidate in candidates]
    if any(not isinstance(name, str) or tool_to_family.get(name) != family for name in names):
        return "candidate-unregistered-or-cross-family"
    return "candidate-contract-or-evidence-invalid"


def build_raw_transport_diagnostic(
    *,
    transport_rows: Sequence[Mapping[str, object]],
    scan_rows: Sequence[Mapping[str, object]],
    corpus_document: Mapping[str, object],
    expected_by_id: Mapping[str, Sequence[ToolCall]],
) -> dict[str, object]:
    """Describe raw shapes and nomination ceilings without changing sealed scores."""

    index = _contract_index(corpus_document)
    scans = validate_scan_rows(scan_rows, corpus_document)
    responses = _transport_responses(transport_rows)
    families = set(index["families"])
    if set(_families_from_transport(responses)) != families:
        raise RuntimeError("transport trace families disagree with the frozen corpus")
    tool_to_family: Mapping[str, str] = index["tool_to_family"]  # type: ignore[assignment]
    registered_tools = set(tool_to_family)
    shape_counts: Counter[str] = Counter()
    raw_applicable: dict[str, set[str]] = {sample_id: set() for sample_id in G6_IDS}
    raw_nominations: dict[str, set[str]] = {sample_id: set() for sample_id in G6_IDS}
    raw_candidate_count = 0
    family_local_nomination_count = 0

    for sample_id in G6_IDS:
        for family, official_report in scans[sample_id].items():
            raw = responses[(sample_id, f"g6-scan-{family}")]
            shape_counts[
                _raw_scan_category(
                    raw=raw,
                    official_report=official_report,
                    family=family,
                    tool_to_family=tool_to_family,
                )
            ] += 1
            document, _ = _raw_json_document(raw)
            if not isinstance(document, dict):
                continue
            if document.get("applicable") is True:
                raw_applicable[sample_id].add(family)
            candidates = document.get("candidates")
            if not isinstance(candidates, list):
                continue
            raw_candidate_count += len(candidates)
            for candidate in candidates:
                name = candidate.get("tool_name") if isinstance(candidate, dict) else None
                if isinstance(name, str) and tool_to_family.get(name) == family:
                    family_local_nomination_count += 1
                    raw_nominations[sample_id].add(name)

    gold_family_rows = 0
    gold_tool_rows = 0
    ceiling_rows: list[dict[str, object]] = []
    for sample_id in G6_IDS:
        expected = expected_by_id[sample_id]
        gold_tools = {call.name for call in expected}
        if not gold_tools.issubset(registered_tools):
            raise RuntimeError("gold tool is absent from the frozen family corpus")
        gold_families = {tool_to_family[tool] for tool in gold_tools}
        family_covered = gold_families.issubset(raw_applicable[sample_id])
        tools_nominated = gold_tools.issubset(raw_nominations[sample_id])
        gold_family_rows += family_covered
        gold_tool_rows += tools_nominated
        ceiling_rows.append(
            {
                "sample_id": sample_id,
                "gold_family_applicable": family_covered,
                "gold_tool_nominated": tools_nominated,
            }
        )

    raw_call_count = 0
    raw_registered_call_count = 0
    raw_resolve_parse_count = 0
    for sample_id in G6_IDS:
        document, fenced = _raw_json_document(responses[(sample_id, "g6-resolve")])
        if fenced or not isinstance(document, list):
            continue
        raw_resolve_parse_count += 1
        for call in document:
            raw_call_count += 1
            if isinstance(call, dict) and call.get("name") in registered_tools:
                raw_registered_call_count += 1

    official_valid = sum(
        bool(report["valid"])
        for sample_reports in scans.values()
        for report in sample_reports.values()
    )
    return {
        "contacts": {"scan": SCAN_ROW_COUNT, "resolve": len(G6_IDS), "total": CONTACT_COUNT},
        "nonempty_response_texts": len(responses),
        "scan": {
            "official_valid": official_valid,
            "official_invalid_empty_fallback": SCAN_ROW_COUNT - official_valid,
            "raw_shape_counts": dict(sorted(shape_counts.items())),
            "raw_applicable_true": sum(len(rows) for rows in raw_applicable.values()),
            "raw_candidate_count": raw_candidate_count,
            "raw_registered_family_local_nominations": family_local_nomination_count,
        },
        "resolve": {
            "raw_json_array_rows": raw_resolve_parse_count,
            "raw_call_count": raw_call_count,
            "raw_registered_call_count": raw_registered_call_count,
            "raw_unregistered_call_count": raw_call_count - raw_registered_call_count,
        },
        "diagnostic_ceiling": {
            "gold_family_applicable_rows": gold_family_rows,
            "gold_tool_nominated_rows": gold_tool_rows,
            "rows": ceiling_rows,
        },
        "scope_note": (
            "Diagnostic only: raw-shape recovery does not alter official G6 outputs, "
            "scores, validity, or make a counterfactual end-to-end claim."
        ),
    }


def _resolver_valid(
    score: Mapping[str, object],
    nominated_tools: set[str],
    legal_skeletons: Mapping[str, tuple[tuple[str, ...], ...]],
) -> bool:
    predicted = score["predicted"]
    if not score["parsed"] or not isinstance(predicted, list) or not predicted:
        return False
    names: list[str] = []
    for call in predicted:
        if not isinstance(call, dict):
            return False
        name = call.get("name")
        arguments = call.get("arguments")
        if (
            not isinstance(name, str)
            or name not in nominated_tools
            or name not in legal_skeletons
            or not isinstance(arguments, dict)
            or tuple(arguments) not in legal_skeletons[name]
            or name in names
        ):
            return False
        names.append(name)
    return True


def _outcome(left: float, right: float) -> str:
    return "win" if right > left else "loss" if right < left else "tie"


def build_analysis(
    *,
    g6_rows: Mapping[str, Mapping[str, object]],
    m0_rows: Mapping[str, Mapping[str, object]],
    expected_by_id: Mapping[str, Sequence[ToolCall]],
    scan_rows: Sequence[Mapping[str, object]],
    corpus_document: Mapping[str, object],
    sources: Mapping[str, object],
) -> dict[str, object]:
    """Build the deterministic result document from already-sealed inputs."""

    roster = set(G6_IDS)
    if set(g6_rows) != roster:
        raise RuntimeError("G6 outputs do not cover exactly the frozen fixed16 roster")
    if not roster.issubset(m0_rows):
        raise RuntimeError("frozen G1 M0 does not cover G6 fixed16")
    if not roster.issubset(expected_by_id):
        raise RuntimeError("scorer-side gold does not cover G6 fixed16")
    index = _contract_index(corpus_document)
    scans = validate_scan_rows(scan_rows, corpus_document)
    tool_to_family: Mapping[str, str] = index["tool_to_family"]  # type: ignore[assignment]
    tool_to_contract: Mapping[str, str] = index["tool_to_contract"]  # type: ignore[assignment]
    legal_skeletons: Mapping[str, tuple[tuple[str, ...], ...]] = index["legal_skeletons"]  # type: ignore[assignment]

    result_rows: list[dict[str, object]] = []
    for sample_id in G6_IDS:
        expected = expected_by_id[sample_id]
        gold_tools = [call.name for call in expected]
        missing_tools = [tool for tool in gold_tools if tool not in tool_to_family]
        if missing_tools:
            raise RuntimeError(f"gold tools are absent from the frozen corpus: {missing_tools}")
        gold_families = list(dict.fromkeys(tool_to_family[tool] for tool in gold_tools))
        gold_contracts = [tool_to_contract[tool] for tool in gold_tools]
        sample_scans = scans[sample_id]
        nominated_tools = {
            tool
            for report in sample_scans.values()
            for tool in report["nominations"]  # type: ignore[union-attr]
        }
        selected_contracts = {tool_to_contract[tool] for tool in nominated_tools}
        g6_score = score_row(g6_rows[sample_id], expected)
        m0_score = score_row(m0_rows[sample_id], expected)
        gold_family_valid = all(bool(sample_scans[family]["valid"]) for family in gold_families)
        gold_family_applicable = all(
            bool(sample_scans[family]["valid"] and sample_scans[family]["applicable"])
            for family in gold_families
        )
        gold_tools_nominated = [tool in nominated_tools for tool in gold_tools]
        gold_contracts_selected = [contract in selected_contracts for contract in gold_contracts]
        resolver_valid = _resolver_valid(g6_score, nominated_tools, legal_skeletons)
        facts = {
            "exact": bool(g6_score["exact"]),
            "tool": bool(g6_score["tool"]),
            "gold_family_valid": gold_family_valid,
            "gold_family_applicable": gold_family_applicable,
            "gold_tools_selected": all(gold_tools_nominated),
            "resolver_valid": resolver_valid,
        }
        result_rows.append(
            {
                "sample_id": sample_id,
                "tier": sample_id.split(":", 1)[0],
                "expected": [
                    {"name": call.name, "arguments": dict(call.arguments)}
                    for call in expected
                ],
                "gold_families": gold_families,
                "gold_contracts": gold_contracts,
                "scan": {
                    "total": FAMILY_COUNT,
                    "valid": sum(bool(report["valid"]) for report in sample_scans.values()),
                    "applicable": sum(
                        bool(report["valid"] and report["applicable"])
                        for report in sample_scans.values()
                    ),
                    "nominations": sum(
                        len(report["nominations"]) for report in sample_scans.values()  # type: ignore[arg-type]
                    ),
                    "nominated_tools": sorted(nominated_tools),
                    "selected_contract_ids": sorted(selected_contracts),
                },
                "gold_family_valid": gold_family_valid,
                "gold_family_applicable": gold_family_applicable,
                "gold_tools_nominated": gold_tools_nominated,
                "gold_contracts_selected": gold_contracts_selected,
                "resolver_valid": resolver_valid,
                "g6": g6_score,
                "g1_m0": m0_score,
                "paired": {
                    "exact": _outcome(float(m0_score["exact"]), float(g6_score["exact"])),
                    "tool": _outcome(float(m0_score["tool"]), float(g6_score["tool"])),
                    "slot_f1": _outcome(
                        float(m0_score["slot_f1"]), float(g6_score["slot_f1"])
                    ),
                },
                "bottleneck": classify_bottleneck(facts),
            }
        )

    def summarize(selected: Sequence[Mapping[str, object]]) -> dict[str, object]:
        scan_total = sum(int(row["scan"]["total"]) for row in selected)  # type: ignore[index]
        scan_valid = sum(int(row["scan"]["valid"]) for row in selected)  # type: ignore[index]
        return {
            "samples": len(selected),
            "g6": aggregate_view([row["g6"] for row in selected]),  # type: ignore[list-item]
            "g1_m0": aggregate_view([row["g1_m0"] for row in selected]),  # type: ignore[list-item]
            "paired_exact": paired_view(selected, "exact"),
            "paired_tool": paired_view(selected, "tool"),
            "paired_slot_f1": paired_view(selected, "slot_f1"),
            "scan": {
                "total": scan_total,
                "valid": scan_valid,
                "invalid": scan_total - scan_valid,
                "applicable": sum(int(row["scan"]["applicable"]) for row in selected),  # type: ignore[index]
                "nominations": sum(int(row["scan"]["nominations"]) for row in selected),  # type: ignore[index]
            },
            "gold_family_valid_rows": sum(bool(row["gold_family_valid"]) for row in selected),
            "gold_family_coverage_rows": sum(
                bool(row["gold_family_applicable"]) for row in selected
            ),
            "selected_contract_coverage_rows": sum(
                all(row["gold_contracts_selected"]) for row in selected  # type: ignore[arg-type]
            ),
            "resolver_valid_rows": sum(bool(row["resolver_valid"]) for row in selected),
            "bottlenecks": dict(sorted(Counter(str(row["bottleneck"]) for row in selected).items())),
        }

    aggregate = summarize(result_rows)
    aggregate["per_tier"] = {
        tier: summarize([row for row in result_rows if row["tier"] == tier])
        for tier in dict.fromkeys(row["tier"] for row in result_rows)
    }
    g6_view = aggregate["g6"]
    per_tier = aggregate["per_tier"]
    measurable_gates = {
        "parse_at_least_15": int(g6_view["parse_count"]) >= 15,  # type: ignore[index]
        "exact_at_least_15": int(g6_view["exact_count"]) >= 15,  # type: ignore[index]
        "tool_16_of_16": int(g6_view["tool_count"]) == 16,  # type: ignore[index]
        "slot_micro_f1_at_least_0_90": float(g6_view["slot_f1"]) >= 0.90,  # type: ignore[index]
        "at_least_one_exact_per_tier": all(
            int(tier_view["g6"]["exact_count"]) >= 1  # type: ignore[index]
            for tier_view in per_tier.values()  # type: ignore[union-attr]
        ),
    }
    aggregate["official_equivalent_score_gate"] = {
        "conditions": measurable_gates,
        "pass": all(measurable_gates.values()),
        "scope_note": "Score conditions only; non-score protocol gates require the sealed runtime records.",
    }
    return {
        "schema": "saea-a2t-g6-fixed16-result-analysis-v1",
        "scope": {
            "model_contacts": 0,
            "tool_service_contacts": 0,
            "network_contacts": 0,
            "scorer_processes": 0,
            "audio_reads": 0,
            "tuning": False,
            "score_semantics": "unchanged Audio2Tool parser and item scorer imported in-process",
        },
        "sources": dict(sources),
        "selected_ids": list(G6_IDS),
        "aggregate": aggregate,
        "rows": result_rows,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g6-outputs", type=Path, required=True)
    parser.add_argument("--g6-scan-states", type=Path, required=True)
    parser.add_argument(
        "--transport-trace",
        type=Path,
        action="append",
        required=True,
        help="Immutable G6 transport trace; repeat once per source attempt.",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.out.exists():
        raise RuntimeError("refusing to overwrite an existing G6 analysis")

    root = data_root()
    m0_path = Path(root) / M0_RELPATH
    corpus_path = REPO / CORPUS_RELPATH
    if sha256_file(m0_path) != M0_SHA256:
        raise RuntimeError("frozen G1 M0 output identity drift")
    if sha256_file(corpus_path) != CORPUS_SHA256:
        raise RuntimeError("frozen G5 family corpus identity drift")
    lock = load_lock(umbrella_lock_path(REPO))
    expected = load_expected_calls(lock, root, repo_root=REPO)
    g6_rows = read_rows(args.g6_outputs)
    scan_rows = read_jsonl(args.g6_scan_states)
    corpus_document = json.loads(corpus_path.read_text(encoding="utf-8"))
    result = build_analysis(
        g6_rows=g6_rows,
        m0_rows=read_rows(m0_path),
        expected_by_id=expected,
        scan_rows=scan_rows,
        corpus_document=corpus_document,
        sources={
            "g6_outputs": str(args.g6_outputs.resolve()),
            "g6_outputs_sha256": sha256_file(args.g6_outputs),
            "g6_scan_states": str(args.g6_scan_states.resolve()),
            "g6_scan_states_sha256": sha256_file(args.g6_scan_states),
            "g1_m0_outputs": str(m0_path),
            "g1_m0_outputs_sha256": M0_SHA256,
            "family_corpus": str(corpus_path),
            "family_corpus_sha256": CORPUS_SHA256,
            "transport_traces": [
                {
                    "path": str(path.resolve()),
                    "sha256": sha256_file(path),
                }
                for path in args.transport_trace
            ],
        },
    )
    transport_rows = [
        row for path in args.transport_trace for row in read_jsonl(path)
    ]
    result["raw_transport_diagnostic"] = build_raw_transport_diagnostic(
        transport_rows=transport_rows,
        scan_rows=scan_rows,
        corpus_document=corpus_document,
        expected_by_id=expected,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result["aggregate"], ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
