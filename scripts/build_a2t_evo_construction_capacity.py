#!/usr/bin/env python3
"""CLI: the EVO-A1 construction-capacity census (MODEL-FREE, zero contacts).

Exposure row ``SAEA-A2T-MF-EVO-CONSTRUCTION-CAPACITY-V1``, registered before
this runs; arithmetic in ``analysis.a2t_evo_capacity``; authority
``docs/readiness/2026-09-05-three-dimension-experiment-program.md`` sections 4c
and 5, target list ``configs/knowledge/a2t-kc-a1/targets-v1.json`` re-verified
here against the MF-1 receipt it cites.

IDENTIFIERS AND GOLD TOOL NAMES ONLY: each construction unit's tier,
``query_idx``, gold primary ``tool_name`` and wav duration. No query text, no
argument value, no evaluation identity, no output, no score.

Usage: ``--write`` lands the receipt; without it the census only prints.
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

from speech_aware_evidence_acquisition.analysis.a2t_evo_capacity import (  # noqa: E402
    FOLD_MAX_AUDIO_SECONDS,
    audio_seconds_by_sample_id,
    capacity_document,
    capacity_verdict,
    read_json,
    target_capacity,
    tool_capacity,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import write_json_artifact  # noqa: E402
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)

AUTHORITY = "docs/readiness/2026-09-05-three-dimension-experiment-program.md"
EXPOSURE_ROW_ID = "SAEA-A2T-MF-EVO-CONSTRUCTION-CAPACITY-V1"
SEED = 20260906
CHECKS = REPO_ROOT / "docs/checks/speech-aware-evidence-acquisition"
AUDIT_DIR = CHECKS / "2026-09-05-a2t-query-cue-audit"
TARGET_SPEC = REPO_ROOT / "configs/knowledge/a2t-kc-a1/targets-v1.json"
OUT_PATH = CHECKS / "2026-09-06-a2t-evo-construction-capacity" / "capacity.json"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()
    rows, inventory = a2t_pool_rows(lock, root)
    construction = propose_partition(rows, exposed_sample_ids(REPO_ROOT)).construction
    seconds = audio_seconds_by_sample_id(lock, root)
    pool = tuple(
        row
        for row in construction
        if seconds.get(row.sample_ids[0], 0.0) <= FOLD_MAX_AUDIO_SECONDS
    )

    summary = read_json(AUDIT_DIR / "summary.json")
    targets = summary["primary_population"]["targets"]["targets"]  # type: ignore[index]
    spec = read_json(TARGET_SPEC)["targets"]  # type: ignore[index]
    if {t["target_id"]: sorted(t["tools"]) for t in spec} != {
        t["target_id"]: sorted(t["tools"]) for t in targets
    }:
        raise SystemExit("the KC-A1 target spec and the MF-1 receipt name different tools")
    pair_mass = {
        row["pair_id"]: row["sealed_miss_mass"]
        for row in read_json(AUDIT_DIR / "per-pair-table.json")["primary"]  # type: ignore[index]
    }
    mass_total = summary["primary_population"]["targets"]["strict_mass_total"]  # type: ignore[index]
    capacity = tool_capacity(
        pool, [tool for target in targets for tool in target["tools"]], seed=args.seed
    )
    per_target = target_capacity(targets, capacity, pair_mass)
    verdict = capacity_verdict(per_target, capacity, target_strict_mass_total=mass_total)

    document = capacity_document(
        seed=args.seed,
        generator="scripts/build_a2t_evo_construction_capacity.py",
        exposure_row=EXPOSURE_ROW_ID,
        authority=AUTHORITY,
        population={
            "source": "the V3 exposure-free construction pool, runtime wav at most 60 s",
            "carrier_units_total": inventory["usable_units"],
            "construction_units": len(construction),
            "construction_blocks": len({row.query_idx for row in construction}),
            "fold_eligible_units": len(pool),
            "fold_eligible_blocks": len({row.query_idx for row in pool}),
            "units_over_audio_cap": len(construction) - len(pool),
            "audio_seconds_cap": FOLD_MAX_AUDIO_SECONDS,
            "partition_receipt": "docs/receipts/knowledge/a2t-partition-proposal.json",
        },
        mf1_receipt={
            "relpath": f"{AUDIT_DIR.relative_to(REPO_ROOT).as_posix()}/summary.json",
            "sha256": hashlib.sha256((AUDIT_DIR / "summary.json").read_bytes()).hexdigest(),
            "target_strict_mass_total": mass_total,
            "sealed_miss_total": summary["primary_population"]["sealed_miss_total"],
        },
        capacity=capacity,
        per_target=per_target,
        verdict=verdict,
        offline_guard={
            "exposure_row": EXPOSURE_ROW_ID,
            "outbound_connection_attempts": attempts.count,
            "attempted_targets": list(attempts.targets),
        },
    )

    for tool in sorted(capacity):
        row = capacity[tool]
        print(
            f"{tool:24s} units={row['units']:3d} blocks={row['blocks']:3d} "
            f"rule={row['rule_quota']:2d} realized={row['realized_quota']:2d} "
            f"{'SURVIVES' if row['survives'] else 'DROPPED'}"
        )
    print(json.dumps(verdict, indent=2, sort_keys=True))
    if not args.write:
        print("(print only; pass --write to land the receipt)")
        return 0
    write_json_artifact(OUT_PATH, document)
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    print(f"wrote {OUT_PATH.relative_to(REPO_ROOT)} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
