"""Shared, pure media-path helpers (R0 repair T3, I4). Deliberately hold no
object state: the adapter and the transport each call these with THEIR OWN
root(s), so the transport's confinement check never depends on the adapter
having run first -- two independent rails, one shared syntax rule.

Split out of the former monolithic ``core/model.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import FrozenCoreError

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def _normalized_relative_path(value: object, label: str) -> str:
    """Reject anything that is not a normalized POSIX relative path: absolute,
    drive-letter, backslash, leading '/', or any '.'/'..' segment. Purely
    syntactic -- touches no filesystem -- so a forged value never reaches
    ``Path.__truediv__`` (whose join silently discards the left side for an
    absolute right side, the reproduced transport defect).

    Also refuses per-segment Windows-only looseness that would still let a
    forged relpath land on a legitimate file even though it is not, by
    itself, an escape: a trailing dot/space (Windows silently strips both
    from a path component, e.g. ``"5000001.mp3."`` -> ``"5000001.mp3"``) and
    a colon inside a segment (NTFS alternate-data-stream syntax)."""

    if not isinstance(value, str) or not value:
        raise FrozenCoreError(f"{label} must be a non-empty string")
    if "\\" in value:
        raise FrozenCoreError(f"{label} must not contain a backslash, got {value!r}")
    if value.startswith("/"):
        raise FrozenCoreError(f"{label} must be relative, got absolute path {value!r}")
    if _DRIVE_PREFIX.match(value):
        raise FrozenCoreError(f"{label} must not carry a drive letter, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise FrozenCoreError(f"{label} contains an empty or traversal segment: {value!r}")
    for part in parts:
        if part.rstrip(". ") != part:
            raise FrozenCoreError(
                f"{label} segment {part!r} has a trailing dot or space (Windows "
                f"silently strips these, so it would not name a normalized path): {value!r}"
            )
        if ":" in part:
            raise FrozenCoreError(
                f"{label} segment {part!r} contains ':' (NTFS alternate-data-stream "
                f"syntax): {value!r}"
            )
    return value


def _resolve_confined(
    join_root: Path, relative: str, confine_root: Path, label: str, *, strict: bool
) -> Path:
    """Join ``relative`` under ``join_root`` and refuse (``FrozenCoreError``) if
    the fully resolved path -- following any symlinks -- lands outside
    ``confine_root`` once both are resolved. ``strict=True`` also requires the
    final path to exist (used by the adapter, which must prove the loader
    fact-checked media is what will be sent); ``strict=False`` tolerates a
    missing leaf so a caller (the transport) can raise its own
    ``FileNotFoundError`` for that case specifically."""

    try:
        confine_resolved = Path(confine_root).resolve(strict=True)
    except OSError as error:
        raise FrozenCoreError(
            f"{label}: confinement root {confine_root} is unavailable: {error}"
        ) from error
    candidate = Path(join_root) / relative
    try:
        resolved = candidate.resolve(strict=strict)
    except OSError as error:
        raise FrozenCoreError(f"{label}: cannot resolve {candidate}: {error}") from error
    if not resolved.is_relative_to(confine_resolved):
        raise FrozenCoreError(
            f"{label} escapes its confined root {confine_root}: {relative!r}"
        )
    return resolved
