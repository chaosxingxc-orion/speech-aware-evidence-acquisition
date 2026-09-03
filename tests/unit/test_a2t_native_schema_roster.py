import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_native_schema_roster import (
    SELECTION_NAMESPACE,
    SPLIT_NAME,
    select_native_schema_roster,
    render_native_schema_receipt,
)


RECEIPT = Path("docs/receipts/a2t/A2T-GROUND-QUAL-104.json")
EXPECTED = (
    "tier1_direct:000062",
    "tier2_parametric:001693",
    "tier3_multi_intent:002490",
    "tier4_implicit:001628",
    "tier5_needle:001679",
    "tier6_correction:002940",
    "tier7_multiturn:000293",
    "tier8_intent_blending:000052",
)


def _items():
    return json.loads(RECEIPT.read_text(encoding="utf-8"))["items"]


def test_selects_one_identity_only_row_per_tier() -> None:
    selected = select_native_schema_roster(_items())
    assert tuple(row["sample_id"] for row in selected) == EXPECTED
    assert len(selected) == 8
    assert round(sum(row["audio_seconds"] for row in selected), 3) == 45.096


def test_selection_is_invariant_to_reversed_input() -> None:
    assert select_native_schema_roster(_items()) == select_native_schema_roster(
        list(reversed(_items()))
    )


def test_rejects_wrong_population_and_non_identity_fields() -> None:
    with pytest.raises(ValueError, match="104"):
        select_native_schema_roster(_items()[:-1])
    rows = _items()
    rows[0]["task_text"] = "must not be accepted"
    with pytest.raises(ValueError, match="identity-only"):
        select_native_schema_roster(rows)


def test_rendered_receipt_is_identity_only_and_reproducible() -> None:
    receipt = render_native_schema_receipt(_items())
    assert receipt["selection_namespace"] == SELECTION_NAMESPACE
    assert receipt["count"] == 8
    assert receipt["audio_seconds_total"] == 45.096
    assert receipt["split_name"] == SPLIT_NAME
    assert "secondary discovery" in receipt["exposure"]
    assert receipt["split_identity_hash"] == (
        "f95efe70b615d71bb082f9ef804d1fa2b6f04ce4114d5d2694151cbaf44019ba"
    )
    assert set(receipt) == {
        "audio_seconds_total",
        "carrier",
        "count",
        "design",
        "exposure",
        "items",
        "schema",
        "selection_namespace",
        "selection_proof",
        "split_identity_hash",
        "split_name",
        "split_role",
    }
    assert all(set(item) <= {
        "audio_seconds", "audio_sha256", "id", "key", "media_relpath",
        "packet_id", "query_block", "query_idx", "sample_id",
        "selection_rank_sha256", "tier",
    } for item in receipt["items"])
    assert all(
        item["selection_rank_sha256"]
        == hashlib.sha256(
            f"{SELECTION_NAMESPACE}\0{item['sample_id']}".encode("utf-8")
        ).hexdigest()
        for item in receipt["items"]
    )
