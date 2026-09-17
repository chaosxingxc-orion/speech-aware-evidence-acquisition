"""Pure typed role-context compilation over source-bound episode state."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from jsonschema import Draft202012Validator, SchemaError, ValidationError

from ..reproduction.slurp_scoring import parse_slu_response
from .knowledge import AgentStateArtifact, RailsError
from .native_tool_authority import validate_native_call_rejection
from .review_findings import ReviewFindingsError, parse_review_findings
from .slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS,
    CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID,
    DEFAULT_FALLBACK_DISTINCTION,
    FALLBACK_CANDIDATE_SOURCE,
    MODEL_CANDIDATE_SOURCE,
    SlurpIntentHypothesisError,
    project_bounded_slurp_intent_hypotheses,
    validate_fallback_candidate_ids,
    validate_fallback_distinction,
)

ROLE_CONTEXT_POLICY_ID = "typed-slurp-role-context-v1"
ROLE_CONTEXT_STATE_SCHEMA = "saea-typed-role-context-state-v1"
ROLE_CONTEXT_RECEIPT_SCHEMA = "saea-role-context-compilation-v1"
_ROLE_KINDS = ("perception", "solver", "reviewer", "planner")


class RoleContextError(ValueError):
    """A role view cannot be compiled without weakening source custody."""


@dataclass(frozen=True)
class RoleContextCompilation:
    """The exact selected state and its JSON-serializable audit receipt."""

    states: tuple[AgentStateArtifact, ...]
    receipt: Mapping[str, object]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise RoleContextError("role context values must be finite JSON") from error


def validate_role_context_draft_schema(document: Mapping[str, object]) -> Draft202012Validator:
    """Validate one closed, self-contained draft contract without external resolution."""
    if not isinstance(document, Mapping):
        raise RoleContextError("draft_response_schema must be a mapping")
    schema = json.loads(_canonical_json(dict(document)))
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as error:
        raise RoleContextError("draft_response_schema is invalid") from error

    def references(value):
        if isinstance(value, Mapping):
            return any(key in {"$ref", "$dynamicRef", "$recursiveRef"} or references(item)
                       for key, item in value.items())
        return isinstance(value, list) and any(references(item) for item in value)

    if references(schema):
        raise RoleContextError("role context schema must be self-contained without references")
    # Require a closed structural contract; missing entities must not become [].
    try:
        props = schema["properties"]
        entity = props["entities"]["items"]
        valid = (
            schema["type"] == "object" and schema["additionalProperties"] is False
            and set(schema["required"]) == {"scenario", "action", "entities"}
            and set(props) == {"scenario", "action", "entities"}
            and props["scenario"]["type"] == props["action"]["type"] == "string"
            and props["entities"]["type"] == "array" and entity["type"] == "object"
            and entity["additionalProperties"] is False
            and set(entity["required"]) == {"type", "filler"}
            and set(entity["properties"]) == {"type", "filler"}
            and entity["properties"]["type"]["type"] == "string"
            and entity["properties"]["filler"]["type"] == "string"
        )
    except (KeyError, TypeError):
        valid = False
    if not valid:
        raise RoleContextError("role context draft schema requires closed intent and entity fields")
    return Draft202012Validator(schema)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RoleContextError("role context JSON repeats a key")
        result[key] = value
    return result


def _reject_constant(_value):
    raise RoleContextError("role context JSON contains a nonfinite constant")


def _strict_json(text: str) -> object:
    try:
        return json.loads(
            text, object_pairs_hook=_unique_object, parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as error:
        raise RoleContextError("role context source is not strict JSON") from error


def _texts(value: object, *, field: str, allow_empty: bool = False) -> tuple[str, ...]:
    if not isinstance(value, tuple):
        raise RoleContextError(f"{field} must be a tuple")
    if any(not isinstance(item, str) or (not allow_empty and not item.strip()) for item in value):
        raise RoleContextError(f"{field} must contain non-empty strings")
    if len(value) != len(set(value)):
        raise RoleContextError(f"{field} must contain unique strings")
    return value


def _source_binding(source: AgentStateArtifact, position: int) -> dict[str, object]:
    return {
        "state_id": source.state_id,
        "state_kind": source.state_kind,
        "artifact_sha256": source.content_hash(),
        "content_sha256": _sha256_text(source.content),
        "source_response_sha256": source.source_response_sha256,
        "source_query_state_sha256": source.source_query_state_sha256,
        "producer_policy_id": source.producer_policy_id,
        "source_position": position,
    }


def _derived_state(
    *, source: AgentStateArtifact, source_position: int, role_kind: str,
    semantic_class: str, parse_status: str, declaration_status: str,
    view: Mapping[str, object], sample_id: str,
) -> AgentStateArtifact:
    content = _canonical_json({
        "schema": ROLE_CONTEXT_STATE_SCHEMA,
        "policy_id": ROLE_CONTEXT_POLICY_ID,
        "role_kind": role_kind,
        "semantic_class": semantic_class,
        "source": {"state_id": source.state_id, "state_kind": source.state_kind},
        "parse_status": parse_status,
        "declaration_status": declaration_status,
        "view": dict(view),
    })
    content_sha256 = _sha256_text(content)
    return AgentStateArtifact(
        state_id=(
            f"role-context:{role_kind}:{semantic_class}:{sample_id}:{content_sha256}"
        ),
        state_kind=f"role-context:{semantic_class}",
        content=content,
        source_query_state_sha256=source.source_query_state_sha256,
        source_response_sha256=source.source_response_sha256,
        producer_policy_id=ROLE_CONTEXT_POLICY_ID,
        cited_value_ids=source.cited_value_ids,
    ).validate()


def _phase_ids(value: Mapping[str, str]) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != set(_ROLE_KINDS):
        raise RoleContextError("phase_ids must map exactly the four native role kinds")
    result = {}
    for role in _ROLE_KINDS:
        phase_id = value[role]
        if (
            not isinstance(phase_id, str) or not phase_id or ":" in phase_id
            or any(character.isspace() for character in phase_id)
        ):
            raise RoleContextError("phase_ids must contain plain non-empty phase IDs")
        result[role] = phase_id
    if len(set(result.values())) != len(result):
        raise RoleContextError("phase_ids must be unique")
    return result


def _draft_view(
    source: AgentStateArtifact, *, validator: Draft202012Validator, planner: bool,
) -> tuple[str, str, Mapping[str, object]]:
    parsed_view = None
    try:
        document = _strict_json(source.content)
        if not isinstance(document, Mapping) or "entities" not in document:
            raise RoleContextError("a SLURP draft must explicitly declare entities")
        validator.validate(document)
        scenario, action, entities, parsed = parse_slu_response(source.content)
        if not parsed:
            raise RoleContextError("a schema-valid SLURP draft must parse")
        parsed_view = {
            "scenario": scenario,
            "action": action,
            "entities": [
                {"type": entity.type, "filler": entity.filler} for entity in entities
            ],
        }
    except (RoleContextError, ValidationError):
        parse_status = "malformed"
    else:
        parse_status = "parsed"
    if planner:
        view = {"source_state_id": source.state_id, "parse_status": parse_status}
    elif parsed_view is not None:
        view = {"parsed": parsed_view}
    else:
        view = {"raw_text": source.content}
    return parse_status, "unverified-current-draft", view


def _citation_availability(
    evidence_ids: Iterable[str], visible_evidence_ids: set[str],
) -> list[dict[str, object]]:
    return [
        {"evidence_id": evidence_id, "available": evidence_id in visible_evidence_ids}
        for evidence_id in dict.fromkeys(evidence_ids)
    ]


def _review_view(
    source: AgentStateArtifact, *, visible_evidence_ids: set[str], draft_state_id: str,
) -> tuple[str, str, Mapping[str, object]]:
    try:
        report = parse_review_findings(source.content)
    except ReviewFindingsError:
        return "unavailable", "unavailable", {"reason": "malformed-review-findings"}
    evidence_ids = list(dict.fromkeys(
        evidence_id
        for finding in report["findings"]
        for evidence_id in finding["evidence_ids"]
    ))
    return "parsed", "unverified-review-declaration", {
        "reviewed_draft_state_id": draft_state_id,
        "report": report,
        "citation_availability": _citation_availability(
            evidence_ids, visible_evidence_ids,
        ),
    }


def _candidate_view(
    source: AgentStateArtifact, *, sample_id: str, legal_intent_ids: tuple[str, ...],
    max_candidates: int, projection_policy: str, visible_evidence_ids: set[str],
    fallback_candidates: tuple[str, ...] = (),
    fallback_distinction: str = DEFAULT_FALLBACK_DISTINCTION,
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    if _sha256_text(source.content) != source.source_response_sha256:
        raise RoleContextError("candidate source content differs from its response hash")
    try:
        projection = project_bounded_slurp_intent_hypotheses(
            source.content,
            sample_id=sample_id,
            legal_intent_ids=legal_intent_ids,
            max_candidates=max_candidates,
            projection_policy=projection_policy,
        )
    except SlurpIntentHypothesisError as error:
        raise RoleContextError(str(error)) from error
    document = json.loads(projection.content)
    # FIX-1 standing fallback: applied ONCE here, after the projection, to
    # the RENDERED view only -- never to ``document``/``projection``, whose
    # hashes stay the sealed Perception response's own audit trail. With no
    # fallback configured, ``candidates`` is ``document["candidates"]``
    # itself, unchanged, so an unconfigured role view is byte-identical to
    # the view this function rendered before the option existed.
    try:
        fallback_ids = validate_fallback_candidate_ids(
            fallback_candidates, legal_intent_ids=legal_intent_ids,
        )
    except SlurpIntentHypothesisError as error:
        raise RoleContextError(str(error)) from error
    if not fallback_ids:
        candidates = document["candidates"]
    else:
        distinction = validate_fallback_distinction(fallback_distinction)
        candidates = [
            dict(candidate, source=MODEL_CANDIDATE_SOURCE)
            for candidate in document["candidates"]
        ]
        present = {candidate["intent_id"] for candidate in candidates}
        for fallback_id in fallback_ids:
            if fallback_id in present:
                continue
            candidates.append({
                "intent_id": fallback_id,
                "distinction": distinction,
                "evidence_refs": [],
                "unresolved_fields": [],
                "source": FALLBACK_CANDIDATE_SOURCE,
            })
    view = {
        "sample_id": sample_id,
        "candidates": candidates,
        "evidence_ref_availability": [
            {
                "intent_id": candidate["intent_id"],
                "evidence_refs": _citation_availability(
                    candidate["evidence_refs"], visible_evidence_ids,
                ),
            }
            for candidate in candidates
        ],
    }
    audit = {
        "original_text_sha256": projection.original_text_sha256,
        "projected_content_sha256": projection.projected_content_sha256,
        "projection_policy_id": projection.projection_policy_id,
        "projection_policy_sha256": projection.projection_policy_sha256,
        "raw_positions": [
            {
                "raw_position": item.raw_position,
                "intent_id": item.intent_id,
                "candidate_sha256": item.candidate_sha256,
                "first_raw_position": item.first_raw_position,
                "projected_position": item.projected_position,
                "retained_sha256": item.retained_sha256,
            }
            for item in projection.raw_positions
        ],
    }
    return view, audit


def _assert_raw_phase_source(
    source: AgentStateArtifact, *, semantic_class: str, phase_id: str, sample_id: str,
) -> None:
    sealed_id = f"{phase_id}:{sample_id}"
    if (
        source.state_kind != f"phase:{phase_id}"
        or not (
            source.state_id == sealed_id or source.state_id.endswith(f":{sealed_id}")
        )
    ):
        raise RoleContextError(f"{semantic_class} source is bound to another sample or phase")
    if _sha256_text(source.content) != source.source_response_sha256:
        raise RoleContextError(
            f"{semantic_class} source content differs from its response hash"
        )


@dataclass(frozen=True)
class _NativePair:
    source_position: int
    result_positions: tuple[int, ...]
    source: AgentStateArtifact
    results: tuple[AgentStateArtifact, ...]
    evidence_ids: tuple[str, ...]
    feedback_kind: str | None


def _known_tool_sources(states: tuple[AgentStateArtifact, ...]) -> set[str]:
    sources = set()
    for state in states:
        if state.state_kind != "tool-result":
            continue
        try:
            document = _strict_json(state.content)
        except RoleContextError:
            continue
        if isinstance(document, Mapping) and isinstance(
            document.get("native_source_state_id"), str
        ):
            sources.add(document["native_source_state_id"])
    return sources


def _native_pairs(
    *, states: tuple[AgentStateArtifact, ...], local_ids: tuple[str, ...],
    phase_ids: Mapping[str, str], role_kind: str, sample_id: str,
    latest_solver_position: int | None,
) -> tuple[_NativePair, ...]:
    positions = {state.state_id: index for index, state in enumerate(states)}
    pairs = []
    seen_sources = set()
    cursor = 0
    while cursor < len(local_ids):
        result_id = local_ids[cursor]
        result_position = positions.get(result_id)
        if result_position is None:
            raise RoleContextError("local native tool result is missing")
        result = states[result_position]
        if result.state_kind != "tool-result":
            raise RoleContextError("local native history ID is not a tool result")
        document = _strict_json(result.content)
        if not isinstance(document, Mapping) or document.get("schema") not in {
            "saea-phase-tool-result-v1",
            "saea-phase-tool-result-v2",
            "saea-phase-tool-rejection-v1",
        }:
            raise RoleContextError("local native tool result envelope is invalid")
        source_id = document.get("native_source_state_id")
        source_position = positions.get(source_id) if isinstance(source_id, str) else None
        if source_position is None or source_id in seen_sources:
            raise RoleContextError("local native tool source is missing or repeated")
        source = states[source_position]
        expected_kind = f"phase:{document.get('phase')}"
        if (
            source.state_kind != expected_kind
            or document.get("phase") not in phase_ids.values()
            or document.get("sample_id") != sample_id
            or _sha256_text(source.content) != source.source_response_sha256
        ):
            raise RoleContextError("local native call/result source binding differs")
        if role_kind == "reviewer":
            if (
                source.state_kind != f"phase:{phase_ids['reviewer']}"
                or latest_solver_position is None
                or source_position <= latest_solver_position
            ):
                raise RoleContextError("Reviewer local tool chain is foreign or stale")
        elif latest_solver_position is None or source_position <= latest_solver_position:
            raise RoleContextError("native tool pair does not follow the latest Solver")

        def validate_result_binding(
            candidate: AgentStateArtifact, candidate_document: Mapping[str, object],
        ) -> None:
            if (
                candidate_document.get("native_source_state_id") != source_id
                or candidate_document.get("query_state_sha256")
                != source.source_query_state_sha256
                or candidate_document.get("source_response_sha256")
                != source.source_response_sha256
                or candidate.source_query_state_sha256
                != source.source_query_state_sha256
                or candidate.source_response_sha256 != source.source_response_sha256
            ):
                raise RoleContextError("local native call/result source binding differs")

        if document.get("schema") == "saea-phase-tool-rejection-v1":
            try:
                authority, _selected_call = validate_native_call_rejection(document)
                calls = authority["original_assistant_message"]["tool_calls"]
                original_ids = [call["id"] for call in calls]
            except (RailsError, KeyError, TypeError) as error:
                raise RoleContextError("local rejected native batch is invalid") from error
            batch_ids = local_ids[cursor : cursor + len(original_ids)]
            if len(batch_ids) != len(original_ids):
                raise RoleContextError("local rejected native batch is incomplete")
            batch_positions = []
            batch_results = []
            for offset, (batch_id, original_id) in enumerate(
                zip(batch_ids, original_ids, strict=True), start=1
            ):
                batch_position = positions.get(batch_id)
                if batch_position != source_position + offset:
                    raise RoleContextError(
                        "local rejected native batch is omitted, reordered or interleaved"
                    )
                batch_result = states[batch_position]
                if batch_result.state_kind != "tool-result":
                    raise RoleContextError(
                        "local rejected native batch contains a non-result"
                    )
                batch_document = _strict_json(batch_result.content)
                try:
                    batch_authority, batch_call = validate_native_call_rejection(
                        batch_document
                    )
                except (RailsError, TypeError, ValueError) as error:
                    raise RoleContextError(
                        "local rejected native batch is invalid"
                    ) from error
                if (
                    batch_authority != authority
                    or batch_call.get("id") != original_id
                ):
                    raise RoleContextError(
                        "local rejected native batch mixes source or call identities"
                    )
                validate_result_binding(batch_result, batch_document)
                batch_positions.append(batch_position)
                batch_results.append(batch_result)
            seen_sources.add(source_id)
            pairs.append(_NativePair(
                source_position=source_position,
                result_positions=tuple(batch_positions),
                source=source,
                results=tuple(batch_results),
                evidence_ids=(),
                feedback_kind="rejected-action-feedback",
            ))
            cursor += len(original_ids)
            continue

        if result_position != source_position + 1:
            raise RoleContextError("local native call/result source binding differs")
        validate_result_binding(result, document)
        blocks = document.get("native_result_content")
        if not isinstance(blocks, list) or any(
            not isinstance(block, Mapping) for block in blocks
        ):
            raise RoleContextError("native tool evidence blocks are malformed")
        evidence_ids = tuple(
            block["evidence_id"]
            for block in blocks
            if block.get("type") == "text"
            and isinstance(block.get("evidence_id"), str)
            and block["evidence_id"].strip()
        )
        if len(evidence_ids) != len(set(evidence_ids)):
            raise RoleContextError("native tool evidence IDs are duplicated")
        seen_sources.add(source_id)
        pairs.append(_NativePair(
            source_position=source_position,
            result_positions=(result_position,),
            source=source,
            results=(result,),
            evidence_ids=evidence_ids,
            feedback_kind=None,
        ))
        cursor += 1
    result_positions = [
        position for pair in pairs for position in pair.result_positions
    ]
    if result_positions != sorted(result_positions):
        raise RoleContextError("local native tool results are reordered")
    return tuple(pairs)

class SlurpRoleContextCompiler:
    """Compile one bounded, typed SLURP view without retrieval or judgment."""

    def __init__(
        self, *, legal_intent_ids: Iterable[str], max_candidates: int,
        projection_policy: str,
        fallback_candidates: Iterable[str] = (),
        fallback_distinction: str = DEFAULT_FALLBACK_DISTINCTION,
    ) -> None:
        if isinstance(legal_intent_ids, (str, bytes)):
            raise RoleContextError("legal_intent_ids must be an iterable of IDs")
        legal = tuple(legal_intent_ids)
        if (
            not legal or any(not isinstance(item, str) or not item.strip() for item in legal)
            or len(legal) != len(set(legal))
        ):
            raise RoleContextError("legal_intent_ids must be non-empty and unique")
        if (
            isinstance(max_candidates, bool) or not isinstance(max_candidates, int)
            or not 1 <= max_candidates <= len(legal)
        ):
            raise RoleContextError("max_candidates must fit the legal intent inventory")
        if projection_policy not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS:
            raise RoleContextError("projection_policy is unsupported")
        if (
            max_candidates > 3
            and projection_policy
            != CONFIGURABLE_BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_ID
        ):
            raise RoleContextError("candidate bounds above three require the configurable policy")
        try:
            fallback_ids = validate_fallback_candidate_ids(
                fallback_candidates, legal_intent_ids=legal,
            )
            fallback_text = (
                validate_fallback_distinction(fallback_distinction)
                if fallback_ids
                else fallback_distinction
            )
        except SlurpIntentHypothesisError as error:
            raise RoleContextError(str(error)) from error
        self.legal_intent_ids = legal
        self.max_candidates = max_candidates
        self.projection_policy = projection_policy
        self.fallback_candidates = fallback_ids
        self.fallback_distinction = fallback_text

    def compile(
        self, *, role_kind: str, phase_ids: Mapping[str, str], sample_id: str,
        states: tuple[AgentStateArtifact, ...], local_tool_result_ids: tuple[str, ...],
        available_evidence_ids: tuple[str, ...], draft_response_schema: Mapping[str, object],
    ) -> RoleContextCompilation:
        """Return a role view and JSON receipt without changing source artifacts."""
        if role_kind not in _ROLE_KINDS:
            raise RoleContextError("role_kind is unsupported")
        phases = _phase_ids(phase_ids)
        if not isinstance(sample_id, str) or not sample_id.strip():
            raise RoleContextError("sample_id must be a non-empty string")
        if not isinstance(states, tuple):
            raise RoleContextError("states must be an ordered tuple")
        local_ids = _texts(local_tool_result_ids, field="local_tool_result_ids")
        base_evidence_ids = _texts(
            available_evidence_ids, field="available_evidence_ids",
        )
        validator = validate_role_context_draft_schema(draft_response_schema)

        state_ids = []
        for state in states:
            if not isinstance(state, AgentStateArtifact):
                raise RoleContextError("states must contain AgentStateArtifact values")
            try:
                state.validate()
            except RailsError as error:
                raise RoleContextError("role context contains an invalid artifact") from error
            state_ids.append(state.state_id)
        if len(state_ids) != len(set(state_ids)):
            raise RoleContextError("role context contains duplicate state IDs")
        if any(result_id not in state_ids for result_id in local_ids):
            raise RoleContextError("local native tool result is missing")
        local_positions = [state_ids.index(result_id) for result_id in local_ids]
        if local_positions != sorted(local_positions):
            raise RoleContextError("local native tool results are reordered")

        known_tool_sources = _known_tool_sources(states)
        phase_positions = {
            role: [
                index for index, state in enumerate(states)
                if state.state_kind == f"phase:{phase_id}"
                and state.state_id not in known_tool_sources
            ]
            for role, phase_id in phases.items()
        }
        latest_solver_position = (
            phase_positions["solver"][-1] if phase_positions["solver"] else None
        )
        selected_tool_ids = list(local_ids)
        if role_kind != "reviewer" and latest_solver_position is not None:
            relevant = []
            for position, state in enumerate(states):
                if position <= latest_solver_position or state.state_kind != "tool-result":
                    continue
                try:
                    document = _strict_json(state.content)
                except RoleContextError:
                    continue
                if isinstance(document, Mapping) and isinstance(
                    document.get("native_source_state_id"), str
                ):
                    relevant.append(state.state_id)
            selected_tool_ids = sorted(
                set((*relevant, *local_ids)), key=state_ids.index,
            )
        pairs = _native_pairs(
            states=states, local_ids=tuple(selected_tool_ids), phase_ids=phases,
            role_kind=role_kind, sample_id=sample_id,
            latest_solver_position=latest_solver_position,
        )
        tool_evidence_ids = tuple(
            evidence_id for pair in pairs for evidence_id in pair.evidence_ids
        )
        visible_evidence_ids = tuple(dict.fromkeys((*base_evidence_ids, *tool_evidence_ids)))
        visible_evidence_set = set(visible_evidence_ids)

        selected: dict[int, tuple[AgentStateArtifact, str, str | None]] = {}
        derived_audits: dict[int, Mapping[str, object]] = {}
        tool_feedback_by_position: dict[int, Mapping[str, object]] = {}
        represented_source_ids = set()

        def retain_derived(
            position: int, semantic_class: str, parse_status: str,
            declaration_status: str, view: Mapping[str, object],
            audit: Mapping[str, object] | None = None,
        ) -> None:
            source = states[position]
            derived = _derived_state(
                source=source, source_position=position, role_kind=role_kind,
                semantic_class=semantic_class, parse_status=parse_status,
                declaration_status=declaration_status, view=view, sample_id=sample_id,
            )
            selected[position] = (derived, "derived", source.state_id)
            if audit is not None:
                derived_audits[position] = audit
            represented_source_ids.add(source.state_id)

        if role_kind in {"solver", "reviewer"} and phase_positions["perception"]:
            position = phase_positions["perception"][-1]
            _assert_raw_phase_source(
                states[position], semantic_class="candidate hypothesis",
                phase_id=phases["perception"], sample_id=sample_id,
            )
            candidate_view, candidate_audit = _candidate_view(
                states[position], sample_id=sample_id,
                legal_intent_ids=self.legal_intent_ids,
                max_candidates=self.max_candidates,
                projection_policy=self.projection_policy,
                visible_evidence_ids=visible_evidence_set,
                fallback_candidates=self.fallback_candidates,
                fallback_distinction=self.fallback_distinction,
            )
            retain_derived(
                position, "candidate-hypothesis", "parsed",
                "unverified-model-hypotheses",
                candidate_view, candidate_audit,
            )

        if latest_solver_position is not None and role_kind in {"solver", "reviewer", "planner"}:
            _assert_raw_phase_source(
                states[latest_solver_position], semantic_class="current draft",
                phase_id=phases["solver"], sample_id=sample_id,
            )
            parse_status, declaration_status, view = _draft_view(
                states[latest_solver_position], validator=validator,
                planner=role_kind == "planner",
            )
            retain_derived(
                latest_solver_position, "current-draft", parse_status,
                declaration_status, view,
            )

        review_positions = [
            position for position in phase_positions["reviewer"]
            if latest_solver_position is not None and position > latest_solver_position
        ]
        if role_kind in {"solver", "planner", "perception"} and review_positions:
            position = review_positions[-1]
            _assert_raw_phase_source(
                states[position], semantic_class="review finding",
                phase_id=phases["reviewer"], sample_id=sample_id,
            )
            parse_status, declaration_status, view = _review_view(
                states[position], visible_evidence_ids=visible_evidence_set,
                draft_state_id=states[latest_solver_position].state_id,
            )
            retain_derived(
                position, "review-finding", parse_status, declaration_status, view,
            )

        for pair in pairs:
            selected[pair.source_position] = (
                pair.source, "verbatim", pair.source.state_id,
            )
            represented_source_ids.add(pair.source.state_id)
            for result_position, result in zip(
                pair.result_positions, pair.results, strict=True,
            ):
                selected[result_position] = (result, "verbatim", result.state_id)
                represented_source_ids.add(result.state_id)
                if pair.feedback_kind is not None:
                    tool_feedback_by_position[result_position] = {
                        "kind": pair.feedback_kind,
                        "evidence_ids": [],
                    }

        ordered = sorted(selected.items())
        output_states = tuple(item[1][0] for item in ordered)
        retained = []
        for position, (state, disposition, source_state_id) in ordered:
            source = states[position]
            row = {
                "state_id": state.state_id,
                "state_kind": state.state_kind,
                "source_state_id": source_state_id,
                "source_position": position,
                "disposition": disposition,
                "artifact_sha256": state.content_hash(),
                "content_sha256": _sha256_text(state.content),
                "source": _source_binding(source, position),
            }
            if position in derived_audits:
                row["projection"] = dict(derived_audits[position])
            if position in tool_feedback_by_position:
                row["native_tool_feedback"] = dict(
                    tool_feedback_by_position[position]
                )
            retained.append(row)

        selected_candidate = (
            phase_positions["perception"][-1]
            if role_kind in {"solver", "reviewer"} and phase_positions["perception"]
            else None
        )
        selected_review = (
            review_positions[-1]
            if role_kind in {"solver", "planner", "perception"} and review_positions
            else None
        )
        exact_ids = {state.state_id for state in output_states if state in states}
        excluded = []
        for position, state in enumerate(states):
            if state.state_id in represented_source_ids or state.state_id in exact_ids:
                continue
            if role_kind == "perception" and latest_solver_position is None:
                reason = "first-perception-has-no-prior-role-view"
            elif state.state_id in known_tool_sources or state.state_kind == "tool-result":
                reason = "unselected-native-tool-history"
            elif position in phase_positions["perception"]:
                reason = (
                    "stale-perception" if selected_candidate is not None
                    else "role-does-not-receive-candidate-prose"
                )
            elif position in phase_positions["solver"]:
                reason = (
                    "stale-solver" if latest_solver_position != position
                    else "role-does-not-receive-draft"
                )
            elif position in phase_positions["reviewer"]:
                if role_kind == "reviewer":
                    reason = "role-does-not-inherit-review-opinion"
                else:
                    reason = "stale-review" if selected_review is not None else "review-not-current"
            else:
                reason = "not-selected-by-role-policy"
            excluded.append({
                "state_id": state.state_id,
                "state_kind": state.state_kind,
                "source_position": position,
                "artifact_sha256": state.content_hash(),
                "content_sha256": _sha256_text(state.content),
                "source_response_sha256": state.source_response_sha256,
                "source_query_state_sha256": state.source_query_state_sha256,
                "producer_policy_id": state.producer_policy_id,
                "reason": reason,
            })

        receipt = {
            "schema": ROLE_CONTEXT_RECEIPT_SCHEMA,
            "policy_id": ROLE_CONTEXT_POLICY_ID,
            "role_kind": role_kind,
            "sample_id": sample_id,
            "projection_policy": self.projection_policy,
            "phase_ids": phases,
            "available_evidence_ids": list(visible_evidence_ids),
            "retained": retained,
            "excluded": excluded,
            "output_state_ids": [state.state_id for state in output_states],
        }
        receipt["receipt_sha256"] = _sha256_text(_canonical_json(receipt))
        return RoleContextCompilation(states=output_states, receipt=receipt)


__all__ = [
    "ROLE_CONTEXT_POLICY_ID",
    "ROLE_CONTEXT_RECEIPT_SCHEMA",
    "ROLE_CONTEXT_STATE_SCHEMA",
    "RoleContextCompilation",
    "RoleContextError",
    "SlurpRoleContextCompiler",
    "validate_role_context_draft_schema",
]
