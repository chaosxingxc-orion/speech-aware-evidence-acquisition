"""Pure post-seal verification of native tool-result exposure.

This reports custody and request visibility, not semantic use, benefit, or
carrier quality. Bundle and phase-artifact verification remain caller-owned.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from ..core.model import FrozenCoreError
from ..core.model.native_framework_history import (
    project_native_framework_history,
    validate_native_framework_contact,
)
from ..core.model.native_history import project_native_history
from ..core.model.transport import _speech_history_texts
from ..rails.errors import RailsError
from ..rails.hashing import content_hash
from ..rails.native_tool_authority import (
    validate_native_call_rejection,
    validate_native_tool_authority,
)
from .native_episode_diagnostics import analyze_verified_native_episode_statistics


class NativeToolExposureError(ValueError):
    """Native tool custody or a claimed later exposure is inconsistent."""


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise NativeToolExposureError(f"{label} must be a mapping")
    return value


def _document(payload: Mapping[str, object], prefix: str) -> dict[str, object]:
    return {
        str(key)[len(prefix) + 1 :]: value
        for key, value in payload.items()
        if isinstance(key, str) and key.startswith(prefix + "_")
    }


def _state_id(document: Mapping[str, object], *, rejected: bool = False) -> str:
    kind = "tool-rejection" if rejected else "tool-result"
    return f"{kind}:{document['phase']}:{document['sample_id']}:" + content_hash(
        {
            "request_id": document["core_request_id"],
            "tool_call_id": document["tool_call_id"],
        }
    )


def _native_state_document(state: Mapping[str, object]) -> dict[str, object] | None:
    if state.get("role") != "agent_state" or state.get("state_kind") != "tool-result":
        return None
    try:
        document = json.loads(state.get("content", ""))
    except (TypeError, ValueError):
        return None
    if not isinstance(document, dict) or "native_tool_calls_json" not in document:
        return None
    return document


def _visible_selection(result: object) -> tuple[int | None, bool | None]:
    if not isinstance(result, Mapping):
        return None, None
    selected = [
        value
        for key, value in result.items()
        if isinstance(key, str)
        and key.startswith("selected_")
        and isinstance(value, list)
    ]
    if not selected:
        return None, None
    count = sum(len(value) for value in selected)
    return count, count == 0


def _check_source_custody(
    *,
    sample_id: str,
    role_id: str,
    contact: Mapping[str, object],
    document: Mapping[str, object],
    trace_records: Mapping[str, Mapping[str, object]],
) -> tuple[dict[str, object], bool]:
    rejection = document.get("schema") == "saea-phase-tool-rejection-v1"
    selected_original_call: Mapping[str, object] | None = None
    try:
        if rejection:
            authority, selected_original_call = validate_native_call_rejection(document)
        else:
            authority = validate_native_tool_authority(document.get("source_authority"))
    except (RailsError, KeyError, TypeError, ValueError) as error:
        raise NativeToolExposureError(
            "native result has invalid source authority"
        ) from error
    invocation = (
        None
        if rejection
        else _mapping(document.get("tool_invocation"), "native tool invocation")
    )
    raw_calls = document.get("native_tool_calls_json")
    result = document.get("result")
    blocks = document.get("native_result_content")
    try:
        calls = json.loads(raw_calls) if isinstance(raw_calls, str) else None
    except ValueError as error:
        raise NativeToolExposureError("native result call bytes are invalid") from error
    matching_calls = (
        []
        if not isinstance(calls, list)
        else [call for call in calls if isinstance(call, Mapping)
              and call.get("id") == document.get("tool_call_id")]
    )
    common_invalid = (
        document.get("selection_mode") != "native-tools"
        or document.get("source_authority_sha256") != content_hash(authority)
        or not isinstance(result, Mapping)
        or content_hash(result) != document.get("result_sha256")
        or not isinstance(blocks, list)
        or content_hash({"blocks": blocks})
        != document.get("native_result_content_sha256")
        or not isinstance(raw_calls, str)
        or hashlib.sha256(raw_calls.encode()).hexdigest()
        != document.get("tool_calls_sha256")
        or not isinstance(calls, list)
        or not calls
        or len(matching_calls) != 1
        or not isinstance(matching_calls[0].get("function"), Mapping)
        or matching_calls[0]["function"].get("name") != document.get("tool_id")
        or authority.get("original_assistant_message", {}).get("tool_calls") != calls
    )
    if rejection:
        if (
            common_invalid
            or len(calls) <= 1
            or "tool_invocation" in document
            or selected_original_call != matching_calls[0]
            or result.get("status") != "rejected"
            or result.get("error_code") != "multiple-tool-calls"
            or result.get("lookup_performed") is not False
            or blocks != []
        ):
            raise NativeToolExposureError(
                "native rejection event has invalid source custody"
            )
    elif (
        common_invalid
        or document.get("schema") != "saea-phase-tool-result-v2"
        or len(calls) != 1
        or invocation is None
        or invocation.get("request_id") != document.get("core_request_id")
        or invocation.get("tool_call_id") != document.get("tool_call_id")
        or invocation.get("tool_id") != document.get("tool_id")
    ):
        raise NativeToolExposureError("native result event has invalid counted custody")
    request_id = document.get("core_request_id")
    if not isinstance(request_id, str) or not request_id:
        raise NativeToolExposureError("native result lacks its source request identity")
    request = _mapping(
        trace_records.get(f"{request_id}/request"), "source request trace"
    )
    response = _mapping(
        trace_records.get(f"{request_id}/response"), "source response trace"
    )
    completion_raw = trace_records.get(f"{request_id}/native-completion")
    completion = (
        _mapping(completion_raw, "source native completion trace")
        if completion_raw is not None
        else None
    )
    request_payload = _mapping(request.get("payload"), "source request payload")
    expected = {
        "request_id": request_id,
        "sample_id": sample_id,
        "role_id": role_id,
        "agent_contact_id": contact.get("agent_contact_id"),
        "source_request_sha256": request.get("payload_sha256"),
        "source_response_sha256": response.get("response_sha256"),
        "source_response_text_sha256": response.get("response_text_sha256"),
        "source_tool_calls_sha256": document.get("tool_calls_sha256"),
    }
    if any(authority.get(key) != value for key, value in expected.items()):
        raise NativeToolExposureError(
            f"native result source authority differs from verified contact {request_id!r}"
        )
    if (
        authority.get("phase_id") != document.get("phase")
        or document.get("sample_id") != sample_id
        or document.get("tool_calls_sha256")
        != authority.get("source_tool_calls_sha256")
        or document.get("source_response_sha256")
        != authority.get("source_response_text_sha256")
        or (
            completion is not None
            and (
                completion.get("schema") != "saea-native-completion-v1"
                or completion.get("request_id") != request_id
                or completion.get("sample_id") != sample_id
                or completion.get("agent_contact_id") != contact.get("agent_contact_id")
                or completion.get("request_sha256") != request.get("payload_sha256")
                or completion.get("response_sha256") != response.get("response_sha256")
                or completion.get("response_text_sha256")
                != response.get("response_text_sha256")
                or completion.get("native_tool_calls_json")
                != document.get("native_tool_calls_json")
                or completion.get("native_tool_calls_sha256")
                != document.get("tool_calls_sha256")
            )
        )
        or authority.get("selected_tool_schemas") != request_payload.get("tool_schemas")
    ):
        raise NativeToolExposureError(
            f"native result differs from source request/response custody {request_id!r}"
        )
    return authority, completion is not None

def _check_event_document(
    receipt: Mapping[str, object], document: Mapping[str, object]
) -> None:
    receipt_only = {"internal_memory_lineage", "internal_observation_lineage"}
    for key, value in receipt.items():
        if key in receipt_only or key in {
            "result",
            "result_sha256",
            "model_result_sha256",
        }:
            continue
        if document.get(key) != value:
            raise NativeToolExposureError(
                f"visible native result field {key!r} differs from its result event"
            )
    model_hash = receipt.get("model_result_sha256")
    expected_hash = (
        model_hash if model_hash is not None else receipt.get("result_sha256")
    )
    if (
        document.get("result_sha256") != expected_hash
        or content_hash(document.get("result")) != expected_hash
    ):
        raise NativeToolExposureError(
            "visible document.result differs from its result event"
        )
    if model_hash is None and document.get("result") != receipt.get("result"):
        raise NativeToolExposureError("visible document.result content was substituted")


def _project_request(
    payload: Mapping[str, object],
) -> tuple[list[Mapping[str, object]], str]:
    """Use the same pure history projection as the real transport."""
    history = payload.get("history", [])
    try:
        state_texts = _speech_history_texts(history)
        messages = [
            {"role": "system", "content": payload.get("task_instruction")},
            {
                "role": "user",
                "content": [{"type": "text", "text": text} for text in state_texts],
            },
        ]
        validated = validate_native_framework_contact(payload)
        if validated is not None:
            projected = project_native_framework_history(
                payload=payload, messages=messages, state_texts=state_texts
            )
            assert projected is not None
            return projected[0], "framework-or-inherited-history"
        rendered, _packets = project_native_history(
            payload=payload, messages=messages, state_texts=state_texts
        )
        return rendered, "legacy-inherited-history"
    except (FrozenCoreError, AssertionError, KeyError, TypeError, ValueError) as error:
        raise NativeToolExposureError(
            "native request history does not project exactly"
        ) from error


def analyze_verified_native_tool_exposure(
    *,
    sample_ids: Sequence[str],
    controller_policy_id: str,
    phase_results: Mapping[str, Mapping[str, object]],
    output_rows: Mapping[str, Mapping[str, object]],
    trace_records: Mapping[str, Mapping[str, object]],
) -> dict[str, Any]:
    """Verify successful results and counted rejection feedback separately."""
    diagnostics = analyze_verified_native_episode_statistics(
        sample_ids=sample_ids,
        controller_policy_id=controller_policy_id,
        phase_results=phase_results,
        output_rows=output_rows,
        trace_records=trace_records,
    )
    contact_by_request: dict[str, Mapping[str, object]] = {}
    contact_rank: dict[str, int] = {}
    for sample in diagnostics["samples"]:
        for rank, contact in enumerate(sample["model_contacts"]):
            request_id = str(contact["request_id"])
            if request_id in contact_by_request:
                raise NativeToolExposureError(
                    f"native episodes repeat request identity {request_id!r}"
                )
            contact_by_request[request_id] = contact
            contact_rank[request_id] = rank

    observations: dict[tuple[str, str], dict[str, object]] = {}
    pre_dispatch_rejections: set[tuple[str, str]] = set()
    non_results: list[dict[str, object]] = []
    for sample in diagnostics["samples"]:
        sample_id = str(sample["sample_id"])
        for event in sample["native_tool_events"]:
            if event["event"] != "result":
                non_results.append(
                    {
                        key: event[key]
                        for key in (
                            "record_id",
                            "event",
                            "axis",
                            "role_id",
                            "tool_id",
                            "request_id",
                            "tool_call_id",
                            "source_call_identity_available",
                        )
                    }
                )
                if event["event"] != "rejected":
                    continue
                raw_rejection = _mapping(
                    trace_records.get(str(event["record_id"])), "tool rejection event"
                )
                prefix = "use" if event["axis"] == "analytical" else "obs"
                rejected_document = _document(raw_rejection, prefix)
                rejection_schema = rejected_document.get("schema")
                if rejection_schema not in {
                    "saea-phase-tool-result-v2",
                    "saea-phase-tool-rejection-v1",
                }:
                    # Historical pre-dispatch rejections have no counted result.
                    continue
                rejected_result = _mapping(
                    rejected_document.get("result"), "tool rejection result"
                )
                if (
                    rejected_result.get("status") != "rejected"
                    or rejected_result.get("lookup_performed") is not False
                    or rejected_document.get("native_result_content") != []
                    or (
                        rejection_schema == "saea-phase-tool-rejection-v1"
                        and event["contact_receipt_available"] is not False
                    )
                ):
                    raise NativeToolExposureError("rejection claims executed evidence")
            rejected = event["event"] == "rejected"
            request_id = str(event["request_id"])
            call_id = str(event["tool_call_id"])
            key = (request_id, call_id)
            if key in observations:
                raise NativeToolExposureError(
                    "native trace duplicates a returned call"
                )
            if (
                rejected
                and rejected_document.get("schema")
                == "saea-phase-tool-rejection-v1"
            ):
                pre_dispatch_rejections.add(key)
            raw = _mapping(
                trace_records.get(str(event["record_id"])), "tool result event"
            )
            prefix = "use" if event["axis"] == "analytical" else "obs"
            receipt = _document(raw, prefix)
            contact = contact_by_request[request_id]
            authority, completion_trace_available = _check_source_custody(
                sample_id=sample_id,
                role_id=str(event["role_id"]),
                contact=contact,
                document=receipt,
                trace_records=trace_records,
            )
            state_id = _state_id(receipt, rejected=rejected)
            result_hash = receipt.get(
                "model_result_sha256", receipt.get("result_sha256")
            )
            if not isinstance(result_hash, str):
                raise NativeToolExposureError(
                    "native result lacks its model-visible result hash"
                )
            selection_count, selection_empty = _visible_selection(receipt.get("result"))
            observations[key] = {
                **({"outcome": "rejected"} if rejected else {}),
                "record_id": event["record_id"],
                "sample_id": sample_id,
                "axis": event["axis"],
                "role_id": event["role_id"],
                "tool_id": event["tool_id"],
                "source_request_id": request_id,
                "tool_call_id": call_id,
                "source_completion_sha256": authority["completion_sha256"],
                "source_completion_trace_available": completion_trace_available,
                "contact_receipt_available": event["contact_receipt_available"],
                "result_sha256": result_hash,
                "result_empty": receipt.get("result") == {},
                "selection_count": selection_count,
                "selection_empty": selection_empty,
                "state_id": state_id,
                "exposed_request_ids": [],
                "exposure_paths": {},
            }

    attempted = {
        (str(event["request_id"]), str(event["tool_call_id"]))
        for sample in diagnostics["samples"]
        for event in sample["native_tool_events"]
        if event["event"] == "attempt" and event["source_call_identity_available"]
    }
    attempted_with_contact_receipts = {
        (str(event["request_id"]), str(event["tool_call_id"]))
        for sample in diagnostics["samples"]
        for event in sample["native_tool_events"]
        if (
            event["event"] == "attempt"
            and event["source_call_identity_available"]
            and event["contact_receipt_available"] is True
        )
    }
    if any(key in attempted_with_contact_receipts for key in pre_dispatch_rejections):
        raise NativeToolExposureError(
            "native pre-dispatch rejection claims a contact receipt"
        )
    if any(key not in attempted for key in observations):
        raise NativeToolExposureError(
            "native return lacks its attempt event"
        )

    for request_id, contact in contact_by_request.items():
        request = _mapping(trace_records.get(f"{request_id}/request"), "request trace")
        payload = _mapping(request.get("payload"), "request payload")
        rendered, path = _project_request(payload)
        history = payload.get("history", [])
        documents: list[tuple[str, dict[str, object]]] = []
        if isinstance(history, list):
            for state in history:
                if not isinstance(state, Mapping):
                    continue
                document = _native_state_document(state)
                if document is not None:
                    documents.append((str(state.get("state_id")), document))
        tool_messages = [row for row in rendered if row.get("role") == "tool"]
        visible_pairs = []
        for message in tool_messages:
            try:
                body = json.loads(message.get("content", ""))
            except (TypeError, ValueError):
                continue
            if isinstance(body, Mapping) and "result" in body:
                visible_pairs.append((message.get("tool_call_id"), body["result"]))
        expected_pairs = [
            (document.get("tool_call_id"), document.get("result"))
            for _state_id, document in documents
        ]
        if visible_pairs != expected_pairs:
            raise NativeToolExposureError(
                f"request {request_id!r} does not project its exact ordered "
                "visible document.result sequence"
            )
        for state_id, document in documents:
            key = (
                str(document.get("core_request_id")),
                str(document.get("tool_call_id")),
            )
            call = observations.get(key)
            if call is None:
                raise NativeToolExposureError(
                    f"request {request_id!r} claims foreign native call history {key!r}"
                )
            if state_id != call["state_id"]:
                raise NativeToolExposureError(
                    f"request {request_id!r} claims the wrong native result state"
                )
            if contact["sample_id"] != call["sample_id"]:
                raise NativeToolExposureError(
                    f"request {request_id!r} claims another sample native result"
                )
            if contact_rank[request_id] <= contact_rank[str(call["source_request_id"])]:
                raise NativeToolExposureError(
                    f"request {request_id!r} claims future or same-contact native history"
                )
            raw_event = _mapping(
                trace_records[str(call["record_id"])], "tool result event"
            )
            prefix = "use" if call["axis"] == "analytical" else "obs"
            _check_event_document(_document(raw_event, prefix), document)

            exposed_ids = call["exposed_request_ids"]
            assert isinstance(exposed_ids, list)
            exposed_ids.append(request_id)
            paths = call["exposure_paths"]
            assert isinstance(paths, dict)
            paths[request_id] = path

    calls = []
    for call in observations.values():
        exposed_ids = list(call.pop("exposed_request_ids"))
        paths = dict(call.pop("exposure_paths"))
        calls.append(
            {
                **call,
                "exposed": bool(exposed_ids),
                "exposed_request_count": len(exposed_ids),
                "exposed_request_ids": exposed_ids,
                "exposed_state_id": call["state_id"] if exposed_ids else None,
                "exposure_path_by_request": paths,
            }
        )
    calls.sort(
        key=lambda row: (
            str(row["sample_id"]),
            str(row["source_request_id"]),
            str(row["tool_call_id"]),
        )
    )
    rejected_calls = [row for row in calls if row.get("outcome") == "rejected"]
    calls = [row for row in calls if row.get("outcome") != "rejected"]
    rejection_summary = ({
        "rejected_call_count": len(rejected_calls),
        "exposed_rejected_call_count": sum(row["exposed"] is True for row in rejected_calls),
        "rejected_call_contact_receipt_count": sum(
            row["contact_receipt_available"] is True for row in rejected_calls
        ),
        "rejected_calls": rejected_calls,
    } if rejected_calls else {})
    counts = Counter(row["event"] for row in non_results)
    return {
        "schema": "saea-native-tool-exposure-postseal-v1",
        "sample_count": diagnostics["sample_count"],
        "model_contact_count": diagnostics["model_contacts"]["count"],
        "successful_call_count": len(calls),
        "exposed_successful_call_count": sum(row["exposed"] is True for row in calls),
        "unexposed_successful_call_count": sum(
            row["exposed"] is False for row in calls
        ),
        "non_result_event_counts": {
            name: counts.get(name, 0) for name in ("attempt", "failed", "rejected")
        },
        "calls": calls,
        "non_result_events": non_results,
        **rejection_summary,
        "semantics": (
            "Exposure proves exact native tool-result visibility in a later "
            "frozen-core request history projection; it does not establish "
            "semantic use, causal benefit, or task quality."
        ),
    }


__all__ = [
    "NativeToolExposureError",
    "analyze_verified_native_tool_exposure",
]
