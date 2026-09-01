"""Assembly, score-mode, and phase-combination tests for the v2 launcher."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


REPO = Path(__file__).resolve().parents[2]
LAUNCHER = (
    REPO
    / "docs/checks/speech-aware-evidence-acquisition"
    / "2026-09-01-a2t-contract-preserving-cascade-104-v2/launcher"
    / "launch_a2t_contract_preserving_cascade.py"
)


def _launcher():
    spec = importlib.util.spec_from_file_location("cpv2_launcher", LAUNCHER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_launcher_assembles_and_binds_the_frozen_identities() -> None:
    launcher = _launcher()
    assert launcher.RUN_ID == (
        "SAEA-A2T-TFRL-CONTRACT-PRESERVING-CASCADE-104-V2"
    )
    assert launcher.SPLIT_IDENTITY_SHA256 == (
        "401a28684adea908c80363df0815c9ce04b0ffa46a654975b129d4b69e60f8a1"
    )
    assert launcher.COMPOSED_CONFIG_SHA256 == (
        "ff6f8a0065279243126635caf2b648568c2b579274a2c5a44bbdfe624946dd93"
    )


def test_summary_combination_reuses_canaries_without_duplicate_contacts() -> None:
    launcher = _launcher()
    canary = SimpleNamespace(
        results=(SimpleNamespace(sample_id="a", final_response_text="one"),)
    )
    remaining = SimpleNamespace(
        results=(SimpleNamespace(sample_id="b", final_response_text="two"),)
    )
    combined = launcher._combine_phase_summaries(
        canary,
        remaining,
        expected_ids=("a", "b"),
    )
    assert [item.sample_id for item in combined.results] == ["a", "b"]

    with pytest.raises(RuntimeError, match="duplicate"):
        launcher._combine_phase_summaries(
            canary,
            canary,
            expected_ids=("a",),
        )


def test_score_batch_omits_unsupported_flag_for_default_score(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    captured: dict[str, object] = {}
    output_dir = tmp_path / "wave2"

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        output_dir.mkdir()
        (output_dir / "batch-summary.json").write_text(
            json.dumps({"failed": 0, "succeeded": 1}),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    summary = launcher._run_score_batch(
        mission_dir=tmp_path,
        name="wave2",
        jobs=({"job_id": "policy", "manifest": "/fixed/policy.json"},),
        workers=1,
        finalize=False,
    )
    assert summary == {"failed": 0, "succeeded": 1}
    assert "--score" not in captured["command"]
    assert "--finalize" not in captured["command"]


def test_score_batch_uses_existing_per_job_operation_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = _launcher()
    captured: dict[str, object] = {}
    output_dir = tmp_path / "wave1"

    def fake_run(command, **kwargs):
        captured["command"] = command
        output_dir.mkdir()
        (output_dir / "batch-summary.json").write_text(
            json.dumps({"failed": 0, "succeeded": 1}),
            encoding="utf-8",
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(launcher.subprocess, "run", fake_run)
    launcher._run_score_batch(
        mission_dir=tmp_path,
        name="wave1",
        jobs=(
            {
                "job_id": "m0",
                "manifest": "/fixed/m0.run-manifest.json",
                "operation": "score",
            },
        ),
        workers=4,
        finalize=False,
        per_job_operation=True,
    )
    assert "--per-job-operation" in captured["command"]
    assert "--finalize" not in captured["command"]


def test_policy_derivative_accepts_terminal_aborted_source() -> None:
    launcher = _launcher()
    assert launcher._terminal_policy_attempt_state("ABORTED") == "ABORTED"
    assert launcher._terminal_policy_attempt_state("FINALIZED") == "FINALIZED"
    with pytest.raises(RuntimeError, match="terminal source attempt"):
        launcher._terminal_policy_attempt_state("OPENED")


def test_repair_m0_manifest_only_adds_the_two_sealed_trace_entries(
    tmp_path: Path,
) -> None:
    launcher = _launcher()
    raw_trace = tmp_path / "run.trace.jsonl"
    trace_manifest = tmp_path / "run.trace-manifest.json"
    raw_trace.write_text("sealed raw trace\n", encoding="utf-8")
    trace_manifest.write_text("{}\n", encoding="utf-8")
    source = {
        "schema": "saea-run-manifest-v1",
        "study_commit": "d" * 40,
        "attempt": {"attempt_id": "fixed"},
        "outputs": {"sha256": "a" * 64},
        "raw_trace": None,
        "trace_manifest": None,
    }

    repaired = launcher._repair_m0_manifest_document(
        source,
        raw_trace=raw_trace,
        trace_manifest=trace_manifest,
    )

    assert repaired["study_commit"] == "d" * 40
    assert repaired["attempt"] == {"attempt_id": "fixed"}
    assert repaired["outputs"] == {"sha256": "a" * 64}
    assert repaired["raw_trace"] == {
        "path": str(raw_trace.resolve()),
        "sha256": launcher._sha256_file(raw_trace),
    }
    assert repaired["trace_manifest"] == {
        "path": str(trace_manifest.resolve()),
        "sha256": launcher._sha256_file(trace_manifest),
    }
    assert source["raw_trace"] is None


def test_trace_union_preserves_records_and_recovers_sample_responses(
    tmp_path: Path,
) -> None:
    launcher = _launcher()
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_sink = launcher.TraceSink(first, launcher.RUN_ID)
    first_sink.emit(
        "MODEL_REQUEST",
        "new-1/request",
        {
            "arm": "speech-feature-query",
            "payload": {"sample_id": "sample-1"},
            "payload_sha256": "a" * 64,
        },
    )
    first_sink.emit(
        "MODEL_RESPONSE",
        "new-1/response",
        {
            "text": "sealed response",
            "response_sha256": "b" * 64,
            "response_text_sha256": "c" * 64,
        },
    )
    first_sink.close()
    second_sink = launcher.TraceSink(second, launcher.RUN_ID)
    second_sink.emit(
        "TOOL",
        "composite-1/request",
        {"tool_id": "fixed", "source": {"source_request_id": "new-1"}},
    )
    second_sink.close()

    raw, manifest = launcher._combine_trace_artifacts(
        tmp_path / "combined", (first, second)
    )
    assert raw.is_file() and manifest.is_file()
    documents = launcher._trace_documents(tmp_path / "combined")
    assert {row["record_id"] for row in documents} == {
        "new-1/request",
        "new-1/response",
        "composite-1/request",
    }
    texts, request_ids = launcher._responses_from_trace(documents)
    assert texts == {"sample-1": "sealed response"}
    assert request_ids == {"sample-1": "new-1"}
