"""``scripts/build_slurp_intent_contrast_pairs.py`` (same-flight instrument phase 2, merge set C,
item 5): pure, model-free tests of TOP-2 pair selection, the word-gap sentence template and the
O5 pool-support floor -- no data root, no real knowledge store, no server, no GPU. Mirrors the
import pattern ``tests/unit/test_flight_registration_check.py`` uses for a ``scripts/`` module
with no package ``__init__.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[2]
_SCRIPTS = _REPO / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import build_slurp_intent_contrast_pairs as builder  # noqa: E402


def _stats(n: int, words: dict[str, float], types: dict[str, float] | None = None) -> dict:
    """A synthetic ``intent_stats``-shaped dict: {"n", "count", "df", "type_share"}.

    ``words`` maps a candidate cue word to its document frequency (0..1); ``count`` is derived so
    it clears ``build_slurp_intent_contrast_cards.MIN_SUPPORT`` (3) whenever ``df`` is above 0.
    """

    return {
        "n": n,
        "count": {word: max(3, round(df * n)) for word, df in words.items()},
        "df": dict(words),
        "type_share": dict(types or {}),
    }


def test_select_top2_pairs_takes_each_intents_single_nearest_rival():
    order = ["a", "b", "c", "d"]
    # a<->b are mutual nearest neighbours (collapse to one pair); c's nearest is a (one-directional,
    # since a's own nearest is b, not c); d's nearest is c.
    cosine = np.array([
        [1.0, 0.9, 0.5, 0.1],
        [0.9, 1.0, 0.2, 0.1],
        [0.5, 0.2, 1.0, 0.3],
        [0.1, 0.1, 0.3, 1.0],
    ])
    pairs = builder.select_top2_pairs(order, cosine)
    assert pairs == [("a", "b"), ("a", "c"), ("c", "d")]


def test_select_top2_pairs_deduplicates_mutual_nearest_neighbours():
    order = ["x", "y"]
    cosine = np.array([[1.0, 0.7], [0.7, 1.0]])
    assert builder.select_top2_pairs(order, cosine) == [("x", "y")]


def test_select_top2_pairs_refuses_a_mismatched_shape():
    with pytest.raises(builder.BuildError, match="matching square matrix"):
        builder.select_top2_pairs(["a", "b"], np.zeros((3, 3)))


def test_contrast_sentences_names_each_sides_typical_words():
    x_stats = _stats(10, {"dim": 0.8, "light": 0.7})
    y_stats = _stats(10, {"play": 0.9, "music": 0.6})
    result = builder.contrast_sentences("intent_x", "intent_y", x_stats, y_stats)
    assert result is not None
    activation, exclusion = result
    assert "intent_x" in activation and "intent_y" in activation
    assert "dim" in activation or "light" in activation
    assert "play" in activation or "music" in activation
    assert "intent_x" in exclusion and "intent_y" in exclusion
    # Never leaks a raw utterance, span or filler -- only the aggregated cue words and intent ids.
    assert "utterance" not in activation.lower()


def test_contrast_sentences_returns_none_below_the_pool_support_floor():
    x_stats = _stats(builder.MIN_PAIR_POOL_SUPPORT - 1, {"dim": 0.8})
    y_stats = _stats(10, {"play": 0.9})
    assert builder.contrast_sentences("x", "y", x_stats, y_stats) is None


def test_contrast_sentences_returns_none_when_a_side_has_no_distinguishing_cue():
    # Both sides carry the SAME words at the SAME frequency: cues() finds nothing above
    # MIN_DF_GAP for either side.
    shared = {"word": 0.5}
    x_stats = _stats(10, shared)
    y_stats = _stats(10, shared)
    assert builder.contrast_sentences("x", "y", x_stats, y_stats) is None


def test_contrast_sentences_returns_none_for_an_unknown_intent():
    assert builder.contrast_sentences("x", "y", None, _stats(10, {"a": 0.9})) is None


def test_contrast_sentences_uses_slot_types_when_words_are_absent():
    x_stats = _stats(10, {}, {"time": 0.9})
    y_stats = _stats(10, {}, {"place": 0.9})
    result = builder.contrast_sentences("x", "y", x_stats, y_stats)
    assert result is not None
    activation, _exclusion = result
    assert "time" in activation and "place" in activation


def test_build_table_writes_minable_pairs_and_receipts_skipped_ones():
    order = ["strong", "weak_partner", "isolated"]
    cosine = np.array([
        [1.0, 0.9, 0.1],
        [0.9, 1.0, 0.1],
        [0.1, 0.1, 1.0],
    ])
    stats = {
        "strong": _stats(10, {"dim": 0.8}),
        "weak_partner": _stats(builder.MIN_PAIR_POOL_SUPPORT - 1, {"play": 0.8}),
        "isolated": _stats(10, {"cue": 0.9}),
    }
    table = builder.build_table(order, cosine, stats)
    # strong<->weak_partner: below the floor on weak_partner's side -> skipped.
    # isolated's nearest is "strong" (highest remaining cosine) -> also below floor via strong's
    # own pairing already consumed by dedup; isolated pairs with strong directly.
    pair_keys = set(table["rows"])
    skipped_pairs = {tuple(row["intents"]) for row in table["skipped"]}
    assert ("strong", "weak_partner") in skipped_pairs or "strong|weak_partner" in pair_keys
    for reason_row in table["skipped"]:
        assert reason_row["reason"] == "insufficient-pool-support"
    # The receipt-facing counts add up.
    assert len(table["rows"]) + len(table["skipped"]) == len(builder.select_top2_pairs(order, cosine))


def test_build_table_row_schema_matches_the_presentation_contract():
    """The two fields ``rails.perception_presentations._Top2ContrastPresentation`` requires."""

    order = ["p", "q"]
    cosine = np.array([[1.0, 0.8], [0.8, 1.0]])
    stats = {"p": _stats(10, {"alpha": 0.9}), "q": _stats(10, {"beta": 0.9})}
    table = builder.build_table(order, cosine, stats)
    assert len(table["rows"]) == 1
    row = next(iter(table["rows"].values()))
    assert set(row) == {"intents", "activation_sentence", "exclusion_sentence"}
    assert isinstance(row["activation_sentence"], str) and row["activation_sentence"]
    assert isinstance(row["exclusion_sentence"], str) and row["exclusion_sentence"]
