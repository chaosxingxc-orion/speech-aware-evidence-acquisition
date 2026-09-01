"""Recovery and trace-sealing tests for the self-transcript launcher."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.knowledge import (
    KeyFacet,
    KnowledgeSnapshot,
    ValueBundle,
)


REPO = Path(__file__).resolve().parents[2]
LAUNCHER_PATH = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-self-transcript-cascade-104-v1/launcher/"
    "launch_a2t_self_transcript_cascade.py"
)


def _launcher():
    spec = importlib.util.spec_from_file_location("self_transcript_launcher", LAUNCHER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")


def _context() -> dict[str, object]:
    sample_ids = tuple(
        f"tier{tier}_fixture:{index:06d}"
        for tier in range(1, 9)
        for index in range(13)
    )
    facets = (
        KeyFacet(
            facet_id="facet-light",
            dimension="content",
            representation_kind="text",
            representation="dim the kitchen lights percent",
            source_sample_ids=("train:000001",),
        ).validate(),
    )
    values = (
        ValueBundle(
            value_id="value-light",
            content='{"name":"setLightBrightness","arguments":{"source":"train"}}',
            associated_facet_ids=("facet-light",),
            source_sample_ids=("train:000001",),
            provenance_refs=("fixture:value-light",),
            task_target="setLightBrightness",
        ).validate(),
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id="fixture-self-transcript-recovery",
        source_split_identity_hash="a" * 64,
        source_sample_ids=("train:000001",),
        builder_policy_id="fixture-builder",
        facets=facets,
        values=values,
        source_partition_role="train",
    ).validate()
    return {
        "sample_ids": sample_ids,
        "items": tuple(
            {
                "sample_id": sample_id,
                "tier": sample_id.split("_", 1)[0],
            }
            for sample_id in sample_ids
        ),
        "snapshot": snapshot,
    }


def test_primary_trace_closes_before_transport_and_supplies_manifest_hash() -> None:
    launcher = _launcher()
    events: list[str] = []

    class Sink:
        def close(self) -> str:
            events.append("primary")
            return "p" * 64

    class Client:
        def close(self) -> dict[str, object]:
            assert events == ["primary"]
            events.append("transport")
            return {"trace_manifest_hash": "t" * 64, "request_count": 104}

    trace_hash, summary = launcher._close_phase_traces(Sink(), Client())
    assert trace_hash == "p" * 64
    assert summary["trace_manifest_hash"] == "t" * 64
    assert events == ["primary", "transport"]


def test_recovery_accepts_only_fixed_aborted_observation_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    context = _context()
    source = tmp_path / "runs" / launcher.RUN_ID / "flight-fixed" / "observation"
    outputs = source / f"{launcher.RUN_ID}.outputs.jsonl"
    trace = source / f"{launcher.RUN_ID}.trace.jsonl"
    plan = source / "execution-plan.json"
    failure = source.parent / "failure-receipt.json"
    attempt = (
        tmp_path
        / "attempts"
        / launcher.RUN_ID
        / "attempt-fixed-selftxobs.json"
    )
    source.mkdir(parents=True)
    rows = [
        {
            "admitted": True,
            "arm": "speech-feature-query",
            "carrier_lock_key": "audio2tool",
            "phase": launcher.OBSERVATION_PHASE,
            "request_id": f"selftxobs-{index:04d}",
            "request_sha256": hashlib.sha256(f"request-{sample_id}".encode()).hexdigest(),
            "response_sha256": hashlib.sha256(f"response-{sample_id}".encode()).hexdigest(),
            "response_text_sha256": hashlib.sha256(
                f"dim the kitchen lights percent number {index}".encode()
            ).hexdigest(),
            "sample_id": sample_id,
            "text": f"dim the kitchen lights percent number {index}",
        }
        for index, sample_id in enumerate(context["sample_ids"], start=1)
    ]
    outputs.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    trace_rows: list[dict[str, object]] = []
    for row in rows:
        request_id = str(row["request_id"])
        trace_rows.extend(
            (
                {
                    "channel": "MODEL_REQUEST",
                    "record_id": f"{request_id}/request",
                    "payload": {
                        "payload": {"sample_id": row["sample_id"]},
                        "payload_sha256": row["request_sha256"],
                    },
                },
                {
                    "channel": "MODEL_RESPONSE",
                    "record_id": f"{request_id}/response",
                    "payload": {
                        "response_sha256": row["response_sha256"],
                        "response_text_sha256": row["response_text_sha256"],
                        "text": row["text"],
                    },
                },
            )
        )
    trace.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in trace_rows),
        encoding="utf-8",
    )
    _write_json(plan, {"attempt_id": "attempt-fixed-selftxobs"})
    _write_json(
        failure,
        {
            "attempt_ids": {"observation": "attempt-fixed-selftxobs"},
            "error": "BundleError('missing trace manifest')",
        },
    )
    _write_json(
        attempt,
        {
            "actual": {"audio_seconds": 587.017, "calls": 104},
            "attempt_id": "attempt-fixed-selftxobs",
            "failure_reason": "BundleError('missing trace manifest')",
            "run_id": launcher.RUN_ID,
            "state": "ABORTED",
        },
    )
    monkeypatch.setattr(
        launcher,
        "RECOVERY_OBSERVATION_RELPATH",
        source.relative_to(tmp_path),
    )
    monkeypatch.setattr(
        launcher,
        "RECOVERY_ATTEMPT_RELPATH",
        attempt.relative_to(tmp_path),
    )
    monkeypatch.setattr(launcher, "RECOVERY_ATTEMPT_ID", "attempt-fixed-selftxobs")
    monkeypatch.setattr(launcher, "RECOVERY_OUTPUTS_SHA256", _sha256(outputs))
    monkeypatch.setattr(launcher, "RECOVERY_TRACE_SHA256", _sha256(trace))
    monkeypatch.setattr(launcher, "RECOVERY_PLAN_SHA256", _sha256(plan))
    monkeypatch.setattr(launcher, "RECOVERY_FAILURE_SHA256", _sha256(failure))
    monkeypatch.setattr(launcher, "RECOVERY_ATTEMPT_SHA256", _sha256(attempt))

    recovered = launcher._load_recovered_observation(tmp_path, context)
    assert recovered["passed"] is True
    assert recovered["report"].response_count == 104
    assert len(recovered["matched_material"]) == 104
    assert len(recovered["resend_ids"]) == 16

    outputs.write_text(outputs.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="outputs SHA-256 drift"):
        launcher._load_recovered_observation(tmp_path, context)
