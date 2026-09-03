#!/usr/bin/env python3
"""Continue the fixed-eight flight through its untouched handbook arm only.

The contact-free preflight pins the already-complete registry artifacts and
the terminal registry attempt without interpreting response content.  The run
path changes only the registry manifest's missing scorer metadata, verifies
that externally sealed eight-row source, and then executes the eight handbook
contacts under a fresh exact attempt.  It never dispatches the registry arm.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Callable, Mapping, Sequence
from urllib.parse import urlparse


REPO = Path(__file__).resolve().parents[5]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

_SOURCE_PATH = Path(__file__).with_name("launch_native_structured_action_fixed8.py")
_SPEC = importlib.util.spec_from_file_location("_saea_native_structured_source", _SOURCE_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError("cannot load the frozen structured-action launcher")
source = importlib.util.module_from_spec(_SPEC)
sys.modules.setdefault(_SPEC.name, source)
_SPEC.loader.exec_module(source)

from speech_aware_evidence_acquisition.contracts import (  # noqa: E402
    ExecutionPlan,
    FrozenCoreGate,
)
from speech_aware_evidence_acquisition.core.bundle import (  # noqa: E402
    abort_attempt_if_opened,
    verify_bundle,
)
from speech_aware_evidence_acquisition.core.config import ComposedConfig  # noqa: E402


RUN_ID = source.RUN_ID
ARM_ORDER = source.ARM_ORDER
REGISTRY_ATTEMPT_ID = source.ATTEMPT_IDS[source.ARM_ORDER[0]]
ORIGINAL_HANDBOOK_ATTEMPT_ID = source.ATTEMPT_IDS[source.ARM_ORDER[1]]
RECOVERY_ATTEMPT_ID = "attempt-20260903T013000Z-handbook-strict-recovery-v1"
EXPECTED_SCORERS = ("a2t-toolcall",)
SOURCE_FLIGHT_ID = "flight-20260903T013000Z"
SOURCE_MISSION_RELPATH = Path("runs") / RUN_ID / SOURCE_FLIGHT_ID
RECOVERY_RUN_DIRNAME = "handbook_strict_action_recovery_v1"
PREREGISTRATION_PATH = Path(__file__).with_name("recovery-preregistration.json")
PREREGISTRATION_SHA256 = (
    "bf0658c13b8cdfa07fd372951cf662eea3ffc044b0f6dcd9e32924f778d816d1"
)
EXECUTION_PLAN_PATH = Path(__file__).with_name("recovery-execution-plan.json")
EXECUTION_PLAN_FILE_SHA256 = (
    "3aa2da2e71f78a507a6f443cd8d4ac3269b7e106ffd908401f0cfdba961d6763"
)
EXECUTION_PLAN_CANONICAL_SHA256 = (
    "a5fdb9d15e33b84949b7e267acd373675bb05d5a1d032c6b102acd5ca6baa46b"
)
REGISTRY_SUCCESSOR_DIRNAME = "registry_strict_action_recovery_v1"


class RecoveryError(RuntimeError):
    """The frozen source or exact continuation contract failed closed."""


@dataclass(frozen=True)
class SourceHashes:
    registry_trace_sha256: str
    registry_trace_manifest_sha256: str
    registry_outputs_sha256: str
    registry_manifest_before_sha256: str
    registry_successor_manifest_sha256: str
    registry_attempt_sha256: str
    flight_plan_sha256: str
    precontact_plan_sha256: str
    failure_receipt_sha256: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _canonical_sha256(document: object) -> str:
    raw = json.dumps(
        document, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _read_object(path: Path, label: str) -> dict[str, object]:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RecoveryError(f"{label} is not a readable UTF-8 JSON object: {error}") from error
    if not isinstance(document, dict):
        raise RecoveryError(f"{label} must be a JSON object")
    return document


def _atomic_write_json(path: Path, document: Mapping[str, object]) -> None:
    raw = (
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    )
    temporary = path.with_name(f".{path.name}.recovery-{os.getpid()}")
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _require_hash(path: Path, expected: str, label: str) -> None:
    if not Path(path).is_file() or _sha256(path) != expected:
        raise RecoveryError(f"{label} SHA-256 drift")


def recovery_execution_plan() -> ExecutionPlan:
    """Return the exact successor plan; cumulative ceilings remain unchanged."""

    return ExecutionPlan(
        run_id=RUN_ID,
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="audio2tool",
        split_role="discovery",
        split_identity_hash=source.SPLIT_IDENTITY_HASH,
        planned_model_calls=source.MAX_MODEL_CONTACTS,
        planned_gpu_hours=0.2,
        planned_speech_audio_seconds=source.PLANNED_AUDIO_SECONDS,
        protocol_hash=source.PROTOCOL_SHA256,
        attempt_id=RECOVERY_ATTEMPT_ID,
    ).validate()


def load_recovery_preregistration() -> dict[str, object]:
    _require_hash(
        PREREGISTRATION_PATH,
        PREREGISTRATION_SHA256,
        "recovery preregistration",
    )
    _require_hash(
        EXECUTION_PLAN_PATH,
        EXECUTION_PLAN_FILE_SHA256,
        "recovery execution plan file",
    )
    preregistration = _read_object(PREREGISTRATION_PATH, "recovery preregistration")
    plan_document = _read_object(EXECUTION_PLAN_PATH, "recovery execution plan")
    plan = recovery_execution_plan()
    if (
        preregistration.get("schema")
        != "saea-a2t-native-structured-action-fixed8-recovery-preregistration-v1"
        or preregistration.get("run_id") != RUN_ID
        or preregistration.get("source_flight_id") != SOURCE_FLIGHT_ID
        or preregistration.get("source_mission_relpath")
        != SOURCE_MISSION_RELPATH.as_posix()
        or preregistration.get("source_registry_attempt_id") != REGISTRY_ATTEMPT_ID
        or preregistration.get("source_registry_attempt_state") != "ABORTED"
        or preregistration.get("source_registry_actual_calls") != 8
        or preregistration.get("original_handbook_attempt_id")
        != ORIGINAL_HANDBOOK_ATTEMPT_ID
        or preregistration.get("remaining_contact_arm") != ARM_ORDER[1]
        or preregistration.get("remaining_model_calls") != 8
        or preregistration.get("registry_recontact_authorized") is not False
        or preregistration.get("manifest_scorers") != list(EXPECTED_SCORERS)
        or preregistration.get("recovery_execution_plan") != asdict(plan)
        or preregistration.get("recovery_execution_plan_sha256")
        != EXECUTION_PLAN_CANONICAL_SHA256
        or plan_document != asdict(plan)
        or _canonical_sha256(plan_document) != EXECUTION_PLAN_CANONICAL_SHA256
    ):
        raise RecoveryError("recovery preregistration identity drift")
    protocol = preregistration.get("execution_protocol")
    if protocol != {
        "batch_size": 2,
        "concurrency": 2,
        "network_jitter_testing": False,
        "queue_depth": 4,
        "repair_contacts": 0,
        "resends": 0,
        "retries": 0,
    }:
        raise RecoveryError("recovery execution geometry drift")
    return preregistration


def with_registered_scorer(composed: ComposedConfig) -> ComposedConfig:
    """Change manifest metadata only, retaining the frozen config identity."""

    values = dict(composed.values)
    if "scorers" in values and values["scorers"] != []:
        raise RecoveryError(
            "source composed config no longer has the observed missing or empty "
            "scorer declaration"
        )
    values["scorers"] = list(EXPECTED_SCORERS)
    return ComposedConfig(
        values=values,
        config_hash=composed.config_hash,
        fragments=dict(composed.fragments),
    )


def _source_paths(mission_dir: Path) -> dict[str, Path]:
    arm_dir = Path(mission_dir) / "registry_strict_action"
    return {
        "trace": arm_dir / f"{RUN_ID}.trace.jsonl",
        "trace_manifest": arm_dir / f"{RUN_ID}.trace-manifest.json",
        "outputs": arm_dir / f"{RUN_ID}.outputs.jsonl",
        "manifest": arm_dir / f"{RUN_ID}.run-manifest.json",
        "flight_plan": Path(mission_dir) / "flight-plan.json",
        "precontact_plan": Path(mission_dir) / "precontact-plan.json",
        "failure": Path(mission_dir) / "failure-receipt.json",
    }


def assert_handbook_attempts_absent(attempts_root: Path) -> None:
    run_root = Path(attempts_root) / RUN_ID
    for attempt_id in (ORIGINAL_HANDBOOK_ATTEMPT_ID, RECOVERY_ATTEMPT_ID):
        path = run_root / f"{attempt_id}.json"
        if path.exists():
            raise RecoveryError(f"handbook attempt already exists: {path}")


def _validate_source_bytes(
    mission_dir: Path,
    *,
    attempts_root: Path,
    expected: SourceHashes,
) -> tuple[dict[str, Path], str]:
    paths = _source_paths(mission_dir)
    for key, digest, label in (
        ("trace", expected.registry_trace_sha256, "registry trace"),
        (
            "trace_manifest",
            expected.registry_trace_manifest_sha256,
            "registry trace manifest",
        ),
        ("outputs", expected.registry_outputs_sha256, "registry outputs"),
        ("flight_plan", expected.flight_plan_sha256, "source flight plan"),
        ("precontact_plan", expected.precontact_plan_sha256, "source precontact plan"),
        ("failure", expected.failure_receipt_sha256, "source failure receipt"),
    ):
        _require_hash(paths[key], digest, label)
    _require_hash(
        paths["manifest"],
        expected.registry_manifest_before_sha256,
        "registry manifest",
    )
    attempt_path = (
        Path(attempts_root) / RUN_ID / f"{REGISTRY_ATTEMPT_ID}.json"
    )
    _require_hash(attempt_path, expected.registry_attempt_sha256, "registry attempt")
    attempt = _read_object(attempt_path, "registry attempt")
    actual = attempt.get("actual")
    if (
        attempt.get("run_id") != RUN_ID
        or attempt.get("attempt_id") != REGISTRY_ATTEMPT_ID
        or attempt.get("state") != "ABORTED"
        or not isinstance(actual, Mapping)
        or actual.get("calls") != 8
        or abs(float(actual.get("audio_seconds", -1)) - 45.096) > 1e-9
    ):
        raise RecoveryError("registry attempt is not the exact eight-contact terminal source")
    failure = _read_object(paths["failure"], "source failure receipt")
    attempt_ids = failure.get("attempt_ids")
    if (
        failure.get("run_id") != RUN_ID
        or failure.get("recontacted_rows") != 0
        or not isinstance(attempt_ids, Mapping)
        or attempt_ids.get(ARM_ORDER[0]) != REGISTRY_ATTEMPT_ID
        or attempt_ids.get(ARM_ORDER[1]) != ORIGINAL_HANDBOOK_ATTEMPT_ID
    ):
        raise RecoveryError("source failure receipt identity drift")
    return paths, "IMMUTABLE_ORIGINAL"


def _artifact_reference(
    manifest: Mapping[str, object], key: str, path: Path, digest: str
) -> None:
    reference = manifest.get(key)
    if (
        not isinstance(reference, Mapping)
        or Path(str(reference.get("path", ""))).resolve() != Path(path).resolve()
        or reference.get("sha256") != digest
    ):
        raise RecoveryError(f"registry manifest {key} binding drift")


def _write_registry_receipt(mission_dir: Path, document: Mapping[str, object]) -> None:
    path = Path(mission_dir) / "registry-recovery-receipt.json"
    if path.exists():
        raise RecoveryError(f"registry recovery receipt already exists: {path}")
    _atomic_write_json(path, document)


def repair_and_verify_registry(
    mission_dir: Path,
    *,
    attempts_root: Path,
    expected: SourceHashes,
    verify: Callable[[Path], object] = verify_bundle,
) -> dict[str, object]:
    """Repair one metadata list and mechanically verify the sealed source."""

    paths, _state = _validate_source_bytes(
        mission_dir, attempts_root=attempts_root, expected=expected
    )
    manifest = _read_object(paths["manifest"], "registry manifest")
    _artifact_reference(manifest, "outputs", paths["outputs"], expected.registry_outputs_sha256)
    _artifact_reference(manifest, "raw_trace", paths["trace"], expected.registry_trace_sha256)
    _artifact_reference(
        manifest,
        "trace_manifest",
        paths["trace_manifest"],
        expected.registry_trace_manifest_sha256,
    )
    if manifest.get("run_id") != RUN_ID or manifest.get("status") != "COMPLETED":
        raise RecoveryError("registry manifest is not the completed fixed source")
    if manifest.get("scorers") != []:
        raise RecoveryError("registry manifest observed defect changed")

    successor_dir = Path(mission_dir) / REGISTRY_SUCCESSOR_DIRNAME
    if successor_dir.exists():
        raise RecoveryError(f"registry successor directory already exists: {successor_dir}")
    successor_dir.mkdir(parents=False, exist_ok=False)
    successor_paths: dict[str, Path] = {}
    for key in ("outputs", "trace", "trace_manifest"):
        destination = successor_dir / paths[key].name
        shutil.copyfile(paths[key], destination)
        successor_paths[key] = destination
    for key, digest, label in (
        ("outputs", expected.registry_outputs_sha256, "successor registry outputs"),
        ("trace", expected.registry_trace_sha256, "successor registry trace"),
        (
            "trace_manifest",
            expected.registry_trace_manifest_sha256,
            "successor registry trace manifest",
        ),
    ):
        _require_hash(successor_paths[key], digest, label)
    manifest["scorers"] = list(EXPECTED_SCORERS)
    for key, successor_key in (
        ("outputs", "outputs"),
        ("raw_trace", "trace"),
        ("trace_manifest", "trace_manifest"),
    ):
        reference = manifest[key]
        assert isinstance(reference, dict)
        reference["path"] = str(successor_paths[successor_key].resolve())
    successor_manifest = successor_dir / paths["manifest"].name
    _atomic_write_json(successor_manifest, manifest)
    _require_hash(
        successor_manifest,
        expected.registry_successor_manifest_sha256,
        "successor registry manifest",
    )
    _require_hash(
        paths["manifest"],
        expected.registry_manifest_before_sha256,
        "immutable source registry manifest",
    )
    bundle = verify(successor_manifest)
    attempt_state = getattr(bundle, "attempt_state", None)
    outputs_rows = getattr(bundle, "outputs_rows", ())
    if attempt_state != "ABORTED" or len(outputs_rows) != source.SAMPLE_COUNT:
        raise RecoveryError("registry source is not a verified complete terminal eight")
    result = {
        "schema": (
            "saea-a2t-native-structured-action-fixed8-"
            "registry-recovery-receipt-v1"
        ),
        "run_id": RUN_ID,
        "cell": ARM_ORDER[0],
        "status": "EXTERNALLY_SEALED_SOURCE",
        "recovered_from_attempt_id": REGISTRY_ATTEMPT_ID,
        "recovered_from_attempt_state": "ABORTED",
        "registry_recontacted": False,
        "registry_model_contacts": 0,
        "completed_rows": source.SAMPLE_COUNT,
        "scorers": list(EXPECTED_SCORERS),
        "successor_manifest_path": str(successor_manifest.resolve()),
        "successor_manifest_sha256": expected.registry_successor_manifest_sha256,
        "source_attempt": {
            "attempt_id": REGISTRY_ATTEMPT_ID,
            "state": "ABORTED",
            "sha256": expected.registry_attempt_sha256,
        },
        "original_source_artifacts": {
            "manifest_path": str(paths["manifest"].resolve()),
            "manifest_sha256": expected.registry_manifest_before_sha256,
            "outputs_sha256": expected.registry_outputs_sha256,
            "raw_trace_sha256": expected.registry_trace_sha256,
            "trace_manifest_sha256": expected.registry_trace_manifest_sha256,
        },
        "source_artifacts": {
            "manifest_path": str(successor_manifest.resolve()),
            "manifest_sha256": expected.registry_successor_manifest_sha256,
            "outputs_path": str(successor_paths["outputs"].resolve()),
            "outputs_sha256": expected.registry_outputs_sha256,
            "raw_trace_path": str(successor_paths["trace"].resolve()),
            "raw_trace_sha256": expected.registry_trace_sha256,
            "trace_manifest_path": str(successor_paths["trace_manifest"].resolve()),
            "trace_manifest_sha256": expected.registry_trace_manifest_sha256,
        },
        "contacts": {
            "gold": 0,
            "model": 0,
            "network": 0,
            "scorer": 0,
            "tokenizer": 0,
        },
        "response_meanings_opened": False,
        "gold_opened": False,
        "scorer_opened": False,
    }
    _write_registry_receipt(mission_dir, result)
    return result


def continue_arms(
    *,
    seal_registry: Callable[[], Mapping[str, object]],
    run_handbook: Callable[[], Mapping[str, object]],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    registry = seal_registry()
    handbook = run_handbook()
    return registry, handbook


def _source_hashes(preregistration: Mapping[str, object]) -> SourceHashes:
    raw = preregistration.get("source_hashes")
    if not isinstance(raw, Mapping):
        raise RecoveryError("recovery preregistration lacks source hashes")
    try:
        return SourceHashes(**raw)
    except TypeError as error:
        raise RecoveryError(f"recovery source hashes are malformed: {error}") from error


def recovery_preflight(root: Path) -> dict[str, object]:
    root = Path(root)
    preregistration = load_recovery_preregistration()
    mission_dir = (root / SOURCE_MISSION_RELPATH).resolve()
    if mission_dir != (root / str(preregistration["source_mission_relpath"])).resolve():
        raise RecoveryError("source mission path drift")
    attempts_root = root / "attempts"
    assert_handbook_attempts_absent(attempts_root)
    hashes = _source_hashes(preregistration)
    _paths, source_state = _validate_source_bytes(
        mission_dir, attempts_root=attempts_root, expected=hashes
    )

    original_check = source.assert_run_has_no_attempt_records
    source.assert_run_has_no_attempt_records = lambda _root: None
    try:
        context = source.static_preflight(root)
    finally:
        source.assert_run_has_no_attempt_records = original_check
    frozen = preregistration.get("frozen_contracts")
    if (
        not isinstance(frozen, Mapping)
        or frozen.get("registered_flight_plan_sha256") != source.REGISTERED_PLAN_SHA256
        or frozen.get("precontact_request_contract_sha256")
        != context["precontact_plan_sha256"]
        or frozen.get("protocol_sha256") != source.PROTOCOL_SHA256
        or frozen.get("response_format_sha256") != source.SCHEMA_SHA256
        or frozen.get("split_identity_sha256") != source.SPLIT_IDENTITY_HASH
    ):
        raise RecoveryError("frozen request, split, schema, or protocol binding drift")
    context = dict(context)
    context["composed"] = with_registered_scorer(context["composed"])
    context["mission_dir"] = mission_dir
    context["attempts_root"] = attempts_root
    context["source_hashes"] = hashes
    context["source_state"] = source_state
    context["recovery_plan"] = recovery_execution_plan()
    context["recovery_execution_plan_sha256"] = EXECUTION_PLAN_CANONICAL_SHA256
    return context


def _run_handbook_only(
    *,
    root: Path,
    context: Mapping[str, object],
    gate: FrozenCoreGate,
    transport: object,
    session_receipt: Path,
    run_dir: Path,
) -> Mapping[str, object]:
    arm = ARM_ORDER[1]
    original_attempt_id = source.ATTEMPT_IDS[arm]
    source.ATTEMPT_IDS[arm] = RECOVERY_ATTEMPT_ID
    try:
        return source._run_arm(
            root=root,
            context=context,
            gate=gate,
            transport=transport,
            arm=arm,
            plan=context["recovery_plan"],
            run_dir=run_dir,
            session_receipt_path=session_receipt,
        )
    finally:
        source.ATTEMPT_IDS[arm] = original_attempt_id


def _handbook_receipt(bundle: object) -> dict[str, object]:
    manifest = getattr(bundle, "manifest", None)
    if not isinstance(manifest, Mapping):
        raise RecoveryError("verified handbook bundle lacks manifest metadata")
    artifacts: dict[str, object] = {}
    for key, prefix in (
        ("outputs", "outputs"),
        ("raw_trace", "raw_trace"),
        ("trace_manifest", "trace_manifest"),
    ):
        reference = manifest.get(key)
        if not isinstance(reference, Mapping):
            raise RecoveryError(f"verified handbook bundle lacks {key}")
        path = Path(str(reference.get("path", "")))
        digest = reference.get("sha256")
        if not path.is_file() or not isinstance(digest, str) or _sha256(path) != digest:
            raise RecoveryError(f"verified handbook {key} hash drift")
        artifacts[f"{prefix}_path"] = str(path.resolve())
        artifacts[f"{prefix}_sha256"] = digest
    manifest_path = Path(getattr(bundle, "manifest_path"))
    artifacts["manifest_path"] = str(manifest_path.resolve())
    artifacts["manifest_sha256"] = _sha256(manifest_path)
    if manifest.get("scorers") != list(EXPECTED_SCORERS):
        raise RecoveryError("verified handbook scorer list drift")
    return {
        "cell": ARM_ORDER[1],
        "attempt_id": RECOVERY_ATTEMPT_ID,
        "attempt_state": "OPENED",
        "completed_rows": source.SAMPLE_COUNT,
        "model_contacts": source.SAMPLE_COUNT,
        "source_artifacts": artifacts,
        "response_meanings_opened": False,
        "gold_opened": False,
        "scorer_opened": False,
    }


def launch_recovery(root: Path) -> Mapping[str, object]:
    root = Path(root)
    context = recovery_preflight(root)
    mission_dir = Path(context["mission_dir"])
    attempts_root = Path(context["attempts_root"])
    hashes = context["source_hashes"]
    assert isinstance(hashes, SourceHashes)
    plan = context["recovery_plan"]
    assert isinstance(plan, ExecutionPlan)
    run_dir = mission_dir / RECOVERY_RUN_DIRNAME
    if run_dir.exists():
        raise RecoveryError(f"handbook recovery directory already exists: {run_dir}")

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
        raise RecoveryError("decoder endpoint must be explicit loopback")

    service_dir = mission_dir / "recovery-service-v1"
    if service_dir.exists():
        raise RecoveryError(f"recovery service directory already exists: {service_dir}")
    service_dir.mkdir()
    session_receipt = service_dir / "session-receipt.json"
    stop_receipt = service_dir / "stop-receipt.json"
    session = None
    started = time.perf_counter()
    registry: Mapping[str, object] | None = None
    try:
        registry = repair_and_verify_registry(
            mission_dir,
            attempts_root=attempts_root,
            expected=hashes,
        )
        session = source.start_session(
            runtime_root=source.RUNTIME_ROOT,
            data_root=root,
            runtime_receipt=context["runtime_receipt"],
            host="127.0.0.1",
            port=parsed.port,
            session_id=f"{RUN_ID}-HANDBOOK-RECOVERY-V1",
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
        registry, handbook = continue_arms(
            seal_registry=lambda: registry,
            run_handbook=lambda: _run_handbook_only(
                root=root,
                context=context,
                gate=gate,
                transport=transport,
                session_receipt=session_receipt,
                run_dir=run_dir,
            ),
        )
        source._stop(session, context["runtime_receipt"], stop_receipt)
        session = None
        registry = repair_and_verify_registry(
            mission_dir,
            attempts_root=attempts_root,
            expected=hashes,
        )
        handbook_bundle = verify_bundle(Path(str(handbook["manifest"])))
        if (
            handbook_bundle.attempt_state != "OPENED"
            or len(handbook_bundle.outputs_rows) != source.SAMPLE_COUNT
        ):
            raise RecoveryError("handbook continuation did not seal a complete eight")
        handbook_recovery = _handbook_receipt(handbook_bundle)
        receipt = {
            "schema": "saea-a2t-native-structured-action-fixed8-recovery-flight-v1",
            "run_id": RUN_ID,
            "status": "BOTH_STRICT_ARMS_SEALED_UNSCORED",
            "elapsed_seconds": time.perf_counter() - started,
            "registry_recovery": dict(registry),
            "handbook_recovery": handbook_recovery,
            "recovery_attempt_id": RECOVERY_ATTEMPT_ID,
            "recovery_model_contacts": source.SAMPLE_COUNT,
            "cumulative_model_contacts": source.MAX_MODEL_CONTACTS,
            "registry_recontacted": False,
            "registry_recontact_count": 0,
            "scorers": list(EXPECTED_SCORERS),
            "response_meanings_opened": False,
            "gold_opened": False,
            "scorer_opened": False,
            "session_receipt": str(session_receipt),
            "stop_receipt": str(stop_receipt),
        }
        source._write_json(mission_dir / "recovery-flight-receipt.json", receipt)
        return receipt
    except BaseException as error:
        abort_attempt_if_opened(root, RUN_ID, RECOVERY_ATTEMPT_ID, reason=repr(error))
        source._write_json(
            mission_dir / "recovery-failure-receipt.json",
            {
                "schema": "saea-a2t-native-structured-action-fixed8-recovery-failure-v1",
                "run_id": RUN_ID,
                "recovery_attempt_id": RECOVERY_ATTEMPT_ID,
                "error": repr(error),
                "registry_recontacted_rows": 0,
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
        print(json.dumps(launch_recovery(root), indent=2, sort_keys=True))
        return 0
    context = recovery_preflight(root)
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
