"""Build the identity-only G8B fixed16 roster from the exact G8 support remainder."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


NAMESPACE = "speech-aware-evidence-acquisition-g8b-action-support-fixed16-v1"
TIER_ORDER = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)


def rank_digest(sample_id: str) -> str:
    """Return the declared identity-only rank for one sample."""
    return hashlib.sha256((NAMESPACE + "\0" + sample_id).encode("ascii")).hexdigest()


def manifest_identity_hash(rows: list[dict[str, str]]) -> str:
    """Return the carrier-prefixed hash for the selected identities."""
    identities = sorted(f"audio2tool/{row['sample_id']}" for row in rows)
    return hashlib.sha256("\n".join(identities).encode("ascii")).hexdigest()


def build_roster(g8_path: Path) -> dict[str, Any]:
    """Select exactly two identities per frozen tier without reading task content."""
    document = json.loads(Path(g8_path).read_text(encoding="utf-8"))
    rows = [
        {"sample_id": row["sample_id"], "key": row["key"], "tier": row["tier"]}
        for row in document["support_remainder"]
    ]
    if len(rows) != 28 or len({row["sample_id"] for row in rows}) != 28:
        raise RuntimeError("G8B source must be the exact 28-row G8 support_remainder")
    if {row["tier"] for row in rows} != set(TIER_ORDER):
        raise RuntimeError("G8B source must contain the eight frozen Audio2Tool tiers")

    selected: list[dict[str, str]] = []
    support: list[dict[str, str]] = []
    for tier in TIER_ORDER:
        ranked = sorted(
            (row for row in rows if row["tier"] == tier),
            key=lambda row: (rank_digest(row["sample_id"]), row["sample_id"]),
        )
        if len(ranked) < 2:
            raise RuntimeError(f"G8B source tier {tier} contains fewer than two identities")
        enriched = [
            {**row, "selection_rank_sha256": rank_digest(row["sample_id"])}
            for row in ranked
        ]
        selected.extend(enriched[:2])
        support.extend(enriched[2:])

    selected.sort(key=lambda row: (TIER_ORDER.index(row["tier"]), row["sample_id"]))
    support.sort(key=lambda row: (TIER_ORDER.index(row["tier"]), row["sample_id"]))
    return {
        "selected": selected,
        "support_remainder": support,
        "selected_tier_counts": {
            tier: sum(row["tier"] == tier for row in selected) for tier in TIER_ORDER
        },
        "support_tier_counts": {
            tier: sum(row["tier"] == tier for row in support) for tier in TIER_ORDER
        },
        "manifest_split_identity_hash": manifest_identity_hash(selected),
    }


def make_receipt(root: Path) -> dict[str, object]:
    """Return the contact-free G8B identity receipt."""
    source = root / "docs/receipts/a2t/A2T-G8-ACTION-SUPPORT-FIXED16.json"
    roster = build_roster(source)
    return {
        "schema": "saea-a2t-g8b-action-support-fixed16-identity-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "date": "2026-09-03",
        "execution_profile": "model-free-check",
        "carrier": "audio2tool",
        "split_name": "A2T-G8B-ACTION-SUPPORT-FIXED16",
        "split_role": "discovery",
        "purpose": (
            "Prospective identity-only action-set reachability successor roster; not a "
            "policy-fitting surface and not a model-contact authorization."
        ),
        "source_receipt": str(source.relative_to(root)).replace("\\", "/"),
        "source_receipt_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_surface": "exact 28-row G8 support_remainder",
        "selection": {
            "namespace": NAMESPACE,
            "algorithm": (
                "Within each tier of the exact G8 support_remainder, sort by "
                "SHA-256(namespace NUL sample_id), then sample_id, and retain the first two."
            ),
            "source_count": 28,
            "selected_count": 16,
            "support_remainder_count": 12,
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
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(make_receipt(args.root), indent=2, ensure_ascii=True) + "\n"
    if args.stdout:
        print(rendered, end="")
        return 0
    output = args.output or args.root / "docs/receipts/a2t/A2T-G8B-ACTION-SUPPORT-FIXED16.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
