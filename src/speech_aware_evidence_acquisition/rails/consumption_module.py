"""The evidence-consumption module: ONE policy compiler for the composed arm.

Owner decisions 195 (one module carries every component; it may call the
model) and 196 (carrier-agnostic: transfer to every other locked carrier
with only an adapter and a config block per carrier), 199 (an empty supply
is legal). Design: the 2026-09-29 consumption-module design note in
``docs/superpowers/specs/`` (sections 1-5, 2b, 2c and the coordinator rulings
R1-R5); this file names no carrier, so it does not spell that note's path. This file implements migration steps 1 and 2:

* the closed registry entry :data:`CONSUMPTION_MODULE_ID` in
  ``core.base.CONSUMPTION_MODULES`` and the parse of the config block
  ``native_episode.consumption_module`` (:func:`parse_consumption_module_block`,
  fail-closed);
* the compiler (:func:`compile_module`): a PURE function from a component list
  plus a carrier's hooks to exactly the config blocks the runtime already
  reads -- ``policy``, ``knowledge_stores``, ``native_episode`` and
  ``phase_material`` -- and the per-row header receipt schema
  :data:`CONSUMPTION_MODULE_RECEIPT_SCHEMA` (:func:`module_header_receipt`).

What this module is NOT (study ``CLAUDE.md``, "one base, thin derivations"):
not a controller (no ``initial_contact`` / ``advance``), not a
``TaskAdapter``, not a model client. It never talks to the core: every model
contact stays on ``FlightRuntime._dispatch_phase_program``, the native
episode, and ``_dispatch_relisten_contact``. The module is a policy the one
harness executes; it adds no execution path.

Carrier independence (design 2b): this file names no carrier. Every carrier
fact -- the lock layer, the path of the decision node's supply seed, the
flown program ids -- reaches it through :class:`CarrierHooks`, whose members
all default to ``None`` ("no analogue on this carrier"); a component that
needs a ``None`` hook refuses to arm. A carrier's hooks live beside its
adapter as ``rails/adapters/<profile>_module_hooks.py``.

Program ids (ruling R1): the compiler computes the contact ceiling from the
lock program plus each armed component's own term. When the (ceiling, Solver
response contract) pair is one a carrier already flew, it emits that flown
program id (flown cells keep their bytes; this is what makes the all-off
module compile byte for byte to the v2.0 lock, ruling R2); otherwise it emits
the family id ``phase-native-module-v1-c<ceiling>`` registered by
``rails.controllers.register_module_program_family_v1``.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.base import CONSUMPTION_MODULE_PROFILES, CONSUMPTION_MODULES
from .errors import RailsError

#: The module id (design "Proposed id"; the carrier enters as ``profile``).
CONSUMPTION_MODULE_ID = "saea-evidence-consumption-module-v1"
CONSUMPTION_MODULE_VERSION = "1"
#: The per-row header receipt schema (design section 2.5).
CONSUMPTION_MODULE_RECEIPT_SCHEMA = "saea-consumption-module-v1"
#: The block's key inside ``native_episode``.
CONSUMPTION_MODULE_CONFIG_KEY = "consumption_module"

#: The top-level composed-config keys the module OWNS: its compiled output is
#: exactly these four, and every other key (cell identity, carrier base,
#: prepared artifacts) is never written by it.
POLICY_OWNED_KEYS: tuple[str, ...] = (
    "policy", "knowledge_stores", "native_episode", "phase_material",
)
#: The keys of a DIRECT lock layer (design 3.2 "bare"; 2b.3 admission gate):
#: a carrier with no locked system (every carrier but the first) has as its
#: null arm the direct baseline of the shared controller -- the direct-only
#: phase program, which declares no ``native_episode`` and no
#: ``knowledge_stores`` (the loader refuses a ``native_episode`` block on any
#: program that is not the native-role episode). A direct layer compiles with
#: every component off; a component that writes into a block the layer does
#: not carry refuses (the writer finds no such object).
DIRECT_LAYER_KEYS: tuple[str, ...] = ("policy", "phase_material")

STATE_ON = "on"
STATE_OFF = "off"
STATE_SHADOW = "shadow"
STATE_COLUMN = "column"
COMPONENT_STATES: tuple[str, ...] = (STATE_ON, STATE_OFF, STATE_SHADOW, STATE_COLUMN)

_BLOCK_REQUIRED = frozenset({"module_id", "profile", "components"})
_BLOCK_OPTIONAL = frozenset({"columns", "lock"})
#: A lock-version name a block may declare (migration step 6, owner decision
#: 204): ``v<major>.<minor>``, resolved through the carrier's ``lock_versions``.
_LOCK_VERSION = re.compile(r"^v[0-9]+\.[0-9]+$")
_COMPONENT_REQUIRED = frozenset({"component_id", "state"})
_COMPONENT_OPTIONAL = frozenset({"admitted_by", "record", "params"})
_PROFILE = re.compile(r"^[a-z][a-z0-9]*$")

#: The node-action receipts a header receipt may point at (design 2.5).
NODE_RECEIPT_SCHEMAS = frozenset({
    "saea-perception-branch-arms-v1",
    "saea-supply-variant-arms-v3",
    "saea-solver-citations-v1",
    "saea-deliver-normaliser-v1",
    "saea-relisten-v1",
})

_REPO_ROOT = Path(__file__).resolve().parents[3]


class ConsumptionModuleConfigError(RailsError):
    """A consumption-module block, component or compilation is refused.
    Raised before any contact."""


# ---------------------------------------------------------------------------
# The component catalogue (design section 1, layer C). Closed: an unknown
# component id is refused. ``states`` are the non-off states this step
# compiles; ``pending`` names the migration step that arms a known component
# not yet compiled here (its non-off states are refused until then).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComponentSpec:
    component_id: str
    plane: str
    states: frozenset[str]
    params: frozenset[str]
    pending: str | None = None
    optional_params: frozenset[str] = frozenset()


AGREE_VOTE_SEED = "agree-vote-seed"
CENTROID_BOUNDARY_KEY = "centroid-boundary-key"
SOLVER_CITATION_CONTRACT = "solver-citation-contract"
REVIEWER_G5_REPAIR = "reviewer-g5-repair"
KNOWLEDGE_CONSUMPTION_OPPORTUNITY = "knowledge-consumption-opportunity"
NODE_CONTEXT_PRESENTATION = "node-context-presentation"
CONSTRUCTION_STORE_BINDING = "construction-store-binding"
RELISTEN = "relisten"
SCOPE_RULE = "scope-rule"
TOP2_CONTRAST = "top2-contrast"
FORCED_CANDIDATE_LIST = "forced-candidate-list"
#: 2026-09-30: the centred centroid + agreement retrieval key (K6p; the retrieval-key recall
#: read of 2026-09-30) as a Perception column: compiles to a B
#: branch's ``key_source`` axis. ``column`` only until a column read nominates it and an
#: admitting record exists.
KEY_SOURCE_K6P = "key-source:k6p"
#: The Perception components (migration step 4): each compiles to one axis of
#: a Perception branch -- a B branch in ``column`` state, the delivering
#: branch A in ``on`` state (ruling R3, admitted only). ``{component id: the
#: branch-row keys its params write}``.
PERCEPTION_AXIS_COMPONENTS: dict[str, tuple[str, ...]] = {
    TOP2_CONTRAST: ("presentation_id", "contrast_pairs"),
    FORCED_CANDIDATE_LIST: ("min_candidates",),
    KEY_SOURCE_K6P: ("key_source",),
}
_COLUMN_REQUIRED = frozenset({"column_id", "toggle", "to", "level"})
#: ``prepared_seed`` is the receipt of an artifact prepared FROM the compiled
#: identity (design 2.6, the branch-seed lesson): it is written into the
#: branch row and excluded from the block's own sha256.
_COLUMN_OPTIONAL = frozenset({"prepared_seed"})

COMPONENT_CATALOGUE: tuple[ComponentSpec, ...] = (
    ComponentSpec(NODE_CONTEXT_PRESENTATION, "USE, explicit node context presentation",
        frozenset({STATE_ON}), frozenset(),
        optional_params=frozenset({"tool_schema_rendering", "reviewer_history_scope"})),
    ComponentSpec(KNOWLEDGE_CONSUMPTION_OPPORTUNITY, "SUPPLY/USE, bounded knowledge opportunity",
        frozenset({STATE_ON}), frozenset({"mode", "store_id", "reviewer_template", "planner_template"}),
        optional_params=frozenset({"solver_template", "value_limit", "knowledge_binding",
                                   "reviewer_response_format_id"})),
    ComponentSpec(CONSTRUCTION_STORE_BINDING, "ORG, source-isolated construction release",
        frozenset({STATE_ON}), frozenset({"store_id", "snapshot", "release"})),
    ComponentSpec(
        AGREE_VOTE_SEED, "SUPPLY -> Perception seed", frozenset({STATE_ON}),
        frozenset({"w_agree", "k", "agreement_source"}),
    ),
    ComponentSpec(
        CENTROID_BOUNDARY_KEY, "ORG -> Perception seed", frozenset({STATE_ON}),
        frozenset({"facet_source"}),
    ),
    ComponentSpec(
        SOLVER_CITATION_CONTRACT, "USE, Solver response contract", frozenset({STATE_ON}),
        frozenset({"instruction_template", "response_format_id", "deliver_normaliser"}),
    ),
    ComponentSpec(
        REVIEWER_G5_REPAIR, "USE, Reviewer instruction", frozenset({STATE_ON}),
        frozenset({"instruction_template"}),
    ),
    # Ruling R4: re-listen stays ``shadow`` in the first composed read; a
    # ``live`` delivery mode does not exist yet (design 2.2 (c)).
    ComponentSpec(
        RELISTEN, "OBS post-delivery verification", frozenset({STATE_SHADOW}),
        frozenset({
            "policy", "max_slots_per_row", "value_max_words", "delivery",
            "blind_template_id", "confirm_template_id",
        }),
    ),
    # Migration step 4: ``column`` compiles to a same-flight Perception B
    # branch; ``on`` sets the delivering branch A's axis and is admitted only
    # through the carrier's ``delivered_path_admissions`` (ruling R3).
    ComponentSpec(
        TOP2_CONTRAST, "SUPPLY presentation -> Perception", frozenset({STATE_COLUMN, STATE_ON}),
        frozenset({"presentation_id", "contrast_pairs", "max_supplied_items"}),
    ),
    ComponentSpec(
        FORCED_CANDIDATE_LIST, "Perception response contract", frozenset({STATE_COLUMN, STATE_ON}),
        frozenset({"min_candidates", "max_supplied_items"}),
    ),
    # 2026-09-30: ``column`` only (no delivered-path admission exists); the branch swaps
    # the first phase's retrieval-key pins inside its own router (rails.supply_variants.
    # PerceptionBranchKeySource).
    ComponentSpec(
        KEY_SOURCE_K6P, "ORG -> Perception seed key (same-flight column)", frozenset({STATE_COLUMN}),
        frozenset({"key_source", "max_supplied_items"}),
    ),
    # Migration step 3 (owner decision 195 = B): a deterministic deliver
    # stage composed after the carrier's deliver normaliser; zero contacts.
    ComponentSpec(
        SCOPE_RULE, "USE, deliver node", frozenset({STATE_ON}),
        frozenset({"min_pool_occurrences", "untagged_share", "table"}),
    ),
    ComponentSpec(
        "e3-progressive-slots", "ORG/USE slot-types node", frozenset(), frozenset(),
        pending="the E3 build go (not decided)",
    ),
    ComponentSpec(
        "supply-abstain", "SUPPLY/USE abstention", frozenset(), frozenset(),
        pending="migration step 6a (supply abstention)",
    ),
)
_CATALOGUE = {spec.component_id: spec for spec in COMPONENT_CATALOGUE}


# ---------------------------------------------------------------------------
# Carrier hooks (design 2b.1).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CarrierHooks:
    """What the module may know about one carrier. Every member defaults to
    ``None``: "this component has no analogue on this carrier", and the
    compiler refuses to arm a component whose hook is ``None``.

    * ``profile`` -- the carrier profile name a block's ``profile`` must equal.
    * ``lock_layer`` -- returns the carrier lock's :data:`POLICY_OWNED_KEYS`
      blocks (the null arm of every composed read, ruling R2).
    * ``decision_supply_path`` -- the key path, from the composed config's
      top level, of the decision node's first-phase supply seed object.
    * ``flown_programs`` -- ``{(ceiling, solver response_format_id): program
      id}`` for the programs the carrier already flew.
    * ``decision_candidates`` / ``max_decision_candidates`` /
      ``delivered_units`` / ``default_deliver_normaliser`` -- the four design
      hooks of section 2b.1, consumed from migration step 4 on.
    * ``perception_branch_frame`` -- where and how Perception columns
      compile: ``{"block_path", "delivering_branch_id", "twin_branch_id",
      "max_supplied_items", "fit_estimate"}`` (migration step 4).
    * ``flown_branch_programs`` -- ``{(branch level, ceiling, Solver
      response_format_id): program id}`` for the branched programs the
      carrier already flew.
    * ``delivered_path_admissions`` -- ``{component id: admitting record}``
      of the Perception components whose column read NOMINATED and whose
      composed read carried them (ruling R3); empty until then, so ``on``
      refuses.
    * ``deliver_stages`` -- ``{component id: {"compositions": {base deliver
      normaliser id: that normaliser composed with the stage}, "params": the
      stage's registered pins}}`` for the deterministic deliver stages the
      carrier registers (migration step 3).
    * ``lock_versions`` -- ``{lock version: a callable returning that lock's
      POLICY_OWNED_KEYS blocks}`` (migration step 6, owner decision 204): the
      layers a block may name in its ``lock`` key. ``lock_layer`` stays the
      layer of a block that names none.
    * ``current_lock`` -- the carrier's CURRENT lock version: the null arm of
      every composed read registered from now on, and the lock the harness
      ``module`` switch class's OFF arm must name.
    * ``roster_pin_paths`` -- the key paths (from the composed config's top
      level) of the ROSTER pins inside the policy-owned blocks: the sealed
      per-roster query vectors a speech-keyed supply reads. They are cell
      identity, never policy: :meth:`ComposedPolicy.apply_to` keeps the
      target's own and :func:`verify_declared_module` compares everything
      else (migration step 6: a module cell on a roster other than the
      lock's own).
    """

    profile: str | None = None
    lock_layer: Callable[[], Mapping[str, object]] | None = None
    decision_supply_path: tuple[str, ...] | None = None
    flown_programs: Mapping[tuple[int, str | None], str] | None = None
    decision_candidates: Callable[..., tuple[str, ...]] | None = None
    max_decision_candidates: Callable[[], int] | None = None
    delivered_units: Callable[..., tuple[str, ...]] | None = None
    default_deliver_normaliser: Callable[[], str] | None = None
    deliver_stages: Mapping[str, Mapping[str, object]] | None = None
    perception_branch_frame: Mapping[str, object] | None = None
    flown_branch_programs: Mapping[tuple[int, int, str | None], str] | None = None
    delivered_path_admissions: Mapping[str, str] | None = None
    lock_versions: Mapping[str, Callable[[], Mapping[str, object]]] | None = None
    current_lock: str | None = None
    roster_pin_paths: tuple[tuple[str, ...], ...] | None = None
    #: Design section 2d: ``tool_offer_units(delivered text) -> (context
    #: label, units, parsed)`` in the ``delivered_units`` shape -- the units a
    #: model-initiated tool offer (``verify_span(index)``) is indexed over on
    #: this carrier. ``None``: no offer target on this carrier. The module
    #: OFFERS; it never calls a tool (owner directive 2026-09-29).
    tool_offer_units: Callable[..., tuple] | None = None
    #: The carrier's own component ANALOGUES that are not (yet) catalogue
    #: components -- ``{carrier component id: {"analogue_of", "plane",
    #: "status", "record", "armable"}}`` -- so the per-carrier inventory of
    #: design 2b.2 is data beside the hooks rather than prose. A listed
    #: analogue is never armable through a block (it is not in the module's
    #: catalogue, so the parse refuses its id); it names what a later
    #: registration would compile.
    carrier_components: Mapping[str, Mapping[str, object]] | None = None


@dataclass(frozen=True)
class DeliveredUnit:
    """One unit a ``delivered_units`` / ``tool_offer_units`` hook returns on
    a carrier whose delivered answer has no parser-native unit type: ``type``
    and ``filler`` are the two attributes the carrier-agnostic consumers read
    (re-listen targets ``(type, filler)``, as the first carrier's parsed
    entities carry);
    ``index`` is the unit's 0-based position in delivery order and ``kind`` a
    carrier-defined class of the value (e.g. a JSON type, a numeric kind)."""

    type: str
    filler: str
    index: int
    kind: str | None = None


def registered_profiles() -> tuple[str, ...]:
    """The carrier profiles ``core.base.CONSUMPTION_MODULE_PROFILES`` lists."""

    return tuple(sorted(CONSUMPTION_MODULE_PROFILES))


def profile_for_carrier_lock_key(carrier_lock_key: object) -> str | None:
    """The profile whose hooks a config's ``carrier_lock_key`` reaches, or
    ``None`` (``core.base.CONSUMPTION_MODULE_PROFILES``)."""

    if not isinstance(carrier_lock_key, str):
        return None
    for profile, lock_keys in CONSUMPTION_MODULE_PROFILES.items():
        if carrier_lock_key in lock_keys:
            return profile
    return None


def resolve_carrier_hooks(profile: str, *, repo_root: Path | None = None) -> CarrierHooks:
    """The hooks of ``profile``, from ``rails/adapters/<profile>_module_hooks.py``
    (its ``carrier_module_hooks(repo_root=...)``). Refuses a profile that
    ``core.base.CONSUMPTION_MODULE_PROFILES`` does not list, and one with no
    hooks file: a carrier without an adapter cannot carry the module."""

    if not isinstance(profile, str) or _PROFILE.fullmatch(profile) is None:
        raise ConsumptionModuleConfigError(f"profile must match {_PROFILE.pattern}, got {profile!r}")
    if profile not in CONSUMPTION_MODULE_PROFILES:
        raise ConsumptionModuleConfigError(
            f"profile {profile!r} has no carrier hooks: it is not a registered profile "
            f"(core.base.CONSUMPTION_MODULE_PROFILES: {list(registered_profiles())})"
        )
    try:
        hooks_module = importlib.import_module(
            f"{__package__}.adapters.{profile}_module_hooks"
        )
    except ModuleNotFoundError as error:
        raise ConsumptionModuleConfigError(
            f"profile {profile!r} has no carrier hooks (rails/adapters/"
            f"{profile}_module_hooks.py)"
        ) from error
    hooks = hooks_module.carrier_module_hooks(repo_root=repo_root)
    if not isinstance(hooks, CarrierHooks) or hooks.profile != profile:
        raise ConsumptionModuleConfigError(
            f"carrier hooks for {profile!r} must be a CarrierHooks naming that profile"
        )
    return hooks


def carrier_hooks_for_lock_key(carrier_lock_key: object) -> CarrierHooks | None:
    """The hooks of the carrier a config declares (``carrier_lock_key``), or
    ``None`` when that carrier reaches no registered profile -- the
    carrier-agnostic rails (the config loader, the runner, re-listen's
    replay) reach carrier facts through this, never by naming a carrier
    (migration step 5). The lock key maps to its profile through
    ``core.base.CONSUMPTION_MODULE_PROFILES`` (a lock key such as
    ``<carrier>-original`` is not itself a profile name)."""

    profile = profile_for_carrier_lock_key(carrier_lock_key)
    if profile is None:
        return None
    try:
        return resolve_carrier_hooks(profile)
    except ConsumptionModuleConfigError:
        return None


# ---------------------------------------------------------------------------
# Parse (migration step 1).
# ---------------------------------------------------------------------------


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ComponentDecl:
    component_id: str
    state: str
    admitted_by: str | None
    record: str | None
    params_json: str

    @property
    def params(self) -> dict[str, object]:
        return json.loads(self.params_json)


@dataclass(frozen=True)
class ColumnDecl:
    """One same-flight column: it toggles exactly one component (design 3.3)."""

    column_id: str
    toggle: str
    to: str
    level: int
    prepared_seed_json: str | None

    @property
    def prepared_seed(self) -> dict[str, str] | None:
        return None if self.prepared_seed_json is None else json.loads(self.prepared_seed_json)


@dataclass(frozen=True)
class ConsumptionModuleBlock:
    module_id: str
    profile: str
    components: tuple[ComponentDecl, ...]
    block_sha256: str
    block_json: str
    columns: tuple[ColumnDecl, ...] = ()
    #: The lock version the block composes onto (migration step 6, owner
    #: decision 204), or ``None``: the carrier's ``lock_layer`` -- the layer
    #: every block written before step 6 compiled onto (the v2.0 lock on the
    #: first carrier), kept so their bytes and proofs never move.
    lock: str | None = None

    def component(self, component_id: str) -> ComponentDecl | None:
        for decl in self.components:
            if decl.component_id == component_id:
                return decl
        return None

    def armed(self) -> tuple[ComponentDecl, ...]:
        """The non-off components, in catalogue order (deterministic)."""

        order = {spec.component_id: i for i, spec in enumerate(COMPONENT_CATALOGUE)}
        return tuple(sorted(
            (d for d in self.components if d.state != STATE_OFF),
            key=lambda d: order[d.component_id],
        ))


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConsumptionModuleConfigError(f"{field} must be non-empty text")
    return value


def _require_record(value: object, *, field: str, repo_root: Path, must_exist: bool) -> str:
    text = _require_text(value, field=field)
    if (
        "\\" in text or text.startswith("/") or re.match(r"^[A-Za-z]:", text)
        or any(part in ("", ".", "..") for part in text.split("/"))
    ):
        raise ConsumptionModuleConfigError(f"{field} must be a repo-relative POSIX path: {text!r}")
    if must_exist and not (repo_root / text).is_file():
        raise ConsumptionModuleConfigError(
            f"{field} {text!r} does not resolve to a file in the repository; an "
            "armed component must name the record that admits it"
        )
    return text


def parse_consumption_module_block(
    raw: object, *, repo_root: Path | None = None,
) -> ConsumptionModuleBlock:
    """Validate one ``native_episode.consumption_module`` block, fail-closed.

    Refused: unknown or missing block keys; a ``module_id`` not registered in
    ``core.base.CONSUMPTION_MODULES``; a malformed ``profile``; an unknown or
    repeated ``component_id``; an unknown ``state``; a non-off state the
    component does not compile in this step; a non-off component without an
    ``admitted_by`` text and a ``record`` path that resolves to a repository
    file; params whose key set is not exactly the component's; a malformed
    column, a column toggling a component that is not in ``column`` state (or
    re-listen, whose same-flight columns are its ``shadow`` state), a
    ``column`` component no column toggles or two columns toggle, a ``to``
    other than ``on``, mixed levels, or repeated column ids."""

    root = _REPO_ROOT if repo_root is None else Path(repo_root)
    if not isinstance(raw, Mapping):
        raise ConsumptionModuleConfigError("consumption_module must be an object")
    keys = set(raw)
    if not _BLOCK_REQUIRED <= keys or keys - _BLOCK_REQUIRED - _BLOCK_OPTIONAL:
        raise ConsumptionModuleConfigError(
            f"consumption_module keys must be {sorted(_BLOCK_REQUIRED)} plus optional "
            f"{sorted(_BLOCK_OPTIONAL)}, got {sorted(keys)}"
        )
    module_id = _require_text(raw["module_id"], field="consumption_module.module_id")
    if module_id not in CONSUMPTION_MODULES.names():
        raise ConsumptionModuleConfigError(
            f"consumption_module.module_id {module_id!r} is not registered; "
            f"registered: {CONSUMPTION_MODULES.names()}"
        )
    profile = raw["profile"]
    if not isinstance(profile, str) or _PROFILE.fullmatch(profile) is None:
        raise ConsumptionModuleConfigError(
            f"consumption_module.profile must match {_PROFILE.pattern}, got {profile!r}"
        )
    columns = raw.get("columns", [])
    if not isinstance(columns, list):
        raise ConsumptionModuleConfigError("consumption_module.columns must be a list")
    lock = raw.get("lock")
    if "lock" in raw and (not isinstance(lock, str) or _LOCK_VERSION.fullmatch(lock) is None):
        raise ConsumptionModuleConfigError(
            f"consumption_module.lock must match {_LOCK_VERSION.pattern}, got {lock!r}"
        )
    components = raw["components"]
    if not isinstance(components, list):
        raise ConsumptionModuleConfigError("consumption_module.components must be a list")
    decls: list[ComponentDecl] = []
    seen: set[str] = set()
    for index, entry in enumerate(components):
        field = f"consumption_module.components[{index}]"
        if not isinstance(entry, Mapping):
            raise ConsumptionModuleConfigError(f"{field} must be an object")
        entry_keys = set(entry)
        if not _COMPONENT_REQUIRED <= entry_keys or entry_keys - _COMPONENT_REQUIRED - _COMPONENT_OPTIONAL:
            raise ConsumptionModuleConfigError(
                f"{field} keys must be {sorted(_COMPONENT_REQUIRED)} plus optional "
                f"{sorted(_COMPONENT_OPTIONAL)}, got {sorted(entry_keys)}"
            )
        component_id = entry["component_id"]
        spec = _CATALOGUE.get(component_id) if isinstance(component_id, str) else None
        if spec is None:
            raise ConsumptionModuleConfigError(
                f"{field}.component_id {component_id!r} is unknown; known: {sorted(_CATALOGUE)}"
            )
        if component_id in seen:
            raise ConsumptionModuleConfigError(f"{field}.component_id {component_id!r} is repeated")
        seen.add(component_id)
        state = entry["state"]
        if state not in COMPONENT_STATES:
            raise ConsumptionModuleConfigError(
                f"{field}.state {state!r} is unknown; states: {list(COMPONENT_STATES)}"
            )
        armed = state != STATE_OFF
        if armed and state not in spec.states:
            reason = (
                f"it compiles from {spec.pending}" if spec.pending is not None
                else f"its compiled states are {sorted(spec.states)}"
            )
            raise ConsumptionModuleConfigError(
                f"{field}: component {component_id!r} cannot be {state!r}; {reason}"
            )
        admitted_by = entry.get("admitted_by")
        record = entry.get("record")
        if armed or admitted_by is not None:
            admitted_by = _require_text(admitted_by, field=f"{field}.admitted_by")
        if armed or record is not None:
            record = _require_record(
                record, field=f"{field}.record", repo_root=root, must_exist=armed,
            )
        params = entry.get("params", {})
        if not isinstance(params, Mapping):
            raise ConsumptionModuleConfigError(f"{field}.params must be an object")
        if armed and (not spec.params <= set(params) or set(params) - spec.params - spec.optional_params):
            raise ConsumptionModuleConfigError(
                f"{field}.params of {component_id!r} must carry exactly "
                f"{sorted(spec.params)}, got {sorted(params)}"
            )
        decls.append(ComponentDecl(
            component_id, state, admitted_by, record, _canonical(dict(params)),
        ))
    column_decls = _parse_columns(columns, decls)
    block_json = _canonical(dict(raw))
    identity = dict(raw)
    if "columns" in identity:
        identity["columns"] = [
            {k: v for k, v in dict(c).items() if k != "prepared_seed"} for c in columns
        ]
    return ConsumptionModuleBlock(
        module_id=module_id,
        profile=profile,
        components=tuple(decls),
        block_sha256=_sha256_text(_canonical(identity)),
        block_json=block_json,
        columns=column_decls,
        lock=lock,
    )


def _pin(value: object, *, field: str) -> dict[str, str]:
    if (
        not isinstance(value, Mapping) or set(value) != {"relpath", "sha256"}
        or not isinstance(value["relpath"], str) or not value["relpath"]
        or not re.fullmatch(r"[0-9a-f]{64}", str(value["sha256"]))
    ):
        raise ConsumptionModuleConfigError(
            f"{field} must be exactly {{relpath, sha256}} with a lowercase 64-hex sha256"
        )
    return {"relpath": value["relpath"], "sha256": value["sha256"]}


def _parse_columns(columns: list, decls: list[ComponentDecl]) -> tuple[ColumnDecl, ...]:
    by_id = {d.component_id: d for d in decls}
    out: list[ColumnDecl] = []
    for index, entry in enumerate(columns):
        field = f"consumption_module.columns[{index}]"
        if not isinstance(entry, Mapping):
            raise ConsumptionModuleConfigError(f"{field} must be an object")
        keys = set(entry)
        if not _COLUMN_REQUIRED <= keys or keys - _COLUMN_REQUIRED - _COLUMN_OPTIONAL:
            raise ConsumptionModuleConfigError(
                f"{field} keys must be {sorted(_COLUMN_REQUIRED)} plus optional "
                f"{sorted(_COLUMN_OPTIONAL)}, got {sorted(keys)}"
            )
        column_id = _require_text(entry["column_id"], field=f"{field}.column_id")
        toggle = entry["toggle"]
        if toggle == RELISTEN:
            raise ConsumptionModuleConfigError(
                f"{field}: re-listen's same-flight columns are its 'shadow' state "
                "(replace-only and replace + drop, read in the same flight); it takes no column"
            )
        decl = by_id.get(toggle) if isinstance(toggle, str) else None
        if decl is None or decl.state != STATE_COLUMN:
            raise ConsumptionModuleConfigError(
                f"{field}.toggle {toggle!r} must name a listed component in 'column' state"
            )
        if entry["to"] != STATE_ON:
            raise ConsumptionModuleConfigError(
                f"{field}.to must be 'on': a column shows one component on over a "
                "delivered policy that carries it off"
            )
        level = entry["level"]
        if isinstance(level, bool) or level not in (1, 2):
            raise ConsumptionModuleConfigError(f"{field}.level must be 1 or 2")
        seed = entry.get("prepared_seed")
        out.append(ColumnDecl(
            column_id, toggle, STATE_ON, level,
            None if seed is None else _canonical(_pin(seed, field=f"{field}.prepared_seed")),
        ))
    ids = [c.column_id for c in out]
    if len(set(ids)) != len(ids):
        raise ConsumptionModuleConfigError("consumption_module.columns ids must be distinct")
    toggled = [c.toggle for c in out]
    for decl in decls:
        if decl.state == STATE_COLUMN and toggled.count(decl.component_id) != 1:
            raise ConsumptionModuleConfigError(
                f"component {decl.component_id!r} is in 'column' state and must be toggled "
                "by exactly one column"
            )
    if len({c.level for c in out}) > 1:
        raise ConsumptionModuleConfigError(
            "consumption_module.columns must share one level (one branch block per flight)"
        )
    return tuple(out)


# ---------------------------------------------------------------------------
# Compile (migration step 2).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComposedPolicy:
    """The compiler's output: the :data:`POLICY_OWNED_KEYS` blocks the
    runtime reads, the program it chose and its ceiling, and the provenance
    a header receipt names."""

    module_id: str
    module_version: str
    profile: str
    program_id: str
    program_ceiling: int
    components: tuple[ComponentDecl, ...]
    config_block_sha256: str
    blocks_json: str
    written_paths: tuple[str, ...]
    #: The lock version the block named (``None``: the carrier's ``lock_layer``).
    lock_version: str | None = None
    #: The carrier's roster-pin paths (``CarrierHooks.roster_pin_paths``).
    roster_paths: tuple[tuple[str, ...], ...] = ()

    def values(self) -> dict[str, object]:
        """A fresh copy of the compiled blocks (``POLICY_OWNED_KEYS``)."""

        return json.loads(self.blocks_json)

    def values_on_roster_of(self, target: Mapping[str, object]) -> dict[str, object]:
        """The compiled blocks with every roster pin taken from ``target``
        (a fragment or composed config): the module's policy on the target's
        own roster. A roster pin the target does not carry stays the lock's."""

        return _rebind_roster(self.values(), target, self.roster_paths)

    def apply_to(self, fragment: Mapping[str, object]) -> dict[str, object]:
        """``fragment`` with its policy-owned keys replaced by the compiled
        blocks; every other key -- and every roster pin -- is the
        fragment's own."""

        out = copy.deepcopy(dict(fragment))
        out.update(self.values_on_roster_of(fragment))
        return out


def _get_path(node: object, path: Sequence[str]) -> tuple[bool, object]:
    for key in path:
        if not isinstance(node, Mapping) or key not in node:
            return False, None
        node = node[key]
    return True, node


def _rebind_roster(
    compiled: dict[str, object], target: Mapping[str, object], paths: Sequence[Sequence[str]],
) -> dict[str, object]:
    """``compiled`` with the value at each roster-pin path replaced by
    ``target``'s, where both carry it (a pin is REPLACED, never added)."""

    for path in paths:
        found, value = _get_path(target, path)
        parent_found, parent = _get_path(compiled, path[:-1])
        if found and parent_found and isinstance(parent, dict) and path[-1] in parent:
            parent[path[-1]] = copy.deepcopy(value)
    return compiled


def policy_owned_values(values: Mapping[str, object]) -> dict[str, object]:
    """The :data:`POLICY_OWNED_KEYS` of a composed config or fragment, with
    the module's own declaration removed from ``native_episode`` (the block
    declares the policy; it is not part of what it compiles to)."""

    out = {key: copy.deepcopy(values[key]) for key in POLICY_OWNED_KEYS if key in values}
    # An optional tool block is owned only when present. Historical OFF blocks
    # remain the exact four-key layer and do not acquire an empty tool field.
    if "phase_tools" in values:
        out["phase_tools"] = copy.deepcopy(values["phase_tools"])
    episode = out.get("native_episode")
    if isinstance(episode, dict):
        episode.pop(CONSUMPTION_MODULE_CONFIG_KEY, None)
    return out


def _node(layer: dict, path: Sequence[str], *, field: str) -> dict:
    node: object = layer
    for key in path:
        if not isinstance(node, dict) or key not in node:
            raise ConsumptionModuleConfigError(
                f"{field}: the lock layer has no {'.'.join(path)!r} object"
            )
        node = node[key]
    if not isinstance(node, dict):
        raise ConsumptionModuleConfigError(f"{field}: {'.'.join(path)!r} is not an object")
    return node


class _Writer:
    """Writes leaves into the layer and refuses a leaf written twice: two
    components claiming one leaf is a composition conflict (decision 138),
    never a silent last-writer-wins."""

    def __init__(self, layer: dict) -> None:
        self.layer = layer
        self.written: dict[str, str] = {}

    def set(self, path: Sequence[str], value: object, *, component_id: str, replace_only: bool) -> None:
        dotted = ".".join(path)
        if dotted in self.written:
            raise ConsumptionModuleConfigError(
                f"components {self.written[dotted]!r} and {component_id!r} both write {dotted!r}"
            )
        parent = _node(self.layer, path[:-1], field=component_id)
        if replace_only and path[-1] not in parent:
            raise ConsumptionModuleConfigError(
                f"{component_id}: the lock layer has no {dotted!r} leaf to replace"
            )
        if not replace_only and path[-1] in parent:
            raise ConsumptionModuleConfigError(
                f"{component_id}: the lock layer already declares {dotted!r}"
            )
        parent[path[-1]] = copy.deepcopy(value)
        self.written[dotted] = component_id

    def chain(self, path: Sequence[str], compositions: Mapping[str, str], *, component_id: str) -> None:
        """Replace an existing leaf by its registered composition with a
        stage (a deliver stage runs AFTER whatever normaliser the layer, or an
        earlier component, put there). The one sanctioned second write of a
        leaf: it never discards the earlier writer's choice, it composes it."""

        dotted = ".".join(path)
        parent = _node(self.layer, path[:-1], field=component_id)
        current = parent.get(path[-1])
        composed = compositions.get(current) if isinstance(current, str) else None
        if composed is None:
            raise ConsumptionModuleConfigError(
                f"{component_id}: no registered composition of {dotted} = {current!r} with "
                f"this stage; composable: {sorted(compositions)}"
            )
        parent[path[-1]] = composed
        prior = self.written.get(dotted)
        self.written[dotted] = component_id if prior is None else f"{prior}+{component_id}"


def _require_hook(hooks: CarrierHooks, name: str, component_id: str) -> object:
    value = getattr(hooks, name)
    if value is None:
        raise ConsumptionModuleConfigError(
            f"component {component_id!r} needs the carrier hook {name!r}, which "
            f"profile {hooks.profile!r} does not provide (no analogue on this carrier)"
        )
    return value


def _compile_node_presentation(params: Mapping, writer: _Writer) -> None:
    """Select existing presentation paths without granting tools or adding contacts.

    Node instructions remain independent phase material. The narrow history option
    exposes the existing source-checked Reviewer projection; it does not invent a
    projection for other roles or discard the speech and supplied knowledge inputs.
    """
    if not params:
        raise ConsumptionModuleConfigError("node context presentation needs an explicit option")
    options = {
        "tool_schema_rendering": (
            ("native_episode", "tool_schema_rendering"), {"constant", "per-role"}),
        "reviewer_history_scope": (
            ("native_episode", "roles", "reviewer", "history_scope"),
            {"full", "latest-solver-and-local-tools"}),
    }
    for name, value in params.items():
        path, allowed = options[name]
        if not isinstance(value, str) or value not in allowed:
            raise ConsumptionModuleConfigError(f"invalid node context presentation {name}")
        parent = _node(writer.layer, path[:-1], field=NODE_CONTEXT_PRESENTATION)
        writer.set(path, value, component_id=NODE_CONTEXT_PRESENTATION,
                   replace_only=path[-1] in parent)


def _compile(block: ConsumptionModuleBlock, hooks: CarrierHooks) -> ComposedPolicy:
    from .controllers import (  # noqa: PLC0415
        RailsControllersError, default_phase_program, module_program_family_id,
    )

    if not isinstance(hooks, CarrierHooks):
        raise ConsumptionModuleConfigError("carrier_hooks must be a CarrierHooks")
    if hooks.profile != block.profile:
        raise ConsumptionModuleConfigError(
            f"block profile {block.profile!r} does not match the carrier hooks' "
            f"profile {hooks.profile!r}"
        )
    if block.lock is None:
        lock_layer = _require_hook(hooks, "lock_layer", "lock layer")()
    else:
        versions = dict(_require_hook(hooks, "lock_versions", f"lock {block.lock}"))
        if block.lock not in versions:
            raise ConsumptionModuleConfigError(
                f"lock {block.lock!r} is not a lock version of profile {hooks.profile!r}; "
                f"known: {sorted(versions)}"
            )
        lock_layer = versions[block.lock]()
    if not isinstance(lock_layer, Mapping) or set(lock_layer) not in (
        set(POLICY_OWNED_KEYS), set(DIRECT_LAYER_KEYS),
    ):
        raise ConsumptionModuleConfigError(
            f"the lock layer must carry exactly {list(POLICY_OWNED_KEYS)} (a system lock) or "
            f"{list(DIRECT_LAYER_KEYS)} (a direct layer)"
        )
    layer = json.loads(_canonical(dict(lock_layer)))
    direct_layer = "native_episode" not in layer
    lock_program = default_phase_program(str(layer["policy"]))
    if direct_layer:
        # Design 3.2 "bare" / 2b.3: the direct baseline of the shared
        # controller. It carries no episode, so it has no deliver node to
        # check and no block to declare; a native-role program is refused
        # here because the loader refuses it without a native_episode block.
        if lock_program.stop_rule == "native-role-episode":
            raise ConsumptionModuleConfigError(
                f"a direct lock layer cannot run the native-role program {layer['policy']!r}"
            )
    else:
        if CONSUMPTION_MODULE_CONFIG_KEY in layer["native_episode"]:
            raise ConsumptionModuleConfigError("the lock layer must not itself declare a module")
        if hooks.default_deliver_normaliser is not None:
            deliver = layer["native_episode"].get("deliver_normaliser")
            if not isinstance(deliver, Mapping) or deliver.get("normaliser") != hooks.default_deliver_normaliser():
                raise ConsumptionModuleConfigError(
                    "the lock layer's deliver node is not the carrier's default deliver "
                    f"normaliser {hooks.default_deliver_normaliser()!r}"
                )
    ceiling = lock_program.max_contacts
    if direct_layer and (block.armed() or block.columns):
        raise ConsumptionModuleConfigError(
            f"profile {hooks.profile!r} compiles onto a direct layer ({layer['policy']!r}): "
            "only the all-off block (the carrier admission gate, design 2b.3) compiles there; "
            f"armed {[d.component_id for d in block.armed()]} need a locked system layer"
        )
    writer = _Writer(layer)
    context_decl = block.component(NODE_CONTEXT_PRESENTATION)
    context_owns_tools = (
        context_decl is not None and context_decl.state == STATE_ON
        and "tool_schema_rendering" in context_decl.params
    )
    for decl in block.armed():
        cid, params = decl.component_id, decl.params
        if cid == NODE_CONTEXT_PRESENTATION:
            _compile_node_presentation(params, writer)
        elif cid in (AGREE_VOTE_SEED, CENTROID_BOUNDARY_KEY):
            seed = tuple(_require_hook(hooks, "decision_supply_path", cid))
            if cid == AGREE_VOTE_SEED:
                writer.set((*seed, "rank_weights", "w_agree"), params["w_agree"],
                           component_id=cid, replace_only=True)
                writer.set((*seed, "k"), params["k"], component_id=cid, replace_only=True)
                writer.set((*seed, "agreement_source"), params["agreement_source"],
                           component_id=cid, replace_only=False)
            else:
                writer.set((*seed, "facet_source"), params["facet_source"],
                           component_id=cid, replace_only=True)
        elif cid == CONSTRUCTION_STORE_BINDING:
            store_id = _require_text(params["store_id"], field="construction store")
            for field in ("snapshot", "release"):
                pin = params[field]
                if (not isinstance(pin, Mapping) or set(pin) != {"relpath", "sha256"}
                        or not re.fullmatch(r"[0-9a-f]{64}", str(pin["sha256"]))
                        or not isinstance(pin["relpath"], str)
                        or not pin["relpath"] or pin["relpath"].startswith("/")
                        or ".." in pin["relpath"].split("/")):
                    raise ConsumptionModuleConfigError("construction store requires source pins")
                writer.set(("knowledge_stores", store_id, field), dict(pin),
                           component_id=cid, replace_only=True)
        elif cid == KNOWLEDGE_CONSUMPTION_OPPORTUNITY:
            if params["mode"] not in {"targeted", "reread"}:
                raise ConsumptionModuleConfigError("knowledge opportunity mode is invalid")
            store_id = _require_text(params["store_id"], field="knowledge opportunity store")
            _node(layer, ("knowledge_stores", store_id), field=cid)
            for role in ("reviewer", "planner"):
                template = _require_text(params[role + "_template"], field=role + " template")
                writer.set(("phase_material", role, "instruction_template"), template,
                           component_id=cid, replace_only=True)
            if "reviewer_response_format_id" in params:
                reviewer_contract = params["reviewer_response_format_id"]
                if reviewer_contract != "saea-slot-review-handoff-v1":
                    raise ConsumptionModuleConfigError("unregistered Reviewer handoff contract")
                writer.set(("phase_material", "reviewer", "response_format_id"), reviewer_contract,
                           component_id=cid, replace_only=True)
            if "solver_template" in params:
                template = _require_text(params["solver_template"], field="solver template")
                writer.set(("phase_material", "solver", "instruction_template"), template,
                           component_id=cid, replace_only=True)
            if "knowledge_binding" in params:
                binding = params["knowledge_binding"]
                if not isinstance(binding, Mapping) or set(binding) != {"snapshot", "release"}:
                    raise ConsumptionModuleConfigError("knowledge binding needs snapshot and release")
                for key, pin in binding.items():
                    normalized = _pin(pin, field="knowledge binding " + key)
                    if (normalized["relpath"].startswith("/") or "\\" in normalized["relpath"]
                            or ":" in normalized["relpath"] or ".." in normalized["relpath"].split("/")):
                        raise ConsumptionModuleConfigError("knowledge binding must stay under data root")
                    writer.set(("knowledge_stores", store_id, key), normalized,
                               component_id=cid, replace_only=True)
            value_limit = params.get("value_limit", 2)
            if type(value_limit) is not int or not 1 <= value_limit <= 2:
                raise ConsumptionModuleConfigError("knowledge opportunity permits one or two values")
            episode = layer["native_episode"]
            if episode["max_revisions"] != 1:
                raise ConsumptionModuleConfigError("knowledge opportunity requires one revision")
            old_iterations = episode["roles"]["planner"]["max_iterations"]
            if old_iterations != 1:
                raise ConsumptionModuleConfigError("knowledge opportunity requires default Planner iterations")
            writer.set(("native_episode", "roles", "planner", "max_iterations"), 2,
                       component_id=cid, replace_only=True)
            writer.set(("native_episode", "review_handoff"), "slot-issues-v1",
                       component_id=cid, replace_only=False)
            if not context_owns_tools:
                # Preserve historical bytes unless presentation explicitly owns this leaf.
                writer.set(("native_episode", "tool_schema_rendering"), "constant",
                           component_id=cid, replace_only=False)
            writer.set(("phase_tools",), {"planner": {
                "mode": "native-tools", "source_authority_role": "planner",
                "allowed_tools": ["saea-tool-knowledge-target-lookup-v1"],
                "knowledge_views": ["text"], "knowledge_store_ids": [store_id],
                "candidate_limit": 2, "knowledge_values_per_candidate": 1,
                "knowledge_value_limit": value_limit, "knowledge_target_axis": "slot-type",
                "knowledge_selection_mode": params["mode"], "max_calls_per_sample": 1,
            }}, component_id=cid, replace_only=False)
            ceiling += 2
        elif cid == SOLVER_CITATION_CONTRACT:
            writer.set(("phase_material", "solver", "instruction_template"),
                       params["instruction_template"], component_id=cid, replace_only=True)
            writer.set(("phase_material", "solver", "response_format_id"),
                       params["response_format_id"], component_id=cid, replace_only=True)
            writer.set(("native_episode", "deliver_normaliser", "normaliser"),
                       params["deliver_normaliser"], component_id=cid, replace_only=True)
        elif cid == REVIEWER_G5_REPAIR:
            reviewer = layer["phase_material"].get("reviewer")
            if isinstance(reviewer, Mapping) and reviewer.get("instruction_template") == params["instruction_template"]:
                raise ConsumptionModuleConfigError(
                    f"{cid}: the lock layer already carries this Reviewer template (a lock that "
                    "took the repair in, e.g. v2.1 = v2.0 + G5, owner decision 204); list it 'off'"
                )
            writer.set(("phase_material", "reviewer", "instruction_template"),
                       params["instruction_template"], component_id=cid, replace_only=True)
        elif cid == RELISTEN:
            from .relisten import RelistenError, parse_relisten  # noqa: PLC0415

            try:
                relisten = parse_relisten(dict(params))
            except RelistenError as error:
                raise ConsumptionModuleConfigError(f"relisten params are invalid: {error}") from error
            writer.set(("native_episode", "relisten"), params, component_id=cid, replace_only=False)
            ceiling += relisten.extra_contacts_ceiling
        elif cid == SCOPE_RULE:
            stage = _require_hook(hooks, "deliver_stages", cid).get(cid)
            if not isinstance(stage, Mapping):
                raise ConsumptionModuleConfigError(
                    f"profile {hooks.profile!r} registers no {cid!r} deliver stage"
                )
            if _canonical(dict(params)) != _canonical(dict(stage["params"])):
                raise ConsumptionModuleConfigError(
                    f"{cid} params must equal the registered stage's pins "
                    "(thresholds and the table's relpath and sha256)"
                )
            writer.chain(("native_episode", "deliver_normaliser", "normaliser"),
                         stage["compositions"], component_id=cid)
        elif cid in PERCEPTION_AXIS_COMPONENTS:
            continue  # compiled below, with the columns (one branch block)
        else:  # pragma: no cover - the parse refuses every other armed id
            raise ConsumptionModuleConfigError(f"component {cid!r} does not compile in v1")
    level = _compile_perception_branches(block, hooks, writer)
    if level is not None:
        from .supply_variants import perception_branch_ceiling  # noqa: PLC0415

        branch_count = len(block.columns) + 2
        ceiling = perception_branch_ceiling(base_ceiling=ceiling, branch_count=branch_count, level=level)
    solver_material = layer["phase_material"].get("solver")
    contract = solver_material.get("response_format_id") if isinstance(solver_material, Mapping) else None
    flown = (
        dict(hooks.flown_programs or {}) if level is None
        else {
            (c, f): pid for (lv, c, f), pid in dict(hooks.flown_branch_programs or {}).items()
            if lv == level
        }
    )
    program_id = flown.get((ceiling, contract))
    reviewer_material = layer["phase_material"].get("reviewer")
    reviewer_contract = (reviewer_material.get("response_format_id")
                         if isinstance(reviewer_material, Mapping) else None)
    if reviewer_contract == "saea-slot-review-handoff-v1":
        if ceiling != 13 or contract is not None or level is not None:
            raise ConsumptionModuleConfigError(
                "Reviewer handoff contract requires the registered uncited 13-contact phase shape"
            )
        program_id = "phase-native-slot-review-contract-v1"
    if program_id is None:
        if contract is not None:
            raise ConsumptionModuleConfigError(
                f"no program carries Solver contract {contract!r} at ceiling {ceiling}: the "
                "program family is the lock's uncited phase shape, and no flown program "
                "matches -- register one before composing this set"
            )
        try:
            program_id = module_program_family_id(ceiling)
        except RailsControllersError as error:
            raise ConsumptionModuleConfigError(str(error)) from error
    program = default_phase_program(program_id)
    if program.max_contacts != ceiling:
        raise ConsumptionModuleConfigError(
            f"program {program_id!r} has ceiling {program.max_contacts}, the module "
            f"computed {ceiling}"
        )
    if "solver" in program.phase_names() and program.phase("solver").response_format_id != contract:
        raise ConsumptionModuleConfigError(
            f"program {program_id!r} declares Solver contract "
            f"{program.phase('solver').response_format_id!r}; the module composed {contract!r}"
        )
    if layer["policy"] != program_id:
        writer.set(("policy",), program_id, component_id="program", replace_only=True)
    return ComposedPolicy(
        module_id=block.module_id,
        module_version=CONSUMPTION_MODULE_VERSION,
        profile=block.profile,
        program_id=program_id,
        program_ceiling=ceiling,
        components=block.components,
        config_block_sha256=block.block_sha256,
        blocks_json=_canonical(layer),
        written_paths=tuple(sorted(writer.written)),
        lock_version=block.lock,
        roster_paths=tuple(tuple(p) for p in (hooks.roster_pin_paths or ())),
    )


def _compile_perception_branches(
    block: ConsumptionModuleBlock, hooks: CarrierHooks, writer: _Writer,
) -> int | None:
    """Compile the Perception components into ONE branch block: one B branch
    per column (in column order), the twin T, then the delivering branch A
    carrying the ``on`` components' axes (ruling R3, admitted only). Returns
    the block's level, or ``None`` when no Perception component is armed."""

    armed = [d for d in block.armed() if d.component_id in PERCEPTION_AXIS_COMPONENTS]
    if not armed:
        return None
    on = [d for d in armed if d.state == STATE_ON]
    admissions = dict(hooks.delivered_path_admissions or {})
    for decl in on:
        if admissions.get(decl.component_id) != decl.record:
            raise ConsumptionModuleConfigError(
                f"component {decl.component_id!r} cannot be 'on': no admitting record for the "
                f"delivered path on profile {hooks.profile!r} (ruling R3: a Perception component "
                "rides the delivered path only after its column read NOMINATED it and a composed "
                "read carried it; until then it is a 'column')"
            )
    if not block.columns:
        raise ConsumptionModuleConfigError(
            "a delivered-path Perception axis rides the branch block's delivering branch A; "
            "declare at least one column"
        )
    frame = _require_hook(hooks, "perception_branch_frame", armed[0].component_id)
    by_id = {d.component_id: d for d in armed}
    rows = []
    for column in block.columns:
        params = by_id[column.toggle].params
        row = {"branch_id": column.column_id, "max_supplied_items": params["max_supplied_items"]}
        for key in PERCEPTION_AXIS_COMPONENTS[column.toggle]:
            row[key] = params[key]
        if column.prepared_seed is not None:
            row["prepared_seed"] = column.prepared_seed
        rows.append(row)
    delivering = {
        "branch_id": frame["delivering_branch_id"], "deliver": True,
        "max_supplied_items": frame["max_supplied_items"],
    }
    for decl in on:
        for key in PERCEPTION_AXIS_COMPONENTS[decl.component_id]:
            delivering[key] = decl.params[key]
    rows.append({
        "branch_id": frame["twin_branch_id"], "max_supplied_items": frame["max_supplied_items"],
        "replicate_of": frame["delivering_branch_id"],
    })
    rows.append(delivering)
    level = block.columns[0].level
    branches_block = {
        "branches": rows, "fit_estimate": dict(frame["fit_estimate"]), "level": level,
    }
    writer.set(tuple(frame["block_path"]), branches_block,
               component_id="+".join(d.component_id for d in armed), replace_only=False)
    return level


def delivered_perception_axes(raw_block: object) -> tuple[str, ...]:
    """The branch-row axes a declared block's ``on`` Perception components
    set on the delivering branch A -- what the loader passes to
    ``parse_perception_branches(..., delivering_axes_admitted=)``. ``()`` for
    an absent or malformed block (the loader's own verification refuses the
    latter) and for every block with no Perception component ``on``."""

    if not isinstance(raw_block, Mapping) or not isinstance(raw_block.get("components"), list):
        return ()
    axes: set[str] = set()
    for entry in raw_block["components"]:
        if (
            isinstance(entry, Mapping) and entry.get("state") == STATE_ON
            and entry.get("component_id") in PERCEPTION_AXIS_COMPONENTS
        ):
            axes.update(
                key for key in PERCEPTION_AXIS_COMPONENTS[entry["component_id"]] if key != "contrast_pairs"
            )
    return tuple(sorted(axes))


class EvidenceConsumptionModule:
    """The registry entry: ``module(block, carrier_hooks) -> ComposedPolicy``.
    A policy compiler, never a controller (no ``initial_contact`` /
    ``advance``) and never a model client."""

    id = CONSUMPTION_MODULE_ID
    version = CONSUMPTION_MODULE_VERSION

    def __call__(self, block: ConsumptionModuleBlock, carrier_hooks: CarrierHooks) -> ComposedPolicy:
        return _compile(block, carrier_hooks)


CONSUMPTION_MODULES.register(CONSUMPTION_MODULE_ID, EvidenceConsumptionModule())


def compile_module(
    block: Mapping[str, object] | ConsumptionModuleBlock,
    carrier_hooks: CarrierHooks,
    *,
    repo_root: Path | None = None,
) -> ComposedPolicy:
    """Compile one module block for one carrier. PURE: no core, no runtime,
    no network; it reads only the carrier's lock layer through its hook and
    the registered phase programs."""

    parsed = (
        block if isinstance(block, ConsumptionModuleBlock)
        else parse_consumption_module_block(block, repo_root=repo_root)
    )
    entry = CONSUMPTION_MODULES.resolve(parsed.module_id)
    return entry(parsed, carrier_hooks)


def _leaf_paths(node: object, prefix: str = "") -> dict[str, object]:
    if isinstance(node, Mapping) and node:
        out: dict[str, object] = {}
        for key, value in node.items():
            out.update(_leaf_paths(value, f"{prefix}.{key}" if prefix else str(key)))
        return out
    return {prefix: node}


def differing_paths(left: Mapping[str, object], right: Mapping[str, object]) -> list[str]:
    """Leaf paths whose values differ between two config mappings."""

    a, b = _leaf_paths(left), _leaf_paths(right)
    missing = object()
    return sorted(k for k in set(a) | set(b) if a.get(k, missing) != b.get(k, missing))


def is_module_off_block(raw_block: object, *, repo_root: Path | None = None) -> bool:
    """Whether ``raw_block`` is a well-formed block whose every component is
    ``off`` and which declares no column: the module's OFF arm (the harness
    ``module`` switch class, ruling R2), which compiles to its lock layer."""

    try:
        parsed = parse_consumption_module_block(raw_block, repo_root=repo_root)
    except ConsumptionModuleConfigError:
        return False
    return not parsed.armed() and not parsed.columns


def verify_declared_module(
    raw_block: object, values: Mapping[str, object], *, repo_root: Path | None = None,
) -> str:
    """The loader's check (``rails.native_episode_config``): a config that
    DECLARES a module block must carry exactly the blocks the block compiles
    to, so a declared component can never be silently unarmed. Returns the
    block's canonical text."""

    parsed = parse_consumption_module_block(raw_block, repo_root=repo_root)
    composed = compile_module(
        parsed, resolve_carrier_hooks(parsed.profile, repo_root=repo_root), repo_root=repo_root,
    )
    declared = policy_owned_values(values)
    diff = differing_paths(composed.values_on_roster_of(values), declared)
    if diff:
        raise ConsumptionModuleConfigError(
            "the config's own policy blocks differ from what its consumption_module "
            f"block compiles to at {diff[:12]}"
        )
    return parsed.block_json


# ---------------------------------------------------------------------------
# The per-row header receipt (design section 2.5).
# ---------------------------------------------------------------------------


def module_header_receipt(
    composed: ComposedPolicy, *, node_receipts: Sequence[Mapping[str, str]] = (),
) -> dict[str, object]:
    """The ``saea-consumption-module-v1`` header receipt of one row. It
    carries no content of its own -- only the module identity, the compiled
    component list with each entry's admitting record and state, the
    config-block sha256, and pointers to the node-action receipts -- so
    replay re-derives it from the node receipts."""

    pointers = []
    for index, pointer in enumerate(node_receipts):
        if not isinstance(pointer, Mapping) or set(pointer) != {"schema", "pointer"}:
            raise ConsumptionModuleConfigError(
                f"node_receipts[{index}] must be exactly {{schema, pointer}}"
            )
        if pointer["schema"] not in NODE_RECEIPT_SCHEMAS:
            raise ConsumptionModuleConfigError(
                f"node_receipts[{index}].schema {pointer['schema']!r} is not a node-action "
                f"receipt schema; known: {sorted(NODE_RECEIPT_SCHEMAS)}"
            )
        _require_text(pointer["pointer"], field=f"node_receipts[{index}].pointer")
        pointers.append({"schema": pointer["schema"], "pointer": pointer["pointer"]})
    return {
        "schema": CONSUMPTION_MODULE_RECEIPT_SCHEMA,
        "module_id": composed.module_id,
        "module_version": composed.module_version,
        "profile": composed.profile,
        "program_id": composed.program_id,
        "program_ceiling": composed.program_ceiling,
        "config_block_sha256": composed.config_block_sha256,
        "components": [
            {
                "component_id": decl.component_id,
                "state": decl.state,
                "admitted_by": decl.admitted_by,
                "record": decl.record,
            }
            for decl in composed.components
        ],
        "node_receipts": pointers,
    }


MODULE_HEADER_RECEIPT_KEYS = frozenset({
    "schema", "module_id", "module_version", "profile", "program_id", "program_ceiling",
    "config_block_sha256", "components", "node_receipts",
})


def validate_module_header_receipt(receipt: object) -> Mapping[str, object]:
    """Refuse a header receipt that is not exactly the schema's shape."""

    if not isinstance(receipt, Mapping) or set(receipt) != MODULE_HEADER_RECEIPT_KEYS:
        raise ConsumptionModuleConfigError(
            f"a {CONSUMPTION_MODULE_RECEIPT_SCHEMA} receipt carries exactly "
            f"{sorted(MODULE_HEADER_RECEIPT_KEYS)}"
        )
    if receipt["schema"] != CONSUMPTION_MODULE_RECEIPT_SCHEMA:
        raise ConsumptionModuleConfigError(f"schema must be {CONSUMPTION_MODULE_RECEIPT_SCHEMA!r}")
    if receipt["module_id"] not in CONSUMPTION_MODULES.names():
        raise ConsumptionModuleConfigError(f"module_id {receipt['module_id']!r} is not registered")
    if not re.fullmatch(r"[0-9a-f]{64}", str(receipt["config_block_sha256"])):
        raise ConsumptionModuleConfigError("config_block_sha256 must be a lowercase 64-hex SHA-256")
    for entry in receipt["components"]:
        if not isinstance(entry, Mapping) or entry.get("component_id") not in _CATALOGUE:
            raise ConsumptionModuleConfigError("components entries must name catalogued components")
        if entry.get("state") not in COMPONENT_STATES:
            raise ConsumptionModuleConfigError("components entries must carry a known state")
    for pointer in receipt["node_receipts"]:
        if not isinstance(pointer, Mapping) or pointer.get("schema") not in NODE_RECEIPT_SCHEMAS:
            raise ConsumptionModuleConfigError("node_receipts entries must name node-action schemas")
    return receipt


__all__ = [
    "AGREE_VOTE_SEED",
    "CENTROID_BOUNDARY_KEY",
    "COMPONENT_CATALOGUE",
    "COMPONENT_STATES",
    "CONSUMPTION_MODULE_CONFIG_KEY",
    "CONSUMPTION_MODULE_ID",
    "CONSUMPTION_MODULE_RECEIPT_SCHEMA",
    "CONSUMPTION_MODULE_VERSION",
    "CarrierHooks",
    "ColumnDecl",
    "ComponentDecl",
    "ComposedPolicy",
    "ConsumptionModuleBlock",
    "ConsumptionModuleConfigError",
    "EvidenceConsumptionModule",
    "FORCED_CANDIDATE_LIST",
    "KEY_SOURCE_K6P",
    "PERCEPTION_AXIS_COMPONENTS",
    "TOP2_CONTRAST",
    "NODE_RECEIPT_SCHEMAS",
    "POLICY_OWNED_KEYS",
    "RELISTEN",
    "REVIEWER_G5_REPAIR",
    "SCOPE_RULE",
    "SOLVER_CITATION_CONTRACT",
    "carrier_hooks_for_lock_key",
    "compile_module",
    "delivered_perception_axes",
    "is_module_off_block",
    "differing_paths",
    "module_header_receipt",
    "parse_consumption_module_block",
    "policy_owned_values",
    "resolve_carrier_hooks",
    "validate_module_header_receipt",
    "verify_declared_module",
]
