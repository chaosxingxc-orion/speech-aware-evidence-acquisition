#!/usr/bin/env python3
"""Build a SLURP speech-native runtime view and its packet prerequisites, for ANY roster.

The roster-parameterised generalisation of
``scripts/build_dev2000_added_runtime_view.py`` (owner decision 34 of
2026-09-19), written for owner decision 107 of 2026-09-23 -- the expansion of
the development side up to the full SLURP ``devel`` split -- so that a second
roster does not need a second copy of the same 400 lines. The DEV-2000-ADDED
builder is left exactly as it is: its artifacts are sealed and its byte-for-byte
reproducibility is part of the record.

Given a committed ``saea-roster-receipt-v1`` it produces everything the packet
pipeline needs that can be produced WITHOUT a model:

1. ``--output`` -- the label-free ``saea-speech-native-runtime-view-v1``
   fragment (media identity only: relpath, bytes, SHA-256, header duration,
   sample rate, packet id), the same schema and the same consume-verbatim
   discipline as ``scripts/build_dev1000_runtime_view.py`` and its
   DEV-2000-ADDED sibling. It is what ``scripts/slurp_evo_fold_preprocess.py``'s
   ENCODE phase and ``core.model.speech_features.
   materialize_legacy_cached_speech_feature_packets``'s PROMOTE phase bind.
2. ``--checks-dir`` -- ``media-inventory.json`` (aggregate facts plus measured
   CPU throughput and the legacy feature-cache warmth: how many rows could be
   promoted with ZERO contacts) and ``packet-preparation-plan.json`` (what
   remains, and the id-level audit of which rows the resident packet root
   already serves).

Why the packets themselves are NOT promoted here. In this repository a "speech
packet" is an ENCODER product: the two-phase pipeline first drives a CPU
llama-server sidecar (decoder + bf16 mmproj) with one contact per row to warm
the legacy feature cache, and only then promotes the warm entries into audited
packets. The first phase is a model contact, so a model-free mission cannot run
it. Every model-free prerequisite is produced here and the plan states exactly
what remains.

MODEL-FREE: no model, tokenizer, encoder, ASR, server, network or GPU is
reached; the offline guard is armed before the first input is opened. CPU work
is capped at 8 workers (standing rule while a GPU campaign flies). Media is
decoded through ``soundfile`` headers only -- no resampling, no ffmpeg (absent
by design), and no byte of any media file is rewritten. The D1 closure is proved
through the GATE'S OWN READER (``contracts.FrozenCoreGate.
assert_media_identity_closure``), not through a local re-read of the artifact,
so "no D1 supplement is needed" is the gate's answer rather than this script's.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_runtime_view.py \\
        --roster-receipt docs/receipts/rosters/slurp-devel-remainder-v2.json \\
        --output configs/dataset/slurp-speech-native-devel-remainder-v2.json \\
        --checks-dir docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-devel-remainder-v2-packets \\
        --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
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
from speech_aware_evidence_acquisition.contracts import FrozenCoreGate  # noqa: E402
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
MAX_WORKERS = 8  # standing rule: <= 8 CPU workers while a GPU campaign may fly
PARENT_D1_RELPATH = "docs/receipts/artifacts/d1-identity.json"
RUNTIME_RECEIPT_RELPATH = "receipts/runtime-q4km-preprocess.json"
RUNTIME_ROOT = Path("/home/chao")
PREPROCESS_MODEL_LOCK_KEY = "qwen3-omni-30b-a3b-instruct-gguf-q4km"
LEGACY_CACHE_DIR = Path("/home/chao/feat-cache/slurp-q4km")
SERVED_PACKET_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
GENERATOR = "scripts/build_slurp_runtime_view.py"

#: ``slurp:<split>:<utterance>:<recording>`` -- the loader split each roster
#: prefix belongs to.
SPLIT_OF_PREFIX = {"devel": "devel", "train": "train", "test": "test"}


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


def split_of(sample_ids: Sequence[str]) -> str:
    """The one loader split every roster row belongs to; refuse a mixture."""

    splits = {sample_id.split(":")[1] for sample_id in sample_ids}
    if len(splits) != 1:
        raise SystemExit(f"roster rows span several splits: {sorted(splits)}")
    split = splits.pop()
    if split not in SPLIT_OF_PREFIX:
        raise SystemExit(f"roster rows name an unknown split {split!r}")
    return SPLIT_OF_PREFIX[split]


def default_split_name(roster_id: str) -> str:
    """``SLURP-DEVEL-REMAINDER-V2`` -> ``DEVEL-REMAINDER``.

    The ``split_name`` a runtime view carries is the roster's own name without
    the carrier prefix and version suffix -- the convention
    ``DEV-2000-ADDED`` / ``STAGE3-CONSTRUCTION-R01`` already follow. ANY
    ``-V<n>`` suffix is dropped, not just ``-V1``: which population a view
    describes is the split name, which FREEZE of it is the roster id, the
    receipt relpath and the split identity hash, and conflating the two would
    make ``DEVEL-REMAINDER-V2`` read like a different population. A caller that
    wants something else passes ``--split-name``.
    """

    name = roster_id
    if name.startswith("SLURP-"):
        name = name[len("SLURP-") :]
    return re.sub(r"-V\d+$", "", name)


def promoted_coverage(packet_ids: Sequence[str]) -> dict[str, object]:
    """Id-level audit: which rows the resident packet root already serves.

    Reads only promotion-receipt JSON documents and directory names under the
    resident root -- never a packet byte, never a ``.feat`` file, never a media
    file. The same method the R01 preparation note used, generalised.
    """

    wanted = set(packet_ids)
    if not SERVED_PACKET_ROOT.is_dir():
        return {"root": str(SERVED_PACKET_ROOT), "available": False, "covered_rows": 0}
    receipts: list[dict[str, object]] = []
    covered: set[str] = set()
    for path in sorted(SERVED_PACKET_ROOT.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            receipts.append({"receipt": path.name, "packets": None, "covers": None})
            continue
        entries = document.get("packets")
        if not isinstance(entries, list):
            receipts.append({"receipt": path.name, "packets": None, "covers": None})
            continue
        ids = {str(entry.get("packet_id")) for entry in entries}
        hits = ids & wanted
        covered |= hits
        receipts.append({"receipt": path.name, "packets": len(ids), "covers": len(hits)})
    leaves: set[str] = set()
    for prefix in sorted({pid.rsplit("/", 2)[0] for pid in wanted}):
        directory = SERVED_PACKET_ROOT / prefix
        if not directory.is_dir():
            continue
        for utterance in directory.iterdir():
            if not utterance.is_dir():
                continue
            for recording in utterance.iterdir():
                if recording.is_dir():
                    leaves.add(f"{prefix}/{utterance.name}/{recording.name}")
    return {
        "root": str(SERVED_PACKET_ROOT),
        "available": True,
        "method": (
            "id level only: every promotion-receipt document under the resident root is "
            "parsed for its packets[].packet_id set and intersected with this roster's "
            "packet ids, then confirmed against the on-disk leaf directories. No packet "
            "byte, no .feat file and no media file is read."
        ),
        "receipts_inspected": receipts,
        "covered_rows": len(covered),
        "uncovered_rows": len(wanted) - len(covered),
        "on_disk_leaf_directories_under_this_carrier_split": len(leaves),
        "on_disk_leaves_that_are_roster_rows": len(leaves & wanted),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster-receipt", required=True, help="committed roster receipt relpath")
    parser.add_argument("--output", required=True, help="runtime view relpath to write")
    parser.add_argument("--checks-dir", required=True, help="check directory relpath to write")
    parser.add_argument("--split-name", default=None, help="override the derived split_name")
    parser.add_argument(
        "--workers", type=int, default=MAX_WORKERS, help=f"CPU workers (<= {MAX_WORKERS})"
    )
    parser.add_argument("--write", action="store_true", help="write the artifacts")
    args = parser.parse_args(argv)

    if not 1 <= args.workers <= MAX_WORKERS:
        raise SystemExit(
            f"--workers must be between 1 and {MAX_WORKERS} (a GPU campaign may be flying)"
        )

    attempts = arm_offline_guard()
    roster = read_roster(REPO_ROOT / args.roster_receipt)
    if roster["carrier_lock_key"] != CARRIER:
        raise SystemExit(f"{args.roster_receipt} is not a SLURP roster")
    sample_ids = sorted(str(item["sample_id"]) for item in roster["items"])
    if len(sample_ids) != len(roster["items"]):
        raise SystemExit("the roster repeats a sample id")
    split = split_of(sample_ids)
    split_name = args.split_name or default_split_name(str(roster["roster_id"]))

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    relpath_by_id = {
        record.sample_id: record.media_relpath
        for record in load_slurp_split(lock, root, split)
    }
    missing = [sid for sid in sample_ids if sid not in relpath_by_id]
    if missing:
        raise SystemExit(f"{len(missing)} roster id(s) absent from the {split} loader")

    confined = [
        (
            sample_id,
            *_confined_media_path(
                root,
                relpath_by_id[sample_id],
                context=f"{split_name} sample {sample_id!r}",
            ),
        )
        for sample_id in sample_ids
    ]

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=min(args.workers, len(confined))) as pool:
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

    # ---- D1 closure, answered by the GATE'S OWN READER --------------------
    # The gate is constructed WITHOUT a D1 media supplement on purpose: if the
    # base D1 identity artifact already closes over every roster row, no
    # supplement is needed and the runtime view says so by carrying nulls.
    # assert_media_identity_closure raises GateClosed on the first id that is
    # not declared; it opens no media file and makes no model touch.
    gate = FrozenCoreGate.for_study_repo(
        REPO_ROOT,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=RUNTIME_RECEIPT_RELPATH,
        expected_model_lock_key=PREPROCESS_MODEL_LOCK_KEY,
    )
    gate.assert_media_identity_closure(CARRIER, sample_ids)
    closure_ids = gate.media_identity_closure_ids(CARRIER)
    # The bytes half of the same question: D1's record for each row must be
    # the bytes measured above, or the view would pin media D1 never saw.
    d1 = json.loads((REPO_ROOT / PARENT_D1_RELPATH).read_text(encoding="utf-8"))
    d1_media = {
        entry["id"]: entry for entry in d1["carriers"][CARRIER]["layers"]["media"]["manifest"]
    }
    for item in items:
        base = d1_media.get(str(item["sample_id"]))
        if base is None:
            raise SystemExit(f"sample {item['sample_id']!r} is OUTSIDE the D1 closure")
        if base["sha256"] != item["audio_sha256"] or base["bytes"] != item["bytes"]:
            raise SystemExit(
                f"sample {item['sample_id']!r} media bytes drifted from D1's record"
            )

    view_items = [
        {key: value for key, value in item.items() if key != "bytes"} for item in items
    ]
    unsigned: dict[str, object] = {
        "schema": "saea-speech-native-runtime-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": CARRIER,
        "split_name": split_name,
        "split_role": roster["split_role"],
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
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        keys = list(pool.map(cache_key_of, paths, chunksize=16))
    cache_seconds = time.monotonic() - started
    warm = 0
    cold_ids: list[str] = []
    cache_available = LEGACY_CACHE_DIR.is_dir()
    if cache_available:
        entries = {path.name for path in LEGACY_CACHE_DIR.glob("*_o*.feat")}
        prefixes = {name.split("_o", 1)[0] for name in entries}
        for sample_id, key in zip(sample_ids, keys, strict=True):
            if key in prefixes:
                warm += 1
            else:
                cold_ids.append(sample_id)
    else:
        cold_ids = list(sample_ids)

    audio_seconds_total = float(runtime_view["audio_seconds_total"])
    coverage = promoted_coverage([str(item["packet_id"]) for item in items])
    inventory = {
        "schema": "saea-slurp-speech-native-media-inventory-v1",
        "study": "speech-aware-evidence-acquisition",
        "generator": GENERATOR,
        "roster": {
            "relpath": args.roster_receipt,
            "roster_id": roster["roster_id"],
            "split_identity_hash": roster["split_identity_hash"],
            "receipt_file_sha256": hashlib.sha256(
                (REPO_ROOT / args.roster_receipt).read_bytes()
            ).hexdigest(),
        },
        "runtime_view": {
            "relpath": args.output,
            "runtime_view_sha256": runtime_view["runtime_view_sha256"],
            "per_file_sha256": (
                "one audio_sha256 per row inside the runtime view; the inventory does not "
                "duplicate the digests"
            ),
        },
        "counts": {
            "recordings": len(items),
            "distinct_utterances": len({str(i["sample_id"]).rsplit(":", 1)[0] for i in items}),
            "total_bytes": total_bytes,
            "audio_seconds_total": audio_seconds_total,
            "audio_seconds_declared_ceiling": int(math.ceil(audio_seconds_total)),
            "sample_rates_hz": sorted({int(item["sample_rate_hz"]) for item in items}),
        },
        "d1_closure": {
            "relpath": PARENT_D1_RELPATH,
            "reader": (
                "contracts.FrozenCoreGate.assert_media_identity_closure / "
                "media_identity_closure_ids -- the gate's own reader, with NO D1 media "
                "supplement configured"
            ),
            "closure_ids_for_carrier": len(closure_ids),
            "covered_items": len(items),
            "supplement_required": False,
        },
        "cpu_pipeline": {
            "workers": args.workers,
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
        "promoted_packet_coverage": coverage,
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    inventory["inventory_sha256"] = canonical_sha256(inventory)

    plan = {
        "schema": "saea-slurp-speech-native-packet-plan-v1",
        "study": "speech-aware-evidence-acquisition",
        "generator": GENERATOR,
        "state": "PREREQUISITES COMPLETE; ENCODE AND PROMOTE NOT RUN",
        "why_not_run": (
            "A speech packet in this repository is an ENCODER product. The pipeline "
            "(scripts/slurp_evo_fold_preprocess.py, precedent SAEA-SN-DEV2000-ADDED-"
            "PREPROCESS) first drives a CPU llama-server sidecar carrying the decoder and "
            "the bf16 mmproj with one contact per row at max_tokens 1 to warm the legacy "
            "feature cache, and only then promotes the warm entries. That first phase is a "
            "model contact under a structured ExecutionPlan, which a model-free mission may "
            "not make. Everything that does not need the encoder is done and committed."
        ),
        "rows": len(items),
        "rows_needing_encode": len(cold_ids),
        "rows_promotable_with_zero_contacts": warm,
        "rows_already_promoted_under_the_resident_root": coverage.get("covered_rows"),
        "target_packet_root": {
            "path": str(SERVED_PACKET_ROOT),
            "write_mode": (
                "ADDITIVE ONLY: new per-row packet directories plus one new promotion "
                "receipt. No file the resident session already serves is read-modified-"
                "written, and no existing promotion receipt is touched; an already-promoted "
                "packet id is re-verified byte for byte (item E40 makes an encoder-receipt-"
                "only difference SHARED rather than a refusal)."
            ),
        },
        "what_remains": [
            {
                "step": 1,
                "name": "ENCODE",
                "detail": (
                    "CPU llama-server sidecar on port 8081 (-ngl 0 --no-mmproj-offload, "
                    "receipts/runtime-q4km-preprocess.json), one contact per roster row at "
                    "max_tokens 1, under its own session and stop receipts. GPU stays free."
                ),
                "contacts": len(items),
                "speech_seconds": round(audio_seconds_total, 3),
            },
            {
                "step": 2,
                "name": "PROMOTE",
                "detail": (
                    "core.model.speech_features."
                    "materialize_legacy_cached_speech_feature_packets over the runtime "
                    "view's packet ids, workers <= 8, writing the roster's own promotion "
                    "receipt beside the existing per-set receipts."
                ),
                "contacts": 0,
            },
        ],
        "binding": {
            "runtime_view": args.output,
            "runtime_view_sha256": runtime_view["runtime_view_sha256"],
            "roster": args.roster_receipt,
            "split_identity_hash": roster["split_identity_hash"],
        },
    }
    plan["plan_sha256"] = canonical_sha256(plan)

    summary = {
        "roster_id": roster["roster_id"],
        "split_name": split_name,
        "count": runtime_view["count"],
        "audio_seconds_total": runtime_view["audio_seconds_total"],
        "audio_seconds_declared_ceiling": int(math.ceil(audio_seconds_total)),
        "total_bytes": total_bytes,
        "runtime_view_sha256": runtime_view["runtime_view_sha256"],
        "split_identity_hash": runtime_view["split_identity_hash"],
        "d1_closure": inventory["d1_closure"],
        "cpu_pipeline": inventory["cpu_pipeline"],
        "legacy_feature_cache": inventory["legacy_feature_cache"],
        "promoted_packet_coverage": {
            "covered_rows": coverage.get("covered_rows"),
            "uncovered_rows": coverage.get("uncovered_rows"),
        },
        "offline_guard": inventory["offline_guard"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.write:
        view_file_sha256 = write_json(REPO_ROOT / args.output, runtime_view)
        check_dir = REPO_ROOT / args.checks_dir
        write_json(check_dir / "media-inventory.json", inventory)
        write_json(check_dir / "packet-preparation-plan.json", plan)
        print(f"wrote {args.output} (file sha256 {view_file_sha256})")
        print(f"wrote {args.checks_dir}/media-inventory.json")
        print(f"wrote {args.checks_dir}/packet-preparation-plan.json")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
