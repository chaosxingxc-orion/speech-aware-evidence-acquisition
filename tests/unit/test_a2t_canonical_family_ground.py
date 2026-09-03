"""Model-free tests for the canonical family-local action ground."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails import (
    a2t_canonical_family_ground as ground_module,
)
from speech_aware_evidence_acquisition.rails.a2t_canonical_family_ground import (
    FAMILY_GROUND_ASCII_BYTE_CAP,
    CanonicalFamilyGround,
    CanonicalFamilyGroundError,
)
from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    CompatibilityRule,
)


REPO = Path(__file__).resolve().parents[2]
CORPUS = (
    REPO
    / "knowledge"
    / "audio2tool"
    / "g5-exhaustive-family-contracts-v1"
    / "corpus.json"
)


def _compatibility_rules() -> tuple[CompatibilityRule, ...]:
    document = json.loads(CORPUS.read_text(encoding="ascii"))
    rules = [
        CompatibilityRule(
            tool_name="setAdaptiveLighting",
            legal_argument_key_set=("enabled",),
            value_forms=(("enabled", "boolean-string"),),
            construction_support_count=21,
        )
    ]
    seen = {("setAdaptiveLighting", ("enabled",))}
    for row in document["contracts"]:
        for skeleton in row["legal_key_skeletons"]:
            identity = (row["tool_name"], tuple(skeleton))
            if not skeleton or identity in seen:
                continue
            seen.add(identity)
            rules.append(
                CompatibilityRule(
                    tool_name=row["tool_name"],
                    legal_argument_key_set=tuple(skeleton),
                    value_forms=(),
                    construction_support_count=2,
                )
            )
            if len(rules) == 43:
                return tuple(rules)
    raise AssertionError("fixture could not form 43 compatibility rules")


def _ground() -> CanonicalFamilyGround:
    return CanonicalFamilyGround.from_path(
        CORPUS, compatibility_rules=_compatibility_rules()
    )


def _branches(
    response_format: dict[str, object],
) -> dict[tuple[str, tuple[str, ...]], object]:
    schema = response_format["json_schema"]["schema"]  # type: ignore[index]
    return {
        (
            branch["properties"]["name"]["const"],  # type: ignore[index]
            tuple(branch["properties"]["arguments"]["required"]),  # type: ignore[index]
        ): branch
        for branch in schema["items"]["oneOf"]  # type: ignore[index]
    }


def test_loads_the_frozen_corpus_without_rewriting_it() -> None:
    before = CORPUS.read_bytes()

    ground = _ground()

    assert ground.corpus_sha256 == hashlib.sha256(before).hexdigest()
    assert len(ground.family_tags) == 28
    assert len(ground.tool_names) == 152
    assert set(ground.contracts_by_tool) == set(ground.tool_names)
    assert ground.contracts_by_tool["adjustVolume"].tool_name == "adjustVolume"
    assert ground.canonicalizers
    assert all(name.isascii() and text.isascii() for name, text in ground.canonicalizers.items())
    assert CORPUS.read_bytes() == before


def test_family_card_is_complete_value_free_ascii_and_compact() -> None:
    ground = _ground()

    card = ground.render_family("smart-car-media-cabin")

    assert card == ground.render_family("smart-car-media-cabin")
    assert card.isascii()
    assert "CANONICAL FAMILY ACTION GROUND" in card
    assert "Exact tool: adjustVolume" in card
    assert (
        "Choose when: Increases or decreases the volume by a specified number of steps."
        in card
    )
    assert "Sibling contrast:" in card
    assert "Legal key sets: {direction, steps}" in card
    assert "Key types: direction: UpDown; steps: Int" in card
    assert "Constraints: direction: [Up, Down], steps: [1-10]" in card
    assert "A public default may complete an explicitly requested operation" in card
    assert "Omission rules:" in card
    assert "Canonicalization rules:" in card
    assert "Compatibility forms:" in card
    assert "Positive construction language" not in card
    assert "Synthetic" not in card
    assert "Example" not in card
    assert len(card.encode("ascii")) <= FAMILY_GROUND_ASCII_BYTE_CAP


def test_family_local_schema_allows_abstention_and_exact_legal_calls() -> None:
    ground = _ground()

    response_format = ground.response_format("smart-car-media-cabin")

    document = response_format["json_schema"]["schema"]  # type: ignore[index]
    assert response_format["type"] == "json_schema"
    assert document["type"] == "array"
    assert document["minItems"] == 0
    assert document["maxItems"] == 4
    branches = _branches(response_format)
    assert ("adjustVolume", ("direction", "steps")) in branches
    assert ("activateRoutine", ()) not in branches
    arguments = branches[("adjustVolume", ("direction", "steps"))]["properties"][  # type: ignore[index]
        "arguments"
    ]["properties"]
    assert arguments["direction"] == {"type": "string", "enum": ["Up", "Down"]}
    assert arguments["steps"] == {"type": "integer", "minimum": 1, "maximum": 10}

    lighting = _branches(ground.response_format("smart-home-lighting"))
    assert lighting[("setAdaptiveLighting", ("enabled",))]["properties"][  # type: ignore[index]
        "arguments"
    ]["properties"]["enabled"] == {
        "type": "string",
        "enum": ["True", "False"],
    }


def test_family_schema_and_card_are_order_deterministic() -> None:
    first = _ground()
    second = _ground()

    for family_tag in first.family_tags:
        assert first.render_family(family_tag) == second.render_family(family_tag)
        assert first.response_format(family_tag) == second.response_format(family_tag)


@pytest.mark.parametrize("family_tag", ("", "not-a-family"))
def test_unknown_family_fails_closed(family_tag: str) -> None:
    ground = _ground()

    with pytest.raises(CanonicalFamilyGroundError, match="unknown family"):
        ground.render_family(family_tag)
    with pytest.raises(CanonicalFamilyGroundError, match="unknown family"):
        ground.response_format(family_tag)


def test_every_family_is_compact_and_every_tool_has_a_schema_branch() -> None:
    ground = _ground()
    schema_tools: set[str] = set()

    for family_tag in ground.family_tags:
        rendered = ground.render_family(family_tag)
        assert len(rendered.encode("ascii")) <= FAMILY_GROUND_ASCII_BYTE_CAP
        schema_tools.update(
            name for name, _keys in _branches(ground.response_format(family_tag))
        )

    assert schema_tools == set(ground.tool_names)


def test_every_exact_family_request_fits_the_operational_context_bound() -> None:
    ground = _ground()

    for family_tag in ground.family_tags:
        request = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Use the canonical family action ground. Return only the JSON "
                        "array allowed by the response schema."
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": ground.render_family(family_tag)},
                        {
                            "type": "input_speech_features",
                            "speech_features": {
                                "packet_id": "preflight/query",
                                "sha256": "0" * 64,
                                "role": "query",
                            },
                        },
                    ],
                },
            ],
            "response_format": ground.response_format(family_tag),
            "agent_control": {
                "contact_id": f"canonical-family-{family_tag}",
                "instruction": (
                    "Follow the system instruction for this registered contact."
                ),
            },
        }
        serialized_bytes = len(
            json.dumps(
                request,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
        )
        # Bounded OBS state, speech features, special tokens, and completion.
        conservative_total = serialized_bytes + 1_024 + 169 + 512 + 1_024

        assert conservative_total <= 24_576, family_tag


def test_low_level_contract_fields_reject_malformed_or_non_english_data() -> None:
    with pytest.raises(CanonicalFamilyGroundError, match="must be text"):
        ground_module._text(None, field="field")
    with pytest.raises(CanonicalFamilyGroundError, match="ASCII English"):
        ground_module._text("caf\u00e9", field="field")
    with pytest.raises(CanonicalFamilyGroundError, match="must be a list"):
        ground_module._text_tuple("not-a-list", field="field")
    with pytest.raises(CanonicalFamilyGroundError, match="duplicates"):
        ground_module._text_tuple(["same", "same"], field="field")
    with pytest.raises(CanonicalFamilyGroundError, match="types must be a list"):
        ground_module._types("not-a-list")
    with pytest.raises(CanonicalFamilyGroundError, match="type entry"):
        ground_module._types([["only-one-item"]])
    with pytest.raises(
        CanonicalFamilyGroundError, match="argument keys are duplicated"
    ):
        ground_module._types([["key", "String"], ["key", "String"]])


def test_low_level_skeleton_and_contract_rows_fail_closed() -> None:
    with pytest.raises(CanonicalFamilyGroundError, match="non-empty list"):
        ground_module._skeletons([], known_keys=frozenset())
    with pytest.raises(CanonicalFamilyGroundError, match="is malformed"):
        ground_module._skeletons(["not-a-list"], known_keys=frozenset())
    with pytest.raises(CanonicalFamilyGroundError, match="outside declared types"):
        ground_module._skeletons([["unknown"]], known_keys=frozenset({"known"}))
    with pytest.raises(CanonicalFamilyGroundError, match="are duplicated"):
        ground_module._skeletons(
            [["known"], ["known"]], known_keys=frozenset({"known"})
        )
    with pytest.raises(CanonicalFamilyGroundError, match="contract row"):
        ground_module._load_contract("not-a-mapping")


def test_ground_refuses_missing_or_out_of_contract_compatibility_rules() -> None:
    with pytest.raises(CanonicalFamilyGroundError, match="exactly 43"):
        CanonicalFamilyGround.from_path(CORPUS, compatibility_rules=())

    rules = list(_compatibility_rules())
    rules[0] = CompatibilityRule(
        tool_name="notRegistered",
        legal_argument_key_set=("enabled",),
        value_forms=(("enabled", "boolean-string"),),
        construction_support_count=2,
    )
    with pytest.raises(CanonicalFamilyGroundError, match="outside"):
        CanonicalFamilyGround.from_path(CORPUS, compatibility_rules=rules)
