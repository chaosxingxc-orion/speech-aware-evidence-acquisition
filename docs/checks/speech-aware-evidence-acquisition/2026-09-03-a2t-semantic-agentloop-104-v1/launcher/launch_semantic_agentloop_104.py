"""Contact-ready, fail-closed launcher for the 104-row semantic flight.

The default command is a zero-contact preflight. Execution is exposed only
through an explicitly supplied local runtime factory and an exact, fully
resolved authority document. No authority is authored here.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
import hashlib
import importlib.util
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
    parse_observation_response,
    run_phase as run_openjiuwen_phase,
)


CHECK_DIR = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-semantic-agentloop-104-v1"
)
LOCAL_RUNTIME_FACTORY_PATH = CHECK_DIR / "launcher/local_runtime_factory.py"
ROSTER_PATH = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-fresh-agentloop-roster/flight-roster-receipt.json"
)
ROSTER_SHA256 = "457297464e4e0acc9db541cbee5a2215d3447974c55d9c712c0cb1765623079e"
SPLIT_ID = "A2T-AGENTLOOP-FRESH-FLIGHT"
SPLIT_IDENTITY_HASH = "84c56416a36d5eb1737fa49f6b255b0a59585df8c8ff1754240a87022983eab0"
RUN_ID = "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1"

PREPROCESS_REPORT_PATH = CHECK_DIR / "preprocess-report.json"
PREPROCESS_REPORT_SHA256 = (
    "32ec7ab4b93926f81a9f352e0dbcabf669f41eec23956e94f694c987d4a45950"
)
PROMOTION_RECEIPT_PATH = Path(
    "/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a/"
    "A2T-SEMANTIC-AGENTLOOP-104-V1-promotion.json"
)
PROMOTION_RECEIPT_SHA256 = (
    "6f5d77438b50ebba8130122c6cc39acff18f0707836c61e72a03f6af1380c6b5"
)
PROMOTED_PACKET_ROOT = Path(
    "/home/chao/feat-cache/a2t-semantic-agentloop-v1-packets-04ccc72a"
)
LLAMA_CPP_BUILD_COMMIT = "04ccc72a2207347ca76161b93fd9d846dd0a8675"
GENERATION_DECODER_GGUF_SHA256 = (
    "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
)
QWEN3_EMBEDDING_Q8_GGUF_SHA256 = (
    "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
)

M0_PHASE = "M0_DIRECT"
EMBEDDING_PHASE = "EMBED_TRANSCRIPT_AND_RETRIEVAL_QUERY"
TRANSCRIPT_USE_PHASE = "TRANSCRIPT_TOP16_USE"
MODEL_QUERY_USE_PHASE = "MODEL_QUERY_TOP16_USE"
RRF_FUSED_USE_PHASE = "RRF_FUSED_TOP16_USE"
SHUFFLED_FUSED_USE_PHASE = "SAME_STRATUM_SHUFFLED_FUSED_USE"
PHASE_ORDER = (
    M0_PHASE,
    OBSERVATION_PHASE,
    EMBEDDING_PHASE,
    TRANSCRIPT_USE_PHASE,
    MODEL_QUERY_USE_PHASE,
    RRF_FUSED_USE_PHASE,
    SHUFFLED_FUSED_USE_PHASE,
)

MANIFEST_ROLES = (
    "direct_m0",
    "obs_semantic_retrieval",
    "transcript_top16_use",
    "model_query_top16_use",
    "rrf_fused_top16_use",
    "same_stratum_shuffled_fused_use",
)

SAMPLE_COUNT = FRESH_DISCOVERY_ROW_COUNT
GENERATION_CONTACTS = SAMPLE_COUNT * 6
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
PROPS_ENDPOINT = "/props"
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
    "coordinator_launcher_sha256": None,
    "local_runtime_factory_sha256": None,
    "governed_embedding_tool_sha256": None,
    "execution_plan_set_sha256": None,
    "embedding_execution_plan_sha256": None,
    "exposure_preregistration_sha256": None,
    "generation_runtime_receipt_sha256": None,
    "generation_decoder_gguf_sha256": GENERATION_DECODER_GGUF_SHA256,
    "embedding_runtime_receipt_sha256": None,
    "qwen3_embedding_0_6b_q8_gguf_sha256": QWEN3_EMBEDDING_Q8_GGUF_SHA256,
    "speech_packet_promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
    "construction_rows_sha256": None,
    "construction_embedding_receipt_sha256": None,
    "construction_vector_artifact_sha256": None,
    "semantic_runtime_asset_receipt_sha256": None,
    "semantic_centroid_artifact_sha256": None,
    "semantic_compatibility_rules_sha256": None,
    "semantic_index_sha256": None,
    "runner_snapshot_sha256": None,
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
        "preprocess_report_sha256": PREPROCESS_REPORT_SHA256,
        "speech_packet_promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
        "phase_order": list(PHASE_ORDER),
        "manifest_roles": list(MANIFEST_ROLES),
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
            "precontact_endpoints": [
                PROPS_ENDPOINT,
                APPLY_TEMPLATE_ENDPOINT,
                TOKENIZE_ENDPOINT,
            ],
        },
        "embedding": {
            "model_id": EMBEDDING_MODEL_ID,
            "gguf_sha256": QWEN3_EMBEDDING_Q8_GGUF_SHA256,
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
            "outcome_arms": [
                TRANSCRIPT_USE_PHASE,
                MODEL_QUERY_USE_PHASE,
                RRF_FUSED_USE_PHASE,
                SHUFFLED_FUSED_USE_PHASE,
            ],
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


@dataclass(frozen=True)
class PreprocessedPackets:
    """Exact promoted packet bindings and measured speech-token counts."""

    bindings: Mapping[str, Mapping[str, str]]
    speech_tokens: Mapping[str, int]
    feature_root: Path
    promotion_receipt_sha256: str
    decoder_gguf_sha256: str


def validate_preprocessing_documents(
    report: object,
    promotion: object,
    roster: ValidatedRoster,
) -> PreprocessedPackets:
    """Bind the V2 report and promotion receipt to every frozen roster row."""

    if not isinstance(report, Mapping) or not isinstance(promotion, Mapping):
        raise RuntimeError("preprocessing artifacts must be JSON objects")
    if (
        report.get("schema") != "saea-a2t-semantic-agentloop-preprocess-report-v2"
        or report.get("count") != SAMPLE_COUNT
        or report.get("packets_promoted") != SAMPLE_COUNT
        or report.get("promotion_receipt_sha256") != PROMOTION_RECEIPT_SHA256
        or report.get("promotion_receipt") != str(PROMOTION_RECEIPT_PATH)
        or report.get("packet_root") != str(PROMOTED_PACKET_ROOT)
        or report.get("llama_cpp_build_commit") != LLAMA_CPP_BUILD_COMMIT
    ):
        raise RuntimeError("preprocess V2 report identity drift")
    if (
        promotion.get("schema") != "saea-a2t-speech-packet-promotion-receipt-v1"
        or promotion.get("count") != SAMPLE_COUNT
        or promotion.get("feature_root") != str(PROMOTED_PACKET_ROOT)
        or promotion.get("llama_cpp_build_commit") != LLAMA_CPP_BUILD_COMMIT
        or promotion.get("split_identity_hash") != SPLIT_IDENTITY_HASH
    ):
        raise RuntimeError("speech-packet promotion identity drift")
    report_tokens = report.get("speech_feature_tokens")
    promotion_tokens = promotion.get("speech_feature_tokens")
    if not isinstance(report_tokens, Mapping) or not isinstance(
        promotion_tokens, Mapping
    ):
        raise RuntimeError("preprocessing token receipts are missing")
    expected_distribution = {
        "count": 104,
        "min": 26,
        "median": 65.0,
        "p95": 169,
        "max": 481,
    }
    for token_receipt in (report_tokens, promotion_tokens):
        distribution = token_receipt.get("distribution")
        if not isinstance(distribution, Mapping) or any(
            distribution.get(name) != value
            for name, value in expected_distribution.items()
        ):
            raise RuntimeError("promoted packet token distribution drift")
    report_rows = report_tokens.get("packets")
    promotion_token_rows = promotion_tokens.get("packets")
    packet_rows = promotion.get("packets")
    if any(
        not isinstance(rows, list) or len(rows) != SAMPLE_COUNT
        for rows in (report_rows, promotion_token_rows, packet_rows)
    ):
        raise RuntimeError("preprocessing must describe exactly 104 packets")

    def token_map(rows: object) -> dict[str, int]:
        assert isinstance(rows, list)
        result: dict[str, int] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                raise RuntimeError("packet token row is malformed")
            packet_id, count = row.get("packet_id"), row.get("n_tokens")
            if (
                not isinstance(packet_id, str)
                or not packet_id
                or packet_id in result
                or isinstance(count, bool)
                or not isinstance(count, int)
                or count <= 0
            ):
                raise RuntimeError("packet token identity or count is malformed")
            result[packet_id] = count
        return result

    measured = token_map(report_rows)
    if measured != token_map(promotion_token_rows):
        raise RuntimeError("report and promotion packet-token counts differ")
    promoted_by_id: dict[str, Mapping[str, object]] = {}
    for row in packet_rows:  # type: ignore[union-attr]
        if not isinstance(row, Mapping):
            raise RuntimeError("promoted packet descriptor is malformed")
        packet_id = row.get("packet_id")
        if not isinstance(packet_id, str) or packet_id in promoted_by_id:
            raise RuntimeError("promoted packet identity is malformed or duplicate")
        if (
            not _is_sha256(row.get("packet_sha256"))
            or not _is_sha256(row.get("audio_sha256"))
            or row.get("decoder_gguf_sha256") != GENERATION_DECODER_GGUF_SHA256
            or row.get("n_tokens") != measured.get(packet_id)
        ):
            raise RuntimeError("promoted packet descriptor hash or token drift")
        promoted_by_id[packet_id] = row
    bindings: dict[str, Mapping[str, str]] = {}
    for roster_row in roster.items:
        sample_id = str(roster_row["sample_id"])
        packet_id = sample_id.replace(":", "/", 1)
        descriptor = promoted_by_id.get(packet_id)
        if descriptor is None or descriptor.get("audio_sha256") != roster_row.get(
            "audio_sha256"
        ):
            raise RuntimeError(f"promoted packet does not bind roster row {sample_id!r}")
        bindings[sample_id] = {
            "packet_id": packet_id,
            "sha256": str(descriptor["packet_sha256"]),
        }
    if set(promoted_by_id) != set(measured) or len(bindings) != SAMPLE_COUNT:
        raise RuntimeError("promoted packet coverage differs from the fresh roster")
    return PreprocessedPackets(
        bindings=bindings,
        speech_tokens=measured,
        feature_root=PROMOTED_PACKET_ROOT,
        promotion_receipt_sha256=PROMOTION_RECEIPT_SHA256,
        decoder_gguf_sha256=GENERATION_DECODER_GGUF_SHA256,
    )


def validate_preprocessed_packet_paths(
    roster: ValidatedRoster,
    *,
    report_path: Path = PREPROCESS_REPORT_PATH,
    promotion_path: Path = PROMOTION_RECEIPT_PATH,
) -> PreprocessedPackets:
    """Read only the two exact pinned preprocessing artifacts."""

    if Path(report_path).resolve() != PREPROCESS_REPORT_PATH.resolve():
        raise RuntimeError("preprocess report path is not frozen")
    if Path(promotion_path) != PROMOTION_RECEIPT_PATH:
        raise RuntimeError("promotion receipt path is not frozen")
    if sha256_file(report_path) != PREPROCESS_REPORT_SHA256:
        raise RuntimeError("preprocess report SHA-256 drift")
    if sha256_file(promotion_path) != PROMOTION_RECEIPT_SHA256:
        raise RuntimeError("promotion receipt SHA-256 drift")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        promotion = json.loads(promotion_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError("pinned preprocessing artifacts cannot be read") from error
    return validate_preprocessing_documents(report, promotion, roster)


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
    """Three matched packet maps plus auditable full ranking identities."""

    transcript_packets: Mapping[str, SelectedToolDecisionPacket]
    model_query_packets: Mapping[str, SelectedToolDecisionPacket]
    fused_packets: Mapping[str, SelectedToolDecisionPacket]
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
    transcript_packets: dict[str, SelectedToolDecisionPacket] = {}
    query_packets: dict[str, SelectedToolDecisionPacket] = {}
    fused_packets: dict[str, SelectedToolDecisionPacket] = {}
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
        transcript_top16 = tuple(transcript.full_ranked_tool_names[:TOP_K])
        query_top16 = tuple(query.full_ranked_tool_names[:TOP_K])
        transcript_packet = ground.build(transcript_top16)
        query_packet = ground.build(query_top16)
        fused_packet = ground.build(fused.selected_tool_names)
        if (
            transcript_packet.selected_tool_names != transcript_top16
            or query_packet.selected_tool_names != query_top16
            or fused_packet.selected_tool_names != fused.selected_tool_names
        ):
            raise RuntimeError("selected-tool packet order differs from fused ranking")
        transcript_packets[sample_id] = transcript_packet
        query_packets[sample_id] = query_packet
        fused_packets[sample_id] = fused_packet
        receipts[sample_id] = {
            "index_sha256": fused.index_sha256,
            "transcript_query_vector_sha256": transcript.query_vector_sha256,
            "retrieval_query_vector_sha256": query.query_vector_sha256,
            "transcript_full_ranking": list(transcript.full_ranked_tool_names),
            "retrieval_query_full_ranking": list(query.full_ranked_tool_names),
            "fused_full_ranking": list(fused.full_ranked_tool_names),
            "transcript_selected_tool_names": list(transcript_top16),
            "model_query_selected_tool_names": list(query_top16),
            "fused_selected_tool_names": list(fused.selected_tool_names),
            "rrf_constant": fused.rrf_constant,
            "fusion_sha256": fused.fusion_sha256,
            "transcript_packet_text_sha256": transcript_packet.text_sha256,
            "model_query_packet_text_sha256": query_packet.text_sha256,
            "fused_packet_text_sha256": fused_packet.text_sha256,
            "transcript_response_format_sha256": (
                transcript_packet.response_format_sha256
            ),
            "model_query_response_format_sha256": query_packet.response_format_sha256,
            "fused_response_format_sha256": fused_packet.response_format_sha256,
        }
    return RoutingMaterial(
        transcript_packets=transcript_packets,
        model_query_packets=query_packets,
        fused_packets=fused_packets,
        routing_receipts=receipts,
    )


@dataclass(frozen=True)
class UseArmMaterial:
    """The four USE arm maps in their frozen execution order."""

    transcript: Mapping[str, object]
    model_query: Mapping[str, object]
    fused: Mapping[str, object]
    shuffled_fused: Mapping[str, object]


def build_use_materials(
    *,
    roster: ValidatedRoster,
    observations: Mapping[str, ObservationState],
    routing: RoutingMaterial,
) -> UseArmMaterial:
    """Create three matched arms and the fused same-stratum control."""

    packet_maps = (
        routing.transcript_packets,
        routing.model_query_packets,
        routing.fused_packets,
    )
    if set(roster.sample_ids) != set(observations) or any(
        set(roster.sample_ids) != set(packets) for packets in packet_maps
    ):
        raise RuntimeError("roster, observation, and packet identities must match")
    transcript, _unused_transcript_control = build_matched_and_shuffled_material(
        observations=observations,
        matched_packets=routing.transcript_packets,
        sample_tiers=roster.tiers,
        seed=DERANGEMENT_SEED,
    )
    model_query, _unused_query_control = build_matched_and_shuffled_material(
        observations=observations,
        matched_packets=routing.model_query_packets,
        sample_tiers=roster.tiers,
        seed=DERANGEMENT_SEED,
    )
    fused, shuffled = build_matched_and_shuffled_material(
        observations=observations,
        matched_packets=routing.fused_packets,
        sample_tiers=roster.tiers,
        seed=DERANGEMENT_SEED,
    )
    for sample_id in roster.sample_ids:
        recipient = fused[sample_id]
        donor = shuffled[sample_id]
        if (
            recipient.donor_sample_id != sample_id
            or donor.donor_sample_id == sample_id
            or donor.tier != recipient.tier
            or len(donor.packet.selected_tool_names)
            != len(recipient.packet.selected_tool_names)
        ):
            raise RuntimeError("shuffled USE control violates its matched stratum")
    return UseArmMaterial(
        transcript=transcript,
        model_query=model_query,
        fused=fused,
        shuffled_fused=shuffled,
    )


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
        request_role: str = "generation",
        allow_missing_response_format: bool = False,
    ) -> None:
        if not isinstance(media_marker, str) or not media_marker:
            raise RuntimeError("prompt-budget gate requires a pinned media marker")
        if not callable(post_json) or not callable(send):
            raise RuntimeError("prompt-budget gate requires explicit contact callables")
        if allow_missing_response_format and request_role != "direct_m0":
            raise RuntimeError(
                "response-format-free contact is reserved for the direct M0 role"
            )
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
        self._request_role = request_role
        self._allow_missing_response_format = allow_missing_response_format
        self._audits: list[dict[str, object]] = []
        self._lock = Lock()

    @property
    def audits(self) -> tuple[Mapping[str, object], ...]:
        with self._lock:
            return tuple(dict(row) for row in self._audits)

    def __call__(self, url: str, body_bytes: bytes) -> bytes:
        if not isinstance(url, str) or not url.endswith(CHAT_ENDPOINT):
            raise RuntimeError("generation send must target the registered chat endpoint")
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
        has_response_format = isinstance(response_format, Mapping) and bool(response_format)
        if not has_response_format and not self._allow_missing_response_format:
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
        template_payload = {"messages": messages}
        if has_response_format:
            template_payload["response_format"] = response_format
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
            "request_body_sha256": hashlib.sha256(body_bytes).hexdigest(),
            "messages_sha256": sha256_json(messages),
            "response_format_sha256": (
                sha256_json(response_format) if has_response_format else None
            ),
            "request_role": self._request_role,
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


def parse_complete_observations(
    summary: object,
    *,
    expected_sample_ids: Sequence[str],
    registered_tool_names: Sequence[str],
) -> dict[str, ObservationState]:
    """Parse all OBS results exactly and refuse the complete phase on one error."""

    expected = tuple(expected_sample_ids)
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != SAMPLE_COUNT:
        raise RuntimeError("OBS summary must contain exactly 104 results")
    observations: dict[str, ObservationState] = {}
    for result in results:
        sample_id = getattr(result, "sample_id", None)
        response_text = getattr(result, "final_response_text", None)
        if not isinstance(sample_id, str) or sample_id in observations:
            raise RuntimeError("OBS summary contains malformed or duplicate identities")
        observations[sample_id] = parse_observation_response(
            response_text,
            registered_tool_names=registered_tool_names,
        )
    if set(observations) != set(expected) or len(set(expected)) != SAMPLE_COUNT:
        raise RuntimeError("OBS results are incomplete or outside the frozen roster")
    return observations


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


def _hook(runtime: object, name: str) -> Callable[..., object]:
    value = getattr(runtime, name, None)
    if not callable(value):
        raise RuntimeError(f"contact runtime is missing required hook {name!r}")
    return value


def _summary_ids(summary: object, *, label: str) -> tuple[str, ...]:
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != SAMPLE_COUNT:
        raise RuntimeError(f"{label} summary must contain exactly 104 results")
    identities = tuple(getattr(result, "sample_id", None) for result in results)
    if any(not isinstance(value, str) or not value for value in identities) or len(
        set(identities)
    ) != SAMPLE_COUNT:
        raise RuntimeError(f"{label} summary identities are malformed or duplicate")
    return identities  # type: ignore[return-value]


def _validate_manifest_descriptor(
    value: object, *, role: str, runtime_receipt_sha256: str
) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"manifest sealer returned no descriptor for {role!r}")
    if (
        value.get("role") != role
        or value.get("status") != "COMPLETE"
        or value.get("complete_rows") != SAMPLE_COUNT
        or not isinstance(value.get("manifest"), str)
        or not value.get("manifest")
        or value.get("runtime_receipt_sha256") != runtime_receipt_sha256
    ):
        raise RuntimeError(f"manifest {role!r} is not complete and scoreable")
    return dict(value)


def execute_contact_ready_flight(
    *,
    runtime: object,
    roster: ValidatedRoster,
    packets: PreprocessedPackets,
    authority_hashes: Mapping[str, object],
    m0_runner: Callable[..., object] = run_m0_direct_phase,
    agentloop_runner: Callable[..., object] = run_openjiuwen_phase,
) -> dict[str, object]:
    """Execute the frozen one-shot order using repository runners.

    The caller supplies only governed runtime construction and service lifecycle
    hooks. This function owns phase ordering, runner selection, OBS parsing,
    batching/routing, and complete-manifest requirements. It never retries.
    """

    validated_hashes = validate_authority_hashes(authority_hashes)
    if set(roster.sample_ids) != set(packets.bindings):
        raise RuntimeError("packet bindings differ from the exact fresh roster")
    if getattr(runtime, "agent_executor_id", None) != AGENT_EXECUTOR_ID:
        raise RuntimeError("runtime must use the existing OpenJiuwen executor")
    if getattr(runtime, "slot_count", None) != SLOT_COUNT or getattr(
        runtime, "queue_depth", None
    ) != QUEUE_DEPTH:
        raise RuntimeError("runtime generation geometry must be slots=2 queue=4")
    _hook(runtime, "assert_attempt_unopened")()
    gate = ServerPhaseGate()
    summaries: dict[str, object] = {}

    gate.start_generation("pre-embedding")
    _hook(runtime, "start_generation")("pre-embedding")
    try:
        m0_kwargs = _hook(runtime, "m0_kwargs")(packets.bindings)
        if not isinstance(m0_kwargs, Mapping):
            raise RuntimeError("M0 runtime arguments must be a mapping")
        summaries["direct_m0"] = m0_runner(**dict(m0_kwargs))
        if set(_summary_ids(summaries["direct_m0"], label="M0")) != set(
            roster.sample_ids
        ):
            raise RuntimeError("M0 results differ from the frozen roster")

        obs_kwargs = _hook(runtime, "observation_kwargs")(packets.bindings)
        if not isinstance(obs_kwargs, Mapping) or "phase" in obs_kwargs:
            raise RuntimeError("OBS runtime arguments are malformed")
        obs_summary = agentloop_runner(phase=OBSERVATION_PHASE, **dict(obs_kwargs))
        summaries["obs_semantic_retrieval"] = obs_summary
        registered = getattr(runtime, "registered_tool_names", None)
        if not isinstance(registered, tuple) or not registered:
            raise RuntimeError("runtime must expose frozen registered tool names")
        observations = parse_complete_observations(
            obs_summary,
            expected_sample_ids=roster.sample_ids,
            registered_tool_names=registered,
        )
    finally:
        _hook(runtime, "stop_generation")("pre-embedding")
        gate.stop_generation("pre-embedding")

    gate.start_embedding()
    _hook(runtime, "start_embedding")()
    try:
        client = _hook(runtime, "embedding_client")()
        vectors = embed_observations(client, observations)
        routing = route_observations(
            index=_hook(runtime, "semantic_index")(),
            ground=_hook(runtime, "selected_tool_ground")(),
            observations=observations,
            vectors=vectors,
        )
        use_material = build_use_materials(
            roster=roster,
            observations=observations,
            routing=routing,
        )
    finally:
        _hook(runtime, "stop_embedding")()
        gate.stop_embedding()

    use_arms = (
        (TRANSCRIPT_USE_PHASE, "transcript_top16_use", use_material.transcript),
        (MODEL_QUERY_USE_PHASE, "model_query_top16_use", use_material.model_query),
        (RRF_FUSED_USE_PHASE, "rrf_fused_top16_use", use_material.fused),
        (
            SHUFFLED_FUSED_USE_PHASE,
            "same_stratum_shuffled_fused_use",
            use_material.shuffled_fused,
        ),
    )
    gate.start_generation("post-embedding")
    _hook(runtime, "start_generation")("post-embedding")
    try:
        for public_phase, manifest_role, material in use_arms:
            kwargs = _hook(runtime, "use_kwargs")(
                public_phase, material, packets.bindings
            )
            if not isinstance(kwargs, Mapping) or "phase" in kwargs:
                raise RuntimeError(f"{public_phase} runtime arguments are malformed")
            runner_phase = (
                SHUFFLED_USE_PHASE
                if public_phase == SHUFFLED_FUSED_USE_PHASE
                else MATCHED_USE_PHASE
            )
            summary = agentloop_runner(phase=runner_phase, **dict(kwargs))
            if set(_summary_ids(summary, label=public_phase)) != set(roster.sample_ids):
                raise RuntimeError(f"{public_phase} results differ from frozen roster")
            summaries[manifest_role] = summary
    finally:
        _hook(runtime, "stop_generation")("post-embedding")
        gate.stop_generation("post-embedding")

    audits = _hook(runtime, "prompt_budget_audits")()
    if not isinstance(audits, Sequence) or len(audits) != GENERATION_CONTACTS:
        raise RuntimeError("every one of 624 generation contacts must have a budget audit")
    if any(
        not isinstance(audit, Mapping)
        or audit.get("context_decision") != ContextBudgetDecision.ALLOW.value
        or audit.get("required_window_tokens", MAX_REQUIRED_WINDOW_TOKENS + 1)
        > MAX_REQUIRED_WINDOW_TOKENS
        for audit in audits
    ):
        raise RuntimeError("generation prompt-budget audit is missing or refused")
    audit_by_role = {
        role: tuple(audits[index * SAMPLE_COUNT : (index + 1) * SAMPLE_COUNT])
        for index, role in enumerate(MANIFEST_ROLES)
    }

    descriptors: list[dict[str, object]] = []
    runtime_receipt_hashes: set[str] = set()
    for role in MANIFEST_ROLES:
        runtime_receipt = _hook(runtime, "seal_runtime_receipt")(
            role, summaries[role]
        )
        if (
            not isinstance(runtime_receipt, Mapping)
            or runtime_receipt.get("status") != "STOPPED"
            or runtime_receipt.get("role") != role
            or not _is_sha256(runtime_receipt.get("sha256"))
        ):
            raise RuntimeError(f"fresh runtime receipt is missing for {role!r}")
        receipt_hash = str(runtime_receipt["sha256"])
        if receipt_hash in runtime_receipt_hashes:
            raise RuntimeError("each phase requires a distinct fresh runtime receipt")
        runtime_receipt_hashes.add(receipt_hash)
        extras: dict[str, object] = {
            "config_sha256": CONFIG_SHA256,
            "protocol_sha256": PROTOCOL_SHA256,
            "authority_hashes": validated_hashes,
            "prompt_budget_audits": audit_by_role[role],
            "runtime_receipt": dict(runtime_receipt),
        }
        if role != "direct_m0":
            extras["observations"] = {
                sample_id: state.as_json()
                for sample_id, state in sorted(observations.items())
            }
        if role.endswith("use"):
            extras["tool_ranking_receipts"] = routing.routing_receipts
        descriptor = _hook(runtime, "seal_manifest")(
            role, summaries[role], extras
        )
        descriptors.append(
            _validate_manifest_descriptor(
                descriptor,
                role=role,
                runtime_receipt_sha256=receipt_hash,
            )
        )
    gate.seal()
    flight_receipt = _hook(runtime, "seal_flight")(
        tuple(descriptors), gate.events, CONFIG_SHA256, PROTOCOL_SHA256
    )
    if not isinstance(flight_receipt, Mapping) or flight_receipt.get("status") != "SEALED":
        raise RuntimeError("flight sealer did not return a sealed receipt")
    return dict(flight_receipt)


def validate_authority_hashes(values: Mapping[str, object]) -> dict[str, str]:
    """Require every external authority and runtime identity before contact."""

    if set(values) != set(REQUIRED_AUTHORITY_HASHES):
        raise RuntimeError("authority hash keys differ from the frozen requirement set")
    validated = {}
    for name, value in values.items():
        if not _is_sha256(value) or value == "0" * 64:
            raise RuntimeError(f"authority hash {name!r} is unresolved")
        expected = REQUIRED_AUTHORITY_HASHES[name]
        if expected is not None and value != expected:
            raise RuntimeError(f"authority hash {name!r} differs from its pinned value")
        validated[name] = str(value)
    return validated


def validate_execution_authority(document: object) -> Mapping[str, object]:
    """Validate a future owner-authored authority without creating one."""

    if not isinstance(document, Mapping):
        raise RuntimeError("execution authority must be one JSON object")
    if (
        document.get("schema") != "saea-a2t-semantic-agentloop-104-authority-v1"
        or document.get("status") != "CONTACT_AUTHORIZED"
        or document.get("run_id") != RUN_ID
        or document.get("config_sha256") != CONFIG_SHA256
        or document.get("protocol_sha256") != PROTOCOL_SHA256
        or document.get("roster_sha256") != ROSTER_SHA256
        or document.get("split_identity_hash") != SPLIT_IDENTITY_HASH
        or document.get("one_shot") is not True
        or document.get("generation_contact_ceiling") != GENERATION_CONTACTS
        or document.get("embedding_physical_request_ceiling")
        != EMBEDDING_PHYSICAL_REQUESTS
    ):
        raise RuntimeError("execution authority identity or budget drift")
    core_protocol_sha256 = document.get("core_protocol_sha256")
    if not _is_sha256(core_protocol_sha256):
        raise RuntimeError("authority must pin the core bundle protocol SHA-256")
    plans = document.get("execution_plans")
    authority_hashes = document.get("hashes")
    preregistration_sha256 = (
        authority_hashes.get("exposure_preregistration_sha256")
        if isinstance(authority_hashes, Mapping)
        else None
    )
    if not isinstance(plans, Mapping) or tuple(plans) != MANIFEST_ROLES:
        raise RuntimeError("authority must carry six ordered phase ExecutionPlans")
    attempt_ids: set[str] = set()
    for role, plan in plans.items():
        if (
            not isinstance(plan, Mapping)
            or plan.get("split_role") != "discovery"
            or plan.get("split_identity_hash") != SPLIT_IDENTITY_HASH
            or plan.get("protocol_hash") != core_protocol_sha256
            or not _is_sha256(plan.get("exposure_preregistration_sha256"))
            or plan.get("exposure_preregistration_sha256")
            != preregistration_sha256
            or not isinstance(plan.get("attempt_id"), str)
            or not plan.get("attempt_id")
        ):
            raise RuntimeError(f"ExecutionPlan {role!r} is incomplete or unsafe")
        attempt_id = str(plan["attempt_id"])
        if attempt_id in attempt_ids:
            raise RuntimeError("generation ExecutionPlan attempt identities must be unique")
        attempt_ids.add(attempt_id)
    embedding_plan = document.get("embedding_execution_plan")
    if (
        not isinstance(embedding_plan, Mapping)
        or embedding_plan.get("run_id")
        != "SAEA-A2T-SEMANTIC-AGENTLOOP-104-V1-EMBED"
        or embedding_plan.get("execution_profile") != "bounded-discovery-probe"
        or embedding_plan.get("carrier_lock_key") != "audio2tool"
        or embedding_plan.get("split_role") != "discovery"
        or embedding_plan.get("split_identity_hash") != SPLIT_IDENTITY_HASH
        or embedding_plan.get("protocol_hash") != core_protocol_sha256
        or embedding_plan.get("planned_model_calls") != SEMANTIC_ITEM_COUNT
        or embedding_plan.get("planned_gpu_hours") != 0.2
        or embedding_plan.get("planned_speech_audio_seconds") != 1
        or embedding_plan.get("exposure_preregistration_sha256")
        != preregistration_sha256
        or not isinstance(embedding_plan.get("attempt_id"), str)
        or not embedding_plan.get("attempt_id")
        or embedding_plan.get("attempt_id") in attempt_ids
    ):
        raise RuntimeError("embedding ExecutionPlan is incomplete or unsafe")
    validate_authority_hashes(authority_hashes or {})  # type: ignore[arg-type]
    return document


def _load_runtime_factory(
    specification: str, *, expected_sha256: str
) -> Callable[..., object]:
    if not isinstance(specification, str) or specification.count(":") != 1:
        raise RuntimeError("runtime factory must be PATH.py:callable")
    path_text, name = specification.split(":", 1)
    path = Path(path_text).resolve()
    if (
        path != LOCAL_RUNTIME_FACTORY_PATH.resolve()
        or not path.is_file()
        or not name.isidentifier()
        or not _is_sha256(expected_sha256)
        or sha256_file(path) != expected_sha256
    ):
        raise RuntimeError("runtime factory path or callable name is invalid")
    module_spec = importlib.util.spec_from_file_location("a2t_flight_runtime", path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError("runtime factory module cannot be loaded")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    factory = getattr(module, name, None)
    if not callable(factory):
        raise RuntimeError("runtime factory callable is unavailable")
    return factory


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
        "generation_contact_ceiling": GENERATION_CONTACTS,
        "embedding_physical_request_ceiling": EMBEDDING_PHYSICAL_REQUESTS,
        "preprocess_report_sha256": PREPROCESS_REPORT_SHA256,
        "promotion_receipt_sha256": PROMOTION_RECEIPT_SHA256,
        "phase_order": list(PHASE_ORDER),
        "resolved_pinned_hashes": {
            name: value
            for name, value in sorted(REQUIRED_AUTHORITY_HASHES.items())
            if value is not None
        },
        "unresolved_authority_hashes": sorted(
            name
            for name, value in REQUIRED_AUTHORITY_HASHES.items()
            if value is None
        ),
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
    parser.add_argument("--preflight-contact-ready", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--authority", type=Path)
    parser.add_argument("--authority-sha256")
    parser.add_argument("--runtime-factory")
    args = parser.parse_args(argv)
    selected_modes = sum(
        int(value)
        for value in (args.preflight_only, args.preflight_contact_ready, args.execute)
    )
    if selected_modes > 1:
        raise SystemExit("choose exactly one preflight or execution mode")
    if args.preflight_only:
        print(json.dumps(preflight_report(), ensure_ascii=True, indent=2, sort_keys=True))
        return 0
    if not args.execute and not args.preflight_contact_ready:
        raise SystemExit(
            "No contact is the default; use --preflight-only or explicitly supply "
            "--preflight-contact-ready or --execute with a pinned authority and "
            "local runtime factory."
        )
    if (
        args.authority is None
        or not _is_sha256(args.authority_sha256)
        or not args.runtime_factory
    ):
        raise SystemExit(
            "contact-ready preflight or execution requires --authority, "
            "--authority-sha256, and --runtime-factory"
        )
    if sha256_file(args.authority) != args.authority_sha256:
        raise SystemExit("execution authority SHA-256 drift")
    runtime = None
    try:
        authority = validate_execution_authority(
            json.loads(args.authority.read_text(encoding="utf-8"))
        )
        if sha256_file(Path(__file__)) != authority["hashes"][  # type: ignore[index]
            "coordinator_launcher_sha256"
        ]:
            raise RuntimeError("coordinator launcher SHA-256 drift")
        roster = validate_roster_path()
        packets = validate_preprocessed_packet_paths(roster)
        factory = _load_runtime_factory(
            args.runtime_factory,
            expected_sha256=authority["hashes"][  # type: ignore[index]
                "local_runtime_factory_sha256"
            ],
        )
        runtime = factory(
            authority=authority,
            roster=roster,
            packets=packets,
            protocol_config=protocol_config(),
            launcher_module=sys.modules[__name__],
        )
        preflight = _hook(runtime, "assert_contact_ready_preflight")()
        if not isinstance(preflight, Mapping) or preflight.get("status") != (
            "CONTACT_READY_NO_CONTACT"
        ):
            raise RuntimeError("concrete runtime did not pass full zero-contact preflight")
        if args.preflight_contact_ready:
            print(json.dumps(preflight, ensure_ascii=True, indent=2, sort_keys=True))
            return 0
        receipt = execute_contact_ready_flight(
            runtime=runtime,
            roster=roster,
            packets=packets,
            authority_hashes=authority["hashes"],  # type: ignore[index]
        )
    except (OSError, UnicodeError, json.JSONDecodeError, RuntimeError) as error:
        abort = getattr(runtime, "abort_open_attempts", None)
        if args.execute and callable(abort):
            abort(repr(error))
        raise SystemExit(f"flight refused: {error}") from error
    print(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True))
    return 0


__all__ = [
    "CONFIG_SHA256",
    "PROTOCOL_SHA256",
    "ExactPromptBudgetTransport",
    "MANIFEST_ROLES",
    "ServerPhaseGate",
    "build_embedding_batches",
    "build_use_materials",
    "embed_observations",
    "execute_contact_ready_flight",
    "observation_response_format",
    "parse_complete_observations",
    "route_observations",
    "run_m0_direct_phase",
    "run_openjiuwen_phase",
    "validate_authority_hashes",
    "validate_execution_authority",
    "validate_preprocessed_packet_paths",
    "validate_preprocessing_documents",
    "validate_roster",
]


if __name__ == "__main__":
    raise SystemExit(main())
