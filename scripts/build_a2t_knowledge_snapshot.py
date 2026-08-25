#!/usr/bin/env python3
"""CLI: Audio2Tool generality campaign, stage G0 -- build the A2T knowledge
snapshot, land its coverage + decontamination receipt, and compute the
LEXICAL reachability ceiling that is the campaign's go/stop gate.

Authority: ``docs/readiness/2026-08-25-a2t-generality-campaign-plan.md``
sections 3.2, 3.3 and 3.6. Exposure row: ``SAEA-SN-MF-A2T-G0``
(``docs/exposure-ledger.md``), registered BEFORE this script computes
anything.

ZERO CONTACTS OF ANY KIND. ``analysis.dev100_reviewer_audit.arm_offline_guard``
is armed before the first input is opened and the recorded outbound attempt
count is written into every receipt this script emits. No model, no
tokenizer, no embedding sidecar, no network, no audio decoded.

Usage::

    python scripts/build_a2t_knowledge_snapshot.py --size full
    python scripts/build_a2t_knowledge_snapshot.py --size 5000
    python scripts/build_a2t_knowledge_snapshot.py --size full --no-ceiling

Artifacts::

    $SPEECHRL_DATA_DIR/knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-<N>/snapshot.json
    docs/receipts/knowledge/a2t-kb-size-<N>.json
    docs/receipts/knowledge/a2t-partition-proposal.json     (--size full only)
    docs/receipts/knowledge/a2t-kb-lexical-ceiling.json     (--size full only)

Deterministic: re-running the same ``--size`` against unchanged manifests and
an unchanged frozen probe receipt produces byte-identical governance
receipts (sorted ids, canonical JSON via ``e0.artifacts.write_json_artifact``,
explicit UTF-8), except for the ``timing_seconds`` block, which is written
only into the size receipt and is excluded from every hash the campaign
cites.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.analysis.a2t_lexical_ceiling import (  # noqa: E402
    CEILING_POLICY_ID,
    DEFAULT_K_GRID,
    gate_verdict,
    lexical_reachability_ceiling,
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
    A2T_KB_BUILD_POLICY_ID,
    EXPOSED_RECEIPT_RELPATH,
    A2tKnowledgeBuildSpec,
    a2t_pool_rows,
    build_a2t_knowledge_snapshot,
    coverage_report_a2t,
    exposed_sample_ids,
    load_tool_registry_by_name,
    propose_partition,
)

AUTHORITY = (
    "docs/readiness/2026-08-25-a2t-generality-campaign-plan.md sections 3.2, 3.3 and 3.6"
)
EXPOSURE_ROW_ID = "SAEA-SN-MF-A2T-G0"
BUILD_SEED = 20260825
PARTITION_SEED = 20260807
A0_TOOL_ACCURACY = 0.5425
GATE_K = 5
RECEIPTS_DIR = REPO_ROOT / "docs" / "receipts" / "knowledge"


def _parse_size(raw: str) -> int | None:
    if raw == "full":
        return None
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"--size must be a positive int or 'full', got {raw!r}"
        ) from None
    if value <= 0:
        raise argparse.ArgumentTypeError("--size must be a positive int or 'full'")
    return value


def _size_label(size: int | None) -> str:
    return "full" if size is None else str(size)


def _offline_block(attempts) -> dict[str, object]:
    return {
        "exposure_row": EXPOSURE_ROW_ID,
        "outbound_connection_attempts": attempts.count,
        "attempted_targets": list(attempts.targets),
        "mechanism": (
            "socket.socket.connect / connect_ex / socket.create_connection were replaced "
            "with counting refusals before the first input was opened"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--size", type=str, default="full", help="positive int datastore size, or 'full'"
    )
    parser.add_argument(
        "--no-ceiling",
        action="store_true",
        help="build the snapshot only; skip the G0 lexical ceiling and gate",
    )
    args = parser.parse_args()
    size = _parse_size(args.size)

    attempts = arm_offline_guard()

    lock = load_lock(umbrella_lock_path(REPO_ROOT))
    root = data_root()

    load_start = time.monotonic()
    rows, inventory = a2t_pool_rows(lock, root)
    registry = load_tool_registry_by_name(lock, root)
    load_seconds = time.monotonic() - load_start
    print(
        f"loaded {inventory['pool_items']} pool items in {inventory['pool_units']} units "
        f"({inventory['usable_units']} usable) in {load_seconds:.2f}s"
    )

    partition_start = time.monotonic()
    exposed = exposed_sample_ids(REPO_ROOT)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    partition_seconds = time.monotonic() - partition_start
    eval_ids = frozenset(partition.eval_sample_ids)
    forbidden = frozenset(exposed) | eval_ids
    print(
        f"partition: construction={partition.report['units_construction']} units, "
        f"eval={len(eval_ids)} items, exposed-reserved="
        f"{partition.report['units_reserved_exposed']} units "
        f"({partition_seconds:.2f}s)"
    )

    spec = A2tKnowledgeBuildSpec(datastore_size=size, seed=BUILD_SEED)
    build_start = time.monotonic()
    snapshot = build_a2t_knowledge_snapshot(
        spec,
        rows=partition.construction,
        registry=registry,
        forbidden_sample_ids=forbidden,
        governed_relpath_by_tier={
            tier: f"datasets/audio2tool/public/{tier}_data/{tier}.json"
            for tier in {row.tier for row in partition.construction}
        },
    )
    build_seconds = time.monotonic() - build_start
    print(
        f"built snapshot {snapshot.snapshot_id} facets={len(snapshot.facets)} "
        f"values={len(snapshot.values)} in {build_seconds:.2f}s"
    )

    report_start = time.monotonic()
    coverage = coverage_report_a2t(
        snapshot,
        partition.construction,
        registry_tool_count=len(registry),
    )
    report_seconds = time.monotonic() - report_start

    frozen = snapshot.frozen_json()
    snapshot_sha256 = frozen["snapshot_sha256"]
    snapshot_path = (
        root
        / "knowledge"
        / "audio2tool"
        / A2T_KB_BUILD_POLICY_ID
        / f"size-{_size_label(size)}"
        / "snapshot.json"
    )
    write_json_artifact(snapshot_path, frozen)
    print(f"wrote {snapshot_path}  snapshot_sha256={snapshot_sha256[:16]}...")

    receipt = {
        "schema": "saea-kb-a2t-build-receipt-v1",
        "generator": "scripts/build_a2t_knowledge_snapshot.py",
        "authority": AUTHORITY,
        "exposure_row": EXPOSURE_ROW_ID,
        "offline_guard": _offline_block(attempts),
        "builder_policy_id": A2T_KB_BUILD_POLICY_ID,
        "spec": {
            "carrier_lock_key": spec.carrier_lock_key,
            "datastore_size": spec.datastore_size,
            "seed": spec.seed,
            "dimensions": list(spec.dimensions),
        },
        "snapshot_sha256": snapshot_sha256,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_artifact_relpath": str(snapshot_path.relative_to(root)),
        "source_split_identity_hash": snapshot.source_split_identity_hash,
        "facet_count": len(snapshot.facets),
        "value_count": len(snapshot.values),
        "carrier_inventory": inventory,
        "partition_report": dict(partition.report),
        "coverage_report": coverage,
        "decontamination": {
            "verdict": "clean",
            "checked_sample_count": len(snapshot.source_sample_ids),
            "forbidden_roster_size": len(forbidden),
            "forbidden_rosters": [
                EXPOSED_RECEIPT_RELPATH,
                "docs/receipts/knowledge/a2t-partition-proposal.json (proposed eval tier)",
            ],
            "exposed_400_count": len(exposed),
            "proposed_eval_count": len(eval_ids),
        },
        "timing_seconds": {
            "load_pool_rows": round(load_seconds, 3),
            "propose_partition": round(partition_seconds, 3),
            "build_snapshot": round(build_seconds, 3),
            "coverage_report": round(report_seconds, 3),
        },
    }
    receipt_path = RECEIPTS_DIR / f"a2t-kb-size-{_size_label(size)}.json"
    receipt_sha256 = write_json_artifact(receipt_path, receipt)
    print(f"wrote {receipt_path.relative_to(REPO_ROOT)}  sha256={receipt_sha256[:16]}...")
    print(
        f"  tool_coverage={coverage['tool_coverage']:.4f} "
        f"family_coverage={coverage['argument_pattern_family_coverage']:.4f} "
        f"tier_coverage={coverage['tier_coverage']:.4f} "
        f"kl_tool={coverage['kl_selected_given_pool_over_tool']:.6f}"
    )

    if size is None:
        proposal_doc = {
            "schema": "saea-a2t-partition-proposal-v1",
            "generator": "scripts/build_a2t_knowledge_snapshot.py",
            "authority": AUTHORITY,
            "exposure_row": EXPOSURE_ROW_ID,
            "offline_guard": _offline_block(attempts),
            "status": (
                "PROPOSAL ONLY. This document is NOT a registered split and is deliberately "
                "NOT written under docs/receipts/probe-samples/, so it does not enter the "
                "Audio2Tool loader's frozen sample universe. Registering the evaluation "
                "tier as flyable is later campaign work with its own preregistration."
            ),
            "policy_id": partition.policy_id,
            "seed": partition.seed,
            "report": dict(partition.report),
            "proposed_eval_split_identity_hash": partition.split_identity_hash(),
            "proposed_eval_items": [
                {"tier": tier, "id": item_id, "key": f"audio2tool:{tier}:{item_id:06d}"}
                for tier, item_id, _text, _tool in partition.eval_items
            ],
            "reserved_exposed_blocks": list(partition.reserved_exposed_blocks),
            "eval_blocks": list(partition.eval_blocks),
        }
        proposal_path = RECEIPTS_DIR / "a2t-partition-proposal.json"
        digest = write_json_artifact(proposal_path, proposal_doc)
        print(f"wrote {proposal_path.relative_to(REPO_ROOT)}  sha256={digest[:16]}...")

    if args.no_ceiling or size is not None:
        print("skipping the G0 lexical ceiling (not the full snapshot, or --no-ceiling)")
        print(f"offline guard: {attempts.count} outbound connection attempts")
        return 0

    ceiling_start = time.monotonic()
    ceiling = lexical_reachability_ceiling(
        snapshot, partition.eval_items, k_grid=DEFAULT_K_GRID
    )
    ceiling_seconds = time.monotonic() - ceiling_start
    verdict = gate_verdict(ceiling, gate_k=GATE_K, a0_tool_accuracy=A0_TOOL_ACCURACY)

    ceiling_doc = {
        "schema": "saea-a2t-lexical-ceiling-v1",
        "generator": "scripts/build_a2t_knowledge_snapshot.py",
        "authority": AUTHORITY,
        "exposure_row": EXPOSURE_ROW_ID,
        "offline_guard": _offline_block(attempts),
        "ceiling_policy_id": CEILING_POLICY_ID,
        "snapshot_id": snapshot.snapshot_id,
        "snapshot_sha256": snapshot_sha256,
        "proposed_eval_split_identity_hash": partition.split_identity_hash(),
        "proxy_disclosure": (
            "LEXICAL PROXY, cutting BOTH ways, restated wherever this number is cited. "
            "Pessimistic in the ranking function: token overlap cannot follow paraphrase "
            "the way a dense encoder can, so a dense ranker over the same facets would "
            "place at least some gold-tool facets higher. Optimistic in the query "
            "representation: the query text is the manifest transcript of the spoken "
            "command, while at runtime the controller sees only a speech-derived percept. "
            "Neither direction dominates, so this is a ceiling on the LEXICAL channel "
            "conditioned on a PERFECT TRANSCRIPT, and the gate treats it as a necessary "
            "condition, never a sufficient one."
        ),
        "ceiling": ceiling,
        "gate": verdict,
    }
    ceiling_path = RECEIPTS_DIR / "a2t-kb-lexical-ceiling.json"
    digest = write_json_artifact(ceiling_path, ceiling_doc)
    print(
        f"wrote {ceiling_path.relative_to(REPO_ROOT)}  sha256={digest[:16]}...  "
        f"({ceiling_seconds:.2f}s; timing is deliberately NOT written into this "
        "receipt so it is byte-stable)"
    )
    for k in DEFAULT_K_GRID:
        print(
            f"  recall@{k:<4} = {ceiling['recall_at_k'][str(k)]:.4f}   "
            f"(random {ceiling['random_ranking_expectation_at_k'][str(k)]:.4f})"
        )
    print(
        f"GATE at k={GATE_K}: ceiling {verdict['lexical_ceiling_at_gate_k']:.4f} vs "
        f"A0 tool accuracy {A0_TOOL_ACCURACY:.4f} -> {verdict['verdict']} "
        f"(margin {verdict['margin']:+.4f})"
    )
    print(f"offline guard: {attempts.count} outbound connection attempts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
