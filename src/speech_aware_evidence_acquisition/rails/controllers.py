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
  ``core.base.JudgeVerdict`` tuple. It supplies criticism to an explicitly configured Planner -- see
  "Criticism and explicit control" below -- and ``rails.phase_review`` builds it from a baseline fragment's
  ``phase_review`` block.

Criticism and explicit control (owner Decision 11-C and later continuation)
-------------------------------------------------

**A judge SCORES and FLAGS; it never proposes a revision.** Review alone
records criticism. Without a configured stop policy, review flags do not
change the transition, successor QueryState, or next contact. The optional
bounded phase Planner may use those flags to choose continuation; the
Reviewer never acquires answer authority. The separate task-action bridge
returns source-bound tool state and optional knowledge supply to the same
controller. Both behaviors require explicit configuration.

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
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ..core.base import (
    AGENT_CONTROLLERS,
    PHASE_STATE_VIEWS,
    RESPONSE_FORMATS,
    JudgeVerdict,
)
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
from .core_client import CoreCompletion, FrozenCoreClientError
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
    {"always-run-full-program", "stop-policy-optional-early-exit", "native-answer-or-tool", "native-role-episode"}
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
        # A native-role-episode graph may configure Reviewer and Planner to
        # 0 iterations (the review loop off, E1); those two phases are then
        # never contacted, so the floor every other stop rule keeps --
        # "one contact per phase, at minimum" -- no longer holds. Perception
        # and Solver are always positive (rails.native_episode_config), so 2
        # is this stop rule's own true structural minimum; every other stop
        # rule keeps its unchanged, unmoved len(phases) floor.
        if self.stop_rule == "native-role-episode":
            if (
                isinstance(self.max_contacts, bool)
                or not isinstance(self.max_contacts, int)
                or self.max_contacts < 2
            ):
                raise RailsControllersError(
                    "PhaseProgram.max_contacts must be an int >= 2 for a "
                    "native-role-episode program"
                )
        elif (
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


@dataclass(frozen=True)
class PhaseToolStep:
    """One executed task action and its returned source-bound state."""

    supply: PhaseSupply | None
    state: AgentStateArtifact

    def validate(self):
        if self.supply is not None:
            self.supply.validate()
        if not isinstance(self.state, AgentStateArtifact):
            raise RailsControllersError("tool action must return AgentStateArtifact")
        self.state.validate()
        if self.state.state_kind != "tool-result":
            raise RailsControllersError("tool action state must have kind tool-result")
        return self


ToolsForPhase = Callable[[str, str, AgentRuntimeContext], "PhaseToolStep | None"]


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
#: WAVE R7 (owner Decision 12-F, 2026-09-08): a phase's KNOWLEDGE VIEW of its
#: own answer. ``state_view_for_phase(phase_name, response_text) -> str``
#: returns what that phase SEALS as its :class:`~.knowledge.AgentStateArtifact`
#: content, which is also what the next phase reads. ``None`` -- the default,
#: and every caller written before R7 -- seals the raw response and is
#: byte-identical to before the seam existed.
#:
#: It exists because a retired controller
#: (``rails.a2t_hard_validity.HardValidityRepairController``) sealed a DERIVED
#: state -- a bounded, deterministic validity report over its own draft -- and
#: folding it onto this base without the seam would have changed the bytes the
#: repair contact reads. A view is a pure ``(text) -> text`` function
#: registered in ``core.base.PHASE_STATE_VIEWS``; it never reads gold, the
#: sample, or anything outside the response it is given.
StateViewForPhase = Callable[[str, str], str]
#: WAVE R7: a cell's own ``(key_representation_id, matcher_policy_id)``, either
#: one pair for the whole trajectory or one per phase. It exists so two arms of
#: one cell can share a phase program and still be different arms -- the G3
#: matched and shuffled arms differ in exactly the matcher id -- and so a folded
#: cell keeps the identity its sealed receipts already carry. ``None`` keeps the
#: program-derived default and is byte-identical to before the seam existed.
ContactIdentity = tuple[str, str] | Mapping[str, tuple[str, str]]


def _starts_with_textual_native_tool_call(response_text: str) -> bool:
    """Reject a native tool frame that arrived as answer text."""

    candidate = response_text.lstrip()
    if candidate.startswith("```"):
        newline = candidate.find("\n")
        if newline < 0:
            return False
        candidate = candidate[newline + 1 :].lstrip()
    prefix = "<tool_call"
    return candidate.startswith(prefix) and (
        len(candidate) == len(prefix)
        or candidate[len(prefix)] in "> \t\r\n"
    )


def seal_phase_response_state(
    *,
    phase_name: str,
    sample_id: str,
    state_content: str,
    raw_response_text: str,
    source_query_state_sha256: str,
    producer_policy_id: str,
    state_namespace: str | None = None,
    cited_value_ids: Sequence[str] = (),
) -> AgentStateArtifact:
    """Seal one phase response with distinct visible and source bytes.

    state_content is the raw response or a registered view of it.
    source_response_sha256 always binds raw_response_text so a view cannot
    obscure the model bytes from which it was derived.
    """

    state_id = (
        f"{state_namespace}:{phase_name}:{sample_id}"
        if state_namespace is not None
        else f"{phase_name}:{sample_id}"
    )
    return AgentStateArtifact(
        state_id=state_id,
        state_kind=f"phase:{phase_name}",
        content=state_content,
        source_query_state_sha256=source_query_state_sha256,
        source_response_sha256=hashlib.sha256(
            raw_response_text.encode("utf-8")
        ).hexdigest(),
        producer_policy_id=producer_policy_id,
        cited_value_ids=tuple(cited_value_ids),
    ).validate()


def advance_phase_response_state(
    *,
    context: AgentRuntimeContext,
    added_states: tuple[AgentStateArtifact, ...],
    action_target_ref: str,
    supply: PhaseSupply | None = None,
) -> tuple[QueryState, AgentStepTransition]:
    """Materialize a response/tool observation without choosing the next node.

    The sequential controller and native Workflow share these custody bytes.
    Routing and final answer selection remain with their respective executors.
    """
    new_value_ids: tuple[str, ...] = ()
    new_facet_ids: tuple[str, ...] = ()
    action_kind = "organize"
    action_target_refs = (action_target_ref,)
    if supply is not None:
        supply.validate()
        if supply.retain_prior:
            raise RailsControllersError("state materialization cannot select a final answer")
        new_value_ids, new_facet_ids = EvidenceAgentController._acquired_ids(supply, context)
        action_kind = "acquire"
        action_target_refs = (*action_target_refs, supply.action_target_ref)
    next_state = QueryState(
        query_id=context.query_state.query_id,
        query_sample_id=context.query_state.query_sample_id,
        speech_packet_id=context.query_state.speech_packet_id,
        speech_packet_sha256=context.query_state.speech_packet_sha256,
        query_source=context.query_state.query_source,
        use_split_identity_hash=context.query_state.use_split_identity_hash,
        loop_step=context.query_state.loop_step + 1,
        visible_facet_ids=context.query_state.visible_facet_ids + new_facet_ids,
        agent_state_ids=context.query_state.agent_state_ids + tuple(s.state_id for s in added_states),
        retrieved_value_ids=context.query_state.retrieved_value_ids + new_value_ids,
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
        new_agent_state_ids=tuple(s.state_id for s in added_states),
        dropped_agent_state_ids=(),
        new_facet_ids=new_facet_ids,
    ).validate()
    return next_state, transition


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

    ``state_namespace`` optionally qualifies state identities when independent
    window trajectories share one call-level sample. It changes only state ids;
    instructions, contacts and the scientific sample roster stay unchanged.

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
        state_view_for_phase: StateViewForPhase | None = None,
        contact_identity: ContactIdentity | None = None,
        state_namespace: str | None = None,
        tools_for_phase: ToolsForPhase | None = None,
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
        if state_view_for_phase is not None and not callable(state_view_for_phase):
            raise RailsControllersError(
                "EvidenceAgentController state_view_for_phase must be callable or None"
            )
        if contact_identity is not None:
            pairs = (
                list(contact_identity.values())
                if isinstance(contact_identity, Mapping)
                else [contact_identity]
            )
            if isinstance(contact_identity, Mapping):
                declared = set(contact_identity)
                phases = set(program.phase_names())
                if declared != phases:
                    raise RailsControllersError(
                        "EvidenceAgentController contact_identity, when given per "
                        f"phase, must name every phase exactly once: expected "
                        f"{sorted(phases)}, got {sorted(declared)}"
                    )
            for pair in pairs:
                if (
                    not isinstance(pair, tuple)
                    or len(pair) != 2
                    or not all(
                        isinstance(part, str) and part.strip() for part in pair
                    )
                ):
                    raise RailsControllersError(
                        "EvidenceAgentController contact_identity must be a "
                        "(key_representation_id, matcher_policy_id) pair of "
                        "non-empty strings, a per-phase mapping of them, or None"
                    )
        if state_namespace is not None and (
            not isinstance(state_namespace, str) or not state_namespace.strip()
        ):
            raise RailsControllersError("state_namespace must be a non-empty string or None")
        if tools_for_phase is not None and not callable(tools_for_phase):
            raise RailsControllersError("tools_for_phase must be callable or None")
        self._native_mode = program.stop_rule == "native-answer-or-tool"
        native_dispatcher = getattr(tools_for_phase, "native_enabled", False)
        if self._native_mode != bool(native_dispatcher):
            raise RailsControllersError(
                "native answer-or-tool program requires its native tool dispatcher"
            )
        if self._native_mode and stop_policy is not None:
            raise RailsControllersError("native model decisions cannot use an external stop policy")
        if self._native_mode and any(
            phase.response_format_id is not None or phase.barrier
            for phase in program.phases
        ):
            raise RailsControllersError(
                "native answer-or-tool phases cannot force a response format or phase barrier"
            )
        self._tools_for_phase = tools_for_phase
        self._state_namespace = state_namespace
        self._program = program
        self._material_for_phase = material_for_phase
        self._supply_for_phase = supply_for_phase
        self._stop_policy = stop_policy
        self._review_for_phase = review_for_phase
        self._state_view_for_phase = state_view_for_phase
        self._contact_identity = contact_identity
        self._contact_phases: dict[str, str] = {}
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
        tool_instruction = getattr(self._tools_for_phase, "instruction_for_phase", None)
        if callable(tool_instruction):
            extra = tool_instruction(phase.name, context)
            if extra:
                instruction = f"{instruction}\n\n{extra}"
        decoding_params: dict[str, object] = {}
        if material.response_format is not None:
            decoding_params["response_format"] = dict(material.response_format)
        if self._native_mode:
            decoding_params.update(
                tool_choice="none" if phase == self._program.phases[-1] else "auto",
                parallel_tool_calls=False,
            )
        self._pending_contact_id = material.contact_id
        # Decision 283 A: remember which program phase (node) authored each contact, so the runner can resolve a per-node
        # ``thinking_policy`` override without changing the contact plan's shape.
        self._contact_phases[material.contact_id] = phase.name
        # WAVE R7: a cell may declare its OWN key-representation / matcher
        # identity instead of the program-derived default. It exists for the
        # folds: two arms of one cell can share a phase program and still be
        # different arms (the G3 matched and shuffled arms differ in exactly
        # this string), and a receipt that collapsed them would be describing
        # one cell where there were two. ``None`` is the pre-R7 default and is
        # byte-identical to it.
        key_representation_id = f"{self._program.program_id}:{phase.name}"
        matcher_policy_id = self._program.program_id
        if isinstance(self._contact_identity, Mapping):
            key_representation_id, matcher_policy_id = self._contact_identity[phase.name]
        elif self._contact_identity is not None:
            key_representation_id, matcher_policy_id = self._contact_identity
        return AgentContactPlan(
            contact_id=material.contact_id,
            query_state_sha256=context.query_state.content_hash(),
            purpose=phase.purpose,
            instruction=instruction,
            key_representation_id=key_representation_id,
            matcher_policy_id=matcher_policy_id,
            decoding_params=decoding_params,
        ).validate()

    def phase_name_for_contact(self, contact_id: str) -> str | None:
        """The program phase (node id) that authored ``contact_id``, or None for a contact this controller never dispatched."""

        return self._contact_phases.get(contact_id)

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if self._initial_dispatched or self._completed or context.contact_index != 0:
            raise RailsControllersError(
                "EvidenceAgentController.initial_contact called out of sequence"
            )
        if self._program.stop_rule == "native-role-episode":
            raise RailsControllersError("native-role-episode requires the OpenJiuwen episode binding")
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
        native_requested = False
        if self._native_mode:
            if (
                len(context.core_completions) != 1
                or not isinstance(context.core_completions[0], CoreCompletion)
                or contact.query_state_sha256 != context.query_state.content_hash()
            ):
                raise RailsControllersError("native completion binding is missing or stale")
            completion = context.core_completions[0]
            try:
                completion.assert_binding(
                    sample_id=context.sample_id, agent_contact_id=contact.contact_id,
                    response_text=response_text,
                )
            except FrozenCoreClientError as error:
                raise RailsControllersError(f"native completion binding refused: {error}") from error
            raw_calls = completion.tool_calls
            native_requested = raw_calls is not None and raw_calls != []
            if (
                not native_requested
                and _starts_with_textual_native_tool_call(response_text)
            ):
                raise RailsControllersError(
                    "textual native tool frame cannot be accepted as an answer"
                )
            if index + 1 == len(self._program.phases) and native_requested:
                raise RailsControllersError("final answer contact returned a native tool request")
        response_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        # WAVE R7: what this phase SEALS may be a registered VIEW of the raw
        # response rather than the raw response itself (class docstring,
        # "Knowledge views"). source_response_sha256 continues to hash the
        # RAW response through the shared pure sealer.
        state_content = self._resolve_state_view(phase, response_text)
        state_namespace = self._state_namespace
        if context.execution_unit_id is not None:
            from .execution_units import execution_unit_scope

            scope = execution_unit_scope(context.execution_unit_id)
            state_namespace = scope if state_namespace is None else scope + "/" + state_namespace
            if state_content == "" and response_text == "":
                # Record absence as state metadata while retaining empty answer
                # bytes and their raw source hash for terminal delivery.
                state_content = '{"schema":"saea-empty-phase-response-v1","response_text":""}'
        if (
            state_content == "" and response_text == ""
            and not self._native_mode and index + 1 >= len(self._program.phases)
        ):
            # Owner decision 199 (empty is legal) at the direct-only boundary: a
            # final non-native phase whose frozen core delivered no content (a
            # thinking core that spent its whole completion budget on reasoning
            # leaves ``message.content`` empty) seals the same explicit empty
            # marker the execution-unit branch above uses, and the row delivers
            # the empty answer bytes. The runner receipts the contact first
            # (``saea-empty-completion-v1``); this branch only keeps the seal
            # from raising. Added for a response that previously raised, so no
            # flown cell's bytes move.
            state_content = '{"schema":"saea-empty-phase-response-v1","response_text":""}'
        artifact = seal_phase_response_state(
            phase_name=phase.name,
            sample_id=context.sample_id,
            state_content=state_content,
            raw_response_text=response_text,
            source_query_state_sha256=context.query_state.content_hash(),
            producer_policy_id=self._program.program_id,
            state_namespace=state_namespace,
            cited_value_ids=(),
        )
        self._sealed[phase.name] = artifact
        self._completed.append(phase.name)
        self._pending_contact_id = None

        # The Reviewer seat (owner Decision 11-B change #1, 2026-09-08): the
        # judges read the phase's SEALED bytes, here, before the stop
        # decision and before any supply decision -- so a verdict is about
        # the answer that was actually given, and every judge of every
        # reviewed phase runs exactly once per row. Criticism only: what
        # comes back is recorded and steers nothing (class docstring).
        staged = self._review_context(context, artifact, response_sha256)
        self._resolve_review(phase, staged, response_text)

        is_last = index + 1 >= len(self._program.phases)
        should_stop = not native_requested if self._native_mode else is_last
        if (
            not should_stop
            and self._program.stop_rule == "stop-policy-optional-early-exit"
            and self._stop_policy is not None
        ):
            # WAVE R7: the stop policy sees the STAGED context -- this phase's
            # own just-sealed state appended, the query_state unchanged -- the
            # same context ``supply_for_phase`` and the Reviewer already
            # receive. It is a strict superset of what it saw before (one more
            # entry in ``agent_states`` and in ``prior_response_sha256s``), and
            # it is what an early exit conditioned on the answer just given
            # needs: ``KbAlphaBlendController`` reads its direct-decode
            # response before deciding to skip the evidence contact, and
            # ``a2t-hard-validity-repair-v1`` reads its draft before deciding
            # to skip the repair contact.
            should_stop = bool(self._stop_policy(staged, tuple(self._completed)))

        # E6: the supply decision for the NEXT phase is taken HERE, on the
        # wave that just completed, because that is the only wave whose
        # transition can carry it (module docstring, "Traced supply"). The
        # context it sees carries this phase's just-sealed state but the
        # PRIOR QueryState -- the state the RankResult/FusionDecision must
        # be bound to (rails.runner._validate_agent_knowledge_decision
        # validates them against exactly that state).
        action_phase = getattr(self._tools_for_phase, "is_action_phase", lambda _name: False)
        if should_stop and action_phase(phase.name) and not self._native_mode:
            raise RailsControllersError("a Planner action phase cannot deliver its response")
        tool_step: PhaseToolStep | None = None
        supply: PhaseSupply | None = None
        if not should_stop:
            next_spec = self._program.phases[index + 1]
            if self._tools_for_phase is not None:
                tool_step = self._tools_for_phase(phase.name, next_spec.name, staged)
                if self._native_mode and tool_step is None:
                    raise RailsControllersError("native tool request produced no tool observation")
                if tool_step is not None:
                    if not isinstance(tool_step, PhaseToolStep):
                        raise RailsControllersError("tools_for_phase must return PhaseToolStep or None")
                    tool_step.validate()
            supply = (tool_step.supply if tool_step is not None else
                      self._resolve_supply(next_spec, staged))
            if supply is not None and next_spec.knowledge != "supplied":
                raise RailsControllersError("tool knowledge requires a supplied successor phase")
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
            if supply is not None:
                # E3c: a phase this trajectory has already answered may not
                # acquire what it already holds (restrict_repeat_visit_supply).
                # A linearly walked PhaseProgram never repeats a phase, so
                # this is a no-op here today and the decision is returned
                # unchanged; the seam lives on the base because the native
                # role episode's REVISE route DOES re-enter the Solver.
                supply = restrict_repeat_visit_supply(
                    supply, context, phase_name=next_spec.name
                )

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
        added_states = (artifact,) + (() if tool_step is None else (tool_step.state,))
        next_state, transition = advance_phase_response_state(
            context=context,
            added_states=added_states,
            action_target_ref=f"{self._program.program_id}:{phase.name}->{next_phase.name}",
            supply=supply,
        )
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
            agent_states=context.agent_states + added_states,
            prior_response_sha256s=context.prior_response_sha256s + (response_sha256,),
            contact_index=context.contact_index + 1,
        )
        next_contact = self._dispatch(next_phase, next_context)
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=next_state,
            new_agent_states=added_states,
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
            core_completions=context.core_completions,
        )

    def _resolve_state_view(self, phase: PhaseSpec, response_text: str) -> str:
        """What this phase seals: the raw response, or the registered view of
        it (:data:`StateViewForPhase`).

        Fail-closed on anything that is not non-empty text, for the same reason
        every other injected callable here is type-checked: a view that
        returned ``None`` would silently seal nothing, and the next phase would
        read an empty state instead of refusing.
        """

        if self._state_view_for_phase is None:
            return response_text
        content = self._state_view_for_phase(phase.name, response_text)
        if not isinstance(content, str) or not content:
            raise RailsControllersError(
                f"state_view_for_phase({phase.name!r}) must return non-empty text, "
                f"got {type(content).__name__}"
            )
        return content

    def _resolve_review(
        self,
        phase: PhaseSpec,
        staged: AgentRuntimeContext,
        response_text: str,
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
        verdicts = self._review_for_phase(phase.name, staged, response_text)
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
        staged: AgentRuntimeContext,
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
        supply = self._supply_for_phase(next_phase.name, staged)
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


def _phase_already_visited(context: AgentRuntimeContext, phase_name: str) -> bool:
    """Has ``phase_name`` already answered once in THIS trajectory?

    The evidence is the phase's own sealed state: every phase response is
    sealed by :func:`seal_phase_response_state` with
    ``state_kind="phase:<phase name>"``, so one such artifact in
    ``context.agent_states`` means the phase is about to be RE-entered
    (a native episode's Planner routing REVISE back into the Solver), not
    entered for the first time.
    """

    kind = f"phase:{phase_name}"
    return any(
        getattr(artifact, "state_kind", None) == kind
        for artifact in context.agent_states
    )


def restrict_repeat_visit_supply(
    supply: PhaseSupply,
    context: AgentRuntimeContext,
    *,
    phase_name: str,
) -> PhaseSupply | None:
    """The supply decision a RE-ENTERED phase may still acquire (E3c).

    A prepared phase supply is a pure function of (phase, sample): when a
    native episode's Planner routes REVISE, the Solver is visited a second
    time and the SAME decision comes back. Its values are already in
    ``QueryState.retrieved_value_ids`` -- they reached the first Solver
    request and, because every later request renders from the ACCUMULATED
    state, they reach the second one too without being acquired again.
    Acquiring them a second time is not merely redundant: ``QueryState``
    refuses duplicate ``retrieved_value_ids``, so
    ``EvidenceAgentController._acquired_ids`` refuses the decision and the
    whole trajectory dies (the 2026-09-17 cell B1 abort).

    So on a repeat visit this returns the decision restricted to what is
    NOT yet visible -- exactly what ``rails.kb_policy``'s own fuser does
    against ``query_state.retrieved_value_ids`` before it ever builds a
    decision -- as a filtered :class:`PhaseSupply`, or ``None`` when the
    revisit acquires nothing at all (an ``acquire`` transition that
    introduces neither a value nor a facet is refused by
    ``AgentStepTransition.validate``; the wave then seals its response as an
    ordinary ``organize`` step and the accumulated state still carries every
    earlier value).

    Two invariants make this safe to put on the base:

    * **The FIRST visit of every phase is untouched.** Without a sealed
      ``phase:<phase_name>`` state this returns the caller's own object,
      so the transition, the ``new_value_ids`` and the rendered request
      bytes are identical to before this function existed -- and
      ``_acquired_ids``' refusal keeps its original purpose, which is to
      catch a fuser that fails to exclude already-visible values on a
      first, genuinely new acquisition.
    * **Facet exposure does not change.** Whether the decision exposes its
      supporting facets is decided from the decision AS GIVEN
      (``expose_facets or not selected_value_ids``, the same expression
      ``_acquired_ids`` evaluates), never from the filtered selection, so a
      value-only supply whose values are all visible yields ``None`` rather
      than silently promoting its facets into a ``knowledge_role="key"``
      block the first visit never carried.

    A filtered decision keeps every hash edge of the original
    (``snapshot_sha256``/``query_state_sha256``/``rank_result_sha256`` and
    the supporting facets), so ``rails.knowledge.assert_knowledge_use_binding``
    still holds: dropping selected values cannot break the value-to-supporting-
    facet association it checks.
    """

    supply.validate()
    _require_nonempty_str(phase_name, field="restrict_repeat_visit_supply.phase_name")
    if not _phase_already_visited(context, phase_name):
        return supply
    decision = supply.fusion_decision
    selected = tuple(decision.selected_value_ids)
    visible_values = set(context.query_state.retrieved_value_ids)
    unseen = tuple(value_id for value_id in selected if value_id not in visible_values)
    visible_facets = set(context.query_state.visible_facet_ids)
    newly_supporting = tuple(
        facet_id
        for facet_id in decision.supporting_facet_ids
        if facet_id not in visible_facets
    )
    # The decision's OWN exposure semantics, read off the decision as given
    # -- `_acquired_ids` evaluates exactly this expression.
    expose = supply.expose_facets or not selected
    if not unseen and not (expose and newly_supporting):
        return None
    if unseen == selected:
        return supply
    return replace(
        supply,
        fusion_decision=replace(decision, selected_value_ids=unseen).validate(),
    ).validate()


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
    "phase-native-slot-review-contract-v1": "phase-native-slot-review-contract-v1.json",
    "phase-audio2tool-native-candidate-recovery-tools-v1": (
        "phase-audio2tool-native-candidate-recovery-tools-v1.json"
    ),
    "phase-audio2tool-native-candidates-review-revise-v1": "phase-audio2tool-native-candidates-review-revise-v1.json",
    "phase-audio2tool-native-candidates-review-revise-json-v1": "phase-audio2tool-native-candidates-review-revise-json-v1.json",
    "phase-native-review-revise-v1": "phase-native-review-revise-v1.json",
    "phase-native-review-revise-json-v1": "phase-native-review-revise-json-v1.json",
    "phase-native-candidates-review-revise-v1": "phase-native-candidates-review-revise-v1.json",
    # Cell B7r, 2026-09-17 (the Node Context Policy's review-finding
    # PRODUCER format): the SAME four phases, the SAME episode shape and
    # the SAME contact ceiling 11 as
    # "phase-native-candidates-review-revise-v1", with the Reviewer phase
    # declaring the registered "saea-review-findings-v1" output contract.
    # A phase's output contract has exactly one authority
    # (rails.phase_material.load_phase_material_specs), and
    # rails.native_episode_config refuses a context_policy "producers"
    # block whose declared format differs from the producing phase's, so
    # the Reviewer format is a program id rather than a flag on the
    # review-revise program.
    "phase-native-candidates-review-revise-findings-v1": (
        "phase-native-candidates-review-revise-findings-v1.json"
    ),
    # Gap G1 plumbing, 2026-09-26 (``rails.solver_citation``): the SAME four
    # phases, the SAME episode shape and the SAME contact ceiling 11 as
    # "phase-native-candidates-review-revise-v1", with the Solver phase
    # declaring the registered "saea-solver-cited-answer-v1" output contract.
    # A phase's output contract has exactly one authority, so the citing
    # Solver is a program id rather than a flag on the review-revise program;
    # rails.native_episode_config refuses it without a cited-answer delivery
    # normaliser.
    "phase-native-candidates-review-revise-cited-v1": (
        "phase-native-candidates-review-revise-cited-v1.json"
    ),
    # E1, 2026-09-16: the SAME four phases as
    # "phase-native-candidates-review-revise-v1", with the Reviewer/Planner
    # review loop switched off by the baseline's own native_episode.roles
    # (max_iterations 0 + max_revisions 0). Only max_contacts moves (11 -> 2)
    # because the program id still names all four phases; the two program
    # ids must never resolve to the same object because their contact
    # ceilings differ.
    "phase-native-candidates-solve-v1": "phase-native-candidates-solve-v1.json",
    # Cell P1, 2026-09-22 (owner decision 85, the first pruning cell on the
    # measurable-Reviewer base R-PRIM, decision 97): the SAME four phases and
    # the SAME episode shape as "phase-native-candidates-review-revise-v1",
    # with the Reviewer at ONE visit per revision round (the baseline's own
    # native_episode.roles.reviewer.max_iterations 3 -> 1). Only max_contacts
    # moves (11 -> 7: 1 + (1+1)*(1+1+1)); a separate program id because the
    # two program ids must never resolve to the same object when their
    # contact ceilings differ.
    "phase-native-candidates-review1-revise-v1": "phase-native-candidates-review1-revise-v1.json",
    # E2b, 2026-09-16: the SAME four phases and the SAME episode_id as
    # "phase-native-candidates-solve-v1", with a wider contact ceiling for
    # a grouped Solver visit (rails.native_episode_config: 1 + 1*(0+0+5) =
    # 6 when the Solver role declares samples 5). A separate program id,
    # never a flag on the first, for the same reason E1's own comment
    # above states: the two program ids must never resolve to the same
    # object because their contact ceilings differ.
    "phase-native-candidates-solve-samples5-v1": (
        "phase-native-candidates-solve-samples5-v1.json"
    ),
    # Cell B2 on the sealed dual-store ANCHOR, 2026-09-17 (module M2 re-based
    # after the B0 re-decision returned module M0 HARMFUL under the TRAIN A
    # own null): the SAME four phases and the SAME episode_id as
    # "phase-native-candidates-review-revise-v1" -- the review loop ON,
    # reviewer 3 / planner 1 / max_revisions 1 -- with the grouped Solver
    # ceiling. rails.native_episode_config multiplies the Solver's own
    # contribution by its registered samples, so the bounded graph ceiling is
    # 1 + (1+1)*(5*1 + 3 + 1) = 19 when the Solver role declares samples 5.
    # A separate program id, never a flag on the review-revise program, for
    # the reason the two comments above state: two program ids must never
    # resolve to the same object when their contact ceilings differ.
    "phase-native-candidates-review-revise-samples5-v1": (
        "phase-native-candidates-review-revise-samples5-v1.json"
    ),
    # Cell ROLL-AA, 2026-09-24 (board route F2, the Stage-3 within-flight A/A null):
    # the SAME four phases and the SAME episode_id as
    # "phase-native-candidates-review-revise-samples5-v1" -- the review loop ON,
    # reviewer 3 / planner 1 / max_revisions 1 -- with the grouped-Solver ceiling at
    # samples 2 instead of 5: 1 + (1+1)*(1*2 + 3 + 1) = 13. A separate program id,
    # never a flag on the samples5 program, for the reason every comment above
    # states: two program ids must never resolve to the same object when their
    # contact ceilings differ, and rails.native_episode_config asserts
    # program.max_contacts equals the graph ceiling.
    "phase-native-candidates-review-revise-samples2-v1": (
        "phase-native-candidates-review-revise-samples2-v1.json"
    ),
    # Item E42, 2026-09-25 (board route F12, Stage-3 family VAR-2: per-row
    # CONSTRUCTION-VARIANT interleaving inside ONE campaign): the SAME four
    # phases, the SAME episode_id and the SAME role graph as
    # "phase-native-candidates-review-revise-v1" -- the review loop ON,
    # reviewer 3 / planner 1 / max_revisions 1 -- with the Solver visit fanned
    # out to FOUR declared supply-variant arms instead of one.
    # rails.native_episode_config multiplies the Solver's own contribution by
    # its registered arm count exactly as it multiplies it by samples, so the
    # bounded graph ceiling is 1 + (1+1)*(1*1*4 + 3 + 1) = 17. A separate
    # program id, never a flag on the review-revise program, for the reason
    # every comment above states: two program ids must never resolve to the
    # same object when their contact ceilings differ, and
    # rails.native_episode_config asserts program.max_contacts equals the
    # graph ceiling. A group of some other size needs its own id and its own
    # fragment, exactly as samples2 needed one beside samples5.
    "phase-native-candidates-review-revise-variants4-v1": (
        "phase-native-candidates-review-revise-variants4-v1.json"
    ),
    # Owner decision 172, 2026-09-27 (docs/superpowers/specs/2026-09-27-
    # same-flight-supply-variant-instrument-design.md, merge set B): the SAME
    # four phases, the SAME episode_id and the SAME role graph as
    # "phase-native-candidates-review-revise-cited-v1" (max_contacts 11) --
    # reviewer 3 / planner 1 / max_revisions 1 -- with the Solver visit
    # fanned out to TWO declared supply-variant arms (the delivering arm plus
    # its twin, Q3 ruling) under ``arm_visits: "first"``: only the Solver's
    # first visit of the whole episode fans out, so the bounded graph
    # ceiling is the anchor's 11 plus (K - 1) = 12, not
    # ``rails.native_episode_config``'s ordinary per-revision product (that
    # product is exactly VAR-2's own bug). A separate program id, never a
    # flag on the cited program, for the reason every comment above states:
    # two program ids must never resolve to the same object when their
    # contact ceilings differ.
    "phase-native-candidates-review-revise-cited-variants2first-v1": (
        "phase-native-candidates-review-revise-cited-variants2first-v1.json"
    ),
    # Owner decision 172, 2026-09-27: the SAME shape as the variants2first
    # program directly above, with a THIRD arm (one treatment arm beside the
    # delivering arm and its twin, section 5's inner-loop use), so K = 3 and
    # the bounded graph ceiling is 11 + (3 - 1) = 13.
    "phase-native-candidates-review-revise-cited-variants3first-v1": (
        "phase-native-candidates-review-revise-cited-variants3first-v1.json"
    ),
    # Coordinator amendment, 2026-09-28 (docs/superpowers/specs/2026-09-27-
    # same-flight-supply-variant-instrument-design.md, "Coordinator amendment
    # (2026-09-28)"): an UNCITED twin of
    # "phase-native-candidates-review-revise-cited-variants2first-v1" directly
    # above -- the SAME four phases, the SAME episode_id and the SAME role
    # graph as "phase-native-candidates-review-revise-v1" (max_contacts 11,
    # the Solver's response_format_id null instead of the cited-answer
    # contract) -- with the Solver visit fanned out to TWO declared
    # supply-variant arms under ``arm_visits: "first"``, so the bounded graph
    # ceiling is the anchor's 11 plus (K - 1) = 12, by the same
    # ``rails.native_episode_config`` formula as its cited sibling. A separate
    # program id, never a flag on the uncited program, for the reason every
    # comment above states: two program ids must never resolve to the same
    # object when their contact ceilings differ.
    "phase-native-candidates-review-revise-variants2first-v1": (
        "phase-native-candidates-review-revise-variants2first-v1.json"
    ),
    # Coordinator amendment, 2026-09-28: the SAME shape as the uncited
    # variants2first program directly above, with a THIRD arm, so K = 3 and
    # the bounded graph ceiling is 11 + (3 - 1) = 13 -- the uncited twin of
    # "phase-native-candidates-review-revise-cited-variants3first-v1".
    "phase-native-candidates-review-revise-variants3first-v1": (
        "phase-native-candidates-review-revise-variants3first-v1.json"
    ),
    # Cell B7b on the sealed anchor, 2026-09-17 (M5 / NCP level L2): the SAME
    # four phases, the SAME episode_id and the SAME role graph as
    # "phase-native-candidates-review-revise-v1" -- reviewer 3 / planner 1 /
    # max_revisions 1 -- with ONE declared cleaning boundary. A cleaned
    # boundary spends at most one extra contact per contact of its CONSUMER
    # role, so rails.native_episode_config adds
    # (max_revisions + 1) * consumer.max_iterations = 2 * 1 to the bounded
    # graph ceiling: 1 + (1+1)*(1 + 3 + 1 + 1) = 13. A separate program id,
    # never a flag on the review-revise program, for the reason the samples5
    # comment states: two program ids must never resolve to the same object
    # when their contact ceilings differ, and rails.native_episode_config
    # asserts program.max_contacts equals the graph ceiling.
    "phase-native-candidates-review-revise-clean1-v1": (
        "phase-native-candidates-review-revise-clean1-v1.json"
    ),
    # E32, 2026-09-21 (item E18 wired to cell B9a, owner decisions 43/44/78):
    # the SAME four phases, the SAME episode_id and the SAME role graph as
    # "phase-native-candidates-review-revise-v1" -- reviewer 3 / planner 1 /
    # max_revisions 1 -- PLUS the fifth, optional Acquisition phase E18
    # built (rails.native_episode_config.ACQUISITION_ROLE_KIND). A separate
    # program id, never a flag on the review-revise program, because its
    # PHASE LIST differs from that program's even though the ceiling does
    # not move for a zero-contact acquisition kind: rails.native_episode_
    # config's own formula adds max_acquisitions_per_row * roles.acquisition.
    # max_iterations, which is 0 for the registered "knowledge-requery" and
    # "tool-acquire" kinds, so this program's bounded ceiling is still
    # 1 + (1+1)*(1+3+1) + 1*0 = 11 -- the same 11 as the four-phase program,
    # by construction rather than by coincidence. Composing this program id
    # WITHOUT native_episode.acquisition/roles.acquisition is refused
    # (rails.native_episode_config: the fifth phase would have no role
    # covering it, "native roles must cover the program once each"); the
    # OFF arm of cell B9a therefore stays on
    # "phase-native-candidates-review-revise-v1", the program the sealed
    # PLAN arm already flies, never on this one.
    "phase-native-candidates-review-revise-acquire-v1": (
        "phase-native-candidates-review-revise-acquire-v1.json"
    ),
    # Item E35 (owner decision 89, 2026-09-21): a CARRIER-NEUTRAL twin of the
    # program above -- the same five phases, the same contact ceiling and
    # the same stop rule, but with the Perception phase's
    # response_format_id null instead of SLURP's "slurp-intent-hypotheses-v1"
    # -- so the Earnings21+ConEC carrier can fly the same six-node native
    # episode SLURP flies through the shared harness
    # (rails.controllers.EvidenceAgentController, core.flight.FlightRuntime).
    "phase-native-review-revise-acquire-v1": "phase-native-review-revise-acquire-v1.json",
    "phase-native-candidates-review-refresh-v1": "phase-native-candidates-review-refresh-v1.json",
    "native-answer-or-one-tool-v1": "native-answer-or-one-tool-v1.json",
    "native-answer-or-tool-v1": "native-answer-or-tool-v1.json",
    "phase-task-tools-then-solve-v1": "phase-task-tools-then-solve-v1.json",
    "phase-task-tools-solve-revise-v1": "phase-task-tools-solve-revise-v1.json",
    "phase-direct-only-v1": "phase-direct-only-v1.json",
    "phase-system-group-operations-v1": "phase-system-group-operations-v1.json",
    "phase-system-batch-operations-v1": "phase-system-batch-operations-v1.json",
    "phase-knowledge-value-edit-v1": "phase-knowledge-value-edit-v1.json",
    # Stage-3 S3-4 (2026-09-22): one phase ("advantage"), one contact, the
    # SAME one-phase shape ``phase-direct-only-v1`` uses. What differs is
    # what the fragment binds it to: the "construction-advantage-text" arm
    # (bare-core plus this row's own construction gold, `e0.d2_leakage
    # .ARM_VISIBLE_FIELDS`) and the ``stage3-advantage-statement-v1``
    # response format (`rails.stage3_advantage`). The program object itself
    # carries no knowledge of the best/worst sample-answer material -- that
    # is rendered into the phase's instruction by a caller-supplied
    # ``material_for_phase`` at flight time (`rails.stage3_advantage`
    # module docstring), never by this program.
    "phase-stage3-advantage-v1": "phase-stage3-advantage-v1.json",
    # Stage-3 S3-4s (owner decision 106, 2026-09-23): the SYSTEM-level
    # advantage program. Identical in shape to v1 -- one phase
    # ("advantage"), one contact, no knowledge -- and different in exactly
    # one field: it binds the ``stage3-advantage-statement-v2`` response
    # format (one to three NODE/DELTA-KIND/TARGET/STATEMENT blocks)
    # instead of v1's single three-line statement. A program and its
    # fragment must agree on a phase output contract
    # (``rails.phase_material``), so the v2 contract needs its own program
    # rather than a mutation of v1's -- and v1 stays reachable, byte for
    # byte, for anything already registered against it.
    "phase-stage3-advantage-v2": "phase-stage3-advantage-v2.json",
    # Stage-3 layer A, the GEPA arm (owner decision 101; design note
    # docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md):
    # one phase ("gepa"), one contact, no knowledge -- the same one-phase
    # shape ``phase-stage3-advantage-v2`` has. It differs in exactly one
    # field, the ``stage3-gepa-proposal-v1`` response format (one to FIVE
    # blocks, all addressed to the group's single node), and a program and
    # its fragment must agree on a phase output contract
    # (``rails.phase_material``), so the GEPA contract needs its own program
    # rather than a mutation of the advantage one. It is also the id
    # ``core.flight.runtime._default_construction_material`` dispatches the
    # GEPA material on, because both cells fly the SAME arm.
    "phase-stage3-gepa-v1": "phase-stage3-gepa-v1.json",
    # Stage-3 F11, cell VERIFY-1 (2026-09-25): ONE phase ("choose"), one
    # contact, no knowledge -- the same one-phase shape
    # ``phase-slots-given-intent-v1`` has, and reached the same way: the
    # phase's speech rides the ordinary phase-program path and its per-row text
    # is an EXTERNAL sealed state, here the row's five sealed ROLL-1 Solver
    # candidates under the opt-in ``sealed-samples-manifest`` predecessor
    # binding (``rails.phase_material``). It differs from every one-phase
    # program already registered in exactly one field, the
    # ``slurp-verifier-choice-v1`` response format, and a program and its
    # fragment must agree on a phase output contract
    # (``rails.phase_material.load_phase_material_specs``), so the selection
    # contract needs its own program rather than a mutation of a slots one.
    #
    # ``max_contacts`` 2 against ONE phase, deliberately: the program spends
    # exactly one contact per row ("always-run-full-program" walks each phase
    # once), and the ceiling carries one contact of headroom so the registered
    # per-row bound is 2 rather than a bound with no slack at all. It is a
    # BOUND, never a target, and the cell's expected spend is 1.0 per row.
    "phase-slurp-verify-select-v1": "phase-slurp-verify-select-v1.json",
    # Decision 263-A (2026-10-11), E-T1: the typed proposer and the ACE
    # reflector. Each is ONE text-only phase and ONE contact on a
    # construction carrier row, the same one-phase shape the GEPA program
    # has; each differs in exactly its response format (a program and its
    # fragment must agree on a phase output contract). They are the ids
    # ``core.flight.runtime._default_construction_material`` dispatches the
    # two materials on (``rails.tfrl_typed_proposer``).
    "phase-tfrl-typed-proposer-v1": "phase-tfrl-typed-proposer-v1.json",
    "phase-tfrl-ace-reflector-v1": "phase-tfrl-ace-reflector-v1.json",
    "phase-training-feedback-proposal-v1": "phase-training-feedback-proposal-v1.json",
    "phase-intent-hypotheses-only-v1": "phase-intent-hypotheses-only-v1.json",
    "phase-direct-then-slots-v1": "phase-direct-then-slots-v1.json",
    "phase-direct-then-slots-supplied-v1": "phase-direct-then-slots-supplied-v1.json",
    "phase-direct-evidence-alpha-blend-v1": "phase-direct-evidence-alpha-blend-v1.json",
    "phase-select-then-fill-v1": "phase-select-then-fill-v1.json",
    "phase-draft-revise-v1": "phase-draft-revise-v1.json",
    "phase-reviewed-repair-v1": "phase-reviewed-repair-v1.json",
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
    # KU-S4N, 2026-09-09: ``phase-direct-only-v1``'s single direct-decode
    # phase with ``knowledge: "supplied"``, which is what
    # ``rails.phase_supply.load_phase_supply_specs`` requires before a
    # baseline fragment may supply it. A second program id rather than a flag
    # on the first, for the reason the slots pair states above: the phase's
    # ``knowledge`` value rides the config hash and is part of what the cell
    # IS, so the unsupplied direct program and the narrowing cell must never
    # resolve to the same program object.
    "phase-direct-only-supplied-v1": "phase-direct-only-supplied-v1.json",
    # WAVE R7, 2026-09-08: the fold of the retired
    # ``rails.a2t_hard_validity.HardValidityRepairController``. ``draft`` then,
    # only when the draft is hard-invalid, ``repair`` -- the early exit is the
    # ``stop_policy`` seam reading the draft's own registered validity report,
    # so the phase index decides which phase runs and the retired controller's
    # hard-coded ``QueryState.loop_step`` branch is gone.
    "phase-hard-validity-repair-v1": "phase-hard-validity-repair-v1.json",
    # Same-flight instrument, PHASE 2 (merge set C, design docs/superpowers/
    # specs/2026-09-28-same-flight-instrument-phase2-perception-variants-
    # design.md section 5, item 8): the SAME four phases, the SAME episode_id
    # and the SAME role graph as "phase-native-candidates-review-revise-v1"
    # (max_contacts 11) -- reviewer 3 / planner 1 / max_revisions 1 -- with the
    # Perception visit fanned out to K = 3 declared branches (design section 6,
    # cells P-SV-1 and P-SV-2), level 1 (note only): the bounded graph ceiling
    # is the anchor's 11 plus (K - 1) = 13
    # (rails.supply_variants.perception_branch_ceiling). A separate program id,
    # never a flag on the base program, for the reason every comment above
    # states: two program ids must never resolve to the same object when their
    # contact ceilings differ.
    "phase-native-candidates-review-revise-pbranch3-l1-v1": (
        "phase-native-candidates-review-revise-pbranch3-l1-v1.json"
    ),
    # Same-flight instrument, PHASE 2: the SAME shape as the pbranch3-l1
    # program directly above, at level 2 (note + one Solver contact per
    # non-A branch) instead of level 1: the bounded graph ceiling is the
    # anchor's 11 plus 2 (K - 1) = 15.
    "phase-native-candidates-review-revise-pbranch3-l2-v1": (
        "phase-native-candidates-review-revise-pbranch3-l2-v1.json"
    ),
    # Item E4 (2026-09-28, owner decision 185, "core-native targeted re-
    # listen"; design docs/superpowers/specs/2026-09-28-e4-core-native-
    # targeted-relisten-design.md, section 6's implementation-plan table and
    # the section 8 coordinator rulings): the SAME four phases, the SAME
    # episode_id shape and the SAME role graph as
    # "phase-native-candidates-review-revise-v1" (max_contacts 11), with a
    # post-accept ``native_episode.relisten`` block armed
    # (max_slots_per_row 3, two contacts per triggered entity --
    # ``rails.relisten.RelistenConfig.extra_contacts_ceiling``): the bounded
    # graph ceiling is the anchor's 11 plus 2 * 3 = 17
    # (``rails.native_episode_config``'s own relisten ceiling term). A
    # separate program id, never a flag on the base program, for the reason
    # every comment above states: two program ids must never resolve to the
    # same object when their contact ceilings differ. Uncited: no baseline
    # or experiment fragment names it yet, and v1 registers no cell -- this
    # entry only makes the program available to compose against.
    "phase-native-candidates-review-revise-relisten-v1": (
        "phase-native-candidates-review-revise-relisten-v1.json"
    ),
}

_LOADED_PROGRAMS: dict[str, PhaseProgram] = {}


# --- The consumption module's PROGRAM FAMILY (coordinator ruling R1, design
# docs/superpowers/specs/2026-09-29-slurp-consumption-module-design.md) ------
#
# The module (``rails.consumption_module``) computes its contact ceiling from
# the components it arms, and the rule every comment above states -- two
# program ids must never resolve to the same object when their contact
# ceilings differ -- forces one program id per ceiling. R1: one registered id
# per computed ceiling, ``phase-native-module-v1-c<ceiling>``, all registered
# through ONE family registration below and none written by hand as a
# ``configs/policy`` fragment. Every family program is the v2.0 lock program
# (:data:`MODULE_PROGRAM_FAMILY_BASE`) with exactly two fields replaced: its
# ``program_id`` and its ``max_contacts``, which equals the ceiling its own id
# names. The ceilings are the closed range the module's contact table (design
# section 2.4) can reach over the lock's 11: + 1 (the E3 slot-types node),
# + 2..6 (one or two same-flight Perception columns at level 1 or 2), + 6
# (re-listen, 3 entities x 2 contacts) -- every value from 11 to 24.
# The prospective review-off profile adds only 2 and 3: Perception/Solver,
# with one optional bounded Solver lookup followed by its reserved answer.
#
# The ids are written out as literals in one tuple so the engineering-base
# gate reads them from source without importing the package
# (scripts/checks/engineering_base_check.py, "family registration" rule).
MODULE_PROGRAM_FAMILY_PREFIX = "phase-native-module-v1-c"
MODULE_PROGRAM_FAMILY_BASE = "phase-native-candidates-review-revise-v1"
MODULE_PROGRAM_FAMILY_IDS: tuple[str, ...] = (
    "phase-native-module-v1-c2",
    "phase-native-module-v1-c3",
    # NX programme E1 (2026-10-09): the review-off graph (perception 1 +
    # solver 1 = 2) with a node-template arm group of K contacts at the Solver's
    # first visit has ceiling 2 + (K - 1); K runs 2..8 (one candidate to six,
    # the delivering arm and a twin), plus the lookup profile's one extra.
    "phase-native-module-v1-c4",
    "phase-native-module-v1-c5",
    "phase-native-module-v1-c6",
    "phase-native-module-v1-c7",
    "phase-native-module-v1-c8",
    "phase-native-module-v1-c9",
    "phase-native-module-v1-c10",
    "phase-native-module-v1-c11",
    "phase-native-module-v1-c12",
    "phase-native-module-v1-c13",
    "phase-native-module-v1-c14",
    "phase-native-module-v1-c15",
    "phase-native-module-v1-c16",
    "phase-native-module-v1-c17",
    "phase-native-module-v1-c18",
    "phase-native-module-v1-c19",
    "phase-native-module-v1-c20",
    "phase-native-module-v1-c21",
    "phase-native-module-v1-c22",
    "phase-native-module-v1-c23",
    "phase-native-module-v1-c24",
)


def module_program_family_ceiling(program_id: str) -> int:
    """The contact ceiling a family id names (``...-c<ceiling>``); refuses an
    id that is not a registered family member."""

    if program_id not in MODULE_PROGRAM_FAMILY_IDS:
        raise RailsControllersError(
            f"{program_id!r} is not a registered consumption-module program id; "
            f"registered: {list(MODULE_PROGRAM_FAMILY_IDS)}"
        )
    return int(program_id[len(MODULE_PROGRAM_FAMILY_PREFIX):])


def module_program_fallback_contacts_per_row(program_id: str) -> int:
    """Family-level ``fallback_contacts_per_row`` (decision 278 / 283 A): the extra answer-only re-ask contacts a row's plan
    ceiling must allow when its requests are budgeted thinking requests. Module family programs allow two (one per thinking
    node of the review-off graph); every other program allows one."""

    from ..core.reasoning_knobs import FALLBACK_CONTACTS_PER_ROW_DIRECT, FALLBACK_CONTACTS_PER_ROW_MODULE  # noqa: PLC0415

    return (
        FALLBACK_CONTACTS_PER_ROW_MODULE
        if program_id in MODULE_PROGRAM_FAMILY_IDS else FALLBACK_CONTACTS_PER_ROW_DIRECT
    )


def module_program_family_id(ceiling: int) -> str:
    """The family id for ``ceiling``; refuses a ceiling outside the family."""

    program_id = f"{MODULE_PROGRAM_FAMILY_PREFIX}{ceiling}"
    module_program_family_ceiling(program_id)
    return program_id


def _module_family_program(program_id: str) -> PhaseProgram:
    import dataclasses  # noqa: PLC0415

    base = default_phase_program(MODULE_PROGRAM_FAMILY_BASE)
    program = dataclasses.replace(
        base,
        program_id=program_id,
        max_contacts=module_program_family_ceiling(program_id),
    )
    program.validate()
    return program


def registered_program_ids() -> tuple[str, ...]:
    """The program ids this module registers into
    ``core.base.AGENT_CONTROLLERS`` (declaration order, not registry order)."""

    return tuple(_PROGRAM_CONFIG_FILENAMES)


def default_phase_program(program_id: str) -> PhaseProgram:
    """The frozen :class:`PhaseProgram` this module loaded for ``program_id``
    from its ``configs/policy/phase-*.json`` fragment (cached after first
    load; the file is never re-read once registration has run)."""

    if program_id in MODULE_PROGRAM_FAMILY_IDS:
        if program_id not in _LOADED_PROGRAMS:
            _LOADED_PROGRAMS[program_id] = _module_family_program(program_id)
        return _LOADED_PROGRAMS[program_id]
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
    if "phase-audio2tool-native-candidate-recovery-tools-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-audio2tool-native-candidate-recovery-tools-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-audio2tool-native-candidate-recovery-tools-v1"
                )
            ),
        )
    if "phase-native-candidates-review-refresh-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-refresh-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review-refresh-v1")
            ),
        )
    if "phase-audio2tool-native-candidates-review-revise-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-audio2tool-native-candidates-review-revise-v1",
            default_controller_factory(default_phase_program("phase-audio2tool-native-candidates-review-revise-v1")),
        )
    if "phase-audio2tool-native-candidates-review-revise-json-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-audio2tool-native-candidates-review-revise-json-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-audio2tool-native-candidates-review-revise-json-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review-revise-v1")
            ),
        )
    if "phase-native-candidates-review-revise-findings-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-findings-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-findings-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-cited-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-cited-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-cited-v1"
                )
            ),
        )
    if "phase-native-candidates-solve-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-solve-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-solve-v1")
            ),
        )
    if "phase-native-candidates-solve-samples5-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-solve-samples5-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-solve-samples5-v1")
            ),
        )
    if "phase-native-candidates-review1-revise-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review1-revise-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review1-revise-v1")
            ),
        )
    if "phase-native-candidates-review-revise-samples5-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-samples5-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review-revise-samples5-v1")
            ),
        )
    if "phase-native-candidates-review-revise-samples2-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-samples2-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review-revise-samples2-v1")
            ),
        )
    if "phase-native-candidates-review-revise-variants4-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-variants4-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review-revise-variants4-v1")
            ),
        )
    if "phase-native-candidates-review-revise-cited-variants2first-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-cited-variants2first-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-cited-variants2first-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-cited-variants3first-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-cited-variants3first-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-cited-variants3first-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-variants2first-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-variants2first-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-variants2first-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-variants3first-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-variants3first-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-variants3first-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-pbranch3-l1-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-pbranch3-l1-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-pbranch3-l1-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-pbranch3-l2-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-pbranch3-l2-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-pbranch3-l2-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-relisten-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-relisten-v1",
            default_controller_factory(
                default_phase_program(
                    "phase-native-candidates-review-revise-relisten-v1"
                )
            ),
        )
    if "phase-native-candidates-review-revise-clean1-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-clean1-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review-revise-clean1-v1")
            ),
        )
    if "phase-native-candidates-review-revise-acquire-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-candidates-review-revise-acquire-v1",
            default_controller_factory(
                default_phase_program("phase-native-candidates-review-revise-acquire-v1")
            ),
        )
    if "phase-native-review-revise-acquire-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-review-revise-acquire-v1",
            default_controller_factory(
                default_phase_program("phase-native-review-revise-acquire-v1")
            ),
        )
    if "phase-native-review-revise-json-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-review-revise-json-v1",
            default_controller_factory(default_phase_program("phase-native-review-revise-json-v1")),
        )
    if "phase-native-review-revise-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-review-revise-v1",
            default_controller_factory(default_phase_program("phase-native-review-revise-v1")),
        )
    if "native-answer-or-one-tool-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "native-answer-or-one-tool-v1",
            default_controller_factory(default_phase_program("native-answer-or-one-tool-v1")),
        )
    if "native-answer-or-tool-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "native-answer-or-tool-v1",
            default_controller_factory(default_phase_program("native-answer-or-tool-v1")),
        )
    if "phase-direct-only-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-direct-only-v1",
            default_controller_factory(default_phase_program("phase-direct-only-v1")),
        )
    if "phase-system-group-operations-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-system-group-operations-v1",
            default_controller_factory(default_phase_program("phase-system-group-operations-v1")),
        )
    if "phase-system-batch-operations-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-system-batch-operations-v1",
            default_controller_factory(default_phase_program("phase-system-batch-operations-v1")),
        )
    if "phase-knowledge-value-edit-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-knowledge-value-edit-v1",
            default_controller_factory(default_phase_program("phase-knowledge-value-edit-v1")),
        )
    if "phase-stage3-advantage-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-stage3-advantage-v1",
            default_controller_factory(default_phase_program("phase-stage3-advantage-v1")),
        )
    if "phase-stage3-advantage-v2" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-stage3-advantage-v2",
            default_controller_factory(default_phase_program("phase-stage3-advantage-v2")),
        )
    if "phase-stage3-gepa-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-stage3-gepa-v1",
            default_controller_factory(default_phase_program("phase-stage3-gepa-v1")),
        )
    if "phase-tfrl-typed-proposer-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-tfrl-typed-proposer-v1",
            default_controller_factory(default_phase_program("phase-tfrl-typed-proposer-v1")),
        )
    if "phase-tfrl-ace-reflector-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-tfrl-ace-reflector-v1",
            default_controller_factory(default_phase_program("phase-tfrl-ace-reflector-v1")),
        )
    if "phase-slurp-verify-select-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-slurp-verify-select-v1",
            default_controller_factory(
                default_phase_program("phase-slurp-verify-select-v1")
            ),
        )
    if "phase-training-feedback-proposal-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-training-feedback-proposal-v1",
            default_controller_factory(
                default_phase_program("phase-training-feedback-proposal-v1")
            ),
        )
    if "phase-intent-hypotheses-only-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-intent-hypotheses-only-v1",
            default_controller_factory(
                default_phase_program("phase-intent-hypotheses-only-v1")
            ),
        )
    if "phase-direct-then-slots-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-direct-then-slots-v1",
            default_controller_factory(
                default_phase_program("phase-direct-then-slots-v1")
            ),
        )
    if "phase-direct-then-slots-supplied-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-direct-then-slots-supplied-v1",
            default_controller_factory(
                default_phase_program("phase-direct-then-slots-supplied-v1")
            ),
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
    if "phase-reviewed-repair-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-reviewed-repair-v1",
            default_controller_factory(default_phase_program("phase-reviewed-repair-v1")),
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
    if "phase-direct-only-supplied-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-direct-only-supplied-v1",
            default_controller_factory(
                default_phase_program("phase-direct-only-supplied-v1")
            ),
        )
    if "phase-hard-validity-repair-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-hard-validity-repair-v1",
            default_controller_factory(
                default_phase_program("phase-hard-validity-repair-v1")
            ),
        )
    if "phase-task-tools-then-solve-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-task-tools-then-solve-v1",
            default_controller_factory(default_phase_program("phase-task-tools-then-solve-v1")),
        )
    if "phase-task-tools-solve-revise-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-task-tools-solve-revise-v1",
            default_controller_factory(
                default_phase_program("phase-task-tools-solve-revise-v1")
            ),
        )
    if "phase-native-slot-review-contract-v1" not in registered:
        AGENT_CONTROLLERS.register(
            "phase-native-slot-review-contract-v1",
            default_controller_factory(default_phase_program("phase-native-slot-review-contract-v1")),
        )
    unregistered = set(_PROGRAM_CONFIG_FILENAMES) - set(AGENT_CONTROLLERS.names())
    if unregistered:
        raise RailsControllersError(
            f"phase program ids without a literal registration: {sorted(unregistered)}"
        )


register_phase_programs_v1()


def register_module_program_family_v1() -> None:
    """The ONE family registration of coordinator ruling R1: every id in
    :data:`MODULE_PROGRAM_FAMILY_IDS` registers into
    ``core.base.AGENT_CONTROLLERS`` with the default controller factory over
    its own family program. Idempotent, like
    :func:`register_phase_programs_v1`."""

    registered = AGENT_CONTROLLERS.names()
    for program_id in MODULE_PROGRAM_FAMILY_IDS:
        if program_id not in registered:
            AGENT_CONTROLLERS.register(
                program_id, default_controller_factory(default_phase_program(program_id))
            )


register_module_program_family_v1()


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


def audio2tool_perception_state_response_format_v1(
    lock: Mapping[str, object],
    root: Path,
    *,
    max_actions: int,
    max_candidates_per_action: int,
) -> Mapping[str, object]:
    """Build the native Perception state schema over the whole pinned registry."""

    from .a2t_response_schema import (  # noqa: PLC0415 (import cost)
        audio2tool_perception_state_response_format,
    )

    return audio2tool_perception_state_response_format(
        _a2t_registry_rows(lock, root),
        max_actions=max_actions,
        max_candidates_per_action=max_candidates_per_action,
    )


def native_planner_action_response_format(
    actions: Sequence[str],
) -> Mapping[str, object]:
    """Render the strict shared Planner control envelope."""

    action_values = tuple(actions)
    if (
        not action_values
        or len(set(action_values)) != len(action_values)
        or any(not isinstance(action, str) or not action for action in action_values)
    ):
        raise ValueError("Planner response actions must be ordered unique strings")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "saea_native_planner_action_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["action"],
                "properties": {
                    "action": {"type": "string", "enum": list(action_values)},
                },
            },
        },
    }


def native_planner_action_response_format_v1(
    _lock: Mapping[str, object], _root: Path, *, actions: Sequence[str],
) -> Mapping[str, object]:
    """Registry adapter for the configuration-bound Planner action enum."""

    return native_planner_action_response_format(actions)


def register_response_formats_v1() -> None:
    """Idempotently register the E1 response-format ids into the shared
    ``core.base.RESPONSE_FORMATS`` registry (same shape and same
    re-entrancy discipline as :func:`register_phase_programs_v1`)."""

    registered = RESPONSE_FORMATS.names()
    if "saea-slot-review-handoff-v1" not in registered:
        from .review_handoff import slot_review_response_format

        RESPONSE_FORMATS.register("saea-slot-review-handoff-v1", slot_review_response_format)
    # Each id is a literal inside its own ``register`` call so the
    # engineering-base gate can read the registered name set from source
    # without importing the package.
    if "select-response-v1" not in registered:
        RESPONSE_FORMATS.register("select-response-v1", select_response_format_v1)
    if "fill-response-v1" not in registered:
        RESPONSE_FORMATS.register("fill-response-v1", fill_response_format_v1)
    if "audio2tool-perception-state-v1" not in registered:
        RESPONSE_FORMATS.register(
            "audio2tool-perception-state-v1",
            audio2tool_perception_state_response_format_v1,
        )
    if "saea-native-planner-action-v1" not in registered:
        RESPONSE_FORMATS.register(
            "saea-native-planner-action-v1",
            native_planner_action_response_format_v1,
        )
    if "slurp-intent-hypotheses-v1" not in registered:
        from .artifact_results import slurp_intent_hypotheses_response_format

        RESPONSE_FORMATS.register(
            "slurp-intent-hypotheses-v1",
            slurp_intent_hypotheses_response_format,
        )
    if "system-group-operations-v1" not in registered:
        from .system_operation_contract import group_operations_response_format

        RESPONSE_FORMATS.register("system-group-operations-v1", group_operations_response_format)
    if "system-batch-operations-v1" not in registered:
        from .system_operation_contract import batch_operations_response_format

        RESPONSE_FORMATS.register("system-batch-operations-v1", batch_operations_response_format)
    if "slot-value-edits-v1" not in registered:
        from .system_operation_contract import knowledge_edit_response_format

        RESPONSE_FORMATS.register("slot-value-edits-v1", knowledge_edit_response_format)
    if "training-feedback-proposal-v1" not in registered:
        from .training_feedback_artifacts import training_feedback_response_format

        RESPONSE_FORMATS.register(
            "training-feedback-proposal-v1",
            training_feedback_response_format,
        )
    # E8a (2026-09-17, Node Context Policy, coordinator decision 1): the
    # structured output contract the ``review-finding`` PRODUCER may declare.
    # Registering the id gives a cell config something to bind; no phase
    # changes until one does.
    if "saea-review-findings-v1" not in registered:
        from .review_findings import review_findings_response_format

        RESPONSE_FORMATS.register(
            "saea-review-findings-v1",
            review_findings_response_format,
        )
    # Gap G1 plumbing (2026-09-26, ``rails.solver_citation``): the Solver's
    # cited-answer contract -- the answer object beside the supplied evidence
    # ids it relied on, per intent and per entity. Registering the id changes
    # no phase; a phase program binds it to its ANSWERING phase and the
    # runner specialises it per contact to the ids that contact rendered.
    if "saea-solver-cited-answer-v1" not in registered:
        from .solver_citation import cited_answer_response_format

        RESPONSE_FORMATS.register(
            "saea-solver-cited-answer-v1",
            cited_answer_response_format,
        )
    # E8b (2026-09-17, Node Context Policy level L2): the closed output
    # contract one context-cleaning contact answers under. It is the schema
    # rails.node_context_policy.validate_cleaning_document checks, so a
    # response generated under this format satisfies the schema half of that
    # validation by construction. Registering the id changes no phase; a
    # boundary's cleaning block binds it.
    if "ncp-review-issues-v1" not in registered:
        from .node_context_policy import ncp_review_issues_response_format

        RESPONSE_FORMATS.register(
            "ncp-review-issues-v1",
            ncp_review_issues_response_format,
        )
    # Stage-3 S3-4 (2026-09-22): the ADV-t contact's structured-output
    # contract, beside the parser of record
    # (`rails.stage3_advantage.parse_advantage_statement`) in the same
    # module. Registering the id changes no phase; the advantage program's
    # own fragment (configs/policy/phase-stage3-advantage-v1.json) binds it.
    if "stage3-advantage-statement-v1" not in registered:
        from .stage3_advantage import stage3_advantage_response_format_v1

        RESPONSE_FORMATS.register(
            "stage3-advantage-statement-v1",
            stage3_advantage_response_format_v1,
        )
    # Stage-3 S3-4s (owner decision 106, 2026-09-23): the SYSTEM-level
    # contact's structured-output contract -- one to three blocks, each
    # NODE / DELTA-KIND / TARGET / STATEMENT. Its parser of record is
    # ``rails.stage3_advantage.parse_advantage_statements_v2``, which
    # reads BOTH this JSON shape and the literal four-line form, so the
    # schema and the parser are one contract. Registering the id changes
    # no phase; ``configs/policy/phase-stage3-advantage-v2.json`` binds it.
    if "stage3-advantage-statement-v2" not in registered:
        from .stage3_advantage import stage3_advantage_response_format_v2

        RESPONSE_FORMATS.register(
            "stage3-advantage-statement-v2",
            stage3_advantage_response_format_v2,
        )
    # Stage-3 layer A, the GEPA arm: the reflective proposal's own
    # structured-output contract -- one to five blocks, each NODE /
    # DELTA-KIND / TARGET / STATEMENT, with the group's node fixed by the
    # CONTACT rather than by the format. Its parser of record is
    # ``rails.stage3_gepa.parse_gepa_proposal``, which reads BOTH this JSON
    # shape and the literal four-line form, so the schema and the parser are
    # one contract. Registering the id changes no phase;
    # ``configs/policy/phase-stage3-gepa-v1.json`` binds it.
    if "stage3-gepa-proposal-v1" not in registered:
        from .stage3_gepa import stage3_gepa_response_format_v1

        RESPONSE_FORMATS.register(
            "stage3-gepa-proposal-v1",
            stage3_gepa_response_format_v1,
        )
    # Decision 263-A (2026-10-11), E-T1: the typed proposer's closed
    # candidate schema (no free-text field, no effect field; parser and
    # validator of record are ``rails.tfrl_typed_proposer``) and the ACE
    # reflector's delta-items schema (owned by ``rails.tfrl_ace_material``).
    # Registering the ids changes no phase; the two policy fragments bind them.
    if "saea-tfrl-typed-candidate-v1" not in registered:
        from .tfrl_typed_proposer import typed_candidate_response_format

        RESPONSE_FORMATS.register(
            "saea-tfrl-typed-candidate-v1",
            typed_candidate_response_format,
        )
    if "saea-ace-delta-items-v1" not in registered:
        from .tfrl_typed_proposer import ace_delta_items_response_format

        RESPONSE_FORMATS.register(
            "saea-ace-delta-items-v1",
            ace_delta_items_response_format,
        )
    # Stage-3 F11, cell VERIFY-1 (2026-09-25): the SELECTION contact's
    # structured-output contract -- exactly two fields, the 1-based position of
    # the chosen candidate and one bounded diagnostic line. Its parser of
    # record is ``rails.artifact_results.parse_slurp_verifier_choice``, beside
    # the schema in the same module, so the request's contract and the read's
    # leniency are one thing. Registering the id changes no phase;
    # ``configs/policy/phase-slurp-verify-select-v1.json`` binds it.
    if "slurp-verifier-choice-v1" not in registered:
        from .artifact_results import slurp_verifier_choice_response_format

        RESPONSE_FORMATS.register(
            "slurp-verifier-choice-v1",
            slurp_verifier_choice_response_format,
        )
    # Item E4 (2026-09-28, owner decision 185): the post-accept targeted
    # re-listen's two contacts, blind and forced-choice. Registering the ids
    # changes no phase (design section 6: the stage is wired beside
    # ``rails.runner``'s node-context-cleaning contact, never through a
    # ``PhaseProgram`` phase entry); ``native_episode.relisten`` names them
    # directly.
    if "slurp-relisten-value-v1" not in registered:
        from .relisten import relisten_blind_response_format

        RESPONSE_FORMATS.register(
            "slurp-relisten-value-v1",
            relisten_blind_response_format,
        )
    if "slurp-relisten-confirm-v1" not in registered:
        from .relisten import relisten_confirm_response_format

        RESPONSE_FORMATS.register(
            "slurp-relisten-confirm-v1",
            relisten_confirm_response_format,
        )


register_response_formats_v1()


# -- WAVE R7: the hard-validity repair fold ----------------------------------
#
# ``rails.a2t_hard_validity.HardValidityRepairController`` was an
# ``AgentController`` outside this module -- one of the 33 the September audit
# counted -- that sequenced a draft contact and a conditional repair contact
# and branched on ``QueryState.loop_step`` to tell them apart. It is gone. What
# replaces it is this file's own base walking ``phase-hard-validity-repair-v1``
# with three registered, switchable seams:
#
# * ``material_for_phase`` renders the two instruction constants, which
#   ``rails.a2t_hard_validity`` still owns, unchanged;
# * ``state_view_for_phase`` seals the bounded validity report as the draft
#   phase's state -- the ONE thing the retired controller did that the raw
#   response could not express, now a registered
#   ``core.base.PHASE_STATE_VIEWS`` id instead of a branch inside a controller;
# * ``stop_policy`` ends the trajectory on a VALID draft, which is the same
#   early exit the retired controller took, now taken by the base's own
#   ``stop-policy-optional-early-exit`` rule.
#
# ``tests/unit/test_a2t_hard_validity_fold.py`` proves the wire equivalence
# against the sealed G3 flight: same contact sequence, same control-turn bytes,
# same sealed-state bytes, same final answer, on the flight's own responses.

from .a2t_hard_validity import (  # noqa: E402  (registration block: see above)
    DRAFT_CONTACT_ID,
    DRAFT_INSTRUCTION,
    REPAIR_CONTACT_ID,
    REPAIR_INSTRUCTION,
    hard_validity_repair_state_view,
)

HARD_VALIDITY_PROGRAM_ID = "phase-hard-validity-repair-v1"


def hard_validity_repair_state_view_v1(
    registry_rows: Sequence[Mapping[str, str]],
) -> Callable[[str], str]:
    """The registered ``PHASE_STATE_VIEWS`` factory: bind the pinned registry
    rows, get the pure ``(response_text) -> state_content`` view."""

    rows = tuple(dict(row) for row in registry_rows)

    def view(response_text: str) -> str:
        return hard_validity_repair_state_view(response_text, rows)

    return view


def register_phase_state_views_v1() -> None:
    """Idempotently register this wave's ``core.base.PHASE_STATE_VIEWS`` ids
    (same shape and re-entrancy discipline as
    :func:`register_response_formats_v1`)."""

    # A literal id inside its own ``register`` call, so the engineering-base
    # gate can read the registered name set from this file's source.
    if "a2t-hard-validity-repair-report-v1" not in PHASE_STATE_VIEWS.names():
        PHASE_STATE_VIEWS.register(
            "a2t-hard-validity-repair-report-v1", hard_validity_repair_state_view_v1
        )


register_phase_state_views_v1()


def make_hard_validity_phase_controller(
    *,
    registry_rows: Sequence[Mapping[str, str]],
    key_representation_id: str,
    matcher_policy_id: str,
    decoding_params: Mapping[str, object],
) -> Callable[[str], EvidenceAgentController]:
    """The fold: a ``Callable[[str], AgentController]`` factory that reproduces
    the retired ``HardValidityRepairController`` on this module's base.

    Takes the same four constructor arguments the retired controller took, so a
    caller swaps one name and keeps its own identity strings. Note that
    ``key_representation_id`` and ``matcher_policy_id`` are carried into the
    dispatched plan exactly as they were: they are that cell's declared
    identity, not this base's, and a receipt that renamed them would be
    describing a different cell.
    """

    program = default_phase_program(HARD_VALIDITY_PROGRAM_ID)
    rows = tuple(dict(row) for row in registry_rows)
    view = hard_validity_repair_state_view_v1(rows)
    params = dict(decoding_params)
    instructions = {"draft": DRAFT_INSTRUCTION, "repair": REPAIR_INSTRUCTION}
    contact_ids = {"draft": DRAFT_CONTACT_ID, "repair": REPAIR_CONTACT_ID}

    def material_for_phase(
        phase_name: str, _context: AgentRuntimeContext
    ) -> PhaseMaterial:
        phase = program.phase(phase_name)
        return PhaseMaterial(
            instruction=instructions[phase_name],
            response_format=None,
            contact_id=contact_ids[phase_name],
            purpose=phase.purpose,
        ).validate()

    def state_view_for_phase(phase_name: str, response_text: str) -> str:
        # Only the draft's state is ever read by a later phase; the repair
        # phase is terminal, so its own state is sealed as the raw answer.
        if phase_name != "draft":
            return response_text
        return view(response_text)

    def stop_policy(context: AgentRuntimeContext, completed: Sequence[str]) -> bool:
        if tuple(completed) != ("draft",):
            return False
        # The staged context carries the draft's just-sealed state (WAVE R7's
        # stop-policy change); its content is the registered validity report,
        # so the early exit reads exactly what the retired controller read.
        sealed = context.agent_states[-1]
        return json.loads(sealed.content)["report"]["status"] == "valid"

    if params:
        # The retired controller put its decoding params on every contact plan;
        # ``rails.runner`` merges a plan's params OVER the run-level ones
        # (:func:`rails.runner._run_agent_trajectory`), and the G3 flight handed
        # the SAME mapping to both, so carrying them here would be a no-op that
        # only made the two look different. Refuse a mapping that is not that
        # no-op rather than silently dropping a real override.
        raise RailsControllersError(
            "make_hard_validity_phase_controller: decoding_params belong to the "
            "run, not to the contact -- rails.runner merges the run-level "
            "mapping into every plan already. Pass {} and set them on the "
            f"runner; got {sorted(params)}"
        )

    def factory(_sample_id: str) -> EvidenceAgentController:
        return EvidenceAgentController(
            program=program,
            material_for_phase=material_for_phase,
            stop_policy=stop_policy,
            state_view_for_phase=state_view_for_phase,
            contact_identity=(key_representation_id, matcher_policy_id),
        )

    return factory


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
    "PhaseToolStep",
    "ToolsForPhase",
    "RailsControllersError",
    "HARD_VALIDITY_PROGRAM_ID",
    "ContactIdentity",
    "ReviewForPhase",
    "StateViewForPhase",
    "StopPolicy",
    "SupplyForPhase",
    "default_controller_factory",
    "default_phase_program",
    "fill_response_format_v1",
    "load_phase_program",
    "make_hard_validity_phase_controller",
    "register_phase_programs_v1",
    "register_phase_state_views_v1",
    "register_response_formats_v1",
    "registered_program_ids",
    "restrict_repeat_visit_supply",
    "seal_phase_response_state",
    "select_response_format_v1",
]


# Consumer-specific views leave canonical phase artifacts and providers unchanged.
def register_role_context_compilers_v1():
    from ..core.base import ROLE_CONTEXT_COMPILERS
    from .role_context_binding import build_slurp_role_context_compiler

    if "typed-slurp-role-context-v1" not in ROLE_CONTEXT_COMPILERS.names():
        ROLE_CONTEXT_COMPILERS.register(
            "typed-slurp-role-context-v1", build_slurp_role_context_compiler,
        )
    # E8a (2026-09-17): the Node Context Policy registers in the SAME registry
    # (design section 12) because it is the same seam -- a consumer-specific,
    # source-bound view of state the episode already holds -- and because
    # folding ``native_episode.role_context`` under
    # ``native_episode.context_policy`` means one registry, not two.
    if "typed-slurp-node-context-v1" not in ROLE_CONTEXT_COMPILERS.names():
        from .node_context_binding import build_slurp_node_context_policy_compiler

        ROLE_CONTEXT_COMPILERS.register(
            "typed-slurp-node-context-v1", build_slurp_node_context_policy_compiler,
        )


register_role_context_compilers_v1()
