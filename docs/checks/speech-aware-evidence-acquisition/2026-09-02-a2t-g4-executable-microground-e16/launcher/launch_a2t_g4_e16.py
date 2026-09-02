#!/usr/bin/env python3
"""Launch the zero-reuse G4 executable-microground E arm on selected16.

Preflight is deliberately contact-free.  The explicit run path is the only
path allowed to open the frozen core or the unchanged official scorer.
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
from urllib.parse import urlparse

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import TRANSPORTS, RunResult
from speech_aware_evidence_acquisition.core.bundle import (
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.session import (
    load_runtime_receipt,
    start_session,
)
from speech_aware_evidence_acquisition.core.split_receipt import VerifiedSplit
from speech_aware_evidence_acquisition.core.tracing import TraceSink
from speech_aware_evidence_acquisition.data.lock import data_root
from speech_aware_evidence_acquisition.rails.a2t_semantic_microground import (
    route_semantic_microground,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g4_microground_flight import (
    G4_MICROGROUND_E_PHASE,
    G4_QUEUE_DEPTH,
    G4_SCREEN_SPLIT_ID,
    G4_SLOT_COUNT,
    G4MicrogroundAdapter,
    run_g4_microground_phase,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_bundle import (
    emit_composite_rows,
)


REPO = Path(__file__).resolve().parents[5]
RUN_ID = "SAEA-A2T-G4-EXECUTABLE-MICROGROUND-SCREEN-16-V1"
AUDIO2TOOL_LOCK_KEY = "audio2tool"
RUNTIME_ROOT = Path("/home/chao")
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g3-pilot-40"
BASELINE_FRAGMENT = "a2t-g4-executable-microground-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g4-executable-microground-screen-16-v1"
BASELINE_CONFIG_RELPATH = Path(
    "configs/baseline/a2t-g4-executable-microground-agentloop.json"
)
BASELINE_CONFIG_SHA256 = (
    "dd7f38fe941d1c6ece607ff695f0ab700a9aea2c75fd5808674ceba8119820e5"
)
EXPERIMENT_CONFIG_RELPATH = Path(
    "configs/experiment/a2t-g4-executable-microground-screen-16-v1.json"
)
EXPERIMENT_CONFIG_SHA256 = (
    "f2f31ad178d54e99cffa60d24fae1f0c72a8ea2d6894e6d1f19929e161100d5a"
)
ROUTER_RELPATH = Path(
    "src/speech_aware_evidence_acquisition/rails/a2t_semantic_microground.py"
)
ROUTER_SHA256 = (
    "63fe8dc77ca208bc02ce501eef4c5f79a8f11eda7243b6226709736241d451ea"
)
G3_LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g3-plain-english-v1/launcher/launch_a2t_g3.py"
)
BUILDER = REPO / "scripts/build_a2t_g4_semantic_cards.py"
SELECTED_RECEIPT_RELPATH = Path(
    "docs/receipts/a2t/A2T-G4-MICROGROUND-SCREEN-16.json"
)
SELECTED_RECEIPT_SHA256 = (
    "41a14ab576d7a428dd9849f26432e2c4998371b9f601189a1d558d694a12c884"
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
SELECTED_SPLIT_SHA256 = (
    "7590dfef54b42601c266f2bb325faee073143a575beeccd0c33cc8baf13aed45"
)
SELECTED_RUN_SHA256 = (
    "f9e3055f7eceff49405a192806be933db9bfcab150a1778bb3ddd937a8f57269"
)
PLANNED_AUDIO_SECONDS = 179

SLOT_COUNT = G4_SLOT_COUNT
QUEUE_DEPTH = G4_QUEUE_DEPTH
MAX_TOKENS = 1024
MAX_CONTACTS = 1
REPAIR_CONTACTS = 0
RETRIES = 0
JITTER_TESTING = False
PROMPT_UTF8_BYTE_CAP = 24_000

# These bindings are intentionally fail-closed until the independent builder
# and frozen configuration receipts land.  Never replace them with guessed
# identities.
CORPUS_BUILD_RELPATH: str | None = (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g4-semantic-cards-build-v1/build-receipt.json"
)
CORPUS_BUILD_SHA256: str | None = (
    "f2da2a1b77a59ff7f5d9e74c2fabe1e04c87d560f4ca066c573f3d65803680fa"
)
CORPUS_FILE_RELPATH: str | None = (
    "knowledge/audio2tool/g4-executable-semantic-cards-v1/corpus.txt"
)
CORPUS_FILE_SHA256: str | None = (
    "85a04fc72c49802853d0da3785f30a266a90d88275901c8292231442ef4a294f"
)
CORPUS_BOUND_SHA256: str | None = CORPUS_FILE_SHA256
COMPOSED_CONFIG_SHA256: str | None = (
    "c651ac7b631ebdbbe19a450582d17a8d728f5fd3fae2e6600b3fe7affc531da2"
)
PROTOCOL_SHA256: str | None = (
    "64236977c29d4babbacabbb597da5d21ec8b019c524191a64457452f66b889e0"
)
ROUTE_SET_SHA256: str | None = (
    "17bd588853706623263868bd07a7962cd696b670f6bf30bb3f27cea9c5806cc2"
)

OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "workers": 1,
    "operation": "finalize",
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "network_jitter_testing": False,
    "jobs": [
        {
            "job_id": "g4-e16",
            "input": "complete 16-row run manifest",
            "row_count": 16,
        }
    ],
}


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    if not Path(path).is_file() or _sha256_file(path) != expected:
        raise RuntimeError(f"{label} SHA-256 drift")


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: object) -> None:
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    Path(path).write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def _execution_plan(attempt_id: str, *, protocol_hash: str | None = None) -> ExecutionPlan:
    bound_protocol = protocol_hash or PROTOCOL_SHA256
    if not isinstance(bound_protocol, str) or len(bound_protocol) != 64:
        raise RuntimeError("PROTOCOL_SHA256 is not bound")
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SELECTED_RUN_SHA256,
        planned_model_calls=16,
        planned_gpu_hours=0.3,
        planned_speech_audio_seconds=PLANNED_AUDIO_SECONDS,
        protocol_hash=bound_protocol,
        attempt_id=attempt_id,
    ).validate()


def _route_selected(
    corpus: object,
    observations: Mapping[str, str],
    *,
    route_fn: Callable[..., object] = route_semantic_microground,
) -> tuple[dict[str, object], str]:
    if set(observations) != set(SELECTED_IDS):
        raise RuntimeError("OBS identities drift from the frozen G3 selected16")
    routes = {
        sample_id: route_fn(
            corpus,
            observation=observations[sample_id],
            max_utf8_bytes=16_384,
        )
        for sample_id in SELECTED_IDS
    }
    route_binding = {
        sample_id: {
            "packet_sha256": getattr(route, "packet_sha256"),
            "trace_sha256": getattr(route, "trace_sha256"),
            "candidate_names": list(getattr(route, "candidate_names")),
        }
        for sample_id, route in routes.items()
    }
    return routes, _canonical_sha256(route_binding)


def _build_adapter(
    samples: Sequence[object],
    observations: Mapping[str, str],
    routes: Mapping[str, object],
    *,
    prompt_utf8_byte_cap: int = PROMPT_UTF8_BYTE_CAP,
) -> tuple[G4MicrogroundAdapter, dict[str, object]]:
    sample_by_id = {str(getattr(sample, "sample_id")): sample for sample in samples}
    if set(sample_by_id) != set(SELECTED_IDS):
        raise RuntimeError("runtime samples drift from the frozen G3 selected16")
    if set(observations) != set(SELECTED_IDS) or set(routes) != set(SELECTED_IDS):
        raise RuntimeError("G4 adapter surfaces are incomplete")
    adapter = G4MicrogroundAdapter(
        tuple(sample_by_id[sample_id] for sample_id in SELECTED_IDS),
        phase=G4_MICROGROUND_E_PHASE,
        state_by_sample=observations,
        packet_by_sample={
            sample_id: str(getattr(routes[sample_id], "packet"))
            for sample_id in SELECTED_IDS
        },
    )
    by_sample: dict[str, int] = {}
    for sample in adapter.load_split(G4_SCREEN_SPLIT_ID):
        prompt = adapter.assemble_prompt(sample, None)
        size = len(
            json.dumps(prompt, sort_keys=True, separators=(",", ":")).encode("utf-8")
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


def _validate_official_score_plan(
    plan: Mapping[str, object],
) -> Mapping[str, object]:
    jobs = plan.get("jobs")
    if (
        plan.get("workers") != 1
        or plan.get("operation") != "finalize"
        or plan.get("dataset_sharding") is not False
        or plan.get("shard_metric_averaging") is not False
        or plan.get("network_jitter_testing") is not False
        or not isinstance(jobs, list)
        or len(jobs) != 1
        or jobs[0].get("input") != "complete 16-row run manifest"
        or jobs[0].get("row_count") != 16
    ):
        raise RuntimeError("G4 scoring must be one whole-manifest official job")
    return plan


def _unbound_requirements() -> tuple[str, ...]:
    names = (
        "CORPUS_BUILD_RELPATH",
        "CORPUS_BUILD_SHA256",
        "CORPUS_FILE_RELPATH",
        "CORPUS_FILE_SHA256",
        "CORPUS_BOUND_SHA256",
        "COMPOSED_CONFIG_SHA256",
        "PROTOCOL_SHA256",
        "ROUTE_SET_SHA256",
    )
    return tuple(name for name in names if globals()[name] is None)


def _verified_split() -> VerifiedSplit:
    return VerifiedSplit(
        name=G4_SCREEN_SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=SELECTED_IDS,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in SELECTED_IDS),
        identity_hash=SELECTED_RUN_SHA256,
    )


def _rebuild_corpus(root: Path, builder: object) -> tuple[object, dict[str, object]]:
    lock = builder.load_lock(builder.umbrella_lock_path(REPO))
    registry = builder.load_tool_registry(lock, root)
    rows, _inventory = builder.a2t_pool_rows(lock, root)
    partition = builder.propose_partition(
        rows,
        builder.exposed_sample_ids(REPO),
        seed=builder.PARTITION_SEED,
    )
    corpus, audit = builder.build_from_partition(registry, partition.construction)
    if corpus.sha256 != CORPUS_BOUND_SHA256:
        raise RuntimeError("rebuilt G4 corpus semantic identity drift")
    return corpus, {"lock": lock, "registry": registry, "audit": audit}


def _static_preflight(root: Path) -> dict[str, object]:
    missing = _unbound_requirements()
    if missing:
        raise RuntimeError(
            "G4 launcher bindings are incomplete: " + ", ".join(missing)
        )
    commit = require_clean_study_repo(REPO)
    _validate_official_score_plan(OFFICIAL_SCORE_PLAN)
    for path, digest, label in (
        (BASELINE_CONFIG_RELPATH, BASELINE_CONFIG_SHA256, "G4 baseline config"),
        (EXPERIMENT_CONFIG_RELPATH, EXPERIMENT_CONFIG_SHA256, "G4 experiment config"),
        (ROUTER_RELPATH, ROUTER_SHA256, "G4 microground router"),
    ):
        _require_hash(REPO / path, digest, label)
    _require_hash(
        REPO / SELECTED_RECEIPT_RELPATH,
        SELECTED_RECEIPT_SHA256,
        "G4 selected16 receipt",
    )
    receipt = _read_json(REPO / SELECTED_RECEIPT_RELPATH)
    selected = receipt.get("selected16")
    tiers = selected.get("tiers") if isinstance(selected, Mapping) else None
    if (
        not isinstance(tiers, Mapping)
        or selected.get("split_identity_hash") != SELECTED_SPLIT_SHA256
        or selected.get("run_identity_hash") != SELECTED_RUN_SHA256
        or tuple(sorted(item for rows in tiers.values() for item in rows))
        != SELECTED_IDS
    ):
        raise RuntimeError("G4 selected16 receipt content drift")

    composed = compose(
        REPO,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("composed G4 config identity drift")
    bundle_protocol = protocol_hash(
        composed.config_hash,
        str(composed.values.get("arm")),
        SELECTED_RUN_SHA256,
    )
    if bundle_protocol != PROTOCOL_SHA256:
        raise RuntimeError("G4 protocol identity drift")

    assert CORPUS_BUILD_RELPATH is not None
    assert CORPUS_BUILD_SHA256 is not None
    assert CORPUS_FILE_RELPATH is not None
    assert CORPUS_FILE_SHA256 is not None
    _require_hash(REPO / CORPUS_BUILD_RELPATH, CORPUS_BUILD_SHA256, "G4 build receipt")
    _require_hash(REPO / CORPUS_FILE_RELPATH, CORPUS_FILE_SHA256, "G4 corpus file")
    build_receipt = _read_json(REPO / CORPUS_BUILD_RELPATH)
    corpus_meta = build_receipt.get("corpus")
    if (
        not isinstance(corpus_meta, Mapping)
        or corpus_meta.get("path") != CORPUS_FILE_RELPATH
        or corpus_meta.get("sha256") != CORPUS_BOUND_SHA256
    ):
        raise RuntimeError("G4 build receipt content drift")

    g3 = _load_module(G3_LAUNCHER, "a2t_g4_bound_g3_launcher")
    builder = _load_module(BUILDER, "a2t_g4_bound_semantic_builder")
    for path, digest, label in (
        (REPO / g3.ROSTER_RELPATH, g3.ROSTER_SHA256, "G3 roster"),
        (Path(root) / g3.MEDIA_RELPATH, g3.MEDIA_SHA256, "G3 runtime media"),
        (g3.BINDING_MAP, g3.BINDING_SHA256, "G3 binding map"),
        (g3.PROMOTION_RECEIPT, g3.PROMOTION_SHA256, "G3 promotion receipt"),
    ):
        _require_hash(path, digest, label)
    roster = _read_json(REPO / g3.ROSTER_RELPATH)
    media = _read_json(Path(root) / g3.MEDIA_RELPATH)
    bindings = _read_json(g3.BINDING_MAP)
    surface = g3.g3_flight.resolve_g3_runtime_media(
        roster, media, bindings, data_root=root
    )
    completed = g3._load_completed_flight(root, tuple(surface.tier_by_sample))
    observations40 = g3.g3_flight.normalize_observation_texts(
        completed["observation"]["summary"],
        dialogue_sample_ids=surface.derived_dialogue_sample_ids,
    )
    observations = {sample_id: observations40[sample_id] for sample_id in SELECTED_IDS}
    _validate_selected_ids(
        {sample_id: surface.tier_by_sample[sample_id] for sample_id in SELECTED_IDS}
    )
    corpus, corpus_context = _rebuild_corpus(root, builder)
    if corpus.text != (REPO / CORPUS_FILE_RELPATH).read_text(encoding="utf-8"):
        raise RuntimeError("rebuilt G4 corpus bytes drift")
    routes, route_set_sha256 = _route_selected(corpus, observations)
    if route_set_sha256 != ROUTE_SET_SHA256:
        raise RuntimeError("G4 selected16 route-set identity drift")
    samples = tuple(
        sample for sample in surface.samples if sample.sample_id in set(SELECTED_IDS)
    )
    adapter, prompt_report = _build_adapter(samples, observations, routes)
    if composed.values.get("prompt_token_cap") != 8192:
        raise RuntimeError("G4 prompt token cap drift")
    runtime_path = REPO / g3.RUNTIME_RECEIPT_RELPATH
    _require_hash(runtime_path, g3.RUNTIME_RECEIPT_SHA256, "runtime receipt")
    runtime_receipt = _read_json(runtime_path)
    g3.Q._validate_runtime_receipt(runtime_receipt)
    snapshot = g3.KnowledgeSnapshot.from_frozen_json(
        _read_json(Path(root) / g3.KNOWLEDGE_SNAPSHOT_RELPATH)
    )
    execution_plan_template = _execution_plan("attempt-preflight-g4-e16")
    return {
        "commit": commit,
        "composed": composed,
        "surface": surface,
        "samples": samples,
        "selected_ids": SELECTED_IDS,
        "observations": observations,
        "routes": routes,
        "route_set_sha256": route_set_sha256,
        "prompt_report": prompt_report,
        "adapter": adapter,
        "packet_bindings": {
            sample_id: surface.packet_bindings[sample_id] for sample_id in SELECTED_IDS
        },
        "runtime_receipt": runtime_receipt,
        "snapshot": snapshot,
        "execution_plan_template": execution_plan_template,
        "lock": corpus_context["lock"],
        "registry": corpus_context["registry"],
        "g3": g3,
    }


def _launch(root: Path) -> Mapping[str, object]:  # pragma: no cover
    """Enter the explicit contact path only after the full preflight passes."""

    context = _static_preflight(root)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt_id = f"attempt-{stamp.lower()}-g4-e16"
    plan = _execution_plan(attempt_id)
    mission_dir = Path(root) / "runs" / RUN_ID / f"flight-{stamp}" / "e"
    mission_dir.mkdir(parents=True, exist_ok=False)
    _write_json(mission_dir / "execution-plan.json", asdict(plan))
    _write_json(
        mission_dir / "preflight-receipt.json",
        {
            "study_commit": context["commit"],
            "route_set_sha256": context["route_set_sha256"],
            "prompt_report": context["prompt_report"],
            "source_obs_trace_sha256": context["g3"].COMPLETED_FLIGHT_OBS_TRACE_SHA256,
            "source_obs_trace_manifest_sha256": (
                context["g3"].COMPLETED_FLIGHT_OBS_TRACE_MANIFEST_SHA256
            ),
            "contacts_before_launch": 0,
        },
    )
    values = context["composed"].values
    parsed = urlparse(str(values["base_url"]))
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
        raise RuntimeError("G4 decoder must use an explicit loopback port")
    g3 = context["g3"]
    runtime_receipt = load_runtime_receipt(REPO / g3.RUNTIME_RECEIPT_RELPATH)
    gate = g3._build_g3_gate(
        root=root,
        values=values,
        media_identity_by_sample=context["surface"].media_identity_by_sample,
    )
    gate.assert_model_touch_allowed(plan, full_hash=True)
    service_dir = mission_dir / "service"
    service_dir.mkdir()
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = None
    client = None
    try:
        session = start_session(
            runtime_root=RUNTIME_ROOT,
            data_root=root,
            runtime_receipt=runtime_receipt,
            host="127.0.0.1",
            port=parsed.port,
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
        client = g3._client(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            plan=plan,
            samples=context["samples"],
            packet_bindings=context["packet_bindings"],
            run_dir=mission_dir,
            prefix="g4e16",
        )
        agent_sink = TraceSink(mission_dir / "agent-trace", RUN_ID)
        summary = run_g4_microground_phase(
            data_root=root,
            plan=plan,
            adapter=context["adapter"],
            core_client=client,
            knowledge_snapshot=context["snapshot"],
            speech_packet_bindings=context["packet_bindings"],
            trace_sink=agent_sink,
        )
        agent_trace_manifest_sha256 = agent_sink.close()
        client_summary = client.close()
        client = None
        source_trace = mission_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
        texts = {row.sample_id: row.final_response_text for row in summary.results}
        source_by_id = {
            sample_id: {
                "action": G4_MICROGROUND_E_PHASE,
                "source_agent_trace_manifest_sha256": agent_trace_manifest_sha256,
                "source_artifact_path": str(source_trace),
                "source_artifact_sha256": _sha256_file(source_trace),
            }
            for sample_id in SELECTED_IDS
        }
        sink = TraceSink(mission_dir, RUN_ID)
        rows = emit_composite_rows(
            texts=texts, source_by_id=source_by_id, sink=sink, variant="policy"
        )
        trace_hash = sink.close()
        outputs = mission_dir / f"{RUN_ID}.outputs.jsonl"
        _write_jsonl(outputs, rows)
        cost = dict(client_summary["cost"])
        cost["tool_calls"] = 16
        manifest = build_manifest(
            repo_root=REPO,
            data_root=root,
            composed=context["composed"],
            plan=plan,
            verified_split=_verified_split(),
            session_receipt_path=session_receipt,
            run_dir=mission_dir,
            status=STATUS_COMPLETED,
            result=RunResult(
                run_id=RUN_ID,
                arm="speech-feature-query",
                outputs_path=outputs,
                trace_manifest_hash=trace_hash,
                cost=cost,
            ),
        )
        bundle = verify_bundle(manifest)
        if len(bundle.outputs_rows) != 16:
            raise RuntimeError("G4 E bundle is incomplete")
        g3._stop_service(session, runtime_receipt, stop_receipt)
        session = None
        receipt = {
            "schema": "saea-a2t-g4-e16-flight-receipt-v1",
            "run_id": RUN_ID,
            "phase": G4_MICROGROUND_E_PHASE,
            "attempt_id": attempt_id,
            "status": "SEALED_UNSCORED",
            "manifest": str(manifest),
            "manifest_sha256": _sha256_file(manifest),
            "model_contacts": 16,
            "official_scorer_contacts": 0,
            "semantic_output_inspection": False,
            "route_set_sha256": ROUTE_SET_SHA256,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        if client is not None:
            client.close()
        if session is not None:
            g3._stop_service(session, runtime_receipt, stop_receipt)
        abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        raise


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
                    "route_set_sha256": context["route_set_sha256"],
                    "max_prompt_utf8_bytes": context["prompt_report"][
                        "max_utf8_bytes"
                    ],
                    "official_score_manifests": 1,
                    "planned_model_calls": context[
                        "execution_plan_template"
                    ].planned_model_calls,
                    "contacts": {
                        "gold": 0,
                        "model": 0,
                        "network": 0,
                        "retriever": 0,
                        "scorer": 0,
                        "tokenizer": 0,
                    },
                },
                sort_keys=True,
            )
        )
        return 0
    result = _launch(root)
    print(json.dumps(result, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
