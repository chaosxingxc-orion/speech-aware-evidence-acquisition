"""Bounded lexical contrast values for Audio2Tool activation knowledge."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import re

import pytest

from speech_aware_evidence_acquisition.rails import knowledge_compile_a2t as compilation
from speech_aware_evidence_acquisition.rails.errors import RailsError
from test_a2t_semantic_card_compilation import (
    _compile_native_view,
    _config_document,
    _native_source,
    _registry_rows,
    _row,
    _world,
    _write_json,
)


CONTRAST_VIEW = "tool-activation-contrast-v1"


def _contrast_corpus():
    registry = list(_registry_rows())
    definitions = (
        (
            "playMusic",
            "playMusic(secretParameter: String?)",
            "Play music on speaker.",
            "secretParameter: [private construction-only detail]",
        ),
        ("musicPlayQueue", "musicPlayQueue()", "Play music queue.", ""),
        ("playMusicNow", "playMusicNow()", "Play music now.", ""),
        ("playRadio", "playRadio()", "Play radio on speaker.", ""),
        ("stopMusic", "stopMusic()", "Stop music.", ""),
        ("weatherForecast", "weatherForecast()", "Report rain forecast.", ""),
    )
    for index, (name, signature, description, constraints) in enumerate(definitions):
        registry[index] = {
            **registry[index],
            "tool_name": name,
            "signature": signature,
            "description": description,
            "argument_constraints": constraints,
        }
    construction = replace(
        _row(),
        tool_name="playMusic",
        arg_signature=("secretParameter",),
        arg_pairs=(("secretParameter", '"PRIVATE VALUE"'),),
        call_render='playMusic(secretParameter="PRIVATE VALUE")',
    )
    corpus, _report = compilation.build_from_partition_with_native_compatibility(
        tuple(registry), (construction,)
    )
    return corpus


def _contrast_snapshot(corpus):
    return compilation.build_native_compatible_knowledge_snapshot(
        corpus,
        compilation_source=_native_source(corpus, value_view=CONTRAST_VIEW),
        value_view=CONTRAST_VIEW,
    )


def _content(snapshot, tool_name: str) -> str:
    return next(
        value.content for value in snapshot.values if value.task_target == tool_name
    )


def test_contrast_view_is_deterministic_and_preserves_all_positive_keys() -> None:
    corpus = _contrast_corpus()
    forward = _contrast_snapshot(corpus)
    reverse = _contrast_snapshot(
        replace(corpus, tool_cards=tuple(reversed(corpus.tool_cards)))
    )
    historical = compilation.build_native_compatible_knowledge_snapshot(
        corpus,
        compilation_source=_native_source(corpus, value_view="tool-activation"),
        value_view="tool-activation",
    )

    assert forward.frozen_json() == reverse.frozen_json()
    assert len(forward.facets) == len(forward.values) == 152
    assert [(facet.facet_id, facet.representation) for facet in forward.facets] == [
        (facet.facet_id, facet.representation) for facet in historical.facets
    ]
    assert forward.snapshot_id != historical.snapshot_id
    assert (
        forward.source_split_identity_hash
        != historical.source_split_identity_hash
    )
    assert {value.task_target for value in forward.values} == {
        card.tool_name for card in corpus.tool_cards
    }


def test_contrast_view_supplies_described_neighbors_with_strict_bounds() -> None:
    content = _content(_contrast_snapshot(_contrast_corpus()), "playMusic")

    assert "Exact tool name: playMusic" in content
    assert "Choose semantics: Play music on speaker." in content
    assert re.findall(
        r"^Lexically related alternative \d+ exact tool name: (.+)$",
        content,
        flags=re.MULTILINE,
    ) == ["musicPlayQueue", "playMusicNow", "playRadio"]
    for index, description in enumerate(
        ("Play music queue.", "Play music now.", "Play radio on speaker."), start=1
    ):
        assert (
            f"Lexically related alternative {index} choose semantics: {description}"
            in content
        )
    assert "stopMusic" not in content
    assert "weatherForecast" not in content
    assert "alternative 1 exact tool name: playMusic" not in content
    assert (
        "Related operations (lexical search aid; up to 3, non-exhaustive and "
        "non-exclusive):"
    ) in content
    assert "Compare the requested operation, object, and scope" in content
    for implementation_detail in (
        "set-Jaccard",
        "stopword",
        "camelCase",
        "alphanumeric token",
        "descending score",
    ):
        assert implementation_detail not in content

    zero_overlap_content = _content(
        _contrast_snapshot(_contrast_corpus()), "weatherForecast"
    )
    assert "Lexically related alternative" not in zero_overlap_content


def test_contrast_view_excludes_parameters_examples_sources_values_and_ids() -> None:
    content = _content(_contrast_snapshot(_contrast_corpus()), "playMusic")

    for forbidden in (
        "secretParameter",
        "PRIVATE VALUE",
        "Public signature:",
        "Public constraints:",
        "Avoid when:",
        "synthetic JSON",
        "Source-supported",
        "construction support",
        "tool_id",
        "unit_id",
    ):
        assert forbidden not in content


def test_contrast_view_does_not_parse_the_legacy_avoid_line() -> None:
    corpus = _contrast_corpus()
    target_index = next(
        index
        for index, card in enumerate(corpus.tool_cards)
        if card.tool_name == "playMusic"
    )
    cards = list(corpus.tool_cards)
    cards[target_index] = replace(
        cards[target_index],
        text=cards[target_index].text.replace(
            "Avoid when:", "Legacy generic avoid text:", 1
        ),
    )

    content = _content(
        _contrast_snapshot(replace(corpus, tool_cards=tuple(cards))), "playMusic"
    )

    assert "Choose semantics: Play music on speaker." in content
    assert "Legacy generic avoid text:" not in content


def test_contrast_view_receipt_binds_only_to_tool_activation_store(tmp_path: Path) -> None:
    receipt, snapshot = _compile_native_view(tmp_path, CONTRAST_VIEW)
    snapshot_path = tmp_path / "outputs" / "snapshot.json"
    snapshot_file_sha256 = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()

    metadata = compilation.validate_compiled_knowledge_snapshot(
        receipt,
        snapshot,
        store_role="tool-activation",
        snapshot_file_sha256=snapshot_file_sha256,
        snapshot_path=snapshot_path,
    )
    assert metadata["value_view"] == CONTRAST_VIEW
    assert receipt["knowledge_snapshot"]["value_view"] == CONTRAST_VIEW
    assert receipt["knowledge_snapshot"]["value_view_policy"] == (
        compilation._ACTIVATION_CONTRAST_POLICY_V1
    )
    assert "set-Jaccard" in receipt["knowledge_snapshot"]["value_view_policy"]
    assert "camelCase" in receipt["knowledge_snapshot"]["value_view_policy"]
    assert (
        f"a2t-native-card-value-view:{CONTRAST_VIEW}"
        in snapshot.values[0].provenance_refs
    )

    with pytest.raises(RailsError, match="compiled store role or compiler schema differs"):
        compilation.validate_compiled_knowledge_snapshot(
            receipt,
            snapshot,
            store_role="parameter-meaning",
            snapshot_file_sha256=snapshot_file_sha256,
            snapshot_path=snapshot_path,
        )


def test_compiler_config_parser_accepts_contrast_view(tmp_path: Path) -> None:
    config = replace(
        _world(tmp_path),
        presentation_version=compilation.NATIVE_COMPATIBLE_PRESENTATION_V1,
        snapshot_output_path=tmp_path / "outputs" / "snapshot.json",
        snapshot_value_view=CONTRAST_VIEW,
    )
    config_path = tmp_path / "compile.json"
    _write_json(config_path, _config_document(config))

    loaded = compilation.load_a2t_semantic_card_compilation_config(config_path)

    assert loaded == config


def test_contrast_view_refuses_source_metadata_view_tampering(tmp_path: Path) -> None:
    receipt, snapshot = _compile_native_view(tmp_path, CONTRAST_VIEW)
    snapshot_path = tmp_path / "outputs" / "snapshot.json"
    tampered = deepcopy(receipt)
    tampered["knowledge_snapshot"]["source"]["metadata"][
        "value_view"
    ] = "tool-activation"

    with pytest.raises(RailsError, match="compiled store role or compiler schema differs"):
        compilation.validate_compiled_knowledge_snapshot(
            tampered,
            snapshot,
            store_role="tool-activation",
            snapshot_file_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
            snapshot_path=snapshot_path,
        )


def test_contrast_view_rejects_non_text_receipt_and_metadata_views(
    tmp_path: Path,
) -> None:
    receipt, snapshot = _compile_native_view(tmp_path, CONTRAST_VIEW)
    snapshot_path = tmp_path / "outputs" / "snapshot.json"
    malformed = deepcopy(receipt)
    malformed_view = [CONTRAST_VIEW]
    malformed["knowledge_snapshot"]["value_view"] = malformed_view
    malformed["knowledge_snapshot"]["source"]["metadata"][
        "value_view"
    ] = malformed_view

    with pytest.raises(RailsError, match="compiled store role or compiler schema differs"):
        compilation.validate_compiled_knowledge_snapshot(
            malformed,
            snapshot,
            store_role="tool-activation",
            snapshot_file_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
            snapshot_path=snapshot_path,
        )


def test_contrast_view_rejects_receipt_policy_tampering(tmp_path: Path) -> None:
    receipt, snapshot = _compile_native_view(tmp_path, CONTRAST_VIEW)
    snapshot_path = tmp_path / "outputs" / "snapshot.json"
    tampered = deepcopy(receipt)
    tampered["knowledge_snapshot"]["value_view_policy"] = "different policy"

    with pytest.raises(RailsError, match="compiled store role or compiler schema differs"):
        compilation.validate_compiled_knowledge_snapshot(
            tampered,
            snapshot,
            store_role="tool-activation",
            snapshot_file_sha256=hashlib.sha256(snapshot_path.read_bytes()).hexdigest(),
            snapshot_path=snapshot_path,
        )


def test_new_view_keeps_historical_default_snapshot_bytes_unchanged(
    tmp_path: Path,
) -> None:
    _receipt, snapshot = _compile_native_view(tmp_path, None)
    frozen_bytes = (json.dumps(snapshot.frozen_json(), indent=2, sort_keys=True) + "\n").encode()

    assert snapshot.frozen_json()["snapshot_sha256"] == (
        "d88f144e5273c9497318a9fe568ff7d9b93e3b277256fffdeca7f3047bb21a2e"
    )
    assert hashlib.sha256(frozen_bytes).hexdigest() == (
        "8d476d35537c4fd5292571026fa268b20950dde965d324e262c65baf5a591c2e"
    )
