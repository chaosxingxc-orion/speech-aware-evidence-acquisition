"""Build the frozen Audio2Tool G4 executable semantic-card corpus offline."""

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
from speech_aware_evidence_acquisition.rails.knowledge_compile_a2t import (  # noqa: E402
    MINIMUM_COMPATIBILITY_SUPPORT,
    CompatibilityRule,  # noqa: F401
    SemanticCardCompilationError,
    build_from_partition,
    derive_compatibility_rules,  # noqa: F401
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import (  # noqa: E402
    a2t_pool_rows,
    exposed_sample_ids,
    propose_partition,
)

RUN_ID = "SAEA-A2T-MF-G4-SEMANTIC-CARDS-BUILD-V1"
PARTITION_SEED = 20260807
EXPECTED_REGISTRY_TOOLS = 152
EXPECTED_PATTERN_FAMILIES = 354
EXPECTED_ARGUMENT_KEYS = 85
PROPOSED_EVAL_IDENTITY = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)
PARTITION_PROPOSAL = REPO / "docs/receipts/knowledge/a2t-partition-proposal.json"
PARTITION_PROPOSAL_SHA256 = (
    "3bbf77a328c2983fb6299bcfe34a975624fee330a9325614dc1f84a7338678a1"
)
REGISTRY_SHA256 = "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"
DEFAULT_CORPUS_OUTPUT = (
    REPO / "knowledge" / "audio2tool" / "g4-executable-semantic-cards-v1" / "corpus.txt"
)
DEFAULT_RECEIPT_OUTPUT = (
    REPO
    / "docs"
    / "checks"
    / "speech-aware-evidence-acquisition"
    / "2026-09-02-a2t-g4-semantic-cards-build-v1"
    / "build-receipt.json"
)

G4SemanticCardBuildError = SemanticCardCompilationError


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(values: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def run_build(root: Path) -> tuple[str, dict[str, object]]:
    """Run the hash-pinned, model-free build on the frozen construction partition."""

    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    if _sha256_file(PARTITION_PROPOSAL) != PARTITION_PROPOSAL_SHA256:
        raise G4SemanticCardBuildError("partition proposal SHA-256 drift")
    lock = load_lock(umbrella_lock_path(REPO))
    registry_path = asset_dir(lock, "audio2tool", root) / "tools_registry.csv"
    if _sha256_file(registry_path) != REGISTRY_SHA256:
        raise G4SemanticCardBuildError("registry SHA-256 drift")
    registry = load_tool_registry(lock, root)
    rows, inventory = a2t_pool_rows(lock, root)
    exposed = exposed_sample_ids(REPO)
    partition = propose_partition(rows, exposed, seed=PARTITION_SEED)
    if partition.split_identity_hash() != PROPOSED_EVAL_IDENTITY:
        raise G4SemanticCardBuildError("proposed evaluation identity drift")
    evaluation_ids = frozenset(partition.eval_sample_ids)
    construction_ids = frozenset(
        sample_id for row in partition.construction for sample_id in row.sample_ids
    )
    forbidden_intersection = construction_ids & (exposed | evaluation_ids)
    if forbidden_intersection:
        raise G4SemanticCardBuildError("construction decontamination drift")

    corpus, audit = build_from_partition(registry, partition.construction)
    if len(registry) != EXPECTED_REGISTRY_TOOLS:
        raise G4SemanticCardBuildError("registry tool-count drift")
    if audit["construction_argument_pattern_family_count"] != EXPECTED_PATTERN_FAMILIES:
        raise G4SemanticCardBuildError("construction argument-pattern count drift")
    if audit["construction_argument_key_count"] != EXPECTED_ARGUMENT_KEYS:
        raise G4SemanticCardBuildError("construction argument-key count drift")
    expected_corpus_report = {
        "registry_tool_count": EXPECTED_REGISTRY_TOOLS,
        "tool_card_count": EXPECTED_REGISTRY_TOOLS,
        "task_card_count": 4,
        "examples_validated": True,
        "ascii_only": True,
        "source_utterances_rendered": 0,
        "reference_transcripts_rendered": 0,
        "source_argument_values_rendered": 0,
        "gold_values_rendered": 0,
        "source_sample_ids_rendered": 0,
        "evaluation_samples_consumed": 0,
    }
    if any(
        corpus.report.get(key) != value for key, value in expected_corpus_report.items()
    ):
        raise G4SemanticCardBuildError("semantic-card static safety gate failed")
    compatibility = dict(audit["compatibility"])
    if compatibility["minimum_support"] != MINIMUM_COMPATIBILITY_SUPPORT:
        raise G4SemanticCardBuildError("compatibility support threshold drift")
    if compatibility["concrete_argument_values_rendered"] != 0:
        raise G4SemanticCardBuildError("compatibility derivation rendered values")
    if offline.count != 0:
        raise G4SemanticCardBuildError("offline guard observed an outbound attempt")

    receipt = {
        "schema": "saea-a2t-g4-semantic-card-build-receipt-v1",
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
            "construction_unit_count": len(partition.construction),
            "construction_sample_count": len(construction_ids),
            "construction_identity_sha256": _identity(
                tuple(row.unit_id for row in partition.construction)
            ),
            "exposed_sample_count": len(exposed),
            "proposed_eval_sample_count": len(evaluation_ids),
            "proposed_eval_identity_sha256": partition.split_identity_hash(),
            "construction_forbidden_intersection_count": len(forbidden_intersection),
        },
        "carrier_inventory": {
            "pool_items": inventory["pool_items"],
            "pool_units": inventory["pool_units"],
            "usable_units": inventory["usable_units"],
        },
        "construction_summary": {
            "argument_pattern_family_count": audit[
                "construction_argument_pattern_family_count"
            ],
            "argument_key_count": audit["construction_argument_key_count"],
            "safe_construction_row_count": audit["safe_construction_row_count"],
            "excluded_construction_row_count": audit["excluded_construction_row_count"],
            "source_utterances_rendered": 0,
            "source_sample_ids_rendered": 0,
            "call_renders_rendered": 0,
            "concrete_argument_values_rendered": 0,
        },
        "compatibility": compatibility,
        "corpus": {
            "path": str(DEFAULT_CORPUS_OUTPUT.relative_to(REPO)).replace("\\", "/"),
            "sha256": corpus.sha256,
            "report": dict(corpus.report),
            "deterministic_rebuild_equal": audit["deterministic_rebuild_equal"],
        },
        "contacts": {
            "frozen_core": 0,
            "network": 0,
            "retriever": 0,
            "embedding_tool": 0,
            "tokenizer": 0,
            "scorer": 0,
            "audio_seconds": 0,
            "gpu_hours": 0,
        },
        "offline_guard": {
            "outbound_connection_attempts": offline.count,
            "targets": [],
        },
        "scope": {
            "model_flight_authorized": False,
            "launcher_created": False,
            "exposure_row_created": False,
            "evaluation_or_fresh_rows_rendered": 0,
            "network_jitter_testing": False,
        },
    }
    return corpus.text, receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-output", type=Path, default=DEFAULT_CORPUS_OUTPUT)
    parser.add_argument("--receipt-output", type=Path, default=DEFAULT_RECEIPT_OUTPUT)
    args = parser.parse_args(argv)
    text, receipt = run_build(data_root())
    args.corpus_output.parent.mkdir(parents=True, exist_ok=True)
    args.corpus_output.write_text(text, encoding="utf-8", newline="\n")
    args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    args.receipt_output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
