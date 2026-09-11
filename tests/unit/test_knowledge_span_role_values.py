from __future__ import annotations

import json
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    KbEntityMention,
    KbRow,
    KbSourceToken,
    KnowledgeBuildSpec,
    VIEW_SLOT_FILLERS,
    build_knowledge_snapshot,
    slurp_kb_rows,
)


def _row(
    *,
    tokens: tuple[KbSourceToken, ...],
    mentions: tuple[KbEntityMention, ...],
) -> KbRow:
    sample_id = "slurp:train:1:audio-1"
    return KbRow(
        utterance_id="1",
        content="call New York then New York",
        scenario="communication",
        action="call",
        intent="communication_call",
        entity_types=("place_name",),
        entity_fillers={"place_name": ("new york",)},
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: "speaker-1"},
        media_relpath_by_sample_id={sample_id: "datasets/slurp/audio-1.flac"},
        source_tokens=tokens,
        entity_mentions=mentions,
    )


def _build(row: KbRow, value_format: str):
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp",
            dimensions=("content",),
            view=VIEW_SLOT_FILLERS,
            value_format=value_format,
        ),
        rows=(row,),
        forbidden_sample_ids=frozenset(),
    )


def _value_document(snapshot) -> dict[str, object]:
    assert len(snapshot.values) == 1
    return json.loads(snapshot.values[0].content)


def test_span_role_frame_preserves_tokens_mentions_multiplicity_and_delexicalizes():
    tokens = tuple(
        KbSourceToken(index, surface)
        for index, surface in enumerate(
            ("call", "New", "York", "then", "New", "York")
        )
    )
    mentions = (
        KbEntityMention("place_name", (1, 2), "New York"),
        KbEntityMention("place_name", (4, 5), "New York"),
    )
    document = _value_document(_build(_row(tokens=tokens, mentions=mentions), "span-role-frame"))

    assert document == {
        "schema": "saea-slurp-span-role-frame-v1",
        "sentence_tokens": [
            {"id": 0, "surface": "call"},
            {"id": 1, "surface": "New"},
            {"id": 2, "surface": "York"},
            {"id": 3, "surface": "then"},
            {"id": 4, "surface": "New"},
            {"id": 5, "surface": "York"},
        ],
        "ordered_mentions": [
            {
                "type": "place_name",
                "token_ids": [1, 2],
                "filler": "New York",
            },
            {
                "type": "place_name",
                "token_ids": [4, 5],
                "filler": "New York",
            },
        ],
        "delexicalized_typed_template": (
            "call {place_name} then {place_name}"
        ),
    }


def test_span_role_frame_keeps_existing_keys_order_and_value_metadata():
    row = _row(
        tokens=(KbSourceToken(0, "nothing"),),
        mentions=(),
    )
    historical = _build(row, "historical")
    framed = _build(row, "span-role-frame")

    assert [facet.as_json() for facet in framed.facets] == [
        facet.as_json() for facet in historical.facets
    ]
    assert len(framed.values) == len(historical.values) == 1
    old = historical.values[0].as_json()
    new = framed.values[0].as_json()
    assert {key: value for key, value in new.items() if key != "content"} == {
        key: value for key, value in old.items() if key != "content"
    }


def test_actual_train_default_legacy_and_source_annotations(slurp_world):
    lock = load_lock(slurp_world.lock_path)
    rows = slurp_kb_rows(lock, slurp_world.data_root)
    assert [row.utterance_id for row in rows] == ["301", "302"]
    assert rows[0].entity_fillers == {"house_place": ("kitchen",)}
    assert rows[0].source_tokens[-1] == KbSourceToken(5, "kitchen")
    assert rows[0].entity_mentions == (
        KbEntityMention("house_place", (5,), "kitchen"),
    )

    historical = build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp",
            dimensions=("content",),
            view=VIEW_SLOT_FILLERS,
        ),
        rows=rows,
        forbidden_sample_ids=frozenset(),
    )
    assert historical.values[0].content == (
        "Slot type=filler pairs observed in TRAIN utterance 301: "
        "house_place=kitchen."
    )


def test_no_entity_value_keeps_tokens_and_plain_template():
    row = _row(
        tokens=(
            KbSourceToken(0, "what"),
            KbSourceToken(1, "now"),
        ),
        mentions=(),
    )
    document = _value_document(_build(row, "span-role-frame"))
    assert document["ordered_mentions"] == []
    assert document["delexicalized_typed_template"] == "what now"


@pytest.mark.parametrize(
    ("row", "message"),
    [
        (
            _row(
                tokens=(KbSourceToken(0, "call"),),
                mentions=(KbEntityMention("person", (1,), "Alice"),),
            ),
            "unknown token ID",
        ),
        (
            _row(
                tokens=(KbSourceToken(0, "call"),),
                mentions=(KbEntityMention("person", (), ""),),
            ),
            "non-empty token IDs",
        ),
        (
            _row(
                tokens=(KbSourceToken(0, "call"), KbSourceToken(0, "again")),
                mentions=(),
            ),
            "token IDs must be unique",
        ),
    ],
)
def test_span_role_frame_refuses_invalid_annotations(row, message):
    with pytest.raises(RailsError, match=message):
        _build(row, "span-role-frame")


def test_overlap_or_noncontiguous_span_retains_mentions_but_omits_template():
    tokens = tuple(
        KbSourceToken(index, surface)
        for index, surface in enumerate(("book", "New", "York", "today"))
    )
    overlapping = _row(
        tokens=tokens,
        mentions=(
            KbEntityMention("place_name", (1, 2), "New York"),
            KbEntityMention("date", (2, 3), "York today"),
        ),
    )
    overlap_document = _value_document(_build(overlapping, "span-role-frame"))
    assert len(overlap_document["ordered_mentions"]) == 2
    assert overlap_document["delexicalized_typed_template"] is None

    noncontiguous = replace(
        overlapping,
        entity_mentions=(
            KbEntityMention("place_name", (1, 3), "New today"),
        ),
    )
    noncontiguous_document = _value_document(
        _build(noncontiguous, "span-role-frame")
    )
    assert noncontiguous_document["ordered_mentions"][0]["token_ids"] == [1, 3]
    assert noncontiguous_document["delexicalized_typed_template"] is None

    duplicate = replace(
        overlapping,
        entity_mentions=(
            KbEntityMention("place_name", (1, 2), "New York"),
            KbEntityMention("place_name", (1, 2), "New York"),
        ),
    )
    duplicate_document = _value_document(_build(duplicate, "span-role-frame"))
    assert duplicate_document["ordered_mentions"] == [
        {"type": "place_name", "token_ids": [1, 2], "filler": "New York"},
        {"type": "place_name", "token_ids": [1, 2], "filler": "New York"},
    ]
    assert duplicate_document["delexicalized_typed_template"] is None


def test_cli_and_spec_accept_span_role_frame_without_intent_label():
    spec = KnowledgeBuildSpec(
        carrier_lock_key="slurp",
        dimensions=("content",),
        view=VIEW_SLOT_FILLERS,
        value_format="span-role-frame",
    ).validate()
    assert spec.value_format == "span-role-frame"

    document = _value_document(
        _build(
            _row(
                tokens=(KbSourceToken(0, "hello"),),
                mentions=(),
            ),
            "span-role-frame",
        )
    )
    encoded = json.dumps(document)
    assert "communication_call" not in encoded
    assert "scenario" not in encoded
    assert "action" not in encoded
