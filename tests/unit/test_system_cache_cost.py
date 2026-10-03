from __future__ import annotations

import base64
import copy
import hashlib
import json

import pytest

from test_system_trajectory import _source
from test_native_episode_diagnostics import _finite_fixture, _terminal_fixture
from speech_aware_evidence_acquisition.analysis.system_cache_cost import (
    CacheCostError, export_system_cache_cost, read_llama_cache_metrics,
)


def _read(body):
    raw = json.dumps(body).encode()
    return read_llama_cache_metrics(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


def _wire(source, request_id="request-solver-1", body=None):
    raw = json.dumps(body or {
        "choices": [{"message": {"content": "private answer"}}],
        "usage": {"prompt_tokens": 100, "prompt_tokens_details": {"cached_tokens": 70}},
        "timings": {"cache_n": 70, "prompt_n": 30, "prompt_ms": 12.5},
        "tokens_cached": 109,
    }).encode()
    source.bundle.trace_records[request_id + "/wire-response"] = {
        "request_id": request_id, "sample_id": "s1",
        "response_b64": base64.b64encode(raw).decode(),
        "response_sha256": hashlib.sha256(raw).hexdigest(),
    }


def test_distinguishes_reused_input_from_final_resident_tokens_and_prefill():
    metrics = _read({
        "usage": {"prompt_tokens": 100, "completion_tokens": 9,
                  "prompt_tokens_details": {"cached_tokens": 70}},
        "timings": {"cache_n": 70, "prompt_n": 30, "prompt_ms": 12.5,
                    "predicted_n": 9, "predicted_ms": 42},
        "tokens_cached": 109,
        "content": "private answer",
    })
    assert metrics["values"] == {
        "input_tokens": 100, "reused_input_tokens": 70,
        "evaluated_input_tokens": 30, "generated_tokens": 9,
        "prefill_ms": 12.5, "generation_ms": 42,
        "final_resident_tokens": 109,
    }
    assert metrics["sources"]["reused_input_tokens"] == [
        "usage.prompt_tokens_details.cached_tokens", "timings.cache_n"]
    assert "private answer" not in str(metrics)


def test_responses_api_and_zero_are_supported_without_inventing_missing_values():
    metrics = _read({"usage": {"input_tokens": 0, "output_tokens": 0,
                               "input_tokens_details": {"cached_tokens": 0}}})
    assert metrics["values"]["reused_input_tokens"] == 0
    assert metrics["values"]["generated_tokens"] == 0
    assert metrics["values"]["prefill_ms"] is None
    legacy = _read({"tokens_cached": 100})
    assert legacy["values"]["reused_input_tokens"] is None
    assert legacy["sources"]["reused_input_tokens"] == []


@pytest.mark.parametrize("body", [
    {"usage": {"prompt_tokens": True}},
    {"usage": {"prompt_tokens": "100"}},
    {"usage": {"prompt_tokens": 100.0}},
    {"timings": {"cache_n": -1}},
    {"timings": {"prompt_ms": -0.1}},
    {"timings": {"prompt_ms": True}},
    {"usage": {"prompt_tokens": 10, "input_tokens": 11}},
    {"usage": {"prompt_tokens": 10, "prompt_tokens_details": {"cached_tokens": 11}}},
    {"usage": {"prompt_tokens_details": {"cached_tokens": 10}}, "timings": {"cache_n": 9}},
    {"usage": []}, {"usage": {"prompt_tokens_details": []}}, {"timings": "bad"},
    {"usage": {"completion_tokens": 2}, "timings": {"predicted_n": 3}},
])
def test_invalid_or_conflicting_measurement_is_rejected(body):
    with pytest.raises(CacheCostError):
        _read(body)


@pytest.mark.parametrize("raw", [
    b'{"usage":{"prompt_tokens":1,"prompt_tokens":2}}',
    b'{"timings":{"prompt_ms":NaN}}',
    b'{"timings":{"prompt_ms":Infinity}}', b'{"timings":{"prompt_ms":1e999}}',
    b'[]', b'null', b'{', b'\xff',
])
def test_invalid_wire_json_is_rejected(raw):
    with pytest.raises(CacheCostError):
        read_llama_cache_metrics(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


def test_wire_hash_and_empty_or_null_measurements():
    with pytest.raises(CacheCostError, match="hash"):
        read_llama_cache_metrics(b'{}', expected_sha256="0" * 64)
    assert all(value is None for value in _read({})["values"].values())
    assert _read({"usage": None, "timings": None})["values"]["input_tokens"] is None


def test_exports_all_contacts_without_answer_text_or_partial_totals():
    source = _source()
    _wire(source)
    before = copy.deepcopy(source.bundle.trace_records)
    report = export_system_cache_cost(source)
    assert len(report["contacts"]) == 5
    solver = next(row for row in report["contacts"] if row["role_id"] == "solver")
    assert solver["metrics"]["values"]["reused_input_tokens"] == 70
    assert solver["sample_id"] == "s1"
    assert solver["wire_response"]["record_id"] == "request-solver-1/wire-response"
    missing = next(row for row in report["contacts"] if row["role_id"] == "planner")
    assert missing["metrics"]["values"]["reused_input_tokens"] is None
    assert report["totals"]["reused_input_tokens"] == {
        "observed_contacts": 1, "total_contacts": 5,
        "sum_observed": 70, "complete_total": None,
    }
    assert "private answer" not in str(report)
    assert source.bundle.trace_records == before
    assert report == export_system_cache_cost(source)


def test_complete_zero_cache_total_is_distinct_from_missing():
    source = _source()
    for rid in [key.removesuffix("/request") for key in source.bundle.trace_records
                if key.endswith("/request")]:
        _wire(source, rid, {"timings": {"cache_n": 0}})
    report = export_system_cache_cost(source)
    assert report["totals"]["reused_input_tokens"]["complete_total"] == 0
    assert report["totals"]["input_tokens"]["sum_observed"] is None


@pytest.mark.parametrize("mutation", ["hash", "sample", "request", "base64", "missing-body"])
def test_export_rejects_bad_wire_custody(mutation):
    source = _source()
    _wire(source)
    record = source.bundle.trace_records["request-solver-1/wire-response"]
    if mutation == "hash":
        record["response_sha256"] = "0" * 64
    elif mutation in {"sample", "request"}:
        record[mutation + "_id"] = "other"
    elif mutation == "base64":
        record["response_b64"] = "!not-base64"
    else:
        del record["response_b64"]
    with pytest.raises(CacheCostError):
        export_system_cache_cost(source)


def test_export_requires_verified_complete_source_and_retains_existing_validation():
    with pytest.raises(CacheCostError):
        export_system_cache_cost({})
    source = _source()
    del source.bundle.trace_records["request-solver-1/response"]
    with pytest.raises(CacheCostError):
        export_system_cache_cost(source)


def test_terminal_and_interrupted_contacts_are_counted():
    terminal = export_system_cache_cost(_source(_terminal_fixture))
    assert len(terminal["contacts"]) == 5
    finite = export_system_cache_cost(_source(lambda: _finite_fixture(with_solver=True)))
    assert len(finite["contacts"]) == 4
    interrupted = [row for row in finite["contacts"] if row["interrupted"]]
    assert len(interrupted) == 2
    assert interrupted[-1]["metrics"]["values"]["generated_tokens"] == 2


def test_requested_slot_is_recorded_without_inventing_an_actual_assignment():
    source = _source()
    source.bundle.trace_records["request-solver-1/request"]["payload"]["decoding_params"]["id_slot"] = 2
    report = export_system_cache_cost(source)
    solver = next(row for row in report["contacts"] if row["role_id"] == "solver")
    assert solver["requested_slot_id"] == 2
    assert report["contacts"][0]["requested_slot_id"] is None


@pytest.mark.parametrize("slot", [True, -2, "per-sample", 1.0])
def test_unresolved_or_invalid_slot_is_rejected(slot):
    source = _source()
    source.bundle.trace_records["request-solver-1/request"]["payload"]["decoding_params"]["id_slot"] = slot
    with pytest.raises(CacheCostError):
        export_system_cache_cost(source)
