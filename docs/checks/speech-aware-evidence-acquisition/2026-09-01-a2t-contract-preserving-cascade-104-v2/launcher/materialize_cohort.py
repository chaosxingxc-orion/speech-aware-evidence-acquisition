"""Materialize the identity-only A2T-CPV2-104 receipt exactly once."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis.a2t_contract_preserving_cohort import (  # noqa: E402
    PER_TIER,
    SELECTION_NAMESPACE,
    SPLIT_NAME,
    TIERS,
    build_receipt,
    query_block,
    select_block_disjoint,
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

PARENT_RELPATH = Path("docs/receipts/probe-samples/r1-audio2tool-sample.json")
EXCLUDED_RELPATH = Path("docs/receipts/a2t/A2T-G1-104.json")
OUTPUT_RELPATH = Path("docs/receipts/a2t/A2T-CPV2-104.json")


@dataclass(frozen=True)
class ReceiptCandidate:
    sample_id: str
    media_relpath: str
    audio_seconds: float
    audio_sha256: str


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"receipt must be a JSON object: {path}")
    return value


def main() -> int:
    study_commit = require_clean_study_repo(REPO)
    parent_path = REPO / PARENT_RELPATH
    excluded_path = REPO / EXCLUDED_RELPATH
    output_path = REPO / OUTPUT_RELPATH
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite cohort receipt: {output_path}")
    parent_document = _read_object(parent_path)
    excluded_document = _read_object(excluded_path)
    parent_items = parent_document.get("items")
    excluded_items = excluded_document.get("items")
    if not isinstance(parent_items, list) or len(parent_items) != 400:
        raise RuntimeError("parent receipt is not the frozen 400-item population")
    if not isinstance(excluded_items, list) or len(excluded_items) != 104:
        raise RuntimeError("excluded receipt is not A2T-G1-104")

    lock = load_lock(umbrella_lock_path())
    root = data_root()
    parent_samples = tuple(
        Audio2ToolAdapter(lock, root, repo_root=REPO).load_split("discovery")
    )
    parent_ids = {
        f"{item['tier']}:{int(item['id']):06d}" for item in parent_items
    }
    if len(parent_samples) != 400 or {
        sample.sample_id for sample in parent_samples
    } != parent_ids:
        raise RuntimeError("runtime-legal parent identities drifted from the parent receipt")

    excluded_candidates = tuple(
        ReceiptCandidate(
            sample_id=str(item["sample_id"]),
            media_relpath=str(item["media_relpath"]),
            audio_seconds=float(item["audio_seconds"]),
            audio_sha256=str(item["audio_sha256"]),
        )
        for item in excluded_items
    )
    selected = select_block_disjoint(
        parent_samples,
        excluded_candidates,
        tiers=TIERS,
        per_tier=PER_TIER,
        namespace=SELECTION_NAMESPACE,
    )
    excluded_blocks = tuple(
        sorted(
            query_block(str(item["tier"]), str(item["media_relpath"]))
            for item in excluded_items
        )
    )
    parent_split_identity = parent_document.get("split_identity_hash")
    if not isinstance(parent_split_identity, str):
        raise RuntimeError("parent receipt lacks a split identity hash")
    receipt = build_receipt(
        selected,
        split_name=SPLIT_NAME,
        namespace=SELECTION_NAMESPACE,
        parent_receipt=PARENT_RELPATH.as_posix(),
        parent_receipt_sha256=_sha256_file(parent_path),
        parent_split_identity_hash=parent_split_identity,
        excluded_receipt=EXCLUDED_RELPATH.as_posix(),
        excluded_receipt_sha256=_sha256_file(excluded_path),
        excluded_query_blocks=excluded_blocks,
        expected_tiers=TIERS,
        per_tier=PER_TIER,
    )
    receipt["materialization_study_commit"] = study_commit
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "output": str(output_path),
                "count": receipt["count"],
                "audio_seconds_total": receipt["audio_seconds_total"],
                "split_identity_hash": receipt["split_identity_hash"],
                "run_identity_hash": receipt["run_identity_hash"],
                "receipt_sha256": _sha256_file(output_path),
                "gold_read": False,
                "prior_outputs_read": False,
                "prior_scores_read": False,
                "test_read": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
