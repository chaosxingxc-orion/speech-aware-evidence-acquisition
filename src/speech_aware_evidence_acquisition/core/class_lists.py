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
"""

from __future__ import annotations

import re
from typing import Mapping, Sequence

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


TRANSFORMS.register("conec-class-lists-roster", "v1", conec_class_lists_roster_content)
TRANSFORMS.register("conec-class-lists-document", "v1", conec_class_lists_document_content)
TRANSFORMS.register(
    "conec-class-lists-roster-placebo", "v1", conec_class_lists_roster_placebo_content
)
TRANSFORMS.register(
    "conec-class-lists-document-placebo", "v1", conec_class_lists_document_placebo_content
)

CLASS_LIST_TRANSFORMS = (
    "conec-class-lists-roster",
    "conec-class-lists-document",
    "conec-class-lists-roster-placebo",
    "conec-class-lists-document-placebo",
)
