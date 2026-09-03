from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.analysis.a2t_observation_text_ablation import (
    ObservationTextAblationError,
    analyze_observation_text_ablation,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _row(
    unit_id: str,
    *,
    query_idx: int,
    tier: str,
    text: str,
    tool_name: str,
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=unit_id,
        tier=tier,
        query_idx=query_idx,
        text=text,
        domain="test-domain",
        category="test-category",
        tool_id=query_idx,
        tool_name=tool_name,
        arg_signature=(),
        arg_pairs=(),
        call_render=f"{tool_name}()",
        extra_call_names=(),
        call_count=1,
        sample_ids=(f"{tier}:{query_idx:06d}",),
        item_ids=(query_idx,),
        media_relpath_by_sample_id={
            f"{tier}:{query_idx:06d}": f"audio/{query_idx}.wav"
        },
        speaker_ids=("speaker",),
    )


def _world() -> tuple[tuple[A2tKbRow, ...], tuple[A2tKbRow, ...]]:
    build = (
        _row(
            "tier1_direct:000000",
            query_idx=0,
            tier="tier1_direct",
            text="activate the alpha lamp",
            tool_name="alphaTool",
        ),
        _row(
            "tier1_direct:000001",
            query_idx=1,
            tier="tier1_direct",
            text="activate the beta fan",
            tool_name="betaTool",
        ),
    )
    validation = (
        _row(
            "tier7_multiturn:000002",
            query_idx=2,
            tier="tier7_multiturn",
            text="do it now",
            tool_name="betaTool",
        ),
    )
    return build, validation


def test_complete_dialogue_recovers_information_missing_from_final_turn() -> None:
    build, validation = _world()

    result = analyze_observation_text_ablation(
        construction_rows=build,
        validation_rows=validation,
        registry_tool_names=("alphaTool", "betaTool"),
        complete_dialogue_text_by_unit_id={
            "tier7_multiturn:000002": (
                "Earlier we discussed the beta fan. Please do it now."
            )
        },
        k_grid=(1, 2),
    )

    report = result.report
    assert report["schema"] == "saea-a2t-observation-text-factorial-v2"
    assert report["input_boundary"] == {
        "construction_rows_only": True,
        "evaluation_or_test_rows_consumed": 0,
        "complete_dialogue_text_emitted": False,
        "gold_used_only_for_postranking_measurement": True,
        "model_contacts": 0,
        "network_contacts": 0,
        "runtime_eligible": False,
        "scorer_contacts": 0,
    }
    assert report["population"]["tier7_validation_units"] == 1
    assert (
        report["cells"]["final_key_final_query"]["overall"]["1"]["full_set_coverage"]
        == 0.0
    )
    assert (
        report["cells"]["final_key_complete_query"]["overall"]["1"]["full_set_coverage"]
        == 1.0
    )
    assert (
        report["contrasts"]["observation_only_minus_baseline"]["overall"]["1"][
            "full_set_coverage"
        ]
        == 1.0
    )
    assert report["decision"]["observation_information_gain_detected"] is True
    assert "beta fan" not in result.canonical_json
    assert json.loads(result.canonical_json) == report


def test_ablation_is_order_invariant_and_hashes_source_text_without_emitting_it() -> (
    None
):
    build, validation = _world()
    kwargs = {
        "registry_tool_names": ("betaTool", "alphaTool"),
        "complete_dialogue_text_by_unit_id": {
            "tier7_multiturn:000002": "The beta fan was selected. Do it now."
        },
        "k_grid": (2, 1),
    }

    forward = analyze_observation_text_ablation(
        construction_rows=build,
        validation_rows=validation,
        **kwargs,
    )
    reverse = analyze_observation_text_ablation(
        construction_rows=tuple(reversed(build)),
        validation_rows=tuple(reversed(validation)),
        **kwargs,
    )

    assert forward.canonical_json == reverse.canonical_json
    identity = forward.report["complete_dialogue_text_identity"]
    assert identity["unit_count"] == 1
    assert len(identity["sha256"]) == 64
    assert "The beta fan was selected" not in forward.canonical_json


def test_factorial_separates_joint_gain_from_observation_only_gain() -> None:
    build = (
        _row(
            "tier7_multiturn:000000",
            query_idx=0,
            tier="tier7_multiturn",
            text="do it now",
            tool_name="alphaTool",
        ),
        _row(
            "tier7_multiturn:000001",
            query_idx=1,
            tier="tier7_multiturn",
            text="do it now",
            tool_name="betaTool",
        ),
    )
    validation = (
        _row(
            "tier7_multiturn:000002",
            query_idx=2,
            tier="tier7_multiturn",
            text="do it now",
            tool_name="betaTool",
        ),
    )
    result = analyze_observation_text_ablation(
        construction_rows=build,
        validation_rows=validation,
        registry_tool_names=("alphaTool", "betaTool"),
        complete_dialogue_text_by_unit_id={
            "tier7_multiturn:000000": "We discussed the alpha lamp. Do it now.",
            "tier7_multiturn:000001": "We discussed the beta fan. Do it now.",
            "tier7_multiturn:000002": "The beta fan was selected. Do it now.",
        },
        k_grid=(1,),
    ).report

    assert (
        result["cells"]["final_key_final_query"]["overall"]["1"]["full_set_coverage"]
        == 0.0
    )
    assert (
        result["cells"]["complete_key_final_query"]["overall"]["1"]["full_set_coverage"]
        == 0.0
    )
    assert (
        result["cells"]["final_key_complete_query"]["overall"]["1"]["full_set_coverage"]
        == 0.0
    )
    assert (
        result["cells"]["complete_key_complete_query"]["overall"]["1"][
            "full_set_coverage"
        ]
        == 1.0
    )
    assert (
        result["contrasts"]["observation_only_minus_baseline"]["overall"]["1"][
            "full_set_coverage"
        ]
        == 0.0
    )
    assert (
        result["contrasts"]["joint_minus_baseline"]["overall"]["1"]["full_set_coverage"]
        == 1.0
    )
    assert (
        result["contrasts"]["factorial_interaction"]["overall"]["1"][
            "full_set_coverage"
        ]
        == 1.0
    )


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({}, "must exactly cover"),
        (
            {
                "tier7_multiturn:000002": "valid dialogue",
                "tier7_multiturn:999999": "extra dialogue",
            },
            "must exactly cover",
        ),
        ({"tier7_multiturn:000002": ""}, "non-empty English text"),
        ({"tier7_multiturn:000002": 7}, "non-empty English text"),
    ],
)
def test_ablation_rejects_malformed_complete_dialogue_mapping(
    overrides: dict[str, object], message: str
) -> None:
    build, validation = _world()

    with pytest.raises(ObservationTextAblationError, match=message):
        analyze_observation_text_ablation(
            construction_rows=build,
            validation_rows=validation,
            registry_tool_names=("alphaTool", "betaTool"),
            complete_dialogue_text_by_unit_id=overrides,  # type: ignore[arg-type]
            k_grid=(1,),
        )


def test_ablation_rejects_query_block_overlap() -> None:
    build, validation = _world()
    overlapping = (
        _row(
            "tier7_multiturn:000000",
            query_idx=0,
            tier="tier7_multiturn",
            text="do it",
            tool_name="betaTool",
        ),
    )

    with pytest.raises(ObservationTextAblationError, match="query-block-disjoint"):
        analyze_observation_text_ablation(
            construction_rows=build,
            validation_rows=overlapping,
            registry_tool_names=("alphaTool", "betaTool"),
            complete_dialogue_text_by_unit_id={
                "tier7_multiturn:000000": "The beta fan was selected. Do it."
            },
            k_grid=(1,),
        )


def test_ablation_rejects_non_ascii_dialogue_before_context_use() -> None:
    build, validation = _world()

    with pytest.raises(ObservationTextAblationError, match="English ASCII"):
        analyze_observation_text_ablation(
            construction_rows=build,
            validation_rows=validation,
            registry_tool_names=("alphaTool", "betaTool"),
            complete_dialogue_text_by_unit_id={
                "tier7_multiturn:000002": "Earlier context: \u6253\u5f00 the beta fan."
            },
            k_grid=(1,),
        )
