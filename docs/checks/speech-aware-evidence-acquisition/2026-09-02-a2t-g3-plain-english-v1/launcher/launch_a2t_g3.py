"""Run the frozen 40-sample Audio2Tool G3 plain-English AgentLoop pilot."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Mapping, Sequence
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.analysis.bootstrap import (  # noqa: E402
    paired_cluster_bootstrap,
)
from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
    TraceRecord,
)
from speech_aware_evidence_acquisition.core.base import (  # noqa: E402
    TRANSPORTS,
    RunResult,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    ATTEMPT_STATE_NEVER_OPENED,
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import (  # noqa: E402
    compose,
    d1_media_supplement_relpath,
    d1_media_supplement_sha256,
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
from speech_aware_evidence_acquisition.rails.probes import (  # noqa: E402
    a2t_g3_plain_english_flight as g3_flight,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_contract_preserving_cascade_flight import (  # noqa: E402
    DirectPhaseResult,
    DirectPhaseSummary,
    run_direct_phase,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_bundle import (  # noqa: E402
    build_resend_composite_texts,
)
from speech_aware_evidence_acquisition.reproduction.a2t_scorer import (  # noqa: E402
    score_audio2tool_outputs,
)


RUN_ID = "SAEA-A2T-G3-PLAIN-ENGLISH-V1"
RUNTIME_ROOT = Path("/home/chao")
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g3-pilot-40"
BASELINE_FRAGMENT = "a2t-g3-plain-english-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g3-plain-english-v1"

COMPOSED_CONFIG_SHA256 = (
    "f258c7deb56653055883b69fef4b5263c3b8b664242e014bbd0f97978e109520"
)
PROTOCOL_SHA256 = (
    "748492b23e571dd05e5ab2ae09aa55759c5d9a2628d9f43d4e4ab949e4f86155"
)
RUN_IDENTITY_SHA256 = (
    "3b25dfe3b850ab83ec72a62e2972e882e0e5c386c3bf00c798cc75460da3d614"
)
SPLIT_IDENTITY_SHA256 = (
    "7d170a0e333be385a99ecd35012de5c8e38f98c99304442d01145ed8fe6a1aaf"
)
SPLIT_COUNT = 40
PACKET_UTF8_BYTE_CAP = 64_000

G3_M0_DIRECT_PHASE = g3_flight.G3_M0_DIRECT_PHASE
G3_OBSERVATION_PHASE = g3_flight.G3_OBSERVATION_PHASE
G3_MATCHED_USE_PHASE = g3_flight.G3_MATCHED_USE_PHASE
G3_SHUFFLED_USE_PHASE = g3_flight.G3_SHUFFLED_USE_PHASE
PHASES = (
    G3_M0_DIRECT_PHASE,
    G3_OBSERVATION_PHASE,
    G3_MATCHED_USE_PHASE,
    G3_SHUFFLED_USE_PHASE,
)
PHASE_SUFFIXES = {
    G3_M0_DIRECT_PHASE: "m0",
    G3_OBSERVATION_PHASE: "obs",
    G3_MATCHED_USE_PHASE: "matched",
    G3_SHUFFLED_USE_PHASE: "shuffled",
}
PHASE_CONTACT_CEILINGS = {
    G3_M0_DIRECT_PHASE: 40,
    G3_OBSERVATION_PHASE: 40,
    G3_MATCHED_USE_PHASE: 80,
    G3_SHUFFLED_USE_PHASE: 32,
}
CANONICAL_TIERS = (
    "tier1_direct",
    "tier2_parametric",
    "tier3_multi_intent",
    "tier4_implicit",
    "tier5_needle",
    "tier6_correction",
    "tier7_multiturn",
    "tier8_intent_blending",
)

ROSTER_RELPATH = Path("docs/receipts/a2t/A2T-G3-PILOT-40.json")
ROSTER_SHA256 = (
    "179535049414fa0e9747075db84e8ced3fbc60001955be25a75e9d70a4ba7e92"
)
MEDIA_RELPATH = Path(
    "derived/audio2tool/a2t-g3-human-hierarchical-pilot-v1/pilot-media.json"
)
MEDIA_SHA256 = (
    "72cc6b1a1cc320b425414d178cfaeff81ef2aaf4b7d1dbc40721bb513cd2e271"
)
BINDING_MAP = Path(
    "/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/"
    "A2T-G3-OBS-40-bindings.json"
)
BINDING_SHA256 = (
    "0bfddebabe6582e0a075da55073a992ba57459d690460c6048c0edc2f7b11043"
)
PROMOTION_RECEIPT = Path(
    "/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/"
    "A2T-G3-OBS-40-promotion.json"
)
PROMOTION_SHA256 = (
    "77b1b8675aabd65423014a7e6c11a17047ad8d45f4dfcd8e311b57622516a37a"
)
CARD_BUILD_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g3-plain-english-cards-build/build-receipt.json"
)
CARD_BUILD_SHA256 = (
    "3139a34b4df66876a30dd609beed51fa57deb23ecc82703adfb43d2cc22d6a1c"
)
CORPUS_RELPATH = Path("knowledge/audio2tool/g3-plain-english-cards-v1/corpus.txt")
CORPUS_FILE_SHA256 = (
    "6c9a89780ed0f18c2473c9bbfca97e8f2eb5b3724386ac41c6075fd7b35f463b"
)
CORPUS_BOUND_SHA256 = (
    "95af7c6072c7fed7fc0212f16e589e41457cd010dcb13b1cdf801907ed678ece"
)
CONSTRUCTION_ACCESS_SHA256 = (
    "1a2942f6b6c139adb5932af62d40cdd148f496baf56aa0309b0cd4bdebe6bf0f"
)

M0_RECOVERY_FLIGHT_RELPATH = Path(
    "runs/SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T172919Z"
)
M0_RECOVERY_TRACE_DIR_RELPATH = M0_RECOVERY_FLIGHT_RELPATH / "m0/transport-trace"
M0_RECOVERY_TRACE_RELPATH = M0_RECOVERY_TRACE_DIR_RELPATH / f"{RUN_ID}.trace.jsonl"
M0_RECOVERY_TRACE_MANIFEST_RELPATH = (
    M0_RECOVERY_TRACE_DIR_RELPATH / f"{RUN_ID}.trace-manifest.json"
)
M0_RECOVERY_FAILURE_RELPATH = M0_RECOVERY_FLIGHT_RELPATH / "failure-receipt.json"
M0_RECOVERY_ATTEMPT_ID = "attempt-20260902t172919z-g3-m0"
M0_RECOVERY_ATTEMPT_RELPATH = (
    Path("attempts") / RUN_ID / f"{M0_RECOVERY_ATTEMPT_ID}.json"
)
M0_RECOVERY_TRACE_SHA256 = (
    "d101379ca60518ebb66076fdd0444b5114cd3ab4288139158fd0024f6872b2cf"
)
M0_RECOVERY_TRACE_MANIFEST_SHA256 = (
    "3fe9093e8562000e6741e650668eaac06298c0a731cef89c347ae7f7b3fe7ddd"
)
M0_RECOVERY_FAILURE_SHA256 = (
    "2b0d81a176895e855376321b2b6201e04e5ae59afb5b113e79df6d19f915515a"
)
M0_RECOVERY_ATTEMPT_SHA256 = (
    "01e041f3bd42cb3f54162f0da22d75cd0e18cc03e5bedcd29620a554d64ae864"
)
M0_RECOVERY_COMPLETED_COUNT = 31
COMPLETED_FLIGHT_RELPATH = Path(
    "runs/SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T174427Z"
)
COMPLETED_FLIGHT_M0_DIR_RELPATH = COMPLETED_FLIGHT_RELPATH / "m0"
COMPLETED_FLIGHT_M0_OUTPUTS_RELPATH = (
    COMPLETED_FLIGHT_M0_DIR_RELPATH / f"{RUN_ID}.outputs.jsonl"
)
COMPLETED_FLIGHT_M0_MANIFEST_RELPATH = (
    COMPLETED_FLIGHT_M0_DIR_RELPATH / f"{RUN_ID}.run-manifest.json"
)
COMPLETED_FLIGHT_M0_TRACE_RELPATH = (
    COMPLETED_FLIGHT_M0_DIR_RELPATH / f"{RUN_ID}.trace.jsonl"
)
COMPLETED_FLIGHT_M0_TRACE_MANIFEST_RELPATH = (
    COMPLETED_FLIGHT_M0_DIR_RELPATH / f"{RUN_ID}.trace-manifest.json"
)
COMPLETED_FLIGHT_OBS_TRACE_DIR_RELPATH = COMPLETED_FLIGHT_RELPATH / "obs/agent-trace"
COMPLETED_FLIGHT_OBS_TRACE_RELPATH = (
    COMPLETED_FLIGHT_OBS_TRACE_DIR_RELPATH / f"{RUN_ID}.trace.jsonl"
)
COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_RELPATH = (
    COMPLETED_FLIGHT_OBS_TRACE_DIR_RELPATH / f"{RUN_ID}.trace-manifest.json"
)
COMPLETED_FLIGHT_FAILURE_RELPATH = COMPLETED_FLIGHT_RELPATH / "failure-receipt.json"
COMPLETED_FLIGHT_M0_ATTEMPT_ID = "attempt-20260902t174427z-g3-m0"
COMPLETED_FLIGHT_OBS_ATTEMPT_ID = "attempt-20260902t174427z-g3-obs"
COMPLETED_FLIGHT_M0_ATTEMPT_RELPATH = (
    Path("attempts") / RUN_ID / f"{COMPLETED_FLIGHT_M0_ATTEMPT_ID}.json"
)
COMPLETED_FLIGHT_OBS_ATTEMPT_RELPATH = (
    Path("attempts") / RUN_ID / f"{COMPLETED_FLIGHT_OBS_ATTEMPT_ID}.json"
)
COMPLETED_FLIGHT_M0_OUTPUTS_SHA256 = (
    "15c542c3d44f9e760a529cd21e334c0643de76e468ebce3acf174097d4deba55"
)
COMPLETED_FLIGHT_M0_MANIFEST_SHA256 = (
    "1a25d4a9e12114c4d74e7a6021ea8d13184d513fcaa5dbc931a82a2ab790f1bc"
)
COMPLETED_FLIGHT_M0_TRACE_SHA256 = (
    "08d9c70227a3d36f32a2fb47f712715ae2a29c90cc1820a4e8f8761d10d23077"
)
COMPLETED_FLIGHT_M0_TRACE_MANIFEST_SHA256 = (
    "0095de3eca8fade86e6722009ce9a3af6616cbf7056f2673cf39fe1f2d0b7c2e"
)
COMPLETED_FLIGHT_OBS_TRACE_SHA256 = (
    "7f50c98d39d6d6f721603304094d9108658b91ab7d7f10349e17b2d1b4e83aa8"
)
COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_SHA256 = (
    "5c06db3c246f5f631bbeadd62a67f6f996b21691bc6dbc0781d13da772a1222e"
)
COMPLETED_FLIGHT_FAILURE_SHA256 = (
    "75186ab604c6b362e3f8a9cd8f1a0d2ac0b2349233820f80c12d4688f651a3b6"
)
COMPLETED_FLIGHT_M0_ATTEMPT_SHA256 = (
    "4e76dbefba4632a12fcf5d9ce6aad86556f7639dede72e78a0bcf86c5361c2fe"
)
COMPLETED_FLIGHT_OBS_ATTEMPT_SHA256 = (
    "c928fd1adc45ae4ab37f30381e1f5c0899b5b81ef28094f021c9eb351a730db6"
)
MATCHED_RECOVERY_FLIGHT_RELPATH = Path(
    "runs/SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T180333Z"
)
MATCHED_RECOVERY_DIR_RELPATH = MATCHED_RECOVERY_FLIGHT_RELPATH / "matched"
MATCHED_RECOVERY_OUTPUTS_RELPATH = (
    MATCHED_RECOVERY_DIR_RELPATH / f"{RUN_ID}.outputs.jsonl"
)
MATCHED_RECOVERY_MANIFEST_RELPATH = (
    MATCHED_RECOVERY_DIR_RELPATH / f"{RUN_ID}.run-manifest.json"
)
MATCHED_RECOVERY_AGENT_TRACE_DIR_RELPATH = (
    MATCHED_RECOVERY_DIR_RELPATH / "agent-trace"
)
MATCHED_RECOVERY_AGENT_TRACE_RELPATH = (
    MATCHED_RECOVERY_AGENT_TRACE_DIR_RELPATH / f"{RUN_ID}.trace.jsonl"
)
MATCHED_RECOVERY_AGENT_MANIFEST_RELPATH = (
    MATCHED_RECOVERY_AGENT_TRACE_DIR_RELPATH / f"{RUN_ID}.trace-manifest.json"
)
MATCHED_RECOVERY_COMPOSITE_DIR_RELPATH = (
    MATCHED_RECOVERY_DIR_RELPATH / "composite-trace"
)
MATCHED_RECOVERY_COMPOSITE_TRACE_RELPATH = (
    MATCHED_RECOVERY_COMPOSITE_DIR_RELPATH / f"{RUN_ID}.trace.jsonl"
)
MATCHED_RECOVERY_COMPOSITE_MANIFEST_RELPATH = (
    MATCHED_RECOVERY_COMPOSITE_DIR_RELPATH / f"{RUN_ID}.trace-manifest.json"
)
MATCHED_RECOVERY_SESSION_RELPATH = MATCHED_RECOVERY_FLIGHT_RELPATH / (
    "service/session-receipt.json"
)
MATCHED_RECOVERY_FAILURE_RELPATH = MATCHED_RECOVERY_FLIGHT_RELPATH / "failure-receipt.json"
MATCHED_RECOVERY_ATTEMPT_ID = "attempt-20260902t180333z-g3-matched"
MATCHED_RECOVERY_ATTEMPT_RELPATH = (
    Path("attempts") / RUN_ID / f"{MATCHED_RECOVERY_ATTEMPT_ID}.json"
)
MATCHED_RECOVERY_OUTPUTS_SHA256 = (
    "6e6589ce03f638957731ceddeec109c3d9e0cca0cf365d7ae9b98634bd4b1f8f"
)
MATCHED_RECOVERY_MANIFEST_SHA256 = (
    "f43569b9b82bdb3a480a0444749140d451015f732e4440d965f8fffc9f85763e"
)
MATCHED_RECOVERY_AGENT_TRACE_SHA256 = (
    "431025422c6f111c7983582a8b6e4a9f03dcdc27a3db2b7f1991383c509d019a"
)
MATCHED_RECOVERY_AGENT_MANIFEST_SHA256 = (
    "ae9c6d60cc5cc2a4b27288790d789db6545d5cb2289fb99d2bba2338504fb2ec"
)
MATCHED_RECOVERY_COMPOSITE_TRACE_SHA256 = (
    "18b55fa9bd8bbedab3f9d7d42230e17152c54978832674654099ae88de244536"
)
MATCHED_RECOVERY_COMPOSITE_MANIFEST_SHA256 = (
    "d1e24908eb30946f841d383ab25730f766d9e4d2245bf89d75521303dc4c62d2"
)
MATCHED_RECOVERY_SESSION_SHA256 = (
    "54869b19466added1e44ec7521a0d2fa3dea4df639ae95fc7757701ae2c05e6e"
)
MATCHED_RECOVERY_FAILURE_SHA256 = (
    "f8cdfb325ef873663a24374426d013969f473c24dd206610796a934c23f86251"
)
MATCHED_RECOVERY_ATTEMPT_SHA256 = (
    "4217d688085aecaf72bffdb6bea48e48d3bc7247a115a4a6a856d672e1f77668"
)
POSTPROCESS_FLIGHT_RELPATH = Path(
    "runs/SAEA-A2T-G3-PLAIN-ENGLISH-V1/flight-20260902T182038Z"
)
POSTPROCESS_FAILURE_SHA256 = (
    "2ee1e640a0918c4f29b63100b76aaced6c2923307075611f6cd0056ecbe12f70"
)
POSTPROCESS_BATCH_SHA256 = (
    "4dd9fb0ec6fc8935467f42802855db747d03eea48bfed3d0688d15d22883b82f"
)
POSTPROCESS_M0_SCORE_SHA256 = (
    "387135c104d6956275fa0a6ac3ec4e295844cba761c660c814cba8d157ad2f81"
)
POSTPROCESS_MATCHED_SCORE_SHA256 = (
    "cfc7fcd2b64889a89ff5de2d9c81811b11d99bd5333ed473a8c520e00e9e6c5b"
)
POSTPROCESS_SHUFFLED_SCORE_SHA256 = (
    "2c7eb21357a3c8035e63b9e00f704936bf9b0e26e9f4e3ef1a77569d70aaf5d0"
)
KNOWLEDGE_SNAPSHOT_RELPATH = Path(
    "knowledge/audio2tool/saea-kb-a2t-toolshaped-v1/size-full/snapshot.json"
)
RUNTIME_RECEIPT_RELPATH = Path("docs/receipts/runtime-q4km-mmproj-free.json")
RUNTIME_RECEIPT_SHA256 = (
    "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
)

OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "schema": "saea-a2t-g3-whole-manifest-score-plan-v1",
    "entrypoint": "scripts/evaluate_parallel.sh",
    "operation": "per-job",
    "workers": 3,
    "official_scorer_modified": False,
    "processes_per_job": 1,
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "g3-m0-direct",
            "operation": "score",
            "input": "one complete 40-row manifest",
            "row_count": 40,
        },
        {
            "job_id": "g3-matched-use",
            "operation": "score",
            "input": "one complete 40-row manifest",
            "row_count": 40,
        },
        {
            "job_id": "g3-shuffled-use",
            "operation": "finalize",
            "input": "one complete 40-row manifest",
            "row_count": 40,
        },
    ],
}


def _load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen helper {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


Q = _load_module(
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-qualification-104-v1/launcher/"
    "launch_ground_qualification.py",
    "saea_g3_frozen_g2_qualification_helper",
)
CARD_BUILDER = _load_module(
    REPO / "scripts/build_a2t_g3_plain_english_cards.py",
    "saea_g3_card_builder",
)


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


def _read_json(path: Path) -> dict[str, object]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError(f"expected one JSON object: {path}")
    return document


def _trace_documents(run_dir: Path) -> tuple[Mapping[str, object], ...]:
    path = Path(run_dir) / f"{RUN_ID}.trace.jsonl"
    documents: list[Mapping[str, object]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line:
            continue
        document = json.loads(line)
        if not isinstance(document, Mapping):
            raise RuntimeError(f"G3 trace row {number} is not an object")
        documents.append(document)
    if not documents:
        raise RuntimeError(f"G3 sealed trace is empty: {path}")
    return tuple(documents)


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def _validate_m0_recovery_trace(
    documents: Sequence[Mapping[str, object]],
    manifest: Mapping[str, object],
    *,
    expected_ids: Sequence[str],
    expected_completed_count: int = M0_RECOVERY_COMPLETED_COUNT,
) -> dict[str, object]:
    """Verify complete prior M0 contacts without interpreting their answers."""

    expected = tuple(sorted(expected_ids))
    if not expected or len(set(expected)) != len(expected):
        raise RuntimeError("M0 recovery expected identities must be nonempty and unique")
    if (
        isinstance(expected_completed_count, bool)
        or not isinstance(expected_completed_count, int)
        or not 0 < expected_completed_count <= len(expected)
    ):
        raise RuntimeError("M0 recovery completed count must fit the expected surface")
    manifest_records = manifest.get("records")
    if manifest.get("run_id") != RUN_ID or not isinstance(manifest_records, Mapping):
        raise RuntimeError("M0 recovery trace manifest is malformed")

    record_ids: set[str] = set()
    documents_by_contact: dict[str, dict[str, Mapping[str, object]]] = {}
    suffix_by_channel = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "COST": "/cost",
    }
    for number, document in enumerate(documents, start=1):
        if not isinstance(document, Mapping):
            raise RuntimeError(f"M0 recovery trace row {number} is not an object")
        channel = document.get("channel")
        record_id = document.get("record_id")
        payload = document.get("payload")
        suffix = suffix_by_channel.get(channel) if isinstance(channel, str) else None
        if (
            suffix is None
            or not isinstance(record_id, str)
            or not record_id.endswith(suffix)
            or not isinstance(payload, Mapping)
            or record_id in record_ids
        ):
            raise RuntimeError(f"M0 recovery trace row {number} is malformed or duplicated")
        record_ids.add(record_id)
        measured = TraceRecord(
            channel=channel,
            record_id=record_id,
            payload=payload,
        ).content_hash()
        if manifest_records.get(record_id) != measured:
            raise RuntimeError(f"M0 recovery record hash drift for {record_id!r}")
        contact_id = record_id[: -len(suffix)]
        documents_by_contact.setdefault(contact_id, {})[channel] = document
    if set(manifest_records) != record_ids:
        raise RuntimeError("M0 recovery trace manifest record set drift")

    required_channels = set(suffix_by_channel)
    results: list[DirectPhaseResult] = []
    completed_ids: set[str] = set()
    for contact_id, contact in sorted(documents_by_contact.items()):
        if set(contact) != required_channels:
            raise RuntimeError(
                "M0 recovery requires one complete request/response/cost triple per contact"
            )
        request_outer = contact["MODEL_REQUEST"]["payload"]
        request_payload = request_outer.get("payload")
        if (
            request_outer.get("arm") != "speech-feature-query"
            or not isinstance(request_payload, Mapping)
            or request_payload.get("request_id") != contact_id
            or request_payload.get("key_representation_id")
            != "audio2tool-direct-registry-v1"
            or request_payload.get("matcher_policy_id")
            != "saea-a2t-contract-v2-m0-direct"
        ):
            raise RuntimeError(f"M0 recovery request contract drift for {contact_id!r}")
        canonical_payload = json.dumps(
            request_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if request_outer.get("payload_sha256") != hashlib.sha256(
            canonical_payload
        ).hexdigest():
            raise RuntimeError(f"M0 recovery request payload hash drift for {contact_id!r}")
        sample_id = request_payload.get("sample_id")
        if (
            not isinstance(sample_id, str)
            or sample_id not in expected
            or sample_id in completed_ids
        ):
            raise RuntimeError("M0 recovery sample identity is unknown or duplicated")
        response = contact["MODEL_RESPONSE"]["payload"]
        text = response.get("text")
        if (
            not isinstance(text, str)
            or response.get("response_text_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise RuntimeError(f"M0 recovery response text hash drift for {sample_id!r}")
        cost = contact["COST"]["payload"]
        if cost.get("calls") != 1:
            raise RuntimeError(f"M0 recovery cost is not one call for {sample_id!r}")
        completed_ids.add(sample_id)
        results.append(DirectPhaseResult(sample_id, text))

    if len(results) != expected_completed_count:
        raise RuntimeError(
            f"M0 recovery contains {len(results)} complete contacts, expected "
            f"{expected_completed_count}"
        )
    summary = DirectPhaseSummary(tuple(sorted(results, key=lambda row: row.sample_id)))
    g3_flight.build_g3_m0_bundle_material(
        summary,
        documents,
        umbrella_lock_sha256="0" * 64,
    )
    missing_ids = tuple(sorted(set(expected) - completed_ids))
    return {
        "summary": summary,
        "completed_ids": tuple(sorted(completed_ids)),
        "missing_ids": missing_ids,
    }


def _load_m0_recovery(root: Path, expected_ids: Sequence[str]) -> dict[str, object]:
    """Load the exact 31-contact aborted flight as a one-shot recovery source."""

    root = Path(root)
    trace_path = root / M0_RECOVERY_TRACE_RELPATH
    manifest_path = root / M0_RECOVERY_TRACE_MANIFEST_RELPATH
    failure_path = root / M0_RECOVERY_FAILURE_RELPATH
    attempt_path = root / M0_RECOVERY_ATTEMPT_RELPATH
    _require_hash(trace_path, M0_RECOVERY_TRACE_SHA256, "M0 recovery trace")
    _require_hash(
        manifest_path,
        M0_RECOVERY_TRACE_MANIFEST_SHA256,
        "M0 recovery trace manifest",
    )
    _require_hash(failure_path, M0_RECOVERY_FAILURE_SHA256, "M0 recovery failure")
    _require_hash(attempt_path, M0_RECOVERY_ATTEMPT_SHA256, "M0 recovery attempt")
    failure = _read_json(failure_path)
    attempt = _read_json(attempt_path)
    if (
        failure.get("phase_attempt_ids", {}).get(G3_M0_DIRECT_PHASE)
        != M0_RECOVERY_ATTEMPT_ID
        or "payload media_relpath escapes its confined root" not in str(failure.get("error"))
    ):
        raise RuntimeError("M0 recovery failure identity drift")
    actual = attempt.get("actual")
    if (
        attempt.get("attempt_id") != M0_RECOVERY_ATTEMPT_ID
        or attempt.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != M0_RECOVERY_COMPLETED_COUNT
    ):
        raise RuntimeError("M0 recovery attempt state drift")
    documents = _trace_documents(root / M0_RECOVERY_TRACE_DIR_RELPATH)
    result = _validate_m0_recovery_trace(
        documents,
        _read_json(manifest_path),
        expected_ids=expected_ids,
    )
    if len(result["missing_ids"]) != SPLIT_COUNT - M0_RECOVERY_COMPLETED_COUNT:
        raise RuntimeError("M0 recovery source does not leave exactly nine missing identities")
    return {
        **result,
        "documents": documents,
        "source_attempt_id": M0_RECOVERY_ATTEMPT_ID,
        "source_trace_sha256": M0_RECOVERY_TRACE_SHA256,
        "source_trace_manifest_sha256": M0_RECOVERY_TRACE_MANIFEST_SHA256,
    }


def _validate_obs_recovery_trace(
    documents: Sequence[Mapping[str, object]],
    manifest: Mapping[str, object],
    *,
    expected_ids: Sequence[str],
) -> dict[str, object]:
    """Verify and mechanically recover one complete task-blind OBS trace."""

    expected = set(expected_ids)
    if len(expected) != SPLIT_COUNT:
        raise RuntimeError("OBS recovery requires the complete 40-row identity surface")
    manifest_records = manifest.get("records")
    if manifest.get("run_id") != RUN_ID or not isinstance(manifest_records, Mapping):
        raise RuntimeError("OBS recovery trace manifest is malformed")
    by_contact: dict[str, dict[str, Mapping[str, object]]] = {}
    record_ids: set[str] = set()
    suffix_by_channel = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "COST": "/cost",
    }
    for number, document in enumerate(documents, start=1):
        channel = document.get("channel")
        record_id = document.get("record_id")
        payload = document.get("payload")
        if (
            not isinstance(channel, str)
            or not isinstance(record_id, str)
            or not isinstance(payload, Mapping)
            or record_id in record_ids
        ):
            raise RuntimeError(f"OBS recovery trace row {number} is malformed or duplicated")
        record_ids.add(record_id)
        measured = TraceRecord(
            channel=channel,
            record_id=record_id,
            payload=payload,
        ).content_hash()
        if manifest_records.get(record_id) != measured:
            raise RuntimeError(f"OBS recovery record hash drift for {record_id!r}")
        suffix = suffix_by_channel.get(channel)
        if suffix is not None:
            if not record_id.endswith(suffix):
                raise RuntimeError(f"OBS recovery record id drift for {record_id!r}")
            contact_id = record_id[: -len(suffix)]
            by_contact.setdefault(contact_id, {})[channel] = document
    if set(manifest_records) != record_ids:
        raise RuntimeError("OBS recovery trace manifest record set drift")

    required = set(suffix_by_channel)
    results: list[DirectPhaseResult] = []
    contact_counts: dict[str, int] = {}
    cost_totals = {
        "calls": 0,
        "audio_seconds": 0.0,
        "completion_tokens": 0,
        "latency_seconds": 0.0,
        "prompt_tokens": 0,
    }
    for contact_id, contact in sorted(by_contact.items()):
        if set(contact) != required:
            raise RuntimeError(
                "OBS recovery requires one complete request/response/cost triple per contact"
            )
        request_outer = contact["MODEL_REQUEST"]["payload"]
        request_payload = request_outer.get("payload")
        if (
            request_outer.get("arm") != "speech-feature-query"
            or not isinstance(request_payload, Mapping)
            or request_payload.get("request_id") != contact_id
            or request_payload.get("key_representation_id")
            != "saea-a2t-contract-v2-self-transcript-observation:speech"
            or request_payload.get("matcher_policy_id")
            != "saea-a2t-contract-v2-self-transcript-observation"
        ):
            raise RuntimeError(f"OBS recovery request contract drift for {contact_id!r}")
        canonical_payload = json.dumps(
            request_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if request_outer.get("payload_sha256") != hashlib.sha256(
            canonical_payload
        ).hexdigest():
            raise RuntimeError(f"OBS recovery request payload hash drift for {contact_id!r}")
        sample_id = request_payload.get("sample_id")
        if (
            not isinstance(sample_id, str)
            or sample_id not in expected
            or sample_id in contact_counts
        ):
            raise RuntimeError("OBS recovery sample identity is unknown or duplicated")
        response = contact["MODEL_RESPONSE"]["payload"]
        text = response.get("text")
        if (
            not isinstance(text, str)
            or response.get("response_text_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise RuntimeError(f"OBS recovery response text hash drift for {sample_id!r}")
        cost = contact["COST"]["payload"]
        if cost.get("calls") != 1:
            raise RuntimeError(f"OBS recovery cost is not one call for {sample_id!r}")
        contact_counts[sample_id] = 1
        results.append(DirectPhaseResult(sample_id, text))
        for field in cost_totals:
            value = cost.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise RuntimeError(f"OBS recovery cost field {field!r} is malformed")
            cost_totals[field] += value
    if set(contact_counts) != expected:
        raise RuntimeError("OBS recovery does not contain exactly forty sample contacts")
    summary = DirectPhaseSummary(tuple(sorted(results, key=lambda row: row.sample_id)))
    return {
        "summary": summary,
        "texts": {row.sample_id: row.final_response_text for row in summary.results},
        "contact_counts": dict(sorted(contact_counts.items())),
        "cost": cost_totals,
    }


def _validate_matched_recovery_trace(
    documents: Sequence[Mapping[str, object]],
    manifest: Mapping[str, object],
    *,
    expected_ids: Sequence[str],
) -> dict[str, object]:
    """Verify the complete 40-draft plus 5-repair matched Agent trace."""

    expected = set(expected_ids)
    if len(expected) != SPLIT_COUNT:
        raise RuntimeError("matched recovery requires the complete 40-row surface")
    manifest_records = manifest.get("records")
    if manifest.get("run_id") != RUN_ID or not isinstance(manifest_records, Mapping):
        raise RuntimeError("matched recovery trace manifest is malformed")
    suffix_by_channel = {
        "MODEL_REQUEST": "/request",
        "MODEL_RESPONSE": "/response",
        "COST": "/cost",
    }
    by_contact: dict[str, dict[str, Mapping[str, object]]] = {}
    record_ids: set[str] = set()
    for number, document in enumerate(documents, start=1):
        channel = document.get("channel")
        record_id = document.get("record_id")
        payload = document.get("payload")
        if (
            not isinstance(channel, str)
            or not isinstance(record_id, str)
            or not isinstance(payload, Mapping)
            or record_id in record_ids
        ):
            raise RuntimeError(
                f"matched recovery trace row {number} is malformed or duplicated"
            )
        record_ids.add(record_id)
        measured = TraceRecord(
            channel=channel,
            record_id=record_id,
            payload=payload,
        ).content_hash()
        if manifest_records.get(record_id) != measured:
            raise RuntimeError(f"matched recovery record hash drift for {record_id!r}")
        suffix = suffix_by_channel.get(channel)
        if suffix is not None:
            if not record_id.endswith(suffix):
                raise RuntimeError(f"matched recovery record id drift for {record_id!r}")
            contact_id = record_id[: -len(suffix)]
            contact = by_contact.setdefault(contact_id, {})
            if channel in contact:
                raise RuntimeError(f"matched recovery duplicate channel for {contact_id!r}")
            contact[channel] = document
    if set(manifest_records) != record_ids:
        raise RuntimeError("matched recovery trace manifest record set drift")

    required = set(suffix_by_channel)
    contact_counts: Counter[str] = Counter()
    cost_totals = {
        "calls": 0,
        "audio_seconds": 0.0,
        "completion_tokens": 0,
        "latency_seconds": 0.0,
        "prompt_tokens": 0,
    }
    for contact_id, contact in sorted(by_contact.items()):
        if set(contact) != required:
            raise RuntimeError(
                "matched recovery requires complete request/response/cost triples"
            )
        request_outer = contact["MODEL_REQUEST"]["payload"]
        request_payload = request_outer.get("payload")
        if (
            request_outer.get("arm") != "speech-feature-query"
            or not isinstance(request_payload, Mapping)
            or request_payload.get("request_id") != contact_id
            or request_payload.get("key_representation_id")
            != "a2t-g3-plain-english-k32-v1"
            or request_payload.get("matcher_policy_id")
            != "a2t-g3-construction-bm25-k32-matched-v1"
        ):
            raise RuntimeError(f"matched recovery request contract drift for {contact_id!r}")
        canonical_payload = json.dumps(
            request_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if request_outer.get("payload_sha256") != hashlib.sha256(
            canonical_payload
        ).hexdigest():
            raise RuntimeError(f"matched recovery payload hash drift for {contact_id!r}")
        sample_id = request_payload.get("sample_id")
        if not isinstance(sample_id, str) or sample_id not in expected:
            raise RuntimeError("matched recovery sample identity is unknown")
        response = contact["MODEL_RESPONSE"]["payload"]
        text = response.get("text")
        if (
            not isinstance(text, str)
            or response.get("response_text_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
        ):
            raise RuntimeError(f"matched recovery response hash drift for {sample_id!r}")
        cost = contact["COST"]["payload"]
        if cost.get("calls") != 1:
            raise RuntimeError(f"matched recovery cost is not one call for {sample_id!r}")
        contact_counts[sample_id] += 1
        for field in cost_totals:
            value = cost.get(field)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise RuntimeError(f"matched recovery cost field {field!r} is malformed")
            cost_totals[field] += value
    repair_ids = tuple(sorted(sample_id for sample_id, count in contact_counts.items() if count == 2))
    if (
        set(contact_counts) != expected
        or any(count not in {1, 2} for count in contact_counts.values())
        or sum(contact_counts.values()) != 45
        or len(repair_ids) != 5
    ):
        raise RuntimeError("matched recovery is not exactly forty drafts plus five repairs")
    return {
        "contact_counts": dict(sorted(contact_counts.items())),
        "repair_count": len(repair_ids),
        "repair_sample_ids": repair_ids,
        "cost": cost_totals,
    }


def _load_completed_flight(root: Path, expected_ids: Sequence[str]) -> dict[str, object]:
    """Load the hash-pinned complete M0 and OBS surfaces without new contacts."""

    root = Path(root)
    pinned = (
        (COMPLETED_FLIGHT_M0_OUTPUTS_RELPATH, COMPLETED_FLIGHT_M0_OUTPUTS_SHA256),
        (COMPLETED_FLIGHT_M0_MANIFEST_RELPATH, COMPLETED_FLIGHT_M0_MANIFEST_SHA256),
        (COMPLETED_FLIGHT_M0_TRACE_RELPATH, COMPLETED_FLIGHT_M0_TRACE_SHA256),
        (
            COMPLETED_FLIGHT_M0_TRACE_MANIFEST_RELPATH,
            COMPLETED_FLIGHT_M0_TRACE_MANIFEST_SHA256,
        ),
        (COMPLETED_FLIGHT_OBS_TRACE_RELPATH, COMPLETED_FLIGHT_OBS_TRACE_SHA256),
        (
            COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_RELPATH,
            COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_SHA256,
        ),
        (COMPLETED_FLIGHT_FAILURE_RELPATH, COMPLETED_FLIGHT_FAILURE_SHA256),
        (COMPLETED_FLIGHT_M0_ATTEMPT_RELPATH, COMPLETED_FLIGHT_M0_ATTEMPT_SHA256),
        (COMPLETED_FLIGHT_OBS_ATTEMPT_RELPATH, COMPLETED_FLIGHT_OBS_ATTEMPT_SHA256),
    )
    for relpath, digest in pinned:
        _require_hash(root / relpath, digest, f"completed-flight {relpath.name}")

    failure = _read_json(root / COMPLETED_FLIGHT_FAILURE_RELPATH)
    m0_attempt = _read_json(root / COMPLETED_FLIGHT_M0_ATTEMPT_RELPATH)
    obs_attempt = _read_json(root / COMPLETED_FLIGHT_OBS_ATTEMPT_RELPATH)
    if "dialogue OBS lacks alternating role labels" not in str(failure.get("error")):
        raise RuntimeError("completed-flight failure identity drift")
    for attempt, attempt_id, calls in (
        (m0_attempt, COMPLETED_FLIGHT_M0_ATTEMPT_ID, 9),
        (obs_attempt, COMPLETED_FLIGHT_OBS_ATTEMPT_ID, 40),
    ):
        actual = attempt.get("actual")
        if (
            attempt.get("attempt_id") != attempt_id
            or attempt.get("state") != "ABORTED"
            or not isinstance(actual, Mapping)
            or actual.get("calls") != calls
        ):
            raise RuntimeError("completed-flight attempt state drift")

    m0_manifest_path = root / COMPLETED_FLIGHT_M0_MANIFEST_RELPATH
    bundle = verify_bundle(m0_manifest_path)
    if bundle.attempt_state != "ABORTED" or len(bundle.outputs_rows) != SPLIT_COUNT:
        raise RuntimeError("completed-flight M0 bundle is not a complete aborted recovery")
    m0_documents = _trace_documents(root / COMPLETED_FLIGHT_M0_DIR_RELPATH)
    m0_trace = _validate_m0_recovery_trace(
        m0_documents,
        _read_json(root / COMPLETED_FLIGHT_M0_TRACE_MANIFEST_RELPATH),
        expected_ids=expected_ids,
        expected_completed_count=SPLIT_COUNT,
    )
    output_texts = {
        str(row["sample_id"]): str(row["text"]) for row in bundle.outputs_rows
    }
    trace_texts = {
        row.sample_id: row.final_response_text for row in m0_trace["summary"].results
    }
    if output_texts != trace_texts:
        raise RuntimeError("completed-flight M0 outputs and trace disagree")
    manifest_document = _read_json(m0_manifest_path)
    m0_cost = manifest_document.get("cost")
    if not isinstance(m0_cost, Mapping) or m0_cost.get("calls_used") != SPLIT_COUNT:
        raise RuntimeError("completed-flight M0 cost drift")

    obs_documents = _trace_documents(root / COMPLETED_FLIGHT_OBS_TRACE_DIR_RELPATH)
    observation = _validate_obs_recovery_trace(
        obs_documents,
        _read_json(root / COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_RELPATH),
        expected_ids=expected_ids,
    )
    if (
        observation["cost"]["calls"] != SPLIT_COUNT
        or observation["cost"]["audio_seconds"]
        != obs_attempt["actual"]["audio_seconds"]
    ):
        raise RuntimeError("completed-flight OBS cost drift")
    return {
        "m0": {
            "texts": dict(sorted(output_texts.items())),
            "manifest": m0_manifest_path,
            "cost": dict(m0_cost),
        },
        "observation": {
            **observation,
            "agent_trace_hash": COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_SHA256,
        },
        "contact_accounting": {
            "original_m0": M0_RECOVERY_COMPLETED_COUNT,
            "m0_recovery": SPLIT_COUNT - M0_RECOVERY_COMPLETED_COUNT,
            "observation": SPLIT_COUNT,
            "cumulative_before_use": 80,
        },
    }


def _load_matched_recovery(root: Path, expected_ids: Sequence[str]) -> dict[str, object]:
    """Load and verify the hash-pinned 45-contact matched recovery surface."""

    root = Path(root)
    pinned = (
        (MATCHED_RECOVERY_OUTPUTS_RELPATH, MATCHED_RECOVERY_OUTPUTS_SHA256),
        (MATCHED_RECOVERY_MANIFEST_RELPATH, MATCHED_RECOVERY_MANIFEST_SHA256),
        (MATCHED_RECOVERY_AGENT_TRACE_RELPATH, MATCHED_RECOVERY_AGENT_TRACE_SHA256),
        (
            MATCHED_RECOVERY_AGENT_MANIFEST_RELPATH,
            MATCHED_RECOVERY_AGENT_MANIFEST_SHA256,
        ),
        (
            MATCHED_RECOVERY_COMPOSITE_TRACE_RELPATH,
            MATCHED_RECOVERY_COMPOSITE_TRACE_SHA256,
        ),
        (
            MATCHED_RECOVERY_COMPOSITE_MANIFEST_RELPATH,
            MATCHED_RECOVERY_COMPOSITE_MANIFEST_SHA256,
        ),
        (MATCHED_RECOVERY_SESSION_RELPATH, MATCHED_RECOVERY_SESSION_SHA256),
        (MATCHED_RECOVERY_FAILURE_RELPATH, MATCHED_RECOVERY_FAILURE_SHA256),
        (MATCHED_RECOVERY_ATTEMPT_RELPATH, MATCHED_RECOVERY_ATTEMPT_SHA256),
    )
    for relpath, digest in pinned:
        _require_hash(root / relpath, digest, f"matched recovery {relpath.name}")

    failure = _read_json(root / MATCHED_RECOVERY_FAILURE_RELPATH)
    attempt = _read_json(root / MATCHED_RECOVERY_ATTEMPT_RELPATH)
    actual = attempt.get("actual")
    if (
        "lacks a usable raw trace entry" not in str(failure.get("error"))
        or failure.get("phase_attempt_ids", {}).get(G3_MATCHED_USE_PHASE)
        != MATCHED_RECOVERY_ATTEMPT_ID
        or attempt.get("attempt_id") != MATCHED_RECOVERY_ATTEMPT_ID
        or attempt.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != 45
    ):
        raise RuntimeError("matched recovery failure or attempt identity drift")

    source_manifest = _read_json(root / MATCHED_RECOVERY_MANIFEST_RELPATH)
    source_cost = source_manifest.get("cost")
    if (
        source_manifest.get("status") != STATUS_COMPLETED
        or source_manifest.get("raw_trace") is not None
        or source_manifest.get("trace_manifest") is not None
        or source_manifest.get("outputs", {}).get("sha256")
        != MATCHED_RECOVERY_OUTPUTS_SHA256
        or source_manifest.get("plan", {}).get("attempt_id")
        != MATCHED_RECOVERY_ATTEMPT_ID
        or not isinstance(source_cost, Mapping)
        or source_cost.get("calls_used") != 45
    ):
        raise RuntimeError("matched recovery source manifest drift")

    agent_documents = _trace_documents(root / MATCHED_RECOVERY_AGENT_TRACE_DIR_RELPATH)
    agent = _validate_matched_recovery_trace(
        agent_documents,
        _read_json(root / MATCHED_RECOVERY_AGENT_MANIFEST_RELPATH),
        expected_ids=expected_ids,
    )
    cost = agent["cost"]
    if (
        cost["calls"] != source_cost.get("calls_used")
        or cost["audio_seconds"] != source_cost.get("audio_seconds_used")
        or cost["completion_tokens"] != source_cost.get("completion_tokens_total")
        or cost["latency_seconds"] != source_cost.get("latency_seconds_total")
        or cost["prompt_tokens"] != source_cost.get("prompt_tokens_total")
        or actual.get("audio_seconds") != cost["audio_seconds"]
    ):
        raise RuntimeError("matched recovery cost totals drift")

    composite_documents = _trace_documents(
        root / MATCHED_RECOVERY_COMPOSITE_DIR_RELPATH
    )
    composite_manifest = _read_json(root / MATCHED_RECOVERY_COMPOSITE_MANIFEST_RELPATH)
    composite_records = composite_manifest.get("records")
    if not isinstance(composite_records, Mapping) or len(composite_documents) != 80:
        raise RuntimeError("matched recovery composite trace shape drift")
    composite_ids: set[str] = set()
    for document in composite_documents:
        record_id = document.get("record_id")
        if not isinstance(record_id, str) or record_id in composite_ids:
            raise RuntimeError("matched recovery composite record identity drift")
        composite_ids.add(record_id)
        if composite_records.get(record_id) != TraceRecord(**document).content_hash():
            raise RuntimeError(f"matched recovery composite hash drift for {record_id!r}")
    if set(composite_records) != composite_ids:
        raise RuntimeError("matched recovery composite manifest record set drift")

    outputs_path = root / MATCHED_RECOVERY_OUTPUTS_RELPATH
    rows = tuple(
        json.loads(line)
        for line in outputs_path.read_text(encoding="utf-8").splitlines()
        if line
    )
    expected = set(expected_ids)
    by_id: dict[str, Mapping[str, object]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            raise RuntimeError("matched recovery output row is not an object")
        sample_id = row.get("sample_id")
        text = row.get("text")
        request_id = row.get("request_id")
        if (
            not isinstance(sample_id, str)
            or sample_id in by_id
            or not isinstance(text, str)
            or row.get("response_text_sha256")
            != hashlib.sha256(text.encode("utf-8")).hexdigest()
            or not isinstance(request_id, str)
            or f"{request_id}/request" not in composite_ids
            or f"{request_id}/response" not in composite_ids
        ):
            raise RuntimeError("matched recovery output binding drift")
        by_id[sample_id] = row
    if len(rows) != SPLIT_COUNT or set(by_id) != expected:
        raise RuntimeError("matched recovery outputs do not cover all forty samples")
    return {
        "source_outputs": outputs_path,
        "source_agent_trace": root / MATCHED_RECOVERY_AGENT_TRACE_RELPATH,
        "source_composite_trace": root / MATCHED_RECOVERY_COMPOSITE_TRACE_RELPATH,
        "source_composite_manifest": root / MATCHED_RECOVERY_COMPOSITE_MANIFEST_RELPATH,
        "source_session_receipt": root / MATCHED_RECOVERY_SESSION_RELPATH,
        "texts": {sample_id: str(by_id[sample_id]["text"]) for sample_id in sorted(by_id)},
        "contact_counts": agent["contact_counts"],
        "repair_count": agent["repair_count"],
        "repair_sample_ids": agent["repair_sample_ids"],
        "cost": dict(source_cost),
    }


def _write_combined_trace(
    run_dir: Path,
    documents: Sequence[Mapping[str, object]],
) -> tuple[str, Mapping[str, object]]:
    sink = TraceSink(run_dir, RUN_ID)
    for document in documents:
        sink.emit(
            str(document["channel"]),
            str(document["record_id"]),
            document["payload"],
        )
    manifest_hash = sink.close()
    manifest = _read_json(Path(run_dir) / f"{RUN_ID}.trace-manifest.json")
    return manifest_hash, manifest


def _execution_plan(phase: str, attempt_id: str) -> ExecutionPlan:
    if phase not in PHASES:
        raise RuntimeError(f"unknown G3 phase {phase!r}")
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=RUN_IDENTITY_SHA256,
        planned_model_calls=192,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1865,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def _phase_attempt_ids(stamp: str) -> dict[str, str]:
    return {
        phase: f"attempt-{stamp}-g3-{suffix}"
        for phase, suffix in PHASE_SUFFIXES.items()
    }


def _validate_roster(document: Mapping[str, object]) -> dict[str, object]:
    items = document.get("items")
    if document.get("count") != SPLIT_COUNT or not isinstance(items, list) or len(items) != 40:
        raise RuntimeError("G3 roster must contain exactly 40 rows")
    sample_ids: list[str] = []
    tiers: dict[str, str] = {}
    for item in items:
        if not isinstance(item, Mapping):
            raise RuntimeError("G3 roster item must be an object")
        sample_id = item.get("sample_id")
        tier = item.get("tier")
        if not isinstance(sample_id, str) or not sample_id or not isinstance(tier, str):
            raise RuntimeError("G3 roster identity fields are malformed")
        sample_ids.append(sample_id)
        tiers[sample_id] = tier
    if len(set(sample_ids)) != 40:
        raise RuntimeError("G3 roster requires 40 unique sample identities")
    counts = Counter(tiers.values())
    if counts != Counter({tier: 5 for tier in CANONICAL_TIERS}):
        raise RuntimeError("G3 roster requires five rows in each canonical tier")
    return {
        "items": tuple(items),
        "sample_ids": tuple(sorted(sample_ids)),
        "tier_by_sample": dict(sorted(tiers.items())),
        "tier_counts": dict(sorted(counts.items())),
    }


def _validate_official_score_plan(plan: Mapping[str, object]) -> dict[str, object]:
    jobs = plan.get("jobs")
    if (
        plan.get("entrypoint") != "scripts/evaluate_parallel.sh"
        or plan.get("operation") != "per-job"
        or plan.get("workers") != 3
        or plan.get("official_scorer_modified") is not False
        or plan.get("processes_per_job") != 1
        or plan.get("dataset_sharding") is not False
        or plan.get("shard_metric_averaging") is not False
        or plan.get("network_jitter_testing") is not False
        or not isinstance(jobs, list)
        or len(jobs) != 3
    ):
        raise RuntimeError("G3 official score plan drift")
    for job in jobs:
        if (
            not isinstance(job, Mapping)
            or job.get("row_count") != 40
            or job.get("input") != "one complete 40-row manifest"
            or job.get("operation") not in {"score", "finalize"}
        ):
            raise RuntimeError("every scorer input must be one complete 40-row manifest")
    return dict(plan)


def _validate_packet_routes(
    routes: Mapping[str, object],
    sample_ids: Sequence[str],
    representation_flags: Mapping[str, Mapping[str, bool]] | None = None,
) -> dict[str, object]:
    expected = set(sample_ids)
    if len(expected) != 40 or set(routes) != expected:
        raise RuntimeError("OBS must produce exactly one packet route for all 40 samples")
    maximum = 0
    for sample_id in sorted(routes):
        route = routes[sample_id]
        matched = getattr(route, "matched_packet", None)
        shuffled = getattr(route, "shuffled_packet", None)
        matched_names = getattr(route, "matched_tool_names", None)
        shuffled_names = getattr(route, "shuffled_tool_names", None)
        if (
            not isinstance(matched, str)
            or not matched
            or not isinstance(shuffled, str)
            or not shuffled
            or not isinstance(matched_names, tuple)
            or len(matched_names) != 32
            or not isinstance(shuffled_names, tuple)
            or len(shuffled_names) != 32
            or set(matched_names) & set(shuffled_names)
        ):
            raise RuntimeError(f"invalid OBS packet route for {sample_id!r}")
        maximum = max(maximum, len(matched.encode()), len(shuffled.encode()))
        if maximum > PACKET_UTF8_BYTE_CAP:
            raise RuntimeError("OBS packet exceeds the frozen 64KB cap")
    flags = representation_flags or {}
    if flags and set(flags) != expected:
        raise RuntimeError("OBS representation flags must cover all forty samples")
    missing_ids = tuple(
        sorted(sample_id for sample_id, row in flags.items() if row.get("role_labels_missing"))
    )
    normalized_ids = tuple(
        sorted(sample_id for sample_id, row in flags.items() if row.get("normalized_non_ascii"))
    )
    return {
        "route_count": 40,
        "maximum_packet_utf8_bytes": maximum,
        "role_labels_missing": len(missing_ids),
        "role_labels_missing_sample_ids": missing_ids,
        "normalized_non_ascii": len(normalized_ids),
        "normalized_non_ascii_sample_ids": normalized_ids,
    }


def _validate_promotion(
    promotion: Mapping[str, object], bindings: Mapping[str, object]
) -> None:
    packets = promotion.get("packets")
    binding_rows = bindings.get("bindings")
    if (
        promotion.get("count") != 40
        or promotion.get("derived_complete_dialogue_count") != 5
        or promotion.get("reused_original_count") != 35
        or not isinstance(packets, list)
        or len(packets) != 40
        or bindings.get("count") != 40
        or not isinstance(binding_rows, Mapping)
        or len(binding_rows) != 40
    ):
        raise RuntimeError("G3 packet promotion geometry drift")
    by_sample = {
        row.get("sample_id"): row for row in packets if isinstance(row, Mapping)
    }
    if set(by_sample) != set(binding_rows):
        raise RuntimeError("G3 promotion and binding sample identities disagree")
    for sample_id, binding in binding_rows.items():
        packet = by_sample[sample_id]
        if (
            not isinstance(binding, Mapping)
            or binding.get("packet_id") != packet.get("packet_id")
            or binding.get("sha256") != packet.get("packet_sha256")
        ):
            raise RuntimeError(f"G3 packet binding drift for {sample_id!r}")
        loaded = load_speech_feature_packet(PROMOTION_RECEIPT.parent, str(binding["packet_id"]))
        if loaded.packet_sha256 != binding.get("sha256"):
            raise RuntimeError(f"G3 packet bytes drift for {sample_id!r}")


def _rebuild_corpus(root: Path) -> tuple[object, dict[str, object]]:
    text, receipt = CARD_BUILDER.build(REPO, root)
    corpus_meta = receipt.get("corpus")
    if (
        not isinstance(corpus_meta, Mapping)
        or corpus_meta.get("sha256") != CORPUS_BOUND_SHA256
        or corpus_meta.get("construction_access_sha256") != CONSTRUCTION_ACCESS_SHA256
        or not text.isascii()
    ):
        raise RuntimeError("deterministic G3 corpus identity drift")
    external = Path(root) / CORPUS_RELPATH
    _require_hash(external, CORPUS_FILE_SHA256, "external G3 corpus")
    if external.read_text(encoding="ascii") != text:
        raise RuntimeError("external G3 corpus differs from deterministic rebuild")
    lock = load_lock(umbrella_lock_path(REPO))
    registry = load_tool_registry(lock, root)
    rows, _inventory = CARD_BUILDER.a2t_pool_rows(lock, root)
    partition = CARD_BUILDER.propose_partition(
        rows,
        CARD_BUILDER.exposed_sample_ids(REPO),
        seed=CARD_BUILDER.PARTITION_SEED,
    )
    forbidden = CARD_BUILDER.exposed_sample_ids(REPO) | frozenset(partition.eval_sample_ids)
    corpus = CARD_BUILDER.build_plain_english_card_corpus(
        registry,
        partition.construction,
        forbidden_sample_ids=forbidden,
        max_corpus_utf8_bytes=512_000,
        max_tool_card_utf8_bytes=6_000,
    )
    if corpus.sha256 != CORPUS_BOUND_SHA256:
        raise RuntimeError("rebuilt in-memory G3 corpus identity drift")
    return corpus, {
        "corpus_utf8_bytes": len(text.encode()),
        "corpus_bound_sha256": corpus.sha256,
        "construction_access_sha256": corpus.construction_access_sha256,
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
        raise RuntimeError("composed G3 config identity drift")
    if (
        protocol_hash(composed.config_hash, str(composed.values.get("arm")), RUN_IDENTITY_SHA256)
        != PROTOCOL_SHA256
    ):
        raise RuntimeError("G3 protocol identity drift")
    geometry = Q._validate_server_geometry(composed.values)
    _validate_official_score_plan(OFFICIAL_SCORE_PLAN)

    _require_hash(REPO / ROSTER_RELPATH, ROSTER_SHA256, "G3 roster")
    roster_document = _read_json(REPO / ROSTER_RELPATH)
    roster = _validate_roster(roster_document)
    _require_hash(Path(root) / MEDIA_RELPATH, MEDIA_SHA256, "G3 runtime media")
    media = _read_json(Path(root) / MEDIA_RELPATH)
    _require_hash(BINDING_MAP, BINDING_SHA256, "G3 binding map")
    bindings = _read_json(BINDING_MAP)
    _require_hash(PROMOTION_RECEIPT, PROMOTION_SHA256, "G3 promotion receipt")
    promotion = _read_json(PROMOTION_RECEIPT)
    _validate_promotion(promotion, bindings)
    surface = g3_flight.resolve_g3_runtime_media(
        roster_document,
        media,
        bindings,
        data_root=root,
    )
    m0_recovery = _load_m0_recovery(root, tuple(surface.tier_by_sample))
    completed_flight = _load_completed_flight(root, tuple(surface.tier_by_sample))
    matched_recovery = _load_matched_recovery(root, tuple(surface.tier_by_sample))

    _require_hash(REPO / CARD_BUILD_RELPATH, CARD_BUILD_SHA256, "G3 card build")
    card_build = _read_json(REPO / CARD_BUILD_RELPATH)
    corpus_meta = card_build.get("corpus")
    if (
        not isinstance(corpus_meta, Mapping)
        or corpus_meta.get("sha256") != CORPUS_BOUND_SHA256
        or corpus_meta.get("construction_access_sha256") != CONSTRUCTION_ACCESS_SHA256
    ):
        raise RuntimeError("G3 card build receipt content drift")
    corpus, route_build = _rebuild_corpus(root)

    _require_hash(REPO / RUNTIME_RECEIPT_RELPATH, RUNTIME_RECEIPT_SHA256, "runtime receipt")
    runtime_document = _read_json(REPO / RUNTIME_RECEIPT_RELPATH)
    Q._validate_runtime_receipt(runtime_document)
    lock = load_lock(umbrella_lock_path(REPO))
    snapshot = KnowledgeSnapshot.from_frozen_json(
        _read_json(Path(root) / KNOWLEDGE_SNAPSHOT_RELPATH)
    )
    selected_ids = g3_flight.select_shuffled_control_ids(surface.tier_by_sample)
    return {
        "commit": commit,
        "composed": composed,
        "geometry": geometry,
        "items": roster["items"],
        "sample_ids": roster["sample_ids"],
        "tier_by_sample": roster["tier_by_sample"],
        "surface": surface,
        "m0_recovery": m0_recovery,
        "completed_flight": completed_flight,
        "matched_recovery": matched_recovery,
        "selected_ids": selected_ids,
        "corpus": corpus,
        "route_build": route_build,
        "lock": lock,
        "registry_rows": load_tool_registry(lock, root),
        "registry_contract": render_tool_schemas(lock, root),
        "carrier_root": asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root),
        "snapshot": snapshot,
        "runtime_receipt": runtime_document,
    }


def _verified_split(sample_ids: Sequence[str]) -> VerifiedSplit:
    ids = tuple(sorted(sample_ids))
    if len(ids) != 40 or len(set(ids)) != 40:
        raise RuntimeError("G3 bundle requires the complete 40 identities")
    return VerifiedSplit(
        name=g3_flight.G3_SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in ids),
        identity_hash=RUN_IDENTITY_SHA256,
    )


def _decoding(context: Mapping[str, object]) -> dict[str, object]:
    values = context["composed"].values
    decoding = dict(values["decoding_params"])
    decoding.pop("id_slot", None)
    return decoding


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
    expected_attempt_state: str = "OPENED",
) -> Path:
    manifest = build_manifest(
        repo_root=REPO,
        data_root=root,
        composed=context["composed"],
        plan=plan,
        verified_split=_verified_split(context["sample_ids"]),
        session_receipt_path=session_receipt_path,
        run_dir=run_dir,
        status=STATUS_COMPLETED,
        result=RunResult(
            run_id=RUN_ID,
            arm="speech-feature-query",
            outputs_path=outputs_path,
            trace_manifest_hash=trace_manifest_hash,
            cost=cost,
        ),
    )
    bundle = verify_bundle(manifest)
    if bundle.attempt_state != expected_attempt_state or len(bundle.outputs_rows) != 40:
        raise RuntimeError(
            "G3 phase did not seal a complete manifest in the expected attempt state"
        )
    return manifest


def _client(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    plan: ExecutionPlan,
    samples: Sequence[object],
    packet_bindings: Mapping[str, Mapping[str, object]],
    run_dir: Path,
    prefix: str,
) -> FrozenCoreClient:
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=root,
    )
    return FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir / "transport-trace",
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix=prefix,
        speech_feature_root=PROMOTION_RECEIPT.parent,
        speech_packet_bindings=packet_bindings,
    )


class _G3MediaIdentityGate:
    """Translate logical G3 ids only at the D1 media-identity boundary.

    AgentLoop results, model traces, and scorer rows retain the frozen logical
    ``tier7_multiturn:*`` identities.  The five complete-dialogue WAVs have
    separately frozen ``a2t-g3-dialogue:*`` identities in the protocol-bound
    D1 supplement, so only the gate lookup key is translated.
    """

    def __init__(self, delegate: object, media_identity_by_sample: Mapping[str, str]) -> None:
        identities = dict(media_identity_by_sample)
        if (
            not identities
            or any(
                not isinstance(sample_id, str)
                or not sample_id
                or not isinstance(media_id, str)
                or not media_id
                for sample_id, media_id in identities.items()
            )
            or len(set(identities.values())) != len(identities)
        ):
            raise RuntimeError("G3 media identity mapping must be nonempty and one-to-one")
        self.delegate = delegate
        self._media_identity_by_sample = identities

    def verify_media_identity(
        self,
        carrier_lock_key: str,
        media_facts: Mapping[str, tuple[str, float]],
    ) -> None:
        unknown = set(media_facts) - set(self._media_identity_by_sample)
        if not media_facts or unknown:
            raise RuntimeError(
                "G3 media identity facts must be a nonempty subset of the frozen runtime surface"
            )
        translated = {
            self._media_identity_by_sample[sample_id]: fact
            for sample_id, fact in media_facts.items()
        }
        self.delegate.verify_media_identity(carrier_lock_key, translated)

    def __getattr__(self, name: str) -> object:
        return getattr(self.delegate, name)


def _build_g3_gate(
    *,
    root: Path,
    values: Mapping[str, object],
    media_identity_by_sample: Mapping[str, str],
    gate_factory: object | None = None,
) -> _G3MediaIdentityGate:
    factory = gate_factory or FrozenCoreGate.for_study_repo
    if not callable(factory):
        raise RuntimeError("G3 gate factory must be callable")
    delegate = factory(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=str(RUNTIME_RECEIPT_RELPATH.relative_to("docs")),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=Path(str(values["model_materialization_root"])),
        d1_media_supplement_relpath=d1_media_supplement_relpath(values),
        d1_media_supplement_sha256=d1_media_supplement_sha256(values),
    )
    return _G3MediaIdentityGate(delegate, media_identity_by_sample)


def _run_m0(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    plan: ExecutionPlan,
    run_dir: Path,
    session_receipt_path: Path,
) -> dict[str, object]:
    surface = context["surface"]
    recovery = context["m0_recovery"]
    missing_ids = tuple(recovery["missing_ids"])
    if len(missing_ids) != SPLIT_COUNT - M0_RECOVERY_COMPLETED_COUNT:
        raise RuntimeError("G3 M0 recovery must contact exactly nine missing identities")
    missing = set(missing_ids)
    recovery_samples = tuple(
        sample for sample in surface.samples if sample.sample_id in missing
    )
    recovery_bindings = {
        sample_id: surface.packet_bindings[sample_id] for sample_id in missing_ids
    }
    if len(recovery_samples) != len(missing_ids):
        raise RuntimeError("G3 M0 recovery sample surface is incomplete")
    adapter = g3_flight.G3PilotAdapter(
        recovery_samples,
        phase=G3_M0_DIRECT_PHASE,
        registry_contract=context["registry_contract"],
    )
    client = _client(
        root=root,
        context=context,
        gate=gate,
        transport=transport,
        plan=plan,
        samples=recovery_samples,
        packet_bindings=recovery_bindings,
        run_dir=run_dir,
        prefix="g3m0r",
    )
    try:
        new_summary = run_direct_phase(
            adapter=adapter,
            core_client=client,
            split_id=g3_flight.G3_SPLIT_ID,
            speech_packet_bindings=recovery_bindings,
            slot_count=2,
            decoding_params=_decoding(context),
        )
    except Exception:
        client.close()
        raise
    client_summary = client.close()
    new_ids = tuple(sorted(row.sample_id for row in new_summary.results))
    if client_summary.get("request_count") != len(missing_ids) or new_ids != missing_ids:
        raise RuntimeError("G3 M0 recovery did not complete exactly the nine missing rows")
    new_documents = _trace_documents(run_dir / "transport-trace")
    documents = tuple(recovery["documents"]) + tuple(new_documents)
    trace_manifest_hash, trace_manifest = _write_combined_trace(run_dir, documents)
    combined = _validate_m0_recovery_trace(
        documents,
        trace_manifest,
        expected_ids=tuple(surface.tier_by_sample),
        expected_completed_count=SPLIT_COUNT,
    )
    summary = combined["summary"]
    if combined["missing_ids"]:
        raise RuntimeError("G3 M0 combined trace is not a complete 40-row surface")
    rows, cost = g3_flight.build_g3_m0_bundle_material(
        summary,
        documents,
        umbrella_lock_sha256=str(client_summary["cost"]["umbrella_lock_sha256"]),
    )
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, tuple({**row, "phase": G3_M0_DIRECT_PHASE} for row in rows))
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=trace_manifest_hash,
        cost=cost,
    )
    return {
        "summary": summary,
        "texts": {row.sample_id: row.final_response_text for row in summary.results},
        "manifest": manifest,
        "outputs": outputs,
        "client": client_summary,
        "recovery": {
            "prior_contacts": M0_RECOVERY_COMPLETED_COUNT,
            "new_contacts": len(missing_ids),
            "source_attempt_id": recovery["source_attempt_id"],
            "source_trace_sha256": recovery["source_trace_sha256"],
            "source_trace_manifest_sha256": recovery[
                "source_trace_manifest_sha256"
            ],
        },
    }


def _run_agent_phase(
    *,
    phase: str,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    plan: ExecutionPlan,
    adapter: object,
    packet_bindings: Mapping[str, Mapping[str, object]],
    run_dir: Path,
) -> dict[str, object]:
    samples = adapter.load_split(g3_flight.G3_SPLIT_ID)
    client = _client(
        root=root,
        context=context,
        gate=gate,
        transport=transport,
        plan=plan,
        samples=samples,
        packet_bindings=packet_bindings,
        run_dir=run_dir,
        prefix=f"g3{PHASE_SUFFIXES[phase]}",
    )
    sink = TraceSink(run_dir / "agent-trace", RUN_ID)
    try:
        summary = g3_flight.run_g3_agent_phase(
            phase=phase,
            data_root=root,
            plan=plan,
            adapter=adapter,
            core_client=client,
            knowledge_snapshot=context["snapshot"],
            speech_packet_bindings=packet_bindings,
            trace_sink=sink,
            slot_count=2,
            queue_depth=4,
            decoding_params=_decoding(context),
            registry_rows=(context["registry_rows"] if phase != G3_OBSERVATION_PHASE else ()),
        )
    except Exception:
        sink.close()
        client.close()
        raise
    agent_trace_hash = sink.close()
    client_summary = client.close()
    contact_counts = {row.sample_id: len(row.contacts) for row in summary.results}
    if sum(contact_counts.values()) > PHASE_CONTACT_CEILINGS[phase]:
        raise RuntimeError(f"{phase} exceeded its contact ceiling")
    return {
        "summary": summary,
        "texts": {row.sample_id: row.final_response_text for row in summary.results},
        "contact_counts": contact_counts,
        "agent_trace_hash": agent_trace_hash,
        "client": client_summary,
        "run_dir": run_dir,
    }


def _seal_composite(
    *,
    phase: str,
    texts: Mapping[str, str],
    source_result: Mapping[str, object],
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    run_dir: Path,
    session_receipt_path: Path,
) -> dict[str, object]:
    client_summary = source_result["client"]
    source_trace = Path(source_result["run_dir"]) / "agent-trace" / (
        f"{RUN_ID}.trace.jsonl"
    )
    source_trace_sha256 = _sha256_file(source_trace)
    source_by_id = {
        sample_id: {
            "action": phase,
            "source_agent_trace_manifest_sha256": source_result["agent_trace_hash"],
            "source_artifact_path": str(source_trace),
            "source_artifact_sha256": source_trace_sha256,
        }
        for sample_id in texts
    }
    sink = TraceSink(run_dir, RUN_ID)
    rows = g3_flight.emit_g3_use_rows(
        texts=texts,
        source_by_id=source_by_id,
        sink=sink,
        phase=phase,
    )
    trace_hash = sink.close()
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    cost = dict(client_summary["cost"])
    cost["tool_calls"] = 40
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        outputs_path=outputs,
        trace_manifest_hash=trace_hash,
        cost=cost,
    )
    return {
        **source_result,
        "texts": dict(texts),
        "outputs": outputs,
        "manifest": manifest,
    }


def _materialize_matched_recovery(
    *,
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    run_dir: Path,
) -> dict[str, object]:
    """Copy verified matched artifacts byte-for-byte into a score-only bundle."""

    recovery = context["matched_recovery"]
    source_by_id = {
        sample_id: {
            "action": G3_MATCHED_USE_PHASE,
            "source_agent_trace_manifest_sha256": (
                MATCHED_RECOVERY_AGENT_MANIFEST_SHA256
            ),
            "source_artifact_path": str(recovery["source_agent_trace"]),
            "source_artifact_sha256": MATCHED_RECOVERY_AGENT_TRACE_SHA256,
        }
        for sample_id in recovery["texts"]
    }
    sink = TraceSink(run_dir, RUN_ID)
    rows = g3_flight.emit_g3_use_rows(
        texts=recovery["texts"],
        source_by_id=source_by_id,
        sink=sink,
        phase=G3_MATCHED_USE_PHASE,
    )
    trace_hash = sink.close()
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    manifest = _build_completed_manifest(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=recovery["source_session_receipt"],
        outputs_path=outputs,
        trace_manifest_hash=trace_hash,
        cost=recovery["cost"],
        expected_attempt_state=ATTEMPT_STATE_NEVER_OPENED,
    )
    _write_json(
        run_dir / "recovery-receipt.json",
        {
            "source_attempt_id": MATCHED_RECOVERY_ATTEMPT_ID,
            "source_outputs_sha256": MATCHED_RECOVERY_OUTPUTS_SHA256,
            "source_agent_trace_sha256": MATCHED_RECOVERY_AGENT_TRACE_SHA256,
            "source_agent_trace_manifest_sha256": (
                MATCHED_RECOVERY_AGENT_MANIFEST_SHA256
            ),
            "source_composite_trace_sha256": MATCHED_RECOVERY_COMPOSITE_TRACE_SHA256,
            "source_composite_manifest_sha256": (
                MATCHED_RECOVERY_COMPOSITE_MANIFEST_SHA256
            ),
            "successor_outputs_sha256": _sha256_file(outputs),
            "successor_trace_manifest_sha256": trace_hash,
            "contacts_reused": sum(recovery["contact_counts"].values()),
            "repair_count": recovery["repair_count"],
            "repair_sample_ids": recovery["repair_sample_ids"],
            "new_attempt_state": ATTEMPT_STATE_NEVER_OPENED,
        },
    )
    return {
        "texts": dict(recovery["texts"]),
        "contact_counts": dict(recovery["contact_counts"]),
        "outputs": outputs,
        "manifest": manifest,
        "recovered": True,
    }


def _human_ledger_cells(phase: str, lock_sha256: str) -> dict[str, str]:
    return {
        "experiment_id": RUN_ID,
        "speech task/carrier": "Audio2Tool A2T-G3-PILOT-40 discovery",
        "changed axes": phase,
        "shared code revision": "receipt-pinned G3 OpenJiuwen launcher",
        "model rev": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
        "dataset rev": lock_sha256,
        "MLflow run": "not uploaded",
        "effectiveness": "unread before all three manifests seal",
        "reasonableness": "one complete verified 40-row official scorer job",
        "efficiency": "three whole-manifest jobs with three outer workers",
        "deviations": "none; no retries and no network-jitter testing",
        "decision": "apply frozen G3 gates after all jobs settle",
    }


def _run_parallel_scorers(
    *,
    mission_dir: Path,
    manifests: Mapping[str, Path],
    lock_sha256: str,
) -> dict[str, object]:
    if set(manifests) != {"m0", "matched", "shuffled"}:
        raise RuntimeError("official scoring requires exactly three G3 manifests")
    jobs = []
    for name in ("m0", "matched", "shuffled"):
        job = {
            "job_id": f"g3-{name}",
            "manifest": str(manifests[name]),
            "operation": "score" if name in {"m0", "matched"} else "finalize",
        }
        if name == "shuffled":
            cells = mission_dir / f"{name}-ledger-cells.json"
            _write_json(cells, _human_ledger_cells(name, lock_sha256))
            job["ledger_cells"] = str(cells)
        jobs.append(job)
    jobs_path = mission_dir / "official-score-jobs.jsonl"
    _write_jsonl(jobs_path, jobs)
    output_dir = mission_dir / "official-score"
    command = [
        "bash",
        str(REPO / "scripts/evaluate_parallel.sh"),
        "--per-job-operation",
        "--jobs",
        str(jobs_path),
        "--output-dir",
        str(output_dir),
        "--workers",
        "3",
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
    (mission_dir / "official-score.stdout.log").write_text(
        completed.stdout, encoding="utf-8", newline="\n"
    )
    (mission_dir / "official-score.stderr.log").write_text(
        completed.stderr, encoding="utf-8", newline="\n"
    )
    if completed.returncode != 0:
        raise RuntimeError(f"official scorer batch exited {completed.returncode}")
    summary = _read_json(output_dir / "batch-summary.json")
    if summary.get("failed") != 0 or summary.get("succeeded") != 3:
        raise RuntimeError("official scorer batch did not settle three jobs")
    return summary


def _official_surface(
    scores: Mapping[str, object], items: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    outer = scores.get("a2t-toolcall")
    rows = outer.get("per_sample") if isinstance(outer, Mapping) else None
    aggregate = outer.get("aggregate") if isinstance(outer, Mapping) else None
    expected_ids = {str(item["sample_id"]) for item in items}
    if not isinstance(rows, list) or not isinstance(aggregate, Mapping):
        raise RuntimeError("official score surface is malformed")
    by_id = {
        str(row.get("sample_id")): row for row in rows if isinstance(row, Mapping)
    }
    if len(by_id) != 40 or set(by_id) != expected_ids:
        raise RuntimeError("official score surface must contain the complete 40 rows")
    return {
        "by_id": by_id,
        "parse_count": sum(bool(row.get("parsed")) for row in by_id.values()),
        "exact_count": sum(float(row.get("exact_match", 0)) for row in by_id.values()),
        "tool_count": sum(float(row.get("tool_accuracy", 0)) for row in by_id.values()),
        "slot_f1": float(aggregate.get("slot_f1", 0.0)),
    }


def _grouped_ci(
    *,
    items: Sequence[Mapping[str, object]],
    left: Mapping[str, Mapping[str, object]],
    right: Mapping[str, Mapping[str, object]],
    selected_ids: Sequence[str] | None = None,
) -> dict[str, object]:
    selected = set(selected_ids or (str(item["sample_id"]) for item in items))
    groups: dict[str, list[str]] = defaultdict(list)
    for item in items:
        sample_id = str(item["sample_id"])
        if sample_id in selected:
            group = item.get("query_block")
            if not isinstance(group, str) or not group:
                raise RuntimeError("G3 item lacks query_block for grouped CI")
            groups[group].append(sample_id)
    group_ids = tuple(sorted(groups))

    def statistic(resampled: Sequence[str]) -> float:
        values = [
            float(left[sample_id].get("exact_match", 0))
            - float(right[sample_id].get("exact_match", 0))
            for group in resampled
            for sample_id in groups[group]
        ]
        return sum(values) / len(values)

    return paired_cluster_bootstrap(
        sample_ids=group_ids,
        statistic=statistic,
        n_replicates=10_000,
        seed=20260902,
        ci_level=0.9,
    ).as_json()


def _build_result(
    *,
    items: Sequence[Mapping[str, object]],
    selected_ids: Sequence[str],
    m0_scores: Mapping[str, object],
    matched_scores: Mapping[str, object],
    shuffled_scores: Mapping[str, object],
    matched_contact_counts: Mapping[str, int],
    shuffled_contact_counts: Mapping[str, int],
) -> dict[str, object]:
    m0 = _official_surface(m0_scores, items)
    matched = _official_surface(matched_scores, items)
    shuffled = _official_surface(shuffled_scores, items)
    selected = tuple(selected_ids)
    if len(selected) != 16 or set(shuffled_contact_counts) != set(selected):
        raise RuntimeError("G3 shuffled read requires the frozen selected 16")

    def summary(surface: Mapping[str, object]) -> dict[str, object]:
        return {
            "parse_count": int(surface["parse_count"]),
            "exact_count": int(surface["exact_count"]),
            "tool_count": int(surface["tool_count"]),
            "slot_f1": float(surface["slot_f1"]),
        }

    def selected_summary(surface: Mapping[str, object]) -> dict[str, object]:
        rows = [surface["by_id"][sample_id] for sample_id in selected]
        return {
            "samples": len(rows),
            "parse_count": sum(bool(row.get("parsed")) for row in rows),
            "exact_count": int(sum(float(row.get("exact_match", 0)) for row in rows)),
            "tool_count": int(sum(float(row.get("tool_accuracy", 0)) for row in rows)),
            "mean_slot_f1": sum(float(row.get("slot_f1", 0.0)) for row in rows)
            / len(rows),
        }

    def paired_outcomes(
        left: Mapping[str, object],
        right: Mapping[str, object],
        sample_ids: Sequence[str],
        metric: str,
    ) -> dict[str, int]:
        differences = [
            int(float(left["by_id"][sample_id].get(metric, 0)))
            - int(float(right["by_id"][sample_id].get(metric, 0)))
            for sample_id in sample_ids
        ]
        wins = sum(value > 0 for value in differences)
        losses = sum(value < 0 for value in differences)
        return {
            "wins": wins,
            "losses": losses,
            "ties": len(differences) - wins - losses,
            "net": sum(differences),
        }

    per_tier: dict[str, object] = {}
    for tier in CANONICAL_TIERS:
        tier_ids = [
            str(item["sample_id"]) for item in items if item.get("tier") == tier
        ]
        per_tier[tier] = {
            name: {
                "exact_count": sum(
                    float(surface["by_id"][sample_id].get("exact_match", 0))
                    for sample_id in tier_ids
                ),
                "tool_count": sum(
                    float(surface["by_id"][sample_id].get("tool_accuracy", 0))
                    for sample_id in tier_ids
                ),
            }
            for name, surface in (("m0", m0), ("matched", matched), ("shuffled", shuffled))
        }
    matched_selected = selected_summary(matched)
    shuffled_selected = selected_summary(shuffled)
    all_ids = tuple(str(item["sample_id"]) for item in items)
    matched_m0_exact = paired_outcomes(matched, m0, all_ids, "exact_match")
    matched_m0_tool = paired_outcomes(matched, m0, all_ids, "tool_accuracy")
    paired_exact = paired_outcomes(matched, shuffled, selected, "exact_match")
    paired_tool = paired_outcomes(matched, shuffled, selected, "tool_accuracy")
    bootstrap = _grouped_ci(
        items=items,
        left=matched["by_id"],
        right=m0["by_id"],
    )
    control_bootstrap = _grouped_ci(
        items=items,
        left=matched["by_id"],
        right=shuffled["by_id"],
        selected_ids=selected,
    )
    return {
        "schema": "saea-a2t-g3-plain-english-result-v2",
        "absolute": {
            "m0": summary(m0),
            "matched": summary(matched),
            "shuffled_composite_40": summary(shuffled),
        },
        "paired": {
            "matched_minus_m0_exact": int(matched["exact_count"] - m0["exact_count"]),
            "matched_minus_m0_tool": int(matched["tool_count"] - m0["tool_count"]),
            "matched_vs_m0_exact": matched_m0_exact,
            "matched_vs_m0_tool": matched_m0_tool,
        },
        "selected16": {
            "scope": "preregistered-selected16-only",
            "sample_ids": list(selected),
            "matched": matched_selected,
            "shuffled": shuffled_selected,
            "paired_exact": paired_exact,
            "paired_tool": paired_tool,
            "grouped_ci90": control_bootstrap,
        },
        "hard_repair_counts": {
            "matched": sum(count == 2 for count in matched_contact_counts.values()),
            "shuffled": sum(count == 2 for count in shuffled_contact_counts.values()),
        },
        "per_tier_scope": "40-row composite arms; not the selected16 control read",
        "per_tier": per_tier,
        "bootstrap": bootstrap,
        "gates": {
            "matched_parse_at_least_39": int(matched["parse_count"]) >= 39,
            "matched_exact_at_least_36": int(matched["exact_count"]) >= 36,
            "matched_tool_at_least_38": int(matched["tool_count"]) >= 38,
            "matched_slot_f1_at_least_0_90": float(matched["slot_f1"]) >= 0.90,
            "matched_minus_shuffled_exact_at_least_5": paired_exact["net"] >= 5,
            "matched_minus_shuffled_ci90_lower_positive": float(control_bootstrap["ci_low"]) > 0,
        },
    }


def _load_scores(manifest: Path) -> dict[str, object]:
    return Q._load_final_scores(manifest)


def _load_batch_scores(path: Path) -> dict[str, object]:
    document = _read_json(path)
    scores = document.get("scores")
    if document.get("verified") is not True:
        raise RuntimeError("official batch score result is not verified")
    if isinstance(scores, Mapping):
        normalized: dict[str, object] = {}
        for name, value in scores.items():
            if not isinstance(name, str) or not isinstance(value, Mapping):
                raise RuntimeError("official inline score result is malformed")
            if "aggregate" in value or "per_sample" in value:
                normalized[name] = dict(value)
            else:
                normalized[name] = {"per_sample": None, "aggregate": dict(value)}
        return normalized
    if isinstance(scores, str) and scores:
        scores_path = Path(scores)
        if not scores_path.is_absolute():
            scores_path = Path(path).parent / scores_path
        loaded = _read_json(scores_path)
        if document.get("attempt_state") != "FINALIZED":
            raise RuntimeError("official score path requires a FINALIZED result")
        return loaded
    raise RuntimeError("official batch score result is malformed")


def _stop_service(session: object, runtime_receipt: object, receipt_path: Path) -> None:
    stop_session(
        session,
        runtime_receipt=runtime_receipt,
        runtime_root=RUNTIME_ROOT,
        force_after_timeout=True,
        receipt_path=receipt_path,
    )


def _prepare_recovered_observations(
    *,
    observation_summary: object,
    surface: object,
    corpus: object,
    sample_ids: Sequence[str],
) -> tuple[dict[str, str], dict[str, object], dict[str, object]]:
    """Normalize once, then share the exact OBS text with routing and USE."""

    representation_flags: dict[str, dict[str, bool]] = {}
    observations = g3_flight.normalize_observation_texts(
        observation_summary,
        dialogue_sample_ids=surface.derived_dialogue_sample_ids,
        representation_flags=representation_flags,
    )
    routes = g3_flight.build_packet_routes(
        observation_summary,
        corpus=corpus,
        detailed_tool_limit=32,
        dialogue_sample_ids=surface.derived_dialogue_sample_ids,
        normalized_observation_texts=observations,
    )
    route_report = _validate_packet_routes(
        routes,
        sample_ids,
        representation_flags,
    )
    return observations, routes, route_report


def _offline_full_score(
    *,
    bundle: object,
    recorded_scores: Mapping[str, object],
    context: Mapping[str, object],
) -> dict[str, object]:
    """Reconstruct per-sample rows locally and cross-check the recorded aggregate."""

    outputs_path = getattr(bundle, "outputs_path", None)
    if not isinstance(outputs_path, Path):
        raise RuntimeError("offline score reconstruction requires verified outputs")
    full = score_audio2tool_outputs(
        outputs_path,
        context["lock"],
        Path(context["data_root"]),
    )
    recorded = recorded_scores.get("a2t-toolcall")
    aggregate = recorded.get("aggregate") if isinstance(recorded, Mapping) else None
    if not isinstance(aggregate, Mapping) or full.get("aggregate") != dict(aggregate):
        raise RuntimeError("offline per-sample reconstruction disagrees with official aggregate")
    return {"a2t-toolcall": full}


def _verified_agent_contact_counts(
    trace_dir: Path,
    *,
    expected_ids: Sequence[str],
) -> dict[str, int]:
    """Count contacts from an agent trace already artifact-bound by a bundle."""

    expected = set(expected_ids)
    counts: Counter[str] = Counter()
    for document in _trace_documents(trace_dir):
        if document.get("channel") != "MODEL_REQUEST":
            continue
        outer = document.get("payload")
        payload = outer.get("payload") if isinstance(outer, Mapping) else None
        if not isinstance(payload, Mapping):
            raise RuntimeError("verified Agent request payload is malformed")
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        sample_id = payload.get("sample_id")
        if (
            not isinstance(sample_id, str)
            or sample_id not in expected
            or outer.get("payload_sha256") != hashlib.sha256(canonical).hexdigest()
        ):
            raise RuntimeError("verified Agent request identity or hash drift")
        counts[sample_id] += 1
    if set(counts) != expected or any(value not in {1, 2} for value in counts.values()):
        raise RuntimeError("verified Agent contact surface is incomplete")
    return dict(sorted(counts.items()))


def _postprocess_existing(root: Path) -> Mapping[str, object]:
    """Assemble the completed G3 result offline from the 182038Z artifacts."""

    context = _static_preflight(root)
    context["data_root"] = Path(root)
    mission_dir = Path(root) / POSTPROCESS_FLIGHT_RELPATH
    official_dir = mission_dir / "official-score"
    pinned = (
        (mission_dir / "failure-receipt.json", POSTPROCESS_FAILURE_SHA256),
        (official_dir / "batch-summary.json", POSTPROCESS_BATCH_SHA256),
        (official_dir / "g3-m0.score.json", POSTPROCESS_M0_SCORE_SHA256),
        (official_dir / "g3-matched.score.json", POSTPROCESS_MATCHED_SCORE_SHA256),
        (official_dir / "g3-shuffled.score.json", POSTPROCESS_SHUFFLED_SCORE_SHA256),
    )
    for path, digest in pinned:
        _require_hash(path, digest, f"postprocess {path.name}")

    failure = _read_json(mission_dir / "failure-receipt.json")
    if failure.get("error") != "RuntimeError('official score surface is malformed')":
        raise RuntimeError("postprocess source failure identity drift")
    batch = _read_json(official_dir / "batch-summary.json")
    jobs = batch.get("jobs")
    if (
        batch.get("failed") != 0
        or batch.get("succeeded") != 3
        or not isinstance(jobs, list)
        or [(row.get("job_id"), row.get("operation")) for row in jobs]
        != [("g3-m0", "score"), ("g3-matched", "score"), ("g3-shuffled", "finalize")]
    ):
        raise RuntimeError("postprocess official score batch drift")
    expected_result_hashes = {
        "g3-m0": POSTPROCESS_M0_SCORE_SHA256,
        "g3-matched": POSTPROCESS_MATCHED_SCORE_SHA256,
        "g3-shuffled": POSTPROCESS_SHUFFLED_SCORE_SHA256,
    }
    for row in jobs:
        if row.get("status") != "succeeded" or row.get("result_sha256") != (
            expected_result_hashes[row["job_id"]]
        ):
            raise RuntimeError("postprocess official score job hash drift")

    score_paths = {
        name: official_dir / f"g3-{name}.score.json"
        for name in ("m0", "matched", "shuffled")
    }
    score_documents = {name: _read_json(path) for name, path in score_paths.items()}
    bundles = {
        name: verify_bundle(Path(str(document["manifest"])))
        for name, document in score_documents.items()
    }
    if (
        any(len(bundle.outputs_rows) != SPLIT_COUNT for bundle in bundles.values())
        or bundles["shuffled"].attempt_state != "FINALIZED"
    ):
        raise RuntimeError("postprocess verified bundle state drift")
    recorded = {name: _load_batch_scores(path) for name, path in score_paths.items()}
    full_scores = {
        "m0": _offline_full_score(
            bundle=bundles["m0"], recorded_scores=recorded["m0"], context=context
        ),
        "matched": _offline_full_score(
            bundle=bundles["matched"],
            recorded_scores=recorded["matched"],
            context=context,
        ),
        "shuffled": recorded["shuffled"],
    }
    shuffled_rows = full_scores["shuffled"].get("a2t-toolcall")
    if (
        not isinstance(shuffled_rows, Mapping)
        or not isinstance(shuffled_rows.get("per_sample"), list)
        or len(shuffled_rows["per_sample"]) != SPLIT_COUNT
    ):
        raise RuntimeError("postprocess shuffled score surface is incomplete")

    selected_ids = tuple(context["selected_ids"])
    shuffled_contacts = _verified_agent_contact_counts(
        mission_dir / "shuffled" / "agent-trace",
        expected_ids=selected_ids,
    )
    matched_contacts = context["matched_recovery"]["contact_counts"]
    result = _build_result(
        items=context["items"],
        selected_ids=selected_ids,
        m0_scores=full_scores["m0"],
        matched_scores=full_scores["matched"],
        shuffled_scores=full_scores["shuffled"],
        matched_contact_counts=matched_contacts,
        shuffled_contact_counts=shuffled_contacts,
    )
    result["analysis_only_per_sample_reconstruction"] = {
        "function": "score_audio2tool_outputs",
        "official_aggregate_crosscheck": True,
        "model_contacts": 0,
        "network_contacts": 0,
        "new_scorer_processes": 0,
        "reason": "score-only CLI artifacts intentionally retained aggregate rows only",
    }
    _write_json(mission_dir / "result.json", result)
    route_receipt = _read_json(mission_dir / "obs" / "observation-receipt.json")
    attempts = failure.get("phase_attempt_ids")
    receipt = {
        "schema": "saea-a2t-g3-plain-english-flight-receipt-v2",
        "run_id": RUN_ID,
        "status": "SCORED",
        "flight_study_commit": bundles["shuffled"].manifest.get("study_commit"),
        "postprocess_study_commit": context["commit"],
        "mission_dir": str(mission_dir),
        "phase_attempt_ids": attempts,
        "phase_contact_counts": {
            G3_M0_DIRECT_PHASE: 40,
            G3_OBSERVATION_PHASE: 40,
            G3_MATCHED_USE_PHASE: sum(matched_contacts.values()),
            G3_SHUFFLED_USE_PHASE: sum(shuffled_contacts.values()),
        },
        "cumulative_model_contacts": 148,
        "route_report": route_receipt.get("route_report"),
        "official_score": batch,
        "postprocess_existing": True,
        "postprocess_model_contacts": 0,
        "postprocess_network_contacts": 0,
        "postprocess_scorer_processes": 0,
        "superseded_failure_sha256": POSTPROCESS_FAILURE_SHA256,
        "result_path": str(mission_dir / "result.json"),
        "result_sha256": _sha256_file(mission_dir / "result.json"),
        "network_jitter_testing": False,
        "retries": 0,
    }
    _write_json(mission_dir / "flight-receipt.json", receipt)
    return receipt


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stamp_lower = stamp.lower()
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}"
    mission_dir.mkdir(parents=True, exist_ok=False)
    attempts = _phase_attempt_ids(stamp_lower)
    attempts[G3_M0_DIRECT_PHASE] = COMPLETED_FLIGHT_M0_ATTEMPT_ID
    attempts[G3_OBSERVATION_PHASE] = COMPLETED_FLIGHT_OBS_ATTEMPT_ID
    plans = {
        phase: _execution_plan(phase, attempts[phase])
        for phase in (G3_MATCHED_USE_PHASE, G3_SHUFFLED_USE_PHASE)
    }
    for phase in PHASES:
        phase_dir = mission_dir / PHASE_SUFFIXES[phase]
        phase_dir.mkdir()
        if phase in plans:
            _write_json(phase_dir / "execution-plan.json", asdict(plans[phase]))

    completed_flight = context["completed_flight"]
    m0 = completed_flight["m0"]
    observation = completed_flight["observation"]
    surface = context["surface"]
    observations, routes, route_report = _prepare_recovered_observations(
        observation_summary=observation["summary"],
        surface=surface,
        corpus=context["corpus"],
        sample_ids=context["sample_ids"],
    )
    if route_report["role_labels_missing"] != 5 or route_report["normalized_non_ascii"] != 1:
        raise RuntimeError("completed-flight OBS representation failure counts drift")
    matched = _materialize_matched_recovery(
        root=root,
        context=context,
        plan=plans[G3_MATCHED_USE_PHASE],
        run_dir=mission_dir / "matched",
    )
    reused_contact_accounting = {
        **completed_flight["contact_accounting"],
        "matched": sum(matched["contact_counts"].values()),
        "cumulative_before_shuffled": 125,
    }
    _write_json(
        mission_dir / "m0" / "recovery-receipt.json",
        {
            "source_manifest": str(m0["manifest"]),
            "source_manifest_sha256": COMPLETED_FLIGHT_M0_MANIFEST_SHA256,
            "source_outputs_sha256": COMPLETED_FLIGHT_M0_OUTPUTS_SHA256,
            "source_trace_sha256": COMPLETED_FLIGHT_M0_TRACE_SHA256,
            "contact_accounting": reused_contact_accounting,
        },
    )
    _write_json(
        mission_dir / "obs" / "observation-receipt.json",
        {
            "phase": G3_OBSERVATION_PHASE,
            "source_attempt_id": COMPLETED_FLIGHT_OBS_ATTEMPT_ID,
            "contacts_reused": SPLIT_COUNT,
            "route_report": route_report,
            "source_agent_trace_sha256": COMPLETED_FLIGHT_OBS_TRACE_SHA256,
            "source_agent_trace_manifest_sha256": (
                COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_SHA256
            ),
        },
    )

    values = context["composed"].values
    runtime_receipt = load_runtime_receipt(REPO / RUNTIME_RECEIPT_RELPATH)
    model_root = Path(str(values["model_materialization_root"]))
    gate = _build_g3_gate(
        root=root,
        values=values,
        media_identity_by_sample=context["surface"].media_identity_by_sample,
    )
    gate.assert_model_touch_allowed(plans[G3_SHUFFLED_USE_PHASE], full_hash=True)
    parsed_url = urlparse(str(values["base_url"]))
    if parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.port is None:
        raise RuntimeError("G3 decoder must use an explicit loopback port")

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
        selected_ids = tuple(context["selected_ids"])
        selected = set(selected_ids)
        selected_samples = tuple(
            sample for sample in surface.samples if sample.sample_id in selected
        )
        selected_bindings = {
            sample_id: surface.packet_bindings[sample_id] for sample_id in selected_ids
        }
        shuffled_adapter = g3_flight.G3PilotAdapter(
            selected_samples,
            phase=G3_SHUFFLED_USE_PHASE,
            observation_by_sample={sample_id: observations[sample_id] for sample_id in selected_ids},
            packet_by_sample={sample_id: routes[sample_id].shuffled_packet for sample_id in selected_ids},
        )
        shuffled_raw = _run_agent_phase(
            phase=G3_SHUFFLED_USE_PHASE,
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            plan=plans[G3_SHUFFLED_USE_PHASE],
            adapter=shuffled_adapter,
            packet_bindings=selected_bindings,
            run_dir=mission_dir / "shuffled",
        )
        shuffled_texts = build_resend_composite_texts(
            matched["texts"],
            selected_ids=selected_ids,
            resend_responses=shuffled_raw["texts"],
        )
        shuffled = _seal_composite(
            phase=G3_SHUFFLED_USE_PHASE,
            texts=shuffled_texts,
            source_result=shuffled_raw,
            root=root,
            context=context,
            plan=plans[G3_SHUFFLED_USE_PHASE],
            run_dir=mission_dir / "shuffled",
            session_receipt_path=session_receipt,
        )

        _stop_service(session, runtime_receipt, stop_receipt)
        session = None
        lock_sha256 = str(m0["cost"]["umbrella_lock_sha256"])
        score_summary = _run_parallel_scorers(
            mission_dir=mission_dir,
            manifests={
                "m0": m0["manifest"],
                "matched": matched["manifest"],
                "shuffled": shuffled["manifest"],
            },
            lock_sha256=lock_sha256,
        )
        score_paths = {
            name: mission_dir / "official-score" / f"g3-{name}.score.json"
            for name in ("m0", "matched", "shuffled")
        }
        recorded_scores = {
            name: _load_batch_scores(path) for name, path in score_paths.items()
        }
        score_context = {**context, "data_root": Path(root)}
        full_scores = {
            "m0": _offline_full_score(
                bundle=verify_bundle(m0["manifest"]),
                recorded_scores=recorded_scores["m0"],
                context=score_context,
            ),
            "matched": _offline_full_score(
                bundle=verify_bundle(matched["manifest"]),
                recorded_scores=recorded_scores["matched"],
                context=score_context,
            ),
            "shuffled": recorded_scores["shuffled"],
        }
        result = _build_result(
            items=context["items"],
            selected_ids=selected_ids,
            m0_scores=full_scores["m0"],
            matched_scores=full_scores["matched"],
            shuffled_scores=full_scores["shuffled"],
            matched_contact_counts=matched["contact_counts"],
            shuffled_contact_counts=shuffled["contact_counts"],
        )
        result["analysis_only_per_sample_reconstruction"] = {
            "function": "score_audio2tool_outputs",
            "official_aggregate_crosscheck": True,
            "model_contacts": 0,
            "network_contacts": 0,
            "new_scorer_processes": 0,
            "reason": "score-only CLI artifacts intentionally retained aggregate rows only",
        }
        _write_json(mission_dir / "result.json", result)
        receipt = {
            "schema": "saea-a2t-g3-plain-english-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SCORED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "phase_attempt_ids": attempts,
            "phase_contact_counts": {
                G3_M0_DIRECT_PHASE: 40,
                G3_OBSERVATION_PHASE: sum(observation["contact_counts"].values()),
                G3_MATCHED_USE_PHASE: sum(matched["contact_counts"].values()),
                G3_SHUFFLED_USE_PHASE: sum(shuffled["contact_counts"].values()),
            },
            "reused_contact_accounting": reused_contact_accounting,
            "route_report": route_report,
            "official_score": score_summary,
            "result_path": str(mission_dir / "result.json"),
            "result_sha256": _sha256_file(mission_dir / "result.json"),
            "network_jitter_testing": False,
            "retries": 0,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        for phase, plan in plans.items():
            attempt_id = plan.attempt_id
            abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _write_json(
            mission_dir / "failure-receipt.json",
            {"run_id": RUN_ID, "error": repr(error), "phase_attempt_ids": attempts},
        )
        raise
    finally:
        if session is not None:
            _stop_service(session, runtime_receipt, stop_receipt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--postprocess-existing", action="store_true")
    args = parser.parse_args(argv)
    root = data_root()
    if args.postprocess_existing:
        print(json.dumps(_postprocess_existing(root), indent=2, sort_keys=True))
        return 0
    if args.preflight_only:
        context = _static_preflight(root)
        print(
            json.dumps(
                {
                    "preflight": "passed",
                    "run_id": RUN_ID,
                    "study_commit": context["commit"],
                    "samples": len(context["sample_ids"]),
                    "slot_count": context["geometry"]["slot_count"],
                    "corpus_utf8_bytes": context["route_build"]["corpus_utf8_bytes"],
                    "official_score_workers": 3,
                    "contacts": {
                        "model": 0,
                        "network": 0,
                        "scorer": 0,
                        "tokenizer": 0,
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    print(json.dumps(_launch(root), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
