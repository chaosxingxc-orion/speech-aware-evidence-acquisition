from __future__ import annotations

import importlib.util
from pathlib import Path
import wave

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-factorial-128-roster-v1/build_roster.py"
)


def _module():
    spec = importlib.util.spec_from_file_location(
        "build_a2t_select_fill_factorial_roster",
        SCRIPT,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_manifest_projection_emits_only_identity_hash_and_media_fields() -> None:
    module = _module()
    entry = {
        "id": 7,
        "query_idx": 70,
        "query": "Set the kitchen light to blue.",
        "path": "tier1_direct_audios/query_00070/7.wav",
        "duration": 1.25,
        "tool_name": "must-not-leave-projection",
        "expected_tool_call": "must-not-leave-projection",
        "extracted_params": {"secret": True},
        "additional_tool_calls": ["must-not-leave-projection"],
    }

    projected = module._project_manifest_entry("tier1_direct", entry)

    assert set(projected) == {
        "audio_relpath_in_public",
        "audio_seconds",
        "id",
        "normalized_token_class_sha256",
        "query_idx",
    }
    assert projected["id"] == 7
    assert projected["query_idx"] == 70
    assert projected["audio_seconds"] == 1.25
    rendered = str(projected)
    assert "Set the kitchen" not in rendered
    assert "must-not-leave-projection" not in rendered
    assert "secret" not in rendered


def test_tier7_projection_uses_final_request_text_and_media_only() -> None:
    module = _module()
    projected = module._project_manifest_entry(
        "tier7_multiturn",
        {
            "id": 8,
            "query_idx": 80,
            "user_request": "Actually set it to seventy percent.",
            "chat_history": [
                {"role": "assistant", "content": "Earlier response."},
                {
                    "role": "user",
                    "path": "tier7_multiturn_audios/query_00080/8.wav",
                    "duration": 2.5,
                },
            ],
            "expected_tool_call": "must-not-leave-projection",
        },
    )

    assert projected["id"] == 8
    assert projected["audio_seconds"] == 2.5
    assert "Actually set it" not in str(projected)


def test_builder_source_does_not_use_any_gold_loader() -> None:
    source = SCRIPT.read_text(encoding="ascii")
    assert "a2t_pool_rows" not in source
    assert "expected_tool_calls_for_entry" not in source
    assert "load_expected_calls" not in source
    assert "reproduction.toolcall_gold" not in source


def test_wav_metadata_accepts_manifest_millisecond_rounding(tmp_path: Path) -> None:
    module = _module()
    path = tmp_path / "rounded.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16_000)
        handle.writeframes(b"\x00\x00" * 100)

    digest, seconds = module._wav_metadata(path, 0.006)

    assert len(digest) == 64
    assert seconds == 0.00625
    with pytest.raises(RuntimeError, match="duration disagrees"):
        module._wav_metadata(path, 0.005)
