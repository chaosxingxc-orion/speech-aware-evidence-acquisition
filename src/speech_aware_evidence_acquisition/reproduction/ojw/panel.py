"""Join independent native callers in one existing node-stage executor.

Each caller retains its client, budgets, requests and trace sink. This rendezvous
changes scheduling only; it cannot authorize, seal, score or retry a flight.
"""

from __future__ import annotations

import asyncio
import contextvars
import threading
from dataclasses import dataclass
from time import monotonic_ns


class NativeWorkflowPanelError(ValueError):
    """Refuse ambiguous identity, incompatible scheduling or repeated execution."""


@dataclass(frozen=True)
class NativePanelMember:
    run_id: str
    attempt_id: str
    job_keys: tuple[tuple[str, str | None], ...]

    def __post_init__(self):
        if any(
            not isinstance(s, str) or not s.strip()
            for s in (self.run_id, self.attempt_id)
        ):
            raise NativeWorkflowPanelError(
                "panel members need explicit run and attempt identities"
            )
        if not isinstance(self.job_keys, (tuple, list)) or not self.job_keys:
            raise NativeWorkflowPanelError(
                "panel members need an exact nonempty ordered job roster"
            )
        keys = []
        for key in self.job_keys:
            if (
                not isinstance(key, (tuple, list))
                or len(key) != 2
                or not isinstance(key[0], str)
                or not key[0].strip()
                or (
                    key[1] is not None
                    and (not isinstance(key[1], str) or not key[1].strip())
                )
            ):
                raise NativeWorkflowPanelError(
                    "job identity is sample id plus optional execution-unit id"
                )
            keys.append(tuple(key))
        if len(set(keys)) != len(keys):
            raise NativeWorkflowPanelError("panel member repeats an execution job")
        object.__setattr__(self, "job_keys", tuple(keys))


@dataclass
class _Call:
    member: NativePanelMember
    states: list
    options: dict
    context: contextvars.Context


@dataclass(frozen=True)
class _Job:
    call: _Call
    local_index: int

    @property
    def state(self):
        return self.call.states[self.local_index]


class NativeWorkflowPanel:
    """Rendezvous separately owned synchronous callers before any model work."""

    _COMMON = (
        "branch_count",
        "slot_count",
        "queue_depth",
        "workflow_timeout_seconds",
        "local_tool_workers",
        "node_pipeline_order",
        "node_pipeline_group_size",
        "node_pipeline_prepare_workers",
        "node_pipeline_max_jobs",
    )
    _CALLBACKS = ("episode_invoker", "sample_timing_sink", "node_pipeline_timing_sink")

    def __init__(self, panel_id, members):
        members = tuple(members)
        if (
            not isinstance(panel_id, str)
            or not panel_id.strip()
            or not 2 <= len(members) <= 8
            or any(not isinstance(m, NativePanelMember) for m in members)
            or len({m.run_id for m in members}) != len(members)
            or len({m.attempt_id for m in members}) != len(members)
        ):
            raise NativeWorkflowPanelError(
                "panel needs an id and two to eight independent members"
            )
        self.panel_id = panel_id
        self.members = members
        self.submitted_ns = monotonic_ns()
        self._condition = threading.Condition()
        self._calls = {}
        self._common = None
        self._failure = None
        self._running = False
        self._done = False

    def member(self, run_id, attempt_id):
        for member in self.members:
            if member.run_id == run_id and member.attempt_id == attempt_id:
                return member
        raise NativeWorkflowPanelError("runtime identity is outside the declared panel")

    def abort(self, error):
        """Stop admission; never wake owners while their model workers are live."""
        with self._condition:
            if self._failure is None:
                self._failure = error
            if not self._running:
                self._condition.notify_all()

    def assert_completed(self, run_id, attempt_id):
        """Refuse a member returning through a path outside the shared executor."""
        with self._condition:
            self._assert_live()
            self.member(run_id, attempt_id)
            if not self._done or run_id not in self._calls:
                raise NativeWorkflowPanelError(
                    "panel member bypassed the declared node-stage execution"
                )

    def _assert_live(self):
        with self._condition:
            if self._failure is not None:
                raise self._failure

    def execute(self, run_id, attempt_id, states, *, job_keys, **options):
        """Wait for every exact member and dispatch its original invoker once."""
        leader = False
        try:
            with self._condition:
                self._assert_live()
                member = self.member(run_id, attempt_id)
                if self._done or run_id in self._calls:
                    raise NativeWorkflowPanelError(
                        "panel member execution cannot be repeated"
                    )
                states = list(states)
                if tuple(job_keys) != member.job_keys or len(states) != len(
                    member.job_keys
                ):
                    raise NativeWorkflowPanelError(
                        "panel job roster differs from its registered member"
                    )
                if set(options) - set(self._COMMON + self._CALLBACKS):
                    raise NativeWorkflowPanelError(
                        "panel accepts only the declared native stage scheduler"
                    )
                options = dict(options)
                options.setdefault("local_tool_workers", 0)
                order = options.get("node_pipeline_order")
                if not isinstance(order, (tuple, list)):
                    raise NativeWorkflowPanelError(
                        "panel needs an explicit node pipeline"
                    )
                options["node_pipeline_order"] = tuple(order)
                common = {key: options.get(key) for key in self._COMMON}
                if (
                    common["branch_count"] != 1
                    or common["node_pipeline_group_size"] != len(member.job_keys)
                    or type(common["node_pipeline_max_jobs"]) is not int
                    or sum(len(m.job_keys) for m in self.members)
                    > common["node_pipeline_max_jobs"]
                    or any(not callable(options.get(k)) for k in ("episode_invoker",))
                    or any(
                        options.get(k) is not None and not callable(options[k])
                        for k in self._CALLBACKS[1:]
                    )
                ):
                    raise NativeWorkflowPanelError(
                        "panel group, bound or native callbacks are invalid"
                    )
                if self._common is not None and common != self._common:
                    raise NativeWorkflowPanelError(
                        "panel members have different scheduling envelopes"
                    )
                previous_states = {
                    id(s) for call in self._calls.values() for s in call.states
                }
                if len({id(s) for s in states}) != len(states) or any(
                    id(s) in previous_states for s in states
                ):
                    raise NativeWorkflowPanelError(
                        "panel members must own separate state objects"
                    )
                self._common = common
                self._calls[run_id] = _Call(
                    member, states, options, contextvars.copy_context()
                )
                if len(self._calls) == len(self.members):
                    self._running = leader = True
                else:
                    while not self._done and (self._running or self._failure is None):
                        self._condition.wait()
                    self._assert_live()
                    return states
            # Only the final arriving caller runs the shared event loop. Other
            # callers keep their clients and sinks open until all contacts drain.
            try:
                self._execute_combined()
            except BaseException as error:
                self.abort(error)
            finally:
                with self._condition:
                    self._running = False
                    self._done = True
                    self._condition.notify_all()
            self._assert_live()
            return states
        except BaseException as error:
            self.abort(error)
            if not leader:
                with self._condition:
                    while self._running:
                        self._condition.wait()
            raise

    def _execute_combined(self):
        from .runner import execute_speech_agent_workflows

        jobs = [
            _Job(self._calls[m.run_id], i)
            for m in self.members
            for i in range(len(m.job_keys))
        ]

        def checked(callback):
            def invoke(*args):
                self._assert_live()
                return callback(*args)

            return invoke

        async def invoke(job, contact, session, *, run_prepare, run_local=None):
            async def owned_contact(callback, **kw):
                self._assert_live()
                return await contact(checked(callback), **kw)

            async def owned_prepare(callback, **kw):
                self._assert_live()
                return await run_prepare(checked(callback), **kw)

            async def owned_local(callback):
                self._assert_live()
                return await run_local(checked(callback))

            async def run():
                kwargs = {"run_prepare": owned_prepare}
                if run_local is not None:
                    kwargs["run_local"] = owned_local
                return await job.call.options["episode_invoker"](
                    job.state, owned_contact, session, **kwargs
                )

            # Creating a coroutine in another Context does not run it there.
            # Give each native workflow its owner's context on a distinct Task.
            await asyncio.create_task(run(), context=job.call.context.copy())

        def timing(job, event):
            sink = job.call.options.get("sample_timing_sink")
            if sink is not None:
                own = {
                    **event,
                    "panel_id": self.panel_id,
                    "panel_admission_index": event["admission_index"],
                    "panel_expected_samples": event["expected_samples"],
                    "panel_execution_started_ns": event["batch_started_ns"],
                    "batch_started_ns": self.submitted_ns,
                    "admission_index": job.local_index,
                    "expected_samples": len(job.call.states),
                }
                job.call.context.copy().run(sink, job.state, own)

        def node_timing(job, event):
            sink = job.call.options.get("node_pipeline_timing_sink")
            if sink is not None:
                job.call.context.copy().run(
                    sink, job.state, {**event, "panel_id": self.panel_id}
                )

        execute_speech_agent_workflows(
            jobs,
            **self._common,
            episode_invoker=invoke,
            sample_timing_sink=timing,
            node_pipeline_timing_sink=node_timing,
        )


@dataclass(frozen=True)
class NativePanelParticipation:
    """Bind one runtime to its exact place in the declared panel."""

    panel: NativeWorkflowPanel
    member: NativePanelMember

    def __post_init__(self):
        if not isinstance(self.panel, NativeWorkflowPanel) or not isinstance(
            self.member, NativePanelMember
        ):
            raise NativeWorkflowPanelError("invalid panel participation")
        if self.panel.member(self.member.run_id, self.member.attempt_id) != self.member:
            raise NativeWorkflowPanelError("panel participation roster differs")

    def execute(self, run_id, states, **options):
        if run_id != self.member.run_id:
            error = NativeWorkflowPanelError(
                "native caller differs from its panel owner"
            )
            self.panel.abort(error)
            raise error
        return self.panel.execute(
            run_id,
            self.member.attempt_id,
            states,
            job_keys=tuple(
                (s.prepared.sample.sample_id, s.prepared.execution_unit_id)
                for s in states
            ),
            **options,
        )

    def receipt(self):
        import hashlib
        import json

        identities = [
            {"run_id": m.run_id, "attempt_id": m.attempt_id, "job_keys": m.job_keys}
            for m in self.panel.members
        ]
        return {
            "schema": "saea-native-workflow-panel-member-v1",
            "panel_id": self.panel.panel_id,
            "member_run_id": self.member.run_id,
            "member_attempt_id": self.member.attempt_id,
            "member_index": self.panel.members.index(self.member),
            "member_jobs": len(self.member.job_keys),
            "panel_jobs": sum(len(m.job_keys) for m in self.panel.members),
            "panel_members_sha256": hashlib.sha256(
                json.dumps(identities, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest(),
        }
