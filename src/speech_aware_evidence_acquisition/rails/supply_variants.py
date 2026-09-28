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


__all__ = [
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
