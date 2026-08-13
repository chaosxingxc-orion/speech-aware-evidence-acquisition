"""Deterministic phonetic/fuzzy candidate matcher (2026-08-12, ``docs/readiness/
2026-08-12-clean-floor-context-verdict.md`` "the decisive pilot": "a
deterministic lexical/phonetic matcher"). Pure functions only -- no model
calls, no I/O beyond what the caller passes in, stdlib-only (``re``) -- the
same "pure, testable seam" discipline :mod:`core.bias_lists` already applies
to its own deterministic text transforms.

This module is NOT wired into any policy yet (deliberately, per the owner
direction that named this deliverable): it exists so ASR-hypothesis terms
can later be matched against a candidate knowledge-base term list before any
such integration is decided. Nothing here reads a config value, calls
``core.base.Registry``, or touches ``core.driver.run_experiment``.

Phonetic algorithm (:func:`phonetic_key`) -- a documented SIMPLIFICATION, not
Double Metaphone, and no new pip dependency: a consonant-skeleton encoder in
the same family as Soundex/Metaphone, built from a small, explicit table of
English digraph/context rules applied in ONE left-to-right scan (longest
rule first, so e.g. "ph" is consumed before a lone "p" ever is), then every
vowel (a/e/i/o/u/y -- y is always treated as a vowel here, never as the
Metaphone-correct "consonant only word-initially before a vowel") is
dropped, and finally adjacent duplicate letters collapse to one (handles
both genuinely doubled consonants, e.g. "ll", and duplicates the rule table
itself creates, e.g. "ck" -> "k" landing next to an existing "k"):

  * ``ph`` -> f; ``ck`` -> k; ``sh``/``ch`` -> x (one shared token for both
    sibilant-ish sounds); ``th``/``wh`` -> t/w; ``qu`` -> k; ``gh`` -> silent
    (dropped) EXCEPT: this is wrong for a word-initial hard-g "gh" (e.g.
    "ghost") -- accepted, documented limitation, no context tracking beyond
    the two-letter window.
  * leading ``kn``/``gn``/``pn``/``wr`` drop their silent first letter.
  * lone ``c``/``g`` before e/i/y soften to s/j, else stay k/g (the classic
    "soft vs hard c/g before a front vowel" English spelling rule).
  * ``x`` -> k+s (the sound it actually makes).
  * anything else alphabetic that survives is kept as itself (English
    consonants map to themselves: b, d, f, j, k, l, m, n, p, q, r, s, t, v,
    w, x done above, z).

Known, deliberate limitations (not silently claimed as covered -- see
``tests/unit/test_retrieval.py`` for the pair this module's OWN test suite
documents as a miss rather than papering over): no handling for
non-English/transliteration-only spelling variation such as "z"/"tz" both
standing in for a /ts/ or /s/ sound (e.g. a "-itzer"/"-icer" surname
variant) -- Double Metaphone's real algorithm carries dozens of such
origin-aware rules this simplification does not attempt; non-ASCII letters
are dropped entirely (English-only, per this module's own scope); no
context beyond a two-letter lookahead, so a rule that depends on a THIRD
letter (Metaphone has several) is never applied here.

Scoring (:func:`score_candidate`) combines two independent [0, 1] similarity
components with fixed, documented weights (:data:`_TEXT_SIMILARITY_WEIGHT` /
:data:`_PHONETIC_SIMILARITY_WEIGHT`, equal 0.5/0.5 -- neither signal is
trusted alone: text similarity alone misses same-sound/different-spelling
pairs like an ASR mis-segmentation ("re proxy lap" for "reproxalap"), and
phonetic similarity alone would let two unrelated short words with the same
few surviving consonants swamp genuinely close spellings): normalized edit
(Levenshtein) similarity of the two terms' :func:`normalize_term` forms, and
normalized edit similarity of their two :func:`phonetic_key` forms. Both
components and their fixed-weight sum are exact, deterministic arithmetic
over Python floats -- no randomness, no external call, same inputs always
produce the same bit-identical output.
"""

from __future__ import annotations

import re

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_ALPHA_RE = re.compile(r"[^a-z]")

# score_candidate's fixed weights (module docstring): MUST sum to 1.0 so a
# combined score never needs anything beyond a defensive float-rounding
# clamp to stay within [0, 1].
_TEXT_SIMILARITY_WEIGHT = 0.5
_PHONETIC_SIMILARITY_WEIGHT = 0.5

# _consonant_skeleton's rule table (longest match first at each scan
# position -- module docstring): two-letter digraphs consumed before any
# lone-letter rule gets a chance to fire on their first character.
_SILENT_LEADING_PAIRS = ("kn", "gn", "pn", "wr")
_DIGRAPHS = {
    "ph": "f",
    "ck": "k",
    "sh": "x",
    "ch": "x",
    "th": "t",
    "wh": "w",
    "qu": "k",
    "gh": "",  # silent (module docstring's documented limitation)
}
_VOWELS = frozenset("aeiouy")


class RetrievalError(RuntimeError):
    """A retrieval-matcher input is malformed, or a fail-closed bound
    (``k``/``min_score`` in :func:`retrieve`) was violated."""


def normalize_term(text: str) -> str:
    """Lowercase, strip punctuation (replaced with a space, never merely
    deleted -- "co-op" normalizes to "co op", not the glued "coop", so word
    boundaries a candidate-matching caller cares about survive), collapse
    runs of whitespace to one space, and trim the ends."""

    if not isinstance(text, str):
        raise RetrievalError(f"normalize_term requires a string, got {type(text).__name__}")
    lowered = text.lower()
    despunctuated = _PUNCTUATION_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", despunctuated).strip()


def _consonant_skeleton(letters: str) -> str:
    """``letters`` is already lowercase ASCII a-z only (no spaces, no
    digits, no punctuation -- :func:`phonetic_key` guarantees this before
    calling in). One left-to-right scan applying :data:`_DIGRAPHS` and the
    context-sensitive c/g/x rules (module docstring), dropping vowels
    on the way, then a second pass collapses adjacent duplicate letters."""

    n = len(letters)
    skeleton_chars: list[str] = []
    i = 0
    if letters[:2] in _SILENT_LEADING_PAIRS:
        i = 1
    while i < n:
        two = letters[i : i + 2]
        replacement = _DIGRAPHS.get(two)
        if replacement is not None:
            if replacement:
                skeleton_chars.append(replacement)
            i += 2
            continue
        ch = letters[i]
        if ch == "c":
            following = letters[i + 1] if i + 1 < n else ""
            skeleton_chars.append("s" if following in "eiy" else "k")
            i += 1
            continue
        if ch == "g":
            following = letters[i + 1] if i + 1 < n else ""
            skeleton_chars.append("j" if following in "eiy" else "g")
            i += 1
            continue
        if ch == "x":
            skeleton_chars.append("k")
            skeleton_chars.append("s")
            i += 1
            continue
        if ch in _VOWELS:
            i += 1
            continue
        skeleton_chars.append(ch)
        i += 1

    collapsed: list[str] = []
    for ch in skeleton_chars:
        if not collapsed or collapsed[-1] != ch:
            collapsed.append(ch)
    return "".join(collapsed)


def phonetic_key(term: str) -> str:
    """Deterministic simplified-Metaphone-style phonetic key (module
    docstring for the exact rule table and its documented limitations).
    Self-contained: extracts its own a-z letters (case-insensitive, every
    non-letter -- including internal whitespace, so a multi-word ASR
    mis-segmentation like "re proxy lap" can still key-match a single glued
    candidate word "reproxalap") from ``term`` rather than requiring a
    caller to pre-normalize it. An input with no ASCII letters at all
    (empty, punctuation/digits/non-English-script only) has no phonetic
    content to encode and returns ``""`` -- never an error, since a
    :class:`score_candidate` caller must be able to score that case as
    "no phonetic similarity" rather than crash."""

    if not isinstance(term, str):
        raise RetrievalError(f"phonetic_key requires a string, got {type(term).__name__}")
    letters = _NON_ALPHA_RE.sub("", term.lower())
    if not letters:
        return ""
    return _consonant_skeleton(letters)


def _levenshtein(a: str, b: str) -> int:
    """Classic O(len(a) * len(b)) edit-distance DP, stdlib-only, two rolling
    rows (never the full matrix) -- the one primitive both similarity
    components in :func:`score_candidate` share."""

    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous_row = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        current_row = [i] + [0] * len(b)
        for j, char_b in enumerate(b, start=1):
            insert_cost = current_row[j - 1] + 1
            delete_cost = previous_row[j] + 1
            substitute_cost = previous_row[j - 1] + (0 if char_a == char_b else 1)
            current_row[j] = min(insert_cost, delete_cost, substitute_cost)
        previous_row = current_row
    return previous_row[-1]


def _normalized_edit_similarity(a: str, b: str) -> float:
    """``1 - edit_distance / max(len(a), len(b))``, i.e. 1.0 for identical
    strings down to 0.0 for two strings sharing no edit-alignable content;
    two EMPTY strings are defined as maximally similar (1.0, never a
    division by zero) -- the only case that arises is both
    :func:`phonetic_key` calls returning ``""`` (module docstring), which
    should not be scored as "similarity 0" (that would penalize two terms
    for both being un-encodable identically to penalizing them for being
    OPPOSITE)."""

    if not a and not b:
        return 1.0
    distance = _levenshtein(a, b)
    return 1.0 - (distance / max(len(a), len(b)))


def score_candidate(query_term: str, candidate_term: str) -> float:
    """Combine normalized-text edit similarity and phonetic-key edit
    similarity into one [0, 1] score with the fixed weights documented at
    the top of this module. Exact, deterministic arithmetic: same two
    strings always produce the same float."""

    if not isinstance(query_term, str) or not isinstance(candidate_term, str):
        raise RetrievalError("score_candidate requires two strings")
    text_similarity = _normalized_edit_similarity(
        normalize_term(query_term), normalize_term(candidate_term)
    )
    phonetic_similarity = _normalized_edit_similarity(
        phonetic_key(query_term), phonetic_key(candidate_term)
    )
    score = (
        _TEXT_SIMILARITY_WEIGHT * text_similarity
        + _PHONETIC_SIMILARITY_WEIGHT * phonetic_similarity
    )
    # Defensive clamp only: both components are already within [0, 1] and
    # the weights sum to 1.0, so `score` is mathematically in [0, 1]; this
    # guards against nothing but float rounding at the boundary.
    return min(1.0, max(0.0, score))


def retrieve(
    query_terms: list[str], candidates: list[str], k: int, min_score: float
) -> list[tuple[str, float]]:
    """Score every candidate against the BEST-matching query term (a
    candidate is retrievable if it is close to ANY one query term, not
    every one), keep those at or above ``min_score``, and return the top
    ``k`` as ``(candidate, score)`` pairs.

    Deterministic tie-breaking: sorted by score descending, then by the
    candidate string ascending (lexicographic) -- so the OUTPUT depends only
    on the multiset of ``candidates`` values, never on their input order
    (shuffling ``candidates`` before calling never changes the result).

    Fail-closed validation, before any scoring work: ``k`` must be a
    positive ``int`` (a bare ``bool`` is rejected too -- ``True``/``False``
    are ``int`` subclasses in Python but were never meant as a count here);
    ``min_score`` must be a real number in ``[0, 1]``; ``query_terms``/
    ``candidates`` must each be a non-empty list of non-empty strings.
    """

    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise RetrievalError(f"k must be a positive integer, got {k!r}")
    if isinstance(min_score, bool) or not isinstance(min_score, (int, float)):
        raise RetrievalError(f"min_score must be a real number, got {min_score!r}")
    min_score_value = float(min_score)
    if not (0.0 <= min_score_value <= 1.0):
        raise RetrievalError(f"min_score must be within [0, 1], got {min_score!r}")
    if not isinstance(query_terms, list) or not query_terms or not all(
        isinstance(term, str) and term for term in query_terms
    ):
        raise RetrievalError("query_terms must be a non-empty list of non-empty strings")
    if not isinstance(candidates, list) or not candidates or not all(
        isinstance(candidate, str) and candidate for candidate in candidates
    ):
        raise RetrievalError("candidates must be a non-empty list of non-empty strings")

    scored: list[tuple[str, float]] = []
    for candidate in candidates:
        best_score = max(score_candidate(query, candidate) for query in query_terms)
        if best_score >= min_score_value:
            scored.append((candidate, best_score))
    scored.sort(key=lambda pair: (-pair[1], pair[0]))
    return scored[:k]
