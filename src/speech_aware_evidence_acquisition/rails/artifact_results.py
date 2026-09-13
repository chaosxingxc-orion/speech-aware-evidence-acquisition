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
        return canonical


def build_slurp_hypothesis_artifact_validator(
    contract: Mapping[str, object], *, data_root: Path
) -> SlurpHypothesisArtifactValidator:
    if not isinstance(contract, Mapping) or set(contract) not in (
        {"id", "max_candidates", "source_catalog"},
        {"id", "min_candidates", "max_candidates", "source_catalog"},
    ):
        raise ArtifactContentError(
            "SLURP hypothesis content contract must contain id, max_candidates, "
            "source_catalog and optional min_candidates"
        )
    if contract.get("id") != SLURP_HYPOTHESIS_CONTENT_ID:
        raise ArtifactContentError("SLURP hypothesis content contract id is invalid")
    maximum = contract.get("max_candidates")
    minimum = contract.get("min_candidates", 1)
    if (
        isinstance(minimum, bool)
        or not isinstance(minimum, int)
        or isinstance(maximum, bool)
        or not isinstance(maximum, int)
        or not 1 <= minimum <= maximum <= 3
    ):
        raise ArtifactContentError(
            "SLURP hypothesis candidate bounds must satisfy 1 <= min <= max <= 3"
        )
    ids, source_sha = _source_catalog(contract, data_root)
    return SlurpHypothesisArtifactValidator(ids, minimum, maximum, source_sha)


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


register_artifact_content_v1()

__all__ = [
    "ArtifactContentError",
    "SLURP_HYPOTHESIS_CONTENT_ID",
    "SlurpHypothesisArtifactValidator",
    "build_slurp_hypothesis_artifact_validator",
    "slurp_intent_hypotheses_response_format",
]
