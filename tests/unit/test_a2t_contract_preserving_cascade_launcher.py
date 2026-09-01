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
