"""Independent owners rendezvous in the one existing native workflow engine."""

import contextvars
import json
import threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw.panel import (
    NativePanelMember,
    NativeWorkflowPanel,
    NativeWorkflowPanelError,
)


def members(count=8, rows=20):
    return tuple(
        NativePanelMember(
            f"run-{i}", f"attempt-{i}", tuple((f"s{j}", None) for j in range(rows))
        )
        for i in range(count)
    )


def options(episode, rows=20, total=160, **kw):
    return dict(
        episode_invoker=episode,
        branch_count=1,
        slot_count=4,
        queue_depth=16,
        workflow_timeout_seconds=10,
        node_pipeline_order=("solver", "reviewer"),
        node_pipeline_group_size=rows,
        node_pipeline_prepare_workers=2,
        node_pipeline_max_jobs=total,
        local_tool_workers=0,
        **kw,
    )


def test_eight_owners_keep_context_budgets_and_timing_across_global_stages():
    owner = contextvars.ContextVar("own-experiment")
    panel = NativeWorkflowPanel("panel", members())
    seen, clocks, events = [], [], []
    counts = [0] * 8
    lock = threading.Lock()
    submitted = threading.Barrier(8)

    def run(index):
        owner.set(index)
        states = [(f"s{j}", None) for j in range(20)]

        async def episode(state, contact, session, *, run_prepare):
            assert owner.get() == index
            for node in ("solver", "reviewer"):
                prepared = await run_prepare(
                    lambda: (owner.get(), state, node), prefix_family=node
                )
                assert prepared == (index, state, node)

                def model(slot):
                    assert owner.get() == index
                    with lock:
                        counts[index] += 1
                        assert counts[index] <= 40
                        seen.append((index, state, node, slot))

                await contact(model, prefix_family=node)

        submitted.wait(5)
        return panel.execute(
            f"run-{index}",
            f"attempt-{index}",
            states,
            job_keys=states,
            **options(
                episode,
                sample_timing_sink=lambda s, t: clocks.append((index, s, t)),
                node_pipeline_timing_sink=lambda s, e: events.append((index, s, e)),
            ),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, range(8)))
    assert all(result == [(f"s{j}", None) for j in range(20)] for result in results)
    assert counts == [40] * 8
    assert [n for _, _, n, _ in seen] == ["solver"] * 160 + ["reviewer"] * 160
    assert len(clocks) == 160 and len(events) == 640
    assert {t["batch_started_ns"] for _, _, t in clocks} == {panel.submitted_ns}
    for i, state, t in clocks:
        assert t["expected_samples"] == 20
        assert t["panel_expected_samples"] == 160
        assert t["panel_admission_index"] == i * 20 + t["admission_index"]
        assert (
            t["batch_started_ns"]
            <= t["panel_execution_started_ns"]
            <= t["admitted_ns"]
            <= t["finished_ns"]
        )
        assert t["panel_id"] == "panel"


def test_prejoin_failure_wakes_waiting_member_without_any_contact():
    panel = NativeWorkflowPanel("panel", members(2, 2))
    entered = threading.Event()
    called = []

    async def episode(*args, **kwargs):
        called.append(True)

    def run():
        entered.set()
        return panel.execute(
            "run-0",
            "attempt-0",
            [0, 1],
            job_keys=(("s0", None), ("s1", None)),
            **options(episode, 2, 4),
        )

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run)
        assert entered.wait(3)
        panel.abort(RuntimeError("member preparation failed"))
        with pytest.raises(RuntimeError, match="preparation failed"):
            future.result(3)
    assert called == []


def test_member_failure_stops_entire_panel_and_drains_active_contact():
    panel = NativeWorkflowPanel("panel", members(2, 1))
    started = threading.Barrier(2)
    drained = threading.Event()
    called = []

    def run(index):
        async def episode(state, contact, session, *, run_prepare):
            await run_prepare(lambda: state, prefix_family="solver")

            def model(slot):
                called.append((index, "solver"))
                started.wait(3)
                if index == 0:
                    raise RuntimeError("own budget exhausted")
                drained.set()

            await contact(model, prefix_family="solver")
            await run_prepare(lambda: state, prefix_family="reviewer")
            await contact(
                lambda slot: called.append((index, "reviewer")),
                prefix_family="reviewer",
            )

        return panel.execute(
            f"run-{index}",
            f"attempt-{index}",
            [object()],
            job_keys=(("s0", None),),
            **options(episode, 1, 2),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, i) for i in range(2)]
        for future in futures:
            with pytest.raises(RuntimeError, match="own budget exhausted"):
                future.result(5)
    assert drained.is_set() and sorted(called) == [(0, "solver"), (1, "solver")]


@pytest.mark.parametrize("defect", ["attempt", "roster", "schedule"])
def test_identity_or_schedule_mismatch_refuses_whole_panel(defect):
    panel = NativeWorkflowPanel("panel", members(2, 2))
    called = []

    async def episode(*args, **kwargs):
        called.append(1)

    def run(index):
        kwargs = options(episode, 2, 4)
        attempt = f"attempt-{index}"
        roster = (("s0", None), ("s1", None))
        if index == 1:
            if defect == "attempt":
                attempt = "wrong"
            if defect == "roster":
                roster = tuple(reversed(roster))
            if defect == "schedule":
                kwargs["slot_count"] = 3
        return panel.execute(
            f"run-{index}", attempt, [object(), object()], job_keys=roster, **kwargs
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(run, i) for i in range(2)]
        for future in futures:
            with pytest.raises(NativeWorkflowPanelError):
                future.result(5)
    assert called == []


def test_reused_panel_and_duplicate_identities_are_refused():
    with pytest.raises(NativeWorkflowPanelError):
        NativeWorkflowPanel("panel", (members(1, 1)[0],) * 2)
    with pytest.raises(NativeWorkflowPanelError):
        NativePanelMember("run", "attempt", (("s0", None), ("s0", None)))


from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401,E402


@pytest.mark.parametrize("disk_traces", [False, True])
def test_eight_actual_native_runtimes_keep_own_clients_rosters_traces_and_counts(
    tmp_path, monkeypatch, disk_traces
):
    from dataclasses import replace
    from test_native_episode_runner import _ActualEpisodeHarness
    import test_native_episode_runner as harness_module
    from test_flight_resume_recovery import _skeleton, _trace_lines
    from test_rails_frozen_core_client import _plan
    from speech_aware_evidence_acquisition.core import preparation_fit

    original_world = harness_module._World

    def world(*args, **kwargs):
        result = original_world(*args, **kwargs)
        result.samples = [
            replace(result.samples[i % 2], sample_id=f"s{i}") for i in range(20)
        ]
        return result

    monkeypatch.setattr(harness_module, "_World", world)
    harnesses, runtimes = [], []
    expected = members()
    panel = NativeWorkflowPanel("actual-panel", expected)
    fitted = []
    closed = []
    for i in range(8):
        h = _ActualEpisodeHarness(
            tmp_path / f"owner-{i}",
            sample_count=20,
            max_revisions=0,
            max_contacts=4,
            planner_actions=("ACCEPT",),
            arm="speech-feature-query",
            execution_plan=_plan(
                run_id=f"run-{i}", attempt_id=f"attempt-{i}", planned_model_calls=80
            ),
        )
        harnesses.append(h)
        own_material = h.material_for_phase

        def material(*args, original=own_material, owner_index=i, **kwargs):
            value = original(*args, **kwargs)
            return replace(
                value,
                instruction=value.instruction
                + f"\nIndependent experiment owner {owner_index} context.",
            )

        h.material_for_phase = material
        rt = _skeleton(h, monkeypatch)
        rt._seal_only = False
        rt._run_id, rt._attempt_id = h.plan.run_id, h.plan.attempt_id
        rt._composed.values["native_node_pipeline"] = {
            "schema": "saea-native-node-pipeline-v1",
            "node_order": ["perception", "solver", "reviewer", "planner"],
            "group_size": 20,
            "prepare_workers": 2,
            "max_jobs": 160,
        }
        if disk_traces:
            rt._composed.values["native_node_pipeline"]["trace_spool"] = {
                "schema": "saea-native-trace-spool-v1",
                "max_record_bytes": 1_048_576,
                "max_total_bytes": 64 * 1_048_576,
            }
        rt.bind_native_workflow_panel(panel)
        runtimes.append(rt)

    def fit_gate(rt, program, plan):
        i = runtimes.index(rt)
        h = harnesses[i]

        def gate(request):
            h.request_gate(request)
            key = h._material_key(h.transport.render_request(request.payload_bytes))
            fitted.append((i, key[1]))
            gate.receipts.append({"capacity_verified": False})

        gate.receipts = []
        return gate

    monkeypatch.setattr(preparation_fit, "build_native_contact_fit_gate", fit_gate)

    def run(i):
        h, rt = harnesses[i], runtimes[i]
        try:
            return rt._dispatch_phase_program(h.client, h.plan, h.program.program_id)
        except BaseException as error:
            panel.abort(error)
            raise

    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(run, range(8)))
    finally:
        closed = [h.close() for h in harnesses]
    manifests = list(tmp_path.rglob("trace-intermediates/*/*.json"))
    assert len(manifests) == (8 if disk_traces else 0)
    for manifest in manifests:
        storage = json.loads(manifest.read_text())
        assert storage["closed"] and not storage["failed"]
        assert storage["retained_payload_bytes"] == 0
        assert storage["written_records"] > 80
        assert storage["stored_bytes"] == Path(storage["path"]).stat().st_size
    assert [node for _, node in fitted] == [
        n for n in ("perception", "solver", "reviewer", "planner") for _ in range(160)
    ]
    for i, (rows, contacts, _, dispatch, _) in enumerate(results):
        assert len(rows) == 20 and contacts == 80 and closed[i]["request_count"] == 80
        assert dispatch["native_workflow_panel"]["panel_id"] == "actual-panel"
        assert dispatch["native_workflow_panel"]["member_run_id"] == f"run-{i}"
        h = harnesses[i]
        assert len(h.prepared) == len(h.dispatched) == 80
        assert all(
            f"Independent experiment owner {i} context." in json.dumps(v["rendered"])
            for v in h.prepared.values()
        )
        assert all(
            h.events.index(("fit", k)) < h.events.index(("dispatch", k))
            for k in h.prepared
        )
        records = _trace_lines(h.world.run_dir / f"{h.plan.run_id}.trace.jsonl")
        own_timing = [
            record["payload"]["use_sample_execution_timing"]
            for record in records
            if "use_sample_execution_timing" in record["payload"]
        ]
        if disk_traces:
            pipeline_events = [
                row["payload"]["use_node_pipeline_timing"]
                for row in records
                if "use_node_pipeline_timing" in row["payload"]
            ]
            assert pipeline_events
            assert all(
                event["process_memory"]["rss_bytes"] > 0 for event in pipeline_events
            )
        assert len(own_timing) == 20
        assert all(
            t["expected_samples"] == 20 and t["panel_expected_samples"] == 160
            for t in own_timing
        )


def test_completed_panel_refuses_a_second_execution_without_new_contacts():
    panel = NativeWorkflowPanel("once", members(2, 1))
    called = []

    async def episode(state, contact, session, *, run_prepare):
        await run_prepare(lambda: state, prefix_family="solver")
        await contact(lambda slot: called.append(state), prefix_family="solver")

    def run(index):
        return panel.execute(
            f"run-{index}",
            f"attempt-{index}",
            [index],
            job_keys=(("s0", None),),
            **options(episode, 1, 2),
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run, range(2))) == [[0], [1]]
    with pytest.raises(NativeWorkflowPanelError, match="repeated"):
        run(0)
    assert sorted(called) == [0, 1]


def test_runtime_rejects_non_native_owners_and_binding_after_contact():
    from types import SimpleNamespace
    from speech_aware_evidence_acquisition.core.flight.runtime import (
        FlightRuntime,
        FlightRuntimeError,
    )

    panel = NativeWorkflowPanel("panel", members(2, 1))
    rt = object.__new__(FlightRuntime)
    rt._run_id, rt._attempt_id = "run-0", "attempt-0"
    rt._seal_only = True
    with pytest.raises(FlightRuntimeError, match="seal-only"):
        rt.bind_native_workflow_panel(panel)
    rt._seal_only = False
    rt.shows_construction_targets = lambda: True
    with pytest.raises(FlightRuntimeError, match="construction"):
        rt.bind_native_workflow_panel(panel)
    rt.shows_construction_targets = lambda: False
    rt._native_node_pipeline = lambda: None
    with pytest.raises(FlightRuntimeError, match="pipeline"):
        rt.bind_native_workflow_panel(panel)
    rt._native_node_pipeline = lambda: SimpleNamespace()
    rt._attempt_id = "outside"
    with pytest.raises(FlightRuntimeError, match="outside"):
        rt.bind_native_workflow_panel(panel)
    rt._attempt_id = "attempt-0"
    rt._client = object()
    with pytest.raises(FlightRuntimeError, match="started"):
        rt.bind_native_workflow_panel(panel)
