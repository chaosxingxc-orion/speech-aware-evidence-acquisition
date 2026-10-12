"""``scripts/data/migrate_data_root_ext4.sh`` on synthetic roots (ruling 284, step 2).

Dry-run is the default and writes nothing; --execute copies each subtree, writes per-subtree sha256
manifests for BOTH sides and a receipt, re-points absolute symlinks that pointed into the source
root, never modifies the source, and is idempotent; a non-ext4 target is refused; --link-cold
links datasets/ and models/ and refuses to shadow a real directory. The liveness preflight
(flights, flips, serving) is bypassed with SAEA_MIGRATE_SKIP_ALIVE_CHECK=1 -- the host's own
processes are not the subject here. Skipped where bash or rsync is absent.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "data" / "migrate_data_root_ext4.sh"

pytestmark = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None or shutil.which("rsync") is None,
    reason="needs POSIX bash and rsync",
)


def _findmnt(tmp: Path, fstype: str) -> str:
    stub = tmp / f"findmnt-{fstype}"
    stub.write_text(f"#!/bin/bash\necho {fstype}\n", encoding="utf-8")
    stub.chmod(0o755)
    return str(stub)


def _run(tmp: Path, *args: str, fstype: str = "ext4") -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k not in ("SAEA_DATA_ROOT", "SPEECHRL_DATA_DIR")}
    env.update(SAEA_MIGRATE_SKIP_ALIVE_CHECK="1", SAEA_DATA_ROOT_FINDMNT=_findmnt(tmp, fstype))
    return subprocess.run(["bash", str(SCRIPT), *args], env=env, capture_output=True, text=True, check=False)


def _source(tmp: Path) -> Path:
    src = tmp / "source"
    (src / "runs" / "R1").mkdir(parents=True)
    (src / "runs" / "R1" / "rows.jsonl").write_text('{"row": 1}\n', encoding="utf-8")
    (src / "knowledge").mkdir()
    (src / "knowledge" / "snapshot.json").write_text("{}", encoding="utf-8")
    (src / "knowledge" / "abs-link").symlink_to(src / "runs" / "R1" / "rows.jsonl")
    (src / "knowledge" / "rel-link").symlink_to("snapshot.json")
    (src / "datasets" / "slurp").mkdir(parents=True)
    (src / "models").mkdir()
    (src / "loose.csv").write_text("a,b\n", encoding="utf-8")
    return src


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_symlink():
            digest.update(os.readlink(path).encode())
        elif path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    src = _source(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    result = _run(tmp_path, "--source", str(src), "--target", str(target), "--subtrees", "runs,knowledge")
    assert result.returncode == 0, result.stderr
    assert "DRY-RUN" in result.stdout and "plan  runs (target absent)" in result.stdout
    assert "--execute would proceed" in result.stdout
    assert list(target.iterdir()) == []


def test_rest_phase_excludes_the_cold_subtrees(tmp_path: Path) -> None:
    src = _source(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    result = _run(tmp_path, "--source", str(src), "--target", str(target), "--phase", "rest")
    assert result.returncode == 0, result.stderr
    assert "plan  loose.csv" in result.stdout
    assert "plan  datasets" not in result.stdout and "plan  models" not in result.stdout


def test_execute_copies_verifies_repoints_and_is_idempotent(tmp_path: Path) -> None:
    src = _source(tmp_path)
    before = _tree_digest(src)
    target = tmp_path / "target"
    target.mkdir()
    receipts = tmp_path / "receipts"
    args = ("--source", str(src), "--target", str(target), "--subtrees", "runs,knowledge,loose.csv",
            "--receipt-dir", str(receipts), "--jobs", "2", "--execute")
    first = _run(tmp_path, *args)
    assert first.returncode == 0, first.stdout + first.stderr
    assert (target / "runs" / "R1" / "rows.jsonl").read_text(encoding="utf-8") == '{"row": 1}\n'
    assert (target / "loose.csv").is_file()
    assert os.readlink(target / "knowledge" / "abs-link") == str(target / "runs" / "R1" / "rows.jsonl")
    assert os.readlink(target / "knowledge" / "rel-link") == "snapshot.json"
    assert _tree_digest(src) == before, "the source must never change"
    (run_dir,) = list(receipts.iterdir())
    receipt = json.loads((run_dir / "receipt.json").read_text(encoding="utf-8"))
    assert receipt["all_verified"] is True
    rows = {r["subtree"]: r for r in receipt["subtrees"]}
    assert rows["runs"]["files"] == 1 and rows["knowledge"]["symlinks_repointed"] == 1
    assert (run_dir / "runs.source.sha256.tsv").read_bytes() == (run_dir / "runs.target.sha256.tsv").read_bytes()
    second = _run(tmp_path, *args)
    assert second.returncode == 0, second.stdout + second.stderr
    assert len(list(receipts.iterdir())) == 2


def test_execute_flags_a_target_that_differs_from_the_source(tmp_path: Path) -> None:
    src = _source(tmp_path)
    target = tmp_path / "target"
    (target / "runs").mkdir(parents=True)
    (target / "runs" / "stray.json").write_text("{}", encoding="utf-8")
    result = _run(tmp_path, "--source", str(src), "--target", str(target), "--subtrees", "runs",
                  "--receipt-dir", str(tmp_path / "r"), "--execute")
    assert result.returncode == 4
    assert "MISMATCH" in result.stdout


def test_non_ext4_target_is_refused(tmp_path: Path) -> None:
    src = _source(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    result = _run(tmp_path, "--source", str(src), "--target", str(target), "--subtrees", "runs", "--execute",
                  fstype="tmpfs")
    assert result.returncode == 3
    assert "not ext4" in result.stdout
    assert list(target.iterdir()) == []


def test_link_cold_links_and_refuses_to_shadow(tmp_path: Path) -> None:
    src = _source(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    ok = _run(tmp_path, "--source", str(src), "--target", str(target), "--link-cold", str(src), "--execute")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert os.readlink(target / "datasets") == str(src / "datasets")
    assert os.readlink(target / "models") == str(src / "models")
    (target / "models").unlink()
    (target / "models").mkdir()
    refused = _run(tmp_path, "--source", str(src), "--target", str(target), "--link-cold", str(src), "--execute")
    assert refused.returncode == 3
    assert "real directory" in refused.stdout
