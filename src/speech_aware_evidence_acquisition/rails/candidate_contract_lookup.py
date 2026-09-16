"""Typed, hashable candidate-contract lookup results for native task actions.

The provider is bound to a canonical task-contract source by the caller. The
native model supplies only ordered candidate IDs; source identity and evidence
classification stay in the returned receipt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Protocol, Sequence, runtime_checkable

TOOL_ID = "saea-tool-candidate-contract-lookup-v1"
SCHEMA = "saea-candidate-contract-lookup-v1"
EVIDENCE_STATUS = "task-contract"
# The task-facing tools retain their separately configured request limits.
# This shared result model must also represent a complete SLURP legal inventory.
MAX_CANDIDATE_IDS = 64


class CandidateContractLookupError(ValueError):
    """A candidate request or canonical provider result is malformed."""


def canonical_sha256(value: object) -> str:
    """Hash one JSON-safe value with the repository's canonical JSON spelling."""

    try:
        encoded = json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise CandidateContractLookupError(
            "candidate-contract value is not canonically JSON serializable"
        ) from error
    return hashlib.sha256(encoded).hexdigest()


def _text(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value.strip() != value
        or not value.isascii()
    ):
        raise CandidateContractLookupError(
            f"{field} must be non-empty trimmed ASCII text"
        )
    return value


def _text_tuple(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise CandidateContractLookupError(f"{field} must be a tuple")
    result = tuple(_text(item, field=field) for item in value)
    if len(result) != len(set(result)):
        raise CandidateContractLookupError(f"{field} contains a duplicate")
    return result


def _sha256(value: object, *, field: str) -> str:
    text = _text(value, field=field)
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise CandidateContractLookupError(f"{field} must be 64 lowercase hex characters")
    return text


@dataclass(frozen=True)
class CandidateContractRequest:
    """The only model-supplied payload: an ordered unique candidate list."""

    candidate_ids: tuple[str, ...]

    @classmethod
    def from_ids(cls, candidate_ids: Sequence[str]) -> "CandidateContractRequest":
        if isinstance(candidate_ids, (str, bytes)):
            raise CandidateContractLookupError("candidate_ids must be a sequence")
        try:
            request = cls(tuple(candidate_ids))
        except TypeError as error:
            raise CandidateContractLookupError(
                "candidate_ids must be a sequence"
            ) from error
        return request.validate()

    def validate(self) -> "CandidateContractRequest":
        if not 1 <= len(self.candidate_ids) <= MAX_CANDIDATE_IDS:
            raise CandidateContractLookupError(
                f"candidate_ids must contain 1 to {MAX_CANDIDATE_IDS} items"
            )
        _text_tuple(self.candidate_ids, field="candidate_ids")
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": "saea-candidate-contract-request-v1",
            "candidate_ids": list(self.candidate_ids),
        }

    def content_hash(self) -> str:
        return canonical_sha256(self.as_json())


@dataclass(frozen=True)
class CandidateContractEvidence:
    """One value-free contract and contrast description for one candidate."""

    candidate_id: str
    operation: str
    schema: tuple[tuple[str, str], ...]
    contrast: str
    required_keys: tuple[str, ...] = ()
    optional_keys: tuple[str, ...] = ()
    conditional_keys: tuple[str, ...] = ()
    forbidden_keys: tuple[str, ...] = ()

    def validate(self) -> "CandidateContractEvidence":
        _text(self.candidate_id, field="candidate_id")
        _text(self.operation, field="operation")
        _text(self.contrast, field="contrast")
        if not isinstance(self.schema, tuple):
            raise CandidateContractLookupError("schema must be a tuple")
        schema_keys: list[str] = []
        for entry in self.schema:
            if (
                not isinstance(entry, tuple)
                or len(entry) != 2
                or not isinstance(entry[0], str)
                or not isinstance(entry[1], str)
            ):
                raise CandidateContractLookupError(
                    "schema entries must be (name, type) tuples"
                )
            schema_keys.append(_text(entry[0], field="schema name"))
            _text(entry[1], field="schema type")
        if len(schema_keys) != len(set(schema_keys)):
            raise CandidateContractLookupError("schema contains a duplicate name")
        known = set(schema_keys)
        for field, values in (
            ("required_keys", self.required_keys),
            ("optional_keys", self.optional_keys),
            ("conditional_keys", self.conditional_keys),
            ("forbidden_keys", self.forbidden_keys),
        ):
            names = _text_tuple(values, field=field)
            if field != "forbidden_keys" and not set(names) <= known:
                raise CandidateContractLookupError(
                    f"{field} names a field outside schema"
                )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "candidate_id": self.candidate_id,
            "operation": self.operation,
            "schema": [
                {"name": name, "type": type_name}
                for name, type_name in self.schema
            ],
            "required_keys": list(self.required_keys),
            "optional_keys": list(self.optional_keys),
            "conditional_keys": list(self.conditional_keys),
            "forbidden_keys": list(self.forbidden_keys),
            "contrast": self.contrast,
        }


@dataclass(frozen=True)
class CandidateContractLookupResult:
    """A source-bound, ordered, hashable lookup result."""

    request: CandidateContractRequest
    source_sha256: str
    candidates: tuple[CandidateContractEvidence, ...]
    evidence_status: str = EVIDENCE_STATUS

    def validate(self) -> "CandidateContractLookupResult":
        self.request.validate()
        _sha256(self.source_sha256, field="source_sha256")
        if self.evidence_status != EVIDENCE_STATUS:
            raise CandidateContractLookupError(
                f"evidence_status must be {EVIDENCE_STATUS!r}"
            )
        if not isinstance(self.candidates, tuple):
            raise CandidateContractLookupError("candidates must be a tuple")
        for candidate in self.candidates:
            if not isinstance(candidate, CandidateContractEvidence):
                raise CandidateContractLookupError(
                    "candidates must contain CandidateContractEvidence values"
                )
            candidate.validate()
        returned_ids = tuple(candidate.candidate_id for candidate in self.candidates)
        if len(returned_ids) != len(set(returned_ids)):
            raise CandidateContractLookupError("returned candidates contain a duplicate")
        if returned_ids != self.request.candidate_ids:
            raise CandidateContractLookupError(
                "returned candidate IDs must exactly match the requested order"
            )
        return self

    def validate_for(self, request: CandidateContractRequest) -> "CandidateContractLookupResult":
        request.validate()
        self.validate()
        if self.request != request:
            raise CandidateContractLookupError(
                "provider result is bound to a different candidate request"
            )
        return self

    def as_json(self) -> dict[str, object]:
        self.validate()
        return {
            "schema": SCHEMA,
            "request": self.request.as_json(),
            "request_sha256": self.request.content_hash(),
            "source_sha256": self.source_sha256,
            "evidence_status": self.evidence_status,
            "candidates": [candidate.as_json() for candidate in self.candidates],
        }

    def content_hash(self) -> str:
        return canonical_sha256(self.as_json())


@runtime_checkable
class CandidateContractProvider(Protocol):
    """Canonical task-contract source bound by a carrier adapter."""

    source_sha256: str

    def lookup(
        self, candidate_ids: tuple[str, ...]
    ) -> CandidateContractLookupResult:
        """Return contracts for exactly these IDs, in exactly this order."""


__all__ = [
    "CandidateContractEvidence",
    "CandidateContractLookupError",
    "CandidateContractLookupResult",
    "CandidateContractProvider",
    "CandidateContractRequest",
    "EVIDENCE_STATUS",
    "MAX_CANDIDATE_IDS",
    "SCHEMA",
    "TOOL_ID",
    "canonical_sha256",
]
