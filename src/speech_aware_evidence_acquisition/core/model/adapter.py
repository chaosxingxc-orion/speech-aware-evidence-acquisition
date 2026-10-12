"""``FrozenCoreAdapter``: the gate-enforced, one-time-metered model request path.

Split out of the former monolithic ``core/model.py`` (R0 repair refactor
stage 1, pure move, no behaviour change). R0 repair refactor stage 2 (part C):
the constructor's gate/media-identity/session/attempt-open lifecycle moved to
``lifecycle.py``'s own ``_AttemptLifecycleMixin`` (``_open_gate_and_attempt``,
a pure move, mirroring ``binding.py``'s own mixin), and the per-request value
types (``CoreResponse``, ``ALLOWED_DECODING_KEYS``, ``_canonical``) moved to
``request_types.py`` -- both again purely for file size; every name stays
importable from exactly ``core.model`` (this package's own ``__init__.py``).
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import threading
import time
from typing import Callable, Mapping

from ...contracts import ExecutionPlan, assert_information_boundary
from ...e0.d2_leakage import ARM_VISIBLE_FIELDS
from ..attempts import AttemptError
from ..base import CoreError, PayloadBindingContext
from ..tracing import TraceSink
from . import FrozenCoreError
from .binding import _PayloadBindingMixin
from .lifecycle import _AttemptLifecycleMixin
from ..reasoning_knobs import ReasoningKnobError, validate_request_controls
from .request_types import (
    ALLOWED_DECODING_KEYS,
    MAX_TOP_LOGPROBS,
    CoreResponse,
    _canonical,
    native_tool_request_controls,
)
from .slices import SliceRegistry


def _wire_provenance(parsed: object) -> dict[str, object] | None:
    """Validate and normalize transport-supplied exact wire provenance."""

    if not isinstance(parsed, Mapping):
        return None
    b64 = parsed.get("wire_response_b64")
    digest = parsed.get("wire_response_sha256")
    if b64 is None and digest is None:
        if "wire_finish_reason" in parsed:
            raise FrozenCoreError(
                "transport returned finish reason without wire response provenance"
            )
        return None
    if not isinstance(b64, str) or not isinstance(digest, str) or len(digest) != 64:
        raise FrozenCoreError("transport returned malformed wire response provenance")
    try:
        wire_bytes = base64.b64decode(b64, validate=True)
    except (ValueError, TypeError):
        raise FrozenCoreError("transport returned malformed wire response base64") from None
    if hashlib.sha256(wire_bytes).hexdigest() != digest:
        raise FrozenCoreError("transport wire response hash does not match its bytes")
    return {
        "response_b64": b64,
        "response_sha256": digest,
        "finish_reason": parsed.get("wire_finish_reason"),
    }


def _logprobs_sha256(logprobs: object) -> str:
    """sha256 of the canonical JSON form of a transport-forwarded
    ``choices[0].logprobs`` object (2026-09-08 logprob-as-judge probe).

    Same canonicalization every other identity cell in this study uses
    (``request_types._canonical``: ``ensure_ascii=False``, ``sort_keys=True``,
    tight separators) so a MODEL_LOGPROBS record is re-verifiable from its own
    ``logprobs`` field alone. Fail-closed on an unserializable object: the
    record must never carry a hash that nothing can recompute.
    """

    try:
        blob = json.dumps(
            logprobs, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise FrozenCoreError(
            f"transport forwarded a non-serializable logprobs object: {error}"
        ) from error
    return hashlib.sha256(blob).hexdigest()


class FrozenCoreAdapter(_PayloadBindingMixin, _AttemptLifecycleMixin):
    def __init__(
        self,
        gate: object,
        plan: ExecutionPlan,
        arm: str,
        transport: Callable[[bytes], bytes],
        sink: TraceSink,
        binding: PayloadBindingContext,
        slice_registry: SliceRegistry | None = None,
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
        # Slice-rail extension (obs-agent-loop, owner directive 2026-08-08):
        # optional and default-None, so every whole-file caller is untouched;
        # when supplied it must be the real registry type -- a duck-typed
        # stand-in here would silently weaken the derivation-chain guarantees
        # _enforce_slice_payload_binding relies on (fail-closed constructor
        # discipline, same as the binding context above).
        if slice_registry is not None and not isinstance(slice_registry, SliceRegistry):
            raise FrozenCoreError(
                "FrozenCoreAdapter slice_registry must be a core.model.SliceRegistry "
                f"or None; got {type(slice_registry).__name__}"
            )
        self._slice_registry = slice_registry
        # R0 repair refactor stage 2 (part C): the gate check, D1 media-
        # identity re-verification, transport session-liveness check, and the
        # durable one-time attempt open all live in
        # `_AttemptLifecycleMixin._open_gate_and_attempt` (lifecycle.py) now
        # -- same order, same exceptions, see that method's own docstring.
        lock_sha256, session_check, store, handle = self._open_gate_and_attempt(
            gate, plan, binding, transport, arm
        )
        self._lock_sha256 = lock_sha256
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
        # Intra-process metering atomicity (owner batching directive
        # 2026-08-08): under sample-level concurrency N tasks call request()
        # from worker threads THROUGH THIS ONE ADAPTER (the driver builds
        # exactly one per run). The lock makes [fresh sibling read -> budget
        # checks -> MODEL_REQUEST trace -> durable record_usage] atomic, so
        # two in-flight requests can never both pass the check on the same
        # stale usage figure and jointly overshoot the plan's budget -- the
        # simultaneous double-read the I3 comment below deliberately left to
        # a "cross-process lock in core.attempts" is hereby closed for the
        # in-process case (the cross-PROCESS case remains core.attempts's
        # concern, unchanged). The transport call itself stays OUTSIDE the
        # lock: holding it across a multi-second model request would
        # serialize the very concurrency batching exists to provide.
        self._metering_lock = threading.Lock()
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
            try:
                native_tool_request_controls(
                    decoding_params, native_tools="tool_schemas" in self._allowlist
                )
            except ValueError as error:
                raise FrozenCoreError(str(error)) from error
            try:
                validate_request_controls(decoding_params)
            except ReasoningKnobError as error:
                raise FrozenCoreError(str(error)) from error
            if "id_slot" in decoding_params:
                id_slot = decoding_params["id_slot"]
                if isinstance(id_slot, bool) or not isinstance(id_slot, int) or id_slot < 0:
                    raise FrozenCoreError(
                        f"decoding_params id_slot must be a non-negative integer, got "
                        f"{id_slot!r} — a config declares the sentinel 'per-sample' and "
                        "the batch executor resolves it to an allocated slot; this "
                        "executor did not (slot affinity is resolved by the ojw batch "
                        "path, reproduction/ojw/runner.py)"
                    )
            if "max_tokens" in decoding_params:
                max_tokens = decoding_params["max_tokens"]
                if (
                    isinstance(max_tokens, bool)
                    or not isinstance(max_tokens, int)
                    or max_tokens < 1
                ):
                    raise FrozenCoreError(
                        f"decoding_params max_tokens must be an integer >= 1, got "
                        f"{max_tokens!r} — a config may declare a PER-SAMPLE rule object "
                        "instead of an integer (core.flight.runtime."
                        "MAX_TOKENS_POLICY_KEY) and the flight runtime resolves it from "
                        "the sample's own audio_seconds; this executor did not, so the "
                        "cap would have reached the server unresolved"
                    )
            if "response_format" in decoding_params:
                response_format = decoding_params["response_format"]
                if not isinstance(response_format, Mapping):
                    raise FrozenCoreError(
                        "decoding_params response_format must be a mapping"
                    )
                response_type = response_format.get("type")
                if response_type == "json_object":
                    schema = response_format.get("schema", {})
                    if not isinstance(schema, Mapping):
                        raise FrozenCoreError(
                            "json_object response_format schema must be a mapping"
                        )
                elif response_type == "json_schema":
                    wrapper = response_format.get("json_schema")
                    if not isinstance(wrapper, Mapping) or not isinstance(
                        wrapper.get("schema"), Mapping
                    ):
                        raise FrozenCoreError(
                            "json_schema response_format must contain a mapping schema"
                        )
                else:
                    raise FrozenCoreError(
                        "decoding_params response_format type must be json_object or "
                        "json_schema"
                    )
            # Decode-confidence request (2026-09-08 logprob-as-judge probe).
            # `logprobs`/`top_logprobs` have been in ALLOWED_DECODING_KEYS
            # since the 2026-08-13 obs-replay-loop policy, but their VALUES
            # were never shape-checked here: a config typo reached the wire and
            # was refused by the server -- after this method had already
            # metered the call and durably recorded it as spent (the
            # record_usage-before-transport order below is deliberate and
            # unchanged). The two rules are the pinned server's own, restated
            # on this side of the wire so the refusal is free:
            # llama.cpp 04ccc72a `tools/server/server-common.cpp:1525-1529`
            # reads `logprobs` as a BOOLEAN and maps a true value to
            # `n_probs = top_logprobs` (defaulting to 20), and `:1530-1531`
            # raises "top_logprobs requires logprobs to be set to true" for a
            # `top_logprobs` sent without it.
            if "logprobs" in decoding_params:
                logprobs_requested = decoding_params["logprobs"]
                if not isinstance(logprobs_requested, bool):
                    raise FrozenCoreError(
                        "decoding_params logprobs must be a bool, got "
                        f"{logprobs_requested!r} — llama-server reads this field as a "
                        "boolean and maps a true value to n_probs"
                    )
            if "top_logprobs" in decoding_params:
                top_logprobs = decoding_params["top_logprobs"]
                if (
                    isinstance(top_logprobs, bool)
                    or not isinstance(top_logprobs, int)
                    or not 1 <= top_logprobs <= MAX_TOP_LOGPROBS
                ):
                    raise FrozenCoreError(
                        "decoding_params top_logprobs must be an integer in "
                        f"[1, {MAX_TOP_LOGPROBS}], got {top_logprobs!r}"
                    )
                if decoding_params.get("logprobs") is not True:
                    raise FrozenCoreError(
                        "decoding_params top_logprobs requires logprobs: true — the "
                        "pinned llama-server refuses the pair itself, but only after "
                        "this call has been metered"
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
        # Owner batching directive 2026-08-08: everything from the fresh
        # sibling read through the durable record_usage is ONE atomic section
        # under self._metering_lock (see __init__ for the race this closes);
        # order and messages inside are byte-identical to the pre-lock code.
        with self._metering_lock:
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
        wire_provenance: dict[str, object] | None = None
        wire_response_bytes: bytes | None = None
        parsed: object = None
        try:
            parsed = json.loads(response_bytes.decode("utf-8"))
            wire_provenance = _wire_provenance(parsed)
            if wire_provenance is not None:
                wire_response_bytes = base64.b64decode(
                    wire_provenance["response_b64"], validate=True
                )
            text = parsed["text"]  # type: ignore[index]
            usage = {
                str(k): int(v)
                for k, v in dict(parsed.get("usage", {})).items()  # type: ignore[union-attr]
            }
            # Optional transport-forwarded provenance stays outside the
            # normalized MODEL_RESPONSE payload.
            logprobs = parsed.get("logprobs")  # type: ignore[union-attr]
            tool_calls = parsed.get("tool_calls")  # type: ignore[union-attr]
            forwarded_finish_reason = parsed.get("finish_reason")  # type: ignore[union-attr]
            forwarded_reasoning = parsed.get("reasoning")  # type: ignore[union-attr]
        except (KeyError, TypeError, ValueError, UnicodeError) as error:
            if wire_provenance is not None:
                self._sink.emit(
                    "MODEL_WIRE_RESPONSE",
                    f"{request_id}/wire-response",
                    {
                        "request_id": request_id,
                        "sample_id": payload["sample_id"],
                        **wire_provenance,
                    },
                )
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
        # Decode-confidence trace (2026-09-08 logprob-as-judge probe): the raw
        # per-token distribution the server returned, recorded as its OWN
        # hashed record on its OWN channel beside MODEL_RESPONSE rather than as
        # a MODEL_RESPONSE field. That placement is the byte-identity
        # guarantee: a run that never sets decoding_params.logprobs gets no
        # logprobs key on the choice (transport.py's own guard), keeps this
        # branch unentered, and keeps every MODEL_RESPONSE record, every
        # trace-manifest entry and every outputs row exactly as they were
        # before this record existed. `requested_top_logprobs` is None when the
        # request asked for logprobs without naming a k -- the server then
        # applies its own default of 20 (server-common.cpp:1529) and the reader
        # must not silently assume a number the request never sent.
        if wire_provenance is not None:
            self._sink.emit(
                "MODEL_WIRE_RESPONSE",
                f"{request_id}/wire-response",
                {
                    "request_id": request_id,
                    "sample_id": payload["sample_id"],
                    **wire_provenance,
                },
            )
        if logprobs is not None:
            declared = payload.get("decoding_params")
            self._sink.emit(
                "MODEL_LOGPROBS",
                f"{request_id}/logprobs",
                {
                    "logprobs": logprobs,
                    "logprobs_sha256": _logprobs_sha256(logprobs),
                    "requested_top_logprobs": (
                        declared.get("top_logprobs")
                        if isinstance(declared, Mapping)
                        else None
                    ),
                },
            )
        # Post-transport aggregate counters: += on plain ints/floats races
        # under worker-thread concurrency exactly like the budget section;
        # same lock, held only for the increments.
        with self._metering_lock:
            self._latency_total += latency
            self._prompt_tokens += usage.get("prompt_tokens", 0)
            self._completion_tokens += usage.get("completion_tokens", 0)
        cost_payload: dict[str, object] = {
            "calls": 1,
            "audio_seconds": float(audio_seconds),
            "latency_seconds": latency,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
        }
        if isinstance(forwarded_finish_reason, str):
            # Present only when the transport forwarded it (the opt-in reasoning guard): no other COST record gains a key.
            cost_payload["finish_reason"] = forwarded_finish_reason
        if isinstance(forwarded_reasoning, Mapping):
            # Present only when the response carried a reasoning channel or the fragment declared reasoning knobs (decision 286 projection): no other COST
            # record gains a key. Counts and booleans only -- never reasoning text.
            for key in ("reasoning_tokens", "reasoning_chars", "forced_close", "reasoning_content_sha256", "reasoning_bytes_policy"):
                if key in forwarded_reasoning:
                    cost_payload[key] = forwarded_reasoning[key]
        self._sink.emit("COST", f"{request_id}/cost", cost_payload)
        return CoreResponse(
            text=text,
            usage=usage,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            response_text_sha256=response_text_sha256,
            latency_seconds=latency,
            logprobs=logprobs,
            tool_calls=tool_calls,
            wire_response_bytes=wire_response_bytes,
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
        with self._metering_lock:
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
