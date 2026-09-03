"""Model-free, fail-closed construction of a fresh Audio2Tool roster.

This module consumes identity manifests only.  In particular, it requires the
upstream partition to carry a precomputed normalized-token equivalence class;
without that field a freshness claim cannot be made without reading task text.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from typing import Any, Iterable, Mapping, Sequence

from ..scoring.normalize import normalize_text_v1
from ..rails.knowledge_build_a2t import A2tKbRow

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
NAMESPACE = "speech-aware-evidence-acquisition-a2t-agentloop-fresh-v1"


def _identity(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"source row is missing {field}")
    return value


def _canonicalize(row: Mapping[str, Any]) -> dict[str, Any]:
    """Canonicalize legacy A2T identity rows without reading task content."""
    result = dict(row)
    if not result.get("sample_id") and isinstance(result.get("key"), str):
        result["sample_id"] = result["key"].removeprefix("audio2tool:")
    if not result.get("query_block") and isinstance(result.get("query_idx"), int):
        tier = result.get("tier")
        result["query_block"] = f"{tier}:query-{result['query_idx']:06d}"
    return result


def _validate_source(rows: Sequence[Mapping[str, Any]], source_split_role: str) -> None:
    if source_split_role.lower() == "test":
        raise ValueError("test split is prohibited")
    if not rows:
        raise ValueError("source population is empty")
    for row in rows:
        for field in (
            "sample_id",
            "query_block",
            "normalized_token_class",
            "tier",
            "key",
        ):
            try:
                _identity(row, field)
            except ValueError as error:
                if field == "normalized_token_class":
                    raise ValueError(
                        "source row is missing normalized-token equivalence metadata"
                    ) from error
                raise
    for field in ("sample_id", "query_block", "normalized_token_class", "key"):
        values = [_identity(row, field) for row in rows]
        if len(values) != len(set(values)):
            raise ValueError(f"source contains duplicate {field}")
    unknown = set(row["tier"] for row in rows) - set(TIERS)
    if unknown:
        raise ValueError(f"source contains unknown tiers: {sorted(unknown)}")


def select_fresh_roster(
    rows: Iterable[Mapping[str, Any]],
    *,
    excluded_rows: Iterable[Mapping[str, Any]] = (),
    construction_rows: Iterable[Mapping[str, Any]] = (),
    target_per_tier: int = 13,
    namespace: str = NAMESPACE,
    source_split_role: str = "discovery",
) -> tuple[dict[str, Any], ...]:
    """Select ``target_per_tier`` fresh identities by stable SHA-256 rank."""
    if (
        not isinstance(target_per_tier, int)
        or isinstance(target_per_tier, bool)
        or target_per_tier < 1
    ):
        raise ValueError("target_per_tier must be a positive integer")
    if not isinstance(namespace, str) or not namespace or not namespace.isascii():
        raise ValueError("namespace must be non-empty ASCII text")
    source = tuple(_canonicalize(row) for row in rows)
    _validate_source(source, source_split_role)
    excluded = tuple(_canonicalize(row) for row in (*excluded_rows, *construction_rows))
    for row in excluded:
        if not any(
            isinstance(row.get(field), str) and row[field]
            for field in ("sample_id", "query_block", "normalized_token_class", "key")
        ):
            raise ValueError("exclusion row has no auditable identity")
    excluded_sets = {
        field: {
            row[field]
            for row in excluded
            if isinstance(row.get(field), str) and row[field]
        }
        for field in ("sample_id", "query_block", "normalized_token_class", "key")
        if excluded
    }
    eligible = [
        row
        for row in source
        if all(
            _identity(row, field) not in excluded_sets.get(field, set())
            for field in excluded_sets
        )
    ]
    counts = Counter(row["tier"] for row in eligible)
    missing = {
        tier: target_per_tier - counts[tier]
        for tier in TIERS
        if counts[tier] < target_per_tier
    }
    if missing:
        raise ValueError(f"insufficient fresh identities per tier: {missing}")
    selected: list[dict[str, Any]] = []
    for tier in TIERS:
        candidates = [row for row in eligible if row["tier"] == tier]
        candidates.sort(
            key=lambda row: (
                hashlib.sha256(
                    f"{namespace}\0{row['sample_id']}".encode("ascii")
                ).hexdigest(),
                row["sample_id"],
            )
        )
        for row in candidates[:target_per_tier]:
            item = dict(row)
            item["selection_rank_sha256"] = hashlib.sha256(
                f"{namespace}\0{row['sample_id']}".encode("ascii")
            ).hexdigest()
            selected.append(item)
    return tuple(selected)


def build_receipt(
    rows: Iterable[Mapping[str, Any]],
    *,
    source_name: str,
    source_sha256: str,
    excluded_rows: Iterable[Mapping[str, Any]] = (),
    construction_rows: Iterable[Mapping[str, Any]] = (),
    target_per_tier: int = 13,
    namespace: str = NAMESPACE,
) -> dict[str, Any]:
    """Create an identity-only no-contact receipt for a proposed roster."""
    excluded = tuple(excluded_rows)
    construction = tuple(construction_rows)
    selected = select_fresh_roster(
        rows,
        excluded_rows=excluded,
        construction_rows=construction,
        target_per_tier=target_per_tier,
        namespace=namespace,
    )
    keys = sorted(str(row["key"]) for row in selected)
    return {
        "schema": "saea-a2t-fresh-agentloop-roster-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": "audio2tool",
        "split_name": "A2T-AGENTLOOP-FRESH-DISCOVERY",
        "split_role": "discovery",
        "execution_profile": "model-free-check",
        "status": "PROPOSED_IDENTITY_ONLY_NO_CONTACT_AUTHORIZATION",
        "source": {"name": source_name, "sha256": source_sha256},
        "selection": {
            "namespace": namespace,
            "algorithm": "SHA-256 namespace-NUL-sample_id rank within each tier",
            "target_per_tier": target_per_tier,
            "excluded_identity_rows": len(excluded),
            "construction_identity_rows": len(construction),
            "uses_task_text": False,
            "uses_normalized_token_text": False,
            "uses_gold": False,
            "uses_test": False,
            "uses_model_or_tool": False,
            "uses_network_or_tokenizer_or_scorer": False,
        },
        "contacts": {"model": 0, "network": 0, "scorer": 0, "audio": 0},
        "count": len(selected),
        "tier_counts": dict(Counter(row["tier"] for row in selected)),
        "items": list(selected),
        "split_identity_hash": hashlib.sha256(
            "\n".join(keys).encode("ascii")
        ).hexdigest(),
    }


def _validate_kb(rows: Sequence[A2tKbRow]) -> None:
    if not rows or any(not isinstance(row, A2tKbRow) for row in rows):
        raise ValueError("development source must contain A2tKbRow values")
    if any(row.tier not in TIERS for row in rows):
        raise ValueError("development source contains unknown tier")
    if len({row.unit_id for row in rows}) != len(rows):
        raise ValueError("development source contains duplicate unit_id")


def _kb_identity(row: A2tKbRow) -> dict[str, Any]:
    return {
        "unit_id": row.unit_id,
        "tier": row.tier,
        "query_idx": row.query_idx,
        "query_block": f"query_idx:{row.query_idx}",
        "normalized_token_class": normalize_text_v1(row.text),
        "tool_name": row.tool_name,
        "sample_ids": list(row.sample_ids),
    }


def select_development_roster(
    construction_rows: Sequence[A2tKbRow],
    *,
    excluded_sample_ids: Iterable[str] = (),
    target_per_tier: int = 13,
    namespace: str = NAMESPACE,
) -> tuple[A2tKbRow, ...]:
    """Select fresh development units, keeping query blocks globally unique."""
    _validate_kb(construction_rows)
    if (
        not isinstance(target_per_tier, int)
        or isinstance(target_per_tier, bool)
        or target_per_tier < 1
    ):
        raise ValueError("target_per_tier must be a positive integer")
    forbidden = set(excluded_sample_ids)
    eligible = [
        r for r in construction_rows if not forbidden.intersection(r.sample_ids)
    ]
    chosen: list[A2tKbRow] = []
    used_blocks: set[int] = set()
    for tier in TIERS:
        candidates = [r for r in eligible if r.tier == tier]
        candidates.sort(
            key=lambda r: (
                hashlib.sha256(f"{namespace}\0{r.unit_id}".encode("ascii")).hexdigest(),
                r.unit_id,
            )
        )
        for row in candidates:
            if row.query_idx in used_blocks:
                continue
            chosen.append(row)
            used_blocks.add(row.query_idx)
            if sum(r.tier == tier for r in chosen) == target_per_tier:
                break
        if sum(r.tier == tier for r in chosen) < target_per_tier:
            raise ValueError(f"insufficient fresh development rows in {tier}")
    return tuple(chosen)


def build_development_receipt(
    construction_rows: Sequence[A2tKbRow],
    *,
    source_name: str,
    source_sha256: str,
    excluded_sample_ids: Iterable[str] = (),
    target_per_tier: int = 13,
    namespace: str = NAMESPACE,
) -> dict[str, Any]:
    """Build a no-contact roster and complete semantic-index exclusion sets."""
    selected = select_development_roster(
        construction_rows,
        excluded_sample_ids=excluded_sample_ids,
        target_per_tier=target_per_tier,
        namespace=namespace,
    )
    selected_ids = {r.unit_id for r in selected}
    selected_blocks = {r.query_idx for r in selected}
    selected_classes = {normalize_text_v1(r.text) for r in selected}
    build_excluded = [
        r
        for r in construction_rows
        if (
            r.unit_id in selected_ids
            or r.query_idx in selected_blocks
            or normalize_text_v1(r.text) in selected_classes
        )
    ]
    build_remaining = [r for r in construction_rows if r not in build_excluded]
    selected_tools = {r.tool_name for r in selected}
    retained_tools = selected_tools.issubset({r.tool_name for r in build_remaining})
    if not retained_tools:
        raise ValueError("remaining build index cannot retain every selected gold tool")
    items = [_kb_identity(r) for r in selected]
    return {
        "schema": "saea-a2t-fresh-agentloop-development-roster-receipt-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": "audio2tool",
        "split_name": "A2T-AGENTLOOP-FRESH-DEVELOPMENT",
        "split_role": "discovery",
        "execution_profile": "model-free-check",
        "status": "PROPOSED_IDENTITY_ONLY_NO_CONTACT_AUTHORIZATION",
        "source": {
            "name": source_name,
            "sha256": source_sha256,
            "count": len(construction_rows),
        },
        "count": len(items),
        "tier_counts": dict(Counter(r["tier"] for r in items)),
        "items": items,
        "build_exclusions": {
            "unit_ids": sorted(r.unit_id for r in build_excluded),
            "query_blocks": [
                f"query_idx:{x}" for x in sorted({r.query_idx for r in build_excluded})
            ],
            "normalized_token_classes": sorted(
                {normalize_text_v1(r.text) for r in build_excluded}
            ),
            "count": len(build_excluded),
        },
        "build_index": {
            "source_count": len(construction_rows),
            "remaining_count": len(build_remaining),
            "selected_gold_tools_retained": retained_tools,
        },
        "contacts": {"model": 0, "network": 0, "scorer": 0, "audio": 0},
        "selection": {
            "namespace": namespace,
            "uses_gold_at_runtime": False,
            "uses_test": False,
            "uses_model_or_tool": False,
        },
        "split_identity_hash": hashlib.sha256(
            "\n".join(sorted(r["unit_id"] for r in items)).encode("ascii")
        ).hexdigest(),
    }


def build_partition_flight_receipt(
    source_rows: Sequence[A2tKbRow],
    partition: Any,
    *,
    exposed_sample_ids: Iterable[str],
    excluded_identity_rows: Iterable[Mapping[str, Any]] = (),
    per_tier: int = 13,
    namespace: str = NAMESPACE,
    split_name: str = "A2T-AGENTLOOP-FRESH-FLIGHT",
    carrier_metadata: Mapping[str, tuple[str, str, float]] | None = None,
) -> dict[str, Any]:
    """Build a compact roster from ``propose_partition``'s fresh eval draw."""
    if not isinstance(split_name, str) or not split_name or not split_name.isascii():
        raise ValueError("split name must be non-empty ASCII text")
    by_item = {(r.tier, item): r for r in source_rows for item in r.item_ids}
    candidates: list[A2tKbRow] = []
    for tier, item_id, text, tool in partition.eval_items:
        row = by_item.get((tier, item_id))
        if row is None or row.text != text or row.tool_name != tool:
            raise ValueError(
                "partition eval item cannot be resolved to source A2tKbRow"
            )
        candidates.append(row)
    excluded_rows = tuple(excluded_identity_rows)
    excluded_ids: set[str] = set()
    excluded_blocks: set[int] = set()
    excluded_classes: set[str] = set()
    for item in excluded_rows:
        if not isinstance(item, Mapping):
            raise ValueError("excluded identity row must be a mapping")
        sample_id = item.get("sample_id")
        query_idx = item.get("query_idx")
        normalized_hash = item.get("normalized_token_class_sha256")
        if isinstance(sample_id, str) and sample_id:
            excluded_ids.add(sample_id)
        if isinstance(query_idx, int) and not isinstance(query_idx, bool):
            excluded_blocks.add(query_idx)
        if isinstance(normalized_hash, str) and len(normalized_hash) == 64:
            excluded_classes.add(normalized_hash)
        if not (
            isinstance(sample_id, str)
            and sample_id
            or isinstance(query_idx, int)
            and not isinstance(query_idx, bool)
            or isinstance(normalized_hash, str)
            and len(normalized_hash) == 64
        ):
            raise ValueError("excluded identity row has no supported identity")
    construction = tuple(partition.construction)
    construction_classes = {
        hashlib.sha256(normalize_text_v1(row.text).encode("utf-8")).hexdigest()
        for row in construction
    }
    exposed = set(exposed_sample_ids)
    candidates = [
        row
        for row in candidates
        if f"{row.tier}:{row.item_ids[0]:06d}" not in exposed | excluded_ids
        and row.query_idx not in excluded_blocks
        and hashlib.sha256(
            normalize_text_v1(row.text).encode("utf-8")
        ).hexdigest()
        not in excluded_classes | construction_classes
    ]
    selected = []
    for tier in TIERS:
        pool = [r for r in candidates if r.tier == tier]
        if len(pool) < per_tier:
            raise ValueError(
                f"partition tier {tier} has fewer than {per_tier} eval items"
            )
        selected.extend(
            sorted(
                pool,
                key=lambda r: hashlib.sha256(
                    f"{namespace}\0{r.tier}:{r.item_ids[0]:06d}".encode("ascii")
                ).hexdigest(),
            )[:per_tier]
        )
    selected_ids = {f"{r.tier}:{r.item_ids[0]:06d}" for r in selected}
    if selected_ids & exposed:
        raise ValueError("flight roster intersects exposed sample IDs")
    if any(selected_ids.intersection(r.sample_ids) for r in construction):
        raise ValueError("flight roster intersects construction sample IDs")
    selected_blocks = {r.query_idx for r in selected}
    if selected_blocks & {r.query_idx for r in construction}:
        raise ValueError("flight roster intersects construction query blocks")
    selected_classes = {
        hashlib.sha256(normalize_text_v1(row.text).encode("utf-8")).hexdigest()
        for row in selected
    }
    if selected_blocks & excluded_blocks or selected_classes & (
        excluded_classes | construction_classes
    ):
        raise ValueError("flight roster intersects an excluded identity class")
    items = []
    if carrier_metadata is None:
        raise ValueError("audio metadata is required to build a flyable receipt")
    for row in selected:
        sid = f"{row.tier}:{row.item_ids[0]:06d}"
        metadata = carrier_metadata.get(sid)
        if metadata is None or len(metadata) != 3:
            raise ValueError(f"missing audio metadata for {sid}")
        media_relpath, audio_sha256, audio_seconds = metadata
        if (
            not isinstance(media_relpath, str)
            or not media_relpath
            or not isinstance(audio_sha256, str)
            or len(audio_sha256) != 64
            or audio_sha256 != audio_sha256.lower()
            or not isinstance(audio_seconds, (int, float))
            or audio_seconds <= 0
        ):
            raise ValueError(f"invalid audio metadata for {sid}")
        items.append(
            {
                "sample_id": sid,
                "tier": row.tier,
                "id": row.item_ids[0],
                "key": f"audio2tool:{sid}",
                "query_idx": row.query_idx,
                "query_block": f"query_idx:{row.query_idx}",
                "query_block_sha256": hashlib.sha256(
                    f"query_idx:{row.query_idx}".encode("ascii")
                ).hexdigest(),
                "normalized_token_class_sha256": hashlib.sha256(
                    normalize_text_v1(row.text).encode("utf-8")
                ).hexdigest(),
                "media_relpath": media_relpath,
                "audio_sha256": audio_sha256,
                "audio_seconds": round(float(audio_seconds), 6),
                "selection_rank_sha256": hashlib.sha256(
                    f"{namespace}\0{sid}".encode("ascii")
                ).hexdigest(),
            }
        )
    return {
        "schema": "saea-a2t-agentloop-flight-roster-receipt-v1",
        "carrier": "audio2tool",
        "split_name": split_name,
        "split_role": "discovery",
        "status": "PREPARED_NOT_CONTACT_AUTHORITY",
        "count": len(items),
        "tier_counts": dict(Counter(item["tier"] for item in items)),
        "items": items,
        "partition": partition.report if hasattr(partition, "report") else {},
        "contacts": {"model": 0, "network": 0, "scorer": 0, "audio": 0},
        "selection": {
            "namespace": namespace,
            "per_tier": per_tier,
            "excluded_identity_rows": len(excluded_rows),
            "construction_normalized_class_exclusions": len(construction_classes),
            "uses_test": False,
            "uses_gold_at_runtime": False,
        },
        "audio_seconds_total": round(sum(i["audio_seconds"] for i in items), 6),
        "media_roster_sha256": hashlib.sha256(
            "\n".join(
                f"{i['sample_id']}\t{i['media_relpath']}\t{i['audio_sha256']}\t{i['audio_seconds']}"
                for i in items
            ).encode("utf-8")
        ).hexdigest(),
        "split_identity_hash": hashlib.sha256(
            "\n".join(sorted(i["key"] for i in items)).encode("ascii")
        ).hexdigest(),
    }


__all__ = [
    "NAMESPACE",
    "TIERS",
    "build_receipt",
    "build_development_receipt",
    "build_partition_flight_receipt",
    "select_development_roster",
    "select_fresh_roster",
]
