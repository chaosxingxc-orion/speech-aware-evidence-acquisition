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
from speech_aware_evidence_acquisition.core.attempts import AttemptStore  # noqa: E402
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
RECOVERY_ATTEMPT_ID = "attempt-20260901t203803z-selftxobs"
RECOVERY_OBSERVATION_RELPATH = Path(
    "runs/SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1/"
    "flight-20260901T203803Z/observation"
)
RECOVERY_ATTEMPT_RELPATH = Path(
    "attempts/SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1/"
    f"{RECOVERY_ATTEMPT_ID}.json"
)
RECOVERY_OUTPUTS_SHA256 = (
    "b37f5d2b92404a41c4b9f0ca8516fff612d44befeb2be6428eacf73a6b694544"
)
RECOVERY_TRACE_SHA256 = (
    "d4161541fc0d438ca6f5d01b0775e6337124275f4d715f066812789e02eca4de"
)
RECOVERY_PLAN_SHA256 = (
    "c6b0202a24708f3b91b5edfc9c87a42a235598cde18df8efecc99afaa3d73e37"
)
RECOVERY_FAILURE_SHA256 = (
    "92f8ec2f59fbad661af6175abf50e17bd9f152c3ca734540d27e0d773406b2cb"
)
RECOVERY_ATTEMPT_SHA256 = (
    "780ec2a2d5924e020b4360b0a7d5dc53f681ffcd600e4d6ff3c984c85d733c04"
)
RECOVERY_USE_SOURCE_RELPATH = Path(
    "runs/SAEA-A2T-TFRL-SELF-TRANSCRIPT-CASCADE-104-V1/"
    "flight-20260901T205433Z"
)
RECOVERY_MATCHED_ATTEMPT_ID = "attempt-20260901t205433z-selftxmatch"
RECOVERY_SHUFFLED_ATTEMPT_ID = "attempt-20260901t205433z-selftxshuffle"
RECOVERY_MATCHED_MANIFEST_SHA256 = (
    "f553c1ac684ebcb85e95622be751a630369eeb734d2a5007f139c51568903c50"
)
RECOVERY_SHUFFLED_MANIFEST_SHA256 = (
    "060e54b07f3c82ae09e2577283535884928c6098f58da406cd33611329b6ee92"
)
RECOVERY_MATCHED_ATTEMPT_SHA256 = (
    "171bde8c2d7c4e8da0bcb464aeca1998d53a67000ee5c301bcca6e52d9017e59"
)
RECOVERY_SHUFFLED_ATTEMPT_SHA256 = (
    "76eec7326174f0f211e300a3a1a6ee7c770a31ac0552ecd05c188340637d2781"
)
RECOVERY_USE_FAILURE_SHA256 = (
    "71223984c545dd19a84b3f06d38b6b706d381a04a8d0157dafcad38212b1f91e"
)
RECOVERY_KNOWN_ATTEMPT_RELPATHS = (
    RECOVERY_ATTEMPT_RELPATH,
    RECOVERY_ATTEMPT_RELPATH.with_name(f"{RECOVERY_MATCHED_ATTEMPT_ID}.json"),
    RECOVERY_ATTEMPT_RELPATH.with_name(f"{RECOVERY_SHUFFLED_ATTEMPT_ID}.json"),
)


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


def _close_phase_traces(
    trace_sink: object, client: object
) -> tuple[str, Mapping[str, object]]:
    """Seal the authoritative phase trace before the adapter-owned fallback sink."""

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
    retriever = cascade.EvidenceRetriever(context["snapshot"])  # type: ignore[arg-type]
    transcripts: dict[str, cascade.TranscriptParse] = {}
    routes: dict[str, cascade.EvidenceRoute] = {}
    observations: list[cascade.ObservationRecord] = []
    tiers = {
        str(item["sample_id"]): str(item["tier"])
        for item in context["items"]  # type: ignore[union-attr]
    }
    for sample_id in expected_ids:
        parsed = cascade.validate_self_transcript(responses.get(sample_id))
        route = (
            retriever.route(parsed.text)
            if parsed.valid
            else cascade.EvidenceRoute(False, (), (), (), (), 0, 0.0, "")
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
    material: dict[str, object] = {
        "passed": report.passed,
        "report": report,
        "transcripts": transcripts,
        "routes": routes,
        "tiers": tiers,
    }
    if not report.passed:
        return material
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
    material.update(
        {
            "receipt": receipt,
            "routed_tiers": routed_tiers,
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
            "schema": "saea-a2t-self-transcript-liveness-report-v1",
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
    routed_tiers = material["routed_tiers"]
    shuffled_material = material["shuffled_material"]
    _write_json(
        run_dir / "use-authorization-receipt.json",
        {
            "schema": "saea-a2t-self-transcript-use-authorization-v1",
            "liveness": asdict(material["receipt"]),  # type: ignore[arg-type]
            "routed_ids": sorted(routed_tiers),  # type: ignore[arg-type]
            "routed_tiers": dict(sorted(routed_tiers.items())),  # type: ignore[union-attr]
            "same_tier_donors": {
                sample_id: shuffled_material[sample_id].donor_id  # type: ignore[index]
                for sample_id in sorted(shuffled_material)  # type: ignore[arg-type]
            },
            "resend_ids": list(material["resend_ids"]),  # type: ignore[arg-type]
            "sealed_before_use": True,
        },
    )


def _load_recovered_observation(
    root: Path, context: Mapping[str, object]
) -> dict[str, object]:
    """Load the one registered OBS abort without repeating a model contact."""

    source_dir = (Path(root) / RECOVERY_OBSERVATION_RELPATH).resolve()
    expected_source = (Path(root).resolve() / RECOVERY_OBSERVATION_RELPATH).resolve()
    if source_dir != expected_source:
        raise RuntimeError("recovery observation path escaped the registered data root")
    outputs_path = source_dir / f"{RUN_ID}.outputs.jsonl"
    trace_path = source_dir / f"{RUN_ID}.trace.jsonl"
    plan_path = source_dir / "execution-plan.json"
    failure_path = source_dir.parent / "failure-receipt.json"
    attempt_path = (Path(root) / RECOVERY_ATTEMPT_RELPATH).resolve()
    fixed = (
        (outputs_path, RECOVERY_OUTPUTS_SHA256, "outputs"),
        (trace_path, RECOVERY_TRACE_SHA256, "trace"),
        (plan_path, RECOVERY_PLAN_SHA256, "execution plan"),
        (failure_path, RECOVERY_FAILURE_SHA256, "failure receipt"),
        (attempt_path, RECOVERY_ATTEMPT_SHA256, "attempt record"),
    )
    for path, expected_sha256, label in fixed:
        if not path.is_file() or _sha256_file(path) != expected_sha256:
            raise RuntimeError(f"recovery {label} SHA-256 drift")
    attempt_files = sorted(attempt_path.parent.glob("*.json"))
    expected_attempt_files = sorted(
        (Path(root) / relpath).resolve()
        for relpath in RECOVERY_KNOWN_ATTEMPT_RELPATHS
    )
    if attempt_files != expected_attempt_files:
        raise RuntimeError("recovery run has unregistered sibling attempt spend")
    plan_document = _read_json(plan_path)
    failure_document = _read_json(failure_path)
    attempt_document = _read_json(attempt_path)
    actual = attempt_document.get("actual")
    if (
        plan_document.get("attempt_id") != RECOVERY_ATTEMPT_ID
        or failure_document.get("attempt_ids", {}).get("observation")  # type: ignore[union-attr]
        != RECOVERY_ATTEMPT_ID
        or "trace manifest" not in str(failure_document.get("error", ""))
        or attempt_document.get("attempt_id") != RECOVERY_ATTEMPT_ID
        or attempt_document.get("run_id") != RUN_ID
        or attempt_document.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != SPLIT_COUNT
        or abs(float(actual.get("audio_seconds", -1)) - SPLIT_AUDIO_SECONDS) > 1e-9
    ):
        raise RuntimeError("recovery source is not the registered 104-call OBS abort")
    rows = [
        json.loads(line)
        for line in outputs_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    expected_ids = tuple(sorted(str(value) for value in context["sample_ids"]))  # type: ignore[union-attr]
    if len(rows) != SPLIT_COUNT or any(not isinstance(row, Mapping) for row in rows):
        raise RuntimeError("recovery outputs are not exactly 104 objects")
    responses: dict[str, str] = {}
    output_by_request: dict[str, Mapping[str, object]] = {}
    for row in rows:
        sample_id = str(row.get("sample_id", ""))
        request_id = str(row.get("request_id", ""))
        text = row.get("text")
        if (
            sample_id in responses
            or request_id in output_by_request
            or not isinstance(text, str)
            or row.get("phase") != OBSERVATION_PHASE
            or row.get("admitted") is not True
            or row.get("response_text_sha256") != _sha256_text(text)
        ):
            raise RuntimeError("recovery output row binding is malformed")
        responses[sample_id] = text
        output_by_request[request_id] = row
    if set(responses) != set(expected_ids):
        raise RuntimeError("recovery output identities differ from the frozen split")
    requests: dict[str, Mapping[str, object]] = {}
    response_records: dict[str, Mapping[str, object]] = {}
    for document in _trace_documents(source_dir):
        record_id = str(document.get("record_id", ""))
        payload = document.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if document.get("channel") == "MODEL_REQUEST" and record_id.endswith("/request"):
            requests[record_id.removesuffix("/request")] = payload
        if document.get("channel") == "MODEL_RESPONSE" and record_id.endswith("/response"):
            response_records[record_id.removesuffix("/response")] = payload
    if set(requests) != set(output_by_request) or set(response_records) != set(
        output_by_request
    ):
        raise RuntimeError("recovery trace does not bind every OBS request and response")
    for request_id, row in output_by_request.items():
        request = requests[request_id]
        response = response_records[request_id]
        request_payload = request.get("payload")
        if (
            request.get("payload_sha256") != row.get("request_sha256")
            or not isinstance(request_payload, Mapping)
            or request_payload.get("sample_id") != row.get("sample_id")
            or response.get("response_sha256") != row.get("response_sha256")
            or response.get("response_text_sha256") != row.get("response_text_sha256")
            or response.get("text") != row.get("text")
        ):
            raise RuntimeError("recovery output/trace cryptographic binding drift")
    material = _materialize_observation(context, responses)
    if material["passed"] is not True:
        raise RuntimeError("registered recovery OBS no longer passes the frozen liveness gate")
    material.update(
        {
            "attempt_id": RECOVERY_ATTEMPT_ID,
            "manifest": None,
            "outputs": outputs_path,
            "recovery_source": {
                "observation_dir": str(source_dir),
                "outputs_sha256": RECOVERY_OUTPUTS_SHA256,
                "trace_sha256": RECOVERY_TRACE_SHA256,
                "execution_plan_sha256": RECOVERY_PLAN_SHA256,
                "failure_receipt_sha256": RECOVERY_FAILURE_SHA256,
                "attempt_record_sha256": RECOVERY_ATTEMPT_SHA256,
                "actual_calls": SPLIT_COUNT,
                "actual_audio_seconds": SPLIT_AUDIO_SECONDS,
            },
        }
    )
    return material


def _load_recovered_use_sources(
    root: Path,
    context: Mapping[str, object],
    observation: Mapping[str, object],
) -> dict[str, dict[str, object]]:
    """Verify and load the two complete USE surfaces from the second abort."""

    source_root = (Path(root) / RECOVERY_USE_SOURCE_RELPATH).resolve()
    failure_path = source_root / "failure-receipt.json"
    if (
        not failure_path.is_file()
        or _sha256_file(failure_path) != RECOVERY_USE_FAILURE_SHA256
    ):
        raise RuntimeError("recovery USE failure receipt SHA-256 drift")
    failure = _read_json(failure_path)
    if "not a MODEL_REQUEST" not in str(failure.get("error", "")):
        raise RuntimeError("recovery USE failure is not the registered resend extractor abort")
    expected_ids = set(str(value) for value in context["sample_ids"])  # type: ignore[union-attr]
    phase_specs = (
        (
            "matched",
            source_root / "matched-composite",
            RECOVERY_MATCHED_ATTEMPT_ID,
            RECOVERY_MATCHED_MANIFEST_SHA256,
            RECOVERY_MATCHED_ATTEMPT_SHA256,
        ),
        (
            "shuffled",
            source_root / "shuffled-evidence-composite",
            RECOVERY_SHUFFLED_ATTEMPT_ID,
            RECOVERY_SHUFFLED_MANIFEST_SHA256,
            RECOVERY_SHUFFLED_ATTEMPT_SHA256,
        ),
    )
    loaded: dict[str, dict[str, object]] = {}
    cumulative_calls = 0
    cumulative_audio = 0.0
    for name, run_dir, attempt_id, manifest_sha256, attempt_sha256 in phase_specs:
        manifest_path = run_dir / f"{RUN_ID}.run-manifest.json"
        attempt_path = (
            Path(root) / "attempts" / RUN_ID / f"{attempt_id}.json"
        ).resolve()
        if (
            not manifest_path.is_file()
            or _sha256_file(manifest_path) != manifest_sha256
            or not attempt_path.is_file()
            or _sha256_file(attempt_path) != attempt_sha256
        ):
            raise RuntimeError(f"recovery {name} manifest or attempt SHA-256 drift")
        verified = verify_bundle(manifest_path)
        attempt = _read_json(attempt_path)
        actual = attempt.get("actual")
        if (
            verified.attempt_state != "ABORTED"
            or verified.manifest.get("status") != STATUS_COMPLETED
            or len(verified.outputs_rows) != SPLIT_COUNT
            or not isinstance(actual, Mapping)
            or actual.get("calls") != SPLIT_COUNT
            or abs(float(actual.get("audio_seconds", -1)) - SPLIT_AUDIO_SECONDS) > 1e-9
        ):
            raise RuntimeError(f"recovery {name} is not a complete 104-call aborted USE")
        texts = {
            str(row["sample_id"]): str(row["text"]) for row in verified.outputs_rows
        }
        if set(texts) != expected_ids:
            raise RuntimeError(f"recovery {name} output identity drift")
        cumulative_calls += int(actual["calls"])
        cumulative_audio += float(actual["audio_seconds"])
        loaded[name] = {
            "texts": texts,
            "manifest": manifest_path,
            "outputs": verified.outputs_path,
            "request_source_run_dir": run_dir,
            "source_attempt_id": attempt_id,
            "source_manifest_sha256": manifest_sha256,
            "source_attempt_sha256": attempt_sha256,
        }
    if cumulative_calls != 208 or abs(cumulative_audio - 2 * SPLIT_AUDIO_SECONDS) > 1e-9:
        raise RuntimeError("recovery matched/shuffled cumulative spend drift")
    adapter = A2TSelfTranscriptAdapter(
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
    for source in loaded.values():
        source["binding"] = binding
    return loaded


def _materialize_recovered_use_derivative(
    *,
    root: Path,
    context: Mapping[str, object],
    source: Mapping[str, object],
    attempt_id: str,
    run_dir: Path,
    session_receipt_path: Path,
    lock_sha256: str,
    variant: str,
    action: str,
) -> dict[str, object]:
    """Create an OPENED, zero-model-call derivative of one sealed USE surface."""

    plan = _execution_plan(attempt_id)
    handle = AttemptStore(Path(root) / "attempts").open_attempt(
        RUN_ID,
        attempt_id,
        carrier_lock_key=plan.carrier_lock_key,
        reserved_calls=plan.planned_model_calls,
        reserved_audio_seconds=plan.planned_speech_audio_seconds,
    )
    if handle.state() != "OPENED":
        raise RuntimeError("recovered USE derivative attempt did not open")
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    source_outputs = Path(source["outputs"])  # type: ignore[arg-type]
    source_sha256 = _sha256_file(source_outputs)
    texts = {
        str(sample_id): str(text)
        for sample_id, text in source["texts"].items()  # type: ignore[union-attr]
    }
    expected_ids = set(str(value) for value in context["sample_ids"])  # type: ignore[union-attr]
    if set(texts) != expected_ids:
        raise RuntimeError("recovered USE derivative identity drift")
    sink = TraceSink(run_dir, RUN_ID)
    rows = emit_composite_rows(
        texts=texts,
        source_by_id={
            sample_id: {
                "action": action,
                "source_artifact_path": str(source_outputs),
                "source_artifact_sha256": source_sha256,
            }
            for sample_id in texts
        },
        sink=sink,
        variant=variant,
    )
    trace_manifest_hash = sink.close()
    outputs_path = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs_path, rows)
    cost = {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
        "tool_calls": len(texts),
        "umbrella_lock_sha256": lock_sha256,
        "derivation": (
            "model-free complete-manifest recovery from a fixed aborted USE source"
        ),
    }
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
        run_dir / "recovery-derivative-receipt.json",
        {
            "schema": "saea-a2t-self-transcript-use-recovery-derivative-v1",
            "variant": variant,
            "attempt_id": attempt_id,
            "source_attempt_id": source.get("source_attempt_id"),
            "source_manifest": str(source.get("manifest")),
            "source_manifest_sha256": source.get("source_manifest_sha256"),
            "source_outputs_sha256": source_sha256,
            "new_model_contacts": 0,
            "manifest": str(manifest_path),
            "manifest_sha256": _sha256_file(manifest_path),
        },
    )
    return {
        **source,
        "texts": texts,
        "manifest": manifest_path,
        "outputs": outputs_path,
        "attempt_id": attempt_id,
        "run_dir": run_dir,
        "ledger_deviation": (
            "zero-call complete-manifest derivative of the fixed aborted USE source"
        ),
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
    trace_manifest_hash, client_summary = _close_phase_traces(trace_sink, client)
    documents = _trace_documents(run_dir)
    rows, cost = build_phase_bundle_material(
        summary,
        documents,
        phase=OBSERVATION_PHASE,
        umbrella_lock_sha256=lock_sha256,
    )
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
        trace_manifest_hash=trace_manifest_hash,
        cost=cost,
        expected_attempt_state="OPENED",
    )
    material = _materialize_observation(context, _phase_responses(summary))
    _write_observation_receipts(run_dir, material)
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
    material.update(
        {
            "manifest": manifest_path,
            "outputs": outputs_path,
            "attempt_id": attempt_id,
        }
    )
    return material


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
    trace_manifest_hash, client_summary = _close_phase_traces(trace_sink, client)
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
        trace_manifest_hash=trace_manifest_hash,
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
    request_source_run_dir = Path(
        matched.get("request_source_run_dir", matched["run_dir"])  # type: ignore[arg-type]
    )
    documents = _trace_documents(request_source_run_dir)
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


def _human_ledger_cells(
    phase: str, lock_sha256: str, *, deviations: str = "none"
) -> dict[str, str]:
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
        "deviations": deviations,
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
    ]
    if finalize:
        command.append("--finalize")
    command.extend([
        "--jobs",
        str(jobs_path),
        "--output-dir",
        str(output_dir),
        "--workers",
        str(workers),
    ])
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
        _write_json(
            cells,
            _human_ledger_cells(
                phase,
                lock_sha256,
                deviations=str(result.get("ledger_deviation", "none")),
            ),
        )
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


def _launch(
    root: Path,
    *,
    recover_sealed_observation: bool = False,
    recover_sealed_use: bool = False,
) -> Mapping[str, object]:
    if recover_sealed_use and not recover_sealed_observation:
        raise RuntimeError("sealed USE recovery requires sealed observation recovery")
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = root / "runs" / RUN_ID / f"flight-{stamp}"
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    attempt_ids = {
        "matched": f"attempt-{stamp.lower()}-selftxmatchseal",
        "shuffled": f"attempt-{stamp.lower()}-selftxshuffleseal",
        "resend": f"attempt-{stamp.lower()}-selftxresend",
    }
    if not recover_sealed_observation:
        attempt_ids["observation"] = f"attempt-{stamp.lower()}-selftxobs"
    observation: Mapping[str, object] | None = None
    use_sources: Mapping[str, Mapping[str, object]] | None = None
    if recover_sealed_observation:
        observation = _load_recovered_observation(root, context)
        recovery_dir = mission_dir / "observation-reuse"
        _write_observation_receipts(recovery_dir, observation)
        _write_json(
            recovery_dir / "recovery-receipt.json",
            {
                "schema": "saea-a2t-self-transcript-observation-recovery-v1",
                "run_id": RUN_ID,
                "source_attempt_id": RECOVERY_ATTEMPT_ID,
                "source": observation["recovery_source"],
                "liveness": asdict(observation["report"]),  # type: ignore[arg-type]
                "new_observation_contacts": 0,
                "remaining_registered_call_ceiling": 230,
                "scientific_protocol_changed": False,
            },
        )
        if recover_sealed_use:
            use_sources = _load_recovered_use_sources(root, context, observation)
            _write_json(
                recovery_dir / "use-source-recovery-receipt.json",
                {
                    "schema": "saea-a2t-self-transcript-use-source-recovery-v1",
                    "source_root": str(Path(root) / RECOVERY_USE_SOURCE_RELPATH),
                    "matched_source_manifest_sha256": (
                        RECOVERY_MATCHED_MANIFEST_SHA256
                    ),
                    "shuffled_source_manifest_sha256": (
                        RECOVERY_SHUFFLED_MANIFEST_SHA256
                    ),
                    "source_failure_receipt_sha256": RECOVERY_USE_FAILURE_SHA256,
                    "source_calls": 208,
                    "cumulative_calls_before_resend": 312,
                    "new_matched_or_shuffled_contacts": 0,
                    "remaining_registered_call_ceiling": 22,
                    "scientific_protocol_changed": False,
                },
            )
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
    authorization_attempt = (
        attempt_ids["resend"]
        if recover_sealed_use
        else (
            attempt_ids["matched"]
            if recover_sealed_observation
            else attempt_ids["observation"]
        )
    )
    lock_sha256 = gate.assert_model_touch_allowed(
        _execution_plan(authorization_attempt), full_hash=True
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
        if observation is None:
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

        if use_sources is not None:
            matched = _materialize_recovered_use_derivative(
                root=root,
                context=context,
                source=use_sources["matched"],
                attempt_id=attempt_ids["matched"],
                run_dir=mission_dir / "matched-composite",
                session_receipt_path=session_receipt_path,
                lock_sha256=lock_sha256,
                variant="matched",
                action="RECOVER_MATCHED_ABORTED_SOURCE",
            )
            shuffled = _materialize_recovered_use_derivative(
                root=root,
                context=context,
                source=use_sources["shuffled"],
                attempt_id=attempt_ids["shuffled"],
                run_dir=mission_dir / "shuffled-evidence-composite",
                session_receipt_path=session_receipt_path,
                lock_sha256=lock_sha256,
                variant="shuffled-evidence",
                action="RECOVER_SHUFFLED_ABORTED_SOURCE",
            )
        else:
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
            "recovery": {
                "sealed_observation": recover_sealed_observation,
                "sealed_matched_and_shuffled": recover_sealed_use,
                "new_observation_contacts": 0 if recover_sealed_observation else SPLIT_COUNT,
                "new_matched_contacts": 0 if recover_sealed_use else SPLIT_COUNT,
                "new_shuffled_contacts": 0 if recover_sealed_use else SPLIT_COUNT,
            },
            "attempts": {
                "observation": (
                    {
                        "attempt_id": RECOVERY_ATTEMPT_ID,
                        "state": "REUSED_ABORTED_OBSERVATION",
                        "manifest": None,
                        "source": observation["recovery_source"],
                    }
                    if recover_sealed_observation
                    else {
                        "attempt_id": attempt_ids["observation"],
                        "state": "ABORTED_OBSERVATION_ONLY_SUCCESS",
                        "manifest": str(observation["manifest"]),
                    }
                ),
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
    parser.add_argument("--recover-sealed-observation", action="store_true")
    parser.add_argument("--recover-sealed-use", action="store_true")
    args = parser.parse_args(argv)
    if args.recover_sealed_use and not args.recover_sealed_observation:
        parser.error("--recover-sealed-use requires --recover-sealed-observation")
    root = data_root()
    if args.preflight_only:
        context = _static_preflight(root)
        recovery = (
            _load_recovered_observation(root, context)
            if args.recover_sealed_observation
            else None
        )
        recovered_use = (
            _load_recovered_use_sources(root, context, recovery)
            if args.recover_sealed_use and recovery is not None
            else None
        )
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
                    "recovery_observation": (
                        {
                            "source_attempt_id": RECOVERY_ATTEMPT_ID,
                            "liveness": asdict(recovery["report"]),
                            "new_observation_contacts": 0,
                            "remaining_registered_call_ceiling": 230,
                        }
                        if recovery is not None
                        else None
                    ),
                    "recovery_use": (
                        {
                            "source_attempt_ids": [
                                RECOVERY_MATCHED_ATTEMPT_ID,
                                RECOVERY_SHUFFLED_ATTEMPT_ID,
                            ],
                            "source_calls": 208,
                            "new_matched_or_shuffled_contacts": 0,
                            "remaining_registered_call_ceiling": 22,
                            "verified_variants": sorted(recovered_use),
                        }
                        if recovered_use is not None
                        else None
                    ),
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
                recover_sealed_observation=args.recover_sealed_observation,
                recover_sealed_use=args.recover_sealed_use,
            ),
            indent=2,
            sort_keys=True,
            default=str,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
