"""Feature packet custody for source-bound execution units."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.model import (
    SliceRecord,
    SpeechFeatureChunkData,
    materialize_speech_feature_packet,
)
from speech_aware_evidence_acquisition.core.preparation_window_packets import (
    PreparedWindowFeaturePackets,
    WindowPacketBinding,
)
from speech_aware_evidence_acquisition.rails import (
    FrozenCoreClientError,
    build_payload_binding,
    build_slice_registry,
)
from speech_aware_evidence_acquisition.rails.errors import RailsError
from speech_aware_evidence_acquisition.rails.execution_units import (
    ExecutionUnit,
    ExecutionUnitRoster,
    scoped_execution_contact_id,
)
from test_rails_frozen_core_client import (
    _CapturingTransport,
    _OpenGate,
    _World,
    _client,
    _sha256_file,
    _write_wav,
)


def _feature_unit_world(tmp_path: Path):
    world = _World(tmp_path)
    parent = world.samples[0]
    samples = (parent,)
    binding = build_payload_binding(
        carrier_lock_key="fake-carrier",
        samples=samples,
        data_root=world.data_root,
        carrier_root=world.carrier_root,
    )
    registry = build_slice_registry(
        data_root=world.data_root,
        run_id="feature-unit-source",
        samples=samples,
    )
    feature_root = tmp_path / "features"
    units = []
    packet_bindings = []
    packets = []
    for index, (start, duration) in enumerate(((0.0, 0.5), (0.5, 0.75))):
        relpath = registry.slice_relpath(parent.sample_id, index)
        path = world.data_root / relpath
        _write_wav(path, seconds=duration)
        record = SliceRecord(
            sample_id=parent.sample_id,
            parent_media_relpath=parent.audio_ref.path,
            parent_sha256=parent.audio_ref.sha256,
            start_seconds=start,
            end_seconds=start + duration,
            audio_seconds=duration,
            sample_rate_hz=16000,
            media_relpath=relpath,
            sha256=_sha256_file(path),
            bytes=path.stat().st_size,
            iteration=index,
        )
        registry.register(record)
        request_key = f"{parent.sample_id}#w{index + 1:04d}"
        units.append(ExecutionUnit(parent.sample_id, request_key, record))
        packet = materialize_speech_feature_packet(
            feature_root=feature_root,
            packet_id=f"window/{index}",
            audio_sha256=record.sha256,
            encoder_receipt_sha256="e" * 64,
            decoder_gguf_sha256="d" * 64,
            mmproj_sha256="f" * 64,
            position_mode="mrope_1d",
            causal_attention=True,
            chunks=(
                SpeechFeatureChunkData(
                    n_tokens=2,
                    n_pos=2,
                    n_embd=4,
                    feature_bytes=struct.pack("<8f", *range(8)),
                    position_bytes=struct.pack(
                        "<8i", 0, 1, 0, 1, 0, 1, 0, 1
                    ),
                ),
            ),
        )
        packets.append(packet)
        packet_bindings.append(
            WindowPacketBinding(
                request_key=request_key,
                source_key=f"{request_key}@{record.sha256}",
                packet_id=packet.packet_id,
                packet_sha256=packet.packet_sha256,
                audio_sha256=record.sha256,
                cache_key=f"cache-{index}",
                sources=({"source_provenance": record.trace_view()},),
                chunks=(),
            )
        )
    prepared = PreparedWindowFeaturePackets(
        inventory_file_sha256="1" * 64,
        cache_audit_file_sha256="2" * 64,
        provenance_file_sha256="3" * 64,
        inventory_sha256="4" * 64,
        encoder_identity={},
        legacy_cache_dir="unused",
        feature_root=str(feature_root),
        request_count=2,
        unique_packet_count=2,
        bindings=tuple(packet_bindings),
        by_request_key={item.request_key: item for item in packet_bindings},
    )
    roster = ExecutionUnitRoster(tuple(units)).with_speech_packets(prepared)
    return world, parent, binding, registry, feature_root, roster, tuple(packets)


def _messages(packet):
    return (
        {"role": "system", "content": "Transcribe this speech window."},
        {
            "role": "user",
            "content": [
                {
                    "type": "input_speech_features",
                    "speech_features": {
                        "packet_id": packet.packet_id,
                        "sha256": packet.packet_sha256,
                        "role": "query",
                    },
                }
            ],
        },
    )


def _arguments(parent, request_key):
    return {
        "speech_feature_sample_id": parent.sample_id,
        "agent_state": (),
        "key_representation_id": "window-query-v1",
        "matcher_policy_id": "window-direct-v1",
        "agent_contact_id": scoped_execution_contact_id("direct", request_key),
        "contact_instruction": "Transcribe this registered window.",
    }


def test_unit_packet_attachment_preserves_raw_identity_and_legacy_bytes(tmp_path):
    _, _, _, _, _, roster, packets = _feature_unit_world(tmp_path)
    attached = roster.units[0]
    raw = ExecutionUnit(
        attached.parent_sample_id, attached.request_key, attached.slice_record
    )

    assert raw.as_json() == {
        "parent_sample_id": attached.parent_sample_id,
        "request_key": attached.request_key,
        "slice_record": attached.slice_record.trace_view(),
    }
    assert raw.query_descriptor("speech_audio") == {
        "media_relpath": attached.slice_record.media_relpath,
        "sha256": attached.slice_record.sha256,
    }
    with pytest.raises(RailsError, match="no bound speech packet"):
        raw.query_descriptor("speech_features")
    assert attached.query_descriptor("speech_features") == {
        "packet_id": packets[0].packet_id,
        "sha256": packets[0].packet_sha256,
        "role": "query",
    }


def test_packet_attachment_requires_exact_complete_roster(tmp_path):
    _, _, _, _, _, roster, _ = _feature_unit_world(tmp_path)
    incomplete = PreparedWindowFeaturePackets(
        inventory_file_sha256="1" * 64,
        cache_audit_file_sha256="2" * 64,
        provenance_file_sha256="3" * 64,
        inventory_sha256="4" * 64,
        encoder_identity={},
        legacy_cache_dir="unused",
        feature_root="unused",
        request_count=1,
        unique_packet_count=1,
        bindings=(),
        by_request_key={roster.units[0].request_key: object()},
    )
    raw = ExecutionUnitRoster(
        tuple(
            ExecutionUnit(unit.parent_sample_id, unit.request_key, unit.slice_record)
            for unit in roster.units
        )
    )
    with pytest.raises(RailsError, match="exact execution unit roster"):
        raw.with_speech_packets(incomplete)


def test_feature_client_uses_two_packets_and_slice_facts_for_one_parent(tmp_path):
    world, parent, binding, registry, root, roster, packets = _feature_unit_world(
        tmp_path
    )
    gate, transport = _OpenGate(), _CapturingTransport()
    client, _, _ = _client(
        world,
        tmp_path,
        gate=gate,
        transport=transport,
        binding=binding,
        arm="speech-feature-query",
        speech_feature_root=root,
        execution_units=roster,
        slice_registry=registry,
    )

    for unit, packet in zip(roster.units, packets, strict=True):
        assert client.complete(
            _messages(packet), **_arguments(parent, unit.request_key)
        ) == "ok"

    assert len(gate.checked_plans) == 1
    assert [payload["sample_id"] for payload in transport.calls] == ["s1", "s1"]
    for payload, unit, packet in zip(
        transport.calls, roster.units, packets, strict=True
    ):
        assert payload["media_relpath"] == unit.slice_record.media_relpath
        assert payload["audio_seconds"] == unit.slice_record.audio_seconds
        assert payload["sample_rate_hz"] == unit.slice_record.sample_rate_hz
        assert payload["speech_feature_parts"] == [
            {
                "packet_id": packet.packet_id,
                "sha256": packet.packet_sha256,
                "role": "query",
            }
        ]


@pytest.mark.parametrize(
    "failure", ["missing-scope", "foreign-scope", "wrong-parent", "wrong-packet"]
)
def test_feature_client_refuses_wrong_unit_or_packet_before_dispatch(
    tmp_path, failure
):
    world, parent, binding, registry, root, roster, packets = _feature_unit_world(
        tmp_path
    )
    transport = _CapturingTransport()
    client, _, _ = _client(
        world,
        tmp_path,
        transport=transport,
        binding=binding,
        arm="speech-feature-query",
        speech_feature_root=root,
        execution_units=roster,
        slice_registry=registry,
    )
    arguments = _arguments(parent, roster.units[0].request_key)
    messages = _messages(packets[0])
    if failure == "missing-scope":
        arguments["agent_contact_id"] = "direct"
    elif failure == "foreign-scope":
        arguments["agent_contact_id"] = scoped_execution_contact_id(
            "direct", "foreign#w0001"
        )
    elif failure == "wrong-parent":
        arguments["speech_feature_sample_id"] = "s2"
    else:
        messages = _messages(packets[1])

    with pytest.raises(FrozenCoreClientError):
        client.complete(messages, **arguments)
    assert transport.calls == []


def test_prepared_feature_request_rechecks_changed_source_before_dispatch(tmp_path):
    world, parent, binding, registry, root, roster, packets = _feature_unit_world(
        tmp_path
    )
    transport = _CapturingTransport()
    client, _, _ = _client(
        world,
        tmp_path,
        transport=transport,
        binding=binding,
        arm="speech-feature-query",
        speech_feature_root=root,
        execution_units=roster,
        slice_registry=registry,
    )
    unit = roster.units[0]
    prepared = client.prepare_request(
        _messages(packets[0]), **_arguments(parent, unit.request_key)
    )
    (world.data_root / unit.slice_record.media_relpath).write_bytes(b"changed")

    with pytest.raises(FrozenCoreClientError):
        client.complete_prepared(prepared)
    assert transport.calls == []



def test_legacy_feature_client_still_uses_parent_packet_binding(tmp_path):
    from test_rails_frozen_core_client import _speech_feature_world

    world = _World(tmp_path)
    feature_root, packet, bindings = _speech_feature_world(world, tmp_path)
    client, _, transport = _client(
        world,
        tmp_path,
        arm="speech-feature-query",
        speech_feature_root=feature_root,
        speech_packet_bindings=bindings,
    )
    client.complete(
        _messages(packet),
        speech_feature_sample_id="s1",
        key_representation_id="legacy-key",
        matcher_policy_id="legacy-matcher",
    )
    assert transport.calls[0]["media_relpath"] == world.samples[0].audio_ref.path
