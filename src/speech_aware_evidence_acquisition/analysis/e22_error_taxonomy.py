"""Earnings-22 DEV semantic error taxonomy (``SAEA-E22-MF-SEMANTIC-ERROR-SCAN-V1``).

Owner request of 2026-09-06: *not* a WER decomposition -- scan the error
comparisons and dig out the root causes at the SEMANTIC level. This module is
the mechanical half of that scan. It is model-free by construction: it reads
already-sealed hypothesis text, the hash-pinned dev10 reference layer and the
hash-pinned dev10 segment table, and it contacts nothing.

Three things make the measurement auditable rather than merely plausible.

**The identity gate.** :func:`align_spans` re-implements the frozen
``scoring.wer.align`` backtrace (match/substitution, then deletion, then
insertion, at equal cost) and emits the individual operations it walks over.
Its S/D/I totals must equal ``scoring.wer.align``'s on any pair -- a unit test
asserts that on random pairs, and :func:`build_receipts` refuses to write a
receipt unless the flight-level totals reproduce the sealed verdict table
(arm A 4,526 / 2,370 / 11,270 over 103,423 reference words, and its two
siblings) to the unit. If the aligner is not the alignment the verdict scored,
nothing downstream is worth reading.

**The dual pass.** Every utterance is aligned twice: on the RAW text
(whitespace tokens, casefolded) and on the WHISPER-NORMALIZED text (the
paper-facing convention, ``str.split()`` after
``reproduction.asr_wer_whisper.normalize_whisper_english``). A raw error span
whose two sides normalize to the same string is mechanically ``format-only``:
that is what makes "errors that vanish under normalization" -- the owner's
*"twenty twenty two"* vs *"2022"* example -- a measurement instead of an
opinion. All category, impact and agentic-error-rate figures are computed on
the NORMALIZED pass, because that is the pass the published number lives on;
the raw pass exists only to size what the normalizer has already folded.

**Named rules.** :func:`classify_span` is an ordered, first-match-wins cascade
and every span carries the name of the rule that decided it, so every share in
the readiness note can be traced to one rule. The residual bucket is
sub-bucketed by named rules too -- nothing is left as a nameless remainder.

Nothing here licenses a fix: no normalizer is edited, no scorer is changed, no
hypothesis is post-processed. A "could be folded" figure is an option with an
authority attached (the Whisper normalizer's own rules, the ESB protocol, the
Open ASR Leaderboard's ``merge_compounds``); folds without an authority are
reported under their own name and refused.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from ..reproduction.asr_wer_whisper import (
    WHISPER_NORMALIZER_NAME,
    normalize_whisper_english,
)

TAXONOMY_VERSION = "saea-e22-error-taxonomy-v1"
EXPOSURE_ROW_ID = "SAEA-E22-MF-SEMANTIC-ERROR-SCAN-V1"
READ_SAMPLE_SEED = 20260903
READ_SAMPLE_SIZE = 1500

#: The sealed 2026-09-05 flight totals, under the Whisper normalizer. These are
#: the correctness gate on this module's aligner, not an input to any figure.
SEALED_TOTALS: Mapping[str, Mapping[str, int]] = {
    "A": {"substitutions": 4526, "deletions": 2370, "insertions": 11270, "reference_words": 103423},
    "B": {"substitutions": 4563, "deletions": 2479, "insertions": 11982, "reference_words": 103423},
    "C": {"substitutions": 4433, "deletions": 4975, "insertions": 9094, "reference_words": 103423},
}

CATEGORIES = (
    "format-convention",
    "reference-convention",
    "segmentation-artifact",
    "named-entity",
    "domain-term",
    "model-behaviour",
    "acoustic-misrecognition",
    "other",
)

IMPACTS = ("NONE", "LOW", "HIGH")

#: Every rule :func:`classify_span` can return, in cascade order. The four-bin
#: estimate must partition exactly this tuple -- a rule that reaches a receipt
#: without a bin would be error mass with no account of what it is.
ALL_RULES = (
    "format-convention/stray-punctuation-token",
    "format-convention/merge-compound",
    "format-convention/symbol-only",
    "format-convention/whisper-refold",
    "format-convention/numeric-equal",
    "reference-convention/empty-reference",
    "reference-convention/redacted-region",
    "reference-convention/false-start-stem",
    "reference-convention/filler-token",
    "reference-convention/backchannel-variant",
    "reference-convention/discourse-phrase",
    "reference-convention/reference-repetition",
    "reference-convention/discourse-single",
    "segmentation-artifact/neighbour-bleed",
    "segmentation-artifact/boundary-continuation",
    "segmentation-artifact/boundary-onset",
    "segmentation-artifact/boundary-partial-word",
    "named-entity/call-inventory",
    "domain-term/pinned-lexicon",
    "model-behaviour/non-english-script",
    "model-behaviour/hypothesis-loop",
    "model-behaviour/hypothesis-repetition",
    "model-behaviour/runaway-tail",
    "model-behaviour/runaway-head",
    "model-behaviour/truncation",
    "acoustic-misrecognition/string-near",
    "other/function-word-swap",
    "other/substituted-content-word",
    "other/deleted-function-word",
    "other/inserted-function-word",
    "other/deleted-content-word",
    "other/inserted-content-word",
)

#: Categories whose spans can never be semantically HIGH, by ruling rather than
#: by measurement -- stated here so the ruling is visible and reversible. A
#: format equivalence and a reference-side transcription convention change no
#: fact; a boundary bleed duplicates the NEIGHBOURING segment's own reference
#: words, so at call level nothing is lost or invented. ``build_receipts`` also
#: reports a STRICT variant that drops ``segmentation-artifact`` from this set.
IMPACT_NEUTRAL_CATEGORIES = frozenset(
    {"format-convention", "reference-convention", "segmentation-artifact"}
)

# ---------------------------------------------------------------------------
# Pinned lexicons. Every one of these is literal, committed and reproduced into
# the receipt, so a share that rests on a lexicon can be re-derived from it.
# ---------------------------------------------------------------------------

#: Non-lexical fillers. The Whisper normalizer already deletes
#: ``hmm|mm|mhm|mmm|uh|um``; these are the ones it leaves standing.
NONLEXICAL_FILLERS = frozenset(
    {"umm", "uhh", "uhm", "erm", "er", "hm", "mmhmm", "uhhuh", "huh", "ah", "aah", "eh", "mhmm"}
)

#: Multi-word discourse markers. Unambiguous: no ordinary sentence loses meaning
#: when "you know" is removed from it.
DISCOURSE_PHRASES = (
    ("you", "know"),
    ("i", "mean"),
    ("kind", "of"),
    ("sort", "of"),
    ("you", "see"),
    ("or", "whatever"),
)

#: Single-token discourse markers. AMBIGUOUS: each is also an ordinary word, so
#: their mass is reported as its own sub-rule and never folded into the
#: authority-bearing scoring-convention bin.
DISCOURSE_SINGLES = frozenset(
    {"yeah", "yep", "okay", "ok", "right", "well", "so", "like", "actually", "basically", "anyway"}
)

#: Acknowledgement tokens. A substitution with ONLY these on both sides is one
#: backchannel spelled as another ("yep" for "yeah"), which is a transcription
#: convention rather than a recognition failure.
BACKCHANNELS = frozenset(
    {"yeah", "yep", "yes", "okay", "ok", "right", "sure", "thanks", "thank", "alright",
     "hi", "hello", "bye", "uhhuh", "mhmm"}
)

#: Finance / earnings-call domain vocabulary, single tokens after Whisper
#: normalization (which lowercases, expands contractions and turns "&" and "-"
#: into spaces, so "S&P" is "s p" and "year-over-year" is "year over year").
DOMAIN_TERMS = frozenset(
    {
        "ebitda", "ebit", "ebitdar", "eps", "arr", "mrr", "arpu", "cagr", "capex", "opex",
        "cogs", "fcf", "nim", "npl", "roe", "roa", "roic", "wacc", "dso", "dpo", "bps",
        "gaap", "sku", "asp", "ltv", "yoy", "fx",
        "revenue", "revenues", "margin", "margins", "guidance", "sequential", "sequentially",
        "amortization", "amortisation", "depreciation", "goodwill", "impairment", "provision",
        "dividend", "dividends", "buyback", "repurchase", "backlog", "bookings", "churn",
        "accretive", "dilutive", "dilution", "headwind", "headwinds", "tailwind", "tailwinds",
        "deleveraging", "leverage", "gearing", "receivables", "payables", "inventory",
        "inventories", "liquidity", "solvency", "covenant", "covenants", "maturities",
        "amortizing", "annualized", "annualised", "normalized", "normalised", "underlying",
        "organic", "inorganic", "synergies", "utilization", "utilisation", "occupancy",
        "attrition", "retention", "penetration", "elasticity", "hedge", "hedging", "hedged",
        "forex", "currency", "constant", "comparable", "comparables", "comps", "consensus",
        "ebitda margin", "topline", "capitalization", "capitalisation", "valuation",
        "earnings", "profitability", "profit", "profits", "loss", "losses", "cashflow",
        "creditor", "creditors", "debtor", "debtors", "equity", "debt", "interest",
        "tax", "taxation", "yield", "yields", "spread", "spreads", "basis", "coupon",
        "quarter", "quarterly", "annum", "fiscal", "guidance", "outlook", "forecast",
        "repo", "wholesale", "retail", "segment", "segments", "portfolio", "pipeline",
        "reconciliation", "restructuring", "writedown", "writeoff", "accrual", "accruals",
    }
)

#: Words carrying a negation. Whisper expands "don't" to "do not", so the bare
#: forms are enough.
NEGATIONS = frozenset(
    {"not", "no", "never", "none", "nothing", "neither", "nor", "without", "aint", "cannot"}
)

#: Function words. A span whose only changed tokens are these is wording, not
#: content -- it drops out of the LOW tier into NONE.
STOPWORDS = frozenset(
    {
        "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for", "with",
        "as", "is", "are", "was", "were", "be", "been", "being", "am", "that", "this",
        "these", "those", "it", "its", "i", "we", "you", "they", "he", "she", "our",
        "your", "their", "my", "me", "us", "them", "him", "her", "his", "do", "does",
        "did", "have", "has", "had", "will", "would", "can", "could", "should", "may",
        "might", "must", "there", "here", "then", "if", "about", "from", "by", "up",
        "down", "out", "over", "into", "just", "also", "very", "really", "quite", "now",
        "which", "who", "what", "when", "where", "how", "because", "while", "all", "any",
        "some", "more", "most", "other", "such", "own", "same", "too", "s", "t",
    }
)

#: Never an entity form, however the transcript capitalizes it: the pronoun "I",
#: any one-character form, the function words, the acknowledgement and filler
#: vocabulary, and the domain terms (which have their own category and rule). Rev
#: writes "IT", "US" and "EBITDA" in capitals, and without this the pronoun "it",
#: the pronoun "us" and a domain term would all be scored as named entities.
ENTITY_INVENTORY_EXCLUSIONS = frozenset(
    {"i"} | set(STOPWORDS) | set(DOMAIN_TERMS) | set(NONLEXICAL_FILLERS)
    | set(DISCOURSE_SINGLES) | set(BACKCHANNELS)
)

#: Rules whose spans are NONE by ruling even though their category is not: a
#: hypothesis that says the same phrase twice has lost nothing, whatever the
#: phrase contains.
IMPACT_NEUTRAL_RULES = frozenset({"model-behaviour/hypothesis-repetition"})

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'&.-]*")
_TAG_RE = re.compile(r"[<\[][^>\]]*[>\]]|\([^)]+?\)")
_TRUNCATION_RE = re.compile(r"\b([A-Za-z']+)-(?=[\s,.?!;:]|$)")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_TICKER_RE = re.compile(r"\b[A-Z]{2,5}\b")
#: Codepoint blocks that are not the Latin script the task is defined over: CJK,
#: Hangul, fullwidth forms, Cyrillic and Thai. Built from hex bounds so this source
#: file stays pure ASCII.
_NON_LATIN_BLOCKS = (
    (0x3000, 0x9FFF),
    (0xAC00, 0xD7AF),
    (0xFF00, 0xFFEF),
    (0x0400, 0x04FF),
    (0x0E00, 0x0E7F),
)
_CJK_RE = re.compile(
    "[" + "".join(chr(low) + "-" + chr(high) for low, high in _NON_LATIN_BLOCKS) + "]"
)
_DIGIT_RE = re.compile(r"\d")


# ---------------------------------------------------------------------------
# Alignment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ErrorSpan:
    """One maximal run of same-typed alignment operations, with its context."""

    op: str
    ref_start: int
    ref_end: int
    hyp_start: int
    hyp_end: int
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]
    ref_left: tuple[str, ...]
    ref_right: tuple[str, ...]
    hyp_left: tuple[str, ...]
    hyp_right: tuple[str, ...]

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.op, self.ref_start, self.hyp_start)

    @property
    def ref_text(self) -> str:
        return " ".join(self.ref_tokens)

    @property
    def hyp_text(self) -> str:
        return " ".join(self.hyp_tokens)

    @property
    def reference_word_charge(self) -> int:
        """Reference words this span puts at risk (an insertion charges one)."""

        return len(self.ref_tokens) if self.op in ("SUB", "DEL") else 1


@dataclass(frozen=True)
class SpanAlignment:
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int
    hypothesis_length: int
    spans: tuple[ErrorSpan, ...]

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions


def _operations(ref: Sequence[str], hyp: Sequence[str]) -> list[tuple[str, int, int]]:
    """The frozen ``scoring.wer.align`` backtrace, emitted operation by operation.

    Same cost matrix, same tie-break order (match/substitution, then deletion,
    then insertion), so the S/D/I totals are identical by construction; only the
    per-operation record is new. Returned left to right as ``(op, i, j)`` with
    ``i`` the reference index and ``j`` the hypothesis index the operation
    consumes (``-1`` where the operation consumes nothing on that side).
    """

    rows, cols = len(ref) + 1, len(hyp) + 1
    cost = [[0] * cols for _ in range(rows)]
    for i in range(1, rows):
        cost[i][0] = i
    for j in range(1, cols):
        cost[0][j] = j
    for i in range(1, rows):
        row, previous = cost[i], cost[i - 1]
        ref_token = ref[i - 1]
        for j in range(1, cols):
            diagonal = previous[j - 1] + (0 if ref_token == hyp[j - 1] else 1)
            row[j] = min(diagonal, previous[j] + 1, row[j - 1] + 1)

    operations: list[tuple[str, int, int]] = []
    i, j = len(ref), len(hyp)
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            diagonal = cost[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1)
            if cost[i][j] == diagonal:
                operations.append(
                    ("HIT" if ref[i - 1] == hyp[j - 1] else "SUB", i - 1, j - 1)
                )
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            operations.append(("DEL", i - 1, j))
            i -= 1
            continue
        operations.append(("INS", i, j - 1))
        j -= 1
    operations.reverse()
    return operations


def align_spans(
    ref: Sequence[str], hyp: Sequence[str], *, context: int = 5
) -> SpanAlignment:
    """Align ``hyp`` against ``ref`` and return the merged error spans.

    Adjacent operations of the SAME type are merged into one span, so a run of
    three substitutions is one span of three reference words rather than three
    spans of one. Each span carries a ``context``-token window on both sides of
    both sequences.
    """

    operations = _operations(ref, hyp)
    substitutions = sum(1 for op, _, _ in operations if op == "SUB")
    deletions = sum(1 for op, _, _ in operations if op == "DEL")
    insertions = sum(1 for op, _, _ in operations if op == "INS")

    groups: list[list[tuple[str, int, int]]] = []
    for operation in operations:
        op, i, j = operation
        if op == "HIT":
            continue
        if groups:
            previous = groups[-1][-1]
            if previous[0] == op:
                if op == "SUB" and previous[1] + 1 == i and previous[2] + 1 == j:
                    groups[-1].append(operation)
                    continue
                if op == "DEL" and previous[1] + 1 == i and previous[2] == j:
                    groups[-1].append(operation)
                    continue
                if op == "INS" and previous[1] == i and previous[2] + 1 == j:
                    groups[-1].append(operation)
                    continue
        groups.append([operation])

    spans: list[ErrorSpan] = []
    for group in groups:
        op = group[0][0]
        if op == "SUB":
            ref_start, ref_end = group[0][1], group[-1][1] + 1
            hyp_start, hyp_end = group[0][2], group[-1][2] + 1
        elif op == "DEL":
            ref_start, ref_end = group[0][1], group[-1][1] + 1
            hyp_start = hyp_end = group[0][2]
        else:
            ref_start = ref_end = group[0][1]
            hyp_start, hyp_end = group[0][2], group[-1][2] + 1
        spans.append(
            ErrorSpan(
                op=op,
                ref_start=ref_start,
                ref_end=ref_end,
                hyp_start=hyp_start,
                hyp_end=hyp_end,
                ref_tokens=tuple(ref[ref_start:ref_end]),
                hyp_tokens=tuple(hyp[hyp_start:hyp_end]),
                ref_left=tuple(ref[max(0, ref_start - context):ref_start]),
                ref_right=tuple(ref[ref_end:ref_end + context]),
                hyp_left=tuple(hyp[max(0, hyp_start - context):hyp_start]),
                hyp_right=tuple(hyp[hyp_end:hyp_end + context]),
            )
        )

    return SpanAlignment(
        substitutions=substitutions,
        deletions=deletions,
        insertions=insertions,
        reference_length=len(ref),
        hypothesis_length=len(hyp),
        spans=tuple(spans),
    )


# ---------------------------------------------------------------------------
# Per-utterance and per-call context the rules read
# ---------------------------------------------------------------------------


def normalized_tokens(text: str) -> tuple[str, ...]:
    return tuple(normalize_whisper_english(text).split())


def raw_tokens(text: str) -> tuple[str, ...]:
    return tuple(text.casefold().split())


def truncation_stems(raw_reference: str) -> frozenset[str]:
    """Normalized forms of raw reference tokens that END in a hyphen.

    Rev's convention writes a cut-off word as ``H-`` / ``Co-`` / ``increbl-``.
    The Whisper normalizer turns the hyphen into a space, so the stem survives
    into the scored reference as a token no model will ever emit.
    """

    stems: set[str] = set()
    for match in _TRUNCATION_RE.finditer(raw_reference):
        form = normalize_whisper_english(match.group(1)).split()
        if len(form) == 1:
            stems.add(form[0])
    return frozenset(stems)


def tag_anchor_indices(raw_reference: str) -> tuple[int, ...]:
    """Normalized reference indices where an ``<inaudible>``-style tag was removed."""

    anchors: list[int] = []
    for match in _TAG_RE.finditer(raw_reference):
        anchors.append(len(normalize_whisper_english(raw_reference[: match.start()]).split()))
    return tuple(sorted(set(anchors)))


def build_entity_inventory(raw_by_call: Mapping[str, Sequence[str]]) -> dict[str, frozenset[str]]:
    """Per-call named-entity forms, derived model-free from that call's own references.

    A normalized form is an entity form for a call when it appears CAPITALIZED
    in a non-sentence-initial position at least once and does so more often than
    it appears lowercase in a non-sentence-initial position -- the majority rule
    that keeps ordinary words which merely start sentences out of the set.
    Uppercase 2-5 letter tokens (ticker shape) are added unconditionally.
    """

    inventory: dict[str, frozenset[str]] = {}
    for call, sentences in raw_by_call.items():
        capitalized: Counter[str] = Counter()
        lowercased: Counter[str] = Counter()
        tickers: set[str] = set()
        for sentence in sentences:
            for clause in _SENTENCE_SPLIT_RE.split(sentence):
                words = _WORD_RE.findall(clause)
                for position, word in enumerate(words):
                    form = normalize_whisper_english(word).split()
                    if len(form) != 1:
                        continue
                    if position == 0:
                        continue
                    if word[0].isupper():
                        capitalized[form[0]] += 1
                    else:
                        lowercased[form[0]] += 1
            for ticker in _TICKER_RE.findall(sentence):
                form = normalize_whisper_english(ticker).split()
                if len(form) == 1:
                    tickers.add(form[0])
        forms = {
            form
            for form, count in capitalized.items()
            if count > lowercased.get(form, 0)
        }
        inventory[call] = frozenset(
            form
            for form in forms | tickers
            if len(form) >= 2 and form not in ENTITY_INVENTORY_EXCLUSIONS
        )
    return inventory


@dataclass(frozen=True)
class UtteranceContext:
    """Everything the cascade may read about one utterance. No model, no gold beyond
    this utterance's own reference and its two neighbours' references."""

    sample_id: str
    call: str
    raw_reference: str
    raw_hypothesis: str
    ref_tokens: tuple[str, ...]
    hyp_tokens: tuple[str, ...]
    duration_s: float
    stems: frozenset[str]
    tag_anchors: tuple[int, ...]
    previous_tokens: tuple[str, ...]
    next_tokens: tuple[str, ...]
    entity_forms: frozenset[str]

    @property
    def neighbour_tokens(self) -> tuple[str, ...]:
        """Both neighbours, separated so no match can straddle the two."""

        if not self.previous_tokens:
            return self.next_tokens
        if not self.next_tokens:
            return self.previous_tokens
        return self.previous_tokens + (NEIGHBOUR_SEPARATOR,) + self.next_tokens

    @property
    def reference_empty(self) -> bool:
        return not self.ref_tokens

    @property
    def truncated(self) -> bool:
        return bool(self.ref_tokens) and len(self.hyp_tokens) * 2 < len(self.ref_tokens)


# ---------------------------------------------------------------------------
# The cascade
# ---------------------------------------------------------------------------


def _normalizes_equal(left: Iterable[str], right: Iterable[str]) -> bool:
    return normalize_whisper_english(" ".join(left)) == normalize_whisper_english(" ".join(right))


def _digits(tokens: Iterable[str]) -> str:
    return "".join(_DIGIT_RE.findall(" ".join(tokens)))


#: Symbols that carry meaning rather than layout. A sign, a currency mark or a
#: percent sign is part of the VALUE, so two sides that differ in them are never
#: a format equivalence however their letters and digits line up: ``-18`` against
#: ``18`` is a sign flip and ``14.9%`` against ``14.9`` drops the unit.
MEANINGFUL_SYMBOLS = "+-$%"


def _squash(tokens: Iterable[str]) -> str:
    """Letters and digits only, no spaces -- the shape ``merge_compounds`` compares on."""

    return "".join(character for token in tokens for character in token if character.isalnum())


def _meaningful_symbols(tokens: Iterable[str]) -> Counter[str]:
    return Counter(
        character
        for token in tokens
        for character in token
        if character in MEANINGFUL_SYMBOLS
    )


def _merge_compound_window(span: ErrorSpan) -> str | None:
    """``"merge-compound"``, ``"symbol-only"`` or ``None``.

    The two sides differ only in where the WORD BOUNDARIES fall, or only in
    symbols the Whisper normalizer deliberately keeps (``.%$`` and the currency
    signs). Compared over a window that reaches up to two tokens past the span on
    each side, because a compound split shows up in the alignment as an error
    span plus its aligned neighbour: ``the U.S. and`` against ``the US and`` is a
    deletion of ``u`` whose fold only becomes visible once ``s`` / ``us`` is in
    the window. Boundary differences are exactly the Open ASR Leaderboard's
    ``merge_compounds``, which the published ESB column applies and this study
    does not; symbol-only differences have no such authority and are named
    separately so they can be subtracted.
    """

    for left in (0, 1, 2):
        for right in (0, 1, 2):
            if left == 0 and right == 0 and span.op != "SUB":
                continue
            if left and (len(span.ref_left) < left or len(span.hyp_left) < left):
                continue
            if right and (len(span.ref_right) < right or len(span.hyp_right) < right):
                continue
            reference = (
                span.ref_left[len(span.ref_left) - left:] + span.ref_tokens + span.ref_right[:right]
                if left
                else span.ref_tokens + span.ref_right[:right]
            )
            hypothesis = (
                span.hyp_left[len(span.hyp_left) - left:] + span.hyp_tokens + span.hyp_right[:right]
                if left
                else span.hyp_tokens + span.hyp_right[:right]
            )
            squashed = _squash(reference)
            if len(squashed) < 2 or squashed != _squash(hypothesis) or reference == hypothesis:
                continue
            if _meaningful_symbols(reference) != _meaningful_symbols(hypothesis):
                continue
            return "symbol-only" if len(reference) == len(hypothesis) else "merge-compound"
    return None


def _token_repeats(span: ErrorSpan, index: int, context: "UtteranceContext") -> bool:
    """The deleted reference token also stands, unaffected, within two tokens of itself."""

    position = span.ref_start + index
    token = context.ref_tokens[position]
    for offset in (-2, -1, 1, 2):
        neighbour = position + offset
        if neighbour < 0 or neighbour >= len(context.ref_tokens):
            continue
        if span.ref_start <= neighbour < span.ref_end:
            continue
        if context.ref_tokens[neighbour] == token:
            return True
    return False


def _reference_convention_rule(span: ErrorSpan, context: "UtteranceContext") -> str | None:
    """Name the reference-side convention that covers EVERY token of a deletion.

    Token by token rather than span by span, because the aligner merges adjacent
    deletions: ``the, the ha- two halves`` deletes ``the`` (a repetition) and
    ``ha`` (a truncation stem) as ONE span, and a span-level test would call
    that mixed run neither.
    """

    if span.op != "DEL" or not span.ref_tokens:
        return None
    flags: list[str | None] = []
    for index, token in enumerate(span.ref_tokens):
        if token in context.stems:
            flags.append("false-start-stem")
        elif token in NONLEXICAL_FILLERS:
            flags.append("filler-token")
        elif _token_repeats(span, index, context):
            flags.append("reference-repetition")
        elif token in DISCOURSE_SINGLES:
            flags.append("discourse-single")
        else:
            flags.append(None)
    if not all(flags):
        return None
    for name in ("false-start-stem", "reference-repetition", "filler-token", "discourse-single"):
        if name in flags:
            return name
    return None


def _contained_in_neighbour(tokens: Sequence[str], neighbour: Sequence[str]) -> float:
    """Longest contiguous run of ``tokens`` that also occurs in ``neighbour``, as a share."""

    if not tokens or not neighbour:
        return 0.0
    matcher = difflib.SequenceMatcher(a=list(tokens), b=list(neighbour), autojunk=False)
    match = matcher.find_longest_match(0, len(tokens), 0, len(neighbour))
    return match.size / len(tokens)


def _has_loop(tokens: Sequence[str]) -> bool:
    """An n-gram (n = 1..4) repeated three or more times back to back."""

    for size in (1, 2, 3, 4):
        if len(tokens) < size * 3:
            continue
        for start in range(len(tokens) - size * 3 + 1):
            unit = tuple(tokens[start:start + size])
            if all(
                tuple(tokens[start + step * size:start + (step + 1) * size]) == unit
                for step in (1, 2)
            ):
                return True
    return False


def _string_near(left: Sequence[str], right: Sequence[str]) -> bool:
    for a in left:
        for b in right:
            if difflib.SequenceMatcher(a=a, b=b, autojunk=False).ratio() >= 0.6:
                return True
            if _soundex(a) == _soundex(b) and _soundex(a) != "":
                return True
    return False


_SOUNDEX_CODES = {
    **{c: "1" for c in "bfpv"},
    **{c: "2" for c in "cgjkqsxz"},
    **{c: "3" for c in "dt"},
    "l": "4",
    **{c: "5" for c in "mn"},
    "r": "6",
}


def _soundex(token: str) -> str:
    letters = [c for c in token.lower() if c.isalpha()]
    if not letters:
        return ""
    head, tail = letters[0], letters[1:]
    digits: list[str] = []
    previous = _SOUNDEX_CODES.get(head, "")
    for letter in tail:
        code = _SOUNDEX_CODES.get(letter, "")
        if code and code != previous:
            digits.append(code)
        if letter not in "hw":
            previous = code
    return (head.upper() + "".join(digits) + "000")[:4]


def classify_span(span: ErrorSpan, context: UtteranceContext) -> tuple[str, str]:
    """``(category, rule)`` for one span. Ordered, first match wins.

    Rules 4 and 5 (named entity, domain term) are bounded to spans of at most
    three tokens on a pure insertion or deletion, so that a long runaway or a
    bled-in neighbouring sentence -- which nearly always contains SOME proper
    noun -- reaches rule 6 and is reported as what it is.
    """

    ref, hyp = span.ref_tokens, span.hyp_tokens

    # 0. The one check that precedes the cascade. A hypothesis token in a
    # non-Latin script is a defect of the frozen core whatever position it
    # occupies, and the sealed verdicts count these rows by name; leaving it at
    # rule 6 let a one-word Chinese answer on a near-empty clip be absorbed by
    # the boundary rule at rule 3 instead of being reported.
    if any(_CJK_RE.search(token) for token in hyp):
        return "model-behaviour", "model-behaviour/non-english-script"

    # 1. format / convention equivalents -- folds with a published authority.
    if not _squash(ref) and not _squash(hyp) and (ref or hyp):
        return "format-convention", "format-convention/stray-punctuation-token"
    compound = _merge_compound_window(span)
    if compound is not None:
        return "format-convention", f"format-convention/{compound}"
    if span.op == "SUB" and _meaningful_symbols(ref) == _meaningful_symbols(hyp):
        if _normalizes_equal(ref, hyp):
            return "format-convention", "format-convention/whisper-refold"
        if (
            _digits(ref)
            and _digits(ref) == _digits(hyp)
            and _meaningful_symbols(ref) == _meaningful_symbols(hyp)
        ):
            return "format-convention", "format-convention/numeric-equal"

    # 2. reference-style conventions -- the transcript's rules, not the speech.
    if context.reference_empty:
        return "reference-convention", "reference-convention/empty-reference"
    if span.op == "INS" and span.ref_start in context.tag_anchors:
        return "reference-convention", "reference-convention/redacted-region"
    if span.op == "SUB" and ref and all(token in context.stems for token in ref):
        return "reference-convention", "reference-convention/false-start-stem"
    if span.op == "SUB" and ref and all(token in NONLEXICAL_FILLERS for token in ref):
        return "reference-convention", "reference-convention/filler-token"
    if span.op == "SUB" and ref and hyp and all(
        token in BACKCHANNELS for token in tuple(ref) + tuple(hyp)
    ):
        return "reference-convention", "reference-convention/backchannel-variant"
    if span.op == "DEL" and tuple(ref) in DISCOURSE_PHRASES:
        return "reference-convention", "reference-convention/discourse-phrase"
    covered = _reference_convention_rule(span, context)
    if covered is not None:
        return "reference-convention", f"reference-convention/{covered}"

    # 3. segmentation artifacts at the clip boundary, decided by the segment table.
    at_head = span.op == "INS" and span.hyp_start == 0
    at_tail = span.op == "INS" and span.hyp_end == len(context.hyp_tokens)
    if span.op == "INS" and len(hyp) >= 2 and (at_head or at_tail):
        if _contained_in_neighbour(hyp, context.neighbour_tokens) >= 0.6:
            return "segmentation-artifact", "segmentation-artifact/neighbour-bleed"
    if at_tail and len(hyp) <= 2 and span.ref_start == len(context.ref_tokens):
        return "segmentation-artifact", "segmentation-artifact/boundary-continuation"
    if at_head and len(hyp) <= 2 and span.ref_start == 0:
        return "segmentation-artifact", "segmentation-artifact/boundary-onset"
    if span.op in ("SUB", "DEL") and len(ref) == 1 and (
        span.ref_start == 0 or span.ref_end == len(context.ref_tokens)
    ):
        for token in hyp:
            if token.startswith(ref[0]) or ref[0].startswith(token):
                return "segmentation-artifact", "segmentation-artifact/boundary-partial-word"

    short = span.op == "SUB" or len(ref) + len(hyp) <= 3
    tokens = tuple(ref) + tuple(hyp)

    # 4. named entities.
    if short and any(token in context.entity_forms for token in tokens):
        return "named-entity", "named-entity/call-inventory"

    # 5. financial / domain vocabulary.
    if short and any(token in DOMAIN_TERMS for token in tokens):
        return "domain-term", "domain-term/pinned-lexicon"

    # 6. model behaviour (the non-Latin-script check already ran, at rule 0).
    if span.op == "INS" and _has_loop(hyp):
        return "model-behaviour", "model-behaviour/hypothesis-loop"
    if span.op == "INS" and hyp and (
        span.hyp_right[: len(hyp)] == hyp or span.hyp_left[-len(hyp):] == hyp
    ):
        return "model-behaviour", "model-behaviour/hypothesis-repetition"
    if at_tail:
        return "model-behaviour", "model-behaviour/runaway-tail"
    if at_head:
        return "model-behaviour", "model-behaviour/runaway-head"
    if span.op == "DEL" and len(ref) >= 3 and context.truncated:
        return "model-behaviour", "model-behaviour/truncation"

    # 7. ordinary-word acoustic misrecognition.
    if span.op == "SUB" and _string_near(ref, hyp):
        return "acoustic-misrecognition", "acoustic-misrecognition/string-near"

    # 8. the residual, sub-bucketed by named rules read off the drawn sample.
    if span.op == "SUB" and all(token in STOPWORDS for token in tokens):
        return "other", "other/function-word-swap"
    if span.op == "SUB":
        return "other", "other/substituted-content-word"
    if span.op == "DEL" and ref and all(token in STOPWORDS for token in ref):
        return "other", "other/deleted-function-word"
    if span.op == "INS" and hyp and all(token in STOPWORDS for token in hyp):
        return "other", "other/inserted-function-word"
    if span.op == "DEL":
        return "other", "other/deleted-content-word"
    return "other", "other/inserted-content-word"


def semantic_impact(span: ErrorSpan, context: UtteranceContext) -> str:
    """``NONE`` / ``LOW`` / ``HIGH`` for the span's CONTENT alone -- the operator of
    the owner's point that WER weights every error the same.

    HIGH means a downstream agent would act differently: a number or value, a
    currency or percentage, a negation, or a named entity was changed or lost.
    LOW means ordinary wording moved. NONE means nothing a task consumes moved.
    The category ruling in :data:`IMPACT_NEUTRAL_CATEGORIES` is applied on TOP of
    this, by the caller, so that both readings stay available.
    """

    changed = tuple(span.ref_tokens) + tuple(span.hyp_tokens)
    if any(_DIGIT_RE.search(token) for token in changed):
        return "HIGH"
    if any(token in NEGATIONS for token in changed):
        return "HIGH"
    if any(token in context.entity_forms for token in changed):
        return "HIGH"
    if any(token not in STOPWORDS for token in changed):
        return "LOW"
    return "NONE"


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ScoredSpan:
    """One classified span. ``content_impact`` is what the tokens themselves say;
    ``impact`` is that reading after the category ruling of
    :data:`IMPACT_NEUTRAL_CATEGORIES`. Both are kept so the strict variant of the
    agentic error rate can be computed without re-running the scan."""

    sample_id: str
    call: str
    category: str
    rule: str
    content_impact: str
    impact: str
    span: ErrorSpan


def scan_arm(
    contexts: Mapping[str, UtteranceContext],
    *,
    order: Sequence[str],
) -> tuple[SpanAlignment, list[ScoredSpan]]:
    """Align, classify and impact-tag every utterance of one arm."""

    substitutions = deletions = insertions = reference_words = hypothesis_words = 0
    scored: list[ScoredSpan] = []
    for sample_id in order:
        context = contexts[sample_id]
        alignment = align_spans(context.ref_tokens, context.hyp_tokens)
        substitutions += alignment.substitutions
        deletions += alignment.deletions
        insertions += alignment.insertions
        reference_words += alignment.reference_length
        hypothesis_words += alignment.hypothesis_length
        for span in alignment.spans:
            category, rule = classify_span(span, context)
            content = semantic_impact(span, context)
            scored.append(
                ScoredSpan(
                    sample_id=sample_id,
                    call=context.call,
                    category=category,
                    rule=rule,
                    content_impact=content,
                    impact="NONE"
                    if category in IMPACT_NEUTRAL_CATEGORIES or rule in IMPACT_NEUTRAL_RULES
                    else content,
                    span=span,
                )
            )
    return (
        SpanAlignment(
            substitutions=substitutions,
            deletions=deletions,
            insertions=insertions,
            reference_length=reference_words,
            hypothesis_length=hypothesis_words,
            spans=(),
        ),
        scored,
    )


def raw_format_only(contexts: Mapping[str, UtteranceContext], order: Sequence[str]) -> dict[str, int]:
    """The RAW-text pass: how much of the raw error mass the Whisper normalizer folds.

    A raw span whose two sides normalize to the same string is ``format-only``.
    This is the measurement behind the owner's *"twenty twenty two"* vs *"2022"*
    example, and it is already spent on the paper-facing number.
    """

    totals = {
        "raw_errors": 0,
        "raw_error_spans": 0,
        "raw_reference_words": 0,
        "format_only_spans": 0,
        "format_only_errors": 0,
    }
    for sample_id in order:
        context = contexts[sample_id]
        ref = raw_tokens(context.raw_reference)
        hyp = raw_tokens(context.raw_hypothesis)
        alignment = align_spans(ref, hyp)
        totals["raw_errors"] += alignment.errors
        totals["raw_reference_words"] += alignment.reference_length
        for span in alignment.spans:
            weight = max(len(span.ref_tokens), len(span.hyp_tokens))
            totals["raw_error_spans"] += 1
            if _normalizes_equal(span.ref_tokens, span.hyp_tokens):
                totals["format_only_spans"] += 1
                totals["format_only_errors"] += weight
    return totals


def stratified_sample(
    scored: Sequence[ScoredSpan],
    *,
    seed: int = READ_SAMPLE_SEED,
    size: int = READ_SAMPLE_SIZE,
) -> list[ScoredSpan]:
    """A deterministic, call-stratified draw of error spans for the human read.

    Allocation is proportional to each call's span count with the remainder
    handed out by descending count then call id, so the draw is a pure function
    of ``(scored, seed, size)``.
    """

    by_call: dict[str, list[ScoredSpan]] = defaultdict(list)
    for item in scored:
        by_call[item.call].append(item)
    total = len(scored)
    if total <= size:
        return list(scored)
    quotas: dict[str, int] = {}
    for call, items in by_call.items():
        quotas[call] = min(len(items), size * len(items) // total)
    remainder = size - sum(quotas.values())
    for call in sorted(by_call, key=lambda name: (-len(by_call[name]), name)):
        if remainder <= 0:
            break
        if quotas[call] < len(by_call[call]):
            quotas[call] += 1
            remainder -= 1
    drawn: list[ScoredSpan] = []
    for call in sorted(by_call):
        rng = random.Random(f"{seed}:{call}")
        pool = sorted(by_call[call], key=lambda item: (item.sample_id, item.span.key))
        drawn.extend(rng.sample(pool, quotas[call]))
    return sorted(drawn, key=lambda item: (item.call, item.sample_id, item.span.key))


def agentic_error_rate(
    scored: Sequence[ScoredSpan],
    reference_words: int,
    *,
    neutral_categories: frozenset[str] = IMPACT_NEUTRAL_CATEGORIES,
) -> dict[str, float | int]:
    """HIGH-impact reference-word mass over reference words, beside the WER.

    A HIGH substitution or deletion charges the reference tokens it covers; a
    HIGH insertion charges one reference-word-equivalent at its anchor. The
    denominator is the same 103,423 reference words the corpus WER uses, so the
    two numbers are directly comparable, point for point.
    """

    charge = 0
    high = 0
    for item in scored:
        neutral = item.category in neutral_categories or item.rule in IMPACT_NEUTRAL_RULES
        impact = "NONE" if neutral else item.content_impact
        if impact != "HIGH":
            continue
        high += 1
        charge += item.span.reference_word_charge
    return {
        "high_impact_spans": high,
        "high_impact_reference_word_mass": charge,
        "reference_words": reference_words,
        "agentic_error_rate_percent": round(100.0 * charge / reference_words, 4)
        if reference_words
        else 0.0,
    }


def _mass(span: ErrorSpan) -> int:
    """Error operations this span carries -- the WER numerator it owns."""

    if span.op == "SUB":
        return len(span.ref_tokens)
    if span.op == "DEL":
        return len(span.ref_tokens)
    return len(span.hyp_tokens)


def category_table(scored: Sequence[ScoredSpan], reference_words: int) -> list[dict[str, object]]:
    """Per-category span count, error mass, share of errors and WER points."""

    spans: Counter[str] = Counter()
    mass: Counter[str] = Counter()
    impacts: dict[str, Counter[str]] = {name: Counter() for name in CATEGORIES}
    for item in scored:
        spans[item.category] += 1
        mass[item.category] += _mass(item.span)
        impacts[item.category][item.impact] += 1
    total_mass = sum(mass.values())
    rows: list[dict[str, object]] = []
    for name in CATEGORIES:
        rows.append(
            {
                "category": name,
                "spans": spans[name],
                "error_mass": mass[name],
                "share_of_error_mass_percent": round(100.0 * mass[name] / total_mass, 3)
                if total_mass
                else 0.0,
                "wer_points": round(100.0 * mass[name] / reference_words, 4)
                if reference_words
                else 0.0,
                "impact_NONE": impacts[name]["NONE"],
                "impact_LOW": impacts[name]["LOW"],
                "impact_HIGH": impacts[name]["HIGH"],
            }
        )
    return rows


def rule_table(scored: Sequence[ScoredSpan], reference_words: int) -> list[dict[str, object]]:
    spans: Counter[str] = Counter()
    mass: Counter[str] = Counter()
    for item in scored:
        spans[item.rule] += 1
        mass[item.rule] += _mass(item.span)
    return [
        {
            "rule": rule,
            "category": rule.split("/")[0],
            "spans": spans[rule],
            "error_mass": mass[rule],
            "wer_points": round(100.0 * mass[rule] / reference_words, 4) if reference_words else 0.0,
        }
        for rule in sorted(spans, key=lambda name: (-mass[name], name))
    ]


def impact_table(scored: Sequence[ScoredSpan], reference_words: int) -> dict[str, object]:
    mass: Counter[str] = Counter()
    spans: Counter[str] = Counter()
    for item in scored:
        mass[item.impact] += _mass(item.span)
        spans[item.impact] += 1
    total = sum(mass.values())
    return {
        impact: {
            "spans": spans[impact],
            "error_mass": mass[impact],
            "share_of_error_mass_percent": round(100.0 * mass[impact] / total, 3) if total else 0.0,
            "wer_points": round(100.0 * mass[impact] / reference_words, 4) if reference_words else 0.0,
        }
        for impact in IMPACTS
    }


def per_call_table(
    scored: Sequence[ScoredSpan],
    contexts: Mapping[str, UtteranceContext],
    order: Sequence[str],
) -> list[dict[str, object]]:
    words: Counter[str] = Counter()
    for sample_id in order:
        context = contexts[sample_id]
        words[context.call] += len(context.ref_tokens)
    mass: dict[str, Counter[str]] = defaultdict(Counter)
    high: Counter[str] = Counter()
    for item in scored:
        mass[item.call][item.category] += _mass(item.span)
        if item.impact == "HIGH":
            high[item.call] += item.span.reference_word_charge
    rows: list[dict[str, object]] = []
    for call in sorted(words):
        reference_words = words[call]
        total = sum(mass[call].values())
        row: dict[str, object] = {
            "call": call,
            "reference_words": reference_words,
            "error_mass": total,
            "corpus_wer_percent": round(100.0 * total / reference_words, 4) if reference_words else 0.0,
            "agentic_error_rate_percent": round(100.0 * high[call] / reference_words, 4)
            if reference_words
            else 0.0,
        }
        for name in CATEGORIES:
            row[f"points_{name}"] = (
                round(100.0 * mass[call][name] / reference_words, 4) if reference_words else 0.0
            )
        rows.append(row)
    return rows


DURATION_BUCKETS = ((0.0, 1.0), (1.0, 2.0), (2.0, 4.0), (4.0, 8.0), (8.0, 16.0), (16.0, 1e9))


def per_duration_table(
    scored: Sequence[ScoredSpan],
    contexts: Mapping[str, UtteranceContext],
    order: Sequence[str],
) -> list[dict[str, object]]:
    def bucket_of(seconds: float) -> str:
        for low, high in DURATION_BUCKETS:
            if low <= seconds < high:
                return f"{low:g}-{high:g}s" if high < 1e8 else f"{low:g}s+"
        return "unbucketed"

    words: Counter[str] = Counter()
    rows_seen: Counter[str] = Counter()
    for sample_id in order:
        context = contexts[sample_id]
        words[bucket_of(context.duration_s)] += len(context.ref_tokens)
        rows_seen[bucket_of(context.duration_s)] += 1
    mass: dict[str, Counter[str]] = defaultdict(Counter)
    for item in scored:
        bucket = bucket_of(contexts[item.sample_id].duration_s)
        mass[bucket][item.category] += _mass(item.span)
    table: list[dict[str, object]] = []
    for low, high in DURATION_BUCKETS:
        bucket = f"{low:g}-{high:g}s" if high < 1e8 else f"{low:g}s+"
        reference_words = words[bucket]
        total = sum(mass[bucket].values())
        row: dict[str, object] = {
            "bucket": bucket,
            "utterances": rows_seen[bucket],
            "reference_words": reference_words,
            "corpus_wer_percent": round(100.0 * total / reference_words, 4) if reference_words else 0.0,
        }
        for name in CATEGORIES:
            row[f"points_{name}"] = (
                round(100.0 * mass[bucket][name] / reference_words, 4) if reference_words else 0.0
            )
        table.append(row)
    return table


def boundary_diagnostics(
    scored: Sequence[ScoredSpan], contexts: Mapping[str, UtteranceContext]
) -> dict[str, object]:
    """How much of the over-generation is the NEIGHBOURING utterance's own words.

    The tail insertions are the largest single block of error mass on every arm.
    This asks the segment table, not a judgement, how many of them the next
    published utterance's reference already contains: a run that the neighbour
    carries is speech the clip boundary cut, not speech the core invented.
    """

    report: dict[str, object] = {}
    for side, matcher in (("tail", "next"), ("head", "previous")):
        spans = 0
        mass = 0
        buckets = {"contains_0.6_or_more": 0, "contains_0.34_to_0.6": 0, "contains_some": 0, "contains_none": 0}
        matched_mass = 0
        for item in scored:
            span = item.span
            if span.op != "INS":
                continue
            context = contexts[item.sample_id]
            if side == "tail" and span.hyp_end != len(context.hyp_tokens):
                continue
            if side == "head" and span.hyp_start != 0:
                continue
            neighbour = context.next_tokens if matcher == "next" else context.previous_tokens
            share = _contained_in_neighbour(span.hyp_tokens, neighbour)
            spans += 1
            mass += len(span.hyp_tokens)
            if share >= 0.6:
                buckets["contains_0.6_or_more"] += 1
                matched_mass += len(span.hyp_tokens)
            elif share >= 0.34:
                buckets["contains_0.34_to_0.6"] += 1
            elif share > 0:
                buckets["contains_some"] += 1
            else:
                buckets["contains_none"] += 1
        report[side] = {
            "insertion_spans": spans,
            "inserted_words": mass,
            "words_matched_at_0.6": matched_mass,
            "spans_by_containment": buckets,
        }
    return report


def top_patterns(scored: Sequence[ScoredSpan], *, limit: int = 20) -> list[dict[str, object]]:
    """The most frequent literal (reference -> hypothesis) rewrites, with examples."""

    counter: Counter[tuple[str, str, str, str]] = Counter()
    examples: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    for item in scored:
        key = (item.span.op, item.rule, item.span.ref_text, item.span.hyp_text)
        counter[key] += 1
        if len(examples[key]) < 3:
            examples[key].append(item.sample_id)
    rows: list[dict[str, object]] = []
    for (op, rule, ref_text, hyp_text), count in counter.most_common(limit):
        rows.append(
            {
                "op": op,
                "rule": rule,
                "reference": ref_text,
                "hypothesis": hyp_text,
                "occurrences": count,
                "example_sample_ids": examples[(op, rule, ref_text, hyp_text)],
            }
        )
    return rows


# ---------------------------------------------------------------------------
# The four-bin gap estimate
# ---------------------------------------------------------------------------

#: Which rule goes into which of the owner's four bins, and the AUTHORITY that
#: licenses a fold where one exists. A bin entry without an authority is not a
#: fold: it is a statement about what the number is made of.
GAP_BINS: Mapping[str, tuple[str, ...]] = {
    "scoring-convention": (
        "format-convention/merge-compound",
        "format-convention/symbol-only",
        "format-convention/stray-punctuation-token",
        "format-convention/whisper-refold",
        "format-convention/numeric-equal",
        "reference-convention/empty-reference",
    ),
    "missing-pre-meeting-context": (
        "named-entity/call-inventory",
        "domain-term/pinned-lexicon",
    ),
    "core-capability": (
        "acoustic-misrecognition/string-near",
        "model-behaviour/non-english-script",
        "model-behaviour/hypothesis-loop",
        "model-behaviour/truncation",
        "model-behaviour/hypothesis-repetition",
        "other/substituted-content-word",
        "other/deleted-content-word",
        "other/inserted-content-word",
    ),
    "task-definition": (
        "reference-convention/redacted-region",
        "reference-convention/false-start-stem",
        "reference-convention/reference-repetition",
        "reference-convention/filler-token",
        "reference-convention/discourse-phrase",
        "reference-convention/discourse-single",
        "reference-convention/backchannel-variant",
        "segmentation-artifact/neighbour-bleed",
        "segmentation-artifact/boundary-continuation",
        "segmentation-artifact/boundary-onset",
        "segmentation-artifact/boundary-partial-word",
        "model-behaviour/runaway-tail",
        "model-behaviour/runaway-head",
        "other/deleted-function-word",
        "other/inserted-function-word",
        "other/function-word-swap",
    ),
}

FOLD_AUTHORITIES: Mapping[str, str] = {
    "format-convention/merge-compound": (
        "Open ASR Leaderboard `merge_compounds`, which the published ESB column applies and "
        "this study does not"
    ),
    "format-convention/symbol-only": (
        "NO PUBLISHED AUTHORITY. The Whisper normalizer deliberately KEEPS `.%$` and the "
        "currency signs, so `$340` against `340` is a difference the recipe intends to "
        "preserve. Reported inside the scoring-convention bin so it can be subtracted, "
        "never claimed as an existing convention"
    ),
    "format-convention/stray-punctuation-token": (
        "NO PUBLISHED AUTHORITY, but no published recipe treats a token with zero "
        "alphanumeric characters as a word either: these are Rev's ellipsis marks surviving "
        "the normalizer as bare `.` / `..` tokens. Reported separately for the same reason"
    ),
    "format-convention/whisper-refold": (
        "the Whisper `EnglishTextNormalizer`'s own rules, applied a second time over the "
        "span in isolation"
    ),
    "format-convention/numeric-equal": (
        "the Whisper `EnglishTextNormalizer`'s number rules; the residue is digits that "
        "agree with a different surface form around them"
    ),
    "reference-convention/empty-reference": (
        "the ESB protocol: a reference that normalizes to nothing contributes no denominator, "
        "and the leaderboard's own recipe drops such rows"
    ),
}

REFUSED_FOLDS: Mapping[str, str] = {
    "reference-convention/false-start-stem": (
        "no published normalizer removes Rev's truncated-word stems; folding them would be "
        "this study inventing a convention to improve its own number"
    ),
    "reference-convention/reference-repetition": (
        "the 2026-09-05 A/B verdict already measured that collapsing repeats makes the number "
        "WORSE, and no ESB or leaderboard rule collapses them"
    ),
    "reference-convention/filler-token": (
        "the Whisper normalizer's filler list is exactly hmm|mm|mhm|mmm|uh|um; extending it is "
        "a new convention, not an existing one"
    ),
    "reference-convention/discourse-phrase": (
        "no authority removes 'you know' / 'I mean' from a reference"
    ),
    "reference-convention/discourse-single": (
        "these tokens are ordinary words as often as they are fillers; folding them would "
        "silently delete content"
    ),
    "segmentation-artifact/neighbour-bleed": (
        "the ESB protocol scores each published utterance against its own sentence; crediting a "
        "neighbour's words would change the task, not the scoring"
    ),
}


#: The one bin member that a PUBLISHED recipe already folds. Everything else in
#: ``scoring-convention`` is a proposal this scan reports so it can be subtracted,
#: never a number the study may claim.
AUTHORIZED_FOLD_RULES = ("format-convention/merge-compound",)


def gap_bins(scored: Sequence[ScoredSpan], reference_words: int) -> dict[str, object]:
    mass: Counter[str] = Counter()
    for item in scored:
        mass[item.rule] += _mass(item.span)
    assigned = {rule for rules in GAP_BINS.values() for rule in rules}
    unassigned = sorted(set(mass) - assigned)
    authorized = sum(mass[rule] for rule in AUTHORIZED_FOLD_RULES)
    bins: dict[str, object] = {}
    for name, rules in GAP_BINS.items():
        total = sum(mass[rule] for rule in rules)
        bins[name] = {
            "rules": list(rules),
            "error_mass": total,
            "wer_points": round(100.0 * total / reference_words, 4) if reference_words else 0.0,
            "share_of_error_mass_percent": round(100.0 * total / sum(mass.values()), 3)
            if mass
            else 0.0,
        }
    return {
        "bins": bins,
        "unassigned_rules": unassigned,
        "unassigned_error_mass": sum(mass[rule] for rule in unassigned),
        "authorized_fold_rules": list(AUTHORIZED_FOLD_RULES),
        "authorized_fold_error_mass": authorized,
        "authorized_fold_wer_points": round(100.0 * authorized / reference_words, 4)
        if reference_words
        else 0.0,
        "fold_authorities": dict(FOLD_AUTHORITIES),
        "refused_folds": dict(REFUSED_FOLDS),
    }


# ---------------------------------------------------------------------------
# Inputs. Everything below reads sealed bytes only: the dev10 reference layer,
# the dev10 segment table, and the three sealed hypothesis files. The six ESB
# TEST calls are unreachable from here -- the reference loader is pinned to the
# dev10 receipt and the segment-table loader to the dev10 extracted table.
# ---------------------------------------------------------------------------

SEGMENT_TABLE_RECEIPT_RELPATH = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-05-e22-dev-esb-prompt-ab-v1/segment-table/segment-table-receipt.json"
)

ARM_SOURCES: Mapping[str, Mapping[str, str]] = {
    "A": {
        "run_id": "SAEA-E22-DEV-ESB-PROMPT-A-V1",
        "attempt": "attempt-20260905T073641Z-f977d1",
        "label": "this study's verbatim instruction, system message before the audio",
    },
    "B": {
        "run_id": "SAEA-E22-DEV-ESB-PROMPT-B-V1",
        "attempt": "attempt-20260905T080709Z-b77462",
        "label": "the Qwen3-Omni model-card ASR prompt, system message before the audio",
    },
    "C": {
        "run_id": "SAEA-E22-DEV-ESB-SHAPE-C-V1",
        "attempt": "attempt-20260905T094322Z-2174df",
        "label": "the official request shape, no system message, instruction after the audio",
    },
}

CARRIER_LOCK_KEY = "earnings22-original"
NEIGHBOUR_SEPARATOR = "\x00"


class TaxonomyError(RuntimeError):
    """An input is missing, has drifted from its committed hash, or the aligner
    failed to reproduce the sealed totals."""


def outputs_path(root: "Path", arm: str) -> "Path":
    source = ARM_SOURCES[arm]
    run_id = source["run_id"]
    return Path(root) / "runs" / run_id / source["attempt"] / f"{run_id}.outputs.jsonl"


def load_segment_table(
    root: "Path",
    repo_root: "Path",
    *,
    receipt_relpath: str = SEGMENT_TABLE_RECEIPT_RELPATH,
) -> dict[str, dict[str, object]]:
    """One segment table, re-hashed against its committed receipt on every load.

    The default is the dev10 table every existing caller reads. A caller whose
    population is a different ESB split names that split's own committed receipt
    instead -- the loader is unchanged, the receipt it verifies against is the
    argument -- so a population never silently borrows another split's
    boundaries.
    """

    receipt_path = Path(repo_root) / receipt_relpath
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    table = receipt["extracted_table"]
    path = Path(root) / str(table["relpath"])
    payload = path.read_bytes()
    measured = hashlib.sha256(payload).hexdigest()
    if measured != table["sha256"]:
        raise TaxonomyError(
            f"segment table identity drift: the receipt pins {str(table['sha256'])[:12]}..., "
            f"{path} now hashes to {measured[:12]}..."
        )
    rows: dict[str, dict[str, object]] = {}
    for line in payload.decode("utf-8").split("\n"):
        if not line.strip():
            continue
        row = json.loads(line)
        rows[str(row["id"])] = row
    if len(rows) != int(table["rows"]):
        raise TaxonomyError(
            f"segment table holds {len(rows)} rows, the receipt pins {table['rows']}"
        )
    return rows


def load_hypotheses(path: "Path") -> dict[str, str]:
    """``{sample_id -> hypothesis text}`` from one sealed outputs file."""

    hypotheses: dict[str, str] = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").split("\n"), start=1):
        if not line:
            continue
        row = json.loads(line)
        if row.get("carrier_lock_key") != CARRIER_LOCK_KEY:
            raise TaxonomyError(
                f"{path} line {number} names carrier {row.get('carrier_lock_key')!r}"
            )
        sample_id = row["sample_id"]
        if sample_id in hypotheses:
            raise TaxonomyError(f"{path} line {number} repeats sample {sample_id!r}")
        hypotheses[sample_id] = str(row["text"])
    if not hypotheses:
        raise TaxonomyError(f"{path} carries no rows")
    return hypotheses


def build_contexts(
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
    hypotheses: Mapping[str, str],
    entity_inventory: Mapping[str, frozenset[str]],
) -> dict[str, UtteranceContext]:
    """One :class:`UtteranceContext` per sealed row, neighbours resolved by segment id."""

    by_position: dict[tuple[str, int], str] = {}
    for sample_id, row in segments.items():
        by_position[(str(row["source_id"]), int(str(row["segment_id"])))] = sample_id

    contexts: dict[str, UtteranceContext] = {}
    for sample_id, hypothesis in hypotheses.items():
        row = segments[sample_id]
        call = str(row["source_id"])
        position = int(str(row["segment_id"]))
        reference = references[sample_id]
        neighbours: dict[int, tuple[str, ...]] = {}
        for step in (-1, 1):
            neighbour_id = by_position.get((call, position + step))
            neighbours[step] = (
                normalized_tokens(references[neighbour_id]) if neighbour_id is not None else ()
            )
        contexts[sample_id] = UtteranceContext(
            sample_id=sample_id,
            call=call,
            raw_reference=reference,
            raw_hypothesis=hypothesis,
            ref_tokens=normalized_tokens(reference),
            hyp_tokens=normalized_tokens(hypothesis),
            duration_s=float(row["end_ts"]) - float(row["start_ts"]),
            stems=truncation_stems(reference),
            tag_anchors=tag_anchor_indices(reference),
            previous_tokens=neighbours[-1],
            next_tokens=neighbours[1],
            entity_forms=entity_inventory[call],
        )
    return contexts


# ---------------------------------------------------------------------------
# Receipts
# ---------------------------------------------------------------------------


def reference_layer_profile(
    references: Mapping[str, str], contexts: Mapping[str, UtteranceContext]
) -> dict[str, object]:
    """What KIND of transcript the references are, counted rather than assumed.

    The 2026-09-05 shape-C verdict named "Rev's cleaned sentence transcript" as
    the leading suspect. The layer is not cleaned: it is close to verbatim, and
    the difference matters, because a verbatim reference carries disfluency the
    Whisper normalizer removes from BOTH sides (so it costs nothing) alongside
    repetition and truncation it removes from NEITHER (so it costs the model
    every time).
    """

    filler_tokens = Counter()
    tag_counts: Counter[str] = Counter()
    rows_with_tag = 0
    rows_with_stem = 0
    stems = 0
    rows_with_adjacent_repeat = 0
    adjacent_repeats = 0
    for sample_id, sentence in references.items():
        lowered = sentence.lower()
        for token in re.findall(r"\b(?:um|uh|hmm|mm|mhm|mmm)\b", lowered):
            filler_tokens[token] += 1
        tags = _TAG_RE.findall(sentence)
        if tags:
            rows_with_tag += 1
        for tag in tags:
            tag_counts[tag.lower()] += 1
        found = truncation_stems(sentence)
        if found:
            rows_with_stem += 1
            stems += len(found)
        tokens = contexts[sample_id].ref_tokens
        repeats = sum(1 for index in range(1, len(tokens)) if tokens[index] == tokens[index - 1])
        if repeats:
            rows_with_adjacent_repeat += 1
        adjacent_repeats += repeats
    return {
        "rows": len(references),
        "whisper_deleted_filler_tokens": dict(filler_tokens.most_common()),
        "whisper_deleted_filler_total": sum(filler_tokens.values()),
        "rows_carrying_a_bracket_tag": rows_with_tag,
        "bracket_tags": dict(tag_counts.most_common(12)),
        "rows_carrying_a_truncated_word": rows_with_stem,
        "truncated_word_forms": stems,
        "rows_with_an_adjacent_repeated_word": rows_with_adjacent_repeat,
        "adjacent_repeated_words_after_normalization": adjacent_repeats,
        "reading": (
            "verbatim, not cleaned: the layer carries speaker disfluency, immediate "
            "repetition, truncated words and redaction tags. The normalizer removes the "
            "fillers and the tags from both sides; it removes neither the repetitions nor "
            "the truncation stems, and no model will ever emit those"
        ),
    }


def rule_examples(
    drawn: Sequence[ScoredSpan], *, per_rule: int = 4, quote_tokens: int = 12
) -> dict[str, list[dict[str, object]]]:
    """Short dev-text examples per rule, taken from the committed read sample only."""

    examples: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in sorted(drawn, key=lambda entry: (entry.rule, entry.sample_id, entry.span.key)):
        if len(examples[item.rule]) >= per_rule:
            continue
        span = item.span
        examples[item.rule].append(
            {
                "sample_id": item.sample_id,
                "op": span.op,
                "impact": item.impact,
                "reference": " ".join(span.ref_tokens[:quote_tokens]),
                "hypothesis": " ".join(span.hyp_tokens[:quote_tokens]),
                "reference_context": " ".join(span.ref_left[-4:] + ("[[",) + span.ref_tokens[:quote_tokens] + ("]]",) + span.ref_right[:4]),
            }
        )
    return dict(examples)


def build_receipts(
    *,
    repo_root: "Path",
    root: "Path",
    references: Mapping[str, str],
    segments: Mapping[str, Mapping[str, object]],
    outbound_attempts: int,
    outbound_targets: Sequence[str],
) -> tuple[dict[str, object], str, dict[str, object]]:
    """``(summary, per-arm tables markdown, read-sample document)``.

    Refuses to return anything if the aligner does not reproduce every sealed
    S/D/I total exactly: a taxonomy over a different alignment than the verdict
    scored would be a different experiment wearing this one's name.
    """

    raw_by_call: dict[str, list[str]] = defaultdict(list)
    for sample_id, sentence in references.items():
        raw_by_call[str(segments[sample_id]["source_id"])].append(sentence)
    entity_inventory = build_entity_inventory(raw_by_call)

    arms: dict[str, object] = {}
    read_sample: dict[str, object] = {}
    profile: dict[str, object] = {}
    for arm in sorted(ARM_SOURCES):
        path = outputs_path(root, arm)
        hypotheses = load_hypotheses(path)
        contexts = build_contexts(references, segments, hypotheses, entity_inventory)
        order = sorted(contexts)
        if not profile:
            profile = reference_layer_profile(references, contexts)
        totals, scored = scan_arm(contexts, order=order)
        sealed = SEALED_TOTALS[arm]
        measured = {
            "substitutions": totals.substitutions,
            "deletions": totals.deletions,
            "insertions": totals.insertions,
            "reference_words": totals.reference_length,
        }
        if measured != dict(sealed):
            raise TaxonomyError(
                f"identity gate FAILED for arm {arm}: measured {measured}, sealed {dict(sealed)}"
            )
        reference_words = totals.reference_length
        drawn = stratified_sample(scored)
        arms[arm] = {
            "run_id": ARM_SOURCES[arm]["run_id"],
            "attempt": ARM_SOURCES[arm]["attempt"],
            "label": ARM_SOURCES[arm]["label"],
            "outputs_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "utterances": len(order),
            "identity_gate": {"measured": measured, "sealed": dict(sealed), "reproduced": True},
            "corpus_wer_percent": round(100.0 * totals.errors / reference_words, 4),
            "hypothesis_words": totals.hypothesis_length,
            "hypothesis_over_reference_ratio": round(
                totals.hypothesis_length / reference_words, 4
            ),
            "error_spans": len(scored),
            "category_table": category_table(scored, reference_words),
            "rule_table": rule_table(scored, reference_words),
            "impact_table": impact_table(scored, reference_words),
            "agentic_error_rate": agentic_error_rate(scored, reference_words),
            "agentic_error_rate_strict": agentic_error_rate(
                scored,
                reference_words,
                neutral_categories=frozenset({"format-convention", "reference-convention"}),
            ),
            "per_call_table": per_call_table(scored, contexts, order),
            "per_duration_table": per_duration_table(scored, contexts, order),
            "top_patterns": top_patterns(scored),
            "boundary_diagnostics": boundary_diagnostics(scored, contexts),
            "gap_bins": gap_bins(scored, reference_words),
            "raw_pass": raw_format_only(contexts, order),
            "read_sample": {
                "seed": READ_SAMPLE_SEED,
                "requested": READ_SAMPLE_SIZE,
                "drawn": len(drawn),
                "strata": "source call",
                "composition_by_rule": dict(Counter(item.rule for item in drawn)),
            },
            "read_sample_examples": rule_examples(drawn),
        }
        read_sample[arm] = [
            {
                "sample_id": item.sample_id,
                "call": item.call,
                "op": item.span.op,
                "ref_start": item.span.ref_start,
                "hyp_start": item.span.hyp_start,
                "category": item.category,
                "rule": item.rule,
                "impact": item.impact,
            }
            for item in drawn
        ]

    summary = {
        "schema": "saea-e22-semantic-error-scan-summary-v1",
        "taxonomy_version": TAXONOMY_VERSION,
        "exposure_row": EXPOSURE_ROW_ID,
        "study": "speech-aware-evidence-acquisition",
        "carrier": CARRIER_LOCK_KEY,
        "split_name": "E22-ESB-DEV10-UTTERANCES",
        "split_role": "dev",
        "normalizer": WHISPER_NORMALIZER_NAME,
        "contacts": {
            "model": 0,
            "tokenizer": 0,
            "embedder": 0,
            "network_attempts": outbound_attempts,
            "network_targets": list(outbound_targets),
            "gpu": 0,
            "audio_decode": 0,
        },
        "test_split_read": False,
        "categories": list(CATEGORIES),
        "impacts": list(IMPACTS),
        "impact_neutral_categories": sorted(IMPACT_NEUTRAL_CATEGORIES),
        "lexicons": {
            "nonlexical_fillers": sorted(NONLEXICAL_FILLERS),
            "discourse_phrases": [" ".join(phrase) for phrase in DISCOURSE_PHRASES],
            "discourse_singles": sorted(DISCOURSE_SINGLES),
            "domain_terms": sorted(DOMAIN_TERMS),
            "negations": sorted(NEGATIONS),
            "stopwords": sorted(STOPWORDS),
        },
        "reference_layer_profile": profile,
        "entity_inventory_sizes": {
            call: len(forms) for call, forms in sorted(entity_inventory.items())
        },
        "agentic_error_rate_definition": (
            "HIGH-impact reference-word mass over total reference words. A HIGH substitution "
            "or deletion charges the reference tokens it covers; a HIGH insertion charges one "
            "reference-word-equivalent at its anchor. Same denominator as the corpus WER, so "
            "the two are comparable point for point. Spans classified format-convention, "
            "reference-convention or segmentation-artifact are NONE by ruling; the strict "
            "variant re-admits segmentation-artifact."
        ),
        "arms": arms,
    }
    return summary, render_tables(summary), {
        "schema": "saea-e22-semantic-error-scan-read-sample-v1",
        "seed": READ_SAMPLE_SEED,
        "size_per_arm": READ_SAMPLE_SIZE,
        "strata": "source call",
        "arms": read_sample,
    }


def _md_table(headers: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(lines)


def render_tables(summary: Mapping[str, object]) -> str:
    """The per-arm tables, as committed Markdown beside the JSON."""

    arms = summary["arms"]
    assert isinstance(arms, Mapping)
    parts = [
        "# Earnings-22 DEV semantic error scan -- per-arm tables",
        "",
        f"Taxonomy `{summary['taxonomy_version']}`, normalizer `{summary['normalizer']}`, "
        f"exposure row `{summary['exposure_row']}`. Dev split only; the six ESB test calls "
        "are not read.",
        "",
    ]
    for arm in sorted(arms):
        block = arms[arm]
        assert isinstance(block, Mapping)
        parts.append(f"## Arm {arm} -- {block['label']}")
        parts.append("")
        parts.append(
            f"Corpus WER {block['corpus_wer_percent']} %, "
            f"{block['error_spans']} error spans, identity gate reproduced: "
            f"{block['identity_gate']['reproduced']}."
        )
        parts.append("")
        parts.append("### Category mass")
        parts.append("")
        parts.append(
            _md_table(
                ["category", "spans", "error mass", "share %", "WER points", "NONE", "LOW", "HIGH"],
                [
                    [
                        row["category"],
                        row["spans"],
                        row["error_mass"],
                        row["share_of_error_mass_percent"],
                        row["wer_points"],
                        row["impact_NONE"],
                        row["impact_LOW"],
                        row["impact_HIGH"],
                    ]
                    for row in block["category_table"]
                ],
            )
        )
        parts.append("")
        parts.append("### Rule mass")
        parts.append("")
        parts.append(
            _md_table(
                ["rule", "spans", "error mass", "WER points"],
                [
                    [row["rule"], row["spans"], row["error_mass"], row["wer_points"]]
                    for row in block["rule_table"]
                ],
            )
        )
        parts.append("")
        parts.append("### Semantic impact")
        parts.append("")
        parts.append(
            _md_table(
                ["impact", "spans", "error mass", "share %", "WER points"],
                [
                    [
                        impact,
                        block["impact_table"][impact]["spans"],
                        block["impact_table"][impact]["error_mass"],
                        block["impact_table"][impact]["share_of_error_mass_percent"],
                        block["impact_table"][impact]["wer_points"],
                    ]
                    for impact in IMPACTS
                ],
            )
        )
        parts.append("")
        parts.append("### Per call")
        parts.append("")
        parts.append(
            _md_table(
                ["call", "ref words", "corpus WER %", "agentic error rate %"]
                + [f"pts {name}" for name in CATEGORIES],
                [
                    [
                        row["call"],
                        row["reference_words"],
                        row["corpus_wer_percent"],
                        row["agentic_error_rate_percent"],
                    ]
                    + [row[f"points_{name}"] for name in CATEGORIES]
                    for row in block["per_call_table"]
                ],
            )
        )
        parts.append("")
        parts.append("### Per clip duration")
        parts.append("")
        parts.append(
            _md_table(
                ["bucket", "utterances", "ref words", "corpus WER %"]
                + [f"pts {name}" for name in CATEGORIES],
                [
                    [
                        row["bucket"],
                        row["utterances"],
                        row["reference_words"],
                        row["corpus_wer_percent"],
                    ]
                    + [row[f"points_{name}"] for name in CATEGORIES]
                    for row in block["per_duration_table"]
                ],
            )
        )
        parts.append("")
        parts.append("### Four-bin gap estimate")
        parts.append("")
        parts.append(
            _md_table(
                ["bin", "error mass", "share %", "WER points"],
                [
                    [
                        name,
                        values["error_mass"],
                        values["share_of_error_mass_percent"],
                        values["wer_points"],
                    ]
                    for name, values in block["gap_bins"]["bins"].items()
                ],
            )
        )
        parts.append("")
    return "\n".join(parts) + "\n"


__all__ = [
    "ARM_SOURCES",
    "CARRIER_LOCK_KEY",
    "SEGMENT_TABLE_RECEIPT_RELPATH",
    "TaxonomyError",
    "build_contexts",
    "build_receipts",
    "load_hypotheses",
    "load_segment_table",
    "outputs_path",
    "render_tables",
    "rule_examples",
    "reference_layer_profile",
    "ALL_RULES",
    "AUTHORIZED_FOLD_RULES",
    "BACKCHANNELS",
    "ENTITY_INVENTORY_EXCLUSIONS",
    "IMPACT_NEUTRAL_RULES",
    "NEGATIONS",
    "boundary_diagnostics",
    "CATEGORIES",
    "DISCOURSE_PHRASES",
    "DISCOURSE_SINGLES",
    "DOMAIN_TERMS",
    "ErrorSpan",
    "EXPOSURE_ROW_ID",
    "FOLD_AUTHORITIES",
    "GAP_BINS",
    "IMPACTS",
    "IMPACT_NEUTRAL_CATEGORIES",
    "NONLEXICAL_FILLERS",
    "READ_SAMPLE_SEED",
    "READ_SAMPLE_SIZE",
    "REFUSED_FOLDS",
    "SEALED_TOTALS",
    "STOPWORDS",
    "ScoredSpan",
    "SpanAlignment",
    "TAXONOMY_VERSION",
    "UtteranceContext",
    "WHISPER_NORMALIZER_NAME",
    "agentic_error_rate",
    "align_spans",
    "build_entity_inventory",
    "category_table",
    "classify_span",
    "gap_bins",
    "impact_table",
    "normalized_tokens",
    "per_call_table",
    "per_duration_table",
    "raw_format_only",
    "raw_tokens",
    "rule_table",
    "scan_arm",
    "semantic_impact",
    "stratified_sample",
    "tag_anchor_indices",
    "top_patterns",
    "truncation_stems",
]
