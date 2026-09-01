"""OpenJiuwen phase boundary for the contract-preserving cascade v2.

M0 retains the historical Audio2Tool direct message bytes and is invoked as
the single-call comparator. OBS and USE remain separate one-contact AgentLoop
workflows. USE inserts state and evidence before the unchanged final direct
output sentence instead of replacing that sentence.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from queue import Queue
from typing import Callable, Mapping, Sequence

from ...analysis import training_free_a2t_self_transcript_cascade as selftx
from ...core.base import Registry
from ..adapters.audio2tool import (
    Audio2ToolAdapter,
    Audio2ToolSample,
    render_audio2tool_instruction,
)
from ..knowledge import AgentStepTransition
from ..runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)
from .a2t_self_transcript_cascade_flight import (
    UseMaterial,
    build_use_material,
)

SPLIT_ID = "A2T-CPV2-104"
M0_DIRECT_PHASE = "M0_DIRECT"
OBSERVATION_PHASE = "OBS_SELF_TRANSCRIPT"
MATCHED_USE_PHASE = "USE_MATCHED"
SHUFFLED_USE_PHASE = "USE_SHUFFLED_EVIDENCE"
AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"

OBSERVATION_CONTACT_ID = "contract-v2-self-transcript-observation"
MATCHED_CONTACT_ID = "contract-v2-matched-final"
SHUFFLED_CONTACT_ID = "contract-v2-shuffled-final"

_PHASE_POLICY = {
    OBSERVATION_PHASE: "saea-a2t-contract-v2-self-transcript-observation",
    MATCHED_USE_PHASE: "saea-a2t-contract-v2-matched-use",
    SHUFFLED_USE_PHASE: "saea-a2t-contract-v2-shuffled-use",
}
_PHASE_CONTACT = {
    OBSERVATION_PHASE: OBSERVATION_CONTACT_ID,
    MATCHED_USE_PHASE: MATCHED_CONTACT_ID,
    SHUFFLED_USE_PHASE: SHUFFLED_CONTACT_ID,
}
_USE_CONTROL_INSTRUCTION = (
    "Produce the final task answer from the original speech. Use the English "
    "self-transcript Agent state and supplied evidence as auxiliary context. "
    "Obey the final exact JSON output contract in the system instruction."
)


class A2TContractPreservingFlightError(RuntimeError):
    """The v2 phase boundary refused an unregistered or unsafe execution."""


@dataclass(frozen=True)
class DirectPhaseResult:
    """One same-flight single-call comparator response."""

    sample_id: str
    final_response_text: str


@dataclass(frozen=True)
class DirectPhaseSummary:
    """The complete direct comparator surface, with no Agent history."""

    results: tuple[DirectPhaseResult, ...]
    direct_single_call: bool = True


def render_observation_system_contract() -> str:
    """Return the unchanged task-blind English OBS contract."""

    return selftx.SELF_TRANSCRIPT_INSTRUCTION


def render_use_system_contract(
    *,
    tool_schemas: str,
    recipient_transcript: str,
    evidence_contents: Sequence[str],
    phase: str,
) -> str:
    """Insert state/evidence before the historical direct output suffix."""

    if phase not in {MATCHED_USE_PHASE, SHUFFLED_USE_PHASE}:
        raise A2TContractPreservingFlightError(
            "USE system contract requires a registered USE phase"
        )
    parsed = selftx.validate_self_transcript(recipient_transcript)
    if not parsed.valid:
        raise A2TContractPreservingFlightError(
            f"USE system contract rejected recipient transcript: {parsed.reason}"
        )
    evidence = tuple(evidence_contents)
    if not 1 <= len(evidence) <= selftx.MAX_VALUES or any(
        not isinstance(item, str) or not item.strip() for item in evidence
    ):
        raise A2TContractPreservingFlightError(
            "USE system contract requires one through six non-empty evidence values"
        )
    label = "matched" if phase == MATCHED_USE_PHASE else "shuffled-control"
    rendered_evidence = "\n".join(
        f"[evidence {index}] {value}"
        for index, value in enumerate(evidence, start=1)
    )
    auxiliary = (
        "English self-transcript Agent state:\n"
        f"{parsed.text}\n\n"
        f"Supplied {label} evidence:\n{rendered_evidence}"
    )
    try:
        return render_audio2tool_instruction(
            tool_schemas,
            auxiliary_context=auxiliary,
        )
    except ValueError as error:
        raise A2TContractPreservingFlightError(str(error)) from error


class A2TContractPreservingAdapter(Audio2ToolAdapter):
    """Receipt-filtered direct/OBS/USE adapter with scoring deferred."""

    def __init__(
        self,
        lock: Mapping[str, object],
        root: Path,
        *,
        repo_root: Path,
        receipt_items: Sequence[Mapping[str, object]],
        phase: str,
        use_material: Mapping[str, UseMaterial] | None = None,
    ) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        if phase not in {
            M0_DIRECT_PHASE,
            OBSERVATION_PHASE,
            MATCHED_USE_PHASE,
            SHUFFLED_USE_PHASE,
        }:
            raise A2TContractPreservingFlightError(
                f"unknown contract-preserving phase {phase!r}"
            )
        by_id: dict[str, Mapping[str, object]] = {}
        for item in receipt_items:
            sample_id = item.get("sample_id")
            if not isinstance(sample_id, str) or not sample_id:
                raise A2TContractPreservingFlightError(
                    "receipt item lacks a non-empty sample_id"
                )
            if sample_id in by_id:
                raise A2TContractPreservingFlightError(
                    f"receipt contains duplicate sample_id {sample_id!r}"
                )
            by_id[sample_id] = item
        if not by_id:
            raise A2TContractPreservingFlightError(
                "receipt resolves to zero samples"
            )
        material = dict(use_material or {})
        if phase in {M0_DIRECT_PHASE, OBSERVATION_PHASE} and material:
            raise A2TContractPreservingFlightError(
                "direct and observation adapters cannot receive USE material"
            )
        if phase in {MATCHED_USE_PHASE, SHUFFLED_USE_PHASE}:
            if not material or not set(material).issubset(by_id):
                raise A2TContractPreservingFlightError(
                    "USE material must be a non-empty receipt subset"
                )
            if any(
                value.sample_id != sample_id
                for sample_id, value in material.items()
            ):
                raise A2TContractPreservingFlightError(
                    "USE material sample identities drifted"
                )
        self._phase = phase
        self._by_id = by_id
        self._material = material
        self._cache: tuple[Audio2ToolSample, ...] | None = None
        self._contracts: dict[str, str] = {}

    def load_split(self, split_id: str) -> tuple[Audio2ToolSample, ...]:
        if split_id != SPLIT_ID:
            raise A2TContractPreservingFlightError(
                f"adapter serves only {SPLIT_ID!r}, not {split_id!r}"
            )
        if self._cache is None:
            target_ids = (
                set(self._material)
                if self._phase in {MATCHED_USE_PHASE, SHUFFLED_USE_PHASE}
                else set(self._by_id)
            )
            exposed = super().load_split("discovery")
            picked = tuple(
                sorted(
                    (sample for sample in exposed if sample.sample_id in target_ids),
                    key=lambda sample: sample.sample_id,
                )
            )
            if {sample.sample_id for sample in picked} != target_ids:
                missing = target_ids - {sample.sample_id for sample in picked}
                raise A2TContractPreservingFlightError(
                    f"discovery carrier lacks receipt samples: {sorted(missing)!r}"
                )
            for sample in picked:
                item = self._by_id[sample.sample_id]
                if sample.media_relpath != item.get("media_relpath"):
                    raise A2TContractPreservingFlightError(
                        f"media path drift for {sample.sample_id!r}"
                    )
                if sample.audio_ref.sha256 != item.get("audio_sha256"):
                    raise A2TContractPreservingFlightError(
                        f"audio bytes drift for {sample.sample_id!r}"
                    )
            self._cache = picked
        return self._cache

    def build_task_contract(self, sample: Audio2ToolSample, obs: object) -> str:
        if self._phase == OBSERVATION_PHASE:
            contract = render_observation_system_contract()
        elif self._phase == M0_DIRECT_PHASE:
            contract = super().build_task_contract(sample, obs)  # type: ignore[arg-type]
        else:
            tool_schemas = super().build_task_contract(sample, obs)  # type: ignore[arg-type]
            material = self._material[sample.sample_id]
            contract = render_use_system_contract(
                tool_schemas=tool_schemas,
                recipient_transcript=material.recipient_transcript,
                evidence_contents=material.evidence_contents,
                phase=self._phase,
            )
        self._contracts[sample.sample_id] = contract
        return contract

    def assemble_prompt(
        self, sample: Audio2ToolSample, supply: object
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise A2TContractPreservingFlightError(
                "contract-preserving adapter rejects a second supply channel"
            )
        if self._phase == M0_DIRECT_PHASE:
            return tuple(super().assemble_prompt(sample, None))
        try:
            contract = self._contracts[sample.sample_id]
        except KeyError:
            raise A2TContractPreservingFlightError(
                "task contract must be built before prompt assembly"
            ) from None
        return (
            {"role": "system", "content": contract},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "media_relpath": sample.media_relpath}
                ],
            },
        )

    def score(self, sample: Audio2ToolSample, response: str) -> Mapping[str, object]:
        return {"scoring_deferred": True}


def run_direct_phase(
    *,
    adapter: object,
    core_client: object,
    split_id: str,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    slot_count: int,
    decoding_params: Mapping[str, object],
) -> DirectPhaseSummary:
    """Run M0 as one call per sample without Agent state or control history."""

    if isinstance(slot_count, bool) or not isinstance(slot_count, int) or slot_count < 1:
        raise A2TContractPreservingFlightError(
            "direct phase slot count must be a positive integer"
        )
    if not isinstance(decoding_params, Mapping) or "id_slot" in decoding_params:
        raise A2TContractPreservingFlightError(
            "direct phase decoding parameters must omit id_slot"
        )
    samples = tuple(adapter.load_split(split_id))
    sample_ids = [sample.sample_id for sample in samples]
    if (
        not samples
        or len(set(sample_ids)) != len(sample_ids)
        or set(sample_ids) != set(speech_packet_bindings)
    ):
        raise A2TContractPreservingFlightError(
            "direct sample and speech-packet identities must match uniquely"
        )

    slots: Queue[int] = Queue()
    for slot in range(slot_count):
        slots.put(slot)

    def invoke(sample: object) -> DirectPhaseResult:
        packet = speech_packet_bindings[sample.sample_id]
        packet_id = packet.get("packet_id")
        packet_sha256 = packet.get("sha256")
        if (
            not isinstance(packet_id, str)
            or not packet_id
            or not isinstance(packet_sha256, str)
            or len(packet_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in packet_sha256
            )
        ):
            raise A2TContractPreservingFlightError(
                f"direct phase has a malformed packet binding for {sample.sample_id!r}"
            )
        base = tuple(adapter.assemble_prompt(sample, None))
        if (
            len(base) != 2
            or not isinstance(base[0], Mapping)
            or base[0].get("role") != "system"
            or not isinstance(base[0].get("content"), str)
            or not base[0].get("content")
        ):
            raise A2TContractPreservingFlightError(
                "direct adapter did not produce its exact system message"
            )
        messages = (
            dict(base[0]),
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_speech_features",
                        "speech_features": {
                            "packet_id": packet_id,
                            "sha256": packet_sha256,
                            "role": "query",
                        },
                    }
                ],
            },
        )
        slot = slots.get()
        try:
            decoding = dict(decoding_params)
            decoding["id_slot"] = slot
            response = core_client.complete(
                messages,
                decoding_params=decoding,
                speech_feature_sample_id=sample.sample_id,
                key_representation_id="audio2tool-direct-registry-v1",
                matcher_policy_id="saea-a2t-contract-v2-m0-direct",
            )
        finally:
            slots.put(slot)
        if not isinstance(response, str) or not response:
            raise A2TContractPreservingFlightError(
                f"direct phase returned no response for {sample.sample_id!r}"
            )
        return DirectPhaseResult(sample.sample_id, response)

    with ThreadPoolExecutor(max_workers=slot_count) as executor:
        results = tuple(executor.map(invoke, samples))
    return DirectPhaseSummary(
        results=tuple(sorted(results, key=lambda result: result.sample_id))
    )


def _assert_liveness_receipt(receipt: object) -> None:
    if getattr(receipt, "passed", None) is not True or getattr(
        receipt, "row_count", None
    ) != 104:
        raise A2TContractPreservingFlightError(
            "evidence use requires a passing 104-row liveness receipt"
        )
    report_sha256 = getattr(receipt, "report_sha256", None)
    if (
        not isinstance(report_sha256, str)
        or len(report_sha256) != 64
        or any(character not in "0123456789abcdef" for character in report_sha256)
    ):
        raise A2TContractPreservingFlightError(
            "liveness receipt must carry a lowercase 64-hex report hash"
        )


class SingleContactController:
    """One registered OBS or USE contact followed by an unconditional stop."""

    def __init__(self, *, phase: str, liveness_receipt: object | None = None) -> None:
        try:
            self._policy_id = _PHASE_POLICY[phase]
            self._contact_id = _PHASE_CONTACT[phase]
        except KeyError:
            raise A2TContractPreservingFlightError(
                f"unknown contract-preserving Agent phase {phase!r}"
            ) from None
        self._phase = phase
        if phase == OBSERVATION_PHASE:
            if liveness_receipt is not None:
                raise A2TContractPreservingFlightError(
                    "observation phase cannot receive a liveness receipt"
                )
        else:
            _assert_liveness_receipt(liveness_receipt)

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if context.query_state.loop_step != 0:
            raise A2TContractPreservingFlightError(
                "single-contact phase requires loop step zero"
            )
        if self._phase == OBSERVATION_PHASE:
            instruction = selftx.SELF_TRANSCRIPT_INSTRUCTION
            decoding = {"max_tokens": 192, "temperature": 0}
            purpose = "observe-english-self-transcript"
        else:
            instruction = _USE_CONTROL_INSTRUCTION
            decoding = {}
            purpose = (
                "answer-with-matched-evidence"
                if self._phase == MATCHED_USE_PHASE
                else "answer-with-shuffled-evidence"
            )
        return AgentContactPlan(
            contact_id=self._contact_id,
            query_state_sha256=context.query_state.content_hash(),
            purpose=purpose,
            instruction=instruction,
            key_representation_id=f"{self._policy_id}:speech",
            matcher_policy_id=(
                selftx.RETRIEVER_POLICY_ID
                if self._phase != OBSERVATION_PHASE
                else self._policy_id
            ),
            decoding_params=decoding,
        ).validate()

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: object,
    ) -> AgentLoopAdvance:
        if not isinstance(contact, AgentContactPlan):
            raise A2TContractPreservingFlightError(
                "single-contact controller received a batched contact"
            )
        if context.query_state.loop_step != 0 or contact.contact_id != self._contact_id:
            raise A2TContractPreservingFlightError(
                "single-contact controller received an invalid contact sequence"
            )
        if not isinstance(response_text, str):
            raise A2TContractPreservingFlightError(
                "single-contact controller requires one string response"
            )
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
            final_response_contact_id=self._contact_id,
        )


def run_phase(
    *,
    phase: str,
    data_root: object,
    plan: object,
    adapter: object,
    core_client: object,
    split_id: str,
    knowledge_snapshot: object,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    trace_sink: object,
    slot_count: int,
    queue_depth: int,
    decoding_params: Mapping[str, object],
    liveness_receipt: object | None = None,
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
) -> object:
    """Execute one OBS or USE phase through the pinned openJiuwen executor."""

    try:
        policy_id = _PHASE_POLICY[phase]
    except KeyError:
        raise A2TContractPreservingFlightError(
            f"unknown contract-preserving Agent phase {phase!r}"
        ) from None
    if phase != OBSERVATION_PHASE:
        _assert_liveness_receipt(liveness_receipt)
    controller_registry = Registry("contract-preserving cascade v2 controller")
    controller_registry.register(
        policy_id,
        lambda _sample_id: SingleContactController(
            phase=phase,
            liveness_receipt=liveness_receipt,
        ),
    )
    summary = agent_runner(
        data_root=data_root,
        plan=plan,
        adapter=adapter,
        core_client=core_client,
        split_id=split_id,
        knowledge_snapshot=knowledge_snapshot,
        speech_packet_bindings=speech_packet_bindings,
        controller_policy_id=policy_id,
        max_contacts=1,
        slot_count=slot_count,
        queue_depth=queue_depth,
        trace_sink=trace_sink,
        agent_executor_id=AGENT_EXECUTOR_ID,
        decoding_params=decoding_params,
        controller_registry=controller_registry,
    )
    if getattr(summary, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise A2TContractPreservingFlightError(
            "phase summary is not bound to openjiuwen-workflow-v1"
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple):
        raise A2TContractPreservingFlightError(
            "AgentLoop summary must expose a tuple of results"
        )
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise A2TContractPreservingFlightError(
                "AgentLoop result lacks a non-empty sample_id"
            )
        if not isinstance(contacts, tuple) or len(contacts) != 1:
            raise A2TContractPreservingFlightError(
                f"AgentLoop result {sample_id!r} must have exactly one contact"
            )
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids):
        raise A2TContractPreservingFlightError(
            "AgentLoop results contain duplicate ids"
        )
    expected = set(speech_packet_bindings)
    observed = set(result_ids)
    if expected != observed:
        raise A2TContractPreservingFlightError(
            "speech-packet/result identity mismatch: "
            f"packet_only={sorted(expected - observed)!r}, "
            f"result_only={sorted(observed - expected)!r}"
        )
    return summary


__all__ = [
    "AGENT_EXECUTOR_ID",
    "MATCHED_CONTACT_ID",
    "MATCHED_USE_PHASE",
    "M0_DIRECT_PHASE",
    "OBSERVATION_CONTACT_ID",
    "OBSERVATION_PHASE",
    "SHUFFLED_CONTACT_ID",
    "SHUFFLED_USE_PHASE",
    "SPLIT_ID",
    "A2TContractPreservingAdapter",
    "A2TContractPreservingFlightError",
    "DirectPhaseResult",
    "DirectPhaseSummary",
    "SingleContactController",
    "UseMaterial",
    "build_use_material",
    "render_observation_system_contract",
    "render_use_system_contract",
    "run_direct_phase",
    "run_phase",
]
