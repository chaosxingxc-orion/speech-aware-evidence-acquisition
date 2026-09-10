"""Model-free tests for exact-window formal packet promotion."""

from __future__ import annotations

import hashlib
import json
import struct

import pytest

from speech_aware_evidence_acquisition.core.model import legacy_audio_feature_cache_key
from speech_aware_evidence_acquisition.core.preparation import PreparationError, digest, prepare_artifact
from speech_aware_evidence_acquisition.core.preparation_feature_cache import (
    FEATURE_CACHE_AUDIT_KIND, build_feature_cache_audit,
)
from speech_aware_evidence_acquisition.core.preparation_feature_provenance import (
    PROVENANCE_KIND, PROVENANCE_SCHEMA, PROVENANCE_STATE,
)
from speech_aware_evidence_acquisition.core.preparation_window_packets import (
    load_prepared_window_feature_packets, prepare_window_feature_packets,
)
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WindowFeatureEncoderIdentity, WindowRequestBatch, prepare_window_feature_inventory,
)


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _identity() -> WindowFeatureEncoderIdentity:
    return WindowFeatureEncoderIdentity("a" * 64, "b" * 40, "c" * 64, "d" * 64)


def _batch(root, run: str, *, audio=b"same exact window", start=10.0):
    parent_rel = "datasets/e21/sample.wav"
    parent = root / parent_rel
    parent.parent.mkdir(parents=True, exist_ok=True)
    parent.write_bytes(b"parent")
    media_rel = f"derived/obs-slices/{run}/sample/i0000.wav"
    media = root / media_rel
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(audio)
    source = {
        "sample_id": "sample", "parent_media_relpath": parent_rel,
        "parent_sha256": _sha(parent.read_bytes()),
        "start_seconds": start, "end_seconds": start + 1.0, "audio_seconds": 1.0,
        "sample_rate_hz": 16000, "media_relpath": media_rel, "sha256": _sha(audio),
        "bytes": len(audio), "iteration": 0, "preprocess": [], "pre_sha256": None,
    }
    payload = {
        "request_id": f"{run}-request", "sample_id": "sample",
        "media_relpath": media_rel, "audio_seconds": 1.0, "sample_rate_hz": 16000,
        "task_instruction": f"different draft text for {run}",
    }
    return WindowRequestBatch((payload,), ("sample#w0001",), (source,))


def _write_cache(cache, audio: bytes):
    cache.mkdir(exist_ok=True)
    key = legacy_audio_feature_cache_key(audio)
    (cache / f"{key}_o0.feat").write_bytes(struct.pack("<QQ", 2, 4) + b"\0" * 32)


def _chain(tmp_path, *, batches=None):
    batches = batches or {"arm-a": _batch(tmp_path, "a"), "arm-b": _batch(tmp_path, "b")}
    identity = _identity()
    inventory_path = tmp_path / "inventory.json"
    inventory_ref = prepare_window_feature_inventory(
        inventory_path, batches=batches, data_root=tmp_path, encoder_identity=identity,
    )
    cache = tmp_path / "cache"
    _write_cache(cache, b"same exact window")
    audit = build_feature_cache_audit(
        batches=batches, data_root=tmp_path, encoder_identity=identity,
        legacy_cache_dir=cache, expected_n_embd=4,
    )
    audit_path = tmp_path / "audit.json"
    audit_ref = prepare_artifact(
        audit_path, kind=FEATURE_CACHE_AUDIT_KIND, inputs=audit["inputs"],
        producer=lambda: {key: value for key, value in audit.items() if key != "inputs"},
    )
    audit_output = json.loads(audit_path.read_text())["output"]
    features = [
        {"audio_sha256": entry["audio_sha256"], "cache_key": entry["cache_key"],
         "chunks": entry["chunks"]}
        for entry in audit_output["entries"]
    ]
    provenance = {
        "schema": PROVENANCE_SCHEMA, "state": PROVENANCE_STATE,
        "study": "speech-aware-evidence-acquisition", "run_id": "encoder-run",
        "attempt_id": "encoder-attempt", "session_id": "encoder-session",
        "runtime_receipt_file_sha256": "a" * 64,
        "runtime_receipt_document_sha256": "e" * 64,
        "session_receipt_file_sha256": "f" * 64, "stop_receipt_file_sha256": "1" * 64,
        "encoding_record_file_sha256": "2" * 64,
        "cache_audit_file_sha256": audit_ref["sha256"],
        "inventory_sha256": audit_output["inventory_sha256"],
        "encoder_identity": identity.as_json(), "trace_manifest_hash": "3" * 64,
        "cost": {"calls_used": 1}, "current_contact_count": 1,
        "unique_audio_count": len(features),
        "entries": [
            {"audio_sha256": item["audio_sha256"], "cache_key": item["cache_key"],
             "status": "encoded", "success": True, "current_contact_id": "contact-1",
             "source_contact_id": None, "source_provenance_receipt_sha256": None}
            for item in features
        ],
        "feature_outputs": features,
    }
    provenance_path = tmp_path / "provenance.json"
    provenance_ref = prepare_artifact(
        provenance_path, kind=PROVENANCE_KIND, inputs={"chain": "synthetic"},
        producer=lambda: provenance,
    )
    return {
        "inventory_path": inventory_path, "inventory_sha256": inventory_ref["sha256"],
        "cache_audit_path": audit_path, "cache_audit_sha256": audit_ref["sha256"],
        "provenance_path": provenance_path, "provenance_sha256": provenance_ref["sha256"],
        "data_root": tmp_path, "feature_root": tmp_path / "packets", "workers": 2,
    }


def test_deduplicates_run_owned_sources_and_warm_load_is_model_free(tmp_path, monkeypatch):
    kwargs = _chain(tmp_path)
    output = tmp_path / "promotion.json"
    ref = prepare_window_feature_packets(output, **kwargs)
    prepared = load_prepared_window_feature_packets(output, ref["sha256"], tmp_path)

    assert prepared.unique_packet_count == 1
    assert tuple(prepared.by_request_key) == ("sample#w0001",)
    binding = prepared.by_request_key["sample#w0001"]
    assert binding.source_key == f"sample#w0001@{_sha(b'same exact window')}"
    assert binding.packet_id == f"window-audio/{binding.audio_sha256[:2]}/{binding.audio_sha256}"
    assert len(binding.sources) == 2
    assert {source["batch"] for source in binding.sources} == {"arm-a", "arm-b"}
    binding.validate_source(binding.sources[0]["source_provenance"])
    with pytest.raises(TypeError):
        prepared.by_request_key["other"] = binding

    import speech_aware_evidence_acquisition.core.preparation_window_packets as module
    monkeypatch.setattr(
        module, "materialize_legacy_cached_speech_feature_packets",
        lambda **_kwargs: pytest.fail("warm prepared artifact reran packet promotion"),
    )
    assert prepare_window_feature_packets(output, **kwargs)["cache"] == "warm"


@pytest.mark.parametrize("name", ["inventory", "cache_audit", "provenance"])
def test_refuses_wrong_artifact_hash(tmp_path, name):
    kwargs = _chain(tmp_path)
    kwargs[f"{name}_sha256"] = "0" * 64
    with pytest.raises(PreparationError, match="hash"):
        prepare_window_feature_packets(tmp_path / "promotion.json", **kwargs)


def _rewrite_artifact(path, mutate):
    document = json.loads(path.read_text())
    mutate(document["output"])
    document["output_sha256"] = digest(document["output"])
    path.write_bytes(json.dumps(
        document, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode())
    return _sha(path.read_bytes())


def test_refuses_missing_audit_request_coverage(tmp_path):
    kwargs = _chain(tmp_path)
    kwargs["cache_audit_sha256"] = _rewrite_artifact(
        kwargs["cache_audit_path"], lambda output: output["entries"][0]["requests"].pop(),
    )
    kwargs["provenance_sha256"] = _rewrite_artifact(
        kwargs["provenance_path"],
        lambda output: output.__setitem__(
            "cache_audit_file_sha256", kwargs["cache_audit_sha256"]
        ),
    )
    with pytest.raises(PreparationError, match="coverage"):
        prepare_window_feature_packets(tmp_path / "promotion.json", **kwargs)


def test_refuses_request_key_collision_with_changed_source(tmp_path):
    batches = {"arm-a": _batch(tmp_path, "a"), "arm-b": _batch(tmp_path, "b", start=11.0)}
    kwargs = _chain(tmp_path, batches=batches)
    with pytest.raises(PreparationError, match="request key.*source"):
        prepare_window_feature_packets(tmp_path / "promotion.json", **kwargs)


def test_refuses_changed_feature_descriptor(tmp_path):
    kwargs = _chain(tmp_path)
    kwargs["provenance_sha256"] = _rewrite_artifact(
        kwargs["provenance_path"],
        lambda output: output["feature_outputs"][0]["chunks"][0].__setitem__(
            "file_sha256", "9" * 64
        ),
    )
    with pytest.raises(PreparationError, match="feature descriptors"):
        prepare_window_feature_packets(tmp_path / "promotion.json", **kwargs)


def test_loader_refuses_changed_source_and_parent(tmp_path):
    kwargs = _chain(tmp_path)
    output = tmp_path / "promotion.json"
    ref = prepare_window_feature_packets(output, **kwargs)
    source = tmp_path / "derived/obs-slices/a/sample/i0000.wav"
    source.write_bytes(b"changed source!")
    with pytest.raises(PreparationError, match="source differs"):
        load_prepared_window_feature_packets(output, ref["sha256"], tmp_path)


def test_binding_accepts_new_run_path_but_refuses_changed_source_identity(tmp_path):
    kwargs = _chain(tmp_path)
    output = tmp_path / "promotion.json"
    ref = prepare_window_feature_packets(output, **kwargs)
    prepared = load_prepared_window_feature_packets(output, ref["sha256"], tmp_path)
    binding = prepared.by_request_key["sample#w0001"]
    source = dict(binding.sources[0]["source_provenance"])
    source["media_relpath"] = "derived/obs-slices/new-run/sample/i0000.wav"
    binding.validate_source(source)
    for field, value in (
        ("sha256", "8" * 64),
        ("start_seconds", 11.0),
        ("parent_sha256", "7" * 64),
    ):
        changed = dict(source)
        changed[field] = value
        with pytest.raises(PreparationError, match="source"):
            binding.validate_source(changed)

def test_refuses_duplicate_audit_coverage_before_writes(tmp_path):
    kwargs = _chain(tmp_path)
    kwargs["cache_audit_sha256"] = _rewrite_artifact(
        kwargs["cache_audit_path"],
        lambda output: output["entries"].append(dict(output["entries"][0])),
    )
    kwargs["provenance_sha256"] = _rewrite_artifact(
        kwargs["provenance_path"],
        lambda output: output.__setitem__(
            "cache_audit_file_sha256", kwargs["cache_audit_sha256"]
        ),
    )
    with pytest.raises(PreparationError, match="duplicate"):
        prepare_window_feature_packets(tmp_path / "promotion.json", **kwargs)
    assert not kwargs["feature_root"].exists()

@pytest.mark.parametrize("workers", [0, 21, True])
def test_refuses_invalid_worker_count_before_promotion(tmp_path, workers):
    kwargs = _chain(tmp_path)
    kwargs["workers"] = workers
    with pytest.raises(PreparationError, match="workers"):
        prepare_window_feature_packets(tmp_path / "promotion.json", **kwargs)
    assert not kwargs["feature_root"].exists()


def test_binding_refuses_unregistered_request(tmp_path):
    kwargs = _chain(tmp_path)
    output = tmp_path / "promotion.json"
    ref = prepare_window_feature_packets(output, **kwargs)
    prepared = load_prepared_window_feature_packets(output, ref["sha256"], tmp_path)
    source = prepared.bindings[0].sources[0]["source_provenance"]
    with pytest.raises(PreparationError, match="no formal packet"):
        prepared.binding_for("foreign#w0001", source)


def test_loader_refuses_changed_formal_packet_bytes(tmp_path):
    kwargs = _chain(tmp_path)
    output = tmp_path / "promotion.json"
    ref = prepare_window_feature_packets(output, **kwargs)
    prepared = load_prepared_window_feature_packets(output, ref["sha256"], tmp_path)
    packet = prepared.bindings[0]
    feature = kwargs["feature_root"] / packet.packet_id / "chunks/0000.f32"
    feature.write_bytes(feature.read_bytes()[:-1] + b"x")
    with pytest.raises(Exception, match="SHA-256|packet"):
        load_prepared_window_feature_packets(output, ref["sha256"], tmp_path)