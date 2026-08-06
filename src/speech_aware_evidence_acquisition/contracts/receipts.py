"""Path-safety helpers, general-audio exclusion parsing, byte measurement and the
GGUF cheap-identity fast-path cache.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1,
pure move, no behaviour change). ``_measure_file`` and ``_SESSION_FULL_HASH_DONE``
are defined here but are also monkeypatch targets exercised through the top-level
``contracts`` package (``tests/contract/test_runtime_identity_fastpath.py`` does
``monkeypatch.setattr(contracts, "_measure_file", spy)`` and
``monkeypatch.setattr(contracts, "_SESSION_FULL_HASH_DONE", set())``) -- the
callers that actually invoke them (in ``contracts.gate``) reach them through a
live reference to the ``speech_aware_evidence_acquisition.contracts`` package
object rather than a bare/imported name, specifically so that patch is observed
at the real call sites. See ``contracts/gate.py``'s own module comment for why.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Mapping

from .errors import GateClosed
from .identifiers import STUDY_SLUG

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


# ---------------------------------------------------------------------------
# GGUF cheap-identity fast path (owner decision 2026-08-06,
# docs/owner-decisions-pending.md item 7): re-hashing the pinned ~34.7 GB GGUF
# set on EVERY gate open (142-175s measured over the WSL2 9p mount onto the
# Windows-hosted data root) makes routine verification painful without making
# any run safer than a cheap, well-scoped identity check already would for the
# overwhelmingly common case -- nothing about the files changed since the last
# genuine full verification. STATED GUARANTEE, precisely, not overstated: a
# fast-path PASS proves the file at this path has the same size, last-modified
# time and OS file identity (inode+device) as it did the last time this
# process (or an earlier trusted cache write) actually read every byte and
# recomputed its SHA-256. It defends against a WRONG, PARTIAL, or
# ACCIDENTALLY-REPLACED model set -- a different file swapped in, a truncated
# or resumed download, a stale/foreign directory pointed to by
# SPEECHRL_DATA_DIR. It does NOT defend against an adversary who edits a
# file's bytes IN PLACE while deliberately preserving its size, mtime and file
# identity (e.g. `open(path, "r+b")` followed by `os.utime()` restoring the
# original timestamp) -- that is a genuine, accepted, owner-approved residual
# weakness, not an oversight (see the module/FrozenCoreGate docstrings and
# docs/owner-decisions-pending.md item 7 for the full record; pinned by
# ``tests/contract/test_runtime_identity_fastpath.py``).
# ---------------------------------------------------------------------------

RUNTIME_IDENTITY_CACHE_SCHEMA = "saea-runtime-identity-cache-v1"
RUNTIME_IDENTITY_CACHE_FILENAME = ".saea-runtime-identity-cache.json"

# Process-local floor: ``FrozenCoreGate.assert_model_touch_allowed``'s own
# default (``full_hash=None``, and no recognized ``RUNTIME_FULL_HASH_ENV``
# override -- see below) must still perform ONE genuine full SHA-256
# verification of the pinned GGUF set, per runtime-receipt identity, per
# process, before it will ever trust a fast-path cheap-identity cache -- even
# a pre-existing, on-disk, apparently-valid one written by an EARLIER process
# (e.g. a prior ``scripts/reproduce.sh`` dry run). Keyed by the runtime
# receipt's own SHA-256 (not a bare process-wide bool) so a receipt rotation
# mid-process is treated as a genuinely new floor, never silently inherited
# from a stale receipt this process happened to fully verify earlier. There is
# no cross-process synchronization by design: "session" here means exactly
# "this interpreter process" (reset only by process restart) -- a real model
# touch (``core.model.FrozenCoreAdapter``, which never overrides ``full_hash``
# and runs in its own freshly-started process) therefore always pays the full
# cost at least once before it can ever be fast-pathed within that same run,
# UNLESS ``RUNTIME_FULL_HASH_ENV`` happens to already be set to a fast value in
# that process's own environment -- an operational responsibility of whatever
# launched it, not a gap in this module (see ``RUNTIME_FULL_HASH_ENV``'s own
# comment for why ``scripts/reproduce.sh`` setting it is safe: the export is
# scoped to that script's own short-lived subprocess tree, never a parent
# interactive shell).
_SESSION_FULL_HASH_DONE: set[str] = set()

# ``src/.../e0/**`` is a frozen, previously-reviewed surface this task does not
# touch, so the CLI (``e0.generate._verify``, invoked by ``scripts/
# reproduce.sh``) cannot be given a new ``--full`` argument to forward as an
# explicit ``full_hash=`` keyword the way a real caller could. Instead, when a
# caller passes ``full_hash=None`` (its own default -- the CLI never overrides
# this), this environment variable is consulted BEFORE falling back to the
# session/process floor above: a recognized value is honored as if the caller
# had passed that literal bool; anything unset or unrecognized falls through
# to the safe auto/session behavior (never silently treated as either explicit
# value). ``scripts/reproduce.sh`` exports this only around its own `python -m
# ... verify` invocation -- a subprocess of that one script run, never
# persisted into the caller's interactive shell -- so a real model touch
# started independently, in a separate shell command, is unaffected by it.
RUNTIME_FULL_HASH_ENV = "SAEA_RUNTIME_FULL_HASH"
_ENV_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_ENV_FALSE_VALUES = frozenset({"0", "false", "no", "off"})


def _resolve_full_hash_override(explicit: bool | None) -> bool | None:
    """An explicit caller value always wins. Otherwise a recognized
    ``RUNTIME_FULL_HASH_ENV`` value is honored as if it had been passed
    explicitly. Anything unset or unrecognized returns ``None`` unchanged --
    "let the auto/session floor decide" (the safe behavior) -- a malformed
    environment value therefore fails toward the SAFE (full-hash) side, never
    silently toward the fast one."""

    if explicit is not None:
        return explicit
    raw = os.environ.get(RUNTIME_FULL_HASH_ENV)
    if raw is None:
        return None
    normalized = raw.strip().lower()
    if normalized in _ENV_TRUE_VALUES:
        return True
    if normalized in _ENV_FALSE_VALUES:
        return False
    return None


_CHEAP_IDENTITY_FIELDS = ("size", "mtime_ns", "st_ino", "st_dev")


def _cheap_file_identity(path: Path, label: str) -> dict[str, int]:
    """No-byte-read file identity: size, last-modified time (nanoseconds) and
    OS file identity (inode + device). ``os.stat`` is used UNCHANGED on every
    platform this study runs on: on POSIX (the WSL2/ext4 compute authority)
    ``st_ino``/``st_dev`` are the kernel's own inode/device pair; on Windows,
    CPython's own ``os.stat`` already populates the SAME two attributes from
    the NTFS file ID via ``GetFileInformationByHandle`` -- verified
    empirically on this checkout (stable and non-zero across repeated
    ``os.stat()`` calls on the same file) -- so no separate ``ctypes``/
    ``nFileIndex`` path was needed."""

    try:
        info = path.stat()
    except OSError as error:
        raise GateClosed(f"{label}: cannot stat for cheap identity check: {error}") from error
    return {
        "size": info.st_size,
        "mtime_ns": info.st_mtime_ns,
        "st_ino": info.st_ino,
        "st_dev": info.st_dev,
    }


def _cheap_identity_matches(current: Mapping[str, int], cached: object) -> bool:
    """Every cheap-identity field must be present, integral and equal. A
    missing/malformed cached record (or a non-mapping) never matches -- the
    caller then falls back to a full re-hash, fail-safe."""

    if not isinstance(cached, Mapping):
        return False
    for field in _CHEAP_IDENTITY_FIELDS:
        value = cached.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or current[field] != value:
            return False
    return True


def _load_identity_cache(
    cache_path: Path, receipt_sha256: str
) -> Mapping[str, Mapping[str, int]] | None:
    """Fail-safe: any missing, unreadable, malformed or receipt-mismatched
    cache is treated as simply ABSENT (never fail-open) -- the caller then
    re-hashes every file for real. Never raises."""

    try:
        raw = cache_path.read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        document = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, Mapping):
        return None
    if (
        document.get("schema") != RUNTIME_IDENTITY_CACHE_SCHEMA
        or document.get("study") != STUDY_SLUG
        # Bound to the runtime receipt's own bytes (item 1c): any change to
        # the receipt -- a new build, a re-pinned file, even an unrelated
        # field -- invalidates every cached identity record outright.
        or document.get("runtime_receipt_sha256") != receipt_sha256
    ):
        return None
    entries = document.get("gguf_files")
    if not isinstance(entries, Mapping):
        return None
    return entries


def _write_identity_cache(
    cache_path: Path, receipt_sha256: str, entries: Mapping[str, Mapping[str, int]]
) -> None:
    """Best-effort convenience write: the cache is never an authority (module
    docstring above), so a write failure (read-only mount, disk full,
    permissions) must never fail a gate check that has already genuinely
    succeeded -- it only means the NEXT gate open pays the full cost again.
    Atomic (write-then-replace) so a process interrupted mid-write never
    leaves a half-written, misleadingly-parseable cache file behind."""

    document = {
        "schema": RUNTIME_IDENTITY_CACHE_SCHEMA,
        "study": STUDY_SLUG,
        "runtime_receipt_sha256": receipt_sha256,
        "gguf_files": entries,
    }
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_name(f"{cache_path.name}.tmp-{os.getpid()}")
        tmp_path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        tmp_path.replace(cache_path)
    except OSError:
        pass
