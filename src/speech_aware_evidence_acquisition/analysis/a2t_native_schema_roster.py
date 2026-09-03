"""Pure identity-only selector for a fixed one-row-per-tier A2T roster."""

from __future__ import annotations

from hashlib import sha256
from typing import Mapping, Sequence

from ..reproduction.sampling import split_identity_hash


SELECTION_NAMESPACE = (
    "speech-aware-evidence-acquisition-g8d-structured-action-fixed8-v1"
)
SPLIT_NAME = "A2T-NATIVE-STRUCTURED-ACTION-FIXED8"
TIERS = (
    "tier1_direct", "tier2_parametric", "tier3_multi_intent", "tier4_implicit",
    "tier5_needle", "tier6_correction", "tier7_multiturn", "tier8_intent_blending",
)
ALLOWED_FIELDS = frozenset({
    "audio_seconds", "audio_sha256", "id", "key", "media_relpath", "packet_id",
    "query_block", "query_idx", "sample_id", "selection_rank_sha256", "tier",
})


def _validate(rows: Sequence[Mapping[str, object]]) -> None:
    if len(rows) != 104:
        raise ValueError("source population must contain exactly 104 identity rows")
    if any(set(row) - ALLOWED_FIELDS for row in rows):
        raise ValueError("source rows must contain identity-only fields")
    if len({row.get("sample_id") for row in rows}) != 104:
        raise ValueError("sample identities must be unique")
    if len({row.get("query_block") for row in rows}) != 104:
        raise ValueError("query blocks must be unique")
    counts = {tier: sum(row.get("tier") == tier for row in rows) for tier in TIERS}
    if counts != dict.fromkeys(TIERS, 13):
        raise ValueError("source population must contain 8 tiers with 13 rows each")


def select_native_schema_roster(
    rows: Sequence[Mapping[str, object]],
    *, namespace: str = SELECTION_NAMESPACE,
) -> tuple[dict[str, object], ...]:
    """Select the lowest namespace-hash row independently within each tier."""
    if not isinstance(namespace, str) or not namespace or not namespace.isascii():
        raise ValueError("selection namespace must be non-empty ASCII text")
    frozen = tuple(dict(row) for row in rows)
    _validate(frozen)
    selected = []
    for tier in TIERS:
        candidates = [row for row in frozen if row["tier"] == tier]
        chosen = min(
            candidates,
            key=lambda row: (
                sha256(
                    f"{namespace}\0{row['sample_id']}".encode("utf-8")
                ).hexdigest(),
                str(row["sample_id"]),
            ),
        )
        selected_row = dict(chosen)
        selected_row["selection_rank_sha256"] = sha256(
            f"{namespace}\0{chosen['sample_id']}".encode("utf-8")
        ).hexdigest()
        selected.append(selected_row)
    return tuple(selected)


def render_native_schema_receipt(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Render the selected roster without task, gold, output, or scoring fields."""
    selected = select_native_schema_roster(rows)
    items = [dict(row) for row in selected]
    return {
        "audio_seconds_total": round(sum(float(row["audio_seconds"]) for row in items), 3),
        "carrier": "audio2tool",
        "count": len(items),
        "design": (
            "Identity-only SHA-256 rank selection of one row per tier from the "
            "already-exposed A2T-GROUND-QUAL-104 discovery cohort."
        ),
        "exposure": (
            "Already-exposed cohort; secondary discovery only. Protected confirmation "
            "and test identities remain unopened."
        ),
        "items": items,
        "schema": "saea-a2t-native-schema-roster-v1",
        "selection_namespace": SELECTION_NAMESPACE,
        "selection_proof": {
            "identity_only": True,
            "one_per_tier": True,
            "reversed_input_deterministic": True,
        },
        "split_identity_hash": split_identity_hash(
            str(row["key"]) for row in items
        ),
        "split_name": SPLIT_NAME,
        "split_role": "discovery",
    }
