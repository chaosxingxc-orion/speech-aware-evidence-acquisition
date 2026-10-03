"""Verify bounded node batches on the existing native OpenJiuwen executor."""

import asyncio
import threading

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

pytestmark = pytest.mark.skipif(
    not openjiuwen_available(), reason="OpenJiuwen unavailable"
)


def run(states, episode, *, size=4, slots=2, events=None, timing=None, **kwargs):
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    return execute_speech_agent_workflows(
        states,
        episode_invoker=episode,
        branch_count=1,
        slot_count=slots,
        queue_depth=8,
        workflow_timeout_seconds=5,
        node_batch_order=("perception", "solver", "reviewer", "planner"),
        node_batch_size=size,
        node_batch_timing_sink=(
            None if events is None else lambda s, e: events.append((s, e))
        ),
        sample_timing_sink=timing,
        **kwargs,
    )


@pytest.mark.parametrize("slots", [2, 4])
def test_each_node_uses_all_slots_then_feeds_its_own_sample_to_next_node(slots):
    seen = []
    barrier = threading.Barrier(slots)

    async def episode(state, contact, _session):
        value = str(state)
        for role in ("perception", "solver", "reviewer", "planner"):

            def compute(slot):
                barrier.wait(2)
                seen.append((state, role, slot, value))
                return value + "/" + role

            value = await contact(compute, prefix_family=role)
        assert value == str(state) + "/perception/solver/reviewer/planner"

    assert run(range(4), episode, slots=slots) == list(range(4))
    assert [r for _, r, _, _ in seen] == [
        r for r in ("perception", "solver", "reviewer", "planner") for _ in range(4)
    ]
    for r in ("perception", "solver", "reviewer", "planner"):
        assert {sl for _, role, sl, _ in seen if role == r} == set(range(slots))


def test_conditional_tools_revisions_and_early_completion_do_not_deadlock():
    seen = []

    async def episode(state, contact, _session):
        async def call(role):
            await contact(lambda slot: seen.append((state, role)), prefix_family=role)

        await call("perception")
        if state == 0:
            return
        await call("solver")
        if state == 1:
            await asyncio.sleep(0.001)
            await call("solver")
        await call("reviewer")
        await call("planner")
        if state == 2:
            await call("solver")
            await call("reviewer")
            await call("planner")

    run([0, 1, 2], episode)
    assert [r for _, r in seen] == ["perception"] * 3 + ["solver"] * 3 + [
        "reviewer"
    ] * 2 + ["planner"] * 2 + ["solver", "reviewer", "planner"]


def test_cohorts_are_bounded_and_each_finishes_before_next_admission():
    seen = []

    async def episode(state, contact, _session):
        for role in ("perception", "solver"):
            await contact(lambda slot: seen.append((state, role)), prefix_family=role)

    run(range(5), episode, size=2)
    assert seen == [
        (0, "perception"),
        (1, "perception"),
        (0, "solver"),
        (1, "solver"),
        (2, "perception"),
        (3, "perception"),
        (2, "solver"),
        (3, "solver"),
        (4, "perception"),
        (4, "solver"),
    ]


def test_failure_stops_queued_contacts_and_next_cohort_but_settles_active_workers():
    started = threading.Barrier(2)
    settled = threading.Event()
    seen = []

    async def episode(state, contact, _session):
        def model(slot):
            seen.append(state)
            started.wait(2)
            if state == 0:
                raise RuntimeError("synthetic failed contact")
            settled.set()

        await contact(model, prefix_family="solver")
        await contact(
            lambda slot: pytest.fail("post-failure request"), prefix_family="reviewer"
        )

    with pytest.raises(RuntimeError, match="synthetic failed contact"):
        run(range(6), episode)
    assert sorted(seen) == [0, 1] and settled.is_set()


def test_failure_before_first_contact_unblocks_the_waiting_cohort():
    async def episode(state, contact, _session):
        if state == 1:
            raise ValueError("preparation failed")
        await contact(
            lambda slot: pytest.fail("no request after preparation failure"),
            prefix_family="solver",
        )

    with pytest.raises(ValueError, match="preparation failed"):
        run(range(3), episode)


def test_local_tools_run_between_contacts_without_cross_sample_state():
    seen = []

    async def episode(state, contact, _session, *, run_local):
        value = await contact(lambda slot: state, prefix_family="solver")
        value = await run_local(lambda: value + 10)
        assert value == state + 10
        await contact(lambda slot: seen.append((state, value)), prefix_family="solver")
        await contact(lambda slot: state, prefix_family="reviewer")

    run(range(4), episode, local_tool_workers=2)
    assert sorted(seen) == [(i, i + 10) for i in range(4)]


def test_timing_keeps_node_wait_and_original_sample_boundaries():
    events = []
    samples = []

    async def episode(state, contact, _session):
        for role in ("solver", "reviewer"):
            await contact(lambda slot: state, prefix_family=role)

    run(range(3), episode, events=events, timing=lambda s, t: samples.append((s, t)))
    assert len(events) == 6 and len(samples) == 3
    for state, e in events:
        assert e["queued_ns"] <= e["started_ns"] <= e["finished_ns"]
        assert e["status"] == "completed"
        st = next(t for s, t in samples if s == state)
        assert (
            st["admitted_ns"] <= e["queued_ns"] <= e["finished_ns"] <= st["finished_ns"]
        )
    assert all(e["cohort_index"] == 0 for _, e in events)


def test_invalid_role_is_refused_before_any_callback():
    async def episode(_state, contact, _session):
        await contact(
            lambda slot: pytest.fail("invalid role callback"), prefix_family="unknown"
        )

    with pytest.raises(ValueError, match="node batch"):
        run([0], episode)


@pytest.mark.parametrize("size", [0, -1, True, 1.5, 9])
def test_invalid_cohort_bound_rejected_without_work(size):
    async def episode(*a):
        pytest.fail("bad bound invoked workflow")

    with pytest.raises(ValueError, match="node batch"):
        run([], episode, size=size)


def test_node_batches_cannot_combine_with_permanent_role_slots():
    async def episode(*a):
        pytest.fail("incompatible schedulers")

    with pytest.raises(ValueError, match="node batch"):
        run([], episode, prefix_slot_bindings={"solver": 0})


def test_empty_roster_adds_no_contacts():
    async def episode(*a):
        pytest.fail("empty roster")

    assert run([], episode) == []


def test_repeated_active_cancellation_drains_before_returning_and_never_advances():
    started = threading.Event()
    release = threading.Event()
    settled = threading.Event()

    async def episode(state, contact, _session):
        def model(slot):
            started.set()
            assert release.wait(2)
            settled.set()

        task = asyncio.create_task(contact(model, prefix_family="solver"))
        while not started.is_set():
            await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert settled.is_set()

    with pytest.raises(asyncio.CancelledError):
        run([0], episode)
    assert settled.is_set()


def test_queued_cancellation_aborts_before_any_worker_is_submitted():
    async def episode(state, contact, _session):
        if state == 0:
            task = asyncio.create_task(
                contact(
                    lambda slot: pytest.fail("cancelled work"), prefix_family="solver"
                )
            )
            await asyncio.sleep(0)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            await asyncio.sleep(0.01)
            await contact(
                lambda slot: pytest.fail("aborted cohort"), prefix_family="solver"
            )

    with pytest.raises(asyncio.CancelledError):
        run([0, 1], episode)


def test_context_variables_are_copied_from_each_sample_not_the_batch_driver():
    import contextvars

    token = contextvars.ContextVar("test_node_batch_context")

    async def episode(state, contact, _session):
        token.set(state)
        for role in ("solver", "reviewer"):
            assert await contact(lambda slot: token.get(), prefix_family=role) == state

    run(range(4), episode)


def test_timing_sink_failure_stops_followup_calls():
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )

    def sink(*_):
        raise RuntimeError("timing failed")

    async def episode(state, contact, _session):
        await contact(lambda slot: state, prefix_family="solver")
        await contact(
            lambda slot: pytest.fail("after sink failure"), prefix_family="reviewer"
        )

    with pytest.raises(RuntimeError, match="timing failed"):
        execute_speech_agent_workflows(
            [0],
            episode_invoker=episode,
            branch_count=1,
            slot_count=1,
            queue_depth=1,
            workflow_timeout_seconds=5,
            node_batch_order=("solver", "reviewer"),
            node_batch_size=1,
            node_batch_timing_sink=sink,
        )
