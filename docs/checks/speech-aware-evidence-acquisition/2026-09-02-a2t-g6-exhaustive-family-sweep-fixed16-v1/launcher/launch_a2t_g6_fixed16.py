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
    contact_id: str
    stage: str
    family_tag: str | None
    slot_id: int
    response_sha256: str
    envelope: object

    def as_json(self) -> dict[str, object]:
        return {
            "contact_id": self.contact_id,
            "stage": self.stage,
            "family_tag": self.family_tag,
            "slot_id": self.slot_id,
            "response_sha256": self.response_sha256,
            "prompt_envelope": _envelope_json(self.envelope),
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
        trace_sink.emit(
            phase,
            f"g6:{state.sample.sample_id}:{phase.lower()}",
            state.trace_documents[phase],
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
        if not isinstance(response_text, str):
            raise RuntimeError("G6 frozen core response must be text")
        return {
            "contact_id": context.contact_id,
            "stage": context.stage,
            "family_tag": context.family_tag,
            "slot_id": slot_id,
            "response_text": response_text,
            "response_sha256": hashlib.sha256(response_text.encode("utf-8")).hexdigest(),
            "envelope": envelope,
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
            if response.get("contact_id") != context.contact_id:
                raise RuntimeError("G6 fan-in changed contact order")
            response_text = response.get("response_text")
            if not isinstance(response_text, str):
                raise RuntimeError("G6 fan-in returned malformed response text")
            if response.get("response_sha256") != hashlib.sha256(
                response_text.encode("utf-8")
            ).hexdigest():
                raise RuntimeError("G6 fan-in response hash mismatch")
            state.contacts.append(
                G6ContactRecord(
                    contact_id=context.contact_id,
                    stage=context.stage,
                    family_tag=context.family_tag,
                    slot_id=int(response["slot_id"]),
                    response_sha256=str(response["response_sha256"]),
                    envelope=response["envelope"],
                )
            )
        if state.stage == "SCAN":
            by_family = {
                str(response["family_tag"]): response["response_text"]
                for response in responses
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


def _launch(root: Path) -> Mapping[str, object]:
    context = _static_preflight(root)
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
            request_id_prefix="g6fixed16",
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
        )
        agent_trace_hash = trace_sink.close()
        trace_sink = None
        client_summary = client.close()
        client = None
        if client_summary.get("request_count") != MAX_TOTAL_CONTACTS:
            raise RuntimeError("G6 transport did not record exactly 464 requests")
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
            "schema": "saea-a2t-g6-exhaustive-family-sweep-fixed16-flight-receipt-v1",
            "run_id": RUN_ID,
            "status": "SEALED_UNSCORED",
            "study_commit": context["commit"],
            "attempt_id": attempt_id,
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "model_contacts": MAX_TOTAL_CONTACTS,
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
    result = _launch(root)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
