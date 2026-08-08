#!/usr/bin/env python3
"""Build pre-registered sample-identity lists for probes R1/R2/R5 (P0.D).

Model-free: reads carrier METADATA only (tier/category manifests), never
audio bytes, never gold answers — identity lists carry item keys + strata
only. Runs in WSL2 (data root on /mnt/e). Output: docs/receipts/
probe-samples/*.json with the split-identity hash per probe (E0 convention:
SHA-256 over sorted carrier-prefixed keys).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from speech_aware_evidence_acquisition.reproduction.sampling import (  # noqa: E402
    split_identity_hash,
    stratified_sample,
)

SEED = 20260807
DATA_ROOT = Path(
    os.environ.get(
        "SPEECHRL_DATA_DIR", "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data"
    )
)
OUT_DIR = REPO_ROOT / "docs" / "receipts" / "probe-samples"

VAB_COMPLEX_CATEGORIES = ("parallel_tool", "seqdep_tool", "multi_turn")


def write_receipt(name: str, payload: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"wrote {path.relative_to(REPO_ROOT)}  items={len(payload['items'])}  "
          f"hash={payload['split_identity_hash'][:16]}…")


def build_r1_audio2tool() -> None:
    base = DATA_ROOT / "datasets/audio2tool/public"
    pool: list[dict] = []
    tier_files = sorted(base.glob("tier*_data/*.json"))
    if not tier_files:
        raise FileNotFoundError(f"no tier manifests under {base}")
    for tier_file in tier_files:
        entries = json.loads(tier_file.read_text(encoding="utf-8"))
        for entry in entries:
            pool.append(
                {
                    "key": f"audio2tool:{entry['tier']}:{int(entry['id']):06d}",
                    "tier": entry["tier"],
                    "id": entry["id"],
                    "query_idx": entry.get("query_idx"),
                }
            )
    sample = stratified_sample(
        pool, per_stratum=50, seed=SEED, stratum_of=lambda x: x["tier"], key_of=lambda x: x["key"]
    )
    strata: dict[str, int] = {}
    for item in sample:
        strata[item["tier"]] = strata.get(item["tier"], 0) + 1
    write_receipt(
        "r1-audio2tool-sample.json",
        {
            "probe": "R1-audio2tool-direct",
            "carrier": "audio2tool",
            "seed": SEED,
            "design": "50 per tier, seeded, order-independent; success/audio-existence cross-check deferred to run prep",
            "pool_size": len(pool),
            "strata_counts": strata,
            "items": sample,
            "split_identity_hash": split_identity_hash([item["key"] for item in sample]),
            "split_role": "discovery",
        },
    )


def build_r2_bba() -> None:
    meta = DATA_ROOT / "datasets/big-bench-audio/metadata.jsonl"
    pool = []
    with meta.open(encoding="utf-8") as fh:
        for line in fh:
            entry = json.loads(line)
            pool.append(
                {
                    "key": f"big-bench-audio:{int(entry['id']):04d}",
                    "id": entry["id"],
                    "category": entry["category"],
                    "file_name": entry["file_name"],
                }
            )
    sample = stratified_sample(
        pool, per_stratum=50, seed=SEED, stratum_of=lambda x: x["category"], key_of=lambda x: x["key"]
    )
    strata: dict[str, int] = {}
    for item in sample:
        strata[item["category"]] = strata.get(item["category"], 0) + 1
    write_receipt(
        "r2-bba-sample.json",
        {
            "probe": "R2-bba-cascade-vs-direct",
            "carrier": "big-bench-audio",
            "seed": SEED,
            "design": "50 per BBH category x 4, paired arms on the same items; official_answer deliberately NOT copied here",
            "pool_size": len(pool),
            "strata_counts": strata,
            "items": sample,
            "split_identity_hash": split_identity_hash([item["key"] for item in sample]),
            "split_role": "discovery",
        },
    )


def build_r5_vab() -> None:
    """Sample from the top-level metadata.csv — the one index that is uniform
    across categories (per-category data dirs differ in layout). EN items are
    those whose audio path sits under an ``original_english`` directory."""
    import csv

    meta = DATA_ROOT / "datasets/voiceagentbench/metadata.csv"
    by_cat_variant: dict[str, dict[str, list[dict]]] = {}
    with meta.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            category = row["category"]
            file_name = row["file_name"]
            if category not in VAB_COMPLEX_CATEGORIES:
                continue
            parts = file_name.split("/")
            variant = parts[2] if len(parts) > 2 else ""
            if variant not in ("original_english", "english"):
                continue
            by_cat_variant.setdefault(category, {}).setdefault(variant, []).append(
                {
                    "key": f"voiceagentbench:{category}:{file_name}",
                    "id": row["id"],
                    "category": category,
                    "variant": variant,
                    "file_name": file_name,
                }
            )
    pool = []
    variant_chosen: dict[str, str] = {}
    for category in VAB_COMPLEX_CATEGORIES:
        variants = by_cat_variant.get(category, {})
        if not variants:
            raise RuntimeError(f"no EN rows for category {category}")
        # multi_turn/seqdep_tool ship only the 'english' variant; parallel_tool
        # ships both — prefer original_english where it exists, and record the
        # choice so arms stay variant-homogeneous within a stratum.
        chosen = "original_english" if "original_english" in variants else "english"
        variant_chosen[category] = chosen
        pool.extend(variants[chosen])
    sample = stratified_sample(
        pool, per_stratum=50, seed=SEED, stratum_of=lambda x: x["category"], key_of=lambda x: x["key"]
    )
    strata: dict[str, int] = {}
    for item in sample:
        strata[item["category"]] = strata.get(item["category"], 0) + 1
    write_receipt(
        "r5-vab-sample.json",
        {
            "probe": "R5-vab-oneshot",
            "carrier": "voiceagentbench",
            "seed": SEED,
            "design": "50 per EN complex stratum (parallel_tool/seqdep_tool/multi_turn), paired arms; strata smaller than 50 taken whole",
            "en_variant_per_stratum": variant_chosen,
            "pool_size": len(pool),
            "strata_counts": strata,
            "items": sample,
            "split_identity_hash": split_identity_hash([item["key"] for item in sample]),
            "split_role": "discovery",
        },
    )


def main() -> int:
    build_r1_audio2tool()
    build_r2_bba()
    build_r5_vab()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
