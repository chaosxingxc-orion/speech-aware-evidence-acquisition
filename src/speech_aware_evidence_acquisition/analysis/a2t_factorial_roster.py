"""Identity-only selection for a fresh Audio2Tool factorial roster."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import math
from pathlib import PurePosixPath
import re
from typing import Iterable, Sequence

from .a2t_fresh_agentloop_roster import TIERS


_SHA256 = re.compile(r"[0-9a-f]{64}", flags=re.ASCII)


class FactorialRosterError(ValueError):
    """A proposed roster cannot prove its identity and leakage boundaries."""


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _require_hash(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise FactorialRosterError(f"{label} must be a lowercase SHA-256")
    return value


@dataclass(frozen=True)
class IdentityCandidate:
    """One hash-only evaluation identity with auditable carrier metadata."""

    sample_id: str
    tier: str
    item_id: int
    query_idx: int
    normalized_token_class_sha256: str
    media_relpath: str
    audio_sha256: str
    audio_seconds: float

    def __post_init__(self) -> None:
        if self.tier not in TIERS:
            raise FactorialRosterError("candidate tier is unknown")
        if (
            isinstance(self.item_id, bool)
            or not isinstance(self.item_id, int)
            or self.item_id < 0
            or self.sample_id != f"{self.tier}:{self.item_id:06d}"
        ):
            raise FactorialRosterError("candidate sample identity is malformed")
        if (
            isinstance(self.query_idx, bool)
            or not isinstance(self.query_idx, int)
            or self.query_idx < 0
        ):
            raise FactorialRosterError("candidate query identity is malformed")
        _require_hash(
            self.normalized_token_class_sha256,
            label="normalized token class hash",
        )
        _require_hash(self.audio_sha256, label="audio hash")
        path = PurePosixPath(self.media_relpath)
        if (
            not isinstance(self.media_relpath, str)
            or not self.media_relpath
            or not self.media_relpath.isascii()
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or path.suffix.casefold() != ".wav"
        ):
            raise FactorialRosterError("candidate media path is malformed")
        if (
            isinstance(self.audio_seconds, bool)
            or not isinstance(self.audio_seconds, (int, float))
            or not math.isfinite(float(self.audio_seconds))
            or self.audio_seconds <= 0
        ):
            raise FactorialRosterError("candidate audio duration is malformed")


def _validate_candidates(
    candidates: Iterable[IdentityCandidate],
) -> tuple[IdentityCandidate, ...]:
    if isinstance(candidates, (str, bytes)):
        raise FactorialRosterError("candidate population must be an iterable")
    try:
        rows = tuple(candidates)
    except TypeError as error:
        raise FactorialRosterError("candidate population must be an iterable") from error
    if not rows or any(not isinstance(row, IdentityCandidate) for row in rows):
        raise FactorialRosterError("candidate population is empty or malformed")
    sample_ids = tuple(row.sample_id for row in rows)
    if len(sample_ids) != len(set(sample_ids)):
        raise FactorialRosterError("candidate population contains duplicate samples")
    return rows


def _validate_target(target_per_tier: object) -> int:
    if (
        isinstance(target_per_tier, bool)
        or not isinstance(target_per_tier, int)
        or target_per_tier <= 0
    ):
        raise FactorialRosterError("target per tier must be a positive integer")
    return target_per_tier


def _hash_set(values: Iterable[str], *, label: str) -> frozenset[str]:
    try:
        result = frozenset(values)
    except TypeError as error:
        raise FactorialRosterError(f"{label} must be iterable") from error
    for value in result:
        _require_hash(value, label=label)
    return result


def select_factorial_roster(
    candidates: Iterable[IdentityCandidate],
    *,
    excluded_sample_ids: Iterable[str] = (),
    excluded_query_indices: Iterable[int] = (),
    excluded_normalized_class_sha256s: Iterable[str] = (),
    target_per_tier: int = 16,
    namespace: str = "speech-aware-evidence-acquisition-a2t-select-fill-factorial-128-v1",
) -> tuple[IdentityCandidate, ...]:
    """Select a deterministic tier-balanced roster with three-way exclusion."""

    rows = _validate_candidates(candidates)
    target = _validate_target(target_per_tier)
    if not isinstance(namespace, str) or not namespace or not namespace.isascii():
        raise FactorialRosterError("selection namespace must be non-empty ASCII")
    try:
        excluded_samples = frozenset(excluded_sample_ids)
        excluded_queries = frozenset(excluded_query_indices)
    except TypeError as error:
        raise FactorialRosterError("exclusion identities must be iterable") from error
    if any(not isinstance(value, str) or not value for value in excluded_samples):
        raise FactorialRosterError("excluded sample identity is malformed")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0
        for value in excluded_queries
    ):
        raise FactorialRosterError("excluded query identity is malformed")
    excluded_classes = _hash_set(
        excluded_normalized_class_sha256s,
        label="excluded normalized class hash",
    )
    eligible = tuple(
        row
        for row in rows
        if row.sample_id not in excluded_samples
        and row.query_idx not in excluded_queries
        and row.normalized_token_class_sha256 not in excluded_classes
    )

    selected: list[IdentityCandidate] = []
    used_queries: set[int] = set()
    used_classes: set[str] = set()
    for tier in TIERS:
        ranked = sorted(
            (row for row in eligible if row.tier == tier),
            key=lambda row: (
                _sha256(f"{namespace}\0{row.sample_id}"),
                row.sample_id,
            ),
        )
        tier_selected: list[IdentityCandidate] = []
        for row in ranked:
            if (
                row.query_idx in used_queries
                or row.normalized_token_class_sha256 in used_classes
            ):
                continue
            tier_selected.append(row)
            used_queries.add(row.query_idx)
            used_classes.add(row.normalized_token_class_sha256)
            if len(tier_selected) == target:
                break
        if len(tier_selected) != target:
            raise FactorialRosterError(
                f"{tier} has only {len(tier_selected)} safe unique identities; "
                f"{target} required"
            )
        selected.extend(tier_selected)
    return tuple(selected)


def build_factorial_roster_receipt(
    candidates: Sequence[IdentityCandidate],
    *,
    source_path: str,
    source_sha256: str,
    source_split_identity_sha256: str,
    excluded_sample_ids: Iterable[str],
    excluded_query_indices: Iterable[int],
    excluded_normalized_class_sha256s: Iterable[str],
    target_per_tier: int = 16,
    namespace: str = "speech-aware-evidence-acquisition-a2t-select-fill-factorial-128-v1",
) -> dict[str, object]:
    """Build a no-contact, no-text roster receipt from protected identities."""

    rows = _validate_candidates(candidates)
    _require_hash(source_sha256, label="source receipt hash")
    _require_hash(
        source_split_identity_sha256,
        label="source split identity hash",
    )
    if (
        not isinstance(source_path, str)
        or not source_path
        or not source_path.isascii()
    ):
        raise FactorialRosterError("source path must be non-empty ASCII")
    excluded_samples = tuple(excluded_sample_ids)
    excluded_queries = tuple(excluded_query_indices)
    excluded_classes = tuple(excluded_normalized_class_sha256s)
    selected = select_factorial_roster(
        rows,
        excluded_sample_ids=excluded_samples,
        excluded_query_indices=excluded_queries,
        excluded_normalized_class_sha256s=excluded_classes,
        target_per_tier=target_per_tier,
        namespace=namespace,
    )
    items = [
        {
            "sample_id": row.sample_id,
            "tier": row.tier,
            "id": row.item_id,
            "key": f"audio2tool:{row.sample_id}",
            "query_idx": row.query_idx,
            "query_block_sha256": _sha256(f"query_idx:{row.query_idx}"),
            "normalized_token_class_sha256": row.normalized_token_class_sha256,
            "media_relpath": row.media_relpath,
            "audio_sha256": row.audio_sha256,
            "audio_seconds": round(float(row.audio_seconds), 6),
            "selection_rank_sha256": _sha256(
                f"{namespace}\0{row.sample_id}"
            ),
        }
        for row in selected
    ]
    candidate_keys = sorted(f"audio2tool:{row.sample_id}" for row in rows)
    selected_keys = sorted(str(item["key"]) for item in items)
    return {
        "schema": "saea-a2t-select-fill-factorial-roster-v1",
        "study": "speech-aware-evidence-acquisition",
        "carrier": "audio2tool",
        "split_name": "A2T-SELECT-FILL-FACTORIAL-128",
        "split_role": "discovery",
        "execution_profile": "model-free-check",
        "status": "PREPARED_NOT_CONTACT_AUTHORITY",
        "source": {
            "path": source_path,
            "sha256": source_sha256,
            "split_identity_sha256": source_split_identity_sha256,
            "candidate_count": len(rows),
            "candidate_universe_sha256": _sha256("\n".join(candidate_keys)),
        },
        "selection": {
            "namespace": namespace,
            "algorithm": "SHA-256 namespace-NUL-sample rank with global query and normalized-class uniqueness",
            "target_per_tier": target_per_tier,
            "excluded_sample_count": len(set(excluded_samples)),
            "excluded_query_count": len(set(excluded_queries)),
            "excluded_normalized_class_count": len(set(excluded_classes)),
            "task_text_emitted": False,
            "normalized_text_emitted": False,
            "gold_fields_accessed": False,
            "test_used": False,
        },
        "count": len(items),
        "tier_counts": dict(Counter(str(item["tier"]) for item in items)),
        "items": items,
        "audio_seconds_total": round(
            sum(float(item["audio_seconds"]) for item in items),
            6,
        ),
        "media_roster_sha256": _sha256(
            "\n".join(
                f"{item['sample_id']}\t{item['media_relpath']}\t{item['audio_sha256']}\t{item['audio_seconds']}"
                for item in items
            )
        ),
        "split_identity_hash": _sha256("\n".join(selected_keys)),
        "contacts": {
            "audio_decode": 0,
            "embedding": 0,
            "frozen_core": 0,
            "network": 0,
            "scorer": 0,
            "tokenizer": 0,
        },
    }


__all__ = [
    "FactorialRosterError",
    "IdentityCandidate",
    "build_factorial_roster_receipt",
    "select_factorial_roster",
]
