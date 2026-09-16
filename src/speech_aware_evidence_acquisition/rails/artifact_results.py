"""Registered scoreless artifact content contracts.

The model response remains immutable trace evidence. A validator may add
trusted sample/schema bookkeeping in a separate canonical artifact view, but
must never repair, reorder, or drop model-proposed content.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from ..core.base import ARTIFACT_CONTENT_VALIDATORS
from .candidate_contract_lookup import canonical_sha256
from .slurp_candidate_contracts import PROVIDER_SCHEMA
from .slurp_intent_hypotheses import canonicalize_slurp_intent_hypothesis_response

SLURP_HYPOTHESIS_CONTENT_ID = "slurp-intent-hypotheses-v1"


class ArtifactContentError(ValueError):
    """A typed artifact source or its model-produced content is invalid."""


def _source_catalog(
    contract: Mapping[str, object], data_root: Path
) -> tuple[tuple[str, ...], str]:
    pin = contract.get("source_catalog")
    if not isinstance(pin, Mapping) or set(pin) != {
        "data_relpath",
        "sha256",
        "source_sha256",
    }:
        raise ArtifactContentError(
            "source_catalog must pin data_relpath, sha256 and source_sha256"
        )
    relpath = pin.get("data_relpath")
    if (
        not isinstance(relpath, str)
        or not relpath
        or "\\" in relpath
        or ":" in relpath
        or any(part in {"", ".", ".."} for part in relpath.split("/"))
    ):
        raise ArtifactContentError(
            "source_catalog data_relpath must be canonical relative POSIX"
        )
    path = (Path(data_root) / relpath).resolve()
    if not path.is_relative_to(Path(data_root).resolve()):
        raise ArtifactContentError("source_catalog escapes data root")
    try:
        raw = path.read_bytes()
        document = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ArtifactContentError(f"cannot read source_catalog: {error}") from error
    if hashlib.sha256(raw).hexdigest() != pin.get("sha256"):
        raise ArtifactContentError("source_catalog file SHA mismatch")
    if not isinstance(document, Mapping) or document.get("schema") != PROVIDER_SCHEMA:
        raise ArtifactContentError(
            "source_catalog is not a canonical SLURP provider catalog"
        )
    if canonical_sha256(document) != pin.get("source_sha256"):
        raise ArtifactContentError("source_catalog provider source SHA mismatch")
    profiles = document.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise ArtifactContentError("source_catalog profiles must be non-empty")
    ids = tuple(row.get("candidate_id") for row in profiles if isinstance(row, Mapping))
    if len(ids) != len(profiles) or any(
        not isinstance(value, str) or not value for value in ids
    ):
        raise ArtifactContentError("source_catalog profiles need candidate_id")
    if len(ids) != len(set(ids)):
        raise ArtifactContentError(
            "source_catalog candidate IDs must be unique and ordered"
        )
    return ids, str(pin["source_sha256"])


@dataclass(frozen=True)
class SlurpHypothesisArtifactValidator:
    legal_intent_ids: tuple[str, ...]
    min_candidates: int
    max_candidates: int
    source_sha256: str
    max_distinction_chars: int | None = None
    max_evidence_refs: int | None = None
    max_unresolved_fields: int | None = None

    def canonicalize(self, raw_response: str, *, sample_id: str) -> str:
        canonical = canonicalize_slurp_intent_hypothesis_response(
            raw_response,
            sample_id=sample_id,
            legal_intent_ids=self.legal_intent_ids,
            max_candidates=self.max_candidates,
        )
        if len(json.loads(canonical)["candidates"]) < self.min_candidates:
            raise ArtifactContentError(
                f"SLURP hypothesis response requires at least {self.min_candidates} candidates"
            )
        candidates = json.loads(canonical)["candidates"]
        for index, candidate in enumerate(candidates):
            if (
                self.max_distinction_chars is not None
                and len(candidate["distinction"]) > self.max_distinction_chars
            ):
                raise ArtifactContentError(
                    "SLURP hypothesis candidate "
                    f"{index} distinction exceeds {self.max_distinction_chars} characters"
                )
            if (
                self.max_evidence_refs is not None
                and len(candidate["evidence_refs"]) > self.max_evidence_refs
            ):
                raise ArtifactContentError(
                    "SLURP hypothesis candidate "
                    f"{index} evidence_refs exceeds {self.max_evidence_refs} items"
                )
            if (
                self.max_unresolved_fields is not None
                and len(candidate["unresolved_fields"]) > self.max_unresolved_fields
            ):
                raise ArtifactContentError(
                    "SLURP hypothesis candidate "
                    f"{index} unresolved_fields exceeds {self.max_unresolved_fields} items"
                )
        return canonical


def build_slurp_hypothesis_artifact_validator(
    contract: Mapping[str, object], *, data_root: Path
) -> SlurpHypothesisArtifactValidator:
    required = {"id", "max_candidates", "source_catalog"}
    optional = {
        "min_candidates",
        "max_distinction_chars",
        "max_evidence_refs",
        "max_unresolved_fields",
    }
    if (
        not isinstance(contract, Mapping)
        or not required <= set(contract)
        or not set(contract) <= required | optional
    ):
        raise ArtifactContentError(
            "SLURP hypothesis content contract must contain id, max_candidates, "
            "source_catalog and optional candidate or output bounds"
        )
    if contract.get("id") != SLURP_HYPOTHESIS_CONTENT_ID:
        raise ArtifactContentError("SLURP hypothesis content contract id is invalid")
    ids, source_sha = _source_catalog(contract, data_root)
    maximum = contract.get("max_candidates")
    minimum = contract.get("min_candidates", 1)
    if (
        isinstance(minimum, bool)
        or not isinstance(minimum, int)
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or not 1 <= minimum <= maximum <= len(ids)
    ):
        raise ArtifactContentError(
            "SLURP hypothesis candidate bounds must satisfy "
            "1 <= min <= max <= the legal intent count"
        )
    max_distinction_chars = contract.get("max_distinction_chars")
    if max_distinction_chars is not None and (
        isinstance(max_distinction_chars, bool)
        or not isinstance(max_distinction_chars, int)
        or max_distinction_chars < 1
    ):
        raise ArtifactContentError(
            "SLURP hypothesis output bound max_distinction_chars must be a positive integer"
        )
    max_evidence_refs = contract.get("max_evidence_refs")
    max_unresolved_fields = contract.get("max_unresolved_fields")
    for field, value in (
        ("max_evidence_refs", max_evidence_refs),
        ("max_unresolved_fields", max_unresolved_fields),
    ):
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 0 <= value <= 32
        ):
            raise ArtifactContentError(
                f"SLURP hypothesis output bound {field} must be an integer from 0 to 32"
            )
    return SlurpHypothesisArtifactValidator(
        ids,
        minimum,
        maximum,
        source_sha,
        max_distinction_chars,
        max_evidence_refs,
        max_unresolved_fields,
    )


def slurp_intent_hypotheses_response_format(
    _lock: Mapping[str, object], root: Path, **params: object
) -> Mapping[str, object]:
    validator = build_slurp_hypothesis_artifact_validator(params, data_root=root)
    candidate = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "intent_id",
            "distinction",
            "evidence_refs",
            "unresolved_fields",
        ],
        "properties": {
            "intent_id": {
                "type": "string",
                "enum": list(validator.legal_intent_ids),
            },
            "distinction": {"type": "string"},
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 32,
            },
            "unresolved_fields": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 32,
            },
        },
    }
    if validator.max_distinction_chars is not None:
        candidate["properties"]["distinction"]["maxLength"] = (
            validator.max_distinction_chars
        )
    if validator.max_evidence_refs is not None:
        candidate["properties"]["evidence_refs"]["maxItems"] = (
            validator.max_evidence_refs
        )
    if validator.max_unresolved_fields is not None:
        candidate["properties"]["unresolved_fields"]["maxItems"] = (
            validator.max_unresolved_fields
        )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "slurp_intent_hypotheses",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["candidates"],
                "properties": {
                    "candidates": {
                        "type": "array",
                        "minItems": validator.min_candidates,
                        "maxItems": validator.max_candidates,
                        "items": candidate,
                    }
                },
            },
        },
    }


def register_artifact_content_v1() -> None:
    if SLURP_HYPOTHESIS_CONTENT_ID not in ARTIFACT_CONTENT_VALIDATORS.names():
        ARTIFACT_CONTENT_VALIDATORS.register(
            SLURP_HYPOTHESIS_CONTENT_ID,
            build_slurp_hypothesis_artifact_validator,
        )
    from .training_feedback_artifacts import (
        TRAINING_FEEDBACK_CONTENT_ID,
        build_training_feedback_artifact_validator,
    )

    if TRAINING_FEEDBACK_CONTENT_ID not in ARTIFACT_CONTENT_VALIDATORS.names():
        ARTIFACT_CONTENT_VALIDATORS.register(
            TRAINING_FEEDBACK_CONTENT_ID,
            build_training_feedback_artifact_validator,
        )


register_artifact_content_v1()

__all__ = [
    "ArtifactContentError",
    "SLURP_HYPOTHESIS_CONTENT_ID",
    "SlurpHypothesisArtifactValidator",
    "build_slurp_hypothesis_artifact_validator",
    "slurp_intent_hypotheses_response_format",
]
