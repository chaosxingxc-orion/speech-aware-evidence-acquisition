"""Fail-closed coordinator for the fresh 104-row SELECT/FILL experiment.

This module does not author contact authority and its default command never
contacts a service.  An authority-bound runtime supplies exact phase request
material, OpenJiuwen execution, parsing, tracing, and manifest persistence.
The coordinator owns the immutable schedule, whole-phase request admission,
cross-workflow barriers, and contact accounting.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
from threading import Lock


REPO = Path(__file__).resolve().parents[5]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speech_aware_evidence_acquisition.rails.a2t_stage_state import (  # noqa: E402
    JOINT_DRAFT_STAGE,
    SELECT_STAGE,
    JointDraftPayload,
    SelectPayload,
    StageStateEnvelope,
)
from speech_aware_evidence_acquisition.rails.context_budget import (  # noqa: E402
    REGISTERED_SPECIAL_TOKEN_RESERVE,
)


CHECK_DIR = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-agentloop-104-v1"
)
LOCAL_RUNTIME_FACTORY_PATH = CHECK_DIR / "launcher/local_runtime_factory.py"
ROSTER_PATH = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-fresh-roster-v1/flight-roster-receipt.json"
)
ROSTER_SHA256 = "dea74114430ed5e45e29d908dc2ecebf41788edfa2704435a2966f260de5bc4f"
SPLIT_ID = "A2T-SELECT-FILL-FRESH-FLIGHT"
SPLIT_IDENTITY_HASH = "bcbad5405aa8522ff53a91d624c54a909e01f8a31612b5165844b8e2cbca6eb3"
BUNDLE_SPLIT_IDENTITY_HASH = (
    "122da6752c7c4011c2f632cee4e737899bfbb451501666fb47aa0676f372d2c8"
)
BUNDLE_PROTOCOL_SHA256 = (
    "4f192381d41c96b55d53433035ff0566795b0fb772503a59555a0f83d15d1171"
)
SOURCE_RUN_ID = "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V2"
RUN_ID = "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5"
PREPROCESS_REPORT_PATH = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-select-fill-fresh-preprocess-v1/preprocess-report.json"
)
PREPROCESS_REPORT_SHA256 = (
    "bc1794eb2805bd65a96bb78cd7bf2b70dd4ce0e71d0cc0887a86d77d7727cf6d"
)
PROMOTED_PACKET_ROOT = Path(
    "/home/chao/feat-cache/"
    "a2t-semantic-agentloop-select-fill-v1-packets-04ccc72a"
)
PROMOTION_RECEIPT_PATH = PROMOTED_PACKET_ROOT / (
    "A2T-SEMANTIC-AGENTLOOP-SELECT-FILL-104-V1-promotion.json"
)
PROMOTION_RECEIPT_SHA256 = (
    "1f7411359311a012c5162ee5472ef767d055a66521f2b12b4da267d1f0660e07"
)

M0_PHASE = "M0_DIRECT"
OBS_PHASE = "OBS_SEMANTIC_STATE"
EMBEDDING_PHASE = "EMBED_OBS_TRANSCRIPT"
JOINT_PHASE = "JOINT_ONE_CALL"
SELECT_PHASE = "SELECT"
REVISE_PHASE = "JOINT_DRAFT_REVISE"
FILL_PHASE = "FILL"
PHASE_ORDER = (
    M0_PHASE,
    OBS_PHASE,
    EMBEDDING_PHASE,
    JOINT_PHASE,
    SELECT_PHASE,
    REVISE_PHASE,
    FILL_PHASE,
)
REUSED_GENERATION_PHASES = (
    M0_PHASE,
    OBS_PHASE,
)
GENERATION_PHASES = (
    JOINT_PHASE,
    SELECT_PHASE,
    REVISE_PHASE,
    FILL_PHASE,
)
ALL_GENERATION_PHASES = REUSED_GENERATION_PHASES + GENERATION_PHASES
FINAL_MANIFEST_ROLES = (
    "direct_m0",
    "joint_one_call",
    "joint_draft_revise",
    "select_then_fill",
)
DIAGNOSTIC_PHASES = (OBS_PHASE, SELECT_PHASE)

SAMPLE_COUNT = 104
GENERATION_CONTACTS = SAMPLE_COUNT * len(GENERATION_PHASES)
FULL_FLIGHT_GENERATION_CONTACTS = SAMPLE_COUNT * len(ALL_GENERATION_PHASES)
EMBEDDING_LOGICAL_ITEMS = SAMPLE_COUNT
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_PHYSICAL_REQUESTS = math.ceil(
    EMBEDDING_LOGICAL_ITEMS / EMBEDDING_BATCH_SIZE
)
TOP_K = 32
SLOT_COUNT = 2
QUEUE_DEPTH = 4
PHYSICAL_CONTEXT_PER_SLOT = 32_768
CONTEXT_RESERVE = 8_192
MAX_REQUIRED_WINDOW_TOKENS = PHYSICAL_CONTEXT_PER_SLOT - CONTEXT_RESERVE
CHAT_ENDPOINT = "/v1/chat/completions"
PROPS_ENDPOINT = "/props"
APPLY_TEMPLATE_ENDPOINT = "/apply-template"
TOKENIZE_ENDPOINT = "/tokenize"
AGENT_EXECUTOR_ID = "openjiuwen-workflow-v1"

_SHA256 = re.compile(r"[0-9a-f]{64}", flags=re.ASCII)
_GENERATION_PHASE_SET = frozenset(ALL_GENERATION_PHASES)
_FORBIDDEN_VISIBLE_KEYS = frozenset(
    {"gold", "label", "reference", "annotation", "future_turn", "test_answer"}
)


def canonical_json_bytes(value: object) -> bytes:
    """Return the flight's sole canonical JSON representation."""

    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError, UnicodeEncodeError) as error:
        raise RuntimeError("flight material must be canonical ASCII JSON") from error


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _require_sha256(value: object, *, label: str) -> str:
    if not _is_sha256(value):
        raise RuntimeError(f"{label} must be a lowercase SHA-256")
    return str(value)


def protocol_config() -> dict[str, object]:
    """Return the fully mechanical experiment and transport contract."""

    return {
        "schema": "saea-a2t-select-fill-agentloop-config-v1",
        "run_id": RUN_ID,
        "split_id": SPLIT_ID,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "roster_sha256": ROSTER_SHA256,
        "preprocess_report_sha256": PREPROCESS_REPORT_SHA256,
        "promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
        "phase_order": list(PHASE_ORDER),
        "generation_phases": list(GENERATION_PHASES),
        "reused_generation_phases": list(REUSED_GENERATION_PHASES),
        "generation_contacts": GENERATION_CONTACTS,
        "inherited_generation_contacts": SAMPLE_COUNT * len(REUSED_GENERATION_PHASES),
        "full_flight_generation_contacts": FULL_FLIGHT_GENERATION_CONTACTS,
        "manifest_roles": list(FINAL_MANIFEST_ROLES),
        "diagnostic_phases": list(DIAGNOSTIC_PHASES),
        "retrieval": {
            "query": "canonical OBS transcript only",
            "top_k": TOP_K,
            "logical_embedding_items": EMBEDDING_LOGICAL_ITEMS,
            "embedding_batch_size": EMBEDDING_BATCH_SIZE,
            "embedding_physical_requests": EMBEDDING_PHYSICAL_REQUESTS,
        },
        "generation": {
            "agent_executor_id": AGENT_EXECUTOR_ID,
            "slot_count": SLOT_COUNT,
            "queue_depth": QUEUE_DEPTH,
            "request_batch_size": 1,
            "retry": False,
            "repair": False,
            "fallback": False,
            "physical_context_per_slot": PHYSICAL_CONTEXT_PER_SLOT,
            "maximum_required_window_tokens": MAX_REQUIRED_WINDOW_TOKENS,
            "context_reserve": CONTEXT_RESERVE,
            "registered_special_token_reserve": REGISTERED_SPECIAL_TOKEN_RESERVE,
            "whole_phase_exact_preflight": True,
            "slot_body_hash_variants": [0, 1],
        },
        "state": {
            "joint_draft_generated_once": True,
            "joint_draft_raw_history_forwarded": False,
            "select_and_joint_barriers_before_second_stage": True,
            "fill_ground_scope": "selected-only-parameter",
        },
        "scoring": {
            "complete_manifests": 4,
            "official_scorer_in_flight": False,
        },
    }


CONFIG_SHA256 = sha256_json(protocol_config())


@dataclass(frozen=True)
class ObservationArtifact:
    """Canonical OBS state used by transcript retrieval and later workflows."""

    sample_id: str
    transcript: str
    state_sha256: str
    source_response_sha256: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.sample_id, str)
            or not self.sample_id
            or not self.sample_id.isascii()
            or not isinstance(self.transcript, str)
            or not self.transcript
            or not self.transcript.isascii()
        ):
            raise RuntimeError("OBS artifact must contain non-empty ASCII identity and transcript")
        _require_sha256(self.state_sha256, label="OBS state hash")
        _require_sha256(self.source_response_sha256, label="OBS response hash")


@dataclass(frozen=True)
class CandidateSet:
    """Ordered local dense K=32 retrieval result for one OBS transcript."""

    sample_id: str
    tool_names: tuple[str, ...]
    scores: tuple[float, ...]
    query_state_sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.sample_id, str) or not self.sample_id.isascii():
            raise RuntimeError("candidate set sample identity is malformed")
        if (
            not isinstance(self.tool_names, tuple)
            or len(self.tool_names) != TOP_K
            or len(set(self.tool_names)) != TOP_K
            or any(
                not isinstance(name, str) or not name or not name.isascii()
                for name in self.tool_names
            )
        ):
            raise RuntimeError("candidate set must contain 32 unique ASCII tool names")
        if (
            not isinstance(self.scores, tuple)
            or len(self.scores) != TOP_K
            or any(
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(float(score))
                for score in self.scores
            )
        ):
            raise RuntimeError("candidate set must carry 32 finite dense scores")
        _require_sha256(self.query_state_sha256, label="candidate query state hash")

    @property
    def candidate_set_sha256(self) -> str:
        return sha256_json(
            {
                "sample_id": self.sample_id,
                "tool_names": list(self.tool_names),
                "scores": list(self.scores),
                "query_state_sha256": self.query_state_sha256,
            }
        )

    @property
    def candidate_order_sha256(self) -> str:
        """Return the names-only hash required by StageStateEnvelope v2."""

        return sha256_json(list(self.tool_names))


@dataclass(frozen=True)
class PreparedGenerationRequest:
    """One physical llama.cpp body with both permitted slot encodings.

    ``body`` is the body after the transport has assembled messages and
    flattened every decoding parameter.  An adapter-level rails envelope or
    an abstract renderer body is not an admissible substitute.
    """

    phase: str
    sample_id: str
    packet_id: str
    packet_sha256: str
    system_ground_sha256: str
    base_body_json: str
    body_bytes_by_slot: tuple[bytes, bytes]
    body_sha256_by_slot: tuple[str, str]
    ground_sha256: str | None = None

    @classmethod
    def from_body(
        cls,
        *,
        phase: str,
        sample_id: str,
        packet_id: str,
        body: Mapping[str, object],
        ground_sha256: str | None = None,
    ) -> "PreparedGenerationRequest":
        if phase not in _GENERATION_PHASE_SET:
            raise RuntimeError("prepared request phase is not registered")
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not sample_id.isascii()
            or not isinstance(packet_id, str)
            or not packet_id
            or not packet_id.isascii()
        ):
            raise RuntimeError("prepared request identities must be non-empty ASCII")
        copied = dict(body)
        if phase in {JOINT_PHASE, SELECT_PHASE, REVISE_PHASE, FILL_PHASE}:
            _require_sha256(ground_sha256, label="prepared request ground hash")
        elif ground_sha256 is not None:
            _require_sha256(ground_sha256, label="prepared request ground hash")
        messages = copied.get("messages")
        system_text = (
            messages[0].get("content")
            if isinstance(messages, Sequence)
            and not isinstance(messages, (str, bytes))
            and messages
            and isinstance(messages[0], Mapping)
            and messages[0].get("role") == "system"
            else None
        )
        if not isinstance(system_text, str) or not system_text or not system_text.isascii():
            raise RuntimeError("physical generation body lacks ASCII system ground")
        descriptors: list[Mapping[str, object]] = []
        for message in messages:
            content = message.get("content") if isinstance(message, Mapping) else None
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, Mapping) and part.get("type") == "input_speech_features":
                    descriptor = part.get("speech_features")
                    if isinstance(descriptor, Mapping):
                        descriptors.append(descriptor)
        if (
            len(descriptors) != 1
            or set(descriptors[0]) != {"packet_id", "sha256", "role"}
            or descriptors[0].get("packet_id") != packet_id
            or descriptors[0].get("role") != "query"
            or not _is_sha256(descriptors[0].get("sha256"))
        ):
            raise RuntimeError("physical generation body packet binding is malformed")
        system_ground_sha256 = hashlib.sha256(system_text.encode("ascii")).hexdigest()
        if ground_sha256 is not None and system_ground_sha256 != ground_sha256:
            raise RuntimeError("physical system ground differs from its bound hash")
        if "id_slot" in copied:
            raise RuntimeError("request template must not preselect a generation slot")
        try:
            # FrozenCoreAdapter canonicalizes and decodes its full payload
            # before LlamaServerTransport rebuilds the message list.  That
            # round trip sorts decoding/schema keys and speech-descriptor
            # keys; the final HTTP body is then stdlib json.dumps output in
            # insertion order.  Reproduce both steps exactly here.
            normalized_messages: list[dict[str, object]] = []
            for message in messages:
                assert isinstance(message, Mapping)
                content = message.get("content")
                if isinstance(content, list):
                    normalized_content: object = []
                    for part in content:
                        assert isinstance(part, Mapping)
                        normalized_part = dict(part)
                        descriptor = normalized_part.get("speech_features")
                        if normalized_part.get("type") == "input_speech_features":
                            assert isinstance(descriptor, Mapping)
                            normalized_part["speech_features"] = json.loads(
                                canonical_json_bytes(descriptor)
                            )
                        normalized_content.append(normalized_part)
                else:
                    normalized_content = content
                normalized_messages.append(
                    {"role": message.get("role"), "content": normalized_content}
                )
            decoding = {
                key: value for key, value in copied.items() if key != "messages"
            }
            normalized_decoding = json.loads(canonical_json_bytes(decoding))
            base_body: dict[str, object] = {"messages": normalized_messages}
            base_body.update(normalized_decoding)
            base = json.dumps(base_body).encode("utf-8").decode("ascii")
            bodies_list: list[bytes] = []
            for slot in range(SLOT_COUNT):
                slot_decoding = {**decoding, "id_slot": slot}
                normalized_slot_decoding = json.loads(
                    canonical_json_bytes(slot_decoding)
                )
                physical: dict[str, object] = {"messages": normalized_messages}
                physical.update(normalized_slot_decoding)
                bodies_list.append(json.dumps(physical).encode("utf-8"))
        except (TypeError, UnicodeDecodeError, UnicodeEncodeError) as error:
            raise RuntimeError("physical generation body must be ASCII JSON") from error
        bodies = tuple(bodies_list)
        hashes = tuple(hashlib.sha256(item).hexdigest() for item in bodies)
        return cls(
            phase=phase,
            sample_id=sample_id,
            packet_id=packet_id,
            packet_sha256=str(descriptors[0]["sha256"]),
            system_ground_sha256=system_ground_sha256,
            base_body_json=base,
            body_bytes_by_slot=(bodies[0], bodies[1]),
            body_sha256_by_slot=(hashes[0], hashes[1]),
            ground_sha256=ground_sha256,
        )

    @property
    def base_body(self) -> Mapping[str, object]:
        value = json.loads(self.base_body_json)
        if not isinstance(value, Mapping):  # pragma: no cover - constructor invariant
            raise AssertionError("prepared request body must remain an object")
        return value


@dataclass(frozen=True)
class PromptBudgetAudit:
    """Exact pre-generation measurement for one prepared request."""

    sample_id: str
    phase: str
    prompt_sha256: str
    response_format_sha256: str | None
    measured_text_tokens: int
    speech_feature_tokens: int
    completion_token_ceiling: int
    required_window_tokens: int

    def __post_init__(self) -> None:
        if self.phase not in _GENERATION_PHASE_SET:
            raise RuntimeError("prompt audit phase is not registered")
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise RuntimeError("prompt audit sample identity is missing")
        _require_sha256(self.prompt_sha256, label="prompt hash")
        if self.response_format_sha256 is not None:
            _require_sha256(self.response_format_sha256, label="response-format hash")
        counts = (
            self.measured_text_tokens,
            self.speech_feature_tokens,
            self.completion_token_ceiling,
            self.required_window_tokens,
        )
        if any(isinstance(value, bool) or not isinstance(value, int) or value <= 0 for value in counts):
            raise RuntimeError("prompt audit token counts must be positive integers")
        if self.required_window_tokens > MAX_REQUIRED_WINDOW_TOKENS:
            raise RuntimeError("prompt audit exceeds the operational context cap")


@dataclass(frozen=True)
class PhaseRequestPreflightReceipt:
    """Atomic admission receipt created only after every row passes."""

    phase: str
    sample_ids: tuple[str, ...]
    allowed_body_hashes_by_slot: tuple[tuple[str, ...], tuple[str, ...]]
    audits: tuple[PromptBudgetAudit, ...]
    receipt_sha256: str
    status: str = "COMPLETE_NO_GENERATION_SENT"

    @classmethod
    def create(
        cls,
        phase: str,
        requests: Sequence[PreparedGenerationRequest],
        audits: Sequence[PromptBudgetAudit],
    ) -> "PhaseRequestPreflightReceipt":
        prepared = tuple(requests)
        measured = tuple(audits)
        if phase not in _GENERATION_PHASE_SET:
            raise RuntimeError("preflight phase is not registered")
        if len(prepared) != SAMPLE_COUNT or len(measured) != SAMPLE_COUNT:
            raise RuntimeError("phase preflight requires exactly 104 requests and audits")
        sample_ids = tuple(item.sample_id for item in prepared)
        if len(set(sample_ids)) != SAMPLE_COUNT:
            raise RuntimeError("phase preflight sample identities are duplicate")
        if any(item.phase != phase for item in prepared) or tuple(
            item.sample_id for item in measured
        ) != sample_ids or any(item.phase != phase for item in measured):
            raise RuntimeError("phase preflight request or audit binding drift")
        allowlist = tuple(
            tuple(request.body_sha256_by_slot[slot] for request in prepared)
            for slot in range(SLOT_COUNT)
        )
        body = {
            "schema": "saea-a2t-whole-phase-request-preflight-v1",
            "status": "COMPLETE_NO_GENERATION_SENT",
            "phase": phase,
            "sample_ids": list(sample_ids),
            "allowed_body_hashes_by_slot": [list(row) for row in allowlist],
            "audits": [audit.__dict__ for audit in measured],
        }
        return cls(
            phase=phase,
            sample_ids=sample_ids,
            allowed_body_hashes_by_slot=(allowlist[0], allowlist[1]),
            audits=measured,
            receipt_sha256=sha256_json(body),
        )

    @property
    def row_count(self) -> int:
        return len(self.sample_ids)


@dataclass(frozen=True)
class GenerationResponse:
    """Raw bytes from one admitted, single-sample generation request."""

    sample_id: str
    phase: str
    request_body_sha256: str
    response_bytes: bytes
    source_query_state_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.phase not in _GENERATION_PHASE_SET:
            raise RuntimeError("generation response phase is not registered")
        if not isinstance(self.sample_id, str) or not self.sample_id:
            raise RuntimeError("generation response sample identity is missing")
        _require_sha256(self.request_body_sha256, label="request body hash")
        if self.source_query_state_sha256 is not None:
            _require_sha256(
                self.source_query_state_sha256,
                label="producing query-state hash",
            )
        if not isinstance(self.response_bytes, bytes) or not self.response_bytes:
            raise RuntimeError("generation response bytes are empty")
        try:
            self.response_bytes.decode("ascii")
        except UnicodeDecodeError as error:
            raise RuntimeError("generation response must be ASCII before reuse") from error

    @property
    def response_sha256(self) -> str:
        return hashlib.sha256(self.response_bytes).hexdigest()


@dataclass(frozen=True)
class GenerationPhaseOutput:
    phase: str
    rows: tuple[GenerationResponse, ...]

    def __post_init__(self) -> None:
        if self.phase not in _GENERATION_PHASE_SET:
            raise RuntimeError("generation output phase is not registered")
        if not isinstance(self.rows, tuple) or len(self.rows) != SAMPLE_COUNT:
            raise RuntimeError("generation phase must contain exactly 104 responses")
        identities = tuple(row.sample_id for row in self.rows)
        if (
            any(row.phase != self.phase for row in self.rows)
            or len(set(identities)) != SAMPLE_COUNT
        ):
            raise RuntimeError("generation phase response identities are invalid")


@dataclass(frozen=True)
class GenerationPhaseRun:
    phase: str
    requests: tuple[PreparedGenerationRequest, ...]
    preflight: PhaseRequestPreflightReceipt
    output: GenerationPhaseOutput


@dataclass(frozen=True)
class RecoveredPrefixArtifacts:
    """Hash-verified V2 M0/OBS artifacts admitted without new generation."""

    m0: GenerationPhaseRun
    obs: GenerationPhaseRun
    observations: Mapping[str, ObservationArtifact]
    source_report_sha256: str

    def __post_init__(self) -> None:
        _require_sha256(self.source_report_sha256, label="source recovery report hash")
        if self.m0.phase != M0_PHASE or self.obs.phase != OBS_PHASE:
            raise RuntimeError("recovered prefix phases are malformed")
        sample_ids = tuple(row.sample_id for row in self.m0.output.rows)
        if (
            tuple(row.sample_id for row in self.obs.output.rows) != sample_ids
            or set(self.observations) != set(sample_ids)
            or any(
                self.observations[sample_id].sample_id != sample_id
                for sample_id in sample_ids
            )
        ):
            raise RuntimeError("recovered prefix roster or OBS lineage drift")


def _walk_visible(value: object, *, path: str = "body") -> None:
    if isinstance(value, str):
        if not value.isascii():
            raise RuntimeError(f"{path} contains non-ASCII model-visible text")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _walk_visible(item, path=f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str) or not key.isascii():
                raise RuntimeError(f"{path} contains a non-ASCII key")
            if key.casefold() in _FORBIDDEN_VISIBLE_KEYS:
                raise RuntimeError(f"{path} contains forbidden runtime field {key!r}")
            if key == "properties" and isinstance(item, Mapping):
                for field_name, field_schema in item.items():
                    if not isinstance(field_name, str) or not field_name.isascii():
                        raise RuntimeError(
                            f"{path}.properties contains a non-ASCII field name"
                        )
                    _walk_visible(
                        field_schema,
                        path=f"{path}.properties[{field_name!r}]",
                    )
                continue
            _walk_visible(item, path=f"{path}.{key}")


def _inspect_request(
    request: PreparedGenerationRequest,
    *,
    expected_phase: str,
) -> tuple[Mapping[str, object], list[object], Mapping[str, object] | None, int]:
    if request.phase != expected_phase:
        raise RuntimeError("prepared request phase binding drift")
    body = request.base_body
    _walk_visible(body)
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages or any(
        isinstance(message, list) for message in messages
    ):
        raise RuntimeError("generation request requires one unbatched message sequence")
    if body.get("n", 1) != 1 or body.get("best_of", 1) != 1:
        raise RuntimeError("generation request requires n=1 and best_of=1")
    max_tokens = body.get("max_tokens")
    if isinstance(max_tokens, bool) or not isinstance(max_tokens, int) or max_tokens <= 0:
        raise RuntimeError("generation request requires a positive max_tokens")
    response_format = body.get("response_format")
    if response_format is None and expected_phase != M0_PHASE:
        raise RuntimeError("structured phase request requires response_format")
    if response_format is not None:
        if (
            not isinstance(response_format, Mapping)
            or response_format.get("type") != "json_schema"
            or not isinstance(response_format.get("json_schema"), Mapping)
            or response_format["json_schema"].get("strict") is not True  # type: ignore[index]
            or not isinstance(response_format["json_schema"].get("schema"), Mapping)  # type: ignore[index]
        ):
            raise RuntimeError("response_format must be one strict JSON schema")
    packet_ids: list[str] = []
    packet_hashes: list[str] = []
    for message in messages:
        if not isinstance(message, Mapping):
            raise RuntimeError("generation messages must contain objects")
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, Mapping) or part.get("type") != "input_speech_features":
                continue
            descriptor = part.get("speech_features")
            packet_id = descriptor.get("packet_id") if isinstance(descriptor, Mapping) else None
            packet_sha = descriptor.get("sha256") if isinstance(descriptor, Mapping) else None
            role = descriptor.get("role") if isinstance(descriptor, Mapping) else None
            if (
                not isinstance(packet_id, str)
                or not _is_sha256(packet_sha)
                or role != "query"
                or set(descriptor) != {"packet_id", "sha256", "role"}
            ):
                raise RuntimeError("speech packet identity is malformed")
            packet_ids.append(packet_id)
            packet_hashes.append(str(packet_sha))
    system_text = (
        messages[0].get("content")
        if isinstance(messages[0], Mapping) and messages[0].get("role") == "system"
        else None
    )
    if (
        packet_ids != [request.packet_id]
        or packet_hashes != [request.packet_sha256]
        or not isinstance(system_text, str)
        or hashlib.sha256(system_text.encode("ascii")).hexdigest()
        != request.system_ground_sha256
        or (
            request.ground_sha256 is not None
            and request.system_ground_sha256 != request.ground_sha256
        )
    ):
        raise RuntimeError("request must contain exactly its one bound speech packet")
    for slot, encoded in enumerate(request.body_bytes_by_slot):
        slot_body = json.loads(encoded)
        if slot_body != {**body, "id_slot": slot}:
            raise RuntimeError("prepared slot body differs from the exact base request")
        if hashlib.sha256(encoded).hexdigest() != request.body_sha256_by_slot[slot]:
            raise RuntimeError("prepared slot body hash drift")
    return body, messages, response_format, max_tokens


def _matches_json_type(value: object, expected: object) -> bool:
    kinds = (expected,) if isinstance(expected, str) else tuple(expected or ())
    for kind in kinds:
        if kind == "null" and value is None:
            return True
        if kind == "boolean" and isinstance(value, bool):
            return True
        if kind == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if kind == "number" and isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if kind == "string" and isinstance(value, str):
            return True
        if kind == "array" and isinstance(value, list):
            return True
        if kind == "object" and isinstance(value, dict):
            return True
    return False


def _validate_json_schema(value: object, schema: object, *, path: str = "$") -> None:
    """Validate the strict schema subset emitted by the Audio2Tool builders."""

    if not isinstance(schema, Mapping):
        raise RuntimeError(f"response schema at {path} is not an object")
    if "const" in schema and value != schema["const"]:
        raise RuntimeError(f"response at {path} differs from schema const")
    enum = schema.get("enum")
    if enum is not None and (not isinstance(enum, list) or value not in enum):
        raise RuntimeError(f"response at {path} is outside schema enum")
    one_of = schema.get("oneOf")
    if one_of is not None:
        if not isinstance(one_of, list) or not one_of:
            raise RuntimeError(f"response schema oneOf at {path} is malformed")
        matches = 0
        for branch in one_of:
            try:
                _validate_json_schema(value, branch, path=path)
            except RuntimeError:
                continue
            matches += 1
        if matches != 1:
            raise RuntimeError(f"response at {path} must match exactly one schema branch")
        return
    expected_type = schema.get("type")
    if expected_type is not None and not _matches_json_type(value, expected_type):
        raise RuntimeError(f"response at {path} has the wrong JSON type")
    if isinstance(value, float) and not math.isfinite(value):
        raise RuntimeError(f"response at {path} contains a non-finite number")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise RuntimeError(f"response at {path} is below schema minimum")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise RuntimeError(f"response at {path} is above schema maximum")
    if isinstance(value, list):
        minimum = schema.get("minItems")
        maximum = schema.get("maxItems")
        if isinstance(minimum, int) and len(value) < minimum:
            raise RuntimeError(f"response at {path} has too few array items")
        if isinstance(maximum, int) and len(value) > maximum:
            raise RuntimeError(f"response at {path} has too many array items")
        prefix = schema.get("prefixItems")
        if prefix is not None:
            if not isinstance(prefix, list) or len(value) != len(prefix):
                raise RuntimeError(f"response at {path} differs from locked positions")
            for index, (item, item_schema) in enumerate(zip(value, prefix, strict=True)):
                _validate_json_schema(item, item_schema, path=f"{path}[{index}]")
        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                _validate_json_schema(item, item_schema, path=f"{path}[{index}]")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, Mapping) or not isinstance(required, list):
            raise RuntimeError(f"response object schema at {path} is malformed")
        if any(key not in value for key in required):
            raise RuntimeError(f"response at {path} omits a required property")
        if schema.get("additionalProperties") is False and not set(value).issubset(properties):
            raise RuntimeError(f"response at {path} contains an additional property")
        for key, item in value.items():
            if key in properties:
                _validate_json_schema(item, properties[key], path=f"{path}.{key}")


def validate_response_against_request(
    response_bytes: bytes, request: PreparedGenerationRequest
) -> None:
    """Revalidate assistant JSON and every argument after model response."""

    if request.phase == M0_PHASE:
        return
    try:
        text = response_bytes.decode("ascii")
        value = json.loads(
            text,
            object_pairs_hook=lambda pairs: _unique_json_object(pairs),
            parse_constant=lambda raw: (_raise_nonfinite(raw)),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("structured response is not exact ASCII JSON") from error
    response_format = request.base_body.get("response_format")
    wrapper = (
        response_format.get("json_schema")
        if isinstance(response_format, Mapping)
        else None
    )
    schema = wrapper.get("schema") if isinstance(wrapper, Mapping) else None
    _validate_json_schema(value, schema)


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuntimeError(f"structured response repeats JSON key {key!r}")
        result[key] = value
    return result


def _raise_nonfinite(value: str) -> object:
    raise RuntimeError(f"structured response contains non-finite value {value!r}")


def _extract_chat_response_text(raw: bytes) -> bytes:
    try:
        document = json.loads(raw.decode("utf-8"))
        text = document["choices"][0]["message"]["content"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as error:
        raise RuntimeError("chat endpoint returned a malformed response") from error
    if not isinstance(text, str) or not text or not text.isascii():
        raise RuntimeError("chat endpoint response text must be non-empty ASCII")
    return text.encode("ascii")


class WholePhaseRequestGate:
    """Preflight 104 exact bodies, then admit only their two slot variants."""

    def __init__(
        self,
        *,
        expected_sample_ids: Sequence[str],
        speech_packet_tokens: Mapping[str, int],
        get_json: Callable[[str], object],
        post_json: Callable[[str, Mapping[str, object]], object],
        send: Callable[[str, bytes], bytes],
    ) -> None:
        self._expected_sample_ids = tuple(expected_sample_ids)
        if (
            len(self._expected_sample_ids) != SAMPLE_COUNT
            or len(set(self._expected_sample_ids)) != SAMPLE_COUNT
        ):
            raise RuntimeError("whole-phase gate requires 104 unique sample identities")
        if (
            not isinstance(speech_packet_tokens, Mapping)
            or any(
                not isinstance(key, str)
                or not key
                or isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
                for key, value in speech_packet_tokens.items()
            )
        ):
            raise RuntimeError("whole-phase gate requires positive speech-token counts")
        if not callable(get_json) or not callable(post_json) or not callable(send):
            raise RuntimeError("whole-phase gate requires explicit endpoint callables")
        self._speech_packet_tokens = dict(speech_packet_tokens)
        self._get_json = get_json
        self._post_json = post_json
        self._send = send
        self._active_receipt: PhaseRequestPreflightReceipt | None = None
        self._consumed: set[str] = set()
        self._lock = Lock()

    @property
    def active_receipt(self) -> PhaseRequestPreflightReceipt | None:
        return self._active_receipt

    def preflight_phase(
        self,
        phase: str,
        requests: Sequence[PreparedGenerationRequest],
    ) -> PhaseRequestPreflightReceipt:
        """Run every local and live non-generative check before admitting one body."""

        self._active_receipt = None
        self._consumed.clear()
        prepared = tuple(requests)
        if (
            len(prepared) != SAMPLE_COUNT
            or tuple(item.sample_id for item in prepared) != self._expected_sample_ids
        ):
            raise RuntimeError("phase requests differ from the exact 104-row roster")

        # Validate every local body before the first live preflight endpoint.
        inspected = tuple(
            _inspect_request(request, expected_phase=phase) for request in prepared
        )
        if len({digest for item in prepared for digest in item.body_sha256_by_slot}) != SAMPLE_COUNT * SLOT_COUNT:
            raise RuntimeError("phase slot body hashes must be globally unique")

        props = self._get_json(PROPS_ENDPOINT)
        marker = props.get("media_marker") if isinstance(props, Mapping) else None
        settings = props.get("default_generation_settings") if isinstance(props, Mapping) else None
        if (
            not isinstance(marker, str)
            or not marker
            or not marker.isascii()
            or not isinstance(settings, Mapping)
            or settings.get("n_ctx") != PHYSICAL_CONTEXT_PER_SLOT
        ):
            raise RuntimeError("live /props does not expose the pinned 32768-token slot")

        audits: list[PromptBudgetAudit] = []
        for request, (_body, messages, response_format, max_tokens) in zip(
            prepared, inspected, strict=True
        ):
            template_payload: dict[str, object] = {"messages": messages}
            if response_format is not None:
                # llama.cpp performs JSON-schema-to-grammar conversion on this path.
                template_payload["response_format"] = response_format
            rendered = self._post_json(APPLY_TEMPLATE_ENDPOINT, template_payload)
            prompt = rendered.get("prompt") if isinstance(rendered, Mapping) else None
            if not isinstance(prompt, str) or not prompt or prompt.count(marker) != 1:
                raise RuntimeError("live template/schema check returned an invalid speech prompt")
            if not prompt.isascii():
                raise RuntimeError("live rendered prompt is not ASCII")
            measured = 0
            for segment in prompt.split(marker):
                if not segment:
                    continue
                tokenized = self._post_json(
                    TOKENIZE_ENDPOINT,
                    {"content": segment, "add_special": False, "parse_special": True},
                )
                tokens = tokenized.get("tokens") if isinstance(tokenized, Mapping) else None
                if not isinstance(tokens, list) or any(
                    isinstance(token, bool) or not isinstance(token, int) for token in tokens
                ):
                    raise RuntimeError("live tokenizer returned malformed token identifiers")
                measured += len(tokens)
            speech_tokens = self._speech_packet_tokens.get(request.packet_id)
            if speech_tokens is None:
                raise RuntimeError("speech token count is unavailable for a prepared packet")
            required = (
                measured
                + speech_tokens
                + REGISTERED_SPECIAL_TOKEN_RESERVE
                + max_tokens
            )
            if required > MAX_REQUIRED_WINDOW_TOKENS:
                raise RuntimeError(
                    f"exact required window {required} exceeds 24576 operational tokens"
                )
            audits.append(
                PromptBudgetAudit(
                    sample_id=request.sample_id,
                    phase=phase,
                    prompt_sha256=hashlib.sha256(prompt.encode("ascii")).hexdigest(),
                    response_format_sha256=(
                        sha256_json(response_format) if response_format is not None else None
                    ),
                    measured_text_tokens=measured,
                    speech_feature_tokens=speech_tokens,
                    completion_token_ceiling=max_tokens,
                    required_window_tokens=required,
                )
            )
        receipt = PhaseRequestPreflightReceipt.create(phase, prepared, audits)
        self._active_receipt = receipt
        return receipt

    def send_preflighted(
        self,
        receipt: PhaseRequestPreflightReceipt,
        body_bytes: bytes,
        *,
        url: str = f"http://127.0.0.1:8090{CHAT_ENDPOINT}",
    ) -> bytes:
        """Consume one allowlisted body exactly once; never retry a failed send."""

        if self._active_receipt is None or receipt is not self._active_receipt:
            raise RuntimeError("generation body has no active whole-phase preflight receipt")
        if not isinstance(body_bytes, bytes):
            raise RuntimeError("generation body must be exact bytes")
        try:
            body = json.loads(body_bytes.decode("ascii"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("generation body is not ASCII JSON") from error
        slot = body.get("id_slot") if isinstance(body, Mapping) else None
        digest = hashlib.sha256(body_bytes).hexdigest()
        if (
            isinstance(slot, bool)
            or not isinstance(slot, int)
            or slot not in range(SLOT_COUNT)
            or digest not in receipt.allowed_body_hashes_by_slot[slot]
        ):
            raise RuntimeError("generation body is outside the phase/slot allowlist")
        if not isinstance(url, str) or not url.endswith(CHAT_ENDPOINT):
            raise RuntimeError("generation send must target the registered chat endpoint")
        with self._lock:
            if digest in self._consumed:
                raise RuntimeError("generation body allowlist entry was already consumed")
            # Consume before I/O so a transport failure cannot become a retry.
            self._consumed.add(digest)
        return self._send(url, body_bytes)

    def dispatch_phase(
        self,
        receipt: PhaseRequestPreflightReceipt,
        requests: Sequence[PreparedGenerationRequest],
    ) -> tuple[GenerationResponse, ...]:
        """Send 104 individual bodies with queue depth four over two slots."""

        prepared = tuple(requests)
        validate_phase_preflight(receipt, prepared, expected_sample_ids=self._expected_sample_ids)

        def dispatch(item: tuple[int, PreparedGenerationRequest]) -> GenerationResponse:
            index, request = item
            slot = index % SLOT_COUNT
            body = request.body_bytes_by_slot[slot]
            response = _extract_chat_response_text(
                self.send_preflighted(receipt, body)
            )
            return GenerationResponse(
                sample_id=request.sample_id,
                phase=request.phase,
                request_body_sha256=request.body_sha256_by_slot[slot],
                response_bytes=response,
            )

        with ThreadPoolExecutor(max_workers=QUEUE_DEPTH) as pool:
            rows = tuple(pool.map(dispatch, enumerate(prepared)))
        if len(rows) != SAMPLE_COUNT:
            raise RuntimeError("generation dispatch did not return 104 responses")
        for request, response in zip(prepared, rows, strict=True):
            validate_response_against_request(response.response_bytes, request)
        return rows


def validate_phase_preflight(
    receipt: object,
    requests: Sequence[PreparedGenerationRequest],
    *,
    expected_sample_ids: Sequence[str],
) -> PhaseRequestPreflightReceipt:
    if not isinstance(receipt, PhaseRequestPreflightReceipt):
        raise RuntimeError("runtime did not return a phase preflight receipt")
    prepared = tuple(requests)
    expected = tuple(expected_sample_ids)
    if (
        receipt.status != "COMPLETE_NO_GENERATION_SENT"
        or receipt.row_count != SAMPLE_COUNT
        or receipt.sample_ids != expected
        or tuple(item.sample_id for item in prepared) != expected
        or tuple(item.phase for item in prepared) != (receipt.phase,) * SAMPLE_COUNT
    ):
        raise RuntimeError("phase preflight roster or phase binding drift")
    expected_hashes = tuple(
        tuple(request.body_sha256_by_slot[slot] for request in prepared)
        for slot in range(SLOT_COUNT)
    )
    if receipt.allowed_body_hashes_by_slot != expected_hashes:
        raise RuntimeError("phase preflight body allowlist drift")
    if tuple(audit.sample_id for audit in receipt.audits) != expected:
        raise RuntimeError("phase preflight audits differ from the roster")
    for request in prepared:
        _inspect_request(request, expected_phase=receipt.phase)
    independently_rebuilt = PhaseRequestPreflightReceipt.create(
        receipt.phase, prepared, receipt.audits
    )
    if independently_rebuilt != receipt:
        raise RuntimeError("phase preflight receipt fails independent recomputation")
    return receipt


def build_embedding_batches(
    observations: Mapping[str, ObservationArtifact],
    sample_ids: Sequence[str],
) -> tuple[tuple[tuple[str, str], ...], ...]:
    """Create four deterministic batches from canonical transcripts only."""

    expected = tuple(sample_ids)
    if (
        len(expected) != SAMPLE_COUNT
        or len(set(expected)) != SAMPLE_COUNT
        or set(observations) != set(expected)
        or any(observations[sample_id].sample_id != sample_id for sample_id in expected)
    ):
        raise RuntimeError("OBS artifacts differ from the exact 104-row roster")
    items = tuple(
        (
            f"embed:{sample_id}:transcript",
            observations[sample_id].transcript,
        )
        for sample_id in expected
    )
    batches = tuple(
        items[index : index + EMBEDDING_BATCH_SIZE]
        for index in range(0, len(items), EMBEDDING_BATCH_SIZE)
    )
    if len(batches) != EMBEDDING_PHYSICAL_REQUESTS or tuple(map(len, batches)) != (
        32,
        32,
        32,
        8,
    ):
        raise RuntimeError("transcript embedding schedule differs from four fixed batches")
    return batches


def _candidate_hash(names: Sequence[str]) -> str:
    return sha256_json(list(names))


def _response_matches_stage_payload(
    response: GenerationResponse,
    state: StageStateEnvelope,
    *,
    expected_stage: str,
) -> bool:
    """Independently prove the sealed payload came from exact response bytes."""

    try:
        value = json.loads(
            response.response_bytes.decode("ascii"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_raise_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, RuntimeError):
        return False
    if not isinstance(value, list):
        return False
    if expected_stage == SELECT_STAGE and isinstance(state.payload, SelectPayload):
        return value == [
            {"name": occurrence.tool_name}
            for occurrence in state.payload.occurrences
        ]
    if expected_stage == JOINT_DRAFT_STAGE and isinstance(
        state.payload, JointDraftPayload
    ):
        return value == [call.as_json() for call in state.payload.calls]
    return False


def validate_stage_barrier(
    states: Mapping[str, object],
    *,
    expected_stage: str,
    phase_run: GenerationPhaseRun,
    observations: Mapping[str, ObservationArtifact],
    candidates: Mapping[str, CandidateSet],
    packet_bindings: Mapping[str, Mapping[str, object]],
    sample_ids: Sequence[str],
    split_identity_sha256: str = SPLIT_IDENTITY_HASH,
) -> Mapping[str, StageStateEnvelope]:
    """Verify all lineage fields before a downstream workflow is materialized."""

    expected = tuple(sample_ids)
    if expected_stage not in {JOINT_DRAFT_STAGE, SELECT_STAGE}:
        raise RuntimeError("stage barrier kind is not registered")
    if set(states) != set(expected) or len(states) != SAMPLE_COUNT:
        raise RuntimeError(f"{expected_stage} barrier must contain all 104 rows")
    request_by_id = {item.sample_id: item for item in phase_run.requests}
    response_by_id = {item.sample_id: item for item in phase_run.output.rows}
    verified: dict[str, StageStateEnvelope] = {}
    for sample_id in expected:
        state = states[sample_id]
        if not isinstance(state, StageStateEnvelope) or state.stage != expected_stage:
            raise RuntimeError(f"{expected_stage} barrier contains an invalid envelope")
        binding = packet_bindings.get(sample_id)
        packet_sha = binding.get("sha256") if isinstance(binding, Mapping) else None
        observation = observations.get(sample_id)
        candidate = candidates.get(sample_id)
        request = request_by_id.get(sample_id)
        response = response_by_id.get(sample_id)
        if (
            not _is_sha256(packet_sha)
            or not isinstance(observation, ObservationArtifact)
            or not isinstance(candidate, CandidateSet)
            or request is None
            or response is None
        ):
            raise RuntimeError(f"{expected_stage} barrier input lineage is incomplete")
        response_format = request.base_body.get("response_format")
        response_format_hash = (
            sha256_json(response_format) if isinstance(response_format, Mapping) else None
        )
        payload_ok = (
            isinstance(state.payload, JointDraftPayload)
            if expected_stage == JOINT_DRAFT_STAGE
            else isinstance(state.payload, SelectPayload)
        )
        if (
            state.sample_identity_sha256
            != hashlib.sha256(sample_id.encode("ascii")).hexdigest()
            or state.split_identity_sha256 != split_identity_sha256
            or state.speech_packet_sha256 != packet_sha
            or state.predecessor_envelope_sha256 is not None
            or response.source_query_state_sha256 is None
            or state.source_query_state_sha256
            != response.source_query_state_sha256
            or state.source_response_sha256 != response.response_sha256
            or state.observation_state_sha256 != observation.state_sha256
            or state.observation_source_response_sha256
            != observation.source_response_sha256
            or state.source_request_body_sha256 != response.request_body_sha256
            or response.request_body_sha256 not in {
                *request.body_sha256_by_slot,
            }
            or state.candidate_set_sha256
            != _candidate_hash(candidate.tool_names)
            or response_format_hash is None
            or state.response_schema_sha256 != response_format_hash
            or request.ground_sha256 is None
            or state.ground_sha256 != request.ground_sha256
            or not payload_ok
            or not _response_matches_stage_payload(
                response, state, expected_stage=expected_stage
            )
        ):
            raise RuntimeError(f"{expected_stage} barrier lineage binding drift")
        verified[sample_id] = state
    return verified


def _hook(runtime: object, name: str) -> Callable[..., object]:
    value = getattr(runtime, name, None)
    if not callable(value):
        raise RuntimeError(f"contact runtime is missing required hook {name!r}")
    return value


def _validate_packets(
    sample_ids: Sequence[str], packet_bindings: Mapping[str, Mapping[str, object]]
) -> None:
    expected = tuple(sample_ids)
    if (
        len(expected) != SAMPLE_COUNT
        or len(set(expected)) != SAMPLE_COUNT
        or set(packet_bindings) != set(expected)
    ):
        raise RuntimeError("packet bindings differ from the exact 104-row roster")
    packet_ids: set[str] = set()
    for sample_id in expected:
        value = packet_bindings[sample_id]
        packet_id = value.get("packet_id") if isinstance(value, Mapping) else None
        packet_sha = value.get("sha256") if isinstance(value, Mapping) else None
        if (
            not isinstance(packet_id, str)
            or not packet_id
            or packet_id in packet_ids
            or not _is_sha256(packet_sha)
        ):
            raise RuntimeError("speech packet binding is malformed or duplicate")
        packet_ids.add(packet_id)


def _prepare_phase(
    runtime: object,
    phase: str,
    *,
    sample_ids: tuple[str, ...],
    packet_bindings: Mapping[str, Mapping[str, object]],
    observations: Mapping[str, ObservationArtifact] | None = None,
    candidates: Mapping[str, CandidateSet] | None = None,
    predecessor_states: Mapping[str, StageStateEnvelope] | None = None,
) -> tuple[PreparedGenerationRequest, ...]:
    raw = _hook(runtime, "prepare_generation_phase")(
        phase,
        sample_ids=sample_ids,
        packet_bindings=packet_bindings,
        observations=observations,
        candidates=candidates,
        predecessor_states=predecessor_states,
    )
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise RuntimeError(f"{phase} request preparation returned no sequence")
    requests = tuple(raw)
    if (
        len(requests) != SAMPLE_COUNT
        or any(not isinstance(item, PreparedGenerationRequest) for item in requests)
        or tuple(item.sample_id for item in requests) != sample_ids
        or any(item.phase != phase for item in requests)
    ):
        raise RuntimeError(f"{phase} request preparation is incomplete")
    return requests  # type: ignore[return-value]


def _preflight_phase(
    runtime: object,
    phase: str,
    requests: tuple[PreparedGenerationRequest, ...],
    *,
    sample_ids: tuple[str, ...],
) -> PhaseRequestPreflightReceipt:
    receipt = _hook(runtime, "preflight_generation_phase")(phase, requests)
    validated = validate_phase_preflight(
        receipt, requests, expected_sample_ids=sample_ids
    )
    if validated.phase != phase:
        raise RuntimeError("runtime preflight phase binding drift")
    return validated


def _dispatch_phase(
    runtime: object,
    phase: str,
    requests: tuple[PreparedGenerationRequest, ...],
    preflight: PhaseRequestPreflightReceipt,
    *,
    sample_ids: tuple[str, ...],
) -> GenerationPhaseRun:
    raw = _hook(runtime, "dispatch_generation_phase")(phase, requests, preflight)
    if not isinstance(raw, GenerationPhaseOutput) or raw.phase != phase:
        raise RuntimeError(f"{phase} dispatch returned no exact phase output")
    if tuple(row.sample_id for row in raw.rows) != sample_ids:
        raise RuntimeError(f"{phase} output differs from the frozen roster")
    for request, response in zip(requests, raw.rows, strict=True):
        if response.request_body_sha256 not in request.body_sha256_by_slot:
            raise RuntimeError(f"{phase} response request hash was not preflighted")
        validate_response_against_request(response.response_bytes, request)
    return GenerationPhaseRun(phase, requests, preflight, raw)


def _run_phase(
    runtime: object,
    phase: str,
    *,
    sample_ids: tuple[str, ...],
    packet_bindings: Mapping[str, Mapping[str, object]],
    observations: Mapping[str, ObservationArtifact] | None = None,
    candidates: Mapping[str, CandidateSet] | None = None,
    predecessor_states: Mapping[str, StageStateEnvelope] | None = None,
) -> GenerationPhaseRun:
    requests = _prepare_phase(
        runtime,
        phase,
        sample_ids=sample_ids,
        packet_bindings=packet_bindings,
        observations=observations,
        candidates=candidates,
        predecessor_states=predecessor_states,
    )
    preflight = _preflight_phase(
        runtime, phase, requests, sample_ids=sample_ids
    )
    return _dispatch_phase(
        runtime, phase, requests, preflight, sample_ids=sample_ids
    )


def _validate_observations(
    value: object, *, sample_ids: tuple[str, ...]
) -> Mapping[str, ObservationArtifact]:
    if not isinstance(value, Mapping) or set(value) != set(sample_ids):
        raise RuntimeError("OBS parser did not produce the complete frozen roster")
    if any(
        not isinstance(value[sample_id], ObservationArtifact)
        or value[sample_id].sample_id != sample_id
        for sample_id in sample_ids
    ):
        raise RuntimeError("OBS parser produced a malformed canonical artifact")
    return value  # type: ignore[return-value]


def _run_embedding(
    runtime: object,
    observations: Mapping[str, ObservationArtifact],
    *,
    sample_ids: tuple[str, ...],
) -> Mapping[str, tuple[float, ...]]:
    vectors: dict[str, tuple[float, ...]] = {}
    for batch in build_embedding_batches(observations, sample_ids):
        response = _hook(runtime, "embed_batch")(batch)
        expected = tuple(contact_id for contact_id, _text in batch)
        if not isinstance(response, Mapping) or set(response) != set(expected):
            raise RuntimeError("embedding response differs from its physical batch")
        for contact_id in expected:
            vector = response[contact_id]
            if (
                not isinstance(vector, tuple)
                or not vector
                or any(
                    isinstance(item, bool)
                    or not isinstance(item, (int, float))
                    or not math.isfinite(float(item))
                    for item in vector
                )
            ):
                raise RuntimeError("embedding vector is malformed")
            vectors[contact_id] = tuple(float(item) for item in vector)
    if len(vectors) != EMBEDDING_LOGICAL_ITEMS:
        raise RuntimeError("embedding phase did not produce exactly 104 vectors")
    return vectors


def _validate_candidates(
    value: object,
    *,
    observations: Mapping[str, ObservationArtifact],
    sample_ids: tuple[str, ...],
) -> Mapping[str, CandidateSet]:
    if not isinstance(value, Mapping) or set(value) != set(sample_ids):
        raise RuntimeError("dense retrieval did not cover the frozen roster")
    for sample_id in sample_ids:
        candidate = value[sample_id]
        if (
            not isinstance(candidate, CandidateSet)
            or candidate.sample_id != sample_id
            or candidate.query_state_sha256 != observations[sample_id].state_sha256
        ):
            raise RuntimeError("dense K32 candidate lineage drift")
    return value  # type: ignore[return-value]


def _validate_manifest(value: object, *, role: str) -> Mapping[str, object]:
    if (
        not isinstance(value, Mapping)
        or value.get("role") != role
        or value.get("status") != "COMPLETE"
        or value.get("complete_rows") != SAMPLE_COUNT
    ):
        raise RuntimeError(f"final manifest {role!r} is not complete")
    return value


def execute_contact_ready_flight(
    *,
    runtime: object,
    sample_ids: Sequence[str],
    packet_bindings: Mapping[str, Mapping[str, object]],
) -> Mapping[str, object]:
    """Resume V2 after OBS and execute only the remaining authorized contacts."""

    expected = tuple(sample_ids)
    _validate_packets(expected, packet_bindings)
    if getattr(runtime, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise RuntimeError("runtime must use the existing OpenJiuwen workflow executor")
    if (
        getattr(runtime, "slot_count", None) != SLOT_COUNT
        or getattr(runtime, "queue_depth", None) != QUEUE_DEPTH
    ):
        raise RuntimeError("runtime generation geometry must be slots=2 queue=4")
    _hook(runtime, "assert_attempt_unopened")()
    recovered = _hook(runtime, "rehydrate_completed_prefix")()
    if not isinstance(recovered, RecoveredPrefixArtifacts):
        raise RuntimeError("runtime did not return a verified recovered prefix")
    m0 = recovered.m0
    obs = recovered.obs
    observations = _validate_observations(
        recovered.observations,
        sample_ids=expected,
    )

    _hook(runtime, "start_embedding")()
    try:
        vectors = _run_embedding(runtime, observations, sample_ids=expected)
        candidates = _validate_candidates(
            _hook(runtime, "retrieve_candidates")(
                observations, vectors, top_k=TOP_K
            ),
            observations=observations,
            sample_ids=expected,
        )
    finally:
        _hook(runtime, "stop_embedding")()
    checkpoint = _hook(runtime, "persist_post_embedding_checkpoint")(
        observations,
        candidates,
    )
    candidates = _validate_candidates(
        _hook(runtime, "rehydrate_post_embedding_checkpoint")(
            checkpoint,
            observations,
        ),
        observations=observations,
        sample_ids=expected,
    )

    _hook(runtime, "start_generation")("post-embedding")
    try:
        # Prepare and preflight both first-stage arms before either can send.
        joint_requests = _prepare_phase(
            runtime,
            JOINT_PHASE,
            sample_ids=expected,
            packet_bindings=packet_bindings,
            observations=observations,
            candidates=candidates,
        )
        select_requests = _prepare_phase(
            runtime,
            SELECT_PHASE,
            sample_ids=expected,
            packet_bindings=packet_bindings,
            observations=observations,
            candidates=candidates,
        )
        joint_preflight = _preflight_phase(
            runtime, JOINT_PHASE, joint_requests, sample_ids=expected
        )
        select_preflight = _preflight_phase(
            runtime, SELECT_PHASE, select_requests, sample_ids=expected
        )
        joint = _dispatch_phase(
            runtime,
            JOINT_PHASE,
            joint_requests,
            joint_preflight,
            sample_ids=expected,
        )
        raw_joint_states = _hook(runtime, "parse_stage_states")(
            JOINT_DRAFT_STAGE,
            joint,
            observations,
            candidates,
            packet_bindings,
        )
        joint_states = validate_stage_barrier(
            raw_joint_states,
            expected_stage=JOINT_DRAFT_STAGE,
            phase_run=joint,
            observations=observations,
            candidates=candidates,
            packet_bindings=packet_bindings,
            sample_ids=expected,
        )

        select = _dispatch_phase(
            runtime,
            SELECT_PHASE,
            select_requests,
            select_preflight,
            sample_ids=expected,
        )
        raw_select_states = _hook(runtime, "parse_stage_states")(
            SELECT_STAGE,
            select,
            observations,
            candidates,
            packet_bindings,
        )
        select_states = validate_stage_barrier(
            raw_select_states,
            expected_stage=SELECT_STAGE,
            phase_run=select,
            observations=observations,
            candidates=candidates,
            packet_bindings=packet_bindings,
            sample_ids=expected,
        )

        # Both first-stage barriers are complete.  Materialize and preflight
        # every second-stage request before either second-stage send.
        revise_requests = _prepare_phase(
            runtime,
            REVISE_PHASE,
            sample_ids=expected,
            packet_bindings=packet_bindings,
            observations=observations,
            candidates=candidates,
            predecessor_states=joint_states,
        )
        fill_requests = _prepare_phase(
            runtime,
            FILL_PHASE,
            sample_ids=expected,
            packet_bindings=packet_bindings,
            observations=observations,
            candidates=candidates,
            predecessor_states=select_states,
        )
        revise_preflight = _preflight_phase(
            runtime, REVISE_PHASE, revise_requests, sample_ids=expected
        )
        fill_preflight = _preflight_phase(
            runtime, FILL_PHASE, fill_requests, sample_ids=expected
        )
        revise = _dispatch_phase(
            runtime,
            REVISE_PHASE,
            revise_requests,
            revise_preflight,
            sample_ids=expected,
        )
        fill = _dispatch_phase(
            runtime,
            FILL_PHASE,
            fill_requests,
            fill_preflight,
            sample_ids=expected,
        )
    finally:
        _hook(runtime, "stop_generation")("post-embedding")

    phase_runs = (m0, obs, joint, select, revise, fill)
    audits = tuple(audit for run in phase_runs for audit in run.preflight.audits)
    if len(audits) != FULL_FLIGHT_GENERATION_CONTACTS:
        raise RuntimeError("flight must carry 624 exact prompt-budget audits")
    if sum(len(run.output.rows) for run in phase_runs) != FULL_FLIGHT_GENERATION_CONTACTS:
        raise RuntimeError("full flight generation artifact accounting drift")
    send_accounting = _hook(runtime, "generation_send_accounting")()
    if (
        not isinstance(send_accounting, Mapping)
        or set(send_accounting) != set(GENERATION_PHASES)
        or any(send_accounting.get(phase) != SAMPLE_COUNT for phase in GENERATION_PHASES)
        or sum(int(value) for value in send_accounting.values())
        != GENERATION_CONTACTS
    ):
        raise RuntimeError("flight physical generation-send accounting drift")

    final_runs = {
        "direct_m0": m0,
        "joint_one_call": joint,
        "joint_draft_revise": revise,
        "select_then_fill": fill,
    }
    manifests: list[Mapping[str, object]] = []
    for role in FINAL_MANIFEST_ROLES:
        extras = {
            "config_sha256": CONFIG_SHA256,
            "prompt_budget_audits": final_runs[role].preflight.audits,
            "observation_phase_sha256": sha256_json(
                [row.response_sha256 for row in obs.output.rows]
            ),
            "candidate_set_sha256": sha256_json(
                {
                    sample_id: candidates[sample_id].candidate_set_sha256
                    for sample_id in expected
                }
            ),
            "joint_draft_state_sha256": sha256_json(
                {
                    sample_id: joint_states[sample_id].envelope_sha256
                    for sample_id in expected
                }
            ),
            "select_state_sha256": sha256_json(
                {
                    sample_id: select_states[sample_id].envelope_sha256
                    for sample_id in expected
                }
            ),
            "recovered_prefix_sha256": recovered.source_report_sha256,
            "post_embedding_checkpoint_sha256": checkpoint.get(
                "checkpoint_sha256"
            ) if isinstance(checkpoint, Mapping) else None,
        }
        seal_hook = (
            "seal_recovered_direct_manifest"
            if role == "direct_m0"
            else "seal_manifest"
        )
        manifests.append(_validate_manifest(
            _hook(runtime, seal_hook)(role, final_runs[role], extras),
            role=role,
        ))
    flight = _hook(runtime, "seal_flight")(
        tuple(manifests),
        {
            "config_sha256": CONFIG_SHA256,
            "generation_contacts": GENERATION_CONTACTS,
            "inherited_generation_contacts": SAMPLE_COUNT
            * len(REUSED_GENERATION_PHASES),
            "full_flight_generation_contacts": FULL_FLIGHT_GENERATION_CONTACTS,
            "embedding_logical_items": EMBEDDING_LOGICAL_ITEMS,
            "embedding_physical_requests": EMBEDDING_PHYSICAL_REQUESTS,
            "diagnostic_phases": DIAGNOSTIC_PHASES,
            "network_jitter_study": False,
            "scorer_started": False,
            "gold_opened": False,
        },
    )
    if not isinstance(flight, Mapping) or flight.get("status") != "SEALED":
        raise RuntimeError("runtime did not seal the complete fresh flight")
    return flight


def preflight_report() -> dict[str, object]:
    """Describe the immutable schedule without opening any runtime artifact."""

    return {
        "schema": "saea-a2t-select-fill-agentloop-preflight-v1",
        "status": "PREFLIGHT_ONLY_NO_CONTACT",
        "run_id": RUN_ID,
        "config_sha256": CONFIG_SHA256,
        "roster_path": str(ROSTER_PATH),
        "roster_sha256": ROSTER_SHA256,
        "preprocess_report_path": str(PREPROCESS_REPORT_PATH),
        "preprocess_report_sha256": PREPROCESS_REPORT_SHA256,
        "promotion_receipt": str(PROMOTION_RECEIPT_PATH),
        "promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
        "packet_root": str(PROMOTED_PACKET_ROOT),
        "phase_order": list(PHASE_ORDER),
        "generation_contacts": GENERATION_CONTACTS,
        "embedding_logical_items": EMBEDDING_LOGICAL_ITEMS,
        "embedding_physical_requests": EMBEDDING_PHYSICAL_REQUESTS,
        "complete_final_manifests": len(FINAL_MANIFEST_ROLES),
        "contacts_made": {
            "generation": 0,
            "embedding": 0,
            "template": 0,
            "tokenizer": 0,
            "scorer": 0,
        },
    }


def _load_json_object(path: Path, *, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} cannot be read as JSON") from error
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return value


def _load_runtime_factory(
    specification: str, *, expected_sha256: str
) -> Callable[..., object]:
    """Load only the exact local factory named by the execution authority."""

    if not isinstance(specification, str) or specification.count(":") != 1:
        raise RuntimeError("runtime factory must be PATH.py:callable")
    path_text, callable_name = specification.split(":", 1)
    path = Path(path_text).resolve()
    if (
        path != LOCAL_RUNTIME_FACTORY_PATH.resolve()
        or not path.is_file()
        or not callable_name.isidentifier()
        or not _is_sha256(expected_sha256)
        or sha256_file(path) != expected_sha256
    ):
        raise RuntimeError("runtime factory path, hash, or callable is invalid")
    spec = importlib.util.spec_from_file_location("a2t_select_fill_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("runtime factory module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    factory = getattr(module, callable_name, None)
    if not callable(factory):
        raise RuntimeError("runtime factory callable is unavailable")
    return factory


def _validate_execution_authority(document: object) -> Mapping[str, object]:
    """Validate coordinator-owned identity fields; the runtime validates plans."""

    if not isinstance(document, Mapping):
        raise RuntimeError("execution authority must be a JSON object")
    hashes = document.get("hashes")
    if (
        document.get("status") != "CONTACT_AUTHORIZED"
        or document.get("run_id") != RUN_ID
        or document.get("config_sha256") != CONFIG_SHA256
        or document.get("roster_sha256") != ROSTER_SHA256
        or document.get("split_name") != SPLIT_ID
        or document.get("split_identity_hash") != SPLIT_IDENTITY_HASH
        or document.get("bundle_split_identity_hash")
        != BUNDLE_SPLIT_IDENTITY_HASH
        or document.get("bundle_protocol_sha256") != BUNDLE_PROTOCOL_SHA256
        or document.get("one_shot") is not True
        or document.get("generation_contact_ceiling") != GENERATION_CONTACTS
        or document.get("embedding_physical_request_ceiling")
        != EMBEDDING_PHYSICAL_REQUESTS
        or not isinstance(hashes, Mapping)
        or not _is_sha256(hashes.get("coordinator_launcher_sha256"))
        or not _is_sha256(hashes.get("local_runtime_factory_sha256"))
    ):
        raise RuntimeError("execution authority identity or budget drift")
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--preflight-contact-ready", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--authority", type=Path)
    parser.add_argument("--authority-sha256")
    parser.add_argument("--runtime-factory")
    args = parser.parse_args(argv)
    selected = sum(
        int(value)
        for value in (
            args.preflight_only,
            args.preflight_contact_ready,
            args.execute,
        )
    )
    if selected > 1:
        raise SystemExit("choose exactly one preflight or execution mode")
    if args.preflight_only:
        print(json.dumps(preflight_report(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    if not args.preflight_contact_ready and not args.execute:
        raise SystemExit(
            "No contact is the default; choose --preflight-only or supply a "
            "hash-bound authority and concrete runtime factory."
        )
    if (
        args.authority is None
        or not _is_sha256(args.authority_sha256)
        or not isinstance(args.runtime_factory, str)
    ):
        raise SystemExit(
            "contact-ready modes require --authority, --authority-sha256, "
            "and --runtime-factory"
        )
    runtime = None
    try:
        if sha256_file(args.authority) != args.authority_sha256:
            raise RuntimeError("execution authority SHA-256 drift")
        authority = _validate_execution_authority(
            _load_json_object(args.authority, label="execution authority")
        )
        hashes = authority["hashes"]
        assert isinstance(hashes, Mapping)
        if sha256_file(Path(__file__)) != hashes["coordinator_launcher_sha256"]:
            raise RuntimeError("coordinator launcher SHA-256 drift")
        factory = _load_runtime_factory(
            args.runtime_factory,
            expected_sha256=str(hashes["local_runtime_factory_sha256"]),
        )
        runtime = factory(
            authority=authority,
            protocol_config=protocol_config(),
            launcher_module=sys.modules[__name__],
        )
        ready = _hook(runtime, "assert_contact_ready_preflight")()
        if not isinstance(ready, Mapping) or ready.get("status") != (
            "CONTACT_READY_NO_CONTACT"
        ):
            raise RuntimeError("concrete runtime did not pass contact-ready preflight")
        if args.preflight_contact_ready:
            print(json.dumps(ready, ensure_ascii=True, indent=2, sort_keys=True))
            return 0
        receipt = execute_contact_ready_flight(
            runtime=runtime,
            sample_ids=getattr(runtime, "sample_ids", ()),
            packet_bindings=getattr(runtime, "packet_bindings", {}),
        )
    except Exception as error:
        abort = getattr(runtime, "abort_open_attempts", None)
        if args.execute and callable(abort):
            abort(repr(error))
        raise SystemExit(f"flight refused: {error}") from error
    print(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


__all__ = [
    "CONFIG_SHA256",
    "BUNDLE_SPLIT_IDENTITY_HASH",
    "BUNDLE_PROTOCOL_SHA256",
    "CandidateSet",
    "DIAGNOSTIC_PHASES",
    "EMBEDDING_BATCH_SIZE",
    "EMBEDDING_LOGICAL_ITEMS",
    "EMBEDDING_PHYSICAL_REQUESTS",
    "FILL_PHASE",
    "FINAL_MANIFEST_ROLES",
    "FULL_FLIGHT_GENERATION_CONTACTS",
    "GENERATION_CONTACTS",
    "GENERATION_PHASES",
    "GenerationPhaseOutput",
    "GenerationResponse",
    "JOINT_PHASE",
    "MAX_REQUIRED_WINDOW_TOKENS",
    "M0_PHASE",
    "OBS_PHASE",
    "ObservationArtifact",
    "PHASE_ORDER",
    "PHYSICAL_CONTEXT_PER_SLOT",
    "PhaseRequestPreflightReceipt",
    "PreparedGenerationRequest",
    "PromptBudgetAudit",
    "QUEUE_DEPTH",
    "REUSED_GENERATION_PHASES",
    "REVISE_PHASE",
    "RecoveredPrefixArtifacts",
    "SAMPLE_COUNT",
    "SELECT_PHASE",
    "SLOT_COUNT",
    "TOP_K",
    "WholePhaseRequestGate",
    "_load_runtime_factory",
    "_validate_execution_authority",
    "build_embedding_batches",
    "execute_contact_ready_flight",
    "preflight_report",
    "protocol_config",
    "sha256_json",
    "validate_phase_preflight",
    "validate_stage_barrier",
]


if __name__ == "__main__":
    raise SystemExit(main())
