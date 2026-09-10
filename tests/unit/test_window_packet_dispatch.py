"""Source-complete window representation preflight refuses before dispatch."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.base import CoreError
from speech_aware_evidence_acquisition.core.driver.run import load_window_packet_binding
from speech_aware_evidence_acquisition.core import preparation_window_packets
from speech_aware_evidence_acquisition.reproduction import repair_loop


def _world(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    artifact = data / "packets.json"
    artifact.write_text("{}")
    feature_root = str(tmp_path / "features")
    entries = {
        f"call#w{i:04d}": SimpleNamespace(sources=({"source_provenance": {
            "sample_id": "call", "start_seconds": float((i - 1) * 90),
            "end_seconds": float(i * 90),
        }},)) for i in (1, 2)
    }
    prepared = SimpleNamespace(
        feature_root=feature_root, encoder_identity={"decoder_gguf_sha256": "a" * 64},
        bindings=tuple(entries.values()), by_request_key=entries,
    )
    monkeypatch.setattr(
        preparation_window_packets, "load_prepared_window_feature_packets",
        lambda *args: prepared,
    )
    monkeypatch.setattr(
        repair_loop, "_bound_snapshot", lambda *args: SimpleNamespace(
            for_sample=lambda _: (
                SimpleNamespace(start_seconds=0.0, end_seconds=90.0),
                SimpleNamespace(start_seconds=90.0, end_seconds=180.0),
            )
        ),
    )
    values = {
        "arm": "speech-feature-query", "policy": "obs-repair-loop-ojw",
        "obs_boundary_mode": "fixed", "obs_buffer_seconds": 90,
        "obs_vad_trim_min_seconds": 0, "obs_condition_tail_chars": 0,
        "speech_feature_root": feature_root,
        "server_env": {
            "LLAMA_SPEECH_FEATURE_ROOT": feature_root,
            "LLAMA_SPEECH_DECODER_SHA256": "a" * 64,
        },
        "prepared_window_feature_packets": {"path": str(artifact), "sha256": "b" * 64},
        "predecessor_snapshot": {
            "receipt_relpath": "receipts/predecessor.json", "receipt_sha256": "c" * 64,
        },
        "speech_feature_key_representation_id": "window-features",
        "speech_feature_matcher_policy_id": "exact-window-source",
    }
    return data, values, prepared, [SimpleNamespace(sample_id="call")]


def test_loader_checks_entire_sequence_before_exposing_any_request(tmp_path, monkeypatch):
    data, values, prepared, samples = _world(tmp_path, monkeypatch)
    assert load_window_packet_binding(values, samples, data, tmp_path) is prepared


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong-span", "foreign-root", "decoder"])
def test_loader_refuses_incomplete_or_mismatched_window_binding(tmp_path, monkeypatch, mutation):
    data, values, prepared, samples = _world(tmp_path, monkeypatch)
    if mutation == "missing":
        prepared.by_request_key.pop("call#w0002")
    elif mutation == "extra":
        prepared.by_request_key["call#w0003"] = prepared.by_request_key["call#w0002"]
    elif mutation == "wrong-span":
        prepared.by_request_key["call#w0002"].sources[0]["source_provenance"]["end_seconds"] = 179
    elif mutation == "foreign-root":
        outside = tmp_path / "outside.json"
        outside.write_text("{}")
        values["prepared_window_feature_packets"]["path"] = str(outside)
    else:
        values["server_env"]["LLAMA_SPEECH_DECODER_SHA256"] = "d" * 64
    with pytest.raises(CoreError):
        load_window_packet_binding(values, samples, data, tmp_path)


def test_absent_window_configuration_does_not_load_any_packet(tmp_path, monkeypatch):
    monkeypatch.setattr(
        preparation_window_packets, "load_prepared_window_feature_packets",
        lambda *args: pytest.fail("legacy configuration must not load window packets"),
    )
    assert load_window_packet_binding({}, (), tmp_path, tmp_path) is None


def test_frozen_obs_plan_selects_only_its_bound_windows(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.preparation_window_packets import (
        PreparedWindowFeaturePackets,
    )
    from speech_aware_evidence_acquisition.reproduction.obs_loop import ObsLoopConfig
    data, values, raw, samples = _world(tmp_path, monkeypatch)
    for key, entry in raw.by_request_key.items():
        entry.packet_id = key
    prepared = PreparedWindowFeaturePackets(
        "a" * 64, "b" * 64, "c" * 64, "d" * 64, raw.encoder_identity,
        "unused", raw.feature_root, 2, 2, raw.bindings, raw.by_request_key,
    )
    monkeypatch.setattr(
        preparation_window_packets, "load_prepared_window_feature_packets",
        lambda *args: prepared,
    )
    monkeypatch.setattr(
        ObsLoopConfig, "from_values", lambda *args: SimpleNamespace(
            boundary_mode="fixed", condition_tail_chars=0, vad_trim_min_seconds=0,
            unit_plan=SimpleNamespace(units_by_sample={
                "call": [SimpleNamespace(cut_start_seconds=0, cut_end_seconds=90)],
            }),
        ),
    )
    selected = load_window_packet_binding(values, samples, data, tmp_path)
    assert list(selected.by_request_key) == ["call#w0001"]
    assert selected.request_count == selected.unique_packet_count == 1
    assert list(prepared.by_request_key) == ["call#w0001", "call#w0002"]
