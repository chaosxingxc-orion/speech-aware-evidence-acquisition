"""Exercise governed speech preparation with synthetic media and no model."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pytest
import soundfile

from speech_aware_evidence_acquisition.contracts import ExecutionPlan
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.core.speech_preparation_runtime import (
    BoundedAudioPrefetch,
    run_preparation,
)


def pin(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def job(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    wav = data / "speech.wav"
    soundfile.write(wav, np.zeros(400, dtype=np.float32), 16000)
    rows = [
        {
            "id": "sample",
            "media_relpath": "speech.wav",
            "audio_sha256": hashlib.sha256(wav.read_bytes()).hexdigest(),
            "source_frames": 400,
            "source_sample_rate_hz": 16000,
        }
    ]
    inventory = data / "sources.json"
    inventory.write_text(json.dumps({"rows": rows, "roster_sha256": "b" * 64}))
    encoder = data / "encoder.json"
    encoder.write_text(
        json.dumps({"model_dir_relpath": "model", "files": {}, "packages": {}})
    )
    protocol = {
        "schema": "saea-speech-query-encoding-protocol-v1",
        "sources": pin(inventory),
        "encoder": pin(encoder),
        "roster_sha256": "b" * 64,
        "query_prompt": "query: ",
        "dimension": 2,
        "max_seconds": 120.0,
        "overlap_seconds": 8.0,
        "max_audio_samples": 1920000,
        "max_sequence_tokens": 8192,
        "cpu_workers": 2,
        "monitor_interval_seconds": 10,
        "expected_unique_spans": 1,
        "output_relpath": "prepared/index.json",
        "query_rows_relpath": "prepared/queries.jsonl",
        "cache_relpath": "cache",
    }
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_bytes(canonical_bytes(protocol))
    plan = ExecutionPlan(
        run_id="TEST-ENCODE",
        execution_profile="bounded-discovery-probe",
        carrier_lock_key="test-speech",
        split_role="discovery",
        split_identity_hash=hashlib.sha256(b"test-speech/sample").hexdigest(),
        planned_model_calls=1,
        planned_gpu_hours=1,
        planned_speech_audio_seconds=1,
        protocol_hash=pin(protocol_path)["sha256"],
        attempt_id="attempt-v1",
    )
    config = {
        "plan": asdict(plan),
        "protocol": pin(protocol_path),
        "umbrella_lock": {"path": str(tmp_path / "lock.json"), "sha256": "c" * 64},
        "session_id": "encoder-test",
        "study_head": "a" * 40,
    }
    import speech_aware_evidence_acquisition.core.speech_preparation_runtime as runtime

    monkeypatch.setattr(runtime, "admit", lambda **_: {})
    monkeypatch.setattr(runtime, "verify_encoder", lambda *_: None)
    monkeypatch.setattr(runtime, "start_monitor", lambda *_: lambda: None)
    return tmp_path, data, config, runtime


class Backend:
    def __init__(self):
        self.sources = []
        self.calls = []
        self.closed = False

    def prepare_sources(self, sources):
        self.sources = sources

    def __call__(self, source):
        self.calls.append(source)
        return [1.0, 0.0]

    def close(self):
        self.closed = True


def test_preparation_seals_bound_rows_and_accounts_before_contact(job):
    root, data, config, runtime = job
    backend = Backend()
    original = backend.__call__

    class CheckingBackend(Backend):
        def __call__(self, source):
            state = json.loads(
                (data / "attempts/TEST-ENCODE/attempt-v1.json").read_text()
            )
            assert state["actual"]["calls"] == 1
            assert (data / "locks/flight.lock").exists()
            return original(source)

    backend = CheckingBackend()
    result = run_preparation(
        config, source_root=root, data_root=data, backend_factory=lambda *_: backend
    )
    assert result["status"] == "SEALED"
    assert result["logical_encoder_contacts"] == 1
    assert result["actual_speech_audio_seconds"] == pytest.approx(0.025)
    assert backend.closed
    rows = [
        json.loads(line)
        for line in (data / "prepared/queries.jsonl").read_text().splitlines()
    ]
    assert rows[0]["segments"][0]["vectors"] == {"content": [1.0, 0.0]}
    assert not (data / "locks/flight.lock").exists()


def test_warm_index_has_zero_encoder_contacts(job):
    root, data, config, runtime = job
    run_preparation(
        config, source_root=root, data_root=data, backend_factory=lambda *_: Backend()
    )
    config["plan"]["attempt_id"] = "attempt-v2"

    class NoContact(Backend):
        def __call__(self, source):
            pytest.fail("warm cache contacted encoder")

    result = run_preparation(
        config, source_root=root, data_root=data, backend_factory=lambda *_: NoContact()
    )
    assert result["logical_encoder_contacts"] == 0


def test_failure_is_sealed_as_abort_and_cannot_replay(job):
    root, data, config, runtime = job

    class Failing(Backend):
        def __call__(self, source):
            raise RuntimeError("synthetic encoder failure")

    with pytest.raises(RuntimeError, match="synthetic"):
        run_preparation(
            config,
            source_root=root,
            data_root=data,
            backend_factory=lambda *_: Failing(),
        )
    state = json.loads((data / "attempts/TEST-ENCODE/attempt-v1.json").read_text())
    assert state["state"] == "ABORTED"
    assert state["actual"]["calls"] == 1
    assert (data / "locks/flight.lock").exists()
    with pytest.raises(Exception):
        run_preparation(
            config,
            source_root=root,
            data_root=data,
            backend_factory=lambda *_: Backend(),
        )


@pytest.mark.parametrize(
    "change", ["protocol", "roster", "budget", "span_count", "path"]
)
def test_invalid_binding_refuses_before_backend(job, change):
    root, data, config, runtime = job
    protocol_path = Path(config["protocol"]["path"])
    p = json.loads(protocol_path.read_text())
    if change == "protocol":
        config["protocol"]["sha256"] = "d" * 64
    elif change == "roster":
        p["roster_sha256"] = "d" * 64
    elif change == "budget":
        config["plan"]["planned_speech_audio_seconds"] = 0
    elif change == "span_count":
        p["expected_unique_spans"] = 2
    elif change == "path":
        p["output_relpath"] = "../escape.json"
    if change in {"roster", "span_count", "path"}:
        protocol_path.write_bytes(canonical_bytes(p))
        config["protocol"] = pin(protocol_path)
        config["plan"]["protocol_hash"] = config["protocol"]["sha256"]
    with pytest.raises(Exception):
        run_preparation(
            config,
            source_root=root,
            data_root=data,
            backend_factory=lambda *_: pytest.fail("invalid job reached backend"),
        )


def test_prefetch_consumes_exact_spans_in_order():
    sources = [
        {"audio_sha256": str(i), "start_frame": 0, "end_frame": i + 1} for i in range(8)
    ]
    prefetch = BoundedAudioPrefetch(2, reader=lambda source: source["audio_sha256"])
    prefetch.prepare_sources(sources)
    assert prefetch.pending_count == 2
    assert [prefetch.take(s) for s in sources] == [str(i) for i in range(8)]
    assert prefetch.pending_count == 0
    prefetch.close()


def test_lazy_backend_preserves_query_prefix_and_complete_audio(job, monkeypatch):
    root, data, config, runtime = job
    protocol = json.loads(Path(config["protocol"]["path"]).read_text())
    events, rendered = [], []
    monkeypatch.setattr(
        runtime,
        "load_stack",
        lambda *_, **kw: (
            ("processor", "model", "template")
            if kw == {"local_files_only": True}
            else pytest.fail("unbound load")
        ),
    )
    monkeypatch.setattr(
        runtime,
        "render",
        lambda proc, template, content: rendered.append(content) or "rendered",
    )

    def fake_encode(proc, model, texts, audio, **kw):
        assert texts == ["rendered"]
        assert len(audio[0]) == 400
        assert kw["require_complete_audio"] is True
        assert kw["max_audio_samples"] == 1920000
        return [[1, 0]]

    monkeypatch.setattr(runtime, "encode", fake_encode)
    backend = runtime.NemotronSpeechEncoder(
        {"model_dir_relpath": "model"}, protocol, data, events.append
    )
    source = {
        "media_path": str(data / "speech.wav"),
        "source_frames": 400,
        "source_sample_rate_hz": 16000,
        "start_frame": 0,
        "end_frame": 400,
        "audio_sha256": hashlib.sha256((data / "speech.wav").read_bytes()).hexdigest(),
    }
    backend.prepare_sources([source])
    assert backend.stack is None
    assert backend(source) == [1, 0]
    assert rendered == [[{"type": "text", "text": "query: "}, {"type": "audio"}]]
    assert events[:2] == ["model_load_started", "model_load_finished"]
    backend.close()


def test_verify_encoder_refuses_drift_before_loading(tmp_path):
    import speech_aware_evidence_acquisition.core.speech_preparation_runtime as runtime

    directory = tmp_path / "model"
    directory.mkdir()
    names = [
        "config.json",
        "config_sentence_transformers.json",
        "preprocessor_config.json",
        "modeling_nv_omni_embed.py",
        "tokenizer.json",
        "tokenizer_config.json",
        "model.safetensors.index.json",
        "1_Pooling/config.json",
        "additional_chat_templates/sentence_transformers.jinja",
        "weight.safetensors",
    ]
    files = {}
    for name in names:
        p = directory / name
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_text(
            json.dumps({"weight_map": {"w": "weight.safetensors"}})
            if "index" in name
            else "{}"
        )
        files[name] = {"bytes": p.stat().st_size, "sha256": pin(p)["sha256"]}
    inventory = {
        "schema": "saea-pinned-speech-query-encoder-inventory-v1",
        "model_dir_relpath": "model",
        "files": files,
        "packages": {},
    }
    runtime.verify_encoder(inventory, tmp_path)
    (directory / "weight.safetensors").write_text("changed")
    with pytest.raises(Exception, match="size|hash"):
        runtime.verify_encoder(inventory, tmp_path)


def test_wall_budget_refuses_before_first_encoder_contact(job):
    root, data, config, runtime = job
    config["plan"]["planned_gpu_hours"] = 1e-12

    class NoForward(Backend):
        def __call__(self, source):
            pytest.fail("exhausted budget reached encoder")

    with pytest.raises(runtime.SpeechPreparationError, match="budget exhausted"):
        run_preparation(
            config,
            source_root=root,
            data_root=data,
            backend_factory=lambda *_: NoForward(),
        )
    state = json.loads((data / "attempts/TEST-ENCODE/attempt-v1.json").read_text())
    assert state["actual"]["calls"] == 0


def test_preparation_monitor_uses_shared_read_only_telemetry(tmp_path, monkeypatch):
    import threading
    import time
    from speech_aware_evidence_acquisition.core import (
        speech_preparation_runtime as runtime,
    )
    from speech_aware_evidence_acquisition.core.session import serving, telemetry

    sampled = threading.Event()
    monkeypatch.setattr(telemetry, "read_gpu", lambda: {"utilization_percent": 73})

    def host_memory():
        sampled.set()
        return {"available_gb": 20}

    monkeypatch.setattr(serving, "read_host_memory", host_memory)
    path = tmp_path / "monitor.jsonl"
    close = runtime.start_monitor(
        path,
        {
            "started_monotonic": time.monotonic(),
            "calls": 3,
            "phase": "encoder_forward_started",
        },
        10,
    )
    assert sampled.wait(timeout=2)
    close()
    record = json.loads(path.read_text().splitlines()[0])
    assert record["gpu"]["utilization_percent"] == 73
    assert record["busy_slots"] == 1
    assert record["logical_encoder_contacts"] == 3


def test_prepared_overlapping_rows_are_consumed_by_shared_phase_loader(job):
    from speech_aware_evidence_acquisition.rails.phase_supply import (
        load_sealed_segment_vectors,
    )

    root, data, config, runtime = job
    path = Path(config["protocol"]["path"])
    protocol = json.loads(path.read_text())
    protocol.update(max_seconds=0.02, overlap_seconds=0.005, expected_unique_spans=2)
    path.write_bytes(canonical_bytes(protocol))
    config["protocol"] = pin(path)
    config["plan"].update(protocol_hash=pin(path)["sha256"], planned_model_calls=2)
    result = run_preparation(
        config, source_root=root, data_root=data, backend_factory=lambda *_: Backend()
    )
    consumed = load_sealed_segment_vectors(
        Path(result["query_rows_path"]),
        expected_sha256=result["query_rows_sha256"],
        dimensions=("content",),
    )
    assert len(consumed["sample"].segments) == 2
    assert (
        consumed["sample"].audio_sha256
        == hashlib.sha256((data / "speech.wav").read_bytes()).hexdigest()
    )
