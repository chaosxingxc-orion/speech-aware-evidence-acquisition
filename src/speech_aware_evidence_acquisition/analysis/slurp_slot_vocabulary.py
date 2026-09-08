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

TWO rules are implemented, and BOTH are reported, because the first one is
wrong in a way worth publishing rather than quietly fixing.

**:data:`SLOT_CLASS_RULE_V1`** (``mf10-novelty-v1``) is the rule this audit
declared before it read the table: CLOSED when ``novelty_ratio <= 0.10`` AND
``dev_verbatim_share_pct >= 85``; OPEN when ``novelty_ratio >= 0.35`` OR
``dev_verbatim_share_pct <= 60``; MIXED otherwise.

It selects four types out of fifty-five, and the reason is a measurable defect
rather than a property of the corpus: **the novelty ratio is a rate estimate,
and a rare type cannot have a low one.** ``alarm_type`` has FOUR distinct
surface forms -- as closed a vocabulary as SLURP contains -- but only nine
TRAIN mentions, so its ratio is 0.44 and v1 calls it open. ``date``, the type
the owner's question names, has 289 forms over 1,823 mentions for a ratio of
0.16 and lands in MIXED. The ratio measures how fast the corpus mints forms,
which is only the same question as "is this vocabulary closed" when the corpus
has minted enough of them to tell.

**:data:`SLOT_CLASS_RULE_V2`** (``mf10-cardability-v2``) is the operative rule,
and it puts the three statistics in the roles the measurement supports:

* **coverage decides.** CLOSED needs
  ``dev_verbatim_share_pct >= CLOSED_MIN_VERBATIM_PCT``; OPEN is
  ``dev_verbatim_share_pct <= OPEN_MAX_VERBATIM_PCT``. A card pays exactly when
  the value DEV needs is inside it, and cannot pay when the value was never
  seen. This is the one condition that speaks to the mechanism.
* **re-use disqualifies, where it is estimable.** A type whose corpus keeps
  minting new forms is not a vocabulary even when DEV happened to be covered,
  so ``novelty_ratio >= OPEN_MIN_NOVELTY`` forces OPEN -- but ONLY when the
  type has at least :data:`NOVELTY_MIN_MENTIONS` TRAIN mentions, below which
  the ratio is an artefact of the sample rather than a property of the type.
* **size is checked, not capped.** No per-type form limit is imposed. The
  enumerability question is asked where it is actually binding -- of the
  per-intent card SET, against the arm's own measured prompt headroom -- and
  the caller checks it with :func:`price_intent_cards`, so the threshold is a
  measured budget rather than a taste.

Under either rule the CLOSED and OPEN conditions are disjoint, so the three
classes partition the types. A type with no DEV gold mention has no verbatim
share to test: v2 puts it in MIXED (there is nothing for a card to cover) and
its ``class_basis`` says so, so a reader never mistakes a TRAIN-only verdict
for a measured one.

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

#: How many TRAIN mentions a type needs before its novelty ratio is treated as
#: an estimate of anything. Below this the ratio is bounded from below by
#: ``1 / mentions`` and says more about the sample than about the type -- the
#: defect that made ``SLOT_CLASS_RULE_V1`` call a four-form vocabulary open.
NOVELTY_MIN_MENTIONS = 50

#: The rule this audit DECLARED before reading the table.
SLOT_CLASS_RULE_V1 = "mf10-novelty-v1"
#: The rule the measurement licensed, and the one the views are built on.
SLOT_CLASS_RULE_V2 = "mf10-cardability-v2"
SLOT_CLASS_RULES = (SLOT_CLASS_RULE_V1, SLOT_CLASS_RULE_V2)

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
    rule: str = SLOT_CLASS_RULE_V2

    def as_json(self) -> dict[str, object]:
        return {
            "entity_type": self.entity_type,
            "train_mentions": self.train_mentions,
            "distinct_train_fillers": self.distinct_fillers,
            "novelty_ratio": round(self.novelty_ratio, 4),
            "novelty_ratio_is_estimable": self.train_mentions >= NOVELTY_MIN_MENTIONS,
            "dev_gold_mentions": self.dev_gold_mentions,
            "dev_verbatim_share_pct": self.dev_verbatim_share_pct,
            "rule": self.rule,
            "slot_class": self.slot_class,
            "class_basis": self.class_basis,
        }


def _classify_v1(
    novelty: float, verbatim: float | None
) -> tuple[str, str]:
    """The DECLARED rule, kept so its verdict stays readable beside v2's."""

    if verbatim is None:
        basis = "train-only (no DEV gold mention of this type)"
        if novelty <= CLOSED_MAX_NOVELTY:
            return SLOT_CLASS_CLOSED, basis
        if novelty >= OPEN_MIN_NOVELTY:
            return SLOT_CLASS_OPEN, basis
        return SLOT_CLASS_MIXED, basis
    basis = "novelty ratio and MF-9 DEV verbatim share"
    closed = novelty <= CLOSED_MAX_NOVELTY and verbatim >= CLOSED_MIN_VERBATIM_PCT
    open_ = novelty >= OPEN_MIN_NOVELTY or verbatim <= OPEN_MAX_VERBATIM_PCT
    if closed and open_:  # pragma: no cover -- the thresholds exclude it
        raise SlotVocabularyError("a type satisfies both v1 class rules")
    return (
        SLOT_CLASS_CLOSED if closed else SLOT_CLASS_OPEN if open_ else SLOT_CLASS_MIXED
    ), basis


def _classify_v2(
    mentions: int, novelty: float, verbatim: float | None
) -> tuple[str, str]:
    """The OPERATIVE rule: coverage decides, re-use disqualifies where it is
    estimable, and size is checked as a budget rather than capped here."""

    estimable = mentions >= NOVELTY_MIN_MENTIONS
    disqualified = estimable and novelty >= OPEN_MIN_NOVELTY
    if verbatim is None:
        return (
            SLOT_CLASS_MIXED,
            "train-only (no DEV gold mention of this type, so nothing for a card to cover)",
        )
    if verbatim <= OPEN_MAX_VERBATIM_PCT:
        return SLOT_CLASS_OPEN, "DEV gold routinely lands outside the TRAIN vocabulary"
    if disqualified:
        return (
            SLOT_CLASS_OPEN,
            f"the corpus mints a new form per {1 / novelty:.1f} mentions over "
            f"{mentions} mentions, so this is not a vocabulary",
        )
    if verbatim >= CLOSED_MIN_VERBATIM_PCT:
        return (
            SLOT_CLASS_CLOSED,
            "TRAIN carries the DEV gold value at or above the coverage floor"
            + ("" if estimable else "; the novelty ratio is not estimable at this size"),
        )
    return SLOT_CLASS_MIXED, "coverage sits between the two floors"


def classify_slot_types(
    train_counts: Mapping[str, Mapping[str, int]],
    dev_verbatim: Mapping[str, tuple[int, float]],
    *,
    rule: str = SLOT_CLASS_RULE_V2,
) -> tuple[SlotTypeStats, ...]:
    """Classify every TRAIN slot type, sorted by descending TRAIN mentions.

    ``train_counts`` maps an entity type to ``{surface form: TRAIN mention
    count}``. ``dev_verbatim`` maps an entity type to
    ``(DEV gold mentions, verbatim share in percent)`` and is READ out of
    MF-9's committed receipt -- a type absent from it simply has no DEV gold.

    ``rule`` selects :data:`SLOT_CLASS_RULE_V1` (the rule this audit declared
    before reading the table) or :data:`SLOT_CLASS_RULE_V2` (the one the
    measurement licensed, and the default). Both are kept and both are
    reported; see the module docstring for why the first one is wrong.
    """

    if rule not in SLOT_CLASS_RULES:
        raise SlotVocabularyError(
            f"unknown rule {rule!r}; registered rules are {SLOT_CLASS_RULES}"
        )
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
        if rule == SLOT_CLASS_RULE_V1:
            slot_class, basis = _classify_v1(novelty, verbatim)
        else:
            slot_class, basis = _classify_v2(mentions, novelty, verbatim)
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
                rule=rule,
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
    remap: Mapping[str, Mapping[str, str]] | None = None,
) -> tuple[IntentCardCost, ...]:
    """Price one card set per intent: the cards for the CLOSED types that
    intent's own schema block lists, and nothing else.

    ``block_types`` maps an intent to the entity types its KC-S1b schema block
    lists; ``cards`` maps a closed entity type to its card. A type the block
    lists but no card covers is simply skipped -- that is the open half, which
    KU-S3's retrieval keeps.

    ``remap`` prices the TWIN through the same function rather than through a
    second one: it is :func:`derange_card_mapping`'s per-intent mapping, and a
    type listed by the intent takes the card of the type the mapping names.
    Nothing else changes, which is what makes the twin's volume comparable to
    the arm's by construction on every intent that could rotate in place.
    """

    out: list[IntentCardCost] = []
    for intent, types in sorted(block_types.items()):
        substitution = (remap or {}).get(str(intent), {})
        selected = [
            cards[substitution.get(name, name)]
            for name in types
            if substitution.get(name, name) in cards and name in cards
        ]
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
) -> dict[str, dict[str, str]]:
    """The TWIN's per-intent type -> vocabulary mapping.

    The twin is the control the owner's 2026-09-06 ruling asks for -- a card set
    of the same size whose vocabularies are attached to the wrong types -- and
    the mapping is **per intent**, which is the whole reason it is token-matched
    BY CONSTRUCTION rather than by a cap: rotating an intent's carded types
    among themselves leaves that intent's card set holding exactly the same
    MULTISET of vocabularies, so its rendered volume is identical to the arm's,
    character for character, whatever the vocabularies happen to be. A single
    GLOBAL mapping cannot do that -- a type reached from two intents would carry
    one intent's rotation into the other -- which is why this returns a mapping
    per intent instead of one map.

    An intent that lists exactly ONE carded type cannot rotate inside itself:
    any twin of a single card is a different vocabulary of a different size.
    Those types, and any carded type no block lists at all (its share stays
    under every intent's own floor), are pooled and rotated among themselves --
    the resolution KU-S3's own derangement uses for its singleton scenario
    buckets -- and such an intent's volume difference is a covariate the caller
    reports rather than a match it can claim.

    Returns ``{intent: {type: the type whose vocabulary it receives}}`` for
    every intent listing at least one carded type. Raises if any type would
    keep its own vocabulary.
    """

    carded_set = {str(name) for name in carded}
    if len(carded_set) < 2:
        raise SlotVocabularyError("a single carded type cannot be deranged")
    per_intent: dict[str, dict[str, str]] = {}
    orphans: set[str] = set()
    for intent in sorted(block_types):
        present = sorted(
            {str(name) for name in block_types[intent] if str(name) in carded_set}
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
    orphans |= carded_set - {
        name for mapping in per_intent.values() for name in mapping
    }
    pool = sorted(orphans)
    pool_map: dict[str, str] = {}
    if len(pool) == 1:
        others = sorted(carded_set - {pool[0]})
        pool_map[pool[0]] = others[0]
    else:
        for offset, name in enumerate(pool):
            pool_map[name] = pool[(offset + 1) % len(pool)]
    for intent in sorted(block_types):
        present = sorted(
            {str(name) for name in block_types[intent] if str(name) in carded_set}
        )
        if len(present) == 1:
            per_intent[str(intent)] = {present[0]: pool_map[present[0]]}
    for intent, mapping in per_intent.items():
        for name, donor in mapping.items():
            if name == donor:
                raise SlotVocabularyError(
                    f"{name!r} kept its own vocabulary in intent {intent!r}"
                )
    assigned = {name for mapping in per_intent.values() for name in mapping} | set(
        pool_map
    )
    missing = sorted(carded_set - assigned)
    if missing:
        raise SlotVocabularyError(
            f"{missing[0]!r} was never assigned a twin vocabulary"
        )
    return dict(sorted(per_intent.items()))


def twin_pool_types(
    block_types: Mapping[str, Sequence[str]], carded: Iterable[str]
) -> tuple[str, ...]:
    """The carded types the twin has to pool rather than rotate in place.

    These are the ones whose intents list a single carded type, or that no block
    lists at all; an intent built only from them cannot be volume-matched, and
    the caller reports that as a covariate.
    """

    carded_set = {str(name) for name in carded}
    pooled: set[str] = set(carded_set)
    for intent in block_types:
        present = {str(name) for name in block_types[intent] if str(name) in carded_set}
        if len(present) >= 2:
            pooled -= present
    return tuple(sorted(pooled))


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
    "NOVELTY_MIN_MENTIONS",
    "OPEN_MAX_VERBATIM_PCT",
    "OPEN_MIN_NOVELTY",
    "SLOT_CLASSES",
    "SLOT_CLASS_RULES",
    "SLOT_CLASS_RULE_V1",
    "SLOT_CLASS_RULE_V2",
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
    "twin_pool_types",
    "render_card_set",
    "token_proxy",
]
