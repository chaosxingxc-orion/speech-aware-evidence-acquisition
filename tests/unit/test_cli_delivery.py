"""CLI phase-delivery workflow tests with synthetic inputs only."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from speech_aware_evidence_acquisition.core.driver import cli as cli_module
from speech_aware_evidence_acquisition.core.bundle import delivery as delivery_module
from speech_aware_evidence_acquisition.core.bundle import delivery_replay
from speech_aware_evidence_acquisition.rails.controllers import default_phase_program
from test_cli_flight import (
    _RecordingFlightRuntime,
    _flight_argv,
    _patch_repo_and_lock,
)


def _write_phase_declaration_fixture(tmp_path, monkeypatch, *, parent_baseline="b"):
    _patch_repo_and_lock(monkeypatch, tmp_path)
    repo_root = tmp_path / "repo"
    (repo_root / "configs" / "baseline" / "b.json").write_text(
        json.dumps({"arm": "bare-core", "policy": "phase-direct-then-slots-v1"}),
        encoding="utf-8",
    )
    program = default_phase_program("phase-direct-then-slots-v1")
    program_hash = delivery_replay.sha256(
        delivery_replay.canonical(program.as_json())
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
                },
                "cells": [{
                    "cell_id": "generation",
                    "model_fragment": "m",
                    "dataset_fragment": "d",
                    "baseline_fragment": parent_baseline,
                }],
                "delivery_derivatives": [{
                    "cell_id": "delivery",
                    "parent_cell_id": "generation",
                    "response_postprocessor": "slurp-intent-slots-delivery-v1",
                    "response_postprocessor_params": {},
                    "source_selector": {
                        "schema": "saea-phase-response-pair-v1",
                        "program_id": program.program_id,
                        "program_sha256": program_hash,
                        "predecessor_phase": "direct",
                        "response_phase": "slots",
                    },
                }],
            }
        ),
        encoding="utf-8",
    )


def test_phase_delivery_refuses_before_runtime_construction(tmp_path, monkeypatch):
    _write_phase_declaration_fixture(tmp_path, monkeypatch)

    def forbidden(*args, **kwargs):
        pytest.fail("phase delivery refusal must precede FlightRuntime construction")

    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.flight.runtime.FlightRuntime",
        forbidden,
    )
    with pytest.raises(ValueError, match="must be derived before scoring"):
        cli_module.main(_flight_argv(tmp_path))


def test_seal_only_forwards_defer_scoring_and_skips_score(tmp_path, monkeypatch):
    _write_phase_declaration_fixture(tmp_path, monkeypatch)
    import speech_aware_evidence_acquisition.core.flight.runtime as flight_runtime_module

    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)
    assert cli_module.main(_flight_argv(tmp_path, extra=["--seal-only"])) == 0
    instance = _RecordingFlightRuntime.last_instance
    assert instance is not None
    assert instance.calls == ["preflight", "preprocess", "serve", "run_phases", "seal"]
    assert instance.seal_kwargs == {"defer_scoring": True}


def test_dry_run_allows_phase_delivery_validation(tmp_path, monkeypatch):
    _write_phase_declaration_fixture(tmp_path, monkeypatch)
    import speech_aware_evidence_acquisition.core.flight.runtime as flight_runtime_module

    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)
    assert cli_module.main(_flight_argv(tmp_path, extra=["--dry-run"])) == 0
    instance = _RecordingFlightRuntime.last_instance
    assert instance is not None
    assert instance.calls == ["preflight"]


def test_other_parent_declaration_is_skipped_by_real_validator(tmp_path, monkeypatch):
    _write_phase_declaration_fixture(tmp_path, monkeypatch, parent_baseline="other")
    import speech_aware_evidence_acquisition.core.flight.runtime as flight_runtime_module

    monkeypatch.setattr(flight_runtime_module, "FlightRuntime", _RecordingFlightRuntime)
    assert cli_module.main(_flight_argv(tmp_path)) == 0
    instance = _RecordingFlightRuntime.last_instance
    assert instance is not None
    assert instance.calls[-1] == "score"

def test_build_delivery_is_a_thin_api_dispatch(tmp_path, monkeypatch, capsys):
    imported_root = cli_module.REPO_ROOT.resolve()
    calls = {}

    def fake_build(**kwargs):
        calls.update(kwargs)
        return tmp_path / "derived" / "run-manifest.json"

    monkeypatch.setattr(delivery_module, "build_delivery_bundle", fake_build)
    args = SimpleNamespace(
        parent_manifest=str(tmp_path / "parent.json"),
        experiment_path=str(tmp_path / "experiment.json"),
        derivative_cell_id="delivery-cell",
        output_dir=str(tmp_path / "derived"),
        repo_root=str(imported_root),
        data_root=str(tmp_path / "data"),
    )
    assert cli_module.main([
        "build-delivery",
        "--parent-manifest", args.parent_manifest,
        "--experiment-path", args.experiment_path,
        "--derivative-cell-id", args.derivative_cell_id,
        "--output-dir", args.output_dir,
        "--repo-root", args.repo_root,
        "--data-root", args.data_root,
    ]) == 0
    assert calls == {
        "parent_manifest": tmp_path / "parent.json",
        "repo_root": imported_root,
        "experiment_path": tmp_path / "experiment.json",
        "data_root": tmp_path / "data",
        "derivative_cell_id": "delivery-cell",
        "output_dir": tmp_path / "derived",
    }
    output = json.loads(capsys.readouterr().out)
    assert output == {
        "manifest": str(tmp_path / "derived" / "run-manifest.json"),
        "derivative_cell_id": "delivery-cell",
    }


def test_build_delivery_rejects_foreign_explicit_repo_root(tmp_path):
    args = SimpleNamespace(
        parent_manifest=str(tmp_path / "parent.json"),
        experiment_path=str(tmp_path / "experiment.json"),
        derivative_cell_id="delivery-cell",
        output_dir=str(tmp_path / "derived"),
        repo_root=str(tmp_path / "foreign-repo"),
        data_root=str(tmp_path / "data"),
    )
    with pytest.raises(ValueError, match="imported source checkout"):
        cli_module.main([
            "build-delivery",
            "--parent-manifest", args.parent_manifest,
            "--experiment-path", args.experiment_path,
            "--derivative-cell-id", args.derivative_cell_id,
            "--output-dir", args.output_dir,
            "--repo-root", args.repo_root,
            "--data-root", args.data_root,
        ])
