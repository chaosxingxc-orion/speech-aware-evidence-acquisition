"""Join verified Audio2Tool Perception states to preserved supply receipts.

This reader is CPU-only and outcome-free.  It accepts the already-verified
native episode source rather than opening traces or execution state itself,
then verifies the separate FlightReceipts selection ledger against the exact
runtime configuration, public candidate inventory, raw Perception response,
sealed AgentStateArtifact, and provider audit hashes.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import re

from ..rails.a2t_perception_state import (
    Audio2ToolPerceptionStateError,
    parse_audio2tool_perception_state,
)
from ..rails.errors import RailsError
from ..rails.hashing import content_hash
from ..rails.knowledge import AgentStateArtifact, KnowledgeSnapshot
from ..rails.knowledge_stores import qualify_id
from ..rails.task_adapter import CandidateInventory
from .native_episode_source import VerifiedNativeEpisodeSource


A2T_CANDIDATE_SUPPLY_REPORT_SCHEMA = "saea-a2t-candidate-supply-attribution-v1"
_PROVIDER_ID = "audio2tool-candidate-semantic-v1"
_RANK_POLICY_ID = "saea-ranked-candidate-round-robin-v1"
_FUSE_POLICY_ID = "saea-candidate-semantic-passthrough-v1"
_SELECTION_SCHEMA = "saea-candidate-semantic-selection-v1"
_SUPPLY_SCHEMA = "saea-candidate-semantic-supply-v1"
_ROUTING_SCHEMA = "saea-named-knowledge-store-routing-v1"
_SHA256 = re.compile(r"[0-9a-f]{64}")
_STORE_FIELDS = (
    "store_id",
    "store_role",
    "store_snapshot_sha256",
    "store_release_sha256",
    "store_source_sha256",
    "composite_snapshot_sha256",
)
_PROVIDER_FIELDS = (
    "schema",
    "snapshot_sha256",
    "sample_id",
    "candidate_state_id",
    "candidate_state_sha256",
    "candidate_source_response_sha256",
    "candidate_ids",
    "legal_candidate_inventory_sha256",
    "selection_policy_id",
    "max_actions",
    "max_candidates_per_action",
    "max_values_per_candidate",
    "max_total_values",
    "mappings",
    "selected_value_ids",
    "compact_source_phase",
    "candidate_occurrences",
)
_RECEIPT_EXTENSION_FIELDS = (
    "selection_sha256",
    *_STORE_FIELDS,
    "candidate_inventory_source_sha256",
    "candidate_inventory_authority",
    "query_state_sha256",
    "qualified_selected_value_ids",
    "supply_disposition",
    "selection_receipt_sha256",
)
_SPEC_REQUIRED = {
    "provider",
    "rank_policy",
    "fuse_policy",
    "candidate_state_phase",
    "compact_source_phase",
    "max_actions",
    "max_candidates_per_action",
    "max_values_per_candidate",
    "max_total_values",
}
_SPEC_OPTIONAL = {"supply_mode", "candidate_state_selection"}


class A2TCandidateSupplyError(ValueError):
    """The source and preserved A2T candidate evidence do not agree."""


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise A2TCandidateSupplyError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise A2TCandidateSupplyError(f"{label} must be an ordered sequence")
    return value


def _text_sequence(value: object, label: str) -> tuple[str, ...]:
    sequence = _sequence(value, label)
    if any(not isinstance(item, str) or not item for item in sequence):
        raise A2TCandidateSupplyError(f"{label} must contain nonempty text")
    return tuple(sequence)


def _sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise A2TCandidateSupplyError(f"{label} must be a lowercase SHA-256")
    return value


def _positive_integer(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise A2TCandidateSupplyError(f"{label} must be a positive integer")
    return value


def _configured_spec(
    source: VerifiedNativeEpisodeSource,
) -> tuple[str, str, Mapping[str, object], dict[str, object]]:
    stores = _mapping(
        source.composed.values.get("knowledge_stores"),
        "composed native knowledge stores",
    )
    found: list[tuple[str, str, Mapping[str, object], Mapping[str, object]]] = []
    for raw_store_id, raw_store in stores.items():
        if not isinstance(raw_store_id, str) or not raw_store_id:
            raise A2TCandidateSupplyError("configured store ID must be nonempty text")
        store = _mapping(raw_store, f"configured store {raw_store_id!r}")
        declared = store.get("candidate_supply")
        if declared in (None, {}):
            continue
        supplies = _mapping(
            declared, f"configured store {raw_store_id!r} candidate supply"
        )
        for phase, raw_spec in supplies.items():
            spec = _mapping(raw_spec, f"configured candidate spec {phase!r}")
            if spec.get("provider") == _PROVIDER_ID:
                found.append((raw_store_id, str(phase), store, spec))
    if len(found) != 1:
        raise A2TCandidateSupplyError(
            "native configuration must contain exactly one Audio2Tool candidate spec"
        )
    store_id, phase, store, spec = found[0]
    if set(spec) - (_SPEC_REQUIRED | _SPEC_OPTIONAL) or not _SPEC_REQUIRED <= set(spec):
        raise A2TCandidateSupplyError("configured Audio2Tool candidate spec has wrong fields")
    if (
        phase != "solver"
        or store.get("store_role") != "parameter-meaning"
        or spec.get("candidate_state_phase") != "perception"
        or spec.get("compact_source_phase") != "perception"
        or spec.get("rank_policy") != _RANK_POLICY_ID
        or spec.get("fuse_policy") != _FUSE_POLICY_ID
        or spec.get("candidate_state_selection", "single") != "single"
        or spec.get("supply_mode", "provide") not in {"provide", "withhold"}
    ):
        raise A2TCandidateSupplyError(
            "configured Audio2Tool candidate route is unsupported by this reader"
        )
    max_actions = _positive_integer(spec.get("max_actions"), "configured max_actions")
    max_per_action = _positive_integer(
        spec.get("max_candidates_per_action"),
        "configured max_candidates_per_action",
    )
    max_per_candidate = _positive_integer(
        spec.get("max_values_per_candidate"),
        "configured max_values_per_candidate",
    )
    max_total = _positive_integer(
        spec.get("max_total_values"), "configured max_total_values"
    )
    if max_total > max_actions * max_per_action * max_per_candidate:
        raise A2TCandidateSupplyError("configured candidate selection bounds are inconsistent")
    normalized = dict(spec)
    if normalized.get("supply_mode") == "provide":
        normalized.pop("supply_mode")
    if normalized.get("candidate_state_selection") == "single":
        normalized.pop("candidate_state_selection")
    receipt_spec = {"phase": phase, "store_id": store_id, **normalized}
    return store_id, phase, spec, receipt_spec


def _flight_supply(
    source: VerifiedNativeEpisodeSource,
    flight_receipts: Mapping[str, object],
    inventory: CandidateInventory,
    *,
    store_id: str,
    receipt_spec: Mapping[str, object],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    document = _mapping(flight_receipts, "validated FlightReceipts document")
    if (
        document.get("schema") != "saea-flight-receipts-v1"
        or document.get("run_id") != source.plan.run_id
        or document.get("attempt_id") != source.plan.attempt_id
    ):
        raise A2TCandidateSupplyError(
            "FlightReceipts run or attempt identity differs from the native source"
        )
    stages = _mapping(document.get("stages"), "FlightReceipts stages")
    run_phases = _mapping(stages.get("run_phases"), "run_phases receipt")
    phase_supply = _mapping(run_phases.get("phase_supply"), "native phase supply receipt")
    if phase_supply.get("schema") != _ROUTING_SCHEMA:
        raise A2TCandidateSupplyError("native phase supply routing schema mismatch")
    candidate_supply = _mapping(
        phase_supply.get("candidate_supply"), "native candidate supply receipt"
    )
    if candidate_supply.get("schema") != _SUPPLY_SCHEMA:
        raise A2TCandidateSupplyError("native candidate supply schema mismatch")
    legal_hash = content_hash({"candidate_ids": sorted(inventory.candidate_ids)})
    if (
        candidate_supply.get("candidate_inventory_authority")
        != inventory.source_authority
        or candidate_supply.get("candidate_inventory_source_sha256")
        != inventory.source_sha256
        or candidate_supply.get("candidate_inventory_sha256") != legal_hash
        or candidate_supply.get("candidate_inventory_count")
        != len(inventory.candidate_ids)
    ):
        raise A2TCandidateSupplyError(
            "candidate supply differs from the authoritative public inventory"
        )
    if candidate_supply.get("specs") != [dict(receipt_spec)]:
        raise A2TCandidateSupplyError(
            "candidate supply receipt spec differs from the composed configuration"
        )
    stores = _mapping(phase_supply.get("stores"), "native named store receipts")
    store = _mapping(stores.get(store_id), "native candidate store receipt")
    if (
        store.get("candidate_supply") != [dict(receipt_spec)]
        or store.get("store_id") != store_id
        or store.get("store_role") != "parameter-meaning"
    ):
        raise A2TCandidateSupplyError(
            "candidate store receipt differs from its configured route"
        )
    outer = _mapping(
        phase_supply.get("candidate_selections"), "native candidate selection receipts"
    )
    nested = _mapping(
        candidate_supply.get("candidate_selections"),
        "nested native candidate selection receipts",
    )
    if outer != nested:
        raise A2TCandidateSupplyError("native candidate selection receipt copies differ")
    return store, outer


def _authoritative_candidate_values(
    source: VerifiedNativeEpisodeSource,
    *,
    data_root: Path,
    store_id: str,
    store_receipt: Mapping[str, object],
    inventory: CandidateInventory,
) -> Mapping[str, tuple[str, ...]]:
    stores = _mapping(
        source.composed.values.get("knowledge_stores"),
        "composed native knowledge stores",
    )
    store = _mapping(stores.get(store_id), "configured candidate store")
    pin = _mapping(store.get("snapshot"), "configured candidate snapshot")
    relpath = pin.get("relpath")
    expected_hash = pin.get("sha256")
    if not isinstance(relpath, str) or not relpath:
        raise A2TCandidateSupplyError("configured candidate snapshot pin is malformed")
    expected_hash = _sha256(expected_hash, "configured candidate snapshot hash")
    root = Path(data_root).resolve()
    path = (root / relpath).resolve()
    if path == root or root not in path.parents:
        raise A2TCandidateSupplyError("configured candidate snapshot escapes data root")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
        snapshot = KnowledgeSnapshot.from_frozen_json(
            _mapping(document, "configured frozen candidate snapshot")
        )
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        KeyError,
        TypeError,
        ValueError,
        RailsError,
    ) as error:
        raise A2TCandidateSupplyError(
            f"cannot load configured frozen candidate snapshot: {error}"
        ) from error
    semantic_hash = snapshot.content_hash()
    if (
        semantic_hash != expected_hash
        or semantic_hash != store_receipt.get("store_snapshot_sha256")
    ):
        raise A2TCandidateSupplyError(
            "configured candidate snapshot semantic hash differs from its store receipt"
        )
    legal = frozenset(inventory.candidate_ids)
    index: dict[str, list[str]] = {}
    for value in snapshot.values:
        if value.task_target not in legal:
            raise A2TCandidateSupplyError(
                "candidate snapshot value lacks a legal authoritative task_target"
            )
        index.setdefault(str(value.task_target), []).append(value.value_id)
    return {
        candidate_id: tuple(sorted(value_ids))
        for candidate_id, value_ids in index.items()
    }


def _finite_reason(receipt: Mapping[str, object]) -> dict[str, object] | None:
    disposition = receipt.get("terminal_disposition")
    if not isinstance(disposition, Mapping) or disposition.get("reason") != "finite_completion":
        return None
    result = {
        key: disposition.get(key)
        for key in ("reason", "finish_reason", "role_id", "stage", "revision_count")
    }
    if (
        result["finish_reason"] not in {"length", "content_filter"}
        or not isinstance(result["role_id"], str)
        or not result["role_id"]
        or not isinstance(result["stage"], str)
        or not result["stage"]
        or isinstance(result["revision_count"], bool)
        or not isinstance(result["revision_count"], int)
        or result["revision_count"] < 0
    ):
        raise A2TCandidateSupplyError("finite terminal disposition is malformed")
    return result


def _phase_contact(
    result: Mapping[str, object], agent_contact_id: str, *, sample_id: str
) -> Mapping[str, object]:
    contacts = _sequence(result.get("contacts"), f"phase contacts for {sample_id!r}")
    matches = []
    for raw in contacts:
        contact = _mapping(raw, f"phase contact for {sample_id!r}")
        plan = contact.get("plan")
        if isinstance(plan, Mapping) and plan.get("contact_id") == agent_contact_id:
            matches.append(contact)
    if len(matches) != 1:
        raise A2TCandidateSupplyError(
            f"native contact {agent_contact_id!r} has no unique phase contact"
        )
    return matches[0]


def _contact_source(
    source: VerifiedNativeEpisodeSource,
    result: Mapping[str, object],
    execution: Mapping[str, object],
    *,
    sample_id: str,
    stage: str,
) -> tuple[dict[str, object], Mapping[str, object], str]:
    contacts = _sequence(execution.get("contacts"), f"{stage} execution contacts")
    final = _mapping(execution.get("final_contact"), f"{stage} final contact")
    if not contacts or final != contacts[-1]:
        raise A2TCandidateSupplyError(f"{stage} final contact must equal its last contact")
    agent_contact_id = final.get("agent_contact_id")
    request_id = final.get("request_id")
    if not isinstance(agent_contact_id, str) or not agent_contact_id:
        raise A2TCandidateSupplyError(f"{stage} final contact lacks an agent contact ID")
    if not isinstance(request_id, str) or not request_id:
        raise A2TCandidateSupplyError(f"{stage} final contact lacks a request ID")
    request_sha = _sha256(final.get("request_sha256"), f"{stage} request hash")
    response_sha = _sha256(final.get("response_sha256"), f"{stage} response hash")
    text_sha = _sha256(
        final.get("response_text_sha256"), f"{stage} response text hash"
    )
    phase_contact = _phase_contact(result, agent_contact_id, sample_id=sample_id)
    plan = _mapping(phase_contact.get("plan"), f"{stage} phase contact plan")
    query_sha = _sha256(
        phase_contact.get("query_state_sha256"), f"{stage} query state hash"
    )
    traces = _mapping(source.bundle.trace_records, "verified native trace records")
    request = _mapping(traces.get(f"{request_id}/request"), f"{stage} request trace")
    response = _mapping(traces.get(f"{request_id}/response"), f"{stage} response trace")
    use = _mapping(
        traces.get(f"{request_id}/native-role-contact"), f"{stage} USE trace"
    )
    payload = _mapping(request.get("payload"), f"{stage} request payload")
    text = response.get("text")
    if (
        payload.get("request_id") != request_id
        or payload.get("sample_id") != sample_id
        or request.get("payload_sha256") != request_sha
        or not isinstance(text, str)
        or hashlib.sha256(text.encode("utf-8")).hexdigest() != text_sha
        or response.get("response_sha256") != response_sha
        or response.get("response_text_sha256") != text_sha
        or use.get("use_role_id") != stage
        or use.get("use_agent_contact_id") != agent_contact_id
        or use.get("use_request_sha256") != request_sha
        or use.get("use_response_sha256") != response_sha
        or use.get("use_response_text_sha256") != text_sha
        or phase_contact.get("response_sha256") != text_sha
        or plan.get("query_state_sha256") != query_sha
    ):
        raise A2TCandidateSupplyError(
            f"{stage} final contact differs from its raw request/response custody"
        )
    return ({
        "agent_contact_id": agent_contact_id,
        "request_id": request_id,
        "request_sha256": request_sha,
        "response_sha256": response_sha,
        "response_text_sha256": text_sha,
        "query_state_sha256": query_sha,
    }, phase_contact, text)


def _perception_state(
    source: VerifiedNativeEpisodeSource,
    result: Mapping[str, object],
    *,
    sample_id: str,
    inventory: CandidateInventory,
    max_actions: int,
    max_candidates_per_action: int,
) -> dict[str, object]:
    receipt = _mapping(
        result.get("native_episode_receipt"), f"native episode receipt {sample_id!r}"
    )
    visits = _sequence(receipt.get("role_visits"), f"native role visits {sample_id!r}")
    perception = [
        (index, _mapping(raw, f"role visit {sample_id!r}[{index}]"), False)
        for index, raw in enumerate(visits)
        if isinstance(raw, Mapping) and raw.get("stage") == "perception"
    ]
    interrupted = receipt.get("interrupted_role")
    if isinstance(interrupted, Mapping) and interrupted.get("stage") == "perception":
        perception.append((None, interrupted, True))
    if len(perception) != 1:
        raise A2TCandidateSupplyError(
            "this Audio2Tool reader requires exactly one Perception visit"
        )
    visit_index, visit, is_interrupted = perception[0]
    execution = _mapping(visit.get("execution_receipt"), "Perception execution receipt")
    contact, _phase, raw_text = _contact_source(
        source, result, execution, sample_id=sample_id, stage="perception"
    )
    finite = _finite_reason(receipt)
    if is_interrupted:
        if finite is None or finite.get("stage") != "perception":
            raise A2TCandidateSupplyError(
                "interrupted Perception lacks a matching finite disposition"
            )
        return {
            "status": "unavailable",
            "missing_reason": "Perception did not complete before finite termination",
            "malformed_reason": None,
            "finite_reason": finite,
            "perception": {"visit_index": visit_index, **contact,
                           "agent_state_id": None,
                           "candidate_state_sha256": None,
                           "agent_state_artifact_sha256": None},
            "parsed": None,
        }
    expected_state_id = f"{contact['agent_contact_id']}:perception:{sample_id}"
    states = _sequence(result.get("agent_states"), f"agent states for {sample_id!r}")
    matches = [
        raw for raw in states
        if isinstance(raw, Mapping) and raw.get("state_id") == expected_state_id
    ]
    if len(matches) != 1:
        raise A2TCandidateSupplyError(
            f"Perception state {expected_state_id!r} is not unique"
        )
    try:
        state = AgentStateArtifact.from_json(matches[0]).validate()
    except (KeyError, TypeError, ValueError) as error:
        raise A2TCandidateSupplyError(f"Perception AgentStateArtifact is invalid: {error}") from error
    candidate_state_sha = hashlib.sha256(state.content.encode("utf-8")).hexdigest()
    if (
        state.state_kind != "phase:perception"
        or state.source_query_state_sha256 != contact["query_state_sha256"]
        or state.source_response_sha256 != contact["response_text_sha256"]
        or state.content != raw_text
        or candidate_state_sha != contact["response_text_sha256"]
    ):
        raise A2TCandidateSupplyError(
            "Perception state differs from its final contact and raw response"
        )
    metadata = {
        "visit_index": visit_index,
        **contact,
        "agent_state_id": state.state_id,
        "candidate_state_sha256": candidate_state_sha,
        "agent_state_artifact_sha256": state.content_hash(),
    }
    try:
        parsed = parse_audio2tool_perception_state(
            raw_text,
            legal_tool_names=inventory.candidate_ids,
            max_actions=max_actions,
            max_candidates_per_action=max_candidates_per_action,
        )
    except Audio2ToolPerceptionStateError as error:
        return {
            "status": "malformed",
            "missing_reason": None,
            "malformed_reason": str(error),
            "finite_reason": finite,
            "perception": metadata,
            "parsed": None,
        }
    return {
        "status": "observed",
        "missing_reason": None,
        "malformed_reason": None,
        "finite_reason": finite,
        "perception": metadata,
        "parsed": parsed,
    }


def _solver_query_hashes(
    result: Mapping[str, object], *, sample_id: str
) -> frozenset[str]:
    receipt = _mapping(result.get("native_episode_receipt"), "native episode receipt")
    visits = list(_sequence(receipt.get("role_visits"), "native role visits"))
    interrupted = receipt.get("interrupted_role")
    if isinstance(interrupted, Mapping):
        visits.append(interrupted)
    hashes: list[str] = []
    for raw in visits:
        visit = _mapping(raw, f"native role visit for {sample_id!r}")
        if visit.get("stage") != "solver":
            continue
        execution = _mapping(visit.get("execution_receipt"), "Solver execution receipt")
        contacts = _sequence(execution.get("contacts"), "Solver execution contacts")
        final = _mapping(execution.get("final_contact"), "Solver final contact")
        if not contacts or final != contacts[-1]:
            raise A2TCandidateSupplyError("Solver final contact must equal its last contact")
        contact_id = final.get("agent_contact_id")
        if not isinstance(contact_id, str) or not contact_id:
            raise A2TCandidateSupplyError("Solver final contact lacks an agent contact ID")
        phase = _phase_contact(result, contact_id, sample_id=sample_id)
        plan = _mapping(phase.get("plan"), "Solver phase contact plan")
        query_hash = _sha256(phase.get("query_state_sha256"), "Solver query state hash")
        if plan.get("query_state_sha256") != query_hash:
            raise A2TCandidateSupplyError("Solver query state binding differs")
        hashes.append(query_hash)
    if len(hashes) != len(set(hashes)):
        raise A2TCandidateSupplyError("Solver visits duplicate a query state")
    return frozenset(hashes)


def _expected_mapping_selection(
    candidate_ids: tuple[str, ...],
    mappings: Sequence[Mapping[str, object]],
    *,
    candidate_values: Mapping[str, tuple[str, ...]],
    max_values_per_candidate: int,
    max_total_values: int,
) -> tuple[list[str], list[dict[str, object]]]:
    values_by_candidate: list[tuple[str, ...]] = []
    for index, (candidate_id, raw_mapping) in enumerate(
        zip(candidate_ids, mappings, strict=True)
    ):
        mapping = _mapping(raw_mapping, f"candidate mapping {index}")
        if set(mapping) != {
            "candidate_id", "mapped_value_ids", "selected_value_ids",
            "ignored_mappings", "status",
        } or mapping.get("candidate_id") != candidate_id:
            raise A2TCandidateSupplyError("candidate mapping identity is malformed")
        mapped = _text_sequence(mapping.get("mapped_value_ids"), "mapped value IDs")
        if len(mapped) != len(set(mapped)) or tuple(sorted(mapped)) != mapped:
            raise A2TCandidateSupplyError(
                "candidate mapping value IDs must be unique and sorted"
            )
        if mapped != candidate_values.get(candidate_id, ()):
            raise A2TCandidateSupplyError(
                "candidate mapping differs from frozen value task_target fields"
            )
        values_by_candidate.append(mapped)
    positions = [0] * len(candidate_ids)
    selected_by: list[list[str]] = [[] for _ in candidate_ids]
    ignored_by: list[list[dict[str, str]]] = [[] for _ in candidate_ids]
    selected: list[str] = []
    selected_set: set[str] = set()
    while len(selected) < max_total_values:
        progressed = False
        for index, values in enumerate(values_by_candidate):
            if len(selected) >= max_total_values:
                break
            if len(selected_by[index]) >= max_values_per_candidate:
                continue
            while positions[index] < len(values):
                value_id = values[positions[index]]
                positions[index] += 1
                progressed = True
                if value_id in selected_set:
                    ignored_by[index].append({
                        "value_id": value_id,
                        "reason": "shared-value-already-selected",
                    })
                    continue
                selected.append(value_id)
                selected_set.add(value_id)
                selected_by[index].append(value_id)
                break
        if not progressed:
            break
        if all(
            positions[index] >= len(values)
            or len(selected_by[index]) >= max_values_per_candidate
            for index, values in enumerate(values_by_candidate)
        ):
            break
    total_full = len(selected) >= max_total_values
    for index, values in enumerate(values_by_candidate):
        while positions[index] < len(values):
            value_id = values[positions[index]]
            positions[index] += 1
            reason = (
                "shared-value-already-selected" if value_id in selected_set
                else "per-candidate-limit"
                if len(selected_by[index]) >= max_values_per_candidate
                else "total-limit" if total_full else "not-selected"
            )
            ignored_by[index].append({"value_id": value_id, "reason": reason})
    expected = [
        {
            "candidate_id": candidate_id,
            "mapped_value_ids": list(values_by_candidate[index]),
            "selected_value_ids": selected_by[index],
            "ignored_mappings": sorted(
                ignored_by[index], key=lambda item: (item["value_id"], item["reason"])
            ),
            "status": "mapped" if values_by_candidate[index] else "absent",
        }
        for index, candidate_id in enumerate(candidate_ids)
    ]
    return selected, expected


def _validate_selection(
    key: object,
    raw: object,
    *,
    sample_id: str,
    parsed: object,
    perception: Mapping[str, object],
    solver_queries: frozenset[str],
    inventory: CandidateInventory,
    legal_hash: str,
    spec: Mapping[str, object],
    store: Mapping[str, object],
    store_id: str,
    phase: str,
    candidate_values: Mapping[str, tuple[str, ...]],
) -> dict[str, object]:
    audit = _mapping(raw, f"candidate selection {key!r}")
    expected_keys = set(_PROVIDER_FIELDS) | set(_RECEIPT_EXTENSION_FIELDS)
    if set(audit) != expected_keys:
        raise A2TCandidateSupplyError("candidate selection receipt has wrong fields")
    receipt_unsigned = dict(audit)
    receipt_hash = receipt_unsigned.pop("selection_receipt_sha256")
    if receipt_hash != content_hash(receipt_unsigned):
        raise A2TCandidateSupplyError("candidate selection receipt hash mismatch")
    provider_body = {field: audit[field] for field in _PROVIDER_FIELDS}
    if audit.get("selection_sha256") != content_hash(provider_body):
        raise A2TCandidateSupplyError("candidate provider selection hash mismatch")
    occurrences = [
        {"action_id": action.action_id, "candidate_tools": list(action.candidate_tools)}
        for action in parsed.actions
    ]
    candidate_ids = tuple(parsed.unique_tool_names)
    query_hash = _sha256(audit.get("query_state_sha256"), "selection query state hash")
    if (
        audit.get("schema") != _SELECTION_SCHEMA
        or audit.get("sample_id") != sample_id
        or key != f"{phase}:{sample_id}:{query_hash}"
        or query_hash not in solver_queries
        or audit.get("candidate_state_id") != perception.get("agent_state_id")
        or audit.get("candidate_state_sha256")
        != perception.get("candidate_state_sha256")
        or audit.get("candidate_source_response_sha256")
        != perception.get("response_text_sha256")
        or audit.get("candidate_ids") != list(candidate_ids)
        or audit.get("candidate_occurrences") != occurrences
        or audit.get("legal_candidate_inventory_sha256") != legal_hash
        or audit.get("selection_policy_id") != _RANK_POLICY_ID
        or audit.get("compact_source_phase") != "perception"
        or audit.get("max_actions") != spec.get("max_actions")
        or audit.get("max_candidates_per_action")
        != spec.get("max_candidates_per_action")
        or audit.get("max_values_per_candidate")
        != spec.get("max_values_per_candidate")
        or audit.get("max_total_values") != spec.get("max_total_values")
        or audit.get("candidate_inventory_source_sha256") != inventory.source_sha256
        or audit.get("candidate_inventory_authority") != inventory.source_authority
    ):
        raise A2TCandidateSupplyError(
            "candidate selection sample, state, inventory, or configured bounds mismatch"
        )
    for field in _STORE_FIELDS:
        if audit.get(field) != store.get(field):
            raise A2TCandidateSupplyError("candidate selection store binding mismatch")
    if audit.get("store_id") != store_id or audit.get("snapshot_sha256") != store.get(
        "store_snapshot_sha256"
    ):
        raise A2TCandidateSupplyError("candidate selection snapshot binding mismatch")
    mappings = _sequence(audit.get("mappings"), "candidate mappings")
    if len(mappings) != len(candidate_ids):
        raise A2TCandidateSupplyError("candidate mapping count mismatch")
    selected, expected_mappings = _expected_mapping_selection(
        candidate_ids,
        [_mapping(row, "candidate mapping") for row in mappings],
        candidate_values=candidate_values,
        max_values_per_candidate=int(spec["max_values_per_candidate"]),
        max_total_values=int(spec["max_total_values"]),
    )
    if audit.get("mappings") != expected_mappings or audit.get("selected_value_ids") != selected:
        raise A2TCandidateSupplyError("candidate mapping selection differs from the provider policy")
    qualified = [qualify_id(store_id, value_id) for value_id in selected]
    if audit.get("qualified_selected_value_ids") != qualified:
        raise A2TCandidateSupplyError("qualified selected IDs differ from the store binding")
    disposition = audit.get("supply_disposition")
    mode = spec.get("supply_mode", "provide")
    allowed = (
        {"no-mapping"} if not selected
        else {"withheld"} if mode == "withhold"
        else {"acquired", "already-visible"}
    )
    if disposition not in allowed:
        raise A2TCandidateSupplyError("candidate supply disposition is inconsistent")
    return dict(audit)


def _unavailable_selection(store_id: str, reason: str) -> dict[str, object]:
    return {
        "status": "unavailable",
        "missing_reason": reason,
        "selection_count": 0,
        "supply_dispositions": {},
        "store_id": store_id,
        "store_role": "parameter-meaning",
        "selected_value_ids": None,
        "qualified_selected_value_ids": None,
        "mappings": None,
        "mapped_candidate_ids": None,
        "absent_candidate_ids": None,
        "mapped_candidate_count": None,
        "absent_candidate_count": None,
        "mapping_coverage": None,
    }


def analyze_a2t_candidate_supply(
    source: VerifiedNativeEpisodeSource,
    *,
    flight_receipts: Mapping[str, object],
    candidate_inventory: CandidateInventory,
    data_root: Path,
) -> dict[str, object]:
    """Return source-complete A2T candidate and mapping attribution rows.

    ``flight_receipts`` must be the document returned by
    :func:`core.flight.receipts.read_flight_receipts`.  Missing per-sample
    selection entries remain explicit unavailable evidence.  A successfully
    parsed state with zero actions remains an observed empty candidate set.
    """
    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise A2TCandidateSupplyError(
            "source must be a VerifiedNativeEpisodeSource from the shared loader"
        )
    if not isinstance(candidate_inventory, CandidateInventory):
        raise A2TCandidateSupplyError("candidate_inventory must be a CandidateInventory")
    try:
        candidate_inventory.validate()
    except ValueError as error:
        raise A2TCandidateSupplyError(f"candidate inventory is invalid: {error}") from error
    sample_ids = tuple(source.sample_ids)
    if (
        not sample_ids
        or len(sample_ids) != len(set(sample_ids))
        or not isinstance(source.phase_results, Mapping)
        or set(source.phase_results) != set(sample_ids)
    ):
        raise A2TCandidateSupplyError("verified native source has an invalid exact cohort")
    store_id, phase, spec, receipt_spec = _configured_spec(source)
    store, selections = _flight_supply(
        source,
        flight_receipts,
        candidate_inventory,
        store_id=store_id,
        receipt_spec=receipt_spec,
    )
    candidate_values = _authoritative_candidate_values(
        source,
        data_root=data_root,
        store_id=store_id,
        store_receipt=store,
        inventory=candidate_inventory,
    )
    legal_hash = content_hash({"candidate_ids": sorted(candidate_inventory.candidate_ids)})
    selections_by_sample: dict[str, list[tuple[object, object]]] = {
        sample_id: [] for sample_id in sample_ids
    }
    for key, audit in selections.items():
        sample_id = audit.get("sample_id") if isinstance(audit, Mapping) else None
        if sample_id not in selections_by_sample:
            raise A2TCandidateSupplyError("candidate selection has a foreign sample")
        selections_by_sample[str(sample_id)].append((key, audit))

    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    selection_status_counts: Counter[str] = Counter()
    disposition_counts: Counter[str] = Counter()
    selection_total = 0
    mapped_total = 0
    mapping_total = 0
    unique_observations = 0
    for sample_id in sample_ids:
        result = _mapping(source.phase_results[sample_id], f"phase result {sample_id!r}")
        if result.get("sample_id") != sample_id:
            raise A2TCandidateSupplyError("phase result sample identity mismatch")
        state_row = _perception_state(
            source,
            result,
            sample_id=sample_id,
            inventory=candidate_inventory,
            max_actions=int(spec["max_actions"]),
            max_candidates_per_action=int(spec["max_candidates_per_action"]),
        )
        status = str(state_row["status"])
        status_counts[status] += 1
        parsed = state_row["parsed"]
        audits = selections_by_sample[sample_id]
        solver_queries = _solver_query_hashes(result, sample_id=sample_id)
        if parsed is None:
            if audits:
                raise A2TCandidateSupplyError(
                    "unavailable or malformed Perception state has a selection receipt"
                )
            reason = (
                "candidate state was malformed before selection"
                if status == "malformed"
                else "no Solver selection occurred before finite termination"
            )
            selection_report = _unavailable_selection(store_id, reason)
            actions = None
            widths = None
            candidate_ids = None
        else:
            actions = [
                {
                    "action_id": action.action_id,
                    "candidate_tools": list(action.candidate_tools),
                    "candidate_width": len(action.candidate_tools),
                }
                for action in parsed.actions
            ]
            widths = [len(action.candidate_tools) for action in parsed.actions]
            candidate_ids = list(parsed.unique_tool_names)
            unique_observations += len(candidate_ids)
            validated = [
                _validate_selection(
                    key,
                    audit,
                    sample_id=sample_id,
                    parsed=parsed,
                    perception=_mapping(state_row["perception"], "Perception source"),
                    solver_queries=solver_queries,
                    inventory=candidate_inventory,
                    legal_hash=legal_hash,
                    spec=spec,
                    store=store,
                    store_id=store_id,
                    phase=phase,
                    candidate_values=candidate_values,
                )
                for key, audit in audits
            ]
            if not validated:
                selection_report = _unavailable_selection(
                    store_id, "candidate selection receipt is missing"
                )
            else:
                stable_fields = (
                    *_PROVIDER_FIELDS,
                    "selection_sha256",
                    *_STORE_FIELDS,
                    "candidate_inventory_source_sha256",
                    "candidate_inventory_authority",
                    "qualified_selected_value_ids",
                )
                reference = {field: validated[0][field] for field in stable_fields}
                if any(
                    {field: audit[field] for field in stable_fields} != reference
                    for audit in validated[1:]
                ):
                    raise A2TCandidateSupplyError(
                        "repeated Solver selections changed the single Perception mapping"
                    )
                per_sample_dispositions = Counter(
                    str(audit["supply_disposition"]) for audit in validated
                )
                dispositions = dict(sorted(per_sample_dispositions.items()))
                disposition_counts.update(per_sample_dispositions)
                mappings = validated[0]["mappings"]
                mapped = [
                    row["candidate_id"] for row in mappings if row["status"] == "mapped"
                ]
                absent = [
                    row["candidate_id"] for row in mappings if row["status"] == "absent"
                ]
                denominator = len(mapped) + len(absent)
                mapped_total += len(mapped)
                mapping_total += denominator
                selection_report = {
                    "status": "available",
                    "missing_reason": None,
                    "selection_count": len(validated),
                    "supply_dispositions": dispositions,
                    "store_id": store_id,
                    "store_role": store["store_role"],
                    "selected_value_ids": list(validated[0]["selected_value_ids"]),
                    "qualified_selected_value_ids": list(
                        validated[0]["qualified_selected_value_ids"]
                    ),
                    "mappings": mappings,
                    "mapped_candidate_ids": mapped,
                    "absent_candidate_ids": absent,
                    "mapped_candidate_count": len(mapped),
                    "absent_candidate_count": len(absent),
                    "mapping_coverage": (
                        len(mapped) / denominator if denominator else None
                    ),
                }
                selection_total += len(validated)
        selection_status_counts[str(selection_report["status"])] += 1
        rows.append({
            "sample_id": sample_id,
            "candidate_state_status": status,
            "candidate_state_missing_reason": state_row["missing_reason"],
            "candidate_state_malformed_reason": state_row["malformed_reason"],
            "finite_reason": state_row["finite_reason"],
            "perception": state_row["perception"],
            "actions": actions,
            "action_count": None if actions is None else len(actions),
            "per_action_candidate_widths": widths,
            "unique_candidate_ids": candidate_ids,
            "unique_candidate_count": None if candidate_ids is None else len(candidate_ids),
            "selection": selection_report,
        })

    return {
        "schema": A2T_CANDIDATE_SUPPLY_REPORT_SCHEMA,
        "run_id": source.plan.run_id,
        "attempt_id": source.plan.attempt_id,
        "source_sample_ids": list(sample_ids),
        "candidate_inventory": {
            "candidate_count": len(candidate_inventory.candidate_ids),
            "candidate_inventory_sha256": legal_hash,
            "source_sha256": candidate_inventory.source_sha256,
            "source_authority": candidate_inventory.source_authority,
        },
        "configured_route": dict(receipt_spec),
        "summary": {
            "sample_count": len(sample_ids),
            "candidate_state_status_counts": dict(sorted(status_counts.items())),
            "selection_status_counts": dict(sorted(selection_status_counts.items())),
            "selection_receipt_count": selection_total,
            "supply_dispositions": dict(sorted(disposition_counts.items())),
            "unique_candidate_observation_count": unique_observations,
            "mapped_candidate_observation_count": mapped_total,
            "candidate_mapping_observation_count": mapping_total,
            "mapping_coverage": mapped_total / mapping_total if mapping_total else None,
        },
        "samples": rows,
    }


__all__ = [
    "A2T_CANDIDATE_SUPPLY_REPORT_SCHEMA",
    "A2TCandidateSupplyError",
    "analyze_a2t_candidate_supply",
]
