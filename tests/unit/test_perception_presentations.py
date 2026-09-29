"""Unit tests for the Perception-branch presentation registry (same-flight
instrument phase 2, merge set C, item 6).
"""

import pytest

from speech_aware_evidence_acquisition.core.base import (
    PERCEPTION_PRESENTATIONS,
    CoreError,
    PerceptionPresentationError,
    assert_perception_presentation,
)
from speech_aware_evidence_acquisition.rails import perception_presentations as pp


def test_both_presentations_are_registered():
    assert set(PERCEPTION_PRESENTATIONS.names()) == {
        pp.RANK_VISIBLE_PRESENTATION_ID, pp.TOP2_CONTRAST_PRESENTATION_ID,
    }


def test_rank_visible_wraps_the_existing_renderer():
    from speech_aware_evidence_acquisition.rails.runner import rank_visible_value_renderer

    entry = PERCEPTION_PRESENTATIONS.resolve(pp.RANK_VISIBLE_PRESENTATION_ID)
    assert entry.id == "rank-visible-v1"
    wrapped = entry(snapshot_sha256="a" * 64, stores=("intent-boundaries",))
    direct = rank_visible_value_renderer(snapshot_sha256="a" * 64, stores=("intent-boundaries",))
    assert callable(wrapped) and callable(direct)


def test_top2_contrast_renders_the_pinned_pair():
    entry = PERCEPTION_PRESENTATIONS.resolve(pp.TOP2_CONTRAST_PRESENTATION_ID)
    text, reason = entry(
        rank1_intent_id="play_music", rank2_intent_id="play_radio",
        contrast_pairs={
            frozenset({"play_music", "play_radio"}): {
                "activation_sentence": "Says a song or artist name.",
                "exclusion_sentence": "Never names a station or frequency.",
            },
        },
    )
    assert reason is None
    assert "song or artist" in text
    assert "station or frequency" in text


def test_top2_contrast_is_order_independent():
    entry = PERCEPTION_PRESENTATIONS.resolve(pp.TOP2_CONTRAST_PRESENTATION_ID)
    table = {
        frozenset({"a", "b"}): {
            "activation_sentence": "act", "exclusion_sentence": "exc",
        },
    }
    forward = entry(rank1_intent_id="a", rank2_intent_id="b", contrast_pairs=table)
    backward = entry(rank1_intent_id="b", rank2_intent_id="a", contrast_pairs=table)
    assert forward == backward


def test_top2_contrast_renders_nothing_without_fallback_on_missing_pair():
    entry = PERCEPTION_PRESENTATIONS.resolve(pp.TOP2_CONTRAST_PRESENTATION_ID)
    text, reason = entry(
        rank1_intent_id="a", rank2_intent_id="z", contrast_pairs={},
    )
    assert text is None
    assert reason == pp.TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT


def test_top2_contrast_renders_nothing_on_incomplete_row():
    entry = PERCEPTION_PRESENTATIONS.resolve(pp.TOP2_CONTRAST_PRESENTATION_ID)
    text, reason = entry(
        rank1_intent_id="a", rank2_intent_id="b",
        contrast_pairs={frozenset({"a", "b"}): {"activation_sentence": "act"}},
    )
    assert text is None
    assert reason == pp.TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT


def test_top2_contrast_refuses_identical_candidates():
    entry = PERCEPTION_PRESENTATIONS.resolve(pp.TOP2_CONTRAST_PRESENTATION_ID)
    with pytest.raises(ValueError, match="DISTINCT"):
        entry(rank1_intent_id="a", rank2_intent_id="a", contrast_pairs={})


def test_registration_door_refuses_a_bad_entry():
    class _NoVersion:
        id = "bad-entry-v1"

    with pytest.raises(PerceptionPresentationError):
        assert_perception_presentation(_NoVersion(), name="bad-entry-v1")

    def _mismatched_id():
        pass

    _mismatched_id.id = "other-id"
    _mismatched_id.version = "1"
    with pytest.raises(PerceptionPresentationError):
        assert_perception_presentation(_mismatched_id, name="bad-entry-v1")


def test_unknown_presentation_id_refused_by_registry():
    with pytest.raises(CoreError):
        PERCEPTION_PRESENTATIONS.resolve("not-a-real-presentation")
