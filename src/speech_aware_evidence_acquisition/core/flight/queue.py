"""Ready-first FlightRuntime scheduling with scientific gates and CPU scoring overlap."""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from contextlib import nullcontext
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, ContextManager, Mapping, Sequence

if TYPE_CHECKING:  # the runtime stack is heavy; annotations only (lazy import in FlightQueue.add)
    from .runtime import FlightRuntime


class FlightQueueError(RuntimeError):
    """A queue input or scheduling state is invalid."""


def _default_score_pool_factory() -> ThreadPoolExecutor:
    return ThreadPoolExecutor(max_workers=1, thread_name_prefix="saea-flight-score")


@dataclass(frozen=True)
class FlightReadiness:
    """A visible scheduling state; a refusal always carries a useful reason."""

    state: str
    reason: str = ""

    def __post_init__(self) -> None:
        allowed = {
            "ready", "dependency-blocked", "preparation-pending", "held",
            "preflight-failed", "running", "sealed", "scored", "failed", "dry-run",
        }
        if self.state not in allowed:
            raise FlightQueueError(f"unknown readiness state: {self.state!r}")
        if self.state in {"dependency-blocked", "preparation-pending", "held", "preflight-failed", "failed"}:
            if not self.reason.strip():
                raise FlightQueueError(f"{self.state} requires a reason")

    @classmethod
    def ready(cls) -> FlightReadiness:
        return cls("ready")


@dataclass(frozen=True)
class FlightDependency:
    run_id: str
    required_state: str = "scored"

    def __post_init__(self) -> None:
        if not self.run_id or self.required_state not in {"sealed", "scored"}:
            raise FlightQueueError("dependencies require a run id and sealed/scored state")


@dataclass
class FlightQueueEntry:
    flight: FlightRuntime
    dry_run: bool
    served_geometry: Mapping[str, object] | None
    score_future: Future[Mapping[str, object]] | None = None


class FlightQueue:
    """Prefer ready flights that match the complete resident serving profile.

    External preparation and scientific decisions are evaluated through the
    readiness callback on every scheduling pass. Dependencies require an explicit
    sealed/scored state. Preflight failures remain pending with their reason;
    an attempted flight is never silently retried.
    """

    def __init__(
        self, flights: Sequence[FlightRuntime] = (), *, dry_run: bool = False,
        score_pool_factory: Callable[[], object] = _default_score_pool_factory,
        readiness: Callable[[FlightRuntime], FlightReadiness] | None = None,
        dependencies: Mapping[str, Sequence[FlightDependency]] | None = None,
        execution_context_factory: Callable[[FlightRuntime], ContextManager] | None = None,
        include_per_sample: bool = False,
    ) -> None:
        self._pending: list[FlightRuntime] = []
        self._known: set[str] = set()
        self._states: dict[str, FlightReadiness] = {}
        for flight in flights:
            self.add(flight)
        self.dry_run = bool(dry_run)
        self._preflighted: set[int] = set()
        # A preflight refusal is terminal for this queue invocation. Keep it
        # separate from successful preflights so repeated readiness polls do
        # not rebuild the same request roster while another flight proceeds.
        self._preflight_failed: set[int] = set()
        self._served_geometry: Mapping[str, object] | None = None
        self._served_profile: str | None = None
        self._served_flight: FlightRuntime | None = None
        self._server_owner: FlightRuntime | None = None
        self._score_pool_factory = score_pool_factory
        self._score_pool_instance: object | None = None
        self._readiness = readiness or (lambda flight: FlightReadiness.ready())
        self._dependencies = {key: tuple(value) for key, value in (dependencies or {}).items()}
        self._execution_context_factory = execution_context_factory
        self._include_per_sample = include_per_sample
        self.completed: list[FlightQueueEntry] = []

    def add(self, flight: FlightRuntime) -> None:
        from .runtime import FlightRuntime

        if not isinstance(flight, FlightRuntime):
            raise FlightQueueError("FlightQueue only accepts FlightRuntime instances")
        if flight.run_id in self._known:
            raise FlightQueueError(f"duplicate flight run id: {flight.run_id}")
        self._known.add(flight.run_id)
        self._pending.append(flight)

    @property
    def pending(self) -> tuple[FlightRuntime, ...]:
        return tuple(self._pending)

    @property
    def states(self) -> Mapping[str, FlightReadiness]:
        self._refresh_scores()
        return dict(self._states)

    def _refresh_scores(self) -> None:
        for entry in self.completed:
            future = entry.score_future
            if future is None or not future.done():
                continue
            try:
                result = future.result()
                batch = result.get("result", result) if isinstance(result, Mapping) else {}
                if isinstance(batch, Mapping) and batch.get("failed", 0):
                    raise FlightQueueError("official score batch reported failed jobs")
            except Exception as error:  # noqa: BLE001 -- retain explicit failure metadata
                self._states[entry.flight.run_id] = FlightReadiness(
                    "failed", f"official scoring failed: {type(error).__name__}: {error}",
                )
            else:
                self._states[entry.flight.run_id] = FlightReadiness("scored")

    def _dependency_state(self, flight: FlightRuntime) -> FlightReadiness:
        for dependency in self._dependencies.get(flight.run_id, ()):
            state = self._states.get(dependency.run_id)
            satisfied = {"scored"} if dependency.required_state == "scored" else {"sealed", "scored"}
            if state is None or state.state not in satisfied:
                actual = state.state if state else "not completed"
                return FlightReadiness(
                    "dependency-blocked",
                    f"{dependency.run_id} requires {dependency.required_state}; current state: {actual}",
                )
        return FlightReadiness.ready()

    def _ensure_preflighted(self, flight: FlightRuntime) -> None:
        if id(flight) not in self._preflighted and id(flight) not in self._preflight_failed:
            flight.preflight()
            self._preflighted.add(id(flight))

    def next_ready(self) -> FlightRuntime | None:
        self._refresh_scores()
        if self._pending:
            for entry in self.completed:
                state = self._states.get(entry.flight.run_id)
                if state is not None and state.state == "failed":
                    raise FlightQueueError(
                        f"Campaign admission refused after {entry.flight.run_id}: {state.reason}"
                    )
        ready: list[FlightRuntime] = []
        for flight in self._pending:
            if id(flight) in self._preflight_failed:
                # Preserve the terminal refusal across polling passes; the
                # readiness callback must not overwrite it with ``ready``.
                continue
            state = self._dependency_state(flight)
            if state.state == "ready":
                try:
                    state = self._readiness(flight)
                    if not isinstance(state, FlightReadiness):
                        raise FlightQueueError("readiness callback must return FlightReadiness")
                except Exception as error:  # noqa: BLE001 -- fail closed, visible reason
                    state = FlightReadiness("held", f"readiness check failed: {error}")
            if state.state == "ready":
                ready.append(flight)
            self._states[flight.run_id] = state
        fallback = None
        for flight in ready:
            if id(flight) in self._preflight_failed:
                continue
            try:
                self._ensure_preflighted(flight)
            except Exception as error:  # noqa: BLE001 -- preflight is a readiness refusal
                self._preflight_failed.add(id(flight))
                self._states[flight.run_id] = FlightReadiness(
                    "preflight-failed", f"{type(error).__name__}: {error}"
                )
                continue
            if fallback is None:
                fallback = flight
            # Once an admissible matching flight is found, do not delay it
            # behind unrelated complete-roster preflights. Preserve geometry
            # preference when selecting a successor to the current service.
            if (
                self._served_profile is None
                or flight.serving_profile_fingerprint() == self._served_profile
            ):
                return flight
        return fallback

    def _score_pool(self) -> object:
        if self._score_pool_instance is None:
            self._score_pool_instance = self._score_pool_factory()
        return self._score_pool_instance

    def _serve(self, flight: FlightRuntime, profile: str) -> None:
        if self._execution_context_factory is not None:
            # The coordinator context owns profile switching. Each worker attaches
            # independently; this queue owns no shutdown capability.
            flight.serve()
        elif self._served_profile != profile:
            if self._server_owner is not None:
                self._server_owner.stop_serving()
            flight.serve()
            self._server_owner = flight
        else:
            flight.serve(reuse=self._served_flight)
        self._served_flight = flight
        self._served_profile = profile
        self._served_geometry = dict(flight.adapter.serving_geometry())

    def run(self, max_flights: int | None = None) -> tuple[FlightQueueEntry, ...]:
        if max_flights is not None and (
            isinstance(max_flights, bool) or not isinstance(max_flights, int) or max_flights < 0
        ):
            raise FlightQueueError("max_flights must be a non-negative integer or None")
        results: list[FlightQueueEntry] = []
        while self._pending and (max_flights is None or len(results) < max_flights):
            flight = self.next_ready()
            if flight is None:
                break
            self._pending.remove(flight)
            if self.dry_run:
                entry = FlightQueueEntry(flight, True, None)
                self._states[flight.run_id] = FlightReadiness("dry-run")
            else:
                self._states[flight.run_id] = FlightReadiness("running")
                try:
                    flight.preprocess()
                    context = (
                        self._execution_context_factory(flight)
                        if self._execution_context_factory else nullcontext()
                    )
                    with context:
                        profile = flight.serving_profile_fingerprint()
                        self._serve(flight, profile)
                        try:
                            flight.run_phases()
                            flight.seal()
                        except Exception as error:
                            # An attempt may already be OPENED once generation
                            # begins. Abort it before the coordinator-owned
                            # execution context releases its lease, while
                            # retaining the generation failure as the primary
                            # error if aborting also fails.
                            try:
                                flight.abort(
                                    "generation failed during run_phases or seal: "
                                    f"{type(error).__name__}: {error}"
                                )
                            except Exception as abort_error:
                                error.add_note(
                                    "FlightQueue could not abort the failed attempt: "
                                    f"{type(abort_error).__name__}: {abort_error}"
                                )
                            raise
                    self._states[flight.run_id] = FlightReadiness("sealed")
                    kwargs = {"include_per_sample": True} if self._include_per_sample else {}
                    future = self._score_pool().submit(flight.score, **kwargs)
                    entry = FlightQueueEntry(flight, False, self._served_geometry, future)
                except Exception as error:
                    self._states[flight.run_id] = FlightReadiness(
                        "failed", f"{type(error).__name__}: {error}",
                    )
                    raise
            self.completed.append(entry)
            results.append(entry)
        return tuple(results)

    def drain_scores(self) -> tuple[Mapping[str, object] | None, ...]:
        try:
            return tuple(
                entry.score_future.result() if entry.score_future else None
                for entry in self.completed
            )
        finally:
            self._refresh_scores()

    def shutdown(self) -> None:
        if self._score_pool_instance is not None:
            self._score_pool_instance.shutdown(wait=True)
        self._refresh_scores()
        if self._server_owner is not None:
            self._server_owner.stop_serving()
            self._server_owner = None
            self._served_flight = None
            self._served_geometry = None
            self._served_profile = None


__all__ = ["FlightQueue", "FlightQueueEntry", "FlightQueueError", "FlightReadiness", "FlightDependency"]
