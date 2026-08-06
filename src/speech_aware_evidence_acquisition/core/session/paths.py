"""Safe-path + hashing helpers (deliberately NOT imported from contracts.py --
an independent rail, same discipline core.model's media-confinement helpers
already follow relative to contracts.py's).

Split out of the former monolithic ``core/session.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from . import SessionError

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def _safe_relative(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SessionError(f"{label} must be a non-empty relative path")
    if "\\" in value or value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise SessionError(f"{label} must be a relative POSIX path, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise SessionError(f"{label} contains empty or traversal segments: {value!r}")
    return value


def _resolve_under(root: Path, relative: str, label: str, *, must_exist: bool) -> Path:
    _safe_relative(relative, label)
    try:
        root_resolved = Path(root).resolve(strict=True)
    except OSError as error:
        raise SessionError(f"{label}: controlled root {root} is unavailable: {error}") from error
    candidate = root_resolved / relative
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as error:
        raise SessionError(f"{label}: cannot resolve {candidate}: {error}") from error
    if not resolved.is_relative_to(root_resolved):
        raise SessionError(f"{label} escapes its controlled root {root}: {relative!r}")
    return resolved


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise SessionError(f"cannot read {path}: {error}") from error
    return digest.hexdigest()
