"""Launch the preregistered A2T contract-preserving cascade v2.

The launcher seals a same-flight direct comparator and all self-transcript
observations before USE. It runs eight matched and eight shuffled canaries,
reads only their structural JSON envelopes, and either stops or completes the
same two attempts without repeating a canary. Gold and the unchanged official
scorer remain closed until every model response and four complete prediction
manifests have sealed.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from typing import Mapping, Sequence
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[5]
RUNTIME_ROOT = Path("/home/chao")

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    a2t_contract_preserving_cascade as cascade_v2,
)
from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    training_free_a2t_self_transcript_cascade as selftx,
)
from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    TRANSPORTS,
    RunResult,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    protocol_hash,
)
from speech_aware_evidence_acquisition.core.model import FrozenCoreAdapter  # noqa: E402
from speech_aware_evidence_acquisition.core.model.speech_features import (  # noqa: E402
    load_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.core.split_receipt import (  # noqa: E402
    VerifiedSplit,
)
from speech_aware_evidence_acquisition.core.tracing import TraceSink  # noqa: E402
from speech_aware_evidence_acquisition.data.audio2tool import (  # noqa: E402
    AUDIO2TOOL_LOCK_KEY,
    load_expected_calls,
    load_tool_registry,
    render_tool_schemas,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_bundle import (  # noqa: E402
    build_phase_bundle_material,
    build_policy_composite_texts,
    build_resend_composite_texts,
    build_use_composite_texts,
    emit_composite_rows,
    extract_exact_matched_payloads,
    merge_canary_and_remaining,
    select_resend_ids,
    validate_parallel_score_plan,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_flight import (  # noqa: E402
    A2TContractPreservingAdapter,
    MATCHED_USE_PHASE,
    M0_DIRECT_PHASE,
    OBSERVATION_PHASE,
    SHUFFLED_USE_PHASE,
    SPLIT_ID,
    build_use_material,
    run_direct_phase,
    run_phase,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    parse_tool_calls_text,
    score_item,
)

RUN_ID = "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-cpv2-104"
BASELINE_FRAGMENT = "a2t-contract-preserving-cascade-agentloop"
EXPERIMENT_FRAGMENT = "a2t-training-free-contract-preserving-cascade-104-v2"
COMPOSED_CONFIG_SHA256 = (
    "ff6f8a0065279243126635caf2b648568c2b579274a2c5a44bbdfe624946dd93"
)
PROTOCOL_SHA256 = (
    "52d1d4e589bf6663e5724b7095cbbfce9fd1e6f9eaee9a12280e7b4f93348dba"
)
SPLIT_IDENTITY_SHA256 = (
    "401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1"
)
RECEIPT_IDENTITY_SHA256 = (
    "a0acb1672aa1d65517f050418c530cebce9946328d030f41af958ff1a946d42c"
)
RECEIPT_RELPATH = Path("docs/receipts/a2t/A2T-CPV2-104.json")
RECEIPT_SHA256 = (
    "8f47922124c61f92fee03273c1165eb1f8f97048d910ddd4a6a7243906d78783"
)
SPLIT_COUNT = 104
SPLIT_AUDIO_SECONDS = 536.05
SNAPSHOT_RELPATH = Path(
    "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
)
SNAPSHOT_SHA256 = (
    "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
)
REGISTRY_SHA256 = (
    "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"
)
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-CPV2-104-promotion.json"
PROMOTION_SHA256 = (
    "a9ae338fbc9ba4734553b97a417403923aa6e085d3bd4446848a2abff3b65c87"
)
PROMPT_FIT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-contract-preserving-cascade-104-v2/prompt-fit-cpv2.json"
)
PROMPT_FIT_SHA256 = (
    "9b6b8464926af01b33bdd6f1f5360eb6623702033e217491b26141b3f947d5df"
)
RUNTIME_RECEIPT_RELPATH = Path("receipts/runtime-q4km-mmproj-free.json")
CHECK_DIR = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-contract-preserving-cascade-104-v2"
)
PLAN_TEMPLATE = CHECK_DIR / "execution-plan-template.json"
SCORE_PLAN = CHECK_DIR / "parallel-score-plan.json"
OPENJIUWEN_VERSION = "0.1.16.post2"
M0_RECOVERY_PLAN = CHECK_DIR / "m0-manifest-recovery-plan.json"
M0_RECOVERY_PLAN_SHA256 = (
    "00ec5bf6781816a8349959850e17da0d13f5dd96affbef7c04a57b0654ae9737"
)
M0_SOURCE_FLIGHT = Path(
    "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/"
    "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T223557Z"
)
M0_SOURCE_ATTEMPT_ID = "attempt-20260901t223557z-cpv2m0"
POST_MATCHED_RECOVERY_PLAN = CHECK_DIR / "post-matched-recovery-plan.json"
POST_MATCHED_RECOVERY_PLAN_SHA256 = (
    "da51434ba9c93d17017af40066ce804d3180b82ae190c4418a7b4f1d1d0e09ec"
)
POST_MATCHED_SOURCE_FLIGHT = Path(
    "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/"
    "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T225026Z"
)
OBS_SOURCE_ATTEMPT_ID = "attempt-20260901t225026z-cpv2obs"
MATCHED_SOURCE_ATTEMPT_ID = "attempt-20260901t225026z-cpv2matched"
SHUFFLED_CANARY_SOURCE_ATTEMPT_ID = "attempt-20260901t225026z-cpv2shuffled"
POST_SHUFFLED_RECOVERY_PLAN = CHECK_DIR / "post-shuffled-recovery-plan.json"
POST_SHUFFLED_RECOVERY_PLAN_SHA256 = (
    "8bc48ea3e91d6ab6ea7a9d7d963da055260a78f613609af9ad96bffc9429a321"
)
POST_SHUFFLED_SOURCE_FLIGHT = Path(
    "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/"
    "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T230624Z"
)
SHUFFLED_SOURCE_ATTEMPT_ID = "attempt-20260901t230624z-cpv2shuffledrecovery"
POST_WAVE1_RECOVERY_PLAN = CHECK_DIR / "post-wave1-recovery-plan.json"
POST_WAVE1_RECOVERY_PLAN_SHA256 = (
    "5ce00d5c45762211dcecf17575e4d0474379661dd9fa488af3a04efbe10e9542"
)
POST_WAVE1_SOURCE_FLIGHT = Path(
    "/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/runs/"
    "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2/flight-20260901T232133Z"
)
RESEND_SOURCE_ATTEMPT_ID = "attempt-20260901t232133z-cpv2resend"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError(f"JSON document must be an object: {path}")
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _repair_m0_manifest_document(
    source: Mapping[str, object],
    *,
    raw_trace: Path,
    trace_manifest: Path,
) -> dict[str, object]:
    """Add only the sealed trace metadata omitted by the failed assembler."""

    if source.get("raw_trace") is not None or source.get("trace_manifest") is not None:
        raise RuntimeError("source M0 manifest is not the registered null-trace failure")
    repaired = dict(source)
    repaired["raw_trace"] = {
        "path": str(Path(raw_trace).resolve()),
        "sha256": _sha256_file(raw_trace),
    }
    repaired["trace_manifest"] = {
        "path": str(Path(trace_manifest).resolve()),
        "sha256": _sha256_file(trace_manifest),
    }
    return repaired


def _replace_manifest_trace_document(
    source: Mapping[str, object],
    *,
    raw_trace: Path,
    trace_manifest: Path,
) -> dict[str, object]:
    repaired = dict(source)
    repaired["raw_trace"] = {
        "path": str(Path(raw_trace).resolve()),
        "sha256": _sha256_file(raw_trace),
    }
    repaired["trace_manifest"] = {
        "path": str(Path(trace_manifest).resolve()),
        "sha256": _sha256_file(trace_manifest),
    }
    return repaired


def _combine_trace_artifacts(destination: Path, sources: Sequence[Path]) -> tuple[Path, Path]:
    """Union disjoint sealed traces without changing any trace record."""

    if not sources:
        raise RuntimeError("combined trace requires at least one sealed source")
    documents: list[Mapping[str, object]] = []
    records: dict[str, str] = {}
    for source in sources:
        source = Path(source)
        source_manifest = _read_json(source / f"{RUN_ID}.trace-manifest.json")
        source_records = source_manifest.get("records")
        if source_manifest.get("run_id") != RUN_ID or not isinstance(
            source_records, Mapping
        ):
            raise RuntimeError("combined trace source manifest drift")
        for record_id, digest in source_records.items():
            if record_id in records:
                raise RuntimeError(f"combined trace duplicates record id {record_id!r}")
            records[str(record_id)] = str(digest)
        documents.extend(_trace_documents(source))
    destination.mkdir(parents=True, exist_ok=True)
    raw_trace = destination / f"{RUN_ID}.trace.jsonl"
    trace_manifest = destination / f"{RUN_ID}.trace-manifest.json"
    _write_jsonl(raw_trace, documents)
    _write_json(
        trace_manifest,
        {"records": dict(sorted(records.items())), "run_id": RUN_ID},
    )
    return raw_trace, trace_manifest


def _responses_from_trace(
    documents: Sequence[Mapping[str, object]],
) -> tuple[dict[str, str], dict[str, str]]:
    samples_by_request: dict[str, str] = {}
    responses_by_request: dict[str, str] = {}
    for document in documents:
        record_id = document.get("record_id")
        payload = document.get("payload")
        if not isinstance(record_id, str) or not isinstance(payload, Mapping):
            continue
        if document.get("channel") == "MODEL_REQUEST" and record_id.endswith("/request"):
            request = payload.get("payload")
            if isinstance(request, Mapping) and isinstance(request.get("sample_id"), str):
                samples_by_request[record_id[: -len("/request")]] = str(
                    request["sample_id"]
                )
        elif document.get("channel") == "MODEL_RESPONSE" and record_id.endswith(
            "/response"
        ):
            if isinstance(payload.get("text"), str):
                responses_by_request[record_id[: -len("/response")]] = str(
                    payload["text"]
                )
    if set(samples_by_request) != set(responses_by_request):
        raise RuntimeError("sealed trace lacks a one-to-one request/response surface")
    texts = {
        sample_id: responses_by_request[request_id]
        for request_id, sample_id in samples_by_request.items()
    }
    request_ids = {
        sample_id: request_id for request_id, sample_id in samples_by_request.items()
    }
    if len(texts) != len(samples_by_request):
        raise RuntimeError("sealed trace duplicates sample identities")
    return texts, request_ids


def _trace_documents(run_dir: Path) -> tuple[Mapping[str, object], ...]:
    path = Path(run_dir) / f"{RUN_ID}.trace.jsonl"
    documents: list[Mapping[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").split("\n"), start=1
    ):
        if not line:
            continue
        document = json.loads(line)
        if not isinstance(document, Mapping):
            raise RuntimeError(f"trace line {line_number} is not an object")
        documents.append(document)
    if not documents:
        raise RuntimeError(f"runtime trace is empty: {path}")
    return tuple(documents)


def _execution_plan(attempt_id: str) -> ExecutionPlan:
    template = _read_json(PLAN_TEMPLATE)
    fields = dict(template["execution_plan"])  # type: ignore[arg-type]
    fields["attempt_id"] = attempt_id
    return ExecutionPlan(**fields).validate()


def _verified_split(sample_ids: Sequence[str]) -> VerifiedSplit:
    ids = tuple(sorted(sample_ids))
    return VerifiedSplit(
        name=SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in ids),
        identity_hash=SPLIT_IDENTITY_SHA256,
    )


def _server_geometry(values: Mapping[str, object]) -> tuple[int, int]:
    arguments = tuple(values["server_args"])  # type: ignore[arg-type]
    try:
        context = int(arguments[arguments.index("-c") + 1])
        slots = int(arguments[arguments.index("-np") + 1])
    except (ValueError, IndexError, TypeError) as error:
        raise RuntimeError("server arguments lack numeric -c/-np geometry") from error
    return context, slots


def _validate_prompt_fit(values: Mapping[str, object], task_contract: str) -> None:
    if values.get("speech_native_prompt_fit_receipt") != PROMPT_FIT_RELPATH.as_posix():
        raise RuntimeError("composed prompt-fit path drift")
    if values.get("speech_native_prompt_fit_receipt_sha256") != PROMPT_FIT_SHA256:
        raise RuntimeError("composed prompt-fit hash drift")
    path = REPO / PROMPT_FIT_RELPATH
    if _sha256_file(path) != PROMPT_FIT_SHA256:
        raise RuntimeError("prompt-fit receipt byte identity drift")
    receipt = _read_json(path)
    inherited_path = REPO / str(receipt["inherited_text_envelope_receipt"])
    inherited = _read_json(inherited_path)
    context, slots = _server_geometry(values)
    if (
        receipt.get("model_contact") is not False
        or receipt.get("tokenizer_contact") is not False
        or receipt.get("maximum_prompt_fits_one_slot") is not True
        or receipt.get("split_identity_hash") != SPLIT_IDENTITY_SHA256
        or receipt.get("promotion_receipt_sha256") != PROMOTION_SHA256
        or receipt.get("context_tokens") != context
        or receipt.get("slot_count") != slots
        or receipt.get("context_tokens_per_slot") != context // slots
        or int(receipt.get("context_margin_tokens", -1)) <= 0
        or inherited.get("task_contract_sha256") != _sha256_text(task_contract)
        or int(inherited.get("agent_state_texts", -1)) < 1
        or int(inherited.get("visible_key_facets", -1)) < 5
        or int(inherited.get("visible_values", -1)) < 6
    ):
        raise RuntimeError("landed prompt-fit envelope does not dominate this flight")


def _static_preflight(root: Path) -> dict[str, object]:
    commit = require_clean_study_repo(REPO)
    composed = compose(
        REPO,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("composed config identity drift")
    measured_protocol = protocol_hash(
        composed.config_hash,
        str(composed.values["arm"]),
        SPLIT_IDENTITY_SHA256,
    )
    if measured_protocol != PROTOCOL_SHA256:
        raise RuntimeError("audit protocol identity drift")
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("openJiuwen version drift")
    template = _read_json(PLAN_TEMPLATE)
    if (
        template.get("exposure_pre_registration_id") != RUN_ID
        or template.get("composed_config_sha256") != COMPOSED_CONFIG_SHA256
        or _execution_plan("attempt-20260901t000000z-cpv2pre").protocol_hash
        != PROTOCOL_SHA256
    ):
        raise RuntimeError("structured ExecutionPlan identity drift")
    validate_parallel_score_plan(SCORE_PLAN)

    receipt_path = REPO / RECEIPT_RELPATH
    if _sha256_file(receipt_path) != RECEIPT_SHA256:
        raise RuntimeError("subset receipt byte identity drift")
    receipt = _read_json(receipt_path)
    items = receipt.get("items")
    if (
        not isinstance(items, list)
        or len(items) != SPLIT_COUNT
        or receipt.get("count") != SPLIT_COUNT
        or receipt.get("run_identity_hash") != SPLIT_IDENTITY_SHA256
        or receipt.get("split_identity_hash") != RECEIPT_IDENTITY_SHA256
        or abs(float(receipt.get("audio_seconds_total", -1)) - SPLIT_AUDIO_SECONDS)
        > 1e-9
    ):
        raise RuntimeError("subset receipt content drift")
    sample_ids = tuple(str(item["sample_id"]) for item in items)
    if len(set(sample_ids)) != SPLIT_COUNT:
        raise RuntimeError("subset receipt contains duplicate sample ids")

    if _sha256_file(PROMOTION_RECEIPT) != PROMOTION_SHA256:
        raise RuntimeError("speech packet promotion receipt drift")
    promotion = _read_json(PROMOTION_RECEIPT)
    if (
        promotion.get("count") != SPLIT_COUNT
        or promotion.get("split_identity_hash") != SPLIT_IDENTITY_SHA256
        or promotion.get("subset_receipt_sha256") != RECEIPT_SHA256
    ):
        raise RuntimeError("speech packet promotion identity drift")
    promoted = {
        str(row["packet_id"]): row
        for row in promotion.get("packets", [])  # type: ignore[union-attr]
    }
    packet_bindings: dict[str, dict[str, str]] = {}
    for item in items:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        recorded = promoted.get(str(item["packet_id"]))
        if (
            recorded is None
            or packet.audio_sha256 != item["audio_sha256"]
            or packet.packet_sha256 != recorded.get("packet_sha256")
        ):
            raise RuntimeError(f"speech packet drift for {item['sample_id']}")
        packet_bindings[str(item["sample_id"])] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }

    lock = load_lock(umbrella_lock_path(REPO))
    carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    registry_path = carrier_root / "tools_registry.csv"
    if _sha256_file(registry_path) != REGISTRY_SHA256:
        raise RuntimeError("tool registry byte identity drift")
    registry = load_tool_registry(lock, root)
    registry_names = frozenset(row["tool_name"] for row in registry)
    if len(registry) != 152 or len(registry_names) != 152:
        raise RuntimeError("tool registry row or name-count drift")
    task_contract = render_tool_schemas(lock, root)
    _validate_prompt_fit(composed.values, task_contract)

    snapshot_path = root / SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(_read_json(snapshot_path))
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise RuntimeError("knowledge snapshot identity drift")
    if set(sample_ids) & set(snapshot.source_sample_ids):
        raise RuntimeError("knowledge snapshot overlaps the flight population")
    return {
        "commit": commit,
        "composed": composed,
        "lock": lock,
        "carrier_root": carrier_root,
        "receipt": receipt,
        "items": tuple(items),
        "sample_ids": sample_ids,
        "snapshot": snapshot,
        "snapshot_path": snapshot_path,
        "packet_bindings": packet_bindings,
        "registry_names": registry_names,
        "task_contract": task_contract,
    }


def _phase_responses(summary: object) -> dict[str, str]:
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or not results:
        raise RuntimeError("phase summary lacks non-empty tuple results")
    responses = {
        str(result.sample_id): str(result.final_response_text) for result in results
    }
    if len(responses) != len(results):
        raise RuntimeError("phase summary contains duplicate result identities")
    return responses


def _combine_phase_summaries(
    canary: object,
    remaining: object,
    *,
    expected_ids: Sequence[str],
) -> SimpleNamespace:
    first = tuple(getattr(canary, "results", ()))
    second = tuple(getattr(remaining, "results", ()))
    ids = [str(result.sample_id) for result in (*first, *second)]
    if len(set(ids)) != len(ids):
        raise RuntimeError("combined phase summaries contain duplicate contacts")
    if set(ids) != set(expected_ids):
        raise RuntimeError("combined phase summary is not the complete routed surface")
    return SimpleNamespace(
        results=tuple(sorted((*first, *second), key=lambda result: result.sample_id)),
        agent_executor_id="openjiuwen-workflow-v1",
    )


def _request_ids_from_rows(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    result = {str(row["sample_id"]): str(row["request_id"]) for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("phase rows contain duplicate sample identities")
    return result


def _close_phase_traces(
    trace_sink: object,
    client: object,
) -> tuple[str, Mapping[str, object]]:
    trace_manifest_hash = trace_sink.close()  # type: ignore[attr-defined]
    client_summary = client.close()  # type: ignore[attr-defined]
    if not isinstance(trace_manifest_hash, str) or len(trace_manifest_hash) != 64:
        raise RuntimeError("primary trace close did not return a SHA-256")
    if not isinstance(client_summary, Mapping):
        raise RuntimeError("transport trace close did not return a mapping")
    return trace_manifest_hash, client_summary


def _materialize_observation(
    context: Mapping[str, object], responses: Mapping[str, str]
) -> dict[str, object]:
    expected_ids = tuple(sorted(str(value) for value in context["sample_ids"]))  # type: ignore[union-attr]
    if set(responses) != set(expected_ids):
        raise RuntimeError("observation response identity differs from the frozen split")
    retriever = selftx.EvidenceRetriever(context["snapshot"])  # type: ignore[arg-type]
    transcripts: dict[str, selftx.TranscriptParse] = {}
    routes: dict[str, selftx.EvidenceRoute] = {}
    observations: list[selftx.ObservationRecord] = []
    tiers = {
        str(item["sample_id"]): str(item["tier"])
        for item in context["items"]  # type: ignore[union-attr]
    }
    for sample_id in expected_ids:
        parsed = selftx.validate_self_transcript(responses.get(sample_id))
        route = (
            retriever.route(parsed.text)
            if parsed.valid
            else selftx.EvidenceRoute(False, (), (), (), (), 0, 0.0, "")
        )
        transcripts[sample_id] = parsed
        routes[sample_id] = route
        observations.append(
            selftx.ObservationRecord(
                sample_id=sample_id,
                tier=tiers[sample_id],
                response_received=sample_id in responses,
                transcript=parsed,
                positive_route=route.available,
            )
        )
    report = selftx.evaluate_liveness(observations)
    material: dict[str, object] = {
        "passed": report.passed,
        "report": report,
        "transcripts": transcripts,
        "routes": routes,
        "tiers": tiers,
    }
    if not report.passed:
        return material
    receipt = selftx.authorize_use_phase(observations)
    routed_tiers = {
        sample_id: tiers[sample_id]
        for sample_id, route in routes.items()
        if transcripts[sample_id].valid and route.available
    }
    canary_ids = cascade_v2.select_canary_ids(routed_tiers)
    resend_ids = select_resend_ids(routed_tiers)
    matched_material = build_use_material(
        transcripts=transcripts,
        sample_tiers=tiers,
        snapshot=context["snapshot"],
        phase=MATCHED_USE_PHASE,
    )
    shuffled_material = build_use_material(
        transcripts=transcripts,
        sample_tiers=tiers,
        snapshot=context["snapshot"],
        phase=SHUFFLED_USE_PHASE,
    )
    if set(matched_material) != set(routed_tiers) or set(shuffled_material) != set(
        routed_tiers
    ):
        raise RuntimeError("frozen USE material differs from the liveness route set")
    material.update(
        {
            "receipt": receipt,
            "routed_tiers": routed_tiers,
            "canary_ids": canary_ids,
            "resend_ids": resend_ids,
            "matched_material": matched_material,
            "shuffled_material": shuffled_material,
        }
    )
    return material


def _write_observation_receipts(run_dir: Path, material: Mapping[str, object]) -> None:
    transcripts = material["transcripts"]
    routes = material["routes"]
    _write_json(
        run_dir / "liveness-report.json",
        {
            "schema": "saea-a2t-contract-v2-liveness-report-v1",
            "report": asdict(material["report"]),  # type: ignore[arg-type]
            "transcripts": {
                sample_id: asdict(transcripts[sample_id])  # type: ignore[index]
                for sample_id in sorted(transcripts)  # type: ignore[arg-type]
            },
            "routes": {
                sample_id: asdict(routes[sample_id])  # type: ignore[index]
                for sample_id in sorted(routes)  # type: ignore[arg-type]
            },
        },
    )
    if material["passed"] is not True:
        return
    shuffled = material["shuffled_material"]
    _write_json(
        run_dir / "use-authorization-receipt.json",
        {
            "schema": "saea-a2t-contract-v2-use-authorization-v1",
            "liveness": asdict(material["receipt"]),  # type: ignore[arg-type]
            "routed_tiers": dict(sorted(material["routed_tiers"].items())),  # type: ignore[union-attr]
            "same_tier_donors": {
                sample_id: shuffled[sample_id].donor_id  # type: ignore[index]
                for sample_id in sorted(shuffled)  # type: ignore[arg-type]
            },
            "canary_ids": list(material["canary_ids"]),  # type: ignore[arg-type]
            "resend_ids": list(material["resend_ids"]),  # type: ignore[arg-type]
            "sealed_before_use": True,
        },
    )


def _build_completed_manifest(
    *,
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    run_dir: Path,
    session_receipt_path: Path,
    outputs_path: Path,
    trace_manifest_hash: str,
    cost: Mapping[str, object],
    expected_attempt_state: str,
) -> Path:
    result = RunResult(
        run_id=RUN_ID,
        arm="speech-feature-query",
        outputs_path=outputs_path,
        trace_manifest_hash=trace_manifest_hash,
        cost=cost,
    )
    manifest_path = build_manifest(
        repo_root=REPO,
        data_root=root,
        composed=context["composed"],  # type: ignore[arg-type]
        plan=plan,
        verified_split=_verified_split(context["sample_ids"]),  # type: ignore[arg-type]
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=STATUS_COMPLETED,
        result=result,
    )
    verified = verify_bundle(manifest_path)
    if (
        verified.attempt_state != expected_attempt_state
        or len(verified.outputs_rows) != SPLIT_COUNT
    ):
        raise RuntimeError("complete manifest failed state or 104-row verification")
    return manifest_path


def _decoding(context: Mapping[str, object]) -> dict[str, object]:
    values = context["composed"].values  # type: ignore[union-attr]
    result = dict(values["decoding_params"])
    result.pop("id_slot", None)
    return result


def _validate_m0_recovery_sources(root: Path) -> dict[str, object]:
    if _sha256_file(M0_RECOVERY_PLAN) != M0_RECOVERY_PLAN_SHA256:
        raise RuntimeError("M0 recovery plan byte identity drift")
    recovery = _read_json(M0_RECOVERY_PLAN)
    if (
        recovery.get("run_id") != RUN_ID
        or recovery.get("source_attempt_id") != M0_SOURCE_ATTEMPT_ID
        or recovery.get("source_attempt_state") != "ABORTED"
        or recovery.get("observed_boundary", {}).get("gold_opened") is not False  # type: ignore[union-attr]
        or recovery.get("observed_boundary", {}).get("official_scorer_started")  # type: ignore[union-attr]
        is not False
        or recovery.get("authorized_recovery", {}).get("m0_recontact") is not False  # type: ignore[union-attr]
        or recovery.get("authorized_recovery", {}).get("maximum_cumulative_calls")  # type: ignore[union-attr]
        != 432
    ):
        raise RuntimeError("M0 recovery contract drift")
    m0_dir = M0_SOURCE_FLIGHT / "m0-direct"
    transport_dir = m0_dir / "transport-trace"
    paths = {
        "failure_receipt": M0_SOURCE_FLIGHT / "failure-receipt.json",
        "source_manifest": m0_dir / f"{RUN_ID}.run-manifest.json",
        "outputs": m0_dir / f"{RUN_ID}.outputs.jsonl",
        "raw_trace": transport_dir / f"{RUN_ID}.trace.jsonl",
        "trace_manifest": transport_dir / f"{RUN_ID}.trace-manifest.json",
        "session_receipt": M0_SOURCE_FLIGHT / "service/session-receipt.json",
        "stop_receipt": M0_SOURCE_FLIGHT / "service/stop-receipt.json",
    }
    for key, path in paths.items():
        expected = recovery.get(f"{key}_sha256")
        if not isinstance(expected, str) or _sha256_file(path) != expected:
            raise RuntimeError(f"registered M0 recovery source drift: {key}")
    source_manifest = _read_json(paths["source_manifest"])
    attempt = source_manifest.get("attempt")
    if (
        source_manifest.get("study_commit") != recovery.get("source_study_commit")
        or source_manifest.get("status") != STATUS_COMPLETED
        or not isinstance(attempt, Mapping)
        or attempt.get("attempt_id") != M0_SOURCE_ATTEMPT_ID
        or source_manifest.get("raw_trace") is not None
        or source_manifest.get("trace_manifest") is not None
    ):
        raise RuntimeError("source M0 failure manifest structure drift")
    attempt_path = root / "attempts" / RUN_ID / f"{M0_SOURCE_ATTEMPT_ID}.json"
    if _sha256_file(attempt_path) != recovery.get("attempt_receipt_sha256"):
        raise RuntimeError("source M0 attempt receipt byte identity drift")
    attempt_document = _read_json(attempt_path)
    actual = attempt_document.get("actual")
    if (
        attempt_document.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != SPLIT_COUNT
        or abs(float(actual.get("audio_seconds", -1)) - SPLIT_AUDIO_SECONDS) > 1e-9
    ):
        raise RuntimeError("source M0 terminal attempt accounting drift")
    return {
        "recovery": recovery,
        "paths": paths,
        "source_manifest": source_manifest,
        "attempt_path": attempt_path,
    }


def _recover_m0(root: Path, context: Mapping[str, object]) -> dict[str, object]:
    material = _validate_m0_recovery_sources(root)
    paths = material["paths"]
    repaired = _repair_m0_manifest_document(
        material["source_manifest"],  # type: ignore[arg-type]
        raw_trace=paths["raw_trace"],  # type: ignore[index]
        trace_manifest=paths["trace_manifest"],  # type: ignore[index]
    )
    recovered_manifest = (
        M0_SOURCE_FLIGHT
        / "m0-direct"
        / f"{RUN_ID}.recovered.run-manifest.json"
    )
    _write_json(recovered_manifest, repaired)
    verified = verify_bundle(recovered_manifest)
    if verified.attempt_state != "ABORTED" or len(verified.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("recovered M0 bundle did not verify as complete and terminal")
    texts = {
        str(row["sample_id"]): str(row["text"]) for row in verified.outputs_rows
    }
    if set(texts) != set(context["sample_ids"]):  # type: ignore[arg-type]
        raise RuntimeError("recovered M0 output identities differ from the frozen split")
    _write_json(
        recovered_manifest.parent / "m0-recovery-receipt.json",
        {
            "schema": "saea-a2t-cpv2-m0-manifest-recovery-receipt-v1",
            "recovery_plan_sha256": M0_RECOVERY_PLAN_SHA256,
            "source_manifest_sha256": material["recovery"]["source_manifest_sha256"],  # type: ignore[index]
            "recovered_manifest": str(recovered_manifest),
            "recovered_manifest_sha256": _sha256_file(recovered_manifest),
            "attempt_id": M0_SOURCE_ATTEMPT_ID,
            "attempt_state": verified.attempt_state,
            "outputs_count": len(verified.outputs_rows),
            "m0_recontacts": 0,
        },
    )
    return {
        "texts": texts,
        "outputs": Path(paths["outputs"]),  # type: ignore[arg-type]
        "manifest": recovered_manifest,
        "attempt_id": M0_SOURCE_ATTEMPT_ID,
        "run_dir": M0_SOURCE_FLIGHT / "m0-direct",
        "recovered": True,
    }


def _validate_post_matched_recovery_sources(root: Path) -> dict[str, object]:
    if _sha256_file(POST_MATCHED_RECOVERY_PLAN) != POST_MATCHED_RECOVERY_PLAN_SHA256:
        raise RuntimeError("post-matched recovery plan byte identity drift")
    plan = _read_json(POST_MATCHED_RECOVERY_PLAN)
    if (
        plan.get("run_id") != RUN_ID
        or plan.get("observed_boundary", {}).get("gold_opened") is not False  # type: ignore[union-attr]
        or plan.get("observed_boundary", {}).get("official_scorer_started")  # type: ignore[union-attr]
        is not False
        or plan.get("authorized_recovery", {}).get("maximum_cumulative_calls")  # type: ignore[union-attr]
        != 430
    ):
        raise RuntimeError("post-matched recovery contract drift")
    paths = {
        "failure_receipt": POST_MATCHED_SOURCE_FLIGHT / "failure-receipt.json",
        "session_receipt": POST_MATCHED_SOURCE_FLIGHT / "service/session-receipt.json",
        "stop_receipt": POST_MATCHED_SOURCE_FLIGHT / "service/stop-receipt.json",
        "canary_report": POST_MATCHED_SOURCE_FLIGHT / "structural-canary-report.json",
        "observation_dir": POST_MATCHED_SOURCE_FLIGHT / "observation",
        "matched_dir": POST_MATCHED_SOURCE_FLIGHT / "matched-composite",
        "shuffled_dir": POST_MATCHED_SOURCE_FLIGHT / "shuffled-composite",
    }
    for key in ("failure_receipt", "session_receipt", "stop_receipt"):
        if _sha256_file(paths[key]) != plan.get(f"{key}_sha256"):
            raise RuntimeError(f"post-matched source drift: {key}")
    observation = plan.get("observation")
    matched = plan.get("matched")
    shuffled = plan.get("shuffled_canary")
    if not all(isinstance(item, Mapping) for item in (observation, matched, shuffled)):
        raise RuntimeError("post-matched recovery sections are malformed")
    artifact_checks = (
        (paths["observation_dir"] / f"{RUN_ID}.outputs.jsonl", observation["outputs_sha256"]),  # type: ignore[index]
        (paths["observation_dir"] / f"{RUN_ID}.run-manifest.json", observation["source_manifest_sha256"]),  # type: ignore[index]
        (paths["observation_dir"] / f"{RUN_ID}.trace.jsonl", observation["raw_trace_sha256"]),  # type: ignore[index]
        (paths["observation_dir"] / f"{RUN_ID}.trace-manifest.json", observation["trace_manifest_sha256"]),  # type: ignore[index]
        (paths["observation_dir"] / "liveness-report.json", observation["liveness_report_sha256"]),  # type: ignore[index]
        (paths["observation_dir"] / "use-authorization-receipt.json", observation["use_authorization_sha256"]),  # type: ignore[index]
        (paths["matched_dir"] / f"{RUN_ID}.outputs.jsonl", matched["outputs_sha256"]),  # type: ignore[index]
        (paths["matched_dir"] / f"{RUN_ID}.run-manifest.json", matched["source_manifest_sha256"]),  # type: ignore[index]
        (paths["matched_dir"] / f"{RUN_ID}.trace.jsonl", matched["primary_raw_trace_sha256"]),  # type: ignore[index]
        (paths["matched_dir"] / f"{RUN_ID}.trace-manifest.json", matched["primary_trace_manifest_sha256"]),  # type: ignore[index]
        (paths["matched_dir"] / "composite-trace" / f"{RUN_ID}.trace.jsonl", matched["composite_raw_trace_sha256"]),  # type: ignore[index]
        (paths["matched_dir"] / "composite-trace" / f"{RUN_ID}.trace-manifest.json", matched["composite_trace_manifest_sha256"]),  # type: ignore[index]
        (paths["shuffled_dir"] / f"{RUN_ID}.trace.jsonl", shuffled["raw_trace_sha256"]),  # type: ignore[index]
        (paths["canary_report"], shuffled["structural_canary_report_sha256"]),  # type: ignore[index]
    )
    for path, expected in artifact_checks:
        if _sha256_file(path) != expected:
            raise RuntimeError(f"post-matched artifact drift: {path}")
    for section, attempt_id in (
        (observation, OBS_SOURCE_ATTEMPT_ID),
        (matched, MATCHED_SOURCE_ATTEMPT_ID),
        (shuffled, SHUFFLED_CANARY_SOURCE_ATTEMPT_ID),
    ):
        attempt_path = root / "attempts" / RUN_ID / f"{attempt_id}.json"
        if _sha256_file(attempt_path) != section["attempt_receipt_sha256"]:  # type: ignore[index]
            raise RuntimeError(f"post-matched attempt receipt drift: {attempt_id}")
        attempt = _read_json(attempt_path)
        actual = attempt.get("actual")
        if (
            attempt.get("state") != "ABORTED"
            or not isinstance(actual, Mapping)
            or actual.get("calls") != section["calls"]  # type: ignore[index]
            or abs(float(actual.get("audio_seconds", -1)) - float(section["audio_seconds"]))  # type: ignore[index]
            > 1e-6
        ):
            raise RuntimeError(f"post-matched attempt accounting drift: {attempt_id}")
    return {"plan": plan, "paths": paths}


def _validate_post_shuffled_recovery_sources(root: Path) -> dict[str, object]:
    if (
        _sha256_file(POST_SHUFFLED_RECOVERY_PLAN)
        != POST_SHUFFLED_RECOVERY_PLAN_SHA256
    ):
        raise RuntimeError("post-shuffled recovery plan byte identity drift")
    plan = _read_json(POST_SHUFFLED_RECOVERY_PLAN)
    boundary = plan.get("observed_boundary")
    authorization = plan.get("authorized_recovery")
    shuffled = plan.get("shuffled")
    if (
        plan.get("run_id") != RUN_ID
        or not isinstance(boundary, Mapping)
        or boundary.get("cumulative_calls") != 414
        or boundary.get("remaining_resend_contacts") != 16
        or boundary.get("resend_attempt_opened") is not False
        or boundary.get("gold_opened") is not False
        or boundary.get("official_scorer_started") is not False
        or not isinstance(authorization, Mapping)
        or authorization.get("maximum_additional_calls") != 16
        or authorization.get("maximum_cumulative_calls") != 430
        or any(
            authorization.get(key) is not False
            for key in (
                "m0_recontact",
                "observation_recontact",
                "matched_recontact",
                "shuffled_canary_recontact",
                "shuffled_remaining_recontact",
            )
        )
        or not isinstance(shuffled, Mapping)
        or shuffled.get("attempt_id") != SHUFFLED_SOURCE_ATTEMPT_ID
    ):
        raise RuntimeError("post-shuffled recovery contract drift")
    shuffled_dir = POST_SHUFFLED_SOURCE_FLIGHT / "shuffled-recovery"
    complete_dir = shuffled_dir / "complete-bundle"
    paths = {
        "failure_receipt": POST_SHUFFLED_SOURCE_FLIGHT / "failure-receipt.json",
        "session_receipt": POST_SHUFFLED_SOURCE_FLIGHT
        / "service/session-receipt.json",
        "stop_receipt": POST_SHUFFLED_SOURCE_FLIGHT / "service/stop-receipt.json",
        "recovery_receipt": shuffled_dir / "shuffled-recovery-receipt.json",
        "primary_raw_trace": shuffled_dir / "primary-trace" / f"{RUN_ID}.trace.jsonl",
        "primary_trace_manifest": shuffled_dir
        / "primary-trace"
        / f"{RUN_ID}.trace-manifest.json",
        "composite_raw_trace": shuffled_dir
        / "composite-trace"
        / f"{RUN_ID}.trace.jsonl",
        "composite_trace_manifest": shuffled_dir
        / "composite-trace"
        / f"{RUN_ID}.trace-manifest.json",
        "complete_raw_trace": complete_dir / f"{RUN_ID}.trace.jsonl",
        "complete_trace_manifest": complete_dir / f"{RUN_ID}.trace-manifest.json",
        "outputs": complete_dir / f"{RUN_ID}.outputs.jsonl",
        "manifest": complete_dir / f"{RUN_ID}.run-manifest.json",
    }
    expected_hashes = {
        "failure_receipt": plan.get("failure_receipt_sha256"),
        "session_receipt": plan.get("session_receipt_sha256"),
        "stop_receipt": plan.get("stop_receipt_sha256"),
        "recovery_receipt": shuffled.get("recovery_receipt_sha256"),
        "primary_raw_trace": shuffled.get("primary_raw_trace_sha256"),
        "primary_trace_manifest": shuffled.get("primary_trace_manifest_sha256"),
        "composite_raw_trace": shuffled.get("composite_raw_trace_sha256"),
        "composite_trace_manifest": shuffled.get(
            "composite_trace_manifest_sha256"
        ),
        "complete_raw_trace": shuffled.get("complete_raw_trace_sha256"),
        "complete_trace_manifest": shuffled.get(
            "complete_trace_manifest_sha256"
        ),
        "outputs": shuffled.get("outputs_sha256"),
        "manifest": shuffled.get("run_manifest_sha256"),
    }
    for key, path in paths.items():
        expected = expected_hashes[key]
        if not isinstance(expected, str) or _sha256_file(path) != expected:
            raise RuntimeError(f"post-shuffled source drift: {key}")
    attempt_path = root / "attempts" / RUN_ID / f"{SHUFFLED_SOURCE_ATTEMPT_ID}.json"
    if _sha256_file(attempt_path) != shuffled.get("attempt_receipt_sha256"):
        raise RuntimeError("post-shuffled attempt receipt byte identity drift")
    attempt = _read_json(attempt_path)
    actual = attempt.get("actual")
    if (
        attempt.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != 95
        or abs(float(actual.get("audio_seconds", -1)) - 493.2970000000001)
        > 1e-6
    ):
        raise RuntimeError("post-shuffled terminal attempt accounting drift")
    failure = _read_json(paths["failure_receipt"])
    prior_attempts = failure.get("attempt_ids")
    if (
        not isinstance(prior_attempts, Mapping)
        or prior_attempts.get("shuffled") != SHUFFLED_SOURCE_ATTEMPT_ID
        or prior_attempts.get("resend")
        != "attempt-20260901t230624z-cpv2resend"
        or (
            root
            / "attempts"
            / RUN_ID
            / "attempt-20260901t230624z-cpv2resend.json"
        ).exists()
    ):
        raise RuntimeError("post-shuffled pre-contact resend boundary drift")
    recovery_receipt = _read_json(paths["recovery_receipt"])
    if (
        recovery_receipt.get("new_attempt_id") != SHUFFLED_SOURCE_ATTEMPT_ID
        or recovery_receipt.get("old_canary_contacts") != 8
        or recovery_receipt.get("new_contacts") != 95
        or recovery_receipt.get("manifest_sha256")
        != shuffled.get("run_manifest_sha256")
    ):
        raise RuntimeError("post-shuffled recovery receipt drift")
    verified = verify_bundle(paths["manifest"])
    if verified.attempt_state != "ABORTED" or len(verified.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("sealed shuffled bundle failed recovery verification")
    return {
        "plan": plan,
        "paths": paths,
        "verified": verified,
        "attempt_path": attempt_path,
    }


def _recover_shuffled(
    root: Path, context: Mapping[str, object]
) -> dict[str, object]:
    recovery = _validate_post_shuffled_recovery_sources(root)
    verified = recovery["verified"]
    texts = {
        str(row["sample_id"]): str(row["text"])
        for row in verified.outputs_rows  # type: ignore[union-attr]
    }
    if set(texts) != set(context["sample_ids"]):  # type: ignore[arg-type]
        raise RuntimeError("recovered shuffled identities differ from the frozen split")
    return {
        "texts": texts,
        "manifest": recovery["paths"]["manifest"],  # type: ignore[index]
        "outputs": recovery["paths"]["outputs"],  # type: ignore[index]
        "attempt_id": SHUFFLED_SOURCE_ATTEMPT_ID,
        "run_dir": POST_SHUFFLED_SOURCE_FLIGHT / "shuffled-recovery",
        "recovered": True,
    }


def _validate_post_wave1_recovery_sources(root: Path) -> dict[str, object]:
    if _sha256_file(POST_WAVE1_RECOVERY_PLAN) != POST_WAVE1_RECOVERY_PLAN_SHA256:
        raise RuntimeError("post-Wave-1 recovery plan byte identity drift")
    plan = _read_json(POST_WAVE1_RECOVERY_PLAN)
    boundary = plan.get("observed_boundary")
    authorization = plan.get("authorized_recovery")
    resend = plan.get("resend")
    wave1 = plan.get("wave_1")
    if (
        plan.get("run_id") != RUN_ID
        or not isinstance(boundary, Mapping)
        or boundary.get("cumulative_model_calls") != 430
        or boundary.get("remaining_model_calls") != 0
        or boundary.get("gold_opened") is not True
        or boundary.get("wave_1_official_scorers_completed") != 4
        or boundary.get("wave_2_official_scorer_started") is not False
        or not isinstance(authorization, Mapping)
        or authorization.get("model_recontact") is not False
        or authorization.get("wave_1_rescore") is not False
        or authorization.get("maximum_additional_model_calls") != 0
        or authorization.get("maximum_additional_official_scorer_calls") != 1
        or not isinstance(resend, Mapping)
        or resend.get("attempt_id") != RESEND_SOURCE_ATTEMPT_ID
        or not isinstance(wave1, Mapping)
    ):
        raise RuntimeError("post-Wave-1 recovery contract drift")
    resend_dir = POST_WAVE1_SOURCE_FLIGHT / "resend-composite"
    wave1_dir = POST_WAVE1_SOURCE_FLIGHT / "wave1-parallel-finalize"
    policy_dir = POST_WAVE1_SOURCE_FLIGHT / "policy-composite"
    paths = {
        "failure_receipt": POST_WAVE1_SOURCE_FLIGHT / "failure-receipt.json",
        "session_receipt": POST_WAVE1_SOURCE_FLIGHT / "service/session-receipt.json",
        "stop_receipt": POST_WAVE1_SOURCE_FLIGHT / "service/stop-receipt.json",
        "resend_receipt": resend_dir / "resend-receipt.json",
        "resend_outputs": resend_dir / f"{RUN_ID}.outputs.jsonl",
        "resend_raw_trace": resend_dir / f"{RUN_ID}.trace.jsonl",
        "resend_trace_manifest": resend_dir / f"{RUN_ID}.trace-manifest.json",
        "resend_manifest": resend_dir / f"{RUN_ID}.run-manifest.json",
        "resend_scores": resend_dir / f"{RUN_ID}.scores.json",
        "wave1_summary": wave1_dir / "batch-summary.json",
        "wave1_m0": wave1_dir / "contract-v2-m0-direct.score.json",
        "wave1_matched": wave1_dir / "contract-v2-matched-composite.score.json",
        "wave1_shuffled": wave1_dir
        / "contract-v2-shuffled-composite.score.json",
        "wave1_resend": wave1_dir / "contract-v2-resend-composite.score.json",
        "policy_outputs": policy_dir / f"{RUN_ID}.outputs.jsonl",
        "policy_raw_trace": policy_dir / f"{RUN_ID}.trace.jsonl",
        "policy_trace_manifest": policy_dir / f"{RUN_ID}.trace-manifest.json",
        "policy_manifest": policy_dir / f"{RUN_ID}.run-manifest.json",
    }
    failed_policy = plan.get("failed_policy_draft")
    if not isinstance(failed_policy, Mapping):
        raise RuntimeError("post-Wave-1 failed policy section is malformed")
    expected_hashes = {
        "failure_receipt": plan.get("failure_receipt_sha256"),
        "session_receipt": plan.get("session_receipt_sha256"),
        "stop_receipt": plan.get("stop_receipt_sha256"),
        "resend_receipt": resend.get("receipt_sha256"),
        "resend_outputs": resend.get("outputs_sha256"),
        "resend_raw_trace": resend.get("raw_trace_sha256"),
        "resend_trace_manifest": resend.get("trace_manifest_sha256"),
        "resend_manifest": resend.get("run_manifest_sha256"),
        "resend_scores": resend.get("scores_sha256"),
        "wave1_summary": wave1.get("batch_summary_sha256"),
        "wave1_m0": wave1.get("m0_result_sha256"),
        "wave1_matched": wave1.get("matched_result_sha256"),
        "wave1_shuffled": wave1.get("shuffled_result_sha256"),
        "wave1_resend": wave1.get("resend_result_sha256"),
        "policy_outputs": failed_policy.get("outputs_sha256"),
        "policy_raw_trace": failed_policy.get("raw_trace_sha256"),
        "policy_trace_manifest": failed_policy.get("trace_manifest_sha256"),
        "policy_manifest": failed_policy.get("run_manifest_sha256"),
    }
    for key, path in paths.items():
        expected = expected_hashes[key]
        if not isinstance(expected, str) or _sha256_file(path) != expected:
            raise RuntimeError(f"post-Wave-1 source drift: {key}")
    attempt_path = root / "attempts" / RUN_ID / f"{RESEND_SOURCE_ATTEMPT_ID}.json"
    if _sha256_file(attempt_path) != resend.get("attempt_receipt_sha256"):
        raise RuntimeError("post-Wave-1 resend attempt byte identity drift")
    attempt = _read_json(attempt_path)
    actual = attempt.get("actual")
    if (
        attempt.get("state") != "FINALIZED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != 16
        or abs(float(actual.get("audio_seconds", -1)) - 84.603) > 1e-6
    ):
        raise RuntimeError("post-Wave-1 resend attempt accounting drift")
    batch = _read_json(paths["wave1_summary"])
    jobs = batch.get("jobs")
    if (
        batch.get("failed") != 0
        or batch.get("succeeded") != 4
        or batch.get("effective_max_workers") != 4
        or batch.get("parallelism_boundary")
        != "one-complete-verified-manifest-per-process"
        or not isinstance(jobs, list)
        or [job.get("operation") for job in jobs if isinstance(job, Mapping)]
        != ["score", "score", "score", "finalize"]
    ):
        raise RuntimeError("post-Wave-1 parallel score summary drift")
    verified_resend = verify_bundle(paths["resend_manifest"])
    verified_policy_draft = verify_bundle(paths["policy_manifest"])
    if (
        verified_resend.attempt_state != "FINALIZED"
        or len(verified_resend.outputs_rows) != SPLIT_COUNT
        or verified_policy_draft.attempt_state != "ABORTED"
        or len(verified_policy_draft.outputs_rows) != SPLIT_COUNT
    ):
        raise RuntimeError("post-Wave-1 source manifest verification drift")
    return {
        "plan": plan,
        "paths": paths,
        "batch": batch,
        "verified_resend": verified_resend,
    }


def _recover_resend(root: Path, context: Mapping[str, object]) -> dict[str, object]:
    recovery = _validate_post_wave1_recovery_sources(root)
    verified = recovery["verified_resend"]
    texts = {
        str(row["sample_id"]): str(row["text"])
        for row in verified.outputs_rows  # type: ignore[union-attr]
    }
    if set(texts) != set(context["sample_ids"]):  # type: ignore[arg-type]
        raise RuntimeError("recovered resend identities differ from the frozen split")
    return {
        "texts": texts,
        "manifest": recovery["paths"]["resend_manifest"],  # type: ignore[index]
        "outputs": recovery["paths"]["resend_outputs"],  # type: ignore[index]
        "attempt_id": RESEND_SOURCE_ATTEMPT_ID,
        "run_dir": POST_WAVE1_SOURCE_FLIGHT / "resend-composite",
        "recovered": True,
    }


def _recover_observation(
    root: Path, context: Mapping[str, object]
) -> dict[str, object]:
    recovery = _validate_post_matched_recovery_sources(root)
    observation_dir = recovery["paths"]["observation_dir"]  # type: ignore[index]
    manifest = observation_dir / f"{RUN_ID}.run-manifest.json"
    verified = verify_bundle(manifest)
    if verified.attempt_state != "ABORTED" or len(verified.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("sealed observation bundle failed recovery verification")
    responses = {
        str(row["sample_id"]): str(row["text"]) for row in verified.outputs_rows
    }
    material = _materialize_observation(context, responses)
    if material.get("passed") is not True:
        raise RuntimeError("sealed observation no longer passes the frozen liveness gate")
    authorization = _read_json(observation_dir / "use-authorization-receipt.json")
    if (
        list(material["canary_ids"]) != authorization.get("canary_ids")  # type: ignore[arg-type]
        or list(material["resend_ids"]) != authorization.get("resend_ids")  # type: ignore[arg-type]
        or len(material["routed_tiers"]) != 103  # type: ignore[arg-type]
    ):
        raise RuntimeError("recovered observation authorization drift")
    material.update(
        {"manifest": manifest, "attempt_id": OBS_SOURCE_ATTEMPT_ID, "recovered": True}
    )
    return material


def _recover_matched(
    *,
    root: Path,
    context: Mapping[str, object],
    observation: Mapping[str, object],
) -> dict[str, object]:
    recovery = _validate_post_matched_recovery_sources(root)
    run_dir = recovery["paths"]["matched_dir"]  # type: ignore[index]
    combined_dir = run_dir / "recovered-combined-trace"
    raw_trace, trace_manifest = _combine_trace_artifacts(
        combined_dir,
        (run_dir, run_dir / "composite-trace"),
    )
    source_manifest_path = run_dir / f"{RUN_ID}.run-manifest.json"
    repaired = _replace_manifest_trace_document(
        _read_json(source_manifest_path),
        raw_trace=raw_trace,
        trace_manifest=trace_manifest,
    )
    recovered_manifest = run_dir / f"{RUN_ID}.recovered.run-manifest.json"
    _write_json(recovered_manifest, repaired)
    verified = verify_bundle(recovered_manifest)
    if verified.attempt_state != "ABORTED" or len(verified.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("sealed matched bundle failed recovery verification")
    texts = {
        str(row["sample_id"]): str(row["text"]) for row in verified.outputs_rows
    }
    adapter = A2TContractPreservingAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        phase=MATCHED_USE_PHASE,
        use_material=observation["matched_material"],  # type: ignore[arg-type]
    )
    samples = adapter.load_split(SPLIT_ID)
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],  # type: ignore[arg-type]
    )
    return {
        "texts": texts,
        "manifest": recovered_manifest,
        "outputs": run_dir / f"{RUN_ID}.outputs.jsonl",
        "attempt_id": MATCHED_SOURCE_ATTEMPT_ID,
        "run_dir": run_dir,
        "binding": binding,
        "request_source_run_dir": run_dir,
        "recovered": True,
    }


def _run_m0(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    adapter = A2TContractPreservingAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        phase=M0_DIRECT_PHASE,
    )
    samples = adapter.load_split(SPLIT_ID)
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],  # type: ignore[arg-type]
    )
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir,
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix="cpv2m0",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
    )
    summary = run_direct_phase(
        adapter=adapter,
        core_client=client,
        split_id=SPLIT_ID,
        speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
        slot_count=int(context["composed"].values["profile_slot_count"]),  # type: ignore[union-attr]
        decoding_params=_decoding(context),
    )
    client_summary = client.close()
    trace_hash = client_summary.get("trace_manifest_hash")
    if not isinstance(trace_hash, str) or client_summary.get("request_count") != SPLIT_COUNT:
        raise RuntimeError("M0 trace or contact accounting drift")
    rows, cost = build_phase_bundle_material(
        summary,
        _trace_documents(run_dir),
        phase=M0_DIRECT_PHASE,
        umbrella_lock_sha256=str(client_summary["cost"]["umbrella_lock_sha256"]),  # type: ignore[index]
    )
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=trace_hash,
        cost=cost,
        expected_attempt_state="OPENED",
    )
    return {
        "texts": _phase_responses(summary),
        "outputs": outputs,
        "manifest": manifest,
        "attempt_id": attempt_id,
        "binding": binding,
        "run_dir": run_dir,
    }


def _run_observation(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
    lock_sha256: str,
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    adapter = A2TContractPreservingAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        phase=OBSERVATION_PHASE,
    )
    samples = adapter.load_split(SPLIT_ID)
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],  # type: ignore[arg-type]
    )
    sink = TraceSink(run_dir, RUN_ID)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir / "transport-trace",
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix="cpv2obs",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
    )
    values = context["composed"].values  # type: ignore[union-attr]
    summary = run_phase(
        phase=OBSERVATION_PHASE,
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        split_id=SPLIT_ID,
        knowledge_snapshot=context["snapshot"],
        speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
        trace_sink=sink,
        slot_count=int(values["profile_slot_count"]),
        queue_depth=(
            int(values["profile_slot_count"])
            * int(values["profile_queue_depth_multiplier"])
        ),
        decoding_params=_decoding(context),
    )
    trace_hash, client_summary = _close_phase_traces(sink, client)
    rows, cost = build_phase_bundle_material(
        summary,
        _trace_documents(run_dir),
        phase=OBSERVATION_PHASE,
        umbrella_lock_sha256=lock_sha256,
    )
    if client_summary.get("request_count") != SPLIT_COUNT:
        raise RuntimeError("observation contact accounting drift")
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=trace_hash,
        cost=cost,
        expected_attempt_state="OPENED",
    )
    material = _materialize_observation(context, _phase_responses(summary))
    _write_observation_receipts(run_dir, material)
    if not abort_attempt_if_opened(
        root,
        RUN_ID,
        attempt_id,
        reason="observation-only attempt sealed; task scoring remains closed",
    ):
        raise RuntimeError("observation attempt did not reach terminal ABORTED state")
    material.update({"manifest": manifest, "outputs": outputs, "attempt_id": attempt_id})
    return material


def _open_use_arm(
    *,
    phase: str,
    root: Path,
    context: Mapping[str, object],
    observation: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    material_key = (
        "matched_material" if phase == MATCHED_USE_PHASE else "shuffled_material"
    )
    full_material = observation[material_key]
    adapter = A2TContractPreservingAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        phase=phase,
        use_material=full_material,  # type: ignore[arg-type]
    )
    samples = adapter.load_split(SPLIT_ID)
    routed_ids = tuple(sample.sample_id for sample in samples)
    packet_bindings = {
        sample_id: context["packet_bindings"][sample_id]  # type: ignore[index]
        for sample_id in routed_ids
    }
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],  # type: ignore[arg-type]
    )
    sink = TraceSink(run_dir, RUN_ID)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir / "transport-trace",
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix=("cpv2matched" if phase == MATCHED_USE_PHASE else "cpv2shuffled"),
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    canary_ids = tuple(observation["canary_ids"])  # type: ignore[arg-type]
    canary_material = {
        sample_id: full_material[sample_id]  # type: ignore[index]
        for sample_id in canary_ids
    }
    canary_adapter = A2TContractPreservingAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        phase=phase,
        use_material=canary_material,
    )
    values = context["composed"].values  # type: ignore[union-attr]
    canary_summary = run_phase(
        phase=phase,
        data_root=root,
        plan=plan,
        adapter=canary_adapter,
        core_client=client,
        split_id=SPLIT_ID,
        knowledge_snapshot=context["snapshot"],
        speech_packet_bindings={sample_id: packet_bindings[sample_id] for sample_id in canary_ids},
        trace_sink=sink,
        slot_count=int(values["profile_slot_count"]),
        queue_depth=(
            int(values["profile_slot_count"])
            * int(values["profile_queue_depth_multiplier"])
        ),
        decoding_params=_decoding(context),
        liveness_receipt=observation["receipt"],
    )
    return {
        "phase": phase,
        "plan": plan,
        "attempt_id": attempt_id,
        "run_dir": run_dir,
        "binding": binding,
        "sink": sink,
        "client": client,
        "packet_bindings": packet_bindings,
        "full_material": full_material,
        "routed_ids": routed_ids,
        "canary_ids": canary_ids,
        "canary_summary": canary_summary,
        "canary_texts": _phase_responses(canary_summary),
    }


def _close_stopped_use_arm(arm: Mapping[str, object]) -> None:
    trace_hash, client_summary = _close_phase_traces(arm["sink"], arm["client"])
    _write_json(
        Path(arm["run_dir"]) / "canary-stop-trace-receipt.json",
        {
            "phase": arm["phase"],
            "attempt_id": arm["attempt_id"],
            "primary_trace_manifest_sha256": trace_hash,
            "transport": dict(client_summary),
            "canary_contacts": len(arm["canary_ids"]),  # type: ignore[arg-type]
            "remaining_contacts": 0,
        },
    )


def _complete_use_arm(
    *,
    arm: Mapping[str, object],
    root: Path,
    context: Mapping[str, object],
    observation: Mapping[str, object],
    m0: Mapping[str, object],
    session_receipt_path: Path,
    lock_sha256: str,
    variant: str,
) -> dict[str, object]:
    canary_ids = set(arm["canary_ids"])  # type: ignore[arg-type]
    remaining_ids = tuple(
        sample_id
        for sample_id in arm["routed_ids"]  # type: ignore[union-attr]
        if sample_id not in canary_ids
    )
    if remaining_ids:
        remaining_material = {
            sample_id: arm["full_material"][sample_id]  # type: ignore[index]
            for sample_id in remaining_ids
        }
        adapter = A2TContractPreservingAdapter(
            context["lock"],  # type: ignore[arg-type]
            root,
            repo_root=REPO,
            receipt_items=context["items"],  # type: ignore[arg-type]
            phase=str(arm["phase"]),
            use_material=remaining_material,
        )
        values = context["composed"].values  # type: ignore[union-attr]
        remaining_summary = run_phase(
            phase=str(arm["phase"]),
            data_root=root,
            plan=arm["plan"],
            adapter=adapter,
            core_client=arm["client"],
            split_id=SPLIT_ID,
            knowledge_snapshot=context["snapshot"],
            speech_packet_bindings={
                sample_id: arm["packet_bindings"][sample_id]  # type: ignore[index]
                for sample_id in remaining_ids
            },
            trace_sink=arm["sink"],
            slot_count=int(values["profile_slot_count"]),
            queue_depth=(
                int(values["profile_slot_count"])
                * int(values["profile_queue_depth_multiplier"])
            ),
            decoding_params=_decoding(context),
            liveness_receipt=observation["receipt"],
        )
    else:
        remaining_summary = SimpleNamespace(results=())
    summary = _combine_phase_summaries(
        arm["canary_summary"],
        remaining_summary,
        expected_ids=arm["routed_ids"],  # type: ignore[arg-type]
    )
    primary_trace_hash, client_summary = _close_phase_traces(
        arm["sink"], arm["client"]
    )
    phase_rows, cost = build_phase_bundle_material(
        summary,
        _trace_documents(Path(arm["run_dir"])),
        phase=str(arm["phase"]),
        umbrella_lock_sha256=lock_sha256,
    )
    if client_summary.get("request_count") != len(arm["routed_ids"]):  # type: ignore[arg-type]
        raise RuntimeError(f"{arm['phase']} contact accounting drift")
    use_texts = merge_canary_and_remaining(
        canary=arm["canary_texts"],  # type: ignore[arg-type]
        remaining=_phase_responses(remaining_summary) if remaining_ids else {},
        expected_ids=arm["routed_ids"],  # type: ignore[arg-type]
    )
    request_ids = _request_ids_from_rows(phase_rows)
    composite = build_use_composite_texts(
        m0_texts=m0["texts"],  # type: ignore[arg-type]
        use_texts=use_texts,
        routed_ids=arm["routed_ids"],  # type: ignore[arg-type]
    )
    m0_path = Path(m0["outputs"])
    source_by_id = {
        sample_id: (
            {
                "action": (
                    "USE_MATCHED"
                    if arm["phase"] == MATCHED_USE_PHASE
                    else "USE_SHUFFLED_EVIDENCE"
                ),
                "source_request_id": request_ids[sample_id],
                "source_primary_trace_manifest_sha256": primary_trace_hash,
            }
            if sample_id in request_ids
            else {
                "action": "STOP_M0",
                "source_artifact_path": str(m0_path),
                "source_artifact_sha256": _sha256_file(m0_path),
            }
        )
        for sample_id in composite
    }
    composite_dir = Path(arm["run_dir"]) / "composite-trace"
    composite_sink = TraceSink(composite_dir, RUN_ID)
    rows = emit_composite_rows(
        texts=composite,
        source_by_id=source_by_id,
        sink=composite_sink,
        variant=variant,
    )
    composite_trace_hash = composite_sink.close()
    outputs = Path(arm["run_dir"]) / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=arm["plan"],  # type: ignore[arg-type]
        run_dir=Path(arm["run_dir"]),
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=composite_trace_hash,
        cost=cost,
        expected_attempt_state="OPENED",
    )
    _write_json(
        Path(arm["run_dir"]) / "phase-receipt.json",
        {
            "phase": arm["phase"],
            "variant": variant,
            "attempt_id": arm["attempt_id"],
            "manifest": str(manifest),
            "manifest_sha256": _sha256_file(manifest),
            "outputs_sha256": _sha256_file(outputs),
            "primary_trace_manifest_sha256": primary_trace_hash,
            "transport_trace_manifest_sha256": client_summary.get("trace_manifest_hash"),
            "canary_contacts": len(canary_ids),
            "remaining_contacts": len(remaining_ids),
            "routed_count": len(arm["routed_ids"]),  # type: ignore[arg-type]
            "fallback_count": SPLIT_COUNT - len(arm["routed_ids"]),  # type: ignore[arg-type]
            "cost": cost,
        },
    )
    return {
        "texts": composite,
        "use_texts": use_texts,
        "manifest": manifest,
        "outputs": outputs,
        "attempt_id": arm["attempt_id"],
        "run_dir": arm["run_dir"],
        "binding": arm["binding"],
        "request_source_run_dir": arm["run_dir"],
    }


def _continue_shuffled_after_canary(
    *,
    root: Path,
    context: Mapping[str, object],
    observation: Mapping[str, object],
    m0: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
    lock_sha256: str,
) -> dict[str, object]:
    _validate_post_matched_recovery_sources(root)
    old_run_dir = POST_MATCHED_SOURCE_FLIGHT / "shuffled-composite"
    old_trace = _trace_documents(old_run_dir)
    canary_texts, _old_request_ids = _responses_from_trace(old_trace)
    canary_ids = tuple(observation["canary_ids"])  # type: ignore[arg-type]
    if set(canary_texts) != set(canary_ids):
        raise RuntimeError("sealed shuffled canary identities drift")
    full_material = observation["shuffled_material"]
    routed_ids = tuple(sorted(observation["routed_tiers"]))  # type: ignore[arg-type]
    remaining_ids = tuple(
        sample_id for sample_id in routed_ids if sample_id not in set(canary_ids)
    )
    if len(remaining_ids) != 95:
        raise RuntimeError("shuffled recovery must contain exactly 95 new contacts")
    remaining_material = {
        sample_id: full_material[sample_id]  # type: ignore[index]
        for sample_id in remaining_ids
    }
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    adapter = A2TContractPreservingAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        phase=SHUFFLED_USE_PHASE,
        use_material=remaining_material,
    )
    samples = adapter.load_split(SPLIT_ID)
    if {sample.sample_id for sample in samples} != set(remaining_ids):
        raise RuntimeError("shuffled recovery adapter identity drift")
    packet_bindings = {
        sample_id: context["packet_bindings"][sample_id]  # type: ignore[index]
        for sample_id in remaining_ids
    }
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],  # type: ignore[arg-type]
    )
    primary_dir = run_dir / "primary-trace"
    sink = TraceSink(primary_dir, RUN_ID)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir / "transport-trace",
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix="cpv2shuffledrecovery",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    values = context["composed"].values  # type: ignore[union-attr]
    summary = run_phase(
        phase=SHUFFLED_USE_PHASE,
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        split_id=SPLIT_ID,
        knowledge_snapshot=context["snapshot"],
        speech_packet_bindings=packet_bindings,
        trace_sink=sink,
        slot_count=int(values["profile_slot_count"]),
        queue_depth=(
            int(values["profile_slot_count"])
            * int(values["profile_queue_depth_multiplier"])
        ),
        decoding_params=_decoding(context),
        liveness_receipt=observation["receipt"],
    )
    primary_trace_hash, client_summary = _close_phase_traces(sink, client)
    phase_rows, cost = build_phase_bundle_material(
        summary,
        _trace_documents(primary_dir),
        phase=SHUFFLED_USE_PHASE,
        umbrella_lock_sha256=lock_sha256,
    )
    if client_summary.get("request_count") != len(remaining_ids):
        raise RuntimeError("shuffled recovery contact accounting drift")
    remaining_texts = _phase_responses(summary)
    use_texts = merge_canary_and_remaining(
        canary=canary_texts,
        remaining=remaining_texts,
        expected_ids=routed_ids,
    )
    composite = build_use_composite_texts(
        m0_texts=m0["texts"],  # type: ignore[arg-type]
        use_texts=use_texts,
        routed_ids=routed_ids,
    )
    new_request_ids = _request_ids_from_rows(phase_rows)
    old_trace_path = old_run_dir / f"{RUN_ID}.trace.jsonl"
    m0_path = Path(m0["outputs"])
    source_by_id: dict[str, dict[str, str]] = {}
    for sample_id in composite:
        if sample_id in canary_texts:
            source_by_id[sample_id] = {
                "action": "USE_SHUFFLED_EVIDENCE_CANARY_REUSE",
                "source_artifact_path": str(old_trace_path),
                "source_artifact_sha256": _sha256_file(old_trace_path),
            }
        elif sample_id in new_request_ids:
            source_by_id[sample_id] = {
                "action": "USE_SHUFFLED_EVIDENCE_RECOVERY",
                "source_request_id": new_request_ids[sample_id],
            }
        else:
            source_by_id[sample_id] = {
                "action": "STOP_M0",
                "source_artifact_path": str(m0_path),
                "source_artifact_sha256": _sha256_file(m0_path),
            }
    composite_dir = run_dir / "composite-trace"
    composite_sink = TraceSink(composite_dir, RUN_ID)
    rows = emit_composite_rows(
        texts=composite,
        source_by_id=source_by_id,
        sink=composite_sink,
        variant="shuffled-evidence",
    )
    composite_trace_hash = composite_sink.close()
    bundle_dir = run_dir / "complete-bundle"
    _combine_trace_artifacts(bundle_dir, (primary_dir, composite_dir))
    outputs = bundle_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=bundle_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=composite_trace_hash,
        cost=cost,
        expected_attempt_state="OPENED",
    )
    _write_json(
        run_dir / "shuffled-recovery-receipt.json",
        {
            "schema": "saea-a2t-cpv2-shuffled-recovery-receipt-v1",
            "post_matched_recovery_plan_sha256": POST_MATCHED_RECOVERY_PLAN_SHA256,
            "old_canary_attempt_id": SHUFFLED_CANARY_SOURCE_ATTEMPT_ID,
            "old_canary_contacts": len(canary_ids),
            "new_attempt_id": attempt_id,
            "new_contacts": len(remaining_ids),
            "primary_trace_manifest_sha256": primary_trace_hash,
            "manifest": str(manifest),
            "manifest_sha256": _sha256_file(manifest),
            "outputs_sha256": _sha256_file(outputs),
            "cost": cost,
        },
    )
    return {
        "texts": composite,
        "use_texts": use_texts,
        "manifest": manifest,
        "outputs": outputs,
        "attempt_id": attempt_id,
        "run_dir": run_dir,
        "binding": binding,
    }


def _run_resend(
    *,
    root: Path,
    context: Mapping[str, object],
    observation: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
    matched: Mapping[str, object],
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    selected_ids = tuple(observation["resend_ids"])  # type: ignore[arg-type]
    documents = _trace_documents(Path(matched["request_source_run_dir"]))
    payloads = extract_exact_matched_payloads(documents, selected_ids)
    sink = TraceSink(run_dir, RUN_ID)
    adapter = FrozenCoreAdapter(
        gate=gate,
        plan=plan,
        arm="speech-feature-query",
        transport=transport,  # type: ignore[arg-type]
        sink=sink,
        binding=matched["binding"],  # type: ignore[arg-type]
    )
    responses: dict[str, str] = {}
    response_receipts: dict[str, dict[str, object]] = {}
    for sample_id in sorted(payloads):
        response = adapter.request(payloads[sample_id])
        responses[sample_id] = response.text
        response_receipts[sample_id] = {
            "request_id": payloads[sample_id]["request_id"],
            "request_sha256": response.request_sha256,
            "response_sha256": response.response_sha256,
            "response_text_sha256": response.response_text_sha256,
            "latency_seconds": response.latency_seconds,
        }
    composite = build_resend_composite_texts(
        matched["texts"],  # type: ignore[arg-type]
        selected_ids=selected_ids,
        resend_responses=responses,
    )
    matched_path = Path(matched["outputs"])
    source_by_id = {
        sample_id: (
            {
                "action": "RESEND_MATCHED",
                "source_request_id": str(payloads[sample_id]["request_id"]),
            }
            if sample_id in responses
            else {
                "action": "REUSE_MATCHED_COMPOSITE",
                "source_artifact_path": str(matched_path),
                "source_artifact_sha256": _sha256_file(matched_path),
            }
        )
        for sample_id in composite
    }
    rows = emit_composite_rows(
        texts=composite,
        source_by_id=source_by_id,
        sink=sink,
        variant="resend",
    )
    trace_hash = sink.close()
    cost = adapter.cost_summary()
    if cost.get("calls_used") != 16:
        raise RuntimeError("resend attempt did not account for sixteen calls")
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=trace_hash,
        cost=cost,
        expected_attempt_state="OPENED",
    )
    _write_json(
        run_dir / "resend-receipt.json",
        {
            "attempt_id": attempt_id,
            "manifest": str(manifest),
            "manifest_sha256": _sha256_file(manifest),
            "outputs_sha256": _sha256_file(outputs),
            "selected_ids": list(selected_ids),
            "responses": response_receipts,
            "cost": cost,
        },
    )
    return {
        "texts": composite,
        "responses": responses,
        "manifest": manifest,
        "outputs": outputs,
        "attempt_id": attempt_id,
    }


def _human_ledger_cells(phase: str, lock_sha256: str) -> dict[str, str]:
    return {
        "experiment_id": RUN_ID,
        "speech task/carrier": "Audio2Tool A2T-CPV2-104 discovery",
        "changed axes": phase,
        "shared code revision": f"openJiuwen {OPENJIUWEN_VERSION}",
        "model rev": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
        "dataset rev": lock_sha256,
        "MLflow run": "not uploaded",
        "effectiveness": "unread before finalization",
        "reasonableness": "complete verified 104-row scorer job",
        "efficiency": "four-worker outer parallelism across complete manifests",
        "deviations": "none",
        "decision": "pending preregistered scorer-side read",
    }


def _run_score_batch(
    *,
    mission_dir: Path,
    name: str,
    jobs: Sequence[Mapping[str, str]],
    workers: int,
    finalize: bool,
    per_job_operation: bool = False,
) -> dict[str, object]:
    jobs_path = mission_dir / f"{name}-jobs.jsonl"
    _write_jsonl(jobs_path, jobs)
    output_dir = mission_dir / name
    command = ["bash", str(REPO / "scripts/evaluate_parallel.sh")]
    if finalize and per_job_operation:
        raise RuntimeError("score batch cannot combine uniform and per-job operation modes")
    if finalize:
        command.append("--finalize")
    elif per_job_operation:
        command.append("--per-job-operation")
    command.extend(
        [
            "--jobs",
            str(jobs_path),
            "--output-dir",
            str(output_dir),
            "--workers",
            str(workers),
        ]
    )
    completed = subprocess.run(
        command,
        cwd=REPO,
        env={
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}:{os.environ.get('PATH', '')}",
            "PYTHONDONTWRITEBYTECODE": "1",
        },
        check=False,
        text=True,
        capture_output=True,
    )
    (mission_dir / f"{name}.stdout.log").write_text(
        completed.stdout, encoding="utf-8", newline="\n"
    )
    (mission_dir / f"{name}.stderr.log").write_text(
        completed.stderr, encoding="utf-8", newline="\n"
    )
    if completed.returncode != 0:
        raise RuntimeError(f"outer-parallel official scoring exited {completed.returncode}")
    summary = _read_json(output_dir / "batch-summary.json")
    if summary.get("failed") != 0 or summary.get("succeeded") != len(jobs):
        raise RuntimeError("outer-parallel official scoring did not settle every job")
    return summary


def _parallel_finalize(
    *,
    mission_dir: Path,
    lock_sha256: str,
    m0: Mapping[str, object],
    matched: Mapping[str, object],
    shuffled: Mapping[str, object],
    resend: Mapping[str, object],
) -> dict[str, object]:
    jobs: list[dict[str, str]] = []
    for job_id, phase, result, operation in (
        ("contract-v2-m0-direct", "same-flight direct M0", m0, "score"),
        ("contract-v2-matched-composite", "matched evidence", matched, "score"),
        (
            "contract-v2-shuffled-composite",
            "same-tier shuffled evidence",
            shuffled,
            "score",
        ),
        (
            "contract-v2-resend-composite",
            "exact matched request replay",
            resend,
            "finalize",
        ),
    ):
        job = {
            "job_id": job_id,
            "manifest": str(result["manifest"]),
            "operation": operation,
        }
        if operation == "finalize":
            cells = mission_dir / f"{job_id}-ledger-cells.json"
            _write_json(cells, _human_ledger_cells(phase, lock_sha256))
            job["ledger_cells"] = str(cells)
        jobs.append(job)
    return _run_score_batch(
        mission_dir=mission_dir,
        name="wave1-parallel-finalize",
        jobs=jobs,
        workers=4,
        finalize=False,
        per_job_operation=True,
    )


def _query_group(item: Mapping[str, object]) -> str:
    value = item.get("query_block")
    if not isinstance(value, str) or not value:
        raise RuntimeError("receipt item lacks its frozen query block")
    return value


def _score_text(expected: Sequence[object], text: str):
    predicted, _parsed = parse_tool_calls_text(text)
    return score_item(expected, predicted)  # type: ignore[arg-type]


def _terminal_policy_attempt_state(value: str) -> str:
    if value not in {"ABORTED", "FINALIZED"}:
        raise RuntimeError("policy derivative requires a terminal source attempt")
    return value


def _postseal_policy_read(
    *,
    root: Path,
    context: Mapping[str, object],
    mission_dir: Path,
    session_receipt_path: Path,
    observation: Mapping[str, object],
    canary_report: cascade_v2.StructuralCanaryReport,
    m0: Mapping[str, object],
    matched: Mapping[str, object],
    shuffled: Mapping[str, object],
    resend: Mapping[str, object],
    policy_attempt_id: str,
    policy_attempt_state: str,
) -> dict[str, object]:
    expected = load_expected_calls(context["lock"], root, repo_root=REPO)  # type: ignore[arg-type]
    items_by_id = {
        str(item["sample_id"]): item
        for item in context["items"]  # type: ignore[union-attr]
    }
    outcomes: list[selftx.SelfTranscriptOutcome] = []
    for sample_id in sorted(context["sample_ids"]):  # type: ignore[arg-type]
        route = observation["routes"][sample_id]  # type: ignore[index]
        transcript = observation["transcripts"][sample_id]  # type: ignore[index]
        gold = expected[sample_id]
        outcomes.append(
            selftx.SelfTranscriptOutcome(
                sample_id=sample_id,
                group_id=_query_group(items_by_id[sample_id]),
                state=selftx.extract_runtime_state(
                    transcript=transcript,
                    route=route,
                    m0_response=m0["texts"][sample_id],  # type: ignore[index]
                ),
                route_available=route.available,
                top5_gold_tool_correct=(
                    route.available
                    and {call.name for call in gold}.issubset(set(route.task_targets))
                ),
                stop_score=_score_text(gold, m0["texts"][sample_id]),  # type: ignore[index]
                matched_score=_score_text(gold, matched["texts"][sample_id]),  # type: ignore[index]
                shuffled_score=_score_text(gold, shuffled["texts"][sample_id]),  # type: ignore[index]
            )
        )
    matched_exact = sum(item.matched_score.exact_match for item in outcomes)
    resend_exact = sum(
        _score_text(expected[item.sample_id], resend["texts"][item.sample_id]).exact_match  # type: ignore[index]
        for item in outcomes
    )
    resend_floor = abs(int(matched_exact - resend_exact))
    report = cascade_v2.evaluate_policy(
        outcomes,
        liveness_passed=True,
        canary_passed=canary_report.passed,
        resend_absolute_exact_count_difference=resend_floor,
    )
    actions = {
        decision.outcome.sample_id: decision.action for decision in report.decisions
    }
    policy_texts = build_policy_composite_texts(
        m0_texts=m0["texts"],  # type: ignore[arg-type]
        matched_texts=matched["texts"],  # type: ignore[arg-type]
        actions=actions,
    )
    run_dir = mission_dir / "policy-composite"
    sink = TraceSink(run_dir, RUN_ID)
    matched_path = Path(matched["outputs"])
    m0_path = Path(m0["outputs"])
    source_by_id = {
        sample_id: (
            {
                "action": "USE_MATCHED",
                "source_artifact_path": str(matched_path),
                "source_artifact_sha256": _sha256_file(matched_path),
            }
            if actions[sample_id] == selftx.USE_MATCHED
            else {
                "action": "STOP_M0",
                "source_artifact_path": str(m0_path),
                "source_artifact_sha256": _sha256_file(m0_path),
            }
        )
        for sample_id in policy_texts
    }
    rows = emit_composite_rows(
        texts=policy_texts,
        source_by_id=source_by_id,
        sink=sink,
        variant="policy",
    )
    trace_hash = sink.close()
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    policy_attempt_state = _terminal_policy_attempt_state(policy_attempt_state)
    plan = _execution_plan(policy_attempt_id)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=trace_hash,
        cost={
            "calls_used": 0,
            "audio_seconds_used": 0.0,
            "latency_seconds_total": 0.0,
            "prompt_tokens_total": 0,
            "completion_tokens_total": 0,
            "tool_calls": SPLIT_COUNT,
            "umbrella_lock_sha256": verify_bundle(matched["manifest"]).manifest["cost"][  # type: ignore[index]
                "umbrella_lock_sha256"
            ],
            "derivation": "model-free cross-fitted composition from sealed same-flight M0 and matched outputs",
        },
        expected_attempt_state=policy_attempt_state,
    )
    wave2 = _run_score_batch(
        mission_dir=mission_dir,
        name="wave2-policy-score",
        jobs=(
            {
                "job_id": "contract-v2-crossfit-policy-composite",
                "manifest": str(manifest),
            },
        ),
        workers=1,
        finalize=False,
    )
    result = {
        "schema": "saea-a2t-contract-preserving-policy-result-v2",
        "run_id": RUN_ID,
        "promotion_passed": report.promotion_passed,
        "liveness": asdict(observation["report"]),  # type: ignore[arg-type]
        "structural_canary": canary_report.as_json(),
        "metrics": asdict(report.metrics),
        "gates": dict(report.gates),
        "state_class_counts": dict(report.state_class_counts),
        "resend_absolute_exact_count_difference": resend_floor,
        "actions": actions,
        "policy_manifest": str(manifest),
        "policy_manifest_sha256": _sha256_file(manifest),
        "policy_outputs": str(outputs),
        "policy_outputs_sha256": _sha256_file(outputs),
        "wave2_official_score": wave2,
        "decision": (
            "permit only a separate block-disjoint approximately-104 support proposal"
            if report.promotion_passed
            else "close contract-preserving cascade v2; no support or scale"
        ),
    }
    _write_json(mission_dir / "policy-result.json", result)
    return result


def _stop_service(
    session: object,
    *,
    runtime_receipt: Mapping[str, object],
    receipt_path: Path,
) -> None:
    stop_session(
        session,
        runtime_receipt=runtime_receipt,
        runtime_root=RUNTIME_ROOT,
        force_after_timeout=True,
        receipt_path=receipt_path,
    )


def _recover_canary_report(
    context: Mapping[str, object], observation: Mapping[str, object]
) -> cascade_v2.StructuralCanaryReport:
    matched_texts, _matched_requests = _responses_from_trace(
        _trace_documents(POST_MATCHED_SOURCE_FLIGHT / "matched-composite")
    )
    shuffled_texts, _shuffled_requests = _responses_from_trace(
        _trace_documents(POST_MATCHED_SOURCE_FLIGHT / "shuffled-composite")
    )
    canary_ids = tuple(observation["canary_ids"])  # type: ignore[arg-type]
    canary_tiers = {
        sample_id: observation["routed_tiers"][sample_id]  # type: ignore[index]
        for sample_id in canary_ids
    }
    report = cascade_v2.evaluate_structural_canary(
        matched={sample_id: matched_texts[sample_id] for sample_id in canary_ids},
        shuffled={sample_id: shuffled_texts[sample_id] for sample_id in canary_ids},
        sample_tiers=canary_tiers,
        registry_names=context["registry_names"],  # type: ignore[arg-type]
    )
    if report.as_json() != _read_json(
        POST_MATCHED_SOURCE_FLIGHT / "structural-canary-report.json"
    ):
        raise RuntimeError("recovered structural canary report drift")
    return report


def _launch(root: Path, *, recover_post_shuffled_failure: bool) -> Mapping[str, object]:
    context = _static_preflight(root)
    if not recover_post_shuffled_failure:
        raise RuntimeError(
            "the post-shuffled recovery is required; all 414 prior contacts are sealed"
        )
    _validate_m0_recovery_sources(root)
    _validate_post_matched_recovery_sources(root)
    _validate_post_shuffled_recovery_sources(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = root / "runs" / RUN_ID / f"flight-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    attempt_ids = {
        "m0": M0_SOURCE_ATTEMPT_ID,
        "observation": OBS_SOURCE_ATTEMPT_ID,
        "matched": MATCHED_SOURCE_ATTEMPT_ID,
        "shuffled_canary": SHUFFLED_CANARY_SOURCE_ATTEMPT_ID,
        "shuffled": SHUFFLED_SOURCE_ATTEMPT_ID,
        "resend": f"attempt-{stamp.lower()}-cpv2resend",
    }
    m0 = _recover_m0(root, context)
    observation = _recover_observation(root, context)
    matched = _recover_matched(
        root=root,
        context=context,
        observation=observation,
    )
    canary_report = _recover_canary_report(context, observation)
    if not canary_report.passed:
        raise RuntimeError("sealed structural canary no longer passes")
    shuffled = _recover_shuffled(root, context)
    selected_ids = tuple(observation["resend_ids"])  # type: ignore[arg-type]
    exact_payloads = extract_exact_matched_payloads(
        _trace_documents(Path(matched["request_source_run_dir"])), selected_ids
    )
    if len(exact_payloads) != 16:
        raise RuntimeError("post-shuffled recovery did not bind sixteen exact resends")
    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    values = context["composed"].values  # type: ignore[union-attr]
    model_root = Path(str(values["model_materialization_root"]))
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=str(RUNTIME_RECEIPT_RELPATH),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=model_root,
    )
    lock_sha256 = gate.assert_model_touch_allowed(
        _execution_plan(attempt_ids["resend"]), full_hash=True
    )
    parsed_url = urlparse(str(values["base_url"]))
    if parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.port is None:
        raise RuntimeError("decoder base_url must be an explicit loopback port")
    service_dir = mission_dir / "service"
    service_dir.mkdir()
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = None
    started = time.perf_counter()
    try:
        session = start_session(
            runtime_root=RUNTIME_ROOT,
            data_root=root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=parsed_url.port,
            session_id=f"{RUN_ID}-SESSION-{stamp}",
            extra_argv=tuple(values["server_args"]),
            extra_env=dict(values.get("server_env", {})),
            receipt_path=session_receipt,
            ready_timeout_seconds=600.0,
            server_log_path=service_dir / "server.log",
            role="inference",
            model_root=model_root,
        )
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
        )
        resend = _run_resend(
            root=root,
            context=context,
            observation=observation,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["resend"],
            run_dir=mission_dir / "resend-composite",
            session_receipt_path=session_receipt,
            matched=matched,
        )
        _stop_service(
            session,
            runtime_receipt=runtime_receipt,
            receipt_path=stop_receipt,
        )
        session = None
        wave1 = _parallel_finalize(
            mission_dir=mission_dir,
            lock_sha256=lock_sha256,
            m0=m0,
            matched=matched,
            shuffled=shuffled,
            resend=resend,
        )
        expected_states = ("ABORTED", "ABORTED", "ABORTED", "FINALIZED")
        for result, expected_state in zip(
            (m0, matched, shuffled, resend), expected_states, strict=True
        ):
            if verify_bundle(result["manifest"]).attempt_state != expected_state:  # type: ignore[arg-type]
                raise RuntimeError("official score wave left an unexpected attempt state")
        policy = _postseal_policy_read(
            root=root,
            context=context,
            mission_dir=mission_dir,
            session_receipt_path=session_receipt,
            observation=observation,
            canary_report=canary_report,
            m0=m0,
            matched=matched,
            shuffled=shuffled,
            resend=resend,
            policy_attempt_id=attempt_ids["shuffled"],
            policy_attempt_state="ABORTED",
        )
        receipt = {
            "schema": "saea-a2t-contract-preserving-flight-receipt-v2",
            "run_id": RUN_ID,
            "status": "SCORED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "umbrella_lock_sha256": lock_sha256,
            "session_receipt": str(session_receipt),
            "liveness": asdict(observation["report"]),
            "structural_canary": canary_report.as_json(),
            "attempts": {
                "m0": {
                    "attempt_id": attempt_ids["m0"],
                    "state": "ABORTED_RECOVERED_AND_SCORED_READ_ONLY",
                    "recontacts": 0,
                },
                "observation": {
                    "attempt_id": attempt_ids["observation"],
                    "state": "ABORTED_RECOVERED_OBSERVATION_ONLY_SUCCESS",
                    "recontacts": 0,
                },
                "matched": {
                    "attempt_id": attempt_ids["matched"],
                    "state": "ABORTED_RECOVERED_AND_SCORED_READ_ONLY",
                    "recontacts": 0,
                },
                "shuffled_canary": {
                    "attempt_id": attempt_ids["shuffled_canary"],
                    "state": "ABORTED_SOURCE_REUSED",
                    "recontacts": 0,
                },
                "shuffled": {
                    "attempt_id": attempt_ids["shuffled"],
                    "state": "ABORTED_RECOVERED_AND_SCORED_READ_ONLY",
                    "recontacts": 0,
                },
                "resend": {
                    "attempt_id": attempt_ids["resend"],
                    "state": "FINALIZED",
                },
            },
            "wave1_parallel_official_finalizer": wave1,
            "post_matched_recovery_plan_sha256": POST_MATCHED_RECOVERY_PLAN_SHA256,
            "post_shuffled_recovery_plan_sha256": (
                POST_SHUFFLED_RECOVERY_PLAN_SHA256
            ),
            "policy_result": policy,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        for attempt_id in attempt_ids.values():
            abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _write_json(
            mission_dir / "failure-receipt.json",
            {
                "schema": "saea-a2t-contract-preserving-flight-failure-v2",
                "run_id": RUN_ID,
                "attempt_ids": attempt_ids,
                "error": repr(error),
            },
        )
        raise
    finally:
        if session is not None:
            _stop_service(
                session,
                runtime_receipt=runtime_receipt,
                receipt_path=stop_receipt,
            )


def _recover_post_wave1(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    _validate_m0_recovery_sources(root)
    _validate_post_matched_recovery_sources(root)
    _validate_post_shuffled_recovery_sources(root)
    wave1_recovery = _validate_post_wave1_recovery_sources(root)
    m0 = _recover_m0(root, context)
    observation = _recover_observation(root, context)
    matched = _recover_matched(
        root=root,
        context=context,
        observation=observation,
    )
    shuffled = _recover_shuffled(root, context)
    resend = _recover_resend(root, context)
    canary_report = _recover_canary_report(context, observation)
    if not canary_report.passed:
        raise RuntimeError("sealed structural canary no longer passes")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = root / "runs" / RUN_ID / f"policy-recovery-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"policy recovery directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    started = time.perf_counter()
    try:
        policy = _postseal_policy_read(
            root=root,
            context=context,
            mission_dir=mission_dir,
            session_receipt_path=wave1_recovery["paths"]["session_receipt"],  # type: ignore[index]
            observation=observation,
            canary_report=canary_report,
            m0=m0,
            matched=matched,
            shuffled=shuffled,
            resend=resend,
            policy_attempt_id=SHUFFLED_SOURCE_ATTEMPT_ID,
            policy_attempt_state="ABORTED",
        )
        receipt = {
            "schema": "saea-a2t-contract-preserving-policy-recovery-receipt-v1",
            "run_id": RUN_ID,
            "status": "SCORED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "model_recontacts": 0,
            "wave1_rescores": 0,
            "wave1_source_batch_summary": str(
                wave1_recovery["paths"]["wave1_summary"]  # type: ignore[index]
            ),
            "wave1_source_batch_summary_sha256": _sha256_file(
                wave1_recovery["paths"]["wave1_summary"]  # type: ignore[index]
            ),
            "post_wave1_recovery_plan_sha256": POST_WAVE1_RECOVERY_PLAN_SHA256,
            "policy_result": policy,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        _write_json(
            mission_dir / "failure-receipt.json",
            {
                "schema": "saea-a2t-contract-preserving-policy-recovery-failure-v1",
                "run_id": RUN_ID,
                "error": repr(error),
                "model_recontacts": 0,
                "wave1_rescores": 0,
            },
        )
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--recover-m0-manifest-failure", action="store_true")
    parser.add_argument("--recover-post-matched-failure", action="store_true")
    parser.add_argument("--recover-post-shuffled-failure", action="store_true")
    parser.add_argument("--recover-post-wave1-failure", action="store_true")
    args = parser.parse_args(argv)
    root = data_root()
    if args.preflight_only:
        context = _static_preflight(root)
        recovery = None
        post_matched_recovery = None
        post_shuffled_recovery = None
        post_wave1_recovery = None
        if args.recover_m0_manifest_failure:
            recovery = _validate_m0_recovery_sources(root)
        if args.recover_post_matched_failure:
            recovery = _validate_m0_recovery_sources(root)
            post_matched_recovery = _validate_post_matched_recovery_sources(root)
            recovered_m0 = _recover_m0(root, context)
            recovered_observation = _recover_observation(root, context)
            recovered_matched = _recover_matched(
                root=root,
                context=context,
                observation=recovered_observation,
            )
            recovered_canary = _recover_canary_report(
                context, recovered_observation
            )
        if args.recover_post_shuffled_failure:
            recovery = _validate_m0_recovery_sources(root)
            post_matched_recovery = _validate_post_matched_recovery_sources(root)
            post_shuffled_recovery = _validate_post_shuffled_recovery_sources(root)
            recovered_m0 = _recover_m0(root, context)
            recovered_observation = _recover_observation(root, context)
            recovered_matched = _recover_matched(
                root=root,
                context=context,
                observation=recovered_observation,
            )
            recovered_canary = _recover_canary_report(
                context, recovered_observation
            )
            recovered_shuffled = _recover_shuffled(root, context)
            exact_resends = extract_exact_matched_payloads(
                _trace_documents(Path(recovered_matched["request_source_run_dir"])),
                tuple(recovered_observation["resend_ids"]),  # type: ignore[arg-type]
            )
        if args.recover_post_wave1_failure:
            recovery = _validate_m0_recovery_sources(root)
            post_matched_recovery = _validate_post_matched_recovery_sources(root)
            post_shuffled_recovery = _validate_post_shuffled_recovery_sources(root)
            post_wave1_recovery = _validate_post_wave1_recovery_sources(root)
            recovered_m0 = _recover_m0(root, context)
            recovered_observation = _recover_observation(root, context)
            recovered_matched = _recover_matched(
                root=root,
                context=context,
                observation=recovered_observation,
            )
            recovered_canary = _recover_canary_report(
                context, recovered_observation
            )
            recovered_shuffled = _recover_shuffled(root, context)
            recovered_resend = _recover_resend(root, context)
            exact_resends = extract_exact_matched_payloads(
                _trace_documents(Path(recovered_matched["request_source_run_dir"])),
                tuple(recovered_observation["resend_ids"]),  # type: ignore[arg-type]
            )
        print(
            json.dumps(
                {
                    "preflight": "passed",
                    "run_id": RUN_ID,
                    "study_commit": context["commit"],
                    "samples": len(context["sample_ids"]),
                    "official_score_workers": 4,
                    "scoring_boundary": "one-complete-manifest-per-process",
                    "dataset_sharding": False,
                    "prompt_fit_margin_tokens": 12240,
                    "promotion_receipt_sha256": PROMOTION_SHA256,
                    "m0_recovery": (
                        {
                            "attempt_id": M0_SOURCE_ATTEMPT_ID,
                            "recontacts": 0,
                            "source_manifest_sha256": recovery["recovery"][  # type: ignore[index]
                                "source_manifest_sha256"
                            ],
                        }
                        if recovery is not None
                        else None
                    ),
                    "post_matched_recovery": (
                        {
                            "plan_sha256": POST_MATCHED_RECOVERY_PLAN_SHA256,
                            "prior_contacts": post_matched_recovery["plan"][  # type: ignore[index]
                                "observed_boundary"
                            ]["cumulative_calls"],
                            "maximum_new_contacts": post_matched_recovery["plan"][  # type: ignore[index]
                                "authorized_recovery"
                            ]["maximum_additional_calls"],
                            "m0_rows_verified": len(recovered_m0["texts"]),
                            "observation_rows_verified": len(
                                recovered_observation["transcripts"]  # type: ignore[arg-type]
                            ),
                            "matched_rows_verified": len(recovered_matched["texts"]),
                            "canary_passed": recovered_canary.passed,
                        }
                        if post_matched_recovery is not None
                        else None
                    ),
                    "post_shuffled_recovery": (
                        {
                            "plan_sha256": POST_SHUFFLED_RECOVERY_PLAN_SHA256,
                            "prior_contacts": post_shuffled_recovery["plan"][  # type: ignore[index]
                                "observed_boundary"
                            ]["cumulative_calls"],
                            "maximum_new_contacts": post_shuffled_recovery["plan"][  # type: ignore[index]
                                "authorized_recovery"
                            ]["maximum_additional_calls"],
                            "shuffled_rows_verified": len(
                                recovered_shuffled["texts"]
                            ),
                            "exact_resend_payloads_verified": len(exact_resends),
                        }
                        if post_shuffled_recovery is not None
                        else None
                    ),
                    "post_wave1_recovery": (
                        {
                            "plan_sha256": POST_WAVE1_RECOVERY_PLAN_SHA256,
                            "prior_model_contacts": post_wave1_recovery["plan"][  # type: ignore[index]
                                "observed_boundary"
                            ]["cumulative_model_calls"],
                            "maximum_new_model_contacts": post_wave1_recovery["plan"][  # type: ignore[index]
                                "authorized_recovery"
                            ]["maximum_additional_model_calls"],
                            "wave1_jobs_verified": post_wave1_recovery["batch"][  # type: ignore[index]
                                "succeeded"
                            ],
                            "resend_rows_verified": len(recovered_resend["texts"]),
                            "policy_source_attempt_state": "ABORTED",
                        }
                        if post_wave1_recovery is not None
                        else None
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    if not args.recover_post_wave1_failure:
        raise RuntimeError(
            "all 430 model contacts and four Wave-1 scores are sealed; "
            "--recover-post-wave1-failure is required"
        )
    print(
        json.dumps(
            _recover_post_wave1(root),
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
