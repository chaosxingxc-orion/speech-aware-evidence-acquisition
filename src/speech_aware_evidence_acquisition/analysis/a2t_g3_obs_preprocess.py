"""Plan and merge the receipt-pinned G3 observation packet preprocessing pass.

The first 35 runtime bindings reuse already-promoted original packets. The five
tier-7 bindings use complete-dialogue audio and distinct packet identities. This
module contains only identity, media, packet, and accounting logic; it never
accepts task text, gold, model output, or scores.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from ..contracts import ExecutionPlan

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
TIER7 = "tier7_multiturn"
DERIVED_PACKET_PREFIX = "g3_complete_dialogue"
DERIVED_CONTACT_PREFIX = "a2t-g3-dialogue"
_FORBIDDEN_KEYS = frozenset(
    {
        "additional_tool_calls",
        "content",
        "expected_tool_call",
        "extracted_params",
        "gold",
        "query",
        "score",
        "transcript",
    }
)


class G3ObsPreprocessError(RuntimeError):
    """The roster, media, source packet, or merged identity is invalid."""


@dataclass(frozen=True)
class OriginalPacket:
    sample_id: str
    tier: str
    packet_id: str
    packet_sha256: str
    audio_sha256: str
    decoder_gguf_sha256: str
    mmproj_sha256: str
    source_receipt: str
    source_receipt_sha256: str


@dataclass(frozen=True)
class DerivedEncoding:
    sample_id: str
    tier: str
    contact_sample_id: str
    packet_id: str
    media_relpath: str
    audio_sha256: str
    audio_seconds: float


@dataclass(frozen=True)
class G3ObsPreprocessPlan:
    split_name: str
    split_identity_hash: str
    run_identity_hash: str
    original_verified: tuple[OriginalPacket, ...]
    reused: tuple[OriginalPacket, ...]
    derived: tuple[DerivedEncoding, ...]
    planned_contacts: int
    derived_audio_seconds: float
    execution_plan_audio_seconds: int


def _sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise G3ObsPreprocessError(f"{label} must be lowercase 64-hex")
    return value


def _reject_task_information(value: object, label: str) -> None:
    if isinstance(value, Mapping):
        overlap = set(value) & _FORBIDDEN_KEYS
        if overlap:
            raise G3ObsPreprocessError(
                f"{label} contains prohibited task-information keys {sorted(overlap)}"
            )
        for key, child in value.items():
            _reject_task_information(child, f"{label}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_task_information(child, f"{label}[{index}]")


def _items(document: object, label: str, expected: int | None = None) -> list[object]:
    if not isinstance(document, Mapping) or not isinstance(document.get("items"), list):
        raise G3ObsPreprocessError(f"{label} must contain an items list")
    items = document["items"]
    if expected is not None and (document.get("count") != expected or len(items) != expected):
        raise G3ObsPreprocessError(f"{label} must contain exactly {expected} items")
    return items


def _packet_record(packet: object, source: str, receipt_sha256: str) -> OriginalPacket:
    if not isinstance(packet, Mapping):
        raise G3ObsPreprocessError(f"source promotion {source} contains a malformed packet")
    packet_id = packet.get("packet_id")
    if not isinstance(packet_id, str) or packet_id.count("/") != 1:
        raise G3ObsPreprocessError(f"source promotion {source} packet_id is malformed")
    tier, numeric = packet_id.split("/", 1)
    if tier not in G3_TIERS or not numeric.isdigit():
        raise G3ObsPreprocessError(f"source promotion {source} packet_id is malformed")
    return OriginalPacket(
        sample_id=f"{tier}:{numeric}",
        tier=tier,
        packet_id=packet_id,
        packet_sha256=_sha256(packet.get("packet_sha256"), "packet SHA-256"),
        audio_sha256=_sha256(packet.get("audio_sha256"), "packet audio SHA-256"),
        decoder_gguf_sha256=_sha256(
            packet.get("decoder_gguf_sha256"), "decoder GGUF SHA-256"
        ),
        mmproj_sha256=_sha256(packet.get("mmproj_sha256"), "mmproj SHA-256"),
        source_receipt=source,
        source_receipt_sha256=_sha256(receipt_sha256, "source receipt SHA-256"),
    )


def build_preprocess_plan(
    roster: Mapping[str, object],
    media_manifest: Mapping[str, object],
    source_promotions: Mapping[str, Mapping[str, object]],
) -> G3ObsPreprocessPlan:
    """Verify all 40 originals and form the immutable 35/5 OBS partition."""

    _reject_task_information(roster, "roster")
    _reject_task_information(media_manifest, "media manifest")
    roster_items = _items(roster, "G3 roster", 40)
    media_items = _items(media_manifest, "G3 media manifest", 40)
    if media_manifest.get("tier7_complete_dialogue_count") != 5:
        raise G3ObsPreprocessError("G3 media manifest must carry five complete dialogues")
    if not isinstance(source_promotions, Mapping) or len(source_promotions) != 3:
        raise G3ObsPreprocessError("exactly three source promotion receipts are required")

    originals_by_id: dict[str, list[OriginalPacket]] = {}
    for source in sorted(source_promotions):
        promotion = source_promotions[source]
        if not isinstance(promotion, Mapping):
            raise G3ObsPreprocessError(f"source promotion {source} must be an object")
        packets = promotion.get("packets")
        if (
            not isinstance(packets, list)
            or promotion.get("count") != len(packets)
            or not packets
        ):
            raise G3ObsPreprocessError(f"source promotion {source} count is invalid")
        receipt_sha256 = promotion.get("receipt_sha256")
        for packet in packets:
            record = _packet_record(packet, source, receipt_sha256)
            originals_by_id.setdefault(record.sample_id, []).append(record)

    roster_by_id: dict[str, Mapping[str, object]] = {}
    for item in roster_items:
        if not isinstance(item, Mapping):
            raise G3ObsPreprocessError("G3 roster item must be an object")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or sample_id in roster_by_id:
            raise G3ObsPreprocessError("G3 roster sample identities must be unique")
        roster_by_id[sample_id] = item
    media_by_id: dict[str, Mapping[str, object]] = {}
    for item in media_items:
        if not isinstance(item, Mapping):
            raise G3ObsPreprocessError("G3 media item must be an object")
        sample_id = item.get("sample_id")
        if not isinstance(sample_id, str) or sample_id in media_by_id:
            raise G3ObsPreprocessError("G3 media sample identities must be unique")
        media_by_id[sample_id] = item
    if set(media_by_id) != set(roster_by_id):
        raise G3ObsPreprocessError("G3 roster and media identities disagree")

    original_verified: list[OriginalPacket] = []
    reused: list[OriginalPacket] = []
    derived: list[DerivedEncoding] = []
    tier_counts: dict[str, int] = {tier: 0 for tier in G3_TIERS}
    for sample_id in sorted(roster_by_id):
        roster_item = roster_by_id[sample_id]
        tier = roster_item.get("tier")
        if tier not in tier_counts:
            raise G3ObsPreprocessError(f"invalid G3 tier for {sample_id}")
        tier_counts[str(tier)] += 1
        matches = originals_by_id.get(sample_id, [])
        if len(matches) != 1:
            raise G3ObsPreprocessError(
                f"original packet for {sample_id} must occur in exactly one promotion receipt"
            )
        original = matches[0]
        roster_audio_sha256 = _sha256(
            roster_item.get("audio_sha256"), f"roster audio SHA-256 for {sample_id}"
        )
        if original.audio_sha256 != roster_audio_sha256:
            raise G3ObsPreprocessError(f"original audio SHA-256 drift for {sample_id}")
        if original.packet_id != roster_item.get("packet_id"):
            raise G3ObsPreprocessError(f"original packet id drift for {sample_id}")
        original_verified.append(original)

        media = media_by_id[sample_id]
        if media.get("tier") != tier:
            raise G3ObsPreprocessError(f"media tier drift for {sample_id}")
        if tier != TIER7:
            if (
                media.get("media_relpath") != roster_item.get("media_relpath")
                or media.get("audio_sha256") != roster_audio_sha256
            ):
                raise G3ObsPreprocessError(f"non-tier-7 media drift for {sample_id}")
            reused.append(original)
            continue
        if media.get("source_final_turn_media_relpath") != roster_item.get("media_relpath"):
            raise G3ObsPreprocessError(f"tier-7 source media drift for {sample_id}")
        audio_seconds = media.get("audio_seconds")
        media_relpath = media.get("media_relpath")
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(audio_seconds)
            or audio_seconds <= 0
            or not isinstance(media_relpath, str)
            or not media_relpath
        ):
            raise G3ObsPreprocessError(f"derived media facts are invalid for {sample_id}")
        numeric = sample_id.split(":", 1)[1]
        derived.append(
            DerivedEncoding(
                sample_id=sample_id,
                tier=TIER7,
                contact_sample_id=f"{DERIVED_CONTACT_PREFIX}:{numeric}",
                packet_id=f"{DERIVED_PACKET_PREFIX}/{TIER7}/{numeric}",
                media_relpath=media_relpath,
                audio_sha256=_sha256(
                    media.get("audio_sha256"), f"derived audio SHA-256 for {sample_id}"
                ),
                audio_seconds=float(audio_seconds),
            )
        )
    if tier_counts != {tier: 5 for tier in G3_TIERS}:
        raise G3ObsPreprocessError("G3 roster must contain five identities per tier")
    if len(reused) != 35 or len(derived) != 5 or len(original_verified) != 40:
        raise G3ObsPreprocessError("G3 OBS partition must be 40 verified, 35 reused, 5 derived")
    original_ids = {item.packet_id for item in original_verified}
    if original_ids & {item.packet_id for item in derived}:
        raise G3ObsPreprocessError("derived packet ids overlap original packet ids")
    audio_total = round(sum(item.audio_seconds for item in derived), 6)
    return G3ObsPreprocessPlan(
        split_name=str(roster.get("split_name")),
        split_identity_hash=_sha256(roster.get("split_identity_hash"), "split identity hash"),
        run_identity_hash=_sha256(roster.get("run_identity_hash"), "run identity hash"),
        original_verified=tuple(original_verified),
        reused=tuple(reused),
        derived=tuple(derived),
        planned_contacts=5,
        derived_audio_seconds=audio_total,
        execution_plan_audio_seconds=math.ceil(audio_total),
    )


def _canonical_sha256(document: object) -> str:
    return hashlib.sha256(
        json.dumps(
            document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def build_merged_outputs(
    plan: G3ObsPreprocessPlan,
    derived_packets: Sequence[Mapping[str, object]],
    *,
    feature_root: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Merge 35 reused and five new packets into deterministic runtime bindings."""

    derived_by_id: dict[str, Mapping[str, object]] = {}
    for packet in derived_packets:
        if not isinstance(packet, Mapping):
            raise G3ObsPreprocessError("derived packet record must be an object")
        packet_id = packet.get("packet_id")
        if not isinstance(packet_id, str) or packet_id in derived_by_id:
            raise G3ObsPreprocessError("derived packet ids must be unique")
        derived_by_id[packet_id] = packet
    if set(derived_by_id) != {item.packet_id for item in plan.derived}:
        raise G3ObsPreprocessError("derived packet set is incomplete")

    rows: list[dict[str, object]] = []
    for item in plan.reused:
        rows.append(
            {
                "audio_sha256": item.audio_sha256,
                "decoder_gguf_sha256": item.decoder_gguf_sha256,
                "mmproj_sha256": item.mmproj_sha256,
                "packet_id": item.packet_id,
                "packet_sha256": item.packet_sha256,
                "sample_id": item.sample_id,
                "source_kind": "reused_original",
                "source_promotion_receipt": item.source_receipt,
                "source_promotion_receipt_sha256": item.source_receipt_sha256,
            }
        )
    for item in plan.derived:
        packet = derived_by_id[item.packet_id]
        if packet.get("audio_sha256") != item.audio_sha256:
            raise G3ObsPreprocessError(f"derived audio SHA-256 drift for {item.sample_id}")
        rows.append(
            {
                "audio_sha256": item.audio_sha256,
                "decoder_gguf_sha256": _sha256(
                    packet.get("decoder_gguf_sha256"), "derived decoder GGUF SHA-256"
                ),
                "mmproj_sha256": _sha256(
                    packet.get("mmproj_sha256"), "derived mmproj SHA-256"
                ),
                "packet_id": item.packet_id,
                "packet_sha256": _sha256(
                    packet.get("packet_sha256"), "derived packet SHA-256"
                ),
                "sample_id": item.sample_id,
                "source_contact_sample_id": item.contact_sample_id,
                "source_kind": "derived_complete_dialogue",
            }
        )
    rows.sort(key=lambda row: str(row["sample_id"]))
    if len(rows) != 40 or len({row["packet_id"] for row in rows}) != 40:
        raise G3ObsPreprocessError("merged promotion must contain 40 unique packets")
    decoder_hashes = {row["decoder_gguf_sha256"] for row in rows}
    mmproj_hashes = {row["mmproj_sha256"] for row in rows}
    if len(decoder_hashes) != 1 or len(mmproj_hashes) != 1:
        raise G3ObsPreprocessError("merged packets do not share one encoder identity")
    bindings = {
        "bindings": {
            str(row["sample_id"]): {
                "packet_id": row["packet_id"],
                "sha256": row["packet_sha256"],
            }
            for row in rows
        },
        "count": 40,
        "feature_root": feature_root,
        "schema": "saea-a2t-g3-obs-packet-binding-map-v1",
        "split_identity_hash": plan.split_identity_hash,
    }
    receipt = {
        "binding_map_payload_sha256": _canonical_sha256(bindings),
        "carrier": "audio2tool",
        "count": 40,
        "derived_audio_seconds": plan.derived_audio_seconds,
        "derived_complete_dialogue_count": 5,
        "encode_contacts": 5,
        "feature_root": feature_root,
        "packets": rows,
        "response_semantics_read": False,
        "reused_original_count": 35,
        "run_identity_hash": plan.run_identity_hash,
        "schema": "saea-a2t-g3-obs-promotion-receipt-v1",
        "split_identity_hash": plan.split_identity_hash,
        "split_name": plan.split_name,
        "study": "speech-aware-evidence-acquisition",
    }
    return receipt, bindings


def build_execution_plan(
    plan: G3ObsPreprocessPlan,
    *,
    run_id: str,
    protocol_hash: str,
    attempt_id: str,
    planned_gpu_hours: float = 0.1,
) -> ExecutionPlan:
    """Build the structured gate plan for only the five derived contacts."""

    return ExecutionPlan(
        run_id=run_id,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=plan.run_identity_hash,
        planned_model_calls=plan.planned_contacts,
        planned_gpu_hours=planned_gpu_hours,
        planned_speech_audio_seconds=plan.execution_plan_audio_seconds,
        protocol_hash=protocol_hash,
        attempt_id=attempt_id,
    ).validate()


__all__ = [
    "DERIVED_CONTACT_PREFIX",
    "DERIVED_PACKET_PREFIX",
    "G3ObsPreprocessError",
    "G3ObsPreprocessPlan",
    "OriginalPacket",
    "DerivedEncoding",
    "build_execution_plan",
    "build_merged_outputs",
    "build_preprocess_plan",
]
