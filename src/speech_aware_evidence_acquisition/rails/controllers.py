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
  barrier), ``phase-slots-given-intent-v1`` (one slot-extraction contact
  conditioned on an already-sealed intent), and
  ``phase-slots-given-intent-supplied-v1`` (the same contact, with its phase
  declaring ``knowledge: "supplied"`` so a baseline fragment may hand it
  retrieved values).
* :class:`EvidenceAgentController` -- one ``AgentController`` (the
  ``rails.runner.AgentController`` Protocol) that walks a ``PhaseProgram``'s
  phases in order, one contact per phase. Per-phase content (the actual
  instruction text, and an optional response format) is never hard-coded
  here: it comes from a caller-injected ``material_for_phase`` callable
  returning a :class:`~.material.PhaseMaterial`. An optional
  ``supply_for_phase`` callable may return a :class:`PhaseSupply` for the
  NEXT phase -- a hash-bound ``RankResult``/``FusionDecision`` pair, never
  prompt text -- which this controller turns into an ``acquire`` transition
  and a successor ``QueryState`` carrying the selected value ids (E6,
  2026-09-06; see "Traced supply" below). This module never ranks or fuses
  evidence itself. An
  optional ``stop_policy`` callable lets a non-final phase decide to stop
  early instead of continuing to the next phase (used by
  ``phase-direct-evidence-alpha-blend-v1``: a caller-injected policy mirrors
  ``KbAlphaBlendController``'s own "the direct-decode label already wins,
  skip the evidence contact" shortcut, without this module re-implementing
  that ranking/fusion decision). An optional ``review_for_phase`` callable
  is the Reviewer seat of the four-agent loop (owner Decision 11-B change #1,
  2026-09-08): after each phase's response is sealed it hands the sealed
  bytes to that phase's registered judges and records their
  ``core.base.JudgeVerdict`` tuple. It steers nothing -- see "Criticism only"
  below -- and ``rails.phase_review`` builds it from a baseline fragment's
  ``phase_review`` block.

Criticism only (owner Decision 11-C, 2026-09-08)
-------------------------------------------------

**A judge SCORES and FLAGS; it never proposes a revision.** The verdicts
``review_for_phase`` returns are recorded on the controller and traced by
``rails.phase_review``; not one byte this controller sends depends on them.
The transition, the successor ``QueryState`` and the next contact are
identical whether ``review_for_phase`` is ``None`` or returns a hundred
flags, which is precisely what makes a judge's admission receipt one config
key against its null arm instead of a second code path. Acting on a flag
(the design's ``on_flag: "loop"``) needs ``rails.runner``'s state-id and
contact-id rails relaxed first, and is refused by name until then.

Traced supply (E6, 2026-09-06)
-----------------------------

Before E6 a ``SupplyPacket`` returned by ``supply_for_phase`` was folded as
TEXT into the next phase's ``AgentContactPlan.instruction``. That was the
defect the KU-S1 verdict measured
(``docs/readiness/2026-09-05-slurp-consumption-ku-s1-v1-verdict.md`` section
6): ``rails.runner._assert_agent_control_excludes_knowledge_payloads`` reads
exactly ``plan.instruction``, a ``KbFacetProvider`` packet renders
``KnowledgeValue.content`` verbatim, and 11,514 of 11,514 SLURP values are
at or over the 8-character protected-material floor -- so every
knowledge-supplying phase cell was illegal by construction, on 100 % of
rows. The fold is GONE; there is no fallback and no flag to bring it back.

What replaces it: ``supply_for_phase(next_phase_name, context)`` returns a
:class:`PhaseSupply` (or ``None``). This controller then emits, on the SAME
wave that seals the completed phase's response, one ``action_kind="acquire"``
transition carrying that ``RankResult``/``FusionDecision`` pair -- the same
record shapes ``rails.kb_policy.KbAlphaBlendController._advance_after_direct``
emits, so traces of the two are directly comparable -- and a successor
``QueryState`` whose ``retrieved_value_ids`` (and, when the decision is
facet-bearing, ``visible_facet_ids``) grow by exactly that decision.
``rails.runner._agent_messages`` then renders those snapshot entries as
TYPED CONTENT BLOCKS carrying ``evidence_id`` / ``source_uri`` /
``knowledge_role``, validated by
``rails.knowledge.assert_knowledge_use_binding``, and the containment rule
does not read them precisely because they are traced.

The consequence worth stating twice: **a phase's instruction text is
byte-identical whether or not that phase is supplied.** The supply reaches
the model only through the frozen snapshot entries the successor
``QueryState`` names; a :class:`PhaseSupply`'s optional ``packet`` is
observational provenance and its ``prompt_block`` never reaches a request.

A transition between two of this controller's phases is therefore
``"acquire"`` when a supply decision was made and ``"organize"`` otherwise;
either way it seals the completed phase's raw response as one hash-bound
:class:`~.knowledge.AgentStateArtifact` and carries it forward on the
successor ``QueryState.agent_state_ids``, exactly the discipline
``rails.runner._validate_new_agent_states``/``assert_agent_step_binding``
already enforce for every other controller in this study.

The FIRST phase of a program cannot be supplied by this seam: there is no
``advance`` before it, so there is no wave on which to emit an acquire
transition. A one-phase supplied cell (KU-A1) seeds its values into the
initial ``QueryState`` instead, per sample, through
``rails.runner.run_speech_native_agent_loop``'s ``bootstrap_value_ids``
seam; ``core.flight.FlightRuntime`` resolves both from the same
``phase_supply`` config key and says which route a phase took in its
receipt.

Registration mirrors ``rails.kb_policy.register_kb_policy_v1``: every
program id is registered into the shared ``core.base.AGENT_CONTROLLERS``
registry at import time, with a snapshot-free, always-safe default factory
(a controller whose ``material_for_phase`` synthesizes a generic instruction
per phase rather than reading any per-run injected material) -- the same
"maximally conservative default" shape ``kb_policy``'s own module docstring
describes. A real flight builds its OWN richer ``material_for_phase`` (and
optionally ``supply_for_phase``/``stop_policy``/``review_for_phase``) and
passes a fresh
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

from ..core.base import AGENT_CONTROLLERS, RESPONSE_FORMATS, JudgeVerdict
from ..core.frozen_historical import frozen_agent_controller
from .errors import RailsError
from .knowledge import (
    AgentStateArtifact,
    AgentStepTransition,
    FusionDecision,
    QueryState,
    RankResult,
)
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


@dataclass(frozen=True)
class PhaseSupply:
    """One phase's TRACED knowledge-supply decision (module docstring,
    "Traced supply").

    ``rank_result``/``fusion_decision`` are the hash-bound pair
    ``rails.runner._validate_agent_knowledge_decision`` requires of every
    ``acquire`` transition; both must be bound to the snapshot and to the
    ``QueryState`` of the contact that just completed (the controller passes
    exactly that state, so a supply callable computing them from
    ``context.query_state`` is correct by construction).

    ``packet`` is OBSERVATIONAL provenance only -- what a
    ``rails.knowledge_provider.KnowledgeProvider.materialize`` produced for
    this decision. Its ``prompt_block`` never reaches a request: the values
    that reach the model are exactly ``fusion_decision.selected_value_ids``,
    rendered from the frozen snapshot by
    ``rails.runner._agent_messages`` as typed content blocks.

    ``expose_facets`` promotes the decision's newly supporting facets into
    the successor ``QueryState.visible_facet_ids`` (rendered as
    ``knowledge_role="key"`` blocks). A decision that selects NO values is
    facet-only acquisition and always exposes them --
    ``rails.runner._validate_agent_knowledge_decision`` requires it.

    ``retain_prior`` is the supply-side realisation of a
    ``"stop-policy-optional-early-exit"`` program's early exit: the
    retrieval decision itself says the completed phase's own answer already
    stands, so no further contact is spent (this is
    ``KbAlphaBlendController``'s retain-primary shortcut, expressed on the
    base). It is refused on an ``"always-run-full-program"`` program.
    """

    rank_result: RankResult
    fusion_decision: FusionDecision
    packet: SupplyPacket | None = None
    expose_facets: bool = False
    retain_prior: bool = False
    action_target_ref: str = "phase-supply-v1:recall-rank-fuse"

    def validate(self) -> "PhaseSupply":
        if not isinstance(self.rank_result, RankResult):
            raise RailsControllersError("PhaseSupply.rank_result must be a RankResult")
        if not isinstance(self.fusion_decision, FusionDecision):
            raise RailsControllersError(
                "PhaseSupply.fusion_decision must be a FusionDecision"
            )
        self.rank_result.validate()
        self.fusion_decision.validate()
        if self.packet is not None:
            if not isinstance(self.packet, SupplyPacket):
                raise RailsControllersError(
                    "PhaseSupply.packet must be a SupplyPacket or None"
                )
            self.packet.validate()
        for name in ("expose_facets", "retain_prior"):
            if not isinstance(getattr(self, name), bool):
                raise RailsControllersError(f"PhaseSupply.{name} must be a bool")
        _require_nonempty_str(
            self.action_target_ref, field="PhaseSupply.action_target_ref"
        )
        return self


MaterialForPhase = Callable[[str, AgentRuntimeContext], PhaseMaterial]
SupplyForPhase = Callable[[str, AgentRuntimeContext], "PhaseSupply | None"]
StopPolicy = Callable[[AgentRuntimeContext, Sequence[str]], bool]
#: The Reviewer seat (owner Decision 11-B change #1 / 11-C, 2026-09-08):
#: ``review_for_phase(completed_phase_name, context, response_text)`` returns
#: the judges' :class:`~..core.base.JudgeVerdict` tuple for the phase that
#: just answered. ``rails.phase_review.build_review_for_phase`` builds one
#: from config; ``None`` is today's behaviour, unchanged.
ReviewForPhase = Callable[
    [str, AgentRuntimeContext, str], Sequence["JudgeVerdict"]
]


class EvidenceAgentController:
    """One generic ``rails.runner.AgentController`` walking a
    :class:`PhaseProgram` phase-by-phase (module docstring).

    ``material_for_phase(phase_name, context)`` must return a validated
    :class:`~.material.PhaseMaterial`; its ``response_format`` presence must
    agree with the phase's own declared ``response_format_id`` (both
    present, or both absent). ``supply_for_phase(next_phase_name, context)``,
    when given, may return a :class:`PhaseSupply` naming the frozen-snapshot
    values the NEXT phase should see; they travel the successor
    ``QueryState``, never the instruction (module docstring, "Traced
    supply"). ``stop_policy`` is consulted only for a
    program whose ``stop_rule`` is ``"stop-policy-optional-early-exit"``,
    only after a NON-FINAL phase, with the tuple of phase names completed so
    far; returning ``True`` stops the program on that phase's own response.

    ``review_for_phase(completed_phase_name, context, response_text)`` is the
    Reviewer seat (owner Decision 11-B change #1, 2026-09-08). It is called
    once per phase, AFTER that phase's response is sealed as an
    :class:`~.knowledge.AgentStateArtifact` and BEFORE the stop decision, with
    a context carrying the just-sealed state and the UNCHANGED
    ``query_state`` -- the same synthetic context ``supply_for_phase``
    receives, for the same reason. It returns a sequence of
    ``core.base.JudgeVerdict``; this controller type-checks and records them
    and does nothing else with them.

    **Nothing this controller sends depends on a verdict.** Owner Decision
    11-C: a judge SCORES and FLAGS and never proposes a revision, so the
    verdicts are criticism, not control. The transition, the successor
    ``QueryState`` and the next contact are byte-identical whether
    ``review_for_phase`` is ``None`` or returns a hundred flags -- which is
    what lets a judge's admission receipt be one config key against its null
    arm rather than a second code path. Acting on a flag (the design's
    ``on_flag: "loop"``) is a change to ``rails.runner``'s state-id and
    contact-id rails, refused by name in ``rails.phase_review`` until that
    lands.

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
        review_for_phase: ReviewForPhase | None = None,
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
        if review_for_phase is not None and not callable(review_for_phase):
            raise RailsControllersError(
                "EvidenceAgentController review_for_phase must be callable or None"
            )
        self._program = program
        self._material_for_phase = material_for_phase
        self._supply_for_phase = supply_for_phase
        self._stop_policy = stop_policy
        self._review_for_phase = review_for_phase
        self._sealed: dict[str, AgentStateArtifact] = {}
        self._reviews: dict[str, tuple[JudgeVerdict, ...]] = {}
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

    @property
    def review_verdicts(self) -> Mapping[str, tuple[JudgeVerdict, ...]]:
        """This sample's own judge verdicts so far, keyed by phase name.

        Observability only, exactly like :attr:`sealed_states`: the runner
        never consults it, and nothing this controller sends depends on it
        (owner Decision 11-C -- the Reviewer criticises, it does not steer).
        Empty for every controller built without ``review_for_phase``.
        """

        return dict(self._reviews)

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
        # E6: the instruction is the phase material's text and NOTHING
        # else. Supply never rides the control turn (module docstring,
        # "Traced supply"); it travels the successor QueryState. A supplied
        # phase's control-turn bytes are therefore identical to the same
        # phase's unsupplied bytes -- the property the containment rule and
        # every paired contrast both depend on.
        instruction = material.instruction
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

        # The Reviewer seat (owner Decision 11-B change #1, 2026-09-08): the
        # judges read the phase's SEALED bytes, here, before the stop
        # decision and before any supply decision -- so a verdict is about
        # the answer that was actually given, and every judge of every
        # reviewed phase runs exactly once per row. Criticism only: what
        # comes back is recorded and steers nothing (class docstring).
        self._resolve_review(phase, context, response_text, artifact, response_sha256)

        is_last = index + 1 >= len(self._program.phases)
        should_stop = is_last
        if (
            not should_stop
            and self._program.stop_rule == "stop-policy-optional-early-exit"
            and self._stop_policy is not None
        ):
            should_stop = bool(self._stop_policy(context, tuple(self._completed)))

        # E6: the supply decision for the NEXT phase is taken HERE, on the
        # wave that just completed, because that is the only wave whose
        # transition can carry it (module docstring, "Traced supply"). The
        # context it sees carries this phase's just-sealed state but the
        # PRIOR QueryState -- the state the RankResult/FusionDecision must
        # be bound to (rails.runner._validate_agent_knowledge_decision
        # validates them against exactly that state).
        supply: PhaseSupply | None = None
        if not should_stop:
            supply = self._resolve_supply(
                self._program.phases[index + 1],
                context,
                artifact,
                response_sha256,
            )
            if supply is not None and supply.retain_prior:
                if self._program.stop_rule != "stop-policy-optional-early-exit":
                    raise RailsControllersError(
                        f"phase supply for {self._program.phases[index + 1].name!r} "
                        "asked to retain the prior phase's answer, but program "
                        f"{self._program.program_id!r} declares stop_rule "
                        f"{self._program.stop_rule!r}; an early exit is legal only "
                        "under 'stop-policy-optional-early-exit'"
                    )
                should_stop = True
                supply = None

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
        new_value_ids: tuple[str, ...] = ()
        new_facet_ids: tuple[str, ...] = ()
        action_kind = "organize"
        action_target_refs = (
            f"{self._program.program_id}:{phase.name}->{next_phase.name}",
        )
        if supply is not None:
            new_value_ids, new_facet_ids = self._acquired_ids(supply, context)
            action_kind = "acquire"
            action_target_refs = (*action_target_refs, supply.action_target_ref)

        next_state = QueryState(
            query_id=context.query_state.query_id,
            query_sample_id=context.query_state.query_sample_id,
            speech_packet_id=context.query_state.speech_packet_id,
            speech_packet_sha256=context.query_state.speech_packet_sha256,
            use_split_identity_hash=context.query_state.use_split_identity_hash,
            loop_step=context.query_state.loop_step + 1,
            visible_facet_ids=(
                context.query_state.visible_facet_ids + new_facet_ids
            ),
            agent_state_ids=context.query_state.agent_state_ids + (artifact.state_id,),
            retrieved_value_ids=(
                context.query_state.retrieved_value_ids + new_value_ids
            ),
        ).validate()
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=next_state.content_hash(),
            action_kind=action_kind,
            action_target_refs=action_target_refs,
            new_value_ids=new_value_ids,
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(artifact.state_id,),
            dropped_agent_state_ids=(),
            new_facet_ids=new_facet_ids,
        ).validate()
        # A synthetic "as of the next contact" context: the runner itself
        # only reconstructs a fresh AgentRuntimeContext at the TOP of its
        # next trajectory iteration (rails.runner._run_agent_trajectory),
        # but the CONTACT dispatched for that iteration is whatever this
        # call returns as `next_contact` right now, built with whatever
        # context material_for_phase needs. This mirrors
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
            rank_result=None if supply is None else supply.rank_result,
            fusion_decision=None if supply is None else supply.fusion_decision,
        )

    def _review_context(
        self,
        context: AgentRuntimeContext,
        artifact: AgentStateArtifact,
        response_sha256: str,
    ) -> AgentRuntimeContext:
        """The "as of the answer just sealed" context both the Reviewer and
        the supply decision see: this phase's own state appended, the
        ``query_state`` UNCHANGED (a decision or a criticism is about the
        state that produced the answer, not about its successor)."""

        return AgentRuntimeContext(
            sample_id=context.sample_id,
            knowledge_snapshot_sha256=context.knowledge_snapshot_sha256,
            catalog_facet_ids=context.catalog_facet_ids,
            catalog_value_ids=context.catalog_value_ids,
            query_state=context.query_state,
            task_contract=context.task_contract,
            agent_states=context.agent_states + (artifact,),
            prior_response_sha256s=(
                context.prior_response_sha256s + (response_sha256,)
            ),
            contact_index=context.contact_index,
        )

    def _resolve_review(
        self,
        phase: PhaseSpec,
        context: AgentRuntimeContext,
        response_text: str,
        artifact: AgentStateArtifact,
        response_sha256: str,
    ) -> tuple[JudgeVerdict, ...]:
        """Call ``review_for_phase`` for the phase that just answered and
        type-check what comes back.

        Fail-closed on anything that is not a sequence of validated
        ``core.base.JudgeVerdict``: a judge that returns a string, a mapping
        or a rewritten draft is exactly the Decision 11-C violation the
        verdict type exists to make unrepresentable, and a controller that
        quietly accepted it would reopen the ruling in the one place nobody
        reads.
        """

        if self._review_for_phase is None:
            return ()
        verdicts = self._review_for_phase(
            phase.name,
            self._review_context(context, artifact, response_sha256),
            response_text,
        )
        if verdicts is None:
            verdicts = ()
        if isinstance(verdicts, (str, bytes, Mapping)) or not isinstance(
            verdicts, Sequence
        ):
            raise RailsControllersError(
                "review_for_phase must return a sequence of core.base.JudgeVerdict, "
                f"got {type(verdicts).__name__}"
            )
        recorded: list[JudgeVerdict] = []
        for verdict in verdicts:
            if not isinstance(verdict, JudgeVerdict):
                raise RailsControllersError(
                    "review_for_phase entries must be core.base.JudgeVerdict; a judge "
                    "scores and flags and never proposes a revision (owner Decision "
                    "11-C)"
                )
            verdict.validate()
            recorded.append(verdict)
        self._reviews[phase.name] = tuple(recorded)
        return tuple(recorded)

    def _resolve_supply(
        self,
        next_phase: PhaseSpec,
        context: AgentRuntimeContext,
        artifact: AgentStateArtifact,
        response_sha256: str,
    ) -> "PhaseSupply | None":
        """Call ``supply_for_phase`` for ``next_phase`` and type-check it.

        The context handed on carries the just-sealed state (so a decision
        may read the phase's own answer, exactly as
        ``KbAlphaBlendController`` reads its direct-decode response) but the
        UNCHANGED ``query_state``: a ``RankResult``/``FusionDecision`` must
        be bound to the state of the contact that produced the answer.
        """

        if self._supply_for_phase is None:
            return None
        supply = self._supply_for_phase(
            next_phase.name,
            self._review_context(context, artifact, response_sha256),
        )
        if supply is None:
            return None
        if isinstance(supply, SupplyPacket):
            raise RailsControllersError(
                "supply_for_phase returned a bare SupplyPacket; the "
                "fold-a-packet-into-the-instruction path was removed in E6 "
                "(2026-09-06) because it put frozen knowledge payloads on the "
                "CONTROL turn. Return a PhaseSupply carrying the decision's "
                "RankResult/FusionDecision instead, so the values travel the "
                "traced typed-content channel"
            )
        if not isinstance(supply, PhaseSupply):
            raise RailsControllersError(
                "supply_for_phase must return a PhaseSupply or None"
            )
        supply.validate()
        if next_phase.knowledge != "supplied":
            raise RailsControllersError(
                f"phase {next_phase.name!r} declares knowledge="
                f"{next_phase.knowledge!r} but supply_for_phase returned a decision "
                "for it; a supplied phase must say so in its PhaseSpec"
            )
        return supply

    @staticmethod
    def _acquired_ids(
        supply: "PhaseSupply", context: AgentRuntimeContext
    ) -> tuple[tuple[str, ...], tuple[str, ...]]:
        """``(new_value_ids, new_facet_ids)`` for one supply decision.

        Both are computed HERE from the ``FusionDecision`` rather than taken
        from the caller, so the transition this controller emits satisfies
        ``rails.runner._validate_agent_knowledge_decision`` by construction:
        ``new_value_ids`` IS ``fusion_decision.selected_value_ids`` (exact
        tuple equality is required), and ``new_facet_ids`` is a subset of
        the decision's NEWLY supporting facets -- the whole of it when the
        decision selects no values at all, which the runner demands of
        facet-only acquisition.
        """

        visible_values = set(context.query_state.retrieved_value_ids)
        selected = tuple(supply.fusion_decision.selected_value_ids)
        repeated = [value_id for value_id in selected if value_id in visible_values]
        if repeated:
            raise RailsControllersError(
                "phase supply selected values already visible in this trajectory: "
                f"{sorted(set(repeated))}; a FusionDecision must exclude "
                "QueryState.retrieved_value_ids (rails.kb_policy's own fuser does)"
            )
        visible_facets = set(context.query_state.visible_facet_ids)
        newly_supporting = tuple(
            facet_id
            for facet_id in supply.fusion_decision.supporting_facet_ids
            if facet_id not in visible_facets
        )
        expose = supply.expose_facets or not selected
        return selected, (newly_supporting if expose else ())



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
    # KU-S3, 2026-09-07: the same one-contact slot program with its single
    # phase declaring ``knowledge: "supplied"``, which is what
    # ``rails.phase_supply.load_phase_supply_specs`` requires before a
    # baseline fragment may supply it. Two program ids rather than a flag on
    # one, because the phase's ``knowledge`` value rides the config hash and
    # is part of what the cell IS -- KC-S1b and KU-S3 must never be able to
    # resolve to the same program object.
    "phase-slots-given-intent-supplied-v1": (
        "phase-slots-given-intent-supplied-v1.json"
    ),
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
    if "phase-slots-given-intent-supplied-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-slots-given-intent-supplied-v1",
            default_controller_factory(
                default_phase_program("phase-slots-given-intent-supplied-v1")
            ),
        )
    unregistered = set(_PROGRAM_CONFIG_FILENAMES) - set(AGENT_CONTROLLERS.names())
    if unregistered:
        raise RailsControllersError(
            f"phase program ids without a literal registration: {sorted(unregistered)}"
        )


register_phase_programs_v1()


# --- WAVE R7: the two frozen-historical controller_policy_id values ---------
#
# ``configs/experiment/a2t-g5-exhaustive-family-fixed16-v1.json`` and its G6
# sibling declare ``frozen_components.controller_policy_id``, which
# scripts/checks/engineering_base_check.py resolves in AGENT_CONTROLLERS (not
# in POLICIES, where the same two ids also appear as the baseline fragment's
# ``policy``). Both sealed cells flew from a rails/probes launcher whose
# controller class is one of the 33 out-of-base controllers the September audit
# retired; neither id has, or should have, a live controller factory.
#
# They register as ``core.base.FrozenHistoricalComponent`` for the same reason
# and with the same discipline as their POLICIES twins in core/policies.py: the
# name RESOLVES so the base accounts for it, and every use REFUSES with the
# sealed receipt's path. See core/frozen_historical.py.


def register_frozen_historical_controllers_r7() -> None:
    """Idempotently register the two retired A2T ``controller_policy_id``
    values as frozen-historical entries (never as runnable factories)."""

    registered = AGENT_CONTROLLERS.names()
    if "saea-a2t-g5-plan-compile-execute-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "saea-a2t-g5-plan-compile-execute-v1",
            frozen_agent_controller("saea-a2t-g5-plan-compile-execute-v1"),
        )
    if "saea-a2t-g6-exhaustive-family-sweep-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "saea-a2t-g6-exhaustive-family-sweep-v1",
            frozen_agent_controller("saea-a2t-g6-exhaustive-family-sweep-v1"),
        )


register_frozen_historical_controllers_r7()


# -- registered response formats (E1, 2026-09-05) -----------------------------
#
# ``PhaseSpec.response_format_id`` has always been a config-declared name;
# nothing resolved it, so every phase that wanted a real structured-output
# schema had to be handed one by a launcher. These two entries close that
# seam for the Audio2Tool select-then-fill program. Both are
# ``(lock, root, **params) -> Mapping`` thunks over the pinned
# ``tools_registry.csv``, exactly the shape ``core.base.INSTRUCTION_FILLS``
# entries use, because a 152-tool JSON schema is far too large to live in a
# config fragment. They register HERE, in the controllers module, because
# ``scripts/checks/engineering_base_check.py`` names this file as one of the
# canonical registration sites and a registry populated from anywhere else
# is exactly the fragmentation that check exists to catch.


def _a2t_registry_rows(lock: Mapping[str, object], root: Path):
    from ..data.audio2tool import load_tool_registry  # noqa: PLC0415 (import cost)

    return load_tool_registry(lock, root)


def select_response_format_v1(
    lock: Mapping[str, object], root: Path, **params: object
) -> Mapping[str, object]:
    """``rails.a2t_response_schema.audio2tool_selection_response_format`` over
    the WHOLE pinned registry: an array of exact tool-name objects, no
    argument field at all -- the SELECT phase's output contract. ``params``
    (``schema_name``, ``min_calls``, ``max_calls``) come from the baseline
    fragment's ``phase_material.<phase>.fill_params`` and default to the
    schema builder's own defaults; ``candidate_tool_names`` defaults to every
    registered tool name in sorted order, so the phase is unconditioned on
    any per-sample retrieval."""

    from .a2t_response_schema import (  # noqa: PLC0415 (import cost)
        audio2tool_selection_response_format,
    )

    rows = _a2t_registry_rows(lock, root)
    candidates = tuple(sorted({str(row["tool_name"]) for row in rows}))
    return audio2tool_selection_response_format(rows, candidates, **params)


def fill_response_format_v1(
    lock: Mapping[str, object], root: Path, **params: object
) -> Mapping[str, object]:
    """``rails.a2t_response_schema.audio2tool_outer_call_array_response_format``
    over the whole pinned registry: the documented ``[{name, arguments}]``
    envelope with an exact tool-name enum and a deliberately open
    ``arguments`` object -- the FILL phase's output contract.

    Why not ``audio2tool_locked_call_array_response_format``, which locks the
    exact occurrence list: that schema is a function of ONE sample's SELECT
    answer, so it cannot be a phase-level, sample-independent format at all.
    A per-sample response format is a different seam (the phase material
    would have to carry one schema per sample) and is deliberately out of
    scope here; this entry is the strongest format that is genuinely static
    for the phase.
    """

    from .a2t_response_schema import (  # noqa: PLC0415 (import cost)
        audio2tool_outer_call_array_response_format,
    )

    return audio2tool_outer_call_array_response_format(
        _a2t_registry_rows(lock, root), **params
    )


def register_response_formats_v1() -> None:
    """Idempotently register the E1 response-format ids into the shared
    ``core.base.RESPONSE_FORMATS`` registry (same shape and same
    re-entrancy discipline as :func:`register_phase_programs_v1`)."""

    registered = RESPONSE_FORMATS.names()
    # Each id is a literal inside its own ``register`` call so the
    # engineering-base gate can read the registered name set from source
    # without importing the package.
    if "select-response-v1" not in registered:
        RESPONSE_FORMATS.register("select-response-v1", select_response_format_v1)
    if "fill-response-v1" not in registered:
        RESPONSE_FORMATS.register("fill-response-v1", fill_response_format_v1)


register_response_formats_v1()


__all__ = [
    "DEFAULT_PROGRAM_CONFIG_DIR",
    "PHASE_KNOWLEDGE_KINDS",
    "PHASE_PROGRAM_SCHEMA",
    "PHASE_PROGRAM_STOP_RULES",
    "EvidenceAgentController",
    "MaterialForPhase",
    "PhaseProgram",
    "PhaseSpec",
    "PhaseSupply",
    "RailsControllersError",
    "ReviewForPhase",
    "StopPolicy",
    "SupplyForPhase",
    "default_controller_factory",
    "default_phase_program",
    "fill_response_format_v1",
    "load_phase_program",
    "register_phase_programs_v1",
    "register_response_formats_v1",
    "registered_program_ids",
    "select_response_format_v1",
]
