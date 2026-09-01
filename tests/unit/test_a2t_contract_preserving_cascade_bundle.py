"""Bundle, reuse, replay, and parallel-score gates for cascade v2."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.probes import (
    a2t_contract_preserving_cascade_bundle as bundle,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_flight import (
    MATCHED_CONTACT_ID,
    M0_DIRECT_PHASE,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def test_canary_and_remaining_merge_once_into_a_complete_surface() -> None:
    expected = tuple(f"tier1:{index:06d}" for index in range(4))
    merged = bundle.merge_canary_and_remaining(
        canary={expected[0]: "a", expected[1]: "b"},
        remaining={expected[2]: "c", expected[3]: "d"},
        expected_ids=expected,
    )
    assert merged == dict(zip(expected, ("a", "b", "c", "d"), strict=True))

    with pytest.raises(bundle.ContractPreservingBundleError, match="overlap"):
        bundle.merge_canary_and_remaining(
            canary={expected[0]: "a"},
            remaining={expected[0]: "again"},
            expected_ids=expected,
        )
    with pytest.raises(bundle.ContractPreservingBundleError, match="complete"):
        bundle.merge_canary_and_remaining(
            canary={expected[0]: "a"},
            remaining={expected[1]: "b"},
            expected_ids=expected,
        )


def test_resend_selection_is_two_per_tier_and_order_invariant() -> None:
    tiers = {
        f"tier{tier}:{index:06d}": f"tier{tier}"
        for tier in range(1, 9)
        for index in range(1, 14)
    }
    selected = bundle.select_resend_ids(tiers)
    reverse = bundle.select_resend_ids(dict(reversed(tuple(tiers.items()))))
    assert selected == reverse
    assert len(selected) == 16
    assert all(sum(tiers[item] == f"tier{tier}" for item in selected) == 2 for tier in range(1, 9))


def _request_document(
    *, sample_id: str, request_id: str, contact_id: str
) -> dict[str, object]:
    payload = {
        "sample_id": sample_id,
        "request_id": request_id,
        "history": [{"contact_id": contact_id}],
    }
    return {
        "channel": "MODEL_REQUEST",
        "record_id": f"{request_id}/request",
        "payload": {
            "payload": payload,
            "payload_sha256": hashlib.sha256(
                bundle.canonical_payload_bytes(payload)
            ).hexdigest(),
        },
    }


def test_exact_resend_extractor_accepts_only_v2_matched_requests() -> None:
    selected = "tier1:000001"
    matched = _request_document(
        sample_id=selected,
        request_id="cpv2matched-0001",
        contact_id=MATCHED_CONTACT_ID,
    )
    documents = (
        _request_document(
            sample_id="tier1:000099",
            request_id="cpv2obs-0001",
            contact_id="contract-v2-observation",
        ),
        {"channel": "MODEL_RESPONSE", "record_id": "cpv2matched-0001/response"},
        matched,
    )

    extracted = bundle.extract_exact_matched_payloads(documents, (selected,))

    assert extracted == {selected: matched["payload"]["payload"]}


def test_direct_phase_bundle_material_is_trace_bound() -> None:
    text = '[{"name":"setLighting","arguments":{}}]'
    request_id = "cpv2m0-0001"
    summary = SimpleNamespace(
        results=(
            SimpleNamespace(
                sample_id="tier1:000001",
                final_response_text=text,
            ),
        )
    )
    traces = (
        {
            "channel": "MODEL_REQUEST",
            "record_id": f"{request_id}/request",
            "payload": {
                "arm": "speech-feature-query",
                "payload": {"sample_id": "tier1:000001"},
                "payload_sha256": "a" * 64,
            },
        },
        {
            "channel": "MODEL_RESPONSE",
            "record_id": f"{request_id}/response",
            "payload": {
                "text": text,
                "response_sha256": "b" * 64,
                "response_text_sha256": _sha(text),
            },
        },
        {
            "channel": "COST",
            "record_id": f"{request_id}/cost",
            "payload": {
                "calls": 1,
                "audio_seconds": 1.25,
                "latency_seconds": 0.5,
                "prompt_tokens": 10,
                "completion_tokens": 5,
            },
        },
    )

    rows, cost = bundle.build_phase_bundle_material(
        summary,
        traces,
        phase=M0_DIRECT_PHASE,
        umbrella_lock_sha256="c" * 64,
    )

    assert rows[0]["phase"] == M0_DIRECT_PHASE
    assert rows[0]["text"] == text
    assert cost["calls_used"] == 1
    assert cost["audio_seconds_used"] == 1.25


def _score_plan() -> dict[str, object]:
    return {
        "schema": "saea-parallel-score-plan-v2",
        "experiment_id": "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2",
        "entrypoint": "scripts/evaluate_parallel.sh",
        "mode": "per-wave",
        "official_scorer": {
            "modified": False,
            "processes_per_job": 1,
            "invocations_per_complete_manifest": 1,
        },
        "wave_1": {
            "mode": "--per-job-operation",
            "workers": 4,
            "jobs": [
                {
                    "job_id": job_id,
                    "input": "one complete 104-row manifest",
                    "operation": (
                        "finalize" if job_id == "resend" else "score"
                    ),
                }
                for job_id in ("m0", "matched", "shuffled", "resend")
            ],
        },
        "wave_2": {
            "mode": "default-score",
            "workers": 1,
            "jobs": [
                {
                    "job_id": "policy",
                    "input": "one complete 104-row policy manifest",
                }
            ],
        },
        "dataset_sharding": False,
        "shard_metric_averaging": False,
        "aggregation_rule": "Never split one dataset into scoring shards.",
    }


def test_parallel_plan_uses_four_whole_manifests_then_one_policy(tmp_path: Path) -> None:
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(_score_plan()), encoding="utf-8")
    validated = bundle.validate_parallel_score_plan(path)
    assert validated["wave_1"]["workers"] == 4

    plan = _score_plan()
    plan["dataset_sharding"] = True
    path.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(bundle.ContractPreservingBundleError, match="sharding"):
        bundle.validate_parallel_score_plan(path)

    plan = _score_plan()
    plan["wave_1"]["jobs"] = plan["wave_1"]["jobs"][:3]
    path.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(bundle.ContractPreservingBundleError, match="four"):
        bundle.validate_parallel_score_plan(path)

    plan = _score_plan()
    plan["wave_1"]["jobs"][2]["operation"] = "finalize"
    path.write_text(json.dumps(plan), encoding="utf-8")
    with pytest.raises(bundle.ContractPreservingBundleError, match="operations"):
        bundle.validate_parallel_score_plan(path)


def test_committed_parallel_plan_is_valid() -> None:
    repo = Path(__file__).resolve().parents[2]
    path = (
        repo
        / "docs/checks/speech-aware-evidence-acquisition"
        / "2026-09-01-a2t-contract-preserving-cascade-104-v2"
        / "parallel-score-plan.json"
    )
    plan = bundle.validate_parallel_score_plan(path)
    assert plan["dataset_sharding"] is False
    assert plan["shard_metric_averaging"] is False
