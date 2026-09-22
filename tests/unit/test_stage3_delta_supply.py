"""Stage-3 S3-6 proof obligation: the context-supply route test (candidate-
bound, cap 8, twin derangement) -- docs/superpowers/specs/2026-09-22-
stage3-tfrl-base-loop-engineering.md section S3-6 and "Proof obligations".

Covers ``rails.stage3_delta_supply.select_stage3_delta_values`` (the
selection algorithm) and ``scripts/build_slurp_stage3_delta_twin.py`` (the
derangement generator), on synthetic fixtures only.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.knowledge_provider import (
    KNOWLEDGE_PROVIDERS,
    Stage3DeltaCandidateProvider,
    resolve_provider,
)
from speech_aware_evidence_acquisition.rails.stage3_delta_supply import (
    DEFAULT_STAGE3_DELTA_CAP,
    STAGE3_DELTA_CONTEXT_PROVIDER_ID,
    DeltaCandidate,
    Stage3DeltaSupplyError,
    select_stage3_delta_values,
    stage3_delta_selection_receipt,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
TWIN_SCRIPT_PATH = REPO_ROOT / "scripts" / "build_slurp_stage3_delta_twin.py"

_spec = importlib.util.spec_from_file_location("_build_slurp_stage3_delta_twin", TWIN_SCRIPT_PATH)
_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)  # type: ignore[union-attr]

derange_facet_assignment = _module.derange_facet_assignment
build_twin_document = _module.build_twin_document
Stage3DeltaTwinError = _module.Stage3DeltaTwinError


# ---------------------------------------------------------------------------
# select_stage3_delta_values
# ---------------------------------------------------------------------------


def _candidates() -> tuple[DeltaCandidate, ...]:
    return (
        DeltaCandidate("delta:1:aaaaaaaaaaaa", ("stage3-delta-target:alarm_set",), 0.9),
        DeltaCandidate("delta:1:bbbbbbbbbbbb", ("stage3-delta-target:alarm_set",), 0.5),
        DeltaCandidate("delta:1:cccccccccccc", ("stage3-delta-target:play_music",), 0.95),
        DeltaCandidate("delta:1:dddddddddddd", ("stage3-delta-target:alarm_set", "stage3-delta-target:play_music"), 0.7),
    )


def test_selects_only_deltas_whose_facets_intersect_the_candidates() -> None:
    selected = select_stage3_delta_values(("stage3-delta-target:alarm_set",), _candidates())
    assert set(selected) == {
        "delta:1:aaaaaaaaaaaa",
        "delta:1:bbbbbbbbbbbb",
        "delta:1:dddddddddddd",
    }


def test_orders_by_prior_score_descending() -> None:
    selected = select_stage3_delta_values(("stage3-delta-target:alarm_set",), _candidates())
    assert selected[0] == "delta:1:aaaaaaaaaaaa"  # 0.9 highest among matches
    assert selected[-1] == "delta:1:bbbbbbbbbbbb"  # 0.5 lowest


def test_caps_at_the_requested_count() -> None:
    many = tuple(
        DeltaCandidate(f"delta:1:{index:012d}".replace(" ", "0"), ("stage3-delta-target:alarm_set",), float(index))
        for index in range(20)
    )
    selected = select_stage3_delta_values(("stage3-delta-target:alarm_set",), many, cap=8)
    assert len(selected) == 8
    assert selected == select_stage3_delta_values(
        ("stage3-delta-target:alarm_set",), many, cap=DEFAULT_STAGE3_DELTA_CAP
    )


def test_no_matching_candidate_returns_empty_never_raises() -> None:
    assert select_stage3_delta_values(("stage3-delta-target:nowhere",), _candidates()) == ()
    assert select_stage3_delta_values((), _candidates()) == ()
    assert select_stage3_delta_values(("x",), ()) == ()


def test_tie_break_is_value_id_ascending() -> None:
    tied = (
        DeltaCandidate("delta:1:zzzzzzzzzzzz", ("stage3-delta-target:t",), 0.5),
        DeltaCandidate("delta:1:aaaaaaaaaaaa", ("stage3-delta-target:t",), 0.5),
    )
    selected = select_stage3_delta_values(("stage3-delta-target:t",), tied)
    assert selected == ("delta:1:aaaaaaaaaaaa", "delta:1:zzzzzzzzzzzz")


def test_cap_must_be_a_positive_integer() -> None:
    with pytest.raises(Stage3DeltaSupplyError, match="positive integer"):
        select_stage3_delta_values(("t",), _candidates(), cap=0)


def test_delta_candidate_validates_its_own_fields() -> None:
    with pytest.raises(Stage3DeltaSupplyError, match="associated_facet_ids"):
        DeltaCandidate("delta:1:aaaaaaaaaaaa", (), 0.1).validate()


def test_receipt_carries_no_content_only_identities_and_counts() -> None:
    selected = select_stage3_delta_values(("stage3-delta-target:alarm_set",), _candidates())
    receipt = stage3_delta_selection_receipt(
        sample_id="row-1",
        candidate_facet_ids=("stage3-delta-target:alarm_set",),
        deltas=_candidates(),
        selected_value_ids=selected,
        cap=8,
    )
    assert receipt["selected_count"] == len(selected)
    assert receipt["delta_pool_size"] == 4
    assert set(receipt["selected_value_ids"]) == set(selected)


# ---------------------------------------------------------------------------
# The twin generator: seeded derangement, zero fixed points, content preserved.
# ---------------------------------------------------------------------------


def _authored_rows(n: int) -> list[dict[str, object]]:
    return [
        {
            "value_id": f"delta:1:{index:012d}",
            "content": f"Synthetic statement {index}.",
            "associated_facet_ids": [f"stage3-delta-target:target-{index}"],
            "source_sample_ids": [f"row-{index}"],
            "provenance_refs": [f"advantage:SAEA-TEST-RUN:row-{index}:0:1"],
            "task_target": f"exemplar-note:target-{index}",
            "prior_score": float(index) / 10,
        }
        for index in range(n)
    ]


def test_derangement_has_zero_fixed_points_and_preserves_content() -> None:
    rows = _authored_rows(6)
    twinned = derange_facet_assignment(rows, seed=20260922)
    assert len(twinned) == len(rows)
    for original, twin in zip(rows, twinned):
        assert original["associated_facet_ids"] != twin["associated_facet_ids"]
        assert original["content"] == twin["content"]
        assert original["value_id"] == twin["value_id"]
        assert original["prior_score"] == twin["prior_score"]
    # Every donated facet set is SOME other row's original set.
    original_facet_sets = [tuple(row["associated_facet_ids"]) for row in rows]
    for twin in twinned:
        assert tuple(twin["associated_facet_ids"]) in original_facet_sets


def test_derangement_is_deterministic_for_a_fixed_seed() -> None:
    rows = _authored_rows(9)
    first = derange_facet_assignment(rows, seed=42)
    second = derange_facet_assignment(rows, seed=42)
    assert first == second


def test_derangement_refuses_fewer_than_two_rows() -> None:
    with pytest.raises(Stage3DeltaTwinError, match="at least two rows"):
        derange_facet_assignment(_authored_rows(1), seed=1)


def test_build_twin_document_end_to_end() -> None:
    document = {
        "schema": "saea-stage3-authored-deltas-v1",
        "iteration": 1,
        "rows": _authored_rows(5),
    }
    twin = build_twin_document(document, seed=20260922)
    assert twin["schema"] == document["schema"]
    assert twin["iteration"] == 1
    assert twin["twin_of_seed"] == 20260922
    assert len(twin["rows"]) == 5
    for original, twinned_row in zip(document["rows"], twin["rows"]):
        assert original["associated_facet_ids"] != twinned_row["associated_facet_ids"]


def test_build_twin_document_refuses_wrong_schema() -> None:
    with pytest.raises(Stage3DeltaTwinError, match="expected schema"):
        build_twin_document({"schema": "not-the-right-schema", "rows": _authored_rows(3)}, seed=1)


# ---------------------------------------------------------------------------
# Stage3DeltaCandidateProvider: registered, and matches the pure algorithm.
# ---------------------------------------------------------------------------


def test_provider_is_registered_in_knowledge_providers() -> None:
    assert STAGE3_DELTA_CONTEXT_PROVIDER_ID in KNOWLEDGE_PROVIDERS.names()
    provider = resolve_provider(STAGE3_DELTA_CONTEXT_PROVIDER_ID)
    assert isinstance(provider, Stage3DeltaCandidateProvider)
    assert provider.provider_id == STAGE3_DELTA_CONTEXT_PROVIDER_ID


def test_provider_candidates_matches_the_pure_selection_function() -> None:
    rows = [
        {
            "value_id": candidate.value_id,
            "associated_facet_ids": list(candidate.associated_facet_ids),
            "prior_score": candidate.prior_score,
        }
        for candidate in _candidates()
    ]
    provider = Stage3DeltaCandidateProvider()
    provider.build(rows, policy_id="saea-authored-stage3-deltas-v1")
    ranking = provider.candidates(("stage3-delta-target:alarm_set",), k=8)
    expected = select_stage3_delta_values(("stage3-delta-target:alarm_set",), _candidates())
    assert tuple(entry.entry_id for entry in ranking.entries) == expected
    ranking.validate()  # sorted score-descending, entry_id-ascending tie-break


def test_provider_candidates_requires_build_first() -> None:
    provider = Stage3DeltaCandidateProvider()
    with pytest.raises(Exception, match="build"):
        provider.candidates(("t",), k=8)


def test_provider_fuse_merges_and_keeps_the_higher_score_per_entry() -> None:
    rows = [
        {"value_id": "delta:1:aaaaaaaaaaaa", "associated_facet_ids": ["t"], "prior_score": 0.3},
    ]
    provider = Stage3DeltaCandidateProvider()
    provider.build(rows, policy_id="saea-authored-stage3-deltas-v1")
    low = provider.candidates(("t",), k=8)
    # A second ranking claiming a higher score for the same entry (as fuse()
    # would see from a second source) must win.
    from speech_aware_evidence_acquisition.rails.knowledge_provider import RankedEntry, Ranking

    high = Ranking(
        entries=(RankedEntry(entry_id="delta:1:aaaaaaaaaaaa", score=0.9, provenance={}),),
        index_sha256=low.index_sha256,
        query_sha256=low.query_sha256,
        source="synthetic-other-source",
    )
    fused = provider.fuse([low, high], k=8, policy_id="x")
    assert fused.entries[0].entry_id == "delta:1:aaaaaaaaaaaa"
    assert fused.entries[0].score == pytest.approx(0.9)
