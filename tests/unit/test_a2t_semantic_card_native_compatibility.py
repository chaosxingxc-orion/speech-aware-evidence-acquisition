"""Opt-in native-compatible Audio2Tool semantic-card presentation."""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_compile_a2t as compilation
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


PUBLIC_FIRST_FIXTURE_SHA256 = (
    "3907295f80e4d98837ac890fa64290c35df0dea86667f6b70e61eb6b701cdb77"
)


def _registry() -> tuple[dict[str, str], ...]:
    rows = [
        {
            "tool_id": "0",
            "domain": "calendar",
            "category": "scheduling",
            "tool_name": "scheduleSynthetic",
            "signature": "scheduleSynthetic(account: String, day: String?, hour: Int?)",
            "description": "Schedule an artificial calendar entry.",
            "argument_defaults": "",
            "argument_constraints": "hour: [0-23]",
        },
        {
            "tool_id": "1",
            "domain": "calendar",
            "category": "lookup",
            "tool_name": "lookupSynthetic",
            "signature": "lookupSynthetic(account: String, region: String?)",
            "description": "Look up an artificial calendar entry.",
            "argument_defaults": "",
            "argument_constraints": "",
        },
    ]
    for index in range(150):
        name = f"syntheticTool{index:03d}"
        rows.append(
            {
                "tool_id": str(index + 2),
                "domain": "synthetic",
                "category": f"group_{index % 5}",
                "tool_name": name,
                "signature": f"{name}()",
                "description": f"Perform synthetic operation {index:03d}.",
                "argument_defaults": "",
                "argument_constraints": "",
            }
        )
    assert len(rows) == 152
    return tuple(rows)


def _row(
    index: int,
    keys: tuple[str, ...],
    *,
    values: dict[str, str] | None = None,
) -> A2tKbRow:
    serialized = values or {key: f"PRIVATE_{key.upper()}_VALUE" for key in keys}
    return A2tKbRow(
        unit_id=f"tier1_direct:{index:06d}",
        tier="tier1_direct",
        query_idx=index,
        text="PRIVATE CONSTRUCTION UTTERANCE",
        domain="private",
        category="private",
        tool_id=0,
        tool_name="scheduleSynthetic",
        arg_signature=keys,
        arg_pairs=tuple((key, serialized[key]) for key in keys),
        call_render="PRIVATE GOLD CALL",
        extra_call_names=(),
        call_count=1,
        sample_ids=(f"tier1_direct:{index:06d}",),
        item_ids=(index,),
        media_relpath_by_sample_id={
            f"tier1_direct:{index:06d}": "private/synthetic.wav"
        },
        speaker_ids=("PRIVATE SPEAKER",),
    )


def test_native_replacement_is_separate_from_public_documentation() -> None:
    rows = (_row(1, ("legacyFlag",)), _row(2, ("legacyFlag",)))

    corpus, report = compilation.build_from_partition_with_native_compatibility(
        _registry(), rows
    )

    card = corpus.cards_by_name["scheduleSynthetic"]
    assert card.public_required_argument_keys == ("account",)
    assert card.public_optional_argument_keys == ("day", "hour")
    assert card.construction_observed_argument_patterns == (("legacyFlag",),)
    assert card.native_task_form_rules[0].legal_argument_key_set == ("legacyFlag",)
    assert "Public API documentation:" in card.text
    assert "Observed native replacement form" in card.text
    assert "do not force omitted public required keys" in corpus.text
    assert "not exhaustive" in corpus.text
    assert "does not prohibit public combinations" in corpus.text
    assert "when the user request grounds every named role" in corpus.text
    assert "PRIVATE_" not in corpus.text
    assert "exact legal argument-key set from its card" not in corpus.text
    assert "Legal argument-key sets:" not in corpus.text
    assert "Training-supported compatibility rule" not in corpus.text

    native_example = json.loads(card.native_task_form_examples[0])
    assert native_example["name"] == "scheduleSynthetic"
    assert set(native_example["arguments"]) == {"legacyFlag"}
    assert "account" not in native_example["arguments"]
    assert (
        report["presentation_version"] == compilation.NATIVE_COMPATIBLE_PRESENTATION_V1
    )
    assert report["public_required_keys_forced_into_observed_replacements"] is False
    assert report["observations_exhaustive"] is False
    assert report["unobserved_public_combinations_forbidden"] is False


def test_observed_replacement_can_omit_a_public_required_key() -> None:
    rows = (_row(1, ("day",)), _row(2, ("day",)))

    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        _registry(), rows
    )

    card = corpus.cards_by_name["scheduleSynthetic"]
    rule = card.native_task_form_rules[0]
    assert rule.legal_argument_key_set == ("day",)
    assert rule.value_forms == ()
    assert "Observed native replacement form {day}" in card.text
    native_example = json.loads(card.native_task_form_examples[0])
    assert set(native_example["arguments"]) == {"day"}
    assert "account" not in native_example["arguments"]


def test_native_extension_keeps_public_combinations_available() -> None:
    rows = (
        _row(1, ("account", "legacyFlag")),
        _row(2, ("account", "legacyFlag")),
    )

    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        _registry(), rows
    )

    card = corpus.cards_by_name["scheduleSynthetic"]
    assert "Observed native extension form" in card.text
    assert "construction support count: 2" in card.text
    assert "Small support counts are narrow evidence" in corpus.text
    assert "may include any subset of the public optional keys" in card.text
    assert any(
        "legacy flag -> legacyFlag" in line for line in card.native_role_guidance
    )


def test_schema_only_tools_retain_public_documentation_without_native_claims() -> None:
    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        _registry(), (_row(1, ("account",)),)
    )

    assert len(corpus.tool_cards) == 152
    card = corpus.cards_by_name["lookupSynthetic"]
    assert card.public_required_argument_keys == ("account",)
    assert card.public_optional_argument_keys == ("region",)
    assert card.construction_observed_argument_patterns == ()
    assert card.native_task_form_rules == ()
    assert "Observed native task forms: none supported." in card.text


def test_native_presentation_excludes_scorer_lexical_artifacts() -> None:
    rows = (
        _row(1, ("legacyNull",), values={"legacyNull": "null"}),
        _row(2, ("legacyNull",), values={"legacyNull": "null"}),
    )

    corpus, report = compilation.build_from_partition_with_native_compatibility(
        _registry(), rows
    )

    card = corpus.cards_by_name["scheduleSynthetic"]
    assert card.native_task_form_rules == ()
    assert "legacyNull" not in corpus.text
    assert "nullable-string" not in corpus.text
    assert "boolean-string" not in corpus.text
    assert "first-call" not in corpus.text.lower()
    assert report["scorer_lexical_form_patterns_excluded"] == 1
    assert report["scorer_parsing_tricks_rendered"] == 0


def test_native_presentation_is_deterministic_and_counts_rendered_content() -> None:
    registry = _registry()
    rows = (
        _row(1, ("legacyFlag",)),
        _row(2, ("legacyFlag",)),
        _row(3, ("account", "day")),
    )

    first = compilation.build_from_partition_with_native_compatibility(registry, rows)
    second = compilation.build_from_partition_with_native_compatibility(
        tuple(reversed(registry)), tuple(reversed(rows))
    )

    assert first == second
    corpus, report = first
    assert corpus.report["rendered_native_task_form_count"] == sum(
        len(card.native_task_form_rules) for card in corpus.tool_cards
    )
    assert corpus.report["rendered_observed_argument_pattern_count"] == sum(
        len(card.construction_observed_argument_patterns) for card in corpus.tool_cards
    )
    rendered_example_count = sum(len(card.examples) for card in corpus.tool_cards)
    assert corpus.report["example_count"] == rendered_example_count
    assert corpus.report["rendered_example_count"] == rendered_example_count
    assert corpus.report["spoken_role_guidance_count"] == sum(
        len(card.role_guidance) for card in corpus.tool_cards
    )
    assert (
        corpus.report["spoken_role_guidance_count"]
        == corpus.report["rendered_role_guidance_count"]
    )
    assert corpus.report["tool_card_count"] == len(corpus.tool_cards)
    assert corpus.report["task_card_count"] == len(corpus.task_cards)
    assert corpus.report["construction_summary_count"] == len(rows)
    assert corpus.report["construction_tool_count"] == sum(
        bool(card.construction_observed_argument_patterns) for card in corpus.tool_cards
    )
    assert corpus.report["compatibility_rule_count"] == sum(
        len(card.native_task_form_rules) for card in corpus.tool_cards
    )
    assert (
        corpus.report["compatibility_rule_construction_support_count"]
        == (corpus.report["rendered_native_task_form_support_count"])
    )
    assert corpus.report["rendered_native_task_form_example_count"] == sum(
        len(card.native_task_form_examples) for card in corpus.tool_cards
    )
    assert corpus.report["rendered_native_role_guidance_count"] == sum(
        len(card.native_role_guidance) for card in corpus.tool_cards
    )
    assert (
        report["rendered_native_task_form_count"]
        == corpus.report["rendered_native_task_form_count"]
    )


def test_native_report_counts_public_constraint_literals_in_rendered_examples() -> None:
    rows = (
        _row(1, ("account", "hour", "legacyFlag")),
        _row(2, ("account", "hour", "legacyFlag")),
    )

    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        _registry(), rows
    )

    rendered_hour_literals = sum(
        "hour" in json.loads(example)["arguments"]
        for card in corpus.tool_cards
        for example in card.examples
    )
    assert rendered_hour_literals == 2
    assert (
        corpus.report["public_constraint_example_literal_count"]
        == rendered_hour_literals
    )


def test_legacy_and_public_first_presentations_keep_their_exact_bytes() -> None:
    registry = _registry()
    row = _row(1, ("account", "day"))

    public, _report = compilation.build_from_partition_with_public_legality(
        registry, (row,)
    )
    legacy_first = compilation.build_from_partition(registry, (row,))
    legacy_second = compilation.build_from_partition(registry, (row,))

    assert public.sha256 == PUBLIC_FIRST_FIXTURE_SHA256
    assert legacy_first == legacy_second


def test_native_header_preserves_the_json_array_output_contract() -> None:
    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        _registry(), (_row(1, ("account",)),)
    )

    assert "Return only one JSON array." in corpus.text
    assert "Every element must be exactly" in corpus.text
    assert (
        "Copy task values only from the speech or its same-core observation."
        in corpus.text
    )


def _snapshot_source(
    corpus: compilation.NativeCompatibleSemanticCardCorpus,
    *,
    tool_registry_sha256: str = "3" * 64,
) -> dict[str, object]:
    return {
        "schema": compilation.NATIVE_CARD_SNAPSHOT_SOURCE_V1,
        "compilation_id": "SYNTHETIC-NATIVE-CARD-SNAPSHOT",
        "presentation_version": compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        "dataset_lock_sha256": "1" * 64,
        "construction_selection_sha256": "2" * 64,
        "tool_registry_sha256": tool_registry_sha256,
        "corpus_sha256": corpus.sha256,
        "minimum_compatibility_support": 2,
        "max_utf8_bytes": 524288,
    }


def test_snapshot_key_combines_public_and_native_positive_guidance_once() -> None:
    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        _registry(),
        (
            _row(1, ("account", "legacyFlag")),
            _row(2, ("account", "legacyFlag")),
        ),
    )

    snapshot = compilation.build_native_compatible_knowledge_snapshot(
        corpus,
        compilation_source=_snapshot_source(corpus),
    )

    values = {value.task_target: value for value in snapshot.values}
    facets = {facet.facet_id: facet for facet in snapshot.facets}
    value = values["scheduleSynthetic"]
    key_text = facets[value.associated_facet_ids[0]].representation
    card = corpus.cards_by_name["scheduleSynthetic"]
    assert "Exact tool name: scheduleSynthetic (schedule synthetic)." in key_text
    assert key_text.count("Spoken role: account -> account (String).") == 1
    assert key_text.count("Observed native role: legacy flag -> legacyFlag") == 1
    assert card.avoid_semantics not in key_text
    assert value.content == card.text
    assert value.task_target == card.tool_name


def test_snapshot_identity_changes_with_compilation_source_and_refuses_corpus_drift() -> (
    None
):
    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        _registry(), (_row(1, ("account",)),)
    )
    source = _snapshot_source(corpus)

    first = compilation.build_native_compatible_knowledge_snapshot(
        corpus, compilation_source=source
    )
    second = compilation.build_native_compatible_knowledge_snapshot(
        corpus,
        compilation_source={**source, "tool_registry_sha256": "4" * 64},
    )

    assert first.source_split_identity_hash != second.source_split_identity_hash
    assert first.content_hash() != second.content_hash()
    with pytest.raises(
        compilation.SemanticCardCompilationError,
        match="does not bind its corpus",
    ):
        compilation.build_native_compatible_knowledge_snapshot(
            corpus,
            compilation_source={**source, "corpus_sha256": "5" * 64},
        )
