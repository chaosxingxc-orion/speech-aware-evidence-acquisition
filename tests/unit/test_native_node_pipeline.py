"""Prove full-panel CPU prefetch and strict node inference barriers."""

import asyncio
import contextvars
import threading

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw.node_pipeline import (
    NodePipelineCoordinator,
)


async def execute(count, episode, *, group_size=20, slots=4, workers=2, events=None):
    coordinator = NodePipelineCoordinator(
        tuple(range(count)),
        ("perception", "solver", "reviewer", "planner"),
        slots=slots,
        group_size=group_size,
        prepare_workers=workers,
        event_sink=None
        if events is None
        else lambda member, event: events.append((member, event)),
    )
    errors = []

    async def one(member):
        error = None
        try:
            await episode(member, coordinator)
        except BaseException as caught:
            error = caught
            errors.append(caught)
        finally:
            coordinator.finish(member, error)

    driver = asyncio.create_task(coordinator.drive())
    await asyncio.gather(*(one(member) for member in range(count)))
    await driver
    if errors:
        raise errors[0]
    return coordinator


def test_160_jobs_prefetch_groups20_without_interleaving_node_inference():
    lock = threading.Lock()
    done = set()
    prepared = set()
    first_prepared = threading.Event()
    all_first = threading.Event()
    active = 0
    max_active = 0
    seen = []
    owner = contextvars.ContextVar("panel_job")
    events = []

    async def episode(member, coordinator):
        owner.set((member // 20, member % 20))

        def prepare(family, value):
            assert owner.get() == (member // 20, member % 20)
            if family == "solver":
                with lock:
                    assert set(range(member // 20 * 20, member // 20 * 20 + 20)) <= done
                    prepared.add(member)
                    if member < 20:
                        assert not all_first.is_set()
                        first_prepared.set()
            return f"{value}/{family}"

        value = await coordinator.prepare(
            member, "perception", lambda: prepare("perception", str(member))
        )

        def node1(slot):
            nonlocal active, max_active
            assert owner.get() == (member // 20, member % 20)
            with lock:
                active += 1
                max_active = max(max_active, active)
            if member == 159:
                assert first_prepared.wait(3), "No CPU preparation overlap"
            with lock:
                done.add(member)
                if len(done) == 160:
                    all_first.set()
                active -= 1
                seen.append((member, "perception", slot))
            return value + "/result"

        value = await coordinator.contact(member, "perception", node1)
        value = await coordinator.prepare(
            member, "solver", lambda: prepare("solver", value)
        )

        def node2(slot):
            assert all_first.is_set() and len(prepared) == 160
            assert value == f"{member}/perception/result/solver"
            with lock:
                seen.append((member, "solver", slot))
            return member

        assert await coordinator.contact(member, "solver", node2) == member

    asyncio.run(execute(160, episode, events=events))
    assert len(seen) == 320
    assert all(role == "perception" for _, role, _ in seen[:160])
    assert all(role == "solver" for _, role, _ in seen[160:])
    assert max_active <= 4
    assert {e["group_index"] for _, e in events} == set(range(8))
    assert sum(e["kind"] == "prepare" for _, e in events) == 320
    assert sum(e["kind"] == "model" for _, e in events) == 320
    for _, e in events:
        assert e["queued_ns"] <= e["started_ns"] <= e["finished_ns"]
        assert e["status"] == "completed"


def test_slow_final_preparation_is_a_real_barrier_and_slots_refill_without_wave_wait():
    second_started = threading.Event()
    fast_replacement = threading.Event()
    prepared_last = threading.Event()
    seen = []

    async def episode(member, c):
        await c.prepare(member, "solver", lambda: member)

        def first(slot):
            if member == 0:
                assert fast_replacement.wait(3), (
                    "A slow slot blocked all ready requests"
                )
            if member == 2:
                fast_replacement.set()
            seen.append((member, "solver"))

        await c.contact(member, "solver", first)

        def prepare_next():
            if member == 3:
                assert not second_started.is_set()
                prepared_last.set()
            return member

        await c.prepare(member, "reviewer", prepare_next)

        def second(slot):
            assert prepared_last.is_set()
            assert len([x for x in seen if x[1] == "solver"]) == 4
            second_started.set()

        await c.contact(member, "reviewer", second)

    asyncio.run(execute(4, episode, slots=2, group_size=2))


def test_skips_revisions_tool_continuations_and_partial_last_group():
    seen = []

    async def episode(member, c):
        async def role(name, tool=False):
            await c.prepare(member, name, lambda: member)
            await c.contact(member, name, lambda slot: seen.append((member, name)))
            if tool:
                await c.contact(member, name, lambda slot: member, "tool")
                await c.contact(member, name, lambda slot: member)

        await role("perception")
        if member == 0:
            return
        await role("solver", tool=member == 1)
        await role("reviewer")
        await role("planner")
        if member == 2:
            await role("solver")
            await role("reviewer")
            await role("planner")

    events = []
    asyncio.run(execute(5, episode, group_size=3, events=events))
    assert len(seen) == 20
    assert [
        e["round_index"] for m, e in events if m == 2 and e["kind"] == "prepare"
    ] == [0, 0, 0, 0, 1, 1, 1]
    assert sum(e["kind"] == "tool" for _, e in events) == 1


def test_preparation_failure_stops_all_future_contacts_and_drains_cpu():
    started = threading.Barrier(2)
    settled = threading.Event()
    seen = []

    async def episode(member, c):
        def prepare():
            if member < 2:
                started.wait(3)
                if member == 0:
                    raise ValueError("named CPU failure")
                settled.set()
            return member

        await c.prepare(member, "solver", prepare)
        await c.contact(member, "solver", lambda slot: seen.append(member))

    with pytest.raises(ValueError, match="named CPU failure"):
        asyncio.run(execute(8, episode, group_size=2))
    assert settled.is_set() and seen == []


def test_model_failure_drains_active_requests_and_refuses_next_stage():
    started = threading.Barrier(2)
    settled = threading.Event()
    failure_observed = threading.Event()
    seen = []

    async def episode(member, c):
        await c.prepare(member, "solver", lambda: member)

        async def release_after_failure():
            while c.failure is None:
                await asyncio.sleep(0)
            failure_observed.set()

        observer = asyncio.create_task(release_after_failure()) if member == 1 else None

        def model(slot):
            seen.append(member)
            started.wait(3)
            if member == 0:
                raise RuntimeError("named model failure")
            # The stop boundary is the scheduler observing the failure. A
            # request dispatched before that observation is already in flight.
            assert failure_observed.wait(3)
            settled.set()

        try:
            await c.contact(member, "solver", model)
        finally:
            if observer is not None:
                await observer
        await c.prepare(member, "reviewer", lambda: member)
        await c.contact(member, "reviewer", lambda slot: pytest.fail("future stage"))

    with pytest.raises(RuntimeError, match="named model failure"):
        asyncio.run(execute(8, episode, group_size=2, slots=2))
    assert set(seen) == {0, 1} and settled.is_set()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"slots": 0},
        {"slots": True},
        {"group_size": 0},
        {"group_size": True},
        {"prepare_workers": 0},
        {"prepare_workers": 9},
        {"event_sink": 3},
    ],
)
def test_invalid_configuration_fails_before_work(kwargs):
    args = dict(slots=4, group_size=20, prepare_workers=2)
    args.update(kwargs)
    with pytest.raises(ValueError):
        NodePipelineCoordinator((0, 1), ("solver",), **args)


def test_duplicate_members_and_unknown_node_refused():
    with pytest.raises(ValueError):
        NodePipelineCoordinator(
            (0, 0), ("solver",), slots=1, group_size=2, prepare_workers=1
        )

    async def episode(member, c):
        await c.prepare(member, "unknown", lambda: pytest.fail("unknown preparation"))

    with pytest.raises(ValueError, match="declared"):
        asyncio.run(execute(1, episode))


def test_contact_requires_its_prepared_role_and_does_not_guess_transition():
    async def episode(member, c):
        await c.prepare(member, "solver", lambda: member)
        await c.contact(member, "reviewer", lambda slot: pytest.fail("unprepared node"))

    with pytest.raises(ValueError, match="prepared"):
        asyncio.run(execute(2, episode))


def test_shared_executor_handles_eight_distinct20_job_members_and_original_timing():
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    jobs = [{"experiment": e, "sample": i} for e in range(8) for i in range(20)]
    events = []
    timing = []
    seen = []

    async def episode(state, contact, session, *, run_prepare):
        owner = f"run-{state['experiment']}/sample-{state['sample']}"
        for node in ("perception", "solver", "reviewer", "planner"):
            value = await run_prepare(lambda: (owner, node), prefix_family=node)
            await contact(lambda slot: seen.append((value, slot)), prefix_family=node)

    result = execute_speech_agent_workflows(
        jobs,
        episode_invoker=episode,
        branch_count=1,
        slot_count=4,
        queue_depth=16,
        workflow_timeout_seconds=10,
        node_pipeline_order=("perception", "solver", "reviewer", "planner"),
        node_pipeline_group_size=20,
        node_pipeline_prepare_workers=2,
        node_pipeline_max_jobs=160,
        node_pipeline_timing_sink=lambda s, e: events.append((s, e)),
        sample_timing_sink=lambda s, t: timing.append((s, t)),
    )
    assert result == jobs and len(seen) == 640 and len(timing) == 160
    assert [node for (_, node), _ in seen] == [
        node
        for node in ("perception", "solver", "reviewer", "planner")
        for _ in range(160)
    ]
    for state, t in timing:
        own = [e for s, e in events if s is state]
        assert len(own) == 8 and t["queue_depth"] == 160
        assert (
            t["batch_started_ns"]
            <= t["admitted_ns"]
            <= min(e["queued_ns"] for e in own)
        )
        assert max(e["finished_ns"] for e in own) <= t["finished_ns"]


@pytest.mark.parametrize(
    "extra",
    [
        {"node_pipeline_max_jobs": 1},
        {"node_pipeline_max_jobs": True},
        {"node_pipeline_group_size": 0},
        {"node_pipeline_group_size": 161},
        {"node_pipeline_prepare_workers": 0},
        {"node_batch_order": ("solver",), "node_batch_size": 1},
        {"prefix_slot_bindings": {"solver": 0}},
    ],
)
def test_shared_executor_refuses_bad_panel_envelope_before_invocation(extra):
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    async def episode(*a, **kw):
        pytest.fail("invalid pipeline invoked")

    args = dict(
        node_pipeline_order=("solver",),
        node_pipeline_group_size=20,
        node_pipeline_prepare_workers=2,
        node_pipeline_max_jobs=160,
    )
    args.update(extra)
    with pytest.raises(ValueError, match="pipeline"):
        execute_speech_agent_workflows(
            [0, 1],
            episode_invoker=episode,
            branch_count=1,
            slot_count=4,
            queue_depth=16,
            workflow_timeout_seconds=3,
            **args,
        )


def test_cpu_worker_limit_and_four_slot_concurrency_are_real():
    cpu_barrier = threading.Barrier(2)
    gpu_barrier = threading.Barrier(4)
    cpu_lock = threading.Lock()
    gpu_lock = threading.Lock()
    cpu_active = 0
    cpu_peak = 0
    gpu_active = 0
    gpu_peak = 0

    async def episode(member, c):
        def prepare():
            nonlocal cpu_active, cpu_peak
            with cpu_lock:
                cpu_active += 1
                cpu_peak = max(cpu_peak, cpu_active)
            cpu_barrier.wait(3)
            with cpu_lock:
                cpu_active -= 1
            return member

        await c.prepare(member, "solver", prepare)

        def model(slot):
            nonlocal gpu_active, gpu_peak
            with gpu_lock:
                gpu_active += 1
                gpu_peak = max(gpu_peak, gpu_active)
            gpu_barrier.wait(3)
            with gpu_lock:
                gpu_active -= 1

        await c.contact(member, "solver", model)

    asyncio.run(execute(8, episode, group_size=4))
    assert cpu_peak == 2 and gpu_peak == 4


def test_repeated_cancellation_drains_started_cpu_and_model_workers():
    async def scenario(kind):
        entered = threading.Event()
        release = threading.Event()
        settled = threading.Event()
        c = NodePipelineCoordinator(
            (0,), ("solver",), slots=1, group_size=1, prepare_workers=1
        )

        def blocking(*args):
            entered.set()
            assert release.wait(3)
            settled.set()
            return 1

        async def one():
            error = None
            try:
                await c.prepare(
                    0, "solver", blocking if kind == "prepare" else lambda: 1
                )
                await c.contact(0, "solver", blocking)
            except BaseException as caught:
                error = caught
            finally:
                c.finish(0, error)

        driver = asyncio.create_task(c.drive())
        worker = asyncio.create_task(one())
        assert await asyncio.to_thread(entered.wait, 3)
        worker.cancel()
        await asyncio.sleep(0)
        worker.cancel()
        await asyncio.sleep(0)
        assert not worker.done() and not settled.is_set()
        release.set()
        await worker
        await driver
        assert settled.is_set() and isinstance(c.failure, asyncio.CancelledError)

    asyncio.run(scenario("prepare"))
    asyncio.run(scenario("model"))


def test_async_builder_and_timing_sink_failure_stop_without_contacts():
    called = []

    async def bad_builder():
        return 1

    async def episode(member, c):
        await c.prepare(member, "solver", bad_builder)
        await c.contact(member, "solver", lambda slot: called.append(member))

    with pytest.raises(TypeError, match="synchronous"):
        asyncio.run(execute(2, episode))
    assert called == []

    async def sink_case():
        def broken(member, event):
            raise LookupError("timing evidence failed")

        c = NodePipelineCoordinator(
            (0,),
            ("solver",),
            slots=1,
            group_size=1,
            prepare_workers=1,
            event_sink=broken,
        )
        driver = asyncio.create_task(c.drive())
        try:
            with pytest.raises(LookupError, match="timing evidence failed"):
                await c.prepare(0, "solver", lambda: 1)
        finally:
            c.finish(0, c.failure)
        await driver

    asyncio.run(sink_case())


def test_empty_panel_finishes_and_unknown_contact_kind_is_refused():
    asyncio.run(execute(0, lambda *a: None))

    async def episode(member, c):
        await c.prepare(member, "solver", lambda: member)
        await c.contact(
            member, "solver", lambda slot: pytest.fail("bad kind"), "unregistered"
        )

    with pytest.raises(ValueError, match="kind"):
        asyncio.run(execute(1, episode))


@pytest.mark.parametrize("failure_at", ["prepare", "model", "timing"])
def test_shared_executor_preserves_failure_and_stops_later_stages(failure_at):
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    contacts = []
    timings = []

    def record(state, timing):
        timings.append((state, timing))
        if failure_at == "timing" and state == 0:
            raise RuntimeError("named timing failure")

    async def episode(state, contact, session, *, run_prepare):
        def prepare():
            if failure_at == "prepare" and state == 0:
                raise RuntimeError("named prepare failure")
            return state

        await run_prepare(prepare, prefix_family="solver")

        def model(slot):
            contacts.append((state, "solver"))
            if failure_at == "model" and state == 0:
                raise RuntimeError("named model failure")

        await contact(model, prefix_family="solver")
        if failure_at != "timing":
            await run_prepare(lambda: state, prefix_family="reviewer")
            await contact(
                lambda slot: contacts.append((state, "reviewer")),
                prefix_family="reviewer",
            )

    with pytest.raises(RuntimeError, match=f"named {failure_at} failure"):
        execute_speech_agent_workflows(
            list(range(8)),
            episode_invoker=episode,
            branch_count=1,
            slot_count=2,
            queue_depth=2,
            workflow_timeout_seconds=5,
            node_pipeline_order=("solver", "reviewer"),
            node_pipeline_group_size=2,
            node_pipeline_prepare_workers=2,
            node_pipeline_max_jobs=8,
            sample_timing_sink=record,
        )
    assert len(timings) == 8
    assert not any(node == "reviewer" for _, node in contacts)
    if failure_at == "prepare":
        assert contacts == []


from test_llama_server_transport import _spawn_live_matching_process  # noqa: F401,E402


@pytest.mark.parametrize("failure", [False, True])
def test_native_disk_traces_preserve_revision_requests_and_failure_evidence(
    tmp_path, failure
):
    import json
    from test_native_episode_runner import _ActualEpisodeHarness
    from speech_aware_evidence_acquisition.rails.dispatch_slot_fill import (
        parse_native_node_pipeline,
    )

    options = dict(
        sample_count=2,
        max_revisions=1,
        max_contacts=8,
        planner_actions=("REVISE", "ACCEPT"),
    )
    on = _ActualEpisodeHarness(tmp_path / "disk", **options)
    on.solver_hints_data_root = on.world.data_root
    on.node_pipeline = parse_native_node_pipeline(
        {
            "native_node_pipeline": {
                "schema": "saea-native-node-pipeline-v1",
                "node_order": ["perception", "solver", "reviewer", "planner"],
                "group_size": 1,
                "prepare_workers": 2,
                "max_jobs": 2,
                "trace_spool": {
                    "schema": "saea-native-trace-spool-v1",
                    "max_record_bytes": 1048576,
                    "max_total_bytes": 16 * 1048576,
                },
            }
        }
    )
    if failure:
        original_output = on._output

        def output(key):
            if key[1] == "reviewer":
                raise RuntimeError("synthetic reviewer contact failed")
            return original_output(key)

        on._output = output
        try:
            with pytest.raises(Exception, match="synthetic reviewer contact failed"):
                on.run()
        finally:
            on.close()
        assert len(on.dispatched) > 0
    else:
        off = _ActualEpisodeHarness(tmp_path / "memory", **options)
        try:
            got, expected = on.run(), off.run()
        finally:
            on.close()
            off.close()
        assert [r.final_response_text for r in got.results] == [
            r.final_response_text for r in expected.results
        ]
        assert {k: v["rendered"] for k, v in on.prepared.items()} == {
            k: v["rendered"] for k, v in off.prepared.items()
        }
        assert len(on.dispatched) == len(off.dispatched)
    manifests = list(tmp_path.rglob("trace-intermediates/*/*.json"))
    assert len(manifests) == 1
    receipt = json.loads(manifests[0].read_text())
    assert receipt["closed"] and receipt["written_records"] > 0
    assert receipt["read_records"] == receipt["written_records"]
    assert receipt["retained_payload_bytes"] == 0
    assert on.trace.records
