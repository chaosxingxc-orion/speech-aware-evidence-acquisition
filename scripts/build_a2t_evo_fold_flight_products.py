#!/usr/bin/env python3
"""CLI: make the two EVO-A1 folds FLYABLE (MODEL-FREE, identity and media only).

Exposure row ``SAEA-SN-MF-A2T-EVO-FOLD-SUPPLEMENTS-V2``. A frozen construction
roster carries identity; a speech-bearing cell needs three more model-free
artifacts per fold, and this script writes the first two: a **probe-sample
view** under ``docs/receipts/probe-samples/`` (so ``data.audio2tool`` can
resolve the ids at all and the official scorer can score them) and a
**flight-roster receipt** carrying per-row MEASURED media facts, of the same
``saea-a2t-agentloop-flight-roster-receipt-v1`` schema every other Audio2Tool
direct cell flies through. The third, the ``d1-a2t-evo-fold-{a,b}-v2`` media
supplement, is built by the existing
``scripts/build_a2t_semantic_agentloop_d1_supplement.py --roster`` against the
flight-roster receipt this script writes.

ZERO CONTACTS: wav bytes are hashed and wav headers read for duration and
sample rate; no decoding, no frozen core, tokenizer, embedder, retriever,
scorer, network or GPU. No query text, expected call, annotation, prior output
or score is opened, and the per-row gold tool the construction receipt records
is deliberately NOT copied into the file the flight entry point reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import (  # noqa: E402
    domains_by_sample_id,
    measured_media_facts,
    read_json,
)
from speech_aware_evidence_acquisition.analysis.a2t_evo_rosters import (  # noqa: E402
    covered_by_probe_receipts,
    flight_roster_document,
    probe_sample_document,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)

EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-EVO-FOLD-SUPPLEMENTS-V2"
ROSTER_ROW_ID = "SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V2"
AUTHORITY = (
    "docs/readiness/2026-09-06-a2t-evo-a1-description-evolution-v1-preregistration.md"
)
CHECK_DIR = REPO_ROOT / (
    "docs/checks/speech-aware-evidence-acquisition/2026-09-06-a2t-evo-fold-flight-products"
)
PROBES = REPO_ROOT / "docs/receipts/probe-samples"
FOLDS = {
    "a": ("docs/receipts/rosters/a2t-evo-fold-a-v2.json", "A2T-EVO-FOLD-A-V2"),
    "b": ("docs/receipts/rosters/a2t-evo-fold-b-v2.json", "A2T-EVO-FOLD-B-V2"),
}
DESIGN = (
    "Additive identity receipt for {split}: the sample ids of that frozen "
    "construction roster that no committed audio2tool probe-sample receipt covers "
    "yet. Identifiers only -- no gold, expected call, task text, media path, "
    "annotation, output or score. It grants no contact authority."
)


def _write(path: Path, document: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fold", choices=sorted(FOLDS), action="append")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    for fold in args.fold or sorted(FOLDS):
        relpath, split_name = FOLDS[fold]
        receipt = read_json(REPO_ROOT / relpath)
        ids = [str(item["sample_id"]) for item in receipt["items"]]  # type: ignore[index,union-attr]
        started = time.monotonic()
        media = measured_media_facts(lock, root, ids)
        elapsed = time.monotonic() - started
        covered = covered_by_probe_receipts(PROBES, ids)
        probe_stem = f"a2t-evo-fold-{fold}-v2"
        shared = {
            "authority": AUTHORITY,
            "generator": "scripts/build_a2t_evo_fold_flight_products.py",
            "exposure_row": EXPOSURE_ROW_ID,
            "source_roster": relpath,
            "source_roster_sha256": hashlib.sha256(
                (REPO_ROOT / relpath).read_bytes()
            ).hexdigest(),
            "source_roster_count": len(ids),
            "source_roster_exposure_row": ROSTER_ROW_ID,
            "offline_guard": {
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
        }
        flight = flight_roster_document(
            receipt,
            media,
            split_name=split_name,
            domains=domains_by_sample_id(lock, root, ids),
            shared=shared,
        )
        probe = probe_sample_document(
            receipt,
            probe=probe_stem,
            already_covered=covered,
            shared={**shared, "design": DESIGN.format(split=split_name)},
        )
        print(
            f"{split_name}: {flight['count']} rows, {flight['audio_seconds_total']} s, "
            f"longest {flight['audio_seconds_longest_item']} s, {probe['n_items']} new "
            f"probe ids ({sum(map(len, covered.values()))} already covered), media "
            f"measured in {elapsed:.1f} s"
        )
        if not args.write:
            continue
        flight_path = CHECK_DIR / f"flight-roster-receipt-fold-{fold}.json"
        probe_path = PROBES / f"{probe_stem}.json"
        for path in (flight_path, probe_path):
            if path.exists():
                raise SystemExit(f"refusing to overwrite an existing receipt: {path}")
        for path, document in ((flight_path, flight), (probe_path, probe)):
            digest = _write(path, document)
            print(f"  wrote {path.relative_to(REPO_ROOT)} sha256={digest}")
    print(f"offline guard: {attempts.count} outbound connection attempts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
