"""Frozen-core adapter and transports: the ONLY model request path (R0).

Discipline (docs/engineering.md): the gate is checked in the same process
that sends requests (no check-then-run-elsewhere TOCTOU gap); the D2 per-arm
visible-field allowlist is enforced as an exact key set on every request —
the choke point that makes a leakage a hard error rather than a convention.
The real llama-server endpoint shape is confirmed at R0 smoke time against
the receipt-pinned build — tests inject `post` and never open a socket.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
import re
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from ..contracts import ExecutionPlan, assert_information_boundary
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .attempts import AttemptError, AttemptStore
from .base import TRANSPORTS, CoreError, PayloadBindingContext
from .session import SessionError, SessionReceipt, assert_session_alive, require_loopback
from .tracing import TraceSink


class FrozenCoreError(RuntimeError):
    """The adapter refuses: unknown arm, allowlist violation, exhausted budget,
    payload<->plan<->split value mismatch (I3), or media confinement (I4)."""


# Shared, pure media-path helpers (R0 repair T3, I4). Deliberately hold no
# object state: the adapter and the transport each call these with THEIR OWN
# root(s), so the transport's confinement check never depends on the adapter
# having run first -- two independent rails, one shared syntax rule.
_DRIVE_PREFIX = re.compile(r"^[A-Za-z]:")


def _normalized_relative_path(value: object, label: str) -> str:
    """Reject anything that is not a normalized POSIX relative path: absolute,
    drive-letter, backslash, leading '/', or any '.'/'..' segment. Purely
    syntactic -- touches no filesystem -- so a forged value never reaches
    ``Path.__truediv__`` (whose join silently discards the left side for an
    absolute right side, the reproduced transport defect).

    Also refuses per-segment Windows-only looseness that would still let a
    forged relpath land on a legitimate file even though it is not, by
    itself, an escape: a trailing dot/space (Windows silently strips both
    from a path component, e.g. ``"5000001.mp3."`` -> ``"5000001.mp3"``) and
    a colon inside a segment (NTFS alternate-data-stream syntax)."""

    if not isinstance(value, str) or not value:
        raise FrozenCoreError(f"{label} must be a non-empty string")
    if "\\" in value:
        raise FrozenCoreError(f"{label} must not contain a backslash, got {value!r}")
    if value.startswith("/"):
        raise FrozenCoreError(f"{label} must be relative, got absolute path {value!r}")
    if _DRIVE_PREFIX.match(value):
        raise FrozenCoreError(f"{label} must not carry a drive letter, got {value!r}")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise FrozenCoreError(f"{label} contains an empty or traversal segment: {value!r}")
    for part in parts:
        if part.rstrip(". ") != part:
            raise FrozenCoreError(
                f"{label} segment {part!r} has a trailing dot or space (Windows "
                f"silently strips these, so it would not name a normalized path): {value!r}"
            )
        if ":" in part:
            raise FrozenCoreError(
                f"{label} segment {part!r} contains ':' (NTFS alternate-data-stream "
                f"syntax): {value!r}"
            )
    return value


def _resolve_confined(
    join_root: Path, relative: str, confine_root: Path, label: str, *, strict: bool
) -> Path:
    """Join ``relative`` under ``join_root`` and refuse (``FrozenCoreError``) if
    the fully resolved path -- following any symlinks -- lands outside
    ``confine_root`` once both are resolved. ``strict=True`` also requires the
    final path to exist (used by the adapter, which must prove the loader
    fact-checked media is what will be sent); ``strict=False`` tolerates a
    missing leaf so a caller (the transport) can raise its own
    ``FileNotFoundError`` for that case specifically."""

    try:
        confine_resolved = Path(confine_root).resolve(strict=True)
    except OSError as error:
        raise FrozenCoreError(
            f"{label}: confinement root {confine_root} is unavailable: {error}"
        ) from error
    candidate = Path(join_root) / relative
    try:
        resolved = candidate.resolve(strict=strict)
    except OSError as error:
        raise FrozenCoreError(f"{label}: cannot resolve {candidate}: {error}") from error
    if not resolved.is_relative_to(confine_resolved):
        raise FrozenCoreError(
            f"{label} escapes its confined root {confine_root}: {relative!r}"
        )
    return resolved


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


class FrozenCoreAdapter:
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

    def _enforce_payload_binding(self, payload: Mapping[str, object], audio_seconds: object) -> None:
        """I3/I4: the payload's own claimed values must agree with what the
        driver actually verified for this run (the T1 split + carrier loader
        facts bound at construction), not merely be well-typed. A payload can
        name any carrier, sample, path or audio fact it likes; only what
        ``self._binding`` says was loaded is ever trusted."""

        binding = self._binding
        carrier_lock_key = payload["carrier_lock_key"]
        if carrier_lock_key != self._plan.carrier_lock_key:
            raise FrozenCoreError(
                f"payload carrier_lock_key {carrier_lock_key!r} does not match the "
                f"execution plan carrier_lock_key {self._plan.carrier_lock_key!r}"
            )
        sample_id = payload["sample_id"]
        if not isinstance(sample_id, str) or sample_id not in binding.allowed_sample_ids:
            raise FrozenCoreError(
                f"payload sample_id {sample_id!r} is not in the verified split bound "
                "to this run"
            )
        expected_speech_ref = f"{self._plan.carrier_lock_key}/{sample_id}"
        if payload["speech_ref"] != expected_speech_ref:
            raise FrozenCoreError(
                f"payload speech_ref {payload['speech_ref']!r} does not match the "
                f"expected {expected_speech_ref!r} for carrier_lock_key/sample_id"
            )
        fact_audio_seconds, fact_sample_rate_hz = binding.sample_facts[sample_id]
        if float(audio_seconds) != float(fact_audio_seconds):
            raise FrozenCoreError(
                f"payload audio_seconds {audio_seconds!r} disagrees with the loader "
                f"fact {fact_audio_seconds!r} for sample {sample_id!r}"
            )
        sample_rate_hz = payload["sample_rate_hz"]
        if (
            isinstance(sample_rate_hz, bool)
            or not isinstance(sample_rate_hz, int)
            or sample_rate_hz != fact_sample_rate_hz
        ):
            raise FrozenCoreError(
                f"payload sample_rate_hz {sample_rate_hz!r} disagrees with the loader "
                f"fact {fact_sample_rate_hz!r} for sample {sample_id!r}"
            )
        relative = _normalized_relative_path(payload["media_relpath"], "payload media_relpath")
        # IMPORTANT A (round-2 external-threat-model review): confinement alone
        # only proved the payload's media_relpath stays INSIDE the carrier
        # root -- it never compared it to what this run's verified split
        # actually names for THIS sample (``binding.media_relpaths``, the same
        # per-sample mapping ``core.driver.run_experiment`` builds from the
        # loader and the gate's ``verify_media_identity`` re-hashes). A
        # payload could therefore name any OTHER file confined under the same
        # carrier root -- e.g. a decoy media file -- and it sailed straight
        # through: the gate re-hashed the BINDING's claimed path, but the
        # transport read and sent whatever path the payload itself carried.
        # Demonstrated: a gate verified {'s1': ('carrier/s1.mp3', 10.0)}; a
        # payload naming media_relpath="carrier/decoy.mp3" was accepted, the
        # decoy's bytes were sent, and only 10.0s (the BOUND sample's
        # duration) was metered against this run's own planned audio-seconds
        # budget regardless of the decoy's real length. Requiring an EXACT
        # match after
        # normalization closes this: the only media_relpath a payload for
        # ``sample_id`` may ever carry is the one the verified split/loader
        # bound for that exact sample id.
        if binding.media_relpaths:
            expected_relpath = binding.media_relpaths.get(sample_id)
            if expected_relpath is None:
                raise FrozenCoreError(
                    f"payload binding has no verified media_relpath for sample "
                    f"{sample_id!r}; a sample the binding cannot vouch for can never "
                    "be sent"
                )
            if relative != expected_relpath:
                raise FrozenCoreError(
                    f"payload media_relpath {relative!r} does not match the verified "
                    f"split's own media_relpath {expected_relpath!r} for sample "
                    f"{sample_id!r} -- confinement under the carrier root is necessary "
                    "but not sufficient; the payload must name EXACTLY the file the "
                    "binding (and, at the gate, verify_media_identity) vouches for, "
                    "never merely some other file that happens to live under the same "
                    "root (I4 exact media-relpath binding)"
                )
        _resolve_confined(
            binding.data_root,
            relative,
            binding.carrier_root,
            "payload media_relpath",
            strict=True,
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


def _default_post(timeout_seconds: float) -> Callable[[str, bytes], bytes]:
    def post(url: str, body: bytes) -> bytes:
        request = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"}, method="POST"
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return response.read()

    return post


class LlamaServerTransport:
    def __init__(
        self,
        base_url: str,
        data_root: Path,
        session: SessionReceipt,
        runtime_receipt: Mapping[str, object],
        runtime_root: Path,
        timeout_seconds: float = 300.0,
        post: Callable[[str, bytes], bytes] | None = None,
    ) -> None:
        # R0 repair T5 (I5): there is no "no session" transport, mirroring the
        # T3 fail-closed constructor discipline for PayloadBindingContext --
        # a caller can never construct a transport that could ever be asked
        # to send without first proving WHO is going to answer. Its host/port
        # must be the exact endpoint this transport will talk to -- a session
        # receipt is only ever a proof about ONE specific loopback endpoint,
        # never a blanket credential.
        if not isinstance(session, SessionReceipt):
            raise SessionError(
                "LlamaServerTransport requires a core.session.SessionReceipt; got "
                f"{type(session).__name__} (no session receipt -> no send, I5)"
            )
        loopback_host, loopback_port = require_loopback(base_url)
        if (loopback_host, loopback_port) != (session.host, session.port):
            raise SessionError(
                f"transport base_url host/port {loopback_host}:{loopback_port} does not "
                f"match the session receipt's host/port {session.host}:{session.port}; "
                "refused (I5: a session receipt only authorizes the exact endpoint it "
                "was recorded for)"
            )
        self._url = base_url.rstrip("/") + "/v1/chat/completions"
        self._data_root = Path(data_root)
        self._post = post or _default_post(timeout_seconds)
        self._session = session
        self._runtime_receipt = runtime_receipt
        self._runtime_root = Path(runtime_root)
        # R0 repair T5 fix-1/fix-2 (I5, reviewer-flagged CRITICAL gap): full
        # liveness+PROCESS-IDENTITY re-verification, not merely a declared-
        # value comparison -- at construction AND (see __call__) on every
        # single send. A transport instance answers an entire run (potentially
        # many calls / hours of audio, per the plan's own declared budget --
        # no numeric ceiling since the 2026-08-06 owner amendment retired the
        # first-slice caps); a session proven valid once at construction time
        # proves nothing about who is listening later.
        self._assert_session_still_valid()

    def _assert_session_still_valid(self) -> None:
        assert_session_alive(self._session, self._runtime_receipt, self._runtime_root)

    def assert_session_alive(self) -> None:
        """Public re-verification entry point (R0 repair T5 fix-3): lets a
        holder of this transport (``core.model.FrozenCoreAdapter``)
        independently trigger the SAME liveness+identity check this class
        runs on every ``__call__`` -- a second enforcement call site, not an
        independently reimplemented rail (see ``core.session.
        assert_session_alive``'s docstring for why full reimplementation is
        not appropriate for a transport-specific concept like process
        identity)."""

        self._assert_session_still_valid()

    def __call__(self, request_bytes: bytes) -> bytes:
        # R0 repair T5 fix-2 (IMPORTANT, reviewer-flagged): re-verify on the
        # send path itself, every time -- not merely once at construction.
        # Cheap (a few KB re-hash of the launcher stub plus one process-image
        # lookup, never the multi-GB GGUF files), so there is no reason to
        # skip it on the hot path; a process that died or was replaced since
        # the last send is caught HERE, before this request does anything.
        self._assert_session_still_valid()
        payload: Mapping[str, object] = json.loads(request_bytes.decode("utf-8"))
        # I4, independent second rail: refuse absolute/backslash/traversal
        # media_relpath and anything resolving outside self._data_root on the
        # transport's OWN authority -- this must hold even if the adapter's
        # binding-context check were somehow bypassed or absent (the
        # reproduced defect: `self._data_root / <absolute path>` silently
        # discards the data root via Path.__truediv__).
        relative = _normalized_relative_path(payload["media_relpath"], "transport media_relpath")
        media = _resolve_confined(
            self._data_root,
            relative,
            self._data_root,
            "transport media_relpath",
            strict=False,
        )
        if not media.is_file():
            raise FileNotFoundError(f"media missing for transport: {media}")
        audio_b64 = base64.b64encode(media.read_bytes()).decode("ascii")
        content: list[dict[str, object]] = [
            {
                "type": "input_audio",
                "input_audio": {"data": audio_b64, "format": media.suffix.lstrip(".").lower()},
            }
        ]
        for field in ("supplied_evidence", "retrieved_evidence"):
            for item in payload.get(field, []):  # type: ignore[union-attr]
                content.append(
                    {"type": "text", "text": f"[evidence {item['evidence_id']}] {item['content']}"}
                )
        body: dict[str, object] = {
            "messages": [
                {"role": "system", "content": payload["task_instruction"]},
                {"role": "user", "content": content},
            ],
        }
        for key, value in dict(payload.get("decoding_params", {})).items():  # type: ignore[arg-type]
            if key in body:
                raise FrozenCoreError(
                    f"decoding_params key {key!r} collides with the constructed "
                    "request body and would silently override it"
                )
            body[key] = value
        raw = self._post(self._url, json.dumps(body).encode("utf-8"))
        try:
            parsed = json.loads(raw.decode("utf-8"))
            text = parsed["choices"][0]["message"]["content"]
            usage = {str(k): int(v) for k, v in dict(parsed.get("usage", {})).items()}
        except (KeyError, TypeError, ValueError, IndexError, UnicodeError) as error:
            raise FrozenCoreError(
                f"transport returned a malformed response: {error}"
            ) from error
        return json.dumps({"text": text, "usage": usage}).encode("utf-8")


def _llama_server_factory(
    values: Mapping[str, object],
    data_root: Path,
    *,
    session: SessionReceipt,
    runtime_receipt: Mapping[str, object],
    runtime_root: Path,
):
    return LlamaServerTransport(
        str(values["base_url"]),
        data_root,
        session,
        runtime_receipt,
        runtime_root,
        float(values.get("timeout_seconds", 300.0)),
    )


TRANSPORTS.register("llama-server", _llama_server_factory)
