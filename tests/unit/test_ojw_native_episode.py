"""Model-free execution tests for the native conditional role episode."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass, field

import pytest

from speech_aware_evidence_acquisition.rails.core_client import CoreCompletion
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    NativeEpisodeActions,
    NativeEpisodeError,
    NativeEpisodeNodes,
    NativeEpisodeSpec,
    build_native_episode,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeRoleContactContext,
    NativeRoleNode,
    NativeRoleNodeSpec,
)


def _completion(text: str, contact_id: str, serial: int) -> CoreCompletion:
    request_id = f"request-{serial}"
    wire = json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
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
        tool_calls_json=b"null",
        wire_response_bytes=wire,
    )


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


@dataclass
class _Script:
    values: list[str]
    requests: list[object] = field(default_factory=list)

    def __call__(self, request):
        self.requests.append(request)
        if not self.values:
            raise AssertionError("script exhausted")
        serial = sum(len(script.requests) for script in _ALL_SCRIPTS)
        return _completion(self.values.pop(0), request.context.agent_contact_id, serial)


_ALL_SCRIPTS: list[_Script] = []


def _node(role_id: str, role_kind: str, values: list[str], *, valid=False):
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


def _episode(*, solver, reviewer, planner, max_revisions=1, acquisition=None):
    perception, perception_script = _node("perception", "perception", ["heard"])
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
