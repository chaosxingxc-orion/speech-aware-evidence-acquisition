#!/usr/bin/env python3
"""Preflight and launch the G4 structured-state executable-microground SE16 arm.

The preflight is local and contact-free.  Only ``--run`` starts the pinned
loopback service.  This launcher seals model outputs without scoring or
interpreting them; the registered whole-manifest scorer remains a later step.
"""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
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
    load_tool_registry,
)
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.a2t_observation_state_organizer import (  # noqa: E402
    build_external_state_receipt,
    organize_sealed_observation,
)
from speech_aware_evidence_acquisition.rails.a2t_semantic_microground import (  # noqa: E402
    route_semantic_microground,
)
from speech_aware_evidence_acquisition.rails.knowledge import (  # noqa: E402
    KnowledgeSnapshot,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_factor_top1_bundle import (  # noqa: E402
    emit_composite_rows,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g4_microground_flight import (  # noqa: E402
    G4_MICROGROUND_SE_PHASE,
    G4_PACKET_UTF8_BYTE_CAP,
    G4_QUEUE_DEPTH,
    G4_SCREEN_SPLIT_ID,
    G4_SE_STATE_UTF8_BYTE_CAP,
    G4_SLOT_COUNT,
    G4MicrogroundAdapter,
    run_g4_microground_phase,
)


def _load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen helper {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


G3 = _load_module(
    REPO
    / "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g3-plain-english-v1/launcher/launch_a2t_g3.py",
    "saea_g4_se16_frozen_g3_helper",
)
CARD_BUILDER = _load_module(
    REPO / "scripts/build_a2t_g4_semantic_cards.py",
    "saea_g4_se16_card_builder",
)

RUN_ID = "SAEA-A2T-G4-STRUCTURED-EXECUTABLE-MICROGROUND-SE16-V1"
RUNTIME_ROOT = Path("/home/chao")
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g3-pilot-40"
BASELINE_FRAGMENT = "a2t-g4-executable-microground-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g4-executable-microground-screen-16-v1"

EXPERIMENT_CONFIG_SHA256 = (
    "f0b942d05121f14ee433371c730b77d155fb5ae0cfdb80b5ef110f862bcbacf7"
)
COMPOSED_CONFIG_SHA256 = (
    "04f02dfd3c620351799947ef6582ef5b5064a80591bca07fc6519a717887d8f9"
)
PROTOCOL_SHA256 = (
    "041b87305f8357ffb19487ac3f8a76a7da78f37fdad0ea4dca4399c13b733cf4"
)
SELECTED_RECEIPT_SHA256 = (
    "41a14ab576d7a428dd9849f26432e2c4998371b9f601189a1d558d694a12c884"
)
SELECTED_PARTITION_SHA256 = (
    "7590dfef54b42601c266f2bb325faee073143a575beeccd0c33cc8baf13aed45"
)
SELECTED_RUN_SHA256 = (
    "f9e3055f7eceff49405a192806be933db9bfcab150a1778bb3ddd937a8f57269"
)
PLANNED_AUDIO_SECONDS = 179

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
SELECTED_IDS = tuple(
    sorted(
        (
            "tier1_direct:003713",
            "tier1_direct:000074",
            "tier2_parametric:001869",
            "tier2_parametric:000568",
            "tier3_multi_intent:001732",
            "tier3_multi_intent:002166",
            "tier4_implicit:001759",
            "tier4_implicit:001628",
            "tier5_needle:001059",
            "tier5_needle:002546",
            "tier6_correction:001056",
            "tier6_correction:003671",
            "tier7_multiturn:001590",
            "tier7_multiturn:000637",
            "tier8_intent_blending:000489",
            "tier8_intent_blending:000324",
        )
    )
)

SLOT_COUNT = G4_SLOT_COUNT
QUEUE_DEPTH = G4_QUEUE_DEPTH
MAX_TOKENS = 1024
TEMPERATURE = 0
MAX_CONTACTS = 1
REPAIR_CONTACTS = 0
RETRIES = 0
JITTER_TESTING = False
PROMPT_UTF8_BYTE_CAP = 24_000

BASELINE_CONFIG_RELPATH = Path(
    "configs/baseline/a2t-g4-executable-microground-agentloop.json"
)
BASELINE_CONFIG_SHA256 = (
    "dd7f38fe941d1c6ece607ff695f0ab700a9aea2c75fd5808674ceba8119820e5"
)
EXPERIMENT_CONFIG_RELPATH = Path(
    "configs/experiment/a2t-g4-executable-microground-screen-16-v1.json"
)
PREREGISTRATION_RELPATH = Path(
    "docs/readiness/"
    "2026-09-02-a2t-g4-executable-microground-screen-16-v1-preregistration.md"
)
PREREGISTRATION_SHA256 = (
    "9e380eacfb87e29550804548d54a693ebf27deb745a3cb662f53c0cbcca36387"
)
SELECTED_RECEIPT_RELPATH = Path(
    "docs/receipts/a2t/A2T-G4-MICROGROUND-SCREEN-16.json"
)
CORPUS_BUILD_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g4-semantic-cards-build-v1/build-receipt.json"
)
CORPUS_BUILD_SHA256 = (
    "f2da2a1b77a59ff7f5d9e74c2fabe1e04c87d560f4ca066c573f3d65803680fa"
)
CORPUS_FILE_RELPATH = Path(
    "knowledge/audio2tool/g4-executable-semantic-cards-v1/corpus.txt"
)
CORPUS_FILE_SHA256 = (
    "85a04fc72c49802853d0da3785f30a266a90d88275901c8292231442ef4a294f"
)
BUILDER_RELPATH = Path("scripts/build_a2t_g4_semantic_cards.py")
BUILDER_SHA256 = (
    "e49c5b71348efbfdcb284d17b847efb341a3a5898324ef2432ebe9e880da080e"
)
ORGANIZER_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/"
    "a2t_observation_state_organizer.py"
)
ORGANIZER_SHA256 = (
    "cf313b819d944306f1ff67c9bb9a556a2e083d5d6944509fe775ee3a928f2c06"
)
STRUCTURED_STATE_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/a2t_structured_dialogue_state.py"
)
STRUCTURED_STATE_SHA256 = (
    "58d26aac9fc1946d080008904ddbd5217d1ab711e342754169ded72cb5266523"
)
ROUTER_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/a2t_semantic_microground.py"
)
ROUTER_SHA256 = (
    "31da304a1e5c989972b8f7a435ad15827f0995fd35740b851b3043bb18d86d31"
)
FLIGHT_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/probes/"
    "a2t_g4_microground_flight.py"
)
FLIGHT_SHA256 = (
    "d9dbc3fe3ffaac8fbf46b89edbb00b8bdc213ebfc21c8c0e78a1c5c106d000e5"
)
RUNTIME_RECEIPT_RELPATH = G3.RUNTIME_RECEIPT_RELPATH
RUNTIME_RECEIPT_SHA256 = G3.RUNTIME_RECEIPT_SHA256
KNOWLEDGE_SNAPSHOT_RELPATH = G3.KNOWLEDGE_SNAPSHOT_RELPATH
STATE_RECEIPT_RELPATH = Path(
    "derived/audio2tool/g4-executable-microground-screen-16-v1/"
    "se16-structured-state-receipt.json"
)

# Bound after a deterministic no-contact reconstruction of the already-sealed
# G3 selected16 OBS.  These are source-free set identities, not source bytes.
STATE_SET_SHA256: str | None = (
    "2e42e636e36d7e15dcab9a6c7e3e450bd38a930b02f1e7270d4a617d8c45abad"
)
ROUTE_SET_SHA256: str | None = (
    "2b2d8b444ae67edd06abf7a3d59bab09d74db3e21b242246a392569f4ce5236c"
)

OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "workers": 1,
    "processes_per_job": 1,
    "operation": "finalize",
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "g4-se16",
            "input": "complete 16-row run manifest",
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


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


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


def _validate_selected_ids(tier_by_sample: Mapping[str, str]) -> tuple[str, ...]:
    if set(tier_by_sample) != set(SELECTED_IDS):
        raise RuntimeError("runtime identities drift from the frozen G3 selected16")
    counts = Counter(tier_by_sample.values())
    if counts != Counter({tier: 2 for tier in EXPECTED_TIERS}):
        raise RuntimeError("runtime tiers drift from the frozen G3 selected16")
    if any(
        tier_by_sample[sample_id] != sample_id.split(":", 1)[0]
        for sample_id in SELECTED_IDS
    ):
        raise RuntimeError("runtime tier labels drift from the frozen G3 selected16")
    return SELECTED_IDS


def _execution_plan(attempt_id: str, protocol: str = PROTOCOL_SHA256) -> ExecutionPlan:
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SELECTED_RUN_SHA256,
        planned_model_calls=16,
        planned_gpu_hours=0.3,
        planned_speech_audio_seconds=PLANNED_AUDIO_SECONDS,
        protocol_hash=protocol,
        attempt_id=attempt_id,
    ).validate()


def _verified_split() -> VerifiedSplit:
    return VerifiedSplit(
        name=G4_SCREEN_SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=SELECTED_IDS,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in SELECTED_IDS),
        identity_hash=SELECTED_RUN_SHA256,
    )


def _state_set_sha256(states: Mapping[str, str]) -> str:
    if set(states) != set(SELECTED_IDS):
        raise RuntimeError("state identity surface is not selected16")
    hashes = sorted(hashlib.sha256(states[sample_id].encode("utf-8")).hexdigest() for sample_id in states)
    return hashlib.sha256("\n".join(hashes).encode("ascii")).hexdigest()


def _organize_selected(
    observations: Mapping[str, str],
) -> tuple[dict[str, str], dict[str, object]]:
    if set(observations) != set(SELECTED_IDS):
        raise RuntimeError("sealed OBS identities drift from the frozen G3 selected16")
    artifacts = {
        sample_id: organize_sealed_observation(observations[sample_id])
        for sample_id in SELECTED_IDS
    }
    states = {sample_id: artifacts[sample_id].json_text for sample_id in SELECTED_IDS}
    if any(
        len(text.encode("utf-8")) > G4_SE_STATE_UTF8_BYTE_CAP
        for text in states.values()
    ):
        raise RuntimeError("structured-state byte cap exceeded")
    receipt = build_external_state_receipt(observations)
    measured = _state_set_sha256(states)
    if receipt.get("state_set_sha256") != measured:
        raise RuntimeError("external receipt and structured-state set identities disagree")
    return states, receipt


def _route_selected(
    corpus: object,
    states: Mapping[str, str],
    *,
    route_fn: Callable[..., object] = route_semantic_microground,
) -> tuple[dict[str, object], str]:
    if set(states) != set(SELECTED_IDS):
        raise RuntimeError("structured-state identities drift from selected16")
    routes = {
        sample_id: route_fn(
            corpus,
            structured_state=json.loads(states[sample_id]),
            max_utf8_bytes=G4_PACKET_UTF8_BYTE_CAP,
        )
        for sample_id in SELECTED_IDS
    }
    binding: dict[str, object] = {}
    for sample_id, route in routes.items():
        if getattr(route, "packet_utf8_bytes", G4_PACKET_UTF8_BYTE_CAP + 1) > G4_PACKET_UTF8_BYTE_CAP:
            raise RuntimeError("microground packet byte cap exceeded")
        binding[sample_id] = {
            "packet_sha256": getattr(route, "packet_sha256"),
            "trace_sha256": getattr(route, "trace_sha256"),
            "candidate_names": list(getattr(route, "candidate_names")),
        }
    return routes, _canonical_sha256(binding)


def _build_adapter(
    samples: Sequence[object],
    states: Mapping[str, str],
    routes: Mapping[str, object],
    *,
    prompt_utf8_byte_cap: int = PROMPT_UTF8_BYTE_CAP,
) -> tuple[G4MicrogroundAdapter, dict[str, object]]:
    sample_by_id = {str(getattr(sample, "sample_id")): sample for sample in samples}
    if set(sample_by_id) != set(SELECTED_IDS):
        raise RuntimeError("runtime sample identities drift from selected16")
    adapter = G4MicrogroundAdapter(
        tuple(sample_by_id[sample_id] for sample_id in SELECTED_IDS),
        phase=G4_MICROGROUND_SE_PHASE,
        state_by_sample=states,
        packet_by_sample={
            sample_id: str(getattr(routes[sample_id], "packet"))
            for sample_id in SELECTED_IDS
        },
    )
    by_sample: dict[str, int] = {}
    for sample in adapter.load_split(G4_SCREEN_SPLIT_ID):
        prompt = adapter.assemble_prompt(sample, None)
        size = len(
            json.dumps(
                prompt, ensure_ascii=True, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
        )
        if size > prompt_utf8_byte_cap:
            raise RuntimeError(
                f"G4 prompt-size cap exceeded for {sample.sample_id}: "
                f"{size} > {prompt_utf8_byte_cap}"
            )
        by_sample[sample.sample_id] = size
    return adapter, {
        "count": len(by_sample),
        "cap_utf8_bytes": prompt_utf8_byte_cap,
        "max_utf8_bytes": max(by_sample.values()),
        "by_sample": dict(sorted(by_sample.items())),
    }


def _validate_official_score_plan(plan: Mapping[str, object]) -> Mapping[str, object]:
    jobs = plan.get("jobs")
    if (
        plan.get("workers") != 1
        or plan.get("processes_per_job") != 1
        or plan.get("operation") != "finalize"
        or plan.get("dataset_sharding") is not False
        or plan.get("shard_metric_averaging") is not False
        or plan.get("network_jitter_testing") is not False
        or not isinstance(jobs, list)
        or len(jobs) != 1
        or not isinstance(jobs[0], Mapping)
        or jobs[0].get("input") != "complete 16-row run manifest"
        or jobs[0].get("row_count") != 16
    ):
        raise RuntimeError("G4 scoring must be one whole-manifest single-process job")
    return plan


def _rebuild_corpus(root: Path, lock: Mapping[str, object], registry: Sequence[Mapping[str, str]]) -> object:
    rows, _inventory = CARD_BUILDER.a2t_pool_rows(lock, root)
    exposed = CARD_BUILDER.exposed_sample_ids(REPO)
    partition = CARD_BUILDER.propose_partition(
        rows, exposed, seed=CARD_BUILDER.PARTITION_SEED
    )
    corpus, _audit = CARD_BUILDER.build_from_partition(registry, partition.construction)
    if corpus.sha256 != CORPUS_FILE_SHA256 or corpus.text != (REPO / CORPUS_FILE_RELPATH).read_text(encoding="ascii"):
        raise RuntimeError("deterministic G4 corpus identity drift")
    return corpus


def _static_preflight(root: Path) -> dict[str, object]:
    if STATE_SET_SHA256 is None or ROUTE_SET_SHA256 is None:
        raise RuntimeError("G4 SE16 state-set and route-set bindings are incomplete")
    commit = require_clean_study_repo(REPO)
    for relpath, expected, label in (
        (BASELINE_CONFIG_RELPATH, BASELINE_CONFIG_SHA256, "baseline config"),
        (EXPERIMENT_CONFIG_RELPATH, EXPERIMENT_CONFIG_SHA256, "experiment config"),
        (PREREGISTRATION_RELPATH, PREREGISTRATION_SHA256, "preregistration"),
        (SELECTED_RECEIPT_RELPATH, SELECTED_RECEIPT_SHA256, "selected16 receipt"),
        (CORPUS_BUILD_RELPATH, CORPUS_BUILD_SHA256, "corpus build receipt"),
        (CORPUS_FILE_RELPATH, CORPUS_FILE_SHA256, "semantic corpus"),
        (BUILDER_RELPATH, BUILDER_SHA256, "semantic-card builder"),
        (ORGANIZER_RELPATH, ORGANIZER_SHA256, "state organizer"),
        (STRUCTURED_STATE_RELPATH, STRUCTURED_STATE_SHA256, "structured-state module"),
        (ROUTER_RELPATH, ROUTER_SHA256, "semantic router"),
        (FLIGHT_RELPATH, FLIGHT_SHA256, "G4 flight boundary"),
        (RUNTIME_RECEIPT_RELPATH, RUNTIME_RECEIPT_SHA256, "runtime receipt"),
    ):
        _require_hash(REPO / relpath, expected, label)
    composed = compose(
        REPO,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("composed G4 config identity drift")
    measured_protocol = protocol_hash(
        composed.config_hash, str(composed.values.get("arm")), SELECTED_RUN_SHA256
    )
    if measured_protocol != PROTOCOL_SHA256:
        raise RuntimeError("G4 protocol identity drift")
    G3.Q._validate_server_geometry(composed.values)
    _validate_official_score_plan(OFFICIAL_SCORE_PLAN)

    _require_hash(REPO / G3.ROSTER_RELPATH, G3.ROSTER_SHA256, "G3 roster")
    roster_document = G3._read_json(REPO / G3.ROSTER_RELPATH)
    roster = G3._validate_roster(roster_document)
    _require_hash(Path(root) / G3.MEDIA_RELPATH, G3.MEDIA_SHA256, "G3 runtime media")
    media = G3._read_json(Path(root) / G3.MEDIA_RELPATH)
    _require_hash(G3.BINDING_MAP, G3.BINDING_SHA256, "G3 packet binding")
    bindings = G3._read_json(G3.BINDING_MAP)
    _require_hash(G3.PROMOTION_RECEIPT, G3.PROMOTION_SHA256, "G3 packet promotion")
    G3._validate_promotion(G3._read_json(G3.PROMOTION_RECEIPT), bindings)
    surface = G3.g3_flight.resolve_g3_runtime_media(
        roster_document, media, bindings, data_root=root
    )
    selected_ids = G3.g3_flight.select_shuffled_control_ids(surface.tier_by_sample)
    if tuple(sorted(selected_ids)) != SELECTED_IDS:
        raise RuntimeError("G3 deterministic selected16 identity drift")
    _validate_selected_ids(
        {sample_id: surface.tier_by_sample[sample_id] for sample_id in SELECTED_IDS}
    )

    obs_trace_dir = Path(root) / G3.COMPLETED_FLIGHT_OBS_TRACE_DIR_RELPATH
    obs_trace_path = Path(root) / G3.COMPLETED_FLIGHT_OBS_TRACE_RELPATH
    obs_manifest_path = Path(root) / G3.COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_RELPATH
    _require_hash(obs_trace_path, G3.COMPLETED_FLIGHT_OBS_TRACE_SHA256, "sealed G3 OBS trace")
    _require_hash(
        obs_manifest_path,
        G3.COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_SHA256,
        "sealed G3 OBS trace manifest",
    )
    obs = G3._validate_obs_recovery_trace(
        G3._trace_documents(obs_trace_dir),
        G3._read_json(obs_manifest_path),
        expected_ids=roster["sample_ids"],
    )
    dialogue_ids = tuple(
        sample_id
        for sample_id, tier in surface.tier_by_sample.items()
        if tier == "tier7_multiturn"
    )
    all_observations = G3.g3_flight.normalize_observation_texts(
        obs["summary"], dialogue_sample_ids=dialogue_ids
    )
    observations = {
        sample_id: all_observations[sample_id] for sample_id in SELECTED_IDS
    }
    states, state_receipt = _organize_selected(observations)
    if state_receipt["state_set_sha256"] != STATE_SET_SHA256:
        raise RuntimeError("G4 SE16 structured-state set identity drift")
    state_receipt_path = Path(root) / STATE_RECEIPT_RELPATH
    _write_json(state_receipt_path, state_receipt)

    lock = load_lock(umbrella_lock_path(REPO))
    registry = load_tool_registry(lock, root)
    corpus = _rebuild_corpus(root, lock, registry)
    routes, route_set = _route_selected(corpus, states)
    if route_set != ROUTE_SET_SHA256:
        raise RuntimeError("G4 SE16 route-set identity drift")
    selected = set(SELECTED_IDS)
    samples = tuple(sample for sample in surface.samples if sample.sample_id in selected)
    adapter, prompt_report = _build_adapter(samples, states, routes)
    packet_bindings = {
        sample_id: surface.packet_bindings[sample_id] for sample_id in SELECTED_IDS
    }

    runtime_document = G3._read_json(REPO / RUNTIME_RECEIPT_RELPATH)
    G3.Q._validate_runtime_receipt(runtime_document)
    snapshot = KnowledgeSnapshot.from_frozen_json(
        G3._read_json(Path(root) / KNOWLEDGE_SNAPSHOT_RELPATH)
    )
    return {
        "commit": commit,
        "composed": composed,
        "selected_ids": SELECTED_IDS,
        "samples": samples,
        "surface": surface,
        "states": states,
        "state_set_sha256": STATE_SET_SHA256,
        "state_receipt_path": state_receipt_path,
        "routes": routes,
        "route_set_sha256": route_set,
        "prompt_report": prompt_report,
        "adapter": adapter,
        "packet_bindings": packet_bindings,
        "snapshot": snapshot,
        "runtime_receipt": runtime_document,
    }


def _run_phase(
    *,
    root: Path,
    plan: object,
    adapter: G4MicrogroundAdapter,
    client: object,
    snapshot: object,
    packet_bindings: Mapping[str, Mapping[str, object]],
    trace_sink: object,
    run_phase: Callable[..., object] = run_g4_microground_phase,
) -> object:
    summary = run_phase(
        data_root=root,
        plan=plan,
        adapter=adapter,
        core_client=client,
        knowledge_snapshot=snapshot,
        speech_packet_bindings=packet_bindings,
        trace_sink=trace_sink,
    )
    results = getattr(summary, "results", None)
    if not isinstance(results, tuple) or len(results) != 16:
        raise RuntimeError("G4 SE16 did not return exactly sixteen results")
    ids = tuple(sorted(str(getattr(row, "sample_id", "")) for row in results))
    if ids != SELECTED_IDS or sum(len(getattr(row, "contacts", ())) for row in results) != 16:
        raise RuntimeError("G4 SE16 did not complete exactly sixteen single contacts")
    return summary


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
    agent_trace = run_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
    agent_trace_sha256 = _sha256_file(agent_trace)
    results = getattr(summary, "results")
    texts = {
        str(getattr(row, "sample_id")): str(getattr(row, "final_response_text"))
        for row in results
    }
    source_by_id = {
        sample_id: {
            "action": G4_MICROGROUND_SE_PHASE,
            "source_agent_trace_manifest_sha256": agent_trace_hash,
            "source_artifact_path": str(agent_trace),
            "source_artifact_sha256": agent_trace_sha256,
        }
        for sample_id in SELECTED_IDS
    }
    sink = TraceSink(run_dir, RUN_ID)
    rows = emit_composite_rows(
        texts=texts, source_by_id=source_by_id, sink=sink, variant="main"
    )
    output_trace_hash = sink.close()
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, rows)
    cost = dict(client_summary["cost"])
    cost["tool_calls"] = 16
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
        raise RuntimeError("G4 SE16 sealed bundle is not exactly sixteen rows")
    return {
        "outputs": outputs,
        "outputs_sha256": _sha256_file(outputs),
        "manifest": manifest,
        "manifest_sha256": _sha256_file(manifest),
        "agent_trace_sha256": agent_trace_sha256,
        "agent_trace_manifest_sha256": agent_trace_hash,
        "output_trace_manifest_sha256": output_trace_hash,
    }


def _stop_service(session: object, runtime_receipt: object, receipt: Path) -> None:
    stop_session(
        session,
        runtime_receipt=runtime_receipt,
        runtime_root=RUNTIME_ROOT,
        receipt_path=receipt,
    )


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt_id = f"attempt-{stamp.lower()}-g4-se16"
    plan = _execution_plan(attempt_id)
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}"
    run_dir = mission_dir / "se16"
    service_dir = mission_dir / "service"
    run_dir.mkdir(parents=True, exist_ok=False)
    service_dir.mkdir()
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    _write_json(run_dir / "official-score-plan.json", OFFICIAL_SCORE_PLAN)

    values = context["composed"].values
    runtime_receipt = load_runtime_receipt(REPO / RUNTIME_RECEIPT_RELPATH)
    gate = G3._build_g3_gate(
        root=root,
        values=values,
        media_identity_by_sample=context["surface"].media_identity_by_sample,
    )
    gate.assert_model_touch_allowed(plan, full_hash=True)
    parsed_url = urlparse(str(values["base_url"]))
    if parsed_url.hostname not in {"127.0.0.1", "localhost"} or parsed_url.port is None:
        raise RuntimeError("G4 SE16 decoder must use an explicit loopback port")
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = None
    client = None
    sink = None
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
            model_root=Path(str(values["model_materialization_root"])),
        )
        transport = TRANSPORTS.resolve(str(values["transport"]))(
            values,
            root,
            session=session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
        )
        client = G3._client(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            plan=plan,
            samples=context["samples"],
            packet_bindings=context["packet_bindings"],
            run_dir=run_dir,
            prefix="g4se16",
        )
        sink = TraceSink(run_dir / "agent-trace", RUN_ID)
        summary = _run_phase(
            root=root,
            plan=plan,
            adapter=context["adapter"],
            client=client,
            snapshot=context["snapshot"],
            packet_bindings=context["packet_bindings"],
            trace_sink=sink,
        )
        agent_trace_hash = sink.close()
        sink = None
        client_summary = client.close()
        client = None
        if client_summary.get("request_count") != 16:
            raise RuntimeError("G4 SE16 transport did not record exactly sixteen requests")
        _stop_service(session, runtime_receipt, stop_receipt)
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
            "schema": "saea-a2t-g4-structured-executable-microground-se16-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SEALED_UNSCORED",
            "study_commit": context["commit"],
            "attempt_id": attempt_id,
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "model_contacts": 16,
            "repair_contacts": REPAIR_CONTACTS,
            "retries": RETRIES,
            "network_jitter_testing": JITTER_TESTING,
            "slot_count": SLOT_COUNT,
            "queue_depth": QUEUE_DEPTH,
            "max_tokens": MAX_TOKENS,
            "temperature": TEMPERATURE,
            "state_set_sha256": context["state_set_sha256"],
            "route_set_sha256": context["route_set_sha256"],
            "state_receipt_path": str(context["state_receipt_path"]),
            "state_receipt_sha256": _sha256_file(context["state_receipt_path"]),
            "scorer_contacts": 0,
            **{key: str(value) if isinstance(value, Path) else value for key, value in sealed.items()},
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
        if sink is not None:
            sink.close()
        if client is not None:
            client.close()
        if session is not None:
            _stop_service(session, runtime_receipt, stop_receipt)


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
        print(
            json.dumps(
                {
                    "run_id": RUN_ID,
                    "preflight": "passed",
                    "study_commit": context["commit"],
                    "samples": len(context["selected_ids"]),
                    "state_set_sha256": context["state_set_sha256"],
                    "route_set_sha256": context["route_set_sha256"],
                    "max_prompt_utf8_bytes": context["prompt_report"]["max_utf8_bytes"],
                    "state_receipt_path": str(context["state_receipt_path"]),
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
