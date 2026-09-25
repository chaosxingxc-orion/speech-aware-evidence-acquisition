"""Per-row supply-variant interleaving at ONE node (item E42, family VAR-2).

WHY THIS EXISTS. Cell ROLL-AA (``docs/results/2026-09-24-slurp-stage3-roll-aa-
within-flight-null-read.md``) measured the locked v2.0 plan against itself
INSIDE one flight: byte-identical prompts at temperature 0 repeat the delivered
answer on 91.5 % of rows, the delivered intent never changes, and the paired
per-row half-width is ``h_within`` = 0.735 pp SLU / 0.000 pp intent at n = 200.
The SAME identity flown as two separate campaigns reads about 1.25 pp. So a
construction variant compared per row INSIDE one campaign is read at roughly a
third of the cross-flight floor. The VAR-1 family flies one campaign per
variant and pays the between-flight penalty; this module is the harness
capability that removes it.

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

#: The receipt schema one arm group seals under.
SUPPLY_VARIANT_RECEIPT_SCHEMA = "saea-supply-variant-arms-v1"

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

#: Keys the ``supply_variants`` block carries, exactly.
SUPPLY_VARIANT_BLOCK_KEYS = frozenset({"arms", "fit_estimate"})

#: Keys one arm row carries. ``deliver`` and ``overrides`` are optional in the
#: JSON and defaulted here; ``arm_id`` and ``max_supplied_items`` are required,
#: the second because the fit refusal below is fail-closed and cannot estimate
#: an arm that declares no bound.
SUPPLY_VARIANT_ARM_REQUIRED_KEYS = frozenset({"arm_id", "max_supplied_items"})
SUPPLY_VARIANT_ARM_OPTIONAL_KEYS = frozenset({"deliver", "overrides"})

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
class SupplyVariantArm:
    """One arm of one node's supply-variant group."""

    arm_id: str
    deliver: bool
    knobs: tuple[SupplyVariantKnob, ...]
    max_supplied_items: int

    def as_json(self) -> dict[str, object]:
        return {
            "arm_id": self.arm_id,
            "deliver": self.deliver,
            "overrides": {knob.path: knob.value for knob in self.knobs},
            "knobs": [knob.as_json() for knob in self.knobs],
            "max_supplied_items": self.max_supplied_items,
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
    6. a delivering arm that is not the LAST arm, or that carries overrides;
    7. an override path this module does not admit -- unknown root, unknown
       route, unknown knob, an undeclared store, the program's first phase, or
       another node's phase (:func:`parse_supply_variant_knob`);
    8. two arms whose whole override set is identical (two spellings of one
       arm cost a contact per row and measure nothing);
    9. an arm whose estimated prompt exceeds the live slot with the registered
       reserve.
    """

    if not isinstance(block, Mapping) or set(block) != set(
        SUPPLY_VARIANT_BLOCK_KEYS
    ):
        raise SupplyVariantError(
            "roles.<role>.supply_variants must be an object with exactly "
            f"{sorted(SUPPLY_VARIANT_BLOCK_KEYS)}"
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
        knobs = tuple(
            parse_supply_variant_knob(
                path, value, phase_id=phase_id, first_phase_id=first_phase_id,
                declared_stores=declared_stores,
            )
            for path, value in sorted(overrides.items())
        )
        arms.append(SupplyVariantArm(
            arm_id=arm_id,
            deliver=deliver,
            knobs=knobs,
            max_supplied_items=_positive_int(
                row["max_supplied_items"],
                field=f"supply_variants.arms[{position}].max_supplied_items",
            ),
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
    signatures = [
        tuple((knob.path, knob.value) for knob in arm.knobs) for arm in arms
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
    return SupplyVariantGroup(arms=tuple(arms), fit_estimate=fit_estimate)


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
    """The whole arm group's receipt, as the delivered role result carries it."""

    return {
        "schema": SUPPLY_VARIANT_RECEIPT_SCHEMA,
        "phase_id": _nonempty_str(
            phase_id, field="supply_variant_receipt.phase_id"
        ),
        "arm_count": group.arm_count,
        "delivered_arm_id": group.delivered_arm.arm_id,
        "fit_estimate": group.fit_estimate.as_json(),
        "arms": [dict(record) for record in records],
    }


__all__ = [
    "MAX_SUPPLY_VARIANT_ARMS",
    "MIN_SUPPLY_VARIANT_ARMS",
    "SUPPLY_VARIANT_ARM_OPTIONAL_KEYS",
    "SUPPLY_VARIANT_ARM_REQUIRED_KEYS",
    "SUPPLY_VARIANT_BLOCK_KEYS",
    "SUPPLY_VARIANT_FIT_KEYS",
    "SUPPLY_VARIANT_KNOB_ROOT",
    "SUPPLY_VARIANT_KNOB_TAILS",
    "SUPPLY_VARIANT_RECEIPT_SCHEMA",
    "SupplyVariantArm",
    "SupplyVariantError",
    "SupplyVariantFitEstimate",
    "SupplyVariantGroup",
    "SupplyVariantKnob",
    "arm_supplied_value_ids",
    "parse_supply_variant_fit_estimate",
    "parse_supply_variant_knob",
    "parse_supply_variants",
    "supply_variant_arm_record",
    "supply_variant_receipt",
]
