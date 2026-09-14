"""Exact request-time QueryState replay for verified native episodes.

The caller supplies phase results and trace records from an already pinned bundle
and phase artifact. This module reuses the whole-episode source join, then
replays only the state transitions emitted by the shared native runner. It does
not infer state from model-visible evidence or make a quality claim.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace

from ..core.model import FrozenCoreError
from ..core.model.native_framework_history import validate_native_framework_contact
from ..rails.errors import RailsError
from ..rails.knowledge import AgentStateArtifact, AgentStepTransition, QueryState
from .native_episode_diagnostics import (
    NativeEpisodeDiagnosticError,
    analyze_verified_native_episode_statistics,
)


class NativeQueryStateReplayError(ValueError):
    """A sealed native state chain does not reconstruct exactly."""


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise NativeQueryStateReplayError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise NativeQueryStateReplayError(f"{label} must be an ordered sequence")
    return value


def _query_state(value: object, label: str) -> QueryState:
    try:
        return QueryState.from_json(_mapping(value, label))
    except (KeyError, TypeError, ValueError, RailsError) as error:
        raise NativeQueryStateReplayError(f"{label} is invalid: {error}") from error


def _transition(value: object, label: str) -> AgentStepTransition:
    try:
        return AgentStepTransition.from_json(_mapping(value, label))
    except (KeyError, TypeError, ValueError, RailsError) as error:
        raise NativeQueryStateReplayError(f"{label} is invalid: {error}") from error


def _agent_states(value: object, label: str) -> dict[str, AgentStateArtifact]:
    rows = _sequence(value, label)
    result: dict[str, AgentStateArtifact] = {}
    for index, raw in enumerate(rows):
        try:
            state = AgentStateArtifact.from_json(_mapping(raw, f"{label}[{index}]"))
        except (KeyError, TypeError, ValueError, RailsError) as error:
            raise NativeQueryStateReplayError(
                f"{label}[{index}] is invalid: {error}"
            ) from error
        if state.state_id in result:
            raise NativeQueryStateReplayError(f"{label} repeats a state identity")
        result[state.state_id] = state
    return result


def _state_traces(
    *,
    sample_id: str,
    controller_policy_id: str,
    trace_records: Mapping[str, Mapping[str, object]],
) -> tuple[Mapping[str, object], Mapping[str, object]]:
    """Find the runner's uniquely paired ORG and runtime USE records.

    Direct runner callers retain the historical ``sample/agent-loop`` prefix;
    phase-program callers insert a namespace before ``agent-loop``. The
    payload's controller identity and exact phase-state checks below provide
    authority, so this lookup accepts both shared-runner forms without
    guessing a phase namespace.
    """

    suffix = "/agent-loop/org"
    candidates: list[tuple[str, Mapping[str, object]]] = []
    for record_id, payload in trace_records.items():
        if (
            record_id.startswith(f"{sample_id}/")
            and record_id.endswith(suffix)
            and isinstance(payload, Mapping)
            and payload.get("org_controller_policy_id") == controller_policy_id
        ):
            candidates.append((record_id[: -len("/org")], payload))
    if len(candidates) != 1:
        raise NativeQueryStateReplayError(
            f"sample {sample_id!r} must have exactly one native ORG state trace"
        )
    base, organization = candidates[0]
    runtime = trace_records.get(f"{base}/runtime-use")
    if not isinstance(runtime, Mapping):
        raise NativeQueryStateReplayError(
            f"sample {sample_id!r} lacks its paired native runtime USE state trace"
        )
    if runtime.get("use_controller_policy_id") != controller_policy_id:
        raise NativeQueryStateReplayError(
            f"sample {sample_id!r} runtime state trace has foreign controller authority"
        )
    return organization, runtime


def _native_successor(
    current: QueryState,
    transition: AgentStepTransition,
    *,
    states: Mapping[str, AgentStateArtifact],
    action_target_ref: str,
    response_text_sha256: str,
    label: str,
) -> QueryState:
    """Replay ``advance_phase_response_state`` without runtime-only objects."""

    if transition.prior_query_state_sha256 != current.content_hash():
        raise NativeQueryStateReplayError(
            f"{label} is bound to a different prior QueryState"
        )
    if transition.action_kind not in {"organize", "acquire"}:
        raise NativeQueryStateReplayError(
            f"{label} is not a shared native state-materialization transition"
        )
    expected_target_count = 1 if transition.action_kind == "organize" else 2
    if (
        len(transition.action_target_refs) != expected_target_count
        or transition.action_target_refs[0] != action_target_ref
        or not transition.new_agent_state_ids
    ):
        raise NativeQueryStateReplayError(
            f"{label} has invalid shared native materialization identity"
        )
    if (
        transition.used_value_ids
        or transition.dropped_value_ids
        or transition.used_facet_ids
        or transition.dropped_facet_ids
        or transition.dropped_agent_state_ids
        or transition.speech_packet_derivation is not None
    ):
        raise NativeQueryStateReplayError(
            f"{label} carries a delta outside shared native state materialization"
        )
    current_hash = current.content_hash()
    for state_id in transition.new_agent_state_ids:
        state = states.get(state_id)
        if state is None:
            raise NativeQueryStateReplayError(
                f"{label} introduces an unavailable agent state"
            )
        if state.source_query_state_sha256 != current_hash:
            raise NativeQueryStateReplayError(
                f"{label} introduces an agent state from another QueryState"
            )
        if state.source_response_sha256 != response_text_sha256:
            raise NativeQueryStateReplayError(
                f"{label} introduces an agent state from another response"
            )

    try:
        successor = replace(
            current,
            loop_step=current.loop_step + 1,
            visible_facet_ids=current.visible_facet_ids + transition.new_facet_ids,
            agent_state_ids=current.agent_state_ids + transition.new_agent_state_ids,
            retrieved_value_ids=(
                current.retrieved_value_ids + transition.new_value_ids
            ),
        ).validate()
    except (TypeError, ValueError, RailsError) as error:
        raise NativeQueryStateReplayError(
            f"{label} cannot materialize its successor QueryState: {error}"
        ) from error
    if transition.next_query_state_sha256 != successor.content_hash():
        raise NativeQueryStateReplayError(
            f"{label} next QueryState hash differs from the replayed state"
        )
    return successor


def _terminal_transition(
    current: QueryState, transition: AgentStepTransition, *, label: str
) -> None:
    if (
        transition.action_kind != "stop"
        or transition.prior_query_state_sha256 != current.content_hash()
        or transition.next_query_state_sha256 is not None
        or transition.action_target_refs
        or transition.new_value_ids
        or transition.used_value_ids
        or transition.dropped_value_ids
        or transition.new_agent_state_ids
        or transition.dropped_agent_state_ids
        or transition.new_facet_ids
        or transition.used_facet_ids
        or transition.dropped_facet_ids
        or transition.speech_packet_derivation is not None
    ):
        raise NativeQueryStateReplayError(
            f"{label} is not the exact terminal native stop transition"
        )


def reconstruct_verified_native_query_states(
    *,
    sample_ids: Sequence[str],
    controller_policy_id: str,
    phase_results: Mapping[str, Mapping[str, object]],
    output_rows: Mapping[str, Mapping[str, object]],
    trace_records: Mapping[str, Mapping[str, object]],
) -> Mapping[str, QueryState]:
    """Return each verified native request's exact request-time QueryState.

    The returned mapping preserves sample order and within-sample contact order.
    Empty ``retrieved_value_ids`` is a valid reconstructed state.
    """

    try:
        diagnostics = analyze_verified_native_episode_statistics(
            sample_ids=sample_ids,
            controller_policy_id=controller_policy_id,
            phase_results=phase_results,
            output_rows=output_rows,
            trace_records=trace_records,
        )
    except NativeEpisodeDiagnosticError as error:
        raise NativeQueryStateReplayError(
            f"native episode source join failed: {error}"
        ) from error
    if set(phase_results) != set(sample_ids) or set(output_rows) != set(sample_ids):
        raise NativeQueryStateReplayError(
            "native QueryState replay population must match the exact sample roster"
        )

    replayed: dict[str, QueryState] = {}
    diagnostics_by_sample = {
        str(row["sample_id"]): row for row in diagnostics["samples"]
    }
    for sample_id in sample_ids:
        phase = _mapping(phase_results[sample_id], f"phase result {sample_id!r}")
        organization, runtime = _state_traces(
            sample_id=sample_id,
            controller_policy_id=controller_policy_id,
            trace_records=trace_records,
        )
        if (
            phase.get("initial_query_state")
            != organization.get("org_initial_query_state")
            or phase.get("final_query_state")
            != organization.get("org_final_query_state")
            or phase.get("agent_states") != organization.get("org_agent_states")
            or phase.get("contacts") != runtime.get("use_contacts")
            or phase.get("waves") != runtime.get("use_waves")
            or phase.get("transitions") != runtime.get("use_transitions")
        ):
            raise NativeQueryStateReplayError(
                f"phase result {sample_id!r} differs from its verified ORG/USE state trace"
            )

        current = _query_state(
            phase.get("initial_query_state"), f"initial QueryState {sample_id!r}"
        )
        final = _query_state(
            phase.get("final_query_state"), f"final QueryState {sample_id!r}"
        )
        if (
            runtime.get("use_initial_query_state_sha256") != current.content_hash()
            or runtime.get("use_final_query_state_sha256") != final.content_hash()
        ):
            raise NativeQueryStateReplayError(
                f"runtime QueryState hashes differ for {sample_id!r}"
            )
        states = _agent_states(phase.get("agent_states"), f"agent states {sample_id!r}")
        if any(state_id not in states for state_id in current.agent_state_ids):
            raise NativeQueryStateReplayError(
                f"initial QueryState {sample_id!r} names an unavailable agent state"
            )

        waves = _sequence(phase.get("waves"), f"waves {sample_id!r}")
        contact_records = _sequence(
            phase.get("contacts"), f"contact records {sample_id!r}"
        )
        transitions = _sequence(phase.get("transitions"), f"transitions {sample_id!r}")
        contacts = _sequence(
            diagnostics_by_sample[sample_id].get("model_contacts"),
            f"verified contacts {sample_id!r}",
        )
        if len(waves) != len(contacts) or len(contact_records) != len(contacts):
            raise NativeQueryStateReplayError(
                f"native wave/contact-record/receipt count differs for {sample_id!r}"
            )
        if len(transitions) != len(waves) + 1:
            raise NativeQueryStateReplayError(
                f"native transition count differs for {sample_id!r}"
            )

        for index, (raw_wave, raw_record, raw_contact) in enumerate(
            zip(waves, contact_records, contacts, strict=True)
        ):
            wave = _mapping(raw_wave, f"wave {sample_id!r}[{index}]")
            record = _mapping(raw_record, f"contact record {sample_id!r}[{index}]")
            contact = _mapping(raw_contact, f"contact {sample_id!r}[{index}]")
            plans = _sequence(
                wave.get("contact_plans"), f"wave plans {sample_id!r}[{index}]"
            )
            if len(plans) != 1:
                raise NativeQueryStateReplayError(
                    f"native wave {sample_id!r}[{index}] must contain one contact"
                )
            plan = _mapping(plans[0], f"wave plan {sample_id!r}[{index}]")
            current_hash = current.content_hash()
            if (
                wave.get("wave_index") != index
                or wave.get("fanout_semantics") != "single"
                or wave.get("query_state_sha256") != current_hash
                or wave.get("speech_packet_sha256") != current.speech_packet_sha256
                or plan.get("query_state_sha256") != current_hash
                or plan.get("contact_id") != contact.get("agent_contact_id")
                or record.get("plan") != plan
                or record.get("query_state_sha256") != current_hash
                or record.get("speech_packet_sha256") != current.speech_packet_sha256
            ):
                raise NativeQueryStateReplayError(
                    f"native wave {sample_id!r}[{index}] differs from replayed QueryState"
                )
            request_id = contact.get("request_id")
            if (
                not isinstance(request_id, str)
                or not request_id
                or request_id in replayed
            ):
                raise NativeQueryStateReplayError(
                    f"native contact {sample_id!r}[{index}] has an invalid request ID"
                )
            request = _mapping(
                trace_records.get(f"{request_id}/request"),
                f"request trace {request_id!r}",
            )
            payload = _mapping(
                request.get("payload"), f"request payload {request_id!r}"
            )
            try:
                framework = validate_native_framework_contact(payload)
            except (FrozenCoreError, KeyError, TypeError, ValueError) as error:
                raise NativeQueryStateReplayError(
                    f"native request {request_id!r} has invalid framework custody: {error}"
                ) from error
            if framework is None or framework[0].get("contact_id") != plan.get(
                "contact_id"
            ):
                raise NativeQueryStateReplayError(
                    f"native request {request_id!r} differs from its wave contact"
                )
            # The request has no top-level QueryState hash. Bind its actual
            # speech descriptor and ordered state history to the replayed wave.
            query_parts = [
                row for row in _sequence(
                    payload.get("speech_feature_parts"), "native speech descriptors"
                )
                if isinstance(row, Mapping) and row.get("role") == "query"
            ]
            history_states = [
                row for row in _sequence(payload.get("history"), "native history")
                if isinstance(row, Mapping) and row.get("role") == "agent_state"
            ]
            if (
                current.query_sample_id != sample_id
                or payload.get("query_source") != current.query_source
                or payload.get("speech_packet_sha256") != current.speech_packet_sha256
                or query_parts != [{
                    "packet_id": current.speech_packet_id,
                    "sha256": current.speech_packet_sha256,
                    "role": "query",
                }]
                or tuple(row.get("state_id") for row in history_states)
                != current.agent_state_ids
                or any(
                    row.get("state_kind") != states[row["state_id"]].state_kind
                    for row in history_states
                )
            ):
                raise NativeQueryStateReplayError(
                    f"native request {request_id!r} differs from replayed speech or history"
                )
            replayed[request_id] = current

            if wave.get("transition") != transitions[index]:
                raise NativeQueryStateReplayError(
                    f"native wave transition differs at {sample_id!r}[{index}]"
                )
            step = _transition(transitions[index], f"transition {sample_id!r}[{index}]")
            contract = framework[0]
            current = _native_successor(
                current,
                step,
                states=states,
                action_target_ref=(
                    f"{controller_policy_id}:{contract['role_id']}:{plan['contact_id']}"
                ),
                response_text_sha256=str(record["response_sha256"]),
                label=f"transition {sample_id!r}[{index}]",
            )
            if wave.get("next_query_state_sha256") != current.content_hash():
                raise NativeQueryStateReplayError(
                    f"wave {sample_id!r}[{index}] next QueryState hash differs"
                )

        if current != final:
            raise NativeQueryStateReplayError(
                f"final QueryState {sample_id!r} differs from replayed state"
            )
        if tuple(current.agent_state_ids) != tuple(states):
            raise NativeQueryStateReplayError(
                f"final QueryState {sample_id!r} does not bind the exact agent-state order"
            )
        terminal = _transition(transitions[-1], f"terminal transition {sample_id!r}")
        _terminal_transition(
            current, terminal, label=f"terminal transition {sample_id!r}"
        )

    return replayed


__all__ = [
    "NativeQueryStateReplayError",
    "reconstruct_verified_native_query_states",
]
