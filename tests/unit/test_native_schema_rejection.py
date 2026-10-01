"""Schema rejection must leave a source-bound tool observation."""
import asyncio
import pytest
from speech_aware_evidence_acquisition.reproduction.ojw.native_roles import NativeSourceFunction
from openjiuwen.core.foundation.tool import ToolCard

def test_invalid_arguments_return_observation_without_invoking_lookup():
    events = []
    async def lookup(**arguments):
        events.append("lookup")
        return "evidence"
    async def reject(arguments):
        events.append(arguments)
        return "source-bound rejection"
    tool = NativeSourceFunction(card=ToolCard(id="lookup", name="lookup", description="Test",
        input_params={"type": "object", "properties": {"ids": {"type": "array", "maxItems": 2}},
                      "required": ["ids"], "additionalProperties": False}),
        func=lookup, invalid_arguments=reject)
    args = {"ids": ["a", "b", "c"]}
    assert asyncio.run(tool.invoke(args)) == "source-bound rejection"
    assert events == [args]
    assert asyncio.run(tool.invoke({"ids": ["a"]})) == "evidence"
    assert events[-1] == "lookup"

def test_lookup_failure_is_not_reclassified_as_argument_rejection():
    async def lookup(**arguments):
        raise RuntimeError("storage unavailable")
    async def reject(arguments):
        pytest.fail("not a validation error")
    tool = NativeSourceFunction(card=ToolCard(id="lookup", name="lookup", description="Test",
        input_params={"type": "object"}), func=lookup, invalid_arguments=reject)
    with pytest.raises(RuntimeError, match="storage"):
        asyncio.run(tool.invoke({}))

def _argument_rejection_document(*, invalid=True):
    import copy
    import hashlib
    import json
    from test_native_tool_authority import _authority_world
    from speech_aware_evidence_acquisition.rails import native_tool_authority as authority
    from speech_aware_evidence_acquisition.rails.hashing import content_hash
    step = _authority_world()[3]
    document = json.loads(step.state.content)
    source = copy.deepcopy(document["source_authority"])
    source["role_id"] = source["phase_id"]
    call, = source["original_assistant_message"]["tool_calls"]
    arguments = json.loads(call["function"]["arguments"])
    if invalid:
        arguments["undeclared_argument"] = True
    call["function"]["arguments"] = json.dumps(arguments)
    calls_json = json.dumps([call], sort_keys=True, separators=(",", ":"))
    source["source_tool_calls_sha256"] = hashlib.sha256(calls_json.encode()).hexdigest()
    source["original_assistant_message_sha256"] = content_hash(source["original_assistant_message"])
    source["completion_sha256"] = content_hash(authority._completion_identity(source))
    result = authority.invalid_arguments_rejection_result(1)
    document.update(schema=authority.MULTIPLE_CALL_REJECTION_SCHEMA,
        next_phase=document["phase"], arguments=arguments, native_tool_calls_json=calls_json,
        tool_calls_sha256=source["source_tool_calls_sha256"],
        source_authority=source, source_authority_sha256=content_hash(source),
        result=result, result_sha256=content_hash(result),
        native_result_content=[], native_result_content_sha256=content_hash({"blocks": []}))
    document.pop("tool_invocation")
    return document

def test_argument_rejection_validates_against_original_advertised_schema():
    from speech_aware_evidence_acquisition.rails.native_tool_authority import validate_native_call_rejection, NativeToolAuthorityError
    document = _argument_rejection_document()
    validate_native_call_rejection(document)
    document["arguments"]["undeclared_argument"] = False
    with pytest.raises(NativeToolAuthorityError):
        validate_native_call_rejection(document)
    with pytest.raises(NativeToolAuthorityError, match="schema-valid"):
        validate_native_call_rejection(_argument_rejection_document(invalid=False))


