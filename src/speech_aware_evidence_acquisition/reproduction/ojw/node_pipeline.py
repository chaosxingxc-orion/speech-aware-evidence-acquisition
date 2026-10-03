"""Schedule independent native workflows by global node stage with CPU prefetch.

The existing workflow owns dependencies, tools, requests, budgets and answers.
This helper releases pure preparation by fixed group and model contacts by a
strict panel barrier. It never submits a future-stage model to hide CPU work.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
from dataclasses import dataclass
from time import monotonic_ns


@dataclass
class _Work:
    member: int
    key: tuple[int, int]
    family: str
    kind: str
    callback: object
    context: object
    result: asyncio.Future
    settled: asyncio.Future
    queued_ns: int


class NodePipelineCoordinator:
    """Keep a full panel logically pending while bounding CPU and model workers."""

    def __init__(
        self, members, order, *, slots, group_size, prepare_workers, event_sink=None
    ):
        members, order = tuple(members), tuple(order)
        if (
            len(set(members)) != len(members)
            or any(type(m) is not int for m in members)
            or not order
            or len(set(order)) != len(order)
            or any(not isinstance(n, str) or not n.strip() for n in order)
            or type(slots) is not int
            or slots < 1
            or type(group_size) is not int
            or group_size < 1
            or type(prepare_workers) is not int
            or not 1 <= prepare_workers <= 8
            or (event_sink is not None and not callable(event_sink))
        ):
            raise ValueError(
                "node pipeline requires unique jobs, node order and bounded workers"
            )
        self.order = order
        self.members = members
        self.slots = slots
        self.prepare_workers = prepare_workers
        self.groups = tuple(
            members[i : i + group_size] for i in range(0, len(members), group_size)
        )
        self.group_index = {m: i for i, group in enumerate(self.groups) for m in group}
        self.event_sink = event_sink
        self.states = dict.fromkeys(members, "new")
        self.keys = dict.fromkeys(members)
        self.prepared = dict.fromkeys(members, False)
        self.pending = {}
        self.cpu_tasks = {}
        self.model_tasks = {}
        self.changed = asyncio.Event()
        self.failure = None
        self.current = None

    def abort(self, error):
        if self.failure is None:
            self.failure = error
        for member, work in list(self.pending.items()):
            if self.states[member] in {"prepare-ready", "contact-ready"}:
                self.pending.pop(member)
                self.states[member] = "between"
                work.result.set_exception(self.failure)
                work.settled.set_result(None)
        self.changed.set()

    def finish(self, member, error=None):
        if error is not None:
            self.abort(error)
        self.states[member] = "finished"
        self.changed.set()

    def _check(self, member, family, callback):
        if self.failure is not None:
            raise self.failure
        if (
            member not in self.states
            or family not in self.order
            or not callable(callback)
        ):
            raise ValueError("node pipeline contact needs its declared member and node")
        if self.states[member] not in {"new", "between"}:
            raise ValueError("node pipeline allows only one pending operation per job")

    async def prepare(self, member, family, callback):
        """Run a pure CPU builder only after its fixed group leaves predecessors."""
        self._check(member, family, callback)
        previous = self.keys[member]
        index = self.order.index(family)
        round_index = 0 if previous is None else previous[0] + (index <= previous[1])
        self.keys[member] = (round_index, index)
        self.prepared[member] = False
        return await self._enqueue(member, family, "prepare", callback)

    async def contact(self, member, family, callback, contact_kind="model"):
        """Dispatch an unchanged metered model/tool callback in its active stage."""
        self._check(member, family, callback)
        key = self.keys[member]
        if key is None or not self.prepared[member] or self.order[key[1]] != family:
            raise ValueError("node pipeline contact requires its prepared role")
        if contact_kind not in {"model", "tool"}:
            raise ValueError("node pipeline contact kind must be model or tool")
        return await self._enqueue(member, family, contact_kind, callback)

    async def _enqueue(self, member, family, kind, callback):
        loop = asyncio.get_running_loop()
        work = _Work(
            member,
            self.keys[member],
            family,
            kind,
            callback,
            contextvars.copy_context(),
            loop.create_future(),
            loop.create_future(),
            monotonic_ns(),
        )
        work.result.add_done_callback(
            lambda f: None if f.cancelled() else f.exception()
        )
        self.pending[member] = work
        self.states[member] = "prepare-ready" if kind == "prepare" else "contact-ready"
        self.changed.set()
        try:
            return await asyncio.shield(work.result)
        except asyncio.CancelledError as error:
            self.abort(error)
            while not work.settled.done():
                try:
                    await asyncio.shield(work.settled)
                except asyncio.CancelledError:
                    continue
            raise

    def _group_ready(self, work):
        return all(
            self.states[m] == "finished"
            or (self.keys[m] is not None and self.keys[m] >= work.key)
            for m in self.groups[self.group_index[work.member]]
        )

    async def _perform(self, work, slot):
        started = monotonic_ns()
        error, value = None, None
        args = () if work.kind == "prepare" else (slot,)
        worker = asyncio.create_task(
            asyncio.to_thread(work.context.run, work.callback, *args)
        )
        try:
            value = await asyncio.shield(worker)
            if inspect.isawaitable(value):
                if inspect.iscoroutine(value):
                    value.close()
                raise TypeError("node pipeline workers must be synchronous callbacks")
        except BaseException as caught:
            error = caught
            self.abort(caught)
            while not worker.done():
                try:
                    await asyncio.shield(worker)
                except asyncio.CancelledError:
                    continue
                except BaseException:
                    break
            if not worker.cancelled():
                worker.exception()
        finished = monotonic_ns()
        if self.event_sink is not None:
            try:
                self.event_sink(
                    work.member,
                    {
                        "schema": "saea-node-pipeline-timing-v1",
                        "group_index": self.group_index[work.member],
                        "round_index": work.key[0],
                        "node_index": work.key[1],
                        "node_id": work.family,
                        "kind": work.kind,
                        "slot_id": slot,
                        "queued_ns": work.queued_ns,
                        "started_ns": started,
                        "finished_ns": finished,
                        "status": "completed" if error is None else "failed",
                        "error_type": None if error is None else type(error).__name__,
                    },
                )
            except BaseException as caught:
                error = error or caught
                self.abort(caught)
        self.pending.pop(work.member)
        self.states[work.member] = "between"
        if work.kind == "prepare":
            self.cpu_tasks.pop(work.member)
            self.prepared[work.member] = error is None
        else:
            self.model_tasks.pop(slot)
        if error is None:
            work.result.set_result(value)
        else:
            work.result.set_exception(error)
        work.settled.set_result(None)
        self.changed.set()

    async def drive(self):
        try:
            while True:
                self.changed.clear()
                if all(state == "finished" for state in self.states.values()):
                    return
                if self.failure is None:
                    # Bounded CPU tasks may prepare future stages while current
                    # model work continues. Registered group membership is fixed.
                    for member in self.members:
                        if len(self.cpu_tasks) >= self.prepare_workers:
                            break
                        work = self.pending.get(member)
                        if self.states[member] == "prepare-ready" and self._group_ready(
                            work
                        ):
                            self.states[member] = "preparing"
                            self.cpu_tasks[member] = asyncio.create_task(
                                self._perform(work, None)
                            )
                    if (
                        self.current is not None
                        and not self.model_tasks
                        and all(
                            self.states[m] == "finished"
                            or (
                                self.keys[m] is not None and self.keys[m] > self.current
                            )
                            for m in self.members
                        )
                    ):
                        self.current = None
                    # Both barriers close: every workflow is terminal or at its
                    # next prepared model/tool request; no earlier worker remains.
                    if self.current is None and all(
                        state in {"finished", "contact-ready"}
                        for state in self.states.values()
                    ):
                        self.current = min(work.key for work in self.pending.values())
                    if self.current is not None:
                        ready = [
                            self.pending[m]
                            for m in self.members
                            if self.states[m] == "contact-ready"
                            and self.keys[m] == self.current
                        ]
                        free = [
                            s for s in range(self.slots) if s not in self.model_tasks
                        ]
                        for work, slot in zip(ready, free):
                            self.states[work.member] = "working"
                            self.model_tasks[slot] = asyncio.create_task(
                                self._perform(work, slot)
                            )
                await self.changed.wait()
        except BaseException as error:
            self.abort(error)
            tasks = tuple(self.cpu_tasks.values()) + tuple(self.model_tasks.values())
            for task in tasks:
                while not task.done():
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        continue
            raise
