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


# ---------------------------------------------------------------------------
# --pair-scope (O7): "nearest-rival" stays byte-reproducible; "all-pairs"
# considers every unordered pair, roster-agnostic.
# ---------------------------------------------------------------------------


def test_select_all_pairs_is_every_unordered_pair_on_a_tiny_synthetic_pool():
    order = ["a", "b", "c", "d", "e"]
    import math

    pairs = builder.select_all_pairs(order)
    assert len(pairs) == math.comb(len(order), 2)
    # Every pair is a sorted 2-tuple of distinct, known intents; no duplicates.
    assert len(set(pairs)) == len(pairs)
    for x_id, y_id in pairs:
        assert x_id != y_id
        assert x_id < y_id
        assert x_id in order and y_id in order
    # The whole space, not a per-intent nearest-rival subset: (a, e) is far apart yet still
    # considered, unlike select_top2_pairs over a cosine matrix that would never pick it.
    assert ("a", "e") in pairs


def test_select_pairs_dispatches_on_pair_scope():
    order = ["a", "b", "c"]
    cosine = np.array([[1.0, 0.9, 0.1], [0.9, 1.0, 0.1], [0.1, 0.1, 1.0]])
    assert builder.select_pairs(order, cosine, "nearest-rival") == builder.select_top2_pairs(order, cosine)
    assert builder.select_pairs(order, cosine, "all-pairs") == builder.select_all_pairs(order)
    with pytest.raises(builder.BuildError, match="unknown --pair-scope"):
        builder.select_pairs(order, cosine, "bogus-scope")


def test_build_table_default_pair_scope_is_unchanged_nearest_rival():
    """The default (no ``pair_scope`` kwarg) is byte-identical to explicit ``"nearest-rival"``,
    and to this function's behaviour before ``--pair-scope`` existed -- the v1 reproducibility
    guarantee."""

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
    default_table = builder.build_table(order, cosine, stats)
    explicit_table = builder.build_table(order, cosine, stats, pair_scope="nearest-rival")
    assert default_table == explicit_table


def test_build_table_all_pairs_considers_c_n_choose_2_pairs_on_a_tiny_synthetic_pool():
    import math

    order = ["strong", "weak_partner", "isolated", "another"]
    cosine = np.eye(len(order))  # unused by all-pairs, but build_table still takes it
    stats = {
        "strong": _stats(10, {"dim": 0.8}),
        "weak_partner": _stats(builder.MIN_PAIR_POOL_SUPPORT - 1, {"play": 0.8}),
        "isolated": _stats(10, {"cue": 0.9}),
        "another": _stats(10, {"word": 0.9}),
    }
    table = builder.build_table(order, cosine, stats, pair_scope="all-pairs")
    pairs_considered = len(table["rows"]) + len(table["skipped"])
    assert pairs_considered == math.comb(len(order), 2)
    # weak_partner is below the floor on every one of its pairs -> skipped every time.
    skipped_pairs = {tuple(row["intents"]) for row in table["skipped"]}
    assert all("weak_partner" in pair for pair in skipped_pairs)
    assert len(skipped_pairs) == len(order) - 1  # weak_partner paired with each of the other three
    for reason_row in table["skipped"]:
        assert reason_row["reason"] == "insufficient-pool-support"
