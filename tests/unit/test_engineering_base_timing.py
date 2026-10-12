"""``scripts/checks/engineering_base_timing.py``: a model-free receipt on synthetic inputs.

A synthetic git checkout and data root are timed (import of a stdlib module, ``git status``, a
snapshot load, a small-file walk); the receipt records every sample and compares the minimum to
the manifest's timing budget. Nothing here touches the real data root.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "checks" / "engineering_base_timing.py"


def _load():
    spec = importlib.util.spec_from_file_location("engineering_base_timing", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ebt = _load()


@pytest.mark.skipif(shutil.which("git") is None, reason="needs git")
def test_receipt_on_synthetic_repo_and_root(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    root = tmp_path / "root"
    (root / "knowledge" / "a").mkdir(parents=True)
    (root / "knowledge" / "snap.json").write_text(json.dumps({"k": list(range(100))}), encoding="utf-8")
    for i in range(5):
        (root / "knowledge" / "a" / f"{i}.json").write_text("{}", encoding="utf-8")
    out = tmp_path / "receipt.json"
    code = ebt.main(["--repo", str(repo), "--root", str(root), "--module", "json", "--python", sys.executable,
                     "--snapshot-relpath", "knowledge/snap.json", "--small-count", "4", "--out", str(out)])
    receipt = json.loads(out.read_text(encoding="utf-8"))
    assert receipt["model_free"] is True
    repo_row, root_row = receipt["rows"]
    assert repo_row["cli_import"]["samples"][0]["ok"] is True
    assert repo_row["git_status"]["samples"][0]["dirty_entries"] == 0
    assert root_row["snapshot_load"]["samples"][0]["ok"] is True
    assert root_row["small_files"]["samples"][0]["files"] == 4
    assert {v["measure"] for v in receipt["verdicts"]} == {"cli_import", "git_status", "snapshot_load", "small_files"}
    assert code == (0 if receipt["all_within_budget"] else 1)


def test_missing_snapshot_is_recorded_not_raised(tmp_path: Path) -> None:
    row = ebt.measure_snapshot(tmp_path, "knowledge/absent.json")
    assert row["ok"] is False and row["seconds"] is None


def test_usage_requires_a_target() -> None:
    with pytest.raises(SystemExit):
        ebt.main([])
