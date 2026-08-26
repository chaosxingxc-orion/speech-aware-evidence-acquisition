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
from speech_aware_evidence_acquisition.core.config import compose, protocol_hash
from speech_aware_evidence_acquisition.core.driver import main as driver_main
from speech_aware_evidence_acquisition.core.driver.run import load_split
from speech_aware_evidence_acquisition.core.session import SessionError
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
    # Second-pinned-model plumbing: a model fragment naming a NON-DEFAULT
    # runtime receipt (tests/unit/test_runtime_receipt_selection.py-style,
    # but reusing this module's own real-git-repo smoke fixture) -- proves
    # `saea-driver smoke`'s non-dry-run path genuinely reads this key rather
    # than always hard-coding "docs/receipts/runtime.json".
    (configs / "model" / "test-model-custom-receipt.json").write_text(
        json.dumps(
            {
                "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf",
                "transport": "llama-server",
                "base_url": "http://127.0.0.1:8080",
                "timeout_seconds": 300.0,
                "decoding_params": {"temperature": 0, "seed": 20260803},
                "runtime_receipt": "receipts/runtime-smoke-custom.json",
            }
        ),
        encoding="utf-8",
    )
    # A DIFFERENT declared model_lock_key than every other fragment here (all
    # of which share "qwen3-omni-30b-a3b-instruct-gguf") -- the one value
    # that can distinguish "the gate learned this run's declared key from the
    # composed config" from "the gate silently kept its own default", since
    # the two coincide for every other fragment in this module.
    (configs / "model" / "test-model-alt-key.json").write_text(
        json.dumps(
            {
                "model_lock_key": "qwen3-omni-30b-a3b-instruct-gguf-q4km",
                "transport": "llama-server",
                "base_url": "http://127.0.0.1:8080",
                "timeout_seconds": 300.0,
                "decoding_params": {"temperature": 0, "seed": 20260803},
                "runtime_receipt": "receipts/runtime-smoke-alt-key.json",
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


def test_smoke_uses_one_preregistered_plan_without_changing_its_attempt_identity(
    synthetic_world, smoke_repo, tmp_path, capsys, monkeypatch
):
    lock, repo_root = smoke_repo
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    monkeypatch.setitem(sys.modules, "mlflow", _MlflowStub())
    composed = compose(
        repo_root,
        "test-model",
        "test-dataset",
        "test-baseline",
        "test-experiment",
    )
    _ids, split_hash, split_role = load_split(
        repo_root, "discovery", lock, synthetic_world.data_root
    )
    run_id = "SAEA-E-000-smoke-preregistered"
    plan = {
        "attempt_id": "attempt-20260822T000000Z-prereg",
        "carrier_lock_key": "earnings21-original",
        "execution_profile": "bounded-discovery-probe",
        "planned_gpu_hours": 1.0,
        "planned_model_calls": 10,
        "planned_speech_audio_seconds": 1000,
        "protocol_hash": protocol_hash(composed.config_hash, "bare-core", split_hash),
        "run_id": run_id,
        "schema": "saea-execution-plan-v1",
        "split_identity_hash": split_hash,
        "split_role": split_role,
        "study": "speech-aware-evidence-acquisition",
    }
    source_plan = tmp_path / "preregistered-plan.json"
    source_plan.write_text(
        json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    ledger_cells = tmp_path / "preregistered-ledger-cells.json"
    ledger_cells.write_text(json.dumps(_HUMAN_LEDGER_CELLS), encoding="utf-8")

    exit_code = driver_main(
        [
            "smoke",
            "--model",
            "test-model",
            "--dataset",
            "test-dataset",
            "--baseline",
            "test-baseline",
            "--experiment",
            "test-experiment",
            "--run-id",
            run_id,
            "--planned-model-calls",
            "10",
            "--planned-gpu-hours",
            "1.0",
            "--planned-speech-audio-seconds",
            "1000",
            "--plan",
            str(source_plan),
            "--run-dir",
            str(tmp_path / "smoke-runs"),
            "--tracking-uri",
            str(tmp_path / "mlruns"),
            "--ledger-cells",
            str(ledger_cells),
            "--repo-root",
            str(repo_root),
            "--dry-run",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["attempt_id"] == plan["attempt_id"]
    assert json.loads(Path(payload["plan"]).read_text(encoding="utf-8")) == plan


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


def test_inference_smoke_persists_the_live_mmproj_zero_audit_before_requests(
    tmp_path, monkeypatch
):
    from types import SimpleNamespace

    from speech_aware_evidence_acquisition.core.driver.smoke import (
        _write_inference_process_audit,
    )

    session = SimpleNamespace(role="inference", session_id="inference-1", pid=42)
    expected = {
        "schema": "saea-mmproj-free-process-audit-v1",
        "session_id": "inference-1",
        "pid": 42,
        "role": "inference",
        "mmproj_loaded": False,
        "mmproj_hit_count": 0,
        "receipt_argv_checked": True,
        "live_argv_checked": True,
        "process_maps_checked": True,
        "open_files_checked": True,
    }
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.core.session.audit_mmproj_free_inference",
        lambda actual: expected if actual is session else pytest.fail("wrong session"),
    )
    output = tmp_path / "mmproj-audit.json"

    assert _write_inference_process_audit(session, output) == output
    assert json.loads(output.read_text(encoding="utf-8")) == expected

    with pytest.raises(FileExistsError):
        _write_inference_process_audit(session, output)


def test_speech_feature_server_root_cannot_drift_from_transport_root():
    from speech_aware_evidence_acquisition.core.driver.smoke import _server_env

    with pytest.raises(ValueError, match="speech feature root"):
        _server_env(
            {
                "speech_feature_root": "/home/chao/packets-a",
                "server_env": {
                    "LLAMA_SPEECH_FEATURE_ROOT": "/home/chao/packets-b",
                },
            }
        )

    assert _server_env(
        {
            "speech_feature_root": "/home/chao/packets-a",
            "server_env": {
                "LLAMA_SPEECH_FEATURE_ROOT": "/home/chao/packets-a",
            },
        }
    )["LLAMA_SPEECH_FEATURE_ROOT"] == "/home/chao/packets-a"


def test_smoke_non_dry_run_reads_the_models_custom_runtime_receipt_path(
    synthetic_world, smoke_repo, tmp_path, monkeypatch
):
    """Second-pinned-model plumbing: a NON-DRY-RUN smoke invocation with a
    model fragment naming ``runtime_receipt: "receipts/runtime-smoke-
    custom.json"`` must fail closed on THAT exact file (which does not exist
    in this synthetic repo), not on the default ``docs/receipts/
    runtime.json`` -- proving `_cli_smoke` genuinely reads the composed
    model config's own key rather than a hard-coded path."""

    lock, repo_root = smoke_repo
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    with pytest.raises(SessionError, match="runtime-smoke-custom.json"):
        driver_main(
            [
                "smoke",
                "--model", "test-model-custom-receipt",
                "--dataset", "test-dataset",
                "--baseline", "test-baseline",
                "--experiment", "test-experiment",
                "--run-id", "SAEA-E-000-smoke-custom-receipt",
                "--planned-model-calls", "10",
                "--planned-gpu-hours", "1.0",
                "--planned-speech-audio-seconds", "1000",
                "--run-dir", str(tmp_path / "smoke-runs"),
                "--runtime-root", str(tmp_path / "runtime-root-not-used"),
                "--tracking-uri", str(tmp_path / "mlruns"),
                "--repo-root", str(repo_root),
            ]
        )


def test_smoke_non_dry_run_falls_back_to_the_default_runtime_receipt_path(
    synthetic_world, smoke_repo, tmp_path, monkeypatch
):
    """The existing ``test-model`` fragment (no ``runtime_receipt`` key)
    keeps failing closed on the DEFAULT path -- unchanged behaviour for
    every fragment that predates the new key."""

    lock, repo_root = smoke_repo
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    with pytest.raises(SessionError, match="runtime.json"):
        driver_main(
            [
                "smoke",
                "--model", "test-model",
                "--dataset", "test-dataset",
                "--baseline", "test-baseline",
                "--experiment", "test-experiment",
                "--run-id", "SAEA-E-000-smoke-default-receipt",
                "--planned-model-calls", "10",
                "--planned-gpu-hours", "1.0",
                "--planned-speech-audio-seconds", "1000",
                "--run-dir", str(tmp_path / "smoke-runs"),
                "--runtime-root", str(tmp_path / "runtime-root-not-used"),
                "--tracking-uri", str(tmp_path / "mlruns"),
                "--repo-root", str(repo_root),
            ]
        )


@pytest.mark.requires_wsl2_execution_authority
def test_smoke_non_dry_run_passes_the_models_declared_model_lock_key_to_the_gate(
    synthetic_world, smoke_repo, tmp_path, monkeypatch
):
    """Identity-binding wiring (mirrors ``tests/unit/
    test_runtime_receipt_selection.py``'s equivalent ``_cli_run`` proof): the
    SAME composed config that selects the receipt PATH must also select the
    gate's identity EXPECTATION, so ``_cli_smoke`` can never keep asserting
    the frozen Q8_0 constant while resolving a genuinely different model's
    receipt file. See ``tests/contract/test_model_lock_key_binding.py`` for
    the gate's own refusal semantics once it has the wrong expectation.

    The receipt file must actually PARSE here (unlike the sibling "falls
    back"/"custom path" tests above, which prove the path selection itself
    via a missing-file refusal) -- ``_cli_smoke`` calls ``load_runtime_
    receipt`` BEFORE ``FrozenCoreGate.for_study_repo``, so a missing file
    would refuse before the spy ever observes the gate construction this
    test exists to check. An empty JSON object is enough: it fails one step
    later, inside ``start_session``, for lacking a ``llama_cpp`` mapping --
    strictly after the gate (and the spy) have already run."""

    import speech_aware_evidence_acquisition.contracts as contracts_mod

    lock, repo_root = smoke_repo
    monkeypatch.setenv("SPEECHRL_DATA_DIR", str(synthetic_world.data_root))
    monkeypatch.setattr(
        "speech_aware_evidence_acquisition.data.lock.umbrella_lock_path",
        lambda *a, **k: synthetic_world.lock_path,
    )
    receipt_path = repo_root / "docs" / "receipts" / "runtime-smoke-alt-key.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text("{}", encoding="utf-8")

    captured: dict = {}
    original = contracts_mod.FrozenCoreGate.for_study_repo.__func__

    def _spy(cls, *args, **kwargs):
        captured.update(kwargs)
        return original(cls, *args, **kwargs)

    monkeypatch.setattr(contracts_mod.FrozenCoreGate, "for_study_repo", classmethod(_spy))

    with pytest.raises(SessionError, match="llama_cpp mapping"):
        driver_main(
            [
                "smoke",
                "--model", "test-model-alt-key",
                "--dataset", "test-dataset",
                "--baseline", "test-baseline",
                "--experiment", "test-experiment",
                "--run-id", "SAEA-E-000-smoke-alt-key",
                "--planned-model-calls", "10",
                "--planned-gpu-hours", "1.0",
                "--planned-speech-audio-seconds", "1000",
                "--run-dir", str(tmp_path / "smoke-runs"),
                "--runtime-root", str(tmp_path / "runtime-root-not-used"),
                "--tracking-uri", str(tmp_path / "mlruns"),
                "--repo-root", str(repo_root),
            ]
        )

    assert captured["expected_model_lock_key"] == "qwen3-omni-30b-a3b-instruct-gguf-q4km"
    assert captured["runtime_receipt_relpath"] == "receipts/runtime-smoke-alt-key.json"
