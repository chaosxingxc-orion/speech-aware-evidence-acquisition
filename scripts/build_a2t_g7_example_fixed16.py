"""Build the identity-only G7 fixed16 roster from the exact G6 remainder."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


NAMESPACE = "speech-aware-evidence-acquisition-g7-example-fixed16-v1"


def rank_digest(sample_id: str) -> str:
    return hashlib.sha256((NAMESPACE + "\0" + sample_id).encode("ascii")).hexdigest()


def manifest_identity_hash(rows: list[dict[str, str]]) -> str:
    ids = sorted(f"audio2tool/{row['sample_id']}" for row in rows)
    return hashlib.sha256("\n".join(ids).encode("ascii")).hexdigest()


def build_roster(g6_path: Path) -> dict[str, Any]:
    document = json.loads(Path(g6_path).read_text(encoding="utf-8"))
    tier_order = tuple(document["tier_order"])
    source = document["remainder"]
    rows = [
        {"sample_id": row["sample_id"], "key": row["key"], "tier": row["tier"]}
        for row in source
    ]
    if len(rows) != 60 or len({row["sample_id"] for row in rows}) != 60:
        raise RuntimeError("G7 source must be the exact 60-row G6 remainder")
    selected: list[dict[str, str]] = []
    support: list[dict[str, str]] = []
    for tier in tier_order:
        ranked = sorted(
            (row for row in rows if row["tier"] == tier),
            key=lambda row: (rank_digest(row["sample_id"]), row["sample_id"]),
        )
        enriched = [
            {**row, "selection_rank_sha256": rank_digest(row["sample_id"])}
            for row in ranked
        ]
        selected.extend(enriched[:2])
        support.extend(enriched[2:])
    selected.sort(key=lambda row: (tier_order.index(row["tier"]), row["sample_id"]))
    support.sort(key=lambda row: (tier_order.index(row["tier"]), row["sample_id"]))
    return {
        "selected": selected,
        "support_remainder": support,
        "selected_tier_counts": {
            tier: sum(row["tier"] == tier for row in selected) for tier in tier_order
        },
        "support_tier_counts": {
            tier: sum(row["tier"] == tier for row in support) for tier in tier_order
        },
        "manifest_split_identity_hash": manifest_identity_hash(selected),
    }


def make_receipt(root: Path) -> dict[str, object]:
    source = root / "docs/receipts/a2t/A2T-G6-FAMILY-SWEEP-FIXED16.json"
    roster = build_roster(source)
    return {
        "schema": "saea-a2t-g7-example-fixed16-identity-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "date": "2026-09-02",
        "execution_profile": "model-free-check",
        "carrier": "audio2tool",
        "split_name": "A2T-G7-EXAMPLE-FIXED16",
        "split_role": "discovery",
        "source_receipt": str(source.relative_to(root)).replace("\\", "/"),
        "source_receipt_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_surface": "exact 60-row G6 support remainder",
        "selection": {
            "namespace": NAMESPACE,
            "algorithm": "Within each tier of the exact G6 remainder, sort by SHA-256(namespace NUL sample_id), then sample_id, and retain the first two.",
            "source_count": 60,
            "selected_count": 16,
            "support_remainder_count": 44,
            "items_per_tier": 2,
            "fields_read": ["key", "sample_id", "tier"],
            "uses_task_text": False,
            "uses_audio": False,
            "uses_gold": False,
            "uses_outputs": False,
            "uses_scores": False,
            "uses_rewards": False,
            "uses_test": False,
            "uses_future_turns": False,
            "uses_model_or_tool": False,
            "uses_network_or_tokenizer_or_scorer": False,
        },
        **roster,
        "split_identity_hash": roster["manifest_split_identity_hash"],
        "status": "IDENTITY_FROZEN_NO_CONTACT_AUTHORIZATION",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.root / "docs/receipts/a2t/A2T-G7-EXAMPLE-FIXED16.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(make_receipt(args.root), indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
