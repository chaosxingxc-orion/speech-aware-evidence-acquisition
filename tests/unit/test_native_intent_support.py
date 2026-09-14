"""Synthetic coverage/support joins from the actual initial request only."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.native_candidate_stage_projections import (
    NativeCandidateStage, NativeCandidateStagePair,
)
from speech_aware_evidence_acquisition.analysis.slurp_topn_diagnostics import ReferenceIntentRow
from speech_aware_evidence_acquisition.analysis.native_intent_support import (
    NativeIntentSupportError, build_initial_intent_support_diagnostics,
)
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.knowledge import QueryState

SPEC = {
    "schema": "saea-initial-intent-support-projection-v1",
    "policy_id": "initial-perception-request-intent-value-id-suffix-v1",
    "store_id": "intent-boundaries",
    "value_id_prefix": "intent-boundary:",
}


def _world():
    ids = tuple(f"slurp:train:synthetic-{i}" for i in range(4))
    traces, pairs, phases = {}, [], {}
    references = tuple(ReferenceIntentRow(s, "private-gold-alpha") for s in ids)
    for i, sample in enumerate(ids):
        supplied = "private-gold-alpha" if i < 2 else "beta"
        candidates = ("private-gold-alpha",) if i in (0, 2) else ("beta",)
        request_id = f"{sample}/initial"
        evidence = [{
            "evidence_id": f"intent-boundaries::intent-boundary:{supplied}",
            "content": "Synthetic discriminative content, not an annotation.",
            "source_uri": "synthetic://released-store",
        }, {
            "evidence_id": "slot-contracts::intent-boundary:private-gold-alpha",
            "content": "A different store is not intent support.",
            "source_uri": "synthetic://slot-store",
        }]
        for block in evidence:
            block["knowledge_role"] = "value"
            block["source_uri"] = "knowledge-snapshot://" + "c" * 64 + "/" + block["evidence_id"]
        query = QueryState(
            query_id=f"query:{sample}", query_sample_id=sample,
            speech_packet_id=f"packet:{sample}", speech_packet_sha256="d" * 64,
            use_split_identity_hash="e" * 64,
            retrieved_value_ids=tuple(b["evidence_id"] for b in evidence),
        )
        initial = query.as_json()
        phases[sample] = {"initial_query_state": initial}
        base = f"{sample}/phase-synthetic/agent-loop"
        traces[base + "/org"] = {
            "org_controller_policy_id": "phase-synthetic",
            "org_initial_query_state": initial,
            "org_knowledge_snapshot_sha256": "c" * 64,
        }
        traces[base + "/supply"] = {
            "supply_bootstrap_value_ids": list(query.retrieved_value_ids),
        }
        traces[base + "/runtime-use"] = {
            "use_initial_query_state_sha256": query.content_hash(),
        }
        payload = {"request_id": request_id, "sample_id": sample,
                   "supplied_evidence": evidence}
        request_sha = content_hash(payload)
        traces[f"{request_id}/request"] = {
            "payload": payload, "payload_sha256": request_sha,
        }
        # Future supply is deliberately present and must not leak into C0 support.
        traces[f"{sample}/future/request"] = {
            "payload": {"supplied_evidence": [{"evidence_id":
                "intent-boundaries::intent-boundary:private-gold-alpha"}]},
        }
        stage = NativeCandidateStage(
            visit_index=0, state_id=f"{sample}/state", state_sha256="1" * 64,
            query_state_sha256=query.content_hash(), agent_contact_id=f"{sample}/contact",
            request_id=request_id, request_sha256=request_sha,
            response_sha256="3" * 64, response_text_sha256="4" * 64,
            candidate_ids=candidates, candidate_set_sha256=content_hash(list(candidates)),
        )
        pairs.append(NativeCandidateStagePair(sample, stage, stage, False))
    source = SimpleNamespace(sample_ids=ids, phase_results=phases, bundle=SimpleNamespace(trace_records=traces),
        composed=SimpleNamespace(values={"policy": "phase-synthetic", "knowledge_stores": {
            "intent-boundaries": {"store_role": "intent-boundaries",
                "phase_supply": {"perception": {"expose_facets": False}},
                "snapshot": {"sha256": "a" * 64}, "release": {"sha256": "b" * 64}}
        }}))
    return source, tuple(pairs), references


def _build(source, pairs, references, **kwargs):
    return build_initial_intent_support_diagnostics(
        source=source, stage_pairs=pairs, reference_rows=references,
        legal_candidate_ids=frozenset({"private-gold-alpha", "beta"}),
        specification=kwargs.get("specification", SPEC),
    )


def test_four_cells_use_c0_request_and_export_no_gold_strings():
    result = _build(*_world())
    assert result["cell_counts"] == {
        "supplied_and_covered": 1, "supplied_but_missed": 1,
        "not_supplied_but_covered": 1, "neither": 1,
    }
    assert result["aggregate"]["gold_intent_value_supplied"]["value"] == 0.5
    assert result["aggregate"]["c0_coverage_given_supply"]["value"] == 0.5
    assert result["aggregate"]["c0_coverage_without_supply"]["value"] == 0.5
    assert result["semantics"]["semantic_use_proven"] is False
    assert "private-gold-alpha" not in json.dumps(result)
    assert [r["intent_value_count"] for r in result["samples"]] == [1] * 4


def test_empty_actual_supply_is_supported_and_empty_condition_has_no_value():
    source, pairs, references = _world()
    changed = []
    for pair in pairs:
        row = source.bundle.trace_records[f"{pair.c0.request_id}/request"]
        row["payload"]["supplied_evidence"] = []
        row["payload_sha256"] = content_hash(row["payload"])
        initial = source.phase_results[pair.sample_id]["initial_query_state"]
        initial["retrieved_value_ids"] = []
        qsha = QueryState.from_json(initial).content_hash()
        base = f"{pair.sample_id}/phase-synthetic/agent-loop"
        source.bundle.trace_records[base + "/supply"]["supply_bootstrap_value_ids"] = []
        source.bundle.trace_records[base + "/runtime-use"]["use_initial_query_state_sha256"] = qsha
        stage = replace(pair.c0, request_sha256=row["payload_sha256"], query_state_sha256=qsha)
        changed.append(replace(pair, c0=stage, c1=stage))
    result = _build(source, tuple(changed), references)
    assert result["aggregate"]["c0_coverage_given_supply"] == {
        "numerator": 0, "denominator": 0, "value": None,
    }
    assert result["cell_counts"]["not_supplied_but_covered"] == 2
    assert result["cell_counts"]["neither"] == 2


def test_missing_c0_retains_unknown_support_row_and_full_roster_denominator():
    source, pairs, references = _world()
    pairs = (
        NativeCandidateStagePair(pairs[0].sample_id, None, None, False),
        *pairs[1:],
    )

    result = _build(source, pairs, references)

    assert result["support_availability"] == {
        "available_count": 3,
        "unavailable_count": 1,
    }
    assert result["aggregate"]["gold_intent_value_supplied"] == {
        "numerator": 1,
        "denominator": 4,
        "value": 0.25,
    }
    assert result["cell_counts"] == {
        "supplied_and_covered": 0,
        "supplied_but_missed": 1,
        "not_supplied_but_covered": 1,
        "neither": 1,
    }
    unavailable = result["samples"][0]
    assert unavailable == {
        "sample_id": pairs[0].sample_id,
        "support_available": False,
        "request_sha256": None,
        "candidate_set_sha256": None,
        "supplied_intent_value_ids_sha256": None,
        "intent_value_count": None,
        "gold_intent_value_supplied": None,
        "c0_gold_covered": None,
        "cell": None,
    }


@pytest.mark.parametrize("mutation", [
    "request-sha", "payload-tamper", "sample", "missing-request", "missing-evidence",
    "non-list", "duplicate-id", "unmapped-store-value", "empty-content",
    "reference-order", "pair-order", "duplicate-pair", "foreign-reference",
])
def test_rejects_incomplete_or_misaligned_support_evidence(mutation):
    source, pairs, references = _world()
    row = source.bundle.trace_records[f"{pairs[0].c0.request_id}/request"]
    if mutation == "request-sha":
        row["payload_sha256"] = "c" * 64
    elif mutation == "payload-tamper":
        row["payload"]["supplied_evidence"][0]["content"] += " changed"
    elif mutation == "sample":
        row["payload"]["sample_id"] = "slurp:train:foreign"
    elif mutation == "missing-request":
        del source.bundle.trace_records[f"{pairs[0].c0.request_id}/request"]
    elif mutation == "missing-evidence":
        del row["payload"]["supplied_evidence"]
    elif mutation == "non-list":
        row["payload"]["supplied_evidence"] = "not-a-list"
    elif mutation == "duplicate-id":
        row["payload"]["supplied_evidence"].append(
            deepcopy(row["payload"]["supplied_evidence"][0]))
    elif mutation == "unmapped-store-value":
        row["payload"]["supplied_evidence"][0]["evidence_id"] = (
            "intent-boundaries::another-value:private-gold-alpha")
    elif mutation == "empty-content":
        row["payload"]["supplied_evidence"][0]["content"] = " "
    elif mutation == "reference-order":
        references = tuple(reversed(references))
    elif mutation == "pair-order":
        pairs = tuple(reversed(pairs))
    elif mutation == "duplicate-pair":
        pairs = (*pairs[:-1], pairs[0])
    else:
        references = (ReferenceIntentRow(references[0].sample_id, "illegal"), *references[1:])
    # These cases must fail beyond hash checks, not only as payload tampering.
    if mutation in {"sample", "missing-evidence", "non-list", "duplicate-id",
                    "unmapped-store-value", "empty-content"}:
        row["payload_sha256"] = content_hash(row["payload"])
        stage = replace(pairs[0].c0, request_sha256=row["payload_sha256"])
        pairs = (replace(pairs[0], c0=stage, c1=stage), *pairs[1:])
    with pytest.raises(NativeIntentSupportError):
        _build(source, pairs, references)


@pytest.mark.parametrize("spec", [
    None, {}, {**SPEC, "extra": True}, {**SPEC, "policy_id": "unknown"},
    {**SPEC, "store_id": "slot-contracts"}, {**SPEC, "value_id_prefix": ""},
])
def test_rejects_undeclared_support_mapping(spec):
    with pytest.raises(NativeIntentSupportError):
        _build(*_world(), specification=spec)


@pytest.mark.parametrize("mutation", [
    "source-uri", "key-role", "bootstrap-order", "initial-query", "snapshot",
    "undeclared-route", "missing-store-pin", "block-not-mapping", "illegal-value-id",
])
def test_rejects_route_or_supply_state_contradictions(mutation):
    source, pairs, refs = _world()
    row = source.bundle.trace_records[pairs[0].c0.request_id + "/request"]
    base = f"{pairs[0].sample_id}/phase-synthetic/agent-loop"
    if mutation == "source-uri":
        row["payload"]["supplied_evidence"][0]["source_uri"] = "foreign://content"
    elif mutation == "key-role":
        row["payload"]["supplied_evidence"][0]["knowledge_role"] = "key"
    elif mutation == "bootstrap-order":
        source.bundle.trace_records[base + "/supply"]["supply_bootstrap_value_ids"].reverse()
    elif mutation == "initial-query":
        source.bundle.trace_records[base + "/runtime-use"]["use_initial_query_state_sha256"] = "0" * 64
    elif mutation == "snapshot":
        source.bundle.trace_records[base + "/org"]["org_knowledge_snapshot_sha256"] = "0" * 64
    elif mutation == "undeclared-route":
        source.composed.values["knowledge_stores"]["intent-boundaries"]["phase_supply"] = {}
    elif mutation == "missing-store-pin":
        del source.composed.values["knowledge_stores"]["intent-boundaries"]["snapshot"]
    elif mutation == "block-not-mapping":
        row["payload"]["supplied_evidence"][0] = "invalid block"
    else:
        row["payload"]["supplied_evidence"][0]["evidence_id"] = "intent-boundaries::intent-boundary:illegal"
    row["payload_sha256"] = content_hash(row["payload"])
    stage = replace(pairs[0].c0, request_sha256=row["payload_sha256"])
    pairs = (replace(pairs[0], c0=stage, c1=stage), *pairs[1:])
    with pytest.raises(NativeIntentSupportError):
        _build(source, pairs, refs)
