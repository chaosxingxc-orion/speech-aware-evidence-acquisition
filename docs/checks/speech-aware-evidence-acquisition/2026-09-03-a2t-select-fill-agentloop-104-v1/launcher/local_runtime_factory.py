"""Concrete WSL2 runtime for the fresh Audio2Tool SELECT/FILL flight.

Import and construction are contact-free.  The coordinator may start local
services and send requests only after its hash-bound authority checks and this
runtime's complete contact-ready preflight both succeed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
from threading import Lock
import urllib.request

from speech_aware_evidence_acquisition.contracts import (
    ExecutionPlan,
    FrozenCoreGate,
    TraceRecord,
)
from speech_aware_evidence_acquisition.core.attempts import AttemptStore, STATE_OPENED
from speech_aware_evidence_acquisition.core.base import RunResult
from speech_aware_evidence_acquisition.core.bundle import (
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.bundle.git_commit import (
    require_clean_study_repo,
)
from speech_aware_evidence_acquisition.core.config import (
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
    runtime_receipt_relpath,
)
from speech_aware_evidence_acquisition.core.model import LlamaServerTransport
from speech_aware_evidence_acquisition.core.session import (
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.core.split_receipt import VerifiedSplit
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.audio2tool import (
    AUDIO2TOOL_LOCK_KEY,
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (
    asset_dir,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.data.splits import split_identity_hash
from speech_aware_evidence_acquisition.rails.a2t_canonical_family_ground import (
    CanonicalFamilyGround,
)
from speech_aware_evidence_acquisition.rails.a2t_executable_semantic_cards import (
    ExecutableSemanticCardCorpus,
    TaskSemanticCard,
    ToolSemanticCard,
)
from speech_aware_evidence_acquisition.rails.a2t_frozen_semantic_assets import (
    load_frozen_semantic_runtime_assets,
)
from speech_aware_evidence_acquisition.rails.a2t_response_schema import (
    audio2tool_locked_outer_call_array_response_format,
    audio2tool_outer_call_array_response_format,
)
from speech_aware_evidence_acquisition.rails.a2t_select_fill_ground import (
    PARAMETER_MAX_OCCURRENCES,
    build_joint_knowledge_ground,
    build_parameter_knowledge_ground,
    build_routing_knowledge_ground,
)
from speech_aware_evidence_acquisition.rails.a2t_stage_state import (
    JOINT_DRAFT_STAGE,
    SELECT_STAGE,
    JointDraftCall,
    SelectOccurrence,
    StageStateEnvelope,
    build_joint_draft_stage_envelope,
    build_select_stage_envelope,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (
    render_audio2tool_instruction,
)
from speech_aware_evidence_acquisition.rails.consumption import (
    build_consumption_trace,
)
from speech_aware_evidence_acquisition.rails.core_client import FrozenCoreClient
from speech_aware_evidence_acquisition.rails.embedding_client import EmbeddingClient
from speech_aware_evidence_acquisition.rails.knowledge import KnowledgeSnapshot
from speech_aware_evidence_acquisition.rails.obs import AudioRef
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_flight import (
    run_direct_phase,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_select_fill_agentloop import (
    FreshSelectFillPhaseAdapter,
    PhaseMaterial,
    parse_call_array_response,
    parse_select_response,
    run_phase as run_select_fill_phase,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_semantic_agentloop import (
    FreshSemanticPhaseAdapter,
    OBSERVATION_CONTACT_ID,
    OBSERVATION_PHASE,
    observation_response_format,
    parse_observation_response,
    run_phase as run_observation_phase,
)
from speech_aware_evidence_acquisition.rails.task_adapter import TaskAdapter


GENERATION_PORT = 8090
EMBEDDING_PORT = 8082
EMBEDDING_DIMENSION = 1024
EMBEDDING_MODEL_BYTES = 639_150_592
EMBEDDING_MODEL_RELPATH = (
    "models/qwen3-embedding-0.6b-gguf/Qwen3-Embedding-0.6B-Q8_0.gguf"
)
EMBEDDING_RUNTIME_RECEIPT = "receipts/runtime-qwen3-embedding-q8.json"
EMBEDDING_MODEL_LOCK_KEY = "qwen3-embedding-0.6b-gguf"
GENERATION_ARM = "speech-feature-query"
BUNDLE_SPLIT_IDENTITY_SHA256 = (
    "122da6752c7c4011c2f632cee4e737899bfbb451501666fb47aa0676f372d2c8"
)
BUNDLE_PROTOCOL_SHA256 = (
    "4f192381d41c96b55d53433035ff0566795b0fb772503a59555a0f83d15d1171"
)
COMMITTED_CONFIG_FRAGMENTS = {
    "model": "q4km-mmproj-free-speech-native-np2-a2t-select-fill-max1024",
    "dataset": "audio2tool-semantic-agentloop-select-fill-104-v1",
    "baseline": "a2t-semantic-agentloop-select-fill-top32",
    "experiment": "a2t-semantic-agentloop-select-fill-104-v1",
}
_SHA256 = frozenset("0123456789abcdef")


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _phase_trace_path(run_dir: Path, run_id: str) -> Path:
    """Return the trace written by the phase's AgentLoop trace sink."""

    return Path(run_dir) / "agent-loop" / f"{run_id}.trace.jsonl"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Mapping[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read runtime JSON {path}: {error}") from error
    if not isinstance(value, Mapping):
        raise RuntimeError(f"runtime JSON must be an object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _read_jsonl(path: Path, *, label: str) -> tuple[Mapping[str, object], ...]:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
        rows = tuple(json.loads(line) for line in lines if line)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} is not valid UTF-8 JSONL") from error
    if not rows or any(not isinstance(row, Mapping) for row in rows):
        raise RuntimeError(f"{label} must contain JSON objects")
    return rows  # type: ignore[return-value]


def _load_recovery_trace_rows(
    *,
    launcher: object,
    phase: str,
    trace_path: Path,
    expected_trace_sha256: str,
    requests: Sequence[object],
    packet_bindings: Mapping[str, Mapping[str, object]],
    sent_body_sha256_by_sample: Mapping[str, str],
) -> object:
    """Rehydrate one completed source phase from hash-bound trace bytes."""

    _require_file_hash(
        Path(trace_path), expected_trace_sha256, label=f"source {phase} trace"
    )
    prepared = tuple(requests)
    request_by_sample = {item.sample_id: item for item in prepared}
    sample_ids = tuple(item.sample_id for item in prepared)
    if (
        len(prepared) != 104
        or len(request_by_sample) != 104
        or set(packet_bindings) != set(sample_ids)
        or set(sent_body_sha256_by_sample) != set(sample_ids)
    ):
        raise RuntimeError(f"source {phase} recovery roster drift")

    records = _read_jsonl(Path(trace_path), label=f"source {phase} trace")
    by_suffix: dict[str, dict[str, Mapping[str, object]]] = {
        "request": {},
        "response": {},
        "runtime-use": {},
    }
    seen_record_ids: set[str] = set()
    for document in records:
        if set(document) != {"channel", "payload", "record_id"}:
            raise RuntimeError(f"source {phase} trace record shape drift")
        record_id = document.get("record_id")
        payload = document.get("payload")
        channel = document.get("channel")
        if (
            not isinstance(record_id, str)
            or record_id in seen_record_ids
            or not isinstance(channel, str)
            or not isinstance(payload, Mapping)
        ):
            raise RuntimeError(f"source {phase} trace record identity drift")
        TraceRecord(channel=channel, record_id=record_id, payload=payload).validate()
        seen_record_ids.add(record_id)
        suffix = record_id.rsplit("/", 1)[-1]
        if suffix in by_suffix:
            prefix = record_id[: -(len(suffix) + 1)]
            if not prefix or prefix in by_suffix[suffix]:
                raise RuntimeError(f"source {phase} trace request identity drift")
            by_suffix[suffix][prefix] = payload

    requests_by_id = by_suffix["request"]
    responses_by_id = by_suffix["response"]
    if len(requests_by_id) != 104 or set(responses_by_id) != set(requests_by_id):
        raise RuntimeError(f"source {phase} request/response trace count drift")
    runtime_use_by_sample = {}
    for prefix, payload in by_suffix["runtime-use"].items():
        suffix = "/agent-loop"
        if not prefix.endswith(suffix):
            raise RuntimeError("source OBS runtime-use identity is malformed")
        sample_id = prefix[: -len(suffix)]
        if not sample_id or sample_id in runtime_use_by_sample:
            raise RuntimeError("source OBS runtime-use identity is duplicate")
        runtime_use_by_sample[sample_id] = payload
    if phase == launcher.OBS_PHASE and set(runtime_use_by_sample) != set(sample_ids):
        raise RuntimeError("source OBS runtime-use lineage is incomplete")
    if phase != launcher.OBS_PHASE and runtime_use_by_sample:
        raise RuntimeError(f"source {phase} unexpectedly contains runtime-use state")

    request_id_by_sample: dict[str, str] = {}
    for request_id, request_record in requests_by_id.items():
        inner = request_record.get("payload")
        sample_id = inner.get("sample_id") if isinstance(inner, Mapping) else None
        if (
            not isinstance(sample_id, str)
            or sample_id in request_id_by_sample
            or sample_id not in request_by_sample
            or request_record.get("payload_sha256") != _sha256_json(inner)
            or inner.get("speech_packet_sha256")
            != packet_bindings[sample_id].get("sha256")
        ):
            raise RuntimeError(f"source {phase} request lineage drift")
        request_id_by_sample[sample_id] = request_id
    if set(request_id_by_sample) != set(sample_ids):
        raise RuntimeError(f"source {phase} trace sample set drift")

    rows = []
    query_state_hashes: set[str] = set()
    for sample_id in sample_ids:
        request = request_by_sample[sample_id]
        body_sha256 = sent_body_sha256_by_sample[sample_id]
        if body_sha256 not in request.body_sha256_by_slot:
            raise RuntimeError(f"source {phase} request body was not preflighted")
        request_id = request_id_by_sample[sample_id]
        response_record = responses_by_id[request_id]
        text = response_record.get("text")
        if not isinstance(text, str) or not text or not text.isascii():
            raise RuntimeError(f"source {phase} response is not non-empty ASCII")
        response_text_sha256 = hashlib.sha256(text.encode("ascii")).hexdigest()
        if response_record.get("response_text_sha256") != response_text_sha256:
            raise RuntimeError(f"source {phase} response text hash drift")
        query_state_sha256 = None
        if phase == launcher.OBS_PHASE:
            use = runtime_use_by_sample[sample_id]
            contacts = use.get("use_contacts")
            contact = contacts[0] if isinstance(contacts, list) and len(contacts) == 1 else None
            use_response_sha256 = response_record.get("response_text_sha256")
            if (
                not isinstance(contact, Mapping)
                or use.get("use_final_response_sha256") != use_response_sha256
                or contact.get("response_sha256") != use_response_sha256
                or not _is_sha256(contact.get("query_state_sha256"))
            ):
                raise RuntimeError("source OBS response/query-state lineage drift")
            query_state_sha256 = str(contact["query_state_sha256"])
            if query_state_sha256 in query_state_hashes:
                raise RuntimeError("source OBS query states are not unique")
            query_state_hashes.add(query_state_sha256)
        rows.append(
            launcher.GenerationResponse(
                sample_id=sample_id,
                phase=phase,
                request_body_sha256=body_sha256,
                response_bytes=text.encode("ascii"),
                source_query_state_sha256=query_state_sha256,
            )
        )
    return launcher.GenerationPhaseOutput(phase=phase, rows=tuple(rows))


def _derive_recovered_direct_bundle_material(
    *,
    launcher: object,
    trace_path: Path,
    phase_run: object,
    sample_ids: Sequence[str],
) -> tuple[tuple[Mapping[str, object], ...], Mapping[str, object], Mapping[str, str]]:
    """Derive score rows, cost, and record hashes from the frozen M0 trace."""

    records = _read_jsonl(Path(trace_path), label="source M0 trace")
    request_by_id: dict[str, Mapping[str, object]] = {}
    response_by_id: dict[str, Mapping[str, object]] = {}
    cost_by_id: dict[str, Mapping[str, object]] = {}
    record_hashes: dict[str, str] = {}
    for document in records:
        if set(document) != {"channel", "payload", "record_id"}:
            raise RuntimeError("source M0 trace record shape drift")
        channel = document.get("channel")
        record_id = document.get("record_id")
        payload = document.get("payload")
        if (
            not isinstance(channel, str)
            or not isinstance(record_id, str)
            or record_id in record_hashes
            or not isinstance(payload, Mapping)
        ):
            raise RuntimeError("source M0 trace record identity drift")
        record = TraceRecord(channel=channel, record_id=record_id, payload=payload)
        record_hashes[record_id] = record.content_hash()
        for expected_channel, suffix, target in (
            ("MODEL_REQUEST", "/request", request_by_id),
            ("MODEL_RESPONSE", "/response", response_by_id),
            ("COST", "/cost", cost_by_id),
        ):
            if channel == expected_channel:
                if not record_id.endswith(suffix):
                    raise RuntimeError("source M0 transport record suffix drift")
                request_id = record_id[: -len(suffix)]
                if not request_id or request_id in target:
                    raise RuntimeError("source M0 transport identity drift")
                target[request_id] = payload
    if (
        len(request_by_id) != 104
        or set(response_by_id) != set(request_by_id)
        or set(cost_by_id) != set(request_by_id)
        or len(records) != 312
    ):
        raise RuntimeError("source M0 trace must contain 104 request/response/cost triplets")

    response_rows = {
        row.sample_id: row for row in getattr(getattr(phase_run, "output", None), "rows", ())
    }
    expected_samples = tuple(sample_ids)
    if set(response_rows) != set(expected_samples) or len(response_rows) != 104:
        raise RuntimeError("recovered M0 phase output roster drift")
    request_id_by_sample: dict[str, str] = {}
    for request_id, request in request_by_id.items():
        inner = request.get("payload")
        sample_id = inner.get("sample_id") if isinstance(inner, Mapping) else None
        if (
            not isinstance(sample_id, str)
            or sample_id in request_id_by_sample
            or sample_id not in response_rows
            or request.get("arm") != GENERATION_ARM
            or request.get("payload_sha256") != _sha256_json(inner)
        ):
            raise RuntimeError("source M0 request/sample lineage drift")
        request_id_by_sample[sample_id] = request_id
    if set(request_id_by_sample) != set(expected_samples):
        raise RuntimeError("source M0 request roster drift")

    output_rows: list[Mapping[str, object]] = []
    totals: dict[str, int | float] = {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
    }
    for sample_id in sorted(expected_samples):
        request_id = request_id_by_sample[sample_id]
        request = request_by_id[request_id]
        response = response_by_id[request_id]
        cost = cost_by_id[request_id]
        text = response.get("text")
        if not isinstance(text, str) or not text.isascii():
            raise RuntimeError("source M0 response text is not ASCII")
        text_sha256 = hashlib.sha256(text.encode("ascii")).hexdigest()
        recovered = response_rows[sample_id]
        if (
            response.get("response_text_sha256") != text_sha256
            or getattr(recovered, "response_sha256", None) != text_sha256
            or getattr(recovered, "response_bytes", None) != text.encode("ascii")
            or not _is_sha256(request.get("payload_sha256"))
            or not _is_sha256(response.get("response_sha256"))
        ):
            raise RuntimeError("source M0 response lineage drift")
        output_rows.append(
            {
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": AUDIO2TOOL_LOCK_KEY,
                "arm": GENERATION_ARM,
                "text": text,
                "admitted": True,
                "request_sha256": request["payload_sha256"],
                "response_sha256": response["response_sha256"],
                "response_text_sha256": text_sha256,
                "phase": launcher.M0_PHASE,
                "source_run_id": launcher.SOURCE_RUN_ID,
            }
        )
        for field in (
            "calls",
            "audio_seconds",
            "latency_seconds",
            "prompt_tokens",
            "completion_tokens",
        ):
            value = cost.get(field)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or value < 0
            ):
                raise RuntimeError(f"source M0 cost field {field!r} is invalid")
        if cost["calls"] != 1:
            raise RuntimeError("source M0 cost must record one call per request")
        totals["calls_used"] = int(totals["calls_used"]) + 1
        totals["audio_seconds_used"] = float(totals["audio_seconds_used"]) + float(
            cost["audio_seconds"]
        )
        totals["latency_seconds_total"] = float(totals["latency_seconds_total"]) + float(
            cost["latency_seconds"]
        )
        totals["prompt_tokens_total"] = int(totals["prompt_tokens_total"]) + int(
            cost["prompt_tokens"]
        )
        totals["completion_tokens_total"] = int(
            totals["completion_tokens_total"]
        ) + int(cost["completion_tokens"])
    if totals["calls_used"] != 104:
        raise RuntimeError("source M0 recovered cost count drift")
    totals["tool_calls"] = 0
    return tuple(output_rows), totals, record_hashes


def _load_recovery_send_accounting(
    path: Path,
    *,
    expected_sha256: object,
    launcher: object,
    sample_ids: Sequence[str],
) -> Mapping[str, Mapping[str, str]]:
    """Load the exact 208 durable V2 sends without opening response meaning."""

    _require_file_hash(Path(path), expected_sha256, label="source send accounting")
    rows = _read_jsonl(Path(path), label="source send accounting")
    expected_samples = set(sample_ids)
    result = {phase: {} for phase in launcher.REUSED_GENERATION_PHASES}
    for row in rows:
        phase = row.get("phase")
        sample_id = row.get("sample_id")
        body_sha256 = row.get("body_sha256")
        if (
            phase not in result
            or not isinstance(sample_id, str)
            or sample_id not in expected_samples
            or sample_id in result[phase]
            or not _is_sha256(body_sha256)
            or row.get("status") != "CONSUMED_BEFORE_IO"
        ):
            raise RuntimeError("source send accounting identity drift")
        result[phase][sample_id] = str(body_sha256)
    if len(rows) != 208 or any(set(values) != expected_samples for values in result.values()):
        raise RuntimeError("source send accounting must contain exactly 104 M0 and 104 OBS sends")
    return result


def _load_recovery_preflight(
    path: Path,
    *,
    expected_sha256: object,
    launcher: object,
    phase: str,
    requests: Sequence[object],
) -> object:
    """Rebuild and verify one source whole-phase preflight receipt."""

    _require_file_hash(Path(path), expected_sha256, label=f"source {phase} preflight")
    document = _read_json(Path(path))
    audits_raw = document.get("audits")
    if not isinstance(audits_raw, list) or len(audits_raw) != 104:
        raise RuntimeError(f"source {phase} preflight audit count drift")
    try:
        audits = tuple(launcher.PromptBudgetAudit(**row) for row in audits_raw)
    except (TypeError, RuntimeError) as error:
        raise RuntimeError(f"source {phase} preflight audits are malformed") from error
    receipt = launcher.PhaseRequestPreflightReceipt.create(phase, requests, audits)
    if (
        document.get("phase") != phase
        or document.get("status") != receipt.status
        or document.get("sample_ids") != list(receipt.sample_ids)
        or document.get("allowed_body_hashes_by_slot")
        != [list(values) for values in receipt.allowed_body_hashes_by_slot]
        or document.get("receipt_sha256") != receipt.receipt_sha256
    ):
        raise RuntimeError(f"source {phase} preflight binding drift")
    return launcher.validate_phase_preflight(
        receipt,
        requests,
        expected_sample_ids=receipt.sample_ids,
    )


def _write_post_embedding_checkpoint(
    path: Path,
    *,
    launcher: object,
    run_id: str,
    source_report_sha256: str,
    observations: Mapping[str, object],
    candidates: Mapping[str, object],
) -> Mapping[str, object]:
    """Persist the derived K32 state before any resumed generation request."""

    if not _is_sha256(source_report_sha256) or set(observations) != set(candidates):
        raise RuntimeError("post-embedding checkpoint lineage is incomplete")
    rows = []
    for sample_id in sorted(observations):
        observation = observations[sample_id]
        candidate = candidates[sample_id]
        if (
            candidate.sample_id != sample_id
            or candidate.query_state_sha256 != observation.state_sha256
        ):
            raise RuntimeError("post-embedding candidate lineage drift")
        rows.append(
            {
                "sample_id": sample_id,
                "observation_state_sha256": observation.state_sha256,
                "candidate_query_state_sha256": candidate.query_state_sha256,
                "candidate_tool_names": list(candidate.tool_names),
                "candidate_scores": list(candidate.scores),
                "candidate_set_sha256": candidate.candidate_set_sha256,
            }
        )
    if len(rows) != 104:
        raise RuntimeError("post-embedding checkpoint requires exactly 104 rows")
    document = {
        "schema": "saea-a2t-select-fill-post-embedding-k32-v1",
        "run_id": run_id,
        "source_report_sha256": source_report_sha256,
        "count": 104,
        "top_k": 32,
        "rows": rows,
    }
    _write_json(Path(path), document)
    return {
        "path": str(Path(path).resolve()),
        "checkpoint_sha256": _sha256_file(Path(path)),
        "count": 104,
        "top_k": 32,
    }


def _load_post_embedding_checkpoint(
    path: Path,
    *,
    launcher: object,
    expected_sha256: object,
    run_id: str,
    source_report_sha256: str,
    observations: Mapping[str, object],
) -> Mapping[str, object]:
    """Reload and independently validate the durable K32 checkpoint."""

    _require_file_hash(
        Path(path), expected_sha256, label="post-embedding checkpoint"
    )
    document = _read_json(Path(path))
    rows = document.get("rows")
    if (
        document.get("schema") != "saea-a2t-select-fill-post-embedding-k32-v1"
        or document.get("run_id") != run_id
        or document.get("source_report_sha256") != source_report_sha256
        or document.get("count") != 104
        or document.get("top_k") != 32
        or not isinstance(rows, list)
        or len(rows) != 104
    ):
        raise RuntimeError("post-embedding checkpoint identity drift")
    result = {}
    for row in rows:
        sample_id = row.get("sample_id") if isinstance(row, Mapping) else None
        observation = observations.get(sample_id) if isinstance(sample_id, str) else None
        names = row.get("candidate_tool_names") if isinstance(row, Mapping) else None
        scores = row.get("candidate_scores") if isinstance(row, Mapping) else None
        if (
            observation is None
            or sample_id in result
            or not isinstance(names, list)
            or not isinstance(scores, list)
            or row.get("observation_state_sha256") != observation.state_sha256
            or row.get("candidate_query_state_sha256") != observation.state_sha256
        ):
            raise RuntimeError("post-embedding checkpoint row lineage drift")
        candidate = launcher.CandidateSet(
            sample_id=sample_id,
            tool_names=tuple(names),
            scores=tuple(scores),
            query_state_sha256=observation.state_sha256,
        )
        if row.get("candidate_set_sha256") != candidate.candidate_set_sha256:
            raise RuntimeError("post-embedding checkpoint candidate hash drift")
        result[sample_id] = candidate
    if set(result) != set(observations):
        raise RuntimeError("post-embedding checkpoint roster drift")
    return result


def _require_file_hash(path: Path, expected: object, *, label: str) -> Path:
    if not path.is_file() or not _is_sha256(expected) or _sha256_file(path) != expected:
        raise RuntimeError(f"{label} SHA-256 drift")
    return path


def _confined_file(root: Path, raw: object, *, label: str) -> Path:
    if not isinstance(raw, str) or not raw or "\\" in raw:
        raise RuntimeError(f"{label} must be a non-empty POSIX path")
    base = Path(root).resolve()
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (base / candidate).resolve()
    if resolved != base and base not in resolved.parents:
        raise RuntimeError(f"{label} escapes its registered root")
    if not resolved.is_file():
        raise RuntimeError(f"{label} is unavailable: {resolved}")
    return resolved


def parse_execution_plans(
    authority: Mapping[str, object], *, roles: Sequence[str], run_id: str
) -> dict[str, ExecutionPlan]:
    """Build and bind the four remaining generation ExecutionPlans."""

    raw = authority.get("execution_plans")
    ordered = tuple(roles)
    if not isinstance(raw, Mapping) or tuple(raw) != ordered or len(ordered) != 4:
        raise RuntimeError("runtime requires four ordered generation ExecutionPlans")
    hashes = authority.get("hashes")
    preregistration = (
        hashes.get("exposure_preregistration_sha256")
        if isinstance(hashes, Mapping)
        else None
    )
    if not _is_sha256(preregistration):
        raise RuntimeError("authority lacks exposure preregistration SHA-256")
    plans: dict[str, ExecutionPlan] = {}
    attempts: set[str] = set()
    allowed = set(ExecutionPlan.__dataclass_fields__)
    for role in ordered:
        value = raw[role]
        if not isinstance(value, Mapping):
            raise RuntimeError(f"ExecutionPlan {role!r} must be an object")
        if value.get("exposure_preregistration_sha256") != preregistration:
            raise RuntimeError(f"ExecutionPlan {role!r} preregistration binding drift")
        plan = ExecutionPlan(
            **{key: item for key, item in value.items() if key in allowed}
        ).validate()
        if (
            plan.run_id != run_id
            or plan.execution_profile != "bounded-discovery-probe"
            or plan.carrier_lock_key != AUDIO2TOOL_LOCK_KEY
            or plan.split_role != "discovery"
            or plan.split_identity_hash != authority.get("split_identity_hash")
            or plan.protocol_hash != authority.get("core_protocol_sha256")
            or plan.planned_model_calls != 416
            or plan.planned_gpu_hours != 4.0
            or plan.planned_speech_audio_seconds != 3400
            or not plan.attempt_id
            or plan.attempt_id in attempts
        ):
            raise RuntimeError(f"ExecutionPlan {role!r} identity or budget drift")
        attempts.add(plan.attempt_id)
        plans[role] = plan
    expected = hashes.get("execution_plan_set_sha256")  # type: ignore[union-attr]
    if _sha256_json({key: asdict(value) for key, value in plans.items()}) != expected:
        raise RuntimeError("ExecutionPlan set SHA-256 drift")
    return plans


def parse_embedding_execution_plan(
    authority: Mapping[str, object], *, protocol_sha256: str
) -> ExecutionPlan:
    """Build the separately governed 104-item embedding plan."""

    raw = authority.get("embedding_execution_plan")
    hashes = authority.get("hashes")
    if not isinstance(raw, Mapping) or not isinstance(hashes, Mapping):
        raise RuntimeError("authority lacks the embedding ExecutionPlan")
    if raw.get("exposure_preregistration_sha256") != hashes.get(
        "exposure_preregistration_sha256"
    ):
        raise RuntimeError("embedding ExecutionPlan preregistration binding drift")
    allowed = set(ExecutionPlan.__dataclass_fields__)
    plan = ExecutionPlan(
        **{key: value for key, value in raw.items() if key in allowed}
    ).validate()
    if (
        plan.run_id != "SAEA-A2T-SELECT-FILL-AGENTLOOP-104-RECOVERY-V5-EMBED"
        or plan.execution_profile != "bounded-discovery-probe"
        or plan.carrier_lock_key != AUDIO2TOOL_LOCK_KEY
        or plan.split_role != "discovery"
        or plan.split_identity_hash != authority.get("split_identity_hash")
        or plan.protocol_hash != protocol_sha256
        or plan.planned_model_calls != 104
        or plan.planned_gpu_hours != 0.2
        or plan.planned_speech_audio_seconds != 1
        or not plan.attempt_id
    ):
        raise RuntimeError("embedding ExecutionPlan identity or budget drift")
    if _sha256_json(asdict(plan)) != hashes.get("embedding_execution_plan_sha256"):
        raise RuntimeError("embedding ExecutionPlan SHA-256 drift")
    return plan


@dataclass(frozen=True)
class RuntimeSample:
    sample_id: str
    audio_ref: AudioRef
    audio_seconds: float


class DirectAdapter(TaskAdapter):
    def __init__(self, samples: Sequence[RuntimeSample], task_contract: str) -> None:
        self.samples = tuple(samples)
        self.task_contract = task_contract

    def load_split(self, split_id: str) -> tuple[RuntimeSample, ...]:
        if not split_id:
            raise RuntimeError("direct split id is empty")
        return self.samples

    def build_task_contract(self, sample: object, obs: object) -> str:
        return self.task_contract

    def assemble_prompt(self, sample: object, supply: object):
        if supply is not None:
            raise RuntimeError("M0 forbids supplied evidence")
        return (
            {"role": "system", "content": self.task_contract},
            {"role": "user", "content": []},
        )

    def score(self, sample: object, response: str) -> Mapping[str, object]:
        return {"scoring_deferred": True}

    def extract_consumption(self, sample: object, supply: object, response: str):
        return build_consumption_trace(span_id="full", supply=None, response_text=response)


def _physical_body(
    *, messages: Sequence[Mapping[str, object]], decoding_params: Mapping[str, object]
) -> dict[str, object]:
    """Mirror LlamaServerTransport's flattened physical body construction."""

    body: dict[str, object] = {"messages": [dict(item) for item in messages]}
    for key, value in decoding_params.items():
        if key == "id_slot" or key in body:
            raise RuntimeError("prepared decoding parameters may not preselect a slot")
        body[key] = value
    return body


def _prepared_request(
    launcher: object,
    *,
    phase: str,
    sample_id: str,
    binding: Mapping[str, object],
    body: Mapping[str, object],
    ground_sha256: str | None = None,
) -> object:
    packet_id = binding.get("packet_id")
    packet_sha256 = binding.get("sha256")
    if not isinstance(packet_id, str) or not packet_id or not _is_sha256(packet_sha256):
        raise RuntimeError("prepared request packet binding is malformed")
    return launcher.PreparedGenerationRequest.from_body(
        phase=phase,
        sample_id=sample_id,
        packet_id=packet_id,
        body=body,
        ground_sha256=ground_sha256,
    )


def _seal_stage_envelope(
    *,
    expected_stage: str,
    sample_id: str,
    request: object,
    response: object,
    observation: object,
    candidate: object,
    packet_sha256: str,
    split_identity_sha256: str,
) -> StageStateEnvelope:
    """Parse strict response bytes and seal all first-stage lineage directly."""

    response_bytes = getattr(response, "response_bytes", None)
    if not isinstance(response_bytes, bytes):
        raise RuntimeError("stage response bytes are unavailable")
    try:
        response_text = response_bytes.decode("ascii")
    except UnicodeDecodeError as error:
        raise RuntimeError("stage response is not ASCII") from error
    names = tuple(getattr(candidate, "tool_names", ()))
    response_format = getattr(request, "base_body", {}).get("response_format")
    common = {
        "sample_identity_sha256": hashlib.sha256(sample_id.encode("ascii")).hexdigest(),
        "split_identity_sha256": split_identity_sha256,
        "speech_packet_sha256": packet_sha256,
        "source_query_state_sha256": getattr(response, "source_query_state_sha256"),
        "source_response_sha256": getattr(response, "response_sha256"),
        "observation_state_sha256": getattr(observation, "state_sha256"),
        "observation_source_response_sha256": getattr(
            observation, "source_response_sha256"
        ),
        "source_request_body_sha256": getattr(response, "request_body_sha256"),
        "candidate_tool_names": names,
        "ground_sha256": getattr(request, "ground_sha256"),
        "response_schema_sha256": _sha256_json(response_format),
        "predecessor_envelope_sha256": None,
    }
    if expected_stage == JOINT_DRAFT_STAGE:
        calls = parse_call_array_response(response_text, allowed_tool_names=names)
        return build_joint_draft_stage_envelope(
            **common,
            calls=tuple(
                JointDraftCall.from_arguments(call.name, call.arguments)
                for call in calls
            ),
        )
    if expected_stage == SELECT_STAGE:
        selected = parse_select_response(response_text, candidate_tool_names=names)
        return build_select_stage_envelope(
            **common,
            occurrences=tuple(
                SelectOccurrence(f"occurrence-{index:02d}", name)
                for index, name in enumerate(selected, start=1)
            ),
        )
    raise RuntimeError("stage kind is not registered")


@dataclass
class PhaseState:
    phase: str
    plan: ExecutionPlan
    run_dir: Path
    session_receipt_path: Path
    client: FrozenCoreClient
    loop_sink: TraceSink | None
    output: object | None = None
    client_summary: Mapping[str, object] | None = None


class LocalSelectFillRuntime:
    """Concrete services, OpenJiuwen workflows, tracing, and sealing."""

    agent_executor_id = "openjiuwen-workflow-v1"
    slot_count = 2
    queue_depth = 4

    def __init__(
        self,
        *,
        authority: Mapping[str, object],
        protocol_config: Mapping[str, object],
        launcher_module: object,
    ) -> None:
        self.authority = authority
        self.protocol_config = protocol_config
        self.launcher = launcher_module
        self.repo = Path(getattr(launcher_module, "REPO")).resolve()
        self.hashes = authority.get("hashes")
        self.spec = authority.get("local_runtime")
        if not isinstance(self.hashes, Mapping) or not isinstance(self.spec, Mapping):
            raise RuntimeError("authority lacks local_runtime or hashes")
        if (
            _sha256_file(Path(__file__)) != self.hashes.get("local_runtime_factory_sha256")
            or _sha256_file(Path(str(getattr(launcher_module, "__file__"))))
            != self.hashes.get("coordinator_launcher_sha256")
        ):
            raise RuntimeError("authority does not bind the running code bytes")
        if (
            authority.get("core_protocol_sha256")
            != "db933dfc8975b30ac8ce07526aa074874e554c1fbc055b39ebbc7719d3e936bd"
            or authority.get("split_identity_hash")
            != getattr(launcher_module, "SPLIT_IDENTITY_HASH")
            or authority.get("bundle_split_identity_hash")
            != BUNDLE_SPLIT_IDENTITY_SHA256
            or authority.get("bundle_protocol_sha256") != BUNDLE_PROTOCOL_SHA256
        ):
            raise RuntimeError("contact split or protocol identity drift")
        self.data_root = Path(str(self.spec.get("data_root", ""))).resolve()
        self.runtime_root = Path(str(self.spec.get("runtime_root", ""))).resolve()
        if not self.data_root.is_dir() or not self.runtime_root.is_dir():
            raise RuntimeError("runtime roots are unavailable")
        mission_id = self.spec.get("mission_id")
        if not isinstance(mission_id, str) or not mission_id or not mission_id.isascii():
            raise RuntimeError("mission_id must be non-empty ASCII")
        self.mission_dir = self.data_root / "runs" / str(authority["run_id"]) / mission_id
        if self.mission_dir.exists():
            raise RuntimeError("one-shot mission already exists")
        source = self.spec.get("recovery_source")
        if not isinstance(source, Mapping):
            raise RuntimeError("authority lacks the V2 recovery source binding")
        source_mission_id = source.get("mission_id")
        if (
            source.get("run_id") != getattr(launcher_module, "SOURCE_RUN_ID")
            or not isinstance(source_mission_id, str)
            or not source_mission_id
            or not source_mission_id.isascii()
            or not isinstance(source.get("hashes"), Mapping)
        ):
            raise RuntimeError("V2 recovery source identity is malformed")
        self.recovery_source = source
        self.source_mission_dir = (
            self.data_root
            / "runs"
            / str(source["run_id"])
            / source_mission_id
        ).resolve()
        if (
            not self.source_mission_dir.is_dir()
            or self.data_root not in self.source_mission_dir.parents
        ):
            raise RuntimeError("V2 recovery source mission is unavailable or unconfined")
        roles = tuple(getattr(launcher_module, "GENERATION_PHASES"))
        self.plans = parse_execution_plans(
            authority, roles=roles, run_id=str(authority["run_id"])
        )
        self.embedding_plan = parse_embedding_execution_plan(
            authority, protocol_sha256=str(authority["core_protocol_sha256"])
        )
        self.preregistration_path = _require_file_hash(
            _confined_file(
                self.repo,
                self.spec.get("exposure_preregistration"),
                label="exposure preregistration",
            ),
            self.hashes.get("exposure_preregistration_sha256"),
            label="exposure preregistration",
        )
        self.composed = compose(self.repo, **COMMITTED_CONFIG_FRAGMENTS)
        if self.composed.config_hash != self.spec.get("composed_config_hash"):
            raise RuntimeError("composed configuration hash drift")
        values = self.composed.values
        if (
            values.get("arm") != GENERATION_ARM
            or values.get("a2t_semantic_agentloop_select_fill_split_identity_hash")
            != authority.get("split_identity_hash")
            or values.get("speech_packet_promotion_receipt_sha256")
            != getattr(launcher_module, "PROMOTION_RECEIPT_SHA256")
        ):
            raise RuntimeError("composed SELECT/FILL identity drift")
        self._load_roster_and_packets()
        self._load_knowledge_and_registry()
        self._load_receipts_and_gates()
        self.generation = self._generation_spec()
        self.embedding = self._embedding_spec()
        self.active: str | None = None
        self.session = None
        self.window_session_paths: dict[str, Path] = {}
        self.window_receipts: dict[str, Mapping[str, object]] = {}
        self.media_markers: dict[str, str] = {}
        self.phase_gates: dict[str, object] = {}
        self.phase_states: dict[str, PhaseState] = {}
        self.phase_adapters: dict[str, object] = {}
        self.prepared: dict[str, tuple[object, ...]] = {}
        self.sent_hash_by_phase_sample: dict[tuple[str, str], str] = {}
        self.observation_states: dict[str, object] = {}
        self.phase_candidates: dict[str, Mapping[str, object]] = {}
        self._send_lock = Lock()
        self.embedding_client_instance: EmbeddingClient | None = None
        self.embedding_attempt = None
        self.embedding_receipt: Mapping[str, object] | None = None
        self.recovered_prefix = None
        self.post_embedding_checkpoint_receipt: Mapping[str, object] | None = None

    def _load_roster_and_packets(self) -> None:
        launcher = self.launcher
        roster_path = _require_file_hash(
            Path(getattr(launcher, "ROSTER_PATH")),
            getattr(launcher, "ROSTER_SHA256"),
            label="fresh roster",
        )
        roster = _read_json(roster_path)
        rows = roster.get("items")
        if (
            roster.get("split_name") != launcher.SPLIT_ID
            or roster.get("split_role") != "discovery"
            or roster.get("split_identity_hash") != launcher.SPLIT_IDENTITY_HASH
            or roster.get("count") != 104
            or roster.get("contacts")
            != {"audio": 0, "model": 0, "network": 0, "scorer": 0}
            or not isinstance(rows, list)
            or len(rows) != 104
        ):
            raise RuntimeError("fresh roster identity or no-contact status drift")
        indexed: dict[str, Mapping[str, object]] = {}
        for row in rows:
            sample_id = row.get("sample_id") if isinstance(row, Mapping) else None
            if (
                not isinstance(sample_id, str)
                or not sample_id.isascii()
                or sample_id in indexed
                or not _is_sha256(row.get("audio_sha256"))
                or not isinstance(row.get("media_relpath"), str)
                or Path(str(row["media_relpath"])).is_absolute()
                or ".." in Path(str(row["media_relpath"])).parts
            ):
                raise RuntimeError("fresh roster row is malformed")
            indexed[sample_id] = row
        self.sample_ids = tuple(sorted(indexed))
        self.roster_rows = tuple(indexed[sample_id] for sample_id in self.sample_ids)
        preprocess_path = _require_file_hash(
            Path(getattr(launcher, "PREPROCESS_REPORT_PATH")),
            getattr(launcher, "PREPROCESS_REPORT_SHA256"),
            label="preprocess report",
        )
        preprocess = _read_json(preprocess_path)
        if (
            preprocess.get("count") != 104
            or preprocess.get("split_identity_hash") != launcher.SPLIT_IDENTITY_HASH
            or preprocess.get("subset_receipt_sha256") != launcher.ROSTER_SHA256
            or preprocess.get("promotion_receipt_sha256")
            != launcher.PROMOTION_RECEIPT_SHA256
            or preprocess.get("packets_promoted") != 104
        ):
            raise RuntimeError("preprocess report identity drift")
        promotion_path = _require_file_hash(
            Path(getattr(launcher, "PROMOTION_RECEIPT_PATH")),
            getattr(launcher, "PROMOTION_RECEIPT_SHA256"),
            label="packet promotion receipt",
        )
        promotion = _read_json(promotion_path)
        packet_rows = promotion.get("packets")
        if (
            promotion.get("count") != 104
            or promotion.get("split_identity_hash") != launcher.SPLIT_IDENTITY_HASH
            or promotion.get("subset_receipt_sha256") != launcher.ROSTER_SHA256
            or Path(str(promotion.get("feature_root", ""))).resolve()
            != Path(getattr(launcher, "PROMOTED_PACKET_ROOT")).resolve()
            or not isinstance(packet_rows, list)
            or len(packet_rows) != 104
        ):
            raise RuntimeError("promotion receipt identity drift")
        by_packet = {
            str(row["packet_id"]): row
            for row in packet_rows
            if isinstance(row, Mapping) and isinstance(row.get("packet_id"), str)
        }
        tokens: dict[str, int] = {}
        bindings: dict[str, dict[str, str]] = {}
        for sample_id, row in zip(self.sample_ids, self.roster_rows, strict=True):
            packet_id = sample_id.replace(":", "/", 1)
            packet = by_packet.get(packet_id)
            if (
                not isinstance(packet, Mapping)
                or packet.get("audio_sha256") != row.get("audio_sha256")
                or not _is_sha256(packet.get("packet_sha256"))
                or type(packet.get("n_tokens")) is not int
                or int(packet["n_tokens"]) <= 0
            ):
                raise RuntimeError(f"promoted packet drift for {sample_id!r}")
            bindings[sample_id] = {
                "packet_id": packet_id,
                "sha256": str(packet["packet_sha256"]),
            }
            tokens[packet_id] = int(packet["n_tokens"])
        if set(by_packet) != set(tokens):
            raise RuntimeError("promotion packet roster contains extras")
        self.packet_bindings = bindings
        self.speech_packet_tokens = tokens
        self.feature_root = Path(str(promotion["feature_root"]))
        self.samples = tuple(
            RuntimeSample(
                sample_id=sample_id,
                audio_ref=AudioRef(
                    path=str(row["media_relpath"]), sha256=str(row["audio_sha256"])
                ).validate(),
                audio_seconds=float(row["audio_seconds"]),
            )
            for sample_id, row in zip(self.sample_ids, self.roster_rows, strict=True)
        )
        prefixed = tuple(f"audio2tool/{sample_id}" for sample_id in self.sample_ids)
        if split_identity_hash(prefixed) != BUNDLE_SPLIT_IDENTITY_SHA256:
            raise RuntimeError("bundle split identity drift")
        self.verified_split = VerifiedSplit(
            name=launcher.SPLIT_ID,
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            split_role="discovery",
            ids=self.sample_ids,
            prefixed_ids=prefixed,
            identity_hash=BUNDLE_SPLIT_IDENTITY_SHA256,
        )

    def _load_knowledge_and_registry(self) -> None:
        lock = load_lock(umbrella_lock_path(self.repo))
        self.carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, self.data_root)
        registry = load_tool_registry(lock, self.data_root)
        self.registry_rows = registry
        self.registered_tool_names = tuple(sorted({row["tool_name"] for row in registry}))
        if len(self.registered_tool_names) != 152:
            raise RuntimeError("Audio2Tool registry must contain exactly 152 tools")
        self.task_contract = render_audio2tool_instruction(
            render_tool_schemas(lock, self.data_root)
        )
        from speech_aware_evidence_acquisition.rails.core_client import build_payload_binding

        self.binding = build_payload_binding(
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            samples=self.samples,
            data_root=self.data_root,
            carrier_root=self.carrier_root,
        )
        assets = load_frozen_semantic_runtime_assets(repo=self.repo, data_root=self.data_root)
        self.index = assets.index
        if self.index.registry_tool_names != self.registered_tool_names:
            raise RuntimeError("semantic index and live registry differ")
        if self.index.index_sha256 != self.hashes.get("semantic_index_sha256"):
            raise RuntimeError("semantic index SHA-256 drift")
        corpus_path = _require_file_hash(
            self.repo / "knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json",
            self.hashes.get("canonical_contract_corpus_sha256"),
            label="canonical contract corpus",
        )
        canonical = CanonicalFamilyGround.from_path(
            corpus_path, compatibility_rules=assets.compatibility_rules
        )
        cards = tuple(
            ToolSemanticCard(
                tool_name=contract.tool_name,
                choose_semantics=contract.operation,
                avoid_semantics="Choose only for this exact public operation.",
                signature=contract.tool_name
                + "("
                + ", ".join(f"{key}: {kind}" for key, kind in contract.types)
                + ")",
                constraints=contract.constraints,
                legal_argument_key_sets=contract.legal_key_skeletons,
                compatibility_rules=tuple(
                    rule
                    for rule in assets.compatibility_rules
                    if rule.tool_name == contract.tool_name
                ),
                role_guidance=(),
                examples=(),
                text="Frozen public tool contract.",
            )
            for contract in canonical.contracts_by_tool.values()
        )
        self.corpus = ExecutableSemanticCardCorpus(
            text="Frozen public Audio2Tool execution corpus.",
            sha256=_sha256_file(corpus_path),
            tool_cards=cards,
            task_cards=(
                TaskSemanticCard("multi-call-ordering", "Preserve call order."),
                TaskSemanticCard("correction-resolution", "Use final corrections."),
                TaskSemanticCard("implicit-end-state-resolution", "Use the requested end state."),
                TaskSemanticCard("multiturn-carryover", "Use relevant earlier facts."),
            ),
            report={"source_sha256": _sha256_file(corpus_path)},
        )
        self.contracts_by_tool = canonical.contracts_by_tool
        self.canonicalizers = canonical.canonicalizers
        snapshot_path = _require_file_hash(
            self.repo / "knowledge/audio2tool/semantic-agentloop-runtime-v1/runner-snapshot.json",
            self.hashes.get("runner_snapshot_sha256"),
            label="runner snapshot",
        )
        self.snapshot = KnowledgeSnapshot.from_frozen_json(_read_json(snapshot_path))

    def _load_receipts_and_gates(self) -> None:
        values = self.composed.values
        generation_path = _require_file_hash(
            _confined_file(
                self.repo / "docs",
                self.spec.get("generation_runtime_receipt"),
                label="generation runtime receipt",
            ),
            self.hashes.get("generation_runtime_receipt_sha256"),
            label="generation runtime receipt",
        )
        if self.spec.get("generation_runtime_receipt") != runtime_receipt_relpath(values):
            raise RuntimeError("generation runtime receipt differs from configuration")
        self.generation_runtime_receipt_path = generation_path
        self.generation_runtime_receipt = load_runtime_receipt(generation_path)
        embedding_path = _require_file_hash(
            _confined_file(
                self.repo / "docs",
                self.spec.get("embedding_runtime_receipt"),
                label="embedding runtime receipt",
            ),
            self.hashes.get("embedding_runtime_receipt_sha256"),
            label="embedding runtime receipt",
        )
        self.embedding_runtime_receipt = load_runtime_receipt(embedding_path)
        gguf = self.embedding_runtime_receipt.get("gguf_files")
        record = gguf[0] if isinstance(gguf, list) and len(gguf) == 1 else None
        if (
            not isinstance(record, Mapping)
            or record.get("path") != EMBEDDING_MODEL_RELPATH
            or record.get("bytes") != EMBEDDING_MODEL_BYTES
            or record.get("sha256") != self.hashes.get("embedding_gguf_sha256")
        ):
            raise RuntimeError("embedding runtime receipt GGUF drift")
        self.embedding_runtime_receipt_path = embedding_path
        self.gate = FrozenCoreGate.for_study_repo(
            self.repo,
            self.data_root,
            self.runtime_root,
            runtime_receipt_relpath=str(self.spec["generation_runtime_receipt"]),
            expected_model_lock_key=str(values["model_lock_key"]),
            model_root=Path(str(values["model_materialization_root"])),
            d1_media_supplement_relpath=d1_media_supplement_relpath(values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(values),
        )
        self.embedding_gate = FrozenCoreGate.for_study_repo(
            self.repo,
            self.data_root,
            self.runtime_root,
            runtime_receipt_relpath=EMBEDDING_RUNTIME_RECEIPT,
            expected_model_lock_key=EMBEDDING_MODEL_LOCK_KEY,
            model_root=self.data_root,
            d1_media_supplement_relpath=d1_media_supplement_relpath(values),
            d1_media_supplement_sha256=d1_media_supplement_sha256(values),
        )

    def _generation_spec(self) -> Mapping[str, object]:
        value = self.spec.get("generation")
        expected = self.composed.values
        if not isinstance(value, Mapping):
            raise RuntimeError("generation service spec is missing")
        args = tuple(value.get("server_args", ()))
        if (
            value.get("base_url") != "http://127.0.0.1:8090"
            or args != tuple(expected.get("server_args", ()))
            or value.get("prompt_order") != "speech-query-prefix-v2"
            or value.get("decoding_params") != expected.get("decoding_params")
            or args[args.index("-c") + 1] != "65536"
            or args[args.index("-np") + 1] != "2"
        ):
            raise RuntimeError("generation service is not the pinned two-slot profile")
        env = value.get("server_env")
        if (
            not isinstance(env, Mapping)
            or env.get("LLAMA_SPEECH_FEATURE_ROOT") != str(self.feature_root)
            or set(env) != {"LLAMA_SPEECH_FEATURE_ROOT", "LLAMA_SPEECH_DECODER_SHA256"}
        ):
            raise RuntimeError("generation service does not bind the packet root")
        return value

    def _embedding_spec(self) -> Mapping[str, object]:
        value = self.spec.get("embedding")
        if not isinstance(value, Mapping):
            raise RuntimeError("embedding service spec is missing")
        args = tuple(value.get("server_args", ()))
        expected = (
            "--embedding", "--pooling", "last", "-ngl", "0", "-c", "4096",
            "-b", "4096", "-ub", "4096", "-np", "1", "-t", "16",
        )
        if (
            value.get("base_url") != "http://127.0.0.1:8082"
            or args != expected
            or value.get("expected_dim") != EMBEDDING_DIMENSION
            or value.get("physical_batch_size") != 32
        ):
            raise RuntimeError("embedding service is not the pinned batch-32 profile")
        return value

    def _run_decoding(self) -> dict[str, object]:
        value = dict(self.generation["decoding_params"])
        value.pop("id_slot", None)
        if value != {"temperature": 0, "seed": 20260803, "max_tokens": 1024}:
            raise RuntimeError("generation decoding parameters drift")
        return value

    def _source_file(self, key: str, relpath: str) -> tuple[Path, str]:
        hashes = self.recovery_source.get("hashes")
        expected = hashes.get(key) if isinstance(hashes, Mapping) else None
        path = (self.source_mission_dir / relpath).resolve()
        if self.source_mission_dir not in path.parents:
            raise RuntimeError(f"source recovery path {key!r} escapes its mission")
        _require_file_hash(path, expected, label=f"source recovery {key}")
        return path, str(expected)

    def rehydrate_completed_prefix(self) -> object:
        """Recover V2 M0/OBS bytes and prove their lineage without new I/O."""

        if self.recovered_prefix is not None:
            return self.recovered_prefix
        launcher = self.launcher
        m0_requests = self.prepare_generation_phase(
            launcher.M0_PHASE,
            sample_ids=self.sample_ids,
            packet_bindings=self.packet_bindings,
        )
        obs_requests = self.prepare_generation_phase(
            launcher.OBS_PHASE,
            sample_ids=self.sample_ids,
            packet_bindings=self.packet_bindings,
        )
        send_path, send_hash = self._source_file(
            "generation_send_accounting_sha256", "generation-send-accounting.jsonl"
        )
        sends = _load_recovery_send_accounting(
            send_path,
            expected_sha256=send_hash,
            launcher=launcher,
            sample_ids=self.sample_ids,
        )
        m0_preflight_path, m0_preflight_hash = self._source_file(
            "m0_preflight_sha256", "preflight/M0_DIRECT.json"
        )
        obs_preflight_path, obs_preflight_hash = self._source_file(
            "obs_preflight_sha256", "preflight/OBS_SEMANTIC_STATE.json"
        )
        m0_preflight = _load_recovery_preflight(
            m0_preflight_path,
            expected_sha256=m0_preflight_hash,
            launcher=launcher,
            phase=launcher.M0_PHASE,
            requests=m0_requests,
        )
        obs_preflight = _load_recovery_preflight(
            obs_preflight_path,
            expected_sha256=obs_preflight_hash,
            launcher=launcher,
            phase=launcher.OBS_PHASE,
            requests=obs_requests,
        )
        m0_trace_path, m0_trace_hash = self._source_file(
            "m0_trace_sha256",
            f"m0-direct/{launcher.SOURCE_RUN_ID}.trace.jsonl",
        )
        obs_trace_path, obs_trace_hash = self._source_file(
            "obs_trace_sha256",
            f"obs-semantic-state/agent-loop/{launcher.SOURCE_RUN_ID}.trace.jsonl",
        )
        m0_output = _load_recovery_trace_rows(
            launcher=launcher,
            phase=launcher.M0_PHASE,
            trace_path=m0_trace_path,
            expected_trace_sha256=m0_trace_hash,
            requests=m0_requests,
            packet_bindings=self.packet_bindings,
            sent_body_sha256_by_sample=sends[launcher.M0_PHASE],
        )
        obs_output = _load_recovery_trace_rows(
            launcher=launcher,
            phase=launcher.OBS_PHASE,
            trace_path=obs_trace_path,
            expected_trace_sha256=obs_trace_hash,
            requests=obs_requests,
            packet_bindings=self.packet_bindings,
            sent_body_sha256_by_sample=sends[launcher.OBS_PHASE],
        )
        observations = launcher._validate_observations(
            self.parse_observations(obs_output),
            sample_ids=self.sample_ids,
        )
        if len({item.state_sha256 for item in observations.values()}) != 104:
            raise RuntimeError("source OBS state identities are not unique")
        authority_path, authority_hash = self._source_file(
            "authority_binding_sha256", "authority-binding.json"
        )
        source_authority = _read_json(authority_path)
        source_plans = source_authority.get("contact_plans")
        source_m0_raw = (
            source_plans.get(launcher.M0_PHASE)
            if isinstance(source_plans, Mapping)
            else None
        )
        if not isinstance(source_m0_raw, Mapping):
            raise RuntimeError("source authority lacks its M0 execution plan")
        try:
            source_m0_plan = ExecutionPlan(**source_m0_raw).validate()
        except (TypeError, ValueError) as error:
            raise RuntimeError("source M0 execution plan is malformed") from error
        if (
            source_m0_plan.run_id != launcher.SOURCE_RUN_ID
            or source_m0_plan.carrier_lock_key != AUDIO2TOOL_LOCK_KEY
            or source_m0_plan.split_role != "discovery"
            or source_m0_plan.split_identity_hash != launcher.SPLIT_IDENTITY_HASH
            or source_m0_plan.protocol_hash
            != "db933dfc8975b30ac8ce07526aa074874e554c1fbc055b39ebbc7719d3e936bd"
            or source_m0_plan.planned_model_calls != 624
            or source_m0_plan.planned_speech_audio_seconds != 3400
            or source_m0_plan.planned_gpu_hours != 4.0
            or not source_m0_plan.attempt_id
        ):
            raise RuntimeError("source M0 execution plan identity drift")
        source_session_path, source_session_hash = self._source_file(
            "generation_pre_embedding_session_receipt_sha256",
            "services/generation-pre-embedding/session-receipt.json",
        )
        source_attempt_path = (
            self.data_root
            / "attempts"
            / source_m0_plan.run_id
            / f"{source_m0_plan.attempt_id}.json"
        ).resolve()
        source_hashes = self.recovery_source.get("hashes")
        source_attempt_hash = (
            source_hashes.get("m0_attempt_sha256")
            if isinstance(source_hashes, Mapping)
            else None
        )
        _require_file_hash(
            source_attempt_path,
            source_attempt_hash,
            label="source M0 attempt",
        )
        source_attempt = _read_json(source_attempt_path)
        actual = source_attempt.get("actual")
        actual_audio_seconds = (
            actual.get("audio_seconds") if isinstance(actual, Mapping) else None
        )
        if (
            source_attempt.get("run_id") != source_m0_plan.run_id
            or source_attempt.get("attempt_id") != source_m0_plan.attempt_id
            or source_attempt.get("state") != "ABORTED"
            or not isinstance(actual, Mapping)
            or actual.get("calls") != 104
            or isinstance(actual_audio_seconds, bool)
            or not isinstance(actual_audio_seconds, (int, float))
            or abs(float(actual_audio_seconds) - 549.489916) > 1e-6
        ):
            raise RuntimeError("source M0 attempt state or cost drift")
        self.source_m0_plan = source_m0_plan
        self.source_m0_trace_path = m0_trace_path
        self.source_authority_binding_path = authority_path
        self.source_generation_session_receipt_path = source_session_path
        self.source_m0_attempt_path = source_attempt_path
        embedding_path, embedding_hash = self._source_file(
            "embedding_tool_receipt_sha256", "services/embedding/tool-receipt.json"
        )
        source_embedding = _read_json(embedding_path)
        if (
            source_embedding.get("status") != "FINALIZED"
            or source_embedding.get("logical_items") != 104
            or source_embedding.get("physical_requests") != 4
        ):
            raise RuntimeError("source embedding receipt is not the completed 104/4 pass")
        source_report = {
            "schema": "saea-a2t-select-fill-recovered-prefix-v1",
            "source_run_id": launcher.SOURCE_RUN_ID,
            "source_mission": str(self.source_mission_dir),
            "sample_count": 104,
            "m0_responses": 104,
            "obs_responses": 104,
            "obs_states": 104,
            "source_generation_contacts": 208,
            "source_embedding_logical_items": 104,
            "source_embedding_physical_requests": 4,
            "source_embedding_vectors_persisted": False,
            "new_generation_contacts": 0,
            "new_embedding_contacts": 0,
            "response_meanings_opened": False,
            "artifacts": {
                "send_accounting_sha256": send_hash,
                "m0_preflight_sha256": m0_preflight_hash,
                "obs_preflight_sha256": obs_preflight_hash,
                "m0_trace_sha256": m0_trace_hash,
                "obs_trace_sha256": obs_trace_hash,
                "embedding_tool_receipt_sha256": embedding_hash,
                "authority_binding_sha256": authority_hash,
                "generation_pre_embedding_session_receipt_sha256": source_session_hash,
                "m0_attempt_sha256": str(source_attempt_hash),
            },
        }
        self.recovery_source_report = source_report
        self.recovered_prefix = launcher.RecoveredPrefixArtifacts(
            m0=launcher.GenerationPhaseRun(
                launcher.M0_PHASE, m0_requests, m0_preflight, m0_output
            ),
            obs=launcher.GenerationPhaseRun(
                launcher.OBS_PHASE, obs_requests, obs_preflight, obs_output
            ),
            observations=observations,
            source_report_sha256=_sha256_json(source_report),
        )
        return self.recovered_prefix

    def assert_contact_ready_preflight(self) -> Mapping[str, object]:
        if self.mission_dir.exists():
            raise RuntimeError("mission already exists")
        study_commit = require_clean_study_repo(self.repo)
        recovered = self.rehydrate_completed_prefix()
        for plan in (*self.plans.values(), self.embedding_plan):
            attempt = self.data_root / "attempts" / plan.run_id / f"{plan.attempt_id}.json"
            if attempt.exists():
                raise RuntimeError(f"one-shot attempt already exists: {plan.attempt_id}")
        for plan in self.plans.values():
            self.gate.assert_model_touch_allowed(plan, full_hash=True)
        self.embedding_gate.assert_model_touch_allowed(self.embedding_plan, full_hash=True)
        self.gate.verify_media_identity(
            AUDIO2TOOL_LOCK_KEY,
            {
                sample_id: (
                    self.binding.media_relpaths[sample_id],
                    self.binding.sample_facts[sample_id][0],
                )
                for sample_id in self.binding.allowed_sample_ids
            },
        )
        return {
            "schema": "saea-a2t-select-fill-contact-ready-preflight-v1",
            "status": "CONTACT_READY_NO_CONTACT",
            "run_id": self.authority["run_id"],
            "study_commit": study_commit,
            "sample_count": 104,
            "generation_plan_count": 4,
            "generation_contact_ceiling": 416,
            "embedding_logical_items": 104,
            "embedding_physical_requests": 4,
            "embedding_speech_audio_seconds": 0,
            "reused_generation_contacts": 208,
            "recovered_prefix_sha256": recovered.source_report_sha256,
            "bundle_split_identity_sha256": BUNDLE_SPLIT_IDENTITY_SHA256,
            "contacts_made": 0,
        }

    def assert_attempt_unopened(self) -> None:
        for plan in (*self.plans.values(), self.embedding_plan):
            path = self.data_root / "attempts" / plan.run_id / f"{plan.attempt_id}.json"
            if path.exists():
                raise RuntimeError(f"one-shot attempt already exists: {plan.attempt_id}")
        self.mission_dir.mkdir(parents=True)
        if self.recovered_prefix is None:
            self.rehydrate_completed_prefix()
        _write_json(
            self.mission_dir / "authority-binding.json",
            {
                "authority_sha256": _sha256_json(self.authority),
                "protocol_config": self.protocol_config,
                "contact_plans": {key: asdict(value) for key, value in self.plans.items()},
                "embedding_plan": asdict(self.embedding_plan),
                "recovery_source": dict(self.recovery_source),
                "recovered_prefix_sha256": self.recovered_prefix.source_report_sha256,
                "bundle_split_identity_sha256": BUNDLE_SPLIT_IDENTITY_SHA256,
                "bundle_protocol_sha256": BUNDLE_PROTOCOL_SHA256,
            },
        )
        _write_json(
            self.mission_dir / "recovered-prefix-report.json",
            self.recovery_source_report,
        )

    def _post_bytes(self, url: str, body: bytes, timeout: float) -> bytes:
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()

    def _get_json(self, endpoint: str) -> Mapping[str, object]:
        base = str(self.generation["base_url"])
        with urllib.request.urlopen(
            base + endpoint, timeout=float(self.generation.get("timeout_seconds", 900))
        ) as response:
            raw = response.read()
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, Mapping):
            raise RuntimeError(f"loopback endpoint {endpoint} returned no object")
        return value

    def _post_json(self, endpoint: str, payload: Mapping[str, object]) -> object:
        raw = self._post_bytes(
            str(self.generation["base_url"]) + endpoint,
            _canonical_bytes(payload),
            float(self.generation.get("timeout_seconds", 900)),
        )
        return json.loads(raw.decode("utf-8"))

    def start_generation(self, window: str) -> None:
        if self.active is not None or window != "post-embedding":
            raise RuntimeError("generation service order violation")
        directory = self.mission_dir / "services" / f"generation-{window}"
        receipt = directory / "session-receipt.json"
        self.session = start_session(
            runtime_root=self.runtime_root,
            data_root=self.data_root,
            runtime_receipt=self.generation_runtime_receipt,
            host="127.0.0.1",
            port=GENERATION_PORT,
            session_id=f"{self.authority['run_id']}-{window}",
            extra_argv=tuple(self.generation["server_args"]),
            extra_env=dict(self.generation["server_env"]),
            receipt_path=receipt,
            ready_timeout_seconds=float(self.generation.get("ready_timeout_seconds", 600)),
            server_log_path=directory / "server.log",
            role="inference",
            model_root=Path(str(self.composed.values["model_materialization_root"])),
        )
        props = self._get_json("/props")
        marker = props.get("media_marker")
        settings = props.get("default_generation_settings")
        if (
            not isinstance(marker, str)
            or not marker.isascii()
            or not isinstance(settings, Mapping)
            or settings.get("n_ctx") != 32768
        ):
            raise RuntimeError("generation /props profile drift")
        self.media_markers[window] = marker
        self.window_session_paths[window] = receipt
        self.active = f"generation:{window}"

    def stop_generation(self, window: str) -> None:
        if self.active != f"generation:{window}" or self.session is None:
            raise RuntimeError("generation service is not active")
        stop_path = self.mission_dir / "services" / f"generation-{window}" / "stop.json"
        stop = stop_session(
            self.session,
            runtime_receipt=self.generation_runtime_receipt,
            runtime_root=self.runtime_root,
            force_after_timeout=True,
            receipt_path=stop_path,
        )
        self.window_receipts[window] = {
            "session_receipt_sha256": _sha256_file(self.window_session_paths[window]),
            "stop_receipt_sha256": _sha256_file(stop_path),
            "stop": stop,
        }
        self.session = None
        self.active = None

    def start_embedding(self) -> None:
        if self.active is not None:
            raise RuntimeError("embedding and generation may not coexist")
        self.embedding_gate.assert_model_touch_allowed(self.embedding_plan, full_hash=True)
        self.embedding_attempt = AttemptStore(self.data_root / "attempts").open_attempt(
            self.embedding_plan.run_id,
            self.embedding_plan.attempt_id or "",
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            reserved_calls=104,
            reserved_audio_seconds=1.0,
        )
        directory = self.mission_dir / "services" / "embedding"
        receipt = directory / "session-receipt.json"
        self.session = start_session(
            runtime_root=self.runtime_root,
            data_root=self.data_root,
            runtime_receipt=self.embedding_runtime_receipt,
            host="127.0.0.1",
            port=EMBEDDING_PORT,
            session_id=f"{self.authority['run_id']}-embedding",
            extra_argv=tuple(self.embedding["server_args"]),
            receipt_path=receipt,
            ready_timeout_seconds=float(self.embedding.get("ready_timeout_seconds", 1800)),
            server_log_path=directory / "server.log",
            model_root=self.data_root,
        )
        self.embedding_client_instance = EmbeddingClient(
            base_url=str(self.embedding["base_url"]),
            timeout_seconds=float(self.embedding.get("timeout_seconds", 600)),
            expected_dim=EMBEDDING_DIMENSION,
            require_marker_verification=False,
        )
        self.embedding_client_instance.verify_media_marker()
        self.window_session_paths["embedding"] = receipt
        self.active = "embedding"

    def embed_batch(self, batch: Sequence[tuple[str, str]]) -> Mapping[str, tuple[float, ...]]:
        if (
            self.active != "embedding"
            or self.embedding_client_instance is None
            or self.embedding_attempt is None
            or not 1 <= len(batch) <= 32
        ):
            raise RuntimeError("embedding batch is outside its active governed window")
        state = self.embedding_attempt._read()  # noqa: SLF001 - text-only durable meter
        if state.get("state") != STATE_OPENED or not isinstance(state.get("actual"), dict):
            raise RuntimeError("embedding attempt state is malformed")
        state["actual"]["calls"] += len(batch)  # type: ignore[index]
        if state["actual"]["calls"] > 104:  # type: ignore[index]
            raise RuntimeError("embedding logical contact ceiling exceeded")
        self.embedding_attempt._write(state)  # noqa: SLF001 - atomic pre-I/O accounting
        vectors = self.embedding_client_instance.embed_text_batch(
            tuple((contact_id, text, "") for contact_id, text in batch)
        )
        return {
            vector.contact_id: tuple(float(value) for value in vector.values)
            for vector in vectors
        }

    def stop_embedding(self) -> None:
        client = self.embedding_client_instance
        if (
            self.active != "embedding"
            or self.session is None
            or client is None
            or self.embedding_attempt is None
            or client.http_request_count != 4
            or len(client.contacts) != 104
        ):
            raise RuntimeError("embedding phase must complete 104 items in four requests")
        client_summary = client.close()
        self.embedding_attempt.mark_finalized()
        stop_path = self.mission_dir / "services/embedding/stop.json"
        stop = stop_session(
            self.session,
            runtime_receipt=self.embedding_runtime_receipt,
            runtime_root=self.runtime_root,
            force_after_timeout=True,
            receipt_path=stop_path,
        )
        self.embedding_receipt = {
            "status": "FINALIZED",
            "logical_items": 104,
            "physical_requests": 4,
            "client": client_summary,
            "stop": stop,
        }
        _write_json(self.mission_dir / "services/embedding/tool-receipt.json", self.embedding_receipt)
        self.session = None
        self.active = None

    def _phase_gate(self, phase: str):
        gate = self.phase_gates.get(phase)
        if gate is None:
            gate = self.launcher.WholePhaseRequestGate(
                expected_sample_ids=self.sample_ids,
                speech_packet_tokens=self.speech_packet_tokens,
                get_json=self._get_json,
                post_json=self._post_json,
                send=lambda url, body, owned_phase=phase: self._durable_send(
                    owned_phase, url, body
                ),
            )
            self.phase_gates[phase] = gate
        return gate

    def _durable_send(self, phase: str, url: str, body: bytes) -> bytes:
        digest = hashlib.sha256(body).hexdigest()
        sample_id = None
        for request in self.prepared.get(phase, ()):
            if digest in request.body_sha256_by_slot:
                sample_id = request.sample_id
                break
        if sample_id is None:
            raise RuntimeError("send body does not belong to the prepared phase")
        path = self.mission_dir / "generation-send-accounting.jsonl"
        record = {
            "phase": phase,
            "sample_id": sample_id,
            "body_sha256": digest,
            "status": "CONSUMED_BEFORE_IO",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._send_lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="ascii", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self.sent_hash_by_phase_sample[(phase, sample_id)] = digest
        response = self._post_bytes(
            url, body, float(self.generation.get("timeout_seconds", 900))
        )
        return response

    def generation_send_accounting(self) -> Mapping[str, int]:
        """Return actual, pre-I/O-durable physical sends by generation phase."""

        return {
            phase: sum(
                1
                for recorded_phase, _sample_id in self.sent_hash_by_phase_sample
                if recorded_phase == phase
            )
            for phase in self.launcher.GENERATION_PHASES
        }

    def _new_phase_state(self, phase: str, receipt: object, *, loop: bool) -> PhaseState:
        if not isinstance(self.active, str) or not self.active.startswith("generation:"):
            raise RuntimeError("generation service is not active")
        window = self.active.split(":", 1)[1]
        gate = self._phase_gate(phase)
        timeout = float(self.generation.get("timeout_seconds", 900))
        transport = LlamaServerTransport(
            base_url=str(self.generation["base_url"]),
            data_root=self.data_root,
            session=self.session,
            runtime_receipt=self.generation_runtime_receipt,
            runtime_root=self.runtime_root,
            timeout_seconds=timeout,
            post=lambda url, body: gate.send_preflighted(receipt, body, url=url),
            prompt_order=str(self.generation["prompt_order"]),
            feature_root=self.feature_root,
        )
        run_dir = self.mission_dir / phase.casefold().replace("_", "-")
        run_dir.mkdir(parents=True)
        client = FrozenCoreClient(
            plan=self.plans[phase],
            gate=self.gate,
            transport=transport,
            run_dir=run_dir,
            binding=self.binding,
            arm=GENERATION_ARM,
            request_id_prefix=phase.casefold().replace("_", "-"),
            speech_feature_root=self.feature_root,
            speech_packet_bindings=self.packet_bindings,
        )
        state = PhaseState(
            phase=phase,
            plan=self.plans[phase],
            run_dir=run_dir,
            session_receipt_path=self.window_session_paths[window],
            client=client,
            loop_sink=(TraceSink(run_dir / "agent-loop", str(self.authority["run_id"])) if loop else None),
        )
        self.phase_states[phase] = state
        return state

    def prepare_generation_phase(
        self,
        phase: str,
        *,
        sample_ids: tuple[str, ...],
        packet_bindings: Mapping[str, Mapping[str, object]],
        observations: Mapping[str, object] | None = None,
        candidates: Mapping[str, object] | None = None,
        predecessor_states: Mapping[str, StageStateEnvelope] | None = None,
    ) -> tuple[object, ...]:
        if sample_ids != self.sample_ids or packet_bindings != self.packet_bindings:
            raise RuntimeError("generation preparation roster or packet drift")
        decode = self._run_decoding()
        requests: list[object] = []
        if phase == self.launcher.M0_PHASE:
            adapter: object = DirectAdapter(self.samples, self.task_contract)
            for sample_id in sample_ids:
                binding = packet_bindings[sample_id]
                messages = (
                    {"role": "system", "content": self.task_contract},
                    {"role": "user", "content": [{
                        "type": "input_speech_features",
                        "speech_features": {**binding, "role": "query"},
                    }]},
                )
                requests.append(_prepared_request(
                    self.launcher, phase=phase, sample_id=sample_id, binding=binding,
                    body=_physical_body(messages=messages, decoding_params=decode),
                ))
        elif phase == self.launcher.OBS_PHASE:
            adapter = FreshSemanticPhaseAdapter(
                split_id=self.launcher.SPLIT_ID,
                samples=self.samples,
                phase=OBSERVATION_PHASE,
                registered_tool_names=self.registered_tool_names,
            )
            response_format = observation_response_format()
            instruction = adapter.build_task_contract(self.samples[0], None)
            for sample_id in sample_ids:
                binding = packet_bindings[sample_id]
                messages = (
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": [
                        {"type": "input_speech_features", "speech_features": {**binding, "role": "query"}},
                        {"type": "text", "text": f"[agent control {OBSERVATION_CONTACT_ID}] {instruction}"},
                    ]},
                )
                effective = {**decode, "max_tokens": 768, "temperature": 0, "response_format": response_format}
                requests.append(_prepared_request(
                    self.launcher, phase=phase, sample_id=sample_id, binding=binding,
                    body=_physical_body(messages=messages, decoding_params=effective),
                ))
        else:
            if (
                observations is None
                or candidates is None
                or set(observations) != set(sample_ids)
                or set(candidates) != set(sample_ids)
            ):
                raise RuntimeError("SELECT/FILL phases require complete OBS and K32 state")
            self.phase_candidates[phase] = candidates
            material: dict[str, PhaseMaterial] = {}
            for sample_id in sample_ids:
                observation = observations[sample_id]
                candidate = candidates[sample_id]
                names = tuple(candidate.tool_names)
                predecessor = predecessor_states.get(sample_id) if predecessor_states else None
                if phase == self.launcher.SELECT_PHASE:
                    ground = build_routing_knowledge_ground(self.corpus, names)
                    response_format = ground.response_format
                elif phase in {self.launcher.JOINT_PHASE, self.launcher.REVISE_PHASE}:
                    ground = build_joint_knowledge_ground(
                        self.corpus, names,
                        contracts_by_tool=self.contracts_by_tool,
                        canonicalizers=self.canonicalizers,
                    )
                    response_format = audio2tool_outer_call_array_response_format(
                        self.registry_rows,
                        names,
                        schema_name="audio2tool_joint_candidate_outer_calls",
                        min_calls=1,
                        max_calls=PARAMETER_MAX_OCCURRENCES,
                    )
                elif phase == self.launcher.FILL_PHASE:
                    if predecessor is None or predecessor.stage != SELECT_STAGE:
                        raise RuntimeError("FILL requires a verified SELECT predecessor")
                    selected = tuple(item.tool_name for item in predecessor.payload.occurrences)
                    ground = build_parameter_knowledge_ground(
                        self.corpus, selected,
                        contracts_by_tool=self.contracts_by_tool,
                        canonicalizers=self.canonicalizers,
                    )
                    response_format = (
                        audio2tool_locked_outer_call_array_response_format(
                            self.registry_rows,
                            selected,
                            schema_name="audio2tool_parameter_locked_outer_calls",
                        )
                    )
                else:
                    raise RuntimeError("generation phase is unknown")
                observation_state = self.observation_states.get(sample_id)
                if observation_state is None:
                    raise RuntimeError("canonical OBS state is unavailable")
                observation_json = _canonical_bytes(observation_state.as_json()).decode("ascii")
                if _sha256_json(observation_state.as_json()) != observation.state_sha256:
                    raise RuntimeError("canonical OBS state hash drift")
                material[sample_id] = PhaseMaterial(
                    sample_id=sample_id,
                    phase=phase,
                    candidate_tool_names=names,
                    ground_text=ground.text,
                    ground_sha256=ground.text_sha256,
                    response_format=response_format,
                    response_format_sha256=_sha256_json(response_format),
                    observation_state_json=observation_json,
                    observation_state_sha256=_sha256_json(json.loads(observation_json)),
                    observation_source_response_sha256=observation.source_response_sha256,
                    predecessor=predecessor,
                )
            adapter = FreshSelectFillPhaseAdapter(
                split_id=self.launcher.SPLIT_ID,
                samples=self.samples,
                phase=phase,
                material=material,
            )
            for sample_id in sample_ids:
                rendered = adapter.render_request(
                    sample_id,
                    packet_bindings[sample_id],
                    prompt_order=str(self.generation["prompt_order"]),
                    decoding_params=decode,
                )
                requests.append(_prepared_request(
                    self.launcher,
                    phase=phase,
                    sample_id=sample_id,
                    binding=packet_bindings[sample_id],
                    body=_physical_body(
                        messages=rendered.transport_messages,
                        decoding_params=rendered.decoding_params,
                    ),
                    ground_sha256=material[sample_id].ground_sha256,
                ))
        self.phase_adapters[phase] = adapter
        self.prepared[phase] = tuple(requests)
        return tuple(requests)

    def preflight_generation_phase(self, phase: str, requests: Sequence[object]) -> object:
        if tuple(requests) != self.prepared.get(phase):
            raise RuntimeError("phase preflight did not receive its prepared requests")
        receipt = self._phase_gate(phase).preflight_phase(phase, requests)
        _write_json(
            self.mission_dir / "preflight" / f"{phase}.json",
            {
                "phase": phase,
                "status": receipt.status,
                "receipt_sha256": receipt.receipt_sha256,
                "sample_ids": list(receipt.sample_ids),
                "allowed_body_hashes_by_slot": [list(row) for row in receipt.allowed_body_hashes_by_slot],
                "audits": [audit.__dict__ for audit in receipt.audits],
            },
        )
        return receipt

    def dispatch_generation_phase(
        self, phase: str, requests: Sequence[object], preflight: object
    ) -> object:
        if tuple(requests) != self.prepared.get(phase):
            raise RuntimeError("dispatch request material drift")
        loop = phase != self.launcher.M0_PHASE
        state = self._new_phase_state(phase, preflight, loop=loop)
        adapter = self.phase_adapters[phase]
        if phase == self.launcher.M0_PHASE:
            summary = run_direct_phase(
                adapter=adapter,
                core_client=state.client,
                split_id=self.launcher.SPLIT_ID,
                speech_packet_bindings=self.packet_bindings,
                slot_count=2,
                decoding_params=self._run_decoding(),
            )
        elif phase == self.launcher.OBS_PHASE:
            summary = run_observation_phase(
                phase=OBSERVATION_PHASE,
                data_root=self.data_root,
                plan=state.plan,
                adapter=adapter,
                core_client=state.client,
                split_id=self.launcher.SPLIT_ID,
                knowledge_snapshot=self.snapshot,
                speech_packet_bindings=self.packet_bindings,
                trace_sink=state.loop_sink,
                decoding_params=self._run_decoding(),
            )
        else:
            summary = run_select_fill_phase(
                phase=phase,
                data_root=self.data_root,
                plan=state.plan,
                adapter=adapter,
                core_client=state.client,
                split_id=self.launcher.SPLIT_ID,
                knowledge_snapshot=self.snapshot,
                speech_packet_bindings=self.packet_bindings,
                trace_sink=state.loop_sink,
                decoding_params=self._run_decoding(),
            )
        result_by_id = {result.sample_id: result for result in summary.results}
        rows = []
        for request in requests:
            result = result_by_id[request.sample_id]
            text = result.final_response_text
            contact = result.contacts[0] if loop else None
            rows.append(self.launcher.GenerationResponse(
                sample_id=request.sample_id,
                phase=phase,
                request_body_sha256=self.sent_hash_by_phase_sample[(phase, request.sample_id)],
                response_bytes=text.encode("ascii"),
                source_query_state_sha256=(contact.query_state_sha256 if contact else None),
            ))
        output = self.launcher.GenerationPhaseOutput(phase=phase, rows=tuple(rows))
        state.output = output
        return output

    def parse_observations(self, output: object) -> Mapping[str, object]:
        result = {}
        for row in output.rows:
            parsed = parse_observation_response(
                row.response_bytes.decode("ascii"),
                registered_tool_names=self.registered_tool_names,
            )
            self.observation_states[row.sample_id] = parsed
            result[row.sample_id] = self.launcher.ObservationArtifact(
                sample_id=row.sample_id,
                transcript=parsed.transcript,
                state_sha256=parsed.content_hash(),
                source_response_sha256=row.response_sha256,
            )
        return result

    def retrieve_candidates(
        self,
        observations: Mapping[str, object],
        vectors: Mapping[str, tuple[float, ...]],
        *,
        top_k: int,
    ) -> Mapping[str, object]:
        if top_k != 32:
            raise RuntimeError("retrieval must use K=32")
        result = {}
        for sample_id in self.sample_ids:
            ranking = self.index.rank(vectors[f"embed:{sample_id}:transcript"], top_k=top_k)
            result[sample_id] = self.launcher.CandidateSet(
                sample_id=sample_id,
                tool_names=ranking.selected_tool_names,
                scores=tuple(
                    float(item.score) if item.score is not None else -1.0
                    for item in ranking.selected
                ),
                query_state_sha256=observations[sample_id].state_sha256,
            )
        return result

    def persist_post_embedding_checkpoint(
        self,
        observations: Mapping[str, object],
        candidates: Mapping[str, object],
    ) -> Mapping[str, object]:
        if self.active is not None or self.embedding_receipt is None:
            raise RuntimeError("post-embedding checkpoint requires a finalized embedding pass")
        if self.recovered_prefix is None:
            raise RuntimeError("post-embedding checkpoint lacks recovered source lineage")
        path = self.mission_dir / "post-embedding-k32.json"
        if path.exists():
            raise RuntimeError("post-embedding checkpoint already exists")
        receipt = _write_post_embedding_checkpoint(
            path,
            launcher=self.launcher,
            run_id=str(self.authority["run_id"]),
            source_report_sha256=self.recovered_prefix.source_report_sha256,
            observations=observations,
            candidates=candidates,
        )
        self.post_embedding_checkpoint_receipt = receipt
        _write_json(self.mission_dir / "post-embedding-k32-receipt.json", receipt)
        return receipt

    def rehydrate_post_embedding_checkpoint(
        self,
        receipt: Mapping[str, object],
        observations: Mapping[str, object],
    ) -> Mapping[str, object]:
        if (
            receipt != self.post_embedding_checkpoint_receipt
            or self.recovered_prefix is None
        ):
            raise RuntimeError("post-embedding checkpoint receipt identity drift")
        return _load_post_embedding_checkpoint(
            Path(str(receipt.get("path", ""))),
            launcher=self.launcher,
            expected_sha256=receipt.get("checkpoint_sha256"),
            run_id=str(self.authority["run_id"]),
            source_report_sha256=self.recovered_prefix.source_report_sha256,
            observations=observations,
        )

    def parse_stage_states(
        self,
        expected_stage: str,
        phase_run: object,
        observations: Mapping[str, object],
        candidates: Mapping[str, object],
        packet_bindings: Mapping[str, Mapping[str, object]],
    ) -> Mapping[str, StageStateEnvelope]:
        requests = {item.sample_id: item for item in phase_run.requests}
        responses = {item.sample_id: item for item in phase_run.output.rows}
        return {
            sample_id: _seal_stage_envelope(
                expected_stage=expected_stage,
                sample_id=sample_id,
                request=requests[sample_id],
                response=responses[sample_id],
                observation=observations[sample_id],
                candidate=candidates[sample_id],
                packet_sha256=str(packet_bindings[sample_id]["sha256"]),
                split_identity_sha256=str(self.authority["split_identity_hash"]),
            )
            for sample_id in self.sample_ids
        }

    def _close_phase(self, phase: str) -> Mapping[str, object]:
        state = self.phase_states[phase]
        if state.client_summary is None:
            if state.loop_sink is not None:
                state.loop_sink.close()
            state.client_summary = state.client.close()
        return state.client_summary

    def seal_manifest(
        self, role: str, phase_run: object, extras: Mapping[str, object]
    ) -> Mapping[str, object]:
        role_phase = {
            "direct_m0": self.launcher.M0_PHASE,
            "joint_one_call": self.launcher.JOINT_PHASE,
            "joint_draft_revise": self.launcher.REVISE_PHASE,
            "select_then_fill": self.launcher.FILL_PHASE,
        }
        phase = role_phase.get(role)
        if phase is None or phase_run.phase != phase:
            raise RuntimeError("manifest role and phase differ")
        state = self.phase_states[phase]
        summary = self._close_phase(phase)
        timings = summary.get("timings")
        if not isinstance(timings, list) or len(timings) != 104:
            raise RuntimeError("phase client accounting is incomplete")
        request_by_sample = {str(item["sample_id"]): str(item["request_id"]) for item in timings}
        response_by_sample = {row.sample_id: row for row in phase_run.output.rows}
        trace_path = _phase_trace_path(
            state.run_dir, str(self.authority["run_id"])
        )
        trace_records = {
            document["record_id"]: document["payload"]
            for document in (
                json.loads(line)
                for line in trace_path.read_text(encoding="utf-8").splitlines()
                if line
            )
        }
        rows_list = []
        for sample_id in self.sample_ids:
            request_id = request_by_sample[sample_id]
            request_trace = trace_records.get(f"{request_id}/request")
            response_trace = trace_records.get(f"{request_id}/response")
            if not isinstance(request_trace, Mapping) or not isinstance(
                response_trace, Mapping
            ):
                raise RuntimeError("phase transport trace is incomplete")
            text = response_by_sample[sample_id].response_bytes.decode("ascii")
            if response_trace.get("text") != text:
                raise RuntimeError("phase trace response text drift")
            rows_list.append({
                "request_id": request_id,
                "sample_id": sample_id,
                "carrier_lock_key": AUDIO2TOOL_LOCK_KEY,
                "arm": GENERATION_ARM,
                "text": text,
                "admitted": True,
                "request_sha256": request_trace.get("payload_sha256"),
                "response_sha256": response_trace.get("response_sha256"),
                "response_text_sha256": response_trace.get("response_text_sha256"),
                "phase": phase,
            })
        rows = tuple(rows_list)
        outputs = state.run_dir / f"{self.authority['run_id']}.outputs.jsonl"
        _write_jsonl(outputs, rows)
        lineage = state.run_dir / "select-fill-lineage.json"
        _write_json(lineage, {
            "schema": "saea-a2t-select-fill-score-ready-lineage-v1",
            "role": role,
            "phase": phase,
            "extras": extras,
            "rows": [{
                "sample_id": item.sample_id,
                "request_body_sha256": item.request_body_sha256,
                "response_text_sha256": item.response_sha256,
                **(
                    {
                        "candidate_set_sha256": self.phase_candidates[phase][
                            item.sample_id
                        ].candidate_set_sha256,
                        "candidate_order_sha256": self.phase_candidates[phase][
                            item.sample_id
                        ].candidate_order_sha256,
                        "candidate_tool_names": list(
                            self.phase_candidates[phase][item.sample_id].tool_names
                        ),
                        "candidate_scores": list(
                            self.phase_candidates[phase][item.sample_id].scores
                        ),
                        "candidate_query_state_sha256": self.phase_candidates[phase][
                            item.sample_id
                        ].query_state_sha256,
                    }
                    if phase in self.phase_candidates
                    else {}
                ),
            } for item in phase_run.output.rows],
        })
        cost = dict(summary["cost"])
        result = RunResult(
            run_id=str(self.authority["run_id"]),
            arm=GENERATION_ARM,
            outputs_path=outputs,
            trace_manifest_hash=str(summary["trace_manifest_hash"]),
            cost=cost,
        )
        bundle_plan = replace(
            state.plan,
            split_identity_hash=BUNDLE_SPLIT_IDENTITY_SHA256,
            protocol_hash=BUNDLE_PROTOCOL_SHA256,
        )
        manifest = build_manifest(
            repo_root=self.repo,
            data_root=self.data_root,
            composed=self.composed,
            plan=bundle_plan,
            verified_split=self.verified_split,
            session_receipt_path=state.session_receipt_path,
            run_dir=state.run_dir,
            status=STATUS_COMPLETED,
            result=result,
        )
        verified = verify_bundle(manifest)
        if len(verified.outputs_rows) != 104:
            raise RuntimeError("verified score-ready manifest is incomplete")
        return {
            "role": role,
            "status": "COMPLETE",
            "complete_rows": 104,
            "manifest": str(manifest),
            "manifest_sha256": _sha256_file(manifest),
            "lineage": str(lineage),
            "lineage_sha256": _sha256_file(lineage),
        }

    def seal_recovered_direct_manifest(
        self, role: str, phase_run: object, extras: Mapping[str, object]
    ) -> Mapping[str, object]:
        """Seal a standard verified M0 bundle from the immutable V2 source."""

        if (
            role != "direct_m0"
            or phase_run.phase != self.launcher.M0_PHASE
            or self.recovered_prefix is None
        ):
            raise RuntimeError("recovered direct manifest identity drift")
        directory = self.mission_dir / "recovered-direct-m0"
        directory.mkdir(parents=True, exist_ok=False)
        source_run_id = self.launcher.SOURCE_RUN_ID
        raw_trace = directory / f"{source_run_id}.trace.jsonl"
        shutil.copyfile(self.source_m0_trace_path, raw_trace)
        if _sha256_file(raw_trace) != _sha256_file(self.source_m0_trace_path):
            raise RuntimeError("recovered M0 trace copy drift")
        rows, cost, record_hashes = _derive_recovered_direct_bundle_material(
            launcher=self.launcher,
            trace_path=raw_trace,
            phase_run=phase_run,
            sample_ids=tuple(row.sample_id for row in phase_run.output.rows),
        )
        trace_manifest = directory / f"{source_run_id}.trace-manifest.json"
        _write_json(
            trace_manifest,
            {"run_id": source_run_id, "records": dict(record_hashes)},
        )
        outputs = directory / f"{source_run_id}.outputs.jsonl"
        _write_jsonl(outputs, rows)
        prompt_audits = extras.get("prompt_budget_audits")
        audit_rows = (
            [audit.__dict__ for audit in prompt_audits]
            if isinstance(prompt_audits, tuple)
            else []
        )
        bundle_plan = replace(
            self.source_m0_plan,
            split_identity_hash=BUNDLE_SPLIT_IDENTITY_SHA256,
            protocol_hash=BUNDLE_PROTOCOL_SHA256,
        )
        result = RunResult(
            run_id=source_run_id,
            arm=GENERATION_ARM,
            outputs_path=outputs,
            trace_manifest_hash=_sha256_file(trace_manifest),
            cost=cost,
        )
        manifest_path = build_manifest(
            repo_root=self.repo,
            data_root=self.data_root,
            composed=self.composed,
            plan=bundle_plan,
            verified_split=self.verified_split,
            session_receipt_path=self.source_generation_session_receipt_path,
            run_dir=directory,
            status=STATUS_COMPLETED,
            result=result,
        )
        manifest_document = dict(_read_json(manifest_path))
        manifest_document["recovery_source"] = {
            "execution_plan": asdict(self.source_m0_plan),
            "attempt_path": str(self.source_m0_attempt_path.resolve()),
            "attempt_sha256": _sha256_file(self.source_m0_attempt_path),
            "attempt_state": "ABORTED",
            "authority_binding_path": str(
                self.source_authority_binding_path.resolve()
            ),
            "authority_binding_sha256": _sha256_file(
                self.source_authority_binding_path
            ),
            "session_receipt_path": str(
                self.source_generation_session_receipt_path.resolve()
            ),
            "session_receipt_sha256": _sha256_file(
                self.source_generation_session_receipt_path
            ),
            "trace_path": str(self.source_m0_trace_path.resolve()),
            "trace_sha256": _sha256_file(self.source_m0_trace_path),
            "source_report_sha256": self.recovered_prefix.source_report_sha256,
            "prompt_budget_audits_sha256": _sha256_json(audit_rows),
            "new_model_contacts": 0,
            "inherited_model_contacts": 104,
        }
        _write_json(manifest_path, manifest_document)
        verified = verify_bundle(manifest_path)
        if len(verified.outputs_rows) != 104 or verified.attempt_state != "ABORTED":
            raise RuntimeError("recovered direct standard bundle verification failed")
        return {
            "role": role,
            "status": "COMPLETE",
            "complete_rows": 104,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
        }

    def seal_flight(
        self, manifests: Sequence[Mapping[str, object]], events: Mapping[str, object]
    ) -> Mapping[str, object]:
        self._close_phase(self.launcher.SELECT_PHASE)
        contacts = sum(int(self._close_phase(phase)["request_count"]) for phase in self.plans)
        if (
            self.active is not None
            or contacts != 416
            or len(manifests) != 4
            or self.embedding_receipt is None
            or self.embedding_receipt.get("physical_requests") != 4
            or self.recovered_prefix is None
            or self.post_embedding_checkpoint_receipt is None
        ):
            raise RuntimeError("flight contact or manifest accounting drift")
        document = {
            "schema": "saea-a2t-select-fill-agentloop-104-flight-receipt-v1",
            "status": "SEALED",
            "run_id": self.authority["run_id"],
            "generation_contacts": contacts,
            "inherited_generation_contacts": 208,
            "full_flight_generation_contacts": 624,
            "embedding_logical_items": 104,
            "embedding_physical_requests": 4,
            "manifests": list(manifests),
            "events": dict(events),
            "recovered_prefix_sha256": self.recovered_prefix.source_report_sha256,
            "post_embedding_checkpoint": dict(self.post_embedding_checkpoint_receipt),
            "gold_opened": False,
            "scorer_started": False,
        }
        path = self.mission_dir / "flight-receipt.json"
        _write_json(path, document)
        return {**document, "path": str(path), "sha256": _sha256_file(path)}

    def abort_open_attempts(self, reason: str) -> None:
        if self.embedding_attempt is not None:
            try:
                self.embedding_attempt.mark_aborted(reason)
            except Exception:
                pass
        if self.session is not None:
            try:
                stop_session(
                    self.session,
                    runtime_receipt=(
                        self.embedding_runtime_receipt
                        if self.active == "embedding"
                        else self.generation_runtime_receipt
                    ),
                    runtime_root=self.runtime_root,
                    force_after_timeout=True,
                    receipt_path=self.mission_dir / "failure-stop.json",
                )
            finally:
                self.session = None
                self.active = None
        for plan in self.plans.values():
            abort_attempt_if_opened(
                self.data_root, plan.run_id, plan.attempt_id, reason=reason
            )
        if self.mission_dir.exists():
            _write_json(self.mission_dir / "failure-receipt.json", {
                "status": "ABORTED", "reason": reason,
            })


def build_runtime(
    *,
    authority: Mapping[str, object],
    protocol_config: Mapping[str, object],
    launcher_module: object,
) -> LocalSelectFillRuntime:
    """Factory entry point consumed by the coordinator CLI."""

    return LocalSelectFillRuntime(
        authority=authority,
        protocol_config=protocol_config,
        launcher_module=launcher_module,
    )


__all__ = [
    "LocalSelectFillRuntime",
    "build_runtime",
    "parse_embedding_execution_plan",
    "parse_execution_plans",
]
