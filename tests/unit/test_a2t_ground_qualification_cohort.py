from __future__ import annotations

from dataclasses import dataclass, fields
import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_ground_qualification_cohort import (
    GroundQualificationCohortError,
    GroundRosterSource,
    build_ground_roster_receipt,
    select_ground_roster,
)


@dataclass(frozen=True)
class _Candidate:
    sample_id: str
    media_relpath: str
    audio_seconds: float
    audio_sha256: str


def _candidate(tier: str, index: int) -> _Candidate:
    return _Candidate(
        sample_id=f"{tier}:{index:06d}",
        media_relpath=f"datasets/audio2tool/public/{tier}_audios/query_{index:05d}/x.wav",
        audio_seconds=float(index + 1),
        audio_sha256=f"{index + 1:064x}"[-64:],
    )


def test_select_ground_roster_excludes_two_disjoint_block_sets_and_is_order_independent() -> (
    None
):
    tiers = ("tier1_direct", "tier2_parametric")
    parent = tuple(
        _candidate(tier, offset + index)
        for offset, tier in ((0, tiers[0]), (100, tiers[1]))
        for index in range(6)
    )
    excluded_g1 = (parent[0], parent[6])
    excluded_cpv2 = (parent[1], parent[7])

    first = select_ground_roster(
        parent,
        (excluded_g1, excluded_cpv2),
        tiers=tiers,
        per_tier=2,
        namespace="ground-test",
    )
    second = select_ground_roster(
        tuple(reversed(parent)),
        (tuple(reversed(excluded_g1)), tuple(reversed(excluded_cpv2))),
        tiers=tiers,
        per_tier=2,
        namespace="ground-test",
    )

    assert first == second
    assert len(first) == 4
    assert {item.tier for item in first} == set(tiers)
    assert not {item.query_block for item in first} & {
        "tier1_direct:query-00000",
        "tier1_direct:query-00001",
        "tier2_parametric:query-00100",
        "tier2_parametric:query-00101",
    }


def test_select_ground_roster_refuses_overlap_between_exclusion_receipts() -> None:
    parent = tuple(_candidate("tier1_direct", index) for index in range(5))
    with pytest.raises(
        GroundQualificationCohortError, match="excluded receipts overlap"
    ):
        select_ground_roster(
            parent,
            ((parent[0],), (parent[0],)),
            tiers=("tier1_direct",),
            per_tier=1,
            namespace="ground-test",
        )


def test_build_ground_roster_receipt_is_stable_and_contains_no_task_answer_fields() -> (
    None
):
    tiers = ("tier1_direct", "tier2_parametric")
    selected = select_ground_roster(
        tuple(
            _candidate(tier, offset + index)
            for offset, tier in ((0, tiers[0]), (100, tiers[1]))
            for index in range(4)
        ),
        ((), ()),
        tiers=tiers,
        per_tier=2,
        namespace="ground-test",
    )
    sources = (
        GroundRosterSource(
            receipt="g1.json",
            sha256="1" * 64,
            split_identity_hash="2" * 64,
            item_count=2,
            query_block_count=2,
        ),
        GroundRosterSource(
            receipt="cpv2.json",
            sha256="3" * 64,
            split_identity_hash="4" * 64,
            item_count=2,
            query_block_count=2,
        ),
    )

    receipt = build_ground_roster_receipt(
        selected,
        split_name="GROUND-4",
        namespace="ground-test",
        parent_receipt="parent.json",
        parent_receipt_sha256="5" * 64,
        parent_split_identity_hash="6" * 64,
        excluded_sources=sources,
        materialization_study_commit="7" * 40,
        expected_tiers=tiers,
        per_tier=2,
    )
    reversed_receipt = build_ground_roster_receipt(
        tuple(reversed(selected)),
        split_name="GROUND-4",
        namespace="ground-test",
        parent_receipt="parent.json",
        parent_receipt_sha256="5" * 64,
        parent_split_identity_hash="6" * 64,
        excluded_sources=tuple(reversed(sources)),
        materialization_study_commit="7" * 40,
        expected_tiers=tiers,
        per_tier=2,
    )

    assert receipt == reversed_receipt
    assert receipt["count"] == 4
    assert receipt["strata_counts"] == {
        "tier1_direct": 2,
        "tier2_parametric": 2,
    }
    assert receipt["selection_proof"]["query_block_overlap_count"] == 0
    rendered = json.dumps(receipt, sort_keys=True).casefold()
    for forbidden in (
        "expected_tool_call",
        "tool_name",
        "gold",
        "prior_output",
        "prior_score",
        "reward",
        "query_text",
    ):
        assert forbidden not in rendered


def test_runtime_candidate_and_selected_types_cannot_carry_task_answer_fields() -> None:
    selected = select_ground_roster(
        tuple(_candidate("tier1_direct", index) for index in range(3)),
        ((), ()),
        tiers=("tier1_direct",),
        per_tier=1,
        namespace="ground-test",
    )[0]
    allowed = {
        "sample_id",
        "tier",
        "media_relpath",
        "audio_seconds",
        "audio_sha256",
        "query_block",
        "selection_rank_sha256",
    }
    assert {field.name for field in fields(selected)} == allowed
