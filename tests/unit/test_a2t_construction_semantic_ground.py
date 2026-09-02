"""Construction-semantic Audio2Tool ground without source-text leakage."""

from __future__ import annotations

import re

import pytest

from speech_aware_evidence_acquisition.rails import (
    a2t_construction_semantic_ground as ground,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _registry_row(
    name: str,
    *,
    description: str | None = None,
    signature: str | None = None,
    category: str = "lighting",
) -> dict[str, str]:
    return {
        "tool_id": "1",
        "domain": "smart_home",
        "category": category,
        "tool_name": name,
        "signature": signature or f"{name}(deviceId: str)",
        "description": description or f"Perform the declared {name} operation.",
        "argument_defaults": "deviceId='PRIVATE-DEFAULT'",
        "argument_constraints": "",
    }


def _row(
    index: int,
    *,
    tier: str,
    tool: str,
    pairs: tuple[tuple[str, str], ...],
    extra_calls: tuple[str, ...] = (),
    text: str = "PRIVATE FULL SOURCE UTTERANCE",
    sample_id: str | None = None,
) -> A2tKbRow:
    sequence = (tool, *extra_calls)
    rendered = " ".join(f"{name}()" for name in sequence)
    return A2tKbRow(
        unit_id=f"{tier}:{index:06d}",
        tier=tier,
        query_idx=index,
        text=text,
        domain="smart_home",
        category="lighting",
        tool_id=1,
        tool_name=tool,
        arg_signature=tuple(key for key, _value in pairs),
        arg_pairs=pairs,
        call_render=rendered,
        extra_call_names=extra_calls,
        call_count=len(sequence),
        sample_ids=(sample_id or f"{tier}:{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={},
        speaker_ids=("speaker",),
    )


def test_ground_conditions_patterns_on_tier_and_tool_without_cross_tier_required_keys() -> None:
    registry = (
        _registry_row("setLight"),
        _registry_row("notifyUser", category="communication"),
    )
    rows = (
        _row(
            1,
            tier="tier1_direct",
            tool="setLight",
            pairs=(("deviceId", "lamp"),),
        ),
        _row(
            2,
            tier="tier1_direct",
            tool="setLight",
            pairs=(("deviceId", "lamp"), ("level", "3")),
        ),
        _row(
            3,
            tier="tier2_parametric",
            tool="setLight",
            pairs=(("level", "3"),),
            extra_calls=("notifyUser",),
        ),
    )

    artifact = ground.build_construction_semantic_ground(registry, rows)

    assert "U000=notifyUser" in artifact.text
    assert "U001=setLight" in artifact.text
    assert "K00=deviceId" in artifact.text
    assert "K01=level" in artifact.text
    assert "P T1 U001 K=K00/K00,K01 V=K01:i C=1 S=-" in artifact.text
    assert "P T2 U001 K=K01 V=K01:i C=2 S=U000" in artifact.text
    assert "Universal required arguments" not in artifact.text
    assert artifact.report["tier_tool_pair_count"] == 2
    assert artifact.report["argument_key_pattern_count"] == 3
    assert artifact.report["tool_sequence_pattern_count"] == 2


def test_ground_renders_cautious_serialized_value_forms_but_no_values_or_sources() -> None:
    private_source = "TURN ON SECRET-ALPHA IN THE PRIVATE BEDROOM"
    private_sample = "tier2_parametric:987654"
    rows = (
        _row(
            1,
            tier="tier2_parametric",
            tool="setLight",
            pairs=(
                ("plain", "SECRET-ALPHA"),
                ("integer", "3"),
                ("decimal", "3.5"),
                ("boolean", "true"),
                ("missing", "null"),
                ("array", '["x",2]'),
                ("object", '{"a":1}'),
                ("quoted", '"x"'),
                ("noncanonical", "03"),
            ),
            text=private_source,
            sample_id=private_sample,
        ),
    )

    artifact = ground.build_construction_semantic_ground(
        (_registry_row("setLight"),), rows
    )

    assert "K00=array" in artifact.text
    assert "K01=boolean" in artifact.text
    assert "K02=decimal" in artifact.text
    assert "K03=integer" in artifact.text
    assert "K04=missing" in artifact.text
    assert "K05=noncanonical" in artifact.text
    assert "K06=object" in artifact.text
    assert "K07=plain" in artifact.text
    assert "K08=quoted" in artifact.text
    assert "V=K00:a;K01:b;K02:n;K03:i;K04:0;K06:o;K08:s" in artifact.text
    assert "K05:" not in artifact.text
    assert "K07:" not in artifact.text
    assert "Serialized forms are observations, not required source JSON types." in artifact.text
    assert private_source not in artifact.text
    assert private_sample not in artifact.text
    assert "SECRET-ALPHA" not in artifact.text
    assert "PRIVATE-DEFAULT" not in artifact.text
    assert artifact.report["invocation_texts_rendered"] == 0
    assert artifact.report["sample_ids_rendered"] == 0
    assert artifact.report["argument_values_rendered"] == 0
    assert artifact.report["lexical_cues_rendered"] > 0
    assert artifact.report["source_sample_count"] == 1


def test_ground_contains_global_tier_rules_registry_meanings_and_exact_json_contract() -> None:
    artifact = ground.build_construction_semantic_ground(
        (
            _registry_row("setLight", description="Set the requested light state."),
            _registry_row("unusedTool", description="Read the unused device state."),
        ),
        (
            _row(
                1,
                tier="tier6_correction",
                tool="setLight",
                pairs=(("deviceId", "lamp"),),
            ),
        ),
    )

    for tier in (
        "tier1_direct",
        "tier2_parametric",
        "tier3_multi_intent",
        "tier4_implicit",
        "tier5_needle",
        "tier6_correction",
        "tier7_multiturn",
        "tier8_intent_blending",
    ):
        assert f"{tier}:" in artifact.text
    assert "use the final corrected intent and values" in artifact.text
    assert "U000=setLight | Meaning: Set the requested light state." in artifact.text
    assert "U001=unusedTool | Meaning: Read the unused device state." in artifact.text
    assert 'each element is exactly {"name":"toolName","arguments":{...}}' in artifact.text
    assert "Return only one JSON array" in artifact.text
    assert artifact.text.isascii()
    assert re.fullmatch(r"[0-9a-f]{64}", artifact.sha256)
    assert artifact.report["registry_tool_count"] == 2
    assert artifact.report["construction_primary_tool_count"] == 1
    assert artifact.report["registry_only_tool_count"] == 1


def test_ground_is_deterministic_under_input_permutation() -> None:
    registry = (_registry_row("zTool"), _registry_row("aTool"))
    rows = (
        _row(2, tier="tier2_parametric", tool="zTool", pairs=(("z", "1"),)),
        _row(1, tier="tier1_direct", tool="aTool", pairs=(("a", "value"),)),
    )

    first = ground.build_construction_semantic_ground(registry, rows)
    second = ground.build_construction_semantic_ground(
        tuple(reversed(registry)), tuple(reversed(rows))
    )

    assert first == second
    assert first.report["source_row_count"] == 2
    assert first.report["source_unit_count"] == 2
    assert first.report["source_rows_by_tier"] == {
        "tier1_direct": 1,
        "tier2_parametric": 1,
    }
    assert first.report["utf8_bytes"] <= first.report["max_utf8_bytes"]


def test_ground_cues_are_distinctive_and_remove_values_numbers_and_full_sources() -> None:
    rows = (
        _row(
            1,
            tier="tier4_implicit",
            tool="setLight",
            pairs=(("room", "kitchen"), ("level", "42")),
            text="Please brighten kitchen lamp to 42 percent",
        ),
        _row(
            2,
            tier="tier4_implicit",
            tool="setLight",
            pairs=(("room", "Kitchen"),),
            text="Could you brighten the kitchen lamp",
        ),
        _row(
            3,
            tier="tier4_implicit",
            tool="unusedTool",
            pairs=(),
            text="activate",
        ),
    )

    artifact = ground.build_construction_semantic_ground(
        (_registry_row("setLight"), _registry_row("unusedTool")),
        rows,
        max_cues_per_pair=3,
    )

    set_light_row = next(
        line for line in artifact.text.splitlines() if line.startswith("P T4 U000")
    )
    unused_row = next(
        line for line in artifact.text.splitlines() if line.startswith("P T4 U001")
    )
    assert "Q=" in set_light_row
    assert "brighten" in set_light_row
    assert "kitchen" not in set_light_row
    assert "42" not in set_light_row
    assert "Q=" not in unused_row
    assert "activate" not in artifact.text
    assert artifact.report["lexical_cues_rendered"] <= 3


@pytest.mark.parametrize("bad_cap", [0, -1, True, 1.5])
def test_ground_refuses_invalid_byte_caps(bad_cap: object) -> None:
    with pytest.raises(ground.ConstructionSemanticGroundError, match="positive integer"):
        ground.build_construction_semantic_ground(
            (_registry_row("setLight"),), (), max_utf8_bytes=bad_cap  # type: ignore[arg-type]
        )


def test_ground_fails_closed_on_malformed_inputs_and_oversize_output() -> None:
    registry = (_registry_row("setLight"),)
    valid = _row(
        1,
        tier="tier1_direct",
        tool="setLight",
        pairs=(("deviceId", "lamp"),),
    )
    unknown_tool = _row(
        2, tier="tier1_direct", tool="missing", pairs=(("deviceId", "lamp"),)
    )
    bad_signature = A2tKbRow(
        **{
            **valid.__dict__,
            "arg_signature": ("differentKey",),
        }
    )
    bad_count = A2tKbRow(**{**valid.__dict__, "call_count": 2})

    with pytest.raises(ground.ConstructionSemanticGroundError, match="duplicate"):
        ground.build_construction_semantic_ground((registry[0], registry[0]), ())
    with pytest.raises(ground.ConstructionSemanticGroundError, match="outside the registry"):
        ground.build_construction_semantic_ground(registry, (unknown_tool,))
    with pytest.raises(ground.ConstructionSemanticGroundError, match="argument keys"):
        ground.build_construction_semantic_ground(registry, (bad_signature,))
    with pytest.raises(ground.ConstructionSemanticGroundError, match="call count"):
        ground.build_construction_semantic_ground(registry, (bad_count,))
    with pytest.raises(ground.ConstructionSemanticGroundError, match="ASCII"):
        ground.build_construction_semantic_ground(
            (_registry_row("setLight", description="non-English: caf\u00e9"),), ()
        )
    with pytest.raises(ground.ConstructionSemanticGroundError, match="byte budget"):
        ground.build_construction_semantic_ground(registry, (valid,), max_utf8_bytes=100)
