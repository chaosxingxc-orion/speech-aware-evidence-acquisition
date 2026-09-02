"""Build the identity-only G6 family-sweep roster without touching payload fields."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


NAMESPACE = "speech-aware-evidence-acquisition-g6-family-sweep-fixed16-v1"
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


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rank_digest(sample_id: str) -> str:
    return hashlib.sha256((NAMESPACE + "\0" + sample_id).encode("utf-8")).hexdigest()


def canonical_identity_hash(items: list[dict[str, str]]) -> str:
    lines = [f"{item['tier']}\t{item['sample_id']}\n" for item in items]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def manifest_identity_hash(items: list[dict[str, str]]) -> str:
    """Match data.splits: hash sorted ``audio2tool/<sample_id>`` lines, no final LF."""
    ids = [f"audio2tool/{item['sample_id']}" for item in items]
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def _identity_rows(path: Path, *, reserve: bool = False) -> list[dict[str, str]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    source = document["confirmation_reserve"]["items"] if reserve else document["items"]
    # Copy only identity fields. No task, audio, gold, output, score, or transcript field is read.
    return [{"sample_id": row["sample_id"], "key": row["key"], "tier": row["tier"]} for row in source]


def build_roster(g1_path: Path, g3_path: Path, g5_path: Path) -> dict[str, Any]:
    source_rows = _identity_rows(g1_path)
    excluded_rows = _identity_rows(g3_path) + _identity_rows(g3_path, reserve=True)
    g5 = json.loads(g5_path.read_text(encoding="utf-8"))
    excluded_rows.extend(
        {"sample_id": row["sample_id"], "key": row["key"], "tier": tier}
        for tier in TIER_ORDER
        for row in g5["tiers"][tier]
    )
    excluded_ids = {row["sample_id"] for row in excluded_rows}
    eligible = [row for row in source_rows if row["sample_id"] not in excluded_ids]
    by_tier: dict[str, list[dict[str, str]]] = {tier: [] for tier in TIER_ORDER}
    for row in eligible:
        by_tier[row["tier"]].append(row)
    selected: list[dict[str, str]] = []
    remainder: list[dict[str, str]] = []
    for tier in TIER_ORDER:
        ranked = sorted(by_tier[tier], key=lambda row: (rank_digest(row["sample_id"]), row["sample_id"]))
        for row in ranked[:2]:
            selected.append({**row, "selection_rank_sha256": rank_digest(row["sample_id"])})
        remainder.extend({**row, "selection_rank_sha256": rank_digest(row["sample_id"])} for row in ranked[2:])
    selected.sort(key=lambda row: (TIER_ORDER.index(row["tier"]), row["sample_id"]))
    remainder.sort(key=lambda row: (TIER_ORDER.index(row["tier"]), row["sample_id"]))
    return {
        "selected": selected,
        "remainder": remainder,
        "eligible_count": len(eligible),
        "selected_tier_counts": {tier: sum(row["tier"] == tier for row in selected) for tier in TIER_ORDER},
        "remainder_tier_counts": {tier: sum(row["tier"] == tier for row in remainder) for tier in TIER_ORDER},
        "selection_identity_hash": canonical_identity_hash(selected),
        "manifest_split_identity_hash": manifest_identity_hash(selected),
    }


def make_receipt(root: Path) -> dict[str, Any]:
    g1 = root / "docs/receipts/a2t/A2T-G1-104.json"
    g3 = root / "docs/receipts/a2t/A2T-G3-PILOT-40.json"
    g5 = root / "docs/receipts/a2t/A2T-G5-FIXED16-IDENTITY.json"
    roster = build_roster(g1, g3, g5)
    return {
        "schema": "saea-a2t-g6-family-sweep-fixed16-identity-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "date": "2026-09-02",
        "execution_profile": "model-free-check",
        "carrier": "audio2tool",
        "split_name": "A2T-G6-FAMILY-SWEEP-FIXED16",
        "split_role": "discovery",
        "purpose": "Prospective identity-only G6 family-sweep roster; this receipt authorizes no model, tool, network, scorer, audio, task, gold, output, reward, test, or future-turn contact.",
        "source_hashes": {"g1": file_sha256(g1), "g3": file_sha256(g3), "g5": file_sha256(g5)},
        "tier_order": list(TIER_ORDER),
        "selection": {
            "namespace": NAMESPACE,
            "algorithm": "Read only identity fields from G1, G3 pilot and G3 confirmation-reserve authorities, and G5 tier identities. Exclude every G3/G4 and G5 identity. Within each tier, sort by SHA-256(UTF-8(namespace || NUL || sample_id)), then sample_id, and retain the first two.",
            "source_count": 104,
            "excluded_authority_identity_count": 56,
            "eligible_count": 76,
            "items_per_tier": 2,
            "uses_task_text": False, "uses_audio": False, "uses_gold": False,
            "uses_outputs": False, "uses_scores": False, "uses_rewards": False,
            "uses_test": False, "uses_future_turns": False, "uses_model_or_tool": False,
            "uses_network_or_tokenizer_or_scorer": False,
        },
        "selected": roster["selected"],
        "remainder": roster["remainder"],
        "selected_tier_counts": roster["selected_tier_counts"],
        "remainder_tier_counts": roster["remainder_tier_counts"],
        "selection_identity_hash": roster["selection_identity_hash"],
        "manifest_split_identity_hash": roster["manifest_split_identity_hash"],
        "split_identity_hash": roster["manifest_split_identity_hash"],
        "manifest_binding": "Use manifest_split_identity_hash (the data.splits carrier-prefixed convention) for ExecutionPlan, protocol_hash, VerifiedSplit.identity_hash, and the manifest. Do not use selection_identity_hash.",
        "status": "IDENTITY_FROZEN_NO_CONTACT_AUTHORIZATION",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    output = args.output or args.root / "docs/receipts/a2t/A2T-G6-FAMILY-SWEEP-FIXED16.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(make_receipt(args.root), indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
