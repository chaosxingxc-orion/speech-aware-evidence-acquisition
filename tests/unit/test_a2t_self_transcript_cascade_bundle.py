"""Bundle, replay, and complete-manifest scoring tests for the cascade."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.rails.probes import (
    a2t_self_transcript_cascade_bundle as bundle,
)


REPO = Path(__file__).resolve().parents[2]


def _request(sample_id: str, request_id: str) -> dict[str, object]:
    payload = {
        "request_id": request_id,
        "sample_id": sample_id,
        "carrier_lock_key": "audio2tool",
        "history": [
            {
                "role": "control",
                "contact_id": "self-transcript-matched-final",
                "content": "Answer from speech, state, and supplied evidence.",
            }
        ],
        "decoding_params": {"id_slot": 2, "temperature": 0},
    }
    payload_sha256 = hashlib.sha256(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "channel": "MODEL_REQUEST",
        "record_id": f"{request_id}/request",
        "payload": {
            "arm": "speech-feature-query",
            "payload": payload,
            "payload_sha256": payload_sha256,
        },
    }


def _phase_trace(sample_id: str, request_id: str, text: str) -> tuple[dict[str, object], ...]:
    request = _request(sample_id, request_id)
    response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    response_sha256 = hashlib.sha256(f"response:{text}".encode("utf-8")).hexdigest()
    return (
        request,
        {
            "channel": "MODEL_RESPONSE",
            "record_id": f"{request_id}/response",
            "payload": {
                "text": text,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
            },
        },
        {
            "channel": "COST",
            "record_id": f"{request_id}/cost",
            "payload": {
                "calls": 1,
                "audio_seconds": 2.5,
                "latency_seconds": 1.25,
                "prompt_tokens": 100,
                "completion_tokens": 12,
            },
        },
    )
def test_resend_selection_is_hash_ranked_two_per_tier() -> None:
    tiers = {
        f"tier{tier}:{index:06d}": f"tier{tier}"
        for tier in range(8)
        for index in range(3)
    }
    selected = bundle.select_resend_ids(tiers, per_tier=2)
    assert len(selected) == 16
    assert all(
        sum(sample_id.startswith(f"tier{tier}:") for sample_id in selected) == 2
        for tier in range(8)
    )


def test_exact_replay_extracts_only_byte_identical_matched_payloads() -> None:
    documents = (
        _request("tier1:000001", "matched-0001"),
        _request("tier1:000002", "matched-0002"),
    )
    extracted = bundle.extract_exact_matched_payloads(
        documents, ("tier1:000002",)
    )
    original = documents[1]["payload"]["payload"]
    assert bundle.canonical_payload_bytes(extracted["tier1:000002"]) == (
        bundle.canonical_payload_bytes(original)
    )

    documents[0]["payload"]["payload"]["history"][0][
        "contact_id"
    ] = "self-transcript-shuffled-final"
    documents[0]["payload"]["payload_sha256"] = hashlib.sha256(
        bundle.canonical_payload_bytes(documents[0]["payload"]["payload"])
    ).hexdigest()
    with pytest.raises(bundle.SelfTranscriptBundleError, match="matched final"):
        bundle.extract_exact_matched_payloads(
            (documents[0],), ("tier1:000001",)
        )


def test_exact_replay_ignores_non_request_records_in_a_complete_trace() -> None:
    request = _request("tier1:000001", "matched-0001")
    trace = (
        request,
        {
            "channel": "MODEL_RESPONSE",
            "record_id": "matched-0001/response",
            "payload": {"text": "response"},
        },
        {
            "channel": "COST",
            "record_id": "matched-0001/cost",
            "payload": {"calls": 1},
        },
    )
    extracted = bundle.extract_exact_matched_payloads(
        trace, ("tier1:000001",)
    )
    assert extracted["tier1:000001"]["request_id"] == "matched-0001"


def test_complete_composites_refuse_missing_duplicate_or_extra_rows() -> None:
    expected = tuple(f"tier1:{index:06d}" for index in range(4))
    texts = {sample_id: f"response-{sample_id}" for sample_id in expected}
    assert bundle.assert_complete_composite(texts, expected_ids=expected) == texts

    with pytest.raises(bundle.SelfTranscriptBundleError, match="identity"):
        bundle.assert_complete_composite(
            {sample_id: text for sample_id, text in texts.items() if sample_id != expected[0]},
            expected_ids=expected,
        )
    with pytest.raises(bundle.SelfTranscriptBundleError, match="unique"):
        bundle.assert_complete_composite(texts, expected_ids=expected + (expected[0],))


def test_policy_composite_uses_only_frozen_m0_or_matched_authority() -> None:
    expected = ("tier1:000001", "tier1:000002", "tier1:000003")
    policy = bundle.build_policy_composite_texts(
        m0_texts={sample_id: f"m0-{sample_id}" for sample_id in expected},
        matched_texts={sample_id: f"matched-{sample_id}" for sample_id in expected},
        actions={
            expected[0]: "USE_MATCHED",
            expected[1]: "STOP_M0",
            expected[2]: "STOP_M0",
        },
    )
    assert policy[expected[0]].startswith("matched-")
    assert policy[expected[1]].startswith("m0-")
    assert set(policy) == set(expected)


def test_phase_bundle_material_preserves_trace_identity_and_cost() -> None:
    results = tuple(
        SimpleNamespace(
            sample_id=f"tier1:{index:06d}",
            final_response_text=f"response-{index}",
        )
        for index in range(2)
    )
    trace = tuple(
        row
        for index in range(2)
        for row in _phase_trace(
            f"tier1:{index:06d}", f"matched-{index:04d}", f"response-{index}"
        )
    )
    rows, cost = bundle.build_phase_bundle_material(
        SimpleNamespace(results=results),
        trace,
        phase="USE_MATCHED",
        umbrella_lock_sha256="a" * 64,
    )
    assert len(rows) == 2
    assert all(row["phase"] == "USE_MATCHED" for row in rows)
    assert cost == {
        "calls_used": 2,
        "audio_seconds_used": 5.0,
        "latency_seconds_total": 2.5,
        "prompt_tokens_total": 200,
        "completion_tokens_total": 24,
        "tool_calls": 0,
        "umbrella_lock_sha256": "a" * 64,
    }


def test_matched_shuffled_and_resend_composites_remain_complete() -> None:
    expected = tuple(f"tier1:{index:06d}" for index in range(4))
    m0 = {sample_id: f"m0-{sample_id}" for sample_id in expected}
    phase = {sample_id: f"use-{sample_id}" for sample_id in expected[:3]}
    matched = bundle.build_use_composite_texts(
        m0_texts=m0,
        use_texts=phase,
        routed_ids=expected[:3],
    )
    assert matched[expected[3]].startswith("m0-")
    resend = bundle.build_resend_composite_texts(
        matched,
        selected_ids=(expected[0], expected[1]),
        resend_responses={expected[0]: "r0", expected[1]: "r1"},
    )
    assert set(resend) == set(expected)
    assert resend[expected[0]] == "r0"


def test_composite_rows_are_bound_to_deterministic_tool_trace_records() -> None:
    texts = {"tier1:000001": "one", "tier1:000002": "two"}
    sources = {
        "tier1:000001": {"action": "USE_MATCHED", "request_id": "matched-1"},
        "tier1:000002": {"action": "STOP_M0", "request_id": "frozen-m0"},
    }
    sink = TraceBuffer("SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1")
    rows = bundle.emit_composite_rows(
        texts=texts,
        source_by_id=sources,
        sink=sink,
        variant="matched",
    )
    assert len(rows) == 2
    assert len(sink.records) == 4
    assert all(channel == "TOOL" for channel, _record_id, _payload in sink.records)
    assert all(row["composite_variant"] == "matched" for row in rows)


def test_registered_score_plan_parallelizes_only_complete_manifests() -> None:
    path = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-self-transcript-cascade-104-v1"
        / "parallel-score-plan.json"
    )
    plan = bundle.validate_parallel_score_plan(path)
    assert plan["official_scorer"] == {
        "modified": False,
        "processes_per_job": 1,
        "invocations_per_complete_manifest": 1,
    }
    assert plan["mode"] == "per-wave"
    assert plan["wave_1"]["mode"] == "--finalize"
    assert plan["wave_2"]["mode"] == "--score"
    assert plan["wave_1"]["workers"] == len(plan["wave_1"]["jobs"]) == 3
    assert all("complete 104-row" in job["input"] for job in plan["wave_1"]["jobs"])
    assert "Never split one dataset" in plan["aggregation_rule"]


def test_execution_plan_binds_the_exact_composed_protocol() -> None:
    checks = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-self-transcript-cascade-104-v1"
    )
    plan = json.loads((checks / "execution-plan-template.json").read_text())
    fragments = plan["config_composition"]
    composed = compose(
        REPO,
        fragments["model"],
        fragments["dataset"],
        fragments["baseline"],
        fragments["experiment"],
    )
    execution = plan["execution_plan"]
    assert composed.config_hash == plan["composed_config_sha256"]
    assert execution["protocol_hash"] == protocol_hash(
        composed.config_hash,
        composed.values["arm"],
        execution["split_identity_hash"],
    )
    assert execution["planned_model_calls"] == 334
    assert len(plan["phase_attempts"]) == 4


def test_parallel_plan_validator_rejects_shard_language(tmp_path: Path) -> None:
    source = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-self-transcript-cascade-104-v1"
        / "parallel-score-plan.json"
    )
    plan = json.loads(source.read_text(encoding="utf-8"))
    plan["wave_1"]["jobs"][0]["input"] = "one 52-row shard"
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(bundle.SelfTranscriptBundleError, match="complete 104-row"):
        bundle.validate_parallel_score_plan(bad)
