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

THE NODE-TEMPLATE KIND (NX programme, items E1/E2, 2026-10-09). A group
parsed by :func:`parse_template_variants` is the same form with the varied axis
moved from SUPPLY to the node's INSTRUCTION TEMPLATE: each non-delivering,
non-twin arm overrides exactly ONE thing -- ``phase_material.<role>.
instruction_template``, a hash-pinned relpath under ``probes/`` -- and nothing
else (no knob, no release swap, no supply of its own). The supply is therefore
UNVARIED: every arm renders the delivering arm's own evidence, which the v4
receipt (:data:`SUPPLY_VARIANT_RECEIPT_SCHEMA_V4`) states and its validator
checks. The delivering arm is still LAST and carries no override, so invariants
I7 and I7v hold unchanged and the delivered request is the locked plan's, byte
for byte. Design: docs/superpowers/specs/2026-10-09-slurp-nx-node-template-
variant-instrument-design.md.

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

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .context_budget import (
    REGISTERED_SPECIAL_TOKEN_RESERVE,
    serving_bound_reserve_tokens,
)
from .errors import RailsError
from .native_episode_receipt import (
    DECODING_VARIANT_KNOBS,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA as _RECEIPT_PERCEPTION_BRANCH_RECEIPT_SCHEMA,
    PERCEPTION_BRANCH_KEY_SOURCE_FIELDS,
    PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS,
    PERCEPTION_BRANCH_ABSENT_REASONS,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5,
    PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6,
    SAMPLING_AXES,
    perception_branch_sampling_error,
    parse_perception_branch_note,
    perception_branch_thinking_policy_error,
    perception_branch_key_source_error,
    perception_branch_note_fields_error,
    validate_perception_branch_receipt,
)

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

#: The multi-store supply receipt (loop engineering item E-T6, 2026-10-11,
#: owner decision 263-A / 265): v3's arm rows with ``release_swap`` replaced by
#: ``release_swaps`` -- the ordered list of every ``{store_id, release}`` the
#: arm repoints (``[]`` when none). A group seals under v5 ONLY when some arm
#: swaps two or more stores (:attr:`SupplyVariantGroup.uses_release_swaps`);
#: every group with at most one swap per arm keeps sealing v3, byte for byte.
SUPPLY_VARIANT_RECEIPT_SCHEMA_V5 = "saea-supply-variant-arms-v5"

#: What the tfrl archive view writer sets as ``release_swaps_supported`` (E-T6 landed:
#: an arm may repoint several stores). ``rails.tfrl_typed_proposer.ArchiveView.
#: from_mapping`` reads the key; it defaults to False, so the writer must pass this.
MULTI_STORE_RELEASE_SWAPS_SUPPORTED = True

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
    {"deliver", "overrides", "replicate_of", "release_swap", "release_swaps"}
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


#: The receipt schema a NODE-TEMPLATE group seals under (NX programme E1):
#: v3's arm rows plus ``instruction_template`` -- ``None`` for the delivering
#: arm and the twin, the declared ``{relpath, sha256}`` for every other arm.
SUPPLY_VARIANT_RECEIPT_SCHEMA_V4 = "saea-supply-variant-arms-v4"

#: The group kinds. ``"supply"`` is every group written before the NX
#: programme; ``"template"`` is the node-template kind.
SUPPLY_VARIANT_KIND_SUPPLY = "supply"
SUPPLY_VARIANT_KIND_TEMPLATE = "template"
#: The node-DECODING kind (NX-T R4, owner rulings 329 A / 332 A, 2026-10-18): a
#: sibling of the template kind. Every arm renders the delivering arm's own
#: evidence AND the node's own locked instruction template; the only thing a
#: candidate arm overrides is the SAMPLING parameters of its Solver contact.
SUPPLY_VARIANT_KIND_DECODING = "decoding"

#: The receipt schema a NODE-DECODING group seals under: v3's arm rows plus
#: ``decoding_override`` -- ``None`` for the delivering arm and the twin, the
#: declared (canonical, sorted-key) sampling override for every other arm.
#: Older receipts (v1-v5) validate unchanged.
SUPPLY_VARIANT_RECEIPT_SCHEMA_V6 = "saea-supply-variant-arms-v6"

#: The closed set of sampling parameters a decoding arm may override, with the
#: bounds each must satisfy (inclusive unless noted). Everything else on a
#: Solver contact -- the template, the evidence, the response format, the
#: thinking budget and completion cap, the request seed and the tool
#: authority -- is the lock's and is refused BY NAME if an arm names it.
#: ``min_p`` is intentionally absent (admit it only if a round needs it).
#: The table itself is owned by ``rails.native_episode_receipt`` (imported
#: above) so the parser and the receipt validator share it.
#:
#: Names an arm might try to override that belong to another axis, named so the
#: refusal says which axis owns them.
DECODING_VARIANT_REFUSED_KNOBS: Mapping[str, str] = {
    "seed": "the request seed is the lock's for every arm (a fixed seed is part of the registered design)",
    "max_tokens": "the completion cap belongs to the thinking-budget axis",
    "thinking_budget_tokens": "the thinking budget belongs to the thinking-budget axis",
    "chat_template_kwargs": "the thinking switch belongs to the thinking-budget axis",
    "response_format": "the response format is the node's own",
    "tool_choice": "tool authority is the node's own",
    "parallel_tool_calls": "tool authority is the node's own",
    "id_slot": "slot pinning is serving geometry",
    "min_p": "min_p is not admitted to the closed decoding set",
    "frequency_penalty": "frequency_penalty is not admitted to the closed decoding set",
    "logprobs": "logprobs is not a sampling parameter",
    "top_logprobs": "logprobs is not a sampling parameter",
}
#: Keys the ``decoding_variants`` block carries, exactly. ``template_tokens`` is
#: the locked template's token count, shared by every arm (all arms render it);
#: it enters only the fit estimate.
DECODING_VARIANT_BLOCK_KEYS = frozenset({
    "node", "arms", "max_supplied_items", "fit_estimate", "template_tokens",
})
#: Keys one decoding arm row may carry.
DECODING_VARIANT_ARM_KEYS = frozenset({"arm_id", "deliver", "replicate_of", "decoding"})
DECODING_VARIANT_NODES: tuple[str, ...] = ("solver",)
MIN_DECODING_CANDIDATE_ARMS = 1
MAX_DECODING_CANDIDATE_ARMS = 6

#: The nodes a template group may sit at. Solver first (NX round R1); the
#: parser, the materials builder and the arm record are keyed on the node's
#: own ``phase_id`` and are node-agnostic -- widening this tuple is the config
#: half of admitting the Reviewer or the Planner (the runtime wiring half is
#: listed in the instrument README).
TEMPLATE_VARIANT_NODES: tuple[str, ...] = ("solver", "perception")

#: Keys the ``template_variants`` block carries, exactly.
TEMPLATE_VARIANT_BLOCK_KEYS = frozenset({
    "node", "arms", "max_supplied_items", "fit_estimate",
})
#: Keys one template arm row may carry. ``arm_id`` is required;
#: ``instruction_template`` and ``template_tokens`` are required on every arm
#: but the twin (the delivering arm declares its own LOCKED template's token
#: count only, never a path -- the path is the node's own ``phase_material``).
TEMPLATE_VARIANT_ARM_KEYS = frozenset({
    "arm_id", "deliver", "replicate_of", "instruction_template", "template_tokens",
})
#: Keys an arm of the SUPPLY kind may carry that a template arm may NOT, named
#: so the refusal says which knob the arm tried to reach.
TEMPLATE_VARIANT_REFUSED_KNOB_KEYS = frozenset({
    "overrides", "release_swap", "knobs", "max_supplied_items",
})
#: The roots an arm's template may live under, relative to ``configs/`` (the
#: base of every ``phase_material.instruction_template``). A declaration may
#: spell the path with or without the ``configs/`` prefix.
TEMPLATE_VARIANT_ROOTS: tuple[str, ...] = ("probes/",)
#: Candidate (non-delivering, non-twin) template arms per group, inclusive:
#: programme C0.5 caps a round at six candidates. With the delivering arm and
#: the optional twin the group spans at most
#: :data:`MAX_SUPPLY_VARIANT_ARMS` (8) contacts.
MIN_TEMPLATE_CANDIDATE_ARMS = 1
MAX_TEMPLATE_CANDIDATE_ARMS = 6

_TEMPLATE_RELPATH_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*"
)
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


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
class SupplyVariantTemplate:
    """One arm's pinned instruction template (NX programme E1).

    ``relpath`` is relative to ``configs/`` -- the exact form a
    ``phase_material.<role>.instruction_template`` carries -- and ``sha256``
    is the lowercase digest of the file's bytes, verified by the flight
    before any contact (``core.flight.runtime.FlightRuntime.
    _template_variant_materials``).
    """

    relpath: str
    sha256: str

    def as_json(self) -> dict[str, str]:
        return {"relpath": self.relpath, "sha256": self.sha256}


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
    # NX programme E1 (2026-10-09): this arm's INSTRUCTION-TEMPLATE override --
    # the pinned template it renders in place of the node's own -- or ``None``
    # for every arm of the SUPPLY kind, the delivering arm and the twin.
    # Declared LAST, so every arm parsed before this field existed composes
    # byte-identically (``as_json`` omits the key while it is ``None``).
    instruction_template: "SupplyVariantTemplate | None" = None
    # The measured token count of the template this arm renders (the template
    # arm's own, or the delivering arm's locked template); 0 on the SUPPLY
    # kind. Enters only the fit estimate.
    template_tokens: int = 0
    # Loop engineering item E-T6 (2026-10-11): the arm's swaps when it
    # repoints TWO OR MORE stores, ordered by ``store_id``, one per distinct
    # store. Canonical form (enforced in ``__post_init__``): ``release_swap``
    # carries the swap of a one-store arm exactly as before, ``release_swaps``
    # is non-empty only from two stores up, and the two are never both set --
    # so a one-store swap spelled either way is the same arm. Declared LAST,
    # so every arm parsed before this field existed composes byte-identically.
    release_swaps: tuple[SupplyVariantReleaseSwap, ...] = ()
    # NX-T R4 (2026-10-18): this arm's SAMPLING override -- a tuple of
    # ``(name, value)`` pairs sorted by name, drawn from
    # :data:`DECODING_VARIANT_KNOBS` -- or ``None`` for every arm of the other
    # kinds, the delivering arm and the twin. Declared LAST, so every arm
    # parsed before this field existed composes byte-identically
    # (``as_json`` omits the key while it is ``None``).
    decoding_override: tuple[tuple[str, float | int], ...] | None = None

    @property
    def decoding(self) -> dict[str, float | int] | None:
        """The override as the mapping applied to the Solver contact's request."""

        return None if self.decoding_override is None else dict(self.decoding_override)

    def __post_init__(self) -> None:
        swaps = tuple(self.release_swaps)
        if swaps and self.release_swap is not None:
            raise SupplyVariantError(
                f"supply-variant arm {self.arm_id!r} declares both release_swap "
                "and release_swaps; declare one"
            )
        if len({swap.store_id for swap in swaps}) != len(swaps):
            raise SupplyVariantError(
                f"supply-variant arm {self.arm_id!r} release_swaps names a store "
                "twice; one swap per distinct store"
            )
        if len(swaps) == 1:
            object.__setattr__(self, "release_swap", swaps[0])
            swaps = ()
        object.__setattr__(
            self, "release_swaps",
            tuple(sorted(swaps, key=lambda swap: swap.store_id)),
        )

    @property
    def all_release_swaps(self) -> tuple[SupplyVariantReleaseSwap, ...]:
        """Every swap this arm declares, ordered by ``store_id`` (empty when
        none): the one accessor a consumer of the multi-store route reads."""

        if self.release_swap is not None:
            return (self.release_swap,)
        return self.release_swaps

    def as_json(self) -> dict[str, object]:
        row = {
            "arm_id": self.arm_id,
            "deliver": self.deliver,
            "overrides": {knob.path: knob.value for knob in self.knobs},
            "knobs": [knob.as_json() for knob in self.knobs],
            "max_supplied_items": self.max_supplied_items,
            "replicate_of": self.replicate_of,
            "release_swap": None if self.release_swap is None else self.release_swap.as_json(),
        }
        if self.release_swaps:
            row["release_swaps"] = [swap.as_json() for swap in self.release_swaps]
        if self.instruction_template is not None:
            row["instruction_template"] = self.instruction_template.as_json()
        if self.decoding_override is not None:
            row["decoding"] = dict(self.decoding_override)
        return row


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
            + getattr(arm, "template_tokens", 0)
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
    # NX programme E1: :data:`SUPPLY_VARIANT_KIND_SUPPLY` for every group
    # written before the programme, :data:`SUPPLY_VARIANT_KIND_TEMPLATE` for a
    # group :func:`parse_template_variants` returned.
    kind: str = SUPPLY_VARIANT_KIND_SUPPLY

    @property
    def is_template(self) -> bool:
        return self.kind == SUPPLY_VARIANT_KIND_TEMPLATE

    @property
    def is_decoding(self) -> bool:
        return self.kind == SUPPLY_VARIANT_KIND_DECODING

    @property
    def unvaried_evidence(self) -> bool:
        """True for the kinds whose every arm renders the delivering arm's own
        evidence (template and decoding): the runner takes the arms' messages
        from the one ``base_messages`` and resolves no per-arm supply."""

        return self.kind in (SUPPLY_VARIANT_KIND_TEMPLATE, SUPPLY_VARIANT_KIND_DECODING)

    @property
    def uses_release_swaps(self) -> bool:
        """True when some arm repoints two or more stores (E-T6): the group
        then seals the v5 receipt. False for every group written before."""

        return (
            not self.unvaried_evidence and any(arm.release_swaps for arm in self.arms)
        )

    @property
    def receipt_schema(self) -> str:
        if self.is_decoding:
            return SUPPLY_VARIANT_RECEIPT_SCHEMA_V6
        if self.is_template:
            return SUPPLY_VARIANT_RECEIPT_SCHEMA_V4
        if self.uses_release_swaps:
            return SUPPLY_VARIANT_RECEIPT_SCHEMA_V5
        return SUPPLY_VARIANT_RECEIPT_SCHEMA

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
        document = {
            "arms": [arm.as_json() for arm in self.arms],
            "fit_estimate": self.fit_estimate.as_json(),
            "arm_visits": self.arm_visits,
        }
        if self.is_template or self.is_decoding:
            document["kind"] = self.kind
        return document


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


def parse_supply_variant_release_swaps(
    block: object,
    *,
    declared_stores: Sequence[str] | None = None,
    declared_alternate_relpaths: Mapping[str, Sequence[str]] | None = None,
) -> tuple[SupplyVariantReleaseSwap, ...]:
    """Parse ONE ``arms[i].release_swaps`` list (loop item E-T6), fail-closed.

    A non-empty ordered list of ``{store_id, release}`` objects, each parsed by
    :func:`parse_supply_variant_release_swap` (so an undeclared store or a
    release absent from that store's declared alternates is refused by name),
    and no store named twice. Returned ordered by ``store_id``.
    """

    if (
        not isinstance(block, Sequence)
        or isinstance(block, (str, bytes))
        or not block
    ):
        raise SupplyVariantError(
            "supply_variants arm release_swaps must be a non-empty list of "
            "{store_id, release} objects"
        )
    swaps = tuple(
        parse_supply_variant_release_swap(
            entry, declared_stores=declared_stores,
            declared_alternate_relpaths=declared_alternate_relpaths,
        )
        for entry in block
    )
    stores = [swap.store_id for swap in swaps]
    repeated = sorted({store for store in stores if stores.count(store) > 1})
    if repeated:
        raise SupplyVariantError(
            f"supply-variant release_swaps names store(s) {repeated} more than "
            "once; one swap per distinct store"
        )
    return tuple(sorted(swaps, key=lambda swap: swap.store_id))


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
        raw_release_swaps = row.get("release_swaps")
        if raw_release_swaps is not None:
            if release_swap is not None:
                raise SupplyVariantError(
                    f"supply_variants.arms[{position}] declares both release_swap "
                    "and release_swaps; declare one"
                )
            release_swaps = parse_supply_variant_release_swaps(
                raw_release_swaps, declared_stores=declared_stores,
                declared_alternate_relpaths=declared_alternate_relpaths,
            )
        else:
            release_swaps = ()
        if replicate_of is not None and (release_swap is not None or release_swaps):
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
            release_swaps=release_swaps,
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
    if arms[-1].all_release_swaps:
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
            None if not arm.all_release_swaps else tuple(
                (swap.store_id, swap.release_relpath)
                for swap in arm.all_release_swaps
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


def _template_pin(value: object, *, field: str) -> SupplyVariantTemplate:
    """Parse one ``{relpath, sha256}`` template pin, refusing every other shape.

    A leading ``configs/`` is accepted and stripped (a declaration may spell
    the repository-relative path); what remains must be a plain relative path
    under one of :data:`TEMPLATE_VARIANT_ROOTS`. The digest must be lowercase
    64-hex. The BYTES are not read here -- this parser is pure; the flight
    hashes the file before any contact.
    """

    if not isinstance(value, Mapping) or set(value) != {"relpath", "sha256"}:
        raise SupplyVariantError(
            f"{field} must be exactly {{relpath, sha256}}: a template override is "
            "hash-pinned"
        )
    relpath, digest = value["relpath"], value["sha256"]
    if not isinstance(relpath, str) or not relpath.strip():
        raise SupplyVariantError(f"{field}.relpath must be a non-empty string")
    if not isinstance(digest, str) or _SHA256_RE.fullmatch(digest) is None:
        raise SupplyVariantError(
            f"{field}.sha256 must be a lowercase 64-hex digest; an unpinned "
            "template is not evidence"
        )
    path = relpath[len("configs/"):] if relpath.startswith("configs/") else relpath
    if (
        "\\" in path or path.startswith("/") or re.match(r"^[A-Za-z]:", path)
        or ".." in path.split("/") or _TEMPLATE_RELPATH_RE.fullmatch(path) is None
    ):
        raise SupplyVariantError(
            f"{field}.relpath {relpath!r} is not a plain repository-relative path"
        )
    if not any(path.startswith(root) for root in TEMPLATE_VARIANT_ROOTS):
        raise SupplyVariantError(
            f"{field}.relpath {relpath!r} is outside the allowed template roots "
            f"{['configs/' + root for root in TEMPLATE_VARIANT_ROOTS]}"
        )
    return SupplyVariantTemplate(relpath=path, sha256=digest)


def parse_template_variants(
    block: object,
    *,
    role_kind: str,
    phase_id: str,
    locked_template: str | None = None,
) -> SupplyVariantGroup:
    """Parse ``roles.<role>.template_variants`` into a template-kind group,
    fail-closed (NX programme E1).

    The refusals, each raised by name BEFORE any contact:

    1. a block that is not an object with exactly ``node``, ``arms``,
       ``max_supplied_items`` and ``fit_estimate``;
    2. a ``node`` that is not the role the block sits on, or a role outside
       :data:`TEMPLATE_VARIANT_NODES` (a variant declared on a node other than
       the one named);
    3. an arm count outside 1..:data:`MAX_TEMPLATE_CANDIDATE_ARMS` candidate
       arms (plus the delivering arm and at most one twin);
    4. an arm row with an unknown key -- and a supply knob (``overrides``,
       ``release_swap``, ``knobs``, a per-arm ``max_supplied_items``) named as
       such: the ONLY thing an arm overrides is its instruction template;
    5. an arm id collision, zero or several delivering arms, a delivering arm
       that is not LAST or that carries a template override, several twins or a
       twin that is not the delivering arm's;
    6. a candidate arm with a missing, mismatched-shape or unpinned template
       (``{relpath, sha256}``, lowercase 64-hex), a template outside
       :data:`TEMPLATE_VARIANT_ROOTS`, or a missing/non-positive
       ``template_tokens`` (on every arm but the twin);
    7. two arms naming the same template path or digest, or a candidate whose
       path equals the node's own locked template (``locked_template``: that
       arm would be a second spelling of the delivering arm);
    8. an arm whose estimated prompt exceeds the live slot with the registered
       reserve (:class:`SupplyVariantFitEstimate`).

    Every arm renders the SAME supplied evidence (the delivering arm's), so one
    ``max_supplied_items`` bounds them all.
    """

    keys = set(block) if isinstance(block, Mapping) else set()
    if not isinstance(block, Mapping) or keys != TEMPLATE_VARIANT_BLOCK_KEYS:
        raise SupplyVariantError(
            "roles.<role>.template_variants must be an object with exactly "
            f"{sorted(TEMPLATE_VARIANT_BLOCK_KEYS)}"
        )
    node = block["node"]
    if role_kind not in TEMPLATE_VARIANT_NODES:
        raise SupplyVariantError(
            f"template_variants may sit only at {list(TEMPLATE_VARIANT_NODES)}, "
            f"not the {role_kind!r} role"
        )
    if node != role_kind:
        raise SupplyVariantError(
            f"template_variants names node {node!r} but sits on the {role_kind!r} "
            "role; a variant is declared on exactly the node it names"
        )
    max_items = _positive_int(
        block["max_supplied_items"], field="template_variants.max_supplied_items"
    )
    rows = block["arms"]
    if (
        not isinstance(rows, Sequence) or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise SupplyVariantError(
            "template_variants.arms must be an ordered list of arm objects"
        )
    twins = [row for row in rows if row.get("replicate_of") is not None]
    candidates = len(rows) - len(twins) - 1
    if len(twins) > 1:
        raise SupplyVariantError(
            "template_variants admits at most one replicate_of twin"
        )
    if not MIN_TEMPLATE_CANDIDATE_ARMS <= candidates <= MAX_TEMPLATE_CANDIDATE_ARMS:
        raise SupplyVariantError(
            "template_variants must declare between "
            f"{MIN_TEMPLATE_CANDIDATE_ARMS} and {MAX_TEMPLATE_CANDIDATE_ARMS} "
            "candidate template arms (plus the delivering arm and at most one "
            f"twin); this block declares {max(candidates, 0)}"
        )
    fit_estimate = parse_supply_variant_fit_estimate(block["fit_estimate"])
    arms: list[SupplyVariantArm] = []
    for position, row in enumerate(rows):
        where = f"template_variants.arms[{position}]"
        refused = sorted(set(row) & TEMPLATE_VARIANT_REFUSED_KNOB_KEYS)
        if refused:
            raise SupplyVariantError(
                f"{where} names {refused}: a template arm overrides exactly its "
                "instruction_template and nothing else (no supply knob, no "
                "release swap, no bound of its own)"
            )
        unknown = sorted(set(row) - TEMPLATE_VARIANT_ARM_KEYS)
        if unknown or "arm_id" not in row:
            raise SupplyVariantError(
                f"{where} must carry arm_id plus optional "
                f"{sorted(TEMPLATE_VARIANT_ARM_KEYS - {'arm_id'})}; unknown keys: "
                f"{unknown}"
            )
        arm_id = _nonempty_str(row["arm_id"], field=f"{where}.arm_id")
        deliver = row.get("deliver", False)
        if not isinstance(deliver, bool):
            raise SupplyVariantError(f"{where}.deliver must be a bool")
        raw_replicate = row.get("replicate_of")
        replicate_of = (
            None if raw_replicate is None
            else _nonempty_str(raw_replicate, field=f"{where}.replicate_of")
        )
        if deliver and replicate_of is not None:
            raise SupplyVariantError(
                f"{where} declares both deliver: true and replicate_of"
            )
        pin = None
        if "instruction_template" in row:
            if deliver or replicate_of is not None:
                raise SupplyVariantError(
                    f"{where} is the delivering arm or the twin and must declare "
                    "no instruction_template: it renders the node's own locked "
                    "template, so its request is the locked plan's byte for byte"
                )
            pin = _template_pin(
                row["instruction_template"], field=f"{where}.instruction_template",
            )
        elif not deliver and replicate_of is None:
            raise SupplyVariantError(
                f"{where} is a candidate arm and must declare an "
                "instruction_template"
            )
        tokens = 0
        if replicate_of is None:
            tokens = _positive_int(
                row.get("template_tokens"), field=f"{where}.template_tokens"
            )
        elif "template_tokens" in row:
            raise SupplyVariantError(
                f"{where} is a twin and declares no template_tokens: it renders "
                "the delivering arm's template"
            )
        arms.append(SupplyVariantArm(
            arm_id=arm_id, deliver=deliver, knobs=(), max_supplied_items=max_items,
            replicate_of=replicate_of, instruction_template=pin,
            template_tokens=tokens,
        ))
    ids = [arm.arm_id for arm in arms]
    if len(set(ids)) != len(ids):
        raise SupplyVariantError("template_variants arm ids must be distinct")
    delivering = [arm.arm_id for arm in arms if arm.deliver]
    if len(delivering) != 1:
        raise SupplyVariantError(
            "template_variants must declare exactly one arm with deliver: true; "
            f"this block declares {len(delivering)}"
        )
    if not arms[-1].deliver:
        raise SupplyVariantError(
            f"template_variants delivering arm {delivering[0]!r} must be the LAST "
            "arm: the delivered text is then the group's final contact's own "
            "response, so invariant I7 holds with no new exception"
        )
    for arm in arms:
        if arm.replicate_of is not None and arm.replicate_of != arms[-1].arm_id:
            raise SupplyVariantError(
                f"template_variants arm {arm.arm_id!r} names replicate_of "
                f"{arm.replicate_of!r}, which is not the delivering arm "
                f"{arms[-1].arm_id!r}"
            )
    pins = [arm.instruction_template for arm in arms if arm.instruction_template]
    if len({pin.relpath for pin in pins}) != len(pins) or len(
        {pin.sha256 for pin in pins}
    ) != len(pins):
        raise SupplyVariantError(
            "two template_variants arms name the same template; two spellings of "
            "one construction spend a contact per row and measure nothing"
        )
    if locked_template is not None and any(
        pin.relpath == locked_template for pin in pins
    ):
        raise SupplyVariantError(
            f"a template_variants arm names the node's own locked template "
            f"{locked_template!r}; that arm is a second spelling of the "
            "delivering arm"
        )
    for arm in arms:
        estimated = fit_estimate.estimated_prompt_tokens(arm)
        if estimated > fit_estimate.prompt_limit_tokens:
            raise SupplyVariantError(
                f"template_variants arm {arm.arm_id!r} estimates {estimated} prompt "
                f"tokens, which exceeds the {fit_estimate.prompt_limit_tokens}-token "
                f"limit of a {fit_estimate.slot_tokens}-token slot with its "
                f"registered {fit_estimate.reserve_tokens}-token reserve, the "
                f"{fit_estimate.completion_ceiling}-token completion ceiling and "
                f"the {REGISTERED_SPECIAL_TOKEN_RESERVE}-token special reserve"
            )
    return SupplyVariantGroup(
        arms=tuple(arms), fit_estimate=fit_estimate,
        arm_visits=SUPPLY_VARIANT_ARM_VISITS_INSTRUMENT,
        kind=SUPPLY_VARIANT_KIND_TEMPLATE,
    )


def _decoding_override(
    value: object, *, field: str, locked_decoding: Mapping[str, object] | None,
) -> tuple[tuple[str, float | int], ...]:
    """Parse one arm's ``decoding`` object into its canonical override, fail-closed.

    The object is non-empty and every key is in :data:`DECODING_VARIANT_KNOBS`;
    every value is a finite non-boolean number of the knob's kind inside its
    bounds. A key another axis owns (the seed, the completion cap, the thinking
    budget and switch, the response format, tool authority, slot pinning) is
    refused BY NAME with the axis that owns it. When ``locked_decoding`` is
    given (the node's own request decoding), an override that sets every key to
    the lock's own value is refused: it would be a second spelling of the
    delivering arm.
    """

    if not isinstance(value, Mapping) or not value:
        raise SupplyVariantError(
            f"{field} must be a non-empty object of sampling parameters "
            f"{sorted(DECODING_VARIANT_KNOBS)}"
        )
    for name in sorted(value, key=str):
        if name in DECODING_VARIANT_REFUSED_KNOBS:
            raise SupplyVariantError(
                f"{field} names {name!r}: {DECODING_VARIANT_REFUSED_KNOBS[name]}; a "
                f"decoding arm overrides only {sorted(DECODING_VARIANT_KNOBS)}"
            )
        if name not in DECODING_VARIANT_KNOBS:
            raise SupplyVariantError(
                f"{field} names the unknown sampling parameter {name!r}; the closed "
                f"set is {sorted(DECODING_VARIANT_KNOBS)}"
            )
    out: dict[str, float | int] = {}
    for name in sorted(value):
        number = value[name]
        kind, low, high, low_exclusive = DECODING_VARIANT_KNOBS[name]
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            raise SupplyVariantError(f"{field}.{name} must be a number, got {number!r}")
        if kind == "integer" and not isinstance(number, int):
            raise SupplyVariantError(f"{field}.{name} must be an integer, got {number!r}")
        if isinstance(number, float) and not math.isfinite(number):
            raise SupplyVariantError(f"{field}.{name} must be finite")
        below = number <= low if low_exclusive else number < low
        if below or number > high:
            raise SupplyVariantError(
                f"{field}.{name} is {number!r}, outside "
                f"{'(' if low_exclusive else '['}{low}, {high}]"
            )
        out[name] = number
    if locked_decoding is not None and all(
        name in locked_decoding and locked_decoding[name] == number
        and not isinstance(locked_decoding[name], bool)
        for name, number in out.items()
    ):
        raise SupplyVariantError(
            f"{field} sets every named parameter to the node's own locked value; that "
            "arm is a second spelling of the delivering arm"
        )
    return tuple(sorted(out.items()))


def parse_decoding_variants(
    block: object,
    *,
    role_kind: str,
    phase_id: str,
    locked_decoding: Mapping[str, object] | None = None,
) -> SupplyVariantGroup:
    """Parse ``roles.<role>.decoding_variants`` into a decoding-kind group,
    fail-closed (NX-T R4, owner rulings 329 A / 332 A).

    The sibling of :func:`parse_template_variants`: every arm renders the
    delivering arm's own supplied evidence and the node's own locked
    instruction template; a candidate arm differs ONLY in the sampling
    parameters of its own contact. The refusals, each raised by name BEFORE any
    contact:

    1. a block that is not an object with exactly ``node``, ``arms``,
       ``max_supplied_items``, ``fit_estimate`` and ``template_tokens``;
    2. a ``node`` other than the role the block sits on, or a role outside
       :data:`DECODING_VARIANT_NODES`;
    3. a candidate count outside 1..:data:`MAX_DECODING_CANDIDATE_ARMS` (plus the
       delivering arm and at most one twin);
    4. an arm row with an unknown key, or a supply/template knob named as such
       (``overrides``, ``release_swap``, ``knobs``, ``max_supplied_items``,
       ``instruction_template``, ``template_tokens``): the ONLY thing an arm
       overrides is its ``decoding``;
    5. an arm id collision, zero or several delivering arms, a delivering arm
       that is not LAST or that carries a ``decoding`` override, several twins,
       or a twin that is not the delivering arm's;
    6. a candidate arm with a missing, empty, out-of-bounds, mistyped or
       non-closed-set ``decoding`` (see :func:`_decoding_override`), a sampling
       parameter another axis owns, an override equal to the lock's own decoding
       (``locked_decoding``), or two arms with the same override;
    7. an arm whose estimated prompt exceeds the live slot with the registered
       reserve (:class:`SupplyVariantFitEstimate`).
    """

    keys = set(block) if isinstance(block, Mapping) else set()
    if not isinstance(block, Mapping) or keys != DECODING_VARIANT_BLOCK_KEYS:
        raise SupplyVariantError(
            "roles.<role>.decoding_variants must be an object with exactly "
            f"{sorted(DECODING_VARIANT_BLOCK_KEYS)}"
        )
    if role_kind not in DECODING_VARIANT_NODES:
        raise SupplyVariantError(
            f"decoding_variants may sit only at {list(DECODING_VARIANT_NODES)}, "
            f"not the {role_kind!r} role"
        )
    if block["node"] != role_kind:
        raise SupplyVariantError(
            f"decoding_variants names node {block['node']!r} but sits on the "
            f"{role_kind!r} role; a variant is declared on exactly the node it names"
        )
    max_items = _positive_int(
        block["max_supplied_items"], field="decoding_variants.max_supplied_items"
    )
    template_tokens = _positive_int(
        block["template_tokens"], field="decoding_variants.template_tokens"
    )
    rows = block["arms"]
    if (
        not isinstance(rows, Sequence) or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise SupplyVariantError("decoding_variants.arms must be an ordered list of arm objects")
    twins = [row for row in rows if row.get("replicate_of") is not None]
    candidates = len(rows) - len(twins) - 1
    if len(twins) > 1:
        raise SupplyVariantError("decoding_variants admits at most one replicate_of twin")
    if not MIN_DECODING_CANDIDATE_ARMS <= candidates <= MAX_DECODING_CANDIDATE_ARMS:
        raise SupplyVariantError(
            "decoding_variants must declare between "
            f"{MIN_DECODING_CANDIDATE_ARMS} and {MAX_DECODING_CANDIDATE_ARMS} "
            "candidate decoding arms (plus the delivering arm and at most one "
            f"twin); this block declares {max(candidates, 0)}"
        )
    fit_estimate = parse_supply_variant_fit_estimate(block["fit_estimate"])
    arms: list[SupplyVariantArm] = []
    for position, row in enumerate(rows):
        where = f"decoding_variants.arms[{position}]"
        refused = sorted(
            set(row) & (TEMPLATE_VARIANT_REFUSED_KNOB_KEYS | {"instruction_template", "template_tokens"})
        )
        if refused:
            raise SupplyVariantError(
                f"{where} names {refused}: a decoding arm overrides exactly its "
                "sampling parameters and nothing else (no template, no supply knob, "
                "no release swap, no bound of its own)"
            )
        unknown = sorted(set(row) - DECODING_VARIANT_ARM_KEYS)
        if unknown or "arm_id" not in row:
            raise SupplyVariantError(
                f"{where} must carry arm_id plus optional "
                f"{sorted(DECODING_VARIANT_ARM_KEYS - {'arm_id'})}; unknown keys: {unknown}"
            )
        arm_id = _nonempty_str(row["arm_id"], field=f"{where}.arm_id")
        deliver = row.get("deliver", False)
        if not isinstance(deliver, bool):
            raise SupplyVariantError(f"{where}.deliver must be a bool")
        raw_replicate = row.get("replicate_of")
        replicate_of = (
            None if raw_replicate is None
            else _nonempty_str(raw_replicate, field=f"{where}.replicate_of")
        )
        if deliver and replicate_of is not None:
            raise SupplyVariantError(f"{where} declares both deliver: true and replicate_of")
        override = None
        if "decoding" in row:
            if deliver or replicate_of is not None:
                raise SupplyVariantError(
                    f"{where} is the delivering arm or the twin and must declare no "
                    "decoding: it samples exactly as the node's own locked request does, "
                    "so its request is the locked plan's byte for byte"
                )
            override = _decoding_override(
                row["decoding"], field=f"{where}.decoding", locked_decoding=locked_decoding,
            )
        elif not deliver and replicate_of is None:
            raise SupplyVariantError(
                f"{where} is a candidate arm and must declare a decoding override"
            )
        arms.append(SupplyVariantArm(
            arm_id=arm_id, deliver=deliver, knobs=(), max_supplied_items=max_items,
            replicate_of=replicate_of, template_tokens=template_tokens,
            decoding_override=override,
        ))
    ids = [arm.arm_id for arm in arms]
    if len(set(ids)) != len(ids):
        raise SupplyVariantError("decoding_variants arm ids must be distinct")
    delivering = [arm.arm_id for arm in arms if arm.deliver]
    if len(delivering) != 1:
        raise SupplyVariantError(
            "decoding_variants must declare exactly one arm with deliver: true; "
            f"this block declares {len(delivering)}"
        )
    if not arms[-1].deliver:
        raise SupplyVariantError(
            f"decoding_variants delivering arm {delivering[0]!r} must be the LAST arm: "
            "the delivered text is then the group's final contact's own response, so "
            "invariant I7 holds with no new exception"
        )
    for arm in arms:
        if arm.replicate_of is not None and arm.replicate_of != arms[-1].arm_id:
            raise SupplyVariantError(
                f"decoding_variants arm {arm.arm_id!r} names replicate_of "
                f"{arm.replicate_of!r}, which is not the delivering arm {arms[-1].arm_id!r}"
            )
    overrides = [arm.decoding_override for arm in arms if arm.decoding_override is not None]
    if len(set(overrides)) != len(overrides):
        raise SupplyVariantError(
            "two decoding_variants arms declare the same sampling override; two "
            "spellings of one construction spend a contact per row and measure nothing"
        )
    for arm in arms:
        estimated = fit_estimate.estimated_prompt_tokens(arm)
        if estimated > fit_estimate.prompt_limit_tokens:
            raise SupplyVariantError(
                f"decoding_variants arm {arm.arm_id!r} estimates {estimated} prompt "
                f"tokens, which exceeds the {fit_estimate.prompt_limit_tokens}-token "
                f"limit of a {fit_estimate.slot_tokens}-token slot with its "
                f"registered {fit_estimate.reserve_tokens}-token reserve, the "
                f"{fit_estimate.completion_ceiling}-token completion ceiling and "
                f"the {REGISTERED_SPECIAL_TOKEN_RESERVE}-token special reserve"
            )
    return SupplyVariantGroup(
        arms=tuple(arms), fit_estimate=fit_estimate,
        arm_visits=SUPPLY_VARIANT_ARM_VISITS_INSTRUMENT,
        kind=SUPPLY_VARIANT_KIND_DECODING,
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
    template_group: bool = False,
    release_swaps_group: bool = False,
    decoding_group: bool = False,
) -> dict[str, object]:
    """One arm's receipt row: labels, ids and counts, never supplied text.

    ``template_group`` (NX programme E1) selects the v4 row shape: the same
    row plus ``instruction_template`` -- ``None`` for the delivering arm and
    the twin, the declared ``{relpath, sha256}`` for every other arm.

    ``decoding_group`` (NX-T R4) selects the v6 row shape: the v3 row plus
    ``decoding_override`` -- ``None`` for the delivering arm and the twin, the
    declared sampling override (``{name: value}``) for every other arm.

    ``release_swaps_group`` (loop item E-T6) selects the v5 row shape: the v3
    row with ``release_swap`` replaced by ``release_swaps`` -- every declared
    ``{store_id, release}`` of the arm, ordered by store (``[]`` when none).
    """

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
    row = {
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
    if template_group:
        row["instruction_template"] = (
            None if arm.instruction_template is None
            else arm.instruction_template.as_json()
        )
    if release_swaps_group:
        del row["release_swap"]
        row["release_swaps"] = [swap.as_json() for swap in arm.all_release_swaps]
    if decoding_group:
        row["decoding_override"] = arm.decoding
    return row


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
        "schema": group.receipt_schema,
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
#: ``perception_branches``: v2 since 2026-09-29 (a degenerate candidate list
#: is a measured outcome; see ``rails.native_episode_receipt``), the SAME
#: constant the validator owns.
PERCEPTION_BRANCH_RECEIPT_SCHEMA = _RECEIPT_PERCEPTION_BRANCH_RECEIPT_SCHEMA

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
#: The axes a consumption module's admitted delivered policy may set on the
#: delivering branch A (ruling R3; ``parse_perception_branches``'s
#: ``delivering_axes_admitted``). Knobs and release swaps stay refused on A.
DELIVERING_BRANCH_MODULE_AXES = frozenset({"presentation_id", "min_candidates"})
#: Keys one branch row carries. ``branch_id`` and ``max_supplied_items`` are
#: required; every other key is one of the four closed axis categories a
#: non-A, non-T branch declares exactly one of (design section 1, "one factor
#: per non-A branch").
PERCEPTION_BRANCH_REQUIRED_KEYS = frozenset({"branch_id", "max_supplied_items"})
#: ``prepared_seed`` is NOT one of the four axis categories (it names no
#: knob, swap, presentation or contract bound): it is a B branch's own
#: offline-pinned seed artifact, optional at parse time and required only by
#: the ``branch-seed-unpinned`` registration gate.
#: ``key_source`` (2026-09-30, docs/results/2026-09-30-slurp-retrieval-key-
#: recall-offline.md) is a FIFTH axis category: a rendering-only swap of the
#: first phase's retrieval-key pins (``facet_source`` / ``query_source`` /
#: ``agreement_source``) inside the branch's own pre-flight router; see
#: :class:`PerceptionBranchKeySource`.
PERCEPTION_BRANCH_OPTIONAL_KEYS = frozenset({
    "deliver", "overrides", "replicate_of", "release_swap",
    "presentation_id", "min_candidates", "prepared_seed", "contrast_pairs",
    "key_source",
})
#: The exact keys one ``key_source`` block carries: the store whose
#: first-phase ``phase_supply`` the branch re-keys, and one entry per
#: swappable pin (``None`` = keep the cell's own pin).
PERCEPTION_BRANCH_KEY_SOURCE_KEYS = frozenset({"store_id", *PERCEPTION_BRANCH_KEY_SOURCE_FIELDS})
#: The exact keys one swapped source carries: the ``phase_supply`` source
#: shape itself (``rails.phase_supply._SOURCE_KEYS``), so the branch router
#: validates it exactly as it validates the cell's own pin.
PERCEPTION_BRANCH_KEY_SOURCE_PIN_KEYS = frozenset({
    "kind", "relpath", "sha256", "tool_contact_ledger_row", "embedded_signal",
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
    # Schema v2 (2026-09-29): how many intent ids the note listed before the
    # first-occurrence collapse (0 for an empty or malformed note).
    "candidate_intent_ids_raw_count",
    # "What to build" items 2 and 3: a branch's own presentation outcome
    # (None/None when the branch has no presentation_id, or when it does but
    # the renderer added no block -- "no extra content item" and "skipped
    # with a reason" are then the same receipted shape: text absent,
    # skip_reason present) and its own response-contract outcome (None
    # unless the branch declares min_candidates).
    "presentation_skip_reason", "contrast_block_sha256", "min_candidates_met",
    # Schema v3 (2026-09-30): the branch's swapped retrieval-key pins, or None.
    "key_source",
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
class PerceptionBranchKeySource:
    """One B branch's ``key_source`` axis: a swap of the first phase's
    retrieval-key pins inside the branch's OWN pre-flight router.

    RENDERING-ONLY, exactly like the other four axis categories: the branch's
    seed (the boundary ids its Perception request is shown) is built by
    ``core.flight.runtime.FlightRuntime._perception_branch_seeds`` through a
    one-off router whose ``knowledge_stores.<store_id>.phase_supply.<first
    phase>`` carries the swapped ``facet_source`` / ``query_source`` /
    ``agreement_source`` pins; the store, its release, its snapshot and every
    delivered body are unchanged, and A and T never see the swap (AT-P1/P2).

    Each swapped source is the full ``phase_supply`` source object (``kind``,
    ``relpath``, ``sha256``, ``tool_contact_ledger_row``, ``embedded_signal``)
    so the branch router validates it exactly as it validates the cell's own
    pin (a swapped ``query_source`` must still declare a speech modality). A
    ``None`` entry keeps the cell's own pin.
    """

    store_id: str
    facet_source: Mapping[str, object] | None = None
    query_source: Mapping[str, object] | None = None
    agreement_source: Mapping[str, object] | None = None

    def swapped(self) -> dict[str, Mapping[str, object]]:
        """``{field: source}`` for every swapped field, in the fixed field order."""

        return {
            field: getattr(self, field)
            for field in PERCEPTION_BRANCH_KEY_SOURCE_FIELDS
            if getattr(self, field) is not None
        }

    def as_json(self) -> dict[str, object]:
        return {
            "store_id": self.store_id,
            **{
                field: (None if getattr(self, field) is None else dict(getattr(self, field)))
                for field in PERCEPTION_BRANCH_KEY_SOURCE_FIELDS
            },
        }

    def receipt_pins(self) -> dict[str, object]:
        """The receipt's compact form: ``{store_id, <field>: {relpath, sha256} | None}``."""

        return {
            "store_id": self.store_id,
            **{
                field: (
                    None if getattr(self, field) is None
                    else {
                        "relpath": getattr(self, field)["relpath"],
                        "sha256": getattr(self, field)["sha256"],
                    }
                )
                for field in PERCEPTION_BRANCH_KEY_SOURCE_FIELDS
            },
        }


def parse_perception_branch_key_source(
    block: object,
    *,
    field: str,
    declared_stores: Sequence[str] | None = None,
) -> PerceptionBranchKeySource:
    """Parse ONE branch's ``key_source`` block, fail-closed, before any contact.

    Refuses: a block that is not exactly ``{store_id, facet_source,
    query_source, agreement_source}``; an empty or undeclared ``store_id``
    (when ``declared_stores`` is given); a swapped source that is not exactly
    the ``phase_supply`` source shape with a non-empty ``relpath`` and a
    lowercase 64-hex ``sha256``; and a block that swaps ZERO fields (a
    key-source branch that swaps nothing is a second spelling of A). Whether
    each swapped FILE exists and hashes to its pin is checked where it is
    read, at seed preparation (``FlightRuntime._supply_action_router``).
    """

    if not isinstance(block, Mapping) or set(block) != PERCEPTION_BRANCH_KEY_SOURCE_KEYS:
        raise PerceptionBranchError(
            f"{field} must be an object with exactly "
            f"{sorted(PERCEPTION_BRANCH_KEY_SOURCE_KEYS)}"
        )
    store_id = block["store_id"]
    if not isinstance(store_id, str) or not store_id:
        raise PerceptionBranchError(f"{field}.store_id must be a non-empty string")
    if declared_stores is not None and store_id not in set(declared_stores):
        raise PerceptionBranchError(
            f"{field}.store_id {store_id!r} is not a store this configuration "
            f"declares; declared stores are {sorted(set(declared_stores))}"
        )
    sources: dict[str, Mapping[str, object] | None] = {}
    for name in PERCEPTION_BRANCH_KEY_SOURCE_FIELDS:
        source = block[name]
        if source is None:
            sources[name] = None
            continue
        if (
            not isinstance(source, Mapping)
            or set(source) != PERCEPTION_BRANCH_KEY_SOURCE_PIN_KEYS
            or any(
                not isinstance(source[key], str) or not source[key]
                for key in PERCEPTION_BRANCH_KEY_SOURCE_PIN_KEYS
            )
        ):
            raise PerceptionBranchError(
                f"{field}.{name} must be null or exactly "
                f"{sorted(PERCEPTION_BRANCH_KEY_SOURCE_PIN_KEYS)} with non-empty strings"
            )
        _sha256_hex(source["sha256"], field=f"{field}.{name}.sha256")
        sources[name] = {key: source[key] for key in sorted(source)}
    if all(value is None for value in sources.values()):
        raise PerceptionBranchError(
            f"{field} swaps zero retrieval-key pins; a key_source branch must swap at "
            f"least one of {list(PERCEPTION_BRANCH_KEY_SOURCE_FIELDS)}"
        )
    return PerceptionBranchKeySource(store_id=store_id, **sources)


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
    # "What to build" item 1: the pinned, model-free contrast-pair table a
    # ``top2-contrast-v1`` branch's presentation reads, ``{relpath, sha256}``
    # shaped exactly like ``prepared_seed``. Required on (and only on) a
    # branch whose ``presentation_id`` is ``top2-contrast-v1``
    # (``parse_perception_branches`` refuses both directions); ``None`` for
    # every other branch, including A and T, and for every config written
    # before this table existed.
    contrast_pairs: Mapping[str, str] | None = None
    # 2026-09-30: the ``key_source`` axis (:class:`PerceptionBranchKeySource`),
    # ``None`` for A, T and every branch that swaps no retrieval-key pin.
    key_source: PerceptionBranchKeySource | None = None
    # NX programme E1 for the Perception node (2026-10-10): this branch's
    # INSTRUCTION-TEMPLATE override -- the pinned template its Perception
    # contact renders in place of the node's locked one -- or ``None`` for A,
    # T and every branch of the non-template kinds. Written only by
    # :func:`parse_perception_template_variants`.
    instruction_template: "SupplyVariantTemplate | None" = None
    # The measured token count of the template this branch renders; 0 when
    # the branch is not a template branch. Enters only the fit estimate.
    template_tokens: int = 0
    # NX-T R1 (2026-10-13): this branch's per-node THINKING-POLICY override, ``{role kind: {enable_thinking |
    # reasoning_budget_tokens | answer_reserve_tokens}}`` (``core.reasoning_knobs.NODE_POLICY_KEYS``), or ``None`` for A, the twin
    # and every branch of the other kinds. Written only by :func:`parse_perception_thinking_variants`. Declared LAST, so every
    # branch parsed before this field existed composes byte-identically.
    thinking_policy: "Mapping[str, Mapping[str, object]] | None" = None
    # Decision 338 (2026-10-19): the SAMPLING axes -- ``None`` for A, the twin and every branch of the other kinds. Written only
    # by :func:`parse_perception_sampling_variants`. Declared LAST, so every branch parsed before composes byte-identically.
    perception_samples: "PerceptionSamplesAxis | None" = None
    solver_samples: "SolverSamplesAxis | None" = None

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
            "contrast_pairs": (
                None if self.contrast_pairs is None else dict(self.contrast_pairs)
            ),
            "key_source": (
                None if self.key_source is None else self.key_source.as_json()
            ),
            **(
                {} if self.instruction_template is None
                else {"instruction_template": self.instruction_template.as_json()}
            ),
            **(
                {} if self.thinking_policy is None
                else {"thinking_policy": canonical_thinking_policy(self.thinking_policy)}
            ),
            **(
                {} if self.perception_samples is None
                else {"perception_samples": self.perception_samples.as_json()}
            ),
            **(
                {} if self.solver_samples is None
                else {"solver_samples": self.solver_samples.as_json()}
            ),
        }


@dataclass(frozen=True)
class PerceptionBranchGroup:
    """One row's whole Perception branch group: branches in A-last order."""

    branches: tuple[PerceptionBranch, ...]
    fit_estimate: SupplyVariantFitEstimate
    level: int

    @property
    def is_template(self) -> bool:
        """True for a group :func:`parse_perception_template_variants` built:
        every non-A, non-twin branch varies the Perception instruction template
        and nothing else (the receipt then seals as schema v4)."""

        return any(branch.instruction_template is not None for branch in self.branches)

    @property
    def is_thinking(self) -> bool:
        """True for a group :func:`parse_perception_thinking_variants` built: every non-A, non-twin branch varies the per-node
        thinking policy and nothing else (the receipt then seals as schema v5)."""

        return any(branch.thinking_policy is not None for branch in self.branches)

    @property
    def is_sampling(self) -> bool:
        """True for a group :func:`parse_perception_sampling_variants` built: every non-A, non-twin branch fans out Perception
        and/or Solver samples and nothing else (the receipt then seals as schema v6)."""

        return any(
            branch.perception_samples is not None or branch.solver_samples is not None for branch in self.branches
        )

    @property
    def renders_unvaried_evidence(self) -> bool:
        """True when every branch renders the delivering branch's own evidence (a template or a thinking-policy group): no
        branch seed, no presentation, no contract item, and the Solver supply is re-resolved from each branch's own note."""

        return self.is_template or self.is_thinking or self.is_sampling

    @property
    def has_twin(self) -> bool:
        return any(branch.is_twin for branch in self.branches)

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
    def twin_branch(self) -> PerceptionBranch:  # raises when the group declares none (a v5 column may)
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


def parse_perception_template_variants(
    block: object,
    *,
    phase_id: str,
    locked_template: str | None = None,
) -> PerceptionBranchGroup:
    """Parse ``roles.perception.template_variants`` into a LEVEL-2
    Perception branch group whose axis is the instruction template (NX
    programme E1, Perception node, owner decision 239).

    The block, its refusals and its pins are :func:`parse_template_variants`'
    own (``role_kind="perception"``): the same ``node``/``arms``/
    ``max_supplied_items``/``fit_estimate`` shape, 1 to 6 candidate arms, the
    delivering arm LAST and untemplated (invariant I7), template paths under
    ``probes/`` hash-pinned, duplicate and locked-template arms refused. The
    result is the existing Perception branch group at level 2, so each
    candidate arm is one Perception contact plus its own first-visit Solver
    contact (contact term ``base + 2 (K - 1)``), the twin is the within-flight
    A/A, and the receipt, settle logic, bundle invariant and resume are the
    branch mechanism's own. One addition over the Solver form: the twin
    ``replicate_of`` the delivering arm is REQUIRED (an A/A read has no null
    without it).
    """

    group = parse_template_variants(
        block, role_kind="perception", phase_id=phase_id,
        locked_template=locked_template,
    )
    twins = [arm for arm in group.arms if arm.replicate_of is not None]
    if len(twins) != 1:
        raise PerceptionBranchError(
            "perception template_variants must declare exactly one twin "
            "(replicate_of the delivering arm): the within-flight A/A null "
            f"every node-column read requires; this block declares {len(twins)}"
        )
    branches = tuple(
        PerceptionBranch(
            branch_id=arm.arm_id, deliver=arm.deliver, knobs=(),
            max_supplied_items=arm.max_supplied_items,
            replicate_of=arm.replicate_of,
            instruction_template=arm.instruction_template,
            template_tokens=arm.template_tokens,
        )
        for arm in group.arms
    )
    return PerceptionBranchGroup(
        branches=branches, fit_estimate=group.fit_estimate,
        level=PERCEPTION_BRANCH_LEVEL_SOLVER,
    )


#: NX-T R1 (2026-10-13): the thinking-policy column. The block is the template block's shape with ``thinking_policy`` in place
#: of ``instruction_template``; the only knobs an arm may set are ``core.reasoning_knobs.NODE_POLICY_KEYS``, per role kind.
THINKING_VARIANT_BLOCK_KEYS = frozenset({"node", "arms", "max_supplied_items", "fit_estimate"})
THINKING_VARIANT_ARM_KEYS = frozenset({"arm_id", "deliver", "replicate_of", "thinking_policy"})
THINKING_VARIANT_ROLE_KINDS: tuple[str, ...] = ("perception", "solver")
MIN_THINKING_CANDIDATE_ARMS = 1
MAX_THINKING_CANDIDATE_ARMS = 6


def canonical_thinking_policy(policy: Mapping[str, Mapping[str, object]]) -> dict[str, dict[str, object]]:
    """The policy as plain dicts in sorted key order (the form receipts, hashes and ``as_json`` carry)."""

    return {kind: {key: policy[kind][key] for key in sorted(policy[kind])} for kind in sorted(policy)}


def _thinking_policy(value: object, *, field: str) -> dict[str, dict[str, object]]:
    reason = perception_branch_thinking_policy_error(value)
    if reason is not None or value is None:
        raise PerceptionBranchError(f"{field}: {reason or 'a candidate arm must declare a thinking_policy'}")
    return canonical_thinking_policy(value)  # type: ignore[arg-type]


def parse_perception_thinking_variants(block: object, *, phase_id: str) -> PerceptionBranchGroup:
    """Parse ``roles.perception.thinking_variants`` into a LEVEL-2 Perception branch group whose axis is the per-node thinking
    policy (NX-T R1, owner ruling 304; the later budget round uses the same arm kind).

    Same-flight COLUMN over the decoding knobs: every arm renders the delivering arm's own evidence, template and QueryState (no
    seed, no presentation, no template); only the per-node ``enable_thinking`` / ``reasoning_budget_tokens`` /
    ``answer_reserve_tokens`` of the arm's own contacts differ. Each candidate arm is one Perception contact plus its own
    first-visit Solver contact that reads THAT arm's Perception note (contact term ``base + 2 (K - 1)``).

    Refusals, each raised by name before any contact: a block that is not exactly ``node``/``arms``/``max_supplied_items``/
    ``fit_estimate``; a ``node`` other than ``perception``; 1..6 candidate arms; at most one twin (the twin is OPTIONAL here,
    unlike the template kind); an arm key outside ``arm_id``/``deliver``/``replicate_of``/``thinking_policy``; a policy naming
    any other knob or role kind; a candidate without a policy; a delivering arm or twin that declares one; two arms with the
    same policy; a delivering arm that is not last; a twin that is not the delivering arm's; an estimated prompt above the live
    slot limit.
    """

    if not isinstance(block, Mapping) or set(block) != THINKING_VARIANT_BLOCK_KEYS:
        raise PerceptionBranchError(
            "roles.perception.thinking_variants must be an object with exactly "
            f"{sorted(THINKING_VARIANT_BLOCK_KEYS)}"
        )
    if block["node"] != "perception":
        raise PerceptionBranchError(
            f"thinking_variants names node {block['node']!r} but sits on the 'perception' role; a variant is declared on "
            "exactly the node it names"
        )
    max_items = _positive_int(block["max_supplied_items"], field="thinking_variants.max_supplied_items")
    rows = block["arms"]
    if (
        not isinstance(rows, Sequence) or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise PerceptionBranchError("thinking_variants.arms must be an ordered list of arm objects")
    twins = [row for row in rows if row.get("replicate_of") is not None]
    if len(twins) > 1:
        raise PerceptionBranchError("thinking_variants admits at most one replicate_of twin")
    candidates = len(rows) - len(twins) - 1
    if not MIN_THINKING_CANDIDATE_ARMS <= candidates <= MAX_THINKING_CANDIDATE_ARMS:
        raise PerceptionBranchError(
            f"thinking_variants must declare between {MIN_THINKING_CANDIDATE_ARMS} and {MAX_THINKING_CANDIDATE_ARMS} "
            f"candidate policy arms (plus the delivering arm and at most one twin); this block declares {max(candidates, 0)}"
        )
    fit_estimate = parse_supply_variant_fit_estimate(block["fit_estimate"])
    branches: list[PerceptionBranch] = []
    for position, row in enumerate(rows):
        where = f"thinking_variants.arms[{position}]"
        unknown = sorted(set(row) - THINKING_VARIANT_ARM_KEYS)
        if unknown or "arm_id" not in row:
            raise PerceptionBranchError(
                f"{where} must carry arm_id plus optional {sorted(THINKING_VARIANT_ARM_KEYS - {'arm_id'})}; unknown keys: "
                f"{unknown}; a thinking arm overrides the per-node thinking policy and nothing else"
            )
        arm_id = _nonempty_str(row["arm_id"], field=f"{where}.arm_id")
        deliver = row.get("deliver", False)
        if not isinstance(deliver, bool):
            raise PerceptionBranchError(f"{where}.deliver must be a bool")
        raw_replicate = row.get("replicate_of")
        replicate_of = None if raw_replicate is None else _nonempty_str(raw_replicate, field=f"{where}.replicate_of")
        if deliver and replicate_of is not None:
            raise PerceptionBranchError(f"{where} declares both deliver: true and replicate_of")
        policy = None
        if "thinking_policy" in row:
            if deliver or replicate_of is not None:
                raise PerceptionBranchError(
                    f"{where} is the delivering arm or the twin and must declare no thinking_policy: it runs the locked "
                    "form, so its requests are the locked plan's byte for byte"
                )
            policy = _thinking_policy(row["thinking_policy"], field=f"{where}.thinking_policy")
        elif not deliver and replicate_of is None:
            raise PerceptionBranchError(f"{where} is a candidate arm and must declare a thinking_policy")
        branches.append(PerceptionBranch(
            branch_id=arm_id, deliver=deliver, knobs=(), max_supplied_items=max_items,
            replicate_of=replicate_of, thinking_policy=policy,
        ))
    ids = [branch.branch_id for branch in branches]
    if len(set(ids)) != len(ids):
        raise PerceptionBranchError("thinking_variants arm ids must be distinct")
    delivering = [branch.branch_id for branch in branches if branch.deliver]
    if len(delivering) != 1:
        raise PerceptionBranchError(
            f"thinking_variants must declare exactly one arm with deliver: true; this block declares {len(delivering)}"
        )
    if not branches[-1].deliver:
        raise PerceptionBranchError(
            f"thinking_variants delivering arm {delivering[0]!r} must be the LAST arm: the delivered text is then the group's "
            "final contact's own response, so invariant I7 holds with no new exception"
        )
    for branch in branches:
        if branch.replicate_of is not None and branch.replicate_of != branches[-1].branch_id:
            raise PerceptionBranchError(
                f"thinking_variants arm {branch.branch_id!r} names replicate_of {branch.replicate_of!r}, which is not the "
                f"delivering arm {branches[-1].branch_id!r}"
            )
    policies = [json.dumps(canonical_thinking_policy(b.thinking_policy), sort_keys=True) for b in branches if b.thinking_policy]
    if len(set(policies)) != len(policies):
        raise PerceptionBranchError(
            "two thinking_variants arms declare the same policy; two spellings of one configuration spend a contact per row "
            "and measure nothing"
        )
    for branch in branches:
        estimated = fit_estimate.base_prompt_tokens + branch.max_supplied_items * fit_estimate.tokens_per_supplied_item
        if estimated > fit_estimate.prompt_limit_tokens:
            raise PerceptionBranchError(
                f"thinking_variants arm {branch.branch_id!r} estimates {estimated} prompt tokens, which exceeds the "
                f"{fit_estimate.prompt_limit_tokens}-token limit of a {fit_estimate.slot_tokens}-token slot with its "
                f"registered {fit_estimate.reserve_tokens}-token reserve, the {fit_estimate.completion_ceiling}-token "
                f"completion ceiling and the {REGISTERED_SPECIAL_TOKEN_RESERVE}-token special reserve"
            )
    return PerceptionBranchGroup(
        branches=tuple(branches), fit_estimate=fit_estimate, level=PERCEPTION_BRANCH_LEVEL_SOLVER,
    )


#: Decision 338 (2026-10-19): the SAMPLING column. A branch of a ``roles.perception.sampling_variants`` group declares one or
#: both of two fan-out axes -- ``perception_samples`` (k Perception contacts over the same packet, merged into the shortlist
#: its branch Solver contact reads) and ``solver_samples`` (n Solver contacts committed into the branch's delivered answer).
#: Sample 0 is greedy at the lock seed; samples 1..n-1 sample at the axis's ``decoding`` with seed = lock seed + offset. The
#: delivering branch and the twin run the locked form and declare neither axis, so any delivery-time rule (the v4g
#: normaliser) stays scoped to the delivering branch alone.
SAMPLING_VARIANT_BLOCK_KEYS = frozenset({"node", "arms", "max_supplied_items", "fit_estimate"})
SAMPLING_VARIANT_ARM_KEYS = frozenset({"arm_id", "deliver", "replicate_of", *SAMPLING_AXES})
SAMPLING_VARIANT_KIND_PERCEPTION = "perception-sampling"
SAMPLING_VARIANT_KIND_SOLVER = "solver-sampling"
SAMPLING_VARIANT_KINDS = (SAMPLING_VARIANT_KIND_PERCEPTION, SAMPLING_VARIANT_KIND_SOLVER)
#: The sampling parameters a sampling axis may set: ``DECODING_VARIANT_KNOBS`` narrowed to what the R4 ``decoding_variants``
#: kind bounds for the Thinking core (``presence_penalty`` is refused by name).
SAMPLING_DECODING_NAMES = frozenset({"temperature", "top_p", "top_k"})
MIN_PERCEPTION_SAMPLES, MAX_PERCEPTION_SAMPLES = 2, 4
MIN_SOLVER_SAMPLES, MAX_SOLVER_SAMPLES = 2, 8
MAX_SAMPLING_SEED_OFFSET = 10_000
MAX_SAMPLING_CAP = 8
MIN_SAMPLING_CANDIDATE_ARMS, MAX_SAMPLING_CANDIDATE_ARMS = 1, 6
PERCEPTION_SAMPLES_KEYS = frozenset({"k", "decoding", "merge_policy", "cap"})
PERCEPTION_SAMPLES_OPTIONAL_KEYS = frozenset({"seed_offsets"})
SOLVER_SAMPLES_KEYS = frozenset({"n", "decoding", "commit"})
SOLVER_SAMPLES_OPTIONAL_KEYS = frozenset({"greedy_first", "seed_offsets"})
SOLVER_COMMIT_REQUIRED_KEYS = frozenset({"policy", "min_support", "similarity_threshold"})
SOLVER_COMMIT_GATE_KEYS = frozenset({"n1_min", "empty_votes_min"})


def derive_sample_seeds(lock_seed: int, seed_offsets: Sequence[int]) -> tuple[int, ...]:
    """The fixed per-sample seeds of a sampling axis: sample 0 runs greedy at the lock seed, sample i at lock seed + offset i."""

    if isinstance(lock_seed, bool) or not isinstance(lock_seed, int) or lock_seed < 0:
        raise PerceptionBranchError("the lock seed must be a non-negative integer")
    return (lock_seed, *(lock_seed + int(offset) for offset in seed_offsets))


def _sampling_decoding(value: object, *, field: str) -> tuple[tuple[str, float | int], ...]:
    try:
        override = _decoding_override(value, field=field, locked_decoding=None)
    except PerceptionBranchError:
        raise
    except SupplyVariantError as error:
        raise PerceptionBranchError(str(error)) from error
    names = {name for name, _number in override}
    extra = sorted(names - SAMPLING_DECODING_NAMES)
    if extra:
        raise PerceptionBranchError(
            f"{field} names {extra}: a sampling axis sets only {sorted(SAMPLING_DECODING_NAMES)} (the bounds the R4 "
            "decoding_variants kind admits)"
        )
    if dict(override).get("temperature", 0) <= 0:
        raise PerceptionBranchError(f"{field} must set a positive temperature: samples 1..n-1 are drawn, not greedy")
    return override


def _sampling_seed_offsets(value: object, *, count: int, field: str) -> tuple[int, ...]:
    if value is None:
        return tuple(range(1, count))
    if (
        not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != count - 1
        or any(isinstance(item, bool) or not isinstance(item, int) or not 1 <= item <= MAX_SAMPLING_SEED_OFFSET for item in value)
        or len(set(value)) != len(value)
    ):
        raise PerceptionBranchError(
            f"{field} must be {count - 1} distinct integers from 1 to {MAX_SAMPLING_SEED_OFFSET} (the offsets of samples "
            "1..n-1; sample 0 runs at the lock seed)"
        )
    return tuple(int(item) for item in value)


@dataclass(frozen=True)
class PerceptionSamplesAxis:
    """``perception_samples``: k Perception contacts merged by a registered merge policy."""

    k: int
    decoding: tuple[tuple[str, float | int], ...]
    seed_offsets: tuple[int, ...]
    merge_policy: str
    cap: int

    def as_json(self) -> dict[str, object]:
        return {
            "k": self.k, "decoding": dict(self.decoding), "seed_offsets": list(self.seed_offsets),
            "merge_policy": self.merge_policy, "cap": self.cap,
        }

    @property
    def extra_contacts(self) -> int:
        return self.k - 1


@dataclass(frozen=True)
class SolverSamplesAxis:
    """``solver_samples``: n Solver contacts committed by a registered commit policy."""

    n: int
    decoding: tuple[tuple[str, float | int], ...]
    seed_offsets: tuple[int, ...]
    commit_policy: str
    min_support: int
    similarity_threshold: float
    n1_min: float | None = None
    empty_votes_min: int | None = None
    greedy_first: bool = True

    def commit_json(self) -> dict[str, object]:
        return {
            "policy": self.commit_policy, "min_support": self.min_support,
            "similarity_threshold": self.similarity_threshold, "n1_min": self.n1_min,
            "empty_votes_min": self.empty_votes_min,
        }

    def as_json(self) -> dict[str, object]:
        return {
            "n": self.n, "greedy_first": self.greedy_first, "decoding": dict(self.decoding),
            "seed_offsets": list(self.seed_offsets), "commit": self.commit_json(),
        }

    @property
    def extra_contacts(self) -> int:
        return self.n - 1


def parse_perception_samples(value: object, *, field: str) -> PerceptionSamplesAxis:
    """Parse one branch's ``perception_samples`` block, fail-closed."""

    if (
        not isinstance(value, Mapping)
        or not PERCEPTION_SAMPLES_KEYS <= set(value)
        or set(value) - PERCEPTION_SAMPLES_KEYS - PERCEPTION_SAMPLES_OPTIONAL_KEYS
    ):
        raise PerceptionBranchError(
            f"{field} must be an object with {sorted(PERCEPTION_SAMPLES_KEYS)} and optionally "
            f"{sorted(PERCEPTION_SAMPLES_OPTIONAL_KEYS)}"
        )
    k = value["k"]
    if isinstance(k, bool) or not isinstance(k, int) or not MIN_PERCEPTION_SAMPLES <= k <= MAX_PERCEPTION_SAMPLES:
        raise PerceptionBranchError(f"{field}.k must be an integer from {MIN_PERCEPTION_SAMPLES} to {MAX_PERCEPTION_SAMPLES}")
    cap = value["cap"]
    if isinstance(cap, bool) or not isinstance(cap, int) or not 1 <= cap <= MAX_SAMPLING_CAP:
        raise PerceptionBranchError(f"{field}.cap must be an integer from 1 to {MAX_SAMPLING_CAP}")
    policy_id = _nonempty_str(value["merge_policy"], field=f"{field}.merge_policy")
    # Function-local: importing the registering module is what populates the registry.
    from . import perception_merge_policies as _merge_policies  # noqa: PLC0415, F401
    from ..core.base import PERCEPTION_MERGE_POLICIES, CoreError  # noqa: PLC0415

    try:
        PERCEPTION_MERGE_POLICIES.resolve(policy_id)
    except CoreError as error:
        raise PerceptionBranchError(f"{field}.merge_policy is invalid: {error}") from error
    return PerceptionSamplesAxis(
        k=k, decoding=_sampling_decoding(value["decoding"], field=f"{field}.decoding"),
        seed_offsets=_sampling_seed_offsets(value.get("seed_offsets"), count=k, field=f"{field}.seed_offsets"),
        merge_policy=policy_id, cap=cap,
    )


def parse_solver_samples(value: object, *, field: str) -> SolverSamplesAxis:
    """Parse one branch's ``solver_samples`` block, fail-closed."""

    if (
        not isinstance(value, Mapping)
        or not SOLVER_SAMPLES_KEYS <= set(value)
        or set(value) - SOLVER_SAMPLES_KEYS - SOLVER_SAMPLES_OPTIONAL_KEYS
    ):
        raise PerceptionBranchError(
            f"{field} must be an object with {sorted(SOLVER_SAMPLES_KEYS)} and optionally "
            f"{sorted(SOLVER_SAMPLES_OPTIONAL_KEYS)}"
        )
    n = value["n"]
    if isinstance(n, bool) or not isinstance(n, int) or not MIN_SOLVER_SAMPLES <= n <= MAX_SOLVER_SAMPLES:
        raise PerceptionBranchError(f"{field}.n must be an integer from {MIN_SOLVER_SAMPLES} to {MAX_SOLVER_SAMPLES}")
    if value.get("greedy_first", True) is not True:
        raise PerceptionBranchError(
            f"{field}.greedy_first must be true: the first-support commit keeps sample 0's labels, and sample 0 is the "
            "greedy contact at the lock seed"
        )
    commit = value["commit"]
    if (
        not isinstance(commit, Mapping) or not SOLVER_COMMIT_REQUIRED_KEYS <= set(commit)
        or set(commit) - SOLVER_COMMIT_REQUIRED_KEYS - SOLVER_COMMIT_GATE_KEYS
    ):
        raise PerceptionBranchError(
            f"{field}.commit must carry {sorted(SOLVER_COMMIT_REQUIRED_KEYS)} and optionally the gate "
            f"{sorted(SOLVER_COMMIT_GATE_KEYS)}"
        )
    policy_id = _nonempty_str(commit["policy"], field=f"{field}.commit.policy")
    from . import commit_policies as _commit_policies  # noqa: PLC0415
    from ..core.base import COMMIT_POLICIES, CoreError  # noqa: PLC0415

    try:
        COMMIT_POLICIES.resolve(policy_id)
    except CoreError as error:
        raise PerceptionBranchError(f"{field}.commit.policy is invalid: {error}") from error
    min_support = commit["min_support"]
    if isinstance(min_support, bool) or not isinstance(min_support, int) or not 1 <= min_support <= n:
        raise PerceptionBranchError(f"{field}.commit.min_support must be an integer from 1 to n")
    similarity = commit["similarity_threshold"]
    if isinstance(similarity, bool) or not isinstance(similarity, (int, float)) or not 0 < similarity <= 1:
        raise PerceptionBranchError(f"{field}.commit.similarity_threshold must be in (0, 1]")
    gate_given = set(commit) & SOLVER_COMMIT_GATE_KEYS
    n1_min = empty_votes_min = None
    if gate_given:
        if gate_given != SOLVER_COMMIT_GATE_KEYS:
            raise PerceptionBranchError(f"{field}.commit declares half a gate: n1_min and empty_votes_min come together")
        if policy_id != _commit_policies.FIRST_SUPPORT_V1:
            raise PerceptionBranchError(
                f"{field}.commit.policy {policy_id!r} takes no gate; only {_commit_policies.FIRST_SUPPORT_V1!r} does"
            )
        n1_min, empty_votes_min = commit["n1_min"], commit["empty_votes_min"]
        if isinstance(n1_min, bool) or not isinstance(n1_min, (int, float)) or not 0 <= n1_min <= 1:
            raise PerceptionBranchError(f"{field}.commit.n1_min must be in [0, 1]")
        if isinstance(empty_votes_min, bool) or not isinstance(empty_votes_min, int) or not 1 <= empty_votes_min <= n - 1:
            raise PerceptionBranchError(f"{field}.commit.empty_votes_min must be an integer from 1 to n - 1")
    return SolverSamplesAxis(
        n=n, decoding=_sampling_decoding(value["decoding"], field=f"{field}.decoding"),
        seed_offsets=_sampling_seed_offsets(value.get("seed_offsets"), count=n, field=f"{field}.seed_offsets"),
        commit_policy=policy_id, min_support=min_support, similarity_threshold=similarity,
        n1_min=n1_min, empty_votes_min=empty_votes_min,
    )


def sampling_extra_contacts(group: PerceptionBranchGroup) -> int:
    """The extra model contacts a sampling group spends per row beyond the level-2 base term: (k - 1) Perception contacts for
    every ``perception_samples`` branch plus (n - 1) Solver contacts for every ``solver_samples`` branch. Zero otherwise."""

    total = 0
    for branch in group.branches:
        if branch.perception_samples is not None:
            total += branch.perception_samples.extra_contacts
        if branch.solver_samples is not None:
            total += branch.solver_samples.extra_contacts
    return total


def perception_contact_slots(group: PerceptionBranchGroup) -> tuple[tuple[int, int | None], ...]:
    """The ordered Perception-phase contact slots of one visit: ``(branch_index, sample_index)``.

    A branch without a ``perception_samples`` axis owns one slot whose sample index is ``None`` (the unsampled contact every
    other branch group makes). A ``perception_samples`` branch owns ``k`` consecutive slots, sample indices ``0..k-1``. The
    flat slot list is the order the Perception node invokes its contacts in, so a node-global contact index maps to its slot.
    """

    slots: list[tuple[int, int | None]] = []
    for index, branch in enumerate(group.branches):
        axis = branch.perception_samples
        if axis is None:
            slots.append((index, None))
        else:
            slots.extend((index, sample) for sample in range(axis.k))
    return tuple(slots)


def solver_contact_slots(group: PerceptionBranchGroup) -> tuple[tuple[int, int | None], ...]:
    """The ordered first-visit Solver contact slots of a level-2 group: ``(branch_index, sample_index)``, ``n`` consecutive
    slots for a ``solver_samples`` branch and one unsampled slot (``None``) for every other branch."""

    slots: list[tuple[int, int | None]] = []
    for index, branch in enumerate(group.branches):
        axis = branch.solver_samples
        if axis is None:
            slots.append((index, None))
        else:
            slots.extend((index, sample) for sample in range(axis.n))
    return tuple(slots)


def sampling_decoding_table(group: PerceptionBranchGroup, *, perception_phase_id: str, solver_phase_id: str) -> dict[str, dict[str, dict[str, object]]]:
    """``{branch_id: {role phase id: {"decoding": {...}, "seed_offsets": [...]}}}`` for the request adapter. Empty for a group
    that declares no sampling axis (every adapter written before decision 338 then composes the requests it always did)."""

    table: dict[str, dict[str, dict[str, object]]] = {}
    for branch in group.branches:
        entry: dict[str, dict[str, object]] = {}
        if branch.perception_samples is not None:
            axis = branch.perception_samples
            entry[perception_phase_id] = {"decoding": dict(axis.decoding), "seed_offsets": list(axis.seed_offsets)}
        if branch.solver_samples is not None:
            axis = branch.solver_samples
            entry[solver_phase_id] = {"decoding": dict(axis.decoding), "seed_offsets": list(axis.seed_offsets)}
        if entry:
            table[branch.branch_id] = entry
    return table


def parse_perception_sampling_variants(block: object, *, phase_id: str) -> PerceptionBranchGroup:
    """Parse ``roles.perception.sampling_variants`` into a LEVEL-2 Perception branch group whose axes are the sampling fan-outs
    (decision 338, levers L1 and L2).

    The block mirrors ``thinking_variants``: ``node`` (``perception``), ``arms``, ``max_supplied_items``, ``fit_estimate``.
    Every candidate arm declares ``perception_samples``, ``solver_samples`` or both (one fan-out per node, so each key at most
    once). The delivering arm is LAST and declares no axis; exactly one twin ``replicate_of`` the delivering arm is REQUIRED (the
    within-flight A/A every node-column read needs). 1..6 candidate arms; two arms with the same axes are refused.
    """

    if not isinstance(block, Mapping) or set(block) != SAMPLING_VARIANT_BLOCK_KEYS:
        raise PerceptionBranchError(
            "roles.perception.sampling_variants must be an object with exactly "
            f"{sorted(SAMPLING_VARIANT_BLOCK_KEYS)}"
        )
    if block["node"] != "perception":
        raise PerceptionBranchError(
            f"sampling_variants names node {block['node']!r} but sits on the 'perception' role"
        )
    max_items = _positive_int(block["max_supplied_items"], field="sampling_variants.max_supplied_items")
    rows = block["arms"]
    if (
        not isinstance(rows, Sequence) or isinstance(rows, (str, bytes))
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        raise PerceptionBranchError("sampling_variants.arms must be an ordered list of arm objects")
    twins = [row for row in rows if row.get("replicate_of") is not None]
    if len(twins) != 1:
        raise PerceptionBranchError(
            "sampling_variants must declare exactly one twin (replicate_of the delivering arm): the within-flight A/A "
            f"null the column read requires; this block declares {len(twins)}"
        )
    candidates = len(rows) - len(twins) - 1
    if not MIN_SAMPLING_CANDIDATE_ARMS <= candidates <= MAX_SAMPLING_CANDIDATE_ARMS:
        raise PerceptionBranchError(
            f"sampling_variants must declare between {MIN_SAMPLING_CANDIDATE_ARMS} and {MAX_SAMPLING_CANDIDATE_ARMS} "
            f"candidate arms (plus the delivering arm and the twin); this block declares {max(candidates, 0)}"
        )
    fit_estimate = parse_supply_variant_fit_estimate(block["fit_estimate"])
    branches: list[PerceptionBranch] = []
    for position, row in enumerate(rows):
        where = f"sampling_variants.arms[{position}]"
        unknown = sorted(set(row) - SAMPLING_VARIANT_ARM_KEYS)
        if unknown or "arm_id" not in row:
            raise PerceptionBranchError(
                f"{where} must carry arm_id plus optional {sorted(SAMPLING_VARIANT_ARM_KEYS - {'arm_id'})}; unknown keys: "
                f"{unknown}; a sampling arm declares the sampling axes and no other axis"
            )
        arm_id = _nonempty_str(row["arm_id"], field=f"{where}.arm_id")
        deliver = row.get("deliver", False)
        if not isinstance(deliver, bool):
            raise PerceptionBranchError(f"{where}.deliver must be a bool")
        raw_replicate = row.get("replicate_of")
        replicate_of = None if raw_replicate is None else _nonempty_str(raw_replicate, field=f"{where}.replicate_of")
        if deliver and replicate_of is not None:
            raise PerceptionBranchError(f"{where} declares both deliver: true and replicate_of")
        axes = [name for name in SAMPLING_AXES if name in row]
        perception_axis = solver_axis = None
        if deliver or replicate_of is not None:
            if axes:
                raise PerceptionBranchError(
                    f"{where} is the delivering arm or the twin and must declare no sampling axis: it runs the locked "
                    "form, so delivery-time rules apply to it alone"
                )
        else:
            if not axes:
                raise PerceptionBranchError(
                    f"{where} is a candidate arm and must declare perception_samples, solver_samples or both"
                )
            if "perception_samples" in row:
                perception_axis = parse_perception_samples(row["perception_samples"], field=f"{where}.perception_samples")
            if "solver_samples" in row:
                solver_axis = parse_solver_samples(row["solver_samples"], field=f"{where}.solver_samples")
        branches.append(PerceptionBranch(
            branch_id=arm_id, deliver=deliver, knobs=(), max_supplied_items=max_items,
            replicate_of=replicate_of, perception_samples=perception_axis, solver_samples=solver_axis,
        ))
    ids = [branch.branch_id for branch in branches]
    if len(set(ids)) != len(ids):
        raise PerceptionBranchError("sampling_variants arm ids must be distinct")
    delivering = [branch.branch_id for branch in branches if branch.deliver]
    if len(delivering) != 1:
        raise PerceptionBranchError(
            f"sampling_variants must declare exactly one arm with deliver: true; this block declares {len(delivering)}"
        )
    if not branches[-1].deliver:
        raise PerceptionBranchError(
            f"sampling_variants delivering arm {delivering[0]!r} must be the LAST arm: the delivered text is then the "
            "group's final contact's own response, so invariant I7 holds with no new exception"
        )
    for branch in branches:
        if branch.replicate_of is not None and branch.replicate_of != branches[-1].branch_id:
            raise PerceptionBranchError(
                f"sampling_variants arm {branch.branch_id!r} names replicate_of {branch.replicate_of!r}, which is not the "
                f"delivering arm {branches[-1].branch_id!r}"
            )
    signatures = [
        json.dumps(
            [None if b.perception_samples is None else b.perception_samples.as_json(),
             None if b.solver_samples is None else b.solver_samples.as_json()],
            sort_keys=True,
        )
        for b in branches if b.perception_samples is not None or b.solver_samples is not None
    ]
    if len(set(signatures)) != len(signatures):
        raise PerceptionBranchError(
            "two sampling_variants arms declare the same axes; two spellings of one configuration spend contacts per row "
            "and measure nothing"
        )
    for branch in branches:
        estimated = fit_estimate.base_prompt_tokens + branch.max_supplied_items * fit_estimate.tokens_per_supplied_item
        if estimated > fit_estimate.prompt_limit_tokens:
            raise PerceptionBranchError(
                f"sampling_variants arm {branch.branch_id!r} estimates {estimated} prompt tokens, which exceeds the "
                f"{fit_estimate.prompt_limit_tokens}-token limit of a {fit_estimate.slot_tokens}-token slot"
            )
    return PerceptionBranchGroup(
        branches=tuple(branches), fit_estimate=fit_estimate, level=PERCEPTION_BRANCH_LEVEL_SOLVER,
    )


def sampling_stream_record(
    axis: "PerceptionSamplesAxis | SolverSamplesAxis",
    *,
    lock_seed: int,
    samples: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """The per-sample rows of a sampling record: the caller supplies each contact's identity, hashes and parse result; this
    adds the sample index, the derived seed and the override (``None`` for greedy sample 0)."""

    seeds = derive_sample_seeds(lock_seed, axis.seed_offsets)
    count = len(seeds)
    if len(samples) != count:
        raise PerceptionBranchError(f"a sampling record needs exactly {count} samples, got {len(samples)}")
    rows: list[dict[str, object]] = []
    for index, sample in enumerate(samples):
        rows.append({
            "sample_index": index, "seed": seeds[index],
            "override": None if index == 0 else dict(axis.decoding),
            **{key: sample[key] for key in sorted(sample)},
        })
    return rows


def perception_samples_record(
    axis: PerceptionSamplesAxis, *, lock_seed: int, samples: Sequence[Mapping[str, object]], outcome: object,
) -> dict[str, object]:
    """``sampling["perception_samples"]`` of a v6 row. ``samples`` carry ``contact_id``, ``request_sha256``,
    ``response_text_sha256``, ``note_parse_status`` and ``candidate_intent_ids``; ``outcome`` is the
    ``rails.perception_merge_policies.MergeOutcome`` of the merge."""

    seeds = derive_sample_seeds(lock_seed, axis.seed_offsets)
    return {
        "k": axis.k, "decoding": dict(axis.decoding), "seed_offsets": list(axis.seed_offsets), "seeds": list(seeds),
        "samples": sampling_stream_record(axis, lock_seed=lock_seed, samples=samples),
        "merge_policy": axis.merge_policy, "cap": axis.cap,
        "support_counts": [
            {"intent_id": intent_id, "support": support, "best_rank": rank}
            for (intent_id, support), (_same, rank) in zip(outcome.support_counts, outcome.best_ranks)
        ],
        "merged_candidate_ids": list(outcome.merged_candidate_ids),
        "appended_candidate_ids": list(outcome.appended_candidate_ids),
    }


def solver_samples_record(
    axis: SolverSamplesAxis, *, lock_seed: int, samples: Sequence[Mapping[str, object]], outcome: object,
) -> dict[str, object]:
    """``sampling["solver_samples"]`` of a v6 row. ``samples`` carry ``contact_id``, ``request_sha256``,
    ``response_text_sha256`` and ``parse_status``; ``outcome`` is the ``rails.commit_policies.CommitOutcome``."""

    seeds = derive_sample_seeds(lock_seed, axis.seed_offsets)
    return {
        "n": axis.n, "greedy_first": axis.greedy_first, "decoding": dict(axis.decoding),
        "seed_offsets": list(axis.seed_offsets), "seeds": list(seeds),
        "samples": sampling_stream_record(axis, lock_seed=lock_seed, samples=samples),
        "commit": axis.commit_json(),
        "outcome": {
            "intent_support": outcome.intent_support,
            "entity_supports": [{"type": e.type, "support": e.support} for e in outcome.entities],
            "delivered_entity_count": len(outcome.entities),
            "gate": None if outcome.gate is None else dict(outcome.gate),
        },
    }


def merge_perception_samples(axis: PerceptionSamplesAxis, texts: Sequence[str | None]):
    """The merge outcome of one branch's k Perception sample notes (``None`` = a sample that produced no note text).

    The ONE derivation the live runner, the resume replay and the bundle verifier all apply, so a sealed merge can always be
    re-derived from the trace's own recorded response texts.
    """

    from ..core.base import PERCEPTION_MERGE_POLICIES  # noqa: PLC0415
    from . import perception_merge_policies as _merge_policies  # noqa: PLC0415, F401
    from .native_episode_receipt import PERCEPTION_BRANCH_NOTE_MALFORMED  # noqa: PLC0415

    if len(texts) != axis.k:
        raise PerceptionBranchError(f"a perception_samples merge needs exactly {axis.k} sample notes, got {len(texts)}")
    lists: list[list[str] | None] = []
    for text in texts:
        if text is None:
            lists.append(None)
            continue
        status, ids, _raw = parse_perception_branch_note(text)
        lists.append(None if status == PERCEPTION_BRANCH_NOTE_MALFORMED else list(ids))
    return PERCEPTION_MERGE_POLICIES.resolve(axis.merge_policy)(lists, cap=axis.cap)


def solver_sample_parse_status(text: str | None, *, finite_reason: str | None = None) -> str:
    """``ok`` / ``malformed`` for a Solver sample's raw text; ``finite-completion:<reason>`` for a sample that ended on one."""

    if finite_reason is not None:
        return f"finite-completion:{finite_reason}"
    from ..reproduction.ojw.native_group_solver import parse_solver_answer_text  # noqa: PLC0415

    return "ok" if text is not None and parse_solver_answer_text(text) is not None else "malformed"


def commit_solver_samples(axis: SolverSamplesAxis, texts: Sequence[str | None], *, n1: float | None = None):
    """The commit outcome of one branch's n Solver samples (``None`` = no text: a sample that ended on a finite completion).

    ``n1`` is the entity-free share of the supplied exemplars; it is unavailable in flight (the run declares no N1 source), so
    a configured gate reports ``n1-unavailable`` and does not fire. The ONE derivation shared by the runner, the replay and the
    bundle verifier.
    """

    from ..core.base import COMMIT_POLICIES  # noqa: PLC0415
    from ..reproduction.ojw.native_group_solver import parse_solver_answer_text  # noqa: PLC0415
    from . import commit_policies as _commit_policies  # noqa: PLC0415

    if len(texts) != axis.n:
        raise PerceptionBranchError(f"a solver_samples commit needs exactly {axis.n} sample answers, got {len(texts)}")
    votes = [
        _commit_policies.SolverSampleVote(
            sample_index=index, parsed=None if text is None else parse_solver_answer_text(text),
        )
        for index, text in enumerate(texts)
    ]
    policy = COMMIT_POLICIES.resolve(axis.commit_policy)
    kwargs: dict[str, object] = {
        "min_support": axis.min_support, "similarity_threshold": axis.similarity_threshold,
    }
    if axis.commit_policy == _commit_policies.FIRST_SUPPORT_V1:
        kwargs.update(n1=n1, n1_min=axis.n1_min, empty_votes_min=axis.empty_votes_min)
    return policy(votes, **kwargs)


def _sampling_record_matches_axes(branch: PerceptionBranch, sampling: Mapping[str, object]) -> str | None:
    """Why a v6 ``sampling`` value disagrees with the axes ``branch`` declared, or ``None``."""

    declared = {"perception_samples": branch.perception_samples, "solver_samples": branch.solver_samples}
    for name, axis in declared.items():
        record = sampling.get(name)
        if (axis is None) != (record is None):
            return f"the {name} record and the branch's declared {name} axis disagree"
        if axis is None:
            continue
        count_key = "k" if name == "perception_samples" else "n"
        if (
            record[count_key] != getattr(axis, count_key) or record["decoding"] != dict(axis.decoding)
            or record["seed_offsets"] != list(axis.seed_offsets)
        ):
            return f"the {name} record differs from the count, decoding or seed offsets the branch declared"
        if name == "perception_samples" and (
            record["merge_policy"] != axis.merge_policy or record["cap"] != axis.cap
        ):
            return "the perception_samples record differs from the merge policy or cap the branch declared"
        if name == "solver_samples" and record["commit"] != axis.commit_json():
            return "the solver_samples record differs from the commit the branch declared"
    return None


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
    top2_contrast_presentation_id: str | None = None,
    delivering_axes_admitted: Sequence[str] = (),
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
    upper check beyond "positive integer". ``top2_contrast_presentation_id``
    is ``rails.perception_presentations.TOP2_CONTRAST_PRESENTATION_ID`` --
    passed in by name for the same reason ``registered_presentation_ids`` is
    (this module does not import that registering module either); a caller
    that omits it gets no coupling check between ``presentation_id`` and
    ``contrast_pairs`` beyond each field's own shape.

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
        registered reserve;
    16. a malformed ``contrast_pairs`` pin (not exactly ``{relpath, sha256}``,
        with sha256 a lowercase 64-hex SHA-256);
    17. a branch whose ``presentation_id`` equals ``top2_contrast_
        presentation_id`` and carries no ``contrast_pairs``, or a branch
        whose ``presentation_id`` differs (including ``None``) and carries
        one anyway, when ``top2_contrast_presentation_id`` is given;
    18. ``contrast_pairs`` on A or its twin T (like ``prepared_seed``,
        neither may carry a branch-owned pin);
    19. a malformed ``key_source`` block, one naming an undeclared store, or
        one that swaps zero pins (:func:`parse_perception_branch_key_source`);
    20. ``key_source`` on A or its twin T (refusals 6/7: neither declares an
        axis -- AT-P1/P2 hold because A and T never see a swapped key).

    ``key_source`` counts as ONE axis category (refusal 13) however many of
    its three pins it swaps, exactly as a knob tuple does.

    ``delivering_axes_admitted`` (evidence-consumption module, migration
    step 4, coordinator ruling R3) lifts refusal 6 for exactly the named
    axes -- a subset of :data:`DELIVERING_BRANCH_MODULE_AXES` -- on A only:
    the module's own delivered Perception policy may carry an ADMITTED
    presentation (with its ``contrast_pairs`` pin) or response contract. The
    twin T still declares no axis and resolves A's request, axes included.
    Only ``rails.native_episode_config`` passes it, and only for a config
    whose declared ``native_episode.consumption_module`` compiles those axes
    onto A; a hand-written block (the default ``()``) keeps refusal 6 whole.
    """

    admitted_axes = frozenset(delivering_axes_admitted)
    if not admitted_axes <= DELIVERING_BRANCH_MODULE_AXES:
        raise PerceptionBranchError(
            f"delivering_axes_admitted {sorted(admitted_axes)} is not a subset of "
            f"{sorted(DELIVERING_BRANCH_MODULE_AXES)}"
        )

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
        raw_contrast_pairs = row.get("contrast_pairs")
        contrast_pairs = None
        if raw_contrast_pairs is not None:
            if (
                not isinstance(raw_contrast_pairs, Mapping)
                or set(raw_contrast_pairs) != {"relpath", "sha256"}
                or not isinstance(raw_contrast_pairs.get("relpath"), str)
                or not raw_contrast_pairs["relpath"]
                or not isinstance(raw_contrast_pairs.get("sha256"), str)
                or len(raw_contrast_pairs["sha256"]) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in raw_contrast_pairs["sha256"]
                )
            ):
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}].contrast_pairs "
                    "must be exactly {relpath, sha256}, with sha256 a "
                    "lowercase 64-hex SHA-256"
                )
            contrast_pairs = {
                "relpath": raw_contrast_pairs["relpath"],
                "sha256": raw_contrast_pairs["sha256"],
            }
        if top2_contrast_presentation_id is not None:
            if (
                presentation_id == top2_contrast_presentation_id
                and contrast_pairs is None
            ):
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}] declares "
                    f"presentation_id {top2_contrast_presentation_id!r} and "
                    "must carry a contrast_pairs pin"
                )
            if (
                presentation_id != top2_contrast_presentation_id
                and contrast_pairs is not None
            ):
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}] carries "
                    "contrast_pairs but its presentation_id is not "
                    f"{top2_contrast_presentation_id!r}"
                )
        raw_key_source = row.get("key_source")
        key_source = (
            None if raw_key_source is None
            else parse_perception_branch_key_source(
                raw_key_source,
                field=f"perception branches.branches[{position}].key_source",
                declared_stores=declared_stores,
            )
        )
        has_axis = (
            bool(knobs) or release_swap is not None or presentation_id is not None
            or min_candidates is not None or key_source is not None
        )
        if replicate_of is not None and has_axis:
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] names replicate_of "
                "and must declare no axis: it resolves exactly the delivering "
                "branch's (A's) own request"
            )
        delivering_axes = {
            "presentation_id": presentation_id is not None,
            "min_candidates": min_candidates is not None,
        }
        if deliver and (
            bool(knobs) or release_swap is not None or key_source is not None
            or any(present and axis not in admitted_axes for axis, present in delivering_axes.items())
        ):
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] carries deliver: "
                "true and must declare no axis: A is the cell's own request, "
                "override-free (only a consumption module's admitted delivered "
                "policy may set A's presentation_id / min_candidates)"
            )
        if (deliver or replicate_of is not None) and prepared_seed is not None:
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] carries a "
                "prepared_seed but is A or its twin (T): A's seed is the "
                "cell's own prepared_phase_supply, and T takes A's seed"
            )
        if (
            (replicate_of is not None or (deliver and "presentation_id" not in admitted_axes))
            and contrast_pairs is not None
        ):
            raise PerceptionBranchError(
                f"perception branches.branches[{position}] carries "
                "contrast_pairs but is A or its twin (T): neither branch "
                "carries a presentation axis"
            )
        if not deliver and replicate_of is None:
            axis_categories = sum((
                bool(knobs), release_swap is not None, presentation_id is not None,
                min_candidates is not None, key_source is not None,
            ))
            if axis_categories != 1:
                raise PerceptionBranchError(
                    f"perception branches.branches[{position}] must declare "
                    "exactly one axis category (a boundary-supply knob, a "
                    "release_swap, a presentation_id, a min_candidates or a "
                    "key_source) -- one factor per non-A branch"
                )
        branches.append(PerceptionBranch(
            branch_id=branch_id, deliver=deliver, knobs=knobs,
            max_supplied_items=_positive_int(
                row["max_supplied_items"],
                field=f"perception branches.branches[{position}].max_supplied_items",
            ),
            replicate_of=replicate_of, release_swap=release_swap,
            presentation_id=presentation_id, min_candidates=min_candidates,
            prepared_seed=prepared_seed, contrast_pairs=contrast_pairs,
            key_source=key_source,
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
            None if branch.key_source is None else json.dumps(
                branch.key_source.receipt_pins(), sort_keys=True,
            ),
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
    presentation_skip_reason: str | None = None,
    contrast_block_sha256: str | None = None,
    min_candidates_met: bool | None = None,
    candidate_intent_ids_raw_count: int | None = None,
    template_group: bool = False,
    thinking_group: bool = False,
    sampling_group: bool = False,
    sampling: Mapping[str, object] | None = None,
    sampling_pending: bool = False,
    solver_absent: bool = False,
    absent_reason: str | None = None,
) -> dict[str, object]:
    """One branch's receipt row (design section 3, "Receipt").

    ``solver_absent``/``absent_reason`` (NX-T R1 seal fix, 2026-10-15) mark a NON-delivering level-2 branch whose Solver contact
    ended on a finite completion: the row still names that real, metered contact through the four level-2 fields, and gains the
    two optional keys ``solver_absent`` (true) and ``absent_reason`` (the code path). A row that is not absent is byte-identical
    to every row sealed before this change.

    ``thinking_group`` (NX-T R1) selects the v5 row shape: the v3 row plus ``thinking_policy`` -- ``None`` for A and the twin,
    the declared override map for every other branch.

    ``template_group`` (NX programme E1, Perception node) selects the v4 row
    shape: the v3 row plus ``instruction_template`` -- ``None`` for A and the
    twin, the declared ``{relpath, sha256}`` for every other branch.

    ``note_parse_status``/``candidate_intent_ids``/
    ``candidate_intent_ids_raw_count`` (schema v2) are exactly what
    ``rails.native_episode_receipt.parse_perception_branch_note`` returned for
    the branch's note: the collapsed, possibly empty list plus the listed count
    (``None`` defaults it to the list length -- a note with no duplicates).
    Any consistent triple is a measured outcome; only an inconsistent one is
    refused.

    The four ``solver_*``/``candidate_supply_value_ids`` fields are declared
    together or not at all: level 1 never supplies them, level 2 supplies
    them for every branch (A's naming its own ordinary first Solver visit,
    every other branch's naming the one Solver contact its note fanned out
    -- design section 3, "Level 2").

    ``presentation_skip_reason``/``contrast_block_sha256`` ("What to build"
    item 2) are the rendered outcome of the branch's own ``presentation_id``:
    at most one of the two is ever non-``None`` (a block either rendered --
    ``contrast_block_sha256`` -- or was skipped and says why -- ``
    presentation_skip_reason``), and both are ``None`` for a branch that
    declares no ``presentation_id`` (A, T, and every non-presentation B
    branch). ``min_candidates_met`` ("What to build" item 3) is ``None``
    unless ``branch.min_candidates`` is declared, in which case it is
    whatever this branch's own note parse found -- a bool, never a refusal:
    a short list is a measured outcome, not a defect.
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
    raw_count = (
        len(candidates) if candidate_intent_ids_raw_count is None
        else candidate_intent_ids_raw_count
    )
    reason = perception_branch_note_fields_error(note_parse_status, candidates, raw_count)
    if reason is not None:
        raise PerceptionBranchError(f"perception branch {branch.branch_id!r}: {reason}")
    if branch.min_candidates is not None and isinstance(min_candidates_met, bool) and (
        min_candidates_met != (len(candidates) >= branch.min_candidates)
    ):
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} min_candidates_met disagrees "
            "with its own collapsed candidate list"
        )
    level2_fields = (
        solver_contact_id, solver_request_sha256, solver_response_text_sha256,
        candidate_supply_value_ids,
    )
    has_level2 = any(field is not None for field in level2_fields)
    if solver_absent:
        if branch.deliver:
            raise PerceptionBranchError(
                f"perception branch {branch.branch_id!r} is the delivering branch (A) and cannot have an absent Solver column"
            )
        if absent_reason not in PERCEPTION_BRANCH_ABSENT_REASONS:
            raise PerceptionBranchError(
                f"perception branch {branch.branch_id!r} absent_reason must be one of "
                f"{sorted(PERCEPTION_BRANCH_ABSENT_REASONS)}, got {absent_reason!r}"
            )
        if not has_level2:
            raise PerceptionBranchError(
                f"perception branch {branch.branch_id!r} has an absent Solver column and must still name its Solver contact"
            )
    elif absent_reason is not None:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} carries an absent_reason but no solver_absent mark"
        )
    if has_level2 and any(field is None for field in level2_fields):
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} must declare all four "
            "level-2 fields together or none of them"
        )
    if presentation_skip_reason is not None and (
        not isinstance(presentation_skip_reason, str) or not presentation_skip_reason
    ):
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} presentation_skip_reason "
            "must be a non-empty string or None"
        )
    if presentation_skip_reason is not None and branch.presentation_id is None:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} carries a "
            "presentation_skip_reason but declares no presentation_id"
        )
    if contrast_block_sha256 is not None:
        contrast_block_sha256 = _sha256_hex(
            contrast_block_sha256, field="contrast_block_sha256",
        )
        if branch.presentation_id is None:
            raise PerceptionBranchError(
                f"perception branch {branch.branch_id!r} carries a "
                "contrast_block_sha256 but declares no presentation_id"
            )
    if presentation_skip_reason is not None and contrast_block_sha256 is not None:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} cannot carry both a "
            "rendered contrast_block_sha256 and a presentation_skip_reason"
        )
    if branch.min_candidates is None and min_candidates_met is not None:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} carries "
            "min_candidates_met but declares no min_candidates"
        )
    if branch.min_candidates is not None:
        if not isinstance(min_candidates_met, bool):
            raise PerceptionBranchError(
                f"perception branch {branch.branch_id!r} declares "
                "min_candidates and must carry a min_candidates_met bool"
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
        "candidate_intent_ids_raw_count": int(raw_count),
        "presentation_skip_reason": presentation_skip_reason,
        "contrast_block_sha256": contrast_block_sha256,
        "min_candidates_met": min_candidates_met,
        "key_source": (
            None if branch.key_source is None else branch.key_source.receipt_pins()
        ),
    }
    reason = perception_branch_key_source_error(record["key_source"])
    if reason is not None:
        raise PerceptionBranchError(f"perception branch {branch.branch_id!r}: {reason}")
    if template_group:
        record["instruction_template"] = (
            None if branch.instruction_template is None
            else branch.instruction_template.as_json()
        )
    elif branch.instruction_template is not None:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} declares an instruction_template "
            "but its row is not the template (v4) shape"
        )
    if template_group and thinking_group:
        raise PerceptionBranchError("a perception branch row is a template (v4) row or a thinking (v5) row, never both")
    if thinking_group:
        record["thinking_policy"] = (
            None if branch.thinking_policy is None else canonical_thinking_policy(branch.thinking_policy)
        )
    elif branch.thinking_policy is not None:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} declares a thinking_policy but its row is not the thinking (v5) shape"
        )
    declares_sampling = branch.perception_samples is not None or branch.solver_samples is not None
    if sampling_group:
        if template_group or thinking_group:
            raise PerceptionBranchError("a perception branch row has one shape: template (v4), thinking (v5) or sampling (v6)")
        if sampling_pending:
            # The Perception-visit row of a level-2 sampling branch: its Solver samples (and, for the last Perception sample, the
            # merge) do not exist yet. The runner re-seals the row through this same constructor at the episode's final receipt
            # assembly, with the complete sampling value and sampling_pending False, so the pending form never survives.
            if sampling is not None or has_level2:
                raise PerceptionBranchError(
                    f"perception branch {branch.branch_id!r}: a pending sampling row carries neither a sampling value nor level-2 fields"
                )
            record["sampling"] = None
        else:
            reason = perception_branch_sampling_error(sampling, is_b=branch.is_b)
            if reason is None and branch.is_b:
                reason = _sampling_record_matches_axes(branch, sampling)
            if reason is not None:
                raise PerceptionBranchError(f"perception branch {branch.branch_id!r}: {reason}")
            record["sampling"] = None if sampling is None else json.loads(json.dumps(sampling))
    elif declares_sampling or sampling is not None or sampling_pending:
        raise PerceptionBranchError(
            f"perception branch {branch.branch_id!r} declares sampling but its row is not the sampling (v6) shape"
        )
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
    if solver_absent:
        record["solver_absent"] = True
        record["absent_reason"] = absent_reason
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
        "schema": (
            PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6 if group.is_sampling
            else PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5 if group.is_thinking
            else PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4 if group.is_template
            else PERCEPTION_BRANCH_RECEIPT_SCHEMA
        ),
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


#: The evidence-id prefix a branch's own ``top2-contrast-v1`` block carries on
#: the wire (``rails.runner.PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_SCHEME``,
#: restated so this module never imports the runner).
PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_PREFIX = "perception-branch-presentation:"


@dataclass(frozen=True)
class PerceptionBranchReplayContact:
    """One recorded model contact, as a Perception-branch replay needs it.

    ``presentation_block_sha256`` maps each ``perception-branch-presentation:
    <branch_id>`` evidence item the recorded REQUEST carried to the sha256 of
    its content -- the digest the live runner seals as
    ``contrast_block_sha256``. Only digests, never text, beside ``text`` (the
    recorded response, which is the branch note).
    """

    request_sha256: str | None
    response_text_sha256: str | None
    text: str | None
    presentation_block_sha256: Mapping[str, str] | None = None


def _replay_sampling_value(sampling: object, *, contacts: Mapping[str, "PerceptionBranchReplayContact"], what: str) -> None:
    """Decision 338: hold a recorded v6 ``sampling`` value to its recorded contacts.

    Every sample contact must be one the row recorded, with the recorded request / response digests; the merge and the commit
    must re-derive from the recorded response texts. A sample that ended on a finite completion has no text to re-derive from, so
    its recorded status stands (the bundle verifier checks it against the wire ``finish_reason``). Raises
    :class:`PerceptionBranchError` on any disagreement, which the caller turns into an INCOMPLETE (re-flown) row.
    """

    if sampling is None:
        return
    if not isinstance(sampling, Mapping):
        raise PerceptionBranchError(f"{what} sampling record is not an object")

    def texts_of(record: Mapping[str, object], label: str) -> list[str | None]:
        texts: list[str | None] = []
        for sample in record["samples"]:
            found = contacts.get(sample.get("contact_id"))
            if found is None:
                raise PerceptionBranchError(f"{what} {label} sample names a contact this row did not record")
            if (
                found.request_sha256 != sample.get("request_sha256")
                or found.response_text_sha256 != sample.get("response_text_sha256")
            ):
                raise PerceptionBranchError(f"{what} {label} sample digests differ from its recorded contact")
            status = sample.get("parse_status")
            if isinstance(status, str) and status.startswith("finite-completion:"):
                texts.append(None)
                continue
            if not isinstance(found.text, str) or hashlib.sha256(found.text.encode("utf-8")).hexdigest() != sample.get(
                "response_text_sha256"
            ):
                raise PerceptionBranchError(f"{what} {label} sample text does not hash to its recorded response")
            texts.append(found.text)
        return texts

    record = sampling.get("perception_samples")
    if isinstance(record, Mapping):
        axis = PerceptionSamplesAxis(
            k=record["k"], decoding=tuple(sorted(record["decoding"].items())), seed_offsets=tuple(record["seed_offsets"]),
            merge_policy=record["merge_policy"], cap=record["cap"],
        )
        texts = texts_of(record, "perception")
        for sample, text in zip(record["samples"], texts):
            status, ids, _raw = parse_perception_branch_note(text)
            if sample.get("note_parse_status") != status or list(sample.get("candidate_intent_ids") or ()) != list(ids):
                raise PerceptionBranchError(f"{what} perception sample note fields differ from their re-derivation")
        outcome = merge_perception_samples(axis, texts)
        if (
            list(outcome.merged_candidate_ids) != record["merged_candidate_ids"]
            or list(outcome.appended_candidate_ids) != record["appended_candidate_ids"]
        ):
            raise PerceptionBranchError(f"{what} perception merge differs from its re-derivation")
    record = sampling.get("solver_samples")
    if isinstance(record, Mapping):
        commit = record["commit"]
        axis = SolverSamplesAxis(
            n=record["n"], decoding=tuple(sorted(record["decoding"].items())), seed_offsets=tuple(record["seed_offsets"]),
            commit_policy=commit["policy"], min_support=commit["min_support"],
            similarity_threshold=commit["similarity_threshold"], n1_min=commit["n1_min"],
            empty_votes_min=commit["empty_votes_min"],
        )
        texts = texts_of(record, "solver")
        for sample, text in zip(record["samples"], texts):
            if text is not None and solver_sample_parse_status(text) != sample.get("parse_status"):
                raise PerceptionBranchError(f"{what} solver sample parse status differs from its re-derivation")
        outcome = commit_solver_samples(axis, texts, n1=None)
        recorded = record["outcome"]
        if (
            recorded["intent_support"] != outcome.intent_support
            or recorded["delivered_entity_count"] != len(outcome.entities)
            or recorded["entity_supports"] != [{"type": e.type, "support": e.support} for e in outcome.entities]
        ):
            raise PerceptionBranchError(f"{what} solver commit differs from its re-derivation")


def replay_perception_branch_block(
    block: Mapping[str, object],
    *,
    contacts: Mapping[str, PerceptionBranchReplayContact],
) -> dict[str, object]:
    """Re-derive one row's ``perception_branches`` receipt from its RECORDED
    contacts (seal-only resume-recovery, 2026-09-29, the P-SV-1 seal abort).

    ``contacts`` maps each agent contact id the row's receipt names to its
    recorded request/response (``core.flight.resume`` builds it from the
    trace). Every branch row is rebuilt under the current schema (v3; a v1/v2 row gains key_source None):

    * identity fields (branch id/index, deliver, replicate_of, knobs, swap,
      presentation id, min_candidates, supplied ids, contact id and digests,
      and the level-2 Solver custody) are KEPT from the recorded receipt, and
      each named contact must exist with the recorded request/response digests;
    * the note fields are RE-DERIVED from the recorded response text with
      :func:`parse_perception_branch_note` (the note must hash to the recorded
      ``note_sha256``);
    * the presentation outcome is RE-DERIVED from the recorded request: a
      ``top2-contrast-v1`` branch whose request carried its block seals that
      block's digest; one whose request carried none seals the renderer's own
      skip reason (fewer than two distinct supplied intents, else insufficient
      pool support -- the only two reasons the renderer has). This restores
      the custody the level-2 fold dropped before 2026-09-29;
    * ``min_candidates_met`` is recomputed on the collapsed list.

    A recorded non-``None`` field that disagrees with its re-derivation, or any
    contact that cannot be accounted for, raises :class:`PerceptionBranchError`
    -- the caller marks the row INCOMPLETE (re-flown), never approximated. The
    rebuilt block is validated with ``validate_perception_branch_receipt``.
    """

    from .perception_presentations import (  # noqa: PLC0415 (lazy: core.base import)
        TOP2_CONTRAST_PRESENTATION_ID,
        TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES,
        TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT,
        branch_supplied_intent_ids,
    )

    if not isinstance(block, Mapping):
        raise PerceptionBranchError("perception_branches is not a receipt object")
    schema = block.get("schema")
    if schema not in (PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1, *PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS):
        raise PerceptionBranchError("perception_branches carries an unregistered schema")
    rows = block.get("branches")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)) or not rows:
        raise PerceptionBranchError("perception_branches has no ordered branches")
    level = block.get("level")

    def contact(contact_id: object, *, what: str) -> PerceptionBranchReplayContact:
        found = contacts.get(contact_id) if isinstance(contact_id, str) else None
        if found is None:
            raise PerceptionBranchError(f"{what} names a contact this row did not record")
        return found

    rebuilt: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise PerceptionBranchError("a perception branch record is not an object")
        branch_id = row.get("branch_id")
        what = f"perception branch {branch_id!r}"
        recorded = contact(row.get("contact_id"), what=what)
        if (
            recorded.request_sha256 != row.get("request_sha256")
            or recorded.response_text_sha256 != row.get("response_text_sha256")
        ):
            raise PerceptionBranchError(f"{what} digests differ from its recorded contact")
        if not isinstance(recorded.text, str) or hashlib.sha256(
            recorded.text.encode("utf-8")
        ).hexdigest() != row.get("note_sha256"):
            raise PerceptionBranchError(f"{what} note does not hash to its recorded response")
        status, candidates, raw_count = parse_perception_branch_note(recorded.text)
        if schema in PERCEPTION_BRANCH_NOTE_FIELD_SCHEMAS and (
            row.get("note_parse_status") != status
            or list(row.get("candidate_intent_ids") or ()) != list(candidates)
            or row.get("candidate_intent_ids_raw_count") != raw_count
        ):
            raise PerceptionBranchError(f"{what} note fields differ from their re-derivation")

        blocks = recorded.presentation_block_sha256 or {}
        own_block = blocks.get(f"{PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_PREFIX}{branch_id}")
        foreign = [key for key in blocks if key != f"{PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_PREFIX}{branch_id}"]
        if foreign:
            raise PerceptionBranchError(f"{what} request carried another branch's presentation")
        presentation_id = row.get("presentation_id")
        if presentation_id == TOP2_CONTRAST_PRESENTATION_ID:
            if own_block is not None:
                contrast_block_sha256, skip_reason = own_block, None
            else:
                contrast_block_sha256 = None
                skip_reason = (
                    TOP2_CONTRAST_SKIP_REASON_FEWER_THAN_TWO_CANDIDATES
                    if len(branch_supplied_intent_ids(tuple(row.get("supplied_value_ids") or ()))) < 2
                    else TOP2_CONTRAST_SKIP_REASON_INSUFFICIENT_POOL_SUPPORT
                )
        else:
            if own_block is not None:
                raise PerceptionBranchError(
                    f"{what} request carried a presentation block its branch does not declare"
                )
            contrast_block_sha256, skip_reason = None, None
        for field, value in (
            ("contrast_block_sha256", contrast_block_sha256),
            ("presentation_skip_reason", skip_reason),
        ):
            if row.get(field) is not None and row.get(field) != value:
                raise PerceptionBranchError(f"{what} {field} differs from its re-derivation")
        min_candidates = row.get("min_candidates")
        min_candidates_met = (
            None if min_candidates is None else len(candidates) >= int(min_candidates)
        )
        if level == 2:
            solver = contact(row.get("solver_contact_id"), what=f"{what} Solver column")
            if (
                solver.request_sha256 != row.get("solver_request_sha256")
                or solver.response_text_sha256 != row.get("solver_response_text_sha256")
            ):
                raise PerceptionBranchError(
                    f"{what} Solver column digests differ from its recorded contact"
                )
        if schema == PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6:
            _replay_sampling_value(row.get("sampling"), contacts=contacts, what=what)
        new_row = dict(row)
        new_row.update({
            "note_parse_status": status,
            "candidate_intent_ids": list(candidates),
            "candidate_intent_ids_raw_count": raw_count,
            "contrast_block_sha256": contrast_block_sha256,
            "presentation_skip_reason": skip_reason,
            "min_candidates_met": min_candidates_met,
        })
        # A v1/v2 row predates the key_source axis, so it swapped no key:
        # ``None`` is its exact v3 value. A v3 row keeps its recorded pins.
        if schema in (PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2):
            new_row["key_source"] = None
        rebuilt.append(new_row)
    result = dict(block)
    # Every block is rebuilt under the CURRENT schema (v3), as v1 -> v2 was before.
    # A v4 (template) block stays v4: its rows carry the template axis.
    # A v5 (thinking-policy) block stays v5: its rows carry the thinking axis.
    # A v6 (sampling) block stays v6: its rows carry the sampling records.
    result["schema"] = (
        schema if schema in (
            PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5, PERCEPTION_BRANCH_RECEIPT_SCHEMA_V6,
        )
        else PERCEPTION_BRANCH_RECEIPT_SCHEMA
    )
    result["branches"] = rebuilt
    branch_ids = [row.get("branch_id") for row in rebuilt]
    twin = next((row.get("branch_id") for row in rebuilt if row.get("replicate_of") is not None), None)
    validate_perception_branch_receipt(
        result, branch_ids=branch_ids, delivered_branch_id=branch_ids[-1],
        twin_branch_id=twin, phase_id=str(block.get("phase_id")), level=level,
        error_type=PerceptionBranchError,
    )
    return result


__all__ = [
    "SAMPLING_VARIANT_KINDS",
    "PerceptionSamplesAxis",
    "SolverSamplesAxis",
    "derive_sample_seeds",
    "merge_perception_samples",
    "commit_solver_samples",
    "solver_sample_parse_status",
    "perception_contact_slots",
    "solver_contact_slots",
    "sampling_decoding_table",
    "parse_perception_samples",
    "parse_perception_sampling_variants",
    "parse_solver_samples",
    "perception_samples_record",
    "sampling_extra_contacts",
    "solver_samples_record",
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
    "PERCEPTION_BRANCH_PRESENTATION_EVIDENCE_PREFIX",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V1",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V2",
    "PERCEPTION_BRANCH_KEY_SOURCE_KEYS",
    "PerceptionBranchKeySource",
    "parse_perception_branch_key_source",
    "PERCEPTION_BRANCH_RECORD_KEYS",
    "PERCEPTION_BRANCH_REQUIRED_KEYS",
    "PERCEPTION_BRANCH_VISITS",
    "PerceptionBranch",
    "PerceptionBranchError",
    "PerceptionBranchGroup",
    "PerceptionBranchKnob",
    "PerceptionBranchReplayContact",
    "parse_perception_branch_knob",
    "parse_perception_branches",
    "parse_perception_template_variants",
    "parse_perception_thinking_variants",
    "canonical_thinking_policy",
    "THINKING_VARIANT_BLOCK_KEYS",
    "THINKING_VARIANT_ARM_KEYS",
    "THINKING_VARIANT_ROLE_KINDS",
    "MIN_THINKING_CANDIDATE_ARMS",
    "MAX_THINKING_CANDIDATE_ARMS",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V4",
    "PERCEPTION_BRANCH_RECEIPT_SCHEMA_V5",
    "perception_branch_ceiling",
    "perception_branch_record",
    "perception_branch_receipt",
    "parse_perception_branch_note",
    "replay_perception_branch_block",
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
    "SUPPLY_VARIANT_RECEIPT_SCHEMA_V4",
    "SUPPLY_VARIANT_KIND_SUPPLY",
    "SUPPLY_VARIANT_KIND_TEMPLATE",
    "SUPPLY_VARIANT_KIND_DECODING",
    "SUPPLY_VARIANT_RECEIPT_SCHEMA_V6",
    "DECODING_VARIANT_KNOBS",
    "DECODING_VARIANT_REFUSED_KNOBS",
    "DECODING_VARIANT_NODES",
    "MIN_DECODING_CANDIDATE_ARMS",
    "MAX_DECODING_CANDIDATE_ARMS",
    "parse_decoding_variants",
    "TEMPLATE_VARIANT_NODES",
    "TEMPLATE_VARIANT_ROOTS",
    "MIN_TEMPLATE_CANDIDATE_ARMS",
    "MAX_TEMPLATE_CANDIDATE_ARMS",
    "SupplyVariantTemplate",
    "parse_template_variants",
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
    "parse_supply_variant_release_swaps",
    "SUPPLY_VARIANT_RECEIPT_SCHEMA_V5",
    "MULTI_STORE_RELEASE_SWAPS_SUPPORTED",
    "parse_supply_variants",
    "supply_variant_arm_record",
    "supply_variant_receipt",
]
