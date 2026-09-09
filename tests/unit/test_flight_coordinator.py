"""Contact-free lifecycle tests for root-owned coordinate-fit."""
import json
from pathlib import Path

import pytest

from speech_aware_evidence_acquisition.core.flight.coordinator import CoordinatorError, coordinate_fit


class Lease:
    token = "lease-token"
    def __init__(self, events):
        self.events = events
    def __enter__(self):
        self.events.append("lease-enter")
        return self
    def __exit__(self, exc_type, *_):
        self.events.append("lease-preserved" if exc_type else "lease-release")


class Process:
    returncode = None
    def poll(self):
        return self.returncode


class OneTickProcess(Process):
    def __init__(self):
        self.ticks = 0
    def poll(self):
        self.ticks += 1
        if self.ticks > 1:
            self.returncode = 0
        return self.returncode


class Runtime:
    def __init__(self, data_root):
        self.data_root = data_root
    def preparation_context(self):
        return {
            "required_identity": {"model_fragment": "same"}, "sample_ids": ["a", "b"],
            "data_root": self.data_root, "run_id": "fit-run", "attempt_id": "fit-attempt",
        }


def resident(session_id="session", identity=None):
    return Path("serving") / session_id, {"session_id": session_id, "identity": identity or {"model_fragment": "same"}}


def test_cpu_materialization_precedes_wrapper_and_monitor(tmp_path):
    events, processes = [], []
    def fit(runtime, output, *, policy, contact_cap, attach=None):
        events.append("materialize")
        attach()
        events.append("fit-contact")
        return {"path": str(output), "sha256": "a" * 64}
    def process(command, **kwargs):
        processes.append(command)
        events.append("wrapper" if "serving_session.sh" in command[0] else "monitor")
        return Process()
    def attach_runner(*, policy, **kwargs):
        events.append("attach")
        return (Path("serving/session"), {"session_id": "session"}, object())
    resident_calls = iter([None, resident()])
    result = coordinate_fit(
        Runtime(tmp_path), repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
        output=tmp_path / "fit.json", owner="root", expected_session_id="session",
        contact_cap=3, model_fragment="model", lease_factory=lambda *a, **k: Lease(events),
            fit_runner=fit, attach_runner=attach_runner, find_resident=lambda _: next(resident_calls),
        process_factory=process, sleep=lambda _: None, monotonic=iter([0, 1, 1]).__next__,
        study_head_factory=lambda _: "a" * 40, hold_wrapper_foreground=False,
    )
    assert result["coordinator"]["wrapper_started"] is True
    assert events.index("materialize") < events.index("wrapper") < events.index("attach") < events.index("fit-contact")
    assert len(processes) == 2


def test_existing_mismatched_resident_refuses_before_fit_or_start(tmp_path):
    called = []
    with pytest.raises(CoordinatorError, match="identity mismatch"):
        coordinate_fit(
            Runtime(tmp_path), repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
            output=tmp_path / "fit.json", owner="root", expected_session_id="session",
            contact_cap=3, model_fragment="model", fit_runner=lambda *a, **k: called.append(1),
            find_resident=lambda _: resident(identity={"model_fragment": "different"}),
            study_head_factory=lambda _: "a" * 40,
        )
    assert called == []


def test_reuses_matching_resident_without_starting_wrapper(tmp_path):
    events = []
    def fit(runtime, output, *, policy, contact_cap, attach=None):
        attach()
        return {"path": str(output)}
    result = coordinate_fit(
        Runtime(tmp_path), repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
        output=tmp_path / "fit.json", owner="root", expected_session_id="session",
        contact_cap=3, model_fragment="model", lease_factory=lambda *a, **k: Lease(events),
        fit_runner=fit, attach_runner=lambda **k: events.append("attach") or (),
        find_resident=lambda _: resident(),
        process_factory=lambda command, **kwargs: events.append("wrapper" if "serving_session.sh" in command[0] else "monitor") or Process(),
        study_head_factory=lambda _: "a" * 40, hold_wrapper_foreground=False,
    )
    assert result["coordinator"]["session_reused"] is True
    assert "wrapper" not in events and "monitor" in events


def test_fit_error_preserves_lease_and_started_wrapper(tmp_path):
    events = []
    resident_calls = iter([None, resident()])
    def fit(runtime, output, *, policy, contact_cap, attach=None):
        attach()
        raise RuntimeError("fit failed")
    with pytest.raises(RuntimeError, match="fit failed"):
        coordinate_fit(
            Runtime(tmp_path), repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
            output=tmp_path / "fit.json", owner="root", expected_session_id="session",
            contact_cap=3, model_fragment="model", lease_factory=lambda *a, **k: Lease(events),
            fit_runner=fit, attach_runner=lambda **k: (), find_resident=lambda _: next(resident_calls),
            process_factory=lambda *a, **k: Process(), sleep=lambda _: None,
            monotonic=iter([0, 1, 1]).__next__, study_head_factory=lambda _: "a" * 40,
            hold_wrapper_foreground=False,
        )
    assert "lease-preserved" in events


def test_started_wrapper_stays_foreground_after_receipt_until_stop(tmp_path):
    events = []
    def fit(runtime, output, *, policy, contact_cap, attach=None):
        attach()
        return {"path": str(output)}
    processes = iter([OneTickProcess(), Process()])
    resident_calls = iter([None, resident()])
    result = coordinate_fit(
        Runtime(tmp_path), repo_root=tmp_path, data_root=tmp_path, runtime_root=tmp_path,
        output=tmp_path / "fit.json", owner="root", expected_session_id="session",
        contact_cap=3, model_fragment="model", lease_factory=lambda *a, **k: Lease(events),
        fit_runner=fit, attach_runner=lambda **k: (),
        find_resident=lambda _: next(resident_calls),
        process_factory=lambda *a, **k: next(processes), sleep=lambda _: None,
        study_head_factory=lambda _: "a" * 40,
    )
    lines = (tmp_path / "coordination/session.coordinate-fit.jsonl").read_text().splitlines()
    names = [json.loads(line)["event"] for line in lines]
    assert names.index("fit-receipt-published") < names.index("serving-wrapper-exited")
    assert result["coordinator"]["wrapper_started"] is True


def test_cli_coordinate_fit_uses_prompt_fit_stage_and_root_fields(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import cli, coordinator
    from speech_aware_evidence_acquisition.core.flight.campaign import CampaignCell

    repo = tmp_path / "repo"
    captured = {}
    document = {
        "cell_id": "fit-cell", "model_fragment": "model", "dataset_fragment": "dataset",
        "baseline_fragment": "baseline", "run_id": "run", "attempt_id": "attempt",
        "allowed_execution_stages": ["prompt-fit"], "readiness": {"state": "held", "reason": "pending"},
    }
    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *args: (CampaignCell.from_document(document),))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *args, **kwargs: object())
    def fake_coordinate(runtime, **kwargs):
        captured.update(kwargs)
        return {"ok": True}
    monkeypatch.setattr(coordinator, "coordinate_fit", fake_coordinate)
    assert cli.main([
        "coordinate-fit", "--repo-root", str(repo), "--data-root", str(tmp_path),
        "--runtime-root", str(tmp_path), "--lock-path", str(tmp_path / "lock"),
        "--experiment", "experiment", "--cell", "fit-cell", "--owner", "root",
        "--expected-session-id", "session", "--output", str(tmp_path / "fit.json"),
        "--contact-cap", "3",
    ]) == 0
    assert captured["owner"] == "root"
    assert captured["expected_session_id"] == "session"
    assert captured["model_fragment"] == "model"
