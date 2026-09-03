import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_canonical_family_secondary_roster import (
    DEFAULT_NAMESPACE,
    TIER_ORDER,
    build_receipt,
    select_rows,
)


def row(tier: str, number: int, block: str | None = None) -> dict[str, object]:
    return {
        "sample_id": f"{tier}:{number:06d}",
        "key": f"audio2tool:{tier}:{number:06d}",
        "tier": tier,
        "query_block": block or f"{tier}:query-{number}",
        "audio_seconds": 1.25,
    }


def test_selects_one_per_tier_deterministically_and_excludes_ids() -> None:
    source = [item for tier in TIER_ORDER for item in (row(tier, 1), row(tier, 2))]
    selected = select_rows(source, {f"{TIER_ORDER[0]}:000001"})
    assert [item["tier"] for item in selected] == list(TIER_ORDER)
    assert len({item["query_block"] for item in selected}) == 8
    assert select_rows(list(reversed(source)), {f"{TIER_ORDER[0]}:000001"}) == selected


def test_rejects_missing_tier_or_duplicate_query_block() -> None:
    source = [row(tier, 1) for tier in TIER_ORDER]
    source[0]["tier"] = "unknown"
    with pytest.raises(ValueError, match="tier"):
        select_rows(source, set())

    source = [row(tier, 1) for tier in TIER_ORDER]
    source[1]["query_block"] = source[0]["query_block"]
    with pytest.raises(ValueError, match="query block"):
        select_rows(source, set())


def test_rejects_insufficient_eligible_tier() -> None:
    source = [row(tier, 1) for tier in TIER_ORDER]
    with pytest.raises(ValueError, match="eligible"):
        select_rows(source, {f"{TIER_ORDER[0]}:000001"})


def test_build_receipt_hashes_sources_and_has_no_content_fields(tmp_path: Path) -> None:
    source_path = tmp_path / "ground.json"
    exclusion_path = tmp_path / "excluded.json"
    source_path.write_text(
        json.dumps(
            {"items": [row(tier, number) for tier in TIER_ORDER for number in (1, 2)]}
        ),
        encoding="utf-8",
    )
    exclusion_path.write_text(
        json.dumps({"items": [row(TIER_ORDER[0], 1)]}), encoding="utf-8"
    )
    receipt = build_receipt(source_path, (exclusion_path,), namespace=DEFAULT_NAMESPACE)
    assert receipt["execution_profile"] == "model-free-check"
    assert receipt["contacts"] == {"model": 0, "scorer": 0, "network": 0, "audio": 0}
    assert receipt["count"] == 8
    assert receipt["selected_audio_seconds_total"] == 10.0
    assert (
        receipt["source"]["sha256"]
        == hashlib.sha256(source_path.read_bytes()).hexdigest()
    )
    expected_source_identity = hashlib.sha256(
        "\n".join(
            sorted(
                f"audio2tool:{tier}:{number:06d}"
                for tier in TIER_ORDER
                for number in (1, 2)
            )
        ).encode("ascii")
    ).hexdigest()
    assert receipt["source"]["split_identity_hash"] == expected_source_identity
    assert (
        receipt["exclusions"][0]["sha256"]
        == hashlib.sha256(exclusion_path.read_bytes()).hexdigest()
    )
    assert receipt["selection"]["uses_gold"] is False
    assert receipt["selection"]["uses_audio"] is False
    assert receipt["split_identity_hash"]


def test_real_receipts_are_96_eligible_and_eight_selected() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "docs/receipts/a2t/A2T-GROUND-QUAL-104.json"
    exclusions = tuple(
        root / "docs/receipts/a2t" / name
        for name in (
            "A2T-G5-FIXED16-IDENTITY.json",
            "A2T-G6-FAMILY-SWEEP-FIXED16.json",
            "A2T-G7-EXAMPLE-FIXED16.json",
            "A2T-G8-ACTION-SUPPORT-FIXED16.json",
            "A2T-G8B-ACTION-SUPPORT-FIXED16.json",
            "A2T-G8C-ACTION-SUPPORT-FIXED12.json",
            "A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json",
        )
    )
    receipt = build_receipt(source, exclusions)
    assert receipt["selection"]["eligible_count"] == 96
    assert [entry["count"] for entry in receipt["exclusions"]] == [
        16,
        16,
        16,
        16,
        16,
        12,
        8,
    ]
    assert receipt["selection"]["eligible_per_tier"] == dict.fromkeys(TIER_ORDER, 12)
    assert receipt["selected_tier_counts"] == dict.fromkeys(TIER_ORDER, 1)
    assert receipt["selected_query_block_count"] == 8
    assert receipt["source"]["split_identity_hash"] == (
        "c6bb080bb264733087b3da352fe930702ec6509bc02e6a639b0f4c30c5017dac"
    )
    assert all("audio_sha256" in row for row in receipt["selected"])
    assert all("packet_id" in row for row in receipt["selected"])
    materialized = json.loads(
        (
            root / "docs/receipts/a2t/A2T-CANONICAL-FAMILY-SECONDARY-FIXED8.json"
        ).read_text(encoding="utf-8")
    )
    assert materialized == receipt
