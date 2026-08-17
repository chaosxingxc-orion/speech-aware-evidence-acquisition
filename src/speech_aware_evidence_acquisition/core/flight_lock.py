"""Flight lock: advisory single-flight guard for a multi-arm launch sequence
(E0-prime flight protection, 2026-08-16).

Written by ``scripts/run_arm_sequence.sh`` (via ``scripts/lib/flight_lock.sh``)
at launch, under ``$SPEECHRL_DATA_DIR/locks/flight.lock``, and removed at
terminal on any exit path (a bash ``EXIT`` trap). This module is the PYTHON
READ side only -- it never creates, refreshes, or removes the lock itself.
Reading it is always best-effort/advisory: a missing, unreadable, or
malformed lock file is never an error here, just "no launch context is
available" -- a manifest built by calling ``core.bundle.build_manifest``
directly (tests, a one-off repair, a manual ``finalize`` invocation with no
``run_arm_sequence.sh`` flight ever having run) legitimately has no flight
lock at all, and must not be penalised for that.

Consumed by ``core.bundle.git_commit``'s narrowed COMPLETED-manifest bind:
when a lock IS present, its recorded ``study_head`` is cross-checked against
the study repo's CURRENT HEAD, so a COMPLETED manifest can never bind a
commit the flight never actually ran under -- even though ordinary dirt
confined outside the load-bearing surface is now tolerated there.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

# Relative to SPEECHRL_DATA_DIR. Mirrors scripts/lib/flight_lock.sh's own
# ``flight_lock_path`` -- the two must always agree, since one writes what
# the other reads.
FLIGHT_LOCK_RELPATH = Path("locks") / "flight.lock"


def flight_lock_path(data_root: Path) -> Path:
    """The lock file path for a given data root. Pure path arithmetic --
    does not touch the filesystem."""

    return Path(data_root) / FLIGHT_LOCK_RELPATH


def read_flight_lock(data_root: Path) -> Mapping[str, object] | None:
    """Best-effort read of the flight lock. Returns ``None`` for anything
    short of a genuinely parseable JSON object: a missing file, unreadable
    bytes, malformed JSON, or a JSON value that is not itself an object.
    Never raises -- this is advisory metadata, not a source of truth a
    caller can fail-closed against by itself (the caller decides what a
    ``None`` read means for its own check)."""

    path = flight_lock_path(data_root)
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, Mapping):
        return None
    return document
