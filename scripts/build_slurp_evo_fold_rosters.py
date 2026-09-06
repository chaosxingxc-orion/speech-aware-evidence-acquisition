#!/usr/bin/env python3
"""CLI: freeze the three EVO-S1 loop rosters (MODEL-FREE, identity only).

Exposure row ``SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V1``, registered before the
first draw; the cut, its proof and its receipt blocks live in
``analysis.slurp_evo_rosters``. Authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` sections 4c
and 5. ZERO CONTACTS: flac HEADERS only, so a duration reaches the receipt.
``--write`` lands them.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.analysis.slurp_evo_rosters import (  # noqa: E402
    EXEMPLAR_QUOTA,
    FOLD_QUOTA,
    SEED,
    assert_clean_cut,
    disjointness_proof,
    freeze_evo_rosters,
    pool_block,
    roster_documents,
    summary_lines,
    touched_train_utterances,
    utterance_of,
)
from speech_aware_evidence_acquisition.core.roster import write_roster  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402

AUTHORITY = "docs/readiness/2026-09-05-three-dimension-experiment-program.md"
EXPOSURE_ROW_ID = "SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-V1"
CAPACITY_ROW_ID = "SAEA-SLURP-MF-EVO-CONSTRUCTION-CAPACITY-V1"
CAPACITY_DIR = "docs/checks/speech-aware-evidence-acquisition"
CAPACITY_RECEIPT = f"{CAPACITY_DIR}/2026-09-06-slurp-evo-construction-capacity/capacity.json"
SPLIT_IDENTITY = REPO_ROOT / "docs/receipts/knowledge/slurp-split-identity.json"
ROSTERS = REPO_ROOT / "docs/receipts/rosters"


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--fold-quota", type=int, default=FOLD_QUOTA)
    parser.add_argument("--exemplar-quota", type=int, default=EXEMPLAR_QUOTA)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    records = load_slurp_split(lock, data_root(), "train")
    identity = _read_json(SPLIT_IDENTITY)
    touched, touched_rows = touched_train_utterances(REPO_ROOT)
    excluded_ids = [
        record.sample_id
        for record in records
        if utterance_of(record.sample_id) in touched
    ]

    cut = freeze_evo_rosters(
        records,
        seed=args.seed,
        fold_quota=args.fold_quota,
        exemplar_quota=args.exemplar_quota,
        exclude_sample_ids=excluded_ids,
    )
    proof = disjointness_proof(
        cut,
        devel_ids=identity["splits"]["devel"]["ids"],
        test_ids=identity["splits"]["test"]["ids"],
        contacted_train_utterances=sorted(touched),
    )
    assert_clean_cut(proof)

    documents = roster_documents(
        cut,
        proof=proof,
        shared={
            "authority": AUTHORITY,
            "generator": "scripts/build_slurp_evo_fold_rosters.py",
            "exposure_row": EXPOSURE_ROW_ID,
            "capacity_row": CAPACITY_ROW_ID,
            "capacity_receipt": CAPACITY_RECEIPT,
            "pool": pool_block(
                records,
                touched=touched,
                excluded_recordings=len(excluded_ids),
                touched_rows=touched_rows,
            ),
            "split_identity_receipt": {
                "relpath": "docs/receipts/knowledge/slurp-split-identity.json",
                "devel_identity_hash": identity["splits"]["devel"]["identity_hash"],
                "devel_ids": identity["splits"]["devel"]["count"],
                "test_identity_hash": identity["splits"]["test"]["identity_hash"],
                "test_ids": identity["splits"]["test"]["count"],
            },
            "reserved_roster_note": (
                "SLURP-DEV-500-B-V1 is not opened here. Its own receipt declares "
                "carrier slurp and split_role 'dev', so every one of its identities "
                "is a member of the devel enumeration above, which these rosters are "
                "proved disjoint from id by id."
            ),
            "offline_guard": {
                "exposure_row": EXPOSURE_ROW_ID,
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
        },
    )
    for line in summary_lines(documents):
        print(line)
    print(f"disjointness proof: {json.dumps(proof, sort_keys=True)}")
    print(f"offline guard: {attempts.count} outbound connection attempts")
    if not args.write:
        print("(print only; pass --write to land the receipts)")
        return 0

    for stem, document in documents:
        path = ROSTERS / f"{stem}.json"
        if path.exists():
            raise SystemExit(f"refusing to overwrite an existing receipt: {path}")
        write_roster(document, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"wrote {path.relative_to(REPO_ROOT)} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
