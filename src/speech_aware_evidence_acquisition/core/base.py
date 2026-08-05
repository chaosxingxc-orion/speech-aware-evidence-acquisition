"""Foundation seams: ONE registry mechanism + shared value types (R0).

Anti-fragmentation contract (owner direction 2026-08-05): every pluggable
dimension of a Stage-2 experiment — carrier, evidence source, transport,
policy, scorer — registers here through the same Registry class, and every
run flows through core.driver.run_experiment(). A new experiment is config
plus at most one newly registered component, never new wiring.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from ..contracts import assert_information_boundary


class CoreError(RuntimeError):
    """A foundation seam refuses: unknown/duplicate registration or wiring misuse."""


class Registry:
    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._entries: dict[str, object] = {}

    def register(self, name: str, entry: object) -> object:
        if not isinstance(name, str) or not name.strip():
            raise CoreError(f"{self._kind} registry: blank name")
        if name in self._entries:
            raise CoreError(f"{self._kind} registry: duplicate name {name!r}")
        self._entries[name] = entry
        return entry

    def resolve(self, name: str) -> object:
        try:
            return self._entries[name]
        except KeyError:
            raise CoreError(
                f"unknown {self._kind} {name!r}; registered: {self.names()}"
            ) from None

    def names(self) -> list[str]:
        return sorted(self._entries)


CARRIERS = Registry("carrier")
EVIDENCE_SOURCES = Registry("evidence source")
TRANSPORTS = Registry("transport")
POLICIES = Registry("policy")
SCORERS = Registry("scorer")

_REQUIRED_PROVENANCE = ("lock_key", "relpath", "sha256")


class EvidenceError(RuntimeError):
    """An evidence item is malformed or an evidence source is unavailable."""


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_uri: str
    content: str
    provenance: Mapping[str, str]

    def validate(self) -> "EvidenceItem":
        for label, value in (
            ("evidence_id", self.evidence_id),
            ("source_uri", self.source_uri),
            ("content", self.content),
        ):
            if not isinstance(value, str) or not value:
                raise EvidenceError(f"evidence {label} must be a non-empty string")
        if not isinstance(self.provenance, Mapping):
            raise EvidenceError("evidence provenance must be a mapping")
        missing = [key for key in _REQUIRED_PROVENANCE if key not in self.provenance]
        if missing:
            raise EvidenceError(f"evidence provenance lacks required keys {missing}")
        assert_information_boundary(self.runtime_view())
        assert_information_boundary(dict(self.provenance))
        return self

    def runtime_view(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "source_uri": self.source_uri,
            "content": self.content,
        }

    def provenance_view(self) -> dict[str, object]:
        return dict(self.provenance)


@dataclass(frozen=True)
class SampleOutcome:
    sample_id: str
    request_ids: tuple[str, ...]
    text: str
    admitted: bool
    request_sha256: str
    response_sha256: str


@dataclass(frozen=True)
class RunResult:
    run_id: str
    arm: str
    outputs_path: Path
    trace_manifest_hash: str
    cost: Mapping[str, object]


@dataclass(frozen=True)
class PayloadBindingContext:
    """Immutable payload<->plan<->split binding facts (R0 repair T3, invariants I3/I4).

    Built by the driver from the T1 :class:`~.split_receipt.VerifiedSplit` (the
    frozen, live-recomputed sample id set actually authorized for this run) and
    the same carrier loader's per-sample facts, plus the controlled data root
    and the specific carrier's own subdirectory beneath it. This is the object
    a :class:`~.model.FrozenCoreAdapter` must be constructed with: a payload can
    name any sample id, carrier or path string it likes, but the adapter only
    ever trusts what this context says was actually loaded for this run.
    """

    carrier_lock_key: str
    allowed_sample_ids: frozenset[str]
    sample_facts: Mapping[str, tuple[float, int]]
    data_root: Path
    carrier_root: Path

    def validate(self) -> "PayloadBindingContext":
        """Structural self-check, no filesystem access: a malformed binding
        context (wrong shape, sample_facts that don't exactly cover
        allowed_sample_ids, a carrier_root outside data_root) refuses rather
        than silently under-checking payloads later."""

        if not isinstance(self.carrier_lock_key, str) or not self.carrier_lock_key.strip():
            raise CoreError("binding context carrier_lock_key must be a non-empty string")
        if not isinstance(self.allowed_sample_ids, frozenset) or not self.allowed_sample_ids:
            raise CoreError("binding context allowed_sample_ids must be a non-empty frozenset")
        if not all(
            isinstance(sample_id, str) and sample_id for sample_id in self.allowed_sample_ids
        ):
            raise CoreError("binding context allowed_sample_ids must contain non-empty strings")
        if not isinstance(self.sample_facts, Mapping) or set(self.sample_facts) != set(
            self.allowed_sample_ids
        ):
            raise CoreError(
                "binding context sample_facts keys must exactly match allowed_sample_ids"
            )
        for sample_id, fact in self.sample_facts.items():
            if not isinstance(fact, tuple) or len(fact) != 2:
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] must be an "
                    "(audio_seconds, sample_rate_hz) tuple"
                )
            audio_seconds, sample_rate_hz = fact
            if (
                isinstance(audio_seconds, bool)
                or not isinstance(audio_seconds, (int, float))
                or not math.isfinite(audio_seconds)
                or audio_seconds <= 0
            ):
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] audio_seconds must be "
                    "a finite positive number"
                )
            if (
                isinstance(sample_rate_hz, bool)
                or not isinstance(sample_rate_hz, int)
                or sample_rate_hz <= 0
            ):
                raise CoreError(
                    f"binding context sample_facts[{sample_id!r}] sample_rate_hz must be "
                    "a positive integer"
                )
        if not isinstance(self.data_root, Path) or not isinstance(self.carrier_root, Path):
            raise CoreError("binding context data_root/carrier_root must be Path objects")
        if not self.carrier_root.is_relative_to(self.data_root):
            raise CoreError("binding context carrier_root must be beneath data_root")
        return self


@dataclass
class SampleContext:
    sample: object
    evidence: list[EvidenceItem]
    adapter: object
    sink: object
    arm: str
    task_instruction: str
    decoding_params: Mapping[str, object]
    request_id_base: str
    retrieval_query: str | None = None
    extras: dict[str, object] = field(default_factory=dict)
