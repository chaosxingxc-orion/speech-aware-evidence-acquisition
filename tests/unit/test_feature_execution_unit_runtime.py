"""Root proofs for exact feature-window configuration, fit and delivery custody."""
from dataclasses import replace
from types import MethodType, SimpleNamespace
import hashlib
from pathlib import Path
import json

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime, FlightRuntimeError
from speech_aware_evidence_acquisition.core.preparation import PreparationError, canonical_bytes
from speech_aware_evidence_acquisition.core.preparation_fit import build_native_contact_fit_gate
from speech_aware_evidence_acquisition.rails.core_client import PreparedCoreRequest
from speech_aware_evidence_acquisition.rails.execution_units import ExecutionUnitRoster, scoped_execution_contact_id
from test_feature_execution_unit_client import _feature_unit_world
from test_native_contact_fit import _Runtime, _Tokenizer, _plan, _program, _prepared
from test_execution_unit_static_fit import _phase_runtime


def test_static_fit_captures_feature_units_in_order_and_refuses_swapped_packets(tmp_path):
    _world, _parent, _binding, _registry, _root, roster, _packets = _feature_unit_world(tmp_path)
    runtime = _phase_runtime(roster)
    runtime._samples = [SimpleNamespace(sample_id=roster.units[0].parent_sample_id)]
    payloads = [{
        "sample_id": unit.parent_sample_id,
        "media_relpath": unit.slice_record.media_relpath,
        "audio_seconds": unit.slice_record.audio_seconds,
        "sample_rate_hz": unit.slice_record.sample_rate_hz,
        "speech_feature_parts": [unit.query_descriptor("speech_features")],
        "history": [{"role": "control", "contact_id": scoped_execution_contact_id("direct", unit.request_key)}],
    } for unit in roster.units]

    def wire_check(**kwargs):
        for payload in reversed(payloads):
            kwargs["request_payload_observer"](payload)
    runtime.wire_check = wire_check
    assert runtime.materialize_phase_requests() == tuple(payloads)
    payloads[0]["speech_feature_parts"] = payloads[1]["speech_feature_parts"]
    with pytest.raises(PreparationError, match="ordered execution unit"):
        runtime.materialize_phase_requests()


def test_feature_native_fit_keeps_per_window_budget_and_checks_actual_packets(tmp_path):
    world, parent, _binding, registry, feature_root, roster, _packets = _feature_unit_world(tmp_path)
    runtime = _Runtime(world.data_root)
    runtime._composed.values["speech_feature_root"] = str(feature_root)
    runtime._session.model_files = (SimpleNamespace(path="decoder.gguf", sha256="d" * 64),)
    runtime._samples = (SimpleNamespace(sample_id=parent.sample_id),)
    runtime.execution_unit_roster = lambda: roster
    runtime._execution_unit_registry = registry
    for name in ("execution_unit_for_contact", "validate_execution_unit_feature_payload",
                 "validate_execution_unit_observation"):
        setattr(runtime, name, MethodType(getattr(FlightRuntime, name), runtime))
    tokenizer = _Tokenizer()
    gate = build_native_contact_fit_gate(runtime, _program(), _plan(),
        client_factory=lambda **_kwargs: tokenizer)
    assert gate.execution_plan.planned_model_calls == 16

    def request(index, contact, *, packet_index=None):
        unit = roster.units[index]
        packet_unit = roster.units[index if packet_index is None else packet_index]
        payload = _prepared(parent.sample_id,
            scoped_execution_contact_id(f"role:{contact}", unit.request_key)).as_payload()
        payload.update(
            media_relpath=unit.slice_record.media_relpath,
            audio_seconds=unit.slice_record.audio_seconds,
            sample_rate_hz=unit.slice_record.sample_rate_hz,
            speech_feature_parts=[packet_unit.query_descriptor("speech_features")],
        )
        return PreparedCoreRequest(canonical_bytes(payload), object())

    gate(request(0, 1))
    endpoints = len(tokenizer.calls)
    with pytest.raises(FlightRuntimeError, match="execution unit"):
        gate(request(0, 2, packet_index=1))
    assert len(tokenizer.calls) == endpoints
    gate(request(0, 2))
    endpoints = len(tokenizer.calls)
    with pytest.raises(PreparationError, match="per-unit"):
        gate(request(0, 3))
    assert len(tokenizer.calls) == endpoints
    gate(request(1, 1))
    gate(request(1, 2))
    assert len(gate.receipts) == 4
    assert all(path != "/v1/chat/completions/input_tokens" for _,path,_ in tokenizer.calls)
    assert [json.loads(Path(item["path"]).read_text())
        ["inputs"]["native_contact"]["execution_unit_id"] for item in gate.receipts] == [
            roster.units[0].request_key, roster.units[0].request_key,
            roster.units[1].request_key, roster.units[1].request_key,
        ]

def test_configured_runtime_loads_window_packets_without_a_parent_packet(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core import preparation_window_packets as packet_module
    from speech_aware_evidence_acquisition.core.preparation_window_packets import (
        PreparedWindowFeaturePackets, WindowPacketBinding,
    )
    from speech_aware_evidence_acquisition.core.preparation_windows import (
        WindowFeatureEncoderIdentity, WindowRequestBatch, prepare_window_feature_inventory,
    )
    from speech_aware_evidence_acquisition.rails import build_payload_binding, FrozenCoreClient
    from test_rails_frozen_core_client import _OpenGate, _CapturingTransport

    world, parent, _binding, registry, feature_root, roster, packets = _feature_unit_world(tmp_path)
    samples = (SimpleNamespace(sample_id=parent.sample_id,
        media_relpath=parent.audio_ref.path, audio_seconds=parent.audio_seconds,
        audio_ref=parent.audio_ref),)
    raw_roster = ExecutionUnitRoster(tuple(replace(
        unit, speech_packet_id=None, speech_packet_sha256=None) for unit in roster.units))
    inventory = world.data_root / "prepared/units.json"
    batch = WindowRequestBatch(
        tuple({"sample_id": unit.parent_sample_id, "media_relpath": unit.slice_record.media_relpath,
               "audio_seconds": unit.slice_record.audio_seconds,
               "sample_rate_hz": unit.slice_record.sample_rate_hz} for unit in raw_roster.units),
        tuple(unit.request_key for unit in raw_roster.units),
        tuple(unit.slice_record.trace_view() for unit in raw_roster.units),
    )
    prepare_window_feature_inventory(inventory, batches={"full": batch}, data_root=world.data_root,
        encoder_identity=WindowFeatureEncoderIdentity("a"*64, "b"*40, "d"*64, "f"*64))
    packet_path = world.data_root / "prepared/packets.json"
    packet_path.write_text("{}")
    bindings = tuple(WindowPacketBinding(
        request_key=unit.request_key, source_key=f"{unit.request_key}@{unit.slice_record.sha256}",
        packet_id=packet.packet_id, packet_sha256=packet.packet_sha256,
        audio_sha256=packet.audio_sha256, cache_key=str(index),
        sources=({"source_provenance": unit.slice_record.trace_view()},), chunks=(),
    ) for index,(unit,packet) in enumerate(zip(raw_roster.units, packets, strict=True)))
    prepared = PreparedWindowFeaturePackets(
        inventory_file_sha256="1"*64, cache_audit_file_sha256="2"*64,
        provenance_file_sha256="3"*64, inventory_sha256="4"*64,
        encoder_identity={"decoder_gguf_sha256":"d"*64}, legacy_cache_dir="unused",
        feature_root=str(feature_root), request_count=2, unique_packet_count=2,
        bindings=bindings, by_request_key={item.request_key:item for item in bindings},
    )
    loads = []
    def load(path, expected_sha256, data_root):
        assert path == packet_path and data_root == world.data_root
        assert expected_sha256 == hashlib.sha256(packet_path.read_bytes()).hexdigest()
        loads.append(path)
        return prepared
    monkeypatch.setattr(packet_module, "load_prepared_window_feature_packets", load)
    runtime = object.__new__(FlightRuntime)
    runtime._composed = SimpleNamespace(values={
        "arm":"speech-feature-query", "policy":"phase-direct-only-v1",
        "prepared_execution_units":{
            "relpath":"prepared/units.json",
            "sha256":hashlib.sha256(inventory.read_bytes()).hexdigest(),
            "batch":"full", "registry_run_id":"feature-unit-source",
            "unit_count":2, "split_identity_hash":"a"*64,
        },
        "prepared_window_feature_packets":{
            "path":str(packet_path), "sha256":hashlib.sha256(packet_path.read_bytes()).hexdigest(),
        },
        "speech_feature_root":str(feature_root),
        "speech_feature_key_representation_id":"window-query-v1",
        "speech_feature_matcher_policy_id":"window-direct-v1",
        "server_env":{"LLAMA_SPEECH_FEATURE_ROOT":str(feature_root),
                      "LLAMA_SPEECH_DECODER_SHA256":"d"*64},
    })
    runtime._samples, runtime._data_root, runtime._repo_root = samples, world.data_root, tmp_path
    runtime._plan = _plan()
    runtime._request_id_prefix = "window-proof"
    runtime._carrier_root_resolver = lambda *_args: world.carrier_root
    runtime._payload_binding_factory = build_payload_binding
    runtime._lock = object()
    bound = runtime.execution_unit_roster()
    assert bound == roster
    assert runtime.execution_unit_roster() is bound
    assert len(loads) == 1
    kwargs = runtime.frozen_core_client_kwargs(
        gate=_OpenGate(), transport=_CapturingTransport(), run_dir=world.run_dir)
    assert kwargs["execution_units"] is bound
    assert kwargs["slice_registry"] is runtime._execution_unit_registry
    assert "speech_packet_bindings" not in kwargs and "validated_packet_set" not in kwargs
    client = FrozenCoreClient(**kwargs)
    client.close()
    runtime._composed.values["prepared_window_feature_packets"] = None
    with pytest.raises(FlightRuntimeError, match="prepared window packets"):
        runtime.execution_unit_roster()


def test_preflight_estimate_visits_every_window_and_uses_window_duration(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import runtime as runtime_module
    from test_execution_unit_static_fit import _unit
    from test_flight_runtime import _make_runtime

    runtime = _make_runtime(tmp_path, happy_path=True)
    runtime.preflight()
    for sample in runtime._samples:
        sample.audio_seconds = 3600.0
    units = tuple(replace(
        _unit(parent.sample_id, index),
        speech_packet_id=f"window/{parent.sample_id}/{index}",
        speech_packet_sha256=f"{index + 1:064x}",
    ) for parent in runtime._samples for index in range(2))
    roster = ExecutionUnitRoster(units)
    runtime.execution_unit_roster = lambda: roster
    values = runtime._composed.values
    values.update(
        arm="speech-feature-query", policy="phase-direct-only-v1",
        phase_material={"direct": {
            "instruction_fill": None, "instruction_template": "probes/direct.txt",
            "predecessor_binding": "none",
        }},
    )
    prompt = runtime._repo_root / "configs/probes/direct.txt"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("Transcribe this speech window.", encoding="utf-8")
    runtime.speech_packet_bindings = lambda: pytest.fail("whole-parent packet requested")
    rendered, budgets = [], []
    original_render = runtime_module.render_phase_prompt_envelopes
    original_assess = runtime_module.assess_context_budget

    def render(**kwargs):
        rendered.append(kwargs)
        return original_render(**kwargs)

    def assess(candidate, **kwargs):
        # E17 (2026-09-19): forward whatever keywords the runtime passes.
        # Before E17 this wrapper took the candidate alone, so it raised
        # TypeError the moment the runtime started naming ``limits=`` -- a
        # pre-existing defect in this proof, not in the runtime.
        budgets.append(candidate)
        return original_assess(candidate, **kwargs)

    monkeypatch.setattr(runtime_module, "render_phase_prompt_envelopes", render)
    monkeypatch.setattr(runtime_module, "assess_context_budget", assess)
    receipts = runtime._assess_prompt_budget(runtime._samples)

    assert len(receipts) == 1
    assert [item["sample_id"] for item in rendered] == [unit.request_key for unit in units]
    assert [item["packet_descriptor"] for item in rendered] == [{
        "packet_id": unit.speech_packet_id, "sha256": unit.speech_packet_sha256,
    } for unit in units]
    assert len(budgets) == 1
    assert budgets[0].breakdown.speech_feature_tokens == max(
        1, round(runtime._speech_tokens_per_second)
    )


def test_window_material_refuses_unscoped_external_parent_predecessors():
    from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
    from speech_aware_evidence_acquisition.rails.phase_material import (
        PhaseMaterialError, load_phase_material_specs,
    )

    values = {
        "prepared_execution_units": {"relpath": "windows.json", "sha256": "a" * 64},
        "phase_material": {"direct": {
            "instruction_template": "probes/direct.txt",
            "instruction_fill": None,
            "predecessor_binding": "sealed-manifest",
            "predecessor_source": {
                "manifest_relpath": "runs/parent-manifest.json",
                "manifest_sha256": "b" * 64,
                "producer_policy_id": "phase-direct-only-v1",
            },
        }},
    }
    with pytest.raises(PhaseMaterialError, match="unit-bound external predecessor"):
        load_phase_material_specs(values, default_phase_program("phase-direct-only-v1"))
