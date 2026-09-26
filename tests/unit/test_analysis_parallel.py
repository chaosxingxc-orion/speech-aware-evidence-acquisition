"""``analysis.parallel``: the one bounded, order-independent fan-out.

The point of this module is that a read's numbers do not depend on how many
workers ran it, so these tests are about ORDER and BOUNDS, not about speed:

* the emitted mapping is in sorted key order even when the tasks finish in
  the opposite order;
* the same tasks at different worker counts give the same values;
* a seeded bootstrap through the fan-out reproduces the serial replicates
  exactly;
* the worker count comes from ONE place, defaults to the campaign cap rather
  than the host's core count, and refuses nonsense;
* a nested fan-out is refused rather than silently oversubscribing the host.
"""

from __future__ import annotations

import os
import random
import time

import pytest

from speech_aware_evidence_acquisition.analysis import parallel as par
from speech_aware_evidence_acquisition.analysis.parallel import (
    CAMPAIGN_WORKER_CAP,
    DEFAULT_WORKERS,
    MAX_WORKERS,
    WORKERS_ENV,
    ParallelReadError,
    map_by_key,
    resolve_workers,
)


# ---------------------------------------------------------------------------
# resolve_workers: one decision point, a bounded default, no core probing
# ---------------------------------------------------------------------------


def test_default_is_the_campaign_cap_not_the_core_count(monkeypatch):
    """The default is a written-down policy number, not a property of the host."""

    monkeypatch.delenv(WORKERS_ENV, raising=False)
    assert DEFAULT_WORKERS == CAMPAIGN_WORKER_CAP == 8
    assert resolve_workers(None) == 8
    # A host with 1,000 cores would still get 8: nothing is probed.
    monkeypatch.setattr(os, "cpu_count", lambda: 1000)
    assert resolve_workers(None) == 8
    assert par.IDLE_HOST_WORKERS == 20  # the number to PASS, never a default


def test_environment_overrides_the_default_but_not_an_explicit_request(monkeypatch):
    monkeypatch.setenv(WORKERS_ENV, "3")
    assert resolve_workers(None) == 3
    assert resolve_workers(6) == 6


def test_blank_environment_falls_back_to_the_default(monkeypatch):
    monkeypatch.setenv(WORKERS_ENV, "   ")
    assert resolve_workers(None) == DEFAULT_WORKERS


def test_a_cap_clamps_to_the_units_that_actually_exist(monkeypatch):
    monkeypatch.delenv(WORKERS_ENV, raising=False)
    assert resolve_workers(None, cap=2) == 2
    assert resolve_workers(64, cap=4) == 4
    assert resolve_workers(64) == MAX_WORKERS


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "8"])
def test_refuses_a_nonsense_request(bad, monkeypatch):
    monkeypatch.delenv(WORKERS_ENV, raising=False)
    with pytest.raises(ParallelReadError, match="positive integer"):
        resolve_workers(bad)


def test_refuses_a_nonsense_environment_value(monkeypatch):
    monkeypatch.setenv(WORKERS_ENV, "many")
    with pytest.raises(ParallelReadError, match="not an integer"):
        resolve_workers(None)


def test_refuses_a_nonsense_cap():
    with pytest.raises(ParallelReadError, match="cap must be"):
        resolve_workers(4, cap=0)


# ---------------------------------------------------------------------------
# map_by_key: sorted key order, never completion order
# ---------------------------------------------------------------------------


def _sleeper(seconds: float, value: object):
    def task():
        time.sleep(seconds)
        return value

    return task


def test_emits_sorted_key_order_even_when_completion_order_is_reversed():
    # "a" is the slowest, so completion order is d, c, b, a.
    tasks = {
        "a": _sleeper(0.30, 1),
        "b": _sleeper(0.20, 2),
        "c": _sleeper(0.10, 3),
        "d": _sleeper(0.00, 4),
    }
    result = map_by_key(tasks, workers=4)
    assert list(result) == ["a", "b", "c", "d"]
    assert result == {"a": 1, "b": 2, "c": 3, "d": 4}


def test_keys_are_sorted_even_on_the_in_process_path():
    tasks = {"z": lambda: 26, "a": lambda: 1, "m": lambda: 13}
    assert list(map_by_key(tasks, workers=1)) == ["a", "m", "z"]


@pytest.mark.parametrize("workers", [1, 2, 4, 7])
def test_the_same_tasks_give_the_same_values_at_any_worker_count(workers):
    tasks = {f"k{index:02d}": (lambda i=index: i * i) for index in range(9)}
    assert map_by_key(tasks, workers=workers) == {
        f"k{index:02d}": index * index for index in range(9)
    }


def test_an_empty_or_single_task_batch_is_fine():
    assert map_by_key({}, workers=4) == {}
    assert map_by_key({"only": lambda: "v"}, workers=4) == {"only": "v"}


def test_a_worker_exception_propagates():
    def boom():
        raise ValueError("task failed")

    with pytest.raises(ValueError, match="task failed"):
        map_by_key({"a": boom, "b": lambda: 1}, workers=2)


def test_refuses_a_non_callable_task():
    with pytest.raises(ParallelReadError, match="not callable"):
        map_by_key({"a": lambda: 1, "b": 2}, workers=2)  # type: ignore[dict-item]


def test_refuses_unsortable_keys():
    with pytest.raises(ParallelReadError, match="mutually sortable"):
        map_by_key({"a": lambda: 1, 2: lambda: 2}, workers=2)  # type: ignore[dict-item]


@pytest.mark.parametrize("workers", [0, -3, True, "4"])
def test_refuses_a_nonsense_worker_count(workers):
    with pytest.raises(ParallelReadError, match="positive integer"):
        map_by_key({"a": lambda: 1, "b": lambda: 2}, workers=workers)  # type: ignore[arg-type]


requires_fork = pytest.mark.skipif(
    par._fork_context() is None, reason="this platform has no fork start method"
)


@requires_fork
def test_refuses_a_nested_fan_out():
    """Nesting would multiply the worker counts; the guard is not advisory."""

    def inner():
        return map_by_key({"x": lambda: 1, "y": lambda: 2}, workers=2)

    with pytest.raises(ParallelReadError, match="nested fan-out"):
        map_by_key({"a": inner, "b": inner}, workers=2)


def test_the_task_table_is_released_even_when_a_task_raises():
    def boom():
        raise RuntimeError("no")

    with pytest.raises(RuntimeError):
        map_by_key({"a": boom, "b": lambda: 1}, workers=2)
    # A second fan-out must not see the previous batch's table.
    assert map_by_key({"a": lambda: 1, "b": lambda: 2}, workers=2) == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# The determinism the reads actually depend on: a seeded resampling is a
# function of its seed, never of the worker count or the execution order.
# ---------------------------------------------------------------------------


def _seeded_mean(seed: int, draws: int, values: tuple[float, ...]):
    def task() -> tuple[float, ...]:
        rng = random.Random(seed)
        out = []
        for _ in range(draws):
            out.append(
                sum(values[rng.randrange(len(values))] for _ in values) / len(values)
            )
        return tuple(out)

    return task


@pytest.mark.parametrize("workers", [1, 2, 4])
def test_a_seeded_resampling_is_identical_at_every_worker_count(workers):
    values = tuple(float(index % 7) for index in range(40))
    tasks = {
        f"boot-{offset}": _seeded_mean(1000 + offset, 50, values) for offset in range(6)
    }
    result = map_by_key(tasks, workers=workers)
    reference = {key: task() for key, task in sorted(tasks.items())}
    assert result == reference
    assert list(result) == sorted(tasks)


def test_two_tasks_with_the_same_seed_agree_regardless_of_order():
    values = tuple(float(index) for index in range(20))
    tasks = {
        "early": _seeded_mean(7, 30, values),
        "late": _seeded_mean(7, 30, values),
    }
    out = map_by_key(tasks, workers=2)
    assert out["early"] == out["late"]


def test_workers_argument_is_registered_with_one_spelling_and_default():
    import argparse

    parser = argparse.ArgumentParser()
    par.add_workers_argument(parser)
    namespace = parser.parse_args([])
    assert namespace.workers is None
    assert parser.parse_args(["--workers", "5"]).workers == 5
    help_text = parser.format_help()
    assert "--workers" in help_text
    assert str(DEFAULT_WORKERS) in help_text
    assert WORKERS_ENV in help_text


def test_the_environment_is_not_mutated_by_resolving(monkeypatch):
    monkeypatch.setenv(WORKERS_ENV, "5")
    before = dict(os.environ)
    resolve_workers(None)
    assert dict(os.environ) == before
