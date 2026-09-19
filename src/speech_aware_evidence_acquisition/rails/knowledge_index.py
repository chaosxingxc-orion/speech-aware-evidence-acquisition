"""Item E21 (knowledge index; not the Earnings-21 carrier), 2026-09-19:
the knowledge INDEX and index-based context assembly.

Owner decisions 48 and 50 of 2026-09-19. Design:
``docs/superpowers/specs/2026-09-19-knowledge-index-and-context-assembly-design.md``
(sections 3, 4, 6 and 7.0) and its item note
``docs/superpowers/specs/2026-09-19-e21-knowledge-index-design.md``.

An INDEX is a stable, addressable, ordered catalogue of the task's knowledge
space, rendered into the CONSTANT prefix of every request at a declared
granularity, with short ids the model can cite. It is not a retrieval result
and it is not evidence: it is the map that makes a retrieval result readable.
The row's own context then carries POINTERS into the index (which entries this
row's speech selected, and how strongly) plus a BOUNDED EXPANSION (the full
text of a few entries), instead of the full text of everything retrieved.

Three properties define it, and this module encodes each of them:

* **Addressable.** :func:`intent_id`, :func:`slot_id`, :func:`edge_id` and
  :func:`exemplar_id` are the whole id grammar; the NAME inside an id is the
  one the closed contract inventory already legalises, verbatim, so a
  citation is checkable by MEMBERSHIP (:meth:`KnowledgeIndexTable.resolves`)
  rather than by parsing, and a hallucinated id is detectable.
* **Constant.** :func:`render_constant_index` is a pure function of the
  released view and the declared granularity -- never of the row. A per-row
  index is not an index; it is a pointer block (design section 3.6).
* **Ordered.** The order is declared (:data:`TAXONOMY_FREQUENCY_ORDERING`,
  registered in ``core.base.KNOWLEDGE_INDEX_ORDERINGS``) and the order IS the
  degradation order: :func:`index_droppable_items` spends the expansion tail
  first, then the pointers below the top-1, then L1 -> L0, and never the L0
  index, the contract, the speech packet or the states.

THE BOUNDARY, and it is the whole licence for this layer (design 4.5):

* the index is CONSTRUCTION-ONLY: every entry, every L1 line and every
  ordering statistic comes from the released construction stores the builder
  pins (``intent-boundaries-v1``, ``slot-contracts-v2``, ``scenario-hints-v1``)
  and from the closed legal inventory the contract already renders;
* no gold of an evaluated row enters the index at any granularity, and the
  ``exemplar`` kind -- the one kind that carries construction utterance text --
  is NEVER in the constant index (:data:`CONSTANT_INDEX_KINDS`);
* a pointer derived from the Solver's own draft is MODEL STATE, not a label;
  a pointer derived from the gold intent would be an oracle and this module
  has no seam for one;
* rendering the index, the pointer block and the expansion block makes ZERO
  contacts of any kind -- no model, tokenizer, encoder, scorer, tool, server
  or network. Every function here is pure.

Q6 of the design ("should ``intent-boundaries-factored-v1`` become the L2
store, or should the factoring be done inside the renderer?") is answered
INSIDE THE RENDERER: :data:`HOISTED_SECTIONS` names the card sections whose
text is shared across a kind's cards (``Uncertainty behavior``: one identical
199-character string on all 60 intent cards; ``Missing behavior``: 8 distinct
values over 54 slot cards), the builder lifts them into the index's own
section headers, and :func:`restore_card` splices them back byte-for-byte.
No released store is touched and nothing is re-pinned.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from .context_fit import DroppableItem

# ---------------------------------------------------------------------------
# 1. Identities.
# ---------------------------------------------------------------------------

#: The registered identity of the first instance of this schema; the value a
#: fragment's ``native_episode.knowledge_index.view`` must carry.
KNOWLEDGE_INDEX_VIEW_ID = "slurp-knowledge-index-v1"

#: The builder that produces the released view
#: (``scripts/build_slurp_knowledge_index_view.py``).
KNOWLEDGE_INDEX_BUILDER_POLICY_ID = "saea-knowledge-index-construction-v1"

#: Document schemas of the three released files.
KNOWLEDGE_INDEX_RELEASE_SCHEMA = "saea-knowledge-index-release-v1"
KNOWLEDGE_INDEX_VIEW_SCHEMA = "saea-knowledge-index-view-v1"
KNOWLEDGE_INDEX_COMPLETION_SCHEMA = "saea-knowledge-index-completion-v1"

#: The per-row receipt block, sealed exactly where E17's
#: ``tool_schema_rendering`` block is sealed (``rails.runner``).
KNOWLEDGE_INDEX_RECEIPT_SCHEMA = "saea-native-knowledge-index-v1"

#: The one registered ordering id (design section 3.4): taxonomy first
#: (scenario), then construction frequency within the scenario, with an
#: intent's confusion edges on the line after it.
TAXONOMY_FREQUENCY_ORDERING = "taxonomy-frequency-v1"

#: The carrier this first instance is defined for.
KNOWLEDGE_INDEX_CARRIER = "slurp"

#: The ``store_role`` of the exemplar store refusal 3 of design section 6.4
#: looks for.
EXEMPLAR_STORE_ROLE = "train-exemplars"

#: Every entry kind the SCHEMA defines.
ENTRY_KINDS: tuple[str, ...] = ("intent", "slot", "edge", "exemplar")

#: The kinds that may enter the CONSTANT index. ``exemplar`` is deliberately
#: absent: 9,354 entries at about 124 characters each is 1.16 MB, and the
#: schema's own rule is that an entry kind enters the constant index only
#: when its whole L1 rendering fits the prefix budget; otherwise it is
#: reachable by pointer and by expansion alone (design section 3.1).
CONSTANT_INDEX_KINDS: tuple[str, ...] = ("intent", "slot", "edge")

#: One sigil per kind, one character (design section 3.2 rule 2).
KIND_SIGILS: Mapping[str, str] = {
    "intent": "I", "slot": "S", "edge": "E", "exemplar": "X",
}
SIGIL_KINDS: Mapping[str, str] = {
    sigil: kind for kind, sigil in KIND_SIGILS.items()
}

#: The granularity levels, weakest first. L0 is id + display name, L1 adds
#: the entry's one operative contract line, L2 is the entry's full released
#: card and lives in the row's expansion block, never in the prefix.
GRANULARITY_LEVELS: tuple[str, ...] = ("L0", "L1")

#: Q3/Q4 of the design, answered as CONFIG VALUES with the recommended
#: defaults rather than as constants: which card section is an entry kind's
#: L1 line. ``Confusable exclusions`` is folded into the EDGE entries, so
#: "what distinguishes A from B" is attached to the pair rather than to A.
DEFAULT_L1_SECTIONS: Mapping[str, str] = {
    "intent": "Activation boundary",
    "slot": "Admissible formats",
    "edge": "Confusable exclusions",
}

#: The card sections each kind's L1 line may be drawn from. A section outside
#: this table is refused by name: the view carries the operative line of the
#: sections it was built with and nothing else.
L1_SECTION_CHOICES: Mapping[str, tuple[str, ...]] = {
    "intent": ("Activation boundary", "Confusable exclusions"),
    "slot": ("Admissible formats", "Extraction cues"),
    "edge": ("Confusable exclusions",),
}

#: Q6, answered inside the renderer: the card sections whose text is SHARED
#: across a kind's cards and is therefore lifted into the index's own section
#: headers instead of being paid for once per card at retrieval time.
HOISTED_SECTIONS: Mapping[str, tuple[str, ...]] = {
    "intent": ("Uncertainty behavior",),
    "slot": ("Missing behavior",),
}

#: A hoisted section may hold at most this many distinct values over its
#: kind's cards. Measured today: 1 over 60 intent cards, 8 over 54 slot
#: cards. The builder refuses a store whose section has drifted past it,
#: because hoisting a section with a value per card saves nothing and turns
#: the index header into a second copy of the store.
MAX_HOISTED_DISTINCT = 8

#: The defaults of the one key (design section 6.2, with Q8 answered at 4).
DEFAULT_GRANULARITY: Mapping[str, str] = {
    "intent": "L1", "slot": "L1", "edge": "L0",
}
DEFAULT_POINTER_BUDGET: Mapping[str, int] = {
    "intent": 3, "slot": 8, "exemplar_vote": 3,
}
DEFAULT_EXPANSION_BUDGET: Mapping[str, int] = {
    "exemplar": 5, "slot_card": 4, "intent_card": 0,
}

#: The budget names, exactly.
POINTER_BUDGET_KEYS: tuple[str, ...] = ("intent", "slot", "exemplar_vote")
EXPANSION_BUDGET_KEYS: tuple[str, ...] = ("exemplar", "slot_card", "intent_card")

#: Q7, answered as a config value with the recommended default. ``required``
#: is a later cell (it changes the answer surface, which is where the official
#: scorer reads) and is refused here by name until that cell is designed.
SOLVER_CITATION_MODES: tuple[str, ...] = ("permitted", "required")
DEFAULT_SOLVER_CITATION = "permitted"

#: Q12, answered OFF by default: with no override table every role receives
#: the same pointer/expansion block the Solver receives, which is today's
#: byte-identical-evidence shape (design finding F-4). The Planner-L0-only
#: and Reviewer-cited-only reads of section 4.2 are owner decisions still
#: open, so they are EXPRESSIBLE as overrides and armed by nobody.
ROLE_BUDGET_KEY = "knowledge_index_budget"
OVERRIDABLE_ROLES: tuple[str, ...] = (
    "perception", "solver", "reviewer", "planner", "acquisition",
)

#: The evidence id of the row's pointer block. Not a store value id: the
#: pointer block is authored by this rail from the row's own selection.
POINTER_BLOCK_EVIDENCE_ID = "index-pointers"

#: The ordered droppable classes of the INDEX's own degradation ladder
#: (design section 4.4). Expansions from the tail first, then the pointers
#: below the top-1, then L1 -> L0. Never the L0 index, the contract, the
#: speech packet or the states -- dropping L0 would let the model emit an id
#: the closed inventory does not contain.
INDEX_EXPANSION_BLOCK = "index-expansion"
INDEX_POINTER_BLOCK = "index-pointer"
INDEX_GRANULARITY_BLOCK = "index-granularity"
INDEX_DROP_ORDER: tuple[str, ...] = (
    INDEX_EXPANSION_BLOCK, INDEX_POINTER_BLOCK, INDEX_GRANULARITY_BLOCK,
)

#: What the index ladder never touches, named so a receipt reader does not
#: have to infer it from the absence of an entry.
INDEX_NEVER_DROPPABLE: tuple[str, ...] = (
    "l0-index", "task-contract", "speech-packet-reference", "agent-states",
)

#: The closed English phrases the pointer block may emit beside table values,
#: so an "adds no information" property test over this block stays finite.
NO_CANDIDATES = "(none: this row selected no index entry)"
NO_VOTE = "(none: no retrieved exemplar carries a construction intent)"
NO_SLOT_TYPES = "(none: no slot type is bound to these candidates)"
POINTER_VOCABULARY: tuple[str, ...] = (NO_CANDIDATES, NO_VOTE, NO_SLOT_TYPES)

#: The released view lives under the controlled data root, beside the stores
#: it indexes: it carries construction card TEXT.
PIN_ROOT = "data"
PIN_NAMESPACE = "knowledge/slurp/semantic/"
_PIN_KEYS = frozenset({"relpath", "root", "sha256"})

#: Chars per token, the measured anchor of design section 2.1 used for every
#: DERIVED token figure in this item. Nothing here is ever tokenized.
CHARS_PER_TOKEN = 4.60


class KnowledgeIndexError(ValueError):
    """A knowledge-index view, pin, config or selection input is invalid."""


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_text(value: str) -> str:
    """The digest a receipt records for a rendered block."""

    return _sha256_bytes(value.encode("utf-8"))


def canonical_json(document: object) -> str:
    return json.dumps(
        document, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
        allow_nan=False,
    )


def estimated_tokens(chars: int) -> int:
    """The DERIVED token count of a character count, at the measured anchor.

    Derived, never measured: re-tokenising would be a tokenizer contact, and
    this item makes none (design section 7.0).
    """

    if isinstance(chars, bool) or not isinstance(chars, int) or chars < 0:
        raise KnowledgeIndexError("a character count must be a nonnegative integer")
    return int(round(chars / CHARS_PER_TOKEN))


# ---------------------------------------------------------------------------
# 2. The id grammar (design section 3.2).
# ---------------------------------------------------------------------------

#: A name is the one the closed contract inventory legalises, verbatim: the
#: SLURP intent ``<scenario>_<action>`` and entity-type spellings are lower
#: snake case, and nothing else may enter an id.
_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_EXEMPLAR_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def _name(value: object, *, field: str) -> str:
    if not isinstance(value, str) or _NAME_PATTERN.fullmatch(value) is None:
        raise KnowledgeIndexError(
            f"{field} must be a closed-inventory name in lower snake case, got "
            f"{value!r}"
        )
    return value


def intent_id(name: object) -> str:
    """``I/play_music`` -- one of the closed 60 legal intents."""

    return f"{KIND_SIGILS['intent']}/{_name(name, field='intent name')}"


def slot_id(name: object) -> str:
    """``S/artist_name`` -- one entity type."""

    return f"{KIND_SIGILS['slot']}/{_name(name, field='slot name')}"


def edge_id(source: object, neighbour: object) -> str:
    """``E/play_music~play_radio`` -- one construction confusion pair.

    The pair is ORDERED: ``E/a~b`` is "what separates a from b as stated on
    a's card", which is not the same sentence as ``E/b~a``.
    """

    left = _name(source, field="edge source")
    right = _name(neighbour, field="edge neighbour")
    if left == right:
        raise KnowledgeIndexError("an edge joins two DIFFERENT intents")
    return f"{KIND_SIGILS['edge']}/{left}~{right}"


def exemplar_id(value: object) -> str:
    """``X/10005`` -- one annotated construction utterance.

    The store alias that replaces ``train-exemplars::value:10005`` in the
    token stream: which store an entry came from is PROVENANCE and belongs in
    the receipt, not in bytes the model reads five times per row (design
    finding F-13).
    """

    text = str(value)
    if _EXEMPLAR_PATTERN.fullmatch(text) is None:
        raise KnowledgeIndexError(f"exemplar key {value!r} is not a plain key")
    return f"{KIND_SIGILS['exemplar']}/{text}"


def parse_index_id(value: object) -> tuple[str, tuple[str, ...]]:
    """``("edge", ("play_music", "play_radio"))`` for ``E/play_music~play_radio``.

    Refuses anything outside the grammar. This is the one parser; a citation
    check is :meth:`KnowledgeIndexTable.resolves`, which is MEMBERSHIP, not
    parsing.
    """

    if not isinstance(value, str) or "/" not in value:
        raise KnowledgeIndexError(f"{value!r} is not an index id")
    sigil, _, rest = value.partition("/")
    kind = SIGIL_KINDS.get(sigil)
    if kind is None or not rest:
        raise KnowledgeIndexError(f"{value!r} names no registered entry kind")
    if kind == "edge":
        left, sep, right = rest.partition("~")
        if not sep:
            raise KnowledgeIndexError(f"edge id {value!r} names no pair")
        return kind, (_name(left, field="edge source"), _name(right, field="edge neighbour"))
    if kind == "exemplar":
        if _EXEMPLAR_PATTERN.fullmatch(rest) is None:
            raise KnowledgeIndexError(f"exemplar id {value!r} is malformed")
        return kind, (rest,)
    return kind, (_name(rest, field=f"{kind} name"),)


def is_index_id(value: object) -> bool:
    """Whether ``value`` parses as an id of the grammar. Never raises."""

    try:
        parse_index_id(value)
    except KnowledgeIndexError:
        return False
    return True


#: Ids a model may emit inside free text. Bounded on both sides so a citation
#: inside a sentence is found without swallowing neighbouring punctuation.
_CITATION_PATTERN = re.compile(
    r"(?<![0-9A-Za-z_/~])([ISEX])/([A-Za-z0-9][A-Za-z0-9._~-]*)"
)


def extract_citations(text: object) -> tuple[str, ...]:
    """Every well-formed index id a response text names, in first-seen order.

    Pure text scanning over the CLOSED grammar; it reads no gold, resolves
    nothing and decides nothing. Whether a citation RESOLVES is a separate,
    membership-only question the receipt records as two counts.
    """

    if text is None:
        return ()
    if not isinstance(text, str):
        raise KnowledgeIndexError("a citation source must be text")
    seen: list[str] = []
    for match in _CITATION_PATTERN.finditer(text):
        candidate = f"{match.group(1)}/{match.group(2)}"
        # A citation at the end of a sentence carries the sentence's
        # punctuation. Trailing separators are trimmed one at a time until
        # the id validates, never characters from the middle: a name the
        # closed inventory legalises never ENDS in one of them, so the trim
        # can only ever remove prose.
        while candidate and not is_index_id(candidate):
            if candidate[-1] not in ".,;:!?)]}'\"-_~":
                break
            candidate = candidate[:-1]
        if is_index_id(candidate) and candidate not in seen:
            seen.append(candidate)
    return tuple(seen)


def display_name(entry_id: str) -> str:
    """The human-readable half of an L0 line: the id's own name, unscored.

    Derived, never authored: a second spelling of a closed label is how a
    closed list stops being closed.
    """

    kind, parts = parse_index_id(entry_id)
    if kind == "edge":
        return f"{parts[0].replace('_', ' ')} vs {parts[1].replace('_', ' ')}"
    return parts[0].replace("_", " ")


# ---------------------------------------------------------------------------
# 3. Card sections: parsing, the operative line, and the hoist splice.
# ---------------------------------------------------------------------------

_SECTION_HEAD = re.compile(r"^([A-Z][A-Za-z ]*?):(?:[ ](.*))?$")
_BULLET = re.compile(r"^- (.*)$")
_LABELLED_BULLET = re.compile(r"^- ([a-z][a-z0-9_]*): (.*)$")


@dataclass(frozen=True)
class CardSection:
    """One labelled section of a released card, with its exact byte span."""

    name: str
    #: The section's exact text inside the card, label line included.
    text: str
    start: int
    end: int

    @property
    def chars(self) -> int:
        return len(self.text)


def parse_card_sections(content: object) -> tuple[CardSection, ...]:
    """The labelled sections of one released card, in order, byte-exact.

    Both authored SLURP stores are written as labelled sections and the
    sections are separable (design section 3.3). The leading ``Intent
    <name>.`` / ``Slot <name>.`` header line is not a section and is not
    returned; every section's ``text`` is the exact substring
    ``content[start:end]``, so a caller can splice one out and put it back.
    """

    if not isinstance(content, str) or not content:
        raise KnowledgeIndexError("a card must be non-empty text")
    heads: list[tuple[str, int]] = []
    offset = 0
    for line in content.split("\n"):
        match = _SECTION_HEAD.fullmatch(line)
        if match is not None:
            heads.append((match.group(1), offset))
        offset += len(line) + 1
    sections: list[CardSection] = []
    for index, (name, start) in enumerate(heads):
        end = heads[index + 1][1] - 1 if index + 1 < len(heads) else len(content)
        sections.append(
            CardSection(name=name, text=content[start:end], start=start, end=end)
        )
    if not sections:
        raise KnowledgeIndexError("a released card must carry labelled sections")
    return tuple(sections)


def section_body(section: CardSection) -> str:
    """The section's own statement, without its label.

    ``Label: text`` yields ``text``; ``Label:`` followed by ``- `` bullets
    yields the bullet bodies joined by one space, in card order. Both forms
    occur in the released stores and both are one operative line.
    """

    lines = section.text.split("\n")
    head = _SECTION_HEAD.fullmatch(lines[0])
    if head is None:
        raise KnowledgeIndexError("a card section must start with its label")
    inline = head.group(2)
    bullets = [
        match.group(1)
        for match in (_BULLET.fullmatch(line) for line in lines[1:])
        if match is not None
    ]
    if inline:
        if bullets:
            raise KnowledgeIndexError(
                f"card section {section.name!r} mixes an inline statement with bullets"
            )
        return inline
    if not bullets:
        raise KnowledgeIndexError(f"card section {section.name!r} states nothing")
    return " ".join(bullets)


def labelled_bullets(section: CardSection) -> dict[str, str]:
    """``{neighbour: statement}`` for a section whose bullets are ``- x: y``.

    This is what folds ``Confusable exclusions`` into the EDGE entries: each
    bullet already names the neighbour it separates this intent from.
    """

    found: dict[str, str] = {}
    for line in section.text.split("\n")[1:]:
        match = _LABELLED_BULLET.fullmatch(line)
        if match is None:
            continue
        found[match.group(1)] = match.group(2)
    return found


@dataclass(frozen=True)
class HoistedSection:
    """One section lifted out of a card into the index's section headers.

    ``offset`` is the position in the RESIDUE where the section's text was
    removed from, so :func:`restore_card` is an exact splice and the hoist is
    provably lossless.
    """

    label: str
    section: str
    offset: int
    chars: int

    def as_json(self) -> dict[str, object]:
        return {
            "label": self.label, "section": self.section,
            "offset": self.offset, "chars": self.chars,
        }


def hoist_sections(
    content: str, *, sections: Sequence[CardSection], labels: Mapping[str, str],
) -> tuple[str, tuple[HoistedSection, ...]]:
    """Splice ``sections`` out of ``content`` and record where they were.

    ``labels`` maps a section's exact text to its shared-group label. Removal
    takes the section's own bytes plus the newline that joined it to the
    previous section, which is what makes the residue a well-formed card and
    the restore exact.
    """

    ordered = sorted(sections, key=lambda item: item.start, reverse=True)
    residue = content
    removed: list[HoistedSection] = []
    for section in ordered:
        label = labels.get(section.text)
        if label is None:
            raise KnowledgeIndexError(
                f"section {section.name!r} has no shared-group label"
            )
        start = section.start
        end = section.end
        if start > 0 and residue[start - 1] == "\n":
            start -= 1
        residue = residue[:start] + residue[end:]
        removed.append(
            HoistedSection(
                label=label, section=section.name, offset=start,
                chars=section.chars,
            )
        )
    return residue, tuple(sorted(removed, key=lambda item: item.offset))


def restore_card(
    residue: str, hoisted: Sequence[HoistedSection], shared: Mapping[str, str],
) -> str:
    """The original released card, byte for byte.

    The falsifier of the whole hoist: index text = header + per-card residue,
    and this function is what a test runs over every card of the view to
    prove the factoring lost nothing (design Q6, finding F-5).
    """

    restored = residue
    for item in sorted(hoisted, key=lambda entry: entry.offset, reverse=True):
        text = shared.get(item.label)
        if text is None:
            raise KnowledgeIndexError(f"shared section {item.label!r} is absent")
        if len(text) != item.chars:
            raise KnowledgeIndexError(
                f"shared section {item.label!r} is {len(text)} characters, not the "
                f"recorded {item.chars}"
            )
        restored = f"{restored[:item.offset]}\n{text}{restored[item.offset:]}"
    return restored


# ---------------------------------------------------------------------------
# 4. The view: entries, shared sections, the table and its loader.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SharedSection:
    """One hoisted card section, once, in the index's own header."""

    label: str
    kind: str
    section: str
    text: str

    def as_json(self) -> dict[str, object]:
        return {
            "label": self.label, "kind": self.kind, "section": self.section,
            "text": self.text,
        }


@dataclass(frozen=True)
class IndexEntry:
    """One addressable unit of the knowledge space.

    ``l1`` maps a section name to that section's one operative line, for
    every section this kind's L1 may be drawn from; ``residue`` is the L2
    card with the hoisted sections spliced out (empty for an ``edge``, whose
    whole content is one folded bullet).
    """

    entry_id: str
    kind: str
    group: str
    rank: int
    l1: Mapping[str, str]
    residue: str = ""
    hoisted: tuple[HoistedSection, ...] = ()

    def __post_init__(self) -> None:
        kind, _parts = parse_index_id(self.entry_id)
        if kind != self.kind:
            raise KnowledgeIndexError(
                f"entry {self.entry_id!r} declares kind {self.kind!r}"
            )
        if self.kind not in CONSTANT_INDEX_KINDS:
            raise KnowledgeIndexError(
                f"kind {self.kind!r} is pointer-and-expansion only and may not be "
                "an index entry"
            )
        if isinstance(self.rank, bool) or not isinstance(self.rank, int) or self.rank < 0:
            raise KnowledgeIndexError("an entry rank must be a nonnegative count")
        if not isinstance(self.l1, Mapping) or not self.l1:
            raise KnowledgeIndexError(f"entry {self.entry_id!r} states no L1 line")

    @property
    def name(self) -> str:
        return display_name(self.entry_id)

    def line(self, *, level: str, section: str) -> str:
        """This entry's rendered index line at one granularity.

        L0 is the ID ALONE, and that is not a shortcut: id grammar rule 1
        says the name inside an id is the one the closed contract inventory
        already legalises, VERBATIM, so ``I/play_music`` already carries the
        display name and printing a second, unscored spelling beside it would
        be exactly the second spelling of a closed label that rule 1 exists
        to prevent (it also costs about 2,500 characters of constant prefix
        across the 195 entries, for no information). The section LABEL is
        stated once, in the section header, for the same reason -- paying for
        a per-kind constant on every line is the mistake finding F-5 measures
        inside the cards themselves.
        """

        if level not in GRANULARITY_LEVELS:
            raise KnowledgeIndexError(f"unknown granularity level {level!r}")
        head = self.entry_id
        if level == "L0":
            return head
        statement = self.l1.get(section)
        if statement is None:
            raise KnowledgeIndexError(
                f"entry {self.entry_id!r} carries no {section!r} line; the view was "
                f"built with {sorted(self.l1)}"
            )
        return f"{head}  {statement}"

    def as_json(self) -> dict[str, object]:
        return {
            "id": self.entry_id,
            "kind": self.kind,
            "group": self.group,
            "rank": self.rank,
            "l1": {name: self.l1[name] for name in sorted(self.l1)},
            "residue": self.residue,
            "hoisted": [item.as_json() for item in self.hoisted],
        }


def entry_from_json(document: object) -> IndexEntry:
    if not isinstance(document, Mapping) or set(document) != {
        "id", "kind", "group", "rank", "l1", "residue", "hoisted",
    }:
        raise KnowledgeIndexError("an index entry has unknown or missing fields")
    hoisted = document["hoisted"]
    if not isinstance(hoisted, list):
        raise KnowledgeIndexError("an index entry's hoisted table must be a list")
    rows: list[HoistedSection] = []
    for row in hoisted:
        if not isinstance(row, Mapping) or set(row) != {
            "label", "section", "offset", "chars",
        }:
            raise KnowledgeIndexError("a hoisted section has unknown fields")
        rows.append(
            HoistedSection(
                label=str(row["label"]), section=str(row["section"]),
                offset=int(row["offset"]), chars=int(row["chars"]),
            )
        )
    l1 = document["l1"]
    if not isinstance(l1, Mapping):
        raise KnowledgeIndexError("an index entry's L1 table must be an object")
    return IndexEntry(
        entry_id=str(document["id"]),
        kind=str(document["kind"]),
        group=str(document["group"]),
        rank=int(document["rank"]),
        l1={str(key): str(value) for key, value in l1.items()},
        residue=str(document["residue"]),
        hoisted=tuple(rows),
    )


@dataclass(frozen=True)
class KnowledgeIndexTable:
    """The released, pinned view the constant index is rendered from."""

    view_id: str
    builder_policy_id: str
    carrier: str
    ordering: str
    source_split: str
    source_split_identity_hash: str
    construction_utterance_count: int
    entries: tuple[IndexEntry, ...]
    shared_sections: tuple[SharedSection, ...]
    legal_intents: tuple[str, ...]
    legal_slot_types: tuple[str, ...]
    #: The released source stores' own pins, verbatim. Provenance only: the
    #: index never reaches for a store at runtime.
    store_pins: Mapping[str, object]
    release_sha256: str = ""
    snapshot_sha256: str = ""

    def __post_init__(self) -> None:
        ids = [entry.entry_id for entry in self.entries]
        if len(set(ids)) != len(ids):
            raise KnowledgeIndexError("index entry ids must be unique")

    @property
    def entry_ids(self) -> frozenset[str]:
        return frozenset(entry.entry_id for entry in self.entries)

    @property
    def kinds(self) -> frozenset[str]:
        return frozenset(entry.kind for entry in self.entries)

    def counts(self) -> dict[str, int]:
        return {
            kind: sum(1 for entry in self.entries if entry.kind == kind)
            for kind in CONSTANT_INDEX_KINDS
        }

    def entry(self, entry_id: str) -> IndexEntry | None:
        for entry in self.entries:
            if entry.entry_id == entry_id:
                return entry
        return None

    def shared(self) -> dict[str, str]:
        return {row.label: row.text for row in self.shared_sections}

    def resolves(self, entry_id: object) -> bool:
        """Whether a cited id names an entry this index actually carries.

        Membership, never parsing: an ``exemplar`` id resolves when its key
        is one the row was pointed at, which the caller supplies through
        :meth:`RowSelection.expanded_ids`; here only constant-index entries
        are known, which is exactly what "resolves in the index" means.
        """

        return isinstance(entry_id, str) and entry_id in self.entry_ids

    def content_hash(self) -> str:
        return _sha256_bytes(canonical_json(self.as_json()).encode("utf-8"))

    def as_json(self) -> dict[str, object]:
        return {
            "schema": KNOWLEDGE_INDEX_VIEW_SCHEMA,
            "view_id": self.view_id,
            "builder_policy_id": self.builder_policy_id,
            "carrier": self.carrier,
            "ordering": self.ordering,
            "source_split": self.source_split,
            "source_split_identity_hash": self.source_split_identity_hash,
            "construction_utterance_count": self.construction_utterance_count,
            "legal_intents": list(self.legal_intents),
            "legal_slot_types": list(self.legal_slot_types),
            "store_pins": {
                role: dict(pin) for role, pin in sorted(self.store_pins.items())
            },
            "shared_sections": [row.as_json() for row in self.shared_sections],
            "entries": [entry.as_json() for entry in self.entries],
        }


def table_from_snapshot(
    document: object, *, release_sha256: str = "", snapshot_sha256: str = "",
) -> KnowledgeIndexTable:
    """Build the table from one released snapshot document, fail-closed."""

    required = {
        "schema", "view_id", "builder_policy_id", "carrier", "ordering",
        "source_split", "source_split_identity_hash",
        "construction_utterance_count", "legal_intents", "legal_slot_types",
        "store_pins", "shared_sections", "entries",
    }
    if not isinstance(document, Mapping) or set(document) != required:
        raise KnowledgeIndexError("the index snapshot has unknown or missing fields")
    if document["schema"] != KNOWLEDGE_INDEX_VIEW_SCHEMA:
        raise KnowledgeIndexError("the index snapshot is not this view's schema")
    if document["source_split"] != "train":
        raise KnowledgeIndexError(
            "the index must be built from the TRAIN construction pool"
        )
    if document["ordering"] not in registered_orderings():
        raise KnowledgeIndexError(
            f"the index snapshot declares ordering {document['ordering']!r}, which "
            "is not registered in core.base.KNOWLEDGE_INDEX_ORDERINGS"
        )
    shared_rows = document["shared_sections"]
    if not isinstance(shared_rows, list):
        raise KnowledgeIndexError("shared_sections must be a list")
    shared: list[SharedSection] = []
    for row in shared_rows:
        if not isinstance(row, Mapping) or set(row) != {
            "label", "kind", "section", "text",
        }:
            raise KnowledgeIndexError("a shared section has unknown fields")
        shared.append(
            SharedSection(
                label=str(row["label"]), kind=str(row["kind"]),
                section=str(row["section"]), text=str(row["text"]),
            )
        )
    entries = document["entries"]
    if not isinstance(entries, list) or not entries:
        raise KnowledgeIndexError("the index snapshot carries no entry")
    return KnowledgeIndexTable(
        view_id=str(document["view_id"]),
        builder_policy_id=str(document["builder_policy_id"]),
        carrier=str(document["carrier"]),
        ordering=str(document["ordering"]),
        source_split=str(document["source_split"]),
        source_split_identity_hash=str(document["source_split_identity_hash"]),
        construction_utterance_count=int(document["construction_utterance_count"]),
        entries=tuple(entry_from_json(row) for row in entries),
        shared_sections=tuple(shared),
        legal_intents=tuple(str(value) for value in document["legal_intents"]),
        legal_slot_types=tuple(str(value) for value in document["legal_slot_types"]),
        # Provenance, carried VERBATIM: these are the released stores' own
        # pins, and re-typing them here would make the view's content hash a
        # function of this loader rather than of the released bytes.
        store_pins=json.loads(json.dumps(document["store_pins"])),
        release_sha256=release_sha256,
        snapshot_sha256=snapshot_sha256,
    )


def validate_knowledge_index_pin(value: object, *, field_name: str) -> Mapping[str, str]:
    """The one pin validator, public because the config loader checks a pin's
    SHAPE before any released file needs to exist -- so a fragment can be
    validated, and its hash composed, on a machine with no data root."""

    if (
        not isinstance(value, Mapping)
        or set(value) != _PIN_KEYS
        or not isinstance(value["relpath"], str)
        or not isinstance(value["root"], str)
        or not isinstance(value["sha256"], str)
    ):
        raise KnowledgeIndexError(
            f"{field_name} must be a pin declaring exactly relpath, root and sha256"
        )
    relpath, root, digest = value["relpath"], value["root"], value["sha256"]
    if root != PIN_ROOT:
        raise KnowledgeIndexError(
            f"{field_name}.root must be {PIN_ROOT!r}; the released knowledge index "
            "lives under the controlled data root"
        )
    if (
        not relpath.startswith(PIN_NAMESPACE)
        or relpath.startswith("/")
        or "\\" in relpath
        or ".." in Path(relpath).parts
    ):
        raise KnowledgeIndexError(
            f"{field_name}.relpath must be a plain relative POSIX path under "
            f"{PIN_NAMESPACE}"
        )
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise KnowledgeIndexError(f"{field_name}.sha256 must be a lower-case sha256")
    return {"relpath": relpath, "root": root, "sha256": digest}


def _read_pinned(data_root: Path, pin: Mapping[str, str], *, field_name: str) -> object:
    root = Path(data_root).resolve()
    path = (root / pin["relpath"]).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise KnowledgeIndexError(f"{field_name} escapes the data root") from None
    if not path.is_file():
        raise KnowledgeIndexError(f"{field_name} names no file: {path}")
    raw = path.read_bytes()
    measured = _sha256_bytes(raw)
    if measured != pin["sha256"]:
        raise KnowledgeIndexError(
            f"{field_name} hashes to {measured}, not the pinned {pin['sha256']}"
        )
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise KnowledgeIndexError(f"{field_name} is not JSON: {error}") from error


def load_knowledge_index_table(
    data_root: Path, *, release: object, snapshot: object, view_id: str,
) -> KnowledgeIndexTable:
    """Load the released view from its two pinned data-root files.

    Refusal 1 of design section 6.4, in its byte form: each file's bytes must
    hash to its declared pin, the release must name this view id and the
    snapshot's own pin, and the two documents must agree on the builder
    policy and the construction identity. No network, no repository, no model.
    """

    release_pin = validate_knowledge_index_pin(
        release, field_name="knowledge_index.release"
    )
    snapshot_pin = validate_knowledge_index_pin(
        snapshot, field_name="knowledge_index.snapshot"
    )
    release_document = _read_pinned(
        data_root, release_pin, field_name="knowledge_index.release"
    )
    snapshot_document = _read_pinned(
        data_root, snapshot_pin, field_name="knowledge_index.snapshot"
    )
    if (
        not isinstance(release_document, Mapping)
        or release_document.get("schema") != KNOWLEDGE_INDEX_RELEASE_SCHEMA
        or release_document.get("view_id") != view_id
        or release_document.get("snapshot_sha256") != snapshot_pin["sha256"]
    ):
        raise KnowledgeIndexError(
            "knowledge_index.release is not this view's release, or does not pin "
            "the declared snapshot"
        )
    if (
        not isinstance(snapshot_document, Mapping)
        or snapshot_document.get("view_id") != view_id
    ):
        raise KnowledgeIndexError("knowledge_index.snapshot is not this view's snapshot")
    if release_document.get("builder_policy_id") != snapshot_document.get(
        "builder_policy_id"
    ) or release_document.get("source_split_identity_hash") != snapshot_document.get(
        "source_split_identity_hash"
    ):
        raise KnowledgeIndexError(
            "knowledge_index release and snapshot disagree on the construction identity"
        )
    return table_from_snapshot(
        snapshot_document,
        release_sha256=release_pin["sha256"],
        snapshot_sha256=snapshot_pin["sha256"],
    )


# ---------------------------------------------------------------------------
# 5. The ordering (design section 3.4), registered in core.base.
# ---------------------------------------------------------------------------


def taxonomy_frequency_order(entries: Sequence[IndexEntry]) -> tuple[IndexEntry, ...]:
    """Scenario, then construction frequency, with each intent's edges after it.

    (a) taxonomy first: the SLURP intent ids ARE the taxonomy
        (``<scenario>_<action>`` over 18 scenarios), and the contract already
        renders them grouped;
    (b) within a group, most-frequent construction first, ties by id;
    (c) an intent's confusion edges on the lines after it, most-leaked first
        as the released table ordered them;
    (d) slots last, as their own group, ordered by construction frequency then
        id.

    Deterministic and total: two entries never compare equal unless they are
    the same id, so the rendered index is a pure function of the view.
    """

    intents = [entry for entry in entries if entry.kind == "intent"]
    slots = [entry for entry in entries if entry.kind == "slot"]
    edges_by_source: dict[str, list[IndexEntry]] = {}
    for entry in entries:
        if entry.kind != "edge":
            continue
        source = parse_index_id(entry.entry_id)[1][0]
        edges_by_source.setdefault(source, []).append(entry)
    ordered: list[IndexEntry] = []
    for entry in sorted(
        intents, key=lambda item: (item.group, -item.rank, item.entry_id)
    ):
        ordered.append(entry)
        source = parse_index_id(entry.entry_id)[1][0]
        ordered.extend(
            sorted(
                edges_by_source.get(source, ()),
                key=lambda item: (-item.rank, item.entry_id),
            )
        )
    ordered.extend(
        sorted(slots, key=lambda item: (-item.rank, item.entry_id))
    )
    seen = {entry.entry_id for entry in ordered}
    ordered.extend(entry for entry in entries if entry.entry_id not in seen)
    return tuple(ordered)


def _register_orderings() -> None:
    """Populate ``core.base.KNOWLEDGE_INDEX_*``.

    Function-local import for the reason every other registration site in
    this package uses one: ``core.base`` is imported by everything and this
    module must stay importable without it having been populated first.
    """

    from ..core.base import (  # noqa: PLC0415
        CoreError,
        KNOWLEDGE_INDEX_ORDERINGS,
        KNOWLEDGE_INDEX_RECEIPTS,
        KNOWLEDGE_INDEX_VIEWS,
    )

    for registry, name, entry in (
        (KNOWLEDGE_INDEX_ORDERINGS, TAXONOMY_FREQUENCY_ORDERING, taxonomy_frequency_order),
        (KNOWLEDGE_INDEX_VIEWS, KNOWLEDGE_INDEX_VIEW_ID, KNOWLEDGE_INDEX_BUILDER_POLICY_ID),
        (KNOWLEDGE_INDEX_RECEIPTS, KNOWLEDGE_INDEX_RECEIPT_SCHEMA, KNOWLEDGE_INDEX_VIEW_ID),
    ):
        try:
            registry.register(name, entry)
        except CoreError:
            # Already registered: this module is imported from several seams
            # and registration is idempotent by identity, never by overwrite.
            if registry.resolve(name) is not entry:
                raise


def registered_orderings() -> list[str]:
    """The ordering ids ``core.base`` admits."""

    from ..core.base import KNOWLEDGE_INDEX_ORDERINGS  # noqa: PLC0415

    _register_orderings()
    return KNOWLEDGE_INDEX_ORDERINGS.names()


def resolve_ordering(ordering_id: str):
    """The registered ordering callable. Refusal 6 of design section 6.4."""

    from ..core.base import KNOWLEDGE_INDEX_ORDERINGS, CoreError  # noqa: PLC0415

    _register_orderings()
    try:
        return KNOWLEDGE_INDEX_ORDERINGS.resolve(ordering_id)
    except CoreError as error:
        raise KnowledgeIndexError(
            f"knowledge_index.ordering is invalid: {error}"
        ) from error


# ---------------------------------------------------------------------------
# 6. The one config key -> a resolved plan.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IndexBudget:
    """One role's pointer and expansion allowance."""

    pointer: Mapping[str, int]
    expansion: Mapping[str, int]

    def as_json(self) -> dict[str, object]:
        return {
            "pointer_budget": {key: int(self.pointer[key]) for key in POINTER_BUDGET_KEYS},
            "expansion_budget": {
                key: int(self.expansion[key]) for key in EXPANSION_BUDGET_KEYS
            },
        }


@dataclass(frozen=True)
class IndexPlan:
    """The resolved ``native_episode.knowledge_index``."""

    view_id: str
    release: Mapping[str, str]
    snapshot: Mapping[str, str]
    granularity: Mapping[str, str]
    l1_sections: Mapping[str, str]
    ordering: str
    budget: IndexBudget
    solver_citation: str
    role_budgets: Mapping[str, IndexBudget]

    def budget_for(self, role_id: object) -> IndexBudget:
        """The block this role receives.

        Q12's default, stated once: with no override table every role
        receives the SAME block the Solver receives, which is today's
        byte-identical-evidence shape (finding F-4).
        """

        if isinstance(role_id, str):
            override = self.role_budgets.get(role_id)
            if override is not None:
                return override
        return self.budget

    def as_json(self) -> dict[str, object]:
        document: dict[str, object] = {
            "view": self.view_id,
            "release": dict(self.release),
            "snapshot": dict(self.snapshot),
            "granularity": {
                kind: {"level": self.granularity[kind], "section": self.l1_sections[kind]}
                for kind in sorted(self.granularity)
            },
            "ordering": self.ordering,
            "solver_citation": self.solver_citation,
            **self.budget.as_json(),
        }
        if self.role_budgets:
            document["roles"] = {
                role: self.role_budgets[role].as_json()
                for role in sorted(self.role_budgets)
            }
        return document


def _budget_block(
    declared: object, *, keys: Sequence[str], defaults: Mapping[str, int], field: str,
) -> dict[str, int]:
    values = {key: int(defaults[key]) for key in keys}
    if declared is None:
        return values
    if not isinstance(declared, Mapping):
        raise KnowledgeIndexError(f"{field} must be an object")
    unknown = sorted(set(declared) - set(keys))
    if unknown:
        raise KnowledgeIndexError(
            f"{field} carries unknown budget(s) {unknown}; the declared set is "
            f"{list(keys)}"
        )
    for name, value in declared.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise KnowledgeIndexError(f"{field}.{name} must be a nonnegative integer")
        values[name] = int(value)
    return values


def _granularity_block(declared: object) -> tuple[dict[str, str], dict[str, str]]:
    levels = dict(DEFAULT_GRANULARITY)
    sections = dict(DEFAULT_L1_SECTIONS)
    if declared is None:
        return levels, sections
    if not isinstance(declared, Mapping):
        raise KnowledgeIndexError("knowledge_index.granularity must be an object")
    unknown = sorted(set(declared) - set(CONSTANT_INDEX_KINDS))
    if unknown:
        # Refusal 2 of design section 6.4, in its config form: a granularity
        # naming an entry kind the view does not carry. ``exemplar`` is the
        # one that will be tried, and it is refused by name.
        raise KnowledgeIndexError(
            f"knowledge_index.granularity names entry kind(s) {unknown} the constant "
            f"index does not carry; it carries {list(CONSTANT_INDEX_KINDS)} "
            "(the exemplar kind is pointer-and-expansion only)"
        )
    for kind, value in declared.items():
        if isinstance(value, str):
            level, section = value, DEFAULT_L1_SECTIONS[kind]
        elif isinstance(value, Mapping) and set(value) == {"level", "section"}:
            level, section = value["level"], value["section"]
        else:
            raise KnowledgeIndexError(
                f"knowledge_index.granularity.{kind} must be a level string or an "
                "object with exactly a level and a section"
            )
        if level not in GRANULARITY_LEVELS:
            raise KnowledgeIndexError(
                f"knowledge_index.granularity.{kind}.level must be one of "
                f"{list(GRANULARITY_LEVELS)}"
            )
        if section not in L1_SECTION_CHOICES[kind]:
            raise KnowledgeIndexError(
                f"knowledge_index.granularity.{kind}.section must be one of "
                f"{list(L1_SECTION_CHOICES[kind])}"
            )
        levels[kind] = level
        sections[kind] = section
    return levels, sections


_REQUIRED_KEYS = frozenset({"view", "release", "snapshot"})
_OPTIONAL_KEYS = frozenset({
    "granularity", "ordering", "pointer_budget", "expansion_budget",
    "solver_citation", "roles",
})


def parse_knowledge_index_config(document: object) -> IndexPlan:
    """Resolve ``native_episode.knowledge_index`` into a plan, fail-closed."""

    if not isinstance(document, Mapping):
        raise KnowledgeIndexError(
            "native_episode.knowledge_index must be an object declaring "
            f"{sorted(_REQUIRED_KEYS)}"
        )
    unknown = sorted(set(document) - _REQUIRED_KEYS - _OPTIONAL_KEYS)
    if unknown or not _REQUIRED_KEYS <= set(document):
        raise KnowledgeIndexError(
            "native_episode.knowledge_index has unknown or missing fields; it "
            f"declares {sorted(_REQUIRED_KEYS)} and may add {sorted(_OPTIONAL_KEYS)}"
        )
    view_id = document["view"]
    if view_id != KNOWLEDGE_INDEX_VIEW_ID:
        # Refusal 1, in its config form: only a RELEASED view id is admitted.
        raise KnowledgeIndexError(
            f"native_episode.knowledge_index.view must be {KNOWLEDGE_INDEX_VIEW_ID!r}; "
            f"{view_id!r} is not a released knowledge-index view"
        )
    release = validate_knowledge_index_pin(
        document["release"], field_name="knowledge_index.release"
    )
    snapshot = validate_knowledge_index_pin(
        document["snapshot"], field_name="knowledge_index.snapshot"
    )
    levels, sections = _granularity_block(document.get("granularity"))
    ordering = document.get("ordering", TAXONOMY_FREQUENCY_ORDERING)
    if not isinstance(ordering, str) or not ordering.strip():
        raise KnowledgeIndexError("knowledge_index.ordering must be a non-empty string")
    resolve_ordering(ordering)
    pointer = _budget_block(
        document.get("pointer_budget"), keys=POINTER_BUDGET_KEYS,
        defaults=DEFAULT_POINTER_BUDGET, field="knowledge_index.pointer_budget",
    )
    expansion = _budget_block(
        document.get("expansion_budget"), keys=EXPANSION_BUDGET_KEYS,
        defaults=DEFAULT_EXPANSION_BUDGET, field="knowledge_index.expansion_budget",
    )
    citation = document.get("solver_citation", DEFAULT_SOLVER_CITATION)
    if citation not in SOLVER_CITATION_MODES:
        raise KnowledgeIndexError(
            "knowledge_index.solver_citation must be 'permitted' or 'required'"
        )
    if citation == "required":
        # Q7: a REQUIRED citation is a ``response_format_id`` change and a
        # second factor -- it changes the answer surface, which is where the
        # official scorer reads. Refused by name until that cell exists.
        raise KnowledgeIndexError(
            "knowledge_index.solver_citation 'required' changes the Solver's answer "
            "surface and is a second factor; only 'permitted' is implemented (design "
            "question Q7)"
        )
    role_budgets = _role_budgets(document.get("roles"), pointer, expansion)
    return IndexPlan(
        view_id=view_id,
        release=release,
        snapshot=snapshot,
        granularity=levels,
        l1_sections=sections,
        ordering=ordering,
        budget=IndexBudget(pointer=pointer, expansion=expansion),
        solver_citation=citation,
        role_budgets=role_budgets,
    )


def _role_budgets(
    declared: object, pointer: Mapping[str, int], expansion: Mapping[str, int],
) -> dict[str, IndexBudget]:
    if declared is None:
        return {}
    if not isinstance(declared, Mapping) or not declared:
        raise KnowledgeIndexError(
            "knowledge_index.roles, when declared, must be a non-empty object of "
            "per-role budget overrides"
        )
    unknown = sorted(set(declared) - set(OVERRIDABLE_ROLES))
    if unknown:
        raise KnowledgeIndexError(
            f"knowledge_index.roles names no episode role: {unknown}"
        )
    budgets: dict[str, IndexBudget] = {}
    for role, block in declared.items():
        if not isinstance(block, Mapping) or not set(block) <= {
            "pointer_budget", "expansion_budget",
        } or not block:
            raise KnowledgeIndexError(
                f"knowledge_index.roles.{role} must declare a pointer_budget, an "
                "expansion_budget, or both"
            )
        budgets[role] = IndexBudget(
            pointer=_budget_block(
                block.get("pointer_budget"), keys=POINTER_BUDGET_KEYS,
                defaults=pointer, field=f"knowledge_index.roles.{role}.pointer_budget",
            ),
            expansion=_budget_block(
                block.get("expansion_budget"), keys=EXPANSION_BUDGET_KEYS,
                defaults=expansion,
                field=f"knowledge_index.roles.{role}.expansion_budget",
            ),
        )
    return budgets


def validate_knowledge_index_config(document: object) -> str:
    """The canonical text of a validated ``knowledge_index`` block.

    Same contract every other episode module's validator carries: the parsed
    plan re-serialised canonically, so the config hash is a pure function of
    MEANING and two spellings of one arm compose one cell identity.
    """

    return canonical_json(parse_knowledge_index_config(document).as_json())


def is_knowledge_index_null_arm(value: object) -> bool:
    """The key's OFF arm: its ABSENCE. There is no third shape.

    An index is either rendered or it is not; with the key absent the request
    carries exactly its pre-E21 bytes and the receipt exactly its pre-E21
    fields.
    """

    return value is None


def parse_role_budget_override(value: object, *, role: str) -> Mapping[str, object]:
    """Validate a ``native_episode.roles.<role>.knowledge_index_budget`` block.

    Shape only: the numbers are resolved against the module's own budget by
    :func:`parse_knowledge_index_config`, so the role row and the module block
    can never drift into two different meanings of one override.
    """

    if not isinstance(value, Mapping) or not value or not set(value) <= {
        "pointer_budget", "expansion_budget",
    }:
        raise KnowledgeIndexError(
            f"native_episode.roles.{role}.{ROLE_BUDGET_KEY} must declare a "
            "pointer_budget, an expansion_budget, or both"
        )
    _budget_block(
        value.get("pointer_budget"), keys=POINTER_BUDGET_KEYS,
        defaults=DEFAULT_POINTER_BUDGET,
        field=f"native_episode.roles.{role}.{ROLE_BUDGET_KEY}.pointer_budget",
    )
    _budget_block(
        value.get("expansion_budget"), keys=EXPANSION_BUDGET_KEYS,
        defaults=DEFAULT_EXPANSION_BUDGET,
        field=f"native_episode.roles.{role}.{ROLE_BUDGET_KEY}.expansion_budget",
    )
    return {key: dict(value[key]) for key in sorted(value)}


# ---------------------------------------------------------------------------
# 7. The renderer: the constant index (design sections 3.3, 3.4, 3.7).
# ---------------------------------------------------------------------------

INDEX_HEADER = (
    "Knowledge index {view_id} (ordering {ordering}). Every entry below carries a "
    "short id. Cite an id exactly as written; never invent one, and never cite an "
    "id that is not listed here."
)


def render_constant_index(table: KnowledgeIndexTable, plan: IndexPlan) -> str:
    """The index, as a pure suffix of the already-rendered contract fill.

    A PURE function of the released view and the declared granularity -- the
    row never enters, which is what makes this text part of the prefix the
    per-slot KV cache keeps (design section 3.6: at ``-np 4`` over 1,080 rows
    a 3,526-token index costs 13.1 tokens per row).

    The template ``probes/slurp_native_role_context_v3.txt`` is NOT touched:
    the index extends the FILL, exactly as the closed inventory once extended
    the ontology (design section 3.7).
    """

    if table.ordering != plan.ordering:
        raise KnowledgeIndexError(
            f"the released view is ordered {table.ordering!r} but the config declares "
            f"{plan.ordering!r}"
        )
    order = resolve_ordering(plan.ordering)
    ordered = order(table.entries)
    shared_by_kind: dict[str, list[SharedSection]] = {}
    for row in table.shared_sections:
        shared_by_kind.setdefault(row.kind, []).append(row)
    lines: list[str] = [
        INDEX_HEADER.format(view_id=table.view_id, ordering=table.ordering)
    ]
    counts = table.counts()
    for kind in ("intent", "slot"):
        rows = shared_by_kind.get(kind, [])
        if not rows:
            continue
        lines.append(f"Shared {kind} guidance, referenced by label below:")
        lines.extend(
            f"[{row.label}] {row.text}" for row in sorted(rows, key=lambda r: r.label)
        )
    lines.append(
        f"Intent entries ({counts['intent']}), grouped by scenario, most frequent "
        f"construction first. Each I/ line is "
        f"{_line_shape('I/<intent>', kind='intent', plan=plan)}. Each E/ line names a "
        f"construction confusion pair ({counts['edge']} in total) as "
        f"{_line_shape('E/<intent>~<neighbour>', kind='edge', plan=plan)}."
    )
    group = None
    tail: list[str] = []
    for entry in ordered:
        if entry.kind == "slot":
            tail.append(entry.line(
                level=plan.granularity["slot"], section=plan.l1_sections["slot"]
            ))
            continue
        if entry.kind == "intent" and entry.group != group:
            group = entry.group
            lines.append(f"## {group}")
        lines.append(entry.line(
            level=plan.granularity[entry.kind], section=plan.l1_sections[entry.kind]
        ))
    lines.append(
        f"Slot entries ({counts['slot']} carded of {len(table.legal_slot_types)} legal "
        f"entity types). Each S/ line is "
        f"{_line_shape('S/<type>', kind='slot', plan=plan)}."
    )
    lines.extend(tail)
    return "\n".join(lines)


def _line_shape(pattern: str, *, kind: str, plan: IndexPlan) -> str:
    """How a kind's lines read, stated ONCE in its section header."""

    if plan.granularity[kind] == "L0":
        return f'"{pattern}"'
    return f'"{pattern}  <{plan.l1_sections[kind]}>"'


def index_suffix(table: KnowledgeIndexTable, plan: IndexPlan) -> str:
    """The exact suffix appended to the rendered contract fill."""

    return f"\n\n{render_constant_index(table, plan)}"


# ---------------------------------------------------------------------------
# 8. The assembly: the row's pointer block and its bounded expansion.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RowSelection:
    """What this row's speech and its own model state selected.

    Every field is a POINTER or a RANK, never a label: ``candidates`` are the
    Perception node's own hypotheses in its own order, ``exemplar_votes`` is
    the aggregation of the retrieved construction exemplars' own construction
    intents, ``slot_types`` are the types the candidate projection bound, and
    ``exemplars`` are the retrieved construction utterances in RETRIEVAL RANK
    order (today's rendering is lexicographic by evidence id and carries no
    rank at all -- M1 analysis section 4.2).
    """

    candidates: tuple[str, ...] = ()
    exemplar_votes: tuple[tuple[str, int], ...] = ()
    slot_types: tuple[str, ...] = ()
    exemplars: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        for name in self.candidates:
            _name(name, field="candidate intent")
        for name in self.slot_types:
            _name(name, field="bound slot type")
        for name, count in self.exemplar_votes:
            _name(name, field="voted intent")
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise KnowledgeIndexError("an exemplar vote must be a positive count")
        for key, content in self.exemplars:
            exemplar_id(key)
            if not isinstance(content, str) or not content:
                raise KnowledgeIndexError("an exemplar must carry its content")


@dataclass(frozen=True)
class ExpansionItem:
    """One L2 card or exemplar the row reads in full."""

    entry_id: str
    text: str

    @property
    def chars(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class IndexAssembly:
    """One contact's rendered pointer block and bounded expansion."""

    pointer_block: str
    pointer_ids: tuple[str, ...]
    expansions: tuple[ExpansionItem, ...]
    degradation: tuple[Mapping[str, object], ...] = ()

    @property
    def expanded_ids(self) -> tuple[str, ...]:
        return tuple(item.entry_id for item in self.expansions)

    @property
    def expansion_text(self) -> str:
        return "\n".join(f"{item.entry_id}  {item.text}" for item in self.expansions)

    def content_parts(self) -> tuple[dict[str, object], ...]:
        """The user-message content parts, in LAYOUT ORDER (design 4.1).

        The pointer block first -- short, row-specific, and therefore the
        exact byte where the cacheable prefix ends -- then the expansion
        block, one part per expanded entry, LAST in the knowledge region.
        Truncating the expansion block from its tail removes trailing parts
        and moves no byte before them, which is what keeps a compacted row's
        prefix a prefix of the uncompacted one.
        """

        parts: list[dict[str, object]] = [
            {
                "type": "text",
                "text": self.pointer_block,
                "evidence_id": POINTER_BLOCK_EVIDENCE_ID,
                "knowledge_role": "value",
            }
        ]
        parts.extend(
            {
                "type": "text",
                "text": f"{item.entry_id}  {item.text}",
                "evidence_id": item.entry_id,
                "knowledge_role": "value",
            }
            for item in self.expansions
        )
        return tuple(parts)

    def evidence_items(self) -> tuple[dict[str, object], ...]:
        """The same blocks as ``supplied_evidence`` payload items.

        The transport renders one item as ``[evidence <evidence_id>] <content>``,
        so the id the model reads IS the index id -- the store alias
        ``X/10005`` in place of ``train-exemplars::value:10005``.
        """

        return tuple(
            {
                "evidence_id": part["evidence_id"],
                "content": part["text"],
                "knowledge_role": "value",
                "source_uri": f"knowledge-index://{KNOWLEDGE_INDEX_VIEW_ID}/"
                              f"{part['evidence_id']}",
            }
            for part in self.content_parts()
        )


def render_pointer_block(selection: RowSelection, budget: IndexBudget) -> tuple[str, tuple[str, ...]]:
    """The row's pointers: ids, ranks and the neighbour vote, nothing else.

    Ordered by rank (or vote count), highest first, so a COMPACT disposition
    truncating the tail removes the least-supported pointer deterministically
    (design section 3.4(d)).
    """

    candidates = tuple(
        dict.fromkeys(selection.candidates)
    )[: max(int(budget.pointer["intent"]), 0)]
    votes = tuple(
        sorted(selection.exemplar_votes, key=lambda row: (-row[1], row[0]))
    )[: max(int(budget.pointer["exemplar_vote"]), 0)]
    slots = tuple(
        dict.fromkeys(selection.slot_types)
    )[: max(int(budget.pointer["slot"]), 0)]
    candidate_ids = tuple(intent_id(name) for name in candidates)
    vote_ids = tuple(intent_id(name) for name, _count in votes)
    slot_ids = tuple(slot_id(name) for name in slots)
    lines = [
        "Index pointers for this utterance. Each id resolves in the knowledge index "
        "above; the index states what the id means.",
        "Candidate intents, best first: " + (
            ", ".join(
                f"{value} (rank {rank})"
                for rank, value in enumerate(candidate_ids, start=1)
            ) or NO_CANDIDATES
        ),
        "Construction neighbour vote over the retrieved exemplars: " + (
            ", ".join(
                f"{intent_id(name)} x {count}" for name, count in votes
            ) or NO_VOTE
        ),
        "Slot types bound to these candidates: " + (
            ", ".join(slot_ids) or NO_SLOT_TYPES
        ),
    ]
    pointer_ids = tuple(dict.fromkeys(candidate_ids + vote_ids + slot_ids))
    return "\n".join(lines), pointer_ids


def render_expansions(
    table: KnowledgeIndexTable, selection: RowSelection, budget: IndexBudget,
) -> tuple[ExpansionItem, ...]:
    """The bounded expansion, most-relevant-first, in the declared classes.

    Exemplars first (retrieval rank), then the top candidate's bound slot
    cards, then intent cards -- so truncating from the TAIL spends the
    intent cards before the slot cards and the slot cards before the
    exemplars, which is the declared order and not a heuristic.
    """

    shared = table.shared()
    items: list[ExpansionItem] = []
    for key, content in selection.exemplars[: max(int(budget.expansion["exemplar"]), 0)]:
        items.append(ExpansionItem(entry_id=exemplar_id(key), text=content))
    for name in tuple(dict.fromkeys(selection.slot_types))[
        : max(int(budget.expansion["slot_card"]), 0)
    ]:
        entry = table.entry(slot_id(name))
        if entry is None:
            continue
        items.append(ExpansionItem(entry_id=entry.entry_id, text=_card_text(entry, shared)))
    for name in tuple(dict.fromkeys(selection.candidates))[
        : max(int(budget.expansion["intent_card"]), 0)
    ]:
        entry = table.entry(intent_id(name))
        if entry is None:
            continue
        items.append(ExpansionItem(entry_id=entry.entry_id, text=_card_text(entry, shared)))
    return tuple(items)


def _card_text(entry: IndexEntry, shared: Mapping[str, str]) -> str:
    """The L2 card as the expansion block renders it: the residue plus a
    REFERENCE to the shared sections the index header already carries.

    The reference is a rendering addition, never part of the residue --
    :func:`restore_card` still reproduces the released card byte for byte
    from the residue and the index's own shared text.
    """

    if not entry.hoisted:
        return entry.residue
    labels = ", ".join(sorted({item.label for item in entry.hoisted}))
    missing = [item.label for item in entry.hoisted if item.label not in shared]
    if missing:
        raise KnowledgeIndexError(f"shared section(s) {missing} are absent from the view")
    return f"{entry.residue}\nShared guidance: {labels}"


def assemble(
    table: KnowledgeIndexTable,
    plan: IndexPlan,
    selection: RowSelection,
    *,
    role_id: str | None = None,
) -> IndexAssembly:
    """One contact's assembly, at this role's own budget."""

    budget = plan.budget_for(role_id)
    pointer_block, pointer_ids = render_pointer_block(selection, budget)
    return IndexAssembly(
        pointer_block=pointer_block,
        pointer_ids=pointer_ids,
        expansions=render_expansions(table, selection, budget),
    )


# ---------------------------------------------------------------------------
# 9. The degradation ladder (design section 4.4), over E20's primitives.
# ---------------------------------------------------------------------------


def index_droppable_items(assembly: IndexAssembly) -> tuple[DroppableItem, ...]:
    """The index's own ladder, in the declared order, as E20 drop items.

    1. expansions, from the TAIL (lowest rank / lowest vote first);
    2. the pointer block, once every expansion is gone;
    3. the L1 index falls back to L0 -- recorded here as one granularity step,
       executed by re-rendering the prefix at L0.

    Never the L0 index, the contract, the speech packet or the states
    (:data:`INDEX_NEVER_DROPPABLE`). Rule 4 is the safety property: dropping
    L0 would let the model emit an id the closed inventory does not contain,
    which the delivery normaliser would then have to repair and the official
    scorer would count as a miss.

    This function does not change E20's own :func:`rails.context_fit.
    droppable_items`; it produces items in the SAME shape so one caller can
    concatenate the two ladders and drive both through
    :func:`rails.context_fit.apply_drops`.
    """

    if not isinstance(assembly, IndexAssembly):
        raise KnowledgeIndexError("index_droppable_items needs an IndexAssembly")
    items: list[DroppableItem] = []
    total = len(assembly.expansions)
    for position in range(total - 1, -1, -1):
        items.append(
            DroppableItem(
                block=INDEX_EXPANSION_BLOCK,
                identifier=f"value:{assembly.expansions[position].entry_id}",
                tranche=1,
                location="content",
                index=position + 1,
            )
        )
    items.append(
        DroppableItem(
            block=INDEX_POINTER_BLOCK,
            identifier=f"value:{POINTER_BLOCK_EVIDENCE_ID}",
            tranche=2,
            location="content",
            index=0,
        )
    )
    items.append(
        DroppableItem(
            block=INDEX_GRANULARITY_BLOCK,
            identifier="index:L1->L0",
            tranche=2,
            location="prefix",
            index=0,
        )
    )
    return tuple(items)


def degradation_step(item: DroppableItem, *, pass_index: int) -> dict[str, object]:
    """One recorded degradation step. Never silent: every step is a row
    disposition, the same honesty requirement owner decision 45 states for
    the serving side."""

    return {
        "block": item.block,
        "identifier": item.identifier,
        "pass": int(pass_index),
        "never_droppable": list(INDEX_NEVER_DROPPABLE),
    }


# ---------------------------------------------------------------------------
# 10. The receipt (design section 4.2, E17's block shape).
# ---------------------------------------------------------------------------


def contact_receipt(
    *,
    contact_id: str,
    role_id: str,
    assembly: IndexAssembly,
    system_message: str,
    index_text: str,
    cited_ids: Sequence[str] = (),
    table: KnowledgeIndexTable | None = None,
    degradation: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    """One contact's row of the per-row receipt block.

    Digests and counts only -- never the rendered TEXT: the expansion block
    carries construction utterances and released card text, and a receipt is
    not a place to copy them to.
    """

    pointer_block = assembly.pointer_block
    expansion_text = assembly.expansion_text
    resolved = 0
    unresolved: list[str] = []
    known = set(assembly.expanded_ids) | set(assembly.pointer_ids)
    for cited in cited_ids:
        if (table is not None and table.resolves(cited)) or cited in known:
            resolved += 1
        else:
            unresolved.append(cited)
    return {
        "contact_id": contact_id,
        "role_id": role_id,
        "pointer_ids": list(assembly.pointer_ids),
        "expanded_ids": list(assembly.expanded_ids),
        "pointer_block_sha256": sha256_text(pointer_block),
        "pointer_block_chars": len(pointer_block),
        "expansion_block_sha256": sha256_text(expansion_text),
        "expansion_block_chars": len(expansion_text),
        "index_sha256": sha256_text(index_text),
        "index_chars": len(index_text),
        "system_message_sha256": sha256_text(system_message),
        "cited_ids": list(cited_ids),
        "citations_resolved": resolved,
        "citations_unresolved": len(unresolved),
        "unresolved_ids": unresolved,
        "degradation": [dict(step) for step in degradation],
    }


def knowledge_index_receipt(
    *,
    plan: IndexPlan,
    table: KnowledgeIndexTable,
    index_text: str,
    contacts: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """The per-row block, sealed where E17's ``tool_schema_rendering`` is."""

    rows = [dict(row) for row in contacts]
    return {
        "schema": KNOWLEDGE_INDEX_RECEIPT_SCHEMA,
        "view": {
            "view_id": table.view_id,
            "release_sha256": table.release_sha256,
            "snapshot_sha256": table.snapshot_sha256,
            "content_hash": table.content_hash(),
        },
        "granularity": {
            kind: {"level": plan.granularity[kind], "section": plan.l1_sections[kind]}
            for kind in sorted(plan.granularity)
        },
        "ordering": plan.ordering,
        "solver_citation": plan.solver_citation,
        "pointer_budget": dict(plan.budget.pointer),
        "expansion_budget": dict(plan.budget.expansion),
        "role_budgets": {
            role: plan.role_budgets[role].as_json()
            for role in sorted(plan.role_budgets)
        },
        "index_sha256": sha256_text(index_text),
        "index_chars": len(index_text),
        "entry_counts": table.counts(),
        "contacts": rows,
        "distinct_system_message_sha256": len(
            {row["system_message_sha256"] for row in rows}
        ),
        "citations_resolved": sum(int(row["citations_resolved"]) for row in rows),
        "citations_unresolved": sum(int(row["citations_unresolved"]) for row in rows),
        "degradation_steps": sum(len(row["degradation"]) for row in rows),
    }


# ---------------------------------------------------------------------------
# 11. Applying the assembly to one logical request payload.
# ---------------------------------------------------------------------------


def _rebind_framework_history(history: Sequence[object], instruction: str) -> list:
    """Carry the armed instruction into the framework contact envelope.

    ``core.model.native_framework_history.validate_native_framework_contact``
    refuses a request whose framework ``messages[0]`` differs from its own
    ``task_instruction`` -- the custody rail that makes the framework's copy
    of the system message and the payload's ONE object. A live armed episode
    composes both from the same binding, so both carry the index; this
    function does the same thing to a re-composed sealed request, and
    re-hashes the envelope it rewrote rather than leaving a stale digest
    behind.
    """

    rebound: list = []
    for item in history:
        if not isinstance(item, Mapping):
            rebound.append(item)
            continue
        entry = dict(item)
        if entry.get("role") == "control" and isinstance(entry.get("content"), str):
            try:
                envelope = json.loads(entry["content"])
            except ValueError:
                rebound.append(entry)
                continue
            messages = (
                envelope.get("messages") if isinstance(envelope, Mapping) else None
            )
            if (
                isinstance(messages, list)
                and messages
                and isinstance(messages[0], Mapping)
                and messages[0].get("role") == "system"
            ):
                messages[0] = {"role": "system", "content": instruction}
                text = json.dumps(
                    envelope, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":"), allow_nan=False,
                )
                entry["content"] = text
                if "content_sha256" in entry:
                    entry["content_sha256"] = sha256_text(text)
        rebound.append(entry)
    return rebound


def apply_to_payload(
    payload: Mapping[str, object],
    *,
    index_text: str | None,
    assembly: IndexAssembly | None,
) -> dict[str, object]:
    """One sealed logical request, re-composed under the armed key.

    The index becomes a pure SUFFIX of ``task_instruction`` (the contract
    fill's own extension point, design section 3.7), and every ``value:``
    evidence item is replaced by the pointer block plus the bounded
    expansion, in layout order. ``key`` items -- the stable knowledge prefix
    -- are untouched, as is every other field of the payload.

    With ``index_text`` and ``assembly`` both ``None`` this returns the
    payload unchanged, which is the key's OFF arm and the byte-identity
    falsifier this item carries.
    """

    if not isinstance(payload, Mapping):
        raise KnowledgeIndexError("a request payload must be a mapping")
    if index_text is None and assembly is None:
        return dict(payload)
    if index_text is None or assembly is None:
        raise KnowledgeIndexError(
            "the index prefix and the pointer block are two halves of one mechanism; "
            "apply both or neither (design section 6.3)"
        )
    composed = dict(payload)
    instruction = payload.get("task_instruction")
    if not isinstance(instruction, str) or not instruction:
        raise KnowledgeIndexError("a request payload must carry its task_instruction")
    armed_instruction = f"{instruction}\n\n{index_text}"
    composed["task_instruction"] = armed_instruction
    composed["history"] = _rebind_framework_history(
        payload.get("history") or [], armed_instruction
    )
    supplied = payload.get("supplied_evidence") or []
    if not isinstance(supplied, Sequence) or isinstance(supplied, (str, bytes)):
        raise KnowledgeIndexError("supplied_evidence must be a sequence")
    kept = [
        dict(item) for item in supplied
        if isinstance(item, Mapping) and item.get("knowledge_role") != "value"
    ]
    composed["supplied_evidence"] = kept + [
        dict(item) for item in assembly.evidence_items()
    ]
    return composed


__all__ = [
    "CHARS_PER_TOKEN",
    "CONSTANT_INDEX_KINDS",
    "DEFAULT_EXPANSION_BUDGET",
    "DEFAULT_GRANULARITY",
    "DEFAULT_L1_SECTIONS",
    "DEFAULT_POINTER_BUDGET",
    "DEFAULT_SOLVER_CITATION",
    "ENTRY_KINDS",
    "EXEMPLAR_STORE_ROLE",
    "EXPANSION_BUDGET_KEYS",
    "GRANULARITY_LEVELS",
    "HOISTED_SECTIONS",
    "INDEX_DROP_ORDER",
    "INDEX_EXPANSION_BLOCK",
    "INDEX_GRANULARITY_BLOCK",
    "INDEX_NEVER_DROPPABLE",
    "INDEX_POINTER_BLOCK",
    "KIND_SIGILS",
    "KNOWLEDGE_INDEX_BUILDER_POLICY_ID",
    "KNOWLEDGE_INDEX_CARRIER",
    "KNOWLEDGE_INDEX_COMPLETION_SCHEMA",
    "KNOWLEDGE_INDEX_RECEIPT_SCHEMA",
    "KNOWLEDGE_INDEX_RELEASE_SCHEMA",
    "KNOWLEDGE_INDEX_VIEW_ID",
    "KNOWLEDGE_INDEX_VIEW_SCHEMA",
    "L1_SECTION_CHOICES",
    "MAX_HOISTED_DISTINCT",
    "NO_CANDIDATES",
    "NO_SLOT_TYPES",
    "NO_VOTE",
    "OVERRIDABLE_ROLES",
    "PIN_NAMESPACE",
    "PIN_ROOT",
    "POINTER_BLOCK_EVIDENCE_ID",
    "POINTER_BUDGET_KEYS",
    "POINTER_VOCABULARY",
    "ROLE_BUDGET_KEY",
    "SOLVER_CITATION_MODES",
    "TAXONOMY_FREQUENCY_ORDERING",
    "CardSection",
    "ExpansionItem",
    "HoistedSection",
    "IndexAssembly",
    "IndexBudget",
    "IndexEntry",
    "IndexPlan",
    "KnowledgeIndexError",
    "KnowledgeIndexTable",
    "RowSelection",
    "SharedSection",
    "apply_to_payload",
    "assemble",
    "canonical_json",
    "contact_receipt",
    "degradation_step",
    "display_name",
    "edge_id",
    "entry_from_json",
    "estimated_tokens",
    "exemplar_id",
    "extract_citations",
    "hoist_sections",
    "index_droppable_items",
    "index_suffix",
    "intent_id",
    "is_index_id",
    "is_knowledge_index_null_arm",
    "knowledge_index_receipt",
    "labelled_bullets",
    "load_knowledge_index_table",
    "parse_card_sections",
    "parse_index_id",
    "parse_knowledge_index_config",
    "parse_role_budget_override",
    "registered_orderings",
    "render_constant_index",
    "render_expansions",
    "render_pointer_block",
    "resolve_ordering",
    "restore_card",
    "section_body",
    "sha256_text",
    "slot_id",
    "table_from_snapshot",
    "taxonomy_frequency_order",
    "validate_knowledge_index_config",
    "validate_knowledge_index_pin",
]
