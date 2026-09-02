"""Build the preregistered Audio2Tool executable ground without contact."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Sequence

REPO = Path(__file__).resolve().parents[5]

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_executable_ground import (  # noqa: E402
    build_executable_ground,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)

RUN_ID = "SAEA-A2T-MF-EXECUTABLE-GROUND-BUILD-V1"
PARTITION_SEED = 20260807
PROPOSED_EVAL_IDENTITY = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)
PARTITION_PROPOSAL = REPO / "docs/receipts/knowledge/a2t-partition-proposal.json"
PARTITION_PROPOSAL_SHA256 = (
    "3bbf77a328c2983fb6299bcfe34a975624fee330a9325614dc1f84a7338678a1"
)
REGISTRY_SHA256 = "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def run_build(root: Path) -> tuple[str, dict[str, object]]:
    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    proposal_sha = _sha256_file(PARTITION_PROPOSAL)
    if proposal_sha != PARTITION_PROPOSAL_SHA256:
        raise RuntimeError("partition proposal SHA-256 drift")
    lock = load_lock(umbrella_lock_path(REPO))
    registry_path = asset_dir(lock, "audio2tool", root) / "tools_registry.csv"
    if _sha256_file(registry_path) != REGISTRY_SHA256:
        raise RuntimeError("registry SHA-256 drift")
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    if partition.split_identity_hash() != PROPOSED_EVAL_IDENTITY:
        raise RuntimeError("proposed evaluation identity drift")
    eval_ids = frozenset(partition.eval_sample_ids)
    construction_ids = frozenset(
        sample_id
        for row in partition.construction
        for sample_id in row.sample_ids
    )
    if construction_ids & (exposed | eval_ids):
        raise RuntimeError("construction decontamination drift")

    first = build_executable_ground(registry, partition.construction)
    second = build_executable_ground(registry, tuple(reversed(partition.construction)))
    if first.text != second.text or first.sha256 != second.sha256:
        raise RuntimeError("executable-ground build is not pool-order deterministic")
    expected = {
        "registry_tool_count": 152,
        "construction_tool_count": 151,
        "argument_pattern_family_count": 354,
        "argument_key_count": 85,
        "ascii_only": True,
        "default_literal_match_count": 0,
        "invocation_texts_rendered": 0,
        "argument_values_rendered": 0,
    }
    if any(first.report[key] != value for key, value in expected.items()):
        raise RuntimeError("executable-ground static coverage or safety gate failed")

    receipt = {
        "schema": "saea-a2t-executable-ground-build-receipt-v1",
        "experiment_id": RUN_ID,
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "source_hashes": {
            "partition_proposal": PARTITION_PROPOSAL_SHA256,
            "registry": REGISTRY_SHA256,
        },
        "partition": {
            "policy_id": partition.policy_id,
            "seed": partition.seed,
            "construction_unit_count": len(partition.construction),
            "construction_sample_count": len(construction_ids),
            "construction_identity_sha256": _identity(
                tuple(row.unit_id for row in partition.construction)
            ),
            "exposed_sample_count": len(exposed),
            "proposed_eval_sample_count": len(eval_ids),
            "proposed_eval_identity_sha256": partition.split_identity_hash(),
            "construction_forbidden_intersection_count": len(
                construction_ids & (exposed | eval_ids)
            ),
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
        },
        "contacts": {
            "frozen_core": 0,
            "retriever": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "http_or_socket": 0,
            "audio_seconds": 0,
            "gpu_hours": 0.0,
        },
        "offline_guard": {
            "outbound_connection_attempts": offline.count,
            "targets": [],
        },
        "decision": "permit only a separately preregistered tokenizer prompt-fit check",
        "engineering_scope": {
            "complete_manifest_outer_parallel_scoring": True,
            "network_jitter_testing": False,
        },
    }
    return first.text, receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handbook-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args(argv)
    text, receipt = run_build(data_root())
    args.handbook_output.parent.mkdir(parents=True, exist_ok=True)
    args.handbook_output.write_text(text, encoding="utf-8", newline="\n")
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    args.receipt_output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
