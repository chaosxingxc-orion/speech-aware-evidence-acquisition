"""Umbrella-lock resolution: the only live authority for asset identity.

The umbrella ``docs/datasets.lock.json`` is the single live source for dataset and
model identity (study client guide, routing section). This module resolves that lock
and the controlled data root fail-closed; it never copies revisions or hashes into
study code — callers read the lock at use time.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_ROOT_ENV = "SPEECHRL_DATA_DIR"

CORE_CARRIER_LOCK_KEYS = ("earnings21-original", "earnings22-original", "conec")


class AssetResolutionError(RuntimeError):
    """The lock, the data root or a required asset entry cannot be resolved."""


def umbrella_lock_path(repo_root: Path | None = None) -> Path:
    """Locate the umbrella lock in the registered adjacent-checkout layout."""

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    candidate = root.parent.parent / "docs" / "datasets.lock.json"
    if not candidate.is_file():
        raise AssetResolutionError(
            f"umbrella datasets lock not found at {candidate}; the registered layout is "
            "<umbrella>/studies/speech-aware-evidence-acquisition/"
        )
    return candidate


def load_lock(lock_path: Path) -> Mapping[str, object]:
    try:
        document = json.loads(Path(lock_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AssetResolutionError(f"cannot read datasets lock {lock_path}: {error}") from error
    if not isinstance(document, Mapping):
        raise AssetResolutionError(f"datasets lock {lock_path} must be a JSON object")
    return document


def lock_entry(lock: Mapping[str, object], name: str) -> Mapping[str, object]:
    """Find one named asset entry across every list-valued lock section."""

    for value in lock.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, Mapping) and item.get("name") == name:
                return item
    raise AssetResolutionError(f"asset {name!r} not found in the umbrella datasets lock")


def data_root() -> Path:
    """Resolve the controlled asset root from ``SPEECHRL_DATA_DIR`` (fail-closed)."""

    raw = os.environ.get(DATA_ROOT_ENV, "").strip()
    if not raw:
        raise AssetResolutionError(
            f"{DATA_ROOT_ENV} is not set; large bytes live only under the controlled "
            "data root and are never bundled with the repository"
        )
    root = Path(raw)
    if not root.is_dir():
        raise AssetResolutionError(f"{DATA_ROOT_ENV}={raw} is not an existing directory")
    return root


def asset_dir(lock: Mapping[str, object], name: str, root: Path) -> Path:
    """Resolve one asset's materialized directory under the controlled root."""

    entry = lock_entry(lock, name)
    subdir = entry.get("local_subdir")
    if not isinstance(subdir, str) or not subdir:
        raise AssetResolutionError(f"asset {name!r} lacks a usable local_subdir in the lock")
    path = Path(root) / subdir
    if not path.is_dir():
        raise AssetResolutionError(
            f"asset {name!r} is not materialized at {path}; run the umbrella fetch scripts"
        )
    return path
