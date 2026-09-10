"""Unit tests for the ``saea-driver flight`` subcommand (C4c).

Drives ``core.driver.cli.main(["flight", ...])`` directly (no subprocess --
``tests/contract/test_cli_module_dispatch.py`` already covers real-process
dispatch for the CLI module as a whole). ``core.flight.runtime.FlightRuntime``
itself is monkeypatched to a small recording double so these tests exercise
only the CLI's OWN wiring (argument parsing, carrier/task_kind adapter
dispatch, ``--dry-run`` stopping at ``preflight()``, keyword forwarding) --
no model, GPU, llama-server, embedding, or network contact, and no real
config/git/exposure-ledger fixture is required because the real
``FlightRuntime`` never runs.
"""

from __future__ import annotations

import json

import pytest

import speech_aware_evidence_acquisition.core.flight.runtime as flight_runtime_module
import speech_aware_evidence_acquisition.data.lock as data_lock_module
from speech_aware_evidence_acquisition.core.driver import cli as cli_module


class _RecordingFlightRuntime:
    """Records construction kwargs and which stage methods were called, in
    order; every stage method beyond what a real ``--dry-run`` (or a real
    full flight) is expected to reach raises, so an unexpected extra call
    fails the test immediately rather than silently succeeding."""

    last_instance: "_RecordingFlightRuntime | None" = None

    def __init__(self, repo_root, data_root, **kwargs):
        self.repo_root = repo_root
        self.data_root = data_root
        self.kwargs = dict(kwargs)
        self.calls: list[str] = []
        self.score_kwargs: dict[str, object] | None = None
        self.seal_kwargs: dict[str, object] | None = None
        type(self).last_instance = self

    def preflight(self):
        self.calls.append("preflight")
        return {"stage": "preflight", "run_id": self.kwargs["run_id"]}

    def preprocess(self, *args, **kwargs):
        self.calls.append("preprocess")
        return {"stage": "preprocess"}

    def serve(self, *args, **kwargs):
        self.calls.append("serve")
        return {"stage": "serve"}

    def run_phases(self, *args, **kwargs):
        self.calls.append("run_phases")
        return {"stage": "run_phases"}

    def seal(self, *args, **kwargs):
        self.calls.append("seal")
        self.seal_kwargs = dict(kwargs)
        return {"stage": "seal"}

    def score(self, *args, **kwargs):
        self.calls.append("score")
        self.score_kwargs = dict(kwargs)
        return {"stage": "score"}

    @property
    def receipts(self):
        calls = self.calls

        class _Receipts:
            def as_json(self_inner):
                return {"stages": list(calls)}

        return _Receipts()


def _patch_repo_and_lock(monkeypatch, tmp_path):
    repo_root = tmp_path / "repo"
    (repo_root / "configs" / "model").mkdir(parents=True)
    (repo_root / "configs" / "dataset").mkdir(parents=True)
    (repo_root / "configs" / "baseline").mkdir(parents=True)
    (repo_root / "configs" / "experiment").mkdir(parents=True)
    (repo_root / "configs" / "model" / "m.json").write_text(
        json.dumps({"model_lock_key": "fake-lock"}), encoding="utf-8"
    )
    (repo_root / "configs" / "dataset" / "d.json").write_text(
        # A real, registered carrier lock key so data.carriers.carrier_task_layout
        # resolves for real -- the point of this test is the CLI's OWN dispatch
        # wiring, not a synthetic carrier registry.
        json.dumps({"carrier_lock_key": "audio2tool", "split_id": "fake-split"}),
        encoding="utf-8",
    )
    (repo_root / "configs" / "baseline" / "b.json").write_text(
        json.dumps({"arm": "bare-core", "policy": "fixed"}), encoding="utf-8"
    )
    (repo_root / "configs" / "experiment" / "e.json").write_text(
        json.dumps(
            {
                "execution_plan": {
                    "execution_profile": "bounded-discovery-probe",
                    "split_role": "discovery",
                    "planned_model_calls": 10,
                    "planned_gpu_hours": 1.0,
                    "planned_speech_audio_seconds": 100,
                }
            }
        ),
        encoding="utf-8",
    )

    data_root = tmp_path / "data"
    data_root.mkdir(parents=True)

    monkeypatch.setattr(cli_module, "REPO_ROOT", repo_root)
    monkeypatch.setattr(data_lock_module, "data_root", lambda: data_root)
    monkeypatch.setattr(data_lock_module, "umbrella_lock_path", lambda *a, **kw: tmp_path / "datasets.lock.json")
    monkeypatch.setattr(data_lock_module, "load_lock", lambda path: {})
    return repo_root, data_root


def _flight_argv(tmp_path, *, extra=()):
    return [
        "flight",
        "--model", "m",
        "--dataset", "d",
        "--baseline", "b",
        "--experiment", "e",
        "--run-id", "SAEA-CLI-FLIGHT-TEST",
        "--attempt-id", "attempt-cli-test",
        "--runtime-root", str(tmp_path / "runtime"),
        *extra,
    ]


def test_dry_run_reaches_preflight_only(tmp_path, monkeypatch, capsys):
    _patch_repo_and_lock(monkeypatch, tmp_path)
    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)

    exit_code = cli_module.main(_flight_argv(tmp_path, extra=["--dry-run"]))

    assert exit_code == 0
    instance = _RecordingFlightRuntime.last_instance
    assert instance is not None
    assert instance.calls == ["preflight"]
    printed = json.loads(capsys.readouterr().out)
    assert printed["stage"] == "preflight"
    assert printed["dry_run"] is True
    assert printed["run_id"] == "SAEA-CLI-FLIGHT-TEST"
    assert printed["attempt_id"] == "attempt-cli-test"


def test_full_flight_runs_every_stage_in_order(tmp_path, monkeypatch, capsys):
    _patch_repo_and_lock(monkeypatch, tmp_path)
    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)

    exit_code = cli_module.main(_flight_argv(tmp_path, extra=["--max-workers", "4"]))

    assert exit_code == 0
    instance = _RecordingFlightRuntime.last_instance
    assert instance is not None
    assert instance.calls == ["preflight", "preprocess", "serve", "run_phases", "seal", "score"]
    assert instance.score_kwargs == {"max_workers": 4}
    printed = json.loads(capsys.readouterr().out)
    assert printed["run_id"] == "SAEA-CLI-FLIGHT-TEST"
    assert printed["receipts"]["stages"] == [
        "preflight", "preprocess", "serve", "run_phases", "seal", "score",
    ]


def test_campaign_active_flag_is_forwarded_to_the_runtime(tmp_path, monkeypatch):
    _patch_repo_and_lock(monkeypatch, tmp_path)
    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)

    cli_module.main(_flight_argv(tmp_path, extra=["--dry-run", "--campaign-active"]))

    instance = _RecordingFlightRuntime.last_instance
    assert instance.kwargs["campaign_active"] is True


def test_attempt_id_defaults_to_a_fresh_one_when_omitted(tmp_path, monkeypatch):
    _patch_repo_and_lock(monkeypatch, tmp_path)
    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)

    argv = [
        "flight",
        "--model", "m",
        "--dataset", "d",
        "--baseline", "b",
        "--experiment", "e",
        "--run-id", "SAEA-CLI-FLIGHT-TEST-2",
        "--runtime-root", str(tmp_path / "runtime"),
        "--dry-run",
    ]
    cli_module.main(argv)

    instance = _RecordingFlightRuntime.last_instance
    assert isinstance(instance.kwargs["attempt_id"], str) and instance.kwargs["attempt_id"]


def test_unregistered_task_kind_carrier_is_refused(tmp_path, monkeypatch):
    repo_root, _data_root = _patch_repo_and_lock(monkeypatch, tmp_path)
    # earnings21-original is a real carrier with no task layer at all --
    # carrier_task_layout must refuse it, before FlightRuntime is ever
    # constructed.
    (repo_root / "configs" / "dataset" / "d.json").write_text(
        json.dumps({"carrier_lock_key": "earnings21-original", "split_id": "fake-split"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)
    _RecordingFlightRuntime.last_instance = None

    with pytest.raises(Exception):
        cli_module.main(_flight_argv(tmp_path, extra=["--dry-run"]))
    assert _RecordingFlightRuntime.last_instance is None
