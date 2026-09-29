"""E4 v1: the core-native targeted re-listen (owner decision 185).

Design: ``docs/superpowers/specs/2026-09-28-e4-core-native-targeted-relisten-
design.md`` (sections 1, 2, 4, 6, and the section 8 coordinator rulings that
supersede section 2's dependency paragraph and section 7's open questions).
Node-gain motivation: ``docs/results/2026-09-28-slurp-node-information-gain-
ledger.md`` sections 4-5.

THE MECHANISM (section 1, extended by the section 8 rulings). A post-accept
stage, ``relisten``, runs after ACCEPT and after the deliver normaliser, for
up to :data:`DEFAULT_MAX_SLOTS_PER_ROW` delivered entities per row, in
delivery order, with no type filter and never re-opening the decided intent:

* **Contact 1 (blind).** The packet, the decided intent and the slot type,
  never the delivered value ``c``. Format ``slurp-relisten-value-v1``
  (:data:`BLIND_RESPONSE_FORMAT_ID`): ``{"heard": bool, "value": <= 8
  words}``. Parsed by :func:`parse_blind_response`.
* **Contact 2 (forced choice), conditionally.** Fired whenever the blind
  contact did NOT return a value canonically equal to ``c`` while claiming to
  have heard one -- :func:`should_fire_confirm` is the one place this rule
  lives. On a genuine disagreement it presents ``c`` and the blind's value
  ``v`` in an order fixed by ``sha256(sample_id, slot_type)``
  (:func:`confirm_order`); on a blind ``heard = false`` (or an unparsed
  blind) it presents ``c`` against the UNHEARD sentinel in the same fixed
  order -- ruling 2b: "the confirm contact is therefore also fired on a
  blind heard = false, so that both contacts vote". Format
  ``slurp-relisten-confirm-v1`` (:data:`CONFIRM_RESPONSE_FORMAT_ID``):
  ``{"choice": "A"|"B"|"neither"}``. It sees the decided intent only, never
  Perception's candidates (ruling 3).
* **Acceptance.** Replace ``c`` with ``v`` iff the blind returned a
  canonically different value AND the confirm chose it. An unheard or
  invalid-length blind never manufactures a value. v1 never deletes or adds
  an entity in the DELIVERED column: deletion is a SHADOW-column-only effect
  (ruling 2b).

SHADOW DELIVERY (ruling 2, ruling 5). The delivered answer is never changed
in flight. Every decision above is sealed per entity, with the confirm's own
firing/vote and hashes only -- never the value's bytes (the "no transcript
state" rule) -- into the row's ``saea-relisten-v1`` receipt
(:func:`seal_relisten_receipt`). Two shadow columns are rebuilt OFFLINE from
the sealed receipt plus the sealed trace (:func:`bind_shadow_entities`):

* (a) :data:`COLUMN_REPLACE_ONLY` -- the section 1 acceptance rule, unchanged;
* (b) :data:`COLUMN_REPLACE_DROP_UNHEARD` -- (a) plus dropping an entity when
  BOTH contacts vote unheard (ruling 2b, aimed at the 253 SPURIOUS
  predictions of the node-gain ledger's section 2.3).

Both columns declare ``expected_effect_pp`` 0.0 and claim ceiling
``"nominated"`` (ruling 7): no measured analogue exists yet, so the bar is
the design's own twin/shadow null, registered in
``scripts/checks/stage3_effect_floor_check.py`` as the
``same-flight-shadow-relisten`` design -- SLU only, ``1.49 * sqrt(1080 /
rows)`` (owner decision 190, 2026-09-29: the larger of the two measured
same-flight CONTRAST half-widths, cell W-SV-1 and cell W4-SV; intent carries
no floor at all on this design, identical by construction) -- until an
instrument cell has flown and measured its own paired-difference null.

THE NODE. The post-accept stage is wired into ``rails.runner``'s own
per-row dispatch (not into ``reproduction.ojw.native_episode``'s
ACCEPT/REVISE/ACQUIRE workflow graph, which has already finished by the time
this stage runs): a dedicated ``MeteredNativeSpeechRequest`` instance, built
unconditionally beside its E8b node-context-cleaning sibling and spent only
when ``native_episode.relisten`` is armed, sends each blind/forced-choice
contact through the SAME ``FrozenCoreClient`` every role contact uses, over
the packet-only messages ``rails.runner.node_context_cleaning_messages``
already composes (audio, no evidence -- exactly section 1's "the packet ...
but not c"). The E18 ``speech-reobserve`` acquisition node
(``rails/acquisition.py``) and the E8b cleaning contact
(``rails.node_context_policy`` / ``rails.runner.run_cleaning_contact``) are
the closest existing analogues: like acquisition's kind (b), it is a
Perception-kind role making a real metered contact outside the ACCEPT/REVISE
FSM; like a cleaning contact, its response format and instruction are named
explicitly per call rather than resolved from a fixed ``PhaseProgram`` phase
entry, because the blind and forced-choice contacts need two different
response formats under the one post-accept stage. Every function in THIS
module stays pure and model-free, so it is fully testable without any model,
server or GPU contact -- the config surface (``rails.native_episode_config``),
the registered program id (``rails.controllers``), the two gates, the
``rails.runner`` wiring, the ``I7l`` bundle custody check
(``core.bundle.outputs``), and the offline shadow-column render/score
(``scripts/analysis/stage3_rollout_score.py``) all depend only on this
module's pure functions and the receipt shape they define.

Research-boundary discipline (repository ``CLAUDE.md``): no gold, no
reference transcript and no future turn ever reaches this module -- it reads
and writes only the row's own sealed relisten contacts. The value's bytes
never enter any role's context and are never persisted as plain text by this
module; only hashes are sealed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Mapping, Sequence

from ..core.base import RELISTEN_POLICIES, CoreError


class RelistenError(ValueError):
    """The relisten stage refuses: malformed config or an invalid contract."""


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------

#: ``core.base.RELISTEN_POLICIES`` id for this mechanism (section 6's
#: implementation plan table). Registered below, at import time, exactly as
#: ``rails.acquisition`` registers its three kinds into
#: ``core.base.ACQUISITION_POLICIES``.
RELISTEN_POLICY_ID = "saea-obs-targeted-relisten-v1"

#: The per-row receipt schema section 1's receipt paragraph names.
RELISTEN_RECEIPT_SCHEMA = "saea-relisten-v1"

#: The two pinned response formats (section 1, section 6's config table).
BLIND_RESPONSE_FORMAT_ID = "slurp-relisten-value-v1"
CONFIRM_RESPONSE_FORMAT_ID = "slurp-relisten-confirm-v1"

#: The two pinned prompt templates (section 6),
#: ``configs/probes/slurp_relisten_{blind,confirm}_v1.txt``.
BLIND_TEMPLATE_ID = "slurp_relisten_blind_v1"
CONFIRM_TEMPLATE_ID = "slurp_relisten_confirm_v1"

#: The forced-choice CANDIDATE option's text on a blind ``heard = false`` (or
#: unparsed) fire (ruling 2b): neither contact names a real value there, so
#: this fixed, bracketed sentinel stands in for it. It is never a legal SLURP
#: filler and no template asks the model to reproduce it, so it can never be
#: mistaken for a real heard value if it ever appears in a hash comparison or
#: a rendered confirm option.
UNHEARD_SENTINEL = "[no value heard]"


def relisten_blind_response_format(
    _lock: object = None, _root: object = None, **params: object
) -> dict[str, object]:
    """``core.base.RESPONSE_FORMATS`` entry :data:`BLIND_RESPONSE_FORMAT_ID`
    (``slurp-relisten-value-v1``, section 1): ``{"heard": bool, "value":
    string}``. :func:`parse_blind_response` is the schema's own reader, so a
    response generated under this format satisfies the shape half of that
    parser by construction; the parser alone still enforces the word-count
    bound (a JSON Schema cannot count words) and every malformed-input
    fallback.

    Registered from ``rails.controllers.register_response_formats_v1`` --
    the ONE canonical ``RESPONSE_FORMATS`` registration site
    (``scripts/checks/engineering_base_check.py``'s own rule) -- not from
    this module, exactly as every other bespoke response format (cited-
    answer, NCP cleaning, Stage-3 advantage/GEPA, SLURP verifier choice) is:
    the function lives beside its schema and parser, the ``.register(...)``
    call lives at the one canonical site.
    """

    if params:
        raise RelistenError("the relisten blind response format takes no parameters")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "slurp_relisten_value_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["heard", "value"],
                "properties": {
                    "heard": {"type": "boolean"},
                    "value": {"type": "string"},
                },
            },
        },
    }


def relisten_confirm_response_format(
    _lock: object = None, _root: object = None, **params: object
) -> dict[str, object]:
    """``core.base.RESPONSE_FORMATS`` entry :data:`CONFIRM_RESPONSE_FORMAT_ID`
    (``slurp-relisten-confirm-v1``, section 1): ``{"choice": "A"|"B"|
    "neither"}``. :func:`parse_confirm_letter` is the schema's own reader.
    Registered from ``rails.controllers.register_response_formats_v1``; see
    :func:`relisten_blind_response_format`.
    """

    if params:
        raise RelistenError("the relisten confirm response format takes no parameters")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "slurp_relisten_confirm_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["choice"],
                "properties": {
                    "choice": {"type": "string", "enum": ["A", "B", "neither"]},
                },
            },
        },
    }


#: Section 1: "the stage re-listens to at most 3 entities per row" -- the
#: hard v1 ceiling; ``native_episode.relisten.max_slots_per_row`` may declare
#: anything from 1 up to this bound.
DEFAULT_MAX_SLOTS_PER_ROW = 3

#: Section 1: "a value span ... of at most 8 words".
MAX_VALUE_WORDS = 8

#: Both contacts count against the budget (section 1's implementation
#: instructions): the ceiling's own additive unit is 2 contacts per
#: triggered slot (blind + forced choice), whether or not the confirm
#: actually fires for a given row -- the CEILING is a bound, not the
#: expected spend (section 3's cost table is the expected spend).
CONTACTS_PER_ENTITY = 2

#: v1's only legal delivery mode (ruling 5: "Shadow delivery, on TRAIN Fold A
#: first").
DELIVERY_MODE = "shadow"

#: The two shadow columns (ruling 2), written by
#: ``scripts/analysis/stage3_rollout_score.py`` as
#: ``arm-<column>-<scorer>-scores.json`` -- the same naming
#: ``score_supply_variant_copies`` uses for a Solver arm, so
#: ``stage3_paired_read.py --left-column/--right-column`` reads either
#: shadow column against the delivered column with no new machinery.
COLUMN_REPLACE_ONLY = "relisten-replace-only"
COLUMN_REPLACE_DROP_UNHEARD = "relisten-replace-drop-unheard"
SHADOW_COLUMNS: tuple[str, str] = (COLUMN_REPLACE_ONLY, COLUMN_REPLACE_DROP_UNHEARD)

#: Ruling 7 / the same-flight-supply-variant precedent: a Solver-local (here,
#: post-accept-local) shadow effect never supports a system-level claim.
CLAIM_CEILING = "nominated"

#: A blind entity's disposition, the four mutually exclusive terminal states
#: :func:`parse_blind_response` may report.
BLIND_VALUE = "value"
BLIND_UNHEARD = "unheard"
BLIND_INVALID_LENGTH = "invalid-length"
BLIND_UNPARSED = "unparsed"
BLIND_DISPOSITIONS: tuple[str, ...] = (
    BLIND_VALUE, BLIND_UNHEARD, BLIND_INVALID_LENGTH, BLIND_UNPARSED,
)

#: A fired confirm's vote, resolved from its raw letter through the fixed
#: order (:func:`resolve_confirm_vote`).
CONFIRM_DELIVERED = "delivered"
CONFIRM_CANDIDATE = "candidate"
CONFIRM_NEITHER = "neither"
CONFIRM_UNPARSED = "unparsed"


# ---------------------------------------------------------------------------
# canonical comparison (section 1: "normalize_filler_p2 plus number-word
# folding")
# ---------------------------------------------------------------------------

#: A v1-scoped, single-token number-word fold, applied AFTER
#: ``normalize_filler_p2`` for canonical comparison only. It never mutates a
#: persisted filler (blind or delivered) -- only the throwaway string
#: :func:`canonical_value` returns for an equality test. ``normalize_filler_
#: p2``'s own ``N`` rung already folds a DIGIT token to its English word
#: ("5" -> "five"), so this fold's own direction (word -> digit) is chosen
#: only so the two rules compose to one FIXED point applied identically to
#: both sides of every comparison; which direction is canonical is
#: immaterial to correctness as long as it is the same direction for both.
_NUMBER_WORDS: Mapping[str, str] = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
    "fourteen": "14", "fifteen": "15", "sixteen": "16", "seventeen": "17",
    "eighteen": "18", "nineteen": "19", "twenty": "20", "thirty": "30",
    "forty": "40", "fifty": "50", "sixty": "60", "seventy": "70",
    "eighty": "80", "ninety": "90", "hundred": "100",
}


def fold_number_words(text: str) -> str:
    """Replace whole number-word TOKENS with their digit string.

    Token-wise only (no compound-numeral arithmetic: "twenty one" stays two
    tokens, "20 1", never merged into "21") -- a v1-scoped fold, deliberately
    smaller than a full text-to-number library, because it exists only to
    make :func:`canonical_value` a fixed point across the small vocabulary
    the blind template's 8-word answers actually use.
    """

    if not isinstance(text, str) or not text:
        return text
    return " ".join(_NUMBER_WORDS.get(word, word) for word in text.split())


def canonical_value(text: str | None) -> str:
    """The canonical form section 1's acceptance rule compares by.

    ``rails.slurp_projection_v3.normalize_filler_p2`` (the pinned P2 rule),
    then :func:`fold_number_words`. ``None`` and the empty string both
    canonicalise to the empty string, so an absent blind value never
    accidentally compares equal to a non-empty delivered filler.
    """

    if not isinstance(text, str) or not text.strip():
        return ""
    from .slurp_projection_v3 import normalize_filler_p2  # noqa: PLC0415

    return fold_number_words(normalize_filler_p2(text))


def canonical_equal(a: str | None, b: str | None) -> bool:
    """Whether ``a`` and ``b`` are the same slot filler up to canonical form."""

    return canonical_value(a) == canonical_value(b)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# config (``native_episode.relisten``, section 6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelistenPolicy:
    """The one registered relisten policy record (mirrors ``rails.acquisition
    .AcquisitionPolicy``'s registration shape, at a smaller surface: v1 has
    exactly one policy, so this record carries identity only)."""

    policy_id: str
    contacts_per_entity: int = CONTACTS_PER_ENTITY

    def __post_init__(self) -> None:
        if self.policy_id != RELISTEN_POLICY_ID:
            raise RelistenError(f"unknown relisten policy id {self.policy_id!r}")


RELISTEN_POLICY: RelistenPolicy = RELISTEN_POLICIES.register(
    RELISTEN_POLICY_ID, RelistenPolicy(policy_id=RELISTEN_POLICY_ID),
)

#: The exact key set ``native_episode.relisten`` must declare (section 6):
#: no optional keys in v1, so a config can never silently omit a cap.
RELISTEN_CONFIG_KEYS: frozenset[str] = frozenset({
    "policy", "max_slots_per_row", "value_max_words", "delivery",
    "blind_template_id", "confirm_template_id",
})


@dataclass(frozen=True)
class RelistenConfig:
    """The parsed, validated ``native_episode.relisten`` block."""

    policy_id: str
    max_slots_per_row: int
    value_max_words: int
    delivery: str
    blind_template_id: str
    confirm_template_id: str

    def __post_init__(self) -> None:
        if self.policy_id != RELISTEN_POLICY_ID:
            raise RelistenError(f"relisten.policy must be {RELISTEN_POLICY_ID!r}")
        if (
            isinstance(self.max_slots_per_row, bool)
            or not isinstance(self.max_slots_per_row, int)
            or not 1 <= self.max_slots_per_row <= DEFAULT_MAX_SLOTS_PER_ROW
        ):
            raise RelistenError(
                "relisten.max_slots_per_row must be an integer in "
                f"1..{DEFAULT_MAX_SLOTS_PER_ROW}"
            )
        if (
            isinstance(self.value_max_words, bool)
            or not isinstance(self.value_max_words, int)
            or not 1 <= self.value_max_words <= MAX_VALUE_WORDS
        ):
            raise RelistenError(
                f"relisten.value_max_words must be an integer in 1..{MAX_VALUE_WORDS}"
            )
        if self.delivery != DELIVERY_MODE:
            raise RelistenError(f"relisten.delivery must be {DELIVERY_MODE!r} in v1")
        if self.blind_template_id != BLIND_TEMPLATE_ID:
            raise RelistenError(
                f"relisten.blind_template_id must be {BLIND_TEMPLATE_ID!r}"
            )
        if self.confirm_template_id != CONFIRM_TEMPLATE_ID:
            raise RelistenError(
                f"relisten.confirm_template_id must be {CONFIRM_TEMPLATE_ID!r}"
            )

    @property
    def extra_contacts_ceiling(self) -> int:
        """The ceiling's own additive term (section 3, section 6): up to
        :data:`CONTACTS_PER_ENTITY` contacts per declared slot."""

        return CONTACTS_PER_ENTITY * self.max_slots_per_row

    def as_json(self) -> str:
        """The canonical text a ``NativeEpisodeConfig`` stores (the same
        idiom ``knowledge_index_json`` / ``reviewer_audit_json`` use).

        Exactly :data:`RELISTEN_CONFIG_KEYS` -- no wrapping ``schema`` key --
        so ``parse_relisten(json.loads(self.relisten_json))`` round-trips
        without a second, incompatible shape to reconcile.
        """

        return json.dumps(
            {
                "policy": self.policy_id,
                "max_slots_per_row": self.max_slots_per_row,
                "value_max_words": self.value_max_words,
                "delivery": self.delivery,
                "blind_template_id": self.blind_template_id,
                "confirm_template_id": self.confirm_template_id,
            },
            sort_keys=True, separators=(",", ":"),
        )


def parse_relisten(raw: object) -> RelistenConfig:
    """Parse and validate ``native_episode.relisten`` (section 6). Model-free.

    Refused, by name, before any contact: an unknown key set, an
    unregistered policy id, or a value out of the declared bounds. Combining
    ``relisten`` with a Solver ``supply_variants`` arm group or a grouped
    Solver visit (``samples > 1``) is refused by the CALLER
    (``rails.native_episode_config.load_native_episode_config``), which is
    where those two facts are already known; this parser is config-shape
    only.
    """

    if not isinstance(raw, Mapping):
        raise RelistenError("native_episode.relisten must be an object")
    if set(raw) != RELISTEN_CONFIG_KEYS:
        raise RelistenError(
            "native_episode.relisten must declare exactly "
            f"{sorted(RELISTEN_CONFIG_KEYS)}"
        )
    policy_id = raw["policy"]
    if not isinstance(policy_id, str):
        raise RelistenError("relisten.policy must be a string")
    try:
        resolved = RELISTEN_POLICIES.resolve(policy_id)
    except CoreError as error:
        raise RelistenError(f"relisten.policy is invalid: {error}") from error
    if not isinstance(resolved, RelistenPolicy):
        raise RelistenError(f"relisten.policy {policy_id!r} is not a RelistenPolicy")
    for key in ("max_slots_per_row", "value_max_words"):
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise RelistenError(f"relisten.{key} must be an integer")
    for key in ("delivery", "blind_template_id", "confirm_template_id"):
        if not isinstance(raw[key], str):
            raise RelistenError(f"relisten.{key} must be a string")
    return RelistenConfig(
        policy_id=policy_id,
        max_slots_per_row=raw["max_slots_per_row"],
        value_max_words=raw["value_max_words"],
        delivery=raw["delivery"],
        blind_template_id=raw["blind_template_id"],
        confirm_template_id=raw["confirm_template_id"],
    )


def relisten_extra_ceiling(max_slots_per_row: int) -> int:
    """The ceiling formula's own additive term, as a free function so
    ``rails.native_episode_config``'s ceiling arithmetic and this module's
    tests read the exact same definition ``RelistenConfig.extra_contacts_
    ceiling`` does."""

    if isinstance(max_slots_per_row, bool) or not isinstance(max_slots_per_row, int) or max_slots_per_row < 0:
        raise RelistenError("max_slots_per_row must be a nonnegative integer")
    return CONTACTS_PER_ENTITY * max_slots_per_row


# ---------------------------------------------------------------------------
# targeting and ordering (section 1)
# ---------------------------------------------------------------------------


def select_relisten_targets(
    entities: Sequence[Mapping[str, object]], max_slots_per_row: int,
) -> tuple[int, ...]:
    """Up to ``max_slots_per_row`` delivered entity INDICES, in delivery
    order (section 1: "in delivery order", "no type filter"; the decided
    intent is never reopened -- there is no intent index to select here at
    all)."""

    if (
        isinstance(max_slots_per_row, bool)
        or not isinstance(max_slots_per_row, int)
        or max_slots_per_row < 0
    ):
        raise RelistenError("max_slots_per_row must be a nonnegative integer")
    return tuple(range(min(len(entities), max_slots_per_row)))


def confirm_order(sample_id: str, slot_type: str) -> tuple[str, str]:
    """Which of the two forced-choice OPTIONS sits at letter A vs B.

    Fixed by ``sha256(sample_id, slot_type)`` (section 1) so position bias
    cancels over the roster: ``("delivered", "candidate")`` when the
    digest's low bit is 0, the swapped tuple otherwise. ``"candidate"`` is
    the blind's own value on a differ-fire, or the UNHEARD sentinel on an
    unheard-fire (ruling 2b) -- the letter mapping is identical either way,
    only what "candidate" DENOTES differs, and that denotation is carried by
    the caller, never by this function.
    """

    if not isinstance(sample_id, str) or not isinstance(slot_type, str):
        raise RelistenError("confirm_order requires sample_id and slot_type strings")
    digest = hashlib.sha256(f"{sample_id}:{slot_type}".encode("utf-8")).digest()
    if digest[0] & 1 == 0:
        return (CONFIRM_DELIVERED, CONFIRM_CANDIDATE)
    return (CONFIRM_CANDIDATE, CONFIRM_DELIVERED)


# ---------------------------------------------------------------------------
# response parsing (finite-completion policy: a malformed answer never
# aborts the arm -- it becomes a per-entity flag, item 4 of the brief)
# ---------------------------------------------------------------------------

_WORD_SPLIT = re.compile(r"\s+")


@dataclass(frozen=True)
class BlindResult:
    """One parsed ``slurp-relisten-value-v1`` response."""

    disposition: str
    value: str | None
    word_count: int

    def __post_init__(self) -> None:
        if self.disposition not in BLIND_DISPOSITIONS:
            raise RelistenError(f"unknown blind disposition {self.disposition!r}")


def parse_blind_response(raw_text: str, *, max_words: int = MAX_VALUE_WORDS) -> BlindResult:
    """Parse one blind contact's response text. Never raises on bad input.

    Four dispositions, in the order this function tests them:

    * :data:`BLIND_UNPARSED` -- the text is not JSON, or is JSON that is not
      exactly ``{"heard": bool, "value": string}`` in shape;
    * :data:`BLIND_UNHEARD` -- a well-formed response with ``heard`` false;
    * :data:`BLIND_INVALID_LENGTH` -- ``heard`` true but the value is empty
      or over :data:`MAX_VALUE_WORDS` words (section 1: "An over-length or
      empty value keeps c ... as a per-row disposition") -- its own
      terminal state, never treated as a genuine "unheard" vote;
    * :data:`BLIND_VALUE` -- a well-formed, in-bound heard value.
    """

    try:
        payload = json.loads(raw_text)
    except (TypeError, ValueError):
        return BlindResult(BLIND_UNPARSED, None, 0)
    if not isinstance(payload, Mapping) or set(payload) != {"heard", "value"}:
        return BlindResult(BLIND_UNPARSED, None, 0)
    heard, value = payload.get("heard"), payload.get("value")
    if not isinstance(heard, bool) or not isinstance(value, str):
        return BlindResult(BLIND_UNPARSED, None, 0)
    if not heard:
        return BlindResult(BLIND_UNHEARD, None, 0)
    stripped = value.strip()
    word_count = len(_WORD_SPLIT.split(stripped)) if stripped else 0
    if word_count == 0 or word_count > max_words:
        return BlindResult(BLIND_INVALID_LENGTH, value, word_count)
    return BlindResult(BLIND_VALUE, value, word_count)


def should_fire_confirm(blind: BlindResult, delivered_value: str) -> bool:
    """Section 1's skip rule, extended by ruling 2b.

    Skip (spend nothing more) when the blind's own disposition is
    :data:`BLIND_INVALID_LENGTH` (its own terminal fallback -- section 1
    never asks a forced choice about a value already discarded for shape),
    or when it heard a value canonically equal to the delivered one. Fire
    otherwise: on a genuine disagreement (section 1's original trigger) and
    on a genuine ``heard = false`` or unparsed blind (ruling 2b: "the
    confirm contact is therefore also fired on a blind heard = false, so
    that both contacts vote").
    """

    if blind.disposition == BLIND_INVALID_LENGTH:
        return False
    if blind.disposition == BLIND_VALUE:
        return not canonical_equal(blind.value, delivered_value)
    return True  # BLIND_UNHEARD or BLIND_UNPARSED


def parse_confirm_letter(raw_text: str) -> str:
    """Parse one forced-choice response to its raw letter.

    Returns ``"A"``, ``"B"``, ``"neither"``, or :data:`CONFIRM_UNPARSED`.
    Never raises: a malformed confirm answer is its own flag, never an
    abort (item 4 of the brief).
    """

    try:
        payload = json.loads(raw_text)
    except (TypeError, ValueError):
        return CONFIRM_UNPARSED
    if not isinstance(payload, Mapping) or set(payload) != {"choice"}:
        return CONFIRM_UNPARSED
    choice = payload.get("choice")
    if choice not in ("A", "B", "neither"):
        return CONFIRM_UNPARSED
    return choice


def resolve_confirm_vote(letter: str, order: tuple[str, str]) -> str:
    """Map a parsed letter through the fixed ``order`` to what it means.

    Returns one of :data:`CONFIRM_DELIVERED`, :data:`CONFIRM_CANDIDATE`,
    :data:`CONFIRM_NEITHER`, :data:`CONFIRM_UNPARSED`.
    """

    if letter == CONFIRM_UNPARSED:
        return CONFIRM_UNPARSED
    if letter == "neither":
        return CONFIRM_NEITHER
    if letter not in ("A", "B"):
        raise RelistenError(f"unknown confirm letter {letter!r}")
    return order[0 if letter == "A" else 1]


# ---------------------------------------------------------------------------
# per-entity decision (section 1's acceptance rule; ruling 2b's drop vote)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RelistenEntityRecord:
    """One entity's sealed decision -- the receipt's per-entity unit."""

    index: int
    slot_type: str
    blind_contact_id: str
    blind_disposition: str
    blind_value_sha256: str | None
    blind_canonical_sha256: str | None
    blind_word_count: int
    confirm_fired: bool
    confirm_contact_id: str | None
    confirm_order: tuple[str, str] | None
    confirm_vote: str | None
    accept: bool
    confirm_unheard_vote: bool | None
    #: The accepted filler text itself, kept ONLY in-process for the caller
    #: that renders the LIVE bound answer at bind time; never sealed into the
    #: receipt (``as_receipt`` omits it) and never compared for equality --
    #: the "no transcript state" rule (module docstring).
    bound_value: str | None = field(default=None, compare=False)

    @property
    def dropped_when_unheard(self) -> bool:
        """Column (b)'s drop condition (ruling 2b): both contacts vote
        unheard."""

        return (
            self.blind_disposition in (BLIND_UNHEARD, BLIND_UNPARSED)
            and bool(self.confirm_unheard_vote)
        )

    def as_receipt(self) -> dict[str, object]:
        """The per-entity block ``saea-relisten-v1`` seals: contact ids,
        hashes and flags -- never the value's own bytes (module docstring's
        receipt paragraph)."""

        return {
            "index": self.index,
            "slot_type": self.slot_type,
            "blind": {
                "contact_id": self.blind_contact_id,
                "disposition": self.blind_disposition,
                "value_sha256": self.blind_value_sha256,
                "canonical_sha256": self.blind_canonical_sha256,
                "word_count": self.blind_word_count,
            },
            "confirm": (
                None if not self.confirm_fired else {
                    "contact_id": self.confirm_contact_id,
                    "order": list(self.confirm_order) if self.confirm_order else None,
                    "vote": self.confirm_vote,
                }
            ),
            "accept": self.accept,
            "confirm_unheard_vote": self.confirm_unheard_vote,
        }


def decide_entity(
    *,
    index: int,
    slot_type: str,
    delivered_value: str,
    blind: BlindResult,
    blind_contact_id: str,
    confirm_letter: str | None,
    order: tuple[str, str] | None,
    confirm_contact_id: str | None = None,
) -> RelistenEntityRecord:
    """Section 1's acceptance rule, extended by ruling 2b's drop vote.

    ``confirm_letter`` / ``order`` / ``confirm_contact_id`` are ``None``
    exactly when :func:`should_fire_confirm` was ``False`` for this entity
    (the second contact was never spent) -- the caller (the runner's own
    dispatch loop, not this module) is what actually decides whether to
    spend it, using that same predicate.
    """

    fired = confirm_letter is not None
    if fired and (order is None or confirm_contact_id is None):
        raise RelistenError(
            "a fired confirm contact requires its fixed order and its contact id"
        )
    vote = resolve_confirm_vote(confirm_letter, order) if fired else None
    accept = False
    confirm_unheard_vote: bool | None = None
    if fired:
        if blind.disposition in (BLIND_UNHEARD, BLIND_UNPARSED):
            # Ruling 2b: the confirm contact ALSO votes on hearing. Choosing
            # the candidate slot (the UNHEARD sentinel here) or "neither" is
            # a vote FOR "not heard"; choosing the delivered slot is a vote
            # AGAINST it (the confirm contradicts the blind). An unparsed
            # confirm is conservative: no drop, no replace.
            confirm_unheard_vote = vote in (CONFIRM_CANDIDATE, CONFIRM_NEITHER, CONFIRM_UNPARSED)
            accept = False  # v1 never manufactures a value from a non-value blind
        else:
            # disposition == BLIND_VALUE and canonically different from c
            # (the only other reason a confirm fires): accept iff the
            # confirm chose the candidate slot -- the blind's own value.
            accept = vote == CONFIRM_CANDIDATE
    value_sha = _sha256_text(blind.value) if blind.value is not None else None
    canonical_sha = (
        _sha256_text(canonical_value(blind.value)) if blind.value is not None else None
    )
    return RelistenEntityRecord(
        index=index,
        slot_type=slot_type,
        blind_contact_id=blind_contact_id,
        blind_disposition=blind.disposition,
        blind_value_sha256=value_sha,
        blind_canonical_sha256=canonical_sha,
        blind_word_count=blind.word_count,
        confirm_fired=fired,
        confirm_contact_id=confirm_contact_id if fired else None,
        confirm_order=order,
        confirm_vote=vote,
        accept=accept,
        confirm_unheard_vote=confirm_unheard_vote,
        bound_value=blind.value if accept else None,
    )


# ---------------------------------------------------------------------------
# receipt sealing (section 1's receipt paragraph)
# ---------------------------------------------------------------------------


def seal_relisten_receipt(
    records: Sequence[RelistenEntityRecord], *, max_slots_per_row: int,
) -> dict[str, object]:
    """The row's ``saea-relisten-v1`` receipt.

    ``contacts_used`` is one blind contact per triggered entity plus one
    confirm contact per entity whose ``confirm_fired`` is true -- both
    contacts count against the budget (section 1's implementation
    instructions), so this is exactly the row's own relisten spend, never
    an estimate.
    """

    if (
        isinstance(max_slots_per_row, bool)
        or not isinstance(max_slots_per_row, int)
        or not 1 <= max_slots_per_row <= DEFAULT_MAX_SLOTS_PER_ROW
    ):
        raise RelistenError(
            f"max_slots_per_row must be an integer in 1..{DEFAULT_MAX_SLOTS_PER_ROW}"
        )
    if len(records) > max_slots_per_row:
        raise RelistenError("more relisten records than the declared max_slots_per_row")
    contacts_used = len(records) + sum(1 for record in records if record.confirm_fired)
    return {
        "schema": RELISTEN_RECEIPT_SCHEMA,
        "policy": RELISTEN_POLICY_ID,
        "max_slots_per_row": max_slots_per_row,
        "triggered_count": len(records),
        "contacts_used": contacts_used,
        "entities": [record.as_receipt() for record in records],
    }


def relisten_contact_request_ids(receipt: object) -> tuple[str, ...]:
    """The request ids of a sealed ``saea-relisten-v1`` receipt's own SHADOW
    contacts: every entity's blind contact and, when fired, its confirm
    contact, in receipt order (the order the runner spent them).

    The runner records each contact's ``completion.request_id`` as the
    receipt's ``contact_id`` (``rails.runner.run_relisten_stage``), so these
    are the same identities the client's per-request timings carry. The seal
    uses them to tell the post-delivery shadow contacts apart from the actual
    sample contacts that could move delivery (E4-1 seal abort, 2026-09-29).
    ``None`` -- a row whose config never armed ``native_episode.relisten``,
    or an abstention -- names no contact. Structure only: I7l
    (``core.bundle.outputs._verify_relisten_trace_binding``) remains the
    authority on each contact's trace pair, sample and parsed content.
    """

    if receipt is None:
        return ()
    if not isinstance(receipt, Mapping):
        raise RelistenError("relisten receipt must be an object")
    entities = receipt.get("entities")
    if not isinstance(entities, Sequence) or isinstance(entities, (str, bytes)):
        raise RelistenError("relisten receipt carries no entities list")
    request_ids: list[str] = []
    for entity in entities:
        if not isinstance(entity, Mapping):
            raise RelistenError("relisten entity is not an object")
        blocks = [entity.get("blind")]
        if entity.get("confirm") is not None:
            blocks.append(entity["confirm"])
        for block in blocks:
            contact_id = block.get("contact_id") if isinstance(block, Mapping) else None
            if not isinstance(contact_id, str) or not contact_id:
                raise RelistenError("relisten contact has invalid identity")
            if contact_id in request_ids:
                raise RelistenError("relisten receipt repeats a contact identity")
            request_ids.append(contact_id)
    return tuple(request_ids)


#: The pinned response-format schema names that tell a recorded relisten
#: contact's kind apart in a trace (the request payload's
#: ``decoding_params.response_format.json_schema.name``).
BLIND_SCHEMA_NAME = "slurp_relisten_value_v1"
CONFIRM_SCHEMA_NAME = "slurp_relisten_confirm_v1"
CONTACT_KIND_BY_SCHEMA_NAME = {
    BLIND_SCHEMA_NAME: "blind",
    CONFIRM_SCHEMA_NAME: "confirm",
}


def replay_relisten_receipt(
    *,
    sample_id: str,
    delivered_text: str,
    contacts: Sequence[tuple[str, str, str]],
    config: RelistenConfig,
    delivered_units=None,
) -> dict[str, object]:
    """Re-derive a row's sealed ``saea-relisten-v1`` receipt from its trace.

    Model-free: ``contacts`` is the row's own recorded relisten contacts in
    dispatch order, each ``(request_id, kind, response_text)`` with ``kind``
    ``"blind"`` or ``"confirm"``. The walk is the runner's own
    (``rails.runner.run_relisten_stage``): parse the DELIVERED answer (after
    the deliver normaliser), target up to ``max_slots_per_row`` entities in
    delivery order, consume one blind contact per target and one confirm
    contact exactly when :func:`should_fire_confirm` says the live stage
    spent one, and seal through the SAME :func:`decide_entity` /
    :func:`seal_relisten_receipt`. A contact of the wrong kind, a missing
    contact, or a left-over contact is refused, never approximated -- a
    resume-recovery then re-flies the row (``core.flight.resume``).
    """

    if not isinstance(config, RelistenConfig):
        raise RelistenError("relisten replay requires the cell's RelistenConfig")
    # Migration step 5: the delivered units come from the carrier's
    # ``delivered_units`` hook; ``None`` is SLURP's (the one carrier re-listen
    # is armed on), exactly the live runner's default.
    if delivered_units is None:
        from .adapters.slurp_module_hooks import slurp_delivered_units  # noqa: PLC0415

        delivered_units = slurp_delivered_units
    pending = list(contacts)

    def take(kind: str) -> tuple[str, str]:
        if not pending:
            raise RelistenError(f"relisten replay expected a {kind} contact the trace lacks")
        request_id, recorded_kind, text = pending.pop(0)
        if recorded_kind != kind:
            raise RelistenError(
                f"relisten replay expected a {kind} contact, the trace records a "
                f"{recorded_kind!r} contact ({request_id!r})"
            )
        if not isinstance(text, str):
            raise RelistenError(f"relisten contact {request_id!r} has no recorded response")
        return request_id, text

    _label, entities, parsed = delivered_units(delivered_text)
    records: list[RelistenEntityRecord] = []
    if parsed:
        for index in select_relisten_targets(entities, config.max_slots_per_row):
            entity = entities[index]
            blind_id, blind_text = take("blind")
            blind = parse_blind_response(blind_text, max_words=config.value_max_words)
            confirm_letter = confirm_id = order = None
            if should_fire_confirm(blind, entity.filler):
                order = confirm_order(sample_id, entity.type)
                confirm_id, confirm_text = take("confirm")
                confirm_letter = parse_confirm_letter(confirm_text)
            records.append(decide_entity(
                index=index, slot_type=entity.type, delivered_value=entity.filler,
                blind=blind, blind_contact_id=blind_id,
                confirm_letter=confirm_letter, order=order,
                confirm_contact_id=confirm_id,
            ))
    if pending:
        raise RelistenError(
            f"relisten replay leaves {len(pending)} recorded relisten contact(s) unexplained"
        )
    return seal_relisten_receipt(records, max_slots_per_row=config.max_slots_per_row)


# ---------------------------------------------------------------------------
# shadow columns (ruling 2; rendered offline by
# ``scripts/analysis/stage3_rollout_score.py``'s
# ``render_relisten_shadow_columns`` from the sealed receipt above plus the
# sealed trace's own bound values)
# ---------------------------------------------------------------------------


def bind_shadow_entities(
    delivered_entities: Sequence[Mapping[str, object]],
    receipt: Mapping[str, object],
    *,
    bound_values: Mapping[int, str] = {},
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Render columns (a) replace-only and (b) replace-plus-drop-when-unheard.

    Pure post-processing over already-sealed bytes: no model contact, no new
    randomness -- exactly the "same-flight-paired, shadow delivery" design
    (section 4). ``bound_values`` supplies the ACCEPTED filler text for an
    ``accept`` entity, keyed by its ``index``, read by the caller from the
    row's own sealed trace (the receipt itself carries only a hash, never
    the value's bytes -- the "no transcript state" rule). An accepted entity
    whose value is missing from ``bound_values`` is left unreplaced rather
    than silently dropped, and the caller (the renderer's own AT1 self-check)
    is expected to treat that as a reproduction failure, not this function.

    Returns ``(column_a, column_b)``, each a list of ``{"type", "filler"}``
    entity dicts in the SAME delivery order as ``delivered_entities`` (column
    (b) simply omits the dropped indices, preserving the remaining order).
    """

    if receipt.get("schema") != RELISTEN_RECEIPT_SCHEMA:
        raise RelistenError("bind_shadow_entities requires a saea-relisten-v1 receipt")
    entities = receipt.get("entities")
    if not isinstance(entities, Sequence):
        raise RelistenError("saea-relisten-v1 receipt carries no entities list")
    by_index: dict[int, Mapping[str, object]] = {}
    for entry in entities:
        if not isinstance(entry, Mapping) or "index" not in entry:
            raise RelistenError("a relisten receipt entity is malformed")
        by_index[int(entry["index"])] = entry

    column_a = [dict(entity) for entity in delivered_entities]
    drop: set[int] = set()
    for index, entry in by_index.items():
        if not 0 <= index < len(column_a):
            raise RelistenError("a relisten receipt entity index is out of range")
        if entry.get("accept"):
            value = bound_values.get(index)
            if value is not None:
                column_a[index] = {**column_a[index], "filler": value}
        blind = entry.get("blind") or {}
        if (
            blind.get("disposition") in (BLIND_UNHEARD, BLIND_UNPARSED)
            and entry.get("confirm_unheard_vote")
        ):
            drop.add(index)
    column_b = [entity for index, entity in enumerate(column_a) if index not in drop]
    return column_a, column_b
