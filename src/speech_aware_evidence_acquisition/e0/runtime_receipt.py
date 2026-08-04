"""Runtime receipt generator: llama.cpp build commit + per-file GGUF SHA-256.

Model-free by construction: it hashes bytes and reads Git metadata; it never starts
llama-server and never loads the model. The generator pre-checks everything the
gate will re-verify (file count and total bytes against the umbrella lock, clean
build tree, on-disk binary) so a bad receipt fails at generation time, not at the
first model touch. ``contracts.FrozenCoreGate`` remains the enforcement point —
receipts are verified there, never trusted.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..contracts import MODEL_LOCK_KEY, RUNTIME_RECEIPT_SCHEMA, STUDY_SLUG
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


def build_runtime_receipt(
    lock_path: Path,
    data_root: Path,
    runtime_root: Path,
    llama_dir_name: str = "llama.cpp",
    binary_relpath: str = "build/bin/llama-server",
) -> dict[str, object]:
    lock = load_lock(lock_path)
    entry = lock_entry(lock, MODEL_LOCK_KEY)
    subdir = str(entry.get("local_subdir", "")).rstrip("/")
    expected_files = entry.get("files")
    expected_bytes = entry.get("size_bytes")
    if not subdir or not isinstance(expected_files, int) or not isinstance(expected_bytes, int):
        raise ArtifactError(f"lock entry {MODEL_LOCK_KEY!r} lacks subdir/files/size_bytes")

    model_dir = Path(data_root) / subdir
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

    return {
        "schema": RUNTIME_RECEIPT_SCHEMA,
        "study": STUDY_SLUG,
        "model_lock_key": MODEL_LOCK_KEY,
        "llama_cpp": {
            "build_commit": commit,
            "binary_path": f"{llama_dir_name}/{binary_relpath}",
            "binary_bytes": binary.stat().st_size,
            "binary_sha256": sha256_file(binary),
        },
        "gguf_files": gguf_entries,
    }
