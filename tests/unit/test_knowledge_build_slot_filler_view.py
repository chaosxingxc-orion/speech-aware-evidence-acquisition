"""KB-BUILD's SLOT-FILLER view (cell KU-S3, 2026-09-07).

The view exists because a cell that RECALLS on per-utterance content facets
must BIND them, and the exemplar view's content facets are raw TRAIN
utterances that the runner's leakage rule then finds inside ordinary English.
These tests pin the two rendered strings, the refusals, and -- the property
that matters most -- that every snapshot built before this view existed keeps
its bytes.

MODEL-FREE and filesystem-free: a small synthetic ``KbRow`` corpus only.
"""

from __future__ import annotations

import pytest

from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.knowledge_build import (
    VIEW_EXEMPLAR,
    VIEW_SLOT_FILLERS,
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
        _row("1", scenario="alarm", action="set", words="how much",
             entity_fillers={"date": ("friday",), "time": ("nine am",)}),
        _row("2", scenario="alarm", action="set", words="wake me at six",
             entity_fillers={"time": ("six",)}),
        _row("3", scenario="iot", action="hue_lightoff", words="lights off"),
        _row("4", scenario="iot", action="hue_lightoff", words="turn the lamp off",
             entity_fillers={"device_type": ("lamp",)}),
    )


def _build(view: str, dimensions=("content",)):
    return build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp", dimensions=dimensions, view=view
        ).validate(),
        rows=_rows(),
        forbidden_sample_ids=frozenset(),
    )


def test_the_default_view_is_the_exemplar_one() -> None:
    assert KnowledgeBuildSpec(carrier_lock_key="slurp").view == VIEW_EXEMPLAR


def test_a_bare_utterance_is_a_protected_payload_under_the_exemplar_view() -> None:
    """The measured defect, in one assertion: the exemplar view protects
    ``how much``, so any SLURP instruction containing those two words is
    refused by ``rails.runner._assert_agent_control_excludes_knowledge_
    payloads``."""

    snapshot = _build(VIEW_EXEMPLAR)
    representations = {facet.representation for facet in snapshot.facets}
    assert "how much" in representations
    assert any(len(text.strip()) >= 8 for text in representations if text == "how much")


def test_the_slot_filler_view_quotes_the_utterance_inside_a_descriptor() -> None:
    snapshot = _build(VIEW_SLOT_FILLERS)
    by_id = {facet.facet_id: facet for facet in snapshot.facets}
    facet = by_id["facet:content:1"]
    assert facet.representation == (
        'TRAIN utterance 1 (slot-filler retrieval key): "how much"'
    )
    # the utterance is still IN the key, so a cell that exposes facets still
    # shows it; it is no longer the whole protected payload.
    assert "how much" in facet.representation
    assert facet.representation != "how much"


def test_the_slot_filler_view_renders_fillers_and_nothing_else() -> None:
    snapshot = _build(VIEW_SLOT_FILLERS)
    by_id = {value.value_id: value for value in snapshot.values}
    assert by_id["value:1"].content == (
        "Slot type=filler pairs observed in TRAIN utterance 1: "
        "date=friday; time=nine am."
    )
    for value in snapshot.values:
        assert "Exemplar sentence" not in value.content
        assert "-> intent" not in value.content
        assert "surface-form variants" not in value.content
        assert "Entity-type prior" not in value.content


def test_an_utterance_with_no_entity_still_gets_a_value() -> None:
    snapshot = _build(VIEW_SLOT_FILLERS)
    by_id = {value.value_id: value for value in snapshot.values}
    assert by_id["value:3"].content == (
        "Slot type=filler pairs observed in TRAIN utterance 3: none recorded."
    )


def test_ids_priors_and_provenance_are_identical_across_the_two_views() -> None:
    """The view changes two rendered strings. Everything a downstream artifact
    is pinned to -- facet ids (the sealed key vectors are keyed by them),
    value ids, prior scores, source samples, provenance -- must not move."""

    exemplar = _build(VIEW_EXEMPLAR)
    fillers = _build(VIEW_SLOT_FILLERS)
    assert [f.facet_id for f in exemplar.facets] == [f.facet_id for f in fillers.facets]
    assert [f.dimension for f in exemplar.facets] == [f.dimension for f in fillers.facets]
    assert [v.value_id for v in exemplar.values] == [v.value_id for v in fillers.values]
    assert [v.prior_score for v in exemplar.values] == [
        v.prior_score for v in fillers.values
    ]
    assert [v.provenance_refs for v in exemplar.values] == [
        v.provenance_refs for v in fillers.values
    ]
    assert [v.task_target for v in exemplar.values] == [
        v.task_target for v in fillers.values
    ]
    assert exemplar.source_sample_ids == fillers.source_sample_ids
    assert exemplar.content_hash() != fillers.content_hash()


@pytest.mark.parametrize(
    "receipt_name,dimensions",
    [
        ("slurp-kb-size-full.json", ("content", "label", "speaker", "prior")),
        ("slurp-kb-size-full-label-prior-speaker.json", ("label", "speaker", "prior")),
    ],
)
def test_every_committed_snapshot_keeps_its_bytes(receipt_name, dimensions) -> None:
    """The regression that matters: a default-view build hashes exactly as it
    did before 2026-09-07, because the build descriptor gains a ``view`` key
    only for a NON-default view.

    Proved against the REAL committed receipts -- KU-S1 pins ``size-full``'s
    hash and KC-S1a/b pin ``size-full-label-prior-speaker``'s -- whenever
    ``SPEECHRL_DATA_DIR`` carries the governed TRAIN corpus. The dimension
    tuple is taken in the receipt's own ORDER, because the descriptor hashes
    the list as given.
    """

    import json
    import os

    if not os.environ.get("SPEECHRL_DATA_DIR"):
        pytest.skip("SPEECHRL_DATA_DIR is not set; the governed TRAIN corpus is absent")
    from speech_aware_evidence_acquisition.data.lock import (
        REPO_ROOT,
        data_root,
        load_lock,
        umbrella_lock_path,
    )
    from speech_aware_evidence_acquisition.rails.knowledge_build import slurp_kb_rows

    receipt_path = REPO_ROOT / "docs" / "receipts" / "knowledge" / receipt_name
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert list(receipt["spec"]["dimensions"]) == list(dimensions)
    lock = load_lock(umbrella_lock_path())
    root = data_root()
    snapshot = build_knowledge_snapshot(
        KnowledgeBuildSpec(
            carrier_lock_key="slurp",
            datastore_size=receipt["spec"]["datastore_size"],
            seed=receipt["spec"]["seed"],
            dimensions=tuple(dimensions),
        ),
        lock=lock,
        root=root,
        rows=slurp_kb_rows(lock, root),
    )
    assert snapshot.frozen_json()["snapshot_sha256"] == receipt["snapshot_sha256"]


def test_the_slot_filler_view_requires_the_content_dimension() -> None:
    with pytest.raises(RailsError, match="requires the 'content' dimension"):
        KnowledgeBuildSpec(
            carrier_lock_key="slurp",
            dimensions=("label", "prior"),
            view=VIEW_SLOT_FILLERS,
        ).validate()


def test_an_unknown_view_is_refused() -> None:
    with pytest.raises(RailsError, match="view must be one of"):
        KnowledgeBuildSpec(carrier_lock_key="slurp", view="fillers").validate()
