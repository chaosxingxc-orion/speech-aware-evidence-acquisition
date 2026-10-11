"""Owner decision 266-E / 199: an empty direct-only completion is a receipted abstention, never an exception.

The four-row Thinking smoke lost a whole flight to ONE row: the Thinking core spent its 2,048-token completion budget on reasoning, the
server routed that reasoning to ``reasoning_content`` and ``message.content`` came back empty, and the wave raised
``AgentStateArtifact.content must be a non-empty string``. These tests pin the harness-boundary repair: the final non-native phase seals the
explicit empty marker, the runner leaves a ``saea-empty-completion-v1`` receipt (``cap_hit``, ``completion_tokens``, ``finish_reason``), the
row delivers the empty answer bytes, a non-empty content is unchanged, and the Instruct request path is untouched. Model-free.
"""

from __future__ import annotations

import hashlib
import threading
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.tracing import get_current_trace_buffer
from speech_aware_evidence_acquisition.core.model import transport as transport_mod
from speech_aware_evidence_acquisition.rails import controllers as rc
from speech_aware_evidence_acquisition.rails import runner as rails_runner
from speech_aware_evidence_acquisition.rails import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.rails.runner import RailsRunnerError
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_rails_controllers import _context, _material, _query_state
from test_rails_runner import (
    _SHA_C,
    _agent_trace,
    _controller_registry,
    _knowledge_snapshot,
    _one_sample_adapter,
    _plan,
)

EMPTY_MARKER = '{"schema":"saea-empty-phase-response-v1","response_text":""}'
CAP = 2048


def _direct_controller() -> rc.EvidenceAgentController:
    return rc.EvidenceAgentController(
        program=rc.default_phase_program("phase-direct-only-v1"),
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )


# ---------------------------------------------------------------------------
# the controller seal
# ---------------------------------------------------------------------------


def test_empty_direct_response_seals_the_empty_marker_and_stops():
    controller = _direct_controller()
    ctx = _context(_query_state())
    contact = controller.initial_contact(ctx)
    advance = controller.advance(ctx, contact, "")
    assert advance.transition.action_kind == "stop"
    assert advance.final_response_contact_id == contact.contact_id
    sealed = controller.sealed_states["direct"]
    assert sealed.content == EMPTY_MARKER
    # the raw source hash still binds the EMPTY model bytes
    assert sealed.source_response_sha256 == hashlib.sha256(b"").hexdigest()


def test_non_empty_direct_response_is_unchanged():
    controller = _direct_controller()
    ctx = _context(_query_state())
    contact = controller.initial_contact(ctx)
    controller.advance(ctx, contact, "the direct answer")
    assert controller.sealed_states["direct"].content == "the direct answer"


def test_empty_non_final_phase_still_raises():
    """The repair is the final delivering phase only: an empty intermediate state would feed the next phase nothing."""

    program = rc.default_phase_program("phase-draft-revise-v1")
    assert len(program.phases) > 1
    controller = rc.EvidenceAgentController(
        program=program,
        material_for_phase=lambda name, ctx: _material(name, ctx.sample_id),
    )
    ctx = _context(_query_state())
    contact = controller.initial_contact(ctx)
    with pytest.raises(Exception, match="non-empty string"):
        controller.advance(ctx, contact, "")


# ---------------------------------------------------------------------------
# the runner: receipt + delivery, both executors
# ---------------------------------------------------------------------------


class _CapClient:
    """A text-only client that mimics the adapter: it emits each completion's COST record into the current trace buffer."""

    def __init__(self, text: str, *, completion_tokens: int, finish_reason: str | None):
        self.text, self.completion_tokens, self.finish_reason = text, completion_tokens, finish_reason
        self.calls = []
        self._lock = threading.Lock()

    def complete(self, messages, **options):
        with self._lock:
            self.calls.append((tuple(messages), dict(options)))
            index = len(self.calls)
        cost = {"calls": 1, "audio_seconds": 2.0, "latency_seconds": 0.5, "prompt_tokens": 2285,
                "completion_tokens": self.completion_tokens}
        if self.finish_reason is not None:
            cost["finish_reason"] = self.finish_reason
        get_current_trace_buffer().emit("COST", f"req-{index}/cost", cost)
        return self.text


def _fly(tmp_path: Path, client, executor: str):
    trace = _agent_trace()
    summary = run_speech_native_agent_loop(
        data_root=tmp_path,
        plan=_plan(execution_profile="model-free-check"),
        adapter=_one_sample_adapter(),
        core_client=client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings={"s1": {"packet_id": "fake/dev/s1", "sha256": _SHA_C}},
        controller_policy_id="direct-empty-test-v1",
        controller_registry=_controller_registry("direct-empty-test-v1", lambda _sid: _direct_controller()),
        max_contacts=1,
        slot_count=1,
        queue_depth=1,
        trace_sink=trace,
        agent_executor_id=executor,
        decoding_params={"temperature": 0, "max_tokens": CAP},
    )
    return summary, trace


def _receipts(trace):
    out = []
    for channel, record_id, payload in trace.iter_records():
        if channel == "TOOL" and isinstance(payload, dict) and payload.get("schema") == rails_runner.EMPTY_COMPLETION_SCHEMA:
            out.append((record_id, payload))
    return out


EXECUTORS = [
    "reference-trajectory-v1",
    pytest.param("openjiuwen-workflow-v1", marks=pytest.mark.skipif(
        not openjiuwen_available(), reason="openjiuwen is absent; the reference executor remains dependency-free")),
]


@pytest.mark.parametrize("executor", EXECUTORS)
def test_cap_hit_empty_completion_flows_to_an_empty_row_without_raising(tmp_path, executor):
    client = _CapClient("", completion_tokens=CAP, finish_reason="length")
    summary, trace = _fly(tmp_path, client, executor)
    result = summary.results[0]
    assert result.final_response_text == ""
    assert len(result.contacts) == 1 and len(client.calls) == 1
    receipts = _receipts(trace)
    assert len(receipts) == 1
    record_id, payload = receipts[0]
    assert record_id.endswith("/empty-completion")
    assert payload["cap_hit"] is True
    assert payload["completion_tokens"] == CAP and payload["max_tokens"] == CAP
    assert payload["finish_reason"] == "length"
    assert payload["cap_hit_basis"] == "finish-reason-length"
    assert payload["response_text_sha256"] == hashlib.sha256(b"").hexdigest()
    assert payload["agent_contact_id"] == "c-direct-s1"


@pytest.mark.parametrize("executor", EXECUTORS)
def test_cap_hit_is_recovered_from_token_counts_when_the_finish_reason_is_not_forwarded(tmp_path, executor):
    client = _CapClient("", completion_tokens=CAP, finish_reason=None)
    _summary, trace = _fly(tmp_path, client, executor)
    (_rid, payload), = _receipts(trace)
    assert payload["cap_hit"] is True and payload["finish_reason"] is None
    assert payload["cap_hit_basis"] == "completion-tokens-reach-max-tokens"


@pytest.mark.parametrize("executor", EXECUTORS)
def test_empty_completion_that_stopped_is_an_abstention_but_not_a_cap_hit(tmp_path, executor):
    client = _CapClient("", completion_tokens=97, finish_reason="stop")
    summary, trace = _fly(tmp_path, client, executor)
    assert summary.results[0].final_response_text == ""
    (_rid, payload), = _receipts(trace)
    assert payload["cap_hit"] is False and payload["finish_reason"] == "stop"
    assert payload["cap_hit_basis"] == "not-at-cap"


@pytest.mark.parametrize("executor", EXECUTORS)
def test_non_empty_completion_leaves_no_receipt_and_is_delivered_verbatim(tmp_path, executor):
    client = _CapClient("turn on the lights", completion_tokens=7, finish_reason="stop")
    summary, trace = _fly(tmp_path, client, executor)
    assert summary.results[0].final_response_text == "turn on the lights"
    assert _receipts(trace) == []


def test_an_unreceipted_empty_final_response_is_still_refused():
    """The repair does not loosen the runner gate: only a receipted contact may deliver empty bytes."""

    contact = rails_runner.AgentContactPlan(
        contact_id="c1", query_state_sha256="a" * 64, purpose="direct", instruction="x",
        key_representation_id="K1", matcher_policy_id="m", decoding_params={},
    )
    with pytest.raises(RailsRunnerError, match="non-empty model response"):
        rails_runner._resolve_final_agent_response(contact, "", "c1")
    assert rails_runner._resolve_final_agent_response(contact, "", "c1", empty_receipted=lambda cid: cid == "c1") == ""


def test_instruct_request_path_is_unchanged_a_non_guarded_envelope_gains_no_key():
    """I7 by construction: the finish reason is forwarded only under the opt-in reasoning guard."""

    source = Path(transport_mod.__file__).read_text(encoding="utf-8")
    assert source.count('envelope["finish_reason"]') == 1
    at = source.index('envelope["finish_reason"]')
    assert 'getattr(self, "_reasoning_content_guard", None)' in source[at - 900:at]
