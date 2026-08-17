"""T-NDL library: deterministic number/date canonicalizer + alignment backtrace.

OFFLINE, MODEL-FREE. Used only for scoring-side decomposition of already-consumed
discovery traces (owner ruling D5 archival replay). Nothing here may ever be wired
into a runtime supply path.

Two capabilities the frozen scoring stack deliberately does NOT provide:

1. ``align_trace`` -- the frozen ``scoring.wer.align`` exposes only a per-reference
   boolean hit mask and "never a hypothesis-side backtrace, so this adapter has no
   way to name WHAT incorrect text a hypothesis substituted for a missed entity"
   (core/scorers.py docstring). We need exactly that text, so this module mirrors
   the frozen DP and its documented tie-break order (match/substitution, then
   deletion, then insertion) and additionally records the ref->hyp index map. The
   caller MUST assert the derived mask equals the frozen ``align()`` mask; that
   equality is the proof the mirror did not drift.

2. ``canonical_variants`` -- a writing-convention normalizer. The frozen
   ``normalize_text_v1`` is explicitly "no number expansion"; it also destroys the
   very characters that carry format ($ . % , -), so the format comparison is done
   on RAW text, never on v1-normalized tokens.
"""

from __future__ import annotations

import re
from decimal import Decimal
from itertools import product

# --------------------------------------------------------------------------
# 1. Alignment with a hypothesis-side backtrace
# --------------------------------------------------------------------------

MATCH, SUB, DEL = "match", "sub", "del"


def align_trace(ref, hyp):
    """Mirror of ``scoring.wer.align`` that also returns the ref->hyp index map.

    Returns ``(ref_to_hyp, ref_ops, hyp_aligned, mask)`` where ``ref_to_hyp[i]`` is
    the hypothesis index aligned to reference position ``i`` (``None`` for a
    deletion) and ``hyp_aligned[j]`` is False exactly for insertions.

    The cost matrix is filled with the SAME recurrence as the frozen aligner. The
    row update is vectorised with the standard prefix-minimum identity
    ``cost[i][j] = min_{k<=j} (d[k] + (j-k))`` where ``d[k] = min(diagonal,
    deletion)`` -- algebraically identical to the frozen serial
    ``min(d[j], cost[i][j-1] + 1)``, not an approximation.
    """
    import numpy as np

    n, m = len(ref), len(hyp)
    rows, cols = n + 1, m + 1
    cost = np.empty((rows, cols), dtype=np.int32)
    cost[0] = np.arange(cols, dtype=np.int32)
    if m:
        hyp_arr = np.array(hyp, dtype=object)
        arange = np.arange(cols, dtype=np.int32)
        for i in range(1, rows):
            prev = cost[i - 1]
            same = hyp_arr == ref[i - 1]
            diagonal = prev[:-1] + (~same).astype(np.int32)
            deletion = prev[1:] + 1
            d = np.empty(cols, dtype=np.int32)
            d[0] = i
            np.minimum(diagonal, deletion, out=d[1:])
            cost[i] = np.minimum.accumulate(d - arange) + arange
    else:
        for i in range(1, rows):
            cost[i][0] = i

    ref_to_hyp = [None] * n
    ref_ops = [None] * n
    hyp_aligned = [False] * m
    mask = [False] * n
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            equal = ref[i - 1] == hyp[j - 1]
            diagonal = int(cost[i - 1][j - 1]) + (0 if equal else 1)
            if int(cost[i][j]) == diagonal:
                ref_to_hyp[i - 1] = j - 1
                hyp_aligned[j - 1] = True
                if equal:
                    mask[i - 1] = True
                    ref_ops[i - 1] = MATCH
                else:
                    ref_ops[i - 1] = SUB
                i, j = i - 1, j - 1
                continue
        if i > 0 and int(cost[i][j]) == int(cost[i - 1][j]) + 1:
            ref_ops[i - 1] = DEL
            i -= 1
            continue
        j -= 1
    return ref_to_hyp, ref_ops, hyp_aligned, tuple(mask)


def chunk_offsets(raw_chunks, tokens_v1):
    """For each RAW whitespace chunk, the half-open ``[start, end)`` range it
    occupies in ``tokens_v1(" ".join(raw_chunks))``.

    Same construction (and same justification) as ``core.scorers.
    _normalized_span_offsets``: ``normalize_text_v1`` is per-character and
    whitespace-collapsing, so normalising chunk-by-chunk and concatenating equals
    normalising the joined string.
    """
    spans = []
    cursor = 0
    for chunk in raw_chunks:
        count = len(tokens_v1(chunk))
        spans.append((cursor, cursor + count))
        cursor += count
    return spans


def chunks_covering(spans, lo, hi):
    """Indices of raw chunks whose normalized range intersects ``[lo, hi]``."""
    return [k for k, (s, e) in enumerate(spans) if e > s and s <= hi and e > lo]


# --------------------------------------------------------------------------
# 2. Writing-convention canonicalizer
# --------------------------------------------------------------------------

ONES = {
    "zero": 0, "oh": 0, "nought": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {"hundred": 100, "thousand": 1000, "million": 10 ** 6,
          "billion": 10 ** 9, "trillion": 10 ** 12}
DIGIT_WORDS = {"zero", "oh", "nought", "one", "two", "three", "four", "five",
               "six", "seven", "eight", "nine"}
NUMWORDS = set(ONES) | set(TENS) | set(SCALES) | {"point"}

WORD_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
    "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
    "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
    "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
    "sixtieth": 60, "seventieth": 70, "eightieth": 80, "ninetieth": 90,
    "hundredth": 100,
}
MONTHS = {
    "jan": "january", "feb": "february", "mar": "march", "apr": "april",
    "may": "may", "jun": "june", "jul": "july", "aug": "august",
    "sep": "september", "sept": "september", "oct": "october",
    "nov": "november", "dec": "december",
}
MONTH_NUM = {name: index for index, name in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}

# magnitude letters glued to digits in written form: 53.2M / 6.5bn / 250k
SUFFIX_SCALE = {"k": "thousand", "m": "million", "mm": "million", "b": "billion",
                "bn": "billion", "t": "trillion", "tn": "trillion"}

CURRENCY = {"$": "#usd", "€": "#eur", "£": "#gbp", "¥": "#jpy"}
CURRENCY_WORDS = {"dollar": "#usd", "dollars": "#usd", "cent": "#cent",
                  "cents": "#cent", "euro": "#eur", "euros": "#eur",
                  "pound": "#gbp", "pounds": "#gbp"}
PCT_WORDS = {"percent", "percentage", "pct"}
MARKERS = {"#usd", "#eur", "#gbp", "#jpy", "#cent", "#pct"}

CONTRACTIONS = {
    "i'd": ("i", "would"), "i'll": ("i", "will"), "i'm": ("i", "am"),
    "i've": ("i", "have"), "we'll": ("we", "will"), "we're": ("we", "are"),
    "we've": ("we", "have"), "we'd": ("we", "would"), "they'll": ("they", "will"),
    "they're": ("they", "are"), "they've": ("they", "have"),
    "you'll": ("you", "will"), "you're": ("you", "are"), "you've": ("you", "have"),
    "it's": ("it", "is"), "that's": ("that", "is"), "there's": ("there", "is"),
    "he's": ("he", "is"), "she's": ("she", "is"), "what's": ("what", "is"),
    "let's": ("let", "us"), "don't": ("do", "not"), "doesn't": ("does", "not"),
    "didn't": ("did", "not"), "won't": ("will", "not"), "can't": ("can", "not"),
    "cannot": ("can", "not"), "couldn't": ("could", "not"),
    "wouldn't": ("would", "not"), "shouldn't": ("should", "not"),
    "isn't": ("is", "not"), "aren't": ("are", "not"), "wasn't": ("was", "not"),
    "weren't": ("were", "not"), "haven't": ("have", "not"),
    "hasn't": ("has", "not"), "hadn't": ("had", "not"), "we'd've": ("we", "would"),
}

STOPWORDS = {"the", "a", "an", "of", "and", "our", "this", "that", "in", "on",
             "at", "for", "to", "s"}

_DASHES = "‐‑‒–—―-"
_GLUED_SCALE = re.compile(r"^(\d+(?:\.\d+)?)(k|mm|m|bn|b|tn|t)$")


def _dec(value):
    """Render a Decimal in a canonical, trailing-zero-free form."""
    quantised = value.normalize()
    text = format(quantised, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def pre_tokenize(text):
    """Raw text -> flat list of atoms, preserving format-carrying characters.

    Deliberately NOT ``normalize_text_v1``: that function turns ``$``, ``.``,
    ``%`` and ``,`` into spaces, which is precisely the information the format
    question depends on.
    """
    import unicodedata

    s = unicodedata.normalize("NFKC", text).casefold()
    for ch in "‘’ʼ":
        s = s.replace(ch, "'")
    # contractions before punctuation stripping
    for src, dst in CONTRACTIONS.items():
        s = re.sub(r"\b" + re.escape(src) + r"\b", " " + " ".join(dst) + " ", s)
    for ch in CURRENCY:
        s = s.replace(ch, " " + CURRENCY[ch] + " ")
    s = s.replace("%", " #pct ")
    # thousands separators inside digit groups
    s = re.sub(r"(?<=\d),(?=\d\d\d(\D|$))", "", s)
    # Magnitude letter GLUED to the digits ("53.2m", "250k", "6.5bn") is a
    # written magnitude. The same letter separated by a dash or a space is NOT:
    # "10-K" and "8-K" are SEC form names, "ten K" is a spoken form name. Testing
    # a whole whitespace token also keeps "b2b" out (it does not full-match).
    s = " ".join(
        f"{_GLUED_SCALE.match(t).group(1)} #sc{_GLUED_SCALE.match(t).group(2)}"
        if _GLUED_SCALE.match(t) else t
        for t in s.split()
    )
    for ch in _DASHES:
        s = s.replace(ch, " ")
    # protect decimal points, drop every other period
    s = re.sub(r"(?<!\d)\.(?!\d)", " ", s)
    s = re.sub(r"(?<=\d)\.(?!\d)", " ", s)
    # split letter/digit boundaries (10-K -> 10 k, b2b -> b 2 b, 53m -> 53 m)
    s = re.sub(r"(?<=\d)(?=[a-z])", " ", s)
    s = re.sub(r"(?<=[a-z])(?=\d)", " ", s)
    # every surviving non-alnum, non-apostrophe, non-#, non-dot char -> space
    s = "".join(c if (c.isalnum() or c in "'#." or c.isspace()) else " " for c in s)
    atoms = [t for t in s.split() if t]
    # digit ordinals, re-joined AFTER the letter/digit split ("18th" -> "18","th")
    merged = []
    index = 0
    while index < len(atoms):
        if (index + 1 < len(atoms) and _NUM_RE.match(atoms[index])
                and "." not in atoms[index] and atoms[index + 1] in ("st", "nd", "rd", "th")):
            merged.append("#ord" + str(int(atoms[index])))
            index += 2
            continue
        merged.append(atoms[index])
        index += 1
    return merged


_NUM_RE = re.compile(r"^\d+(\.\d+)?$")
_ORD_RE = re.compile(r"^#ord(\d+)$")


def _parse_standard(words):
    """Standard English cardinal reading of a spelled number run.

    Returns a Decimal, or None if the run is not a well-formed cardinal.
    """
    total = Decimal(0)
    current = Decimal(0)
    seen = False
    index = 0
    while index < len(words):
        word = words[index]
        if word == "point":
            digits = []
            index += 1
            while index < len(words) and words[index] in DIGIT_WORDS:
                digits.append(str(ONES[words[index]]))
                index += 1
            if not digits or index != len(words):
                return None
            base = total + current
            return base + Decimal("0." + "".join(digits))
        if word in ONES:
            current += ONES[word]
            seen = True
        elif word in TENS:
            current += TENS[word]
            seen = True
        elif word == "hundred":
            current = (current if current else Decimal(1)) * 100
            seen = True
        elif word in SCALES:
            total += (current if current else Decimal(1)) * SCALES[word]
            current = Decimal(0)
            seen = True
        else:
            return None
        index += 1
    return (total + current) if seen else None


def _run_renderings(words, cap=6):
    """Every canonical rendering of one maximal spelled-number run.

    A set, not a single value: "twenty twenty" is 40 as a cardinal and 2020 as a
    year, and the gold annotation sometimes splits "5.1 million" into a CARDINAL
    mention "5.1" plus a separate mention "million" -- so the scale-word-detached
    reading must be offered too. Matching succeeds if ANY rendering agrees, i.e.
    "can this text be read as the same value under some standard convention?".
    """
    out = []

    # A run that is nothing but a bare scale word ("million", carried as its own
    # gold mention next to a "$6.5" mention) is the WORD, not the value 1e6.
    if len(words) == 1 and words[0] in SCALES:
        return [(words[0],)]

    standard = _parse_standard(words)
    if standard is not None:
        out.append((_dec(standard),))

    # scale word left detached: "five point one million" -> ("5.1", "million")
    if words and words[-1] in SCALES and words[-1] != "hundred":
        head = _parse_standard(words[:-1])
        if head is not None:
            out.append((_dec(head), words[-1]))

    # year-style concatenation: twenty twenty six -> 2026, nineteen ninety eight -> 1998
    for split in range(1, len(words)):
        left = _parse_standard(words[:split])
        right = _parse_standard(words[split:])
        if (left is not None and right is not None
                and left == left.to_integral_value() and right == right.to_integral_value()
                and 10 <= int(left) <= 99 and 0 <= int(right) <= 99):
            out.append((str(int(left) * 100 + int(right)),))

    # digit-string reading: "two zero two zero" -> 2020
    if words and all(w in DIGIT_WORDS for w in words):
        out.append(("".join(str(ONES[w]) for w in words),))

    # always keep the literal words as a fallback rendering
    out.append(tuple(words))

    seen, unique = set(), []
    for item in out:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique[:cap]


def _reorder_markers(tokens):
    """Move a currency marker that precedes its number to just after it, so that
    ``$53 million`` and ``53 million dollars`` reach the same canonical form."""
    out = list(tokens)
    index = 0
    while index < len(out) - 1:
        if out[index] in MARKERS and out[index] != "#pct" and _NUM_RE.match(out[index + 1]):
            out[index], out[index + 1] = out[index + 1], out[index]
            index += 2
            continue
        index += 1
    return tuple(out)


def canonical_variants(text, cap=48):
    """Canonical renderings of ``text`` as a frozenset of token tuples."""
    atoms = pre_tokenize(text)
    segments = []          # list of (kind, payload)
    index = 0
    while index < len(atoms):
        atom = atoms[index]
        if atom in NUMWORDS:
            run = []
            while index < len(atoms) and (atoms[index] in NUMWORDS
                                          or (atoms[index] == "and" and run
                                              and index + 1 < len(atoms)
                                              and atoms[index + 1] in NUMWORDS)):
                if atoms[index] != "and":
                    run.append(atoms[index])
                index += 1
            segments.append(("run", run))
            continue
        segments.append(("atom", atom))
        index += 1

    fixed = []
    previous_run_value = None
    for kind, payload in segments:
        if kind == "run":
            fixed.append(_run_renderings(payload))
            standard = _parse_standard(payload)
            previous_run_value = (int(standard) if standard is not None
                                  and standard == standard.to_integral_value() else None)
            continue
        atom = payload
        if (atom in WORD_ORDINALS and previous_run_value in TENS.values()
                and WORD_ORDINALS[atom] < 10):
            # Compound word ordinal: "thirty first" is 31st, written out. The
            # tens part was already consumed as a number run, so fold it back.
            fixed.pop()
            fixed.append([("#ord" + str(previous_run_value + WORD_ORDINALS[atom]),),
                          (str(previous_run_value), atom)])
            previous_run_value = None
            continue
        previous_run_value = None
        if _NUM_RE.match(atom):
            fixed.append([(_dec(Decimal(atom)),)])
        elif _ORD_RE.match(atom):
            fixed.append([("#ord" + str(int(_ORD_RE.match(atom).group(1))),)])
        elif atom in WORD_ORDINALS:
            fixed.append([("#ord" + str(WORD_ORDINALS[atom]),), (atom,)])
        elif atom in CURRENCY_WORDS:
            fixed.append([(CURRENCY_WORDS[atom],)])
        elif atom in PCT_WORDS:
            fixed.append([("#pct",)])
        elif (atom.startswith("#sc") and atom[3:] in SUFFIX_SCALE and fixed
              and fixed[-1][0] and _NUM_RE.match(fixed[-1][0][-1])):
            scale = SUFFIX_SCALE[atom[3:]]
            previous = fixed.pop()
            options = []
            for option in previous:
                if option and _NUM_RE.match(option[-1]):
                    value = Decimal(option[-1]) * SCALES[scale]
                    options.append(option[:-1] + (_dec(value),))
                    options.append(option + (scale,))
                else:
                    options.append(option + (atom,))
            fixed.append(options[:6])
        elif atom.startswith("#sc") and atom[3:] in SUFFIX_SCALE:
            fixed.append([(SUFFIX_SCALE[atom[3:]],)])
        elif atom in MONTHS:
            fixed.append([(MONTHS[atom],)])
        elif atom.rstrip("s") in MONTH_NUM and atom in MONTH_NUM:
            fixed.append([(atom,)])
        else:
            fixed.append([(atom,)])

    total = 1
    for options in fixed:
        total *= max(1, len(options))
    if total > cap:
        fixed = [options[:1] if len(options) > 1 and idx > 0 else options
                 for idx, options in enumerate(fixed)]

    variants = set()
    for combination in product(*fixed) if fixed else [()]:
        flat = tuple(t for part in combination for t in part)
        variants.add(_reorder_markers(flat))
        if len(variants) >= cap:
            break
    return frozenset(variants) if variants else frozenset({()})


CURRENCY_MARKERS = {"#usd", "#eur", "#gbp", "#jpy", "#cent"}


def drop_currency(tokens):
    """Currency-marker tolerance for the headline tier.

    The Earnings21 ``wer_tags`` annotation frequently cuts a money mention at the
    numeral -- gold mention ``$6.5`` with the scale word ``million`` carried by a
    SEPARATE mention -- while the hypothesis writes the whole phrase out ("six
    point five million dollars"). Comparing with the currency marker in place
    would score that boundary artifact as a content error. ``#pct`` and ordinal
    markers are deliberately RETAINED: "19" vs "19%" and "3" vs "3rd" are genuine
    content differences, not writing conventions.
    """
    return tuple(t for t in tokens if t not in CURRENCY_MARKERS)


def value_only(tokens):
    """Strip every marker and function word -- the most generous tier."""
    return tuple(t for t in tokens
                 if t not in MARKERS and t not in STOPWORDS and not t.startswith("#ord"))


def contains_subsequence(haystack, needle):
    if not needle:
        return False
    span = len(needle)
    return any(haystack[i:i + span] == needle
               for i in range(0, len(haystack) - span + 1))


SLACK = 6  # extra raw chunks a hypothesis may spend saying the same value


def format_match(ref_text, hyp_text, tier):
    """Does ``hyp_text`` say what ``ref_text`` says, differing only in convention?

    ``tier`` in {'strict', 'window', 'value'}:

    strict -- canonical equality of the WHOLE tight aligned window, every marker
              retained. Conservative lower bound.
    window -- headline tier. Slides over every contiguous sub-span of the wide
              hypothesis window and asks for canonical equality with currency
              markers dropped (see :func:`drop_currency`); ``#pct`` and ordinal
              markers are retained, so "19" vs "19%" still counts as an error.
    value  -- as 'window' but with every marker and function word stripped:
              pure numeric-value agreement, a generous upper bound.

    Sliding over sub-spans rather than canonicalising the window as one string is
    deliberate: a whole-window canonicalisation multiplies out one rendering set
    per number run, and the variant cap then silently drops the year reading of
    "twenty twenty". A sub-span carries at most one or two runs, so nothing is
    truncated.
    """
    ref_variants = canonical_variants(ref_text)
    if tier == "strict":
        return bool(ref_variants & canonical_variants(hyp_text))

    if tier == "window":
        targets = {drop_currency(r) for r in ref_variants}
    else:
        targets = {value_only(r) for r in ref_variants}
    targets = {t for t in targets if t}
    if not targets:
        return False

    chunks = hyp_text.split()
    max_len = min(len(chunks), len(ref_text.split()) + SLACK)
    for start in range(len(chunks)):
        for length in range(1, min(max_len, len(chunks) - start) + 1):
            span = " ".join(chunks[start:start + length])
            for variant in canonical_variants(span):
                candidate = (drop_currency(variant) if tier == "window"
                             else value_only(variant))
                if candidate and candidate in targets:
                    return True
    return False
