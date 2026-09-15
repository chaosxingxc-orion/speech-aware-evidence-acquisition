"""Model-free execution tests for the native conditional role episode."""

from __future__ import annotations

import asyncio
import dataclasses
import hashlib
import json
from dataclasses import dataclass, field
from types import SimpleNamespace

import pytest
from openjiuwen.core.foundation.tool import LocalFunction, ToolCard
from openjiuwen.core.workflow import create_workflow_session

from speech_aware_evidence_acquisition.rails.core_client import CoreCompletion
from speech_aware_evidence_acquisition.reproduction.ojw import (
    native_episode as native_episode_module,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    NativeEpisodeActions,
    NativeEpisodeError,
    NativeEpisodeNodes,
    NativeEpisodeSpec,
    build_native_episode,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    FrozenCoreRoleFiniteCompletionError,
    NativeRoleContactContext,
    NativeRoleNode,
    NativeRoleNodeSpec,
)


def _completion(
    text: str,
    contact_id: str,
    serial: int,
    *,
    finish_reason: str = "stop",
    tool_calls: object = None,
) -> CoreCompletion:
    request_id = f"request-{serial}"
    message: dict[str, object] = {"role": "assistant", "content": text}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    wire = json.dumps(
        {
            "choices": [
                {
                    "message": message,
                    "finish_reason": finish_reason,
                }
            ]
        },
        separators=(",", ":"),
    ).encode()
    return CoreCompletion(
        text=text,
        request_id=request_id,
        sample_id="sample-1",
        agent_contact_id=contact_id,
        request_sha256=hashlib.sha256(request_id.encode()).hexdigest(),
        response_sha256=hashlib.sha256(wire).hexdigest(),
        response_text_sha256=hashlib.sha256(text.encode()).hexdigest(),
        tool_calls_json=json.dumps(
            tool_calls,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode(),
        wire_response_bytes=wire,
    )


def _source_contact(completion: CoreCompletion) -> dict[str, str]:
    return {
        "agent_contact_id": completion.agent_contact_id,
        "request_id": completion.request_id,
        "request_sha256": completion.request_sha256,
        "response_sha256": completion.response_sha256,
        "response_text_sha256": completion.response_text_sha256,
    }


def _execution_receipt(
    *, text: str, contact_id: str, serial: int
) -> dict[str, object]:
    request_id = f"request-{serial}"
    contact = {
        "agent_contact_id": contact_id,
        "request_id": request_id,
        "request_sha256": hashlib.sha256(request_id.encode()).hexdigest(),
        "response_sha256": hashlib.sha256(
            _completion(text, contact_id, serial).wire_response_bytes
        ).hexdigest(),
        "response_text_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }
    return {"contacts": [contact], "final_contact": dict(contact)}


@dataclass(frozen=True)
class _FiniteResponse:
    text: str
    finish_reason: str


@dataclass
class _Script:
    values: list[str | _FiniteResponse]
    requests: list[object] = field(default_factory=list)
    completions: list[CoreCompletion] = field(default_factory=list)

    def __call__(self, request):
        self.requests.append(request)
        if not self.values:
            raise AssertionError("script exhausted")
        serial = sum(len(script.requests) for script in _ALL_SCRIPTS)
        value = self.values.pop(0)
        if isinstance(value, _FiniteResponse):
            completion = _completion(
                value.text,
                request.context.agent_contact_id,
                serial,
                finish_reason=value.finish_reason,
            )
        else:
            completion = _completion(
                value,
                request.context.agent_contact_id,
                serial,
            )
        self.completions.append(completion)
        return completion


_ALL_SCRIPTS: list[_Script] = []


class _CapturingWorkflow:
    def __init__(self) -> None:
        self.sessions: list[object] = []

    async def invoke(self, *, inputs, session):
        self.sessions.append(session)
        return SimpleNamespace(
            result={
                "output": {
                    "accepted": {
                        "state": {"original_query": inputs["original_query"]},
                        "delivery": {"actor_output": "synthetic"},
                    }
                }
            }
        )


def _node(
    role_id: str,
    role_kind: str,
    values: list[str | _FiniteResponse],
    *,
    valid=False,
):
    script = _Script(values)
    _ALL_SCRIPTS.append(script)
    node = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id=role_id,
            role_kind=role_kind,
            prompt=f"Act as the {role_id}.",
            max_iterations=1,
        ),
        metered_request=script,
        contact_context_provider=lambda index, role=role_id: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"{role}-contact-{index + 1}"
        ),
        delivery_allowed=(lambda _role, output: output.startswith("draft"))
        if valid
        else None,
    )
    return node, script


def _episode(
    *,
    solver,
    reviewer,
    planner,
    max_revisions=1,
    acquisition=None,
    exhaustion_policy="raise",
    refresh_action=None,
    max_candidate_refreshes=0,
    finite_completion_policy="raise",
    planner_output_format="exact-text",
    perception_values=None,
):
    perception, perception_script = _node(
        "perception",
        "perception",
        ["heard"] if perception_values is None else perception_values,
    )
    seen: list[tuple[str, dict[str, object]]] = []

    def role_input(role_id, state):
        seen.append((role_id, dict(state)))
        return f"{role_id}: use the supplied episode state."

    workflow = build_native_episode(
        spec=NativeEpisodeSpec(
            episode_id="synthetic-episode",
            max_revisions=max_revisions,
            actions=NativeEpisodeActions(
                accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"
            ),
            exhaustion_policy=exhaustion_policy,
            refresh_action=refresh_action,
            max_candidate_refreshes=max_candidate_refreshes,
            finite_completion_policy=finite_completion_policy,
            planner_output_format=planner_output_format,
        ),
        nodes=NativeEpisodeNodes(
            perception=perception,
            solver=solver,
            reviewer=reviewer,
            planner=planner,
            acquisition=acquisition,
        ),
        role_input_builder=role_input,
    )
    return workflow, perception_script, seen


@pytest.fixture(autouse=True)
def _clear_scripts():
    _ALL_SCRIPTS.clear()


def test_accept_delivers_only_the_validated_solver_output():
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["ACCEPT"])
    workflow, _, seen = _episode(solver=solver, reviewer=reviewer, planner=planner)

    result = asyncio.run(
        workflow.invoke_direct("original query", ({"intent_id": "intent-a"},))
    )

    assert result["delivery"] == {
        "role_id": "solver",
        "actor_output": "draft one",
        "result_type": "answer",
        "delivery_eligible": True,
        "execution_receipt": _execution_receipt(
            text="draft one", contact_id="solver-contact-1", serial=2
        ),
    }
    assert result["state"]["latest_solver"] == result["delivery"]
    assert result["state"]["accepted_solver_receipt"] == result["delivery"][
        "execution_receipt"
    ]
    assert result["state"]["review"] == "review one"
    assert result["state"]["plan"] == "ACCEPT"
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
    ]
    assert [visit["role_id"] for visit in result["state"]["role_visits"]] == [
        "perception",
        "solver",
        "reviewer",
        "planner",
    ]
    assert result["state"]["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "ACCEPT"},
    ]
    assert [role for role, _ in seen] == [
        "perception",
        "solver",
        "reviewer",
        "planner",
    ]


def test_json_planner_action_accepts_and_preserves_raw_control():
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    raw = '{"action":"ACCEPT"}'
    planner, _ = _node("planner", "planner", [raw])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        planner_output_format="json-action-v1",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    assert result["delivery"]["actor_output"] == "draft one"
    assert result["state"]["plan"] == raw
    assert result["state"]["planner_control"] == {"action": "ACCEPT"}
    assert result["state"]["planner_routes"][-1]["action"] == "ACCEPT"


def test_json_exhausted_revise_delivers_latest_solver_without_extra_generation():
    solver, solver_script = _node(
        "solver", "solver", ["draft one", "draft two"], valid=True
    )
    reviewer, reviewer_script = _node(
        "reviewer", "reviewer", ["review one", "review two"]
    )
    planner, planner_script = _node(
        "planner", "planner",
        ['{"action":"REVISE"}', '{"action":"REVISE"}'],
    )
    workflow, perception_script, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=1,
        exhaustion_policy="deliver-latest-solver",
        planner_output_format="json-action-v1",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    assert result["delivery"]["actor_output"] == "draft two"
    assert result["state"]["terminal_disposition"]["planner_action"] == "REVISE"
    assert [len(script.requests) for script in (
        perception_script, solver_script, reviewer_script, planner_script
    )] == [1, 2, 2, 2]


@pytest.mark.parametrize(
    "raw",
    [
        "REVISE",
        '{"action":"REVISE","reason":"extra"}',
        '{"action":"REVISE","action":"ACCEPT"}',
        '{"action":"UNKNOWN"}',
        '{"action":"ACQUIRE"}',
    ],
)
def test_json_planner_action_rejects_malformed_extra_duplicate_or_unknown(raw):
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", [raw])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        planner_output_format="json-action-v1",
    )

    with pytest.raises(NativeEpisodeError):
        asyncio.run(workflow.invoke_direct("query", ()))


def test_revise_runs_solver_and_review_again_before_acceptance():
    solver, solver_script = _node(
        "solver", "solver", ["draft one", "draft two"], valid=True
    )
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", ["REVISE", "ACCEPT"])
    workflow, _, seen = _episode(solver=solver, reviewer=reviewer, planner=planner)

    result = asyncio.run(workflow.invoke_direct("query", ()))

    assert result["delivery"]["actor_output"] == "draft two"
    assert result["state"]["revision_count"] == 1
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
        "solver",
        "review",
        "planner",
    ]
    assert result["state"]["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "REVISE"},
        {"role_visit_index": 6, "revision_count": 1, "action": "ACCEPT"},
    ]
    assert result["state"]["accepted_solver_receipt"] == _execution_receipt(
        text="draft two", contact_id="solver-contact-2", serial=5
    )
    assert len(solver_script.requests) == 2
    second_solver_state = [state for role, state in seen if role == "solver"][1]
    assert second_solver_state["review"] == "review one"
    assert second_solver_state["plan"] == "REVISE"


def test_acquire_routes_to_configured_analytical_role_then_revises():
    solver, _ = _node("solver", "solver", ["draft one", "draft two"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", ["ACQUIRE", "ACCEPT"])
    acquisition, acquisition_script = _node(
        "analyst", "reviewer", ["acquired fact"]
    )
    workflow, _, seen = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        acquisition=acquisition,
    )

    result = asyncio.run(workflow.invoke_direct("query", ("candidate",)))

    assert result["delivery"]["actor_output"] == "draft two"
    assert result["state"]["acquisition"] == "acquired fact"
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
        "acquisition",
        "solver",
        "review",
        "planner",
    ]
    assert result["state"]["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "ACQUIRE"},
        {"role_visit_index": 7, "revision_count": 1, "action": "ACCEPT"},
    ]
    assert len(acquisition_script.requests) == 1
    second_solver_state = [state for role, state in seen if role == "solver"][1]
    assert second_solver_state["acquisition"] == "acquired fact"


@pytest.mark.parametrize("plan", [" ACCEPT", "accept", "UNKNOWN"])
def test_malformed_planner_action_never_delivers(plan):
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", [plan])
    workflow, _, _ = _episode(solver=solver, reviewer=reviewer, planner=planner)

    with pytest.raises(NativeEpisodeError, match="registered action"):
        asyncio.run(workflow.invoke_direct("query", ()))


def test_exhausted_revision_and_invalid_solver_never_deliver():
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["REVISE"])
    exhausted, _, _ = _episode(
        solver=solver, reviewer=reviewer, planner=planner, max_revisions=0
    )
    with pytest.raises(NativeEpisodeError, match="revision limit"):
        asyncio.run(exhausted.invoke_direct("query", ()))

    bad_solver, _ = _node("bad-solver", "solver", ["not validated"])
    reviewer2, _ = _node("reviewer-2", "reviewer", ["unused"])
    planner2, _ = _node("planner-2", "planner", ["ACCEPT"])
    invalid, _, _ = _episode(
        solver=bad_solver, reviewer=reviewer2, planner=planner2
    )
    with pytest.raises(NativeEpisodeError, match="valid Solver"):
        asyncio.run(invalid.invoke_direct("query", ()))


def test_opt_in_terminal_delivery_still_refuses_invalid_solver_and_early_acquire():
    bad_solver, _ = _node("bad-solver", "solver", ["not validated"])
    reviewer, _ = _node("reviewer", "reviewer", ["review"])
    planner, _ = _node("planner", "planner", ["REVISE"])
    invalid, _, _ = _episode(
        solver=bad_solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        exhaustion_policy="deliver-latest-solver",
    )
    with pytest.raises(NativeEpisodeError, match="valid Solver"):
        asyncio.run(invalid.invoke_direct("query", ()))

    solver, _ = _node("solver-2", "solver", ["draft one"], valid=True)
    reviewer2, _ = _node("reviewer-2", "reviewer", ["review"])
    planner2, _ = _node("planner-2", "planner", ["ACQUIRE"])
    early_acquire, _, _ = _episode(
        solver=solver,
        reviewer=reviewer2,
        planner=planner2,
        max_revisions=1,
        exhaustion_policy="deliver-latest-solver",
    )
    with pytest.raises(NativeEpisodeError, match="no configured analytical acquisition"):
        asyncio.run(early_acquire.invoke_direct("query", ()))


@pytest.mark.parametrize("planner_action", ("REVISE", "ACQUIRE"))
def test_terminal_exhaustion_delivery_is_opt_in_and_records_actual_planner_action(
    planner_action,
):
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", [planner_action])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        exhaustion_policy="deliver-latest-solver",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    assert result["delivery"]["actor_output"] == "draft one"
    assert "accepted_solver_receipt" not in state
    assert state["terminal_solver_receipt"] == _execution_receipt(
        text="draft one", contact_id="solver-contact-1", serial=2
    )
    assert state["terminal_disposition"] == {
        "reason": "revision_limit",
        "planner_action": planner_action,
        "revision_count": 0,
        "planner_accepted": False,
    }
    assert state["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": planner_action}
    ]


def test_opt_in_terminal_delivery_binds_the_last_revision_solver():
    solver, _ = _node(
        "solver", "solver", ["draft one", "draft two"], valid=True
    )
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", ["REVISE", "ACQUIRE"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=1,
        exhaustion_policy="deliver-latest-solver",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    assert result["delivery"]["actor_output"] == "draft two"
    assert state["terminal_solver_receipt"] == _execution_receipt(
        text="draft two", contact_id="solver-contact-2", serial=5
    )
    assert state["terminal_disposition"] == {
        "reason": "revision_limit",
        "planner_action": "ACQUIRE",
        "revision_count": 1,
        "planner_accepted": False,
    }


def test_framework_node_error_never_delivers():
    def fail_contact(_request):
        raise RuntimeError("synthetic metered failure")

    perception = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="perception",
            role_kind="perception",
            prompt="Perceive.",
            max_iterations=1,
        ),
        metered_request=fail_contact,
        contact_context=NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id="perception-contact-1"
        ),
    )
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["ACCEPT"])
    workflow = build_native_episode(
        spec=NativeEpisodeSpec(
            episode_id="node-error",
            max_revisions=0,
            actions=NativeEpisodeActions(
                accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"
            ),
        ),
        nodes=NativeEpisodeNodes(
            perception=perception,
            solver=solver,
            reviewer=reviewer,
            planner=planner,
        ),
        role_input_builder=lambda role, _state: f"Run {role}.",
    )

    with pytest.raises(NativeEpisodeError, match="native episode node failed"):
        asyncio.run(workflow.invoke_direct("query", ()))


def test_invoke_direct_passes_the_exact_caller_session(monkeypatch):
    solver, _ = _node("solver", "solver", ["unused"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["unused"])
    planner, _ = _node("planner", "planner", ["unused"])
    workflow, _, _ = _episode(solver=solver, reviewer=reviewer, planner=planner)
    capturing = _CapturingWorkflow()
    supplied_session = create_workflow_session()
    monkeypatch.setattr(workflow, "_build", lambda _checkpoint: capturing)
    monkeypatch.setattr(
        native_episode_module,
        "create_workflow_session",
        lambda: pytest.fail("caller session must suppress the default factory"),
    )

    result = asyncio.run(
        workflow.invoke_direct("query", (), session=supplied_session)
    )

    assert capturing.sessions[0] is supplied_session
    assert result["state"]["original_query"] == "query"


def test_invoke_direct_still_creates_a_default_session_when_absent(monkeypatch):
    solver, _ = _node("solver", "solver", ["unused"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["unused"])
    planner, _ = _node("planner", "planner", ["unused"])
    workflow, _, _ = _episode(solver=solver, reviewer=reviewer, planner=planner)
    capturing = _CapturingWorkflow()
    default_session = create_workflow_session()
    factory_calls: list[None] = []
    monkeypatch.setattr(workflow, "_build", lambda _checkpoint: capturing)

    def default_factory():
        factory_calls.append(None)
        return default_session

    monkeypatch.setattr(
        native_episode_module, "create_workflow_session", default_factory
    )

    asyncio.run(workflow.invoke_direct("query", ()))

    assert factory_calls == [None]
    assert capturing.sessions[0] is default_session


def test_refresh_revisits_perception_then_solver_and_preserves_both_receipts():
    solver, _ = _node("solver", "solver", ["draft one", "draft two"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["missing operation", "resolved"])
    planner, _ = _node("planner", "planner", ["REFRESH_CANDIDATES", "ACCEPT"])
    workflow, perception_script, seen = _episode(
        solver=solver, reviewer=reviewer, planner=planner,
        refresh_action="REFRESH_CANDIDATES", max_candidate_refreshes=1,
    )
    perception_script.values.append("new candidate set")
    result = asyncio.run(workflow.invoke_direct("query", ()))
    visits = result["state"]["role_visits"]
    assert [v["stage"] for v in visits] == [
        "perception", "solver", "review", "planner",
        "perception", "solver", "review", "planner",
    ]
    assert visits[0]["execution_receipt"] != visits[4]["execution_receipt"]
    assert len(perception_script.requests) == 2
    solver_states = [state for role, state in seen if role == "solver"]
    assert solver_states[0]["perception"] == "heard"
    assert solver_states[1]["perception"] == "new candidate set"
    assert solver_states[1]["review"] == "missing operation"
    assert solver_states[1]["candidate_refresh_count"] == 1
    assert result["state"]["revision_count"] == 1
    assert result["delivery"]["actor_output"] == "draft two"


def test_refresh_cannot_exceed_its_sub_bound_even_with_more_revision_budget():
    solver, _ = _node("solver", "solver", ["draft one", "draft two"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", ["REFRESH_CANDIDATES"] * 2)
    workflow, perception_script, _ = _episode(
        solver=solver, reviewer=reviewer, planner=planner, max_revisions=3,
        refresh_action="REFRESH_CANDIDATES", max_candidate_refreshes=1,
    )
    perception_script.values.append("new candidate set")
    with pytest.raises(NativeEpisodeError, match="candidate refresh limit"):
        asyncio.run(workflow.invoke_direct("query", ()))
    assert len(perception_script.requests) == 2


def test_refresh_after_final_revision_delivers_only_latest_solver_under_explicit_policy():
    solver, _ = _node("solver", "solver", ["draft one", "draft two"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", ["REFRESH_CANDIDATES"] * 2)
    workflow, perception_script, _ = _episode(
        solver=solver, reviewer=reviewer, planner=planner,
        refresh_action="REFRESH_CANDIDATES", max_candidate_refreshes=1,
        exhaustion_policy="deliver-latest-solver",
    )
    perception_script.values.append("new candidate set")
    result = asyncio.run(workflow.invoke_direct("query", ()))
    assert len(perception_script.requests) == 2
    assert result["delivery"]["actor_output"] == "draft two"
    assert result["state"]["terminal_disposition"]["planner_accepted"] is False
    assert result["state"]["terminal_disposition"]["planner_action"] == "REFRESH_CANDIDATES"


def test_unconfigured_refresh_action_never_revisits_perception():
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["REFRESH_CANDIDATES"])
    workflow, perception_script, _ = _episode(
        solver=solver, reviewer=reviewer, planner=planner,
    )
    with pytest.raises(NativeEpisodeError, match="registered action"):
        asyncio.run(workflow.invoke_direct("query", ()))
    assert len(perception_script.requests) == 1


@pytest.mark.parametrize(
    ("failed_stage", "finish_reason", "expected_visits", "has_solver"),
    [
        ("perception", "length", [], False),
        ("solver", "content_filter", ["perception"], False),
        ("reviewer", "length", ["perception", "solver"], True),
        ("planner", "content_filter", ["perception", "solver", "review"], True),
    ],
)
def test_finite_completion_policy_terminalizes_at_actual_initial_role_checkpoint(
    failed_stage,
    finish_reason,
    expected_visits,
    has_solver,
):
    finite = _FiniteResponse(f"partial {failed_stage}", finish_reason)
    perception_values = [finite] if failed_stage == "perception" else ["heard"]
    solver, solver_script = _node(
        "solver",
        "solver",
        [finite] if failed_stage == "solver" else ["draft one"],
        valid=True,
    )
    reviewer, reviewer_script = _node(
        "reviewer",
        "reviewer",
        [finite] if failed_stage == "reviewer" else ["review one"],
    )
    planner, planner_script = _node(
        "planner",
        "planner",
        [finite] if failed_stage == "planner" else ["ACCEPT"],
    )
    workflow, perception_script, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        finite_completion_policy="deliver-latest-or-abstain",
        perception_values=perception_values,
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    failed_script = {
        "perception": perception_script,
        "solver": solver_script,
        "reviewer": reviewer_script,
        "planner": planner_script,
    }[failed_stage]
    completion = failed_script.completions[-1]
    rejected_contact = _source_contact(completion)
    state = result["state"]
    assert [visit["stage"] for visit in state["role_visits"]] == expected_visits
    assert state["terminal_disposition"] == {
        "reason": "finite_completion",
        "finish_reason": finish_reason,
        "role_id": failed_stage,
        "stage": "review" if failed_stage == "reviewer" else failed_stage,
        "revision_count": 0,
        "planner_accepted": False,
        "rejected_contact": rejected_contact,
    }
    assert state["interrupted_role"] == {
        "role_id": failed_stage,
        "stage": "review" if failed_stage == "reviewer" else failed_stage,
        "execution_receipt": {
            "contacts": [rejected_contact],
            "final_contact": rejected_contact,
        },
    }
    assert "accepted_solver_receipt" not in state
    assert "partial" not in json.dumps(result)
    if has_solver:
        assert result["delivery"]["actor_output"] == "draft one"
        assert result["delivery"] == state["latest_solver"]
        assert state["terminal_solver_receipt"] == result["delivery"][
            "execution_receipt"
        ]
        assert "abstention_receipt" not in state
    else:
        assert result["delivery"] == {
            "actor_output": "",
            "result_type": "abstention",
            "delivery_eligible": False,
        }
        assert state["abstention_receipt"] == {
            "source_contact": rejected_contact,
        }
        assert "terminal_solver_receipt" not in state
    if failed_stage == "planner":
        assert state["plan"] is None
        assert state["planner_routes"] == []


def test_finite_refreshed_perception_preserves_last_solver_without_failed_visit():
    solver, _ = _node("solver", "solver", ["draft one", "unused"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["REFRESH_CANDIDATES"])
    workflow, perception_script, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=1,
        refresh_action="REFRESH_CANDIDATES",
        max_candidate_refreshes=1,
        finite_completion_policy="deliver-latest-or-abstain",
        perception_values=[
            "heard",
            _FiniteResponse("partial refreshed perception", "length"),
        ],
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    rejected_contact = _source_contact(perception_script.completions[-1])
    assert [visit["stage"] for visit in state["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
    ]
    assert state["revision_count"] == 1
    assert state["candidate_refresh_count"] == 1
    assert state["planner_routes"] == [
        {
            "role_visit_index": 3,
            "revision_count": 0,
            "action": "REFRESH_CANDIDATES",
        }
    ]
    assert result["delivery"]["actor_output"] == "draft one"
    assert state["terminal_disposition"]["stage"] == "perception"
    assert state["terminal_disposition"]["rejected_contact"] == rejected_contact
    assert "partial refreshed perception" not in json.dumps(result)


def test_finite_revised_solver_preserves_previous_solver_without_failed_visit():
    solver, solver_script = _node(
        "solver",
        "solver",
        ["draft one", _FiniteResponse("partial revised answer", "content_filter")],
        valid=True,
    )
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["REVISE"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=1,
        finite_completion_policy="deliver-latest-or-abstain",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    rejected_contact = _source_contact(solver_script.completions[-1])
    assert [visit["stage"] for visit in state["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
    ]
    assert state["revision_count"] == 1
    assert result["delivery"]["actor_output"] == "draft one"
    assert state["terminal_disposition"] == {
        "reason": "finite_completion",
        "finish_reason": "content_filter",
        "role_id": "solver",
        "stage": "solver",
        "revision_count": 1,
        "planner_accepted": False,
        "rejected_contact": rejected_contact,
    }
    assert "partial revised answer" not in json.dumps(result)


def test_interrupted_reviewer_keeps_completed_tool_and_finite_contacts_separate():
    completions: list[CoreCompletion] = []
    invoked: list[int] = []

    def reviewer_request(request):
        serial = 3 + len(completions)
        if not completions:
            tool_calls = [
                {
                    "id": "inspect-1",
                    "type": "function",
                    "function": {
                        "name": "inspect",
                        "arguments": '{"value":4}',
                    },
                }
            ]
            completion = _completion(
                "Inspect the draft.",
                request.context.agent_contact_id,
                serial,
                finish_reason="tool_calls",
                tool_calls=tool_calls,
            )
        else:
            completion = _completion(
                "partial reviewer conclusion",
                request.context.agent_contact_id,
                serial,
                finish_reason="length",
            )
        completions.append(completion)
        return completion

    card = ToolCard(
        id="inspect",
        name="inspect",
        description="Inspect a synthetic integer.",
        input_params={
            "type": "object",
            "properties": {"value": {"type": "integer"}},
            "required": ["value"],
            "additionalProperties": False,
        },
        stateless=True,
        idempotent=True,
    )
    reviewer = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="reviewer",
            role_kind="reviewer",
            prompt="Review.",
            max_iterations=3,
            ability_names=("inspect",),
        ),
        metered_request=reviewer_request,
        contact_context_provider=lambda index: NativeRoleContactContext(
            sample_id="sample-1",
            agent_contact_id=f"reviewer-contact-{index + 1}",
        ),
        abilities=(
            LocalFunction(
                card=card,
                func=lambda value: invoked.append(value) or {"value": value},
            ),
        ),
        tool_allowed=lambda role, name: role == "reviewer" and name == "inspect",
    )
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    planner, _ = _node("planner", "planner", ["unused"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        finite_completion_policy="deliver-latest-or-abstain",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    expected_contacts = [_source_contact(completion) for completion in completions]
    assert invoked == [4]
    assert len(completions) == 2
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception",
        "solver",
    ]
    assert result["state"]["interrupted_role"] == {
        "role_id": "reviewer",
        "stage": "review",
        "execution_receipt": {
            "contacts": expected_contacts,
            "final_contact": expected_contacts[-1],
        },
    }
    assert result["state"]["terminal_disposition"]["rejected_contact"] == (
        expected_contacts[-1]
    )
    assert result["delivery"]["actor_output"] == "draft one"
    assert "partial reviewer conclusion" not in json.dumps(result)


def test_finite_completion_policy_default_and_invalid_value_are_strict():
    spec = NativeEpisodeSpec(
        episode_id="strict-default",
        max_revisions=0,
        actions=NativeEpisodeActions(
            accept="ACCEPT",
            revise="REVISE",
            acquire="ACQUIRE",
        ),
    )
    assert spec.finite_completion_policy == "raise"

    with pytest.raises(ValueError, match="finite_completion_policy"):
        NativeEpisodeSpec(
            episode_id="invalid-policy",
            max_revisions=0,
            actions=spec.actions,
            finite_completion_policy="deliver-partial",
        )

    solver, _ = _node("solver", "solver", ["unused"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["unused"])
    planner, _ = _node("planner", "planner", ["unused"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        perception_values=[_FiniteResponse("partial", "length")],
    )
    with pytest.raises(NativeEpisodeError, match="native episode node failed"):
        asyncio.run(workflow.invoke_direct("query", ()))


@pytest.mark.parametrize("mismatch", ["role", "contact"])
def test_finite_terminalization_rejects_interrupted_custody_mismatch(mismatch):
    checkpoint = native_episode_module._RoleCheckpoint()
    checkpoint.capture(
        state={
            "latest_solver": None,
            "revision_count": 0,
            "role_visits": [],
        },
        role_id="reviewer",
        stage="review",
    )
    completion = _completion(
        "partial",
        "reviewer-contact-1",
        1,
        finish_reason="length",
    )
    error = FrozenCoreRoleFiniteCompletionError(
        completion=completion,
        finish_reason="length",
        original_message=completion.original_message,
    )
    contact = _source_contact(completion)
    error.role_id = "planner" if mismatch == "role" else "reviewer"
    receipt_contact = dict(contact)
    if mismatch == "contact":
        receipt_contact["request_id"] = "wrong-request"
    error.execution_receipt = {
        "contacts": [receipt_contact],
        "final_contact": receipt_contact,
    }

    with pytest.raises(NativeEpisodeError, match="does not match"):
        native_episode_module._finite_terminal_outcome(error, checkpoint)


def test_finite_checkpoint_is_isolated_between_concurrent_invocations(monkeypatch):
    solver, _ = _node("solver", "solver", ["unused"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["unused"])
    planner, _ = _node("planner", "planner", ["unused"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        finite_completion_policy="deliver-latest-or-abstain",
    )
    checkpoints: list[object] = []

    class FiniteWorkflow:
        def __init__(self, checkpoint):
            self.checkpoint = checkpoint

        async def invoke(self, *, inputs, session):
            del session
            query = inputs["original_query"]
            await asyncio.sleep(0 if query == "second" else 0.01)
            self.checkpoint.capture(
                state={
                    "original_query": query,
                    "latest_solver": None,
                    "revision_count": 0,
                    "role_visits": [],
                    "accepted_solver_receipt": None,
                },
                role_id="perception",
                stage="perception",
            )
            serial = 1 if query == "first" else 2
            completion = _completion(
                f"partial {query}",
                f"{query}-contact",
                serial,
                finish_reason="length",
            )
            error = FrozenCoreRoleFiniteCompletionError(
                completion=completion,
                finish_reason="length",
                original_message=completion.original_message,
            )
            contact = _source_contact(completion)
            error.role_id = "perception"
            error.execution_receipt = {
                "contacts": [contact],
                "final_contact": contact,
            }
            raise RuntimeError("wrapped finite completion") from error

    def build(checkpoint):
        checkpoints.append(checkpoint)
        return FiniteWorkflow(checkpoint)

    monkeypatch.setattr(workflow, "_build", build)

    async def invoke_both():
        return await asyncio.gather(
            workflow.invoke_direct("first", ()),
            workflow.invoke_direct("second", ()),
        )

    first, second = asyncio.run(invoke_both())

    assert len(checkpoints) == 2
    assert checkpoints[0] is not checkpoints[1]
    assert first["state"]["original_query"] == "first"
    assert second["state"]["original_query"] == "second"
    assert first["state"]["terminal_disposition"]["rejected_contact"][
        "agent_contact_id"
    ] == "first-contact"
    assert second["state"]["terminal_disposition"]["rejected_contact"][
        "agent_contact_id"
    ] == "second-contact"


@pytest.mark.parametrize("failure_kind", ["unknown_finish", "invalid_source"])
def test_opt_in_policy_does_not_downgrade_other_source_failures(failure_kind):
    def failed_perception(request):
        completion = _completion(
            "partial",
            request.context.agent_contact_id,
            1,
            finish_reason=(
                "server_error" if failure_kind == "unknown_finish" else "length"
            ),
        )
        if failure_kind == "invalid_source":
            completion = dataclasses.replace(completion, response_sha256="")
        return completion

    perception = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id="perception",
            role_kind="perception",
            prompt="Perceive.",
            max_iterations=1,
        ),
        metered_request=failed_perception,
        contact_context=NativeRoleContactContext(
            sample_id="sample-1",
            agent_contact_id="perception-contact-1",
        ),
    )
    solver, _ = _node("solver", "solver", ["unused"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["unused"])
    planner, _ = _node("planner", "planner", ["unused"])
    workflow = build_native_episode(
        spec=NativeEpisodeSpec(
            episode_id=failure_kind,
            max_revisions=0,
            actions=NativeEpisodeActions(
                accept="ACCEPT",
                revise="REVISE",
                acquire="ACQUIRE",
            ),
            finite_completion_policy="deliver-latest-or-abstain",
        ),
        nodes=NativeEpisodeNodes(
            perception=perception,
            solver=solver,
            reviewer=reviewer,
            planner=planner,
        ),
        role_input_builder=lambda role, _state: f"Run {role}.",
    )

    with pytest.raises(NativeEpisodeError, match="native episode node failed"):
        asyncio.run(workflow.invoke_direct("query", ()))
