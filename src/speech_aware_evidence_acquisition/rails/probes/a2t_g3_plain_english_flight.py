"""Focused OpenJiuwen runtime boundary for the bounded Audio2Tool G3 pilot.

The four phases are independent requests over the same frozen speech bindings:
legacy direct M0, task-blind English observation, matched-card USE, and the
identity-only shuffled-card control. Construction retrieval receives only the
bounded observation text. Gold, tier hints, and earlier conversation state do
not enter any runtime request.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from ...analysis import training_free_a2t_self_transcript_cascade as selftx
from ...core.base import Registry
from ..controllers import (
    HARD_VALIDITY_PROGRAM_ID,
    make_hard_validity_phase_controller,
)
from ..a2t_plain_english_cards import (
    MAX_DETAILED_TOOLS,
    PlainEnglishCardCorpus,
    PlainEnglishPacketRoute,
    retrieve_plain_english_packets,
)
from ..adapters.audio2tool import (
    Audio2ToolSample,
    render_audio2tool_instruction,
)
from ..consumption import ConsumptionTrace, build_consumption_trace
from ..obs import AudioRef
from ..runner import (
    AgentContact,
    AgentLoopAdvance,
    AgentResponse,
    AgentRuntimeContext,
    run_speech_native_agent_loop,
)
from ..task_adapter import TaskAdapter
from .a2t_contract_preserving_cascade_flight import (
    AGENT_EXECUTOR_ID,
    SingleContactController,
    run_direct_phase,
)
from .a2t_self_transcript_cascade_bundle import (
    build_phase_bundle_material,
    build_resend_composite_texts,
    build_use_composite_texts,
    emit_composite_rows,
)

G3_SPLIT_ID = "A2T-G3-PILOT-40"
G3_M0_DIRECT_PHASE = "G3_M0_DIRECT"
G3_OBSERVATION_PHASE = "G3_OBSERVATION"
G3_MATCHED_USE_PHASE = "G3_MATCHED_USE"
G3_SHUFFLED_USE_PHASE = "G3_SHUFFLED_USE"
G3_SHUFFLED_SELECTION_NAMESPACE = "a2t-g3-shuffled-control-v1"
G3_SHUFFLED_PER_TIER = 2
G3_EXPECTED_TIERS = 8
G3_EXPECTED_ROWS = 40
G3_EXPECTED_SHUFFLED_ROWS = 16
G3_DERIVED_MEDIA_IDENTITY_PREFIX = "a2t-g3-dialogue"

_OBS_POLICY_ID = "saea-a2t-g3-task-blind-observation-v1"
_USE_KEY_REPRESENTATION_ID = "a2t-g3-plain-english-k32-v1"
_MATCHED_POLICY_ID = "a2t-g3-construction-bm25-k32-matched-v1"
_SHUFFLED_POLICY_ID = "a2t-g3-construction-bm25-k32-shuffled-v1"
_PHASES = {
    G3_M0_DIRECT_PHASE,
    G3_OBSERVATION_PHASE,
    G3_MATCHED_USE_PHASE,
    G3_SHUFFLED_USE_PHASE,
}
_DIALOGUE_OBSERVATION_CONTRACT = (
    "The audio contains chronological English turns alternating user and assistant. "
    "It begins with a user turn and ends with the current user turn. Transcribe all "
    "turns verbatim with explicit role labels. Output only the role-labeled English "
    "transcript. Do not answer the request, infer missing content, emit JSON, or name "
    "a tool."
)
_USE_PREFIX = (
    "Use the original speech as the task authority and the task-blind English "
    "observation only as auxiliary evidence. Return only a nonempty JSON array of "
    'objects with exactly {"name":"exactToolName","arguments":{...}}. '
    "Do not add prose."
)
_DIALOGUE_ROLE_LINE = re.compile(r"(?im)^\s*(user|assistant)\s*:\s*\S")


class G3PilotFlightError(RuntimeError):
    """A frozen G3 identity, phase, packet, or result invariant failed."""


@dataclass(frozen=True)
class G3RuntimeSurface:
    """The exact 40 runtime samples and their already-promoted speech packets."""

    samples: tuple[Audio2ToolSample, ...]
    packet_bindings: Mapping[str, Mapping[str, str]]
    tier_by_sample: Mapping[str, str]
    derived_dialogue_sample_ids: tuple[str, ...]
    media_identity_by_sample: Mapping[str, str]


@dataclass(frozen=True)
class G3CompleteArmTexts:
    """Three complete maps directly consumable by existing bundle composition."""

    m0: Mapping[str, str]
    matched: Mapping[str, str]
    shuffled: Mapping[str, str]


def _items(document: object, *, label: str) -> tuple[Mapping[str, object], ...]:
    if not isinstance(document, Mapping) or not isinstance(document.get("items"), list):
        raise G3PilotFlightError(f"{label} must contain an items list")
    rows = tuple(document["items"])
    if document.get("count") != G3_EXPECTED_ROWS or len(rows) != G3_EXPECTED_ROWS:
        raise G3PilotFlightError(f"{label} must contain exactly 40 items")
    if any(not isinstance(row, Mapping) for row in rows):
        raise G3PilotFlightError(f"{label} contains a malformed item")
    return rows  # type: ignore[return-value]


def _lower_hex(value: object, *, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise G3PilotFlightError(f"{label} must be lowercase 64-hex")
    return value


def _indexed(
    rows: Sequence[Mapping[str, object]], *, label: str
) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for row in rows:
        sample_id = row.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id or sample_id in result:
            raise G3PilotFlightError(f"{label} sample identities must be unique text")
        result[sample_id] = row
    return result


def _resolve_path(data_root: Path, relpath: object, *, sample_id: str) -> Path:
    if not isinstance(relpath, str) or not relpath or Path(relpath).is_absolute():
        raise G3PilotFlightError(f"runtime media path is invalid for {sample_id!r}")
    root = Path(data_root).resolve()
    resolved = (root / relpath).resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise G3PilotFlightError(f"runtime media is missing for {sample_id!r}")
    return resolved


def resolve_g3_runtime_media(
    roster: Mapping[str, object],
    media_manifest: Mapping[str, object],
    packet_binding_document: Mapping[str, object],
    *,
    data_root: Path,
) -> G3RuntimeSurface:
    """Resolve and byte-verify the frozen 40-row runtime speech surface."""

    roster_by_id = _indexed(_items(roster, label="G3 roster"), label="G3 roster")
    media_by_id = _indexed(
        _items(media_manifest, label="G3 runtime media manifest"),
        label="G3 runtime media manifest",
    )
    bindings_value = packet_binding_document.get("bindings")
    if (
        packet_binding_document.get("count") != G3_EXPECTED_ROWS
        or not isinstance(bindings_value, Mapping)
    ):
        raise G3PilotFlightError("G3 packet binding document must contain 40 bindings")
    bindings = dict(bindings_value)
    if set(roster_by_id) != set(media_by_id) or set(roster_by_id) != set(bindings):
        raise G3PilotFlightError("G3 roster, media, and packet identities disagree")
    if media_manifest.get("tier7_complete_dialogue_count") != 5:
        raise G3PilotFlightError("G3 runtime media must contain five complete dialogues")

    samples: list[Audio2ToolSample] = []
    tiers: dict[str, str] = {}
    derived_ids: list[str] = []
    media_identity_by_sample: dict[str, str] = {}
    for sample_id in sorted(roster_by_id):
        roster_item = roster_by_id[sample_id]
        media_item = media_by_id[sample_id]
        tier = roster_item.get("tier")
        if not isinstance(tier, str) or media_item.get("tier") != tier:
            raise G3PilotFlightError(f"runtime tier drift for {sample_id!r}")
        relpath = media_item.get("media_relpath")
        path = _resolve_path(data_root, relpath, sample_id=sample_id)
        expected_audio_sha256 = _lower_hex(
            media_item.get("audio_sha256"), label=f"audio SHA-256 for {sample_id}"
        )
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_audio_sha256:
            raise G3PilotFlightError(f"audio SHA-256 drift for {sample_id!r}")
        audio_seconds = media_item.get("audio_seconds")
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or float(audio_seconds) <= 0.0
        ):
            raise G3PilotFlightError(f"audio duration is invalid for {sample_id!r}")
        if tier == "tier7_multiturn":
            if media_item.get("source_final_turn_media_relpath") != roster_item.get(
                "media_relpath"
            ):
                raise G3PilotFlightError(f"complete-dialogue source drift for {sample_id!r}")
            derived_ids.append(sample_id)
            numeric = sample_id.split(":", 1)[1]
            media_identity_by_sample[sample_id] = (
                f"{G3_DERIVED_MEDIA_IDENTITY_PREFIX}:{numeric}"
            )
        elif (
            relpath != roster_item.get("media_relpath")
            or expected_audio_sha256 != roster_item.get("audio_sha256")
        ):
            raise G3PilotFlightError(f"original runtime media drift for {sample_id!r}")
        else:
            media_identity_by_sample[sample_id] = sample_id

        binding = bindings[sample_id]
        if not isinstance(binding, Mapping):
            raise G3PilotFlightError(f"packet binding is malformed for {sample_id!r}")
        packet_id = binding.get("packet_id")
        packet_sha256 = _lower_hex(
            binding.get("sha256"), label=f"packet SHA-256 for {sample_id}"
        )
        if not isinstance(packet_id, str) or not packet_id:
            raise G3PilotFlightError(f"packet id is malformed for {sample_id!r}")
        if tier == "tier7_multiturn" and not packet_id.startswith(
            "g3_complete_dialogue/"
        ):
            raise G3PilotFlightError(
                f"complete-dialogue packet identity is missing for {sample_id!r}"
            )
        bindings[sample_id] = {"packet_id": packet_id, "sha256": packet_sha256}
        samples.append(
            Audio2ToolSample(
                sample_id=sample_id,
                audio_ref=AudioRef(path=str(relpath), sha256=expected_audio_sha256).validate(),
                audio_seconds=float(audio_seconds),
                media_relpath=str(relpath),
            )
        )
        tiers[sample_id] = tier

    if Counter(tiers.values()) != Counter({tier: 5 for tier in set(tiers.values())}):
        raise G3PilotFlightError("G3 runtime must contain five identities per tier")
    if len(set(tiers.values())) != G3_EXPECTED_TIERS or len(derived_ids) != 5:
        raise G3PilotFlightError("G3 runtime must contain eight tiers and five dialogues")
    return G3RuntimeSurface(
        samples=tuple(samples),
        packet_bindings={sample_id: bindings[sample_id] for sample_id in sorted(bindings)},
        tier_by_sample=dict(sorted(tiers.items())),
        derived_dialogue_sample_ids=tuple(sorted(derived_ids)),
        media_identity_by_sample=dict(sorted(media_identity_by_sample.items())),
    )


def select_shuffled_control_ids(
    tier_by_sample: Mapping[str, str],
) -> tuple[str, ...]:
    """Select the preregistered two-per-tier control from identity fields only."""

    by_tier: dict[str, list[str]] = defaultdict(list)
    for sample_id, tier in tier_by_sample.items():
        if not isinstance(sample_id, str) or not sample_id or not isinstance(tier, str):
            raise G3PilotFlightError("shuffled selection requires text identities")
        by_tier[tier].append(sample_id)
    if len(by_tier) != G3_EXPECTED_TIERS or any(len(rows) != 5 for rows in by_tier.values()):
        raise G3PilotFlightError("shuffled selection requires eight five-row tiers")
    selected: list[str] = []
    for tier in sorted(by_tier):
        ranked = sorted(
            by_tier[tier],
            key=lambda sample_id: (
                hashlib.sha256(
                    f"{G3_SHUFFLED_SELECTION_NAMESPACE}\0{sample_id}".encode()
                ).hexdigest(),
                sample_id,
            ),
        )
        selected.extend(ranked[:G3_SHUFFLED_PER_TIER])
    return tuple(selected)


class G3PilotAdapter(TaskAdapter):
    """Scoring-deferred adapter for one fresh G3 phase."""

    def __init__(
        self,
        samples: Sequence[Audio2ToolSample],
        *,
        phase: str,
        registry_contract: str | None = None,
        observation_by_sample: Mapping[str, str] | None = None,
        packet_by_sample: Mapping[str, str] | None = None,
        dialogue_sample_ids: Collection[str] = (),
    ) -> None:
        if phase not in _PHASES:
            raise G3PilotFlightError(f"unknown G3 phase {phase!r}")
        sample_by_id = {sample.sample_id: sample for sample in samples}
        if not sample_by_id or len(sample_by_id) != len(tuple(samples)):
            raise G3PilotFlightError("G3 adapter samples must be nonempty and unique")
        observations = dict(observation_by_sample or {})
        packets = dict(packet_by_sample or {})
        if phase == G3_M0_DIRECT_PHASE:
            if not isinstance(registry_contract, str) or not registry_contract.strip():
                raise G3PilotFlightError("M0 requires the legacy registry contract")
            if observations or packets:
                raise G3PilotFlightError("M0 cannot receive OBS or G3 packet text")
        elif phase == G3_OBSERVATION_PHASE:
            if registry_contract is not None or observations or packets:
                raise G3PilotFlightError("OBS must remain task blind")
        elif set(observations) != set(sample_by_id) or set(packets) != set(sample_by_id):
            raise G3PilotFlightError("USE requires one observation and packet per sample")
        dialogue_ids = frozenset(dialogue_sample_ids)
        if not dialogue_ids.issubset(sample_by_id):
            raise G3PilotFlightError("dialogue observation identities fall outside the phase")
        self._samples = tuple(sorted(sample_by_id.values(), key=lambda item: item.sample_id))
        self._phase = phase
        self._registry_contract = registry_contract
        self._observations = observations
        self._packets = packets
        self._dialogue_ids = dialogue_ids

    @property
    def dialogue_sample_ids(self) -> frozenset[str]:
        """Return media-receipt identities that use the dialogue OBS protocol."""

        return self._dialogue_ids

    def load_split(self, split_id: str) -> tuple[Audio2ToolSample, ...]:
        if split_id != G3_SPLIT_ID:
            raise G3PilotFlightError(f"G3 adapter serves only {G3_SPLIT_ID!r}")
        return self._samples

    def build_task_contract(self, sample: Audio2ToolSample, obs: object) -> str:
        del obs
        if self._phase == G3_M0_DIRECT_PHASE:
            assert self._registry_contract is not None
            return render_audio2tool_instruction(self._registry_contract)
        if self._phase == G3_OBSERVATION_PHASE:
            return (
                _DIALOGUE_OBSERVATION_CONTRACT
                if sample.sample_id in self._dialogue_ids
                else selftx.SELF_TRANSCRIPT_INSTRUCTION
            )
        observation = self._observations[sample.sample_id]
        packet = self._packets[sample.sample_id]
        if not observation.isascii() or not packet.isascii():
            raise G3PilotFlightError("USE observation and packet must be ASCII English")
        return (
            f"{_USE_PREFIX}\n\nTASK-BLIND ENGLISH OBSERVATION\n{observation}\n\n"
            f"G3 PLAIN-ENGLISH KNOWLEDGE PACKET\n{packet}"
        )

    def assemble_prompt(
        self, sample: Audio2ToolSample, supply: object
    ) -> tuple[Mapping[str, object], ...]:
        if supply is not None:
            raise G3PilotFlightError("G3 adapter rejects a second supply channel")
        contract = self.build_task_contract(sample, None)
        return (
            {"role": "system", "content": contract},
            {
                "role": "user",
                "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}],
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
            span_id="g3-final", supply=supply, response_text=response
        )


class G3ObservationController:
    """One OBS contact with a media-identity-conditioned transcript budget."""

    def __init__(self, *, dialogue: bool) -> None:
        self._dialogue = dialogue
        self._delegate = SingleContactController(phase="OBS_SELF_TRANSCRIPT")

    def initial_contact(self, context: AgentRuntimeContext) -> AgentContact:
        contact = self._delegate.initial_contact(context)
        instruction = (
            _DIALOGUE_OBSERVATION_CONTRACT
            if self._dialogue
            else selftx.SELF_TRANSCRIPT_INSTRUCTION
        )
        max_tokens = 768 if self._dialogue else 256
        return replace(
            contact,
            instruction=instruction,
            decoding_params={"max_tokens": max_tokens, "temperature": 0},
        ).validate()

    def advance(
        self,
        context: AgentRuntimeContext,
        contact: AgentContact,
        response_text: AgentResponse,
    ) -> AgentLoopAdvance:
        return self._delegate.advance(context, contact, response_text)


def _summary_texts(summary: object, *, label: str) -> dict[str, str]:
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or not results:
        raise G3PilotFlightError(f"{label} summary must contain tuple results")
    texts: dict[str, str] = {}
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        text = getattr(result, "final_response_text", None)
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(text, str)
            or sample_id in texts
        ):
            raise G3PilotFlightError(f"{label} results are malformed or duplicated")
        texts[sample_id] = text
    return dict(sorted(texts.items()))


def normalize_observation_texts(
    observation_summary: object,
    *,
    dialogue_sample_ids: Collection[str] = (),
    representation_flags: dict[str, dict[str, bool]] | None = None,
) -> dict[str, str]:
    """Return the one ASCII English OBS representation consumed downstream."""

    observations = _summary_texts(observation_summary, label="OBS")
    dialogue_ids = frozenset(dialogue_sample_ids)
    if not dialogue_ids.issubset(observations):
        raise G3PilotFlightError("dialogue OBS identities fall outside the summary")
    normalized_observations: dict[str, str] = {}
    for sample_id, text in observations.items():
        role_labels_missing = False
        normalized_non_ascii = False
        if sample_id in dialogue_ids:
            observation_text = text.strip()
            roles = tuple(
                match.group(1).lower()
                for match in _DIALOGUE_ROLE_LINE.finditer(observation_text)
            )
            if not roles:
                role_labels_missing = True
                normalized = (
                    observation_text.replace("\N{DEGREE SIGN}", " degrees")
                    .replace("\N{EM DASH}", " - ")
                    .replace("\N{RIGHT SINGLE QUOTATION MARK}", "'")
                )
                normalized_non_ascii = normalized != observation_text
                observation_text = normalized
            elif (
                len(roles) < 3
                or roles[0] != "user"
                or roles[-1] != "user"
                or any(left == right for left, right in zip(roles, roles[1:]))
            ):
                raise G3PilotFlightError(
                    f"dialogue OBS lacks alternating role labels for {sample_id!r}"
                )
        else:
            parsed = selftx.validate_self_transcript(text)
            if not parsed.valid:
                raise G3PilotFlightError(
                    f"OBS text is invalid for {sample_id!r}: {parsed.reason}"
                )
            observation_text = parsed.text
        if not observation_text.isascii():
            raise G3PilotFlightError(f"OBS text is not ASCII English for {sample_id!r}")
        if representation_flags is not None:
            representation_flags[sample_id] = {
                "role_labels_missing": role_labels_missing,
                "normalized_non_ascii": normalized_non_ascii,
            }
        normalized_observations[sample_id] = observation_text
    return normalized_observations


def build_packet_routes(
    observation_summary: object,
    *,
    corpus: PlainEnglishCardCorpus,
    detailed_tool_limit: int = MAX_DETAILED_TOOLS,
    dialogue_sample_ids: Collection[str] = (),
    representation_flags: dict[str, dict[str, bool]] | None = None,
    normalized_observation_texts: Mapping[str, str] | None = None,
    retriever: Callable[..., PlainEnglishPacketRoute] = retrieve_plain_english_packets,
) -> dict[str, PlainEnglishPacketRoute]:
    """Build matched and shuffled packets from OBS text alone, without tier hints."""

    if normalized_observation_texts is None:
        observations = normalize_observation_texts(
            observation_summary,
            dialogue_sample_ids=dialogue_sample_ids,
            representation_flags=representation_flags,
        )
    else:
        raw_ids = set(_summary_texts(observation_summary, label="OBS"))
        observations = dict(normalized_observation_texts)
        if set(observations) != raw_ids or any(
            not text or not text.isascii() for text in observations.values()
        ):
            raise G3PilotFlightError("normalized OBS texts are malformed or incomplete")
    routes: dict[str, PlainEnglishPacketRoute] = {}
    for sample_id, observation_text in observations.items():
        routes[sample_id] = retriever(
            observation_text,
            corpus,
            detailed_tool_limit=detailed_tool_limit,
            shuffle_seed=0,
        )
    return routes


def run_g3_m0_phase(
    *,
    adapter: G3PilotAdapter,
    core_client: object,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    slot_count: int,
    decoding_params: Mapping[str, object],
    direct_runner: Callable[..., object] = run_direct_phase,
) -> object:
    """Run the fixed 40-row legacy direct comparator in this flight."""

    summary = direct_runner(
        adapter=adapter,
        core_client=core_client,
        split_id=G3_SPLIT_ID,
        speech_packet_bindings=speech_packet_bindings,
        slot_count=slot_count,
        decoding_params=decoding_params,
    )
    if len(_summary_texts(summary, label="M0")) != G3_EXPECTED_ROWS:
        raise G3PilotFlightError("M0 must return exactly 40 results")
    return summary


def run_g3_agent_phase(
    *,
    phase: str,
    data_root: Path,
    plan: object,
    adapter: G3PilotAdapter,
    core_client: object,
    knowledge_snapshot: object,
    speech_packet_bindings: Mapping[str, Mapping[str, object]],
    trace_sink: object,
    slot_count: int,
    queue_depth: int,
    decoding_params: Mapping[str, object],
    registry_rows: Sequence[Mapping[str, str]] = (),
    agent_runner: Callable[..., object] = run_speech_native_agent_loop,
) -> object:
    """Run one fresh task-blind OBS or hard-validity USE AgentLoop phase."""

    if phase not in {G3_OBSERVATION_PHASE, G3_MATCHED_USE_PHASE, G3_SHUFFLED_USE_PHASE}:
        raise G3PilotFlightError(f"unknown G3 Agent phase {phase!r}")
    controller_registry = Registry("A2T G3 pilot controller")
    if phase == G3_OBSERVATION_PHASE:
        controller_policy_id = _OBS_POLICY_ID
        max_contacts = 1
        controller_registry.register(
            controller_policy_id,
            lambda sample_id: G3ObservationController(
                dialogue=sample_id in adapter.dialogue_sample_ids
            ),
        )
    else:
        if not registry_rows:
            raise G3PilotFlightError("G3 USE requires public registry rows for repair")
        # WAVE R7 (2026-09-08): the retired HardValidityRepairController's
        # sequencing is now the registered ``phase-hard-validity-repair-v1``
        # program on rails.controllers.EvidenceAgentController. Same two
        # contact ids, same two instructions, same sealed validity report, same
        # early exit on a valid draft, same declared arm identity; what changed
        # is that the phase index -- not a hard-coded QueryState.loop_step --
        # says which phase is running. ``decoding_params`` are handed to the
        # runner only: it already merges the run-level mapping into every plan,
        # and this flight passes the SAME mapping to both.
        controller_policy_id = HARD_VALIDITY_PROGRAM_ID
        max_contacts = 2
        matcher_policy_id = (
            _MATCHED_POLICY_ID
            if phase == G3_MATCHED_USE_PHASE
            else _SHUFFLED_POLICY_ID
        )
        controller_registry.register(
            controller_policy_id,
            make_hard_validity_phase_controller(
                registry_rows=registry_rows,
                key_representation_id=_USE_KEY_REPRESENTATION_ID,
                matcher_policy_id=matcher_policy_id,
                decoding_params={},
            ),
        )
    summary = agent_runner(
        data_root=data_root,
        plan=plan,
        adapter=adapter,
        core_client=core_client,
        split_id=G3_SPLIT_ID,
        knowledge_snapshot=knowledge_snapshot,
        speech_packet_bindings=speech_packet_bindings,
        controller_policy_id=controller_policy_id,
        bootstrap_facet_ids=(),
        bootstrap_value_ids=(),
        max_contacts=max_contacts,
        slot_count=slot_count,
        queue_depth=queue_depth,
        trace_sink=trace_sink,
        agent_executor_id=AGENT_EXECUTOR_ID,
        decoding_params=decoding_params,
        controller_registry=controller_registry,
    )
    if getattr(summary, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise G3PilotFlightError("G3 phase is not bound to OpenJiuwen")
    results = getattr(summary, "results", None)
    expected_count = (
        G3_EXPECTED_SHUFFLED_ROWS
        if phase == G3_SHUFFLED_USE_PHASE
        else G3_EXPECTED_ROWS
    )
    if not isinstance(results, tuple) or len(results) != expected_count:
        raise G3PilotFlightError(
            f"{phase} must return exactly {expected_count} results"
        )
    result_ids: list[str] = []
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        contacts = getattr(result, "contacts", None)
        if (
            not isinstance(sample_id, str)
            or not isinstance(contacts, tuple)
            or not 1 <= len(contacts) <= max_contacts
        ):
            raise G3PilotFlightError(f"{phase} result or contact count is malformed")
        result_ids.append(sample_id)
    if len(set(result_ids)) != len(result_ids) or set(result_ids) != set(
        speech_packet_bindings
    ):
        raise G3PilotFlightError(f"{phase} result and speech identities disagree")
    return summary


def build_complete_arm_texts(
    *,
    m0_summary: object,
    matched_summary: object,
    shuffled_summary: object,
    shuffled_ids: Sequence[str],
) -> G3CompleteArmTexts:
    """Compose complete scorer surfaces with existing bundle primitives."""

    m0 = _summary_texts(m0_summary, label="M0")
    matched_use = _summary_texts(matched_summary, label="matched USE")
    shuffled_use = _summary_texts(shuffled_summary, label="shuffled USE")
    if len(m0) != G3_EXPECTED_ROWS or len(matched_use) != G3_EXPECTED_ROWS:
        raise G3PilotFlightError("M0 and matched USE must each contain 40 rows")
    matched = build_use_composite_texts(
        m0_texts=m0,
        use_texts=matched_use,
        routed_ids=tuple(matched_use),
    )
    shuffled = build_resend_composite_texts(
        matched,
        selected_ids=shuffled_ids,
        resend_responses=shuffled_use,
    )
    return G3CompleteArmTexts(m0=m0, matched=matched, shuffled=shuffled)


def build_g3_m0_bundle_material(
    summary: object,
    trace_documents: Sequence[Mapping[str, object]],
    *,
    umbrella_lock_sha256: str,
) -> tuple[tuple[dict[str, object], ...], dict[str, object]]:
    """Convert the direct phase through the existing bundle materializer."""

    return build_phase_bundle_material(
        summary,
        trace_documents,
        phase="M0_DIRECT",
        umbrella_lock_sha256=umbrella_lock_sha256,
    )


def emit_g3_use_rows(
    *,
    texts: Mapping[str, str],
    source_by_id: Mapping[str, Mapping[str, str]],
    sink: object,
    phase: str,
    emitter: Callable[..., tuple[dict[str, object], ...]] = emit_composite_rows,
) -> tuple[dict[str, object], ...]:
    """Emit matched or shuffled complete rows in the existing scorer shape."""

    variants = {
        G3_MATCHED_USE_PHASE: "matched",
        G3_SHUFFLED_USE_PHASE: "shuffled-evidence",
    }
    try:
        variant = variants[phase]
    except KeyError:
        raise G3PilotFlightError("G3 composite rows require a USE phase") from None
    return emitter(
        texts=texts,
        source_by_id=source_by_id,
        sink=sink,
        variant=variant,
    )


__all__ = [
    "G3_MATCHED_USE_PHASE",
    "G3_M0_DIRECT_PHASE",
    "G3_OBSERVATION_PHASE",
    "G3_SHUFFLED_SELECTION_NAMESPACE",
    "G3_SHUFFLED_USE_PHASE",
    "G3_SPLIT_ID",
    "G3CompleteArmTexts",
    "G3PilotAdapter",
    "G3PilotFlightError",
    "G3ObservationController",
    "G3RuntimeSurface",
    "build_complete_arm_texts",
    "build_g3_m0_bundle_material",
    "build_packet_routes",
    "emit_g3_use_rows",
    "resolve_g3_runtime_media",
    "run_g3_agent_phase",
    "run_g3_m0_phase",
    "select_shuffled_control_ids",
    "normalize_observation_texts",
]
