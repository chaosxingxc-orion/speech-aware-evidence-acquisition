"""Fresh two-phase Audio2Tool AgentLoop boundary for semantic retrieval.

OBS and USE are separate one-contact OpenJiuwen workflows.  OBS produces a
strict, label-free English observation state.  An external frozen retriever
uses that state to select a value-safe decision packet.  USE then receives the
same speech, the recipient observation as control state, and only the selected
packet as system context.  Scoring remains deferred outside this module.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Callable

from ...core.base import Registry
from ...core.model import FrozenCoreError
from ...core.model.transport import (
    _assert_agent_history_suffix,
    _ordered_speech_feature_content,
    _speech_history_texts,
)
from ..a2t_selected_tool_ground import SelectedToolDecisionPacket
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..core_client import _agent_history
from ..knowledge import AgentStepTransition
from ..runner import (
    AgentContactPlan,
    AgentLoopAdvance,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)
from ..supply import SupplyPacket
from ..task_adapter import TaskAdapter, TaskSample


OBSERVATION_PHASE = "OBS_SEMANTIC_STATE"
MATCHED_USE_PHASE = "USE_MATCHED_SELECTED_TOOLS"
SHUFFLED_USE_PHASE = "USE_SAME_TIER_SHUFFLED_SELECTED_TOOLS"
AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"
SLOT_COUNT = 2
QUEUE_DEPTH = 4
FRESH_DISCOVERY_ROW_COUNT = 104
OBS_TRANSCRIPT_MAX_CHARS = 2_048
OBS_QUERY_MAX_CHARS = 512

OBSERVATION_CONTACT_ID = "semantic-observation"
MATCHED_CONTACT_ID = "selected-tools-matched-use"
SHUFFLED_CONTACT_ID = "selected-tools-shuffled-use"

_PHASE_POLICY = {
    OBSERVATION_PHASE: "saea-a2t-semantic-observation-v1",
    MATCHED_USE_PHASE: "saea-a2t-selected-tools-matched-use-v1",
    SHUFFLED_USE_PHASE: "saea-a2t-selected-tools-shuffled-use-v1",
}
_PHASE_CONTACT = {
    OBSERVATION_PHASE: OBSERVATION_CONTACT_ID,
    MATCHED_USE_PHASE: MATCHED_CONTACT_ID,
    SHUFFLED_USE_PHASE: SHUFFLED_CONTACT_ID,
}
_USE_PHASES = frozenset({MATCHED_USE_PHASE, SHUFFLED_USE_PHASE})
_SHA256 = re.compile(r"[0-9a-f]{64}")
_ENGLISH_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")

_OBSERVATION_SYSTEM_CONTEXT = (
    "Listen to the speech once. Return exactly one JSON object with exactly "
    "the keys transcript and retrieval_query. transcript must be a faithful, "
    "non-empty English transcript of the speech. retrieval_query must be a "
    "concise, non-empty English paraphrase of the desired state or action, "
    "without any registered tool name. Do not answer the task, choose a tool, "
    "or add information absent from the speech."
)


class SemanticAgentLoopError(RuntimeError):
    """The fresh semantic AgentLoop boundary refused an unsafe input."""


@dataclass(frozen=True)
class ObservationState:
    """One exact, label-free OBS result derived from recipient speech."""

    transcript: str
    retrieval_query: str
    response_sha256: str

    def as_json(self) -> dict[str, str]:
        return {
            "transcript": self.transcript,
            "retrieval_query": self.retrieval_query,
        }

    def content_hash(self) -> str:
        return hashlib.sha256(_canonical_json_bytes(self.as_json())).hexdigest()


@dataclass(frozen=True)
class UseMaterial:
    """Recipient OBS state paired with one matched or shuffled donor packet."""

    recipient_sample_id: str
    donor_sample_id: str
    tier: str
    recipient_observation: ObservationState
    packet: SelectedToolDecisionPacket
    phase: str


@dataclass(frozen=True)
class RenderedUseRequest:
    """Rails envelope plus exact transport messages for prompt measurement."""

    prompt_order: str
    rails_messages: tuple[Mapping[str, object], ...]
    contact_instruction: str
    response_format: Mapping[str, object]
    history: tuple[Mapping[str, object], ...]
    rails_messages_ascii_bytes: int
    rails_messages_sha256: str
    rails_envelope_ascii_bytes: int
    rails_envelope_sha256: str
    rails_envelope: Mapping[str, object]
    transport_messages: tuple[Mapping[str, object], ...]
    transport_messages_ascii_bytes: int
    transport_messages_sha256: str


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, UnicodeEncodeError) as error:
        raise SemanticAgentLoopError("request surface must be ASCII JSON") from error


def observation_response_format() -> dict[str, object]:
    """Return the exact constrained OBS response grammar."""

    printable_ascii = r"^[\x20-\x7E]+$"
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "audio2tool_semantic_observation",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    "transcript": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": OBS_TRANSCRIPT_MAX_CHARS,
                        "pattern": printable_ascii,
                    },
                    "retrieval_query": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": OBS_QUERY_MAX_CHARS,
                        "pattern": printable_ascii,
                    },
                },
                "required": ["transcript", "retrieval_query"],
                "additionalProperties": False,
            },
        },
    }


def _reject_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _bounded_ascii_text(value: object, *, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SemanticAgentLoopError(f"{field} must be non-empty text")
    if not value.isascii():
        raise SemanticAgentLoopError(f"{field} must be ASCII English")
    if len(value) > maximum:
        raise SemanticAgentLoopError(f"{field} exceeds its character bound")
    if any(ord(character) < 32 or ord(character) > 126 for character in value):
        raise SemanticAgentLoopError(f"{field} must contain printable ASCII")
    return value


def parse_observation_response(
    response_text: object,
    *,
    registered_tool_names: Sequence[str],
) -> ObservationState:
    """Parse one OBS response exactly, without repair, fallback, or retry."""

    if (
        not isinstance(response_text, str)
        or not response_text
        or not response_text.isascii()
    ):
        raise SemanticAgentLoopError("OBS response must be non-empty ASCII JSON")
    try:
        document = json.loads(
            response_text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ValueError) as error:
        message = (
            "duplicate JSON key"
            if "duplicate JSON key" in str(error)
            else "invalid JSON"
        )
        raise SemanticAgentLoopError(f"OBS response is {message}") from error
    if not isinstance(document, Mapping) or set(document) != {
        "transcript",
        "retrieval_query",
    }:
        raise SemanticAgentLoopError(
            "OBS response must contain exactly transcript and retrieval_query"
        )
    transcript = _bounded_ascii_text(
        document["transcript"],
        field="transcript",
        maximum=OBS_TRANSCRIPT_MAX_CHARS,
    )
    retrieval_query = _bounded_ascii_text(
        document["retrieval_query"],
        field="retrieval_query",
        maximum=OBS_QUERY_MAX_CHARS,
    )
    names = tuple(registered_tool_names)
    if not names or any(
        not isinstance(name, str) or not name or not name.isascii() for name in names
    ):
        raise SemanticAgentLoopError(
            "registered tool names must be non-empty ASCII text"
        )
    query_folded = retrieval_query.casefold()
    if any(name.casefold() in query_folded for name in names):
        raise SemanticAgentLoopError("retrieval_query contains a registered tool name")
    if len(_ENGLISH_WORD.findall(retrieval_query)) < 2:
        raise SemanticAgentLoopError(
            "retrieval_query must be an English desired-state/action paraphrase"
        )
    return ObservationState(
        transcript=transcript,
        retrieval_query=retrieval_query,
        response_sha256=hashlib.sha256(response_text.encode("ascii")).hexdigest(),
    )


def _validate_packet(packet: object) -> SelectedToolDecisionPacket:
    if not isinstance(packet, SelectedToolDecisionPacket):
        raise SemanticAgentLoopError(
            "USE material requires a SelectedToolDecisionPacket"
        )
    names = packet.selected_tool_names
    if (
        not isinstance(names, tuple)
        or not 1 <= len(names) <= 16
        or len(set(names)) != len(names)
        or any(
            not isinstance(name, str) or not name or not name.isascii()
            for name in names
        )
    ):
        raise SemanticAgentLoopError("selected-tool packet identity is malformed")
    if (
        not isinstance(packet.text, str)
        or not packet.text
        or not packet.text.isascii()
        or hashlib.sha256(packet.text.encode("ascii")).hexdigest() != packet.text_sha256
    ):
        raise SemanticAgentLoopError("selected-tool packet text hash drift")
    if (
        hashlib.sha256(_canonical_json_bytes(packet.response_format)).hexdigest()
        != packet.response_format_sha256
    ):
        raise SemanticAgentLoopError("selected-tool packet response-format hash drift")
    try:
        schema = packet.response_format["json_schema"]["schema"]  # type: ignore[index]
        branches = schema["items"]["oneOf"]  # type: ignore[index]
        branch_names = {branch["properties"]["name"]["const"] for branch in branches}
    except (KeyError, TypeError) as error:
        raise SemanticAgentLoopError(
            "selected-tool packet response format is malformed"
        ) from error
    if branch_names != set(names):
        raise SemanticAgentLoopError(
            "selected-tool packet schema and selected identities disagree"
        )
    if packet.report.get("selected_tool_count") != len(names):
        raise SemanticAgentLoopError("selected-tool packet count report drift")
    prohibited = (
        "construction example",
        "source utterance",
        "sample id",
        "reference label",
        "gold label",
        "score:",
    )
    if any(marker in packet.text.casefold() for marker in prohibited):
        raise SemanticAgentLoopError(
            "selected-tool packet contains prohibited runtime material"
        )
    return packet


def deterministic_same_stratum_derangement(
    stratum_by_sample: Mapping[str, tuple[str, int]],
    *,
    seed: str,
) -> dict[str, str]:
    """Return a deterministic donor derangement within tier/card-count strata."""

    if not isinstance(seed, str) or not seed or not seed.isascii():
        raise SemanticAgentLoopError("derangement seed must be non-empty ASCII")
    if not stratum_by_sample:
        raise SemanticAgentLoopError("derangement requires non-empty identities")
    groups: dict[tuple[str, int], list[str]] = defaultdict(list)
    for sample_id, stratum in stratum_by_sample.items():
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(stratum, tuple)
            or len(stratum) != 2
            or not isinstance(stratum[0], str)
            or not stratum[0]
            or isinstance(stratum[1], bool)
            or not isinstance(stratum[1], int)
            or stratum[1] < 1
        ):
            raise SemanticAgentLoopError("derangement strata are malformed")
        groups[stratum].append(sample_id)
    donors: dict[str, str] = {}
    for stratum, members in groups.items():
        if len(members) < 2:
            raise SemanticAgentLoopError(
                f"derangement is impossible for singleton stratum {stratum!r}"
            )
        ordered = sorted(
            members,
            key=lambda sample_id: (
                hashlib.sha256(f"{seed}\0{sample_id}".encode("utf-8")).hexdigest(),
                sample_id,
            ),
        )
        for index, recipient in enumerate(ordered):
            donors[recipient] = ordered[(index + 1) % len(ordered)]
    if any(recipient == donor for recipient, donor in donors.items()):
        raise SemanticAgentLoopError("deterministic derangement retained a recipient")
    return donors


def build_matched_and_shuffled_material(
    *,
    observations: Mapping[str, ObservationState],
    matched_packets: Mapping[str, SelectedToolDecisionPacket],
    sample_tiers: Mapping[str, str],
    seed: str,
) -> tuple[dict[str, UseMaterial], dict[str, UseMaterial]]:
    """Create matched and same-tier, equal-card-count control material."""

    identities = set(observations)
    if (
        not identities
        or identities != set(matched_packets)
        or identities != set(sample_tiers)
    ):
        raise SemanticAgentLoopError(
            "observation, packet, and tier identities must match exactly"
        )
    for sample_id in identities:
        if not isinstance(observations[sample_id], ObservationState):
            raise SemanticAgentLoopError("observation material has the wrong type")
        _validate_packet(matched_packets[sample_id])
        if not isinstance(sample_tiers[sample_id], str) or not sample_tiers[sample_id]:
            raise SemanticAgentLoopError("sample tiers must be non-empty text")
    strata = {
        sample_id: (
            sample_tiers[sample_id],
            len(matched_packets[sample_id].selected_tool_names),
        )
        for sample_id in identities
    }
    donors = deterministic_same_stratum_derangement(strata, seed=seed)
    matched: dict[str, UseMaterial] = {}
    shuffled: dict[str, UseMaterial] = {}
    for sample_id in sorted(identities):
        donor_id = donors[sample_id]
        matched[sample_id] = UseMaterial(
            recipient_sample_id=sample_id,
            donor_sample_id=sample_id,
            tier=sample_tiers[sample_id],
            recipient_observation=observations[sample_id],
            packet=matched_packets[sample_id],
            phase=MATCHED_USE_PHASE,
        )
        shuffled[sample_id] = UseMaterial(
            recipient_sample_id=sample_id,
            donor_sample_id=donor_id,
            tier=sample_tiers[sample_id],
            recipient_observation=observations[sample_id],
            packet=matched_packets[donor_id],
            phase=SHUFFLED_USE_PHASE,
        )
    return matched, shuffled


def _use_control_instruction(material: UseMaterial) -> str:
    observation = material.recipient_observation
    rendered = (
        "Use the original speech, the recipient observation state below, and only "
        "the selected decision cards in the system context. Return the ordered "
        "JSON call array allowed by the per-sample response format.\n"
        "Recipient transcript:\n"
        f"{observation.transcript}\n"
        "Recipient retrieval query:\n"
        f"{observation.retrieval_query}"
    )
    if not rendered.isascii():
        raise SemanticAgentLoopError("USE control instruction must be ASCII English")
    return rendered


class FreshSemanticPhaseAdapter(TaskAdapter):
    """In-memory, score-deferred adapter for one fresh OBS or USE phase."""

    def __init__(
        self,
        *,
        split_id: str,
        samples: Sequence[TaskSample],
        phase: str,
        registered_tool_names: Sequence[str] = (),
        use_material: Mapping[str, UseMaterial] | None = None,
    ) -> None:
        if not isinstance(split_id, str) or not split_id or not split_id.isascii():
            raise SemanticAgentLoopError("fresh split id must be non-empty ASCII")
        if phase not in _PHASE_POLICY:
            raise SemanticAgentLoopError("unknown semantic AgentLoop phase")
        sample_rows = tuple(samples)
        sample_ids = tuple(getattr(sample, "sample_id", None) for sample in sample_rows)
        if (
            not sample_rows
            or any(
                not isinstance(sample_id, str) or not sample_id
                for sample_id in sample_ids
            )
            or len(set(sample_ids)) != len(sample_ids)
        ):
            raise SemanticAgentLoopError("fresh samples must have unique non-empty ids")
        material = dict(use_material or {})
        names = tuple(registered_tool_names)
        if phase == OBSERVATION_PHASE:
            if material:
                raise SemanticAgentLoopError("OBS cannot receive USE material")
            if not names:
                raise SemanticAgentLoopError("OBS requires registered tool names")
        else:
            if names:
                raise SemanticAgentLoopError("USE cannot receive a registry name list")
            if set(material) != set(sample_ids):
                raise SemanticAgentLoopError(
                    "USE material must cover fresh samples exactly"
                )
            for sample_id, item in material.items():
                if (
                    not isinstance(item, UseMaterial)
                    or item.recipient_sample_id != sample_id
                    or item.phase != phase
                ):
                    raise SemanticAgentLoopError(
                        "USE material phase or recipient drift"
                    )
                _validate_packet(item.packet)
        self.split_id = split_id
        self.phase = phase
        self.samples = sample_rows
        self.sample_ids = tuple(sample_ids)
        self.registered_tool_names = names
        self.use_material = material

    def load_split(self, split_id: str) -> tuple[TaskSample, ...]:
        if split_id != self.split_id:
            raise SemanticAgentLoopError("fresh adapter split id drift")
        return self.samples

    def build_task_contract(self, sample: TaskSample, obs: object) -> str:
        if sample.sample_id not in self.sample_ids:
            raise SemanticAgentLoopError("sample is outside the fresh adapter")
        if self.phase == OBSERVATION_PHASE:
            return _OBSERVATION_SYSTEM_CONTEXT
        return self.use_material[sample.sample_id].packet.text

    def assemble_prompt(
        self, sample: TaskSample, supply: SupplyPacket | None
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise SemanticAgentLoopError("fresh semantic adapter rejects supply")
        contract = self.build_task_contract(sample, object())
        return (
            {"role": "system", "content": contract},
            {"role": "user", "content": []},
        )

    def score(self, sample: TaskSample, response: str) -> Mapping[str, object]:
        return {"scoring_deferred": True}

    def extract_consumption(
        self,
        sample: TaskSample,
        supply: SupplyPacket | None,
        response: str,
    ) -> ConsumptionTrace:
        return build_consumption_trace(
            span_id="full", supply=supply, response_text=response
        )

    def render_use_request(
        self,
        sample_id: str,
        speech_packet_binding: Mapping[str, object],
        *,
        prompt_order: str,
    ) -> RenderedUseRequest:
        """Render the rails envelope and exact pre-template transport messages."""

        if self.phase not in _USE_PHASES:
            raise SemanticAgentLoopError("request rendering requires a USE phase")
        if sample_id not in self.use_material:
            raise SemanticAgentLoopError("request sample is outside USE material")
        if set(speech_packet_binding) != {"packet_id", "sha256"}:
            raise SemanticAgentLoopError("speech packet binding keys are malformed")
        packet_id = speech_packet_binding["packet_id"]
        packet_sha256 = speech_packet_binding["sha256"]
        if (
            not isinstance(packet_id, str)
            or not packet_id
            or not packet_id.isascii()
            or not isinstance(packet_sha256, str)
            or _SHA256.fullmatch(packet_sha256) is None
        ):
            raise SemanticAgentLoopError("speech packet binding values are malformed")
        material = self.use_material[sample_id]
        rails_messages: tuple[Mapping[str, object], ...] = (
            {"role": "system", "content": material.packet.text},
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
        instruction = _use_control_instruction(material)
        history = tuple(
            _agent_history(
                agent_state=(),
                agent_contact_id=_PHASE_CONTACT[self.phase],
                contact_instruction=instruction,
            )
        )
        rails_envelope: Mapping[str, object] = {
            "messages": rails_messages,
            "agent_state": [],
            "agent_contact_id": _PHASE_CONTACT[self.phase],
            "contact_instruction": instruction,
            "response_format": material.packet.response_format,
        }
        feature_parts = list(rails_messages[1]["content"])  # type: ignore[arg-type,index]
        try:
            state_texts = _speech_history_texts(list(history))
            ordered_content = _ordered_speech_feature_content(
                prompt_order=prompt_order,
                evidence_texts=[],
                feature_parts=feature_parts,
                state_texts=state_texts,
                knowledge_roles=(),
            )
            _assert_agent_history_suffix(
                prompt_order=prompt_order,
                content=ordered_content,
                state_texts=state_texts,
            )
        except FrozenCoreError as error:
            raise SemanticAgentLoopError(
                f"unsupported or invalid transport prompt order: {error}"
            ) from error
        transport_messages: tuple[Mapping[str, object], ...] = (
            {"role": "system", "content": material.packet.text},
            {"role": "user", "content": ordered_content},
        )
        rails_message_bytes = _canonical_json_bytes(rails_messages)
        rails_envelope_bytes = _canonical_json_bytes(rails_envelope)
        transport_message_bytes = _canonical_json_bytes(transport_messages)
        return RenderedUseRequest(
            prompt_order=prompt_order,
            rails_messages=rails_messages,
            contact_instruction=instruction,
            response_format=material.packet.response_format,
            history=history,
            rails_messages_ascii_bytes=len(rails_message_bytes),
            rails_messages_sha256=hashlib.sha256(rails_message_bytes).hexdigest(),
            rails_envelope_ascii_bytes=len(rails_envelope_bytes),
            rails_envelope_sha256=hashlib.sha256(rails_envelope_bytes).hexdigest(),
            rails_envelope=rails_envelope,
            transport_messages=transport_messages,
            transport_messages_ascii_bytes=len(transport_message_bytes),
            transport_messages_sha256=hashlib.sha256(
                transport_message_bytes
            ).hexdigest(),
        )


class SingleContactController:
    """One fresh OBS or USE contact followed by an unconditional stop."""

    def __init__(
        self,
        *,
        phase: str,
        registered_tool_names: Sequence[str] = (),
        use_material: UseMaterial | None = None,
    ) -> None:
        if phase not in _PHASE_POLICY:
            raise SemanticAgentLoopError("unknown semantic AgentLoop phase")
        self.phase = phase
        self.registered_tool_names = tuple(registered_tool_names)
        self.use_material = use_material
        self.observation: ObservationState | None = None
        if phase == OBSERVATION_PHASE:
            if not self.registered_tool_names or use_material is not None:
                raise SemanticAgentLoopError(
                    "OBS requires registry names and forbids USE material"
                )
        elif (
            self.registered_tool_names
            or not isinstance(use_material, UseMaterial)
            or use_material.phase != phase
        ):
            raise SemanticAgentLoopError(
                "USE requires phase-matched material and no registry list"
            )

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContactPlan:
        if context.query_state.loop_step != 0 or context.contact_index != 0:
            raise SemanticAgentLoopError(
                "single-contact phase requires fresh step zero"
            )
        if self.phase == OBSERVATION_PHASE:
            instruction = _OBSERVATION_SYSTEM_CONTEXT
            decoding = {
                "max_tokens": 768,
                "temperature": 0,
                "response_format": observation_response_format(),
            }
            purpose = "observe-label-free-semantic-state"
        else:
            assert self.use_material is not None
            if context.sample_id != self.use_material.recipient_sample_id:
                raise SemanticAgentLoopError("USE controller recipient identity drift")
            instruction = _use_control_instruction(self.use_material)
            decoding = {
                "temperature": 0,
                "response_format": self.use_material.packet.response_format,
            }
            purpose = (
                "answer-with-matched-selected-tools"
                if self.phase == MATCHED_USE_PHASE
                else "answer-with-shuffled-selected-tools"
            )
        return AgentContactPlan(
            contact_id=_PHASE_CONTACT[self.phase],
            query_state_sha256=context.query_state.content_hash(),
            purpose=purpose,
            instruction=instruction,
            key_representation_id=f"{_PHASE_POLICY[self.phase]}:speech",
            matcher_policy_id=_PHASE_POLICY[self.phase],
            decoding_params=decoding,
        ).validate()

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContactPlan,
        response_text: object,
    ) -> AgentLoopAdvance:
        if (
            not isinstance(contact, AgentContactPlan)
            or context.query_state.loop_step != 0
            or context.contact_index != 0
            or contact.contact_id != _PHASE_CONTACT[self.phase]
        ):
            raise SemanticAgentLoopError("invalid one-contact sequence")
        if self.phase == OBSERVATION_PHASE:
            self.observation = parse_observation_response(
                response_text,
                registered_tool_names=self.registered_tool_names,
            )
        elif not isinstance(response_text, str) or not response_text:
            raise SemanticAgentLoopError("USE response must be a non-empty string")
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
            final_response_contact_id=contact.contact_id,
        )


def run_phase(
    *,
    phase: str,
    data_root: object,
    plan: object,
    adapter: FreshSemanticPhaseAdapter,
    core_client: object,
    split_id: str,
    knowledge_snapshot: object,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    trace_sink: object,
    decoding_params: Mapping[str, object],
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
) -> object:
    """Run one fresh 104-row phase with fixed OpenJiuwen concurrency."""

    if phase not in _PHASE_POLICY:
        raise SemanticAgentLoopError("unknown semantic AgentLoop phase")
    if not isinstance(adapter, FreshSemanticPhaseAdapter) or adapter.phase != phase:
        raise SemanticAgentLoopError("phase requires its matching fresh adapter")
    if adapter.split_id != split_id:
        raise SemanticAgentLoopError("phase split id drift")
    if (
        len(adapter.sample_ids) != FRESH_DISCOVERY_ROW_COUNT
        or len(speech_packet_bindings) != FRESH_DISCOVERY_ROW_COUNT
    ):
        raise SemanticAgentLoopError("fresh phase requires exactly 104 samples")
    if set(adapter.sample_ids) != set(speech_packet_bindings):
        raise SemanticAgentLoopError("speech packet and fresh sample identities differ")
    if not isinstance(decoding_params, Mapping) or "response_format" in decoding_params:
        raise SemanticAgentLoopError(
            "run decoding parameters must leave response_format per sample"
        )

    controller_registry = Registry("fresh semantic Audio2Tool controller")
    if phase == OBSERVATION_PHASE:
        controller_registry.register(
            _PHASE_POLICY[phase],
            lambda _sample_id: SingleContactController(
                phase=phase,
                registered_tool_names=adapter.registered_tool_names,
            ),
        )
    else:
        controller_registry.register(
            _PHASE_POLICY[phase],
            lambda sample_id: SingleContactController(
                phase=phase,
                use_material=adapter.use_material[sample_id],
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
        controller_policy_id=_PHASE_POLICY[phase],
        max_contacts=1,
        slot_count=SLOT_COUNT,
        queue_depth=QUEUE_DEPTH,
        trace_sink=trace_sink,
        agent_executor_id=AGENT_EXECUTOR_ID,
        decoding_params=decoding_params,
        controller_registry=controller_registry,
    )
    if getattr(summary, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise SemanticAgentLoopError(
            "phase summary is not bound to openjiuwen-workflow-v1"
        )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != FRESH_DISCOVERY_ROW_COUNT:
        raise SemanticAgentLoopError("phase must return exactly 104 results")
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise SemanticAgentLoopError("phase result lacks a sample identity")
        if not isinstance(contacts, tuple) or len(contacts) != 1:
            raise SemanticAgentLoopError(
                "every fresh phase result must contain exactly one contact"
            )
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids) or set(result_ids) != set(
        adapter.sample_ids
    ):
        raise SemanticAgentLoopError(
            "phase result identities differ from fresh samples"
        )
    return summary


__all__ = [
    "AGENT_EXECUTOR_ID",
    "FRESH_DISCOVERY_ROW_COUNT",
    "MATCHED_CONTACT_ID",
    "MATCHED_USE_PHASE",
    "OBSERVATION_CONTACT_ID",
    "OBSERVATION_PHASE",
    "OBS_QUERY_MAX_CHARS",
    "OBS_TRANSCRIPT_MAX_CHARS",
    "QUEUE_DEPTH",
    "SHUFFLED_CONTACT_ID",
    "SHUFFLED_USE_PHASE",
    "SLOT_COUNT",
    "FreshSemanticPhaseAdapter",
    "ObservationState",
    "RenderedUseRequest",
    "SemanticAgentLoopError",
    "SingleContactController",
    "UseMaterial",
    "build_matched_and_shuffled_material",
    "deterministic_same_stratum_derangement",
    "observation_response_format",
    "parse_observation_response",
    "run_phase",
]
