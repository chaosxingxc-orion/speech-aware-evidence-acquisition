#!/usr/bin/env python3
"""CLI: freeze the Audio2Tool CONSTRUCTION roster and reserve A2T-FRESH-800.

Authority: ``docs/readiness/2026-09-05-three-dimension-experiment-program.md``
(enabler E2, prerequisite MF-2). Exposure row
``SAEA-SN-MF-A2T-CONSTRUCTION-ROSTER-V1``, registered BEFORE anything is
written.

ZERO CONTACTS OF ANY KIND: no frozen core, no tokenizer, no embedder, no
network, no audio decoded, no gold read. The offline guard is armed before
the first input is opened and its attempt count is written into every
receipt.

Two rosters, drawn in one deterministic pass so they can be proven disjoint:

* ``A2T-FRESH-800-V1`` -- the RESERVED rung-3 evaluation roster. Drawn first,
  from every exposure-free unit whose gold primary tool clears
  ``EVAL_TOOL_MIN_POOL_ROWS`` in the exposure-free pool (the same evaluation
  candidacy rule ``propose_partition`` applies), one wav per unit by the
  release's first-successful-speaker rule. Written under
  ``docs/receipts/rosters/`` ONLY: no probe-sample view exists, so no flight
  can hydrate it, which is exactly the intended state until rung 3.
* ``A2T-CONSTRUCTION-800-V1`` -- the construction roster the evolution loop
  draws its folds from. Drawn second, from the block partition's construction
  pool minus every block A2T-FRESH-800 just took, so the two rosters are
  block-disjoint by construction. Written under ``docs/receipts/rosters/``
  AND, through :func:`core.roster.as_probe_sample_receipt`, under
  ``docs/receipts/probe-samples/`` so ``data.audio2tool`` can load it.

Usage::

    python scripts/build_a2t_construction_roster.py            # print only
    python scripts/build_a2t_construction_roster.py --write
    python scripts/build_a2t_construction_roster.py --write \\
        --per-tier 100 --seed 20260803
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import sys
from pathlib import Path
from typing import Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.roster import (  # noqa: E402
    RosterItem,
    as_probe_sample_receipt,
    canonical_receipt_bytes,
    freeze_roster,
    write_roster,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.e0.artifacts import (  # noqa: E402
    write_json_artifact,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    EVAL_TOOL_MIN_POOL_ROWS,
    A2tKbRow,
    a2t_pool_rows,
    exposed_identity_report,
    exposed_sample_ids,
    propose_partition,
)

AUTHORITY = "docs/readiness/2026-09-05-three-dimension-experiment-program.md"
EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-CONSTRUCTION-ROSTER-V1"
CONSTRUCTION_ROSTER_ID = "A2T-CONSTRUCTION-800-V1"
FRESH_ROSTER_ID = "A2T-FRESH-800-V1"
ROSTERS_DIR = REPO_ROOT / "docs" / "receipts" / "rosters"
PROBE_SAMPLES_DIR = REPO_ROOT / "docs" / "receipts" / "probe-samples"
CONSTRUCTION_RELPATH = "docs/receipts/rosters/a2t-construction-800-v1.json"
FRESH_RELPATH = "docs/receipts/rosters/a2t-fresh-800-v1.json"
PROBE_VIEW_RELPATH = "docs/receipts/probe-samples/a2t-construction-800-v1.json"
DEFAULT_PER_TIER = 100
DEFAULT_SEED = 20260803

GROUP_KEY_RATIONALE = (
    "one unit per (tier, block): cross-tier siblings inside ONE roster are allowed, "
    "exactly as the released evaluation populations allow them (the 4,000-row ORG-1 "
    "union spans 2,059 blocks), because the property that matters is disjointness "
    "BETWEEN a construction roster and every evaluation identity. Demanding one unit "
    "per block ACROSS a whole roster is also infeasible on the post-union free pool: "
    "measured, tier7_multiturn offers 70 such candidates for a quota of 100."
)

CONSTRUCTION_DESIGN = (
    "CONSTRUCTION-role roster (owner decision 2026-09-05): these identities may be "
    "read WITH their gold labels -- the same legality class as TRAIN gold entering a "
    "knowledge-base build -- and gold may reach the frozen core only through the "
    "text-only 'construction-proposer-text' D2 arm, whose outputs are artifacts "
    "(prompt text), never answers. split_role stays 'discovery' (the TRAIN90 "
    "precedent); roster_role is 'construction', which is why the Audio2Tool exposure "
    "union excludes this roster by design. Block-disjoint from every committed "
    "evaluation identity and from the reserved A2T-FRESH-800-V1."
)
FRESH_DESIGN = (
    "RESERVED rung-3 evaluation roster. Unopened: no model, tool or scorer has seen "
    "these identities, and no probe-sample view of this receipt exists, so no flight "
    "can hydrate it. Registering it here makes it source (c) of the Audio2Tool "
    "exposure union, so every knowledge base built from now on reserves its blocks "
    "automatically. The knowledge receipts committed alongside this roster were built "
    "BEFORE it existed, so 404 of its 610 blocks (1,744 units) still sit inside that "
    "snapshot's construction pool; rebuild them "
    "(scripts/build_a2t_knowledge_snapshot.py, model-free, seconds) before any rung-3 "
    "read."
)


def _group_key(row: A2tKbRow) -> str:
    """The within-roster uniqueness key: TIER-scoped, see
    :data:`GROUP_KEY_RATIONALE`."""

    return f"{row.tier}:block:{row.query_idx}"


def _candidate_items(rows: Iterable[A2tKbRow]) -> list[RosterItem]:
    """One :class:`RosterItem` per unit, the wav chosen by the release's own
    first-successful-speaker rule -- which, on these manifests, is the unit's
    LOWEST manifest id (``a2t_pool_rows`` sorts a unit's members by id). The
    official-population roster builders verified that equivalence against the
    released loader's own directory walk: 2,145 agreements, zero
    disagreements and one documented exception on tier 1."""

    return [
        RosterItem(
            sample_id=row.sample_ids[0],
            stratum=row.tier,
            extra={
                "id": row.item_ids[0],
                "key": f"{AUDIO2TOOL_LOCK_KEY}:{row.sample_ids[0]}",
                "query_idx": row.query_idx,
                "tier": row.tier,
            },
        )
        for row in sorted(rows, key=lambda row: row.unit_id)
    ]


def _sample_ids(receipt: dict[str, object]) -> set[str]:
    return {str(item["sample_id"]) for item in receipt["items"]}  # type: ignore[index]


def _blocks(receipt: dict[str, object]) -> set[int]:
    return {int(item["query_idx"]) for item in receipt["items"]}  # type: ignore[index]


def _tier_counts(rows: Iterable[A2tKbRow]) -> dict[str, int]:
    return dict(sorted(collections.Counter(row.tier for row in rows).items()))


def _enrich(receipt: dict[str, object], **blocks: object) -> dict[str, object]:
    enriched = dict(receipt)
    enriched.update(
        {
            "authority": AUTHORITY,
            "generator": "scripts/build_a2t_construction_roster.py",
            "exposure_row": EXPOSURE_ROW_ID,
            "sample_selection_rule": (
                "one wav per (tier, query_idx) unit: the unit's lowest manifest id, "
                "which is the release's own first-successful-speaker pick"
            ),
            "target_gold_opened_before_receipt": False,
        }
    )
    enriched.update(blocks)
    return enriched


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-tier", type=int, default=DEFAULT_PER_TIER)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--write", action="store_true", help="write the receipts (default: print only)"
    )
    args = parser.parse_args(argv)

    attempts = arm_offline_guard()
    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    rows, inventory = a2t_pool_rows(lock, data_root())
    exposure = exposed_identity_report(REPO_ROOT)
    exposed = exposed_sample_ids(REPO_ROOT)
    partition = propose_partition(rows, exposed)

    exposed_blocks = frozenset(partition.reserved_exposed_blocks)
    free_rows = tuple(row for row in rows if row.query_idx not in exposed_blocks)
    tool_counts = collections.Counter(row.tool_name for row in free_rows)
    fresh_candidates = tuple(
        row for row in free_rows if tool_counts[row.tool_name] >= EVAL_TOOL_MIN_POOL_ROWS
    )
    groups = {sid: _group_key(row) for row in rows for sid in row.sample_ids}

    fresh = freeze_roster(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        candidates=_candidate_items(fresh_candidates),
        per_stratum=args.per_tier,
        seed=args.seed,
        split_role="discovery",
        exclude_sample_ids=exposed,
        exclude_groups=groups,
        roster_id=FRESH_ROSTER_ID,
        roster_role="evaluation",
    )
    fresh_blocks = _blocks(fresh)

    construction_candidates = tuple(
        row for row in partition.construction if row.query_idx not in fresh_blocks
    )
    construction = freeze_roster(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        candidates=_candidate_items(construction_candidates),
        per_stratum=args.per_tier,
        seed=args.seed,
        split_role="discovery",
        exclude_sample_ids=set(exposed) | _sample_ids(fresh),
        exclude_groups=groups,
        roster_id=CONSTRUCTION_ROSTER_ID,
        roster_role="construction",
    )
    construction_blocks = _blocks(construction)

    # The zero-overlap proof, recomputed from the exposure sources themselves
    # rather than from a cached number, and fail-closed: a non-zero overlap
    # stops the script before a byte is written.
    block_of = {sid: row.query_idx for row in rows for sid in row.sample_ids}
    exposure_blocks = {block_of[sid] for sid in exposed if sid in block_of}
    unmapped_exposure_ids = {sid for sid in exposed if sid not in block_of}
    drawn_ids = _sample_ids(fresh) | _sample_ids(construction)
    overlaps = {
        "overlap_with_exposure_union_blocks": len(
            (construction_blocks | fresh_blocks) & exposure_blocks
        ),
        "overlap_with_exposure_union_sample_ids": len(drawn_ids & set(exposed)),
        "overlap_with_unmapped_exposure_ids": len(drawn_ids & unmapped_exposure_ids),
        "overlap_between_the_two_rosters": len(construction_blocks & fresh_blocks),
    }
    if any(count for count in overlaps.values()):
        raise SystemExit(f"refusing to write: the rosters are not disjoint: {overlaps}")

    disjointness = {
        "policy": (
            "block-level: a query_idx block is the leakage unit, because the carrier "
            "re-renders the same base scenario at several tiers"
        ),
        "exposure_union_sample_ids": exposure["union_sample_ids"],
        "exposure_union_blocks": len(exposure_blocks),
        "exposure_union_sources": [
            str(source["relpath"])
            for source in exposure["sources"]  # type: ignore[index]
        ],
        **overlaps,
    }
    offline = {
        "exposure_row": EXPOSURE_ROW_ID,
        "outbound_connection_attempts": attempts.count,
        "attempted_targets": list(attempts.targets),
    }
    pool_common = {
        "carrier_units_total": inventory["usable_units"],
        "blocks_total": partition.report["blocks_total"],
        "blocks_reserved_by_exposure": partition.report["blocks_reserved_exposed"],
        "eval_tool_min_pool_rows": EVAL_TOOL_MIN_POOL_ROWS,
        "within_roster_group_key": "<tier>:block:<query_idx>",
        "within_roster_group_key_rationale": GROUP_KEY_RATIONALE,
    }

    fresh_doc = _enrich(
        fresh,
        design=FRESH_DESIGN,
        status="RESERVED_AND_UNOPENED",
        exposure_union=exposure,
        candidate_pool={
            **pool_common,
            "source": "every exposure-free unit whose gold tool clears the eval floor",
            "candidate_units": len(fresh_candidates),
            "candidate_units_by_tier": _tier_counts(fresh_candidates),
        },
        block_disjointness={**disjointness, "distinct_blocks": len(fresh_blocks)},
        offline_guard=offline,
    )
    construction_doc = _enrich(
        construction,
        design=CONSTRUCTION_DESIGN,
        status="FROZEN_CONSTRUCTION_ROSTER",
        exposure_union=exposure,
        candidate_pool={
            **pool_common,
            "source": (
                "the block partition's construction pool, minus every block "
                f"{FRESH_ROSTER_ID} reserved"
            ),
            "candidate_units": len(construction_candidates),
            "candidate_units_by_tier": _tier_counts(construction_candidates),
        },
        block_disjointness={
            **disjointness,
            "distinct_blocks": len(construction_blocks),
            "reserved_evaluation_roster": FRESH_ROSTER_ID,
        },
        offline_guard=offline,
    )
    probe_view = as_probe_sample_receipt(
        construction_doc, carrier=AUDIO2TOOL_LOCK_KEY, design=CONSTRUCTION_DESIGN
    )
    probe_view.update(
        {
            "authority": AUTHORITY,
            "exposure_row": EXPOSURE_ROW_ID,
            "source_roster": CONSTRUCTION_RELPATH,
            "target_gold_opened_before_receipt": False,
        }
    )

    for label, doc in (
        (FRESH_ROSTER_ID, fresh_doc),
        (CONSTRUCTION_ROSTER_ID, construction_doc),
    ):
        print(
            f"{label}: {len(doc['items'])} items in {len(_blocks(doc))} blocks, "
            f"{doc['strata_counts']}"
        )
        print(
            f"  split_identity_hash={doc['split_identity_hash']}  "
            f"receipt_sha256={hashlib.sha256(canonical_receipt_bytes(doc)).hexdigest()}"
        )
    print(f"block/id overlap proof: {overlaps}")
    print(
        f"probe-sample view: {probe_view['n_items']} items, "
        f"split_identity_hash={probe_view['split_identity_hash']}"
    )
    print(f"offline guard: {attempts.count} outbound connection attempts")

    if not args.write:
        print("(print only; pass --write to land the receipts)")
        return 0

    probe_path = PROBE_SAMPLES_DIR / "a2t-construction-800-v1.json"
    if probe_path.exists():
        raise SystemExit(f"refusing to overwrite an existing receipt: {probe_path}")
    write_roster(fresh_doc, ROSTERS_DIR / "a2t-fresh-800-v1.json")
    write_roster(construction_doc, ROSTERS_DIR / "a2t-construction-800-v1.json")
    write_json_artifact(probe_path, probe_view)
    for path in (
        ROSTERS_DIR / "a2t-fresh-800-v1.json",
        ROSTERS_DIR / "a2t-construction-800-v1.json",
        probe_path,
    ):
        print(
            f"wrote {path.relative_to(REPO_ROOT)}  "
            f"sha256={hashlib.sha256(path.read_bytes()).hexdigest()}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
