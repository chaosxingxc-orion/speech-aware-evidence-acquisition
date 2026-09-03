"""Model-free tests for value-safe selected-tool decision cards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    CompatibilityRule,
)
from speech_aware_evidence_acquisition.rails.a2t_selected_tool_ground import (
    SELECTED_TOOL_MAX_COUNT,
    SelectedToolDecisionGround,
    SelectedToolGroundError,
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


def _ground(*, byte_cap: int | None = None) -> SelectedToolDecisionGround:
    kwargs = {} if byte_cap is None else {"byte_cap": byte_cap}
    return SelectedToolDecisionGround.from_path(
        CORPUS,
        compatibility_rules=_compatibility_rules(),
        **kwargs,
    )


def _branches(packet: object) -> set[tuple[str, tuple[str, ...]]]:
    response_format = packet.response_format  # type: ignore[attr-defined]
    schema = response_format["json_schema"]["schema"]
    return {
        (
            branch["properties"]["name"]["const"],
            tuple(branch["properties"]["arguments"]["required"]),
        )
        for branch in schema["items"]["oneOf"]
    }


def test_renders_only_ordered_selected_tools_with_selected_sibling_contrasts() -> None:
    packet = _ground().build(("adjustVolume", "setAudioVolume"))

    assert packet.selected_tool_names == (
        "adjustVolume",
        "setAudioVolume",
    )
    assert packet.text.isascii()
    assert "SELECTED-TOOL DECISION CARDS" in packet.text
    assert "Exact tool: adjustVolume" in packet.text
    assert "Exact tool: setAudioVolume" in packet.text
    assert "Exact tool: activateRoutine" not in packet.text
    assert "Selected-sibling contrast meanings:" in packet.text
    assert (
        "- adjustVolume: Increases or decreases the volume by a specified number "
        "of steps."
    ) in packet.text
    assert (
        "- setAudioVolume: Sets the volume level for a specific audio stream "
        "(Media, Navigation, or Voice)."
    ) in packet.text
    assert "Legal key sets: {direction, steps}" in packet.text
    assert "Key types: direction: UpDown; steps: Int" in packet.text
    assert "Required keys:" in packet.text
    assert "Optional keys:" in packet.text
    assert "Conditional keys:" in packet.text
    assert "Forbidden keys:" in packet.text
    assert "Declared defaults for omission semantics:" in packet.text
    assert "Omission rules:" in packet.text
    assert "Canonicalization rules:" in packet.text
    for prohibited in (
        "Construction example",
        "Sample ID",
        "Source utterance",
        "Reference label",
        "Gold label",
        "SYNTHETIC_",
    ):
        assert prohibited not in packet.text


def test_selected_schema_allows_abstention_and_only_selected_legal_branches() -> None:
    packet = _ground().build(("adjustVolume", "setAdaptiveLighting"))

    schema = packet.response_format["json_schema"]["schema"]
    assert schema["type"] == "array"
    assert schema["minItems"] == 0
    assert schema["maxItems"] == 7
    branches = _branches(packet)
    assert {name for name, _keys in branches} == {
        "adjustVolume",
        "setAdaptiveLighting",
    }
    assert ("adjustVolume", ("direction", "steps")) in branches
    adaptive = next(
        branch
        for branch in schema["items"]["oneOf"]
        if branch["properties"]["name"]["const"] == "setAdaptiveLighting"
        and branch["properties"]["arguments"]["required"] == ["enabled"]
    )
    assert adaptive["properties"]["arguments"]["properties"]["enabled"] == {
        "type": "string",
        "enum": ["True", "False"],
    }
    assert "Return [] only when no registered action is requested." in packet.text
    assert "preserve their spoken order" in packet.text


def test_packet_is_deterministic_hash_bound_counted_and_source_preserving() -> None:
    before = CORPUS.read_bytes()
    ground = _ground()

    first = ground.build(("adjustVolume", "setAudioVolume"))
    second = ground.build(("adjustVolume", "setAudioVolume"))

    assert first == second
    assert ground.corpus_sha256 == hashlib.sha256(before).hexdigest()
    assert first.text_sha256 == hashlib.sha256(first.text.encode("ascii")).hexdigest()
    assert (
        first.response_format_sha256
        == hashlib.sha256(
            json.dumps(
                first.response_format,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("ascii")
        ).hexdigest()
    )
    assert first.report == {
        "corpus_sha256": ground.corpus_sha256,
        "compatibility_sha256": ground.compatibility_sha256,
        "registered_family_count": 28,
        "registered_tool_count": 152,
        "qualified_compatibility_rule_count": 43,
        "selected_tool_count": 2,
        "selected_family_count": 1,
        "selected_legal_skeleton_count": 2,
        "selected_compatibility_rule_count": 1,
        "rendered_ascii_bytes": len(first.text.encode("ascii")),
        "rendered_byte_cap": ground.byte_cap,
        "construction_examples_rendered": 0,
        "sample_ids_rendered": 0,
        "source_utterances_rendered": 0,
        "reference_or_gold_labels_rendered": 0,
        "construction_concrete_values_rendered": 0,
    }
    assert CORPUS.read_bytes() == before


@pytest.mark.parametrize(
    ("selection", "message"),
    (
        ((), "between 1 and 16"),
        (("adjustVolume", "adjustVolume"), "duplicate"),
        (("notRegistered",), "unknown"),
        (("adjustVolume", 3), "ASCII registered tool names"),
        (("adjustVolume",) * (SELECTED_TOOL_MAX_COUNT + 1), "between 1 and 16"),
    ),
)
def test_selection_fails_closed(selection: tuple[object, ...], message: str) -> None:
    with pytest.raises(SelectedToolGroundError, match=message):
        _ground().build(selection)  # type: ignore[arg-type]


def test_enforces_rendered_byte_cap() -> None:
    ground = _ground(byte_cap=128)

    with pytest.raises(SelectedToolGroundError, match="byte cap"):
        ground.build(("adjustVolume",))


def test_requires_a_positive_integer_byte_cap() -> None:
    for cap in (0, -1, True):
        with pytest.raises(SelectedToolGroundError, match="byte cap"):
            _ground(byte_cap=cap)  # type: ignore[arg-type]
