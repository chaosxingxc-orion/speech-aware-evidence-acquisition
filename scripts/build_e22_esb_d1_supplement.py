#!/usr/bin/env python3
"""Build the additive D1 media receipt for the ESB Earnings-22 utterances.

Sibling of ``scripts/build_a2t_tier1_official_population_d1_supplement.py``,
for the other carrier. Same schema (``saea-d1-media-supplement-v1``, the shape
``contracts.gate_media_identity`` reads), same discipline: each derived WAV is
re-hashed here and only its container header is read for duration and sample
rate. No reference sentence, transcript, annotation, model output, score or
future turn is opened. No model, network, tokenizer or scorer contact.

One behavioural difference from the Audio2Tool sibling, forced by this
population: every id here is NEW to the immutable D1 identity artifact by
construction. The 2,735 ids are ``<call>-<segment>`` derived media cut from
six parent calls; D1 records the six PARENTS (bare numeric ids) and nothing
else for this carrier, so an overlap would be a defect rather than an expected
case. Any id that already appears in the parent manifest is therefore a hard
refusal here, not a skip.

The parent linkage is checked rather than assumed: every roster item's
``parent_sample_id`` must be one of the six ESB test calls AND must appear in
the parent D1 media manifest with the byte identity the roster measured, so a
derived utterance can only ever chain to media D1 itself closed over.

``--profile dev10`` builds the same supplement for the ESB train-split
utterances of this study's own Earnings-22 ``dev`` subset10 (2026-09-05 prompt
A/B experiment); ``--profile test`` (the default) is the sealed 2026-09-04
six-call population and is unchanged.

Usage::

    python scripts/build_e22_esb_d1_supplement.py --write
    python scripts/build_e22_esb_d1_supplement.py --profile dev10 --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import wave
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]
CARRIER = "earnings22-original"
ESB_TEST_CALLS = ("4432298", "4450488", "4470290", "4479741", "4483338", "4485244")
ROSTER_SCHEMA = "saea-e22-esb-utterance-roster-receipt-v1"

DEFAULT_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-e22-esb-shortform-alignment-400-v1"
    / "roster"
    / "flight-roster-receipt.json"
)
DEFAULT_PARENT_D1 = REPO / "docs/receipts/artifacts/d1-identity.json"
DEFAULT_OUTPUT = REPO / "docs/receipts/artifacts/d1-e22-esb-utterances-2735.json"

# The ten calls docs/receipts/splits.json assigns this study's own ``dev`` role.
DEV10_CALLS = (
    "4453225",
    "4469088",
    "4470684",
    "4474506",
    "4479944",
    "4481952",
    "4482383",
    "4482613",
    "4483937",
    "4485192",
)
DEV10_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-e22-dev-esb-prompt-ab-v1"
    / "roster"
    / "flight-roster-receipt.json"
)
DEV10_OUTPUT = REPO / "docs/receipts/artifacts/d1-e22-esb-dev10-utterances.json"

PROFILES: dict[str, dict[str, object]] = {
    "test": {"calls": ESB_TEST_CALLS, "roster": DEFAULT_ROSTER, "output": DEFAULT_OUTPUT},
    "dev10": {"calls": DEV10_CALLS, "roster": DEV10_ROSTER, "output": DEV10_OUTPUT},
}


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


def _parent_entries(parent: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    carriers = parent.get("carriers")
    carrier = carriers.get(CARRIER) if isinstance(carriers, Mapping) else None
    layers = carrier.get("layers") if isinstance(carrier, Mapping) else None
    media = layers.get("media") if isinstance(layers, Mapping) else None
    manifest = media.get("manifest") if isinstance(media, Mapping) else None
    if not isinstance(manifest, list):
        raise ValueError(f"parent D1 lacks the {CARRIER} media manifest")
    entries = {
        str(entry["id"]): entry
        for entry in manifest
        if isinstance(entry, Mapping) and isinstance(entry.get("id"), str)
    }
    if len(entries) != len(manifest):
        raise ValueError(f"parent D1 {CARRIER} media IDs are malformed or duplicated")
    return entries


def _resolve_media(data_root: Path, relpath: object, sample_id: str) -> tuple[str, Path]:
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
    *,
    roster_path: Path,
    data_root: Path,
    parent_d1_path: Path,
    calls: tuple[str, ...] = ESB_TEST_CALLS,
) -> dict[str, object]:
    roster_path = Path(roster_path)
    parent_d1_path = Path(parent_d1_path)
    roster = _load_object(roster_path, "ESB utterance roster")
    if (
        roster.get("schema") != ROSTER_SCHEMA
        or roster.get("carrier") != CARRIER
        or roster.get("split_role") == "test"
    ):
        raise ValueError("roster identity or split role is invalid")
    items = roster.get("items")
    if not isinstance(items, list) or not items or roster.get("count") != len(items):
        raise ValueError("roster count or items are invalid")
    parent = _load_object(parent_d1_path, "parent D1")
    base_entries = _parent_entries(parent)

    manifest: list[dict[str, object]] = []
    seen: set[str] = set()
    parents_seen: set[str] = set()
    for item in sorted(
        items, key=lambda row: str(row.get("sample_id")) if isinstance(row, Mapping) else ""
    ):
        if not isinstance(item, Mapping):
            raise ValueError("roster item must be an object")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in seen:
            raise ValueError("roster sample IDs are malformed or duplicated")
        seen.add(sample_id)
        if sample_id in base_entries:
            raise ValueError(
                f"{sample_id} already exists in the immutable D1 identity artifact; a "
                "derived utterance id can never collide with a parent call id"
            )
        parent_id = item.get("parent_sample_id")
        if parent_id not in calls:
            raise ValueError(
                f"{sample_id} names a parent {parent_id!r} this profile does not pin"
            )
        parents_seen.add(str(parent_id))
        base = base_entries.get(str(parent_id))
        if base is None:
            raise ValueError(
                f"parent call {parent_id!r} has no D1-recorded media identity; a derived "
                "utterance can only chain to media D1 already closed over"
            )
        if base.get("sha256") != item.get("parent_sha256"):
            raise ValueError(
                f"parent call {parent_id!r} media identity disagrees with D1: the roster "
                f"measured {str(item.get('parent_sha256'))[:12]}..., D1 records "
                f"{str(base.get('sha256'))[:12]}..."
            )
        media_relpath, media_path = _resolve_media(
            Path(data_root), item.get("media_relpath"), sample_id
        )
        actual_sha256 = sha256_file(media_path)
        if item.get("audio_sha256") != actual_sha256:
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

    if sorted(parents_seen) != sorted(calls):
        raise ValueError(
            f"roster covers parents {sorted(parents_seen)}, not this profile's "
            f"{len(calls)} calls {sorted(calls)}"
        )
    ordered_ids = [str(entry["id"]) for entry in manifest]
    return {
        "schema": "saea-d1-media-supplement-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier_lock_key": CARRIER,
        "parent_d1_sha256": sha256_file(parent_d1_path),
        "source_binding_sha256": sha256_file(roster_path),
        "count": len(manifest),
        "ids_sha256": hashlib.sha256("\n".join(ordered_ids).encode("utf-8")).hexdigest(),
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
        "total_bytes": sum(int(entry["bytes"]) for entry in manifest),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=sorted(PROFILES), default="test")
    parser.add_argument("--roster", type=Path, default=None)
    parser.add_argument("--parent-d1", type=Path, default=DEFAULT_PARENT_D1)
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    profile = PROFILES[args.profile]
    roster_path = Path(args.roster or profile["roster"])
    output_path = Path(args.output or profile["output"])
    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)
    supplement = build_supplement(
        roster_path=roster_path,
        data_root=root,
        parent_d1_path=args.parent_d1,
        calls=tuple(profile["calls"]),
    )
    payload = json.dumps(supplement, ensure_ascii=False, indent=2) + "\n"
    if args.write:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        temporary.replace(output)
    print(
        json.dumps(
            {
                "count": supplement["count"],
                "profile": args.profile,
                "ids_sha256": supplement["ids_sha256"],
                "manifest_sha256": supplement["manifest_sha256"],
                "output": str(output_path),
                "output_sha256": (
                    sha256_file(output_path)
                    if args.write
                    else hashlib.sha256(payload.encode()).hexdigest()
                ),
                "parent_d1_sha256": supplement["parent_d1_sha256"],
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
