"""Identity-only roster construction for the bounded A2T G3 pilot.

The pilot is selected only from media identities already exposed by the G1,
CPV2, and ground-qualification discovery cohorts. Task text, transcripts,
expected calls, model outputs, and scores are neither accepted nor copied into
the selection surface.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..reproduction.sampling import split_identity_hash
from .a2t_contract_preserving_cohort import query_block

G3_SELECTION_NAMESPACE = "a2t-g3-human-hierarchical-pilot-v1"
G3_SPLIT_NAME = "A2T-G3-PILOT-40"
G3_PER_TIER = 5
G3_TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)
G3_EXPOSED_RECEIPTS = (
    "docs/receipts/a2t/A2T-G1-104.json",
    "docs/receipts/a2t/A2T-CPV2-104.json",
    "docs/receipts/a2t/A2T-GROUND-QUAL-104.json",
)
G3_PARENT_RECEIPT = "docs/receipts/probe-samples/r1-audio2tool-sample.json"


class PilotRosterError(RuntimeError):
    """The identity-only source geometry or selection proof is invalid."""


@dataclass(frozen=True)
class _ExposedIdentity:
    sample_id: str
    tier: str
    item_id: int
    key: str
    media_relpath: str
    audio_seconds: float
    audio_sha256: str
    query_block: str
    selection_rank_sha256: str


@dataclass(frozen=True)
class _ParentIdentity:
    sample_id: str
    tier: str
    item_id: int
    key: str
    query_idx: int


def _rank(sample_id: str) -> str:
    return hashlib.sha256(
        f"{G3_SELECTION_NAMESPACE}\0{sample_id}".encode("utf-8")
    ).hexdigest()


def _sample_id(tier: object, item_id: object) -> tuple[str, str, int]:
    if not isinstance(tier, str) or tier not in G3_TIERS:
        raise PilotRosterError(f"invalid Audio2Tool tier {tier!r}")
    if isinstance(item_id, bool) or not isinstance(item_id, int) or item_id < 0:
        raise PilotRosterError(f"invalid Audio2Tool item id {item_id!r}")
    return f"{tier}:{item_id:06d}", tier, item_id


def _parent_identity(item: object) -> _ParentIdentity:
    if not isinstance(item, Mapping):
        raise PilotRosterError("parent receipt item must be an object")
    sample_id, tier, item_id = _sample_id(item.get("tier"), item.get("id"))
    key = item.get("key")
    query_idx = item.get("query_idx")
    if key != f"audio2tool:{sample_id}":
        raise PilotRosterError(f"parent key does not match {sample_id}")
    if isinstance(query_idx, bool) or not isinstance(query_idx, int):
        raise PilotRosterError(f"parent query_idx is invalid for {sample_id}")
    return _ParentIdentity(sample_id, tier, item_id, key, query_idx)


def _exposed_identity(item: object) -> _ExposedIdentity:
    if not isinstance(item, Mapping):
        raise PilotRosterError("exposed receipt item must be an object")
    sample_id, tier, item_id = _sample_id(item.get("tier"), item.get("id"))
    if item.get("sample_id") != sample_id or item.get("key") != f"audio2tool:{sample_id}":
        raise PilotRosterError(f"exposed identity fields disagree for {sample_id}")
    media_relpath = item.get("media_relpath")
    audio_seconds = item.get("audio_seconds")
    audio_sha256 = item.get("audio_sha256")
    if not isinstance(media_relpath, str) or not media_relpath:
        raise PilotRosterError(f"exposed media path is invalid for {sample_id}")
    if (
        isinstance(audio_seconds, bool)
        or not isinstance(audio_seconds, (int, float))
        or float(audio_seconds) <= 0.0
    ):
        raise PilotRosterError(f"exposed audio duration is invalid for {sample_id}")
    if (
        not isinstance(audio_sha256, str)
        or len(audio_sha256) != 64
        or any(character not in "0123456789abcdef" for character in audio_sha256)
    ):
        raise PilotRosterError(f"exposed audio SHA-256 is invalid for {sample_id}")
    block = query_block(tier, media_relpath)
    declared_block = item.get("query_block")
    if declared_block is not None and declared_block != block:
        raise PilotRosterError(f"exposed query block disagrees for {sample_id}")
    return _ExposedIdentity(
        sample_id=sample_id,
        tier=tier,
        item_id=item_id,
        key=f"audio2tool:{sample_id}",
        media_relpath=media_relpath,
        audio_seconds=float(audio_seconds),
        audio_sha256=audio_sha256,
        query_block=block,
        selection_rank_sha256=_rank(sample_id),
    )


def _items(receipt: object, label: str) -> Sequence[object]:
    if not isinstance(receipt, Mapping):
        raise PilotRosterError(f"{label} receipt must be an object")
    items = receipt.get("items")
    if not isinstance(items, list) or not items:
        raise PilotRosterError(f"{label} receipt must contain items")
    return items


def build_pilot_roster(
    parent_receipt: Mapping[str, object],
    exposed_receipts: Mapping[str, Mapping[str, object]],
    *,
    expected_parent_per_tier: int = 50,
    expected_exposed_per_tier: int = 39,
) -> dict[str, object]:
    """Build the G3 pilot and untouched reserve proof from identity fields only."""

    if not exposed_receipts:
        raise PilotRosterError("at least one exposed receipt is required")
    parent = tuple(_parent_identity(item) for item in _items(parent_receipt, "parent"))
    parent_by_id = {item.sample_id: item for item in parent}
    if len(parent_by_id) != len(parent):
        raise PilotRosterError("duplicate identity in parent population")
    parent_counts = Counter(item.tier for item in parent)
    expected_parent = {tier: expected_parent_per_tier for tier in G3_TIERS}
    if parent_counts != expected_parent:
        raise PilotRosterError(
            f"parent population must contain {expected_parent_per_tier} identities per tier"
        )

    exposed_by_id: dict[str, _ExposedIdentity] = {}
    source_counts: dict[str, int] = {}
    for name in sorted(exposed_receipts):
        source = tuple(
            _exposed_identity(item)
            for item in _items(exposed_receipts[name], f"exposed {name}")
        )
        source_counts[name] = len(source)
        for identity in source:
            if identity.sample_id not in parent_by_id:
                raise PilotRosterError(
                    f"exposed identity {identity.sample_id} is outside the parent population"
                )
            prior = exposed_by_id.setdefault(identity.sample_id, identity)
            if prior != identity:
                raise PilotRosterError(
                    f"conflicting media identity for {identity.sample_id} across receipts"
                )
    exposed_counts = Counter(item.tier for item in exposed_by_id.values())
    expected_exposed = {tier: expected_exposed_per_tier for tier in G3_TIERS}
    if exposed_counts != expected_exposed:
        raise PilotRosterError(
            f"exposed union must contain {expected_exposed_per_tier} identities per tier"
        )

    selected: list[_ExposedIdentity] = []
    for tier in G3_TIERS:
        ranked = sorted(
            (item for item in exposed_by_id.values() if item.tier == tier),
            key=lambda item: (item.selection_rank_sha256, item.sample_id),
        )
        selected.extend(ranked[:G3_PER_TIER])
    selected.sort(key=lambda item: (item.tier, item.sample_id))
    if len({item.sample_id for item in selected}) != len(G3_TIERS) * G3_PER_TIER:
        raise PilotRosterError("pilot identities are not unique")
    if len({item.query_block for item in selected}) != len(selected):
        raise PilotRosterError("pilot query blocks are not unique")

    reserve = sorted(
        (item for item in parent if item.sample_id not in exposed_by_id),
        key=lambda item: (item.tier, item.sample_id),
    )
    reserve_counts = Counter(item.tier for item in reserve)
    expected_reserve_per_tier = expected_parent_per_tier - expected_exposed_per_tier
    expected_reserve = {tier: expected_reserve_per_tier for tier in G3_TIERS}
    if reserve_counts != expected_reserve:
        raise PilotRosterError("confirmation reserve geometry is not complete")
    selected_ids = {item.sample_id for item in selected}
    reserve_ids = {item.sample_id for item in reserve}
    if selected_ids & reserve_ids:
        raise PilotRosterError("pilot overlaps the confirmation reserve")

    selected_items = [
        {
            "audio_seconds": item.audio_seconds,
            "audio_sha256": item.audio_sha256,
            "id": item.item_id,
            "key": item.key,
            "media_relpath": item.media_relpath,
            "packet_id": item.sample_id.replace(":", "/"),
            "query_block": item.query_block,
            "sample_id": item.sample_id,
            "selection_rank_sha256": item.selection_rank_sha256,
            "tier": item.tier,
        }
        for item in selected
    ]
    reserve_items = [
        {
            "id": item.item_id,
            "key": item.key,
            "query_idx": item.query_idx,
            "sample_id": item.sample_id,
            "tier": item.tier,
        }
        for item in reserve
    ]
    return {
        "audio_seconds_total": round(sum(item.audio_seconds for item in selected), 6),
        "carrier": "audio2tool",
        "confirmation_reserve": {
            "count": len(reserve_items),
            "items": reserve_items,
            "pilot_overlap_count": 0,
            "split_identity_hash": split_identity_hash(
                item["key"] for item in reserve_items
            ),
            "strata_counts": dict(sorted(reserve_counts.items())),
            "status": "UNTOUCHED_BY_G3_PILOT",
        },
        "count": len(selected_items),
        "design": (
            "Five identities per tier selected by stable namespace hash from the "
            "identity-only union of three already-exposed discovery cohorts."
        ),
        "exposure": (
            "Already-exposed discovery identities only; the separate 88-identity "
            "parent reserve remains untouched for prospective confirmation."
        ),
        "items": selected_items,
        "parent_split_identity_hash": parent_receipt.get("split_identity_hash"),
        "purpose": "G3 human-readable hierarchical-ground pilot.",
        "run_identity_hash": split_identity_hash(
            f"audio2tool/{item['sample_id']}" for item in selected_items
        ),
        "schema": "saea-a2t-g3-identity-only-pilot-roster-v1",
        "selection_namespace": G3_SELECTION_NAMESPACE,
        "selection_proof": {
            "exposed_union_count": len(exposed_by_id),
            "exposed_union_strata_counts": dict(sorted(exposed_counts.items())),
            "gold_used": False,
            "pilot_query_block_count": len(selected_items),
            "prior_outputs_used": False,
            "prior_scores_used": False,
            "reserve_count": len(reserve_items),
            "test_used": False,
            "transcripts_used": False,
        },
        "source_receipts": [
            {"item_count": source_counts[name], "path": name}
            for name in sorted(source_counts)
        ],
        "split_identity_hash": split_identity_hash(
            item["key"] for item in selected_items
        ),
        "split_name": G3_SPLIT_NAME,
        "split_role": "discovery",
        "strata_counts": dict(sorted(Counter(item.tier for item in selected).items())),
        "study": "speech-aware-evidence-acquisition",
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_repo_pilot_roster(repo_root: Path) -> dict[str, object]:
    """Load the four frozen receipts and bind their byte hashes to the roster."""

    root = Path(repo_root)
    parent_path = root / G3_PARENT_RECEIPT
    exposed_paths = {relpath: root / relpath for relpath in G3_EXPOSED_RECEIPTS}
    try:
        parent = json.loads(parent_path.read_text(encoding="utf-8"))
        exposed = {
            relpath: json.loads(path.read_text(encoding="utf-8"))
            for relpath, path in exposed_paths.items()
        }
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PilotRosterError(f"cannot read a frozen cohort receipt: {error}") from error
    receipt = build_pilot_roster(parent, exposed)
    receipt["parent_receipt"] = G3_PARENT_RECEIPT
    receipt["parent_receipt_sha256"] = _sha256(parent_path)
    for source in receipt["source_receipts"]:
        source["sha256"] = _sha256(exposed_paths[source["path"]])
    return receipt


__all__ = [
    "G3_EXPOSED_RECEIPTS",
    "G3_PARENT_RECEIPT",
    "G3_PER_TIER",
    "G3_SELECTION_NAMESPACE",
    "G3_SPLIT_NAME",
    "G3_TIERS",
    "PilotRosterError",
    "build_pilot_roster",
    "build_repo_pilot_roster",
]
