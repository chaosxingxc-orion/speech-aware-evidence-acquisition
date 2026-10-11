"""A writable overlay of the repository for DRAFT packages and tests (Linux/WSL only).

``make_overlay(dest)`` builds a directory whose read-only parts (``src``, ``scripts``, every ``configs/<kind>`` that the loop does not
write, every ``docs/*`` except ``readiness`` and the exposure ledger) are symlinks into the real repository, and whose written parts
(``configs/baseline``, ``configs/experiment``, ``configs/campaign``, ``docs/readiness``, ``docs/receipts/rosters``) are real
directories seeded with per-file symlinks, so the derive and registration scripts can run against it without touching the real
tree. The exposure ledger is COPIED so a test can append a DRAFT row without writing the real ledger.

Used by ``tests/unit/test_tfrl_iteration_cell_registration.py`` and by ``--root`` on the registration writer when an example package
is wanted outside the repository.
"""

from __future__ import annotations

import shutil
from pathlib import Path

REAL_DIRS = {"configs": {"baseline", "experiment", "campaign"}, "docs": {"readiness"}}
SEEDED_SUBDIRS = {"docs/receipts": {"rosters"}}


def _link_children(src: Path, dst: Path, skip: set[str]) -> None:
    for child in sorted(src.iterdir()):
        if child.name in skip:
            continue
        target = dst / child.name
        if not target.exists() and not target.is_symlink():
            target.symlink_to(child, target_is_directory=child.is_dir())


def _seed_dir(src: Path, dst: Path) -> None:
    """Seed ``dst`` from ``src``. Entries the loop writes (any name containing ``tfrl``) are COPIED, never linked: a write through a
    symlink would overwrite the real repository file (the live iteration packages exist, so a test run would clobber them)."""

    dst.mkdir(parents=True, exist_ok=True)
    for child in sorted(src.iterdir()):
        target = dst / child.name
        if target.exists() or target.is_symlink():
            continue
        if "tfrl" in child.name:
            if child.is_dir():
                shutil.copytree(child, target, symlinks=False)
            else:
                shutil.copyfile(child, target)
        else:
            target.symlink_to(child, target_is_directory=child.is_dir())


def make_overlay(dest: Path, repo_root: Path, *, copy_ledger: bool = True) -> Path:
    dest, repo_root = Path(dest), Path(repo_root)
    dest.mkdir(parents=True, exist_ok=True)
    for name in ("src", "scripts", "knowledge", "reference"):
        if (repo_root / name).exists() and not (dest / name).exists():
            (dest / name).symlink_to(repo_root / name, target_is_directory=True)
    for top, writable in REAL_DIRS.items():
        (dest / top).mkdir(exist_ok=True)
        _link_children(repo_root / top, dest / top, writable | {"receipts", "exposure-ledger.md"} if top == "docs" else writable)
        for sub in writable:
            _seed_dir(repo_root / top / sub, dest / top / sub)
    receipts = dest / "docs" / "receipts"
    receipts.mkdir(exist_ok=True)
    _link_children(repo_root / "docs" / "receipts", receipts, {"rosters"})
    _seed_dir(repo_root / "docs" / "receipts" / "rosters", receipts / "rosters")
    ledger = repo_root / "docs" / "exposure-ledger.md"
    if ledger.is_file() and not (dest / "docs" / "exposure-ledger.md").exists():
        if copy_ledger:
            shutil.copyfile(ledger, dest / "docs" / "exposure-ledger.md")
        else:
            (dest / "docs" / "exposure-ledger.md").symlink_to(ledger)
    return dest
