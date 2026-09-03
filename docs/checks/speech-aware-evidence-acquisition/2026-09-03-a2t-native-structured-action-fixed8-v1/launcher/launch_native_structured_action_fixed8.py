#!/usr/bin/env python3
"""Run the frozen native structured-action fixed-eight contact screen.

The default command is a read-only, contact-free preflight.  The explicit
``--run`` path keeps scoring and gold outside this module: it only executes the
two registered strict-action arms and seals their traces and complete manifests.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
from threading import Lock
import time
from typing import Callable, Mapping, Sequence
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
from speech_aware_evidence_acquisition.rails.probes import (  # noqa: E402
    a2t_executable_ground_qualification_flight as ground_flight,
)
from speech_aware_evidence_acquisition.rails.probes.a2t_self_transcript_cascade_bundle import (  # noqa: E402
    build_phase_bundle_material,
)


RUN_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-V1"
SPLIT_ID = "A2T-NATIVE-STRUCTURED-ACTION-FIXED8"
SPLIT_IDENTITY_HASH = "f95efe70b615d71bb082f9ef804d1fa2b6f04ce4114d5d2694151cbaf44019ba"
ARM_ORDER = ("REGISTRY_STRICT_ACTION", "HANDBOOK_STRICT_ACTION")
ATTEMPT_IDS = {
    ARM_ORDER[0]: "attempt-20260903T013000Z-registry-strict",
    ARM_ORDER[1]: "attempt-20260903T013000Z-handbook-strict",
}
KEY_REPRESENTATION_IDS = {
    ARM_ORDER[0]: "audio2tool-direct-registry-v1",
    ARM_ORDER[1]: "audio2tool-full-executable-ground-v1",
}
MATCHER_POLICY_IDS = {
    ARM_ORDER[0]: "saea-a2t-ground-qualification-m0-v1",
    ARM_ORDER[1]: "saea-a2t-ground-qualification-g1-v1",
}
SAMPLE_COUNT = 8
BATCH_SIZE = 2
CONCURRENCY = 2
QUEUE_DEPTH = 4
EXPECTED_MODEL_CONTACTS = 16
MAX_MODEL_CONTACTS = 16
EXACT_AUDIO_SECONDS = 90.192
PLANNED_AUDIO_SECONDS = 91
CONTEXT_TOKENS = 32_768
PROMPT_PLUS_COMPLETION_CAP = 24_576
MINIMUM_HEADROOM = 8_192
COMPLETION_TOKENS = 1_024
SPECIAL_TOKEN_RESERVE = 512

MODEL_FRAGMENT = "q4km-mmproj-free-speech-native-np2-a2t-max1024"
DATASET_FRAGMENT = "audio2tool-ground-qual-104"
BASELINE_FRAGMENT = "a2t-native-structured-action"
EXPERIMENT_FRAGMENT = "a2t-native-structured-action-fixed8-v1"
COMPOSED_CONFIG_SHA256 = (
    "e8a16944585d99e62bdc9d6c86d3181c0fa23c10d1295118edf2225752a8a526"
)
PROTOCOL_SHA256 = "a6d6634e2139673acd6ddee13fe87280e906b8bca09cbfe355cab0c00507f034"
BASELINE_CONFIG_RELPATH = Path("configs/baseline/a2t-native-structured-action.json")
BASELINE_CONFIG_SHA256 = (
    "bada07bb961016303842cf013cb71b8200873ab5c9b82a8cba96907f9b735ad0"
)
EXPERIMENT_CONFIG_RELPATH = Path(
    "configs/experiment/a2t-native-structured-action-fixed8-v1.json"
)
EXPERIMENT_CONFIG_SHA256 = (
    "42e285a6c6713215c21f418dc5b8234bd8423e8b71050dabd835aa1afca5b03b"
)
REGISTERED_PLAN_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-native-structured-action-fixed8-v1/launcher/"
    "registered-flight-plan.json"
)
REGISTERED_PLAN_SHA256 = (
    "fc522f84047f6cf6d07eb90f7edd0508f3b5658507fdf59e49c8fb033710fb39"
)

ROSTER_RELPATH = Path("docs/receipts/a2t/A2T-NATIVE-STRUCTURED-ACTION-FIXED8.json")
ROSTER_SHA256 = "b777f05e830af84209d6aa3403fe86d3835991452f983b3185214990004a4be3"
PARENT_REQUESTS_RELPATH = Path(
    "docs/receipts/a2t/A2T-NATIVE-STRUCTURED-ACTION-FIXED8-PARENT-REQUESTS.json"
)
PARENT_REQUESTS_SHA256 = (
    "02940b2f5bed784df16e3985ec6136dac9cda65ec9fa206c600f8da1627a38bd"
)
PARENT_ROSTER_SHA256 = (
    "eeb90abbe8695e449c676f18339db6618cb6d606d6c1e7c656626e4e9b6b6c16"
)
PARENT_SPLIT_IDENTITY_HASH = (
    "c6bb080bb264733087b3da352fe930702ec6509bc02e6a639b0f4c30c5017dac"
)
SCHEMA_RELPATH = Path(
    "knowledge/audio2tool/structured-action-schema-v1/response-format.json"
)
SCHEMA_SHA256 = "8fe5db869f044b9e952765f7bee045027ad137db2cc445ff428db5303fb1a2ed"
SCHEMA_BYTES = 91_407
SCHEMA_BUILD_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-structured-action-schema-build-v1/build-receipt.json"
)
SCHEMA_BUILD_SHA256 = "2931aba40a9a94921f670b857a052e69e1fba9820250cb1a8206b9838b35c581"
HANDBOOK_RELPATH = Path("knowledge/audio2tool/executable-ground-v1/handbook.txt")
HANDBOOK_SHA256 = "58ba08f3cebbe390156506653051d54aa37796822f49f5b851fd6eba4818fbc8"
REGISTRY_SHA256 = "7c50b0e8b49f514b169f4040c38ac67ca69ebaf361f754f1f3e994c7cb09d0a4"
RUNTIME_RECEIPT_RELPATH = Path("docs/receipts/runtime-q4km-mmproj-free.json")
RUNTIME_RECEIPT_SHA256 = (
    "b061c8f53635916f6169acac75896048112a9fad5860db4bf7d1a51700e96e77"
)
LLAMA_CPP_BUILD_COMMIT = "04ccc72a2207347ca76161b93fd9d846dd0a8675"
DECODER_GGUF_SHA256 = "0751c279498785c0b07130ae7748038d1e2cfd04617928e4557063807f98066d"
PROMOTION_RECEIPT = Path(
    "/home/chao/feat-cache/a2t-q4km-packets-04ccc72a/A2T-GROUND-QUAL-104-promotion.json"
)
PROMOTION_SHA256 = "b350567a6dd8b5d9021725756424f2b6ae99803c8c0327901c724fe3ebe8a47f"
PROMPT_FIT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-02-a2t-executable-ground-prompt-fit-468-v1/prompt-fit-result.json"
)
PROMPT_FIT_SHA256 = "277f5147b8ce1ac9acca538e4b8a83a2c5b282c62f278afd56e27c9fd61a2fd5"
REGISTRY_PROMPT_FIT_RELPATH = Path(
    "docs/checks/speech-aware-evidence-acquisition/2026-08-25-a2t-g1/"
    "prompt-fit-np2.json"
)
REGISTRY_PROMPT_FIT_SHA256 = (
    "0c77812d9439b6a7d6d3ff0227fc27924f617245d1ec9a0cbca20960f090946b"
)
TEXT_PROMPT_TOKENS = {
    ARM_ORDER[0]: 13_236,
    ARM_ORDER[1]: 12_557,
}
TEXT_PROMPT_MESSAGE_SHA256 = {
    ARM_ORDER[0]: "7ffb41343267f6caae7fc727f631a4d7320552b84c80f308be0ddab2fdae34a0",
    ARM_ORDER[1]: "95fec4672fb85ea2654247b34d334827a3450cbb7edb7254ec7650e8dfe910c5",
}
RUNTIME_ROOT = Path("/home/chao")


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file_hash(path: Path, expected: str, label: str) -> None:
    try:
        measured = sha256_file(path)
    except OSError as error:
        raise RuntimeError(f"cannot read governed {label}: {path}: {error}") from error
    if measured != expected:
        raise RuntimeError(
            f"{label} SHA-256 drift: expected {expected}, measured {measured}"
        )


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"cannot read governed JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise RuntimeError(f"governed JSON must be an object: {path}")
    return value


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        "".join(
            json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def execution_plan(attempt_id: str) -> ExecutionPlan:
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        split_identity_hash=SPLIT_IDENTITY_HASH,
        planned_model_calls=MAX_MODEL_CONTACTS,
        planned_gpu_hours=0.2,
        planned_speech_audio_seconds=PLANNED_AUDIO_SECONDS,
        protocol_hash=PROTOCOL_SHA256,
        attempt_id=attempt_id,
    ).validate()


def load_registered_flight_plan(path: Path) -> dict[str, object]:
    expected_path = (REPO / REGISTERED_PLAN_RELPATH).resolve()
    if Path(path).resolve() != expected_path:
        raise RuntimeError("registered flight plan path is not the frozen input")
    require_file_hash(expected_path, REGISTERED_PLAN_SHA256, "registered flight plan")
    document = _read_json(expected_path)
    attempts = document.get("attempts")
    if (
        document.get("schema")
        != "saea-a2t-native-structured-action-registered-flight-plan-v1"
        or document.get("run_id") != RUN_ID
        or document.get("flight_id") != "flight-20260903T013000Z"
        or tuple(document.get("arm_order", ())) != ARM_ORDER
        or not isinstance(attempts, Mapping)
        or set(attempts) != set(ARM_ORDER)
    ):
        raise RuntimeError("registered flight plan identity or arm order drift")
    plans: dict[str, ExecutionPlan] = {}
    for arm in ARM_ORDER:
        raw = attempts.get(arm)
        if not isinstance(raw, Mapping):
            raise RuntimeError(f"registered flight plan lacks {arm}")
        try:
            plan = ExecutionPlan(**raw).validate()
        except (TypeError, ValueError) as error:
            raise RuntimeError(
                f"registered {arm} ExecutionPlan is malformed"
            ) from error
        if raw.get("attempt_id") != ATTEMPT_IDS[arm]:
            raise RuntimeError(f"registered {arm} attempt identity drift")
        expected = execution_plan(ATTEMPT_IDS[arm])
        if asdict(plan) != asdict(expected):
            raise RuntimeError(f"registered {arm} ExecutionPlan drift")
        plans[arm] = plan
    return {**document, "validated_plans": plans}


def assert_run_has_no_attempt_records(root: Path) -> None:
    attempt_root = Path(root) / "attempts" / RUN_ID
    if attempt_root.exists() and any(attempt_root.iterdir()):
        raise RuntimeError(
            "registered run id already has an attempt record; this one-shot flight is closed"
        )


def validate_roster(document: Mapping[str, object]) -> dict[str, object]:
    source = document.get("source")
    items = document.get("items")
    if (
        document.get("schema") != "saea-a2t-native-schema-roster-v1"
        or document.get("split_name") != SPLIT_ID
        or document.get("split_role") != "discovery"
        or document.get("split_identity_hash") != SPLIT_IDENTITY_HASH
        or document.get("count") != SAMPLE_COUNT
        or not isinstance(source, Mapping)
        or source.get("count") != 104
        or source.get("sha256") != PARENT_ROSTER_SHA256
        or source.get("split_identity_hash") != PARENT_SPLIT_IDENTITY_HASH
        or not isinstance(items, list)
        or len(items) != SAMPLE_COUNT
    ):
        raise RuntimeError("governed fixed-eight roster identity drift")
    sample_ids: list[str] = []
    tiers: list[str] = []
    packet_ids: list[str] = []
    seconds = 0.0
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise RuntimeError(f"roster item {index} is not an object")
        sample_id = item.get("sample_id")
        tier = item.get("tier")
        packet_id = item.get("packet_id")
        media_relpath = item.get("media_relpath")
        audio_sha256 = item.get("audio_sha256")
        audio_seconds = item.get("audio_seconds")
        if (
            not isinstance(sample_id, str)
            or not sample_id
            or not isinstance(tier, str)
            or not tier
            or not isinstance(packet_id, str)
            or not packet_id
            or not isinstance(media_relpath, str)
            or not media_relpath.endswith(".wav")
            or not isinstance(audio_sha256, str)
            or len(audio_sha256) != 64
            or isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or audio_seconds <= 0
        ):
            raise RuntimeError(f"roster item {index} is malformed")
        sample_ids.append(sample_id)
        tiers.append(tier)
        packet_ids.append(packet_id)
        seconds += float(audio_seconds)
    if len(set(sample_ids)) != SAMPLE_COUNT or len(set(packet_ids)) != SAMPLE_COUNT:
        raise RuntimeError("fixed-eight sample and packet identities must be unique")
    if len(set(tiers)) != SAMPLE_COUNT:
        raise RuntimeError("fixed-eight roster requires one row per tier")
    if abs(float(document.get("audio_seconds_total", -1)) - 45.096) > 1e-9:
        raise RuntimeError("fixed-eight receipt audio duration drift")
    if abs(seconds - 45.096) > 1e-6:
        raise RuntimeError("fixed-eight item audio duration sum drift")
    return {
        "items": tuple(items),
        "sample_ids": tuple(sorted(sample_ids)),
        "packet_ids": tuple(packet_ids),
        "audio_seconds_total": seconds,
    }


def validate_parent_request_bindings(
    document: Mapping[str, object],
    *,
    sample_ids: Sequence[str],
    packet_bindings: Mapping[str, Mapping[str, str]],
) -> dict[str, dict[str, Mapping[str, object]]]:
    source_rows_by_arm = document.get("requests")
    sources = document.get("sources")
    extraction = document.get("extraction")
    expected_ids = set(sample_ids)
    if (
        document.get("schema")
        != "saea-a2t-native-structured-action-parent-request-binding-v1"
        or document.get("experiment_id") != RUN_ID
        or document.get("split_identity_hash") != SPLIT_IDENTITY_HASH
        or document.get("sample_count") != SAMPLE_COUNT
        or document.get("request_count") != EXPECTED_MODEL_CONTACTS
        or not isinstance(source_rows_by_arm, Mapping)
        or tuple(source_rows_by_arm) != ARM_ORDER
        or not isinstance(sources, Mapping)
        or set(sources) != set(ARM_ORDER)
        or not isinstance(extraction, Mapping)
        or extraction.get("selected_channel") != "MODEL_REQUEST"
        or extraction.get("model_response_records_parsed") != 0
        or extraction.get("score_records_read") != 0
        or extraction.get("gold_read") is not False
        or extraction.get("reference_transcript_read") is not False
        or extraction.get("selection_or_tuning_performed") is not False
    ):
        raise RuntimeError("historical parent request binding identity drift")
    result: dict[str, dict[str, Mapping[str, object]]] = {}
    for arm in ARM_ORDER:
        rows = source_rows_by_arm.get(arm)
        if not isinstance(rows, list) or len(rows) != SAMPLE_COUNT:
            raise RuntimeError(f"historical parent request binding lacks {arm}")
        by_id: dict[str, Mapping[str, object]] = {}
        for row in rows:
            if not isinstance(row, Mapping):
                raise RuntimeError(
                    f"historical parent request row in {arm} is malformed"
                )
            sample_id = row.get("sample_id")
            slot = row.get("id_slot")
            source_request_id = row.get("source_request_id")
            payload_sha256 = row.get("source_payload_sha256")
            packet_sha256 = row.get("speech_packet_sha256")
            if (
                not isinstance(sample_id, str)
                or sample_id in by_id
                or sample_id not in expected_ids
                or isinstance(slot, bool)
                or slot not in {0, 1}
                or not isinstance(source_request_id, str)
                or not source_request_id
                or not isinstance(payload_sha256, str)
                or len(payload_sha256) != 64
                or not isinstance(packet_sha256, str)
                or len(packet_sha256) != 64
                or packet_sha256 != packet_bindings[sample_id]["sha256"]
            ):
                raise RuntimeError(
                    f"historical parent request row for {sample_id!r} drifted"
                )
            by_id[sample_id] = dict(row)
        if set(by_id) != expected_ids:
            raise RuntimeError(f"historical parent request identities drift for {arm}")
        result[arm] = by_id
    return result


def _speech_messages(
    adapter: object,
    sample: object,
    packet_binding: Mapping[str, str],
) -> tuple[Mapping[str, object], ...]:
    base = tuple(adapter.assemble_prompt(sample, None))
    if (
        len(base) != 2
        or base[0].get("role") != "system"
        or base[1].get("role") != "user"
    ):
        raise RuntimeError("strict arm requires the exact two-message direct prompt")
    return (
        dict(base[0]),
        {
            "role": "user",
            "content": [
                {
                    "type": "input_speech_features",
                    "speech_features": {
                        "packet_id": packet_binding["packet_id"],
                        "sha256": packet_binding["sha256"],
                        "role": "query",
                    },
                }
            ],
        },
    )


def _decoding(response_format: Mapping[str, object], slot: int) -> dict[str, object]:
    return {
        "temperature": 0,
        "seed": 20260803,
        "max_tokens": COMPLETION_TOKENS,
        "id_slot": slot,
        "response_format": response_format,
    }


def request_measurement(
    *,
    arm: str,
    sample_id: str,
    messages: Sequence[Mapping[str, object]],
    decoding_params: Mapping[str, object],
    packet_tokens: int,
    text_prompt_tokens: int,
    key_representation_id: str | None = None,
    matcher_policy_id: str | None = None,
) -> dict[str, object]:
    if arm not in ARM_ORDER or not isinstance(sample_id, str) or not sample_id:
        raise RuntimeError("request measurement has an unknown arm or sample")
    expected_keys = {"temperature", "seed", "max_tokens", "id_slot", "response_format"}
    if set(decoding_params) != expected_keys:
        raise RuntimeError("strict decoding parameters drifted")
    slot = decoding_params["id_slot"]
    if (
        decoding_params["temperature"] != 0
        or decoding_params["seed"] != 20260803
        or decoding_params["max_tokens"] != COMPLETION_TOKENS
        or slot not in {0, 1}
        or not isinstance(decoding_params["response_format"], Mapping)
    ):
        raise RuntimeError("strict decoding values drifted")
    key_id = key_representation_id or KEY_REPRESENTATION_IDS[arm]
    policy_id = matcher_policy_id or MATCHER_POLICY_IDS[arm]
    if key_id != KEY_REPRESENTATION_IDS[arm] or policy_id != MATCHER_POLICY_IDS[arm]:
        raise RuntimeError("historical parent request provenance drifted")
    if (
        isinstance(packet_tokens, bool)
        or not isinstance(packet_tokens, int)
        or packet_tokens <= 0
        or isinstance(text_prompt_tokens, bool)
        or not isinstance(text_prompt_tokens, int)
        or text_prompt_tokens <= 0
    ):
        raise RuntimeError("prompt token components must be positive integers")
    serialized_prompt = _canonical_bytes(tuple(messages))
    request = {
        "arm": arm,
        "sample_id": sample_id,
        "messages": tuple(messages),
        "decoding_params": dict(decoding_params),
        "key_representation_id": key_id,
        "matcher_policy_id": policy_id,
    }
    prompt_tokens = text_prompt_tokens + packet_tokens + SPECIAL_TOKEN_RESERVE
    total_tokens = prompt_tokens + COMPLETION_TOKENS
    remaining = CONTEXT_TOKENS - total_tokens
    if total_tokens > PROMPT_PLUS_COMPLETION_CAP or remaining < MINIMUM_HEADROOM:
        raise RuntimeError(
            "serialized prompt is refused before contact because it leaves less than "
            "8192 tokens of operational headroom"
        )
    return {
        "arm": arm,
        "sample_id": sample_id,
        "id_slot": slot,
        "serialized_prompt_sha256": hashlib.sha256(serialized_prompt).hexdigest(),
        "system_message_sha256": canonical_sha256(messages[0]),
        "user_message_sha256": canonical_sha256(messages[1]),
        "decoding_params_sha256": canonical_sha256(decoding_params),
        "request_sha256": canonical_sha256(request),
        "response_format_sha256": canonical_sha256(decoding_params["response_format"]),
        "key_representation_id": key_id,
        "matcher_policy_id": policy_id,
        "text_prompt_tokens": text_prompt_tokens,
        "speech_feature_tokens": packet_tokens,
        "special_token_reserve": SPECIAL_TOKEN_RESERVE,
        "completion_tokens": COMPLETION_TOKENS,
        "prompt_tokens": prompt_tokens,
        "total_tokens": total_tokens,
        "remaining_tokens": remaining,
    }


def build_precontact_plan(
    *,
    adapters: Mapping[str, object],
    packet_bindings: Mapping[str, Mapping[str, str]],
    packet_tokens: Mapping[str, int],
    response_format: Mapping[str, object],
    text_prompt_tokens: Mapping[str, int],
    source_request_bindings: Mapping[str, Mapping[str, Mapping[str, object]]],
) -> dict[str, object]:
    if (
        tuple(adapters) != ARM_ORDER
        or set(text_prompt_tokens) != set(ARM_ORDER)
        or tuple(source_request_bindings) != ARM_ORDER
    ):
        raise RuntimeError("precontact plan requires the exact ordered arm surface")
    arm_rows: list[dict[str, object]] = []
    reference_ids: tuple[str, ...] | None = None
    for arm in ARM_ORDER:
        adapter = adapters[arm]
        samples = tuple(adapter.load_split(ground_flight.SPLIT_ID))
        samples = tuple(sorted(samples, key=lambda sample: sample.sample_id))
        sample_ids = tuple(sample.sample_id for sample in samples)
        if len(samples) != SAMPLE_COUNT or len(set(sample_ids)) != SAMPLE_COUNT:
            raise RuntimeError(
                "each strict arm requires the complete unique fixed eight"
            )
        if reference_ids is None:
            reference_ids = sample_ids
        elif sample_ids != reference_ids:
            raise RuntimeError("strict arms must carry identical sample order")
        if set(sample_ids) != set(packet_bindings) or set(sample_ids) != set(
            packet_tokens
        ):
            raise RuntimeError("sample, packet, and token identities differ")
        rows: list[dict[str, object]] = []
        for index, sample in enumerate(samples):
            messages = _speech_messages(
                adapter, sample, packet_bindings[sample.sample_id]
            )
            source_request = source_request_bindings[arm].get(sample.sample_id)
            if not isinstance(source_request, Mapping):
                raise RuntimeError("precontact plan lacks a historical source request")
            decoding = _decoding(response_format, int(source_request["id_slot"]))
            measured = request_measurement(
                arm=arm,
                sample_id=sample.sample_id,
                messages=messages,
                decoding_params=decoding,
                packet_tokens=packet_tokens[sample.sample_id],
                text_prompt_tokens=text_prompt_tokens[arm],
            )
            parent_decoding = dict(decoding)
            parent_decoding.pop("response_format")
            shared = {
                "sample_id": sample.sample_id,
                "task_instruction": messages[0]["content"],
                "speech_feature_parts": messages[1]["content"],
                "key_representation_id": KEY_REPRESENTATION_IDS[arm],
                "matcher_policy_id": MATCHER_POLICY_IDS[arm],
            }
            parent_contract = {
                **shared,
                "request_id": source_request["source_request_id"],
                "decoding_params": parent_decoding,
            }
            strict_contract = {
                **shared,
                "request_id": f"strict-contract-{sample.sample_id}",
                "decoding_params": decoding,
            }
            assert_only_response_format_factor(
                {sample.sample_id: parent_contract},
                {sample.sample_id: strict_contract},
                response_format,
            )
            measured["parent_request_contract_sha256"] = canonical_sha256(
                parent_contract
            )
            measured["strict_request_contract_sha256"] = canonical_sha256(
                strict_contract
            )
            measured["source_request_id"] = source_request["source_request_id"]
            measured["source_payload_sha256"] = source_request["source_payload_sha256"]
            measured["text_prompt_token_evidence"] = {
                "kind": "exact-historical-tokenizer-measurement",
                "prompt_shape": "speech-query-prefix-v2-direct",
                "text_tokens": text_prompt_tokens[arm],
                "special_token_reserve_applied_now": SPECIAL_TOKEN_RESERVE,
                "receipt_sha256": (
                    REGISTRY_PROMPT_FIT_SHA256
                    if arm == ARM_ORDER[0]
                    else PROMPT_FIT_SHA256
                ),
            }
            rows.append(measured)
        arm_rows.append({"arm": arm, "requests": rows})
    result = {
        "schema": "saea-a2t-native-structured-action-precontact-plan-v1",
        "run_id": RUN_ID,
        "arm_order": list(ARM_ORDER),
        "sample_count_per_arm": SAMPLE_COUNT,
        "expected_model_contacts": EXPECTED_MODEL_CONTACTS,
        "batch_size": BATCH_SIZE,
        "concurrency": CONCURRENCY,
        "queue_depth": QUEUE_DEPTH,
        "parent_request_binding_sha256": PARENT_REQUESTS_SHA256,
        "response_format": response_format,
        "arms": arm_rows,
    }
    return result


class PromptGuardedCoreClient:
    """Measure and hash the exact direct envelope immediately before delegation."""

    def __init__(
        self,
        core: object,
        *,
        arm: str,
        response_format: Mapping[str, object],
        packet_tokens: Mapping[str, int],
        text_prompt_tokens: int,
        expected_request_hashes: Mapping[str, str],
        record: Callable[[Mapping[str, object]], None],
    ) -> None:
        self.core = core
        self.arm = arm
        self.response_format = response_format
        self.packet_tokens = dict(packet_tokens)
        self.text_prompt_tokens = text_prompt_tokens
        self.expected_request_hashes = dict(expected_request_hashes)
        self.record = record

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        **kwargs: object,
    ) -> str:
        sample_id = kwargs.get("speech_feature_sample_id")
        decoding = kwargs.get("decoding_params")
        if not isinstance(sample_id, str) or not isinstance(decoding, Mapping):
            raise RuntimeError(
                "strict client requires a sample id and decoding mapping"
            )
        if decoding.get("response_format") is not self.response_format:
            raise RuntimeError("native response_format was copied or replaced")
        measured = request_measurement(
            arm=self.arm,
            sample_id=sample_id,
            messages=messages,
            decoding_params=decoding,
            packet_tokens=self.packet_tokens[sample_id],
            text_prompt_tokens=self.text_prompt_tokens,
            key_representation_id=kwargs.get("key_representation_id"),
            matcher_policy_id=kwargs.get("matcher_policy_id"),
        )
        expected = self.expected_request_hashes.get(sample_id)
        if expected is None or measured["request_sha256"] != expected:
            raise RuntimeError(f"precontact request hash drift for {sample_id!r}")
        self.record(measured)
        return self.core.complete(messages, **kwargs)


def assert_only_response_format_factor(
    parent_payloads: Mapping[str, Mapping[str, object]],
    strict_payloads: Mapping[str, Mapping[str, object]],
    response_format: Mapping[str, object],
) -> None:
    if not parent_payloads or set(parent_payloads) != set(strict_payloads):
        raise RuntimeError("parent and strict payload identities differ")
    for sample_id in sorted(parent_payloads):
        parent = json.loads(json.dumps(parent_payloads[sample_id]))
        strict = json.loads(json.dumps(strict_payloads[sample_id]))
        parent.pop("request_id", None)
        strict.pop("request_id", None)
        parent_decoding = parent.get("decoding_params")
        strict_decoding = strict.get("decoding_params")
        if not isinstance(parent_decoding, dict) or not isinstance(
            strict_decoding, dict
        ):
            raise RuntimeError("payload decoding blocks must be objects")
        observed = strict_decoding.pop("response_format", None)
        if observed != response_format or strict != parent:
            raise RuntimeError(
                f"strict payload for {sample_id!r} does not differ by only response_format"
            )


def run_two_arms_batched(
    sample_ids: Sequence[str],
    *,
    phase_runner: Callable[..., Sequence[object]],
) -> dict[str, tuple[object, ...]]:
    ordered = tuple(sample_ids)
    if len(ordered) != SAMPLE_COUNT or len(set(ordered)) != SAMPLE_COUNT:
        raise RuntimeError("two-arm run requires the exact unique fixed eight")
    result: dict[str, tuple[object, ...]] = {}
    for arm in ARM_ORDER:
        rows: list[object] = []
        for offset in range(0, SAMPLE_COUNT, BATCH_SIZE):
            batch = ordered[offset : offset + BATCH_SIZE]
            produced = tuple(phase_runner(arm=arm, sample_batch=batch))
            produced_ids = tuple(getattr(row, "sample_id", None) for row in produced)
            if produced_ids != batch:
                raise RuntimeError(
                    "phase result does not match its exact two-row batch"
                )
            rows.extend(produced)
        if len(rows) != SAMPLE_COUNT:
            raise RuntimeError("strict arm did not produce eight one-shot results")
        result[arm] = tuple(rows)
    return result


class _SubsetAdapter:
    def __init__(self, parent: object, sample_ids: Sequence[str]) -> None:
        samples = tuple(parent.load_split(ground_flight.SPLIT_ID))
        by_id = {sample.sample_id: sample for sample in samples}
        self.parent = parent
        self.samples = tuple(by_id[sample_id] for sample_id in sample_ids)

    def load_split(self, split_id: str) -> tuple[object, ...]:
        if split_id != ground_flight.SPLIT_ID:
            raise RuntimeError("subset adapter split drift")
        return self.samples

    def assemble_prompt(self, sample: object, supply: object):
        return self.parent.assemble_prompt(sample, supply)


class _MeasurementRecorder:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.rows: list[Mapping[str, object]] = []

    def __call__(self, row: Mapping[str, object]) -> None:
        line = json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n"
        with self.lock:
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(line)
                handle.flush()
            self.rows.append(dict(row))


def _trace_documents(run_dir: Path) -> tuple[Mapping[str, object], ...]:
    path = Path(run_dir) / f"{RUN_ID}.trace.jsonl"
    rows: list[Mapping[str, object]] = []
    for number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        value = json.loads(line)
        if not isinstance(value, Mapping):
            raise RuntimeError(f"trace row {number} is not an object")
        rows.append(value)
    if not rows:
        raise RuntimeError("strict arm trace is empty")
    return tuple(rows)


def _verified_split(sample_ids: Sequence[str]) -> VerifiedSplit:
    ids = tuple(sorted(sample_ids))
    if len(ids) != SAMPLE_COUNT or len(set(ids)) != SAMPLE_COUNT:
        raise RuntimeError("verified split requires the complete fixed eight")
    return VerifiedSplit(
        name=SPLIT_ID,
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        split_role="discovery",
        ids=ids,
        prefixed_ids=tuple(f"audio2tool/{sample_id}" for sample_id in ids),
        identity_hash=SPLIT_IDENTITY_HASH,
    )


def _seal_arm(
    *,
    root: Path,
    context: Mapping[str, object],
    plan: ExecutionPlan,
    run_dir: Path,
    session_receipt_path: Path,
    summary: object,
    client_summary: Mapping[str, object],
    arm: str,
) -> dict[str, object]:
    documents = _trace_documents(run_dir)
    rows, cost = build_phase_bundle_material(
        summary,
        documents,
        phase="M0_DIRECT",
        umbrella_lock_sha256=str(client_summary["cost"]["umbrella_lock_sha256"]),
    )
    frozen_rows = tuple({**row, "phase": arm} for row in rows)
    outputs = Path(run_dir) / f"{RUN_ID}.outputs.jsonl"
    _write_jsonl(outputs, frozen_rows)
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
            outputs_path=outputs,
            trace_manifest_hash=str(client_summary["trace_manifest_hash"]),
            cost=cost,
        ),
    )
    bundle = verify_bundle(manifest)
    if bundle.attempt_state != "OPENED" or len(bundle.outputs_rows) != SAMPLE_COUNT:
        raise RuntimeError("strict arm did not seal a complete eight-row manifest")
    return {
        "arm": arm,
        "manifest": str(manifest),
        "outputs": str(outputs),
        "trace_manifest_sha256": client_summary["trace_manifest_hash"],
        "request_count": client_summary["request_count"],
    }


def _run_arm(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    arm: str,
    plan: ExecutionPlan,
    run_dir: Path,
    session_receipt_path: Path,
) -> dict[str, object]:
    if arm not in ARM_ORDER:
        raise RuntimeError(f"unknown strict arm {arm!r}")
    expected_plan = execution_plan(ATTEMPT_IDS[arm])
    if asdict(plan) != asdict(expected_plan):
        raise RuntimeError(f"runtime ExecutionPlan drift for {arm}")
    _write_json(Path(run_dir) / "execution-plan.json", asdict(plan))
    adapter = context["adapters"][arm]
    samples = tuple(adapter.load_split(ground_flight.SPLIT_ID))
    binding = build_payload_binding(
        carrier_lock_key=AUDIO2TOOL_LOCK_KEY,
        samples=samples,
        data_root=root,
        carrier_root=context["carrier_root"],
    )
    core = FrozenCoreClient(
        plan=plan,
        gate=gate,
        transport=transport,
        run_dir=run_dir,
        binding=binding,
        arm="speech-feature-query",
        request_id_prefix=(
            "structured-registry" if arm == ARM_ORDER[0] else "structured-handbook"
        ),
        speech_feature_root=PROMOTION_RECEIPT.parent,
        speech_packet_bindings=context["packet_bindings"],
    )
    expected = {
        row["sample_id"]: row["request_sha256"]
        for arm_plan in context["precontact_plan"]["arms"]
        if arm_plan["arm"] == arm
        for row in arm_plan["requests"]
    }
    recorder = _MeasurementRecorder(Path(run_dir) / "prompt-measurements.jsonl")
    guarded = PromptGuardedCoreClient(
        core,
        arm=arm,
        response_format=context["response_format"],
        packet_tokens=context["packet_tokens"],
        text_prompt_tokens=TEXT_PROMPT_TOKENS[arm],
        expected_request_hashes=expected,
        record=recorder,
    )
    ordered_ids = tuple(sorted(context["sample_ids"]))

    def phase_runner(*, arm: str, sample_batch: tuple[str, ...]):
        subset = _SubsetAdapter(adapter, sample_batch)
        slot_map = {
            sample_id: int(
                context["source_request_bindings"][arm][sample_id]["id_slot"]
            )
            for sample_id in sample_batch
        }
        summary = ground_flight.run_direct_qualification_phase(
            adapter=subset,
            core_client=guarded,
            split_id=ground_flight.SPLIT_ID,
            speech_packet_bindings={
                sample_id: context["packet_bindings"][sample_id]
                for sample_id in sample_batch
            },
            slot_count=CONCURRENCY,
            decoding_params={
                "temperature": 0,
                "seed": 20260803,
                "max_tokens": COMPLETION_TOKENS,
                "response_format": context["response_format"],
            },
            key_representation_id=KEY_REPRESENTATION_IDS[arm],
            matcher_policy_id=MATCHER_POLICY_IDS[arm],
            slot_by_sample=slot_map,
        )
        return summary.results

    try:
        rows: list[object] = []
        for offset in range(0, SAMPLE_COUNT, BATCH_SIZE):
            rows.extend(
                phase_runner(
                    arm=arm,
                    sample_batch=ordered_ids[offset : offset + BATCH_SIZE],
                )
            )
        summary = ground_flight.GroundDirectSummary(tuple(rows))
    except BaseException:
        core.close()
        raise
    client_summary = core.close()
    if (
        client_summary["request_count"] != SAMPLE_COUNT
        or len(recorder.rows) != SAMPLE_COUNT
    ):
        raise RuntimeError("strict arm must make and measure exactly eight contacts")
    return _seal_arm(
        root=root,
        context=context,
        plan=plan,
        run_dir=run_dir,
        session_receipt_path=session_receipt_path,
        summary=summary,
        client_summary=client_summary,
        arm=arm,
    )


def _validate_runtime_receipt(document: Mapping[str, object]) -> None:
    llama = document.get("llama_cpp")
    files = document.get("gguf_files")
    if (
        document.get("schema") != "saea-runtime-receipt-v3"
        or not isinstance(llama, Mapping)
        or llama.get("build_commit") != LLAMA_CPP_BUILD_COMMIT
        or not isinstance(files, list)
        or len(files) != 1
        or not isinstance(files[0], Mapping)
        or files[0].get("sha256") != DECODER_GGUF_SHA256
    ):
        raise RuntimeError("runtime receipt or GGUF identity drift")


def _validate_prompt_token_evidence(
    registry: Mapping[str, object], handbook: Mapping[str, object]
) -> None:
    registry_rows = registry.get("envelopes")
    handbook_bounds = handbook.get("bounds")
    handbook_rows = (
        handbook_bounds.get("envelopes")
        if isinstance(handbook_bounds, Mapping)
        else None
    )
    registry_direct = (
        next(
            (
                row
                for row in registry_rows
                if isinstance(row, Mapping)
                and row.get("envelope_id") == "m0-direct-decode"
            ),
            None,
        )
        if isinstance(registry_rows, list)
        else None
    )
    handbook_direct = (
        next(
            (
                row
                for row in handbook_rows
                if isinstance(row, Mapping)
                and row.get("envelope_id") == "ground-direct"
            ),
            None,
        )
        if isinstance(handbook_rows, list)
        else None
    )
    handbook_message_hashes = (
        handbook_bounds.get("message_sha256")
        if isinstance(handbook_bounds, Mapping)
        else None
    )
    if (
        registry.get("prompt_order") != "speech-query-prefix-v2"
        or registry.get("special_token_reserve") != 2
        or not isinstance(registry_direct, Mapping)
        or registry_direct.get("text_prompt_tokens") != TEXT_PROMPT_TOKENS[ARM_ORDER[0]]
        or registry_direct.get("messages_sha256")
        != TEXT_PROMPT_MESSAGE_SHA256[ARM_ORDER[0]]
        or not isinstance(handbook_direct, Mapping)
        or handbook_direct.get("text_prompt_tokens") != TEXT_PROMPT_TOKENS[ARM_ORDER[1]]
        or handbook_direct.get("special_token_reserve") != 2
        or not isinstance(handbook_message_hashes, Mapping)
        or handbook_message_hashes.get("ground-direct")
        != TEXT_PROMPT_MESSAGE_SHA256[ARM_ORDER[1]]
    ):
        raise RuntimeError("exact historical direct-prompt token evidence drift")


def _validate_rendered_text_surfaces(adapters: Mapping[str, object]) -> None:
    if tuple(adapters) != ARM_ORDER:
        raise RuntimeError("rendered text validation requires the exact arm order")
    audit_packet_ids = {
        ARM_ORDER[0]: "audit/a2t-g1-prompt-fit/query",
        ARM_ORDER[1]: "audit/a2t-executable-ground-prompt-fit/query",
    }
    for arm in ARM_ORDER:
        samples = tuple(adapters[arm].load_split(ground_flight.SPLIT_ID))
        if not samples:
            raise RuntimeError(f"rendered text validation lacks samples for {arm}")
        messages = _speech_messages(
            adapters[arm],
            samples[0],
            {"packet_id": audit_packet_ids[arm], "sha256": "0" * 64},
        )
        if canonical_sha256(messages) != TEXT_PROMPT_MESSAGE_SHA256[arm]:
            raise RuntimeError(
                f"rendered {arm} direct message no longer matches its exact token count"
            )


def _load_packet_surface(
    roster: Mapping[str, object], promotion: Mapping[str, object]
) -> tuple[dict[str, dict[str, str]], dict[str, int]]:
    rows = promotion.get("packets")
    if not isinstance(rows, list) or promotion.get("count") != 104:
        raise RuntimeError("promotion receipt geometry drift")
    promoted = {row.get("packet_id"): row for row in rows if isinstance(row, Mapping)}
    bindings: dict[str, dict[str, str]] = {}
    tokens: dict[str, int] = {}
    for item in roster["items"]:
        sample_id = str(item["sample_id"])
        packet_id = str(item["packet_id"])
        row = promoted.get(packet_id)
        if not isinstance(row, Mapping):
            raise RuntimeError(f"promotion lacks packet {packet_id!r}")
        packet = load_speech_feature_packet(
            PROMOTION_RECEIPT.parent,
            packet_id,
            expected_sha256=row.get("packet_sha256"),
            expected_decoder_gguf_sha256=DECODER_GGUF_SHA256,
        )
        if packet.audio_sha256 != item["audio_sha256"]:
            raise RuntimeError(f"packet audio identity drift for {sample_id!r}")
        bindings[sample_id] = {"packet_id": packet_id, "sha256": packet.packet_sha256}
        tokens[sample_id] = sum(chunk.n_tokens for chunk in packet.chunks)
    return bindings, tokens


def static_preflight(
    root: Path,
    registered_plan_path: Path | None = None,
) -> dict[str, object]:
    frozen_plan_path = registered_plan_path or (REPO / REGISTERED_PLAN_RELPATH)
    registered_flight = load_registered_flight_plan(frozen_plan_path)
    assert_run_has_no_attempt_records(root)
    commit = require_clean_study_repo(REPO)
    composed = compose(
        REPO,
        MODEL_FRAGMENT,
        DATASET_FRAGMENT,
        BASELINE_FRAGMENT,
        EXPERIMENT_FRAGMENT,
    )
    require_file_hash(
        REPO / BASELINE_CONFIG_RELPATH,
        BASELINE_CONFIG_SHA256,
        "structured-action baseline config",
    )
    require_file_hash(
        REPO / EXPERIMENT_CONFIG_RELPATH,
        EXPERIMENT_CONFIG_SHA256,
        "fixed-eight structured-action experiment config",
    )
    if composed.config_hash != COMPOSED_CONFIG_SHA256:
        raise RuntimeError("composed config identity drift")
    if protocol_hash(
        composed.config_hash, "speech-feature-query", SPLIT_IDENTITY_HASH
    ) != (PROTOCOL_SHA256):
        raise RuntimeError("structured ExecutionPlan protocol drift")
    values = composed.values
    contact_budget = values.get("contact_budget")
    execution_protocol = values.get("execution_protocol")
    if (
        values.get("profile_slot_count") != CONCURRENCY
        or values.get("profile_queue_depth_multiplier") != 2
        or values.get("obs_batch_samples") != BATCH_SIZE
        or values.get("max_concurrent_model_requests") != CONCURRENCY
        or values.get("queue_depth") != QUEUE_DEPTH
        or values.get("per_slot_context_tokens") != CONTEXT_TOKENS
        or values.get("prompt_plus_completion_cap_per_slot")
        != PROMPT_PLUS_COMPLETION_CAP
        or values.get("operational_headroom_token_minimum") != MINIMUM_HEADROOM
        or values.get("special_token_reserve") != SPECIAL_TOKEN_RESERVE
        or values.get("repair_contacts") != 0
        or values.get("retries") != 0
        or values.get("resends") != 0
        or values.get("network_jitter_testing") is not False
        or values.get("speech_native_contact_ceiling_per_task") != 1
        or values.get("decoding_params")
        != {
            "temperature": 0,
            "seed": 20260803,
            "max_tokens": COMPLETION_TOKENS,
            "id_slot": "per-sample",
        }
        or not isinstance(contact_budget, Mapping)
        or contact_budget.get("sample_count") != SAMPLE_COUNT
        or contact_budget.get("new_model_calls") != MAX_MODEL_CONTACTS
        or contact_budget.get("planned_model_calls") != MAX_MODEL_CONTACTS
        or contact_budget.get("exact_speech_audio_seconds") != EXACT_AUDIO_SECONDS
        or contact_budget.get("planned_speech_audio_seconds") != PLANNED_AUDIO_SECONDS
        or contact_budget.get("planned_gpu_hours") != 0.2
        or contact_budget.get("tokenizer_contacts") != 0
        or not isinstance(execution_protocol, Mapping)
        or tuple(execution_protocol.get("new_cell_order", ())) != ARM_ORDER
        or execution_protocol.get("batch_slots") != BATCH_SIZE
        or execution_protocol.get("max_concurrent_model_requests") != CONCURRENCY
        or execution_protocol.get("queue_depth") != QUEUE_DEPTH
        or execution_protocol.get("expected_and_maximum_new_calls")
        != MAX_MODEL_CONTACTS
    ):
        raise RuntimeError("batch, queue, slot, or decoding config drift")

    roster_path = REPO / ROSTER_RELPATH
    require_file_hash(roster_path, ROSTER_SHA256, "fixed-eight roster")
    roster = validate_roster(_read_json(roster_path))
    schema_path = Path(root) / SCHEMA_RELPATH
    require_file_hash(schema_path, SCHEMA_SHA256, "structured response format")
    if schema_path.stat().st_size != SCHEMA_BYTES:
        raise RuntimeError("structured response format byte count drift")
    response_format = _read_json(schema_path)
    wrapper = response_format.get("json_schema")
    schema = wrapper.get("schema") if isinstance(wrapper, Mapping) else None
    if (
        response_format.get("type") != "json_schema"
        or not isinstance(wrapper, Mapping)
        or wrapper.get("strict") is not True
        or not isinstance(schema, Mapping)
        or schema.get("type") != "array"
    ):
        raise RuntimeError("structured response format shape drift")
    require_file_hash(
        REPO / SCHEMA_BUILD_RELPATH, SCHEMA_BUILD_SHA256, "schema build receipt"
    )
    require_file_hash(
        Path(root) / HANDBOOK_RELPATH, HANDBOOK_SHA256, "executable handbook"
    )
    require_file_hash(
        REPO / PROMPT_FIT_RELPATH, PROMPT_FIT_SHA256, "handbook prompt fit"
    )
    require_file_hash(
        REPO / REGISTRY_PROMPT_FIT_RELPATH,
        REGISTRY_PROMPT_FIT_SHA256,
        "registry prompt fit",
    )
    registry_prompt_fit = _read_json(REPO / REGISTRY_PROMPT_FIT_RELPATH)
    handbook_prompt_fit = _read_json(REPO / PROMPT_FIT_RELPATH)
    _validate_prompt_token_evidence(registry_prompt_fit, handbook_prompt_fit)
    require_file_hash(
        REPO / RUNTIME_RECEIPT_RELPATH, RUNTIME_RECEIPT_SHA256, "runtime receipt"
    )
    _validate_runtime_receipt(_read_json(REPO / RUNTIME_RECEIPT_RELPATH))
    require_file_hash(PROMOTION_RECEIPT, PROMOTION_SHA256, "packet promotion receipt")
    promotion = _read_json(PROMOTION_RECEIPT)
    packet_bindings, packet_tokens = _load_packet_surface(roster, promotion)
    parent_requests_path = REPO / PARENT_REQUESTS_RELPATH
    require_file_hash(
        parent_requests_path,
        PARENT_REQUESTS_SHA256,
        "historical parent request binding",
    )
    source_request_bindings = validate_parent_request_bindings(
        _read_json(parent_requests_path),
        sample_ids=roster["sample_ids"],
        packet_bindings=packet_bindings,
    )

    lock = load_lock(umbrella_lock_path(REPO))
    carrier_root = asset_dir(lock, AUDIO2TOOL_LOCK_KEY, root)
    require_file_hash(
        carrier_root / "tools_registry.csv", REGISTRY_SHA256, "tool registry"
    )
    handbook = (Path(root) / HANDBOOK_RELPATH).read_text(encoding="ascii")
    adapters = {
        ARM_ORDER[0]: ground_flight.GroundQualificationAdapter(
            lock,
            root,
            repo_root=REPO,
            receipt_items=roster["items"],
            mode=ground_flight.REGISTRY_DIRECT,
            handbook=handbook,
        ),
        ARM_ORDER[1]: ground_flight.GroundQualificationAdapter(
            lock,
            root,
            repo_root=REPO,
            receipt_items=roster["items"],
            mode=ground_flight.FULL_EXECUTABLE_GROUND,
            handbook=handbook,
        ),
    }
    _validate_rendered_text_surfaces(adapters)
    precontact = build_precontact_plan(
        adapters=adapters,
        packet_bindings=packet_bindings,
        packet_tokens=packet_tokens,
        response_format=response_format,
        text_prompt_tokens=TEXT_PROMPT_TOKENS,
        source_request_bindings=source_request_bindings,
    )
    launcher_hash = sha256_file(Path(__file__))
    validated_plans = registered_flight["validated_plans"]
    plan_hashes = {
        arm: canonical_sha256(asdict(validated_plans[arm])) for arm in ARM_ORDER
    }
    return {
        "commit": commit,
        "launcher_sha256": launcher_hash,
        "composed": composed,
        "config_sha256": composed.config_hash,
        "registered_flight_plan_sha256": REGISTERED_PLAN_SHA256,
        "registered_flight_plan": registered_flight,
        "registered_plans": validated_plans,
        "execution_plan_sha256": plan_hashes,
        "precontact_plan": precontact,
        "precontact_plan_sha256": canonical_sha256(precontact),
        "sample_ids": roster["sample_ids"],
        "items": roster["items"],
        "response_format": response_format,
        "packet_bindings": packet_bindings,
        "packet_tokens": packet_tokens,
        "source_request_bindings": source_request_bindings,
        "lock": lock,
        "carrier_root": carrier_root,
        "adapters": adapters,
        "runtime_receipt": load_runtime_receipt(REPO / RUNTIME_RECEIPT_RELPATH),
    }


def _stop(session: object, runtime_receipt: object, receipt_path: Path) -> None:
    stop_session(
        session,
        runtime_receipt=runtime_receipt,
        runtime_root=RUNTIME_ROOT,
        force_after_timeout=True,
        receipt_path=receipt_path,
    )


def launch(
    root: Path,
    registered_plan_path: Path | None = None,
) -> Mapping[str, object]:
    context = static_preflight(root, registered_plan_path)
    registered_flight = context["registered_flight_plan"]
    plans = context["registered_plans"]
    mission_dir = Path(root) / "runs" / RUN_ID / str(registered_flight["flight_id"])
    if mission_dir.exists():
        raise RuntimeError(f"mission directory already exists: {mission_dir}")
    mission_dir.mkdir(parents=True)
    attempt_ids = {arm: str(plans[arm].attempt_id) for arm in ARM_ORDER}
    flight_plan = {
        "schema": "saea-a2t-native-structured-action-flight-plan-v1",
        "run_id": RUN_ID,
        "study_commit": context["commit"],
        "launcher_sha256": context["launcher_sha256"],
        "config_sha256": context["config_sha256"],
        "baseline_config_sha256": BASELINE_CONFIG_SHA256,
        "experiment_config_sha256": EXPERIMENT_CONFIG_SHA256,
        "protocol_sha256": PROTOCOL_SHA256,
        "roster_sha256": ROSTER_SHA256,
        "parent_request_binding_sha256": PARENT_REQUESTS_SHA256,
        "handbook_sha256": HANDBOOK_SHA256,
        "registry_sha256": REGISTRY_SHA256,
        "response_format_file_sha256": SCHEMA_SHA256,
        "precontact_plan_sha256": context["precontact_plan_sha256"],
        "registered_flight_plan_sha256": context["registered_flight_plan_sha256"],
        "attempt_ids": attempt_ids,
        "execution_plan_sha256": context["execution_plan_sha256"],
        "arm_order": list(ARM_ORDER),
        "contacts": EXPECTED_MODEL_CONTACTS,
        "audio_seconds": EXACT_AUDIO_SECONDS,
    }
    _write_json(mission_dir / "flight-plan.json", flight_plan)
    _write_json(mission_dir / "precontact-plan.json", context["precontact_plan"])

    values = context["composed"].values
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        RUNTIME_ROOT,
        runtime_receipt_relpath=str(RUNTIME_RECEIPT_RELPATH.relative_to("docs")),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=Path(str(values["model_materialization_root"])),
    )
    for arm in ARM_ORDER:
        gate.assert_model_touch_allowed(plans[arm], full_hash=True)
    parsed = urlparse(str(values["base_url"]))
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
        raise RuntimeError("decoder endpoint must be explicit loopback")
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
            runtime_receipt=context["runtime_receipt"],
            host="127.0.0.1",
            port=parsed.port,
            session_id=f"{RUN_ID}-SESSION-20260903T013000Z",
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
            runtime_receipt=context["runtime_receipt"],
            runtime_root=RUNTIME_ROOT,
        )
        arms: list[dict[str, object]] = []
        for arm in ARM_ORDER:
            arms.append(
                _run_arm(
                    root=root,
                    context=context,
                    gate=gate,
                    transport=transport,
                    arm=arm,
                    plan=plans[arm],
                    run_dir=mission_dir / arm.lower(),
                    session_receipt_path=session_receipt,
                )
            )
        _stop(session, context["runtime_receipt"], stop_receipt)
        session = None
        if sum(int(row["request_count"]) for row in arms) != EXPECTED_MODEL_CONTACTS:
            raise RuntimeError("flight did not seal exactly sixteen measured contacts")
        receipt = {
            "schema": "saea-a2t-native-structured-action-fixed8-flight-v1",
            "run_id": RUN_ID,
            "status": "SEALED_UNSCORED",
            "study_commit": context["commit"],
            "mission_dir": str(mission_dir),
            "elapsed_seconds": time.perf_counter() - started,
            "contacts": EXPECTED_MODEL_CONTACTS,
            "audio_seconds": EXACT_AUDIO_SECONDS,
            "arms": arms,
            "session_receipt": str(session_receipt),
            "stop_receipt": str(stop_receipt),
            "gold_opened": False,
            "scorer_contacts": 0,
        }
        _write_json(mission_dir / "flight-receipt.json", receipt)
        return receipt
    except BaseException as error:
        for attempt_id in attempt_ids.values():
            abort_attempt_if_opened(root, RUN_ID, attempt_id, reason=repr(error))
        _write_json(
            mission_dir / "failure-receipt.json",
            {
                "schema": "saea-a2t-native-structured-action-fixed8-failure-v1",
                "run_id": RUN_ID,
                "attempt_ids": attempt_ids,
                "error": repr(error),
                "recontacted_rows": 0,
            },
        )
        raise
    finally:
        if session is not None:
            _stop(session, context["runtime_receipt"], stop_receipt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument(
        "--registered-flight-plan",
        type=Path,
        default=REPO / REGISTERED_PLAN_RELPATH,
    )
    args = parser.parse_args(argv)
    root = args.data_root or data_root()
    if args.run:
        print(
            json.dumps(
                launch(root, args.registered_flight_plan), indent=2, sort_keys=True
            )
        )
        return 0
    context = static_preflight(root, args.registered_flight_plan)
    print(
        json.dumps(
            {
                "preflight": "passed",
                "run_id": RUN_ID,
                "study_commit": context["commit"],
                "samples": len(context["sample_ids"]),
                "arms": list(ARM_ORDER),
                "precontact_plan_sha256": context["precontact_plan_sha256"],
                "execution_plan_sha256": context["execution_plan_sha256"],
                "contacts": {
                    "model": 0,
                    "network": 0,
                    "tokenizer": 0,
                    "scorer": 0,
                    "gold": 0,
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
