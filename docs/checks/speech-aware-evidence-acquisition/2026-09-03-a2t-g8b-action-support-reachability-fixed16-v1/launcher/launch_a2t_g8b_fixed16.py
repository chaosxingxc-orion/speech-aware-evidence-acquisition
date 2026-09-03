#!/usr/bin/env python3
"""G8B successor launcher with sample-local strict SELECT/BIND failures.

This module imports the executed G8 V1 launcher as an immutable helper surface.
It gives the corrected protocol a new run identity and implements its dynamic
contact geometry without changing the prior launcher's bytes or semantics.
The default command remains a contact-free preflight.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import importlib.util
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

_V1_PATH = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-g8-action-support-reachability-fixed16-v1/launcher/"
    "launch_a2t_g8_fixed16.py"
)
_V1_SPEC = importlib.util.spec_from_file_location("_saea_g8_executed_v1", _V1_PATH)
if _V1_SPEC is None or _V1_SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("cannot load the immutable G8 V1 helper surface")
_v1 = importlib.util.module_from_spec(_V1_SPEC)
sys.modules.setdefault(_V1_SPEC.name, _v1)
_V1_SPEC.loader.exec_module(_v1)


# Immutable G8 helper and asset surfaces. These aliases are prospective reuse;
# no global in the executed V1 module is changed.
Audio2ToolSample = _v1.Audio2ToolSample
BoundCall = _v1.BoundCall
ConstructionExampleGround = _v1.ConstructionExampleGround
ExecutionPlan = _v1.ExecutionPlan
FrozenCoreClient = _v1.FrozenCoreClient
FrozenCoreGate = _v1.FrozenCoreGate
G7ExampleGround = _v1.G7ExampleGround
G8ActionSupportCore = _v1.G8ActionSupportCore
G8ActionSupportError = _v1.G8ActionSupportError
Observation = _v1.Observation
ResolveContext = _v1.ResolveContext
RuntimeSurface = _v1.RuntimeSurface
ToolBindings = _v1.ToolBindings
ToolSelection = _v1.ToolSelection
TraceSink = _v1.TraceSink
TRANSPORTS = _v1.TRANSPORTS
asset_dir = _v1.asset_dir
build_manifest = _v1.build_manifest
build_payload_binding = _v1.build_payload_binding
emit_composite_rows = _v1.emit_composite_rows
load_runtime_receipt = _v1.load_runtime_receipt
start_session = _v1.start_session
stop_session = _v1.stop_session
verify_bundle = _v1.verify_bundle

AudioRef = _v1.AudioRef
GROUND_SHA256 = _v1.GROUND_SHA256
GROUND_STRUCTURED_SHA256 = _v1.GROUND_STRUCTURED_SHA256
GROUND_RECEIPT_SHA256 = _v1.GROUND_RECEIPT_SHA256
G1_RECEIPT_SHA256 = _v1.G1_RECEIPT_SHA256
RUNTIME_RECEIPT_SHA256 = _v1.RUNTIME_RECEIPT_SHA256
PROMOTION_RECEIPT_SHA256 = _v1.PROMOTION_RECEIPT_SHA256
OPENJIUWEN_VERSION = _v1.OPENJIUWEN_VERSION
RUNTIME_ROOT = _v1.RUNTIME_ROOT
FEATURE_ROOT = _v1.FEATURE_ROOT
RUNTIME_RECEIPT = _v1.RUNTIME_RECEIPT
PROMOTION_RECEIPT = _v1.PROMOTION_RECEIPT
M0_RELPATH = _v1.M0_RELPATH
M0_SHA256 = _v1.M0_SHA256
G1_RECEIPT = _v1.G1_RECEIPT
GROUND_CORPUS = _v1.GROUND_CORPUS
GROUND_STRUCTURED = _v1.GROUND_STRUCTURED
GROUND_RECEIPT = _v1.GROUND_RECEIPT

MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-g1-104"
BASELINE_FRAGMENT = "a2t-g8b-action-support-reachability-agentloop"
EXPERIMENT_FRAGMENT = "a2t-g8b-action-support-reachability-fixed16-v1"
SPLIT_ID = "A2T-G8B-ACTION-SUPPORT-FIXED16"
SPLIT_IDENTITY_HASH = "bd2c17552efb7139359087e313e0290aaafe9999d695d94ece48650c7d9ef5c6"
ROSTER_SHA256 = "9a7b60394f53578d5ab948d1e5de4737cff73d1803a86883182c90fd0cc48705"
G8_ROSTER_SHA256 = _v1.ROSTER_SHA256
G8_ROSTER = REPO / "docs/receipts/a2t/A2T-G8-ACTION-SUPPORT-FIXED16.json"
G8B_ROSTER = REPO / "docs/receipts/a2t/A2T-G8B-ACTION-SUPPORT-FIXED16.json"
COMPOSED_CONFIG_SHA256 = "73a542e45b70d0f17eb23c816b0b098d3d9419fc825248b5709fb38b7b42ac10"

SAMPLE_COUNT = 16
SHARED_CONTACTS_PER_SAMPLE = 29
MAX_MODEL_CONTACTS = 544
MIN_MODEL_CONTACTS = 512
MODEL_CONTACTS = MAX_MODEL_CONTACTS
REPEATED_SPEECH_AUDIO_SECONDS = 75.808
PLANNED_SPEECH_AUDIO_SECONDS = 2578
SLOTS = _v1.SLOTS
QUEUE_DEPTH = _v1.QUEUE_DEPTH
WORKFLOW_TIMEOUT_SECONDS = _v1.WORKFLOW_TIMEOUT_SECONDS
CONTROL_INSTRUCTION = _v1.CONTROL_INSTRUCTION
BRANCH_ORDER = _v1.BRANCH_ORDER

RUN_ID = "SAEA-A2T-G8B-ACTION-SUPPORT-REACHABILITY-FIXED16-V1"
TRACE_RECORD_PREFIX = "g8b"
DERIVATIVE_SOURCE_KIND = "sealed-g8b"
RAW_INVALID_SOURCE_KIND = "sealed-g8b-raw-invalid-stage-response"
FINAL_SOURCE_KIND = "sealed-g8b-frozen-core-final"
MISSION_SUBDIR = "g8b"
REQUEST_ID_PREFIX = "g8bfixed16"
PREFLIGHT_SCHEMA = "saea-a2t-g8b-action-support-precontact-report-v1"
FLIGHT_RECEIPT_SCHEMA = "saea-a2t-g8b-action-support-fixed16-flight-v1"
BASE_DYNAMIC_CONTACTS = SAMPLE_COUNT * (SHARED_CONTACTS_PER_SAMPLE + 4)
PROTOCOL_DESCRIPTOR = {
    "schema": "saea-a2t-g8b-action-support-reachability-protocol-v1",
    "parent_run_id": _v1.RUN_ID,
    "run_id": RUN_ID,
    "empty_selection": "EMPTY_BIND_PASSTHROUGH_THEN_FINAL_RESOLVE",
    "invalid_select": "TERMINAL_RAW_RESPONSE_FOR_SAMPLE",
    "invalid_nonempty_bind": "TERMINAL_RAW_RESPONSE_FOR_SAMPLE",
    "retry_repair_strip_substitution": False,
    "planned_contact_ceiling": MAX_MODEL_CONTACTS,
    "realized_contact_formula": (
        f"{BASE_DYNAMIC_CONTACTS} + nonempty_valid_selections - "
        "invalid_selects - invalid_binds"
    ),
}
PROTOCOL_DESCRIPTOR_SHA256 = hashlib.sha256(
    json.dumps(
        PROTOCOL_DESCRIPTOR,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
).hexdigest()
PROTOCOL_SHA256 = "ae3f6bb34cc6462fb221838ebce52e3117da697164caa6bcd0cc4accb4820448"


@dataclass(frozen=True)
class ModelFreeTransition:
    """A sealed, hash-addressable transition that spends no model contact."""

    stage: str
    canonical_json: str
    sha256: str
    model_contacts: int = 0


@dataclass(frozen=True)
class SelectionOutcome:
    """Strict SELECT result without changing an invalid raw response."""

    status: str
    selection: ToolSelection | None
    raw_terminal_text: str | None
    error: str | None
    retry_or_repair_authorized: bool = False


@dataclass(frozen=True)
class BindingOutcome:
    """Strict BIND result without changing an invalid raw response."""

    status: str
    bindings: ToolBindings | None
    raw_terminal_text: str | None
    error: str | None
    retry_or_repair_authorized: bool = False


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
    model_free_transitions: list[ModelFreeTransition] = field(default_factory=list)
    invalid_stage: str | None = None
    invalid_status: str | None = None
    invalid_error: str | None = None


@dataclass(frozen=True)
class FlightSummary:
    results: tuple[_WorkflowState, ...]
    physical_model_contacts: int


@dataclass(frozen=True)
class BranchDerivative:
    branch: str
    texts: Mapping[str, str]
    new_model_contacts: int
    source_kind: str


def _selected_roster_ids() -> tuple[str, ...]:
    """Return only the hash-bound G8B identity surface."""
    if _v1._sha256(G8B_ROSTER) != ROSTER_SHA256:
        raise RuntimeError("G8B roster hash drift")
    if _v1._sha256(G8_ROSTER) != G8_ROSTER_SHA256:
        raise RuntimeError("consumed G8 source-roster hash drift")
    document = json.loads(G8B_ROSTER.read_text(encoding="utf-8"))
    selected = document.get("selected")
    if (
        document.get("split_identity_hash") != SPLIT_IDENTITY_HASH
        or not isinstance(selected, list)
        or len(selected) != SAMPLE_COUNT
    ):
        raise RuntimeError("G8B roster split identity drift")
    ids = tuple(row.get("sample_id") for row in selected if isinstance(row, Mapping))
    if len(ids) != SAMPLE_COUNT or len(set(ids)) != SAMPLE_COUNT or not all(
        isinstance(sample_id, str) and sample_id for sample_id in ids
    ):
        raise RuntimeError("G8B roster identities are malformed")
    old_document = json.loads(G8_ROSTER.read_text(encoding="utf-8"))
    old_ids = {
        row.get("sample_id")
        for row in old_document.get("selected", ())
        if isinstance(row, Mapping)
    }
    if set(ids) & old_ids:
        raise RuntimeError("G8B selected identities overlap the consumed G8 roster")
    return ids


def _verify_repeated_speech_reservation() -> float:
    """Derive the G8B maximum repeated-speech reservation from receipts only."""
    if _v1._sha256(G1_RECEIPT) != G1_RECEIPT_SHA256:
        raise RuntimeError("G8B G1 receipt hash drift")
    ids = set(_selected_roster_ids())
    g1 = json.loads(G1_RECEIPT.read_text(encoding="utf-8"))
    by_id = {
        row.get("sample_id"): row.get("audio_seconds")
        for row in g1.get("items", ())
        if isinstance(row, Mapping)
    }
    if not ids <= set(by_id):
        raise RuntimeError("G8B roster identities lack G1 audio metadata")
    try:
        seconds = sum(float(by_id[sample_id]) for sample_id in ids)
    except (TypeError, ValueError) as error:
        raise RuntimeError("G8B G1 audio duration is malformed") from error
    if abs(seconds - REPEATED_SPEECH_AUDIO_SECONDS) > 1e-9:
        raise RuntimeError("G8B repeated-speech duration drift")
    if math.ceil(seconds * 34) != PLANNED_SPEECH_AUDIO_SECONDS:
        raise RuntimeError("G8B repeated-speech reservation drift")
    return seconds


def load_runtime_surface() -> RuntimeSurface:
    """Join the fresh G8B roster to frozen G1 carriers and promoted packets."""
    for path, expected in (
        (G8B_ROSTER, ROSTER_SHA256),
        (G1_RECEIPT, G1_RECEIPT_SHA256),
        (PROMOTION_RECEIPT, PROMOTION_RECEIPT_SHA256),
    ):
        if _v1._sha256(path) != expected:
            raise RuntimeError(f"G8B runtime identity hash drift: {path.name}")
    roster = json.loads(G8B_ROSTER.read_text(encoding="utf-8"))
    g1 = json.loads(G1_RECEIPT.read_text(encoding="utf-8"))
    promotion = json.loads(PROMOTION_RECEIPT.read_text(encoding="ascii"))
    expected_ids = _selected_roster_ids()
    g1_by_id = {row["sample_id"]: row for row in g1["items"]}
    promoted = {row["packet_id"]: row for row in promotion["packets"]}
    samples: list[Audio2ToolSample] = []
    bindings: dict[str, Mapping[str, str]] = {}
    speech_tokens: dict[str, int] = {}
    for selected, expected_id in zip(roster["selected"], expected_ids, strict=True):
        sample_id = selected["sample_id"]
        if sample_id != expected_id:
            raise RuntimeError("G8B roster order drift")
        item = g1_by_id.get(sample_id)
        if item is None or (item["key"], item["tier"]) != (
            selected["key"],
            selected["tier"],
        ):
            raise RuntimeError("G8B roster row is absent from frozen G1")
        packet_id = item["packet_id"]
        packet_path = PROMOTION_RECEIPT.parent / packet_id / "packet.json"
        packet = json.loads(packet_path.read_text(encoding="ascii"))
        promoted_row = promoted.get(packet_id)
        if (
            promoted_row is None
            or packet["packet_sha256"] != promoted_row["packet_sha256"]
            or packet["audio_sha256"] != item["audio_sha256"]
        ):
            raise RuntimeError("G8B promoted packet identity drift")
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
        speech_tokens[sample_id] = sum(
            int(chunk["n_tokens"]) for chunk in packet["chunks"]
        )
    if (
        tuple(sample.sample_id for sample in samples) != expected_ids
        or abs(
            sum(sample.audio_seconds for sample in samples)
            - REPEATED_SPEECH_AUDIO_SECONDS
        )
        > 1e-9
    ):
        raise RuntimeError("G8B runtime sample or duration geometry drift")
    return RuntimeSurface(tuple(samples), bindings, speech_tokens)


def _verified_split():
    """Bind manifests to the new G8B split rather than the consumed G8 split."""
    ids = _selected_roster_ids()
    return _v1.VerifiedSplit(
        name=SPLIT_ID,
        carrier_lock_key=_v1.AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in ids),
        identity_hash=SPLIT_IDENTITY_HASH,
    )


def execution_plan(attempt_id: str) -> ExecutionPlan:
    """Bind the successor run to its maximum physical-contact exposure."""
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=MAX_MODEL_CONTACTS,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=PLANNED_SPEECH_AUDIO_SECONDS,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def classify_selection_response(
    core: G8ActionSupportCore, raw: str
) -> SelectionOutcome:
    """Parse once; an invalid response remains the sample's terminal raw text."""
    try:
        selection = core.parse_selection(raw)
    except G8ActionSupportError as error:
        return SelectionOutcome(
            status="INVALID_SELECT_TERMINAL_RAW_RESPONSE",
            selection=None,
            raw_terminal_text=raw,
            error=str(error),
        )
    return SelectionOutcome("VALID_SELECT", selection, None, None)


def classify_binding_response(
    core: G8ActionSupportCore, raw: str, selection: ToolSelection
) -> BindingOutcome:
    """Parse one nonempty BIND response once, without repair or substitution."""
    if not selection.tool_names:
        raise ValueError("empty selection must use EMPTY_BIND_PASSTHROUGH")
    try:
        bindings = core.parse_bindings(raw, selection)
    except G8ActionSupportError as error:
        return BindingOutcome(
            status="INVALID_BIND_TERMINAL_RAW_RESPONSE",
            bindings=None,
            raw_terminal_text=raw,
            error=str(error),
        )
    return BindingOutcome("VALID_BIND", bindings, None, None)


def empty_bind_passthrough(
    sample_id: str, selection: ToolSelection
) -> tuple[ToolBindings, ModelFreeTransition]:
    """Seal exact empty bindings and a zero-contact transition document."""
    if selection.tool_names or selection.canonical_json != "[]":
        raise ValueError("EMPTY_BIND_PASSTHROUGH requires the exact sealed empty selection")
    document = {
        "bindings": [],
        "sample_id": sample_id,
        "selection": [],
        "stage": "EMPTY_BIND_PASSTHROUGH",
    }
    canonical = json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    )
    return (
        ToolBindings((), "[]"),
        ModelFreeTransition(
            stage="EMPTY_BIND_PASSTHROUGH",
            canonical_json=canonical,
            sha256=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        ),
    )


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


def _execute_openjiuwen(*args: object, **kwargs: object) -> object:
    return _v1._execute_openjiuwen(*args, **kwargs)


def _state_geometry(states: Sequence[_WorkflowState]) -> dict[str, int]:
    nonempty = sum(
        state.selection is not None and bool(state.selection.tool_names)
        for state in states
    )
    invalid_selects = sum(state.invalid_stage == "DECOMPOSED_SELECT" for state in states)
    invalid_binds = sum(state.invalid_stage == "DECOMPOSED_BIND" for state in states)
    successful_resolves = SAMPLE_COUNT - invalid_selects - invalid_binds
    expected = BASE_DYNAMIC_CONTACTS + nonempty - invalid_selects - invalid_binds
    return {
        "base_with_all_final_resolves": BASE_DYNAMIC_CONTACTS,
        "nonempty_valid_selections": nonempty,
        "invalid_selects": invalid_selects,
        "invalid_binds": invalid_binds,
        "successful_final_resolves": successful_resolves,
        "expected_physical_contacts": expected,
    }


def _emit_state_audits(state: _WorkflowState, trace_sink: TraceSink) -> None:
    """Persist contact and OBS/ORG/SUPPLY/USE audits on every terminal path."""
    sample_id = state.sample.sample_id
    for index, contact in enumerate(state.contacts):
        trace_sink.emit(
            "COST",
            f"{TRACE_RECORD_PREFIX}:{sample_id}:contact-audit:{index:02d}",
            {
                "sample_id": contact.sample_id,
                "contact_id": contact.contact_id,
                "stage": contact.stage,
                "slot_id": contact.slot_id,
                "response_sha256": contact.response_sha256,
                "prompt_fit": dict(contact.prompt_fit),
            },
        )
    for index, transition in enumerate(state.model_free_transitions):
        trace_sink.emit(
            "USE",
            f"{TRACE_RECORD_PREFIX}:{sample_id}:model-free-transition:{index:02d}",
            {
                "use_sample_id": sample_id,
                "use_stage": transition.stage,
                "use_canonical_json": transition.canonical_json,
                "use_sha256": transition.sha256,
                "use_model_contacts": transition.model_contacts,
            },
        )
    assert state.observation is not None
    assert state.normalized_sheet is not None and state.support_sheet is not None
    statuses: dict[str, int] = {}
    for row in state.normalized_sheet.assessments:
        statuses[row.status] = statuses.get(row.status, 0) + 1
    trace_sink.emit(
        "OBS",
        f"{TRACE_RECORD_PREFIX}:{sample_id}:obs",
        {
            "obs_sample_id": sample_id,
            "obs_valid": state.observation.valid,
            "obs_text": state.observation.text,
        },
    )
    trace_sink.emit(
        "ORG",
        f"{TRACE_RECORD_PREFIX}:{sample_id}:org",
        {
            "org_sample_id": sample_id,
            "org_normalized_tool_count": len(state.normalized_sheet.assessments),
            "org_status_counts": statuses,
            "org_normalized_execution_sheet": state.normalized_sheet.text,
        },
    )
    trace_sink.emit(
        "SUPPLY",
        f"{TRACE_RECORD_PREFIX}:{sample_id}:supply",
        {
            "supply_sample_id": sample_id,
            "supply_support_tool_count": len(state.support_sheet.assessments),
            "supply_support_tool_names": [
                row.tool_name for row in state.support_sheet.assessments
            ],
            "supply_support_execution_sheet": state.support_sheet.text,
        },
    )
    for branch in BRANCH_ORDER[1:]:
        text = state.branch_texts[branch]
        document: dict[str, object] = {
            "use_sample_id": sample_id,
            "use_branch": branch,
            "use_final_response_text": text,
            "use_final_response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        if branch == "DECOMPOSED_SELECT_BIND_RESOLVE":
            document.update(
                {
                    "use_selected_tool_names": (
                        list(state.selection.tool_names) if state.selection is not None else None
                    ),
                    "use_binding_count": (
                        len(state.bindings.calls) if state.bindings is not None else None
                    ),
                    "use_bindings_json": (
                        state.bindings.canonical_json if state.bindings is not None else None
                    ),
                    "use_invalid_stage": state.invalid_stage,
                    "use_invalid_status": state.invalid_status,
                    "use_invalid_error": state.invalid_error,
                    "use_terminal_source": (
                        "raw_invalid_frozen_core_response"
                        if state.invalid_stage
                        else "frozen_core_final_resolve"
                    ),
                    "use_retry_or_repair_authorized": False,
                }
            )
        trace_sink.emit(
            "USE",
            f"{TRACE_RECORD_PREFIX}:{sample_id}:use:{branch.lower()}",
            document,
        )


def run_openjiuwen_phase(
    *,
    surface: RuntimeSurface,
    ground: ConstructionExampleGround,
    client: FrozenCoreClient,
    trace_sink: TraceSink,
    workflow_runner: Callable[..., object] = _execute_openjiuwen,
) -> FlightSummary:
    """Execute dynamic G8B waves; strict parser failures terminalize only one sample."""
    if len(surface.samples) != SAMPLE_COUNT:
        raise RuntimeError(f"G8B execution requires the exact {SAMPLE_COUNT} selected samples")
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
    fatal = threading.Event()

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
            if not state.selection.tool_names:
                raise RuntimeError("empty selection reached a forbidden BIND contact")
            state.current = (state.g8.build_binding_context(state.observation, state.selection),)
        elif state.stage == "DECOMPOSED_RESOLVE":
            assert state.observation is not None
            assert state.selection is not None and state.bindings is not None
            state.current = (
                state.g8.build_resolve_context(
                    state.observation, state.selection, state.bindings
                ),
            )
        else:
            state.current = ()
        update = getattr(session, "update_global_state", None)
        if callable(update):
            update({"g8b_stage": state.stage, "g8b_sample_id": state.sample.sample_id})
        return len(state.current)

    def invoke(
        state: _WorkflowState, branch_index: int, slot_id: int
    ) -> Mapping[str, object]:
        if fatal.is_set():
            raise RuntimeError("G8B attempt has a fatal runtime failure")
        try:
            context = state.current[branch_index]
            messages = _v1._packet_messages(state.stage, context)
            for part in messages[1]["content"]:
                if isinstance(part, dict) and part.get("type") == "input_speech_features":
                    part["speech_features"] = {**state.packet_binding, "role": "query"}
            contact_stage = str(getattr(context, "stage", state.stage))
            fit = _v1._measure(
                contact_id=context.contact_id,
                rendered_request=_v1._exact_request(messages, context),
                completion_tokens=_v1._completion_tokens(contact_stage),
                speech_feature_tokens=state.speech_tokens,
            )
            fit_document = _v1._fit_dict(fit)
            state.pending_fits[context.contact_id] = fit_document
            text = client.complete(
                messages,
                speech_feature_sample_id=state.sample.sample_id,
                key_representation_id=f"g8b-action-support:{contact_stage.lower()}",
                matcher_policy_id="saea-a2t-g8b-action-support-reachability-v1",
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
            fatal.set()
            raise

    def aggregate_unchecked(
        state: _WorkflowState,
        responses: tuple[Mapping[str, object], ...],
        session: object,
    ) -> None:
        del session
        if len(responses) != len(state.current):
            raise RuntimeError("G8B fan-in contact count drift")
        for context, response in zip(state.current, responses, strict=True):
            text = str(response["response_text"])
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if response["response_sha256"] != digest:
                raise RuntimeError("G8B response hash mismatch")
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
            state.observation = _v1.parse_observation(
                str(responses[0]["response_text"]), state.g7.tool_names
            )
            state.stage = "EVIDENCE"
        elif state.stage == "EVIDENCE":
            state.assessments = tuple(
                _v1.parse_family_assessment(
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
            raw = str(responses[2]["response_text"])
            outcome = classify_selection_response(state.g8, raw)
            if outcome.selection is None:
                state.invalid_stage = "DECOMPOSED_SELECT"
                state.invalid_status = outcome.status
                state.invalid_error = outcome.error
                state.branch_texts["DECOMPOSED_SELECT_BIND_RESOLVE"] = raw
                state.stage = "DONE"
            else:
                state.selection = outcome.selection
                if state.selection.tool_names:
                    state.stage = "DECOMPOSED_BIND"
                else:
                    state.bindings, transition = empty_bind_passthrough(
                        state.sample.sample_id, state.selection
                    )
                    state.model_free_transitions.append(transition)
                    state.stage = "DECOMPOSED_RESOLVE"
        elif state.stage == "DECOMPOSED_BIND":
            assert state.selection is not None
            raw = str(responses[0]["response_text"])
            outcome = classify_binding_response(state.g8, raw, state.selection)
            if outcome.bindings is None:
                state.invalid_stage = "DECOMPOSED_BIND"
                state.invalid_status = outcome.status
                state.invalid_error = outcome.error
                state.branch_texts["DECOMPOSED_SELECT_BIND_RESOLVE"] = raw
                state.stage = "DONE"
            else:
                state.bindings = outcome.bindings
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
        if fatal.is_set():
            raise RuntimeError("G8B attempt has a fatal runtime failure")
        try:
            aggregate_unchecked(state, responses, session)
        except BaseException:
            fatal.set()
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
    if list(completed) != states:
        raise RuntimeError("G8B workflow identity drift")
    geometry = _state_geometry(states)
    actual = sum(len(state.contacts) for state in states)
    if actual != geometry["expected_physical_contacts"]:
        raise RuntimeError("G8B dynamic physical-contact geometry drift")
    if not MIN_MODEL_CONTACTS <= actual <= MAX_MODEL_CONTACTS:
        raise RuntimeError("G8B realized physical contacts exceed the registered range")
    for state in states:
        if state.stage != "DONE" or set(state.branch_texts) != set(BRANCH_ORDER[1:]):
            raise RuntimeError("G8B sample did not yield three complete branch texts")
        _emit_state_audits(state, trace_sink)
    return FlightSummary(tuple(states), actual)


def physical_and_logical_costs(summary: FlightSummary | None = None) -> dict[str, object]:
    """Report the maximum before flight or reconciled dynamic costs after flight."""
    if summary is None:
        return {
            "physical_model_contacts_maximum": MAX_MODEL_CONTACTS,
            "physical_model_contacts_minimum": MIN_MODEL_CONTACTS,
            "logical_action_contacts_nonadditive": True,
            "dynamic_formula": (
                f"{BASE_DYNAMIC_CONTACTS} + nonempty_valid_selections - "
                "invalid_selects - invalid_binds"
            ),
        }
    geometry = _state_geometry(summary.results)
    if summary.physical_model_contacts != geometry["expected_physical_contacts"]:
        raise RuntimeError("G8B summary does not match its state-derived contact count")
    decomposed = (
        SAMPLE_COUNT * (SHARED_CONTACTS_PER_SAMPLE + 1)
        + geometry["nonempty_valid_selections"]
        + geometry["successful_final_resolves"]
    )
    return {
        "physical_model_contacts": summary.physical_model_contacts,
        "physical_model_contacts_maximum": MAX_MODEL_CONTACTS,
        "shared_physical_contacts": SAMPLE_COUNT * SHARED_CONTACTS_PER_SAMPLE,
        "branch_physical_contacts": (
            summary.physical_model_contacts - SAMPLE_COUNT * SHARED_CONTACTS_PER_SAMPLE
        ),
        "logical_action_contacts_nonadditive": True,
        "logical_action_contacts": {
            "STOP_M0": 0,
            "EXHAUSTIVE_G7": SAMPLE_COUNT * (SHARED_CONTACTS_PER_SAMPLE + 1),
            "SUPPORT_ONLY_RESOLVE": SAMPLE_COUNT * (SHARED_CONTACTS_PER_SAMPLE + 1),
            "DECOMPOSED_SELECT_BIND_RESOLVE": decomposed,
        },
        "dynamic_formula": {
            key: geometry[key]
            for key in (
                "base_with_all_final_resolves",
                "nonempty_valid_selections",
                "invalid_selects",
                "invalid_binds",
            )
        },
    }


def _validate_client_summary(
    summary: Mapping[str, object], *, expected_contacts: int
) -> Mapping[str, object]:
    """Reconcile transport request and billed-call counts with realized contacts."""
    if not MIN_MODEL_CONTACTS <= expected_contacts <= MAX_MODEL_CONTACTS:
        raise RuntimeError("G8B expected contact count is outside its registered range")
    if summary.get("request_count") != expected_contacts:
        raise RuntimeError("G8B transport realized request count does not match the workflow")
    cost = summary.get("cost")
    if not isinstance(cost, Mapping) or cost.get("calls_used") != expected_contacts:
        raise RuntimeError("G8B transport cost does not match the realized request count")
    digest = summary.get("trace_manifest_hash")
    if (
        not isinstance(digest, str)
        or len(digest) != 64
        or any(character not in "0123456789abcdef" for character in digest)
    ):
        raise RuntimeError("G8B transport trace manifest hash is malformed")
    return summary


def build_branch_derivatives(
    *,
    sample_ids: Sequence[str],
    m0_texts: Mapping[str, str],
    branch_final_texts: Mapping[str, Mapping[str, str]],
    decomposed_new_contacts: int,
) -> dict[str, BranchDerivative]:
    """Build four complete sources with the realized decomposed-branch cost."""
    ids = tuple(sample_ids)
    required = set(BRANCH_ORDER[1:])
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError("branch derivatives require non-empty unique sample identities")
    if set(branch_final_texts) != required or set(m0_texts) != set(ids):
        raise ValueError("branch derivatives require exact identity-complete branch inputs")
    contacts = {
        "EXHAUSTIVE_G7": SAMPLE_COUNT,
        "SUPPORT_ONLY_RESOLVE": SAMPLE_COUNT,
        "DECOMPOSED_SELECT_BIND_RESOLVE": decomposed_new_contacts,
    }
    derivatives = {
        "STOP_M0": BranchDerivative("STOP_M0", dict(m0_texts), 0, "frozen-g1-m0")
    }
    for branch in BRANCH_ORDER[1:]:
        texts = branch_final_texts[branch]
        if set(texts) != set(ids) or any(
            not isinstance(texts[sample_id], str) for sample_id in ids
        ):
            raise ValueError("branch derivatives require exact identity-complete final texts")
        derivatives[branch] = BranchDerivative(
            branch=branch,
            texts={sample_id: texts[sample_id] for sample_id in ids},
            new_model_contacts=contacts[branch],
            source_kind=DERIVATIVE_SOURCE_KIND,
        )
    return derivatives


def parallel_score_plan(branch_manifests: Mapping[str, Path]) -> dict[str, object]:
    """Describe future scoring jobs without opening the official scorer."""
    document = _v1.parallel_score_plan(branch_manifests)
    document["experiment_id"] = RUN_ID
    return document


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
    """Seal four identity-complete branch bundles; do not invoke any scorer."""
    sample_ids = tuple(state.sample.sample_id for state in summary.results)
    final_texts = {
        branch: {
            state.sample.sample_id: state.branch_texts[branch]
            for state in summary.results
        }
        for branch in BRANCH_ORDER[1:]
    }
    costs = physical_and_logical_costs(summary)
    decomposed_new_contacts = (
        int(costs["logical_action_contacts"]["DECOMPOSED_SELECT_BIND_RESOLVE"])
        - SAMPLE_COUNT * SHARED_CONTACTS_PER_SAMPLE
    )
    derivatives = build_branch_derivatives(
        sample_ids=sample_ids,
        m0_texts=context["m0_texts"],
        branch_final_texts=final_texts,
        decomposed_new_contacts=decomposed_new_contacts,
    )
    invalid_by_id = {
        state.sample.sample_id: {
            "invalid_stage": state.invalid_stage,
            "invalid_status": state.invalid_status,
        }
        for state in summary.results
    }
    manifests: dict[str, Path] = {}
    sealed: dict[str, object] = {}
    logical_costs = costs["logical_action_contacts"]
    for branch, derivative in derivatives.items():
        branch_dir = run_dir / "branches" / branch.lower()
        source_by_id = {}
        for sample_id in sample_ids:
            if branch == "STOP_M0":
                source_by_id[sample_id] = {
                    "action": branch,
                    "source_kind": "frozen-g1-m0-exact-sample-identity",
                    "source_artifact_path": str((root / M0_RELPATH).resolve()),
                    "source_artifact_sha256": M0_SHA256,
                }
            else:
                source_by_id[sample_id] = {
                    "action": branch,
                    "source_kind": (
                        RAW_INVALID_SOURCE_KIND
                        if branch == "DECOMPOSED_SELECT_BIND_RESOLVE"
                        and invalid_by_id[sample_id]["invalid_stage"]
                        else FINAL_SOURCE_KIND
                    ),
                    "invalid_stage": (
                        invalid_by_id[sample_id]["invalid_stage"]
                        if branch == "DECOMPOSED_SELECT_BIND_RESOLVE"
                        else None
                    ),
                    "invalid_status": (
                        invalid_by_id[sample_id]["invalid_status"]
                        if branch == "DECOMPOSED_SELECT_BIND_RESOLVE"
                        else None
                    ),
                    "source_artifact_path": str(agent_trace_path.resolve()),
                    "source_artifact_sha256": _v1._sha256(agent_trace_path),
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
        _v1._write_jsonl(outputs, rows)
        manifest = build_manifest(
            repo_root=REPO,
            data_root=root,
            composed=context["composed"],
            plan=plan,
            verified_split=_verified_split(),
            session_receipt_path=session_receipt,
            run_dir=branch_dir,
            status=_v1.STATUS_COMPLETED,
            result=_v1.RunResult(
                run_id=RUN_ID,
                arm="speech-feature-query",
                outputs_path=outputs,
                trace_manifest_hash=output_trace_hash,
                cost={
                    "calls_used": int(logical_costs[branch]),
                    "logical_action_contacts": int(logical_costs[branch]),
                    "logical_costs_are_nonadditive": True,
                    "parent_physical_contacts_realized": summary.physical_model_contacts,
                    "parent_physical_contacts_maximum": MAX_MODEL_CONTACTS,
                    "parent_actual_cost": dict(client_summary["cost"]),
                },
            ),
        )
        _v1._bind_official_scorer(manifest)
        if len(verify_bundle(manifest).outputs_rows) != SAMPLE_COUNT:
            raise RuntimeError(
                f"G8B {branch} bundle is not complete for {SAMPLE_COUNT} identities"
            )
        manifests[branch] = manifest
        sealed[branch] = {
            "outputs": str(outputs),
            "outputs_sha256": _v1._sha256(outputs),
            "manifest": str(manifest),
            "manifest_sha256": _v1._sha256(manifest),
            "output_trace_manifest_sha256": output_trace_hash,
            "logical_action_contacts": int(logical_costs[branch]),
            "logical_costs_are_nonadditive": True,
        }
    score_plan = parallel_score_plan(manifests)
    _v1._write_json(run_dir / "official-score-plan.json", score_plan)
    _v1._write_jsonl(
        run_dir / "official-score-jobs.jsonl",
        tuple(
            {"job_id": row["job_id"], "manifest": row["manifest"]}
            for row in score_plan["jobs"]
        ),
    )
    return {"branches": sealed, "score_plan": score_plan}


def static_preflight(root: Path) -> dict[str, object]:
    """Verify fresh identity/config surfaces and reuse only frozen G8 prompt helpers."""
    commit = _v1.require_clean_study_repo(REPO)
    for path, expected in (
        (G8B_ROSTER, ROSTER_SHA256),
        (G1_RECEIPT, G1_RECEIPT_SHA256),
        (GROUND_CORPUS, GROUND_SHA256),
        (GROUND_STRUCTURED, GROUND_STRUCTURED_SHA256),
        (GROUND_RECEIPT, GROUND_RECEIPT_SHA256),
        (RUNTIME_RECEIPT, RUNTIME_RECEIPT_SHA256),
    ):
        if _v1._sha256(path) != expected:
            raise RuntimeError(f"G8B static asset hash drift: {path}")
    m0_path = Path(root) / M0_RELPATH
    if not m0_path.is_file() or _v1._sha256(m0_path) != M0_SHA256:
        raise RuntimeError("G8B frozen same-row M0 artifact hash drift")
    composed = _v1.compose(
        REPO,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("G8B composed configuration hash drift")
    if (
        _v1.protocol_hash(
            composed.config_hash,
            str(composed.values["arm"]),
            SPLIT_IDENTITY_HASH,
        )
        != PROTOCOL_SHA256
    ):
        raise RuntimeError("G8B protocol hash drift")
    repeated_seconds = _verify_repeated_speech_reservation()
    if importlib.metadata.version("openjiuwen") != OPENJIUWEN_VERSION:
        raise RuntimeError("G8B OpenJiuwen version drift")
    values = composed.values
    if (
        int(values["profile_slot_count"]) != SLOTS
        or int(values["max_concurrent_model_requests"]) != SLOTS
        or int(values["queue_depth"]) != QUEUE_DEPTH
        or int(values["repair_contacts"]) != 0
        or int(values["retries"]) != 0
        or int(values["resends"]) != 0
        or bool(values["network_jitter_testing"])
    ):
        raise RuntimeError("G8B concurrency or one-shot geometry drift")
    surface = load_runtime_surface()
    selected_ids = tuple(sample.sample_id for sample in surface.samples)
    if selected_ids != _selected_roster_ids():
        raise RuntimeError("G8B runtime surface does not match its fresh roster")
    m0_texts = _v1.load_m0_outputs(m0_path, selected_ids)
    ground = _v1.load_ground()
    prompt_fit = dict(
        _v1.preflight_ground(
            ground,
            speech_feature_tokens_max=max(
                surface.speech_feature_tokens_by_sample.values()
            ),
        )
    )
    prompt_fit.update(
        {
            "schema": PREFLIGHT_SCHEMA,
            "run_id": RUN_ID,
            "split_id": SPLIT_ID,
            "split_identity_hash": SPLIT_IDENTITY_HASH,
            "contacts": MAX_MODEL_CONTACTS,
            "contacts_are_maximum": True,
            "minimum_contacts": MIN_MODEL_CONTACTS,
            "protocol_sha256": PROTOCOL_SHA256,
        }
    )
    return {
        "commit": commit,
        "run_id": RUN_ID,
        "composed": composed,
        "lock": _v1.load_lock(_v1.umbrella_lock_path(REPO)),
        "ground": ground,
        "surface": surface,
        "m0_texts": m0_texts,
        "composed_config_sha256": composed.config_hash,
        "protocol_sha256": PROTOCOL_SHA256,
        "protocol_descriptor_sha256": PROTOCOL_DESCRIPTOR_SHA256,
        "repeated_speech_audio_seconds": repeated_seconds,
        "planned_speech_audio_seconds": PLANNED_SPEECH_AUDIO_SECONDS,
        "prompt_fit": prompt_fit,
        "costs": physical_and_logical_costs(),
        "status": "PREFLIGHT_PASSED",
    }


def launch(root: Path, attempt_id: str, *, execute: bool = False) -> Mapping[str, object]:
    """Preflight by default; execute only after the G8B gate authorizes it."""
    context = static_preflight(root)
    if not execute:
        return {
            "status": "PREFLIGHT_PASSED",
            "contacts_sent": 0,
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "planned_model_calls_maximum": MAX_MODEL_CONTACTS,
            "prompt_fit": context["prompt_fit"],
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
    gate.assert_model_touch_allowed(plan, full_hash=True)
    parsed = urlparse(str(values["base_url"]))
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
        raise RuntimeError("G8B decoder must use an explicit loopback port")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    mission = root / "runs" / RUN_ID / f"flight-{stamp}"
    run_dir = mission / MISSION_SUBDIR
    service_dir = mission / "service"
    run_dir.mkdir(parents=True, exist_ok=False)
    service_dir.mkdir()
    _v1._write_json(run_dir / "execution-plan.json", asdict(plan))
    _v1._write_json(run_dir / "precontact-prompt-fit.json", context["prompt_fit"])
    runtime_receipt = load_runtime_receipt(RUNTIME_RECEIPT)
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = client = trace_sink = None
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
            model_root=Path(str(values["model_materialization_root"])),
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
            carrier_lock_key=_v1.AUDIO2TOOL_LOCK_KEY,
            samples=surface.samples,
            data_root=root,
            carrier_root=asset_dir(context["lock"], _v1.AUDIO2TOOL_LOCK_KEY, root),
        )
        client = FrozenCoreClient(
            plan=plan,
            gate=gate,
            transport=transport,
            run_dir=run_dir / "transport-trace",
            binding=binding,
            arm="speech-feature-query",
            request_id_prefix=REQUEST_ID_PREFIX,
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
        _validate_client_summary(
            client_summary, expected_contacts=summary.physical_model_contacts
        )
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
            "schema": FLIGHT_RECEIPT_SCHEMA,
            "status": "SEALED_FOUR_BRANCHES_UNSCORED",
            "run_id": RUN_ID,
            "attempt_id": attempt_id,
            "study_commit": context["commit"],
            "elapsed_seconds": time.perf_counter() - started,
            "physical_cost": {
                "model_contacts_realized": summary.physical_model_contacts,
                "model_contacts_maximum": MAX_MODEL_CONTACTS,
                "speech_audio_seconds_cap_once": PLANNED_SPEECH_AUDIO_SECONDS,
                "client": client_summary["cost"],
            },
            "transport_trace_manifest_sha256": client_summary[
                "trace_manifest_hash"
            ],
            "logical_costs": physical_and_logical_costs(summary),
            "scorer_contacts": 0,
            "gold_opened": False,
            **sealed,
        }
        _v1._write_json(mission / "flight-receipt.json", receipt)
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
        _v1.abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _v1._write_json(
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
    root = args.data_root or _v1.data_root()
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
