"""Contract (R0 operator-path repair, independent rereview finding B1): the
official ``python -m ...core.driver`` entry genuinely DISPATCHES, on every
platform -- not merely ``--help``/no-args inside a bash wrapper, which exit
before ever reaching Python (``tests/contract/test_scripts_fail_closed.py``'s
existing coverage).

Reproduced pre-fix failure this guards against: turning ``core/driver.py``
into a package without a ``__main__.py`` made
``python -m speech_aware_evidence_acquisition.core.driver`` refuse with
``... is a package and cannot be directly executed`` -- 712 unit tests never
caught this because they call ``driver_main([...])`` directly (in-process,
never through ``python -m``), and the shell contract test only exercises
``--help``/no-args, both of which exit inside bash before dispatch. These
tests run as REAL subprocesses (``subprocess.run([sys.executable, "-m", ...])``)
so a regression of the SAME shape (a broken module/console entry point) is
caught the same way an operator would hit it.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_MODULE = "speech_aware_evidence_acquisition.core.driver"


def test_module_help_dispatches_successfully_on_every_platform():
    """(a) ``python -m ...core.driver --help`` must exit 0 on Windows AND
    WSL/POSIX -- no ``skipif`` here, unlike the bash-only contract test."""

    completed = subprocess.run(
        [sys.executable, "-m", _MODULE, "--help"],
        check=False, capture_output=True, text=True, cwd=REPO_ROOT,
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode == 0, combined
    assert "cannot be directly executed" not in combined
    assert "saea-driver" in completed.stdout
    for subcommand in ("score", "run", "finalize", "smoke"):
        assert subcommand in completed.stdout


def test_console_script_help_dispatches_if_installed():
    """The ``saea-driver`` console script (``pyproject.toml``'s
    ``[project.scripts]``) is a second, equally-real way to reach the same
    ``main`` -- skipped only if this environment's install did not (yet)
    place the shim on PATH (e.g. a stale editable install predating this
    change; CI's ``uv sync --frozen`` always installs it fresh)."""

    console_script = shutil.which("saea-driver")
    if console_script is None:
        pytest.skip("saea-driver console script not on PATH in this environment")
    completed = subprocess.run(
        [console_script, "--help"], check=False, capture_output=True, text=True, cwd=REPO_ROOT,
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode == 0, combined
    assert "saea-driver" in completed.stdout


def _synthetic_outputs_row(tmp_path: Path) -> Path:
    outputs = tmp_path / "outputs.jsonl"
    outputs.write_text(
        json.dumps(
            {
                "sample_id": "does-not-exist-in-this-empty-data-root",
                "carrier_lock_key": "earnings21-original",
                "arm": "bare-core",
                "text": "hello world",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return outputs


def _empty_data_root_env(tmp_path: Path) -> dict:
    """A real, EXISTING, but empty directory: makes ``data_root()`` succeed
    (so dispatch proceeds past argument parsing into the scorer) while
    guaranteeing no real, private, multi-GB carrier assets are ever touched
    -- deterministic on every machine, CI included."""

    empty_data_root = tmp_path / "empty-data-root"
    empty_data_root.mkdir()
    env = dict(os.environ)
    env["SPEECHRL_DATA_DIR"] = str(empty_data_root)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def test_module_score_outputs_genuinely_reaches_the_scorer(tmp_path):
    """(b) ``python -m ...core.driver score --outputs <synthetic file>``
    must genuinely dispatch into ``core.scorers.score_asr_outputs`` -- proven
    by asserting on the scorer's own real refusal (a data-layer
    ``AssetResolutionError``, "asset ... is not materialized at ..."), not on
    an argparse/shell-branch error. No real carrier assets are needed or
    touched: the empty synthetic data root makes the scorer refuse for a
    real, meaningful, scorer-level reason."""

    outputs = _synthetic_outputs_row(tmp_path)
    env = _empty_data_root_env(tmp_path)
    completed = subprocess.run(
        [sys.executable, "-m", _MODULE, "score", "--outputs", str(outputs)],
        check=False, capture_output=True, text=True, cwd=REPO_ROOT, env=env,
    )
    combined = completed.stdout + completed.stderr
    assert "cannot be directly executed" not in combined
    assert "unrecognized arguments" not in completed.stderr
    assert "invalid choice" not in completed.stderr
    # The --outputs banner proves _cli_score's unverified-scoring branch
    # itself dispatched, before the scorer loop's own refusal below.
    assert "WARNING: unverified raw-outputs scoring" in completed.stderr
    assert completed.returncode != 0, combined
    assert "AssetResolutionError" in completed.stderr
    assert "not materialized at" in completed.stderr


@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="entrypoint behavior is exercised in the POSIX runtime environment",
)
def test_evaluate_sh_outputs_reaches_python_not_merely_a_shell_branch(tmp_path):
    """(c) ``bash scripts/evaluate.sh --outputs <synthetic>`` must likewise
    reach Python -- POSIX-only (bash), same refusal-based proof as (b)."""

    outputs = _synthetic_outputs_row(tmp_path)
    env = _empty_data_root_env(tmp_path)
    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "evaluate.sh"), "--outputs", str(outputs)],
        check=False, capture_output=True, text=True, cwd=REPO_ROOT, env=env,
    )
    combined = completed.stdout + completed.stderr
    assert "cannot be directly executed" not in combined
    assert "WARNING: unverified raw-outputs scoring" in completed.stderr
    assert completed.returncode != 0, combined
    assert "AssetResolutionError" in completed.stderr
    assert "not materialized at" in completed.stderr
