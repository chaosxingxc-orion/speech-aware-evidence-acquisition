#!/usr/bin/env python3
"""CLI: freeze the 4-row np8 GEOMETRY-EQUIVALENCE roster.

Owner decision 107 of 2026-09-23 expands the development side to the whole
SLURP ``devel`` split, and that 6,570-row preprocessing pass wants more sidecar
slots than the ``-np 4`` geometry every sealed speech packet was produced with.
More slots change how the server batches, so before the big pass runs the
equivalence is MEASURED: four ALREADY-PROMOTED DEV-2000-ADDED recordings are
re-encoded through the ``-np 8`` sidecar into a scratch cache and compared,
byte for byte, against the packets the resident root already serves
(``scripts/slurp_evo_fold_preprocess.py --roster devel-remainder-np8-equivalence-4``).

This generator freezes WHICH four rows, so the choice is a committed receipt
rather than a flag typed at launch time.

The selection (no randomness, no new exposure)
----------------------------------------------
The candidate pool is the 1,000 ``SLURP-DEV-2000-ADDED-V1`` recordings that the
resident packet root ALREADY serves -- every row is already promoted, so this
preflight opens no new speech identity at all; its four contacts re-encode
audio the frozen core has already seen under
``SAEA-SN-DEV2000-ADDED-PREPROCESS``. The pool is sorted by
``(audio_seconds, sample_id)`` and the rows at the 10th, 35th, 65th and 90th
percentile positions are taken, so the measured per-row wall clock spans the
duration range instead of four near-identical clips. The four are then frozen
through ``core.roster.freeze_roster`` with quota == pool size per stratum (the
take-all trick ``scripts/build_slurp_stage3_construction_roster.py`` uses), so
the canonical schema, hash and disjointness machinery produce the receipt.

MODEL-FREE, ZERO CONTACTS: no model, tokenizer, encoder, embedder, scorer,
network or GPU is reached, no audio sample is decoded, and no utterance text,
gold label, intent or slot annotation is read. The resident packet root is read
for directory names only.

Run in WSL2::

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=<repo>/src \\
      python scripts/build_slurp_np8_equivalence_roster.py --write
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    RosterItem,
    freeze_roster,
    read_roster,
    verify_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402

CARRIER = "slurp"
SEED = 20260923
TOTAL = 4
ROSTER_ID = "SLURP-DEVEL-REMAINDER-NP8-EQUIVALENCE-4-V1"
ROSTER_RELPATH = "docs/receipts/rosters/slurp-devel-remainder-np8-equivalence-4-v1.json"
PARENT_RELPATH = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
RESIDENT_PACKET_ROOT = Path("/home/chao/feat-cache/slurp-q4km-packets-04ccc72a")
REFERENCE_PROMOTION_RECEIPT = "DEV-2000-ADDED-promotion.json"
GENERATOR = "scripts/build_slurp_np8_equivalence_roster.py"
AUTHORITY = (
    "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md owner decision 107 "
    "of 2026-09-23; docs/readiness/2026-09-23-slurp-devel-remainder-preparations-v1.md "
    "section 4"
)
#: Percentile positions of the duration-sorted pool, fixed here so the draw is
#: a committed rule rather than a magic list of four ids.
PERCENTILES: tuple[float, ...] = (0.10, 0.35, 0.65, 0.90)


def sha256_file(relpath: str) -> str:
    return hashlib.sha256((REPO_ROOT / relpath).read_bytes()).hexdigest()


def promoted_packet_ids() -> set[str]:
    """Packet ids the resident root serves, from its promotion receipts.

    Directory names and receipt documents only -- no packet byte is read.
    """

    if not RESIDENT_PACKET_ROOT.is_dir():
        raise SystemExit(f"resident packet root unavailable: {RESIDENT_PACKET_ROOT}")
    ids: set[str] = set()
    for path in sorted(RESIDENT_PACKET_ROOT.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        entries = document.get("packets")
        if isinstance(entries, list):
            ids |= {str(entry.get("packet_id")) for entry in entries}
    return ids


def percentile_selection(
    pool: Sequence[tuple[float, str]], percentiles: Sequence[float]
) -> list[str]:
    """The rows at the given percentile positions of a duration-sorted pool."""

    if len(pool) < len(percentiles):
        raise SystemExit("the candidate pool is smaller than the number of rows wanted")
    chosen: list[str] = []
    for fraction in percentiles:
        index = int(fraction * len(pool))
        index = min(max(index, 0), len(pool) - 1)
        while pool[index][1] in chosen:  # never the same row twice
            index += 1
            if index >= len(pool):
                raise SystemExit("percentile selection ran off the end of the pool")
        chosen.append(pool[index][1])
    return chosen


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the receipt")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    parent = read_roster(REPO_ROOT / PARENT_RELPATH)
    parent_ids = sorted(str(item["sample_id"]) for item in parent["items"])
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    record_by_id = {
        record.sample_id: record
        for record in load_slurp_split(lock, root, "devel")
        if record.sample_id in set(parent_ids)
    }
    missing = [sid for sid in parent_ids if sid not in record_by_id]
    if missing:
        raise SystemExit(f"{len(missing)} parent id(s) absent from the devel loader")

    promoted = promoted_packet_ids()
    eligible = [sid for sid in parent_ids if sid.replace(":", "/") in promoted]
    if len(eligible) != len(parent_ids):
        raise SystemExit(
            f"only {len(eligible)} of {len(parent_ids)} parent rows are promoted; the "
            "preflight must compare against already-served packets"
        )
    pool = sorted(
        (round(float(record_by_id[sid].audio_seconds), 9), sid) for sid in eligible
    )
    chosen = percentile_selection(pool, PERCENTILES)
    if len(set(chosen)) != TOTAL:
        raise SystemExit("the percentile selection did not resolve four distinct rows")

    candidates = [
        RosterItem(
            sample_id=sid,
            stratum=record_by_id[sid].scenario,
            extra={
                "utterance_id": sid.rsplit(":", 1)[0],
                "audio_seconds": round(float(record_by_id[sid].audio_seconds), 9),
                "packet_id": sid.replace(":", "/"),
            },
        )
        for sid in sorted(chosen)
    ]
    quotas = {item.stratum: sum(1 for c in candidates if c.stratum == item.stratum) for item in candidates}
    receipt = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=candidates,
        per_stratum=quotas,
        seed=SEED,
        split_role="dev",
        roster_id=ROSTER_ID,
        roster_role="evaluation",
    )
    if len(receipt["items"]) != TOTAL:
        raise SystemExit("the frozen roster does not carry four rows")

    audio_total = round(
        sum(float(record_by_id[str(item["sample_id"])].audio_seconds) for item in receipt["items"]),
        9,
    )
    receipt.update(
        {
            "authority": AUTHORITY,
            "generator": GENERATOR,
            "status": "FROZEN; MODEL-FREE, ZERO CONTACTS",
            "design": (
                "The four DEV-2000-ADDED recordings the np8 geometry-equivalence preflight "
                "re-encodes. It is not a preparation: the rows are already promoted, the "
                "re-encode writes into a scratch cache, and nothing is promoted from it."
            ),
            "selection_rule": (
                "The 1,000 SLURP-DEV-2000-ADDED-V1 recordings the resident packet root "
                "already serves, sorted by (audio_seconds, sample_id); the rows at the "
                f"{', '.join(f'{int(p * 100)}th' for p in PERCENTILES)} percentile positions "
                "are taken so the measured per-row wall clock spans the duration range. "
                "Frozen through core.roster.freeze_roster with quota == pool size per "
                "stratum, so the canonical machinery produces the receipt and the shuffle "
                "has nothing left to choose between."
            ),
            "parent_roster": {
                "relpath": PARENT_RELPATH,
                "roster_id": parent["roster_id"],
                "count": len(parent_ids),
                "receipt_file_sha256": sha256_file(PARENT_RELPATH),
                "split_identity_hash": parent["split_identity_hash"],
            },
            "reference": {
                "feature_root": str(RESIDENT_PACKET_ROOT),
                "promotion_receipt": REFERENCE_PROMOTION_RECEIPT,
                "geometry_slots": 4,
                "rows_already_promoted": TOTAL,
                "reading": (
                    "Every row is already promoted, so this preflight opens NO new speech "
                    "identity: its four contacts re-encode audio the frozen core already "
                    "saw under SAEA-SN-DEV2000-ADDED-PREPROCESS."
                ),
            },
            "audio_seconds_total": audio_total,
            "item_fields": ["audio_seconds", "packet_id", "sample_id", "stratum", "utterance_id"],
            "stratum_withheld_per_item": False,
            "target_gold_opened_before_receipt": False,
            "offline_guard": {
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
        }
    )
    verify_roster(receipt)

    print(
        json.dumps(
            {
                "roster_id": ROSTER_ID,
                "split_identity_hash": receipt["split_identity_hash"],
                "count": len(receipt["items"]),
                "audio_seconds_total": audio_total,
                "audio_seconds_per_row": [
                    round(float(record_by_id[str(item["sample_id"])].audio_seconds), 6)
                    for item in receipt["items"]
                ],
                "strata_counts": receipt["strata_counts"],
                "offline_guard": receipt["offline_guard"],
            },
            indent=2,
            sort_keys=True,
        )
    )

    if args.write:
        write_roster(receipt, REPO_ROOT / ROSTER_RELPATH)
        print(f"wrote {ROSTER_RELPATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
