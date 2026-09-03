#!/usr/bin/env python3
"""Receipt-gated launcher for the G8 action-support fixed16 screen.

The default path is a complete contact-free preflight.  Execution is possible
only through ``launch(..., execute=True)`` and the normal frozen-core gate; in
particular an absent or inexact exposure-ledger row refuses before service,
model, audio, scorer, gold, or network contact.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from typing import Callable, Mapping, Sequence
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

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
from speech_aware_evidence_acquisition.rails.probes.a2t_g7_example_ground import (  # noqa: E402
    G7ExampleGround,
    MAX_OBSERVATION_ASCII_BYTES,
    Observation,
    PromptFit,
    ResolveContext,
    parse_family_assessment,
    parse_observation,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_g8_action_support import (  # noqa: E402
    BoundCall,
    G8ActionSupportCore,
    G8ActionSupportError,  # noqa: F401 - public launcher error surface
    MAX_BINDING_RESPONSE_UTF8_BYTES,
    MAX_SELECTION_CALLS,
    ToolBindings,
    ToolSelection,
    build_g8_trace_documents,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_factor_top1_bundle import (  # noqa: E402
    emit_composite_rows,
)


RUN_ID = "SAEA-A2T-G8-ACTION-SUPPORT-REACHABILITY-FIXED16-V1"
MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-g8-action-support-reachability-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g8-action-support-reachability-fixed16-v1"
SPLIT_ID = "A2T-G8-ACTION-SUPPORT-FIXED16"
SPLIT_IDENTITY_HASH = "06acbcf6b9bd3fde67c1de8da622d6d446a5ec993926be3f58c42968dddb250b"
ROSTER_SHA256 = "c752fa6e273edbc064a66c388ae5b7dee31d456bcc210af0e346b9dac62f3888"
GROUND_SHA256 = "a5bb788a64db320b8d09de3712ede38f46c5395d8e7dd1932d8acbbf8cedc855"
GROUND_STRUCTURED_SHA256 = "f890e2a0975c4517e1909ecb2dee04d38eeaa05c4f0d9830b41ac634dbc9d830"
GROUND_RECEIPT_SHA256 = "87fea65bb2d9c36444c28311778f0a81fd968fbf0fb69192608080e764495536"
G1_RECEIPT_SHA256 = "b42f0953a0d168955ba5ddfc77f2c300aacb54e48dce902d1b3d4a109c1996db"
M0_SHA256 = "dea60ff1e63fd2ef11c93edf8808217062fea3f0565ed5b60f136264bc6a9467"
RUNTIME_RECEIPT_SHA256 = "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
OPENJIUWEN_VERSION = "0.1.16.post2"
RUNTIME_ROOT = Path("/home/chao")
FEATURE_ROOT = Path("/home/chao/feat-cache/a2t-q4km-packets-04ccc72a")
PROMOTION_RECEIPT = FEATURE_ROOT / "A2T-G1-104-promotion.json"
PROMOTION_RECEIPT_SHA256 = "be07c69c030fc12e56e4e2e1f5e08423636a84fb823d16293fae7bf5819218bc"
WORKFLOW_TIMEOUT_SECONDS = 14_400.0
CONTROL_INSTRUCTION = "Follow the system instruction for this registered contact."
OFFICIAL_SCORERS = ("a2t-toolcall",)

SAMPLE_COUNT = 16
SHARED_CONTACTS_PER_SAMPLE = 29
BRANCH_CONTACTS_PER_SAMPLE = 5
CONTACTS_PER_SAMPLE = 34
MODEL_CONTACTS = SAMPLE_COUNT * CONTACTS_PER_SAMPLE
# Receipt-bound G8 selected rows total 80.213 seconds.  Every one of the 34
# future contacts per row carries its exact speech packet, so 80.213 * 34 is
# rounded upward once to the registered carrier-accounting reservation.
REPEATED_SPEECH_AUDIO_SECONDS = 80.213
PLANNED_SPEECH_AUDIO_SECONDS = 2728
SLOTS = 2
MAX_CONCURRENT_MODEL_REQUESTS = 2
QUEUE_DEPTH = 4
OBS_COMPLETION_TOKENS = 512
EVIDENCE_COMPLETION_TOKENS = 512
RESOLVE_COMPLETION_TOKENS = 1024
# These are intentionally visible future-update points until the G8 core gains
# pre-registered response-size constants.  They are not model contacts.
SELECTION_COMPLETION_TOKENS = 4096
BINDING_COMPLETION_TOKENS = 12288
SPECIAL_TOKEN_RESERVE = 512
WAVE_ORDER = (
    "OBS",
    "EVIDENCE",
    "BRANCH_ROUND_1",
    "DECOMPOSED_BIND",
    "DECOMPOSED_RESOLVE",
)
BRANCH_ORDER = (
    "STOP_M0",
    "EXHAUSTIVE_G7",
    "SUPPORT_ONLY_RESOLVE",
    "DECOMPOSED_SELECT_BIND_RESOLVE",
)

COMPOSED_CONFIG_SHA256 = "4bc209b1967364a05748f1c8c53d2898c9b27b0d8c4daa02604e3a8cac8cbbfd"
PROTOCOL_SHA256 = "69ee892a08a51adbb61a18b9f6827a9f33e7669155325fd198de384b5fab044e"

G8_ROSTER = REPO / "docs/receipts/a2t/A2T-G8-ACTION-SUPPORT-FIXED16.json"
G1_RECEIPT = REPO / "docs/receipts/a2t/A2T-G1-104.json"
BASELINE = REPO / "configs/baseline/a2t-g8-action-support-reachability-agentloop.json"
EXPERIMENT = REPO / "configs/experiment/a2t-g8-action-support-reachability-fixed16-v1.json"
GROUND_CORPUS = REPO / "knowledge/audio2tool/g7-construction-example-ground-v1/corpus.txt"
GROUND_STRUCTURED = REPO / "knowledge/audio2tool/g7-construction-example-ground-v1/ground.json"
GROUND_RECEIPT = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-g7-exhaustive-example-ground-fixed16-v1/ground-receipt.json"
)
RUNTIME_RECEIPT = REPO / "docs/receipts/runtime-q4km-mmproj-free.json"
M0_RELPATH = Path(
    "runs/SAEA-A2T-G1/attempt-20260825T100735Z-a2tg1m0/arm1-m0-outputs.jsonl"
)


@dataclass(frozen=True)
class BranchDerivative:
    """A complete contact-free branch output source before manifest materialization."""

    branch: str
    texts: Mapping[str, str]
    new_model_contacts: int
    source_kind: str


@dataclass(frozen=True)
class RuntimeSurface:
    """Exact selected speech carriers and promoted packet metadata."""

    samples: tuple[Audio2ToolSample, ...]
    packet_bindings: Mapping[str, Mapping[str, str]]
    speech_feature_tokens_by_sample: Mapping[str, int]


@dataclass(frozen=True)
class ContactRecord:
    sample_id: str
    contact_id: str
    stage: str
    slot_id: int
    response_sha256: str
    prompt_fit: Mapping[str, object]


@dataclass
class _WorkflowState:
    sample: Audio2ToolSample
    g7: G7ExampleGround
    g8: G8ActionSupportCore
    packet_binding: Mapping[str, str]
    speech_tokens: int
    stage: str = "OBS"
    current: tuple[object, ...] = ()
    observation: Observation | None = None
    assessments: tuple[object, ...] = ()
    normalized_sheet: object | None = None
    support_sheet: object | None = None
    selection: ToolSelection | None = None
    bindings: ToolBindings | None = None
    branch_texts: dict[str, str] = field(default_factory=dict)
    contacts: list[ContactRecord] = field(default_factory=list)
    pending_fits: dict[str, Mapping[str, object]] = field(default_factory=dict)


@dataclass(frozen=True)
class FlightSummary:
    results: tuple[_WorkflowState, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _byte_upper_bound(text: str) -> int:
    return len(text.encode("utf-8"))


def _verify_repeated_speech_reservation() -> float:
    """Derive the future packet-reuse reservation from receipt metadata only."""
    roster = json.loads(G8_ROSTER.read_text(encoding="utf-8"))
    g1 = json.loads(G1_RECEIPT.read_text(encoding="utf-8"))
    selected = roster.get("selected")
    items = g1.get("items")
    if not isinstance(selected, list) or not isinstance(items, list):
        raise RuntimeError("G8/G1 receipt lacks the selected item surfaces")
    selected_ids = {row.get("sample_id") for row in selected if isinstance(row, Mapping)}
    by_id = {
        row.get("sample_id"): row.get("audio_seconds")
        for row in items
        if isinstance(row, Mapping)
    }
    if len(selected_ids) != SAMPLE_COUNT or None in selected_ids or not selected_ids <= set(by_id):
        raise RuntimeError("G8 receipt identities are not covered by G1 audio metadata")
    try:
        seconds = sum(float(by_id[sample_id]) for sample_id in selected_ids)
    except (TypeError, ValueError) as error:
        raise RuntimeError("G1 receipt audio duration is malformed") from error
    if abs(seconds - REPEATED_SPEECH_AUDIO_SECONDS) > 1e-9:
        raise RuntimeError("G8 repeated-speech duration drift")
    if math.ceil(seconds * CONTACTS_PER_SAMPLE) != PLANNED_SPEECH_AUDIO_SECONDS:
        raise RuntimeError("G8 repeated-speech reservation drift")
    return seconds


def execution_plan(attempt_id: str) -> ExecutionPlan:
    """Return the future G8 plan shape; it does not authorize a model touch."""
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=MODEL_CONTACTS,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=PLANNED_SPEECH_AUDIO_SECONDS,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def load_m0_outputs(path: Path, expected_sample_ids: Sequence[str]) -> dict[str, str]:
    """Load the pinned G1 M0 response source by exact sample identity."""
    expected = tuple(expected_sample_ids)
    if not expected or len(expected) != len(set(expected)):
        raise RuntimeError("M0 expected identities must be non-empty and unique")
    texts: dict[str, str] = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        row = json.loads(line)
        sample_id = row.get("sample_id")
        text = row.get("direct_response_text", row.get("text"))
        if not isinstance(sample_id, str) or not isinstance(text, str):
            raise RuntimeError(f"M0 row {line_number} lacks exact identity or text")
        if sample_id in texts:
            raise RuntimeError(f"M0 contains duplicate identity {sample_id!r}")
        texts[sample_id] = text
    if not set(expected) <= set(texts):
        raise RuntimeError("M0 source does not cover every selected identity")
    return {sample_id: texts[sample_id] for sample_id in expected}


def load_runtime_surface() -> RuntimeSurface:
    """Join the frozen G8 roster to G1 media and promoted packet metadata."""
    for path, expected in (
        (G8_ROSTER, ROSTER_SHA256),
        (G1_RECEIPT, G1_RECEIPT_SHA256),
        (PROMOTION_RECEIPT, PROMOTION_RECEIPT_SHA256),
    ):
        if _sha256(path) != expected:
            raise RuntimeError(f"G8 runtime identity hash drift: {path.name}")
    roster = json.loads(G8_ROSTER.read_text(encoding="utf-8"))
    g1 = json.loads(G1_RECEIPT.read_text(encoding="utf-8"))
    promotion = json.loads(PROMOTION_RECEIPT.read_text(encoding="ascii"))
    if roster.get("split_identity_hash") != SPLIT_IDENTITY_HASH:
        raise RuntimeError("G8 roster split identity drift")
    g1_by_id = {row["sample_id"]: row for row in g1["items"]}
    promoted = {row["packet_id"]: row for row in promotion["packets"]}
    samples: list[Audio2ToolSample] = []
    bindings: dict[str, Mapping[str, str]] = {}
    speech_tokens: dict[str, int] = {}
    for selected in roster["selected"]:
        sample_id = selected["sample_id"]
        item = g1_by_id.get(sample_id)
        if item is None or (item["key"], item["tier"]) != (
            selected["key"],
            selected["tier"],
        ):
            raise RuntimeError("G8 roster row is absent from frozen G1")
        packet_id = item["packet_id"]
        packet_path = PROMOTION_RECEIPT.parent / packet_id / "packet.json"
        packet = json.loads(packet_path.read_text(encoding="ascii"))
        promoted_row = promoted.get(packet_id)
        if (
            promoted_row is None
            or packet["packet_sha256"] != promoted_row["packet_sha256"]
            or packet["audio_sha256"] != item["audio_sha256"]
        ):
            raise RuntimeError("G8 promoted packet identity drift")
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
        speech_tokens[sample_id] = sum(int(chunk["n_tokens"]) for chunk in packet["chunks"])
    if (
        len(samples) != SAMPLE_COUNT
        or max(speech_tokens.values(), default=-1) != 169
        or sum(speech_tokens.values()) != 1157
        or abs(sum(sample.audio_seconds for sample in samples) - REPEATED_SPEECH_AUDIO_SECONDS)
        > 1e-9
    ):
        raise RuntimeError("G8 runtime sample, token, or duration geometry drift")
    return RuntimeSurface(tuple(samples), bindings, speech_tokens)


def load_ground() -> ConstructionExampleGround:
    """Load the frozen G7 structured ground without reopening construction rows."""
    for path, expected in (
        (GROUND_CORPUS, GROUND_SHA256),
        (GROUND_STRUCTURED, GROUND_STRUCTURED_SHA256),
        (GROUND_RECEIPT, GROUND_RECEIPT_SHA256),
    ):
        if _sha256(path) != expected:
            raise RuntimeError(f"G8 frozen ground hash drift: {path.name}")
    document = json.loads(GROUND_STRUCTURED.read_text(encoding="ascii"))
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
        raise RuntimeError("G8 frozen structured ground identity drift")
    return ground


def _full_observation() -> Observation:
    seed = "The speaker describes a device request in bounded plain English. "
    text = (seed * (MAX_OBSERVATION_ASCII_BYTES // len(seed) + 1))[
        :MAX_OBSERVATION_ASCII_BYTES
    ]
    return parse_observation(text, ())


def _fit_dict(fit: PromptFit) -> dict[str, int | str]:
    return {
        "contact_id": fit.contact_id,
        "prompt_tokens": fit.prompt_tokens,
        "completion_tokens": fit.completion_tokens,
        "total_tokens": fit.total_tokens,
        "remaining_tokens": fit.remaining_tokens,
    }


def _measure(
    *,
    contact_id: str,
    rendered_request: str,
    completion_tokens: int,
    speech_feature_tokens: int,
) -> PromptFit:
    """Measure the exact serialized contact immediately before a future send."""
    prompt = (
        _byte_upper_bound(rendered_request)
        + speech_feature_tokens
        + SPECIAL_TOKEN_RESERVE
    )
    total = prompt + completion_tokens
    if total > 24_576:
        raise ValueError("G8 prompt is refused before contact below 8192 headroom")
    return PromptFit(contact_id, prompt, completion_tokens, total, 32_768 - total)


def _packet_messages(stage: str, context: object) -> tuple[Mapping[str, object], ...]:
    packet = {
        "type": "input_speech_features",
        "speech_features": {
            "packet_id": "preflight/query",
            "sha256": "0" * 64,
            "role": "query",
        },
    }
    instruction = str(getattr(context, "instruction"))
    if stage == "OBS":
        return ({"role": "system", "content": instruction}, {"role": "user", "content": [packet]})
    if getattr(context, "stage", None) == "DECOMPOSED_SELECT":
        # Preserve the complete core surface while avoiding repeated family
        # labels and repeated tool identities.  Status characters and sparse
        # evidence are position-aligned to the displayed frozen tool order.
        families: list[list[object]] = []
        for row in context.family_operations:
            if not families or families[-1][0] != row.family_tag:
                families.append([row.family_tag, row.family_objective, []])
            families[-1][2].append([row.tool_name, row.operation])
        legend = {"support": "s", "contradict": "c", "uncertain": "u"}
        supplied = json.dumps(
            {
                "observation": context.observation,
                "families": families,
                "status_order": "tools in families order",
                "status_legend": "s=support,c=contradict,u=uncertain",
                "statuses": "".join(legend[row.status] for row in context.status_surface),
                "evidence": [
                    [index, list(row.evidence)]
                    for index, row in enumerate(context.status_surface)
                    if row.evidence
                ],
                "instruction": context.instruction,
            },
            ensure_ascii=True,
            separators=(",", ":"),
        )
    elif hasattr(context, "render_prompt"):
        supplied = context.render_prompt()
    elif isinstance(context, ResolveContext):
        sheet_name = (
            "SUPPORT-ONLY EXECUTION SHEET"
            if context.stage == "SUPPORT_ONLY_RESOLVE"
            else "ALL-TOOL EXECUTION SHEET WITH 152 NORMALIZED ASSESSMENTS"
        )
        supplied = (
            f"OBSERVATION\n{context.observation}\n\n{sheet_name}\n"
            f"{context.execution_sheet}"
        )
    else:
        supplied = (
            f"OBS o1\n{context.observation}\n\nFAMILY CONSTRUCTION EXAMPLES\n"
            f"{context.family_bundle_text}"
        )
    return (
        {"role": "system", "content": instruction},
        {"role": "user", "content": [{"type": "text", "text": supplied}, packet]},
    )


def _exact_request(messages: object, context: object) -> str:
    return json.dumps(
        {
            "messages": messages,
            "agent_control": {
                "contact_id": str(getattr(context, "contact_id")),
                "instruction": "Follow the system instruction for this registered contact.",
            },
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def preflight_ground(
    ground: object, *, speech_feature_tokens_max: int
) -> dict[str, object]:
    """Construct every future request shape without contacting any runtime."""
    if getattr(ground, "sha256", None) != GROUND_SHA256:
        raise ValueError("G8 ground SHA-256 drift")
    if getattr(ground, "receipt", {}).get("schema") != (
        "saea-a2t-construction-example-ground-receipt-v1"
    ):
        raise ValueError("G8 ground receipt schema drift")
    g7 = G7ExampleGround(ground.bundles)
    g8 = G8ActionSupportCore(ground.bundles)
    observation = _full_observation()
    obs_context = SimpleNamespace(contact_id="g8-obs", instruction=(
        "Listen to the original complete dialogue. Describe the spoken request in bounded "
        "plain English. Do not name tools, propose a final answer, or add metadata."
    ))
    obs = _measure(
        contact_id="g8-obs",
        rendered_request=_exact_request(_packet_messages("OBS", obs_context), obs_context),
        completion_tokens=OBS_COMPLETION_TOKENS,
        speech_feature_tokens=speech_feature_tokens_max,
    )
    evidence_contexts = g7.build_evidence_contexts(observation)
    evidence = tuple(
        _measure(
            contact_id=context.contact_id,
            rendered_request=_exact_request(_packet_messages("EVIDENCE", context), context),
            completion_tokens=EVIDENCE_COMPLETION_TOKENS,
            speech_feature_tokens=speech_feature_tokens_max,
        )
        for context in evidence_contexts
    )
    assessments = tuple(
        parse_family_assessment(
            "{}", family_tag=context.family_tag, family_tool_names=context.tool_names
        )
        for context in evidence_contexts
    )
    sheet = g8.build_normalized_sheet(assessments)
    exhaustive = g7.build_resolve_context(observation, assessments)
    support = ResolveContext(
        contact_id="g8-support-only-resolve",
        stage="SUPPORT_ONLY_RESOLVE",
        uses_audio=True,
        observation=observation.text,
        assessments=g8.build_support_only_sheet(sheet).assessments,
        tool_names=tuple(),
        execution_sheet=g8.build_support_only_sheet(sheet).text,
        instruction=(
            "Use only this sealed support-only sheet and the original speech. Return only "
            "the unchanged official tool-call JSON array without a fallback."
        ),
    )
    selection = g8.build_selection_context(observation, sheet)
    repeated_name = g8.registry_order[0][1]
    maximum_selection = g8.parse_selection(
        json.dumps([repeated_name] * MAX_SELECTION_CALLS, separators=(",", ":"))
    )
    binding = g8.build_binding_context(observation, maximum_selection)
    base_values = [
        {"name": repeated_name, "arguments": {}} for _ in range(MAX_SELECTION_CALLS)
    ]
    base_values[0]["arguments"] = {"value": ""}
    base_json = json.dumps(base_values, ensure_ascii=True, separators=(",", ":"))
    padding = MAX_BINDING_RESPONSE_UTF8_BYTES - len(base_json.encode("utf-8"))
    if padding < 0:
        raise RuntimeError("G8 maximum binding envelope construction overflow")
    base_values[0]["arguments"] = {"value": "x" * padding}
    maximum_binding_json = json.dumps(
        base_values, ensure_ascii=True, separators=(",", ":")
    )
    if len(maximum_binding_json.encode("utf-8")) != MAX_BINDING_RESPONSE_UTF8_BYTES:
        raise RuntimeError("G8 maximum binding envelope does not reach its frozen cap")
    maximum_calls = tuple(
        BoundCall(row["name"], json.dumps(row["arguments"], separators=(",", ":")))
        for row in base_values
    )
    maximum_bindings = ToolBindings(maximum_calls, maximum_binding_json)
    decomposed = g8.build_resolve_context(
        observation, maximum_selection, maximum_bindings
    )

    def measured(stage: str, context: object, completion: int) -> PromptFit:
        return _measure(
            contact_id=str(getattr(context, "contact_id")),
            rendered_request=_exact_request(_packet_messages(stage, context), context),
            completion_tokens=completion,
            speech_feature_tokens=speech_feature_tokens_max,
        )

    return {
        "schema": "saea-a2t-g8-action-support-precontact-report-v1",
        "run_id": RUN_ID,
        "split_id": SPLIT_ID,
        "split_identity_hash": SPLIT_IDENTITY_HASH,
        "contacts": MODEL_CONTACTS,
        "contacts_per_sample": CONTACTS_PER_SAMPLE,
        "shared_contacts_per_sample": SHARED_CONTACTS_PER_SAMPLE,
        "branch_contacts_per_sample": BRANCH_CONTACTS_PER_SAMPLE,
        "family_count": len(ground.bundles),
        "tool_count": len(g7.tool_names),
        "slots": SLOTS,
        "max_concurrent_model_requests": MAX_CONCURRENT_MODEL_REQUESTS,
        "queue_depth": QUEUE_DEPTH,
        "dynamic_measurement": "immediately-before-every-contact",
        "serialized_request_counter": "utf8-byte-upper-bound",
        "special_token_reserve": SPECIAL_TOKEN_RESERVE,
        "prompt_fits": {
            "obs": _fit_dict(obs),
            "evidence": [_fit_dict(fit) for fit in evidence],
            "exhaustive_resolve": _fit_dict(
                measured("EXHAUSTIVE_G7", exhaustive, RESOLVE_COMPLETION_TOKENS)
            ),
            "support_only_resolve": _fit_dict(
                measured("SUPPORT_ONLY_RESOLVE", support, RESOLVE_COMPLETION_TOKENS)
            ),
            "decomposed_select": _fit_dict(
                measured("DECOMPOSED_SELECT", selection, SELECTION_COMPLETION_TOKENS)
            ),
            "decomposed_bind_maximum": _fit_dict(
                measured("DECOMPOSED_BIND", binding, BINDING_COMPLETION_TOKENS)
            ),
            "decomposed_resolve_maximum": _fit_dict(
                measured("DECOMPOSED_RESOLVE", decomposed, RESOLVE_COMPLETION_TOKENS)
            ),
        },
    }


def _execute_openjiuwen(*args: object, **kwargs: object) -> object:
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    return execute_speech_agent_workflows(*args, **kwargs)


def _completion_tokens(stage: str) -> int:
    if stage == "OBS":
        return OBS_COMPLETION_TOKENS
    if stage == "EVIDENCE":
        return EVIDENCE_COMPLETION_TOKENS
    if stage == "DECOMPOSED_SELECT":
        return SELECTION_COMPLETION_TOKENS
    if stage == "DECOMPOSED_BIND":
        return BINDING_COMPLETION_TOKENS
    return RESOLVE_COMPLETION_TOKENS


def _support_context(state: _WorkflowState) -> ResolveContext:
    assert state.observation is not None and state.support_sheet is not None
    sheet = state.support_sheet
    return ResolveContext(
        contact_id="g8-support-only-resolve",
        stage="SUPPORT_ONLY_RESOLVE",
        uses_audio=True,
        observation=state.observation.text,
        assessments=sheet.assessments,
        tool_names=tuple(row.tool_name for row in sheet.assessments),
        execution_sheet=sheet.text,
        instruction=(
            "Use only this sealed support-only sheet and the original speech. Return only "
            "the unchanged official tool-call JSON array without a fallback."
        ),
    )


def run_openjiuwen_phase(
    *,
    surface: RuntimeSurface,
    ground: ConstructionExampleGround,
    client: FrozenCoreClient,
    trace_sink: TraceSink,
    workflow_runner: Callable[..., object] = _execute_openjiuwen,
) -> FlightSummary:
    """Execute five causal waves with sample-affine state and strict fan-in."""
    if len(surface.samples) != SAMPLE_COUNT:
        raise RuntimeError("G8 execution requires the exact sixteen selected samples")
    g7 = G7ExampleGround(ground.bundles)
    g8 = G8ActionSupportCore(ground.bundles)
    states = [
        _WorkflowState(
            sample=sample,
            g7=g7,
            g8=g8,
            packet_binding=surface.packet_bindings[sample.sample_id],
            speech_tokens=surface.speech_feature_tokens_by_sample[sample.sample_id],
        )
        for sample in surface.samples
    ]
    terminal = threading.Event()

    def prepare(state: _WorkflowState, session: object) -> int:
        if state.stage == "OBS":
            state.current = (
                SimpleNamespace(
                    contact_id="g8-obs",
                    instruction=(
                        "Listen to the original complete dialogue. Describe the spoken request "
                        "in bounded plain English. Do not name tools, propose a final answer, "
                        "or add metadata."
                    ),
                ),
            )
        elif state.stage == "EVIDENCE":
            assert state.observation is not None
            state.current = state.g7.build_evidence_contexts(state.observation)
        elif state.stage == "BRANCH_ROUND_1":
            assert state.observation is not None and state.normalized_sheet is not None
            state.current = (
                state.g7.build_resolve_context(state.observation, state.assessments),
                _support_context(state),
                state.g8.build_selection_context(state.observation, state.normalized_sheet),
            )
        elif state.stage == "DECOMPOSED_BIND":
            assert state.observation is not None and state.selection is not None
            state.current = (
                state.g8.build_binding_context(state.observation, state.selection),
            )
        elif state.stage == "DECOMPOSED_RESOLVE":
            assert (
                state.observation is not None
                and state.selection is not None
                and state.bindings is not None
            )
            state.current = (
                state.g8.build_resolve_context(
                    state.observation, state.selection, state.bindings
                ),
            )
        else:
            state.current = ()
        update = getattr(session, "update_global_state", None)
        if callable(update):
            update({"g8_stage": state.stage, "g8_sample_id": state.sample.sample_id})
        return len(state.current)

    def invoke(
        state: _WorkflowState, branch_index: int, slot_id: int
    ) -> Mapping[str, object]:
        if terminal.is_set():
            raise RuntimeError("G8 attempt is terminal; no later contact is allowed")
        try:
            context = state.current[branch_index]
            messages = _packet_messages(state.stage, context)
            # Replace the preflight packet with the receipt-bound sample packet before
            # serializing and measuring the exact request that will be sent.
            for part in messages[1]["content"]:
                if isinstance(part, dict) and part.get("type") == "input_speech_features":
                    part["speech_features"] = {
                        **state.packet_binding,
                        "role": "query",
                    }
            contact_stage = str(getattr(context, "stage", state.stage))
            fit = _measure(
                contact_id=context.contact_id,
                rendered_request=_exact_request(messages, context),
                completion_tokens=_completion_tokens(contact_stage),
                speech_feature_tokens=state.speech_tokens,
            )
            fit_document = _fit_dict(fit)
            state.pending_fits[context.contact_id] = fit_document
            text = client.complete(
                messages,
                speech_feature_sample_id=state.sample.sample_id,
                key_representation_id=f"g8-action-support:{contact_stage.lower()}",
                matcher_policy_id="saea-a2t-g8-action-support-reachability-v1",
                agent_state=(),
                agent_contact_id=context.contact_id,
                contact_instruction=CONTROL_INSTRUCTION,
                decoding_params={
                    "max_tokens": fit.completion_tokens,
                    "temperature": 0,
                    "id_slot": slot_id,
                },
            )
            return {
                "response_text": text,
                "slot_id": slot_id,
                "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        except BaseException:
            terminal.set()
            raise

    def aggregate_unchecked(
        state: _WorkflowState,
        responses: tuple[Mapping[str, object], ...],
        session: object,
    ) -> None:
        del session
        if len(responses) != len(state.current):
            raise RuntimeError("G8 fan-in contact count drift")
        for context, response in zip(state.current, responses, strict=True):
            text = str(response["response_text"])
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if response["response_sha256"] != digest:
                raise RuntimeError("G8 response hash mismatch")
            state.contacts.append(
                ContactRecord(
                    state.sample.sample_id,
                    context.contact_id,
                    context.stage if hasattr(context, "stage") else state.stage,
                    int(response["slot_id"]),
                    digest,
                    state.pending_fits.pop(context.contact_id),
                )
            )
        if state.stage == "OBS":
            state.observation = parse_observation(
                str(responses[0]["response_text"]), state.g7.tool_names
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
            state.normalized_sheet = state.g8.build_normalized_sheet(state.assessments)
            state.support_sheet = state.g8.build_support_only_sheet(state.normalized_sheet)
            state.stage = "BRANCH_ROUND_1"
        elif state.stage == "BRANCH_ROUND_1":
            state.branch_texts["EXHAUSTIVE_G7"] = str(responses[0]["response_text"])
            state.branch_texts["SUPPORT_ONLY_RESOLVE"] = str(responses[1]["response_text"])
            # Strict parsing is deliberately inside fan-in: any invalid SELECT
            # raises before BIND can be prepared or contacted.
            state.selection = state.g8.parse_selection(str(responses[2]["response_text"]))
            state.stage = "DECOMPOSED_BIND"
        elif state.stage == "DECOMPOSED_BIND":
            assert state.selection is not None
            # Likewise, invalid BIND raises before final resolve or any sealing.
            state.bindings = state.g8.parse_bindings(
                str(responses[0]["response_text"]), state.selection
            )
            state.stage = "DECOMPOSED_RESOLVE"
        else:
            state.branch_texts["DECOMPOSED_SELECT_BIND_RESOLVE"] = str(
                responses[0]["response_text"]
            )
            state.stage = "DONE"

    def aggregate(
        state: _WorkflowState,
        responses: tuple[Mapping[str, object], ...],
        session: object,
    ) -> None:
        if terminal.is_set():
            raise RuntimeError("G8 attempt is terminal; no later aggregation is allowed")
        try:
            aggregate_unchecked(state, responses, session)
        except BaseException:
            terminal.set()
            raise

    completed = workflow_runner(
        states,
        prepare_wave=prepare,
        invoke_contact=invoke,
        aggregate_wave=aggregate,
        should_continue=lambda state: state.stage != "DONE",
        branch_count=28,
        slot_count=SLOTS,
        queue_depth=QUEUE_DEPTH,
        workflow_timeout_seconds=WORKFLOW_TIMEOUT_SECONDS,
    )
    if list(completed) != states or sum(len(state.contacts) for state in states) != MODEL_CONTACTS:
        raise RuntimeError("G8 did not complete exactly 544 contacts")
    for state in states:
        if len(state.contacts) != CONTACTS_PER_SAMPLE or state.stage != "DONE":
            raise RuntimeError("G8 sample-affine contact geometry drift")
        for index, contact in enumerate(state.contacts):
            trace_sink.emit(
                "COST",
                f"g8:{state.sample.sample_id}:contact-audit:{index:02d}",
                {
                    "sample_id": contact.sample_id,
                    "contact_id": contact.contact_id,
                    "stage": contact.stage,
                    "slot_id": contact.slot_id,
                    "response_sha256": contact.response_sha256,
                    "prompt_fit": dict(contact.prompt_fit),
                },
            )
        assert (
            state.observation is not None
            and state.normalized_sheet is not None
            and state.support_sheet is not None
            and state.selection is not None
            and state.bindings is not None
        )
        trace = build_g8_trace_documents(
            sample_id=state.sample.sample_id,
            observation=state.observation,
            normalized_sheet=state.normalized_sheet,
            support_only_sheet=state.support_sheet,
            selection=state.selection,
            bindings=state.bindings,
            final_response_text=state.branch_texts["DECOMPOSED_SELECT_BIND_RESOLVE"],
        )
        trace_sink.emit("OBS", f"g8:{state.sample.sample_id}:obs", trace["obs_state"])
        trace_sink.emit("ORG", f"g8:{state.sample.sample_id}:org", trace["org_state"])
        trace_sink.emit("SUPPLY", f"g8:{state.sample.sample_id}:supply", trace["supply_state"])
        for branch in BRANCH_ORDER[1:]:
            trace_sink.emit(
                "USE",
                f"g8:{state.sample.sample_id}:use:{branch.lower()}",
                {
                    "sample_id": state.sample.sample_id,
                    "branch": branch,
                    "final_response_text": state.branch_texts[branch],
                    "final_response_sha256": hashlib.sha256(
                        state.branch_texts[branch].encode("utf-8")
                    ).hexdigest(),
                },
            )
    return FlightSummary(tuple(states))


def physical_and_logical_costs() -> dict[str, object]:
    """Report physical spend once and nonadditive macro-action costs explicitly."""
    return {
        "physical_model_contacts": MODEL_CONTACTS,
        "shared_physical_contacts": SAMPLE_COUNT * SHARED_CONTACTS_PER_SAMPLE,
        "branch_physical_contacts": SAMPLE_COUNT * BRANCH_CONTACTS_PER_SAMPLE,
        "logical_action_contacts_nonadditive": True,
        "logical_action_contacts": {
            "STOP_M0": 0,
            "EXHAUSTIVE_G7": 480,
            "SUPPORT_ONLY_RESOLVE": 480,
            "DECOMPOSED_SELECT_BIND_RESOLVE": 512,
        },
    }


def _validate_client_summary(
    summary: Mapping[str, object],
) -> Mapping[str, object]:
    """Require the exact physical contact count and its transport trace seal."""
    if summary.get("request_count") != MODEL_CONTACTS:
        raise RuntimeError("G8 transport request count is not exactly 544")
    digest = summary.get("trace_manifest_hash")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise RuntimeError("G8 transport trace manifest hash is malformed")
    return summary


def build_branch_derivatives(
    *,
    sample_ids: Sequence[str],
    m0_texts: Mapping[str, str],
    branch_final_texts: Mapping[str, Mapping[str, str]],
) -> dict[str, BranchDerivative]:
    """Build four complete output sources with exact identity preservation."""
    ids = tuple(sample_ids)
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("branch derivatives require non-empty unique sample identities")
    required = set(BRANCH_ORDER[1:])
    if set(branch_final_texts) != required or set(m0_texts) != set(ids):
        raise ValueError("branch derivatives require exact identity-complete branch inputs")
    derivatives: dict[str, BranchDerivative] = {
        "STOP_M0": BranchDerivative("STOP_M0", dict(m0_texts), 0, "frozen-g1-m0")
    }
    contacts = {
        "EXHAUSTIVE_G7": SAMPLE_COUNT,
        "SUPPORT_ONLY_RESOLVE": SAMPLE_COUNT,
        "DECOMPOSED_SELECT_BIND_RESOLVE": SAMPLE_COUNT * 3,
    }
    for branch in BRANCH_ORDER[1:]:
        texts = branch_final_texts[branch]
        if set(texts) != set(ids) or any(not isinstance(texts[item], str) for item in ids):
            raise ValueError("branch derivatives require exact identity-complete final texts")
        derivatives[branch] = BranchDerivative(
            branch, {sample_id: texts[sample_id] for sample_id in ids}, contacts[branch], "sealed-g8"
        )
    return derivatives


def parallel_score_plan(
    branch_manifests: Mapping[str, Path],
) -> dict[str, object]:
    """Describe one complete-manifest scorer process per branch."""
    if set(branch_manifests) != set(BRANCH_ORDER):
        raise ValueError("score plan requires all four complete branch manifests")
    return {
        "schema": "saea-parallel-score-plan-v1",
        "experiment_id": RUN_ID,
        "workers": 4,
        "processes_per_job": 1,
        "dataset_sharding": False,
        "shard_metric_averaging": False,
        "include_per_sample": True,
        "invocation": (
            "python -B -m speech_aware_evidence_acquisition.core.driver "
            "score-batch --jobs <jobs.jsonl> --output-dir <scores> --workers 4 "
            "--include-per-sample"
        ),
        "jobs": [
            {
                "job_id": branch.lower().replace("_", "-"),
                "branch": branch,
                "manifest": str(branch_manifests[branch]),
                "row_count": SAMPLE_COUNT,
                "whole_manifest_only": True,
                "include_per_sample": True,
            }
            for branch in BRANCH_ORDER
        ],
    }


def future_oracle_manifest_spec(
    *, branch_manifests: Mapping[str, Path]
) -> dict[str, object]:
    """Specify the later model-free oracle derivative without selecting rows."""
    if set(branch_manifests) != set(BRANCH_ORDER):
        raise ValueError("future oracle requires all four complete branch manifests")
    return {
        "source_branch_order": list(BRANCH_ORDER),
        "source_manifests": {branch: str(branch_manifests[branch]) for branch in BRANCH_ORDER},
        "model_contacts": 0,
        "scoring_invocations": 1,
        "selection_rule": "post-score official exact, slot F1, tool correctness, frozen branch order",
    }


def _verified_split() -> VerifiedSplit:
    roster = json.loads(G8_ROSTER.read_text(encoding="utf-8"))
    ids = tuple(row["sample_id"] for row in roster["selected"])
    return VerifiedSplit(
        name=SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in ids),
        identity_hash=SPLIT_IDENTITY_HASH,
    )


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


def _bind_official_scorer(manifest_path: Path) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing = manifest.get("scorers")
    if existing not in ([], list(OFFICIAL_SCORERS)):
        raise RuntimeError("G8 manifest carries an unexpected scorer")
    manifest["scorers"] = list(OFFICIAL_SCORERS)
    _write_json(manifest_path, manifest)


def static_preflight(root: Path) -> dict[str, object]:
    """Run all contact-free asset, runtime, geometry, and prompt checks."""
    commit = require_clean_study_repo(REPO)
    for path, expected in (
        (G8_ROSTER, ROSTER_SHA256),
        (G1_RECEIPT, G1_RECEIPT_SHA256),
        (GROUND_CORPUS, GROUND_SHA256),
        (GROUND_STRUCTURED, GROUND_STRUCTURED_SHA256),
        (GROUND_RECEIPT, GROUND_RECEIPT_SHA256),
        (RUNTIME_RECEIPT, RUNTIME_RECEIPT_SHA256),
    ):
        if _sha256(path) != expected:
            raise RuntimeError(f"G8 static asset hash drift: {path}")
    m0_path = Path(root) / M0_RELPATH
    if not m0_path.is_file() or _sha256(m0_path) != M0_SHA256:
        raise RuntimeError("G8 frozen same-row M0 artifact hash drift")
    composed = compose(
        REPO, MODEL_FRAGMENT, DATASET_FRAGMENT, BASELINE_FRAGMENT, EXPERIMENT_FRAGMENT
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("G8 composed configuration hash drift")
    if protocol_hash(composed.config_hash, str(composed.values["arm"]), SPLIT_IDENTITY_HASH) != PROTOCOL_SHA256:
        raise RuntimeError("G8 protocol hash drift")
    roster = json.loads(G8_ROSTER.read_text(encoding="utf-8"))
    if roster.get("split_identity_hash") != SPLIT_IDENTITY_HASH or len(roster.get("selected", [])) != SAMPLE_COUNT:
        raise RuntimeError("G8 receipt identity drift")
    repeated_seconds = _verify_repeated_speech_reservation()
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("G8 OpenJiuwen version drift")
    values = composed.values
    if (
        int(values["profile_slot_count"]) != SLOTS
        or int(values["max_concurrent_model_requests"]) != MAX_CONCURRENT_MODEL_REQUESTS
        or int(values["queue_depth"]) != QUEUE_DEPTH
        or int(values["repair_contacts"]) != 0
        or int(values["retries"]) != 0
        or int(values["resends"]) != 0
        or bool(values["network_jitter_testing"])
    ):
        raise RuntimeError("G8 concurrency or one-shot geometry drift")
    surface = load_runtime_surface()
    selected_ids = tuple(sample.sample_id for sample in surface.samples)
    m0_texts = load_m0_outputs(m0_path, selected_ids)
    return {
        "commit": commit,
        "run_id": RUN_ID,
        "composed": composed,
        "lock": load_lock(umbrella_lock_path(REPO)),
        "ground": load_ground(),
        "surface": surface,
        "m0_texts": m0_texts,
        "composed_config_sha256": composed.config_hash,
        "protocol_sha256": PROTOCOL_SHA256,
        "repeated_speech_audio_seconds": repeated_seconds,
        "planned_speech_audio_seconds": PLANNED_SPEECH_AUDIO_SECONDS,
        "prompt_fit": preflight_ground(
            load_ground(),
            speech_feature_tokens_max=max(surface.speech_feature_tokens_by_sample.values()),
        ),
        "costs": physical_and_logical_costs(),
        "status": "PREFLIGHT_PASSED",
    }


def _seal_branches(
    *,
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    summary: FlightSummary,
    client_summary: Mapping[str, object],
    run_dir: Path,
    agent_trace_path: Path,
    agent_trace_hash: str,
    session_receipt: Path,
) -> dict[str, object]:
    """Seal four complete tool-derived output traces and manifests before gold."""
    sample_ids = tuple(state.sample.sample_id for state in summary.results)
    final_texts = {
        branch: {
            state.sample.sample_id: state.branch_texts[branch]
            for state in summary.results
        }
        for branch in BRANCH_ORDER[1:]
    }
    derivatives = build_branch_derivatives(
        sample_ids=sample_ids,
        m0_texts=context["m0_texts"],
        branch_final_texts=final_texts,
    )
    manifests: dict[str, Path] = {}
    sealed: dict[str, object] = {}
    logical_costs = physical_and_logical_costs()["logical_action_contacts"]
    for branch, derivative in derivatives.items():
        branch_dir = run_dir / "branches" / branch.lower()
        source_by_id = {}
        for sample_id in sample_ids:
            if branch == "STOP_M0":
                source_by_id[sample_id] = {
                    "action": "STOP_M0",
                    "source_kind": "frozen-g1-m0-exact-sample-identity",
                    "source_artifact_path": str((root / M0_RELPATH).resolve()),
                    "source_artifact_sha256": M0_SHA256,
                }
            else:
                source_by_id[sample_id] = {
                    "action": branch,
                    "source_kind": "sealed-g8-frozen-core-final",
                    "source_artifact_path": str(agent_trace_path.resolve()),
                    "source_artifact_sha256": _sha256(agent_trace_path),
                    "source_agent_trace_manifest_sha256": agent_trace_hash,
                    "source_transport_trace_manifest_sha256": str(
                        client_summary["trace_manifest_hash"]
                    ),
                }
        sink = TraceSink(branch_dir, RUN_ID)
        rows = emit_composite_rows(
            texts=derivative.texts,
            source_by_id=source_by_id,
            sink=sink,
            variant="main",
        )
        output_trace_hash = sink.close()
        outputs = branch_dir / f"{RUN_ID}.{branch}.outputs.jsonl"
        _write_jsonl(outputs, rows)
        cost = {
            "calls_used": int(logical_costs[branch]),
            "logical_action_contacts": int(logical_costs[branch]),
            "logical_costs_are_nonadditive": True,
            "shared_parent_physical_contacts": SAMPLE_COUNT * SHARED_CONTACTS_PER_SAMPLE,
            "parent_physical_contacts_once": MODEL_CONTACTS,
            "parent_actual_cost": dict(client_summary["cost"]),
        }
        manifest = build_manifest(
            repo_root=REPO,
            data_root=root,
            composed=context["composed"],
            plan=plan,
            verified_split=_verified_split(),
            session_receipt_path=session_receipt,
            run_dir=branch_dir,
            status=STATUS_COMPLETED,
            result=RunResult(
                run_id=RUN_ID,
                arm="speech-feature-query",
                outputs_path=outputs,
                trace_manifest_hash=output_trace_hash,
                cost=cost,
            ),
        )
        _bind_official_scorer(manifest)
        if len(verify_bundle(manifest).outputs_rows) != SAMPLE_COUNT:
            raise RuntimeError(f"G8 {branch} bundle is not complete fixed16")
        manifests[branch] = manifest
        sealed[branch] = {
            "outputs": str(outputs),
            "outputs_sha256": _sha256(outputs),
            "manifest": str(manifest),
            "manifest_sha256": _sha256(manifest),
            "output_trace_manifest_sha256": output_trace_hash,
            "logical_action_contacts": int(logical_costs[branch]),
            "logical_costs_are_nonadditive": True,
        }
    score_plan = parallel_score_plan(manifests)
    _write_json(run_dir / "official-score-plan.json", score_plan)
    _write_jsonl(
        run_dir / "official-score-jobs.jsonl",
        tuple(
            {"job_id": row["job_id"], "manifest": row["manifest"]}
            for row in score_plan["jobs"]
        ),
    )
    return {"branches": sealed, "score_plan": score_plan}


def launch(
    root: Path, attempt_id: str, *, execute: bool = False
) -> Mapping[str, object]:
    """Preflight by default; execute once only after the exact gate authorizes it."""
    context = static_preflight(root)
    if not execute:
        return {
            "status": "PREFLIGHT_PASSED",
            "contacts_sent": 0,
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "planned_model_calls": MODEL_CONTACTS,
            "prompt_fit": context.get("prompt_fit"),
            "costs": physical_and_logical_costs(),
        }
    plan = execution_plan(attempt_id)
    values = context["composed"].values
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath="receipts/runtime-q4km-mmproj-free.json",
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=Path(str(values["model_materialization_root"])),
    )
    # This is the decisive future-authorization check.  The current ledger has
    # no G8 row, so today's execute=True call fails here before service contact.
    gate.assert_model_touch_allowed(plan, full_hash=True)
    parsed = urlparse(str(values["base_url"]))
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
        raise RuntimeError("G8 decoder must use an explicit loopback port")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission = root / "runs" / RUN_ID / f"flight-{stamp}"
    run_dir = mission / "g8"
    service_dir = mission / "service"
    run_dir.mkdir(parents=True, exist_ok=False)
    service_dir.mkdir()
    _write_json(run_dir / "execution-plan.json", asdict(plan))
    _write_json(run_dir / "precontact-prompt-fit.json", context["prompt_fit"])
    runtime_receipt = load_runtime_receipt(RUNTIME_RECEIPT)
    model_root = Path(str(values["model_materialization_root"]))
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
            request_id_prefix="g8fixed16",
            speech_feature_root=FEATURE_ROOT,
            speech_packet_bindings=surface.packet_bindings,
        )
        trace_sink = TraceSink(run_dir / "agent-trace", RUN_ID)
        summary = run_openjiuwen_phase(
            surface=surface,
            ground=context["ground"],
            client=client,
            trace_sink=trace_sink,
        )
        agent_trace_path = run_dir / "agent-trace" / f"{RUN_ID}.trace.jsonl"
        agent_trace_hash = trace_sink.close()
        trace_sink = None
        client_summary = client.close()
        client = None
        _validate_client_summary(client_summary)
        stop_session(
            session,
            runtime_receipt=runtime_receipt,
            runtime_root=RUNTIME_ROOT,
            force_after_timeout=True,
            receipt_path=stop_receipt,
        )
        session = None
        sealed = _seal_branches(
            root=root,
            context=context,
            plan=plan,
            summary=summary,
            client_summary=client_summary,
            run_dir=run_dir,
            agent_trace_path=agent_trace_path,
            agent_trace_hash=agent_trace_hash,
            session_receipt=session_receipt,
        )
        receipt = {
            "schema": "saea-a2t-g8-action-support-fixed16-flight-v1",
            "status": "SEALED_FOUR_BRANCHES_UNSCORED",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "study_commit": context["commit"],
            "elapsed_seconds": time.perf_counter() - started,
            "physical_cost": {
                "model_contacts_once": MODEL_CONTACTS,
                "speech_audio_seconds_cap_once": PLANNED_SPEECH_AUDIO_SECONDS,
                "client": client_summary["cost"],
            },
            "transport_trace_manifest_sha256": client_summary[
                "trace_manifest_hash"
            ],
            "logical_costs": physical_and_logical_costs(),
            "scorer_contacts": 0,
            "gold_opened": False,
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
        _write_json(
            mission / "failure-receipt.json",
            {
                "run_id": RUN_ID,
                "attempt_id": attempt_id,
                "error": repr(error),
                "terminal": True,
                "retry_or_repair_authorized": False,
                "branch_manifests_emitted": False,
                "scoring_started": False,
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
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--attempt-id", required=True)
    args = parser.parse_args(argv)
    root = args.data_root or data_root()
    print(
        json.dumps(
            launch(root, args.attempt_id, execute=args.run),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
