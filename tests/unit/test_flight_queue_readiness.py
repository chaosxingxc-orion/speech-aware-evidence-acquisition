"""Scientific prerequisites and complete scoring govern the shared queue."""
from contextlib import contextmanager
from concurrent.futures import Future

from speech_aware_evidence_acquisition.core.flight.queue import (
    FlightQueue, FlightReadiness, FlightDependency,
)
from test_flight_queue import _make_flight


def test_unready_flight_explains_why_and_does_not_block_ready_peer(tmp_path):
    blocked = _make_flight(tmp_path, run_id="blocked", attempt_id="a")
    ready = _make_flight(tmp_path, run_id="ready", attempt_id="b")
    queue = FlightQueue(
        [blocked, ready], dry_run=True,
        readiness=lambda flight: (
            FlightReadiness("preparation-pending", "cold encoder receipt missing")
            if flight is blocked else FlightReadiness.ready()
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
        score_pool_factory=lambda: pool, include_per_sample=True,
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
    queue = FlightQueue([flight], execution_context_factory=context, include_per_sample=True)
    queue.run()
    queue.drain_scores()
    assert not active
    assert queue.states["owned"].state == "scored"
