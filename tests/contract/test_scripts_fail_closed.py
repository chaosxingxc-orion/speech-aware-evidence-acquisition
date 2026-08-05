"""Contract 7 (R0 form): entrypoints are model-free and fail closed on misuse."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="entrypoint behavior is exercised in the POSIX runtime environment",
)


@pytest.mark.parametrize("script", ["reproduce.sh", "evaluate.sh"])
def test_help_is_model_free_and_exits_zero(script):
    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / script), "--help"],
        check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 0
    assert "model-free" in completed.stdout


def test_evaluate_without_outputs_refuses_with_exit_2():
    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / "evaluate.sh")],
        check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 2
    assert "usage" in completed.stderr.lower()


@pytest.mark.parametrize("script", ["reproduce.sh", "evaluate.sh"])
def test_entrypoints_contain_no_model_touch_path(script):
    text = (REPO_ROOT / "scripts" / script).read_text(encoding="utf-8")
    assert "llama-server" not in text
    assert "chat/completions" not in text
    assert "driver run" not in text


def test_reproduce_forwards_a_runtime_root_to_the_verify_gate():
    text = (REPO_ROOT / "scripts" / "reproduce.sh").read_text(encoding="utf-8")
    assert "--runtime-root" in text
