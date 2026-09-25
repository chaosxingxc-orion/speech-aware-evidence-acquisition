"""Pure post-seal diagnostics for verified native-role episodes.

The caller owns bundle and phase-artifact verification. This module joins native
receipts to verified request, response, USE, and tool trace payloads. It neither
parses carrier answers nor reconstructs an unavailable candidate-selection ledger.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from ..rails.consumption import ConsumptionTrace
from ..rails.errors import RailsError
from ..rails.hashing import content_hash
from ..rails.native_episode_receipt import (
    is_illegal_planner_route,
    validate_native_episode_delivery_receipt,
)
from .completion_budget import CompletionBudgetError, analyze_completion_metadata


class NativeEpisodeDiagnosticError(ValueError):
    """A native receipt does not match its manifest-verified trace."""


_CONTACT_FIELDS = (
    "agent_contact_id", "request_id", "request_sha256",
    "response_sha256", "response_text_sha256",
)
_TOOL_EVENTS = ("attempt", "failed", "rejected", "result")


def _map(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise NativeEpisodeDiagnosticError(f"{label} must be a mapping")
    return value


def _seq(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise NativeEpisodeDiagnosticError(f"{label} must be an ordered sequence")
    return value


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _contact(value: object, label: str) -> dict[str, str]:
    raw = _map(value, label)
    result: dict[str, str] = {}
    for field in _CONTACT_FIELDS:
        item = raw.get(field)
        if not isinstance(item, str) or not item:
            raise NativeEpisodeDiagnosticError(f"{label}.{field} must be nonempty text")
        if field.endswith("sha256") and (
            len(item) != 64
            or any(character not in "0123456789abcdef" for character in item)
        ):
            raise NativeEpisodeDiagnosticError(f"{label}.{field} must be a lowercase SHA-256")
        result[field] = item
    return result


def join_native_role_contact_response(
    *,
    sample_id: str,
    role_id: str,
    contact: object,
    trace_records: Mapping[str, Mapping[str, object]],
    label: str = "native role contact",
) -> tuple[
    dict[str, str],
    Mapping[str, object],
    Mapping[str, object],
    Mapping[str, object],
]:
    """Join one receipt contact to its exact request, response, and USE trace.

    This is the shared post-seal role-contact custody predicate. Callers may
    select a role visit, but they must never select response text without this
    join. The returned tuple is ``(contact, request, response, use)``.
    """
    if not isinstance(sample_id, str) or not sample_id:
        raise NativeEpisodeDiagnosticError("sample_id must be nonempty text")
    if not isinstance(role_id, str) or not role_id:
        raise NativeEpisodeDiagnosticError("role_id must be nonempty text")
    item = _contact(contact, label)
    request_id = item["request_id"]
    request = trace_records.get(f"{request_id}/request")
    response = trace_records.get(f"{request_id}/response")
    use = trace_records.get(f"{request_id}/native-role-contact")
    if not all(isinstance(value, Mapping) for value in (request, response, use)):
        raise NativeEpisodeDiagnosticError(
            f"native contact {request_id!r} lacks request/response/USE custody"
        )
    request = _map(request, "request trace")
    response = _map(response, "response trace")
    use = _map(use, "role USE trace")
    payload = _map(request.get("payload"), "request payload")
    response_text = response.get("text")
    if (
        payload.get("request_id") != request_id
        or payload.get("sample_id") != sample_id
        or request.get("payload_sha256") != item["request_sha256"]
        or not isinstance(response_text, str)
        or _sha(response_text) != item["response_text_sha256"]
        or response.get("response_sha256") != item["response_sha256"]
        or response.get("response_text_sha256") != item["response_text_sha256"]
        or use.get("use_role_id") != role_id
        or use.get("use_agent_contact_id") != item["agent_contact_id"]
        or use.get("use_request_sha256") != item["request_sha256"]
        or use.get("use_response_sha256") != item["response_sha256"]
        or use.get("use_response_text_sha256") != item["response_text_sha256"]
    ):
        raise NativeEpisodeDiagnosticError(
            f"native contact {request_id!r} differs from receipt/trace"
        )
    return item, request, response, use


def _completion(
    request_id: str,
    request: Mapping[str, object],
    response: Mapping[str, object],
    wire: Mapping[str, object] | None,
    *,
    delivered_text: str | None = None,
) -> dict[str, object]:
    payload = request.get("payload")
    decoding = payload.get("decoding_params") if isinstance(payload, Mapping) else None
    limit = decoding.get("max_tokens") if isinstance(decoding, Mapping) else None
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        return {
            "metadata_available": False,
            "missing_reason": "request completion ceiling is unavailable",
            "max_tokens": None,
            "completion_tokens": None,
            "at_cap": None,
            "actual_length_stop": None,
            "stop_reason": None,
            "wire_metadata_available": wire is not None,
        }
    records: list[Mapping[str, object]] = [
        {"channel": "MODEL_REQUEST", "record_id": f"{request_id}/request", "payload": request},
        {"channel": "MODEL_RESPONSE", "record_id": f"{request_id}/response", "payload": response},
    ]
    if wire is not None:
        records.append({
            "channel": "MODEL_WIRE_RESPONSE",
            "record_id": f"{request_id}/wire-response",
            "payload": wire,
        })
    outputs: tuple[Mapping[str, object], ...] = ()
    if delivered_text is not None:
        outputs = ({
            "request_id": request_id,
            "sample_id": payload.get("sample_id"),
            "text": delivered_text,
            "response_text_sha256": _sha(delivered_text),
        },)
    try:
        row = analyze_completion_metadata(records, outputs)["rows"][0]
    except CompletionBudgetError as error:
        raise NativeEpisodeDiagnosticError(
            f"completion metadata for {request_id!r} is inconsistent: {error}"
        ) from error
    return {
        "metadata_available": True,
        "missing_reason": None,
        "max_tokens": row["max_tokens"],
        "completion_tokens": row["completion_tokens"],
        "at_cap": row["at_cap"],
        "actual_length_stop": row["actual_length_stop"],
        "stop_reason": row["stop_reason"],
        "wire_metadata_available": bool(row["wire"]["available"]),
    }


def _supplied(payload: Mapping[str, object], label: str) -> dict[str, object]:
    if "supplied_evidence" not in payload:
        return {
            "supply_metadata_available": False,
            "supplied_evidence_ids": None,
            "supplied_value_ids": None,
        }
    rows = _seq(payload["supplied_evidence"], f"{label}.supplied_evidence")
    evidence_ids: list[str] = []
    value_ids: list[str] = []
    for index, value in enumerate(rows):
        item = _map(value, f"{label}.supplied_evidence[{index}]")
        evidence_id = item.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            raise NativeEpisodeDiagnosticError(
                f"{label}.supplied_evidence[{index}] lacks an evidence ID"
            )
        evidence_ids.append(evidence_id)
        if item.get("knowledge_role") == "value":
            value_ids.append(evidence_id)
    return {
        "supply_metadata_available": True,
        "supplied_evidence_ids": evidence_ids,
        "supplied_value_ids": value_ids,
    }


def _cap_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, int]:
    return {
        "contact_count": len(rows),
        "metadata_available_count": sum(row.get("metadata_available") is True for row in rows),
        "metadata_unavailable_count": sum(row.get("metadata_available") is not True for row in rows),
        "completion_tokens_available_count": sum(row.get("completion_tokens") is not None for row in rows),
        "at_cap_count": sum(row.get("at_cap") is True for row in rows),
        "at_cap_unknown_count": sum(row.get("at_cap") is None for row in rows),
        "length_stop_count": sum(row.get("actual_length_stop") is True for row in rows),
        "length_stop_unknown_count": sum(row.get("actual_length_stop") is None for row in rows),
    }


def _abstention_completion() -> dict[str, object]:
    return {
        "metadata_available": False,
        "missing_reason": "no Solver response was delivered; deterministic abstention",
        "max_tokens": None,
        "completion_tokens": None,
        "at_cap": None,
        "actual_length_stop": None,
        "stop_reason": None,
        "wire_metadata_available": False,
    }


def _tool_rows(
    sample_id: str,
    controller_policy_id: str,
    trace_records: Mapping[str, Mapping[str, object]],
    contacts: Mapping[str, Mapping[str, object]],
) -> list[dict[str, object]]:
    base = f"{sample_id}/{controller_policy_id}/"
    result: list[dict[str, object]] = []
    for record_id, raw_payload in trace_records.items():
        if not isinstance(record_id, str) or not record_id.startswith(base):
            continue
        parts = record_id[len(base):].split("/")
        if len(parts) not in {2, 3} or not parts[1].startswith("tool-"):
            continue
        phase, event = parts[0], parts[1].removeprefix("tool-")
        if event not in _TOOL_EVENTS:
            continue
        payload = _map(raw_payload, f"native tool event {record_id!r}")
        prefixes = [
            prefix for prefix in ("use", "obs")
            if any(str(key).startswith(f"{prefix}_") for key in payload)
        ]
        if len(prefixes) != 1:
            raise NativeEpisodeDiagnosticError(
                f"native tool event {record_id!r} has no unique trace axis"
            )
        prefix = prefixes[0]
        request_id = payload.get(f"{prefix}_core_request_id")
        call_id = payload.get(f"{prefix}_tool_call_id")
        tool_id = payload.get(f"{prefix}_tool_id")
        source_identity_available = all(
            isinstance(item, str) and item for item in (request_id, call_id, tool_id)
        )
        if not source_identity_available:
            if event != "rejected" or len(parts) != 2:
                raise NativeEpisodeDiagnosticError(
                    f"native tool event {record_id!r} lacks source call identity"
                )
            request_id = call_id = tool_id = None
        else:
            source = contacts.get(str(request_id))
            if (
                source is None
                or source.get("role_id") != phase
                or payload.get(f"{prefix}_sample_id") != sample_id
                or payload.get(f"{prefix}_phase") != phase
            ):
                raise NativeEpisodeDiagnosticError(
                    f"native tool event {record_id!r} differs from its role contact"
                )
            suffix = content_hash({"request_id": request_id, "tool_call_id": call_id})
            if len(parts) != 3 or parts[2] != suffix:
                raise NativeEpisodeDiagnosticError(
                    f"native tool event {record_id!r} has an invalid source hash suffix"
                )
        invocation = payload.get(f"{prefix}_tool_invocation")
        if invocation is not None:
            invocation = _map(invocation, f"native tool event {record_id!r} invocation")
            if (
                invocation.get("schema") not in {
                    "saea-native-phase-tool-contact-v1",
                    "saea-native-phase-tool-contact-v2",
                }
                or invocation.get("sample_id") != sample_id
                or invocation.get("phase") != phase
                or invocation.get("request_id") != request_id
                or invocation.get("tool_call_id") != call_id
                or invocation.get("tool_id") != tool_id
            ):
                raise NativeEpisodeDiagnosticError(
                    f"native tool event {record_id!r} invocation binding mismatch"
                )
        result.append({
            "record_id": record_id,
            "event": event,
            "axis": "analytical" if prefix == "use" else "observation",
            "role_id": phase,
            "tool_id": tool_id,
            "request_id": request_id,
            "tool_call_id": call_id,
            "source_call_identity_available": source_identity_available,
            "contact_receipt_available": invocation is not None,
        })
    return sorted(result, key=lambda row: str(row["record_id"]))


def _consumption(
    sample_id: str,
    controller_policy_id: str,
    phase_result: Mapping[str, object],
    final_sha256: str,
    trace_records: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    base = f"{sample_id}/{controller_policy_id}/agent-loop"
    runtime = trace_records.get(f"{base}/runtime-use")
    posthoc = trace_records.get(f"{base}/posthoc-use")
    if not isinstance(runtime, Mapping) or not isinstance(posthoc, Mapping):
        return {
            "available": False,
            "missing_reason": "manifest-verified runtime/posthoc consumption trace is unavailable",
            "record_count": None,
            "outcome_counts": None,
            "copy_rate": None,
            "dose_realized": None,
        }
    raw = posthoc.get("use_consumption")
    if raw is None:
        return {
            "available": False,
            "missing_reason": "posthoc lexical consumption metadata is unavailable",
            "record_count": None,
            "outcome_counts": None,
            "copy_rate": None,
            "dose_realized": None,
        }
    document = _map(raw, f"native consumption for {sample_id!r}")
    if (
        phase_result.get("consumption") != document
        or posthoc.get("use_runtime_trace_sha256") != runtime.get("use_runtime_trace_sha256")
        or posthoc.get("use_final_response_sha256") != final_sha256
        or runtime.get("use_final_response_sha256") != final_sha256
    ):
        raise NativeEpisodeDiagnosticError(
            f"native consumption for {sample_id!r} differs from phase/runtime custody"
        )
    try:
        trace = ConsumptionTrace.from_json(document)
    except (KeyError, TypeError, ValueError, RailsError) as error:
        raise NativeEpisodeDiagnosticError(
            f"native consumption for {sample_id!r} is malformed: {error}"
        ) from error
    counts = Counter(record.outcome.value for record in trace.records)
    return {
        "available": True,
        "missing_reason": None,
        "record_count": len(trace.records),
        "outcome_counts": {name: counts.get(name, 0) for name in ("copy", "use", "ignore")},
        "copy_rate": trace.copy_rate,
        "dose_realized": trace.dose_realized,
    }


def analyze_verified_native_episode_statistics(
    *,
    sample_ids: Sequence[str],
    controller_policy_id: str,
    phase_results: Mapping[str, Mapping[str, object]],
    output_rows: Mapping[str, Mapping[str, object]],
    trace_records: Mapping[str, Mapping[str, object]],
) -> dict[str, Any]:
    """Return descriptive statistics after exact receipt/trace joins."""
    ids = tuple(sample_ids)
    if (
        not ids
        or len(ids) != len(set(ids))
        or any(not isinstance(sample_id, str) or not sample_id for sample_id in ids)
    ):
        raise NativeEpisodeDiagnosticError("sample_ids must be distinct nonempty text")
    if not isinstance(controller_policy_id, str) or not controller_policy_id:
        raise NativeEpisodeDiagnosticError("controller_policy_id must be nonempty text")
    if not set(ids) <= set(phase_results) or not set(ids) <= set(output_rows):
        raise NativeEpisodeDiagnosticError("native diagnostic population is incomplete")

    samples: list[dict[str, object]] = []
    all_contacts: list[dict[str, object]] = []
    all_tools: list[dict[str, object]] = []
    final_completions: list[Mapping[str, object]] = []
    consumptions: list[Mapping[str, object]] = []
    action_counts: Counter[str] = Counter()
    illegal_routes = 0
    revision_counts: Counter[int] = Counter()
    terminal_actions: Counter[str] = Counter()
    terminal_revisions: Counter[int] = Counter()
    finite_finish_reasons: Counter[str] = Counter()
    finite_roles: Counter[str] = Counter()
    finite_stages: Counter[str] = Counter()
    finite_solver_deliveries = 0
    abstentions = 0

    for sample_id in ids:
        phase_result = _map(phase_results[sample_id], f"phase result {sample_id!r}")
        output = _map(output_rows[sample_id], f"output row {sample_id!r}")
        text = output.get("text")
        if not isinstance(text, str):
            raise NativeEpisodeDiagnosticError(f"output row {sample_id!r} lacks text")
        final_sha256 = _sha(text)
        episode = _map(
            phase_result.get("native_episode_receipt"),
            f"native episode receipt {sample_id!r}",
        )
        if (
            output.get("native_episode_receipt") != episode
            or phase_result.get("final_response_text") != text
            or phase_result.get("final_response_sha256") != final_sha256
        ):
            raise NativeEpisodeDiagnosticError(
                f"native episode {sample_id!r} differs from final output"
            )

        visits = _seq(episode.get("role_visits"), f"native role visits {sample_id!r}")
        flattened: list[dict[str, object]] = []
        executions: list[tuple[str, str, Mapping[str, object]]] = []
        contact_ids: set[str] = set()
        request_ids: set[str] = set()
        by_request: dict[str, Mapping[str, object]] = {}
        visit_rows: list[tuple[int | None, object, bool]] = [
            (index, raw_visit, False) for index, raw_visit in enumerate(visits)
        ]
        if episode.get("interrupted_role") is not None:
            visit_rows.append((None, episode["interrupted_role"], True))
        for visit_index, raw_visit, interrupted in visit_rows:
            label = "interrupted role" if interrupted else f"role visit [{visit_index}]"
            visit = _map(raw_visit, f"native {label} {sample_id!r}")
            role_id, stage = visit.get("role_id"), visit.get("stage")
            if not all(isinstance(item, str) and item for item in (role_id, stage)):
                raise NativeEpisodeDiagnosticError("native role visit lacks role identity")
            execution = _map(visit.get("execution_receipt"), "native role execution")
            raw_contacts = _seq(execution.get("contacts"), "native role contacts")
            if not raw_contacts:
                raise NativeEpisodeDiagnosticError("native role visit has no contacts")
            contacts = [
                _contact(raw, f"native contact {sample_id!r}[{label}][{index}]")
                for index, raw in enumerate(raw_contacts)
            ]
            if _contact(execution.get("final_contact"), "native role final contact") != contacts[-1]:
                raise NativeEpisodeDiagnosticError("native role final contact is not its last contact")
            if not interrupted:
                executions.append((str(role_id), str(stage), execution))
            for contact_index, item in enumerate(contacts):
                request_id = item["request_id"]
                agent_contact_id = item["agent_contact_id"]
                if request_id in request_ids or agent_contact_id in contact_ids:
                    raise NativeEpisodeDiagnosticError("native episode duplicates a contact identity")
                request_ids.add(request_id)
                contact_ids.add(agent_contact_id)
                item, request, response, _use = join_native_role_contact_response(
                    sample_id=sample_id,
                    role_id=str(role_id),
                    contact=item,
                    trace_records=trace_records,
                    label=f"native contact {sample_id!r}[{label}][{contact_index}]",
                )
                payload = _map(request.get("payload"), "request payload")
                wire = trace_records.get(f"{request_id}/wire-response")
                if interrupted:
                    wire_mapping = wire if isinstance(wire, Mapping) else None
                    wire_reason = wire_mapping.get("finish_reason") if wire_mapping else None
                    if contact_index == len(contacts) - 1:
                        disposition = _map(
                            episode.get("terminal_disposition"), "finite terminal disposition"
                        )
                        if wire_reason != disposition.get("finish_reason"):
                            raise NativeEpisodeDiagnosticError(
                                "interrupted role wire finish reason differs from disposition"
                            )
                    elif wire_reason in {"length", "content_filter"}:
                        raise NativeEpisodeDiagnosticError(
                            "only the interrupted role final contact may have a finite wire finish reason"
                        )
                row = {
                    "sample_id": sample_id,
                    "role_id": role_id,
                    "stage": stage,
                    "visit_index": visit_index,
                    "contact_index": contact_index,
                    "agent_contact_id": agent_contact_id,
                    "request_id": request_id,
                    "completion": _completion(
                        request_id, request, response,
                        wire,
                    ),
                    **_supplied(payload, f"request payload {request_id!r}"),
                }
                if interrupted:
                    row["interrupted"] = True
                flattened.append(row)
                all_contacts.append(row)
                by_request[request_id] = row

        phase_contacts = _seq(phase_result.get("contacts"), f"phase contacts {sample_id!r}")
        if len(phase_contacts) != len(flattened):
            raise NativeEpisodeDiagnosticError(
                f"native episode {sample_id!r} receipt omits phase contacts"
            )
        for index, (raw_phase, receipt_contact) in enumerate(zip(phase_contacts, flattened)):
            phase_contact = _map(raw_phase, f"phase contact {sample_id!r}[{index}]")
            plan = _map(phase_contact.get("plan"), "phase contact plan")
            response = _map(
                trace_records[f"{receipt_contact['request_id']}/response"], "phase response"
            )
            if (
                plan.get("contact_id") != receipt_contact["agent_contact_id"]
                or phase_contact.get("response_sha256") != response.get("response_text_sha256")
            ):
                raise NativeEpisodeDiagnosticError(
                    f"native episode {sample_id!r} receipt differs from phase contacts"
                )

        routes = _seq(episode.get("planner_routes"), f"Planner routes {sample_id!r}")
        ordered_routes: list[dict[str, object]] = []
        for index, raw_route in enumerate(routes):
            route = _map(raw_route, f"Planner route {sample_id!r}[{index}]")
            visit_index = route.get("role_visit_index")
            revision = route.get("revision_count")
            action = route.get("action")
            if (
                isinstance(visit_index, bool)
                or not isinstance(visit_index, int)
                or not 0 <= visit_index < len(visits)
                or _map(visits[visit_index], "Planner route visit").get("stage") != "planner"
                or isinstance(revision, bool)
                or not isinstance(revision, int)
                or revision < 0
                or not isinstance(action, str)
                or not action
            ):
                raise NativeEpisodeDiagnosticError(
                    f"Planner route {sample_id!r}[{index}] is malformed"
                )
            ordered_route: dict[str, object] = {
                "role_visit_index": visit_index,
                "revision_count": revision,
                "action": action,
            }
            if is_illegal_planner_route(route):
                # E8c: a RETAINED row whose Planner named no registered
                # action. Its "action" is the truncated malformed token,
                # so a reader must not take it for a configured action.
                ordered_route["legal"] = False
                ordered_route["disposition"] = route["disposition"]
                illegal_routes += 1
            ordered_routes.append(ordered_route)
            action_counts[action] += 1
            revision_counts[revision] += 1

        delivery = validate_native_episode_delivery_receipt(
            episode,
            visits,
            routes,
            error_type=NativeEpisodeDiagnosticError,
        )
        delivered_final = _contact(delivery.final_contact, f"{delivery.kind} final contact")
        delivered_request_id: str | None = None
        derived_request_id: str | None = None
        if delivery.kind == "abstention":
            from ..core.delivery import native_abstention_records

            disposition = _map(delivery.terminal_disposition, "finite terminal disposition")
            derived_request_id, request_document, response_document = (
                native_abstention_records(
                    sample_id=sample_id,
                    source_contact=delivered_final,
                    finish_reason=str(disposition["finish_reason"]),
                )
            )
            if (
                text != ""
                or output.get("request_id") != derived_request_id
                or output.get("request_sha256") != request_document["payload_sha256"]
                or output.get("response_sha256") != response_document["response_sha256"]
                or output.get("response_text_sha256") != response_document["response_text_sha256"]
                or trace_records.get(f"{derived_request_id}/request") != request_document
                or trace_records.get(f"{derived_request_id}/response") != response_document
            ):
                raise NativeEpisodeDiagnosticError(
                    f"native abstention derivative {sample_id!r} differs from shared delivery"
                )
            final_completion = _abstention_completion()
        else:
            delivered_request_id = delivered_final["request_id"]
            delivered_response = _map(
                trace_records.get(f"{delivered_request_id}/response"),
                f"{delivery.kind} Solver response",
            )
            normalisation = episode.get("deliver_normaliser")
            if normalisation is not None:
                from ..core.bundle import BundleError
                from ..core.bundle.outputs import _verify_delivery_normalisation

                try:
                    _verify_delivery_normalisation(
                        output, _map(normalisation, "delivery normalisation"),
                        delivered_response,
                    )
                except BundleError as error:
                    raise NativeEpisodeDiagnosticError(
                        f"delivery normalisation custody failed: {error}"
                    ) from error
            elif (
                delivered_final["response_text_sha256"] != final_sha256
                or delivered_response.get("text") != text
            ):
                raise NativeEpisodeDiagnosticError(
                    f"{delivery.kind} Solver response {sample_id!r} is not final output"
                )
            final_completion = _completion(
                delivered_request_id,
                _map(
                    trace_records[f"{delivered_request_id}/request"],
                    "delivered Solver request",
                ),
                delivered_response,
                trace_records.get(f"{delivered_request_id}/wire-response"),
                # Completion limits describe generated bytes before delivery.
                delivered_text=delivered_response["text"],
            )
            by_request[delivered_request_id]["completion"] = final_completion
        final_completions.append(final_completion)
        if delivery.kind == "terminal":
            disposition = _map(delivery.terminal_disposition, "terminal disposition")
            planner_route = _map(delivery.planner_route, "terminal Planner route")
            planner_visit_index = planner_route["role_visit_index"]
            planner_execution = executions[planner_visit_index][2]
            planner_final = _contact(
                planner_execution.get("final_contact"), "terminal Planner final contact"
            )
            planner_response = _map(
                trace_records.get(f"{planner_final['request_id']}/response"),
                "terminal Planner response",
            )
            # The shared receipt validator already binds JSON control to the
            # raw Planner text, final contact hash and route action.
            expected_planner_text = (
                episode["plan"]
                if episode.get("planner_control") is not None
                else disposition["planner_action"]
            )
            if planner_response.get("text") != expected_planner_text:
                raise NativeEpisodeDiagnosticError(
                    f"terminal Planner response {sample_id!r} differs from disposition"
                )
            terminal_actions[str(disposition["planner_action"])] += 1
            terminal_revisions[int(disposition["revision_count"])] += 1
        elif delivery.kind in {"finite", "abstention"}:
            disposition = _map(delivery.terminal_disposition, "finite terminal disposition")
            finite_finish_reasons[str(disposition["finish_reason"])] += 1
            finite_roles[str(disposition["role_id"])] += 1
            finite_stages[str(disposition["stage"])] += 1
            if delivery.kind == "finite":
                finite_solver_deliveries += 1
            else:
                abstentions += 1

        tools = _tool_rows(sample_id, controller_policy_id, trace_records, by_request)
        consumption = _consumption(
            sample_id, controller_policy_id, phase_result, final_sha256, trace_records
        )
        all_tools.extend(tools)
        consumptions.append(consumption)
        sample = {
            "sample_id": sample_id,
            "model_contacts": flattened,
            "planner_routes": ordered_routes,
            "native_tool_events": tools,
            "lexical_consumption": consumption,
        }
        normalisation = episode.get("deliver_normaliser")
        if normalisation is not None:
            sample["delivery_normalisation"] = {
                key: normalisation[key]
                for key in ("normaliser_id", "input_sha256", "output_sha256")
            }
            sample["delivery_normalisation"]["changed"] = (
                normalisation["input_sha256"] != normalisation["output_sha256"]
            )
        delivery_record = {
            "request_id": delivered_request_id,
            "agent_contact_id": delivered_final["agent_contact_id"],
            "completion": final_completion,
        }
        if delivery.kind == "accepted":
            sample["accepted_solver"] = delivery_record
        elif delivery.kind == "terminal":
            sample["terminal_solver"] = delivery_record
            sample["terminal_disposition"] = dict(
                _map(delivery.terminal_disposition, "terminal disposition")
            )
        elif delivery.kind == "finite":
            sample["finite_solver"] = delivery_record
            sample["finite_disposition"] = dict(
                _map(delivery.terminal_disposition, "finite terminal disposition")
            )
        else:
            sample["abstention"] = {
                "derived_request_id": derived_request_id,
                "source_request_id": delivered_final["request_id"],
                "delivered_solver": False,
                "completion": final_completion,
            }
            sample["finite_disposition"] = dict(
                _map(delivery.terminal_disposition, "finite terminal disposition")
            )
        samples.append(sample)

    role_counts = Counter(str(row["role_id"]) for row in all_contacts)
    role_caps = {
        role: _cap_summary([
            _map(row["completion"], "role completion")
            for row in all_contacts if row["role_id"] == role
        ])
        for role in sorted(role_counts)
    }
    event_counts = Counter(str(row["event"]) for row in all_tools)
    contacted_tool_calls = {
        (str(row["axis"]), str(row["request_id"]), str(row["tool_call_id"]))
        for row in all_tools if row["contact_receipt_available"] is True
    }
    axis_counts = {
        axis: {
            event: sum(row["axis"] == axis and row["event"] == event for row in all_tools)
            for event in _TOOL_EVENTS
        }
        for axis in ("analytical", "observation")
    }
    supply_rows = [row for row in all_contacts if row["supply_metadata_available"] is True]
    value_ids = [
        value_id for row in supply_rows for value_id in (row["supplied_value_ids"] or [])
    ]
    lexical_counts: Counter[str] = Counter()
    lexical_record_count = 0
    for row in consumptions:
        if row["available"] is True:
            lexical_record_count += int(row["record_count"])
            lexical_counts.update(_map(row["outcome_counts"], "consumption counts"))

    result = {
        "schema": "saea-native-episode-postseal-diagnostics-v1",
        "sample_count": len(ids),
        "model_contacts": {
            "count": len(all_contacts),
            "by_role": dict(sorted(role_counts.items())),
            "role_completion_cap": role_caps,
            "final_completion_cap": _cap_summary(final_completions),
        },
        "native_tool_events": {
            "event_count": len(all_tools),
            "by_event": {event: event_counts.get(event, 0) for event in _TOOL_EVENTS},
            "by_axis_and_event": axis_counts,
            "source_call_identity_unavailable_event_count": sum(
                row["source_call_identity_available"] is not True for row in all_tools
            ),
            "contact_receipt_available_event_count": sum(
                row["contact_receipt_available"] is True for row in all_tools
            ),
            "contacted_call_count": len(contacted_tool_calls),
            "contacted_call_count_by_axis": {
                axis: sum(call[0] == axis for call in contacted_tool_calls)
                for axis in ("analytical", "observation")
            },
        },
        "planner": {
            "route_count": sum(action_counts.values()),
            "action_counts": dict(sorted(action_counts.items())),
            # E8c: how many of those routes are the row-level
            # illegal-Planner-output disposition rather than an action.
            "illegal_route_count": illegal_routes,
            "revision_count_histogram": {
                str(key): value for key, value in sorted(revision_counts.items())
            },
        },
        "knowledge": {
            "supply": {
                "contacts_with_metadata": len(supply_rows),
                "contacts_without_metadata": len(all_contacts) - len(supply_rows),
                "supplied_value_occurrences": len(value_ids),
                "unique_supplied_value_ids": sorted(set(value_ids)),
                "source": "manifest-verified per-contact MODEL_REQUEST supplied_evidence",
            },
            "lexical_consumption": {
                "available_sample_count": sum(row["available"] is True for row in consumptions),
                "unavailable_sample_count": sum(row["available"] is not True for row in consumptions),
                "record_count": lexical_record_count,
                "outcome_counts": {
                    name: lexical_counts.get(name, 0) for name in ("copy", "use", "ignore")
                },
                "semantics": (
                    "Lexical USE/COPY/IGNORE describes final-answer token overlap; "
                    "it does not establish semantic or causal use."
                ),
            },
            "candidate_selection_audit": {
                "status": "not-reconstructed",
                "reason": (
                    "candidate-to-value selection is unavailable without genuine "
                    "preserved FlightReceipts"
                ),
            },
        },
        "samples": samples,
    }
    if terminal_actions:
        result["terminal_stops"] = {
            "count": sum(terminal_actions.values()),
            "by_planner_action": dict(sorted(terminal_actions.items())),
            "by_revision_count": {
                str(key): value for key, value in sorted(terminal_revisions.items())
            },
        }
    if finite_finish_reasons:
        result["finite_stops"] = {
            "count": sum(finite_finish_reasons.values()),
            "solver_delivery_count": finite_solver_deliveries,
            "abstention_count": abstentions,
            "by_finish_reason": dict(sorted(finite_finish_reasons.items())),
            "by_role": dict(sorted(finite_roles.items())),
            "by_stage": dict(sorted(finite_stages.items())),
        }
    return result


__all__ = ["NativeEpisodeDiagnosticError", "analyze_verified_native_episode_statistics"]
