"""The stage scheduler must use the original role builder and metered client."""

from dataclasses import replace
from types import SimpleNamespace

import pytest
from speech_aware_evidence_acquisition.rails.dispatch_slot_fill import (
    NativeNodePipelineError,
    parse_native_node_pipeline,
)
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_prefix_slot_binding import _semantic_output

BLOCK = {
    "schema": "saea-native-node-pipeline-v1",
    "node_order": ["perception", "solver", "reviewer", "planner"],
    "group_size": 2,
    "prepare_workers": 2,
    "max_jobs": 160,
}


def config():
    return SimpleNamespace(
        roles=tuple(
            SimpleNamespace(phase_id=r, max_iterations=1) for r in BLOCK["node_order"]
        ),
        relisten_json=None,
        context_policy_json=None,
    )


def test_absence_and_roundtrip_do_not_mutate_policy_fields():
    assert parse_native_node_pipeline({}) is None
    raw = {**BLOCK, "node_order": list(BLOCK["node_order"])}
    parsed = parse_native_node_pipeline({"native_node_pipeline": raw})
    raw["node_order"].clear()
    assert parsed.as_json() == BLOCK
    parsed.validate(config())


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        True,
        {**BLOCK, "schema": "bad"},
        {**BLOCK, "extra": 1},
        {**BLOCK, "group_size": 0},
        {**BLOCK, "max_jobs": True},
        {**BLOCK, "prepare_workers": 9},
        {**BLOCK, "node_order": []},
        {**BLOCK, "node_order": ["solver", "solver"]},
    ],
)
def test_bad_configuration_refused(raw):
    with pytest.raises(NativeNodePipelineError):
        parse_native_node_pipeline({"native_node_pipeline": raw})


@pytest.mark.parametrize("other", ["native_prefix_slots", "native_node_batch"])
def test_conflicting_scheduler_refused(other):
    with pytest.raises(NativeNodePipelineError):
        parse_native_node_pipeline({"native_node_pipeline": BLOCK, other: {}})


def test_incomplete_roles_and_hidden_model_preparation_refused(monkeypatch):
    from speech_aware_evidence_acquisition.rails import node_context_binding

    b = parse_native_node_pipeline({"native_node_pipeline": BLOCK})
    with pytest.raises(NativeNodePipelineError):
        b.validate(None)
    c = config()
    c.roles = c.roles[:-1]
    with pytest.raises(NativeNodePipelineError):
        b.validate(c)
    c = config()
    c.context_policy_json = "{}"
    monkeypatch.setattr(
        node_context_binding, "node_context_cleaning_boundaries", lambda _: ("solver",)
    )
    with pytest.raises(NativeNodePipelineError, match="cleaning"):
        b.validate(c)


@pytest.mark.parametrize("revisions", [0, 1])
def test_actual_flight_same_requests_outputs_fit_before_dispatch_and_omni_custody(
    tmp_path, monkeypatch, revisions
):
    from test_flight_resume_recovery import _harness, _skeleton
    from test_dispatch_slot_fill import _rendered

    result = []
    for label, block in [("off", None), ("on", BLOCK)]:
        h = _harness(tmp_path, label, ("s1", "s2"), max_revisions=revisions)
        geometry = h.adapter.serving_geometry()
        monkeypatch.setattr(
            h.adapter, "serving_geometry", lambda: {**geometry, "slots": 2}
        )
        rt = _skeleton(h, monkeypatch)
        if block is not None:
            rt._composed.values["native_node_pipeline"] = block
        try:
            rows, contacts, _, receipt, _ = rt._dispatch_phase_program(
                h.client, h.plan, h.program.program_id
            )
        finally:
            h.close()
        assert contacts == 2 * (4 + 3 * revisions)
        if block is None:
            assert "native_node_pipeline" not in receipt
        else:
            assert receipt["native_node_pipeline"] == block
            assert "panel" in receipt["barrier"]
        rt._output_rows = rows
        result.append(
            (_rendered(h), _semantic_output(rt._canonical_output_rows(h.client)))
        )
        assert all(
            h.events.index(("fit", k)) < h.events.index(("dispatch", k))
            for k in h.prepared
        )
    assert result[0] == result[1]


@pytest.mark.parametrize("workers", [0, 1])
def test_actual_role_tool_branch_uses_metered_contacts_not_cpu_prefetch(
    tmp_path, workers
):
    from test_native_episode_runner import _ActualEpisodeHarness

    h = _ActualEpisodeHarness(
        tmp_path,
        sample_count=2,
        max_revisions=0,
        max_contacts=5,
        planner_actions=("ACCEPT",),
        reviewer_task_tool=True,
    )
    h.config = replace(h.config, local_tool_workers=workers)
    h.node_pipeline = parse_native_node_pipeline({"native_node_pipeline": BLOCK})
    h.slot_count = 2
    try:
        result = h.run()
    finally:
        h.close()
    assert (
        len(result.results) == 2 and len(h.prepared) == 10 and len(h.tool_contacts) == 2
    )
    timings = [
        p["use_node_pipeline_timing"]
        for _, _, p in h.trace.records
        if "use_node_pipeline_timing" in p
    ]
    assert sum(e["kind"] == "prepare" for e in timings) == 8
    assert sum(e["kind"] == "model" for e in timings) == 10
    assert sum(e["kind"] == "tool" for e in timings) == (2 if workers == 0 else 0)
    assert all(e["slot_id"] is None for e in timings if e["kind"] == "prepare")


def test_policy_selector_cannot_change_pipeline_envelope():
    from speech_aware_evidence_acquisition.rails.system_episode_policy import (
        SystemEpisodePolicy,
        SystemEpisodePolicyError,
    )
    from speech_aware_evidence_acquisition.rails.native_episode_config import (
        NativeEpisodeRunBinding,
    )

    c = config()
    c.max_contacts = 4
    c.local_tool_workers = 0
    ref = NativeEpisodeRunBinding(
        config=c,
        program=SimpleNamespace(max_contacts=4),
        material_for_phase=None,
        render_request=None,
        request_gate=None,
    )
    selector = object.__new__(SystemEpisodePolicy)
    selector._reference = ref
    with pytest.raises(SystemEpisodePolicyError, match="envelope"):
        selector.assert_envelope(
            replace(
                ref,
                node_pipeline=parse_native_node_pipeline(
                    {"native_node_pipeline": BLOCK}
                ),
            )
        )


def test_unprepared_relisten_is_refused_before_dispatch():
    c = config()
    c.relisten_json = "{}"
    with pytest.raises(NativeNodePipelineError, match="relisten"):
        parse_native_node_pipeline({"native_node_pipeline": BLOCK}).validate(c)
