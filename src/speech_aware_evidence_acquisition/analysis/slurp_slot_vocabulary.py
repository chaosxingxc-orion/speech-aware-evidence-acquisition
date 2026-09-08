"""TRAIN-only slot-type classes and the vocabulary cards they license (MF-10).

The owner, 2026-09-08: *`date` and `time` slots look like FORMAT knowledge that
should be pre-loaded into the context -- the expected surface conventions --
while `place` needs PROPER-NOUN recognition; would statistically pre-loading
that knowledge into context engineering pay?*

This module is the measurement half of that question. It splits SLURP's slot
types into three classes from TRAIN statistics alone, and for the closed half it
builds the artefact a supply block would actually carry: the **whole** TRAIN
vocabulary of that type, with its mention counts, priced in tokens.

Why the split is worth making at all, in one number MF-9 already published: on
DEV gold, `transport_type`, `weather_descriptor`, `timeofday` and `order_type`
are carried **verbatim by TRAIN 100 % of the time** while `song_name` is
carried **0 %** and `person` **57.1 %**. Supplying a vocabulary can only help
where the corpus has one; on the open half the value was never seen and no
amount of filler supply reaches it. MF-8's standing / utterance-local partition
is a statement about PROVENANCE and does not predict this split -- MF-9 section
4.1 measured the partition inverting -- which is exactly why this module
measures vocabulary size directly instead of inheriting a partition.

The three statistics, all TRAIN-only, all declared before the table was read.

* ``train_mentions`` -- how many TRAIN entity mentions carry the type.
* ``distinct_fillers`` -- how many distinct surface forms those mentions use.
* ``novelty_ratio`` -- ``distinct_fillers / train_mentions``. A closed
  vocabulary re-uses its forms, so the ratio is small; an open one mints a new
  form per mention, so the ratio approaches 1.
* ``dev_verbatim_share_pct`` -- the share of DEV gold mentions of that type
  whose value occurs verbatim in the TRAIN filler set of the same type. **This
  one is READ, never recomputed**: it is lifted out of MF-9's committed
  ``value-headroom.json``, so this module opens no DEV text and the two notes
  cannot drift. :func:`classify_slot_types` takes it as an argument for exactly
  that reason.

The classification rule, frozen before the read
(:data:`CLOSED_MAX_NOVELTY` and friends):

* **CLOSED/FORMAT** -- ``novelty_ratio <= 0.10`` AND
  ``dev_verbatim_share_pct >= 85``. A small vocabulary the corpus re-uses and
  DEV gold stays inside. These are the surface-convention types: what the
  corpus writes, and how it spells it.
* **OPEN/PROPER-NOUN** -- ``novelty_ratio >= 0.35`` OR
  ``dev_verbatim_share_pct <= 60``. Either TRAIN mints a new form per mention,
  or DEV gold routinely lands outside what TRAIN has. Recognition, not
  enumeration.
* **MIXED** -- everything else, reported as its own class rather than forced
  into one of the two.

The two conditions cannot both fire (``<= 0.10`` against ``>= 0.35``, ``>= 85``
against ``<= 60``), so the three classes partition the types. A type with no
DEV gold mention has no verbatim share to test; it is classified on the novelty
ratio alone and its ``class_basis`` says so, so a reader never mistakes a
TRAIN-only verdict for a measured one.

Token cost is a **stated proxy** everywhere in this module: whitespace tokens
times :data:`TOKEN_PROXY_FACTOR`, rounded up. It is not a tokenizer
measurement, no tokenizer is called, and a cell that ever flies a card must
measure its own envelope through the serving ``/apply-template`` + ``/tokenize``
seam exactly as KC-S1b did.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

#: The classification thresholds, frozen before the table was read. A reader
#: who prefers other cut points has every input statistic in the receipt and
#: can re-classify without re-running anything.
CLOSED_MAX_NOVELTY = 0.10
CLOSED_MIN_VERBATIM_PCT = 85.0
OPEN_MIN_NOVELTY = 0.35
OPEN_MAX_VERBATIM_PCT = 60.0

#: The three classes, in report order.
SLOT_CLASS_CLOSED = "CLOSED/FORMAT"
SLOT_CLASS_OPEN = "OPEN/PROPER-NOUN"
SLOT_CLASS_MIXED = "MIXED"
SLOT_CLASSES = (SLOT_CLASS_CLOSED, SLOT_CLASS_MIXED, SLOT_CLASS_OPEN)

#: Whitespace tokens times this, rounded up, is the PROXY token cost this
#: module reports. Never a tokenizer measurement; see the module docstring.
TOKEN_PROXY_FACTOR = 1.3

#: The containment floor ``rails.runner._assert_agent_control_excludes_knowledge_payloads``
#: applies: a protected payload shorter than this is not checked, because a
#: substring rule on one- and two-word English is all false positives.
CONTAINMENT_MIN_LENGTH = 8

#: The header a rendered card set carries. Stated once here so the token cost
#: of a per-intent card set includes the words that make it legible.
CARD_HEADER = (
    "Slot value cards measured on the TRAIN split. A card names one slot type "
    "and every surface form the corpus has used for it, with how often, "
    "written the way the corpus writes it. Use a form only when the speech "
    "supports it, and write it exactly as the card spells it."
)


class SlotVocabularyError(ValueError):
    """The builder refuses its own parameters -- never a model output."""


def token_proxy(text: str) -> int:
    """The stated proxy: ``ceil(whitespace tokens * TOKEN_PROXY_FACTOR)``."""

    if not isinstance(text, str):
        raise SlotVocabularyError(f"text must be str, got {type(text).__name__}")
    words = len(text.split())
    return int(math.ceil(words * TOKEN_PROXY_FACTOR))


@dataclass(frozen=True)
class SlotTypeStats:
    """One slot type's three TRAIN statistics and the class they imply."""

    entity_type: str
    train_mentions: int
    distinct_fillers: int
    novelty_ratio: float
    dev_gold_mentions: int
    dev_verbatim_share_pct: float | None
    slot_class: str
    class_basis: str

    def as_json(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "train_mentions": self.train_mentions,
            "distinct_train_fillers": self.distinct_fillers,
            "novelty_ratio": round(self.novelty_ratio, 4),
            "dev_gold_mentions": self.dev_gold_mentions,
            "dev_verbatim_share_pct": self.dev_verbatim_share_pct,
            "slot_class": self.slot_class,
            "class_basis": self.class_basis,
        }


def classify_slot_types(
    train_counts: Mapping[str, Mapping[str, int]],
    dev_verbatim: Mapping[str, tuple[int, float]],
) -> tuple[SlotTypeStats, ...]:
    """Classify every TRAIN slot type, sorted by descending TRAIN mentions.

    ``train_counts`` maps an entity type to ``{surface form: TRAIN mention
    count}``. ``dev_verbatim`` maps an entity type to
    ``(DEV gold mentions, verbatim share in percent)`` and is READ out of
    MF-9's committed receipt -- a type absent from it simply has no DEV gold
    and is classified on the novelty ratio alone.
    """

    if not train_counts:
        raise SlotVocabularyError("train_counts is empty")
    out: list[SlotTypeStats] = []
    for entity_type, forms in train_counts.items():
        mentions = sum(int(count) for count in forms.values())
        if mentions <= 0:
            raise SlotVocabularyError(f"{entity_type!r} carries no TRAIN mention")
        distinct = len(forms)
        novelty = distinct / mentions
        gold_mentions, verbatim = dev_verbatim.get(str(entity_type), (0, None))
        if verbatim is None:
            basis = "train-only (no DEV gold mention of this type)"
            if novelty <= CLOSED_MAX_NOVELTY:
                slot_class = SLOT_CLASS_CLOSED
            elif novelty >= OPEN_MIN_NOVELTY:
                slot_class = SLOT_CLASS_OPEN
            else:
                slot_class = SLOT_CLASS_MIXED
        else:
            basis = "novelty ratio and MF-9 DEV verbatim share"
            closed = (
                novelty <= CLOSED_MAX_NOVELTY and verbatim >= CLOSED_MIN_VERBATIM_PCT
            )
            open_ = novelty >= OPEN_MIN_NOVELTY or verbatim <= OPEN_MAX_VERBATIM_PCT
            if closed and open_:  # pragma: no cover -- the thresholds exclude it
                raise SlotVocabularyError(
                    f"{entity_type!r} satisfies both class rules; the thresholds moved"
                )
            slot_class = (
                SLOT_CLASS_CLOSED if closed else SLOT_CLASS_OPEN if open_ else SLOT_CLASS_MIXED
            )
        out.append(
            SlotTypeStats(
                entity_type=str(entity_type),
                train_mentions=mentions,
                distinct_fillers=distinct,
                novelty_ratio=novelty,
                dev_gold_mentions=int(gold_mentions),
                dev_verbatim_share_pct=verbatim,
                slot_class=slot_class,
                class_basis=basis,
            )
        )
    return tuple(sorted(out, key=lambda stat: (-stat.train_mentions, stat.entity_type)))


@dataclass(frozen=True)
class VocabularyCard:
    """One slot type's FULL TRAIN vocabulary, priced.

    ``forms`` is every distinct surface form with its TRAIN mention count,
    ordered by descending count then lexicographically -- the same order
    ``reproduction.slurp_value_projection`` breaks its ties in, so a card and a
    projection inventory read the same way.
    """

    entity_type: str
    forms: tuple[tuple[str, int], ...]
    train_mentions: int

    @property
    def text(self) -> str:
        """The rendered card line: the type, then every form with its count."""

        body = "; ".join(f"{form} ({count})" for form, count in self.forms)
        return f"- {self.entity_type}: {body}"

    @property
    def token_proxy(self) -> int:
        return token_proxy(self.text)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def as_json(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "distinct_forms": len(self.forms),
            "train_mentions": self.train_mentions,
            "token_proxy": self.token_proxy,
            "chars": self.char_count,
            "forms": [[form, count] for form, count in self.forms],
        }


def build_vocabulary_card(
    entity_type: str, forms: Mapping[str, int]
) -> VocabularyCard:
    """The full card for one type. Every form, never a sample."""

    if not forms:
        raise SlotVocabularyError(f"{entity_type!r} has no TRAIN surface form")
    ordered = tuple(
        sorted(
            ((str(form), int(count)) for form, count in forms.items()),
            key=lambda item: (-item[1], item[0]),
        )
    )
    return VocabularyCard(
        entity_type=str(entity_type),
        forms=ordered,
        train_mentions=sum(count for _form, count in ordered),
    )


def render_card_set(cards: Sequence[VocabularyCard], *, header: str = CARD_HEADER) -> str:
    """A per-intent card set as one block of typed content."""

    if not cards:
        return ""
    return "\n".join([header, *(card.text for card in cards)])


@dataclass(frozen=True)
class IntentCardCost:
    """What one intent's card set costs, and which types it carries."""

    intent: str
    entity_types: tuple[str, ...]
    closed_types: tuple[str, ...]
    token_proxy: int
    char_count: int

    def as_json(self) -> dict[str, object]:
        return {
            "intent": self.intent,
            "block_types": list(self.entity_types),
            "carded_closed_types": list(self.closed_types),
            "card_token_proxy": self.token_proxy,
            "card_chars": self.char_count,
        }


def price_intent_cards(
    block_types: Mapping[str, Sequence[str]],
    cards: Mapping[str, VocabularyCard],
    *,
    header: str = CARD_HEADER,
) -> tuple[IntentCardCost, ...]:
    """Price one card set per intent: the cards for the CLOSED types that
    intent's own schema block lists, and nothing else.

    ``block_types`` maps an intent to the entity types its KC-S1b schema block
    lists; ``cards`` maps a closed entity type to its card. A type the block
    lists but no card covers is simply skipped -- that is the open half, which
    KU-S3's retrieval keeps.
    """

    out: list[IntentCardCost] = []
    for intent, types in sorted(block_types.items()):
        selected = [cards[name] for name in types if name in cards]
        text = render_card_set(selected, header=header)
        out.append(
            IntentCardCost(
                intent=str(intent),
                entity_types=tuple(str(name) for name in types),
                closed_types=tuple(card.entity_type for card in selected),
                token_proxy=token_proxy(text) if text else 0,
                char_count=len(text),
            )
        )
    return tuple(out)


def derange_card_mapping(
    block_types: Mapping[str, Sequence[str]], carded: Iterable[str]
) -> dict[str, str]:
    """The TWIN's type -> vocabulary mapping: a within-intent rotation.

    The twin is the control the owner's 2026-09-06 ruling asks for -- a card of
    the same size whose vocabularies are attached to the wrong types -- and it
    is **token-matched by construction rather than by a cap**: rotating an
    intent's carded types among themselves leaves the intent's card set holding
    exactly the same multiset of vocabularies, so its rendered volume is
    identical to the arm's, character for character, whatever the vocabularies
    happen to be.

    Types whose intent lists only ONE carded type cannot rotate inside it; they
    are pooled across intents and rotated among themselves, which is the same
    resolution KU-S3's own derangement uses for its singleton scenario buckets.
    A type reached from several intents keeps the FIRST assignment in sorted
    intent order, so the mapping is a pure function of the inputs.

    Returns ``{type: the type whose vocabulary it receives}``. Raises if any
    type would keep its own vocabulary.
    """

    carded_set = {str(name) for name in carded}
    mapping: dict[str, str] = {}
    singletons: list[str] = []
    for intent in sorted(block_types):
        present = [name for name in block_types[intent] if str(name) in carded_set]
        present = sorted({str(name) for name in present})
        if len(present) < 2:
            singletons.extend(name for name in present if name not in mapping)
            continue
        for offset, name in enumerate(present):
            if name in mapping:
                continue
            mapping[name] = present[(offset + 1) % len(present)]
    pool = sorted({name for name in singletons if name not in mapping})
    if len(pool) == 1:
        # One orphan cannot be deranged inside a pool of one; give it the
        # vocabulary of the lexicographically first OTHER carded type, and take
        # that type's own partner as the orphan's donor is never itself.
        orphan = pool[0]
        others = sorted(carded_set - {orphan})
        if not others:
            raise SlotVocabularyError("a single carded type cannot be deranged")
        mapping[orphan] = others[0]
    else:
        for offset, name in enumerate(pool):
            mapping[name] = pool[(offset + 1) % len(pool)]
    for name in sorted(carded_set):
        if name not in mapping:
            raise SlotVocabularyError(f"{name!r} was never assigned a twin vocabulary")
        if mapping[name] == name:
            raise SlotVocabularyError(f"{name!r} kept its own vocabulary in the twin")
    return mapping


def containment_collisions(
    payloads: Iterable[str],
    instruction: str,
    *,
    min_length: int = CONTAINMENT_MIN_LENGTH,
) -> tuple[str, ...]:
    """Every payload of at least ``min_length`` characters that occurs verbatim
    inside ``instruction``.

    The same raw-substring rule at the same floor
    ``rails.runner._assert_agent_control_excludes_knowledge_payloads`` applies
    to a bound snapshot, reproduced here so a card set can be checked BEFORE
    anything is built: a card value must travel as typed content and must never
    also be sitting in the instruction the model reads as its own directive.
    """

    if not isinstance(instruction, str):
        raise SlotVocabularyError("instruction must be str")
    hits = {
        text
        for text in (str(payload) for payload in payloads)
        if len(text) >= min_length and text in instruction
    }
    return tuple(sorted(hits))


__all__ = [
    "CARD_HEADER",
    "CLOSED_MAX_NOVELTY",
    "CLOSED_MIN_VERBATIM_PCT",
    "CONTAINMENT_MIN_LENGTH",
    "OPEN_MAX_VERBATIM_PCT",
    "OPEN_MIN_NOVELTY",
    "SLOT_CLASSES",
    "SLOT_CLASS_CLOSED",
    "SLOT_CLASS_MIXED",
    "SLOT_CLASS_OPEN",
    "TOKEN_PROXY_FACTOR",
    "IntentCardCost",
    "SlotTypeStats",
    "SlotVocabularyError",
    "VocabularyCard",
    "build_vocabulary_card",
    "classify_slot_types",
    "containment_collisions",
    "derange_card_mapping",
    "price_intent_cards",
    "render_card_set",
    "token_proxy",
]
