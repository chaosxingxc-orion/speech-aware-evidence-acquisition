"""End-to-end wiring on the synthetic world with a fake transport."""

import json

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.base import CoreError, RunResult
from speech_aware_evidence_acquisition.core.config import ComposedConfig, protocol_hash
from speech_aware_evidence_acquisition.core.driver import load_split, run_experiment
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import discovery_split, freeze_splits


class _OpenGate:
    def assert_model_touch_allowed(self, plan):
        pass


def _composed(**overrides):
    values = {
        "carrier_lock_key": "earnings21-original",
        "split_name": "discovery",
        "arm": "bare-core",
        "policy": "fixed",
        "evidence_source": "none",
        "evidence_mismatch": False,
        "scorers": ["asr-wer"],
        "task_instruction": "Transcribe.",
        "decoding_params": {"temperature": 0, "seed": 20260803},
        "experiment_id": "SAEA-E-000",
    }
    values.update(overrides)
    return ComposedConfig(
        values=values, config_hash="d" * 64,
        fragments={"model": "m", "dataset": "d", "baseline": "b", "experiment": "e"},
    )


def _plan(split_hash, **overrides):
    base = dict(
        run_id="SAEA-E-000-driver",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="earnings21-original",
        split_role="discovery",
        split_identity_hash=split_hash,
        planned_model_calls=10,
        planned_gpu_hours=1.0,
        planned_speech_audio_seconds=1000,
        protocol_hash="b" * 64,
    )
    base.update(overrides)
    return ExecutionPlan(**base)


def _transport(request_bytes):
    return json.dumps({"text": "token tags", "usage": {"prompt_tokens": 3}}).encode()


def _frozen_world(synthetic_world, tmp_path):
    lock = load_lock(synthetic_world.lock_path)
    receipts = tmp_path / "repo" / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    return lock, tmp_path / "repo"


def test_run_experiment_end_to_end(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    ids, split_hash, split_role = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    assert len(ids) == 3
    assert split_role == "discovery"
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run",
        transport=_transport,
        repo_root=repo_root,
    )
    assert isinstance(result, RunResult)
    lines = result.outputs_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert result.cost["calls_used"] == 3
    manifest = json.loads(
        (tmp_path / "run" / "SAEA-E-000-driver.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/obs") for record_id in manifest)
    assert any(record_id.endswith("/use") for record_id in manifest)


def test_run_experiment_refuses_wrong_split_hash(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    with pytest.raises(CoreError, match="split"):
        run_experiment(
            composed=_composed(),
            plan=_plan("f" * 64),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_receipt_dev_role_mismatch(synthetic_world, tmp_path):
    """A plan labeled 'discovery' must not be able to run against the dev split."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, dev_hash, dev_role = load_split(repo_root, "dev", lock, synthetic_world.data_root)
    assert dev_role == "dev"
    with pytest.raises(CoreError, match="split role"):
        run_experiment(
            composed=_composed(
                carrier_lock_key="earnings22-original",
                split_name="dev",
            ),
            plan=_plan(dev_hash, split_role="discovery"),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_confirmatory_split_under_a_dev_labeled_plan(
    synthetic_world, tmp_path
):
    """A confirmatory split can never run, even mislabeled as a 'dev' plan."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, confirmatory_hash, confirmatory_role = load_split(repo_root, "confirmatory", lock, synthetic_world.data_root)
    assert confirmatory_role == "confirmatory"
    with pytest.raises(CoreError, match="split role"):
        run_experiment(
            composed=_composed(
                carrier_lock_key="earnings22-original",
                split_name="confirmatory",
            ),
            plan=_plan(confirmatory_hash, split_role="dev"),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_supplies_evidence_with_org_and_supply_traces(
    synthetic_world, tmp_path
):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed(arm="fixed-legal-context", evidence_source="conec-contexts")
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    result = run_experiment(
        composed=composed,
        plan=plan,
        gate=_OpenGate(),
        lock=lock,
        root=synthetic_world.data_root,
        run_dir=tmp_path / "run2",
        transport=_transport,
        repo_root=repo_root,
    )
    manifest = json.loads(
        (tmp_path / "run2" / "SAEA-E-000-driver.trace-manifest.json").read_text("utf-8")
    )["records"]
    assert any(record_id.endswith("/org") for record_id in manifest)
    assert any(record_id.endswith("/supply") for record_id in manifest)
    assert result.arm == "fixed-legal-context"


def test_run_experiment_refuses_wrong_protocol_hash(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    with pytest.raises(CoreError, match="protocol hash"):
        run_experiment(
            composed=_composed(),
            plan=_plan(split_hash, protocol_hash="c" * 64),
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_preexisting_outputs_file(synthetic_world, tmp_path):
    """A fresh sink dir (no trace files) but a manually pre-existing outputs
    file must still fail closed — the driver's own "x"-mode open, not just
    the sink's pre-existence check, is the belt-and-suspenders guard."""

    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    run_dir = tmp_path / "run3"
    run_dir.mkdir(parents=True)
    (run_dir / f"{plan.run_id}.outputs.jsonl").write_text("stale\n", encoding="utf-8")
    with pytest.raises(CoreError, match="exists"):
        run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=run_dir,
            transport=_transport,
            repo_root=repo_root,
        )


def test_run_experiment_refuses_wrong_carrier_lock_key(synthetic_world, tmp_path):
    lock, repo_root = _frozen_world(synthetic_world, tmp_path)
    _, split_hash, _ = load_split(repo_root, "discovery", lock, synthetic_world.data_root)
    composed = _composed()
    plan = _plan(
        split_hash,
        carrier_lock_key="earnings22-original",
        protocol_hash=protocol_hash(composed.config_hash, composed.values["arm"], split_hash),
    )
    with pytest.raises(CoreError, match="carrier"):
        run_experiment(
            composed=composed,
            plan=plan,
            gate=_OpenGate(),
            lock=lock,
            root=synthetic_world.data_root,
            run_dir=tmp_path / "run",
            transport=_transport,
            repo_root=repo_root,
        )
