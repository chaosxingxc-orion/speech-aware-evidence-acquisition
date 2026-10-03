"""Exercise optional prefix-family slot routing on the shared executor."""
import asyncio
import threading

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

pytestmark = pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")


def _run(states, episode, assignments, *, slots=2):
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import execute_speech_agent_workflows
    return execute_speech_agent_workflows(
        states, episode_invoker=episode, branch_count=1, slot_count=slots,
        queue_depth=8, workflow_timeout_seconds=10, prefix_slot_bindings=assignments,
    )


def test_distinct_prefixes_return_to_their_reserved_slots_across_samples():
    seen = []
    prefixes = {"solver-v1": "Solver instructions", "reviewer-v1": "Different reviewer instructions"}

    async def episode(state, run_contact, _session):
        for key in ("solver-v1", "reviewer-v1", "solver-v1"):
            text = prefixes[key] + f"; sample={state}"
            await run_contact(lambda slot: seen.append((state, key, slot, text)), prefix_family=key)

    assert _run([0, 1, 2], episode, {"solver-v1": 0, "reviewer-v1": 1}) == [0, 1, 2]
    assert len(seen) == 9
    assert all(slot == (0 if key == "solver-v1" else 1) for _, key, slot, _ in seen)
    assert all(text == prefixes[key] + f"; sample={state}" for state, key, _, text in seen)


def test_same_family_serializes_but_different_families_can_overlap():
    barrier = threading.Barrier(2)
    active = set()
    lock = threading.Lock()
    peaks = []

    async def episode(state, run_contact, _session):
        key = "solver" if state % 2 == 0 else "reviewer"

        def contact(slot):
            with lock:
                assert slot not in active
                active.add(slot)
                peaks.append(len(active))
            barrier.wait(timeout=3)
            with lock:
                active.remove(slot)
        await run_contact(contact, prefix_family=key)

    _run([0, 1, 2, 3], episode, {"solver": 0, "reviewer": 1})
    assert not active and max(peaks) == 2


def test_queued_cancellation_never_submits_a_model_contact():
    started, release = threading.Event(), threading.Event()
    forbidden = []

    async def episode(state, run_contact, _session):
        if state == 0:
            def model(slot):
                started.set()
                assert release.wait(3)
            await run_contact(model, prefix_family="solver")
        else:
            while not started.is_set():
                await asyncio.sleep(0)
            pending = asyncio.create_task(run_contact(lambda slot: forbidden.append(slot), prefix_family="solver"))
            await asyncio.sleep(0)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            release.set()
    _run([0, 1], episode, {"solver": 0})
    assert forbidden == []


def test_repeated_cancellation_drains_the_worker_before_reusing_its_slot():
    started, release, settled = threading.Event(), threading.Event(), threading.Event()
    observed = []

    async def episode(state, run_contact, _session):
        if state == 0:
            def model(slot):
                started.set()
                assert release.wait(3)
                settled.set()
            pending = asyncio.create_task(run_contact(model, prefix_family="solver"))
            while not started.is_set():
                await asyncio.sleep(0)
            pending.cancel()
            await asyncio.sleep(0)
            pending.cancel()
            await asyncio.sleep(0)
            assert not pending.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await pending
        else:
            while not started.is_set():
                await asyncio.sleep(0)
            await run_contact(lambda slot: observed.append((slot, settled.is_set())), prefix_family="solver")

    _run([0, 1], episode, {"solver": 0})
    assert observed == [(0, True)]


@pytest.mark.parametrize("assignments", [
    {}, [], {"solver": True}, {"solver": -1}, {"solver": 2},
    {"solver": 0, "reviewer": 0}, {"": 0}, {1: 0}, {"solver": 1.0},
])
def test_invalid_assignment_fails_before_any_work(assignments):
    async def episode(*args):
        pytest.fail("invalid scheduling reached the episode")
    with pytest.raises(ValueError, match="prefix"):
        _run([0], episode, assignments)


@pytest.mark.parametrize("family", [None, "unknown", True])
def test_unknown_family_is_refused_before_callback(family):
    async def episode(_state, run_contact, _session):
        await run_contact(lambda slot: pytest.fail("unbound contact ran"), prefix_family=family)
    with pytest.raises(ValueError, match="prefix"):
        _run([0], episode, {"solver": 0})


def test_no_implicit_affinity_when_disabled():
    async def episode(_state, run_contact, _session):
        await run_contact(lambda slot: pytest.fail("undeclared affinity ran"), prefix_family="solver")
    with pytest.raises(ValueError, match="prefix"):
        _run([0], episode, None)


def test_failure_releases_the_family_without_cross_sample_memory():
    failed = threading.Event()
    calls = []

    async def episode(state, run_contact, _session):
        if state == 0:
            def model(slot):
                failed.set()
                raise RuntimeError("synthetic request failure")
            with pytest.raises(RuntimeError, match="synthetic"):
                await run_contact(model, prefix_family="solver")
        else:
            while not failed.is_set():
                await asyncio.sleep(0)
            await run_contact(lambda slot: calls.append((state, slot)), prefix_family="solver")
    _run([0, 1], episode, {"solver": 0})
    assert calls == [(1, 0)]


def test_copy_of_bindings_cannot_be_changed_by_a_running_invoker():
    bindings = {"solver": 0}

    async def episode(_state, run_contact, _session):
        bindings["solver"] = 1
        assert await run_contact(lambda slot: slot, prefix_family="solver") == 0
    _run([0], episode, bindings)


def test_native_mode_is_required_even_for_an_empty_batch():
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import execute_speech_agent_workflows
    with pytest.raises(ValueError, match="prefix"):
        execute_speech_agent_workflows([], branch_count=1, slot_count=1, queue_depth=1,
                                       workflow_timeout_seconds=10, prefix_slot_bindings={"solver": 0})


def test_local_tools_do_not_pin_or_change_prefix_slots():
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import execute_speech_agent_workflows
    seen = []

    async def episode(state, run_contact, _session, *, run_local):
        await run_contact(lambda slot: seen.append((state, slot)), prefix_family="solver")
        assert await run_local(lambda: state) == state
        await run_contact(lambda slot: seen.append((state, slot)), prefix_family="reviewer")
    execute_speech_agent_workflows([0, 1], episode_invoker=episode, branch_count=1,
                                   slot_count=2, queue_depth=2, workflow_timeout_seconds=10,
                                   local_tool_workers=1,
                                   prefix_slot_bindings={"solver": 0, "reviewer": 1})
    assert sorted(seen) == [(0, 0), (0, 1), (1, 0), (1, 1)]


def test_cancelled_contact_that_later_fails_is_drained_without_leaking_capacity():
    started, release = threading.Event(), threading.Event()

    async def episode(_state, run_contact, _session):
        def model(slot):
            started.set()
            assert release.wait(3)
            raise RuntimeError("failure after cancellation")
        pending = asyncio.create_task(run_contact(model, prefix_family="solver"))
        while not started.is_set():
            await asyncio.sleep(0)
        pending.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await pending
        assert await run_contact(lambda slot: slot, prefix_family="solver") == 0
    _run([0], episode, {"solver": 0})
