"""The SLURP slot KNOWLEDGE-VIEW family (KV): four renderings of TRAIN
knowledge into the slot phase's own per-sample block, and one form twin each.

Owner Decision 11-A, 2026-09-08: GO for the static slot-value cards, **and**
the slot task's local-optimisation space is widened from "the card" to the
whole knowledge-view space -- type DESCRIPTIONS, FEW-SHOT exemplars,
vocabulary CARDS, RETRIEVED knowledge -- each admitted one module at a time
against its own form twin.

Where these blocks travel, and why
-----------------------------------

KC-S1b's ADMITTED mechanism is a per-sample **instruction** block: the state
fill ``"slurp-intent-slot-schema-for-state"`` renders the sealed intent's
TRAIN slot schema and ``rails.phase_material.build_material_for_phase``
appends it after the sealed state. ``data.slurp.render_slurp_intent_slot_schema``
says in its own docstring why that is the right channel: the block is a
**USE-side instruction** (which types to fill and how to write a filler),
not a retrieved knowledge payload.

Every KV view occupies **that same slot in the prompt**. MF-10 section 2.3
measured the reason it has to: the schema block KC-S1b sends already prints
five example fillers per type, 194 of them card values, so a card shipped
BESIDE the block would be the second place the same string is written. The
resolution the family adopts is the one MF-10 handed on -- the view
**replaces** the five examples -- and a replacement has to occupy the
channel it replaces. So the factor a KV cell moves is the block's CONTENT at
a FIXED channel, contact count, geometry and directive.

The one view that is traced supply is **KV-4 = KU-S3** (retrieved fillers),
which is preregistered separately and keeps ``phase_supply``: it retrieves,
so it must be traced, and its typed values must not also sit in the
instruction. Composing it on KV-0 is exactly what makes that true.

Nothing in this module reads the filesystem, the network, a model or a
tokeniser. Every renderer takes already-loaded TRAIN material and returns a
string; ``rails.phase_material`` owns the loading. Every token figure is the
STATED PROXY MF-10 declared -- whitespace tokens times 1.3, rounded up,
through :func:`analysis.slurp_slot_vocabulary.token_proxy` -- and is never a
tokeniser measurement.

The four views, and the twin of each
-------------------------------------

* **KV-0 ``examples-free``** -- the per-intent schema block with its example
  fillers removed and a header that no longer promises them. It is the base
  every other view is measured against AND its own module test (examples
  against none). It needs no twin: it IS the null view.
* **KV-1 ``descriptions``** -- KV-0 plus one TRAIN-derived description line
  per listed type. A description line carries NO filler value: it carries the
  type's MF-10 class gloss and its TRAIN surface statistics (distinct forms,
  mentions, word length, digit habit, top-form concentration). A hand-written
  semantic gloss was rejected: it would be the author's knowledge rather than
  the corpus's, it could not be reproduced from committed bytes, and its twin
  could not be token-matched by construction. Twin: the intent's own type
  names permuted among themselves, so the same MULTISET of lines is attached
  to the wrong types -- identical characters, wrong pairing.
* **KV-2 ``cards``** -- KV-0 plus MF-10's full TRAIN vocabulary card for each
  CLOSED type the block lists. Twin: MF-10's per-intent
  ``derange_card_mapping``.
* **KV-3 ``fewshot``** -- KV-0 plus k = 3 TRAIN exemplars of that intent as
  ``transcript -> slots`` pairs, chosen by a deterministic seeded greedy cover
  of the intent's listed types. Text-only knowledge about OTHER utterances;
  the query's own transcript never appears and no DEV text is opened. Twin:
  the same k exemplars drawn from a DIFFERENT intent of the same scenario, so
  the twin carries scenario-typical language with the wrong slot structure.

Determinism
------------

Every selection here is a pure function of the TRAIN bytes, the intent, the
declared thresholds and :data:`FEWSHOT_SEED`. No wall clock, no filesystem
order, no set iteration order reaches a rendered string.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from ..analysis.slurp_slot_vocabulary import (
    SLOT_CLASS_CLOSED,
    SLOT_CLASS_MIXED,
    SLOT_CLASS_OPEN,
    VocabularyCard,
    containment_collisions,
    derange_card_mapping,
    render_card_set,
    token_proxy,
)
from .errors import RailsError

#: The four view ids a fragment may name in ``fill_params.view``.
KV_VIEW_EXAMPLES_FREE = "examples-free"
KV_VIEW_DESCRIPTIONS = "descriptions"
KV_VIEW_CARDS = "cards"
KV_VIEW_FEWSHOT = "fewshot"
KV_VIEWS = (
    KV_VIEW_EXAMPLES_FREE,
    KV_VIEW_DESCRIPTIONS,
    KV_VIEW_CARDS,
    KV_VIEW_FEWSHOT,
)

#: The cell id each view flies under, for receipts and the admission table.
KV_CELL_IDS = {
    KV_VIEW_EXAMPLES_FREE: "KV-0",
    KV_VIEW_DESCRIPTIONS: "KV-1",
    KV_VIEW_CARDS: "KV-2",
    KV_VIEW_FEWSHOT: "KV-3",
}

#: How many TRAIN exemplars KV-3 supplies per row.
FEWSHOT_K = 3

#: The seed the KV-3 exemplar selector is declared under. It enters through
#: one shuffle of the SORTED candidate utterance ids, so the selection is
#: reproducible from (seed, sorted ids) and from nothing else.
FEWSHOT_SEED = 20260903

#: KV-0's header. It deliberately does NOT promise example fillers -- the
#: block no longer carries any -- while keeping every other instruction the
#: admitted header carries, so the only thing KV-0 moves is the examples.
KV0_SCHEMA_HEADER = (
    "Slot schema measured on the TRAIN split, one block per intent. A block "
    "names the entity types that intent draws its slots from and how much of "
    "the intent's slot mentions each type carries. Use a type only when the "
    "speech supports it, and write each filler exactly as it was spoken, in "
    "lower case, without translating, expanding, abbreviating or reordering it."
)

#: KV-1's header.
DESCRIPTION_HEADER = (
    "Slot type descriptions measured on the TRAIN split. A description says "
    "what kind of value a type holds and how the corpus writes it -- how many "
    "distinct surface forms it uses, how long they are, whether it writes "
    "digits, and how concentrated the type is on its most frequent form. It "
    "names no filler; use it to judge whether a type fits what you heard."
)

#: KV-3's header.
FEWSHOT_HEADER = (
    "Worked TRAIN examples for this intent. Each line is one utterance the "
    "corpus recorded and the slots it carries, written the way the corpus "
    "writes them. They are OTHER utterances, never the one you are hearing; "
    "use them for the shape of an answer, never for its content."
)

#: The three class glosses, a DECLARED closed list. A description line's
#: prose comes from here and from the type's own TRAIN statistics; nothing
#: else, and nothing hand-written per type.
CLASS_GLOSSES = {
    SLOT_CLASS_CLOSED: "a closed vocabulary the corpus re-uses",
    SLOT_CLASS_MIXED: "a partly closed vocabulary",
    SLOT_CLASS_OPEN: "an open class the corpus keeps minting new forms for",
}

#: Digit-habit thresholds, declared before the table was rendered: the share
#: of a type's TRAIN mentions whose filler contains a digit.
DIGIT_HABIT_NONE = 0.0
DIGIT_HABIT_USUAL = 0.5


class SlurpKnowledgeViewError(RailsError):
    """A view, a twin or a selector refuses its own parameters."""


def assert_view(view: object) -> str:
    """The declared view id, or a fail-closed refusal."""

    if not isinstance(view, str) or view not in KV_VIEWS:
        raise SlurpKnowledgeViewError(
            f"unknown knowledge view {view!r}; the registered views are {list(KV_VIEWS)}"
        )
    return view


# ---------------------------------------------------------------------------
# KV-0 -- the example-free schema block
# ---------------------------------------------------------------------------


def render_examples_free_block(
    intent_types: Mapping[str, Sequence[tuple[str, int, float]]],
    *,
    intents: Sequence[str],
    utterances: Mapping[str, int],
    mentions: Mapping[str, int],
    min_share: float,
    header: str = KV0_SCHEMA_HEADER,
) -> str:
    """The per-intent slot schema block with **no example fillers**.

    Deliberately NOT ``data.slurp.load_slurp_intent_slot_schema(...,
    examples_per_type=0)`` rendered through the admitted renderer. That
    combination is what MF-10 section 2.3 proposed, and it renders every type
    as ``- date (34.6 percent of slot mentions): no example filler recorded``
    under a header that still promises "fillers heard with that type" -- a
    block that tells the model the corpus recorded no filler for `date`, which
    is false. KV-0 is the base of a whole family and has to be honest: it
    lists the types and their shares, and its header stops promising what it
    no longer carries.

    ``intent_types`` maps an intent to its ``(entity_type, count, share)``
    table; the three companion mappings carry the schema's own per-intent
    utterance and mention counts. They are passed in rather than read so this
    module opens no file.
    """

    floor_pct = f"{float(min_share) * 100:g}"
    lines: list[str] = [str(header)]
    for intent in intents:
        try:
            types = tuple(intent_types[intent])
        except KeyError:
            raise SlurpKnowledgeViewError(
                f"no slot table for intent {intent!r}"
            ) from None
        lines.append(
            f"== {intent} == {int(utterances[intent])} TRAIN utterances, "
            f"{int(mentions[intent])} slot mentions"
        )
        if not types:
            lines.append(
                f"- no entity type reaches the {floor_pct} percent floor for this "
                "intent; leave the entity list empty unless the speech plainly "
                "carries one"
            )
            continue
        for entity_type, _count, share in types:
            lines.append(
                f"- {entity_type} ({float(share) * 100:.1f} percent of slot mentions)"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# KV-1 -- TRAIN-derived type descriptions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypeDescription:
    """One slot type's description line, derived from TRAIN statistics alone.

    ``body`` carries no filler value, by construction: every field below is a
    COUNT, a RATIO or a word from :data:`CLASS_GLOSSES`.
    """

    entity_type: str
    slot_class: str
    train_mentions: int
    distinct_forms: int
    min_words: int
    median_words: int
    max_words: int
    digit_share: float
    top_form_share: float

    @property
    def digit_habit(self) -> str:
        if self.digit_share <= DIGIT_HABIT_NONE:
            return "written without digits"
        if self.digit_share < DIGIT_HABIT_USUAL:
            return "sometimes written with digits"
        return "usually written with digits"

    @property
    def body(self) -> str:
        gloss = CLASS_GLOSSES[self.slot_class]
        if self.median_words == self.max_words == self.min_words:
            length = (
                f"{self.median_words} word"
                if self.median_words == 1
                else f"{self.median_words} words"
            )
        else:
            length = (
                f"typically {self.median_words} "
                f"{'word' if self.median_words == 1 else 'words'} "
                f"({self.min_words} to {self.max_words})"
            )
        return (
            f"{gloss}; {self.distinct_forms} distinct TRAIN forms over "
            f"{self.train_mentions} mentions; {length}; {self.digit_habit}; its "
            f"most frequent form carries {self.top_form_share * 100:.1f} percent "
            "of them"
        )

    def as_json(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "slot_class": self.slot_class,
            "train_mentions": self.train_mentions,
            "distinct_forms": self.distinct_forms,
            "min_words": self.min_words,
            "median_words": self.median_words,
            "max_words": self.max_words,
            "digit_share": round(self.digit_share, 6),
            "top_form_share": round(self.top_form_share, 6),
            "body": self.body,
            "token_proxy": token_proxy(f"- {self.entity_type}: {self.body}"),
        }


def build_type_description(
    entity_type: str, forms: Mapping[str, int], *, slot_class: str
) -> TypeDescription:
    """One type's description from its TRAIN ``{surface form: count}`` table."""

    if slot_class not in CLASS_GLOSSES:
        raise SlurpKnowledgeViewError(
            f"{entity_type!r} has unknown slot class {slot_class!r}; the classes are "
            f"{sorted(CLASS_GLOSSES)}"
        )
    table = {str(form): int(count) for form, count in forms.items() if str(form).strip()}
    if not table:
        raise SlurpKnowledgeViewError(f"{entity_type!r} has no TRAIN surface form")
    mentions = sum(table.values())
    word_counts: list[int] = []
    digit_mentions = 0
    for form, count in table.items():
        words = max(1, len(form.split()))
        word_counts.extend([words] * count)
        if any(character.isdigit() for character in form):
            digit_mentions += count
    word_counts.sort()
    median = word_counts[len(word_counts) // 2]
    top_count = max(table.values())
    return TypeDescription(
        entity_type=str(entity_type),
        slot_class=str(slot_class),
        train_mentions=mentions,
        distinct_forms=len(table),
        min_words=word_counts[0],
        median_words=median,
        max_words=word_counts[-1],
        digit_share=digit_mentions / mentions,
        top_form_share=top_count / mentions,
    )


def render_description_block(
    descriptions: Sequence[TypeDescription], *, header: str = DESCRIPTION_HEADER
) -> str:
    """One intent's description lines as a block of instruction text."""

    if not descriptions:
        return ""
    return "\n".join(
        [str(header), *(f"- {item.entity_type}: {item.body}" for item in descriptions)]
    )


def derange_description_mapping(
    block_types: Mapping[str, Sequence[str]], described: Iterable[str]
) -> dict[str, dict[str, str]]:
    """KV-1's twin mapping: ``{intent: {type: the type whose LINE it takes}}``.

    Exactly MF-10's per-intent card derangement, applied to descriptions and
    for the same reason. An intent's described types are rotated among
    **themselves**, so the block holds the same MULTISET of names and the same
    MULTISET of bodies -- character for character the arm's volume -- with
    every pairing wrong. A single global map cannot do that: a type reached
    from two intents would carry one intent's rotation into the other.

    An intent listing a single described type cannot rotate in place; those
    types are pooled and rotated among themselves, and such an intent's volume
    difference is a covariate the caller reports rather than a match it claims.
    """

    described_set = {str(name) for name in described}
    if len(described_set) < 2:
        raise SlurpKnowledgeViewError("a single described type cannot be deranged")
    per_intent: dict[str, dict[str, str]] = {}
    orphans: set[str] = set()
    for intent in sorted(block_types):
        present = sorted(
            {str(name) for name in block_types[intent] if str(name) in described_set}
        )
        if not present:
            continue
        if len(present) == 1:
            orphans.add(present[0])
            per_intent[str(intent)] = {}
            continue
        per_intent[str(intent)] = {
            name: present[(offset + 1) % len(present)]
            for offset, name in enumerate(present)
        }
    orphans |= described_set - {
        name for mapping in per_intent.values() for name in mapping
    }
    pool = sorted(orphans)
    pool_map: dict[str, str] = {}
    if len(pool) == 1:
        pool_map[pool[0]] = sorted(described_set - {pool[0]})[0]
    else:
        for offset, name in enumerate(pool):
            pool_map[name] = pool[(offset + 1) % len(pool)]
    for intent in sorted(block_types):
        present = sorted(
            {str(name) for name in block_types[intent] if str(name) in described_set}
        )
        if len(present) == 1:
            per_intent[str(intent)] = {present[0]: pool_map[present[0]]}
    for intent, mapping in per_intent.items():
        for name, donor in mapping.items():
            if name == donor:
                raise SlurpKnowledgeViewError(
                    f"{name!r} kept its own description in intent {intent!r}"
                )
    return dict(sorted(per_intent.items()))


# ---------------------------------------------------------------------------
# KV-3 -- deterministic TRAIN exemplars
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Exemplar:
    """One TRAIN utterance offered as a worked example."""

    utterance_id: str
    sentence: str
    slots: tuple[tuple[str, str], ...]

    @property
    def line(self) -> str:
        if not self.slots:
            body = "no slot"
        else:
            body = "; ".join(f"{name}={filler}" for name, filler in self.slots)
        return f'"{self.sentence}" -> {body}'

    def as_json(self) -> dict[str, object]:
        return {
            "utterance_id": self.utterance_id,
            "sentence": self.sentence,
            "slots": [[name, filler] for name, filler in self.slots],
        }


def select_exemplars(
    candidates: Sequence[Exemplar],
    target_types: Sequence[str],
    *,
    k: int = FEWSHOT_K,
    seed: int = FEWSHOT_SEED,
) -> tuple[Exemplar, ...]:
    """``k`` TRAIN exemplars covering as many ``target_types`` as possible.

    The rule, declared before it was run and reproducible from
    ``(seed, sorted utterance ids)`` alone:

    1. sort the candidates by utterance id, then shuffle that list once with
       ``random.Random(seed)`` -- the seed's ONLY entry point, and the reason
       the selection is not simply "the first three utterances of the intent";
    2. greedily take the candidate covering the most target types not yet
       covered, breaking ties by the fewest OFF-target types and then by
       position in the shuffled list;
    3. once every target type is covered (or no candidate adds one), keep
       taking by the most target types covered overall, same tie-break;
    4. stop at ``k``, or earlier when the pool runs out.

    No gold, no DEV text and no model output reaches this function: a
    candidate is a TRAIN utterance with its TRAIN slots.
    """

    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise SlurpKnowledgeViewError(f"k must be a positive int, got {k!r}")
    pool = sorted(candidates, key=lambda item: item.utterance_id)
    random.Random(int(seed)).shuffle(pool)
    targets = {str(name) for name in target_types}
    uncovered = set(targets)
    chosen: list[Exemplar] = []
    taken: set[str] = set()
    while pool and len(chosen) < k:
        best: tuple[int, int, int] | None = None
        best_index = -1
        for index, candidate in enumerate(pool):
            if candidate.utterance_id in taken:
                continue
            types = {name for name, _filler in candidate.slots}
            new = len(types & uncovered)
            on_target = len(types & targets)
            off_target = len(types - targets)
            key = (new, on_target, -off_target)
            if best is None or key > best:
                best = key
                best_index = index
        if best_index < 0:
            break
        candidate = pool[best_index]
        chosen.append(candidate)
        taken.add(candidate.utterance_id)
        uncovered -= {name for name, _filler in candidate.slots}
        pool.pop(best_index)
    return tuple(chosen)


def render_fewshot_block(
    exemplars: Sequence[Exemplar], *, header: str = FEWSHOT_HEADER
) -> str:
    """One intent's exemplars as a block of instruction text."""

    if not exemplars:
        return ""
    return "\n".join(
        [
            str(header),
            *(
                f"{position}. {exemplar.line}"
                for position, exemplar in enumerate(exemplars, start=1)
            ),
        ]
    )


def donor_intent_mapping(intents_by_scenario: Mapping[str, Sequence[str]]) -> dict[str, str]:
    """KV-3's twin mapping: ``{intent: the intent whose exemplars it takes}``.

    A donor is a DIFFERENT intent of the SAME scenario, so the twin's
    exemplars carry scenario-typical language, scenario-typical sentence
    length and scenario-typical slot density -- everything except this
    intent's own slot structure. Within a scenario the sorted intents are
    rotated by one, which is a derangement for every scenario of two or more;
    scenarios carrying a single intent are pooled and rotated among
    themselves, the resolution MF-10 and KU-S3 both use for their singleton
    buckets, and the caller reports those rows' volume delta as a covariate.

    Unlike KV-1's and KV-2's twins this one is **token-matched by measurement,
    not by construction**: a donor intent's exemplar sentences are different
    sentences. The measured character volume of arm and twin is therefore a
    reported covariate, exactly as the owner's 2026-09-06 ruling requires.
    """

    mapping: dict[str, str] = {}
    singletons: list[str] = []
    for scenario in sorted(intents_by_scenario):
        intents = sorted({str(name) for name in intents_by_scenario[scenario]})
        if not intents:
            continue
        if len(intents) == 1:
            singletons.append(intents[0])
            continue
        for offset, intent in enumerate(intents):
            mapping[intent] = intents[(offset + 1) % len(intents)]
    if len(singletons) == 1:
        others = sorted(set(mapping) - set(singletons))
        if not others:
            raise SlurpKnowledgeViewError(
                "a single intent cannot be given a donor of another intent"
            )
        mapping[singletons[0]] = others[0]
    else:
        ordered = sorted(singletons)
        for offset, intent in enumerate(ordered):
            mapping[intent] = ordered[(offset + 1) % len(ordered)]
    for intent, donor in mapping.items():
        if intent == donor:
            raise SlurpKnowledgeViewError(f"intent {intent!r} is its own donor")
    return dict(sorted(mapping.items()))


# ---------------------------------------------------------------------------
# Composition -- one intent's whole rendered block, for any view
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderedView:
    """What one intent's block IS, under one view, with its proxy cost."""

    intent: str | None
    view: str
    twin: bool
    schema_text: str
    view_text: str

    @property
    def text(self) -> str:
        if not self.view_text:
            return self.schema_text
        return f"{self.schema_text}\n\n{self.view_text}"

    @property
    def token_proxy(self) -> int:
        return token_proxy(self.text)

    @property
    def view_token_proxy(self) -> int:
        return token_proxy(self.view_text) if self.view_text else 0

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "view": self.view,
            "twin": self.twin,
            "schema_chars": len(self.schema_text),
            "view_chars": len(self.view_text),
            "chars": len(self.text),
            "token_proxy": self.token_proxy,
            "view_token_proxy": self.view_token_proxy,
        }


def compose_view(
    *,
    intent: str | None,
    view: str,
    twin: bool,
    schema_text: str,
    cards: Sequence[VocabularyCard] = (),
    descriptions: Sequence[TypeDescription] = (),
    exemplars: Sequence[Exemplar] = (),
) -> RenderedView:
    """One intent's whole block: the example-free schema, then the view.

    Fail-closed: a view is refused unless it was given exactly the material
    it renders, so a mis-wired fragment cannot degrade into a silently weaker
    prompt (the failure mode ``rails.phase_material`` was built to remove).
    """

    assert_view(view)
    if not isinstance(schema_text, str) or not schema_text.strip():
        raise SlurpKnowledgeViewError("compose_view needs a rendered schema block")
    if view == KV_VIEW_EXAMPLES_FREE:
        if cards or descriptions or exemplars:
            raise SlurpKnowledgeViewError(
                "the examples-free view carries no card, description or exemplar"
            )
        view_text = ""
    elif view == KV_VIEW_DESCRIPTIONS:
        if not descriptions:
            raise SlurpKnowledgeViewError("the descriptions view needs description lines")
        view_text = render_description_block(descriptions)
    elif view == KV_VIEW_CARDS:
        view_text = render_card_set(list(cards)) if cards else ""
    else:
        if not exemplars:
            raise SlurpKnowledgeViewError("the fewshot view needs exemplars")
        view_text = render_fewshot_block(exemplars)
    return RenderedView(
        intent=intent,
        view=view,
        twin=bool(twin),
        schema_text=schema_text,
        view_text=view_text,
    )


def view_payloads(rendered: RenderedView) -> tuple[str, ...]:
    """Every value string the view block WOULD protect if it were bound as
    traced supply -- the payload set MF-10's containment fold checks.

    For the card view these are the card lines; for the fewshot view the
    exemplar lines; for the description view there are none, because a
    description names no value. Returned so a caller can run
    ``analysis.slurp_slot_vocabulary.containment_collisions`` over the arm's
    own directive and state without re-deriving what a payload is.
    """

    if not rendered.view_text:
        return ()
    lines = rendered.view_text.split("\n")
    return tuple(line for line in lines[1:] if line.strip())


__all__ = [
    "CLASS_GLOSSES",
    "containment_collisions",
    "derange_card_mapping",
    "DESCRIPTION_HEADER",
    "DIGIT_HABIT_NONE",
    "DIGIT_HABIT_USUAL",
    "FEWSHOT_HEADER",
    "FEWSHOT_K",
    "FEWSHOT_SEED",
    "KV0_SCHEMA_HEADER",
    "KV_CELL_IDS",
    "KV_VIEWS",
    "KV_VIEW_CARDS",
    "KV_VIEW_DESCRIPTIONS",
    "KV_VIEW_EXAMPLES_FREE",
    "KV_VIEW_FEWSHOT",
    "Exemplar",
    "RenderedView",
    "SlurpKnowledgeViewError",
    "TypeDescription",
    "assert_view",
    "build_type_description",
    "compose_view",
    "derange_description_mapping",
    "donor_intent_mapping",
    "render_description_block",
    "render_examples_free_block",
    "render_fewshot_block",
    "select_exemplars",
    "view_payloads",
]
