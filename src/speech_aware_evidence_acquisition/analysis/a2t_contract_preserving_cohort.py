"""Identity-only construction for the A2T contract-preserving v2 cohort.

The selector accepts runtime-legal media descriptors only. It never accepts query
text, expected calls, model outputs, scores, or test annotations.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from ..reproduction.sampling import split_identity_hash

SELECTION_NAMESPACE = "a2t-contract-preserving-cascade-v2"
SPLIT_NAME = "A2T-CPV2-104"
TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)
PER_TIER = 13

_QUERY_BLOCK = re.compile(r"(?:(?<=/)|^)query_(\d+)(?=/|$)")
_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}")


class CohortError(RuntimeError):
    """A runtime-legal identity or selection invariant failed."""


@dataclass(frozen=True)
class SelectedItem:
    sample_id: str
    tier: str
    media_relpath: str
    audio_seconds: float
    audio_sha256: str
    query_block: str
    selection_rank_sha256: str


def query_block(tier: str, media_relpath: str) -> str:
    """Return the tier-scoped query block encoded by one media path."""

    if not isinstance(tier, str) or not tier:
        raise CohortError("tier must be non-empty text")
    if not isinstance(media_relpath, str) or not media_relpath:
        raise CohortError("media path must be non-empty text")
    matches = _QUERY_BLOCK.findall(media_relpath.replace("\\", "/"))
    if len(matches) != 1:
        raise CohortError("media path must contain exactly one query block")
    return f"{tier}:query-{int(matches[0]):05d}"


def _tier(sample_id: object) -> str:
    if not isinstance(sample_id, str) or sample_id.count(":") != 1:
        raise CohortError("sample_id must have the tier:integer form")
    tier, numeric = sample_id.split(":", 1)
    if not tier or not numeric.isdigit():
        raise CohortError("sample_id must have the tier:integer form")
    return tier


def _audio_sha256(candidate: object) -> str:
    direct = getattr(candidate, "audio_sha256", None)
    if isinstance(direct, str):
        value = direct
    else:
        audio_ref = getattr(candidate, "audio_ref", None)
        value = getattr(audio_ref, "sha256", None)
    if not isinstance(value, str) or _LOWER_HEX_64.fullmatch(value) is None:
        raise CohortError("candidate audio SHA-256 must be lowercase 64-hex")
    return value


def _rank(namespace: str, sample_id: str) -> str:
    return hashlib.sha256(f"{namespace}\0{sample_id}".encode("utf-8")).hexdigest()


def _selected(candidate: object, namespace: str) -> SelectedItem:
    sample_id = getattr(candidate, "sample_id", None)
    tier = _tier(sample_id)
    media_relpath = getattr(candidate, "media_relpath", None)
    audio_seconds = getattr(candidate, "audio_seconds", None)
    if not isinstance(media_relpath, str) or not media_relpath:
        raise CohortError("candidate media path must be non-empty text")
    if isinstance(audio_seconds, bool) or not isinstance(audio_seconds, (int, float)):
        raise CohortError("candidate audio seconds must be numeric")
    duration = float(audio_seconds)
    if not 0.0 < duration < float("inf"):
        raise CohortError("candidate audio seconds must be finite and positive")
    return SelectedItem(
        sample_id=sample_id,
        tier=tier,
        media_relpath=media_relpath,
        audio_seconds=duration,
        audio_sha256=_audio_sha256(candidate),
        query_block=query_block(tier, media_relpath),
        selection_rank_sha256=_rank(namespace, sample_id),
    )


def select_block_disjoint(
    parent: Sequence[object],
    excluded: Sequence[object],
    *,
    tiers: Sequence[str] = TIERS,
    per_tier: int = PER_TIER,
    namespace: str = SELECTION_NAMESPACE,
) -> tuple[SelectedItem, ...]:
    """Select a balanced cohort after excluding complete query blocks."""

    frozen_tiers = tuple(tiers)
    if (
        not frozen_tiers
        or len(set(frozen_tiers)) != len(frozen_tiers)
        or any(not isinstance(tier, str) or not tier for tier in frozen_tiers)
    ):
        raise CohortError("tiers must be unique non-empty strings")
    if isinstance(per_tier, bool) or not isinstance(per_tier, int) or per_tier < 1:
        raise CohortError("per_tier must be a positive integer")
    if not isinstance(namespace, str) or not namespace:
        raise CohortError("selection namespace must be non-empty text")

    parent_items = tuple(_selected(candidate, namespace) for candidate in parent)
    parent_ids = [item.sample_id for item in parent_items]
    if len(set(parent_ids)) != len(parent_ids):
        raise CohortError("duplicate parent sample identity")
    excluded_items = tuple(_selected(candidate, namespace) for candidate in excluded)
    excluded_blocks = {item.query_block for item in excluded_items}

    selected: list[SelectedItem] = []
    for tier in frozen_tiers:
        eligible = [
            item
            for item in parent_items
            if item.tier == tier and item.query_block not in excluded_blocks
        ]
        by_block: dict[str, SelectedItem] = {}
        for item in sorted(
            eligible,
            key=lambda value: (value.selection_rank_sha256, value.sample_id),
        ):
            by_block.setdefault(item.query_block, item)
        ranked_blocks = sorted(
            by_block.values(),
            key=lambda value: (value.selection_rank_sha256, value.sample_id),
        )
        if len(ranked_blocks) < per_tier:
            raise CohortError(
                f"tier {tier!r} needs {per_tier} unique blocks but has {len(ranked_blocks)}"
            )
        selected.extend(ranked_blocks[:per_tier])

    result = tuple(sorted(selected, key=lambda item: (item.tier, item.sample_id)))
    expected_count = len(frozen_tiers) * per_tier
    if len(result) != expected_count or len({item.query_block for item in result}) != len(
        result
    ):
        raise CohortError("selected cohort is not complete and block-unique")
    return result


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or _LOWER_HEX_64.fullmatch(value) is None:
        raise CohortError(f"{label} must be lowercase 64-hex")


def build_receipt(
    selected: Sequence[SelectedItem],
    *,
    split_name: str,
    namespace: str,
    parent_receipt: str,
    parent_receipt_sha256: str,
    parent_split_identity_hash: str,
    excluded_receipt: str,
    excluded_receipt_sha256: str,
    excluded_query_blocks: Sequence[str],
    expected_tiers: Sequence[str] = TIERS,
    per_tier: int = PER_TIER,
) -> dict[str, object]:
    """Build the auditable receipt without accepting any task-answer field."""

    frozen = tuple(selected)
    tiers = tuple(expected_tiers)
    counts = Counter(item.tier for item in frozen)
    expected_counts = {tier: per_tier for tier in tiers}
    if counts != expected_counts:
        raise CohortError("selected strata do not match the frozen tier allocation")
    ids = [item.sample_id for item in frozen]
    blocks = [item.query_block for item in frozen]
    excluded_blocks = set(excluded_query_blocks)
    if len(set(ids)) != len(ids) or len(set(blocks)) != len(blocks):
        raise CohortError("receipt items must be unique by sample and query block")
    overlap = set(blocks) & excluded_blocks
    if overlap:
        raise CohortError("selected receipt overlaps an excluded query block")
    _require_sha256(parent_receipt_sha256, "parent receipt SHA-256")
    _require_sha256(parent_split_identity_hash, "parent split identity hash")
    _require_sha256(excluded_receipt_sha256, "excluded receipt SHA-256")

    items = [
        {
            "audio_seconds": item.audio_seconds,
            "audio_sha256": item.audio_sha256,
            "id": int(item.sample_id.split(":", 1)[1]),
            "key": f"audio2tool:{item.sample_id}",
            "media_relpath": item.media_relpath,
            "packet_id": item.sample_id.replace(":", "/"),
            "query_block": item.query_block,
            "sample_id": item.sample_id,
            "selection_rank_sha256": item.selection_rank_sha256,
            "tier": item.tier,
        }
        for item in frozen
    ]
    return {
        "audio_seconds_total": round(sum(item.audio_seconds for item in frozen), 6),
        "carrier": "audio2tool",
        "count": len(frozen),
        "design": (
            "Query-block-disjoint 13-per-tier deterministic hash selection from "
            "the exposed parent 400 after excluding every A2T-G1-104 query block."
        ),
        "excluded_receipt": excluded_receipt,
        "excluded_receipt_sha256": excluded_receipt_sha256,
        "exposure": (
            "EXPOSED parent population; this receipt is a secondary discovery cohort "
            "and cannot carry a confirmatory or generality claim."
        ),
        "items": items,
        "parent_receipt": parent_receipt,
        "parent_receipt_sha256": parent_receipt_sha256,
        "parent_split_identity_hash": parent_split_identity_hash,
        "purpose": "Contract-preserving self-transcript cascade v2 discovery.",
        "run_identity_hash": split_identity_hash(
            f"audio2tool/{sample_id}" for sample_id in ids
        ),
        "schema": "saea-a2t-block-disjoint-subset-receipt-v2",
        "selection_namespace": namespace,
        "selection_proof": {
            "excluded_query_block_count": len(excluded_blocks),
            "selected_query_block_count": len(blocks),
            "query_block_overlap_count": 0,
            "gold_used": False,
            "prior_outputs_used": False,
            "prior_scores_used": False,
            "test_used": False,
        },
        "split_identity_hash": split_identity_hash(
            f"audio2tool:{sample_id}" for sample_id in ids
        ),
        "split_name": split_name,
        "split_role": "discovery",
        "strata_counts": dict(sorted(counts.items())),
        "study": "speech-aware-evidence-acquisition",
    }


__all__ = [
    "PER_TIER",
    "SELECTION_NAMESPACE",
    "SPLIT_NAME",
    "TIERS",
    "CohortError",
    "SelectedItem",
    "build_receipt",
    "query_block",
    "select_block_disjoint",
]
