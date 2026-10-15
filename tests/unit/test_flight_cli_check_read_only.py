"""``core.flight.cli check --read-only`` (M8, 2026-10-15): the check suppresses the one data-root write preflight makes.

A recording stand-in runtime; no model, server, lease, lock or GPU contact.
"""

from __future__ import annotations

import json

import pytest

from speech_aware_evidence_acquisition.core.flight.campaign import CampaignCell

RUN_ID = "SAEA-CHECK-READ-ONLY-TEST"
ATTEMPT_ID = "attempt-check-read-only-test"


class Runtime:
    def __init__(self, data):
        self.data = data
        self.declaration_writes = 0
        self.attempt_writes = 0

    def _write_resume_declaration(self, plan):
        self.declaration_writes += 1
        (self.data / "runs").mkdir(parents=True, exist_ok=True)

    def preflight(self, *, enforce_prepared_artifacts=True):
        self._write_resume_declaration(None)
        return {"prepared_artifacts": [], "prepared_artifacts_ok": True}


def _cell():
    return CampaignCell.from_document({
        "cell_id": "c", "model_fragment": "m", "dataset_fragment": "d", "baseline_fragment": "b", "run_id": RUN_ID, "attempt_id": ATTEMPT_ID,
        "allowed_execution_stages": ["check"], "readiness": {"state": "held", "reason": "test"},
    })


def _args(repo, data, *extra):
    return ["check", "--repo-root", str(repo), "--data-root", str(data), "--runtime-root", str(data / "rt"), "--lock-path", str(data / "lock.json"),
            "--experiment", "e", "--cell", "c", *extra]


def _patch(monkeypatch, cli, repo, runtime):
    monkeypatch.setenv("PYTHONDONTWRITEBYTECODE", "1")
    monkeypatch.setattr(cli, "__file__", str(repo / "src/package/core/flight/cli.py"))
    monkeypatch.setattr(cli, "load_campaign_cells", lambda *a: (_cell(),))
    monkeypatch.setattr(cli, "build_flight_runtime", lambda *a, **k: runtime)


def test_plain_check_keeps_its_behaviour(tmp_path, monkeypatch, capsys):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo, data = tmp_path / "repo", tmp_path / "data"
    runtime = Runtime(data)
    _patch(monkeypatch, cli, repo, runtime)
    assert cli.main(_args(repo, data)) == 0
    assert runtime.declaration_writes == 1 and (data / "runs").is_dir()
    assert "read_only" not in json.loads(capsys.readouterr().out)


def test_read_only_check_writes_nothing_under_the_data_root(tmp_path, monkeypatch, capsys):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo, data = tmp_path / "repo", tmp_path / "data"
    data.mkdir(parents=True)
    runtime = Runtime(data)
    _patch(monkeypatch, cli, repo, runtime)
    assert cli.main(_args(repo, data, "--read-only")) == 0
    assert runtime.declaration_writes == 0
    assert not (data / "runs").exists() and not (data / "attempts").exists() and not (data / "locks").exists()
    assert json.loads(capsys.readouterr().out)["read_only"] is True


def test_read_only_applies_to_check_only(tmp_path, monkeypatch):
    from speech_aware_evidence_acquisition.core.flight import cli

    repo, data = tmp_path / "repo", tmp_path / "data"
    _patch(monkeypatch, cli, repo, Runtime(data))
    with pytest.raises(SystemExit):
        cli.main(["wire-check", "--repo-root", str(repo), "--data-root", str(data), "--runtime-root", str(data), "--lock-path", str(data / "l"),
                  "--experiment", "e", "--cell", "c", "--read-only"])
