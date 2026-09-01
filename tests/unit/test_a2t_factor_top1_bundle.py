"""Bundle and resend gates for the Audio2Tool factor-top-1 flight."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.tracing import TraceBuffer
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.rails.probes import a2t_factor_top1_bundle as bundle


REPO = Path(__file__).resolve().parents[2]


def _result(sample_id: str, *, available: bool, text: str) -> object:
    return SimpleNamespace(
        sample_id=sample_id,
        final_query_state=SimpleNamespace(
            retrieved_value_ids=("registry-value:11",) if available else ()
        ),
        final_response_text=text,
    )


def _summary(*results: object) -> object:
    return SimpleNamespace(results=tuple(results))


def _request_document(sample_id: str, request_id: str) -> dict[str, object]:
    payload = {
        "request_id": request_id,
        "sample_id": sample_id,
        "history": [
            {
                "role": "control",
                "contact_id": "factor-top1-final",
                "content": "Answer from the original speech.",
            }
        ],
        "decoding_params": {"id_slot": 1, "temperature": 0},
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


def test_resend_selection_is_two_hash_ranked_available_samples_per_tier() -> None:
    results = []
    for tier in ("tier1_direct", "tier2_noisy"):
        for index in range(4):
            results.append(
                _result(
                    f"{tier}:{index:06d}",
                    available=index != 3,
                    text=f"response-{tier}-{index}",
                )
            )
    selected = bundle.select_resend_ids(_summary(*results), per_tier=2)
    assert len(selected) == 4
    assert {sample_id.rsplit(":", 1)[0] for sample_id in selected} == {
        "tier1_direct",
        "tier2_noisy",
    }
    for tier in ("tier1_direct", "tier2_noisy"):
        eligible = [f"{tier}:{index:06d}" for index in range(3)]
        expected = sorted(
            eligible,
            key=lambda sample_id: hashlib.sha256(
                f"resend-v1\n{sample_id}".encode("utf-8")
            ).hexdigest(),
        )[:2]
        assert sorted(sample_id for sample_id in selected if sample_id.startswith(tier)) == sorted(expected)


def test_resend_selection_fails_closed_when_one_tier_lacks_support() -> None:
    summary = _summary(
        _result("tier1_direct:000001", available=True, text="a"),
        _result("tier1_direct:000002", available=False, text="b"),
    )
    with pytest.raises(bundle.FactorTop1BundleError, match="fewer than"):
        bundle.select_resend_ids(summary, per_tier=2)


def test_exact_replay_payloads_preserve_serialized_request_bytes() -> None:
    documents = (
        _request_document("tier1_direct:000001", "factor-0105"),
        _request_document("tier1_direct:000002", "factor-0106"),
    )
    payloads = bundle.extract_exact_final_payloads(
        documents, ("tier1_direct:000002",)
    )
    assert tuple(payloads) == ("tier1_direct:000002",)
    extracted = payloads["tier1_direct:000002"]
    original = documents[1]["payload"]["payload"]
    assert bundle.canonical_payload_bytes(extracted) == bundle.canonical_payload_bytes(original)
    assert extracted["request_id"] == "factor-0106"
    assert extracted["decoding_params"]["id_slot"] == 1


def test_exact_replay_rejects_a_non_final_or_hash_drifted_request() -> None:
    document = _request_document("tier1_direct:000001", "factor-0001")
    document["payload"]["payload"]["history"][0]["contact_id"] = "semantic-factor"
    with pytest.raises(bundle.FactorTop1BundleError, match="final request"):
        bundle.extract_exact_final_payloads(
            (document,), ("tier1_direct:000001",)
        )


def test_main_and_resend_texts_use_m0_only_when_registered() -> None:
    summary = _summary(
        _result("tier1_direct:000001", available=True, text="main-one"),
        _result("tier1_direct:000002", available=False, text="diagnostic-only"),
    )
    main = bundle.build_main_composite_texts(
        summary,
        {
            "tier1_direct:000001": "m0-one",
            "tier1_direct:000002": "m0-two",
        },
    )
    assert main == {
        "tier1_direct:000001": "main-one",
        "tier1_direct:000002": "m0-two",
    }
    resend = bundle.build_resend_composite_texts(
        main,
        selected_ids=("tier1_direct:000001",),
        resend_responses={"tier1_direct:000001": "resend-one"},
    )
    assert resend == {
        "tier1_direct:000001": "resend-one",
        "tier1_direct:000002": "m0-two",
    }


def test_composite_rows_bind_every_complete_output_to_tool_trace_records() -> None:
    sink = TraceBuffer("SAEA-A2T-TFRL-FACTOR-TOP1-104-V1")
    rows = bundle.emit_composite_rows(
        texts={
            "tier1_direct:000001": "main-one",
            "tier1_direct:000002": "m0-two",
        },
        source_by_id={
            "tier1_direct:000001": {
                "action": "USE_FACTOR_TOP1",
                "source_request_id": "factor-0105",
            },
            "tier1_direct:000002": {
                "action": "STOP_M0",
                "source_request_id": "frozen-m0",
            },
        },
        sink=sink,
        variant="main",
    )
    assert len(rows) == 2
    assert len(sink.records) == 4
    assert all(channel == "TOOL" for channel, _record_id, _payload in sink.records)
    trace = {record_id: payload for _channel, record_id, payload in sink.records}
    for row in rows:
        assert trace[f"{row['request_id']}/request"]["payload_sha256"] == row["request_sha256"]
        response = trace[f"{row['request_id']}/response"]
        assert response["text"] == row["text"]
        assert response["response_sha256"] == row["response_sha256"]
        assert response["response_text_sha256"] == row["response_text_sha256"]


def test_real_execution_and_parallel_score_plans_bind_composed_identity() -> None:
    checks = (
        REPO
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-factor-top1-104-v1"
    )
    plan = json.loads((checks / "execution-plan-template.json").read_text())
    score = json.loads((checks / "parallel-score-plan.json").read_text())
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
    prompt_receipt = REPO / composed.values["speech_native_prompt_fit_receipt"]
    assert hashlib.sha256(prompt_receipt.read_bytes()).hexdigest() == composed.values[
        "speech_native_prompt_fit_receipt_sha256"
    ]
    assert score["mode"] == "--finalize"
    assert score["workers"] == len(score["jobs"]) == 2
    assert all("complete 104-row" in job["input"] for job in score["jobs"])
