"""The tool catalog: one manifest per pinned, SYSTEM-INVOKED tool (WAVE W3).

What a tool is here, and what it is not
---------------------------------------
A tool is anything an agent calls that is NOT the frozen core (design note
``docs/readiness/2026-09-08-agent-system-episode-and-core-pressure-v1.md``
section 7). The core stays behind the single door (``rails.core_client`` /
``core.model.FrozenCoreAdapter``) and is never registered here. Scorers are
evaluation instruments and never run inside the loop, so they are not tools
either. Knowledge stores (class lists, schemas, KB facets, exemplar indexes)
are not tools; tools read and build them.

SYSTEM-invoked, not model-invoked -- the 2026-08-08 ruling stands
---------------------------------------------------------------
On 2026-08-08 the owner REVERSED the adoption memo's "DSP functions
registered as framework local tools" line, on the ground that a framework
tool base is reserved for a MODEL-INVOKED re-ask arm and that "wrapping
pipeline DSP as tools would change semantics to model-decided invocation"
(``docs/readiness/2026-08-08-ojw-rebuild-notes.md`` line 57, restated in
``reproduction/ojw/components.py``). Historical entries retain that behavior. OWNER-MULTIMODAL-SYSTEM-FIRST-016
adds the explicit rails.phase_tools action bridge: the frozen core may select a
bounded task action there, and the harness invokes its native primitive here.
Selection mode is recorded separately; no existing toolkit opts in implicitly.

Every entry in this catalog is a **system-invoked** tool: the harness -- the
Planner reading a manifest, or a phase of ``rails.controllers.
EvidenceAgentController`` -- decides that it runs. Native manifests are never rendered as model-callable Python APIs. The
explicit task-action bridge exposes its own JSON-safe action contracts and
records model-selected dispatch; ordinary catalog use stays system-selected. That is enforced in code, not in
prose: :data:`ToolManifest.system_invoked` must be ``True`` or
:func:`register_tool` REFUSES the registration, and the flag is carried
verbatim into the framework ``ToolCard``'s ``properties`` so a reader of the
card sees the same claim.

The manifest fields are exactly the design note's
--------------------------------------------------
Section 7: "id and pinned hash; typed inputs and outputs; side effects
(bytes changed -> derivation record required); cost class (CPU, GPU,
contacts); the axis it serves (OBS / ORG / SUPPLY / USE); scope (general or
carrier); the ledger row type it needs." :class:`ToolManifest` carries those
seven and nothing invented beside them except ``description`` (the framework
``ToolCard`` requires one) and ``source_ref`` (the dotted target the pinned
hash is taken OVER, without which the hash is unverifiable).

How it reaches openJiuwen
-------------------------
``ToolCard`` (``openjiuwen.core.foundation.tool.base``) already carries id,
name, description, ``input_params``, ``parallel_safe``, ``stateless`` and
``idempotent``; everything else in the manifest rides in its free-form
``properties`` dict. :func:`to_tool_card` builds that card and
:func:`to_local_function` binds the wrapper body into a framework
``LocalFunction``, both behind a LAZY import so this module -- and the whole
``rails`` package -- still imports with ``openjiuwen`` absent (D2
zero-dependency gate, ``docs/readiness/2026-08-08-openjiuwen-adoption.md``:
``openjiuwen`` never enters ``pyproject.toml``). The framework's LLM
clients, ``MCPTool`` and ``RestfulApi`` are never imported and never
instantiated (paid API = 0).

The framework's own ``LocalFunction.invoke`` coerces its inputs through
``SchemaUtils.format_with_schema`` (a jsonschema validation plus a pydantic
round trip), which would destroy the ``bytes`` and ``array`` payloads half
of these tools carry. That path is therefore NOT this study's call path: a
system caller invokes :meth:`ToolEntry.call`, which reaches the wrapped
function directly and is what every byte-equivalence test pins. The
``LocalFunction`` exists so the catalog can be registered in the framework's
``ToolMgr`` and appear in its tracing, exactly as the design note asks.

Where the registry object lives
-------------------------------
:data:`TOOL_CATALOG` is a ``core.base.Registry`` like every other component
seam, constructed HERE rather than in ``core/base.py`` -- the same admitted
stopgap ``rails.knowledge_provider.KNOWLEDGE_PROVIDERS`` used before E6
moved it. ``scripts/checks/engineering_base_check.py`` reads this file as a
canonical registration site, so a ``tools`` list in ``configs/`` is checked
against the ids registered here regardless of which module holds the
registry object; a later change owned by ``core/base.py`` may move the
object without moving a single ``TOOL_CATALOG.register`` call.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..core.base import Registry
from ..e0.artifacts import REPO_ROOT
from .errors import RailsError
from .tool_wrappers import phase_knowledge as _phase_knowledge
from .tool_wrappers import candidate_contract_lookup as _candidate_contract_lookup
from .tool_wrappers import speech_observation as _speech_observation
from .tool_wrappers import live_speech_observation as _live_speech_observation
from .tool_wrappers import live_speech_span as _live_speech_span


class ToolCatalogError(RailsError):
    """A tool manifest, registration, toolkit or catalog lookup is malformed."""


#: The four control axes the study separates (study ``CLAUDE.md``: OBS /
#: ORG / SUPPLY / USE). Every tool serves exactly one.
TOOL_AXES = ("OBS", "ORG", "SUPPLY", "USE")

#: Cost classes, exactly the design note's three. ``cpu`` is deterministic
#: local compute; ``gpu`` needs the accelerator; ``contact`` reaches a
#: service or a pinned model and therefore always needs a ledger row.
COST_CLASSES = ("cpu", "gpu", "contact")

#: The ledger row a USE of this tool's output requires.
#:
#: * ``none`` -- pure local computation over material already in the run;
#: * ``tool-contact`` -- the value is (or is read from) the product of a
#:   PINNED frozen tool run, whose own exposure row must be cited;
#: * ``service-contact`` -- a non-generative route on the resident serving
#:   process (``GET /props``, ``POST /tokenize``, ``POST /apply-template``);
#:   no token is generated and no answer is read, but the contact happened.
#:
#: There is deliberately no ``model-contact`` value: the frozen core is never
#: a tool (module docstring), so no manifest may claim one.
LEDGER_ROW_TYPES = ("none", "tool-contact", "service-contact")

#: ``scope`` is the design note's "general or carrier". A carrier scope is
#: spelled ``carrier:<id>`` over the owner-locked carrier set (study
#: ``CLAUDE.md``, "Carriers": Earnings21+ConEC, SLURP, Audio2Tool).
GENERAL_SCOPE = "general"
CARRIER_SCOPE_PREFIX = "carrier:"
LOCKED_CARRIERS = ("audio2tool", "conec", "earnings21", "earnings22", "slurp")

#: Every catalog id carries this prefix, so a ``tools`` list in ``configs/``
#: is recognisably a list of CATALOG ids and not, say, an Audio2Tool
#: function-name payload.
TOOL_ID_PREFIX = "saea-tool-"

#: Carried verbatim into every ``ToolCard.properties``: the 2026-08-08
#: ruling, restated on the card a reader actually holds.
INVOCATION = "system"


def _require_text(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ToolCatalogError(f"tool manifest {field} must be non-empty text, got {value!r}")
    return value


def _require_typed_io(value: object, *, field: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or not value:
        raise ToolCatalogError(f"tool manifest {field} must be a non-empty mapping")
    typed: dict[str, str] = {}
    for name, spelling in value.items():
        _require_text(name, field=f"{field} key")
        _require_text(spelling, field=f"{field}[{name!r}]")
        typed[str(name)] = str(spelling)
    return typed


@dataclass(frozen=True)
class ToolManifest:
    """One tool's manifest -- exactly the design note's section-7 fields.

    ``inputs``/``outputs`` map a name to its PYTHON type spelling, not to a
    JSON-schema type: these tools are system-invoked over native objects
    (``bytes``, ``array``, dataclasses), never over model-emitted JSON, and
    writing a JSON type here would claim a decoding contract that does not
    exist. :func:`to_tool_card` renders them into ``input_params`` under a
    ``python_type`` key for the same reason.

    ``changes_bytes`` is the side-effect field: a tool that changes the bytes
    that go on the wire (tail, resample, slice, re-cut) MUST name the
    derivation record it emits in ``derivation_record``, and a tool that does
    not change bytes must leave it ``None``. :func:`validate` enforces both
    directions, so "bytes changed -> derivation record required" is a
    machine fact rather than a convention.

    ``system_invoked`` must be ``True``. :func:`register_tool` refuses a
    manifest without it (module docstring, 2026-08-08 ruling).
    """

    tool_id: str
    description: str
    source_ref: str
    pinned_sha256: str
    inputs: Mapping[str, str]
    outputs: Mapping[str, str]
    changes_bytes: bool
    derivation_record: str | None
    cost_class: str
    axis: str
    scope: str
    ledger_row_type: str
    system_invoked: bool = True
    parallel_safe: bool = True
    stateless: bool = True
    idempotent: bool = True

    def validate(self) -> ToolManifest:
        """Refuse an incomplete or self-contradictory manifest; return a
        normalized copy (typed I/O frozen into plain ``dict``s)."""

        tool_id = _require_text(self.tool_id, field="tool_id")
        if not tool_id.startswith(TOOL_ID_PREFIX):
            raise ToolCatalogError(
                f"tool id {tool_id!r} must start with {TOOL_ID_PREFIX!r}"
            )
        _require_text(self.description, field="description")
        source_ref = _require_text(self.source_ref, field="source_ref")
        if source_ref.count(":") != 1 or source_ref.startswith(":") or source_ref.endswith(":"):
            raise ToolCatalogError(
                f"tool {tool_id!r}: source_ref must be '<module>:<qualname>', got {source_ref!r}"
            )
        pinned = _require_text(self.pinned_sha256, field="pinned_sha256").lower()
        if len(pinned) != 64 or any(c not in "0123456789abcdef" for c in pinned):
            raise ToolCatalogError(
                f"tool {tool_id!r}: pinned_sha256 must be 64 lowercase hex characters"
            )
        inputs = _require_typed_io(self.inputs, field="inputs")
        outputs = _require_typed_io(self.outputs, field="outputs")
        if not isinstance(self.changes_bytes, bool):
            raise ToolCatalogError(f"tool {tool_id!r}: changes_bytes must be a bool")
        if self.changes_bytes:
            _require_text(self.derivation_record, field="derivation_record")
        elif self.derivation_record is not None:
            raise ToolCatalogError(
                f"tool {tool_id!r} names a derivation record but does not change bytes"
            )
        if self.cost_class not in COST_CLASSES:
            raise ToolCatalogError(
                f"tool {tool_id!r}: cost_class must be one of {COST_CLASSES}, "
                f"got {self.cost_class!r}"
            )
        if self.axis not in TOOL_AXES:
            raise ToolCatalogError(
                f"tool {tool_id!r}: axis must be one of {TOOL_AXES}, got {self.axis!r}"
            )
        scope = _require_text(self.scope, field="scope")
        if scope != GENERAL_SCOPE:
            if not scope.startswith(CARRIER_SCOPE_PREFIX):
                raise ToolCatalogError(
                    f"tool {tool_id!r}: scope must be {GENERAL_SCOPE!r} or "
                    f"'{CARRIER_SCOPE_PREFIX}<carrier>', got {scope!r}"
                )
            carrier = scope[len(CARRIER_SCOPE_PREFIX):]
            if carrier not in LOCKED_CARRIERS:
                raise ToolCatalogError(
                    f"tool {tool_id!r}: carrier {carrier!r} is not one of the locked "
                    f"carriers {LOCKED_CARRIERS}"
                )
        if self.ledger_row_type not in LEDGER_ROW_TYPES:
            raise ToolCatalogError(
                f"tool {tool_id!r}: ledger_row_type must be one of {LEDGER_ROW_TYPES}, "
                f"got {self.ledger_row_type!r}"
            )
        if self.cost_class == "contact" and self.ledger_row_type == "none":
            raise ToolCatalogError(
                f"tool {tool_id!r} costs a contact but needs no ledger row; a contact "
                "is always recorded before its result is read"
            )
        for name, value in (
            ("system_invoked", self.system_invoked),
            ("parallel_safe", self.parallel_safe),
            ("stateless", self.stateless),
            ("idempotent", self.idempotent),
        ):
            if not isinstance(value, bool):
                raise ToolCatalogError(f"tool {tool_id!r}: {name} must be a bool")
        return replace(self, pinned_sha256=pinned, inputs=inputs, outputs=outputs)

    def as_dict(self) -> dict[str, Any]:
        """The manifest as a plain JSON-safe mapping -- what rides in the
        framework ``ToolCard``'s ``properties``."""

        return {
            "tool_id": self.tool_id,
            "description": self.description,
            "source_ref": self.source_ref,
            "pinned_sha256": self.pinned_sha256,
            "inputs": dict(self.inputs),
            "outputs": dict(self.outputs),
            "changes_bytes": self.changes_bytes,
            "derivation_record": self.derivation_record,
            "cost_class": self.cost_class,
            "axis": self.axis,
            "scope": self.scope,
            "ledger_row_type": self.ledger_row_type,
            "system_invoked": self.system_invoked,
            "invocation": INVOCATION,
            "parallel_safe": self.parallel_safe,
            "stateless": self.stateless,
            "idempotent": self.idempotent,
        }


@dataclass(frozen=True)
class DerivationRecord:
    """What a byte-changing tool leaves behind: the transform chain it
    applied, the hash of the bytes BEFORE it (``None`` when nothing changed)
    and the hash of the bytes it returned.

    Same three values ``core.model.SliceRecord`` already needs, named the
    same way, so a derivation record produced here drops into the payload
    -binding rail without translation.
    """

    tool_id: str
    transforms: tuple[str, ...]
    pre_sha256: str | None
    post_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "transforms": list(self.transforms),
            "pre_sha256": self.pre_sha256,
            "post_sha256": self.post_sha256,
        }


@dataclass(frozen=True)
class ToolResult:
    """Every wrapper returns this: the wrapped function's result BYTE FOR
    BYTE in ``result``, plus a :class:`DerivationRecord` when the tool
    changed bytes and ``None`` when it did not.

    The uniform shape is what makes "wrapped output == direct call output"
    a one-line assertion in every equivalence test: ``wrapped(...).result``
    is the direct call's return value and nothing has been re-encoded,
    rounded or re-ordered on the way out.
    """

    tool_id: str
    result: Any
    derivation: DerivationRecord | None = None


@dataclass(frozen=True)
class ToolEntry:
    """A catalog row: the manifest plus the wrapped callable."""

    manifest: ToolManifest
    body: Callable[..., ToolResult]

    def call(self, *args: Any, **kwargs: Any) -> ToolResult:
        """THE system call path (module docstring): straight to the wrapper
        body, no schema coercion, no framework round trip."""

        return self.body(*args, **kwargs)


#: The catalog. ``id -> ToolEntry`` (manifest + wrapped callable), through
#: the one ``core.base.Registry`` mechanism every other component seam uses.
TOOL_CATALOG = Registry("tool")


def build_tool_entry(manifest: ToolManifest, body: Callable[..., ToolResult]) -> ToolEntry:
    """The ONE constructor of a catalog entry: validate the manifest and
    ENFORCE the system-invoked marker.

    A manifest whose ``system_invoked`` is not ``True`` is REFUSED here --
    the 2026-08-08 ruling enforced in code rather than in a comment (module
    docstring). Every ``TOOL_CATALOG.register`` call in the registration
    block below passes its entry through this function, and
    ``scripts/checks/tool_catalog_check.py`` fails if one ever does not, so
    the marker cannot be skipped by registering a hand-built
    :class:`ToolEntry` directly.
    """

    if not isinstance(manifest, ToolManifest):
        raise ToolCatalogError("build_tool_entry needs a ToolManifest")
    if manifest.system_invoked is not True:
        raise ToolCatalogError(
            f"tool {manifest.tool_id!r} is not marked system_invoked; this catalog "
            "holds SYSTEM-invoked tools only (owner ruling 2026-08-08: a framework "
            "tool base is reserved for a model-invoked arm, and registering a "
            "pipeline function without this marker would change its semantics to "
            "model-decided invocation)"
        )
    if not callable(body):
        raise ToolCatalogError(f"tool {manifest.tool_id!r}: body must be callable")
    return ToolEntry(manifest=manifest.validate(), body=body)


def assert_catalog_consistent() -> None:
    """Every registered id equals its entry's own ``manifest.tool_id``.

    The registration block below names each id as a STRING LITERAL, because
    ``scripts/checks/engineering_base_check.py`` reads the registered set out
    of this file's source without importing the package. A literal that
    disagreed with its manifest would make the config check pass on an id the
    catalog does not really carry, so the agreement is asserted at import.
    """

    for tool_id in TOOL_CATALOG.names():
        entry = TOOL_CATALOG.resolve(tool_id)
        if not isinstance(entry, ToolEntry):
            raise ToolCatalogError(f"catalog entry {tool_id!r} is not a ToolEntry")
        if entry.manifest.tool_id != tool_id:
            raise ToolCatalogError(
                f"catalog id {tool_id!r} carries a manifest naming "
                f"{entry.manifest.tool_id!r}"
            )


def catalog_ids() -> list[str]:
    """Every registered tool id, sorted."""

    return TOOL_CATALOG.names()


def resolve_tool(tool_id: str) -> ToolEntry:
    """The :class:`ToolEntry` for ``tool_id``; refuses an unknown id."""

    entry = TOOL_CATALOG.resolve(tool_id)
    if not isinstance(entry, ToolEntry):
        raise ToolCatalogError(f"catalog entry {tool_id!r} is not a ToolEntry")
    return entry


# ---------------------------------------------------------------------------
# The pinned hash: sha256 over the wrapped function's own source text.
# ---------------------------------------------------------------------------


def load_source_target(source_ref: str) -> Any:
    """Import and return the object ``'<module>:<qualname>'`` names.

    ``qualname`` may be dotted (``Class.method``), which is how the prompt
    -fit tokenizer's ``_LoopbackPromptAuditClient.request_json`` is reached.
    """

    _require_text(source_ref, field="source_ref")
    module_name, _, qualname = source_ref.partition(":")
    try:
        target: Any = importlib.import_module(module_name)
    except ImportError as error:
        raise ToolCatalogError(f"cannot import {module_name!r} for {source_ref!r}: {error}") from error
    for part in qualname.split("."):
        try:
            target = getattr(target, part)
        except AttributeError as error:
            raise ToolCatalogError(f"{source_ref!r} does not resolve: {error}") from error
    return target


def source_sha256(source_ref: str) -> str:
    """sha256 over ``inspect.getsource`` of the object ``source_ref`` names.

    ``inspect.getsource`` reads through ``linecache`` in text mode, so the
    digest is the same on a CRLF checkout and an LF one -- which matters
    because ``.gitattributes`` enforces LF but a Windows working tree does
    not always agree.
    """

    target = load_source_target(source_ref)
    try:
        source = inspect.getsource(target)
    except (OSError, TypeError) as error:
        raise ToolCatalogError(f"cannot read source of {source_ref!r}: {error}") from error
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def assert_pinned_hash(manifest: ToolManifest) -> None:
    """Refuse when the wrapped function's source no longer hashes to the
    manifest's pin -- the whole point of pinning it."""

    measured = source_sha256(manifest.source_ref)
    if measured != manifest.pinned_sha256:
        raise ToolCatalogError(
            f"tool {manifest.tool_id!r}: {manifest.source_ref} now hashes to "
            f"{measured}, not the pinned {manifest.pinned_sha256}; the wrapped body "
            "changed and the manifest was not re-pinned"
        )


# ---------------------------------------------------------------------------
# openJiuwen surface (lazy: this module imports with openjiuwen absent).
# ---------------------------------------------------------------------------


def tool_input_params(manifest: ToolManifest) -> dict[str, Any]:
    """``ToolCard.input_params`` for a manifest: an object schema whose
    properties carry the PYTHON type spelling.

    Not a decoding contract (:class:`ToolManifest`): these tools are
    system-invoked over native objects, and ``x-invocation`` says so inside
    the schema itself so a framework reader cannot mistake it for a
    model-facing function signature.
    """

    return {
        "type": "object",
        "properties": {
            name: {"python_type": spelling} for name, spelling in manifest.inputs.items()
        },
        "required": list(manifest.inputs),
        "additionalProperties": False,
        "x-invocation": INVOCATION,
    }


def to_tool_card(tool_id: str) -> Any:
    """The framework ``ToolCard`` for ``tool_id``, manifest in ``properties``.

    Lazy import: ``openjiuwen`` is never in ``pyproject.toml`` and this
    module must import without it (D2 zero-dependency gate).
    """

    entry = resolve_tool(tool_id)
    manifest = entry.manifest
    try:
        from openjiuwen.core.foundation.tool import ToolCard
    except ImportError as error:  # pragma: no cover - exercised by the absent-framework path
        raise ToolCatalogError(
            "to_tool_card needs the pinned openjiuwen runtime, which is not importable "
            "here; install it into the WSL research venv (it never enters "
            "pyproject.toml -- D2 zero-dependency gate)"
        ) from error
    return ToolCard(
        id=manifest.tool_id,
        name=manifest.tool_id,
        description=manifest.description,
        input_params=tool_input_params(manifest),
        properties=manifest.as_dict(),
        parallel_safe=manifest.parallel_safe,
        stateless=manifest.stateless,
        idempotent=manifest.idempotent,
    )


def to_local_function(tool_id: str) -> Any:
    """The framework ``LocalFunction`` binding the wrapper body to its card.

    Registration surface only. The framework's ``LocalFunction.invoke``
    coerces inputs through ``SchemaUtils.format_with_schema``, which would
    destroy the ``bytes``/``array`` payloads these tools carry, so a system
    caller uses :meth:`ToolEntry.call` instead (module docstring).
    """

    entry = resolve_tool(tool_id)
    card = to_tool_card(tool_id)
    from openjiuwen.core.foundation.tool import LocalFunction

    return LocalFunction(card=card, func=entry.body)


# ---------------------------------------------------------------------------
# Toolkits per task type (design note section 7: "Observe modes become
# toolkits selected per task type, which is the framework's own pattern").
#
# The framework's ``core/controller/modules/intent_toolkits.IntentToolkits``
# keeps a ``name -> schema`` mapping and exposes
# ``get_openai_tool_schemas(choices)`` to hand a SUBSET to a caller. This is
# that pattern, with two differences that matter here:
#
# 1. the subset is chosen by TASK TYPE and AGENT ROLE from a config table,
#    never by a model, and the table is data in ``configs/`` so a change to a
#    carrier's toolkit rides in the composed config hash;
# 2. it is fail-closed. The framework's own implementation of that method
#    ignores its ``choices`` argument and returns everything
#    (``intent_toolkits.py``, last three lines of the installed 0.1.16.post2),
#    which is precisely the failure mode a toolkit exists to prevent. An
#    unknown task type, an unknown role, an unknown tool id, or a
#    carrier-scoped tool offered to the wrong carrier's task type all REFUSE.
#
# No framework client is instantiated to build a toolkit; ``cards_for`` only
# reaches openJiuwen when a caller asks for actual ``ToolCard`` objects.
# ---------------------------------------------------------------------------

#: The three agents that may call a catalog tool. The Solver is absent by
#: construction: the Solver IS the frozen core behind the single door, and the
#: core never calls a tool (module docstring).
TOOLKIT_ROLES = ("planner", "observer", "reviewer")

#: The three task types the design note names.
TASK_TYPES = ("meeting", "command", "tool-call")

#: Which carriers each task type covers. A ``carrier:<id>``-scoped tool may
#: only appear in a task type whose carriers include it -- the SLURP legality
#: judge cannot end up in the meeting toolkit by a copy-paste.
TASK_TYPE_CARRIERS = {
    "meeting": ("conec", "earnings21", "earnings22"),
    "command": ("slurp",),
    "tool-call": ("audio2tool",),
}

TOOLKIT_SCHEMA = "saea-task-toolkits-v1"

#: The committed table, relative to the repository root.
TOOLKIT_CONFIG_RELPATH = "configs/toolkit/task-toolkits-v1.json"


@dataclass(frozen=True)
class Toolkit:
    """One task type's toolkit: which tool ids each agent role may call."""

    task_type: str
    tools_by_role: Mapping[str, tuple[str, ...]]

    def tools_for(self, role: str) -> tuple[str, ...]:
        """The tool ids ``role`` may call; refuses an unknown role."""

        if role not in TOOLKIT_ROLES:
            raise ToolCatalogError(
                f"unknown agent role {role!r}; the roles that may call a tool are "
                f"{TOOLKIT_ROLES} (the Solver is the frozen core and calls none)"
            )
        return self.tools_by_role[role]

    def entries_for(self, role: str) -> tuple[ToolEntry, ...]:
        """The catalog entries ``role`` may call, in table order."""

        return tuple(resolve_tool(tool_id) for tool_id in self.tools_for(role))

    def may_call(self, role: str, tool_id: str) -> bool:
        return tool_id in self.tools_for(role)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "tools_by_role": {role: list(ids) for role, ids in self.tools_by_role.items()},
        }


@dataclass(frozen=True)
class ToolkitTable:
    """The whole table: task type -> :class:`Toolkit`."""

    schema: str
    toolkits: Mapping[str, Toolkit]

    def for_task(self, task_type: str) -> Toolkit:
        """The toolkit for ``task_type``; refuses an unknown one."""

        try:
            return self.toolkits[task_type]
        except KeyError:
            raise ToolCatalogError(
                f"unknown task type {task_type!r}; the table declares "
                f"{sorted(self.toolkits)}"
            ) from None

    def cards_for(self, task_type: str, role: str) -> list[Any]:
        """The framework ``ToolCard`` objects ``role`` may call for
        ``task_type`` -- the ``get_openai_tool_schemas(choices)`` analogue,
        with the subset actually applied."""

        return [
            to_tool_card(tool_id) for tool_id in self.for_task(task_type).tools_for(role)
        ]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "toolkits": {
                task_type: toolkit.as_dict()
                for task_type, toolkit in sorted(self.toolkits.items())
            },
        }


def _toolkit_role_ids(
    values: object, *, task_type: str, role: str, carriers: Sequence[str]
) -> tuple[str, ...]:
    if not isinstance(values, Mapping):
        raise ToolCatalogError(
            f"toolkit {task_type!r} role {role!r} must be an object carrying a "
            "'tools' list"
        )
    ids = values.get("tools")
    if not isinstance(ids, list):
        raise ToolCatalogError(
            f"toolkit {task_type!r} role {role!r} must declare a 'tools' list"
        )
    seen: list[str] = []
    for entry in ids:
        if not isinstance(entry, str) or not entry:
            raise ToolCatalogError(
                f"toolkit {task_type!r} role {role!r}: tool id {entry!r} is not text"
            )
        if entry in seen:
            raise ToolCatalogError(
                f"toolkit {task_type!r} role {role!r} repeats tool id {entry!r}"
            )
        manifest = resolve_tool(entry).manifest  # refuses an unregistered id
        if manifest.scope != GENERAL_SCOPE:
            carrier = manifest.scope[len(CARRIER_SCOPE_PREFIX):]
            if carrier not in carriers:
                raise ToolCatalogError(
                    f"toolkit {task_type!r} offers {entry!r}, which is scoped to "
                    f"carrier {carrier!r}; that task type covers {tuple(carriers)}"
                )
        seen.append(entry)
    return tuple(seen)


def parse_toolkit_table(document: object) -> ToolkitTable:
    """Validate a toolkit table document, fail-closed on every field."""

    if not isinstance(document, Mapping):
        raise ToolCatalogError("a toolkit table must be a JSON object")
    schema = document.get("schema")
    if schema != TOOLKIT_SCHEMA:
        raise ToolCatalogError(
            f"toolkit table schema must be {TOOLKIT_SCHEMA!r}, got {schema!r}"
        )
    declared = document.get("toolkits")
    if not isinstance(declared, Mapping) or not declared:
        raise ToolCatalogError("a toolkit table must declare a non-empty 'toolkits' object")
    unknown = sorted(set(declared) - set(TASK_TYPES))
    if unknown:
        raise ToolCatalogError(
            f"toolkit table declares unknown task type(s) {unknown}; the design "
            f"note names {TASK_TYPES}"
        )
    missing = sorted(set(TASK_TYPES) - set(declared))
    if missing:
        raise ToolCatalogError(f"toolkit table declares no toolkit for {missing}")

    toolkits: dict[str, Toolkit] = {}
    for task_type in TASK_TYPES:
        roles = declared[task_type]
        if not isinstance(roles, Mapping):
            raise ToolCatalogError(f"toolkit {task_type!r} must be an object of roles")
        unknown_roles = sorted(set(roles) - set(TOOLKIT_ROLES))
        if unknown_roles:
            raise ToolCatalogError(
                f"toolkit {task_type!r} declares unknown role(s) {unknown_roles}; a "
                f"tool may be called by {TOOLKIT_ROLES}"
            )
        missing_roles = sorted(set(TOOLKIT_ROLES) - set(roles))
        if missing_roles:
            raise ToolCatalogError(
                f"toolkit {task_type!r} declares no {missing_roles} role; declare an "
                "empty 'tools' list to say a role calls nothing yet"
            )
        carriers = TASK_TYPE_CARRIERS[task_type]
        toolkits[task_type] = Toolkit(
            task_type=task_type,
            tools_by_role={
                role: _toolkit_role_ids(
                    roles[role], task_type=task_type, role=role, carriers=carriers
                )
                for role in TOOLKIT_ROLES
            },
        )
    return ToolkitTable(schema=TOOLKIT_SCHEMA, toolkits=toolkits)


def load_toolkit_table(path: Path | str) -> ToolkitTable:
    """Read and validate one toolkit table from disk."""

    file_path = Path(path)
    try:
        document = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ToolCatalogError(f"cannot read toolkit table {file_path}: {error}") from error
    return parse_toolkit_table(document)


def default_toolkit_table(repo_root: Path | None = None) -> ToolkitTable:
    """The committed table at :data:`TOOLKIT_CONFIG_RELPATH`."""

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    return load_toolkit_table(root / TOOLKIT_CONFIG_RELPATH)


# ---------------------------------------------------------------------------
# The eight manifests, and the registration block.
#
# The ids below are STRING LITERALS at the ``TOOL_CATALOG.register`` call
# because ``scripts/checks/engineering_base_check.py`` reads the registered
# set out of this file's source WITHOUT importing the package -- the same
# discipline every other canonical registration site follows.
# :func:`assert_catalog_consistent` then proves each literal agrees with its
# own manifest.
#
# Every entry passes through :func:`build_tool_entry`, which is where the
# system-invoked marker is enforced; ``scripts/checks/tool_catalog_check.py``
# fails if a registration ever bypasses it.
# ---------------------------------------------------------------------------

DIARIZATION_ARTIFACT_MANIFEST = ToolManifest(
    tool_id="saea-tool-diarization-artifact-v1",
    description=(
        "Read and re-derive one sealed saea-diarization-v1 artifact: who spoke "
        "when, per call, from the pinned Sortformer pass. OBS observation only "
        "-- never evidence, never an answer."
    ),
    source_ref="speech_aware_evidence_acquisition.reproduction.diarization:load_diarization",
    pinned_sha256="8dfb36f772250d8cd1c146178834946f50ba8e3f26c00fefd606e358dde87afa",
    inputs={"path": "pathlib.Path | str", "dry_run": "bool"},
    outputs={"artifact": "reproduction.diarization.DiarizationArtifact | DiarizationReadPlan"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="OBS",
    scope=GENERAL_SCOPE,
    ledger_row_type="tool-contact",
)

SLICE_ENCODE_MANIFEST = ToolManifest(
    tool_id="saea-tool-slice-encode-v1",
    description=(
        "Turn one already-cut speech window into the bytes that go on the wire: "
        "raw cut, then rms-norm when declared, then the silence tail. The one "
        "place the transform order is decided."
    ),
    source_ref="speech_aware_evidence_acquisition.reproduction.obs_audio:encode_slice",
    pinned_sha256="20b53a38e119b90a14b953e37aab7bb49bfae5db135d722cd4badff720adca54",
    inputs={
        "slice_samples": "Sequence[int]",
        "sample_rate_hz": "int",
        "preprocess": "Sequence[str]",
        "rms_target_dbfs": "float",
        "tail_silence_seconds": "float",
    },
    outputs={
        "wav_bytes": "bytes",
        "transforms": "tuple[str, ...]",
        "pre_sha256": "str | None",
    },
    changes_bytes=True,
    derivation_record="saea-slice-derivation-v1",
    cost_class="cpu",
    axis="OBS",
    scope=GENERAL_SCOPE,
    ledger_row_type="none",
)

SPEAKER_TURN_UNITS_MANIFEST = ToolManifest(
    tool_id="saea-tool-speaker-turn-units-v2",
    description=(
        "Plan a call's speaker-turn units (OBS-E1 unit plan v2): a proved "
        "tiling of [0, duration) snapped to pauses and speaker changes."
    ),
    source_ref="speech_aware_evidence_acquisition.analysis.e21_speaker_turn_units:plan_units_v2",
    pinned_sha256="f143b844e2dbf72f488663ba9d7a3beca7d6c78df82b574d14a257f2f2978c81",
    inputs={
        "sample_id": "str",
        "segments": "Sequence[SpeakerSegment]",
        "duration_seconds": "float",
        "pauses": "Sequence[Pause]",
        "active": "Sequence[bool]",
        "frame_seconds": "float",
        "max_seconds": "float",
        "min_seconds": "float",
        "snap_radius": "float",
    },
    outputs={"units": "tuple[analysis.e21_speaker_turn_units.UnitV2, ...]"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="OBS",
    scope=f"{CARRIER_SCOPE_PREFIX}earnings21",
    ledger_row_type="none",
)

LEGAL_LABEL_PROJECTION_MANIFEST = ToolManifest(
    tool_id="saea-tool-legal-label-projection-v2",
    description=(
        "Map an illegal SLURP (scenario, action) pair onto the nearest legal "
        "one under slurp-legal-label-projection-v2. Entities are never touched "
        "and an unparsed response stays unparsed."
    ),
    source_ref="speech_aware_evidence_acquisition.reproduction.slurp_scoring:project_slu_label_v2",
    pinned_sha256="d51bfd464df9491092e14a2c3f05b7c69a263f4aa61cc7f8cec308501a14de2f",
    inputs={
        "scenario": "str | None",
        "action": "str | None",
        "inventory": "reproduction.slurp_scoring.LegalIntentInventory",
        "parsed": "bool",
    },
    outputs={"projection": "reproduction.slurp_scoring.LabelProjection"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="USE",
    scope=f"{CARRIER_SCOPE_PREFIX}slurp",
    ledger_row_type="none",
)

REPAIR_ALIGNMENT_MANIFEST = ToolManifest(
    tool_id="saea-tool-repair-alignment-v1",
    description=(
        "Accept a pass-2 delivery only when it differs from its predecessor by "
        "substitutions only, within the span/anchor/fraction bounds; otherwise "
        "refuse and deliver the predecessor verbatim."
    ),
    source_ref="speech_aware_evidence_acquisition.core.repair_alignment:accept_entity_repair",
    pinned_sha256="b648388b31a1e00cfb1c66a581f8c1c973380499bba755a9a61cd1a5a540b8d2",
    inputs={
        "predecessor_text": "str",
        "response_text": "str",
        "max_span_tokens": "int",
        "min_anchor_ratio": "float",
        "max_substituted_fraction": "float",
    },
    outputs={"outcome": "core.repair_alignment.RepairOutcome"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="USE",
    scope=GENERAL_SCOPE,
    ledger_row_type="none",
)

FLAGGED_SPANS_MANIFEST = ToolManifest(
    tool_id="saea-tool-flagged-spans-v1",
    description=(
        "Detect the spans of a draft that deserve a second listen, from one of "
        "two pinned sources: low token-logprob runs, or roster-band near "
        "misses. Non-overlapping, ascending start order."
    ),
    source_ref="speech_aware_evidence_acquisition.core.replay_signals:flag_spans",
    pinned_sha256="edcb9c65f87aa57257317549f0633a9cddd904f20cc57c176686443e70cca334",
    inputs={"source": "str", "args": "tuple", "kwargs": "dict"},
    outputs={"spans": "list[tuple[int, int]] | list[core.flag_sources.RosterBandFlag]"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="OBS",
    scope=GENERAL_SCOPE,
    ledger_row_type="none",
)

SEALED_VECTOR_QUERY_MANIFEST = ToolManifest(
    tool_id="saea-tool-sealed-vector-query-v1",
    description=(
        "Load the receipt-pinned sealed query/facet vectors a supplied phase "
        "ranks the frozen knowledge snapshot against. The query signal is "
        "speech, declared by the fragment and embedded before the flight."
    ),
    source_ref="speech_aware_evidence_acquisition.rails.phase_supply:load_sealed_vectors",
    pinned_sha256="b2eb76eda7d88991c1566df54811b9aac038c641795feb421924eaeaa91da897",
    inputs={
        "path": "pathlib.Path",
        "expected_sha256": "str",
        "dimensions": "Sequence[str]",
    },
    outputs={"vectors": "Mapping[str, Mapping[str, tuple[float, ...]]]"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="SUPPLY",
    scope=GENERAL_SCOPE,
    ledger_row_type="tool-contact",
)

PROMPT_FIT_TOKENS_MANIFEST = ToolManifest(
    tool_id="saea-tool-prompt-fit-tokens-v1",
    description=(
        "Measure a request on the FLIGHT tokenizer through the resident "
        "server's non-generative routes (/props, /apply-template, /tokenize). "
        "No token is generated and no answer is read."
    ),
    source_ref=(
        "speech_aware_evidence_acquisition.core.driver.speech_native:"
        "_LoopbackPromptAuditClient.request_json"
    ),
    pinned_sha256="b08a5d35c3a8c850a7fbf2a8265f6774798aa21a357a2fd70a7e7b0359c1cf04",
    inputs={
        "client": "core.driver.speech_native._LoopbackPromptAuditClient",
        "method": "str",
        "path": "str",
        "payload": "Mapping[str, object] | None",
    },
    outputs={"document": "Mapping[str, object]"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="contact",
    axis="USE",
    scope=GENERAL_SCOPE,
    ledger_row_type="service-contact",
    parallel_safe=False,
    stateless=False,
)

from .tool_wrappers import (  # noqa: E402  (registration block: see above)
    a2t_renderers as _a2t_renderers,
    diarization as _diarization,
    experience_memory as _experience_memory,
    flagged_spans as _flagged_spans,
    legal_label_projection as _legal_label_projection,
    prompt_fit_tokens as _prompt_fit_tokens,
    repair_alignment as _repair_alignment,
    sealed_vector_query as _sealed_vector_query,
    slice_encode as _slice_encode,
    speaker_turn_units as _speaker_turn_units,
)

TOOL_CATALOG.register(
    "saea-tool-diarization-artifact-v1",
    build_tool_entry(DIARIZATION_ARTIFACT_MANIFEST, _diarization.load_diarization_tool),
)
TOOL_CATALOG.register(
    "saea-tool-slice-encode-v1",
    build_tool_entry(SLICE_ENCODE_MANIFEST, _slice_encode.encode_slice_tool),
)
TOOL_CATALOG.register(
    "saea-tool-speaker-turn-units-v2",
    build_tool_entry(SPEAKER_TURN_UNITS_MANIFEST, _speaker_turn_units.plan_units_v2_tool),
)
TOOL_CATALOG.register(
    "saea-tool-legal-label-projection-v2",
    build_tool_entry(
        LEGAL_LABEL_PROJECTION_MANIFEST,
        _legal_label_projection.project_slu_label_v2_tool,
    ),
)
TOOL_CATALOG.register(
    "saea-tool-repair-alignment-v1",
    build_tool_entry(REPAIR_ALIGNMENT_MANIFEST, _repair_alignment.accept_entity_repair_tool),
)
TOOL_CATALOG.register(
    "saea-tool-flagged-spans-v1",
    build_tool_entry(FLAGGED_SPANS_MANIFEST, _flagged_spans.flagged_spans_tool),
)
TOOL_CATALOG.register(
    "saea-tool-sealed-vector-query-v1",
    build_tool_entry(
        SEALED_VECTOR_QUERY_MANIFEST, _sealed_vector_query.load_sealed_vectors_tool
    ),
)
TOOL_CATALOG.register(
    "saea-tool-prompt-fit-tokens-v1",
    build_tool_entry(PROMPT_FIT_TOKENS_MANIFEST, _prompt_fit_tokens.prompt_fit_request_tool),
)


# --- WAVE R7: the eighteen rails/a2t_* renderers -----------------------------
#
# Group A of the reuse map (assessment section 6.1) named every ``rails/a2t_*``
# module a task tool or knowledge view "in the design's own section 7 sense",
# on the strength of their own docstrings ("reads no manifests, audio,
# evaluation fields, model output, scorer, or network service"), and its
# verdict was **"Register, do not rebuild."**
#
# Nothing was rebuilt. ``rails/tool_wrappers/a2t_renderers.py`` holds eighteen
# PASSTHROUGH wrappers -- arguments forwarded unchanged, the wrapped function's
# own return value in ``ToolResult.result`` -- and
# ``tests/unit/test_a2t_renderer_tools.py`` asserts that identity per renderer
# against a direct call, plus the pin, the axis, the scope and the coverage of
# every ``rails/a2t_*.py`` module in the tree.
#
# The ``inputs``/``outputs`` spellings below are the wrapped functions' OWN
# annotations, read off their signatures rather than restated, for the same
# reason the eight tools above spell Python types and not JSON ones: these are
# system-invoked over native objects and a JSON type would claim a decoding
# contract that does not exist.

A2T_CANONICAL_FAMILY_GROUND_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-canonical-family-ground-v1',
    description='Render the value-safe canonical Audio2Tool ground for ONE action family.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_canonical_family_ground:CanonicalFamilyGround.render_family',
    pinned_sha256="1b6f84896b9b697c295793dcd7883026187b37f6a8da9240373182133a1917c0",
    inputs={'family_tag': 'str'},
    outputs={'result': 'str'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_CONSTRUCTION_EXAMPLE_GROUND_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-construction-example-ground-v1',
    description='Build the query-independent construction-example family ground.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_construction_example_ground:build_construction_example_family_ground',
    pinned_sha256="2359584bf348b4780943f69e8bea2b39ece587318fb61ce1e077abd70294afd4",
    inputs={'construction_rows': 'Sequence[A2tKbRow]', 'g5_corpus_path': 'Path', 'forbidden_query_blocks': 'Collection[int]', 'forbidden_source_ids': 'Collection[str]', 'max_examples_per_tool': 'int', 'max_family_ascii_bytes': 'int', 'max_total_ascii_bytes': 'int'},
    outputs={'result': 'ConstructionExampleGround'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_CONSTRUCTION_SEMANTIC_GROUND_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-construction-semantic-ground-v1',
    description='Build construction-conditioned Audio2Tool semantics without source text.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_construction_semantic_ground:build_construction_semantic_ground',
    pinned_sha256="65d407f0b79154d9e8671bedbe0a08b196389417d2ad7c201810f6c263ec37f9",
    inputs={'registry_rows': 'Sequence[Mapping[str, str]]', 'construction_rows': 'Sequence[A2tKbRow]', 'max_utf8_bytes': 'int', 'max_cues_per_pair': 'int'},
    outputs={'result': 'ConstructionSemanticGroundArtifact'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_EXECUTABLE_GROUND_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-executable-ground-v1',
    description='Build the compact, task-wide, values-stripped executable handbook.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_executable_ground:build_executable_ground',
    pinned_sha256="8efe54f2a1676744bea33e9e86b1ed53dd9b95021f0049209945f6ab810d4c16",
    inputs={'registry_rows': 'Sequence[Mapping[str, str]]', 'construction_rows': 'Sequence[A2tKbRow]', 'max_utf8_bytes': 'int'},
    outputs={'result': 'ExecutableGroundArtifact'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_GROUND_PROMPT_ENVELOPES_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-ground-prompt-envelopes-v1',
    description='Build the exact prompt envelopes the executable ground must fit inside.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_executable_ground_prompt_fit:build_ground_envelopes',
    pinned_sha256="48abf19eb610d87c1a265eecb610974e4d1f9ccbc664ce3dd1ac0fdd4f76a5f8",
    inputs={'handbook_text': 'str'},
    outputs={'result': 'tuple[GroundPromptEnvelope, ...]'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='USE',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_EXECUTABLE_SEMANTIC_CARDS_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-executable-semantic-cards-v1',
    description='Build the deterministic, label-free executable semantic card corpus.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards:build_executable_semantic_card_corpus',
    pinned_sha256="0dca111e4562ca42973f2b1aa7f444036419f481ac8ecaab79c68ce5fe6de239",
    inputs={'registry_rows': 'Sequence[Mapping[str, str]]', 'construction_rows': 'Sequence[A2tKbRow]', 'compatibility_rules': 'Sequence[CompatibilityRule]', 'forbidden_example_literals': 'Sequence[str] | set[str] | frozenset[str]', 'max_utf8_bytes': 'int'},
    outputs={'result': 'ExecutableSemanticCardCorpus'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_FROZEN_SEMANTIC_ASSETS_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-frozen-semantic-assets-v1',
    description='Load the frozen, label-free semantic runtime assets at their pinned hashes.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_frozen_semantic_assets:load_frozen_semantic_runtime_assets',
    pinned_sha256="961334919e9ea3b21fd8f58f472afe55f91da60ae985d7884cff590266333ede",
    inputs={'repo': 'Path', 'data_root': 'Path', 'receipt_relpath': 'Path'},
    outputs={'result': 'FrozenSemanticRuntimeAssets'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='tool-contact',
)

A2T_HARD_VALIDITY_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-hard-validity-v1',
    description='Check a tool-call draft for deterministic, deployment-visible invalidity.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_hard_validity:validate_hard_validity',
    pinned_sha256="51498b3ff3a13e358d116a08a97855423af0c2e3708459673ec558a0e68e076e",
    inputs={'response_text': 'str', 'registry_rows': 'Sequence[Mapping[str, str]]'},
    outputs={'result': 'HardValidityReport'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='USE',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_OBSERVATION_STATE_ORGANIZER_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-observation-state-organizer-v1',
    description='Organize sealed ASCII OBS into task-blind structured dialogue state.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_observation_state_organizer:organize_sealed_observation',
    pinned_sha256="2b5ab56501966c525f9b92187a500480cc53bb38bf1d3127386103a72af8bdf1",
    inputs={'sealed_observation_text': 'str'},
    outputs={'result': 'StructuredDialogueStateArtifact'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='ORG',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_PLAIN_ENGLISH_RETRIEVAL_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-plain-english-retrieval-v1',
    description='Retrieve the hierarchical plain-English knowledge packets for one observation.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_plain_english_cards:retrieve_plain_english_packets',
    pinned_sha256="31ddfe1736a3da58ae335eb98aa00f8e1d2a3e52b85c8922a506eef6bbe90a52",
    inputs={'observation_text': 'str', 'corpus': 'PlainEnglishCardCorpus', 'detailed_tool_limit': 'int', 'behavior_card_limit': 'int', 'shuffle_seed': 'int', 'observation_character_cap': 'int', 'packet_utf8_byte_cap': 'int'},
    outputs={'result': 'PlainEnglishPacketRoute'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_CALL_ARRAY_RESPONSE_FORMAT_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-call-array-response-format-v1',
    description='Render the strict JSON-Schema response format for a routed tool subset.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_response_schema:audio2tool_call_array_response_format',
    pinned_sha256="53fdb8cb202d4d56435a59c8d1585b8afa2e968e17330f7861b89f4a49191f6c",
    inputs={'registry_rows': 'Sequence[Mapping[str, str]]', 'selected_cards': 'Sequence[ToolSemanticCard]', 'schema_name': 'str', 'min_calls': 'int', 'max_calls': 'int'},
    outputs={'result': 'dict[str, object]'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='USE',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_SELECT_FILL_FACTORIAL_BINDING_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-select-fill-factorial-binding-v1',
    description="Bind the SELECT/FILL factorial cell's predecessor selector states.",
    source_ref='speech_aware_evidence_acquisition.rails.a2t_select_fill_factorial:bind_factorial_predecessors',
    pinned_sha256="016970d5bdb810581439151dc31ce48b0ba0c6b82aa5274cd5f2264abef9bfef",
    inputs={'selector_states': 'Mapping[str, Mapping[str, StageStateEnvelope]]', 'sample_ids': 'Sequence[str]', 'expected_ground_sha256': 'Mapping[str, Mapping[str, str]]', 'split_identity_sha256': 'str', 'expected_row_count': 'int'},
    outputs={'result': 'tuple[FactorialPredecessorBinding, ...]'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='ORG',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_ROUTING_KNOWLEDGE_GROUND_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-routing-knowledge-ground-v1',
    description='Build the selection-scoped routing knowledge ground.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_select_fill_ground:build_routing_knowledge_ground',
    pinned_sha256="845edb342336a0526961bb78b8a18331568f632aa16598077e9581a2e86f5fa1",
    inputs={'corpus': 'ExecutableSemanticCardCorpus', 'candidate_tool_names': 'Sequence[str]', 'byte_cap': 'int'},
    outputs={'result': 'RoutingKnowledgeGround'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_SELECTED_TOOL_GROUND_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-selected-tool-ground-v1',
    description='Render the compact, value-safe decision cards for the selected tools.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_selected_tool_ground:SelectedToolDecisionGround.build',
    pinned_sha256="592c49b796447d40bb222c7d6df44d52d04f5973de1f682db7e50f77e1319a0b",
    inputs={'selected_tool_names': 'Sequence[str]'},
    outputs={'result': 'SelectedToolDecisionPacket'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_SEMANTIC_MICROGROUND_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-semantic-microground-v1',
    description='Route bounded executable semantic cards without gold or learned control.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_semantic_microground:route_semantic_microground',
    pinned_sha256="9fa2d3245ddccc79435a4dd094c2406a64525f975b9c85e24fc3dbb476a90cb8",
    inputs={'corpus': 'ExecutableSemanticCardCorpus', 'structured_state': 'Mapping[str, object] | None', 'observation': 'str | None', 'max_utf8_bytes': 'int'},
    outputs={'result': 'SemanticMicrogroundRoute'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_SEMANTIC_RANKING_FUSION_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-semantic-ranking-fusion-v1',
    description='Fuse the frozen tool-tier semantic rankings by reciprocal rank.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_semantic_router:fuse_semantic_rankings',
    pinned_sha256="52dbdefedd33f6b3834f399f4c32af70468734899736a42cf8c53b1068aa1a2a",
    inputs={'rankings': 'Sequence[SemanticRanking]', 'top_k': 'int', 'source_names': 'Sequence[str]', 'constant': 'int'},
    outputs={'result': 'FusedSemanticRanking'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='SUPPLY',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_SELECT_STAGE_ENVELOPE_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-select-stage-envelope-v1',
    description='Build the canonical, hash-bound SELECT stage-state envelope.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_stage_state:build_select_stage_envelope',
    pinned_sha256="bb69effa9baaa7ac7bf0be8102c0938ae25529870d19ba4c885816bb64977313",
    inputs={'sample_identity_sha256': 'str', 'split_identity_sha256': 'str', 'speech_packet_sha256': 'str', 'source_query_state_sha256': 'str', 'source_response_sha256': 'str', 'observation_state_sha256': 'str', 'observation_source_response_sha256': 'str', 'source_request_body_sha256': 'str', 'candidate_tool_names': 'Sequence[str]', 'ground_sha256': 'str', 'response_schema_sha256': 'str', 'predecessor_envelope_sha256': 'str | None', 'occurrences': 'Sequence[SelectOccurrence]'},
    outputs={'result': 'StageStateEnvelope'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='ORG',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

A2T_STRUCTURED_DIALOGUE_STATE_V1_MANIFEST = ToolManifest(
    tool_id='saea-tool-a2t-structured-dialogue-state-v1',
    description='Derive strict, task-blind dialogue state from sealed Audio2Tool OBS.',
    source_ref='speech_aware_evidence_acquisition.rails.a2t_structured_dialogue_state:build_structured_dialogue_state',
    pinned_sha256="db2fef183ac12970908d873ba9cbc9687c71f7f639c37007b4053fde0623b085",
    inputs={'sealed_observation_text': 'str', 'turns': 'Sequence[ObservationTurnSpan]', 'current_request': 'StateValue', 'active_actions': 'Sequence[StateValue]', 'superseded_actions': 'Sequence[StateValue]', 'superseded_values': 'Sequence[StateValue]', 'irrelevant_context': 'Sequence[StateValue]'},
    outputs={'result': 'StructuredDialogueStateArtifact'},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis='ORG',
    scope=f"{CARRIER_SCOPE_PREFIX}audio2tool",
    ledger_row_type='none',
)

TOOL_CATALOG.register(
    'saea-tool-a2t-canonical-family-ground-v1',
    build_tool_entry(A2T_CANONICAL_FAMILY_GROUND_V1_MANIFEST, _a2t_renderers.render_family_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-construction-example-ground-v1',
    build_tool_entry(A2T_CONSTRUCTION_EXAMPLE_GROUND_V1_MANIFEST, _a2t_renderers.build_construction_example_family_ground_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-construction-semantic-ground-v1',
    build_tool_entry(A2T_CONSTRUCTION_SEMANTIC_GROUND_V1_MANIFEST, _a2t_renderers.build_construction_semantic_ground_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-executable-ground-v1',
    build_tool_entry(A2T_EXECUTABLE_GROUND_V1_MANIFEST, _a2t_renderers.build_executable_ground_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-ground-prompt-envelopes-v1',
    build_tool_entry(A2T_GROUND_PROMPT_ENVELOPES_V1_MANIFEST, _a2t_renderers.build_ground_envelopes_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-executable-semantic-cards-v1',
    build_tool_entry(A2T_EXECUTABLE_SEMANTIC_CARDS_V1_MANIFEST, _a2t_renderers.build_executable_semantic_card_corpus_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-frozen-semantic-assets-v1',
    build_tool_entry(A2T_FROZEN_SEMANTIC_ASSETS_V1_MANIFEST, _a2t_renderers.load_frozen_semantic_runtime_assets_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-hard-validity-v1',
    build_tool_entry(A2T_HARD_VALIDITY_V1_MANIFEST, _a2t_renderers.validate_hard_validity_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-observation-state-organizer-v1',
    build_tool_entry(A2T_OBSERVATION_STATE_ORGANIZER_V1_MANIFEST, _a2t_renderers.organize_sealed_observation_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-plain-english-retrieval-v1',
    build_tool_entry(A2T_PLAIN_ENGLISH_RETRIEVAL_V1_MANIFEST, _a2t_renderers.retrieve_plain_english_packets_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-call-array-response-format-v1',
    build_tool_entry(A2T_CALL_ARRAY_RESPONSE_FORMAT_V1_MANIFEST, _a2t_renderers.audio2tool_call_array_response_format_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-select-fill-factorial-binding-v1',
    build_tool_entry(A2T_SELECT_FILL_FACTORIAL_BINDING_V1_MANIFEST, _a2t_renderers.bind_factorial_predecessors_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-routing-knowledge-ground-v1',
    build_tool_entry(A2T_ROUTING_KNOWLEDGE_GROUND_V1_MANIFEST, _a2t_renderers.build_routing_knowledge_ground_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-selected-tool-ground-v1',
    build_tool_entry(A2T_SELECTED_TOOL_GROUND_V1_MANIFEST, _a2t_renderers.build_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-semantic-microground-v1',
    build_tool_entry(A2T_SEMANTIC_MICROGROUND_V1_MANIFEST, _a2t_renderers.route_semantic_microground_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-semantic-ranking-fusion-v1',
    build_tool_entry(A2T_SEMANTIC_RANKING_FUSION_V1_MANIFEST, _a2t_renderers.fuse_semantic_rankings_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-select-stage-envelope-v1',
    build_tool_entry(A2T_SELECT_STAGE_ENVELOPE_V1_MANIFEST, _a2t_renderers.build_select_stage_envelope_tool),
)
TOOL_CATALOG.register(
    'saea-tool-a2t-structured-dialogue-state-v1',
    build_tool_entry(A2T_STRUCTURED_DIALOGUE_STATE_V1_MANIFEST, _a2t_renderers.build_structured_dialogue_state_tool),
)

# --- end WAVE R7 -------------------------------------------------------------

assert_catalog_consistent()


__all__ = [
    "CARRIER_SCOPE_PREFIX",
    "COST_CLASSES",
    "DerivationRecord",
    "GENERAL_SCOPE",
    "INVOCATION",
    "LEDGER_ROW_TYPES",
    "LOCKED_CARRIERS",
    "TASK_TYPES",
    "TASK_TYPE_CARRIERS",
    "TOOLKIT_CONFIG_RELPATH",
    "TOOLKIT_ROLES",
    "TOOLKIT_SCHEMA",
    "TOOL_AXES",
    "TOOL_CATALOG",
    "TOOL_ID_PREFIX",
    "ToolCatalogError",
    "ToolEntry",
    "ToolManifest",
    "ToolResult",
    "Toolkit",
    "ToolkitTable",
    "assert_catalog_consistent",
    "assert_pinned_hash",
    "build_tool_entry",
    "catalog_ids",
    "default_toolkit_table",
    "load_source_target",
    "load_toolkit_table",
    "parse_toolkit_table",
    "resolve_tool",
    "source_sha256",
    "to_local_function",
    "to_tool_card",
    "tool_input_params",
]


# Explicit task-action adapters; historical catalog callers retain system invocation.

TASK_CONTRACT_ACTION_MANIFEST = ToolManifest(
    tool_id='saea-tool-task-contract-v1',
    description="Return the current task's legal contract without reading a dataset row.",
    source_ref="speech_aware_evidence_acquisition.rails.tool_wrappers.phase_knowledge:read_task_contract",
    pinned_sha256="93b2f93e56c66cca66c1af79402395198bba6848e057c116811abc1c2018066a",
    inputs={'context': 'AgentRuntimeContext'},
    outputs={"result": "Mapping | PhaseSupply"},
    changes_bytes=False, derivation_record=None, cost_class="cpu",
    axis='ORG', scope=GENERAL_SCOPE, ledger_row_type="none",
)
TOOL_CATALOG.register(
    'saea-tool-task-contract-v1',
    build_tool_entry(TASK_CONTRACT_ACTION_MANIFEST, _phase_knowledge.read_task_contract),
)

PHASE_KNOWLEDGE_ACTION_MANIFEST = ToolManifest(
    tool_id='saea-tool-phase-knowledge-v1',
    description='Execute the shared prepared knowledge provider for the successor state.',
    source_ref="speech_aware_evidence_acquisition.rails.tool_wrappers.phase_knowledge:retrieve_phase_knowledge",
    pinned_sha256="5c626e6119a753fdcff4cd4f22c90d71a88192e6b54f747db992a21a1c88b418",
    inputs={'supply_for_phase': 'Callable', 'next_phase': 'str', 'context': 'AgentRuntimeContext'},
    outputs={"result": "Mapping | PhaseSupply"},
    changes_bytes=False, derivation_record=None, cost_class="cpu",
    axis='SUPPLY', scope=GENERAL_SCOPE, ledger_row_type="none",
)
TOOL_CATALOG.register(
    'saea-tool-phase-knowledge-v1',
    build_tool_entry(PHASE_KNOWLEDGE_ACTION_MANIFEST, _phase_knowledge.retrieve_phase_knowledge),
)

CANDIDATE_CONTRACT_LOOKUP_ACTION_MANIFEST = ToolManifest(
    tool_id="saea-tool-candidate-contract-lookup-v1",
    description=(
        "Resolve ordered candidate IDs against a canonical task contract; "
        "return value-free schema and contrast evidence."
    ),
    source_ref=(
        "speech_aware_evidence_acquisition.rails.tool_wrappers."
        "candidate_contract_lookup:lookup_candidate_contracts"
    ),
    pinned_sha256="723bff22b561686e39b3c1c619551a43c24afd96b441d2209c4221f24bc41507",
    inputs={
        "provider": "CandidateContractProvider",
        "candidate_ids": "Sequence[str]",
    },
    outputs={"result": "CandidateContractLookupResult"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="ORG",
    scope=GENERAL_SCOPE,
    ledger_row_type="none",
)
TOOL_CATALOG.register(
    "saea-tool-candidate-contract-lookup-v1",
    build_tool_entry(
        CANDIDATE_CONTRACT_LOOKUP_ACTION_MANIFEST,
        _candidate_contract_lookup.lookup_candidate_contracts,
    ),
)


CORRECTIVE_MEMORY_ACTION_MANIFEST = ToolManifest(
    tool_id="saea-tool-corrective-memory-v1",
    description=(
        "Select offline-admitted corrective guidance for the successor phase; "
        "the Solver retains final-answer authority."
    ),
    source_ref=(
        "speech_aware_evidence_acquisition.rails.tool_wrappers.experience_memory:"
        "select_corrective_memory"
    ),
    pinned_sha256="23877f7d1f4f89f180026c23571e181fd52a5b09ad66cec6f28ec3cfdf186c02",
    inputs={
        "memory_binding": "LoadedExperienceMemoryBinding",
        "next_phase": "str",
        "context": "AgentRuntimeContext",
    },
    outputs={"result": "ExperienceMemorySelection"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="cpu",
    axis="ORG",
    scope=GENERAL_SCOPE,
    ledger_row_type="none",
)
TOOL_CATALOG.register(
    "saea-tool-corrective-memory-v1",
    build_tool_entry(
        CORRECTIVE_MEMORY_ACTION_MANIFEST,
        _experience_memory.select_corrective_memory,
    ),
)


# Cached speech evidence retains its original neural-contact provenance.

PREPARED_SPEECH_OBSERVATION_MANIFEST = ToolManifest(
    tool_id="saea-tool-prepared-speech-observation-v1",
    description="Read a pinned transcription of the original utterance as OBS evidence.",
    source_ref=(
        "speech_aware_evidence_acquisition.rails.tool_wrappers.speech_observation:"
        "read_prepared_speech_observation"
    ),
    pinned_sha256="a6b27818e4bb1c5e6198a36a1cad7b05e8773a6fcde41a8e6be216ff89560e62",
    inputs={"catalog": "LoadedSpeechObservationCatalog", "context": "AgentRuntimeContext"},
    outputs={"result": "SpeechObservationSelection"},
    changes_bytes=False, derivation_record=None, cost_class="cpu",
    axis="OBS", scope=GENERAL_SCOPE, ledger_row_type="tool-contact",
)
TOOL_CATALOG.register(
    "saea-tool-prepared-speech-observation-v1",
    build_tool_entry(
        PREPARED_SPEECH_OBSERVATION_MANIFEST,
        _speech_observation.read_prepared_speech_observation,
    ),
)


LIVE_SPEECH_OBSERVATION_MANIFEST = ToolManifest(
    tool_id="saea-tool-live-speech-observation-v1",
    description=(
        "Decode the current full utterance with the registered local speech "
        "observer only when selected by the frozen core."
    ),
    source_ref=(
        "speech_aware_evidence_acquisition.rails.tool_wrappers.live_speech_observation:"
        "observe_live_speech"
    ),
    pinned_sha256="916728195c6979ddb61cc1d7fe9b3326904901d1e79ae71309650799f4e103f1",
    inputs={
        "provider": "LiveSpeechObservationProvider",
        "context": "AgentRuntimeContext",
        "arguments": "Mapping",
        "source_response_sha256": "str",
    },
    outputs={"result": "SpeechObservationSelection"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="contact",
    axis="OBS",
    scope=GENERAL_SCOPE,
    ledger_row_type="tool-contact",
)
TOOL_CATALOG.register(
    "saea-tool-live-speech-observation-v1",
    build_tool_entry(
        LIVE_SPEECH_OBSERVATION_MANIFEST,
        _live_speech_observation.observe_live_speech,
    ),
)


LIVE_SPEECH_SPAN_MANIFEST = ToolManifest(
    tool_id="saea-tool-live-speech-span-v1",
    description=(
        "Decode a bounded span of the current registered speech execution unit "
        "only when selected by the frozen core."
    ),
    source_ref=(
        "speech_aware_evidence_acquisition.rails.tool_wrappers.live_speech_span:"
        "observe_live_speech_span"
    ),
    pinned_sha256="07c4f078a10b97b2099b73d88bbf6e6205e2e5f6af5e55af39a7786bf919eb7b",
    inputs={
        "provider": "LiveSpeechObservationProvider",
        "context": "AgentRuntimeContext",
        "arguments": "Mapping",
        "source_response_sha256": "str",
    },
    outputs={"result": "SpeechObservationSelection"},
    changes_bytes=False,
    derivation_record=None,
    cost_class="contact",
    axis="OBS",
    scope=GENERAL_SCOPE,
    ledger_row_type="tool-contact",
)
TOOL_CATALOG.register(
    "saea-tool-live-speech-span-v1",
    build_tool_entry(
        LIVE_SPEECH_SPAN_MANIFEST,
        _live_speech_span.observe_live_speech_span,
    ),
)


KNOWLEDGE_TARGET_LOOKUP_MANIFEST = ToolManifest(
    tool_id="saea-tool-knowledge-target-lookup-v1",
    description="Read bounded target-specific values from one frozen named knowledge store.",
    source_ref="speech_aware_evidence_acquisition.rails.tool_wrappers.phase_knowledge:lookup_target_knowledge",
    pinned_sha256="686cde0eb0246d9ed720352f75cdf8e167374fb41394fccb1ebf87dc8e2655ec",
    inputs={"snapshot": "KnowledgeSnapshot", "query_state": "QueryState",
            "candidate_ids": "Sequence[str]", "max_values_per_candidate": "int",
            "max_total_values": "int", "already_visible_value_ids": "Sequence[str]"},
    outputs={"result": "KnowledgeTargetSelection"},
    changes_bytes=False, derivation_record=None, cost_class="cpu",
    axis="SUPPLY", scope=GENERAL_SCOPE, ledger_row_type="none",
)
TOOL_CATALOG.register(
    "saea-tool-knowledge-target-lookup-v1",
    build_tool_entry(KNOWLEDGE_TARGET_LOOKUP_MANIFEST, _phase_knowledge.lookup_target_knowledge),
)
