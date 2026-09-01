"""Launch the preregistered 104-item factor-top-1 Audio2Tool probe.

The main openJiuwen attempt performs one factor and one diagnostic final
contact per sample. A second gated attempt replays sixteen traced phase-3
payloads byte-for-byte. Each attempt then materializes a complete 104-row
composite. The unchanged official scorer finalizes those two indivisible
manifests concurrently; samples are never sharded and shard metrics are never
averaged.

The flight path never opens gold. Gold becomes readable only inside the two
official finalizer processes after both prediction manifests verify.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
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

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    TRANSPORTS,
    Registry,
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
from speech_aware_evidence_acquisition.core.model import (  # noqa: E402
    FrozenCoreAdapter,
)
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
from speech_aware_evidence_acquisition.rails.probes.a2t_factor_top1_bundle import (  # noqa: E402
    build_main_composite_texts,
    build_resend_composite_texts,
    emit_composite_rows,
    extract_exact_final_payloads,
    select_resend_ids,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_factor_top1_flight import (  # noqa: E402
    CONTROLLER_POLICY_ID,
    FactorTop1Controller,
    build_registry_snapshot,
    factor_response_format,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_self_consistency_flight import (  # noqa: E402
    A2TSelfConsistencyAdapter,
    OBSERVATION_PHASE,
    SPLIT_ID,
    load_frozen_m0_outputs,
)
from speech_aware_evidence_acquisition.rails.runner import (  # noqa: E402
    run_speech_native_agent_loop,
)

RUN_ID = "SAEA-A2T-TFRL-FACTOR-TOP1-104-V1"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-factor-top1-agentloop"
EXPERIMENT_FRAGMENT = "a2t-training-free-factor-top1-104-v1"
COMPOSED_CONFIG_SHA256 = (
    "1ce5782f20f5b9977f02fa5db5f547211b83b4bb15a81ba21d48136c4dfffd63"
)
PROTOCOL_SHA256 = (
    "e6e99f122e14bc3b3969fc0221373c2c51f0a35b5771ec252c9bc4e11f266c54"
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
REGISTRY_SHA256 = (
    "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"
)
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-G1-104-promotion.json"
PROMOTION_SHA256 = (
    "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
)
RUNTIME_RECEIPT_RELPATH = Path("receipts/runtime-q4km-mmproj-free.json")
PLAN_TEMPLATE = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-factor-top1-104-v1/execution-plan-template.json"
)
SCORE_PLAN = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-factor-top1-104-v1/parallel-score-plan.json"
)
RECOVERY_PLAN = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-01-a2t-factor-top1-104-v1/recovery-plan.json"
)
OPENJIUWEN_VERSION = "0.1.16.post2"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_json(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError(f"JSON document must be an object: {path}")
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(
    path: Path,
    rows: Sequence[Mapping[str, object]],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
    )
    path.write_text(text, encoding="utf-8", newline="\n")


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


def _validate_prompt_fit(
    values: Mapping[str, object],
    *,
    task_contract: str,
) -> None:
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
        or int(receipt.get("visible_key_facets", -1)) < 1
        or int(receipt.get("visible_values", -1)) < 1
        or int(receipt.get("context_margin_tokens", -1)) <= 0
    ):
        raise RuntimeError("landed prompt-fit envelope no longer dominates this flight")


def _validate_recovery(root: Path) -> dict[str, object]:
    recovery = _read_json(RECOVERY_PLAN)
    source = recovery.get("source_attempt")
    completed = recovery.get("completed_trajectory")
    failed = recovery.get("failed_requests_without_model_response")
    if (
        recovery.get("registered_before_recovery_contact") is not True
        or not isinstance(source, Mapping)
        or not isinstance(completed, Mapping)
        or not isinstance(failed, list)
    ):
        raise RuntimeError("recovery plan structure drift")
    attempt_id = source.get("attempt_id")
    if not isinstance(attempt_id, str):
        raise RuntimeError("recovery source attempt id is malformed")
    attempt = _read_json(root / "attempts" / RUN_ID / f"{attempt_id}.json")
    actual = attempt.get("actual")
    if (
        attempt.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != source.get("actual_calls")
        or abs(
            float(actual.get("audio_seconds", -1))
            - float(source.get("actual_audio_seconds", -2))
        )
        > 1e-9
    ):
        raise RuntimeError("recovery source attempt accounting drift")
    trace_path = Path(str(source.get("trace_path")))
    if _sha256_file(trace_path) != source.get("trace_sha256"):
        raise RuntimeError("recovery source trace byte identity drift")
    requests: dict[str, Mapping[str, object]] = {}
    response_ids: set[str] = set()
    for line in trace_path.read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        document = json.loads(line)
        channel = document.get("channel")
        record_id = document.get("record_id")
        if not isinstance(record_id, str):
            raise RuntimeError("recovery trace record id is malformed")
        if channel == "MODEL_REQUEST":
            outer = document.get("payload")
            payload = outer.get("payload") if isinstance(outer, Mapping) else None
            if not isinstance(payload, Mapping):
                raise RuntimeError("recovery MODEL_REQUEST lacks payload")
            requests[record_id.removesuffix("/request")] = payload
        elif channel == "MODEL_RESPONSE":
            response_ids.add(record_id.removesuffix("/response"))
    if len(requests) != source.get("model_requests") or len(
        response_ids
    ) != source.get("model_responses"):
        raise RuntimeError("recovery trace request/response counts drift")
    factor_request_id = str(completed.get("factor_request_id"))
    final_request_id = str(completed.get("final_request_id"))
    sample_id = completed.get("sample_id")
    if (
        response_ids != {factor_request_id, final_request_id}
        or requests[factor_request_id].get("sample_id") != sample_id
        or requests[final_request_id].get("sample_id") != sample_id
        or len(requests[final_request_id].get("supplied_evidence", [])) != 0
        or completed.get("recovery_action") != "STOP_M0"
        or completed.get("recontact") is not False
    ):
        raise RuntimeError("completed recovery trajectory structure drift")
    expected_failed = {
        (row.get("request_id"), row.get("sample_id"))
        for row in failed
        if isinstance(row, Mapping)
    }
    actual_failed = {
        (request_id, payload.get("sample_id"))
        for request_id, payload in requests.items()
        if request_id not in response_ids
    }
    if actual_failed != expected_failed or len(actual_failed) != 3:
        raise RuntimeError("failed recovery request identities drift")
    return {
        "source_attempt_id": attempt_id,
        "source_trace": str(trace_path),
        "source_trace_sha256": source["trace_sha256"],
        "completed_sample_id": sample_id,
        "failed_request_sample_ids": tuple(
            sorted(str(sample) for _request, sample in actual_failed)
        ),
    }


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
    ):
        raise RuntimeError("execution-plan template identity drift")
    plan_probe = _execution_plan("attempt-20260901t000000z-factorpre")
    if plan_probe.protocol_hash != PROTOCOL_SHA256:
        raise RuntimeError("structured ExecutionPlan protocol drift")

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
    sample_ids = tuple(item["sample_id"] for item in items)
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
        row["packet_id"]: row
        for row in promotion.get("packets", [])  # type: ignore[union-attr]
    }
    packet_bindings: dict[str, dict[str, str]] = {}
    for item in items:
        packet = load_speech_feature_packet(FEATURE_ROOT, item["packet_id"])
        recorded = promoted.get(item["packet_id"])
        if (
            recorded is None
            or packet.audio_sha256 != item["audio_sha256"]
            or packet.packet_sha256 != recorded.get("packet_sha256")
        ):
            raise RuntimeError(f"speech packet drift for {item['sample_id']}")
        packet_bindings[item["sample_id"]] = {
            "packet_id": packet.packet_id,
            "sha256": packet.packet_sha256,
        }

    recovery = _validate_recovery(root)
    recovered_sample_id = recovery["completed_sample_id"]
    runtime_items = tuple(
        item for item in items if item["sample_id"] != recovered_sample_id
    )
    runtime_packet_bindings = {
        sample_id: descriptor
        for sample_id, descriptor in packet_bindings.items()
        if sample_id != recovered_sample_id
    }
    if len(runtime_items) != 103 or len(runtime_packet_bindings) != 103:
        raise RuntimeError("recovery runtime population is not exactly 103 samples")

    lock = load_lock(umbrella_lock_path(REPO))
    carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    registry_path = carrier_root / "tools_registry.csv"
    if _sha256_file(registry_path) != REGISTRY_SHA256:
        raise RuntimeError("tool registry byte identity drift")
    registry = load_tool_registry(lock, root)
    if len(registry) != 152:
        raise RuntimeError("tool registry row-count drift")
    snapshot = build_registry_snapshot(registry, registry_sha256=REGISTRY_SHA256)
    reversed_snapshot = build_registry_snapshot(
        tuple(reversed(registry)), registry_sha256=REGISTRY_SHA256
    )
    if snapshot.content_hash() != reversed_snapshot.content_hash():
        raise RuntimeError("registry snapshot depends on source row order")
    if any("argument_defaults" in value.content for value in snapshot.values):
        raise RuntimeError("registry snapshot leaked argument defaults")

    response_schema = json.dumps(
        factor_response_format(), ensure_ascii=True, sort_keys=True
    )
    if "tool_name" in response_schema or "tool_calls" in response_schema:
        raise RuntimeError("factor response schema exposes prohibited tool fields")
    task_contract = render_tool_schemas(lock, root)
    _validate_prompt_fit(composed.values, task_contract=task_contract)

    score_plan = _read_json(SCORE_PLAN)
    jobs = score_plan.get("jobs")
    if (
        score_plan.get("mode") != "--finalize"
        or score_plan.get("workers") != 2
        or not isinstance(jobs, list)
        or len(jobs) != 2
        or any("complete 104-row" not in str(job.get("input")) for job in jobs)
    ):
        raise RuntimeError("parallel complete-manifest score plan drift")
    return {
        "commit": commit,
        "composed": composed,
        "lock": lock,
        "carrier_root": carrier_root,
        "receipt": receipt,
        "items": items,
        "runtime_items": runtime_items,
        "sample_ids": sample_ids,
        "m0": m0,
        "registry": registry,
        "snapshot": snapshot,
        "packet_bindings": packet_bindings,
        "runtime_packet_bindings": runtime_packet_bindings,
        "recovery": recovery,
    }


def _controller_registry(
    registry_rows: Sequence[Mapping[str, str]],
    snapshot: object,
) -> Registry:
    controllers = Registry("factor-top-1 Agent controller")
    controllers.register(
        CONTROLLER_POLICY_ID,
        lambda _sample_id: FactorTop1Controller(registry_rows, snapshot),
    )
    return controllers


def _source_request_ids(
    payloads: Mapping[str, Mapping[str, object]],
) -> dict[str, str]:
    request_ids: dict[str, str] = {}
    for sample_id, payload in payloads.items():
        request_id = payload.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise RuntimeError(f"final payload for {sample_id!r} lacks request id")
        request_ids[sample_id] = request_id
    return request_ids


def _assert_final_response_trace(
    trace_documents: Sequence[Mapping[str, object]],
    *,
    request_ids: Mapping[str, str],
    response_texts: Mapping[str, str],
) -> None:
    responses: dict[str, Mapping[str, object]] = {}
    for document in trace_documents:
        if document.get("channel") != "MODEL_RESPONSE":
            continue
        record_id = document.get("record_id")
        payload = document.get("payload")
        if isinstance(record_id, str) and isinstance(payload, Mapping):
            responses[record_id] = payload
    for sample_id, request_id in request_ids.items():
        payload = responses.get(f"{request_id}/response")
        text = response_texts.get(sample_id)
        if payload is None or payload.get("text") != text:
            raise RuntimeError(
                f"final response trace differs from AgentLoop result for {sample_id!r}"
            )


def _human_ledger_cells(
    *,
    phase: str,
    umbrella_lock_sha256: str,
) -> dict[str, str]:
    return {
        "experiment_id": RUN_ID,
        "speech task/carrier": "Audio2Tool A2T-G1-104 discovery",
        "changed axes": phase,
        "shared code revision": f"openJiuwen {OPENJIUWEN_VERSION}",
        "model rev": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
        "dataset rev": umbrella_lock_sha256,
        "MLflow run": "not uploaded",
        "effectiveness": "unread before finalization",
        "reasonableness": "complete verified 104-row composite scorer job",
        "efficiency": "two-worker outer parallelism across complete manifests",
        "deviations": "none",
        "decision": "pending preregistered scorer-side read",
    }


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
    if verified.attempt_state != "OPENED" or len(verified.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("completed composite bundle failed OPENED/104 verification")
    return manifest_path


def _run_main(
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
    adapter = A2TSelfConsistencyAdapter(
        context["lock"],  # type: ignore[arg-type]
        root,
        repo_root=REPO,
        receipt_items=context["runtime_items"],  # type: ignore[arg-type]
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
        request_id_prefix="factortop1",
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=context["runtime_packet_bindings"],  # type: ignore[arg-type]
    )
    decoding = dict(context["composed"].values["decoding_params"])  # type: ignore[union-attr]
    decoding.pop("id_slot", None)
    summary = run_speech_native_agent_loop(
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        split_id=SPLIT_ID,
        knowledge_snapshot=context["snapshot"],  # type: ignore[arg-type]
        speech_packet_bindings=context["runtime_packet_bindings"],  # type: ignore[arg-type]
        controller_policy_id=CONTROLLER_POLICY_ID,
        max_contacts=2,
        slot_count=int(context["composed"].values["profile_slot_count"]),  # type: ignore[union-attr]
        queue_depth=(
            int(context["composed"].values["profile_slot_count"])  # type: ignore[union-attr]
            * int(context["composed"].values["profile_queue_depth_multiplier"])  # type: ignore[union-attr]
        ),
        trace_sink=trace_sink,
        agent_executor_id="openjiuwen-workflow-v1",
        decoding_params=decoding,
        controller_registry=_controller_registry(
            context["registry"], context["snapshot"]  # type: ignore[arg-type]
        ),
    )
    selected_ids = select_resend_ids(summary, per_tier=2)
    if len(selected_ids) != 16:
        raise RuntimeError("resend selection did not produce exactly sixteen samples")
    trace_documents = _trace_documents(run_dir)
    all_available = tuple(
        result.sample_id
        for result in summary.results
        if len(result.final_query_state.retrieved_value_ids) == 1
    )
    final_payloads = extract_exact_final_payloads(trace_documents, all_available)
    request_ids = _source_request_ids(final_payloads)
    _assert_final_response_trace(
        trace_documents,
        request_ids=request_ids,
        response_texts={
            result.sample_id: result.final_response_text for result in summary.results
        },
    )
    runtime_ids = {result.sample_id for result in summary.results}
    runtime_m0 = {
        sample_id: response
        for sample_id, response in context["m0"].items()  # type: ignore[union-attr]
        if sample_id in runtime_ids
    }
    main_texts = build_main_composite_texts(summary, runtime_m0)
    recovered_sample_id = str(context["recovery"]["completed_sample_id"])  # type: ignore[index]
    main_texts[recovered_sample_id] = context["m0"][recovered_sample_id]  # type: ignore[index]
    main_texts = {
        sample_id: main_texts[sample_id] for sample_id in sorted(main_texts)
    }
    source_by_id = {
        sample_id: (
            {
                "action": "USE_FACTOR_TOP1",
                "source_request_id": request_ids[sample_id],
            }
            if sample_id in request_ids
            else (
                {
                    "action": "RECOVERED_CANARY_STOP_M0",
                    "source_request_id": "recovered-zero-value-final",
                    "source_artifact_sha256": str(
                        context["recovery"]["source_trace_sha256"]  # type: ignore[index]
                    ),
                }
                if sample_id == recovered_sample_id
                else {
                "action": "STOP_M0",
                "source_request_id": "frozen-m0",
                "source_artifact_sha256": M0_SHA256,
                }
            )
        )
        for sample_id in main_texts
    }
    rows = emit_composite_rows(
        texts=main_texts,
        source_by_id=source_by_id,
        sink=trace_sink,
        variant="main",
    )
    trace_manifest_hash = trace_sink.close()
    client_summary = client.close()
    expected_main_contacts = len(context["runtime_items"]) * 2  # type: ignore[arg-type]
    if client_summary.get("request_count") != expected_main_contacts:
        raise RuntimeError("recovery main attempt contact accounting drift")
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
        cost=client_summary["cost"],  # type: ignore[arg-type]
    )
    _write_json(
        run_dir / "main-receipt.json",
        {
            "attempt_id": attempt_id,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "outputs_sha256": _sha256_file(outputs_path),
            "trace_manifest_sha256": trace_manifest_hash,
            "selected_resend_ids": list(selected_ids),
            "available_count": len(final_payloads),
            "recovery": context["recovery"],
            "client": client_summary,
        },
    )
    return {
        "summary": summary,
        "binding": binding,
        "selected_ids": selected_ids,
        "selected_payloads": {
            sample_id: final_payloads[sample_id] for sample_id in selected_ids
        },
        "main_texts": main_texts,
        "manifest": manifest_path,
        "outputs": outputs_path,
        "attempt_id": attempt_id,
    }


def _run_resend(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
    main: Mapping[str, object],
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    trace_sink = TraceSink(run_dir, RUN_ID)
    adapter = FrozenCoreAdapter(
        gate=gate,
        plan=plan,
        arm="speech-feature-query",
        transport=transport,  # type: ignore[arg-type]
        sink=trace_sink,
        binding=main["binding"],  # type: ignore[arg-type]
    )
    payloads = main["selected_payloads"]
    if not isinstance(payloads, Mapping) or len(payloads) != 16:
        raise RuntimeError("resend attempt lacks sixteen exact payloads")
    resend_responses: dict[str, str] = {}
    response_receipts: dict[str, dict[str, object]] = {}
    for sample_id in sorted(payloads):
        payload = payloads[sample_id]
        response = adapter.request(payload)
        resend_responses[sample_id] = response.text
        response_receipts[sample_id] = {
            "request_id": payload["request_id"],
            "request_sha256": response.request_sha256,
            "response_sha256": response.response_sha256,
            "response_text_sha256": response.response_text_sha256,
            "latency_seconds": response.latency_seconds,
        }
    selected_ids = main["selected_ids"]
    resend_texts = build_resend_composite_texts(
        main["main_texts"],  # type: ignore[arg-type]
        selected_ids=selected_ids,  # type: ignore[arg-type]
        resend_responses=resend_responses,
    )
    main_outputs_sha256 = _sha256_file(main["outputs"])  # type: ignore[arg-type]
    source_by_id = {
        sample_id: (
            {
                "action": "RESEND_FACTOR_TOP1",
                "source_request_id": str(payloads[sample_id]["request_id"]),
            }
            if sample_id in resend_responses
            else {
                "action": "REUSE_MAIN_COMPOSITE",
                "source_request_id": "main-composite",
                "source_artifact_sha256": main_outputs_sha256,
            }
        )
        for sample_id in resend_texts
    }
    rows = emit_composite_rows(
        texts=resend_texts,
        source_by_id=source_by_id,
        sink=trace_sink,
        variant="resend",
    )
    trace_manifest_hash = trace_sink.close()
    cost = adapter.cost_summary()
    if cost.get("calls_used") != 16:
        raise RuntimeError("resend attempt did not account for exactly sixteen contacts")
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
    )
    _write_json(
        run_dir / "resend-receipt.json",
        {
            "attempt_id": attempt_id,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "outputs_sha256": _sha256_file(outputs_path),
            "trace_manifest_sha256": trace_manifest_hash,
            "main_outputs_sha256": main_outputs_sha256,
            "selected_resend_ids": list(selected_ids),  # type: ignore[arg-type]
            "responses": response_receipts,
            "cost": cost,
        },
    )
    return {
        "responses": resend_responses,
        "manifest": manifest_path,
        "outputs": outputs_path,
        "attempt_id": attempt_id,
    }


def _parallel_finalize(
    *,
    mission_dir: Path,
    lock_sha256: str,
    main: Mapping[str, object],
    resend: Mapping[str, object],
) -> dict[str, object]:
    jobs_path = mission_dir / "score-jobs.jsonl"
    jobs: list[dict[str, str]] = []
    for job_id, phase, result in (
        ("factor-top1-main-composite", "factor plus top-1 main composite", main),
        ("factor-top1-resend-composite", "exact-payload resend composite", resend),
    ):
        cells_path = mission_dir / f"{job_id}-ledger-cells.json"
        _write_json(
            cells_path,
            _human_ledger_cells(phase=phase, umbrella_lock_sha256=lock_sha256),
        )
        jobs.append(
            {
                "job_id": job_id,
                "manifest": str(result["manifest"]),
                "ledger_cells": str(cells_path),
            }
        )
    _write_jsonl(jobs_path, jobs)
    score_dir = mission_dir / "parallel-finalize"
    completed = subprocess.run(
        [
            "bash",
            str(REPO / "scripts/evaluate_parallel.sh"),
            "--finalize",
            "--jobs",
            str(jobs_path),
            "--output-dir",
            str(score_dir),
            "--workers",
            "2",
        ],
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
    (mission_dir / "parallel-finalize.stdout.log").write_text(
        completed.stdout, encoding="utf-8", newline="\n"
    )
    (mission_dir / "parallel-finalize.stderr.log").write_text(
        completed.stderr, encoding="utf-8", newline="\n"
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"outer-parallel official finalization exited {completed.returncode}"
        )
    summary = _read_json(score_dir / "batch-summary.json")
    if summary.get("failed") != 0 or summary.get("succeeded") != 2:
        raise RuntimeError("outer-parallel finalization did not settle both jobs")
    return summary


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = root / "runs" / RUN_ID / f"flight-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    main_attempt = f"attempt-{stamp.lower()}-factormain"
    resend_attempt = f"attempt-{stamp.lower()}-factorresend"
    attempts = (main_attempt, resend_attempt)
    session = None
    runtime_receipt = load_runtime_receipt(REPO / "docs" / RUNTIME_RECEIPT_RELPATH)
    values = context["composed"].values
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
        _execution_plan(main_attempt), full_hash=True
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
        main = _run_main(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            attempt_id=main_attempt,
            run_dir=mission_dir / "main-composite",
            session_receipt_path=session_receipt_path,
        )
        resend = _run_resend(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            attempt_id=resend_attempt,
            run_dir=mission_dir / "resend-composite",
            session_receipt_path=session_receipt_path,
            main=main,
        )
        stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            force_after_timeout=True,
            receipt_path=session_dir / "stop-receipt.json",
        )
        session = None

        score_summary = _parallel_finalize(
            mission_dir=mission_dir,
            lock_sha256=lock_sha256,
            main=main,
            resend=resend,
        )
        main_state = verify_bundle(main["manifest"]).attempt_state
        resend_state = verify_bundle(resend["manifest"]).attempt_state
        if main_state != "FINALIZED" or resend_state != "FINALIZED":
            raise RuntimeError("official finalizer did not settle both attempts")
        receipt = {
            "schema": "saea-a2t-factor-top1-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "FINALIZED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "umbrella_lock_sha256": lock_sha256,
            "session_receipt": str(session_receipt_path),
            "attempts": {
                "main": {
                    "attempt_id": main_attempt,
                    "state": main_state,
                    "manifest": str(main["manifest"]),
                    "manifest_sha256": _sha256_file(main["manifest"]),
                    "outputs_sha256": _sha256_file(main["outputs"]),
                },
                "resend": {
                    "attempt_id": resend_attempt,
                    "state": resend_state,
                    "manifest": str(resend["manifest"]),
                    "manifest_sha256": _sha256_file(resend["manifest"]),
                    "outputs_sha256": _sha256_file(resend["outputs"]),
                },
            },
            "selected_resend_ids": list(main["selected_ids"]),
            "recovery": context["recovery"],
            "parallel_finalizer": score_summary,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        for attempt_id in attempts:
            abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _write_json(
            mission_dir / "failure-receipt.json",
            {
                "schema": "saea-a2t-factor-top1-flight-failure-v1",
                "run_id": RUN_ID,
                "attempt_ids": list(attempts),
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
                    "planned_main_contacts": 206,
                    "planned_resend_contacts": 16,
                    "consumed_canary_contacts": 5,
                    "official_score_workers": 2,
                    "scoring_boundary": "one-complete-manifest-per-process",
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
