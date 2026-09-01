"""Launch the preregistered 104-item self-transcript cascade.

The flight seals all same-core English self-transcripts before evaluating a
label-free liveness gate. Only a passing gate opens matched and same-tier
shuffled evidence-use attempts, followed by sixteen exact matched-request
replays. The three complete 104-row prediction manifests are then finalized
by three outer worker processes; each worker invokes the unchanged official
single-process scorer exactly once and no dataset is sharded.

Gold is unavailable until every model response and complete prediction
manifest has sealed. The post-seal read builds the fixed five-fold
training-free policy, materializes one complete model-free policy manifest,
and scores that manifest once through the same official scorer.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[5]
RUNTIME_ROOT = Path("/home/chao")

if os.environ.get("PYTHONDONTWRITEBYTECODE") != "1":
    raise SystemExit("PYTHONDONTWRITEBYTECODE=1 is required")
if str(REPO / "src") not in os.environ.get("PYTHONPATH", "").split(":"):
    raise SystemExit("PYTHONPATH must contain the literal study src directory")

from speech_aware_evidence_acquisition.analysis import (  # noqa: E402
    training_free_a2t_self_transcript_cascade as cascade,
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
from speech_aware_evidence_acquisition.rails.probes.a2t_self_consistency_flight import (  # noqa: E402
    load_frozen_m0_outputs,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_bundle import (  # noqa: E402
    build_phase_bundle_material,
    build_policy_composite_texts,
    build_resend_composite_texts,
    build_use_composite_texts,
    emit_composite_rows,
    extract_exact_matched_payloads,
    select_resend_ids,
    validate_parallel_score_plan,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_flight import (  # noqa: E402
    A2TSelfTranscriptAdapter,
    MATCHED_USE_PHASE,
    OBSERVATION_PHASE,
    SHUFFLED_USE_PHASE,
    SPLIT_ID,
    build_use_material,
    run_phase,
)
from speech_aware_evidence_acquisition.reproduction.toolcall_scoring import (  # noqa: E402
    parse_tool_calls_text,
    score_item,
)

RUN_ID = "SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-self-transcript-cascade-agentloop"
EXPERIMENT_FRAGMENT = "a2t-training-free-self-transcript-cascade-104-v1"
COMPOSED_CONFIG_SHA256 = (
    "855f6c33aad2a9364ca1bef7af3eea5736edef868d9065c5c10d2b3ff749ff89"
)
PROTOCOL_SHA256 = (
    "7c4518d2e2c7a25fa2106a54e9f2398717586af197f7cf98e39ac7ef49e1bc8d"
)
SPLIT_IDENTITY_SHA256 = (
    "f5a030189cf80dcbc52899e2fa5f819bac03874f2ad3f9645fdc60c432a9bf3a"
)
RECEIPT_IDENTITY_SHA256 = (
    "516f92d9b919640969676eb10b776d9c479169fb0a387497e943c726b2191326"
)
RECEIPT_RELPATH = Path("docs/receipts/a2t/A2T-G1-104.json")
RECEIPT_SHA256 = (
    "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
)
SPLIT_COUNT = 104
SPLIT_AUDIO_SECONDS = 587.017
M0_RELPATH = Path(
    "runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/arm1-m0-outputs.jsonl"
)
M0_SHA256 = "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467"
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
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-G1-104-promotion.json"
PROMOTION_SHA256 = (
    "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
)
RUNTIME_RECEIPT_RELPATH = Path("receipts/runtime-q4km-mmproj-free.json")
CHECK_DIR = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-self-transcript-cascade-104-v1"
)
PLAN_TEMPLATE = CHECK_DIR / "execution-plan-template.json"
SCORE_PLAN = CHECK_DIR / "parallel-score-plan.json"
OPENJIUWEN_VERSION = "0.1.16.post2"
_QUERY_GROUP = re.compile(r"/query_(\d+)(?:/|$)")


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
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True, default=str)
        + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _trace_documents(run_dir: Path) -> tuple[Mapping[str, object], ...]:
    path = run_dir / f"{RUN_ID}.trace.jsonl"
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
        raise RuntimeError("runtime trace is empty")
    return tuple(documents)


def _execution_plan(attempt_id: str) -> ExecutionPlan:
    template = _read_json(PLAN_TEMPLATE)
    fields = dict(template["execution_plan"])  # type: ignore[arg-type]
    fields["attempt_id"] = attempt_id
    return ExecutionPlan(**fields).validate()


def _verified_split(sample_ids: Sequence[str]) -> VerifiedSplit:
    ids = tuple(sorted(sample_ids))
    return VerifiedSplit(
        name="A2T-G1-104",
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
    receipt_relpath = values.get("speech_native_prompt_fit_receipt")
    receipt_sha256 = values.get("speech_native_prompt_fit_receipt_sha256")
    if not isinstance(receipt_relpath, str) or not isinstance(receipt_sha256, str):
        raise RuntimeError("composed config lacks prompt-fit receipt binding")
    receipt_path = REPO / receipt_relpath
    if _sha256_file(receipt_path) != receipt_sha256:
        raise RuntimeError("prompt-fit receipt byte identity drift")
    receipt = _read_json(receipt_path)
    context, slots = _server_geometry(values)
    if (
        receipt.get("model_contact") is not False
        or receipt.get("maximum_prompt_fits_one_slot") is not True
        or receipt.get("flown_subset_receipt_sha256") != RECEIPT_SHA256
        or receipt.get("task_contract_sha256") != _sha256_text(task_contract)
        or receipt.get("context_tokens") != context
        or receipt.get("slot_count") != slots
        or receipt.get("context_tokens_per_slot") != context // slots
        or int(receipt.get("agent_state_texts", -1)) < 1
        or int(receipt.get("visible_key_facets", -1)) < 5
        or int(receipt.get("visible_values", -1)) < 6
        or int(receipt.get("context_margin_tokens", -1)) <= 0
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
    if (
        protocol_hash(
            composed.config_hash,
            str(composed.values["arm"]),
            SPLIT_IDENTITY_SHA256,
        )
        != PROTOCOL_SHA256
    ):
        raise RuntimeError("audit protocol identity drift")
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("openJiuwen version drift")
    plan_template = _read_json(PLAN_TEMPLATE)
    if (
        plan_template.get("exposure_pre_registration_id") != RUN_ID
        or plan_template.get("composed_config_sha256") != COMPOSED_CONFIG_SHA256
        or _execution_plan("attempt-20260901t000000z-selftxpre").protocol_hash
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

    m0_path = root / M0_RELPATH
    if _sha256_file(m0_path) != M0_SHA256:
        raise RuntimeError("frozen M0 output identity drift")
    m0 = load_frozen_m0_outputs(m0_path, expected_ids=sample_ids)

    promotion = _read_json(PROMOTION_RECEIPT)
    if (
        _sha256_file(PROMOTION_RECEIPT) != PROMOTION_SHA256
        or promotion.get("count") != SPLIT_COUNT
        or promotion.get("split_identity_hash") != SPLIT_IDENTITY_SHA256
    ):
        raise RuntimeError("speech packet promotion receipt drift")
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
    if len(registry) != 152:
        raise RuntimeError("tool registry row-count drift")
    snapshot_path = root / SNAPSHOT_RELPATH
    snapshot = KnowledgeSnapshot.from_frozen_json(_read_json(snapshot_path))
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise RuntimeError("knowledge snapshot identity drift")
    if set(sample_ids) & set(snapshot.source_sample_ids):
        raise RuntimeError("knowledge snapshot overlaps the flight population")
    _validate_prompt_fit(composed.values, render_tool_schemas(lock, root))
    return {
        "commit": commit,
        "composed": composed,
        "lock": lock,
        "carrier_root": carrier_root,
        "receipt": receipt,
        "items": tuple(items),
        "sample_ids": sample_ids,
        "m0": m0,
        "m0_path": m0_path,
        "snapshot": snapshot,
        "snapshot_path": snapshot_path,
        "packet_bindings": packet_bindings,
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


def _request_ids_from_rows(
    rows: Sequence[Mapping[str, object]],
) -> dict[str, str]:
    result = {str(row["sample_id"]): str(row["request_id"]) for row in rows}
    if len(result) != len(rows):
        raise RuntimeError("phase rows contain duplicate sample identities")
    return result


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
    adapter = A2TSelfTranscriptAdapter(
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
    trace_sink = TraceSink(run_dir, RUN_ID)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir / "transport-trace",
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix="selftxobs",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
    )
    decoding = dict(context["composed"].values["decoding_params"])  # type: ignore[union-attr]
    decoding.pop("id_slot", None)
    summary = run_phase(
        phase=OBSERVATION_PHASE,
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        split_id=SPLIT_ID,
        knowledge_snapshot=context["snapshot"],
        speech_packet_bindings=context["packet_bindings"],  # type: ignore[arg-type]
        trace_sink=trace_sink,
        slot_count=int(context["composed"].values["profile_slot_count"]),  # type: ignore[union-attr]
        queue_depth=(
            int(context["composed"].values["profile_slot_count"])  # type: ignore[union-attr]
            * int(context["composed"].values["profile_queue_depth_multiplier"])  # type: ignore[union-attr]
        ),
        decoding_params=decoding,
    )
    documents = _trace_documents(run_dir)
    rows, cost = build_phase_bundle_material(
        summary,
        documents,
        phase=OBSERVATION_PHASE,
        umbrella_lock_sha256=lock_sha256,
    )
    client_summary = client.close()
    if client_summary.get("request_count") != SPLIT_COUNT:
        raise RuntimeError("observation contact accounting drift")
    outputs_path = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs_path, rows)
    manifest_path = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs_path,
        trace_manifest_hash=str(client_summary["trace_manifest_hash"]),
        cost=cost,
        expected_attempt_state="OPENED",
    )
    responses = _phase_responses(summary)
    retriever = cascade.EvidenceRetriever(context["snapshot"])  # type: ignore[arg-type]
    transcripts: dict[str, cascade.TranscriptParse] = {}
    routes: dict[str, cascade.EvidenceRoute] = {}
    observations: list[cascade.ObservationRecord] = []
    tiers = {str(item["sample_id"]): str(item["tier"]) for item in context["items"]}  # type: ignore[union-attr]
    for sample_id in sorted(context["sample_ids"]):  # type: ignore[arg-type]
        parsed = cascade.validate_self_transcript(responses.get(sample_id))
        route = retriever.route(parsed.text) if parsed.valid else cascade.EvidenceRoute(
            False, (), (), (), (), 0, 0.0, ""
        )
        transcripts[sample_id] = parsed
        routes[sample_id] = route
        observations.append(
            cascade.ObservationRecord(
                sample_id=sample_id,
                tier=tiers[sample_id],
                response_received=sample_id in responses,
                transcript=parsed,
                positive_route=route.available,
            )
        )
    report = cascade.evaluate_liveness(observations)
    _write_json(
        run_dir / "liveness-report.json",
        {
            "schema": "saea-a2t-self-transcript-liveness-report-v1",
            "report": asdict(report),
            "transcripts": {
                sample_id: asdict(transcripts[sample_id])
                for sample_id in sorted(transcripts)
            },
            "routes": {
                sample_id: asdict(routes[sample_id]) for sample_id in sorted(routes)
            },
        },
    )
    aborted = abort_attempt_if_opened(
        root,
        RUN_ID,
        attempt_id,
        reason=(
            "observation-only attempt sealed successfully; no task-answer output is "
            "eligible for official scoring"
        ),
    )
    if not aborted or verify_bundle(manifest_path).attempt_state != "ABORTED":
        raise RuntimeError("observation-only attempt did not reach terminal ABORTED state")
    if not report.passed:
        return {
            "passed": False,
            "report": report,
            "manifest": manifest_path,
            "outputs": outputs_path,
            "attempt_id": attempt_id,
        }
    receipt = cascade.authorize_use_phase(observations)
    routed_tiers = {
        sample_id: tiers[sample_id]
        for sample_id, route in routes.items()
        if transcripts[sample_id].valid and route.available
    }
    resend_ids = select_resend_ids(routed_tiers, per_tier=2)
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
    _write_json(
        run_dir / "use-authorization-receipt.json",
        {
            "schema": "saea-a2t-self-transcript-use-authorization-v1",
            "liveness": asdict(receipt),
            "routed_ids": sorted(routed_tiers),
            "routed_tiers": dict(sorted(routed_tiers.items())),
            "same_tier_donors": {
                sample_id: shuffled_material[sample_id].donor_id
                for sample_id in sorted(shuffled_material)
            },
            "resend_ids": list(resend_ids),
            "sealed_before_use": True,
        },
    )
    return {
        "passed": True,
        "report": report,
        "receipt": receipt,
        "transcripts": transcripts,
        "routes": routes,
        "tiers": tiers,
        "routed_tiers": routed_tiers,
        "resend_ids": resend_ids,
        "matched_material": matched_material,
        "shuffled_material": shuffled_material,
        "manifest": manifest_path,
        "outputs": outputs_path,
        "attempt_id": attempt_id,
    }


def _run_use(
    *,
    phase: str,
    variant: str,
    root: Path,
    context: Mapping[str, object],
    observation: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
    lock_sha256: str,
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    material_key = (
        "matched_material" if phase == MATCHED_USE_PHASE else "shuffled_material"
    )
    material = observation[material_key]
    adapter = A2TSelfTranscriptAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["items"],  # type: ignore[arg-type]
        phase=phase,
        use_material=material,  # type: ignore[arg-type]
    )
    samples = adapter.load_split(SPLIT_ID)
    routed_ids = tuple(sorted(str(sample.sample_id) for sample in samples))
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
    trace_sink = TraceSink(run_dir, RUN_ID)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,  # type: ignore[arg-type]
        run_dir=run_dir / "transport-trace",
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix=("selftxmatched" if phase == MATCHED_USE_PHASE else "selftxshuffle"),
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    decoding = dict(context["composed"].values["decoding_params"])  # type: ignore[union-attr]
    decoding.pop("id_slot", None)
    summary = run_phase(
        phase=phase,
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        split_id=SPLIT_ID,
        knowledge_snapshot=context["snapshot"],
        speech_packet_bindings=packet_bindings,
        trace_sink=trace_sink,
        slot_count=int(context["composed"].values["profile_slot_count"]),  # type: ignore[union-attr]
        queue_depth=(
            int(context["composed"].values["profile_slot_count"])  # type: ignore[union-attr]
            * int(context["composed"].values["profile_queue_depth_multiplier"])  # type: ignore[union-attr]
        ),
        decoding_params=decoding,
        liveness_receipt=observation["receipt"],
    )
    documents = _trace_documents(run_dir)
    phase_rows, cost = build_phase_bundle_material(
        summary,
        documents,
        phase=phase,
        umbrella_lock_sha256=lock_sha256,
    )
    use_texts = _phase_responses(summary)
    request_ids = _request_ids_from_rows(phase_rows)
    composite = build_use_composite_texts(
        m0_texts=context["m0"],  # type: ignore[arg-type]
        use_texts=use_texts,
        routed_ids=routed_ids,
    )
    m0_path = Path(context["m0_path"])  # type: ignore[arg-type]
    source_by_id = {
        sample_id: (
            {
                "action": "USE_MATCHED" if phase == MATCHED_USE_PHASE else "USE_SHUFFLED_EVIDENCE",
                "source_request_id": request_ids[sample_id],
            }
            if sample_id in request_ids
            else {
                "action": "STOP_M0",
                "source_artifact_path": str(m0_path),
                "source_artifact_sha256": M0_SHA256,
            }
        )
        for sample_id in composite
    }
    rows = emit_composite_rows(
        texts=composite,
        source_by_id=source_by_id,
        sink=trace_sink,
        variant=variant,
    )
    client_summary = client.close()
    if client_summary.get("request_count") != len(routed_ids):
        raise RuntimeError(f"{phase} contact accounting drift")
    outputs_path = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs_path, rows)
    manifest_path = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs_path,
        trace_manifest_hash=str(client_summary["trace_manifest_hash"]),
        cost=cost,
        expected_attempt_state="OPENED",
    )
    _write_json(
        run_dir / "phase-receipt.json",
        {
            "phase": phase,
            "variant": variant,
            "attempt_id": attempt_id,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "outputs_sha256": _sha256_file(outputs_path),
            "routed_count": len(routed_ids),
            "fallback_count": SPLIT_COUNT - len(routed_ids),
            "cost": cost,
        },
    )
    return {
        "summary": summary,
        "binding": binding,
        "request_ids": request_ids,
        "texts": composite,
        "use_texts": use_texts,
        "manifest": manifest_path,
        "outputs": outputs_path,
        "attempt_id": attempt_id,
        "run_dir": run_dir,
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
    selected_ids = observation["resend_ids"]
    documents = _trace_documents(Path(matched["run_dir"]))
    payloads = extract_exact_matched_payloads(
        documents, selected_ids  # type: ignore[arg-type]
    )
    trace_sink = TraceSink(run_dir, RUN_ID)
    adapter = FrozenCoreAdapter(
        gate=gate,
        plan=plan,
        arm="speech-feature-query",
        transport=transport,  # type: ignore[arg-type]
        sink=trace_sink,
        binding=matched["binding"],  # type: ignore[arg-type]
    )
    responses: dict[str, str] = {}
    receipts: dict[str, dict[str, object]] = {}
    for sample_id in sorted(payloads):
        response = adapter.request(payloads[sample_id])
        responses[sample_id] = response.text
        receipts[sample_id] = {
            "request_id": payloads[sample_id]["request_id"],
            "request_sha256": response.request_sha256,
            "response_sha256": response.response_sha256,
            "response_text_sha256": response.response_text_sha256,
            "latency_seconds": response.latency_seconds,
        }
    composite = build_resend_composite_texts(
        matched["texts"],  # type: ignore[arg-type]
        selected_ids=selected_ids,  # type: ignore[arg-type]
        resend_responses=responses,
    )
    matched_path = Path(matched["outputs"])  # type: ignore[arg-type]
    matched_sha256 = _sha256_file(matched_path)
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
                "source_artifact_sha256": matched_sha256,
            }
        )
        for sample_id in composite
    }
    rows = emit_composite_rows(
        texts=composite,
        source_by_id=source_by_id,
        sink=trace_sink,
        variant="resend",
    )
    trace_manifest_hash = trace_sink.close()
    cost = adapter.cost_summary()
    if cost.get("calls_used") != 16:
        raise RuntimeError("resend attempt did not account for exactly sixteen calls")
    outputs_path = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs_path, rows)
    manifest_path = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs_path,
        trace_manifest_hash=trace_manifest_hash,
        cost=cost,
        expected_attempt_state="OPENED",
    )
    _write_json(
        run_dir / "resend-receipt.json",
        {
            "attempt_id": attempt_id,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "outputs_sha256": _sha256_file(outputs_path),
            "matched_outputs_sha256": matched_sha256,
            "selected_ids": list(selected_ids),  # type: ignore[arg-type]
            "responses": receipts,
            "cost": cost,
        },
    )
    return {
        "texts": composite,
        "responses": responses,
        "manifest": manifest_path,
        "outputs": outputs_path,
        "attempt_id": attempt_id,
    }


def _human_ledger_cells(phase: str, lock_sha256: str) -> dict[str, str]:
    return {
        "experiment_id": RUN_ID,
        "speech task/carrier": "Audio2Tool A2T-G1-104 discovery",
        "changed axes": phase,
        "shared code revision": f"openJiuwen {OPENJIUWEN_VERSION}",
        "model rev": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
        "dataset rev": lock_sha256,
        "MLflow run": "not uploaded",
        "effectiveness": "unread before finalization",
        "reasonableness": "complete verified 104-row composite scorer job",
        "efficiency": "three-worker outer parallelism across complete manifests",
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
    command = [
        "bash",
        str(REPO / "scripts/evaluate_parallel.sh"),
        "--finalize" if finalize else "--score",
        "--jobs",
        str(jobs_path),
        "--output-dir",
        str(output_dir),
        "--workers",
        str(workers),
    ]
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
    matched: Mapping[str, object],
    shuffled: Mapping[str, object],
    resend: Mapping[str, object],
) -> dict[str, object]:
    jobs: list[dict[str, str]] = []
    for job_id, phase, result in (
        ("self-transcript-matched-composite", "matched evidence", matched),
        (
            "self-transcript-shuffled-evidence-composite",
            "same-tier shuffled evidence",
            shuffled,
        ),
        ("self-transcript-resend-composite", "exact matched request replay", resend),
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
        workers=3,
        finalize=True,
    )


def _query_group(item: Mapping[str, object]) -> str:
    relpath = item.get("media_relpath")
    if not isinstance(relpath, str):
        raise RuntimeError("receipt item lacks media_relpath for group isolation")
    match = _QUERY_GROUP.search(relpath)
    if match is None:
        raise RuntimeError(f"cannot derive query group from {relpath!r}")
    return f"{item['tier']}:query-{match.group(1)}"


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
    matched: Mapping[str, object],
    shuffled: Mapping[str, object],
    resend: Mapping[str, object],
    matched_attempt_id: str,
) -> dict[str, object]:
    expected = load_expected_calls(context["lock"], root, repo_root=REPO)  # type: ignore[arg-type]
    items_by_id = {
        str(item["sample_id"]): item for item in context["items"]  # type: ignore[union-attr]
    }
    outcomes: list[cascade.SelfTranscriptOutcome] = []
    for sample_id in sorted(context["sample_ids"]):  # type: ignore[arg-type]
        route = observation["routes"][sample_id]  # type: ignore[index]
        transcript = observation["transcripts"][sample_id]  # type: ignore[index]
        gold = expected[sample_id]
        outcomes.append(
            cascade.SelfTranscriptOutcome(
                sample_id=sample_id,
                group_id=_query_group(items_by_id[sample_id]),
                state=cascade.extract_runtime_state(
                    transcript=transcript,
                    route=route,
                    m0_response=context["m0"][sample_id],  # type: ignore[index]
                ),
                route_available=route.available,
                top5_gold_tool_correct=(
                    route.available
                    and {call.name for call in gold}.issubset(set(route.task_targets))
                ),
                stop_score=_score_text(gold, context["m0"][sample_id]),  # type: ignore[index]
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
    report = cascade.evaluate_policy(
        outcomes,
        liveness_passed=True,
        resend_absolute_exact_count_difference=resend_floor,
    )
    actions = {
        decision.outcome.sample_id: decision.action for decision in report.decisions
    }
    policy_texts = build_policy_composite_texts(
        m0_texts=context["m0"],  # type: ignore[arg-type]
        matched_texts=matched["texts"],  # type: ignore[arg-type]
        actions=actions,
    )
    run_dir = mission_dir / "policy-composite"
    sink = TraceSink(run_dir, RUN_ID)
    matched_path = Path(matched["outputs"])  # type: ignore[arg-type]
    m0_path = Path(context["m0_path"])  # type: ignore[arg-type]
    matched_sha256 = _sha256_file(matched_path)
    source_by_id = {
        sample_id: (
            {
                "action": "USE_MATCHED",
                "source_artifact_path": str(matched_path),
                "source_artifact_sha256": matched_sha256,
            }
            if actions[sample_id] == cascade.USE_MATCHED
            else {
                "action": "STOP_M0",
                "source_artifact_path": str(m0_path),
                "source_artifact_sha256": M0_SHA256,
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
    trace_manifest_hash = sink.close()
    outputs_path = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs_path, rows)
    plan = _execution_plan(matched_attempt_id)
    manifest_path = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs_path,
        trace_manifest_hash=trace_manifest_hash,
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
            "derivation": "model-free cross-fitted composition from sealed M0 and matched outputs",
        },
        expected_attempt_state="FINALIZED",
    )
    wave2 = _run_score_batch(
        mission_dir=mission_dir,
        name="wave2-policy-score",
        jobs=(
            {
                "job_id": "self-transcript-crossfit-policy-composite",
                "manifest": str(manifest_path),
            },
        ),
        workers=1,
        finalize=False,
    )
    result = {
        "schema": "saea-a2t-self-transcript-cascade-policy-result-v1",
        "run_id": RUN_ID,
        "promotion_passed": report.promotion_passed,
        "liveness": asdict(observation["report"]),
        "metrics": asdict(report.metrics),
        "gates": dict(report.gates),
        "state_class_counts": dict(report.state_class_counts),
        "resend_absolute_exact_count_difference": resend_floor,
        "actions": actions,
        "policy_manifest": str(manifest_path),
        "policy_manifest_sha256": _sha256_file(manifest_path),
        "policy_outputs": str(outputs_path),
        "policy_outputs_sha256": _sha256_file(outputs_path),
        "wave2_official_score": wave2,
        "decision": (
            "preregister a separate block-disjoint approximately-104 support flight"
            if report.promotion_passed
            else "close this mechanism on A2T-G1-104; no fresh-sample contact"
        ),
    }
    _write_json(mission_dir / "policy-result.json", result)
    return result


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = root / "runs" / RUN_ID / f"flight-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    attempt_ids = {
        "observation": f"attempt-{stamp.lower()}-selftxobs",
        "matched": f"attempt-{stamp.lower()}-selftxmatch",
        "shuffled": f"attempt-{stamp.lower()}-selftxshuffle",
        "resend": f"attempt-{stamp.lower()}-selftxresend",
    }
    session = None
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
        _execution_plan(attempt_ids["observation"]), full_hash=True
    )
    parsed_url = urlparse(str(values["base_url"]))
    if parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.port is None:
        raise RuntimeError("decoder base_url must be an explicit loopback port")
    session_dir = mission_dir / "service"
    session_dir.mkdir()
    session_receipt_path = session_dir / "session-receipt.json"
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
            receipt_path=session_receipt_path,
            ready_timeout_seconds=600.0,
            server_log_path=session_dir / "server.log",
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
        observation = _run_observation(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["observation"],
            run_dir=mission_dir / "observation",
            session_receipt_path=session_receipt_path,
            lock_sha256=lock_sha256,
        )
        if observation["passed"] is not True:
            stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
                force_after_timeout=True,
                receipt_path=session_dir / "stop-receipt.json",
            )
            session = None
            result = {
                "schema": "saea-a2t-self-transcript-cascade-flight-receipt-v1",
                "run_id": RUN_ID,
                "status": "STOPPED_AT_LABEL_FREE_LIVENESS_GATE",
                "study_commit": context["commit"],
                "mission_dir": str(mission_dir),
                "elapsed_seconds": time.perf_counter() - started,
                "liveness": asdict(observation["report"]),
                "model_use_contacts": 0,
                "official_scorer_contacts": 0,
            }
            _write_json(mission_dir / "flight-receipt.json", result)
            return result

        matched = _run_use(
            phase=MATCHED_USE_PHASE,
            variant="matched",
            root=root,
            context=context,
            observation=observation,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["matched"],
            run_dir=mission_dir / "matched-composite",
            session_receipt_path=session_receipt_path,
            lock_sha256=lock_sha256,
        )
        shuffled = _run_use(
            phase=SHUFFLED_USE_PHASE,
            variant="shuffled-evidence",
            root=root,
            context=context,
            observation=observation,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["shuffled"],
            run_dir=mission_dir / "shuffled-evidence-composite",
            session_receipt_path=session_receipt_path,
            lock_sha256=lock_sha256,
        )
        resend = _run_resend(
            root=root,
            context=context,
            observation=observation,
            gate=gate,
            transport=transport,
            attempt_id=attempt_ids["resend"],
            run_dir=mission_dir / "resend-composite",
            session_receipt_path=session_receipt_path,
            matched=matched,
        )
        stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            force_after_timeout=True,
            receipt_path=session_dir / "stop-receipt.json",
        )
        session = None
        wave1 = _parallel_finalize(
            mission_dir=mission_dir,
            lock_sha256=lock_sha256,
            matched=matched,
            shuffled=shuffled,
            resend=resend,
        )
        for result in (matched, shuffled, resend):
            if verify_bundle(result["manifest"]).attempt_state != "FINALIZED":  # type: ignore[arg-type]
                raise RuntimeError("official finalizer left a USE attempt unsettled")
        policy = _postseal_policy_read(
            root=root,
            context=context,
            mission_dir=mission_dir,
            session_receipt_path=session_receipt_path,
            observation=observation,
            matched=matched,
            shuffled=shuffled,
            resend=resend,
            matched_attempt_id=attempt_ids["matched"],
        )
        receipt = {
            "schema": "saea-a2t-self-transcript-cascade-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SCORED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "umbrella_lock_sha256": lock_sha256,
            "session_receipt": str(session_receipt_path),
            "attempts": {
                "observation": {
                    "attempt_id": attempt_ids["observation"],
                    "state": "ABORTED_OBSERVATION_ONLY_SUCCESS",
                    "manifest": str(observation["manifest"]),
                },
                "matched": {
                    "attempt_id": attempt_ids["matched"],
                    "state": "FINALIZED",
                    "manifest": str(matched["manifest"]),
                },
                "shuffled": {
                    "attempt_id": attempt_ids["shuffled"],
                    "state": "FINALIZED",
                    "manifest": str(shuffled["manifest"]),
                },
                "resend": {
                    "attempt_id": attempt_ids["resend"],
                    "state": "FINALIZED",
                    "manifest": str(resend["manifest"]),
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
                "schema": "saea-a2t-self-transcript-cascade-flight-failure-v1",
                "run_id": RUN_ID,
                "attempt_ids": attempt_ids,
                "error": repr(error),
            },
        )
        raise
    finally:
        if session is not None:
            stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
                force_after_timeout=True,
                receipt_path=session_dir / "stop-receipt.json",
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
                    "official_score_workers": 3,
                    "scoring_boundary": "one-complete-manifest-per-process",
                    "dataset_sharding": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(_launch(root), indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
