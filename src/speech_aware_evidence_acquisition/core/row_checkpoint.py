"""Durable row-by-row checkpoints of a flight (owner decision 309, 2026-10-14).

Why this exists. Until this module, a flight made nothing durable until its
seal: every row's trace records sat in memory buffers
(``rails.runner._run_agent_openjiuwen`` -> ``outcome.trace_buffer``) and were
flushed into the client's ``TraceSink`` only after the whole program settled
(``rails.runner.run_speech_native_agent_loop``, the final ``flush_into`` loop;
``core.flight.runtime._dispatch_phase_program``, the ``finally`` flush), and the
canonical outputs rows are rendered only at ``seal()``. The 2026-10-14 NX-T R1
column ran 3 hours (1,204 contacts, about 120 rows) and died in a host restart
with nothing on disk but the session-attach receipt.

What this is. After each row's episode completes (all its contacts, every arm
of a multi-arm row included), the runtime appends ONE record to
``<attempt dir>/<run_id>.rows.ckpt.jsonl`` and ``fsync``s it. A record carries:

* the row's canonical outputs record(s), rendered by the SAME
  ``FlightRuntime._canonical_output_rows`` stage the seal uses, so the seal can
  hold them against the sealed bytes;
* the row's trace records as the exact serialized trace lines, so the file is
  the row's trace custody (``trace_sha256`` is the hash of those lines joined as
  a trace file would join them);
* the row's contact count, audio seconds and cost, and a per-record sha256
  chain (``prev_sha`` -> ``sha``) so any edit, reorder or deletion is detected.

A crash can tear only the LAST line (one ``write`` + ``fsync`` per record); the
reader drops an un-terminated tail and refuses any complete line that does not
chain. The whole-file sha256 is what a resume pins and what the seal records
in the run manifest.

This module is light: stdlib plus ``contracts.TraceRecord``. It imports nothing
from ``core.flight`` or ``core.bundle`` at module level, so bundle verification
and the resume reader can both use it.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

ROW_CHECKPOINT_SCHEMA = "saea-row-checkpoint-v1"
ROW_CHECKPOINT_MANIFEST_SCHEMA = "saea-row-checkpoint-manifest-block-v1"
ROW_CHECKPOINT_SUFFIX = ".rows.ckpt.jsonl"
GENESIS_SHA256 = "0" * 64

_HEX = frozenset("0123456789abcdef")


class RowCheckpointError(RuntimeError):
    """The checkpoint cannot be written, or cannot be trusted when read."""


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in _HEX for c in value)


def checkpoint_path(attempt_dir: Path, run_id: str) -> Path:
    return Path(attempt_dir) / f"{run_id}{ROW_CHECKPOINT_SUFFIX}"


def _canonical(document: object) -> str:
    return json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_row_json(row: Mapping[str, object]) -> str:
    """The exact text the seal writes for one outputs row."""

    return json.dumps(row, ensure_ascii=False, sort_keys=True)


def serialize_trace_records(records: Iterable[tuple[str, str, Mapping[str, object]]]) -> list[str]:
    """Serialize records exactly as ``core.tracing.TraceSink.emit`` writes them."""

    from ..contracts import TraceRecord  # noqa: PLC0415 (keeps the import graph light)

    return [
        TraceRecord(channel=channel, record_id=record_id, payload=payload).serialize()
        for channel, record_id, payload in records
    ]


def trace_text(lines: Sequence[str]) -> str:
    """The bytes a trace file holds for these serialized lines."""

    return "".join(line + "\n" for line in lines)


def summarize_trace_lines(lines: Sequence[str]) -> dict[str, object]:
    """One row's own spend, counted exactly as ``core.flight.resume._scan_trace``
    counts a predecessor trace (requests, COST fields, native tool calls)."""

    from .flight.resume import _native_tool_calls  # noqa: PLC0415 (cycle guard)

    totals: dict[str, object] = {
        "calls": 0, "audio_seconds": 0.0, "latency_seconds": 0.0,
        "prompt_tokens": 0, "completion_tokens": 0, "tool_calls": 0,
    }
    for line in lines:
        record = json.loads(line)
        channel, record_id, payload = record["channel"], record["record_id"], record["payload"]
        if channel == "MODEL_REQUEST" and record_id.endswith("/request"):
            totals["calls"] += 1
        elif channel == "MODEL_WIRE_RESPONSE" and record_id.endswith("/wire-response"):
            totals["tool_calls"] += _native_tool_calls(payload) or 0
        elif channel == "COST" and record_id.endswith("/cost"):
            for key, field in (
                ("latency_seconds", "latency_seconds"), ("audio_seconds", "audio_seconds"),
            ):
                value = payload.get(field)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    totals[key] += float(value)
            for key in ("prompt_tokens", "completion_tokens"):
                value = payload.get(key)
                if isinstance(value, int) and not isinstance(value, bool):
                    totals[key] += value
    return totals


def arm_group_defect(output_row: Mapping[str, object]) -> str | None:
    """Why a multi-arm row's receipts are NOT a complete arm group, or ``None``.

    A column row (supply / template / thinking variants, Perception branches)
    is kept by a resume only when ALL its arms are present. The canonical stage
    already validated the receipt against the DECLARED arm list when the row was
    checkpointed (``validate_supply_variant_receipt`` and its twins); this is the
    reader-side re-check that the receipt is self-consistent -- the declared
    ``arm_count`` equals the arm rows present, indices run 0..n-1, and exactly
    one arm is the delivering (last) one -- so a truncated or edited row is
    re-flown whole instead of kept.
    """

    variants = output_row.get("supply_variants")
    if variants is not None:
        problem = _arm_rows_defect(variants, rows_key="arms", index_key="arm_index",
                                   id_key="arm_id", count_key="arm_count",
                                   delivered_key="delivered_arm_id")
        if problem:
            return f"supply_variants: {problem}"
    receipt = output_row.get("native_episode_receipt")
    if isinstance(receipt, Mapping):
        branches = receipt.get("perception_branches")
        if branches is not None:
            problem = _arm_rows_defect(branches, rows_key="branches", index_key="branch_index",
                                       id_key="branch_id", count_key=None,
                                       delivered_key=None)
            if problem:
                return f"perception_branches: {problem}"
    return None


def _arm_rows_defect(block, *, rows_key, index_key, id_key, count_key, delivered_key):
    if not isinstance(block, Mapping):
        return "the receipt is not a mapping"
    rows = block.get(rows_key)
    if not isinstance(rows, list) or not rows:
        return f"no {rows_key} are recorded"
    if count_key is not None and block.get(count_key) != len(rows):
        return f"{count_key} {block.get(count_key)!r} differs from the {len(rows)} {rows_key} present"
    indices = [row.get(index_key) if isinstance(row, Mapping) else None for row in rows]
    if indices != list(range(len(rows))):
        return f"{index_key} values {indices!r} are not 0..{len(rows) - 1}"
    ids = [row.get(id_key) for row in rows]
    if any(not isinstance(value, str) or not value for value in ids) or len(set(ids)) != len(ids):
        return f"{id_key} values are missing or repeated"
    if delivered_key is not None and block.get(delivered_key) != ids[-1]:
        return "the delivering arm is not the last arm present"
    return None


@dataclass(frozen=True)
class CheckpointRow:
    seq: int
    sample_id: str
    complete: bool
    reason: str | None
    output_rows: tuple[Mapping[str, object], ...]
    trace_lines: tuple[str, ...]
    trace_sha256: str
    contacts: int
    audio_seconds: float
    cost: Mapping[str, object]

    @property
    def keepable(self) -> bool:
        """COMPLETE and, for a column row, carrying every arm."""

        return (
            self.complete
            and bool(self.output_rows)
            and all(arm_group_defect(row) is None for row in self.output_rows)
        )

    def keep_defect(self) -> str | None:
        if not self.complete:
            return self.reason or "the row was recorded as not rendered"
        if not self.output_rows:
            return "the row carries no canonical output record"
        for row in self.output_rows:
            problem = arm_group_defect(row)
            if problem:
                return f"incomplete arm group ({problem})"
        return None


@dataclass(frozen=True)
class CheckpointDocument:
    path: Path
    sha256: str
    header: Mapping[str, object]
    rows: tuple[CheckpointRow, ...]
    last_sha: str
    torn_tail_bytes: int = 0

    @property
    def complete_rows(self) -> int:
        return sum(1 for row in self.rows if row.complete)

    @property
    def unrendered_rows(self) -> int:
        return sum(1 for row in self.rows if not row.complete)

    def by_sample(self) -> dict[str, CheckpointRow]:
        return {row.sample_id: row for row in self.rows}

    def manifest_block(self) -> dict[str, object]:
        return {
            "schema": ROW_CHECKPOINT_MANIFEST_SCHEMA,
            "path": str(self.path),
            "sha256": self.sha256,
            "row_count": len(self.rows),
            "complete_rows": self.complete_rows,
            "unrendered_rows": self.unrendered_rows,
            "last_sha": self.last_sha,
        }


class RowCheckpointWriter:
    """Append-only, fsynced, hash-chained writer (one per attempt)."""

    def __init__(
        self,
        attempt_dir: Path,
        run_id: str,
        attempt_id: str,
        *,
        identity: Mapping[str, object],
        fsync: bool = True,
    ) -> None:
        self._path = checkpoint_path(attempt_dir, run_id)
        self._run_id = run_id
        self._attempt_id = attempt_id
        self._fsync = bool(fsync)
        self._lock = threading.Lock()
        self._seq = 0
        self._last_sha = GENESIS_SHA256
        self._sample_ids: set[str] = set()
        self._closed = False
        Path(attempt_dir).mkdir(parents=True, exist_ok=True)
        try:
            self._handle = self._path.open("xb")
        except FileExistsError as error:
            raise RowCheckpointError(
                f"row checkpoint {self._path} already exists; a re-run must use a fresh "
                "attempt directory, never append to a prior attempt's checkpoint"
            ) from error
        self._append({
            "schema": ROW_CHECKPOINT_SCHEMA, "kind": "header", "run_id": run_id,
            "attempt_id": attempt_id, **{k: v for k, v in identity.items()},
        })
        self._sync_directory(Path(attempt_dir))

    @property
    def path(self) -> Path:
        return self._path

    @property
    def row_count(self) -> int:
        return self._seq - 1

    @staticmethod
    def _sync_directory(directory: Path) -> None:
        if os.name != "posix":
            return
        try:  # make the new file's directory entry durable too
            fd = os.open(directory, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError:
            pass

    def _append(self, body: dict[str, object]) -> str:
        """Write one chained record; the caller holds the lock (or is __init__)."""

        record = {**body, "seq": self._seq, "prev_sha": self._last_sha}
        digest = _sha256_text(_canonical(record))
        line = _canonical({**record, "sha": digest}) + "\n"
        try:
            self._handle.write(line.encode("utf-8"))
            self._handle.flush()
            if self._fsync:
                os.fsync(self._handle.fileno())
        except OSError as error:
            raise RowCheckpointError(f"row checkpoint write failed: {error}") from error
        self._seq += 1
        self._last_sha = digest
        return digest

    def append_row(
        self,
        *,
        sample_id: str,
        complete: bool,
        output_rows: Sequence[Mapping[str, object]],
        trace_lines: Sequence[str],
        reason: str | None = None,
    ) -> str:
        """Append one row. ``output_rows`` are the row's canonical records
        (empty when ``complete`` is false); ``trace_lines`` its serialized trace."""

        if not isinstance(sample_id, str) or not sample_id:
            raise RowCheckpointError("a checkpoint row needs a sample id")
        cost = summarize_trace_lines(trace_lines)
        body = {
            "kind": "row", "sample_id": sample_id, "complete": bool(complete),
            "reason": reason, "output_rows": [dict(row) for row in output_rows],
            "trace": list(trace_lines), "trace_sha256": _sha256_text(trace_text(trace_lines)),
            "contacts": int(cost["calls"]), "audio_seconds": float(cost["audio_seconds"]),
            "cost": cost,
        }
        with self._lock:
            if self._closed:
                raise RowCheckpointError("row checkpoint is closed")
            if sample_id in self._sample_ids:
                raise RowCheckpointError(
                    f"sample {sample_id!r} is checkpointed twice; a row settles once"
                )
            digest = self._append(body)
            self._sample_ids.add(sample_id)
        return digest

    def close(self) -> Path:
        with self._lock:
            if not self._closed:
                self._closed = True
                try:
                    self._handle.flush()
                    if self._fsync:
                        os.fsync(self._handle.fileno())
                finally:
                    self._handle.close()
        return self._path


def read_checkpoint(path: Path, *, expected_sha256: str | None = None) -> CheckpointDocument:
    """Read and verify a checkpoint. Refuses by name; never writes.

    * ``expected_sha256`` pins the WHOLE file (including any torn tail);
    * every newline-terminated line must parse, carry the next ``seq``, chain
      to the previous ``sha`` and re-hash to its own ``sha``;
    * bytes after the last newline are a torn tail (a crash mid-record) and are
      dropped, never trusted;
    * a sample may appear on at most one row.
    """

    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise RowCheckpointError(f"cannot read row checkpoint {path}: {error}") from error
    digest = hashlib.sha256(raw).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise RowCheckpointError(
            f"row checkpoint {path} hashes to {digest}, not the declared {expected_sha256}; "
            "a resume applies only when the checkpoint's bytes are exactly what was declared"
        )
    end = raw.rfind(b"\n") + 1
    torn = len(raw) - end
    body_lines = raw[:end].split(b"\n")[:-1] if end else []
    header: Mapping[str, object] | None = None
    rows: list[CheckpointRow] = []
    seen: set[str] = set()
    previous = GENESIS_SHA256
    for number, encoded in enumerate(body_lines, start=1):
        try:
            record = json.loads(encoded.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as error:
            raise RowCheckpointError(
                f"row checkpoint {path} line {number} is malformed ({error}); the chain is broken"
            ) from error
        if not isinstance(record, dict) or not is_sha256(record.get("sha")):
            raise RowCheckpointError(f"row checkpoint {path} line {number} carries no sha256")
        claimed = record.pop("sha")
        if record.get("seq") != number - 1:
            raise RowCheckpointError(
                f"row checkpoint {path} line {number} has seq {record.get('seq')!r}, "
                f"expected {number - 1}; a record was removed or reordered"
            )
        if record.get("prev_sha") != previous:
            raise RowCheckpointError(
                f"row checkpoint {path} line {number} does not chain to the previous record"
            )
        if _sha256_text(_canonical(record)) != claimed:
            raise RowCheckpointError(
                f"row checkpoint {path} line {number} was edited after it was written "
                "(its sha256 does not re-derive)"
            )
        previous = claimed
        if number == 1:
            if record.get("kind") != "header" or record.get("schema") != ROW_CHECKPOINT_SCHEMA:
                raise RowCheckpointError(
                    f"row checkpoint {path} does not open with a {ROW_CHECKPOINT_SCHEMA} header"
                )
            header = record
            continue
        if record.get("kind") != "row":
            raise RowCheckpointError(f"row checkpoint {path} line {number} is not a row record")
        sample_id = record.get("sample_id")
        lines = record.get("trace")
        if (
            not isinstance(sample_id, str) or not sample_id
            or not isinstance(lines, list) or any(not isinstance(item, str) for item in lines)
            or not isinstance(record.get("output_rows"), list)
        ):
            raise RowCheckpointError(f"row checkpoint {path} line {number} is malformed")
        if record.get("trace_sha256") != _sha256_text(trace_text(lines)):
            raise RowCheckpointError(
                f"row checkpoint {path} line {number}: trace_sha256 does not match its trace lines"
            )
        if sample_id in seen:
            raise RowCheckpointError(
                f"row checkpoint {path} records sample {sample_id!r} twice"
            )
        seen.add(sample_id)
        rows.append(CheckpointRow(
            seq=record["seq"], sample_id=sample_id, complete=bool(record.get("complete")),
            reason=record.get("reason"), output_rows=tuple(record["output_rows"]),
            trace_lines=tuple(lines), trace_sha256=record["trace_sha256"],
            contacts=int(record.get("contacts", 0)),
            audio_seconds=float(record.get("audio_seconds", 0.0)),
            cost=dict(record.get("cost") or {}),
        ))
    if header is None:
        raise RowCheckpointError(f"row checkpoint {path} has no header record")
    return CheckpointDocument(
        path=path, sha256=digest, header=header, rows=tuple(rows),
        last_sha=previous, torn_tail_bytes=torn,
    )


def kept_trace_text(rows: Sequence[CheckpointRow]) -> str:
    """The trace file a resume materializes for the rows it keeps: their
    serialized lines, in checkpoint order -- a pure function of the checkpoint."""

    return "".join(trace_text(row.trace_lines) for row in rows)


def compare_with_sealed(
    document: CheckpointDocument,
    sealed_rows: Mapping[str, Mapping[str, object]],
    flown_sample_ids: Sequence[str],
) -> dict[str, object]:
    """Hold a checkpoint against the rows a seal is about to write.

    Every flown sample needs EXACTLY ONE checkpoint row; a complete row's
    output record(s) must equal the sealed row byte for byte. Returns a report;
    ``problems`` is empty when the checkpoint is consistent with the seal.
    """

    problems: list[str] = []
    flown = [str(sample_id) for sample_id in flown_sample_ids]
    by_sample = document.by_sample()
    missing = sorted(set(flown) - set(by_sample))
    extra = sorted(set(by_sample) - set(flown))
    if missing:
        problems.append(f"{len(missing)} flown row(s) have no checkpoint record, e.g. {missing[:5]}")
    if extra:
        problems.append(f"{len(extra)} checkpoint row(s) are outside the flown roster, e.g. {extra[:5]}")
    different: list[str] = []
    for sample_id in flown:
        row = by_sample.get(sample_id)
        if row is None or not row.complete:
            continue
        sealed = sealed_rows.get(sample_id)
        if (
            sealed is None
            or len(row.output_rows) != 1
            or canonical_row_json(row.output_rows[0]) != canonical_row_json(sealed)
        ):
            different.append(sample_id)
    if different:
        problems.append(
            f"{len(different)} checkpoint row(s) differ from the sealed row, e.g. {different[:5]}"
        )
    return {
        "status": "VERIFIED" if not problems else "MISMATCH",
        "flown": len(flown),
        "checkpoint_rows": len(document.rows),
        "complete_rows": document.complete_rows,
        "unrendered_rows": document.unrendered_rows,
        "problems": problems,
    }


def verify_manifest_block(block: object, outputs_rows: Sequence[Mapping[str, object]]) -> None:
    """Re-derive a manifest's ``row_checkpoint`` block from disk (bundle verify).

    The file must hash to the declared sha256, chain end to end, agree with the
    declared counts, and every complete row's output record must equal the
    outputs row of the same sample byte for byte.
    """

    expected = {"schema", "path", "sha256", "row_count", "complete_rows", "unrendered_rows", "last_sha"}
    if not isinstance(block, Mapping) or set(block) != expected:
        raise RowCheckpointError(f"manifest row_checkpoint must carry exactly {sorted(expected)}")
    if block["schema"] != ROW_CHECKPOINT_MANIFEST_SCHEMA or not is_sha256(block["sha256"]):
        raise RowCheckpointError("manifest row_checkpoint has a wrong schema or sha256")
    document = read_checkpoint(Path(str(block["path"])), expected_sha256=str(block["sha256"]))
    if (
        len(document.rows) != block["row_count"]
        or document.complete_rows != block["complete_rows"]
        or document.unrendered_rows != block["unrendered_rows"]
        or document.last_sha != block["last_sha"]
    ):
        raise RowCheckpointError("manifest row_checkpoint counts differ from the checkpoint file")
    sealed = {str(row.get("sample_id")): row for row in outputs_rows}
    for row in document.rows:
        if not row.complete:
            continue
        match = sealed.get(row.sample_id)
        if (
            match is None
            or len(row.output_rows) != 1
            or canonical_row_json(row.output_rows[0]) != canonical_row_json(match)
        ):
            raise RowCheckpointError(
                f"checkpoint row for sample {row.sample_id!r} differs from the sealed outputs row"
            )


__all__ = [
    "GENESIS_SHA256", "ROW_CHECKPOINT_MANIFEST_SCHEMA", "ROW_CHECKPOINT_SCHEMA",
    "ROW_CHECKPOINT_SUFFIX", "CheckpointDocument", "CheckpointRow", "RowCheckpointError",
    "RowCheckpointWriter", "arm_group_defect", "canonical_row_json", "checkpoint_path",
    "compare_with_sealed", "is_sha256", "kept_trace_text", "read_checkpoint",
    "serialize_trace_records", "sha256_file", "summarize_trace_lines", "trace_text",
    "verify_manifest_block",
]
