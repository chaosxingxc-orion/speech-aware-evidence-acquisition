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
    transport_dir = run_dir / "transport-trace"
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=transport_dir,
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
        _trace_documents(transport_dir),
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
) -> dict[str, object]:
    jobs_path = mission_dir / f"{name}-jobs.jsonl"
    _write_jsonl(jobs_path, jobs)
    output_dir = mission_dir / name
    command = ["bash", str(REPO / "scripts/evaluate_parallel.sh")]
    if finalize:
        command.append("--finalize")
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
    for job_id, phase, result in (
        ("contract-v2-m0-direct", "same-flight direct M0", m0),
        ("contract-v2-matched-composite", "matched evidence", matched),
        ("contract-v2-shuffled-composite", "same-tier shuffled evidence", shuffled),
        ("contract-v2-resend-composite", "exact matched request replay", resend),
    ):
        cells = mission_dir / f"{job_id}-ledger-cells.json"
        _write_json(cells, _human_ledger_cells(phase, lock_sha256))
        jobs.append(
            {
                "job_id": job_id,
                "manifest": str(result["manifest"]),
                "ledger_cells": str(cells),
            }
        )
    return _run_score_batch(
        mission_dir=mission_dir,
        name="wave1-parallel-finalize",
        jobs=jobs,
        workers=4,
        finalize=True,
    )


def _query_group(item: Mapping[str, object]) -> str:
    value = item.get("query_block")
    if not isinstance(value, str) or not value:
        raise RuntimeError("receipt item lacks its frozen query block")
    return value


def _score_text(expected: Sequence[object], text: str):
    predicted, _parsed = parse_tool_calls_text(text)
    return score_item(expected, predicted)  # type: ignore[arg-type]


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
    matched_attempt_id: str,
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
    plan = _execution_plan(matched_attempt_id)
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
        expected_attempt_state="FINALIZED",
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


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = root / "runs" / RUN_ID / f"flight-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    attempt_ids = {
        "m0": f"attempt-{stamp.lower()}-cpv2m0",
        "observation": f"attempt-{stamp.lower()}-cpv2obs",
        "matched": f"attempt-{stamp.lower()}-cpv2matched",
        "shuffled": f"attempt-{stamp.lower()}-cpv2shuffled",
        "resend": f"attempt-{stamp.lower()}-cpv2resend",
    }
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
        _execution_plan(attempt_ids["m0"]), full_hash=True
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
        m0 = _run_m0(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["m0"],
            run_dir=mission_dir / "m0-direct",
            session_receipt_path=session_receipt,
        )
        observation = _run_observation(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["observation"],
            run_dir=mission_dir / "observation",
            session_receipt_path=session_receipt,
            lock_sha256=lock_sha256,
        )
        if observation["passed"] is not True:
            abort_attempt_if_opened(
                root,
                RUN_ID,
                attempt_ids["m0"],
                reason="label-free observation liveness gate failed",
            )
            _stop_service(
                session,
                runtime_receipt=runtime_receipt,
                receipt_path=stop_receipt,
            )
            session = None
            result = {
                "schema": "saea-a2t-contract-preserving-flight-receipt-v2",
                "run_id": RUN_ID,
                "status": "STOPPED_AT_LABEL_FREE_LIVENESS_GATE",
                "study_commit": context["commit"],
                "mission_dir": str(mission_dir),
                "elapsed_seconds": time.perf_counter() - started,
                "liveness": asdict(observation["report"]),
                "use_contacts": 0,
                "official_scorer_contacts": 0,
            }
            _write_json(mission_dir / "flight-receipt.json", result)
            return result

        matched_arm = _open_use_arm(
            phase=MATCHED_USE_PHASE,
            root=root,
            context=context,
            observation=observation,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["matched"],
            run_dir=mission_dir / "matched-composite",
        )
        shuffled_arm = _open_use_arm(
            phase=SHUFFLED_USE_PHASE,
            root=root,
            context=context,
            observation=observation,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["shuffled"],
            run_dir=mission_dir / "shuffled-composite",
        )
        canary_ids = tuple(observation["canary_ids"])  # type: ignore[arg-type]
        canary_tiers = {
            sample_id: observation["routed_tiers"][sample_id]  # type: ignore[index]
            for sample_id in canary_ids
        }
        canary_report = cascade_v2.evaluate_structural_canary(
            matched=matched_arm["canary_texts"],  # type: ignore[arg-type]
            shuffled=shuffled_arm["canary_texts"],  # type: ignore[arg-type]
            sample_tiers=canary_tiers,
            registry_names=context["registry_names"],  # type: ignore[arg-type]
        )
        _write_json(mission_dir / "structural-canary-report.json", canary_report.as_json())
        if not canary_report.passed:
            _close_stopped_use_arm(matched_arm)
            _close_stopped_use_arm(shuffled_arm)
            for attempt_id in (
                attempt_ids["m0"],
                attempt_ids["matched"],
                attempt_ids["shuffled"],
            ):
                abort_attempt_if_opened(
                    root,
                    RUN_ID,
                    attempt_id,
                    reason="label-free structural canary failed",
                )
            _stop_service(
                session,
                runtime_receipt=runtime_receipt,
                receipt_path=stop_receipt,
            )
            session = None
            result = {
                "schema": "saea-a2t-contract-preserving-flight-receipt-v2",
                "run_id": RUN_ID,
                "status": "STOPPED_AT_LABEL_FREE_STRUCTURAL_CANARY",
                "study_commit": context["commit"],
                "mission_dir": str(mission_dir),
                "elapsed_seconds": time.perf_counter() - started,
                "liveness": asdict(observation["report"]),
                "structural_canary": canary_report.as_json(),
                "matched_use_contacts": 8,
                "shuffled_use_contacts": 8,
                "remaining_use_contacts": 0,
                "official_scorer_contacts": 0,
            }
            _write_json(mission_dir / "flight-receipt.json", result)
            return result

        matched = _complete_use_arm(
            arm=matched_arm,
            root=root,
            context=context,
            observation=observation,
            m0=m0,
            session_receipt_path=session_receipt,
            lock_sha256=lock_sha256,
            variant="matched",
        )
        shuffled = _complete_use_arm(
            arm=shuffled_arm,
            root=root,
            context=context,
            observation=observation,
            m0=m0,
            session_receipt_path=session_receipt,
            lock_sha256=lock_sha256,
            variant="shuffled-evidence",
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
        for result in (m0, matched, shuffled, resend):
            if verify_bundle(result["manifest"]).attempt_state != "FINALIZED":  # type: ignore[arg-type]
                raise RuntimeError("official finalizer left a model attempt unsettled")
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
            matched_attempt_id=attempt_ids["matched"],
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
                "m0": {"attempt_id": attempt_ids["m0"], "state": "FINALIZED"},
                "observation": {
                    "attempt_id": attempt_ids["observation"],
                    "state": "ABORTED_OBSERVATION_ONLY_SUCCESS",
                },
                "matched": {
                    "attempt_id": attempt_ids["matched"],
                    "state": "FINALIZED",
                },
                "shuffled": {
                    "attempt_id": attempt_ids["shuffled"],
                    "state": "FINALIZED",
                },
                "resend": {
                    "attempt_id": attempt_ids["resend"],
                    "state": "FINALIZED",
                },
            },
            "wave1_parallel_official_finalizer": wave1,
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    root = data_root()
    if args.preflight_only:
        context = _static_preflight(root)
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
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(_launch(root), indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
