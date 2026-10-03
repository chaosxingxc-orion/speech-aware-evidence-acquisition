"""Measure admitted sample wall time without substituting contact sums."""
import asyncio
import copy
import json
import threading

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401


def _row(index=0, *, count=2, start=10, end=110, status="completed"):
    return {
        "schema": "saea-sample-execution-timing-v1", "sample_id": f"s{index + 1}",
        "execution_unit_id": None, "admission_index": index, "expected_samples": count,
        "slot_count": 4, "queue_depth": 16, "batch_started_ns": 0,
        "admitted_ns": start * 1_000_000_000, "finished_ns": end * 1_000_000_000,
        "status": status, "error_type": None if status == "completed" else "ValueError",
    }


def _summary(rows, ids=("s1", "s2")):
    from speech_aware_evidence_acquisition.analysis.system_cache_cost import (
        summarize_sample_execution_timing,
    )
    return summarize_sample_execution_timing(rows, expected_sample_ids=ids)


def test_first_is_admission_order_not_fastest_completion_and_throughput_is_separate():
    rows = [_row(1, start=20, end=40), _row(0, end=110)]
    before = copy.deepcopy(rows)
    report = _summary(rows)
    assert report["all_samples"]["mean_seconds"] == 60
    assert report["first_admitted_sample"]["sample_id"] == "s1"
    assert report["first_admitted_sample"]["elapsed_seconds"] == 100
    assert report["excluding_first"]["mean_seconds"] == 20
    assert report["all_samples"]["p95_seconds"] == 100
    assert report["batch_dispatch_wall_seconds"] == 110
    assert report["batch_dispatch_wall_seconds_per_sample"] == 55
    assert report["admission_wait"]["mean_seconds"] == 15
    assert report["first_slot_count_admissions"]["count"] == 2
    assert report["completed_samples"] == 2
    assert rows == before


def test_single_sample_has_no_warm_mean_and_failure_is_not_dropped():
    report = _summary([_row(count=1)], ids=("s1",))
    assert report["excluding_first"]["count"] == 0
    assert report["excluding_first"]["mean_seconds"] is None
    failed = _summary([_row(), _row(1, start=20, end=30, status="failed")])
    assert failed["failed_samples"] == 1
    assert failed["all_samples"]["mean_seconds"] == 55
    assert failed["eligible_for_efficiency_comparison"] is False


@pytest.mark.parametrize("field,value", [
    ("schema", "other"), ("sample_id", "unknown"), ("execution_unit_id", "slice"),
    ("admission_index", True), ("admission_index", 4), ("expected_samples", 3),
    ("batch_started_ns", -1), ("batch_started_ns", 1), ("admitted_ns", -1),
    ("admitted_ns", 10.0), ("finished_ns", float("nan")), ("finished_ns", 1),
    ("status", "unknown"), ("status", []), ("error_type", "ValueError"), ("slot_count", 0),
    ("slot_count", 2), ("queue_depth", True), ("queue_depth", 8),
])
def test_refuses_malformed_or_cross_batch_measurements(field, value):
    from speech_aware_evidence_acquisition.analysis.system_cache_cost import CacheCostError
    rows = [_row(), _row(1, start=120, end=220)]
    rows[0][field] = value
    with pytest.raises(CacheCostError):
        _summary(rows)


def test_requires_complete_unique_ordered_roster_and_rejects_unmeasured_rows():
    from speech_aware_evidence_acquisition.analysis.system_cache_cost import CacheCostError
    for rows, ids in [([], ("s1",)), ([_row()], ("s1", "s2")),
                      ([_row(), _row()], ("s1", "s2")),
                      ([_row(), _row(1)], ("s2", "s1")),
                      ([_row(), _row(1)], ("s1", "s1"))]:
        with pytest.raises(CacheCostError):
            _summary(rows, ids)


def test_refuses_reversed_admission_clocks_and_failed_status_without_error_type():
    from speech_aware_evidence_acquisition.analysis.system_cache_cost import CacheCostError
    with pytest.raises(CacheCostError, match="clocks"):
        _summary([_row(start=20), _row(1, start=10)])
    failed = _row(1, status="failed")
    failed["error_type"] = None
    with pytest.raises(CacheCostError, match="status"):
        _summary([_row(), failed])


def _run(states, episode, sink=None, *, depth=1):
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import execute_speech_agent_workflows
    return execute_speech_agent_workflows(
        states, episode_invoker=episode, branch_count=1, slot_count=4,
        queue_depth=depth, workflow_timeout_seconds=10, sample_timing_sink=sink,
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_executor_records_original_boundaries_and_preserves_failure(monkeypatch):
    from speech_aware_evidence_acquisition.reproduction.ojw import runner
    ticks = iter([0, 10, 110, 120, 220])
    monkeypatch.setattr(runner, "_monotonic_ns", lambda: next(ticks) * 1_000_000_000, raising=False)
    rows = []

    async def episode(state, _run_contact, _session):
        if state == "s2":
            raise ValueError("original execution failure")

    with pytest.raises(ValueError, match="original execution failure"):
        _run(["s1", "s2", "s3"], episode, lambda state, row: rows.append((state, row)))
    assert [state for state, _ in rows] == ["s1", "s2"]
    assert rows[0][1]["admitted_ns"] == 10_000_000_000
    assert rows[1][1]["finished_ns"] == 220_000_000_000
    assert rows[0][1]["status"] == "completed"
    assert rows[1][1]["status"] == "failed"
    assert rows[1][1]["error_type"] == "ValueError"
    assert "original execution failure" not in str(rows)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_concurrent_sink_order_does_not_change_first_admission():
    rows = []
    second_done = asyncio.Event()

    async def episode(state, _contact, _session):
        if state == "first":
            await second_done.wait()
        else:
            second_done.set()

    assert _run(["first", "second"], episode, lambda state, row: rows.append((state, row)), depth=2) == ["first", "second"]
    assert [state for state, _ in rows] == ["second", "first"]
    assert [row["admission_index"] for _, row in rows] == [1, 0]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_invalid_sink_fails_before_execution_and_sink_failure_stops_admission():
    seen = []

    async def episode(state, _contact, _session):
        seen.append(state)

    with pytest.raises(TypeError, match="timing"):
        _run([1], episode, True)
    assert not seen

    def broken_sink(_state, _row):
        raise RuntimeError("trace sink failed")

    with pytest.raises(RuntimeError, match="trace sink failed"):
        _run([1, 2], episode, broken_sink)
    assert seen == [1]

    async def failed(_state, _contact, _session):
        raise ValueError("original")

    with pytest.raises(ValueError, match="original") as caught:
        _run([1], failed, broken_sink)
    assert any("RuntimeError" in note for note in caught.value.__notes__)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_timing_finishes_after_cancelled_blocking_contact_settles():
    started = threading.Event()
    release = threading.Event()
    settled = []
    rows = []

    async def episode(_state, run_contact, _session):
        def blocking(_slot):
            started.set()
            assert release.wait(2)
            settled.append(True)
        task = asyncio.create_task(run_contact(blocking))
        while not started.is_set():
            await asyncio.sleep(0)
        task.cancel()
        release.set()
        await task

    def sink(_state, row):
        assert settled == [True]
        rows.append(row)

    with pytest.raises(asyncio.CancelledError):
        _run([1], episode, sink)
    assert rows[0]["status"] == "failed"
    assert rows[0]["error_type"] == "CancelledError"


def _timing_source(monkeypatch):
    from test_system_trajectory import _source
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.rails import controllers
    # The existing trajectory fixture uses a synthetic native program identity.
    monkeypatch.setattr(controllers, "default_phase_program", lambda policy: SimpleNamespace(program_id=policy))
    return _source()


def test_source_export_binds_records_and_historical_missingness_without_contacts(monkeypatch):
    from speech_aware_evidence_acquisition.analysis.system_cache_cost import export_system_sample_timing
    source = _timing_source(monkeypatch)
    absent = export_system_sample_timing(source)
    assert absent["available"] is False
    assert absent["eligible_for_efficiency_comparison"] is False
    program = source.composed.values["policy"]
    key = f"s1/{program}/sample-execution-timing"
    source.bundle.trace_records[key] = {"use_sample_execution_timing": _row(count=1)}
    before = copy.deepcopy(source.bundle.trace_records)
    report = export_system_sample_timing(source)
    assert report["all_samples"]["mean_seconds"] == 100
    assert report["timing_trace_records"][0]["record_id"] == key
    assert report["source"]["run_id"] == "run"
    assert report["model_contacts_added"] == report["scorer_contacts_added"] == 0
    assert "answer" not in report
    assert source.bundle.trace_records == before


@pytest.mark.parametrize("defect", ["not_verified", "wrong_record", "wrong_sample", "partial", "malformed"])
def test_source_export_refuses_unbound_or_incomplete_timing(defect, monkeypatch):
    from speech_aware_evidence_acquisition.analysis.system_cache_cost import CacheCostError, export_system_sample_timing
    source = _timing_source(monkeypatch)
    program = source.composed.values["policy"]
    row = _row(count=1)
    key = f"s1/{program}/sample-execution-timing"
    if defect == "wrong_record":
        key = "other"
    elif defect == "wrong_sample":
        row["sample_id"] = "other"
    elif defect == "partial":
        # Keep the qualified roster; the injected extra row must fail.
        source.bundle.trace_records[f"s2/{program}/sample-execution-timing"] = {
            "use_sample_execution_timing": _row(1)}
    elif defect == "malformed":
        row = None
    source.bundle.trace_records[key] = {"use_sample_execution_timing": row}
    with pytest.raises(CacheCostError):
        export_system_sample_timing({} if defect == "not_verified" else source)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
def test_actual_native_flight_adds_only_timing_trace_not_model_or_answer_changes(tmp_path, monkeypatch):
    from test_flight_resume_recovery import _harness, _fly
    from test_dispatch_slot_fill import _rendered
    from speech_aware_evidence_acquisition.reproduction.ojw import runner
    original = runner.execute_speech_agent_workflows
    results = []
    for enabled in (False, True):
        def execute(*args, **kwargs):
            if not enabled:
                kwargs.pop("sample_timing_sink", None)
            return original(*args, **kwargs)
        monkeypatch.setattr(runner, "execute_speech_agent_workflows", execute)
        harness = _harness(tmp_path, str(enabled), ("s1", "s2"), max_revisions=1)
        _, canonical, path = _fly(harness, monkeypatch)
        records = [json.loads(line) for line in path.read_text().splitlines()]
        timing = [row["payload"]["use_sample_execution_timing"] for row in records
                  if "use_sample_execution_timing" in row["payload"]]
        if enabled:
            assert len(timing) == 2
            report = _summary(timing)
            assert report["all_samples"]["mean_seconds"] >= 0
        else:
            assert not timing
        results.append((_rendered(harness), canonical))
    assert results[0] == results[1]
