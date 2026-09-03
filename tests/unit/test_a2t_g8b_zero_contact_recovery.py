"""Tests for the write-once, zero-contact G8B diagnostic recovery."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from speech_aware_evidence_acquisition.contracts import TraceRecord


ROOT = Path(__file__).resolve().parents[2]
RECOVERY = ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-g8b-action-support-reachability-fixed16-v1/launcher/"
    "recover_a2t_g8b_fixed16.py"
)
SPEC = importlib.util.spec_from_file_location("g8b_zero_contact_recovery", RECOVERY)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_flight(tmp_path: Path) -> tuple[Path, module.SourceHashes]:
    flight = tmp_path / "flight"
    trace_dir = flight / "g8b" / "transport-trace"
    trace_dir.mkdir(parents=True)
    rows = []
    for index, (sample_id, contact_id, slot_id, text) in enumerate(
        (
            ("sample-a", "g8-obs", 1, "Line one.\nLine two."),
            ("sample-b", "g8-decomposed-select", 0, '["tool_name"]'),
        ),
        start=1,
    ):
        request_id = f"g8bfixed16-{index:04d}"
        rows.extend(
            (
                TraceRecord(
                    "MODEL_REQUEST",
                    f"{request_id}/request",
                    {
                        "arm": "speech-feature-query",
                        "payload": {
                            "request_id": request_id,
                            "sample_id": sample_id,
                            "history": [{"contact_id": contact_id}],
                            "decoding_params": {
                                "id_slot": slot_id,
                                "max_tokens": 512,
                                "temperature": 0,
                            },
                            "key_representation_id": "key",
                            "matcher_policy_id": "policy",
                        },
                        "payload_sha256": "a" * 64,
                    },
                ),
                TraceRecord(
                    "MODEL_RESPONSE",
                    f"{request_id}/response",
                    {
                        "text": text,
                        "response_sha256": "b" * 64,
                        "response_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 2,
                            "total_tokens": 12,
                        },
                    },
                ),
                TraceRecord(
                    "COST",
                    f"{request_id}/cost",
                    {
                        "calls": 1,
                        "audio_seconds": 1.25,
                        "latency_seconds": 0.5,
                        "prompt_tokens": 10,
                        "completion_tokens": 2,
                    },
                ),
            )
        )
    trace_path = trace_dir / f"{module.RUN_ID}.trace.jsonl"
    trace_path.write_text(
        "".join(row.serialize() + "\n" for row in rows), encoding="utf-8", newline="\n"
    )
    manifest_path = trace_dir / f"{module.RUN_ID}.trace-manifest.json"
    _write_json(
        manifest_path,
        {
            "run_id": module.RUN_ID,
            "records": {row.record_id: row.content_hash() for row in rows},
        },
    )
    failure_path = flight / "failure-receipt.json"
    _write_json(
        failure_path,
        {
            "attempt_id": module.ATTEMPT_ID,
            "branch_manifests_emitted": False,
            "error": "TraceContractError(\"OBS payload key 'sample_id' must start with 'obs_'\")",
            "retry_or_repair_authorized": False,
            "run_id": module.RUN_ID,
            "scoring_started": False,
            "terminal": True,
        },
    )
    return flight, module.SourceHashes(
        transport_trace_sha256=_sha256(trace_path),
        transport_manifest_sha256=_sha256(manifest_path),
        failure_receipt_sha256=_sha256(failure_path),
    )


def test_loader_verifies_every_triple_and_replay_preserves_exact_utf8_bytes(
    tmp_path: Path,
) -> None:
    flight, hashes = _source_flight(tmp_path)

    sealed = module.load_sealed_transport(
        flight, expected=hashes, expected_contact_count=2
    )
    first = sealed.contacts[("sample-a", "g8-obs")]
    assert first.response_bytes == b"Line one.\nLine two."
    assert first.source_request_id == "g8bfixed16-0001"
    assert sealed.physical_cost == {
        "calls_used": 2,
        "audio_seconds_used": 2.5,
        "latency_seconds_total": 1.0,
        "prompt_tokens_total": 20,
        "completion_tokens_total": 4,
    }

    client = module.ReplayClient(sealed)
    assert client.complete(
        (),
        speech_feature_sample_id="sample-a",
        agent_contact_id="g8-obs",
        decoding_params={"id_slot": 1, "max_tokens": 512, "temperature": 0},
    ) == "Line one.\nLine two."
    with pytest.raises(module.RecoveryError, match="used more than once"):
        client.complete(
            (),
            speech_feature_sample_id="sample-a",
            agent_contact_id="g8-obs",
            decoding_params={"id_slot": 1},
        )
    with pytest.raises(module.RecoveryError, match="not consume every"):
        client.assert_complete(expected_count=2)
    assert client.complete(
        (),
        speech_feature_sample_id="sample-b",
        agent_contact_id="g8-decomposed-select",
        decoding_params={"id_slot": 0},
    ) == '["tool_name"]'
    client.assert_complete(expected_count=2)


def test_loader_refuses_any_pinned_source_drift(tmp_path: Path) -> None:
    flight, hashes = _source_flight(tmp_path)
    trace = (
        flight
        / "g8b"
        / "transport-trace"
        / f"{module.RUN_ID}.trace.jsonl"
    )
    trace.write_bytes(trace.read_bytes() + b" ")

    with pytest.raises(module.RecoveryError, match="transport trace SHA-256 drift"):
        module.load_sealed_transport(
            flight, expected=hashes, expected_contact_count=2
        )


def test_diagnostic_outputs_are_complete_but_explicitly_unscorable(
    tmp_path: Path,
) -> None:
    source = {
        "transport_trace_sha256": "1" * 64,
        "transport_manifest_sha256": "2" * 64,
        "failure_receipt_sha256": "3" * 64,
        "attempt_state": "ABORTED",
        "attempt_state_sha256": "4" * 64,
    }
    branch_texts = {
        branch: {"sample-a": f"{branch}:a", "sample-b": f"{branch}:b"}
        for branch in module.BRANCH_ORDER
    }

    result = module.write_diagnostic_branches(
        output_dir=tmp_path / "diagnostic",
        recovery_id="g8b-zero-contact-unit",
        sample_ids=("sample-a", "sample-b"),
        branch_texts=branch_texts,
        source_binding=source,
    )

    assert set(result) == set(module.BRANCH_ORDER)
    for branch, artifacts in result.items():
        manifest = json.loads(Path(artifacts["manifest"]).read_text(encoding="utf-8"))
        assert manifest["status"] == "EXTERNALLY_SEALED_UNVERIFIABLE"
        assert manifest["scoring_eligible"] is False
        assert manifest["normal_run_manifest"] is False
        assert manifest["row_count"] == 2
        assert len(Path(artifacts["outputs"]).read_text(encoding="utf-8").splitlines()) == 2
    disposition = json.loads(
        (tmp_path / "diagnostic" / "scoring-disposition.json").read_text(encoding="utf-8")
    )
    assert disposition["jobs"] == []
    assert disposition["official_scoring_authorized"] is False
    assert not list((tmp_path / "diagnostic").rglob("*.run-manifest.json"))

    with pytest.raises(module.RecoveryError, match="already exists"):
        module.write_diagnostic_branches(
            output_dir=tmp_path / "diagnostic",
            recovery_id="g8b-zero-contact-unit",
            sample_ids=("sample-a", "sample-b"),
            branch_texts=branch_texts,
            source_binding=source,
        )


def test_verify_only_allows_an_existing_recovery_destination(tmp_path: Path) -> None:
    source_flight = tmp_path / "source-flight"
    destination = tmp_path / "existing-recovery"
    source_flight.mkdir()
    destination.mkdir()

    module._validate_recovery_destination(
        source_flight,
        destination,
        write_output=False,
    )
    with pytest.raises(module.RecoveryError, match="already exists"):
        module._validate_recovery_destination(
            source_flight,
            destination,
            write_output=True,
        )
