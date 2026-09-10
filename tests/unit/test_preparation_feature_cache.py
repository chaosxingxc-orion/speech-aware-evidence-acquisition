"""Synthetic model-free legacy cache audit coverage."""

from __future__ import annotations

import hashlib
import struct
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.core.model import (
    legacy_audio_feature_cache_key,
)
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_feature_cache import (
    FEATURE_CACHE_AUDIT_STATE,
    build_feature_cache_audit,
    prepare_feature_cache_audit,
)
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WindowFeatureEncoderIdentity,
    WindowRequestBatch,
)


def _identity(marker: str = "a") -> WindowFeatureEncoderIdentity:
    return WindowFeatureEncoderIdentity(
        runtime_receipt_sha256=marker * 64,
        build_commit="b" * 40,
        decoder_gguf_sha256="c" * 64,
        mmproj_sha256="d" * 64,
    )


def _batch(root, *, run: str, audio: bytes = b"synthetic exact window"):
    parent_relpath = "datasets/e21/sample-1.wav"
    parent = root / parent_relpath
    parent.parent.mkdir(parents=True, exist_ok=True)
    parent.write_bytes(b"synthetic parent")
    media_relpath = f"derived/obs-slices/{run}/sample-1/i0000.wav"
    media = root / media_relpath
    media.parent.mkdir(parents=True, exist_ok=True)
    media.write_bytes(audio)
    source = {
        "sample_id": "sample-1",
        "parent_media_relpath": parent_relpath,
        "parent_sha256": hashlib.sha256(parent.read_bytes()).hexdigest(),
        "start_seconds": 10.0,
        "end_seconds": 11.0,
        "audio_seconds": 1.0,
        "sample_rate_hz": 16_000,
        "media_relpath": media_relpath,
        "sha256": hashlib.sha256(audio).hexdigest(),
        "bytes": len(audio),
        "iteration": 0,
        "preprocess": [],
        "pre_sha256": None,
    }
    payload = {
        "request_id": f"request-{run}",
        "sample_id": "sample-1",
        "media_relpath": media_relpath,
        "audio_seconds": 1.0,
        "sample_rate_hz": 16_000,
        "messages": [{"role": "system", "content": "Synthetic request."}],
    }
    return WindowRequestBatch(
        payloads=(payload,),
        request_keys=("sample-1#w0001",),
        source_bindings=(source,),
    )


def _write_chunk(cache_dir, audio: bytes, ordinal: int = 0, *, n_tokens=2, n_embd=4):
    key = legacy_audio_feature_cache_key(audio)
    feature = b"\x00" * (n_tokens * n_embd * 4)
    path = cache_dir / f"{key}_o{ordinal}.feat"
    path.write_bytes(struct.pack("<QQ", n_tokens, n_embd) + feature)
    return path


def _write_cache_for_batches(root, cache_dir, batches):
    for batch in batches.values():
        audio_path = root / batch.source_bindings[0]["media_relpath"]
        _write_chunk(cache_dir, audio_path.read_bytes())


def test_complete_deduplicated_audit_preserves_all_request_references(tmp_path):
    batches = {
        "arm-a": _batch(tmp_path, run="a"),
        "arm-b": _batch(tmp_path, run="b"),
    }
    cache = tmp_path / "legacy-cache"
    cache.mkdir()
    _write_cache_for_batches(tmp_path, cache, batches)

    audit = build_feature_cache_audit(
        batches=batches,
        data_root=tmp_path,
        encoder_identity=_identity(),
        legacy_cache_dir=cache,
        expected_n_embd=4,
    )

    assert audit["state"] == FEATURE_CACHE_AUDIT_STATE
    assert audit["inventory_sha256"]
    assert audit["legacy_cache_dir"] == str(cache.resolve())
    assert len(audit["entries"]) == 1
    assert audit["entries"][0]["requests"] == [
        {"batch": "arm-a", "request_key": "sample-1#w0001"},
        {"batch": "arm-b", "request_key": "sample-1#w0001"},
    ]
    assert audit["entries"][0]["chunks"][0]["n_embd"] == 4


@pytest.mark.parametrize(
    "mutation",
    ["missing", "wrong-dimension", "wrong-length", "trailing"],
)
def test_audit_rejects_malformed_or_missing_chunks(tmp_path, mutation):
    batch = _batch(tmp_path, run="a")
    cache = tmp_path / "legacy-cache"
    cache.mkdir()
    audio = (tmp_path / batch.source_bindings[0]["media_relpath"]).read_bytes()
    path = _write_chunk(cache, audio)
    if mutation == "missing":
        path.unlink()
    elif mutation == "wrong-dimension":
        path.write_bytes(struct.pack("<QQ", 2, 3) + b"\x00" * 24)
    elif mutation == "wrong-length":
        path.write_bytes(struct.pack("<QQ", 2, 4) + b"\x00" * 31)
    else:
        path.write_bytes(path.read_bytes() + b"\x00")

    with pytest.raises(PreparationError):
        build_feature_cache_audit(
            batches={"arm": batch},
            data_root=tmp_path,
            encoder_identity=_identity(),
            legacy_cache_dir=cache,
            expected_n_embd=4,
        )


def test_prepare_artifact_refuses_stale_cache_bytes(tmp_path):
    batch = _batch(tmp_path, run="a")
    cache = tmp_path / "legacy-cache"
    cache.mkdir()
    audio = (tmp_path / batch.source_bindings[0]["media_relpath"]).read_bytes()
    path = _write_chunk(cache, audio)
    artifact = tmp_path / "audit.json"

    first = prepare_feature_cache_audit(
        artifact,
        batches={"arm": batch},
        data_root=tmp_path,
        encoder_identity=_identity(),
        legacy_cache_dir=cache,
        expected_n_embd=4,
    )
    assert first["cache"] == "cold"
    path.write_bytes(path.read_bytes()[:-1] + b"")
    with pytest.raises(PreparationError, match="artifact identity mismatch"):
        prepare_feature_cache_audit(
            artifact,
            batches={"arm": batch},
            data_root=tmp_path,
            encoder_identity=_identity(),
            legacy_cache_dir=cache,
            expected_n_embd=4,
        )


def test_audit_refuses_distinct_audio_with_ambiguous_legacy_key(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_feature_cache as audit_module

    batches = {
        "arm-a": _batch(tmp_path, run="a", audio=b"first"),
        "arm-b": _batch(tmp_path, run="b", audio=b"second"),
    }
    cache = tmp_path / "legacy-cache"
    cache.mkdir()
    _write_cache_for_batches(tmp_path, cache, batches)
    original = audit_module.inspect_legacy_cached_speech_feature_cache

    def collision(**kwargs):
        result = original(**kwargs)
        return replace(result, cache_key="ambiguous")

    monkeypatch.setattr(audit_module, "inspect_legacy_cached_speech_feature_cache", collision)
    with pytest.raises(PreparationError, match="ambiguous legacy cache key"):
        build_feature_cache_audit(
            batches=batches,
            data_root=tmp_path,
            encoder_identity=_identity(),
            legacy_cache_dir=cache,
            expected_n_embd=4,
        )


def test_audit_refuses_concurrent_chunk_mutation(tmp_path, monkeypatch):
    import speech_aware_evidence_acquisition.core.preparation_feature_cache as audit_module

    batch = _batch(tmp_path, run="a")
    cache = tmp_path / "legacy-cache"
    cache.mkdir()
    audio = (tmp_path / batch.source_bindings[0]["media_relpath"]).read_bytes()
    path = _write_chunk(cache, audio)
    original = audit_module.inspect_legacy_cached_speech_feature_cache

    def mutate_after_inspection(**kwargs):
        result = original(**kwargs)
        path.write_bytes(path.read_bytes()[:-1] + b"")
        return result

    monkeypatch.setattr(
        audit_module, "inspect_legacy_cached_speech_feature_cache",
        mutate_after_inspection,
    )
    with pytest.raises(PreparationError, match="changed during audit"):
        build_feature_cache_audit(
            batches={"arm": batch},
            data_root=tmp_path,
            encoder_identity=_identity(),
            legacy_cache_dir=cache,
            expected_n_embd=4,
        )
