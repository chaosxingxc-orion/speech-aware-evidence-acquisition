"""No-contact, fail-closed launcher support for the 104-row semantic flight.

This file freezes and validates the flight shape.  It deliberately has no
execution-authority path: the owner-bound ExecutionPlan, runtime receipt,
speech-packet promotion receipt, GGUF hashes, and exposure preregistration
must be supplied by the final flight launcher before any contact is possible.
The helpers here provide the exact roster, batching, routing, selected-ground,
server-lifecycle, and per-request prompt-budget rails for that final binding.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from threading import Lock


REPO = Path(__file__).resolve().parents[5]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from speech_aware_evidence_acquisition.rails.a2t_selected_tool_ground import (  # noqa: E402
    SelectedToolDecisionGround,
    SelectedToolDecisionPacket,
)
from speech_aware_evidence_acquisition.rails.a2t_semantic_router import (  # noqa: E402
    RRF_CONSTANT,
    ToolTierSemanticIndex,
    fuse_semantic_rankings,
)
from speech_aware_evidence_acquisition.rails.context_budget import (  # noqa: E402
    REGISTERED_SPECIAL_TOKEN_RESERVE,
    ContextBudgetBreakdown,
    ContextBudgetDecision,
    ContextBudgetInput,
    assess_context_budget,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_flight import (  # noqa: E402
    run_direct_phase as run_m0_direct_phase,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_semantic_agentloop import (  # noqa: E402
    AGENT_EXECUTOR_ID,
    FRESH_DISCOVERY_ROW_COUNT,
    MATCHED_USE_PHASE,
    OBSERVATION_PHASE,
    QUEUE_DEPTH,
    SHUFFLED_USE_PHASE,
    SLOT_COUNT,
    ObservationState,
    build_matched_and_shuffled_material,
    observation_response_format,
    run_phase as run_openjiuwen_phase,
)


CHECK_DIR = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-semantic-agentloop-104-v1"
)
ROSTER_PATH = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json"
)
ROSTER_SHA256 = "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
SPLIT_ID = "A2T-AGENTLOOP-FRESH-FLIGHT"
SPLIT_IDENTITY_HASH = "84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0"
RUN_ID = "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1"

M0_PHASE = "M0_DIRECT"
EMBEDDING_PHASE = "EMBED_TRANSCRIPT_AND_RETRIEVAL_QUERY"
PHASE_ORDER = (
    M0_PHASE,
    OBSERVATION_PHASE,
    EMBEDDING_PHASE,
    MATCHED_USE_PHASE,
    SHUFFLED_USE_PHASE,
)

SAMPLE_COUNT = FRESH_DISCOVERY_ROW_COUNT
GENERATION_CONTACTS = SAMPLE_COUNT * 4
SEMANTIC_ITEM_COUNT = SAMPLE_COUNT * 2
EMBEDDING_BATCH_SIZE = 32
EMBEDDING_PHYSICAL_REQUESTS = math.ceil(SEMANTIC_ITEM_COUNT / EMBEDDING_BATCH_SIZE)
TOP_K = 16
PHYSICAL_CONTEXT_PER_SLOT = 32_768
CONTEXT_RESERVE = 8_192
MAX_REQUIRED_WINDOW_TOKENS = PHYSICAL_CONTEXT_PER_SLOT - CONTEXT_RESERVE
GENERATION_SERVER_CONTEXT = PHYSICAL_CONTEXT_PER_SLOT * SLOT_COUNT
GENERATION_SERVER_ARGS = ("-c", str(GENERATION_SERVER_CONTEXT), "-np", str(SLOT_COUNT))
EMBEDDING_MODEL_ID = "Qwen3-Embedding-0.6B-Q8"
EMBEDDING_ENDPOINT = "/embedding"
APPLY_TEMPLATE_ENDPOINT = "/apply-template"
TOKENIZE_ENDPOINT = "/tokenize"
CHAT_ENDPOINT = "/v1/chat/completions"
DERANGEMENT_SEED = "saea-a2t-semantic-agentloop-104-v1"

TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)
_SHA256 = frozenset("0123456789abcdef")

# These are intentionally not guessed.  The authority-binding launcher must
# replace every value with the exact governed artifact hash and refuse a blank
# or placeholder.  They are outside the scientific protocol hash.
REQUIRED_AUTHORITY_HASHES = {
    "execution_plan_sha256": None,
    "exposure_preregistration_sha256": None,
    "generation_runtime_receipt_sha256": None,
    "generation_decoder_gguf_sha256": None,
    "embedding_runtime_receipt_sha256": None,
    "qwen3_embedding_0_6b_q8_gguf_sha256": None,
    "speech_packet_promotion_receipt_sha256": None,
    "construction_rows_sha256": None,
    "construction_embedding_manifest_sha256": None,
    "selected_tool_ground_corpus_sha256": None,
    "selected_tool_compatibility_sha256": None,
}


def canonical_json_bytes(value: object) -> bytes:
    """Return the only JSON byte representation used for launcher hashes."""

    try:
        return json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
    except (TypeError, UnicodeEncodeError) as error:
        raise RuntimeError("launcher material must be canonical ASCII JSON") from error


def sha256_json(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def protocol_config() -> dict[str, object]:
    """Return the fully mechanical scientific and transport configuration."""

    return {
        "schema": "saea-a2t-semantic-agentloop-104-config-v1",
        "run_id": RUN_ID,
        "split_id": SPLIT_ID,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "roster_sha256": ROSTER_SHA256,
        "phase_order": list(PHASE_ORDER),
        "sample_count": SAMPLE_COUNT,
        "generation": {
            "contacts": GENERATION_CONTACTS,
            "agent_executor_id": AGENT_EXECUTOR_ID,
            "slot_count": SLOT_COUNT,
            "queue_depth": QUEUE_DEPTH,
            "physical_context_per_slot": PHYSICAL_CONTEXT_PER_SLOT,
            "context_reserve": CONTEXT_RESERVE,
            "maximum_required_window_tokens": MAX_REQUIRED_WINDOW_TOKENS,
            "registered_special_token_reserve": REGISTERED_SPECIAL_TOKEN_RESERVE,
            "server_args": list(GENERATION_SERVER_ARGS),
            "prompt_level_multi_sample_batching": False,
            "retry": False,
            "fallback": False,
            "repair": False,
            "response_format": "per-sample",
            "precontact_endpoints": [APPLY_TEMPLATE_ENDPOINT, TOKENIZE_ENDPOINT],
        },
        "embedding": {
            "model_id": EMBEDDING_MODEL_ID,
            "semantic_items": SEMANTIC_ITEM_COUNT,
            "physical_batch_size": EMBEDDING_BATCH_SIZE,
            "physical_requests": EMBEDDING_PHYSICAL_REQUESTS,
            "sources": ["transcript", "retrieval_query"],
            "generation_server_coexistence": False,
        },
        "routing": {
            "rankings": "full-registry-per-source",
            "fusion": "reciprocal-rank-fusion",
            "rrf_constant": RRF_CONSTANT,
            "selected_top_k": TOP_K,
        },
        "control": {
            "kind": "same-tier-same-card-count-derangement",
            "seed": DERANGEMENT_SEED,
        },
        "gold_and_scorer": "postseal-only",
    }


CONFIG_SHA256 = sha256_json(protocol_config())


def protocol_hash() -> str:
    """Derive the protocol identity from the exact config and roster identity."""

    return sha256_json(
        {
            "schema": "saea-a2t-semantic-agentloop-protocol-binding-v1",
            "config_sha256": CONFIG_SHA256,
            "roster_sha256": ROSTER_SHA256,
            "split_identity_hash": SPLIT_IDENTITY_HASH,
        }
    )


PROTOCOL_SHA256 = protocol_hash()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value).issubset(_SHA256)


@dataclass(frozen=True)
class ValidatedRoster:
    """Identity-only view of the fresh 104-row speech roster."""

    sample_ids: tuple[str, ...]
    tiers: Mapping[str, str]
    items: tuple[Mapping[str, object], ...]
    audio_seconds_total: float
    media_roster_sha256: str


def validate_roster(document: object) -> ValidatedRoster:
    """Refuse any roster other than the exact fresh, uncontacted discovery set."""

    if not isinstance(document, Mapping):
        raise RuntimeError("fresh roster must be a JSON object")
    if (
        document.get("schema") != "saea-a2t-agentloop-flight-roster-receipt-v1"
        or document.get("split_name") != SPLIT_ID
        or document.get("split_role") != "discovery"
        or document.get("status") != "PREPARED_NOT_CONTACT_AUTHORITY"
        or document.get("split_identity_hash") != SPLIT_IDENTITY_HASH
        or document.get("count") != SAMPLE_COUNT
        or document.get("contacts")
        != {"audio": 0, "model": 0, "network": 0, "scorer": 0}
    ):
        raise RuntimeError("fresh roster identity or no-contact status drift")
    selection = document.get("selection")
    if (
        not isinstance(selection, Mapping)
        or selection.get("per_tier") != 13
        or selection.get("uses_test") is not False
        or selection.get("uses_gold_at_runtime") is not False
    ):
        raise RuntimeError("fresh roster selection policy drift")
    rows = document.get("items")
    if not isinstance(rows, list) or len(rows) != SAMPLE_COUNT:
        raise RuntimeError("fresh roster must contain exactly 104 items")
    sample_ids: list[str] = []
    tiers: dict[str, str] = {}
    media_lines: list[str] = []
    audio_total = 0.0
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping):
            raise RuntimeError(f"fresh roster item {index} must be an object")
        sample_id = row.get("sample_id")
        tier = row.get("tier")
        relpath = row.get("media_relpath")
        audio_sha256 = row.get("audio_sha256")
        audio_seconds = row.get("audio_seconds")
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not sample_id.isascii()
            or tier not in TIERS
            or not isinstance(relpath, str)
            or not relpath
            or "\\" in relpath
            or Path(relpath).is_absolute()
            or ".." in Path(relpath).parts
            or not _is_sha256(audio_sha256)
            or isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(float(audio_seconds))
            or float(audio_seconds) <= 0
        ):
            raise RuntimeError(f"fresh roster item {index} is malformed")
        sample_ids.append(sample_id)
        tiers[sample_id] = str(tier)
        audio_total += float(audio_seconds)
        media_lines.append(f"{sample_id}\t{relpath}\t{audio_sha256}\t{audio_seconds}")
    if len(set(sample_ids)) != SAMPLE_COUNT:
        raise RuntimeError("fresh roster sample identities are not unique")
    if Counter(tiers.values()) != Counter({tier: 13 for tier in TIERS}):
        raise RuntimeError("fresh roster must contain exactly 13 rows per tier")
    measured_media_hash = hashlib.sha256(
        "\n".join(media_lines).encode("utf-8")
    ).hexdigest()
    if measured_media_hash != document.get("media_roster_sha256"):
        raise RuntimeError("fresh media roster hash drift")
    if abs(audio_total - float(document.get("audio_seconds_total", -1))) > 1e-6:
        raise RuntimeError("fresh roster audio duration drift")
    return ValidatedRoster(
        sample_ids=tuple(sample_ids),
        tiers=tiers,
        items=tuple(rows),
        audio_seconds_total=audio_total,
        media_roster_sha256=measured_media_hash,
    )


def validate_roster_path(path: Path = ROSTER_PATH) -> ValidatedRoster:
    if Path(path).resolve() != ROSTER_PATH.resolve():
        raise RuntimeError("roster path is not the frozen fresh-roster input")
    if sha256_file(path) != ROSTER_SHA256:
        raise RuntimeError("fresh roster receipt SHA-256 drift")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("fresh roster receipt cannot be read exactly") from error
    return validate_roster(document)


TextEmbeddingItem = tuple[str, str]


def build_embedding_batches(
    observations: Mapping[str, ObservationState],
) -> tuple[tuple[TextEmbeddingItem, ...], ...]:
    """Freeze transcript/query ordering and physical batches of exactly 32."""

    if (
        not isinstance(observations, Mapping)
        or len(observations) != SAMPLE_COUNT
        or any(
            not isinstance(value, ObservationState) for value in observations.values()
        )
    ):
        raise RuntimeError("embedding requires exactly 104 parsed observation states")
    items: list[TextEmbeddingItem] = []
    for sample_id in sorted(observations):
        observation = observations[sample_id]
        items.extend(
            (
                (f"semantic:{sample_id}:transcript", observation.transcript),
                (
                    f"semantic:{sample_id}:retrieval_query",
                    observation.retrieval_query,
                ),
            )
        )
    if len(items) != SEMANTIC_ITEM_COUNT or len({item[0] for item in items}) != len(
        items
    ):
        raise RuntimeError("semantic embedding item identity drift")
    return tuple(
        tuple(items[start : start + EMBEDDING_BATCH_SIZE])
        for start in range(0, len(items), EMBEDDING_BATCH_SIZE)
    )


def embed_observations(
    client: object,
    observations: Mapping[str, ObservationState],
) -> dict[str, tuple[float, ...]]:
    """Make seven physical requests for 208 logical semantic text items."""

    embed_batch = getattr(client, "embed_text_batch", None)
    if not callable(embed_batch):
        raise RuntimeError("embedding client must support physical text batching")
    verify = getattr(client, "verify_media_marker", None)
    if callable(verify):
        verify()
    vectors: dict[str, tuple[float, ...]] = {}
    batches = build_embedding_batches(observations)
    for batch in batches:
        produced = tuple(embed_batch(batch))
        if len(produced) != len(batch):
            raise RuntimeError("embedding response count differs from physical batch")
        for expected, vector in zip(batch, produced, strict=True):
            contact_id = getattr(vector, "contact_id", None)
            values = getattr(vector, "values", None)
            if contact_id != expected[0] or not isinstance(values, tuple) or not values:
                raise RuntimeError("embedding response identity or vector drift")
            vectors[contact_id] = values
    if len(vectors) != SEMANTIC_ITEM_COUNT:
        raise RuntimeError("embedding phase did not produce exactly 208 vectors")
    requests = getattr(client, "http_request_count", EMBEDDING_PHYSICAL_REQUESTS)
    if requests != EMBEDDING_PHYSICAL_REQUESTS:
        raise RuntimeError(
            "embedding phase did not use exactly seven physical requests"
        )
    return vectors


@dataclass(frozen=True)
class RoutingMaterial:
    """Matched packets plus auditable full-ranking fusion identities."""

    packets: Mapping[str, SelectedToolDecisionPacket]
    routing_receipts: Mapping[str, Mapping[str, object]]


def route_observations(
    *,
    index: ToolTierSemanticIndex,
    ground: SelectedToolDecisionGround,
    observations: Mapping[str, ObservationState],
    vectors: Mapping[str, Sequence[float]],
) -> RoutingMaterial:
    """Rank both semantic views completely, fuse RRF60, and ground top 16."""

    if not isinstance(index, ToolTierSemanticIndex):
        raise RuntimeError("routing requires a frozen ToolTierSemanticIndex")
    if not isinstance(ground, SelectedToolDecisionGround):
        raise RuntimeError("routing requires a verified SelectedToolDecisionGround")
    batches = build_embedding_batches(observations)
    expected_ids = {contact_id for batch in batches for contact_id, _text in batch}
    if set(vectors) != expected_ids:
        raise RuntimeError(
            "semantic vectors must exactly cover transcript and query items"
        )
    full_k = len(index.registry_tool_names)
    if full_k < TOP_K:
        raise RuntimeError("tool registry is smaller than the frozen top-16 selection")
    packets: dict[str, SelectedToolDecisionPacket] = {}
    receipts: dict[str, Mapping[str, object]] = {}
    for sample_id in sorted(observations):
        transcript = index.rank(
            vectors[f"semantic:{sample_id}:transcript"], top_k=full_k
        )
        query = index.rank(
            vectors[f"semantic:{sample_id}:retrieval_query"], top_k=full_k
        )
        fused = fuse_semantic_rankings(
            (transcript, query),
            top_k=TOP_K,
            source_names=("transcript", "retrieval_query"),
            constant=RRF_CONSTANT,
        )
        if (
            len(transcript.full_ranked_tool_names) != full_k
            or len(query.full_ranked_tool_names) != full_k
            or len(fused.full_ranked_tool_names) != full_k
            or fused.rrf_constant != 60
            or len(fused.selected_tool_names) != TOP_K
        ):
            raise RuntimeError(
                "semantic router did not preserve full-ranking RRF60/top-16"
            )
        packet = ground.build(fused.selected_tool_names)
        if packet.selected_tool_names != fused.selected_tool_names:
            raise RuntimeError("selected-tool packet order differs from fused ranking")
        packets[sample_id] = packet
        receipts[sample_id] = {
            "index_sha256": fused.index_sha256,
            "transcript_query_vector_sha256": transcript.query_vector_sha256,
            "retrieval_query_vector_sha256": query.query_vector_sha256,
            "transcript_full_ranking": list(transcript.full_ranked_tool_names),
            "retrieval_query_full_ranking": list(query.full_ranked_tool_names),
            "fused_full_ranking": list(fused.full_ranked_tool_names),
            "selected_tool_names": list(fused.selected_tool_names),
            "rrf_constant": fused.rrf_constant,
            "fusion_sha256": fused.fusion_sha256,
            "packet_text_sha256": packet.text_sha256,
            "response_format_sha256": packet.response_format_sha256,
        }
    return RoutingMaterial(packets=packets, routing_receipts=receipts)


def build_use_materials(
    *,
    roster: ValidatedRoster,
    observations: Mapping[str, ObservationState],
    packets: Mapping[str, SelectedToolDecisionPacket],
):
    """Create matched and same-tier/same-card-count shuffled USE materials."""

    if set(roster.sample_ids) != set(observations) or set(roster.sample_ids) != set(
        packets
    ):
        raise RuntimeError("roster, observation, and packet identities must match")
    matched, shuffled = build_matched_and_shuffled_material(
        observations=observations,
        matched_packets=packets,
        sample_tiers=roster.tiers,
        seed=DERANGEMENT_SEED,
    )
    for sample_id in roster.sample_ids:
        recipient = matched[sample_id]
        donor = shuffled[sample_id]
        if (
            recipient.donor_sample_id != sample_id
            or donor.donor_sample_id == sample_id
            or donor.tier != recipient.tier
            or len(donor.packet.selected_tool_names)
            != len(recipient.packet.selected_tool_names)
        ):
            raise RuntimeError("shuffled USE control violates its matched stratum")
    return matched, shuffled


class ExactPromptBudgetTransport:
    """Intercept one assembled chat request and gate its exact prompt text.

    Inject an instance as the ``post`` callable of ``LlamaServerTransport``.
    The transport has already converted the rails payload into its exact
    chat messages at this seam. For each request this wrapper calls the
    non-generative template and tokenizer endpoints, then combines exact text,
    speech-packet, special-token, and completion counts under the 24,576-token
    operational ceiling before sending the original body exactly once. There is no
    retry, fallback, repair, or multi-sample generation path.
    """

    def __init__(
        self,
        *,
        media_marker: str,
        speech_packet_tokens: Mapping[str, int],
        post_json: Callable[[str, Mapping[str, object]], object],
        send: Callable[[str, bytes], bytes],
    ) -> None:
        if not isinstance(media_marker, str) or not media_marker:
            raise RuntimeError("prompt-budget gate requires a pinned media marker")
        if not callable(post_json) or not callable(send):
            raise RuntimeError("prompt-budget gate requires explicit contact callables")
        if (
            not isinstance(speech_packet_tokens, Mapping)
            or not speech_packet_tokens
            or any(
                not isinstance(packet_id, str)
                or not packet_id
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
                for packet_id, count in speech_packet_tokens.items()
            )
        ):
            raise RuntimeError(
                "prompt-budget gate requires positive packet token counts"
            )
        self._media_marker = media_marker
        self._speech_packet_tokens = dict(speech_packet_tokens)
        self._post_json = post_json
        self._send = send
        self._audits: list[dict[str, object]] = []
        self._lock = Lock()

    @property
    def audits(self) -> tuple[Mapping[str, object], ...]:
        with self._lock:
            return tuple(dict(row) for row in self._audits)

    def __call__(self, url: str, body_bytes: bytes) -> bytes:
        try:
            body = json.loads(body_bytes.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise RuntimeError("generation request is not UTF-8 JSON") from error
        if not isinstance(body, Mapping):
            raise RuntimeError("generation request must be one JSON object")
        messages = body.get("messages")
        response_format = body.get("response_format")
        if not isinstance(messages, list) or not messages:
            raise RuntimeError("generation request must carry one message sequence")
        if any(isinstance(message, list) for message in messages):
            raise RuntimeError("prompt-level multi-sample batching is prohibited")
        if body.get("n", 1) != 1 or body.get("best_of", 1) != 1:
            raise RuntimeError("generation requires n=1 and best_of=1")
        if not isinstance(response_format, Mapping) or not response_format:
            raise RuntimeError("every contact requires a per-request response_format")
        completion_ceiling = body.get("max_tokens")
        if (
            isinstance(completion_ceiling, bool)
            or not isinstance(completion_ceiling, int)
            or completion_ceiling <= 0
        ):
            raise RuntimeError("every contact requires a positive max_tokens ceiling")
        packet_ids = []
        for message in messages:
            if not isinstance(message, Mapping):
                raise RuntimeError("generation messages must contain JSON objects")
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if (
                    not isinstance(part, Mapping)
                    or part.get("type") != "input_speech_features"
                ):
                    continue
                descriptor = part.get("speech_features")
                packet_id = (
                    descriptor.get("packet_id")
                    if isinstance(descriptor, Mapping)
                    else None
                )
                if not isinstance(packet_id, str) or not packet_id:
                    raise RuntimeError("speech feature packet identity is malformed")
                packet_ids.append(packet_id)
        if len(packet_ids) != 1:
            raise RuntimeError(
                "every generation request requires exactly one speech packet"
            )
        packet_id = packet_ids[0]
        speech_tokens = self._speech_packet_tokens.get(packet_id)
        if speech_tokens is None:
            raise RuntimeError(
                f"speech packet token count is unavailable for {packet_id!r}"
            )
        template_payload = {
            "messages": messages,
            "response_format": response_format,
        }
        rendered = self._post_json(APPLY_TEMPLATE_ENDPOINT, template_payload)
        prompt = rendered.get("prompt") if isinstance(rendered, Mapping) else None
        if not isinstance(prompt, str) or not prompt:
            raise RuntimeError("apply-template returned no exact prompt text")
        if prompt.count(self._media_marker) != 1:
            raise RuntimeError("exact prompt must contain one pinned speech marker")
        measured = 0
        tokenize_requests = 0
        for segment in prompt.split(self._media_marker):
            if not segment:
                continue
            tokenized = self._post_json(
                TOKENIZE_ENDPOINT,
                {"content": segment, "add_special": False, "parse_special": True},
            )
            tokenize_requests += 1
            tokens = tokenized.get("tokens") if isinstance(tokenized, Mapping) else None
            if not isinstance(tokens, list) or any(
                isinstance(token, bool) or not isinstance(token, int)
                for token in tokens
            ):
                raise RuntimeError("tokenize returned malformed token ids")
            measured += len(tokens)
        if measured <= 0:
            raise RuntimeError("exact prompt has no measurable text tokens")
        breakdown = ContextBudgetBreakdown(
            rendered_text_tokens=measured,
            speech_feature_packet_tokens=((packet_id, speech_tokens),),
            speech_feature_tokens=speech_tokens,
            special_token_reserve=REGISTERED_SPECIAL_TOKEN_RESERVE,
            completion_token_ceiling=completion_ceiling,
            required_window_tokens=(
                measured
                + speech_tokens
                + REGISTERED_SPECIAL_TOKEN_RESERVE
                + completion_ceiling
            ),
        )
        decision = assess_context_budget(
            ContextBudgetInput.from_payload(body_bytes, breakdown=breakdown)
        )
        if decision.decision is not ContextBudgetDecision.ALLOW:
            raise RuntimeError(
                "exact required window "
                f"{breakdown.required_window_tokens} exceeds 24576 operational tokens"
            )
        audit = {
            "messages_sha256": sha256_json(messages),
            "response_format_sha256": sha256_json(response_format),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "measured_text_tokens": measured,
            "speech_packet_id": packet_id,
            "speech_feature_tokens": speech_tokens,
            "special_token_reserve": REGISTERED_SPECIAL_TOKEN_RESERVE,
            "completion_token_ceiling": completion_ceiling,
            "required_window_tokens": breakdown.required_window_tokens,
            "physical_context_per_slot": PHYSICAL_CONTEXT_PER_SLOT,
            "reserved_tokens": CONTEXT_RESERVE,
            "maximum_required_window_tokens": MAX_REQUIRED_WINDOW_TOKENS,
            "physical_margin_tokens": decision.physical_margin_tokens,
            "operational_margin_tokens": decision.operational_margin_tokens,
            "context_decision": decision.decision.value,
            "context_decision_receipt_sha256": decision.receipt_sha256(),
            "apply_template_requests": 1,
            "tokenize_requests": tokenize_requests,
        }
        # Append before the generation send so a failed send remains auditable.
        with self._lock:
            self._audits.append(audit)
        return self._send(url, body_bytes)


class ServerPhaseGate:
    """Fail closed unless generation and embedding services are disjoint."""

    _EXPECTED = (
        "start-generation:pre-embedding",
        "stop-generation:pre-embedding",
        "start-embedding",
        "stop-embedding",
        "start-generation:post-embedding",
        "stop-generation:post-embedding",
        "seal",
    )

    def __init__(self) -> None:
        self._events: list[str] = []
        self._active: str | None = None

    @property
    def events(self) -> tuple[str, ...]:
        return tuple(self._events)

    def _start(self, event: str, active: str) -> None:
        if self._active is not None:
            raise RuntimeError(f"server {self._active!r} is already active")
        expected = self._EXPECTED[len(self._events)]
        if event != expected:
            raise RuntimeError(f"server phase order drift: expected {expected!r}")
        self._events.append(event)
        self._active = active

    def _stop(self, event: str, active: str) -> None:
        if self._active != active:
            raise RuntimeError(f"cannot stop inactive server {active!r}")
        expected = self._EXPECTED[len(self._events)]
        if event != expected:
            raise RuntimeError(f"server phase order drift: expected {expected!r}")
        self._events.append(event)
        self._active = None

    def start_generation(self, window: str) -> None:
        if window not in {"pre-embedding", "post-embedding"}:
            raise RuntimeError("generation window is not registered")
        self._start(f"start-generation:{window}", f"generation:{window}")

    def stop_generation(self, window: str) -> None:
        self._stop(f"stop-generation:{window}", f"generation:{window}")

    def start_embedding(self) -> None:
        self._start("start-embedding", "embedding")

    def stop_embedding(self) -> None:
        self._stop("stop-embedding", "embedding")

    def seal(self) -> None:
        if self._active is not None:
            raise RuntimeError("cannot seal while a server is active")
        expected = self._EXPECTED[len(self._events)]
        if expected != "seal":
            raise RuntimeError(f"cannot seal before {expected!r}")
        self._events.append("seal")


def validate_authority_hashes(values: Mapping[str, object]) -> dict[str, str]:
    """Require every external authority and runtime identity before contact."""

    if set(values) != set(REQUIRED_AUTHORITY_HASHES):
        raise RuntimeError("authority hash keys differ from the frozen requirement set")
    validated = {}
    for name, value in values.items():
        if not _is_sha256(value) or value == "0" * 64:
            raise RuntimeError(f"authority hash {name!r} is unresolved")
        validated[name] = str(value)
    return validated


def preflight_report() -> dict[str, object]:
    roster = validate_roster_path()
    return {
        "schema": "saea-a2t-semantic-agentloop-104-preflight-v1",
        "status": "PREFLIGHT_ONLY_NO_CONTACT",
        "run_id": RUN_ID,
        "config_sha256": CONFIG_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "roster_sha256": ROSTER_SHA256,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "sample_count": len(roster.sample_ids),
        "phase_order": list(PHASE_ORDER),
        "unresolved_authority_hashes": sorted(REQUIRED_AUTHORITY_HASHES),
        "contacts_made": {
            "embedding_physical_requests": 0,
            "generation": 0,
            "network": 0,
            "scorer": 0,
            "tokenizer": 0,
        },
        "gold_or_scorer_read": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if not args.preflight_only:
        raise SystemExit(
            "This skeleton has no execution authority; use --preflight-only. "
            "Bind all governed hashes and a validated ExecutionPlan in the final launcher."
        )
    print(json.dumps(preflight_report(), ensure_ascii=True, indent=2, sort_keys=True))
    return 0


__all__ = [
    "CONFIG_SHA256",
    "PROTOCOL_SHA256",
    "ExactPromptBudgetTransport",
    "ServerPhaseGate",
    "build_embedding_batches",
    "build_use_materials",
    "embed_observations",
    "observation_response_format",
    "route_observations",
    "run_m0_direct_phase",
    "run_openjiuwen_phase",
    "validate_authority_hashes",
    "validate_roster",
]


if __name__ == "__main__":
    raise SystemExit(main())
