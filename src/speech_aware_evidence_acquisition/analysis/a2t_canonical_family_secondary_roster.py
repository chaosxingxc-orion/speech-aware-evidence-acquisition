"""Identity-only secondary fixed-eight roster construction for Audio2Tool."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

DEFAULT_NAMESPACE = "speech-aware-evidence-acquisition-canonical-family-action-ground-secondary-fixed8-v1"
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


def _rank(namespace: str, sample_id: str) -> str:
    return hashlib.sha256(f"{namespace}\0{sample_id}".encode("ascii")).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _identity_rows(document: Mapping[str, object]) -> list[dict[str, Any]]:
    """Extract identity and receipt metadata without reading task content or media."""
    items = document.get("items")
    selected = document.get("selected")
    tiers = document.get("tiers")
    if isinstance(items, list):
        values: list[object] = list(items)
    elif isinstance(selected, list):
        values = list(selected)
    elif isinstance(tiers, Mapping):
        values = [
            {**row, "tier": tier}
            for tier, tier_rows in tiers.items()
            if isinstance(tier_rows, list)
            for row in tier_rows
            if isinstance(row, Mapping)
        ]
    else:
        values = []
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, Mapping):
            continue
        sample_id = value.get("sample_id")
        tier = value.get("tier")
        key = value.get("key")
        if not all(isinstance(item, str) and item for item in (sample_id, tier, key)):
            continue
        if sample_id in seen:
            continue
        seen.add(sample_id)
        row = {"sample_id": sample_id, "tier": tier, "key": key}
        for field in (
            "id",
            "query_idx",
            "query_block",
            "packet_id",
            "audio_seconds",
            "audio_sha256",
            "media_relpath",
        ):
            if field in value:
                row[field] = value[field]
        rows.append(row)
    return rows


def _load_rows(path: Path) -> list[dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError(f"receipt must be a JSON object: {path}")
    return _identity_rows(document)


def select_rows(
    source_rows: Iterable[Mapping[str, Any]],
    excluded_ids: set[str],
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> list[dict[str, Any]]:
    """Select one identity per tier by a stable hash, independent of input order."""
    rows = [
        dict(row) for row in source_rows if row.get("sample_id") not in excluded_ids
    ]
    if any(row.get("tier") not in TIER_ORDER for row in rows):
        raise ValueError("source contains an unknown tier")
    selected: list[dict[str, Any]] = []
    for tier in TIER_ORDER:
        ranked = sorted(
            (row for row in rows if row.get("tier") == tier),
            key=lambda row: (
                _rank(namespace, str(row["sample_id"])),
                str(row["sample_id"]),
            ),
        )
        if not ranked:
            raise ValueError(f"tier {tier} has no eligible identity")
        selected.append(
            {
                **ranked[0],
                "selection_rank_sha256": _rank(namespace, str(ranked[0]["sample_id"])),
            }
        )
    blocks = [row.get("query_block") for row in selected]
    if all(isinstance(block, str) and block for block in blocks) and len(
        set(blocks)
    ) != len(blocks):
        raise ValueError("selected rows contain a duplicate query block")
    return selected


def _manifest_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    identities = sorted(f"audio2tool/{row['sample_id']}" for row in rows)
    return hashlib.sha256("\n".join(identities).encode("ascii")).hexdigest()


def _receipt_split_hash(rows: Sequence[Mapping[str, Any]]) -> str:
    identities = [str(row["key"]) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("receipt contains duplicate identity keys")
    return hashlib.sha256("\n".join(sorted(identities)).encode("ascii")).hexdigest()


def build_receipt(
    source_path: Path,
    exclusion_paths: Sequence[Path],
    *,
    namespace: str = DEFAULT_NAMESPACE,
) -> dict[str, object]:
    """Build a deterministic proposed receipt from identity-only JSON receipts."""
    source_rows = _load_rows(source_path)
    exclusions: list[dict[str, object]] = []
    excluded_ids: set[str] = set()
    for path in exclusion_paths:
        rows = _load_rows(path)
        excluded_ids.update(str(row["sample_id"]) for row in rows)
        exclusions.append(
            {
                "path": _display_path(path),
                "sha256": _file_sha256(path),
                "count": len(rows),
            }
        )
    selected = select_rows(source_rows, excluded_ids, namespace=namespace)
    eligible = [row for row in source_rows if row["sample_id"] not in excluded_ids]
    eligible_per_tier = {
        tier: sum(row["tier"] == tier for row in eligible) for tier in TIER_ORDER
    }
    selected_per_tier = {tier: 1 for tier in TIER_ORDER}
    duration = sum(float(row.get("audio_seconds", 0.0)) for row in selected)
    return {
        "schema": "saea-a2t-canonical-family-secondary-fixed8-proposed-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "date": "2026-09-03",
        "execution_profile": "model-free-check",
        "carrier": "audio2tool",
        "split_name": "A2T-CANONICAL-FAMILY-SECONDARY-FIXED8",
        "split_role": "discovery",
        "purpose": (
            "Identity-only secondary discovery roster for the canonical family "
            "proposal-content reachability screen; this receipt authorizes no contact."
        ),
        "status": "PROPOSED_IDENTITY_ONLY_NO_CONTACT_AUTHORIZATION",
        "contacts": {"model": 0, "scorer": 0, "network": 0, "audio": 0},
        "source": {
            "path": _display_path(source_path),
            "sha256": _file_sha256(source_path),
            "count": len(source_rows),
            "split_identity_hash": _receipt_split_hash(source_rows),
            "run_identity_hash": _manifest_hash(source_rows),
        },
        "exclusions": exclusions,
        "selection": {
            "namespace": namespace,
            "algorithm": "Within each tier after identity-only exclusions, sort by SHA-256(namespace NUL sample_id), then sample_id, and retain the first row.",
            "eligible_count": len(eligible),
            "eligible_per_tier": eligible_per_tier,
            "uses_task_text": False,
            "uses_gold": False,
            "uses_audio": False,
            "uses_outputs": False,
            "uses_scores": False,
            "uses_rewards": False,
            "uses_test": False,
            "uses_future_turns": False,
            "uses_model_or_tool": False,
            "uses_network_or_tokenizer_or_scorer": False,
        },
        "selected": selected,
        "count": len(selected),
        "selected_tier_counts": selected_per_tier,
        "selected_query_block_count": len({row.get("query_block") for row in selected}),
        "selected_audio_seconds_total": round(duration, 6),
        "split_identity_hash": _manifest_hash(selected),
    }


__all__ = ["DEFAULT_NAMESPACE", "TIER_ORDER", "build_receipt", "select_rows"]
