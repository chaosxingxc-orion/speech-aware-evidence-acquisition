from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import packet_promotion
from speech_aware_evidence_acquisition.core.flight.runtime import (
    FlightRuntime,
    load_promotion_receipt,
)
from speech_aware_evidence_acquisition.core.model.speech_features import (
    legacy_audio_feature_cache_key,
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.preparation_feature_provenance import (
    canonical_receipt_sha256,
)
from speech_aware_evidence_acquisition.core.session.receipt import (
    ModelFileRef,
    SESSION_RECEIPT_SCHEMA,
    SessionReceipt,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, value: object) -> str:
    path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")
    return _sha(path)


def _descriptor(path: Path, value: dict[str, object], *, canonical: bool) -> dict[str, str]:
    file_sha256 = _write_json(path, value)
    result = {"path": str(path), "file_sha256": file_sha256}
    if canonical:
        result["document_sha256"] = canonical_receipt_sha256(value)
    return result


def _fixture(tmp_path: Path) -> tuple[Path, str, Path, str]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    media = source_root / "one.wav"
    media.write_bytes(b"synthetic-carrier-one")
    audio_sha256 = _sha(media)
    sample_id = "tier1_direct:000001"
    original_roster_sha256 = "f" * 64
    decoder = "a" * 64
    mmproj = "b" * 64
    binary = "c" * 64
    cache = tmp_path / "cache"
    cache.mkdir()
    cache_key = legacy_audio_feature_cache_key(media.read_bytes())
    cache_file = cache / f"{cache_key}_o0.feat"
    cache_file.write_bytes(struct.pack("<QQf", 1, 1, 0.25))

    runtime = {
        "llama_cpp": {"binary_path": "bin/server", "binary_sha256": binary},
        "gguf_files": [
            {"path": "weights/decoder.gguf", "sha256": decoder},
            {"path": "weights/mmproj.gguf", "sha256": mmproj},
        ],
    }
    runtime_descriptor = _descriptor(tmp_path / "runtime.json", runtime, canonical=True)
    session = SessionReceipt(
        schema=SESSION_RECEIPT_SCHEMA,
        study="speech-aware-evidence-acquisition",
        session_id="legacy-1",
        binary_path="bin/server",
        binary_sha256=binary,
        argv=("server",),
        pid=1,
        host="127.0.0.1",
        port=8080,
        model_files=(
            ModelFileRef(path="weights/decoder.gguf", sha256=decoder),
            ModelFileRef(path="weights/mmproj.gguf", sha256=mmproj),
        ),
        started_at="2026-01-01T00:00:00Z",
        startup_stdout_sha256="d" * 64,
    ).as_json()
    session_descriptor = _descriptor(tmp_path / "session.json", session, canonical=True)
    stop = {
        "session_id": "legacy-1",
        "session_role": "legacy",
        "session_receipt_sha256": canonical_receipt_sha256(session),
        "runtime_receipt_sha256": canonical_receipt_sha256(runtime),
        "forced": False,
        "termination_signal": "SIGTERM",
    }
    stop_descriptor = _descriptor(tmp_path / "stop.json", stop, canonical=True)
    model_descriptor = _descriptor(
        tmp_path / "model.json",
        {"server_env": {"LLAMA_MTMD_FEAT_CACHE_DIR": str(cache)}},
        canonical=False,
    )

    roster_path = tmp_path / "roster.json"
    roster_sha256 = _write_json(
        roster_path,
        {
            "schema": "synthetic-roster-v1",
            "count": 1,
            "source_roster_original_sha256": original_roster_sha256,
            "samples": [
                {
                    "sample_id": sample_id,
                    "media_relpath": "one.wav",
                    "audio_sha256": audio_sha256,
                }
            ],
        },
    )
    audit_path = tmp_path / "audit.json"
    audit_sha256 = _write_json(
        audit_path,
        {
            "schema": packet_promotion.AUDIT_SCHEMA,
            "run_id": "synthetic",
            "registration_sha256": "e" * 64,
            "roster_sha256": original_roster_sha256,
            "legacy_cache_dir": str(cache),
            "expected_n_embd": 1,
            "count": 1,
            "status_counts": {"valid": 1},
            "elapsed_seconds": 0.0,
            "entries": [
                {
                    "sample_id": sample_id,
                    "status": "valid",
                    "inspection": {
                        "audio_sha256": audio_sha256,
                        "cache_key": cache_key,
                        "chunks": [
                            {
                                "ordinal": 0,
                                "relative_filename": cache_file.name,
                                "file_sha256": _sha(cache_file),
                                "file_size": cache_file.stat().st_size,
                                "n_tokens": 1,
                                "n_embd": 1,
                            }
                        ],
                    },
                }
            ],
            "encoder_provenance": "not established by this inspection",
            "new_encoder_contacts": 0,
        },
    )
    provenance_path = tmp_path / "provenance.json"
    provenance_sha256 = _write_json(
        provenance_path,
        {
            "schema": "synthetic-provenance-v1",
            "cache_audit_sha256": audit_sha256,
            "source_roster_sha256": original_roster_sha256,
            "sessions": [
                {
                    "session_id": "legacy-1",
                    "runtime_receipt": runtime_descriptor,
                    "session_receipt": session_descriptor,
                    "stop_receipt": stop_descriptor,
                    "model_fragment": model_descriptor,
                }
            ],
            "sources": [
                {
                    "sample_id": sample_id,
                    "audio_sha256": audio_sha256,
                    "encoder_receipt_sha256": canonical_receipt_sha256(runtime),
                    "decoder_gguf_sha256": decoder,
                    "mmproj_sha256": mmproj,
                    "session_role": "legacy",
                    "session_id": "legacy-1",
                }
            ],
        },
    )
    plan_path = tmp_path / "plan.json"
    plan_sha256 = _write_json(
        plan_path,
        {
            "schema": packet_promotion.PLAN_SCHEMA,
            "source_root": str(source_root),
            "source_roster_path": str(roster_path),
            "source_roster_sha256": roster_sha256,
            "cache_provenance_path": str(provenance_path),
            "cache_provenance_sha256": provenance_sha256,
            "cache_audit_path": str(audit_path),
            "cache_audit_sha256": audit_sha256,
            "legacy_cache_dir": str(cache),
            "feature_root": str(tmp_path / "packets"),
            "receipt_output": str(tmp_path / "receipt.json"),
            "decoder_gguf_sha256": decoder,
            "mmproj_sha256": mmproj,
            "expected_n_embd": 1,
            "causal_attention": True,
            "workers": 1,
        },
    )
    return plan_path, plan_sha256, tmp_path / "receipt.json", audio_sha256


def test_promotes_audit_pinned_synthetic_cache_and_flight_consumes_it(
    tmp_path: Path,
) -> None:
    plan_path, plan_sha256, receipt_path, audio_sha256 = _fixture(tmp_path)

    receipt = packet_promotion.promote_pinned_roster_legacy_cache(
        promotion_plan=plan_path, promotion_plan_sha256=plan_sha256
    )

    packet = load_speech_feature_packet(tmp_path / "packets", "tier1_direct/000001")
    loaded = load_promotion_receipt(receipt_path)
    runtime = object.__new__(FlightRuntime)
    runtime._promotion_receipt = loaded
    runtime._samples = (SimpleNamespace(sample_id="tier1_direct:000001"),)
    runtime._promotion_receipt_path = lambda: receipt_path

    assert receipt["runtime_receipt_sha256"] == receipt["cache_provenance_sha256"]
    assert packet.audio_sha256 == audio_sha256
    assert packet.encoder_receipt_sha256 == receipt["runtime_receipt_sha256"]
    assert receipt["packets"][0]["encoder_receipt_sha256"] == packet.encoder_receipt_sha256
    assert runtime.speech_packet_bindings() == {
        "tier1_direct:000001": {
            "packet_id": "tier1_direct/000001",
            "sha256": packet.packet_sha256,
        }
    }


def test_refuses_cache_audit_drift_before_materialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path, plan_sha256, _receipt_path, _audio_sha256 = _fixture(tmp_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    cache_file = next(Path(plan["legacy_cache_dir"]).glob("*.feat"))
    cache_file.write_bytes(struct.pack("<QQf", 1, 1, 0.5))
    called = False

    def fake_materialize(**kwargs: object) -> tuple[SimpleNamespace, ...]:
        nonlocal called
        called = True
        return ()

    monkeypatch.setattr(
        packet_promotion, "materialize_legacy_cached_speech_feature_packets", fake_materialize
    )
    with pytest.raises(ValueError, match="legacy cache audit drift"):
        packet_promotion.promote_pinned_roster_legacy_cache(
            promotion_plan=plan_path, promotion_plan_sha256=plan_sha256
        )
    assert not called


def test_cli_routes_generic_promotion(monkeypatch: pytest.MonkeyPatch) -> None:
    from speech_aware_evidence_acquisition.core.driver import cli

    seen: dict[str, object] = {}

    def fake_promote(**kwargs: object) -> dict[str, object]:
        seen.update(kwargs)
        return {"schema": packet_promotion.RECEIPT_SCHEMA, "count": 1}

    monkeypatch.setattr(packet_promotion, "promote_pinned_roster_legacy_cache", fake_promote)
    assert cli.main([
        "promote-pinned-roster-speech-packets",
        "--promotion-plan", "/tmp/plan.json",
        "--promotion-plan-sha256", "f" * 64,
    ]) == 0
    assert seen == {
        "promotion_plan": Path("/tmp/plan.json"),
        "promotion_plan_sha256": "f" * 64,
    }


def test_rechecks_pinned_cache_before_receipt_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path, plan_sha256, receipt_path, _audio_sha256 = _fixture(tmp_path)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    cache_file = next(Path(plan["legacy_cache_dir"]).glob("*.feat"))
    original = packet_promotion.materialize_legacy_cached_speech_feature_packets

    def materialize_then_mutate(**kwargs: object):
        packets = original(**kwargs)
        cache_file.write_bytes(struct.pack("<QQf", 1, 1, 0.5))
        return packets

    monkeypatch.setattr(
        packet_promotion,
        "materialize_legacy_cached_speech_feature_packets",
        materialize_then_mutate,
    )
    with pytest.raises(ValueError, match="legacy cache audit drift"):
        packet_promotion.promote_pinned_roster_legacy_cache(
            promotion_plan=plan_path, promotion_plan_sha256=plan_sha256
        )
    assert not receipt_path.exists()


@pytest.mark.parametrize("change", ["role", "model"])
def test_source_claim_cannot_relabel_runtime_or_weights(tmp_path, change):
    plan_path, _, receipt_path, _ = _fixture(tmp_path)
    plan = json.loads(plan_path.read_text())
    path = Path(plan["cache_provenance_path"])
    provenance = json.loads(path.read_text())
    if change == "role":
        provenance["sources"][0]["session_role"] = "preprocess"
    else:
        plan["decoder_gguf_sha256"] = "e" * 64
        provenance["sources"][0]["decoder_gguf_sha256"] = "e" * 64
    plan["cache_provenance_sha256"] = _write_json(path, provenance)
    plan_sha256 = _write_json(plan_path, plan)
    with pytest.raises(ValueError, match="runtime.*(hash|model)"):
        packet_promotion.promote_pinned_roster_legacy_cache(
            promotion_plan=plan_path, promotion_plan_sha256=plan_sha256
        )
    assert not receipt_path.exists()
    assert not Path(plan["feature_root"]).exists()
