"""``saea-driver smoke`` (R0 operator-path repair, independent rereview §10
item 3): end to end via ``--dry-run`` on a fully synthetic world -- no real
model, no real GPU, no real llama-server process, ever.

Mirrors the established ``synthetic_world``/``bundled_repo``-style fixtures
already used throughout ``tests/unit/test_driver.py``/``tests/unit/
test_bundle.py`` (a real git repo, real frozen splits receipt, real
``configs/`` fragments), so ``smoke`` is exercised through the SAME
``compose()``/``load_split()``/``run_experiment_bundled``/``finalize_bundle``
code every other CLI subcommand test already goes through -- only the
transport/gate/session are faked, exactly as the ``--dry-run`` flag documents.
"""

from __future__ import annotations

import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

import speech_aware_evidence_acquisition.core  # noqa: F401 (populate registries)
from speech_aware_evidence_acquisition.core.driver import main as driver_main
from speech_aware_evidence_acquisition.data.lock import load_lock
from speech_aware_evidence_acquisition.data.splits import freeze_splits


def _git(repo_root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo_root, check=True, capture_output=True, text=True)


def _write_synthetic_configs(repo_root: Path) -> None:
    """The 4 real config-fragment kinds, minimal content mirroring the real
    committed fragments (``configs/model/qwen3-omni-llamacpp.json``,
    ``configs/dataset/earnings21-discovery.json``,
    ``configs/baseline/bare-core.json``,
    ``configs/experiment/r0-smoke.json``) -- ``scorers: ["cost"]`` only (not
    ``asr-wer``) so this fixture needs no D1/reference-identity receipt
    machinery; the cost scorer reads only the sibling run manifest already
    produced by the same attempt."""

    configs = repo_root / "configs"
    for kind in ("model", "dataset", "baseline", "experiment"):
        (configs / kind).mkdir(parents=True)
    (configs / "model" / "test-model.json").write_text(
        json.dumps(
            {
                "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf",
                "transport": "llama-server",
                "base_url": "http://127.0.0.1:8080",
                "timeout_seconds": 300.0,
                "decoding_params": {"temperature": 0, "seed": 20260803},
            }
        ),
        encoding="utf-8",
    )
    (configs / "dataset" / "test-dataset.json").write_text(
        json.dumps({"carrier_lock_key": "earnings21-original", "split_name": "discovery"}),
        encoding="utf-8",
    )
    (configs / "baseline" / "test-baseline.json").write_text(
        json.dumps(
            {
                "arm": "bare-core",
                "policy": "fixed",
                "evidence_source": "none",
                "evidence_mismatch": False,
                "scorers": ["cost"],
                "task_instruction": "Transcribe.",
            }
        ),
        encoding="utf-8",
    )
    (configs / "experiment" / "test-experiment.json").write_text(
        json.dumps({"experiment_id": "SAEA-E-000-smoke-test"}),
        encoding="utf-8",
    )


@pytest.fixture()
def smoke_repo(synthetic_world, tmp_path):
    """A study-repo-shaped, ACTUAL git repo distinct from the real study
    checkout: frozen splits receipt + real config fragments + a real commit
    -- mirrors ``tests/unit/test_bundle.py``'s ``bundled_repo`` fixture."""

    lock = load_lock(synthetic_world.lock_path)
    repo_root = tmp_path / "repo"
    receipts = repo_root / "docs" / "receipts"
    freeze_splits(lock, synthetic_world.data_root, receipts)
    _write_synthetic_configs(repo_root)
    _git(repo_root, "init", "-q")
    _git(repo_root, "config", "user.email", "test@example.com")
    _git(repo_root, "config", "user.name", "Test")
    _git(repo_root, "add", "-A")
    _git(repo_root, "commit", "-q", "-m", "smoke test snapshot")
    return lock, repo_root


class _MlflowStub:
    """Mirrors ``test_bundle.py``'s ``test_finalize_bundle_uploads_via_stubbed_mlflow``
    stub exactly -- ``smoke``'s ``--tracking-uri`` is REQUIRED (never silently
    skipped), so every dry-run smoke test needs this to avoid depending on a
    real, installed ``mlflow`` package."""

    def __init__(self) -> None:
        self.artifacts: list[str] = []

    def set_tracking_uri(self, uri):
        return None

    def set_experiment(self, name):
        return None

    def start_run(self, run_name):
        class _ActiveRun:
            def __enter__(self):
                return types.SimpleNamespace(info=types.SimpleNamespace(run_id="mlrun-smoke-1"))

            def __exit__(self, *exc_info):
                return False

        return _ActiveRun()

    def log_params(self, params):
        return None

    def log_metrics(self, metrics):
        return None

    def log_artifact(self, path):
        self.artifacts.append(path)


_HUMAN_LEDGER_CELLS = {
    "experiment_id": "SAEA-E-000-smoke-test",
    "speech task/carrier": "earnings21-original discovery",
    "changed axes": "none (smoke dry-run test)",
    "shared code revision": "n/a",
    "model rev": "n/a",
    "dataset rev": "n/a",
    "effectiveness": "n/a",
    "reasonableness": "n/a",
    "efficiency": "n/a",
    "deviations": "none",
    "decision": "test",
}


def _run_smoke_dry_run(monkeypatch, synthetic_world, smoke_repo, tmp_path, *, run_id):
    lock, repo_root = smoke_repo
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    stub = _MlflowStub()
    monkeypatch.setitem(sys.modules, "mlflow", stub)

    run_dir = tmp_path / "smoke-runs"
    ledger_cells_path = tmp_path / f"{run_id}-ledger-cells.json"
    if not ledger_cells_path.is_file():
        ledger_cells_path.write_text(json.dumps(_HUMAN_LEDGER_CELLS), encoding="utf-8")
    exit_code = driver_main(
        [
            "smoke",
            "--model", "test-model",
            "--dataset", "test-dataset",
            "--baseline", "test-baseline",
            "--experiment", "test-experiment",
            "--run-id", run_id,
            "--planned-model-calls", "10",
            "--planned-gpu-hours", "1.0",
            "--planned-speech-audio-seconds", "1000",
            "--run-dir", str(run_dir),
            "--tracking-uri", str(tmp_path / "mlruns"),
            "--ledger-cells", str(ledger_cells_path),
            "--repo-root", str(repo_root),
            "--dry-run",
        ]
    )
    return exit_code, run_dir, stub


def test_smoke_dry_run_end_to_end_prints_every_artifact_location(
    synthetic_world, smoke_repo, tmp_path, capsys, monkeypatch
):
    exit_code, run_dir, stub = _run_smoke_dry_run(
        monkeypatch, synthetic_world, smoke_repo, tmp_path, run_id="SAEA-E-000-smoke-dry-run"
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["run_id"] == "SAEA-E-000-smoke-dry-run"
    assert payload["dry_run"] is True
    assert payload["attempt_state"] == "FINALIZED"
    assert payload["mlflow_run"] == "mlrun-smoke-1"

    for key in ("plan", "session_receipt", "manifest", "scores", "ledger_markdown", "ledger_json"):
        path = Path(payload[key])
        assert path.is_file(), f"{key} artifact missing on disk: {path}"

    # The printed attempt directory is a FRESH subdirectory of --run-dir, not
    # --run-dir itself -- the whole point of the wrapper auto-generating a
    # fresh attempt_id (independent rereview §7.1).
    assert Path(payload["manifest"]).parent.parent == run_dir.resolve()
    assert payload["attempt_id"] in str(Path(payload["manifest"]).parent)

    plan = json.loads(Path(payload["plan"]).read_text(encoding="utf-8"))
    assert plan["attempt_id"] == payload["attempt_id"]
    assert plan["run_id"] == "SAEA-E-000-smoke-dry-run"

    # The MLflow upload genuinely ran (through the stub) -- proves
    # --tracking-uri actually reached finalize_bundle, not merely accepted
    # and ignored.
    assert len(stub.artifacts) > 0


def test_smoke_dry_run_never_reuses_an_attempt_across_two_invocations(
    synthetic_world, smoke_repo, tmp_path, capsys, monkeypatch
):
    """Two invocations against the SAME --run-dir (mirroring an operator
    re-running after a failure, or simply running smoke twice) each get a
    fresh attempt_id and a fresh attempt directory automatically -- no
    manual fresh-attempt-id/fresh-run-dir dance, and no attempt collision."""

    exit_code_1, run_dir, _ = _run_smoke_dry_run(
        monkeypatch, synthetic_world, smoke_repo, tmp_path, run_id="SAEA-E-000-smoke-repeat"
    )
    payload_1 = json.loads(capsys.readouterr().out)
    assert exit_code_1 == 0

    exit_code_2, _, _ = _run_smoke_dry_run(
        monkeypatch, synthetic_world, smoke_repo, tmp_path, run_id="SAEA-E-000-smoke-repeat"
    )
    payload_2 = json.loads(capsys.readouterr().out)
    assert exit_code_2 == 0

    assert payload_1["attempt_id"] != payload_2["attempt_id"]
    assert payload_1["manifest"] != payload_2["manifest"]
    assert Path(payload_1["manifest"]).is_file()
    assert Path(payload_2["manifest"]).is_file()


def test_smoke_requires_runtime_root_unless_dry_run(
    synthetic_world, smoke_repo, tmp_path, monkeypatch
):
    lock, repo_root = smoke_repo
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    with pytest.raises(SystemExit, match="--runtime-root is required"):
        driver_main(
            [
                "smoke",
                "--model", "test-model",
                "--dataset", "test-dataset",
                "--baseline", "test-baseline",
                "--experiment", "test-experiment",
                "--run-id", "SAEA-E-000-smoke-no-runtime-root",
                "--planned-model-calls", "10",
                "--planned-gpu-hours", "1.0",
                "--planned-speech-audio-seconds", "1000",
                "--run-dir", str(tmp_path / "smoke-runs"),
                "--tracking-uri", str(tmp_path / "mlruns"),
                "--repo-root", str(repo_root),
            ]
        )
