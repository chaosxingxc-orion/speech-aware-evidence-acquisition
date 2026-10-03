"""Bounded contact scheduling within the shared native workflow executor.

The native graph still owns every role, tool decision, state and final answer.
This coordinator only orders ready callbacks and drains workers before stopping.
"""

from __future__ import annotations

import asyncio
import contextvars
from dataclasses import dataclass
from time import monotonic_ns


@dataclass
class _Pending:
    member: int
    family: str
    contact_kind: str
    callback: object
    context: object
    result: asyncio.Future
    settled: asyncio.Future
    queued_ns: int


class NodeBatchCoordinator:
    """Keep one ready node family across all slots until the cohort leaves it."""

    def __init__(self, members, order, slots, cohort_index, event_sink=None):
        self.order = tuple(order)
        self.slots = slots
        self.cohort_index = cohort_index
        self.event_sink = event_sink
        self.states = {member: "between-contacts" for member in members}
        self.pending = {}
        self.changed = asyncio.Event()
        self.failure = None
        self.wave = 0

    def abort(self, error):
        if self.failure is None:
            self.failure = error
        for member, pending in list(self.pending.items()):
            if self.states[member] == "waiting":
                self.pending.pop(member)
                if not pending.result.done():
                    pending.result.set_exception(self.failure)
                pending.settled.set_result(None)
                self.states[member] = "between-contacts"
        self.changed.set()

    def finish(self, member, error=None):
        if error is not None:
            self.abort(error)
        self.states[member] = "finished"
        self.changed.set()

    async def contact(self, member, family, callback, contact_kind="model"):
        if not isinstance(family, str) or family not in self.order:
            raise ValueError("node batch contact needs its declared node family")
        if contact_kind not in {"model", "tool"}:
            raise ValueError("node batch contact kind must be model or tool")
        if self.failure is not None:
            raise self.failure
        if self.states[member] != "between-contacts":
            raise ValueError("node batch permits one pending contact per sample")
        loop = asyncio.get_running_loop()
        pending = _Pending(
            member,
            family,
            contact_kind,
            callback,
            contextvars.copy_context(),
            loop.create_future(),
            loop.create_future(),
            monotonic_ns(),
        )
        # A cancelled caller still preserves the first failure without leaving
        # an unobserved Future exception during mandatory worker settlement.
        pending.result.add_done_callback(
            lambda f: None if f.cancelled() else f.exception()
        )
        self.pending[member] = pending
        self.states[member] = "waiting"
        self.changed.set()
        try:
            return await asyncio.shield(pending.result)
        except asyncio.CancelledError as error:
            self.abort(error)
            while not pending.settled.done():
                try:
                    await asyncio.shield(pending.settled)
                except asyncio.CancelledError:
                    continue
            raise

    async def _invoke(self, pending, slot, wave):
        started = monotonic_ns()
        error = None
        value = None
        worker = asyncio.create_task(
            asyncio.to_thread(
                pending.context.run,
                pending.callback,
                slot,
            )
        )
        try:
            value = await asyncio.shield(worker)
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
                    pending.member,
                    {
                        "schema": "saea-node-batch-contact-timing-v1",
                        "cohort_index": self.cohort_index,
                        "wave_index": wave,
                        "node_id": pending.family,
                        "slot_id": slot,
                        "contact_kind": pending.contact_kind,
                        "queued_ns": pending.queued_ns,
                        "started_ns": started,
                        "finished_ns": finished,
                        "status": "completed" if error is None else "failed",
                        "error_type": None if error is None else type(error).__name__,
                    },
                )
            except BaseException as caught:
                error = error or caught
                self.abort(caught)
        self.pending.pop(pending.member)
        self.states[pending.member] = "between-contacts"
        if error is None:
            pending.result.set_result(value)
        else:
            pending.result.set_exception(error)
        pending.settled.set_result(None)
        self.changed.set()

    async def drive(self):
        current = None
        while True:
            self.changed.clear()
            if all(s == "finished" for s in self.states.values()):
                return
            ready = all(s in {"waiting", "finished"} for s in self.states.values())
            if self.failure is None and ready:
                families = {p.family for p in self.pending.values()}
                if current not in families:
                    current = next(node for node in self.order if node in families)
                group = [
                    p for _, p in sorted(self.pending.items()) if p.family == current
                ][: self.slots]
                for p in group:
                    self.states[p.member] = "working"
                self.wave += 1
                # The next scheduling decision follows settled model workers and
                # each sample's own post-call/tool/state transition. No early feed.
                await asyncio.gather(
                    *(self._invoke(p, slot, self.wave) for slot, p in enumerate(group))
                )
                continue
            await self.changed.wait()
