"""``FrozenCoreGate`` mixin: the pinned GGUF set's per-file cheap/full identity loop.

Split out of ``gate_runtime.py`` (R0 repair refactor stage 2, part C, pure
move, no behaviour change) purely for file size. See ``gate_runtime.py``'s
own module docstring for why ``_measure_file``/``_SESSION_FULL_HASH_DONE``
below go through ``_contracts_pkg`` rather than a bare/imported name --
exactly the same reasoning applies here, unchanged by which file this method
lives in.

MINOR 3 (external-threat-model review round 4): ``_load_identity_cache``,
``_cheap_file_identity``, ``_cheap_identity_matches``, ``_write_identity_
cache`` and ``_resolve_full_hash_override`` are called the SAME way, via
``_contracts_pkg.<name>(...)`` rather than a bare imported name -- before
this fix they were imported directly from ``.receipts`` instead, so they
were re-exported from ``contracts`` (and therefore LOOKED patchable) but a
``monkeypatch.setattr(contracts, "_load_identity_cache", spy)`` in a test
would never actually be observed at this module's own call site (it patches
a different name binding than the one this module reads), passing
vacuously on exactly the sub-check the fast path introduces. Only
``RUNTIME_IDENTITY_CACHE_FILENAME`` (a plain string constant, never a
monkeypatch target) and the path-safety helpers stay bare imports.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from .errors import GateClosed
from .identifiers import _SHA256
from .identity_cache import RUNTIME_IDENTITY_CACHE_FILENAME
from .receipts import _resolve_under, _safe_relative_path


class _GgufIdentityMixin:
    """``_verify_gguf_files``: the per-file cheap/full GGUF identity loop
    ``_validate_runtime`` (``gate_runtime.py``) delegates to."""

    def _verify_gguf_files(
        self,
        files: list,
        lock_entry: Mapping[str, object],
        subdir: str,
        *,
        full_hash: bool | None,
        diagnostics: dict[str, object] | None,
        require_lock_totals: bool = True,
    ) -> None:
        """Verify every entry in ``files`` against ``lock_entry``'s frozen
        totals, honoring the cheap-identity fast path / full-rehash policy
        (see ``_validate_runtime``'s own docstring for the exact True/False/
        None/``RUNTIME_FULL_HASH_ENV`` resolution order this receives
        already-resolved as ``full_hash``). Raises :class:`GateClosed` on any
        drift; never returns a value -- ``diagnostics``, if given a mutable
        dict, is populated the same way ``_validate_runtime`` itself used to
        document."""

        # Owner decision 2026-08-06 (item 7): resolve the fast/full policy and
        # the identity cache BEFORE the per-file loop. ``receipt_sha256`` is
        # the cache's binding key (item 1c) -- read directly from the
        # receipt's own bytes, independent of ``self._load``'s already-parsed
        # document, so this is a genuine re-hash of what is actually on disk,
        # not a re-derivation from the parsed JSON.
        try:
            receipt_sha256 = hashlib.sha256(Path(self.runtime_receipt).read_bytes()).hexdigest()
        except OSError as error:
            raise GateClosed(
                f"runtime receipt: cannot read bytes for identity cache: {error}"
            ) from error
        resolved_full_hash = _contracts_pkg._resolve_full_hash_override(full_hash)
        do_full = (
            resolved_full_hash
            if resolved_full_hash is not None
            else receipt_sha256 not in _contracts_pkg._SESSION_FULL_HASH_DONE
        )
        materialization_root = Path(self.model_root or self.data_root)
        cache_path = materialization_root / RUNTIME_IDENTITY_CACHE_FILENAME
        cached_entries = (
            None if do_full else _contracts_pkg._load_identity_cache(cache_path, receipt_sha256)
        )

        seen: set[str] = set()
        total_bytes = 0
        new_cache_entries: dict[str, dict[str, int]] = {}
        full_hashed_count = 0
        for index, entry in enumerate(files):
            label = f"runtime receipt gguf_files[{index}]"
            if not isinstance(entry, Mapping) or set(entry) != {"path", "bytes", "sha256"}:
                raise GateClosed(f"{label} must have exact path/bytes/sha256")
            relative = _safe_relative_path(entry["path"], f"{label}.path")
            if relative in seen:
                raise GateClosed(f"{label} duplicates model file {relative!r}")
            seen.add(relative)
            if not relative.startswith(subdir + "/"):
                raise GateClosed(
                    f"{label}.path {relative!r} is outside the lock's canonical subdir {subdir!r}"
                )
            recorded_bytes = entry["bytes"]
            recorded_sha = entry["sha256"]
            if (
                isinstance(recorded_bytes, bool)
                or not isinstance(recorded_bytes, int)
                or recorded_bytes <= 0
                or not isinstance(recorded_sha, str)
                or _SHA256.fullmatch(recorded_sha) is None
            ):
                raise GateClosed(f"{label} lacks valid bytes/sha256")
            resolved = _resolve_under(materialization_root, relative, f"{label}.path")

            cheap = _contracts_pkg._cheap_file_identity(resolved, f"{label}.path")
            cached_entry = cached_entries.get(relative) if cached_entries is not None else None
            if cached_entry is not None and _contracts_pkg._cheap_identity_matches(
                cheap, cached_entry
            ):
                # Fast path (items 1/2): size/mtime/file-id match the cache bound
                # to THIS exact runtime receipt -- skip re-reading the bytes.
                # MINOR 1 (external-threat-model review round 4): the cache is
                # NEVER an authority (module docstring) -- an attacker who can
                # write/forge the cache file directly controls what this fast
                # branch considers "matching", so the RECEIPT's own per-file
                # `bytes` (validated JSON, immune to the cache being forged)
                # must still agree with the live-stat size, zero extra I/O
                # (`cheap["size"]` already came from the `os.stat()` call just
                # above). Demonstrated defect: swapping two pinned files'
                # contents while forging matching cache stats left only the
                # AGGREGATE total checked below, which stayed correct even
                # though each individual file drifted.
                if cheap["size"] != recorded_bytes:
                    raise GateClosed(
                        f"{label} size drift (fast path): receipt {recorded_bytes}, "
                        f"actual {cheap['size']}; model touch refused"
                    )
                # STATED LIMITATION (module comment above, owner-decisions-pending
                # item 7): this defends a wrong/partial/accidentally-replaced
                # model set, NOT an adversary who edits bytes in place while
                # preserving size, mtime and OS file identity.
                actual_bytes = cheap["size"]
            else:
                actual_bytes, actual_sha = _contracts_pkg._measure_file(resolved, f"{label}.path")
                if actual_bytes != recorded_bytes:
                    raise GateClosed(
                        f"{label} size drift: receipt {recorded_bytes}, actual {actual_bytes}; "
                        "model touch refused"
                    )
                if actual_sha != recorded_sha:
                    raise GateClosed(
                        f"{label} SHA-256 drift: receipt {recorded_sha[:12]}..., "
                        f"actual {actual_sha[:12]}...; model touch refused"
                    )
                full_hashed_count += 1
            new_cache_entries[relative] = cheap
            total_bytes += actual_bytes
        if require_lock_totals and total_bytes != lock_entry["size_bytes"]:
            raise GateClosed(
                f"model files total {total_bytes} bytes but the lock freezes "
                f"{lock_entry['size_bytes']}; model touch refused"
            )

        # Persist the cache only after every GGUF file verified successfully --
        # never cache a partial/failed check. A write failure is swallowed
        # (best-effort convenience, module docstring); it never fails an already-
        # successful gate check.
        _contracts_pkg._write_identity_cache(cache_path, receipt_sha256, new_cache_entries)
        if full_hashed_count == len(files):
            # Every file was just genuinely, fully re-hashed from bytes this
            # call -- this satisfies the process/session floor (see
            # ``_SESSION_FULL_HASH_DONE``'s own docstring) regardless of
            # whether that full pass was explicitly forced or auto-decided.
            _contracts_pkg._SESSION_FULL_HASH_DONE.add(receipt_sha256)
        if diagnostics is not None:
            diagnostics["gguf_files_total"] = len(files)
            diagnostics["gguf_files_full_hashed"] = full_hashed_count
            diagnostics["gguf_fast_path_used"] = full_hashed_count == 0
