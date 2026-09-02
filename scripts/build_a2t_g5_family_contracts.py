"""Build and qualify the Audio2Tool exhaustive family-contract corpus offline."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Sequence


REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

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
from speech_aware_evidence_acquisition.rails.action_family_contracts import (  # noqa: E402
    DEFAULT_MAX_FAMILY_BUNDLE_ASCII_BYTES,
    ActionFamilyContractError,
    build_action_family_corpus,
    qualify_action_family_corpus,
    split_construction_validation,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)


RUN_ID = "SAEA-A2T-MF-G5-EXHAUSTIVE-FAMILY-CONTRACT-BUILD-V1"
PARTITION_SEED = 20260807
CONSTRUCTION_VALIDATION_SEED = 20260902
PROPOSED_EVAL_IDENTITY = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)
PARTITION_PROPOSAL = REPO / "docs/receipts/knowledge/a2t-partition-proposal.json"
PARTITION_PROPOSAL_SHA256 = (
    "3bbf77a328c2983fb6299bcfe34a975624fee330a9325614dc1f84a7338678a1"
)
REGISTRY_SHA256 = "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"
DEFAULT_CORPUS_OUTPUT = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g5-exhaustive-family-contracts-v1"
    / "corpus.json"
)
DEFAULT_RECEIPT_OUTPUT = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-02-a2t-g5-family-contract-build-v1"
    / "build-receipt.json"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def run_build(root: Path) -> tuple[str, dict[str, object]]:
    """Run the hash-pinned construction-only build and qualification."""

    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    if _sha256_file(PARTITION_PROPOSAL) != PARTITION_PROPOSAL_SHA256:
        raise ActionFamilyContractError("partition proposal SHA-256 drift")
    lock = load_lock(umbrella_lock_path(REPO))
    registry_path = asset_dir(lock, "audio2tool", root) / "tools_registry.csv"
    if _sha256_file(registry_path) != REGISTRY_SHA256:
        raise ActionFamilyContractError("registry SHA-256 drift")
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    if partition.split_identity_hash() != PROPOSED_EVAL_IDENTITY:
        raise ActionFamilyContractError("proposed evaluation identity drift")
    evaluation_ids = frozenset(partition.eval_sample_ids)
    construction_ids = frozenset(
        sample_id for row in partition.construction for sample_id in row.sample_ids
    )
    if construction_ids & (exposed | evaluation_ids):
        raise ActionFamilyContractError("construction decontamination drift")

    build_rows, validation_rows = split_construction_validation(
        partition.construction,
        seed=CONSTRUCTION_VALIDATION_SEED,
    )
    build_blocks = {row.query_idx for row in build_rows}
    validation_blocks = {row.query_idx for row in validation_rows}
    if build_blocks & validation_blocks:
        raise ActionFamilyContractError("construction-validation block overlap")

    corpus = build_action_family_corpus(registry, build_rows)
    reversed_corpus = build_action_family_corpus(
        tuple(reversed(registry)), tuple(reversed(build_rows))
    )
    if corpus.sha256 != reversed_corpus.sha256 or corpus.to_json() != reversed_corpus.to_json():
        raise ActionFamilyContractError("reverse-order corpus build hash drift")
    qualification = qualify_action_family_corpus(
        corpus,
        registry_rows=registry,
        validation_rows=validation_rows,
    )
    if not qualification.passed:
        raise ActionFamilyContractError(
            "fixed family-contract qualification failed; gates will not be weakened: "
            + json.dumps(qualification.as_json(), sort_keys=True)
        )
    if offline.count:
        raise ActionFamilyContractError("offline guard observed an outbound attempt")

    corpus_text = corpus.to_json()
    receipt = {
        "schema": "saea-a2t-g5-family-contract-build-receipt-v1",
        "experiment_id": RUN_ID,
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "source_hashes": {
            "partition_proposal": PARTITION_PROPOSAL_SHA256,
            "registry": REGISTRY_SHA256,
            "builder": _sha256_file(Path(__file__)),
        },
        "partition": {
            "policy_id": partition.policy_id,
            "seed": partition.seed,
            "proposed_eval_identity_sha256": partition.split_identity_hash(),
            "proposed_eval_sample_count": len(evaluation_ids),
            "exposed_sample_count": len(exposed),
            "construction_unit_count": len(partition.construction),
            "construction_sample_count": len(construction_ids),
            "construction_identity_sha256": _identity(
                tuple(row.unit_id for row in partition.construction)
            ),
            "forbidden_intersection_count": 0,
        },
        "construction_validation": {
            "seed": CONSTRUCTION_VALIDATION_SEED,
            "build_unit_count": len(build_rows),
            "validation_unit_count": len(validation_rows),
            "build_query_block_count": len(build_blocks),
            "validation_query_block_count": len(validation_blocks),
            "query_block_intersection_count": 0,
            "build_identity_sha256": _identity(tuple(row.unit_id for row in build_rows)),
            "validation_identity_sha256": _identity(
                tuple(row.unit_id for row in validation_rows)
            ),
        },
        "corpus": {
            "path": DEFAULT_CORPUS_OUTPUT.relative_to(REPO).as_posix(),
            "sha256": corpus.sha256,
            "ascii_bytes": len(corpus_text.encode("ascii")),
            "family_count": len(corpus.families),
            "contract_count": len(corpus.contracts),
            "maximum_family_bundle_ascii_bytes": max(
                family.bundle_utf8_bytes for family in corpus.families
            ),
            "family_bundle_limit_ascii_bytes": DEFAULT_MAX_FAMILY_BUNDLE_ASCII_BYTES,
            "reverse_order_build_sha256": reversed_corpus.sha256,
            "report": dict(corpus.report),
        },
        "qualification": qualification.as_json(),
        "carrier_inventory": inventory,
        "contacts": {
            "frozen_core": 0,
            "network": 0,
            "retriever": 0,
            "tokenizer": 0,
            "scorer": 0,
            "audio_seconds": 0,
            "gpu_hours": 0.0,
        },
        "offline_guard": {"outbound_connection_attempts": offline.count, "targets": []},
        "scope": {
            "evaluation_rows_consumed": 0,
            "test_rows_consumed": 0,
            "fresh_rows_consumed": 0,
            "g4_remainder_rows_consumed": 0,
            "configuration_written": False,
            "preregistration_written": False,
            "exposure_ledger_written": False,
            "flight_launcher_written": False,
            "model_flight_authorized": False,
        },
    }
    return corpus_text, receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-output", type=Path, default=DEFAULT_CORPUS_OUTPUT)
    parser.add_argument("--receipt-output", type=Path, default=DEFAULT_RECEIPT_OUTPUT)
    args = parser.parse_args(argv)
    corpus, receipt = run_build(data_root())
    args.corpus_output.parent.mkdir(parents=True, exist_ok=True)
    args.corpus_output.write_text(corpus, encoding="utf-8", newline="\n")
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    args.receipt_output.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
