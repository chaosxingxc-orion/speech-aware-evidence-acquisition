from __future__ import annotations

import hashlib
import json
import wave
from collections.abc import Mapping
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.data.audio2tool_dialogue import (
    DialogueMaterializationError,
    materialize_tier7_dialogue,
    verify_dialogue_receipt,
)


def _write_wav(path: Path, *, frames: int, value: int, rate: int = 16_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample = int(value).to_bytes(2, byteorder="little", signed=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(sample * frames)


class ContentGuard(Mapping[str, object]):
    """Mapping that fails if production code tries to inspect transcript content."""

    def __init__(self, values: dict[str, object]) -> None:
        self._values = values

    def __getitem__(self, key: str) -> object:
        if key == "content":
            raise AssertionError("textual chat content must never be accessed")
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def get(self, key: str, default: object = None) -> object:
        if key == "content":
            raise AssertionError("textual chat content must never be accessed")
        return self._values.get(key, default)


def _entry() -> dict[str, object]:
    return {
        "id": 9,
        "tier": "tier7_multiturn",
        "chat_history": [
            ContentGuard(
                {
                    "role": "user",
                    "content": "private first transcript",
                    "path": "tier7_multiturn_audios/query_00009/turn_00_user.wav",
                    "duration": 0.001,
                }
            ),
            ContentGuard(
                {
                    "role": "agent",
                    "content": "private reply transcript",
                    "path": "tier7_multiturn_audios/query_00009/turn_01_agent.wav",
                    "duration": 0.002,
                }
            ),
            ContentGuard(
                {
                    "role": "user",
                    "content": "private final transcript",
                    "path": "tier7_multiturn_audios/query_00009/turn_02_user.wav",
                    "duration": 0.003,
                }
            ),
        ],
    }


def _materialize(tmp_path: Path, suffix: str) -> tuple[Path, Path, dict[str, object]]:
    public = tmp_path / "public"
    for index, frames in enumerate((16, 32, 48)):
        role = "agent" if index == 1 else "user"
        _write_wav(
            public
            / "tier7_multiturn_audios"
            / "query_00009"
            / f"turn_{index:02d}_{role}.wav",
            frames=frames,
            value=index + 1,
        )
    output = tmp_path / suffix / "dialogue.wav"
    receipt_path = tmp_path / suffix / "dialogue.receipt.json"
    receipt = materialize_tier7_dialogue(
        sample_id="tier7_multiturn:000009",
        entry=_entry(),
        public_dir=public,
        output_wav=output,
        receipt_path=receipt_path,
        silence_seconds=0.001,
    )
    return output, receipt_path, receipt


def test_dialogue_materializer_is_deterministic_and_never_accesses_content(tmp_path: Path) -> None:
    first_wav, first_receipt_path, first = _materialize(tmp_path, "first")
    second_wav, second_receipt_path, second = _materialize(tmp_path, "second")

    assert first == second
    assert first_wav.read_bytes() == second_wav.read_bytes()
    assert first_receipt_path.read_bytes() == second_receipt_path.read_bytes()
    assert b"private" not in first_receipt_path.read_bytes()


def test_dialogue_wav_geometry_order_roles_and_hashes_are_auditable(tmp_path: Path) -> None:
    output, receipt_path, receipt = _materialize(tmp_path, "run")

    with wave.open(str(output), "rb") as handle:
        assert handle.getnchannels() == 1
        assert handle.getsampwidth() == 2
        assert handle.getframerate() == 16_000
        assert handle.getnframes() == 16 + 16 + 32 + 16 + 48
        rendered = handle.readframes(handle.getnframes())
    assert rendered == (
        (1).to_bytes(2, "little", signed=True) * 16
        + b"\x00\x00" * 16
        + (2).to_bytes(2, "little", signed=True) * 32
        + b"\x00\x00" * 16
        + (3).to_bytes(2, "little", signed=True) * 48
    )
    assert [turn["role"] for turn in receipt["source_turns"]] == ["user", "agent", "user"]
    assert [turn["turn_index"] for turn in receipt["source_turns"]] == [0, 1, 2]
    assert receipt["output"]["frame_count"] == 128
    assert receipt["output"]["audio_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert verify_dialogue_receipt(receipt_path, public_dir=tmp_path / "public", output_wav=output) == receipt


def test_dialogue_receipt_verifier_rejects_tampered_hash(tmp_path: Path) -> None:
    output, receipt_path, receipt = _materialize(tmp_path, "run")
    receipt["output"]["audio_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")

    with pytest.raises(DialogueMaterializationError, match="output WAV SHA-256"):
        verify_dialogue_receipt(receipt_path, public_dir=tmp_path / "public", output_wav=output)


def test_dialogue_materializer_refuses_role_or_wav_geometry_drift(tmp_path: Path) -> None:
    public = tmp_path / "public"
    for index, frames in enumerate((16, 32, 48)):
        role = "agent" if index == 1 else "user"
        _write_wav(
            public / "tier7_multiturn_audios" / "query_00009" / f"turn_{index:02d}_{role}.wav",
            frames=frames,
            value=index + 1,
            rate=22_050 if index == 1 else 16_000,
        )
    entry = _entry()
    entry["chat_history"][1] = ContentGuard(
        {
            "role": "user",
            "content": "private",
            "path": "tier7_multiturn_audios/query_00009/turn_01_agent.wav",
            "duration": 0.002,
        }
    )
    with pytest.raises(DialogueMaterializationError, match="alternate"):
        materialize_tier7_dialogue(
            sample_id="tier7_multiturn:000009",
            entry=entry,
            public_dir=public,
            output_wav=tmp_path / "bad.wav",
            receipt_path=tmp_path / "bad.json",
        )

    entry = _entry()
    with pytest.raises(DialogueMaterializationError, match="WAV format"):
        materialize_tier7_dialogue(
            sample_id="tier7_multiturn:000009",
            entry=entry,
            public_dir=public,
            output_wav=tmp_path / "bad-format.wav",
            receipt_path=tmp_path / "bad-format.json",
        )
