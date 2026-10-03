"""Exercise read-only node timing, missingness and request custody."""
import copy

import pytest

from test_system_cache_cost import _wire
from test_system_trajectory import _source
from test_native_episode_diagnostics import _finite_fixture
from speech_aware_evidence_acquisition.analysis.system_cache_cost import (
    CacheCostError, export_system_cache_cost, export_system_node_timing,
)


def test_role_statistics_count_contacts_not_samples_and_bind_cost():
    source = _source()
    _wire(source, "request-reviewer-1", {
        "usage": {"prompt_tokens": 100, "completion_tokens": 10,
                  "prompt_tokens_details": {"cached_tokens": 90}},
        "timings": {"prompt_ms": 0, "predicted_ms": 2000},
    })
    _wire(source, "request-reviewer-2", {
        "usage": {"prompt_tokens": 300, "completion_tokens": 30,
                  "prompt_tokens_details": {"cached_tokens": 30}},
        "timings": {"prompt_ms": 1000, "predicted_ms": 4000},
    })
    source.bundle.trace_records["request-reviewer-1/cost"] = {
        "calls": 1, "latency_seconds": 4, "prompt_tokens": 999,
    }
    source.bundle.trace_records["request-reviewer-2/cost"] = {
        "calls": 1, "latency_seconds": 8,
    }
    before = copy.deepcopy(source.bundle.trace_records)
    old_export = export_system_cache_cost(source)
    report = export_system_node_timing(source)
    reviewer = report["by_role"]["reviewer"]
    assert reviewer["contacts"] == 2
    assert reviewer["samples"] == 1
    assert reviewer["reused_input_fraction"] == .3  # Token weighted, not mean ratios.
    assert reviewer["metrics"]["prefill_ms"] == {
        "observed_contacts": 2, "total_contacts": 2, "sum_observed": 1000,
        "complete_total": 1000, "mean_observed": 500,
        "p50_observed": 500, "p95_observed": 1000,
    }
    assert reviewer["metrics"]["client_transport_ms"]["mean_observed"] == 6000
    assert reviewer["metrics"]["server_prefill_and_generation_ms"]["mean_observed"] == 3500
    assert reviewer["metrics"]["generated_tokens"]["complete_total"] == 40
    assert reviewer["metrics"]["input_tokens"]["complete_total"] == 400
    assert report["cache_export_content_sha256"] == old_export["content_sha256"]
    measured = [c for c in report["contacts"] if c["role_id"] == "reviewer"]
    assert all(c["cost_record"]["content_sha256"] for c in measured)
    assert all(c["cost_record"]["record_id"].endswith("/cost") for c in measured)
    assert source.bundle.trace_records == before
    assert old_export == export_system_cache_cost(source)
    assert report == export_system_node_timing(source)
    assert "private answer" not in str(report)
    assert "queue_wait_ms" not in str(report)


def test_missing_cost_or_server_timing_is_unknown_not_zero():
    source = _source()
    _wire(source)  # Solver has prefill but no generation or COST.
    report = export_system_node_timing(source)
    solver = report["by_role"]["solver"]
    assert solver["metrics"]["prefill_ms"]["mean_observed"] == 12.5
    for name in ("generation_ms", "server_prefill_and_generation_ms", "client_transport_ms"):
        assert solver["metrics"][name]["observed_contacts"] == 0
        assert solver["metrics"][name]["mean_observed"] is None
        assert solver["metrics"][name]["sum_observed"] is None
    assert report["by_role"]["planner"]["reused_input_fraction"] is None


def test_partial_coverage_and_zero_denominator_do_not_report_complete_reuse():
    source = _source()
    _wire(source, "request-reviewer-1", {
        "usage": {"prompt_tokens": 0, "prompt_tokens_details": {"cached_tokens": 0}},
        "timings": {"prompt_ms": 0, "predicted_ms": 0},
    })
    source.bundle.trace_records["request-reviewer-1/cost"] = {"calls": 1, "latency_seconds": 0}
    report = export_system_node_timing(source)
    reviewer = report["by_role"]["reviewer"]
    assert reviewer["reused_input_fraction"] is None
    for name in ("prefill_ms", "generation_ms", "client_transport_ms"):
        stats = reviewer["metrics"][name]
        assert stats["observed_contacts"] == 1
        assert stats["mean_observed"] == 0
        assert stats["complete_total"] is None
    _wire(source, "request-reviewer-2", {"usage": {"prompt_tokens": 0,
        "prompt_tokens_details": {"cached_tokens": 0}}})
    assert export_system_node_timing(source)["by_role"]["reviewer"]["reused_input_fraction"] is None


@pytest.mark.parametrize("cost", [
    [], {"calls": 2, "latency_seconds": 1}, {"calls": True, "latency_seconds": 1},
    {"calls": 1, "latency_seconds": -1}, {"calls": 1, "latency_seconds": True},
    {"calls": 1, "latency_seconds": float("nan")},
    {"calls": 1, "latency_seconds": float("inf")},
    {"calls": 1, "latency_seconds": "1"}, {"calls": 1},
    {"calls": 1, "latency_seconds": 1, "request_id": "other"},
    {"calls": 1, "latency_seconds": 1, "sample_id": "other"},
])
def test_malformed_or_cross_request_cost_fails_closed(cost):
    source = _source()
    source.bundle.trace_records["request-solver-1/cost"] = cost
    with pytest.raises(CacheCostError):
        export_system_node_timing(source)


def test_same_custody_checks_and_interrupted_contact_coverage():
    with pytest.raises(CacheCostError):
        export_system_node_timing({})
    source = _source()
    _wire(source)
    source.bundle.trace_records["request-solver-1/wire-response"]["response_sha256"] = "0" * 64
    with pytest.raises(CacheCostError):
        export_system_node_timing(source)
    report = export_system_node_timing(_source(lambda: _finite_fixture(with_solver=True)))
    assert sum(r["contacts"] for r in report["by_role"].values()) == 4
    assert sum(c["interrupted"] for c in report["contacts"]) == 2
