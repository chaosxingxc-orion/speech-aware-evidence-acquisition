#!/usr/bin/env python3
"""CLI: reserve `SLURP-DEV-500-B-V1`, the SLURP rung-3 replication roster.

Prerequisite MF-3 of `docs/readiness/2026-09-05-three-dimension-experiment-program.md`
(section 3, "reserved `DEV-500-B`"); claim ladder rung 3, section 6. Exposure row
`SAEA-SN-MF-SLURP-DEV500B-ROSTER-V1`, registered before the first read.

IDENTITY ONLY, ZERO CONTACTS. The SLURP `devel` split is read through the production
loader for utterance id, recording id and scenario; scenario is used to STRATIFY THE
DRAW and is written only as an AGGREGATE allocation, never per item -- the DEV-ladder
discipline (`scripts/build_dev_ladder.py`), which matters more here because this roster
is reserved and unopened. No sentence text, intent, action, entity or transcript is
read. No model, tokenizer, embedder, scorer, network, GPU or audio decode.

The draw. Candidates are every `devel` recording whose UTTERANCE is not in any
committed SLURP-devel exposure receipt; `exclude_groups` keys every recording by its
utterance, so an excluded utterance takes all of its recordings with it and at most one
recording per utterance is ever selected. Quotas reproduce the FULL devel scenario
mixture as closely as the surviving pool allows (`core.roster.mixture_quotas`), because
the equal-per-scenario ladder has already drained the small scenarios. Seed 20260803,
`split_role="dev"`, `roster_role="evaluation"`.

Written to `docs/receipts/rosters/slurp-dev-500-b-v1.json` ONLY: no probe-sample view
exists, so no flight can hydrate it before rung 3.

Usage (WSL2)::

    python scripts/build_slurp_dev500b_roster.py            # print only
    python scripts/build_slurp_dev500b_roster.py --write
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    RosterItem,
    freeze_roster,
    mixture_quotas,
    verify_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.slurp import load_slurp_split  # noqa: E402

ROSTER_ID = "SLURP-DEV-500-B-V1"
CARRIER = "slurp"
SEED = 20260803
TOTAL = 500
RELPATH = "docs/receipts/rosters/slurp-dev-500-b-v1.json"
EXPOSURE_ROW = "SAEA-SN-MF-SLURP-DEV500B-ROSTER-V1"
AUTHORITY = "docs/readiness/2026-09-05-three-dimension-experiment-program.md"

#: Every committed record that has EXPOSED a SLURP `devel` identity. The brief's
#: minimum is DEV-1000 and FINAL60; the other four are added because a reserved
#: rung-3 roster that contained a consumed probe identity would not be reserved.
#: `d1-identity.json` and `slurp-split-identity.json` are deliberately absent: they
#: enumerate the WHOLE split as split identity, not as exposure.
EXPOSURE_SOURCES: tuple[str, ...] = (
    "configs/probes/g0-binding/pkey-flight.json",
    "configs/probes/g0-binding/pslu-flight.json",
    "configs/probes/g0-binding/pslu-s2-flight.json",
    "configs/probes/g0-binding/pslu-sample-devel-n60.json",
    "docs/receipts/probe-samples/DEV-1000.json",
    "docs/receipts/probe-samples/FINAL60.json",
)

DESIGN = (
    "RESERVED rung-3 replication roster for SLURP (claim ladder rung 3). Unopened: no "
    "model, tool or scorer has seen these identities, the receipt lives under "
    "docs/receipts/rosters/ only, and no probe-sample view of it exists, so no flight "
    "can hydrate it before its own registration. Per-item fields are identity only: the "
    "draw stratifies on the gold scenario, but the scenario is published as an AGGREGATE "
    "allocation and withheld per item, exactly as the DEV ladder withholds it."
)

_ID_RE = re.compile(r"slurp:devel:\d{6}:[A-Za-z0-9-]+")


def utterance_of(sample_id: str) -> str:
    return sample_id.rsplit(":", 1)[0]


def exposed_utterances() -> tuple[set[str], list[dict[str, object]]]:
    """Every already-exposed devel UTTERANCE, with a per-source account."""

    union: set[str] = set()
    rows: list[dict[str, object]] = []
    for relpath in EXPOSURE_SOURCES:
        path = REPO_ROOT / relpath
        if not path.is_file():
            raise SystemExit(f"exposure source missing: {relpath}")
        found = {utterance_of(sid) for sid in _ID_RE.findall(path.read_text(encoding="utf-8"))}
        if not found:
            raise SystemExit(f"exposure source names no devel identity: {relpath}")
        rows.append(
            {
                "relpath": relpath,
                "utterances": len(found),
                "new_utterances": len(found - union),
            }
        )
        union |= found
    return union, rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the roster receipt")
    args = parser.parse_args()

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    records = load_slurp_split(lock, data_root(), "devel")
    excluded, exposure_rows = exposed_utterances()

    scenario_by_utterance: dict[str, str] = {}
    recordings_by_utterance: dict[str, list[str]] = defaultdict(list)
    for record in records:
        utterance = utterance_of(record.sample_id)
        scenario_by_utterance[utterance] = record.scenario
        recordings_by_utterance[utterance].append(record.sample_id)

    devel_mixture = Counter(scenario_by_utterance.values())
    eligible = sorted(set(scenario_by_utterance) - excluded)
    capacities = Counter(scenario_by_utterance[utterance] for utterance in eligible)
    quotas = mixture_quotas(TOTAL, devel_mixture, capacities)

    candidates = [
        RosterItem(
            sample_id=record.sample_id,
            stratum=record.scenario,
            extra={
                "id": record.sample_id,
                "key": f"{CARRIER}:{record.sample_id}",
                "utterance_id": utterance_of(record.sample_id),
            },
        )
        for record in records
    ]
    groups = {record.sample_id: utterance_of(record.sample_id) for record in records}
    excluded_ids = [
        sample_id
        for utterance in sorted(excluded)
        for sample_id in recordings_by_utterance.get(utterance, ())
    ]

    receipt = freeze_roster(
        carrier_lock_key=CARRIER,
        candidates=candidates,
        per_stratum=quotas,
        seed=SEED,
        split_role="dev",
        exclude_sample_ids=excluded_ids,
        exclude_groups=groups,
        roster_id=ROSTER_ID,
        roster_role="evaluation",
    )

    drawn = {str(item["sample_id"]) for item in receipt["items"]}
    drawn_utterances = {utterance_of(sample_id) for sample_id in drawn}
    scenario_allocation = dict(sorted(Counter(str(item["stratum"]) for item in receipt["items"]).items()))
    # Identity only per item: the gold scenario stratified the draw and is published as
    # the aggregate allocation above, never beside a sample id.
    receipt["items"] = [
        {key: value for key, value in item.items() if key != "stratum"}
        for item in receipt["items"]
    ]

    dev1000 = {
        utterance_of(sid)
        for sid in _ID_RE.findall(
            (REPO_ROOT / "docs/receipts/probe-samples/DEV-1000.json").read_text(encoding="utf-8")
        )
    }
    final60 = {
        utterance_of(sid)
        for sid in _ID_RE.findall(
            (REPO_ROOT / "docs/receipts/probe-samples/FINAL60.json").read_text(encoding="utf-8")
        )
    }
    receipt.update(
        {
            "authority": AUTHORITY,
            "generator": "scripts/build_slurp_dev500b_roster.py",
            "exposure_row": EXPOSURE_ROW,
            "status": "RESERVED_AND_UNOPENED",
            "design": DESIGN,
            "offline_guard": {
                "outbound_connection_attempts": attempts.count,
                "attempted_targets": list(attempts.targets),
            },
            "item_fields": ["id", "key", "sample_id", "utterance_id"],
            "stratum_withheld_per_item": True,
            "scenario_allocation": scenario_allocation,
            "allocation_rule": (
                "core.roster.mixture_quotas: largest-remainder apportionment of 500 in "
                "proportion to the FULL devel scenario mixture, capped by each scenario's "
                "surviving candidate count and water-filled when a scenario's capacity is "
                "below its fair share. Not the DEV ladder's equal-per-scenario rule, which "
                "the ladder has already made infeasible on the remainder."
            ),
            "sample_selection_rule": (
                "one recording per utterance: exclude_groups keys every recording by its "
                "utterance, so at most one recording per utterance is ever selected and an "
                "excluded utterance takes all of its recordings with it"
            ),
            "candidate_pool": {
                "devel_recordings": len(records),
                "devel_utterances": len(scenario_by_utterance),
                "excluded_utterances": len(excluded),
                "excluded_recordings": len(excluded_ids),
                "eligible_utterances": len(eligible),
                "eligible_utterances_by_scenario": dict(sorted(capacities.items())),
                "devel_mixture_by_scenario": dict(sorted(devel_mixture.items())),
                "exposure_sources": exposure_rows,
            },
            "zero_overlap_proof": {
                "drawn_utterances": len(drawn_utterances),
                "overlap_with_dev1000_utterances": len(drawn_utterances & dev1000),
                "overlap_with_final60_utterances": len(drawn_utterances & final60),
                "overlap_with_every_exposed_utterance": len(drawn_utterances & excluded),
                "recordings_per_drawn_utterance_max": max(
                    Counter(utterance_of(sid) for sid in drawn).values()
                ),
            },
            "target_gold_opened_before_receipt": False,
        }
    )
    proof = receipt["zero_overlap_proof"]
    if (
        proof["overlap_with_dev1000_utterances"]
        or proof["overlap_with_final60_utterances"]
        or proof["overlap_with_every_exposed_utterance"]
        or proof["recordings_per_drawn_utterance_max"] != 1
        or proof["drawn_utterances"] != TOTAL
    ):
        raise SystemExit(f"DEV-500-B legality proof failed: {proof}")
    verify_roster(receipt)

    print(json.dumps({key: receipt[key] for key in ("roster_id", "split_identity_hash")}, indent=1))
    print(json.dumps(receipt["candidate_pool"], indent=1))
    print(json.dumps(scenario_allocation, indent=1))
    print(json.dumps(proof, indent=1))
    if args.write:
        write_roster(receipt, REPO_ROOT / RELPATH)
        print(f"wrote {RELPATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
