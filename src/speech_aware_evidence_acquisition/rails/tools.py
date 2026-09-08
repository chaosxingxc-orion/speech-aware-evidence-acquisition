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
``reproduction/ojw/components.py``). That ruling is not re-litigated here.

Every entry in this catalog is a **system-invoked** tool: the harness -- the
Planner reading a manifest, or a phase of ``rails.controllers.
EvidenceAgentController`` -- decides that it runs. No manifest in this
catalog is ever rendered into a prompt, offered to the core as a callable
function, or selected by model output. That is enforced in code, not in
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
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping

from ..core.base import Registry
from .errors import RailsError


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
    pinned_sha256="8a64a4de71970d01ac8cb4b98a29a7fe4efdcfdd6e417bc986409c3d0b4afc5d",
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
    diarization as _diarization,
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

assert_catalog_consistent()


__all__ = [
    "CARRIER_SCOPE_PREFIX",
    "COST_CLASSES",
    "DerivationRecord",
    "GENERAL_SCOPE",
    "INVOCATION",
    "LEDGER_ROW_TYPES",
    "LOCKED_CARRIERS",
    "TOOL_AXES",
    "TOOL_CATALOG",
    "TOOL_ID_PREFIX",
    "ToolCatalogError",
    "ToolEntry",
    "ToolManifest",
    "ToolResult",
    "assert_catalog_consistent",
    "assert_pinned_hash",
    "build_tool_entry",
    "catalog_ids",
    "load_source_target",
    "resolve_tool",
    "source_sha256",
    "to_local_function",
    "to_tool_card",
    "tool_input_params",
]
