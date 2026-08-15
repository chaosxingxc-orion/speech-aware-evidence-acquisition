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
        # D7 delivery-gate defect fix (word-granularity decomposition): both
        # decomposed words of "John Smith" -- "john" and "smith" -- are now
        # independently in-band against "Jon"/"Smithe", and each scores
        # HIGHER alone than the combined 2-word window against the "john
        # smith" bigram (a window's score is capped by the MIN of its two
        # words' own rarity, which the decomposition case above shows can
        # never exceed the stronger half's own single-word score) -- so the
        # two separate, non-overlapping word-level flags win the greedy
        # selection over the one window flag they would have collapsed into
        # pre-fix. Both still report the ORIGINAL full candidate term.
        words = "please welcome Jon Smithe to the stage".split()
        flags = roster_band_flags(words, ["John Smith"], max_spans=5)
        assert len(flags) == 2
        assert words[flags[0].span[0] : flags[0].span[1]] == ["Jon"]
        assert words[flags[1].span[0] : flags[1].span[1]] == ["Smithe"]
        assert flags[0].candidate == "john smith"
        assert flags[1].candidate == "john smith"
        assert flags[0].matched_form == "john"
        assert flags[1].matched_form == "smith"

    def test_bigram_target_flags_a_window_when_neither_word_matches_alone(self):
        # D7 fix: a genuine bigram-target match -- "Northampton" is an EXACT
        # match to its own decomposed word (distance 0, below BAND_LOW,
        # never flags alone) and "Zzzzz" is unrelated to "silva" (out of
        # BAND_HIGH alone), so NEITHER word independently flags; but the
        # long exact-match prefix dilutes the SAME raw edit cost across a
        # longer combined length, pulling the 2-word window's distance
        # against the "northampton silva" bigram back into band -- proving
        # bigram-target matching (not just word-target matching) fires.
        words = "we welcomed Northampton Zzzzz to the podium".split()
        flags = roster_band_flags(words, ["Northampton Silva"], max_spans=5)
        assert len(flags) == 1
        flag = flags[0]
        assert words[flag.span[0] : flag.span[1]] == ["Northampton", "Zzzzz"]
        assert flag.candidate == "northampton silva"
        assert flag.matched_form == "northampton silva"
        assert BAND_LOW <= flag.distance <= BAND_HIGH

    def test_full_multi_word_candidate_still_flags_via_decomposition(self):
        # D7 delivery-gate defect fix: the SAME Aldera->Aldeyra draft as
        # test_flags_the_corrupted_entity_word_not_function_words above, but
        # the candidate is now the FULL roster string a real evidence pack
        # would carry ("Aldeyra Therapeutics Inc") rather than a bare single
        # word -- pre-fix, matching the whole 24-character string against a
        # 6-character draft word was impossible by length alone (0
        # end-to-end acceptances, docs/exposure-ledger.md's SAEA-D7-delivery
        # consumption note); decomposition recovers the match via the
        # candidate's own "aldeyra" word.
        words = "we spoke with Aldera about the pipeline today".split()
        flags = roster_band_flags(words, ["Aldeyra Therapeutics Inc"], max_spans=5)
        assert len(flags) == 1
        flag = flags[0]
        assert words[flag.span[0] : flag.span[1]] == ["Aldera"]
        # candidate is the ORIGINAL full term (normalized), never the
        # decomposed word alone.
        assert flag.candidate == "aldeyra therapeutics inc"
        assert flag.matched_form == "aldeyra"
        assert BAND_LOW <= flag.distance <= BAND_HIGH

    def test_decomposed_word_lets_a_corrupted_surname_match_a_full_name_candidate(self):
        # D7 fix: "Micheal Frenz" (a two-word person-name candidate, typo
        # preserved exactly as production p1-metadata rosters carry it,
        # docs/exposure-ledger.md's SAEA-P1R-metadata10 consumption note)
        # decomposes to ["micheal", "frenz"]; a corrupted draft form of just
        # the surname ("Frentz") band-matches the decomposed "frenz" word --
        # impossible pre-fix, where the whole 13-character "micheal frenz"
        # string was the only match target.
        words = "we spoke with Frentz about the deal today".split()
        flags = roster_band_flags(words, ["Micheal Frenz"], max_spans=5)
        assert len(flags) == 1
        flag = flags[0]
        assert words[flag.span[0] : flag.span[1]] == ["Frentz"]
        assert flag.candidate == "micheal frenz"
        assert flag.matched_form == "frenz"
        assert BAND_LOW <= flag.distance <= BAND_HIGH

    def test_stop_forms_never_become_match_targets(self):
        # D7 fix: "inc" clears MIN_CANDIDATE_WORD_LENGTH (3 chars) so only
        # the closed STOP_FORMS list keeps it out of the decomposed target
        # set -- "Ink" is in-band of "inc" (distance 1/3) but must never
        # anchor a flag once "inc" is correctly stripped.
        words = "we discussed Ink pricing today".split()
        flags = roster_band_flags(words, ["Aldeyra Therapeutics Inc"], max_spans=5)
        assert flags == []


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
