"""C4a consolidation: one generic ``AgentController`` base for a sequenced
``PhaseProgram`` (config-declared phase list), replacing the need for every
new fixed multi-contact experiment to hand-write its own controller class the
way ``rails.kb_policy.KbAlphaBlendController`` and
``rails.probes.a2t_select_fill_agentloop.SingleContactPhaseController`` each
did.

Two pieces:

* :class:`PhaseProgram` / :class:`PhaseSpec` -- a small, strictly-validated,
  content-hashable declaration of a fixed contact sequence, loaded from
  ``configs/policy/phase-*.json`` by :func:`load_phase_program`. Five
  programs ship today: ``phase-direct-only-v1`` (one phase),
  ``phase-direct-evidence-alpha-blend-v1`` (direct, then an optional
  evidence contact -- the alpha-blend *scoring* stays in ``rails.kb_policy``;
  this module only sequences the two contacts and threads state),
  ``phase-select-then-fill-v1`` (a hard barrier between ``select`` and
  ``fill`` -- see :mod:`rails.phase_runner` for how the barrier is actually
  realized), ``phase-draft-revise-v1`` (``draft`` then ``revise``, no
  barrier), and ``phase-slots-given-intent-v1`` (one slot-extraction contact
  conditioned on an already-sealed intent).
* :class:`EvidenceAgentController` -- one ``AgentController`` (the
  ``rails.runner.AgentController`` Protocol) that walks a ``PhaseProgram``'s
  phases in order, one contact per phase. Per-phase content (the actual
  instruction text, and an optional response format) is never hard-coded
  here: it comes from a caller-injected ``material_for_phase`` callable
  returning a :class:`~.material.PhaseMaterial`. An optional
  ``supply_for_phase`` callable may return a :class:`~.supply.SupplyPacket`
  whose ``prompt_block`` text is folded into that phase's instruction (the
  same "prompt-level delivery only" discipline ``rails.supply`` already
  documents) -- this module never ranks or fuses evidence itself. An
  optional ``stop_policy`` callable lets a non-final phase decide to stop
  early instead of continuing to the next phase (used by
  ``phase-direct-evidence-alpha-blend-v1``: a caller-injected policy mirrors
  ``KbAlphaBlendController``'s own "the direct-decode label already wins,
  skip the evidence contact" shortcut, without this module re-implementing
  that ranking/fusion decision).

Every phase transition this controller emits between two of its own phases
is ``action_kind="organize"``: it never claims new knowledge-snapshot
values/facets (that is ``rails.kb_policy``'s job, reached only through its
own controller); it only seals the completed phase's raw response as one
hash-bound :class:`~.knowledge.AgentStateArtifact` and carries it forward on
the successor ``QueryState.agent_state_ids``, exactly the discipline
``rails.runner._validate_new_agent_states``/``assert_agent_step_binding``
already enforce for every other controller in this study.

Registration mirrors ``rails.kb_policy.register_kb_policy_v1``: every
program id is registered into the shared ``core.base.AGENT_CONTROLLERS``
registry at import time, with a snapshot-free, always-safe default factory
(a controller whose ``material_for_phase`` synthesizes a generic instruction
per phase rather than reading any per-run injected material) -- the same
"maximally conservative default" shape ``kb_policy``'s own module docstring
describes. A real flight builds its OWN richer ``material_for_phase`` (and
optionally ``supply_for_phase``/``stop_policy``) and passes a fresh
``core.base.Registry`` as ``controller_registry=`` to
``rails.runner.run_speech_native_agent_loop`` (or, more commonly, calls
``rails.phase_runner.run_agent_phase``/``run_program``, which build that
private registry for the caller).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.base import AGENT_CONTROLLERS
from .errors import RailsError
from .knowledge import AgentStateArtifact, AgentStepTransition, QueryState
from .material import PhaseMaterial
from .runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
)
from .supply import SupplyPacket

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROGRAM_CONFIG_DIR = _REPO_ROOT / "configs" / "policy"

PHASE_PROGRAM_SCHEMA = "saea-phase-program-v1"

#: A phase's declared knowledge posture. "none": the phase's instruction is
#: whatever ``material_for_phase`` returns, with no ``supply_for_phase``
#: content expected. "supplied": the phase MAY have a
#: ``supply_for_phase``-sourced ``SupplyPacket`` folded into its instruction.
#: Deliberately closed and small -- this module does not itself rank or
#: fuse evidence (module docstring), so it has no need of a richer taxonomy.
PHASE_KNOWLEDGE_KINDS = frozenset({"none", "supplied"})

#: "always-run-full-program": every phase runs in order; the controller
#: stops unconditionally after the last one.
#: "stop-policy-optional-early-exit": after each NON-FINAL phase, an
#: injected ``stop_policy`` (if given) may end the program early, keeping
#: that phase's own response as the final answer -- the last phase always
#: stops regardless.
PHASE_PROGRAM_STOP_RULES = frozenset(
    {"always-run-full-program", "stop-policy-optional-early-exit"}
)

_PHASE_SPEC_KEYS = frozenset(
    {"name", "purpose", "knowledge", "response_format_id", "barrier"}
)
_PHASE_PROGRAM_KEYS = frozenset(
    {"schema", "program_id", "phases", "max_contacts", "stop_rule"}
)


class RailsControllersError(RailsError):
    """A ``PhaseProgram``/``PhaseSpec`` config, or an ``EvidenceAgentController``
    input (material, supply, or a controller-protocol violation), was invalid."""


def _require_nonempty_str(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RailsControllersError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True)
class PhaseSpec:
    """One phase's fixed, config-declared shape (never per-run content --
    the actual instruction/response-format material comes from the
    caller-injected ``material_for_phase`` callable at run time)."""

    name: str
    purpose: str
    knowledge: str
    response_format_id: str | None
    barrier: bool

    def validate(self) -> "PhaseSpec":
        _require_nonempty_str(self.name, field="PhaseSpec.name")
        _require_nonempty_str(self.purpose, field="PhaseSpec.purpose")
        if self.knowledge not in PHASE_KNOWLEDGE_KINDS:
            raise RailsControllersError(
                f"PhaseSpec.knowledge must be one of {sorted(PHASE_KNOWLEDGE_KINDS)}, "
                f"got {self.knowledge!r}"
            )
        if self.response_format_id is not None:
            _require_nonempty_str(
                self.response_format_id, field="PhaseSpec.response_format_id"
            )
        if not isinstance(self.barrier, bool):
            raise RailsControllersError("PhaseSpec.barrier must be a boolean")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "name": self.name,
            "purpose": self.purpose,
            "knowledge": self.knowledge,
            "response_format_id": self.response_format_id,
            "barrier": self.barrier,
        }


@dataclass(frozen=True)
class PhaseProgram:
    """A fixed, ordered sequence of :class:`PhaseSpec` plus the trajectory
    ceiling and stop discipline a bound ``EvidenceAgentController`` enforces
    for it."""

    program_id: str
    phases: tuple[PhaseSpec, ...]
    max_contacts: int
    stop_rule: str

    def validate(self) -> "PhaseProgram":
        _require_nonempty_str(self.program_id, field="PhaseProgram.program_id")
        if not isinstance(self.phases, tuple) or not self.phases:
            raise RailsControllersError(
                "PhaseProgram.phases must be a non-empty tuple"
            )
        names: list[str] = []
        for phase in self.phases:
            if not isinstance(phase, PhaseSpec):
                raise RailsControllersError(
                    "PhaseProgram.phases entries must be PhaseSpec instances"
                )
            phase.validate()
            names.append(phase.name)
        if len(set(names)) != len(names):
            raise RailsControllersError(
                "PhaseProgram.phases must have unique phase names"
            )
        if (
            isinstance(self.max_contacts, bool)
            or not isinstance(self.max_contacts, int)
            or self.max_contacts < len(self.phases)
        ):
            raise RailsControllersError(
                "PhaseProgram.max_contacts must be an int >= len(phases)"
            )
        if self.stop_rule not in PHASE_PROGRAM_STOP_RULES:
            raise RailsControllersError(
                f"PhaseProgram.stop_rule must be one of "
                f"{sorted(PHASE_PROGRAM_STOP_RULES)}, got {self.stop_rule!r}"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": PHASE_PROGRAM_SCHEMA,
            "program_id": self.program_id,
            "phases": [phase.as_json() for phase in self.phases],
            "max_contacts": self.max_contacts,
            "stop_rule": self.stop_rule,
        }

    def phase_names(self) -> tuple[str, ...]:
        return tuple(phase.name for phase in self.validate().phases)

    def phase(self, name: str) -> PhaseSpec:
        for phase in self.validate().phases:
            if phase.name == name:
                return phase
        raise RailsControllersError(
            f"PhaseProgram {self.program_id!r} has no phase named {name!r}"
        )

    def solo(self, phase_name: str) -> "PhaseProgram":
        """Reduce this program to exactly one named phase: the shape
        ``phase_runner.run_agent_phase`` needs for one whole-roster,
        single-contact invocation -- also the shape every ``barrier`` phase
        must run as (``phase_runner`` module docstring)."""

        phase = self.phase(phase_name)
        return PhaseProgram(
            program_id=f"{self.program_id}:{phase_name}",
            phases=(phase,),
            max_contacts=1,
            stop_rule="always-run-full-program",
        ).validate()


def load_phase_program(path: Path | str) -> PhaseProgram:
    """Strictly parse one ``configs/policy/phase-*.json`` fragment.

    Refuses: a document that is not a JSON object; an unknown or missing
    top-level key; ``schema`` other than :data:`PHASE_PROGRAM_SCHEMA`; a
    phase entry that is not a JSON object, or carries an unknown/missing
    key; anything :meth:`PhaseProgram.validate`/:meth:`PhaseSpec.validate`
    themselves refuse (empty ``phases``, duplicate phase names,
    ``max_contacts`` below ``len(phases)``, an unknown ``stop_rule``).
    """

    resolved = Path(path)
    try:
        document = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise RailsControllersError(f"phase program config not found: {resolved}") from None
    except json.JSONDecodeError as error:
        raise RailsControllersError(
            f"phase program config {resolved} is not valid JSON: {error}"
        ) from error
    if not isinstance(document, dict):
        raise RailsControllersError(
            f"phase program config {resolved} must be a JSON object"
        )
    unknown_top = set(document) - _PHASE_PROGRAM_KEYS
    if unknown_top:
        raise RailsControllersError(
            f"phase program config {resolved} has unknown keys: {sorted(unknown_top)}"
        )
    missing_top = _PHASE_PROGRAM_KEYS - set(document)
    if missing_top:
        raise RailsControllersError(
            f"phase program config {resolved} is missing keys: {sorted(missing_top)}"
        )
    if document["schema"] != PHASE_PROGRAM_SCHEMA:
        raise RailsControllersError(
            f"phase program config {resolved} schema must be "
            f"{PHASE_PROGRAM_SCHEMA!r}, got {document['schema']!r}"
        )
    raw_phases = document["phases"]
    if not isinstance(raw_phases, list) or not raw_phases:
        raise RailsControllersError(
            f"phase program config {resolved} 'phases' must be a non-empty array"
        )
    phases: list[PhaseSpec] = []
    for entry in raw_phases:
        if not isinstance(entry, dict):
            raise RailsControllersError(
                f"phase program config {resolved} has a non-object phase entry"
            )
        unknown_phase = set(entry) - _PHASE_SPEC_KEYS
        if unknown_phase:
            raise RailsControllersError(
                f"phase program config {resolved} phase entry has unknown keys: "
                f"{sorted(unknown_phase)}"
            )
        missing_phase = _PHASE_SPEC_KEYS - set(entry)
        if missing_phase:
            raise RailsControllersError(
                f"phase program config {resolved} phase entry is missing keys: "
                f"{sorted(missing_phase)}"
            )
        phases.append(
            PhaseSpec(
                name=entry["name"],
                purpose=entry["purpose"],
                knowledge=entry["knowledge"],
                response_format_id=entry["response_format_id"],
                barrier=entry["barrier"],
            ).validate()
        )
    program = PhaseProgram(
        program_id=document["program_id"],
        phases=tuple(phases),
        max_contacts=document["max_contacts"],
        stop_rule=document["stop_rule"],
    )
    return program.validate()


MaterialForPhase = Callable[[str, AgentRuntimeContext], PhaseMaterial]
SupplyForPhase = Callable[[str, AgentRuntimeContext], SupplyPacket | None]
StopPolicy = Callable[[AgentRuntimeContext, Sequence[str]], bool]


class EvidenceAgentController:
    """One generic ``rails.runner.AgentController`` walking a
    :class:`PhaseProgram` phase-by-phase (module docstring).

    ``material_for_phase(phase_name, context)`` must return a validated
    :class:`~.material.PhaseMaterial`; its ``response_format`` presence must
    agree with the phase's own declared ``response_format_id`` (both
    present, or both absent). ``supply_for_phase``, when given, may return a
    :class:`~.supply.SupplyPacket` whose ``prompt_block`` is appended to
    that phase's instruction text. ``stop_policy`` is consulted only for a
    program whose ``stop_rule`` is ``"stop-policy-optional-early-exit"``,
    only after a NON-FINAL phase, with the tuple of phase names completed so
    far; returning ``True`` stops the program on that phase's own response.

    One instance is bound to exactly one sample's trajectory (mirroring
    every other controller in this study --
    ``rails.runner._run_agent_trajectory`` builds one controller per sample
    via ``controller_factory(sample_id)`` and reuses it for that whole
    trajectory).
    """

    def __init__(
        self,
        *,
        program: PhaseProgram,
        material_for_phase: MaterialForPhase,
        supply_for_phase: SupplyForPhase | None = None,
        stop_policy: StopPolicy | None = None,
    ) -> None:
        program.validate()
        if not callable(material_for_phase):
            raise RailsControllersError(
                "EvidenceAgentController requires a callable material_for_phase"
            )
        if supply_for_phase is not None and not callable(supply_for_phase):
            raise RailsControllersError(
                "EvidenceAgentController supply_for_phase must be callable or None"
            )
        if stop_policy is not None and not callable(stop_policy):
            raise RailsControllersError(
                "EvidenceAgentController stop_policy must be callable or None"
            )
        self._program = program
        self._material_for_phase = material_for_phase
        self._supply_for_phase = supply_for_phase
        self._stop_policy = stop_policy
        self._sealed: dict[str, AgentStateArtifact] = {}
        self._completed: list[str] = []
        self._pending_contact_id: str | None = None
        self._initial_dispatched = False

    @property
    def program(self) -> PhaseProgram:
        return self._program

    @property
    def sealed_states(self) -> Mapping[str, AgentStateArtifact]:
        """This sample's own sealed phase states so far, keyed by phase
        name -- observability/testing only, never consulted by the runner."""

        return dict(self._sealed)

    def _dispatch(self, phase: PhaseSpec, context: AgentRuntimeContext) -> AgentContactPlan:
        material = self._material_for_phase(phase.name, context)
        if not isinstance(material, PhaseMaterial):
            raise RailsControllersError(
                "material_for_phase must return a PhaseMaterial"
            )
        material.validate()
        declares_format = phase.response_format_id is not None
        has_format = material.response_format is not None
        if declares_format != has_format:
            raise RailsControllersError(
                f"phase {phase.name!r} declares response_format_id="
                f"{phase.response_format_id!r} but material.response_format "
                f"presence does not match ({has_format!r})"
            )
        instruction = material.instruction
        if self._supply_for_phase is not None:
            supply = self._supply_for_phase(phase.name, context)
            if supply is not None:
                if not isinstance(supply, SupplyPacket):
                    raise RailsControllersError(
                        "supply_for_phase must return a SupplyPacket or None"
                    )
                supply.validate()
                instruction = f"{instruction}\n\nSupplied evidence:\n{supply.prompt_block}"
        decoding_params: dict[str, object] = {}
        if material.response_format is not None:
            decoding_params["response_format"] = dict(material.response_format)
        self._pending_contact_id = material.contact_id
        return AgentContactPlan(
            contact_id=material.contact_id,
            query_state_sha256=context.query_state.content_hash(),
            purpose=phase.purpose,
            instruction=instruction,
            key_representation_id=f"{self._program.program_id}:{phase.name}",
            matcher_policy_id=self._program.program_id,
            decoding_params=decoding_params,
        ).validate()

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if self._initial_dispatched or self._completed or context.contact_index != 0:
            raise RailsControllersError(
                "EvidenceAgentController.initial_contact called out of sequence"
            )
        self._initial_dispatched = True
        return self._dispatch(self._program.phases[0], context)

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: object,
    ) -> AgentLoopAdvance:
        if not isinstance(response_text, str):
            raise RailsControllersError(
                "EvidenceAgentController requires one string response per contact"
            )
        index = len(self._completed)
        if index >= len(self._program.phases):
            raise RailsControllersError(
                "EvidenceAgentController advanced past its program's phases"
            )
        phase = self._program.phases[index]
        if (
            not isinstance(contact, AgentContactPlan)
            or contact.contact_id != self._pending_contact_id
        ):
            raise RailsControllersError(
                "EvidenceAgentController.advance received an out-of-sequence contact"
            )
        response_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        artifact = AgentStateArtifact(
            state_id=f"{phase.name}:{context.sample_id}",
            state_kind=f"phase:{phase.name}",
            content=response_text,
            source_query_state_sha256=context.query_state.content_hash(),
            source_response_sha256=response_sha256,
            producer_policy_id=self._program.program_id,
            cited_value_ids=(),
        ).validate()
        self._sealed[phase.name] = artifact
        self._completed.append(phase.name)
        self._pending_contact_id = None

        is_last = index + 1 >= len(self._program.phases)
        should_stop = is_last
        if (
            not should_stop
            and self._program.stop_rule == "stop-policy-optional-early-exit"
            and self._stop_policy is not None
        ):
            should_stop = bool(self._stop_policy(context, tuple(self._completed)))

        if should_stop:
            transition = AgentStepTransition(
                snapshot_sha256=context.knowledge_snapshot_sha256,
                prior_query_state_sha256=context.query_state.content_hash(),
                next_query_state_sha256=None,
                action_kind="stop",
                action_target_refs=(),
                new_value_ids=(),
                used_value_ids=(),
                dropped_value_ids=(),
                new_agent_state_ids=(),
                dropped_agent_state_ids=(),
            ).validate()
            return AgentLoopAdvance(
                transition=transition,
                next_query_state=None,
                new_agent_states=(),
                next_contact=None,
                final_response_contact_id=contact.contact_id,
            )

        next_phase = self._program.phases[index + 1]
        next_state = QueryState(
            query_id=context.query_state.query_id,
            query_sample_id=context.query_state.query_sample_id,
            speech_packet_id=context.query_state.speech_packet_id,
            speech_packet_sha256=context.query_state.speech_packet_sha256,
            use_split_identity_hash=context.query_state.use_split_identity_hash,
            loop_step=context.query_state.loop_step + 1,
            visible_facet_ids=context.query_state.visible_facet_ids,
            agent_state_ids=context.query_state.agent_state_ids + (artifact.state_id,),
            retrieved_value_ids=context.query_state.retrieved_value_ids,
        ).validate()
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=next_state.content_hash(),
            action_kind="organize",
            action_target_refs=(f"{self._program.program_id}:{phase.name}->{next_phase.name}",),
            new_value_ids=(),
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(artifact.state_id,),
            dropped_agent_state_ids=(),
        ).validate()
        # A synthetic "as of the next contact" context: the runner itself
        # only reconstructs a fresh AgentRuntimeContext at the TOP of its
        # next trajectory iteration (rails.runner._run_agent_trajectory),
        # but the CONTACT dispatched for that iteration is whatever this
        # call returns as `next_contact` right now, built with whatever
        # context material_for_phase/supply_for_phase need. This mirrors
        # exactly what the runner's own _runtime_context would build next
        # (same ordering: state_store insertion order == query_state's own
        # declared agent_state_ids order, which we set above as
        # prior-order-then-new).
        next_context = AgentRuntimeContext(
            sample_id=context.sample_id,
            knowledge_snapshot_sha256=context.knowledge_snapshot_sha256,
            catalog_facet_ids=context.catalog_facet_ids,
            catalog_value_ids=context.catalog_value_ids,
            query_state=next_state,
            task_contract=context.task_contract,
            agent_states=context.agent_states + (artifact,),
            prior_response_sha256s=context.prior_response_sha256s + (response_sha256,),
            contact_index=context.contact_index + 1,
        )
        next_contact = self._dispatch(next_phase, next_context)
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=next_state,
            new_agent_states=(artifact,),
            next_contact=next_contact,
        )


def _default_material_for_phase(program: PhaseProgram) -> MaterialForPhase:
    """The conservative default every registered program id falls back to
    (module docstring): a generic, sample-independent instruction per phase,
    never reading any per-run injected material. Mirrors
    ``rails.kb_policy``'s own ``_default_controller_factory`` shape.

    When a phase declares a ``response_format_id`` this default cannot know
    the real schema behind that id (only a real, per-run
    ``material_for_phase`` can), so it supplies a minimal placeholder object
    schema -- just enough to keep ``EvidenceAgentController._dispatch``'s own
    "declared id present <=> material response_format present" check
    satisfied for every registered program, including
    ``phase-select-then-fill-v1``'s ``select`` phase."""

    def material_for_phase(phase_name: str, context: AgentRuntimeContext) -> PhaseMaterial:
        phase = program.phase(phase_name)
        response_format = (
            {"type": "object"} if phase.response_format_id is not None else None
        )
        return PhaseMaterial(
            instruction=(
                f"Execute the {phase.purpose} phase under the task contract "
                "already given above, grounding the decision in the speech query."
            ),
            response_format=response_format,
            contact_id=f"{program.program_id}:{phase.name}:{context.sample_id}",
            purpose=phase.purpose,
        ).validate()

    return material_for_phase


def default_controller_factory(program: PhaseProgram) -> Callable[[str], EvidenceAgentController]:
    """Build the snapshot-free, always-safe ``Callable[[str], AgentController]``
    factory registered for ``program.program_id`` at import time."""

    program.validate()
    material_for_phase = _default_material_for_phase(program)

    def factory(_sample_id: str) -> EvidenceAgentController:
        return EvidenceAgentController(program=program, material_for_phase=material_for_phase)

    return factory


_PROGRAM_CONFIG_FILENAMES: Mapping[str, str] = {
    "phase-direct-only-v1": "phase-direct-only-v1.json",
    "phase-direct-evidence-alpha-blend-v1": "phase-direct-evidence-alpha-blend-v1.json",
    "phase-select-then-fill-v1": "phase-select-then-fill-v1.json",
    "phase-draft-revise-v1": "phase-draft-revise-v1.json",
    # MF-3 / KC-S1: one slot-only contact conditioned on an already-sealed
    # intent. A single-phase program, exactly like ``phase-direct-only-v1``,
    # because the intent is NOT re-decided here -- the sealed closed-list
    # prediction is the input, so the arm spends one contact, not two.
    "phase-slots-given-intent-v1": "phase-slots-given-intent-v1.json",
}

_LOADED_PROGRAMS: dict[str, PhaseProgram] = {}


def registered_program_ids() -> tuple[str, ...]:
    """The program ids this module registers into
    ``core.base.AGENT_CONTROLLERS`` (declaration order, not registry order)."""

    return tuple(_PROGRAM_CONFIG_FILENAMES)


def default_phase_program(program_id: str) -> PhaseProgram:
    """The frozen :class:`PhaseProgram` this module loaded for ``program_id``
    from its ``configs/policy/phase-*.json`` fragment (cached after first
    load; the file is never re-read once registration has run)."""

    try:
        filename = _PROGRAM_CONFIG_FILENAMES[program_id]
    except KeyError:
        raise RailsControllersError(
            f"unknown phase program id {program_id!r}; registered: "
            f"{sorted(_PROGRAM_CONFIG_FILENAMES)}"
        ) from None
    if program_id not in _LOADED_PROGRAMS:
        _LOADED_PROGRAMS[program_id] = load_phase_program(
            DEFAULT_PROGRAM_CONFIG_DIR / filename
        )
    return _LOADED_PROGRAMS[program_id]


def register_phase_programs_v1() -> None:
    """Idempotently register this module's phase-program controller ids into
    the shared ``core.base.AGENT_CONTROLLERS`` registry. Safe to call more
    than once (a second import of this module, or a direct re-call from a
    test) -- a name already present is left untouched rather than raising
    ``core.base.CoreError``'s duplicate-name refusal (mirrors
    ``rails.kb_policy.register_kb_policy_v1``)."""

    # Each id is written as a literal inside its own ``register`` call so the
    # engineering-base gate (scripts/checks/engineering_base_check.py) can
    # read the registered name set from source without importing the package.
    registered = AGENT_CONTROLLERS.names()
    if "phase-direct-only-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-direct-only-v1",
            default_controller_factory(default_phase_program("phase-direct-only-v1")),
        )
    if "phase-direct-evidence-alpha-blend-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-direct-evidence-alpha-blend-v1",
            default_controller_factory(
                default_phase_program("phase-direct-evidence-alpha-blend-v1")
            ),
        )
    if "phase-select-then-fill-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-select-then-fill-v1",
            default_controller_factory(default_phase_program("phase-select-then-fill-v1")),
        )
    if "phase-draft-revise-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-draft-revise-v1",
            default_controller_factory(default_phase_program("phase-draft-revise-v1")),
        )
    if "phase-slots-given-intent-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-slots-given-intent-v1",
            default_controller_factory(
                default_phase_program("phase-slots-given-intent-v1")
            ),
        )
    unregistered = set(_PROGRAM_CONFIG_FILENAMES) - set(AGENT_CONTROLLERS.names())
    if unregistered:
        raise RailsControllersError(
            f"phase program ids without a literal registration: {sorted(unregistered)}"
        )


register_phase_programs_v1()


__all__ = [
    "DEFAULT_PROGRAM_CONFIG_DIR",
    "PHASE_KNOWLEDGE_KINDS",
    "PHASE_PROGRAM_SCHEMA",
    "PHASE_PROGRAM_STOP_RULES",
    "EvidenceAgentController",
    "MaterialForPhase",
    "PhaseProgram",
    "PhaseSpec",
    "RailsControllersError",
    "StopPolicy",
    "SupplyForPhase",
    "default_controller_factory",
    "default_phase_program",
    "load_phase_program",
    "register_phase_programs_v1",
    "registered_program_ids",
]
