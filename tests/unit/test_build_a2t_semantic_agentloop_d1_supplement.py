"""Model-free D1 successor coverage for the fresh Audio2Tool roster."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import wave

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts/build_a2t_semantic_agentloop_d1_supplement.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("a2t_d1_supplement_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_wav(path: Path, *, frames: int = 1600, rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\0\0" * frames)


def test_builder_creates_exact_hash_bound_audio2tool_successor(tmp_path: Path) -> None:
    module = _load_script_module()
    data_root = tmp_path / "data"
    media = data_root / "datasets/audio2tool/public/tier1/query.wav"
    _write_wav(media)
    digest = hashlib.sha256(media.read_bytes()).hexdigest()
    roster = tmp_path / "roster.json"
    roster.write_text(
        json.dumps(
            {
                "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
                "carrier": "audio2tool",
                "split_role": "discovery",
                "count": 1,
                "items": [
                    {
                        "sample_id": "tier1_direct:000001",
                        "media_relpath": ("datasets/audio2tool/public/tier1/query.wav"),
                        "audio_sha256": digest,
                        "audio_seconds": 0.1,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    parent = tmp_path / "d1-identity.json"
    parent.write_text(
        json.dumps(
            {"carriers": {"audio2tool": {"layers": {"media": {"manifest": []}}}}},
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    supplement = module.build_supplement(
        roster_path=roster,
        data_root=data_root,
        parent_d1_path=parent,
    )

    assert supplement["schema"] == "saea-d1-media-supplement-v1"
    assert supplement["carrier_lock_key"] == "audio2tool"
    assert (
        supplement["source_binding_sha256"]
        == hashlib.sha256(roster.read_bytes()).hexdigest()
    )
    assert (
        supplement["parent_d1_sha256"]
        == hashlib.sha256(parent.read_bytes()).hexdigest()
    )
    assert supplement["count"] == 1
    entry = supplement["manifest"][0]
    assert entry == {
        "id": "tier1_direct:000001",
        "media_relpath": "datasets/audio2tool/public/tier1/query.wav",
        "bytes": media.stat().st_size,
        "sha256": digest,
        "audio_seconds": 0.1,
        "sample_rate_hz": 16000,
        "roles": ["query"],
    }
    assert supplement["manifest_sha256"] == module.canonical_sha256(
        supplement["manifest"]
    )


def test_builder_refuses_parent_overlap_and_duration_drift(tmp_path: Path) -> None:
    module = _load_script_module()
    data_root = tmp_path / "data"
    media = data_root / "datasets/audio2tool/public/tier1/query.wav"
    _write_wav(media)
    sample_id = "tier1_direct:000001"
    roster = tmp_path / "roster.json"
    roster.write_text(
        json.dumps(
            {
                "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
                "carrier": "audio2tool",
                "split_role": "discovery",
                "count": 1,
                "items": [
                    {
                        "sample_id": sample_id,
                        "media_relpath": ("datasets/audio2tool/public/tier1/query.wav"),
                        "audio_sha256": hashlib.sha256(media.read_bytes()).hexdigest(),
                        "audio_seconds": 0.2,
                    }
                ],
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    parent = tmp_path / "d1-identity.json"
    parent.write_text(
        json.dumps(
            {
                "carriers": {
                    "audio2tool": {
                        "layers": {"media": {"manifest": [{"id": sample_id}]}}
                    }
                }
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicates parent D1"):
        module.build_supplement(
            roster_path=roster,
            data_root=data_root,
            parent_d1_path=parent,
        )

    parent.write_text(
        json.dumps(
            {"carriers": {"audio2tool": {"layers": {"media": {"manifest": []}}}}},
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duration drift"):
        module.build_supplement(
            roster_path=roster,
            data_root=data_root,
            parent_d1_path=parent,
        )
