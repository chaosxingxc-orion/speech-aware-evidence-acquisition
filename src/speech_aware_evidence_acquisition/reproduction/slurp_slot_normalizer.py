"""The Whisper-normalizer analogue for SLURP slot values.

Why this module exists. Most published ASR work on Earnings-21/22 passes BOTH
the reference and the hypothesis through Whisper's ``EnglishTextNormalizer``
before computing WER, and this study already reports that convention as
``asr-wer-whisper`` **beside** -- never instead of -- its own raw
``asr-wer``. The SLURP slot layer has the same problem one level down: MF-9's
loss decomposition
(``docs/readiness/2026-09-08-mf9-slurp-slot-gap-audit-v1.md`` section 1.4)
found that **25.96 %** of KC-S1b's loss mass is "right type, right span, wrong
surface string", and that most of it is three normalization artefacts rather
than three hearing failures: letter spacing (``six a m`` for ``six am``),
casing (the official script lower-cases the gold side and deliberately does
**not** lower-case the prediction side), and span padding (``on wednesday``
for ``wednesday``).

``asr-wer-whisper`` repairs that class for a transcript by normalizing both
sides. This module is the same move for a slot filler, and it is deliberately
built to the same three commitments:

1. **Symmetric.** The normalizer is applied to the GOLD filler and to the
   PREDICTED filler alike, before the official distance blocks. It is
   therefore a property of the METRIC, not of the system: no arm can gain
   from it by writing its answers differently from the corpus, only by
   writing the same thing the corpus writes.
2. **Additional, never a replacement.** The scorer id
   :data:`SLURP_SLU_NORMALIZED_SCORER_ID` is registered beside
   ``slurp-slu-official``, exactly as ``asr-wer-whisper`` is registered beside
   ``asr-wer``. The paper-facing SLURP number stays the official one from the
   pinned ``evaluate.py``; the normalized number is reported next to it.
3. **Pinned and deterministic.** One rule set, one id, one bump policy. The
   vendored Whisper English normalizer is the same read-only, hash-pinned copy
   ``reproduction/whisper_normalizer/`` already carries.

The rule set, in application order. Each rung is separately addressable so a
receipt can price it (:data:`SLURP_SLOT_NORMALIZER_RULES`).

``R0`` -- **case and whitespace.** ``casefold()`` with whitespace collapsed;
:func:`reproduction.slurp_value_projection.normalize_filler`, imported rather
than re-implemented so the two rules cannot drift. On the gold side this is
almost a no-op (``data.slurp._entity_filler`` already lower-cases, exactly as
the official loader does); on the prediction side it is the whole of the
casing artefact.

``R1`` -- **the vendored Whisper English normalizer.** Number words,
contractions, honorifics, British/American spelling, currency and percentage
spelling, bracket removal and punctuation stripping, applied through
:func:`reproduction.asr_wer_whisper.normalize_whisper_english`. Guarded: this
normalizer maps a few whole strings to the empty string (``hmm``, ``uh``,
``um``, ``&`` -- its own disfluency and symbol rules, correct for a transcript
and wrong for a one-token slot value), so a rung that would empty a non-empty
value keeps the value it was given. That guard is a rule of THIS module and is
counted in the receipt.

``R2`` -- **the meridiem join.** A standalone ``a m`` / ``p m`` token pair
becomes ``am`` / ``pm``.

  This rung is **this study's own rule and is NOT inherited from Whisper**,
  and the distinction matters enough to state in the module rather than in a
  note. Measured on the vendored normalizer at the pinned tag: ``six am`` ->
  ``6 am`` but ``six a m`` -> ``6 a m``, and ``6 a.m.`` -> ``6 a m``. The
  Whisper rules therefore *split* a period-spelled meridiem and leave a
  space-spelled one alone, so they align neither of the two spellings SLURP
  actually carries. R2 canonicalizes both onto the corpus's own ``am`` / ``pm``
  and runs AFTER R1 precisely so that the period spelling has already become
  the space spelling and one rule catches every form.

``R3`` -- **the leading-preposition strip.** A value whose first token is a
strippable one loses that token, but ONLY when what remains is itself a TRAIN
filler of the SAME slot type (:func:`learn_leading_prepositions`,
:class:`SlotNormalizerInventory`). This is the ``on wednesday`` / ``wednesday``
and ``the olive garden`` / ``olive garden`` class of MF-9 section 1.4, and the
same-type-membership guard is what stops it from eating the first word of a
value that merely starts with a preposition.

  **Semantics proposes and the corpus confirms -- in that order, and the order
  was learned the hard way.** The first version of this rung took the token
  list from TRAIN alone: any leading token the corpus witnessed on at least
  :data:`LEADING_TOKEN_MIN_WITNESSES` distinct same-type ``(w x, x)`` pairs was
  strippable. Run over SLURP that admits ``the`` and ``in`` -- and also
  ``next``, ``last``, ``this``, ``after``, ``before``, ``every``, ``march``,
  ``april`` and ``5th``, because the corpus witnesses those pairs just as
  faithfully. The scorer's own **false-merge audit** then reported 17 collapsed
  gold values, and they were not artefacts: ``next week``, ``last week``,
  ``this week`` and ``one week`` had all become ``week``. A metric that forgives
  the difference between next week and last week is not a cleaner metric, it is
  a broken one.

  No corpus statistic separates ``on`` from ``next``: both are leading tokens
  the corpus attests, and only one of them carries meaning. So the candidate
  set is a DECLARED, closed list of semantically empty English function words
  (:data:`LEADING_TOKEN_CANDIDATES`) and the corpus's job is to CONFIRM that a
  candidate is attested at the witness floor, never to discover the list. The
  tokens TRAIN witnesses but the candidate set excludes are kept on the
  inventory as ``rejected_tokens``, so the finding stays readable rather than
  becoming a silent threshold.

Boundary. The inventory is mined from ``train.jsonl`` and from nothing else --
:func:`load_slot_normalizer_inventory` refuses any other split by name, the
same discipline ``reproduction.slurp_value_projection`` and
``data.slurp.load_slurp_intent_slot_schema`` already enforce. No devel value,
no gold value of the row under scoring and no held-out byte ever enters the
rule. The DEV gold fillers the SCORER normalizes are read where the official
scorer already reads them and are a metric ingredient, never a rule input.

What this module never does: change a slot TYPE, add or delete a mention,
reorder entities, touch the parse, or alter the official ``evaluate.py``
subprocess. It rewrites two strings, symmetrically, and hands them to the same
distance blocks.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence

from .slurp_scoring import SlotEntity
from .slurp_value_projection import normalize_filler

#: Identity of the normalizer rule set implemented by
#: :func:`normalize_slot_value`. Bumped only when a RULE changes (which rungs
#: exist, their order, the meridiem forms, the witness threshold, or the
#: membership guard) -- never when the corpus the TRAIN list is learned from
#: moves, which the umbrella lock pins instead. Same bump policy as
#: ``SLURP_VALUE_PROJECTION_ID`` and ``SLURP_LABEL_PROJECTION_ID``.
SLURP_SLOT_NORMALIZER_ID = "saea-slurp-slot-normalizer-v1"

#: The registered SCORER id this normalizer backs. Reported BESIDE
#: ``slurp-slu-official``, exactly as ``asr-wer-whisper`` is reported beside
#: ``asr-wer``; it never replaces the official number.
SLURP_SLU_NORMALIZED_SCORER_ID = "slurp-slu-f1-normalized-v1"

#: The rungs, in application order. A receipt prices them cumulatively: ``R0``,
#: then ``R0+R1``, then ``R0+R1+R2``, then the whole rule.
SLURP_SLOT_NORMALIZER_RULES: tuple[str, ...] = (
    "R0-case-whitespace",
    "R1-whisper-english",
    "R2-meridiem-join",
    "R3-train-leading-preposition",
)

#: How many distinct same-type TRAIN witness pairs a candidate token needs
#: before it is admitted to the R3 strippable list.
LEADING_TOKEN_MIN_WITNESSES = 3

#: The DECLARED candidate set R3 draws from: English articles and prepositions
#: that carry no meaning of their own in a slot value. The corpus confirms which
#: of these it actually attests; it never proposes a token of its own, because
#: no corpus statistic separates ``on`` from ``next`` (module docstring).
LEADING_TOKEN_CANDIDATES: tuple[str, ...] = (
    "a",
    "an",
    "at",
    "by",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
)

#: The meridiem forms R2 canonicalizes onto. Keyed by the SPLIT spelling the
#: Whisper rung leaves behind, valued by the corpus's own joined spelling.
MERIDIEM_JOINS: Mapping[str, str] = MappingProxyType({"a m": "am", "p m": "pm"})

_MERIDIEM_RE = re.compile(r"(?<![a-z0-9])([ap]) m(?![a-z0-9])")


class SlurpSlotNormalizerError(ValueError):
    """The rule refuses its own parameters -- never a model output."""


def _apply_r0(value: str) -> str:
    """``R0``: case-fold and collapse whitespace."""

    return normalize_filler(value)


def _apply_r1(value: str) -> str:
    """``R1``: the vendored, pinned Whisper English normalizer, guarded.

    The guard is a rule of this module, not of Whisper: the vendored
    normalizer maps ``hmm`` / ``uh`` / ``um`` / ``&`` to the empty string,
    which is right for a transcript and wrong for a one-token slot value that
    the metric would then charge as a deletion on both sides. A rung that
    would empty a non-empty value keeps what it was given.
    """

    if not value:
        return value
    from .asr_wer_whisper import normalize_whisper_english  # noqa: PLC0415 (import cost)

    normalized = " ".join(normalize_whisper_english(value).split())
    return normalized if normalized else value


def _apply_r2(value: str) -> str:
    """``R2``: join a standalone ``a m`` / ``p m`` into ``am`` / ``pm``."""

    if not value:
        return value
    return _MERIDIEM_RE.sub(lambda match: f"{match.group(1)}m", value)


@dataclass(frozen=True)
class SlotNormalizerInventory:
    """The TRAIN material ``R3`` needs, and the identity of the split it came
    from.

    ``fillers`` maps a slot type to the set of its NORMALIZED (``R0`` then
    ``R1`` then ``R2``) TRAIN surface forms -- normalized, because ``R3``'s
    membership guard has to ask its question in the space the earlier rungs
    have already produced, or it would never match. ``leading_tokens`` is the
    learned strippable list; ``witnesses`` carries, per token, how many
    distinct same-type ``(w x, x)`` pairs TRAIN demonstrates, so a receipt can
    print the evidence rather than the conclusion.
    """

    source_split: str
    utterance_count: int
    min_witnesses: int
    fillers: Mapping[str, frozenset[str]]
    leading_tokens: tuple[str, ...]
    rejected_tokens: tuple[str, ...]
    witnesses: Mapping[str, int]
    witness_examples: Mapping[str, tuple[str, ...]]
    source_identity_hash: str

    @property
    def entity_types(self) -> tuple[str, ...]:
        return tuple(sorted(self.fillers))

    @property
    def distinct_fillers(self) -> int:
        return sum(len(values) for values in self.fillers.values())

    def as_json(self) -> dict[str, object]:
        return {
            "normalizer_id": SLURP_SLOT_NORMALIZER_ID,
            "source_split": self.source_split,
            "utterance_count": self.utterance_count,
            "entity_types": len(self.fillers),
            "distinct_normalized_fillers": self.distinct_fillers,
            "source_identity_hash": self.source_identity_hash,
            "min_witnesses": self.min_witnesses,
            "leading_tokens": list(self.leading_tokens),
            "leading_token_witnesses": {
                token: self.witnesses[token] for token in self.leading_tokens
            },
            "leading_token_examples": {
                token: list(self.witness_examples.get(token, ()))
                for token in self.leading_tokens
            },
            "candidate_set": list(LEADING_TOKEN_CANDIDATES),
            "rejected_tokens": list(self.rejected_tokens),
            "rejected_token_witnesses": {
                token: self.witnesses[token] for token in self.rejected_tokens
            },
            "rejected_token_examples": {
                token: list(self.witness_examples.get(token, ()))
                for token in self.rejected_tokens
            },
            "why_rejected": (
                "the corpus witnesses these leading tokens at the floor, but they "
                "carry meaning: stripping them merges `next week` with `last week`. "
                "No corpus statistic separates them from `on` and `the`, so the "
                "candidate set is declared and the corpus only confirms"
            ),
        }


def learn_leading_prepositions(
    fillers_by_type: Mapping[str, Iterable[str]],
    *,
    min_witnesses: int = LEADING_TOKEN_MIN_WITNESSES,
    candidates: Sequence[str] | None = LEADING_TOKEN_CANDIDATES,
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, int], dict[str, tuple[str, ...]]]:
    """The ``R3`` strippable list: declared candidates, corpus-confirmed.

    A token is ADMITTED when it is in ``candidates`` and the corpus carries at
    least ``min_witnesses`` DISTINCT same-type pairs ``(w x, x)`` -- a
    multi-token filler beginning with ``w`` whose remainder is itself an
    attested filler of the same type.

    ``candidates=None`` drops the semantic filter and returns whatever the
    corpus witnesses. That variant is what the module docstring calls the first
    version of this rung: it is kept so the finding it produced stays
    reproducible, and it is NOT the default, because it strips ``next`` from
    ``next week``.

    Returns ``(admitted, rejected, witness counts, up to three witness examples
    each)``. ``rejected`` is the tokens the corpus witnesses at the floor that
    the candidate set excludes -- the evidence for why the filter exists. Both
    lists are sorted by descending witness count then lexicographically.
    """

    if isinstance(min_witnesses, bool) or not isinstance(min_witnesses, int):
        raise SlurpSlotNormalizerError("min_witnesses must be an int")
    if min_witnesses < 1:
        raise SlurpSlotNormalizerError("min_witnesses must be at least 1")
    allowed = None if candidates is None else {str(token) for token in candidates}
    witnesses: dict[str, set[tuple[str, str]]] = {}
    for entity_type, values in fillers_by_type.items():
        present = set(values)
        for value in present:
            parts = value.split(" ")
            if len(parts) < 2:
                continue
            head, remainder = parts[0], " ".join(parts[1:])
            if remainder in present:
                witnesses.setdefault(head, set()).add((str(entity_type), value))
    counts = {token: len(pairs) for token, pairs in witnesses.items()}
    at_floor = sorted(
        (token for token, count in counts.items() if count >= min_witnesses),
        key=lambda token: (-counts[token], token),
    )
    admitted = tuple(
        token for token in at_floor if allowed is None or token in allowed
    )
    rejected = tuple(
        token for token in at_floor if allowed is not None and token not in allowed
    )
    examples = {
        token: tuple(
            f"{entity_type}: {value}"
            for entity_type, value in sorted(witnesses[token])[:3]
        )
        for token in at_floor
    }
    return admitted, rejected, counts, examples


def build_slot_normalizer_inventory(
    material: Iterable[object],
    *,
    source_split: str = "train",
    min_witnesses: int = LEADING_TOKEN_MIN_WITNESSES,
    candidates: Sequence[str] | None = LEADING_TOKEN_CANDIDATES,
) -> SlotNormalizerInventory:
    """Mine the ``R3`` inventory from loaded TRAIN material.

    ``material`` is any iterable of objects carrying an ``entities`` sequence
    of ``(type, filler)`` pairs -- ``data.slurp.SlurpTrainMaterial`` in
    production, a small hand-built stand-in in the tests, exactly as
    :func:`reproduction.slurp_value_projection.build_value_projection_inventory`
    takes it. Taking the loaded material rather than a path keeps the rule
    testable without the governed corpus and keeps the SPLIT decision at the
    one call site that names it.
    """

    grouped: dict[str, set[str]] = {}
    raw_pairs: set[tuple[str, str]] = set()
    utterances = 0
    for utterance in material:
        utterances += 1
        for entity in getattr(utterance, "entities", ()):
            entity_type = str(getattr(entity, "type", "")).strip()
            raw = str(getattr(entity, "filler", ""))
            if not entity_type or not raw.strip():
                continue
            normalized = _apply_r2(_apply_r1(_apply_r0(raw)))
            if not normalized:
                continue
            grouped.setdefault(entity_type, set()).add(normalized)
            raw_pairs.add((entity_type, normalized))
    tokens, rejected, counts, examples = learn_leading_prepositions(
        grouped, min_witnesses=min_witnesses, candidates=candidates
    )
    identity = hashlib.sha256(
        "\n".join(
            f"{entity_type}\t{filler}" for entity_type, filler in sorted(raw_pairs)
        ).encode("utf-8")
    ).hexdigest()
    return SlotNormalizerInventory(
        source_split=source_split,
        utterance_count=utterances,
        min_witnesses=int(min_witnesses),
        fillers=MappingProxyType(
            {
                entity_type: frozenset(values)
                for entity_type, values in sorted(grouped.items())
            }
        ),
        leading_tokens=tokens,
        rejected_tokens=rejected,
        witnesses=MappingProxyType(dict(sorted(counts.items()))),
        witness_examples=MappingProxyType(dict(sorted(examples.items()))),
        source_identity_hash=identity,
    )


def load_slot_normalizer_inventory(
    lock: Mapping[str, object],
    root: Path,
    *,
    source_split: str = "train",
    min_witnesses: int = LEADING_TOKEN_MIN_WITNESSES,
    candidates: Sequence[str] | None = LEADING_TOKEN_CANDIDATES,
) -> SlotNormalizerInventory:
    """The production entry point: mine the inventory from ``train.jsonl``.

    Split discipline mirrors
    :func:`reproduction.slurp_value_projection.load_value_projection_inventory`:
    the loader this calls has no ``split`` parameter at all, so a devel or test
    file cannot be reached through here, and a caller naming another split is
    refused before anything is opened.
    """

    if source_split != "train":
        raise SlurpSlotNormalizerError(
            f"the slot-normalizer inventory is mined from TRAIN and only from TRAIN; "
            f"got source_split={source_split!r}"
        )
    from ..data.slurp import load_slurp_train_material  # noqa: PLC0415 (import cost)

    material = load_slurp_train_material(lock, root)
    return build_slot_normalizer_inventory(
        material,
        source_split=source_split,
        min_witnesses=min_witnesses,
        candidates=candidates,
    )


def _apply_r3(
    value: str, entity_type: str, inventory: SlotNormalizerInventory | None
) -> str:
    """``R3``: strip one learned leading token when the remainder is a TRAIN
    filler of the SAME type."""

    if inventory is None or not value:
        return value
    parts = value.split(" ")
    if len(parts) < 2:
        return value
    head, remainder = parts[0], " ".join(parts[1:])
    if head not in inventory.leading_tokens:
        return value
    if remainder in inventory.fillers.get(str(entity_type), frozenset()):
        return remainder
    return value


def normalize_slot_value(
    value: str,
    entity_type: str,
    inventory: SlotNormalizerInventory | None = None,
    *,
    rules: Sequence[str] = SLURP_SLOT_NORMALIZER_RULES,
) -> str:
    """Normalize ONE slot filler under ``rules``, in
    :data:`SLURP_SLOT_NORMALIZER_RULES` order.

    ``rules`` exists for the per-rule receipt: passing a PREFIX of the rule
    tuple prices that prefix. It is validated as a prefix rather than as a
    set, because the rungs are ordered by construction -- ``R2`` depends on
    ``R1`` having turned ``a.m.`` into ``a m``, and ``R3``'s membership guard
    asks its question in the space ``R0..R2`` produced.

    ``inventory`` is required only by ``R3``; the earlier rungs need nothing
    but the string, which is what makes ``R0..R2`` a corpus-free normalizer
    and ``R3`` the one rung with a TRAIN dependency.
    """

    resolved = tuple(rules)
    if resolved != SLURP_SLOT_NORMALIZER_RULES[: len(resolved)]:
        raise SlurpSlotNormalizerError(
            f"rules must be a PREFIX of {SLURP_SLOT_NORMALIZER_RULES}; got {resolved}"
        )
    if "R3-train-leading-preposition" in resolved and inventory is None:
        raise SlurpSlotNormalizerError(
            "R3-train-leading-preposition needs a TRAIN inventory; got None"
        )
    if not isinstance(value, str):
        raise SlurpSlotNormalizerError(f"value must be str, got {type(value).__name__}")
    out = value
    for rule in resolved:
        if rule == "R0-case-whitespace":
            out = _apply_r0(out)
        elif rule == "R1-whisper-english":
            out = _apply_r1(out)
        elif rule == "R2-meridiem-join":
            out = _apply_r2(out)
        elif rule == "R3-train-leading-preposition":
            out = _apply_r3(out, entity_type, inventory)
        else:  # pragma: no cover -- the prefix check above already refuses it
            raise SlurpSlotNormalizerError(f"unknown rule {rule!r}")
    return out


def normalize_slot_entities(
    entities: Sequence[SlotEntity],
    inventory: SlotNormalizerInventory | None = None,
    *,
    rules: Sequence[str] = SLURP_SLOT_NORMALIZER_RULES,
    cache: dict[tuple[str, str], str] | None = None,
) -> tuple[SlotEntity, ...]:
    """Normalize a whole entity list, in order, keeping every type.

    The returned list has the same length, the same types and the same order
    as the input: this is a value rewrite and nothing else. ``cache`` is an
    optional caller-owned memo keyed by ``(type, raw filler)``; a corpus-wide
    re-score fills it once and reuses it across 1,000 rows.
    """

    out: list[SlotEntity] = []
    for entity in entities:
        key = (str(entity.type), str(entity.filler))
        if cache is not None and key in cache:
            normalized = cache[key]
        else:
            normalized = normalize_slot_value(
                entity.filler, entity.type, inventory, rules=rules
            )
            if cache is not None:
                cache[key] = normalized
        out.append(SlotEntity(type=entity.type, filler=normalized))
    return tuple(out)


__all__ = [
    "LEADING_TOKEN_CANDIDATES",
    "LEADING_TOKEN_MIN_WITNESSES",
    "MERIDIEM_JOINS",
    "SLURP_SLOT_NORMALIZER_ID",
    "SLURP_SLOT_NORMALIZER_RULES",
    "SLURP_SLU_NORMALIZED_SCORER_ID",
    "SlotNormalizerInventory",
    "SlurpSlotNormalizerError",
    "build_slot_normalizer_inventory",
    "learn_leading_prepositions",
    "load_slot_normalizer_inventory",
    "normalize_slot_entities",
    "normalize_slot_value",
]
