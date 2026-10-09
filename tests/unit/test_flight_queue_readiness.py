"""Scientific prerequisites and complete scoring govern the shared queue."""

from contextlib import contextmanager
from concurrent.futures import Future

from speech_aware_evidence_acquisition.core.flight.queue import (
    FlightQueue,
    FlightReadiness,
    FlightDependency,
)
import pytest

from speech_aware_evidence_acquisition.core.flight.queue import FlightQueueError
from test_flight_queue import _make_flight


def test_unready_flight_explains_why_and_does_not_block_ready_peer(tmp_path):
    blocked = _make_flight(tmp_path, run_id="blocked", attempt_id="a")
    ready = _make_flight(tmp_path, run_id="ready", attempt_id="b")
    queue = FlightQueue(
        [blocked, ready],
        dry_run=True,
        readiness=lambda flight: (
            FlightReadiness("preparation-pending", "cold encoder receipt missing")
            if flight is blocked
            else FlightReadiness.ready()
        ),
    )
    assert queue.next_ready() is ready
    assert queue.states["blocked"].state == "preparation-pending"
    assert "encoder" in queue.states["blocked"].reason


def test_preflight_failure_is_named_and_retained(tmp_path):
    flight = _make_flight(tmp_path, run_id="broken", attempt_id="a")

    def fail():
        raise ValueError("preregistration receipt absent")

    flight.preflight = fail
    queue = FlightQueue([flight])
    assert queue.next_ready() is None
    assert queue.pending == (flight,)
    assert queue.states["broken"].state == "preflight-failed"
    assert "preregistration" in queue.states["broken"].reason


def test_dependency_requires_complete_score_and_requests_per_sample(tmp_path):
    first = _make_flight(tmp_path, run_id="first", attempt_id="a")
    dependent = _make_flight(tmp_path, run_id="dependent", attempt_id="b")
    calls = []

    def score(**kwargs):
        calls.append(kwargs)
        return {"succeeded": 1}

    first.score = score
    pending = Future()

    class Pool:
        def submit(self, fn, **kwargs):
            self.fn, self.kwargs = fn, kwargs
            return pending

        def shutdown(self, **kwargs):
            pass

    pool = Pool()
    queue = FlightQueue(
        [dependent, first],
        dependencies={"dependent": [FlightDependency("first", "scored")]},
        score_pool_factory=lambda: pool,
        include_per_sample=True,
    )
    queue.run(max_flights=1)
    assert queue.next_ready() is None
    assert queue.states["dependent"].state == "dependency-blocked"
    pending.set_result(pool.fn(**pool.kwargs))
    assert calls == [{"include_per_sample": True}]
    assert queue.next_ready() is dependent


def test_root_context_covers_serving_through_seal_but_releases_before_score(tmp_path):
    flight = _make_flight(tmp_path, run_id="owned", attempt_id="a")
    active = []

    @contextmanager
    def context(_flight):
        active.append(True)
        yield
        active.pop()

    for name in ("serve", "run_phases", "seal"):
        original = getattr(flight, name)

        def checked(*args, _original=original, **kwargs):
            assert active
            return _original(*args, **kwargs)

        setattr(flight, name, checked)
    original_score = flight.score

    def score(**kwargs):
        assert not active
        return original_score(**kwargs)

    flight.score = score
    queue = FlightQueue(
        [flight], execution_context_factory=context, include_per_sample=True
    )
    queue.run()
    queue.drain_scores()
    assert not active
    assert queue.states["owned"].state == "scored"


def test_returned_scoring_failure_never_satisfies_a_dependency(tmp_path):
    first = _make_flight(tmp_path, run_id="first", attempt_id="a")
    dependent = _make_flight(tmp_path, run_id="dependent", attempt_id="b")
    first.score = lambda **kwargs: {"result": {"failed": 1, "succeeded": 0}}
    queue = FlightQueue(
        [first, dependent],
        dependencies={"dependent": [FlightDependency("first", "scored")]},
    )
    queue.run(max_flights=1)
    queue.drain_scores()
    assert queue.states["first"].state == "failed"
    # Campaign admission is refused outright once a completed flight's scoring failed (the stricter
    # successor of returning None): the dependent is never handed out as ready.
    with pytest.raises(FlightQueueError, match="Campaign admission refused after first"):
        queue.next_ready()
    assert queue.states["first"].state == "failed"


def test_first_ready_flight_does_not_wait_for_later_preflight(tmp_path):
    from unittest.mock import Mock

    first = _make_flight(tmp_path, run_id="first", attempt_id="a")
    later = _make_flight(tmp_path, run_id="later", attempt_id="b")
    later.preflight = Mock(
        side_effect=AssertionError("later preflight must be deferred")
    )
    queue = FlightQueue([first, later], dry_run=True)
    assert queue.next_ready() is first
    later.preflight.assert_not_called()


def test_first_preflight_failure_allows_next_registered_candidate(tmp_path):
    first = _make_flight(tmp_path, run_id="first", attempt_id="a")
    later = _make_flight(tmp_path, run_id="later", attempt_id="b")
    first.preflight = lambda: (_ for _ in ()).throw(ValueError("source missing"))
    queue = FlightQueue([first, later], dry_run=True)
    assert queue.next_ready() is later
    assert queue.states["first"].state == "preflight-failed"


def test_preflight_failure_is_terminal_across_repeated_polls(tmp_path):
    flight = _make_flight(tmp_path, run_id="broken-once", attempt_id="a")
    ready = _make_flight(tmp_path, run_id="independent", attempt_id="b")
    calls = []

    def fail():
        calls.append("preflight")
        raise ValueError("request roster unavailable")

    flight.preflight = fail
    queue = FlightQueue([flight, ready], dry_run=True)

    assert queue.next_ready() is ready
    completed = queue.run(max_flights=1)
    assert completed[0].flight is ready
    assert queue.next_ready() is None
    assert queue.next_ready() is None
    assert calls == ["preflight"]
    assert queue.states["broken-once"].state == "preflight-failed"
