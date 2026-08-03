"""Contract 7: reproduce/evaluate refuse to run before the R0 slice is delivered."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="entrypoint rejection behavior is exercised in the POSIX runtime environment",
)


@pytest.mark.parametrize("script", ["reproduce.sh", "evaluate.sh"])
def test_pre_r0_entrypoints_reject_with_exit_2(script):
    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts" / script)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 2, f"{script} must refuse (exit 2) before R0 delivery"
    assert "not delivered" in completed.stderr
