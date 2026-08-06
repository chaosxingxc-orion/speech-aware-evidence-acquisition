"""``FrozenCoreGate`` mixin: the pinned GGUF set's per-file cheap/full identity loop.

Split out of ``gate_runtime.py`` (R0 repair refactor stage 2, part C, pure
move, no behaviour change) purely for file size. See ``gate_runtime.py``'s
own module docstring for why ``_measure_file``/``_SESSION_FULL_HASH_DONE``
below go through ``_contracts_pkg`` rather than a bare/imported name --
exactly the same reasoning applies here, unchanged by which file this method
lives in.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from .errors import GateClosed
from .identifiers import _SHA256
from .receipts import (
    RUNTIME_IDENTITY_CACHE_FILENAME,
    _cheap_file_identity,
    _cheap_identity_matches,
    _load_identity_cache,
    _resolve_full_hash_override,
    _resolve_under,
    _safe_relative_path,
    _write_identity_cache,
)


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
        resolved_full_hash = _resolve_full_hash_override(full_hash)
        do_full = (
            resolved_full_hash
            if resolved_full_hash is not None
            else receipt_sha256 not in _contracts_pkg._SESSION_FULL_HASH_DONE
        )
        cache_path = Path(self.data_root) / RUNTIME_IDENTITY_CACHE_FILENAME
        cached_entries = None if do_full else _load_identity_cache(cache_path, receipt_sha256)

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
            resolved = _resolve_under(self.data_root, relative, f"{label}.path")

            cheap = _cheap_file_identity(resolved, f"{label}.path")
            cached_entry = cached_entries.get(relative) if cached_entries is not None else None
            if cached_entry is not None and _cheap_identity_matches(cheap, cached_entry):
                # Fast path (items 1/2): size/mtime/file-id match the cache bound
                # to THIS exact runtime receipt -- skip re-reading the bytes.
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
        if total_bytes != lock_entry["size_bytes"]:
            raise GateClosed(
                f"model files total {total_bytes} bytes but the lock freezes "
                f"{lock_entry['size_bytes']}; model touch refused"
            )

        # Persist the cache only after every GGUF file verified successfully --
        # never cache a partial/failed check. A write failure is swallowed
        # (best-effort convenience, module docstring); it never fails an already-
        # successful gate check.
        _write_identity_cache(cache_path, receipt_sha256, new_cache_entries)
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
