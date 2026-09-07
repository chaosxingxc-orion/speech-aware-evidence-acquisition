"""Unit tests for ``scripts/serving_monitor.py`` and the parked/active
accounting it shares with the flight runtime (E7).

No GPU, no server, no subprocess: ``nvidia-smi`` and the two HTTP endpoints
are injected, and every summary is computed over synthetic samples.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.session.serving import (
    MONITOR_JSONL_NAME,
    PARKED_UTILIZATION_PERCENT,
    SERVING_MONITOR_SUMMARY_SCHEMA,
    read_monitor_samples,
    serving_session_dir,
    summarize_monitor_file,
    summarize_monitor_samples,
)


REPO = Path(__file__).resolve().parents[2]
MONITOR_SCRIPT = REPO / "scripts" / "serving_monitor.py"


def _monitor():
    """Load the script by path (the convention every launcher test in this
    suite uses): the shared WSL venv carries an unrelated top-level
    ``scripts`` package, so ``import scripts.serving_monitor`` resolves to
    that one instead of this repository's."""

    name = "test_serving_monitor_module"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, MONITOR_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


monitor = _monitor()
build_sample = monitor.build_sample
count_new_requests = monitor.count_new_requests
read_gpu = monitor.read_gpu
read_metrics = monitor.read_metrics
read_slots = monitor.read_slots
sample_loop = monitor.sample_loop


class _Completed:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode


def _sample(
    at: float,
    *,
    busy: int = 0,
    utilization: float = 0.0,
    power: float = 30.0,
    requests_total: int = 0,
    tokens: float | None = None,
) -> dict:
    return build_sample(
        now=at,
        gpu={
            "utilization_percent": utilization,
            "memory_used_mib": 18000.0,
            "power_watts": power,
            "pstate": "P0",
            "clocks_sm_mhz": 2100.0,
        },
        slots={"total": 8, "busy": busy, "idle": 8 - busy},
        metrics=({"tokens_predicted_total": tokens} if tokens is not None else None),
        requests_total=requests_total,
    )


# ---------------------------------------------------------------------------
# Sampling.
# ---------------------------------------------------------------------------


def test_read_gpu_parses_one_nvidia_smi_row():
    gpu = read_gpu(run=lambda *a, **k: _Completed("42, 18321, 210.55, P0, 2100\n"))
    assert gpu == {
        "utilization_percent": 42.0,
        "memory_used_mib": 18321.0,
        "power_watts": 210.55,
        "pstate": "P0",
        "clocks_sm_mhz": 2100.0,
    }


@pytest.mark.parametrize(
    "outcome",
    [
        _Completed("", returncode=9),
        _Completed(""),
        _Completed("42, 18321\n"),
    ],
)
def test_read_gpu_fails_open_on_anything_unusable(outcome):
    assert read_gpu(run=lambda *a, **k: outcome) is None


def test_read_gpu_fails_open_when_nvidia_smi_is_absent():
    def _boom(*_args, **_kwargs):
        raise FileNotFoundError("nvidia-smi")

    assert read_gpu(run=_boom) is None


def test_read_slots_counts_busy_and_idle_and_returns_task_ids():
    body = json.dumps(
        [
            {"id": 0, "is_processing": True, "id_task": 17},
            {"id": 1, "is_processing": False, "id_task": 11},
            {"id": 2, "is_processing": False},
        ]
    )
    slots, tasks = read_slots("http://127.0.0.1:8080", get=lambda url, timeout: body)
    assert slots == {"total": 3, "busy": 1, "idle": 2}
    assert tasks == {0: 17, 1: 11, 2: None}


def test_read_slots_reports_nothing_when_the_endpoint_is_unreachable():
    assert read_slots("http://127.0.0.1:8080", get=lambda url, timeout: None) == (None, {})
    assert read_slots("http://127.0.0.1:8080", get=lambda url, timeout: "not json") == (None, {})


def test_read_metrics_parses_the_prometheus_counters():
    body = (
        "# HELP llamacpp:prompt_tokens_total Number of prompt tokens processed.\n"
        "# TYPE llamacpp:prompt_tokens_total counter\n"
        "llamacpp:prompt_tokens_total 1234\n"
        "llamacpp:tokens_predicted_total 567\n"
        "llamacpp:requests_processing 2\n"
    )
    assert read_metrics("http://127.0.0.1:8080", get=lambda url, timeout: body) == {
        "prompt_tokens_total": 1234.0,
        "tokens_predicted_total": 567.0,
        "requests_processing": 2.0,
    }


def test_read_metrics_is_none_when_the_endpoint_is_not_built_in():
    assert read_metrics("http://127.0.0.1:8080", get=lambda url, timeout: None) is None


def test_count_new_requests_counts_each_slot_that_took_a_new_task():
    assert count_new_requests({}, {0: 1, 1: None}) == 1
    assert count_new_requests({0: 1, 1: 2}, {0: 1, 1: 3}) == 1
    assert count_new_requests({0: 1}, {0: 1}) == 0


def test_sample_loop_appends_one_line_and_stops_at_its_duration(tmp_path, monkeypatch):
    session_dir = serving_session_dir(tmp_path, "serving-x")
    session_dir.mkdir(parents=True)
    monkeypatch.setattr(monitor, "read_gpu", lambda: {"utilization_percent": 0.0, "power_watts": 30.0})
    monkeypatch.setattr(
        monitor,
        "read_slots",
        lambda base_url: ({"total": 2, "busy": 0, "idle": 2}, {0: 5, 1: None}),
    )
    monkeypatch.setattr(monitor, "read_metrics", lambda base_url: None)

    class _Args:
        data_root = tmp_path
        session_id = "serving-x"
        host = "127.0.0.1"
        port = 8080
        interval = 0.0
        # A tiny positive duration: the loop writes one sample, then finds
        # its deadline already passed and returns.
        duration = 1e-6

    assert sample_loop(_Args) == 0
    samples = read_monitor_samples(session_dir / MONITOR_JSONL_NAME)
    assert len(samples) == 1
    assert samples[0]["slots"] == {"total": 2, "busy": 0, "idle": 2}
    assert samples[0]["requests_total"] == 1
    assert samples[0]["server_ok"] is True


def test_sample_loop_refuses_a_session_directory_that_does_not_exist(tmp_path):
    class _Args:
        data_root = tmp_path
        session_id = "missing"
        host = "127.0.0.1"
        port = 8080
        interval = 0.0
        duration = 0.1

    with pytest.raises(SystemExit, match="no serving session directory"):
        sample_loop(_Args)


# ---------------------------------------------------------------------------
# The summary -- the number the runtime seals and an agent reports.
# ---------------------------------------------------------------------------


def test_an_empty_window_summarizes_to_zeros():
    summary = summarize_monitor_samples([])
    assert summary["schema"] == SERVING_MONITOR_SUMMARY_SCHEMA
    assert summary["sample_count"] == 0
    assert summary["wall_seconds"] == 0.0
    assert summary["parked_fraction"] is None


def test_parked_and_active_seconds_are_attributed_by_interval():
    samples = [
        _sample(1000.0, busy=0, utilization=1.0),
        _sample(1010.0, busy=4, utilization=95.0),
        _sample(1020.0, busy=4, utilization=90.0),
        _sample(1030.0, busy=0, utilization=0.0),
    ]
    summary = summarize_monitor_samples(samples)
    assert summary["sample_count"] == 4
    assert summary["wall_seconds"] == 30.0
    assert summary["parked_seconds"] == 10.0
    assert summary["active_seconds"] == 20.0
    assert summary["parked_fraction"] == pytest.approx(1 / 3)
    assert summary["parked_seconds"] + summary["active_seconds"] == summary["wall_seconds"]


def test_a_busy_slot_is_never_parked_however_idle_the_card_looks():
    samples = [_sample(0.0, busy=1, utilization=0.0), _sample(10.0, busy=0, utilization=0.0)]
    assert summarize_monitor_samples(samples)["parked_seconds"] == 0.0


def test_the_utilization_threshold_is_the_documented_one():
    below = [
        _sample(0.0, busy=0, utilization=PARKED_UTILIZATION_PERCENT - 0.1),
        _sample(10.0, busy=0, utilization=0.0),
    ]
    at_threshold = [
        _sample(0.0, busy=0, utilization=PARKED_UTILIZATION_PERCENT),
        _sample(10.0, busy=0, utilization=0.0),
    ]
    assert summarize_monitor_samples(below)["parked_seconds"] == 10.0
    assert summarize_monitor_samples(at_threshold)["parked_seconds"] == 0.0


def test_requests_and_tokens_are_last_minus_first_over_the_window():
    samples = [
        _sample(0.0, requests_total=10, tokens=100.0),
        _sample(10.0, requests_total=14, tokens=250.0),
        _sample(20.0, requests_total=21, tokens=900.0),
    ]
    summary = summarize_monitor_samples(samples)
    assert summary["requests_delta"] == 11.0
    assert summary["tokens_delta"] == 800.0


def test_tokens_delta_is_none_without_the_metrics_endpoint():
    samples = [_sample(0.0, requests_total=1), _sample(10.0, requests_total=2)]
    assert summarize_monitor_samples(samples)["tokens_delta"] is None
    assert summarize_monitor_samples(samples)["requests_delta"] == 1.0


def test_power_and_utilization_report_mean_and_peak():
    samples = [
        _sample(0.0, utilization=10.0, power=100.0),
        _sample(10.0, utilization=50.0, power=300.0),
    ]
    summary = summarize_monitor_samples(samples)
    assert summary["mean_power_watts"] == 200.0
    assert summary["peak_power_watts"] == 300.0
    assert summary["mean_utilization_percent"] == 30.0


def test_the_window_bounds_select_only_the_samples_inside_them():
    samples = [_sample(float(second), busy=0, utilization=0.0) for second in range(0, 50, 10)]
    summary = summarize_monitor_samples(samples, from_epoch=10.0, to_epoch=30.0)
    assert summary["sample_count"] == 3
    assert summary["first_sample_at"] == 10.0
    assert summary["last_sample_at"] == 30.0
    assert summary["wall_seconds"] == 20.0


def test_summarize_monitor_file_skips_a_truncated_final_line(tmp_path):
    path = tmp_path / MONITOR_JSONL_NAME
    lines = [json.dumps(_sample(0.0)), json.dumps(_sample(10.0)), '{"sampled_at": 20.0, "gpu"']
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary = summarize_monitor_file(path)
    assert summary["sample_count"] == 2
    assert summary["wall_seconds"] == 10.0


def test_summarize_monitor_file_is_empty_when_no_monitor_ran(tmp_path):
    assert summarize_monitor_file(tmp_path / "absent.jsonl")["sample_count"] == 0
