#!/usr/bin/env python3
"""Build an identity-only scorer roster for the SELECT/FILL discovery flight."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Mapping


REPO = Path(__file__).resolve().parents[1]
DEFAULT_ROSTER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-03-a2t-select-fill-fresh-roster-v1"
    / "flight-roster-receipt.json"
)
DEFAULT_D1 = (
    REPO
    / "docs/receipts/artifacts"
    / "d1-a2t-semantic-agentloop-select-fill-104.json"
)
DEFAULT_OUTPUT = (
    REPO
    / "docs/receipts/probe-samples"
    / "select-fill-agentloop-104-postseal-scoring.json"
)
EXPECTED_SPLIT = "bcbad5405aa8522ff53a91d624c54a909e01f8a31612b5165844b8e2cbca6eb3"
EXPECTED_COUNT = 104
EXPECTED_TIERS = tuple(f"tier{index}_{suffix}" for index, suffix in (
    (1, "direct"),
    (2, "parametric"),
    (3, "multi_intent"),
    (4, "implicit"),
    (5, "needle"),
    (6, "correction"),
    (7, "multiturn"),
    (8, "intent_blending"),
))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}") from error
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return value


def build_receipt(roster_path: Path, d1_path: Path) -> dict[str, object]:
    """Return a roster-derived receipt without opening task data or labels."""

    roster_path = Path(roster_path)
    d1_path = Path(d1_path)
    roster = _load(roster_path, "roster")
    items = roster.get("items")
    if (
        roster.get("schema") != "saea-a2t-agentloop-flight-roster-receipt-v1"
        or roster.get("carrier") != "audio2tool"
        or roster.get("split_role") != "discovery"
        or roster.get("split_identity_hash") != EXPECTED_SPLIT
        or roster.get("count") != EXPECTED_COUNT
        or not isinstance(items, list)
        or len(items) != EXPECTED_COUNT
    ):
        raise ValueError("roster identity is invalid")

    d1 = _load(d1_path, "D1 media receipt")
    manifest = d1.get("manifest")
    if (
        d1.get("schema") != "saea-d1-media-supplement-v1"
        or d1.get("carrier_lock_key") != "audio2tool"
        or d1.get("source_binding_sha256") != _sha256_file(roster_path)
        or d1.get("count") != EXPECTED_COUNT
        or not isinstance(manifest, list)
        or len(manifest) != EXPECTED_COUNT
    ):
        raise ValueError("D1 media receipt is not bound to the roster")
    d1_ids = {entry.get("id") for entry in manifest if isinstance(entry, Mapping)}

    output_items: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("roster item must be an object")
        sample_id = item.get("sample_id")
        tier = item.get("tier")
        key = item.get("key")
        item_id = item.get("id")
        query_idx = item.get("query_idx")
        if (
            not isinstance(sample_id, str)
            or sample_id in seen
            or not isinstance(tier, str)
            or tier not in EXPECTED_TIERS
            or sample_id.split(":", 1)[0] != tier
            or key != f"audio2tool:{sample_id}"
            or type(item_id) is not int
            or type(query_idx) is not int
            or sample_id not in d1_ids
        ):
            raise ValueError("roster item identity is invalid")
        seen.add(sample_id)
        output_items.append(
            {"id": item_id, "key": key, "query_idx": query_idx, "tier": tier}
        )
    output_items.sort(key=lambda item: (str(item["tier"]), int(item["id"])))
    strata = Counter(str(item["tier"]) for item in output_items)
    if dict(strata) != {tier: 13 for tier in EXPECTED_TIERS}:
        raise ValueError("roster must contain exactly 13 rows per tier")
    slash_ids = sorted(f"audio2tool/{sample_id}" for sample_id in seen)
    return {
        "authority": (
            "The 2026-09-03 SELECT/FILL preregistration fixes these 104 "
            "discovery identities before model contact and permits official scoring "
            "only after all four answer manifests seal."
        ),
        "carrier": "audio2tool",
        "d1_media_identity_receipt": (
            "docs/receipts/artifacts/"
            "d1-a2t-semantic-agentloop-select-fill-104.json"
        ),
        "d1_media_identity_receipt_sha256": _sha256_file(d1_path),
        "design": (
            "Identity-only additive receipt derived from the frozen precontact "
            "roster; it changes no scorer metric, label interpretation, prediction, "
            "arm, or sample selection."
        ),
        "items": output_items,
        "n_items": EXPECTED_COUNT,
        "probe": "select-fill-agentloop-104-postseal-scoring",
        "run_identity_hash": hashlib.sha256("\n".join(slash_ids).encode()).hexdigest(),
        "run_identity_hash_basis": (
            "sha256 over LF-joined sorted audio2tool/<sample_id> identities; "
            "the bundle verifier convention"
        ),
        "source_roster": (
            "docs/checks/speech-aware-evidence-acquisition/"
            "2026-09-03-a2t-select-fill-fresh-roster-v1/flight-roster-receipt.json"
        ),
        "source_roster_sha256": _sha256_file(roster_path),
        "split_identity_hash": EXPECTED_SPLIT,
        "split_identity_hash_basis": (
            "sha256 over LF-joined sorted receipt item key values; "
            "the Audio2Tool roster-integrity convention"
        ),
        "split_role": "discovery",
        "strata_counts": dict(strata),
        "target_gold_opened_before_receipt": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roster", type=Path, default=DEFAULT_ROSTER)
    parser.add_argument("--d1", type=Path, default=DEFAULT_D1)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    receipt = build_receipt(args.roster, args.d1)
    payload = json.dumps(receipt, ensure_ascii=True, indent=2) + "\n"
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        temporary.write_text(payload, encoding="ascii", newline="\n")
        temporary.replace(args.output)
    print(
        json.dumps(
            {
                "n_items": receipt["n_items"],
                "output": str(args.output),
                "output_sha256": hashlib.sha256(payload.encode("ascii")).hexdigest(),
                "run_identity_hash": receipt["run_identity_hash"],
                "written": args.write,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
