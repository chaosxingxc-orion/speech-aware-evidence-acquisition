"""Append-only four-axis trace sink writing outside the repository (R0).

Batched execution additions (owner directive 2026-08-08): the per-run trace
file stays SINGLE and append-only, but under sample-level concurrency each
sample's records are buffered in-memory (:class:`TraceBuffer`) and flushed
into the real :class:`TraceSink` in split-id order by the driver — the
simpler of the two deterministic options (order is decided by the flush
loop, not by task completion), and within-sample record order is emission
order exactly as in sequential execution. :class:`DispatchingSink` routes
the shared adapter's emissions to the current sample task's buffer through
a contextvar (task-local under asyncio; ``asyncio.to_thread`` copies the
context, so the adapter's worker-thread emissions land correctly); with no
buffer set it falls through to the real sink, leaving every sequential
caller untouched.
"""

from __future__ import annotations

import contextvars
import copy
import threading
from pathlib import Path
from typing import Mapping

from ..contracts import RUN_ID_PATTERN as _RUN_ID_PATTERN
from ..contracts import TraceRecord
from ..e0.artifacts import REPO_ROOT, write_json_artifact

_CURRENT_TRACE_BUFFER: contextvars.ContextVar[object | None] = contextvars.ContextVar(
    "saea_current_trace_buffer", default=None
)


def set_current_trace_buffer(buffer: object | None) -> None:
    """Bind the calling task's trace emissions (module docstring). Part of
    the batch-policy contract: a ``run_samples`` implementation sets the
    sample's own buffer before any work for that sample, and the driver's
    :class:`DispatchingSink` routes accordingly."""

    _CURRENT_TRACE_BUFFER.set(buffer)


def get_current_trace_buffer() -> object | None:
    """Return the calling task's active buffer without falling through.

    Request-shaping code uses this accessor when an opt-in transformation
    must be recorded before dispatch. Returning ``None`` is deliberate: it
    lets that path fail closed instead of silently writing to another sink.
    """

    return _CURRENT_TRACE_BUFFER.get()


class TraceBuffer:
    """Buffer one sample's ordered trace, optionally on disk.
    Keep eager validation and mutation-proof emit semantics like TraceSink.
    Default storage deep-copies payloads; an explicitly supplied spool keeps
    references to serialized records. Flush once in caller order through
    the original sink, without loading all stored payloads at once."""

    def __init__(self, run_id: str, *, spool=None) -> None:
        if spool is not None and spool.run_id != run_id:
            from .trace_spool import TraceSpoolError
            raise TraceSpoolError("trace buffer and spool must share their owner")
        self._run_id = run_id
        self._spool = spool
        self._records = []

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def records(self):
        """Retain the historical inspection API; runtime uses streaming iteration."""
        return self._records if self._spool is None else list(self.iter_records())

    @property
    def resident_payload_bytes(self):
        """Report retained serialized payload bytes, not Python objects or RSS."""
        if self._spool is not None:
            return 0
        return sum(len(TraceRecord(*record).serialize().encode("utf-8"))
                   for record in self._records)

    def iter_records(self):
        if self._spool is None:
            yield from self._records
        elif self._records:
            yield from self._spool.iter_records(self._records)

    def emit(self, channel: str, record_id: str, payload: Mapping[str, object]) -> str:
        record = TraceRecord(channel=channel, record_id=record_id, payload=payload)
        serialized = record.serialize()  # Preserve eager boundary validation.
        if self._spool is None:
            self._records.append((channel, record_id, copy.deepcopy(payload)))
        else:
            self._records.append(self._spool.append(serialized))
        return record.content_hash()

    def flush_into(self, sink: "TraceSink") -> None:
        for channel, record_id, payload in self.iter_records():
            sink.emit(channel, record_id, payload)
        self._records = []  # One-shot: leave the intermediate evidence on disk.

    def close_storage(self) -> None:
        """Close shared intermediate writing only after all owner traces flush."""
        if self._spool is not None:
            self._spool.close()

    def extend_from(self, child: "TraceBuffer") -> None:
        """Merge one completed contact in caller order without loading shared spools."""
        if child is self or child.run_id != self.run_id:
            raise ValueError("trace child must be distinct and share the parent run_id")
        if self._spool is child._spool:
            self._records.extend(child._records)
        else:
            for record in child.iter_records():
                self.emit(*record)
        child._records = []


class DispatchingSink:
    """The adapter-facing sink under batching: routes to the current task's
    buffer (contextvar) or falls through to the real per-run sink."""

    def __init__(self, sink: "TraceSink") -> None:
        self._sink = sink

    @property
    def run_id(self) -> str:
        return self._sink.run_id

    def emit(self, channel: str, record_id: str, payload: Mapping[str, object]) -> str:
        target = _CURRENT_TRACE_BUFFER.get()
        if target is None:
            target = self._sink
        return target.emit(channel, record_id, payload)


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
        # One append handle for the life of the sink, opened lazily on the
        # first record (the trace file must not exist before the first
        # record: constructing a second sink on the directory is refused
        # because the file exists, and "no file" equals "no records" for
        # every reader). Until 2026-09-26 ``emit`` opened, appended and
        # closed the file per record; on the drvfs/9p run root that round
        # trip cost 7.06 ms per record (355.6 s over ROLL-2's 50,380
        # records against 8.8 s in one open --
        # docs/results/2026-09-26-slurp-seal-path-profile.md, section 3).
        self._handle = None
        self._lock = threading.Lock()

    @property
    def run_id(self) -> str:
        return self._run_id

    def emit(self, channel: str, record_id: str, payload: Mapping[str, object]) -> str:
        """Append one validated record and return its content hash.

        Durability contract (unchanged from the per-record open/close form):
        when ``emit`` returns, the record is a whole ``\\n``-terminated line
        handed to the kernel -- ``flush()`` after every record pushes the
        text and buffered layers down with ``write(2)``, exactly what the old
        ``close()`` per record did, and no ``fsync`` is issued in either form
        (the seal's four whole-file fsyncs are elsewhere). A process killed at
        any instant therefore leaves a trace that is complete up to the last
        ``emit`` that returned, with no torn line from a Python buffer, which
        is the granularity both recovery readers rely on:
        ``core.flight.resume._scan_trace`` refuses the whole predecessor
        attempt on a single malformed line, and
        ``core.driver.speech_native.read_attempt_trace_facts`` counts an
        interrupted attempt's contacts from the same file. The write and the
        bookkeeping are serialised on a lock so two emitters can never
        interleave bytes inside one line.
        """

        if self._closed:
            raise TraceSinkError("sink is closed")
        if record_id in self._hashes:
            raise TraceSinkError(f"duplicate trace record id {record_id!r}")
        record = TraceRecord(channel=channel, record_id=record_id, payload=payload)
        line = record.serialize()
        digest = record.content_hash()
        with self._lock:
            if self._closed:
                raise TraceSinkError("sink is closed")
            if record_id in self._hashes:
                raise TraceSinkError(f"duplicate trace record id {record_id!r}")
            handle = self._handle
            if handle is None:
                handle = self._path.open("a", encoding="utf-8", newline="\n")
                self._handle = handle
            handle.write(line + "\n")
            handle.flush()
            self._hashes[record_id] = digest
        return digest

    def manifest(self) -> dict[str, str]:
        return dict(self._hashes)

    def close(self) -> str:
        with self._lock:
            self._closed = True
            handle = self._handle
            self._handle = None
        if handle is not None:
            handle.close()
        return write_json_artifact(
            self._run_dir / f"{self._run_id}.trace-manifest.json",
            {"run_id": self._run_id, "records": self.manifest()},
        )
