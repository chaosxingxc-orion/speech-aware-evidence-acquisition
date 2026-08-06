"""``FrozenCoreAdapter``: the gate-enforced, one-time-metered model request path.

Split out of the former monolithic ``core/model.py`` (R0 repair refactor
stage 1, pure move, no behaviour change).
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from ...contracts import ExecutionPlan, assert_information_boundary
from ...e0.d2_leakage import ARM_VISIBLE_FIELDS
from ..attempts import AttemptError, AttemptStore
from ..base import CoreError, PayloadBindingContext
from ..tracing import TraceSink
from . import FrozenCoreError
from .binding import _PayloadBindingMixin

# The exact set of decoding_params keys the frozen core will ever accept. This is
# the governance choke point (FrozenCoreAdapter.request): a config-supplied
# decoding_params mapping can never smuggle a "messages"/"model"/"stream"/... key
# through to the transport, where it would otherwise silently replace the
# constructed chat-completions body (dropping audio while the adapter still
# meters it as delivered).
ALLOWED_DECODING_KEYS = frozenset(
    {
        "temperature",
        "seed",
        "top_p",
        "top_k",
        "min_p",
        "max_tokens",
        "presence_penalty",
        "frequency_penalty",
    }
)


@dataclass(frozen=True)
class CoreResponse:
    text: str
    usage: Mapping[str, int]
    request_sha256: str
    response_sha256: str
    # R0 repair T6 (I7, run-bundle closure): sha256 of `text` alone. The
    # adapter only ever hashes the raw transport bytes for `response_sha256`
    # -- and those bytes are not exactly re-derivable later from `text` plus
    # `usage` alone (the transport builds them from a server-controlled
    # `usage` mapping whose key order is not itself pinned anywhere). Minimal
    # adapter change so the outputs<->response binding IS strictly
    # re-verifiable after the fact: `core.bundle.verify_bundle` recomputes
    # this hash from the outputs row's own `text` field and refuses on any
    # mismatch -- closing the reproduced defect where a row's `text` could be
    # mutated post-hoc while `response_sha256` stayed stale and unchecked.
    response_text_sha256: str
    latency_seconds: float


def _canonical(payload: Mapping[str, object]) -> bytes:
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class FrozenCoreAdapter(_PayloadBindingMixin):
    def __init__(
        self,
        gate: object,
        plan: ExecutionPlan,
        arm: str,
        transport: Callable[[bytes], bytes],
        sink: TraceSink,
        binding: PayloadBindingContext,
    ) -> None:
        if arm not in ARM_VISIBLE_FIELDS:
            raise FrozenCoreError(
                f"unknown arm {arm!r}; D2-frozen arms are {sorted(ARM_VISIBLE_FIELDS)}"
            )
        # Fail-closed constructor discipline (R0 repair T3): a binding context
        # is a required argument (no default -- omitting it is a TypeError
        # before this body ever runs) and is itself structurally validated
        # here. There is no "no checks" adapter: every request() call below
        # trusts only what this context says was verified for this run.
        if not isinstance(binding, PayloadBindingContext):
            raise FrozenCoreError(
                "FrozenCoreAdapter requires a PayloadBindingContext binding payload "
                f"values to the verified split and loader facts; got {type(binding).__name__}"
            )
        try:
            binding.validate()
        except CoreError as error:
            raise FrozenCoreError(f"invalid payload binding context: {error}") from error
        if binding.carrier_lock_key != plan.carrier_lock_key:
            raise FrozenCoreError(
                "payload binding context carrier_lock_key "
                f"{binding.carrier_lock_key!r} does not match the execution plan "
                f"carrier_lock_key {plan.carrier_lock_key!r}"
            )
        # M-3 (external-threat-model review): the gate returns the umbrella
        # lock's SHA-256 it read exactly once while checking this touch; carry
        # it so it lands in cost_summary() -> RunResult.cost -> the run
        # manifest (core.driver.run_experiment / core.bundle), instead of
        # "dataset rev" staying a hand-supplied ledger cell. A duck-typed test
        # gate that returns nothing (most of this module's own unit tests use
        # one) simply yields None here -- harmless, just an absent hash.
        lock_sha256 = gate.assert_model_touch_allowed(plan)
        self._lock_sha256 = lock_sha256 if isinstance(lock_sha256, str) else None
        # I-4 (external-threat-model review): re-verify THIS run's actual
        # media -- exactly the samples its verified split can touch, via
        # `binding.media_relpaths` -- against D1's frozen per-file identity,
        # as a re-measured FILE, never merely as a receipt's claim. Duck-typed
        # like the session_check below: the one real gate
        # (`contracts.FrozenCoreGate`) always implements this; test doubles
        # isolating unrelated adapter behavior (allowlist/budget/tracing/etc.)
        # are unaffected if they don't. `binding.media_relpaths` is likewise
        # optional on `PayloadBindingContext` (empty by default) for the same
        # reason -- see that field's own docstring -- but the one true
        # production caller (`core.driver.run_experiment`) always supplies it,
        # so a real run is never silently exempted from this check.
        media_identity_check: Callable[[str, Mapping[str, tuple[str, float]]], None] | None = (
            getattr(gate, "verify_media_identity", None)
        )
        if media_identity_check is not None and binding.media_relpaths:
            media_identity_check(
                binding.carrier_lock_key,
                {
                    sample_id: (binding.media_relpaths[sample_id], binding.sample_facts[sample_id][0])
                    for sample_id in binding.allowed_sample_ids
                },
            )
        # R0 repair T5 fix-3 (I5, reviewer-flagged): a second, adapter-level
        # enforcement call site for session liveness+identity, BEFORE any
        # attempt slot below is consumed. Duck-typed rather than a new
        # required constructor parameter: binary/PID/process-image identity
        # is inherently specific to a subprocess-backed HTTP transport (the
        # only registered transport with any notion of it at all), not a
        # generic concept every Callable[[bytes], bytes] transport shares
        # the way payload/media confinement (I3/I4) is -- so this does not
        # force every bare-callable test transport in the repo to grow a
        # session. A transport lacking assert_session_alive() is completely
        # unaffected; ``core.model.LlamaServerTransport`` -- the one real
        # transport -- has one, and calling it here is a genuinely
        # independent second enforcement site (catches, e.g., a future
        # refactor that accidentally drops the transport's own per-call
        # re-check) even though the underlying verification code
        # (``core.session.assert_session_alive``) is shared, not
        # reimplemented twice the way I3/I4's rails are.
        session_check: Callable[[], None] | None = getattr(
            transport, "assert_session_alive", None
        )
        if session_check is not None:
            session_check()
        # One-time attempt accounting (R0 repair T4, invariant I6). This is the
        # ONLY model request path (module docstring), so it is the correct place
        # to bind "a model touch is about to become possible" to "a durable,
        # one-time attempt token was reserved" -- regardless of which `gate`
        # object (real or a test double) was handed in. See the task report for
        # why this lives here rather than inside FrozenCoreGate.
        attempt_id = plan.attempt_id
        if not isinstance(attempt_id, str) or not attempt_id.strip():
            raise FrozenCoreError(
                "execution plan attempt_id must be a non-empty string; a plan "
                "without a valid attempt_id can never authorize a model touch "
                "(R0 repair T4, invariant I6)"
            )
        attempts_root = Path(binding.data_root) / "attempts"
        store = AttemptStore(attempts_root)
        try:
            handle = store.open_attempt(
                plan.run_id,
                attempt_id,
                carrier_lock_key=plan.carrier_lock_key,
                reserved_calls=plan.planned_model_calls,
                reserved_audio_seconds=plan.planned_speech_audio_seconds,
            )
        except AttemptError as error:
            raise FrozenCoreError(f"attempt accounting refused: {error}") from error
        self._plan = plan
        self._arm = arm
        self._allowlist = frozenset(ARM_VISIBLE_FIELDS[arm])
        self._transport = transport
        self._session_check = session_check
        self._sink = sink
        self._binding = binding
        # R0 repair r0-repair (I3): NOT a `prior_actual_usage` snapshot frozen
        # once here at construction -- see the fresh, per-request re-read in
        # `request()` below for why. The store itself is cheap to hold (it is
        # just `attempts_root`, already resolved).
        self._store = store
        self._attempt_handle = handle
        self._calls_used = 0
        self._audio_seconds_used = 0.0
        self._latency_total = 0.0
        self._prompt_tokens = 0
        self._completion_tokens = 0
        # R0 repair T7 (I8): zero today (no registered policy is tool-using),
        # but wired through the SAME metering choke point every other
        # per-request cost figure already flows through -- see
        # record_tool_call below -- so a future tool-using policy (X-series)
        # never has to invent a parallel accounting path.
        self._tool_calls = 0

    def request(self, payload: Mapping[str, object]) -> CoreResponse:
        keys = set(payload)
        if keys != self._allowlist:
            raise FrozenCoreError(
                f"arm {self._arm!r} allowlist violation: "
                f"extra={sorted(keys - self._allowlist)} "
                f"missing={sorted(self._allowlist - keys)}"
            )
        if "decoding_params" in self._allowlist:
            decoding_params = payload["decoding_params"]
            if not isinstance(decoding_params, Mapping):
                raise FrozenCoreError("payload decoding_params must be a mapping")
            disallowed_decoding_keys = set(decoding_params) - ALLOWED_DECODING_KEYS
            if disallowed_decoding_keys:
                raise FrozenCoreError(
                    "payload decoding_params contains disallowed keys: "
                    f"{sorted(disallowed_decoding_keys)}"
                )
        assert_information_boundary(dict(payload))
        audio_seconds = payload["audio_seconds"]
        if (
            isinstance(audio_seconds, bool)
            or not isinstance(audio_seconds, (int, float))
            or not math.isfinite(audio_seconds)
            or audio_seconds <= 0
        ):
            raise FrozenCoreError("payload audio_seconds must be a finite positive number")
        self._enforce_payload_binding(payload, audio_seconds)
        # Row-level budget check (R0 repair T4/I6, race-hardened R0 repair r0-repair/I3):
        # the ceiling is the SAME plan.planned_* value regardless of which attempt is
        # spending it, so actual usage already persisted by OTHER (e.g. crashed, or a
        # second concurrently-live) attempt on this same run_id counts against it too --
        # not just what THIS attempt has used so far. The reproduced I3 defect was
        # reading that other-attempts total ONCE at __init__ and comparing every later
        # request against that frozen snapshot: two adapters constructed back to back
        # (both before either had recorded any usage) each saw "0 spent elsewhere" for
        # their entire lifetime, so together they could spend up to 2x the row's budget.
        # The fix re-reads sibling usage FRESH on every request, excluding only this
        # attempt's own file (which self._calls_used/self._audio_seconds_used already
        # track exactly in-process, since this attempt's file has exactly one writer).
        # This keeps the check-before-persist order the existing budget-exhaustion tests
        # depend on ("the refused request must never have been persisted as spent"): the
        # fresh sibling read happens before this attempt's own record_usage call, so a
        # request that would cross the budget is refused before anything about it is
        # durably written -- never sent-but-unrecorded, and never persisted-then-refused.
        # Race-safety: correct against sequential/interleaved attempts on the same
        # run_id -- by the time THIS request checks, any sibling attempt's ALREADY
        # completed record_usage call is visible here, so total spend across all
        # attempts on a run_id can never exceed the row's planned budget. It does not
        # (and, without a cross-process lock in core.attempts, cannot) close a true
        # simultaneous-instant double-read between two OS threads/processes; that
        # primitive belongs to core.attempts, not this adapter, and is unchanged here.
        sibling_calls, sibling_audio_seconds = self._store.prior_actual_usage(
            self._plan.run_id, exclude_attempt_id=self._attempt_handle.attempt_id
        )
        if sibling_calls + self._calls_used + 1 > self._plan.planned_model_calls:
            raise FrozenCoreError(
                f"call budget exhausted: plan {self._plan.run_id} allows "
                f"{self._plan.planned_model_calls} calls "
                f"({sibling_calls} already spent by other attempts on this run, "
                f"{self._calls_used} by this attempt)"
            )
        if (
            sibling_audio_seconds + self._audio_seconds_used + float(audio_seconds)
            > self._plan.planned_speech_audio_seconds
        ):
            raise FrozenCoreError(
                f"audio budget exhausted: plan {self._plan.run_id} allows "
                f"{self._plan.planned_speech_audio_seconds} speech audio seconds "
                f"({sibling_audio_seconds} already spent by other attempts on this "
                f"run, {self._audio_seconds_used} by this attempt)"
            )
        # R0 repair T5 fix-3 (I5): re-verify RIGHT BEFORE this specific
        # request's trace/budget side effects, not merely once at
        # construction -- a transport instance is reused for an entire run
        # (potentially many calls / hours of audio, per the plan's own
        # declared budget -- no numeric ceiling since the 2026-08-06 owner
        # amendment retired the first-slice caps), so a session valid at
        # construction time proves nothing about who is listening ten calls
        # later.
        if self._session_check is not None:
            self._session_check()
        request_id = str(payload["request_id"])
        request_bytes = _canonical(payload)
        request_sha256 = hashlib.sha256(request_bytes).hexdigest()
        self._sink.emit(
            "MODEL_REQUEST",
            f"{request_id}/request",
            {"arm": self._arm, "payload": dict(payload), "payload_sha256": request_sha256},
        )
        # Metering counts the attempt as soon as the budget checks above have
        # passed and the request is about to leave the process — a transport
        # that raises (or returns a malformed response) after being invoked
        # must not be under-reported as free; a sent request is a consumed
        # request regardless of what comes back. R0 repair T4 (I6): the durable
        # attempt-file write happens BEFORE the transport call, not after --
        # a process crash between this line and the transport call must still
        # leave the spend on disk, not only in memory that dies with it.
        try:
            new_calls_used, new_audio_seconds_used = self._attempt_handle.record_usage(
                calls=1, audio_seconds=float(audio_seconds)
            )
        except AttemptError as error:
            raise FrozenCoreError(f"attempt accounting refused: {error}") from error
        # Adopt record_usage's own authoritative return value (R0 repair r0-repair,
        # I3) instead of a locally-incremented shadow counter -- this attempt's file
        # has exactly one writer (this handle), so the two are always numerically
        # identical, but tracking the return value directly means there is nothing
        # left to silently drift out of sync with what was actually persisted.
        self._calls_used = new_calls_used
        self._audio_seconds_used = new_audio_seconds_used
        started = time.monotonic()
        response_bytes = self._transport(request_bytes)
        latency = time.monotonic() - started
        response_sha256 = hashlib.sha256(response_bytes).hexdigest()
        try:
            parsed = json.loads(response_bytes.decode("utf-8"))
            text = parsed["text"]
            usage = {str(k): int(v) for k, v in dict(parsed.get("usage", {})).items()}
        except (KeyError, TypeError, ValueError, UnicodeError) as error:
            raise FrozenCoreError(
                f"transport returned a malformed response: {error}"
            ) from error
        if not isinstance(text, str):
            raise FrozenCoreError(
                f"transport returned a non-string text field: {type(text).__name__}"
            )
        response_text_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        self._sink.emit(
            "MODEL_RESPONSE",
            f"{request_id}/response",
            {
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
                "text": text,
                "usage": usage,
            },
        )
        self._latency_total += latency
        self._prompt_tokens += usage.get("prompt_tokens", 0)
        self._completion_tokens += usage.get("completion_tokens", 0)
        self._sink.emit(
            "COST",
            f"{request_id}/cost",
            {
                "calls": 1,
                "audio_seconds": float(audio_seconds),
                "latency_seconds": latency,
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            },
        )
        return CoreResponse(
            text=text,
            usage=usage,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            response_text_sha256=response_text_sha256,
            latency_seconds=latency,
        )

    def record_tool_call(self, count: int = 1) -> None:
        """Increment the run's tool-call counter (R0 repair T7, invariant I8).

        Zero today: R0 registers no tool-using policy (X-series work). This
        exists now so that when one arrives it increments the SAME choke
        point every other cost figure already flows through
        (``cost_summary`` below) via the adapter every ``core.base.
        SampleContext`` already carries (``ctx.adapter.record_tool_call()``),
        rather than inventing a new, parallel accounting path.
        """

        if isinstance(count, bool) or not isinstance(count, int) or count <= 0:
            raise FrozenCoreError(
                f"record_tool_call count must be a positive integer, got {count!r}"
            )
        self._tool_calls += count

    def cost_summary(self) -> dict[str, object]:
        return {
            "calls_used": self._calls_used,
            "audio_seconds_used": self._audio_seconds_used,
            "latency_seconds_total": self._latency_total,
            "prompt_tokens_total": self._prompt_tokens,
            "completion_tokens_total": self._completion_tokens,
            "tool_calls": self._tool_calls,
            # M-3: the umbrella lock's SHA-256, read exactly once by the gate
            # while checking this touch (contracts.FrozenCoreGate.
            # assert_model_touch_allowed) -- carried through so it lands in
            # the run manifest rather than "dataset rev" staying hand-supplied.
            "umbrella_lock_sha256": self._lock_sha256,
        }
