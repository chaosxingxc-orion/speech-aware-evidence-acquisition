"""Identity-only cohort construction for executable-ground qualification."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Sequence

from .a2t_contract_preserving_cohort import (
    CohortError,
    SelectedItem,
    query_block,
    select_block_disjoint,
)
from ..reproduction.sampling import split_identity_hash

SELECTION_NAMESPACE = "a2t-executable-ground-qualification-v1"
SPLIT_NAME = "A2T-GROUND-QUAL-104"
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

_LOWER_HEX_64 = re.compile(r"[0-9a-f]{64}")
_LOWER_HEX_40 = re.compile(r"[0-9a-f]{40}")


class GroundQualificationCohortError(RuntimeError):
    """The ground-qualification roster violated its frozen identity rule."""


@dataclass(frozen=True)
class GroundRosterSource:
    """Identity-only provenance for one excluded predecessor receipt."""

    receipt: str
    sha256: str
    split_identity_hash: str
    item_count: int
    query_block_count: int

    def validate(self) -> "GroundRosterSource":
        if not isinstance(self.receipt, str) or not self.receipt:
            raise GroundQualificationCohortError(
                "source receipt path must be non-empty"
            )
        for value, label in (
            (self.sha256, "source receipt SHA-256"),
            (self.split_identity_hash, "source split identity"),
        ):
            if not isinstance(value, str) or _LOWER_HEX_64.fullmatch(value) is None:
                raise GroundQualificationCohortError(
                    f"{label} must be lowercase 64-hex"
                )
        for value, label in (
            (self.item_count, "source item count"),
            (self.query_block_count, "source query-block count"),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise GroundQualificationCohortError(
                    f"{label} must be a non-negative integer"
                )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "item_count": self.item_count,
            "query_block_count": self.query_block_count,
            "receipt": self.receipt,
            "sha256": self.sha256,
            "split_identity_hash": self.split_identity_hash,
        }


def select_ground_roster(
    parent: Sequence[object],
    excluded_receipts: Sequence[Sequence[object]],
    *,
    tiers: Sequence[str] = TIERS,
    per_tier: int = PER_TIER,
    namespace: str = SELECTION_NAMESPACE,
) -> tuple[SelectedItem, ...]:
    """Exclude two disjoint predecessor block sets, then hash-select by tier."""

    frozen_exclusions = tuple(tuple(group) for group in excluded_receipts)
    if len(frozen_exclusions) != 2:
        raise GroundQualificationCohortError(
            "ground roster requires exactly two excluded receipts"
        )
    block_sets: list[set[str]] = []
    for group in frozen_exclusions:
        blocks: set[str] = set()
        for item in group:
            try:
                sample_id = getattr(item, "sample_id")
                media_relpath = getattr(item, "media_relpath")
                if not isinstance(sample_id, str) or sample_id.count(":") != 1:
                    raise GroundQualificationCohortError(
                        "excluded sample id must have the tier:integer form"
                    )
                tier, numeric = sample_id.split(":", 1)
                if not tier or not numeric.isdigit():
                    raise GroundQualificationCohortError(
                        "excluded sample id must have the tier:integer form"
                    )
                blocks.add(query_block(tier, media_relpath))
            except (AttributeError, CohortError) as error:
                raise GroundQualificationCohortError(str(error)) from error
        block_sets.append(blocks)
    if block_sets[0] & block_sets[1]:
        raise GroundQualificationCohortError("excluded receipts overlap by query block")
    flattened = tuple(item for group in frozen_exclusions for item in group)
    try:
        return select_block_disjoint(
            parent,
            flattened,
            tiers=tiers,
            per_tier=per_tier,
            namespace=namespace,
        )
    except CohortError as error:
        raise GroundQualificationCohortError(str(error)) from error


def _require_sha256(value: str, label: str) -> None:
    if not isinstance(value, str) or _LOWER_HEX_64.fullmatch(value) is None:
        raise GroundQualificationCohortError(f"{label} must be lowercase 64-hex")


def build_ground_roster_receipt(
    selected: Sequence[SelectedItem],
    *,
    split_name: str,
    namespace: str,
    parent_receipt: str,
    parent_receipt_sha256: str,
    parent_split_identity_hash: str,
    excluded_sources: Sequence[GroundRosterSource],
    materialization_study_commit: str,
    expected_tiers: Sequence[str] = TIERS,
    per_tier: int = PER_TIER,
) -> dict[str, object]:
    """Build a deterministic receipt containing only identity and media facts."""

    if not isinstance(split_name, str) or not split_name:
        raise GroundQualificationCohortError("split name must be non-empty")
    if not isinstance(namespace, str) or not namespace:
        raise GroundQualificationCohortError("selection namespace must be non-empty")
    if not isinstance(parent_receipt, str) or not parent_receipt:
        raise GroundQualificationCohortError("parent receipt path must be non-empty")
    _require_sha256(parent_receipt_sha256, "parent receipt SHA-256")
    _require_sha256(parent_split_identity_hash, "parent split identity")
    if (
        not isinstance(materialization_study_commit, str)
        or _LOWER_HEX_40.fullmatch(materialization_study_commit) is None
    ):
        raise GroundQualificationCohortError(
            "materialization study commit must be lowercase 40-hex"
        )
    sources = tuple(
        sorted(
            (source.validate() for source in excluded_sources),
            key=lambda item: item.receipt,
        )
    )
    if len(sources) != 2 or len({source.receipt for source in sources}) != 2:
        raise GroundQualificationCohortError(
            "receipt must bind exactly two distinct excluded sources"
        )

    frozen = tuple(sorted(selected, key=lambda item: (item.tier, item.sample_id)))
    tiers = tuple(expected_tiers)
    counts = Counter(item.tier for item in frozen)
    if counts != {tier: per_tier for tier in tiers}:
        raise GroundQualificationCohortError(
            "selected strata do not match the frozen tier allocation"
        )
    sample_ids = [item.sample_id for item in frozen]
    blocks = [item.query_block for item in frozen]
    if len(set(sample_ids)) != len(sample_ids) or len(set(blocks)) != len(blocks):
        raise GroundQualificationCohortError(
            "selected receipt must be unique by sample and query block"
        )
    items = [
        {
            "audio_seconds": item.audio_seconds,
            "audio_sha256": item.audio_sha256,
            "id": int(item.sample_id.split(":", 1)[1]),
            "key": f"audio2tool:{item.sample_id}",
            "media_relpath": item.media_relpath,
            "packet_id": item.sample_id.replace(":", "/"),
            "query_block": item.query_block,
            "query_idx": int(item.query_block.rsplit("-", 1)[1]),
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
            "Identity-only 13-per-tier deterministic hash selection from the "
            "already-exposed parent after excluding complete G1 and CPV2 query blocks."
        ),
        "excluded_sources": [source.as_json() for source in sources],
        "exposure": (
            "EXPOSED parent population; secondary discovery only. The separately "
            "proposed unexposed 400-item tier remains unopened."
        ),
        "items": items,
        "materialization_study_commit": materialization_study_commit,
        "parent_receipt": parent_receipt,
        "parent_receipt_sha256": parent_receipt_sha256,
        "parent_split_identity_hash": parent_split_identity_hash,
        "purpose": "Executable-ground qualification discovery.",
        "run_identity_hash": split_identity_hash(
            f"audio2tool/{sample_id}" for sample_id in sample_ids
        ),
        "schema": "saea-a2t-ground-qualification-subset-receipt-v1",
        "selection_namespace": namespace,
        "selection_proof": {
            "excluded_query_block_count": sum(
                source.query_block_count for source in sources
            ),
            "selected_query_block_count": len(blocks),
            "query_block_overlap_count": 0,
            "task_annotations_consumed": False,
            "prior_results_consumed": False,
            "test_annotations_consumed": False,
        },
        "split_identity_hash": split_identity_hash(
            f"audio2tool:{sample_id}" for sample_id in sample_ids
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
    "GroundQualificationCohortError",
    "GroundRosterSource",
    "build_ground_roster_receipt",
    "select_ground_roster",
]
