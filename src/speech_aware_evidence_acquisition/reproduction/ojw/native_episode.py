"""A bounded conditional OpenJiuwen episode composed from native role nodes.

The caller supplies every role prompt through a pure input builder and every
model contact through the ``NativeRoleNode`` instances. This module only
defines state transitions and public Workflow edges. It does not own contact
allocation, request history, task prompts, tool execution, or answer scoring.
"""

from __future__ import annotations

import copy
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

from .native_roles import (
    FrozenCoreRoleFiniteCompletionError,
    FrozenCoreRoleModelError,
    NativeRoleNode,
)


class NativeEpisodeError(RuntimeError):
    """The bounded role graph cannot produce an explicitly accepted answer."""


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
        if self.planner_output_format not in {"exact-text", "json-action-v1"}:
            raise ValueError("planner_output_format is invalid")


@dataclass(frozen=True)
class NativeEpisodeNodes:
    """Public framework role components used by the episode graph."""

    perception: NativeRoleNode
    solver: NativeRoleNode
    reviewer: NativeRoleNode
    planner: NativeRoleNode
    acquisition: NativeRoleNode | None = None


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
) -> tuple[str, dict[str, str] | None]:
    if output_format == "exact-text":
        action = output
        control = None
    else:
        def unique_object(pairs):
            document = {}
            for key, value in pairs:
                if key in document:
                    raise NativeEpisodeError("Planner JSON action contains a duplicate key")
                document[key] = value
            return document

        try:
            document = json.loads(output, object_pairs_hook=unique_object)
        except (TypeError, ValueError) as error:
            raise NativeEpisodeError("Planner output is not strict JSON action control") from error
        if not isinstance(document, dict) or set(document) != {"action"}:
            raise NativeEpisodeError("Planner JSON action must contain exactly action")
        action = document["action"]
        if not isinstance(action, str):
            raise NativeEpisodeError("Planner JSON action must be a string")
        control = {"action": action}
    if action not in legal:
        raise NativeEpisodeError("Planner output names no registered action")
    return action, control


class _ApplyRole(WorkflowComponent):
    def __init__(
        self,
        kind: str,
        actions: NativeEpisodeActions,
        refresh_action: str | None = None,
        planner_output_format: str = "exact-text",
        planner_actions: set[str] | None = None,
    ) -> None:
        super().__init__()
        self._kind = kind
        self._actions = actions
        self._refresh_action = refresh_action
        self._planner_output_format = planner_output_format
        self._planner_actions = planner_actions

    async def invoke(
        self, inputs: Input, session: Session, context: ModelContext
    ) -> Output:
        state = _state(inputs)
        role = inputs.get("role")
        if not isinstance(role, Mapping) or role.get("result_type") != "answer":
            raise NativeEpisodeError(f"{self._kind} node did not return an answer")
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
        result: dict[str, object] = {"state": updated}
        if self._kind == "solver":
            if role.get("delivery_eligible") is not True:
                raise NativeEpisodeError("episode has no valid Solver draft")
            updated["latest_solver"] = dict(role)
        elif self._kind == "planner":
            legal = {
                self._actions.accept,
                self._actions.revise,
                self._actions.acquire,
            }
            if self._refresh_action is not None:
                legal.add(self._refresh_action)
            if self._planner_actions is not None:
                legal = set(self._planner_actions)
            action, control = _planner_action(
                output, output_format=self._planner_output_format, legal=legal
            )
            updated["plan"] = output
            if control is not None:
                updated["planner_control"] = control
            routes = updated.get("planner_routes")
            if not isinstance(routes, Sequence) or isinstance(
                routes, (str, bytes)
            ):
                raise NativeEpisodeError("episode state has invalid Planner routes")
            updated_routes = [copy.deepcopy(route) for route in routes]
            updated_routes.append(
                {
                    "role_visit_index": len(updated_visits) - 1,
                    "revision_count": int(updated["revision_count"]),
                    "action": action,
                }
            )
            updated["planner_routes"] = updated_routes
            result["action"] = action
        else:
            updated[self._kind] = output
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
    state["terminal_disposition"] = {
        "reason": "finite_completion",
        "finish_reason": error.finish_reason,
        "role_id": checkpoint.role_id,
        "stage": checkpoint.stage,
        "revision_count": revision_count,
        "planner_accepted": False,
        "rejected_contact": dict(normalized_rejected),
    }

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
                (
                    self._planner_actions
                    if kind == "planner"
                    and self.spec.planner_output_format == "json-action-v1"
                    else None
                ),
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
            finite_error = _finite_error_in_chain(error)
            if (
                finite_error is not None
                and self.spec.finite_completion_policy
                == "deliver-latest-or-abstain"
            ):
                try:
                    return _finite_terminal_outcome(finite_error, checkpoint)
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
        if not isinstance(node, NativeRoleNode) or node.spec.role_kind != kind:
            raise ValueError(f"{field} must be a {kind} NativeRoleNode")
    if nodes.acquisition is not None and (
        not isinstance(nodes.acquisition, NativeRoleNode)
        or nodes.acquisition.spec.role_kind not in {"reviewer", "planner"}
    ):
        raise ValueError("acquisition must be an analytical NativeRoleNode")
    role_ids = [getattr(nodes, field).spec.role_id for field in expected]
    if nodes.acquisition is not None:
        role_ids.append(nodes.acquisition.spec.role_id)
    if len(set(role_ids)) != len(role_ids):
        raise ValueError("episode role ids must be unique")
    return NativeEpisodeWorkflow(
        spec=spec, nodes=nodes, role_input_builder=role_input_builder
    )


__all__ = [
    "NativeEpisodeActions",
    "NativeEpisodeError",
    "NativeEpisodeNodes",
    "NativeEpisodeSpec",
    "NativeEpisodeWorkflow",
    "RoleInputBuilder",
    "build_native_episode",
]
