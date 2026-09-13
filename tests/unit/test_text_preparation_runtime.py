"""Verify text preparation with real shared custody and entirely synthetic inputs."""

import hashlib
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core import speech_preparation_runtime as runtime
from speech_aware_evidence_acquisition.core.preparation import canonical_bytes
from speech_aware_evidence_acquisition.rails.knowledge import (
    KnowledgeSnapshot,
    KeyFacet,
    ValueBundle,
)
from speech_aware_evidence_acquisition.rails.phase_supply import load_sealed_vectors


def pin(path):
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


@pytest.fixture
def job(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    facets = tuple(
        KeyFacet("facet:" + x, "content", "text", x, ("train:one",))
        for x in ("beta", "alpha")
    )
    values = tuple(
        ValueBundle(
            "value:" + x,
            "synthetic evidence",
            ("facet:" + x,),
            ("train:one",),
            ("source:one",),
        )
        for x in ("beta", "alpha")
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id="synthetic-native-keys",
        source_split_identity_hash="a" * 64,
        source_sample_ids=("train:one",),
        builder_policy_id="synthetic",
        facets=facets,
        values=values,
    ).validate()
    snapshot_path = data / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot.frozen_json(), indent=2) + "\n")
    # A real pretty-printed file hash must differ from the content hash.
    assert pin(snapshot_path)["sha256"] != snapshot.content_hash()
    encoder_path = data / "encoder.json"
    encoder_path.write_text("{}")
    protocol = {
        "schema": "saea-text-facet-encoding-protocol-v1",
        "snapshot": pin(snapshot_path),
        "encoder": pin(encoder_path),
        "expected_positive_content_facets": 2,
        "passage_prompt": "passage: ",
        "dimension": 2048,
        "max_sequence_tokens": 8192,
        "cpu_workers": 1,
        "monitor_interval_seconds": 10,
        "output_relpath": "prepared/index.json",
        "facet_rows_relpath": "prepared/facets.jsonl",
        "cache_relpath": "cache",
    }
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_bytes(canonical_bytes(protocol))
    config = {
        "plan": {
            "run_id": "TEST-TEXT",
            "attempt_id": "encode-v1",
            "schema": "saea-text-encoder-plan-v1",
            "execution_profile": "bounded-discovery-probe",
            "carrier_lock_key": "audio2tool",
            "split_role": "discovery",
            "split_identity_hash": hashlib.sha256(
                b"audio2tool/facet:alpha\naudio2tool/facet:beta"
            ).hexdigest(),
            "planned_model_calls": 2,
            "planned_gpu_hours": 1,
            "planned_speech_audio_seconds": 0,
            "protocol_hash": pin(protocol_path)["sha256"],
        },
        "protocol": pin(protocol_path),
        "umbrella_lock": {"path": str(tmp_path / "lock.json"), "sha256": "b" * 64},
        "session_id": "test-text",
        "study_head": "c" * 40,
    }
    monkeypatch.setattr(runtime, "admit", lambda **_: None)
    monkeypatch.setattr(runtime, "verify_encoder", lambda *_: None)
    monkeypatch.setattr(runtime, "start_monitor", lambda *_: lambda: None)
    return tmp_path, data, config, snapshot


class Backend:
    def __init__(self, data, attempt):
        self.data, self.attempt, self.calls, self.closed = data, attempt, [], False

    def __call__(self, text):
        self.calls.append(text)
        state = json.loads(
            (self.data / "attempts/TEST-TEXT" / (self.attempt + ".json")).read_text()
        )
        assert state["contact_kind"] == "text-encoder"
        assert state["actual"] == {"calls": len(self.calls), "audio_seconds": 0.0}
        assert (self.data / "locks/flight.lock").exists()
        return [1.0] + [0.0] * 2047

    def close(self):
        self.closed = True


def execute(job, backend):
    root, data, config, _ = job
    return runtime.run_text_facet_preparation(
        config, source_root=root, data_root=data, backend_factory=lambda *_: backend
    )


def set_protocol(config, **updates):
    path = Path(config["protocol"]["path"])
    protocol = json.loads(path.read_text())
    protocol.update(updates)
    path.write_bytes(canonical_bytes(protocol))
    config["protocol"] = pin(path)
    config["plan"]["protocol_hash"] = config["protocol"]["sha256"]


def test_real_lifecycle_preserves_two_snapshot_hashes_and_zero_audio(job):
    root, data, config, snapshot = job
    backend = Backend(data, "encode-v1")
    result = execute(job, backend)
    assert backend.calls == ["alpha", "beta"] and backend.closed
    assert result["status"] == "SEALED"
    assert result["logical_encoder_contacts"] == 2
    assert result["actual_speech_audio_seconds"] == 0
    assert result["snapshot_content_sha256"] == snapshot.content_hash()
    assert result["snapshot_sha256"] == pin(data / "snapshot.json")["sha256"]
    assert result["index_sha256"] == pin(data / "prepared/index.json")["sha256"]
    assert result["study_head"] == config["study_head"]
    assert result["elapsed_seconds"] > 0 and result["closed_at"]
    loaded = load_sealed_vectors(
        Path(result["facet_rows_path"]),
        expected_sha256=result["facet_rows_sha256"],
        dimensions=("content",),
    )
    assert list(loaded) == ["facet:alpha", "facet:beta"]
    assert not (data / "locks/flight.lock").exists()
    assert (
        json.loads((data / "attempts/TEST-TEXT/encode-v1.json").read_text())["state"]
        == "FINALIZED"
    )
    index = json.loads((data / "prepared/index.json").read_text())
    assert index["inputs"]["geometry"] == {
        "prompt": "passage: ",
        "audio": False,
        "batch_size": 1,
    }
    assert "facet_dimension" not in result


def test_explicit_second_warm_attempt_spends_zero_contacts(job):
    _, data, config, _ = job
    first = execute(job, Backend(data, "encode-v1"))
    config["plan"]["attempt_id"] = "encode-v2"
    backend = Backend(data, "encode-v2")
    second = execute(job, backend)
    assert backend.calls == []
    assert (
        second["logical_encoder_contacts"] == second["actual_speech_audio_seconds"] == 0
    )
    assert second["facet_rows_sha256"] == first["facet_rows_sha256"]


def test_explicit_alternate_facet_dimension_is_selected_and_emitted(job):
    root, data, config, _ = job
    facets = tuple(
        KeyFacet("boundary:" + x, "intent-boundary", "text", x, ("train:one",))
        for x in ("beta", "alpha")
    )
    snapshot = KnowledgeSnapshot(
        snapshot_id="synthetic-boundary-keys",
        source_split_identity_hash="a" * 64,
        source_sample_ids=("train:one",),
        builder_policy_id="synthetic",
        facets=facets,
        values=tuple(
            ValueBundle(
                "value:" + x,
                "synthetic evidence",
                ("boundary:" + x,),
                ("train:one",),
                ("source:one",),
            )
            for x in ("beta", "alpha")
        ),
    ).validate()
    snapshot_path = data / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot.frozen_json(), indent=2) + "\n")
    set_protocol(
        config,
        snapshot=pin(snapshot_path),
        facet_dimension="intent-boundary",
    )
    config["plan"]["split_identity_hash"] = hashlib.sha256(
        b"audio2tool/boundary:alpha\naudio2tool/boundary:beta"
    ).hexdigest()

    backend = Backend(data, "encode-v1")
    result = execute(job, backend)

    assert backend.calls == ["alpha", "beta"]
    assert result["facet_dimension"] == "intent-boundary"
    loaded = load_sealed_vectors(
        Path(result["facet_rows_path"]),
        expected_sha256=result["facet_rows_sha256"],
        dimensions=("intent-boundary",),
    )
    assert set(loaded["boundary:alpha"]["intent-boundary"]) == {0.0, 1.0}


def test_dimension_bound_index_refuses_a_different_dimension_before_encoding(job):
    root, data, config, original_snapshot = job
    facets = tuple(
        KeyFacet("boundary:" + x, "intent-boundary", "text", x, ("train:one",))
        for x in ("beta", "alpha")
    )
    alternate = KnowledgeSnapshot(
        snapshot_id="synthetic-boundary-keys",
        source_split_identity_hash="a" * 64,
        source_sample_ids=("train:one",),
        builder_policy_id="synthetic",
        facets=facets,
        values=tuple(
            ValueBundle(
                "value:" + x,
                "synthetic evidence",
                ("boundary:" + x,),
                ("train:one",),
                ("source:one",),
            )
            for x in ("beta", "alpha")
        ),
    ).validate()
    snapshot_path = data / "snapshot.json"
    snapshot_path.write_text(json.dumps(alternate.frozen_json(), indent=2) + "\n")
    set_protocol(
        config,
        snapshot=pin(snapshot_path),
        facet_dimension="intent-boundary",
    )
    config["plan"]["split_identity_hash"] = hashlib.sha256(
        b"audio2tool/boundary:alpha\naudio2tool/boundary:beta"
    ).hexdigest()
    execute(job, Backend(data, "encode-v1"))

    snapshot_path.write_text(
        json.dumps(original_snapshot.frozen_json(), indent=2) + "\n"
    )
    set_protocol(config, snapshot=pin(snapshot_path), facet_dimension="content")
    config["plan"].update(
        attempt_id="encode-v2",
        split_identity_hash=hashlib.sha256(
            b"audio2tool/facet:alpha\naudio2tool/facet:beta"
        ).hexdigest(),
    )
    backend = Backend(data, "encode-v2")
    with pytest.raises(Exception):
        execute(job, backend)
    assert backend.calls == []


@pytest.mark.parametrize(
    "change",
    ["snapshot", "roster", "count", "budget", "path", "schema", "audio", "prompt"],
)
def test_invalid_text_job_refuses_before_backend(job, change):
    _, data, config, _ = job
    path = Path(config["protocol"]["path"])
    protocol = json.loads(path.read_text())
    if change == "snapshot":
        (data / "snapshot.json").write_text("{}")
    elif change == "roster":
        config["plan"]["split_identity_hash"] = "d" * 64
    elif change == "count":
        protocol["expected_positive_content_facets"] = 3
    elif change == "budget":
        config["plan"]["planned_model_calls"] = 1
    elif change == "path":
        protocol["facet_rows_relpath"] = "../escape.json"
    elif change == "schema":
        config["plan"].update(
            schema="saea-execution-plan-v1", planned_speech_audio_seconds=1
        )
    elif change == "audio":
        config["plan"]["planned_speech_audio_seconds"] = 1
    elif change == "prompt":
        protocol["passage_prompt"] = "query: "
    path.write_bytes(canonical_bytes(protocol))
    config["protocol"] = pin(path)
    config["plan"]["protocol_hash"] = pin(path)["sha256"]
    backend = Backend(data, "encode-v1")
    with pytest.raises(Exception):
        execute(job, backend)
    assert backend.calls == []
    assert not (data / "attempts").exists()


def test_failure_keeps_spent_attempt_and_refuses_reentry(job):
    _, data, _, _ = job

    class Failed(Backend):
        def __call__(self, text):
            super().__call__(text)
            raise RuntimeError("synthetic text forward failure")

    backend = Failed(data, "encode-v1")
    with pytest.raises(RuntimeError, match="synthetic"):
        execute(job, backend)
    state = json.loads((data / "attempts/TEST-TEXT/encode-v1.json").read_text())
    assert state["state"] == "ABORTED"
    assert state["actual"] == {"calls": 1, "audio_seconds": 0.0}
    assert (data / "locks/flight.lock").exists()
    assert list((data / "cache").glob("*.encoder-started.json"))
    with pytest.raises(Exception):
        execute(job, backend)
    assert backend.calls == ["alpha"]
