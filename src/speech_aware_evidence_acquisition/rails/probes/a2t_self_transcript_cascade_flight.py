"""OpenJiuwen phase boundary for the self-transcript cascade.

Observation and evidence use are separate one-contact workflows so the full
label-free observation batch can fail closed before any evidence-use contact.
The final task prompt always retains the original speech carrier; the accepted
English self-transcript and frozen knowledge are auxiliary context only.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...analysis import training_free_a2t_self_transcript_cascade as cascade
from ...core.base import Registry
from ..adapters.audio2tool import Audio2ToolAdapter, Audio2ToolSample
from ..knowledge import AgentStepTransition
from ..runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)

SPLIT_ID = "A2T-SELF-TRANSCRIPT-104"
OBSERVATION_PHASE = "OBS_SELF_TRANSCRIPT"
MATCHED_USE_PHASE = "USE_MATCHED"
SHUFFLED_USE_PHASE = "USE_SHUFFLED_EVIDENCE"
AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"

OBSERVATION_CONTACT_ID = "self-transcript-observation"
MATCHED_CONTACT_ID = "self-transcript-matched-final"
SHUFFLED_CONTACT_ID = "self-transcript-shuffled-final"

_PHASE_POLICY = {
    OBSERVATION_PHASE: "saea-a2t-self-transcript-observation-v1",
    MATCHED_USE_PHASE: "saea-a2t-self-transcript-matched-use-v1",
    SHUFFLED_USE_PHASE: "saea-a2t-self-transcript-shuffled-use-v1",
}
_PHASE_CONTACT = {
    OBSERVATION_PHASE: OBSERVATION_CONTACT_ID,
    MATCHED_USE_PHASE: MATCHED_CONTACT_ID,
    SHUFFLED_USE_PHASE: SHUFFLED_CONTACT_ID,
}
_USE_INSTRUCTION = (
    "Produce the final task answer from the original speech. Use the English "
    "self-transcript Agent state and supplied evidence as auxiliary context. "
    "Respond only with the task contract's JSON array of tool calls."
)


class A2TSelfTranscriptFlightError(RuntimeError):
    """The phase boundary refused an unregistered or unsafe execution."""


@dataclass(frozen=True)
class UseMaterial:
    """One routed sample's own AgentState and bounded evidence references."""

    sample_id: str
    recipient_transcript: str
    route: cascade.EvidenceRoute
    evidence_contents: tuple[str, ...]
    donor_id: str | None
    retrieval_query_sha256: str


def render_observation_system_contract() -> str:
    """Return the exact task-blind English contract for OBS contacts."""

    return cascade.SELF_TRANSCRIPT_INSTRUCTION


def build_use_material(
    *,
    transcripts: Mapping[str, cascade.TranscriptParse],
    sample_tiers: Mapping[str, str],
    snapshot: object,
    phase: str,
) -> dict[str, UseMaterial]:
    """Build matched or donor-routed evidence while preserving own AgentState."""

    if phase not in {MATCHED_USE_PHASE, SHUFFLED_USE_PHASE}:
        raise A2TSelfTranscriptFlightError(
            "use material requires matched or shuffled USE phase"
        )
    if set(transcripts) != set(sample_tiers) or not transcripts:
        raise A2TSelfTranscriptFlightError(
            "transcript and tier identities must match exactly"
        )
    if not hasattr(snapshot, "validate"):
        raise A2TSelfTranscriptFlightError(
            "use material requires a frozen KnowledgeSnapshot"
        )
    snapshot.validate()
    retriever = cascade.EvidenceRetriever(snapshot)
    matched_routes: dict[str, cascade.EvidenceRoute] = {}
    for sample_id in sorted(transcripts):
        parsed = transcripts[sample_id]
        if not isinstance(parsed, cascade.TranscriptParse):
            raise A2TSelfTranscriptFlightError(
                f"transcript record for {sample_id!r} has the wrong type"
            )
        if not parsed.valid:
            continue
        route = retriever.route(parsed.text)
        if route.available:
            matched_routes[sample_id] = route
    if not matched_routes:
        raise A2TSelfTranscriptFlightError("no transcript produced a positive route")
    if phase == SHUFFLED_USE_PHASE:
        donors = cascade.build_same_tier_derangement(
            {sample_id: sample_tiers[sample_id] for sample_id in matched_routes}
        )
    else:
        donors = {sample_id: sample_id for sample_id in matched_routes}

    values_by_id = {value.value_id: value for value in snapshot.values}
    material: dict[str, UseMaterial] = {}
    for sample_id in sorted(matched_routes):
        donor_id = donors[sample_id]
        route = matched_routes[donor_id]
        try:
            contents = tuple(
                values_by_id[value_id].content for value_id in route.value_ids
            )
        except KeyError as error:
            raise A2TSelfTranscriptFlightError(
                f"route references unknown value {error.args[0]!r}"
            ) from None
        if not 1 <= len(contents) <= 6:
            raise A2TSelfTranscriptFlightError(
                f"route for {sample_id!r} violates the six-value budget"
            )
        query_text = transcripts[donor_id].text
        material[sample_id] = UseMaterial(
            sample_id=sample_id,
            recipient_transcript=transcripts[sample_id].text,
            route=route,
            evidence_contents=contents,
            donor_id=(None if phase == MATCHED_USE_PHASE else donor_id),
            retrieval_query_sha256=hashlib.sha256(
                query_text.encode("utf-8")
            ).hexdigest(),
        )
    return material


class A2TSelfTranscriptAdapter(Audio2ToolAdapter):
    """Receipt-filtered phase adapter with scoring permanently deferred."""

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
        if phase not in _PHASE_POLICY:
            raise A2TSelfTranscriptFlightError(
                f"unknown self-transcript phase {phase!r}"
            )
        by_id: dict[str, Mapping[str, object]] = {}
        for item in receipt_items:
            sample_id = item.get("sample_id")
            if not isinstance(sample_id, str) or not sample_id:
                raise A2TSelfTranscriptFlightError(
                    "receipt item lacks a non-empty sample_id"
                )
            if sample_id in by_id:
                raise A2TSelfTranscriptFlightError(
                    f"receipt contains duplicate sample_id {sample_id!r}"
                )
            by_id[sample_id] = item
        if not by_id:
            raise A2TSelfTranscriptFlightError("receipt resolves to zero samples")
        material = dict(use_material or {})
        if phase == OBSERVATION_PHASE and material:
            raise A2TSelfTranscriptFlightError(
                "observation adapter cannot receive use material"
            )
        if phase != OBSERVATION_PHASE:
            if not material or not set(material).issubset(by_id):
                raise A2TSelfTranscriptFlightError(
                    "USE material must be a non-empty receipt subset"
                )
            if any(
                value.sample_id != sample_id
                for sample_id, value in material.items()
            ):
                raise A2TSelfTranscriptFlightError(
                    "USE material sample identities drifted"
                )
        self._phase = phase
        self._by_id = by_id
        self._material = material
        self._cache: tuple[Audio2ToolSample, ...] | None = None
        self._contracts: dict[str, str] = {}

    def load_split(self, split_id: str) -> tuple[Audio2ToolSample, ...]:
        if split_id != SPLIT_ID:
            raise A2TSelfTranscriptFlightError(
                f"adapter serves only {SPLIT_ID!r}, not {split_id!r}"
            )
        if self._cache is None:
            target_ids = (
                set(self._by_id)
                if self._phase == OBSERVATION_PHASE
                else set(self._material)
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
                raise A2TSelfTranscriptFlightError(
                    f"discovery carrier lacks receipt samples: {sorted(missing)!r}"
                )
            for sample in picked:
                item = self._by_id[sample.sample_id]
                if sample.media_relpath != item.get("media_relpath"):
                    raise A2TSelfTranscriptFlightError(
                        f"media path drift for {sample.sample_id!r}"
                    )
                if sample.audio_ref.sha256 != item.get("audio_sha256"):
                    raise A2TSelfTranscriptFlightError(
                        f"audio bytes drift for {sample.sample_id!r}"
                    )
            self._cache = picked
        return self._cache

    def build_task_contract(self, sample: Audio2ToolSample, obs: object) -> str:
        if self._phase == OBSERVATION_PHASE:
            contract = render_observation_system_contract()
        else:
            base_contract = super().build_task_contract(sample, obs)  # type: ignore[arg-type]
            material = self._material[sample.sample_id]
            contract = render_use_prompt_block(
                task_contract=base_contract,
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
            raise A2TSelfTranscriptFlightError(
                "self-transcript adapter rejects a second supply channel"
            )
        try:
            contract = self._contracts[sample.sample_id]
        except KeyError:
            raise A2TSelfTranscriptFlightError(
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


def _assert_liveness_receipt(receipt: object) -> None:
    passed = getattr(receipt, "passed", None)
    row_count = getattr(receipt, "row_count", None)
    report_sha256 = getattr(receipt, "report_sha256", None)
    if passed is not True or row_count != 104:
        raise A2TSelfTranscriptFlightError(
            "evidence use requires a passing 104-row liveness receipt"
        )
    if (
        not isinstance(report_sha256, str)
        or len(report_sha256) != 64
        or any(character not in "0123456789abcdef" for character in report_sha256)
    ):
        raise A2TSelfTranscriptFlightError(
            "liveness receipt must carry a lowercase 64-hex report hash"
        )


class SingleContactController:
    """One registered OBS or USE contact followed by an unconditional stop."""

    def __init__(self, *, phase: str, liveness_receipt: object | None = None) -> None:
        try:
            self._policy_id = _PHASE_POLICY[phase]
            self._contact_id = _PHASE_CONTACT[phase]
        except KeyError:
            raise A2TSelfTranscriptFlightError(
                f"unknown self-transcript phase {phase!r}"
            ) from None
        self._phase = phase
        if phase == OBSERVATION_PHASE:
            if liveness_receipt is not None:
                raise A2TSelfTranscriptFlightError(
                    "observation phase cannot receive a liveness receipt"
                )
        else:
            _assert_liveness_receipt(liveness_receipt)

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if context.query_state.loop_step != 0:
            raise A2TSelfTranscriptFlightError(
                "single-contact phase requires loop step zero"
            )
        if self._phase == OBSERVATION_PHASE:
            instruction = cascade.SELF_TRANSCRIPT_INSTRUCTION
            decoding = {"max_tokens": 192, "temperature": 0}
            purpose = "observe-english-self-transcript"
        else:
            instruction = _USE_INSTRUCTION
            decoding = {}
            purpose = "answer-with-matched-evidence" if self._phase == MATCHED_USE_PHASE else "answer-with-shuffled-evidence"
        return AgentContactPlan(
            contact_id=self._contact_id,
            query_state_sha256=context.query_state.content_hash(),
            purpose=purpose,
            instruction=instruction,
            key_representation_id=f"{self._policy_id}:speech",
            matcher_policy_id=(
                cascade.RETRIEVER_POLICY_ID
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
            raise A2TSelfTranscriptFlightError(
                "single-contact controller received a batched contact"
            )
        if context.query_state.loop_step != 0 or contact.contact_id != self._contact_id:
            raise A2TSelfTranscriptFlightError(
                "single-contact controller received an invalid contact sequence"
            )
        if not isinstance(response_text, str):
            raise A2TSelfTranscriptFlightError(
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


def render_use_prompt_block(
    *,
    task_contract: str,
    recipient_transcript: str,
    evidence_contents: Sequence[str],
    phase: str,
) -> str:
    """Render one English per-sample USE prompt without donor transcript text."""

    if phase not in {MATCHED_USE_PHASE, SHUFFLED_USE_PHASE}:
        raise A2TSelfTranscriptFlightError("prompt rendering requires a USE phase")
    if not isinstance(task_contract, str) or not task_contract.strip():
        raise A2TSelfTranscriptFlightError("USE prompt requires a task contract")
    parsed = cascade.validate_self_transcript(recipient_transcript)
    if not parsed.valid:
        raise A2TSelfTranscriptFlightError(
            f"USE prompt rejected recipient transcript: {parsed.reason}"
        )
    evidence = tuple(evidence_contents)
    if not 1 <= len(evidence) <= 6 or any(
        not isinstance(item, str) or not item.strip() for item in evidence
    ):
        raise A2TSelfTranscriptFlightError(
            "USE prompt requires one through six non-empty evidence values"
        )
    label = "matched" if phase == MATCHED_USE_PHASE else "shuffled-control"
    rendered_evidence = "\n".join(
        f"[evidence {index}] {value}" for index, value in enumerate(evidence, start=1)
    )
    return (
        f"{task_contract.strip()}\n\n"
        "English self-transcript Agent state:\n"
        f"{parsed.text}\n\n"
        f"Supplied {label} evidence:\n{rendered_evidence}"
    )


def _exact_identity(
    left: Mapping[str, object], right_ids: Sequence[str]
) -> None:
    expected = set(left)
    observed = set(right_ids)
    if expected != observed:
        raise A2TSelfTranscriptFlightError(
            "speech-packet/result identity mismatch: "
            f"packet_only={sorted(expected - observed)!r}, "
            f"result_only={sorted(observed - expected)!r}"
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
    """Execute one one-contact phase through the pinned openJiuwen executor."""

    try:
        policy_id = _PHASE_POLICY[phase]
    except KeyError:
        raise A2TSelfTranscriptFlightError(
            f"unknown self-transcript phase {phase!r}"
        ) from None
    if phase != OBSERVATION_PHASE:
        _assert_liveness_receipt(liveness_receipt)
    controller_registry = Registry("self-transcript cascade Agent controller")
    controller_registry.register(
        policy_id,
        lambda _sample_id: SingleContactController(
            phase=phase, liveness_receipt=liveness_receipt
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
        raise A2TSelfTranscriptFlightError(
            "phase summary is not bound to openjiuwen-workflow-v1"
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple):
        raise A2TSelfTranscriptFlightError(
            "AgentLoop summary must expose a tuple of results"
        )
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise A2TSelfTranscriptFlightError(
                "AgentLoop result lacks a non-empty sample_id"
            )
        if not isinstance(contacts, tuple) or len(contacts) != 1:
            raise A2TSelfTranscriptFlightError(
                f"AgentLoop result {sample_id!r} must have exactly one contact"
            )
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids):
        raise A2TSelfTranscriptFlightError("AgentLoop results contain duplicate ids")
    _exact_identity(speech_packet_bindings, result_ids)
    return summary


__all__ = [
    "AGENT_EXECUTOR_ID",
    "MATCHED_CONTACT_ID",
    "MATCHED_USE_PHASE",
    "OBSERVATION_CONTACT_ID",
    "OBSERVATION_PHASE",
    "SHUFFLED_CONTACT_ID",
    "SHUFFLED_USE_PHASE",
    "SPLIT_ID",
    "A2TSelfTranscriptAdapter",
    "A2TSelfTranscriptFlightError",
    "SingleContactController",
    "UseMaterial",
    "build_use_material",
    "render_observation_system_contract",
    "render_use_prompt_block",
    "run_phase",
]
