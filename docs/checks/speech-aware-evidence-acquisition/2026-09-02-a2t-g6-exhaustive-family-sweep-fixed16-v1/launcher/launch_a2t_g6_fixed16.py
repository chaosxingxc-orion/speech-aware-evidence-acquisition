#!/usr/bin/env python3
"""Preflight and launch the G6 exhaustive family-sweep fixed16 screen.

The default preflight is contact-free.  ``--run`` starts one receipt-pinned
local decoder and executes, for each of sixteen frozen discovery samples,
twenty-eight one-attempt family SCAN contacts followed by one dependent
RESOLVE contact.  The launcher seals every nonfinal SCAN record, phase trace,
and final RESOLVE output before any scorer or gold surface may be opened.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import threading
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
from speech_aware_evidence_acquisition.rails.probes.a2t_g6_corpus_integration import (  # noqa: E402
    COMMITTED_CORPUS_SHA256,
    COMMITTED_G1_PROMOTION_SHA256,
    COMMITTED_G1_RECEIPT_SHA256,
    COMMITTED_G6_ROSTER_SHA256,
    G6_MAX_FINAL_CALLS,
    G6CorpusAdapter,
    build_prompt_fit_report,
    load_g6_runtime_surface,
    measure_contact_prompt_fit,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g6_family_sweep import (  # noqa: E402
    CONTROLLER_POLICY_ID,
    FAMILY_COUNT,
    RESOLVE_CONTACT_ID,
    SCAN_CONTACT_PREFIX,
    ContactContext,
    FamilyScanReport,
    ParsedResolution,
    build_trace_documents,
)
RUN_ID = "SAEA-A2T-G6-EXHAUSTIVE-FAMILY-SWEEP-FIXED16-V1"
SPLIT_ID = "A2T-G6-FAMILY-SWEEP-FIXED16"
RUNTIME_ROOT = Path("/home/chao")
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-G1-104-promotion.json"

MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-g6-exhaustive-family-sweep-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g6-exhaustive-family-sweep-fixed16-v1"

BASELINE_CONFIG_RELPATH = Path(
    "configs/baseline/a2t-g6-exhaustive-family-sweep-agentloop.json"
)
EXPERIMENT_CONFIG_RELPATH = Path(
    "configs/experiment/a2t-g6-exhaustive-family-sweep-fixed16-v1.json"
)
INTEGRATION_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/probes/"
    "a2t_g6_corpus_integration.py"
)
SWEEP_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/probes/a2t_g6_family_sweep.py"
)
RENDERER_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/probes/a2t_g6_corpus_renderer.py"
)
CORPUS_RELPATH = Path(
    "knowledge/audio2tool/g5-exhaustive-family-contracts-v1/corpus.json"
)
G1_RECEIPT_RELPATH = Path("docs/receipts/a2t/A2T-G1-104.json")
FIXED16_RECEIPT_RELPATH = Path(
    "docs/receipts/a2t/A2T-G6-FAMILY-SWEEP-FIXED16.json"
)
RUNTIME_RECEIPT_RELPATH = Path("docs/receipts/runtime-q4km-mmproj-free.json")

BASELINE_CONFIG_SHA256: str | None = (
    "0e91cb0a5b3386b30726abd6bbee59455764bf0a66a35bee7a75c0d338a29784"
)
EXPERIMENT_CONFIG_SHA256: str | None = (
    "1c9b666e31e5c9171db2f550de649b795906a864ceb64895586616b62755be0c"
)
COMPOSED_CONFIG_SHA256: str | None = (
    "1cb12843cce818e3ce6fcb8d74213cbedf28de7bbd41435cd7ece3aff80b4007"
)
PROTOCOL_SHA256: str | None = (
    "42d6589ee37d285d0af60c0521be1b83a6106ce643385ec79e9ffaa10e2204bd"
)
INTEGRATION_SHA256: str | None = (
    "b338cc6cfbf55c19a3c156343ca4b5dbc4ee5444eafdb451e0778550f499aafe"
)
SWEEP_SHA256: str | None = (
    "23bb13fd5863d754cda2ff72cf4c15a281f388744577dc28c3dec24a4ecb9ec9"
)
RENDERER_SHA256: str | None = (
    "bbb17e8fbfb63aea22398dfc7f8ffc80fe59185f909c4ccfe2e4bd6b13b63fb5"
)
RUNTIME_RECEIPT_SHA256 = (
    "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
)

RECOVERY_SOURCE_ATTEMPT_ID = "attempt-20260902t220036z-g6-fixed16"
RECOVERY_SOURCE_ATTEMPT_SHA256 = (
    "7cf26402480106e905fd76f001df5a34a6f378e1e16d869c4d2304a018723542"
)
RECOVERY_SOURCE_TRACE_SHA256 = (
    "99f6b74b8eac96b540a0a8cf8e2db5d9ebd66ccd86e6c601769e3eb5ae11e81e"
)
RECOVERY_PRIOR_CONTACTS = 8
RECOVERY_CURRENT_CONTACTS = 456
SEAL_SOURCE_ATTEMPT_ID = "attempt-20260902t221239z-g6-fixed16"
SEAL_SOURCE_ATTEMPT_SHA256 = (
    "e7b085a829f9228ea92864b6f6b8e38ac068f85e9311d03352215a48c1345d40"
)
SEAL_SOURCE_TRACE_SHA256 = (
    "23f5eb29502e1a76ae9242536350e35cf2b9a362a9a982ea5f4b64dc8050b807"
)
SEAL_SOURCE_TRACE_MANIFEST_SHA256 = (
    "89ccefe85d4c3b651bc7d247efc06f977bf366cffe5a8e7fabc23d75ec48ff3a"
)
RECOVERY_EXPECTED_CONTACTS = (
    ("g6fixed16-0001", "tier1_direct:000077", "g6-scan-smart-car-navigation", "5652f43327026e4decdccd5f9b769e20126bedd4ee18334e45582c408440fd5c", "5eb4623ed48a2b54650c6d4d51ef27baa7682e51aab0cf17d7b87b80423fea77", "11a7a96d253b24fe9a68da2c46ac1be2201d08fea8184eabf845e3a5be774236"),
    ("g6fixed16-0002", "tier1_direct:004159", "g6-scan-smart-car-navigation", "27471d1fda32cd0b69587a6aab2958286431e23c1af43efba010dfa059350375", "ed8efcebb9ba3c0623026b092ad498293704d40f3964973338e9026999f02ec0", "d006b279d3b74fda72833d0cbe7042a7bdbaf096f1c8346e45bac562384ffbe5"),
    ("g6fixed16-0003", "tier1_direct:004159", "g6-scan-smart-car-core-control", "eab030824a979239592314cf33fbd211f985b7ef7345cd337ea7b0ed92def378", "2050fc32e4693fe64c82c0a813b473d7d2c05abbe4a7ae6dec538faa4ddf148d", "d006b279d3b74fda72833d0cbe7042a7bdbaf096f1c8346e45bac562384ffbe5"),
    ("g6fixed16-0004", "tier1_direct:000077", "g6-scan-smart-car-core-control", "1c2365048e4ff19f905d10b08131077b9d4e0c0dab4af37ac26f2a3bd592d56a", "780c98a9511020f6b39ef88dc1a3c43ae72690e11773d6ab72f41a5cd6ddade1", "d006b279d3b74fda72833d0cbe7042a7bdbaf096f1c8346e45bac562384ffbe5"),
    ("g6fixed16-0005", "tier2_parametric:001004", "g6-scan-smart-car-navigation", "19e495317bcf7aa7ba1a88d85d83177c4a396d854869a68605b88c2e158f7582", "5eb4623ed48a2b54650c6d4d51ef27baa7682e51aab0cf17d7b87b80423fea77", "11a7a96d253b24fe9a68da2c46ac1be2201d08fea8184eabf845e3a5be774236"),
    ("g6fixed16-0006", "tier2_parametric:002653", "g6-scan-smart-car-navigation", "61ca4ebda9feadffff7155a817cad66ab01e06904de4be2b19cf3464554639eb", "5eb4623ed48a2b54650c6d4d51ef27baa7682e51aab0cf17d7b87b80423fea77", "11a7a96d253b24fe9a68da2c46ac1be2201d08fea8184eabf845e3a5be774236"),
    ("g6fixed16-0007", "tier2_parametric:002653", "g6-scan-smart-car-core-control", "685bfa557c4cb2e407d6eb5bec615c107f963abbd9b788306f8ce9397a07aaf7", "780c98a9511020f6b39ef88dc1a3c43ae72690e11773d6ab72f41a5cd6ddade1", "d006b279d3b74fda72833d0cbe7042a7bdbaf096f1c8346e45bac562384ffbe5"),
    ("g6fixed16-0008", "tier2_parametric:001004", "g6-scan-smart-car-core-control", "84c8e145155adb4c3aac930851fd7fcf064e5a490b6b5e6bc60d2fd45f53d9a3", "780c98a9511020f6b39ef88dc1a3c43ae72690e11773d6ab72f41a5cd6ddade1", "d006b279d3b74fda72833d0cbe7042a7bdbaf096f1c8346e45bac562384ffbe5"),
)

SELECTED_SPLIT_SHA256 = (
    "a99a64f004534516399c520c742132dc31d5c06cab5e59240653ff586a60fcb5"
)
# Deliberately identical: the G6 roster receipt mandates the carrier-prefixed
# manifest convention for the plan, protocol, VerifiedSplit, and manifest.
SELECTED_RUN_SHA256 = SELECTED_SPLIT_SHA256
SELECTED_AUDIO_SECONDS = 87.001
PLANNED_AUDIO_SECONDS = 2600
SELECTED_IDS = tuple(
    sorted(
        (
            "tier1_direct:000077",
            "tier1_direct:004159",
            "tier2_parametric:001004",
            "tier2_parametric:002653",
            "tier3_multi_intent:001424",
            "tier3_multi_intent:003058",
            "tier4_implicit:000655",
            "tier4_implicit:001010",
            "tier5_needle:001458",
            "tier5_needle:004242",
            "tier6_correction:001764",
            "tier6_correction:002430",
            "tier7_multiturn:000440",
            "tier7_multiturn:001516",
            "tier8_intent_blending:000192",
            "tier8_intent_blending:000213",
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

SCAN_CONTACTS = FAMILY_COUNT
RESOLVE_CONTACTS = 1
MAX_CONTACTS = SCAN_CONTACTS + RESOLVE_CONTACTS
MAX_TOTAL_CONTACTS = len(SELECTED_IDS) * MAX_CONTACTS
SLOT_COUNT = 2
MAX_CONCURRENT_REQUESTS = 2
QUEUE_DEPTH = 4
TEMPERATURE = 0
REPAIR_CONTACTS = 0
RETRIES = 0
RESENDS = 0
JITTER_TESTING = False
OPENJIUWEN_VERSION = "0.1.16.post2"
WORKFLOW_TIMEOUT_SECONDS = 7_200.0

TASK_CONTRACT = (
    "Use the original speech as the only task authority. Inspect the supplied "
    "frozen family only as reference evidence during SCAN. RESOLVE only after "
    "all 28 bounded family reports are sealed."
)

OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "workers": 1,
    "processes_per_job": 1,
    "operation": "score",
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "g6-final16",
            "input": "complete final16 RESOLVE output manifest",
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
        "SWEEP_SHA256": SWEEP_SHA256,
        "RENDERER_SHA256": RENDERER_SHA256,
    }
    return tuple(key for key, value in values.items() if value is None)


def _require_bound_requirements() -> None:
    missing = _unbound_requirements()
    if missing:
        raise RuntimeError(f"G6 launcher bindings are incomplete: {', '.join(missing)}")


def _validate_selected_ids(tier_by_sample: Mapping[str, str]) -> tuple[str, ...]:
    if set(tier_by_sample) != set(SELECTED_IDS):
        raise RuntimeError("runtime identities drift from G6 fixed16")
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
        raise RuntimeError("G6 protocol identity is not bound")
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SELECTED_RUN_SHA256,
        planned_model_calls=MAX_TOTAL_CONTACTS,
        planned_gpu_hours=12.0,
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


def _count_tokens_without_contact(text: str) -> int:
    """Fail-closed ASCII byte upper bound; it contacts no tokenizer."""

    return len(text.encode("utf-8"))


def _execute_speech_agent_workflows(*args: object, **kwargs: object) -> object:
    """Import openJiuwen only at the explicit runtime boundary."""

    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    return execute_speech_agent_workflows(*args, **kwargs)


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
        or jobs[0].get("input") != "complete final16 RESOLVE output manifest"
        or jobs[0].get("row_count") != 16
    ):
        raise RuntimeError("G6 scoring must be one complete final16 manifest job")
    return plan


@dataclass(frozen=True)
class RecoveryContact:
    """One hash-verified opaque request/response pair from the aborted source."""

    request_id: str
    sample_id: str
    contact_id: str
    packet_sha256: str
    payload_sha256: str
    response_sha256: str
    response_text_sha256: str
    response_text: str
    slot_id: int
    cost: Mapping[str, object]


@dataclass(frozen=True)
class RecoveryBundle:
    source_attempt_id: str
    source_attempt_sha256: str
    source_trace_path: Path
    source_trace_sha256: str
    contacts: Mapping[tuple[str, str], RecoveryContact]
    cost: Mapping[str, object]
    allow_resolve: bool = False


def _canonical_sha256(document: Mapping[str, object]) -> str:
    payload = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _load_recovery_bundle(root: Path, trace_path: Path) -> RecoveryBundle:
    """Load the eight prior responses as opaque hash-bound bytes."""

    trace_path = Path(trace_path)
    _require_hash(trace_path, RECOVERY_SOURCE_TRACE_SHA256, "recovery source trace")
    attempt_path = (
        Path(root)
        / "attempts"
        / RUN_ID
        / f"{RECOVERY_SOURCE_ATTEMPT_ID}.json"
    )
    _require_hash(
        attempt_path, RECOVERY_SOURCE_ATTEMPT_SHA256, "recovery source attempt"
    )
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    if (
        attempt.get("schema") != "saea-attempt-v1"
        or attempt.get("state") != "ABORTED"
        or attempt.get("run_id") != RUN_ID
        or attempt.get("attempt_id") != RECOVERY_SOURCE_ATTEMPT_ID
        or attempt.get("carrier_lock_key") != AUDIO2TOOL_LOCK_KEY
        or attempt.get("actual", {}).get("calls") != RECOVERY_PRIOR_CONTACTS
    ):
        raise RuntimeError("recovery source attempt identity or accounting drift")

    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != RECOVERY_PRIOR_CONTACTS * 3:
        raise RuntimeError("recovery trace must contain eight complete request triples")
    by_record = {row.get("record_id"): row for row in rows}
    if len(by_record) != len(rows):
        raise RuntimeError("recovery trace contains duplicate records")
    contacts: dict[tuple[str, str], RecoveryContact] = {}
    totals = {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
    }
    for (
        request_id,
        sample_id,
        contact_id,
        payload_sha256,
        response_sha256,
        response_text_sha256,
    ) in RECOVERY_EXPECTED_CONTACTS:
        request = by_record.get(f"{request_id}/request")
        response = by_record.get(f"{request_id}/response")
        cost_row = by_record.get(f"{request_id}/cost")
        if any(row is None for row in (request, response, cost_row)):
            raise RuntimeError("recovery trace is missing a source request triple")
        assert isinstance(request, Mapping)
        assert isinstance(response, Mapping)
        assert isinstance(cost_row, Mapping)
        if (
            request.get("channel") != "MODEL_REQUEST"
            or response.get("channel") != "MODEL_RESPONSE"
            or cost_row.get("channel") != "COST"
        ):
            raise RuntimeError("recovery trace channel drift")
        request_wrapper = request.get("payload")
        response_payload = response.get("payload")
        cost = cost_row.get("payload")
        if not all(
            isinstance(value, Mapping)
            for value in (request_wrapper, response_payload, cost)
        ):
            raise RuntimeError("recovery trace payload shape drift")
        assert isinstance(request_wrapper, Mapping)
        assert isinstance(response_payload, Mapping)
        assert isinstance(cost, Mapping)
        payload = request_wrapper.get("payload")
        if not isinstance(payload, Mapping):
            raise RuntimeError("recovery MODEL_REQUEST payload is malformed")
        history = payload.get("history")
        control = history[-1] if isinstance(history, list) and history else None
        text = response_payload.get("text")
        if (
            request_wrapper.get("arm") != "speech-feature-query"
            or request_wrapper.get("payload_sha256") != payload_sha256
            or _canonical_sha256(payload) != payload_sha256
            or payload.get("request_id") != request_id
            or payload.get("sample_id") != sample_id
            or payload.get("speech_packet_sha256") is None
            or not isinstance(control, Mapping)
            or control.get("contact_id") != contact_id
            or response_payload.get("response_sha256") != response_sha256
            or response_payload.get("response_text_sha256")
            != response_text_sha256
            or not isinstance(text, str)
            or hashlib.sha256(text.encode("utf-8")).hexdigest()
            != response_text_sha256
            or cost.get("calls") != 1
        ):
            raise RuntimeError("recovery request/response identity or hash drift")
        decoding = payload.get("decoding_params")
        slot_id = decoding.get("id_slot") if isinstance(decoding, Mapping) else None
        if slot_id not in range(SLOT_COUNT):
            raise RuntimeError("recovery source slot geometry drift")
        key = (sample_id, contact_id)
        if key in contacts:
            raise RuntimeError("recovery source repeats a sample/contact pair")
        contacts[key] = RecoveryContact(
            request_id=request_id,
            sample_id=sample_id,
            contact_id=contact_id,
            packet_sha256=str(payload["speech_packet_sha256"]),
            payload_sha256=payload_sha256,
            response_sha256=response_sha256,
            response_text_sha256=response_text_sha256,
            response_text=text,
            slot_id=int(slot_id),
            cost=dict(cost),
        )
        totals["calls_used"] += 1
        totals["audio_seconds_used"] += float(cost.get("audio_seconds", 0.0))
        totals["latency_seconds_total"] += float(cost.get("latency_seconds", 0.0))
        totals["prompt_tokens_total"] += int(cost.get("prompt_tokens", 0))
        totals["completion_tokens_total"] += int(cost.get("completion_tokens", 0))
    if set(by_record) != {
        f"{request_id}/{suffix}"
        for request_id, *_rest in RECOVERY_EXPECTED_CONTACTS
        for suffix in ("request", "response", "cost")
    }:
        raise RuntimeError("recovery trace contains an unexpected record")
    if abs(
        totals["audio_seconds_used"]
        - float(attempt.get("actual", {}).get("audio_seconds", -1))
    ) > 1e-6:
        raise RuntimeError("recovery source audio accounting drift")
    return RecoveryBundle(
        source_attempt_id=RECOVERY_SOURCE_ATTEMPT_ID,
        source_attempt_sha256=RECOVERY_SOURCE_ATTEMPT_SHA256,
        source_trace_path=trace_path,
        source_trace_sha256=RECOVERY_SOURCE_TRACE_SHA256,
        contacts=contacts,
        cost=totals,
    )


def _merge_recovery_cost(
    current: Mapping[str, object], recovery: RecoveryBundle | None
) -> dict[str, object]:
    merged = dict(current)
    if recovery is None:
        return merged
    for key in (
        "calls_used",
        "audio_seconds_used",
        "latency_seconds_total",
        "prompt_tokens_total",
        "completion_tokens_total",
    ):
        merged[key] = merged.get(key, 0) + recovery.cost.get(key, 0)
    return merged


def _load_seal_trace_bundle(root: Path, trace_path: Path) -> RecoveryBundle:
    """Validate the immutable 456-contact recovery trace without interpretation."""

    trace_path = Path(trace_path)
    _require_hash(trace_path, SEAL_SOURCE_TRACE_SHA256, "seal source trace")
    manifest_path = trace_path.with_name(f"{RUN_ID}.trace-manifest.json")
    _require_hash(
        manifest_path,
        SEAL_SOURCE_TRACE_MANIFEST_SHA256,
        "seal source trace manifest",
    )
    attempt_path = (
        Path(root) / "attempts" / RUN_ID / f"{SEAL_SOURCE_ATTEMPT_ID}.json"
    )
    _require_hash(attempt_path, SEAL_SOURCE_ATTEMPT_SHA256, "seal source attempt")
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    if (
        attempt.get("schema") != "saea-attempt-v1"
        or attempt.get("state") != "ABORTED"
        or attempt.get("run_id") != RUN_ID
        or attempt.get("attempt_id") != SEAL_SOURCE_ATTEMPT_ID
        or attempt.get("actual", {}).get("calls") != RECOVERY_CURRENT_CONTACTS
    ):
        raise RuntimeError("seal source attempt identity or accounting drift")
    rows = [
        json.loads(line)
        for line in trace_path.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(rows) != RECOVERY_CURRENT_CONTACTS * 3:
        raise RuntimeError("seal source must contain 456 request triples")
    by_record = {row.get("record_id"): row for row in rows}
    if len(by_record) != len(rows):
        raise RuntimeError("seal source contains duplicate records")
    request_ids = sorted(
        str(record_id).removesuffix("/request")
        for record_id, row in by_record.items()
        if isinstance(row, Mapping) and row.get("channel") == "MODEL_REQUEST"
    )
    if len(request_ids) != RECOVERY_CURRENT_CONTACTS:
        raise RuntimeError("seal source request count drift")
    contacts: dict[tuple[str, str], RecoveryContact] = {}
    totals = {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
    }
    for request_id in request_ids:
        request = by_record.get(f"{request_id}/request")
        response = by_record.get(f"{request_id}/response")
        cost_row = by_record.get(f"{request_id}/cost")
        if not all(isinstance(row, Mapping) for row in (request, response, cost_row)):
            raise RuntimeError("seal source has an incomplete request triple")
        assert isinstance(request, Mapping)
        assert isinstance(response, Mapping)
        assert isinstance(cost_row, Mapping)
        wrapper = request.get("payload")
        response_payload = response.get("payload")
        cost = cost_row.get("payload")
        if not all(
            isinstance(value, Mapping) for value in (wrapper, response_payload, cost)
        ):
            raise RuntimeError("seal source payload shape drift")
        assert isinstance(wrapper, Mapping)
        assert isinstance(response_payload, Mapping)
        assert isinstance(cost, Mapping)
        payload = wrapper.get("payload")
        history = payload.get("history") if isinstance(payload, Mapping) else None
        control = history[-1] if isinstance(history, list) and history else None
        text = response_payload.get("text")
        payload_hash = wrapper.get("payload_sha256")
        response_hash = response_payload.get("response_sha256")
        text_hash = response_payload.get("response_text_sha256")
        if (
            wrapper.get("arm") != "speech-feature-query"
            or not isinstance(payload, Mapping)
            or not isinstance(payload_hash, str)
            or _canonical_sha256(payload) != payload_hash
            or payload.get("request_id") != request_id
            or not isinstance(payload.get("sample_id"), str)
            or not isinstance(payload.get("speech_packet_sha256"), str)
            or not isinstance(control, Mapping)
            or not isinstance(control.get("contact_id"), str)
            or not isinstance(response_hash, str)
            or not isinstance(text_hash, str)
            or not isinstance(text, str)
            or hashlib.sha256(text.encode("utf-8")).hexdigest() != text_hash
            or cost.get("calls") != 1
            or response.get("channel") != "MODEL_RESPONSE"
            or cost_row.get("channel") != "COST"
        ):
            raise RuntimeError("seal source request/response hash or identity drift")
        decoding = payload.get("decoding_params")
        slot_id = decoding.get("id_slot") if isinstance(decoding, Mapping) else None
        if slot_id not in range(SLOT_COUNT):
            raise RuntimeError("seal source slot geometry drift")
        sample_id = str(payload["sample_id"])
        contact_id = str(control["contact_id"])
        key = (sample_id, contact_id)
        if key in contacts:
            raise RuntimeError("seal source repeats a sample/contact pair")
        contacts[key] = RecoveryContact(
            request_id=request_id,
            sample_id=sample_id,
            contact_id=contact_id,
            packet_sha256=str(payload["speech_packet_sha256"]),
            payload_sha256=payload_hash,
            response_sha256=response_hash,
            response_text_sha256=text_hash,
            response_text=text,
            slot_id=int(slot_id),
            cost=dict(cost),
        )
        totals["calls_used"] += 1
        totals["audio_seconds_used"] += float(cost.get("audio_seconds", 0.0))
        totals["latency_seconds_total"] += float(cost.get("latency_seconds", 0.0))
        totals["prompt_tokens_total"] += int(cost.get("prompt_tokens", 0))
        totals["completion_tokens_total"] += int(cost.get("completion_tokens", 0))
    if set(by_record) != {
        f"{request_id}/{suffix}"
        for request_id in request_ids
        for suffix in ("request", "response", "cost")
    }:
        raise RuntimeError("seal source contains an unexpected record")
    actual = attempt.get("actual", {})
    if abs(totals["audio_seconds_used"] - float(actual.get("audio_seconds", -1))) > 1e-6:
        raise RuntimeError("seal source audio accounting drift")
    return RecoveryBundle(
        source_attempt_id=SEAL_SOURCE_ATTEMPT_ID,
        source_attempt_sha256=SEAL_SOURCE_ATTEMPT_SHA256,
        source_trace_path=trace_path,
        source_trace_sha256=SEAL_SOURCE_TRACE_SHA256,
        contacts=contacts,
        cost=totals,
    )


def _static_preflight(root: Path) -> dict[str, object]:
    _require_bound_requirements()
    commit = require_clean_study_repo(REPO)
    for relpath, expected, label in (
        (BASELINE_CONFIG_RELPATH, BASELINE_CONFIG_SHA256, "baseline config"),
        (EXPERIMENT_CONFIG_RELPATH, EXPERIMENT_CONFIG_SHA256, "experiment config"),
        (INTEGRATION_RELPATH, INTEGRATION_SHA256, "G6 integration"),
        (SWEEP_RELPATH, SWEEP_SHA256, "G6 family sweep"),
        (RENDERER_RELPATH, RENDERER_SHA256, "G6 corpus renderer"),
        (CORPUS_RELPATH, COMMITTED_CORPUS_SHA256, "G5 frozen corpus"),
        (G1_RECEIPT_RELPATH, COMMITTED_G1_RECEIPT_SHA256, "G1 receipt"),
        (FIXED16_RECEIPT_RELPATH, COMMITTED_G6_ROSTER_SHA256, "G6 roster"),
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
        raise RuntimeError("G6 composed config identity drift")
    measured_protocol = protocol_hash(
        composed.config_hash, str(composed.values["arm"]), SELECTED_RUN_SHA256
    )
    if measured_protocol != PROTOCOL_SHA256:
        raise RuntimeError("G6 protocol identity drift")
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("openJiuwen version drift")
    if int(composed.values["profile_slot_count"]) != SLOT_COUNT:
        raise RuntimeError("G6 slot geometry drift")
    if int(composed.values["max_concurrent_model_requests"]) != MAX_CONCURRENT_REQUESTS:
        raise RuntimeError("G6 request concurrency drift")
    if int(composed.values["queue_depth"]) != QUEUE_DEPTH:
        raise RuntimeError("G6 queue depth drift")
    if "-np" not in composed.values["server_args"]:
        raise RuntimeError("G6 server geometry does not declare parallel slots")

    surface = load_g6_runtime_surface(
        g1_receipt_path=REPO / G1_RECEIPT_RELPATH,
        g6_roster_path=REPO / FIXED16_RECEIPT_RELPATH,
        promotion_receipt_path=PROMOTION_RECEIPT,
        expected_g1_sha256=COMMITTED_G1_RECEIPT_SHA256,
        expected_g6_roster_sha256=COMMITTED_G6_ROSTER_SHA256,
        expected_promotion_sha256=COMMITTED_G1_PROMOTION_SHA256,
    )
    if surface.split_identity_hash != SELECTED_SPLIT_SHA256:
        raise RuntimeError("G6 partition identity drift")
    _validate_selected_ids(
        {
            sample.sample_id: sample.sample_id.split(":", 1)[0]
            for sample in surface.samples
        }
    )
    if abs(sum(sample.audio_seconds for sample in surface.samples) - SELECTED_AUDIO_SECONDS) > 1e-6:
        raise RuntimeError("G6 fixed16 audio duration drift")

    adapter = G6CorpusAdapter.from_path(REPO / CORPUS_RELPATH)
    if len(adapter.family_bundles) != FAMILY_COUNT:
        raise RuntimeError("G6 integration does not expose all 28 families")
    if G6_MAX_FINAL_CALLS < 1:
        raise RuntimeError("G6 final call bound is invalid")
    prompt_report = build_prompt_fit_report(
        adapter=adapter,
        runtime=surface,
        task_contract=TASK_CONTRACT,
        token_counter=_count_tokens_without_contact,
        render_request=lambda contact: _render_request(
            _messages_for_context(contact), contact
        ),
    )
    if prompt_report.get("status") != "PASS":
        raise RuntimeError("G6 SCAN prompt-fit reconstruction failed")
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
        "adapter": adapter,
        "prompt_report": prompt_report,
        "runtime_receipt": runtime_document,
        "selected_ids": SELECTED_IDS,
    }


@dataclass(frozen=True)
class G6ContactRecord:
    sample_id: str
    contact_id: str
    stage: str
    family_tag: str | None
    slot_id: int
    response_sha256: str
    envelope: object
    recovered: bool = False
    source_request_id: str | None = None
    source_payload_sha256: str | None = None
    source_response_sha256: str | None = None

    def as_json(self) -> dict[str, object]:
        return {
            "sample_id": self.sample_id,
            "contact_id": self.contact_id,
            "stage": self.stage,
            "family_tag": self.family_tag,
            "slot_id": self.slot_id,
            "response_sha256": self.response_sha256,
            "prompt_envelope": _envelope_json(self.envelope),
            "recovered": self.recovered,
            "source_request_id": self.source_request_id,
            "source_payload_sha256": self.source_payload_sha256,
            "source_response_sha256": self.source_response_sha256,
        }


@dataclass
class _G6WorkflowState:
    sample: object
    sweep: object
    packet_binding: Mapping[str, object]
    speech_feature_tokens: int
    stage: str = "SCAN"
    current_contexts: tuple[object, ...] = ()
    contacts: list[G6ContactRecord] = field(default_factory=list)
    reports: tuple[object, ...] = ()
    resolve_context: object | None = None
    resolution: object | None = None
    raw_final_response_text: str = ""
    final_response_text: str = ""
    trace_documents: Mapping[str, Mapping[str, object]] | None = None
    pending_metadata: dict[str, Mapping[str, object]] = field(default_factory=dict)


@dataclass(frozen=True)
class G6SampleResult:
    sample_id: str
    contacts: tuple[G6ContactRecord, ...]
    reports: tuple[FamilyScanReport, ...]
    resolve_context: ContactContext
    resolution: ParsedResolution
    raw_final_response_text: str
    final_response_text: str
    trace_documents: Mapping[str, Mapping[str, object]]


@dataclass(frozen=True)
class G6RunSummary:
    run_id: str
    protocol_hash: str
    controller_policy_id: str
    agent_executor_id: str
    results: tuple[G6SampleResult, ...]


def _envelope_json(envelope: object) -> dict[str, object]:
    if isinstance(envelope, Mapping):
        return dict(envelope)
    return {
        key: getattr(envelope, key)
        for key in (
            "contact_id",
            "rendered_request_sha256",
            "text_tokens",
            "speech_feature_tokens",
            "special_token_reserve",
            "completion_token_ceiling",
            "total_tokens",
            "remaining_tokens",
        )
    }


def _messages_for_context(context: object) -> tuple[Mapping[str, object], ...]:
    system_text = f"{context.task_contract}\n\n{context.instruction}"
    content: list[Mapping[str, object]] = [
        {
            "type": "input_speech_features",
            "speech_features": {
                "packet_id": context.speech_packet_id,
                "sha256": context.speech_packet_sha256,
                "role": "query",
            },
        }
    ]
    if context.report_jsons:
        content.append(
            {
                "type": "text",
                "text": "VALIDATED FAMILY REPORTS:\n" + "\n".join(context.report_jsons),
                "evidence_id": "g6:validated-family-reports",
                "source_uri": "g6-runtime://validated-family-reports",
                "knowledge_role": "key",
            }
        )
    if context.contracts:
        family = context.family_tag or "resolve-nominations"
        content.append(
            {
                "type": "text",
                "text": "EXACT VISIBLE CONTRACTS:\n"
                + "\n".join(contract.render() for contract in context.contracts),
                "evidence_id": f"g6:contracts:{family}",
                "source_uri": f"g6-corpus://{family}",
                "knowledge_role": "value",
            }
        )
    return (
        {"role": "system", "content": system_text},
        {"role": "user", "content": content},
    )


def _render_request(
    messages: Sequence[Mapping[str, object]], context: object
) -> str:
    """Canonical upper-bound surface including FrozenCoreClient control history."""

    return json.dumps(
        {
            "messages": messages,
            "agent_control": {
                "contact_id": context.contact_id,
                "instruction": context.instruction,
            },
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _emit_phase_traces(state: _G6WorkflowState, trace_sink: object) -> None:
    assert state.trace_documents is not None
    for phase in ("OBS", "ORG", "SUPPLY", "USE"):
        prefix = phase.lower() + "_"
        trace_sink.emit(
            phase,
            f"g6:{state.sample.sample_id}:{phase.lower()}",
            {
                f"{prefix}{key}": value
                for key, value in state.trace_documents[phase].items()
            },
        )


def _run_phase(
    *,
    root: Path,
    plan: object,
    adapter: object,
    client: object,
    surface: object,
    trace_sink: object,
    workflow_runner: Callable[..., object] = _execute_speech_agent_workflows,
    token_counter: Callable[[str], int] = _count_tokens_without_contact,
    prompt_fit_measurer: Callable[..., Mapping[str, object]] = measure_contact_prompt_fit,
    recovery: RecoveryBundle | None = None,
) -> G6RunSummary:
    del root
    samples = tuple(sorted(surface.samples, key=lambda item: item.sample_id))
    sample_ids = tuple(sample.sample_id for sample in samples)
    if sample_ids != SELECTED_IDS:
        raise RuntimeError("G6 runtime sample identity surface drift")
    if set(surface.packet_bindings) != set(sample_ids):
        raise RuntimeError("G6 packet identity surface drift")
    if set(surface.speech_feature_tokens_by_sample) != set(sample_ids):
        raise RuntimeError("G6 speech-token identity surface drift")
    states = [
        _G6WorkflowState(
            sample=sample,
            sweep=adapter.build_sweep(),
            packet_binding=surface.packet_bindings[sample.sample_id],
            speech_feature_tokens=surface.speech_feature_tokens_by_sample[
                sample.sample_id
            ],
        )
        for sample in samples
    ]
    recovered_used: set[tuple[str, str]] = set()
    recovery_lock = threading.Lock()

    def prepare_wave(state: _G6WorkflowState, session: object) -> int:
        if state.stage == "SCAN":
            state.current_contexts = tuple(
                state.sweep.build_scan_contexts(
                    speech_packet_id=str(state.packet_binding["packet_id"]),
                    speech_packet_sha256=str(state.packet_binding["sha256"]),
                    task_contract=TASK_CONTRACT,
                )
            )
            if len(state.current_contexts) != SCAN_CONTACTS:
                raise RuntimeError("G6 must prospectively schedule all 28 SCANs")
        elif state.stage == "RESOLVE":
            if state.resolve_context is None or len(state.reports) != SCAN_CONTACTS:
                raise RuntimeError("G6 RESOLVE requires all 28 sealed reports")
            state.current_contexts = (state.resolve_context,)
        else:
            state.current_contexts = ()
        update = getattr(session, "update_global_state", None)
        if callable(update):
            update(
                {
                    "g6_stage": state.stage,
                    "g6_sample_id": state.sample.sample_id,
                    "g6_active_contacts": [
                        context.contact_id for context in state.current_contexts
                    ],
                    "g6_scan_reports_sealed": len(state.reports),
                }
            )
        return len(state.current_contexts)

    def invoke_contact(
        state: _G6WorkflowState, branch_index: int, slot_id: int
    ) -> Mapping[str, object]:
        context = state.current_contexts[branch_index]
        messages = _messages_for_context(context)
        envelope = prompt_fit_measurer(
            context=context,
            rendered_request=_render_request(messages, context),
            runtime=surface,
            sample_id=state.sample.sample_id,
            token_counter=token_counter,
        )
        if envelope.get("refuse_contact") is not False or envelope.get("status") != "PASS":
            raise RuntimeError(
                f"G6 {context.stage} prompt does not preserve required headroom"
            )
        recovery_key = (state.sample.sample_id, context.contact_id)
        source = recovery.contacts.get(recovery_key) if recovery is not None else None
        if source is not None:
            if (
                (context.stage != "SCAN" and not recovery.allow_resolve)
                or source.packet_sha256 != context.speech_packet_sha256
                or source.sample_id != state.sample.sample_id
                or source.contact_id != context.contact_id
            ):
                raise RuntimeError("recovery contact disagrees with current G6 context")
            with recovery_lock:
                if recovery_key in recovered_used:
                    raise RuntimeError("recovery contact was reused more than once")
                recovered_used.add(recovery_key)
            response_text = source.response_text
            response_slot_id = source.slot_id
            metadata = {
                "envelope": envelope,
                "recovered": True,
                "source_request_id": source.request_id,
                "source_payload_sha256": source.payload_sha256,
                "source_response_sha256": source.response_sha256,
            }
        else:
            response_text = client.complete(
                messages,
                decoding_params={
                    "max_tokens": context.completion_token_ceiling,
                    "temperature": TEMPERATURE,
                    "id_slot": slot_id,
                },
                speech_feature_sample_id=state.sample.sample_id,
                key_representation_id=f"{CONTROLLER_POLICY_ID}:{context.stage.lower()}",
                matcher_policy_id=CONTROLLER_POLICY_ID,
                agent_state=(),
                agent_contact_id=context.contact_id,
                contact_instruction=context.instruction,
            )
            response_slot_id = slot_id
            metadata = {
                "envelope": envelope,
                "recovered": False,
                "source_request_id": None,
                "source_payload_sha256": None,
                "source_response_sha256": None,
            }
        if not isinstance(response_text, str):
            raise RuntimeError("G6 frozen core response must be text")
        state.pending_metadata[context.contact_id] = metadata
        return {
            "response_text": response_text,
            "slot_id": response_slot_id,
            "response_sha256": hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
        }

    def aggregate_wave(
        state: _G6WorkflowState,
        responses: tuple[Mapping[str, object], ...],
        session: object,
    ) -> None:
        del session
        if len(responses) != len(state.current_contexts):
            raise RuntimeError("G6 fan-in changed the scheduled contact count")
        for context, response in zip(state.current_contexts, responses, strict=True):
            response_text = response.get("response_text")
            if not isinstance(response_text, str):
                raise RuntimeError("G6 fan-in returned malformed response text")
            if response.get("response_sha256") != hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest():
                raise RuntimeError("G6 fan-in response hash mismatch")
            metadata = state.pending_metadata.pop(context.contact_id, None)
            if metadata is None:
                raise RuntimeError("G6 contact metadata was not retained in state")
            state.contacts.append(
                G6ContactRecord(
                    sample_id=state.sample.sample_id,
                    contact_id=context.contact_id,
                    stage=context.stage,
                    family_tag=context.family_tag,
                    slot_id=int(response["slot_id"]),
                    response_sha256=str(response["response_sha256"]),
                    envelope=metadata["envelope"],
                    recovered=bool(metadata["recovered"]),
                    source_request_id=metadata["source_request_id"],
                    source_payload_sha256=metadata["source_payload_sha256"],
                    source_response_sha256=metadata["source_response_sha256"],
                )
            )
        if state.stage == "SCAN":
            by_family = {
                str(context.family_tag): response["response_text"]
                for context, response in zip(
                    state.current_contexts, responses, strict=True
                )
            }
            state.reports = tuple(state.sweep.parse_scan_responses(by_family))
            if len(state.reports) != SCAN_CONTACTS:
                raise RuntimeError("G6 parser did not seal all 28 SCAN reports")
            state.resolve_context = state.sweep.build_resolve_context(
                speech_packet_id=str(state.packet_binding["packet_id"]),
                speech_packet_sha256=str(state.packet_binding["sha256"]),
                task_contract=TASK_CONTRACT,
                reports=state.reports,
            )
            state.stage = "RESOLVE"
            return
        if state.stage != "RESOLVE" or len(responses) != 1:
            raise RuntimeError("G6 received a contact outside SCAN then RESOLVE")
        raw = str(responses[0]["response_text"])
        state.raw_final_response_text = raw
        state.resolution = state.sweep.parse_resolve_response(
            raw, reports=state.reports
        )
        state.final_response_text = state.resolution.canonical_json
        state.trace_documents = build_trace_documents(
            scan_contact_ids=tuple(
                contact.contact_id for contact in state.contacts[:SCAN_CONTACTS]
            ),
            resolve_context=state.resolve_context,
            reports=state.reports,
            resolution=state.resolution,
            final_response_text=raw,
        )
        state.stage = "DONE"

    completed = workflow_runner(
        states,
        prepare_wave=prepare_wave,
        invoke_contact=invoke_contact,
        aggregate_wave=aggregate_wave,
        should_continue=lambda state: state.stage != "DONE",
        branch_count=SCAN_CONTACTS,
        slot_count=SLOT_COUNT,
        queue_depth=QUEUE_DEPTH,
        workflow_timeout_seconds=WORKFLOW_TIMEOUT_SECONDS,
    )
    if list(completed) != states:
        raise RuntimeError("G6 OpenJiuwen workflow changed state identity or order")
    if sum(len(state.contacts) for state in states) != MAX_TOTAL_CONTACTS:
        raise RuntimeError("G6 must complete exactly 464 contacts")
    expected_recovery_keys = set(recovery.contacts) if recovery is not None else set()
    if recovered_used != expected_recovery_keys:
        raise RuntimeError("G6 recovery did not consume every source contact exactly once")
    results: list[G6SampleResult] = []
    for state in states:
        contact_ids = tuple(contact.contact_id for contact in state.contacts)
        if (
            len(contact_ids) != MAX_CONTACTS
            or len(set(contact_ids)) != MAX_CONTACTS
            or any(
                not contact_id.startswith(SCAN_CONTACT_PREFIX)
                for contact_id in contact_ids[:SCAN_CONTACTS]
            )
            or contact_ids[-1] != RESOLVE_CONTACT_ID
            or state.resolution is None
            or state.resolve_context is None
            or state.trace_documents is None
        ):
            raise RuntimeError("G6 row is not exactly 28 SCAN then one RESOLVE")
        _emit_phase_traces(state, trace_sink)
        results.append(
            G6SampleResult(
                sample_id=state.sample.sample_id,
                contacts=tuple(state.contacts),
                reports=tuple(state.reports),
                resolve_context=state.resolve_context,
                resolution=state.resolution,
                raw_final_response_text=state.raw_final_response_text,
                final_response_text=state.final_response_text,
                trace_documents=state.trace_documents,
            )
        )
    return G6RunSummary(
        run_id=RUN_ID,
        protocol_hash=str(plan.protocol_hash),
        controller_policy_id=CONTROLLER_POLICY_ID,
        agent_executor_id="openjiuwen-workflow-v1",
        results=tuple(results),
    )


def _scan_state_rows(summary: object) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for result in sorted(summary.results, key=lambda item: item.sample_id):
        if len(result.reports) != SCAN_CONTACTS:
            raise RuntimeError("G6 scan seal requires exactly 28 reports per sample")
        for contact, report in zip(
            result.contacts[:SCAN_CONTACTS], result.reports, strict=True
        ):
            rows.append(
                {
                    "sample_id": result.sample_id,
                    "nonfinal": True,
                    "stage": "SCAN",
                    "contact": contact.as_json(),
                    "report": {
                        "family_tag": report.family_tag,
                        "valid": report.valid,
                        "status": report.status,
                        "canonical_json": report.canonical_json,
                    },
                }
            )
    return rows


def _final_resolve_texts(summary: object) -> dict[str, str]:
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
    recovery: RecoveryBundle | None = None,
) -> dict[str, object]:
    scan_states = run_dir / "g6-scan-states.jsonl"
    _write_jsonl(scan_states, _scan_state_rows(summary))
    scan_manifest = run_dir / "g6-scan-contact-manifest.json"
    _write_json(
        scan_manifest,
        {
            "schema": "saea-a2t-g6-scan-contact-manifest-v1",
            "run_id": RUN_ID,
            "sample_count": 16,
            "row_count": 16 * SCAN_CONTACTS,
            "contacts_per_sample": SCAN_CONTACTS,
            "nonfinal": True,
            "rows_path": str(scan_states),
            "rows_sha256": _sha256_file(scan_states),
            "recovery_source": (
                None
                if recovery is None
                else {
                    "attempt_id": recovery.source_attempt_id,
                    "attempt_sha256": recovery.source_attempt_sha256,
                    "trace_path": str(recovery.source_trace_path),
                    "trace_sha256": recovery.source_trace_sha256,
                    "reused_contact_count": len(recovery.contacts),
                }
            ),
        },
    )
    trace_path = run_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
    texts = _final_resolve_texts(summary)
    source_by_id = {
        sample_id: {
            "action": RESOLVE_CONTACT_ID,
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
        raise RuntimeError("G6 final bundle is not complete final16")
    return {
        "scan_states": scan_states,
        "scan_states_sha256": _sha256_file(scan_states),
        "scan_contact_manifest": scan_manifest,
        "scan_contact_manifest_sha256": _sha256_file(scan_manifest),
        "outputs": outputs,
        "outputs_sha256": _sha256_file(outputs),
        "manifest": manifest,
        "manifest_sha256": _sha256_file(manifest),
        "agent_trace_manifest_sha256": agent_trace_hash,
        "output_trace_manifest_sha256": output_trace_hash,
    }


def _execute_model_free_workflows(states: Sequence[object], **kwargs: object) -> list[object]:
    """Execute callback state transitions synchronously with no OpenJiuwen import."""

    prepare_wave = kwargs["prepare_wave"]
    invoke_contact = kwargs["invoke_contact"]
    aggregate_wave = kwargs["aggregate_wave"]
    should_continue = kwargs["should_continue"]
    assert callable(prepare_wave)
    assert callable(invoke_contact)
    assert callable(aggregate_wave)
    assert callable(should_continue)
    for state in states:
        while should_continue(state):
            active = prepare_wave(state, object())
            responses = tuple(
                invoke_contact(state, branch_index, 0)
                for branch_index in range(active)
            )
            if any(
                set(response)
                != {"response_text", "slot_id", "response_sha256"}
                for response in responses
            ):
                raise RuntimeError("model-free reconstruction callback shape drift")
            aggregate_wave(state, responses, object())
    return list(states)


class _NoContactClient:
    def complete(self, *args: object, **kwargs: object) -> str:
        del args, kwargs
        raise RuntimeError("model contact is prohibited during source-bound sealing")


def _seal_from(
    root: Path, *, first_trace_path: Path, latest_trace_path: Path
) -> Mapping[str, object]:
    """Reconstruct and externally seal all 464 already-consumed contacts."""

    context = _static_preflight(root)
    first = _load_recovery_bundle(root, first_trace_path)
    latest = _load_seal_trace_bundle(root, latest_trace_path)
    overlap = set(first.contacts) & set(latest.contacts)
    combined_contacts = {**first.contacts, **latest.contacts}
    if overlap or len(combined_contacts) != MAX_TOTAL_CONTACTS:
        raise RuntimeError("source traces do not form one disjoint 464-contact surface")
    combined_cost = _merge_recovery_cost(latest.cost, first)
    combined = RecoveryBundle(
        source_attempt_id=f"{first.source_attempt_id}+{latest.source_attempt_id}",
        source_attempt_sha256=hashlib.sha256(
            (first.source_attempt_sha256 + latest.source_attempt_sha256).encode("ascii")
        ).hexdigest(),
        source_trace_path=latest.source_trace_path,
        source_trace_sha256=hashlib.sha256(
            (first.source_trace_sha256 + latest.source_trace_sha256).encode("ascii")
        ).hexdigest(),
        contacts=combined_contacts,
        cost=combined_cost,
        allow_resolve=True,
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-seal-{stamp}"
    run_dir = mission_dir / "g6-seal"
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_json(run_dir / "official-score-plan.json", OFFICIAL_SCORE_PLAN)
    source_binding = {
        "schema": "saea-a2t-g6-source-bound-plan-v1",
        "run_id": RUN_ID,
        "protocol_hash": PROTOCOL_SHA256,
        "split_identity_hash": SELECTED_RUN_SHA256,
        "model_contacts_already_consumed": MAX_TOTAL_CONTACTS,
        "new_model_contacts": 0,
        "sources": [
            {
                "attempt_id": first.source_attempt_id,
                "attempt_sha256": first.source_attempt_sha256,
                "trace_path": str(first.source_trace_path),
                "trace_sha256": first.source_trace_sha256,
                "contact_count": len(first.contacts),
            },
            {
                "attempt_id": latest.source_attempt_id,
                "attempt_sha256": latest.source_attempt_sha256,
                "trace_path": str(latest.source_trace_path),
                "trace_sha256": latest.source_trace_sha256,
                "trace_manifest_sha256": SEAL_SOURCE_TRACE_MANIFEST_SHA256,
                "contact_count": len(latest.contacts),
            },
        ],
    }
    _write_json(run_dir / "source-bound-plan.json", source_binding)
    agent_sink = TraceSink(run_dir / "agent-trace", RUN_ID)
    summary = _run_phase(
        root=root,
        plan=type("Plan", (), {"protocol_hash": PROTOCOL_SHA256})(),
        adapter=context["adapter"],
        client=_NoContactClient(),
        surface=context["surface"],
        trace_sink=agent_sink,
        workflow_runner=_execute_model_free_workflows,
        recovery=combined,
    )
    agent_trace_manifest_sha256 = agent_sink.close()
    scan_states = run_dir / "g6-scan-states.jsonl"
    _write_jsonl(scan_states, _scan_state_rows(summary))
    agent_trace_path = run_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
    texts = _final_resolve_texts(summary)
    source_by_id = {
        sample_id: {
            "action": RESOLVE_CONTACT_ID,
            "source_agent_trace_manifest_sha256": agent_trace_manifest_sha256,
            "source_artifact_path": str(agent_trace_path),
            "source_artifact_sha256": _sha256_file(agent_trace_path),
        }
        for sample_id in SELECTED_IDS
    }
    output_sink = TraceSink(run_dir, RUN_ID)
    output_rows = emit_composite_rows(
        texts=texts,
        source_by_id=source_by_id,
        sink=output_sink,
        variant="main",
    )
    output_trace_manifest_sha256 = output_sink.close()
    outputs_path = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs_path, output_rows)
    output_trace_path = run_dir / f"{RUN_ID}.trace.jsonl"
    output_trace_manifest_path = run_dir / f"{RUN_ID}.trace-manifest.json"
    external_manifest_path = run_dir / "g6-external-complete-manifest.json"
    external_manifest = {
        "schema": "saea-a2t-g6-external-complete-manifest-v1",
        "status": "EXTERNALLY_SEALED_COMPLETE_UNSCORED",
        "formal_verify_bundle": {
            "achievable": False,
            "reasons": ["source_attempts_aborted_after_all_model_contacts"],
        },
        "run_id": RUN_ID,
        "study_commit": context["commit"],
        "protocol_hash": PROTOCOL_SHA256,
        "split": {
            "name": SPLIT_ID,
            "role": "discovery",
            "identity_hash": SELECTED_RUN_SHA256,
            "ids": list(SELECTED_IDS),
            "count": len(SELECTED_IDS),
        },
        "contacts": {
            "scan": len(SELECTED_IDS) * SCAN_CONTACTS,
            "resolve": len(SELECTED_IDS),
            "total": MAX_TOTAL_CONTACTS,
            "new": 0,
        },
        "cost": combined_cost,
        "source_binding": source_binding,
        "artifacts": {
            "scan_states": {
                "path": str(scan_states),
                "sha256": _sha256_file(scan_states),
            },
            "agent_trace": {
                "path": str(agent_trace_path),
                "sha256": _sha256_file(agent_trace_path),
                "manifest_sha256": agent_trace_manifest_sha256,
            },
            "outputs": {
                "path": str(outputs_path),
                "sha256": _sha256_file(outputs_path),
                "row_count": len(output_rows),
            },
            "output_trace": {
                "path": str(output_trace_path),
                "sha256": _sha256_file(output_trace_path),
                "manifest_path": str(output_trace_manifest_path),
                "manifest_sha256": output_trace_manifest_sha256,
            },
        },
        "contacts_during_seal": {
            "model": 0,
            "network": 0,
            "retriever": 0,
            "tokenizer": 0,
            "scorer": 0,
            "gold": 0,
        },
    }
    _write_json(external_manifest_path, external_manifest)
    receipt = {
        "schema": "saea-a2t-g6-external-source-bound-seal-v1",
        "status": "SEALED_UNSCORED",
        "run_id": RUN_ID,
        "mission_dir": str(mission_dir),
        "external_manifest": str(external_manifest_path),
        "external_manifest_sha256": _sha256_file(external_manifest_path),
        "outputs": str(outputs_path),
        "outputs_sha256": _sha256_file(outputs_path),
        "model_contacts": 0,
        "scorer_contacts": 0,
        "gold_contacts": 0,
    }
    _write_json(mission_dir / "seal-receipt.json", receipt)
    return receipt


def _launch(
    root: Path, *, recovery_trace_path: Path | None = None
) -> Mapping[str, object]:
    context = _static_preflight(root)
    recovery = (
        None
        if recovery_trace_path is None
        else _load_recovery_bundle(root, recovery_trace_path)
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt_id = f"attempt-{stamp.lower()}-g6-fixed16"
    plan = _execution_plan(attempt_id)
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}"
    run_dir = mission_dir / "g6"
    service_dir = mission_dir / "service"
    run_dir.mkdir(parents=True, exist_ok=False)
    service_dir.mkdir()
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    _write_json(run_dir / "official-score-plan.json", OFFICIAL_SCORE_PLAN)
    _write_json(run_dir / "precontact-scan-prompt-fit.json", context["prompt_report"])

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
        raise RuntimeError("G6 decoder must use an explicit loopback port")
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
            request_id_prefix="g6fixed16r" if recovery is not None else "g6fixed16",
            speech_feature_root=FEATURE_ROOT,
            speech_packet_bindings=surface.packet_bindings,
        )
        trace_sink = TraceSink(run_dir / "agent-trace", RUN_ID)
        summary = _run_phase(
            root=root,
            plan=plan,
            adapter=context["adapter"],
            client=client,
            surface=surface,
            trace_sink=trace_sink,
            recovery=recovery,
        )
        agent_trace_hash = trace_sink.close()
        trace_sink = None
        client_summary = client.close()
        client = None
        expected_current = (
            RECOVERY_CURRENT_CONTACTS if recovery is not None else MAX_TOTAL_CONTACTS
        )
        if client_summary.get("request_count") != expected_current:
            raise RuntimeError(
                f"G6 transport did not record exactly {expected_current} current requests"
            )
        client_summary = dict(client_summary)
        client_summary["cost"] = _merge_recovery_cost(
            client_summary["cost"], recovery
        )
        client_summary["request_count_total"] = expected_current + (
            len(recovery.contacts) if recovery is not None else 0
        )
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
            recovery=recovery,
        )
        receipt = {
            "schema": "saea-a2t-g6-exhaustive-family-sweep-fixed16-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SEALED_UNSCORED",
            "study_commit": context["commit"],
            "attempt_id": attempt_id,
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "model_contacts": MAX_TOTAL_CONTACTS,
            "prior_reused_model_contacts": (
                len(recovery.contacts) if recovery is not None else 0
            ),
            "current_model_contacts": expected_current,
            "scan_contacts": 16 * SCAN_CONTACTS,
            "resolve_contacts": 16,
            "repair_contacts": REPAIR_CONTACTS,
            "retries": RETRIES,
            "resends": RESENDS,
            "network_jitter_testing": JITTER_TESTING,
            "slot_count": SLOT_COUNT,
            "max_concurrent_model_requests": MAX_CONCURRENT_REQUESTS,
            "queue_depth": QUEUE_DEPTH,
            "scorer_contacts": 0,
            "recovery_source": (
                None
                if recovery is None
                else {
                    "attempt_id": recovery.source_attempt_id,
                    "attempt_sha256": recovery.source_attempt_sha256,
                    "trace_path": str(recovery.source_trace_path),
                    "trace_sha256": recovery.source_trace_sha256,
                }
            ),
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
    mode.add_argument("--recover-from", type=Path)
    mode.add_argument(
        "--seal-from",
        nargs=2,
        type=Path,
        metavar=("FIRST8_TRACE", "LATEST456_TRACE"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = data_root()
    if args.preflight_only:
        context = _static_preflight(root)
        prompt_report = context["prompt_report"]
        scan_report = prompt_report["scan"]
        family_maxima = scan_report.get("family_maxima", {})
        scan_maximum = scan_report.get("maximum_envelope_tokens")
        if scan_maximum is None and isinstance(family_maxima, Mapping):
            scan_maximum = max(
                (int(row["total_tokens"]) for row in family_maxima.values()),
                default=0,
            )
        print(
            json.dumps(
                {
                    "run_id": RUN_ID,
                    "preflight": "passed",
                    "study_commit": context["commit"],
                    "samples": len(context["selected_ids"]),
                    "planned_model_calls": MAX_TOTAL_CONTACTS,
                    "scan_maximum_envelope_tokens": scan_maximum,
                    "resolve_prompt_fit_precomputed": prompt_report["resolve"].get(
                        "precomputed", False
                    ),
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
    if args.seal_from is not None:
        first_trace, latest_trace = args.seal_from
        result = _seal_from(
            root,
            first_trace_path=first_trace,
            latest_trace_path=latest_trace,
        )
        print(json.dumps(result, ensure_ascii=True, sort_keys=True, default=str))
        return 0
    result = (
        _launch(root, recovery_trace_path=args.recover_from)
        if args.recover_from is not None
        else _launch(root)
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
