from __future__ import annotations

import copy

import pytest

from speech_aware_evidence_acquisition.analysis.native_query_state import (
    NativeQueryStateReplayError,
    reconstruct_verified_native_query_states,
)
from speech_aware_evidence_acquisition.rails.knowledge import QueryState
from speech_aware_evidence_acquisition.rails.native_episode_config import (
    NativeEpisodeRunBinding,
)
from speech_aware_evidence_acquisition.rails.runner import run_speech_native_agent_loop
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_episode_runner import (
    _ActualEpisodeHarness,
    _controller_registry,
    _knowledge_snapshot,
)


def _run(harness: _ActualEpisodeHarness, *, supplied: bool):
    binding = NativeEpisodeRunBinding(
        config=harness.config,
        program=harness.program,
        material_for_phase=harness.material_for_phase,
        render_request=harness.transport.render_request,
        request_gate=harness.request_gate,
        tools_for_phase=harness.tools_for_phase,
    )
    return run_speech_native_agent_loop(
        data_root=harness.world.data_root,
        plan=harness.plan,
        adapter=harness.adapter,
        core_client=harness.client,
        split_id="all",
        knowledge_snapshot=_knowledge_snapshot(),
        speech_packet_bindings=harness.speech_bindings,
        controller_policy_id=harness.program.program_id,
        controller_registry=_controller_registry(
            harness.program.program_id, lambda _sample_id: object()
        ),
        bootstrap_value_ids=("value:dim-light",) if supplied else (),
        max_contacts=harness.config.max_contacts,
        slot_count=len(harness.samples),
        queue_depth=len(harness.samples),
        trace_sink=harness.trace,
        agent_executor_id="openjiuwen-workflow-v1",
        decoding_params={"temperature": 0, "max_tokens": 64},
        native_episode_binding=binding,
    )


def _inputs(summary, trace):
    phase = summary.results[0].as_json()
    sample_id = phase["sample_id"]
    return {
        "sample_ids": (sample_id,),
        "controller_policy_id": summary.controller_policy_id,
        "phase_results": {sample_id: phase},
        "output_rows": {
            sample_id: {
                "sample_id": sample_id,
                "text": phase["final_response_text"],
                "native_episode_receipt": phase["native_episode_receipt"],
            }
        },
        "trace_records": {
            record_id: payload for _channel, record_id, payload in trace.records
        },
    }


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("supplied", (False, True))
def test_replays_actual_native_contact_states_with_empty_or_supplied_knowledge(
    tmp_path, supplied
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    try:
        summary = _run(harness, supplied=supplied)
        inputs = _inputs(summary, harness.trace)
        if supplied:
            prefix = f"{summary.results[0].sample_id}/agent-loop/"
            namespaced = (
                f"{summary.results[0].sample_id}/"
                f"{summary.controller_policy_id}/agent-loop/"
            )
            for record_id in tuple(inputs["trace_records"]):
                if record_id.startswith(prefix):
                    inputs["trace_records"][
                        record_id.replace(prefix, namespaced, 1)
                    ] = inputs["trace_records"].pop(record_id)
        states = reconstruct_verified_native_query_states(**inputs)
    finally:
        harness.close()

    result = summary.results[0]
    request_ids = [
        contact["request_id"]
        for visit in result.native_episode_receipt["role_visits"]
        for contact in visit["execution_receipt"]["contacts"]
    ]
    assert list(states) == request_ids
    assert all(
        state.retrieved_value_ids == (("value:dim-light",) if supplied else ())
        for state in states.values()
    )
    assert states[request_ids[0]] == result.initial_query_state
    assert (
        states[request_ids[-1]].content_hash() == result.contacts[-1].query_state_sha256
    )


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("changed-initial", "differs from replayed QueryState"),
        ("changed-next", "next QueryState hash"),
        ("foreign-agent-state", "another QueryState"),
        ("missing-transition", "transition count"),
        ("reordered-transitions", "wave transition differs"),
    ),
)
def test_replay_rejects_changed_missing_or_reordered_state_chain(
    tmp_path, mutation, message
):
    harness = _ActualEpisodeHarness(
        tmp_path,
        sample_count=1,
        max_revisions=0,
        max_contacts=4,
        planner_actions=("ACCEPT",),
    )
    try:
        summary = _run(harness, supplied=False)
        inputs = _inputs(summary, harness.trace)
    finally:
        harness.close()

    changed = copy.deepcopy(inputs)
    phase = changed["phase_results"]["s1"]
    org = next(
        payload
        for record_id, payload in changed["trace_records"].items()
        if record_id.endswith("/agent-loop/org")
    )
    runtime = next(
        payload
        for record_id, payload in changed["trace_records"].items()
        if record_id.endswith("/agent-loop/runtime-use")
    )
    if mutation == "changed-initial":
        phase["initial_query_state"]["retrieved_value_ids"] = ["value:forged"]
        org["org_initial_query_state"] = copy.deepcopy(phase["initial_query_state"])
        runtime["use_initial_query_state_sha256"] = QueryState.from_json(
            phase["initial_query_state"]
        ).content_hash()
    elif mutation == "changed-next":
        phase["waves"][0]["next_query_state_sha256"] = "0" * 64
        runtime["use_waves"] = copy.deepcopy(phase["waves"])
    elif mutation == "foreign-agent-state":
        phase["agent_states"][0]["source_query_state_sha256"] = "0" * 64
        org["org_agent_states"] = copy.deepcopy(phase["agent_states"])
    elif mutation == "missing-transition":
        phase["transitions"].pop(1)
        runtime["use_transitions"] = copy.deepcopy(phase["transitions"])
    else:
        phase["transitions"][0], phase["transitions"][1] = (
            phase["transitions"][1],
            phase["transitions"][0],
        )
        runtime["use_transitions"] = copy.deepcopy(phase["transitions"])

    with pytest.raises(NativeQueryStateReplayError, match=message):
        reconstruct_verified_native_query_states(**changed)
