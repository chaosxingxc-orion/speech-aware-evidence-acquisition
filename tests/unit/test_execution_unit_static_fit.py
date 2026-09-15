from __future__ import annotations

from types import MethodType, SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from speech_aware_evidence_acquisition.core.model import SliceRecord
from speech_aware_evidence_acquisition.core.preparation import PreparationError
from speech_aware_evidence_acquisition.core.preparation_fit import (
    materialize_request_fit_batch,
)
from speech_aware_evidence_acquisition.core.preparation_windows import WindowRequestBatch
from speech_aware_evidence_acquisition.rails.execution_units import (
    ExecutionUnit,
    ExecutionUnitRoster,
    execution_unit_scope,
)


def _unit(parent: str, index: int) -> ExecutionUnit:
    record = SliceRecord(
        sample_id=parent,
        parent_media_relpath=f"parents/{parent}.mp3",
        parent_sha256="a" * 64,
        start_seconds=float(index),
        end_seconds=float(index + 1),
        audio_seconds=1.0,
        sample_rate_hz=16_000,
        media_relpath=f"derived/{parent}/i{index:04d}.wav",
        sha256=f"{index + 1:064x}",
        bytes=32_044,
        iteration=index,
    )
    return ExecutionUnit(parent, f"{parent}#w{index + 1:04d}", record)


def _payload(unit: ExecutionUnit) -> dict[str, object]:
    contact_id = execution_unit_scope(unit.request_key) + "/phase-direct:direct:0"
    return {
        "sample_id": unit.parent_sample_id,
        "media_relpath": unit.slice_record.media_relpath,
        "audio_seconds": unit.slice_record.audio_seconds,
        "sample_rate_hz": unit.slice_record.sample_rate_hz,
        "raw_speech_query": {
            "media_relpath": unit.slice_record.media_relpath,
            "sha256": unit.slice_record.sha256,
        },
        "history": [{"role": "control", "contact_id": contact_id}],
    }


def _phase_runtime(roster: ExecutionUnitRoster):
    runtime = object.__new__(FlightRuntime)
    runtime._samples = [SimpleNamespace(sample_id="parent")]
    runtime._prepare = lambda: (
        {
            "policy": "phase-direct-only-v1",
            "prepared_execution_units": {"relpath": "units.json", "sha256": "b" * 64},
        },
        "earnings21-original",
        "discovery",
        "c" * 64,
    )
    runtime.execution_unit_roster = lambda: roster
    runtime.execution_unit_for_contact = MethodType(
        FlightRuntime.execution_unit_for_contact, runtime
    )
    runtime._plan = object()
    runtime._client = object()
    runtime._execution_units = roster
    runtime._execution_unit_registry = object()
    runtime._execution_unit_config_hash = "original"
    return runtime


def test_request_fit_batch_uses_actual_phase_payloads_for_prepared_units() -> None:
    roster = ExecutionUnitRoster((_unit("parent", 0), _unit("parent", 1)))
    payloads = tuple(_payload(unit) for unit in roster.units)
    runtime = SimpleNamespace(
        _adapter=SimpleNamespace(preprocess_plan=lambda: {"kind": "raw-speech-windows"}),
        _composed=SimpleNamespace(values={"prepared_execution_units": {"relpath": "x"}}),
        execution_unit_roster=lambda: roster,
        materialize_phase_requests=lambda: payloads,
        materialize_window_batch=lambda **_kwargs: pytest.fail(
            "prepared units used the legacy window prompt"
        ),
    )

    batch = materialize_request_fit_batch(runtime, execution_plan=object())

    assert isinstance(batch, WindowRequestBatch)
    assert batch.payloads == payloads
    assert batch.request_keys == tuple(unit.request_key for unit in roster.units)
    assert batch.source_bindings == tuple(
        unit.slice_record.trace_view() for unit in roster.units
    )
    assert [batch.request_key(payload) for payload in payloads] == list(batch.request_keys)


def test_request_fit_batch_preserves_legacy_raw_and_nonraw_routing() -> None:
    legacy = object()
    raw = SimpleNamespace(
        _adapter=SimpleNamespace(preprocess_plan=lambda: {"kind": "raw-speech-windows"}),
        _composed=SimpleNamespace(values={}),
        materialize_window_batch=lambda **kwargs: (legacy, kwargs),
    )
    plan = object()
    assert materialize_request_fit_batch(raw, execution_plan=plan) == (
        legacy,
        {"execution_plan": plan},
    )
    nonraw = SimpleNamespace(
        _adapter=SimpleNamespace(preprocess_plan=lambda: {"kind": "other"})
    )
    assert materialize_request_fit_batch(nonraw) is None
    nonraw._composed = SimpleNamespace(
        values={"prepared_execution_units": {"relpath": "units.json"}}
    )
    with pytest.raises(PreparationError, match="raw-speech-windows adapter"):
        materialize_request_fit_batch(nonraw)


def test_materialize_phase_requests_accepts_ordered_units_and_restores_scratch() -> None:
    roster = ExecutionUnitRoster((_unit("parent", 0), _unit("parent", 1)))
    runtime = _phase_runtime(roster)
    originals = {
        name: getattr(runtime, name)
        for name in (
            "_plan",
            "_client",
            "_execution_units",
            "_execution_unit_registry",
            "_execution_unit_config_hash",
        )
    }

    def wire_check(**kwargs):
        runtime._execution_units = "scratch-units"
        runtime._execution_unit_registry = "scratch-registry"
        runtime._execution_unit_config_hash = "scratch-hash"
        for unit in reversed(roster.units):
            kwargs["request_payload_observer"](_payload(unit))

    runtime.wire_check = wire_check

    assert runtime.materialize_phase_requests() == tuple(
        _payload(unit) for unit in roster.units
    )
    assert {name: getattr(runtime, name) for name in originals} == originals


@pytest.mark.parametrize(
    "drift", ["duplicate", "parent", "source", "duration", "contact", "missing"]
)
def test_materialize_phase_requests_rejects_unit_coverage_drift(drift: str) -> None:
    roster = ExecutionUnitRoster((_unit("parent", 0), _unit("parent", 1)))
    runtime = _phase_runtime(roster)
    payloads = [_payload(unit) for unit in roster.units]
    if drift == "duplicate":
        payloads[0] = payloads[1]
    elif drift == "parent":
        payloads[0]["sample_id"] = "other"
    elif drift == "source":
        payloads[0]["raw_speech_query"] = {
            "media_relpath": roster.units[0].slice_record.media_relpath,
            "sha256": "f" * 64,
        }
    elif drift == "duration":
        payloads[0]["audio_seconds"] = 2.0
    elif drift == "contact":
        payloads[0]["history"][-1]["contact_id"] = "foreign"
    else:
        payloads.pop()

    def wire_check(**kwargs):
        for payload in payloads:
            kwargs["request_payload_observer"](payload)

    runtime.wire_check = wire_check
    with pytest.raises((PreparationError, RuntimeError), match="(execution unit|registered)"):
        runtime.materialize_phase_requests()


def test_prepared_units_never_fall_back_to_static_multiphase_predecessors() -> None:
    roster = ExecutionUnitRoster((_unit("parent", 0),))
    runtime = SimpleNamespace(
        _adapter=SimpleNamespace(preprocess_plan=lambda: {"kind": "raw-speech-windows"}),
        _composed=SimpleNamespace(values={"prepared_execution_units": {"relpath": "x"}}),
        execution_unit_roster=lambda: roster,
        materialize_phase_requests=lambda: (_ for _ in ()).throw(
            PreparationError("actual fit requires one phase with sealed predecessors")
        ),
        materialize_window_batch=lambda **_kwargs: pytest.fail(
            "multiphase fit used a static legacy predecessor"
        ),
    )

    with pytest.raises(PreparationError, match="one phase"):
        materialize_request_fit_batch(runtime)


def test_prepared_unit_fit_receipt_requires_unit_order(tmp_path, monkeypatch) -> None:
    roster = ExecutionUnitRoster((_unit("parent", 0), _unit("parent", 1)))
    batch = WindowRequestBatch(
        tuple(_payload(unit) for unit in roster.units),
        tuple(unit.request_key for unit in roster.units),
        tuple(unit.slice_record.trace_view() for unit in roster.units),
    )
    fit_path = tmp_path / "fit.json"
    fit_path.write_text("sealed fit", encoding="utf-8")
    runtime = object.__new__(FlightRuntime)
    runtime._data_root = tmp_path
    runtime._composed = SimpleNamespace(
        values={"prepared_execution_units": {"relpath": "units.json"}}
    )
    runtime._prepare = lambda: ({}, "earnings21-original", "discovery", "c" * 64)
    runtime.materialize_request_fit_batch = lambda: batch
    runtime.request_fit_inputs = lambda payloads, *, window_batch: {
        "keys": list(window_batch.request_keys)
    }

    def artifact(_path, **_kwargs):
        return {
            "every_request_fits": True,
            "rows": [
                {"request_key": key, "fits": True}
                for key in reversed(batch.request_keys)
            ],
            "sample_count": len(batch.request_keys),
        }

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.preparation.load_artifact", artifact
    )
    import hashlib

    with pytest.raises(PreparationError, match="full roster"):
        runtime._verify_prepared_request_fit(
            {
                "relpath": "fit.json",
                "sha256": hashlib.sha256(fit_path.read_bytes()).hexdigest(),
            }
        )


def test_wire_check_scratch_plan_uses_execution_unit_count(tmp_path, monkeypatch) -> None:
    from test_flight_runtime import _wire_runtime

    runtime = _wire_runtime(tmp_path)
    prepared = runtime._prepare()
    values = dict(prepared[0])
    values["policy"] = "phase-direct-only-v1"
    values["prepared_execution_units"] = {
        "relpath": "units.json",
        "sha256": "b" * 64,
    }
    runtime._prepare = lambda: (values, *prepared[1:])
    runtime.execution_unit_roster = lambda: SimpleNamespace(units=(1, 2, 3, 4, 5))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.flight.runtime.validate_artifact_result_binding",
        lambda *_args, **_kwargs: None,
    )
    captured = {}

    def stop_at_client_kwargs(*, plan, **_kwargs):
        captured["plan"] = plan
        raise RuntimeError("captured scratch plan")

    runtime.frozen_core_client_kwargs = stop_at_client_kwargs
    with pytest.raises(RuntimeError, match="captured scratch plan"):
        runtime.wire_check(seal_and_score=False)

    assert captured["plan"].planned_model_calls == 5
