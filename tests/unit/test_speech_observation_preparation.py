"""Exercise source export and registered batched ASR preparation without a model."""

import hashlib
import json
from dataclasses import asdict
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.preparation_speech_observations import (
    export_speech_observation_sources,
    run_speech_observation_preparation,
)
from speech_aware_evidence_acquisition.rails.speech_observation import load_speech_observation_catalog


def pin(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))
    return {"relpath": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def job(tmp_path, monkeypatch):
    root, data = tmp_path / "repo", tmp_path / "data"
    root.mkdir()
    data.mkdir()
    bindings = {}
    for number, frames in enumerate((400, 560)):
        path = data / f"speech-{number}.wav"
        soundfile.write(path, np.zeros(frames, dtype=np.float32), 16000)
        bindings[f"sample-{number}"] = {
            "packet_id": f"packet-{number}",
            "packet_sha256": str(number + 1) * 64,
            "source_audio_relpath": path.name,
            "source_audio_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_audio_duration_seconds": frames / 16000,
        }
    split = hashlib.sha256(b"fake-carrier/sample-0\nfake-carrier/sample-1").hexdigest()
    source = export_speech_observation_sources(
        data / "prepared/sources.json", source_bindings=bindings,
        carrier_lock_key="fake-carrier", split_identity_hash=split,
    )
    inventory = pin(root, "receipts/whisper.json", {
        "schema": "saea-local-whisper-runtime-inventory-v1",
        "model": "large-v3", "checkpoint": {"path": "/synthetic/weights", "bytes": 1, "sha256": "a" * 64},
        "whisper_source_path": "/synthetic/source", "source_files": {}, "packages": {},
    })
    protocol = {
        "schema": "saea-speech-observation-preparation-protocol-v1",
        "sources": {"relpath": "prepared/sources.json", "sha256": source["sha256"]},
        "checkpoint_receipt": inventory,
        "decoding": {"schema": "saea-local-whisper-decode-v1", "device": "cuda",
            "cpu_workers": 2, "batch_size": 2, "language": "en", "task": "transcribe",
            "temperature": 0, "beam_size": 5, "sample_len": 224,
            "without_timestamps": True, "fp16": True,
            "no_speech_threshold": 0.6, "logprob_threshold": -1.0},
        "monitor_interval_seconds": 10,
        "catalog_id": "synthetic-asr-preparation-v1",
        "output_relpath": "prepared/TEST-ASR/attempt-v1/catalog.json",
        "artifacts_relpath": "prepared/TEST-ASR/attempt-v1/observations",
    }
    protocol_pin = pin(root, "protocol.json", protocol)
    plan = ExecutionPlan(
        run_id="TEST-ASR", attempt_id="attempt-v1",
        execution_profile="bounded-discovery-probe", carrier_lock_key="fake-carrier",
        split_role="discovery", split_identity_hash=split, planned_model_calls=2,
        planned_gpu_hours=1, planned_speech_audio_seconds=1,
        protocol_hash=protocol_pin["sha256"],
    )
    plan_pin = pin(root, "plan.json", {"execution_plan": asdict(plan)})
    ledger = root / "docs/exposure-ledger.md"
    ledger.parent.mkdir()
    ledger.write_text(
        "| run/experiment id | speech carrier + split | execution profile | split role | split identity hash | consumed | calls | speech audio seconds | gpu hours |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
        f"| TEST-ASR | fake-carrier, discovery | bounded-discovery-probe | discovery | {split} | no | 2 | 1 | 1.0 |\n"
    )
    config = {
        "plan": asdict(plan), "execution_plan": plan_pin,
        "ledger_row": {"relpath": "docs/exposure-ledger.md",
            "sha256": hashlib.sha256(ledger.read_bytes()).hexdigest(), "row_id": plan.run_id},
        "protocol": {"path": str(root / "protocol.json"), "sha256": protocol_pin["sha256"]},
        "umbrella_lock": {"path": str(root / "lock.json"), "sha256": "f" * 64},
        "session_id": "asr-preparation-test", "study_head": "a" * 40,
    }
    import speech_aware_evidence_acquisition.core.speech_preparation_runtime as shared
    import speech_aware_evidence_acquisition.core.preparation_speech_observations as preparation
    monkeypatch.setattr(shared, "admit", lambda **kwargs: None)
    monkeypatch.setattr(shared, "start_monitor", lambda *args: lambda: None)
    monkeypatch.setattr(preparation, "verify_whisper_inventory", lambda value: {
        "schema": "saea-local-whisper-backend-inventory-v1", "model": "large-v3",
        "checkpoint_path": "/synthetic/weights", "checkpoint_sha256": "a" * 64,
        "whisper_source_path": "/synthetic/source",
    })
    return SimpleNamespace(root=root, data=data, config=config, bindings=bindings,
        split=split, protocol=protocol, preparation=preparation, shared=shared)


class Backend:
    def __init__(self, job, fail=False):
        self.job, self.fail = job, fail
        self.batches, self.closed = [], False
    def prepare_sources(self, sources):
        self.sources = tuple(sources)
    def decode_batch(self, sources):
        self.batches.append(tuple(sources))
        state = json.loads((self.job.data / "attempts/TEST-ASR/attempt-v1.json").read_text())
        assert state["actual"]["calls"] == len(sources)
        assert state["actual"]["audio_seconds"] == pytest.approx(0.06)
        assert (self.job.data / "locks/flight.lock").exists()
        markers = list((self.job.data / "prepared/TEST-ASR/attempt-v1/observations").glob("*.speech-tool-started.json"))
        assert len(markers) == len(sources)
        if self.fail:
            raise RuntimeError("synthetic decoder interrupted")
        return [{"schema": "saea-prepared-speech-observation-v1", "status": "ok",
            "transcript": f"Independent words {index}.",
            "diagnostics": {"raw_text": f"Independent words {index}."}}
            for index in range(len(sources))]
    def close(self):
        self.closed = True


def test_batched_preparation_seals_consumer_catalog_and_warm_reuse_has_no_contact(job):
    backend = Backend(job)
    def factory(*args):
        return backend
    result = run_speech_observation_preparation(
        job.config, source_root=job.root, data_root=job.data, backend_factory=factory,
    )
    assert result["status"] == "SEALED"
    assert result["logical_speech_tool_contacts"] == 2
    assert len(backend.batches) == 1
    assert backend.closed
    assert not (job.data / "locks/flight.lock").exists()
    state = json.loads((job.data / "attempts/TEST-ASR/attempt-v1.json").read_text())
    assert state["state"] == "FINALIZED"
    assert state["finalization"]["kind"] == "speech-observation-catalog"
    declaration = {"prepared_speech_observations": {
        "relpath": job.protocol["output_relpath"], "sha256": result["catalog_sha256"]}}
    loaded = load_speech_observation_catalog(declaration, data_root=job.data,
        source_audio_bindings=job.bindings, split_identity_hash=job.split, repo_root=job.root)
    assert loaded.receipt()["prepared_count"] == 2
    def refuse(*args, **kwargs):
        raise AssertionError("warm cache touched admission or backend")
    job.shared.admit = refuse
    warm = run_speech_observation_preparation(job.config, source_root=job.root,
        data_root=job.data, backend_factory=refuse)
    assert warm["cache"] == "warm"
    assert warm["new_neural_contacts"] == 0
    assert warm["producer_contacts"]["calls"] == 2
    assert json.loads((job.data / "attempts/TEST-ASR/attempt-v1.json").read_text()) == state


def test_interrupted_batch_preserves_debit_and_cannot_replay(job):
    backend = Backend(job, fail=True)
    with pytest.raises(RuntimeError, match="interrupted"):
        run_speech_observation_preparation(job.config, source_root=job.root,
            data_root=job.data, backend_factory=lambda *args: backend)
    state = json.loads((job.data / "attempts/TEST-ASR/attempt-v1.json").read_text())
    assert state["state"] == "ABORTED"
    assert state["actual"]["calls"] == 2
    assert backend.closed
    assert (job.data / "locks/flight.lock").exists()
    with pytest.raises(Exception):
        run_speech_observation_preparation(job.config, source_root=job.root,
            data_root=job.data, backend_factory=lambda *args: pytest.fail("automatic replay"))
    assert len(backend.batches) == 1


@pytest.mark.parametrize("change", ["source", "plan", "ledger", "output_extra"])
def test_changed_binding_refuses_before_backend(job, change):
    if change == "source":
        (job.data / "speech-0.wav").write_bytes(b"changed")
    elif change == "plan":
        (job.root / "plan.json").write_bytes(b"changed")
    elif change == "ledger":
        (job.root / "docs/exposure-ledger.md").write_bytes(b"changed")
    else:
        job.protocol["reference"] = "Forbidden task answer."
        p = pin(job.root, "protocol.json", job.protocol)
        job.config["protocol"]["sha256"] = p["sha256"]
        job.config["plan"]["protocol_hash"] = p["sha256"]
        job.config["execution_plan"] = pin(job.root, "plan.json", {"execution_plan": job.config["plan"]})
    with pytest.raises(Exception):
        run_speech_observation_preparation(job.config, source_root=job.root,
            data_root=job.data, backend_factory=lambda *args: pytest.fail("bad binding reached backend"))


def test_source_inventory_exports_bound_media_only_and_reuses_without_producer(job):
    p = job.data / "prepared/sources.json"
    before = p.read_bytes()
    receipt = export_speech_observation_sources(p, source_bindings=job.bindings,
        carrier_lock_key="fake-carrier", split_identity_hash=job.split)
    assert receipt["cache"] == "warm"
    assert p.read_bytes() == before
    bad = {key: dict(value) for key, value in job.bindings.items()}
    bad["sample-0"]["reference"] = "Forbidden."
    with pytest.raises(Exception):
        export_speech_observation_sources(job.data / "bad.json", source_bindings=bad,
            carrier_lock_key="fake-carrier", split_identity_hash=job.split)


def test_runtime_exports_source_metadata_without_preflight_or_model_contact(job):
    from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
    runtime = SimpleNamespace(
        _prepare=lambda: ({}, "fake-carrier", "DEV", job.split),
        uses_speech_feature_packets=lambda: True,
        source_audio_bindings=lambda **kwargs: job.bindings,
    )
    result = FlightRuntime.prepare_speech_observation_sources(
        runtime, job.data / "export.json")
    assert result["contact_class"] == "model-free"
    assert result["cache"] == "cold"


def _rebind_protocol(job):
    bound = pin(job.root, "protocol.json", job.protocol)
    job.config["protocol"]["sha256"] = bound["sha256"]
    job.config["plan"]["protocol_hash"] = bound["sha256"]
    job.config["execution_plan"] = pin(job.root, "plan.json", {"execution_plan": job.config["plan"]})


def test_catalog_uses_persisted_audio_total_and_warm_reuse_accepts_header_tolerance(job):
    job.bindings["sample-0"]["source_audio_duration_seconds"] += 0.0000003
    source = export_speech_observation_sources(job.data / "prepared/rounded-sources.json",
        source_bindings=job.bindings, carrier_lock_key="fake-carrier", split_identity_hash=job.split)
    job.protocol["sources"] = {"relpath": "prepared/rounded-sources.json", "sha256": source["sha256"]}
    _rebind_protocol(job)
    backend = Backend(job)
    result = run_speech_observation_preparation(job.config, source_root=job.root,
        data_root=job.data, backend_factory=lambda *args: backend)
    catalog = json.loads((job.data / result["catalog_relpath"]).read_text())
    attempt = json.loads((job.data / "attempts/TEST-ASR/attempt-v1.json").read_text())
    assert catalog["producer"]["contacts"]["audio_seconds"] == attempt["actual"]["audio_seconds"]
    warm = run_speech_observation_preparation(job.config, source_root=job.root,
        data_root=job.data, backend_factory=lambda *args: pytest.fail("warm decode"))
    assert warm["new_neural_contacts"] == 0


def test_cold_admission_and_frozen_ledger_must_name_the_same_registered_bytes(job):
    canonical = job.root / "docs/exposure-ledger.md"
    frozen = job.root / "docs/frozen-ledger.md"
    frozen.write_bytes(canonical.read_bytes())
    job.config["ledger_row"]["relpath"] = "docs/frozen-ledger.md"
    canonical.write_text(canonical.read_text().replace("| no | 2 |", "| no | 3 |"))
    with pytest.raises(Exception):
        run_speech_observation_preparation(job.config, source_root=job.root,
            data_root=job.data, backend_factory=lambda *args: pytest.fail("different admission ledger"))


def test_post_finalization_event_failure_preserves_finalized_attempt_and_original_error(job, monkeypatch):
    backend = Backend(job)
    dumps = job.shared.json.dumps
    def fail_sealed(value, *args, **kwargs):
        if isinstance(value, dict) and value.get("phase") == "sealed":
            raise OSError("synthetic final telemetry failure")
        return dumps(value, *args, **kwargs)
    monkeypatch.setattr(job.shared.json, "dumps", fail_sealed)
    with pytest.raises(OSError, match="final telemetry"):
        run_speech_observation_preparation(job.config, source_root=job.root,
            data_root=job.data, backend_factory=lambda *args: backend)
    state = json.loads((job.data / "attempts/TEST-ASR/attempt-v1.json").read_text())
    assert state["state"] == "FINALIZED"
    assert backend.closed


def test_runtime_inventory_checks_actual_source_bytes_and_package_versions(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.preparation_speech_observations import verify_whisper_inventory
    root = tmp_path / "official"
    checkpoint = tmp_path / "large-v3.pt"
    checkpoint.write_bytes(b"synthetic pinned checkpoint")
    files = {}
    names = ("whisper/__init__.py", "whisper/audio.py", "whisper/decoding.py",
        "whisper/model.py", "whisper/tokenizer.py", "whisper/assets/mel_filters.npz",
        "whisper/assets/multilingual.tiktoken")
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"synthetic source")
        files[name] = {"bytes": path.stat().st_size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    packages = {name: "1" for name in ("openai-whisper", "torch", "numpy", "tiktoken")}
    inventory = {"schema": "saea-local-whisper-runtime-inventory-v1", "model": "large-v3",
        "checkpoint": {"path": str(checkpoint), "bytes": checkpoint.stat().st_size,
                       "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest()},
        "whisper_source_path": str(root), "source_files": files, "packages": packages}
    import importlib.metadata
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1")
    backend = verify_whisper_inventory(inventory)
    assert backend["checkpoint_path"] == str(checkpoint)
    (root / names[1]).write_bytes(b"changed")
    with pytest.raises(Exception, match="size|hash"):
        verify_whisper_inventory(inventory)
    (root / names[1]).write_bytes(b"synthetic source")
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "2")
    with pytest.raises(Exception, match="version changed"):
        verify_whisper_inventory(inventory)


def _source_version_inventory(tmp_path, version_bytes=b'__version__ = "20250625"\n'):
    source = tmp_path / "source"
    source.mkdir()
    checkpoint = tmp_path / "checkpoint"
    checkpoint.write_bytes(b"synthetic checkpoint; never loaded")
    files = {}
    for relative in (
        "whisper/__init__.py", "whisper/audio.py", "whisper/decoding.py",
        "whisper/model.py", "whisper/tokenizer.py", "whisper/assets/mel_filters.npz",
        "whisper/assets/multilingual.tiktoken", "whisper/version.py",
    ):
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = version_bytes if relative == "whisper/version.py" else b"synthetic source"
        path.write_bytes(raw)
        files[relative] = {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    return {
        "schema": "saea-local-whisper-runtime-inventory-v2", "model": "large-v3",
        "checkpoint": {"path": str(checkpoint), "bytes": checkpoint.stat().st_size,
                       "sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest()},
        "whisper_source_path": str(source), "source_files": files,
        "packages": {"openai-whisper": "20250625", "torch": "1", "numpy": "1", "tiktoken": "1"},
        "whisper_version_source": {"kind": "pinned-source-file", "relpath": "whisper/version.py"},
    }


def test_explicit_source_version_needs_no_whisper_distribution_or_import(tmp_path, monkeypatch):
    import importlib.metadata
    from speech_aware_evidence_acquisition.core.preparation_speech_observations import verify_whisper_inventory
    inventory = _source_version_inventory(tmp_path)
    queried = []

    def version(name):
        queried.append(name)
        if name == "openai-whisper":
            raise importlib.metadata.PackageNotFoundError(name)
        return "1"

    monkeypatch.setattr(importlib.metadata, "version", version)
    result = verify_whisper_inventory(inventory)
    assert result["whisper_source_path"] == inventory["whisper_source_path"]
    assert queried == ["torch", "numpy", "tiktoken"]
    # V1 cannot silently opt into this source-only behavior.
    inventory["schema"] = "saea-local-whisper-runtime-inventory-v1"
    del inventory["whisper_version_source"]
    with pytest.raises(importlib.metadata.PackageNotFoundError):
        verify_whisper_inventory(inventory)


@pytest.mark.parametrize("version_bytes", [
    b'__version__ = "wrong"\n',
    b'__version__ = str(20250625)\n',
    b'__version__ = "20250625"\nraise RuntimeError("must not execute")\n',
    b'__version__: str = "20250625"\n',
])
def test_source_version_rejects_wrong_or_executable_version(tmp_path, monkeypatch, version_bytes):
    import importlib.metadata
    from speech_aware_evidence_acquisition.core.preparation import PreparationError
    from speech_aware_evidence_acquisition.core.preparation_speech_observations import verify_whisper_inventory
    inventory = _source_version_inventory(tmp_path, version_bytes)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1")
    with pytest.raises(PreparationError, match="version|literal"):
        verify_whisper_inventory(inventory)


def test_source_version_keeps_dependency_and_source_hash_checks(tmp_path, monkeypatch):
    import importlib.metadata
    from speech_aware_evidence_acquisition.core.preparation import PreparationError
    from speech_aware_evidence_acquisition.core.preparation_speech_observations import verify_whisper_inventory
    inventory = _source_version_inventory(tmp_path)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "wrong" if name == "torch" else "1")
    with pytest.raises(PreparationError, match="torch"):
        verify_whisper_inventory(inventory)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1")
    from pathlib import Path
    (Path(inventory["whisper_source_path"]) / "whisper/version.py").write_bytes(b'__version__ = "20250626"\n')
    with pytest.raises(PreparationError):
        verify_whisper_inventory(inventory)


@pytest.mark.parametrize("change", ["unpinned", "foreign_path", "unknown_kind"])
def test_source_version_requires_exact_explicit_version_pin(tmp_path, monkeypatch, change):
    import importlib.metadata
    from speech_aware_evidence_acquisition.core.preparation import PreparationError
    from speech_aware_evidence_acquisition.core.preparation_speech_observations import verify_whisper_inventory
    inventory = _source_version_inventory(tmp_path)
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1")
    if change == "unpinned":
        del inventory["source_files"]["whisper/version.py"]
    elif change == "foreign_path":
        inventory["whisper_version_source"]["relpath"] = "../version.py"
    else:
        inventory["whisper_version_source"]["kind"] = "import-and-evaluate"
    with pytest.raises(PreparationError):
        verify_whisper_inventory(inventory)
