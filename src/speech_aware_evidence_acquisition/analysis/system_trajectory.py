"""Content-addressed, score-free exports of verified whole native episodes."""
from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

from ..rails.hashing import content_hash
from ..rails.native_episode_receipt import validate_native_episode_delivery_receipt
from .native_episode_diagnostics import (
    NativeEpisodeDiagnosticError,
    analyze_verified_native_episode_statistics,
    join_native_role_contact_response,
)
from .native_episode_source import VerifiedNativeEpisodeSource


SCHEMA = "saea-system-trajectory-export-v1"
_PHASE_FIELDS = ("agent_states", "transitions", "query_states", "evidence", "consumption")


class SystemTrajectoryError(ValueError):
    """A supposedly verified episode cannot be exported with full custody."""


def _map(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise SystemTrajectoryError(f"{label} must be an object")
    return value


def _seq(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise SystemTrajectoryError(f"{label} must be an ordered sequence")
    return value


def _hash(value: object) -> str:
    try:
        return content_hash(value if isinstance(value, Mapping) else {"value": value})
    except (TypeError, ValueError) as error:
        raise SystemTrajectoryError(f"source content is not canonical JSON: {error}") from error


def _ref(value: object, *, record_id: str | None = None) -> dict[str, object]:
    result: dict[str, object] = {"content_sha256": _hash(value)}
    if record_id is not None:
        result["record_id"] = record_id
    return result


def _phase_fields(result: Mapping[str, object]) -> dict[str, object]:
    fields = {}
    for name in sorted(set(result) | set(_PHASE_FIELDS)):
        if name in {"sample_id", "final_response_text", "native_episode_receipt"}:
            continue
        if name not in result:
            fields[name] = {"status": "unavailable_in_source"}
            continue
        value = result[name]
        item = {"status": "recorded", **_ref(value)}
        if isinstance(value, (list, tuple)):
            item["count"] = len(value)
            item["items"] = [
                {"index": index, **_ref(part)}
                for index, part in enumerate(value)
            ]
        fields[name] = item
    return fields



def _episode_events(episode: Mapping[str, object]) -> dict[str, object]:
    """Expose known terminal/exception evidence without guessing missing counts."""
    result = {}
    for name in ("truncation_events", "planner_action_illegal", "react_exhaustion",
                 "abstention_receipt", "terminal_disposition"):
        if name not in episode:
            result[name] = {"status": "unavailable_in_source"}
            continue
        value = episode[name]
        entry = {"status": "recorded", **_ref(value)}
        events = value.get("events") if isinstance(value, Mapping) else value
        if isinstance(events, (list, tuple)):
            entry.update(count=len(events), items=[
                {"index": index, **_ref(item)} for index, item in enumerate(events)
            ])
        result[name] = entry
    return result


def _trace_refs(trace: Mapping[str, object], sid: str, request_ids: set[str]) -> list[dict]:
    refs = []
    for record_id, value in trace.items():
        if not isinstance(record_id, str):
            raise SystemTrajectoryError("trace record id must be text")
        payload = _map(value, f"trace record {record_id!r}")
        if (
            record_id.startswith(f"{sid}/")
            or any(record_id.startswith(f"{request_id}/") for request_id in request_ids)
            or any(payload.get(key) == sid for key in ("sample_id", "use_sample_id", "obs_sample_id"))
        ):
            refs.append(_ref(payload, record_id=record_id))
    return sorted(refs, key=lambda item: str(item["record_id"]))



def _system_policy_choice(*, sid, phase, episode, output, visits, trace, related, trace_order):
    """Join the pre-role ORG choice to the original query and final receipt."""
    import copy
    from ..rails.knowledge import QueryState
    from ..rails.system_episode_policy import parse_system_policy_record

    record = episode.get("system_policy_decision")
    if record is None and not related:
        return None
    try:
        parse_system_policy_record(record)
        key = f"{sid}/system-policy/initial"
        if (record["sample_id"] != sid or related != {key: record}
                or output.get("native_episode_receipt", {}).get("system_policy_decision") != record):
            raise ValueError("choice is missing, duplicated or differs across source records")
        query = QueryState.from_json(phase["initial_query_state"])
        if (query.query_sample_id != sid or query.loop_step != 0 or query.agent_state_ids
                or query.content_hash() != record["pre_action_query_sha256"]
                or query.speech_packet_sha256 != record["speech_packet_sha256"]):
            raise ValueError("choice differs from the initial speech query")
        contacts = [c for visit in visits for c in visit["contacts"]]
        if not contacts:
            raise ValueError("choice has no realized first request")
        first = contacts[0]["request_record_id"]
        if trace[first]["payload"].get("speech_packet_sha256") != query.speech_packet_sha256:
            raise ValueError("first model request uses different speech")
        # VerifiedBundle preserves raw JSONL order. Check every contact, not a
        # role label that could accidentally hide an earlier interrupted visit.
        if any(trace_order[key] >= trace_order[c["request_record_id"]] for c in contacts):
            raise ValueError("choice was not recorded before all model requests")
    except (KeyError, TypeError, ValueError) as error:
        raise SystemTrajectoryError(f"system policy source custody failed: {error}") from error
    return {
        "record": copy.deepcopy(record), "trace_record_id": key,
        "trace_record_sha256": _hash(trace[key]),
        "claim_scope": "recorded-choice-not-learning-admission",
    }


def _candidate_proposal(*, sid, episode, output, trace):
    """Keep derived candidates addressable across every downstream contact."""
    import copy
    from ..rails.slurp_candidate_proposal import validate_candidate_proposal_consumption

    output_episode = _map(output.get("native_episode_receipt"), "output episode")
    present = "candidate_proposal" in episode
    if present != ("candidate_proposal" in output_episode):
        raise SystemTrajectoryError("candidate proposal differs across phase and output")
    if not present:
        return None
    block = episode["candidate_proposal"]
    if block is None or block != output_episode["candidate_proposal"]:
        raise SystemTrajectoryError("candidate proposal differs across phase and output")
    try:
        validate_candidate_proposal_consumption(
            episode, sample_id=sid, trace_records=trace, error_type=SystemTrajectoryError,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise SystemTrajectoryError(f"candidate proposal source custody failed: {error}") from error
    return {
        "receipt": copy.deepcopy(block), "receipt_sha256": _hash(block),
        "claim_scope": "verified-supply-not-semantic-use",
    }


def export_system_trajectories(source: VerifiedNativeEpisodeSource) -> dict[str, object]:
    """Export every role and contact of a verified source without answer or gold text.

    The source must come from `verify_native_episode_source` in production. Its
    diagnostic custody check is rerun here; this function does not itself seal
    a manifest, phase artifact, score, or flight receipt.
    """
    if not isinstance(source, VerifiedNativeEpisodeSource):
        raise SystemTrajectoryError("source must be a VerifiedNativeEpisodeSource")
    ids = tuple(source.sample_ids)
    if not ids or len(ids) != len(set(ids)) or set(ids) != set(source.phase_results) or set(ids) != set(source.output_rows):
        raise SystemTrajectoryError("source sample ids do not exactly cover phase and output rows")
    trace = _map(source.bundle.trace_records, "verified trace records")
    policy_records = {}
    for rid, payload in trace.items():
        if isinstance(payload, Mapping) and "org_system_policy_decision" in payload:
            record = payload["org_system_policy_decision"]
            if (not isinstance(record, Mapping) or record.get("sample_id") not in ids
                    or rid != f"{record.get('sample_id')}/system-policy/initial"):
                raise SystemTrajectoryError("system policy trace has an orphan or duplicate choice")
            policy_records[record["sample_id"]] = {rid: record}
    policy_trace_order = {rid: index for index, rid in enumerate(trace)} if policy_records else {}
    values = _map(source.composed.values, "composed configuration")
    policy = values.get("policy")
    if not isinstance(policy, str) or not policy:
        raise SystemTrajectoryError("composed source lacks its controller policy")
    try:
        diagnostics = analyze_verified_native_episode_statistics(
            sample_ids=ids, controller_policy_id=policy,
            phase_results=source.phase_results, output_rows=source.output_rows,
            trace_records=trace,
        )
    except (NativeEpisodeDiagnosticError, KeyError, TypeError, ValueError) as error:
        raise SystemTrajectoryError(f"native source custody failed: {error}") from error
    diagnostic_rows = {row["sample_id"]: row for row in diagnostics["samples"]}
    if set(diagnostic_rows) != set(ids):
        raise SystemTrajectoryError("diagnostic rows do not cover the source")
    rows = []
    for sid in ids:
        phase = _map(source.phase_results[sid], f"phase result {sid!r}")
        output = _map(source.output_rows[sid], f"output {sid!r}")
        episode = _map(phase.get("native_episode_receipt"), f"episode {sid!r}")
        try:
            delivery = validate_native_episode_delivery_receipt(
                episode, error_type=SystemTrajectoryError
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SystemTrajectoryError(f"native delivery {sid!r} is invalid: {error}") from error
        raw_visits = list(_seq(episode.get("role_visits"), "role visits"))
        if episode.get("interrupted_role") is not None:
            raw_visits.append(episode["interrupted_role"])
        visits = []
        request_ids: set[str] = set()
        for index, raw_visit in enumerate(raw_visits):
            visit = _map(raw_visit, f"role visit {index}")
            role_id, stage = visit.get("role_id"), visit.get("stage")
            if not isinstance(role_id, str) or not isinstance(stage, str):
                raise SystemTrajectoryError("role visit lacks identity")
            execution = _map(visit.get("execution_receipt"), "role execution")
            contacts = []
            for contact_index, raw_contact in enumerate(_seq(execution.get("contacts"), "role contacts")):
                contact, request, response, use = join_native_role_contact_response(
                    sample_id=sid, role_id=role_id, contact=raw_contact,
                    trace_records=trace, label=f"role {index} contact {contact_index}",
                )
                request_id = contact["request_id"]
                if request_id in request_ids:
                    raise SystemTrajectoryError("role visits repeat a request")
                request_ids.add(request_id)
                payload = _map(request.get("payload"), "request payload")
                contacts.append({
                    **contact,
                    "request_record_id": f"{request_id}/request",
                    "request_record_sha256": _hash(request),
                    "request_payload_sha256": _hash(payload),
                    "response_record_id": f"{request_id}/response",
                    "response_record_sha256": _hash(response),
                    "use_record_id": f"{request_id}/native-role-contact",
                    "use_record_sha256": _hash(use),
                    "wire_response": (
                        _ref(trace[f"{request_id}/wire-response"], record_id=f"{request_id}/wire-response")
                        if f"{request_id}/wire-response" in trace else
                        {"status": "unavailable_in_source"}
                    ),
                })
            visits.append({
                "index": index, "role_id": role_id, "stage": stage,
                "interrupted": index == len(raw_visits) - 1 and episode.get("interrupted_role") is not None,
                "receipt_sha256": _hash(visit), "contacts": contacts,
            })
        diag = _map(diagnostic_rows[sid], "diagnostic row")
        tool_events = []
        for event in _seq(diag.get("native_tool_events"), "native tool events"):
            item = _map(event, "native tool event")
            record_id = item.get("record_id")
            if record_id not in trace:
                raise SystemTrajectoryError("diagnostic tool event is missing from trace")
            tool_events.append({**item, "trace_record_sha256": _hash(trace[record_id])})
        disposition = delivery.terminal_disposition
        normaliser = episode.get("deliver_normaliser")
        if normaliser is not None:
            normaliser = _map(normaliser, "delivery normaliser")
        final = _map(delivery.final_contact, "delivered final contact")
        row = {
            "sample_id": sid,
            "source": {
                "run_id": source.plan.run_id,
                "attempt_id": source.plan.attempt_id,
                "config_hash": source.composed.config_hash,
                "phase_artifact_sha256": source.phase_artifact_sha256,
            },
            "source_phase_result_sha256": _hash(phase),
            "source_episode_receipt_sha256": _hash(episode),
            "role_visits": visits,
            "planner_routes": [
                {"index": i, "action": route.get("action"), "revision_count": route.get("revision_count"),
                 "role_visit_index": route.get("role_visit_index"),
                 "legal": route.get("legal"), "disposition": route.get("disposition"),
                 "receipt_sha256": _hash(route)}
                for i, route in enumerate(_seq(episode.get("planner_routes"), "planner routes"))
            ],
            "delivery": {
                "kind": delivery.kind,
                "final_contact": {key: final[key] for key in ("agent_contact_id", "request_id", "request_sha256", "response_sha256", "response_text_sha256")},
                "solver_receipt_sha256": _hash(delivery.solver_receipt) if delivery.solver_receipt is not None else None,
                "terminal_disposition_sha256": _hash(disposition) if disposition is not None else None,
                "terminal_reason": disposition.get("reason") if isinstance(disposition, Mapping) else None,
                "react_exhaustion_sha256": _hash(delivery.react_exhaustion) if delivery.react_exhaustion is not None else None,
                "normalisation": ({
                    "status": "recorded", "receipt_sha256": _hash(normaliser),
                    "normaliser_id": normaliser.get("normaliser_id"),
                    "raw_input_sha256": normaliser.get("input_sha256"),
                    "delivered_output_sha256": normaliser.get("output_sha256"),
                } if normaliser is not None else {"status": "unavailable_in_source"}),
            },
            "episode_events": _episode_events(episode),
            "tool_events": tool_events,
            "phase_fields": _phase_fields(phase),
            "trace_records": _trace_refs(trace, sid, request_ids),
            "final_output": {
                "record_sha256": _hash(output),
                "delivered_text_sha256": hashlib.sha256(output["text"].encode("utf-8")).hexdigest(),
                "request_id": output.get("request_id"),
                "request_sha256": output.get("request_sha256"),
                "response_sha256": output.get("response_sha256"),
                "response_text_sha256": output.get("response_text_sha256"),
            },
        }
        choice = _system_policy_choice(
            sid=sid, phase=phase, episode=episode, output=output, visits=visits, trace=trace,
            related=policy_records.get(sid, {}), trace_order=policy_trace_order,
        )
        if choice is not None:
            row["system_policy_decision"] = choice
        proposal = _candidate_proposal(sid=sid, episode=episode, output=output, trace=trace)
        if proposal is not None:
            row["candidate_proposal"] = proposal
        row["trajectory_sha256"] = content_hash(row)
        rows.append(row)
    manifest = _map(source.bundle.manifest, "verified run manifest")
    document = {
        "schema": SCHEMA,
        "source": {
            "run_id": source.plan.run_id, "attempt_id": source.plan.attempt_id,
            "manifest_content_sha256": _hash(manifest),
            "phase_artifact_sha256": source.phase_artifact_sha256,
            "outputs_sha256": _map(manifest.get("outputs"), "manifest outputs").get("sha256"),
            "config_hash": source.composed.config_hash,
        },
        "sample_ids": list(ids), "trajectories": rows,
    }
    document["document_sha256"] = content_hash(document)
    return document
