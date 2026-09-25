"""Validated SLURP intent-hypothesis state for registered phase material.

This is a reusable state/view capability, not an always-on agent workflow. A
fixed phase program may bind the view explicitly. The native answer-or-tool
loop cannot treat ordinary hypothesis JSON as an intermediate action: such a
loop needs a separately registered, model-selected candidate-contract tool.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from .errors import RailsError
from .knowledge import AgentStateArtifact

HYPOTHESIS_STATE_SCHEMA = "saea-slurp-intent-hypotheses-v1"
HYPOTHESIS_SEMANTICS = "ranked-mutually-exclusive-intent-alternatives"
FIRST_OCCURRENCE_PROJECTION_POLICY_ID = (
    "first-occurrence-distinct-slurp-intent-hypotheses-v1"
)
_FIRST_OCCURRENCE_PROJECTION_POLICY = {
    "schema": "saea-slurp-intent-hypothesis-projection-policy-v1",
    "policy_id": FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    "input_candidate_count": 3,
    "identity_key": "intent_id",
    "retention": "first-occurrence-in-original-order",
}
FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256 = hashlib.sha256(
    json.dumps(
        _FIRST_OCCURRENCE_PROJECTION_POLICY,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID = (
    "bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
)
_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY = {
    **_FIRST_OCCURRENCE_PROJECTION_POLICY,
    "policy_id": BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    "input_candidate_count": {"min": 1, "max": 3},
}
BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256 = hashlib.sha256(
    json.dumps(
        _BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY,
        ensure_ascii=True, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID = (
    "configurable-bounded-first-occurrence-distinct-slurp-intent-hypotheses-v1"
)
_CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY = {
    **_FIRST_OCCURRENCE_PROJECTION_POLICY,
    "policy_id": CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    "input_candidate_count": {
        "min": 1,
        "max": "configured-max-candidates-within-legal-intent-inventory",
    },
}
CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256 = hashlib.sha256(
    json.dumps(
        _CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()
BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS = frozenset(
    {
        BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    }
)
_CANDIDATE_KEYS = frozenset(
    {"intent_id", "distinction", "evidence_refs", "unresolved_fields"}
)
_DOCUMENT_KEYS = frozenset({"schema", "semantics", "sample_id", "candidates"})
_COMPACT_DOCUMENT_KEYS = frozenset({"candidates"})
_MAX_TEXT_CHARS = 512
_MAX_LIST_ITEMS = 32

#: FIX-1 (docs/results/2026-09-17-slurp-a3-coverage-confusion-audit-v1.md):
#: the source a projected candidate carries. ``"model"`` is every candidate
#: the Perception response itself proposed -- the only value
#: :func:`parse_slurp_intent_hypothesis_content` ever assigns, so an
#: unconfigured cell never sees anything else. ``"fallback"`` marks a
#: candidate :func:`append_fallback_slurp_intent_hypothesis_candidates`
#: appended because a configured standing hypothesis was absent from the
#: model's own set; a fallback candidate is always explicitly labelled and
#: is never mistaken for a model proposal.
MODEL_CANDIDATE_SOURCE = "model"
FALLBACK_CANDIDATE_SOURCE = "fallback"
CANDIDATE_SOURCES = frozenset({MODEL_CANDIDATE_SOURCE, FALLBACK_CANDIDATE_SOURCE})

#: A standing fallback list is short and bounded -- at most two ids -- so the
#: option can never grow into a second, uncontrolled candidate channel; and a
#: fixed English distinction text, overridable up to a small character bound.
MAX_FALLBACK_CANDIDATES = 2
MAX_FALLBACK_DISTINCTION_CHARS = 128
DEFAULT_FALLBACK_DISTINCTION = (
    "standing fallback hypothesis: open-domain or chit-chat request with no "
    "other matching intent"
)


class SlurpIntentHypothesisError(ValueError):
    """Raised when a hypothesis state cannot safely condition a later phase."""


@dataclass(frozen=True)
class SlurpIntentHypothesisCandidate:
    """One ranked, mutually exclusive legal intent alternative.

    ``source`` defaults to :data:`MODEL_CANDIDATE_SOURCE` for every candidate
    the Perception response itself proposed. Only
    :func:`append_fallback_slurp_intent_hypothesis_candidates` ever
    constructs one with :data:`FALLBACK_CANDIDATE_SOURCE`, and it does so
    only for a configured id the model's own candidates did not name.
    """

    intent_id: str
    distinction: str
    evidence_refs: tuple[str, ...]
    unresolved_fields: tuple[str, ...]
    source: str = MODEL_CANDIDATE_SOURCE


@dataclass(frozen=True)
class SlurpIntentHypothesisState:
    """A compact ordered set of alternatives for one source-bound sample."""

    sample_id: str
    candidates: tuple[SlurpIntentHypothesisCandidate, ...]
    projection: SlurpIntentHypothesisProjection | None = None


@dataclass(frozen=True)
class SlurpIntentHypothesisProjectionPosition:
    """Audit binding from one original position to its retained first occurrence."""

    raw_position: int
    intent_id: str
    candidate_sha256: str
    first_raw_position: int
    projected_position: int
    retained_sha256: str


@dataclass(frozen=True)
class SlurpIntentHypothesisProjection:
    """One validated first-occurrence projection and its source provenance."""

    content: str
    original_text_sha256: str
    projected_content_sha256: str
    projection_policy_id: str
    projection_policy_sha256: str
    raw_positions: tuple[SlurpIntentHypothesisProjectionPosition, ...]


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


def validate_fallback_candidate_ids(
    fallback_candidates: object, *, legal_intent_ids: Iterable[str],
) -> tuple[str, ...]:
    """Validate a configured standing-fallback candidate list, fail-closed.

    Absent or empty is legal and returns ``()`` -- the no-op default that
    keeps an unconfigured cell's candidate set byte-for-byte unchanged. A
    non-empty declaration must be a plain list of at most
    :data:`MAX_FALLBACK_CANDIDATES` distinct, non-empty legal intent ids;
    anything else is refused before any candidate is read, so a
    misconfigured fallback can never silently become a partial list.
    """

    if fallback_candidates is None or fallback_candidates == ():
        return ()
    if isinstance(fallback_candidates, (str, bytes)) or not isinstance(
        fallback_candidates, Sequence
    ):
        raise SlurpIntentHypothesisError(
            "fallback_candidates must be a list of legal intent ids"
        )
    ids = tuple(fallback_candidates)
    if not ids:
        return ()
    if len(ids) > MAX_FALLBACK_CANDIDATES:
        raise SlurpIntentHypothesisError(
            f"fallback_candidates carries more than {MAX_FALLBACK_CANDIDATES} ids"
        )
    if any(not isinstance(item, str) or not item for item in ids):
        raise SlurpIntentHypothesisError(
            "fallback_candidates entries must be non-empty strings"
        )
    if len(set(ids)) != len(ids):
        raise SlurpIntentHypothesisError("fallback_candidates entries must be unique")
    legal = _legal_ids(legal_intent_ids)
    unknown = [item for item in ids if item not in legal]
    if unknown:
        raise SlurpIntentHypothesisError(
            f"fallback_candidates names id(s) outside the legal inventory: {unknown}"
        )
    return ids


def validate_fallback_distinction(value: object) -> str:
    """Validate a fixed English fallback distinction text, fail-closed."""

    if not isinstance(value, str) or not value.strip():
        raise SlurpIntentHypothesisError(
            "fallback_distinction must be a non-empty string"
        )
    if len(value) > MAX_FALLBACK_DISTINCTION_CHARS:
        raise SlurpIntentHypothesisError(
            f"fallback_distinction exceeds {MAX_FALLBACK_DISTINCTION_CHARS} characters"
        )
    return value


def append_fallback_slurp_intent_hypothesis_candidates(
    candidates: Sequence[SlurpIntentHypothesisCandidate],
    *,
    fallback_candidates: object = (),
    fallback_distinction: str = DEFAULT_FALLBACK_DISTINCTION,
    legal_intent_ids: Iterable[str],
) -> tuple[SlurpIntentHypothesisCandidate, ...]:
    """Append configured standing fallbacks the projected set is missing.

    Applied ONCE, after the bounded first-occurrence projection, to the
    CONSUMPTION-side candidate list only -- never to the sealed Perception
    artifact, which stays immutable model evidence
    (``rails.artifact_results`` module docstring). Every existing candidate
    is returned unchanged, in its original order, keeping its own
    :data:`MODEL_CANDIDATE_SOURCE` source; each configured fallback id absent
    from that set is appended at the END, in configured order, with
    :data:`FALLBACK_CANDIDATE_SOURCE`, the fixed ``fallback_distinction``
    text and empty ``evidence_refs``/``unresolved_fields``.

    A no-op -- a byte-for-byte identical output tuple -- whenever
    ``fallback_candidates`` is empty or every configured id is already
    present, which is exactly what makes the option's absence and its
    presence with an empty list the same behaviour.
    """

    ids = validate_fallback_candidate_ids(
        fallback_candidates, legal_intent_ids=legal_intent_ids
    )
    ordered = tuple(candidates)
    if not ids:
        return ordered
    distinction = validate_fallback_distinction(fallback_distinction)
    present = {candidate.intent_id for candidate in ordered}
    extra = tuple(
        SlurpIntentHypothesisCandidate(
            intent_id=fallback_id,
            distinction=distinction,
            evidence_refs=(),
            unresolved_fields=(),
            source=FALLBACK_CANDIDATE_SOURCE,
        )
        for fallback_id in ids
        if fallback_id not in present
    )
    if not extra:
        return ordered
    return ordered + extra


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


def _canonical_candidate_sha256(candidate: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            candidate, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def project_fixed_three_slurp_intent_hypotheses(
    content: str,
    *,
    sample_id: str,
    legal_intent_ids: Iterable[str],
) -> SlurpIntentHypothesisProjection:
    """Project a validated fixed-three response by exact first occurrence.

    All three original candidate objects are validated before projection.
    Duplicate intent IDs are allowed only at this explicit projection seam;
    the historical canonicalizer and state parser continue to reject them.
    """

    if not isinstance(content, str):
        raise SlurpIntentHypothesisError(
            "fixed-three hypothesis response must be JSON text"
        )
    legal = _legal_ids(legal_intent_ids)
    try:
        compact = json.loads(content, object_pairs_hook=_unique_json_object)
    except (TypeError, json.JSONDecodeError) as error:
        raise SlurpIntentHypothesisError(
            "fixed-three hypothesis response must be JSON"
        ) from error
    if not isinstance(compact, Mapping) or set(compact) != _COMPACT_DOCUMENT_KEYS:
        raise SlurpIntentHypothesisError(
            "fixed-three hypothesis response must contain exactly candidates"
        )
    rows = compact["candidates"]
    if not isinstance(rows, list) or len(rows) != 3:
        raise SlurpIntentHypothesisError(
            "fixed-three hypothesis response must contain exactly three candidates"
        )

    return _project_validated_rows(
        content, rows=rows, sample_id=sample_id, legal=legal,
        policy_id=FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
        policy_sha256=FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256,
    )


def project_bounded_slurp_intent_hypotheses(
    content: str,
    *,
    sample_id: str,
    legal_intent_ids: Iterable[str],
    max_candidates: int = 3,
    projection_policy: str = BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    raw_max_candidates: int | None = None,
) -> SlurpIntentHypothesisProjection:
    """Project a configured bounded response without editing the source.

    Validate every raw object before retaining the first occurrence of each
    intent. The historical default-three policy retains its exact identity.
    A seal reader with a reduced authority inventory can explicitly preserve
    the original bound on raw positions; duplicates do not consume distinct
    labels. Omission retains the historical parsing contract.
    """
    if not isinstance(content, str):
        raise SlurpIntentHypothesisError("bounded hypothesis response must be JSON text")
    legal = _legal_ids(legal_intent_ids)
    if (
        isinstance(max_candidates, bool)
        or not isinstance(max_candidates, int)
        or not 1 <= max_candidates <= len(legal)
    ):
        raise SlurpIntentHypothesisError(
            "max_candidates must be between 1 and the legal intent count"
        )
    if projection_policy not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS:
        raise SlurpIntentHypothesisError(
            "bounded hypothesis projection policy is unsupported"
        )
    if (
        max_candidates > 3
        and projection_policy
        != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
    ):
        raise SlurpIntentHypothesisError(
            "candidate bounds above three require the configurable bounded "
            "first-occurrence projection policy"
        )
    raw_limit = max_candidates
    if raw_max_candidates is not None:
        if (
            isinstance(raw_max_candidates, bool)
            or not isinstance(raw_max_candidates, int)
            or not max_candidates <= raw_max_candidates <= 3
            or projection_policy != BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        ):
            raise SlurpIntentHypothesisError(
                "explicit raw candidate bound requires the bounded-three policy "
                "and a bound between the projected limit and three"
            )
        raw_limit = raw_max_candidates
    try:
        compact = json.loads(content, object_pairs_hook=_unique_json_object)
    except (TypeError, json.JSONDecodeError) as error:
        raise SlurpIntentHypothesisError("bounded hypothesis response must be JSON") from error
    if not isinstance(compact, Mapping) or set(compact) != _COMPACT_DOCUMENT_KEYS:
        raise SlurpIntentHypothesisError(
            "bounded hypothesis response must contain exactly candidates"
        )
    rows = compact["candidates"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= raw_limit:
        raise SlurpIntentHypothesisError(
            "bounded hypothesis response must contain "
            f"one through {raw_limit} candidates"
        )
    policy_sha256 = (
        BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256
        if projection_policy == BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        else CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_SHA256
    )
    return _project_validated_rows(
        content, rows=rows, sample_id=sample_id, legal=legal,
        policy_id=projection_policy,
        policy_sha256=policy_sha256,
        max_candidates=max_candidates,
    )


def _project_validated_rows(
    content: str, *, rows: list[object], sample_id: str,
    legal: frozenset[str], policy_id: str, policy_sha256: str,
    max_candidates: int = 3,
) -> SlurpIntentHypothesisProjection:
    validated_rows: list[dict[str, object]] = []
    for row in rows:
        single = json.dumps(
            {"candidates": [row]},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        canonical = canonicalize_slurp_intent_hypothesis_response(
            single,
            sample_id=sample_id,
            legal_intent_ids=legal,
            max_candidates=1,
        )
        validated = json.loads(canonical)["candidates"][0]
        validated_rows.append(dict(validated))

    retained: list[dict[str, object]] = []
    first_by_intent: dict[str, tuple[int, int, str]] = {}
    provenance: list[SlurpIntentHypothesisProjectionPosition] = []
    for raw_position, row in enumerate(validated_rows, start=1):
        intent_id = str(row["intent_id"])
        candidate_sha = _canonical_candidate_sha256(row)
        first = first_by_intent.get(intent_id)
        if first is None:
            projected_position = len(retained) + 1
            retained.append(row)
            first = (raw_position, projected_position, candidate_sha)
            first_by_intent[intent_id] = first
        provenance.append(
            SlurpIntentHypothesisProjectionPosition(
                raw_position=raw_position,
                intent_id=intent_id,
                candidate_sha256=candidate_sha,
                first_raw_position=first[0],
                projected_position=first[1],
                retained_sha256=first[2],
            )
        )

    projected_compact = json.dumps(
        {"candidates": retained},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    projected = canonicalize_slurp_intent_hypothesis_response(
        projected_compact,
        sample_id=sample_id,
        legal_intent_ids=legal,
        max_candidates=max_candidates,
    )
    return SlurpIntentHypothesisProjection(
        content=projected,
        original_text_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        projected_content_sha256=hashlib.sha256(
            projected.encode("utf-8")
        ).hexdigest(),
        projection_policy_id=policy_id,
        projection_policy_sha256=policy_sha256,
        raw_positions=tuple(provenance),
    )


def parse_slurp_intent_hypothesis_state(
    artifact: AgentStateArtifact,
    *,
    expected_sample_id: str,
    legal_intent_ids: Iterable[str],
    max_candidates: int,
    compact_source_phase: str | None = None,
    projection_policy: str | None = None,
    raw_max_candidates: int | None = None,
) -> SlurpIntentHypothesisState:
    """Consume raw state without changing its sealed bytes or source hash.

    The default requires the canonical document, including its sample identity.
    Compact native responses require an explicit source phase and the shared
    sealer's phase/sample identity. This local check complements, rather than
    replaces, the runner's per-sample custody or an external manifest verifier.
    """

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
    if projection_policy is not None and (
        projection_policy not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS
        or compact_source_phase is None
        or (
            max_candidates > 3
            and projection_policy
            != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        )
    ):
        raise SlurpIntentHypothesisError(
            "projection_policy requires the bounded first-occurrence policy and compact source"
        )
    if raw_max_candidates is not None and projection_policy is None:
        raise SlurpIntentHypothesisError(
            "an explicit raw candidate bound requires bounded projection"
        )
    projection = None
    content = artifact.content
    legal = _legal_ids(legal_intent_ids)
    if compact_source_phase is not None:
        if (
            not isinstance(compact_source_phase, str)
            or not compact_source_phase
            or ":" in compact_source_phase
            or any(character.isspace() for character in compact_source_phase)
        ):
            raise SlurpIntentHypothesisError(
                "compact_source_phase must be one non-empty phase name"
            )
        sample_id = _text(expected_sample_id, field="expected_sample_id")
        sealed_id = f"{compact_source_phase}:{sample_id}"
        if artifact.state_kind != f"phase:{compact_source_phase}" or not (
            artifact.state_id == sealed_id
            or artifact.state_id.endswith(f":{sealed_id}")
        ):
            raise SlurpIntentHypothesisError(
                "compact hypothesis state must bind the configured phase and sample_id"
            )
        if projection_policy is not None:
            projection = project_bounded_slurp_intent_hypotheses(
                content,
                sample_id=sample_id,
                legal_intent_ids=legal,
                max_candidates=max_candidates,
                projection_policy=projection_policy,
                raw_max_candidates=raw_max_candidates,
            )
            content = projection.content
        else:
            content = canonicalize_slurp_intent_hypothesis_response(
                content,
                sample_id=sample_id,
                legal_intent_ids=legal,
                max_candidates=max_candidates,
            )
    state = parse_slurp_intent_hypothesis_content(
        content,
        expected_sample_id=expected_sample_id,
        legal_intent_ids=legal,
        max_candidates=max_candidates,
    )
    return replace(state, projection=projection) if projection is not None else state


@dataclass(frozen=True)
class SlurpIntentHypothesisStateFill:
    """Render validated alternatives as a deterministic English state suffix."""

    legal_intent_ids: frozenset[str]
    max_candidates: int
    compact_source_phase: str | None

    def __init__(
        self, *, legal_intent_ids: Iterable[str], max_candidates: int,
        compact_source_phase: str | None = None,
    ):
        object.__setattr__(self, "legal_intent_ids", _legal_ids(legal_intent_ids))
        object.__setattr__(self, "max_candidates", max_candidates)
        object.__setattr__(self, "compact_source_phase", compact_source_phase)
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
            compact_source_phase=self.compact_source_phase,
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
