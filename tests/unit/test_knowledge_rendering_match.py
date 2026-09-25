"""Prove matched evidence on full native graphs with optional lookup authority."""

import pytest

from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_target_knowledge_tools import _binding, _config, TARGET


@pytest.mark.usefixtures("_spawn_live_matching_process")
def test_native_tool_availability_preserves_all_role_evidence_with_explicit_plain(
    tmp_path, monkeypatch,
):
    import test_native_episode_runner as episode

    binding = _binding(tmp_path / "stores", monkeypatch)
    builder, shared_run = episode.build_phase_tools, episode.run_speech_native_agent_loop

    def tools(config, *args, **kwargs):
        return builder(
            {**config, **_config(), "knowledge_value_rendering": "canonical-plain-v1"},
            *args, **kwargs, knowledge_stores=binding,
        )

    monkeypatch.setattr(episode, "_knowledge_snapshot", lambda: binding.composite_snapshot)
    monkeypatch.setattr(episode, "TASK_CONTRACT_TOOL", TARGET)
    monkeypatch.setattr(episode, "build_phase_tools", tools)
    captured = {}
    for enabled in (False, True):
        harness = episode._ActualEpisodeHarness(
            tmp_path / ("tools" if enabled else "control"),
            sample_count=1, max_revisions=1, max_contacts=8,
            planner_actions=("REVISE", "ACCEPT"), reviewer_task_tool=enabled,
        )
        # No synthetic tool call is requested. Availability itself must not
        # change prior evidence at Perception, Solver, review or revision.
        ordinary_output = harness._output
        harness._output = lambda key: (
            f"reviewer-analysis:{key[0]}:visit:{key[2]}"
            if key[1] == "reviewer" else ordinary_output(key)
        )
        requests = []
        gate = harness.request_gate

        def request_gate(request):
            requests.append(request.as_payload())
            return gate(request)

        harness.request_gate = request_gate

        def run(**kwargs):
            return shared_run(
                **kwargs,
                bootstrap_facet_ids=tuple(f.facet_id for f in binding.composite_snapshot.facets),
                bootstrap_value_ids=tuple(v.value_id for v in binding.composite_snapshot.values),
                **({"knowledge_value_renderer": harness.tools_for_phase.render_values}
                   if enabled else {}),
            )

        monkeypatch.setattr(episode, "run_speech_native_agent_loop", run)
        try:
            summary = harness.run()
        finally:
            closed = harness.close()
        assert closed["request_count"] == 7
        assert closed["cost"]["tool_calls"] == 0
        assert summary.results[0].final_response_text == "solver-answer:s1:visit:2"
        captured[enabled] = requests

    assert len(captured[False]) == len(captured[True]) == 7
    for control, tools in zip(captured[False], captured[True], strict=True):
        assert control["supplied_evidence"] == tools["supplied_evidence"]
        assert control["speech_packet_sha256"] == tools["speech_packet_sha256"]
        assert all("[knowledge store=" not in item["content"]
                   for item in tools["supplied_evidence"])
    assert not captured[False][2]["tool_schemas"]
    assert captured[True][2]["tool_schemas"][0]["function"]["name"] == TARGET
