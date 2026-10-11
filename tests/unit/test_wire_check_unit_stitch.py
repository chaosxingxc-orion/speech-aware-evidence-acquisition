"""The wire check must emit the seal-time unit-stitch trace exactly as ``seal()``.

Failing shape (2026-10-10 carrier end-to-end proof, E21 ALL-OFF cells): an
execution-unit (E21 window) cell's sealed outputs carry one stitched row per
parent call whose ``request_id`` ends in ``:unit-stitch``. ``seal()`` traces
those rows before the client closes; ``wire_check(seal_and_score=True)`` did
not, so the bundle verifier refused with ``BundleError: outputs request_id
'...:unit-stitch' has no matching trace record '...:unit-stitch/response'
(I7)``. The fix routes both paths through ``_emit_seal_time_traces``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.bundle import BundleError
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntime
from test_flight_runtime import (
    _TransportDrivingClient,
    _fake_bundle_verifier,
    _fake_manifest_builder,
    _wire_runtime,
)

STITCH_ID = "WIRECHECK-RUN:1:unit-stitch"


def _stitched_row(request_id: str = STITCH_ID) -> dict[str, object]:
    return {
        "sample_id": "parent-1",
        "request_id": request_id,
        "arm": "bare-core",
        "text": "stitched text",
        "admitted": True,
        "request_sha256": "a" * 64,
        "response_sha256": "b" * 64,
        "response_text_sha256": "c" * 64,
        "execution_unit_delivery": {
            "request_ids": ["u1", "u2"],
            "execution_unit_roster_sha256": "d" * 64,
            "source_response_sha256s": ["e" * 64, "f" * 64],
            "sources": [{"unit": "u1"}, {"unit": "u2"}],
        },
    }


class _TracingClient(_TransportDrivingClient):
    """Records flushed trace buffers and whether each arrived before close."""

    flushed: list[tuple[str, str]] = []
    flushed_before_close: list[bool] = []

    def flush_trace_buffer(self, buffer) -> None:
        for channel, record_id, _payload in buffer.records:
            type(self).flushed.append((channel, record_id))
            type(self).flushed_before_close.append(not self.closed)


@pytest.fixture(autouse=True)
def _reset_client():
    _TracingClient.flushed = []
    _TracingClient.flushed_before_close = []
    yield


def _i7_verifier_for(outputs_by_manifest: dict[str, Path]):
    """Mirror core.bundle.verify_bundle's I7: every outputs request_id must
    have a '<id>/response' trace record."""

    def _verify(manifest_path):
        outputs = outputs_by_manifest[str(manifest_path)]
        traced = {record_id for _channel, record_id in _TracingClient.flushed}
        for line in outputs.read_text(encoding="utf-8").splitlines():
            request_id = json.loads(line)["request_id"]
            if request_id.endswith(":unit-stitch") and request_id + "/response" not in traced:
                raise BundleError(
                    f"outputs request_id {request_id!r} has no matching trace record "
                    f"'{request_id}/response' (I7: every outputs request_id must appear "
                    "in the trace)"
                )
        return _fake_bundle_verifier(manifest_path)

    return _verify


def _runtime(tmp_path):
    outputs_by_manifest: dict[str, Path] = {}

    def _builder(**kwargs):
        path = _fake_manifest_builder(**kwargs)
        outputs_by_manifest[str(path)] = Path(kwargs["result"].outputs_path)
        return path

    runtime = _wire_runtime(
        tmp_path,
        client_factory=_TracingClient,
        manifest_builder=_builder,
        bundle_verifier=_i7_verifier_for(outputs_by_manifest),
    )
    original = FlightRuntime._canonical_output_rows

    def _rows_with_stitch(self, client, **kwargs):
        return [*original(self, client, **kwargs), _stitched_row()]

    runtime._canonical_output_rows = _rows_with_stitch.__get__(runtime)
    return runtime


def test_wire_check_traces_the_unit_stitch_before_the_client_closes(tmp_path):
    receipt = _runtime(tmp_path).wire_check(seal_and_score=True)

    seal = receipt["seal_and_score"]
    assert seal["status"] == "OK", seal
    traced = {record_id for _channel, record_id in _TracingClient.flushed}
    assert {f"{STITCH_ID}/request", f"{STITCH_ID}/response", f"{STITCH_ID}/use"} <= traced
    assert _TracingClient.flushed_before_close and all(_TracingClient.flushed_before_close)


def test_wire_check_without_seal_and_score_emits_no_seal_time_trace(tmp_path):
    receipt = _runtime(tmp_path).wire_check(seal_and_score=False)

    assert receipt["seal_and_score"]["status"] == "SKIPPED"
    assert _TracingClient.flushed == []


def test_seal_and_wire_check_share_one_seal_time_trace_helper():
    import inspect

    assert "_emit_seal_time_traces" in inspect.getsource(FlightRuntime.seal)
    assert "_emit_seal_time_traces" in inspect.getsource(FlightRuntime.wire_check)
