"""Append-only four-axis trace sink writing outside the repository (R0)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Mapping

from ..contracts import TraceRecord
from ..e0.artifacts import REPO_ROOT, write_json_artifact

_RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


class TraceSinkError(RuntimeError):
    """The sink refuses: bad run directory, duplicate record id, or closed sink."""


class TraceSink:
    def __init__(self, run_dir: Path, run_id: str) -> None:
        run_dir = Path(run_dir)
        resolved = run_dir.resolve()
        if resolved == REPO_ROOT or REPO_ROOT in resolved.parents:
            raise TraceSinkError(
                f"trace run directory {resolved} is inside the repository; raw "
                "traces are never committed (study contract) — use SPEECHRL_DATA_DIR"
            )
        if not _RUN_ID_PATTERN.fullmatch(run_id or ""):
            raise TraceSinkError(f"invalid run id {run_id!r}")
        run_dir.mkdir(parents=True, exist_ok=True)
        self._run_dir = run_dir
        self._run_id = run_id
        self._path = run_dir / f"{run_id}.trace.jsonl"
        manifest_path = run_dir / f"{run_id}.trace-manifest.json"
        if self._path.exists() or manifest_path.exists():
            raise TraceSinkError(
                f"trace file already exists for run id {run_id!r} in {run_dir}; "
                "a re-run must use a fresh attempt directory, not overwrite a prior "
                "attempt's trace"
            )
        self._hashes: dict[str, str] = {}
        self._closed = False

    @property
    def run_id(self) -> str:
        return self._run_id

    def emit(self, channel: str, record_id: str, payload: Mapping[str, object]) -> str:
        if self._closed:
            raise TraceSinkError("sink is closed")
        if record_id in self._hashes:
            raise TraceSinkError(f"duplicate trace record id {record_id!r}")
        record = TraceRecord(channel=channel, record_id=record_id, payload=payload)
        line = record.serialize()
        digest = record.content_hash()
        with self._path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        self._hashes[record_id] = digest
        return digest

    def manifest(self) -> dict[str, str]:
        return dict(self._hashes)

    def close(self) -> str:
        self._closed = True
        return write_json_artifact(
            self._run_dir / f"{self._run_id}.trace-manifest.json",
            {"run_id": self._run_id, "records": self.manifest()},
        )
