"""Runtime receipt generator (v2): llama.cpp build + full runtime set + GGUF hashes.

Model-free by construction: it hashes bytes, reads Git metadata and asks the
launcher for its compiled-in version string (``llama-server --version`` — no model
file is passed or loaded). The launcher itself is a ~18 KB stub; the inference and
audio front-end code lives in the shared libraries next to it, so the receipt binds
**every regular file in the launcher's directory** and the gate re-verifies that
exact set. The binary's self-reported build hash must match ``git rev-parse HEAD``
of the clean tree — a stale build left over from an older commit is refused at
generation time. ``contracts.FrozenCoreGate`` remains the enforcement point —
receipts are verified there, never trusted.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..contracts import (
    MODEL_LOCK_KEY,
    RUNTIME_RECEIPT_SCHEMA,
    RUNTIME_RECEIPT_SCHEMA_V3,
    STUDY_SLUG,
)
from ..data.lock import load_lock, lock_entry
from .artifacts import ArtifactError, sha256_file


def _git(runtime_dir: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(runtime_dir), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise ArtifactError(
            f"git {' '.join(args)} failed in {runtime_dir}: {completed.stderr.strip()}"
        )
    return completed.stdout.strip()


_REPORTED_BUILD = re.compile(r"\(([0-9a-f]{7,40})\)")


def _reported_build_line(binary: Path) -> str:
    """First version line the launcher reports about itself (no model is loaded)."""

    try:
        completed = subprocess.run(
            [str(binary), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ArtifactError(f"cannot execute {binary} --version: {error}") from error
    output = (completed.stdout + "\n" + completed.stderr).strip()
    for line in output.splitlines():
        if _REPORTED_BUILD.search(line):
            return line.strip()
    raise ArtifactError(
        f"cannot parse a build hash from `{binary} --version` output: {output[:200]!r}"
    )


def build_runtime_receipt(
    lock_path: Path,
    data_root: Path,
    runtime_root: Path,
    llama_dir_name: str = "llama.cpp",
    binary_relpath: str = "build/bin/llama-server",
    model_lock_key: str = MODEL_LOCK_KEY,
    role: str | None = None,
    model_root: Path | None = None,
) -> dict[str, object]:
    """Build a runtime receipt for ``model_lock_key`` (default: the frozen
    Q8_0 :data:`~..contracts.MODEL_LOCK_KEY`).

    Passing a different umbrella-lock model entry name lets a SECOND pinned
    model (e.g. a Q4_K_M requant, materialized under its own directory) get
    its own truthful receipt without touching the default key or its
    callers -- the returned document's own ``model_lock_key`` field always
    records exactly the key that was actually used to resolve ``files``/
    ``size_bytes`` below, never the frozen constant unconditionally. Note
    this function only BUILDS the receipt; ``contracts.FrozenCoreGate``
    still enforces its own (currently single, frozen) ``MODEL_LOCK_KEY``
    equality check at gate-open time -- see ``gate_runtime.py``.
    """

    if role not in {None, "preprocess", "inference"}:
        raise ArtifactError("runtime receipt role must be preprocess, inference, or None")
    lock = load_lock(lock_path)
    entry = lock_entry(lock, model_lock_key)
    subdir = str(entry.get("local_subdir", "")).rstrip("/")
    expected_files = entry.get("files")
    expected_bytes = entry.get("size_bytes")
    if not subdir or not isinstance(expected_files, int) or not isinstance(expected_bytes, int):
        raise ArtifactError(f"lock entry {model_lock_key!r} lacks subdir/files/size_bytes")

    materialization_root = Path(model_root) if model_root is not None else Path(data_root)
    model_dir = materialization_root / subdir
    if not model_dir.is_dir():
        raise ArtifactError(f"model directory missing: {model_dir}")
    model_files = sorted(path for path in model_dir.iterdir() if path.is_file())
    if len(model_files) != expected_files:
        raise ArtifactError(
            f"model directory holds {len(model_files)} files but the lock freezes "
            f"{expected_files}: {sorted(path.name for path in model_files)}"
        )
    gguf_entries = []
    total = 0
    for path in model_files:
        size = path.stat().st_size
        gguf_entries.append(
            {
                "path": f"{subdir}/{path.name}",
                "bytes": size,
                "sha256": sha256_file(path),
            }
        )
        total += size
    if total != expected_bytes:
        raise ArtifactError(
            f"model files total {total} bytes; the umbrella lock freezes {expected_bytes}"
        )

    llama_dir = Path(runtime_root) / llama_dir_name
    if not llama_dir.is_dir():
        raise ArtifactError(f"llama.cpp checkout missing: {llama_dir}")
    commit = _git(llama_dir, "rev-parse", "HEAD")
    dirty = _git(llama_dir, "status", "--porcelain")
    if dirty:
        raise ArtifactError(
            f"llama.cpp tree at {llama_dir} is dirty; a receipt commit must describe "
            f"the built tree exactly:\n{dirty}"
        )
    binary = llama_dir / binary_relpath
    if not binary.is_file():
        raise ArtifactError(f"llama-server binary missing: {binary}")

    reported = _reported_build_line(binary)
    reported_hash = _REPORTED_BUILD.search(reported).group(1)
    if not commit.startswith(reported_hash):
        raise ArtifactError(
            f"stale or foreign build: the binary reports build {reported_hash!r} but the "
            f"clean tree is at {commit!r}; rebuild from the checked-out commit first"
        )

    binary_rel = f"{llama_dir_name}/{binary_relpath}"
    bin_dir = binary.parent
    library_entries = []
    for path in sorted(bin_dir.iterdir()):
        if not path.is_file():
            raise ArtifactError(
                f"runtime directory {bin_dir} contains a non-file entry {path.name!r} "
                "(subdirectory or dangling symlink); the exact-set receipt covers "
                "regular files only, so nothing else may live there"
            )
        if path.name == binary.name:
            continue
        library_entries.append(
            {
                "path": f"{binary_rel.rsplit('/', 1)[0]}/{path.name}",
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    if not library_entries:
        raise ArtifactError(
            f"no runtime libraries found next to {binary}; a lone launcher stub cannot "
            "be the inference runtime"
        )

    receipt_files = gguf_entries
    if role == "inference":
        receipt_files = [
            entry
            for entry in gguf_entries
            if "mmproj" not in Path(str(entry["path"])).name.lower()
        ]
        if not receipt_files:
            raise ArtifactError("inference runtime receipt found no decoder GGUF")
    if role == "preprocess" and not any(
        "mmproj" in Path(str(entry["path"])).name.lower() for entry in receipt_files
    ):
        raise ArtifactError("preprocess runtime receipt found no mmproj GGUF")

    receipt: dict[str, object] = {
        "schema": RUNTIME_RECEIPT_SCHEMA if role is None else RUNTIME_RECEIPT_SCHEMA_V3,
        "study": STUDY_SLUG,
        "model_lock_key": model_lock_key,
        "llama_cpp": {
            "build_commit": commit,
            "reported_build": reported,
            "binary_path": binary_rel,
            "binary_bytes": binary.stat().st_size,
            "binary_sha256": sha256_file(binary),
        },
        "gguf_files": receipt_files,
        "runtime_libraries": library_entries,
    }
    if role is not None:
        receipt["role"] = role
    return receipt
