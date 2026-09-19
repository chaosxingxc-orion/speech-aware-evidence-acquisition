#!/usr/bin/env python3
"""Build the DEV-2000-ADDED runtime view and the speech-packet prerequisites.

Owner decision 34 of 2026-09-19: the DEV-2000 development roster's 1,000 added
``devel`` recordings must be ready to fly, so this script produces everything the
packet pipeline needs that can be produced WITHOUT a model:

1. ``configs/dataset/slurp-speech-native-dev2000-added.json`` -- the label-free
   ``saea-speech-native-runtime-view-v1`` fragment (media identity only: relpath,
   bytes, SHA-256, header duration, sample rate, packet id), the same schema and
   the same consume-verbatim discipline as
   ``scripts/build_dev1000_runtime_view.py``. It is what
   ``scripts/slurp_evo_fold_preprocess.py``'s ENCODE phase and
   ``core.model.speech_features.materialize_legacy_cached_speech_feature_packets``'s
   PROMOTE phase both bind.
2. ``docs/checks/speech-aware-evidence-acquisition/2026-09-19-slurp-dev-2000-packets/``
   -- the media inventory (aggregate facts plus measured CPU throughput), the
   legacy feature-cache warmth measurement (how many of the 1,000 rows could be
   promoted with ZERO contacts), and the packet-preparation plan.

Why the packets themselves are NOT promoted here. In this repository a "speech
packet" is an ENCODER product: the two-phase pipeline first drives a CPU
llama-server sidecar (decoder + bf16 mmproj) with one contact per row to warm the
legacy feature cache, and only then promotes the warm entries into audited
packets. The first phase is a model contact, so a model-free mission cannot run
it. Every model-free prerequisite is produced here and the plan states exactly
what remains.

MODEL-FREE: no model, tokenizer, encoder, ASR, server, network or GPU is
reached; the offline guard is armed before the first input is opened. CPU work is
capped at 8 workers (standing rule while a GPU campaign flies). Media is decoded
through ``soundfile`` headers only -- no resampling, no ffmpeg (absent by
design), and no byte of any media file is rewritten.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_dev2000_added_runtime_view.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import read_roster  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402
from speech_aware_evidence_acquisition.e0.d1_identity import (  # noqa: E402
    _confined_media_path,
    _probe_speech_media,
)

CARRIER = "slurp"
SPLIT_NAME = "DEV-2000-ADDED"
SPLIT_ROLE = "dev"
WORKERS = 8  # standing rule: <= 8 CPU workers while a GPU campaign may fly
ROSTER_RELPATH = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
RUNTIME_VIEW_RELPATH = "configs/dataset/slurp-speech-native-dev2000-added.json"
PARENT_D1_RELPATH = "docs/receipts/artifacts/d1-identity.json"
CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-19-slurp-dev-2000-packets"
)
AUTHORITY = (
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md owner decision 34 "
    "of 2026-09-19"
)
GENERATOR = "scripts/build_dev2000_added_runtime_view.py"
LEGACY_CACHE_DIR = Path("/home/chao/feat-cache/slurp-q4km")
SERVED_PACKET_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
PROMOTION_RECEIPT_NAME = "DEV-2000-ADDED-promotion.json"


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def write_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_key_of(path_text: str) -> str:
    """FNV-1a legacy feature-cache key of one media file (process-pool entry)."""

    from speech_aware_evidence_acquisition.core.model.speech_features import (
        legacy_audio_feature_cache_key,
    )

    return legacy_audio_feature_cache_key(Path(path_text).read_bytes())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the artifacts")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    roster = read_roster(REPO_ROOT / ROSTER_RELPATH)
    if roster["carrier_lock_key"] != CARRIER or roster["split_role"] != SPLIT_ROLE:
        raise SystemExit("the added roster is not the dev-role SLURP roster")
    sample_ids = sorted(str(item["sample_id"]) for item in roster["items"])
    if len(sample_ids) != 1000:
        raise SystemExit("the added roster must carry exactly 1,000 recordings")

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    relpath_by_id = {
        record.sample_id: record.media_relpath
        for record in load_slurp_split(lock, root, "devel")
    }
    missing = [sid for sid in sample_ids if sid not in relpath_by_id]
    if missing:
        raise SystemExit(f"{len(missing)} added id(s) absent from the devel loader")

    confined = [
        (
            sample_id,
            *_confined_media_path(
                root,
                relpath_by_id[sample_id],
                context=f"DEV-2000-ADDED sample {sample_id!r}",
            ),
        )
        for sample_id in sample_ids
    ]

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=min(WORKERS, len(confined))) as pool:
        measured = tuple(pool.map(_probe_speech_media, (entry[2] for entry in confined)))
    inventory_seconds = time.monotonic() - started

    items: list[dict[str, object]] = []
    total_bytes = 0
    for (sample_id, media_relpath, _path), facts in zip(confined, measured, strict=True):
        media_bytes, media_sha256, audio_seconds, sample_rate_hz = facts
        total_bytes += int(media_bytes)
        items.append(
            {
                "sample_id": sample_id,
                "media_relpath": media_relpath,
                "audio_sha256": media_sha256,
                "audio_seconds": round(float(audio_seconds), 9),
                "sample_rate_hz": int(sample_rate_hz),
                "packet_id": sample_id.replace(":", "/"),
                "bytes": int(media_bytes),
            }
        )

    # D1 closure proof: base D1's slurp media layer records all 8,690 devel
    # recordings, so every added row must already be there with identical bytes.
    d1 = json.loads((REPO_ROOT / PARENT_D1_RELPATH).read_text(encoding="utf-8"))
    d1_media = {
        entry["id"]: entry
        for entry in d1["carriers"][CARRIER]["layers"]["media"]["manifest"]
    }
    for item in items:
        base = d1_media.get(str(item["sample_id"]))
        if base is None:
            raise SystemExit(
                f"added sample {item['sample_id']!r} is OUTSIDE the D1 closure"
            )
        if base["sha256"] != item["audio_sha256"] or base["bytes"] != item["bytes"]:
            raise SystemExit(
                f"added sample {item['sample_id']!r} media bytes drifted from D1's record"
            )

    view_items = [
        {key: value for key, value in item.items() if key != "bytes"} for item in items
    ]
    unsigned: dict[str, object] = {
        "schema": "saea-speech-native-runtime-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "seed": roster["seed"],
        "split_identity_hash": roster["split_identity_hash"],
        "source_binding_sha256": canonical_sha256(roster),
        "d1_media_supplement": None,
        "d1_media_supplement_sha256": None,
        "d1_manifest_sha256": None,
        "count": len(view_items),
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in view_items), 9
        ),
        "items": view_items,
    }
    runtime_view = {**unsigned, "runtime_view_sha256": canonical_sha256(unsigned)}

    # ---- legacy feature-cache warmth (zero contacts) ----------------------
    started = time.monotonic()
    paths = [str(entry[2]) for entry in confined]
    with ProcessPoolExecutor(max_workers=WORKERS) as pool:
        keys = list(pool.map(cache_key_of, paths, chunksize=16))
    cache_seconds = time.monotonic() - started
    warm = 0
    cold_ids: list[str] = []
    cache_available = LEGACY_CACHE_DIR.is_dir()
    if cache_available:
        entries = {path.name for path in LEGACY_CACHE_DIR.glob("*_o*.feat")}
        for sample_id, key in zip(sample_ids, keys, strict=True):
            if any(name.startswith(f"{key}_o") for name in entries):
                warm += 1
            else:
                cold_ids.append(sample_id)
    else:
        cold_ids = list(sample_ids)

    audio_seconds_total = float(runtime_view["audio_seconds_total"])
    inventory = {
        "schema": "saea-dev2000-added-media-inventory-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "roster": {
            "relpath": ROSTER_RELPATH,
            "roster_id": roster["roster_id"],
            "split_identity_hash": roster["split_identity_hash"],
        },
        "runtime_view": {
            "relpath": RUNTIME_VIEW_RELPATH,
            "runtime_view_sha256": runtime_view["runtime_view_sha256"],
            "per_file_sha256": (
                "one audio_sha256 per row inside the runtime view; the inventory does not "
                "duplicate 1,000 digests"
            ),
        },
        "counts": {
            "recordings": len(items),
            "distinct_utterances": len({str(i["sample_id"]).rsplit(":", 1)[0] for i in items}),
            "total_bytes": total_bytes,
            "audio_seconds_total": audio_seconds_total,
            "sample_rates_hz": sorted({int(item["sample_rate_hz"]) for item in items}),
        },
        "d1_closure": {
            "relpath": PARENT_D1_RELPATH,
            "covered_items": len(items),
            "supplement_required": False,
        },
        "cpu_pipeline": {
            "workers": WORKERS,
            "decoder": (
                "soundfile header probe for duration and rate; bytes hashed with SHA-256. "
                "ffmpeg is absent by design and no media byte is rewritten -- the librosa "
                "fallback stays the pinned decode path for every later consumer."
            ),
            "media_inventory_wall_seconds": round(inventory_seconds, 3),
            "media_inventory_files_per_second": round(len(items) / inventory_seconds, 3),
            "media_inventory_audio_seconds_per_wall_second": round(
                audio_seconds_total / inventory_seconds, 3
            ),
            "media_inventory_mib_per_second": round(
                total_bytes / (1024 * 1024) / inventory_seconds, 3
            ),
            "cache_key_wall_seconds": round(cache_seconds, 3),
            "cache_key_files_per_second": round(len(items) / cache_seconds, 3),
        },
        "legacy_feature_cache": {
            "dir": str(LEGACY_CACHE_DIR),
            "available": cache_available,
            "warm_rows": warm,
            "cold_rows": len(cold_ids),
            "key_convention": (
                "core.model.speech_features.legacy_audio_feature_cache_key -- FNV-1a over "
                "the encoded media bytes, so warmth is a property of the file, not of a "
                "prompt"
            ),
        },
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    inventory["inventory_sha256"] = canonical_sha256(inventory)

    plan = {
        "schema": "saea-dev2000-added-packet-plan-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "state": "PREREQUISITES COMPLETE; ENCODE AND PROMOTE NOT RUN",
        "why_not_run": (
            "A speech packet in this repository is an ENCODER product. The pipeline "
            "(scripts/slurp_evo_fold_preprocess.py, precedent SAEA-SN-DEV1000-PREPROCESS) "
            "first drives a CPU llama-server sidecar carrying the decoder and the bf16 "
            "mmproj with one contact per row at max_tokens 1 to warm the legacy feature "
            "cache, and only then promotes the warm entries. That first phase is a model "
            "contact under a structured ExecutionPlan, which a model-free mission may not "
            "make. Everything that does not need the encoder is done and committed."
        ),
        "rows_needing_encode": len(cold_ids),
        "rows_promotable_with_zero_contacts": warm,
        "target_packet_root": {
            "path": str(SERVED_PACKET_ROOT),
            "promotion_receipt": f"{SERVED_PACKET_ROOT}/{PROMOTION_RECEIPT_NAME}",
            "write_mode": (
                "ADDITIVE ONLY: new per-row packet directories under slurp/devel/<id>/ and "
                "one new promotion receipt. No file the resident session already serves is "
                "read-modified-written, and no existing promotion receipt is touched. If "
                "the coordinator prefers full isolation from the live session, the same "
                "promotion writes to a NEW root (for example "
                "/home/chao/feat-cache/slurp-dev2000-added-packets-04ccc72a) and the model "
                "fragment's LLAMA_SPEECH_FEATURE_ROOT changes with the next session, which "
                "costs a service restart."
            ),
        },
        "what_remains": [
            {
                "step": 1,
                "name": "ENCODE",
                "detail": (
                    "CPU llama-server sidecar on port 8081 (-ngl 0 --no-mmproj-offload, "
                    "receipts/runtime-q4km-preprocess.json), one contact per cold row at "
                    "max_tokens 1, under its own session and stop receipts. GPU stays free."
                ),
                "contacts": len(cold_ids),
                "speech_seconds": round(audio_seconds_total, 3),
            },
            {
                "step": 2,
                "name": "PROMOTE",
                "detail": (
                    "core.model.speech_features."
                    "materialize_legacy_cached_speech_feature_packets over the runtime "
                    "view's packet ids, workers <= 8, writing "
                    f"{PROMOTION_RECEIPT_NAME} beside the existing per-set receipts."
                ),
                "contacts": 0,
            },
        ],
        "binding": {
            "runtime_view": RUNTIME_VIEW_RELPATH,
            "runtime_view_sha256": runtime_view["runtime_view_sha256"],
            "roster": ROSTER_RELPATH,
            "split_identity_hash": roster["split_identity_hash"],
            "model_fragment": (
                "configs/model/q4km-mmproj-free-slurp-native-bounded-perception-proof-"
                "np4-ctx24k-max512-v1.json"
            ),
        },
    }
    plan["plan_sha256"] = canonical_sha256(plan)

    summary = {
        "count": runtime_view["count"],
        "audio_seconds_total": runtime_view["audio_seconds_total"],
        "total_bytes": total_bytes,
        "runtime_view_sha256": runtime_view["runtime_view_sha256"],
        "split_identity_hash": runtime_view["split_identity_hash"],
        "cpu_pipeline": inventory["cpu_pipeline"],
        "legacy_feature_cache": inventory["legacy_feature_cache"],
        "offline_guard": inventory["offline_guard"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.write:
        view_file_sha256 = write_json(REPO_ROOT / RUNTIME_VIEW_RELPATH, runtime_view)
        check_dir = REPO_ROOT / CHECK_DIR
        write_json(check_dir / "media-inventory.json", inventory)
        write_json(check_dir / "packet-preparation-plan.json", plan)
        print(f"wrote {RUNTIME_VIEW_RELPATH} (file sha256 {view_file_sha256})")
        print(f"wrote {CHECK_DIR}/media-inventory.json")
        print(f"wrote {CHECK_DIR}/packet-preparation-plan.json")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
