"""Pure source-bound, candidate-scoped views of released SLURP slot cards."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from jsonschema import ValidationError

from .artifact_results import build_slurp_hypothesis_artifact_validator
from .candidate_semantic_supply import (
    _read_released_authored_source,
    _released_candidate_index,
)
from .errors import RailsError
from .hashing import content_hash
from .knowledge import AgentStateArtifact
from .knowledge_stores import KnowledgeStoreBinding, load_knowledge_store_binding
from .role_context import validate_role_context_draft_schema
from .semantic_knowledge_build import _slot
from .slurp_intent_hypotheses import (
    BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS,
    SlurpIntentHypothesisError,
    parse_slurp_intent_hypothesis_state,
)


POLICY_ID = "native-candidate-slot-view-v1"
RECEIPT_SCHEMA = "saea-native-candidate-slot-value-view-v1"
_TARGET_TOOL = "saea-tool-knowledge-target-lookup-v1"
_ROLE_KINDS = ("perception", "solver", "reviewer", "planner")
_PARAM_KEYS = frozenset({"store_id", "consumer_roles"})
_ROW_KEYS = frozenset({
    "slot_id", "intent_bindings", "extraction_cues", "admissible_formats",
    "missing_behavior", "ambiguity_behavior", "limitations", "source_support",
})
_SLU_DRAFT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["scenario", "action", "entities"],
    "properties": {
        "scenario": {"type": "string"}, "action": {"type": "string"},
        "entities": {"type": "array", "items": {
            "type": "object", "additionalProperties": False,
            "required": ["type", "filler"],
            "properties": {
                "type": {"type": "string"}, "filler": {"type": "string"},
            },
        }},
    },
}


class SlotBindingViewError(ValueError):
    """A projection source, runtime scope, or canonical value binding differs."""


def _canonical(value: object) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=True, sort_keys=True, allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as error:
        raise SlotBindingViewError("slot view value is not canonical JSON") from error


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SlotBindingViewError("slot view JSON repeats a key")
        result[key] = value
    return result


def _strict_json(text: object) -> object:
    if not isinstance(text, str) or not text:
        raise SlotBindingViewError("slot view source must be non-empty JSON text")
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                SlotBindingViewError("slot view JSON contains a nonfinite constant")
            ),
        )
    except json.JSONDecodeError as error:
        raise SlotBindingViewError("slot view source is not strict JSON") from error


@dataclass(frozen=True)
class SlotIntentBinding:
    intent_id: str
    semantic_role: str

    def as_json(self) -> dict[str, str]:
        return {"intent_id": self.intent_id, "semantic_role": self.semantic_role}


@dataclass(frozen=True)
class SlotBindingRow:
    slot_id: str
    intent_bindings: tuple[SlotIntentBinding, ...]
    extraction_cues: tuple[str, ...]
    admissible_formats: tuple[str, ...]
    missing_behavior: str
    ambiguity_behavior: str
    limitations: tuple[str, ...]
    source_support_json: str
    canonical_json: str

    def document(self) -> dict[str, object]:
        return json.loads(self.canonical_json)


@dataclass(frozen=True)
class SlotBindingViewContext:
    policy_id: str
    context_sha256: str
    value_ids: tuple[str, ...]
    rows: tuple[SlotBindingRow, ...]
    rows_by_value_id: Mapping[str, SlotBindingRow]
    legal_candidate_ids: tuple[str, ...]
    consumer_roles: tuple[str, ...]
    role_phases: tuple[tuple[str, str], ...]
    candidate_source_phase: str
    max_candidates: int
    projection_policy: str
    store_id: str
    snapshot_pin: tuple[tuple[str, str], ...]
    release_pin: tuple[tuple[str, str], ...]
    source_pin: tuple[tuple[str, str], ...]
    knowledge_binding: KnowledgeStoreBinding = field(repr=False, compare=False)


def _context_document(context: SlotBindingViewContext) -> dict[str, object]:
    return {
        "policy_id": context.policy_id,
        "value_ids": list(context.value_ids),
        "rows": [json.loads(row.canonical_json) for row in context.rows],
        "legal_candidate_ids": list(context.legal_candidate_ids),
        "consumer_roles": list(context.consumer_roles),
        "role_phases": [list(item) for item in context.role_phases],
        "candidate_source_phase": context.candidate_source_phase,
        "max_candidates": context.max_candidates,
        "projection_policy": context.projection_policy,
        "store_id": context.store_id,
        "snapshot_pin": dict(context.snapshot_pin),
        "release_pin": dict(context.release_pin),
        "source_pin": dict(context.source_pin),
        "composite_snapshot_sha256": context.knowledge_binding.binding_sha256,
    }


def _freeze_row(raw: Mapping[str, object]) -> SlotBindingRow:
    if not isinstance(raw, Mapping) or set(raw) != _ROW_KEYS:
        raise SlotBindingViewError("released slot row has the wrong fields")
    canonical = _canonical(dict(raw))
    document = json.loads(canonical)
    try:
        bindings = tuple(
            SlotIntentBinding(item["intent_id"], item["semantic_role"])
            for item in document["intent_bindings"]
        )
        return SlotBindingRow(
            slot_id=document["slot_id"],
            intent_bindings=bindings,
            extraction_cues=tuple(document["extraction_cues"]),
            admissible_formats=tuple(document["admissible_formats"]),
            missing_behavior=document["missing_behavior"],
            ambiguity_behavior=document["ambiguity_behavior"],
            limitations=tuple(document["limitations"]),
            source_support_json=_canonical(document["source_support"]),
            canonical_json=canonical,
        )
    except (KeyError, TypeError) as error:
        raise SlotBindingViewError("released slot row is malformed") from error


def _roles(values: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    episode = values.get("native_episode")
    raw = episode.get("roles") if isinstance(episode, Mapping) else None
    if not isinstance(raw, Mapping) or set(raw) != set(_ROLE_KINDS):
        raise SlotBindingViewError("native episode must declare the four role kinds")
    result = []
    for kind in _ROLE_KINDS:
        row = raw[kind]
        phase = row.get("phase_id") if isinstance(row, Mapping) else None
        if not isinstance(phase, str) or not phase or ":" in phase or any(c.isspace() for c in phase):
            raise SlotBindingViewError("native role phase IDs must be plain non-empty strings")
        result.append((kind, phase))
    if len({phase for _kind, phase in result}) != len(result):
        raise SlotBindingViewError("native role phase IDs must be distinct")
    return tuple(result)


def bind_slot_view_context(
    values: Mapping[str, object], data_root: Path,
) -> SlotBindingViewContext:
    """Bind the released slot rows and legal Perception inventory once."""
    if not isinstance(values, Mapping):
        raise SlotBindingViewError("slot view values must be a mapping")
    params = values.get("native_evidence_projection_params")
    if not isinstance(params, Mapping) or set(params) != _PARAM_KEYS:
        raise SlotBindingViewError("native evidence projection params have the wrong fields")
    store_id = params["store_id"]
    consumers = params["consumer_roles"]
    if store_id != "slot-contracts":
        raise SlotBindingViewError("slot view store_id must be 'slot-contracts'")
    if (
        not isinstance(consumers, list) or not consumers
        or any(not isinstance(item, str) for item in consumers)
        or len(consumers) != len(set(consumers))
        or not set(consumers) <= set(_ROLE_KINDS)
    ):
        raise SlotBindingViewError("consumer_roles must be distinct native role kinds")
    role_phases = _roles(values)
    phases = dict(role_phases)

    try:
        binding = load_knowledge_store_binding(values, data_root=Path(data_root))
    except (RailsError, ValueError, TypeError) as error:
        raise SlotBindingViewError(str(error)) from error
    if binding is None:
        raise SlotBindingViewError("slot view requires named knowledge stores")
    store = binding.store(store_id)
    if store.store_role != "slot-contracts":
        raise SlotBindingViewError("slot view requires the slot-contracts store role")

    material = values.get("phase_material")
    perception_material = material.get(phases["perception"]) if isinstance(material, Mapping) else None
    fill = perception_material.get("fill_params") if isinstance(perception_material, Mapping) else None
    if not isinstance(fill, Mapping) or perception_material.get("response_format_id") != "slurp-intent-hypotheses-v1":
        raise SlotBindingViewError("Perception must use the pinned SLURP hypothesis catalog")
    try:
        validator = build_slurp_hypothesis_artifact_validator(fill, data_root=Path(data_root))
    except ValueError as error:
        raise SlotBindingViewError(str(error)) from error
    legal = validator.legal_intent_ids

    supplies = store.candidate_supply
    spec = supplies.get(phases["solver"]) if isinstance(supplies, Mapping) else None
    if not isinstance(spec, Mapping):
        raise SlotBindingViewError("slot store must supply the native Solver phase")
    source_phase = spec.get("candidate_state_phase")
    compact_phase = spec.get("compact_source_phase")
    projection = spec.get("projection_policy")
    maximum = spec.get("max_candidates")
    if (
        source_phase != phases["perception"] or compact_phase != phases["perception"]
        or projection not in BOUNDED_FIRST_OCCURRENCE_PROJECTION_POLICY_IDS
        or isinstance(maximum, bool) or not isinstance(maximum, int)
        or not 1 <= maximum <= len(legal)
    ):
        raise SlotBindingViewError("slot candidate supply differs from bounded Perception")
    validate_role_context_draft_schema(_SLU_DRAFT_SCHEMA)
    try:
        _released_candidate_index(store, data_root=Path(data_root), legal_candidate_ids=legal)
        source = _read_released_authored_source(store, Path(data_root))
    except (RailsError, ValueError, TypeError) as error:
        raise SlotBindingViewError(str(error)) from error
    rows = tuple(sorted((_freeze_row(row) for row in source["rows"]), key=lambda row: row.slot_id))
    by_id = MappingProxyType({
        f"{store_id}::slot-contract:{row.slot_id}": row for row in rows
    })
    value_ids = tuple(by_id)
    expected_ids = tuple(sorted(
        value.value_id for value in binding.composite_snapshot.values
        if value.value_id.startswith(store_id + "::")
    ))
    if value_ids != expected_ids:
        raise SlotBindingViewError("released slot rows differ from composite value IDs")
    provisional = SlotBindingViewContext(
        policy_id=POLICY_ID, context_sha256="", value_ids=value_ids, rows=rows,
        rows_by_value_id=by_id, legal_candidate_ids=tuple(legal),
        consumer_roles=tuple(consumers), role_phases=role_phases,
        candidate_source_phase=source_phase, max_candidates=maximum,
        projection_policy=projection, store_id=store_id,
        snapshot_pin=tuple(sorted(store.snapshot_pin.items())),
        release_pin=tuple(sorted(store.release_pin.items())),
        source_pin=tuple(sorted(store.source_pin.items())), knowledge_binding=binding,
    )
    context = SlotBindingViewContext(
        **{**provisional.__dict__, "context_sha256": content_hash(_context_document(provisional))}
    )
    validate_slot_view_context(context)
    return context


def validate_slot_view_context(context: SlotBindingViewContext) -> None:
    if not isinstance(context, SlotBindingViewContext) or context.policy_id != POLICY_ID:
        raise SlotBindingViewError("slot view context type or policy differs")
    if tuple(context.rows_by_value_id) != context.value_ids:
        raise SlotBindingViewError("slot view context value index differs")
    for value_id in context.value_ids:
        row = context.rows_by_value_id[value_id]
        if (
            row not in context.rows
            or value_id != f"{context.store_id}::slot-contract:{row.slot_id}"
        ):
            raise SlotBindingViewError("slot view context row index differs")
    if context.context_sha256 != content_hash(_context_document(context)):
        raise SlotBindingViewError("slot view context hash differs")
    if context.knowledge_binding.composite_snapshot.content_hash() != context.knowledge_binding.binding_sha256:
        raise SlotBindingViewError("slot view composite snapshot differs")
    try:
        store = context.knowledge_binding.store(context.store_id)
    except RailsError as error:
        raise SlotBindingViewError("slot view store binding differs") from error
    if (
        tuple(sorted(store.snapshot_pin.items())) != context.snapshot_pin
        or tuple(sorted(store.release_pin.items())) != context.release_pin
        or tuple(sorted(store.source_pin.items())) != context.source_pin
    ):
        raise SlotBindingViewError("slot view source pins differ")
    values = {value.value_id: value for value in context.knowledge_binding.composite_snapshot.values}
    for value_id, row in context.rows_by_value_id.items():
        _slot_id, _bindings, expected = _slot(row.document())
        value = values.get(value_id)
        if value is None or value.content != expected:
            raise SlotBindingViewError("slot view row differs from canonical knowledge")


def _history_artifacts(payload: Mapping[str, object]) -> tuple[AgentStateArtifact, ...]:
    history = payload.get("history")
    if not isinstance(history, list) or not history:
        raise SlotBindingViewError("native framework history is missing")
    artifacts = []
    for item in history:
        if not isinstance(item, Mapping):
            raise SlotBindingViewError("native framework history item is malformed")
        content = item.get("content")
        if not isinstance(content, str) or item.get("content_sha256") != _sha_text(content):
            raise SlotBindingViewError("native framework state content hash differs")
        if item.get("role") == "control":
            continue
        if item.get("role") != "agent_state":
            raise SlotBindingViewError("native framework history role is invalid")
        try:
            artifact = AgentStateArtifact.from_json(item)
        except (KeyError, RailsError, TypeError, ValueError) as error:
            raise SlotBindingViewError("native framework state artifact is malformed") from error
        artifacts.append(artifact)
    ids = [item.state_id for item in artifacts]
    if len(ids) != len(set(ids)):
        raise SlotBindingViewError("native framework state IDs repeat")
    return tuple(artifacts)


def _tool_scope(
    artifacts: tuple[AgentStateArtifact, ...], context: SlotBindingViewContext,
    sample_id: str,
) -> tuple[set[str], tuple[str, ...], tuple[str, ...]]:
    by_id = {artifact.state_id: artifact for artifact in artifacts}
    source_ids, target_ids, target_states = set(), [], []
    legal = set(context.legal_candidate_ids)
    for artifact in artifacts:
        if artifact.state_kind != "tool-result":
            continue
        document = _strict_json(artifact.content)
        if not isinstance(document, Mapping):
            raise SlotBindingViewError("native tool result document is malformed")
        source_id = document.get("native_source_state_id")
        if isinstance(source_id, str):
            source_ids.add(source_id)
        if document.get("tool_id") != _TARGET_TOOL:
            continue
        result = document.get("result")
        candidates = result.get("candidate_ids") if isinstance(result, Mapping) else None
        selected = result.get("selected_value_ids") if isinstance(result, Mapping) else None
        source = by_id.get(source_id)
        valid = (
            document.get("schema") == "saea-phase-tool-result-v2"
            and document.get("sample_id") == sample_id
            and document.get("snapshot_sha256") == context.knowledge_binding.binding_sha256
            and isinstance(result, Mapping)
            and document.get("result_sha256") == content_hash(dict(result))
            and result.get("store_id") == context.store_id
            and result.get("store_role") == "slot-contracts"
            and result.get("knowledge_view") == "text"
            and isinstance(candidates, list) and candidates
            and len(candidates) == len(set(candidates)) and set(candidates) <= legal
            and isinstance(selected, list)
            and tuple(selected) == artifact.cited_value_ids
            and set(selected) <= set(context.value_ids)
            and source is not None
            and source.source_response_sha256 == artifact.source_response_sha256
            and _sha_text(source.content) == source.source_response_sha256
        )
        if not valid:
            raise SlotBindingViewError("target tool result differs from its source binding")
        target_states.append(artifact.state_id)
        for candidate in candidates:
            if candidate not in target_ids:
                target_ids.append(candidate)
    return source_ids, tuple(target_ids), tuple(target_states)


def _source_fields(prefix: str, artifact: AgentStateArtifact | None) -> dict[str, object]:
    return {
        f"{prefix}_state_id": None if artifact is None else artifact.state_id,
        f"{prefix}_content": None if artifact is None else artifact.content,
        f"{prefix}_content_sha256": None if artifact is None else _sha_text(artifact.content),
        f"{prefix}_source_response_sha256": (
            None if artifact is None else artifact.source_response_sha256
        ),
    }


def _fallback(
    context: SlotBindingViewContext, role: str, reason: str,
    *, perception=None, solver=None, target_states=(),
) -> dict[str, object]:
    return {
        "policy_id": POLICY_ID, "context_sha256": context.context_sha256,
        "eligible": True, "role_kind": role, "candidate_ids": [],
        "fallback_reason": reason,
        "sources": {**_source_fields("perception", perception),
                    **_source_fields("solver", solver),
                    "target_tool_state_ids": list(target_states)},
    }


def scope_for_payload(
    payload: Mapping[str, object], context: SlotBindingViewContext,
) -> dict[str, object]:
    """Derive the current role's ordered candidate union from sealed state."""
    validate_slot_view_context(context)
    if not isinstance(payload, Mapping):
        raise SlotBindingViewError("native payload must be a mapping")
    from ..core.model import FrozenCoreError
    from ..core.model.native_framework_history import validate_native_framework_contact

    try:
        validated = validate_native_framework_contact(payload)
    except FrozenCoreError as error:
        raise SlotBindingViewError("native framework envelope differs") from error
    if validated is None:
        raise SlotBindingViewError("native framework envelope is missing")
    contract = validated[0]
    role_by_phase = {phase: role for role, phase in context.role_phases}
    role = role_by_phase.get(contract["role_id"])
    if role is None:
        raise SlotBindingViewError("native framework role is not bound")
    artifacts = _history_artifacts(payload)
    if role not in context.consumer_roles:
        return {
            "policy_id": POLICY_ID, "context_sha256": context.context_sha256,
            "eligible": False, "role_kind": role, "candidate_ids": [],
            "fallback_reason": "nonconsumer-role",
            "sources": {**_source_fields("perception", None),
                        **_source_fields("solver", None),
                        "target_tool_state_ids": []},
        }
    sample_id = payload.get("sample_id")
    source_ids, target_ids, target_states = _tool_scope(artifacts, context, sample_id)
    phases = dict(context.role_phases)
    perception = [
        item for item in artifacts
        if item.state_kind == f"phase:{phases['perception']}" and item.state_id not in source_ids
    ]
    if not perception:
        return _fallback(context, role, "missing-perception-candidates", target_states=target_states)
    candidate_source = perception[-1]
    try:
        candidate_state = parse_slurp_intent_hypothesis_state(
            candidate_source, expected_sample_id=sample_id,
            legal_intent_ids=context.legal_candidate_ids,
            max_candidates=context.max_candidates,
            compact_source_phase=context.candidate_source_phase,
            projection_policy=context.projection_policy,
        )
    except (SlurpIntentHypothesisError, RailsError, ValueError, TypeError):
        return _fallback(
            context, role, "malformed-perception-candidates",
            perception=candidate_source, target_states=target_states,
        )
    candidates = [item.intent_id for item in candidate_state.candidates]
    solver_states = [
        item for item in artifacts
        if item.state_kind == f"phase:{phases['solver']}" and item.state_id not in source_ids
    ]
    solver = solver_states[-1] if solver_states else None
    if solver is None and role == "reviewer":
        return _fallback(
            context, role, "missing-latest-solver-draft",
            perception=candidate_source, target_states=target_states,
        )
    if solver is not None:
        try:
            document = _strict_json(solver.content)
            validate_role_context_draft_schema(_SLU_DRAFT_SCHEMA).validate(document)
            from ..reproduction.slurp_scoring import parse_slu_response
            scenario, action, _entities, parsed = parse_slu_response(solver.content)
            intent = f"{scenario}_{action}" if parsed else None
            if intent not in set(context.legal_candidate_ids):
                raise SlotBindingViewError("draft intent is outside the legal inventory")
        except (SlotBindingViewError, ValidationError, ValueError, TypeError):
            return _fallback(
                context, role, "malformed-latest-solver-draft",
                perception=candidate_source, solver=solver,
                target_states=target_states,
            )
        if intent not in candidates:
            candidates.append(intent)
    for candidate in target_ids:
        if candidate not in candidates:
            candidates.append(candidate)
    return {
        "policy_id": POLICY_ID, "context_sha256": context.context_sha256,
        "eligible": True, "role_kind": role, "candidate_ids": candidates,
        "fallback_reason": None,
        "sources": {**_source_fields("perception", candidate_source),
                    **_source_fields("solver", solver),
                    "target_tool_state_ids": list(target_states)},
    }


def _scope(scope: Mapping[str, object], context: SlotBindingViewContext) -> None:
    keys = {"policy_id", "context_sha256", "eligible", "role_kind", "candidate_ids",
            "fallback_reason", "sources"}
    if not isinstance(scope, Mapping) or set(scope) != keys:
        raise SlotBindingViewError("slot view scope has the wrong fields")
    if scope["policy_id"] != POLICY_ID or scope["context_sha256"] != context.context_sha256:
        raise SlotBindingViewError("slot view scope belongs to another context")
    ids = scope["candidate_ids"]
    if not isinstance(ids, list) or len(ids) != len(set(ids)) or not set(ids) <= set(context.legal_candidate_ids):
        raise SlotBindingViewError("slot view scope candidate IDs are invalid")


def project_slot_value(
    context: SlotBindingViewContext, *, evidence_id: str, source_uri: str,
    content: str, scope: Mapping[str, object],
) -> tuple[str, dict[str, object] | None]:
    """Project only an exact canonical target; retain full content on uncertainty."""
    validate_slot_view_context(context)
    row = context.rows_by_value_id.get(evidence_id)
    if row is None:
        return content, None
    _scope(scope, context)
    local_id = evidence_id.split("::", 1)[1]
    expected_uri = (
        f"knowledge-snapshot://{context.knowledge_binding.binding_sha256}/{evidence_id}"
    )
    snapshot_value = next(
        value for value in context.knowledge_binding.composite_snapshot.values
        if value.value_id == evidence_id
    )
    expected = context.knowledge_binding.model_evidence_block(
        context.store_id, local_evidence_id=local_id, content=snapshot_value.content,
    )["text"]
    if source_uri != expected_uri:
        raise SlotBindingViewError("target slot source URI differs")
    # Automatic supply keeps canonical bodies plain when the tool dispatcher
    # has no named-store authority. Bind both exact shared representations;
    # never infer a source by trimming or stripping an arbitrary wrapper.
    if content == snapshot_value.content:
        source_representation = "canonical-plain-v1"
    elif content == expected:
        source_representation = "named-store-prefixed-v1"
    else:
        raise SlotBindingViewError("target slot full content differs")
    candidates = set(scope["candidate_ids"])
    indexed = tuple(enumerate(row.intent_bindings))
    selected_pairs = tuple(item for item in indexed if item[1].intent_id in candidates)
    excluded_pairs = tuple(item for item in indexed if item[1].intent_id not in candidates)
    selected = tuple(item for _index, item in selected_pairs)
    excluded = tuple(item for _index, item in excluded_pairs)
    fallback = scope["fallback_reason"]
    disposition = "full-body-fallback"
    projected = content
    if scope["eligible"] and fallback is None and selected:
        if excluded:
            document = row.document()
            document["intent_bindings"] = [item.as_json() for item in selected]
            _slot_id, _bindings, body = _slot(document)
            projected = (
                body if source_representation == "canonical-plain-v1"
                else context.knowledge_binding.model_evidence_block(
                    context.store_id, local_evidence_id=local_id, content=body,
                )["text"]
            )
            disposition = "projected"
        else:
            disposition = "full-body-no-excluded-bindings"
    elif scope["eligible"] and fallback is None:
        fallback = "no-applicable-binding"
    elif fallback is None:
        fallback = "nonconsumer-role"
    selected_addresses = [f"intent_bindings/{index}" for index, _item in selected_pairs]
    excluded_addresses = [f"intent_bindings/{index}" for index, _item in excluded_pairs]
    omitted_addresses = excluded_addresses if disposition == "projected" else []
    retained_addresses = (
        selected_addresses if disposition == "projected"
        else [f"intent_bindings/{index}" for index, _item in indexed]
    )
    receipt = {
        "schema": RECEIPT_SCHEMA, "policy_id": POLICY_ID,
        "context_sha256": context.context_sha256,
        "evidence_id": evidence_id, "source_uri": source_uri,
        "source_representation": source_representation,
        "source_content_sha256": _sha_text(content),
        "projected_content_sha256": _sha_text(projected),
        "candidate_ids": list(scope["candidate_ids"]),
        "selected_bindings": [item.as_json() for item in selected],
        "excluded_bindings": [item.as_json() for item in excluded],
        "selected_binding_addresses": selected_addresses,
        "excluded_binding_addresses": excluded_addresses,
        "retained_binding_addresses": retained_addresses,
        "omitted_binding_addresses": omitted_addresses,
        "binding_content_disposition": (
            "filtered-to-scope" if disposition == "projected" else "full-card-retained"
        ),
        "disposition": disposition, "fallback_reason": fallback,
        "sources": dict(scope["sources"]),
    }
    return projected, receipt


__all__ = [
    "POLICY_ID", "SlotBindingRow", "SlotBindingViewContext", "SlotBindingViewError",
    "SlotIntentBinding", "bind_slot_view_context", "project_slot_value",
    "scope_for_payload", "validate_slot_view_context",
]
