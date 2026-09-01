"""Fail-closed flight boundary for the registered Audio2Tool probe.

The module keeps the two prospective model-contact phases deliberately small:
one speech-conditioned contact per sample, dispatched through the formal
openJiuwen workflow executor.  It also derives the values-stripped SUPPLY
material from frozen M0 and prospective repeat responses without accepting
gold or scorer output.
"""

from __future__ import annotations

import json
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

from ...analysis.training_free_a2t_self_consistency import (
    SelfConsistencyState,
    extract_self_consistency_state,
    render_union_stripped_registry,
)
from ...core.base import Registry
from ..adapters.audio2tool import Audio2ToolAdapter, Audio2ToolSample
from ..knowledge import AgentStepTransition
from ..runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)

SPLIT_ID = "A2T-SELF-CONSISTENCY-104"
OBSERVATION_PHASE = "REOBSERVE_DIRECT"
SUPPLY_PHASE = "SUPPLY_UNION_STRIPPED"
OBSERVATION_POLICY_ID = "saea-a2t-self-consistency-reobserve-direct-v1"
SUPPLY_POLICY_ID = "saea-a2t-self-consistency-supply-union-stripped-v1"
AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"
UNRESOLVED_SUPPLY_SENTINEL = (
    "No registry-resolved tool evidence is available for this query."
)

_A2T_INSTRUCTION_TEMPLATE = (
    "You control tools. Available tools:\n{tool_schemas}\n\n"
    'Respond with ONLY a JSON array of tool calls, e.g. '
    '[{{"name": "x", "arguments": {{}}}}].'
)

_PHASE_POLICY = {
    OBSERVATION_PHASE: OBSERVATION_POLICY_ID,
    SUPPLY_PHASE: SUPPLY_POLICY_ID,
}
_PHASE_CONTACT = {
    OBSERVATION_PHASE: "reobserve-direct",
    SUPPLY_PHASE: "supply-union-stripped",
}
_PHASE_INSTRUCTION = {
    OBSERVATION_PHASE: (
        "Decide under the task contract already given above. Answer using only "
        "the speech query; no external knowledge has been supplied yet."
    ),
    SUPPLY_PHASE: (
        "Decide under the task contract already given above. Answer using the "
        "speech query together with the supplied values-stripped registry "
        "evidence."
    ),
}


class A2TSelfConsistencyFlightError(RuntimeError):
    """The flight boundary refused an invalid or unregistered execution."""


@dataclass(frozen=True)
class SupplyMaterial:
    """Gold-free runtime material derived from a paired direct observation."""

    sample_id: str
    prompt_block: str
    tool_names: tuple[str, ...]
    state: SelfConsistencyState

    @property
    def supply_available(self) -> bool:
        return bool(self.tool_names)


class A2TSelfConsistencyAdapter(Audio2ToolAdapter):
    """Receipt-filtered adapter with gold permanently deferred during flight."""

    def __init__(
        self,
        lock: Mapping[str, object],
        root: Path,
        *,
        repo_root: Path,
        receipt_items: Sequence[Mapping[str, object]],
        phase: str,
        supply_material: Mapping[str, SupplyMaterial] | None = None,
    ) -> None:
        super().__init__(lock, root, repo_root=repo_root)
        if phase not in _PHASE_POLICY:
            raise A2TSelfConsistencyFlightError(
                f"unknown self-consistency phase {phase!r}"
            )
        by_id: dict[str, Mapping[str, object]] = {}
        for item in receipt_items:
            sample_id = item.get("sample_id")
            if not isinstance(sample_id, str) or not sample_id:
                raise A2TSelfConsistencyFlightError(
                    "receipt item lacks a non-empty sample_id"
                )
            if sample_id in by_id:
                raise A2TSelfConsistencyFlightError(
                    f"receipt contains duplicate sample_id {sample_id!r}"
                )
            by_id[sample_id] = item
        if not by_id:
            raise A2TSelfConsistencyFlightError("receipt resolves to zero samples")
        self._phase = phase
        self._by_id = by_id
        self._cache: tuple[Audio2ToolSample, ...] | None = None
        self._supply_material = dict(supply_material or {})
        if phase == SUPPLY_PHASE:
            _exact_identity(
                by_id, self._supply_material, label="receipt/supply-material"
            )
        elif self._supply_material:
            raise A2TSelfConsistencyFlightError(
                "observation phase must not receive supply material"
            )

    def load_split(self, split_id: str) -> tuple[Audio2ToolSample, ...]:
        if split_id != SPLIT_ID:
            raise A2TSelfConsistencyFlightError(
                f"adapter serves only {SPLIT_ID!r}, not {split_id!r}"
            )
        if self._cache is None:
            exposed = super().load_split("discovery")
            picked = tuple(
                sorted(
                    (sample for sample in exposed if sample.sample_id in self._by_id),
                    key=lambda sample: sample.sample_id,
                )
            )
            if len(picked) != len(self._by_id):
                missing = set(self._by_id) - {sample.sample_id for sample in picked}
                raise A2TSelfConsistencyFlightError(
                    f"discovery carrier lacks receipt samples: {sorted(missing)!r}"
                )
            for sample in picked:
                item = self._by_id[sample.sample_id]
                if sample.media_relpath != item.get("media_relpath"):
                    raise A2TSelfConsistencyFlightError(
                        f"media_relpath drift for {sample.sample_id!r}"
                    )
                if sample.audio_ref.sha256 != item.get("audio_sha256"):
                    raise A2TSelfConsistencyFlightError(
                        f"audio bytes drift for {sample.sample_id!r}"
                    )
            self._cache = picked
        return self._cache

    def _supply_for(self, sample_id: str) -> SupplyMaterial:
        try:
            return self._supply_material[sample_id]
        except KeyError:
            raise A2TSelfConsistencyFlightError(
                f"supply material lacks sample {sample_id!r}"
            ) from None

    def build_task_contract(self, sample: Audio2ToolSample, obs: object) -> str:
        if self._phase == OBSERVATION_PHASE:
            return super().build_task_contract(sample, obs)  # type: ignore[arg-type]
        return self._supply_for(sample.sample_id).prompt_block

    def assemble_prompt(
        self, sample: Audio2ToolSample, supply: object
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise A2TSelfConsistencyFlightError(
                "self-consistency adapter does not accept a second supply channel"
            )
        if self._phase == OBSERVATION_PHASE:
            return tuple(super().assemble_prompt(sample, None))
        prompt_block = self._supply_for(sample.sample_id).prompt_block
        instruction = _A2T_INSTRUCTION_TEMPLATE.format(tool_schemas=prompt_block)
        return (
            {"role": "system", "content": instruction},
            {
                "role": "user",
                "content": [
                    {"type": "input_audio", "media_relpath": sample.media_relpath}
                ],
            },
        )

    def score(self, sample: Audio2ToolSample, response: str) -> Mapping[str, object]:
        return {"scoring_deferred": True}


def _exact_identity(
    left: Mapping[str, object], right: Mapping[str, object], *, label: str
) -> tuple[str, ...]:
    left_ids = set(left)
    right_ids = set(right)
    if left_ids != right_ids:
        raise A2TSelfConsistencyFlightError(
            f"{label} identity mismatch: "
            f"left_only={sorted(left_ids - right_ids)!r}, "
            f"right_only={sorted(right_ids - left_ids)!r}"
        )
    if not left_ids:
        raise A2TSelfConsistencyFlightError(f"{label} resolved to zero samples")
    return tuple(sorted(left_ids))


def build_supply_material(
    m0_responses: Mapping[str, str],
    observation_responses: Mapping[str, str],
    registry_rows: Sequence[Mapping[str, str]],
) -> dict[str, SupplyMaterial]:
    """Build the registered deterministic union for every paired sample."""

    sample_ids = _exact_identity(
        m0_responses, observation_responses, label="M0/observation"
    )
    material: dict[str, SupplyMaterial] = {}
    for sample_id in sample_ids:
        m0_response = m0_responses[sample_id]
        observation_response = observation_responses[sample_id]
        if not isinstance(m0_response, str) or not isinstance(
            observation_response, str
        ):
            raise A2TSelfConsistencyFlightError(
                f"responses for {sample_id!r} must both be strings"
            )
        rendered = render_union_stripped_registry(
            m0_response, observation_response, registry_rows
        )
        if "argument_defaults" in rendered.text:
            raise A2TSelfConsistencyFlightError(
                f"values-stripped renderer leaked argument_defaults for {sample_id!r}"
            )
        material[sample_id] = SupplyMaterial(
            sample_id=sample_id,
            prompt_block=(rendered.text or UNRESOLVED_SUPPLY_SENTINEL),
            tool_names=rendered.tool_names,
            state=extract_self_consistency_state(m0_response, observation_response),
        )
    return material


def load_frozen_m0_outputs(
    path: Path, *, expected_ids: Sequence[str]
) -> dict[str, str]:
    """Load the frozen M0 output artifact with exact roster and row checks."""

    expected = tuple(expected_ids)
    if not expected or len(set(expected)) != len(expected):
        raise A2TSelfConsistencyFlightError(
            "expected M0 identities must be non-empty and unique"
        )
    loaded: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise A2TSelfConsistencyFlightError(
            f"could not read frozen M0 outputs: {error}"
        ) from error
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            raise A2TSelfConsistencyFlightError(
                f"blank frozen M0 row at line {line_number}"
            )
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise A2TSelfConsistencyFlightError(
                f"invalid frozen M0 JSON at line {line_number}: {error}"
            ) from error
        if not isinstance(row, Mapping):
            raise A2TSelfConsistencyFlightError(
                f"frozen M0 row {line_number} must be an object"
            )
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise A2TSelfConsistencyFlightError(
                f"frozen M0 row {line_number} lacks sample_id"
            )
        if sample_id in loaded:
            raise A2TSelfConsistencyFlightError(
                f"duplicate frozen M0 sample_id {sample_id!r}"
            )
        final = row.get("final_response_text")
        direct = row.get("direct_response_text")
        if (
            row.get("arm") != "M0"
            or not isinstance(final, str)
            or direct != final
            or row.get("contacts") != 1
            or not isinstance(row.get("slot_ids"), list)
            or len(row["slot_ids"]) != 1
            or row.get("winner_label") is not None
        ):
            raise A2TSelfConsistencyFlightError(
                f"frozen M0 row {line_number} violates the one-contact M0 schema"
            )
        loaded[sample_id] = final
    _exact_identity(
        {sample_id: None for sample_id in expected}, loaded, label="expected/M0"
    )
    return {sample_id: loaded[sample_id] for sample_id in sorted(loaded)}


class SingleContactController:
    """One registered phase contact followed by an unconditional stop."""

    def __init__(self, *, phase: str) -> None:
        try:
            self._policy_id = _PHASE_POLICY[phase]
            self._contact_id = _PHASE_CONTACT[phase]
            self._instruction = _PHASE_INSTRUCTION[phase]
        except KeyError:
            raise A2TSelfConsistencyFlightError(
                f"unknown self-consistency phase {phase!r}"
            ) from None

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        return AgentContactPlan(
            contact_id=self._contact_id,
            query_state_sha256=context.query_state.content_hash(),
            purpose=self._contact_id,
            instruction=self._instruction,
            key_representation_id=f"{self._policy_id}:speech",
            matcher_policy_id=self._policy_id,
            decoding_params={},
        )

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: object,
    ) -> AgentLoopAdvance:
        if not isinstance(contact, AgentContactPlan):
            raise A2TSelfConsistencyFlightError(
                "single-contact controller received a batched contact"
            )
        if contact.contact_id != self._contact_id:
            raise A2TSelfConsistencyFlightError(
                f"unexpected contact id {contact.contact_id!r}"
            )
        if not isinstance(response_text, str):
            raise A2TSelfConsistencyFlightError(
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
        )
        return AgentLoopAdvance(
            transition=transition,
            next_query_state=None,
            new_agent_states=(),
            next_contact=None,
            final_response_contact_id=contact.contact_id,
        )


def run_phase(
    *,
    phase: str,
    data_root: Path,
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
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
) -> object:
    """Execute one phase through openJiuwen and verify one contact per item."""

    try:
        policy_id = _PHASE_POLICY[phase]
    except KeyError:
        raise A2TSelfConsistencyFlightError(
            f"unknown self-consistency phase {phase!r}"
        ) from None
    controller_registry = Registry("self-consistency Agent controller")
    controller_registry.register(
        policy_id, lambda _sample_id: SingleContactController(phase=phase)
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
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple):
        raise A2TSelfConsistencyFlightError(
            "AgentLoop summary must expose a tuple of results"
        )
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise A2TSelfConsistencyFlightError(
                "AgentLoop result lacks a non-empty sample_id"
            )
        if not isinstance(contacts, tuple) or len(contacts) != 1:
            raise A2TSelfConsistencyFlightError(
                f"AgentLoop result {sample_id!r} must have exactly one contact"
            )
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids):
        raise A2TSelfConsistencyFlightError("AgentLoop results contain duplicate ids")
    _exact_identity(
        speech_packet_bindings,
        {sample_id: None for sample_id in result_ids},
        label="packet/result",
    )
    return summary


def _trace_parts(
    trace_documents: Sequence[Mapping[str, object]],
) -> tuple[
    dict[str, Mapping[str, object]],
    dict[str, Mapping[str, object]],
    dict[str, Mapping[str, object]],
]:
    requests: dict[str, Mapping[str, object]] = {}
    responses: dict[str, Mapping[str, object]] = {}
    costs: dict[str, Mapping[str, object]] = {}
    targets = {
        "MODEL_REQUEST": ("/request", requests),
        "MODEL_RESPONSE": ("/response", responses),
        "COST": ("/cost", costs),
    }
    for number, document in enumerate(trace_documents, start=1):
        if not isinstance(document, Mapping):
            raise A2TSelfConsistencyFlightError(
                f"trace document {number} must be an object"
            )
        channel = document.get("channel")
        target = targets.get(channel) if isinstance(channel, str) else None
        if target is None:
            continue
        suffix, destination = target
        record_id = document.get("record_id")
        payload = document.get("payload")
        if (
            not isinstance(record_id, str)
            or not record_id.endswith(suffix)
            or not isinstance(payload, Mapping)
        ):
            raise A2TSelfConsistencyFlightError(
                f"trace document {number} has a malformed {channel} record"
            )
        request_id = record_id[: -len(suffix)]
        if not request_id or request_id in destination:
            raise A2TSelfConsistencyFlightError(
                f"trace carries a duplicate or blank {channel} request id"
            )
        destination[request_id] = payload
    return requests, responses, costs


def _cost_number(payload: Mapping[str, object], field: str) -> float:
    value = payload.get(field)
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or float(value) < 0
    ):
        raise A2TSelfConsistencyFlightError(
            f"trace cost field {field!r} must be finite and non-negative"
        )
    return float(value)


def build_phase_bundle_material(
    summary: object,
    trace_documents: Sequence[Mapping[str, object]],
    *,
    phase: str,
    umbrella_lock_sha256: str,
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    """Convert one sealed AgentLoop phase into standard bundle material."""

    if phase not in _PHASE_POLICY:
        raise A2TSelfConsistencyFlightError(
            f"unknown self-consistency phase {phase!r}"
        )
    if (
        not isinstance(umbrella_lock_sha256, str)
        or len(umbrella_lock_sha256) != 64
        or any(character not in "0123456789abcdef" for character in umbrella_lock_sha256)
    ):
        raise A2TSelfConsistencyFlightError(
            "umbrella lock identity must be lowercase 64-hex"
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or not results:
        raise A2TSelfConsistencyFlightError(
            "AgentLoop summary must carry non-empty tuple results"
        )
    result_by_id: dict[str, object] = {}
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        response_text = getattr(result, "final_response_text", None)
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(response_text, str)
        ):
            raise A2TSelfConsistencyFlightError(
                "AgentLoop result lacks sample_id or final_response_text"
            )
        if sample_id in result_by_id:
            raise A2TSelfConsistencyFlightError(
                f"AgentLoop summary duplicates sample {sample_id!r}"
            )
        result_by_id[sample_id] = result

    requests, responses, costs = _trace_parts(trace_documents)
    if set(requests) != set(responses) or set(requests) != set(costs):
        raise A2TSelfConsistencyFlightError(
            "phase trace request, response, and cost identities differ"
        )
    request_by_sample: dict[str, str] = {}
    for request_id, outer in requests.items():
        payload = outer.get("payload")
        if not isinstance(payload, Mapping):
            raise A2TSelfConsistencyFlightError(
                f"request {request_id!r} lacks its model payload"
            )
        sample_id = payload.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise A2TSelfConsistencyFlightError(
                f"request {request_id!r} lacks sample_id"
            )
        if sample_id in request_by_sample:
            raise A2TSelfConsistencyFlightError(
                f"phase trace has more than one request for sample {sample_id!r}"
            )
        if outer.get("arm") != "speech-feature-query" or payload.get(
            "carrier_lock_key"
        ) != "audio2tool":
            raise A2TSelfConsistencyFlightError(
                f"request {request_id!r} has the wrong arm or carrier"
            )
        request_by_sample[sample_id] = request_id
    if set(request_by_sample) != set(result_by_id):
        raise A2TSelfConsistencyFlightError(
            "phase trace and AgentLoop result identity mismatch"
        )

    rows: list[dict[str, object]] = []
    for sample_id in sorted(result_by_id):
        result = result_by_id[sample_id]
        request_id = request_by_sample[sample_id]
        request = requests[request_id]
        response = responses[request_id]
        response_text = getattr(result, "final_response_text")
        if response.get("text") != response_text:
            raise A2TSelfConsistencyFlightError(
                f"response drift between trace and AgentLoop result for {sample_id!r}"
            )
        response_text_sha256 = hashlib.sha256(response_text.encode("utf-8")).hexdigest()
        if response.get("response_text_sha256") != response_text_sha256:
            raise A2TSelfConsistencyFlightError(
                f"response text hash drift for {sample_id!r}"
            )
        request_sha256 = request.get("payload_sha256")
        response_sha256 = response.get("response_sha256")
        if any(
            not isinstance(value, str)
            or len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in (request_sha256, response_sha256)
        ):
            raise A2TSelfConsistencyFlightError(
                f"request or response hash is malformed for {sample_id!r}"
            )
        rows.append(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": "audio2tool",
                "arm": "speech-feature-query",
                "text": response_text,
                "admitted": True,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
                "phase": phase,
            }
        )

    calls_used = 0
    audio_seconds = 0.0
    latency_seconds = 0.0
    prompt_tokens = 0
    completion_tokens = 0
    for request_id in sorted(costs):
        payload = costs[request_id]
        calls = _cost_number(payload, "calls")
        if calls != 1.0:
            raise A2TSelfConsistencyFlightError(
                f"request {request_id!r} must account for exactly one call"
            )
        calls_used += 1
        audio_seconds += _cost_number(payload, "audio_seconds")
        latency_seconds += _cost_number(payload, "latency_seconds")
        for field, destination in (
            ("prompt_tokens", "prompt"),
            ("completion_tokens", "completion"),
        ):
            value = _cost_number(payload, field)
            if not value.is_integer():
                raise A2TSelfConsistencyFlightError(
                    f"trace cost field {field!r} must be integral"
                )
            if destination == "prompt":
                prompt_tokens += int(value)
            else:
                completion_tokens += int(value)
    if calls_used != len(rows):
        raise A2TSelfConsistencyFlightError(
            "phase cost row count differs from output row count"
        )
    cost = {
        "calls_used": calls_used,
        "audio_seconds_used": audio_seconds,
        "latency_seconds_total": latency_seconds,
        "prompt_tokens_total": prompt_tokens,
        "completion_tokens_total": completion_tokens,
        "tool_calls": 0,
        "umbrella_lock_sha256": umbrella_lock_sha256,
    }
    return tuple(rows), cost


__all__ = [
    "AGENT_EXECUTOR_ID",
    "A2TSelfConsistencyAdapter",
    "A2TSelfConsistencyFlightError",
    "OBSERVATION_PHASE",
    "OBSERVATION_POLICY_ID",
    "SPLIT_ID",
    "SUPPLY_PHASE",
    "SUPPLY_POLICY_ID",
    "UNRESOLVED_SUPPLY_SENTINEL",
    "SingleContactController",
    "SupplyMaterial",
    "build_supply_material",
    "build_phase_bundle_material",
    "load_frozen_m0_outputs",
    "run_phase",
]
