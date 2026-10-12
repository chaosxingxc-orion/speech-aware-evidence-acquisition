"""``scripts/lib/data_root.sh``: the one data-root authority (decision 274 / ruling 284).

Exercised through bash on synthetic roots: the explicit SAEA_DATA_ROOT wins and is exported as
SPEECHRL_DATA_DIR too; the implicit default meeting a different inherited SPEECHRL_DATA_DIR is a
split brain and is refused; a missing root, and a non-legacy root that is not on ext4 (a stand-in
findmnt reports tmpfs / 9p), are refused; a root on ext4 passes. Skipped where bash is absent.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
LIB = REPO / "scripts" / "lib" / "data_root.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None or os.name == "nt", reason="needs POSIX bash")


def _bash(script: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    base = {k: v for k, v in os.environ.items() if k not in ("SAEA_DATA_ROOT", "SPEECHRL_DATA_DIR")}
    return subprocess.run(["bash", "-c", f'source "{LIB}"\n{script}'], env={**base, **env},
                          capture_output=True, text=True, check=False)


def _findmnt(tmp: Path, fstype: str) -> str:
    stub = tmp / f"findmnt-{fstype}"
    stub.write_text(f"#!/bin/bash\necho {fstype}\n", encoding="utf-8")
    stub.chmod(0o755)
    return str(stub)


def test_the_default_is_assigned_exactly_once() -> None:
    text = LIB.read_text(encoding="utf-8")
    assert len(re.findall(r"^SAEA_DATA_ROOT_DEFAULT=\S+\s*$", text, re.M)) == 1


def test_explicit_root_wins_and_is_exported_as_speechrl_data_dir(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    result = _bash('saea_data_root_init || exit 9\necho "$SAEA_DATA_ROOT|$SPEECHRL_DATA_DIR"',
                   {"SAEA_DATA_ROOT": f"{root}/", "SPEECHRL_DATA_DIR": "/somewhere/else",
                    "SAEA_DATA_ROOT_FINDMNT": _findmnt(tmp_path, "ext4")})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{root}|{root}"


def test_implicit_default_with_a_different_inherited_root_is_refused(tmp_path: Path) -> None:
    result = _bash("saea_data_root_init || exit 9", {"SPEECHRL_DATA_DIR": str(tmp_path)})
    assert result.returncode == 9
    assert "REFUSED (decision 274)" in result.stderr


def test_missing_root_is_refused(tmp_path: Path) -> None:
    result = _bash("saea_data_root_init || exit 9", {"SAEA_DATA_ROOT": str(tmp_path / "absent")})
    assert result.returncode == 9
    assert "does not exist" in result.stderr


def test_dangling_hot_symlink_is_refused(tmp_path: Path) -> None:
    link = tmp_path / "saea-data"
    link.symlink_to(tmp_path / "unmounted-vhdx")
    result = _bash("saea_data_root_init || exit 9", {"SAEA_DATA_ROOT": str(link)})
    assert result.returncode == 9
    assert "SAEA-Mount-Data1" in result.stderr


@pytest.mark.parametrize("fstype", ["tmpfs", "9p"])
def test_non_ext4_root_is_refused(tmp_path: Path, fstype: str) -> None:
    root = tmp_path / "root"
    root.mkdir()
    result = _bash("saea_data_root_init || exit 9",
                   {"SAEA_DATA_ROOT": str(root), "SAEA_DATA_ROOT_FINDMNT": _findmnt(tmp_path, fstype)})
    assert result.returncode == 9
    assert f"filesystem '{fstype}'" in result.stderr


def test_ext4_root_passes(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    result = _bash("saea_data_root_init || exit 9; echo ok",
                   {"SAEA_DATA_ROOT": str(root), "SAEA_DATA_ROOT_FINDMNT": _findmnt(tmp_path, "ext4")})
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_live_entry_scripts_source_the_authority_before_any_cd() -> None:
    for rel in ("scripts/flights/batch/batch_driver.sh", "scripts/flights/batch/serving_task_entry.sh",
                "scripts/flights/direct/serving_task_entry_think.sh", "scripts/flights/batch/onepass_flip.sh"):
        text = (REPO / rel).read_text(encoding="utf-8")
        source = text.index("lib/data_root.sh")
        init = text.index("saea_data_root_init || exit 70")
        assert source < init, rel
        first_cd = re.search(r"^\s*cd ", text, re.M)
        assert first_cd is None or first_cd.start() > init, rel
