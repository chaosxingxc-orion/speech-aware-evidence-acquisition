"""Per-row supply-variant interleaving at ONE node (item E42, family VAR-2).

WHY THIS EXISTS. Compare declared supply actions within a shared predecessor
state. This reduces between-flight differences in the prefix but does not
establish a statistical power multiplier: the historical ROLL-AA row-mean F1
interval and cross-flight pooled-F1 intervals use different estimands.

WHAT THE FORM IS. One node, K arms, one episode, one row: the same node is
contacted K times over the SAME ``QueryState``, each time with a DIFFERENT
declared knowledge-supply construction, and the episode delivers exactly ONE
of them. It is the grouped Solver sampler (item E2, ``rails.
native_episode_config`` / ``reproduction.ojw.native_group_solver``) with the
varied axis moved from DECODING to SUPPLY:

* E2 varies ``temperature``/``seed`` per sample at request-composition time
  (``reproduction.ojw.native_request.compose_solver_sample_decoding_params``)
  and delivers the commit policy's aggregate;
* E42 varies the SUPPLIED EVIDENCE per arm at binding-composition time and
  delivers the DELIVERING arm's own raw response.

WHY THE DELIVERING ARM CARRIES NO OVERRIDES AND COMES LAST. Two invariants
this module refuses to weaken:

1. *The delivered request is the locked plan's request, byte for byte.* The
   delivering arm is rendered from the episode's own ``QueryState``, with no
   arm-scoped view of any kind -- it is not "a narrowing that reproduces the
   plan", it IS the ordinary path, so its bytes are identical by construction
   rather than by claim. That is what makes the delivering arm the read's
   baseline and the within-flight comparator for every other arm.
2. *Invariant I7 (the delivered text is a model response) holds with no new
   exception.* The delivering arm is the LAST arm of the group, so the role
   result's ``actor_output`` IS the last contact's own completion text and
   ``rails.runner``'s existing delivery binding check ("native delivery is not
   bound to its actual source response") passes unchanged. A grouped Solver
   visit needs an explicit ``solver_group`` bypass there because its delivered
   text is an AGGREGATE; an arm group needs none.

WHAT AN ARM DOES **NOT** TOUCH. An arm may override exactly the supply
selection knobs of :data:`SUPPLY_VARIANT_KNOB_TAILS`, on its OWN node's phase,
in a store the fragment already declares. It therefore cannot reach the model
fragment, the decoding params, the serving geometry, the prompt order, the task
contract, the tool authority, the role graph, the phase program or the
response format: none of those is addressable by a knob path this module
admits, and an unknown path is refused by name before any contact.

THE ONE NAMED EXCEPTION: THE RELEASE-SWAP ROUTE. Coordinator amendment,
2026-09-28 (docs/superpowers/specs/2026-09-27-same-flight-supply-variant-
instrument-design.md, "Coordinator amendment (2026-09-28)"): an arm may
ADDITIONALLY declare :class:`SupplyVariantReleaseSwap`, naming ONE store the
fragment already declares and ONE alternate release relpath that store's base
config ALSO declares under ``knowledge_stores.<store>.alternates`` --
pinned, hash-verified bytes exactly like the primary, never a component this
module discovers on its own. This is the sole exception to "an arm re-caps a
selection, it never swaps a component or repoints a release": every other
sentence in this docstring, and every refusal below, still holds for the
knob-tail route. The delivering arm and its twin (``replicate_of``) never
carry one, for the same reason neither carries a knob override.

CUSTODY, AND THE ONE DIVERGENCE THIS FORM INTRODUCES. Every arm's request,
resolved knobs, supplied value ids and item count are sealed under the arm's
own id, and the K contacts are recorded as ONE ``AgentContactBatch`` with
``fanout_semantics="action_alternatives"`` -- so all K bind the SAME
``query_state_sha256``, exactly as the K samples of a grouped Solver visit do.
For the DELIVERING arm the sealed ``QueryState`` describes its request exactly.
For a NON-DELIVERING arm it does not: that arm's request carried its own
resolved selection, which the episode's state never claimed. That divergence is
this form's whole point, and it is made checkable rather than silent:
:func:`validate_supply_variant_receipt` requires the delivering arm's rendered
id list to equal the row's own ``retrieved_value_ids`` and every other arm's
ids to be declared, ordered and counted in its own receipt row.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .context_budget import (
    REGISTERED_SPECIAL_TOKEN_RESERVE,
    serving_bound_reserve_tokens,
)
from .errors import RailsError

#: The receipt schema one arm group seals under. Bumped to v2 by owner
#: decision 172 (2026-09-27, merge set B): v2 adds ``arm_visits`` and
#: ``visit_index`` at the block level and ``replicate_of`` on every arm row.
#: Bumped again to v3 by the coordinator amendment (2026-09-28): v3 adds
#: ``release_swap`` on every arm row -- ``None`` for the delivering arm, its
#: twin, and every arm that re-caps only a knob tail; the declared
#: ``{store_id, release}`` of the ONE store this arm repoints, otherwise.
#: ``rails.native_episode_receipt.validate_supply_variant_receipt`` still
#: accepts a v1 or v2 receipt unchanged -- no sealed VAR-2 / E42b data is
#: rewritten.
SUPPLY_VARIANT_RECEIPT_SCHEMA = "saea-supply-variant-arms-v3"

#: The two values ``supply_variants.arm_visits`` may declare. The PARSER
#: default is ``"every"`` -- every fragment written before this key existed
#: carries none at all and composes byte-identically to before -- but an
#: instrument cell (docs/superpowers/specs/2026-09-27-same-flight-supply-
#: variant-instrument-design.md section 2) must declare ``"first"``, checked
#: by ``scripts/checks/flight_registration_check.py``'s ``arm-visits-not-
#: first`` finding. Under ``"first"`` the arms fan out only at the visit
#: whose ``visit_index`` is 0; every later visit of the same node contacts
#: the delivering arm alone -- the VAR-2 fix, because the fit bound
#: (``max_supplied_items``) then covers exactly one visit rather than every
#: revision (``docs/results/2026-09-25-slurp-var2-closed-engineering-
#: failure.md``).
SUPPLY_VARIANT_ARM_VISITS_DEFAULT = "every"
SUPPLY_VARIANT_ARM_VISITS_INSTRUMENT = "first"
SUPPLY_VARIANT_ARM_VISITS_VALUES = (
    SUPPLY_VARIANT_ARM_VISITS_DEFAULT, SUPPLY_VARIANT_ARM_VISITS_INSTRUMENT,
)

#: The root key every admissible knob path starts at. A path outside it cannot
#: name a supply selection, so it is refused by name rather than applied.
SUPPLY_VARIANT_KNOB_ROOT = "knowledge_stores"

#: The two store routes an arm may re-cap, and the exact tails admitted under
#: each. Nothing else in a store entry is addressable: not ``provider``, not
#: ``rank_policy``/``fuse_policy``, not ``query_source``, not a pin, not
#: ``store_role`` -- an arm re-caps a SELECTION, it never swaps a component or
#: repoints a release.
SUPPLY_VARIANT_KNOB_TAILS: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "phase_supply": (
        ("k",),
        ("fuse_coverage", "m"),
        ("fuse_coverage", "c"),
        ("fuse_coverage", "top_l"),
    ),
    "candidate_supply": (
        ("max_candidates",),
    ),
}

#: Keys the ``supply_variants`` block carries, required.
SUPPLY_VARIANT_BLOCK_KEYS = frozenset({"arms", "fit_estimate"})
#: ``arm_visits`` (owner decision 172, merge set B): optional so every
#: fragment written before it exists parses byte-identically; see
#: :data:`SUPPLY_VARIANT_ARM_VISITS_VALUES`.
SUPPLY_VARIANT_BLOCK_OPTIONAL_KEYS = frozenset({"arm_visits"})

#: Keys one arm row carries. ``deliver`` and ``overrides`` are optional in the
#: JSON and defaulted here; ``arm_id`` and ``max_supplied_items`` are required,
#: the second because the fit refusal below is fail-closed and cannot estimate
#: an arm that declares no bound.
SUPPLY_VARIANT_ARM_REQUIRED_KEYS = frozenset({"arm_id", "max_supplied_items"})
#: ``replicate_of`` (owner decision 172, merge set B): the ONE way an arm may
#: declare NO overrides beside the delivering arm -- naming the delivering
#: arm's own id, which makes it the read's TWIN (the delivering arm's greedy
#: repeat, Q3 ruling): no overrides, exempt from the identical-override-set
#: refusal and from the receipt rule that a non-delivering arm must resolve
#: at least one knob. ``release_swap`` (coordinator amendment, 2026-09-28):
#: the arm's release-swap selection, disjoint from ``overrides`` -- see
#: :class:`SupplyVariantReleaseSwap` and :func:`parse_supply_variant_release_swap`.
SUPPLY_VARIANT_ARM_OPTIONAL_KEYS = frozenset(
    {"deliver", "overrides", "replicate_of", "release_swap"}
)

#: Keys the ``fit_estimate`` block carries, exactly. Every one is a MEASURED,
#: pinned number the fragment author reads off an already-sealed cell, never a
#: guess computed here: this module owns the arithmetic, not the inputs.
SUPPLY_VARIANT_FIT_KEYS = frozenset({
    "slot_tokens", "completion_ceiling", "base_prompt_tokens",
    "tokens_per_supplied_item",
})

#: The arm count one node may fan out to, inclusive. The upper bound is the
#: grouped sampler's own (``1 <= samples <= 8``) for the same reason: a node's
#: visits multiply the row's contact ceiling, and a bound a reader can hold in
#: their head is worth more than one more arm.
MIN_SUPPLY_VARIANT_ARMS = 2
MAX_SUPPLY_VARIANT_ARMS = 8


class SupplyVariantError(RailsError):
    """An arm, its knob path, its fit estimate or its receipt is invalid."""


def _positive_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SupplyVariantError(f"{field} must be a positive integer")
    return int(value)


def _nonempty_str(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SupplyVariantError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class SupplyVariantKnob:
    """One parsed, admitted knob path and the value an arm sets it to."""

    path: str
    store_id: str
    route: str
    phase: str
    tail: tuple[str, ...]
    value: int

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "store_id": self.store_id,
            "route": self.route,
            "phase": self.phase,
            "tail": list(self.tail),
            "value": self.value,
        }


@dataclass(frozen=True)
class SupplyVariantReleaseSwap:
    """One arm's selection of an ALTERNATIVE pinned release+snapshot for ONE
    store the base config also declares (coordinator amendment, 2026-09-28,
    docs/superpowers/specs/2026-09-27-same-flight-supply-variant-instrument-
    design.md, "Coordinator amendment (2026-09-28)").

    Unlike every :class:`SupplyVariantKnob`, this does not re-cap a SELECTION
    over the base's own released stores -- it repoints which release the
    arm's own router loads for the named store, to one the base ALSO pins and
    declares by name under ``knowledge_stores.<store>.alternates``. The
    delivering arm and its twin never carry one.
    """

    store_id: str
    release_relpath: str

    def as_json(self) -> dict[str, object]:
        return {"store_id": self.store_id, "release": self.release_relpath}


@dataclass(frozen=True)
class SupplyVariantArm:
    """One arm of one node's supply-variant group."""

    arm_id: str
    deliver: bool
    knobs: tuple[SupplyVariantKnob, ...]
    max_supplied_items: int
    # Owner decision 172 (2026-09-27, merge set B): the delivering arm's id,
    # naming this arm as its TWIN -- no overrides, resolving exactly the
    # delivering arm's ids -- or ``None`` for every arm parsed before this
    # field existed and for every ordinary (non-twin) arm. Declared LAST, so
    # every arm parsed before this field existed composes byte-identically.
    replicate_of: str | None = None
    # Coordinator amendment, 2026-09-28: this arm's release-swap selection, or
    # ``None`` for every arm parsed before the route existed and for every arm
    # that re-caps only a knob tail. Declared LAST, so every arm parsed before
    # this field existed composes byte-identically.
    release_swap: SupplyVariantReleaseSwap | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "deliver": self.deliver,
            "overrides": {knob.path: knob.value for knob in self.knobs},
            "knobs": [knob.as_json() for knob in self.knobs],
            "max_supplied_items": self.max_supplied_items,
            "replicate_of": self.replicate_of,
            "release_swap": None if self.release_swap is None else self.release_swap.as_json(),
        }


@dataclass(frozen=True)
class SupplyVariantFitEstimate:
    """The pinned, measured inputs of the fail-closed prompt-fit refusal."""

    slot_tokens: int
    completion_ceiling: int
    base_prompt_tokens: int
    tokens_per_supplied_item: int

    @property
    def reserve_tokens(self) -> int:
        """The operational reserve the live slot binds (item E33's rule)."""

        return serving_bound_reserve_tokens(self.slot_tokens)

    @property
    def prompt_limit_tokens(self) -> int:
        """What one arm's PROMPT may occupy under this estimate.

        The same arithmetic ``rails.native_episode_config.ContextFitBudget.
        prompt_limit_tokens`` applies to a REALISED request, applied here to an
        estimate: the live slot minus the operational reserve, the completion
        ceiling and the registered special-token reserve.
        """

        return (
            self.slot_tokens
            - self.reserve_tokens
            - self.completion_ceiling
            - REGISTERED_SPECIAL_TOKEN_RESERVE
        )

    def estimated_prompt_tokens(self, arm: SupplyVariantArm) -> int:
        """This arm's estimated prompt, at its own declared item bound."""

        return (
            self.base_prompt_tokens
            + arm.max_supplied_items * self.tokens_per_supplied_item
        )

    def as_json(self) -> dict[str, object]:
        return {
            "slot_tokens": self.slot_tokens,
            "completion_ceiling": self.completion_ceiling,
            "base_prompt_tokens": self.base_prompt_tokens,
            "tokens_per_supplied_item": self.tokens_per_supplied_item,
            "reserve_tokens": self.reserve_tokens,
            "prompt_limit_tokens": self.prompt_limit_tokens,
        }


@dataclass(frozen=True)
class SupplyVariantGroup:
    """One node's whole arm group: the arms, in order, and its fit estimate."""

    arms: tuple[SupplyVariantArm, ...]
    fit_estimate: SupplyVariantFitEstimate
    # Owner decision 172 (2026-09-27, merge set B): "every" (every visit fans
    # out -- the pre-existing and still-default behaviour) or "first" (only
    # the visit whose visit_index is 0 fans out; every later visit contacts
    # the delivering arm alone). Declared LAST, so every group parsed before
    # this field existed composes to "every" byte-identically.
    arm_visits: str = SUPPLY_VARIANT_ARM_VISITS_DEFAULT

    @property
    def arm_count(self) -> int:
        return len(self.arms)

    @property
    def arm_ids(self) -> tuple[str, ...]:
        return tuple(arm.arm_id for arm in self.arms)

    @property
    def delivered_arm(self) -> SupplyVariantArm:
        return self.arms[-1]

    def arm(self, arm_id: str) -> SupplyVariantArm:
        for arm in self.arms:
            if arm.arm_id == arm_id:
                return arm
        raise SupplyVariantError(f"unknown supply-variant arm {arm_id!r}")

    def arm_at(self, index: int) -> SupplyVariantArm:
        if isinstance(index, bool) or not isinstance(index, int) or not (
            0 <= index < len(self.arms)
        ):
            raise SupplyVariantError(
                "supply-variant arm index is outside the declared group"
            )
        return self.arms[index]

    def as_json(self) -> dict[str, object]:
        return {
            "arms": [arm.as_json() for arm in self.arms],
            "fit_estimate": self.fit_estimate.as_json(),
            "arm_visits": self.arm_visits,
        }


def parse_supply_variant_knob(
    path: object,
    value: object,
    *,
    phase_id: str,
    first_phase_id: str,
    declared_stores: Sequence[str] | None = None,
) -> SupplyVariantKnob:
    """Parse ONE ``overrides`` entry, refusing everything it does not admit.

    ``phase_id`` is the arm group's own node phase: a knob on any other phase
    would change what a DIFFERENT node reads, which is not this arm's variable.
    ``first_phase_id`` is the program's first phase, refused outright -- a
    first-phase selection is computed before the flight and seeded into each
    row's ONE initial ``QueryState`` (``core.flight.runtime.
    _resolve_phase_supply``, "a first phase has no preceding advance"), so it
    cannot differ between two arms of the same row however the request is
    composed.
    """

    text = _nonempty_str(path, field="supply_variants arm overrides key")
    segments = text.split(".")
    if len(segments) < 5 or segments[0] != SUPPLY_VARIANT_KNOB_ROOT:
        raise SupplyVariantError(
            f"supply-variant override {text!r} is not a knob path; an arm may "
            f"override only {SUPPLY_VARIANT_KNOB_ROOT}.<store>.<route>.<phase>"
            ".<knob>"
        )
    store_id, route, phase = segments[1], segments[2], segments[3]
    tail = tuple(segments[4:])
    if not store_id or not phase:
        raise SupplyVariantError(
            f"supply-variant override {text!r} names an empty store or phase"
        )
    if route not in SUPPLY_VARIANT_KNOB_TAILS:
        raise SupplyVariantError(
            f"supply-variant override {text!r} names route {route!r}; an arm "
            f"may re-cap only {sorted(SUPPLY_VARIANT_KNOB_TAILS)}"
        )
    if tail not in SUPPLY_VARIANT_KNOB_TAILS[route]:
        admitted = sorted(
            ".".join(item) for item in SUPPLY_VARIANT_KNOB_TAILS[route]
        )
        raise SupplyVariantError(
            f"supply-variant override {text!r} names knob {'.'.join(tail)!r}, "
            f"which {route!r} does not admit; the admitted knobs are {admitted}"
        )
    if phase == first_phase_id:
        raise SupplyVariantError(
            f"supply-variant override {text!r} names the program's FIRST phase "
            f"{first_phase_id!r}, whose selection is computed before the flight "
            "and seeded into each row's one initial QueryState; it cannot "
            "differ between two arms of the same row"
        )
    if phase != phase_id:
        raise SupplyVariantError(
            f"supply-variant override {text!r} names phase {phase!r}, but this "
            f"arm group runs at {phase_id!r}; an arm may only re-cap the supply "
            "of its own node"
        )
    if declared_stores is not None and store_id not in set(declared_stores):
        raise SupplyVariantError(
            f"supply-variant override {text!r} names store {store_id!r}, which "
            f"this configuration does not declare; declared stores are "
            f"{sorted(set(declared_stores))}"
        )
    return SupplyVariantKnob(
        path=text,
        store_id=store_id,
        route=route,
        phase=phase,
        tail=tail,
        value=_positive_int(value, field=f"supply-variant override {text!r}"),
    )


def parse_supply_variant_release_swap(
    block: object,
    *,
    declared_stores: Sequence[str] | None = None,
    declared_alternate_relpaths: Mapping[str, Sequence[str]] | None = None,
) -> SupplyVariantReleaseSwap:
    """Parse ONE ``arms[i].release_swap`` entry, refusing everything it does
    not admit (coordinator amendment, 2026-09-28).

    ``declared_stores`` is the same set :func:`parse_supply_variant_knob`
    checks a knob's store against. ``declared_alternate_relpaths`` is
    ``{store_id: (admitted alternate release relpath, ...)}``
    (``rails.knowledge_stores.declared_alternate_release_relpaths``); an arm
    may never name a release absent from it, refused by name -- the base's
    OWN pin verification (``rails.knowledge_stores.load_knowledge_store_
    binding``) still runs when the swap is actually resolved, so this is a
    by-name pre-check, not the hash proof.
    """

    if not isinstance(block, Mapping) or set(block) != {"store_id", "release"}:
        raise SupplyVariantError(
            "supply_variants arm release_swap must be an object with exactly "
            "store_id and release"
        )
    store_id = _nonempty_str(block["store_id"], field="release_swap.store_id")
    release_relpath = _nonempty_str(block["release"], field="release_swap.release")
    if declared_stores is not None and store_id not in set(declared_stores):
        raise SupplyVariantError(
            f"supply-variant release_swap names store {store_id!r}, which this "
            f"configuration does not declare; declared stores are "
            f"{sorted(set(declared_stores))}"
        )
    if declared_alternate_relpaths is not None:
        admitted = tuple(declared_alternate_relpaths.get(store_id, ()))
        if release_relpath not in admitted:
            raise SupplyVariantError(
                f"supply-variant release_swap names release {release_relpath!r} "
                f"for store {store_id!r}, which is absent from its declared "
                f"alternates {sorted(admitted)}"
            )
    return SupplyVariantReleaseSwap(store_id=store_id, release_relpath=release_relpath)


def parse_supply_variant_fit_estimate(block: object) -> SupplyVariantFitEstimate:
    """Parse the fail-closed prompt-fit estimate, exactly."""

    if not isinstance(block, Mapping) or set(block) != set(
        SUPPLY_VARIANT_FIT_KEYS
    ):
        raise SupplyVariantError(
            "supply_variants.fit_estimate must carry exactly "
            f"{sorted(SUPPLY_VARIANT_FIT_KEYS)}"
        )
    estimate = SupplyVariantFitEstimate(
        slot_tokens=_positive_int(
            block["slot_tokens"], field="fit_estimate.slot_tokens"
        ),
        completion_ceiling=_positive_int(
            block["completion_ceiling"], field="fit_estimate.completion_ceiling"
        ),
        base_prompt_tokens=_positive_int(
            block["base_prompt_tokens"], field="fit_estimate.base_prompt_tokens"
        ),
        tokens_per_supplied_item=_positive_int(
            block["tokens_per_supplied_item"],
            field="fit_estimate.tokens_per_supplied_item",
        ),
    )
    if estimate.prompt_limit_tokens < 1:
        raise SupplyVariantError(
            "supply_variants.fit_estimate leaves no room for a prompt: "
            f"slot {estimate.slot_tokens} - reserve {estimate.reserve_tokens} - "
            f"completion {estimate.completion_ceiling} - special "
            f"{REGISTERED_SPECIAL_TOKEN_RESERVE} is not positive"
        )
    return estimate


def parse_supply_variants(
    block: object,
    *,
    phase_id: str,
    first_phase_id: str,
    declared_stores: Sequence[str] | None = None,
    declared_alternate_relpaths: Mapping[str, Sequence[str]] | None = None,
) -> SupplyVariantGroup:
    """Parse ``roles.<role>.supply_variants``, fail-closed.

    The refusals, in order, each raised by name BEFORE any contact:

    1. a block that is not an object with exactly ``arms`` and
       ``fit_estimate``, or an ``arms`` value that is not an ordered list;
    2. an arm count outside :data:`MIN_SUPPLY_VARIANT_ARMS` ..
       :data:`MAX_SUPPLY_VARIANT_ARMS` (one arm is a second spelling of no
       arms at all);
    3. an arm row with unknown or missing keys;
    4. an arm id collision;
    5. zero or several arms carrying ``deliver``;
    6. a delivering arm that is not the LAST arm, or that carries overrides or
       a release_swap;
    7. an override path this module does not admit -- unknown root, unknown
       route, unknown knob, an undeclared store, the program's first phase, or
       another node's phase (:func:`parse_supply_variant_knob`);
    8. two arms whose whole override set (knobs plus any release_swap) is
       identical (two spellings of one arm cost a contact per row and measure
       nothing);
    9. an arm whose estimated prompt exceeds the live slot with the registered
       reserve;
    10. a release_swap naming an undeclared store, or a release absent from
        that store's declared ``alternates`` (:func:`parse_supply_variant_
        release_swap`), or declared beside ``replicate_of``.
    """

    if (
        not isinstance(block, Mapping)
        or not SUPPLY_VARIANT_BLOCK_KEYS <= set(block)
        or set(block) - SUPPLY_VARIANT_BLOCK_KEYS - SUPPLY_VARIANT_BLOCK_OPTIONAL_KEYS
    ):
        raise SupplyVariantError(
            "roles.<role>.supply_variants must be an object with exactly "
            f"{sorted(SUPPLY_VARIANT_BLOCK_KEYS)} plus optional "
            f"{sorted(SUPPLY_VARIANT_BLOCK_OPTIONAL_KEYS)}"
        )
    arm_visits = block.get("arm_visits", SUPPLY_VARIANT_ARM_VISITS_DEFAULT)
    if arm_visits not in SUPPLY_VARIANT_ARM_VISITS_VALUES:
        raise SupplyVariantError(
            "supply_variants.arm_visits must be one of "
            f"{SUPPLY_VARIANT_ARM_VISITS_VALUES}, got {arm_visits!r}"
        )
    rows = block["arms"]
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise SupplyVariantError(
            "supply_variants.arms must be an ordered list of arm objects"
        )
    if not MIN_SUPPLY_VARIANT_ARMS <= len(rows) <= MAX_SUPPLY_VARIANT_ARMS:
        raise SupplyVariantError(
            "supply_variants.arms must declare between "
            f"{MIN_SUPPLY_VARIANT_ARMS} and {MAX_SUPPLY_VARIANT_ARMS} arms"
        )
    fit_estimate = parse_supply_variant_fit_estimate(block["fit_estimate"])
    arms: list[SupplyVariantArm] = []
    for position, row in enumerate(rows):
        keys = set(row)
        if (
            not SUPPLY_VARIANT_ARM_REQUIRED_KEYS <= keys
            or keys - SUPPLY_VARIANT_ARM_REQUIRED_KEYS
            - SUPPLY_VARIANT_ARM_OPTIONAL_KEYS
        ):
            raise SupplyVariantError(
                f"supply_variants.arms[{position}] must carry exactly "
                f"{sorted(SUPPLY_VARIANT_ARM_REQUIRED_KEYS)} plus optional "
                f"{sorted(SUPPLY_VARIANT_ARM_OPTIONAL_KEYS)}"
            )
        arm_id = _nonempty_str(
            row["arm_id"], field=f"supply_variants.arms[{position}].arm_id"
        )
        deliver = row.get("deliver", False)
        if not isinstance(deliver, bool):
            raise SupplyVariantError(
                f"supply_variants.arms[{position}].deliver must be a bool"
            )
        overrides = row.get("overrides", {})
        if not isinstance(overrides, Mapping):
            raise SupplyVariantError(
                f"supply_variants.arms[{position}].overrides must be an object"
            )
        raw_replicate_of = row.get("replicate_of")
        if raw_replicate_of is not None:
            replicate_of = _nonempty_str(
                raw_replicate_of,
                field=f"supply_variants.arms[{position}].replicate_of",
            )
        else:
            replicate_of = None
        if deliver and replicate_of is not None:
            raise SupplyVariantError(
                f"supply_variants.arms[{position}] declares both deliver: true "
                "and replicate_of; the delivering arm cannot also be a twin"
            )
        knobs = tuple(
            parse_supply_variant_knob(
                path, value, phase_id=phase_id, first_phase_id=first_phase_id,
                declared_stores=declared_stores,
            )
            for path, value in sorted(overrides.items())
        )
        if replicate_of is not None and knobs:
            raise SupplyVariantError(
                f"supply_variants.arms[{position}] names replicate_of and must "
                "declare no overrides: it resolves exactly the delivering "
                "arm's ids"
            )
        raw_release_swap = row.get("release_swap")
        if raw_release_swap is not None:
            release_swap = parse_supply_variant_release_swap(
                raw_release_swap, declared_stores=declared_stores,
                declared_alternate_relpaths=declared_alternate_relpaths,
            )
        else:
            release_swap = None
        if replicate_of is not None and release_swap is not None:
            raise SupplyVariantError(
                f"supply_variants.arms[{position}] names replicate_of and must "
                "declare no release_swap: it resolves exactly the delivering "
                "arm's ids"
            )
        arms.append(SupplyVariantArm(
            arm_id=arm_id,
            deliver=deliver,
            knobs=knobs,
            max_supplied_items=_positive_int(
                row["max_supplied_items"],
                field=f"supply_variants.arms[{position}].max_supplied_items",
            ),
            replicate_of=replicate_of,
            release_swap=release_swap,
        ))
    ids = [arm.arm_id for arm in arms]
    if len(set(ids)) != len(ids):
        raise SupplyVariantError("supply_variants arm ids must be distinct")
    delivering = [arm.arm_id for arm in arms if arm.deliver]
    if len(delivering) != 1:
        raise SupplyVariantError(
            "supply_variants must declare exactly one arm with deliver: true; "
            f"this block declares {len(delivering)}"
        )
    if not arms[-1].deliver:
        raise SupplyVariantError(
            f"supply_variants delivering arm {delivering[0]!r} must be the LAST "
            "arm: the delivered text is then the group's final contact's own "
            "response, so invariant I7 holds with no new exception"
        )
    if arms[-1].knobs:
        raise SupplyVariantError(
            f"supply_variants delivering arm {arms[-1].arm_id!r} must declare no "
            "overrides: it is rendered from the episode's own QueryState, which "
            "is what makes its request bytes the locked plan's by construction "
            "rather than by claim"
        )
    if arms[-1].release_swap is not None:
        raise SupplyVariantError(
            f"supply_variants delivering arm {arms[-1].arm_id!r} must declare no "
            "release_swap: it is rendered from the episode's own QueryState "
            "over the base's own released stores"
        )
    delivered_arm_id = arms[-1].arm_id
    for arm in arms:
        if arm.replicate_of is not None and arm.replicate_of != delivered_arm_id:
            raise SupplyVariantError(
                f"supply_variants arm {arm.arm_id!r} names replicate_of "
                f"{arm.replicate_of!r}, which is not the delivering arm "
                f"{delivered_arm_id!r}"
            )
    signatures = [
        (
            tuple((knob.path, knob.value) for knob in arm.knobs),
            None if arm.release_swap is None else (
                arm.release_swap.store_id, arm.release_swap.release_relpath,
            ),
        )
        for arm in arms
        if arm.replicate_of is None
    ]
    if len(set(signatures)) != len(signatures):
        raise SupplyVariantError(
            "two supply_variants arms declare the same overrides; two spellings "
            "of one construction spend a contact per row and measure nothing"
        )
    for arm in arms:
        estimated = fit_estimate.estimated_prompt_tokens(arm)
        if estimated > fit_estimate.prompt_limit_tokens:
            raise SupplyVariantError(
                f"supply_variants arm {arm.arm_id!r} estimates {estimated} prompt "
                f"tokens at {arm.max_supplied_items} supplied items, which "
                f"exceeds the {fit_estimate.prompt_limit_tokens}-token limit of a "
                f"{fit_estimate.slot_tokens}-token slot with its registered "
                f"{fit_estimate.reserve_tokens}-token reserve, the "
                f"{fit_estimate.completion_ceiling}-token completion ceiling and "
                f"the {REGISTERED_SPECIAL_TOKEN_RESERVE}-token special reserve"
            )
    return SupplyVariantGroup(
        arms=tuple(arms), fit_estimate=fit_estimate, arm_visits=arm_visits,
    )


def accumulate_arm_selection(
    previous: Sequence[str], resolved: Sequence[str],
) -> tuple[str, ...]:
    """Retain this arm's supply across visits while appending only new ids.

    Routers may return an unseen increment or a repeated full selection.
    Both describe a monotone acquisition history, as the ordinary QueryState
    does. Repeated ids across visits are retained once; duplicates within a
    single resolution remain a malformed decision and are refused.
    """

    prior, current = tuple(previous), tuple(resolved)
    for name, ids in (("previous", prior), ("resolved", current)):
        if len(set(ids)) != len(ids):
            raise SupplyVariantError(f"{name} supply-variant selection must be unique")
        for value_id in ids:
            _nonempty_str(value_id, field=f"{name} supply-variant value id")
    visible = set(prior)
    return prior + tuple(value_id for value_id in current if value_id not in visible)


def arm_supplied_value_ids(
    *,
    retrieved_value_ids: Sequence[str],
    node_acquired_value_ids: Sequence[str],
    arm_selected_value_ids: Sequence[str],
) -> tuple[str, ...]:
    """The ordered value ids ONE non-delivering arm's request renders.

    The row's accumulated ``retrieved_value_ids`` hold every earlier phase's
    values plus everything THIS node's own supply steps acquired (the successor
    state is ``context.query_state.retrieved_value_ids + new_value_ids``,
    ``rails.controllers``). An arm keeps the PREFIX -- what the earlier phases
    supplied is not its variable -- and replaces this node's own contribution
    with its own resolved selection.

    ``node_acquired_value_ids`` is the CUMULATIVE set this node's supply steps
    have acquired on this row, not just the latest increment: with
    ``max_revisions >= 1`` the Planner's REVISE re-enters the node, and
    ``rails.controllers.restrict_repeat_visit_supply`` then returns only what is
    not yet visible, so the node's own contribution is spread over two steps.
    Removing the cumulative set is what makes an arm's rendering identical on a
    first visit and on a revisit, which is what makes its per-row comparison to
    the delivering arm read as one construction rather than two.

    Refuses, by name: an acquired id the accumulated state does not carry
    (the caller's bookkeeping and the episode's state disagree), a non-unique
    arm selection, and an arm selection that re-supplies a value the prefix
    already made visible.
    """

    accumulated = tuple(retrieved_value_ids)
    acquired = set(node_acquired_value_ids)
    selection = tuple(arm_selected_value_ids)
    missing = sorted(acquired - set(accumulated))
    if missing:
        raise SupplyVariantError(
            "this node is recorded as having acquired value(s) the row's "
            f"accumulated retrieved_value_ids do not carry: {missing}; an arm "
            "cannot be rendered against a state whose supply steps it cannot "
            "locate"
        )
    prefix = tuple(
        value_id for value_id in accumulated if value_id not in acquired
    )
    if len(set(selection)) != len(selection):
        raise SupplyVariantError("a supply-variant arm selection must be unique")
    overlap = sorted(set(selection) & set(prefix))
    if overlap:
        raise SupplyVariantError(
            "a supply-variant arm selection re-supplies value(s) an earlier "
            f"phase already made visible: {overlap}"
        )
    return prefix + selection


def supply_variant_arm_record(
    *,
    arm: SupplyVariantArm,
    arm_index: int,
    contact_id: str,
    supplied_value_ids: Sequence[str],
    resolved_knobs: Mapping[str, int] | None = None,
) -> dict[str, object]:
    """One arm's receipt row: labels, ids and counts, never supplied text."""

    ids = tuple(supplied_value_ids)
    if len(set(ids)) != len(ids):
        raise SupplyVariantError("a supply-variant arm record must have unique ids")
    if len(ids) > arm.max_supplied_items:
        raise SupplyVariantError(
            f"supply-variant arm {arm.arm_id!r} supplied {len(ids)} items, above "
            f"its declared max_supplied_items {arm.max_supplied_items}; the "
            "fit refusal was computed against that bound"
        )
    declared = {knob.path: knob.value for knob in arm.knobs}
    resolved = dict(declared if resolved_knobs is None else resolved_knobs)
    if resolved != declared:
        raise SupplyVariantError(
            f"supply-variant arm {arm.arm_id!r} resolved knobs {sorted(resolved)} "
            f"differ from the knobs it declared {sorted(declared)}"
        )
    return {
        "arm_index": int(arm_index),
        "arm_id": arm.arm_id,
        "deliver": bool(arm.deliver),
        "replicate_of": arm.replicate_of,
        # Coordinator amendment, 2026-09-28: which release this arm actually
        # consumed -- ``None`` absent a release-swap route, the declared
        # {store_id, release} otherwise. This is the DECLARED selection
        # (exactly as ``resolved_knobs`` below records ``arm.knobs``, not a
        # live re-verification): ``core.flight.runtime.FlightRuntime.
        # _supply_action_router`` already refuses, before any contact, an
        # arm whose release_swap does not resolve to the base's own declared
        # alternate.
        "release_swap": None if arm.release_swap is None else arm.release_swap.as_json(),
        "contact_id": _nonempty_str(
            contact_id, field=f"supply-variant arm {arm.arm_id!r} contact_id"
        ),
        # An ORDERED LIST of {path, value}, not a mapping keyed by the dotted
        # path. Not cosmetic: this record travels the framework's own node
        # result, and the installed workflow engine UNFLATTENS a mapping whose
        # keys contain dots -- ``{"a.b.c": 1}`` arrives as
        # ``{"a": {"b": {"c": 1}}}``, which silently destroys the one thing
        # this row exists to state. A list of objects survives any such
        # transport unchanged.
        "resolved_knobs": [
            {"path": path, "value": int(value)}
            for path, value in sorted(resolved.items())
        ],
        "supplied_value_ids": list(ids),
        "supplied_item_count": len(ids),
        "max_supplied_items": arm.max_supplied_items,
    }


def supply_variant_receipt(
    *,
    group: SupplyVariantGroup,
    phase_id: str,
    records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """The whole arm group's receipt, as the delivered role result carries it.

    Sealed from the FIRST Solver visit only (``visit_index`` 0). Under
    ``arm_visits: "first"`` every later visit contacts the delivering arm
    alone and calls neither this function nor :func:`supply_variant_arm_record`
    at all (``reproduction.ojw.native_supply_variants.SupplyVariantRoleNode``);
    ``reproduction.ojw.native_episode._ApplyRole`` carries this visit's own
    receipt forward so a later visit's plain result never erases it. Under the
    default ``"every"`` every visit still calls this, and -- exactly as before
    this key existed -- the LAST one is the one whose result survives to
    delivery.
    """

    return {
        "schema": SUPPLY_VARIANT_RECEIPT_SCHEMA,
        "phase_id": _nonempty_str(
            phase_id, field="supply_variant_receipt.phase_id"
        ),
        "arm_count": group.arm_count,
        "delivered_arm_id": group.delivered_arm.arm_id,
        "arm_visits": group.arm_visits,
        "visit_index": 0,
        "fit_estimate": group.fit_estimate.as_json(),
        "arms": [dict(record) for record in records],
    }


#: Same-flight instrument, PHASE 2 (item merge set C, design
#: docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-
#: variants-design.md): an episode-level fork at the Perception phase. This is
#: NOT another arm group at the Solver's own visit -- it is a K-way fork of
#: the FIRST phase itself, which is exactly the thing the ordinary Solver arm
#: route (above) refuses by name (refusal 7): a first-phase selection is
#: otherwise seeded once into the row's one initial QueryState, and a
#: Perception branch resolves its own PRE-FLIGHT seed instead
#: (``core.flight.runtime.FlightRuntime._supply_action_router``), never a
#: per-row rendering over the episode's own state.
#:
#: The receipt schema one Perception branch group seals under
#: ``perception_branches``.
PERCEPTION_BRANCH_RECEIPT_SCHEMA = "saea-perception-branch-arms-v1"

#: Perception has exactly one visit per row (``max_iterations`` 1, no
#: refresh, design section 3 "Branch visits"): the fan-out is always at that
#: one visit, so unlike ``supply_variants.arm_visits`` there is no "every" to
#: choose -- this is a fixed receipt constant, not a config knob.
PERCEPTION_BRANCH_VISITS = "first"

#: The two levels a Perception branch group may declare (design section 1,
#: "Two levels"): level 1 seals the branch's NOTE only; level 2 additionally
#: fans one Solver contact per non-A branch at the Solver's first visit.
PERCEPTION_BRANCH_LEVEL_NOTE = 1
PERCEPTION_BRANCH_LEVEL_SOLVER = 2
PERCEPTION_BRANCH_LEVELS = (
    PERCEPTION_BRANCH_LEVEL_NOTE, PERCEPTION_BRANCH_LEVEL_SOLVER,
)

#: The ONE route a Perception branch's boundary-supply knob may re-cap
#: (design section 3, "boundary supply knob"): the program's FIRST phase's own
#: ``phase_supply`` block. ``rank_weights.w_cos|w_prior|w_agree`` is admitted
#: ONLY on this route -- ``SUPPLY_VARIANT_KNOB_TAILS`` (the ordinary Solver
#: arm route) does not carry it (design section 3: "The rank_weights.* tail
#: is admitted only on this branch route").
PERCEPTION_BRANCH_KNOB_ROUTE = "phase_supply"
PERCEPTION_BRANCH_KNOB_TAILS: tuple[tuple[str, ...], ...] = (
    ("k",),
    ("fuse_coverage", "m"),
    ("fuse_coverage", "c"),
    ("fuse_coverage", "top_l"),
    ("rank_weights", "w_cos"),
    ("rank_weights", "w_prior"),
    ("rank_weights", "w_agree"),
)

#: Keys the ``perception_branches`` (``native_episode.roles.perception.
#: branches``) block carries, required exactly.
PERCEPTION_BRANCH_BLOCK_KEYS = frozenset({"branches", "fit_estimate", "level"})
#: Keys one branch row carries. ``branch_id`` and ``max_supplied_items`` are
#: required; every other key is one of the four closed axis categories a
#: non-A, non-T branch declares exactly one of (design section 1, "one factor
#: per non-A branch").
PERCEPTION_BRANCH_REQUIRED_KEYS = frozenset({"branch_id", "max_supplied_items"})
#: ``prepared_seed`` is NOT one of the four axis categories (it names no
#: knob, swap, presentation or contract bound): it is a B branch's own
#: offline-pinned seed artifact, optional at parse time and required only by
#: the ``branch-seed-unpinned`` registration gate.
PERCEPTION_BRANCH_OPTIONAL_KEYS = frozenset({
    "deliver", "overrides", "replicate_of", "release_swap",
    "presentation_id", "min_candidates", "prepared_seed",
})

#: K counts A and T (design section 1): at least A plus its required twin T,
#: at most A + T + :data:`MAX_PERCEPTION_B_BRANCHES` B branches. The upper
#: bound on K equals :data:`MAX_SUPPLY_VARIANT_ARMS`, for the same "a bound a
#: reader can hold in their head" reason.
MIN_PERCEPTION_BRANCHES = 2
MAX_PERCEPTION_BRANCHES = 8
#: "B.. (at most 6)" (design section 1): the branches beside A and T.
MAX_PERCEPTION_B_BRANCHES = 6

#: The four fields one receipt row carries beside the phase-1-shaped ones
#: (design section 3, "Receipt"): a branch's own note custody. Level 2 adds
#: the Solver-column custody fields.
PERCEPTION_BRANCH_RECORD_KEYS = frozenset({
    "branch_index", "branch_id", "deliver", "replicate_of", "resolved_knobs",
    "release_swap", "presentation_id", "min_candidates", "supplied_value_ids",
    "supplied_count", "max_supplied_items", "contact_id", "request_sha256",
    "response_text_sha256", "note_sha256", "note_parse_status",
    "candidate_intent_ids",
})
PERCEPTION_BRANCH_LEVEL2_RECORD_KEYS = PERCEPTION_BRANCH_RECORD_KEYS | frozenset({
    "solver_contact_id", "solver_request_sha256", "solver_response_text_sha256",
    "candidate_supply_value_ids",
})


class PerceptionBranchError(SupplyVariantError):
    """One Perception branch, its axis, its group or its receipt is invalid."""


def _rank_weight_value(value: object, *, field: str) -> float:
    """A rank_weights knob's value: a non-negative, finite real number.

    Unlike a count knob (``k``, ``fuse_coverage.*``), a weight may legitimately
    be 0.0 -- design section 6's optional branch C reads the agreement term by
    setting exactly ``w_agree`` to 0.0 -- so :func:`_positive_int` does not
    apply here.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SupplyVariantError(f"{field} must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise SupplyVariantError(f"{field} must be a non-negative, finite number")
    return number


def _sha256_hex(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PerceptionBranchError(f"{field} must be a lowercase 64-hex SHA-256")
    return value


@dataclass(frozen=True)
class PerceptionBranchKnob:
    """One parsed, admitted boundary-supply knob path a branch re-caps.

    Structurally :class:`SupplyVariantKnob`'s twin, over the DIFFERENT
    admitted route (:data:`PERCEPTION_BRANCH_KNOB_TAILS`, which -- unlike
    ``SUPPLY_VARIANT_KNOB_TAILS`` -- both TARGETS the program's first phase
    and admits ``rank_weights``), and its own type so the two knob families
    can never be silently interchanged by a caller.
    """

    path: str
    store_id: str
    phase: str
    tail: tuple[str, ...]
    #: An int for a count knob (``k``, ``fuse_coverage.*``); a float for a
    #: rank_weights knob, which may legitimately be 0.0 (design section 6's
    #: optional branch C: "w_agree 0.0").
    value: int | float

    def as_json(self) -> dict[str, object]:
        return {
            "path": self.path,
            "store_id": self.store_id,
            "phase": self.phase,
            "tail": list(self.tail),
            "value": self.value,
        }


@dataclass(frozen=True)
class PerceptionBranch:
    """One branch of one row's Perception-phase fork (design section 1).

    ``deliver`` marks branch A (last, override-free, the cell's own request,
    continues through Solver/Reviewer/Planner exactly as today).
    ``replicate_of`` (naming A) marks the required twin T (repeats A's
    request byte for byte in the same batch). Every other branch is a B
    branch: Perception ONLY, its note sealed as a column, declaring exactly
    one of the four closed axis categories below.
    """

    branch_id: str
    deliver: bool
    knobs: tuple[PerceptionBranchKnob, ...]
    max_supplied_items: int
    replicate_of: str | None = None
    release_swap: SupplyVariantReleaseSwap | None = None
    presentation_id: str | None = None
    min_candidates: int | None = None
    # Design section 5 ("Changes and merge set C"): a B branch's own
    # PRE-FLIGHT seed (``core.flight.runtime.FlightRuntime.
    # _perception_branch_seeds``), pinned as ``{relpath, sha256}`` by this
    # program's own offline preparation step -- the same shape
    # ``prepared_phase_supply`` pins the cell's own first-phase seed with.
    # ``None`` for A and T (whose seed is the cell's own prepared_phase_
    # supply, or A's, never a branch-owned artifact) and for every B branch
    # this preparation step has not yet pinned; the ``branch-seed-unpinned``
    # gate finding (``scripts/checks/flight_registration_check.py``) is what
    # refuses a REGISTERED same-flight-perception-variant cell with a B
    # branch that still carries ``None`` here.
    prepared_seed: Mapping[str, str] | None = None

    @property
    def is_twin(self) -> bool:
        return self.replicate_of is not None

    @property
    def is_b(self) -> bool:
        return not self.deliver and self.replicate_of is None

    def as_json(self) -> dict[str, object]:
        return {
            "branch_id": self.branch_id,
            "deliver": self.deliver,
            "overrides": {knob.path: knob.value for knob in self.knobs},
            "knobs": [knob.as_json() for knob in self.knobs],
            "max_supplied_items": self.max_supplied_items,
            "replicate_of": self.replicate_of,
            "release_swap": (
                None if self.release_swap is None else self.release_swap.as_json()
            ),
            "presentation_id": self.presentation_id,
            "min_candidates": self.min_candidates,
            "prepared_seed": (
                None if self.prepared_seed is None else dict(self.prepared_seed)
            ),
        }


@dataclass(frozen=True)
class PerceptionBranchGroup:
    """One row's whole Perception branch group: branches in A-last order."""

    branches: tuple[PerceptionBranch, ...]
    fit_estimate: SupplyVariantFitEstimate
    level: int

    @property
    def branch_count(self) -> int:
        return len(self.branches)

    @property
    def branch_ids(self) -> tuple[str, ...]:
        return tuple(branch.branch_id for branch in self.branches)

    @property
    def delivering_branch(self) -> PerceptionBranch:
        return self.branches[-1]

    @property
    def twin_branch(self) -> PerceptionBranch:
        for branch in self.branches:
            if branch.is_twin:
                return branch
        raise PerceptionBranchError("perception branch group has no twin (T) branch")

    def branch(self, branch_id: str) -> PerceptionBranch:
        for branch in self.branches:
            if branch.branch_id == branch_id:
                return branch
        raise PerceptionBranchError(f"unknown perception branch {branch_id!r}")

    def branch_at(self, index: int) -> PerceptionBranch:
        if isinstance(index, bool) or not isinstance(index, int) or not (
            0 <= index < len(self.branches)
        ):
            raise PerceptionBranchError(
                "perception branch index is outside the declared group"
            )
        return self.branches[index]

    def as_json(self) -> dict[str, object]:
        return {
            "branches": [branch.as_json() for branch in self.branches],
            "fit_estimate": self.fit_estimate.as_json(),
            "level": self.level,
        }


def perception_branch_ceiling(*, base_ceiling: int, branch_count: int, level: int) -> int:
    """The Perception-branch contact-ceiling term (design section 3, "Budget").

    Level 1: ``base + (K - 1)`` -- the extra Perception contacts of the
    K - 1 non-A branches. Level 2: ``base + 2 (K - 1)`` -- the same
    Perception contacts, plus one extra Solver contact per non-A branch.
    ``branch_count`` is K, counting A and T.
    """

    if level not in PERCEPTION_BRANCH_LEVELS:
        raise PerceptionBranchError(
            f"perception branch level must be one of {PERCEPTION_BRANCH_LEVELS}"
        )
    if (
        isinstance(branch_count, bool)
        or not isinstance(branch_count, int)
        or branch_count < MIN_PERCEPTION_BRANCHES
    ):
        raise PerceptionBranchError(
            "perception branch group must declare at least "
            f"{MIN_PERCEPTION_BRANCHES} branches"
        )
    extra = branch_count - 1
    if level == PERCEPTION_BRANCH_LEVEL_SOLVER:
        extra *= 2
    return base_ceiling + extra


def parse_perception_branch_knob(
    path: object,
    value: object,
    *,
    first_phase_id: str,
    declared_stores: Sequence[str] | None = None,
) -> PerceptionBranchKnob:
    """Parse ONE branch ``overrides`` entry, refusing everything it does not admit.

    Unlike :func:`parse_supply_variant_knob`, this ADMITS -- indeed requires
    -- the program's first phase: a Perception branch's boundary-supply knob
    is resolved into the branch's own PRE-FLIGHT seed
    (``core.flight.runtime.FlightRuntime._supply_action_router``), never into
    a per-row rendering over the episode's own QueryState, so the mechanical
    reason refusal 7 exists for the ordinary Solver arm route does not apply
    here.
    """

    text = _nonempty_str(path, field="perception branch overrides key")
    segments = text.split(".")
    if len(segments) < 4 or segments[0] != SUPPLY_VARIANT_KNOB_ROOT:
        raise PerceptionBranchError(
            f"perception branch override {text!r} is not a knob path; a branch "
            f"may override only {SUPPLY_VARIANT_KNOB_ROOT}.<store>."
            f"{PERCEPTION_BRANCH_KNOB_ROUTE}.<phase>.<knob>"
        )
    store_id, route, phase = segments[1], segments[2], segments[3]
    tail = tuple(segments[4:])
    if not store_id or not phase:
        raise PerceptionBranchError(
            f"perception branch override {text!r} names an empty store or phase"
        )
    if route != PERCEPTION_BRANCH_KNOB_ROUTE:
        raise PerceptionBranchError(
            f"perception branch override {text!r} names route {route!r}; a "
            f"branch may re-cap only {PERCEPTION_BRANCH_KNOB_ROUTE!r}"
        )
    if tail not in PERCEPTION_BRANCH_KNOB_TAILS:
        admitted = sorted(".".join(item) for item in PERCEPTION_BRANCH_KNOB_TAILS)
        raise PerceptionBranchError(
            f"perception branch override {text!r} names knob {'.'.join(tail)!r}, "
            f"which is not admitted; the admitted knobs are {admitted}"
        )
    if phase != first_phase_id:
        raise PerceptionBranchError(
            f"perception branch override {text!r} names phase {phase!r}, but a "
            f"branch may re-cap only the program's FIRST phase {first_phase_id!r}: "
            "Perception's own boundary supply"
        )
    if declared_stores is not None and store_id not in set(declared_stores):
        raise PerceptionBranchError(
            f"perception branch override {text!r} names store {store_id!r}, "
            f"which this configuration does not declare; declared stores are "
            f"{sorted(set(declared_stores))}"
        )
    resolved_value = (
        _rank_weight_value(value, field=f"perception branch override {text!r}")
        if tail[0] == "rank_weights"
        else _positive_int(value, field=f"perception branch override {text!r}")
    )
    return PerceptionBranchKnob(
        path=text, store_id=store_id, phase=phase, tail=tail, value=resolved_value,
    )


def parse_perception_branches(
    block: object,
    *,
    first_phase_id: str,
    declared_stores: Sequence[str] | None = None,
    declared_alternate_relpaths: Mapping[str, Sequence[str]] | None = None,
    registered_presentation_ids: Sequence[str] | None = None,
    max_candidates_ceiling: int | None = None,
) -> PerceptionBranchGroup:
    """Parse ``native_episode.roles.perception.branches``, fail-closed.

    Structurally :func:`parse_supply_variants`'s twin (design section 3,
    "Fork point"), with the differences design section 1 names: a branch may
    target the program's first phase (indeed must, for a boundary-supply
    knob); a branch's release_swap, presentation or response-contract axis is
    admitted through the same "one factor" rule a knob override is; and the
    group additionally declares ``level`` (1 or 2, design section 1) and
    requires exactly one twin (T) branch (design section 4, "A/A = twin").

    ``registered_presentation_ids`` is ``core.base.PERCEPTION_PRESENTATIONS
    .names()`` -- this module does not import ``core.base`` itself, so a
    caller that omits it gets shape checking only, exactly as
    ``declared_stores=None`` does for a knob's store. ``max_candidates_ceiling``
    bounds ``min_candidates`` the same way; a caller that omits it gets no
    upper check beyond "positive integer".

    The refusals, in order, each raised by name BEFORE any contact:

    1. a block that is not an object with exactly ``branches``,
       ``fit_estimate`` and ``level``;
    2. a ``level`` outside :data:`PERCEPTION_BRANCH_LEVELS`;
    3. a branch row with unknown or missing keys;
    4. a branch count outside :data:`MIN_PERCEPTION_BRANCHES` ..
       :data:`MAX_PERCEPTION_BRANCHES`;
    5. a branch id collision;
    6. zero or several branches carrying ``deliver`` (branch A), or a
       delivering branch that is not the LAST branch, or that carries any
       axis at all;
    7. zero or several branches naming ``replicate_of`` the delivering
       branch (exactly one twin T is required), a twin naming a branch that
       is not the delivering branch, or a twin that carries any axis;
    8. more than :data:`MAX_PERCEPTION_B_BRANCHES` B branches (beside A
       and T);
    9. an override path this module does not admit
       (:func:`parse_perception_branch_knob`);
    10. a release_swap naming an undeclared store or an undeclared
        alternate (:func:`parse_supply_variant_release_swap`);
    11. a presentation_id absent from ``registered_presentation_ids``, when
        given;
    12. a min_candidates outside ``1 .. max_candidates_ceiling``, when given;
    13. a non-A, non-T branch declaring zero or more than one axis category
        -- "one factor per non-A branch" (design section 1);
    14. two B branches whose whole axis is identical;
    15. a branch whose estimated prompt exceeds the live slot with the
        registered reserve.
    """

    if not isinstance(block, Mapping) or set(block) != PERCEPTION_BRANCH_BLOCK_KEYS:
        raise PerceptionBranchError(
            "native_episode.roles.perception.branches must be an object with "
            f"exactly {sorted(PERCEPTION_BRANCH_BLOCK_KEYS)}"
        )
    level = block["level"]
    if isinstance(level, bool) or level not in PERCEPTION_BRANCH_LEVELS:
        raise PerceptionBranchError(
            f"perception branches.level must be one of {PERCEPTION_BRANCH_LEVELS}"
        )
    rows = block["branches"]
    if (
        not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise PerceptionBranchError(
            "perception branches.branches must be an ordered list of branch objects"
        )
    if not MIN_PERCEPTION_BRANCHES <= len(rows) <= MAX_PERCEPTION_BRANCHES:
        raise PerceptionBranchError(
            "perception branches.branches must declare between "
            f"{MIN_PERCEPTION_BRANCHES} and {MAX_PERCEPTION_BRANCHES} branches"
        )
    fit_estimate = parse_supply_variant_fit_estimate(block["fit_estimate"])
    branches: list[PerceptionBranch] = []
    for position, row in enumerate(rows):
        keys = set(row)
        if (
            not PERCEPTION_BRANCH_REQUIRED_KEYS <= keys
            or keys - PERCEPTION_BRANCH_REQUIRED_KEYS - PERCEPTION_BRANCH_OPTIONAL_KEYS
        ):
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] must carry exactly "
                f"{sorted(PERCEPTION_BRANCH_REQUIRED_KEYS)} plus optional "
                f"{sorted(PERCEPTION_BRANCH_OPTIONAL_KEYS)}"
            )
        branch_id = _nonempty_str(
            row["branch_id"],
            field=f"perception branches.branches[{position}].branch_id",
        )
        deliver = row.get("deliver", False)
        if not isinstance(deliver, bool):
            raise PerceptionBranchError(
                f"perception branches.branches[{position}].deliver must be a bool"
            )
        overrides = row.get("overrides", {})
        if not isinstance(overrides, Mapping):
            raise PerceptionBranchError(
                f"perception branches.branches[{position}].overrides must be an "
                "object"
            )
        raw_replicate_of = row.get("replicate_of")
        replicate_of = None if raw_replicate_of is None else _nonempty_str(
            raw_replicate_of,
            field=f"perception branches.branches[{position}].replicate_of",
        )
        if deliver and replicate_of is not None:
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] declares both "
                "deliver: true and replicate_of; the delivering branch (A) "
                "cannot also be the twin (T)"
            )
        knobs = tuple(
            parse_perception_branch_knob(
                path, value, first_phase_id=first_phase_id,
                declared_stores=declared_stores,
            )
            for path, value in sorted(overrides.items())
        )
        raw_release_swap = row.get("release_swap")
        release_swap = (
            None if raw_release_swap is None
            else parse_supply_variant_release_swap(
                raw_release_swap, declared_stores=declared_stores,
                declared_alternate_relpaths=declared_alternate_relpaths,
            )
        )
        presentation_id = row.get("presentation_id")
        if presentation_id is not None:
            presentation_id = _nonempty_str(
                presentation_id,
                field=f"perception branches.branches[{position}].presentation_id",
            )
            if (
                registered_presentation_ids is not None
                and presentation_id not in set(registered_presentation_ids)
            ):
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}].presentation_id "
                    f"{presentation_id!r} is not registered; registered ids are "
                    f"{sorted(set(registered_presentation_ids))}"
                )
        min_candidates = row.get("min_candidates")
        if min_candidates is not None:
            if (
                isinstance(min_candidates, bool)
                or not isinstance(min_candidates, int)
                or min_candidates < 1
            ):
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}].min_candidates "
                    "must be a positive integer"
                )
            if (
                max_candidates_ceiling is not None
                and min_candidates > max_candidates_ceiling
            ):
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}].min_candidates "
                    f"{min_candidates} exceeds the configured max_candidates "
                    f"ceiling {max_candidates_ceiling}"
                )
        raw_prepared_seed = row.get("prepared_seed")
        prepared_seed = None
        if raw_prepared_seed is not None:
            if (
                not isinstance(raw_prepared_seed, Mapping)
                or set(raw_prepared_seed) != {"relpath", "sha256"}
                or not isinstance(raw_prepared_seed.get("relpath"), str)
                or not raw_prepared_seed["relpath"]
                or not isinstance(raw_prepared_seed.get("sha256"), str)
                or len(raw_prepared_seed["sha256"]) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in raw_prepared_seed["sha256"]
                )
            ):
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}].prepared_seed "
                    "must be exactly {relpath, sha256}, with sha256 a "
                    "lowercase 64-hex SHA-256"
                )
            prepared_seed = {
                "relpath": raw_prepared_seed["relpath"],
                "sha256": raw_prepared_seed["sha256"],
            }
        has_axis = bool(knobs) or release_swap is not None or presentation_id is not None or min_candidates is not None
        if replicate_of is not None and has_axis:
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] names replicate_of "
                "and must declare no axis: it resolves exactly the delivering "
                "branch's (A's) own request"
            )
        if deliver and has_axis:
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] carries deliver: "
                "true and must declare no axis: A is the cell's own request, "
                "override-free"
            )
        if (deliver or replicate_of is not None) and prepared_seed is not None:
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] carries a "
                "prepared_seed but is A or its twin (T): A's seed is the "
                "cell's own prepared_phase_supply, and T takes A's seed"
            )
        if not deliver and replicate_of is None:
            axis_categories = sum((
                bool(knobs), release_swap is not None, presentation_id is not None,
                min_candidates is not None,
            ))
            if axis_categories != 1:
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}] must declare "
                    "exactly one axis category (a boundary-supply knob, a "
                    "release_swap, a presentation_id or a min_candidates) -- "
                    "one factor per non-A branch"
                )
        branches.append(PerceptionBranch(
            branch_id=branch_id, deliver=deliver, knobs=knobs,
            max_supplied_items=_positive_int(
                row["max_supplied_items"],
                field=f"perception branches.branches[{position}].max_supplied_items",
            ),
            replicate_of=replicate_of, release_swap=release_swap,
            presentation_id=presentation_id, min_candidates=min_candidates,
            prepared_seed=prepared_seed,
        ))
    ids = [branch.branch_id for branch in branches]
    if len(set(ids)) != len(ids):
        raise PerceptionBranchError("perception branch ids must be distinct")
    delivering = [branch.branch_id for branch in branches if branch.deliver]
    if len(delivering) != 1:
        raise PerceptionBranchError(
            "perception branches must declare exactly one branch with "
            f"deliver: true (A); this block declares {len(delivering)}"
        )
    if not branches[-1].deliver:
        raise PerceptionBranchError(
            f"perception branches delivering branch (A) {delivering[0]!r} must "
            "be the LAST branch: A continues through Solver/Reviewer/Planner "
            "exactly as today and is contacted last in the branch batch"
        )
    delivered_branch_id = branches[-1].branch_id
    twins = [branch for branch in branches if branch.replicate_of is not None]
    for branch in twins:
        if branch.replicate_of != delivered_branch_id:
            raise PerceptionBranchError(
                f"perception branch {branch.branch_id!r} names replicate_of "
                f"{branch.replicate_of!r}, which is not the delivering branch "
                f"{delivered_branch_id!r}"
            )
    if len(twins) != 1:
        raise PerceptionBranchError(
            "perception branches must declare exactly one twin (replicate_of "
            "the delivering branch A): the within-flight A/A null every "
            "same-flight-perception-variant read requires (design section 4, "
            "'A/A = twin')"
        )
    b_branches = [branch for branch in branches if branch.is_b]
    if len(b_branches) > MAX_PERCEPTION_B_BRANCHES:
        raise PerceptionBranchError(
            "perception branches must declare at most "
            f"{MAX_PERCEPTION_B_BRANCHES} B branches beside A and its twin T"
        )
    signatures = [
        (
            tuple((knob.path, knob.value) for knob in branch.knobs),
            None if branch.release_swap is None else (
                branch.release_swap.store_id, branch.release_swap.release_relpath,
            ),
            branch.presentation_id,
            branch.min_candidates,
        )
        for branch in b_branches
    ]
    if len(set(signatures)) != len(signatures):
        raise PerceptionBranchError(
            "two perception B branches declare the same axis; two spellings "
            "of one construction spend a contact per row and measure nothing"
        )
    for branch in branches:
        estimated = fit_estimate.estimated_prompt_tokens(branch)
        if estimated > fit_estimate.prompt_limit_tokens:
            raise PerceptionBranchError(
                f"perception branch {branch.branch_id!r} estimates {estimated} "
                f"prompt tokens at {branch.max_supplied_items} supplied items, "
                f"which exceeds the {fit_estimate.prompt_limit_tokens}-token "
                f"limit of a {fit_estimate.slot_tokens}-token slot with its "
                f"registered {fit_estimate.reserve_tokens}-token reserve, the "
                f"{fit_estimate.completion_ceiling}-token completion ceiling "
                f"and the {REGISTERED_SPECIAL_TOKEN_RESERVE}-token special "
                "reserve"
            )
    return PerceptionBranchGroup(
        branches=tuple(branches), fit_estimate=fit_estimate, level=level,
    )


def perception_branch_record(
    *,
    branch: PerceptionBranch,
    branch_index: int,
    contact_id: str,
    request_sha256: str,
    response_text_sha256: str,
    note_sha256: str,
    note_parse_status: str,
    candidate_intent_ids: Sequence[str],
    supplied_value_ids: Sequence[str],
    resolved_knobs: Mapping[str, int] | None = None,
    solver_contact_id: str | None = None,
    solver_request_sha256: str | None = None,
    solver_response_text_sha256: str | None = None,
    candidate_supply_value_ids: Sequence[str] | None = None,
) -> dict[str, object]:
    """One branch's receipt row (design section 3, "Receipt").

    The four ``solver_*``/``candidate_supply_value_ids`` fields are declared
    together or not at all: level 1 never supplies them, level 2 supplies
    them for every branch (A's naming its own ordinary first Solver visit,
    every other branch's naming the one Solver contact its note fanned out
    -- design section 3, "Level 2").
    """

    ids = tuple(supplied_value_ids)
    if len(set(ids)) != len(ids):
        raise PerceptionBranchError(
            "a perception branch record must have unique supplied ids"
        )
    if len(ids) > branch.max_supplied_items:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} supplied {len(ids)} "
            f"items, above its declared max_supplied_items "
            f"{branch.max_supplied_items}"
        )
    declared = {knob.path: knob.value for knob in branch.knobs}
    resolved = dict(declared if resolved_knobs is None else resolved_knobs)
    if resolved != declared:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} resolved knobs "
            f"{sorted(resolved)} differ from the knobs it declared "
            f"{sorted(declared)}"
        )
    candidates = tuple(candidate_intent_ids)
    if any(not isinstance(value, str) or not value for value in candidates):
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} candidate_intent_ids "
            "must be non-empty strings"
        )
    level2_fields = (
        solver_contact_id, solver_request_sha256, solver_response_text_sha256,
        candidate_supply_value_ids,
    )
    has_level2 = any(field is not None for field in level2_fields)
    if has_level2 and any(field is None for field in level2_fields):
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} must declare all four "
            "level-2 fields together or none of them"
        )
    record: dict[str, object] = {
        "branch_index": int(branch_index),
        "branch_id": branch.branch_id,
        "deliver": bool(branch.deliver),
        "replicate_of": branch.replicate_of,
        "resolved_knobs": [
            {"path": path, "value": int(value)}
            for path, value in sorted(resolved.items())
        ],
        "release_swap": (
            None if branch.release_swap is None else branch.release_swap.as_json()
        ),
        "presentation_id": branch.presentation_id,
        "min_candidates": branch.min_candidates,
        "supplied_value_ids": list(ids),
        "supplied_count": len(ids),
        "max_supplied_items": branch.max_supplied_items,
        "contact_id": _nonempty_str(
            contact_id, field=f"perception branch {branch.branch_id!r} contact_id",
        ),
        "request_sha256": _sha256_hex(request_sha256, field="request_sha256"),
        "response_text_sha256": _sha256_hex(
            response_text_sha256, field="response_text_sha256",
        ),
        "note_sha256": _sha256_hex(note_sha256, field="note_sha256"),
        "note_parse_status": _nonempty_str(
            note_parse_status, field="note_parse_status",
        ),
        "candidate_intent_ids": list(candidates),
    }
    if has_level2:
        record["solver_contact_id"] = _nonempty_str(
            solver_contact_id,
            field=f"perception branch {branch.branch_id!r} solver_contact_id",
        )
        record["solver_request_sha256"] = _sha256_hex(
            solver_request_sha256, field="solver_request_sha256",
        )
        record["solver_response_text_sha256"] = _sha256_hex(
            solver_response_text_sha256, field="solver_response_text_sha256",
        )
        record["candidate_supply_value_ids"] = list(candidate_supply_value_ids)
    return record


def perception_branch_receipt(
    *,
    group: PerceptionBranchGroup,
    phase_id: str,
    records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    """The whole Perception branch group's receipt (design section 3, "Receipt").

    Sealed once per row, from the ONE Perception visit -- Perception has no
    "every"/"first" choice (design section 3, "Branch visits"), so unlike
    :func:`supply_variant_receipt` there is no later-visit carry-forward rule
    to state.
    """

    return {
        "schema": PERCEPTION_BRANCH_RECEIPT_SCHEMA,
        "phase_id": _nonempty_str(
            phase_id, field="perception_branch_receipt.phase_id",
        ),
        "level": group.level,
        "branch_count": group.branch_count,
        "delivered_branch_id": group.delivering_branch.branch_id,
        "branch_visits": PERCEPTION_BRANCH_VISITS,
        "visit_index": 0,
        "fit_estimate": group.fit_estimate.as_json(),
        "branches": [dict(record) for record in records],
    }


__all__ = [
    "MAX_PERCEPTION_B_BRANCHES",
    "MAX_PERCEPTION_BRANCHES",
    "MIN_PERCEPTION_BRANCHES",
    "PERCEPTION_BRANCH_BLOCK_KEYS",
    "PERCEPTION_BRANCH_KNOB_ROUTE",
    "PERCEPTION_BRANCH_KNOB_TAILS",
    "PERCEPTION_BRANCH_LEVEL2_RECORD_KEYS",
    "PERCEPTION_BRANCH_LEVEL_NOTE",
    "PERCEPTION_BRANCH_LEVEL_SOLVER",
    "PERCEPTION_BRANCH_LEVELS",
    "PERCEPTION_BRANCH_OPTIONAL_KEYS",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA",
    "PERCEPTION_BRANCH_RECORD_KEYS",
    "PERCEPTION_BRANCH_REQUIRED_KEYS",
    "PERCEPTION_BRANCH_VISITS",
    "PerceptionBranch",
    "PerceptionBranchError",
    "PerceptionBranchGroup",
    "PerceptionBranchKnob",
    "parse_perception_branch_knob",
    "parse_perception_branches",
    "perception_branch_ceiling",
    "perception_branch_record",
    "perception_branch_receipt",
    "MAX_SUPPLY_VARIANT_ARMS",
    "MIN_SUPPLY_VARIANT_ARMS",
    "SUPPLY_VARIANT_ARM_OPTIONAL_KEYS",
    "SUPPLY_VARIANT_ARM_REQUIRED_KEYS",
    "SUPPLY_VARIANT_ARM_VISITS_DEFAULT",
    "SUPPLY_VARIANT_ARM_VISITS_INSTRUMENT",
    "SUPPLY_VARIANT_ARM_VISITS_VALUES",
    "SUPPLY_VARIANT_BLOCK_KEYS",
    "SUPPLY_VARIANT_BLOCK_OPTIONAL_KEYS",
    "SUPPLY_VARIANT_FIT_KEYS",
    "SUPPLY_VARIANT_KNOB_ROOT",
    "SUPPLY_VARIANT_KNOB_TAILS",
    "SUPPLY_VARIANT_RECEIPT_SCHEMA",
    "SupplyVariantArm",
    "SupplyVariantError",
    "SupplyVariantFitEstimate",
    "SupplyVariantGroup",
    "SupplyVariantKnob",
    "SupplyVariantReleaseSwap",
    "arm_supplied_value_ids",
    "parse_supply_variant_fit_estimate",
    "parse_supply_variant_knob",
    "parse_supply_variant_release_swap",
    "parse_supply_variants",
    "supply_variant_arm_record",
    "supply_variant_receipt",
]
