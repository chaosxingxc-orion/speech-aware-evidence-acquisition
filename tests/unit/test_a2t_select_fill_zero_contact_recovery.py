"""Tests for the model-free SELECT/FILL V5 recovery sealer."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.contracts import TraceRecord


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-agentloop-104-v1/launcher/"
    "recover_select_fill_v5.py"
)


def _module():
    name = "test_a2t_select_fill_zero_contact_recovery_script"
    spec = importlib.util.spec_from_file_location(name, SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _trace(sample_ids: tuple[str, ...]) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for index, sample_id in enumerate(sample_ids, start=1):
        request_id = f"phase-{index:04d}"
        inner = {"request_id": request_id, "sample_id": sample_id}
        text = f'{{"opaque":"answer-{index}"}}'
        entries = (
            (
                "MODEL_REQUEST",
                f"{request_id}/request",
                {
                    "arm": "speech-feature-query",
                    "payload": inner,
                    "payload_sha256": hashlib.sha256(
                        json.dumps(
                            inner,
                            ensure_ascii=True,
                            sort_keys=True,
                            separators=(",", ":"),
                        ).encode("ascii")
                    ).hexdigest(),
                },
            ),
            (
                "MODEL_RESPONSE",
                f"{request_id}/response",
                {
                    "response_sha256": f"{index:064x}",
                    "response_text_sha256": hashlib.sha256(
                        text.encode("ascii")
                    ).hexdigest(),
                    "text": text,
                    "usage": {},
                },
            ),
            (
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
        rows.extend(
            {"channel": channel, "record_id": record_id, "payload": payload}
            for channel, record_id, payload in entries
        )
    return tuple(rows)


def test_derives_score_rows_and_trace_manifest_only_from_transport_records() -> None:
    module = _module()
    sample_ids = ("sample-a", "sample-b")
    documents = _trace(sample_ids)

    rows, cost, hashes = module._derive_trace_material(
        documents,
        phase="JOINT_ONE_CALL",
        sample_ids=sample_ids,
    )

    assert tuple(row["sample_id"] for row in rows) == sample_ids
    assert tuple(row["text"] for row in rows) == (
        '{"opaque":"answer-1"}',
        '{"opaque":"answer-2"}',
    )
    assert cost["calls_used"] == 2
    assert cost["audio_seconds_used"] == 2.5
    assert hashes == {
        str(document["record_id"]): TraceRecord(
            str(document["channel"]),
            str(document["record_id"]),
            document["payload"],
        ).content_hash()
        for document in documents
    }


def test_derivation_fails_closed_on_missing_or_hash_drifted_response() -> None:
    module = _module()
    documents = list(_trace(("sample-a",)))
    documents[1]["payload"]["response_text_sha256"] = "0" * 64  # type: ignore[index]

    with pytest.raises(module.RecoveryError, match="response text hash drift"):
        module._derive_trace_material(
            tuple(documents),
            phase="FILL",
            sample_ids=("sample-a",),
        )

    with pytest.raises(module.RecoveryError, match="channel counts"):
        module._derive_trace_material(
            _trace(("sample-a",))[:-1],
            phase="FILL",
            sample_ids=("sample-a",),
        )


def test_send_accounting_requires_exact_phase_by_sample_cross_product() -> None:
    module = _module()
    phases = tuple(module.PHASE_ORDER)
    sample_ids = ("sample-a", "sample-b")
    rows = tuple(
        {
            "phase": phase,
            "sample_id": sample_id,
            "body_sha256": hashlib.sha256(
                f"{phase}/{sample_id}".encode("ascii")
            ).hexdigest(),
            "status": "CONSUMED_BEFORE_IO",
        }
        for phase in phases
        for sample_id in sample_ids
    )

    module._validate_send_accounting(
        rows,
        phases=phases,
        sample_ids=sample_ids,
    )

    with pytest.raises(module.RecoveryError, match="send accounting"):
        module._validate_send_accounting(
            rows[:-1],
            phases=phases,
            sample_ids=sample_ids,
        )


def test_reuses_verified_direct_bundle_without_copying_or_rewriting(
    tmp_path, monkeypatch
) -> None:
    module = _module()
    source = tmp_path / "source-direct"
    source.mkdir()
    paths = {}
    for field, suffix in (
        ("manifest", "run-manifest.json"),
        ("outputs", "outputs.jsonl"),
        ("trace", "trace.jsonl"),
        ("trace_manifest", "trace-manifest.json"),
    ):
        path = source / suffix
        path.write_bytes(f"immutable-{field}\n".encode("ascii"))
        paths[f"direct:{field}"] = path
    before = {path: path.read_bytes() for path in paths.values()}
    verified_paths = []

    def verify(path):
        verified_paths.append(Path(path))
        return SimpleNamespace(outputs_rows=(object(), object()), attempt_state="ABORTED")

    monkeypatch.setattr(module, "verify_bundle", verify)

    descriptor = module._reuse_direct_bundle(paths, sample_count=2)

    assert verified_paths == [paths["direct:manifest"]]
    assert descriptor["manifest"] == str(paths["direct:manifest"].resolve())
    assert descriptor["source_manifest_reused_without_rewriting"] is True
    assert set(descriptor["source_bundle"]) == {
        "manifest",
        "outputs",
        "trace",
        "trace_manifest",
    }
    assert {path: path.read_bytes() for path in paths.values()} == before
    assert set(source.iterdir()) == set(before)
