"""Exercise unchanged JSON schemas through the real framework Tool interface."""

import asyncio
from copy import deepcopy

import pytest

pytest.importorskip("openjiuwen")
from jsonschema import ValidationError

from speech_aware_evidence_acquisition.rails.phase_tools import (
    CANDIDATE_CONTRACT_TOOL,
    _native_tool_schema,
)
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import (
    NativeSourceFunction,
)
from openjiuwen.core.foundation.tool import ToolCard


def tool_and_calls():
    schema = _native_tool_schema(
        CANDIDATE_CONTRACT_TOOL, ("text",), candidate_limit=3,
    )["function"]
    calls = []

    async def invoke(**arguments):
        calls.append(deepcopy(arguments))
        return arguments

    tool = NativeSourceFunction(
        card=ToolCard(
            id=schema["name"], name=schema["name"],
            description=schema["description"], input_params=schema["parameters"],
        ),
        func=invoke,
    )
    return tool, calls, schema["parameters"]


def test_valid_unique_candidates_keep_wire_schema_order_and_raw_values():
    tool, calls, schema = tool_and_calls()
    original = deepcopy(schema)
    arguments = {"candidate_ids": ["weather_query", "alarm_set"]}
    result = asyncio.run(tool.invoke(arguments))
    assert result == arguments == calls[0]
    assert tool.card.tool_info().parameters == original
    assert schema == original
    assert original["properties"]["candidate_ids"]["uniqueItems"] is True


@pytest.mark.parametrize("arguments", [
    {"candidate_ids": ["weather_query", "weather_query"]},
    {"candidate_ids": []},
    {"candidate_ids": ["a", "b", "c", "d"]},
    {"candidate_ids": [123]},
    {"candidate_ids": [""]},
    {"candidate_ids": ["weather_query"], "extra": "refuse"},
    {},
])
def test_invalid_arguments_never_reach_the_source_handler(arguments):
    tool, calls, _schema = tool_and_calls()
    with pytest.raises(ValidationError):
        asyncio.run(tool.invoke(arguments, skip_inputs_validate=True))
    assert calls == []


def test_stream_keeps_the_same_one_result_and_validation_contract():
    tool, calls, _schema = tool_and_calls()
    arguments = {"candidate_ids": ["weather_query"]}

    async def collect():
        return [item async for item in tool.stream(arguments)]

    assert asyncio.run(collect()) == [arguments]
    assert calls == [arguments]
