"""Model-free tests for construction-example Audio2Tool family ground."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import (
    a2t_construction_example_ground as ground,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


REPO = Path(__file__).resolve().parents[2]
G5_CORPUS = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g5-exhaustive-family-contracts-v1"
    / "corpus.json"
)


def _row(
    index: int,
    *,
    text: str,
    pairs: tuple[tuple[str, str], ...],
    tier: str = "tier1_direct",
    source_id: str | None = None,
    call_render: str = "PRIVATE GOLD CALL",
) -> A2tKbRow:
    sample_id = source_id or f"construction-source-{index}"
    return A2tKbRow(
        unit_id=f"construction-unit-{index}",
        tier=tier,
        query_idx=index,
        text=text,
        domain="smart_car",
        category="media_cabin",
        tool_id=1,
        tool_name="adjustVolume",
        arg_signature=tuple(key for key, _value in pairs),
        arg_pairs=pairs,
        call_render=call_render,
        extra_call_names=(),
        call_count=1,
        sample_ids=(sample_id,),
        item_ids=(index,),
        media_relpath_by_sample_id={sample_id: "PRIVATE.wav"},
        speaker_ids=("PRIVATE-SPEAKER",),
    )


def _build(
    rows: tuple[A2tKbRow, ...],
    **kwargs: object,
) -> ground.ConstructionExampleGround:
    return ground.build_construction_example_family_ground(
        rows,
        G5_CORPUS,
        forbidden_query_blocks=frozenset({9001, 9002}),
        forbidden_source_ids=frozenset({"evaluation-source-1"}),
        **kwargs,  # type: ignore[arg-type]
    )


def test_builds_family_scan_bundles_with_exact_contracts_and_delexicalized_examples() -> (
    None
):
    secret_source = "construction-source-11"
    artifact = _build(
        (
            _row(
                11,
                text="Please move cabin volume Up by 3 steps",
                pairs=(("direction", "Up"), ("steps", "3")),
                source_id=secret_source,
            ),
        )
    )

    bundle = artifact.bundles_by_family["smart-car-media-cabin"]
    tool = bundle.tools_by_name["adjustVolume"]
    assert len(artifact.bundles) == 28
    assert len(artifact.tool_names) == 152
    assert bundle.family_tag == "smart-car-media-cabin"
    assert bundle.text.isascii()
    assert bundle.ascii_bytes == len(bundle.text.encode("ascii"))
    assert bundle.sha256 == hashlib.sha256(bundle.text.encode("ascii")).hexdigest()
    assert bundle.tool_names == tuple(sorted(bundle.tool_names))
    assert tool.operation == (
        "Increases or decreases the volume by a specified number of steps."
    )
    assert tool.types == (("direction", "UpDown"), ("steps", "Int"))
    assert tool.legal_key_skeletons == (("direction", "steps"),)
    assert tool.patterns == (
        ground.ConstructionLanguagePattern(
            tier="tier1_direct",
            text="Please move cabin volume {direction} by {steps} steps",
            placeholders=("direction", "steps"),
        ),
    )
    assert "Tool: adjustVolume" in bundle.text
    assert (
        "Choose when: Increases or decreases the volume by a specified number of steps."
        in bundle.text
    )
    assert "Sibling operation contrast:" in bundle.text
    assert "controlPlayback:" in bundle.text
    assert "Key types: direction: UpDown; steps: Int" in bundle.text
    assert "Legal key skeletons: {direction, steps}" in bundle.text
    assert "Please move cabin volume {direction} by {steps} steps" in bundle.text
    assert "PRIVATE GOLD CALL" not in artifact.text
    assert "PRIVATE.wav" not in artifact.text
    assert "PRIVATE-SPEAKER" not in artifact.text
    assert secret_source not in artifact.text
    assert " by 3 steps" not in artifact.text
    assert re.fullmatch(r"[0-9a-f]{64}", artifact.sha256)


def test_tier7_uses_only_existing_final_user_request_text_and_never_other_row_fields() -> (
    None
):
    artifact = _build(
        (
            _row(
                12,
                tier="tier7_multiturn",
                text="Lower cabin volume Down by 2 steps",
                pairs=(("direction", "Down"), ("steps", "2")),
                call_render="FULL TIER7 CHAT HISTORY MUST STAY SEALED",
            ),
        )
    )

    text = artifact.bundles_by_family["smart-car-media-cabin"].text
    assert "Lower cabin volume {direction} by {steps} steps" in text
    assert "tier7_multiturn" in text
    assert "FULL TIER7 CHAT HISTORY MUST STAY SEALED" not in artifact.text
    assert artifact.report["construction_fields_consumed"] == [
        "arg_pairs",
        "arg_signature",
        "query_idx",
        "sample_ids",
        "text",
        "tier",
        "tool_name",
        "unit_id",
    ]


def test_selection_is_reverse_order_stable_diverse_and_bounded_to_three() -> None:
    rows = (
        _row(
            21,
            text="Raise the cabin sound Up by 1 steps",
            pairs=(("direction", "Up"), ("steps", "1")),
        ),
        _row(
            22,
            text="Move audio volume Up by 2 steps",
            pairs=(("direction", "Up"), ("steps", "2")),
            tier="tier2_parametric",
        ),
        _row(
            23,
            text="Please increase cabin volume Up by 3 steps",
            pairs=(("direction", "Up"), ("steps", "3")),
            tier="tier4_implicit",
        ),
        _row(
            24,
            text="Turn cabin volume Down by 4 steps",
            pairs=(("direction", "Down"), ("steps", "4")),
            tier="tier6_correction",
        ),
    )

    forward = _build(rows)
    reverse = _build(tuple(reversed(rows)))

    assert forward == reverse
    patterns = (
        forward.bundles_by_family["smart-car-media-cabin"]
        .tools_by_name["adjustVolume"]
        .patterns
    )
    assert len(patterns) == 3
    assert len({pattern.text for pattern in patterns}) == 3
    assert {pattern.tier for pattern in patterns}.issubset(
        {"tier1_direct", "tier2_parametric", "tier4_implicit", "tier6_correction"}
    )
    assert all("{direction}" in pattern.text for pattern in patterns)
    assert all("{steps}" in pattern.text for pattern in patterns)
    assert forward.report["maximum_examples_per_tool"] == 3


def test_registry_only_tools_have_zero_examples_and_are_explicitly_reported() -> None:
    artifact = _build(
        (
            _row(
                30,
                text="Move cabin volume Up by 5 steps",
                pairs=(("direction", "Up"), ("steps", "5")),
            ),
        )
    )

    empty_tools = artifact.report["registry_only_tool_names"]
    assert len(empty_tools) == 151
    assert "getLockStatus" in empty_tools
    assert artifact.report["construction_used_tool_count"] == 1
    assert artifact.report["tools_with_examples"] == 1
    assert artifact.report["task_used_tool_pattern_coverage"] == 1.0
    assert artifact.report["registry_only_tool_pattern_policy"] == (
        "zero patterns; no construction-positive language is available"
    )
    lock_tool = next(
        bundle.tools_by_name["getLockStatus"]
        for bundle in artifact.bundles
        if "getLockStatus" in bundle.tools_by_name
    )
    assert lock_tool.patterns == ()


def test_boundary_rejects_forbidden_query_blocks_and_source_ids() -> None:
    query_overlap = _row(
        9001,
        text="Move cabin volume Up by 2 steps",
        pairs=(("direction", "Up"), ("steps", "2")),
    )
    source_overlap = _row(
        40,
        text="Move cabin volume Up by 2 steps",
        pairs=(("direction", "Up"), ("steps", "2")),
        source_id="evaluation-source-1",
    )

    with pytest.raises(
        ground.ConstructionExampleGroundError, match="query-block overlap"
    ):
        _build((query_overlap,))
    with pytest.raises(ground.ConstructionExampleGroundError, match="source overlap"):
        _build((source_overlap,))


def test_unaligned_values_are_excluded_instead_of_leaked() -> None:
    artifact = _build(
        (
            _row(
                50,
                text="Please make the cabin louder",
                pairs=(("direction", "Up"), ("steps", "7")),
            ),
            _row(
                51,
                text="Move cabin volume Down by 8 steps",
                pairs=(("direction", "Down"), ("steps", "8")),
            ),
        )
    )

    tool = artifact.bundles_by_family["smart-car-media-cabin"].tools_by_name[
        "adjustVolume"
    ]
    assert len(tool.patterns) == 1
    assert "louder" not in artifact.text
    assert "Down" not in tool.patterns[0].text
    assert "8" not in tool.patterns[0].text
    assert artifact.report["unaligned_row_count"] == 1
    assert artifact.report["source_argument_values_rendered"] == 0


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_examples_per_tool": 0}, "between 1 and 3"),
        ({"max_examples_per_tool": 4}, "between 1 and 3"),
        ({"max_family_ascii_bytes": 10}, "family byte cap"),
        ({"max_total_ascii_bytes": 10}, "corpus byte cap"),
    ],
)
def test_caps_fail_closed(kwargs: dict[str, int], message: str) -> None:
    row = _row(
        60,
        text="Move cabin volume Up by 9 steps",
        pairs=(("direction", "Up"), ("steps", "9")),
    )

    with pytest.raises(ground.ConstructionExampleGroundError, match=message):
        _build((row,), **kwargs)


def test_receipt_carries_coverage_and_hashes_but_no_defaults_or_source_identities() -> (
    None
):
    row = _row(
        70,
        text="Move cabin volume Up by 10 steps",
        pairs=(("direction", "Up"), ("steps", "10")),
    )
    artifact = _build((row,))

    assert (
        artifact.receipt["schema"] == "saea-a2t-construction-example-ground-receipt-v1"
    )
    assert artifact.receipt["corpus_sha256"] == artifact.sha256
    assert (
        artifact.receipt["source_hashes"]["g5_corpus_sha256"]
        == hashlib.sha256(G5_CORPUS.read_bytes()).hexdigest()
    )
    assert re.fullmatch(
        r"[0-9a-f]{64}",
        artifact.receipt["source_hashes"]["construction_rows_sha256"],
    )
    assert artifact.report["family_count"] == 28
    assert artifact.report["tool_count"] == 152
    assert artifact.report["legal_key_skeleton_count"] > 0
    assert artifact.report["typed_key_count"] > 0
    assert artifact.report["source_sample_ids_rendered"] == 0
    assert "Good_Morning" not in artifact.text
    assert "argument default" not in artifact.text.casefold()
    assert "construction-unit-70" not in str(artifact.receipt)
    assert "construction-source-70" not in str(artifact.receipt)
