"""Deterministic executable semantic cards for the Audio2Tool G4 successor."""

from __future__ import annotations

import json
import re

import pytest

from speech_aware_evidence_acquisition.rails import (
    a2t_executable_semantic_cards as cards,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _registry() -> tuple[dict[str, str], ...]:
    rows = [
        {
            "tool_id": "1",
            "domain": "smart_home",
            "category": "lighting",
            "tool_name": "setLightState",
            "signature": "setLightState(deviceId: String, state: OnOff)",
            "description": "Set a light to the requested on or off state.",
            "argument_defaults": "state='Off'",
            "argument_constraints": "state: [On, Off]",
        },
        {
            "tool_id": "2",
            "domain": "smart_home",
            "category": "lighting",
            "tool_name": "getLightState",
            "signature": "getLightState(deviceId: String)",
            "description": "Read the current state of a light.",
            "argument_defaults": "",
            "argument_constraints": "",
        },
        {
            "tool_id": "3",
            "domain": "navigation",
            "category": "planning",
            "tool_name": "planSyntheticTrip",
            "signature": (
                "planSyntheticTrip(address: String, retries: Int, confidence: Float, "
                "enabled: Boolean, stops: List<String>?, metadata: Map?)"
            ),
            "description": "Create an artificial trip plan for the supplied destination.",
            "argument_defaults": "",
            "argument_constraints": (
                "retries: [1-10], confidence: [0.0-1.0], enabled: [True, False]"
            ),
        },
    ]
    for index in range(149):
        name = f"syntheticRegistryTool{index:03d}"
        rows.append(
            {
                "tool_id": str(index + 4),
                "domain": "synthetic_domain",
                "category": f"group_{index % 7}",
                "tool_name": name,
                "signature": f"{name}()",
                "description": f"Perform artificial registry operation {index:03d}.",
                "argument_defaults": "",
                "argument_constraints": "",
            }
        )
    assert len(rows) == cards.REQUIRED_TOOL_COUNT
    return tuple(rows)


def _summary(
    index: int,
    tool_name: str,
    keys: tuple[str, ...],
    *,
    text: str = "PRIVATE SOURCE UTTERANCE SENTINEL",
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=f"tier1_direct:{index:06d}",
        tier="tier1_direct",
        query_idx=index,
        text=text,
        domain="private-domain",
        category="private-category",
        tool_id=index,
        tool_name=tool_name,
        arg_signature=keys,
        arg_pairs=tuple((key, f"PRIVATE_{key.upper()}_VALUE") for key in keys),
        call_render=f"PRIVATE GOLD CALL FOR {tool_name}",
        extra_call_names=(),
        call_count=1,
        sample_ids=(f"tier1_direct:PRIVATE_SAMPLE_{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={
            f"tier1_direct:PRIVATE_SAMPLE_{index:06d}": "private/test.wav"
        },
        speaker_ids=("PRIVATE_SPEAKER",),
    )


def _summaries() -> tuple[A2tKbRow, ...]:
    return (
        _summary(1, "setLightState", ("deviceId", "state")),
        _summary(2, "setLightState", ("deviceId",)),
        _summary(3, "getLightState", ("deviceId",)),
        _summary(
            4,
            "planSyntheticTrip",
            ("address", "confidence", "enabled", "metadata", "retries", "stops"),
        ),
    )


def test_cards_cover_exact_registry_semantics_legal_keys_and_examples() -> None:
    corpus = cards.build_executable_semantic_card_corpus(
        _registry(),
        _summaries(),
    )

    assert corpus.report["registry_tool_count"] == 152
    assert corpus.report["tool_card_count"] == 152
    assert len(corpus.tool_cards) == 152
    assert set(corpus.cards_by_name) == {row["tool_name"] for row in _registry()}
    card = corpus.cards_by_name["setLightState"]
    assert card.choose_semantics == "Set a light to the requested on or off state."
    assert "getLightState" in card.avoid_semantics
    assert card.signature == "setLightState(deviceId: String, state: OnOff)"
    assert card.constraints == "state: [On, Off]"
    assert card.legal_argument_key_sets == (("deviceId",), ("deviceId", "state"))
    assert any("device identifier -> deviceId (String)" in row for row in card.role_guidance)
    assert any("state -> state (OnOff)" in row for row in card.role_guidance)
    assert len(card.examples) == 2
    for example_text in card.examples:
        example = json.loads(example_text)
        assert example["name"] == "setLightState"
        assert tuple(sorted(example["arguments"])) in card.legal_argument_key_sets
    assert json.loads(card.examples[0])["arguments"]["deviceId"].startswith(
        cards.SYNTHETIC_LITERAL_PREFIX
    )
    assert corpus.report["examples_validated"] is True
    assert corpus.report["example_count"] >= 152


def test_examples_are_type_correct_constraint_valid_and_visibly_artificial() -> None:
    corpus = cards.build_executable_semantic_card_corpus(_registry(), _summaries())
    card = corpus.cards_by_name["planSyntheticTrip"]
    example = json.loads(card.examples[0])
    arguments = example["arguments"]

    assert arguments["address"].startswith(cards.SYNTHETIC_LITERAL_PREFIX)
    assert isinstance(arguments["retries"], int) and 1 <= arguments["retries"] <= 10
    assert isinstance(arguments["confidence"], float)
    assert 0.0 <= arguments["confidence"] <= 1.0
    assert isinstance(arguments["enabled"], bool)
    assert isinstance(arguments["stops"], list)
    assert arguments["stops"][0].startswith(cards.SYNTHETIC_LITERAL_PREFIX)
    assert isinstance(arguments["metadata"], dict)
    assert cards.SYNTHETIC_LITERAL_PREFIX in card.text
    assert "Every example is artificial" in card.text


def test_list_enum_constraint_produces_a_type_correct_synthetic_array() -> None:
    registry = tuple(
        {
            **row,
            "argument_constraints": (
                row["argument_constraints"] + ", stops: [Alpha_Zone, Beta_Zone]"
            ),
        }
        if row["tool_name"] == "planSyntheticTrip"
        else row
        for row in _registry()
    )

    corpus = cards.build_executable_semantic_card_corpus(registry, _summaries())

    example = json.loads(corpus.cards_by_name["planSyntheticTrip"].examples[0])
    assert example["arguments"]["stops"] == ["Alpha_Zone"]


def test_corpus_has_four_task_cards_and_never_renders_private_row_fields() -> None:
    corpus = cards.build_executable_semantic_card_corpus(_registry(), _summaries())

    assert {card.card_id for card in corpus.task_cards} == {
        "correction-resolution",
        "implicit-end-state-resolution",
        "multi-call-ordering",
        "multiturn-carryover",
    }
    for phrase in (
        "preserve the spoken action order",
        "final correction supersedes",
        "desired end state",
        "earlier user turns",
    ):
        assert phrase in corpus.text
    for private in (
        "PRIVATE SOURCE UTTERANCE SENTINEL",
        "PRIVATE_DEVICEID_VALUE",
        "PRIVATE GOLD CALL",
        "PRIVATE_SAMPLE",
        "private/test.wav",
        "PRIVATE_SPEAKER",
    ):
        assert private not in corpus.text
    assert corpus.report["construction_fields_consumed"] == [
        "arg_signature",
        "tool_name",
    ]
    assert corpus.report["source_utterances_rendered"] == 0
    assert corpus.report["reference_transcripts_rendered"] == 0
    assert corpus.report["source_argument_values_rendered"] == 0
    assert corpus.report["gold_values_rendered"] == 0
    assert corpus.report["source_sample_ids_rendered"] == 0


def test_corpus_is_ascii_and_byte_identical_under_reversed_input() -> None:
    registry = _registry()
    summaries = _summaries()

    first = cards.build_executable_semantic_card_corpus(registry, summaries)
    second = cards.build_executable_semantic_card_corpus(
        tuple(reversed(registry)),
        tuple(reversed(summaries)),
    )

    assert first == second
    assert first.text.isascii()
    assert re.fullmatch(r"[0-9a-f]{64}", first.sha256)
    assert first.report["reversed_input_rebuild_contract"] == "byte-identical"


def test_builder_enforces_152_registered_names_and_legal_key_sets() -> None:
    registry = _registry()

    with pytest.raises(cards.ExecutableSemanticCardError, match="exactly 152"):
        cards.build_executable_semantic_card_corpus(registry[:-1], _summaries())
    with pytest.raises(cards.ExecutableSemanticCardError, match="duplicate registry tool"):
        cards.build_executable_semantic_card_corpus(
            (*registry[:-1], registry[0]), _summaries()
        )
    with pytest.raises(cards.ExecutableSemanticCardError, match="outside the registry"):
        cards.build_executable_semantic_card_corpus(
            registry, (*_summaries(), _summary(9, "unknownTool", ()))
        )
    with pytest.raises(cards.ExecutableSemanticCardError, match="outside its signature"):
        cards.build_executable_semantic_card_corpus(
            registry,
            (*_summaries(), _summary(9, "getLightState", ("goldOnlyKey",))),
        )


def test_example_literal_sentinel_rejects_a_forbidden_generated_literal() -> None:
    registry = tuple(
        {
            **row,
            "argument_constraints": "state: [PRIVATE_ENUM_SENTINEL]",
        }
        if row["tool_name"] == "setLightState"
        else row
        for row in _registry()
    )

    with pytest.raises(cards.ExecutableSemanticCardError, match="forbidden example literal"):
        cards.build_executable_semantic_card_corpus(
            registry,
            _summaries(),
            forbidden_example_literals={"PRIVATE_ENUM_SENTINEL"},
        )


def test_aggregate_compatibility_rules_extend_skeletons_without_values() -> None:
    compatibility = (
        cards.CompatibilityRule(
            tool_name="setLightState",
            legal_argument_key_set=("adaptive", "deviceId"),
            value_forms=(("adaptive", "boolean-string"),),
            construction_support_count=4,
        ),
        cards.CompatibilityRule(
            tool_name="planSyntheticTrip",
            legal_argument_key_set=("address", "valetPin"),
            value_forms=(("valetPin", "nullable-string"),),
            construction_support_count=3,
        ),
    )
    summaries = (
        *_summaries(),
        _summary(10, "setLightState", ("adaptive", "deviceId")),
        _summary(11, "planSyntheticTrip", ("address", "valetPin")),
    )

    corpus = cards.build_executable_semantic_card_corpus(
        _registry(), summaries, compatibility_rules=compatibility
    )

    light = corpus.cards_by_name["setLightState"]
    trip = corpus.cards_by_name["planSyntheticTrip"]
    assert ("adaptive", "deviceId") in light.legal_argument_key_sets
    assert ("address", "valetPin") in trip.legal_argument_key_sets
    assert light.compatibility_rules == (compatibility[0],)
    assert trip.compatibility_rules == (compatibility[1],)
    assert "Boolean lexical form encoded as a JSON string" in light.text
    assert "JSON null or an artificial JSON string" in trip.text
    assert "construction support count: 4" in light.text
    light_compatibility_example = next(
        json.loads(example)
        for example in light.examples
        if "adaptive" in json.loads(example)["arguments"]
    )
    trip_compatibility_example = next(
        json.loads(example)
        for example in trip.examples
        if "valetPin" in json.loads(example)["arguments"]
    )
    assert light_compatibility_example["arguments"]["adaptive"] == "True"
    assert trip_compatibility_example["arguments"]["valetPin"] is None
    assert "PRIVATE_ADAPTIVE_VALUE" not in corpus.text
    assert "PRIVATE_VALETPIN_VALUE" not in corpus.text
    assert corpus.report["compatibility_rule_count"] == 2
    assert corpus.report["compatibility_rule_value_literals_rendered"] == 0


@pytest.mark.parametrize(
    ("rule", "message"),
    (
        (
            cards.CompatibilityRule(
                tool_name="setLightState",
                legal_argument_key_set=("deviceId", "state"),
                value_forms=(),
                construction_support_count=1,
            ),
            "at least two",
        ),
        (
            cards.CompatibilityRule(
                tool_name="setLightState",
                legal_argument_key_set=("deviceId", "state"),
                value_forms=(("state", "verbatim-private-value"),),
                construction_support_count=4,
            ),
            "value form",
        ),
        (
            cards.CompatibilityRule(
                tool_name="unknownTool",
                legal_argument_key_set=("value",),
                value_forms=(("value", "string"),),
                construction_support_count=4,
            ),
            "outside the registry",
        ),
    ),
)
def test_compatibility_rules_are_aggregate_structured_and_fail_closed(
    rule: cards.CompatibilityRule, message: str
) -> None:
    with pytest.raises(cards.ExecutableSemanticCardError, match=message):
        cards.build_executable_semantic_card_corpus(
            _registry(), _summaries(), compatibility_rules=(rule,)
        )


def test_builder_rejects_non_ascii_registry_and_oversize_corpus() -> None:
    non_ascii = tuple(
        {**row, "description": "Non-English caf\u00e9 marker."}
        if row["tool_name"] == "setLightState"
        else row
        for row in _registry()
    )
    with pytest.raises(cards.ExecutableSemanticCardError, match="ASCII English"):
        cards.build_executable_semantic_card_corpus(non_ascii, _summaries())
    with pytest.raises(cards.ExecutableSemanticCardError, match="byte budget"):
        cards.build_executable_semantic_card_corpus(
            _registry(), _summaries(), max_utf8_bytes=100
        )
