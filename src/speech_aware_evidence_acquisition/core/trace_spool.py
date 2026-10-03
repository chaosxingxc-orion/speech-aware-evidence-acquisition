"""Store pending trace payloads on disk without changing canonical trace order.

This is an intermediate record store, not a KV cache, a result manifest or a
resume mechanism. Keep files after success and failure. Bound encoded record
and disk bytes; do not describe those bounds as a total process-RSS limit.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import threading
from time import monotonic_ns
from uuid import uuid4

from ..contracts import RUN_ID_PATTERN
from ..e0.artifacts import REPO_ROOT


class TraceSpoolError(ValueError):
    """Refuse changed, oversized or unavailable intermediate evidence."""


@dataclass(frozen=True, slots=True)
class TraceReference:
    offset: int
    size: int
    sha256: str


def process_memory_snapshot(status_path=None):
    """Read Linux current/peak RSS without changing host settings or cache state."""
    values = {"rss_bytes": None, "peak_rss_bytes": None}
    try:
        lines = Path(status_path or "/proc/self/status").read_text().splitlines()
    except OSError:
        lines = []
    for line in lines:
        fields = line.split()
        if (
            len(fields) != 3
            or fields[0] not in {"VmRSS:", "VmHWM:"}
            or fields[2] != "kB"
        ):
            continue
        try:
            size = int(fields[1]) * 1024
        except ValueError:
            continue
        if size >= 0:
            values["rss_bytes" if fields[0] == "VmRSS:" else "peak_rss_bytes"] = size
    return {
        **values,
        "pid": os.getpid(),
        "sampled_monotonic_ns": monotonic_ns(),
        "source": "linux-proc-status",
        "scope": "whole current process; not per sample or owner",
    }


class TraceSpool:
    """Share one append handle across an owner's concurrently produced records."""

    def __init__(self, data_root, run_id, *, max_record_bytes, max_total_bytes):
        if (
            any(
                type(n) is not int or n <= 0
                for n in (max_record_bytes, max_total_bytes)
            )
            or max_record_bytes > max_total_bytes
        ):
            raise TraceSpoolError(
                "trace spool requires positive record/total byte bounds"
            )
        if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
            raise TraceSpoolError("trace spool requires an exact run identity")
        root = Path(data_root).resolve()
        repo = Path(REPO_ROOT).resolve()
        if root == repo or repo in root.parents:
            raise TraceSpoolError("trace spool cannot write inside the repository")
        self.run_id = run_id
        self.max_record_bytes = max_record_bytes
        self.max_total_bytes = max_total_bytes
        self.path = root / "trace-intermediates" / run_id / (uuid4().hex + ".jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = self.path.open("xb")
        self._lock = threading.Lock()
        self._closed = False
        self._failed = False
        self._bytes = self._written = self._read = self._read_bytes = 0
        self._peak_record = self._peak_read = self._write_ns = self._read_ns = 0

    def append(self, serialized):
        raw = serialized.encode("utf-8") + b"\n"
        if len(raw) > self.max_record_bytes:
            raise TraceSpoolError(
                "trace spool record exceeds its registered byte bound"
            )
        started = monotonic_ns()
        with self._lock:
            if self._closed or self._failed:
                raise TraceSpoolError("trace spool writer is closed or failed")
            if self._bytes + len(raw) > self.max_total_bytes:
                raise TraceSpoolError(
                    "trace spool total exceeds its registered byte bound"
                )
            reference = TraceReference(
                self._bytes, len(raw), hashlib.sha256(raw).hexdigest()
            )
            try:
                self._handle.write(raw)
                self._handle.flush()
            except OSError as error:
                self._failed = True
                raise TraceSpoolError(
                    "trace spool write failed; preserve original bytes"
                ) from error
            self._bytes += len(raw)
            self._written += 1
            self._peak_record = max(self._peak_record, len(raw))
            self._write_ns += monotonic_ns() - started
            return reference

    def iter_records(self, references):
        # Keep one reader open per iteration, never one open per record.
        try:
            with self.path.open("rb") as reader:
                for reference in references:
                    if (
                        not isinstance(reference, TraceReference)
                        or reference.offset < 0
                        or not 0 < reference.size <= self.max_record_bytes
                    ):
                        raise TraceSpoolError("trace spool reference integrity failed")
                    started = monotonic_ns()
                    reader.seek(reference.offset)
                    raw = reader.read(reference.size)
                    if (
                        len(raw) != reference.size
                        or hashlib.sha256(raw).hexdigest() != reference.sha256
                    ):
                        raise TraceSpoolError("trace spool record integrity failed")
                    value = json.loads(raw)
                    with self._lock:
                        self._read += 1
                        self._read_bytes += len(raw)
                        self._peak_read = max(self._peak_read, len(raw))
                        self._read_ns += monotonic_ns() - started
                    yield value["channel"], value["record_id"], value["payload"]
        except OSError as error:
            raise TraceSpoolError("trace spool evidence is unavailable") from error

    def receipt(self):
        with self._lock:
            return {
                "schema": "saea-trace-spool-receipt-v1",
                "run_id": self.run_id,
                "path": str(self.path),
                "max_record_bytes": self.max_record_bytes,
                "max_total_bytes": self.max_total_bytes,
                "stored_bytes": self._bytes,
                "written_records": self._written,
                "read_records": self._read,
                "read_bytes": self._read_bytes,
                "peak_record_bytes": self._peak_record,
                "peak_read_record_bytes": self._peak_read,
                "retained_payload_bytes": 0,
                "write_wall_ns": self._write_ns,
                "read_wall_ns": self._read_ns,
                "closed": self._closed,
                "failed": self._failed,
                "process_memory": process_memory_snapshot(),
                "memory_scope": "spooled payload copies only; references, live workflow state, serialization, reads and process RSS excluded",
            }

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._handle.close()
            self._closed = True
        with self.path.with_suffix(".json").open("x", encoding="utf-8") as handle:
            json.dump(self.receipt(), handle, sort_keys=True, indent=2)
            handle.write("\n")
