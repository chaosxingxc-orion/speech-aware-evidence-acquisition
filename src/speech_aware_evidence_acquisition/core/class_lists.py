"""The Earnings-21 PRE-MEETING BRIEF: ConEC's own call context, rendered as
labelled entity-class lines, plus its equal-length form twin.

E5 (plan revision 2, Part E) needs a knowledge-supply arm whose content is what
a human would read before joining the call -- who is on it, which company and
ticker it is about, what the products and segments are called -- and whose
provenance is unambiguously the benchmark's own pre-existing documents rather
than anything distilled from the answer. This module builds that brief, and only
that brief.

WHAT ConEC ACTUALLY SHIPS FOR EARNINGS-21, COUNTED
--------------------------------------------------
Two per-call text files under the ``conec`` lock key, and nothing else that is
machine-readable (the third context artifact, ``contexts/pdfs/*.pdf``, is
binary, has no D1 layer and is read by nothing in this repository):

``contexts/participant_names/<call>.names.txt`` -- the call's participant
roster, one ``Name - Role`` line per speaker, in real casing and real
punctuation. Example, call 4330115::

    Dru Anderson - Senior Vice President and Investor Relations
    Boyd Chumbley - President of Culp Upholstery Fabric Division
    Robert Griffin - Raymond James & Associates, Inc.

This file is LABELLED data: ConEC itself separates the person from the role with
`` - ``, so participants, their titles, their outside affiliations and the
divisions they run can be read off without guessing. ConEC's own Table 1 is why
this matters -- the roster is what lifts PERSON coverage from 30 % to 82 %.

``contexts/<call>.txt`` -- the call's press release and slides as a LOWERCASED,
function-word-stripped token stream, one token per line, each followed by a
constant `` 1``. Example, the first tokens of 4330115::

    pm 1 / culp 1 / announces 1 / results 1 / third 1 / quarter 1 / fiscal 1 /
    inc 1 / investor 1 / kit 1 / ... / wire 1 / nyse 1 / today 1 / ...

This file is UNLABELLED: casing, punctuation, sentence structure and the
document boundary are all gone, so no class can be read off it -- it can only be
scanned for cue tokens the documents themselves use (``nyse``, ``inc``,
``division``). Every class this module derives from it is therefore emitted as a
CANDIDATE, named as such in the brief's own text, and a reader of a result table
should treat those lines as recall aids, not as an entity inventory.

WHAT IS NEVER READ
------------------
No reference transcript, no timestamp file, no ``wer_tags`` sidecar, no bias
list. ``contexts/`` and ``contexts/participant_names/`` are the only paths this
module can name, and ``tests/unit/test_class_lists.py`` proves it by refusing
the renderer any filesystem access outside them. The distinction is the one
``core.bias_lists`` already states for the shipped ``oracle_list.txt``: ConEC's
context files are pre-existing real-world documents about the call, and a
reference transcript is the answer.

TWO EVIDENCE ITEMS, NOT ONE
---------------------------
The brief spans two source files, and ``contracts.gate_evidence_identity.
_route_evidence_layer_key`` routes ONE relpath per evidence item to ONE D1
layer (``e21_contexts`` for the document, ``e21_participant_names`` for the
roster). A single fused item could not carry a verifiable derivation chain for
either half, so ``conec-class-lists`` returns two items -- roster first, then
document -- each pinned to its own source bytes and its own registered
transform. ``core.model.transport`` renders them in list order as consecutive
``[evidence <id>] <content>`` blocks, so the two read as one brief in the
prompt.

THE FORM TWIN
-------------
``conec-class-lists-placebo`` is KU-E1c's control: the SAME class labels, the
SAME number of entries and the SAME whitespace-token count per line, with every
token of every entry replaced by a neutral placeholder drawn cyclically from
:data:`PLACEHOLDER_WORDS` by POSITION alone. It therefore carries no call
information whatsoever -- not the names, not the company, not even the length
distribution of the individual words -- while holding the prompt's shape and
volume fixed. The distractor twin the E5 brief also names ("the same shape with
names from OTHER calls") needs no new source: it is the existing
``evidence_mismatch`` / ``core.evidence.rotated_mismatch`` machinery applied to
this source, which hands each call another call's brief at identical shape.

"THE SAME VOLUME" HAD TO BE MEASURED, AND IT WAS NOT
---------------------------------------------------
Equal whitespace-token counts are a PROXY for equal prompt volume, and the
KC-E1 prompt fit measured what that proxy is worth on the flight tokenizer:
at ``brief_max_entries_per_class`` 12 the twin renders 42 to 256 tokens
SHORTER than the arm per window, median 161. The owner ruling of 2026-09-06
locks a control to its treatment on the flight tokenizer, so the second half
of this module -- "The TOKEN-matched form twin" -- pads each twin line with
a neutral one-token filler until it measures its own brief line IN CONTEXT,
through the same ``token_counter`` seam ``rails.proposer._token_matched_
control`` uses for the KC-A1 control. The pads are measured once against a
resident server, materialised as a hash-pinned artifact under
``configs/knowledge/``, and replayed on the wire with no tokenizer at all;
``conec-class-lists-placebo-token-matched`` is the evidence source that flies
them. The whitespace twin above is unchanged and still registered -- it is
what the prompt fit measured, and superseding a receipt in place is not how
this repository records a correction.
"""

from __future__ import annotations

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Sequence

from ..e0.artifacts import REPO_ROOT
from ..reproduction.asr_wer_whisper import normalize_whisper_english
from .base import EvidenceError
from .evidence_derivation import TRANSFORMS

DEFAULT_MAX_ENTRIES_PER_CLASS = 0
"""0 means "the whole brief": no class line is truncated. The E5 brief states
the cap as a parameter and defaults it off, because the token cost of the brief
is a measurement the flight makes on the flight tokenizer, not a number to be
guessed here. A positive value caps EVERY class line at that many entries,
keeping first-appearance order."""

MAX_ENTRIES_CEILING = 10_000

#: Title vocabulary. A roster role containing one of these names a position
#: INSIDE the company; a role containing none of them is an outside affiliation
#: (ConEC's rosters list sell-side analysts by their firm alone, e.g. "Robert
#: Griffin - Raymond James & Associates, Inc.").
TITLE_CUES = frozenset(
    {
        "president", "chief", "officer", "vice", "senior", "executive", "secretary",
        "treasurer", "director", "managing", "manager", "head", "counsel", "chairman",
        "chairwoman", "chair", "founder", "partner", "controller", "principal",
        "ceo", "cfo", "coo", "cto", "cio", "evp", "svp", "vp", "relations",
    }
)

#: Segment vocabulary. Used on BOTH files: a roster role saying "President of
#: the Culp Upholstery Fabric Division" names a division, and a cue token in the
#: document stream marks the tokens beside it as a segment candidate.
SEGMENT_CUES = frozenset(
    {"division", "divisions", "segment", "segments", "brand", "brands"}
)
"""``product``, ``platform``, ``portfolio`` and ``franchise`` are dropped for the
reason the company cues drop ``company``: they are ordinary earnings vocabulary,
and a scan around them returns phrases that name no business."""

#: Corporate-suffix vocabulary, for the company candidates in the document
#: stream. ConEC's normalization has already stripped the punctuation, so
#: "Culp, Inc." arrives as the two adjacent tokens "culp" and "inc".
COMPANY_SUFFIX_CUES = frozenset(
    {
        "inc", "incorporated", "corp", "corporation", "holdings", "plc", "ltd",
        "limited", "llc", "lp", "llp", "nv", "sa", "ag",
    }
)
"""Deliberately does NOT include ``company``, ``companies``, ``group``,
``industries``, ``systems`` or ``technologies``: those words occur in ordinary
earnings prose ("the company reported"), and with the source's function words
stripped a scan around them returns phrases like "rate reflected company" that
name nothing. The cues kept are legal-entity suffixes, which in these documents
follow a company name and almost nothing else."""

#: Exchange vocabulary, for the ticker candidates. In the source documents the
#: ticker follows the exchange ("NYSE: CULP"), so the tokens AFTER the cue are
#: the candidate.
EXCHANGE_CUES = frozenset(
    {"nyse", "nasdaq", "amex", "otcqx", "otcqb", "otc", "tsx", "lse", "asx", "ticker", "symbol"}
)

#: Neutral filler for the form twin. Ten ordinary English nouns that name
#: nothing: no call, no company, no person, no sector. Chosen by POSITION only,
#: so the twin cannot encode anything about the call it replaces -- two calls
#: whose briefs have the same shape get byte-identical placebos, which is
#: exactly the property a form control needs.
PLACEHOLDER_WORDS = (
    "item", "entry", "term", "unit", "element", "field", "label", "value", "record", "part",
)

_ANNOTATED_PUNCTUATION = frozenset("&.,'-/()")

_CONTEXT_LINE = re.compile(r"^\s*(?P<token>\S+)\s+\d+\s*$")
_ROSTER_SEPARATOR = " - "
_ENTRY_SEPARATOR = "; "

ROSTER_PROVENANCE = (
    "the call's own participant roster as published by ConEC "
    "(contexts/participant_names/<call>.names.txt: one \"Name - Role\" line per "
    "speaker, real casing and punctuation). No transcript content."
)

DOCUMENT_PROVENANCE = (
    "terms from the call's own press release and slide documents as published by "
    "ConEC (contexts/<call>.txt: a lowercased, function-word-stripped token stream "
    "of those documents, one token per line). The stream carries no casing, "
    "punctuation or sentence structure, so the classes below are CANDIDATES read "
    "off cue words the documents themselves use, not a labelled inventory. No "
    "transcript content."
)


class ClassListError(EvidenceError):
    """The ConEC context could not be rendered as a pre-meeting brief."""


def validate_max_entries_per_class(value: object) -> int:
    """Fail-closed cap validation, mirroring ``core.bias_lists``' own."""

    if value is None:
        return DEFAULT_MAX_ENTRIES_PER_CLASS
    if isinstance(value, bool) or not isinstance(value, int):
        raise ClassListError(
            f"brief_max_entries_per_class must be an integer, got {type(value).__name__}"
        )
    if value < 0 or value > MAX_ENTRIES_CEILING:
        raise ClassListError(
            f"brief_max_entries_per_class must be between 0 (no cap) and "
            f"{MAX_ENTRIES_CEILING}, got {value}"
        )
    return value


def resolve_max_entries_per_class(values: Mapping[str, object] | None) -> int:
    if values is None:
        return DEFAULT_MAX_ENTRIES_PER_CLASS
    return validate_max_entries_per_class(
        values.get("brief_max_entries_per_class", DEFAULT_MAX_ENTRIES_PER_CLASS)
    )


# ---------------------------------------------------------------------------
# Reading the two ConEC shapes
# ---------------------------------------------------------------------------


def roster_entries(text: str) -> list[tuple[str, str]]:
    """``(name, role)`` per roster line, in file order.

    A line with no `` - `` separator is a name with no role, which ConEC does
    produce; it keeps the name and an empty role rather than being dropped, so
    no participant is silently lost from a PERSON-recall aid.
    """

    if not isinstance(text, str):
        raise ClassListError(f"a ConEC roster must be text, got {type(text).__name__}")
    entries: list[tuple[str, str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        name, separator, role = stripped.partition(_ROSTER_SEPARATOR)
        entries.append((name.strip(), role.strip() if separator else ""))
    return entries


def context_tokens(text: str) -> list[str]:
    """The document stream's tokens, in document order, repeats kept.

    Every line is ``<token> <count>``; a line that does not match that shape is
    refused rather than guessed at, because a silently skipped line would move
    the adjacency the cue scan below depends on.
    """

    if not isinstance(text, str):
        raise ClassListError(f"a ConEC context must be text, got {type(text).__name__}")
    tokens: list[str] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        match = _CONTEXT_LINE.match(line)
        if match is None:
            raise ClassListError(
                f"ConEC context line {number} is not '<token> <count>': {line!r}"
            )
        tokens.append(match.group("token"))
    return tokens


# ---------------------------------------------------------------------------
# Class extraction
# ---------------------------------------------------------------------------


def _dedupe(candidates: Sequence[str]) -> list[str]:
    """Case-insensitive de-duplication keeping the FIRST-SEEN form and order --
    the same discipline ``core.bias_lists.extract_bias_candidates`` uses."""

    seen: set[str] = set()
    kept: list[str] = []
    for candidate in candidates:
        text = " ".join(candidate.split())
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        kept.append(text)
    return kept


def _is_title_role(role: str) -> bool:
    return any(word.strip(",.").casefold() in TITLE_CUES for word in role.split())


def participant_class(entries: Sequence[tuple[str, str]]) -> list[str]:
    """``Name (role)`` for every roster line, roles kept verbatim."""

    return _dedupe([f"{name} ({role})" if role else name for name, role in entries])


def affiliation_class(entries: Sequence[tuple[str, str]]) -> list[str]:
    """The outside organizations the roster names: the role field of every line
    whose role carries no title cue. ConEC lists sell-side analysts by their
    firm alone, so this is a labelled ORG class, not a guess."""

    return _dedupe([role for _, role in entries if role and not _is_title_role(role)])


def division_class(entries: Sequence[tuple[str, str]]) -> list[str]:
    """Divisions and segments a roster ROLE names: the words up to and including
    a segment cue, after "of"/"for" where the role has one."""

    found: list[str] = []
    for _, role in entries:
        if not role:
            continue
        words = role.split()
        lowered = [word.strip(",.").casefold() for word in words]
        for index, word in enumerate(lowered):
            if word not in SEGMENT_CUES:
                continue
            start = 0
            for back in range(index - 1, -1, -1):
                if lowered[back] in {"of", "for", "the"}:
                    start = back + 1
                    break
            phrase = " ".join(words[start : index + 1]).strip(" ,.")
            if phrase and phrase.casefold() not in SEGMENT_CUES:
                found.append(phrase)
            break
    return _dedupe(found)


def _window(tokens: Sequence[str], start: int, end: int) -> str:
    return " ".join(tokens[max(start, 0) : min(end, len(tokens))])


def company_class(tokens: Sequence[str], *, span: int = 2, exchange_span: int = 1) -> list[str]:
    """Company and ticker CANDIDATES from the document stream.

    A corporate suffix takes the ``span`` tokens before it ("monro inc"); an
    exchange cue takes the ``exchange_span`` tokens after it, which is where the
    ticker sits in "NASDAQ: MNRO" and a ticker is one token. A cue with nothing
    beside it yields nothing rather than a bare cue word.
    """

    found: list[str] = []
    for index, token in enumerate(tokens):
        if token in COMPANY_SUFFIX_CUES and index > 0:
            phrase = _window(tokens, index - span, index + 1)
            if phrase != token:
                found.append(phrase)
        elif token in EXCHANGE_CUES and index + 1 < len(tokens):
            found.append(_window(tokens, index, index + 1 + exchange_span))
    return _dedupe(found)


def segment_class(tokens: Sequence[str], *, span: int = 2) -> list[str]:
    """Product and segment CANDIDATES: the ``span`` tokens before a segment cue,
    plus the cue itself, which is how the source documents name a business
    ("mattress fabrics segment")."""

    found: list[str] = []
    for index, token in enumerate(tokens):
        if token not in SEGMENT_CUES or index == 0:
            continue
        phrase = _window(tokens, index - span, index + 1)
        if phrase != token:
            found.append(phrase)
    return _dedupe(found)


def term_class(tokens: Sequence[str]) -> list[str]:
    """The residual keyword list: the document stream de-duplicated, in document
    order. This is what ``conec-contexts`` already supplies verbatim, minus the
    constant counts -- kept in the brief so the brief is a superset of the
    context arm, and a difference between the two is attributable to the class
    structure rather than to lost content."""

    return _dedupe(list(tokens))


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def annotate_normalized(entry: str) -> str:
    """``entry`` with its Whisper-normalized form beside it when the two differ.

    Every Earnings metric in play -- ``asr-wer-whisper``,
    ``conec-entity-wer-official``, ``numeric-value-accuracy-v1``,
    ``semantic-high-impact-error-rate-v1`` -- compares WHISPER-NORMALIZED
    strings, so "Raymond James & Associates, Inc." is only ever scored as
    "raymond james and associates inc". Showing that form beside the surface one
    tells the core which spelling the measurement will accept; suppressing it
    when the two agree keeps the token cost on the entries where it buys
    something.

    The annotation is emitted ONLY for entries carrying casing or punctuation --
    the two things normalization removes that a speaker cannot pronounce, and
    therefore the two places where the core could otherwise choose a spelling
    that normalizes to a different token sequence ("CL King" -> ``cl king``
    against "C.L. King" -> ``c l king``). An all-lowercase document token is
    never annotated: "third" and "million" also change under the number
    normalizer ("3rd", "1000000"), but BOTH sides of the metric are normalized,
    so those forms already agree and the annotation would be pure token cost.
    """

    if not any(character.isupper() or character in _ANNOTATED_PUNCTUATION for character in entry):
        return entry
    normalized = normalize_whisper_english(entry)
    if not normalized or normalized == entry:
        return entry
    return f"{entry} [normalized: {normalized}]"


def _class_line(label: str, entries: Sequence[str], max_entries: int) -> str | None:
    kept = list(entries[:max_entries]) if max_entries else list(entries)
    if not kept:
        return None
    return f"{label}: " + _ENTRY_SEPARATOR.join(annotate_normalized(entry) for entry in kept)


def render_roster_brief(text: str, max_entries: int) -> str:
    """Part 1 of the brief: the labelled classes, from the roster file."""

    max_entries = validate_max_entries_per_class(max_entries)
    entries = roster_entries(text)
    if not entries:
        raise ClassListError("the ConEC participant roster is empty; refusing to emit a brief")
    lines = [f"Pre-meeting brief for this earnings call, part 1 of 2 -- {ROSTER_PROVENANCE}"]
    for label, values in (
        ("Participants and roles", participant_class(entries)),
        ("Organizations named in the roster", affiliation_class(entries)),
        ("Divisions and segments named in the roster", division_class(entries)),
    ):
        line = _class_line(label, values, max_entries)
        if line is not None:
            lines.append(line)
    return "\n".join(lines)


def render_document_brief(text: str, max_entries: int) -> str:
    """Part 2 of the brief: the candidate classes, from the document stream."""

    max_entries = validate_max_entries_per_class(max_entries)
    tokens = context_tokens(text)
    if not tokens:
        raise ClassListError("the ConEC context document is empty; refusing to emit a brief")
    lines = [f"Pre-meeting brief for this earnings call, part 2 of 2 -- {DOCUMENT_PROVENANCE}"]
    for label, values in (
        ("Company and ticker candidates", company_class(tokens)),
        ("Product and segment candidates", segment_class(tokens)),
        ("Other terms from the call's documents", term_class(tokens)),
    ):
        line = _class_line(label, values, max_entries)
        if line is not None:
            lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The form twin
# ---------------------------------------------------------------------------


def placebo_of(brief: str) -> str:
    """The equal-length form twin of a rendered brief.

    The first line (the provenance sentence) and every class LABEL survive
    verbatim -- they are the form. Everything after each label's ``": "`` is
    replaced token for token by :data:`PLACEHOLDER_WORDS` chosen by running
    position, so the twin has the same line count, the same class labels, the
    same entry separators and exactly the same whitespace-token count as the
    brief it twins, and carries nothing about the call.
    """

    if not isinstance(brief, str):
        raise ClassListError(f"a brief must be text, got {type(brief).__name__}")
    position = 0
    lines: list[str] = []
    for index, line in enumerate(brief.splitlines()):
        if index == 0 or ": " not in line:
            lines.append(line)
            continue
        label, _, body = line.partition(": ")
        replaced: list[str] = []
        for token in body.split(" "):
            if not token:
                replaced.append(token)
                continue
            replaced.append(PLACEHOLDER_WORDS[position % len(PLACEHOLDER_WORDS)])
            position += 1
        lines.append(f"{label}: " + " ".join(replaced))
    return "\n".join(lines)


def whitespace_token_count(text: str) -> int:
    """The token count the form twin holds equal. Whitespace tokens, not the
    flight tokenizer's -- the flight measures that itself and reports it."""

    return len(text.split())


# ---------------------------------------------------------------------------
# Registered transforms (core.evidence_derivation.TRANSFORMS)
# ---------------------------------------------------------------------------


def _max_entries(params: Mapping[str, object], transform: str) -> int:
    if not isinstance(params, Mapping):
        raise ClassListError(
            f"{transform} transform params must be a mapping, got {type(params).__name__}"
        )
    return validate_max_entries_per_class(params.get("max_entries_per_class"))


def conec_class_lists_roster_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``conec-class-lists-roster`` v1."""

    return render_roster_brief(text, _max_entries(params, "conec-class-lists-roster"))


def conec_class_lists_document_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``conec-class-lists-document`` v1."""

    return render_document_brief(text, _max_entries(params, "conec-class-lists-document"))


def conec_class_lists_roster_placebo_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``conec-class-lists-roster-placebo`` v1 -- the twin of the
    roster half, built from the SAME source bytes so its derivation chain pins
    the same file and its shape can never drift from the arm it controls."""

    return placebo_of(conec_class_lists_roster_content(text, params))


def conec_class_lists_document_placebo_content(text: str, params: Mapping[str, object]) -> str:
    """TRANSFORMS: ``conec-class-lists-document-placebo`` v1."""

    return placebo_of(conec_class_lists_document_content(text, params))


# ---------------------------------------------------------------------------
# The TOKEN-matched form twin (owner ruling, 2026-09-06)
# ---------------------------------------------------------------------------
#
# The twin above holds WHITESPACE tokens equal. The KC-E1 prompt fit
# (``docs/checks/speech-aware-evidence-acquisition/2026-09-06-e21-kc-e1-brief-
# 44-v1/prompt-fit/``, result 4) measured what that is worth on the flight
# tokenizer and the answer is: not enough. At ``brief_max_entries_per_class``
# 12 the placebo renders 42 to 256 tokens SHORTER than the arm per window,
# median 161, because placeholder nouns cost fewer tokens than proper nouns
# and bracketed normalized forms. The owner ruling of 2026-09-06 locks a
# control to its treatment on the FLIGHT TOKENIZER rather than on characters
# or whitespace, so a 161-token-light twin prices content and volume together
# and cannot carry the cell's claim.
#
# The repair is the one ``rails.proposer._token_matched_control`` already uses
# for the KC-A1 category-only control, reached through the same
# ``token_counter`` seam rather than forked: grow the control by whole repeats
# of a neutral one-token filler until it MEASURES the treatment's count, and
# refuse rather than approximate when it cannot land exactly.
#
# Two differences from the A2T control, both forced by this carrier:
#
# * the unit is a LINE of a multi-line brief, not a single description cell.
#   The count each line is matched to is therefore the count of the rendered
#   PREFIX through that line, so equality holds IN CONTEXT -- a per-line count
#   taken in isolation would leave the newline boundaries unaccounted for and
#   whole-block equality would only be likely rather than proven. Equality at
#   the last index IS whole-block equality, by construction;
# * the match is measured ONCE, offline, and replayed. The pad repeats are
#   materialised as a hash-pinned artifact under ``configs/knowledge/``, so the
#   flight itself needs no tokenizer and the derivation registry re-derives the
#   twin from the same source bytes and the same declared params.

#: The pad unit a token-matched line grows by: one leading space and one
#: neutral noun. Same shape and same neutral-noun family as
#: ``rails.proposer.CONTROL_FILLER`` (``" tool"``), the filler the KC-A1
#: control is padded with; the word itself is :data:`PLACEHOLDER_WORDS`'s own
#: first entry, so the pad says nothing the twin does not already say and
#: names no call, company, person or sector. A pad unit has to cost EXACTLY
#: one token on the flight tokenizer for an exact landing to be reachable from
#: any gap; :func:`placebo_pad_repeats` proves that per line by measurement
#: and refuses when it cannot land, rather than assuming it here.
PLACEBO_PAD_FILLER = " " + PLACEHOLDER_WORDS[0]

#: Per-line pad ceiling. The measured gaps are tens of tokens per line; a plan
#: asking for thousands is a broken counter or a mismatched pair, and a silent
#: multi-megabyte line is a worse failure than a refusal.
MAX_PAD_REPEATS_PER_LINE = 4096

#: The pinned pad-plan artifact's schema string, and the config key that names
#: it. The key holds an object with exactly ``artifact_relpath`` (under
#: ``configs/``, so the fragment's config hash pins the PATH) and
#: ``artifact_sha256`` (over the file's bytes, so the hash pins the BYTES) --
#: the same two-field pin ``core.instructions.render_evolved_registry``
#: already uses for an evolved Audio2Tool artifact.
PLACEBO_PAD_PLAN_SCHEMA = "saea-e21-brief-placebo-token-match-v1"
PLACEBO_PAD_PLAN_KEY = "evidence_pad_plan"

_PAD_PLAN_RELPATH = re.compile(r"[A-Za-z0-9._][A-Za-z0-9._/-]*")
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


def _brief_lines(text: str, label: str) -> list[str]:
    """``splitlines()``, refusing text that does not round-trip through it.

    A pad plan is a list of per-line repeats replayed by rejoining the lines
    with a newline. Text carrying a trailing newline, a carriage return or any
    other separator ``str.splitlines`` recognises would come back changed, and
    a twin that is not the bytes that were measured is not a twin.
    """

    if not isinstance(text, str):
        raise ClassListError(f"{label} must be text, got {type(text).__name__}")
    lines = text.splitlines()
    if "\n".join(lines) != text:
        raise ClassListError(
            f"{label} does not round-trip through splitlines(); a per-line pad plan "
            "can never be replayed onto it"
        )
    return lines


def _measured(token_counter: object, text: str, label: str) -> int:
    if not callable(token_counter):
        raise ClassListError("token_counter must be callable")
    value = token_counter(text)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ClassListError(
            f"token_counter returned {value!r} for {label}; a token count must be a "
            "non-negative integer"
        )
    return value


def validate_pad_filler(filler: object) -> str:
    """Fail-closed filler validation: ASCII, non-empty, one leading space and
    no other whitespace. The leading space is what keeps the pad a separate
    token from the entry it follows; a filler carrying a newline or an entry
    separator would rewrite the twin's line and entry structure instead of
    extending it."""

    if not isinstance(filler, str) or not filler:
        raise ClassListError("the pad filler must be non-empty text")
    if not filler.isascii():
        raise ClassListError(f"pad filler {filler!r} carries non-ASCII characters")
    if not filler.startswith(" ") or filler[1:].strip() != filler[1:]:
        raise ClassListError(
            f"pad filler {filler!r} must be one leading space followed by a word"
        )
    if any(character in filler for character in "\n\r\t;") or "  " in filler:
        raise ClassListError(f"pad filler {filler!r} carries a separator or padding")
    return filler


def placebo_pad_repeats(
    brief: str,
    placebo: str,
    *,
    token_counter,
    filler: str = PLACEBO_PAD_FILLER,
) -> list[int]:
    """How many ``filler`` repeats each twin line needs to MEASURE its own
    brief line, in context, on ``token_counter``.

    ``token_counter`` is the seam and the whole point: it selects WHICH
    quantity the twin is matched on. Passing the serving geometry's own
    tokenizer -- ``POST /tokenize`` on the resident llama-server, the same
    route ``scripts/e21_kc_e1_prompt_fit.py`` measures the fit with -- makes
    the twin a FLIGHT-TOKEN twin, which is what the 2026-09-06 owner ruling
    asks for. Passing :func:`whitespace_token_count` reproduces the old
    whitespace twin exactly, and a test can pass a fake.

    Returns one repeat count per line, ``0`` for a line that already measures
    its target (the provenance sentence always does: :func:`placebo_of` copies
    it verbatim). The result is a pure function of the two texts and the
    counter, so re-running it on the same inputs returns the same list.

    Three refusals, all fail-closed:

    * a twin whose line count differs from the brief's is not a form twin at
      all and is refused before a single measurement is taken;
    * a twin line whose prefix already measures MORE than the brief's cannot
      be padded down. Truncating it would leave a twin that is neither matched
      nor a rendering of :func:`placebo_of`, so it is refused -- the same
      refusal ``rails.proposer._token_matched_control`` makes for a category
      longer than its note;
    * a filler that does not close the gap -- one that adds no token, or one
      that overshoots the target -- is refused rather than approximated. An
      approximate control is the defect this function exists to remove.
    """

    validate_pad_filler(filler)
    arm_lines = _brief_lines(brief, "a brief")
    twin_lines = _brief_lines(placebo, "a form twin")
    if len(arm_lines) != len(twin_lines):
        raise ClassListError(
            f"the form twin has {len(twin_lines)} lines against the brief's "
            f"{len(arm_lines)}; a twin that does not share the brief's line count "
            "cannot be matched line by line"
        )
    repeats: list[int] = []
    padded: list[str] = []
    for index, twin_line in enumerate(twin_lines):
        target = _measured(
            token_counter, "\n".join(arm_lines[: index + 1]), f"brief prefix {index}"
        )
        count = 0
        measured = _measured(
            token_counter, "\n".join(padded + [twin_line]), f"twin prefix {index}"
        )
        if measured > target:
            raise ClassListError(
                f"line {index} of the form twin measures {measured} tokens in context "
                f"against the brief's {target}: a twin line already longer than the "
                "line it twins can never be padded down to it, and a truncated twin "
                "is neither matched nor a twin"
            )
        while measured < target:
            grown = count + (target - measured)
            if grown > MAX_PAD_REPEATS_PER_LINE:
                raise ClassListError(
                    f"line {index} of the form twin would need more than "
                    f"{MAX_PAD_REPEATS_PER_LINE} {filler!r} repeats to reach "
                    f"{target} tokens; refusing to build it"
                )
            after = _measured(
                token_counter,
                "\n".join(padded + [twin_line + filler * grown]),
                f"twin prefix {index} at {grown} repeats",
            )
            if after <= measured:
                raise ClassListError(
                    f"filler {filler!r} adds no token to line {index} of the form twin "
                    f"({measured} tokens at {count} repeats, {after} at {grown}); it "
                    "cannot close a token gap"
                )
            if after > target:
                raise ClassListError(
                    f"line {index} of the form twin cannot be token-matched with "
                    f"{filler!r}: {grown} repeats take it from {measured} to {after} "
                    f"tokens against the brief line's {target}"
                )
            count, measured = grown, after
        padded.append(twin_line + filler * count)
        repeats.append(count)
    return repeats


def validate_pad_repeats(pad_repeats: object, line_count: int) -> list[int]:
    """Fail-closed pad-plan validation: one non-negative integer per line."""

    if isinstance(pad_repeats, (str, bytes)) or not isinstance(pad_repeats, Sequence):
        raise ClassListError("a pad plan must be a sequence of per-line repeat counts")
    repeats = list(pad_repeats)
    if len(repeats) != line_count:
        raise ClassListError(
            f"the pad plan carries {len(repeats)} repeat counts for a {line_count}-line "
            "twin; a plan that does not cover every line can never be replayed"
        )
    checked: list[int] = []
    for index, value in enumerate(repeats):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ClassListError(
                f"pad repeat {index} is {value!r}; a repeat count must be an integer"
            )
        if value < 0 or value > MAX_PAD_REPEATS_PER_LINE:
            raise ClassListError(
                f"pad repeat {index} is {value}, outside 0..{MAX_PAD_REPEATS_PER_LINE}"
            )
        checked.append(value)
    return checked


def pad_placebo(
    placebo: str,
    pad_repeats: Sequence[int],
    *,
    filler: str = PLACEBO_PAD_FILLER,
) -> str:
    """Replay a measured pad plan onto a twin. NO tokenizer, no counter, no
    I/O: line ``i`` grows by ``pad_repeats[i]`` whole ``filler`` repeats and
    nothing else, so what the flight renders is a function of the line index
    and the recorded counts alone -- never of the line's content, and never of
    the call it belongs to. This is the half of the mechanism that runs on the
    wire; :func:`placebo_pad_repeats` is the half that runs once, offline,
    beside a resident server."""

    validate_pad_filler(filler)
    lines = _brief_lines(placebo, "a form twin")
    repeats = validate_pad_repeats(pad_repeats, len(lines))
    return "\n".join(line + filler * count for line, count in zip(lines, repeats))


def token_matched_placebo_of(
    brief: str, *, token_counter, filler: str = PLACEBO_PAD_FILLER
) -> tuple[str, list[int]]:
    """The padded twin and its pad plan for one rendered brief -- the offline
    builder's one-call entry point."""

    placebo = placebo_of(brief)
    repeats = placebo_pad_repeats(
        brief, placebo, token_counter=token_counter, filler=filler
    )
    return pad_placebo(placebo, repeats, filler=filler), repeats


# ---------------------------------------------------------------------------
# The pinned pad-plan artifact
# ---------------------------------------------------------------------------


def validate_pad_plan_pin(values: Mapping[str, object] | None) -> tuple[str, str]:
    """The pad plan's ``(artifact_relpath, artifact_sha256)`` out of a composed
    config, fail-closed on every way of not pinning it."""

    if not isinstance(values, Mapping):
        raise ClassListError(
            "the token-matched form twin needs a composed config to read its pad-plan "
            "pin from; there is no default plan and deliberately no fallback to an "
            "unpadded twin"
        )
    pin = values.get(PLACEBO_PAD_PLAN_KEY)
    if not isinstance(pin, Mapping) or set(pin) != {
        "artifact_relpath",
        "artifact_sha256",
    }:
        raise ClassListError(
            f"{PLACEBO_PAD_PLAN_KEY} must be an object with exactly 'artifact_relpath' "
            "and 'artifact_sha256'; a token-matched twin can never be rendered from an "
            "unpinned pad plan"
        )
    relpath = pin["artifact_relpath"]
    sha256_hex = pin["artifact_sha256"]
    if not isinstance(relpath, str) or _PAD_PLAN_RELPATH.fullmatch(relpath) is None:
        raise ClassListError(
            f"pad-plan artifact_relpath {relpath!r} is not a plain relative path "
            "(no absolute paths, no backslashes)"
        )
    if ".." in relpath.split("/"):
        raise ClassListError(
            f"pad-plan artifact_relpath {relpath!r} escapes the repository"
        )
    if not relpath.startswith("configs/"):
        raise ClassListError(
            f"pad-plan artifact_relpath {relpath!r} is not under configs/; the plan has "
            "to live on the committed config surface the fragment's config hash pins"
        )
    if not isinstance(sha256_hex, str) or _SHA256_HEX.fullmatch(sha256_hex) is None:
        raise ClassListError(
            f"pad-plan artifact_sha256 {sha256_hex!r} is not a 64-character sha256 hex "
            "digest"
        )
    return relpath, sha256_hex


@lru_cache(maxsize=8)
def _load_pad_plan(relpath: str, sha256_hex: str, repo_root: str) -> Mapping[str, object]:
    path = Path(repo_root) / relpath
    if not path.is_file():
        raise ClassListError(f"pad-plan artifact missing: {path}")
    try:
        blob = path.read_bytes()
    except OSError as error:
        raise ClassListError(f"cannot read pad-plan artifact {path}: {error}") from error
    measured = hashlib.sha256(blob).hexdigest()
    if measured != sha256_hex:
        raise ClassListError(
            f"pad-plan artifact {path} hashes to {measured}, not the configured "
            f"{sha256_hex}; a plan edited after its fragment was written is refused "
            "rather than silently flown"
        )
    try:
        document = json.loads(blob.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ClassListError(
            f"pad-plan artifact {path} is not UTF-8 JSON: {error}"
        ) from error
    if not isinstance(document, Mapping) or document.get("schema") != PLACEBO_PAD_PLAN_SCHEMA:
        raise ClassListError(
            f"pad-plan artifact {path} does not declare schema "
            f"{PLACEBO_PAD_PLAN_SCHEMA!r}"
        )
    return document


def resolve_placebo_pad_params(
    values: Mapping[str, object] | None, *, repo_root: Path | str | None = None
) -> dict[str, object]:
    """The declared params of the two token-matched transforms, resolved from
    THIS run's own composed config and the bytes it pins.

    Returned to two callers that must agree exactly: ``core.evidence.
    _class_list_items``, which applies them, and ``core.evidence.
    resolve_declared_transform_params``, which ``core.driver.run_experiment``
    uses to re-verify the derivation record independently
    (``core.evidence_derivation.DerivedEvidenceRegistry``, condition 3). Both
    go through THIS function, so a params hash can never disagree with the pads
    that were actually applied.

    The pads themselves are IN the params rather than behind a reference, which
    is what makes the chain complete: ``params_hash`` then covers the exact
    per-line repeat counts, and re-invoking the pinned transform on the same
    source bytes with the same params has to reproduce the same twin byte for
    byte.
    """

    cap = resolve_max_entries_per_class(values)
    relpath, sha256_hex = validate_pad_plan_pin(values)
    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    document = _load_pad_plan(relpath, sha256_hex, str(root))
    caps = document.get("caps")
    if not isinstance(caps, Mapping):
        raise ClassListError(f"pad-plan artifact {relpath} carries no 'caps' object")
    entry = caps.get(str(cap))
    if not isinstance(entry, Mapping):
        raise ClassListError(
            f"pad-plan artifact {relpath} carries no plan for "
            f"brief_max_entries_per_class {cap}; the twin is matched at the cap it was "
            "measured at, never at a cap nobody measured"
        )
    halves = entry.get("halves")
    if isinstance(halves, (str, bytes)) or not isinstance(halves, Sequence) or not halves:
        raise ClassListError(
            f"pad-plan artifact {relpath} cap {cap} carries no 'halves' list"
        )
    line_pad_repeats: dict[str, list[int]] = {}
    for index, half in enumerate(halves):
        if not isinstance(half, Mapping):
            raise ClassListError(
                f"pad-plan {relpath} cap {cap} half {index} is not an object"
            )
        key = half.get("source_sha256")
        if not isinstance(key, str) or _SHA256_HEX.fullmatch(key) is None:
            raise ClassListError(
                f"pad-plan {relpath} cap {cap} half {index} carries no source_sha256"
            )
        if key in line_pad_repeats:
            raise ClassListError(
                f"pad-plan {relpath} cap {cap} names source bytes {key[:12]}... twice; "
                "two plans for one source can never both be the plan"
            )
        repeats = half.get("pad_repeats")
        if isinstance(repeats, (str, bytes)) or not isinstance(repeats, Sequence):
            raise ClassListError(
                f"pad-plan {relpath} cap {cap} half {index} carries no pad_repeats list"
            )
        line_pad_repeats[key] = validate_pad_repeats(repeats, len(list(repeats)))
    return {
        "max_entries_per_class": cap,
        "pad_artifact_relpath": relpath,
        "pad_artifact_sha256": sha256_hex,
        "line_pad_repeats": line_pad_repeats,
    }


def _pad_repeats_for_source(
    text: str, params: Mapping[str, object], transform: str
) -> list[int]:
    """This call's own pad plan, addressed by the SOURCE BYTES it was measured
    on. The transform signature is ``(text, params)`` and carries no sample id,
    and those bytes are the right key anyway: ``core.evidence._conec_names`` and
    ``_conec_contexts`` set ``DerivedEvidenceRecord.source_sha256`` to exactly
    the sha256 of this text's UTF-8 encoding, so a plan entry is bound to the
    bytes the D1 rail already verifies rather than to a name a caller could get
    wrong."""

    plan = params.get("line_pad_repeats") if isinstance(params, Mapping) else None
    if not isinstance(plan, Mapping) or not plan:
        raise ClassListError(
            f"{transform}: the declared params carry no pad plan; a token-matched twin "
            "is never rendered unpadded"
        )
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    repeats = plan.get(key)
    if repeats is None:
        raise ClassListError(
            f"{transform}: the pad plan has no entry for source bytes {key[:12]}...; a "
            "twin can never be token-matched to a call the plan never measured"
        )
    return list(repeats)


def conec_class_lists_roster_placebo_tm_content(
    text: str, params: Mapping[str, object]
) -> str:
    """TRANSFORMS: ``conec-class-lists-roster-placebo-tm`` v1 -- the roster
    twin with its measured pad plan replayed. Pure: the same source bytes and
    the same params always produce the same twin, which is what
    ``DerivedEvidenceRegistry`` condition 4 re-proves on every gated run."""

    transform = "conec-class-lists-roster-placebo-tm"
    base = placebo_of(render_roster_brief(text, _max_entries(params, transform)))
    return pad_placebo(base, _pad_repeats_for_source(text, params, transform))


def conec_class_lists_document_placebo_tm_content(
    text: str, params: Mapping[str, object]
) -> str:
    """TRANSFORMS: ``conec-class-lists-document-placebo-tm`` v1."""

    transform = "conec-class-lists-document-placebo-tm"
    base = placebo_of(render_document_brief(text, _max_entries(params, transform)))
    return pad_placebo(base, _pad_repeats_for_source(text, params, transform))


TRANSFORMS.register("conec-class-lists-roster", "v1", conec_class_lists_roster_content)
TRANSFORMS.register("conec-class-lists-document", "v1", conec_class_lists_document_content)
TRANSFORMS.register(
    "conec-class-lists-roster-placebo", "v1", conec_class_lists_roster_placebo_content
)
TRANSFORMS.register(
    "conec-class-lists-document-placebo", "v1", conec_class_lists_document_placebo_content
)
TRANSFORMS.register(
    "conec-class-lists-roster-placebo-tm", "v1", conec_class_lists_roster_placebo_tm_content
)
TRANSFORMS.register(
    "conec-class-lists-document-placebo-tm",
    "v1",
    conec_class_lists_document_placebo_tm_content,
)

CLASS_LIST_TRANSFORMS = (
    "conec-class-lists-roster",
    "conec-class-lists-document",
    "conec-class-lists-roster-placebo",
    "conec-class-lists-document-placebo",
)

#: The token-matched twin's own two transforms. Kept apart from
#: :data:`CLASS_LIST_TRANSFORMS` because their declared params are a strict
#: superset -- the cap PLUS the pinned pad plan -- and
#: ``core.evidence.resolve_declared_transform_params`` has to resolve the two
#: families differently or a params hash would never match.
CLASS_LIST_TOKEN_MATCHED_TRANSFORMS = (
    "conec-class-lists-roster-placebo-tm",
    "conec-class-lists-document-placebo-tm",
)
