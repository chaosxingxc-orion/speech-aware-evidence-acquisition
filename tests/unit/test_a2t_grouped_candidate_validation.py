from __future__ import annotations

from dataclasses import replace
import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_grouped_candidate_validation import (
    GroupedCandidateValidationError,
    analyze_grouped_candidate_validation,
    assign_grouped_validation_folds,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _row(
    unit_id: str,
    *,
    query_idx: int,
    text: str,
    tool: str,
    tier: str = "tier1_direct",
    extras: tuple[str, ...] = (),
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=unit_id,
        tier=tier,
        query_idx=query_idx,
        text=text,
        domain="private",
        category="private",
        tool_id=query_idx,
        tool_name=tool,
        arg_signature=(),
        arg_pairs=(),
        call_render="PRIVATE",
        extra_call_names=extras,
        call_count=1 + len(extras),
        sample_ids=(unit_id,),
        item_ids=(query_idx,),
        media_relpath_by_sample_id={},
        speaker_ids=("private",),
    )


def _rows() -> tuple[A2tKbRow, ...]:
    return (
        _row("u0", query_idx=0, text="alpha lamp", tool="alphaTool"),
        _row(
            "u1",
            query_idx=0,
            text="alpha lamp variant",
            tool="alphaTool",
            tier="tier2_parametric",
        ),
        _row("u2", query_idx=2, text="beta fan", tool="betaTool"),
        _row("u3", query_idx=3, text="BETA, FAN!", tool="betaTool"),
        _row("u4", query_idx=4, text="gamma lock", tool="gammaTool"),
        _row("u5", query_idx=5, text="delta door", tool="deltaTool"),
        _row("u6", query_idx=6, text="epsilon room", tool="epsilonTool"),
        _row("u7", query_idx=7, text="zeta player", tool="zetaTool"),
        _row("u8", query_idx=8, text="eta volume", tool="etaTool"),
        _row("u9", query_idx=9, text="theta alarm", tool="thetaTool"),
    )


def _fold_by_unit(folds: tuple[tuple[str, ...], ...]) -> dict[str, int]:
    return {unit_id: fold_id for fold_id, fold in enumerate(folds) for unit_id in fold}


def test_assignment_groups_query_blocks_and_normalized_text_twins() -> None:
    folds = assign_grouped_validation_folds(_rows(), seed=41, fold_count=3)
    by_unit = _fold_by_unit(folds)

    assert by_unit["u0"] == by_unit["u1"]
    assert by_unit["u2"] == by_unit["u3"]
    assert sorted(unit_id for fold in folds for unit_id in fold) == [
        f"u{index}" for index in range(10)
    ]
    assert all(fold for fold in folds)


def test_assignment_groups_duplicates_under_alternate_representation() -> None:
    rows = _rows()
    folds = assign_grouped_validation_folds(
        rows,
        seed=41,
        fold_count=3,
        alternate_text_by_unit_id={
            "u8": "The same prior dialogue and request",
            "u9": "  the SAME prior dialogue and request ",
        },
    )
    by_unit = _fold_by_unit(folds)

    assert by_unit["u8"] == by_unit["u9"]


def test_assignment_is_order_invariant_and_label_blind() -> None:
    rows = _rows()
    mutated = tuple(
        replace(row, tool_name="replacementTool", extra_call_names=(), call_count=1)
        for row in rows
    )

    expected = assign_grouped_validation_folds(rows, seed=41, fold_count=3)
    reversed_result = assign_grouped_validation_folds(
        tuple(reversed(rows)), seed=41, fold_count=3
    )
    label_mutated = assign_grouped_validation_folds(mutated, seed=41, fold_count=3)

    assert expected == reversed_result == label_mutated


def test_grouped_out_of_fold_analysis_reports_worst_fold_and_subgroups() -> None:
    rows = _rows()
    registry = tuple(sorted({row.tool_name for row in rows}))

    result = analyze_grouped_candidate_validation(
        construction_rows=rows,
        registry_tool_names=registry,
        seed=41,
        fold_count=3,
        k_grid=(1, 3, 8),
    )
    report = result.report

    assert report["schema"] == "saea-a2t-grouped-candidate-validation-v2"
    assert report["split_policy"]["label_blind"] is True
    assert report["split_policy"]["groups_query_idx"] is True
    assert report["split_policy"]["groups_normalized_text_twins"] is True
    assert report["split_policy"]["groups_bm25_token_sequence_twins"] is True
    assert report["split_policy"]["component_identity_binds_all_member_ids"] is True
    assert report["population"]["unit_count"] == 10
    assert report["population"]["fold_count"] == 3
    assert sum(fold["validation_units"] for fold in report["folds"]) == 10
    assert (
        report["cross_fold_duplicate_audit"]["normalized_text_twin_validation_units"]
        == 0
    )
    assert set(report["aggregate"]) >= {
        "k_metrics",
        "per_tier",
        "multi_call",
        "single_call",
        "worst_fold_full_set_coverage",
        "near_duplicate_sensitivity",
    }
    near = report["aggregate"]["near_duplicate_sensitivity"]
    assert near["threshold"] == 0.8
    assert (
        near["no_near_duplicate"]["unit_count"] + near["near_duplicate"]["unit_count"]
        == 10
    )
    assert report["quality_gate"]["near_duplicate_sensitivity_measured"] is True
    assert json.loads(result.canonical_json) == report
    assert "alpha lamp" not in result.canonical_json


def test_grouped_analysis_applies_public_registry_keys_to_every_fold() -> None:
    rows = (
        _row("u0", query_idx=0, text="make the room bright", tool="alphaTool"),
        _row("u1", query_idx=1, text="reduce cabin heat", tool="betaTool"),
        _row("u2", query_idx=2, text="illuminate the room", tool="alphaTool"),
        _row("u3", query_idx=3, text="lower the temperature", tool="betaTool"),
    )
    public_keys = {
        "alphaTool": "Makes a room bright and illuminates it.",
        "betaTool": "Reduces cabin heat and lowers temperature.",
    }

    baseline = analyze_grouped_candidate_validation(
        construction_rows=rows,
        registry_tool_names=("alphaTool", "betaTool"),
        seed=41,
        fold_count=2,
        k_grid=(1,),
    ).report
    result = analyze_grouped_candidate_validation(
        construction_rows=rows,
        registry_tool_names=("alphaTool", "betaTool"),
        seed=41,
        fold_count=2,
        k_grid=(1,),
        public_tool_key_text_by_name=public_keys,
    ).report

    assert result["retrieval_key_design"]["public_tool_key_count"] == 2
    assert (
        result["aggregate"]["k_metrics"]["1"]["full_set_coverage"]
        > baseline["aggregate"]["k_metrics"]["1"]["full_set_coverage"]
    )
    assert "Reduces cabin heat" not in json.dumps(result)


@pytest.mark.parametrize(
    ("fold_count", "message"),
    ((1, "fold_count"), (20, "fewer grouped components")),
)
def test_assignment_rejects_invalid_fold_count(fold_count: int, message: str) -> None:
    with pytest.raises(GroupedCandidateValidationError, match=message):
        assign_grouped_validation_folds(_rows(), seed=1, fold_count=fold_count)
