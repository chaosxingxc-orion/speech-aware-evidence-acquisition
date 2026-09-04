"""``FlightReceipts``: the hash-bound, append-only stage ledger every
``core.flight.runtime.FlightRuntime`` stage writes into.

C4c consolidation: one flight runtime is the harness every arm and carrier
runs through (``preflight`` -> ``preprocess`` -> ``serve`` -> ``run_phases``
-> ``seal`` -> ``score``). Each stage produces exactly one JSON-serializable
payload; this module is the shared, minimal record that binds those payloads
together under one run/attempt identity, refuses to record the same stage
twice (a stage's own re-run discipline lives in ``runtime.py``; this module
only refuses silent overwrite of an already-recorded receipt), and exposes a
single canonical ``as_json()`` for whatever writes ``preflight.json``/
``flight-receipt.json`` to disk.

Standard-library only, no dependency on ``core.model``/``rails`` -- like
``core.attempts``/``core.session``, this is a small, self-contained seam.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
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
    "require_mandatory_throughput_fields",
]
