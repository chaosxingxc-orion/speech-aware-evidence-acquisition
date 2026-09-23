#!/usr/bin/env python3
"""Build a SLURP roster's label-free runtime view and its packet prerequisites.

Owner decisions 99 (2026-09-22) and 107 (2026-09-23): the ONE complete official
SLURP test-split read happens at the end of Stage 3, and its preparations are
registered now and built ahead of time so the read waits on nothing. This script
produces everything the featcache packet pipeline needs that can be produced
WITHOUT a model:

1. ``configs/dataset/slurp-speech-native-test-full.json`` -- the label-free
   ``saea-speech-native-runtime-view-v1`` fragment (media identity only:
   relpath, SHA-256, header duration, sample rate, packet id), the same schema
   and the same consume-verbatim discipline as
   ``scripts/build_dev2000_added_runtime_view.py``. It is what
   ``scripts/slurp_evo_fold_preprocess.py``'s ENCODE phase and
   ``core.model.speech_features.materialize_legacy_cached_speech_feature_packets``'s
   PROMOTE phase both bind.
2. ``docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-test-full-packets/``
   -- the media inventory (aggregate facts plus measured CPU throughput), the
   legacy feature-cache warmth measurement (how many rows could be promoted with
   ZERO contacts), and the packet-preparation plan.

Roster-parameterised (``--roster-receipt`` / ``--split-name`` / ``--output`` /
``--check-dir`` / ``--promotion-receipt-name``) rather than a near-duplicate of
the DEV-2000-ADDED builder: the defaults name ``SLURP-TEST-FULL-13078-V1``
because that is the roster it was written for. A generic
``scripts/build_slurp_runtime_view.py`` does not exist in this checkout; if one
lands, this file becomes its thin caller.

Why the packets themselves are NOT promoted here. In this repository a "speech
packet" is an ENCODER product: the two-phase pipeline first drives a CPU
llama-server sidecar with one contact per row at ``max_tokens: 1`` to warm the
legacy feature cache, and only then promotes the warm entries into audited
packets. The first phase is a model contact under a structured
``contracts.ExecutionPlan``, which a model-free mission may not make -- and for
this roster it is additionally refused until the owner allowance of
``contracts.plan.require_owner_split_allowance`` says ``authorised``.

MODEL-FREE and LABEL-FREE: no model, tokenizer, encoder, ASR, scorer, server,
network or GPU is reached; the offline guard is armed before the first input is
opened. No utterance text, transcript, gold label, intent or slot annotation is
opened -- the roster receipt is the only source of ids, and media is read as
bytes plus a container HEADER. CPU work is capped at 8 workers (standing rule
while a GPU campaign flies).

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>:<repo>/src \\
      python scripts/build_slurp_test_full_runtime_view.py --write
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
from speech_aware_evidence_acquisition.data.slurp import _governed_roots  # noqa: E402
from speech_aware_evidence_acquisition.e0.d1_identity import (  # noqa: E402
    _confined_media_path,
    _probe_speech_media,
)

CARRIER = "slurp"
WORKERS = 8  # standing rule: <= 8 CPU workers while a GPU campaign may fly
DEFAULT_ROSTER = "docs/receipts/rosters/slurp-test-full-13078-v1.json"
DEFAULT_SPLIT_NAME = "TEST-FULL"
DEFAULT_OUTPUT = "configs/dataset/slurp-speech-native-test-full.json"
DEFAULT_CHECK_DIR = (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-23-slurp-test-full-packets"
)
DEFAULT_PROMOTION_RECEIPT = "TEST-FULL-promotion.json"
PARENT_D1_RELPATH = "docs/receipts/artifacts/d1-identity.json"
LEGACY_CACHE_DIR = Path("/home/chao/feat-cache/slurp-q4km")
SERVED_PACKET_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
AUTHORITY = (
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md owner "
    "decisions 99 (2026-09-22) and 107 (2026-09-23)"
)
GENERATOR = "scripts/build_slurp_test_full_runtime_view.py"
ALLOWANCE_RELPATH = "docs/receipts/owner/2026-09-23-slurp-test-split-allowance-v1.json"


def canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def write_json(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_key_of(path_text: str) -> str:
    """FNV-1a legacy feature-cache key of one media file (process-pool entry)."""

    from speech_aware_evidence_acquisition.core.model.speech_features import (
        legacy_audio_feature_cache_key,
    )

    return legacy_audio_feature_cache_key(Path(path_text).read_bytes())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--roster-receipt", default=DEFAULT_ROSTER)
    parser.add_argument("--split-name", default=DEFAULT_SPLIT_NAME)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--check-dir", default=DEFAULT_CHECK_DIR)
    parser.add_argument("--promotion-receipt-name", default=DEFAULT_PROMOTION_RECEIPT)
    parser.add_argument("--workers", type=int, default=WORKERS)
    parser.add_argument(
        "--no-carry-d1",
        action="store_true",
        help=(
            "write a null D1 supplement triple even when the existing view already "
            "carries one (the first build, before the supplement exists)"
        ),
    )
    parser.add_argument(
        "--verify-d1-gate",
        action="store_true",
        help=(
            "additionally run contracts.FrozenCoreGate.verify_media_identity over every "
            "roster row against the pinned D1 supplement and write its receipt; needs the "
            "supplement to exist, so it is a second pass after the supplement builder"
        ),
    )
    parser.add_argument("--write", action="store_true", help="write the artifacts")
    args = parser.parse_args(argv)
    workers = int(args.workers)
    if not 1 <= workers <= WORKERS:
        raise SystemExit(f"--workers must be in [1, {WORKERS}]")

    attempts = arm_offline_guard()
    roster = read_roster(REPO_ROOT / args.roster_receipt)
    if roster["carrier_lock_key"] != CARRIER:
        raise SystemExit(f"roster receipt carrier must be {CARRIER!r}")
    sample_ids = sorted(str(item["sample_id"]) for item in roster["items"])
    split_tokens = {value.split(":")[1] for value in sample_ids}
    if len(split_tokens) != 1:
        raise SystemExit(f"roster spans several SLURP splits: {sorted(split_tokens)}")
    split = split_tokens.pop()

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    audio_root_relpath, _audio_root, _metadata_dir = _governed_roots(lock, root)
    # Identity only: the media relpath is DERIVED from the roster's own sample
    # id, so no split metadata file is opened here at all. The roster receipt
    # already proved that id set against the governed jsonl and the frozen
    # split-identity receipt.
    confined = [
        (
            sample_id,
            *_confined_media_path(
                root,
                f"{audio_root_relpath}/slurp_real/{sample_id.split(':')[3]}.flac",
                context=f"{args.split_name} sample {sample_id!r}",
            ),
        )
        for sample_id in sample_ids
    ]

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=min(workers, len(confined))) as pool:
        measured = tuple(pool.map(_probe_speech_media, (entry[2] for entry in confined)))
    inventory_seconds = time.monotonic() - started

    roster_seconds = {
        str(item["sample_id"]): float(item["audio_seconds"]) for item in roster["items"]
    }
    items: list[dict[str, object]] = []
    total_bytes = 0
    for (sample_id, media_relpath, _path), facts in zip(confined, measured, strict=True):
        media_bytes, media_sha256, audio_seconds, sample_rate_hz = facts
        if abs(roster_seconds[sample_id] - float(audio_seconds)) > 1e-6:
            raise SystemExit(
                f"audio duration drift for {sample_id!r}: roster "
                f"{roster_seconds[sample_id]} vs header {audio_seconds}"
            )
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

    # D1 closure: base D1 closes over the SLURP devel split only, so a test-split
    # or train-split roster is OUTSIDE it and needs the additive supplement that
    # scripts/build_slurp_stage3_construction_r01_d1_supplement.py writes. The
    # count of rows already inside base D1 is measured, never assumed.
    d1 = json.loads((REPO_ROOT / PARENT_D1_RELPATH).read_text(encoding="utf-8"))
    d1_media = {
        entry["id"]: entry
        for entry in d1["carriers"][CARRIER]["layers"]["media"]["manifest"]
    }
    covered = 0
    for item in items:
        base = d1_media.get(str(item["sample_id"]))
        if base is None:
            continue
        covered += 1
        if base["sha256"] != item["audio_sha256"] or base["bytes"] != item["bytes"]:
            raise SystemExit(
                f"sample {item['sample_id']!r} media bytes drifted from D1's record"
            )

    # A D1 media supplement is written AFTER this view exists (the supplement
    # builder binds the view's own source_binding_sha256), and pinning it moves
    # the view's signature. Rebuilding the view must therefore CARRY the triple
    # forward, or the media inventory beside it would record a signature the
    # committed view no longer has. The supplement file is re-hashed before it
    # is carried, so a stale or edited supplement fails closed rather than being
    # silently re-pinned.
    carried: dict[str, object] = {
        "d1_media_supplement": None,
        "d1_media_supplement_sha256": None,
        "d1_manifest_sha256": None,
    }
    existing_path = REPO_ROOT / args.output
    if not args.no_carry_d1 and existing_path.is_file():
        existing = json.loads(existing_path.read_text(encoding="utf-8"))
        triple = tuple(existing.get(key) for key in carried)
        if all(value is not None for value in triple):
            if existing.get("source_binding_sha256") != canonical_sha256(roster):
                raise SystemExit(
                    "the existing runtime view binds a different roster receipt; refusing "
                    "to carry its D1 supplement triple"
                )
            supplement_path = REPO_ROOT / "docs" / str(triple[0])
            measured = hashlib.sha256(supplement_path.read_bytes()).hexdigest()
            if measured != triple[1]:
                raise SystemExit(
                    f"D1 supplement {supplement_path} hashes to {measured}, not the "
                    f"{triple[1]} the existing runtime view pins; refusing to carry it"
                )
            supplement = json.loads(supplement_path.read_text(encoding="utf-8"))
            if supplement.get("manifest_sha256") != triple[2]:
                raise SystemExit(
                    "the D1 supplement's own manifest_sha256 disagrees with the runtime "
                    "view's; refusing to carry it"
                )
            carried = {
                "d1_media_supplement": triple[0],
                "d1_media_supplement_sha256": triple[1],
                "d1_manifest_sha256": triple[2],
            }

    view_items = [
        {key: value for key, value in item.items() if key != "bytes"} for item in items
    ]
    unsigned: dict[str, object] = {
        "schema": "saea-speech-native-runtime-view-v1",
        "study": "speech-aware-evidence-acquisition",
        "status": "MODEL-FREE, LABEL-FREE ENGINEERING INPUT; NOT AN EXPOSURE REGISTRATION",
        "carrier_lock_key": CARRIER,
        "split_name": args.split_name,
        "split_role": roster["split_role"],
        "seed": roster["seed"],
        "split_identity_hash": roster["split_identity_hash"],
        "source_binding_sha256": canonical_sha256(roster),
        **carried,
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
    with ProcessPoolExecutor(max_workers=workers) as pool:
        keys = list(pool.map(cache_key_of, paths, chunksize=16))
    cache_seconds = time.monotonic() - started
    warm = 0
    cold = 0
    cache_available = LEGACY_CACHE_DIR.is_dir()
    if cache_available:
        entries = {path.name for path in LEGACY_CACHE_DIR.glob("*_o*.feat")}
        prefixes = {name.split("_o", 1)[0] for name in entries}
        for key in keys:
            if key in prefixes:
                warm += 1
            else:
                cold += 1
    else:
        cold = len(keys)

    # Already-promoted packets under the resident root (id level only: no packet
    # byte, no .feat file and no audio sample is read).
    promoted = 0
    if SERVED_PACKET_ROOT.is_dir():
        for item in items:
            leaf = SERVED_PACKET_ROOT / str(item["packet_id"])
            if leaf.is_dir():
                promoted += 1

    audio_seconds_total = float(runtime_view["audio_seconds_total"])
    check_dir = Path(args.check_dir)
    inventory = {
        "schema": "saea-slurp-roster-media-inventory-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "roster": {
            "relpath": args.roster_receipt,
            "roster_id": roster["roster_id"],
            "split": split,
            "split_role": roster["split_role"],
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
                f"duplicate {len(items)} digests"
            ),
        },
        "counts": {
            "recordings": len(items),
            "distinct_utterances": len(
                {":".join(str(i["sample_id"]).split(":")[:3]) for i in items}
            ),
            "headset": sum(
                1 for i in items if str(i["sample_id"]).endswith("-headset")
            ),
            "far_field": sum(
                1 for i in items if not str(i["sample_id"]).endswith("-headset")
            ),
            "total_bytes": total_bytes,
            "audio_seconds_total": audio_seconds_total,
            "sample_rates_hz": sorted({int(item["sample_rate_hz"]) for item in items}),
        },
        "d1_closure": {
            "relpath": PARENT_D1_RELPATH,
            "covered_items": covered,
            "supplement_required": covered < len(items),
            "supplement_relpath": carried["d1_media_supplement"],
            "supplement_sha256": carried["d1_media_supplement_sha256"],
            "supplement_manifest_sha256": carried["d1_manifest_sha256"],
            "note": (
                "The immutable D1 identity artifact closes over the SLURP devel split "
                "only, so every row of a test-split roster sits outside it and the "
                "additive saea-d1-media-supplement-v1 successor is required. The "
                "supplement is written by "
                "scripts/build_slurp_stage3_construction_r01_d1_supplement.py, which "
                "re-hashes every media file, and this builder carries its pinned triple "
                "forward on a rebuild after re-verifying the supplement's bytes."
            ),
        },
        "cpu_pipeline": {
            "workers": workers,
            "decoder": (
                "soundfile header probe for duration and rate; bytes hashed with SHA-256. "
                "ffmpeg is absent by design and no media byte is rewritten -- the librosa "
                "fallback stays the pinned decode path for every later consumer."
            ),
            "media_inventory_wall_seconds": round(inventory_seconds, 3),
            "media_inventory_files_per_second": round(
                len(items) / max(inventory_seconds, 1e-9), 3
            ),
            "media_inventory_audio_seconds_per_wall_second": round(
                audio_seconds_total / max(inventory_seconds, 1e-9), 3
            ),
            "media_inventory_mib_per_second": round(
                total_bytes / (1024 * 1024) / max(inventory_seconds, 1e-9), 3
            ),
            "cache_key_wall_seconds": round(cache_seconds, 3),
            "cache_key_files_per_second": round(
                len(items) / max(cache_seconds, 1e-9), 3
            ),
        },
        "legacy_feature_cache": {
            "dir": str(LEGACY_CACHE_DIR),
            "available": cache_available,
            "warm_rows": warm,
            "cold_rows": cold,
            "key_convention": (
                "core.model.speech_features.legacy_audio_feature_cache_key -- FNV-1a over "
                "the encoded media bytes, so warmth is a property of the file, not of a "
                "prompt"
            ),
        },
        "already_promoted_packets": {
            "packet_root": str(SERVED_PACKET_ROOT),
            "rows_with_a_leaf_directory": promoted,
            "method": (
                "id-level only: the existence of the leaf directory "
                "<packet_root>/<packet_id> is tested. No packet byte, no .feat file and "
                "no audio sample is read."
            ),
        },
        "offline_guard": {
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    }
    inventory["inventory_sha256"] = canonical_sha256(inventory)

    plan = {
        "schema": "saea-slurp-roster-packet-plan-v1",
        "study": "speech-aware-evidence-acquisition",
        "authority": AUTHORITY,
        "generator": GENERATOR,
        "state": "PREREQUISITES COMPLETE; ENCODE AND PROMOTE NOT RUN AND NOT AUTHORISED",
        "why_not_run": (
            "A speech packet in this repository is an ENCODER product. The pipeline "
            "(scripts/slurp_evo_fold_preprocess.py) first drives a CPU llama-server sidecar "
            "with one contact per row at max_tokens 1 to warm the legacy feature cache, and "
            "only then promotes the warm entries. That first phase is a model contact under "
            "a structured ExecutionPlan, which a model-free mission may not make. For THIS "
            "roster it is additionally refused by contracts.plan."
            "require_owner_split_allowance: the split role is 'final-report' and the "
            f"committed allowance {ALLOWANCE_RELPATH} says 'pending-owner'."
        ),
        "rows_needing_encode": len(items),
        "rows_already_warm_in_the_legacy_cache": warm,
        "target_packet_root": {
            "path": str(SERVED_PACKET_ROOT),
            "promotion_receipt": f"{SERVED_PACKET_ROOT}/{args.promotion_receipt_name}",
            "write_mode": (
                "ADDITIVE ONLY: new per-row packet directories under "
                f"slurp/{split}/<utterance>/<recording>/ and one new promotion receipt. No "
                "file the resident session already serves is read-modified-written, and no "
                "existing promotion receipt is touched. Promotion is refuse-on-conflict by "
                "construction."
            ),
        },
        "what_remains": [
            {
                "step": 1,
                "name": "ENCODE",
                "detail": (
                    "CPU llama-server sidecar on port 8081 (-ngl 0 --no-mmproj-offload, "
                    "receipts/runtime-q4km-preprocess.json), one contact per row at "
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
                    "view's packet ids, workers <= 8, writing "
                    f"{args.promotion_receipt_name} beside the existing per-set receipts."
                ),
                "contacts": 0,
            },
        ],
        "binding": {
            "runtime_view": args.output,
            "runtime_view_sha256": runtime_view["runtime_view_sha256"],
            "roster": args.roster_receipt,
            "split_identity_hash": roster["split_identity_hash"],
            "owner_allowance": ALLOWANCE_RELPATH,
        },
    }
    plan["plan_sha256"] = canonical_sha256(plan)

    # ---- the D1 gate reader, over every row (zero contacts) ---------------
    gate_verification: dict[str, object] | None = None
    if args.verify_d1_gate:
        from speech_aware_evidence_acquisition.contracts import (  # noqa: PLC0415
            FrozenCoreGate,
        )

        if carried["d1_media_supplement"] is None:
            raise SystemExit(
                "--verify-d1-gate needs the runtime view to pin a D1 supplement; run "
                "scripts/build_slurp_stage3_construction_r01_d1_supplement.py "
                "--write --pin-runtime-view first"
            )
        gate = FrozenCoreGate(
            e0_receipt=REPO_ROOT / "docs/receipts/e0-closure.json",
            runtime_receipt=REPO_ROOT / "docs/receipts/runtime.json",
            data_root=root,
            lock_path=umbrella_lock_path(REPO_ROOT),
            runtime_root=Path("/home/chao"),
            exposure_ledger=REPO_ROOT / "docs/exposure-ledger.md",
            source_root=REPO_ROOT,
            d1_media_supplement=REPO_ROOT
            / "docs"
            / str(carried["d1_media_supplement"]),
            d1_media_supplement_sha256=str(carried["d1_media_supplement_sha256"]),
        )
        media_facts = {
            str(item["sample_id"]): (
                str(item["media_relpath"]),
                float(item["audio_seconds"]),
            )
            for item in view_items
        }
        started = time.monotonic()
        gate.verify_media_identity(CARRIER, media_facts)
        gate_seconds = time.monotonic() - started
        gate_verification = {
            "schema": "saea-d1-supplement-gate-verification-v1",
            "study": "speech-aware-evidence-acquisition",
            "authority": AUTHORITY,
            "generator": f"{GENERATOR} --verify-d1-gate",
            "checked_by": (
                "contracts.FrozenCoreGate.verify_media_identity -- the SAME reader the "
                "frozen-core gate uses before a model touch: it resolves D1 through the "
                "E0 closure receipt, loads the additive supplement, and re-measures every "
                "named file's size and SHA-256 from disk"
            ),
            "roster": {
                "relpath": args.roster_receipt,
                "roster_id": roster["roster_id"],
                "split_identity_hash": roster["split_identity_hash"],
            },
            "d1_supplement": {
                "relpath": f"docs/{carried['d1_media_supplement']}",
                "sha256": carried["d1_media_supplement_sha256"],
                "manifest_sha256": carried["d1_manifest_sha256"],
            },
            "runtime_view": {
                "relpath": args.output,
                "runtime_view_sha256": runtime_view["runtime_view_sha256"],
            },
            "rows_verified": len(media_facts),
            "rows_from_base_d1": covered,
            "rows_from_the_supplement": len(media_facts) - covered,
            "verdict": "PASS",
            "wall_seconds": round(gate_seconds, 3),
            "contacts": {"model": 0, "encoder": 0, "tokenizer": 0, "scorer": 0, "gpu": 0},
            "note": (
                "A PASS here means the gate READER accepts the supplement over every "
                "roster row. It is NOT an authorisation: a final-report ExecutionPlan is "
                f"still refused by contracts.plan.require_owner_split_allowance while "
                f"{ALLOWANCE_RELPATH} says 'pending-owner'."
            ),
        }
        gate_verification["verification_sha256"] = canonical_sha256(gate_verification)

    summary = {
        "count": runtime_view["count"],
        "split": split,
        "split_role": runtime_view["split_role"],
        "audio_seconds_total": runtime_view["audio_seconds_total"],
        "total_bytes": total_bytes,
        "runtime_view_sha256": runtime_view["runtime_view_sha256"],
        "source_binding_sha256": runtime_view["source_binding_sha256"],
        "split_identity_hash": runtime_view["split_identity_hash"],
        "counts": inventory["counts"],
        "d1_closure": inventory["d1_closure"],
        "cpu_pipeline": inventory["cpu_pipeline"],
        "legacy_feature_cache": inventory["legacy_feature_cache"],
        "already_promoted_packets": inventory["already_promoted_packets"],
        "offline_guard": inventory["offline_guard"],
        "d1_gate_verification": gate_verification,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.write:
        view_file_sha256 = write_json(REPO_ROOT / args.output, runtime_view)
        write_json(REPO_ROOT / check_dir / "media-inventory.json", inventory)
        write_json(REPO_ROOT / check_dir / "packet-preparation-plan.json", plan)
        print(f"wrote {args.output} (file sha256 {view_file_sha256})")
        print(f"wrote {check_dir}/media-inventory.json")
        print(f"wrote {check_dir}/packet-preparation-plan.json")
        if gate_verification is not None:
            write_json(
                REPO_ROOT / check_dir / "d1-gate-verification.json", gate_verification
            )
            print(f"wrote {check_dir}/d1-gate-verification.json")
    return 0


if __name__ == "__main__":
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    raise SystemExit(main())
