#!/usr/bin/env python3
"""CLI: freeze the three EVO-S1 loop rosters (MODEL-FREE, identity only).

Exposure row ``SAEA-SN-MF-SLURP-EVO-FOLD-ROSTERS-<version>``, registered before
the draw it covers; the cut, its proof and every receipt block live in
``analysis.slurp_evo_rosters``. Authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` sections 4c
and 5. ZERO CONTACTS: flac HEADERS only, so a duration reaches the receipt.
``--write`` lands them.

``--version V2 --fold-quota 60 --supersedes V1 --decision <ruling>`` is the
2026-09-06 coordinator re-draw (remedy (b) of preregistration section 16 open
point 1). A non-default version MUST name the version it supersedes, so a V2
receipt records the V1 receipts it replaces by relpath and file SHA-256 rather
than silently orphaning them; the first draw must not.
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
    DEFAULT_VERSION,
    EXEMPLAR_QUOTA,
    FOLD_QUOTA,
    SEED,
    assert_clean_cut,
    disjointness_proof,
    exposure_row_id,
    freeze_evo_rosters,
    roster_documents,
    shared_block,
    summary_lines,
    supersedes_block,
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

SPLIT_IDENTITY = REPO_ROOT / "docs/receipts/knowledge/slurp-split-identity.json"
ROSTERS = REPO_ROOT / "docs/receipts/rosters"


def _parse(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--fold-quota", type=int, default=FOLD_QUOTA)
    parser.add_argument("--exemplar-quota", type=int, default=EXEMPLAR_QUOTA)
    parser.add_argument("--version", default=DEFAULT_VERSION)
    parser.add_argument("--supersedes", default=None)
    parser.add_argument("--decision", default="")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    if (args.version != DEFAULT_VERSION) != bool(args.supersedes):
        raise SystemExit(
            "a re-draw must name the version it supersedes (--supersedes V1); "
            "the first draw must not"
        )
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse(argv)
    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    records = load_slurp_split(lock, data_root(), "train")
    identity = json.loads(SPLIT_IDENTITY.read_text(encoding="utf-8"))
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
        version=args.version,
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
        version=args.version,
        shared=shared_block(
            records,
            touched=touched,
            touched_rows=touched_rows,
            excluded_recordings=len(excluded_ids),
            split_identity=identity,
            version=args.version,
            offline_guard={
                "exposure_row": exposure_row_id(args.version),
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
            supersedes=(
                supersedes_block(ROSTERS, args.supersedes, args.decision)
                if args.supersedes
                else None
            ),
        ),
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
