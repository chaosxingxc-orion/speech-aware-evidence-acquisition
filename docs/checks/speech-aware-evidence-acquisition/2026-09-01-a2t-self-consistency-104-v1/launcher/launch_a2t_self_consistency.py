"""Launch the preregistered 104-item Audio2Tool self-consistency probe.

The normal path owns one decoder session and two independent one-shot
attempts.  A registered recovery path reuses one exact complete observation
bundle after a downstream zero-contact refusal and opens only a fresh supply
attempt.  Both paths start official scoring only after both complete 104-row
prediction manifests exist.  Samples are never sharded and shard metrics are
never averaged.

The flight path never opens gold.  Gold becomes readable only inside the two
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
    A2TSelfConsistencyAdapter,
    OBSERVATION_PHASE,
    SPLIT_ID,
    SUPPLY_PHASE,
    build_phase_bundle_material,
    build_supply_material,
    load_frozen_m0_outputs,
    run_phase,
)
from speech_aware_evidence_acquisition.analysis.training_free_a2t_self_consistency import (  # noqa: E402
    render_union_stripped_registry,
)

RUN_ID = "SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-self-consistency-agentloop"
EXPERIMENT_FRAGMENT = "a2t-training-free-self-consistency-104-v1"
COMPOSED_CONFIG_SHA256 = (
    "f819f460cadbe8911d81c476be3f41050cd93f896bb88fc4836a3033d9a4f66d"
)
PROTOCOL_SHA256 = (
    "c7fafb3e411473228d4191c29e0fb2d7cbbc1ec5965060e889b5fe332d87e54a"
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
SNAPSHOT_SHA256 = "ec2f9ec454d3f16957ac08e4d7686a6f3941f22c600ff2b1b2b97ff43baf9fb2"
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-G1-104-promotion.json"
PROMOTION_SHA256 = (
    "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
)
RUNTIME_RECEIPT_RELPATH = Path("receipts/runtime-q4km-mmproj-free.json")
PLAN_TEMPLATE = REPO / "docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-self-consistency-104-v1/execution-plan-template.json"
SCORE_PLAN = REPO / "docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-self-consistency-104-v1/parallel-score-plan.json"
OPENJIUWEN_VERSION = "0.1.16.post2"
RECOVERED_OBSERVATION_ATTEMPT_ID = "attempt-20260901t172514z-selfobs"
RECOVERED_OBSERVATION_MANIFEST_SHA256 = (
    "73c901639916a28d67c2bc8a996d921371744f438c73be178c7fbe995fc1a238"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Mapping[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise RuntimeError(f"JSON document must be an object: {path}")
    return document


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _trace_documents(run_dir: Path) -> tuple[Mapping[str, object], ...]:
    path = run_dir / f"{RUN_ID}.trace.jsonl"
    documents = tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line
    )
    if not all(isinstance(document, Mapping) for document in documents):
        raise RuntimeError(f"trace contains a non-object row: {path}")
    return documents


def _phase_responses(summary: object) -> dict[str, str]:
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != SPLIT_COUNT:
        raise RuntimeError("phase summary does not carry the complete registered cohort")
    responses = {
        result.sample_id: result.final_response_text
        for result in results
        if isinstance(result.sample_id, str) and isinstance(result.final_response_text, str)
    }
    if len(responses) != SPLIT_COUNT:
        raise RuntimeError("phase summary contains duplicate or malformed results")
    return responses


def _load_recovered_observation(root: Path, manifest_path: Path) -> dict[str, object]:
    manifest_path = manifest_path.resolve(strict=True)
    expected_root = (root / "runs" / RUN_ID).resolve(strict=True)
    if not manifest_path.is_relative_to(expected_root):
        raise RuntimeError("recovered observation manifest is outside this run root")
    if _sha256_file(manifest_path) != RECOVERED_OBSERVATION_MANIFEST_SHA256:
        raise RuntimeError("recovered observation manifest is not the registered source")
    bundle = verify_bundle(manifest_path)
    manifest = bundle.manifest
    if (
        bundle.attempt_state != "ABORTED"
        or manifest.get("status") != STATUS_COMPLETED
        or manifest.get("run_id") != RUN_ID
        or manifest.get("arm") != "speech-feature-query"
        or len(bundle.outputs_rows) != SPLIT_COUNT
        or bundle.outputs_path is None
    ):
        raise RuntimeError("recovered observation is not a complete aborted source bundle")
    split = manifest.get("split")
    if not isinstance(split, Mapping) or split.get("identity_hash") != SPLIT_IDENTITY_SHA256:
        raise RuntimeError("recovered observation split identity drift")
    if any(row.get("phase") != OBSERVATION_PHASE for row in bundle.outputs_rows):
        raise RuntimeError("recovered observation outputs contain another phase")
    responses = {str(row["sample_id"]): str(row["text"]) for row in bundle.outputs_rows}
    if len(responses) != SPLIT_COUNT:
        raise RuntimeError("recovered observation responses are incomplete")
    attempt = manifest.get("attempt")
    if (
        not isinstance(attempt, Mapping)
        or attempt.get("attempt_id") != RECOVERED_OBSERVATION_ATTEMPT_ID
    ):
        raise RuntimeError("recovered observation manifest lacks attempt metadata")
    state = _read_json(Path(str(attempt["state_path"])))
    actual = state.get("actual")
    if (
        not isinstance(actual, Mapping)
        or actual.get("calls") != SPLIT_COUNT
        or abs(float(actual.get("audio_seconds", -1)) - SPLIT_AUDIO_SECONDS) > 1e-6
    ):
        raise RuntimeError("recovered observation durable accounting is incomplete")
    return {
        "summary": None,
        "responses": responses,
        "manifest": manifest_path,
        "outputs": bundle.outputs_path,
        "attempt_id": str(attempt["attempt_id"]),
        "source_attempt_state": "ABORTED",
        "source_manifest_sha256": _sha256_file(manifest_path),
    }


def _execution_plan(attempt_id: str) -> ExecutionPlan:
    template = _read_json(PLAN_TEMPLATE)
    fields = dict(template["execution_plan"])  # type: ignore[arg-type]
    fields["attempt_id"] = attempt_id
    return ExecutionPlan(**fields).validate()


def _human_ledger_cells(
    *, phase: str, umbrella_lock_sha256: str, recovery: bool
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
        "reasonableness": "complete verified 104-row whole-manifest scorer job",
        "efficiency": "two-worker outer parallelism across complete manifests",
        "deviations": (
            "registered zero-contact recovery; observation not re-flown"
            if recovery
            else "none"
        ),
        "decision": "pending preregistered scorer-side read",
    }


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
    if protocol_hash(composed.config_hash, str(composed.values["arm"]), SPLIT_IDENTITY_SHA256) != PROTOCOL_SHA256:
        raise RuntimeError("audit protocol identity drift")
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("openJiuwen version drift")

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
        or abs(float(receipt.get("audio_seconds_total", -1)) - SPLIT_AUDIO_SECONDS) > 1e-9
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
        row["packet_id"]: row for row in promotion.get("packets", [])  # type: ignore[union-attr]
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

    lock = load_lock(umbrella_lock_path(REPO))
    registry = load_tool_registry(lock, root)
    first = sample_ids[0]
    rendered = render_union_stripped_registry(m0[first], m0[first], registry)
    reversed_rendered = render_union_stripped_registry(
        m0[first], m0[first], tuple(reversed(registry))
    )
    if rendered != reversed_rendered or "argument_defaults" in rendered.text:
        raise RuntimeError("values-stripped renderer failed its invariance gate")

    snapshot = KnowledgeSnapshot.from_frozen_json(_read_json(root / SNAPSHOT_RELPATH))
    if snapshot.content_hash() != SNAPSHOT_SHA256:
        raise RuntimeError("knowledge snapshot identity drift")
    overlap = set(sample_ids) & set(snapshot.source_sample_ids)
    if overlap or snapshot.source_split_identity_hash == SPLIT_IDENTITY_SHA256:
        raise RuntimeError("knowledge snapshot overlaps the flight population")

    score_plan = _read_json(SCORE_PLAN)
    if (
        score_plan.get("mode") != "--finalize"
        or score_plan.get("recovery_mode") != "--per-job-operation"
        or score_plan.get("workers") != 2
    ):
        raise RuntimeError("parallel score plan drift")
    return {
        "commit": commit,
        "composed": composed,
        "lock": lock,
        "receipt": receipt,
        "items": items,
        "sample_ids": sample_ids,
        "m0": m0,
        "registry": registry,
        "snapshot": snapshot,
        "packet_bindings": packet_bindings,
    }


def _run_one_phase(
    *,
    phase: str,
    attempt_id: str,
    phase_dir: Path,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    session_receipt_path: Path,
    lock_sha256: str,
    supply_material: Mapping[str, object] | None = None,
) -> dict[str, object]:
    plan = _execution_plan(attempt_id)
    _write_json(phase_dir / "execution-plan.json", asdict(plan))
    items = context["items"]
    lock = context["lock"]
    snapshot = context["snapshot"]
    packet_bindings = context["packet_bindings"]
    composed = context["composed"]
    adapter = A2TSelfConsistencyAdapter(
        lock,
        root,
        repo_root=REPO,
        receipt_items=items,
        phase=phase,
        supply_material=supply_material,
    )
    samples = adapter.load_split(SPLIT_ID)
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root),
    )
    trace_sink = TraceSink(phase_dir, RUN_ID)
    client = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=phase_dir / "transport-trace",
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix=("selfobs" if phase == OBSERVATION_PHASE else "selfsup"),
        speech_feature_root=FEATURE_ROOT,
        speech_packet_bindings=packet_bindings,
    )
    decoding = dict(composed.values["decoding_params"])
    decoding.pop("id_slot", None)
    summary = run_phase(
        phase=phase,
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        split_id=SPLIT_ID,
        knowledge_snapshot=snapshot,
        speech_packet_bindings=packet_bindings,
        trace_sink=trace_sink,
        slot_count=int(composed.values["profile_slot_count"]),
        queue_depth=int(composed.values["profile_slot_count"])
        * int(composed.values["profile_queue_depth_multiplier"]),
        decoding_params=decoding,
    )
    trace_manifest_hash = trace_sink.close()
    client_summary = client.close()
    trace_documents = _trace_documents(phase_dir)
    rows, cost = build_phase_bundle_material(
        summary,
        trace_documents,
        phase=phase,
        umbrella_lock_sha256=lock_sha256,
    )
    outputs_path = phase_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs_path, rows)
    result = RunResult(
        run_id=RUN_ID,
        arm="speech-feature-query",
        outputs_path=outputs_path,
        trace_manifest_hash=trace_manifest_hash,
        cost=cost,
    )
    verified_split = _verified_split(context["sample_ids"])
    manifest_path = build_manifest(
        repo_root=REPO,
        data_root=root,
        composed=composed,
        plan=plan,
        verified_split=verified_split,
        session_receipt_path=session_receipt_path,
        run_dir=phase_dir,
        status=STATUS_COMPLETED,
        result=result,
    )
    bundle = verify_bundle(manifest_path)
    if bundle.attempt_state != "OPENED" or len(bundle.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError(f"phase {phase} did not seal a complete OPENED bundle")
    _write_json(
        phase_dir / "phase-receipt.json",
        {
            "phase": phase,
            "attempt_id": attempt_id,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
            "outputs_sha256": _sha256_file(outputs_path),
            "trace_manifest_sha256": trace_manifest_hash,
            "client": client_summary,
            "cost": cost,
        },
    )
    return {
        "summary": summary,
        "responses": _phase_responses(summary),
        "manifest": manifest_path,
        "outputs": outputs_path,
        "attempt_id": attempt_id,
    }


def _launch(
    root: Path, *, resume_observation_manifest: Path | None = None
) -> Mapping[str, object]:
    context = _static_preflight(root)
    recovered_observation = (
        _load_recovered_observation(root, resume_observation_manifest)
        if resume_observation_manifest is not None
        else None
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = root / "runs" / RUN_ID / f"flight-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    supply_attempt = f"attempt-{stamp.lower()}-selfsup"
    if recovered_observation is None:
        observation_attempt = f"attempt-{stamp.lower()}-selfobs"
        attempts = (observation_attempt, supply_attempt)
        gate_plan = _execution_plan(observation_attempt)
    else:
        observation_attempt = str(recovered_observation["attempt_id"])
        attempts = (supply_attempt,)
        gate_plan = _execution_plan(supply_attempt)
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
    lock_sha256 = gate.assert_model_touch_allowed(gate_plan, full_hash=True)
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
        observation = recovered_observation
        if observation is None:
            observation = _run_one_phase(
                phase=OBSERVATION_PHASE,
                attempt_id=observation_attempt,
                phase_dir=mission_dir / "reobserve-direct",
                root=root,
                context=context,
                gate=gate,
                transport=transport,
                session_receipt_path=session_receipt_path,
                lock_sha256=lock_sha256,
            )
        supply_material = build_supply_material(
            context["m0"], observation["responses"], context["registry"]
        )
        supply = _run_one_phase(
            phase=SUPPLY_PHASE,
            attempt_id=supply_attempt,
            phase_dir=mission_dir / "supply-union-stripped",
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            session_receipt_path=session_receipt_path,
            lock_sha256=lock_sha256,
            supply_material=supply_material,
        )

        stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            force_after_timeout=True,
            receipt_path=session_dir / "stop-receipt.json",
        )
        session = None

        jobs_path = mission_dir / "score-jobs.jsonl"
        supply_ledger_cells = mission_dir / "supply-ledger-cells.json"
        _write_json(
            supply_ledger_cells,
            _human_ledger_cells(
                phase=SUPPLY_PHASE,
                umbrella_lock_sha256=lock_sha256,
                recovery=recovered_observation is not None,
            ),
        )
        if recovered_observation is None:
            observation_ledger_cells = mission_dir / "observation-ledger-cells.json"
            _write_json(
                observation_ledger_cells,
                _human_ledger_cells(
                    phase=OBSERVATION_PHASE,
                    umbrella_lock_sha256=lock_sha256,
                    recovery=False,
                ),
            )
            score_jobs = (
                {
                    "job_id": "reobserve-direct",
                    "manifest": str(observation["manifest"]),
                    "ledger_cells": str(observation_ledger_cells),
                },
                {
                    "job_id": "supply-union-stripped",
                    "manifest": str(supply["manifest"]),
                    "ledger_cells": str(supply_ledger_cells),
                },
            )
            score_mode = "--finalize"
        else:
            score_jobs = (
                {
                    "job_id": "reobserve-direct-recovered",
                    "manifest": str(observation["manifest"]),
                    "operation": "score",
                },
                {
                    "job_id": "supply-union-stripped",
                    "manifest": str(supply["manifest"]),
                    "operation": "finalize",
                    "ledger_cells": str(supply_ledger_cells),
                },
            )
            score_mode = "--per-job-operation"
        _write_jsonl(jobs_path, score_jobs)
        score_dir = mission_dir / "parallel-finalize"
        completed = subprocess.run(
            [
                "bash",
                str(REPO / "scripts/evaluate_parallel.sh"),
                score_mode,
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
        score_summary = _read_json(score_dir / "batch-summary.json")
        if score_summary.get("failed") != 0 or score_summary.get("succeeded") != 2:
            raise RuntimeError("outer-parallel official finalization did not settle both jobs")
        observation_state = verify_bundle(observation["manifest"]).attempt_state
        supply_state = verify_bundle(supply["manifest"]).attempt_state
        if recovered_observation is None:
            if observation_state != "FINALIZED" or supply_state != "FINALIZED":
                raise RuntimeError("official finalizer did not settle both attempts")
        elif observation_state != "ABORTED" or supply_state != "FINALIZED":
            raise RuntimeError("recovery scoring changed source state or failed to finalize supply")

        receipt = {
            "schema": "saea-a2t-self-consistency-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": (
                "FINALIZED"
                if recovered_observation is None
                else "RECOVERED_OBSERVATION_SCORED_AND_SUPPLY_FINALIZED"
            ),
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "umbrella_lock_sha256": lock_sha256,
            "session_receipt": str(session_receipt_path),
            "phases": {
                OBSERVATION_PHASE: {
                    "attempt_id": observation_attempt,
                    "attempt_state": observation_state,
                    "recovered_without_reflight": recovered_observation is not None,
                    "manifest": str(observation["manifest"]),
                    "manifest_sha256": _sha256_file(observation["manifest"]),
                    "outputs_sha256": _sha256_file(observation["outputs"]),
                },
                SUPPLY_PHASE: {
                    "attempt_id": supply_attempt,
                    "attempt_state": supply_state,
                    "manifest": str(supply["manifest"]),
                    "manifest_sha256": _sha256_file(supply["manifest"]),
                    "outputs_sha256": _sha256_file(supply["outputs"]),
                },
            },
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
                "schema": "saea-a2t-self-consistency-flight-failure-v1",
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
    parser.add_argument(
        "--resume-observation-manifest",
        type=Path,
        help=(
            "reuse one complete ABORTED observation bundle after a downstream "
            "zero-contact supply refusal; the observation is never re-flown"
        ),
    )
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
                    "official_score_workers": 2,
                    "scoring_boundary": "one-complete-manifest-per-process",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(
        json.dumps(
            _launch(
                root,
                resume_observation_manifest=args.resume_observation_manifest,
            ),
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
