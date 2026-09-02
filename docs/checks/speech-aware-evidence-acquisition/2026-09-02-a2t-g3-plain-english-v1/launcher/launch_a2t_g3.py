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
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_bundle import (  # noqa: E402
    build_resend_composite_texts,
    build_use_composite_texts,
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
    "operation": "finalize",
    "workers": 3,
    "official_scorer_modified": False,
    "processes_per_job": 1,
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "g3-m0-direct",
            "input": "one complete 40-row manifest",
            "row_count": 40,
        },
        {
            "job_id": "g3-matched-use",
            "input": "one complete 40-row manifest",
            "row_count": 40,
        },
        {
            "job_id": "g3-shuffled-use",
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
        or plan.get("operation") != "finalize"
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
        ):
            raise RuntimeError("every scorer input must be one complete 40-row manifest")
    return dict(plan)


def _validate_packet_routes(
    routes: Mapping[str, object], sample_ids: Sequence[str]
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
    return {"route_count": 40, "maximum_packet_utf8_bytes": maximum}


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
        identity_hash=SPLIT_IDENTITY_SHA256,
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
    if bundle.attempt_state != "OPENED" or len(bundle.outputs_rows) != 40:
        raise RuntimeError("G3 phase did not seal a complete OPENED manifest")
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
        carrier_root=context["carrier_root"],
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
    adapter = g3_flight.G3PilotAdapter(
        surface.samples,
        phase=G3_M0_DIRECT_PHASE,
        registry_contract=context["registry_contract"],
    )
    client = _client(
        root=root,
        context=context,
        gate=gate,
        transport=transport,
        plan=plan,
        samples=surface.samples,
        packet_bindings=surface.packet_bindings,
        run_dir=run_dir,
        prefix="g3m0",
    )
    try:
        summary = g3_flight.run_g3_m0_phase(
            adapter=adapter,
            core_client=client,
            speech_packet_bindings=surface.packet_bindings,
            slot_count=2,
            decoding_params=_decoding(context),
        )
    except Exception:
        client.close()
        raise
    client_summary = client.close()
    if client_summary.get("request_count") != 40:
        raise RuntimeError("G3 M0 did not make exactly 40 contacts")
    documents = Q._trace_documents(run_dir / "transport-trace")
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
        trace_manifest_hash=str(client_summary["trace_manifest_hash"]),
        cost=cost,
    )
    return {
        "summary": summary,
        "texts": {row.sample_id: row.final_response_text for row in summary.results},
        "manifest": manifest,
        "outputs": outputs,
        "client": client_summary,
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
    source_by_id = {
        sample_id: {
            "action": phase,
            "source_agent_trace_manifest_sha256": source_result["agent_trace_hash"],
        }
        for sample_id in texts
    }
    sink = TraceSink(run_dir / "composite-trace", RUN_ID)
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
        cells = mission_dir / f"{name}-ledger-cells.json"
        _write_json(cells, _human_ledger_cells(name, lock_sha256))
        jobs.append(
            {
                "job_id": f"g3-{name}",
                "manifest": str(manifests[name]),
                "ledger_cells": str(cells),
            }
        )
    jobs_path = mission_dir / "official-score-jobs.jsonl"
    _write_jsonl(jobs_path, jobs)
    output_dir = mission_dir / "official-score"
    command = [
        "bash",
        str(REPO / "scripts/evaluate_parallel.sh"),
        "--finalize",
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
    matched_selected = sum(
        float(matched["by_id"][sample_id].get("exact_match", 0)) for sample_id in selected
    )
    shuffled_selected = sum(
        float(shuffled["by_id"][sample_id].get("exact_match", 0)) for sample_id in selected
    )
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
        "schema": "saea-a2t-g3-plain-english-result-v1",
        "absolute": {
            "m0": summary(m0),
            "matched": summary(matched),
            "shuffled": summary(shuffled),
        },
        "paired": {
            "matched_minus_m0_exact": int(matched["exact_count"] - m0["exact_count"]),
            "matched_minus_m0_tool": int(matched["tool_count"] - m0["tool_count"]),
        },
        "selected16": {
            "matched_exact": int(matched_selected),
            "shuffled_exact": int(shuffled_selected),
            "matched_minus_shuffled_exact": int(matched_selected - shuffled_selected),
            "grouped_ci90": control_bootstrap,
        },
        "hard_repair_counts": {
            "matched": sum(count == 2 for count in matched_contact_counts.values()),
            "shuffled": sum(count == 2 for count in shuffled_contact_counts.values()),
        },
        "per_tier": per_tier,
        "bootstrap": bootstrap,
        "gates": {
            "matched_parse_at_least_39": int(matched["parse_count"]) >= 39,
            "matched_exact_at_least_36": int(matched["exact_count"]) >= 36,
            "matched_tool_at_least_38": int(matched["tool_count"]) >= 38,
            "matched_slot_f1_at_least_0_90": float(matched["slot_f1"]) >= 0.90,
            "matched_minus_shuffled_exact_at_least_5": matched_selected - shuffled_selected >= 5,
            "matched_minus_shuffled_ci90_lower_positive": float(control_bootstrap["ci_low"]) > 0,
        },
    }


def _load_scores(manifest: Path) -> dict[str, object]:
    return Q._load_final_scores(manifest)


def _stop_service(session: object, runtime_receipt: object, receipt_path: Path) -> None:
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
    stamp_lower = stamp.lower()
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}"
    mission_dir.mkdir(parents=True, exist_ok=False)
    attempts = _phase_attempt_ids(stamp_lower)
    plans = {phase: _execution_plan(phase, attempts[phase]) for phase in PHASES}
    for phase, plan in plans.items():
        phase_dir = mission_dir / PHASE_SUFFIXES[phase]
        phase_dir.mkdir()
        _write_json(phase_dir / "execution-plan.json", asdict(plan))

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
    for plan in plans.values():
        gate.assert_model_touch_allowed(plan, full_hash=True)
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
        m0 = _run_m0(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            plan=plans[G3_M0_DIRECT_PHASE],
            run_dir=mission_dir / "m0",
            session_receipt_path=session_receipt,
        )

        surface = context["surface"]
        obs_adapter = g3_flight.G3PilotAdapter(
            surface.samples,
            phase=G3_OBSERVATION_PHASE,
            dialogue_sample_ids=surface.derived_dialogue_sample_ids,
        )
        observation = _run_agent_phase(
            phase=G3_OBSERVATION_PHASE,
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            plan=plans[G3_OBSERVATION_PHASE],
            adapter=obs_adapter,
            packet_bindings=surface.packet_bindings,
            run_dir=mission_dir / "obs",
        )
        routes = g3_flight.build_packet_routes(
            observation["summary"],
            corpus=context["corpus"],
            detailed_tool_limit=32,
            dialogue_sample_ids=surface.derived_dialogue_sample_ids,
        )
        route_report = _validate_packet_routes(routes, context["sample_ids"])
        _write_json(
            mission_dir / "obs" / "observation-receipt.json",
            {
                "phase": G3_OBSERVATION_PHASE,
                "attempt_id": attempts[G3_OBSERVATION_PHASE],
                "contacts": sum(observation["contact_counts"].values()),
                "route_report": route_report,
                "agent_trace_manifest_sha256": observation["agent_trace_hash"],
                "transport_trace_manifest_sha256": observation["client"]["trace_manifest_hash"],
            },
        )
        if not abort_attempt_if_opened(
            root,
            RUN_ID,
            attempts[G3_OBSERVATION_PHASE],
            reason="task-blind OBS and all forty bounded packet routes sealed",
        ):
            raise RuntimeError("OBS attempt did not reach terminal ABORTED state")

        observations = observation["texts"]
        matched_adapter = g3_flight.G3PilotAdapter(
            surface.samples,
            phase=G3_MATCHED_USE_PHASE,
            observation_by_sample=observations,
            packet_by_sample={sample_id: routes[sample_id].matched_packet for sample_id in observations},
        )
        matched_raw = _run_agent_phase(
            phase=G3_MATCHED_USE_PHASE,
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            plan=plans[G3_MATCHED_USE_PHASE],
            adapter=matched_adapter,
            packet_bindings=surface.packet_bindings,
            run_dir=mission_dir / "matched",
        )
        matched_texts = build_use_composite_texts(
            m0_texts=m0["texts"],
            use_texts=matched_raw["texts"],
            routed_ids=context["sample_ids"],
        )
        matched = _seal_composite(
            phase=G3_MATCHED_USE_PHASE,
            texts=matched_texts,
            source_result=matched_raw,
            root=root,
            context=context,
            plan=plans[G3_MATCHED_USE_PHASE],
            run_dir=mission_dir / "matched",
            session_receipt_path=session_receipt,
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
        lock_sha256 = str(m0["client"]["cost"]["umbrella_lock_sha256"])
        score_summary = _run_parallel_scorers(
            mission_dir=mission_dir,
            manifests={
                "m0": m0["manifest"],
                "matched": matched["manifest"],
                "shuffled": shuffled["manifest"],
            },
            lock_sha256=lock_sha256,
        )
        result = _build_result(
            items=context["items"],
            selected_ids=selected_ids,
            m0_scores=_load_scores(m0["manifest"]),
            matched_scores=_load_scores(matched["manifest"]),
            shuffled_scores=_load_scores(shuffled["manifest"]),
            matched_contact_counts=matched["contact_counts"],
            shuffled_contact_counts=shuffled["contact_counts"],
        )
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
        for phase, attempt_id in attempts.items():
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
