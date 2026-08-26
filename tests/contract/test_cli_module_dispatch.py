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

CONTROLLER-FLAGGED REGRESSION (fixed here): a real child interpreter spawned
by ``subprocess.run`` does NOT inherit this (parent) process's
``sys.dont_write_bytecode`` -- only ``tests/conftest.py``'s guards apply
in-process. The first version of this file spawned ``sys.executable``
without disabling bytecode writing in the CHILD, which wrote fresh
``.pyc`` files into the frozen ``src/speech_aware_evidence_acquisition/
scoring/__pycache__`` directory -- exactly the shape
``contracts.FrozenCoreGate._validate_scoring_freeze``'s M-1 hardening
refuses (correctly: a forged/relocated ``.pyc`` next to frozen sources is
what CPython would actually execute), so every OTHER test later in the same
session that opens the real gate against this checkout's real ``scoring/``
started failing too -- cross-test interference, not a per-file break. Every
subprocess below now explicitly disables bytecode writing in the CHILD
(``-B`` on the interpreter invocation AND ``PYTHONDONTWRITEBYTECODE=1`` in
its environment, belt-and-suspenders, since the console-script/bash forms
cannot take a bare interpreter flag); ``tests/conftest.py`` additionally now
purges ``scoring/__pycache__`` after EVERY test (not merely once per
session) as a self-healing backstop regardless of the source.
``test_module_dispatch_never_leaves_stray_bytecode_in_the_frozen_scoring_package``
below is the direct regression test for this.
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
_SCORING_PYCACHE = REPO_ROOT / "src" / "speech_aware_evidence_acquisition" / "scoring" / "__pycache__"

_MODULE = "speech_aware_evidence_acquisition.core.driver"


def _no_bytecode_env(overrides: dict | None = None) -> dict:
    """This process's environment, with bytecode writing explicitly disabled
    for any CHILD process -- ``sys.dont_write_bytecode`` (set for THIS
    process by ``tests/conftest.py``) is never inherited across
    ``subprocess.run``; only ``PYTHONDONTWRITEBYTECODE`` in the child's own
    environment is. Every subprocess this module spawns must use this (or
    the equivalent ``-B`` interpreter flag) -- see the module docstring's
    controller-flagged regression."""

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if overrides:
        env.update(overrides)
    return env


def test_module_help_dispatches_successfully_on_every_platform():
    """(a) ``python -m ...core.driver --help`` must exit 0 on Windows AND
    WSL/POSIX -- no ``skipif`` here, unlike the bash-only contract test."""

    completed = subprocess.run(
        [sys.executable, "-B", "-m", _MODULE, "--help"],
        check=False, capture_output=True, text=True, cwd=REPO_ROOT, env=_no_bytecode_env(),
    )
    combined = completed.stdout + completed.stderr
    assert completed.returncode == 0, combined
    assert "cannot be directly executed" not in combined
    assert "saea-driver" in completed.stdout
    for subcommand in ("score", "run", "finalize", "smoke"):
        assert subcommand in completed.stdout


def test_module_dispatch_never_leaves_stray_bytecode_in_the_frozen_scoring_package():
    """Direct regression test for the controller-flagged finding: a real
    subprocess dispatch through ``python -m ...core.driver`` (which
    transitively imports ``core.scorers`` -> ``scoring.*``) must NEVER write
    ``.pyc`` files into the frozen scoring package -- that is exactly what
    ``contracts.FrozenCoreGate._validate_scoring_freeze``'s M-1 hardening
    refuses, and a poisoned tree breaks every OTHER gate-opening test later
    in the same session, not just this one. Asserted INSIDE the test body,
    before this module's own teardown purge (a defense-in-depth backstop,
    not what this assertion relies on) ever runs -- so this genuinely proves
    the subprocess spawn itself is clean, not merely that cleanup happened
    afterward."""

    assert not _SCORING_PYCACHE.exists(), (
        f"{_SCORING_PYCACHE} already existed BEFORE this test spawned anything -- "
        "a prior test or process left it; this test cannot prove its own subprocess "
        "is what created it"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-m", _MODULE, "score", "--help"],
        check=False, capture_output=True, text=True, cwd=REPO_ROOT, env=_no_bytecode_env(),
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert not _SCORING_PYCACHE.exists(), (
        f"{_SCORING_PYCACHE} was created by the subprocess above -- it does not "
        "have bytecode writing disabled (regression of the controller-flagged finding)"
    )


def test_console_script_help_dispatches_if_installed():
    """The ``saea-driver`` console script (``pyproject.toml``'s
    ``[project.scripts]``) is a second, equally-real way to reach the same
    ``main`` -- skipped only if this environment's install did not (yet)
    place the shim on PATH (e.g. a stale editable install predating this
    change; CI's ``uv sync --frozen`` always installs it fresh). No ``-B``
    available here (it is not a bare ``python`` invocation) -- the
    environment variable is the only lever, same as the bash form below."""

    console_script = shutil.which("saea-driver")
    if console_script is None:
        pytest.skip("saea-driver console script not on PATH in this environment")
    completed = subprocess.run(
        [console_script, "--help"],
        check=False, capture_output=True, text=True, cwd=REPO_ROOT, env=_no_bytecode_env(),
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
    -- deterministic on every machine, CI included. Bytecode writing is
    disabled the same way as every other subprocess in this module."""

    empty_data_root = tmp_path / "empty-data-root"
    empty_data_root.mkdir()
    return _no_bytecode_env({"SPEECHRL_DATA_DIR": str(empty_data_root)})


@pytest.mark.requires_umbrella_checkout
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
        [sys.executable, "-B", "-m", _MODULE, "score", "--outputs", str(outputs)],
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
@pytest.mark.requires_umbrella_checkout
def test_evaluate_sh_outputs_reaches_python_not_merely_a_shell_branch(tmp_path):
    """(c) ``bash scripts/evaluate.sh --outputs <synthetic>`` must likewise
    reach Python -- POSIX-only (bash), same refusal-based proof as (b). No
    ``-B`` available (the script invokes ``python`` itself, not this call) --
    the environment variable set on the ``bash`` child is inherited by the
    ``python`` grandchild ``evaluate.sh`` execs, which is sufficient."""

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
