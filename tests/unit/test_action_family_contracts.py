"""Construction-only tests for exhaustive action-family contracts."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.rails.action_family_contracts import (
    ActionFamilyContractError,
    build_action_family_corpus,
    compile_family_bundle,
    qualify_action_family_corpus,
    split_construction_validation,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


def _registry_row(
    name: str,
    signature: str,
    *,
    domain: str = "Media",
    category: str = "Playback Control",
    defaults: str = "",
    constraints: str = "",
) -> dict[str, str]:
    return {
        "tool_id": "1",
        "domain": domain,
        "category": category,
        "tool_name": name,
        "signature": signature,
        "description": f"Perform the public {name} operation.",
        "argument_defaults": defaults,
        "argument_constraints": constraints,
    }


def _row(
    index: int,
    tool: str,
    pairs: tuple[tuple[str, str], ...],
    *,
    extra_calls: tuple[str, ...] = (),
    query_idx: int | None = None,
) -> A2tKbRow:
    return A2tKbRow(
        unit_id=f"tier1_direct:{index:06d}",
        tier="tier1_direct",
        query_idx=index if query_idx is None else query_idx,
        text="PRIVATE CONSTRUCTION UTTERANCE",
        domain="private",
        category="private",
        tool_id=index,
        tool_name=tool,
        arg_signature=tuple(sorted(key for key, _value in pairs)),
        arg_pairs=tuple(sorted(pairs)),
        call_render="PRIVATE CONCRETE CALL",
        extra_call_names=extra_calls,
        call_count=1 + len(extra_calls),
        sample_ids=(f"tier1_direct:PRIVATE_{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={},
        speaker_ids=("PRIVATE SPEAKER",),
    )


def _world():
    registry = (
        _registry_row(
            "controlPlayback",
            "controlPlayback(action: MediaAction, deviceId: String?)",
            constraints="action: [Play, Pause]",
        ),
        _registry_row(
            "setAdaptiveLighting",
            "setAdaptiveLighting(deviceId: String, enabled: Boolean)",
            domain="Smart Home",
            category="Lighting",
        ),
        _registry_row(
            "searchPOI",
            "searchPOI(category: String, filter: String?)",
            domain="Navigation",
            category="Point of Interest",
            defaults="filter: omitted",
        ),
    )
    rows = (
        _row(1, "controlPlayback", (("action", '"Play"'),)),
        _row(
            2,
            "controlPlayback",
            (("action", '"Pause"'), ("deviceId", '"PRIVATE DEVICE"')),
        ),
        _row(
            3,
            "setAdaptiveLighting",
            (("deviceId", '"PRIVATE LIGHT"'), ("enabled", "true")),
        ),
        _row(4, "searchPOI", (("category", '"PRIVATE CATEGORY"'),)),
        _row(
            5,
            "searchPOI",
            (("category", '"PRIVATE CATEGORY"'), ("filter", "null")),
            extra_calls=("controlPlayback",),
        ),
    )
    return registry, rows


def test_builder_emits_closed_exhaustive_contracts_without_source_literals() -> None:
    registry, rows = _world()

    corpus = build_action_family_corpus(registry, rows)

    assert corpus.taxonomy == (
        ("media-playback-control", "Media / Playback Control"),
        ("navigation-point-of-interest", "Navigation / Point of Interest"),
        ("smart-home-lighting", "Smart Home / Lighting"),
    )
    playback = corpus.contracts_by_tool["controlPlayback"]
    assert playback.ordered_keys == ("action", "deviceId")
    assert playback.required_keys == ("action",)
    assert playback.optional_keys == ("deviceId",)
    assert playback.conditional_keys == ()
    assert playback.forbidden_keys == ()
    assert playback.legal_key_skeletons == (("action",), ("action", "deviceId"))
    assert playback.types == (("action", "MediaAction"), ("deviceId", "String"))
    assert playback.canonicalization_rules
    serialized = corpus.to_json()
    for private in (
        "PRIVATE CONSTRUCTION UTTERANCE",
        "PRIVATE DEVICE",
        "PRIVATE CONCRETE CALL",
        "PRIVATE_000001",
        "PRIVATE SPEAKER",
        "SYNTHETIC_",
    ):
        assert private not in serialized
    assert serialized.isascii()


def test_family_compiler_returns_every_contract_in_registry_order_not_a_subset() -> None:
    registry = (
        _registry_row("zetaAction", "zetaAction(value: String)"),
        _registry_row("alphaAction", "alphaAction(value: String)"),
        _registry_row(
            "otherAction",
            "otherAction()",
            domain="Other",
            category="Other",
        ),
    )
    rows = (
        _row(1, "zetaAction", (("value", '"PRIVATE"'),)),
        _row(2, "alphaAction", (("value", '"PRIVATE"'),)),
        _row(3, "otherAction", ()),
    )
    corpus = build_action_family_corpus(registry, rows)

    bundle = compile_family_bundle(corpus, ("media-playback-control",))

    assert bundle.tool_names == ("alphaAction", "zetaAction")
    assert "otherAction" not in bundle.text
    assert bundle.text.index("alphaAction") < bundle.text.index("zetaAction")
    assert bundle.utf8_bytes <= 18_432


def test_family_compiler_rejects_unknown_tags_and_partial_trimming() -> None:
    registry, rows = _world()
    corpus = build_action_family_corpus(registry, rows)

    with pytest.raises(ActionFamilyContractError, match="unknown family"):
        compile_family_bundle(corpus, ("unregistered-family",))
    with pytest.raises(ActionFamilyContractError, match="complete bundle"):
        compile_family_bundle(corpus, ("media-playback-control",), max_ascii_bytes=10)


def test_builder_rejects_malformed_registry_and_declares_syntax_exclusions() -> None:
    registry = (_registry_row("safeTool", "safeTool(value: String)"),)
    rows = (
        _row(1, "safeTool", (("value", '"PRIVATE"'),)),
        _row(2, "safeTool", (("malformed:[", '"PRIVATE"'),)),
    )

    corpus = build_action_family_corpus(registry, rows)

    assert corpus.report["syntax_incompatible_skeleton_count"] == 1
    assert corpus.contracts_by_tool["safeTool"].legal_key_skeletons == (("value",),)
    with pytest.raises(ActionFamilyContractError, match="ASCII"):
        build_action_family_corpus(
            ({**registry[0], "description": "non-English caf\u00e9"},), rows[:1]
        )


def test_reverse_order_build_is_byte_stable() -> None:
    registry, rows = _world()

    forward = build_action_family_corpus(registry, rows)
    reverse = build_action_family_corpus(tuple(reversed(registry)), tuple(reversed(rows)))

    assert forward.sha256 == reverse.sha256
    assert forward.to_json() == reverse.to_json()


def test_construction_validation_split_is_query_block_disjoint_and_stable() -> None:
    rows = (
        _row(1, "controlPlayback", (("action", '"PRIVATE"'),)),
        _row(2, "controlPlayback", (("action", '"PRIVATE"'),)),
        _row(3, "searchPOI", (("category", '"PRIVATE"'),)),
        _row(4, "searchPOI", (("category", '"PRIVATE"'),)),
    )

    build_a, validation_a = split_construction_validation(rows, seed=20260902)
    build_b, validation_b = split_construction_validation(
        tuple(reversed(rows)), seed=20260902
    )

    assert tuple(row.unit_id for row in build_a) == tuple(row.unit_id for row in build_b)
    assert tuple(row.unit_id for row in validation_a) == tuple(
        row.unit_id for row in validation_b
    )
    assert {row.query_idx for row in build_a}.isdisjoint(
        row.query_idx for row in validation_a
    )
    assert build_a and validation_a


def test_model_free_qualification_measures_all_required_gates() -> None:
    registry, rows = _world()
    corpus = build_action_family_corpus(registry, rows[:4])

    result = qualify_action_family_corpus(
        corpus,
        registry_rows=registry,
        validation_rows=rows[4:],
    )

    assert result.gates == {
        "complete_gold_tool_set_recall_at_least_90_percent": True,
        "registry_validity_100_percent": True,
        "legal_key_skeleton_inclusion_100_percent": True,
        "artificial_literal_count_zero": True,
        "reverse_order_build_hash_stable": True,
        "family_bundle_ascii_bytes_at_most_18432": True,
    }
    assert result.passed is True
    assert result.metrics["complete_gold_tool_set_recall"] == 1.0
    assert result.metrics["registry_validity"] == 1.0
    assert result.metrics["legal_key_skeleton_inclusion"] == 1.0
    assert json.loads(corpus.to_json())["schema"] == "saea-action-family-contract-corpus-v1"


def test_qualification_fails_closed_instead_of_weakening_a_gate() -> None:
    registry, rows = _world()
    corpus = build_action_family_corpus(registry, rows[:1])
    incompatible = _row(
        99,
        "setAdaptiveLighting",
        (("constructionExtension", '"PRIVATE"'),),
        extra_calls=("outsideRegistry",),
    )

    result = qualify_action_family_corpus(
        corpus,
        registry_rows=registry,
        validation_rows=(incompatible,),
    )

    assert result.passed is False
    assert result.gates["complete_gold_tool_set_recall_at_least_90_percent"] is False
    assert result.gates["legal_key_skeleton_inclusion_100_percent"] is False
