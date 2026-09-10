"""Model-free exact-window inventory over synthetic request batches."""

from __future__ import annotations

import hashlib
import json
import wave
from dataclasses import replace

import pytest

from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_windows import (
    WindowFeatureEncoderIdentity,
    WindowRequestBatch,
    build_window_feature_inventory,
    prepare_window_feature_inventory,
)


def _identity(marker: str = "a") -> WindowFeatureEncoderIdentity:
    return WindowFeatureEncoderIdentity(
        runtime_receipt_sha256=marker * 64,
        build_commit="b" * 40,
        decoder_gguf_sha256="c" * 64,
        mmproj_sha256="d" * 64,
    )


def _batch(
    root,
    *,
    run: str,
    audio: bytes = b"synthetic exact window",
    request_keys=("sample-1#w0001",),
    source_overrides=None,
    payload_overrides=None,
) -> WindowRequestBatch:
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
    source.update(source_overrides or {})
    payload = {
        "request_id": f"request-{run}",
        "sample_id": "sample-1",
        "media_relpath": media_relpath,
        "audio_seconds": 1.0,
        "sample_rate_hz": 16_000,
        "messages": [{"role": "system", "content": "Synthetic request."}],
    }
    payload.update(payload_overrides or {})
    return WindowRequestBatch(
        payloads=tuple(dict(payload) for _ in request_keys),
        request_keys=tuple(request_keys),
        source_bindings=tuple(dict(source) for _ in request_keys),
    )


def test_cross_arm_audio_is_deduplicated_across_distinct_run_paths(tmp_path):
    batches = {
        "dr-direct": _batch(tmp_path, run="run-direct"),
        "dr-delivery": _batch(tmp_path, run="run-delivery"),
    }

    inventory = build_window_feature_inventory(
        batches=batches, data_root=tmp_path, encoder_identity=_identity()
    )

    assert inventory["state"] == "inputs-verified-features-not-materialized"
    assert inventory["request_count"] == 2
    assert inventory["unique_audio_count"] == 1
    assert [row["name"] for row in inventory["batches"]] == [
        "dr-delivery",
        "dr-direct",
    ]
    encoded = inventory["encoding_inputs"][0]
    assert encoded["audio_byte_count"] == len(b"synthetic exact window")
    assert encoded["requests"] == [
        {"batch": "dr-delivery", "request_key": "sample-1#w0001"},
        {"batch": "dr-direct", "request_key": "sample-1#w0001"},
    ]
    provenances = [
        batch["requests"][0]["source_provenance"]
        for batch in inventory["batches"]
    ]
    assert provenances[0]["media_relpath"] != provenances[1]["media_relpath"]
    assert provenances[0]["sha256"] == provenances[1]["sha256"]


def test_changed_audio_with_matching_source_identity_is_not_deduplicated(tmp_path):
    batches = {
        "arm-a": _batch(tmp_path, run="run-a"),
        "arm-b": _batch(tmp_path, run="run-b", audio=b"different exact window"),
    }

    inventory = build_window_feature_inventory(
        batches=batches, data_root=tmp_path, encoder_identity=_identity()
    )

    assert inventory["request_count"] == 2
    assert inventory["unique_audio_count"] == 2
    assert len({row["encoding_key_sha256"] for row in inventory["encoding_inputs"]}) == 2


@pytest.mark.parametrize("mutation", ["claimed-hash", "changed-bytes"])
def test_changed_window_media_or_claimed_hash_is_refused(tmp_path, mutation):
    batch = _batch(tmp_path, run="run-a")
    if mutation == "claimed-hash":
        source = dict(batch.source_bindings[0], sha256="e" * 64)
        batch = replace(batch, source_bindings=(source,))
    else:
        (tmp_path / batch.source_bindings[0]["media_relpath"]).write_bytes(b"changed")

    with pytest.raises(PreparationError, match="sha256 differs from actual bytes"):
        build_window_feature_inventory(
            batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity()
        )


def test_foreign_window_path_is_refused(tmp_path):
    outside = tmp_path.parent / "foreign-window.wav"
    outside.write_bytes(b"foreign")
    batch = _batch(
        tmp_path,
        run="run-a",
        source_overrides={
            "media_relpath": "../foreign-window.wav",
            "sha256": hashlib.sha256(b"foreign").hexdigest(),
            "bytes": len(b"foreign"),
        },
        payload_overrides={"media_relpath": "../foreign-window.wav"},
    )

    with pytest.raises(PreparationError, match="traversal"):
        build_window_feature_inventory(
            batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity()
        )


@pytest.mark.parametrize(
    "payload_overrides, message",
    [
        ({"sample_id": "foreign-sample"}, "sample ids differ"),
        ({"media_relpath": "derived/other.wav"}, "media paths differ"),
    ],
)
def test_payload_source_mismatch_is_refused(tmp_path, payload_overrides, message):
    batch = _batch(
        tmp_path, run="run-a", payload_overrides=payload_overrides
    )

    with pytest.raises(PreparationError, match=message):
        build_window_feature_inventory(
            batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity()
        )


def test_request_key_window_suffix_must_bind_source_iteration(tmp_path):
    batch = _batch(tmp_path, run="run-a", request_keys=("sample-1#w0002",))

    with pytest.raises(PreparationError, match="suffix disagrees"):
        build_window_feature_inventory(
            batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity()
        )


@pytest.mark.parametrize(
    "payload_overrides, message",
    [
        ({"audio_seconds": 1.5}, "audio_seconds disagrees"),
        ({"sample_rate_hz": 8_000}, "sample_rate_hz disagrees"),
    ],
)
def test_payload_audio_facts_must_bind_source(
    tmp_path, payload_overrides, message
):
    batch = _batch(
        tmp_path, run="run-a", payload_overrides=payload_overrides
    )

    with pytest.raises(PreparationError, match=message):
        build_window_feature_inventory(
            batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity()
        )


def test_non_string_batch_name_is_refused_before_sorting(tmp_path):
    batch = _batch(tmp_path, run="run-a")

    with pytest.raises(PreparationError, match="batch name"):
        build_window_feature_inventory(
            batches={1: batch, "arm": batch},
            data_root=tmp_path,
            encoder_identity=_identity(),
        )


def test_real_materialized_repair_windows_feed_inventory(tmp_path, monkeypatch):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.preparation_windows import (
        materialize_window_requests,
    )
    from speech_aware_evidence_acquisition.reproduction.repair_loop import (
        RepairWindowHook,
    )
    from test_obs_loop_policy import SAMPLE_ID, _World, _config_values, _noise

    values = _config_values(
        obs_boundary_mode="fixed",
        obs_vad_trim_min_seconds=0,
        obs_condition_tail_chars=0,
        obs_batch_slices=3,
        obs_slice_tail_silence_seconds=2.0,
    )
    world = _World(
        tmp_path,
        monkeypatch,
        pcm=_noise(90),
        texts=[],
        values=values,
    )
    hook = RepairWindowHook(
        sample_id=SAMPLE_ID,
        predecessors=[
            SimpleNamespace(start_seconds=0, end_seconds=60, text="draft first"),
            SimpleNamespace(start_seconds=60, end_seconds=90, text="draft final"),
        ],
        frame="Correct this draft: {predecessor}",
        rule=lambda *args: pytest.fail("inventory must not deliver a response"),
    )

    batch = materialize_window_requests(
        [world.ctx],
        expected_sample_ids=[SAMPLE_ID],
        hook_factory=lambda *args: hook,
    )
    inventory = build_window_feature_inventory(
        batches={"repair": batch},
        data_root=world.data_root,
        encoder_identity=_identity(),
    )

    assert inventory["request_count"] == 2
    assert inventory["unique_audio_count"] == 2
    assert not world.adapter.payloads
    assert not hook.outcomes
    rows = inventory["batches"][0]["requests"]
    with wave.open(
        str(world.data_root / batch.payloads[0]["media_relpath"]), "rb"
    ) as handle:
        written_seconds = handle.getnframes() / handle.getframerate()
    assert written_seconds == pytest.approx(batch.payloads[0]["audio_seconds"] + 2.0)
    assert batch.source_bindings[0]["preprocess"] == ["tail-silence-2s"]

    for index, (row, payload, source) in enumerate(
        zip(rows, batch.payloads, batch.source_bindings, strict=True), start=1
    ):
        assert row["request_key"] == f"{SAMPLE_ID}#w{index:04d}"
        assert row["source_provenance"]["audio_seconds"] == payload["audio_seconds"]
        assert row["source_provenance"]["sample_rate_hz"] == payload["sample_rate_hz"]
        assert row["source_provenance"]["sha256"] == source["sha256"]


def test_duplicate_request_keys_are_refused(tmp_path):
    batch = _batch(
        tmp_path,
        run="run-a",
        request_keys=("sample-1#w0001", "sample-1#w0001"),
    )

    with pytest.raises(PreparationError, match="repeats a request key"):
        build_window_feature_inventory(
            batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity()
        )


def test_changed_encoder_identity_cannot_reuse_prepared_inventory(tmp_path):
    batch = _batch(tmp_path, run="run-a")
    first = build_window_feature_inventory(
        batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity("a")
    )
    second = build_window_feature_inventory(
        batches={"arm": batch}, data_root=tmp_path, encoder_identity=_identity("e")
    )
    assert (
        first["encoding_inputs"][0]["encoding_key_sha256"]
        != second["encoding_inputs"][0]["encoding_key_sha256"]
    )

    artifact = tmp_path / "prepared" / "window-inventory.json"
    cold = prepare_window_feature_inventory(
        artifact,
        batches={"arm": batch},
        data_root=tmp_path,
        encoder_identity=_identity("a"),
    )
    document = json.loads(artifact.read_text(encoding="utf-8"))
    assert cold["cache"] == "cold"
    assert document["contact_class"] == "model-free"
    assert document["output"]["state"] == (
        "inputs-verified-features-not-materialized"
    )

    with pytest.raises(PreparationError, match="artifact identity mismatch"):
        prepare_window_feature_inventory(
            artifact,
            batches={"arm": batch},
            data_root=tmp_path,
            encoder_identity=_identity("e"),
        )


def test_parallel_calls_overlap_and_preserve_exact_sequential_batch(tmp_path, monkeypatch):
    import threading
    from speech_aware_evidence_acquisition.core.preparation_windows import materialize_window_requests
    from speech_aware_evidence_acquisition.reproduction import obs_loop
    from test_obs_loop_policy import _World, _config_values, _noise
    pcm = _noise(0.04)
    values = _config_values(obs_boundary_mode="fixed", obs_vad_trim_min_seconds=0,
                            obs_condition_tail_chars=0, obs_batch_slices=2)
    worlds = [_World(tmp_path / str(i), monkeypatch, pcm=pcm, texts=[],
                     values=values, sample_id=str(4000001+i)) for i in range(2)]
    contexts = [w.ctx for w in worlds]
    ids = [w.sample_id for w in worlds]
    serial = materialize_window_requests(contexts, expected_sample_ids=ids, hook_factory=lambda *args: None)
    from speech_aware_evidence_acquisition.core.model.slices import SliceRegistry
    from test_obs_loop_policy import RUN_ID
    for world in worlds:
        world.ctx.extras["slice_registry"] = SliceRegistry(
            data_root=world.data_root, run_id=RUN_ID,
            parent_facts={world.sample_id: (world.parent_relpath, world.duration)},
        )
    barrier = threading.Barrier(2)
    def decode(path, rate):
        barrier.wait(timeout=5)
        return pcm
    monkeypatch.setattr(obs_loop, "decode_parent_pcm", decode)
    parallel = materialize_window_requests(contexts, expected_sample_ids=ids, max_workers=2, hook_factory=lambda *args: None)
    assert parallel == serial
    assert not any(w.adapter.payloads for w in worlds)


@pytest.mark.parametrize("workers", [0, -1, 21, True, 2.5])
def test_window_parallel_worker_budget_refuses_invalid_values(tmp_path, monkeypatch, workers):
    from speech_aware_evidence_acquisition.core.preparation_windows import materialize_window_requests
    from test_obs_loop_policy import _World, _config_values, _noise
    world = _World(tmp_path, monkeypatch, pcm=_noise(0.01), texts=[],
                   values=_config_values(obs_boundary_mode="fixed"))
    with pytest.raises(PreparationError, match="max_workers"):
        materialize_window_requests([world.ctx], expected_sample_ids=[world.sample_id],
                                    max_workers=workers)
