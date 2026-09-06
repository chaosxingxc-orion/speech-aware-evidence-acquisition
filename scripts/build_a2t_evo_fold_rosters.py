#!/usr/bin/env python3
"""CLI: freeze the three EVO-A1 loop rosters (MODEL-FREE, identity only).

``--version v1`` is the original draw, exposure row
``SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V1``. ``--version v2`` (the default) is the
owner's 2026-09-06 "RELAXED with sentinels" re-freeze under
``SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V2``: the four tools the census dropped, plus
``getLightState`` which block contention dropped, keep a small exemplar reserve
and contribute every remaining block to the folds as HARM SENTINELS. A tool the
census kept is drawn exactly as it was in V1.

The cut and its proof live in ``analysis.a2t_evo_rosters``, the quotas in
``analysis.a2t_evo_capacity``. Authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` section 5,
census ``docs/checks/speech-aware-evidence-acquisition/
2026-09-06-a2t-evo-construction-capacity/capacity.json``.

ZERO CONTACTS: no frozen core, tokenizer, embedder, retriever, scorer, network,
audio decode or gold read. Identifiers, gold tool names and wav durations only.
``--write`` lands the receipts; without it the draw only prints.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import (  # noqa: E402
    FOLD_MAX_AUDIO_SECONDS,
    audio_seconds_by_sample_id,
    joint_capacity,
    read_json,
)
from speech_aware_evidence_acquisition.analysis.a2t_evo_rosters import (  # noqa: E402
    BACKGROUND_ROWS,
    disjointness_proof,
    freeze_evo_rosters,
    roster_documents,
    sentinel_tools,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import write_roster  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_identity_report,
    exposed_sample_ids,
    propose_partition,
)

AUTHORITY = "docs/readiness/2026-09-05-three-dimension-experiment-program.md"
EXPOSURE_ROWS = {
    "v1": "SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V1",
    "v2": "SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V2",
}
OWNER_DECISION = (
    "owner 2026-09-06, RELAXED with sentinels: a MF-1 target survives when the GOLD side "
    "of its dominant miss direction has construction capacity, and a thin tool is kept as "
    "a harm sentinel rather than dropped. Supersedes "
    "SAEA-SN-MF-A2T-EVO-FOLD-ROSTERS-V1, whose receipts stay as history."
)
CAPACITY_ROW_ID = "SAEA-A2T-MF-EVO-CONSTRUCTION-CAPACITY-V1"
CAPACITY_RECEIPT = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-06-a2t-evo-construction-capacity/capacity.json"
)
SEED = 20260906
ROSTERS = REPO_ROOT / "docs/receipts/rosters"
TARGET_SPEC = REPO_ROOT / "configs/knowledge/a2t-kc-a1/targets-v1.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--background", type=int, default=BACKGROUND_ROWS)
    parser.add_argument("--version", choices=sorted(EXPOSURE_ROWS), default="v2")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    all_rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO_ROOT)
    exposure = exposed_identity_report(REPO_ROOT)
    construction = propose_partition(all_rows, exposed).construction
    seconds = audio_seconds_by_sample_id(lock, root)
    cap = FOLD_MAX_AUDIO_SECONDS
    pool = tuple(row for row in construction if seconds.get(row.sample_ids[0], 0.0) <= cap)
    tools = sorted({tool for t in read_json(TARGET_SPEC)["targets"] for tool in t["tools"]})
    capacity, _blocks = joint_capacity(
        pool, tools, seed=args.seed, sentinels=args.version != "v1"
    )
    cut = freeze_evo_rosters(
        pool,
        tools,
        capacity,
        seed=args.seed,
        exposed=exposed,
        background_rows=args.background,
        version=args.version,
    )

    block_of = {sid: row.query_idx for row in all_rows for sid in row.sample_ids}
    exposure_blocks = {block_of[sid] for sid in exposed if sid in block_of}
    proof = disjointness_proof(cut, exposure_blocks=exposure_blocks, exposed=exposed)
    if any(proof.values()):
        raise SystemExit(f"refusing to write: the rosters are not disjoint: {proof}")

    documents = roster_documents(
        cut,
        capacity,
        proof=proof,
        exposure=exposure,
        exposure_blocks=len(exposure_blocks),
        version=args.version,
        shared={
            "authority": AUTHORITY,
            "generator": "scripts/build_a2t_evo_fold_rosters.py",
            "exposure_row": EXPOSURE_ROWS[args.version],
            "supersedes": None if args.version == "v1" else EXPOSURE_ROWS["v1"],
            "owner_decision": None if args.version == "v1" else OWNER_DECISION,
            "capacity_row": CAPACITY_ROW_ID,
            "capacity_receipt": CAPACITY_RECEIPT,
            "pool": {
                "source": "the V3 exposure-free construction pool, runtime wav at most 60 s",
                "carrier_units_total": inventory["usable_units"],
                "construction_units": len(construction),
                **cut["pool"],
            },
            "offline_guard": {
                "exposure_row": EXPOSURE_ROWS[args.version],
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
        },
    )
    for _stem, document in documents:
        print(
            f"{document['roster_id']}: {len(document['items'])} items, "
            f"{document['block_disjointness']['distinct_blocks']} blocks, "
            f"identity {document['split_identity_hash']}"
        )
        print(f"  strata: {document['strata_counts']}")
    print(f"sentinel tools: {list(sentinel_tools(capacity))}")
    print(f"disjointness proof: {proof}")
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
