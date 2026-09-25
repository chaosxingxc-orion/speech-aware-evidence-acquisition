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
from .slurp_intent_hypotheses import (
    DEFAULT_FALLBACK_DISTINCTION,
    canonicalize_slurp_intent_hypothesis_response,
    validate_fallback_candidate_ids,
    validate_fallback_distinction,
)

SLURP_HYPOTHESIS_CONTENT_ID = "slurp-intent-hypotheses-v1"

#: Stage-3 F11, cell VERIFY-1: the id of the SELECTION contact's output
#: contract. Registered in ``rails.controllers.register_response_formats_v1``
#: and bound by ``configs/policy/phase-slurp-verify-select-v1.json``.
SLURP_VERIFIER_CHOICE_FORMAT_ID = "slurp-verifier-choice-v1"

#: The hard ceiling on the one-line reason. A reason is diagnostic only -- the
#: cell's measured quantity is the chosen position -- so it is bounded rather
#: than free: an unbounded field on a 625-row probe is a completion-token bill
#: with no read attached to it.
SLURP_VERIFIER_REASON_MAX_CHARS = 512


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
    #: FIX-1: the Perception-side declaration of the standing fallback
    #: option (docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md).
    #: Validated here, next to the rest of this same contract, so
    #: ``perception.fill_params.fallback_candidates`` is one legal, hashed
    #: key of the Perception phase's own material. It is deliberately NEVER
    #: read by :meth:`canonicalize` or by :func:`slurp_intent_hypotheses_response_format`:
    #: the fallback must never repair, reorder or drop the model's own
    #: sealed response, and must never change what the model itself is
    #: asked to produce. The actual consumption-time append happens where
    #: the candidate state is READ -- ``rails.knowledge_provider`` (slot
    #: supply) and ``rails.role_context`` (Solver/Reviewer rendering) --
    #: each of which declares this SAME option, by the same name, at its
    #: own consumption site, exactly as ``max_candidates`` and
    #: ``projection_policy`` are already independently declared at each of
    #: those sites rather than threaded through a single physical config
    #: key.
    fallback_candidates: tuple[str, ...] = ()
    fallback_distinction: str = DEFAULT_FALLBACK_DISTINCTION

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
        "fallback_candidates",
        "fallback_distinction",
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
    # FIX-1: validated here (fail-closed, against this SAME legal inventory)
    # but never fed to the schema below or to .canonicalize() -- see the
    # dataclass field comment for why.
    try:
        fallback_candidates = validate_fallback_candidate_ids(
            contract.get("fallback_candidates"), legal_intent_ids=ids,
        )
    except ValueError as error:
        raise ArtifactContentError(str(error)) from error
    if "fallback_distinction" in contract:
        if not fallback_candidates:
            raise ArtifactContentError(
                "fallback_distinction requires a non-empty fallback_candidates"
            )
        try:
            fallback_distinction = validate_fallback_distinction(
                contract["fallback_distinction"]
            )
        except ValueError as error:
            raise ArtifactContentError(str(error)) from error
    else:
        fallback_distinction = DEFAULT_FALLBACK_DISTINCTION
    return SlurpHypothesisArtifactValidator(
        ids,
        minimum,
        maximum,
        source_sha,
        max_distinction_chars,
        max_evidence_refs,
        max_unresolved_fields,
        fallback_candidates,
        fallback_distinction,
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


# ---------------------------------------------------------------------------
# Stage-3 F11 (cell VERIFY-1): the verifier's two-field choice.
# ---------------------------------------------------------------------------
#
# EXACTLY TWO FIELDS, and the narrower one is the measured one. "chosen_position"
# is the 1-based POSITION in the candidate block
# ``rails.phase_material.render_sealed_sample_block`` rendered, never a sealed
# sample index: the block deliberately never shows the sample index, so a
# position has to be resolved through the per-row permutation
# (``rails.phase_material.sealed_sample_permutation``) and a verifier cannot
# pick "sample 0" by naming a number it read off the prompt. "reason" is one
# bounded line, diagnostic only.
#
# The position is an integer ENUM rather than an integer with minimum/maximum
# for a llama.cpp reason: an enum lowers to a closed set of literal
# alternatives in every JSON-schema-to-grammar version this study has served,
# which is the same reason ``slurp_intent_hypotheses_response_format`` puts its
# legal intent ids in an enum.


def slurp_verifier_choice_response_format(
    _lock: Mapping[str, object],
    _root: Path,
    **params: object,
) -> Mapping[str, object]:
    """The registered ``slurp-verifier-choice-v1`` structured-output contract.

    ``candidate_count`` (required) is how many numbered candidates the block
    carries, and it must equal the phase material's own
    ``predecessor_source.expected_sample_count`` -- the cell config states it
    once per side and ``tests/unit/test_slurp_verify1_registration.py`` proves
    the two agree, because a schema that allowed a position the block does not
    render would admit an unresolvable answer.
    ``max_reason_chars`` (optional) bounds the diagnostic line.
    """

    required = {"candidate_count"}
    optional = {"max_reason_chars"}
    if not required <= set(params) or not set(params) <= required | optional:
        raise ArtifactContentError(
            "the SLURP verifier choice contract takes candidate_count and an "
            "optional max_reason_chars, and nothing else"
        )
    count = params["candidate_count"]
    if isinstance(count, bool) or not isinstance(count, int) or not 2 <= count <= 16:
        raise ArtifactContentError(
            "SLURP verifier choice candidate_count must be an integer from 2 to 16"
        )
    reason_chars = params.get("max_reason_chars", SLURP_VERIFIER_REASON_MAX_CHARS)
    if (
        isinstance(reason_chars, bool)
        or not isinstance(reason_chars, int)
        or not 1 <= reason_chars <= SLURP_VERIFIER_REASON_MAX_CHARS
    ):
        raise ArtifactContentError(
            "SLURP verifier choice max_reason_chars must be an integer from 1 to "
            f"{SLURP_VERIFIER_REASON_MAX_CHARS}"
        )
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "slurp_verifier_choice",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": ["chosen_position", "reason"],
                "properties": {
                    "chosen_position": {
                        "type": "integer",
                        "enum": list(range(1, count + 1)),
                    },
                    "reason": {"type": "string", "maxLength": reason_chars},
                },
            },
        },
    }


def parse_slurp_verifier_choice(
    raw_response: str, *, candidate_count: int,
    max_reason_chars: int = SLURP_VERIFIER_REASON_MAX_CHARS,
) -> dict[str, object]:
    """The parser of record for a ``slurp-verifier-choice-v1`` response.

    Beside the schema above, in this module, so the contract has ONE authority:
    a read that parsed the response differently from the way the request asked
    for it would be measuring its own leniency. Returns
    ``{"chosen_position": int, "reason": str}``; raises
    :class:`ArtifactContentError` on anything the schema would not have
    produced, so a non-conforming row is a counted parse failure in the read
    rather than a silently coerced choice.
    """

    if isinstance(candidate_count, bool) or not isinstance(candidate_count, int) or (
        not 2 <= candidate_count <= 16
    ):
        raise ArtifactContentError(
            "parse_slurp_verifier_choice needs a candidate_count from 2 to 16"
        )
    if not isinstance(raw_response, str) or not raw_response.strip():
        raise ArtifactContentError("a verifier choice response must be non-empty text")
    try:
        document = json.loads(raw_response)
    except json.JSONDecodeError as error:
        raise ArtifactContentError(
            f"verifier choice response is not one JSON object: {error}"
        ) from error
    if not isinstance(document, Mapping) or set(document) != {
        "chosen_position",
        "reason",
    }:
        raise ArtifactContentError(
            "a verifier choice response carries exactly the keys chosen_position "
            "and reason"
        )
    position = document["chosen_position"]
    if (
        isinstance(position, bool)
        or not isinstance(position, int)
        or not 1 <= position <= candidate_count
    ):
        raise ArtifactContentError(
            f"verifier chosen_position must be an integer from 1 to {candidate_count}"
        )
    reason = document["reason"]
    if (isinstance(max_reason_chars, bool) or not isinstance(max_reason_chars, int)
            or not 1 <= max_reason_chars <= SLURP_VERIFIER_REASON_MAX_CHARS):
        raise ArtifactContentError("invalid verifier reason character bound")
    if not isinstance(reason, str) or len(reason) > max_reason_chars:
        raise ArtifactContentError("verifier reason must be a string within its declared bound")
    return {"chosen_position": position, "reason": reason}


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
    "SLURP_VERIFIER_CHOICE_FORMAT_ID",
    "SLURP_VERIFIER_REASON_MAX_CHARS",
    "SlurpHypothesisArtifactValidator",
    "build_slurp_hypothesis_artifact_validator",
    "parse_slurp_verifier_choice",
    "slurp_intent_hypotheses_response_format",
    "slurp_verifier_choice_response_format",
]
