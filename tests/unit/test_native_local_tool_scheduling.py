"""Bounded CPU tools yield model slots without changing episode ordering."""

import asyncio
import contextvars
import threading

import pytest

from speech_aware_evidence_acquisition.reproduction.ojw import openjiuwen_available

pytestmark = pytest.mark.skipif(not openjiuwen_available(), reason="OpenJiuwen unavailable")


def _run(states, episode, *, slots=1, depth=16, workers=1):
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )
    return execute_speech_agent_workflows(
        states, episode_invoker=episode, branch_count=1, slot_count=slots,
        queue_depth=depth, workflow_timeout_seconds=10, local_tool_workers=workers,
    )


def test_cpu_wait_releases_model_slot_and_preserves_context_and_tool_result():
    local_started = threading.Event()
    unrelated_model_finished = threading.Event()
    variable = contextvars.ContextVar("local_tool_test", default="missing")
    events = []

    async def episode(state, run_contact, _session, *, run_local):
        if state == "tool":
            variable.set("bound-context")
            await run_contact(lambda slot: events.append(("initial", slot)))

            def local():
                local_started.set()
                assert unrelated_model_finished.wait(2), "model slot remained held during CPU work"
                assert variable.get() == "bound-context"
                return "actual local evidence"

            evidence = await run_local(local)
            await run_contact(lambda slot: events.append(("final", slot, evidence)))
        else:
            while not local_started.is_set():
                await asyncio.sleep(0)

            def model(slot):
                events.append(("unrelated", slot))
                unrelated_model_finished.set()
            await run_contact(model)

    assert _run(["tool", "model"], episode) == ["tool", "model"]
    assert events == [
        ("initial", 0), ("unrelated", 0), ("final", 0, "actual local evidence"),
    ]


def test_shared_cpu_worker_is_bounded_across_sixteen_admitted_episodes():
    lock = threading.Lock()
    active = peak = 0
    seen = []
    context = contextvars.ContextVar("sample", default=-1)

    async def episode(state, run_contact, _session, *, run_local):
        context.set(state)
        await run_contact(lambda slot: slot)

        def local():
            nonlocal active, peak
            with lock:
                active += 1
                peak = max(peak, active)
                seen.append(context.get())
            threading.Event().wait(0.002)
            with lock:
                active -= 1
            return state

        assert await run_local(local) == state
        await run_contact(lambda slot: slot)

    assert _run(list(range(16)), episode, slots=4) == list(range(16))
    assert sorted(seen) == list(range(16))
    assert active == 0 and peak == 1


def test_cancellation_drains_started_tool_before_cpu_capacity_is_reused():
    active = threading.Event()
    release = threading.Event()
    subsequent = []
    events = []

    async def episode(state, run_contact, _session, *, run_local):
        if state == 0:
            await run_contact(lambda slot: slot)

            def local():
                active.set()
                assert release.wait(2)
                events.append("settled")
                active.clear()
            task = asyncio.create_task(run_local(local))
            while not active.is_set():
                await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            events.append("cancelled")
        else:
            while not active.is_set() and "settled" not in events:
                await asyncio.sleep(0)
            await run_contact(lambda slot: slot)
            await run_local(lambda: subsequent.append(active.is_set()))

    _run([0, 1], episode)
    assert events == ["settled", "cancelled"]
    assert subsequent == [False]


def test_cancellation_while_queued_never_submits_tool_or_leaks_model_slot():
    first_active = threading.Event()
    release = threading.Event()
    forbidden = []
    events = []

    async def episode(state, run_contact, _session, *, run_local):
        if state == 0:
            def local():
                first_active.set()
                assert release.wait(2)
            await run_local(local)
        else:
            while not first_active.is_set():
                await asyncio.sleep(0)
            await run_contact(lambda slot: events.append(("before", slot)))
            queued = asyncio.create_task(run_local(lambda: forbidden.append(state)))
            # The first local worker is still busy; let the second await capacity.
            await asyncio.sleep(0)
            queued.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued
            release.set()
            await run_contact(lambda slot: events.append(("after", slot)))

    _run([0, 1], episode)
    assert not forbidden
    assert events == [("before", 0), ("after", 0)]


def test_opt_in_without_selected_tools_does_no_cpu_work(monkeypatch):
    from speech_aware_evidence_acquisition.reproduction.ojw import runner

    original_pool = runner.ThreadPoolExecutor

    class NoLocalSubmission(original_pool):
        def submit(self, *_args, **_kwargs):
            pytest.fail("unselected local work was submitted")

    monkeypatch.setattr(runner, "ThreadPoolExecutor", NoLocalSubmission)

    async def episode(_state, run_contact, _session, *, run_local):
        assert callable(run_local)
        assert await run_contact(lambda slot: slot) == 0

    assert _run([0], episode) == [0]


@pytest.mark.parametrize("workers", [-1, True, 9, None, 1.5])
def test_invalid_cpu_worker_limit_fails_before_episode(workers):
    async def episode(*args, **kwargs):
        pytest.fail("episode invoked before validation")

    with pytest.raises(ValueError, match="local_tool_workers"):
        _run([0], episode, workers=workers)


def test_local_execution_rejects_legacy_invoker():
    from speech_aware_evidence_acquisition.reproduction.ojw.runner import (
        execute_speech_agent_workflows,
    )
    with pytest.raises(ValueError, match="native episode"):
        execute_speech_agent_workflows(
            [], branch_count=1, slot_count=1, queue_depth=1,
            workflow_timeout_seconds=10, local_tool_workers=1,
        )
