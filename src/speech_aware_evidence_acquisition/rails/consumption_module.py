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

from ..core.base import CONSUMPTION_MODULES
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

STATE_ON = "on"
STATE_OFF = "off"
STATE_SHADOW = "shadow"
STATE_COLUMN = "column"
COMPONENT_STATES: tuple[str, ...] = (STATE_ON, STATE_OFF, STATE_SHADOW, STATE_COLUMN)

_BLOCK_REQUIRED = frozenset({"module_id", "profile", "components"})
_BLOCK_OPTIONAL = frozenset({"columns"})
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


AGREE_VOTE_SEED = "agree-vote-seed"
CENTROID_BOUNDARY_KEY = "centroid-boundary-key"
SOLVER_CITATION_CONTRACT = "solver-citation-contract"
REVIEWER_G5_REPAIR = "reviewer-g5-repair"
RELISTEN = "relisten"

COMPONENT_CATALOGUE: tuple[ComponentSpec, ...] = (
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
    ComponentSpec(
        "top2-contrast", "SUPPLY presentation -> Perception", frozenset(), frozenset(),
        pending="migration step 4 (delivered-path Perception policy)",
    ),
    ComponentSpec(
        "forced-candidate-list", "Perception response contract", frozenset(), frozenset(),
        pending="migration step 4 (delivered-path Perception policy)",
    ),
    ComponentSpec(
        "scope-rule", "USE, deliver node", frozenset(), frozenset(),
        pending="migration step 3 (deterministic USE stage)",
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
    """

    profile: str | None = None
    lock_layer: Callable[[], Mapping[str, object]] | None = None
    decision_supply_path: tuple[str, ...] | None = None
    flown_programs: Mapping[tuple[int, str | None], str] | None = None
    decision_candidates: Callable[..., tuple[str, ...]] | None = None
    max_decision_candidates: Callable[[], int] | None = None
    delivered_units: Callable[..., tuple[str, ...]] | None = None
    default_deliver_normaliser: Callable[[], str] | None = None


def resolve_carrier_hooks(profile: str, *, repo_root: Path | None = None) -> CarrierHooks:
    """The hooks of ``profile``, from ``rails/adapters/<profile>_module_hooks.py``
    (its ``carrier_module_hooks(repo_root=...)``). Refuses a profile with no
    hooks file: a carrier without an adapter cannot carry the module."""

    if not isinstance(profile, str) or _PROFILE.fullmatch(profile) is None:
        raise ConsumptionModuleConfigError(f"profile must match {_PROFILE.pattern}, got {profile!r}")
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
class ConsumptionModuleBlock:
    module_id: str
    profile: str
    components: tuple[ComponentDecl, ...]
    block_sha256: str
    block_json: str

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
    file; params whose key set is not exactly the component's; a non-empty
    ``columns`` list (columns compile from migration step 4)."""

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
    if columns:
        raise ConsumptionModuleConfigError(
            "consumption_module.columns compile from migration step 4; v1 of the "
            "compiler accepts only an empty list"
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
        if armed and set(params) != spec.params:
            raise ConsumptionModuleConfigError(
                f"{field}.params of {component_id!r} must carry exactly "
                f"{sorted(spec.params)}, got {sorted(params)}"
            )
        decls.append(ComponentDecl(
            component_id, state, admitted_by, record, _canonical(dict(params)),
        ))
    block_json = _canonical(dict(raw))
    return ConsumptionModuleBlock(
        module_id=module_id,
        profile=profile,
        components=tuple(decls),
        block_sha256=_sha256_text(block_json),
        block_json=block_json,
    )


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

    def values(self) -> dict[str, object]:
        """A fresh copy of the compiled blocks (``POLICY_OWNED_KEYS``)."""

        return json.loads(self.blocks_json)

    def apply_to(self, fragment: Mapping[str, object]) -> dict[str, object]:
        """``fragment`` with its policy-owned keys replaced by the compiled
        blocks; every other key is carried unchanged."""

        out = copy.deepcopy(dict(fragment))
        out.update(self.values())
        return out


def policy_owned_values(values: Mapping[str, object]) -> dict[str, object]:
    """The :data:`POLICY_OWNED_KEYS` of a composed config or fragment, with
    the module's own declaration removed from ``native_episode`` (the block
    declares the policy; it is not part of what it compiles to)."""

    out = {key: copy.deepcopy(values[key]) for key in POLICY_OWNED_KEYS if key in values}
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


def _require_hook(hooks: CarrierHooks, name: str, component_id: str) -> object:
    value = getattr(hooks, name)
    if value is None:
        raise ConsumptionModuleConfigError(
            f"component {component_id!r} needs the carrier hook {name!r}, which "
            f"profile {hooks.profile!r} does not provide (no analogue on this carrier)"
        )
    return value


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
    lock_layer = _require_hook(hooks, "lock_layer", "lock layer")()
    if not isinstance(lock_layer, Mapping) or set(lock_layer) != set(POLICY_OWNED_KEYS):
        raise ConsumptionModuleConfigError(
            f"the lock layer must carry exactly {list(POLICY_OWNED_KEYS)}"
        )
    layer = json.loads(_canonical(dict(lock_layer)))
    if CONSUMPTION_MODULE_CONFIG_KEY in layer["native_episode"]:
        raise ConsumptionModuleConfigError("the lock layer must not itself declare a module")
    lock_program = default_phase_program(str(layer["policy"]))
    ceiling = lock_program.max_contacts
    writer = _Writer(layer)
    for decl in block.armed():
        cid, params = decl.component_id, decl.params
        if cid in (AGREE_VOTE_SEED, CENTROID_BOUNDARY_KEY):
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
        elif cid == SOLVER_CITATION_CONTRACT:
            writer.set(("phase_material", "solver", "instruction_template"),
                       params["instruction_template"], component_id=cid, replace_only=True)
            writer.set(("phase_material", "solver", "response_format_id"),
                       params["response_format_id"], component_id=cid, replace_only=True)
            writer.set(("native_episode", "deliver_normaliser", "normaliser"),
                       params["deliver_normaliser"], component_id=cid, replace_only=True)
        elif cid == REVIEWER_G5_REPAIR:
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
        else:  # pragma: no cover - the parse refuses every other armed id
            raise ConsumptionModuleConfigError(f"component {cid!r} does not compile in v1")
    solver_material = layer["phase_material"].get("solver")
    contract = solver_material.get("response_format_id") if isinstance(solver_material, Mapping) else None
    flown = dict(hooks.flown_programs or {})
    program_id = flown.get((ceiling, contract))
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
    )


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
    diff = differing_paths(composed.values(), declared)
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
    "ComponentDecl",
    "ComposedPolicy",
    "ConsumptionModuleBlock",
    "ConsumptionModuleConfigError",
    "EvidenceConsumptionModule",
    "NODE_RECEIPT_SCHEMAS",
    "POLICY_OWNED_KEYS",
    "RELISTEN",
    "REVIEWER_G5_REPAIR",
    "SOLVER_CITATION_CONTRACT",
    "compile_module",
    "differing_paths",
    "module_header_receipt",
    "parse_consumption_module_block",
    "policy_owned_values",
    "resolve_carrier_hooks",
    "validate_module_header_receipt",
    "verify_declared_module",
]
