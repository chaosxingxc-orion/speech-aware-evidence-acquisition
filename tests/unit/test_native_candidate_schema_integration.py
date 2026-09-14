"""Candidate-contract JSON Schema compatibility through the actual native episode."""

from __future__ import annotations

import asyncio
import json

import pytest

pytest.importorskip("openjiuwen")
from openjiuwen.core.foundation.tool import LocalFunction, ToolCard

import test_native_episode_runner as episode_runner
from speech_aware_evidence_acquisition.rails.native_tool_authority import (
    validate_native_tool_authority,
)
from speech_aware_evidence_acquisition.rails.phase_tools import (
    CANDIDATE_CONTRACT_TOOL,
    _native_tool_schema,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from test_candidate_contract_lookup import SOURCE_SHA256, SyntheticProvider, _result
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


def _candidate_wire_call(tool_id: str, candidate_ids: tuple[str, ...]) -> bytes:
    return json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I will inspect the competing candidate contracts.",
                        "tool_calls": [
                            {
                                "id": "call-candidate-contract-1",
                                "type": "function",
                                "function": {
                                    "name": tool_id,
                                    "arguments": json.dumps(
                                        {"candidate_ids": list(candidate_ids)},
                                        separators=(",", ":"),
                                    ),
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        },
        separators=(",", ":"),
    ).encode()


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize(
    "candidate_ids",
    (
        ("intent_alpha",),
        ("intent_alpha", "intent_beta"),
        ("intent_alpha", "intent_beta", "intent_gamma"),
        ("intent_gamma", "intent_alpha"),
    ),
)
def test_actual_episode_preserves_candidate_contract_lists_and_source_result(
    tmp_path,
    monkeypatch,
    candidate_ids,
):
    provider = SyntheticProvider(_result)
    provider.candidate_ids = ("intent_alpha", "intent_beta", "intent_gamma")
    original_builder = episode_runner.build_phase_tools

    def build_candidate_tools(config, *args, **kwargs):
        config = {
            **config,
            "phase_tools": {
                **config["phase_tools"],
                "reviewer": {
                    **config["phase_tools"]["reviewer"],
                    "candidate_limit": 3,
                },
            },
        }
        kwargs["candidate_contracts"] = provider
        return original_builder(config, *args, **kwargs)

    monkeypatch.setattr(
        episode_runner, "TASK_CONTRACT_TOOL", CANDIDATE_CONTRACT_TOOL
    )
    monkeypatch.setattr(episode_runner, "build_phase_tools", build_candidate_tools)
    monkeypatch.setattr(
        episode_runner,
        "_wire_tool_call",
        lambda tool_id: _candidate_wire_call(tool_id, candidate_ids),
    )

    harness = episode_runner._ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=1,
        max_contacts=9,
        planner_actions=("REVISE", "ACCEPT"),
        reviewer_task_tool=True,
    )
    try:
        summary = harness.run()
    finally:
        close_summary = harness.close()

    result = summary.results[0]
    assert result.final_response_text == "solver-answer:s1:visit:2"
    assert close_summary["request_count"] == len(result.contacts) == 8
    assert close_summary["cost"]["tool_calls"] == 1
    assert provider.requests == [candidate_ids]

    expected_arguments = {"candidate_ids": list(candidate_ids)}
    assert len(harness.tool_contacts) == 1
    contact = harness.tool_contacts[0]
    assert contact["tool_id"] == CANDIDATE_CONTRACT_TOOL
    assert contact["arguments"] == expected_arguments
    assert contact["source_authority_role"] == "reviewer"

    schema = _native_tool_schema(
        CANDIDATE_CONTRACT_TOOL, ("text",), candidate_limit=3
    )
    authority = validate_native_tool_authority(contact["source_authority"])
    assert authority["role_id"] == authority["phase_id"] == "reviewer"
    assert authority["selected_tool_names"] == [CANDIDATE_CONTRACT_TOOL]
    assert authority["selected_tool_schemas"] == [schema]
    first_reviewer = harness.prepared[("s1", "reviewer", 1, 1)]["rendered"]
    assert first_reviewer["tools"] == [schema]
    wire_array = first_reviewer["tools"][0]["function"]["parameters"]["properties"][
        "candidate_ids"
    ]
    assert wire_array == {
        "type": "array",
        "minItems": 1,
        "maxItems": 3,
        "uniqueItems": True,
        "items": {"type": "string", "minLength": 1},
    }

    for body in (
        harness.prepared[("s1", "reviewer", 1, 2)]["rendered"],
        harness.prepared[("s1", "solver", 2, 1)]["rendered"],
    ):
        messages = [
            message for message in body["messages"] if message["role"] == "tool"
        ]
        assert len(messages) == 1
        assert messages[0]["tool_call_id"] == "call-candidate-contract-1"
        document = json.loads(messages[0]["content"])
        assert document["result"]["request"]["candidate_ids"] == list(candidate_ids)
        assert document["result"]["source_sha256"] == SOURCE_SHA256

    assert harness.tools_for_phase.receipt()["attempts"] == 1
    assert harness.tools_for_phase.receipt()["completed"] == 1


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_pinned_local_function_reproduces_unique_items_conversion_failure():
    function = _native_tool_schema(
        CANDIDATE_CONTRACT_TOOL, ("text",), candidate_limit=3
    )["function"]

    async def source_handler(**arguments):
        return arguments

    old_adapter = LocalFunction(
        card=ToolCard(
            id=function["name"],
            name=function["name"],
            description=function["description"],
            input_params=function["parameters"],
        ),
        func=source_handler,
    )
    with pytest.raises(Exception, match="unique_items.*removed"):
        asyncio.run(
            old_adapter.invoke({"candidate_ids": ["intent_alpha", "intent_beta"]})
        )
