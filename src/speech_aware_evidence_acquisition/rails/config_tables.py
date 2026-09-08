"""WAVE W4: the four config tables, each with a null arm.

Owner Decision 11-B of 2026-09-08, item #6 of the openJiuwen implementation
assessment's change list (``docs/readiness/
2026-09-08-openjiuwen-implementation-assessment-v1.md`` section 7). The
design note's admission gate (``docs/readiness/
2026-09-08-agent-system-episode-and-core-pressure-v1.md`` section 8) requires
that **module ON versus module OFF is one config key on one harness, never a
second code path**. Section 7 of the assessment measured how far that is from
true today: of the seven harness modules exactly one is cleanly one key (the
silence tail) and one is nearly so (the slot schema, whose OFF arm still
changes the program id and the contact count); the other five need a
``policy`` change, a ``scorers`` change or a policy subclass to turn off,
which makes the OFF arm a different code path and therefore not a twin.

This module closes that gap by giving every module a home in one of four
config tables, each of which is:

* an object declared at the TOP LEVEL of a composed config fragment, exactly
  as ``phase_material`` / ``phase_supply`` / ``phase_review`` already are, so
  it rides ``core.config.compose``'s config hash with no new plumbing;
* validated FAIL-CLOSED here, before a run starts; and
* equipped with a NULL ARM whose composed config hash is byte-identical to
  the table being absent (``core.config.NULL_ARM_TABLE_KEYS`` /
  :func:`core.config.drop_null_arms`), so "module off" and "module never
  declared" are the same cell identity.

The four tables
---------------

============================ ============================================
table                        what one entry switches
============================ ============================================
``observe`` (per phase)      the Observer's mode: silence tail, speaker-turn
                             unit plan, selective re-listen (margin, budget,
                             derivation kind, flag source)
``knowledge_views``          the knowledge the phase sees: the wrapped
(per phase)                  ``phase_material`` entry (its ``state_fill`` IS
                             the view) and the wrapped ``phase_supply`` entry
                             (the retrieval provider)
``judges`` (per phase)       the Reviewer: W1's ``phase_review`` entry, judge
                             ids plus ``on_flag``
``toolkits`` (per run)       which W3 task-type toolkit row is armed, and for
                             which agent roles
============================ ============================================

Wrapping, not rewriting
-----------------------

``knowledge_views`` and ``judges`` WRAP the blocks W1/E1/E6 already ship and
change none of their bytes: a ``knowledge_views.<phase>.material`` object is
the same object a ``phase_material.<phase>`` entry carries, handed to
``rails.phase_material.load_phase_material_specs`` verbatim; the same holds
for ``supply`` and ``rails.phase_supply``, and for ``judges`` and
``rails.phase_review``. There is exactly one new rule: a fragment may declare
the flat block OR the table, never both, because two spellings of one switch
is how a cell ends up with two identities.

The tables therefore add no second validator, no second registry and no
second code path. Every id inside them keeps resolving in a ``core.base``
registry, which is what ``scripts/checks/engineering_base_check.py`` reads
out of source -- including the any-depth ``judges`` rule that check already
carries "so a future top-level ``judges`` list (the design note's own 'judges
config table with a null arm') [is caught] without a second rule".

Why the knowledge table is spelled ``knowledge_views``
------------------------------------------------------

The brief's working name for it is ``knowledge``. That spelling is already
taken at the top level of a composed fragment:
``configs/experiment/a2t-g3-plain-english-v1.json`` declares a ``knowledge``
object of card-build provenance, and ``core.config.compose`` refuses a
top-level key defined by two fragments. A ``knowledge`` table would therefore
be permanently uncomposable with that cell -- fail-closed, at the worst
possible moment. ``knowledge_views`` is the assessment's own spelling for the
same object (section 7: ``knowledge_views: {slots: ... | null}``), it collides
with nothing, and it says what the table holds.

What this module does NOT do
----------------------------

It parses, validates and hashes. It runs nothing: turning a validated
:class:`ConfigTables` into an ``ObserveStep``, a ``review_for_phase`` or an
armed toolkit is the phase-program dispatch in ``core/flight/runtime.py``,
which belongs to the wave that owns that file. Model-free, import-light, no
model/tool/network contact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..core.base import JUDGES, CoreError
from ..core.config import NULL_ARM_TABLE_KEYS
from .controllers import PhaseProgram
from .errors import RailsError
from .hashing import content_hash
from .observe import ObserveConfig
from .phase_material import PhaseMaterialSpec, load_phase_material_specs
from .phase_review import PhaseReviewSpec, load_phase_review_specs
from .phase_supply import PhaseSupplySpec, load_phase_supply_specs

CONFIG_TABLES_SCHEMA = "saea-config-tables-v1"

#: The four table names, sorted, and identical to
#: ``core.config.NULL_ARM_TABLE_KEYS`` -- the hashing rule and the loaders
#: must never disagree about which keys are tables (asserted below).
OBSERVE_TABLE = "observe"
KNOWLEDGE_VIEWS_TABLE = "knowledge_views"
JUDGES_TABLE = "judges"
TOOLKITS_TABLE = "toolkits"
CONFIG_TABLE_NAMES = (JUDGES_TABLE, KNOWLEDGE_VIEWS_TABLE, OBSERVE_TABLE, TOOLKITS_TABLE)

assert CONFIG_TABLE_NAMES == NULL_ARM_TABLE_KEYS, (
    "the config tables and the null-arm hashing rule must name the same keys"
)

#: The flat block each wrapping table replaces. A fragment declares one or the
#: other, never both (:func:`_assert_not_double_declared`).
WRAPPED_FLAT_KEYS = {
    JUDGES_TABLE: ("phase_review",),
    KNOWLEDGE_VIEWS_TABLE: ("phase_material", "phase_supply"),
}

#: The Earnings obs-loop's own flat observe knobs (``reproduction.obs_loop``).
#: They are the pre-table spelling of two of the ``observe`` table's entries
#: and stay readable on that policy path until Earnings moves onto
#: ``FlightRuntime`` (assessment changes #8/#9). Declaring both spellings in
#: one fragment is refused for the same reason as any other double
#: declaration.
LEGACY_OBSERVE_KEYS = (
    "obs_slice_tail_silence_seconds",
    "obs_unit_plan",
    "obs_unit_plan_sha256",
)

_OBSERVE_ENTRY_KEYS = frozenset({"tail_silence_seconds", "unit_plan", "relisten"})
_KNOWLEDGE_VIEW_ENTRY_KEYS = frozenset({"material", "supply"})
_JUDGES_ENTRY_KEYS = frozenset({"judges", "on_flag", "params"})
_TOOLKITS_ENTRY_KEYS = frozenset({"task_type", "roles"})

_PINNED_FILE_KEYS = frozenset({"relpath", "sha256"})
_RELISTEN_KEYS = frozenset(
    {
        "judges",
        "fixture",
        "context_margin_seconds",
        "max_relistens_per_sample",
        "derivation_kind",
    }
)

#: Every table's null arm, in the two spellings a fragment may use. Both drop
#: out of the config hash (``core.config.drop_null_arms``), so all three of
#: ``"observe": null``, ``"observe": {}`` and no ``observe`` key at all are
#: ONE cell identity rather than three.
NULL_ARMS: tuple[object, ...] = (None, {})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ConfigTableError(RailsError):
    """A config table, or one of its entries, violated the shape this module
    requires. Raised before a run starts and before any contact."""


def _is_null_arm(declared: object) -> bool:
    return declared is None or declared == {}


def _require_text(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigTableError(f"{field_name} must be a non-empty string")
    return value


def _require_sha256(value: object, *, field_name: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ConfigTableError(f"{field_name} must be a lowercase 64-hex SHA-256")
    return value


def _require_relpath(value: object, *, field_name: str) -> str:
    """A repo-relative POSIX path, under the same refusals ``core.config``
    applies to every other path-shaped config value: no backslash, not
    absolute, no empty or traversal segment."""

    text = _require_text(value, field_name=field_name)
    if "\\" in text:
        raise ConfigTableError(f"{field_name} must not contain a backslash: {text!r}")
    if text.startswith("/") or re.match(r"^[A-Za-z]:", text):
        raise ConfigTableError(f"{field_name} must be relative, got {text!r}")
    if any(part in ("", ".", "..") for part in text.split("/")):
        raise ConfigTableError(
            f"{field_name} contains an empty or traversal segment: {text!r}"
        )
    return text


def _require_mapping(value: object, *, field_name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ConfigTableError(f"{field_name} must be an object")
    return value


def _reject_unknown_keys(
    entry: Mapping[str, object], known: frozenset[str], *, field_name: str
) -> None:
    extra = sorted(set(entry) - known)
    if extra:
        raise ConfigTableError(
            f"{field_name} carries unknown key(s) {extra}; known keys are "
            f"{sorted(known)}"
        )


def _assert_not_double_declared(values: Mapping[str, object], table: str) -> None:
    """A fragment declares the flat block OR its wrapping table, never both."""

    for flat in WRAPPED_FLAT_KEYS.get(table, ()):
        if flat in values and not _is_null_arm(values.get(flat)):
            raise ConfigTableError(
                f"a fragment declares both {flat!r} and the {table!r} table; the "
                f"{table!r} table WRAPS {flat!r} without changing its bytes, so "
                "declaring both is two spellings of one switch and would give one "
                f"cell two identities -- keep {flat!r} or move it under "
                f"{table!r}, not both"
            )


# ---------------------------------------------------------------------------
# Table 1: observe
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PinnedFile:
    """A repo-relative artifact pinned by its exact bytes. Selecting
    different bytes changes the config hash, which is what makes an observe
    mode reproducible."""

    relpath: str
    sha256: str

    def validate(self, *, field_name: str) -> "PinnedFile":
        _require_relpath(self.relpath, field_name=f"{field_name}.relpath")
        _require_sha256(self.sha256, field_name=f"{field_name}.sha256")
        return self

    def as_json(self) -> dict[str, object]:
        return {"relpath": self.relpath, "sha256": self.sha256}


@dataclass(frozen=True)
class ReListenSpec:
    """The selective re-listen entry: WHERE the flags come from, and W2's own
    :class:`rails.observe.ObserveConfig` for the margin, the per-sample budget
    and the derivation kind.

    ``judges`` and ``fixture`` are mutually exclusive and one is required: a
    re-listen that has no flag source re-listens to nothing. ``judges`` is
    spelled as a LIST of ``core.base.JUDGES`` ids on purpose -- that is the
    key ``scripts/checks/engineering_base_check.py`` already resolves at any
    depth, so the flag source is checked by the same rule as every other
    judge id rather than by a second one.
    """

    config: ObserveConfig
    judges: tuple[str, ...] = ()
    fixture: PinnedFile | None = None

    def validate(self, *, field_name: str) -> "ReListenSpec":
        self.config.validate()
        if bool(self.judges) == (self.fixture is not None):
            raise ConfigTableError(
                f"{field_name} must declare exactly one flag source: 'judges' (a "
                "list of registered judge ids) or 'fixture' (a pinned flag "
                "document); a re-listen with neither re-listens to nothing, and a "
                "re-listen with both has two sources of truth"
            )
        seen: set[str] = set()
        for index, judge_id in enumerate(self.judges):
            _require_text(judge_id, field_name=f"{field_name}.judges[{index}]")
            if judge_id in seen:
                raise ConfigTableError(
                    f"{field_name}.judges repeats {judge_id!r}; one judge raises its "
                    "flags once"
                )
            seen.add(judge_id)
            try:
                JUDGES.resolve(judge_id)
            except CoreError as error:
                raise ConfigTableError(
                    f"{field_name}.judges[{index}]: {error}"
                ) from None
        if self.fixture is not None:
            self.fixture.validate(field_name=f"{field_name}.fixture")
        return self

    def as_json(self) -> dict[str, object]:
        document: dict[str, object] = {
            "context_margin_seconds": self.config.context_margin_seconds,
            "max_relistens_per_sample": self.config.max_relistens_per_sample,
            "derivation_kind": self.config.derivation_kind,
        }
        if self.judges:
            document["judges"] = list(self.judges)
        if self.fixture is not None:
            document["fixture"] = self.fixture.as_json()
        return document


@dataclass(frozen=True)
class ObserveModeSpec:
    """One phase's observe row. Every entry is independently nullable, and a
    row that selects no mode at all is refused: it would read as if the
    Observer did something and the cell would carry a key that changes
    nothing."""

    phase: str
    tail_silence_seconds: float | None = None
    unit_plan: PinnedFile | None = None
    relisten: ReListenSpec | None = None

    def validate(self) -> "ObserveModeSpec":
        where = f"observe[{self.phase!r}]"
        _require_text(self.phase, field_name="ObserveModeSpec.phase")
        if self.tail_silence_seconds is not None:
            value = self.tail_silence_seconds
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or value != value  # NaN
                or value in (float("inf"), float("-inf"))
            ):
                raise ConfigTableError(
                    f"{where}.tail_silence_seconds must be a finite number, got "
                    f"{value!r}"
                )
            if float(value) < 0:
                raise ConfigTableError(
                    f"{where}.tail_silence_seconds must be non-negative, got {value!r}"
                )
        if self.unit_plan is not None:
            self.unit_plan.validate(field_name=f"{where}.unit_plan")
        if self.relisten is not None:
            self.relisten.validate(field_name=f"{where}.relisten")
        if (
            self.tail_silence_seconds is None
            and self.unit_plan is None
            and self.relisten is None
        ):
            raise ConfigTableError(
                f"{where} selects no observe mode; an all-null row is the table's "
                "null arm written the long way -- drop the row (or the whole "
                "'observe' block) instead, so the OFF arm and today's graph carry "
                "one config hash"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        document: dict[str, object] = {"phase": self.phase}
        if self.tail_silence_seconds is not None:
            document["tail_silence_seconds"] = float(self.tail_silence_seconds)
        if self.unit_plan is not None:
            document["unit_plan"] = self.unit_plan.as_json()
        if self.relisten is not None:
            document["relisten"] = self.relisten.as_json()
        return document


def _load_pinned_file(entry: object, *, field_name: str) -> PinnedFile:
    document = _require_mapping(entry, field_name=field_name)
    _reject_unknown_keys(document, _PINNED_FILE_KEYS, field_name=field_name)
    missing = sorted(_PINNED_FILE_KEYS - set(document))
    if missing:
        raise ConfigTableError(
            f"{field_name} must carry {sorted(_PINNED_FILE_KEYS)}; missing {missing}"
        )
    return PinnedFile(
        relpath=document["relpath"], sha256=document["sha256"]
    ).validate(field_name=field_name)


def _load_relisten(entry: object, *, field_name: str) -> ReListenSpec:
    document = _require_mapping(entry, field_name=field_name)
    _reject_unknown_keys(document, _RELISTEN_KEYS, field_name=field_name)
    for required in ("context_margin_seconds", "max_relistens_per_sample"):
        if required not in document:
            raise ConfigTableError(f"{field_name} must declare {required!r}")
    judges = document.get("judges")
    if judges is not None and (
        isinstance(judges, (str, bytes)) or not isinstance(judges, (list, tuple))
    ):
        raise ConfigTableError(
            f"{field_name}.judges must be a list of registered judge ids, got "
            f"{judges!r}"
        )
    fixture = document.get("fixture")
    return ReListenSpec(
        config=ObserveConfig(
            context_margin_seconds=document["context_margin_seconds"],
            max_relistens_per_sample=document["max_relistens_per_sample"],
            derivation_kind=document.get("derivation_kind", "recut-span"),
        ),
        judges=tuple(judges or ()),
        fixture=(
            None
            if fixture is None
            else _load_pinned_file(fixture, field_name=f"{field_name}.fixture")
        ),
    ).validate(field_name=field_name)


def load_observe_table(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, ObserveModeSpec]:
    """Parse the fragment's ``observe`` table against ``program``.

    The null arm (absent, ``null`` or ``{}``) returns an empty mapping: no
    phase declares an observe mode and the loop's observation is today's
    fixed window, byte for byte. Present: refuses a non-object; a phase the
    program does not declare; an unknown key in a row; an all-null row; a
    negative or non-finite tail; an unpinned unit plan; a re-listen with no
    flag source, with both, or with an unregistered judge id; and a fragment
    that ALSO carries the Earnings obs-loop's flat observe knobs.

    Returned in the program's own phase order, so a receipt reads the way the
    program runs.
    """

    program.validate()
    declared = values.get(OBSERVE_TABLE)
    if _is_null_arm(declared):
        return {}
    legacy = sorted(key for key in LEGACY_OBSERVE_KEYS if values.get(key) is not None)
    if legacy:
        raise ConfigTableError(
            f"a fragment declares the 'observe' table and the flat obs-loop key(s) "
            f"{legacy}; those keys are the pre-table spelling of the same observe "
            "modes (reproduction.obs_loop) and declaring both is two switches for "
            "one module -- keep the flat keys on the obs-agent-loop policy path, or "
            "move them into 'observe', not both"
        )
    table = _require_mapping(declared, field_name="'observe'")
    known = set(program.phase_names())
    unknown = sorted(set(table) - known)
    if unknown:
        raise ConfigTableError(
            f"observe names phase(s) {unknown} that program {program.program_id!r} "
            f"does not declare; its phases are {sorted(known)}"
        )
    specs: dict[str, ObserveModeSpec] = {}
    for phase in program.phases:
        if phase.name not in table:
            continue
        where = f"observe[{phase.name!r}]"
        entry = _require_mapping(table[phase.name], field_name=where)
        _reject_unknown_keys(entry, _OBSERVE_ENTRY_KEYS, field_name=where)
        unit_plan = entry.get("unit_plan")
        relisten = entry.get("relisten")
        specs[phase.name] = ObserveModeSpec(
            phase=phase.name,
            tail_silence_seconds=entry.get("tail_silence_seconds"),
            unit_plan=(
                None
                if unit_plan is None
                else _load_pinned_file(unit_plan, field_name=f"{where}.unit_plan")
            ),
            relisten=(
                None
                if relisten is None
                else _load_relisten(relisten, field_name=f"{where}.relisten")
            ),
        ).validate()
    return specs


# ---------------------------------------------------------------------------
# Table 2: knowledge_views
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KnowledgeViewsTable:
    """The wrapped E1/E6 specs, produced by the SAME loaders the flat blocks
    use, from the SAME bytes."""

    material: Mapping[str, PhaseMaterialSpec] = field(default_factory=dict)
    supply: Mapping[str, PhaseSupplySpec] = field(default_factory=dict)

    def as_json(self) -> dict[str, object]:
        return {
            "material": sorted(self.material),
            "supply": sorted(self.supply),
        }


def unwrap_knowledge_views(values: Mapping[str, object]) -> dict[str, object]:
    """The flat ``{phase_material, phase_supply}`` mapping a
    ``knowledge_views`` table is equivalent to.

    Bytes in, bytes out: each phase's ``material`` / ``supply`` object is
    carried over UNCHANGED, which is what lets the existing loaders and the
    existing engineering-base-check rules read the table with no change of
    their own. A fragment that declares no table gets its flat blocks back
    verbatim, so this function is the one place the two spellings meet.
    """

    declared = values.get(KNOWLEDGE_VIEWS_TABLE)
    if _is_null_arm(declared):
        return {
            "phase_material": values.get("phase_material"),
            "phase_supply": values.get("phase_supply"),
        }
    _assert_not_double_declared(values, KNOWLEDGE_VIEWS_TABLE)
    table = _require_mapping(declared, field_name="'knowledge_views'")
    material: dict[str, object] = {}
    supply: dict[str, object] = {}
    for phase_name in sorted(table):
        where = f"knowledge_views[{phase_name!r}]"
        entry = _require_mapping(table[phase_name], field_name=where)
        _reject_unknown_keys(entry, _KNOWLEDGE_VIEW_ENTRY_KEYS, field_name=where)
        if entry.get("material") is not None:
            material[phase_name] = entry["material"]
        if entry.get("supply") is not None:
            supply[phase_name] = entry["supply"]
    return {
        "phase_material": material or None,
        "phase_supply": supply or None,
    }


def load_knowledge_views_table(
    values: Mapping[str, object], program: PhaseProgram
) -> KnowledgeViewsTable:
    """Parse the fragment's ``knowledge_views`` table (or its flat
    ``phase_material`` / ``phase_supply`` equivalent) against ``program``.

    Delegates verbatim to ``rails.phase_material.load_phase_material_specs``
    and ``rails.phase_supply.load_phase_supply_specs``: every refusal those
    two already make is this table's refusal too, with no second validator to
    drift from them. ``material`` is required for every phase of a phase
    program (their rule, not a new one); ``supply`` is per-phase optional and
    its absence IS the retrieval provider's OFF arm.
    """

    program.validate()
    flat = unwrap_knowledge_views(values)
    material = (
        load_phase_material_specs(flat, program)
        if flat.get("phase_material") is not None
        else {}
    )
    supply = load_phase_supply_specs(flat, program)
    return KnowledgeViewsTable(material=material, supply=supply)


# ---------------------------------------------------------------------------
# Table 3: judges
# ---------------------------------------------------------------------------


def unwrap_judges(values: Mapping[str, object]) -> dict[str, object]:
    """The flat ``{phase_review}`` mapping a ``judges`` table is equivalent
    to -- the entry objects carried over unchanged."""

    declared = values.get(JUDGES_TABLE)
    if _is_null_arm(declared):
        return {"phase_review": values.get("phase_review")}
    _assert_not_double_declared(values, JUDGES_TABLE)
    table = _require_mapping(declared, field_name="'judges'")
    for phase_name in sorted(table):
        entry = _require_mapping(
            table[phase_name], field_name=f"judges[{phase_name!r}]"
        )
        _reject_unknown_keys(
            entry, _JUDGES_ENTRY_KEYS, field_name=f"judges[{phase_name!r}]"
        )
    return {"phase_review": dict(table)}


def load_judges_table(
    values: Mapping[str, object], program: PhaseProgram
) -> Mapping[str, PhaseReviewSpec]:
    """Parse the fragment's ``judges`` table (or its flat ``phase_review``
    equivalent) against ``program``, through W1's own loader.

    The null arm returns an empty mapping: no phase is reviewed and the cell
    is byte-identical to the same cell with no Reviewer -- which is exactly
    what makes "Reviewer on versus off" a paired arm rather than a rebuild.
    """

    return load_phase_review_specs(unwrap_judges(values), program)


# ---------------------------------------------------------------------------
# Table 4: toolkits
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolkitSelection:
    """Which W3 task-type toolkit row is armed, and for which agent roles.

    Run-scoped rather than per-phase: W3's table is keyed by task type (a
    property of the carrier, not of a phase), and a role's toolkit is the set
    of tools that role may call for the whole episode.
    """

    task_type: str
    roles: tuple[str, ...]
    tools_by_role: Mapping[str, tuple[str, ...]]

    def as_json(self) -> dict[str, object]:
        return {
            "task_type": self.task_type,
            "roles": list(self.roles),
            "tools_by_role": {
                role: list(self.tools_by_role[role]) for role in sorted(self.tools_by_role)
            },
        }


def load_toolkits_table(
    values: Mapping[str, object], *, table: Any | None = None
) -> ToolkitSelection | None:
    """Parse the fragment's ``toolkits`` table against W3's committed table.

    The null arm returns ``None``: no tool is armed and the loop is today's
    loop, which is also W3's own state (no tool is wired into a running loop
    yet). Present: refuses a non-object; an unknown key; a missing or unknown
    ``task_type``; an empty, repeating or unknown ``roles`` entry; and a role
    the selected task type does not declare. ``table`` is the seam a test or
    a caller holding its own table uses; the default is the committed
    ``configs/toolkit/task-toolkits-v1.json``.
    """

    declared = values.get(TOOLKITS_TABLE)
    if _is_null_arm(declared):
        return None
    entry = _require_mapping(declared, field_name="'toolkits'")
    _reject_unknown_keys(entry, _TOOLKITS_ENTRY_KEYS, field_name="'toolkits'")
    task_type = _require_text(entry.get("task_type"), field_name="toolkits.task_type")
    from .tools import TOOLKIT_ROLES, ToolCatalogError, default_toolkit_table

    resolved = default_toolkit_table() if table is None else table
    try:
        toolkit = resolved.for_task(task_type)
    except ToolCatalogError as error:
        raise ConfigTableError(f"toolkits.task_type: {error}") from None
    declared_roles = entry.get("roles")
    if declared_roles is None:
        roles = tuple(role for role in TOOLKIT_ROLES if role in toolkit.tools_by_role)
    else:
        if isinstance(declared_roles, (str, bytes)) or not isinstance(
            declared_roles, (list, tuple)
        ):
            raise ConfigTableError(
                f"toolkits.roles must be a list of agent roles, got {declared_roles!r}"
            )
        if not declared_roles:
            raise ConfigTableError(
                "toolkits.roles is empty; a selection that arms no role arms nothing "
                "-- write \"toolkits\": null, which is the table's null arm and "
                "carries the same config hash as no table at all"
            )
        seen: set[str] = set()
        for index, role in enumerate(declared_roles):
            _require_text(role, field_name=f"toolkits.roles[{index}]")
            if role in seen:
                raise ConfigTableError(f"toolkits.roles repeats {role!r}")
            seen.add(role)
            if role not in TOOLKIT_ROLES:
                raise ConfigTableError(
                    f"toolkits.roles[{index}] is {role!r}; the roles that may call a "
                    f"tool are {list(TOOLKIT_ROLES)} (the Solver is the frozen core "
                    "and calls none)"
                )
            if role not in toolkit.tools_by_role:
                raise ConfigTableError(
                    f"toolkits.roles[{index}] is {role!r} but task type "
                    f"{task_type!r} declares no such role"
                )
        roles = tuple(role for role in TOOLKIT_ROLES if role in seen)
    return ToolkitSelection(
        task_type=task_type,
        roles=roles,
        tools_by_role={role: toolkit.tools_for(role) for role in roles},
    )


# ---------------------------------------------------------------------------
# The bundle, and the flattened-config diff the admission gate reads
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigTables:
    """All four tables of one composed config, validated together."""

    observe: Mapping[str, ObserveModeSpec] = field(default_factory=dict)
    knowledge_views: KnowledgeViewsTable = field(default_factory=KnowledgeViewsTable)
    judges: Mapping[str, PhaseReviewSpec] = field(default_factory=dict)
    toolkits: ToolkitSelection | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "schema": CONFIG_TABLES_SCHEMA,
            "judges": {
                phase: self.judges[phase].as_json() for phase in sorted(self.judges)
            },
            "knowledge_views": self.knowledge_views.as_json(),
            "observe": {
                phase: self.observe[phase].as_json() for phase in sorted(self.observe)
            },
            "toolkits": (
                None if self.toolkits is None else self.toolkits.as_json()
            ),
        }

    def content_hash(self) -> str:
        return content_hash(self.as_json())


def load_config_tables(
    values: Mapping[str, object], program: PhaseProgram, *, toolkit_table: Any | None = None
) -> ConfigTables:
    """Load all four tables of one composed config, fail-closed."""

    return ConfigTables(
        observe=load_observe_table(values, program),
        knowledge_views=load_knowledge_views_table(values, program),
        judges=load_judges_table(values, program),
        toolkits=load_toolkits_table(values, table=toolkit_table),
    )


def flatten_config(values: Mapping[str, object], *, prefix: str = "") -> dict[str, object]:
    """A composed config as ``{dotted.path: leaf}``.

    Nested objects are walked; every other value (including a list) is a
    leaf, so a changed list shows up as ONE changed key rather than as a
    diff of its elements. This is the view the module-admission proof reads:
    ON and OFF of one module must differ in exactly one of these keys.
    """

    flat: dict[str, object] = {}
    for key in values:
        path = f"{prefix}{key}"
        value = values[key]
        if isinstance(value, Mapping):
            if not value:
                flat[path] = {}
                continue
            flat.update(flatten_config(value, prefix=f"{path}."))
        else:
            flat[path] = value
    return flat


def config_key_diff(
    on: Mapping[str, object], off: Mapping[str, object]
) -> tuple[str, ...]:
    """The sorted dotted paths on which two composed configs differ.

    A module is expressible as one config key exactly when this returns a
    one-element tuple for its ON and OFF arms -- the machine form of the
    design note's "one config key, never a second code path".
    """

    flat_on = flatten_config(on)
    flat_off = flatten_config(off)
    return tuple(
        sorted(
            key
            for key in set(flat_on) | set(flat_off)
            if key not in flat_on or key not in flat_off or flat_on[key] != flat_off[key]
        )
    )


def switch_key(on: Mapping[str, object], off: Mapping[str, object]) -> str:
    """The ONE config key that distinguishes two arms, or a refusal.

    A key here is a dotted path, and an object-valued key changes several
    leaves at once (``observe.<phase>.unit_plan`` moves both its ``relpath``
    and its ``sha256``). So the machine form of "one config key" is: every
    leaf on which the two composed configs differ lies under ONE common
    dotted path, and that path resolves in at least one of the two arms.

    That is exactly the property the design note's admission gate needs and
    exactly what today's flat spellings lack: ``obs_unit_plan`` and
    ``obs_unit_plan_sha256`` share no dotted prefix, and neither do a
    ``policy`` swap and the post-processor pair that rides with it, so both
    are refused here by construction rather than by opinion.

    Raises :class:`ConfigTableError` when the arms are identical, or when
    their difference is more than one key.
    """

    diff = config_key_diff(on, off)
    if not diff:
        raise ConfigTableError(
            "the two arms compose to the same config; an ON/OFF pair that moves "
            "no key is not a contrast"
        )
    segments = [key.split(".") for key in diff]
    shared: list[str] = []
    for index in range(min(len(parts) for parts in segments)):
        candidate = segments[0][index]
        if any(parts[index] != candidate for parts in segments):
            break
        shared.append(candidate)
    if not shared:
        raise ConfigTableError(
            f"the two arms differ in {len(diff)} unrelated config keys {list(diff)}; "
            "a module whose OFF arm moves more than one key is not one switch, and "
            "its ON/OFF pair is not a twin"
        )
    path = ".".join(shared)
    if not any(_resolves(values, shared) for values in (on, off)):
        raise ConfigTableError(
            f"the shared path {path!r} of the changed keys {list(diff)} resolves in "
            "neither arm"
        )
    return path


def _resolves(values: Mapping[str, object], path: Sequence[str]) -> bool:
    cursor: object = values
    for segment in path:
        if not isinstance(cursor, Mapping) or segment not in cursor:
            return False
        cursor = cursor[segment]
    return True


def resolve_switch_key(table: str, key: str) -> str:
    """The table entry key a ``switch.key`` declaration names, or a refusal.

    ``docs/receipts/harness-admission.json`` records, per admitted module,
    the ONE config key that switches it -- as a dotted path whose phase
    segment may be the placeholder ``<phase>`` because a module's admission
    is about the module, not about one program's phase names. The path must
    start with its table and must name one of that table's entry keys
    somewhere after it, which is what makes "the key resolves in a table" a
    machine question:

    * ``observe.<phase>.tail_silence_seconds`` -> ``tail_silence_seconds``
    * ``knowledge_views.<phase>.material.state_fill`` -> ``material``
    * ``judges.<phase>.judges`` -> ``judges``
    * ``toolkits.task_type`` -> ``task_type``
    """

    if table not in CONFIG_TABLE_NAMES:
        raise ConfigTableError(
            f"unknown config table {table!r}; the tables are {list(CONFIG_TABLE_NAMES)}"
        )
    segments = key.split(".") if isinstance(key, str) else []
    if not segments or segments[0] != table:
        raise ConfigTableError(
            f"switch key {key!r} does not start with its table {table!r}; a switch "
            "that names no table is not one config key"
        )
    entry_keys = table_entry_keys(table)
    named = [segment for segment in segments[1:] if segment in entry_keys]
    if not named:
        raise ConfigTableError(
            f"switch key {key!r} names no entry of the {table!r} table; its entry "
            f"keys are {list(entry_keys)}"
        )
    return named[0]


def table_entry_keys(table: str) -> tuple[str, ...]:
    """The entry keys ``table`` admits, sorted -- what a switch declaration
    in ``docs/receipts/harness-admission.json`` must name."""

    if table == OBSERVE_TABLE:
        return tuple(sorted(_OBSERVE_ENTRY_KEYS))
    if table == KNOWLEDGE_VIEWS_TABLE:
        return tuple(sorted(_KNOWLEDGE_VIEW_ENTRY_KEYS))
    if table == JUDGES_TABLE:
        return tuple(sorted(_JUDGES_ENTRY_KEYS))
    if table == TOOLKITS_TABLE:
        return tuple(sorted(_TOOLKITS_ENTRY_KEYS))
    raise ConfigTableError(
        f"unknown config table {table!r}; the tables are {list(CONFIG_TABLE_NAMES)}"
    )


__all__ = [
    "CONFIG_TABLES_SCHEMA",
    "CONFIG_TABLE_NAMES",
    "JUDGES_TABLE",
    "KNOWLEDGE_VIEWS_TABLE",
    "LEGACY_OBSERVE_KEYS",
    "NULL_ARMS",
    "OBSERVE_TABLE",
    "TOOLKITS_TABLE",
    "WRAPPED_FLAT_KEYS",
    "ConfigTableError",
    "ConfigTables",
    "KnowledgeViewsTable",
    "ObserveModeSpec",
    "PinnedFile",
    "ReListenSpec",
    "ToolkitSelection",
    "config_key_diff",
    "flatten_config",
    "switch_key",
    "load_config_tables",
    "load_judges_table",
    "load_knowledge_views_table",
    "load_observe_table",
    "load_toolkits_table",
    "resolve_switch_key",
    "table_entry_keys",
    "unwrap_judges",
    "unwrap_knowledge_views",
]
