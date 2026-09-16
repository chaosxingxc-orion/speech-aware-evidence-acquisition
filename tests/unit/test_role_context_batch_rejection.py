"""Typed role context preserves complete rejected native call batches."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.rails.knowledge import AgentStateArtifact
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeRole,
    select_native_role_history,
)
from speech_aware_evidence_acquisition.rails.native_tool_authority import (
    validate_native_call_rejection,
)
from speech_aware_evidence_acquisition.rails.phase_tools import build_phase_tools
from speech_aware_evidence_acquisition.rails.role_context import RoleContextError
from test_phase_native_tools import (
    LIVE,
    Custody,
    LiveProvider,
    NativeRoleProgram,
    role_episode_config,
    staged_role_episode,
)
from test_rails_runner import _knowledge_snapshot
from test_role_context import PHASE_IDS, compile_for, draft, native_pair, phase


def _rejected_batch():
    tool = build_phase_tools(
        role_episode_config(reviewer=(LIVE,)),
        NativeRoleProgram(),
        snapshot=_knowledge_snapshot(),
        live_speech_observations=LiveProvider(),
        tool_contact=Custody(),
    )
    solver = phase("solver", 1, draft("next Friday"))
    context = staged_role_episode(
        tool,
        request_id="request-batch",
        call_id="call-1",
        prior_states=(solver,),
    )
    completion = context.core_completions[0]
    calls = json.loads(completion.tool_calls_json)
    second = deepcopy(calls[0])
    second["id"] = "call-2"
    calls.append(second)
    raw_calls = json.dumps(calls, sort_keys=True, separators=(",", ":")).encode()
    wire = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": calls,
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        separators=(",", ":"),
    ).encode()
    completion = replace(
        completion,
        tool_calls_json=raw_calls,
        wire_response_bytes=wire,
    )
    context = SimpleNamespace(
        **{**context.__dict__, "core_completions": (completion,)}
    )
    steps = tool.reject_native_batch("reviewer", context)
    results = tuple(step.state for step in steps)
    for result in results:
        validate_native_call_rejection(json.loads(result.content))
    return (*context.agent_states, *results), tuple(
        result.state_id for result in results
    )


def _role():
    return NativeEpisodeRole(
        phase_id="reviewer",
        role_kind="reviewer",
        max_iterations=3,
        tool_names=(LIVE,),
        history_scope="latest-solver-and-local-tools",
    )


def _mixed_result(result: AgentStateArtifact) -> AgentStateArtifact:
    document = json.loads(result.content)
    document["schema"] = "saea-phase-tool-result-v2"
    return replace(result, content=json.dumps(document, sort_keys=True)).validate()


def test_rejected_batch_is_retained_once_in_order_without_evidence():
    states, local_ids = _rejected_batch()

    selected = select_native_role_history(
        role=_role(),
        solver_phase_id=PHASE_IDS["solver"],
        states=states,
        local_tool_result_ids=local_ids,
    )
    compilation = compile_for(
        "reviewer",
        states,
        local=local_ids,
    )

    assert selected == states
    assert [state.state_id for state in compilation.states[-3:]] == [
        states[-3].state_id,
        *local_ids,
    ]
    assert sum(state.state_id == states[-3].state_id for state in compilation.states) == 1
    result_rows = [
        row
        for row in compilation.receipt["retained"]
        if row["state_id"] in local_ids
    ]
    assert [row["state_id"] for row in result_rows] == list(local_ids)
    assert [row["native_tool_feedback"] for row in result_rows] == [
        {"kind": "rejected-action-feedback", "evidence_ids": []},
        {"kind": "rejected-action-feedback", "evidence_ids": []},
    ]
    assert compilation.receipt["available_evidence_ids"] == []


@pytest.mark.parametrize("change", ["omitted", "reordered", "duplicate", "mixed"])
def test_rejected_batch_tampering_is_refused_by_selector_and_compiler(change):
    states, local_ids = _rejected_batch()
    if change == "omitted":
        changed_ids = local_ids[:1]
    elif change == "reordered":
        changed_ids = tuple(reversed(local_ids))
    elif change == "duplicate":
        changed_ids = (local_ids[0], local_ids[0])
    else:
        states = (*states[:-1], _mixed_result(states[-1]))
        changed_ids = local_ids

    with pytest.raises(ValueError):
        select_native_role_history(
            role=_role(),
            solver_phase_id=PHASE_IDS["solver"],
            states=states,
            local_tool_result_ids=changed_ids,
        )
    with pytest.raises(RoleContextError):
        compile_for("reviewer", states, local=changed_ids)


def test_ordinary_native_result_receipts_keep_the_historical_shape():
    solver = phase("solver", 1, draft("next Friday"))
    source, result = native_pair(2)

    compilation = compile_for(
        "reviewer",
        (solver, source, result),
        local=(result.state_id,),
    )

    retained = next(
        row
        for row in compilation.receipt["retained"]
        if row["state_id"] == result.state_id
    )
    assert "native_tool_feedback" not in retained