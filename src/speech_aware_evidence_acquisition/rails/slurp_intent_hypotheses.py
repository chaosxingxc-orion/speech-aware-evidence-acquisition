"""Validated SLURP intent-hypothesis state for registered phase material.

This is a reusable state/view capability, not an always-on agent workflow. A
fixed phase program may bind the view explicitly. The native answer-or-tool
loop cannot treat ordinary hypothesis JSON as an intermediate action: such a
loop needs a separately registered, model-selected candidate-contract tool.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .errors import RailsError
from .knowledge import AgentStateArtifact

HYPOTHESIS_STATE_SCHEMA = "saea-slurp-intent-hypotheses-v1"
HYPOTHESIS_SEMANTICS = "ranked-mutually-exclusive-intent-alternatives"
_CANDIDATE_KEYS = frozenset(
    {"intent_id", "distinction", "evidence_refs", "unresolved_fields"}
)
_DOCUMENT_KEYS = frozenset({"schema", "semantics", "sample_id", "candidates"})
_COMPACT_DOCUMENT_KEYS = frozenset({"candidates"})
_MAX_TEXT_CHARS = 512
_MAX_LIST_ITEMS = 32


class SlurpIntentHypothesisError(ValueError):
    """Raised when a hypothesis state cannot safely condition a later phase."""


@dataclass(frozen=True)
class SlurpIntentHypothesisCandidate:
    """One ranked, mutually exclusive legal intent alternative."""

    intent_id: str
    distinction: str
    evidence_refs: tuple[str, ...]
    unresolved_fields: tuple[str, ...]


@dataclass(frozen=True)
class SlurpIntentHypothesisState:
    """A compact ordered set of alternatives for one source-bound sample."""

    sample_id: str
    candidates: tuple[SlurpIntentHypothesisCandidate, ...]


def _text(value: object, *, field: str, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise SlurpIntentHypothesisError(f"{field} must be a non-empty string")
    if len(value) > _MAX_TEXT_CHARS:
        raise SlurpIntentHypothesisError(
            f"{field} exceeds the {_MAX_TEXT_CHARS}-character bound"
        )
    return value


def _texts(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > _MAX_LIST_ITEMS:
        raise SlurpIntentHypothesisError(
            f"{field} must be a list with at most {_MAX_LIST_ITEMS} entries"
        )
    result = tuple(_text(item, field=field) for item in value)
    if len(set(result)) != len(result):
        raise SlurpIntentHypothesisError(f"{field} entries must be unique and ordered")
    return result


def _legal_ids(values: Iterable[str]) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise SlurpIntentHypothesisError(
            "legal_intent_ids must be a non-empty set of strings"
        )
    legal = frozenset(values)
    if not legal or any(not isinstance(value, str) or not value for value in legal):
        raise SlurpIntentHypothesisError(
            "legal_intent_ids must be a non-empty set of strings"
        )
    return legal


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise SlurpIntentHypothesisError(f"duplicate JSON key {key!r}")
        document[key] = value
    return document


def parse_slurp_intent_hypothesis_content(
    content: str,
    *,
    expected_sample_id: str | None,
    legal_intent_ids: Iterable[str],
    max_candidates: int,
) -> SlurpIntentHypothesisState:
    """Parse one compact shortlist against the full legal task inventory."""

    if isinstance(max_candidates, bool) or not isinstance(max_candidates, int):
        raise SlurpIntentHypothesisError("max_candidates must be an integer")
    legal = _legal_ids(legal_intent_ids)
    if max_candidates < 1 or max_candidates > len(legal):
        raise SlurpIntentHypothesisError(
            "max_candidates must be between 1 and the legal intent count"
        )
    try:
        document = json.loads(content, object_pairs_hook=_unique_json_object)
    except (TypeError, json.JSONDecodeError) as error:
        raise SlurpIntentHypothesisError("hypothesis state must be JSON") from error
    if not isinstance(document, Mapping) or set(document) != _DOCUMENT_KEYS:
        raise SlurpIntentHypothesisError(
            f"hypothesis state must contain exactly {sorted(_DOCUMENT_KEYS)}"
        )
    if document["schema"] != HYPOTHESIS_STATE_SCHEMA:
        raise SlurpIntentHypothesisError(
            f"hypothesis state schema must be {HYPOTHESIS_STATE_SCHEMA!r}"
        )
    if document["semantics"] != HYPOTHESIS_SEMANTICS:
        raise SlurpIntentHypothesisError(
            "hypothesis state semantics must identify ranked alternatives"
        )
    sample_id = _text(document["sample_id"], field="sample_id")
    if expected_sample_id is not None and sample_id != expected_sample_id:
        raise SlurpIntentHypothesisError(
            f"hypothesis sample_id {sample_id!r} does not match {expected_sample_id!r}"
        )
    rows = document["candidates"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= max_candidates:
        raise SlurpIntentHypothesisError(
            f"candidates must contain between 1 and at most {max_candidates} alternatives"
        )
    candidates: list[SlurpIntentHypothesisCandidate] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != _CANDIDATE_KEYS:
            raise SlurpIntentHypothesisError(
                f"candidate {index} must contain exactly {sorted(_CANDIDATE_KEYS)}"
            )
        intent_id = _text(row["intent_id"], field=f"candidate {index} intent_id")
        if intent_id not in legal:
            raise SlurpIntentHypothesisError(
                f"candidate {index} intent_id {intent_id!r} is not legal"
            )
        candidates.append(
            SlurpIntentHypothesisCandidate(
                intent_id=intent_id,
                distinction=_text(
                    row["distinction"], field=f"candidate {index} distinction"
                ),
                evidence_refs=_texts(
                    row["evidence_refs"], field=f"candidate {index} evidence_refs"
                ),
                unresolved_fields=_texts(
                    row["unresolved_fields"],
                    field=f"candidate {index} unresolved_fields",
                ),
            )
        )
    intent_ids = [candidate.intent_id for candidate in candidates]
    if len(set(intent_ids)) != len(intent_ids):
        raise SlurpIntentHypothesisError(
            "candidate intent_ids must be unique and ordered"
        )
    return SlurpIntentHypothesisState(
        sample_id=sample_id, candidates=tuple(candidates)
    )


def canonicalize_slurp_intent_hypothesis_response(
    content: str,
    *,
    sample_id: str,
    legal_intent_ids: Iterable[str],
    max_candidates: int,
) -> str:
    """Add trusted bookkeeping to one compact, otherwise unchanged response."""

    try:
        compact = json.loads(content, object_pairs_hook=_unique_json_object)
    except (TypeError, json.JSONDecodeError) as error:
        raise SlurpIntentHypothesisError("compact hypothesis response must be JSON") from error
    if not isinstance(compact, Mapping) or set(compact) != _COMPACT_DOCUMENT_KEYS:
        raise SlurpIntentHypothesisError(
            "compact hypothesis response must contain exactly candidates"
        )
    document = {
        "schema": HYPOTHESIS_STATE_SCHEMA,
        "semantics": HYPOTHESIS_SEMANTICS,
        "sample_id": sample_id,
        "candidates": compact["candidates"],
    }
    canonical = json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    parse_slurp_intent_hypothesis_content(
        canonical,
        expected_sample_id=sample_id,
        legal_intent_ids=legal_intent_ids,
        max_candidates=max_candidates,
    )
    return canonical


def parse_slurp_intent_hypothesis_state(
    artifact: AgentStateArtifact,
    *,
    expected_sample_id: str,
    legal_intent_ids: Iterable[str],
    max_candidates: int,
) -> SlurpIntentHypothesisState:
    """Validate an artifact and its exact source-response content binding."""

    try:
        artifact.validate()
    except RailsError as error:
        raise SlurpIntentHypothesisError(
            f"invalid source-bound hypothesis artifact: {error}"
        ) from error
    if not artifact.state_kind.startswith("phase:") or len(artifact.state_kind) == 6:
        raise SlurpIntentHypothesisError(
            "hypothesis artifact state_kind must name a phase"
        )
    actual = hashlib.sha256(artifact.content.encode("utf-8")).hexdigest()
    if actual != artifact.source_response_sha256:
        raise SlurpIntentHypothesisError(
            "hypothesis content does not match its source response SHA-256"
        )
    return parse_slurp_intent_hypothesis_content(
        artifact.content,
        expected_sample_id=expected_sample_id,
        legal_intent_ids=legal_intent_ids,
        max_candidates=max_candidates,
    )


@dataclass(frozen=True)
class SlurpIntentHypothesisStateFill:
    """Render validated alternatives as a deterministic English state suffix."""

    legal_intent_ids: frozenset[str]
    max_candidates: int

    def __init__(self, *, legal_intent_ids: Iterable[str], max_candidates: int):
        object.__setattr__(self, "legal_intent_ids", _legal_ids(legal_intent_ids))
        object.__setattr__(self, "max_candidates", max_candidates)
        if (
            isinstance(max_candidates, bool)
            or not isinstance(max_candidates, int)
            or max_candidates < 1
            or max_candidates > len(self.legal_intent_ids)
        ):
            raise SlurpIntentHypothesisError(
                "max_candidates must be between 1 and the legal intent count"
            )

    def __call__(self, state_content: str) -> str:
        raise SlurpIntentHypothesisError(
            "source-bound hypothesis fills require the full AgentStateArtifact"
        )

    def render_state(self, artifact: AgentStateArtifact, *, sample_id: str) -> str:
        state = parse_slurp_intent_hypothesis_state(
            artifact,
            expected_sample_id=sample_id,
            legal_intent_ids=self.legal_intent_ids,
            max_candidates=self.max_candidates,
        )
        lines = [
            "Retained intent hypotheses are ranked alternatives, not multiple task outputs."
        ]
        for rank, candidate in enumerate(state.candidates, start=1):
            evidence = ", ".join(candidate.evidence_refs) or "none recorded"
            unresolved = ", ".join(candidate.unresolved_fields) or "none"
            lines.append(
                f"{rank}. {candidate.intent_id}: {candidate.distinction} "
                f"Model-proposed and unverified evidence references: {evidence}. "
                f"Unresolved fields: {unresolved}."
            )
        lines.append(
            "Choose one legal final intent and its entities from the available evidence; "
            "the full legal intent inventory remains authoritative."
        )
        return "\n".join(lines)
