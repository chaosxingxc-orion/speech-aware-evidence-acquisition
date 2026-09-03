"""Contact-free tests for the corrected fixed-eight V2 continuation."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.data.splits import prefixed, split_identity_hash


REPO = Path(__file__).resolve().parents[2]
V2_LAUNCHER = REPO / (
    "docs/checks/speech-aware-evidence-acquisition/"
    "2026-09-03-a2t-native-structured-action-fixed8-v1/launcher/"
    "recover_native_structured_action_fixed8_v2.py"
)


def _v2():
    name = "test_a2t_native_structured_action_fixed8_recovery_v2_module"
    spec = importlib.util.spec_from_file_location(name, V2_LAUNCHER)
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


def _source_fixture(tmp_path: Path, v2: object, *, mission: Path | None = None):
    mission = mission or (tmp_path / "flight-20260903T013000Z")
    original = mission / "registry_strict_action"
    failed_v1 = mission / "registry_strict_action_recovery_v1"
    original.mkdir(parents=True)
    failed_v1.mkdir(parents=True)
    run_id = v2.SOURCE_RUN_ID
    original_paths = {
        "outputs": original / f"{run_id}.outputs.jsonl",
        "trace": original / f"{run_id}.trace.jsonl",
        "trace_manifest": original / f"{run_id}.trace-manifest.json",
        "manifest": original / f"{run_id}.run-manifest.json",
    }
    original_paths["outputs"].write_text("sealed-output\n", encoding="ascii")
    original_paths["trace"].write_text("sealed-trace\n", encoding="ascii")
    _write_json(original_paths["trace_manifest"], {"records": {"x": "a" * 64}})
    manifest = {
        "run_id": run_id,
        "status": "COMPLETED",
        "protocol_hash": v2.SOURCE_PROTOCOL_SHA256,
        "scorers": [],
        "split": {"identity_hash": v2.DECLARED_SPLIT_IDENTITY_SHA256},
        "plan": {
            "run_id": run_id,
            "attempt_id": v2.REGISTRY_ATTEMPT_ID,
            "split_identity_hash": v2.DECLARED_SPLIT_IDENTITY_SHA256,
            "protocol_hash": v2.SOURCE_PROTOCOL_SHA256,
        },
        "attempt": {"attempt_id": v2.REGISTRY_ATTEMPT_ID},
        "outputs": {
            "path": str(original_paths["outputs"]),
            "sha256": _sha256(original_paths["outputs"]),
        },
        "raw_trace": {
            "path": str(original_paths["trace"]),
            "sha256": _sha256(original_paths["trace"]),
        },
        "trace_manifest": {
            "path": str(original_paths["trace_manifest"]),
            "sha256": _sha256(original_paths["trace_manifest"]),
        },
    }
    _write_json(original_paths["manifest"], manifest)
    for key in ("outputs", "trace", "trace_manifest"):
        (failed_v1 / original_paths[key].name).write_bytes(original_paths[key].read_bytes())
    failed_v1_manifest = json.loads(json.dumps(manifest))
    failed_v1_manifest["scorers"] = ["a2t-toolcall"]
    for key, source_key in (
        ("outputs", "outputs"),
        ("raw_trace", "trace"),
        ("trace_manifest", "trace_manifest"),
    ):
        failed_v1_manifest[key]["path"] = str(failed_v1 / original_paths[source_key].name)
    _write_json(failed_v1 / original_paths["manifest"].name, failed_v1_manifest)
    v1_failure = mission / "recovery-failure-receipt.json"
    _write_json(v1_failure, {"run_id": run_id, "registry_recontacted_rows": 0})
    source_flight_plan = mission / "flight-plan.json"
    source_precontact_plan = mission / "precontact-plan.json"
    source_failure = mission / "failure-receipt.json"
    _write_json(source_flight_plan, {"run_id": run_id})
    _write_json(source_precontact_plan, {"arms": list(v2.source.ARM_ORDER)})
    _write_json(source_failure, {"run_id": run_id, "recontacted_rows": 0})
    attempt = (
        tmp_path
        / "attempts"
        / run_id
        / f"{v2.REGISTRY_ATTEMPT_ID}.json"
    )
    _write_json(
        attempt,
        {
            "run_id": run_id,
            "attempt_id": v2.REGISTRY_ATTEMPT_ID,
            "state": "ABORTED",
            "actual": {"calls": 8, "audio_seconds": 45.096},
        },
    )
    successor_dir = mission / v2.REGISTRY_V2_DIRNAME
    successor_manifest = json.loads(json.dumps(manifest))
    successor_manifest["scorers"] = ["a2t-toolcall"]
    successor_manifest["split"]["identity_hash"] = v2.ACTUAL_SPLIT_IDENTITY_SHA256
    successor_manifest["plan"]["split_identity_hash"] = v2.ACTUAL_SPLIT_IDENTITY_SHA256
    successor_manifest["protocol_hash"] = v2.ACTUAL_PROTOCOL_SHA256
    successor_manifest["plan"]["protocol_hash"] = v2.ACTUAL_PROTOCOL_SHA256
    for key, source_key in (
        ("outputs", "outputs"),
        ("raw_trace", "trace"),
        ("trace_manifest", "trace_manifest"),
    ):
        successor_manifest[key]["path"] = str(
            successor_dir / original_paths[source_key].name
        )
    successor_bytes = (
        json.dumps(successor_manifest, ensure_ascii=True, indent=2, sort_keys=True)
        + "\n"
    ).encode("utf-8")
    hashes = v2.SourceHashesV2(
        source_flight_plan_sha256=_sha256(source_flight_plan),
        source_precontact_plan_sha256=_sha256(source_precontact_plan),
        source_failure_receipt_sha256=_sha256(source_failure),
        original_manifest_sha256=_sha256(original_paths["manifest"]),
        original_outputs_sha256=_sha256(original_paths["outputs"]),
        original_trace_sha256=_sha256(original_paths["trace"]),
        original_trace_manifest_sha256=_sha256(original_paths["trace_manifest"]),
        registry_attempt_sha256=_sha256(attempt),
        failed_v1_manifest_sha256=_sha256(failed_v1 / original_paths["manifest"].name),
        failed_v1_outputs_sha256=_sha256(failed_v1 / original_paths["outputs"].name),
        failed_v1_trace_sha256=_sha256(failed_v1 / original_paths["trace"].name),
        failed_v1_trace_manifest_sha256=_sha256(
            failed_v1 / original_paths["trace_manifest"].name
        ),
        failed_v1_receipt_sha256=_sha256(v1_failure),
        successor_v2_manifest_sha256=hashlib.sha256(successor_bytes).hexdigest(),
    )
    return mission, tmp_path / "attempts", original_paths, failed_v1, hashes


def test_v2_plan_uses_distinct_run_and_exact_remaining_budget() -> None:
    v2 = _v2()
    plan = v2.recovery_v2_execution_plan()

    assert plan.run_id == "SAEA-A2T-NATIVE-STRUCTURED-ACTION-FIXED8-RECOVERY-V2"
    assert plan.attempt_id == "attempt-20260903T020500Z-handbook-strict-recovery-v2"
    assert plan.split_identity_hash == v2.ACTUAL_SPLIT_IDENTITY_SHA256
    assert plan.protocol_hash == v2.ACTUAL_PROTOCOL_SHA256
    assert plan.planned_model_calls == 8
    assert plan.planned_speech_audio_seconds == 46
    assert plan.planned_gpu_hours == 0.1


def test_actual_split_identity_recomputes_from_the_frozen_eight_ids() -> None:
    v2 = _v2()
    roster = json.loads((REPO / v2.source.ROSTER_RELPATH).read_text(encoding="utf-8"))
    sample_ids = sorted(row["sample_id"] for row in roster["items"])

    actual = split_identity_hash(prefixed("audio2tool", sample_ids))

    assert actual == v2.ACTUAL_SPLIT_IDENTITY_SHA256
    assert actual != v2.DECLARED_SPLIT_IDENTITY_SHA256
    assert (
        protocol_hash(v2.source.COMPOSED_CONFIG_SHA256, "speech-feature-query", actual)
        == v2.ACTUAL_PROTOCOL_SHA256
    )


def test_v2_registry_successor_corrects_only_identity_protocol_scorer_and_paths(
    tmp_path: Path,
) -> None:
    v2 = _v2()
    mission, attempts, original_paths, failed_v1, hashes = _source_fixture(tmp_path, v2)
    original_bytes = {key: path.read_bytes() for key, path in original_paths.items()}
    failed_v1_bytes = {path: path.read_bytes() for path in failed_v1.iterdir()}

    def verify(path: Path):
        document = json.loads(path.read_text(encoding="utf-8"))
        assert document["run_id"] == v2.SOURCE_RUN_ID
        assert document["plan"]["attempt_id"] == v2.REGISTRY_ATTEMPT_ID
        assert document["split"]["identity_hash"] == v2.ACTUAL_SPLIT_IDENTITY_SHA256
        assert document["protocol_hash"] == v2.ACTUAL_PROTOCOL_SHA256
        return SimpleNamespace(attempt_state="ABORTED", outputs_rows=tuple(range(8)))

    receipt = v2.build_registry_v2_successor(
        mission,
        attempts_root=attempts,
        expected=hashes,
        verify=verify,
    )

    successor = mission / v2.REGISTRY_V2_DIRNAME
    successor_manifest = successor / original_paths["manifest"].name
    assert _sha256(successor_manifest) == hashes.successor_v2_manifest_sha256
    assert receipt["successor_run_id"] == v2.RUN_ID
    assert receipt["verified_manifest_run_id"] == v2.SOURCE_RUN_ID
    assert receipt["successor_split_identity_hash"] == v2.ACTUAL_SPLIT_IDENTITY_SHA256
    assert receipt["successor_protocol_hash"] == v2.ACTUAL_PROTOCOL_SHA256
    assert receipt["registry_recontacted"] is False
    assert receipt["registry_model_contacts"] == 0
    assert receipt["completed_rows"] == 8
    assert {key: path.read_bytes() for key, path in original_paths.items()} == original_bytes
    assert {path: path.read_bytes() for path in failed_v1.iterdir()} == failed_v1_bytes


def test_v2_refuses_any_existing_target_or_handbook_attempt(
    tmp_path: Path,
) -> None:
    v2 = _v2()
    root = tmp_path / "data"
    mission = root / v2.SOURCE_MISSION_RELPATH
    mission.mkdir(parents=True)

    target = mission / v2.HANDBOOK_V2_DIRNAME
    target.mkdir()
    with pytest.raises(v2.RecoveryV2Error, match="V2 target already exists"):
        v2.assert_v2_targets_absent(root, mission)

    target.rmdir()
    attempt = (
        root
        / "attempts"
        / v2.SOURCE_RUN_ID
        / f"{v2.V1_RECOVERY_ATTEMPT_ID}.json"
    )
    _write_json(attempt, {"state": "OPENED"})
    with pytest.raises(v2.RecoveryV2Error, match="handbook attempt already exists"):
        v2.assert_v2_targets_absent(root, mission)


def test_handbook_v2_temporarily_binds_corrected_runtime_globals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    v2 = _v2()
    before = {
        "run": v2.source.RUN_ID,
        "split": v2.source.SPLIT_IDENTITY_HASH,
        "protocol": v2.source.PROTOCOL_SHA256,
        "execution_plan": v2.source.execution_plan,
    }

    def run_arm(**kwargs: object):
        assert v2.source.RUN_ID == v2.RUN_ID
        assert v2.source.SPLIT_IDENTITY_HASH == v2.ACTUAL_SPLIT_IDENTITY_SHA256
        assert v2.source.PROTOCOL_SHA256 == v2.ACTUAL_PROTOCOL_SHA256
        assert v2.source.execution_plan(v2.RECOVERY_ATTEMPT_ID) == kwargs["plan"]
        assert kwargs["arm"] == v2.source.ARM_ORDER[1]
        return {"manifest": "sealed"}

    monkeypatch.setattr(v2.source, "_run_arm", run_arm)
    result = v2.run_handbook_v2(
        root=tmp_path,
        context={"recovery_plan": v2.recovery_v2_execution_plan()},
        gate=object(),
        transport=object(),
        session_receipt=tmp_path / "session.json",
        run_dir=tmp_path / v2.HANDBOOK_V2_DIRNAME,
    )

    assert result == {"manifest": "sealed"}
    assert v2.source.RUN_ID == before["run"]
    assert v2.source.SPLIT_IDENTITY_HASH == before["split"]
    assert v2.source.PROTOCOL_SHA256 == before["protocol"]
    assert v2.source.execution_plan is before["execution_plan"]


def test_v2_preregistration_is_zero_contact_and_pins_failed_v1() -> None:
    v2 = _v2()
    prereg = v2.load_v2_preregistration()

    assert prereg["run_id"] == v2.RUN_ID
    assert prereg["contacts_at_registration"] == {
        "gold": 0,
        "model": 0,
        "network": 0,
        "scorer": 0,
        "tokenizer": 0,
    }
    assert prereg["remaining_model_calls"] == 8
    assert prereg["manifest_scorers"] == ["a2t-toolcall"]
    assert prereg["source_hashes"]["failed_v1_receipt_sha256"] == (
        "34fa23f5db5a2465a9876502d4cad803d37f9470f8ed9faf3c9d2359a3f1c20b"
    )
    assert prereg["source_hashes"]["failed_v1_manifest_sha256"] == (
        "1063e42726ec256c5448c759b9a58b004293b672d28ef030b454724555d77eb3"
    )
    assert prereg["failed_v1_contract"] == {
        "authorized_commit": "d5325dbe7b16cb4f0faba7514af15e24d6e988d1",
        "launcher_sha256": (
            "5b4b323bd4587a922028734545cd1eb09c95edfe7558f4ed3fbe94245c4e98ec"
        ),
        "preregistration_sha256": (
            "bf0658c13b8cdfa07fd372951cf662eea3ffc044b0f6dcd9e32924f778d816d1"
        ),
        "execution_plan_file_sha256": (
            "3aa2da2e71f78a507a6f443cd8d4ac3269b7e106ffd908401f0cfdba961d6763"
        ),
    }
    assert prereg["recovery_execution_plan"] == asdict(
        v2.recovery_v2_execution_plan()
    )


def test_v2_source_has_no_protected_or_registry_contact_surface() -> None:
    source_text = V2_LAUNCHER.read_text(encoding="utf-8")

    assert "load_expected_calls" not in source_text
    assert "score_item" not in source_text
    assert "evaluate_parallel" not in source_text
    assert "requests.get" not in source_text
    assert "requests.post" not in source_text
    assert "run_two_arms_batched" not in source_text
    assert "retry" not in source_text.lower()


def test_v2_preflight_only_never_writes_or_contacts(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    v2 = _v2()
    monkeypatch.setattr(
        v2,
        "v2_preflight",
        lambda root: {
            "source_state": "V1_FAILURE_PINNED",
            "recovery_execution_plan_sha256": "a" * 64,
        },
    )
    monkeypatch.setattr(
        v2, "launch_v2", lambda _root: pytest.fail("contact path entered")
    )

    assert v2.main(["--preflight-only", "--data-root", "/data"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["registry_calls_remaining"] == 0
    assert output["handbook_calls_remaining"] == 8
    assert output["contacts"]["model"] == 0


def test_v2_preflight_recomputes_identity_and_preserves_request_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    v2 = _v2()
    root = tmp_path
    mission = root / v2.SOURCE_MISSION_RELPATH
    _mission, _attempts, _original, _failed_v1, hashes = _source_fixture(
        root, v2, mission=mission
    )
    roster = json.loads((REPO / v2.source.ROSTER_RELPATH).read_text(encoding="utf-8"))
    sample_ids = tuple(sorted(row["sample_id"] for row in roster["items"]))
    precontact_hash = "d" * 64
    prereg = {
        "source_mission_relpath": v2.SOURCE_MISSION_RELPATH.as_posix(),
        "source_hashes": asdict(hashes),
        "frozen_request_contract": {
            "registered_flight_plan_sha256": v2.source.REGISTERED_PLAN_SHA256,
            "precontact_request_contract_sha256": precontact_hash,
            "response_format_sha256": v2.source.SCHEMA_SHA256,
            "batch_size": 2,
            "concurrency": 2,
            "queue_depth": 4,
            "network_jitter_testing": False,
        },
    }
    composed = ComposedConfig(
        values={"scorers": []},
        config_hash=v2.source.COMPOSED_CONFIG_SHA256,
        fragments={},
    )
    original_attempt_check = v2.source.assert_run_has_no_attempt_records

    def static_preflight(received_root: Path):
        assert received_root == root
        v2.source.assert_run_has_no_attempt_records(received_root)
        return {
            "sample_ids": sample_ids,
            "composed": composed,
            "precontact_plan_sha256": precontact_hash,
        }

    monkeypatch.setattr(v2, "load_v2_preregistration", lambda: prereg)
    monkeypatch.setattr(v2.source, "static_preflight", static_preflight)

    context = v2.v2_preflight(root)

    assert context["source_state"] == "V1_FAILURE_PINNED"
    assert context["mission_dir"] == mission.resolve()
    assert context["composed"].values["scorers"] == ["a2t-toolcall"]
    assert context["recovery_plan"] == v2.recovery_v2_execution_plan()
    assert v2.source.assert_run_has_no_attempt_records is original_attempt_check


def test_launch_v2_emits_the_postseal_bound_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    v2 = _v2()
    root = tmp_path / "data"
    mission = root / v2.SOURCE_MISSION_RELPATH
    mission.mkdir(parents=True)
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
        "attempts_root": root / "attempts",
        "source_hashes": v2.SourceHashesV2(*("a" * 64 for _ in range(14))),
        "recovery_plan": v2.recovery_v2_execution_plan(),
        "composed": ComposedConfig(values=values, config_hash="b" * 64, fragments={}),
        "runtime_receipt": object(),
    }
    registry_manifest = tmp_path / "registry.run-manifest.json"
    registry_manifest.write_text("registry", encoding="ascii")
    registry = {
        "successor_manifest_path": str(registry_manifest),
        "successor_run_id": v2.RUN_ID,
        "verified_manifest_run_id": v2.SOURCE_RUN_ID,
    }
    artifacts = {}
    for key in ("outputs", "raw_trace", "trace_manifest"):
        path = tmp_path / f"handbook-{key}.json"
        path.write_text(key, encoding="ascii")
        artifacts[key] = path
    handbook_manifest = tmp_path / "handbook.run-manifest.json"
    handbook_document = {
        "run_id": v2.RUN_ID,
        "protocol_hash": v2.ACTUAL_PROTOCOL_SHA256,
        "scorers": ["a2t-toolcall"],
        **{
            key: {"path": str(path), "sha256": _sha256(path)}
            for key, path in artifacts.items()
        },
    }
    _write_json(handbook_manifest, handbook_document)
    registry_bundle = SimpleNamespace(
        attempt_state="ABORTED", outputs_rows=tuple(range(8))
    )
    handbook_bundle = SimpleNamespace(
        attempt_state="OPENED",
        outputs_rows=tuple(range(8)),
        manifest=handbook_document,
        manifest_path=handbook_manifest,
    )
    events: list[str] = []

    class Gate:
        def assert_model_touch_allowed(self, plan: object, *, full_hash: bool):
            assert plan == context["recovery_plan"]
            assert full_hash is True
            events.append("gate")

    monkeypatch.setattr(v2, "v2_preflight", lambda _root: context)
    monkeypatch.setattr(
        v2,
        "FrozenCoreGate",
        SimpleNamespace(for_study_repo=lambda *_args, **_kwargs: Gate()),
    )
    monkeypatch.setattr(
        v2,
        "build_registry_v2_successor",
        lambda *_args, **_kwargs: events.append("registry") or registry,
    )
    monkeypatch.setattr(
        v2.source,
        "start_session",
        lambda **_kwargs: events.append("start") or object(),
    )
    monkeypatch.setattr(
        v2.source,
        "TRANSPORTS",
        SimpleNamespace(resolve=lambda name: lambda *_args, **_kwargs: name),
    )
    monkeypatch.setattr(v2.source, "_stop", lambda *_args: events.append("stop"))
    monkeypatch.setattr(
        v2,
        "run_handbook_v2",
        lambda **_kwargs: events.append("handbook")
        or {"manifest": str(handbook_manifest)},
    )
    monkeypatch.setattr(
        v2,
        "verify_bundle",
        lambda path: registry_bundle if path == registry_manifest else handbook_bundle,
    )
    monkeypatch.setattr(v2, "_validate_immutable_sources", lambda *_args, **_kwargs: {})

    receipt = v2.launch_v2(root)

    assert events == ["gate", "registry", "start", "handbook", "stop"]
    assert receipt["schema"] == (
        "saea-a2t-native-structured-action-fixed8-recovery-v2-flight-v1"
    )
    assert receipt["run_id"] == v2.RUN_ID
    assert receipt["registry_recovery"] == registry
    assert receipt["handbook_recovery"]["attempt_state"] == "OPENED"
    assert receipt["registry_recontact_count"] == 0
    assert receipt["response_meanings_opened"] is False
    persisted = json.loads(
        (mission / v2.FLIGHT_V2_RECEIPT_NAME).read_text(encoding="utf-8")
    )
    assert persisted["registry_recovery"] == registry
