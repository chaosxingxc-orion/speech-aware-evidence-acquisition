"""Node batching binds through the shared flight, request and custody path."""

from dataclasses import replace
from types import SimpleNamespace
import pytest
from speech_aware_evidence_acquisition.rails.dispatch_slot_fill import (
    NativeNodeBatchError,
    parse_native_node_batch,
)
from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available
from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401
from test_native_prefix_slot_binding import _semantic_output

BLOCK = {
    "schema": "saea-native-node-batch-v1",
    "node_order": ["perception", "solver", "reviewer", "planner"],
    "batch_size": 2,
}


def config():
    return SimpleNamespace(
        roles=tuple(
            SimpleNamespace(phase_id=r, max_iterations=1) for r in BLOCK["node_order"]
        ),
        relisten_json=None,
        context_policy_json=None,
    )


def test_absence_and_immutable_roundtrip():
    assert parse_native_node_batch({}) is None
    raw = {**BLOCK, "node_order": list(BLOCK["node_order"])}
    b = parse_native_node_batch({"native_node_batch": raw})
    raw["node_order"].clear()
    assert b.as_json() == BLOCK
    b.validate(config(), queue_depth=2)


@pytest.mark.parametrize(
    "raw",
    [
        None,
        {},
        True,
        {**BLOCK, "schema": "bad"},
        {**BLOCK, "extra": 1},
        {**BLOCK, "batch_size": True},
        {**BLOCK, "batch_size": 0},
        {**BLOCK, "node_order": []},
        {**BLOCK, "node_order": "solver"},
        {**BLOCK, "node_order": ["solver", "solver"]},
        {**BLOCK, "node_order": [1]},
    ],
)
def test_bad_blocks_fail_before_contacts(raw):
    with pytest.raises(NativeNodeBatchError):
        parse_native_node_batch({"native_node_batch": raw})


def test_incompatible_or_incomplete_envelopes_fail():
    with pytest.raises(NativeNodeBatchError):
        parse_native_node_batch({"native_node_batch": BLOCK, "native_prefix_slots": {}})
    b = parse_native_node_batch({"native_node_batch": BLOCK})
    with pytest.raises(NativeNodeBatchError):
        b.validate(None, queue_depth=4)
    with pytest.raises(NativeNodeBatchError):
        b.validate(config(), queue_depth=1)
    c = config()
    c.roles = c.roles[:-1]
    with pytest.raises(NativeNodeBatchError):
        b.validate(c, queue_depth=4)


def test_unscheduled_model_cleaning_refused(monkeypatch):
    from speech_aware_evidence_acquisition.rails import node_context_binding

    monkeypatch.setattr(
        node_context_binding, "node_context_cleaning_boundaries", lambda _: ("solver",)
    )
    c = config()
    c.context_policy_json = "{}"
    with pytest.raises(NativeNodeBatchError, match="cleaning"):
        parse_native_node_batch({"native_node_batch": BLOCK}).validate(c, queue_depth=4)


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("revisions", [0, 1])
def test_real_flight_request_semantics_and_terminal_custody_match_off(
    tmp_path, monkeypatch, revisions
):
    from test_flight_resume_recovery import _harness, _skeleton
    from test_dispatch_slot_fill import _rendered

    outputs = []
    for label, block in [("off", None), ("on", BLOCK)]:
        h = _harness(tmp_path, label, ("s1", "s2"), max_revisions=revisions)
        geometry = h.adapter.serving_geometry()
        monkeypatch.setattr(
            h.adapter, "serving_geometry", lambda: {**geometry, "slots": 2}
        )
        rt = _skeleton(h, monkeypatch)
        if block is not None:
            rt._composed.values["native_node_batch"] = block
        try:
            rows, contacts, _, receipt, _ = rt._dispatch_phase_program(
                h.client, h.plan, h.program.program_id
            )
        finally:
            h.close()
        assert contacts == 2 * (4 + 3 * revisions)
        if block is None:
            assert "native_node_batch" not in receipt
        else:
            assert receipt["native_node_batch"] == BLOCK
            assert "cohort" in receipt["barrier"]
        rt._output_rows = rows
        outputs.append(
            (_rendered(h), _semantic_output(rt._canonical_output_rows(h.client)))
        )
        assert all(
            h.events.index(("fit", k)) < h.events.index(("dispatch", k))
            for k in h.prepared
        )
    assert outputs[0] == outputs[1]


@pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")
@pytest.mark.parametrize("workers", [0, 1])
def test_real_reviewer_tool_continues_and_emits_node_timing(tmp_path, workers):
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
    h.node_batch = parse_native_node_batch({"native_node_batch": BLOCK})
    h.slot_count = 2
    try:
        result = h.run()
    finally:
        h.close()
    assert (
        len(result.results) == 2 and len(h.prepared) == 10 and len(h.tool_contacts) == 2
    )
    timings = [
        p["use_node_batch_contact_timing"]
        for _, _, p in h.trace.records
        if "use_node_batch_contact_timing" in p
    ]
    assert sum(t["contact_kind"] == "model" for t in timings) == 10
    assert sum(t["contact_kind"] == "tool" for t in timings) == (
        2 if workers == 0 else 0
    )
    assert all(t["queued_ns"] <= t["started_ns"] <= t["finished_ns"] for t in timings)


def test_policy_selector_cannot_change_batch_envelope():
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
    s = object.__new__(SystemEpisodePolicy)
    s._reference = ref
    with pytest.raises(SystemEpisodePolicyError, match="envelope"):
        s.assert_envelope(
            replace(
                ref, node_batch=parse_native_node_batch({"native_node_batch": BLOCK})
            )
        )


def test_flight_rejects_wrong_policy_before_preparation():
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntime,
        FlightRuntimeError,
    )

    r = object.__new__(FlightRuntime)
    r._composed = SimpleNamespace(
        values={"policy": "fixed", "native_node_batch": BLOCK}
    )
    r._adapter = SimpleNamespace(serving_geometry=lambda: {"slots": 4})
    with pytest.raises(FlightRuntimeError):
        r._native_node_batch()
