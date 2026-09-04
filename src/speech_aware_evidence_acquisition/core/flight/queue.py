"""``FlightQueue``: ready-first, geometry-grouped scheduling over a roster of
:class:`~.runtime.FlightRuntime` instances.

Owner rule (study ``CLAUDE.md``, "Engineering base and experiment rules"):
one resident server per serving geometry, ready-first queue by geometry --
GPU is contested, whichever task is ready occupies it, no idle reservations,
priority only orders the ready queue. This module is the harness-level
realization of that rule: it never starts a second server for a geometry it
already has resident, it never blocks a ready flight behind a not-yet-ready
one, and it overlaps official scoring (a CPU/IO-bound batch,
``core.scoring_batch.run_score_batch``) with the NEXT flight's generation by
handing each sealed flight's ``score()`` call to a background thread pool
rather than awaiting it inline.

Zero model/GPU/network contact of its OWN: every actual server start,
generation contact, and score batch happens inside the ``FlightRuntime``
instances this queue merely sequences, each already built with the caller's
own (possibly fake, possibly real) seams. This module adds exactly one more
seam of its own -- ``score_pool_factory`` -- so a unit test can run the
whole queue synchronously without any real thread pool.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable, Mapping, Sequence

from .runtime import FlightRuntime


class FlightQueueError(RuntimeError):
    """A :class:`FlightQueue` input, or its scheduling state, is invalid."""


def _default_score_pool_factory() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix="saea-flight-score")


@dataclass
class FlightQueueEntry:
    """One completed (or dry-run-stopped) flight's outcome, in the order this
    queue finished with it -- NOT necessarily arrival order, since a
    same-geometry flight may be preferred ahead of an earlier-arrived one
    with a different geometry."""

    flight: FlightRuntime
    dry_run: bool
    served_geometry: Mapping[str, object] | None
    score_future: Future[Mapping[str, object]] | None = None


class FlightQueue:
    """Holds pending :class:`FlightRuntime` instances and runs them in
    ready-first, geometry-preferring order.

    ``next_ready()`` preflights every still-pending flight it has not
    already preflighted (a flight whose ``preflight()`` raises is left
    pending, never scheduled, and never silently dropped -- it simply never
    becomes a candidate until removed by the caller) and returns:

    - the first PREFLIGHTED, PENDING flight whose ``adapter.serving_
      geometry()`` equals the geometry this queue currently has resident
      (``served_geometry``), if any such flight exists -- so the server
      restarts only on a geometry change, never merely because an earlier-
      arrived flight of a DIFFERENT geometry is also ready;
    - otherwise, the earliest-arrived preflighted flight (arrival order is
      the order flights were given to the constructor / appended via
      :meth:`add`).

    Returns ``None`` when no pending flight has yet passed preflight (the
    caller may retry later, or treat it as "nothing ready").
    """

    def __init__(
        self,
        flights: Sequence[FlightRuntime] = (),
        *,
        dry_run: bool = False,
        score_pool_factory: Callable[[], object] = _default_score_pool_factory,
    ) -> None:
        self._pending: list[FlightRuntime] = list(flights)
        if any(not isinstance(flight, FlightRuntime) for flight in self._pending):
            raise FlightQueueError("FlightQueue only accepts FlightRuntime instances")
        self.dry_run = bool(dry_run)
        self._preflighted: set[int] = set()
        self._served_geometry: Mapping[str, object] | None = None
        self._served_flight: FlightRuntime | None = None
        # The flight that actually STARTED the resident server. Distinct
        # from _served_flight, which is just the most recent user of it: a
        # reusing flight does not own the process and cannot stop it, so
        # tracking only the latest user would silently lose the owner and
        # leave the server resident forever.
        self._server_owner: FlightRuntime | None = None
        self._score_pool_factory = score_pool_factory
        self._score_pool_instance: object | None = None
        self.completed: list[FlightQueueEntry] = []

    def add(self, flight: FlightRuntime) -> None:
        if not isinstance(flight, FlightRuntime):
            raise FlightQueueError("FlightQueue only accepts FlightRuntime instances")
        self._pending.append(flight)

    @property
    def pending(self) -> tuple[FlightRuntime, ...]:
        return tuple(self._pending)

    def _ensure_preflighted(self, flight: FlightRuntime) -> bool:
        if id(flight) in self._preflighted:
            return True
        flight.preflight()
        self._preflighted.add(id(flight))
        return True

    def next_ready(self) -> FlightRuntime | None:
        ready: list[FlightRuntime] = []
        for flight in self._pending:
            if id(flight) in self._preflighted:
                ready.append(flight)
                continue
            try:
                self._ensure_preflighted(flight)
            except Exception:  # noqa: BLE001 -- a flight that fails preflight is not ready
                continue
            ready.append(flight)
        if not ready:
            return None
        if self._served_geometry is not None:
            for flight in ready:
                if dict(flight.adapter.serving_geometry()) == dict(self._served_geometry):
                    return flight
        return ready[0]

    def _score_pool(self) -> object:
        if self._score_pool_instance is None:
            self._score_pool_instance = self._score_pool_factory()
        return self._score_pool_instance

    def run(self, max_flights: int | None = None) -> tuple[FlightQueueEntry, ...]:
        """Run ready flights in this queue's preferred order until either
        ``max_flights`` have been dispatched or no pending flight is ready.

        ``dry_run`` (constructor flag) stops each flight after
        :meth:`~.runtime.FlightRuntime.preflight` -- ``preprocess``/
        ``serve``/``run_phases``/``seal``/``score`` never run, and no server
        is ever started. A live run preprocesses, then serves/reuses the
        geometry-matching resident server (never restarting it merely
        because a different flight is also ready), then runs phases and
        seals inline, and hands ``score()`` to the background pool so it
        overlaps the NEXT flight's ``preprocess``/``serve``/``run_phases`` --
        this method itself never blocks on a score future; callers that
        need every score to have finished call :meth:`drain_scores` (or
        inspect each entry's own ``score_future``).
        """

        if max_flights is not None and (isinstance(max_flights, bool) or max_flights < 0):
            raise FlightQueueError("max_flights must be a non-negative integer or None")
        dispatched = 0
        results: list[FlightQueueEntry] = []
        while self._pending:
            if max_flights is not None and dispatched >= max_flights:
                break
            flight = self.next_ready()
            if flight is None:
                break
            self._pending.remove(flight)
            dispatched += 1

            if self.dry_run:
                entry = FlightQueueEntry(flight=flight, dry_run=True, served_geometry=None)
                self.completed.append(entry)
                results.append(entry)
                continue

            flight.preprocess()

            geometry = dict(flight.adapter.serving_geometry())
            if self._served_geometry != geometry:
                # A genuine geometry change: stop the resident server BEFORE
                # starting the next one. Two 18.5 GB servers do not fit in
                # this host's VRAM, and the previous one is finished with --
                # every flight that used it has already sealed. Without this
                # the second geometry's server simply fails to start (and
                # the first was orphaned when the process exited).
                if self._server_owner is not None:
                    self._server_owner.stop_serving()
                flight.serve()
                self._served_flight = flight
                self._server_owner = flight
                self._served_geometry = geometry
            else:
                flight.serve(reuse=self._served_flight)
                self._served_flight = flight

            flight.run_phases()
            flight.seal()
            future = self._score_pool().submit(flight.score)  # type: ignore[attr-defined]
            entry = FlightQueueEntry(
                flight=flight, dry_run=False, served_geometry=geometry, score_future=future
            )
            self.completed.append(entry)
            results.append(entry)

        return tuple(results)

    def drain_scores(self) -> tuple[Mapping[str, object] | None, ...]:
        """Block until every dispatched flight's background ``score()`` has
        finished, returning each result in dispatch order (``None`` for a
        dry-run entry, which never scored)."""

        results: list[Mapping[str, object] | None] = []
        for entry in self.completed:
            if entry.score_future is None:
                results.append(None)
            else:
                results.append(entry.score_future.result())
        return tuple(results)

    def shutdown(self) -> None:
        """Drain the score pool and stop the resident server, in that order.

        Scoring first: ``core.scoring_batch`` reads sealed bundles off disk
        and never contacts the server, but draining before the stop keeps
        the ordering obvious and costs nothing. The server stop is the half
        that used to be missing entirely -- a queue that finished its last
        flight left llama-server resident."""

        if self._score_pool_instance is not None:
            self._score_pool_instance.shutdown(wait=True)  # type: ignore[attr-defined]
        if self._server_owner is not None:
            self._server_owner.stop_serving()
            self._server_owner = None
            self._served_flight = None
            self._served_geometry = None


__all__ = [
    "FlightQueue",
    "FlightQueueEntry",
    "FlightQueueError",
]
