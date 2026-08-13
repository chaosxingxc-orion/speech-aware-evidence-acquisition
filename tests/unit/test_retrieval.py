"""core.retrieval: pure deterministic phonetic/fuzzy candidate matcher.

No model, no I/O, no registry wiring -- see the module's own docstring for
why (not yet integrated into any policy). These tests pin: determinism,
documented phonetic hits on ASR-confusion-style pairs, one pair the
module's own simplified algorithm is DOCUMENTED to miss (never silently
papered over), fail-closed validation, and deterministic tie-breaking.
"""

import random

import pytest

from speech_aware_evidence_acquisition.core.retrieval import (
    RetrievalError,
    normalize_term,
    phonetic_key,
    retrieve,
    score_candidate,
)


# ---------------------------------------------------------------------------
# normalize_term
# ---------------------------------------------------------------------------


def test_normalize_term_lowercases_strips_punctuation_and_collapses_whitespace():
    assert normalize_term("  Hello, World!  ") == "hello world"
    assert normalize_term("co-op") == "co op"
    assert normalize_term("A.B.C.") == "a b c"
    assert normalize_term("Bret   Jordan") == "bret jordan"


def test_normalize_term_is_idempotent():
    once = normalize_term("  Brett   PONTON, Jr.  ")
    assert normalize_term(once) == once


def test_normalize_term_rejects_non_string():
    with pytest.raises(RetrievalError, match="requires a string"):
        normalize_term(123)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# phonetic_key -- documented simplified-Metaphone-style consonant skeleton.
# ---------------------------------------------------------------------------


def test_phonetic_key_deterministic_same_input_same_output():
    assert phonetic_key("Bistritzer") == phonetic_key("Bistritzer")
    assert phonetic_key("Bistritzer") == phonetic_key("bistritzer")  # case-insensitive


def test_phonetic_key_empty_for_no_letters():
    assert phonetic_key("") == ""
    assert phonetic_key("1234 !?") == ""


def test_phonetic_key_rejects_non_string():
    with pytest.raises(RetrievalError, match="requires a string"):
        phonetic_key(None)  # type: ignore[arg-type]


def test_phonetic_key_strips_internal_whitespace_so_split_words_can_still_match():
    """The ASR-mis-segmentation case this module exists for: three
    space-separated tokens ASR emitted for what should have been one glued
    term key identically to the correctly-spelled single word."""

    assert phonetic_key("re proxy lap") == phonetic_key("reproxalap") == "rprkslp"


@pytest.mark.parametrize(
    ("term_a", "term_b", "expected_key"),
    [
        # Classic English name/spelling homophone pairs -- documented "ph",
        # "th", and soft/hard "c" rules (module docstring) all fire here.
        ("smith", "smyth", "smt"),
        ("catherine", "katherine", "ktrn"),
        ("philip", "filip", "flp"),
    ],
)
def test_phonetic_key_catches_common_homophone_pairs(term_a, term_b, expected_key):
    assert phonetic_key(term_a) == phonetic_key(term_b) == expected_key


def test_phonetic_key_documented_limitation_transliteration_variant():
    """DOCUMENTED MISS (module docstring's "known, deliberate limitations"):
    a "-icer"/"-itzer" surname variant is a genuinely close ASR-confusion
    pair (both realistically render a similar sibilant sound), but this
    simplified algorithm has no origin-aware "z"/"tz" rule the way real
    Double Metaphone does, so the two keys do NOT match. Asserted as a MISS
    on purpose -- see test_score_candidate_still_ranks_the_transliteration_
    variant_above_unrelated_terms below for what the combined scorer still
    recovers via plain text edit-similarity despite this phonetic gap."""

    assert phonetic_key("bistricer") == "bstrsr"
    assert phonetic_key("bistritzer") == "bstrtzr"
    assert phonetic_key("bistricer") != phonetic_key("bistritzer")


# ---------------------------------------------------------------------------
# score_candidate
# ---------------------------------------------------------------------------


def test_score_candidate_is_deterministic():
    first = score_candidate("Bret Jordan", "Brett Jordan")
    second = score_candidate("Bret Jordan", "Brett Jordan")
    assert first == second


def test_score_candidate_identical_terms_score_one():
    assert score_candidate("Goldman Sachs", "goldman   sachs") == 1.0


def test_score_candidate_rejects_non_strings():
    with pytest.raises(RetrievalError, match="requires two strings"):
        score_candidate("x", 1)  # type: ignore[arg-type]


def test_score_candidate_catches_the_asr_mis_segmentation_pair():
    """"re proxy lap" (three ASR tokens) vs "reproxalap" (the correctly
    spelled single term): a phonetic hit lifts a text-dissimilar pair to a
    high combined score."""

    score = score_candidate("re proxy lap", "reproxalap")
    assert phonetic_key("re proxy lap") == phonetic_key("reproxalap")
    assert score == pytest.approx(0.875, abs=1e-9)
    assert score >= 0.7


@pytest.mark.parametrize(
    ("term_a", "term_b", "expected_score"),
    [
        ("smith", "smyth", 0.9),
        ("catherine", "katherine", 0.9444444444444444),
        ("philip", "filip", 0.8333333333333333),
    ],
)
def test_score_candidate_scores_homophone_pairs_highly(term_a, term_b, expected_score):
    assert score_candidate(term_a, term_b) == pytest.approx(expected_score, abs=1e-9)


def test_score_candidate_still_ranks_the_transliteration_variant_above_unrelated_terms():
    """The documented phonetic MISS (bistricer/bistritzer) still scores well
    above two genuinely unrelated words, because normalized edit similarity
    (the other half of the combined score) is not fooled by it -- the
    phonetic component alone is not the whole story, exactly the point of
    combining the two signals."""

    close_score = score_candidate("bistricer", "bistritzer")
    unrelated_score = score_candidate("apple", "orange")
    assert phonetic_key("bistricer") != phonetic_key("bistritzer")  # the documented miss
    assert close_score == pytest.approx(0.7571428571428571, abs=1e-9)
    assert unrelated_score == pytest.approx(0.08333333333333333, abs=1e-9)
    assert close_score > unrelated_score


# ---------------------------------------------------------------------------
# retrieve
# ---------------------------------------------------------------------------

_ROSTER = ["Bret Jordan", "Brett Ponton", "Brian D'Ambrosia", "Rick Nelson", "IBM"]


def test_retrieve_top_k_and_min_score_threshold():
    results = retrieve(["bret jordan"], _ROSTER, k=3, min_score=0.3)
    assert results == [
        ("Bret Jordan", 1.0),
        ("Brett Ponton", pytest.approx(0.5773809523809523, abs=1e-9)),
    ]


def test_retrieve_k_caps_the_result_even_when_more_candidates_clear_the_threshold():
    results = retrieve(["bret jordan"], _ROSTER, k=1, min_score=0.3)
    assert results == [("Bret Jordan", 1.0)]


def test_retrieve_empty_when_nothing_clears_min_score():
    assert retrieve(["zzzzzzzz"], _ROSTER, k=5, min_score=0.99) == []


def test_retrieve_is_deterministic():
    first = retrieve(["bret jordan"], _ROSTER, k=3, min_score=0.3)
    second = retrieve(["bret jordan"], _ROSTER, k=3, min_score=0.3)
    assert first == second


def test_retrieve_is_order_independent_over_candidate_input_order():
    baseline = retrieve(["bret jordan"], _ROSTER, k=5, min_score=0.0)
    shuffled = list(_ROSTER)
    random.Random(1234).shuffle(shuffled)
    assert shuffled != _ROSTER  # the shuffle actually changed the input order
    reshuffled_result = retrieve(["bret jordan"], shuffled, k=5, min_score=0.0)
    assert reshuffled_result == baseline


def test_retrieve_deterministic_tie_breaking_is_lexicographic_on_the_candidate_string():
    """Two candidates that normalize/phonetic-key identically to the query
    tie at score 1.0; the tie is broken by the candidate STRING itself
    (never by input position) -- "Apple" sorts before "apple" (ASCII 'A' <
    'a'), independent of which one was listed first."""

    tied_first = retrieve(["apple"], ["apple", "Apple"], k=2, min_score=0.0)
    tied_second = retrieve(["apple"], ["Apple", "apple"], k=2, min_score=0.0)
    assert tied_first == tied_second == [("Apple", 1.0), ("apple", 1.0)]


def test_retrieve_uses_the_best_scoring_query_term_per_candidate():
    results = retrieve(["zzzzzzzz", "bret jordan"], _ROSTER, k=1, min_score=0.3)
    assert results == [("Bret Jordan", 1.0)]


@pytest.mark.parametrize("bad_k", [0, -1, 1.5, True, "3"])
def test_retrieve_fails_closed_on_an_invalid_k(bad_k):
    with pytest.raises(RetrievalError, match="k must be a positive integer"):
        retrieve(["x"], ["y"], k=bad_k, min_score=0.5)


@pytest.mark.parametrize("bad_min_score", [-0.1, 1.1, "0.5", None])
def test_retrieve_fails_closed_on_an_invalid_min_score(bad_min_score):
    with pytest.raises(RetrievalError, match="min_score"):
        retrieve(["x"], ["y"], k=1, min_score=bad_min_score)


@pytest.mark.parametrize("bad_query_terms", [[], "not-a-list", [""], [1], None])
def test_retrieve_fails_closed_on_invalid_query_terms(bad_query_terms):
    with pytest.raises(RetrievalError, match="query_terms"):
        retrieve(bad_query_terms, ["y"], k=1, min_score=0.5)


@pytest.mark.parametrize("bad_candidates", [[], "not-a-list", [""], [1], None])
def test_retrieve_fails_closed_on_invalid_candidates(bad_candidates):
    with pytest.raises(RetrievalError, match="candidates"):
        retrieve(["x"], bad_candidates, k=1, min_score=0.5)
