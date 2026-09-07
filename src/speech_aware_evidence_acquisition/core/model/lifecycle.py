"""``FrozenCoreAdapter`` mixin: construction-time gate/session/attempt-open lifecycle.

Split out of ``adapter.py`` (R0 repair refactor stage 2, part C, pure move,
no behaviour change) purely for file size. A plain mixin (method only, no
``__init__``/fields) combined into ``FrozenCoreAdapter`` via multiple
inheritance, mirroring ``binding.py``'s own ``_PayloadBindingMixin`` -- this
changes nothing about the class's runtime behaviour, only which file the
method's source lives in.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Callable, Mapping

from ...contracts import CONSTRUCTION_VISIBLE_ARMS
from ..attempts import AttemptError, AttemptHandle, AttemptStore
from ..base import PayloadBindingContext
from . import FrozenCoreError


class _AttemptLifecycleMixin:
    """``_open_gate_and_attempt``: everything ``FrozenCoreAdapter.__init__``
    needs to check/open BEFORE a request can ever be sent -- the gate itself,
    D1 media identity, transport session liveness, and the durable one-time
    attempt reservation (R0 repair T4, invariant I6)."""

    def _open_gate_and_attempt(
        self,
        gate: object,
        plan: object,
        binding: PayloadBindingContext,
        transport: Callable[[bytes], bytes],
        arm: str | None = None,
    ) -> tuple[str | None, Callable[[], None] | None, AttemptStore, AttemptHandle]:
        """Returns ``(lock_sha256, session_check, store, handle)`` for the
        caller to fold into its own instance fields. Raises
        :class:`FrozenCoreError` on any refusal -- a gate closure, a media
        identity mismatch, or an attempt-accounting refusal (a duplicate
        (run_id, attempt_id), most notably)."""

        # M-3 (external-threat-model review): the gate returns the umbrella
        # lock's SHA-256 it read exactly once while checking this touch; carry
        # it so it lands in cost_summary() -> RunResult.cost -> the run
        # manifest (core.driver.run_experiment / core.bundle), instead of
        # "dataset rev" staying a hand-supplied ledger cell. A duck-typed test
        # gate that returns nothing (most of this module's own unit tests use
        # one) simply yields None here -- harmless, just an absent hash.
        # E2.4 (2026-09-05): the arm is forwarded so the gate can refuse a
        # construction-gold-visible arm whose plan is not bound to a committed
        # construction roster. The capability is detected by SIGNATURE, never
        # by catching TypeError -- catching it would swallow a genuine
        # TypeError raised INSIDE the gate and silently retry the touch
        # without the arm. A gate that cannot take the arm keeps its old
        # behaviour for every ordinary arm (no test double had to change) and
        # is refused outright for a construction-gold-visible one: that is the
        # single case where skipping the check would be a leak.
        gate_call = gate.assert_model_touch_allowed
        try:
            accepts_arm = "arm" in inspect.signature(gate_call).parameters
        except (TypeError, ValueError):
            accepts_arm = False
        if not accepts_arm and arm in CONSTRUCTION_VISIBLE_ARMS:
            raise FrozenCoreError(
                f"arm {arm!r} makes construction gold visible to the frozen core, but "
                "this gate cannot receive the arm and so cannot check the "
                "construction-roster binding; model touch refused"
            )
        lock_sha256 = gate_call(plan, arm=arm) if accepts_arm else gate_call(plan)
        resolved_lock_sha256 = lock_sha256 if isinstance(lock_sha256, str) else None
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
        # IMPORTANT 1 (external-threat-model review round 4): the evidence-
        # layer counterpart to the media-identity rail just above -- re-verify
        # THIS run's evidence (via binding.evidence_relpaths) against D1's
        # frozen evidence-layer facts, duck-typed the same way so test doubles
        # that don't implement verify_evidence_identity are unaffected.
        # binding.evidence_relpaths is empty whenever this run's evidence
        # source supplied no evidence at all (e.g. "none"), in which case
        # there is nothing to check.
        evidence_identity_check: (
            Callable[[str, Mapping[str, str | tuple[str, ...]]], None] | None
        ) = getattr(
            gate, "verify_evidence_identity", None
        )
        if evidence_identity_check is not None and binding.evidence_relpaths:
            evidence_identity_check(binding.carrier_lock_key, dict(binding.evidence_relpaths))
        # IMPROVEMENT (fifth external-threat-model review): the content-identity
        # counterpart, binding the check to the bytes THIS run already read into
        # memory (binding.evidence_contents) rather than a second, later read of
        # the file the check above performs -- see
        # contracts.gate_evidence_identity's own module docstring for the
        # check<->send race this closes. Duck-typed the same way: a test double
        # that implements only verify_evidence_identity is unaffected.
        #
        # conec-names gate-closure incident, follow-up (2026-08-13): threads the
        # SAME binding.evidence_relpaths the file-identity check just above
        # already consulted, so verify_evidence_content_identity can route each
        # sample's content against its OWN D1 layer key
        # (contracts.gate_evidence_identity._route_evidence_layer_key) instead of
        # the carrier's single default layer -- the content-identity mirror of
        # the relpath-routing fix verify_evidence_identity already had. A test
        # double implementing only the old two-argument
        # verify_evidence_content_identity(carrier_lock_key, evidence_contents)
        # signature now raises a TypeError here; every such double in this
        # repo's own test suite was updated alongside this change.
        evidence_content_identity_check: (
            Callable[
                [
                    str,
                    Mapping[str, bytes | tuple[bytes, ...]],
                    Mapping[str, str | tuple[str, ...]],
                ],
                None,
            ]
            | None
        ) = getattr(gate, "verify_evidence_content_identity", None)
        if evidence_content_identity_check is not None and binding.evidence_contents:
            evidence_content_identity_check(
                binding.carrier_lock_key,
                dict(binding.evidence_contents),
                dict(binding.evidence_relpaths),
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
        return resolved_lock_sha256, session_check, store, handle
