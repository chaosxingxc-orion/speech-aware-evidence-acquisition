"""KB-BUILD's ANNOTATED-EXEMPLARS view (SLURP v2 base program item E3,
cell B1, 2026-09-17).

Same discipline as ``test_knowledge_build_slot_filler_view.py``: a small
synthetic ``KbRow`` corpus, model-free and filesystem-free, pinning the
rendered value string, the facet descriptor, the no-entity case, and the
property that matters most -- every id/prior/provenance is identical across
views, only the two rendered strings differ.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    VIEW_ANNOTATED_EXEMPLARS,
    VIEW_EXEMPLAR,
    KbRow,
    KnowledgeBuildSpec,
    build_knowledge_snapshot,
)


def _row(
    utterance_id: str,
    *,
    scenario: str,
    action: str,
    words: str,
    speaker_id: str = "FO-001",
    entity_fillers: dict[str, tuple[str, ...]] | None = None,
) -> KbRow:
    sample_id = f"slurp:train:{utterance_id}:audio-{utterance_id}"
    fillers = entity_fillers or {}
    return KbRow(
        utterance_id=utterance_id,
        content=words,
        scenario=scenario,
        action=action,
        intent=f"{scenario}_{action}",
        entity_types=tuple(sorted(fillers)),
        entity_fillers=fillers,
        sample_ids=(sample_id,),
        speaker_by_sample_id={sample_id: speaker_id},
        media_relpath_by_sample_id={sample_id: f"datasets/slurp/audio-{utterance_id}.flac"},
    )


def _rows() -> tuple[KbRow, ...]:
    return (
        _row("1", scenario="alarm", action="set", words="wake me at nine am on friday",
             entity_fillers={"date": ("friday",), "time": ("nine am",)}),
        _row("2", scenario="alarm", action="set", words="wake me at six",
             entity_fillers={"time": ("six",)}),
        _row("3", scenario="iot", action="hue_lightoff", words="lights off"),
        _row("4", scenario="cooking", action="recipe", words="find a recipe",
             entity_fillers={"food_type": ("pasta", "salad")}),
    )


def _build(view: str, dimensions=("content",)):
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp", dimensions=dimensions, view=view
        ).validate(),
        rows=_rows(),
        forbidden_sample_ids=frozenset(),
    )


def test_the_annotated_exemplars_view_quotes_the_utterance_inside_a_descriptor() -> None:
    snapshot = _build(VIEW_ANNOTATED_EXEMPLARS)
    by_id = {facet.facet_id: facet for facet in snapshot.facets}
    facet = by_id["facet:content:1"]
    assert facet.representation == (
        'TRAIN utterance 1 (annotated-exemplar retrieval key): '
        '"wake me at nine am on friday"'
    )
    assert "wake me at nine am on friday" in facet.representation
    assert facet.representation != "wake me at nine am on friday"


def test_the_annotated_exemplars_view_renders_utterance_label_and_fillers() -> None:
    snapshot = _build(VIEW_ANNOTATED_EXEMPLARS)
    by_id = {value.value_id: value for value in snapshot.values}
    assert by_id["value:1"].content == (
        "wake me at nine am on friday | alarm_set | date=friday; time=nine am"
    )
    for value in snapshot.values:
        assert "Exemplar sentence" not in value.content
        assert "-> intent" not in value.content
        assert "surface-form variants" not in value.content
        assert "Entity-type prior" not in value.content


def test_multiple_fillers_of_one_type_each_get_their_own_pair() -> None:
    snapshot = _build(VIEW_ANNOTATED_EXEMPLARS)
    by_id = {value.value_id: value for value in snapshot.values}
    assert by_id["value:4"].content == (
        "find a recipe | cooking_recipe | food_type=pasta; food_type=salad"
    )


def test_an_utterance_with_no_entity_renders_none() -> None:
    snapshot = _build(VIEW_ANNOTATED_EXEMPLARS)
    by_id = {value.value_id: value for value in snapshot.values}
    assert by_id["value:3"].content == "lights off | iot_hue_lightoff | none"


def test_ids_priors_and_provenance_are_identical_across_views() -> None:
    exemplar = _build(VIEW_EXEMPLAR)
    annotated = _build(VIEW_ANNOTATED_EXEMPLARS)
    assert [f.facet_id for f in exemplar.facets] == [f.facet_id for f in annotated.facets]
    assert [f.dimension for f in exemplar.facets] == [f.dimension for f in annotated.facets]
    assert [v.value_id for v in exemplar.values] == [v.value_id for v in annotated.values]
    assert [v.prior_score for v in exemplar.values] == [
        v.prior_score for v in annotated.values
    ]
    assert [v.provenance_refs for v in exemplar.values] == [
        v.provenance_refs for v in annotated.values
    ]
    assert [v.task_target for v in exemplar.values] == [
        v.task_target for v in annotated.values
    ]
    assert exemplar.source_sample_ids == annotated.source_sample_ids
    assert exemplar.content_hash() != annotated.content_hash()


def test_the_annotated_exemplars_view_requires_the_content_dimension() -> None:
    with pytest.raises(RailsError, match="requires the 'content' dimension"):
        KnowledgeBuildSpec(
            carrier_lock_key="slurp",
            dimensions=("label", "prior"),
            view=VIEW_ANNOTATED_EXEMPLARS,
        ).validate()


def test_annotated_exemplars_is_a_legal_view_choice() -> None:
    KnowledgeBuildSpec(
        carrier_lock_key="slurp", dimensions=("content",), view=VIEW_ANNOTATED_EXEMPLARS,
    ).validate()
