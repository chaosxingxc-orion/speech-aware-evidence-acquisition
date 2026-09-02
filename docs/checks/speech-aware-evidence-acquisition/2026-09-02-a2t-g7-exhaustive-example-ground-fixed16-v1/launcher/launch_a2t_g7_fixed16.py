#!/usr/bin/env python3
"""Preflight and launch the G7 fixed16 exhaustive construction-example screen.

Preflight is contact-free. ``--run`` starts the receipt-pinned local decoder,
executes exactly OBS + 28 EVIDENCE + RESOLVE per row, and seals all state,
traces, and final outputs before any scorer or gold surface can be opened.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import threading
import time
from typing import Callable, Mapping, Sequence
from types import SimpleNamespace
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from speech_aware_evidence_acquisition.rails.probes.a2t_g7_example_ground import (  # noqa: E402
    G7ExampleGround,
    MAX_OBSERVATION_ASCII_BYTES,
    build_trace_documents,
    execute_g7_workflows,
    parse_family_assessment,
    parse_observation,
)
from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.base import RunResult, TRANSPORTS  # noqa: E402
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    STATUS_COMPLETED,
    abort_attempt_if_opened,
    build_manifest,
    require_clean_study_repo,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash  # noqa: E402
from speech_aware_evidence_acquisition.core.session import (  # noqa: E402
    load_runtime_receipt,
    start_session,
    stop_session,
)
from speech_aware_evidence_acquisition.core.split_receipt import VerifiedSplit  # noqa: E402
from speech_aware_evidence_acquisition.core.tracing import TraceSink  # noqa: E402
from speech_aware_evidence_acquisition.data.audio2tool import AUDIO2TOOL_LOCK_KEY  # noqa: E402
from speech_aware_evidence_acquisition.data.lock import (  # noqa: E402
    asset_dir,
    data_root,
    load_lock,
    umbrella_lock_path,
)
from speech_aware_evidence_acquisition.rails.adapters.audio2tool import (  # noqa: E402
    Audio2ToolSample,
)
from speech_aware_evidence_acquisition.rails.core_client import (  # noqa: E402
    FrozenCoreClient,
    build_payload_binding,
)
from speech_aware_evidence_acquisition.rails.obs import AudioRef  # noqa: E402
from speech_aware_evidence_acquisition.rails.a2t_construction_example_ground import (  # noqa: E402
    ConstructionExampleFamilyBundle,
    ConstructionExampleGround,
    ConstructionExampleTool,
    ConstructionLanguagePattern,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_factor_top1_bundle import (  # noqa: E402
    emit_composite_rows,
)


RUN_ID = "SAEA-A2T-G7-EXHAUSTIVE-EXAMPLE-GROUND-FIXED16-V1"
SPLIT_ID = "A2T-G7-EXAMPLE-FIXED16"
SPLIT_IDENTITY_HASH = "94a10c359dfe9e6a96cd63940c4dcb52fc7206e4c0e7d855733b21b69b987212"
ROSTER_SHA256 = "8be941c6e82527f9b63cd1f9ea09449f6cabbf175e7b2401642de455edc975c3"
BUILDER_COMMIT = "7046ce6e7fbbba67ddbae5f122748e2158761e23"
GROUND_SHA256 = "a5bb788a64db320b8d09de3712ede38f46c5395d8e7dd1932d8acbbf8cedc855"
GROUND_RECEIPT_SHA256 = "f85e85b052a4cfdf3eeb8f2a82902dbfec78c4370a4f7c953d15e10421037ae5"
CONTACTS_PER_SAMPLE = 30
SAMPLE_COUNT = 16
MODEL_CONTACTS = CONTACTS_PER_SAMPLE * SAMPLE_COUNT
SLOTS = 2
MAX_CONCURRENT_MODEL_REQUESTS = 2
QUEUE_DEPTH = 4
OBS_COMPLETION_TOKENS = 512
EVIDENCE_COMPLETION_TOKENS = 512
RESOLVE_COMPLETION_TOKENS = 1024
COMPOSED_CONFIG_SHA256 = "2b8ca2f033fcbfe265533adeec8b3bfb8d39bb49174cedd13d2cacc492dcdf10"
PROTOCOL_SHA256 = "6f1c4eb956dfb4519ff880d55f92f19c51e89ffba1e000d47e9a19321e55e9c7"
RUNTIME_ROOT = Path("/home/chao")
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-G1-104-promotion.json"
RUNTIME_RECEIPT = REPO / "docs/receipts/runtime-q4km-mmproj-free.json"
G1_RECEIPT = REPO / "docs/receipts/a2t/A2T-G1-104.json"
G1_RECEIPT_SHA256 = "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
PROMOTION_RECEIPT_SHA256 = "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
RUNTIME_RECEIPT_SHA256 = "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
OPENJIUWEN_VERSION = "0.1.16.post2"
WORKFLOW_TIMEOUT_SECONDS = 14_400.0
CONTROL_INSTRUCTION = "Follow the system instruction for this registered contact."
OFFICIAL_SCORE_PLAN: Mapping[str, object] = {
    "workers": 1,
    "processes_per_job": 1,
    "operation": "score",
    "dataset_sharding": False,
    "shard_metric_averaging": False,
    "jobs": [
        {
            "job_id": "g7-final16",
            "input": "one sealed complete fixed16 RESOLVE manifest",
            "row_count": 16,
        }
    ],
}

ROSTER = REPO / "docs/receipts/a2t/A2T-G7-EXAMPLE-FIXED16.json"
BASELINE = REPO / "configs/baseline/a2t-g7-exhaustive-example-ground-agentloop.json"
EXPERIMENT = REPO / "configs/experiment/a2t-g7-exhaustive-example-ground-fixed16-v1.json"
GROUND_CORPUS = REPO / "knowledge/audio2tool/g7-construction-example-ground-v1/corpus.txt"
GROUND_STRUCTURED = REPO / "knowledge/audio2tool/g7-construction-example-ground-v1/ground.json"
GROUND_STRUCTURED_SHA256 = "f890e2a0975c4517e1909ecb2dee04d38eeaa05c4f0d9830b41ac634dbc9d830"
GROUND_RECEIPT = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/ground-receipt.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def execution_plan(attempt_id: str) -> ExecutionPlan:
    """Return the exact structured G7 flight plan without opening a service."""
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=MODEL_CONTACTS,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=2769,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def _byte_upper_bound(text: str) -> int:
    """Return a conservative tokenizer-free construction bound for ASCII prompts."""
    return len(text.encode("utf-8"))


def load_ground() -> ConstructionExampleGround:
    """Load only the frozen structured rendering; never reopen construction rows."""
    if _sha256(GROUND_STRUCTURED) != GROUND_STRUCTURED_SHA256:
        raise RuntimeError("G7 structured ground hash mismatch")
    document = json.loads(GROUND_STRUCTURED.read_text(encoding="ascii"))
    if document.get("schema") != "saea-a2t-construction-example-ground-runtime-v1":
        raise RuntimeError("G7 structured ground schema mismatch")
    bundles = tuple(
        ConstructionExampleFamilyBundle(
            family_tag=row["family_tag"],
            family_label=row["family_label"],
            tools=tuple(
                ConstructionExampleTool(
                    tool_name=tool["tool_name"],
                    operation=tool["operation"],
                    types=tuple(tuple(item) for item in tool["types"]),
                    legal_key_skeletons=tuple(
                        tuple(item) for item in tool["legal_key_skeletons"]
                    ),
                    patterns=tuple(
                        ConstructionLanguagePattern(
                            tier=pattern["tier"],
                            text=pattern["text"],
                            placeholders=tuple(pattern["placeholders"]),
                        )
                        for pattern in tool["patterns"]
                    ),
                )
                for tool in row["tools"]
            ),
            text=row["text"],
            sha256=row["sha256"],
            ascii_bytes=row["ascii_bytes"],
        )
        for row in document["bundles"]
    )
    receipt = json.loads(GROUND_RECEIPT.read_text(encoding="utf-8"))
    ground = ConstructionExampleGround(
        bundles=bundles,
        text=GROUND_CORPUS.read_text(encoding="ascii"),
        sha256=document["ground_sha256"],
        report=receipt["ground_report"],
        receipt=receipt["ground"],
    )
    if ground.sha256 != GROUND_SHA256 or len(ground.tool_names) != 152:
        raise RuntimeError("G7 structured ground identity drift")
    return ground


@dataclass(frozen=True)
class RuntimeSurface:
    samples: tuple[Audio2ToolSample, ...]
    packet_bindings: Mapping[str, Mapping[str, str]]
    speech_feature_tokens_by_sample: Mapping[str, int]


def load_runtime_surface() -> RuntimeSurface:
    """Join G7 identities to the frozen G1 media and promoted speech packets."""
    for path, expected in (
        (G1_RECEIPT, G1_RECEIPT_SHA256),
        (ROSTER, ROSTER_SHA256),
        (PROMOTION_RECEIPT, PROMOTION_RECEIPT_SHA256),
    ):
        if _sha256(path) != expected:
            raise RuntimeError(f"runtime identity hash mismatch: {path.name}")
    g1 = json.loads(G1_RECEIPT.read_text(encoding="utf-8"))
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    promotion = json.loads(PROMOTION_RECEIPT.read_text(encoding="ascii"))
    if roster["split_identity_hash"] != SPLIT_IDENTITY_HASH:
        raise RuntimeError("G7 roster split identity drift")
    g1_by_id = {row["sample_id"]: row for row in g1["items"]}
    promoted = {row["packet_id"]: row for row in promotion["packets"]}
    samples: list[Audio2ToolSample] = []
    bindings: dict[str, Mapping[str, str]] = {}
    speech_tokens: dict[str, int] = {}
    for selected in roster["selected"]:
        sample_id = selected["sample_id"]
        item = g1_by_id.get(sample_id)
        if item is None or item["key"] != selected["key"] or item["tier"] != selected["tier"]:
            raise RuntimeError("G7 roster row is absent from frozen G1")
        packet_id = item["packet_id"]
        packet = json.loads(
            (PROMOTION_RECEIPT.parent / packet_id / "packet.json").read_text(
                encoding="ascii"
            )
        )
        if (
            packet["packet_sha256"] != promoted[packet_id]["packet_sha256"]
            or packet["audio_sha256"] != item["audio_sha256"]
        ):
            raise RuntimeError("G7 promoted packet identity drift")
        samples.append(
            Audio2ToolSample(
                sample_id=sample_id,
                audio_ref=AudioRef(
                    path=item["media_relpath"], sha256=item["audio_sha256"]
                ).validate(),
                audio_seconds=float(item["audio_seconds"]),
                media_relpath=item["media_relpath"],
            )
        )
        bindings[sample_id] = {
            "packet_id": packet_id,
            "sha256": packet["packet_sha256"],
        }
        speech_tokens[sample_id] = sum(chunk["n_tokens"] for chunk in packet["chunks"])
    if len(samples) != 16 or abs(sum(row.audio_seconds for row in samples) - 92.272) > 1e-6:
        raise RuntimeError("G7 runtime sample count or duration drift")
    return RuntimeSurface(tuple(samples), bindings, speech_tokens)


def _render_obs() -> str:
    return (
        "Listen to the original complete dialogue. Describe the spoken request in bounded "
        "plain English. Do not name tools, propose a final answer, or add metadata."
    )


def _render_evidence(context: object) -> str:
    return (
        f"OBS o1\n{context.observation}\n\nFAMILY CONSTRUCTION EXAMPLES\n"
        f"{context.family_bundle_text}"
    )


def _render_resolve(context: object) -> str:
    return (
        f"OBSERVATION\n{context.observation}\n\n"
        "ALL-TOOL EXECUTION SHEET WITH 152 NORMALIZED ASSESSMENTS\n"
        f"{context.execution_sheet}"
    )


def _fit_dict(fit: object) -> dict[str, int | str]:
    return {
        "contact_id": fit.contact_id,
        "prompt_tokens": fit.prompt_tokens,
        "completion_tokens": fit.completion_tokens,
        "total_tokens": fit.total_tokens,
        "remaining_tokens": fit.remaining_tokens,
    }


def preflight_ground(
    ground: object, *, speech_feature_tokens_max: int
) -> dict[str, object]:
    """Validate the in-memory artifact and measure every static exact prompt."""
    if getattr(ground, "receipt", {}).get("schema") != (
        "saea-a2t-construction-example-ground-receipt-v1"
    ):
        raise ValueError("construction-example ground receipt schema is not frozen")
    if ground.sha256 != GROUND_SHA256:
        raise ValueError("construction-example ground SHA-256 drift")
    core = G7ExampleGround(ground.bundles)
    observation_seed = "The speaker describes the requested device action in plain English. "
    observation_text = (
        observation_seed
        * (MAX_OBSERVATION_ASCII_BYTES // len(observation_seed) + 1)
    )[:MAX_OBSERVATION_ASCII_BYTES]
    if len(observation_text.encode("ascii")) != MAX_OBSERVATION_ASCII_BYTES:
        raise RuntimeError("worst-case observation construction drift")
    observation = type("Obs", (), {"text": observation_text})()
    packet_binding = {"packet_id": "preflight/query", "sha256": "0" * 64}
    obs_context = SimpleNamespace(contact_id="g7-obs", instruction=_render_obs())
    obs_state = SimpleNamespace(stage="OBS", packet_binding=packet_binding)
    obs_messages = _contact_messages(obs_state, obs_context)
    obs = core.measure_prompt(
        contact_id="g7-obs",
        text=_exact_request(obs_messages, obs_context, with_control=True),
        token_counter=_byte_upper_bound,
        completion_tokens=OBS_COMPLETION_TOKENS,
        speech_feature_tokens=speech_feature_tokens_max,
    )
    evidence_contexts = core.build_evidence_contexts(observation)
    evidence_state = SimpleNamespace(stage="EVIDENCE", packet_binding=packet_binding)
    evidence = tuple(
        core.measure_prompt(
            contact_id=context.contact_id,
            text=_exact_request(
                _contact_messages(evidence_state, context), context, with_control=False
            ),
            token_counter=_byte_upper_bound,
            completion_tokens=EVIDENCE_COMPLETION_TOKENS,
        )
        for context in evidence_contexts
    )
    empty = tuple(
        parse_family_assessment(
            "{}", family_tag=context.family_tag, family_tool_names=context.tool_names
        )
        for context in evidence_contexts
    )
    worst = tuple(
        parse_family_assessment(
            json.dumps(
                {
                    "assessments": [
                        {
                            "tool_name": tool_name,
                            "status": "support",
                            "evidence": ["o1"],
                        }
                        for tool_name in context.tool_names
                    ]
                },
                separators=(",", ":"),
            ),
            family_tag=context.family_tag,
            family_tool_names=context.tool_names,
        )
        for context in evidence_contexts
    )
    resolve_state = SimpleNamespace(stage="RESOLVE", packet_binding=packet_binding)
    empty_context = core.build_resolve_context(observation, empty)
    worst_context = core.build_resolve_context(observation, worst)
    resolve_base = core.measure_prompt(
        contact_id="g7-resolve",
        text=_exact_request(
            _contact_messages(resolve_state, empty_context),
            empty_context,
            with_control=True,
        ),
        token_counter=_byte_upper_bound,
        completion_tokens=RESOLVE_COMPLETION_TOKENS,
        speech_feature_tokens=speech_feature_tokens_max,
    )
    resolve_worst = core.measure_prompt(
        contact_id="g7-resolve",
        text=_exact_request(
            _contact_messages(resolve_state, worst_context),
            worst_context,
            with_control=True,
        ),
        token_counter=_byte_upper_bound,
        completion_tokens=RESOLVE_COMPLETION_TOKENS,
        speech_feature_tokens=speech_feature_tokens_max,
    )
    return {
        "schema": "saea-a2t-g7-precontact-report-v1",
        "run_id": RUN_ID,
        "split_id": SPLIT_ID,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "roster_sha256": ROSTER_SHA256,
        "builder_commit": BUILDER_COMMIT,
        "ground_sha256": ground.sha256,
        "contacts": MODEL_CONTACTS,
        "contacts_per_sample": CONTACTS_PER_SAMPLE,
        "audio_contacts_per_sample": 2,
        "family_count": len(ground.bundles),
        "tool_count": len(ground.tool_names),
        "slots": SLOTS,
        "max_concurrent_model_requests": MAX_CONCURRENT_MODEL_REQUESTS,
        "queue_depth": QUEUE_DEPTH,
        "token_counter": "utf8-byte-construction-upper-bound",
        "worst_observation_ascii_bytes": len(observation_text.encode("ascii")),
        "obs_prompt": _fit_dict(obs),
        "evidence_prompts": [_fit_dict(row) for row in evidence],
        "resolve_empty_assessment_base_prompt": _fit_dict(resolve_base),
        "resolve_worst_normalized_assessment_prompt": _fit_dict(resolve_worst),
        "resolve_measurement": "dynamic-after-152-assessments-seal",
    }


def execute_preflighted(
    *,
    sample_ids: Sequence[str],
    ground: object,
    speech_feature_tokens_by_sample: Mapping[str, int],
    invoke_contact: Callable[[str, str, object], str],
) -> tuple[object, ...]:
    """Execute through an injected contact function with fail-closed prompt fits."""
    if len(sample_ids) != SAMPLE_COUNT or set(sample_ids) != set(speech_feature_tokens_by_sample):
        raise ValueError("execution requires the exact sixteen receipt-bound samples")
    preflight_ground(
        ground, speech_feature_tokens_max=max(speech_feature_tokens_by_sample.values())
    )
    core = G7ExampleGround(ground.bundles)

    def measured(sample_id: str, stage: str, context: object) -> str:
        if stage == "OBS":
            rendered, completion, speech = (
                _render_obs(),
                OBS_COMPLETION_TOKENS,
                speech_feature_tokens_by_sample[sample_id],
            )
        elif stage == "EVIDENCE":
            rendered, completion, speech = _render_evidence(context), EVIDENCE_COMPLETION_TOKENS, 0
        else:
            rendered, completion, speech = (
                _render_resolve(context),
                RESOLVE_COMPLETION_TOKENS,
                speech_feature_tokens_by_sample[sample_id],
            )
        core.measure_prompt(
            contact_id=getattr(context, "contact_id", "g7-obs"),
            text=rendered,
            token_counter=_byte_upper_bound,
            completion_tokens=completion,
            speech_feature_tokens=speech,
        )
        return invoke_contact(sample_id, stage, context)

    return execute_g7_workflows(
        sample_ids=sample_ids, bundles=ground.bundles, invoke_contact=measured
    )


def _execute_openjiuwen(*args: object, **kwargs: object) -> object:
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    return execute_speech_agent_workflows(*args, **kwargs)


def _contact_messages(state: object, context: object) -> tuple[Mapping[str, object], ...]:
    packet = {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": state.packet_binding["packet_id"],
            "sha256": state.packet_binding["sha256"],
            "role": "query",
        },
    }
    if state.stage == "OBS":
        return (
            {"role": "system", "content": context.instruction},
            {"role": "user", "content": [packet]},
        )
    if state.stage == "EVIDENCE":
        supplied = _render_evidence(context)
        return (
            {"role": "system", "content": context.instruction},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": supplied,
                        "evidence_id": f"g7:family:{context.family_tag}",
                        "source_uri": f"g7-ground://{context.family_tag}",
                        "knowledge_role": "value",
                    }
                ],
            },
        )
    supplied = _render_resolve(context)
    return (
        {"role": "system", "content": context.instruction},
        {
            "role": "user",
            "content": [
                packet,
                {
                    "type": "text",
                    "text": supplied,
                    "evidence_id": "g7:normalized-all-tool-sheet",
                    "source_uri": "g7-runtime://normalized-all-tool-sheet",
                    "knowledge_role": "value",
                },
            ],
        },
    )


def _exact_request(messages: object, context: object, *, with_control: bool) -> str:
    payload: dict[str, object] = {"messages": messages}
    if with_control:
        payload["agent_control"] = {
            "contact_id": context.contact_id,
            "instruction": CONTROL_INSTRUCTION,
        }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class ContactRecord:
    sample_id: str
    contact_id: str
    stage: str
    slot_id: int
    response_sha256: str
    prompt_fit: Mapping[str, object]
    recovered: bool = False


@dataclass(frozen=True)
class RecoveryContact:
    request_id: str
    sample_id: str
    contact_id: str
    semantic_sha256: str
    response_text: str
    response_sha256: str
    slot_id: int
    cost: Mapping[str, object]


@dataclass(frozen=True)
class RecoveryBundle:
    trace_path: Path
    trace_sha256: str
    contacts: Mapping[tuple[str, str], RecoveryContact]
    cost: Mapping[str, object]


@dataclass
class _WorkflowState:
    sample: Audio2ToolSample
    core: G7ExampleGround
    packet_binding: Mapping[str, str]
    speech_tokens: int
    stage: str = "OBS"
    current: tuple[object, ...] = ()
    observation: object | None = None
    assessments: tuple[object, ...] = ()
    resolve: object | None = None
    contacts: list[ContactRecord] = field(default_factory=list)
    final_response_text: str = ""
    traces: Mapping[str, object] | None = None
    pending_fits: dict[str, Mapping[str, object]] = field(default_factory=dict)
    pending_recovered: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class FlightSummary:
    results: tuple[_WorkflowState, ...]


def _semantic_sha256(
    *, sample_id: str, contact_id: str, task_instruction: str, supply: Sequence[str], packet_sha256: str | None
) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "sample_id": sample_id,
                "contact_id": contact_id,
                "task_instruction": task_instruction,
                "supply": list(supply),
                "packet_sha256": packet_sha256,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("ascii")
    ).hexdigest()


def _message_semantic_sha256(sample_id: str, context: object, messages: object) -> str:
    system, user = messages
    content = user["content"]
    supply = [row["text"] for row in content if row["type"] == "text"]
    packets = [
        row["speech_features"]["sha256"]
        for row in content
        if row["type"] == "input_speech_features"
    ]
    return _semantic_sha256(
        sample_id=sample_id,
        contact_id=context.contact_id,
        task_instruction=system["content"],
        supply=supply,
        packet_sha256=packets[0] if packets else None,
    )


def _canonical_sha256(document: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()


def load_recovery_bundle(root: Path, trace_path: Path) -> RecoveryBundle:
    """Load only complete, hash-bound prior triples and never interpret responses."""
    trace_path = trace_path.resolve()
    failure_receipt = trace_path.parents[2] / "failure-receipt.json"
    failure = json.loads(failure_receipt.read_text(encoding="utf-8"))
    trace_hash = _sha256(trace_path)
    if (
        failure.get("run_id") != RUN_ID
        or failure.get("transport_trace") != str(trace_path)
        or failure.get("transport_trace_sha256") != trace_hash
    ):
        raise RuntimeError("G7 recovery trace is not bound by its failure receipt")
    attempt_id = failure.get("attempt_id")
    attempt_path = root / "attempts" / RUN_ID / f"{attempt_id}.json"
    attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
    if attempt.get("state") != "ABORTED" or attempt.get("run_id") != RUN_ID:
        raise RuntimeError("G7 recovery source attempt is not ABORTED and bound")
    rows = [json.loads(line) for line in trace_path.read_text().splitlines() if line]
    by_id = {row["record_id"]: row for row in rows}
    contacts: dict[tuple[str, str], RecoveryContact] = {}
    totals = {
        "calls_used": 0,
        "audio_seconds_used": 0.0,
        "latency_seconds_total": 0.0,
        "prompt_tokens_total": 0,
        "completion_tokens_total": 0,
    }
    request_ids = sorted(
        row["payload"]["payload"]["request_id"]
        for row in rows
        if row.get("channel") == "MODEL_REQUEST"
    )
    for request_id in request_ids:
        request = by_id.get(f"{request_id}/request")
        response = by_id.get(f"{request_id}/response")
        cost_row = by_id.get(f"{request_id}/cost")
        if response is None or cost_row is None:
            continue
        wrapper = request["payload"]
        payload = wrapper["payload"]
        response_payload = response["payload"]
        cost = cost_row["payload"]
        if wrapper["payload_sha256"] != _canonical_sha256(payload):
            raise RuntimeError("G7 recovery request payload hash drift")
        text = response_payload.get("text")
        if not isinstance(text, str) or response_payload["response_text_sha256"] != hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest():
            raise RuntimeError("G7 recovery response hash drift")
        history = payload.get("history", [])
        control = history[-1] if history else None
        if isinstance(control, Mapping):
            contact_id = control.get("contact_id")
        else:
            supplied = payload.get("supplied_evidence", [])
            content = supplied[0]["content"] if supplied else ""
            marker = "FAMILY CONSTRUCTION EXAMPLES\n"
            family_text = content.split(marker, 1)[1] if marker in content else ""
            family = next(
                (
                    bundle.family_tag
                    for bundle in load_ground().bundles
                    if bundle.text == family_text
                ),
                None,
            )
            contact_id = f"g7-evidence-{family}" if family else None
        if not isinstance(contact_id, str):
            raise RuntimeError("G7 recovery contact identity is unavailable")
        supply = [row["content"] for row in payload.get("supplied_evidence", [])]
        semantic = _semantic_sha256(
            sample_id=payload["sample_id"],
            contact_id=contact_id,
            task_instruction=payload["task_instruction"],
            supply=supply,
            packet_sha256=payload.get("speech_packet_sha256"),
        )
        key = (payload["sample_id"], contact_id)
        if key in contacts or cost.get("calls") != 1:
            raise RuntimeError("G7 recovery contains duplicate or malformed contact")
        contacts[key] = RecoveryContact(
            request_id=request_id,
            sample_id=payload["sample_id"],
            contact_id=contact_id,
            semantic_sha256=semantic,
            response_text=text,
            response_sha256=response_payload["response_text_sha256"],
            slot_id=int(payload["decoding_params"]["id_slot"]),
            cost=dict(cost),
        )
        totals["calls_used"] += 1
        totals["audio_seconds_used"] += float(cost.get("audio_seconds", 0))
        totals["latency_seconds_total"] += float(cost.get("latency_seconds", 0))
        totals["prompt_tokens_total"] += int(cost.get("prompt_tokens", 0))
        totals["completion_tokens_total"] += int(cost.get("completion_tokens", 0))
    if not contacts or int(attempt.get("actual", {}).get("calls", -1)) < len(contacts):
        raise RuntimeError("G7 recovery source has no complete response triples")
    return RecoveryBundle(trace_path, trace_hash, contacts, totals)


def _fit_for_contact(state: _WorkflowState, context: object, messages: object) -> Mapping[str, object]:
    completion = (
        OBS_COMPLETION_TOKENS
        if state.stage == "OBS"
        else EVIDENCE_COMPLETION_TOKENS
        if state.stage == "EVIDENCE"
        else RESOLVE_COMPLETION_TOKENS
    )
    with_audio = state.stage in {"OBS", "RESOLVE"}
    fit = state.core.measure_prompt(
        contact_id=context.contact_id,
        text=_exact_request(messages, context, with_control=with_audio),
        token_counter=_byte_upper_bound,
        completion_tokens=completion,
        speech_feature_tokens=state.speech_tokens if with_audio else 0,
    )
    return {
        "contact_id": fit.contact_id,
        "prompt_tokens": fit.prompt_tokens,
        "completion_tokens": fit.completion_tokens,
        "total_tokens": fit.total_tokens,
        "remaining_tokens": fit.remaining_tokens,
    }


def run_openjiuwen_phase(
    *,
    surface: RuntimeSurface,
    ground: ConstructionExampleGround,
    client: FrozenCoreClient,
    trace_sink: TraceSink,
    workflow_runner: Callable[..., object] = _execute_openjiuwen,
    recovery: RecoveryBundle | None = None,
) -> FlightSummary:
    """Run exact OBS -> 28 EVIDENCE -> RESOLVE waves and seal state in memory."""
    core = G7ExampleGround(ground.bundles)
    states = [
        _WorkflowState(
            sample=sample,
            core=core,
            packet_binding=surface.packet_bindings[sample.sample_id],
            speech_tokens=surface.speech_feature_tokens_by_sample[sample.sample_id],
        )
        for sample in surface.samples
    ]
    recovered_used: set[tuple[str, str]] = set()
    recovery_lock = threading.Lock()

    def prepare(state: _WorkflowState, session: object) -> int:
        if state.stage == "OBS":
            state.current = (
                SimpleNamespace(
                    contact_id="g7-obs",
                    instruction=_render_obs(),
                ),
            )
        elif state.stage == "EVIDENCE":
            assert state.observation is not None
            state.current = state.core.build_evidence_contexts(state.observation)
        elif state.stage == "RESOLVE":
            assert state.resolve is not None
            state.current = (state.resolve,)
        else:
            state.current = ()
        update = getattr(session, "update_global_state", None)
        if callable(update):
            update({"g7_stage": state.stage, "g7_sample_id": state.sample.sample_id})
        return len(state.current)

    def invoke(state: _WorkflowState, branch_index: int, slot_id: int) -> Mapping[str, object]:
        context = state.current[branch_index]
        messages = _contact_messages(state, context)
        fit = _fit_for_contact(state, context, messages)
        state.pending_fits[context.contact_id] = fit
        recovery_key = (state.sample.sample_id, context.contact_id)
        source = recovery.contacts.get(recovery_key) if recovery is not None else None
        if source is not None:
            if source.semantic_sha256 != _message_semantic_sha256(
                state.sample.sample_id, context, messages
            ):
                raise RuntimeError("G7 recovery contact semantic identity drift")
            with recovery_lock:
                if recovery_key in recovered_used:
                    raise RuntimeError("G7 recovery contact reused twice")
                recovered_used.add(recovery_key)
            state.pending_recovered[context.contact_id] = True
            return {
                "response_text": source.response_text,
                "slot_id": source.slot_id,
                "response_sha256": source.response_sha256,
            }
        state.pending_recovered[context.contact_id] = False
        common = {
            "decoding_params": {
                "max_tokens": fit["completion_tokens"],
                "temperature": 0,
                "id_slot": slot_id,
            },
        }
        if state.stage == "EVIDENCE":
            text = client.complete(
                messages,
                text_only_sample_id=state.sample.sample_id,
                **common,
            )
        else:
            text = client.complete(
                messages,
                speech_feature_sample_id=state.sample.sample_id,
                key_representation_id=f"g7-example-ground:{state.stage.lower()}",
                matcher_policy_id="saea-a2t-g7-exhaustive-example-ground-v1",
                agent_state=(),
                agent_contact_id=context.contact_id,
                contact_instruction=CONTROL_INSTRUCTION,
                **common,
            )
        return {
            "response_text": text,
            "slot_id": slot_id,
            "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }

    def aggregate(
        state: _WorkflowState,
        responses: tuple[Mapping[str, object], ...],
        session: object,
    ) -> None:
        del session
        if len(responses) != len(state.current):
            raise RuntimeError("G7 fan-in contact count drift")
        for context, response in zip(state.current, responses, strict=True):
            text = response["response_text"]
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if response["response_sha256"] != digest:
                raise RuntimeError("G7 response hash mismatch")
            state.contacts.append(
                ContactRecord(
                    state.sample.sample_id,
                    context.contact_id,
                    state.stage,
                    int(response["slot_id"]),
                    digest,
                    state.pending_fits.pop(context.contact_id),
                    state.pending_recovered.pop(context.contact_id),
                )
            )
        if state.stage == "OBS":
            state.observation = parse_observation(
                str(responses[0]["response_text"]), state.core.tool_names
            )
            state.stage = "EVIDENCE"
        elif state.stage == "EVIDENCE":
            state.assessments = tuple(
                parse_family_assessment(
                    str(response["response_text"]),
                    family_tag=context.family_tag,
                    family_tool_names=context.tool_names,
                )
                for context, response in zip(state.current, responses, strict=True)
            )
            state.resolve = state.core.build_resolve_context(
                state.observation, state.assessments
            )
            state.stage = "RESOLVE"
        else:
            state.final_response_text = str(responses[0]["response_text"])
            state.traces = build_trace_documents(
                SimpleNamespace(
                    sample_id=state.sample.sample_id,
                    observation=state.observation,
                    family_assessments=state.assessments,
                    resolve_context=state.resolve,
                    final_response_text=state.final_response_text,
                )
            )
            state.stage = "DONE"

    completed = workflow_runner(
        states,
        prepare_wave=prepare,
        invoke_contact=invoke,
        aggregate_wave=aggregate,
        should_continue=lambda state: state.stage != "DONE",
        branch_count=28,
        slot_count=2,
        queue_depth=4,
        workflow_timeout_seconds=WORKFLOW_TIMEOUT_SECONDS,
    )
    if list(completed) != states or sum(len(state.contacts) for state in states) != 480:
        raise RuntimeError("G7 did not complete exactly 480 contacts")
    if recovered_used != (set(recovery.contacts) if recovery is not None else set()):
        raise RuntimeError("G7 recovery did not consume every prior contact exactly once")
    for state in states:
        if [row.stage for row in state.contacts] != ["OBS", *(["EVIDENCE"] * 28), "RESOLVE"]:
            raise RuntimeError("G7 row contact order drift")
        assert state.traces is not None
        for phase, key in (
            ("OBS", "obs_state"),
            ("ORG", "org_assessments"),
            ("SUPPLY", "supply_sheet"),
            ("USE", "use_final"),
        ):
            trace_sink.emit(
                phase,
                f"g7:{state.sample.sample_id}:{phase.lower()}",
                {f"{phase.lower()}_{name}": value for name, value in state.traces[key].items()},
            )
    return FlightSummary(tuple(states))


def _write_json(path: Path, document: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )


def _verified_split() -> VerifiedSplit:
    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    ids = tuple(row["sample_id"] for row in roster["selected"])
    return VerifiedSplit(
        name=SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in ids),
        identity_hash=SPLIT_IDENTITY_HASH,
    )


def static_preflight(root: Path) -> dict[str, object]:
    """Run all contact-free hash, runtime, geometry, and prompt checks."""
    commit = require_clean_study_repo(REPO)
    for path, expected in (
        (ROSTER, ROSTER_SHA256),
        (GROUND_CORPUS, GROUND_SHA256),
        (GROUND_STRUCTURED, GROUND_STRUCTURED_SHA256),
        (GROUND_RECEIPT, GROUND_RECEIPT_SHA256),
        (G1_RECEIPT, G1_RECEIPT_SHA256),
        (PROMOTION_RECEIPT, PROMOTION_RECEIPT_SHA256),
        (RUNTIME_RECEIPT, RUNTIME_RECEIPT_SHA256),
    ):
        if _sha256(path) != expected:
            raise RuntimeError(f"G7 preflight hash drift: {path}")
    composed = compose(
        REPO,
        "q4km-mmproj-free-speech-native-np2-a2t-max1024",
        "audio2tool-g1-104",
        "a2t-g7-exhaustive-example-ground-agentloop",
        "a2t-g7-exhaustive-example-ground-fixed16-v1",
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("G7 composed config drift")
    measured_protocol = protocol_hash(
        composed.config_hash, str(composed.values["arm"]), SPLIT_IDENTITY_HASH
    )
    if measured_protocol != PROTOCOL_SHA256:
        raise RuntimeError("G7 protocol identity drift")
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("G7 openJiuwen version drift")
    if (
        int(composed.values["profile_slot_count"]) != 2
        or int(composed.values["max_concurrent_model_requests"]) != 2
        or int(composed.values["queue_depth"]) != 4
    ):
        raise RuntimeError("G7 np2/concurrency/queue geometry drift")
    lock = load_lock(umbrella_lock_path(REPO))
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath="receipts/runtime-q4km-mmproj-free.json",
        expected_model_lock_key=str(composed.values["model_lock_key"]),
        model_root=Path(str(composed.values["model_materialization_root"])),
    )
    gate._require_exposure_preregistration(execution_plan("preflight-g7"), lock=lock)
    ground = load_ground()
    surface = load_runtime_surface()
    prompt_fit = preflight_ground(
        ground,
        speech_feature_tokens_max=max(surface.speech_feature_tokens_by_sample.values()),
    )
    return {
        "commit": commit,
        "composed": composed,
        "lock": lock,
        "ground": ground,
        "surface": surface,
        "prompt_fit": prompt_fit,
    }


def _seal_outputs(
    *,
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    summary: FlightSummary,
    client_summary: Mapping[str, object],
    run_dir: Path,
    agent_trace_hash: str,
    session_receipt: Path,
) -> dict[str, str]:
    assessment_rows: list[dict[str, object]] = []
    for state in summary.results:
        assessment_rows.append(
            {
                "sample_id": state.sample.sample_id,
                "observation": {
                    "valid": state.observation.valid,
                    "text": state.observation.text,
                },
                "families": [
                    {
                        "family_tag": row.family_tag,
                        "strict_valid": row.strict_valid,
                        "tolerant_valid": row.tolerant_valid,
                        "invalid_record_count": row.invalid_record_count,
                        "canonical_json": row.canonical_json,
                    }
                    for row in state.assessments
                ],
                "contacts": [asdict(row) for row in state.contacts],
                "final_response_sha256": hashlib.sha256(
                    state.final_response_text.encode("utf-8")
                ).hexdigest(),
            }
        )
    assessments_path = run_dir / "g7-assessment-states.jsonl"
    _write_jsonl(assessments_path, assessment_rows)
    trace_path = run_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
    source_by_id = {
        state.sample.sample_id: {
            "action": "g7-resolve",
            "source_agent_trace_manifest_sha256": agent_trace_hash,
            "source_artifact_path": str(trace_path),
            "source_artifact_sha256": _sha256(trace_path),
        }
        for state in summary.results
    }
    sink = TraceSink(run_dir, RUN_ID)
    output_rows = emit_composite_rows(
        texts={state.sample.sample_id: state.final_response_text for state in summary.results},
        source_by_id=source_by_id,
        sink=sink,
        variant="main",
    )
    output_trace_hash = sink.close()
    outputs = run_dir / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, output_rows)
    cost = dict(client_summary["cost"])
    cost["tool_calls"] = MODEL_CONTACTS
    manifest = build_manifest(
        repo_root=REPO,
        data_root=root,
        composed=context["composed"],
        plan=plan,
        verified_split=_verified_split(),
        session_receipt_path=session_receipt,
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
    if len(verify_bundle(manifest).outputs_rows) != 16:
        raise RuntimeError("G7 sealed bundle is not complete fixed16")
    return {
        "assessment_states": str(assessments_path),
        "assessment_states_sha256": _sha256(assessments_path),
        "outputs": str(outputs),
        "outputs_sha256": _sha256(outputs),
        "manifest": str(manifest),
        "manifest_sha256": _sha256(manifest),
        "agent_trace_manifest_sha256": agent_trace_hash,
        "output_trace_manifest_sha256": output_trace_hash,
    }


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
        merged[key] = float(merged.get(key, 0)) + float(recovery.cost.get(key, 0))
    merged["calls_used"] = int(merged["calls_used"])
    merged["prompt_tokens_total"] = int(merged["prompt_tokens_total"])
    merged["completion_tokens_total"] = int(merged["completion_tokens_total"])
    return merged


def launch(root: Path, *, recovery_trace: Path | None = None) -> Mapping[str, object]:
    """Start the receipt-pinned local service, execute once, and seal unscored."""
    context = static_preflight(root)
    recovery = (
        load_recovery_bundle(root, recovery_trace) if recovery_trace is not None else None
    )
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    attempt_id = f"attempt-{stamp.lower()}-g7-fixed16"
    plan = execution_plan(attempt_id)
    mission = root / "runs" / RUN_ID / f"flight-{stamp}"
    run_dir = mission / "g7"
    service_dir = mission / "service"
    run_dir.mkdir(parents=True, exist_ok=False)
    service_dir.mkdir()
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    _write_json(run_dir / "precontact-prompt-fit.json", context["prompt_fit"])
    _write_json(run_dir / "official-score-plan.json", OFFICIAL_SCORE_PLAN)
    values = context["composed"].values
    runtime_receipt = load_runtime_receipt(RUNTIME_RECEIPT)
    model_root = Path(str(values["model_materialization_root"]))
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath="receipts/runtime-q4km-mmproj-free.json",
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=model_root,
    )
    gate.assert_model_touch_allowed(plan, full_hash=True)
    parsed = urlparse(str(values["base_url"]))
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
        raise RuntimeError("G7 decoder must use an explicit loopback port")
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
            port=parsed.port,
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
            request_id_prefix="g7fixed16r" if recovery is not None else "g7fixed16",
            speech_feature_root=FEATURE_ROOT,
            speech_packet_bindings=surface.packet_bindings,
        )
        trace_sink = TraceSink(run_dir / "agent-trace", RUN_ID)
        summary = run_openjiuwen_phase(
            surface=surface,
            ground=context["ground"],
            client=client,
            trace_sink=trace_sink,
            recovery=recovery,
        )
        agent_trace_hash = trace_sink.close()
        trace_sink = None
        client_summary = client.close()
        client = None
        expected_current = MODEL_CONTACTS - (len(recovery.contacts) if recovery else 0)
        if client_summary.get("request_count") != expected_current:
            raise RuntimeError("G7 transport current request count drift")
        client_summary = dict(client_summary)
        client_summary["cost"] = _merge_recovery_cost(client_summary["cost"], recovery)
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
            session_receipt=session_receipt,
        )
        receipt: dict[str, object] = {
            "schema": "saea-a2t-g7-exhaustive-example-ground-fixed16-flight-v1",
            "status": "SEALED_UNSCORED",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "study_commit": context["commit"],
            "elapsed_seconds": time.perf_counter() - started,
            "model_contacts": MODEL_CONTACTS,
            "audio_bearing_contacts": 32,
            "text_only_contacts": 448,
            "delivered_speech_audio_seconds": 184.544,
            "adapter_carrier_reference_audio_seconds_cap": 2769,
            "scorer_contacts": 0,
            "reused_prior_contacts": len(recovery.contacts) if recovery else 0,
            "current_contacts": expected_current,
            **sealed,
        }
        _write_json(mission / "flight-receipt.json", receipt)
        return receipt
    except Exception as error:
        if trace_sink is not None:
            trace_sink.close()
            trace_sink = None
        if client is not None:
            client.close()
            client = None
        if session is not None:
            stop_session(
                session,
                runtime_receipt=runtime_receipt,
                runtime_root=RUNTIME_ROOT,
                force_after_timeout=True,
                receipt_path=stop_receipt,
            )
            session = None
        abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        transport_trace = run_dir / "transport-trace" / f"{RUN_ID}.trace.jsonl"
        trace_fields = (
            {
                "transport_trace": str(transport_trace.resolve()),
                "transport_trace_sha256": _sha256(transport_trace),
            }
            if transport_trace.is_file()
            else {}
        )
        _write_json(
            mission / "failure-receipt.json",
            {
                "run_id": RUN_ID,
                "attempt_id": attempt_id,
                "error": repr(error),
                "recovery_rule": "Reuse every complete hash-bound response triple; never recontact it.",
                **trace_fields,
            },
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--check", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--recover-from", type=Path, metavar="TRACE_JSONL")
    args = parser.parse_args(argv)
    root = data_root()
    if args.run or args.recover_from is not None:
        print(json.dumps(launch(root, recovery_trace=args.recover_from), sort_keys=True))
        return 0
    context = static_preflight(root)
    fit = context["prompt_fit"]
    print(
        json.dumps(
            {
                "status": "PREFLIGHT_PASSED",
                "contacts_sent": 0,
                "study_commit": context["commit"],
                "samples": 16,
                "planned_model_calls": 480,
                "max_evidence_total_tokens": max(
                    row["total_tokens"] for row in fit["evidence_prompts"]
                ),
                "worst_resolve_total_tokens": fit[
                    "resolve_worst_normalized_assessment_prompt"
                ]["total_tokens"],
                "worst_resolve_remaining_tokens": fit[
                    "resolve_worst_normalized_assessment_prompt"
                ]["remaining_tokens"],
                "scorer_contacts": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
