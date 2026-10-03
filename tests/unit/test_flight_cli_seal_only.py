"""``core.flight.cli seal-only`` at the command level (COMP-1 seal-only registration, 2026-09-29).

The E10d stage harness (tests/unit/test_flight_resume_seal_only.py) proves the runtime side; these
tests pin what the CLI adds around it, with a recording stand-in runtime and no model, server,
lease or GPU contact:

* a READY seal-only cell runs preflight -> preprocess -> serve -> run_phases -> seal and then the
  queue's own post-seal step, ``score(include_per_sample=True)`` (the one official finalize job),
  without any ``--expected-session-id`` or ``--lease-token-file``, and persists every stage's
  receipt including ``score``;
* a HELD cell refuses before any stage runs and leaves no receipt (a seal-only completion seals a
  real run, so readiness binds it exactly as it binds ``worker``);
* a cell whose predecessors do NOT cover the roster refuses right after preflight, before any
  zero-work stage, and never scores.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import CampaignCell, CampaignError
from speech_aware_evidence_acquisition.core.flight.receipts import (
    FLIGHT_STAGES,
    FlightReceipts,
    read_flight_receipts,
)

RUN_ID = "SAEA-SEAL-ONLY-CLI-TEST"
ATTEMPT_ID = "attempt-seal-only-cli-test"


class Runtime:
    def __init__(self, *, seal_only=True):
        self.run_id = RUN_ID
        self.attempt_id = ATTEMPT_ID
        self.receipts = FlightReceipts(RUN_ID, ATTEMPT_ID)
        self.calls: list[str] = []
        self.score_kwargs: dict | None = None
        self._seal_only = seal_only

    @property
    def is_seal_only(self) -> bool:
        return self._seal_only

    def _record(self, stage):
        self.calls.append(stage)
        self.receipts.record(stage, {"evidence": stage})

    def verify_prepared_artifacts(self):
        return ()

    def preflight(self, *, enforce_prepared_artifacts=True):
        self._record("preflight")

    def preprocess(self):
        self._record("preprocess")

    def serve(self):
        self._record("serve")

    def run_phases(self):
        self._record("run_phases")

    def seal(self):
        self._record("seal")
        return {"manifest_path": "complete-manifest.json", "status": "COMPLETED"}

    def score(self, **kwargs):
        self.score_kwargs = dict(kwargs)
        self._record("score")
        return {"operation": "finalize", "job_count": 1}

    def stop_serving(self):
        pytest.fail("a seal-only completion never touches a service")


def _cell(*, readiness="ready"):
    return CampaignCell.from_document(
        {
            "cell_id": "seal-only-cell",
            "model_fragment": "m",
            "dataset_fragment": "d",
            "baseline_fragment": "b",
            "run_id": RUN_ID,
            "attempt_id": ATTEMPT_ID,
            "allowed_execution_stages": ["check", "seal-only"],
            "readiness": {"state": readiness, "reason": "test readiness"},
        }
    )


def _args(repo, data):
    return [
        "seal-only",
        "--repo-root", str(repo),
        "--data-root", str(data),
        "--runtime-root", str(data / "runtime"),
        "--lock-path", str(data / "datasets.lock.json"),
        "--experiment", "seal-only-proof",
        "--cell", "seal-only-cell",
    ]


def _patch_cli(monkeypatch, cli, repo, runtime, *, readiness="ready"):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *args: (_cell(readiness=readiness),))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *args, **kwargs: runtime)


def test_ready_seal_only_seals_then_finalizes_without_session_or_lease(tmp_path, monkeypatch, capsys):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo, data = tmp_path / "repo", tmp_path / "data"
    runtime = Runtime()
    _patch_cli(monkeypatch, cli, repo, runtime)

    assert cli.main(_args(repo, data)) == 0

    assert runtime.calls == ["preflight", "preprocess", "serve", "run_phases", "seal", "score"]
    assert runtime.score_kwargs == {"include_per_sample": True}
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "COMPLETED"
    assert output["score"] == {"operation": "finalize", "job_count": 1}
    persisted = read_flight_receipts(data / "runs" / RUN_ID / ATTEMPT_ID / "flight-receipts.json")
    assert tuple(stage for stage in FLIGHT_STAGES if stage in persisted["stages"]) == FLIGHT_STAGES


def test_held_seal_only_cell_refuses_before_any_stage(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo, data = tmp_path / "repo", tmp_path / "data"
    runtime = Runtime()
    _patch_cli(monkeypatch, cli, repo, runtime, readiness="held")

    with pytest.raises(CampaignError, match="test readiness"):
        cli.main(_args(repo, data))

    assert runtime.calls == []
    assert not (data / "runs" / RUN_ID / ATTEMPT_ID / "flight-receipts.json").exists()


def test_not_seal_only_refuses_after_preflight_and_never_scores(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo, data = tmp_path / "repo", tmp_path / "data"
    runtime = Runtime(seal_only=False)
    _patch_cli(monkeypatch, cli, repo, runtime)

    with pytest.raises(CampaignError, match="is not seal-only"):
        cli.main(_args(repo, data))

    assert runtime.calls == ["preflight"]
    assert runtime.score_kwargs is None


def test_batch_driver_dispatches_a_seal_only_step_through_the_seal_only_mode():
    """Wiring only: a queue step of kind seal-only runs ``cli seal-only --experiment --cell``
    (never ``cli campaign``), and refuses a smoke, a campaign plan or a cell without resume_from
    before prelaunch."""

    from pathlib import Path

    driver = (Path(__file__).resolve().parents[2] / "scripts/flights/batch/batch_driver.sh").read_text(
        encoding="utf-8"
    )
    branch = driver[driver.index('if [ "$kind" = "seal-only" ]; then\n    $PY'):]
    branch = branch[: branch.index("  elif ")]
    assert "core.flight.cli seal-only" in branch
    assert '--experiment "$exp" --cell "$cell"' in branch
    assert "--expected-session-id" not in branch and "--campaign-plan" not in branch
    guard = driver[driver.index('log "step-start"'): driver.index("  prelaunch $order")]
    for refusal in ("declares a smoke", "declares a campaign_plan", "declares no resume_from"):
        assert refusal in guard
