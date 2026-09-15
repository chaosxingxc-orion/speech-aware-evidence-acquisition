"""Model-free dispatch checks for the opt-in live speech span tool."""

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.preparation import digest
from speech_aware_evidence_acquisition.rails.hashing import content_hash
from speech_aware_evidence_acquisition.rails.phase_tools import (
    LIVE_SPEECH_OBSERVATION_TOOL,
    LIVE_SPEECH_SPAN_TOOL,
    PhaseToolError,
    build_phase_tools,
    load_phase_tool_specs,
)
from speech_aware_evidence_acquisition.rails.speech_observation import (
    SpeechObservationSelection,
)
from speech_aware_evidence_acquisition.rails.tools import (
    LIVE_SPEECH_OBSERVATION_MANIFEST,
    LIVE_SPEECH_SPAN_MANIFEST,
    assert_pinned_hash,
    resolve_tool,
)
from test_phase_native_tools import (
    Custody,
    NativeProgram,
    call,
    native_config,
    staged_native,
)
from test_rails_runner import _knowledge_snapshot


ARGS = {
    "span": {"start_seconds": 0.25, "end_seconds": 0.5},
    "representation": "asr-transcript",
    "distinction": "Resolve the stated financial name.",
}


class SpanProvider:
    def __init__(self, *, reject=False):
        self.calls = []
        self.validations = []
        self.reject = reject

    def observe_span(self, *, context, arguments, source_response_sha256):
        self.calls.append((context, arguments, source_response_sha256))
        return SpeechObservationSelection(
            visible={
                "schema": "saea-live-speech-observation-selection-v1",
                "execution_unit_id": context.execution_unit_id,
                "source_span": {
                    "kind": "unit-relative-frames",
                    "start_frame": 4000,
                    "end_frame": 8000,
                    "sample_rate_hz": 16000,
                },
                "evidence_id": "span-one",
                "artifact_sha256": "a" * 64,
                "source_uri": "live-speech-observation://" + "a" * 64 + "/span-one",
                "status": "ok",
                "transcript": "Acme Holdings.",
                "sample_id": context.sample_id,
                "speech_packet_id": context.query_state.speech_packet_id,
                "speech_packet_sha256": context.query_state.speech_packet_sha256,
            },
            lineage={
                "schema": "saea-live-speech-observation-lineage-v1",
                "execution_unit_id": context.execution_unit_id,
                "execution_unit_binding_sha256": content_hash(
                    context.execution_unit_binding
                ),
                "source_response_sha256": source_response_sha256,
            },
        )

    def validate_span_selection(
        self, *, context, arguments, source_response_sha256, selection
    ):
        self.validations.append(
            (context, arguments, source_response_sha256, selection)
        )
        if self.reject:
            raise PhaseToolError("span tool returned foreign evidence")

    def receipt(self):
        return {"schema": "saea-live-speech-observation-provider-receipt-v1"}


def _dispatcher(provider, custody):
    return build_phase_tools(
        native_config(LIVE_SPEECH_SPAN_TOOL),
        NativeProgram(),
        snapshot=_knowledge_snapshot(),
        live_speech_observations=provider,
        tool_contact=custody,
    )


def _unit_context(tool_call):
    context = staged_native(tool_call)
    values = dict(context.__dict__)
    values.update(
        execution_unit_id="parent::window:0001",
        execution_unit_binding={
            "request_key": "parent::window:0001",
            "parent_sample_id": context.sample_id,
        },
    )
    return SimpleNamespace(**values)


def test_registered_span_schema_and_pinned_wrapper_are_distinct():
    assert resolve_tool(LIVE_SPEECH_SPAN_TOOL).manifest == LIVE_SPEECH_SPAN_MANIFEST
    assert_pinned_hash(LIVE_SPEECH_SPAN_MANIFEST)
    assert_pinned_hash(LIVE_SPEECH_OBSERVATION_MANIFEST)
    assert LIVE_SPEECH_OBSERVATION_MANIFEST.tool_id == LIVE_SPEECH_OBSERVATION_TOOL

    tool = _dispatcher(SpanProvider(), Custody())
    function = tool.native_tool_schemas()[0]["function"]
    assert function["name"] == LIVE_SPEECH_SPAN_TOOL
    assert function["parameters"] == {
        "type": "object",
        "properties": {
            "span": {
                "type": "object",
                "properties": {
                    "start_seconds": {"type": "number", "minimum": 0},
                    "end_seconds": {"type": "number", "exclusiveMinimum": 0},
                },
                "required": ["start_seconds", "end_seconds"],
                "additionalProperties": False,
            },
            "representation": {
                "type": "string",
                "enum": ["asr-transcript"],
            },
            "distinction": {
                "type": "string",
                "minLength": 1,
                "maxLength": 512,
            },
        },
        "required": ["span", "representation", "distinction"],
        "additionalProperties": False,
    }


def test_span_tool_requires_native_mode_and_valid_span_arguments():
    config = native_config(LIVE_SPEECH_SPAN_TOOL)
    config["phase_tools"]["decision-1"]["mode"] = "fixed"
    config["phase_tools"]["decision-1"]["fixed_action"] = {
        "tool_id": LIVE_SPEECH_SPAN_TOOL,
        "arguments": ARGS,
    }
    with pytest.raises(PhaseToolError, match="requires native-tools"):
        load_phase_tool_specs(config, NativeProgram())

    provider, custody = SpanProvider(), Custody()
    tool = _dispatcher(provider, custody)
    bad = {**ARGS, "span": {"start_seconds": 0.5, "end_seconds": 0.25}}
    step = tool(
        "decision-1",
        "decision-2",
        _unit_context(call(LIVE_SPEECH_SPAN_TOOL, bad)),
    )
    assert step is not None
    assert provider.calls == custody.calls == []
    assert tool.receipt()["native_rejected_requests"]["count"] == 1


@pytest.mark.parametrize("bad", [
    {**ARGS, "representation": "speech-features"},
    {**ARGS, "distinction": ""},
    {**ARGS, "distinction": "x" * 513},
    {**ARGS, "span": {"start_seconds": -0.1, "end_seconds": 0.5}},
    {**ARGS, "span": {"start_seconds": 0.0, "end_seconds": float("nan")}},
])
def test_span_argument_shapes_refuse_before_custody_or_provider(bad):
    provider, custody = SpanProvider(), Custody()
    tool = _dispatcher(provider, custody)
    tool(
        "decision-1",
        "decision-2",
        _unit_context(call(LIVE_SPEECH_SPAN_TOOL, bad)),
    )
    assert provider.calls == custody.calls == []
    assert tool.receipt()["native_rejected_requests"]["count"] == 1


def test_span_dispatch_validates_evidence_and_reports_unit_custody():
    provider, custody = SpanProvider(), Custody()
    tool = _dispatcher(provider, custody)
    context = _unit_context(call(LIVE_SPEECH_SPAN_TOOL, ARGS))
    step = tool("decision-1", "decision-2", context)

    assert len(provider.calls) == len(provider.validations) == 1
    assert provider.calls[0][1] == {
        **ARGS,
        "span": {"start_seconds": 0.25, "end_seconds": 0.5},
    }
    assert custody.calls[0]["execution_unit_id"] == context.execution_unit_id
    assert custody.calls[0]["execution_unit_binding_sha256"] == content_hash(
        context.execution_unit_binding
    ) == digest(context.execution_unit_binding)
    document = json.loads(step.state.content)
    assert document["tool_id"] == LIVE_SPEECH_SPAN_TOOL
    assert "transcript" not in document["result"]
    assert document["native_result_content"][0]["text"].endswith("Acme Holdings.")


def test_span_wrapper_rejects_provider_selection_before_dispatch_result():
    provider, custody = SpanProvider(reject=True), Custody()
    tool = _dispatcher(provider, custody)
    with pytest.raises(PhaseToolError, match="foreign evidence"):
        tool(
            "decision-1",
            "decision-2",
            _unit_context(call(LIVE_SPEECH_SPAN_TOOL, ARGS)),
        )
    assert len(provider.calls) == len(provider.validations) == len(custody.calls) == 1
    assert tool.receipt()["completed"] == 0


def test_unit_custody_facts_apply_to_non_speech_tools():
    from speech_aware_evidence_acquisition.rails.phase_tools import TASK_CONTRACT_TOOL

    custody = Custody()
    tool = build_phase_tools(
        native_config(TASK_CONTRACT_TOOL),
        NativeProgram(),
        snapshot=_knowledge_snapshot(),
        tool_contact=custody,
    )
    task_call = [{
        "id": "call-1", "type": "function",
        "function": {"name": TASK_CONTRACT_TOOL, "arguments": "{}"},
    }]
    context = _unit_context(task_call)
    tool("decision-1", "decision-2", context)
    assert custody.calls[0]["execution_unit_id"] == context.execution_unit_id
    assert custody.calls[0]["execution_unit_binding_sha256"] == content_hash(
        context.execution_unit_binding
    )


def test_opt_in_span_table_preserves_legacy_tables_and_analytical_roles():
    from pathlib import Path
    from speech_aware_evidence_acquisition.rails.tools import load_toolkit_table

    root = Path(__file__).resolve().parents[2]
    path = root / "configs/toolkit/task-toolkits-v3-bounded-speech-span-v1.json"
    load_toolkit_table(path)
    table = json.loads(path.read_text())["toolkits"]
    assert all(
        LIVE_SPEECH_SPAN_TOOL in table["meeting"][role]["tools"]
        for role in ("planner", "reviewer")
    )
    assert LIVE_SPEECH_SPAN_TOOL not in table["meeting"]["observer"]["tools"]
    for legacy in (
        "task-toolkits-v1.json", "task-toolkits-v2-candidate-contract-lookup-v1.json",
    ):
        assert LIVE_SPEECH_SPAN_TOOL not in (root / "configs/toolkit" / legacy).read_text()
