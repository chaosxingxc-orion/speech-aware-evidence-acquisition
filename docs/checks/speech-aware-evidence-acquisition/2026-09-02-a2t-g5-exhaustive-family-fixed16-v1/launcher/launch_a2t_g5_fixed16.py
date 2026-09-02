#!/usr/bin/env python3
"""Preflight and launch the G5 exhaustive-family fixed16 ground screen.

The contact-free preflight reconstructs only frozen identities, sealed packet
metadata, the exhaustive family compiler, and prompt envelopes.  ``--run``
owns one receipt-pinned local decoder session and performs exactly PLAN then
EXECUTE for each of sixteen samples.  It seals outputs without opening gold or
running the scorer.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

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
    emit_composite_rows,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g5_agentloop import (  # noqa: E402
    EXECUTE_CONTACT_ID,
    G5_QUEUE_DEPTH,
    G5_SLOT_COUNT,
    PLAN_CONTACT_ID,
    G5AgentLoopAdapter,
    run_g5_agentloop,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g5_corpus_integration import (  # noqa: E402
    COMMITTED_CORPUS_SHA256,
    COMMITTED_FIXED16_IDENTITY_SHA256,
    COMMITTED_G1_PROMOTION_SHA256,
    COMMITTED_G1_RECEIPT_SHA256,
    CorpusFamilyCompiler,
    FALLBACK_FAMILY_TAGS,
    build_prompt_fit_report,
    load_fixed16_runtime_surface,
)


RUN_ID = "SAEA-A2T-G5-EXHAUSTIVE-FAMILY-FIXED16-V1"
SPLIT_ID = "A2T-G5-FIXED16"
RUNTIME_ROOT = Path("/home/chao")
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-G1-104-promotion.json"

MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-g5-exhaustive-family-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g5-exhaustive-family-fixed16-v1"

BASELINE_CONFIG_RELPATH = Path(
    "configs/baseline/a2t-g5-exhaustive-family-agentloop.json"
)
EXPERIMENT_CONFIG_RELPATH = Path(
    "configs/experiment/a2t-g5-exhaustive-family-fixed16-v1.json"
)
INTEGRATION_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/probes/"
    "a2t_g5_corpus_integration.py"
)
AGENTLOOP_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/probes/a2t_g5_agentloop.py"
)
CORPUS_RELPATH = Path(
    "knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json"
)
G1_RECEIPT_RELPATH = Path("docs/receipts/a2t/A2T-G1-104.json")
FIXED16_RECEIPT_RELPATH = Path("docs/receipts/a2t/A2T-G5-FIXED16-IDENTITY.json")
PROMPT_FIT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g5-fixed16-integration-prompt-fit-v1/prompt-fit.json"
)
RUNTIME_RECEIPT_RELPATH = Path("docs/receipts/runtime-q4km-mmproj-free.json")

BASELINE_CONFIG_SHA256: str | None = (
    "bda861b2d110b2b98b9a0cc8ffa3311cef21d2325091ff2be42417a3a8152e92"
)
EXPERIMENT_CONFIG_SHA256: str | None = (
    "fb69d031fc291e9fdc228430acfda95d9f743059795059593205891e57afe0c4"
)
COMPOSED_CONFIG_SHA256: str | None = (
    "797bf47bcb7fb7c94c46a79cc62e9cd1963414d48c3aa3f8912020f450607f09"
)
PROTOCOL_SHA256: str | None = (
    "e669d545e7ffb7ed09e9a827e99951807699c9fc49796d5942a0b31f6716f9fd"
)
INTEGRATION_SHA256: str | None = (
    "dc6ad763473d7f7854f900330cacf5194a5ccc5beab9955ce0ee97b613541c5d"
)
AGENTLOOP_SHA256 = (
    "df4f40b6b4269b8dc453ef8579ca9ed8b643b020dc5b7852a750488a4639491c"
)
PROMPT_FIT_SHA256 = (
    "75b1a9bfbff4373d4cc35d7ce472ae888567a03863a2a9d226c141eb4289c869"
)
RUNTIME_RECEIPT_SHA256 = (
    "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
)

SELECTED_SPLIT_SHA256 = (
    "c1c38f4ac670846df8c2a488aa62642bb6d14733aa8cc4fa33955f5c2bf76550"
)
SELECTED_RUN_SHA256 = (
    "8c0136a901693548a737bf4bf3fa83206d9bae190283123d6412be6a78b069fe"
)
SELECTED_AUDIO_SECONDS = 123.209
PLANNED_AUDIO_SECONDS = 247
SELECTED_IDS = tuple(
    sorted(
        (
            "tier1_direct:002609",
            "tier1_direct:002728",
            "tier2_parametric:003923",
            "tier2_parametric:006317",
            "tier3_multi_intent:002995",
            "tier3_multi_intent:003153",
            "tier4_implicit:001074",
            "tier4_implicit:001148",
            "tier5_needle:000241",
            "tier5_needle:002215",
            "tier6_correction:002179",
            "tier6_correction:003197",
            "tier7_multiturn:000545",
            "tier7_multiturn:002120",
            "tier8_intent_blending:000581",
            "tier8_intent_blending:000720",
        )
    )
)
EXPECTED_TIERS = tuple(
    f"tier{number}_{name}"
    for number, name in enumerate(
        (
            "direct",
            "parametric",
            "multi_intent",
            "implicit",
            "needle",
            "correction",
            "multiturn",
            "intent_blending",
        ),
        start=1,
    )
)

SLOT_COUNT = G5_SLOT_COUNT
QUEUE_DEPTH = G5_QUEUE_DEPTH
MAX_CONTACTS = 2
MAX_TOTAL_CONTACTS = 32
TEMPERATURE = 0
REPAIR_CONTACTS = 0
RETRIES = 0
JITTER_TESTING = False
OPENJIUWEN_VERSION = "0.1.16.post2"
INTEGRATION_SCHEMA = "saea-a2t-g5-fixed16-model-free-prompt-fit-v1"

OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "workers": 1,
    "processes_per_job": 1,
    "operation": "score",
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "g5-final16",
            "input": "complete final16 output manifest",
            "row_count": 16,
        }
    ],
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    measured = _sha256_file(path)
    if measured != expected:
        raise RuntimeError(f"{label} SHA-256 drift: {measured}")


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
            json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _unbound_requirements() -> tuple[str, ...]:
    values = {
        "BASELINE_CONFIG_SHA256": BASELINE_CONFIG_SHA256,
        "EXPERIMENT_CONFIG_SHA256": EXPERIMENT_CONFIG_SHA256,
        "COMPOSED_CONFIG_SHA256": COMPOSED_CONFIG_SHA256,
        "PROTOCOL_SHA256": PROTOCOL_SHA256,
        "INTEGRATION_SHA256": INTEGRATION_SHA256,
    }
    return tuple(key for key, value in values.items() if value is None)


def _require_bound_requirements() -> None:
    missing = _unbound_requirements()
    if missing:
        raise RuntimeError(f"G5 launcher bindings are incomplete: {', '.join(missing)}")


def _validate_selected_ids(tier_by_sample: Mapping[str, str]) -> tuple[str, ...]:
    if set(tier_by_sample) != set(SELECTED_IDS):
        raise RuntimeError("runtime identities drift from G5 fixed16")
    if Counter(tier_by_sample.values()) != Counter(
        {tier: 2 for tier in EXPECTED_TIERS}
    ):
        raise RuntimeError("runtime tiers drift from the fixed two-per-tier design")
    if any(
        tier_by_sample[sample_id] != sample_id.split(":", 1)[0]
        for sample_id in SELECTED_IDS
    ):
        raise RuntimeError("runtime tier labels disagree with sample identities")
    return SELECTED_IDS


def _execution_plan(
    attempt_id: str, *, protocol_hash: str | None = None
) -> ExecutionPlan:
    bound_protocol = protocol_hash if protocol_hash is not None else PROTOCOL_SHA256
    if bound_protocol is None:
        raise RuntimeError("G5 protocol identity is not bound")
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SELECTED_RUN_SHA256,
        planned_model_calls=MAX_TOTAL_CONTACTS,
        planned_gpu_hours=0.3,
        planned_speech_audio_seconds=PLANNED_AUDIO_SECONDS,
        protocol_hash=bound_protocol,
        attempt_id=attempt_id,
    ).validate()


def _verified_split() -> VerifiedSplit:
    return VerifiedSplit(
        name=SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=SELECTED_IDS,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in SELECTED_IDS),
        identity_hash=SELECTED_RUN_SHA256,
    )


def _load_committed_corpus() -> CorpusFamilyCompiler:
    compiler = CorpusFamilyCompiler.from_path(REPO / CORPUS_RELPATH)
    if compiler.corpus_sha256 != COMMITTED_CORPUS_SHA256:
        raise RuntimeError("G5 corpus identity drift")
    return compiler


def _build_compiler(
    corpus: CorpusFamilyCompiler,
    fallback: Sequence[str] = FALLBACK_FAMILY_TAGS,
) -> tuple[CorpusFamilyCompiler, object]:
    if not isinstance(corpus, CorpusFamilyCompiler):
        raise RuntimeError("G5 corpus loader returned the wrong compiler type")
    if tuple(fallback) != corpus.fallback_family_tags:
        raise RuntimeError("G5 fallback family union drift")
    return corpus, corpus.snapshot


def _snapshot_sha256(corpus: CorpusFamilyCompiler) -> str:
    return corpus.snapshot.content_hash()


def _validate_integration_and_envelopes(
    integration: Mapping[str, object],
    *,
    corpus: CorpusFamilyCompiler,
    compiler: CorpusFamilyCompiler,
    snapshot: object,
    speech_feature_tokens_by_sample: Mapping[str, int],
) -> Mapping[str, object]:
    del corpus
    if snapshot.content_hash() != compiler.snapshot.content_hash():
        raise RuntimeError("G5 compiler and snapshot identities disagree")
    unions = integration.get("allowed_family_unions")
    declared = {
        tuple(row) for row in unions if isinstance(row, list)
    } if isinstance(unions, list) else set()
    expected = {(taxon.family_tag,) for taxon in compiler.taxonomy}
    if declared != expected:
        raise RuntimeError("G5 integration family declaration is not exhaustive")
    maximum_speech = max(speech_feature_tokens_by_sample.values())
    return {
        "family_count": len(compiler.taxonomy),
        "declared_union_count": len(declared),
        "maximum_total_tokens": int(integration.get("maximum_total_tokens", 26_219)),
        "maximum_bundle_ascii_bytes": int(
            integration.get("maximum_bundle_ascii_bytes", 18_426)
        ),
        "maximum_speech_feature_tokens": maximum_speech,
    }


def _validate_official_score_plan(plan: Mapping[str, object]) -> Mapping[str, object]:
    jobs = plan.get("jobs")
    if (
        plan.get("workers") != 1
        or plan.get("processes_per_job") != 1
        or plan.get("operation") != "score"
        or plan.get("dataset_sharding") is not False
        or plan.get("shard_metric_averaging") is not False
        or plan.get("network_jitter_testing") is not False
        or not isinstance(jobs, list)
        or len(jobs) != 1
        or not isinstance(jobs[0], Mapping)
        or jobs[0].get("input") != "complete final16 output manifest"
        or jobs[0].get("row_count") != 16
    ):
        raise RuntimeError("G5 scoring must be one complete final16 manifest job")
    return plan


def _static_preflight(root: Path) -> dict[str, object]:
    _require_bound_requirements()
    commit = require_clean_study_repo(REPO)
    for relpath, expected, label in (
        (BASELINE_CONFIG_RELPATH, BASELINE_CONFIG_SHA256, "baseline config"),
        (EXPERIMENT_CONFIG_RELPATH, EXPERIMENT_CONFIG_SHA256, "experiment config"),
        (INTEGRATION_RELPATH, INTEGRATION_SHA256, "G5 integration"),
        (AGENTLOOP_RELPATH, AGENTLOOP_SHA256, "G5 AgentLoop"),
        (CORPUS_RELPATH, COMMITTED_CORPUS_SHA256, "G5 corpus"),
        (G1_RECEIPT_RELPATH, COMMITTED_G1_RECEIPT_SHA256, "G1 receipt"),
        (
            FIXED16_RECEIPT_RELPATH,
            COMMITTED_FIXED16_IDENTITY_SHA256,
            "G5 fixed16 receipt",
        ),
        (PROMPT_FIT_RELPATH, PROMPT_FIT_SHA256, "G5 prompt-fit receipt"),
        (RUNTIME_RECEIPT_RELPATH, RUNTIME_RECEIPT_SHA256, "runtime receipt"),
    ):
        if expected is None:
            raise RuntimeError(f"{label} identity is not bound")
        _require_hash(REPO / relpath, expected, label)
    _require_hash(PROMOTION_RECEIPT, COMMITTED_G1_PROMOTION_SHA256, "promotion receipt")

    composed = compose(
        REPO,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("G5 composed config identity drift")
    measured_protocol = protocol_hash(
        composed.config_hash, str(composed.values["arm"]), SELECTED_RUN_SHA256
    )
    if measured_protocol != PROTOCOL_SHA256:
        raise RuntimeError("G5 protocol identity drift")
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("openJiuwen version drift")
    if int(composed.values["profile_slot_count"]) != SLOT_COUNT:
        raise RuntimeError("G5 slot geometry drift")
    if "-np" not in composed.values["server_args"]:
        raise RuntimeError("G5 server geometry does not declare parallel slots")

    surface = load_fixed16_runtime_surface(
        g1_receipt_path=REPO / G1_RECEIPT_RELPATH,
        fixed16_identity_path=REPO / FIXED16_RECEIPT_RELPATH,
        promotion_receipt_path=PROMOTION_RECEIPT,
        expected_g1_sha256=COMMITTED_G1_RECEIPT_SHA256,
        expected_fixed16_sha256=COMMITTED_FIXED16_IDENTITY_SHA256,
        expected_promotion_sha256=COMMITTED_G1_PROMOTION_SHA256,
    )
    if surface.split_identity_hash != SELECTED_SPLIT_SHA256:
        raise RuntimeError("G5 partition identity drift")
    tier_by_sample = {
        sample.sample_id: sample.sample_id.split(":", 1)[0]
        for sample in surface.samples
    }
    _validate_selected_ids(tier_by_sample)
    if abs(sum(sample.audio_seconds for sample in surface.samples) - SELECTED_AUDIO_SECONDS) > 1e-6:
        raise RuntimeError("G5 fixed16 audio duration drift")

    compiler = _load_committed_corpus()
    adapter = G5AgentLoopAdapter(
        surface.samples, split_id=SPLIT_ID, taxonomy=compiler.taxonomy
    )
    prompt_report = build_prompt_fit_report(compiler=compiler, runtime=surface)
    committed_prompt_report = json.loads(
        (REPO / PROMPT_FIT_RELPATH).read_text(encoding="utf-8")
    )
    if prompt_report != committed_prompt_report or prompt_report.get("status") != "PASS":
        raise RuntimeError("G5 prompt-fit reconstruction drift")
    _validate_official_score_plan(OFFICIAL_SCORE_PLAN)
    lock = load_lock(umbrella_lock_path(REPO))
    runtime_document = json.loads(
        (REPO / RUNTIME_RECEIPT_RELPATH).read_text(encoding="utf-8")
    )
    return {
        "commit": commit,
        "composed": composed,
        "lock": lock,
        "surface": surface,
        "compiler": compiler,
        "snapshot": compiler.snapshot,
        "adapter": adapter,
        "prompt_report": prompt_report,
        "runtime_receipt": runtime_document,
        "selected_ids": SELECTED_IDS,
    }


def _run_phase(
    *,
    root: Path,
    plan: object,
    adapter: G5AgentLoopAdapter,
    client: object,
    snapshot: object,
    packet_bindings: Mapping[str, Mapping[str, object]],
    speech_feature_tokens_by_sample: Mapping[str, int],
    compiler: CorpusFamilyCompiler,
    trace_sink: object,
    run_phase: Callable[..., object] = run_g5_agentloop,
) -> object:
    summary = run_phase(
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        knowledge_snapshot=snapshot,
        speech_packet_bindings=packet_bindings,
        speech_feature_tokens_by_sample=speech_feature_tokens_by_sample,
        compiler=compiler,
        trace_sink=trace_sink,
    )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != 16:
        raise RuntimeError("G5 did not return sixteen results")
    if tuple(sorted(str(row.sample_id) for row in results)) != SELECTED_IDS:
        raise RuntimeError("G5 result identity surface drift")
    if sum(len(row.contacts) for row in results) != MAX_TOTAL_CONTACTS:
        raise RuntimeError("G5 did not complete exactly thirty-two contacts")
    for row in results:
        if tuple(contact.plan.contact_id for contact in row.contacts) != (
            PLAN_CONTACT_ID,
            EXECUTE_CONTACT_ID,
        ):
            raise RuntimeError("G5 contact order drift")
    return summary


def _plan_state_rows(summary: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in sorted(summary.results, key=lambda item: item.sample_id):
        if len(result.agent_states) != 1:
            raise RuntimeError("G5 requires exactly one canonical PLAN state per sample")
        contact = result.contacts[0]
        contact_json = (
            contact.as_json()
            if callable(getattr(contact, "as_json", None))
            else {"plan": {"contact_id": contact.plan.contact_id}}
        )
        rows.append(
            {
                "sample_id": result.sample_id,
                "nonfinal": True,
                "contact_id": PLAN_CONTACT_ID,
                "contact": contact_json,
                "state": result.agent_states[0].as_json(),
            }
        )
    return rows


def _final_execute_texts(summary: object) -> dict[str, str]:
    return {
        result.sample_id: result.final_response_text
        for result in sorted(summary.results, key=lambda item: item.sample_id)
    }


def _seal_outputs(
    *,
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    summary: object,
    client_summary: Mapping[str, object],
    run_dir: Path,
    agent_trace_hash: str,
    session_receipt_path: Path,
) -> dict[str, object]:
    plan_states = run_dir / "g5-plan-states.jsonl"
    _write_jsonl(plan_states, _plan_state_rows(summary))
    plan_contacts = run_dir / "g5-plan-contact-manifest.json"
    plan_document = {
        "schema": "saea-a2t-g5-plan-contact-manifest-v1",
        "run_id": RUN_ID,
        "row_count": 16,
        "contact_id": PLAN_CONTACT_ID,
        "nonfinal": True,
        "rows_path": str(plan_states),
        "rows_sha256": _sha256_file(plan_states),
    }
    _write_json(plan_contacts, plan_document)

    trace_path = run_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
    texts = _final_execute_texts(summary)
    source_by_id = {
        sample_id: {
            "action": EXECUTE_CONTACT_ID,
            "source_agent_trace_manifest_sha256": agent_trace_hash,
            "source_artifact_path": str(trace_path),
            "source_artifact_sha256": _sha256_file(trace_path),
        }
        for sample_id in SELECTED_IDS
    }
    sink = TraceSink(run_dir, RUN_ID)
    output_rows = emit_composite_rows(
        texts=texts, source_by_id=source_by_id, sink=sink, variant="main"
    )
    output_trace_hash = sink.close()
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, output_rows)
    cost = dict(client_summary["cost"])
    cost["tool_calls"] = MAX_TOTAL_CONTACTS
    manifest = build_manifest(
        repo_root=REPO,
        data_root=root,
        composed=context["composed"],
        plan=plan,
        verified_split=_verified_split(),
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=STATUS_COMPLETED,
        result=RunResult(
            run_id=RUN_ID,
            arm="speech-feature-query",
            outputs_path=outputs,
            trace_manifest_hash=output_trace_hash,
            cost=cost,
        ),
    )
    bundle = verify_bundle(manifest)
    if len(bundle.outputs_rows) != 16:
        raise RuntimeError("G5 final bundle is not complete final16")
    return {
        "plan_states": plan_states,
        "plan_states_sha256": _sha256_file(plan_states),
        "plan_contact_manifest": plan_contacts,
        "plan_contact_manifest_sha256": _sha256_file(plan_contacts),
        "outputs": outputs,
        "outputs_sha256": _sha256_file(outputs),
        "manifest": manifest,
        "manifest_sha256": _sha256_file(manifest),
        "agent_trace_manifest_sha256": agent_trace_hash,
        "output_trace_manifest_sha256": output_trace_hash,
    }


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt_id = f"attempt-{stamp.lower()}-g5-fixed16"
    plan = _execution_plan(attempt_id)
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}"
    run_dir = mission_dir / "g5"
    service_dir = mission_dir / "service"
    run_dir.mkdir(parents=True, exist_ok=False)
    service_dir.mkdir()
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    _write_json(run_dir / "official-score-plan.json", OFFICIAL_SCORE_PLAN)

    values = context["composed"].values
    runtime_receipt = load_runtime_receipt(REPO / RUNTIME_RECEIPT_RELPATH)
    model_root = Path(str(values["model_materialization_root"]))
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=str(RUNTIME_RECEIPT_RELPATH.relative_to("docs")),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=model_root,
    )
    gate.assert_model_touch_allowed(plan, full_hash=True)
    parsed_url = urlparse(str(values["base_url"]))
    if parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.port is None:
        raise RuntimeError("G5 decoder must use an explicit loopback port")
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = None
    client = None
    trace_sink = None
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
        surface = context["surface"]
        binding = build_payload_binding(
            carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
            samples=surface.samples,
            data_root=root,
            carrier_root=asset_dir(context["lock"], AUDIO2TOOL_LOCK_KEY, root),
        )
        client = FrozenCoreClient(
            plan=plan,
            gate=gate,
            transport=transport,
            run_dir=run_dir / "transport-trace",
            binding=binding,
            arm="speech-feature-query",
            request_id_prefix="g5fixed16",
            speech_feature_root=FEATURE_ROOT,
            speech_packet_bindings=surface.packet_bindings,
        )
        trace_sink = TraceSink(run_dir / "agent-trace", RUN_ID)
        summary = _run_phase(
            root=root,
            plan=plan,
            adapter=context["adapter"],
            client=client,
            snapshot=context["snapshot"],
            packet_bindings=surface.packet_bindings,
            speech_feature_tokens_by_sample=surface.speech_feature_tokens_by_sample,
            compiler=context["compiler"],
            trace_sink=trace_sink,
        )
        agent_trace_hash = trace_sink.close()
        trace_sink = None
        client_summary = client.close()
        client = None
        if client_summary.get("request_count") != MAX_TOTAL_CONTACTS:
            raise RuntimeError("G5 transport did not record thirty-two requests")
        stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            force_after_timeout=True,
            receipt_path=stop_receipt,
        )
        session = None
        sealed = _seal_outputs(
            root=root,
            context=context,
            plan=plan,
            summary=summary,
            client_summary=client_summary,
            run_dir=run_dir,
            agent_trace_hash=agent_trace_hash,
            session_receipt_path=session_receipt,
        )
        receipt = {
            "schema": "saea-a2t-g5-exhaustive-family-fixed16-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SEALED_UNSCORED",
            "study_commit": context["commit"],
            "attempt_id": attempt_id,
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "model_contacts": MAX_TOTAL_CONTACTS,
            "plan_contacts": 16,
            "execute_contacts": 16,
            "repair_contacts": REPAIR_CONTACTS,
            "retries": RETRIES,
            "network_jitter_testing": JITTER_TESTING,
            "slot_count": SLOT_COUNT,
            "queue_depth": QUEUE_DEPTH,
            "scorer_contacts": 0,
            **{
                key: str(value) if isinstance(value, Path) else value
                for key, value in sealed.items()
            },
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _write_json(
            mission_dir / "failure-receipt.json",
            {"run_id": RUN_ID, "attempt_id": attempt_id, "error": repr(error)},
        )
        raise
    finally:
        if trace_sink is not None:
            trace_sink.close()
        if client is not None:
            client.close()
        if session is not None:
            stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
                force_after_timeout=True,
                receipt_path=stop_receipt,
            )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = data_root()
    if args.preflight_only:
        context = _static_preflight(root)
        prompt_report = context["prompt_report"]
        plan_envelope = (
            prompt_report["plan"]["maximum_envelope_tokens"]
            if "plan" in prompt_report
            else prompt_report["maximum_total_tokens"]
        )
        execute_envelope = (
            prompt_report["execute"]["maximum_envelope_tokens"]
            if "execute" in prompt_report
            else prompt_report["maximum_total_tokens"]
        )
        print(
            json.dumps(
                {
                    "run_id": RUN_ID,
                    "preflight": "passed",
                    "study_commit": context["commit"],
                    "samples": len(context["selected_ids"]),
                    "planned_model_calls": MAX_TOTAL_CONTACTS,
                    "plan_maximum_envelope_tokens": plan_envelope,
                    "execute_maximum_envelope_tokens": execute_envelope,
                    "official_score_manifests": 1,
                    "contacts": {
                        "gold": 0,
                        "model": 0,
                        "network": 0,
                        "retriever_service": 0,
                        "scorer": 0,
                        "tokenizer": 0,
                    },
                },
                sort_keys=True,
            )
        )
        return 0
    result = _launch(root)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
