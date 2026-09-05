#!/usr/bin/env python3
"""Build the A2T-ORG-1 roster: the UNION of the three sealed official-population draws.

No new draw and no new identity. The 2026-09-04 official-population flights
sealed three rosters -- tier 1 (500 rows), tiers 2/5/8 (1,500) and tiers
3/4/6/7 (2,000) -- and every one of their 4,000 rows already carries a sealed
official-protocol output under the compact registry. A2T-ORG-1 varies exactly
one factor (which of the pinned release's two registry renderers builds the
tool block), so it must fly those same 4,000 rows and nothing else; this
script merges the three receipts into one, recomputes the identity hashes over
the merged set, and writes a receipt of the same
``saea-a2t-agentloop-flight-roster-receipt-v1`` schema the flight entry point
and the D1 supplement builder already read.

What it verifies rather than assumes:

* each parent receipt hashes to the value its own committed dataset fragment
  pins (so the union is built from the bytes the sealed flights flew);
* each parent's own ``split_identity_hash`` and ``flight_split_identity_hash``
  reproduce from its items;
* the three id sets are pairwise disjoint and cover all eight tiers;
* every merged item's media file still exists and still hashes to the
  parent receipt's ``audio_sha256``, and its WAV header still gives the
  parent's ``audio_seconds`` (``--verify-media``, the default);
* the summed audio seconds equal the three parents' recorded sums.

Contact surface: media bytes are re-hashed and WAV headers are read for
duration. Domain COUNTS are read from each tier's released manifest -- the
same stratum metadata the parent receipts already record -- and no gold tool
name, expected call, transcript, annotation, model output, score or future
turn is opened. No model, network, tokenizer or scorer contact.

Usage (WSL2, model-free)::

    python scripts/build_a2t_org1_union_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import wave
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
CARRIER = "audio2tool"
SPLIT_NAME = "A2T-ORG1-UNION-4000"
SPLIT_ROLE = "discovery"

#: The three sealed parents, each with the dataset fragment that pins its hash.
PARENTS: tuple[tuple[str, str, str], ...] = (
    (
        "SAEA-A2T-TIER1-OFFICIAL-POPULATION-V1",
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-04-a2t-tier1-official-population-roster/flight-roster-receipt.json",
        "configs/dataset/audio2tool-tier1-official-population-500.json",
    ),
    (
        "SAEA-A2T-TIER258-OFFICIAL-POPULATION-V1",
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-04-a2t-tier258-official-population-roster/flight-roster-receipt.json",
        "configs/dataset/audio2tool-tier258-official-population-1500.json",
    ),
    (
        "SAEA-A2T-TIER3467-OFFICIAL-POPULATION-V1",
        "docs/checks/speech-aware-evidence-acquisition/"
        "2026-09-04-a2t-tier3467-official-population-roster/flight-roster-receipt.json",
        "configs/dataset/audio2tool-tier3467-official-population-2000.json",
    ),
)

TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)

DEFAULT_OUTPUT = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-05-a2t-org1-domain-grouped-roster"
    / "flight-roster-receipt.json"
)


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


def sha256_lines(lines: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def _load_object(path: Path, label: str) -> Mapping[str, Any]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read {label}: {error}") from error
    if not isinstance(document, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return document


def _resolve_media(data_root: Path, relpath: object, sample_id: str) -> Path:
    if not isinstance(relpath, str) or not relpath or "\\" in relpath:
        raise ValueError(f"media path is malformed for {sample_id}")
    pure = PurePosixPath(relpath)
    if pure.is_absolute() or any(part in ("", ".", "..") for part in pure.parts):
        raise ValueError(f"media path escapes the data root for {sample_id}")
    root = Path(data_root).resolve()
    resolved = (root / pure.as_posix()).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"media path escapes the data root for {sample_id}") from error
    if not resolved.is_file():
        raise ValueError(f"media file is missing for {sample_id}")
    return resolved


def _wav_seconds(path: Path, sample_id: str) -> float:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
    except (OSError, EOFError, wave.Error) as error:
        raise ValueError(f"cannot read WAV header for {sample_id}: {error}") from error
    if frames <= 0 or rate <= 0:
        raise ValueError(f"invalid WAV header for {sample_id}")
    return frames / rate


def _domain_counts(
    items: Sequence[Mapping[str, Any]], data_root: Path
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    """``(overall, per_tier)`` domain counts, read from the released tier manifests.

    Stratum metadata only: the manifests' ``domain`` column, which the three
    parent receipts already record per tier. No gold tool name, expected call
    or query text is read, and nothing here reaches a request.
    """

    import sys

    sys.path.insert(0, str(REPO / "src"))
    from speech_aware_evidence_acquisition.data.lock import (
        asset_dir,
        load_lock,
        umbrella_lock_path,
    )

    lock = load_lock(umbrella_lock_path(REPO))
    public = asset_dir(lock, CARRIER, Path(data_root)) / "public"
    overall: Counter = Counter()
    per_tier: dict[str, Counter] = {}
    by_tier: dict[str, list[Mapping[str, Any]]] = {}
    for item in items:
        by_tier.setdefault(str(item["tier"]), []).append(item)
    for tier, tier_items in by_tier.items():
        manifest = json.loads(
            (public / f"{tier}_data" / f"{tier}.json").read_text(encoding="utf-8")
        )
        domain_by_id = {int(row["id"]): str(row["domain"]) for row in manifest}
        counts: Counter = Counter()
        for item in tier_items:
            domain = domain_by_id[int(item["id"])]
            counts[domain] += 1
            overall[domain] += 1
        per_tier[tier] = counts
    return (
        dict(sorted(overall.items())),
        {tier: dict(sorted(counts.items())) for tier, counts in sorted(per_tier.items())},
    )


def build_roster(*, data_root: Path, verify_media: bool) -> dict[str, object]:
    import sys

    sys.path.insert(0, str(REPO / "src"))
    from speech_aware_evidence_acquisition.data.splits import (
        prefixed,
        split_identity_hash,
    )

    items: list[dict[str, Any]] = []
    sources: list[dict[str, object]] = []
    seen: set[str] = set()
    parent_seconds_total = 0.0
    for run_id, receipt_relpath, fragment_relpath in PARENTS:
        receipt_path = REPO / receipt_relpath
        fragment = _load_object(REPO / fragment_relpath, fragment_relpath)
        measured = sha256_file(receipt_path)
        pinned = str(fragment["a2t_calibration_subset_receipt_sha256"])
        if measured != pinned:
            raise ValueError(
                f"{receipt_relpath} hashes to {measured}, not the {pinned} its own "
                f"dataset fragment {fragment_relpath} pins"
            )
        receipt = _load_object(receipt_path, receipt_relpath)
        if (
            receipt.get("schema") != "saea-a2t-agentloop-flight-roster-receipt-v1"
            or receipt.get("carrier") != CARRIER
            or receipt.get("split_role") != SPLIT_ROLE
        ):
            raise ValueError(f"{receipt_relpath} identity or split role is invalid")
        parent_items = receipt["items"]
        if receipt["count"] != len(parent_items):
            raise ValueError(f"{receipt_relpath} count disagrees with its items")
        # Each parent's own two identity hashes must reproduce from its items.
        parent_keys = sorted(str(item["key"]) for item in parent_items)
        if sha256_lines(parent_keys) != str(receipt["split_identity_hash"]):
            raise ValueError(f"{receipt_relpath} split_identity_hash does not reproduce")
        parent_ids = sorted(str(item["sample_id"]) for item in parent_items)
        if split_identity_hash(prefixed(CARRIER, parent_ids)) != str(
            receipt["flight_split_identity_hash"]
        ):
            raise ValueError(
                f"{receipt_relpath} flight_split_identity_hash does not reproduce"
            )
        for item in parent_items:
            sample_id = str(item["sample_id"])
            if sample_id in seen:
                raise ValueError(
                    f"sample {sample_id!r} appears in more than one parent roster; the "
                    "three official-population draws must be pairwise disjoint"
                )
            seen.add(sample_id)
            items.append(dict(item))
        parent_seconds_total += float(receipt["audio_seconds_total"])
        sources.append(
            {
                "run_id": run_id,
                "receipt": receipt_relpath,
                "receipt_sha256": measured,
                "dataset_fragment": fragment_relpath,
                "split_name": str(receipt["split_name"]),
                "count": int(receipt["count"]),
                "split_identity_hash": str(receipt["split_identity_hash"]),
                "flight_split_identity_hash": str(receipt["flight_split_identity_hash"]),
                "audio_seconds_total": float(receipt["audio_seconds_total"]),
                "tier_counts": dict(receipt["tier_counts"]),
            }
        )

    if verify_media:
        for item in items:
            sample_id = str(item["sample_id"])
            media_path = _resolve_media(data_root, item.get("media_relpath"), sample_id)
            if sha256_file(media_path) != str(item["audio_sha256"]):
                raise ValueError(f"audio bytes drift for {sample_id}")
            header_seconds = _wav_seconds(media_path, sample_id)
            if abs(float(item["audio_seconds"]) - header_seconds) > 1e-6:
                raise ValueError(f"audio duration drift for {sample_id}")

    items.sort(key=lambda item: str(item["sample_id"]))
    tier_counts = Counter(str(item["tier"]) for item in items)
    if sorted(tier_counts) != sorted(TIERS):
        raise ValueError(f"the union covers {sorted(tier_counts)}, expected all eight tiers")
    seconds = [float(item["audio_seconds"]) for item in items]
    total_seconds = round(sum(seconds), 6)
    if not math.isclose(total_seconds, round(parent_seconds_total, 6), abs_tol=1e-6):
        raise ValueError(
            f"union audio seconds {total_seconds} disagree with the parents' sum "
            f"{round(parent_seconds_total, 6)}"
        )
    overall_domains, per_tier_domains = _domain_counts(items, data_root)

    identity = sha256_lines(sorted(str(item["key"]) for item in items))
    flight_identity = split_identity_hash(
        prefixed(CARRIER, [str(item["sample_id"]) for item in items])
    )
    per_tier: dict[str, dict[str, object]] = {}
    for tier in TIERS:
        tier_items = [item for item in items if str(item["tier"]) == tier]
        tier_seconds = [float(item["audio_seconds"]) for item in tier_items]
        per_tier[tier] = {
            "count": len(tier_items),
            "domain_counts": per_tier_domains[tier],
            "audio_seconds_total": round(sum(tier_seconds), 6),
            "audio_seconds_longest_item": round(max(tier_seconds), 6),
            "audio_seconds_shortest_item": round(min(tier_seconds), 6),
        }

    return {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER,
        "split_name": SPLIT_NAME,
        "split_role": SPLIT_ROLE,
        "part": "union",
        "split_identity_hash": identity,
        "split_identity_hash_convention": (
            "sha256 over the LF-joined sorted 'key' values "
            "(audio2tool:<tier>:<id6>, UTF-8, no trailing newline) -- the Audio2Tool "
            "probe-receipt integrity convention"
        ),
        "flight_split_identity_hash": flight_identity,
        "flight_split_identity_hash_convention": (
            "data.splits.split_identity_hash(prefixed('audio2tool', sample_ids)) over "
            "audio2tool/<tier>:<id6> -- the value core.flight.FlightRuntime.preflight "
            "computes at flight time and an exposure row for a FlightRuntime flight of "
            "this roster must carry"
        ),
        "count": len(items),
        "items": items,
        "tier_counts": {tier: tier_counts[tier] for tier in TIERS},
        "domain_counts": overall_domains,
        "strata": "tier and domain",
        "strata_basis": (
            "tier is carried per item. Domain is NOT: it is the domain column of each "
            "tier's released manifest, recorded here as counts exactly as the three "
            "parent receipts record it, and resolved per sample at ANALYSIS time from "
            "the same manifests. Keeping it out of the item rows keeps this receipt's "
            "item shape identical to its parents' and keeps a gold-adjacent label out "
            "of the file the flight entry point reads to build its samples"
        ),
        "audio_seconds_total": total_seconds,
        "audio_seconds_longest_item": round(max(seconds), 6),
        "audio_seconds_shortest_item": round(min(seconds), 6),
        "audio_seconds_basis": (
            "exact wav header value (frames / sample rate) as recorded by the three "
            "parent receipts, re-verified here against the files on disk"
        ),
        "media_roster_sha256": canonical_sha256(
            [
                {
                    "sample_id": item["sample_id"],
                    "media_relpath": item["media_relpath"],
                    "audio_sha256": item["audio_sha256"],
                    "audio_seconds": item["audio_seconds"],
                }
                for item in items
            ]
        ),
        "per_tier": per_tier,
        "selection": {
            "rule": (
                "no new draw: the set-union of the three sealed official-population "
                "rosters, id for id"
            ),
            "algorithm": (
                "merge of the three parent receipts' items after verifying each parent's "
                "committed SHA-256 and both of its identity hashes, then sort by "
                "sample_id; the three id sets are pairwise disjoint by tier"
            ),
            "seed": None,
            "uses_gold_at_runtime": False,
            "uses_test": False,
        },
        "population": {
            "rule": (
                "each parent's own released population under the paper code's loader "
                "rule (the first recording the released loader resolves in every query_* "
                "directory; on tier 7 the FIRST user turn), sampled uniformly without "
                "replacement at 500 per tier with seed 20260803"
            ),
            "official_code_commit": "b9d5383ca30945fbafb965a04bea40117e1e8a82",
            "official_code_receipt": "docs/receipts/environments/audio2tool-official-code.json",
            "evaluator": (
                "audio_benchmark/evaluation/evaluator.py::BenchmarkEvaluator with "
                "max_speakers_per_query 1 evaluates audio_paths[0]"
            ),
            "sources": sources,
        },
        "pairing": (
            "every one of these 4,000 rows carries a sealed official-protocol output "
            "under the compact registry, produced by the three runs named in "
            "population.sources; A2T-ORG-1 is paired against those bytes and re-flies "
            "nothing on the baseline side"
        ),
        "contacts": {
            "audio": (
                "wav bytes re-hashed and wav headers read for duration; no decoding "
                "beyond the container header"
            ),
            "model": "none",
            "network": "none",
            "scorer": "none",
        },
        "media_verified": bool(verify_media),
        "status": "PREPARED_NOT_CONTACT_AUTHORITY",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    parser.add_argument(
        "--no-verify-media",
        dest="verify_media",
        action="store_false",
        help="skip re-hashing every wav (the receipt records that it did)",
    )
    parser.set_defaults(verify_media=True)
    args = parser.parse_args()
    root = args.data_root
    if root is None:
        value = os.environ.get("SPEECHRL_DATA_DIR")
        if not value:
            raise SystemExit("--data-root or SPEECHRL_DATA_DIR is required")
        root = Path(value)

    roster = build_roster(data_root=root, verify_media=args.verify_media)
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
                "count": roster["count"],
                "tier_counts": roster["tier_counts"],
                "domain_counts": roster["domain_counts"],
                "audio_seconds_total": roster["audio_seconds_total"],
                "audio_seconds_longest_item": roster["audio_seconds_longest_item"],
                "split_identity_hash": roster["split_identity_hash"],
                "flight_split_identity_hash": roster["flight_split_identity_hash"],
                "media_roster_sha256": roster["media_roster_sha256"],
                "media_verified": roster["media_verified"],
                "output": str(args.output),
                "output_sha256": (
                    sha256_file(args.output)
                    if args.write
                    else hashlib.sha256(payload.encode("utf-8")).hexdigest()
                ),
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
