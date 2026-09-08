"""Roster-band flag source (D5 rectification, ``docs/readiness/
2026-08-15-rectification-plan.md``): the ``reproduction.replay_loop``
obs-replay-loop policy's config-selectable alternative to logprob-based
SCORE-stage flagging, offline-validated at proper-name P@1=0.252 against the
production logprob flags' 0/17 entity hits (``docs/readiness/
2026-08-14-p1-ceiling-verdict.md``, finding 1: "Flag targeting misses
entities 17/17 ... zero overlap with the real entity errors the oracle
candidates answer").

Ports the DISTANCE FUNCTION and BAND RULE from the flag-eval harness's S1
method (``common_text.py``/``methods.py``, offline scratchpad code, never
committed to this repo) FAITHFULLY -- same weighted grapheme edit distance,
same band, same df-rarity x name-likeness-prior score -- with these FROZEN
parameters:

- band ``[0.05, 0.45]``, weighted toward the LOW end: 1.0 at distance 0.05
  (a near-exact mismatch to a known form -- the strongest corruption
  signal, e.g. "calp"/"culp" at 0.125) linearly down to 0.0 at distance
  0.45; distance < 0.05 means the draft word already matches a candidate
  (correct, not an error -- never flagged); > 0.45 is unrelated.
- weighted grapheme distance: vowel<->vowel substitution 0.5, voiced
  /unvoiced pair (b/p, d/t, g/k, v/f) substitution 0.6, any other
  substitution 1.0, insertion/deletion 1.0, normalized by
  ``max(len(a), len(b))``. A character-histogram lower bound skips the
  O(len_a * len_b) DP for any candidate that provably cannot land in-band
  (exact, never causes a real in-band match to be missed).
- rarity = ``1/sqrt(count)`` in THIS SLICE's own word-frequency table by
  default, times a name-likeness prior: capitalized mid-sentence x1.0 else
  x0.3; word length >= 6 x1.0 else x0.5. :func:`roster_band_flags` takes an
  OPTIONAL ``df`` mapping (D7C delivery-gate fix, ``docs/exposure-ledger.md``'s
  SAEA-D7C-delivery consumption note, 2026-08-15) -- the whole-SAMPLE pass-1
  draft's own word counts, across every slice, not just this one -- and uses
  ``1/sqrt(df[word])`` (clamped ``df >= 1``) in place of the slice-local
  count whenever supplied: a common word recurring dozens of times across a
  call but only once or twice within any single slice (e.g.
  "operations"/"operating" in an earnings call) otherwise reads as locally
  rare and out-competes a genuinely hapax name for the K budget. ``df=None``
  (the default) keeps the slice-local behaviour above byte-identical.
- score = ``band_centrality(distance) * rarity``; 1-2 word spans (single
  draft words and adjacent 2-word windows); closed-class stopwords are
  excluded from query positions (none can plausibly be a corrupted entity
  name under this cost model).

Deliberately narrower CANDIDATE/TARGET set than the offline harness's own S1
gate (that gate = roster + lexicon + this-call's-own capitalized/rare draft
tokens -- machinery this study repo does not carry at replay time): here the
candidate set is exactly what ``reproduction.replay_loop`` already resolves
for RETRIEVE -- the arm's own evidence candidate terms
(``core.candidate_materializer.pack_candidates``) plus exemplar-bank labels
when this run resolved a bank (``reproduction.replay_loop`` module
docstring's RETRIEVE section) -- never a self-referential draft-derived
gate addition (see :func:`roster_band_flags`'s own caller,
``reproduction.replay_loop._roster_band_candidate_terms``). Every
rarity/frequency table is built from THIS SLICE's own draft words: the
SCORE stage's unit of work is one pass-1 slice, not a whole call (unlike
the offline per-call harness).

Text normalization reuses ``core.retrieval.normalize_term`` (lowercase,
strip punctuation, collapse whitespace) rather than porting a second,
independently-drifting normalizer: the SAME normalized form this module
compares words against is what ``reproduction.replay_loop``'s RETRIEVE
correction filter and ACCEPT's unchanged-text check already use.

Pure functions only: no model call, no I/O, no config read -- same
discipline as ``core.retrieval``/``core.replay_signals``.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

from .retrieval import normalize_term

BAND_LOW = 0.05
BAND_HIGH = 0.45
MIN_RARE_WORD_LENGTH = 6

# Word-granularity decomposition (D7 delivery-gate defect fix, ``docs/
# exposure-ledger.md``'s SAEA-D7-delivery consumption note, 2026-08-15): a
# candidate word shorter than this never anchors a decomposed match target
# on its own (mirrors STOPWORDS' spirit for the CANDIDATE side of a match,
# not just the draft side) -- ``_STOP_FORMS`` below additionally excludes a
# small closed list of honorific/corporate-suffix forms that would otherwise
# clear this length bar (e.g. "Inc", "Ltd").
MIN_CANDIDATE_WORD_LENGTH = 3

# Closed-class honorific/corporate-suffix forms (D7 fix): stripped out of a
# candidate term's decomposition below so, e.g., "Dr. Todd Brady" yields
# match targets ``["todd", "brady"]`` (plus the bigram "todd brady"), never
# "dr" -- ``normalize_term`` already turns "Dr." into "dr" before this set is
# checked.
_STOP_FORMS = frozenset(
    """
    dr mr mrs ms prof jr sr inc ltd co corp llc
    """.split()
)

_VOWELS = frozenset("aeiou")
_VOICED_PAIRS = frozenset(
    frozenset(pair) for pair in (("b", "p"), ("d", "t"), ("g", "k"), ("v", "f"))
)

# Closed-class function words (ported verbatim from the flag-eval harness's
# common_text.py STOPWORDS, module docstring): none can plausibly be a
# corrupted entity name under this cost model, so a query position never
# anchors on one.
STOPWORDS = frozenset(
    """
    a an the and or but nor so yet of to in on at for with by from as is are
    was were be been being have has had do does did will would should could
    can may might must this that these those it its they them their he she
    his her him we our us you your i my me not no if than then there here
    what which who whom when where why how all any some more most other
    such only own same too very just about up down out off over under again
    further once thats theres im ive youre youve well shes hes were
    weve theyve dont didnt doesnt isnt arent wasnt werent wont wouldnt
    couldnt shouldnt cant ok okay yeah yes um uh
    """.split()
)


class FlagSourceError(RuntimeError):
    """A roster-band flagging input is malformed."""


def _sub_cost(c1: str, c2: str) -> float:
    if c1 == c2:
        return 0.0
    if c1 in _VOWELS and c2 in _VOWELS:
        return 0.5
    if frozenset((c1, c2)) in _VOICED_PAIRS:
        return 0.6
    return 1.0


def weighted_grapheme_distance(a: str, b: str) -> float:
    """Normalized weighted edit distance in [0, 1] (module docstring's
    frozen substitution-cost table); ported verbatim from the flag-eval
    harness's ``common_text.py``."""

    la, lb = len(a), len(b)
    if la == 0 and lb == 0:
        return 0.0
    if la == 0 or lb == 0:
        return 1.0
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        curr = [i] + [0] * lb
        ca = a[i - 1]
        for j in range(1, lb + 1):
            sub = prev[j - 1] + _sub_cost(ca, b[j - 1])
            delete = prev[j] + 1.0
            insert = curr[j - 1] + 1.0
            curr[j] = min(sub, delete, insert)
        prev = curr
    return prev[lb] / max(la, lb)


def band_centrality(distance: float, lo: float = BAND_LOW, hi: float = BAND_HIGH) -> float:
    """1.0 at ``distance == lo``, linearly decaying to 0.0 at ``distance ==
    hi`` (module docstring); ported verbatim. Caller must already have
    checked ``lo <= distance <= hi``."""

    if hi <= lo:
        return 1.0
    return max(0.0, min(1.0, 1.0 - (distance - lo) / (hi - lo)))


def _char_histogram_lower_bound(la: int, lb: int, common: int) -> float:
    """Exact lower bound on the weighted edit cost from lengths + shared
    character-multiset size alone (never overestimates the true distance) --
    used only to skip the O(la*lb) DP for a pair that provably cannot land
    in-band; ported verbatim from the flag-eval harness."""

    return 0.5 * (min(la, lb) - common) + 1.0 * abs(la - lb)


def _length_prune_ok(la: int, lb: int) -> bool:
    if la == 0 or lb == 0:
        return False
    return abs(la - lb) <= BAND_HIGH * max(la, lb)


def _decompose_candidate_words(term: str) -> list[str]:
    """The constituent NORMALIZED words of one candidate ``term`` that a
    roster-band query may anchor on (D7 delivery-gate defect fix, ``docs/
    exposure-ledger.md``'s SAEA-D7-delivery consumption note, 2026-08-15):
    every raw whitespace-split token of ``term``, normalized via
    :func:`core.retrieval.normalize_term` (further split on any internal
    whitespace THAT normalization itself introduces, e.g. a hyphenated
    token), dropped when it is empty, a closed-class honorific/suffix form
    (:data:`_STOP_FORMS`), or shorter than :data:`MIN_CANDIDATE_WORD_LENGTH`.

    Order-preserving (adjacent survivors are what :func:`_candidate_bigrams`
    below pairs) -- "Dr. Todd Brady" decomposes to ``["todd", "brady"]``,
    "Aldeyra Therapeutics Inc" to ``["aldeyra", "therapeutics"]``. May be
    empty (e.g. a term that is entirely honorifics/short forms)."""

    words: list[str] = []
    for raw in term.split():
        for normalized in normalize_term(raw).split():
            if not normalized or normalized in _STOP_FORMS:
                continue
            if len(normalized) < MIN_CANDIDATE_WORD_LENGTH:
                continue
            words.append(normalized)
    return words


def candidate_word_forms(term: str) -> list[str]:
    """Public name for :func:`_decompose_candidate_words`.

    The frozen decomposition, unchanged and not copied: a second judge that
    matches draft spans against named entities must anchor on the SAME word
    forms this module's own band matcher anchors on, or two flag sources
    would disagree about what a candidate term even contains. Added for
    ``core.judges.BriefNameNearMissJudge`` (E21-LOOP-1), which is the first
    caller outside this module.
    """

    return _decompose_candidate_words(term)


def candidate_bigram_forms(words: Sequence[str]) -> list[str]:
    """Public name for :func:`_candidate_bigrams`, for the same reason as
    :func:`candidate_word_forms`."""

    return _candidate_bigrams(words)


def _candidate_bigrams(words: Sequence[str]) -> list[str]:
    """Adjacent (i, i+1) pairs of already-decomposed candidate words
    (D7 fix), space-joined -- the granularity a 2-word draft window matches
    against, mirroring :func:`roster_band_flags`'s own draft-side 2-word
    window. Empty when ``words`` has fewer than two entries."""

    return [f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1)]


class _TargetIndex:
    """Length-bucketed index over the candidate/target strings so
    :meth:`best_band_match` skips the DP for any pair the cheap
    length/character-histogram lower bounds already rule out of band --
    ported verbatim from the flag-eval harness's ``common_text.TargetIndex``."""

    def __init__(self, targets: Sequence[str]) -> None:
        self._by_len: dict[int, list[tuple[str, Counter]]] = {}
        seen: set[str] = set()
        for target in targets:
            if not target or target in seen:
                continue
            seen.add(target)
            self._by_len.setdefault(len(target), []).append((target, Counter(target)))
        self._lengths = sorted(self._by_len)

    def best_band_match(self, query: str) -> tuple[str, float] | None:
        if not query:
            return None
        lq = len(query)
        qcount = Counter(query)
        best: tuple[str, float] | None = None
        best_centrality = -1.0
        for length in self._lengths:
            if not _length_prune_ok(lq, length):
                continue
            max_len = max(lq, length)
            for target, tcount in self._by_len[length]:
                if target == query:
                    continue
                common = sum(min(n, qcount.get(c, 0)) for c, n in tcount.items())
                if _char_histogram_lower_bound(lq, length, common) / max_len > BAND_HIGH:
                    continue
                distance = weighted_grapheme_distance(query, target)
                if BAND_LOW <= distance <= BAND_HIGH:
                    centrality = band_centrality(distance)
                    if centrality > best_centrality:
                        best_centrality = centrality
                        best = (target, distance)
        return best


@dataclass(frozen=True)
class _RarityModel:
    counts: Counter
    df: Mapping[str, int] | None = None

    def df_rarity(self, word: str) -> float:
        """``1/sqrt(count)`` (module docstring); saturates to 1.0 for a
        hapax. Prefers ``self.df`` (the whole-SAMPLE pass-1 draft word
        count, D7C fix) when supplied -- a missing or malformed entry
        (never expected in practice: ``df`` is built FROM this same
        sample's words, module docstring) falls back to count 1, never
        raising or dividing by zero. Falls back to THIS SLICE's own
        ``counts`` table when ``df`` is ``None`` (byte-identical to the
        pre-fix behaviour)."""

        if self.df is not None:
            count = self.df.get(word, 1)
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                count = 1
            return 1.0 / math.sqrt(count)
        count = self.counts.get(word, 0)
        if count <= 0:
            return 1.0
        return 1.0 / math.sqrt(count)


def _name_likeness_prior(raw_word: str, capitalized_mid_sentence: bool) -> float:
    """Dampens hapax-rarity false positives on ordinary lowercase words
    (module docstring's frozen prior); ported verbatim."""

    case_mult = 1.0 if capitalized_mid_sentence else 0.3
    len_mult = 1.0 if len(raw_word) >= MIN_RARE_WORD_LENGTH else 0.5
    return case_mult * len_mult


_SENTENCE_END_CHARS = frozenset(".?!…")


def _sentence_initial_flags(raw_words: Sequence[str]) -> list[bool]:
    """Gold-free sentence-initial detection from the draft's OWN trailing
    punctuation (never a reference transcript's); ported verbatim from the
    flag-eval harness's ``sentence_initial_from_raw_words``."""

    flags = [False] * len(raw_words)
    if raw_words:
        flags[0] = True
    for i in range(1, len(raw_words)):
        prev = raw_words[i - 1]
        if prev and prev[-1] in _SENTENCE_END_CHARS:
            flags[i] = True
    return flags


@dataclass(frozen=True)
class RosterBandFlag:
    """One roster-band flagged span: ``span`` is a ``(start, end)`` word
    index pair (``end`` exclusive, matching ``core.replay_signals.
    flag_spans``' own convention), ``candidate``/``distance`` are the
    best-band-matching candidate term and its weighted grapheme distance,
    and ``score`` is ``band_centrality(distance) * rarity`` (module
    docstring). ``candidate`` is always the ORIGINAL full candidate term
    (normalized), even when the actual band match landed on one of its
    decomposed WORDS or an adjacent word bigram (D7 fix,
    :func:`_decompose_candidate_words`) -- ``matched_form`` is that
    decomposed form (additive; equal to ``candidate`` whenever a term
    decomposes to a single word matched directly)."""

    span: tuple[int, int]
    candidate: str
    distance: float
    score: float
    matched_form: str


def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def roster_band_flags(
    words: Sequence[str],
    candidate_terms: Sequence[str],
    max_spans: int,
    df: Mapping[str, int] | None = None,
    min_score: float = 0.0,
) -> list[RosterBandFlag]:
    """The top ``max_spans`` non-overlapping roster-band flags for one
    slice's draft ``words`` (module docstring): every non-stopword draft
    word, and every 2-word window starting at a non-stopword word whose
    second word is also not a stopword, is compared against
    ``candidate_terms`` through the band-matching machinery above. Greedy
    non-overlapping selection by descending score (ties broken by earlier
    span start, mirroring the flag-eval harness's ``budget.select_topk``),
    truncated to ``max_spans``, then returned in ascending span-start order
    -- the same "non-overlapping, ascending-start" contract
    ``core.replay_signals.flag_spans`` already guarantees, since
    ``reproduction.replay_loop``'s ACCEPT stage splices spans in one
    left-to-right pass assuming it.

    WORD-GRANULARITY MATCHING (D7 delivery-gate defect fix, ``docs/
    exposure-ledger.md``'s SAEA-D7-delivery consumption note, 2026-08-15):
    each ``candidate_terms`` entry is DECOMPOSED into its constituent words
    (:func:`_decompose_candidate_words`, honorifics/corporate suffixes
    stripped, words shorter than :data:`MIN_CANDIDATE_WORD_LENGTH` dropped)
    before matching -- a multi-word candidate like "Aldeyra Therapeutics
    Inc" no longer has to band-match a 1-2 word draft span AS A WHOLE
    (impossible by length alone; the pre-fix defect measured 0 acceptances
    end to end). A single draft word matches against the decomposed WORDS
    only; a 2-word draft window matches against BOTH those words AND the
    term's adjacent word BIGRAMS (:func:`_candidate_bigrams`) -- whichever
    yields the higher :func:`band_centrality`. Every :class:`RosterBandFlag`
    still reports the ORIGINAL full term as ``candidate`` (module docstring
    -- unchanged trace/test contract), with the actual decomposed form that
    matched additionally in ``matched_form``.

    ``df`` (D7C fix, module docstring's rarity bullet): the whole-SAMPLE
    pass-1 draft's own normalized word-count table, keyed by
    :func:`core.retrieval.normalize_term` form. When supplied, every word's
    rarity uses ``1/sqrt(df[word])`` (clamped ``df >= 1``, missing entries
    treated as 1) instead of this call's own slice-local count. ``None``
    (the default) is byte-identical to the pre-D7C behaviour.

    ``min_score`` (Guard 1, D7D fix, ``docs/exposure-ledger.md``'s
    SAEA-D7D-delivery consumption note, 2026-08-15): a candidate scoring
    below this floor is dropped before selection -- never flagged, never
    consuming a ``max_spans`` slot (measured: near-zero sub-token band
    matches at score 0.0-0.034 were issuing full REPLAY calls). ``0.0``
    (the default) is byte-identical to the pre-D7D behaviour, since every
    ``score`` here is already non-negative.

    Returns an empty list (never raises) when ``words``/``candidate_terms``
    is empty or nothing lands in-band -- SCORE already treats zero flags as
    nothing to replay. Fails closed only on a malformed ``max_spans``."""

    if isinstance(max_spans, bool) or not isinstance(max_spans, int) or max_spans < 1:
        raise FlagSourceError(f"max_spans must be a positive integer, got {max_spans!r}")
    if not words or not candidate_terms:
        return []

    # D7 fix: index DECOMPOSED words/bigrams, not whole candidate strings
    # (see this function's own docstring above) -- target_to_term maps each
    # decomposed form back to its ORIGINAL (normalized, whole) term for the
    # trace-facing `candidate` field; first-registered term wins a shared
    # decomposed form, deterministic given `candidate_terms`' own order.
    word_targets: dict[str, None] = {}
    bigram_targets: dict[str, None] = {}
    target_to_term: dict[str, str] = {}
    for term in candidate_terms:
        full_term = normalize_term(term)
        decomposed = _decompose_candidate_words(term)
        for word in decomposed:
            word_targets.setdefault(word, None)
            target_to_term.setdefault(word, full_term)
        for bigram in _candidate_bigrams(decomposed):
            bigram_targets.setdefault(bigram, None)
            target_to_term.setdefault(bigram, full_term)

    word_index = _TargetIndex(list(word_targets))
    bigram_index = _TargetIndex(list(bigram_targets))
    words = list(words)
    normalized_words = [normalize_term(word) for word in words]
    sentence_initial = _sentence_initial_flags(words)
    rarity_model = _RarityModel(counts=Counter(w for w in normalized_words if w), df=df)

    match_cache: dict[tuple[str, bool], tuple[str, float] | None] = {}

    def lookup(text: str, *, allow_bigram: bool) -> tuple[str, float] | None:
        """Best band match for ``text`` (module docstring's WORD-GRANULARITY
        MATCHING section): always checks ``word_index``; a 2-word draft
        window (``allow_bigram=True``) ALSO checks ``bigram_index``, keeping
        whichever candidate has the higher :func:`band_centrality`."""

        cache_key = (text, allow_bigram)
        if cache_key not in match_cache:
            best: tuple[str, float] | None = None
            best_centrality = -1.0
            lookups = (word_index.best_band_match(text),)
            if allow_bigram:
                lookups += (bigram_index.best_band_match(text),)
            for found in lookups:
                if found is None:
                    continue
                centrality = band_centrality(found[1])
                if centrality > best_centrality:
                    best_centrality = centrality
                    best = found
            match_cache[cache_key] = best
        return match_cache[cache_key]

    def word_rarity(i: int) -> float:
        capitalized = words[i][:1].isupper() and not sentence_initial[i]
        return rarity_model.df_rarity(normalized_words[i]) * _name_likeness_prior(
            words[i], capitalized
        )

    n = len(words)
    candidates: list[RosterBandFlag] = []
    for i in range(n):
        w = normalized_words[i]
        if not w or w in STOPWORDS:
            continue
        match = lookup(w, allow_bigram=False)
        if match is not None:
            target, distance = match
            score = band_centrality(distance) * word_rarity(i)
            candidates.append(
                RosterBandFlag(
                    span=(i, i + 1),
                    candidate=target_to_term[target],
                    distance=distance,
                    score=score,
                    matched_form=target,
                )
            )
        w2 = normalized_words[i + 1] if i + 1 < n else None
        if w2 and w2 not in STOPWORDS:
            window = f"{w} {w2}"
            match2 = lookup(window, allow_bigram=True)
            if match2 is not None:
                target, distance = match2
                score = band_centrality(distance) * min(word_rarity(i), word_rarity(i + 1))
                candidates.append(
                    RosterBandFlag(
                        span=(i, i + 2),
                        candidate=target_to_term[target],
                        distance=distance,
                        score=score,
                        matched_form=target,
                    )
                )

    # Guard 1 (D7D fix, this function's own docstring): dropped BEFORE
    # selection, not after -- a below-floor span never occupies a
    # `max_spans` slot a genuine flag could otherwise have used.
    candidates = [flag for flag in candidates if flag.score >= min_score]
    ordered = sorted(candidates, key=lambda flag: (-flag.score, flag.span[0], flag.span[1]))
    selected: list[RosterBandFlag] = []
    for flag in ordered:
        if len(selected) >= max_spans:
            break
        if any(_overlaps(flag.span, chosen.span) for chosen in selected):
            continue
        selected.append(flag)
    selected.sort(key=lambda flag: flag.span)
    return selected
