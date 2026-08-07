"""Path-safety helpers, general-audio exclusion parsing and byte measurement.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change). The GGUF cheap-identity fast-path cache that
used to live in this same file moved to ``identity_cache.py`` (R0 repair round
4, pure move) once this module crossed the repo's per-file line budget --
see that module's own docstring; nothing importing from ``contracts`` itself
changes, since ``contracts/__init__.py`` re-exports both modules' names
identically either way. ``_measure_file`` is defined here but is also a
monkeypatch target exercised through the top-level ``contracts`` package
(``tests/contract/test_runtime_identity_fastpath.py`` does
``monkeypatch.setattr(contracts, "_measure_file", spy)``) -- the callers that
actually invoke it (in ``contracts.gate``) reach it through a live reference
to the ``speech_aware_evidence_acquisition.contracts`` package object rather
than a bare/imported name, specifically so that patch is observed at the real
call sites. See ``contracts/gate.py``'s own module comment for why.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from .errors import GateClosed

_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")

# The study's excluded-carrier config is the single source of truth for which
# umbrella-lock entries are explicitly out of research scope (human speech and its
# linguistic content only: ASR, entities, contextual biasing, spoken QA, meeting
# speech). ``e0/d2_leakage.py`` already enforces, as a negative control, that no
# excluded asset name is ever hard-coded in package source -- only read from this
# config; this gate reads the same file for the same reason, so the two names
# named in it never drift apart and package source stays free of them (the only
# permitted occurrences of the excluded names themselves are inside the config
# file and inside refusal tests).
_GENERAL_AUDIO_EXCLUSION_CONFIG_RELPATH = "configs/experiment/e0-model-free-closure.yaml"
_EXCLUDED_LOCK_KEYS_MARKER = "excluded_lock_keys:"
_EXCLUDED_LOCK_KEY_LINE = re.compile(r"\s+-\s+(\S+)")


def general_audio_deny_lock_keys(repo_root: Path) -> frozenset[str]:
    """Parse the excluded-carrier denylist from the E0 experiment config.

    Mirrors ``e0.d2_leakage.excluded_lock_keys`` (kept independent rather than
    imported, to avoid a circular import: ``e0.d2_leakage`` already imports from
    this module). Fail-closed: an unreadable config or an empty list refuses
    rather than silently allowing every carrier."""

    config = Path(repo_root) / _GENERAL_AUDIO_EXCLUSION_CONFIG_RELPATH
    try:
        lines = config.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise GateClosed(
            f"cannot read general-audio exclusion config {config}: {error}"
        ) from error
    keys: list[str] = []
    collecting = False
    for line in lines:
        stripped = line.split("#", 1)[0].rstrip()
        if stripped.strip() == _EXCLUDED_LOCK_KEYS_MARKER:
            collecting = True
            continue
        if collecting:
            match = _EXCLUDED_LOCK_KEY_LINE.fullmatch(stripped)
            if match:
                keys.append(match.group(1))
                continue
            if stripped.strip():
                break
    if not keys:
        raise GateClosed(f"no excluded_lock_keys parsed from {config}")
    return frozenset(keys)


def _safe_relative_path(value: object, label: str) -> str:
    """Reject absolute paths, drive letters, backslashes and any traversal segment."""

    if not isinstance(value, str) or not value.strip():
        raise GateClosed(f"{label} must be a non-empty relative path")
    if "\\" in value or value.startswith("/") or _DRIVE_PREFIX.match(value):
        raise GateClosed(f"{label} must be a relative POSIX path, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise GateClosed(f"{label} contains empty or traversal segments: {value!r}")
    return value


def _resolve_under(root: Path, relative: str, label: str) -> Path:
    """Resolve a receipt-declared relative path strictly inside its controlled root."""

    try:
        root_resolved = Path(root).resolve(strict=True)
    except OSError as error:
        raise GateClosed(f"{label}: controlled root {root} is unavailable: {error}") from error
    candidate = (root_resolved / relative).resolve()
    if not candidate.is_relative_to(root_resolved):
        raise GateClosed(f"{label} escapes its controlled root: {relative!r}")
    if not candidate.is_file():
        raise GateClosed(f"{label} does not exist as a regular file: {relative!r}")
    return candidate


def _measure_file(path: Path, label: str) -> tuple[int, str]:
    """Re-read the actual bytes: return (size, sha256). Never trust recorded strings."""

    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
    except OSError as error:
        raise GateClosed(f"{label}: cannot read bytes: {error}") from error
    return size, digest.hexdigest()

