"""Build G8C fixed12 from every identity in the exact G8B support remainder."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


EXPECTED_SOURCE_SCHEMA = "saea-a2t-g8b-action-support-fixed16-identity-receipt-v1"
EXPECTED_SOURCE_COUNT = 12


def manifest_identity_hash(rows: list[dict[str, str]]) -> str:
    """Return the carrier-prefixed hash for selected identities."""
    identities = sorted(f"audio2tool/{row['sample_id']}" for row in rows)
    return hashlib.sha256("\n".join(identities).encode("ascii")).hexdigest()


def _identity_rows(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise RuntimeError("G8C source violates exact G8B support semantics")
    rows: list[dict[str, str]] = []
    for row in value:
        if not isinstance(row, Mapping):
            raise RuntimeError("G8C source violates exact G8B support semantics")
        values = {field: row.get(field) for field in ("sample_id", "key", "tier")}
        if not all(isinstance(item, str) and item for item in values.values()):
            raise RuntimeError("G8C source violates exact G8B support semantics")
        rows.append(values)  # type: ignore[arg-type]
    return rows


def build_roster(g8b_path: Path) -> dict[str, Any]:
    """Retain the exact G8B support surface in its frozen source order."""
    document = json.loads(Path(g8b_path).read_text(encoding="utf-8"))
    selected = _identity_rows(document.get("support_remainder"))
    consumed = _identity_rows(document.get("selected"))
    selected_ids = [row["sample_id"] for row in selected]
    consumed_ids = {row["sample_id"] for row in consumed}
    if (
        document.get("schema") != EXPECTED_SOURCE_SCHEMA
        or len(selected) != EXPECTED_SOURCE_COUNT
        or len(set(selected_ids)) != EXPECTED_SOURCE_COUNT
        or set(selected_ids) & consumed_ids
        or document.get("selection", {}).get("support_remainder_count")
        != EXPECTED_SOURCE_COUNT
    ):
        raise RuntimeError("G8C source violates exact G8B support semantics")
    tier_counts: dict[str, int] = {}
    for row in selected:
        tier_counts[row["tier"]] = tier_counts.get(row["tier"], 0) + 1
    return {
        "selected": selected,
        "support_remainder": [],
        "source_count": EXPECTED_SOURCE_COUNT,
        "selected_count": EXPECTED_SOURCE_COUNT,
        "support_remainder_count": 0,
        "selected_tier_counts": tier_counts,
        "manifest_split_identity_hash": manifest_identity_hash(selected),
    }


def make_receipt(root: Path) -> dict[str, object]:
    """Return the contact-free G8C identity receipt."""
    source = root / "docs/receipts/a2t/A2T-G8B-ACTION-SUPPORT-FIXED16.json"
    roster = build_roster(source)
    return {
        "schema": "saea-a2t-g8c-action-support-fixed12-identity-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "date": "2026-09-03",
        "execution_profile": "model-free-check",
        "carrier": "audio2tool",
        "split_name": "A2T-G8C-ACTION-SUPPORT-FIXED12",
        "split_role": "discovery",
        "purpose": (
            "Prospective official-scoring successor over every untouched G8B support "
            "identity; not policy fitting and not model-contact authorization."
        ),
        "source_receipt": str(source.relative_to(root)).replace("\\", "/"),
        "source_receipt_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_surface": "exact 12-row G8B support_remainder",
        "selection": {
            "algorithm": "Retain every source row in frozen source order.",
            "source_count": EXPECTED_SOURCE_COUNT,
            "selected_count": EXPECTED_SOURCE_COUNT,
            "support_remainder_count": 0,
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
    output = args.output or args.root / "docs/receipts/a2t/A2T-G8C-ACTION-SUPPORT-FIXED12.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
