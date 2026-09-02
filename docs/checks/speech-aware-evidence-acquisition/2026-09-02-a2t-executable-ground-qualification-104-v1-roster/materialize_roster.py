"""Materialize the preregistered identity-only ground-qualification roster."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
from typing import Mapping, Sequence

REPO = Path(__file__).resolve().parents[4]
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis.a2t_contract_preserving_cohort import (  # noqa: E402
    query_block,
)
from speech_aware_evidence_acquisition.analysis.a2t_ground_qualification_cohort import (  # noqa: E402
    PER_TIER,
    SELECTION_NAMESPACE,
    SPLIT_NAME,
    TIERS,
    GroundRosterSource,
    build_ground_roster_receipt,
    select_ground_roster,
)
from speech_aware_evidence_acquisition.analysis.dev100_reviewer_audit import (  # noqa: E402
    arm_offline_guard,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolAdapter,
)

EXPERIMENT_ID = "SAEA-A2T-MF-EXECUTABLE-GROUND-QUALIFICATION-104-V1-ROSTER"
PARENT_RELPATH = Path("docs/receipts/probe-samples/r1-audio2tool-sample.json")
PARENT_SHA256 = "d99570a797744f7dc3db53bdb898611836ae2682a02e726b974d05734c6cbb2d"
PARENT_SPLIT_IDENTITY = (
    "e1d751e6c76e49d087620842ba17c34e432a4602169dc2b93ee7e0a529ca332c"
)
G1_RELPATH = Path("docs/receipts/a2t/A2T-G1-104.json")
G1_SHA256 = "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
CPV2_RELPATH = Path("docs/receipts/a2t/A2T-CPV2-104.json")
CPV2_SHA256 = "8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783"
OUTPUT_RELPATH = Path("docs/receipts/a2t/A2T-GROUND-QUAL-104.json")
RESULT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-qualification-104-v1-roster/roster-result.json"
)
UNEXPOSED_PROPOSAL_IDENTITY = (
    "4d0196ec91858cdc81340ee197c085ff29726a1f1b7fe9119d4e410d62df2f90"
)


@dataclass(frozen=True)
class ReceiptCandidate:
    sample_id: str
    media_relpath: str
    audio_seconds: float
    audio_sha256: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_receipt(path: Path, expected_sha256: str) -> dict[str, object]:
    measured = _sha256_file(path)
    if measured != expected_sha256:
        raise RuntimeError(f"receipt SHA-256 drift for {path}: {measured}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"receipt must be a JSON object: {path}")
    return value


def _receipt_candidates(document: Mapping[str, object]) -> tuple[ReceiptCandidate, ...]:
    items = document.get("items")
    if not isinstance(items, list) or len(items) != 104:
        raise RuntimeError("excluded receipt must contain exactly 104 items")
    candidates = []
    for item in items:
        if not isinstance(item, Mapping):
            raise RuntimeError("excluded receipt item is malformed")
        candidates.append(
            ReceiptCandidate(
                sample_id=str(item["sample_id"]),
                media_relpath=str(item["media_relpath"]),
                audio_seconds=float(item["audio_seconds"]),
                audio_sha256=str(item["audio_sha256"]),
            )
        )
    return tuple(candidates)


def _source(
    relative: Path,
    sha256: str,
    document: Mapping[str, object],
    candidates: Sequence[ReceiptCandidate],
) -> GroundRosterSource:
    split_identity = document.get("split_identity_hash")
    if not isinstance(split_identity, str):
        raise RuntimeError("excluded receipt lacks a split identity")
    blocks = {
        query_block(item.sample_id.split(":", 1)[0], item.media_relpath)
        for item in candidates
    }
    if len(blocks) != len(candidates):
        raise RuntimeError("excluded receipt repeats a query block")
    return GroundRosterSource(
        receipt=relative.as_posix(),
        sha256=sha256,
        split_identity_hash=split_identity,
        item_count=len(candidates),
        query_block_count=len(blocks),
    ).validate()


def main() -> int:
    output_path = REPO / OUTPUT_RELPATH
    result_path = REPO / RESULT_RELPATH
    if output_path.exists() or result_path.exists():
        raise RuntimeError("ground-qualification roster output already exists")
    study_commit = require_clean_study_repo(REPO)
    offline = arm_offline_guard()
    parent = _read_receipt(REPO / PARENT_RELPATH, PARENT_SHA256)
    if parent.get("split_identity_hash") != PARENT_SPLIT_IDENTITY:
        raise RuntimeError("parent split identity drift")
    parent_items = parent.get("items")
    if not isinstance(parent_items, list) or len(parent_items) != 400:
        raise RuntimeError("parent receipt is not the frozen 400-item roster")
    parent_ids = {
        f"{item['tier']}:{int(item['id']):06d}"
        for item in parent_items
        if isinstance(item, Mapping)
    }
    if len(parent_ids) != 400:
        raise RuntimeError("parent receipt identities are malformed or duplicated")

    g1 = _read_receipt(REPO / G1_RELPATH, G1_SHA256)
    cpv2 = _read_receipt(REPO / CPV2_RELPATH, CPV2_SHA256)
    g1_candidates = _receipt_candidates(g1)
    cpv2_candidates = _receipt_candidates(cpv2)
    excluded_ids = {item.sample_id for item in (*g1_candidates, *cpv2_candidates)}
    if len(excluded_ids) != 208 or not excluded_ids <= parent_ids:
        raise RuntimeError("excluded cohorts are not disjoint subsets of the parent")

    lock = load_lock(umbrella_lock_path(REPO))
    root = data_root()
    runtime_samples = Audio2ToolAdapter(lock, root, repo_root=REPO).load_split(
        "discovery"
    )
    parent_samples = tuple(
        sample for sample in runtime_samples if sample.sample_id in parent_ids
    )
    if (
        len(parent_samples) != 400
        or {sample.sample_id for sample in parent_samples} != parent_ids
    ):
        raise RuntimeError("runtime-legal parent sample surface drift")

    selected = select_ground_roster(
        parent_samples,
        (g1_candidates, cpv2_candidates),
        tiers=TIERS,
        per_tier=PER_TIER,
        namespace=SELECTION_NAMESPACE,
    )
    reversed_selected = select_ground_roster(
        tuple(reversed(parent_samples)),
        (tuple(reversed(g1_candidates)), tuple(reversed(cpv2_candidates))),
        tiers=TIERS,
        per_tier=PER_TIER,
        namespace=SELECTION_NAMESPACE,
    )
    if selected != reversed_selected:
        raise RuntimeError("ground-roster selection depends on parent order")

    sources = (
        _source(G1_RELPATH, G1_SHA256, g1, g1_candidates),
        _source(CPV2_RELPATH, CPV2_SHA256, cpv2, cpv2_candidates),
    )
    receipt = build_ground_roster_receipt(
        selected,
        split_name=SPLIT_NAME,
        namespace=SELECTION_NAMESPACE,
        parent_receipt=PARENT_RELPATH.as_posix(),
        parent_receipt_sha256=PARENT_SHA256,
        parent_split_identity_hash=PARENT_SPLIT_IDENTITY,
        excluded_sources=sources,
        materialization_study_commit=study_commit,
        expected_tiers=TIERS,
        per_tier=PER_TIER,
    )
    rebuilt = build_ground_roster_receipt(
        tuple(reversed(selected)),
        split_name=SPLIT_NAME,
        namespace=SELECTION_NAMESPACE,
        parent_receipt=PARENT_RELPATH.as_posix(),
        parent_receipt_sha256=PARENT_SHA256,
        parent_split_identity_hash=PARENT_SPLIT_IDENTITY,
        excluded_sources=tuple(reversed(sources)),
        materialization_study_commit=study_commit,
        expected_tiers=TIERS,
        per_tier=PER_TIER,
    )
    if receipt != rebuilt:
        raise RuntimeError("ground-roster receipt is not order deterministic")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    receipt_sha = _sha256_file(output_path)
    result = {
        "schema": "saea-a2t-ground-qualification-roster-result-v1",
        "experiment_id": EXPERIMENT_ID,
        "study_commit": study_commit,
        "execution_profile": "model-free-check",
        "source_hashes": {
            PARENT_RELPATH.as_posix(): PARENT_SHA256,
            G1_RELPATH.as_posix(): G1_SHA256,
            CPV2_RELPATH.as_posix(): CPV2_SHA256,
        },
        "selection_namespace": SELECTION_NAMESPACE,
        "parent_count": len(parent_ids),
        "excluded_sample_count": len(excluded_ids),
        "selected_count": receipt["count"],
        "selected_strata_counts": receipt["strata_counts"],
        "selected_audio_seconds_total": receipt["audio_seconds_total"],
        "selected_split_identity_hash": receipt["split_identity_hash"],
        "selected_run_identity_hash": receipt["run_identity_hash"],
        "selected_receipt_sha256": receipt_sha,
        "selected_query_block_count": receipt["selection_proof"][
            "selected_query_block_count"
        ],
        "excluded_query_block_count": receipt["selection_proof"][
            "excluded_query_block_count"
        ],
        "query_block_overlap_count": 0,
        "parent_order_deterministic": True,
        "receipt_order_deterministic": True,
        "runtime_media_identity_verified": True,
        "proposed_unexposed_400": {
            "identity_sha256": UNEXPOSED_PROPOSAL_IDENTITY,
            "opened": False,
            "changed": False,
        },
        "contacts": {
            "frozen_core": 0,
            "tokenizer": 0,
            "retriever": 0,
            "embedding_tool": 0,
            "http_or_socket": 0,
            "audio_decoder": 0,
            "scorer": 0,
            "gpu_hours": 0.0,
        },
        "information_boundary": {
            "query_text_read": False,
            "expected_calls_read": False,
            "task_annotations_read": False,
            "prior_outputs_read": False,
            "prior_scores_read": False,
            "test_annotations_read": False,
        },
        "offline_guard": {
            "outbound_connection_attempts": offline.count,
            "targets": [],
        },
        "decision": (
            "permit only separately preregistered packet preprocessing and "
            "ground qualification implementation"
        ),
        "engineering_scope": {
            "complete_manifest_outer_parallel_scoring": True,
            "dataset_sharding": False,
            "network_jitter_testing": False,
        },
    }
    result_path.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"result_sha256: {_sha256_file(result_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
