"""Contact-free tests for the fixed-eight structured-action continuation."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.config import ComposedConfig


REPO = Path(__file__).resolve().parents[2]
RECOVERY = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-native-structured-action-fixed8-v1/launcher/"
    "recover_native_structured_action_fixed8.py"
)


def _recovery():
    name = "test_a2t_native_structured_action_fixed8_recovery_module"
    spec = importlib.util.spec_from_file_location(name, RECOVERY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _source_fixture(
    tmp_path: Path, recovery: object, *, mission: Path | None = None
):
    mission = mission or (tmp_path / "flight-20260903T013000Z")
    arm_dir = mission / "registry_strict_action"
    arm_dir.mkdir(parents=True)
    run_id = recovery.RUN_ID
    trace = arm_dir / f"{run_id}.trace.jsonl"
    trace_manifest = arm_dir / f"{run_id}.trace-manifest.json"
    outputs = arm_dir / f"{run_id}.outputs.jsonl"
    manifest = arm_dir / f"{run_id}.run-manifest.json"
    trace.write_text("sealed-trace\n", encoding="ascii")
    _write_json(trace_manifest, {"records": {"sealed": "a" * 64}})
    outputs.write_text("sealed-output\n", encoding="ascii")
    _write_json(
        manifest,
        {
            "run_id": run_id,
            "status": "COMPLETED",
            "scorers": [],
            "outputs": {"path": str(outputs), "sha256": _sha256(outputs)},
            "raw_trace": {"path": str(trace), "sha256": _sha256(trace)},
            "trace_manifest": {
                "path": str(trace_manifest),
                "sha256": _sha256(trace_manifest),
            },
        },
    )
    flight_plan = mission / "flight-plan.json"
    precontact = mission / "precontact-plan.json"
    failure = mission / "failure-receipt.json"
    _write_json(flight_plan, {"run_id": run_id})
    _write_json(precontact, {"arms": list(recovery.ARM_ORDER)})
    _write_json(
        failure,
        {
            "run_id": run_id,
            "recontacted_rows": 0,
            "attempt_ids": {
                recovery.ARM_ORDER[0]: recovery.REGISTRY_ATTEMPT_ID,
                recovery.ARM_ORDER[1]: recovery.ORIGINAL_HANDBOOK_ATTEMPT_ID,
            },
        },
    )
    attempts = tmp_path / "attempts"
    attempt = attempts / run_id / f"{recovery.REGISTRY_ATTEMPT_ID}.json"
    _write_json(
        attempt,
        {
            "run_id": run_id,
            "attempt_id": recovery.REGISTRY_ATTEMPT_ID,
            "state": "ABORTED",
            "actual": {"calls": 8, "audio_seconds": 45.096},
        },
    )
    before = _sha256(manifest)
    document = json.loads(manifest.read_text(encoding="utf-8"))
    successor = mission / recovery.REGISTRY_SUCCESSOR_DIRNAME
    document["scorers"] = list(recovery.EXPECTED_SCORERS)
    for key, suffix in (
        ("outputs", ".outputs.jsonl"),
        ("raw_trace", ".trace.jsonl"),
        ("trace_manifest", ".trace-manifest.json"),
    ):
        document[key]["path"] = str(successor / f"{run_id}{suffix}")
    successor_bytes = (
        json.dumps(document, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    hashes = recovery.SourceHashes(
        registry_trace_sha256=_sha256(trace),
        registry_trace_manifest_sha256=_sha256(trace_manifest),
        registry_outputs_sha256=_sha256(outputs),
        registry_manifest_before_sha256=before,
        registry_successor_manifest_sha256=hashlib.sha256(successor_bytes).hexdigest(),
        registry_attempt_sha256=_sha256(attempt),
        flight_plan_sha256=_sha256(flight_plan),
        precontact_plan_sha256=_sha256(precontact),
        failure_receipt_sha256=_sha256(failure),
    )
    return mission, attempts, manifest, trace, hashes


def test_recovery_plan_changes_only_attempt_identity() -> None:
    recovery = _recovery()

    plan = recovery.recovery_execution_plan()

    assert plan.run_id == recovery.RUN_ID
    assert plan.attempt_id == recovery.RECOVERY_ATTEMPT_ID
    assert plan.split_role == "discovery"
    assert plan.split_identity_hash == recovery.source.SPLIT_IDENTITY_HASH
    assert plan.protocol_hash == recovery.source.PROTOCOL_SHA256
    assert plan.planned_model_calls == 16
    assert plan.planned_speech_audio_seconds == 91
    assert plan.planned_gpu_hours == 0.2


def test_recovery_composed_config_preserves_identity_and_sets_one_scorer() -> None:
    recovery = _recovery()
    original = ComposedConfig(
        values={"arm": "speech-feature-query", "scorers": []},
        config_hash="a" * 64,
        fragments={"model": "frozen"},
    )

    repaired = recovery.with_registered_scorer(original)

    assert repaired.config_hash == original.config_hash
    assert repaired.fragments == original.fragments
    assert repaired.values["scorers"] == ["a2t-toolcall"]
    assert original.values["scorers"] == []


def test_recovery_composed_config_accepts_the_real_missing_scorers_key() -> None:
    recovery = _recovery()
    original = ComposedConfig(
        values={"arm": "speech-feature-query"},
        config_hash="a" * 64,
        fragments={"model": "frozen"},
    )

    repaired = recovery.with_registered_scorer(original)

    assert repaired.values["scorers"] == ["a2t-toolcall"]
    assert "scorers" not in original.values


def test_registry_repair_is_hash_bound_and_accepts_complete_aborted_source(
    tmp_path: Path,
) -> None:
    recovery = _recovery()
    mission, attempts, manifest, _trace, hashes = _source_fixture(tmp_path, recovery)
    calls = []

    original_manifest_bytes = manifest.read_bytes()

    def verify(path: Path):
        calls.append(path)
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["scorers"] == ["a2t-toolcall"]
        return SimpleNamespace(attempt_state="ABORTED", outputs_rows=tuple(range(8)))

    result = recovery.repair_and_verify_registry(
        mission,
        attempts_root=attempts,
        expected=hashes,
        verify=verify,
    )

    successor_manifest = (
        mission
        / recovery.REGISTRY_SUCCESSOR_DIRNAME
        / f"{recovery.RUN_ID}.run-manifest.json"
    )
    assert calls == [successor_manifest]
    assert result["schema"] == (
        "saea-a2t-native-structured-action-fixed8-registry-recovery-receipt-v1"
    )
    assert result["recovered_from_attempt_state"] == "ABORTED"
    assert result["registry_recontacted"] is False
    assert result["registry_model_contacts"] == 0
    assert result["completed_rows"] == 8
    assert result["scorers"] == ["a2t-toolcall"]
    assert result["response_meanings_opened"] is False
    assert result["gold_opened"] is False
    assert result["scorer_opened"] is False
    assert result["source_artifacts"]["manifest_path"] == str(
        successor_manifest.resolve()
    )
    assert result["source_artifacts"]["manifest_sha256"] == (
        hashes.registry_successor_manifest_sha256
    )
    assert manifest.read_bytes() == original_manifest_bytes
    assert _sha256(manifest) == hashes.registry_manifest_before_sha256
    assert _sha256(successor_manifest) == hashes.registry_successor_manifest_sha256
    original_document = json.loads(manifest.read_text(encoding="utf-8"))
    successor_document = json.loads(successor_manifest.read_text(encoding="utf-8"))
    successor_document["scorers"] = []
    for key in ("outputs", "raw_trace", "trace_manifest"):
        successor_document[key]["path"] = original_document[key]["path"]
    assert successor_document == original_document
    receipt = json.loads(
        (mission / "registry-recovery-receipt.json").read_text(encoding="utf-8")
    )
    assert receipt == result


def test_registry_repair_refuses_source_drift_before_manifest_write(
    tmp_path: Path,
) -> None:
    recovery = _recovery()
    mission, attempts, manifest, trace, hashes = _source_fixture(tmp_path, recovery)
    before = manifest.read_bytes()
    trace.write_bytes(trace.read_bytes() + b"drift")

    with pytest.raises(recovery.RecoveryError, match="registry trace SHA-256 drift"):
        recovery.repair_and_verify_registry(
            mission,
            attempts_root=attempts,
            expected=hashes,
            verify=lambda _path: pytest.fail("verification must not run"),
        )

    assert manifest.read_bytes() == before
    assert not (mission / recovery.REGISTRY_SUCCESSOR_DIRNAME).exists()


def test_registry_repair_refuses_existing_successor_directory(tmp_path: Path) -> None:
    recovery = _recovery()
    mission, attempts, manifest, _trace, hashes = _source_fixture(tmp_path, recovery)
    successor = mission / recovery.REGISTRY_SUCCESSOR_DIRNAME
    successor.mkdir()
    (successor / "unexpected.txt").write_text("occupied", encoding="ascii")

    with pytest.raises(recovery.RecoveryError, match="successor directory already exists"):
        recovery.repair_and_verify_registry(
            mission,
            attempts_root=attempts,
            expected=hashes,
            verify=lambda _path: pytest.fail("verification must not run"),
        )

    assert _sha256(manifest) == hashes.registry_manifest_before_sha256


@pytest.mark.parametrize("attempt_kind", ["original", "recovery"])
def test_any_existing_handbook_attempt_refuses_continuation(
    tmp_path: Path, attempt_kind: str
) -> None:
    recovery = _recovery()
    attempts = tmp_path / "attempts"
    attempt_id = (
        recovery.ORIGINAL_HANDBOOK_ATTEMPT_ID
        if attempt_kind == "original"
        else recovery.RECOVERY_ATTEMPT_ID
    )
    path = attempts / recovery.RUN_ID / f"{attempt_id}.json"
    _write_json(path, {"state": "OPENED"})

    with pytest.raises(recovery.RecoveryError, match="handbook attempt already exists"):
        recovery.assert_handbook_attempts_absent(attempts)


def test_seal_registry_precedes_the_only_handbook_execution() -> None:
    recovery = _recovery()
    events: list[str] = []

    result = recovery.continue_arms(
        seal_registry=lambda: events.append("seal-registry") or {"arm": "registry"},
        run_handbook=lambda: events.append("run-handbook") or {"arm": "handbook"},
    )

    assert events == ["seal-registry", "run-handbook"]
    assert result == ({"arm": "registry"}, {"arm": "handbook"})


def test_source_contains_no_protected_read_or_recontact_surface() -> None:
    source_text = RECOVERY.read_text(encoding="utf-8")

    assert "run_two_arms_batched" not in source_text
    assert "load_expected_calls" not in source_text
    assert "score_item" not in source_text
    assert "evaluate_parallel" not in source_text
    assert "requests.get" not in source_text
    assert "requests.post" not in source_text
    assert "retry" not in source_text.lower()
    assert "REGISTRY_STRICT_ACTION" not in source_text.split("_run_arm(", 1)[-1]


def test_preflight_only_never_repairs_or_contacts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    recovery = _recovery()
    sentinel = {
        "source_state": "ORIGINAL_UNREPAIRED",
        "recovery_execution_plan_sha256": "a" * 64,
    }
    monkeypatch.setattr(recovery, "recovery_preflight", lambda root: sentinel)
    monkeypatch.setattr(
        recovery,
        "launch_recovery",
        lambda _root: pytest.fail("contact path entered"),
    )

    assert recovery.main(["--preflight-only", "--data-root", str(Path("/data"))]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["contacts"] == {
        "gold": 0,
        "model": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert output["handbook_calls_remaining"] == 8
    assert output["registry_calls_remaining"] == 0


def test_recovery_preregistration_is_exact_and_zero_contact() -> None:
    recovery = _recovery()
    prereg = recovery.load_recovery_preregistration()

    assert prereg["run_id"] == recovery.RUN_ID
    assert prereg["source_flight_id"] == "flight-20260903T013000Z"
    assert prereg["source_registry_attempt_state"] == "ABORTED"
    assert prereg["source_registry_actual_calls"] == 8
    assert prereg["remaining_contact_arm"] == "HANDBOOK_STRICT_ACTION"
    assert prereg["remaining_model_calls"] == 8
    assert prereg["registry_recontact_authorized"] is False
    assert prereg["contacts_at_registration"] == {
        "gold": 0,
        "model": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert prereg["manifest_scorers"] == ["a2t-toolcall"]
    assert prereg["execution_protocol"] == {
        "batch_size": 2,
        "concurrency": 2,
        "queue_depth": 4,
        "repair_contacts": 0,
        "resends": 0,
        "retries": 0,
        "network_jitter_testing": False,
    }
    assert prereg["recovery_execution_plan"] == asdict(
        recovery.recovery_execution_plan()
    )


def test_recovery_preflight_rebuilds_the_frozen_request_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recovery = _recovery()
    root = tmp_path / "data"
    mission = root / recovery.SOURCE_MISSION_RELPATH
    _mission, attempts, _manifest, _trace, hashes = _source_fixture(
        tmp_path, recovery, mission=mission
    )
    attempts.rename(root / "attempts")
    attempts = root / "attempts"
    expected_precontact = "d" * 64
    prereg = {
        "source_mission_relpath": recovery.SOURCE_MISSION_RELPATH.as_posix(),
        "source_hashes": asdict(hashes),
        "frozen_contracts": {
            "registered_flight_plan_sha256": recovery.source.REGISTERED_PLAN_SHA256,
            "precontact_request_contract_sha256": expected_precontact,
            "protocol_sha256": recovery.source.PROTOCOL_SHA256,
            "response_format_sha256": recovery.source.SCHEMA_SHA256,
            "split_identity_sha256": recovery.source.SPLIT_IDENTITY_HASH,
        },
    }
    composed = ComposedConfig(
        values={"arm": "speech-feature-query", "scorers": []},
        config_hash="c" * 64,
        fragments={"model": "frozen"},
    )
    original_attempt_check = recovery.source.assert_run_has_no_attempt_records

    def static_preflight(received_root: Path):
        assert received_root == root
        recovery.source.assert_run_has_no_attempt_records(received_root)
        return {
            "composed": composed,
            "precontact_plan_sha256": expected_precontact,
        }

    monkeypatch.setattr(recovery, "load_recovery_preregistration", lambda: prereg)
    monkeypatch.setattr(recovery.source, "static_preflight", static_preflight)

    context = recovery.recovery_preflight(root)

    assert context["mission_dir"] == mission.resolve()
    assert context["attempts_root"] == attempts
    assert context["source_state"] == "IMMUTABLE_ORIGINAL"
    assert context["composed"].values["scorers"] == ["a2t-toolcall"]
    assert context["recovery_plan"] == recovery.recovery_execution_plan()
    assert recovery.source.assert_run_has_no_attempt_records is original_attempt_check


def test_handbook_runner_temporarily_uses_only_the_recovery_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recovery = _recovery()
    observed: dict[str, object] = {}

    def run_arm(**kwargs: object):
        arm = recovery.ARM_ORDER[1]
        observed.update(kwargs)
        assert recovery.source.ATTEMPT_IDS[arm] == recovery.RECOVERY_ATTEMPT_ID
        return {"manifest": "sealed"}

    monkeypatch.setattr(recovery.source, "_run_arm", run_arm)
    original = recovery.ORIGINAL_HANDBOOK_ATTEMPT_ID

    result = recovery._run_handbook_only(
        root=tmp_path,
        context={"recovery_plan": recovery.recovery_execution_plan()},
        gate=object(),
        transport=object(),
        session_receipt=tmp_path / "session.json",
        run_dir=tmp_path / "handbook",
    )

    assert result == {"manifest": "sealed"}
    assert observed["arm"] == recovery.ARM_ORDER[1]
    assert recovery.source.ATTEMPT_IDS[recovery.ARM_ORDER[1]] == original


def test_launch_recovery_seals_both_arms_and_emits_asymmetric_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    recovery = _recovery()
    root = tmp_path / "data"
    mission = root / recovery.SOURCE_MISSION_RELPATH
    mission.mkdir(parents=True)
    attempts = root / "attempts"
    values = {
        "model_lock_key": "model",
        "model_materialization_root": "/model",
        "base_url": "http://127.0.0.1:9999",
        "server_args": [],
        "server_env": {},
        "transport": "fake",
    }
    context = {
        "mission_dir": mission,
        "attempts_root": attempts,
        "source_hashes": recovery.SourceHashes(*("a" * 64 for _ in range(9))),
        "recovery_plan": recovery.recovery_execution_plan(),
        "composed": ComposedConfig(values=values, config_hash="b" * 64, fragments={}),
        "runtime_receipt": object(),
    }
    registry = {
        "schema": (
            "saea-a2t-native-structured-action-fixed8-"
            "registry-recovery-receipt-v1"
        ),
        "cell": recovery.ARM_ORDER[0],
        "recovered_from_attempt_state": "ABORTED",
    }
    artifact_paths = {}
    for name in ("outputs", "raw_trace", "trace_manifest"):
        path = tmp_path / f"{name}.json"
        path.write_text(name, encoding="ascii")
        artifact_paths[name] = path
    manifest_path = tmp_path / "handbook.run-manifest.json"
    manifest_document = {
        "scorers": ["a2t-toolcall"],
        "outputs": {
            "path": str(artifact_paths["outputs"]),
            "sha256": _sha256(artifact_paths["outputs"]),
        },
        "raw_trace": {
            "path": str(artifact_paths["raw_trace"]),
            "sha256": _sha256(artifact_paths["raw_trace"]),
        },
        "trace_manifest": {
            "path": str(artifact_paths["trace_manifest"]),
            "sha256": _sha256(artifact_paths["trace_manifest"]),
        },
    }
    _write_json(manifest_path, manifest_document)
    bundle = SimpleNamespace(
        attempt_state="OPENED",
        outputs_rows=tuple(range(8)),
        manifest=manifest_document,
        manifest_path=manifest_path,
    )
    events: list[str] = []

    class Gate:
        def assert_model_touch_allowed(self, plan: object, *, full_hash: bool):
            assert plan == context["recovery_plan"]
            assert full_hash is True
            events.append("gate")

    gate_factory = SimpleNamespace(for_study_repo=lambda *_args, **_kwargs: Gate())
    transports = SimpleNamespace(
        resolve=lambda name: (
            lambda *_args, **_kwargs: SimpleNamespace(name=name)
        )
    )
    monkeypatch.setattr(recovery, "recovery_preflight", lambda _root: context)
    monkeypatch.setattr(recovery, "FrozenCoreGate", gate_factory)
    monkeypatch.setattr(recovery.source, "TRANSPORTS", transports)
    monkeypatch.setattr(
        recovery.source,
        "start_session",
        lambda **_kwargs: events.append("start") or object(),
    )
    monkeypatch.setattr(
        recovery.source,
        "_stop",
        lambda *_args: events.append("stop"),
    )
    monkeypatch.setattr(
        recovery,
        "repair_and_verify_registry",
        lambda *_args, **_kwargs: events.append("seal-registry") or registry,
    )
    monkeypatch.setattr(
        recovery,
        "_run_handbook_only",
        lambda **_kwargs: events.append("run-handbook")
        or {"manifest": str(manifest_path)},
    )
    monkeypatch.setattr(recovery, "verify_bundle", lambda _path: bundle)

    receipt = recovery.launch_recovery(root)

    assert events == [
        "gate",
        "seal-registry",
        "start",
        "run-handbook",
        "stop",
        "seal-registry",
    ]
    assert receipt["status"] == "BOTH_STRICT_ARMS_SEALED_UNSCORED"
    assert receipt["registry_recovery"] == registry
    assert receipt["handbook_recovery"]["attempt_state"] == "OPENED"
    assert receipt["registry_recontact_count"] == 0
    assert receipt["response_meanings_opened"] is False
    assert receipt["gold_opened"] is False
    assert receipt["scorer_opened"] is False
    persisted = json.loads(
        (mission / "recovery-flight-receipt.json").read_text(encoding="utf-8")
    )
    assert persisted["registry_recovery"] == registry
