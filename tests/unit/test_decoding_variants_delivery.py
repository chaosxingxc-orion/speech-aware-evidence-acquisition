"""NX-T R4: the node-decoding arm kind through the flight runtime's DELIVERY validator (the seal path), model-free.

Drives the same production walk the live-wiring proofs use over four rows, then hands the rows to
``FlightRuntime._canonical_output_rows`` with the RAW declared native block, as the worker's seal does.
"""

from __future__ import annotations

import pytest

pytest.importorskip("openjiuwen", reason="OpenJiuwen unavailable")

import test_native_episode_runner as runner_tests  # noqa: E402
from test_decoding_variants import D1, D2, D3, D4, _block, _parse  # noqa: E402
from test_decoding_variants_live import _decoding_harness  # noqa: E402
from test_llama_server_transport import _spawn_live_matching_process  # noqa: E402,F401
from test_template_variants_delivery import _raw_native, _runtime  # noqa: E402
from test_template_variants_live import _block as _template_block  # noqa: E402

from speech_aware_evidence_acquisition.core.bundle.outputs import _verify_outputs_trace_binding  # noqa: E402
from speech_aware_evidence_acquisition.core.flight.runtime import FlightRuntimeError  # noqa: E402
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available  # noqa: E402

pytestmark = pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")


def _four_row_world(tmp_path, monkeypatch):
    class FourRowWorld(runner_tests._World):
        SAMPLE_SPECS = (("s1", 2.0), ("s2", 3.5), ("s3", 2.5), ("s4", 3.0))

    monkeypatch.setattr(runner_tests, "_World", FourRowWorld)
    group = _parse(locked_decoding=None)
    return group, _decoding_harness(tmp_path, group, rows=4)


def test_four_decoding_rows_seal_through_the_runtime_delivery_validator(tmp_path, monkeypatch):
    group, harness = _four_row_world(tmp_path, monkeypatch)
    summary = harness.run()
    try:
        runtime = _runtime(harness, summary, _raw_native(harness, solver_role={"decoding_variants": _block()}))
        outputs = runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()
    assert [row["sample_id"] for row in outputs] == ["s1", "s2", "s3", "s4"]
    for row, result in zip(outputs, summary.results):
        assert row["supply_variants"]["schema"] == "saea-supply-variant-arms-v6"
        assert [arm["arm_id"] for arm in row["supply_variants"]["arms"]] == list(group.arm_ids)
        assert [arm["decoding_override"] for arm in row["supply_variants"]["arms"]] == [D1, D2, D3, D4, None, None]
        assert row["text"] == result.final_response_text
    records = {rid: payload for _, rid, payload in harness.trace.records}
    _verify_outputs_trace_binding(tuple(outputs), records)


def test_the_validator_refuses_a_sealed_override_other_than_the_declared_one(tmp_path, monkeypatch):
    _group, harness = _four_row_world(tmp_path, monkeypatch)
    summary = harness.run()
    try:
        declared = _block()
        declared["arms"][0]["decoding"] = {"temperature": 0.61, "top_p": 0.95, "top_k": 20}
        runtime = _runtime(harness, summary, _raw_native(harness, solver_role={"decoding_variants": declared}))
        with pytest.raises(FlightRuntimeError, match="sealed decoding overrides differ"):
            runtime._canonical_output_rows(harness.client)
    finally:
        harness.close()


def test_a_decoding_receipt_is_never_validated_against_another_declaration(tmp_path, monkeypatch):
    _group, harness = _four_row_world(tmp_path, monkeypatch)
    summary = harness.run()
    try:
        for role in ({"supply_variants": _block()}, {"template_variants": _template_block()}, {}):
            runtime = _runtime(harness, summary, _raw_native(harness, solver_role=role))
            with pytest.raises(FlightRuntimeError, match="kind does not match"):
                runtime._canonical_output_rows(harness.client)
        both = {"decoding_variants": _block(), "template_variants": _template_block()}
        with pytest.raises(FlightRuntimeError, match="declares both"):
            _runtime(harness, summary, _raw_native(harness, solver_role=both))._canonical_output_rows(harness.client)
    finally:
        harness.close()
