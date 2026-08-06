"""Scoring-side reference access. RUNTIME-FORBIDDEN.

Reads reference transcript tokens for offline scoring only. The ONLY module
allowed to import this is core/scorers.py — an AST contract test enforces
that. References never cross the runtime boundary; they meet the hypothesis
only inside the scoring phase.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

from .lock import asset_dir, lock_entry


class ReferenceError(RuntimeError):
    """A reference layer is missing, malformed, or requested for an unknown carrier."""


_NLP_SUBDIR = {
    "earnings21-original": Path("transcripts") / "nlp_references",
    "earnings22-original": Path("transcripts") / "nlp_references",
}


def reference_file_relpath(
    lock: Mapping[str, object], carrier_lock_key: str, sample_id: str
) -> str:
    """The ``.nlp`` reference file's path, relative to the controlled data
    root -- the SAME relative-path convention :func:`reference_tokens`
    resolves internally (``asset_dir(...) / subdir / f"{sample_id}.nlp"``,
    where ``asset_dir`` is ``root / local_subdir``), exposed here as its own
    function so ``core.scorers``' reference-identity gate (IMPORTANT 2, R0
    repair fix-wave3, external-threat-model review round 3) can ask
    ``contracts.FrozenCoreGate.verify_reference_identity`` to re-hash EXACTLY
    the file :func:`reference_tokens` is about to read, from one shared path
    convention rather than a second, independently-drifting construction.
    Deliberately NOT routed through :func:`reference_tokens` itself (kept
    additive, not a refactor of that RUNTIME-FORBIDDEN, already-tested
    function) and deliberately NOT via ``asset_dir``'s own directory-must-
    exist check (the gate needs the RELATIVE path string to pass to its own
    ``_resolve_under``, which performs its own existence check)."""

    subdir = _NLP_SUBDIR.get(carrier_lock_key)
    if subdir is None:
        raise ReferenceError(f"no reference layer registered for carrier {carrier_lock_key!r}")
    entry = lock_entry(lock, carrier_lock_key)
    local_subdir = entry.get("local_subdir")
    if not isinstance(local_subdir, str) or not local_subdir:
        raise ReferenceError(
            f"asset {carrier_lock_key!r} lacks a usable local_subdir in the lock"
        )
    return f"{local_subdir.rstrip('/')}/{subdir.as_posix()}/{sample_id}.nlp"


def reference_tokens(
    lock: Mapping[str, object], root: Path, carrier_lock_key: str, sample_id: str
) -> list[str]:
    subdir = _NLP_SUBDIR.get(carrier_lock_key)
    if subdir is None:
        raise ReferenceError(f"no reference layer registered for carrier {carrier_lock_key!r}")
    path = asset_dir(lock, carrier_lock_key, root) / subdir / f"{sample_id}.nlp"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as error:
        raise ReferenceError(f"cannot read reference {path}: {error}") from error
    if not lines:
        raise ReferenceError(f"reference {path} is empty")
    header = lines[0].split("|")
    if "token" not in header:
        raise ReferenceError(f"reference {path} lacks a 'token' column: {header}")
    column = header.index("token")
    tokens: list[str] = []
    for number, line in enumerate(lines[1:], start=2):
        if not line.strip():
            continue
        cells = line.split("|")
        if len(cells) <= column:
            raise ReferenceError(f"reference {path}: malformed line {number}")
        tokens.append(cells[column])
    if not tokens:
        raise ReferenceError(f"reference {path} has no token rows")
    return tokens
