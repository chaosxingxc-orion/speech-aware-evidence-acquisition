"""Deterministic complete-dialogue WAV materialization for Audio2Tool tier 7.

Only turn role, audio path, and declared duration cross the manifest boundary.
The textual ``content`` value is never accessed or copied. Source audio remains
auditable through chronological turn metadata and SHA-256 hashes.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import wave
from pathlib import Path
from typing import Mapping

from .audio2tool import _audio_seconds, _validate_audio_relpath

TIER7 = "tier7_multiturn"
DEFAULT_SILENCE_SECONDS = 0.25


class DialogueMaterializationError(RuntimeError):
    """A dialogue identity, role, source WAV, or receipt invariant failed."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _payload_sha256(payload: Mapping[str, object]) -> str:
    scrubbed = {key: value for key, value in payload.items() if key != "receipt_payload_sha256"}
    encoded = json.dumps(
        scrubbed, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        temporary = Path(handle.name)
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


def _validated_turns(
    entry: Mapping[str, object], public_dir: Path
) -> tuple[dict[str, object], ...]:
    history = entry.get("chat_history")
    if not isinstance(history, list) or not history:
        raise DialogueMaterializationError("tier-7 chat_history must be a non-empty list")
    turns: list[dict[str, object]] = []
    for index, turn in enumerate(history):
        if not isinstance(turn, Mapping):
            raise DialogueMaterializationError(f"chat_history turn {index} must be an object")
        role = turn.get("role")
        expected_role = "user" if index % 2 == 0 else "agent"
        if role != expected_role:
            raise DialogueMaterializationError(
                "tier-7 chat_history roles must alternate user/agent starting with user"
            )
        try:
            relpath = _validate_audio_relpath(turn.get("path"), f"tier-7 turn {index}")
            declared_seconds = _audio_seconds(
                turn.get("duration"), f"tier-7 turn {index}"
            )
        except Exception as error:
            raise DialogueMaterializationError(str(error)) from error
        source = public_dir / relpath
        if not source.is_file():
            raise DialogueMaterializationError(f"tier-7 turn {index} WAV is missing: {source}")
        turns.append(
            {
                "declared_audio_seconds": declared_seconds,
                "media_relpath": relpath,
                "role": role,
                "source_path": source,
                "turn_index": index,
            }
        )
    if turns[-1]["role"] != "user":
        raise DialogueMaterializationError("tier-7 dialogue must end with a user turn")
    return tuple(turns)


def materialize_tier7_dialogue(
    *,
    sample_id: str,
    entry: Mapping[str, object],
    public_dir: Path,
    output_wav: Path,
    receipt_path: Path,
    silence_seconds: float = DEFAULT_SILENCE_SECONDS,
    overwrite: bool = False,
) -> dict[str, object]:
    """Write one chronological query WAV and its auditable English receipt."""

    expected_id = entry.get("id")
    if entry.get("tier") != TIER7 or sample_id != f"{TIER7}:{expected_id:06d}":
        raise DialogueMaterializationError("sample identity does not match a tier-7 entry")
    if (
        isinstance(silence_seconds, bool)
        or not isinstance(silence_seconds, (int, float))
        or not math.isfinite(silence_seconds)
        or silence_seconds < 0.0
    ):
        raise DialogueMaterializationError("silence seconds must be finite and non-negative")
    output = Path(output_wav)
    receipt_file = Path(receipt_path)
    if not overwrite and (output.exists() or receipt_file.exists()):
        raise DialogueMaterializationError("output WAV or receipt already exists")

    public = Path(public_dir)
    turns = _validated_turns(entry, public)
    source_material: list[tuple[dict[str, object], bytes]] = []
    format_tuple: tuple[int, int, int, str] | None = None
    for turn in turns:
        source = turn["source_path"]
        try:
            with wave.open(str(source), "rb") as handle:
                current_format = (
                    handle.getnchannels(),
                    handle.getsampwidth(),
                    handle.getframerate(),
                    handle.getcomptype(),
                )
                frame_count = handle.getnframes()
                frames = handle.readframes(frame_count)
        except (OSError, EOFError, wave.Error) as error:
            raise DialogueMaterializationError(f"cannot read source WAV {source}: {error}") from error
        if current_format[3] != "NONE":
            raise DialogueMaterializationError("source WAV must contain uncompressed PCM")
        if format_tuple is None:
            format_tuple = current_format
        elif current_format != format_tuple:
            raise DialogueMaterializationError("every dialogue turn must have the same WAV format")
        channels, sample_width, sample_rate_hz, _ = current_format
        expected_bytes = frame_count * channels * sample_width
        if len(frames) != expected_bytes:
            raise DialogueMaterializationError(f"source WAV frame geometry is truncated: {source}")
        clean = {
            key: value for key, value in turn.items() if key != "source_path"
        }
        clean.update(
            {
                "actual_audio_seconds": frame_count / sample_rate_hz,
                "audio_sha256": _sha256(source),
                "frame_count": frame_count,
            }
        )
        source_material.append((clean, frames))
    assert format_tuple is not None
    channels, sample_width, sample_rate_hz, _ = format_tuple
    silence_frames = int(round(float(silence_seconds) * sample_rate_hz))
    silence_bytes = b"\x00" * silence_frames * channels * sample_width
    output_frames = sum(int(turn["frame_count"]) for turn, _ in source_material)
    output_frames += silence_frames * (len(source_material) - 1)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, delete=False) as handle:
        temporary_wav = Path(handle.name)
    try:
        with wave.open(str(temporary_wav), "wb") as handle:
            handle.setnchannels(channels)
            handle.setsampwidth(sample_width)
            handle.setframerate(sample_rate_hz)
            for index, (_turn, frames) in enumerate(source_material):
                if index:
                    handle.writeframesraw(silence_bytes)
                handle.writeframesraw(frames)
            handle.writeframes(b"")
        os.replace(temporary_wav, output)
    finally:
        if temporary_wav.exists():
            temporary_wav.unlink()

    payload: dict[str, object] = {
        "dialogue_protocol": (
            "Chronological speech turns alternate user and agent, begin with user, "
            "and end with the current user request."
        ),
        "output": {
            "audio_seconds": output_frames / sample_rate_hz,
            "audio_sha256": _sha256(output),
            "channel_count": channels,
            "frame_count": output_frames,
            "sample_rate_hz": sample_rate_hz,
            "sample_width_bytes": sample_width,
            "wav_filename": output.name,
        },
        "sample_id": sample_id,
        "schema": "saea-a2t-tier7-complete-dialogue-receipt-v1",
        "silence": {
            "frame_count_between_turns": silence_frames,
            "seconds_between_turns": silence_frames / sample_rate_hz,
        },
        "source_turns": [turn for turn, _frames in source_material],
        "textual_content_accessed": False,
        "tier": TIER7,
    }
    payload["receipt_payload_sha256"] = _payload_sha256(payload)
    _write_json_atomic(receipt_file, payload)
    return payload


def verify_dialogue_receipt(
    receipt_path: Path, *, public_dir: Path, output_wav: Path
) -> dict[str, object]:
    """Re-hash every source and the derived WAV and return the verified receipt."""

    try:
        payload = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DialogueMaterializationError(f"cannot read dialogue receipt: {error}") from error
    if not isinstance(payload, dict):
        raise DialogueMaterializationError("dialogue receipt must be an object")
    output = payload.get("output")
    if not isinstance(output, Mapping) or output.get("audio_sha256") != _sha256(Path(output_wav)):
        raise DialogueMaterializationError("output WAV SHA-256 does not match the receipt")
    source_turns = payload.get("source_turns")
    if not isinstance(source_turns, list):
        raise DialogueMaterializationError("dialogue receipt source_turns is invalid")
    for turn in source_turns:
        if not isinstance(turn, Mapping):
            raise DialogueMaterializationError("dialogue receipt source turn is invalid")
        relpath = turn.get("media_relpath")
        try:
            validated = _validate_audio_relpath(relpath, "dialogue receipt source")
        except Exception as error:
            raise DialogueMaterializationError(str(error)) from error
        if turn.get("audio_sha256") != _sha256(Path(public_dir) / validated):
            raise DialogueMaterializationError("source WAV SHA-256 does not match the receipt")
    if payload.get("receipt_payload_sha256") != _payload_sha256(payload):
        raise DialogueMaterializationError("receipt payload SHA-256 does not match")
    return payload


__all__ = [
    "DEFAULT_SILENCE_SECONDS",
    "DialogueMaterializationError",
    "TIER7",
    "materialize_tier7_dialogue",
    "verify_dialogue_receipt",
]
