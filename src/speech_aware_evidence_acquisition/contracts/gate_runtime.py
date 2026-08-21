"""``FrozenCoreGate`` mixin: umbrella-lock model entry + runtime receipt
(llama.cpp build, GGUF set, runtime libraries) verification.

Split out of the former monolithic ``contracts.py`` (R0 repair refactor stage 1).
See ``gate_e0.py``'s module docstring for why ``_measure_file`` calls below go
through ``_contracts_pkg`` rather than a bare/imported name; the same reasoning
applies to every ``_SESSION_FULL_HASH_DONE`` read/mutation here --
``tests/unit`` and ``tests/contract/test_runtime_identity_fastpath.py`` patch
``contracts._SESSION_FULL_HASH_DONE`` (by reassignment, via
``monkeypatch.setattr``) and expect this method to observe the swap.

R0 repair refactor stage 2 (part C, pure move, no behaviour change): the
pinned GGUF set's per-file cheap/full identity loop moved to
``gate_runtime_gguf.py``'s own ``_GgufIdentityMixin`` (``_verify_gguf_files``),
purely for file size -- ``FrozenCoreGate`` (``gate.py``) composes both mixins
via multiple inheritance exactly as it already composes four others (that
module's own docstring: mixins carry only methods, so this changes nothing
about runtime behaviour).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Mapping

import speech_aware_evidence_acquisition.contracts as _contracts_pkg

from .errors import GateClosed
from .gate_runtime_gguf import _GgufIdentityMixin
from .identifiers import RUNTIME_RECEIPT_SCHEMA, RUNTIME_RECEIPT_SCHEMA_V3, _SHA256
from .receipts import _resolve_under, _safe_relative_path

_REPORTED_BUILD = re.compile(r"\(([0-9a-f]{7,40})\)")
_FULL_COMMIT = re.compile(r"[0-9a-f]{40}\Z")


class _RuntimeValidationMixin(_GgufIdentityMixin):
    """``_validate_runtime`` and its lock/GGUF/build/runtime-library helpers."""

    def _load_lock_with_hash(self) -> tuple[Mapping[str, object], str]:
        """M-3: read ``docs/datasets.lock.json`` exactly ONCE and derive both the
        parsed document and its SHA-256 from that single read.

        Before this, one ``assert_model_touch_allowed`` call independently
        re-read and re-parsed the lock file up to three times (exposure
        pre-registration, carrier scope resolution, the runtime model-entry
        lookup) -- each a separate ``open()``/``json.loads`` with no guarantee
        all three observed the same bytes, and the file's own identity never
        entered the run manifest or the ledger (a "dataset rev" cell stayed
        hand-supplied). This reads the bytes once, hashes them, and returns
        both; callers needing the parsed lock take it as a parameter instead of
        re-reading. The umbrella lock file itself is deliberately NOT frozen by
        this: it is an editable, shared, program-level asset (outside this
        repository), not a study-owned receipt -- the hash is recorded so a
        downstream reader can tell WHICH revision a run used, not to pin it.
        """

        path = Path(self.lock_path)
        try:
            raw = path.read_bytes()
        except OSError as error:
            raise GateClosed(f"datasets lock missing or unreadable ({path}): {error}") from error
        try:
            document = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise GateClosed(f"datasets lock missing or unreadable ({path}): {error}") from error
        if not isinstance(document, Mapping):
            raise GateClosed(f"datasets lock must be a JSON object ({path})")
        return document, hashlib.sha256(raw).hexdigest()

    def _lock_model_entry(self, lock: Mapping[str, object] | None = None) -> Mapping[str, object]:
        """Resolve the umbrella lock's model entry for ``self.expected_model_
        lock_key`` -- THIS run's own declared model, never a bare module
        constant. Bound to the same key ``_validate_runtime`` compares the
        receipt's own ``model_lock_key`` against, so the GGUF file-set/size
        check below can never be validated against a DIFFERENT model's lock
        entry than the one this run and its receipt both agree on."""

        if lock is None:
            lock, _ = self._load_lock_with_hash()
        models = lock.get("models")
        if not isinstance(models, list):
            raise GateClosed("datasets lock lacks a models list")
        expected = self.expected_model_lock_key
        for entry in models:
            if isinstance(entry, Mapping) and entry.get("name") == expected:
                subdir = entry.get("local_subdir")
                files = entry.get("files")
                size_bytes = entry.get("size_bytes")
                if (
                    not isinstance(subdir, str)
                    or not subdir
                    or isinstance(files, bool)
                    or not isinstance(files, int)
                    or files <= 0
                    or isinstance(size_bytes, bool)
                    or not isinstance(size_bytes, int)
                    or size_bytes <= 0
                ):
                    raise GateClosed(
                        f"datasets lock entry {expected} lacks usable "
                        "local_subdir/files/size_bytes"
                    )
                return entry
        raise GateClosed(f"frozen model key {expected!r} not found in datasets lock")

    def _validate_runtime(
        self,
        lock: Mapping[str, object] | None = None,
        *,
        full_hash: bool | None = None,
        diagnostics: dict[str, object] | None = None,
    ) -> None:
        """Verify the runtime receipt: llama.cpp build, GGUF set, runtime libraries.

        ``full_hash`` governs ONLY the GGUF set (runtime libraries below are always
        fully hashed -- module-level comment above ``_SESSION_FULL_HASH_DONE``,
        ``_validate_runtime_libraries``). Resolution order (``_resolve_full_hash_
        override``):

        1. An explicit ``True``/``False`` argument always wins.
        2. Otherwise, a recognized ``RUNTIME_FULL_HASH_ENV`` environment value is
           honored as if it had been passed explicitly (this is how
           ``scripts/reproduce.sh --full``/default reaches this gate without this
           study's frozen ``e0/`` CLI surface needing its own new argument -- see
           that constant's own comment).
        3. Otherwise (both unset/unrecognized) -- auto/session: the first call THIS
           PROCESS makes for a given runtime-receipt identity forces a full
           re-hash (ignoring even a valid pre-existing cache); subsequent calls in
           the same process behave like ``False``. This is the gate's own SAFE
           default -- a real model touch (``core.model.FrozenCoreAdapter``, which
           never overrides ``full_hash`` and does not itself set the env var)
           always pays the full cost at least once per session.

        Meaning of the resolved value once known:

        - ``True`` -- always fully re-hash every GGUF file from bytes (the
          authoritative check; ignores any cache).
        - ``False`` -- always attempt the cheap-identity fast path first, falling
          back to a full re-hash per file on any cache miss/mismatch (owner
          decision item 7, rules a/b/c).

        ``diagnostics``, if given a mutable dict, is populated with
        ``gguf_files_total``, ``gguf_files_full_hashed`` and
        ``gguf_fast_path_used`` (True iff EVERY GGUF file was verified via the
        cache this call, i.e. zero bytes were re-hashed) -- a caller that wants an
        honest, accurate report of what actually happened (never merely what was
        requested) reads this back after the call.
        """

        runtime = self._load(self.runtime_receipt, "runtime receipt")
        schema = runtime.get("schema")
        if schema not in {RUNTIME_RECEIPT_SCHEMA, RUNTIME_RECEIPT_SCHEMA_V3}:
            raise GateClosed(
                "runtime receipt schema mismatch: expected "
                f"{RUNTIME_RECEIPT_SCHEMA!r} or {RUNTIME_RECEIPT_SCHEMA_V3!r}, "
                f"found {schema!r}"
            )
        if runtime.get("study") != _contracts_pkg.STUDY_SLUG:
            raise GateClosed(
                "runtime receipt study identity mismatch: expected "
                f"{_contracts_pkg.STUDY_SLUG!r}, found {runtime.get('study')!r}"
            )
        expected_keys = {
            "schema",
            "study",
            "model_lock_key",
            "llama_cpp",
            "gguf_files",
            "runtime_libraries",
        }
        role = "legacy"
        if schema == RUNTIME_RECEIPT_SCHEMA_V3:
            expected_keys.add("role")
            role = runtime.get("role")
            if role not in {"preprocess", "inference"}:
                raise GateClosed(
                    "runtime receipt v3 role must be 'preprocess' or 'inference'"
                )
        if set(runtime) != expected_keys:
            raise GateClosed(f"runtime receipt must have exact keys {sorted(expected_keys)}")
        if runtime["model_lock_key"] != self.expected_model_lock_key:
            raise GateClosed(
                f"runtime receipt model_lock_key {runtime['model_lock_key']!r} does not match "
                f"the model this run declares ({self.expected_model_lock_key!r})"
            )
        lock_entry = self._lock_model_entry(lock)
        subdir = str(lock_entry["local_subdir"]).rstrip("/")

        files = runtime["gguf_files"]
        if not isinstance(files, list) or not files:
            raise GateClosed("runtime receipt lacks a non-empty gguf_files list")
        if role != "inference" and len(files) != lock_entry["files"]:
            raise GateClosed(
                f"runtime receipt declares {len(files)} model files but the lock freezes "
                f"{lock_entry['files']}; extra or missing model files are refused"
            )
        if role == "inference":
            if any(
                isinstance(entry, Mapping)
                and "mmproj" in Path(str(entry.get("path", ""))).name.lower()
                for entry in files
            ):
                raise GateClosed("inference runtime receipt must exclude mmproj")
        elif role == "preprocess" and not any(
            isinstance(entry, Mapping)
            and "mmproj" in Path(str(entry.get("path", ""))).name.lower()
            for entry in files
        ):
            raise GateClosed("preprocess runtime receipt must bind mmproj")
        # R0 repair refactor stage 2 (part C): the per-file cheap/full
        # identity loop over `files` lives in `_GgufIdentityMixin.
        # _verify_gguf_files` (gate_runtime_gguf.py) now -- see this class's
        # own module docstring for why the split is behaviour-preserving.
        self._verify_gguf_files(
            files,
            lock_entry,
            subdir,
            full_hash=full_hash,
            diagnostics=diagnostics,
            require_lock_totals=role != "inference",
        )

        build = runtime["llama_cpp"]
        if not isinstance(build, Mapping) or set(build) != {
            "build_commit",
            "reported_build",
            "binary_path",
            "binary_bytes",
            "binary_sha256",
        }:
            raise GateClosed(
                "runtime receipt llama_cpp must have exact "
                "build_commit/reported_build/binary_path/binary_bytes/binary_sha256"
            )
        commit = build["build_commit"]
        if not isinstance(commit, str) or _FULL_COMMIT.fullmatch(commit) is None:
            raise GateClosed(
                "llama_cpp.build_commit must be a full 40-hex commit backed by the build binary"
            )
        reported = build["reported_build"]
        reported_match = _REPORTED_BUILD.search(reported) if isinstance(reported, str) else None
        if reported_match is None or not commit.startswith(reported_match.group(1)):
            raise GateClosed(
                "llama_cpp.reported_build must carry the binary's self-reported build hash "
                "(from `llama-server --version` at receipt time) and it must prefix-match "
                f"build_commit; got {reported!r} vs {commit[:12]}..."
            )
        recorded_bytes = build["binary_bytes"]
        recorded_sha = build["binary_sha256"]
        if (
            isinstance(recorded_bytes, bool)
            or not isinstance(recorded_bytes, int)
            or recorded_bytes <= 0
            or not isinstance(recorded_sha, str)
            or _SHA256.fullmatch(recorded_sha) is None
        ):
            raise GateClosed("llama_cpp binary evidence lacks valid bytes/sha256")
        relative = _safe_relative_path(build["binary_path"], "llama_cpp.binary_path")
        binary = _resolve_under(self.runtime_root, relative, "llama_cpp.binary_path")
        actual_bytes, actual_sha = _contracts_pkg._measure_file(binary, "llama_cpp.binary_path")
        if actual_bytes != recorded_bytes or actual_sha != recorded_sha:
            raise GateClosed(
                "llama_cpp build binary drift: the receipt's build_commit is not backed by "
                "the on-disk binary bytes; model touch refused"
            )
        self._validate_runtime_libraries(runtime, relative)

    def _validate_runtime_libraries(self, runtime: Mapping[str, object], binary_rel: str) -> None:
        """The launcher is ~18 KB of stub; the inference code lives in the shared
        libraries next to it. Bind the launcher's whole directory as an exact set:
        every runtime file re-hashed, no unlisted file tolerated — a rebuilt
        ``libllama*.so`` or ``libggml-cuda.so`` re-closes the gate."""

        libraries = runtime["runtime_libraries"]
        if not isinstance(libraries, list) or not libraries:
            raise GateClosed("runtime receipt lacks a non-empty runtime_libraries list")
        bin_dir_rel = binary_rel.rsplit("/", 1)[0]
        seen: set[str] = set()
        for index, entry in enumerate(libraries):
            label = f"runtime receipt runtime_libraries[{index}]"
            if not isinstance(entry, Mapping) or set(entry) != {"path", "bytes", "sha256"}:
                raise GateClosed(f"{label} must have exact path/bytes/sha256")
            relative = _safe_relative_path(entry["path"], f"{label}.path")
            if relative in seen or relative == binary_rel:
                raise GateClosed(f"{label} duplicates runtime file {relative!r}")
            seen.add(relative)
            if relative.rsplit("/", 1)[0] != bin_dir_rel:
                raise GateClosed(
                    f"{label}.path {relative!r} is outside the launcher directory {bin_dir_rel!r}"
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
            resolved = _resolve_under(self.runtime_root, relative, f"{label}.path")
            actual_bytes, actual_sha = _contracts_pkg._measure_file(resolved, f"{label}.path")
            if actual_bytes != recorded_bytes or actual_sha != recorded_sha:
                raise GateClosed(
                    f"{label} drift: runtime library {relative!r} does not match the "
                    "receipt; model touch refused"
                )
        bin_dir = Path(self.runtime_root) / bin_dir_rel
        actual_files: set[str] = set()
        try:
            for entry in bin_dir.iterdir():
                if entry.is_file():
                    actual_files.add(f"{bin_dir_rel}/{entry.name}")
                else:
                    raise GateClosed(
                        f"runtime directory contains a non-file entry {entry.name!r} "
                        "(subdirectory or dangling symlink); the exact-set contract "
                        "covers regular files only, so nothing else may live there"
                    )
        except OSError as error:
            raise GateClosed(f"cannot enumerate runtime directory {bin_dir}: {error}") from error
        declared = seen | {binary_rel}
        if actual_files != declared:
            raise GateClosed(
                "runtime directory drift: on-disk files "
                f"{sorted(actual_files ^ declared)} are unlisted or missing versus the "
                "receipt; model touch refused"
            )
