"""Shared artifact plumbing for the E0 generators: canonical JSON + re-measured hashes."""

from __future__ import annotations

import datetime as _datetime
import hashlib
import json
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RECEIPTS_DIR = REPO_ROOT / "docs" / "receipts"
ARTIFACTS_SUBDIR = "artifacts"

D1_ARTIFACT = "d1-identity.json"
D2_ARTIFACT = "d2-leakage.json"
D3_ARTIFACT = "d3-scoring.json"
D4_ARTIFACT = "d4-trace.json"

DELIVERABLE_ARTIFACTS = {
    "d1_identity": D1_ARTIFACT,
    "d2_leakage": D2_ARTIFACT,
    "d3_scoring": D3_ARTIFACT,
    "d4_trace": D4_ARTIFACT,
}


class ArtifactError(RuntimeError):
    """An E0 artifact cannot be generated, written or re-measured."""


def today() -> str:
    return _datetime.date.today().isoformat()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as error:
        raise ArtifactError(f"cannot hash {path}: {error}") from error
    return digest.hexdigest()


def write_json_artifact(path: Path, document: Mapping[str, object]) -> str:
    """Write canonical JSON (sorted keys, LF, trailing newline); return the byte hash.

    The returned hash is re-measured from the written file, exactly as the gate will
    re-measure it — never computed from the in-memory string alone.
    """

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    try:
        path.write_text(text, encoding="utf-8", newline="\n")
    except OSError as error:
        raise ArtifactError(f"cannot write artifact {path}: {error}") from error
    return sha256_file(path)
