#!/usr/bin/env python3
"""Build the Audio2Tool direct-baseline calibration flight roster (400 rows).

The population is NOT drawn: it is the already-frozen 400-item Audio2Tool
discovery split (``docs/receipts/probe-samples/r1-audio2tool-sample.json``,
seed 20260807, 8 tiers x 50), already exposed by A0 under the ledger row
``SAEA-BASE-a2t-a0-400``. This builder re-expresses that parent receipt in
the flight-roster schema every September Audio2Tool preprocessing pass
already consumes (``saea-a2t-agentloop-flight-roster-receipt-v1``), adding
only the media facts a receipt-bound preprocessing launcher needs and the
parent receipt itself does not carry: ``media_relpath``, ``audio_seconds``
and ``audio_sha256``.

Label-free and contact-free: it reads the parent receipt's identifiers, the
carrier's own media manifests through ``data.audio2tool.load_audio2tool``
(runtime surface only -- no gold, no expected calls, no task text), and the
WAV bytes themselves for their SHA-256. No model, network, tokenizer,
scorer or audio-decoding contact.

Two identity hashes are recorded, because two conventions are in play and
conflating them would be a silent identity swap:

* ``split_identity_hash`` -- SHA-256 over the LF-joined sorted parent
  ``key`` values (``audio2tool:<tier>:<id6>``). This is the convention the
  parent receipt itself used, so this value MUST reproduce the parent's
  ``e1d751e6...`` exactly; the builder asserts it.
* ``flight_split_identity_hash`` -- ``data.splits.split_identity_hash(
  prefixed("audio2tool", sample_ids))`` over ``audio2tool/<tier>:<id6>``.
  This is the convention ``core.flight.FlightRuntime.preflight`` computes
  at flight time and therefore the value an exposure-ledger row for a
  ``FlightRuntime`` flight of this roster must carry.

Usage::

    python scripts/build_a2t_calibration_400_roster.py            # print only
    python scripts/build_a2t_calibration_400_roster.py --write    # write it
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

REPO = Path(__file__).resolve().parents[1]

PARENT_RECEIPT_RELPATH = "docs/receipts/probe-samples/r1-audio2tool-sample.json"
PARENT_SPLIT_IDENTITY_HASH = (
    "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
)
DEFAULT_OUTPUT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-04-a2t-calibration-400-roster"
    / "flight-roster-receipt.json"
)
SPLIT_NAME = "A2T-CALIBRATION-400"
SPLIT_ROLE = "discovery"
CARRIER = "audio2tool"
EXPECTED_COUNT = 400
EXPECTED_PER_TIER = 50


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_lines(values) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


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


def build_roster(
    *, parent_receipt_path: Path, data_root: Path, repo_root: Path
) -> dict[str, object]:
    """Return the calibration flight roster receipt for the frozen 400."""

    from speech_aware_evidence_acquisition.data.audio2tool import load_audio2tool
    from speech_aware_evidence_acquisition.data.lock import (
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.data.splits import (
        prefixed,
        split_identity_hash,
    )

    parent = _load_object(parent_receipt_path, "parent frozen-400 receipt")
    if parent.get("carrier") != CARRIER or parent.get("split_role") != SPLIT_ROLE:
        raise ValueError("parent receipt carrier or split role is not the frozen 400's")
    items = parent.get("items")
    if not isinstance(items, list) or len(items) != EXPECTED_COUNT:
        raise ValueError(f"parent receipt must carry exactly {EXPECTED_COUNT} items")
    if parent.get("split_identity_hash") != PARENT_SPLIT_IDENTITY_HASH:
        raise ValueError("parent receipt split identity hash drifted")

    lock = load_lock(umbrella_lock_path())
    refs = {ref.sample_id: ref for ref in load_audio2tool(lock, data_root, repo_root=repo_root)}

    root = Path(data_root).resolve()
    rows: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("parent receipt item must be an object")
        tier = item.get("tier")
        raw_id = item.get("id")
        key = item.get("key")
        query_idx = item.get("query_idx")
        if (
            not isinstance(tier, str)
            or not tier
            or isinstance(raw_id, bool)
            or not isinstance(raw_id, int)
            or isinstance(query_idx, bool)
            or not isinstance(query_idx, int)
        ):
            raise ValueError(f"parent receipt item is malformed: {item!r}")
        sample_id = f"{tier}:{int(raw_id):06d}"
        if key != f"{CARRIER}:{sample_id}":
            raise ValueError(f"parent receipt key convention drift for {sample_id}")
        if sample_id in seen:
            raise ValueError(f"duplicate parent receipt sample id: {sample_id}")
        seen.add(sample_id)
        ref = refs.get(sample_id)
        if ref is None:
            raise ValueError(f"sample {sample_id} is absent from the carrier loader")
        media_relpath = ref.media_relpath
        if (
            not isinstance(media_relpath, str)
            or not media_relpath
            or media_relpath.startswith("/")
            or "\\" in media_relpath
            or any(part in ("", ".", "..") for part in media_relpath.split("/"))
        ):
            raise ValueError(f"media_relpath is malformed for {sample_id}")
        media_path = (root / media_relpath).resolve()
        try:
            media_path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"media path escapes the data root for {sample_id}") from error
        if not media_path.is_file():
            raise ValueError(f"media file is missing for {sample_id}")
        audio_seconds = float(ref.audio_seconds)
        if not audio_seconds > 0:
            raise ValueError(f"audio_seconds must be positive for {sample_id}")
        rows.append(
            {
                "audio_seconds": audio_seconds,
                "audio_sha256": sha256_file(media_path),
                "id": int(raw_id),
                "key": key,
                "media_relpath": media_relpath,
                "query_idx": int(query_idx),
                "sample_id": sample_id,
                "tier": tier,
            }
        )

    rows.sort(key=lambda row: str(row["sample_id"]))
    tier_counts = dict(sorted(Counter(str(row["tier"]) for row in rows).items()))
    if sorted(tier_counts.values()) != [EXPECTED_PER_TIER] * len(tier_counts):
        raise ValueError(f"tier counts are not {EXPECTED_PER_TIER} per tier: {tier_counts}")

    identity = sha256_lines(str(row["key"]) for row in rows)
    if identity != PARENT_SPLIT_IDENTITY_HASH:
        raise ValueError(
            "recomputed split identity hash "
            f"{identity} does not reproduce the parent's {PARENT_SPLIT_IDENTITY_HASH}"
        )
    flight_identity = split_identity_hash(
        prefixed(CARRIER, [str(row["sample_id"]) for row in rows])
    )

    return {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "split_identity_hash": identity,
        "split_identity_hash_convention": (
            "sha256 over the LF-joined sorted parent 'key' values "
            "(audio2tool:<tier>:<id6>, UTF-8, no trailing newline)"
        ),
        "flight_split_identity_hash": flight_identity,
        "flight_split_identity_hash_convention": (
            "data.splits.split_identity_hash(prefixed('audio2tool', sample_ids)) over "
            "audio2tool/<tier>:<id6> -- the value core.flight.FlightRuntime.preflight "
            "computes at flight time and an exposure row for a FlightRuntime flight "
            "of this roster must carry"
        ),
        "count": len(rows),
        "tier_counts": tier_counts,
        "audio_seconds_total": round(sum(float(row["audio_seconds"]) for row in rows), 6),
        "media_roster_sha256": canonical_sha256(
            [
                {
                    "sample_id": row["sample_id"],
                    "media_relpath": row["media_relpath"],
                    "audio_sha256": row["audio_sha256"],
                    "audio_seconds": row["audio_seconds"],
                }
                for row in rows
            ]
        ),
        "parent": {
            "receipt": PARENT_RECEIPT_RELPATH,
            "receipt_sha256": sha256_file(parent_receipt_path),
            "split_identity_hash": PARENT_SPLIT_IDENTITY_HASH,
            "probe": parent.get("probe"),
            "seed": parent.get("seed"),
            "pool_size": parent.get("pool_size"),
        },
        "selection": {
            "rule": "the frozen 400 split, no draw",
            "per_tier": EXPECTED_PER_TIER,
            "seed": parent.get("seed"),
            "uses_gold_at_runtime": False,
            "uses_test": False,
        },
        "contacts": {"audio": 0, "model": 0, "network": 0, "scorer": 0},
        "status": "PREPARED_NOT_CONTACT_AUTHORITY",
        "items": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--parent-receipt", type=Path, default=REPO / PARENT_RECEIPT_RELPATH
    )
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
    roster = build_roster(
        parent_receipt_path=args.parent_receipt, data_root=root, repo_root=REPO
    )
    payload = json.dumps(roster, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.write:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix + ".tmp")
        temporary.write_text(payload, encoding="utf-8", newline="\n")
        temporary.replace(output)
    print(
        json.dumps(
            {
                "audio_seconds_total": roster["audio_seconds_total"],
                "count": roster["count"],
                "flight_split_identity_hash": roster["flight_split_identity_hash"],
                "output": str(args.output),
                "output_sha256": (
                    sha256_file(args.output)
                    if args.write
                    else hashlib.sha256(payload.encode("utf-8")).hexdigest()
                ),
                "parent_split_identity_hash_reproduced": True,
                "split_identity_hash": roster["split_identity_hash"],
                "tier_counts": roster["tier_counts"],
                "written": bool(args.write),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
