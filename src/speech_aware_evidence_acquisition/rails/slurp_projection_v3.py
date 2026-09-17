"""SLURP USE-axis projection v3 (module M3, SLURP v2 base program).

Decided by the A1 USE-projection audit on sealed outputs
(``docs/results/2026-09-17-slurp-a1-use-projection-audit-v1.md``) and named as
module M3 by the program design
(``docs/superpowers/specs/2026-09-16-slurp-v2-base-program-design.md`` section
3, row M3, and section 4, item E4). Zero model or server contacts: this
module is pure, deterministic post-processing of an already-delivered SLURP
answer ``{scenario, action, entities: [{type, filler}]}``, applied either
AFTER the fact by a scorer (``reproduction.slurp_official_eval``'s
``score_slurp_outputs_official_projected_v3[_train]``) or BEFORE sealing by
the runtime delivery transform below, so a future cell that turns the runtime
transform on delivers an answer the v3 scorer then finds already projected
(a no-op on it).

Projection v3 has two independent halves, applied in this fixed order:

1. **Label rule** (:func:`project_slu_label_v3`): rule ``R_action``, then the
   already-registered ``slurp-legal-label-projection-v2``
   (:func:`reproduction.slurp_scoring.project_slu_label_v2`) as the
   unmodified fallback. ``R_action`` fires only when the delivered
   ``(scenario, action)`` pair is ILLEGAL (outside the 60-id TRAIN inventory)
   AND the delivered ACTION string, taken alone, is byte-identical to one of
   the 60 legal composed intent ids (``f"{scenario}_{action}"`` for some
   legal pair) -- for example a delivered pair of ``(scenario="music",
   action="play_music")`` is illegal (``music`` has no ``play_music``
   action), but the action string ``"play_music"`` IS itself the legal id
   for ``(scenario="play", action="music")``, so ``R_action`` adopts that
   id's own split. When the delivered pair is already legal, or the action
   string names no legal id, this rule changes nothing beyond what v2 itself
   would do; entities are never touched by this half (A1's own finding:
   "Intent accuracy must change ONLY through the label rule; the entity
   block never changes labels").
2. **Filler normalisation P2** (:func:`normalize_filler_p2` and its four
   named rungs): a deterministic surface rewrite of every PREDICTED filler
   toward SLURP's spoken-form convention -- never applied to gold, and never
   filtered by support (A1's P1a/P1b support filter was REJECTED; v3 carries
   none). Ported VERBATIM from the A1 driver
   (``SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-A1-USE-PROJECTION-AUDIT-V1/
   driver/a1_use_projection_audit.py``, functions ``normalize_filler_p2`` and
   its ``P2_RULE_SETS`` ladder) so the rung-level numbers reproduce exactly;
   see that function's own docstring for its two documented limitations
   (a four-digit year rendering as a cardinal, e.g. "two thousand nineteen",
   and a leading currency symbol such as ``"$"`` being stripped as
   punctuation rather than converted, because the numeric rung (N) runs
   BEFORE the punctuation-strip rung (P) in the fixed rule order below).

Both halves are exposed once here and consumed by BOTH the scorer
(``reproduction.slurp_official_eval``) and the runtime delivery transform
(:func:`apply_slurp_projection_v3_delivery`), so the two forms can never
drift into two different rules.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache

from ..reproduction.slurp_scoring import (
    LabelProjection,
    LegalIntentInventory,
    SlotEntity,
    parse_slu_response,
    project_slu_label_v2,
)

#: Identity of the label half of projection v3 (``R_action`` then the
#: registered v2 fallback, module docstring). Bumped only when the RULE
#: changes, mirroring ``SLURP_LABEL_PROJECTION_V2_ID``'s own bump policy.
SLURP_LABEL_PROJECTION_V3_ID = "slurp-legal-label-projection-v3"

#: The NEW branch v3 introduces beyond ``reproduction.slurp_scoring``'s own
#: :data:`~reproduction.slurp_scoring.PROJECTION_BRANCHES` -- every scorer
#: and runtime call site that counts branches uses ``dict.get(branch, 0)``
#: already, so this is additive and never requires editing that tuple.
PROJECTION_BRANCH_R_ACTION = "r-action"

#: Identity of the filler-normalisation half (P2, all four rungs, no support
#: filter -- A1's "Consequences for the program" section).
SLURP_FILLER_NORMALIZATION_P2_ID = "saea-slurp-filler-normalization-p2-v1"

#: Combined identity for the whole v3 projection (label half + filler half),
#: used as the runtime delivery transform's own ``rule_id``.
SLURP_PROJECTION_V3_ID = "slurp-use-projection-v3"

#: The ONE flat, per-run config key that switches the runtime delivery
#: transform on (``rails.config_tables.RUN_LEVEL_SWITCH_KEYS``): read
#: directly by ``core.flight.runtime.FlightRuntime`` exactly the way
#: ``obs_prefetch_depth`` is read by ``core.driver.run`` -- a scalar the
#: driver consults, never a named ``core.base`` registry entry, because this
#: transform (like the dispatcher) moves no request byte and has no second
#: implementation to select among. ``1`` is ON; absent or ``0`` is OFF (the
#: driver's documented default -- ``rails.config_tables.is_run_null_arm``
#: already treats both as the null arm for an int-valued run key).
SLURP_PROJECTION_V3_DELIVERY_KEY = "slurp_projection_v3_delivery"


# ---------------------------------------------------------------------------
# P2 filler normalisation -- ported VERBATIM from the A1 driver (module
# docstring). Every constant and regex below is byte-for-byte the driver's
# own, so the A1 numbers (TRAIN A 51.995, DEV1000 agent 54.031) reproduce.
# ---------------------------------------------------------------------------

_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_ORD_ONES = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
    7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh", 12: "twelfth",
    13: "thirteenth", 14: "fourteenth", 15: "fifteenth", 16: "sixteenth",
    17: "seventeenth", 18: "eighteenth", 19: "nineteenth",
}
_ORD_TENS = {
    20: "twentieth", 30: "thirtieth", 40: "fortieth", 50: "fiftieth", 60: "sixtieth",
    70: "seventieth", 80: "eightieth", 90: "ninetieth",
}


def _cardinal(value: int) -> str | None:
    if value < 0 or value > 999_999:
        return None
    if value < 20:
        return _ONES[value]
    if value < 100:
        tens, ones = divmod(value, 10)
        return _TENS[tens] if ones == 0 else f"{_TENS[tens]} {_ONES[ones]}"
    if value < 1000:
        hundreds, rest = divmod(value, 100)
        head = f"{_ONES[hundreds]} hundred"
        return head if rest == 0 else f"{head} {_cardinal(rest)}"
    thousands, rest = divmod(value, 1000)
    head = f"{_cardinal(thousands)} thousand"
    return head if rest == 0 else f"{head} {_cardinal(rest)}"


def _ordinal(value: int) -> str | None:
    if value in _ORD_ONES:
        return _ORD_ONES[value]
    if value in _ORD_TENS:
        return _ORD_TENS[value]
    if 20 < value < 100:
        tens, ones = divmod(value, 10)
        if ones:
            return f"{_TENS[tens]} {_ORD_ONES[ones]}"
    return None


_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})(am|pm)?$")
_PERCENT_RE = re.compile(r"^(\d+)%$")
_ORDINAL_RE = re.compile(r"^(\d+)(st|nd|rd|th)$")
_DECIMAL_RE = re.compile(r"^(\d+)\.(\d+)$")
_MERIDIEM_NUM_RE = re.compile(r"^(\d+)(am|pm)$")
_INT_RE = re.compile(r"^(\d+)$")


def _minute_words(minutes: int) -> str:
    if minutes == 0:
        return ""
    if minutes < 10:
        return f"oh {_ONES[minutes]}"
    return _cardinal(minutes) or ""


def _numeric_token(token: str) -> str:
    """First matching rule wins (module docstring's rule (N)): ``H:MM[am|pm]``,
    ``N%``, ``N(st|nd|rd|th)``, ``N.M``, ``N(am|pm)``, then a bare integer;
    every other token is returned unchanged. A four-digit year falls through
    to the bare-integer rule and renders as a cardinal (e.g. "two thousand
    nineteen" for ``2019``) -- a documented limitation, not a bug: this rung
    has no calendar-year special case."""

    match = _TIME_RE.match(token)
    if match:
        hour = _cardinal(int(match.group(1)))
        if hour is None:
            return token
        parts = [hour]
        minutes = _minute_words(int(match.group(2)))
        if minutes:
            parts.append(minutes)
        if match.group(3):
            parts.append(match.group(3))
        return " ".join(parts)
    match = _PERCENT_RE.match(token)
    if match:
        head = _cardinal(int(match.group(1)))
        return f"{head} percent" if head is not None else token
    match = _ORDINAL_RE.match(token)
    if match:
        word = _ordinal(int(match.group(1)))
        return word if word is not None else token
    match = _DECIMAL_RE.match(token)
    if match:
        head = _cardinal(int(match.group(1)))
        if head is None:
            return token
        digits = " ".join(_ONES[int(digit)] for digit in match.group(2))
        return f"{head} point {digits}"
    match = _MERIDIEM_NUM_RE.match(token)
    if match:
        head = _cardinal(int(match.group(1)))
        return f"{head} {match.group(2)}" if head is not None else token
    match = _INT_RE.match(token)
    if match:
        word = _cardinal(int(match.group(1)))
        return word if word is not None else token
    return token


_APOSTROPHES = {"‘": "'", "’": "'", "ʼ": "'", "´": "'", "`": "'"}
_DASHES = {
    "‐": "-", "‑": "-", "‒": "-", "–": "-", "—": "-", "−": "-",
}
_MERIDIEM_RULES = (
    (re.compile(r"\ba\s*\.\s*m\s*\.?"), "am"),
    (re.compile(r"\bp\s*\.\s*m\s*\.?"), "pm"),
    (re.compile(r"\ba\s+m\b"), "am"),
    (re.compile(r"\bp\s+m\b"), "pm"),
)
_KEEP_RE = re.compile(r"[^a-z0-9\s'-]")

#: The four named P2 rungs (A1's own ablation ladder), each a cumulative rule
#: set consumed by :func:`normalize_filler_p2`. The rule LETTERS ("U", "L",
#: "M", "N", "P", "W") are the driver's own; ``normalize_filler_p2`` always
#: tests them in this fixed U/L/M/N/P/W order regardless of which subset a
#: rung names, so going from rung 1 to rung 2 inserts the meridiem step
#: BEFORE the punctuation step already present, and the full rung inserts
#: the numeric step BEFORE punctuation too -- this is why a leading currency
#: symbol is lost rather than converted (module docstring): the numeric rung
#: runs on ``"$5"`` (no match; the token still carries ``$``) and only the
#: LATER punctuation rung strips the symbol, by which point the numeric rung
#: has already passed it by.
RUNG_0_CASE_WHITESPACE: tuple[str, ...] = ("U", "L", "W")
RUNG_1_PUNCTUATION: tuple[str, ...] = ("U", "L", "P", "W")
RUNG_2_MERIDIEM: tuple[str, ...] = ("U", "L", "M", "P", "W")
RUNG_3_NUMERIC: tuple[str, ...] = ("U", "L", "M", "N", "P", "W")

#: The full P2 rule (rung 3): case + whitespace + punctuation + meridiem +
#: numeric words. This is what module M3 (and the runtime delivery
#: transform) applies -- never a lower rung alone.
P2_FULL_RULES: tuple[str, ...] = RUNG_3_NUMERIC

#: The rung ladder in reporting order, name paired with its cumulative rule
#: set, so a caller can report the decomposition (A1's own rung ablation)
#: without re-deriving the rule sets.
P2_RUNGS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("rung0_case_whitespace", RUNG_0_CASE_WHITESPACE),
    ("rung1_punctuation", RUNG_1_PUNCTUATION),
    ("rung2_meridiem", RUNG_2_MERIDIEM),
    ("rung3_numeric", RUNG_3_NUMERIC),
)


def normalize_filler_p2(filler: str, rules: tuple[str, ...] = P2_FULL_RULES) -> str:
    """Surface-normalise one predicted filler toward SLURP's spoken
    convention (module docstring; ported verbatim from the A1 driver's own
    ``normalize_filler_p2``).

    Rules, always tested in this fixed order and applied only when present
    in ``rules``:

    - ``U`` -- typographic apostrophes and dashes folded to ASCII;
    - ``L`` -- lowercase;
    - ``M`` -- meridiem canonicalisation (``"a.m."``, ``"a m"``, ``"AM"`` (via
      ``L`` first) all fold to ``"am"``; symmetrically for ``"pm"``);
    - ``N`` -- numeric tokens to English words, per whitespace token
      (:func:`_numeric_token`);
    - ``P`` -- punctuation strip: keep ``[a-z0-9]``, whitespace and an
      apostrophe anywhere, and a hyphen only when it sits between two
      alphanumerics (an internal hyphen; a leading/trailing/isolated one is
      dropped);
    - ``W`` -- collapse whitespace and strip.

    A rule that would empty an originally non-empty filler is refused and
    the ORIGINAL filler is returned unchanged (never an empty string): this
    is the driver's own "refuse to empty a nonempty filler" guard.
    """

    if not isinstance(filler, str) or not filler.strip():
        return filler
    text = filler
    if "U" in rules:
        for source, target in _APOSTROPHES.items():
            text = text.replace(source, target)
        for source, target in _DASHES.items():
            text = text.replace(source, target)
    if "L" in rules:
        text = text.lower()
    if "M" in rules:
        for pattern, target in _MERIDIEM_RULES:
            text = pattern.sub(target, text)
    if "N" in rules:
        text = " ".join(_numeric_token(token) for token in text.split())
    if "P" in rules:
        text = _KEEP_RE.sub(" ", text)
        text = re.sub(r"(?<![a-z0-9])-|-(?![a-z0-9])", " ", text)
    if "W" in rules:
        text = " ".join(text.split())
    return text if text else filler


def normalize_filler_p2_rung0_case_whitespace(filler: str) -> str:
    """Rung 0: case + whitespace only -- the official-scorer asymmetry
    alone (``evaluate.py`` lower-cases gold, never the prediction)."""

    return normalize_filler_p2(filler, RUNG_0_CASE_WHITESPACE)


def normalize_filler_p2_rung1_punctuation(filler: str) -> str:
    """Rung 1: rung 0 plus the punctuation strip."""

    return normalize_filler_p2(filler, RUNG_1_PUNCTUATION)


def normalize_filler_p2_rung2_meridiem(filler: str) -> str:
    """Rung 2: rung 1 plus meridiem canonicalisation."""

    return normalize_filler_p2(filler, RUNG_2_MERIDIEM)


def normalize_filler_p2_rung3_numeric(filler: str) -> str:
    """Rung 3, the FULL P2 rule: rung 2 plus numeric tokens to English
    words. Identical to :func:`normalize_filler_p2` called with no
    ``rules`` argument; named separately so the rung ladder can be iterated
    uniformly (:data:`P2_RUNGS`)."""

    return normalize_filler_p2(filler, RUNG_3_NUMERIC)


#: Alias: the full P2 rule under its "rung" name, for symmetry with the
#: other three rung functions above.
normalize_filler_p2_full = normalize_filler_p2_rung3_numeric


def normalize_entities_p2(
    entities: Sequence[SlotEntity],
) -> tuple[tuple[SlotEntity, ...], int]:
    """Apply the full P2 rule to every entity's filler.

    Asymmetric and unconditional (module docstring): the PREDICTED side
    only, on every entity regardless of type -- v3 carries no support filter
    of any kind (A1's P1a/P1b were REJECTED). Types are never touched, and
    an entity whose filler does not change is returned as the SAME object
    (identity-preserving where possible, never required by callers).

    Returns ``(new_entities, changed_count)`` where ``changed_count`` is the
    number of entities whose filler text differs from its input.
    """

    changed = 0
    result: list[SlotEntity] = []
    for entity in entities:
        new_filler = normalize_filler_p2(entity.filler)
        if new_filler != entity.filler:
            changed += 1
            result.append(SlotEntity(type=entity.type, filler=new_filler))
        else:
            result.append(entity)
    return tuple(result), changed


# ---------------------------------------------------------------------------
# Label rule: R_action, then the registered v2 fallback (module docstring).
# ---------------------------------------------------------------------------


def _composed_id_to_pair(inventory: LegalIntentInventory) -> dict[str, tuple[str, str]]:
    """Every legal composed intent id (``f"{scenario}_{action}"``) mapped
    back to its own ``(scenario, action)`` split -- the SAME 60 pairs
    ``inventory.pairs`` already carries, just indexed the other way. Scenario
    names in this ontology never contain an underscore, so this mapping is a
    bijection over the 60 legal pairs; even if it were not, this dict
    comprehension resolves any collision deterministically (last write wins
    over ``inventory.pairs``' own arbitrary set order) rather than raising,
    because a same-string collision would make BOTH candidate splits equally
    unrecoverable from the string alone."""

    return {f"{scenario}_{action}": (scenario, action) for scenario, action in inventory.pairs}


def project_slu_label_v3(
    scenario: str | None,
    action: str | None,
    inventory: LegalIntentInventory,
    *,
    parsed: bool = True,
) -> LabelProjection:
    """``slurp-legal-label-projection-v3``: rule ``R_action``, then v2.

    A1's own "Two findings" section 2 (``docs/results/
    2026-09-17-slurp-a1-use-projection-audit-v1.md``): measured against
    gold, on TRAIN A ``R_action`` alone repairs 15 of 20 illegal rows (+1.389
    pp intent, 79.352) where v2's edit-distance fallback mis-repairs the
    same class (e.g. ``music_play_music -> music_likeness``). ``R_action``
    is applied FIRST, ahead of v2, exactly as A1 preregisters it for E4.

    Rows 1-3 of the underlying rule are v1/v2's own, reached through
    :func:`reproduction.slurp_scoring.project_slu_label_v2` unchanged: an
    unparsed response stays unparsed, a row missing either half is
    untouched, and a row already naming a legal pair is untouched (task
    instruction 1: "When (scenario, action) is already legal, do nothing").
    For an ILLEGAL pair:

    * **R_action** -- if the delivered ACTION string, taken alone, is
      byte-identical to one of the 60 legal composed intent ids
      (``f"{scenario}_{action}"`` for some legal pair), adopt THAT id's own
      ``(scenario, action)`` split, discarding the delivered scenario
      entirely. For example a delivered ``(scenario="music",
      action="play_music")`` is illegal, but ``"play_music"`` is itself the
      legal id for ``(scenario="play", action="music")``, so R_action emits
      ``(scenario="play", action="music")``. Recorded under the NEW branch
      :data:`PROJECTION_BRANCH_R_ACTION`.
    * **v2 fallback** -- otherwise, :func:`reproduction.slurp_scoring.
      project_slu_label_v2` unchanged (its own 4-PROMOTE then edit-distance
      branches).

    Entities are not an argument and are never touched (task instruction 3):
    every entity-side metric is structurally unchanged by this function,
    exactly as under v1/v2.
    """

    if (
        parsed
        and isinstance(scenario, str)
        and isinstance(action, str)
        and (scenario, action) not in inventory.pairs
    ):
        target = _composed_id_to_pair(inventory).get(action)
        if target is not None:
            target_scenario, target_action = target
            return LabelProjection(
                scenario=target_scenario,
                action=target_action,
                # The source pair is illegal by the guard above and the
                # target is a legal pair, so the two can never be equal.
                changed=True,
                eligible=True,
                source_scenario=scenario,
                source_action=action,
                branch=PROJECTION_BRANCH_R_ACTION,
            )
    return project_slu_label_v2(scenario, action, inventory, parsed=parsed)


@dataclass(frozen=True)
class ProjectionV3Outcome:
    """One row's complete USE projection v3 outcome: the label half's own
    :class:`~reproduction.slurp_scoring.LabelProjection` plus the filler
    half's changed-entity count, kept as two separate fields exactly because
    A1's contract (task instruction 3) requires intent accuracy to move
    ONLY through the label half."""

    scenario: str | None
    action: str | None
    entities: tuple[SlotEntity, ...]
    label: LabelProjection
    fillers_changed: int

    @property
    def any_filler_changed(self) -> bool:
        return self.fillers_changed > 0


def apply_projection_v3(
    scenario: str | None,
    action: str | None,
    entities: Sequence[SlotEntity],
    inventory: LegalIntentInventory,
    *,
    parsed: bool = True,
) -> ProjectionV3Outcome:
    """Apply the complete USE projection v3 (label half then filler half) to
    one delivered SLURP answer. Pure and deterministic; zero model or corpus
    lookups beyond the already-loaded ``inventory``."""

    label = project_slu_label_v3(scenario, action, inventory, parsed=parsed)
    new_entities, fillers_changed = normalize_entities_p2(entities)
    return ProjectionV3Outcome(
        scenario=label.scenario,
        action=label.action,
        entities=new_entities,
        label=label,
        fillers_changed=fillers_changed,
    )


# ---------------------------------------------------------------------------
# Runtime delivery transform (deliverable 2): the SAME function above,
# applied to a delivered SLURP answer's response TEXT before it is sealed
# into an outputs row. Consumed by ``core.flight.runtime.FlightRuntime``'s
# ``_canonical_output_rows`` (the seal point common to both the native
# episode and the direct phase program), gated by carrier identity and the
# ONE flat run-level config key :data:`SLURP_PROJECTION_V3_DELIVERY_KEY`.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def _default_legal_intent_inventory() -> LegalIntentInventory:
    """The real TRAIN-mined inventory, loaded once per process -- the SAME
    umbrella lock + data root every other SLURP delivery-rule builder in
    ``reproduction.slurp_delivery`` loads its own inventory from (e.g.
    ``slurp_joint_hypothesis_delivery_v1``), cached the way ``core.policies.
    _cached_umbrella_lock`` caches the lock itself. Deferred imports: this
    module must not import ``reproduction.slurp_official_eval`` at module
    scope, because that module imports THIS one for the v3 scorer -- a cycle
    this function call breaks by staying lazy."""

    from ..data.lock import data_root, load_lock, umbrella_lock_path  # noqa: PLC0415
    from ..reproduction.slurp_official_eval import load_legal_intent_inventory  # noqa: PLC0415

    return load_legal_intent_inventory(load_lock(umbrella_lock_path()), data_root())


@dataclass(frozen=True)
class SlurpProjectionV3DeliveryResult:
    """One row's runtime delivery-transform outcome.

    ``text`` is always a value the caller may seal (the projected text when
    ``changed`` is true, otherwise BYTE-IDENTICAL to the input). ``metadata``
    is the custody record the caller attaches beside the raw text when
    ``changed`` is true; it is never used to mutate anything itself.
    """

    text: str
    changed: bool
    metadata: Mapping[str, object]


def render_slurp_answer(
    scenario: str | None, action: str | None, entities: Sequence[SlotEntity]
) -> str:
    """Canonical JSON rendering of one SLURP answer -- the SAME shape/sort
    order :func:`reproduction.slurp_scoring.parse_slu_response` parses and
    ``reproduction.ojw.native_group_solver._default_render_answer`` already
    renders, so a v3-projected answer is indistinguishable in shape from any
    other delivered SLURP answer."""

    payload = {
        "scenario": scenario,
        "action": action,
        "entities": [{"type": entity.type, "filler": entity.filler} for entity in entities],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def apply_slurp_projection_v3_delivery(
    text: str,
    *,
    carrier_lock_key: str,
    inventory: LegalIntentInventory | None = None,
) -> SlurpProjectionV3DeliveryResult:
    """Apply USE projection v3 to one delivered SLURP answer's response text.

    Fails closed on a non-SLURP carrier: this transform's one config key is
    a flat, carrier-blind run-level switch (module docstring), so it is the
    CALLER's job to gate it on carrier identity before ever reaching here;
    a call for the wrong carrier is a configuration defect, not something to
    silently ignore (mirrors ``core.driver.run``'s own refusal when
    ``obs_prefetch_depth`` is declared on a policy that cannot use it).

    An unparsed ``text`` is returned unchanged (``changed=False``): there is
    no label or filler to project, exactly as
    :func:`reproduction.slurp_scoring.parse_slu_response`'s own fail-closed
    convention already treats an unparsed response everywhere else in this
    study. ``inventory`` defaults to the real TRAIN-mined one
    (:func:`_default_legal_intent_inventory`, loaded lazily and cached);
    tests pass a small synthetic inventory instead, so this function never
    requires ``SPEECHRL_DATA_DIR`` to be tested.
    """

    if carrier_lock_key != "slurp":
        raise ValueError(
            f"{SLURP_PROJECTION_V3_DELIVERY_KEY} is only defined for the 'slurp' "
            f"carrier, got {carrier_lock_key!r}"
        )
    scenario, action, entities, parsed = parse_slu_response(text)
    if not parsed:
        return SlurpProjectionV3DeliveryResult(
            text=text,
            changed=False,
            metadata={
                "rule_id": SLURP_PROJECTION_V3_ID,
                "applied": False,
                "reason": "unparsed",
            },
        )
    if inventory is None:
        inventory = _default_legal_intent_inventory()
    outcome = apply_projection_v3(scenario, action, entities, inventory, parsed=parsed)
    new_text = render_slurp_answer(outcome.scenario, outcome.action, outcome.entities)
    changed = new_text != text
    metadata = {
        "rule_id": SLURP_PROJECTION_V3_ID,
        "applied": True,
        "label_branch": outcome.label.branch,
        "label_changed": outcome.label.changed,
        "fillers_changed": outcome.fillers_changed,
        "changed": changed,
    }
    return SlurpProjectionV3DeliveryResult(text=new_text, changed=changed, metadata=metadata)


__all__ = [
    "P2_FULL_RULES",
    "P2_RUNGS",
    "PROJECTION_BRANCH_R_ACTION",
    "RUNG_0_CASE_WHITESPACE",
    "RUNG_1_PUNCTUATION",
    "RUNG_2_MERIDIEM",
    "RUNG_3_NUMERIC",
    "SLURP_FILLER_NORMALIZATION_P2_ID",
    "SLURP_LABEL_PROJECTION_V3_ID",
    "SLURP_PROJECTION_V3_DELIVERY_KEY",
    "SLURP_PROJECTION_V3_ID",
    "ProjectionV3Outcome",
    "SlurpProjectionV3DeliveryResult",
    "apply_projection_v3",
    "apply_slurp_projection_v3_delivery",
    "normalize_entities_p2",
    "normalize_filler_p2",
    "normalize_filler_p2_full",
    "normalize_filler_p2_rung0_case_whitespace",
    "normalize_filler_p2_rung1_punctuation",
    "normalize_filler_p2_rung2_meridiem",
    "normalize_filler_p2_rung3_numeric",
    "project_slu_label_v3",
    "render_slurp_answer",
]
