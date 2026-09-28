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
from speech_aware_evidence_acquisition.rails.commit_policies import (
    ParsedSlurpAnswer, SolverSampleVote, commit_plurality_support_v1,
)
from speech_aware_evidence_acquisition.rails.native_episode_receipt import (
    is_illegal_planner_route,
    validate_native_episode_delivery_receipt,
    validate_solver_group_receipt,
)
from speech_aware_evidence_acquisition.rails.runner import RailsRunnerError
from speech_aware_evidence_acquisition.reproduction.ojw.native_group_solver import (
    GroupedSolverRoleNode,
)
from speech_aware_evidence_acquisition.reproduction.slurp_scoring import SlotEntity
from speech_aware_evidence_acquisition.reproduction.ojw import (
    native_episode as native_episode_module,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_episode import (
    PLANNER_ACTION_ILLEGAL,
    PLANNER_ACTION_ILLEGAL_DISPOSITION,
    PLANNER_ACTION_ILLEGAL_SCHEMA,
    PLANNER_ACTION_RECORD_CHARS,
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


@dataclass(frozen=True)
class _SealRefusalResponse:
    """Item E43: the shape ``rails.runner.capture_completion`` produces when
    a structured-output contract's own parser refuses an otherwise-
    authoritative ("stop") completion -- a ``RailsRunnerError`` tagged with
    the exact completion it refused, raised instead of returned. Standing in
    for ``capture_completion`` here, exactly as an ordinary string return
    stands in for a completion the seal accepted.

    ``text`` is the completion's OWN (refused) answer bytes -- present only
    on the quarantined ``CoreCompletion``, never sealed. ``message`` is the
    refusal's STRUCTURAL reason, exactly as a real
    ``rails.solver_citation.SolverCitationError`` message is: a description
    of the contract violation, never a quote of the answer it refused.
    """

    text: str
    message: str = (
        "cited-answer contract refused: intent citations must be unique non-blank ids"
    )


@dataclass(frozen=True)
class _InfrastructureFailure:
    """A transport/server-shaped failure with no seal-refusal tag at all --
    the class of error item E43 must keep aborting the arm.
    """

    message: str


@dataclass
class _Script:
    values: list[str | _FiniteResponse | _SealRefusalResponse | _InfrastructureFailure]
    requests: list[object] = field(default_factory=list)
    completions: list[CoreCompletion] = field(default_factory=list)

    def __call__(self, request):
        self.requests.append(request)
        if not self.values:
            raise AssertionError("script exhausted")
        serial = sum(len(script.requests) for script in _ALL_SCRIPTS)
        value = self.values.pop(0)
        if isinstance(value, _InfrastructureFailure):
            raise RailsRunnerError(value.message)
        if isinstance(value, _FiniteResponse):
            completion = _completion(
                value.text,
                request.context.agent_contact_id,
                serial,
                finish_reason=value.finish_reason,
            )
        elif isinstance(value, _SealRefusalResponse):
            completion = _completion(
                value.text,
                request.context.agent_contact_id,
                serial,
            )
            self.completions.append(completion)
            refusal = RailsRunnerError(value.message)
            refusal.seal_refusal_completion = completion
            refusal.seal_refusal_role_id = request.role_id
            raise refusal
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


# E8c.  The two shapes the sealed B7a anchor trace actually carried at the
# Planner: a six-letter token outside {ACCEPT, REVISE}, and an 80-character
# response opening on a non-alphabetic character.  Before E8c either one
# aborted the whole 1,080-row campaign at the row that produced it.
ILLEGAL_TOKEN = "REJECT"
ILLEGAL_SENTENCE = (
    '"' + "the draft already answers the question and no revision is needed"
).ljust(80, ".")


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
    ("raw", "token"),
    [
        ("REVISE", "REVISE"),
        (
            '{"action":"REVISE","reason":"extra"}',
            '{"action":"REVISE","reason":"extra"}',
        ),
        (
            '{"action":"REVISE","action":"ACCEPT"}',
            '{"action":"REVISE","action":"ACCEPT"}',
        ),
        ('{"action":"UNKNOWN"}', "UNKNOWN"),
        ('{"action":"ACQUIRE"}', "ACQUIRE"),
        ('{"action":42}', '{"action":42}'),
    ],
)
def test_json_planner_action_malformed_extra_duplicate_or_unknown_seals_the_row(
    raw, token
):
    """E8c: the same row-level disposition under ``json-action-v1``.  A
    document that parses but names no registered action seals the ACTION it
    named; anything the strict parse refuses seals the raw output.  No
    structured control survives beside an illegal route, so the raw-source
    custody check has nothing to bind to the wrong one."""

    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", [raw])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        planner_output_format="json-action-v1",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    assert result["delivery"]["actor_output"] == "draft one"
    assert state["plan"] == raw
    assert "planner_control" not in state
    route = state["planner_routes"][-1]
    assert is_illegal_planner_route(route)
    assert route["action"] == token[:PLANNER_ACTION_RECORD_CHARS]
    assert route["action_sha256"] == hashlib.sha256(token.encode("utf-8")).hexdigest()
    assert state[PLANNER_ACTION_ILLEGAL_DISPOSITION]["count"] == 1
    assert validate_native_episode_delivery_receipt(
        state, error_type=NativeEpisodeError
    ).kind == "accepted"


def test_an_illegal_json_route_clears_an_earlier_visit_structured_control():
    """E8c: a legal REVISE leaves ``planner_control`` behind; the illegal
    route that follows must not inherit it, or the receipt would claim the
    previous visit's parsed action as this row's final control."""

    solver, _ = _node("solver", "solver", ["draft one", "draft two"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node(
        "planner", "planner", ['{"action":"REVISE"}', '{"action":"REJECT"}']
    )
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=1,
        planner_output_format="json-action-v1",
    )

    state = asyncio.run(workflow.invoke_direct("query", ()))["state"]

    assert state["planner_routes"][0] == {
        "role_visit_index": 3, "revision_count": 0, "action": "REVISE",
    }
    assert "planner_control" not in state
    assert state["planner_routes"][-1]["action"] == "REJECT"
    assert validate_native_episode_delivery_receipt(
        state, error_type=NativeEpisodeError
    ).kind == "accepted"


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


@pytest.mark.parametrize(
    "plan", [" ACCEPT", "accept", "UNKNOWN", ILLEGAL_TOKEN, ILLEGAL_SENTENCE]
)
def test_malformed_planner_action_seals_the_row_instead_of_failing_the_flight(plan):
    """E8c.  A Planner output that names no registered action is a ROW-LEVEL
    disposition: the committed draft is delivered unchanged through the same
    explicit-accept seal an ACCEPT takes, no further role is contacted, the
    revision budget is not spent, and the route plus the receipt mark say so
    with at most 32 characters of the token and its sha256."""

    solver, solver_script = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, reviewer_script = _node("reviewer", "reviewer", ["review one"])
    planner, planner_script = _node("planner", "planner", [plan])
    workflow, perception_script, _ = _episode(
        solver=solver, reviewer=reviewer, planner=planner
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    digest = hashlib.sha256(plan.encode("utf-8")).hexdigest()
    assert result["delivery"]["actor_output"] == "draft one"
    assert state["accepted_solver_receipt"] == _execution_receipt(
        text="draft one", contact_id="solver-contact-1", serial=2
    )
    assert "terminal_disposition" not in state
    assert state["revision_count"] == 0
    assert [visit["stage"] for visit in state["role_visits"]] == [
        "perception", "solver", "review", "planner",
    ]
    assert [len(script.requests) for script in (
        perception_script, solver_script, reviewer_script, planner_script
    )] == [1, 1, 1, 1]
    assert state["planner_routes"] == [
        {
            "role_visit_index": 3,
            "revision_count": 0,
            "action": plan[:PLANNER_ACTION_RECORD_CHARS],
            "legal": False,
            "disposition": PLANNER_ACTION_ILLEGAL_DISPOSITION,
            "action_sha256": digest,
            "action_chars": len(plan),
        },
    ]
    assert len(state["planner_routes"][0]["action"]) <= PLANNER_ACTION_RECORD_CHARS
    assert is_illegal_planner_route(state["planner_routes"][0])
    assert state[PLANNER_ACTION_ILLEGAL_DISPOSITION] == {
        "schema": PLANNER_ACTION_ILLEGAL_SCHEMA,
        "count": 1,
        "action_sha256": [digest],
    }
    # Under exact-text the sealed sha256 IS the Planner visit's own response
    # text hash, so the mark is bound to that actual contact.
    assert digest == state["role_visits"][3]["execution_receipt"]["final_contact"][
        "response_text_sha256"
    ]
    assert validate_native_episode_delivery_receipt(
        state, error_type=NativeEpisodeError
    ).kind == "accepted"


def test_an_eighty_character_planner_sentence_keeps_only_its_first_32_characters():
    """E8c (b): the truncation is what keeps draft text out of the record."""

    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", [ILLEGAL_SENTENCE])
    workflow, _, _ = _episode(solver=solver, reviewer=reviewer, planner=planner)

    route = asyncio.run(workflow.invoke_direct("query", ()))["state"]["planner_routes"][-1]

    assert len(ILLEGAL_SENTENCE) == 80
    assert not ILLEGAL_SENTENCE[0].isalpha()
    assert route["action_chars"] == 80
    assert len(route["action"]) == 32
    assert route["action"] == ILLEGAL_SENTENCE[:32]
    assert ILLEGAL_SENTENCE[32:] not in json.dumps(route)


def test_an_earlier_legal_route_stays_byte_identical_beside_an_illegal_one():
    """E8c (c): E8c adds keys to the ILLEGAL route only. A route the episode
    actually took as ACCEPT or REVISE records exactly the three keys it
    recorded before E8c, and the illegal route that follows spends no
    revision of its own."""

    solver, _ = _node("solver", "solver", ["draft one", "draft two"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", ["REVISE", ILLEGAL_TOKEN])
    workflow, _, _ = _episode(
        solver=solver, reviewer=reviewer, planner=planner, max_revisions=1
    )

    state = asyncio.run(workflow.invoke_direct("query", ()))["state"]

    assert state["planner_routes"][0] == {
        "role_visit_index": 3, "revision_count": 0, "action": "REVISE",
    }
    assert set(state["planner_routes"][1]) == {
        "role_visit_index", "revision_count", "action",
        "legal", "disposition", "action_sha256", "action_chars",
    }
    assert state["planner_routes"][1]["revision_count"] == 1
    # The REVISE spent the one revision; the illegal token spent none.
    assert state["revision_count"] == 1
    assert state["accepted_solver_receipt"] == _execution_receipt(
        text="draft two", contact_id="solver-contact-2", serial=5
    )


def test_the_reserved_illegal_routing_value_is_not_a_configurable_action():
    """E8c: the sentinel can never collide with a configured action."""

    with pytest.raises(ValueError, match="reserved illegal action"):
        NativeEpisodeActions(
            accept=PLANNER_ACTION_ILLEGAL, revise="REVISE", acquire="ACQUIRE"
        )
    with pytest.raises(ValueError, match="reserved illegal action"):
        NativeEpisodeSpec(
            episode_id="synthetic-episode",
            max_revisions=1,
            actions=NativeEpisodeActions(
                accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"
            ),
            refresh_action=PLANNER_ACTION_ILLEGAL,
            max_candidate_refreshes=1,
        )


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


def test_opt_in_terminal_delivery_still_refuses_an_invalid_solver_draft():
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


def test_the_acquire_unavailable_branch_still_refuses_loudly_when_forced():
    """E15.  The router keeps its "episode has no configured analytical
    acquisition role" refusal as defence in depth, and after E15 no episode
    built without an acquisition node can reach it: ACQUIRE is not in the
    graph's legal Planner action set, so such a token takes the retained-row
    disposition instead.  The only way left to reach the branch is to force
    ACQUIRE back into that set, and it must still refuse LOUDLY -- a graph
    that answered with no route to the action it took would be the worse
    failure.  This is what the early-ACQUIRE half of the pre-E15
    ``..._still_refuses_invalid_solver_and_early_acquire`` proof asserted on a
    real Planner output.
    """

    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review"])
    planner, _ = _node("planner", "planner", ["ACQUIRE"])
    forced, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=1,
        exhaustion_policy="deliver-latest-solver",
    )
    forced._planner_actions.add("ACQUIRE")
    with pytest.raises(NativeEpisodeError, match="no configured analytical acquisition"):
        asyncio.run(forced.invoke_direct("query", ()))


# ---------------------------------------------------------------------------
# E15 (2026-09-19).  Finding I-1 of the SLURP agent base-lock draft: under the
# flown ``exact-text`` format ACQUIRE was legal at the parser on EVERY
# episode, but an episode built with no acquisition node has no route that can
# execute it, so the token reached the unavailable-acquisition refusal and
# RAISED -- a whole flight died on one Planner word, exactly the failure class
# E8c removed for unregistered tokens.  After E15 the graph's own action set is
# the authority under both output formats, so ACQUIRE on such an episode is an
# illegal Planner output and its row is RETAINED.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "planner_output_format, planner_output",
    [("exact-text", "ACQUIRE"), ("json-action-v1", '{"action":"ACQUIRE"}')],
    ids=["exact-text", "json-action-v1"],
)
@pytest.mark.parametrize(
    "max_revisions, exhaustion_policy",
    [(1, "raise"), (0, "deliver-latest-solver")],
    ids=["first-revision", "terminal-revision"],
)
def test_acquire_without_an_acquisition_node_is_a_retained_row_not_a_flight_abort(
    planner_output_format, planner_output, max_revisions, exhaustion_policy
):
    """E15.  A SLURP-shaped episode -- no acquisition node -- whose Planner
    answers with the configured ACQUIRE token keeps its row: the committed
    Solver draft is delivered unchanged, no further role is contacted, no
    revision is spent, and the E8c disposition names what happened.  The
    episode does not raise, at the first revision or at the terminal one.
    """

    solver, solver_script = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, planner_script = _node("planner", "planner", [planner_output])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=max_revisions,
        exhaustion_policy=exhaustion_policy,
        planner_output_format=planner_output_format,
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    digest = hashlib.sha256(b"ACQUIRE").hexdigest()
    assert result["delivery"]["actor_output"] == "draft one"
    assert state["latest_solver"]["actor_output"] == "draft one"
    assert state["plan"] == planner_output
    assert "planner_control" not in state
    assert "terminal_disposition" not in state
    assert state["revision_count"] == 0
    assert [visit["stage"] for visit in state["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
    ]
    assert len(solver_script.requests) == len(planner_script.requests) == 1
    route = state["planner_routes"][-1]
    assert is_illegal_planner_route(route)
    assert route["action"] == "ACQUIRE"
    assert route["action_sha256"] == digest
    assert route["action_chars"] == len("ACQUIRE")
    assert state[PLANNER_ACTION_ILLEGAL_DISPOSITION] == {
        "schema": PLANNER_ACTION_ILLEGAL_SCHEMA,
        "count": 1,
        "action_sha256": [digest],
    }
    assert validate_native_episode_delivery_receipt(
        state, error_type=NativeEpisodeError
    ).kind == "accepted"


@pytest.mark.parametrize(
    "planner_output_format, acquire_output, accept_output",
    [
        ("exact-text", "ACQUIRE", "ACCEPT"),
        ("json-action-v1", '{"action":"ACQUIRE"}', '{"action":"ACCEPT"}'),
    ],
    ids=["exact-text", "json-action-v1"],
)
def test_acquire_with_an_acquisition_node_still_routes_to_acquisition(
    planner_output_format, acquire_output, accept_output
):
    """E15 changes nothing for an episode that CAN acquire: ACQUIRE stays in
    the legal set, the analytical role is contacted, the revision advances and
    the route is an ordinary legal route carrying no disposition.
    """

    solver, _ = _node("solver", "solver", ["draft one", "draft two"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", [acquire_output, accept_output])
    acquisition, acquisition_script = _node("analyst", "reviewer", ["acquired fact"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        acquisition=acquisition,
        planner_output_format=planner_output_format,
    )

    result = asyncio.run(workflow.invoke_direct("query", ("candidate",)))

    state = result["state"]
    assert result["delivery"]["actor_output"] == "draft two"
    assert state["acquisition"] == "acquired fact"
    assert len(acquisition_script.requests) == 1
    assert [visit["stage"] for visit in state["role_visits"]] == [
        "perception",
        "solver",
        "review",
        "planner",
        "acquisition",
        "solver",
        "review",
        "planner",
    ]
    assert [route["action"] for route in state["planner_routes"]] == [
        "ACQUIRE",
        "ACCEPT",
    ]
    assert not any(
        is_illegal_planner_route(route) for route in state["planner_routes"]
    )
    assert PLANNER_ACTION_ILLEGAL_DISPOSITION not in state
    assert validate_native_episode_delivery_receipt(
        state, error_type=NativeEpisodeError
    ).kind == "accepted"


@pytest.mark.parametrize("planner_action", ("REVISE", "ACQUIRE"))
def test_terminal_exhaustion_delivery_is_opt_in_and_records_actual_planner_action(
    planner_action,
):
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", [planner_action])
    # E15: ACQUIRE is a legal Planner action only on an episode that CAN
    # acquire, so this proof supplies the acquisition node its Planner names.
    # The node is never contacted: at the terminal revision the router sends
    # ACQUIRE straight to the terminal delivery, exactly as it sends REVISE.
    acquisition, acquisition_script = _node("analyst", "reviewer", [])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        acquisition=acquisition,
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
    assert acquisition_script.requests == []
    assert state["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": planner_action}
    ]


def test_opt_in_terminal_delivery_binds_the_last_revision_solver():
    solver, _ = _node(
        "solver", "solver", ["draft one", "draft two"], valid=True
    )
    reviewer, _ = _node("reviewer", "reviewer", ["review one", "review two"])
    planner, _ = _node("planner", "planner", ["REVISE", "ACQUIRE"])
    # E15: see the note in the parametrized proof above -- a terminal ACQUIRE
    # needs an episode that can acquire, and the node is never contacted.
    acquisition, acquisition_script = _node("analyst", "reviewer", [])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        acquisition=acquisition,
        max_revisions=1,
        exhaustion_policy="deliver-latest-solver",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    assert acquisition_script.requests == []
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


# ---------------------------------------------------------------------------
# E1: review loop off (M0). Reviewer and Planner never get a node, let alone
# a contact; the Solver's answer is delivered through the same explicit
# accept every ACCEPT route uses.
# ---------------------------------------------------------------------------


def test_review_loop_disabled_delivers_solver_directly_with_two_contacts():
    perception, perception_script = _node("perception", "perception", ["heard"])
    solver, solver_script = _node("solver", "solver", ["draft one"], valid=True)
    seen: list[tuple[str, dict[str, object]]] = []

    def role_input(role_id, state):
        seen.append((role_id, dict(state)))
        return f"{role_id}: use the supplied episode state."

    workflow = build_native_episode(
        spec=NativeEpisodeSpec(
            episode_id="review-off-episode",
            max_revisions=0,
            actions=NativeEpisodeActions(
                accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"
            ),
            review_loop_enabled=False,
        ),
        nodes=NativeEpisodeNodes(perception=perception, solver=solver),
        role_input_builder=role_input,
    )

    result = asyncio.run(workflow.invoke_direct("original query", ()))

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
    # No Reviewer or Planner ever ran: no visit, no route, no state field.
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception",
        "solver",
    ]
    assert [visit["role_id"] for visit in result["state"]["role_visits"]] == [
        "perception",
        "solver",
    ]
    assert result["state"]["planner_routes"] == []
    assert result["state"]["review"] is None
    assert result["state"]["plan"] is None
    assert [role for role, _ in seen] == ["perception", "solver"]
    assert len(perception_script.requests) == 1
    assert len(solver_script.requests) == 1


def test_review_loop_disabled_refuses_a_present_reviewer_or_planner_node():
    perception, _ = _node("perception", "perception", ["heard"])
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["unused"])
    spec = NativeEpisodeSpec(
        episode_id="review-off-episode",
        max_revisions=0,
        actions=NativeEpisodeActions(accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"),
        review_loop_enabled=False,
    )

    with pytest.raises(ValueError, match="omitted when the review loop is disabled"):
        build_native_episode(
            spec=spec,
            nodes=NativeEpisodeNodes(perception=perception, solver=solver, reviewer=reviewer),
            role_input_builder=lambda role, _state: f"Run {role}.",
        )


def test_review_loop_disabled_requires_max_revisions_zero():
    with pytest.raises(ValueError, match="review loop off requires max_revisions 0"):
        NativeEpisodeSpec(
            episode_id="bad-review-off",
            max_revisions=1,
            actions=NativeEpisodeActions(accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"),
            review_loop_enabled=False,
        )


def test_review_loop_enabled_defaults_true_and_still_requires_reviewer_and_planner():
    perception, _ = _node("perception", "perception", ["heard"])
    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    spec = NativeEpisodeSpec(
        episode_id="ordinary-episode",
        max_revisions=1,
        actions=NativeEpisodeActions(accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"),
    )
    assert spec.review_loop_enabled is True

    with pytest.raises(ValueError, match="reviewer must be a reviewer NativeRoleNode"):
        build_native_episode(
            spec=spec,
            nodes=NativeEpisodeNodes(perception=perception, solver=solver),
            role_input_builder=lambda role, _state: f"Run {role}.",
        )


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
    """An unconfigured refresh action is not a registered action, so (E8c) it
    seals the row as a disposition -- and, the point of this test, Perception
    is still never visited a second time."""

    solver, _ = _node("solver", "solver", ["draft one"], valid=True)
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["REFRESH_CANDIDATES"])
    workflow, perception_script, _ = _episode(
        solver=solver, reviewer=reviewer, planner=planner,
    )
    result = asyncio.run(workflow.invoke_direct("query", ()))
    assert len(perception_script.requests) == 1
    assert result["delivery"]["actor_output"] == "draft one"
    route = result["state"]["planner_routes"][-1]
    assert is_illegal_planner_route(route)
    assert route["action"] == "REFRESH_CANDIDATES"


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


# Item E43 (2026-09-28, coordinator ruling on
# docs/results/2026-09-28-slurp-comp1-citation-abort-diagnosis.md): the
# COMP-1/B7a/B8b-anchor abort class -- a structured-output contract's seal
# refusing an otherwise-authoritative ("stop") completion had no per-row
# disposition and aborted the whole arm at one row. These four tests prove
# the containment: (1) abstain with no prior Solver, (2) deliver the latest
# Solver when one exists, (3) an untagged (infrastructure-shaped) error
# still aborts, (4) the refused answer's own bytes never enter the receipt.


def test_seal_refusal_policy_abstains_with_no_prior_solver():
    solver, solver_script = _node(
        "solver",
        "solver",
        [_SealRefusalResponse("draft one")],
        valid=True,
    )
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["ACCEPT"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        finite_completion_policy="deliver-latest-or-abstain",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    state = result["state"]
    rejected_contact = _source_contact(solver_script.completions[-1])
    assert [visit["stage"] for visit in state["role_visits"]] == ["perception"]
    assert state["terminal_disposition"] == {
        "reason": "seal_refusal",
        "role_id": "solver",
        "stage": "solver",
        "revision_count": 0,
        "planner_accepted": False,
        "rejected_contact": rejected_contact,
        "seal_refusal": {
            "error_class": "RailsRunnerError",
            "message": (
                "cited-answer contract refused: intent citations must be "
                "unique non-blank ids"
            ),
        },
    }
    assert state["interrupted_role"] == {
        "role_id": "solver",
        "stage": "solver",
        "execution_receipt": {
            "contacts": [rejected_contact],
            "final_contact": rejected_contact,
        },
    }
    assert "accepted_solver_receipt" not in state
    assert "terminal_solver_receipt" not in state
    assert result["delivery"] == {
        "actor_output": "",
        "result_type": "abstention",
        "delivery_eligible": False,
    }
    assert state["abstention_receipt"] == {"source_contact": rejected_contact}
    assert "draft one" not in json.dumps(result)


def test_seal_refusal_policy_delivers_latest_solver_when_one_exists():
    solver, solver_script = _node(
        "solver",
        "solver",
        ["draft one", _SealRefusalResponse("draft two - refused")],
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
        "reason": "seal_refusal",
        "role_id": "solver",
        "stage": "solver",
        "revision_count": 1,
        "planner_accepted": False,
        "rejected_contact": rejected_contact,
        "seal_refusal": {
            "error_class": "RailsRunnerError",
            "message": (
                "cited-answer contract refused: intent citations must be "
                "unique non-blank ids"
            ),
        },
    }
    assert state["terminal_solver_receipt"] == result["delivery"]["execution_receipt"]
    assert "abstention_receipt" not in state
    assert "draft two - refused" not in json.dumps(result)


def test_seal_refusal_untagged_infrastructure_error_still_aborts():
    solver, _ = _node(
        "solver",
        "solver",
        [_InfrastructureFailure("model service unavailable")],
        valid=True,
    )
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["ACCEPT"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        # Deliberately the SAME lenient policy the abstain/deliver-latest
        # tests use: an infrastructure-shaped RailsRunnerError with no
        # seal_refusal_completion tag must abort even though the policy
        # would tolerate a TAGGED seal refusal.
        finite_completion_policy="deliver-latest-or-abstain",
    )

    with pytest.raises(NativeEpisodeError, match="model service unavailable"):
        asyncio.run(workflow.invoke_direct("query", ()))


def test_seal_refusal_receipt_never_carries_the_refused_answer_text():
    forbidden = "SECRET_ANSWER_BYTES_never_sealed"
    solver, _ = _node(
        "solver",
        "solver",
        [_SealRefusalResponse(forbidden)],
        valid=True,
    )
    reviewer, _ = _node("reviewer", "reviewer", ["review one"])
    planner, _ = _node("planner", "planner", ["ACCEPT"])
    workflow, _, _ = _episode(
        solver=solver,
        reviewer=reviewer,
        planner=planner,
        max_revisions=0,
        finite_completion_policy="deliver-latest-or-abstain",
    )

    result = asyncio.run(workflow.invoke_direct("query", ()))

    assert forbidden not in json.dumps(result)
    assert result["state"]["terminal_disposition"]["seal_refusal"] == {
        "error_class": "RailsRunnerError",
        "message": (
            "cited-answer contract refused: intent citations must be "
            "unique non-blank ids"
        ),
    }


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


# --- E2b (SLURP v2 base program M2 live wiring): GroupedSolverRoleNode at the
# graph's "solver" position, both review-off and review-loop shapes. Model-
# free: five scripted Solver answers per grouped visit, no rails.runner. ---

_SOLVER_ANSWERS_3_2_SPLIT = [
    json.dumps({"scenario": "alarm_set", "action": "set", "entities": []}),
    json.dumps({"scenario": "alarm_set", "action": "set", "entities": []}),
    json.dumps({"scenario": "alarm_set", "action": "set", "entities": []}),
    json.dumps({"scenario": "alarm_remove", "action": "remove", "entities": []}),
    json.dumps({"scenario": "alarm_remove", "action": "remove", "entities": []}),
]


def _grouped_solver_node(role_id: str, answers: list[str], *, samples: int):
    """A grouped Solver visit: an inner NativeRoleNode whose
    contact_context_provider tags sample_index 0..samples-1, wrapped in
    GroupedSolverRoleNode -- the SAME composition rails.runner.
    _invoke_native_role_episode builds for a samples >= 2 Solver role."""

    script = _Script(list(answers))
    _ALL_SCRIPTS.append(script)
    inner = NativeRoleNode(
        spec=NativeRoleNodeSpec(
            role_id=role_id, role_kind="solver",
            prompt=f"Act as the {role_id}.", max_iterations=1,
        ),
        metered_request=script,
        contact_context_provider=lambda index, role=role_id: NativeRoleContactContext(
            sample_id="sample-1", agent_contact_id=f"{role}-contact-{index + 1}",
            sample_index=index,
        ),
    )
    node = GroupedSolverRoleNode(
        inner=inner, samples=samples, fragment_seed=1000,
        decoding_overrides={"temperature": 0.7, "seed_offset": 0},
        commit={
            "policy": "saea-commit-plurality-support-v1",
            "min_support": 3, "similarity_threshold": 0.8,
        },
        delivery_allowed=lambda _role, output: bool(output.strip()),
    )
    return node, script


def test_grouped_solver_visit_review_off_delivers_the_commit_answer_with_full_custody():
    perception, perception_script = _node("perception", "perception", ["heard"])
    grouped, inner_script = _grouped_solver_node("solver", _SOLVER_ANSWERS_3_2_SPLIT, samples=5)
    seen: list[tuple[str, dict[str, object]]] = []

    def role_input(role_id, state):
        seen.append((role_id, dict(state)))
        return f"{role_id}: use the supplied episode state."

    workflow = build_native_episode(
        spec=NativeEpisodeSpec(
            episode_id="grouped-review-off-episode",
            max_revisions=0,
            actions=NativeEpisodeActions(accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"),
            review_loop_enabled=False,
        ),
        nodes=NativeEpisodeNodes(perception=perception, solver=grouped),
        role_input_builder=role_input,
    )

    result = asyncio.run(workflow.invoke_direct("original query", ()))
    delivery = result["delivery"]

    # Exactly 1 (Perception) + N (grouped Solver samples) contacts -- N = 5.
    assert len(perception_script.requests) == 1
    assert len(inner_script.requests) == 5
    assert delivery["role_id"] == "solver"
    assert delivery["result_type"] == "answer"
    assert delivery["delivery_eligible"] is True
    # The delivered answer is the commit policy's plurality winner (3 of 5).
    assert json.loads(delivery["actor_output"]) == {
        "scenario": "alarm_set", "action": "set", "entities": [],
    }
    # execution_receipt concatenates every sample's own contact, in order.
    contacts = delivery["execution_receipt"]["contacts"]
    assert [c["agent_contact_id"] for c in contacts] == [
        f"solver-contact-{i + 1}" for i in range(5)
    ]
    assert delivery["execution_receipt"]["final_contact"] == contacts[-1]
    # Full custody of every raw sample plus commit provenance.
    group = delivery["solver_group"]
    assert group["commit_policy_id"] == "saea-commit-plurality-support-v1"
    assert [s["sample_index"] for s in group["samples"]] == [0, 1, 2, 3, 4]
    assert [s["parse_status"] for s in group["samples"]] == ["ok"] * 5
    assert [json.loads(a) for a in _SOLVER_ANSWERS_3_2_SPLIT] == [
        s["parsed_answer"] for s in group["samples"]
    ]
    assert len({s["seed"] for s in group["samples"]}) == 5
    assert group["delivered"]["intent_support"] == 3
    assert group["delivered"]["intent_member_sample_indices"] == [0, 1, 2]
    assert group["delivered"]["entities"] == []
    # latest_solver/accepted_solver_receipt/role_visits carry solver_group
    # through unchanged (native_episode._ApplyRole/_Accept never read it).
    assert result["state"]["latest_solver"] == delivery
    assert result["state"]["accepted_solver_receipt"] == delivery["execution_receipt"]
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception", "solver",
    ]
    assert "solver_group" not in result["state"]["role_visits"][1]["execution_receipt"]


def test_grouped_solver_visit_flows_through_the_review_loop_to_delivery():
    grouped, inner_script = _grouped_solver_node("solver", _SOLVER_ANSWERS_3_2_SPLIT, samples=5)
    reviewer, reviewer_script = _node("reviewer", "reviewer", ["review one"])
    planner, planner_script = _node("planner", "planner", ["ACCEPT"])
    workflow, perception_script, seen = _episode(solver=grouped, reviewer=reviewer, planner=planner)

    result = asyncio.run(
        workflow.invoke_direct("original query", ({"intent_id": "intent-a"},))
    )
    delivery = result["delivery"]

    # Exactly 1 (Perception) + N (grouped Solver) + 1 (Reviewer) + 1 (Planner).
    assert len(perception_script.requests) == 1
    assert len(inner_script.requests) == 5
    assert len(reviewer_script.requests) == 1
    assert len(planner_script.requests) == 1
    assert json.loads(delivery["actor_output"]) == {
        "scenario": "alarm_set", "action": "set", "entities": [],
    }
    assert delivery["solver_group"]["delivered"]["intent_support"] == 3
    assert result["state"]["review"] == "review one"
    assert result["state"]["plan"] == "ACCEPT"
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception", "solver", "review", "planner",
    ]


# ---------------------------------------------------------------------------
# E2b (SLURP v2 base program M2 live wiring): GroupedSolverRoleNode at the
# "solver" graph position. No rails.runner/MeteredNativeSpeechRequest here --
# _Script bypasses request composition entirely, so these tests are pure
# proof that native_episode.py's graph (_ApplyRole/_Accept/_TerminalDelivery,
# build_native_episode's node-type check) carries solver_group through
# unchanged, for both episode shapes.
# ---------------------------------------------------------------------------

_GROUPED_ANSWERS = [
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six am"}]},
    {"scenario": "alarm", "action": "set", "entities": [{"type": "time", "filler": "six a m"}]},
    {"scenario": "alarm", "action": "cancel", "entities": []},
]
_GROUPED_COMMIT = {
    "policy": "saea-commit-plurality-support-v1",
    "min_support": 2,
    "similarity_threshold": 0.8,
}


def _grouped_answer_text(answer):
    import json

    return json.dumps(answer, ensure_ascii=False, sort_keys=True)


def _expected_grouped_actor_output():
    votes = [
        SolverSampleVote(
            sample_index=index,
            parsed=ParsedSlurpAnswer(
                scenario=answer["scenario"], action=answer["action"],
                entities=tuple(
                    SlotEntity(type=entity["type"], filler=entity["filler"])
                    for entity in answer["entities"]
                ),
            ),
        )
        for index, answer in enumerate(_GROUPED_ANSWERS)
    ]
    outcome = commit_plurality_support_v1(votes, **{
        k: v for k, v in _GROUPED_COMMIT.items() if k != "policy"
    })
    import json

    return json.dumps(
        {
            "scenario": outcome.answer.scenario,
            "action": outcome.answer.action,
            "entities": [
                {"type": entity.type, "filler": entity.filler}
                for entity in outcome.answer.entities
            ],
        },
        ensure_ascii=False, sort_keys=True,
    )


def test_grouped_solver_review_off_delivers_the_commit_policys_aggregated_answer():
    perception, _ = _node("perception", "perception", ["heard"])
    inner_solver, inner_script = _node(
        "solver", "solver",
        [_grouped_answer_text(answer) for answer in _GROUPED_ANSWERS],
    )
    grouped_solver = GroupedSolverRoleNode(
        inner=inner_solver, samples=3, fragment_seed=500,
        decoding_overrides={"temperature": 0.7, "seed_offset": 0},
        commit=_GROUPED_COMMIT,
    )
    seen: list[tuple[str, dict[str, object]]] = []

    def role_input(role_id, state):
        seen.append((role_id, dict(state)))
        return f"{role_id}: use the supplied episode state."

    workflow = build_native_episode(
        spec=NativeEpisodeSpec(
            episode_id="grouped-review-off-episode",
            max_revisions=0,
            actions=NativeEpisodeActions(
                accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"
            ),
            review_loop_enabled=False,
        ),
        nodes=NativeEpisodeNodes(perception=perception, solver=grouped_solver),
        role_input_builder=role_input,
    )

    result = asyncio.run(workflow.invoke_direct("original query", ()))

    delivery = result["delivery"]
    assert delivery["role_id"] == "solver"
    assert delivery["result_type"] == "answer"
    assert delivery["delivery_eligible"] is True
    assert delivery["actor_output"] == _expected_grouped_actor_output()
    assert len(delivery["execution_receipt"]["contacts"]) == 3
    assert delivery["execution_receipt"]["final_contact"] == (
        delivery["execution_receipt"]["contacts"][-1]
    )
    validate_solver_group_receipt(delivery["solver_group"], samples=3)
    assert delivery["solver_group"]["commit_policy_id"] == "saea-commit-plurality-support-v1"
    assert [r["sample_index"] for r in delivery["solver_group"]["samples"]] == [0, 1, 2]
    assert result["state"]["latest_solver"] == delivery
    assert result["state"]["accepted_solver_receipt"] == delivery["execution_receipt"]
    # One graph-level "solver" visit, THREE underlying model contacts: the
    # role input builder (and hence the episode graph) sees ONE visit.
    assert [role for role, _ in seen] == ["perception", "solver"]
    assert len(inner_script.requests) == 3


def test_grouped_solver_review_loop_on_delivers_solver_group_through_accept():
    perception, _ = _node("perception", "perception", ["heard"])
    inner_solver, inner_script = _node(
        "solver", "solver",
        [_grouped_answer_text(answer) for answer in _GROUPED_ANSWERS],
    )
    grouped_solver = GroupedSolverRoleNode(
        inner=inner_solver, samples=3, fragment_seed=501,
        decoding_overrides={"temperature": 0.7, "seed_offset": 0},
        commit=_GROUPED_COMMIT,
    )
    reviewer, reviewer_script = _node("reviewer", "reviewer", ["review one"])
    planner, planner_script = _node("planner", "planner", ["ACCEPT"])
    workflow, _, seen = _episode(solver=grouped_solver, reviewer=reviewer, planner=planner)

    result = asyncio.run(
        workflow.invoke_direct("original query", ({"intent_id": "intent-a"},))
    )

    delivery = result["delivery"]
    assert delivery["actor_output"] == _expected_grouped_actor_output()
    assert len(delivery["execution_receipt"]["contacts"]) == 3
    validate_solver_group_receipt(delivery["solver_group"], samples=3)
    assert result["state"]["latest_solver"] == delivery
    assert [visit["stage"] for visit in result["state"]["role_visits"]] == [
        "perception", "solver", "review", "planner",
    ]
    assert result["state"]["planner_routes"] == [
        {"role_visit_index": 3, "revision_count": 0, "action": "ACCEPT"},
    ]
    assert [role for role, _ in seen] == [
        "perception", "solver", "reviewer", "planner",
    ]
    assert len(inner_script.requests) == 3
    assert len(reviewer_script.requests) == 1
    assert len(planner_script.requests) == 1


def test_build_native_episode_refuses_a_grouped_node_at_a_non_solver_position():
    perception, _ = _node("perception", "perception", ["heard"])
    inner_solver, _ = _node("solver", "solver", [_grouped_answer_text(_GROUPED_ANSWERS[0])] * 3)
    grouped_solver = GroupedSolverRoleNode(
        inner=inner_solver, samples=3, fragment_seed=502,
        decoding_overrides={"temperature": 0.7, "seed_offset": 0},
        commit=_GROUPED_COMMIT,
    )

    with pytest.raises(ValueError, match="reviewer"):
        build_native_episode(
            spec=NativeEpisodeSpec(
                episode_id="misplaced-grouped-node",
                max_revisions=1,
                actions=NativeEpisodeActions(
                    accept="ACCEPT", revise="REVISE", acquire="ACQUIRE"
                ),
            ),
            nodes=NativeEpisodeNodes(
                perception=perception,
                solver=inner_solver,
                reviewer=grouped_solver,
                planner=_node("planner", "planner", ["ACCEPT"])[0],
            ),
            role_input_builder=lambda role, _state: f"Run {role}.",
        )
