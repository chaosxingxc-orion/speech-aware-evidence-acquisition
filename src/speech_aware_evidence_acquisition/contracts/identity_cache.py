"""The GGUF cheap-identity fast-path cache: schema, session floor, env
override resolution and the cheap-identity (size/mtime/file-id) helpers.

Split out of ``receipts.py`` (R0 repair round 4, pure move, no behaviour
change beyond MINOR 1's own fix -- see that module's own docstring for why
``receipts.py`` was over this repo's per-file line budget) -- purely for
file size, purely a move of the "GGUF cheap-identity fast path" block that
already lived there as its own clearly-delimited section. ``_load_identity_
cache``, ``_cheap_file_identity``, ``_cheap_identity_matches``, ``_write_
identity_cache`` and ``_resolve_full_hash_override`` are defined here but
are monkeypatch targets exercised through the top-level ``contracts``
package (same discipline as ``receipts._measure_file``/``_SESSION_FULL_
HASH_DONE``, and the reason ``gate_runtime_gguf.py`` calls every one of
them via ``_contracts_pkg.<name>(...)`` rather than a bare/imported name --
see that module's own docstring, MINOR 3).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Mapping

from .errors import GateClosed
from .identifiers import STUDY_SLUG

# ---------------------------------------------------------------------------
# GGUF cheap-identity fast path (owner decision 2026-08-06,
# docs/owner-decisions-pending.md item 7): re-hashing the pinned ~34.7 GB GGUF
# set on EVERY gate open (142-175s measured over the WSL2 9p mount onto the
# Windows-hosted data root) makes routine verification painful without making
# any run safer than a cheap, well-scoped identity check already would for the
# overwhelmingly common case -- nothing about the files changed since the last
# genuine full verification. STATED GUARANTEE, precisely, not overstated
# (corrected MINOR 1, external-threat-model review round 4 -- the sentence
# this replaces claimed more than a forged cache can actually prove): a
# fast-path PASS proves two things, both from a live, zero-byte-read
# `os.stat()` this call: (1) the file's CURRENT size equals the size the
# RUNTIME RECEIPT records for it (`gate_runtime_gguf._verify_gguf_files`
# checks this unconditionally on every fast-path call, never merely trusted
# from the cache); and (2) the file's current size, last-modified time and OS
# file identity (inode+device) match an entry in a cache bound to THIS exact
# runtime receipt's own SHA-256. It does NOT prove that cache entry was
# itself ever produced by a genuine full SHA-256 read: `_write_identity_
# cache` below only ever writes an entry after a real full hash succeeded in
# THIS module, but the cache file is ordinary, unsigned JSON on disk -- an
# adversary who can write it directly (never through this module) controls
# every field it claims, and under such a forged cache no full byte read
# ever established the values it reports. So a fast-path PASS defends
# against a WRONG, PARTIAL, or ACCIDENTALLY-REPLACED model set with a
# genuinely-written cache -- a different file swapped in, a truncated or
# resumed download, a stale/foreign directory pointed to by
# SPEECHRL_DATA_DIR -- and, as of MINOR 1's fix, additionally refuses a
# per-file size mismatch against the receipt even under a forged cache
# (closing the case where a manipulated aggregate total previously masked
# it). It still does NOT defend against an adversary who edits a file's
# bytes IN PLACE while deliberately preserving its size, mtime, file
# identity AND the receipt's own recorded size (e.g. `open(path, "r+b")`
# followed by `os.utime()` restoring the original timestamp) -- that is a
# genuine, accepted, owner-approved residual weakness, not an oversight (see
# the module/FrozenCoreGate docstrings and docs/owner-decisions-pending.md
# item 7 for the full record; pinned by
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
