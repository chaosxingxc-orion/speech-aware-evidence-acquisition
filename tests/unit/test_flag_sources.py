"""Roster-band flag source (core.flag_sources): the weighted grapheme
distance function, its band rule, and the top-K non-overlapping span
selection the obs-replay-loop policy's ``replay_flag_source="roster-band"``
mode consumes. Pure functions only -- no policy integration, no model, no
filesystem."""

import pytest

from speech_aware_evidence_acquisition.core.flag_sources import (
    BAND_HIGH,
    BAND_LOW,
    STOPWORDS,
    FlagSourceError,
    band_centrality,
    roster_band_flags,
    weighted_grapheme_distance,
)


class TestWeightedGraphemeDistance:
    def test_identical_strings_are_zero(self):
        assert weighted_grapheme_distance("acme", "acme") == 0.0

    def test_vowel_swap_costs_half(self):
        # "calp"/"culp": one vowel substitution (a<->u) over length-4 strings
        # -- the flag-eval harness's own documented example (band_centrality
        # docstring: "calp/culp at 0.125").
        assert weighted_grapheme_distance("calp", "culp") == pytest.approx(0.125)

    def test_voiced_unvoiced_pair_costs_point_six(self):
        # "pat"/"bat": single b/p substitution over length-3 strings.
        assert weighted_grapheme_distance("pat", "bat") == pytest.approx(0.6 / 3)

    def test_unrelated_substitution_costs_one(self):
        # "cat"/"cax": x is neither a vowel nor voiced/unvoiced-paired with t.
        assert weighted_grapheme_distance("cat", "cax") == pytest.approx(1.0 / 3)

    def test_empty_strings(self):
        assert weighted_grapheme_distance("", "") == 0.0
        assert weighted_grapheme_distance("", "a") == 1.0
        assert weighted_grapheme_distance("a", "") == 1.0

    def test_always_within_unit_interval(self):
        for a, b in [("aldera", "aldeyra"), ("x", "supercalifragilistic"), ("same", "same")]:
            d = weighted_grapheme_distance(a, b)
            assert 0.0 <= d <= 1.0


class TestBandCentrality:
    def test_one_at_low_end_zero_at_high_end(self):
        assert band_centrality(BAND_LOW) == pytest.approx(1.0)
        assert band_centrality(BAND_HIGH) == pytest.approx(0.0)

    def test_linear_midpoint(self):
        mid = (BAND_LOW + BAND_HIGH) / 2.0
        assert band_centrality(mid) == pytest.approx(0.5)

    def test_clamped_outside_band(self):
        assert band_centrality(0.0) == 1.0
        assert band_centrality(1.0) == 0.0


# ---------------------------------------------------------------------------
# (a) a deliberately corrupted draft word near a candidate is flagged; a
#     function word is not.
# ---------------------------------------------------------------------------


class TestRosterBandFlagsCorruptedWord:
    def test_flags_the_corrupted_entity_word_not_function_words(self):
        words = "we spoke with Aldera about the pipeline today".split()
        flags = roster_band_flags(words, ["Aldeyra"], max_spans=5)
        assert len(flags) == 1
        flag = flags[0]
        assert words[flag.span[0] : flag.span[1]] == ["Aldera"]
        assert flag.candidate == "aldeyra"
        assert BAND_LOW <= flag.distance <= BAND_HIGH
        assert flag.score > 0.0

    def test_stopwords_never_anchor_a_flagged_span(self):
        # Every stopword in this draft is closer (in the weighted-distance
        # sense) to at least one candidate than BAND_HIGH would forbid for
        # some short candidate, but STOPWORDS excludes them from ever being
        # a query position regardless.
        words = "the a an and or but".split()
        assert all(w.lower() in STOPWORDS for w in words)
        flags = roster_band_flags(words, ["thee", "ans", "ant"], max_spans=5)
        assert flags == []

    def test_two_word_window_can_match_a_multi_word_candidate(self):
        words = "please welcome Jon Smithe to the stage".split()
        flags = roster_band_flags(words, ["John Smith"], max_spans=5)
        assert len(flags) == 1
        assert words[flags[0].span[0] : flags[0].span[1]] == ["Jon", "Smithe"]
        assert flags[0].candidate == "john smith"


# ---------------------------------------------------------------------------
# (b) an already-exact match (distance < 0.05) is never flagged.
# ---------------------------------------------------------------------------


class TestRosterBandAlreadyMatches:
    def test_exact_match_is_not_flagged(self):
        words = "the company is called Aldeyra Therapeutics".split()
        flags = roster_band_flags(words, ["Aldeyra"], max_spans=5)
        assert flags == []

    def test_case_and_punctuation_only_difference_is_not_flagged(self):
        # normalize_term lowercases and strips punctuation -- "Aldeyra," and
        # "aldeyra" normalize to the same form, distance 0.0 < BAND_LOW.
        words = "we discussed Aldeyra, at length".split()
        flags = roster_band_flags(words, ["aldeyra"], max_spans=5)
        assert flags == []

    def test_unrelated_word_beyond_the_high_band_is_not_flagged(self):
        words = "the weather today is sunny".split()
        flags = roster_band_flags(words, ["Aldeyra"], max_spans=5)
        assert flags == []


# ---------------------------------------------------------------------------
# (c) the K cap is respected.
# ---------------------------------------------------------------------------


class TestRosterBandMaxSpansCap:
    _WORDS = "we spoke with Aldera and Mcmullen and Frentz executives today".split()
    _CANDIDATES = ["Aldeyra", "McMullin", "Frenz"]

    def test_more_candidates_than_the_cap_are_truncated(self):
        flags = roster_band_flags(self._WORDS, self._CANDIDATES, max_spans=1)
        assert len(flags) == 1

    def test_cap_keeps_the_highest_scoring_spans(self):
        capped = roster_band_flags(self._WORDS, self._CANDIDATES, max_spans=2)
        uncapped = roster_band_flags(self._WORDS, self._CANDIDATES, max_spans=10)
        assert len(capped) == 2
        assert len(uncapped) == 3
        top_two_by_score = sorted(uncapped, key=lambda f: -f.score)[:2]
        assert {f.span for f in capped} == {f.span for f in top_two_by_score}

    def test_returned_in_ascending_span_start_order(self):
        flags = roster_band_flags(self._WORDS, self._CANDIDATES, max_spans=10)
        starts = [f.span[0] for f in flags]
        assert starts == sorted(starts)

    def test_selected_spans_never_overlap(self):
        flags = roster_band_flags(self._WORDS, self._CANDIDATES, max_spans=10)
        for i, a in enumerate(flags):
            for b in flags[i + 1 :]:
                assert a.span[1] <= b.span[0] or b.span[1] <= a.span[0]

    @pytest.mark.parametrize("bad", [0, -1, 1.5, True, False, "2"])
    def test_refuses_a_non_positive_or_non_int_max_spans(self, bad):
        with pytest.raises(FlagSourceError, match="max_spans"):
            roster_band_flags(["Aldera"], ["Aldeyra"], max_spans=bad)


class TestRosterBandEmptyInputs:
    def test_empty_words_returns_empty(self):
        assert roster_band_flags([], ["Aldeyra"], max_spans=2) == []

    def test_empty_candidates_returns_empty(self):
        assert roster_band_flags(["Aldera"], [], max_spans=2) == []
