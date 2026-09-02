"""OpenJiuwen boundary for the 16-row G4 executable-microground screen.

The screen reuses the already-sealed G3 speech bindings and task-blind English
observations.  Each request carries one bounded state representation and one
deterministically routed executable-card packet.  The frozen core receives the
original speech on its only contact.  Gold, tier hints, sample identities,
prior outcomes, repair prompts, and a second supply channel are unavailable.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path

from ...core.base import Registry
from ..adapters.audio2tool import Audio2ToolSample
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..runner import (
    AgentContact,
    AgentContactPlan,
    AgentLoopAdvance,
    AgentResponse,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)
from ..knowledge import AgentStepTransition
from ..task_adapter import TaskAdapter
from .a2t_contract_preserving_cascade_flight import AGENT_EXECUTOR_ID

G4_SCREEN_SPLIT_ID = "A2T-G4-MICROGROUND-SCREEN-16"
G4_MICROGROUND_E_PHASE = "G4_EXECUTABLE_MICROGROUND_USE"
G4_MICROGROUND_SE_PHASE = "G4_STRUCTURED_EXECUTABLE_MICROGROUND_USE"
G4_EXPECTED_SCREEN_ROWS = 16
G4_STATE_UTF8_BYTE_CAP = 4_096
G4_SE_STATE_UTF8_BYTE_CAP = 8_192
G4_PACKET_UTF8_BYTE_CAP = 16_384
G4_SLOT_COUNT = 2
G4_QUEUE_DEPTH = 4

_PHASES = {G4_MICROGROUND_E_PHASE, G4_MICROGROUND_SE_PHASE}
_POLICY_ID = "saea-a2t-g4-executable-microground-single-contact-v1"
_CONTACT_ID = "g4-executable-microground-use"
_KEY_REPRESENTATION_ID = "a2t-g4-executable-semantic-cards-v1"
_MATCHER_POLICY_ID = "a2t-g4-structured-action-bm25-k2-8-v1"
_CONTROL_INSTRUCTION = (
    "Use the original speech, bounded state, and executable microground. "
    "Return only the required JSON tool-call array."
)
_FORBIDDEN_RUNTIME_FIELD = re.compile(
    r"(?i)(?:^|[^a-z0-9_])(gold_tool|expected_calls|tier_hint|sample_id)\s*:"
)


class G4MicrogroundFlightError(RuntimeError):
    """A G4 phase, prompt, identity, or contact invariant failed."""


def _bounded_ascii(
    value: object,
    *,
    label: str,
    byte_cap: int,
) -> str:
    if not isinstance(value, str) or not value.strip() or not value.isascii():
        raise G4MicrogroundFlightError(f"{label} must be nonempty ASCII English")
    text = value.strip()
    if _FORBIDDEN_RUNTIME_FIELD.search(text):
        raise G4MicrogroundFlightError(f"{label} contains a forbidden runtime field")
    size = len(text.encode("utf-8"))
    if size > byte_cap:
        raise G4MicrogroundFlightError(
            f"{label} byte cap exceeded: {size} > {byte_cap}"
        )
    return text


class G4MicrogroundAdapter(TaskAdapter):
    """Scoring-deferred adapter for one fixed G4 screen arm."""

    def __init__(
        self,
        samples: Sequence[Audio2ToolSample],
        *,
        phase: str,
        state_by_sample: Mapping[str, str],
        packet_by_sample: Mapping[str, str],
    ) -> None:
        if phase not in _PHASES:
            raise G4MicrogroundFlightError(f"unknown G4 phase {phase!r}")
        sample_rows = tuple(samples)
        sample_by_id = {sample.sample_id: sample for sample in sample_rows}
        if (
            len(sample_rows) != G4_EXPECTED_SCREEN_ROWS
            or len(sample_by_id) != G4_EXPECTED_SCREEN_ROWS
        ):
            raise G4MicrogroundFlightError(
                f"G4 screen requires exactly {G4_EXPECTED_SCREEN_ROWS} unique samples"
            )
        if set(state_by_sample) != set(sample_by_id) or set(packet_by_sample) != set(
            sample_by_id
        ):
            raise G4MicrogroundFlightError(
                "G4 USE requires one state and packet per sample"
            )
        self._samples = tuple(
            sorted(sample_by_id.values(), key=lambda sample: sample.sample_id)
        )
        self._phase = phase
        state_byte_cap = (
            G4_SE_STATE_UTF8_BYTE_CAP
            if phase == G4_MICROGROUND_SE_PHASE
            else G4_STATE_UTF8_BYTE_CAP
        )
        self._states = {
            sample_id: _bounded_ascii(
                state_by_sample[sample_id],
                label="state",
                byte_cap=state_byte_cap,
            )
            for sample_id in sorted(sample_by_id)
        }
        self._packets = {
            sample_id: _bounded_ascii(
                packet_by_sample[sample_id],
                label="packet",
                byte_cap=G4_PACKET_UTF8_BYTE_CAP,
            )
            for sample_id in sorted(sample_by_id)
        }

    def load_split(self, split_id: str) -> tuple[Audio2ToolSample, ...]:
        if split_id != G4_SCREEN_SPLIT_ID:
            raise G4MicrogroundFlightError(
                f"G4 adapter serves only {G4_SCREEN_SPLIT_ID!r}"
            )
        return self._samples

    def build_task_contract(self, sample: Audio2ToolSample, obs: object) -> str:
        del obs
        if sample.sample_id not in self._states:
            raise G4MicrogroundFlightError(
                "G4 sample falls outside the adapter surface"
            )
        representation = (
            "task-blind English observation"
            if self._phase == G4_MICROGROUND_E_PHASE
            else "validated structured dialogue state"
        )
        state = self._states[sample.sample_id]
        packet = self._packets[sample.sample_id]
        return (
            "Use the original speech as task authority. Treat the supplied "
            f"{representation} as bounded auxiliary evidence. Follow the executable "
            "microground exactly, but copy task values only from speech or state. Return "
            "only a nonempty JSON array of objects with exactly "
            '{"name":"registeredToolName","arguments":{...}}. Do not add prose.\n\n'
            f"BOUNDED STATE\n{state}\n\nEXECUTABLE MICROGROUND\n{packet}"
        )

    def assemble_prompt(
        self, sample: Audio2ToolSample, supply: object
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise G4MicrogroundFlightError("G4 adapter rejects a second supply channel")
        return (
            {"role": "system", "content": self.build_task_contract(sample, None)},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "media_relpath": sample.media_relpath}
                ],
            },
        )

    def score(self, sample: Audio2ToolSample, response: str) -> Mapping[str, object]:
        del sample, response
        return {"scoring_deferred": True}

    def extract_consumption(
        self, sample: Audio2ToolSample, supply: object, response: str
    ) -> ConsumptionTrace:
        del sample
        return build_consumption_trace(
            span_id="g4-final", supply=supply, response_text=response
        )


class G4SingleContactController:
    """One frozen-core USE request with no repair or history append."""

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if context.query_state.loop_step != 0:
            raise G4MicrogroundFlightError("G4 single contact requires loop step zero")
        return AgentContactPlan(
            contact_id=_CONTACT_ID,
            query_state_sha256=context.query_state.content_hash(),
            purpose="answer-with-executable-microground",
            instruction=_CONTROL_INSTRUCTION,
            key_representation_id=_KEY_REPRESENTATION_ID,
            matcher_policy_id=_MATCHER_POLICY_ID,
            decoding_params={"max_tokens": 1024, "temperature": 0},
        ).validate()

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContact,
        response_text: AgentResponse,
    ) -> AgentLoopAdvance:
        if (
            not isinstance(contact, AgentContactPlan)
            or contact.contact_id != _CONTACT_ID
        ):
            raise G4MicrogroundFlightError("G4 controller received an invalid contact")
        if context.query_state.loop_step != 0 or not isinstance(response_text, str):
            raise G4MicrogroundFlightError("G4 controller received an invalid response")
        transition = AgentStepTransition(
            snapshot_sha256=context.knowledge_snapshot_sha256,
            prior_query_state_sha256=context.query_state.content_hash(),
            next_query_state_sha256=None,
            action_kind="stop",
            action_target_refs=(),
            new_value_ids=(),
            used_value_ids=(),
            dropped_value_ids=(),
            new_agent_state_ids=(),
            dropped_agent_state_ids=(),
        ).validate()
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
            final_response_contact_id=_CONTACT_ID,
        )


def run_g4_microground_phase(
    *,
    data_root: Path,
    plan: object,
    adapter: G4MicrogroundAdapter,
    core_client: object,
    knowledge_snapshot: object,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    trace_sink: object,
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
) -> object:
    """Run the fixed 16-row phase with two slots and one contact per sample."""

    samples = adapter.load_split(G4_SCREEN_SPLIT_ID)
    sample_ids = {sample.sample_id for sample in samples}
    if set(speech_packet_bindings) != sample_ids:
        raise G4MicrogroundFlightError(
            "G4 sample and speech-packet identity surfaces disagree"
        )
    controllers = Registry("A2T G4 executable-microground controller")
    controllers.register(_POLICY_ID, lambda _sample_id: G4SingleContactController())
    summary = agent_runner(
        data_root=data_root,
        plan=plan,
        adapter=adapter,
        core_client=core_client,
        split_id=G4_SCREEN_SPLIT_ID,
        knowledge_snapshot=knowledge_snapshot,
        speech_packet_bindings=speech_packet_bindings,
        controller_policy_id=_POLICY_ID,
        bootstrap_facet_ids=(),
        bootstrap_value_ids=(),
        max_contacts=1,
        slot_count=G4_SLOT_COUNT,
        queue_depth=G4_QUEUE_DEPTH,
        trace_sink=trace_sink,
        agent_executor_id=AGENT_EXECUTOR_ID,
        decoding_params={},
        controller_registry=controllers,
    )
    if getattr(summary, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise G4MicrogroundFlightError("G4 phase is not bound to OpenJiuwen")
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != G4_EXPECTED_SCREEN_ROWS:
        raise G4MicrogroundFlightError("G4 result identity surface is incomplete")
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not isinstance(contacts, tuple):
            raise G4MicrogroundFlightError("G4 result identity surface is malformed")
        if len(contacts) != 1:
            raise G4MicrogroundFlightError("G4 result must contain exactly one contact")
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids) or set(result_ids) != sample_ids:
        raise G4MicrogroundFlightError("G4 result identity surface disagrees")
    return summary


__all__ = [
    "G4_EXPECTED_SCREEN_ROWS",
    "G4_MICROGROUND_E_PHASE",
    "G4_MICROGROUND_SE_PHASE",
    "G4_PACKET_UTF8_BYTE_CAP",
    "G4_QUEUE_DEPTH",
    "G4_SCREEN_SPLIT_ID",
    "G4_SE_STATE_UTF8_BYTE_CAP",
    "G4_SLOT_COUNT",
    "G4_STATE_UTF8_BYTE_CAP",
    "G4MicrogroundAdapter",
    "G4MicrogroundFlightError",
    "G4SingleContactController",
    "run_g4_microground_phase",
]
