"""Materialize the construction-semantic Audio2Tool ground without contact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Sequence


REPO = Path(__file__).resolve().parents[4]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_construction_semantic_ground import (  # noqa: E402
    build_construction_semantic_ground,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


RUN_ID = "SAEA-A2T-MF-CONSTRUCTION-SEMANTIC-GROUND-BUILD-V2"
PARTITION_SEED = 20260807
PROPOSED_EVAL_IDENTITY = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)
EXPECTED_HANDBOOK_SHA256 = (
    "04c9c78d03b002faf6c828a5b35f1786aadc7f5da3fee2bf675374e7ea2ea697"
)


def _identity(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def run_build(root: Path) -> tuple[str, dict[str, object]]:
    """Build twice, prove determinism, and return the artifact plus receipt."""

    study_commit = require_clean_study_repo(REPO)
    lock = load_lock(umbrella_lock_path(REPO))
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    if partition.split_identity_hash() != PROPOSED_EVAL_IDENTITY:
        raise RuntimeError("construction/evaluation partition identity drift")
    evaluation_ids = frozenset(partition.eval_sample_ids)
    construction_ids = frozenset(
        sample_id for row in partition.construction for sample_id in row.sample_ids
    )
    if construction_ids & (exposed | evaluation_ids):
        raise RuntimeError("construction partition intersects a forbidden identity")

    first = build_construction_semantic_ground(registry, partition.construction)
    second = build_construction_semantic_ground(
        tuple(reversed(registry)), tuple(reversed(partition.construction))
    )
    if first != second or first.sha256 != EXPECTED_HANDBOOK_SHA256:
        raise RuntimeError("construction-semantic ground determinism or identity drift")
    expected_report = {
        "registry_tool_count": 152,
        "construction_primary_tool_count": 151,
        "tier_tool_pair_count": 1094,
        "argument_key_pattern_count": 1326,
        "tool_sequence_pattern_count": 2210,
        "lexical_cues_rendered": 3146,
        "invocation_texts_rendered": 0,
        "sample_ids_rendered": 0,
        "argument_values_rendered": 0,
        "ascii_only": True,
        "utf8_bytes": 97548,
    }
    if any(first.report.get(key) != value for key, value in expected_report.items()):
        raise RuntimeError("construction-semantic ground coverage drift")

    receipt = {
        "schema": "saea-a2t-construction-semantic-ground-build-receipt-v1",
        "experiment_id": RUN_ID,
        "execution_profile": "model-free-check",
        "study_commit": study_commit,
        "partition": {
            "policy_id": partition.policy_id,
            "seed": partition.seed,
            "construction_unit_count": len(partition.construction),
            "construction_sample_count": len(construction_ids),
            "construction_identity_sha256": _identity(
                tuple(row.unit_id for row in partition.construction)
            ),
            "exposed_sample_count": len(exposed),
            "proposed_eval_sample_count": len(evaluation_ids),
            "proposed_eval_identity_sha256": partition.split_identity_hash(),
            "construction_forbidden_intersection_count": 0,
        },
        "carrier_inventory": {
            "pool_items": inventory["pool_items"],
            "pool_units": inventory["pool_units"],
            "usable_units": inventory["usable_units"],
        },
        "handbook": {
            "sha256": first.sha256,
            "report": dict(first.report),
            "deterministic_rebuild_equal": True,
            "source_transcripts_rendered": 0,
            "source_argument_values_rendered": 0,
            "source_sample_ids_rendered": 0,
        },
        "contacts": {
            "model": 0,
            "tokenizer": 0,
            "retriever": 0,
            "network": 0,
            "scorer": 0,
            "gold_runtime": 0,
            "gpu_hours": 0.0,
        },
        "decision": "measure exact prompt fit, then run one bounded G2 discovery arm",
        "engineering_scope": {
            "network_jitter_testing": False,
            "official_scorer_single_process_per_manifest": True,
            "outer_parallel_scoring_allowed": True,
        },
    }
    return first.text, receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handbook-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.handbook_output.exists() or args.receipt_output.exists():
        raise RuntimeError("build outputs must not already exist")
    text, receipt = run_build(data_root())
    args.handbook_output.parent.mkdir(parents=True, exist_ok=True)
    args.handbook_output.write_text(text, encoding="utf-8", newline="\n")
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    args.receipt_output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
