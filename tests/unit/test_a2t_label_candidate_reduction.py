"""Tests for construction-only Audio2Tool label candidate reduction."""

from __future__ import annotations

import json
import math

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_label_candidate_reduction import (
    LabelCandidateReductionError,
    analyze_label_candidate_reduction,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _row(
    *,
    tier: str,
    query_idx: int,
    text: str,
    tool: str,
    extras: tuple[str, ...] = (),
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=f"{tier}:{query_idx:06d}",
        tier=tier,
        query_idx=query_idx,
        text=text,
        domain="private",
        category="private",
        tool_id=query_idx,
        tool_name=tool,
        arg_signature=(),
        arg_pairs=(),
        call_render="PRIVATE CALL RENDER",
        extra_call_names=extras,
        call_count=1 + len(extras),
        sample_ids=(f"{tier}:{query_idx:06d}",),
        item_ids=(query_idx,),
        media_relpath_by_sample_id={},
        speaker_ids=("PRIVATE SPEAKER",),
    )


def _build_rows() -> tuple[A2tKbRow, ...]:
    return (
        _row(
            tier="tier1_direct",
            query_idx=1,
            text="alphaonly command",
            tool="alphaTool",
        ),
        _row(
            tier="tier1_direct",
            query_idx=2,
            text="betaonly command",
            tool="betaTool",
        ),
        _row(
            tier="tier1_direct",
            query_idx=3,
            text="gammaonly command",
            tool="gammaTool",
        ),
    )


def _validation_rows() -> tuple[A2tKbRow, ...]:
    return (
        _row(
            tier="tier2_parametric",
            query_idx=11,
            text="alphaonly request",
            tool="alphaTool",
        ),
        _row(
            tier="tier3_multi_intent",
            query_idx=12,
            text="betaonly gammaonly request",
            tool="betaTool",
            extras=("gammaTool",),
        ),
    )


def test_collapses_ranked_construction_keys_to_unique_tool_candidates() -> None:
    result = analyze_label_candidate_reduction(
        construction_rows=_build_rows(),
        validation_rows=_validation_rows(),
        registry_tool_names=("alphaTool", "betaTool", "gammaTool", "unusedTool"),
        k_grid=(1, 2, 4),
    ).report

    assert result["population"] == {
        "construction_unit_count": 3,
        "validation_unit_count": 2,
        "registry_label_count": 4,
        "construction_observed_label_count": 3,
        "validation_required_unique_label_count": 3,
        "validation_required_call_occurrence_count": 3,
    }
    by_id = {row["unit_id"]: row for row in result["samples"]}
    assert by_id["tier2_parametric:000011"]["ranked_tool_names"][:2] == [
        "alphaTool",
        "betaTool",
    ]
    assert by_id["tier3_multi_intent:000012"]["ranked_tool_names"][:2] == [
        "betaTool",
        "gammaTool",
    ]
    assert by_id["tier3_multi_intent:000012"]["last_required_label_rank"] == 2

    at_one = result["k_metrics"]["1"]
    assert at_one["required_item_recall"] == pytest.approx(2 / 3)
    assert at_one["full_set_coverage"] == 0.5
    assert at_one["precision"] == 1.0
    assert at_one["mean_distractor_burden"] == 0.0

    at_two = result["k_metrics"]["2"]
    assert at_two["required_item_recall"] == 1.0
    assert at_two["full_set_coverage"] == 1.0
    assert at_two["precision"] == pytest.approx(0.75)
    assert at_two["mean_distractor_burden"] == pytest.approx(0.5)
    assert at_two["positive_score_required_item_recall"] == 1.0
    assert at_two["positive_score_full_set_coverage"] == 1.0
    assert at_two["mean_zero_score_fallback_count"] == pytest.approx(0.5)
    assert at_two["maximum_decision_space_reduction_bits"] == pytest.approx(1.0)


def test_reports_per_tier_full_set_coverage_and_required_cardinality() -> None:
    report = analyze_label_candidate_reduction(
        construction_rows=_build_rows(),
        validation_rows=_validation_rows(),
        registry_tool_names=("alphaTool", "betaTool", "gammaTool", "unusedTool"),
        k_grid=(1, 2),
    ).report

    assert report["required_label_cardinality"] == {"1": 1, "2": 1}
    assert report["last_required_label_rank"] == {
        "minimum": 1,
        "median": 2,
        "p90": 2,
        "maximum": 2,
    }
    assert report["per_tier"]["tier2_parametric"]["2"]["full_set_coverage"] == 1.0
    assert report["per_tier"]["tier3_multi_intent"]["1"]["full_set_coverage"] == 0.0


def test_duplicate_required_tool_occurrences_are_preserved_as_a_separate_burden() -> (
    None
):
    validation = (
        _row(
            tier="tier8_intent_blending",
            query_idx=20,
            text="alphaonly repeated",
            tool="alphaTool",
            extras=("alphaTool",),
        ),
    )

    report = analyze_label_candidate_reduction(
        construction_rows=_build_rows(),
        validation_rows=validation,
        registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
        k_grid=(1,),
    ).report

    assert report["required_label_cardinality"] == {"1": 1}
    assert report["duplicate_required_call_occurrence_count"] == 1
    assert report["k_metrics"]["1"]["full_set_coverage"] == 1.0
    assert report["scope"]["multiplicity_coverage_measured"] is False


def test_canonical_output_is_order_independent_and_excludes_text() -> None:
    args = {
        "registry_tool_names": (
            "alphaTool",
            "betaTool",
            "gammaTool",
            "unusedTool",
        ),
        "k_grid": (2, 1),
    }
    forward = analyze_label_candidate_reduction(
        construction_rows=_build_rows(),
        validation_rows=_validation_rows(),
        **args,
    )
    reverse = analyze_label_candidate_reduction(
        construction_rows=tuple(reversed(_build_rows())),
        validation_rows=tuple(reversed(_validation_rows())),
        registry_tool_names=tuple(reversed(args["registry_tool_names"])),
        k_grid=args["k_grid"],
    )

    assert forward.canonical_json == reverse.canonical_json
    assert json.loads(forward.canonical_json) == forward.report
    assert forward.canonical_json.isascii()
    assert "alphaonly" not in forward.canonical_json
    assert "PRIVATE" not in forward.canonical_json
    assert forward.report["scope"] == {
        "construction_training_rows_only": True,
        "query_idx_block_disjoint_validation": True,
        "perfect_transcript_conditioned": True,
        "runtime_eligible": False,
        "retrieval_coverage_only": True,
        "model_consumption_upper_bound": False,
        "multiplicity_coverage_measured": False,
        "argument_or_value_coverage_measured": False,
        "model_contacts": 0,
        "scorer_contacts": 0,
        "network_contacts": 0,
    }


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("overlap", "query_idx blocks overlap"),
        ("duplicate_registry", "registry tool names"),
        ("unknown_construction", "unknown construction tool"),
        ("unknown_validation", "unknown validation tool"),
        ("bad_k", "k_grid"),
        ("empty_build", "construction_rows"),
        ("empty_validation", "validation_rows"),
    ),
)
def test_fails_closed_on_invalid_boundaries(mutation: str, message: str) -> None:
    build = _build_rows()
    validation = _validation_rows()
    registry: tuple[str, ...] = (
        "alphaTool",
        "betaTool",
        "gammaTool",
        "unusedTool",
    )
    k_grid: tuple[int, ...] = (1, 2)
    if mutation == "overlap":
        validation = (
            _row(
                tier="tier2_parametric",
                query_idx=1,
                text="alphaonly",
                tool="alphaTool",
            ),
        )
    elif mutation == "duplicate_registry":
        registry = ("alphaTool", "alphaTool")
    elif mutation == "unknown_construction":
        build = (
            _row(
                tier="tier1_direct",
                query_idx=1,
                text="unknown",
                tool="ghostTool",
            ),
        )
    elif mutation == "unknown_validation":
        validation = (
            _row(
                tier="tier2_parametric",
                query_idx=11,
                text="unknown",
                tool="ghostTool",
            ),
        )
    elif mutation == "bad_k":
        k_grid = (True, 2)  # type: ignore[assignment]
    elif mutation == "empty_build":
        build = ()
    elif mutation == "empty_validation":
        validation = ()

    with pytest.raises(LabelCandidateReductionError, match=message):
        analyze_label_candidate_reduction(
            construction_rows=build,
            validation_rows=validation,
            registry_tool_names=registry,
            k_grid=k_grid,
        )


def test_decision_reduction_is_zero_when_k_spans_registry() -> None:
    report = analyze_label_candidate_reduction(
        construction_rows=_build_rows(),
        validation_rows=_validation_rows(),
        registry_tool_names=("alphaTool", "betaTool", "gammaTool", "unusedTool"),
        k_grid=(4,),
    ).report

    assert report["k_metrics"]["4"]["maximum_decision_space_reduction_bits"] == 0.0
    assert math.isfinite(report["k_metrics"]["4"]["precision"])


def test_zero_score_alphabetical_tail_is_not_counted_as_retrieval_support() -> None:
    validation = (
        _row(
            tier="tier4_implicit",
            query_idx=99,
            text="words absent from every construction key",
            tool="unusedTool",
        ),
    )
    report = analyze_label_candidate_reduction(
        construction_rows=_build_rows(),
        validation_rows=validation,
        registry_tool_names=("alphaTool", "betaTool", "gammaTool", "unusedTool"),
        k_grid=(1, 4),
    ).report

    assert report["k_metrics"]["4"]["full_set_coverage"] == 1.0
    assert report["k_metrics"]["4"]["positive_score_required_item_recall"] == 0.0
    assert report["k_metrics"]["4"]["positive_score_full_set_coverage"] == 0.0
    assert report["k_metrics"]["4"]["mean_zero_score_fallback_count"] == 4.0
    sample = report["samples"][0]
    assert sample["positive_score_tool_count"] == 0
    assert sample["required_tools_with_positive_score"] == []


def test_reports_cross_fold_text_twins_without_emitting_text() -> None:
    build = (
        _row(
            tier="tier1_direct",
            query_idx=1,
            text="Switch on the alpha lamp",
            tool="alphaTool",
        ),
        _row(
            tier="tier1_direct",
            query_idx=2,
            text="Switch on the beta fan",
            tool="betaTool",
        ),
    )
    validation = (
        _row(
            tier="tier1_direct",
            query_idx=11,
            text="  switch   on the ALPHA lamp ",
            tool="alphaTool",
        ),
        _row(
            tier="tier1_direct",
            query_idx=12,
            text="Switch, on the beta fan!",
            tool="alphaTool",
        ),
        _row(
            tier="tier1_direct",
            query_idx=13,
            text="A distinct request",
            tool="betaTool",
        ),
    )

    result = analyze_label_candidate_reduction(
        construction_rows=build,
        validation_rows=validation,
        registry_tool_names=("alphaTool", "betaTool"),
        k_grid=(1, 2),
    )
    audit = result.report["cross_fold_duplicate_audit"]

    assert audit["normalization"] == "casefolded whitespace-collapsed text"
    assert audit["normalized_text_twin_validation_units"] == 1
    assert audit["token_sequence_twin_validation_units"] == 2
    assert audit["normalized_text_twin_same_required_label_set_units"] == 1
    assert audit["subgroups"]["normalized_text_twin"]["unit_count"] == 1
    assert audit["subgroups"]["no_normalized_text_twin"]["unit_count"] == 2
    assert "Switch on the alpha lamp" not in result.canonical_json


def test_public_registry_keys_recover_implicit_effect_language() -> None:
    build = (
        _row(
            tier="tier1_direct",
            query_idx=1,
            text="activate the lamp",
            tool="alphaTool",
        ),
        _row(
            tier="tier1_direct",
            query_idx=2,
            text="set the cooling control",
            tool="betaTool",
        ),
    )
    validation = (
        _row(
            tier="tier4_implicit",
            query_idx=10,
            text="reduce cabin heat",
            tool="betaTool",
        ),
    )

    baseline = analyze_label_candidate_reduction(
        construction_rows=build,
        validation_rows=validation,
        registry_tool_names=("alphaTool", "betaTool"),
        k_grid=(1,),
    ).report
    augmented = analyze_label_candidate_reduction(
        construction_rows=build,
        validation_rows=validation,
        registry_tool_names=("alphaTool", "betaTool"),
        k_grid=(1,),
        public_tool_key_text_by_name={
            "alphaTool": "Produces visible room light.",
            "betaTool": "Reduces cabin heat and lowers temperature.",
        },
    ).report

    assert baseline["k_metrics"]["1"]["full_set_coverage"] == 0.0
    assert augmented["k_metrics"]["1"]["full_set_coverage"] == 1.0
    assert augmented["retrieval_key_design"]["public_tool_key_count"] == 2
    assert augmented["samples"][0]["ranked_tool_names"][0] == "betaTool"
    assert "Reduces cabin heat" not in json.dumps(augmented)


def test_public_registry_keys_must_exactly_cover_registry() -> None:
    with pytest.raises(LabelCandidateReductionError, match="public tool keys"):
        analyze_label_candidate_reduction(
            construction_rows=_build_rows(),
            validation_rows=_validation_rows(),
            registry_tool_names=("alphaTool", "betaTool", "gammaTool"),
            k_grid=(1,),
            public_tool_key_text_by_name={"alphaTool": "Light control."},
        )
