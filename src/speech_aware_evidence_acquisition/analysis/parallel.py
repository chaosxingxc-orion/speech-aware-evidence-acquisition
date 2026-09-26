"""One bounded, order-independent fan-out for the offline analysis reads.

The reads this module serves are CPU-bound pure Python over already-sealed
bytes: cluster bootstraps, per-rule rescorings, one complete official scoring
per derived copy. They are embarrassingly parallel per key and they were all
single-threaded, on a 24-core host, because the only parallelism the
repository had was ``core.scoring_batch``'s outer fan-out over whole scoring
JOBS -- and the engineering-base rule pins the paper-facing number to ONE
complete unsharded scorer run per manifest, so a cell that declares
``official_complete_scoring_jobs: 1`` got exactly one thread.

This module is the other half: fan out INSIDE a read, over independent units
of work, without touching what any of them computes.

Three invariants, built in rather than tested for afterwards
------------------------------------------------------------

1. **Fan out by key, emit in sorted key order.** :func:`map_by_key` takes a
   mapping ``{key: zero-argument callable}`` and returns a plain ``dict``
   whose insertion order is ``sorted(keys)``, never completion order. A
   caller that serialises the result with ``sort_keys=True`` (every read here
   does) is insensitive to the order anyway; emitting sorted makes the
   parallel and serial paths byte-identical even for a caller that is not.

2. **One code path.** ``workers == 1``, a single task, or a platform without
   ``fork`` all run the SAME callables in the SAME process, in sorted key
   order. There is no separate "serial implementation" to drift from the
   parallel one -- the only difference is where the callable is invoked.

3. **Processes, not threads.** The work is pure-Python arithmetic under a
   GIL, so a thread pool would buy nothing. Workers are ``fork`` children:
   the task callables are closures over the read's already-loaded tables and
   are NOT picklable, so they are never pickled -- they are inherited through
   the fork and looked up by key in the child. Only the key (text) travels in
   and only the task's return value travels back, which is why every task
   must return something picklable.

What must NOT come through here
-------------------------------

A task must be a pure function of state that is already frozen when the fork
happens. In particular:

* **No resident encoder, embedder or tokenizer.** Two concurrent CPU
  embedders have already broken jitter-pair reproducibility once in this
  program; a stage that touches an embedding path stays serial and its read
  note says so. This module never makes that safe and does not try to.
* **No shared mutable state and no shared output file.** A fork child gets a
  copy; a mutation in the child is invisible to the parent and to its
  siblings. A task that must persist something writes its OWN path.
* **No process-global RNG.** A bootstrap task must construct its own
  ``random.Random(seed)`` so its replicate sequence is a function of the seed
  alone and not of how many tasks ran before it in the same process. Every
  caller in this repository already does: ``analysis.paired._bootstrap_result``
  seeds a fresh ``random.Random`` per bootstrap.

Worker count
------------

:func:`resolve_workers` is the ONE place that decides how many workers a read
uses. It defaults to :data:`CAMPAIGN_WORKER_CAP`, the pipeline rule's
preparation cap while a campaign is in flight -- never to the host's core
count. An idle host is a deliberate ``--workers`` (or
``SAEA_ANALYSIS_WORKERS``) away, not the default.
"""

from __future__ import annotations

import multiprocessing
import os
from typing import Callable, Mapping, TypeVar

__all__ = [
    "CAMPAIGN_WORKER_CAP",
    "DEFAULT_WORKERS",
    "IDLE_HOST_WORKERS",
    "MAX_WORKERS",
    "WORKERS_ENV",
    "ParallelReadError",
    "add_workers_argument",
    "map_by_key",
    "resolve_workers",
]


class ParallelReadError(RuntimeError):
    """The fan-out description is unsafe or unusable."""


#: CLAUDE.md's pipeline rule: CPU preparation runs 8 workers while a campaign
#: is in flight. That is the default, so a read started during a flight cannot
#: starve the flight by accident.
CAMPAIGN_WORKER_CAP = 8

#: The owner's idle-host baseline for CPU preprocessing on this 24-core host.
#: Documented here as the number to PASS, never as a default.
IDLE_HOST_WORKERS = 20

DEFAULT_WORKERS = CAMPAIGN_WORKER_CAP

#: An absolute sanity ceiling, written down rather than probed. This module
#: never calls ``os.cpu_count()``: reading the core count and using all of it
#: is exactly the failure mode the default is meant to avoid.
MAX_WORKERS = 32

WORKERS_ENV = "SAEA_ANALYSIS_WORKERS"

K = TypeVar("K")
V = TypeVar("V")


def resolve_workers(requested: object = None, *, cap: int | None = None) -> int:
    """The one decision point for how many workers a read fans out over.

    ``requested`` is a ``--workers`` value (or ``None``). ``None`` falls back
    to ``$SAEA_ANALYSIS_WORKERS`` and then to :data:`DEFAULT_WORKERS`. The
    result is clamped into ``[1, min(cap, MAX_WORKERS)]``; ``cap`` is the
    caller's own knowledge of how many independent units it actually has, so
    a read with four bootstraps never forks eight children.
    """

    if requested is None:
        raw = os.environ.get(WORKERS_ENV)
        if raw is None or raw.strip() == "":
            requested = DEFAULT_WORKERS
        else:
            try:
                requested = int(raw.strip())
            except ValueError as error:
                raise ParallelReadError(
                    f"{WORKERS_ENV}={raw!r} is not an integer"
                ) from error
    if isinstance(requested, bool) or not isinstance(requested, int):
        raise ParallelReadError("workers must be a positive integer")
    if requested <= 0:
        raise ParallelReadError("workers must be a positive integer")
    ceiling = MAX_WORKERS
    if cap is not None:
        if isinstance(cap, bool) or not isinstance(cap, int) or cap <= 0:
            raise ParallelReadError("cap must be a positive integer")
        ceiling = min(ceiling, cap)
    return max(1, min(int(requested), ceiling))


#: Set in the parent immediately before the pool forks, read in the child.
#: Never pickled: a closure over a read's loaded tables cannot be, and
#: pickling the tables per task would cost more than the task.
_FORKED_TASKS: dict[object, Callable[[], object]] = {}


def _run_forked_task(key: object) -> object:
    try:
        task = _FORKED_TASKS[key]
    except KeyError:  # pragma: no cover - a fork that did not inherit the table
        raise ParallelReadError(
            f"task {key!r} was not inherited by the worker process"
        ) from None
    return task()


def _fork_context() -> object | None:
    """The ``fork`` start method, or ``None`` where the platform has none."""

    try:
        return multiprocessing.get_context("fork")
    except (ValueError, AttributeError):  # Windows, or a stripped build
        return None


def map_by_key(
    tasks: Mapping[K, Callable[[], V]],
    *,
    workers: int,
) -> dict[K, V]:
    """Run every task and return ``{key: value}`` in SORTED KEY ORDER.

    ``tasks`` values are zero-argument callables; each must be a pure
    function of state already frozen in the parent and must return a
    picklable value. Keys must be mutually sortable -- text keys, in
    practice, which is also what makes the emitted order stable and
    reviewable.

    Runs in-process (still in sorted key order) when there is nothing to
    gain: one task or fewer, ``workers <= 1``, or no ``fork``.
    """

    if not isinstance(workers, int) or isinstance(workers, bool) or workers <= 0:
        raise ParallelReadError("workers must be a positive integer")
    try:
        keys = sorted(tasks)
    except TypeError as error:
        raise ParallelReadError("task keys must be mutually sortable") from error
    for key in keys:
        if not callable(tasks[key]):
            raise ParallelReadError(f"task {key!r} is not callable")

    if len(keys) <= 1 or workers == 1:
        return {key: tasks[key]() for key in keys}
    context = _fork_context()
    if context is None:
        return {key: tasks[key]() for key in keys}

    global _FORKED_TASKS
    if _FORKED_TASKS:
        raise ParallelReadError(
            "map_by_key is already fanning out in this process; nested fan-out "
            "would oversubscribe the host and is refused"
        )
    _FORKED_TASKS = dict(tasks)
    try:
        # chunksize=1: the units are coarse and can differ in cost, so hand
        # them out one at a time rather than in fixed blocks.
        with context.Pool(processes=min(workers, len(keys))) as pool:
            values = pool.map(_run_forked_task, keys, chunksize=1)
    finally:
        _FORKED_TASKS = {}
    # ``Pool.map`` returns results in ARGUMENT order, not completion order,
    # and ``keys`` is sorted -- so this mapping is sorted and reproducible.
    return {key: value for key, value in zip(keys, values)}


def add_workers_argument(parser: object, *, help_suffix: str = "") -> None:
    """Register the uniform ``--workers`` flag on an ``argparse`` parser.

    One spelling, one default, one help text across every read, so the flag
    cannot mean 8 in one CLI and "every core" in the next.
    """

    parser.add_argument(  # type: ignore[attr-defined]
        "--workers",
        type=int,
        default=None,
        help=(
            "worker processes for this read's independent units "
            f"(default {DEFAULT_WORKERS}, the campaign preparation cap; "
            f"${WORKERS_ENV} overrides the default; {IDLE_HOST_WORKERS} is the "
            "owner's idle-host baseline). The numbers a read produces do not "
            "depend on this value." + (f" {help_suffix}" if help_suffix else "")
        ),
    )
