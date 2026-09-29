"""A bounded conditional OpenJiuwen episode composed from native role nodes.

The caller supplies every role prompt through a pure input builder and every
model contact through the ``NativeRoleNode`` instances. This module only
defines state transitions and public Workflow edges. It does not own contact
allocation, request history, task prompts, tool execution, or answer scoring.
"""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from openjiuwen.core.context_engine import ModelContext
from openjiuwen.core.graph.executable import Input, Output
from openjiuwen.core.session.node import Session
from openjiuwen.core.workflow import (
    BranchRouter,
    End,
    Start,
    Workflow,
    WorkflowComponent,
    create_workflow_session,
)

from ...rails.context_fit import (
    CONTEXT_COMPACTION_DISPOSITION,
    terminal_context_disposition,
)
from ...rails.review_primitives import REVIEW_VERDICT_ILLEGAL, parse_review_primitive
from ...rails.runner import SEAL_REFUSAL_DISPOSITION, RailsRunnerError
from .native_group_solver import GroupedSolverRoleNode
from .native_roles import (
    FrozenCoreRoleContextFitError,
    FrozenCoreRoleFiniteCompletionError,
    FrozenCoreRoleModelError,
    NativeRoleNode,
)


class NativeEpisodeError(RuntimeError):
    """The bounded role graph cannot produce an explicitly accepted answer."""


#: E8c: the routing value :func:`_planner_action` returns instead of raising
#: when the Planner's own output names no registered action, or is not the
#: strict action document ``json-action-v1`` requires.  It is a routing
#: value only: no role is ever asked to emit it, it is refused as a
#: configured action (:class:`NativeEpisodeActions`, :class:`NativeEpisodeSpec`),
#: and the graph maps it to the SAME explicit-accept seal an ``ACCEPT``
#: takes.  One malformed Planner token is a row-level disposition, never a
#: flight failure: the row is retained, sealed and reported.
PLANNER_ACTION_ILLEGAL = "__saea_planner_action_illegal__"

#: The ``planner_routes`` disposition and receipt-mark name for that row.
PLANNER_ACTION_ILLEGAL_DISPOSITION = "planner_action_illegal"

#: Item E39 (2026-09-22): the two scopes item E13's
#: ``finite_completion_policy`` may be read under. ``"episode"`` is the
#: default and every pre-E39 row's behaviour.
FINITE_COMPLETION_SCOPES = ("episode", "answering-node")

#: Item E39: the ONE stage of this graph that answers. Under
#: ``"answering-node"`` it is the only stage whose truncated completion is an
#: E13 disposition; every other stage keeps its partial text and the episode
#: walks on.
ANSWERING_STAGE = "solver"

#: Item E39: the mark a role node puts on a tolerated truncation, and the
#: receipt list the graph collects those marks into.
LENGTH_TRUNCATION_MARK = "length_truncation"
TRUNCATION_EVENTS = "truncation_events"
TRUNCATION_EVENTS_SCHEMA = "saea-native-length-truncation-v1"

#: The receipt-mark schema the episode state carries once a row took it.
PLANNER_ACTION_ILLEGAL_SCHEMA = "saea-native-planner-action-illegal-v1"

#: How much of the malformed token the route record keeps.  Beyond this the
#: token survives only as its sha256: the Planner's output may quote the
#: draft, which the route record is not a place for.
PLANNER_ACTION_RECORD_CHARS = 32

#: Item E22 (the ReAct-exhaustion disposition, not the Earnings-22 carrier),
#: 2026-09-19: the receipt-mark name a row carries once one of its tool
#: roles spent its whole ReAct iteration budget on tool calls without ever
#: returning an answer.  It is a VISIT-level disposition, not a terminal
#: one: the visit ends with no finding, the row goes on through the Planner
#: and delivers exactly as it would have, so the row's
#: ``terminal_disposition`` is untouched.
REACT_EXHAUSTION_DISPOSITION = "react_exhaustion"

#: The receipt-mark schema the episode state carries once a visit took it.
REACT_EXHAUSTION_SCHEMA = "saea-native-react-exhaustion-v1"

#: The stages whose exhausted visit may end with NO finding.  Only the
#: Reviewer's: a Solver visit owes a DRAFT (an empty one is not delivery
#: eligible and the row would have nothing to deliver) and a Planner visit
#: owes a ROUTE (with no action the conditional graph has no branch to
#: take), so for those two an exhausted visit keeps exactly its pre-E22
#: raise.  Perception carries no tool authority at all and cannot reach
#: this class.
REACT_EXHAUSTION_STAGES = frozenset({"review"})

#: Item E37 (owner decision 84), 2026-09-22: the receipt-mark disposition a
#: ``reviewer_verdicts`` entry carries when the first non-empty line of the
#: Reviewer's response is one of
#: ``rails.review_primitives.REVIEW_PRIMITIVE_TOKENS``, exactly.
REVIEWER_VERDICT_LEGAL = "legal"

#: The disposition an illegal primitive verdict carries -- the Reviewer's own
#: analogue of :data:`PLANNER_ACTION_ILLEGAL_DISPOSITION`: the row is
#: RETAINED, the raw text still renders into the Planner's query exactly as
#: today, and the receipt keeps only the bounded head
#: ``rails.review_primitives.parse_review_primitive`` returns.
REVIEWER_VERDICT_ILLEGAL_DISPOSITION = "review_verdict_illegal"

#: ``native_episode_receipt.reviewer_verdicts`` is a plain ordered list, one
#: entry per Reviewer visit of the row, each
#: ``{"visit": n, "token": ..., "disposition": ..., "head": ...}``. Present
#: ONLY when ``native_episode.reviewer_verdict`` is armed: an unarmed row's
#: ``_ApplyRole`` Reviewer branch never calls the helper that writes this
#: key, so its state -- and therefore its sealed receipt -- carries no
#: ``reviewer_verdicts`` key at all, byte-identical to its pre-E37 self.
REVIEWER_VERDICTS_KEY = "reviewer_verdicts"

#: E18 (2026-09-19, owner decisions 43 and 44): the stage name one
#: :class:`AcquisitionNode` visit registers in ``role_visits``.  It is the
#: name the finite-path and refresh receipt validators already tolerate
#: (:mod:`rails.native_episode_receipt`), so the sixth node's visits read
#: beside the other five rather than beneath them.
ACQUISITION_STAGE = "acquisition"

#: The keys one acquisition record must carry, exactly.  The record is
#: produced by ``rails.acquisition`` and validated again HERE, at the graph
#: boundary, because the graph is what writes it into episode state: a node
#: that returned something else must stop its own row rather than seal a
#: malformed receipt.
ACQUISITION_RECORD_KEYS = frozenset({
    "schema",
    "kind",
    "policy_id",
    "provenance_ids",
    "item_count",
    "contacts_used",
    "cost",
    "cost_unit",
    "inputs_sha256",
    "evidence_sha256",
    "evidence_chars",
    "visit_index",
    "revision_count",
    "planner_route_index",
    "planner_action",
    "state_filters",
})


class RoleInputBuilder(Protocol):
    """Render one role query from a detached snapshot of episode state."""

    def __call__(self, role_id: str, state: Mapping[str, object]) -> str: ...


@dataclass(frozen=True)
class NativeEpisodeActions:
    """Exact registered Planner actions; matching is case and byte sensitive."""

    accept: str
    revise: str
    acquire: str

    def __post_init__(self) -> None:
        values = (self.accept, self.revise, self.acquire)
        if any(not isinstance(value, str) or not value for value in values):
            raise ValueError("episode actions must be non-empty strings")
        if len(set(values)) != len(values):
            raise ValueError("episode actions must be distinct")
        if PLANNER_ACTION_ILLEGAL in values:
            # E8c: the illegal-output routing value is reserved.
            raise ValueError("episode actions must not use the reserved illegal action")


@dataclass(frozen=True)
class NativeEpisodeSpec:
    """Configuration-bound episode identity and finite revision allowance."""

    episode_id: str
    max_revisions: int
    actions: NativeEpisodeActions
    exhaustion_policy: str = "raise"
    refresh_action: str | None = None
    max_candidate_refreshes: int = 0
    finite_completion_policy: str = "raise"
    planner_output_format: str = "exact-text"
    review_loop_enabled: bool = True
    # E18: how many ACQUIRE routes of this episode may reach an acquisition
    # node.  0 -- every spec written before E18, and every episode with no
    # acquisition node -- builds no acquisition branch at all and leaves the
    # graph byte-identical to its pre-E18 self.  A positive value is the
    # configuration's ``max_acquisitions_per_row`` and is bounded by
    # ``max_revisions`` for the same reason ``max_candidate_refreshes`` is:
    # an ACQUIRE spends a revision, so a budget larger than the revision
    # allowance is a budget that can never be spent.
    max_acquisitions: int = 0
    # E20 (2026-09-19, owner decision 45): what an OVER-LONG request does.
    # ``"raise"`` -- every spec written before E20 -- kills the flight.
    # ``"compact-or-abstain"`` retains the row: the dispatch seam compacts
    # in the declared order and, when even that does not fit, this graph
    # delivers the latest delivery-eligible Solver draft (or abstains)
    # under a ``context_compaction`` terminal disposition. The switch
    # renders no request byte. Declared LAST for exactly the reason
    # ``max_acquisitions`` was: every positional construction written
    # before E20 composes the spec it always did.
    context_fit_policy: str = "raise"
    # Item E22 (the ReAct-exhaustion disposition, not the Earnings-22
    # carrier), 2026-09-19: what a TOOL role's exhausted ReAct loop does.
    # ``"raise"`` -- every spec written before E22 -- is the pre-E22
    # behaviour: :class:`_ApplyRole` refuses the non-answer and the flight
    # dies at that row. ``"continue-without-answer"`` ends that visit with
    # NO finding and lets the row continue: nothing is retried, no extra
    # contact is spent, and no request byte of any other contact moves.
    # Declared LAST, for the same reason ``context_fit_policy`` was.
    react_exhaustion_policy: str = "raise"
    # Item E37 (owner decision 84), 2026-09-22: the Reviewer's verdict as a
    # closed set of primitives. ``None`` -- every spec written before E37 and
    # every OFF arm -- means the Reviewer's ``_ApplyRole`` branch parses
    # nothing and writes no ``reviewer_verdicts`` mark, so the receipt is
    # byte-identical to its pre-E37 self. A non-empty string is the armed
    # vocabulary id (only ``rails.review_primitives.REVIEW_PRIMITIVES_VOCABULARY``
    # is registered today; a config-level refusal of any other id lives in
    # ``rails.native_episode_config.load_native_episode_config``, not here,
    # because THIS class stays the thin, config-free graph identity every
    # other episode-level field already is). Declared LAST, for the same
    # reason ``react_exhaustion_policy`` was.
    reviewer_verdict_vocabulary: str | None = None
    # Item E39 (2026-09-22): WHICH node's truncated completion ends the
    # episode. ``"episode"`` -- every spec written before E39 -- is the
    # pre-E39 behaviour, and the only thing this field then does is stay out
    # of the terminal disposition it is not written into. Under
    # ``"answering-node"`` the role NODES of every non-answering role tolerate
    # a ``length`` truncation (see
    # ``reproduction.ojw.native_roles.NativeRoleNode._tolerated_truncation``),
    # so this graph never sees their refusal at all, and the disposition a
    # Solver truncation still writes records which rule applied. Declared
    # LAST, for the same reason ``reviewer_verdict_vocabulary`` was.
    finite_completion_scope: str = "episode"

    def __post_init__(self) -> None:
        if not isinstance(self.episode_id, str) or not self.episode_id:
            raise ValueError("episode_id must be a non-empty string")
        if (
            isinstance(self.max_revisions, bool)
            or not isinstance(self.max_revisions, int)
            or self.max_revisions < 0
        ):
            raise ValueError("max_revisions must be a non-negative integer")
        if not isinstance(self.actions, NativeEpisodeActions):
            raise ValueError("actions must be NativeEpisodeActions")
        if (
            not isinstance(self.exhaustion_policy, str)
            or self.exhaustion_policy not in {"raise", "deliver-latest-solver"}
        ):
            raise ValueError("exhaustion_policy is invalid")
        if self.refresh_action is None:
            if (
                self.max_candidate_refreshes != 0
                or isinstance(self.max_candidate_refreshes, bool)
                or not isinstance(self.max_candidate_refreshes, int)
            ):
                raise ValueError("candidate refresh count requires an explicit action")
        elif (
            not isinstance(self.refresh_action, str) or not self.refresh_action.strip()
            or self.refresh_action in (
                self.actions.accept, self.actions.revise, self.actions.acquire
            )
            or isinstance(self.max_candidate_refreshes, bool)
            or not isinstance(self.max_candidate_refreshes, int)
            or not 1 <= self.max_candidate_refreshes <= self.max_revisions
        ):
            raise ValueError("candidate refresh must have a distinct action and a bounded count")
        if (
            not isinstance(self.finite_completion_policy, str)
            or self.finite_completion_policy
            not in {"raise", "deliver-latest-or-abstain"}
        ):
            raise ValueError("finite_completion_policy is invalid")
        if (
            not isinstance(self.context_fit_policy, str)
            or self.context_fit_policy not in {"raise", "compact-or-abstain"}
        ):
            raise ValueError("context_fit_policy is invalid")
        if (
            not isinstance(self.react_exhaustion_policy, str)
            or self.react_exhaustion_policy
            not in {"raise", "continue-without-answer"}
        ):
            raise ValueError("react_exhaustion_policy is invalid")
        if self.reviewer_verdict_vocabulary is not None and (
            not isinstance(self.reviewer_verdict_vocabulary, str)
            or not self.reviewer_verdict_vocabulary.strip()
        ):
            raise ValueError("reviewer_verdict_vocabulary must be None or a non-empty string")
        if (
            not isinstance(self.finite_completion_scope, str)
            or self.finite_completion_scope not in FINITE_COMPLETION_SCOPES
        ):
            raise ValueError("finite_completion_scope is invalid")
        if self.refresh_action == PLANNER_ACTION_ILLEGAL:
            # E8c: the illegal-output routing value is reserved.
            raise ValueError("candidate refresh must not use the reserved illegal action")
        if self.planner_output_format not in {"exact-text", "json-action-v1"}:
            raise ValueError("planner_output_format is invalid")
        if not isinstance(self.review_loop_enabled, bool):
            raise ValueError("review_loop_enabled must be a boolean")
        if not self.review_loop_enabled and self.max_revisions != 0:
            raise ValueError("review loop off requires max_revisions 0")
        if (
            isinstance(self.max_acquisitions, bool)
            or not isinstance(self.max_acquisitions, int)
            or not 0 <= self.max_acquisitions <= self.max_revisions
        ):
            # E18: an ACQUIRE spends a revision, exactly as a REVISE and a
            # candidate refresh do, so the acquisition allowance is bounded
            # by the revision allowance.
            raise ValueError("max_acquisitions must be bounded by max_revisions")


@dataclass(frozen=True)
class AcquisitionNodeSpec:
    """Configuration-bound identity of the episode's Acquisition node (E18)."""

    node_id: str
    policy_id: str
    kind: str

    def __post_init__(self) -> None:
        for name in ("node_id", "policy_id", "kind"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"acquisition {name} must be non-empty text")


class AcquisitionNode:
    """The episode's SIXTH node: ``acquire(action -> typed evidence)`` (E18).

    It is deliberately NOT a ``NativeRoleNode``.  A role node is a model
    contact wearing a graph position; the acquire primitive is the opposite
    -- one of its three registered kinds (``knowledge-requery``) makes NO
    contact at all, and the one that does (``speech-reobserve``) spends a
    Perception contact rather than a contact of its own seat.  What the graph
    needs from this node is therefore not a completion but a typed RECORD,
    and that is exactly what :meth:`acquire` returns.

    ``execute`` is the flight-owned callback ``rails.runner`` binds: it
    resolves the registered ``rails.acquisition.AcquisitionPolicy``, hands it
    the trajectory's own state plus whichever acquisition callback its kind
    requires, and seals the result into the episode's custody.  This class
    owns the graph contract and nothing else -- no store, no packet, no
    server, no scorer.

    The pre-E18 shape survives beside it: an acquisition node supplied as an
    ANALYTICAL ``NativeRoleNode`` still routes exactly as it always did
    (:meth:`NativeEpisodeWorkflow._build`), because that path is what the
    graph's own proofs pin and no configuration has ever been able to reach
    either one.
    """

    def __init__(self, *, spec: AcquisitionNodeSpec, execute) -> None:
        if not isinstance(spec, AcquisitionNodeSpec):
            raise ValueError("spec must be AcquisitionNodeSpec")
        if not callable(execute):
            raise ValueError("acquisition execute must be callable")
        self.spec = spec
        self._execute = execute

    async def acquire(self, state: Mapping[str, object]) -> Mapping[str, object]:
        result = await self._execute(copy.deepcopy(dict(state)))
        if not isinstance(result, Mapping):
            raise NativeEpisodeError("acquisition node did not return a record")
        return dict(result)

    async def close(self) -> None:
        """Symmetry with ``NativeRoleNode.close``; this node owns no
        framework resource, so closing it is a no-op the runner may call
        unconditionally."""

        return None


@dataclass(frozen=True)
class NativeEpisodeNodes:
    """Public framework role components used by the episode graph.

    ``reviewer`` and ``planner`` are ``None`` exactly when
    ``NativeEpisodeSpec.review_loop_enabled`` is ``False``: the review loop
    is off by configuration, so no Reviewer or Planner node is ever built,
    let alone contacted (:func:`build_native_episode` enforces the pairing).
    """

    perception: NativeRoleNode
    # E2b (SLURP v2 base program M2 live wiring): a ``GroupedSolverRoleNode``
    # here means the Solver role's registered ``samples >= 2``; ``rails.
    # runner._invoke_native_role_episode`` builds it in place of the plain
    # ``NativeRoleNode`` every other role (and a samples-1 Solver) keeps.
    # Item E42: or a ``reproduction.ojw.native_supply_variants.
    # SupplyVariantRoleNode`` when the Solver role declares an arm group; the
    # annotation stays the two concrete classes this module imports at top
    # level, and ``build_native_episode`` admits the third by name.
    solver: NativeRoleNode | GroupedSolverRoleNode
    reviewer: NativeRoleNode | None = None
    planner: NativeRoleNode | None = None
    # E18: an ``AcquisitionNode`` -- the node a configuration can now build --
    # or the pre-E18 analytical ``NativeRoleNode``, or None (every episode
    # with no acquisition node, which is every episode before E18).
    acquisition: NativeRoleNode | AcquisitionNode | None = None


class _InitialState(WorkflowComponent):
    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        query = inputs.get("original_query")
        candidates = inputs.get("candidates")
        if not isinstance(query, str) or not query:
            raise NativeEpisodeError("original_query must be non-empty text")
        if (
            not isinstance(candidates, Sequence)
            or isinstance(candidates, (str, bytes))
        ):
            raise NativeEpisodeError("candidates must be an ordered sequence")
        return {
            "state": {
                "original_query": query,
                "candidates": copy.deepcopy(tuple(candidates)),
                "perception": None,
                "latest_solver": None,
                "review": None,
                "plan": None,
                "acquisition": None,
                "revision_count": 0,
                "role_visits": [],
                "planner_routes": [],
                "accepted_solver_receipt": None,
            }
        }


@dataclass
class _RoleCheckpoint:
    """Invocation-local committed state immediately before one role contact."""

    state: dict[str, object] | None = None
    role_id: str | None = None
    stage: str | None = None

    def capture(
        self,
        *,
        state: Mapping[str, object],
        role_id: str,
        stage: str,
    ) -> None:
        self.state = copy.deepcopy(dict(state))
        self.role_id = role_id
        self.stage = stage


class _RoleQuery(WorkflowComponent):
    def __init__(
        self,
        role_id: str,
        stage: str,
        builder: RoleInputBuilder,
        checkpoint: _RoleCheckpoint,
    ) -> None:
        super().__init__()
        self._role_id = role_id
        self._stage = stage
        self._builder = builder
        self._checkpoint = checkpoint

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        self._checkpoint.capture(
            state=state,
            role_id=self._role_id,
            stage=self._stage,
        )
        query = self._builder(self._role_id, copy.deepcopy(state))
        if inspect.isawaitable(query):
            # Owner decision 159 (``rails.dispatch_slot_fill``,
            # ``role_input_offload``): the SAME builder, run off the shared
            # event loop. A synchronous builder -- every configuration that
            # does not arm the switch -- never reaches this line.
            query = await query
        if not isinstance(query, str) or not query:
            raise NativeEpisodeError(
                f"role input builder returned no query for {self._role_id!r}"
            )
        return {"state": state, "query": query}


def _planner_action(
    output: str,
    *,
    output_format: str,
    legal: set[str],
) -> tuple[str, dict[str, str] | None, str | None]:
    """Route one Planner output; never fail the flight on the Planner's text.

    E8c.  Returns ``(action, control, illegal_token)``.  For an output the
    configuration registers, ``action`` is that exact action, ``control`` is
    the parsed ``json-action-v1`` document (``None`` under ``exact-text``) and
    ``illegal_token`` is ``None`` -- byte-identical to every route taken
    before E8c.  For an output that names no registered action, or that is
    not the strict single-key action document ``json-action-v1`` requires,
    ``action`` is :data:`PLANNER_ACTION_ILLEGAL`, ``control`` is ``None`` and
    ``illegal_token`` is the exact text the caller seals by truncation and
    sha256.  The caller turns that into a row-level disposition: one
    malformed Planner token ends its own row, not the campaign.
    """
    if output_format == "exact-text":
        action = output
        control = None
        token = output
    else:
        def unique_object(pairs):
            document = {}
            for key, value in pairs:
                if key in document:
                    raise ValueError("Planner JSON action contains a duplicate key")
                document[key] = value
            return document

        try:
            document = json.loads(output, object_pairs_hook=unique_object)
        except (TypeError, ValueError):
            return PLANNER_ACTION_ILLEGAL, None, output
        if not isinstance(document, dict) or set(document) != {"action"}:
            return PLANNER_ACTION_ILLEGAL, None, output
        action = document["action"]
        if not isinstance(action, str) or not action:
            return PLANNER_ACTION_ILLEGAL, None, output
        control = {"action": action}
        token = action
    if action not in legal:
        return PLANNER_ACTION_ILLEGAL, None, token
    return action, control, None


def _append_reviewer_verdict(
    state: dict[str, object],
    *,
    visit: int,
    token: str | None,
    disposition: str,
    head: str | None,
) -> None:
    """E37: append one mark to ``reviewer_verdicts``, beside ``planner_routes``.

    Mutates ``state`` IN PLACE, exactly as the Planner-illegal and
    react-exhaustion marks beside it do, so a caller that already bound a
    result mapping to ``state`` (``{"state": updated}``, set before this
    branch runs) sees the mark without a second assignment.

    Called ONLY from the Reviewer's own ``_ApplyRole`` branch, and only when
    ``native_episode.reviewer_verdict`` is armed -- so an unarmed row never
    calls this, ``reviewer_verdicts`` never enters its state, and its sealed
    receipt stays byte-identical to its pre-E37 self.
    """

    marks = state.get(REVIEWER_VERDICTS_KEY)
    prior = (
        [dict(mark) for mark in marks]
        if isinstance(marks, Sequence) and not isinstance(marks, (str, bytes))
        else []
    )
    prior.append({"visit": visit, "token": token, "disposition": disposition, "head": head})
    state[REVIEWER_VERDICTS_KEY] = prior


class _ApplyRole(WorkflowComponent):
    def __init__(
        self,
        kind: str,
        actions: NativeEpisodeActions,
        refresh_action: str | None = None,
        planner_output_format: str = "exact-text",
        planner_actions: set[str] | None = None,
        react_exhaustion_policy: str = "raise",
        reviewer_verdict_vocabulary: str | None = None,
    ) -> None:
        super().__init__()
        self._kind = kind
        self._actions = actions
        self._refresh_action = refresh_action
        self._planner_output_format = planner_output_format
        self._planner_actions = planner_actions
        self._react_exhaustion_policy = react_exhaustion_policy
        # E37: handed to every stage, exactly as react_exhaustion_policy is;
        # only the Reviewer's own branch (self._kind == "review") ever reads
        # it, because reproduction.ojw.native_episode._build supplies it only
        # for that stage's _ApplyRole (see NativeEpisodeWorkflow._add_role).
        self._reviewer_verdict_vocabulary = reviewer_verdict_vocabulary

    def _react_exhaustion(self, role: Mapping[str, object]) -> Mapping[str, object] | None:
        """E22: this visit's exhaustion evidence when the armed policy admits
        it, else ``None`` (and the caller raises exactly as before E22).

        Four conditions, all required: the policy is armed, the stage is one
        whose finding the graph can do without
        (:data:`REACT_EXHAUSTION_STAGES`), the role node reported the class
        itself, and the block it reported is the shape this module seals.
        The node is the only place that can tell a ReAct exhaustion from any
        other non-answer, so this never re-derives that judgement from the
        output text.
        """

        if (
            self._react_exhaustion_policy != "continue-without-answer"
            or self._kind not in REACT_EXHAUSTION_STAGES
        ):
            return None
        block = role.get(REACT_EXHAUSTION_DISPOSITION)
        if not isinstance(block, Mapping):
            return None
        calls = block.get("calls")
        if (
            not isinstance(calls, Sequence)
            or isinstance(calls, (str, bytes))
            or not calls
            or not all(
                isinstance(call, Mapping)
                and isinstance(call.get("tool_id"), str)
                and call["tool_id"]
                and isinstance(call.get("arguments_sha256"), str)
                for call in calls
            )
        ):
            raise NativeEpisodeError(
                f"{self._kind} node reported a malformed ReAct exhaustion"
            )
        return block

    def _retained_exhaustion(
        self,
        state: Mapping[str, object],
        role: Mapping[str, object],
        block: Mapping[str, object],
    ) -> Output:
        """E22: end this visit with NO finding and let the row continue.

        Everything the visit actually spent stays in custody: its contacts
        are appended to ``role_visits`` exactly as an answering visit's are,
        because they were made, metered and traced. What does NOT happen is
        the finding: ``state[<stage>]`` becomes the empty string -- the same
        state the graph would hold if the role had reviewed and found
        nothing -- so the Planner's next query renders an empty findings
        block and routes on its own. Nothing is retried and no contact is
        spent here.
        """

        role_id = role.get("role_id")
        if not isinstance(role_id, str) or not role_id:
            raise NativeEpisodeError(f"{self._kind} node returned no role id")
        receipt = _execution_receipt(role)
        updated = dict(state)
        visits = updated.get("role_visits")
        if not isinstance(visits, Sequence) or isinstance(visits, (str, bytes)):
            raise NativeEpisodeError("episode state has invalid ordered role visits")
        revision_count = updated.get("revision_count")
        if isinstance(revision_count, bool) or not isinstance(revision_count, int):
            raise NativeEpisodeError("episode state has invalid revision count")
        updated_visits = [copy.deepcopy(visit) for visit in visits]
        updated_visits.append(
            {
                "role_id": role_id,
                "stage": self._kind,
                "execution_receipt": copy.deepcopy(receipt),
            }
        )
        updated["role_visits"] = updated_visits
        updated[self._kind] = ""
        record = {
            "role_id": role_id,
            "stage": self._kind,
            "role_visit_index": len(updated_visits) - 1,
            "revision_count": revision_count,
            "iterations_used": block.get("iterations_used"),
            "max_iterations": block.get("max_iterations"),
            "identical_calls": bool(block.get("identical_calls")),
            "calls": [
                {
                    "tool_id": call["tool_id"],
                    "arguments_sha256": call["arguments_sha256"],
                }
                for call in block["calls"]
            ],
            "last_observation_sha256": block.get("last_observation_sha256"),
        }
        prior: list[object] = []
        mark = updated.get(REACT_EXHAUSTION_DISPOSITION)
        if isinstance(mark, Mapping):
            seen = mark.get("visits")
            if isinstance(seen, Sequence) and not isinstance(seen, (str, bytes)):
                prior = [copy.deepcopy(item) for item in seen]
        updated[REACT_EXHAUSTION_DISPOSITION] = {
            "schema": REACT_EXHAUSTION_SCHEMA,
            "count": len(prior) + 1,
            "visits": [*prior, record],
        }
        if self._kind == "review" and self._reviewer_verdict_vocabulary is not None:
            # E37: the exhausted visit asserted no primitive at all -- no
            # token, no head, just the disposition the Reviewer's own
            # react_exhaustion mark already carries above. ``visit`` is the
            # Reviewer's OWN 0-based visit count (see the note beside the
            # legal/illegal branch below for why, and why that is exactly
            # the revision round index for this graph's one-reviewer-per-
            # round shape).
            _append_reviewer_verdict(
                updated,
                visit=sum(1 for v in updated_visits if v["stage"] == self._kind) - 1,
                token=None,
                disposition=REACT_EXHAUSTION_DISPOSITION,
                head=None,
            )
        return {"state": updated}

    def _record_truncation(self, updated, updated_visits, block) -> None:
        """Item E39: mark the visit whose completion was truncated.

        The node decided the tolerance (only a NON-answering role of an
        ``answering-node`` episode can carry the mark at all); this records
        it, twice and consistently: ``truncated`` on the visit itself, so a
        reader walking ``role_visits`` sees it without a second lookup, and
        one ordered ``truncation_events`` record binding that visit index to
        the contact digests the truncation actually happened on. Ids, digests
        and counts only -- never text.
        """

        if self._kind == ANSWERING_STAGE:
            # The answering node's truncation is item E13's own case and can
            # never be tolerated; a mark here is a wiring defect, not a row.
            raise NativeEpisodeError(
                "the answering stage cannot report a tolerated truncation"
            )
        contact = block.get("contact") if isinstance(block, Mapping) else None
        role_id = updated_visits[-1]["role_id"]
        if (
            not isinstance(block, Mapping)
            or block.get("finish_reason") != "length"
            or block.get("role_id") != role_id
            or not isinstance(contact, Mapping)
            or not contact
        ):
            raise NativeEpisodeError(
                f"{self._kind} node reported a malformed length truncation"
            )
        revision_count = updated.get("revision_count")
        if isinstance(revision_count, bool) or not isinstance(revision_count, int):
            raise NativeEpisodeError("episode state has invalid revision count")
        updated_visits[-1]["truncated"] = True
        prior: list[object] = []
        mark = updated.get(TRUNCATION_EVENTS)
        if isinstance(mark, Mapping):
            seen = mark.get("events")
            if isinstance(seen, Sequence) and not isinstance(seen, (str, bytes)):
                prior = [copy.deepcopy(item) for item in seen]
        record = {
            "role_id": role_id,
            "stage": self._kind,
            "role_visit_index": len(updated_visits) - 1,
            "revision_count": revision_count,
            "finish_reason": "length",
            "contact": copy.deepcopy(dict(contact)),
        }
        updated[TRUNCATION_EVENTS] = {
            "schema": TRUNCATION_EVENTS_SCHEMA,
            "count": len(prior) + 1,
            "events": [*prior, record],
        }

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        role = inputs.get("role")
        if not isinstance(role, Mapping):
            raise NativeEpisodeError(f"{self._kind} node did not return an answer")
        exhausted = None
        if role.get("result_type") != "answer":
            exhausted = self._react_exhaustion(role)
            if exhausted is None:
                raise NativeEpisodeError(
                    f"{self._kind} node did not return an answer"
                )
            return self._retained_exhaustion(state, role, exhausted)
        output = role.get("actor_output")
        if not isinstance(output, str) or not output:
            raise NativeEpisodeError(f"{self._kind} node returned no actor output")
        role_id = role.get("role_id")
        if not isinstance(role_id, str) or not role_id:
            raise NativeEpisodeError(f"{self._kind} node returned no role id")
        receipt = _execution_receipt(role)
        updated = dict(state)
        visits = updated.get("role_visits")
        if not isinstance(visits, Sequence) or isinstance(visits, (str, bytes)):
            raise NativeEpisodeError("episode state has invalid ordered role visits")
        updated_visits = [copy.deepcopy(visit) for visit in visits]
        updated_visits.append(
            {
                "role_id": role_id,
                "stage": self._kind,
                "execution_receipt": copy.deepcopy(receipt),
            }
        )
        updated["role_visits"] = updated_visits
        truncation = role.get(LENGTH_TRUNCATION_MARK)
        if truncation is not None:
            self._record_truncation(updated, updated_visits, truncation)
        result: dict[str, object] = {"state": updated}
        if self._kind == "solver":
            if role.get("delivery_eligible") is not True:
                raise NativeEpisodeError("episode has no valid Solver draft")
            new_solver = dict(role)
            if "supply_variants" not in new_solver:
                # Item E42b (owner decision 172, merge set B, arm_visits
                # "first"): a revisit contacts the delivering arm alone and
                # carries no arm custody of its own, so the visit-0 receipt --
                # the one that actually describes every declared arm -- is
                # carried forward rather than lost when this visit's own role
                # result overwrites the prior one. A plain (non-arm-grouped)
                # episode's ``latest_solver`` never carries the key either
                # way, so this branch is unreachable and every such episode's
                # state stays byte-identical.
                previous_solver = state.get("latest_solver")
                if (
                    isinstance(previous_solver, Mapping)
                    and "supply_variants" in previous_solver
                ):
                    new_solver["supply_variants"] = previous_solver["supply_variants"]
            updated["latest_solver"] = new_solver
        elif self._kind == "perception":
            # Same-flight instrument, PHASE 2 (merge set C, design docs/
            # superpowers/specs/2026-09-28-same-flight-instrument-phase2-
            # perception-variants-design.md): ``latest_solver``'s own twin.
            # Perception has exactly one visit per row (max_iterations 1, no
            # refresh -- design section 3, "Branch visits"), so there is no
            # revisit-carry-forward rule to state: this always runs exactly
            # once, and ``role`` already carries the WHOLE role result,
            # including ``perception_branches`` when
            # ``PerceptionBranchRoleNode`` produced it. ``rails.runner``
            # reads this off the graph's final state to seal the branch
            # receipt under ``native_episode_receipt.perception_branches``;
            # an unbranched Perception visit carries no such key, so this
            # branch is a byte-identical no-op for every episode written
            # before phase 2.
            #
            # ``updated[self._kind] = output`` is the SAME assignment the
            # generic ``else`` branch below makes for every stage that is
            # not solver/perception/planner (e.g. "review") -- restated here,
            # not skipped, because this ``elif`` intercepts "perception"
            # before that branch is ever reached, and downstream prompts
            # read ``state["perception"]`` as plain text (found live: this
            # was dropped in an earlier revision of this change, which
            # left ``state["perception"]`` at its initial ``None`` and broke
            # test_ojw_native_episode.py::
            # test_refresh_revisits_perception_then_solver_and_preserves_
            # both_receipts).
            updated["latest_perception"] = dict(role)
            updated[self._kind] = output
        elif self._kind == "planner":
            # E15: NativeEpisodeWorkflow always supplies `planner_actions` for
            # a Planner node, and that graph-derived set is the authority.
            # The literal set below survives only for a node constructed
            # directly, outside a workflow, which cannot know whether an
            # acquisition node exists.
            legal = {
                self._actions.accept,
                self._actions.revise,
                self._actions.acquire,
            }
            if self._refresh_action is not None:
                legal.add(self._refresh_action)
            if self._planner_actions is not None:
                legal = set(self._planner_actions)
            action, control, illegal_token = _planner_action(
                output, output_format=self._planner_output_format, legal=legal
            )
            updated["plan"] = output
            if control is not None:
                updated["planner_control"] = control
            elif illegal_token is not None:
                # E8c: an illegal final route must never leave an EARLIER
                # visit's structured control standing beside it, or the raw
                # source custody check would bind the wrong route.
                updated.pop("planner_control", None)
            routes = updated.get("planner_routes")
            if not isinstance(routes, Sequence) or isinstance(
                routes, (str, bytes)
            ):
                raise NativeEpisodeError("episode state has invalid Planner routes")
            updated_routes = [copy.deepcopy(route) for route in routes]
            record: dict[str, object] = {
                "role_visit_index": len(updated_visits) - 1,
                "revision_count": int(updated["revision_count"]),
                "action": action,
            }
            if illegal_token is not None:
                # E8c: this row's own disposition.  The route keeps at most
                # PLANNER_ACTION_RECORD_CHARS of the token plus its sha256
                # over the WHOLE token, so an auditor can bind it to the
                # Planner visit's response_text_sha256 (identical under
                # exact-text) without the receipt carrying the text.
                digest = hashlib.sha256(illegal_token.encode("utf-8")).hexdigest()
                record["action"] = illegal_token[:PLANNER_ACTION_RECORD_CHARS]
                record["legal"] = False
                record["disposition"] = PLANNER_ACTION_ILLEGAL_DISPOSITION
                record["action_sha256"] = digest
                record["action_chars"] = len(illegal_token)
                prior: list[str] = []
                mark = updated.get(PLANNER_ACTION_ILLEGAL_DISPOSITION)
                if isinstance(mark, Mapping):
                    seen = mark.get("action_sha256")
                    if isinstance(seen, Sequence) and not isinstance(seen, (str, bytes)):
                        prior = [str(item) for item in seen]
                updated[PLANNER_ACTION_ILLEGAL_DISPOSITION] = {
                    "schema": PLANNER_ACTION_ILLEGAL_SCHEMA,
                    "count": len(prior) + 1,
                    "action_sha256": [*prior, digest],
                }
            updated_routes.append(record)
            updated["planner_routes"] = updated_routes
            result["action"] = action
        else:
            updated[self._kind] = output
            if self._kind == "review" and self._reviewer_verdict_vocabulary is not None:
                # E37: parse-only -- state[self._kind] (the raw text the
                # Planner's query renders) is already set above and is NEVER
                # rewritten here; only the receipt mark below is derived from
                # the parse. ``visit`` is the Reviewer's OWN 0-based visit
                # count, NOT the global role_visits index Planner routes key
                # on (``role_visit_index``): this graph builds exactly one
                # Reviewer visit per revision round, so the Reviewer's own
                # count IS that round's index, and a reader can therefore
                # index ``planner_routes[visit]`` directly to read the same
                # round's route -- which is what the verifier script's
                # "Planner route conditioned on the token" reading needs.
                token, _rationale, head = parse_review_primitive(output)
                legal = token != REVIEW_VERDICT_ILLEGAL
                _append_reviewer_verdict(
                    updated,
                    visit=sum(1 for v in updated_visits if v["stage"] == self._kind) - 1,
                    token=token if legal else None,
                    disposition=(
                        REVIEWER_VERDICT_LEGAL if legal
                        else REVIEWER_VERDICT_ILLEGAL_DISPOSITION
                    ),
                    head=None if legal else head,
                )
        return result


class _AdvanceRevision(WorkflowComponent):
    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        updated = dict(state)
        updated["revision_count"] = int(updated["revision_count"]) + 1
        return {"state": updated}


class _AdvanceCandidateRefresh(WorkflowComponent):
    def __init__(self, limit: int) -> None:
        super().__init__()
        self._limit = limit

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        count = state.get("candidate_refresh_count", 0)
        if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count < self._limit:
            raise NativeEpisodeError("episode candidate refresh limit is exhausted")
        updated = dict(state)
        updated["revision_count"] = int(updated["revision_count"]) + 1
        updated["candidate_refresh_count"] = count + 1
        return {"state": updated}


class _Acquire(WorkflowComponent):
    """E18: run the Acquisition node once and bind its record into state.

    One visit registers exactly one ``role_visits`` entry of stage
    ``acquisition`` carrying the acquisition receipt (and, for a kind that
    spent a contact, that contact's own execution receipt), appends the
    record to ``acquisitions`` in visit order, and leaves ``acquisition``
    holding the latest record -- the shape the pre-E18 analytical path also
    wrote to, so a reader of episode state finds the sixth node's output
    where it has always looked for it.
    """

    def __init__(self, node: AcquisitionNode, checkpoint: _RoleCheckpoint) -> None:
        super().__init__()
        self._node = node
        self._checkpoint = checkpoint

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        # A contact-spending acquisition kind makes its contact inside this
        # component, so the invocation-local checkpoint a finite completion
        # is resolved against must name THIS node, exactly as
        # ``_RoleQuery`` names the role whose contact it is about to make.
        self._checkpoint.capture(
            state=state,
            role_id=self._node.spec.node_id,
            stage=ACQUISITION_STAGE,
        )
        record = await self._node.acquire(state)
        receipt = {
            key: value for key, value in record.items()
            if key != "execution_receipt"
        }
        if set(receipt) != ACQUISITION_RECORD_KEYS:
            raise NativeEpisodeError("acquisition record has unknown or missing fields")
        if receipt["policy_id"] != self._node.spec.policy_id:
            raise NativeEpisodeError("acquisition record names a different policy")
        if receipt["kind"] != self._node.spec.kind:
            raise NativeEpisodeError("acquisition record names a different kind")
        contacts = receipt["contacts_used"]
        if isinstance(contacts, bool) or not isinstance(contacts, int) or contacts < 0:
            raise NativeEpisodeError("acquisition record has invalid contacts_used")
        updated = dict(state)
        visits = updated.get("role_visits")
        if not isinstance(visits, Sequence) or isinstance(visits, (str, bytes)):
            raise NativeEpisodeError("episode state has invalid ordered role visits")
        visit: dict[str, object] = {
            "role_id": self._node.spec.node_id,
            "stage": ACQUISITION_STAGE,
            "acquisition_receipt": copy.deepcopy(receipt),
        }
        if contacts:
            # A contact-spending kind must name the contact it spent, through
            # the SAME normalisation every role visit's receipt takes, so an
            # auditor binds it to a real request/response pair exactly as it
            # binds a Solver's.
            visit["execution_receipt"] = _execution_receipt(record)
        elif "execution_receipt" in record:
            raise NativeEpisodeError(
                "a zero-contact acquisition cannot carry an execution receipt"
            )
        updated["role_visits"] = [
            copy.deepcopy(entry) for entry in visits
        ] + [visit]
        history = updated.get("acquisitions")
        if history is None:
            history = []
        elif not isinstance(history, Sequence) or isinstance(history, (str, bytes)):
            raise NativeEpisodeError("episode state has invalid acquisition history")
        updated["acquisitions"] = [
            copy.deepcopy(entry) for entry in history
        ] + [copy.deepcopy(receipt)]
        updated["acquisition"] = copy.deepcopy(receipt)
        return {"state": updated}


class _Accept(WorkflowComponent):
    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        solver = state.get("latest_solver")
        if not isinstance(solver, Mapping) or solver.get("delivery_eligible") is not True:
            raise NativeEpisodeError("explicit accept has no valid Solver draft")
        updated = dict(state)
        updated["accepted_solver_receipt"] = _execution_receipt(solver)
        return {"state": updated, "delivery": dict(solver)}


class _Exhausted(WorkflowComponent):
    def __init__(self, message: str = "episode revision limit is exhausted") -> None:
        super().__init__()
        self._message = message

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        raise NativeEpisodeError(self._message)


class _TerminalDelivery(WorkflowComponent):
    """Deliver the final Solver draft under an explicit terminal policy."""

    def __init__(
        self,
        actions: NativeEpisodeActions,
        refresh_action: str | None = None,
        planner_output_format: str = "exact-text",
    ) -> None:
        super().__init__()
        self._actions = actions
        self._refresh_action = refresh_action
        self._planner_output_format = planner_output_format

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        solver = state.get("latest_solver")
        if not isinstance(solver, Mapping) or solver.get("delivery_eligible") is not True:
            raise NativeEpisodeError("terminal delivery has no valid Solver draft")
        planner_action = state.get("plan")
        if self._planner_output_format == "json-action-v1":
            control = state.get("planner_control")
            if not isinstance(control, Mapping) or set(control) != {"action"}:
                raise NativeEpisodeError("terminal delivery has no parsed Planner control")
            planner_action = control["action"]
        terminal_actions = {self._actions.revise, self._actions.acquire}
        if self._refresh_action is not None:
            terminal_actions.add(self._refresh_action)
        if planner_action not in terminal_actions:
            raise NativeEpisodeError("terminal delivery has no revision-limit action")
        revision_count = state.get("revision_count")
        if isinstance(revision_count, bool) or not isinstance(revision_count, int):
            raise NativeEpisodeError("terminal delivery has invalid revision count")
        updated = dict(state)
        updated.pop("accepted_solver_receipt", None)
        updated["terminal_solver_receipt"] = _execution_receipt(solver)
        updated["terminal_disposition"] = {
            "reason": "revision_limit",
            "planner_action": planner_action,
            "revision_count": revision_count,
            "planner_accepted": False,
        }
        return {"state": updated, "delivery": dict(solver)}


def _state(inputs: Mapping[str, object]) -> dict[str, object]:
    state = inputs.get("state")
    if not isinstance(state, Mapping):
        raise NativeEpisodeError("workflow stage is missing episode state")
    return copy.deepcopy(dict(state))


def _execution_receipt(role: Mapping[str, object]) -> dict[str, object]:
    receipt = role.get("execution_receipt")
    if not isinstance(receipt, Mapping):
        raise NativeEpisodeError("role result is missing its execution receipt")
    contacts = receipt.get("contacts")
    if (
        not isinstance(contacts, Sequence)
        or isinstance(contacts, (str, bytes))
        or not contacts
    ):
        raise NativeEpisodeError("role execution receipt has no ordered contacts")
    fields = (
        "agent_contact_id",
        "request_id",
        "request_sha256",
        "response_sha256",
        "response_text_sha256",
    )
    normalized: list[dict[str, str]] = []
    for contact in contacts:
        if not isinstance(contact, Mapping):
            raise NativeEpisodeError("role execution contact must be an object")
        selected: dict[str, str] = {}
        for field in fields:
            value = contact.get(field)
            if not isinstance(value, str) or not value:
                raise NativeEpisodeError(
                    f"role execution contact has invalid {field}"
                )
            if field.endswith("sha256") and (
                len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise NativeEpisodeError(
                    f"role execution contact has invalid {field}"
                )
            selected[field] = value
        normalized.append(selected)
    final = receipt.get("final_contact")
    if not isinstance(final, Mapping) or any(
        final.get(field) != normalized[-1][field] for field in fields
    ):
        raise NativeEpisodeError(
            "role execution receipt final contact does not match its last contact"
        )
    return {"contacts": normalized, "final_contact": dict(normalized[-1])}


def _finite_error_in_chain(
    error: BaseException,
) -> FrozenCoreRoleFiniteCompletionError | None:
    cause: BaseException | None = error
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        if isinstance(cause, FrozenCoreRoleFiniteCompletionError):
            return cause
        if isinstance(cause, FrozenCoreRoleModelError):
            return None
        seen.add(id(cause))
        cause = cause.__cause__ or cause.__context__
    return None


def _finite_terminal_outcome(
    error: FrozenCoreRoleFiniteCompletionError,
    checkpoint: _RoleCheckpoint,
    scope: str = "episode",
) -> dict[str, object]:
    if (
        checkpoint.state is None
        or checkpoint.role_id is None
        or checkpoint.stage is None
    ):
        raise NativeEpisodeError(
            "finite completion has no invocation-local role checkpoint"
        )
    error_role_id = getattr(error, "role_id", None)
    if error_role_id != checkpoint.role_id:
        raise NativeEpisodeError(
            "finite completion role does not match its role checkpoint"
        )
    completion = error.completion
    rejected_contact = {
        "agent_contact_id": completion.agent_contact_id,
        "request_id": completion.request_id,
        "request_sha256": completion.request_sha256,
        "response_sha256": completion.response_sha256,
        "response_text_sha256": completion.response_text_sha256,
    }
    normalized_rejected = _execution_receipt(
        {
            "execution_receipt": {
                "contacts": [rejected_contact],
                "final_contact": rejected_contact,
            }
        }
    )["final_contact"]
    interrupted_receipt = getattr(error, "execution_receipt", None)
    if not isinstance(interrupted_receipt, Mapping):
        raise NativeEpisodeError(
            "finite completion has no interrupted execution receipt"
        )
    normalized_interrupted = _execution_receipt(
        {"execution_receipt": interrupted_receipt}
    )
    if normalized_interrupted["final_contact"] != normalized_rejected:
        raise NativeEpisodeError(
            "finite completion contact does not match interrupted role receipt"
        )

    state = copy.deepcopy(checkpoint.state)
    revision_count = state.get("revision_count")
    if isinstance(revision_count, bool) or not isinstance(revision_count, int):
        raise NativeEpisodeError(
            "finite completion checkpoint has invalid revision count"
        )
    state.pop("accepted_solver_receipt", None)
    state["interrupted_role"] = {
        "role_id": checkpoint.role_id,
        "stage": checkpoint.stage,
        "execution_receipt": copy.deepcopy(dict(interrupted_receipt)),
    }
    disposition = {
        "reason": "finite_completion",
        "finish_reason": error.finish_reason,
        "role_id": checkpoint.role_id,
        "stage": checkpoint.stage,
        "revision_count": revision_count,
        "planner_accepted": False,
        "rejected_contact": dict(normalized_rejected),
    }
    if scope != "episode":
        # Item E39: WHICH rule ended this row. Written only under the armed
        # scope, so every row sealed before E39 -- and every ``"episode"``
        # row after it -- carries exactly the seven keys it always did.
        disposition["scope"] = scope
    state["terminal_disposition"] = disposition

    solver = state.get("latest_solver")
    if isinstance(solver, Mapping) and solver.get("delivery_eligible") is True:
        _execution_receipt(solver)
        exact_receipt = solver.get("execution_receipt")
        if not isinstance(exact_receipt, Mapping):
            raise NativeEpisodeError(
                "finite completion latest Solver has no execution receipt"
            )
        state.pop("abstention_receipt", None)
        state["terminal_solver_receipt"] = copy.deepcopy(dict(exact_receipt))
        delivery = copy.deepcopy(dict(solver))
    else:
        state.pop("terminal_solver_receipt", None)
        state["abstention_receipt"] = {
            "source_contact": dict(normalized_rejected),
        }
        delivery = {
            "actor_output": "",
            "result_type": "abstention",
            "delivery_eligible": False,
        }
    return {"state": state, "delivery": delivery}


def _seal_refusal_error_in_chain(error: BaseException) -> RailsRunnerError | None:
    """Item E43 (2026-09-28, coordinator ruling on
    ``docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md``): the
    seal's refusal of an otherwise-authoritative completion, inside a
    framework error chain, if any.

    Mirrors :func:`_finite_error_in_chain`'s stop rule: an ordinary
    :class:`RailsRunnerError` the seal raises for its OWN invariants (never
    a per-row disposition -- a bad plan, a lost contact, a repeated
    identity) ends the walk before it can reach a seal refusal buried
    deeper in the chain, so a real runner defect is never rewritten into a
    retained row. Only a :class:`RailsRunnerError` ``capture_completion``
    (``rails.runner``) itself tagged with ``seal_refusal_completion`` --
    the completion a structured-output contract's parser refused -- is ever
    returned.
    """

    cause: BaseException | None = error
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        if isinstance(cause, RailsRunnerError):
            if getattr(cause, "seal_refusal_completion", None) is not None:
                return cause
            return None
        seen.add(id(cause))
        cause = cause.__cause__ or cause.__context__
    return None


def _seal_refusal_terminal_outcome(
    error: RailsRunnerError,
    checkpoint: _RoleCheckpoint,
) -> dict[str, object]:
    """Item E43: retain the row whose deciding completion the seal refused.

    Built to the E13 contract (:func:`_finite_terminal_outcome`) with the
    difference the facts force: the refused completion never reached
    ``capture_completion``'s own custody bookkeeping (the seal refused it
    before that ran), so there is no earlier contact of this visit to
    cross-check it against -- the interrupted role's execution receipt
    carries exactly the one rejected contact. The row delivers its latest
    delivery-eligible Solver draft, or abstains, exactly as a finite
    completion does. The refusal's exception class and message are recorded
    verbatim under ``seal_refusal``; nothing else about the refused
    completion -- never its answer bytes -- enters the receipt.
    """

    if (
        checkpoint.state is None
        or checkpoint.role_id is None
        or checkpoint.stage is None
    ):
        raise NativeEpisodeError(
            "seal refusal has no invocation-local role checkpoint"
        )
    completion = getattr(error, "seal_refusal_completion", None)
    error_role_id = getattr(error, "seal_refusal_role_id", None)
    if completion is None or error_role_id != checkpoint.role_id:
        raise NativeEpisodeError(
            "seal refusal role does not match its role checkpoint"
        )
    if getattr(completion, "finish_reason", None) != "stop":
        raise NativeEpisodeError(
            "seal refusal did not refuse an authoritative stop completion"
        )
    rejected_contact = {
        "agent_contact_id": completion.agent_contact_id,
        "request_id": completion.request_id,
        "request_sha256": completion.request_sha256,
        "response_sha256": completion.response_sha256,
        "response_text_sha256": completion.response_text_sha256,
    }
    normalized_rejected = _execution_receipt(
        {
            "execution_receipt": {
                "contacts": [rejected_contact],
                "final_contact": rejected_contact,
            }
        }
    )["final_contact"]

    state = copy.deepcopy(checkpoint.state)
    revision_count = state.get("revision_count")
    if isinstance(revision_count, bool) or not isinstance(revision_count, int):
        raise NativeEpisodeError(
            "seal refusal checkpoint has invalid revision count"
        )
    state.pop("accepted_solver_receipt", None)
    state["interrupted_role"] = {
        "role_id": checkpoint.role_id,
        "stage": checkpoint.stage,
        "execution_receipt": {
            "contacts": [dict(normalized_rejected)],
            "final_contact": dict(normalized_rejected),
        },
    }
    state["terminal_disposition"] = {
        "reason": SEAL_REFUSAL_DISPOSITION,
        "role_id": checkpoint.role_id,
        "stage": checkpoint.stage,
        "revision_count": revision_count,
        "planner_accepted": False,
        "rejected_contact": dict(normalized_rejected),
        # Class name and message text only -- never the refused answer's
        # own bytes, which never leave ``error``/``completion`` at all.
        "seal_refusal": {
            "error_class": type(error).__name__,
            "message": str(error),
        },
    }

    solver = state.get("latest_solver")
    if isinstance(solver, Mapping) and solver.get("delivery_eligible") is True:
        _execution_receipt(solver)
        exact_receipt = solver.get("execution_receipt")
        if not isinstance(exact_receipt, Mapping):
            raise NativeEpisodeError(
                "seal refusal latest Solver has no execution receipt"
            )
        state.pop("abstention_receipt", None)
        state["terminal_solver_receipt"] = copy.deepcopy(dict(exact_receipt))
        delivery = copy.deepcopy(dict(solver))
    else:
        state.pop("terminal_solver_receipt", None)
        state["abstention_receipt"] = {
            "source_contact": dict(normalized_rejected),
        }
        delivery = {
            "actor_output": "",
            "result_type": "abstention",
            "delivery_eligible": False,
        }
    return {"state": state, "delivery": delivery}


def _context_fit_error_in_chain(
    error: BaseException,
) -> FrozenCoreRoleContextFitError | None:
    """E20: the context-fit refusal inside a framework error chain, if any.

    Mirrors :func:`_finite_error_in_chain`, including its stop rule: a
    plain :class:`FrozenCoreRoleModelError` that is NOT a context-fit
    refusal ends the walk, so an ordinary bridge refusal is never rewritten
    into a retained row.
    """

    cause: BaseException | None = error
    seen: set[int] = set()
    while cause is not None and id(cause) not in seen:
        if isinstance(cause, FrozenCoreRoleContextFitError):
            return cause
        if isinstance(cause, FrozenCoreRoleModelError):
            return None
        seen.add(id(cause))
        cause = cause.__cause__ or cause.__context__
    return None


def _context_fit_terminal_outcome(
    error: FrozenCoreRoleContextFitError,
    checkpoint: _RoleCheckpoint,
) -> dict[str, object]:
    """E20: retain the row whose next request would not fit the slot.

    Built to the E13 contract (:func:`_finite_terminal_outcome`) with one
    difference that is forced by the facts: there is no rejected contact,
    because the refused request produced no completion. The latest
    delivery-eligible Solver draft is delivered; with none, the row
    abstains, and its abstention receipt names the refusing seam rather
    than a contact that does not exist.
    """

    if (
        checkpoint.state is None
        or checkpoint.role_id is None
        or checkpoint.stage is None
    ):
        raise NativeEpisodeError(
            "context-fit refusal has no invocation-local role checkpoint"
        )
    error_role_id = getattr(error, "role_id", None)
    if error_role_id != checkpoint.role_id:
        raise NativeEpisodeError(
            "context-fit refusal role does not match its role checkpoint"
        )
    state = copy.deepcopy(checkpoint.state)
    revision_count = state.get("revision_count")
    if isinstance(revision_count, bool) or not isinstance(revision_count, int):
        raise NativeEpisodeError(
            "context-fit checkpoint has invalid revision count"
        )
    state.pop("accepted_solver_receipt", None)
    interrupted_receipt = getattr(error, "execution_receipt", None)
    interrupted: dict[str, object] = {
        "role_id": checkpoint.role_id,
        "stage": checkpoint.stage,
    }
    if isinstance(interrupted_receipt, Mapping):
        normalized = _execution_receipt(
            {"execution_receipt": interrupted_receipt}
        )
        interrupted["execution_receipt"] = normalized
    state["interrupted_role"] = interrupted
    state["terminal_disposition"] = terminal_context_disposition(
        role_id=checkpoint.role_id,
        stage=checkpoint.stage,
        revision_count=revision_count,
        compaction_pass=error.compaction_pass,
        dropped_identifiers=error.dropped_identifiers,
        tokens_before=error.tokens_before,
        tokens_after=error.tokens_after,
        limit_tokens=error.limit_tokens,
        source=error.source,
        server_message=error.server_message,
    )

    solver = state.get("latest_solver")
    if isinstance(solver, Mapping) and solver.get("delivery_eligible") is True:
        _execution_receipt(solver)
        exact_receipt = solver.get("execution_receipt")
        if not isinstance(exact_receipt, Mapping):
            raise NativeEpisodeError(
                "context-fit refusal latest Solver has no execution receipt"
            )
        state.pop("abstention_receipt", None)
        state["terminal_solver_receipt"] = copy.deepcopy(dict(exact_receipt))
        delivery = copy.deepcopy(dict(solver))
    else:
        state.pop("terminal_solver_receipt", None)
        state["abstention_receipt"] = {
            "source_contact": None,
            "reason": CONTEXT_COMPACTION_DISPOSITION,
            "source": error.source,
        }
        delivery = {
            "actor_output": "",
            "result_type": "abstention",
            "delivery_eligible": False,
        }
    return {"state": state, "delivery": delivery}


def _first_available_state(component_ids: Sequence[str]):
    ids = tuple(component_ids)

    def select(outputs: Mapping[str, object]) -> dict[str, object]:
        for component_id in ids:
            value = outputs.get(component_id)
            if isinstance(value, Mapping) and isinstance(value.get("state"), Mapping):
                return {"state": copy.deepcopy(value["state"])}
        raise NativeEpisodeError("conditional workflow branch supplied no state")

    return select


def _first_accept(component_ids: Sequence[str]):
    ids = tuple(component_ids)

    def select(outputs: Mapping[str, object]) -> dict[str, object]:
        for component_id in ids:
            value = outputs.get(component_id)
            if isinstance(value, Mapping) and "delivery" in value:
                return {"accepted": copy.deepcopy(value)}
        raise NativeEpisodeError("workflow ended without explicit acceptance")

    return select


class NativeEpisodeWorkflow:
    """Callable facade that builds a fresh public Workflow for each episode."""

    def __init__(
        self,
        *,
        spec: NativeEpisodeSpec,
        nodes: NativeEpisodeNodes,
        role_input_builder: RoleInputBuilder,
    ) -> None:
        self.spec = spec
        self.nodes = nodes
        self._role_input_builder = role_input_builder
        # E15 (finding I-1 of the 2026-09-19 SLURP agent base-lock draft):
        # this set is THE legal Planner action set for every episode this
        # workflow builds, under both output formats.  ACQUIRE is in it only
        # when an acquisition node was actually supplied, because an episode
        # built without one has no route that can execute an ACQUIRE.
        self._planner_actions = {spec.actions.accept, spec.actions.revise}
        if nodes.acquisition is not None:
            self._planner_actions.add(spec.actions.acquire)
        if spec.refresh_action is not None:
            self._planner_actions.add(spec.refresh_action)

    def _add_role(
        self,
        workflow: Workflow,
        checkpoint: _RoleCheckpoint,
        *,
        stage_id: str,
        node: NativeRoleNode,
        predecessors: Sequence[str],
        kind: str,
    ) -> str:
        query_id = f"{stage_id}_input"
        role_id = f"{stage_id}_role"
        apply_id = f"{stage_id}_state"
        workflow.add_workflow_comp(
            query_id,
            _RoleQuery(
                node.spec.role_id,
                kind,
                self._role_input_builder,
                checkpoint,
            ),
            wait_for_all=False,
            inputs_schema=_first_available_state(predecessors),
        )
        for predecessor in predecessors:
            workflow.add_connection(predecessor, query_id)
        workflow.add_workflow_comp(
            role_id,
            node,
            inputs_schema={"query": "${" + query_id + ".query}"},
        )
        workflow.add_connection(query_id, role_id)
        workflow.add_workflow_comp(
            apply_id,
            _ApplyRole(
                kind,
                self.spec.actions,
                self.spec.refresh_action,
                self.spec.planner_output_format,
                # E15.  Before E15 this set reached _ApplyRole only under
                # `json-action-v1`; under the flown `exact-text` the node fell
                # back to {accept, revise, acquire} and called ACQUIRE legal
                # even on an episode with no acquisition node.  Such a token
                # then routed into
                # `_Exhausted("episode has no configured analytical
                # acquisition role")`, which RAISES and takes the whole flight
                # with it -- exactly the failure class E8c removed for
                # unregistered Planner tokens.  Passing the graph's own set
                # under both formats makes an ACQUIRE on such an episode an
                # illegal Planner output, so the E8c path RETAINS the row.  An
                # episode that does carry an acquisition node keeps ACQUIRE in
                # this set and every byte of its behaviour.
                self._planner_actions if kind == "planner" else None,
                # E22: the spec's own key, handed to every stage. Only the
                # stages in REACT_EXHAUSTION_STAGES can act on it, and with
                # the key at its default ``"raise"`` no stage can.
                self.spec.react_exhaustion_policy,
                # E37: only the Reviewer's own branch (kind == "review") ever
                # reads this; every other stage gets None regardless of what
                # the spec carries, exactly as `planner_actions` above is
                # None for every stage but the Planner's.
                self.spec.reviewer_verdict_vocabulary if kind == "review" else None,
            ),
            inputs_schema={
                "state": "${" + query_id + ".state}",
                "role": "${" + role_id + "}",
            },
        )
        workflow.add_connection(role_id, apply_id)
        return apply_id

    def _build(self, checkpoint: _RoleCheckpoint) -> Workflow:
        workflow = Workflow()
        workflow.set_start_comp(
            "start",
            Start(),
            inputs_schema={
                "original_query": "${original_query}",
                "candidates": "${candidates}",
            },
        )
        workflow.add_workflow_comp(
            "episode_state",
            _InitialState(),
            inputs_schema={
                "original_query": "${start.original_query}",
                "candidates": "${start.candidates}",
            },
        )
        workflow.add_connection("start", "episode_state")
        perception = self._add_role(
            workflow,
            checkpoint,
            stage_id="perception",
            node=self.nodes.perception,
            predecessors=("episode_state",),
            kind="perception",
        )
        if not self.spec.review_loop_enabled:
            # Configured off: Perception feeds the Solver directly and its
            # answer is delivered through the same explicit-accept seal a
            # Planner ACCEPT would use. No Reviewer or Planner component is
            # ever added to this graph, so neither is ever contacted.
            solver = self._add_role(
                workflow,
                checkpoint,
                stage_id="solver_0",
                node=self.nodes.solver,
                predecessors=(perception,),
                kind="solver",
            )
            accept_id = "accept_0"
            workflow.add_workflow_comp(
                accept_id,
                _Accept(),
                inputs_schema={"state": "${" + solver + ".state}"},
            )
            workflow.add_connection(solver, accept_id)
            workflow.set_end_comp(
                "end",
                End(),
                inputs_schema=_first_accept([accept_id]),
            )
            workflow.add_connection(accept_id, "end")
            return workflow
        solver_predecessors = (perception,)
        accept_ids: list[str] = []

        for revision in range(self.spec.max_revisions + 1):
            solver = self._add_role(
                workflow,
                checkpoint,
                stage_id=f"solver_{revision}",
                node=self.nodes.solver,
                predecessors=solver_predecessors,
                kind="solver",
            )
            reviewer = self._add_role(
                workflow,
                checkpoint,
                stage_id=f"reviewer_{revision}",
                node=self.nodes.reviewer,
                predecessors=(solver,),
                kind="review",
            )
            planner = self._add_role(
                workflow,
                checkpoint,
                stage_id=f"planner_{revision}",
                node=self.nodes.planner,
                predecessors=(reviewer,),
                kind="planner",
            )
            accept_id = f"accept_{revision}"
            workflow.add_workflow_comp(
                accept_id,
                _Accept(),
                inputs_schema={"state": "${" + planner + ".state}"},
            )
            accept_ids.append(accept_id)

            router = BranchRouter()
            router.add_branch(
                "${" + planner + ".action} == " + json.dumps(self.spec.actions.accept),
                accept_id,
            )
            # E8c: an illegal or unparseable Planner output stops THIS row
            # exactly as an ACCEPT would -- the committed draft is delivered
            # unchanged, no further role is contacted and the revision budget
            # is not spent -- through the very same explicit-accept component.
            # The truth lives in the route record and the receipt mark
            # _ApplyRole wrote, not in a separate delivery path.  The
            # NCP solver:plan-action boundary is reached only on a REVISE, so
            # it is not on this path at all.
            router.add_branch(
                "${" + planner + ".action} == " + json.dumps(PLANNER_ACTION_ILLEGAL),
                accept_id,
            )
            if revision == self.spec.max_revisions:
                exhausted_id = f"exhausted_{revision}"
                terminal_component: WorkflowComponent
                if self.spec.exhaustion_policy == "deliver-latest-solver":
                    terminal_component = _TerminalDelivery(
                        self.spec.actions,
                        self.spec.refresh_action,
                        self.spec.planner_output_format,
                    )
                    accept_ids.append(exhausted_id)
                else:
                    terminal_component = _Exhausted()
                workflow.add_workflow_comp(
                    exhausted_id,
                    terminal_component,
                    inputs_schema={"state": "${" + planner + ".state}"},
                )
                router.add_branch(
                    "${" + planner + ".action} == "
                    + json.dumps(self.spec.actions.revise),
                    exhausted_id,
                )
                router.add_branch(
                    "${" + planner + ".action} == "
                    + json.dumps(self.spec.actions.acquire),
                    exhausted_id,
                )
                if self.spec.refresh_action is not None:
                    router.add_branch(
                        "${" + planner + ".action} == " + json.dumps(self.spec.refresh_action),
                        exhausted_id,
                    )
                workflow.add_conditional_connection(planner, router)
                continue

            revise_id = f"revise_{revision}"
            workflow.add_workflow_comp(
                revise_id,
                _AdvanceRevision(),
                inputs_schema={"state": "${" + planner + ".state}"},
            )
            router.add_branch(
                "${" + planner + ".action} == " + json.dumps(self.spec.actions.revise),
                revise_id,
            )
            next_predecessors = [revise_id]
            if self.spec.refresh_action is not None:
                refresh_id = f"refresh_{revision}"
                workflow.add_workflow_comp(
                    refresh_id,
                    _AdvanceCandidateRefresh(self.spec.max_candidate_refreshes),
                    inputs_schema={"state": "${" + planner + ".state}"},
                )
                router.add_branch(
                    "${" + planner + ".action} == " + json.dumps(self.spec.refresh_action),
                    refresh_id,
                )
                refreshed = self._add_role(
                    workflow,
                    checkpoint,
                    stage_id=f"perception_refresh_{revision}",
                    node=self.nodes.perception,
                    predecessors=(refresh_id,),
                    kind="perception",
                )
                next_predecessors.append(refreshed)
            if self.nodes.acquisition is None:
                # E15: unreachable by construction.  `_planner_actions` holds
                # no ACQUIRE for an episode built without an acquisition node,
                # so `_ApplyRole` classifies such a token as an illegal
                # Planner output and the router's PLANNER_ACTION_ILLEGAL
                # branch above seals the row.  The branch stays as defence in
                # depth: if some future caller ever makes ACQUIRE legal
                # without wiring a node, the graph must refuse loudly rather
                # than silently deliver.
                acquire_id = f"acquire_unavailable_{revision}"
                workflow.add_workflow_comp(
                    acquire_id,
                    _Exhausted("episode has no configured analytical acquisition role"),
                    inputs_schema={"state": "${" + planner + ".state}"},
                )
                router.add_branch(
                    "${" + planner + ".action} == "
                    + json.dumps(self.spec.actions.acquire),
                    acquire_id,
                )
            elif (
                isinstance(self.nodes.acquisition, AcquisitionNode)
                and revision >= self.spec.max_acquisitions
            ):
                # E18: the acquisition budget is spent for this row.  The
                # route stays defence in depth, exactly as the unwired branch
                # above is: `role_input`'s advertised action set stops
                # offering ACQUIRE at these revisions and, under
                # `json-action-v1`, the Planner's own response schema cannot
                # even spell it -- so reaching here means a caller made
                # ACQUIRE legal past its declared budget, and the graph must
                # refuse loudly rather than acquire off the books.
                acquire_id = f"acquire_over_budget_{revision}"
                workflow.add_workflow_comp(
                    acquire_id,
                    _Exhausted("episode acquisition budget is exhausted"),
                    inputs_schema={"state": "${" + planner + ".state}"},
                )
                router.add_branch(
                    "${" + planner + ".action} == "
                    + json.dumps(self.spec.actions.acquire),
                    acquire_id,
                )
            else:
                acquire_advance = f"acquire_{revision}"
                workflow.add_workflow_comp(
                    acquire_advance,
                    _AdvanceRevision(),
                    inputs_schema={"state": "${" + planner + ".state}"},
                )
                router.add_branch(
                    "${" + planner + ".action} == "
                    + json.dumps(self.spec.actions.acquire),
                    acquire_advance,
                )
                if isinstance(self.nodes.acquisition, AcquisitionNode):
                    # E18: the sixth node.  It makes no contact of its own
                    # seat, so it needs no `_RoleQuery`/`_ApplyRole` triple:
                    # one component runs the registered acquisition policy and
                    # binds its typed record into the state the next Solver
                    # revision reads.
                    acquired = f"acquisition_{revision}"
                    workflow.add_workflow_comp(
                        acquired,
                        _Acquire(self.nodes.acquisition, checkpoint),
                        inputs_schema={"state": "${" + acquire_advance + ".state}"},
                    )
                    workflow.add_connection(acquire_advance, acquired)
                else:
                    acquired = self._add_role(
                        workflow,
                        checkpoint,
                        stage_id=f"acquisition_{revision}",
                        node=self.nodes.acquisition,
                        predecessors=(acquire_advance,),
                        kind="acquisition",
                    )
                next_predecessors.append(acquired)
            workflow.add_conditional_connection(planner, router)
            solver_predecessors = tuple(next_predecessors)

        workflow.set_end_comp(
            "end",
            End(),
            inputs_schema=_first_accept(accept_ids),
        )
        for accept_id in accept_ids:
            workflow.add_connection(accept_id, "end")
        return workflow

    async def invoke_direct(
        self,
        original_query: str,
        candidates: Sequence[object],
        *,
        session: Session | None = None,
    ) -> dict[str, object]:
        checkpoint = _RoleCheckpoint()
        try:
            output = await self._build(checkpoint).invoke(
                inputs={"original_query": original_query, "candidates": candidates},
                session=(
                    session if session is not None else create_workflow_session()
                ),
            )
        except Exception as error:
            context_error = _context_fit_error_in_chain(error)
            if (
                context_error is not None
                and self.spec.context_fit_policy == "compact-or-abstain"
            ):
                try:
                    return _context_fit_terminal_outcome(context_error, checkpoint)
                except NativeEpisodeError as terminal_error:
                    raise NativeEpisodeError(str(terminal_error)) from error
            finite_error = _finite_error_in_chain(error)
            if (
                finite_error is not None
                and self.spec.finite_completion_policy
                == "deliver-latest-or-abstain"
            ):
                try:
                    return _finite_terminal_outcome(
                        finite_error,
                        checkpoint,
                        # Item E39: under ``"answering-node"`` the only
                        # refusals that reach here are the answering node's
                        # own and the ones its siblings could not tolerate
                        # (an empty or tool-bearing truncation, or a
                        # ``content_filter`` stop).
                        self.spec.finite_completion_scope,
                    )
                except NativeEpisodeError as terminal_error:
                    raise NativeEpisodeError(str(terminal_error)) from error
            seal_refusal_error = _seal_refusal_error_in_chain(error)
            if (
                seal_refusal_error is not None
                and self.spec.finite_completion_policy
                == "deliver-latest-or-abstain"
            ):
                # Item E43: a structured-output contract's own seal refused
                # this row's deciding completion (a grammar-valid "stop"
                # finish) -- the COMP-1/B7a/B8b-anchor abort class. Disposed
                # of under the SAME policy switch a finite completion is,
                # never a new configuration key.
                try:
                    return _seal_refusal_terminal_outcome(seal_refusal_error, checkpoint)
                except NativeEpisodeError as terminal_error:
                    raise NativeEpisodeError(str(terminal_error)) from error
            cause: BaseException | None = error
            seen: set[int] = set()
            while cause is not None and id(cause) not in seen:
                if isinstance(cause, NativeEpisodeError):
                    raise NativeEpisodeError(str(cause)) from error
                seen.add(id(cause))
                cause = cause.__cause__ or cause.__context__
            raise NativeEpisodeError(f"native episode node failed: {error}") from error
        result = output.result
        if not isinstance(result, Mapping):
            raise NativeEpisodeError("OpenJiuwen returned no episode result")
        end = result.get("output")
        if not isinstance(end, Mapping) or not isinstance(end.get("accepted"), Mapping):
            raise NativeEpisodeError("OpenJiuwen returned no accepted episode state")
        return copy.deepcopy(dict(end["accepted"]))


def build_native_episode(
    *,
    spec: NativeEpisodeSpec,
    nodes: NativeEpisodeNodes,
    role_input_builder: RoleInputBuilder,
) -> NativeEpisodeWorkflow:
    """Validate role authority and compose a bounded conditional episode."""
    if not isinstance(spec, NativeEpisodeSpec):
        raise ValueError("spec must be NativeEpisodeSpec")
    if not isinstance(nodes, NativeEpisodeNodes):
        raise ValueError("nodes must be NativeEpisodeNodes")
    if not callable(role_input_builder):
        raise ValueError("role_input_builder must be callable")
    expected = {
        "perception": "perception",
        "solver": "solver",
        "reviewer": "reviewer",
        "planner": "planner",
    }
    for field, kind in expected.items():
        node = getattr(nodes, field)
        if field in {"reviewer", "planner"} and not spec.review_loop_enabled:
            if node is not None:
                raise ValueError(
                    f"{field} must be omitted when the review loop is disabled"
                )
            continue
        if field == "solver":
            # E2b: a grouped Solver visit (samples >= 2) is a
            # GroupedSolverRoleNode, not a NativeRoleNode; both expose the
            # same spec.role_id/spec.role_kind contract this validation and
            # _RoleQuery/_add_role actually need.
            # Item E42: an ARM-grouped Solver visit is a
            # SupplyVariantRoleNode, which exposes the same contract for the
            # same reason. Imported function-locally, exactly as this module's
            # other registration-style imports are, so the light top-level
            # import discipline is kept.
            # Same-flight instrument, PHASE 2, LEVEL 2 (merge set C item 1):
            # a branched Perception group's own first-visit Solver fan-out is
            # a PerceptionBranchSolverRoleNode, SupplyVariantRoleNode's own
            # twin over the branch group instead of a Solver-declared arm
            # group, exposing the same contract for the same reason.
            from .native_supply_variants import (  # noqa: PLC0415
                PerceptionBranchSolverRoleNode, SupplyVariantRoleNode,
            )

            if (
                not isinstance(
                    node,
                    (
                        NativeRoleNode, GroupedSolverRoleNode,
                        SupplyVariantRoleNode, PerceptionBranchSolverRoleNode,
                    ),
                )
                or node.spec.role_kind != kind
            ):
                raise ValueError(
                    f"{field} must be a {kind} NativeRoleNode, "
                    "GroupedSolverRoleNode, SupplyVariantRoleNode or "
                    "PerceptionBranchSolverRoleNode"
                )
            continue
        if field == "perception":
            # Same-flight instrument, PHASE 2 (merge set C): a BRANCHED
            # Perception visit is a PerceptionBranchRoleNode --
            # SupplyVariantRoleNode's own twin -- which exposes the same
            # spec.role_id/spec.role_kind contract this validation and
            # _RoleQuery/_add_role actually need. Imported function-locally,
            # for the same reason.
            from .native_supply_variants import (  # noqa: PLC0415
                PerceptionBranchRoleNode,
            )

            if (
                not isinstance(node, (NativeRoleNode, PerceptionBranchRoleNode))
                or node.spec.role_kind != kind
            ):
                raise ValueError(
                    f"{field} must be a {kind} NativeRoleNode or "
                    "PerceptionBranchRoleNode"
                )
            continue
        if not isinstance(node, NativeRoleNode) or node.spec.role_kind != kind:
            raise ValueError(f"{field} must be a {kind} NativeRoleNode")
    if nodes.acquisition is not None and not isinstance(
        nodes.acquisition, (NativeRoleNode, AcquisitionNode)
    ):
        raise ValueError(
            "acquisition must be an AcquisitionNode or an analytical NativeRoleNode"
        )
    if isinstance(nodes.acquisition, NativeRoleNode) and (
        nodes.acquisition.spec.role_kind not in {"reviewer", "planner"}
    ):
        raise ValueError("acquisition must be an analytical NativeRoleNode")
    if not spec.review_loop_enabled and nodes.acquisition is not None:
        raise ValueError("acquisition requires the review loop to be enabled")
    if spec.max_acquisitions and not isinstance(nodes.acquisition, AcquisitionNode):
        # E18: a positive acquisition budget is the configuration's promise
        # that ACQUIRE reaches a node that can execute it.  The pre-E18
        # analytical path has no budget of its own and keeps 0.
        raise ValueError("an acquisition budget requires an AcquisitionNode")
    if isinstance(nodes.acquisition, AcquisitionNode) and not spec.max_acquisitions:
        raise ValueError("an AcquisitionNode requires a positive acquisition budget")
    role_ids = [
        getattr(nodes, field).spec.role_id
        for field in expected
        if getattr(nodes, field) is not None
    ]
    if nodes.acquisition is not None:
        role_ids.append(
            nodes.acquisition.spec.node_id
            if isinstance(nodes.acquisition, AcquisitionNode)
            else nodes.acquisition.spec.role_id
        )
    if len(set(role_ids)) != len(role_ids):
        raise ValueError("episode role ids must be unique")
    return NativeEpisodeWorkflow(
        spec=spec, nodes=nodes, role_input_builder=role_input_builder
    )


__all__ = [
    "ACQUISITION_RECORD_KEYS",
    "ACQUISITION_STAGE",
    "AcquisitionNode",
    "AcquisitionNodeSpec",
    "PLANNER_ACTION_ILLEGAL",
    "PLANNER_ACTION_ILLEGAL_DISPOSITION",
    "PLANNER_ACTION_ILLEGAL_SCHEMA",
    "PLANNER_ACTION_RECORD_CHARS",
    "REACT_EXHAUSTION_DISPOSITION",
    "REACT_EXHAUSTION_SCHEMA",
    "REACT_EXHAUSTION_STAGES",
    "REVIEWER_VERDICT_ILLEGAL_DISPOSITION",
    "REVIEWER_VERDICT_LEGAL",
    "REVIEWER_VERDICTS_KEY",
    "NativeEpisodeActions",
    "NativeEpisodeError",
    "NativeEpisodeNodes",
    "NativeEpisodeSpec",
    "NativeEpisodeWorkflow",
    "RoleInputBuilder",
    "build_native_episode",
]
