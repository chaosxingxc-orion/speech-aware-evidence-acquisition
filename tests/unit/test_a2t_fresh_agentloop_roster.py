from __future__ import annotations

import hashlib
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_fresh_agentloop_roster import (
    TIERS,
    build_receipt,
    build_development_receipt,
    select_development_roster,
    select_fresh_roster,
    build_partition_flight_receipt,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _rows(n: int = 20) -> list[dict[str, object]]:
    return [
        {
            "sample_id": f"{tier}:{i:06d}",
            "query_block": f"{tier}:query-{i:06d}",
            "normalized_token_class": f"class-{tier}-{i}",
            "tier": tier,
            "key": f"audio2tool:{tier}:{i:06d}",
            "audio_seconds": 1.0,
        }
        for tier in TIERS
        for i in range(n)
    ]


def test_selects_thirteen_per_tier_and_is_order_independent() -> None:
    rows = _rows()
    chosen = select_fresh_roster(rows, target_per_tier=13)
    assert len(chosen) == 104
    assert {tier: sum(r["tier"] == tier for r in chosen) for tier in TIERS} == {
        tier: 13 for tier in TIERS
    }
    assert chosen == select_fresh_roster(list(reversed(rows)), target_per_tier=13)


def test_excludes_sample_query_and_normalized_equivalence_classes() -> None:
    rows = _rows()
    excluded = rows[0]
    chosen = select_fresh_roster(
        rows,
        excluded_rows=[excluded],
        target_per_tier=13,
    )
    assert excluded["sample_id"] not in {r["sample_id"] for r in chosen}
    assert excluded["query_block"] not in {r["query_block"] for r in chosen}
    assert excluded["normalized_token_class"] not in {
        r["normalized_token_class"] for r in chosen
    }


def test_construction_exclusion_may_be_identity_only() -> None:
    rows = _rows()
    construction = {"sample_id": rows[0]["sample_id"]}
    chosen = select_fresh_roster(rows, construction_rows=[construction])
    assert construction["sample_id"] not in {r["sample_id"] for r in chosen}


def test_refuses_missing_equivalence_metadata_and_test_split() -> None:
    rows = _rows()
    del rows[0]["normalized_token_class"]
    with pytest.raises(ValueError, match="normalized-token"):
        select_fresh_roster(rows)
    with pytest.raises(ValueError, match="test"):
        select_fresh_roster(rows, source_split_role="test")


def test_receipt_is_auditable_and_declares_zero_contacts() -> None:
    rows = _rows()
    receipt = build_receipt(
        rows,
        source_name="fixture-source",
        source_sha256="a" * 64,
        target_per_tier=13,
    )
    assert receipt["count"] == 104
    assert receipt["contacts"] == {"model": 0, "network": 0, "scorer": 0, "audio": 0}
    assert receipt["selection"]["uses_test"] is False
    assert receipt["selection"]["uses_normalized_token_text"] is False
    assert (
        receipt["split_identity_hash"]
        == hashlib.sha256(
            "\n".join(sorted(r["key"] for r in receipt["items"])).encode("ascii")
        ).hexdigest()
    )


def _kb_rows(n: int = 14) -> list[A2tKbRow]:
    return [
        A2tKbRow(
            unit_id=f"{tier}:{i:06d}",
            tier=tier,
            query_idx=i + 100 * number,
            text=f"Turn on lamp {i} in {tier}",
            domain="home",
            category="light",
            tool_id=1,
            tool_name=f"tool_{number}",
            arg_signature=(),
            arg_pairs=(),
            call_render="tool()",
            extra_call_names=(),
            call_count=1,
            sample_ids=(f"{tier}:{i:06d}",),
            item_ids=(i,),
            media_relpath_by_sample_id={},
            speaker_ids=(),
        )
        for number, tier in enumerate(TIERS)
        for i in range(n)
    ]


def test_development_selector_normalizes_text_and_keeps_query_blocks_disjoint() -> None:
    rows = _kb_rows()
    selected = select_development_roster(rows, target_per_tier=13)
    assert len(selected) == 104
    assert len({r.query_idx for r in selected}) == 104
    assert all(r.text == r.text for r in selected)


def test_development_receipt_lists_complete_build_exclusions_and_tool_retention() -> (
    None
):
    rows = _kb_rows()
    receipt = build_development_receipt(
        rows, source_name="fixture", source_sha256="b" * 64
    )
    excluded = receipt["build_exclusions"]
    assert receipt["count"] == 104
    assert len(excluded["unit_ids"]) == 104
    assert len(excluded["query_blocks"]) == 104
    assert len(excluded["normalized_token_classes"]) == 104
    assert receipt["build_index"]["selected_gold_tools_retained"] is True
    assert receipt["contacts"] == {"model": 0, "network": 0, "scorer": 0, "audio": 0}


def test_development_selector_skips_query_block_collisions() -> None:
    rows = _kb_rows()
    rows[1] = A2tKbRow(**{**rows[1].__dict__, "query_idx": rows[0].query_idx})
    selected = select_development_roster(rows)
    assert len({r.query_idx for r in selected}) == len(selected)


def test_partition_flight_receipt_resolves_eval_items_and_hashes_without_text() -> None:
    rows = _kb_rows(14)
    eval_items = tuple((r.tier, r.item_ids[0], r.text, r.tool_name) for r in rows)
    partition = SimpleNamespace(
        eval_items=eval_items, construction=tuple(), eval_blocks=tuple()
    )
    metadata = {
        f"{r.tier}:{r.item_ids[0]:06d}": ("audio.wav", "a" * 64, 1.0) for r in rows
    }
    receipt = build_partition_flight_receipt(
        rows, partition, exposed_sample_ids=(), carrier_metadata=metadata
    )
    assert receipt["count"] == 104
    assert receipt["status"] == "PREPARED_NOT_CONTACT_AUTHORITY"
    assert receipt["tier_counts"] == {tier: 13 for tier in TIERS}
    assert all("text" not in item for item in receipt["items"])
    assert all(
        len(item["normalized_token_class_sha256"]) == 64 for item in receipt["items"]
    )
    assert all(
        item["audio_seconds"] > 0 and len(item["audio_sha256"]) == 64
        for item in receipt["items"]
    )


def test_partition_receipt_rejects_missing_audio_metadata() -> None:
    rows = _kb_rows(14)
    eval_items = tuple((r.tier, r.item_ids[0], r.text, r.tool_name) for r in rows)
    with pytest.raises(ValueError, match="audio metadata"):
        build_partition_flight_receipt(
            rows,
            SimpleNamespace(eval_items=eval_items, construction=()),
            exposed_sample_ids=(),
            carrier_metadata={},
        )
