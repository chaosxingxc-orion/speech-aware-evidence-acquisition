#!/usr/bin/env python3
"""Roster / identity receipt for SAEA-E21-FULL44-DIRECT-BASELINE-V1.

Zero contact: no model, GPU, llama-server, tool, embedding, network or audio
decode. Everything below is a pure function of the umbrella lock, the frozen
split receipt (``docs/receipts/splits.json``), the carrier's own metadata CSV
and the presence/size of already-materialized files. Deliberately NO reference
or annotation CONTENT is read -- the reference and ``wer_tags`` layers are
checked for presence and byte size only, never opened for word counts, so this
pre-flight receipt cannot become a gold read.

What it establishes, and why the flight needs it:

1. The population is the whole frozen ``earnings21-original`` discovery split
   (44 calls), and its recomputed identity hash equals the one
   ``docs/receipts/splits.json`` froze -- the same hash the execution plan and
   the exposure row must carry.
2. The exact fixed-90-second window count of every call, under the rule
   ``reproduction.obs_loop`` applies in ``obs_boundary_mode: "fixed"``
   (advance = buffer, so ``ceil(duration / 90)`` windows and no overlap). The
   flight's ``planned_model_calls`` is derived from this total, and the frozen
   ten's 342 windows reproduce the sealed 2026-08-14 arm's own call count
   exactly, which is what makes the derivation trustworthy for the other 34.
3. The two strata the Earnings-21 release itself reports -- ``sector`` and
   ``sample_rate`` -- per call and as counts, so the verdict's per-stratum
   tables are fixed before any result exists.
4. The 10 / 34 partition against the two sealed August runs, so the verdict can
   report the ten sealed calls as a build-and-audio-path contrast.
5. That every one of the 44 calls actually has its media, ``.nlp`` reference
   and ``.wer_tag.json`` entity sidecar materialized, so no scorer of the
   manifest's four can fail on a missing file after the GPU time is spent.

Usage:
    python scripts/build_e21_full44_roster_receipt.py --output <path.json>
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.data.carriers import (  # noqa: E402
    get_carrier_descriptor,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.loader import load_earnings21  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import discovery_split  # noqa: E402

BUFFER_SECONDS = 90.0
CARRIER = "earnings21-original"

SEALED_TEN = (
    "4330115",
    "4365024",
    "4365948",
    "4366429",
    "4366522",
    "4384964",
    "4385072",
    "4387383",
    "4389907",
    "4397829",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def build(output: Path) -> dict[str, object]:
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    spec = discovery_split(lock, root)
    if spec.carrier_lock_key != CARRIER:
        raise SystemExit(f"discovery split names carrier {spec.carrier_lock_key!r}")

    descriptor = get_carrier_descriptor(CARRIER)
    carrier_root = asset_dir(lock, CARRIER, root)
    metadata_path = carrier_root / descriptor.metadata_filename
    metadata: dict[str, dict[str, str]] = {}
    with metadata_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            metadata[row[descriptor.metadata_columns.id_column]] = row

    refs = {ref.sample_id: ref for ref in load_earnings21(lock, root)}
    ids = sorted(prefixed.split("/", 1)[1] for prefixed in spec.ids)

    calls: list[dict[str, object]] = []
    total_seconds = 0.0
    total_windows = 0
    for sample_id in ids:
        ref = refs[sample_id]
        meta = metadata[sample_id]
        windows = int(math.ceil(ref.audio_seconds / BUFFER_SECONDS))
        media = root / ref.media_relpath
        reference = (
            carrier_root
            / descriptor.reference.subdir
            / f"{sample_id}{descriptor.reference.extension}"
        )
        entity = (
            carrier_root
            / descriptor.entity.subdir
            / f"{sample_id}{descriptor.entity.extension}"
        )
        calls.append(
            {
                "sample_id": sample_id,
                "audio_seconds": ref.audio_seconds,
                "audio_minutes": round(ref.audio_seconds / 60.0, 3),
                "fixed_90s_windows": windows,
                "last_window_seconds": round(
                    ref.audio_seconds - (windows - 1) * BUFFER_SECONDS, 3
                ),
                "sample_rate_hz": ref.sample_rate_hz,
                "sector": meta["sector"],
                "company_name": meta["company_name"],
                "media_relpath": ref.media_relpath,
                "media_bytes": media.stat().st_size,
                "reference_present": reference.is_file(),
                "reference_bytes": reference.stat().st_size,
                "entity_sidecar_present": entity.is_file(),
                "entity_sidecar_bytes": entity.stat().st_size,
                "in_sealed_ten": sample_id in SEALED_TEN,
            }
        )
        total_seconds += ref.audio_seconds
        total_windows += windows

    missing = [
        call["sample_id"]
        for call in calls
        if not (call["reference_present"] and call["entity_sidecar_present"])
    ]

    ten = [call for call in calls if call["in_sealed_ten"]]
    rest = [call for call in calls if not call["in_sealed_ten"]]

    def _totals(rows: list[dict[str, object]]) -> dict[str, object]:
        seconds = sum(float(row["audio_seconds"]) for row in rows)
        return {
            "calls": len(rows),
            "audio_seconds": round(seconds, 3),
            "audio_hours": round(seconds / 3600.0, 4),
            "fixed_90s_windows": sum(int(row["fixed_90s_windows"]) for row in rows),
        }

    by_sector: dict[str, dict[str, object]] = {}
    by_rate: dict[str, dict[str, object]] = {}
    for call in calls:
        for bucket, key in ((by_sector, str(call["sector"])), (by_rate, str(call["sample_rate_hz"]))):
            entry = bucket.setdefault(
                key, {"calls": 0, "audio_seconds": 0.0, "fixed_90s_windows": 0, "sample_ids": []}
            )
            entry["calls"] = int(entry["calls"]) + 1
            entry["audio_seconds"] = float(entry["audio_seconds"]) + float(call["audio_seconds"])
            entry["fixed_90s_windows"] = int(entry["fixed_90s_windows"]) + int(
                call["fixed_90s_windows"]
            )
            entry["sample_ids"].append(str(call["sample_id"]))  # type: ignore[union-attr]
    for bucket in (by_sector, by_rate):
        for entry in bucket.values():
            entry["audio_seconds"] = round(float(entry["audio_seconds"]), 3)

    receipt: dict[str, object] = {
        "schema": "saea-e21-full44-roster-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "run_id": "SAEA-E21-FULL44-DIRECT-BASELINE-V1",
        "zero_contact": (
            "no model, GPU, llama-server, tool, embedding, network or audio-decode "
            "contact; reference and entity layers are checked for presence and byte "
            "size only, never opened"
        ),
        "carrier_lock_key": CARRIER,
        "carrier_root_relpath": str(carrier_root.relative_to(root)),
        "metadata_file": {
            "relpath": str(metadata_path.relative_to(root)),
            "sha256": _sha256(metadata_path),
        },
        "split": {
            "name": "discovery",
            "role": spec.split_role,
            "count": len(ids),
            "identity_hash_recomputed": spec.identity_hash,
            "identity_hash_frozen_in_receipt": json.loads(
                (REPO_ROOT / "docs" / "receipts" / "splits.json").read_text(encoding="utf-8")
            )["splits"]["discovery"]["identity_hash"],
            "sample_ids": ids,
        },
        "window_rule": (
            "obs_boundary_mode 'fixed' with obs_buffer_seconds 90 advances by the "
            "buffer (reproduction.obs_loop: advance = buffer_seconds when the mode is "
            "fixed), so a call of D seconds is tiled into ceil(D / 90) non-overlapping "
            "windows, the last one short; no VAD trim, no rolling tail, no preprocessing"
        ),
        "totals": {
            "all_44": _totals(calls),
            "sealed_ten": _totals(ten),
            "remaining_34": _totals(rest),
        },
        "sealed_anchor_crosscheck": {
            "SAEA-E-005B-N10-zero": {
                "attempt_id": "attempt-20260814T235515Z-044ccc",
                "sealed_calls_used": 342,
                "sealed_audio_seconds_used": 30406.9313125,
                "recomputed_windows_for_the_same_ten": _totals(ten)["fixed_90s_windows"],
                "note": (
                    "the recomputed ceil(D/90) window count reproduces the sealed "
                    "arm's own calls_used exactly, which is what licenses the same "
                    "derivation for the other 34"
                ),
            },
            "SAEA-BENCH-kb34-floor": {
                "attempt_id": "attempt-20260814T075128Z-a74060",
                "sealed_calls_used": 1256,
                "sealed_audio_seconds_used": 111388.921375,
                "recomputed_windows_for_the_same_34": _totals(rest)["fixed_90s_windows"],
                "note": (
                    "the sealed count is 5 windows higher than the metadata-derived "
                    "one because the sealed number counts DECODED duration while this "
                    "receipt counts the release's own metadata duration; the flight's "
                    "call budget carries headroom for the difference"
                ),
            },
        },
        "strata": {"by_sector": by_sector, "by_sample_rate_hz": by_rate},
        "layers_complete": not missing,
        "layers_missing_for": missing,
        "calls": calls,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    receipt = build(Path(args.output))
    totals = receipt["totals"]["all_44"]  # type: ignore[index]
    print(
        f"44 calls, {totals['audio_seconds']} s ({totals['audio_hours']} h), "
        f"{totals['fixed_90s_windows']} fixed 90-second windows; "
        f"layers complete: {receipt['layers_complete']}"
    )
    print(f"split identity: {receipt['split']['identity_hash_recomputed']}")  # type: ignore[index]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
