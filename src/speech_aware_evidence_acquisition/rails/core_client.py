"""CoreClient: the seam every rails runner call reaches "the model" through --
kept SEPARATE from ``core.model.FrozenCoreAdapter`` deliberately.

``FrozenCoreAdapter`` is the production, gate-enforced, budget-metered
request path (``PayloadBindingContext``, ``AttemptStore``, ``TraceSink``,
the D2 arm-field allowlist -- ``core.model.adapter``); wiring it in here
would mean this zero-model-contact engineering skeleton also has to
construct a live ``FrozenCoreGate``, an attempt store and a verified split,
none of which a rails-only test fixture has any business building, and B0's
mission is explicit: engineering only, ZERO model contact. ``CoreClient`` is
instead the MINIMAL request shape a ``TaskAdapter``'s assembled messages
need -- a future model-touching task can implement a ``CoreClient`` that
internally delegates to ``FrozenCoreAdapter`` without changing this
Protocol's shape or any caller of it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Mapping, Protocol, Sequence, runtime_checkable


@runtime_checkable
class CoreClient(Protocol):
    """One completion call: chat-style ``messages`` in, response text out.
    No implementation in THIS module ever touches a real model -- see
    :class:`MockCoreClient` below, the only implementation this engineering
    mission constructs."""

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
    ) -> str: ...


@dataclass
class MockCoreClient:
    """Deterministic, in-process ``CoreClient`` for tests -- zero model
    contact, zero I/O, zero network. ``responder`` resolves each call's
    response text from the messages it was given (default: a stable canned
    string plus a request counter, so distinct calls never collide);
    ``calls`` records every ``(messages, decoding_params)`` pair actually
    sent, for tests that assert on what a runner/adapter actually
    assembled."""

    responder: Callable[[Sequence[Mapping[str, object]]], str] | None = None
    calls: list[tuple[tuple[Mapping[str, object], ...], Mapping[str, object]]] = field(
        default_factory=list
    )

    def complete(
        self,
        messages: Sequence[Mapping[str, object]],
        *,
        decoding_params: Mapping[str, object] | None = None,
    ) -> str:
        recorded_params = dict(decoding_params) if decoding_params else {}
        self.calls.append((tuple(messages), recorded_params))
        if self.responder is not None:
            return self.responder(messages)
        return f"mock-response-{len(self.calls)}"
