"""Opt-in public-legality presentation for Audio2Tool semantic cards."""

from __future__ import annotations

import hashlib
import inspect

from speech_aware_evidence_acquisition.rails import (
    a2t_executable_semantic_cards as legacy_cards,
)
from speech_aware_evidence_acquisition.rails import (
    a2t_semantic_card_compilation as compilation,
)
from speech_aware_evidence_acquisition.rails.knowledge_build_a2t import A2tKbRow


LEGACY_COMPILER_SOURCE_SHA256 = (
    "414ab31f20fce3f6bb47fc08622c49be1395d9d036a478e9ff40c50c5c4aec8c"
)
LEGACY_RENDERER_SOURCE_SHA256 = (
    "0dca111e4562ca42973f2b1aa7f444036419f481ac8ecaab79c68ce5fe6de239"
)


def _registry() -> tuple[dict[str, str], ...]:
    rows = [
        {
            "tool_id": "0",
            "domain": "calendar",
            "category": "scheduling",
            "tool_name": "scheduleSynthetic",
            "signature": (
                "scheduleSynthetic(account: String, day: String?, hour: Int?)"
            ),
            "description": "Schedule an artificial calendar entry.",
            "argument_defaults": "",
            "argument_constraints": "",
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


def _row(index: int, keys: tuple[str, ...]) -> A2tKbRow:
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
        arg_pairs=tuple((key, f"PRIVATE_{key.upper()}_VALUE") for key in keys),
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


def _source_sha256(function) -> str:
    return hashlib.sha256(inspect.getsource(function).encode("utf-8")).hexdigest()


def test_historical_renderer_and_compiler_sources_remain_exact() -> None:
    assert (
        _source_sha256(legacy_cards.build_executable_semantic_card_corpus)
        == LEGACY_RENDERER_SOURCE_SHA256
    )
    assert (
        _source_sha256(compilation.build_from_partition)
        == LEGACY_COMPILER_SOURCE_SHA256
    )


def test_public_legality_is_separate_from_observed_patterns() -> None:
    corpus, report = compilation.build_from_partition_with_public_legality(
        _registry(), (_row(1, ("account", "day")),)
    )

    card = corpus.cards_by_name["scheduleSynthetic"]
    assert card.public_required_argument_keys == ("account",)
    assert card.public_optional_argument_keys == ("day", "hour")
    assert card.construction_observed_argument_patterns == (("account", "day"),)
    assert "may include any subset of the public optional keys" in card.text
    assert "unobserved public combinations remain legal" in card.text
    assert "Legal argument-key sets:" not in corpus.text
    assert "exact legal argument-key set from its card" not in corpus.text
    assert "observed legal argument-key sets" not in corpus.text
    assert "omitted public optional combinations remain legal" in card.text
    assert "PRIVATE_" not in corpus.text
    assert report["presentation_version"] == (
        compilation.PUBLIC_API_LEGALITY_PRESENTATION_V1
    )
    assert report["unobserved_public_combinations_forbidden"] is False


def test_schema_only_tool_keeps_public_required_and_optional_facts() -> None:
    corpus, _report = compilation.build_from_partition_with_public_legality(
        _registry(), (_row(1, ("account", "day")),)
    )

    card = corpus.cards_by_name["lookupSynthetic"]
    assert card.public_required_argument_keys == ("account",)
    assert card.public_optional_argument_keys == ("region",)
    assert card.construction_observed_argument_patterns == ()
    assert "Construction-observed argument patterns: none." in card.text


def test_public_legality_presentation_is_byte_deterministic() -> None:
    registry = _registry()
    rows = (
        _row(1, ("account", "day")),
        _row(2, ("account", "hour")),
    )

    first = compilation.build_from_partition_with_public_legality(registry, rows)
    second = compilation.build_from_partition_with_public_legality(
        tuple(reversed(registry)), tuple(reversed(rows))
    )

    assert first == second


def test_observed_compatibility_does_not_override_public_legality() -> None:
    rows = (
        _row(1, ("account", "legacyFlag")),
        _row(2, ("account", "legacyFlag")),
    )

    corpus, _report = compilation.build_from_partition_with_public_legality(
        _registry(), rows
    )

    card = corpus.cards_by_name["scheduleSynthetic"]
    assert card.public_required_argument_keys == ("account",)
    assert card.public_optional_argument_keys == ("day", "hour")
    assert card.construction_observed_argument_patterns == (("account", "legacyFlag"),)
    assert card.compatibility_rules[0].legal_argument_key_set == (
        "account",
        "legacyFlag",
    )
    assert "does not alter public argument legality" in card.text
    assert "Training-supported compatibility rule" not in card.text
    assert "may additionally admit" not in corpus.text
    assert all("legacyFlag" not in example for example in card.examples)
