#!/usr/bin/env python3
"""Run the corrected, immutable V2 continuation of the fixed-eight flight.

V2 re-verifies the original registry source and the failed V1 successor,
creates a separate registry successor with the mechanically recomputed split
and protocol identities, and executes only the untouched handbook requests
under a distinct run and attempt.  No source or V1 byte is modified.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
from typing import Callable, Mapping, Sequence
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

_V1_PATH = Path(__file__).with_name("recover_native_structured_action_fixed8.py")
_SPEC = importlib.util.spec_from_file_location("_saea_structured_recovery_v1", _V1_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("cannot load the fixed-eight V1 recovery source")
v1 = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault(_SPEC.name, v1)
_SPEC.loader.exec_module(v1)
source = v1.source

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    abort_attempt_if_opened,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import ComposedConfig  # noqa: E402
from speech_aware_evidence_acquisition.data.splits import (  # noqa: E402
    prefixed,
    split_identity_hash,
)


RUN_ID = "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-RECOVERY-V2"
SOURCE_RUN_ID = source.RUN_ID
SOURCE_FLIGHT_ID = "flight-20260903T013000Z"
SOURCE_MISSION_RELPATH = Path("runs") / SOURCE_RUN_ID / SOURCE_FLIGHT_ID
REGISTRY_ATTEMPT_ID = source.ATTEMPT_IDS[source.ARM_ORDER[0]]
ORIGINAL_HANDBOOK_ATTEMPT_ID = source.ATTEMPT_IDS[source.ARM_ORDER[1]]
V1_RECOVERY_ATTEMPT_ID = v1.RECOVERY_ATTEMPT_ID
RECOVERY_ATTEMPT_ID = "attempt-20260903T020500Z-handbook-strict-recovery-v2"
DECLARED_SPLIT_IDENTITY_SHA256 = source.SPLIT_IDENTITY_HASH
ACTUAL_SPLIT_IDENTITY_SHA256 = (
    "b15cf0c0874f7af7d10af6cc9801aae4535bbe57b5a6dc3add50bcdb40fd93aa"
)
SOURCE_PROTOCOL_SHA256 = source.PROTOCOL_SHA256
ACTUAL_PROTOCOL_SHA256 = (
    "a2f24da7254a62020d4dff5d681c873af0ff11e71126dae7b72b7b9b2a7158d0"
)
EXPECTED_SCORERS = ("a2t-toolcall",)
REGISTRY_V1_DIRNAME = v1.REGISTRY_SUCCESSOR_DIRNAME
REGISTRY_V2_DIRNAME = "registry_strict_action_recovery_v2"
HANDBOOK_V2_DIRNAME = "handbook_strict_action_recovery_v2"
SERVICE_V2_DIRNAME = "recovery-service-v2"
REGISTRY_V2_RECEIPT_NAME = "registry-recovery-v2-receipt.json"
FLIGHT_V2_RECEIPT_NAME = "recovery-v2-flight-receipt.json"
FAILURE_V2_RECEIPT_NAME = "recovery-v2-failure-receipt.json"
PREREGISTRATION_PATH = Path(__file__).with_name("recovery-v2-preregistration.json")
PREREGISTRATION_SHA256 = (
    "68524eb21aa5853505e191d98910480e2ba0dadb950984ad57f6cb77051b2b7d"
)
EXECUTION_PLAN_PATH = Path(__file__).with_name("recovery-v2-execution-plan.json")
EXECUTION_PLAN_FILE_SHA256 = (
    "4b4ae113811f380980e0564926bf38f554489dc72a1f83da07548436496aae56"
)
EXECUTION_PLAN_CANONICAL_SHA256 = (
    "f0ab0ac216de7b09f3fdb8f68cefcfb31e1ec26ef89bc58fc058df4ae7dd7392"
)


class RecoveryV2Error(RuntimeError):
    """The corrected source, identity, or one-shot V2 target failed closed."""


@dataclass(frozen=True)
class SourceHashesV2:
    source_flight_plan_sha256: str
    source_precontact_plan_sha256: str
    source_failure_receipt_sha256: str
    original_manifest_sha256: str
    original_outputs_sha256: str
    original_trace_sha256: str
    original_trace_manifest_sha256: str
    registry_attempt_sha256: str
    failed_v1_manifest_sha256: str
    failed_v1_outputs_sha256: str
    failed_v1_trace_sha256: str
    failed_v1_trace_manifest_sha256: str
    failed_v1_receipt_sha256: str
    successor_v2_manifest_sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_sha256(document: object) -> str:
    raw = json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    if not Path(path).is_file() or _sha256(path) != expected:
        raise RecoveryV2Error(f"{label} SHA-256 drift")


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RecoveryV2Error(f"{label} is not readable UTF-8 JSON: {error}") from error
    if not isinstance(document, dict):
        raise RecoveryV2Error(f"{label} must be a JSON object")
    return document


def recovery_v2_execution_plan() -> ExecutionPlan:
    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=ACTUAL_SPLIT_IDENTITY_SHA256,
        planned_model_calls=8,
        planned_gpu_hours=0.1,
        planned_speech_audio_seconds=46,
        protocol_hash=ACTUAL_PROTOCOL_SHA256,
        attempt_id=RECOVERY_ATTEMPT_ID,
    ).validate()


def load_v2_preregistration() -> dict[str, object]:
    _require_hash(PREREGISTRATION_PATH, PREREGISTRATION_SHA256, "V2 preregistration")
    _require_hash(EXECUTION_PLAN_PATH, EXECUTION_PLAN_FILE_SHA256, "V2 execution plan")
    preregistration = _read_object(PREREGISTRATION_PATH, "V2 preregistration")
    plan_document = _read_object(EXECUTION_PLAN_PATH, "V2 execution plan")
    plan = recovery_v2_execution_plan()
    correction = preregistration.get("identity_correction")
    failed_v1_contract = preregistration.get("failed_v1_contract")
    if (
        preregistration.get("schema")
        != "saea-a2t-native-structured-action-fixed8-recovery-v2-preregistration-v1"
        or preregistration.get("run_id") != RUN_ID
        or preregistration.get("source_run_id") != SOURCE_RUN_ID
        or preregistration.get("source_flight_id") != SOURCE_FLIGHT_ID
        or preregistration.get("source_mission_relpath")
        != SOURCE_MISSION_RELPATH.as_posix()
        or preregistration.get("remaining_contact_arm") != source.ARM_ORDER[1]
        or preregistration.get("remaining_model_calls") != 8
        or preregistration.get("registry_recontact_authorized") is not False
        or preregistration.get("manifest_scorers") != list(EXPECTED_SCORERS)
        or preregistration.get("recovery_execution_plan") != asdict(plan)
        or preregistration.get("recovery_execution_plan_sha256")
        != EXECUTION_PLAN_CANONICAL_SHA256
        or plan_document != asdict(plan)
        or _canonical_sha256(plan_document) != EXECUTION_PLAN_CANONICAL_SHA256
        or not isinstance(correction, Mapping)
        or correction.get("declared_split_identity_sha256")
        != DECLARED_SPLIT_IDENTITY_SHA256
        or correction.get("recomputed_split_identity_sha256")
        != ACTUAL_SPLIT_IDENTITY_SHA256
        or correction.get("recomputed_protocol_sha256") != ACTUAL_PROTOCOL_SHA256
        or correction.get("composed_config_sha256") != source.COMPOSED_CONFIG_SHA256
        or correction.get("arm") != "speech-feature-query"
        or not isinstance(failed_v1_contract, Mapping)
        or failed_v1_contract.get("authorized_commit")
        != "d5325dbe7b16cb4f0faba7514af15e24d6e988d1"
        or failed_v1_contract.get("launcher_sha256") != _sha256(_V1_PATH)
        or failed_v1_contract.get("launcher_sha256")
        != "5b4b323bd4587a922028734545cd1eb09c95edfe7558f4ed3fbe94245c4e98ec"
        or failed_v1_contract.get("preregistration_sha256")
        != v1.PREREGISTRATION_SHA256
        or failed_v1_contract.get("execution_plan_file_sha256")
        != v1.EXECUTION_PLAN_FILE_SHA256
    ):
        raise RecoveryV2Error("V2 preregistration identity drift")
    return preregistration


def _source_hashes(preregistration: Mapping[str, object]) -> SourceHashesV2:
    hashes = preregistration.get("source_hashes")
    if not isinstance(hashes, Mapping):
        raise RecoveryV2Error("V2 preregistration lacks source hashes")
    try:
        return SourceHashesV2(**hashes)
    except TypeError as error:
        raise RecoveryV2Error(f"V2 source hashes are malformed: {error}") from error


def _source_paths(mission_dir: Path) -> dict[str, Path]:
    original = Path(mission_dir) / "registry_strict_action"
    failed_v1 = Path(mission_dir) / REGISTRY_V1_DIRNAME
    return {
        "source_flight_plan": Path(mission_dir) / "flight-plan.json",
        "source_precontact_plan": Path(mission_dir) / "precontact-plan.json",
        "source_failure": Path(mission_dir) / "failure-receipt.json",
        "original_manifest": original / f"{SOURCE_RUN_ID}.run-manifest.json",
        "original_outputs": original / f"{SOURCE_RUN_ID}.outputs.jsonl",
        "original_trace": original / f"{SOURCE_RUN_ID}.trace.jsonl",
        "original_trace_manifest": original / f"{SOURCE_RUN_ID}.trace-manifest.json",
        "failed_v1_manifest": failed_v1 / f"{SOURCE_RUN_ID}.run-manifest.json",
        "failed_v1_outputs": failed_v1 / f"{SOURCE_RUN_ID}.outputs.jsonl",
        "failed_v1_trace": failed_v1 / f"{SOURCE_RUN_ID}.trace.jsonl",
        "failed_v1_trace_manifest": failed_v1 / f"{SOURCE_RUN_ID}.trace-manifest.json",
        "failed_v1_receipt": Path(mission_dir) / "recovery-failure-receipt.json",
    }


def _validate_immutable_sources(
    mission_dir: Path,
    *,
    attempts_root: Path,
    expected: SourceHashesV2,
) -> dict[str, Path]:
    paths = _source_paths(mission_dir)
    for key, digest, label in (
        ("source_flight_plan", expected.source_flight_plan_sha256, "source flight plan"),
        (
            "source_precontact_plan",
            expected.source_precontact_plan_sha256,
            "source precontact plan",
        ),
        (
            "source_failure",
            expected.source_failure_receipt_sha256,
            "source failure receipt",
        ),
        ("original_manifest", expected.original_manifest_sha256, "original manifest"),
        ("original_outputs", expected.original_outputs_sha256, "original outputs"),
        ("original_trace", expected.original_trace_sha256, "original raw trace"),
        (
            "original_trace_manifest",
            expected.original_trace_manifest_sha256,
            "original trace manifest",
        ),
        ("failed_v1_manifest", expected.failed_v1_manifest_sha256, "failed V1 manifest"),
        ("failed_v1_outputs", expected.failed_v1_outputs_sha256, "failed V1 outputs"),
        ("failed_v1_trace", expected.failed_v1_trace_sha256, "failed V1 raw trace"),
        (
            "failed_v1_trace_manifest",
            expected.failed_v1_trace_manifest_sha256,
            "failed V1 trace manifest",
        ),
        ("failed_v1_receipt", expected.failed_v1_receipt_sha256, "failed V1 receipt"),
    ):
        _require_hash(paths[key], digest, label)
    attempt = (
        Path(attempts_root) / SOURCE_RUN_ID / f"{REGISTRY_ATTEMPT_ID}.json"
    )
    _require_hash(attempt, expected.registry_attempt_sha256, "registry attempt")
    attempt_document = _read_object(attempt, "registry attempt")
    actual = attempt_document.get("actual")
    if (
        attempt_document.get("run_id") != SOURCE_RUN_ID
        or attempt_document.get("attempt_id") != REGISTRY_ATTEMPT_ID
        or attempt_document.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != 8
        or abs(float(actual.get("audio_seconds", -1)) - 45.096) > 1e-9
    ):
        raise RecoveryV2Error("registry attempt is not the exact terminal source")
    paths["registry_attempt"] = attempt
    return paths


def assert_v2_targets_absent(root: Path, mission_dir: Path) -> None:
    attempt_paths = (
        Path(root)
        / "attempts"
        / SOURCE_RUN_ID
        / f"{ORIGINAL_HANDBOOK_ATTEMPT_ID}.json",
        Path(root)
        / "attempts"
        / SOURCE_RUN_ID
        / f"{V1_RECOVERY_ATTEMPT_ID}.json",
        Path(root) / "attempts" / RUN_ID / f"{RECOVERY_ATTEMPT_ID}.json",
    )
    for path in attempt_paths:
        if path.exists():
            raise RecoveryV2Error(f"handbook attempt already exists: {path}")
    targets = (
        Path(mission_dir) / REGISTRY_V2_DIRNAME,
        Path(mission_dir) / HANDBOOK_V2_DIRNAME,
        Path(mission_dir) / SERVICE_V2_DIRNAME,
        Path(mission_dir) / REGISTRY_V2_RECEIPT_NAME,
        Path(mission_dir) / FLIGHT_V2_RECEIPT_NAME,
        Path(mission_dir) / FAILURE_V2_RECEIPT_NAME,
    )
    for path in targets:
        if path.exists():
            raise RecoveryV2Error(f"V2 target already exists: {path}")


def _artifact_binding(
    manifest: Mapping[str, object], key: str, path: Path, digest: str
) -> None:
    binding = manifest.get(key)
    if (
        not isinstance(binding, Mapping)
        or Path(str(binding.get("path", ""))).resolve() != Path(path).resolve()
        or binding.get("sha256") != digest
    ):
        raise RecoveryV2Error(f"original registry {key} binding drift")


def build_registry_v2_successor(
    mission_dir: Path,
    *,
    attempts_root: Path,
    expected: SourceHashesV2,
    verify: Callable[[Path], object] = verify_bundle,
) -> dict[str, object]:
    paths = _validate_immutable_sources(
        mission_dir, attempts_root=attempts_root, expected=expected
    )
    destination = Path(mission_dir) / REGISTRY_V2_DIRNAME
    if destination.exists():
        raise RecoveryV2Error(f"V2 target already exists: {destination}")
    manifest = _read_object(paths["original_manifest"], "original registry manifest")
    _artifact_binding(
        manifest, "outputs", paths["original_outputs"], expected.original_outputs_sha256
    )
    _artifact_binding(
        manifest, "raw_trace", paths["original_trace"], expected.original_trace_sha256
    )
    _artifact_binding(
        manifest,
        "trace_manifest",
        paths["original_trace_manifest"],
        expected.original_trace_manifest_sha256,
    )
    split = manifest.get("split")
    plan = manifest.get("plan")
    if (
        manifest.get("run_id") != SOURCE_RUN_ID
        or manifest.get("status") != "COMPLETED"
        or manifest.get("scorers") != []
        or manifest.get("protocol_hash") != SOURCE_PROTOCOL_SHA256
        or not isinstance(split, dict)
        or split.get("identity_hash") != DECLARED_SPLIT_IDENTITY_SHA256
        or not isinstance(plan, dict)
        or plan.get("run_id") != SOURCE_RUN_ID
        or plan.get("attempt_id") != REGISTRY_ATTEMPT_ID
        or plan.get("split_identity_hash") != DECLARED_SPLIT_IDENTITY_SHA256
        or plan.get("protocol_hash") != SOURCE_PROTOCOL_SHA256
    ):
        raise RecoveryV2Error("original registry manifest defect surface drift")
    destination.mkdir(parents=False, exist_ok=False)
    copied = {
        "outputs": destination / paths["original_outputs"].name,
        "raw_trace": destination / paths["original_trace"].name,
        "trace_manifest": destination / paths["original_trace_manifest"].name,
    }
    for key, source_key in (
        ("outputs", "original_outputs"),
        ("raw_trace", "original_trace"),
        ("trace_manifest", "original_trace_manifest"),
    ):
        shutil.copyfile(paths[source_key], copied[key])
    for key, digest in (
        ("outputs", expected.original_outputs_sha256),
        ("raw_trace", expected.original_trace_sha256),
        ("trace_manifest", expected.original_trace_manifest_sha256),
    ):
        _require_hash(copied[key], digest, f"V2 registry {key}")
    manifest["scorers"] = list(EXPECTED_SCORERS)
    split["identity_hash"] = ACTUAL_SPLIT_IDENTITY_SHA256
    plan["split_identity_hash"] = ACTUAL_SPLIT_IDENTITY_SHA256
    manifest["protocol_hash"] = ACTUAL_PROTOCOL_SHA256
    plan["protocol_hash"] = ACTUAL_PROTOCOL_SHA256
    for key in copied:
        binding = manifest[key]
        assert isinstance(binding, dict)
        binding["path"] = str(copied[key].resolve())
    successor_manifest = destination / paths["original_manifest"].name
    v1._atomic_write_json(successor_manifest, manifest)
    _require_hash(
        successor_manifest,
        expected.successor_v2_manifest_sha256,
        "V2 registry successor manifest",
    )
    _validate_immutable_sources(
        mission_dir, attempts_root=attempts_root, expected=expected
    )
    bundle = verify(successor_manifest)
    if (
        getattr(bundle, "attempt_state", None) != "ABORTED"
        or len(getattr(bundle, "outputs_rows", ())) != source.SAMPLE_COUNT
    ):
        raise RecoveryV2Error("V2 registry successor is not a verified terminal eight")
    receipt = {
        "schema": "saea-a2t-native-structured-action-fixed8-registry-recovery-v2-v1",
        "run_id": RUN_ID,
        "cell": source.ARM_ORDER[0],
        "successor_run_id": RUN_ID,
        "verified_manifest_run_id": SOURCE_RUN_ID,
        "successor_split_identity_hash": ACTUAL_SPLIT_IDENTITY_SHA256,
        "successor_protocol_hash": ACTUAL_PROTOCOL_SHA256,
        "successor_manifest_path": str(successor_manifest.resolve()),
        "successor_manifest_sha256": expected.successor_v2_manifest_sha256,
        "recovered_from_attempt_id": REGISTRY_ATTEMPT_ID,
        "recovered_from_attempt_state": "ABORTED",
        "source_attempt": {
            "attempt_id": REGISTRY_ATTEMPT_ID,
            "state": "ABORTED",
            "path": str(paths["registry_attempt"].resolve()),
            "sha256": expected.registry_attempt_sha256,
        },
        "registry_recontacted": False,
        "registry_model_contacts": 0,
        "completed_rows": source.SAMPLE_COUNT,
        "scorers": list(EXPECTED_SCORERS),
        "original_source_artifacts": {
            "manifest_path": str(paths["original_manifest"].resolve()),
            "manifest_sha256": expected.original_manifest_sha256,
            "outputs_sha256": expected.original_outputs_sha256,
            "raw_trace_sha256": expected.original_trace_sha256,
            "trace_manifest_sha256": expected.original_trace_manifest_sha256,
        },
        "failed_v1_artifacts": {
            "manifest_path": str(paths["failed_v1_manifest"].resolve()),
            "manifest_sha256": expected.failed_v1_manifest_sha256,
            "outputs_sha256": expected.failed_v1_outputs_sha256,
            "raw_trace_sha256": expected.failed_v1_trace_sha256,
            "trace_manifest_sha256": expected.failed_v1_trace_manifest_sha256,
            "failure_receipt_path": str(paths["failed_v1_receipt"].resolve()),
            "failure_receipt_sha256": expected.failed_v1_receipt_sha256,
        },
        "source_artifacts": {
            "manifest_path": str(successor_manifest.resolve()),
            "manifest_sha256": expected.successor_v2_manifest_sha256,
            "outputs_path": str(copied["outputs"].resolve()),
            "outputs_sha256": expected.original_outputs_sha256,
            "raw_trace_path": str(copied["raw_trace"].resolve()),
            "raw_trace_sha256": expected.original_trace_sha256,
            "trace_manifest_path": str(copied["trace_manifest"].resolve()),
            "trace_manifest_sha256": expected.original_trace_manifest_sha256,
        },
        "response_meanings_opened": False,
        "gold_opened": False,
        "scorer_opened": False,
    }
    v1._atomic_write_json(Path(mission_dir) / REGISTRY_V2_RECEIPT_NAME, receipt)
    return receipt


def _with_scorer(composed: ComposedConfig) -> ComposedConfig:
    return v1.with_registered_scorer(composed)


def v2_preflight(root: Path) -> dict[str, object]:
    root = Path(root)
    preregistration = load_v2_preregistration()
    mission_dir = (root / SOURCE_MISSION_RELPATH).resolve()
    if mission_dir != (root / str(preregistration["source_mission_relpath"])).resolve():
        raise RecoveryV2Error("V2 source mission path drift")
    assert_v2_targets_absent(root, mission_dir)
    hashes = _source_hashes(preregistration)
    _validate_immutable_sources(
        mission_dir, attempts_root=root / "attempts", expected=hashes
    )
    original_check = source.assert_run_has_no_attempt_records
    source.assert_run_has_no_attempt_records = lambda _root: None
    try:
        context = source.static_preflight(root)
    finally:
        source.assert_run_has_no_attempt_records = original_check
    actual_split = split_identity_hash(
        prefixed("audio2tool", tuple(sorted(context["sample_ids"])))
    )
    request_contract = preregistration.get("frozen_request_contract")
    if (
        actual_split != ACTUAL_SPLIT_IDENTITY_SHA256
        or context["composed"].config_hash != source.COMPOSED_CONFIG_SHA256
        or not isinstance(request_contract, Mapping)
        or request_contract.get("registered_flight_plan_sha256")
        != source.REGISTERED_PLAN_SHA256
        or request_contract.get("precontact_request_contract_sha256")
        != context["precontact_plan_sha256"]
        or request_contract.get("response_format_sha256") != source.SCHEMA_SHA256
        or request_contract.get("batch_size") != source.BATCH_SIZE
        or request_contract.get("concurrency") != source.CONCURRENCY
        or request_contract.get("queue_depth") != source.QUEUE_DEPTH
        or request_contract.get("network_jitter_testing") is not False
    ):
        raise RecoveryV2Error("V2 split, schema, request, or execution geometry drift")
    context = dict(context)
    context["composed"] = _with_scorer(context["composed"])
    context["mission_dir"] = mission_dir
    context["attempts_root"] = root / "attempts"
    context["source_hashes"] = hashes
    context["source_state"] = "V1_FAILURE_PINNED"
    context["recovery_plan"] = recovery_v2_execution_plan()
    context["recovery_execution_plan_sha256"] = EXECUTION_PLAN_CANONICAL_SHA256
    return context


def run_handbook_v2(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    session_receipt: Path,
    run_dir: Path,
) -> Mapping[str, object]:
    arm = source.ARM_ORDER[1]
    saved = {
        "run_id": source.RUN_ID,
        "split_identity": source.SPLIT_IDENTITY_HASH,
        "protocol": source.PROTOCOL_SHA256,
        "execution_plan": source.execution_plan,
        "attempt_id": source.ATTEMPT_IDS[arm],
    }
    plan = context["recovery_plan"]
    source.RUN_ID = RUN_ID
    source.SPLIT_IDENTITY_HASH = ACTUAL_SPLIT_IDENTITY_SHA256
    source.PROTOCOL_SHA256 = ACTUAL_PROTOCOL_SHA256
    source.execution_plan = lambda _attempt_id: plan
    source.ATTEMPT_IDS[arm] = RECOVERY_ATTEMPT_ID
    try:
        return source._run_arm(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            arm=arm,
            plan=plan,
            run_dir=run_dir,
            session_receipt_path=session_receipt,
        )
    finally:
        source.RUN_ID = saved["run_id"]
        source.SPLIT_IDENTITY_HASH = saved["split_identity"]
        source.PROTOCOL_SHA256 = saved["protocol"]
        source.execution_plan = saved["execution_plan"]
        source.ATTEMPT_IDS[arm] = saved["attempt_id"]


def _handbook_receipt(bundle: object) -> dict[str, object]:
    manifest = getattr(bundle, "manifest", None)
    if not isinstance(manifest, Mapping):
        raise RecoveryV2Error("verified V2 handbook bundle lacks manifest metadata")
    artifacts: dict[str, object] = {}
    for key in ("outputs", "raw_trace", "trace_manifest"):
        binding = manifest.get(key)
        if not isinstance(binding, Mapping):
            raise RecoveryV2Error(f"verified V2 handbook bundle lacks {key}")
        path = Path(str(binding.get("path", "")))
        digest = binding.get("sha256")
        if not path.is_file() or not isinstance(digest, str) or _sha256(path) != digest:
            raise RecoveryV2Error(f"verified V2 handbook {key} hash drift")
        artifacts[f"{key}_path"] = str(path.resolve())
        artifacts[f"{key}_sha256"] = digest
    manifest_path = Path(getattr(bundle, "manifest_path"))
    artifacts["manifest_path"] = str(manifest_path.resolve())
    artifacts["manifest_sha256"] = _sha256(manifest_path)
    if (
        manifest.get("run_id") != RUN_ID
        or manifest.get("protocol_hash") != ACTUAL_PROTOCOL_SHA256
        or manifest.get("scorers") != list(EXPECTED_SCORERS)
    ):
        raise RecoveryV2Error("verified V2 handbook identity drift")
    return {
        "cell": source.ARM_ORDER[1],
        "run_id": RUN_ID,
        "attempt_id": RECOVERY_ATTEMPT_ID,
        "attempt_state": "OPENED",
        "split_identity_hash": ACTUAL_SPLIT_IDENTITY_SHA256,
        "protocol_hash": ACTUAL_PROTOCOL_SHA256,
        "completed_rows": source.SAMPLE_COUNT,
        "model_contacts": source.SAMPLE_COUNT,
        "source_artifacts": artifacts,
        "response_meanings_opened": False,
        "gold_opened": False,
        "scorer_opened": False,
    }


def launch_v2(root: Path) -> Mapping[str, object]:
    root = Path(root)
    context = v2_preflight(root)
    mission_dir = Path(context["mission_dir"])
    hashes = context["source_hashes"]
    assert isinstance(hashes, SourceHashesV2)
    plan = context["recovery_plan"]
    assert isinstance(plan, ExecutionPlan)
    values = context["composed"].values
    gate = FrozenCoreGate.for_study_repo(
        REPO,
        root,
        source.RUNTIME_ROOT,
        runtime_receipt_relpath=str(
            source.RUNTIME_RECEIPT_RELPATH.relative_to("docs")
        ),
        expected_model_lock_key=str(values["model_lock_key"]),
        model_root=Path(str(values["model_materialization_root"])),
    )
    gate.assert_model_touch_allowed(plan, full_hash=True)
    parsed = urlparse(str(values["base_url"]))
    if parsed.hostname not in {"127.0.0.1", "localhost"} or parsed.port is None:
        raise RecoveryV2Error("decoder endpoint must be explicit loopback")
    started = time.perf_counter()
    registry = build_registry_v2_successor(
        mission_dir,
        attempts_root=Path(context["attempts_root"]),
        expected=hashes,
    )
    service_dir = mission_dir / SERVICE_V2_DIRNAME
    service_dir.mkdir()
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = None
    try:
        session = source.start_session(
            runtime_root=source.RUNTIME_ROOT,
            data_root=root,
            runtime_receipt=context["runtime_receipt"],
            host="127.0.0.1",
            port=parsed.port,
            session_id=f"{RUN_ID}-SESSION",
            extra_argv=tuple(values["server_args"]),
            extra_env=dict(values.get("server_env", {})),
            receipt_path=session_receipt,
            ready_timeout_seconds=600.0,
            server_log_path=service_dir / "server.log",
            role="inference",
            model_root=Path(str(values["model_materialization_root"])),
        )
        transport = source.TRANSPORTS.resolve(str(values["transport"]))(
            values,
            root,
            session=session,
            runtime_receipt=context["runtime_receipt"],
            runtime_root=source.RUNTIME_ROOT,
        )
        handbook = run_handbook_v2(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            session_receipt=session_receipt,
            run_dir=mission_dir / HANDBOOK_V2_DIRNAME,
        )
        source._stop(session, context["runtime_receipt"], stop_receipt)
        session = None
        registry_bundle = verify_bundle(Path(str(registry["successor_manifest_path"])))
        if (
            registry_bundle.attempt_state != "ABORTED"
            or len(registry_bundle.outputs_rows) != source.SAMPLE_COUNT
        ):
            raise RecoveryV2Error("V2 registry successor seal drift")
        handbook_bundle = verify_bundle(Path(str(handbook["manifest"])))
        if (
            handbook_bundle.attempt_state != "OPENED"
            or len(handbook_bundle.outputs_rows) != source.SAMPLE_COUNT
        ):
            raise RecoveryV2Error("V2 handbook did not seal a complete eight")
        _validate_immutable_sources(
            mission_dir,
            attempts_root=Path(context["attempts_root"]),
            expected=hashes,
        )
        receipt = {
            "schema": "saea-a2t-native-structured-action-fixed8-recovery-v2-flight-v1",
            "run_id": RUN_ID,
            "status": "BOTH_CORRECTED_STRICT_ARMS_SEALED_UNSCORED",
            "elapsed_seconds": time.perf_counter() - started,
            "registry_recovery": registry,
            "handbook_recovery": _handbook_receipt(handbook_bundle),
            "recovery_attempt_id": RECOVERY_ATTEMPT_ID,
            "recovery_model_contacts": source.SAMPLE_COUNT,
            "registry_recontacted": False,
            "registry_recontact_count": 0,
            "response_meanings_opened": False,
            "gold_opened": False,
            "scorer_opened": False,
            "session_receipt": str(session_receipt),
            "stop_receipt": str(stop_receipt),
        }
        v1._atomic_write_json(mission_dir / FLIGHT_V2_RECEIPT_NAME, receipt)
        return receipt
    except BaseException as error:
        abort_attempt_if_opened(root, RUN_ID, RECOVERY_ATTEMPT_ID, reason=repr(error))
        v1._atomic_write_json(
            mission_dir / FAILURE_V2_RECEIPT_NAME,
            {
                "schema": "saea-a2t-native-structured-action-fixed8-recovery-v2-failure-v1",
                "run_id": RUN_ID,
                "attempt_id": RECOVERY_ATTEMPT_ID,
                "error": repr(error),
                "registry_recontacted": False,
            },
        )
        raise
    finally:
        if session is not None:
            source._stop(session, context["runtime_receipt"], stop_receipt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--data-root", type=Path)
    args = parser.parse_args(argv)
    root = args.data_root or source.data_root()
    if args.run:
        print(json.dumps(launch_v2(root), indent=2, sort_keys=True))
        return 0
    context = v2_preflight(root)
    print(
        json.dumps(
            {
                "preflight": "passed",
                "run_id": RUN_ID,
                "source_state": context["source_state"],
                "registry_calls_remaining": 0,
                "handbook_calls_remaining": source.SAMPLE_COUNT,
                "recovery_execution_plan_sha256": context[
                    "recovery_execution_plan_sha256"
                ],
                "contacts": {
                    "gold": 0,
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


if __name__ == "__main__":
    raise SystemExit(main())
