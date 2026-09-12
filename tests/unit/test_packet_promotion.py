from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core import packet_promotion


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, document: object) -> str:
    path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
    return _sha256(path)


def _fixture(tmp_path: Path) -> tuple[Path, str, Path]:
    source_root = tmp_path / "source"
    source_root.mkdir()
    media = source_root / "one.wav"
    media.write_bytes(b"synthetic-carrier-one")
    audio_sha256 = _sha256(media)
    decoder = "a" * 64
    mmproj = "b" * 64
    sample_id = "tier1_direct:000001"
    roster_path = tmp_path / "roster.json"
    roster_sha = _write_json(
        roster_path,
        {
            "schema": "synthetic-roster-v1",
            "count": 1,
            "samples": [
                {
                    "sample_id": sample_id,
                    "media_relpath": "one.wav",
                    "audio_sha256": audio_sha256,
                }
            ],
        },
    )
    provenance_path = tmp_path / "provenance.json"
    provenance_sha = _write_json(
        provenance_path,
        {
            "schema": "synthetic-provenance-v1",
            "sources": [
                {
                    "sample_id": sample_id,
                    "audio_sha256": audio_sha256,
                    "encoder_receipt_sha256": "c" * 64,
                    "decoder_gguf_sha256": decoder,
                    "mmproj_sha256": mmproj,
                    "session_role": "inference",
                }
            ],
        },
    )
    plan_path = tmp_path / "plan.json"
    plan_sha = _write_json(
        plan_path,
        {
            "schema": packet_promotion.PLAN_SCHEMA,
            "source_root": str(source_root),
            "source_roster_path": str(roster_path),
            "source_roster_sha256": roster_sha,
            "cache_provenance_path": str(provenance_path),
            "cache_provenance_sha256": provenance_sha,
            "legacy_cache_dir": str(tmp_path / "cache"),
            "feature_root": str(tmp_path / "packets"),
            "receipt_output": str(tmp_path / "receipt.json"),
            "decoder_gguf_sha256": decoder,
            "mmproj_sha256": mmproj,
            "expected_n_embd": 2048,
            "causal_attention": True,
            "workers": 1,
        },
    )
    (tmp_path / "cache").mkdir()
    return plan_path, plan_sha, tmp_path / "receipt.json"


def test_promotes_pinned_roster_with_historical_inference_provenance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path, plan_sha, receipt_path = _fixture(tmp_path)
    captured: dict[str, object] = {}

    def fake_materialize(**kwargs: object) -> tuple[SimpleNamespace, ...]:
        captured.update(kwargs)
        return (
            SimpleNamespace(
                packet_id="tier1_direct/000001",
                packet_sha256="d" * 64,
                audio_sha256="e" * 64,
                decoder_gguf_sha256="a" * 64,
                mmproj_sha256="b" * 64,
            ),
        )

    monkeypatch.setattr(
        packet_promotion,
        "materialize_legacy_cached_speech_feature_packets",
        fake_materialize,
    )

    receipt = packet_promotion.promote_pinned_roster_legacy_cache(
        promotion_plan=plan_path,
        promotion_plan_sha256=plan_sha,
    )

    assert captured["encoder_receipt_sha256"] == receipt["cache_provenance_sha256"]
    assert captured["bindings"] == (
        {
            "packet_id": "tier1_direct/000001",
            "audio_path": str((tmp_path / "source" / "one.wav").resolve()),
        },
    )
    assert receipt["count"] == 1
    assert receipt_path.is_file()


def test_refuses_uncovered_source_before_materialization(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan_path, plan_sha, receipt_path = _fixture(tmp_path)
    document = json.loads(plan_path.read_text(encoding="utf-8"))
    provenance_path = Path(document["cache_provenance_path"])
    provenance_path.write_text(
        json.dumps({"schema": "synthetic-provenance-v1", "sources": []}),
        encoding="utf-8",
    )
    document["cache_provenance_sha256"] = _sha256(provenance_path)
    plan_sha = _write_json(plan_path, document)
    called = False

    def fake_materialize(**kwargs: object) -> tuple[SimpleNamespace, ...]:
        nonlocal called
        called = True
        return ()

    monkeypatch.setattr(
        packet_promotion,
        "materialize_legacy_cached_speech_feature_packets",
        fake_materialize,
    )

    with pytest.raises(ValueError, match="lacks matching cache provenance"):
        packet_promotion.promote_pinned_roster_legacy_cache(
            promotion_plan=plan_path,
            promotion_plan_sha256=plan_sha,
        )

    assert not called
    assert not receipt_path.exists()


def test_cli_routes_generic_promotion(monkeypatch: pytest.MonkeyPatch) -> None:
    from speech_aware_evidence_acquisition.core.driver import cli

    seen: dict[str, object] = {}

    def fake_promote(**kwargs: object) -> dict[str, object]:
        seen.update(kwargs)
        return {"schema": packet_promotion.RECEIPT_SCHEMA, "count": 1}

    monkeypatch.setattr(
        packet_promotion, "promote_pinned_roster_legacy_cache", fake_promote
    )
    assert cli.main([
        "promote-pinned-roster-speech-packets",
        "--promotion-plan",
        "/tmp/plan.json",
        "--promotion-plan-sha256",
        "f" * 64,
    ]) == 0
    assert seen == {
        "promotion_plan": Path("/tmp/plan.json"),
        "promotion_plan_sha256": "f" * 64,
    }


def test_promotes_a_synthetic_legacy_cache_entry(tmp_path: Path) -> None:
    from speech_aware_evidence_acquisition.core.model.speech_features import (
        legacy_audio_feature_cache_key,
        load_speech_feature_packet,
    )

    plan_path, plan_sha, receipt_path = _fixture(tmp_path)
    document = json.loads(plan_path.read_text(encoding="utf-8"))
    document["expected_n_embd"] = 1
    plan_sha = _write_json(plan_path, document)
    media_bytes = (tmp_path / "source" / "one.wav").read_bytes()
    cache_key = legacy_audio_feature_cache_key(media_bytes)
    (tmp_path / "cache" / f"{cache_key}_o0.feat").write_bytes(
        struct.pack("<QQf", 1, 1, 0.25)
    )

    receipt = packet_promotion.promote_pinned_roster_legacy_cache(
        promotion_plan=plan_path,
        promotion_plan_sha256=plan_sha,
    )

    packet = load_speech_feature_packet(
        tmp_path / "packets",
        "tier1_direct/000001",
    )
    assert receipt_path.is_file()
    assert receipt["packets"][0]["packet_sha256"] == packet.packet_sha256
    assert packet.encoder_receipt_sha256 == receipt["cache_provenance_sha256"]
