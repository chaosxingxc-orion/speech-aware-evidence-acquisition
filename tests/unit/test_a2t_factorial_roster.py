from __future__ import annotations

import hashlib

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_factorial_roster import (
    FactorialRosterError,
    IdentityCandidate,
    build_factorial_roster_receipt,
    select_factorial_roster,
)
from speech_aware_evidence_acquisition.analysis.a2t_fresh_agentloop_roster import (
    TIERS,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("ascii")).hexdigest()


def _candidates(per_tier: int = 24) -> tuple[IdentityCandidate, ...]:
    return tuple(
        IdentityCandidate(
            sample_id=f"{tier}:{index:06d}",
            tier=tier,
            item_id=index,
            query_idx=tier_index * 1000 + index,
            normalized_token_class_sha256=_sha(f"class:{tier}:{index}"),
            media_relpath=f"datasets/audio2tool/public/{tier}/{index}.wav",
            audio_sha256=_sha(f"audio:{tier}:{index}"),
            audio_seconds=1.0 + index / 100.0,
        )
        for tier_index, tier in enumerate(TIERS)
        for index in range(per_tier)
    )


def test_selects_sixteen_per_tier_without_identity_equivalence_overlap() -> None:
    candidates = _candidates()
    selected = select_factorial_roster(
        candidates,
        target_per_tier=16,
        namespace="factorial-roster-test",
    )

    assert len(selected) == 128
    assert selected == select_factorial_roster(
        tuple(reversed(candidates)),
        target_per_tier=16,
        namespace="factorial-roster-test",
    )
    assert {tier: sum(row.tier == tier for row in selected) for tier in TIERS} == {
        tier: 16 for tier in TIERS
    }
    assert len({row.sample_id for row in selected}) == 128
    assert len({row.query_idx for row in selected}) == 128
    assert len({row.normalized_token_class_sha256 for row in selected}) == 128


def test_selection_excludes_all_three_leakage_identities_and_internal_classes() -> None:
    candidates = list(_candidates())
    first, second, third = candidates[:3]
    candidates[3] = IdentityCandidate(
        **{
            **candidates[3].__dict__,
            "normalized_token_class_sha256": candidates[4].normalized_token_class_sha256,
        }
    )
    selected = select_factorial_roster(
        candidates,
        excluded_sample_ids={first.sample_id},
        excluded_query_indices={second.query_idx},
        excluded_normalized_class_sha256s={third.normalized_token_class_sha256},
        target_per_tier=16,
        namespace="factorial-roster-exclusion-test",
    )

    assert first.sample_id not in {row.sample_id for row in selected}
    assert second.query_idx not in {row.query_idx for row in selected}
    assert third.normalized_token_class_sha256 not in {
        row.normalized_token_class_sha256 for row in selected
    }
    assert len({row.normalized_token_class_sha256 for row in selected}) == 128


def test_roster_fails_when_any_tier_has_less_than_sixteen_safe_rows() -> None:
    candidates = tuple(
        row
        for row in _candidates()
        if row.tier != TIERS[0] or row.item_id < 15
    )
    with pytest.raises(FactorialRosterError, match=TIERS[0]):
        select_factorial_roster(candidates, target_per_tier=16)


def test_receipt_is_identity_only_hash_bound_and_declares_zero_contacts() -> None:
    receipt = build_factorial_roster_receipt(
        _candidates(),
        source_path="docs/receipts/knowledge/a2t-partition-proposal.json",
        source_sha256="a" * 64,
        source_split_identity_sha256="b" * 64,
        excluded_sample_ids=(),
        excluded_query_indices=(),
        excluded_normalized_class_sha256s=(),
        target_per_tier=16,
        namespace="factorial-roster-receipt-test",
    )

    assert receipt["schema"] == "saea-a2t-select-fill-factorial-roster-v1"
    assert receipt["status"] == "PREPARED_NOT_CONTACT_AUTHORITY"
    assert receipt["count"] == 128
    assert receipt["tier_counts"] == {tier: 16 for tier in TIERS}
    assert receipt["contacts"] == {
        "audio_decode": 0,
        "embedding": 0,
        "frozen_core": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    rendered = str(receipt).casefold()
    assert "expected_tool_call" not in rendered
    assert "extracted_params" not in rendered
    assert "additional_tool_calls" not in rendered
    assert "query_text" not in rendered
    assert all("selection_rank_sha256" in item for item in receipt["items"])
