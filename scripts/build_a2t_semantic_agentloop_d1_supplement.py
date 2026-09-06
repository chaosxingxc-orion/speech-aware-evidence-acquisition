#!/usr/bin/env python3
"""Build the additive D1 media receipt for the fresh Audio2Tool 104 roster.

The source roster contains only sample identifiers and measured media facts.
This builder re-hashes each WAV and reads only its container header for duration
and sample rate. It never loads task text, labels, transcripts, annotations,
model output, scores, test data, or future turns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
import wave


REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-fresh-agentloop-roster"
    / "flight-roster-receipt.json"
)
DEFAULT_PARENT_D1 = REPO / "docs/receipts/artifacts/d1-identity.json"
DEFAULT_OUTPUT = REPO / "docs/receipts/artifacts" / "d1-a2t-semantic-agentloop-104.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(document: object) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return document


def _parent_ids(parent: Mapping[str, Any]) -> set[str]:
    carriers = parent.get("carriers")
    carrier = carriers.get("audio2tool") if isinstance(carriers, Mapping) else None
    layers = carrier.get("layers") if isinstance(carrier, Mapping) else None
    media = layers.get("media") if isinstance(layers, Mapping) else None
    manifest = media.get("manifest") if isinstance(media, Mapping) else None
    if not isinstance(manifest, list):
        raise ValueError("parent D1 lacks the Audio2Tool media manifest")
    ids = {
        entry.get("id")
        for entry in manifest
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    }
    if len(ids) != len(manifest):
        raise ValueError("parent D1 Audio2Tool media IDs are malformed or duplicated")
    return ids


def _resolve_media(
    data_root: Path, relpath: object, sample_id: str
) -> tuple[str, Path]:
    if not isinstance(relpath, str) or not relpath or "\\" in relpath:
        raise ValueError(f"media path is malformed for {sample_id}")
    pure = PurePosixPath(relpath)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"media path escapes the data root for {sample_id}")
    normalized = pure.as_posix()
    root = Path(data_root).resolve()
    resolved = (root / normalized).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"media path escapes the data root for {sample_id}") from error
    if not resolved.is_file():
        raise ValueError(f"media file is missing for {sample_id}")
    return normalized, resolved


def _wav_facts(path: Path, sample_id: str) -> tuple[float, int]:
    try:
        with wave.open(str(path), "rb") as handle:
            frame_count = handle.getnframes()
            sample_rate_hz = handle.getframerate()
    except (OSError, EOFError, wave.Error) as error:
        raise ValueError(f"cannot read WAV header for {sample_id}: {error}") from error
    if frame_count <= 0 or sample_rate_hz <= 0:
        raise ValueError(f"invalid WAV header for {sample_id}")
    return frame_count / sample_rate_hz, sample_rate_hz


def build_supplement(
    *, roster_path: Path, data_root: Path, parent_d1_path: Path
) -> dict[str, object]:
    """Return an exact additive media receipt for the roster.

    TWO INPUT SHAPES, one rule. The usual input is a
    ``saea-a2t-agentloop-flight-roster-receipt-v1`` view, which names its
    carrier in ``carrier`` and its size in ``count``. A ``saea-roster-receipt
    -v1`` is also accepted when its items already carry the four media facts:
    the EVO-A1 per-round proposer roster (``rails.evolution
    .proposer_roster_receipt``) is exactly that -- its items ARE the draws and
    each one records its anchor's measured ``media_relpath``/``audio_sha256``/
    ``audio_seconds`` -- and it has no flight-roster view because it is not a
    speech population. Widening the reader is what keeps ONE supplement
    builder for every roster in the study; nothing below the identity check
    differs between the shapes, and a roster whose items lack a media fact is
    still refused row by row.
    """

    roster_path = Path(roster_path)
    parent_d1_path = Path(parent_d1_path)
    roster = _load_object(roster_path, "fresh roster")
    schema = roster.get("schema")
    carrier = roster.get("carrier", roster.get("carrier_lock_key"))
    if (
        schema
        not in ("saea-a2t-agentloop-flight-roster-receipt-v1", "saea-roster-receipt-v1")
        or carrier != "audio2tool"
        or roster.get("split_role") == "test"
    ):
        raise ValueError("fresh roster identity or split role is invalid")
    items = roster.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("fresh roster count or items are invalid")
    # ``count`` is a flight-roster field; a saea-roster-receipt-v1 has none, and
    # inventing one here would let a truncated file through unnoticed.
    if "count" in roster and roster.get("count") != len(items):
        raise ValueError("fresh roster count or items are invalid")
    parent = _load_object(parent_d1_path, "parent D1")
    base_ids = _parent_ids(parent)

    manifest: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in sorted(
        items,
        key=lambda row: str(row.get("sample_id")) if isinstance(row, Mapping) else "",
    ):
        if not isinstance(item, Mapping):
            raise ValueError("fresh roster item must be an object")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in seen:
            raise ValueError("fresh roster sample IDs are malformed or duplicated")
        if sample_id in base_ids:
            raise ValueError(f"sample {sample_id} duplicates parent D1")
        seen.add(sample_id)
        media_relpath, media_path = _resolve_media(
            Path(data_root), item.get("media_relpath"), sample_id
        )
        expected_sha256 = item.get("audio_sha256")
        actual_sha256 = sha256_file(media_path)
        if not isinstance(expected_sha256, str) or expected_sha256 != actual_sha256:
            raise ValueError(f"audio hash drift for {sample_id}")
        header_seconds, sample_rate_hz = _wav_facts(media_path, sample_id)
        roster_seconds = item.get("audio_seconds")
        if (
            isinstance(roster_seconds, bool)
            or not isinstance(roster_seconds, (int, float))
            or not math.isfinite(roster_seconds)
            or abs(float(roster_seconds) - header_seconds) > 1e-6
        ):
            raise ValueError(f"audio duration drift for {sample_id}")
        manifest.append(
            {
                "id": sample_id,
                "media_relpath": media_relpath,
                "bytes": media_path.stat().st_size,
                "sha256": actual_sha256,
                "audio_seconds": round(header_seconds, 9),
                "sample_rate_hz": sample_rate_hz,
                "roles": ["query"],
            }
        )

    ordered_ids = [str(entry["id"]) for entry in manifest]
    return {
        "schema": "saea-d1-media-supplement-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": "audio2tool",
        "parent_d1_sha256": sha256_file(parent_d1_path),
        "source_binding_sha256": sha256_file(roster_path),
        "count": len(manifest),
        "ids_sha256": hashlib.sha256(
            "\n".join(ordered_ids).encode("utf-8")
        ).hexdigest(),
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
        "total_bytes": sum(int(entry["bytes"]) for entry in manifest),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--parent-d1", type=Path, default=DEFAULT_PARENT_D1)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)
    supplement = build_supplement(
        roster_path=args.roster,
        data_root=root,
        parent_d1_path=args.parent_d1,
    )
    payload = json.dumps(supplement, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        temporary.replace(output)
    print(
        json.dumps(
            {
                "count": supplement["count"],
                "ids_sha256": supplement["ids_sha256"],
                "manifest_sha256": supplement["manifest_sha256"],
                "output": str(args.output),
                "output_sha256": (
                    sha256_file(args.output)
                    if args.write
                    else hashlib.sha256(payload.encode()).hexdigest()
                ),
                "source_binding_sha256": supplement["source_binding_sha256"],
                "total_bytes": supplement["total_bytes"],
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
