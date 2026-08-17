"""EvidenceItem/EvidenceSet: the evidence contract feeding a SupplyPacket.

Legality fields (``span_source``/``reference_source``/``legality_tier``)
REUSE ``core.legality``'s own vocabulary and either-field rule verbatim --
this module never re-derives or duplicates that machinery. See
``core.legality``'s module docstring for the rule itself; this module's own
job is only to carry the three fields on an ``EvidenceItem`` and to give
callers a direct way to run the SAME check
(``core.legality.resolve_legality_declaration``) against one item.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping

from ..core.legality import LegalityDeclaration, resolve_legality_declaration
from .errors import RailsError
from .hashing import content_hash

EVIDENCE_SET_VERSION = "evidence-set-v1"


class RetrievalKeyKind(str, Enum):
    """Names the task-native key a retrieval query was resolved against.
    Non-exhaustive by design (owner scope ruling, 2026-08-17: no encoder
    view is ever a key kind here) -- :class:`RetrievalParams`'s own
    ``key_kind`` field accepts any non-empty string; these two are today's
    known values, not a closed set. A future task adapter is free to
    introduce its own key-kind string without editing this module, the same
    open-registration spirit ``core.base.Registry`` applies everywhere else
    in this study."""

    TASK_CONTEXT = "task-context"
    FIRST_PASS_TEXT = "first-pass-text"


@dataclass(frozen=True)
class EvidenceItem:
    """One evidence item, legality-typed via ``core.legality``'s own
    vocabulary (module docstring) -- never a parallel/re-derived model.
    ``span_source``/``reference_source``/``legality_tier`` are OPTIONAL,
    exactly the way ``core.legality.resolve_legality_declaration`` already
    treats a baseline config's same-named keys: absent is grandfathered (a
    warning, never a refusal); declared-and-inconsistent is refused (the
    either-field rule)."""

    evidence_id: str
    content: str
    source_ref: str
    span_source: str | None = None
    reference_source: str | None = None
    legality_tier: str | None = None
    evidence_materialization_id: str | None = None

    def _legality_values(self) -> dict[str, object]:
        return {
            "arm": f"rails-evidence-item:{self.evidence_id}",
            "span_source": self.span_source,
            "reference_source": self.reference_source,
            "legality_tier": self.legality_tier,
            "evidence_materialization_id": self.evidence_materialization_id,
            "evidence_source": "rails-evidence-item",
        }

    def resolve_legality(self, root: Path) -> LegalityDeclaration:
        """Re-run the SAME either-field rule
        (``core.legality.resolve_legality_declaration``) this study already
        machine-enforces at the baseline-config-arm level -- never a
        parallel legality model. Raises ``core.legality.LegalityError``
        exactly when that function would: a ``legality_tier="legal"``
        declaration alongside a gold-derived ``span_source``/
        ``reference_source``, or a ``reference_source`` inconsistent with a
        known oracle-lineage ``evidence_materialization_id``."""

        return resolve_legality_declaration(self._legality_values(), root)

    def validate(self) -> "EvidenceItem":
        for label, value in (
            ("evidence_id", self.evidence_id),
            ("content", self.content),
            ("source_ref", self.source_ref),
        ):
            if not isinstance(value, str) or not value:
                raise RailsError(f"EvidenceItem.{label} must be a non-empty string")
        for label, value in (
            ("span_source", self.span_source),
            ("reference_source", self.reference_source),
            ("legality_tier", self.legality_tier),
            ("evidence_materialization_id", self.evidence_materialization_id),
        ):
            if value is not None and not isinstance(value, str):
                raise RailsError(f"EvidenceItem.{label} must be a string or None, got {value!r}")
        return self

    def as_json(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "content": self.content,
            "source_ref": self.source_ref,
            "span_source": self.span_source,
            "reference_source": self.reference_source,
            "legality_tier": self.legality_tier,
            "evidence_materialization_id": self.evidence_materialization_id,
        }

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "EvidenceItem":
        return cls(
            evidence_id=document["evidence_id"],
            content=document["content"],
            source_ref=document["source_ref"],
            span_source=document.get("span_source"),
            reference_source=document.get("reference_source"),
            legality_tier=document.get("legality_tier"),
            evidence_materialization_id=document.get("evidence_materialization_id"),
        ).validate()


@dataclass(frozen=True)
class RetrievalParams:
    """Retrieval knobs an ``EvidenceSet`` was assembled under. ``key_kind``
    names the task-native query key (module docstring of
    :class:`RetrievalKeyKind`) -- there is deliberately no ``views`` field
    here (owner scope ruling, 2026-08-17): multi-view speech embeddings are
    out of this study's scope."""

    tau: float
    k: int
    key_kind: str

    def validate(self) -> "RetrievalParams":
        if (
            isinstance(self.tau, bool)
            or not isinstance(self.tau, (int, float))
            or not (0.0 <= float(self.tau) <= 1.0)
        ):
            raise RailsError(f"RetrievalParams.tau must be a number in [0, 1], got {self.tau!r}")
        if isinstance(self.k, bool) or not isinstance(self.k, int) or self.k < 0:
            raise RailsError(f"RetrievalParams.k must be a non-negative integer, got {self.k!r}")
        if not isinstance(self.key_kind, str) or not self.key_kind:
            raise RailsError("RetrievalParams.key_kind must be a non-empty string")
        return self

    def as_json(self) -> dict[str, object]:
        return {"tau": self.tau, "k": self.k, "key_kind": self.key_kind}

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "RetrievalParams":
        return cls(tau=document["tau"], k=document["k"], key_kind=document["key_kind"]).validate()


@dataclass(frozen=True)
class EvidenceSet:
    items: tuple[EvidenceItem, ...]
    query_ref: str
    retrieval_params: RetrievalParams
    evidence_set_version: str = EVIDENCE_SET_VERSION

    def validate(self) -> "EvidenceSet":
        if not isinstance(self.items, tuple):
            raise RailsError("EvidenceSet.items must be a tuple")
        seen: set[str] = set()
        for item in self.items:
            if not isinstance(item, EvidenceItem):
                raise RailsError("EvidenceSet.items entries must be EvidenceItem instances")
            item.validate()
            if item.evidence_id in seen:
                raise RailsError(f"EvidenceSet.items has a duplicate evidence_id {item.evidence_id!r}")
            seen.add(item.evidence_id)
        if not isinstance(self.query_ref, str) or not self.query_ref:
            raise RailsError("EvidenceSet.query_ref must be a non-empty string")
        self.retrieval_params.validate()
        if not isinstance(self.evidence_set_version, str) or not self.evidence_set_version:
            raise RailsError("EvidenceSet.evidence_set_version must be a non-empty string")
        return self

    def assert_legal_for_deployment(self, root: Path) -> tuple[LegalityDeclaration, ...]:
        """Resolve every item's legality declaration (fail-closed:
        ``core.legality.LegalityError`` propagates on the FIRST item that
        fails the either-field rule -- never silently dropped or
        downgraded). Returns each item's :class:`~core.legality.LegalityDeclaration`
        in item order for a caller that wants to record them (e.g. a run
        manifest's own ``"legality"`` block, ``core.legality.
        describe_legality_for_manifest``'s per-arm analog)."""

        return tuple(item.resolve_legality(root) for item in self.items)

    def as_json(self) -> dict[str, object]:
        return {
            "items": [item.as_json() for item in self.items],
            "query_ref": self.query_ref,
            "retrieval_params": self.retrieval_params.as_json(),
            "evidence_set_version": self.evidence_set_version,
        }

    def content_hash(self) -> str:
        return content_hash(self.validate().as_json())

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "EvidenceSet":
        return cls(
            items=tuple(EvidenceItem.from_json(item) for item in document.get("items", [])),
            query_ref=document["query_ref"],
            retrieval_params=RetrievalParams.from_json(document["retrieval_params"]),
            evidence_set_version=document.get("evidence_set_version", EVIDENCE_SET_VERSION),
        ).validate()
