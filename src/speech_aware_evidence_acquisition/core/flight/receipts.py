"""``FlightReceipts``: the hash-bound, append-only stage ledger every
``core.flight.runtime.FlightRuntime`` stage writes into.

C4c consolidation: one flight runtime is the harness every arm and carrier
runs through (``preflight`` -> ``preprocess`` -> ``serve`` -> ``run_phases``
-> ``seal`` -> ``score``). Each stage produces exactly one JSON-serializable
payload; this module is the shared, minimal record that binds those payloads
together under one run/attempt identity, refuses to record the same stage
twice (a stage's own re-run discipline lives in ``runtime.py``; this module
only refuses silent overwrite of an already-recorded receipt), exposes a
single canonical ``as_json()``, and persists exact monotonically growing
snapshots for shared campaigns and generation-only workers.

Standard-library only, no dependency on ``core.model``/``rails`` -- like
``core.attempts``/``core.session``, this is a small, self-contained seam.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

#: The six stages a :class:`FlightRuntime` walks through, in the only order
#: ``runtime.py`` ever accepts them (module docstring). ``score`` is last and
#: optional -- a caller may stop at ``seal`` and never call ``score`` at all
#: (e.g. a ``--dry-run`` flight, or a flight whose scoring is deferred to a
#: separately-registered read mission) -- but every stage that DOES run must
#: run in exactly this relative order.
FLIGHT_STAGES: tuple[str, ...] = (
    "preflight",
    "preprocess",
    "serve",
    "run_phases",
    "seal",
    "score",
)

FLIGHT_RECEIPTS_SCHEMA = "saea-flight-receipts-v1"


class FlightReceiptError(RuntimeError):
    """A stage payload is malformed, out of order, or would overwrite an
    already-recorded stage."""


def _canonical_hash(document: Mapping[str, object]) -> str:
    blob = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def _validate_document(document: object) -> dict[str, object]:
    if not isinstance(document, dict) or set(document) != {
        "schema", "run_id", "attempt_id", "stages", "receipts_hash",
    }:
        raise FlightReceiptError("flight receipts must be an exact schema object")
    if document.get("schema") != FLIGHT_RECEIPTS_SCHEMA:
        raise FlightReceiptError(
            f"flight receipts schema must be {FLIGHT_RECEIPTS_SCHEMA!r}"
        )
    for field_name in ("run_id", "attempt_id"):
        if not isinstance(document.get(field_name), str) or not document[field_name]:
            raise FlightReceiptError(f"flight receipts {field_name} must be nonempty")
    stages = document.get("stages")
    if not isinstance(stages, dict):
        raise FlightReceiptError("flight receipts stages must be an object")
    unknown = set(stages) - set(FLIGHT_STAGES)
    if unknown:
        raise FlightReceiptError(f"flight receipts contain unknown stages: {sorted(unknown)}")
    completed = tuple(stage for stage in FLIGHT_STAGES if stage in stages)
    if completed != FLIGHT_STAGES[: len(completed)]:
        raise FlightReceiptError("flight receipt stages must form the canonical stage prefix")
    for stage in completed:
        payload = stages[stage]
        if not isinstance(payload, dict):
            raise FlightReceiptError(f"flight stage {stage!r} receipt must be an object")
        if payload.get("stage") != stage or not isinstance(payload.get("stage_hash"), str):
            raise FlightReceiptError(f"flight stage {stage!r} identity is malformed")
        hashed = dict(payload)
        recorded_hash = hashed.pop("stage_hash")
        if _canonical_hash(hashed) != recorded_hash:
            raise FlightReceiptError(f"flight stage {stage!r} stage hash mismatch")
    hashed_document = dict(document)
    recorded_receipts_hash = hashed_document.pop("receipts_hash")
    if not isinstance(recorded_receipts_hash, str) or (
        _canonical_hash(hashed_document) != recorded_receipts_hash
    ):
        raise FlightReceiptError("flight receipts hash mismatch")
    return document


def read_flight_receipts(path: Path) -> dict[str, object]:
    """Load and validate one exact :meth:`FlightReceipts.as_json` snapshot."""

    path = Path(path)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise FlightReceiptError(f"cannot read flight receipts {path}: {error}") from error
    return _validate_document(document)


def write_flight_receipts(path: Path, receipts: "FlightReceipts") -> str:
    """Atomically persist an exact, monotonically growing receipt ledger.

    An existing snapshot may be repeated or extended with later stages. Its
    identity and every prior stage must remain identical as JSON values;
    rollback and mutation are refused before the atomic replacement.
    """

    if not isinstance(receipts, FlightReceipts):
        raise FlightReceiptError("write_flight_receipts requires FlightReceipts")
    try:
        document = json.loads(
            json.dumps(receipts.as_json(), ensure_ascii=False, sort_keys=True)
        )
    except (TypeError, ValueError) as error:
        raise FlightReceiptError(f"flight receipts are not JSON serializable: {error}") from error
    document = _validate_document(document)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f".{path.name}.lock")
    temporary = path.with_name(
        f".{path.name}.tmp-{os.getpid()}-{time.monotonic_ns()}"
    )
    try:
        with lock_path.open("a+", encoding="utf-8") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            if path.is_file():
                existing = read_flight_receipts(path)
                if (
                    existing["run_id"], existing["attempt_id"]
                ) != (document["run_id"], document["attempt_id"]):
                    raise FlightReceiptError(
                        "persisted flight receipt identity differs from the live ledger"
                    )
                old_stages = tuple(
                    stage for stage in FLIGHT_STAGES if stage in existing["stages"]
                )
                new_stages = tuple(
                    stage for stage in FLIGHT_STAGES if stage in document["stages"]
                )
                if len(new_stages) < len(old_stages):
                    raise FlightReceiptError("refusing flight receipt stage rollback")
                if new_stages[: len(old_stages)] != old_stages:
                    raise FlightReceiptError("flight receipt stages are not an exact prior prefix")
                for stage in old_stages:
                    if existing["stages"][stage] != document["stages"][stage]:
                        raise FlightReceiptError(
                            f"refusing to change recorded stage {stage!r}"
                        )
                if existing == document:
                    return _file_hash(path)
            raw = json.dumps(
                document, ensure_ascii=False, sort_keys=True, indent=2,
            ).encode("utf-8") + b"\n"
            with temporary.open("xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            return _file_hash(path)
    except FlightReceiptError:
        raise
    except OSError as error:
        raise FlightReceiptError(f"cannot persist flight receipts {path}: {error}") from error
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass


def persist_flight_receipts(
    data_root: Path,
    *,
    run_id: str,
    attempt_id: str,
    receipts: "FlightReceipts",
) -> dict[str, str] | None:
    """Persist genuine stages under the governed live run and attempt identity."""

    if not isinstance(receipts, FlightReceipts):
        raise FlightReceiptError("persist_flight_receipts requires FlightReceipts")
    if not receipts.completed_stages():
        return None
    if (receipts.run_id, receipts.attempt_id) != (run_id, attempt_id):
        raise FlightReceiptError(
            "live flight identity differs from its receipt ledger"
        )
    runs_root = (Path(data_root).resolve() / "runs").resolve()
    receipt_path = (
        runs_root / run_id / attempt_id / "flight-receipts.json"
    ).resolve()
    if len(receipt_path.parents) < 3 or receipt_path.parents[2] != runs_root:
        raise FlightReceiptError(
            "flight receipt path escapes the governed runs directory"
        )
    receipt_sha256 = write_flight_receipts(receipt_path, receipts)
    return {"path": str(receipt_path), "sha256": receipt_sha256}


@dataclass
class FlightReceipts:
    """One flight's stage ledger: ``run_id``/``attempt_id`` identity plus an
    insertion-ordered ``stage -> receipt`` mapping.

    :meth:`record` is the only way a stage payload enters this ledger. It
    stamps ``stage`` and a ``stage_hash`` (the canonical SHA-256 of every
    OTHER field in the payload, so a receipt is self-describing without being
    self-referential) onto a COPY of the given mapping, then refuses ever to
    replace an already-recorded stage -- ``runtime.py``'s own "refuses to run
    out of order" discipline for stage METHODS is a different, complementary
    check; this is the ledger's own, narrower "never silently overwrite a
    sealed stage receipt" invariant, useful even to a caller that bypasses
    ``FlightRuntime`` and drives this ledger directly (e.g. a test).
    """

    run_id: str
    attempt_id: str
    stages: dict[str, Mapping[str, object]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise FlightReceiptError("FlightReceipts.run_id must be a non-empty string")
        if not isinstance(self.attempt_id, str) or not self.attempt_id:
            raise FlightReceiptError("FlightReceipts.attempt_id must be a non-empty string")

    def record(self, stage: str, payload: Mapping[str, object]) -> Mapping[str, object]:
        if stage not in FLIGHT_STAGES:
            raise FlightReceiptError(
                f"unknown flight stage {stage!r}; known stages are {FLIGHT_STAGES}"
            )
        if stage in self.stages:
            raise FlightReceiptError(
                f"flight stage {stage!r} is already recorded for run {self.run_id!r} "
                f"attempt {self.attempt_id!r}; refusing to overwrite a sealed receipt"
            )
        if not isinstance(payload, Mapping):
            raise FlightReceiptError(f"stage {stage!r} payload must be a mapping")
        if "stage" in payload or "stage_hash" in payload:
            raise FlightReceiptError(
                f"stage {stage!r} payload must not itself carry 'stage' or 'stage_hash' "
                "(both are stamped by this ledger)"
            )
        document = dict(payload)
        document["stage"] = stage
        document["stage_hash"] = _canonical_hash(document)
        self.stages[stage] = document
        return document

    def has(self, stage: str) -> bool:
        return stage in self.stages

    def require(self, stage: str) -> Mapping[str, object]:
        """The recorded receipt for ``stage``, or a fail-closed
        :class:`FlightReceiptError` naming exactly what is missing -- the
        primitive every later stage uses to read an earlier stage's own
        receipt (e.g. ``seal()`` reading ``run_phases()``'s contact count)."""

        try:
            return self.stages[stage]
        except KeyError:
            raise FlightReceiptError(
                f"flight stage {stage!r} has not been recorded yet for run "
                f"{self.run_id!r} attempt {self.attempt_id!r}"
            ) from None

    def completed_stages(self) -> tuple[str, ...]:
        return tuple(stage for stage in FLIGHT_STAGES if stage in self.stages)

    def as_json(self) -> dict[str, object]:
        ordered = {stage: self.stages[stage] for stage in FLIGHT_STAGES if stage in self.stages}
        document: dict[str, object] = {
            "schema": FLIGHT_RECEIPTS_SCHEMA,
            "run_id": self.run_id,
            "attempt_id": self.attempt_id,
            "stages": ordered,
        }
        document["receipts_hash"] = _canonical_hash(document)
        return document


def require_mandatory_throughput_fields(
    stage: str, payload: Mapping[str, object], fields: Sequence[str]
) -> None:
    """Fail closed (:class:`FlightReceiptError`) unless every name in
    ``fields`` is present in ``payload`` and is a finite, non-negative
    number. Owner rule (study ``CLAUDE.md``, "Engineering base and
    experiment rules"): throughput lines are mandatory in every receipt, not
    an optional diagnostic a stage may forget to fill in -- this is the one
    place that rule is actually enforced, called from every
    ``FlightRuntime`` stage that produces a throughput number before that
    stage's payload ever reaches :meth:`FlightReceipts.record`.
    """

    import math

    for name in fields:
        if name not in payload:
            raise FlightReceiptError(
                f"{stage} receipt is missing mandatory throughput field {name!r}"
            )
        value = payload[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FlightReceiptError(
                f"{stage} receipt throughput field {name!r} must be a number, got {value!r}"
            )
        if not math.isfinite(value) or value < 0:
            raise FlightReceiptError(
                f"{stage} receipt throughput field {name!r} must be finite and "
                f"non-negative, got {value!r}"
            )


__all__ = [
    "FLIGHT_RECEIPTS_SCHEMA",
    "FLIGHT_STAGES",
    "FlightReceiptError",
    "FlightReceipts",
    "persist_flight_receipts",
    "read_flight_receipts",
    "require_mandatory_throughput_fields",
    "write_flight_receipts",
]
