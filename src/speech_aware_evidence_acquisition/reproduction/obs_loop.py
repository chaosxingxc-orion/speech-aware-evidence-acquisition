"""The ``obs-agent-loop`` policy: model-driven OBS segmentation of long calls.

Owner directive (session message, 2026-08-08; supersedes the fixed-window
segment-as-sample design): the frozen core must never be asked to process a
whole 40-75-minute earnings call in one request, and the OBS layer is a
model-driven agent loop INSIDE a policy -- one sample stays ONE whole call
(splits and D1 identity untouched); per sample the policy maintains a
sliding audio buffer over the parent PCM, sends ONE buffer slice per
request, and advances by a boundary resolved through three tiers
(``reproduction.obs_audio.resolve_advance``):

1. the model's rough end-of-last-complete-sentence estimate, parsed from the
   frozen-format response (``TRANSCRIPT: ... BOUNDARY_SECONDS: <n>``);
2. deterministic VAD snap to the nearest speech/non-speech transition within
   ``+/- obs_silence_snap_seconds`` (owner addition 2026-08-08: VAD
   transitions; v1 engine is the zero-dependency pure-Python energy VAD,
   ``obs_vad: "energy"``; ``webrtcvad`` is runtime-detected, never a
   pyproject dependency -- the dependency set is pinned at zero);
3. clamp into ``[obs_min_advance_seconds, obs_max_advance_seconds]``; an
   unparseable/out-of-range estimate falls back to
   ``obs_fallback_advance_seconds`` and is flagged in the OBS trace.

Transcript acceptance is the deterministic sentence-cut rule
(``obs_audio.accept_up_to_boundary``); the final buffer accepts everything.
The per-sample hypothesis is the ordered concatenation of accepted spans --
the outputs row carries it once per sample, so the frozen ``asr-wer`` scorer
and every downstream shape are unchanged.

Slices are cut at runtime (one decode per sample) and written under
``derived/obs-slices/<run_id>/`` inside the controlled data root; every
slice registers a :class:`core.model.SliceRecord` derivation record BEFORE
the request that names it, and the payload-binding rail admits it only
through that chain (``core.model.slices`` module docstring). VAD pre-trim
(owner addition): non-speech spans longer than ``obs_vad_trim_min_seconds``
are skipped before a buffer is cut -- trimmed seconds never enter a request
and are therefore never metered; every trim is an OBS trace record.
Preprocessing v1 (default OFF): ``obs_preprocess: ["rms-norm"]`` normalizes
each slice's loudness after cutting, before writing; the derivation record
carries the declared transform + the raw-cut hash.

Tail conditioning (owner addition, 2026-08-08 -- Whisper-style
condition-on-previous, Node-1 knowledge v1): each iteration's rendered
task_instruction includes the tail of the previously ACCEPTED transcript
(``obs_condition_tail_chars``, default 400; 0 disables and reproduces the
unconditioned loop exactly). The tail is MODEL OUTPUT -- never gold, never a
reference transcript, never a test annotation -- framed explicitly as prior
transcript context, not instruction; the leakage discipline (D2) is
unaffected, and the bare-core arm's frozen 10-field payload set is untouched
because the tail rides inside the rendered ``task_instruction`` string.

I7 note (stitch records): the outputs row is one stitched hypothesis per
sample, so the policy emits a terminal ``{request_id_base}/request`` +
``/response`` trace-record pair carrying the stitch descriptor hashes the
row binds to (``core.bundle.outputs._verify_outputs_trace_binding``), each
flagged ``"stitch": true`` and chaining every per-iteration
``MODEL_REQUEST``/``MODEL_RESPONSE`` record by request id and hash -- no
model call is implied or double-counted (no COST record is emitted for the
stitch).

Exhausted-slice skip (Task 2, 2026-08-09 -- see the module comment above
``SLICE_RETRYABLE_EXCEPTIONS`` for the full mechanism): a slice that
exhausts ``obs_slice_retry_max`` retries no longer aborts the whole run --
it is skipped as an honest hole, reported per slice (``obs_skipped`` in the
OBS trace) and aggregated per run (``saturated_slice_count``'s sibling,
``skipped_slice_count``/``skipped_sample_ids``, in the run manifest's cost
block), bounded per sample by ``obs_slice_skip_max`` (default 1; exceeding
it IS fatal). This deliberately changes what a run's WER means, so the
manifest -- not only a trace -- always carries the count.

Unit plan (OBS-E1 obs seam, 2026-09-08; the module comment above
:class:`PlannedUnit` carries the full statement): ``obs_unit_plan`` +
``obs_unit_plan_sha256``, both defaulting to ``None``, replace the
clock-derived fixed windows with the hash-pinned SPEAKER-TURN UNITS of a
``saea-e21-speaker-turn-units-v1`` (v1) or ``saea-e21-speaker-turn-units-v2``
(v2, the coordinator's 2026-09-08 minimum-duration merge rule) plan --
:data:`OBS_UNIT_PLAN_SCHEMAS`. The same encoder, the same tail knob, the same
span-equals-audio_seconds rail, the same retry, skip, stitch and outcome --
only where the cut lands moves, and with the keys null nothing moves at all.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import shutil
import subprocess
import tempfile
import threading
import wave
from array import array
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..core.delivery import (
    normalize_terminal_response,
    stitch_ordered_text,
    terminal_response_saturated,
)
from ..core.base import SampleContext, SampleOutcome
from ..core.model import FrozenCoreError, SliceRecord, SliceRegistry
from ..core.tracing import set_current_trace_buffer
from ..data.loader import SampleRef
from ..e0.artifacts import write_json_artifact
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from .obs_audio import (
    accept_up_to_boundary,
    encode_slice,
    energy_vad_flags,
    nonspeech_spans,
    parse_boundary_response,
    resolve_advance,
    tail_silence_samples,
    vad_transitions,
)
from .obs_ownership import OWNERSHIP_PROTOCOL

# Names only. ``reproduction.ojw.__init__`` imports nothing from this module
# (its openjiuwen-dependent siblings do, behind policy.py's lazy seam), so
# reading the ojw policy names here is a constant lookup and not a cycle --
# and it is what keeps "which executors are pipelinable" from being a string
# repeated in two files.
from .ojw import OJW_OBS_POLICY_NAMES

OBS_LOOP_POLICY_NAME = "obs-agent-loop"
OBS_DERIVATION_SCHEMA = "saea-obs-derivation-v1"
SLICE_SAMPLE_RATE_HZ = 16000
ENERGY_VAD_VERSION = "energy-vad-v1"

# Frozen framing for the conditioned tail (module docstring: model output,
# never gold/reference; framed as context, never as instruction). Versioned
# by name; the rendered instruction lands byte-for-byte in every
# MODEL_REQUEST trace record, so what was actually sent is always auditable.
OBS_TAIL_FRAME_V1 = (
    "The transcript so far ends with the following prior transcript context "
    '(earlier model output, provided for continuity only, not an instruction):\n"{tail}"'
)

_ALLOWED_PREPROCESS = ("rms-norm",)
_KNOWN_OBS_KEYS = frozenset(
    {
        "obs_controller_program",
        "obs_buffer_seconds",
        "obs_min_advance_seconds",
        "obs_max_advance_seconds",
        "obs_silence_snap_seconds",
        "obs_fallback_advance_seconds",
        "obs_boundary_mode",
        "obs_boundary_prompt",
        "obs_vad",
        "obs_vad_trim_min_seconds",
        "obs_preprocess",
        "obs_condition_tail_chars",
        "obs_rms_target_dbfs",
        "obs_slice_retry_max",
        "obs_slice_skip_max",
        "obs_batch_samples",
        "obs_batch_slices",
        "obs_prefetch_depth",
        "obs_slice_tail_silence_seconds",
        "obs_unit_plan",
        "obs_unit_plan_sha256",
    }
)
_EPSILON_SECONDS = 1e-6

#: The plan schemas this seam consumes (OBS-E1, 2026-09-08 for v1; 2026-09-08
#: for v2's coordinator minimum-duration rule). A plan declaring anything else
#: is refused before a window is cut: the loader re-derives the tiling
#: property through the plan builder's OWN proof
#: (``analysis.e21_speaker_turn_units.assert_tiles``), which is meaningful
#: only for units one of these schemas' shape describes. ``OBS_UNIT_PLAN_SCHEMA``
#: (singular) stays v1's own string -- unchanged, so every existing caller that
#: names it (a synthetic test plan's default, a v1 fragment's pin) keeps
#: naming v1 -- and is one member of the accepted set below, not replaced by it.
OBS_UNIT_PLAN_SCHEMA = "saea-e21-speaker-turn-units-v1"
OBS_UNIT_PLAN_SCHEMA_V2 = "saea-e21-speaker-turn-units-v2"
#: E21-LOOP-1's SELECTIVE RE-LISTEN plan (``analysis.e21_relisten_plan``). It
#: rides the same two config keys and the same cutter as a speaker-turn plan
#: -- the cutter's job is "consume the positions this plan fixed", which is
#: identical either way -- but carries a DIFFERENT proof obligation, because a
#: re-listen plan deliberately does not tile its call: it covers only the
#: windows the Reviewer criticised, each unit a narrower span of one of them.
#: A separate schema rather than a flag, so the loader can never guess which
#: proof to apply.
OBS_RELISTEN_PLAN_SCHEMA = "saea-e21-relisten-plan-v1"

#: OBS-E1b, 2026-09-08. v2's turns, each carrying the bounds of the audio
#: DELIVERED for it. A v3 plan is the only one whose delivered cut differs from
#: its turn, and therefore the only one for which the run stitches something
#: other than the raw response.
OBS_UNIT_PLAN_SCHEMA_V3 = "saea-e21-speaker-turn-units-v3"

OBS_UNIT_PLAN_SCHEMAS = frozenset(
    {
        OBS_UNIT_PLAN_SCHEMA,
        OBS_UNIT_PLAN_SCHEMA_V2,
        OBS_UNIT_PLAN_SCHEMA_V3,
        OBS_RELISTEN_PLAN_SCHEMA,
    }
)

#: What the ``saea-obs-derivation-v1`` receipt records in ``boundary_mode``
#: when a plan supplied the cut (preregistration section 8.4). The ADVANCE
#: semantics are still ``fixed`` -- every unit position is known before the
#: first contact -- so the config's own ``obs_boundary_mode`` stays ``fixed``
#: and the OBS trace records keep saying so; this name distinguishes the
#: RECEIPT of a plan-cut run from the receipt of a clock-cut one.
OBS_UNIT_PLAN_BOUNDARY_MODE = "unit-plan"

# Bounded per-slice retry (live E-001 finding, 2026-08-08): one slice request
# hung server-side for the full transport socket timeout and the whole
# attempt died with 27 good slices behind it. A retryable failure -- the
# transport's own timeout/connection errors, or a FrozenCoreError (e.g. a
# malformed response after a server hiccup; a budget/binding refusal retried
# once fails identically and spends nothing, so no carve-out is needed) --
# now gets up to ``obs_slice_retry_max`` fresh, separately-metered requests
# under derived request ids (``<id>-r1``, ``-r2``...). This is exactly what
# the +headroom in planned_model_calls exists for. Anything else (a bug) is
# never retried. Shared by BOTH executors: the plain policy below and the
# openJiuwen ``FrozenCoreASR`` component call this one function, so retry
# behaviour can never diverge between them.
#
# Task 2 interaction (2026-08-09): a budget/binding FrozenCoreError never
# recovers between attempts (it is refused BEFORE any usage is durably
# recorded, so a retry fails identically and free) -- since it is retryable
# here, it now also exhausts and skips exactly like a transient failure, and
# because the SAME refusal recurs on every following slice, it crosses
# obs_slice_skip_max within a couple of slices regardless (see
# test_obs_loop_integration.py::test_obs_loop_slice_budget_is_charged_per_
# slice_not_per_parent for the concrete case: the raised message becomes the
# skip-bound one, not the original budget one, but the attempt still aborts
# either way). This is unchanged 2026-08-08 retry classification, not a new
# decision -- Task 2 only changed what happens AFTER exhaustion.
SLICE_RETRYABLE_EXCEPTIONS = (FrozenCoreError, TimeoutError, ConnectionError)

# One WARNING per swallowed retryable failure (2026-08-11 live incident): the
# matched fast arm aborted on two silently skipped slices, and because the
# swallowed exception was never logged anywhere and the OBS trace of an
# ABORTED attempt is never persisted, the ONLY on-disk evidence was the
# generic skip-bound wording -- the actual failure class and message were
# unrecoverable. Logging here is diagnosis only: it changes no request bytes,
# no retry/skip semantics, and no hash.
_LOG = logging.getLogger(__name__)

# Per-slice decode-cap saturation (2026-08-09, continues the retry finding
# above): configs/model/qwen3-omni-llamacpp-q4km.json now caps
# decoding_params.max_tokens at 1024 so an uncapped runaway decode can never
# again outlast the request timeout and abort a whole arm -- but a slice that
# HITS that cap is a truncated decode, not a genuine transcript end, and
# scoring it silently would contaminate WER with no trace. The exposure
# ledger commits to "counted and reported, not scored silently"; this is the
# detector, at the SAME shared seam as the retry above so both executors
# observe identical saturation behaviour.

# Exhausted-slice skip + bound (Task 2, 2026-08-09, continues both findings
# above): a slice that exhausts obs_slice_retry_max used to propagate an
# exception out of request_slice_with_retry and abort the WHOLE arm -- the
# live incident this fixes lost ~3 hours and ~580 completed calls to ONE bad
# slice, twice. request_slice_with_retry itself no longer raises on a
# RETRYABLE exhaustion (see its own docstring below) -- both executors read
# its ``skipped`` flag and treat that slice as an honest hole: no transcript,
# and the sample's cursor advances past it via the SAME fallback-tier
# arithmetic an unparseable boundary response already uses
# (obs_audio.resolve_advance with estimate=None) -- never a special second
# code path. The hole is recorded in the per-slice OBS record
# (``obs_skipped``) next to ``obs_retry_of``/``obs_saturated``. Because this
# changes what a run's WER means, a run that quietly skipped its audio must
# never be scorable as clean: ``obs_slice_skip_max`` (default 1 -- tolerate
# ONE bad slice per sample, matching the incident's own shape; a SECOND
# skipped slice in the same sample signals something systemic, not one bad
# request) makes exceeding the bound fatal, and the run manifest's cost
# block carries the skipped-slice count/sample ids unconditionally (core.
# driver.cost._assemble_run_cost), mirroring exactly how saturated_slice_
# count/saturated_sample_ids were just added -- never buried in a trace
# only. The bound-exceeded message is built by ONE function
# (_skip_bound_exceeded_message below) that both executors call, so the
# raised ObsLoopError can never diverge in wording between them either.


def _slice_saturated(usage: Mapping[str, object] | None, max_tokens: object) -> bool:
    """True iff ``usage['completion_tokens'] >= max_tokens``.

    ``max_tokens`` is whatever the composed config's own
    ``decoding_params.max_tokens`` holds for this request -- ``None`` means
    the config declares no cap, so nothing can saturate (always False, never
    a guessed default). Never raises: a missing/malformed ``usage`` block or
    a non-numeric cap is simply "cannot be judged saturated", not a crash.
    """

    return terminal_response_saturated(usage, max_tokens)


def request_slice_with_retry(adapter_request, build_payload, request_id, retry_max, max_tokens=None):
    """One slice request with bounded retry (comment above).

    ``build_payload(request_id) -> payload`` builds a FRESH payload per
    attempt (each retry is a new request: new request id, separately traced
    and metered by the adapter). Returns ``(request_id_used, response,
    retry_of, saturated, skipped)`` where ``retry_of`` is the ORIGINAL
    request id when a retry was attempted at all (whether it answered or the
    whole slice was ultimately skipped), else None; ``saturated``
    (``_slice_saturated`` above) is computed on the response actually
    returned -- a retried slice's saturation reflects the attempt that
    succeeded, never a discarded failure.

    ``skipped`` (Task 2, 2026-08-09, continues the retry finding above): True
    iff every attempt (the original plus ``retry_max`` retries) raised a
    RETRYABLE failure (``SLICE_RETRYABLE_EXCEPTIONS``) -- this no longer
    raises out of here. ``response`` is then ``None`` (nothing to read a
    transcript or a usage block from -- ``saturated`` is always False in
    this case, there is no completion to judge) and ``request_id_used`` is
    the id of the LAST attempt made, exactly what the adapter's own final
    MODEL_REQUEST trace record names, so a caller's own record for the skip
    lines up with what was actually sent. A NON-retryable exception (a bug,
    never in ``SLICE_RETRYABLE_EXCEPTIONS``) still propagates immediately,
    unretried, exactly as before this change -- only genuine retry
    exhaustion is downgraded to a skip.
    """

    for attempt in range(max(0, int(retry_max)) + 1):
        attempt_id = request_id if attempt == 0 else f"{request_id}-r{attempt}"
        payload = build_payload(attempt_id)
        try:
            response = adapter_request(payload)
            saturated = _slice_saturated(getattr(response, "usage", None), max_tokens)
            return attempt_id, response, (request_id if attempt else None), saturated, False
        except SLICE_RETRYABLE_EXCEPTIONS as error:
            _LOG.warning(
                "slice request %s attempt %d/%d failed retryably: %s: %s",
                attempt_id, attempt + 1, max(0, int(retry_max)) + 1,
                type(error).__name__, error,
            )
            if attempt >= retry_max:
                return attempt_id, None, (request_id if attempt else None), False, True
    raise AssertionError("unreachable: the loop either returns or re-raises")


def _skip_bound_exceeded_message(sample_id: str, skipped_slices: int, cfg: "ObsLoopConfig") -> str:
    """The ONE wording for a skip-bound-exceeded refusal (module comment
    above ``SLICE_RETRYABLE_EXCEPTIONS``): both ``ObsAgentLoopPolicy.
    run_sample`` below and ``ojw.policy._finalize_sample`` call this, so the
    raised ``ObsLoopError`` can never diverge in wording between the two
    executors for the same scenario."""

    return (
        f"sample {sample_id!r} exceeded obs_slice_skip_max={cfg.slice_skip_max} "
        f"skipped slices (skipped_slices={skipped_slices}, obs_slice_retry_max="
        f"{cfg.slice_retry_max} exhausted on each); refusing to score a sample "
        "missing more audio than the configured bound tolerates"
    )


class ObsLoopError(RuntimeError):
    """The obs-agent-loop refuses: bad config, undecodable media, a broken
    derivation chain, or a runaway loop."""


def _number(values: Mapping[str, object], key: str, default: float) -> float:
    value = values.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ObsLoopError(f"config {key} must be a finite number, got {value!r}")
    return float(value)


# ---------------------------------------------------------------------------
# The unit plan (OBS-E1 obs seam, 2026-09-08)
# ---------------------------------------------------------------------------
#
# Section 8 of docs/readiness/2026-09-07-e21-obs-speaker-turn-units-v1-
# preregistration.md. TWO thin keys on the already-registered obs-agent-loop
# policy -- ``obs_unit_plan`` (a repo-relative path) and
# ``obs_unit_plan_sha256`` (the byte pin) -- both defaulting to None, which
# reproduces the fixed-window cutter byte for byte. When they are set the
# cutter stops cutting ceil(D / buffer) windows off the clock and consumes
# the plan's SPEAKER-TURN UNITS instead. Nothing else moves: the same
# obs_audio.encode_slice, the same tail knob, the same SliceRecord spans, the
# same retry/skip/stitch seams, the same registered policy name. No new base,
# no module under rails/probes, no controller subclass (2026-09-03
# engineering-base rules).
#
# The plan is DATA, not code: every position in it is fixed before the first
# contact, which is precisely the independence condition from_values already
# requires for obs_batch_slices > 1 -- so slice batching stays legal under a
# plan, for the same reason and by the same argument.


@dataclass(frozen=True)
class PlannedUnit:
    """One speaker-turn unit as the cutter consumes it.

    A deliberately narrow view of the plan's much richer per-unit record: the
    span the cut needs, plus the three facts the OBS trace must carry so a
    later paired read can pool by call (``unit_id``) and stratify by speaker
    and by how the unit ended. Everything else in the plan file (dominance
    shares, reference-word ranges, flags) is a REPORTING concern of
    ``analysis.e21_speaker_turn_units`` and is deliberately not carried into
    the runtime.
    """

    unit_id: str
    unit_index: int
    start_seconds: float
    end_seconds: float
    speaker: str | None
    end_cut: str
    #: E21-LOOP-1 (selective re-listen plans only): which fixed 90-second
    #: window of the sealed comparator this unit is a narrower cut OF, and
    #: which half-open word range of that window's pass-1 text the cut
    #: corresponds to. ``None`` on every speaker-turn plan, which is what
    #: keeps those plans' runtime behaviour byte-identical.
    parent_window_index: int | None = None
    predecessor_word_start: int | None = None
    predecessor_word_end: int | None = None
    #: OBS-E1b (plan v3): the bounds of the audio actually DELIVERED for this
    #: unit -- its turn widened by the plan's context rule. ``None`` on a v1 or
    #: v2 plan, where the delivered cut IS the turn and nothing below it moves.
    context_start_seconds: float | None = None
    context_end_seconds: float | None = None

    @property
    def duration_seconds(self) -> float:
        return self.end_seconds - self.start_seconds

    @property
    def has_context(self) -> bool:
        return self.context_start_seconds is not None

    @property
    def cut_start_seconds(self) -> float:
        """Where the cutter starts. The turn's own start without context."""

        return (
            self.start_seconds
            if self.context_start_seconds is None
            else self.context_start_seconds
        )

    @property
    def cut_end_seconds(self) -> float:
        """Where the cutter stops. The turn's own end without context."""

        return (
            self.end_seconds
            if self.context_end_seconds is None
            else self.context_end_seconds
        )


@dataclass(frozen=True)
class UnitPlan:
    """A loaded, hash-pinned, tiling-proved unit plan."""

    relpath: str
    sha256: str
    schema: str
    units_by_sample: Mapping[str, tuple[PlannedUnit, ...]]
    duration_by_sample: Mapping[str, float]

    @property
    def unit_count(self) -> int:
        return sum(len(units) for units in self.units_by_sample.values())

    @property
    def has_context(self) -> bool:
        """True for a v3 plan: units are delivered with context and the text
        the run stitches is decided by ``reproduction.obs_ownership``."""

        return self.schema == OBS_UNIT_PLAN_SCHEMA_V3

    def units_for(
        self, sample_id: str, decoded_duration_seconds: float
    ) -> tuple[PlannedUnit, ...]:
        """This call's units, or a refusal -- called ONCE per sample, before
        that sample's first window is cut.

        The two refusals that can only be made here, with the roster and the
        decoded parent in hand (preregistration section 8.2 items 3 and 4):
        a roster call the plan has no block for, and a plan block cut against
        different audio than the runtime just decoded. The decode is the
        authority; a plan whose duration disagrees describes a different
        measurement and must never be silently stretched onto this one.
        """

        units = self.units_by_sample.get(sample_id)
        if units is None:
            raise ObsLoopError(
                f"unit plan {self.relpath!r} has no block for roster sample "
                f"{sample_id!r}; refusing to fall back to fixed windows for a call "
                f"the plan does not cover (plan covers "
                f"{len(self.units_by_sample)} calls)"
            )
        declared = self.duration_by_sample[sample_id]
        if abs(declared - float(decoded_duration_seconds)) > 1e-6:
            raise ObsLoopError(
                f"unit plan {self.relpath!r} declares {declared} s of decoded audio "
                f"for sample {sample_id!r} but the runtime decode is "
                f"{decoded_duration_seconds} s; the decode is the authority and a "
                "plan cut against different audio is a different measurement"
            )
        return units


def _plan_number(unit: Mapping[str, object], key: str, where: str) -> float:
    value = unit.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ObsLoopError(f"unit plan {where}: {key} must be a finite number, got {value!r}")
    return float(value)


def _plan_int(unit: Mapping[str, object], key: str, where: str) -> int:
    value = unit.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ObsLoopError(
            f"unit plan {where}: {key} must be a non-negative integer, got {value!r}"
        )
    return int(value)


def _load_unit_plan(
    repo_root: Path, relpath: str, expected_sha256: str, buffer_seconds: float
) -> UnitPlan:
    """Read, pin, validate and RE-PROVE a unit plan -- fail-closed, before a
    single window is cut (preregistration section 8.2).

    The loader never trusts the file's own claims. It re-derives the tiling
    property through ``analysis.e21_speaker_turn_units.assert_tiles`` -- the
    plan builder's own proof obligation, run again here on the bytes actually
    loaded -- so a hand-edited plan that still hashes to its pin is impossible
    and a plan that hashes to something else never reaches the proof at all.
    """

    # Function-local, exactly as this module's other heavy imports are: the
    # analysis package is a reader over run bundles and has no business in
    # the runtime import graph of a policy that may never see a plan.
    from ..analysis.e21_relisten_plan import (  # noqa: PLC0415
        ParentWindow,
        RelistenPlanError,
        RelistenUnit,
        assert_relisten_units,
    )
    from ..analysis.e21_speaker_turn_units import (  # noqa: PLC0415
        MIN_DELIVERED_CUT_SECONDS,
        SpeakerTurnUnitError,
        Unit,
        UnitV3,
        assert_context,
        assert_tiles,
        unit_id as mint_unit_id,
    )

    path = Path(repo_root) / relpath
    if not path.is_file():
        raise ObsLoopError(
            f"obs_unit_plan {relpath!r} does not resolve to a file under the repo "
            f"root ({path}); a missing plan is never a fall-back to fixed windows"
        )
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise ObsLoopError(f"cannot read obs_unit_plan {path}: {error}") from error
    actual_sha256 = hashlib.sha256(raw).hexdigest()
    if actual_sha256 != expected_sha256:
        raise ObsLoopError(
            f"obs_unit_plan {relpath!r} hashes to {actual_sha256} but "
            f"obs_unit_plan_sha256 pins {expected_sha256}; the plan fixes every "
            "unit position before the first contact and must be the pinned bytes"
        )
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeError, ValueError) as error:
        raise ObsLoopError(f"obs_unit_plan {relpath!r} is not readable JSON: {error}") from error
    if not isinstance(document, Mapping):
        raise ObsLoopError(f"obs_unit_plan {relpath!r} must be a JSON object")
    schema = document.get("schema")
    if schema not in OBS_UNIT_PLAN_SCHEMAS:
        raise ObsLoopError(
            f"obs_unit_plan {relpath!r} declares schema {schema!r}, not one of "
            f"{sorted(OBS_UNIT_PLAN_SCHEMAS)!r}; this seam consumes those schemas only"
        )
    relisten = schema == OBS_RELISTEN_PLAN_SCHEMA
    blocks = document.get("calls")
    if not isinstance(blocks, list) or not blocks:
        raise ObsLoopError(f"obs_unit_plan {relpath!r} carries no 'calls' list")

    units_by_sample: dict[str, tuple[PlannedUnit, ...]] = {}
    duration_by_sample: dict[str, float] = {}
    seen_unit_ids: set[str] = set()
    for block in blocks:
        if not isinstance(block, Mapping):
            raise ObsLoopError(f"obs_unit_plan {relpath!r}: every call block must be an object")
        sample_id = block.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ObsLoopError(
                f"obs_unit_plan {relpath!r}: a call block has sample_id {sample_id!r}"
            )
        duration = _plan_number(block, "decoded_duration_seconds", f"call {sample_id!r}")
        raw_units = block.get("units")
        if not isinstance(raw_units, list) or not raw_units:
            raise ObsLoopError(
                f"obs_unit_plan {relpath!r}: call {sample_id!r} carries no units; a "
                "call in the plan with nothing to cut is a broken plan, never a "
                "silent fall-back to fixed windows"
            )
        planned: list[PlannedUnit] = []
        rebuilt: list[Unit] = []
        for position, entry in enumerate(raw_units, start=1):
            where = f"call {sample_id!r} unit #{position}"
            if not isinstance(entry, Mapping):
                raise ObsLoopError(f"obs_unit_plan {relpath!r}: {where} is not an object")
            index = entry.get("unit_index")
            if isinstance(index, bool) or not isinstance(index, int) or index != position:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} declares unit_index {index!r}; "
                    "units must be listed in unit_index order, numbered from 1"
                )
            identifier = entry.get("unit_id")
            minted = mint_unit_id(sample_id, index)
            if identifier != minted:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} declares unit_id "
                    f"{identifier!r}, not the minted {minted!r}"
                )
            if identifier in seen_unit_ids:
                # The single collision refusal, and the only reachable one:
                # ids are MINTED from (sample_id, unit_index) and indices are
                # required to run 1..N in order, so two units can share an id
                # only when the same call carries two blocks. A colliding id
                # would make two contacts indistinguishable in the trace and
                # unpoolable in the paired read.
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: unit id {identifier!r} appears twice "
                    f"(call {sample_id!r} carries more than one block?)"
                )
            seen_unit_ids.add(identifier)
            start_seconds = _plan_number(entry, "start_seconds", where)
            end_seconds = _plan_number(entry, "end_seconds", where)
            if start_seconds < -1e-9 or end_seconds > duration + 1e-6:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} spans "
                    f"[{start_seconds}, {end_seconds}) which lies outside its call's "
                    f"own {duration} s of audio"
                )
            # OBS-E1b: on a v3 plan the bounds the cutter uses are the
            # DELIVERED ones, so every check below is made against those. On a
            # v1/v2 plan they ARE the turn's bounds and nothing here moves.
            context_start: float | None = None
            context_end: float | None = None
            if schema == OBS_UNIT_PLAN_SCHEMA_V3:
                context_start = _plan_number(entry, "context_start_seconds", where)
                context_end = _plan_number(entry, "context_end_seconds", where)
                if context_start < -1e-6 or context_end > duration + 1e-6:
                    raise ObsLoopError(
                        f"obs_unit_plan {relpath!r}: {where} delivers "
                        f"[{context_start}, {context_end}) which lies outside its "
                        f"call's own {duration} s of audio"
                    )
                if (
                    context_start > start_seconds + 1e-6
                    or context_end < end_seconds - 1e-6
                ):
                    raise ObsLoopError(
                        f"obs_unit_plan {relpath!r}: {where} delivers "
                        f"[{context_start}, {context_end}) which does not cover its "
                        f"own turn [{start_seconds}, {end_seconds})"
                    )
                floor = min(MIN_DELIVERED_CUT_SECONDS, duration)
                if context_end - context_start < floor - 1e-6:
                    raise ObsLoopError(
                        f"obs_unit_plan {relpath!r}: {where} delivers "
                        f"{context_end - context_start} s, under the {floor} s "
                        "minimum a context-bearing plan promises"
                    )
            elif any(key in entry for key in ("context_start_seconds", "context_end_seconds")):
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} carries context bounds but the "
                    f"plan declares schema {schema!r}; only {OBS_UNIT_PLAN_SCHEMA_V3!r} "
                    "delivers context, and a plan that hides it would be cut one way "
                    "and stitched another"
                )
            cut_start = start_seconds if context_start is None else context_start
            cut_end = end_seconds if context_end is None else context_end
            if cut_end - cut_start > buffer_seconds + 1e-6:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} delivers "
                    f"{cut_end - cut_start} s, longer than the slot's audio "
                    f"budget obs_buffer_seconds={buffer_seconds}"
                )
            speaker = entry.get("speaker")
            if speaker is not None and not isinstance(speaker, str):
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} declares speaker {speaker!r}"
                )
            end_cut = entry.get("end_cut")
            if not isinstance(end_cut, str) or not end_cut:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} declares end_cut {end_cut!r}"
                )
            parent_index: int | None = None
            word_start: int | None = None
            word_end: int | None = None
            if relisten:
                parent_index = _plan_int(entry, "parent_window_index", where)
                word_start = _plan_int(entry, "predecessor_word_start", where)
                word_end = _plan_int(entry, "predecessor_word_end", where)
            elif any(
                key in entry
                for key in (
                    "parent_window_index",
                    "predecessor_word_start",
                    "predecessor_word_end",
                )
            ):
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: {where} carries a re-listen field "
                    f"under schema {schema!r}; those keys belong to "
                    f"{OBS_RELISTEN_PLAN_SCHEMA!r} alone"
                )
            planned.append(
                PlannedUnit(
                    unit_id=identifier,
                    unit_index=index,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    speaker=speaker,
                    end_cut=end_cut,
                    parent_window_index=parent_index,
                    predecessor_word_start=word_start,
                    predecessor_word_end=word_end,
                    context_start_seconds=context_start,
                    context_end_seconds=context_end,
                )
            )
            if relisten:
                # A re-listen plan does not tile its call, so it builds no
                # speaker-turn Unit and takes the containment proof below
                # instead of assert_tiles.
                continue
            common = {
                "sample_id": sample_id,
                "unit_index": index,
                "start_seconds": start_seconds,
                "end_seconds": end_seconds,
                "speaker": speaker,
                "speaker_share": 0.0,
                "speaker_count": 0,
                "start_cut": str(entry.get("start_cut", "")),
                "end_cut": end_cut,
                "ends_active": bool(entry.get("ends_on_active_frame", False)),
                "flags": (),
            }
            rebuilt.append(
                Unit(**common)
                if context_start is None
                else UnitV3(
                    **common,
                    context_start_seconds=context_start,
                    context_end_seconds=context_end,
                )
            )
        if relisten:
            raw_windows = block.get("parent_windows")
            if not isinstance(raw_windows, list) or not raw_windows:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: call {sample_id!r} declares no "
                    "'parent_windows'; a re-listen plan proves containment in the "
                    "comparator's own windows and cannot do so without them"
                )
            parents: list[ParentWindow] = []
            for position, entry in enumerate(raw_windows, start=1):
                where = f"call {sample_id!r} parent window #{position}"
                if not isinstance(entry, Mapping):
                    raise ObsLoopError(
                        f"obs_unit_plan {relpath!r}: {where} is not an object"
                    )
                parents.append(
                    ParentWindow(
                        window_index=_plan_int(entry, "window_index", where),
                        start_seconds=_plan_number(entry, "start_seconds", where),
                        end_seconds=_plan_number(entry, "end_seconds", where),
                        draft_words=_plan_int(entry, "draft_words", where),
                    )
                )
            try:
                assert_relisten_units(
                    [
                        RelistenUnit(
                            sample_id=sample_id,
                            unit_index=unit.unit_index,
                            parent_window_index=int(unit.parent_window_index or 0),
                            start_seconds=unit.start_seconds,
                            end_seconds=unit.end_seconds,
                            predecessor_word_start=int(unit.predecessor_word_start or 0),
                            predecessor_word_end=int(unit.predecessor_word_end or 0),
                        )
                        for unit in planned
                    ],
                    parents,
                    min_seconds=float(
                        document.get("min_relisten_seconds", 0.0) or 0.0
                    ),
                )
            except RelistenPlanError as error:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: call {sample_id!r} is not a legal "
                    f"selective re-listen plan: {error}"
                ) from error
        else:
            try:
                assert_tiles(rebuilt, duration)
                if schema == OBS_UNIT_PLAN_SCHEMA_V3:
                    # The plan builder's OWN context proof, re-run here on the
                    # bytes actually loaded -- the same discipline assert_tiles
                    # is applied under. Its load-bearing clause is the last
                    # one: every turn boundary lies inside the audio BOTH of
                    # its units received, which is what makes the overlap the
                    # ownership stitch aligns on exist at all.
                    assert_context(rebuilt, duration)
            except SpeakerTurnUnitError as error:
                raise ObsLoopError(
                    f"obs_unit_plan {relpath!r}: call {sample_id!r} does not tile its "
                    f"own {duration} s: {error}"
                ) from error
        units_by_sample[sample_id] = tuple(planned)
        duration_by_sample[sample_id] = duration
    return UnitPlan(
        relpath=relpath,
        sha256=actual_sha256,
        schema=str(schema),
        units_by_sample=units_by_sample,
        duration_by_sample=duration_by_sample,
    )


def _unit_trace_fields(unit: PlannedUnit | None) -> dict[str, object]:
    """The three fields section 8.3 adds to a plan-cut OBS record, or nothing
    at all on the fixed-window path -- so a run with the keys null emits the
    historical record shape byte for byte. The unit's BOUNDS already ride in
    ``obs_window_start_seconds`` / ``obs_window_end_seconds``, which under a
    plan are the unit's own span."""

    if unit is None:
        return {}
    fields: dict[str, object] = {
        "obs_unit_id": unit.unit_id,
        "obs_unit_speaker": unit.speaker,
        "obs_unit_end_cut": unit.end_cut,
    }
    if unit.parent_window_index is not None:
        # E21-LOOP-1: a re-listen unit is a narrower cut of ONE of the
        # comparator's own fixed windows, and a paired read charges it back to
        # that window. Emitted only when a re-listen plan supplied the cut, so
        # every speaker-turn plan's record keeps its exact three-key shape.
        fields["obs_relisten_parent_window_index"] = unit.parent_window_index
        fields["obs_relisten_predecessor_word_start"] = unit.predecessor_word_start
        fields["obs_relisten_predecessor_word_end"] = unit.predecessor_word_end
    if unit.has_context:
        # OBS-E1b. Under a v3 plan ``obs_window_start/end_seconds`` are the
        # DELIVERED cut -- they must be, because they are the SliceRecord's own
        # span and the registry refuses a record whose audio_seconds disagrees
        # with it. The TURN is what the stitched text is supposed to describe,
        # so it is carried beside them rather than lost.
        fields.update(
            obs_unit_turn_start_seconds=unit.start_seconds,
            obs_unit_turn_end_seconds=unit.end_seconds,
            obs_unit_context_left_seconds=unit.start_seconds - unit.cut_start_seconds,
            obs_unit_context_right_seconds=unit.cut_end_seconds - unit.end_seconds,
        )
    return fields


@dataclass(frozen=True)
class ObsLoopConfig:
    """Validated obs-loop knobs (all flow into config_hash -> protocol_hash
    through the baseline fragment that declares them)."""

    buffer_seconds: float
    min_advance_seconds: float
    max_advance_seconds: float
    silence_snap_seconds: float
    fallback_advance_seconds: float
    boundary_mode: str
    boundary_prompt_relpath: str | None
    boundary_prompt_text: str | None
    boundary_prompt_sha256: str | None
    vad_engine: str
    vad_trim_min_seconds: float
    preprocess: tuple[str, ...]
    condition_tail_chars: int
    rms_target_dbfs: float
    slice_retry_max: int
    slice_skip_max: int
    batch_samples: int
    batch_slices: int
    slice_tail_silence_seconds: float
    prefetch_depth: int = 0
    unit_plan_relpath: str | None = None
    unit_plan_sha256: str | None = None
    unit_plan: UnitPlan | None = None

    @classmethod
    def from_values(cls, values: Mapping[str, object], repo_root: Path) -> "ObsLoopConfig":
        unknown = sorted(
            key
            for key in values
            if isinstance(key, str) and key.startswith("obs_") and key not in _KNOWN_OBS_KEYS
        )
        if unknown:
            raise ObsLoopError(
                f"unknown obs-loop config keys {unknown}; a typo here would silently "
                f"change nothing but the protocol hash -- known keys: {sorted(_KNOWN_OBS_KEYS)}"
            )
        buffer_seconds = _number(values, "obs_buffer_seconds", 60.0)
        min_advance = _number(values, "obs_min_advance_seconds", 20.0)
        max_advance = _number(values, "obs_max_advance_seconds", 55.0)
        snap = _number(values, "obs_silence_snap_seconds", 2.0)
        fallback = _number(values, "obs_fallback_advance_seconds", 50.0)
        trim_min = _number(values, "obs_vad_trim_min_seconds", 5.0)
        rms_target = _number(values, "obs_rms_target_dbfs", -20.0)
        # Slice tail silence (2026-09-07 cross-carrier silence-tail
        # preregistration section 6.3). ONE thin knob on the registered
        # obs-agent-loop policy, not a new base: after the buffered cut and
        # after any declared preprocess transform, append exactly this many
        # seconds of digital silence to the emitted slice. DEFAULT 0.0 = the
        # historical bytes, so every sealed Earnings run stays reproducible;
        # 2.0 at 16 kHz is the 32,000 zero samples whose byte-exact oracle is
        # the committed @ts2 window media
        # (docs/receipts/artifacts/d1-e21-buf90-1593-tail2s.json).
        #
        # The tail changes the DELIVERED bytes only. The window cut, the
        # cursor advance, the slice span and therefore SliceRecord's
        # start/end/audio_seconds are untouched -- core.model.SliceRegistry
        # requires audio_seconds to equal the span, and moving the span would
        # move the next window and destroy the pairing against the sealed
        # comparator. Delivered seconds per slice are audio_seconds + this
        # value, and the record declares the tail in its preprocess tuple.
        tail_silence = _number(values, "obs_slice_tail_silence_seconds", 0.0)
        if tail_silence < 0:
            raise ObsLoopError(
                f"obs_slice_tail_silence_seconds must be >= 0 (0 = today's bytes), "
                f"got {tail_silence}"
            )
        if tail_silence > 0:
            # Refuse a length that is not a whole number of samples at the
            # slice rate, here, before a single window is cut.
            tail_silence_samples(SLICE_SAMPLE_RATE_HZ, tail_silence)
        if buffer_seconds <= 0:
            raise ObsLoopError(f"obs_buffer_seconds must be positive, got {buffer_seconds}")
        if not (0 < min_advance <= max_advance <= buffer_seconds):
            raise ObsLoopError(
                "obs advance window must satisfy 0 < min <= max <= buffer, got "
                f"min={min_advance} max={max_advance} buffer={buffer_seconds}"
            )
        if not (min_advance <= fallback <= max_advance):
            raise ObsLoopError(
                f"obs_fallback_advance_seconds {fallback} must lie inside "
                f"[{min_advance}, {max_advance}]"
            )
        if snap < 0 or trim_min < 0:
            raise ObsLoopError("obs snap/trim seconds must be >= 0 (0 disables)")
        mode = values.get("obs_boundary_mode", "model")
        if mode not in ("model", "fixed"):
            raise ObsLoopError(f"obs_boundary_mode must be 'model' or 'fixed', got {mode!r}")
        engine = values.get("obs_vad", "energy")
        if engine not in ("energy", "webrtc"):
            raise ObsLoopError(f"obs_vad must be 'energy' or 'webrtc', got {engine!r}")
        raw_preprocess = values.get("obs_preprocess", [])
        if not isinstance(raw_preprocess, (list, tuple)) or not all(
            isinstance(name, str) for name in raw_preprocess
        ):
            raise ObsLoopError("obs_preprocess must be a list of transform names")
        bad = sorted(set(raw_preprocess) - set(_ALLOWED_PREPROCESS))
        if bad:
            raise ObsLoopError(
                f"obs_preprocess names unsupported transforms {bad}; v1 supports "
                f"{list(_ALLOWED_PREPROCESS)} only"
            )
        tail_chars = values.get("obs_condition_tail_chars", 400)
        if isinstance(tail_chars, bool) or not isinstance(tail_chars, int) or tail_chars < 0:
            raise ObsLoopError(
                f"obs_condition_tail_chars must be an integer >= 0, got {tail_chars!r}"
            )
        retry_max = values.get("obs_slice_retry_max", 1)
        if isinstance(retry_max, bool) or not isinstance(retry_max, int) or retry_max < 0:
            raise ObsLoopError(
                f"obs_slice_retry_max must be an integer >= 0 (0 disables), got {retry_max!r}"
            )
        # Skip bound (Task 2, 2026-08-09, module comment above
        # SLICE_RETRYABLE_EXCEPTIONS): the count of retry-exhausted slices a
        # SAMPLE tolerates before the whole run refuses rather than scoring
        # audio it is silently missing. Default 1 -- tolerate one bad slice
        # per sample (the live incident's own shape); 0 makes ANY skipped
        # slice fatal.
        skip_max = values.get("obs_slice_skip_max", 1)
        if isinstance(skip_max, bool) or not isinstance(skip_max, int) or skip_max < 0:
            raise ObsLoopError(
                f"obs_slice_skip_max must be an integer >= 0 (0 = no skipped slice "
                f"tolerated), got {skip_max!r}"
            )
        # Sample-level concurrency (owner batching directive 2026-08-08):
        # consumed by the ojw executor's run_samples (and by the driver's
        # dispatch decision); the plain policy accepts and IGNORES it -- it
        # is defined sequential, being the equivalence reference fixture.
        batch_samples = values.get("obs_batch_samples", 1)
        if isinstance(batch_samples, bool) or not isinstance(batch_samples, int) or batch_samples < 1:
            raise ObsLoopError(
                f"obs_batch_samples must be an integer >= 1 (1 = sequential), "
                f"got {batch_samples!r}"
            )
        # Slice-level dispatch (2026-08-12, owner's slice-batching direction):
        # legal ONLY when iterations are provably independent — fixed windows
        # (positions known upfront), no tail (no text fed forward), no VAD
        # trim (window positions must not depend on runtime trim spans).
        # Anything else fails closed here, before a single slice is cut.
        batch_slices = values.get("obs_batch_slices", 1)
        if isinstance(batch_slices, bool) or not isinstance(batch_slices, int) or batch_slices < 1:
            raise ObsLoopError(
                f"obs_batch_slices must be an integer >= 1 (1 = sequential), "
                f"got {batch_slices!r}"
            )
        if batch_slices > 1:
            tail_chars = values.get("obs_condition_tail_chars", 400)
            if values.get("obs_boundary_mode", "model") != "fixed":
                raise ObsLoopError(
                    "obs_batch_slices > 1 requires obs_boundary_mode 'fixed' — "
                    "model-declared boundaries make slice k+1's window depend on "
                    "slice k's answer"
                )
            if tail_chars != 0:
                raise ObsLoopError(
                    "obs_batch_slices > 1 requires obs_condition_tail_chars 0 — "
                    "the rolling tail feeds slice k's transcript into slice k+1's "
                    "prompt (and was measured to HURT WER by ~9 pp besides)"
                )
            if trim_min != 0:
                raise ObsLoopError(
                    "obs_batch_slices > 1 requires obs_vad_trim_min_seconds 0 — "
                    "runtime trim spans would move window positions"
                )
        # Sample-level PREFETCH depth (2026-09-08 obs-pipeline throughput
        # fix; the module comment above :class:`ObsDispatcher` carries the
        # measurement). 0 -- the DEFAULT -- is the strictly sequential
        # sample loop this repository has always run, byte for byte: the
        # driver never builds a pipeline and no code below this line
        # behaves differently. N >= 1 lets the driver keep N samples of
        # LOOKAHEAD in flight, so the next call's decode/cut/encode/register
        # phase runs on its own worker while the current call's windows are
        # still being answered.
        prefetch_depth = resolve_prefetch_depth(values)
        if prefetch_depth > 0:
            # On the PLAIN policy the pipeline drives the slice-parallel pass
            # and nothing else: that policy's own sequential cutter re-reads
            # the previous window's answer to place the next cut, and it does
            # so on `run_sample`'s local `cursor`, so overlapping two samples
            # there would overlap two cursors as well.
            #
            # The openJiuwen executor is exempt, and NOT because its cutter is
            # parallel -- it is strictly sequential per sample. It is exempt
            # because every one of its loop-carried values (cursor, iteration,
            # accepted spans, session) lives in that sample's OWN
            # ``ObsSampleState`` and its own workflow session, so two samples
            # overlap without sharing anything at any boundary mode. What the
            # pipeline buys there is the same two things it buys here: the
            # next call's decode/VAD runs off the critical path, and the run's
            # shared ObsDispatcher keeps the request slots occupied across a
            # call boundary (owner Decision 12-F port, 2026-09-08).
            if batch_slices <= 1 and str(values.get("policy", "")) not in (
                OJW_OBS_POLICY_NAMES
            ):
                raise ObsLoopError(
                    "obs_prefetch_depth > 0 requires obs_batch_slices > 1 — "
                    "the prefetch pipeline overlaps the SLICE-PARALLEL pass, and "
                    "the plain sequential cutter's cursor is not independent "
                    f"(policies whose per-sample loop IS self-contained, and "
                    f"therefore need no slice width: {list(OJW_OBS_POLICY_NAMES)})"
                )
            # Two concurrency planes must never compose silently: the ojw
            # executor's run_samples already runs obs_batch_samples samples at
            # once and owns its own slot pool.
            if batch_samples != 1:
                raise ObsLoopError(
                    "obs_prefetch_depth > 0 requires obs_batch_samples 1 — the "
                    "sample-batch executor already owns sample-level concurrency, "
                    "and two schedulers would multiply the in-flight request count"
                )
        # The unit plan (OBS-E1 obs seam, preregistration section 8.1/8.2).
        # Both keys default to None and BOTH must move together: one without
        # the other is a config that either names bytes it does not pin or
        # pins bytes it does not name, and neither is admissible for a file
        # that fixes every cut position before the first contact.
        plan_relpath = values.get("obs_unit_plan")
        plan_sha256 = values.get("obs_unit_plan_sha256")
        if (plan_relpath is None) != (plan_sha256 is None):
            raise ObsLoopError(
                "obs_unit_plan and obs_unit_plan_sha256 must be set together "
                f"(got obs_unit_plan={plan_relpath!r}, "
                f"obs_unit_plan_sha256={plan_sha256!r}); a plan without its byte pin "
                "is not a plan, and a pin without a plan cuts nothing"
            )
        unit_plan: UnitPlan | None = None
        if plan_relpath is not None:
            if not isinstance(plan_relpath, str) or not plan_relpath.strip():
                raise ObsLoopError(
                    f"obs_unit_plan must be a repo-relative path string, got "
                    f"{plan_relpath!r}"
                )
            if not isinstance(plan_sha256, str) or len(plan_sha256) != 64:
                raise ObsLoopError(
                    f"obs_unit_plan_sha256 must be a 64-character SHA-256 hex digest, "
                    f"got {plan_sha256!r}"
                )
            # The three knobs a plan is incompatible with, refused here rather
            # than discovered at the cut. The plan fixes every unit position
            # up front; a model-declared boundary, a rolling transcript tail or
            # a runtime VAD trim would each make unit k+1 depend on unit k and
            # destroy exactly the independence the plan asserts (the same
            # argument obs_batch_slices > 1 already rests on, which is why
            # slice batching stays LEGAL under a plan).
            if mode != "fixed":
                raise ObsLoopError(
                    "obs_unit_plan requires obs_boundary_mode 'fixed' — the plan "
                    f"fixes every unit position before the first contact, got {mode!r}"
                )
            if tail_chars != 0:
                raise ObsLoopError(
                    "obs_unit_plan requires obs_condition_tail_chars 0 — a rolling "
                    "tail feeds unit k's transcript into unit k+1's prompt and "
                    "destroys the independence the plan asserts"
                )
            if trim_min != 0:
                raise ObsLoopError(
                    "obs_unit_plan requires obs_vad_trim_min_seconds 0 — runtime trim "
                    "spans would move positions the plan already fixed"
                )
            unit_plan = _load_unit_plan(
                Path(repo_root), plan_relpath, plan_sha256, buffer_seconds
            )
            if unit_plan.has_context and batch_slices <= 1:
                # OBS-E1b. The ownership stitch resolves each boundary from
                # BOTH of its units' responses, so it needs the whole call's
                # answers before the first OBS record is written -- which only
                # the slice-parallel pass has (it gathers every result, then
                # emits). The sequential loop emits as it goes and would have
                # to withhold its records or amend them afterwards; neither is
                # worth a second code path, so a context-bearing plan is
                # refused here rather than half-supported there.
                raise ObsLoopError(
                    f"obs_unit_plan {plan_relpath!r} declares schema "
                    f"{unit_plan.schema!r}, whose units are delivered with context "
                    "and whose text ownership is resolved across the whole call; "
                    "that requires obs_batch_slices > 1 (the slice-parallel pass), "
                    f"got {batch_slices}"
                )
        prompt_relpath = values.get("obs_boundary_prompt")
        prompt_text: str | None = None
        prompt_sha256: str | None = None
        if mode == "model":
            if not isinstance(prompt_relpath, str) or not prompt_relpath.strip():
                raise ObsLoopError(
                    "obs_boundary_mode 'model' requires obs_boundary_prompt (a frozen "
                    "template path under configs/)"
                )
            template = Path(repo_root) / "configs" / prompt_relpath
            try:
                prompt_text = template.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as error:
                raise ObsLoopError(
                    f"cannot read obs boundary prompt template {template}: {error}"
                ) from error
            prompt_sha256 = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
        return cls(
            buffer_seconds=buffer_seconds,
            min_advance_seconds=min_advance,
            max_advance_seconds=max_advance,
            silence_snap_seconds=snap,
            fallback_advance_seconds=fallback,
            boundary_mode=str(mode),
            boundary_prompt_relpath=prompt_relpath if mode == "model" else None,
            boundary_prompt_text=prompt_text,
            boundary_prompt_sha256=prompt_sha256,
            vad_engine=str(engine),
            vad_trim_min_seconds=trim_min,
            preprocess=tuple(raw_preprocess),
            condition_tail_chars=tail_chars,
            rms_target_dbfs=rms_target,
            slice_retry_max=retry_max,
            slice_skip_max=skip_max,
            batch_samples=batch_samples,
            batch_slices=batch_slices,
            slice_tail_silence_seconds=tail_silence,
            prefetch_depth=prefetch_depth,
            unit_plan_relpath=plan_relpath,
            unit_plan_sha256=plan_sha256,
            unit_plan=unit_plan,
        )


# ---------------------------------------------------------------------------
# Parent decode (heavy imports stay function-local; tests monkeypatch this)
# ---------------------------------------------------------------------------


def decode_parent_pcm(path: Path, sample_rate_hz: int = SLICE_SAMPLE_RATE_HZ) -> array:
    """Decode the parent media to 16 kHz mono int16 PCM, exactly once per
    sample. Preference order: ffmpeg (resamples deterministically for a
    pinned build), then librosa (the WSL speechrl venv ships it), then
    soundfile (only when the native rate already matches -- soundfile has no
    resampler). Fail-closed with a clear operator message otherwise."""

    path = Path(path)
    if not path.is_file():
        raise ObsLoopError(f"parent media missing: {path}")
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "decoded.wav"
            command = [
                ffmpeg, "-v", "error", "-y", "-i", str(path),
                "-ac", "1", "-ar", str(sample_rate_hz),
                "-c:a", "pcm_s16le", "-map_metadata", "-1", "-bitexact", str(out),
            ]
            proc = subprocess.run(command, capture_output=True, text=True)
            if proc.returncode != 0:
                raise ObsLoopError(
                    f"ffmpeg failed to decode {path}: {proc.stderr.strip()[:500]}"
                )
            with wave.open(str(out), "rb") as handle:
                frames = handle.readframes(handle.getnframes())
            samples = array("h")
            samples.frombytes(frames)
            return samples
    try:
        import librosa  # noqa: PLC0415 (heavy import stays function-local)
        import numpy  # noqa: PLC0415

        # Decode unchanged compressed bytes on the WSL filesystem. Small
        # libsndfile reads across a mounted host filesystem otherwise dominate
        # preparation time; retain the same backend, suffix and PCM conversion.
        with tempfile.TemporaryDirectory(prefix="saea-parent-decode-") as tmp:
            local_media = Path(tmp) / ("parent" + path.suffix)
            shutil.copyfile(path, local_media)
            floats, _ = librosa.load(
                str(local_media), sr=sample_rate_hz, mono=True
            )
        clipped = numpy.clip(numpy.rint(floats * 32767.0), -32768, 32767).astype("int16")
        return array("h", clipped.tolist())
    except ImportError:
        pass
    try:
        import soundfile  # noqa: PLC0415

        data, rate = soundfile.read(str(path), dtype="int16", always_2d=True)
        if rate != sample_rate_hz:
            raise ObsLoopError(
                f"soundfile decoded {path} at {rate} Hz and cannot resample to "
                f"{sample_rate_hz} Hz; install ffmpeg or librosa in the WSL venv"
            )
        mono = array("h")
        for row in data:
            mono.append(int(sum(int(v) for v in row) / len(row)))
        return mono
    except ImportError:
        pass
    raise ObsLoopError(
        f"no decoder available for {path}: need ffmpeg on PATH, or librosa, or "
        "soundfile (16 kHz media only) in the environment"
    )


def _vad_flags(samples: Sequence[int], rate: int, engine: str) -> tuple[list[bool], str]:
    """(flags, engine descriptor). ``webrtc`` is runtime-detected and
    fail-closed when asked for but absent -- never a silent fallback."""

    if engine == "energy":
        return energy_vad_flags(samples, rate), ENERGY_VAD_VERSION
    try:
        import webrtcvad  # noqa: PLC0415 (runtime-detected, never in pyproject)
    except ImportError as error:
        raise ObsLoopError(
            "obs_vad 'webrtc' requested but webrtcvad is not installed in this "
            "environment; install it in the WSL venv or use obs_vad 'energy'"
        ) from error
    vad = webrtcvad.Vad(2)
    frame_len = int(0.03 * rate)
    raw = array("h", samples).tobytes()
    frame_bytes = frame_len * 2
    flags = []
    for start in range(0, len(raw) - frame_bytes + 1, frame_bytes):
        flags.append(bool(vad.is_speech(raw[start : start + frame_bytes], rate)))
    version = getattr(webrtcvad, "__version__", "unknown")
    return flags, f"webrtcvad-{version}"


# ---------------------------------------------------------------------------
# Run-level request pipeline (obs-pipeline throughput fix, 2026-09-08)
# ---------------------------------------------------------------------------
#
# The defect, measured on the sealed SAEA-E21-FULL44-DIRECT-BASELINE-V2
# attempt (44 calls, 1,593 fixed 90-second windows, -c 36864 -np 6; receipt
# under docs/checks/speech-aware-evidence-acquisition/
# 2026-09-08-e21-obs-pipeline/): the run occupied 4.664 of 6 server slots on
# average (77.7 %), spent 15.40 % of its 5,378.8-second wall with ZERO slots
# busy, and delivered 17.77 windows per minute. 828.4 of those 829 idle
# seconds are the 43 CALL BOUNDARIES: ``_slice_parallel_pass`` cuts and
# registers every window of ONE sample before its first request, then drains
# that sample's pool completely, and ``core.driver.run_experiment`` only then
# starts the next sample's decode. The GPU waits out every boundary (mean
# 19.26 s, median 17.90 s) and the slots empty at every sample's tail.
#
# The fix is two halves of one mechanism and moves NO request byte:
#
# 1. PREFETCH -- the driver keeps ``obs_prefetch_depth`` samples of lookahead
#    in flight, each on its own worker with its own ``core.tracing.
#    TraceBuffer``, flushed into the real sink strictly in split-id order.
#    Sample N+1's decode/cut/encode/register therefore runs while sample N's
#    windows are still being answered. The docstring promise that every
#    window of a sample is cut "before that sample's first model touch" is
#    preserved exactly -- prefetch moves WHEN a sample starts cutting, never
#    the cut-then-send order inside it.
# 2. SLOT-SATURATING DISPATCH -- :class:`ObsDispatcher` below is ONE pool of
#    dispatch slots for the whole run, acquired per request and released when
#    it settles. Because it spans samples, sample N+1's first windows occupy
#    the slots sample N's tail is releasing, and the in-flight count never
#    falls to zero at a boundary. It is also the ONE place the
#    ``id_slot="per-sample"`` sentinel resolves under the pipeline: two
#    samples drawing from two per-sample pools would hand the same integer to
#    two live requests and pin them to one server slot.
#
# Fail-closed properties, enforced in ``ObsLoopConfig.from_values`` above and
# in the constructor below: the depth is an integer >= 0 (0 = today's
# behaviour, and the driver then builds no pipeline at all), the width is an
# integer >= 1, and a dispatch slot is always released on the failing path
# (the context manager's ``finally``), so one raised request can never leak a
# slot and silently shrink the run's width.


def resolve_prefetch_depth(values: Mapping[str, object]) -> int:
    """``obs_prefetch_depth`` as a validated integer >= 0 (0 = sequential).

    Read by BOTH ``ObsLoopConfig.from_values`` (which adds the legality the
    knob needs from the rest of the obs block) and ``core.driver.
    run_experiment`` (which decides the loop shape before any policy config
    object exists), so the two can never disagree about what the config
    asked for."""

    raw = values.get("obs_prefetch_depth", 0)
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
        raise ObsLoopError(
            f"obs_prefetch_depth must be an integer >= 0 (0 = today's strictly "
            f"sequential sample loop), got {raw!r}"
        )
    return raw


def resolve_dispatch_width(values: Mapping[str, object]) -> int:
    """How many requests the run's dispatcher keeps in flight at once.

    ``max(obs_batch_slices, serving_geometry.slots)``:

    * never NARROWER than ``obs_batch_slices`` -- that is the per-sample
      width the config already declares and the sealed runs already flew, so
      no run gets slower, and (because a dispatch slot doubles as the
      ``id_slot`` sentinel's value) the set of ``id_slot`` integers a run can
      send is exactly the set it sends today whenever the declared slice
      width is the larger of the two -- which is the case for every fragment
      in this repository;
    * never narrower than the server's own slot count either, so a geometry
      with more slots than the config's slice width can actually fill them.

    The dispatcher never invents concurrency ABOVE both numbers: it cannot
    exceed the server's slots except by inheriting a width the config itself
    declared and already flew. A missing ``serving_geometry`` (or a missing
    ``slots`` key in it) leaves the width at ``obs_batch_slices`` exactly."""

    batch_slices = values.get("obs_batch_slices", 1)
    if isinstance(batch_slices, bool) or not isinstance(batch_slices, int) or batch_slices < 1:
        raise ObsLoopError(
            f"obs_batch_slices must be an integer >= 1 (1 = sequential), "
            f"got {batch_slices!r}"
        )
    slots = 0
    geometry = values.get("serving_geometry")
    if geometry is not None:
        if not isinstance(geometry, Mapping):
            raise ObsLoopError(
                f"serving_geometry must be a mapping, got {type(geometry).__name__}"
            )
        raw_slots = geometry.get("slots")
        if raw_slots is not None:
            if isinstance(raw_slots, bool) or not isinstance(raw_slots, int) or raw_slots < 1:
                raise ObsLoopError(
                    f"serving_geometry.slots must be an integer >= 1, got {raw_slots!r}"
                )
            slots = raw_slots
    return max(batch_slices, slots)


class ObsDispatcher:
    """One run's pool of dispatch slots, shared across sample boundaries.

    A FIFO deque of ``width`` integers guarded by a condition variable: one
    acquire per request bounds the in-flight count AND yields the integer the
    ``id_slot="per-sample"`` sentinel resolves to -- exactly the per-sample
    ``free_slots`` list the slice-parallel pass has used since 2026-08-12,
    lifted from sample scope to run scope and nothing else. ``peak_in_flight``
    is diagnostic only (the concurrency proof in
    ``tests/unit/test_obs_pipeline.py`` reads it); nothing in a run's outputs,
    trace or manifest depends on it."""

    def __init__(self, width: int) -> None:
        if isinstance(width, bool) or not isinstance(width, int) or width < 1:
            raise ObsLoopError(
                f"obs dispatch width must be an integer >= 1, got {width!r}"
            )
        self._width = width
        self._free = deque(range(width))
        self._condition = threading.Condition()
        self._in_flight = 0
        self.peak_in_flight = 0

    @property
    def width(self) -> int:
        return self._width

    @property
    def in_flight(self) -> int:
        with self._condition:
            return self._in_flight

    @contextmanager
    def dispatch_slot(self):
        """Hold one dispatch slot for the whole life of one request --
        retries included, exactly like the per-sample pool it replaces."""

        with self._condition:
            while not self._free:
                self._condition.wait()
            slot = self._free.popleft()
            self._in_flight += 1
            if self._in_flight > self.peak_in_flight:
                self.peak_in_flight = self._in_flight
        try:
            yield slot
        finally:
            with self._condition:
                self._free.append(slot)
                self._in_flight -= 1
                self._condition.notify()


def build_run_dispatcher(values: Mapping[str, object]) -> "ObsDispatcher | None":
    """The run's dispatcher, or ``None`` when ``obs_prefetch_depth`` is 0.

    ``None`` is what every config written before 2026-09-08 resolves to, and
    the slice-parallel pass then takes its historical per-sample slot pool
    unchanged."""

    if resolve_prefetch_depth(values) == 0:
        return None
    return ObsDispatcher(resolve_dispatch_width(values))


def materialize_fixed_windows(cfg, registry, data_root, sample, rate, pcm,
                              duration, parent_sha256):
    """Cut and register the exact independent windows used by live dispatch."""
    # The unit plan, resolved ONCE per sample before the first cut (OBS-E1
    # obs seam, preregistration section 8.3). ``None`` is the historical
    # fixed-window cutter, byte for byte.
    plan_units = (
        None
        if cfg.unit_plan is None
        else cfg.unit_plan.units_for(sample.sample_id, duration)
    )

    windows: list[tuple[int, SliceRecord, bool, float, str | None, PlannedUnit | None]] = []
    slice_records: list[SliceRecord] = []
    cursor = 0.0
    iteration = 0
    while True:
        # Under a plan the PLAN's length is the loop bound, not the clock.
        # OBS-E1b made that distinction load-bearing: a context-bearing
        # unit's cut runs PAST its turn, so the cursor can reach the call's
        # end while units remain, and a clock condition would silently drop
        # the last one. For a v1/v2 plan the two conditions coincide (the
        # cut IS the turn and the turns tile), so this is byte-identical
        # for every plan written before v3 and for the clock cutter, whose
        # branch below still advances and stops on the cursor.
        if plan_units is not None:
            if iteration >= len(plan_units):
                break
        elif cursor >= duration - _EPSILON_SECONDS:
            break
        unit = None
        if plan_units is not None:
            unit = plan_units[iteration]
            # OBS-E1b: the cut is the unit's DELIVERED span, which on a
            # v1/v2 plan IS its turn (PlannedUnit.cut_*_seconds) -- so this
            # line is byte-identical for every plan written before v3.
            start_frame = int(round(unit.cut_start_seconds * rate))
            end_frame = min(int(round(unit.cut_end_seconds * rate)), len(pcm))
        else:
            start_frame = int(round(cursor * rate))
            end_frame = min(int(round((cursor + cfg.buffer_seconds) * rate)), len(pcm))
        if end_frame <= start_frame:
            break
        slice_samples = pcm[start_frame:end_frame]
        slice_seconds = (end_frame - start_frame) / rate
        is_final = (
            iteration == len(plan_units) - 1
            if plan_units is not None
            else end_frame >= len(pcm)
        )
        raw_bytes, transforms, pre_sha256 = encode_slice(
            slice_samples,
            rate,
            preprocess=cfg.preprocess,
            rms_target_dbfs=cfg.rms_target_dbfs,
            tail_silence_seconds=cfg.slice_tail_silence_seconds,
        )
        relpath = registry.slice_relpath(sample.sample_id, iteration)
        slice_path = data_root / relpath
        slice_path.parent.mkdir(parents=True, exist_ok=True)
        slice_path.write_bytes(raw_bytes)
        record = SliceRecord(
            sample_id=sample.sample_id,
            parent_media_relpath=sample.media_relpath,
            parent_sha256=parent_sha256,
            start_seconds=start_frame / rate,
            end_seconds=end_frame / rate,
            audio_seconds=slice_seconds,
            sample_rate_hz=rate,
            media_relpath=relpath,
            sha256=hashlib.sha256(raw_bytes).hexdigest(),
            bytes=len(raw_bytes),
            iteration=iteration,
            preprocess=transforms,
            pre_sha256=pre_sha256,
        )
        registry.register(record)
        slice_records.append(record)
        windows.append((iteration, record, is_final, slice_seconds, pre_sha256, unit))
        cursor = record.start_seconds + slice_seconds
        iteration += 1

    return windows, slice_records


def window_request_factory(ctx, window, *, sample, rate, evidence,
                           allow_empty_evidence=False, window_hook=None, slot=None):
    """Return the live window's payload factory without contacting an adapter."""
    from ..core.policies import build_arm_payload

    win_iteration, record, _is_final, slice_seconds, _pre, _unit = window
    slice_ref = SampleRef(
        carrier_lock_key=sample.carrier_lock_key,
        sample_id=sample.sample_id,
        media_relpath=record.media_relpath,
        audio_seconds=slice_seconds,
        sample_rate_hz=rate,
    )
    base_request_id = f"{ctx.request_id_base}-i{win_iteration:04d}"
    decoding_params = dict(ctx.decoding_params)
    if slot is not None:
        decoding_params["id_slot"] = slot

    instruction = (
        ctx.task_instruction
        if window_hook is None
        else window_hook.instruction(
            iteration=win_iteration,
            record=record,
            default=ctx.task_instruction,
        )
    )

    packet_kwargs = {}
    prepared_packets = ctx.extras.get("window_feature_packets")
    if prepared_packets is not None:
        if ctx.arm != "speech-feature-query":
            raise ObsLoopError("window packet binding requires the speech-feature-query arm")
        binding = prepared_packets.binding_for(
            f"{sample.sample_id}#w{win_iteration + 1:04d}", record.trace_view()
        )
        values = ctx.extras["config_values"]
        packet_kwargs = {
            "speech_feature_parts": [{
                "packet_id": binding.packet_id, "sha256": binding.packet_sha256,
                "role": "query",
            }],
            "speech_packet_sha256": binding.packet_sha256,
            "query_source": "speech_features",
            "key_representation_id": values["speech_feature_key_representation_id"],
            "matcher_policy_id": values["speech_feature_matcher_policy_id"],
            "mmproj_loaded": False,
        }
        # A query-only representation does not invent external knowledge.
        # Evidence-bearing configurations retain their existing refusal rules.
        allow_empty_evidence = allow_empty_evidence or (
            values.get("evidence_source", "none") in (None, "none") and not evidence
        )

    def _payload(
        rid, _slice_ref=slice_ref, _params=decoding_params, _instruction=instruction
    ):
        return build_arm_payload(
            ctx.arm,
            _slice_ref,
            rid,
            _instruction,
            _params,
            evidence=evidence,
            retrieval_query=ctx.retrieval_query,
            # Every slice of this sample carries the SAME bank
            # (ctx.exemplar_bank is resolved once per sample by
            # core.driver.run_experiment, module docstring above).
            exemplar_bank=ctx.exemplar_bank,
            # obs-replay-loop's REPLAY-scoped arm (reproduction.
            # replay_loop module docstring, 2026-08-13): PASS 1 --
            # this slice-parallel pass, reused VERBATIM by
            # ObsReplayLoopPolicy -- never has retrieved delta
            # candidates of its own (RETRIEVE is a per-flagged-span
            # REPLAY concept). But core.driver.run_experiment builds
            # exactly ONE core.model.FrozenCoreAdapter per run, bound
            # to ctx.arm's own D2-frozen field set for EVERY request
            # that arm sends, PASS 1's own included -- so an arm
            # that declares "delta_candidates" (e.g.
            # "fixed-legal-context-replay") requires the key on
            # every one of THIS pass's requests too, or the exact
            # field-set match in build_arm_payload refuses a
            # perfectly legal PASS 1 request as readily as it would
            # refuse a smuggled field. An always-empty list satisfies
            # that requirement without claiming any candidate this
            # pass never retrieved; an arm that does NOT declare the
            # field gets None (an omitted key, byte-identical to
            # every arm registered before this one).
            delta_candidates=(
                [] if "delta_candidates" in ARM_VISIBLE_FIELDS[ctx.arm] else None
            ),
            allow_empty_evidence=allow_empty_evidence,
            **packet_kwargs,
        )

    return base_request_id, _payload


class ObsAgentLoopPolicy:
    """One whole-call sample -> N buffer-slice requests -> one stitched
    hypothesis (module docstring). Stateless; every run fact arrives through
    ``SampleContext`` (``extras``: slice_registry / data_root / run_dir /
    repo_root / config_values, supplied by ``core.driver.run_experiment``)."""

    def _slice_parallel_pass(
        self, ctx, cfg, registry, data_root, sample, rate, pcm, duration,
        parent_sha256, engine_descriptor, evidence, max_tokens,
        *, allow_empty_evidence: bool = False, window_hook=None, dispatcher=None,
    ):
        """Phases of the slice-level dispatch (owner's slice-batching
        direction, 2026-08-12; legality enforced fail-closed in
        ``from_values``): (1) cut and register EVERY fixed window before the
        first model touch; (2) dispatch up to ``cfg.batch_slices`` concurrent
        requests through the SAME ``request_slice_with_retry`` seam (the real
        adapter is thread-safe — the ojw batch mode has exercised it
        concurrently in production since 2026-08-09); (3) accept, count and
        emit OBS records in slice order, so trace shapes, stitch chains and
        the skip bound behave byte-compatibly with the sequential path. The
        MODEL_REQUEST/RESPONSE records interleave in arrival order within
        this sample's sink — ids still chain, and the stitch verifier binds
        by id, not position.

        ``allow_empty_evidence`` (keyword-only, default ``False`` --
        ``reproduction.replay_loop``'s ``replay_pass1_evidence="suppressed"``
        knob, D7 delivery-gate design-gap fix, 2026-08-15): forwarded
        verbatim to ``build_arm_payload`` below. ``run_sample``'s own call
        site now also sets it True for exactly one, narrower reason (SAEA-P2
        abort fix, 2026-08-15 P2 abort): this sample's evidence resolved to a
        legitimately empty ``derived-candidates`` materialization
        (``evidence_empty_by_materialization``, computed in ``run_sample``) --
        every OTHER call keeps today's behaviour (an evidence-bearing arm
        still refuses an empty ``evidence``).

        ``window_hook`` (keyword-only, default ``None`` -- KC-E1f, 2026-09-07):
        the ONE seam a second-pass policy needs and this pass did not have.
        ``None`` is byte-identical to every run before it. A hook is an object
        with two methods, both called once per window, and neither may touch
        anything else:

        * ``instruction(iteration, record, default)`` -> the rendered
          ``task_instruction`` for THAT window's request. Everything else about
          the request -- the arm, the evidence, the decoding params, the slice
          -- is unchanged, so a per-window instruction rides exactly where
          ``OBS_TAIL_FRAME_V1`` already rides and the arm's D2-frozen field set
          is untouched.
        * ``accept(iteration, record, transcript, saturated, skipped)`` ->
          ``(delivered_text, extra_obs_fields)``. This is where a substitution
          -only delivery rule replaces a raw response with what the run will
          actually stitch. It is called for EVERY window, saturated and skipped
          ones included, because "what this window contributes" is precisely
          the decision such a policy exists to make. Its extra fields are
          merged into the window's own OBS record, so what was delivered and
          why is in the sealed trace beside what was said.

        The hook never changes the request count, the slice cutting, the retry
        or skip semantics, the stitch chain or the outcome shape.

        ``dispatcher`` (keyword-only, default ``None`` -- obs-pipeline
        throughput fix, 2026-09-08; the module comment above
        :class:`ObsDispatcher` carries the measurement and the design):
        ``None`` is byte-identical to every run before it -- this pass then
        builds its OWN per-sample pool of ``cfg.batch_slices`` dispatch slots,
        exactly as it has since 2026-08-12. An :class:`ObsDispatcher` is the
        RUN's pool instead, shared with whatever other sample the driver's
        prefetch pipeline has in flight, so the slots stay occupied across a
        sample boundary. What a request CONTAINS is unchanged either way: the
        slot integer rides in ``decoding_params['id_slot']`` only when the
        model profile declares the ``per-sample`` sentinel, and the
        dispatcher's width is never narrower than ``cfg.batch_slices``, so the
        set of integers a run can send does not move. Under a dispatcher this
        pass also binds each request thread to THIS sample's trace buffer
        (``core.tracing.set_current_trace_buffer``, the documented batch-policy
        contract), which is what keeps two concurrent samples' MODEL records
        in their own per-sample blocks."""

        from concurrent.futures import ThreadPoolExecutor


        windows, slice_records = materialize_fixed_windows(
            cfg, registry, data_root, sample, rate, pcm, duration, parent_sha256)
        iteration = len(windows)

        # Slot-affinity sentinel resolution for the PLAIN parallel path
        # (2026-08-12, caught fail-closed by the adapter on first launch):
        # the ojw executor resolves id_slot="per-sample" per SAMPLE; here one
        # sample spans all slots, so the working unit is the DISPATCH SLOT —
        # a pool of cfg.batch_slices integers, acquired per request and
        # released when it settles, exactly the ojw free-slots pattern.
        import threading as _threading

        sentinel_active = ctx.decoding_params.get("id_slot") == "per-sample"
        slot_lock = _threading.Lock()
        free_slots = list(range(cfg.batch_slices))

        def _send(window, slot):
            base_request_id, _payload = window_request_factory(
                ctx, window, sample=sample, rate=rate, evidence=evidence,
                allow_empty_evidence=allow_empty_evidence,
                window_hook=window_hook, slot=slot,
            )

            return request_slice_with_retry(
                ctx.adapter.request, _payload, base_request_id,
                cfg.slice_retry_max, max_tokens,
            )

        def request_one(window):
            # Historical path (``dispatcher is None``): this sample's own
            # pool of cfg.batch_slices integers, acquired before the payload
            # is built and released when the request settles -- unchanged.
            if dispatcher is None:
                slot = None
                if sentinel_active:
                    with slot_lock:
                        slot = free_slots.pop(0)
                try:
                    return _send(window, slot)
                finally:
                    if slot is not None:
                        with slot_lock:
                            free_slots.append(slot)
            # Pipelined path: the RUN's pool. Acquiring it is what bounds the
            # in-flight request count across sample boundaries; the integer is
            # only WRITTEN into the request when the sentinel asked for it.
            with dispatcher.dispatch_slot() as pooled_slot:
                set_current_trace_buffer(ctx.sink)
                try:
                    return _send(window, pooled_slot if sentinel_active else None)
                finally:
                    set_current_trace_buffer(None)

        with ThreadPoolExecutor(max_workers=cfg.batch_slices) as pool:
            results = list(pool.map(request_one, windows))

        accepted_spans: list[str] = []
        request_ids: list[str] = []
        iteration_request_sha256s: list[str] = []
        iteration_response_sha256s: list[str] = []
        saturated_count = 0
        skipped_count = 0

        # Phase 2.5, and ONLY on a context-bearing plan: what each unit
        # CONTRIBUTES. Every window's answer is already in hand -- that is what
        # phase 2 gathered -- and the ownership stitch needs both neighbours of
        # every boundary at once, so it runs here, once per call, before the
        # first OBS record is written. With no plan, or a v1/v2 plan, this
        # block is skipped entirely and every line below it behaves as it has
        # since 2026-08-12.
        transcripts: list[str] = []
        hook_field_list: list[dict[str, object]] = []
        for window, result in zip(windows, results):
            win_iteration, record, _is_final, _slice_seconds, _pre, _unit = window
            _request_id, response, _retry_of, saturated, skipped = result
            transcript = normalize_terminal_response(
                None if response is None else response.text, saturated=saturated, skipped=skipped
            )
            fields: dict[str, object] = {}
            if window_hook is not None:
                from .window_controller import record_controller_terminal

                record_controller_terminal(
                    window_hook, iteration=win_iteration, request_id=_request_id,
                    response=response, saturated=saturated, skipped=skipped,
                )
                transcript, fields = window_hook.accept(
                    iteration=win_iteration,
                    record=record,
                    transcript=transcript,
                    saturated=saturated,
                    skipped=skipped,
                )
            transcripts.append(transcript)
            hook_field_list.append(fields)
        ownership_fields = self._resolve_ownership(windows, transcripts)

        for position, (window, result) in enumerate(zip(windows, results)):
            win_iteration, record, is_final, slice_seconds, pre_sha256, unit = window
            request_id, response, retry_of, saturated, skipped = result
            if saturated:
                saturated_count += 1
            transcript = transcripts[position]
            hook_fields = dict(hook_field_list[position])
            if ownership_fields is not None:
                owned = ownership_fields[position]
                transcript = str(owned["obs_delivered_text"])
                hook_fields.update(owned)
            ctx.sink.emit(
                "OBS",
                f"{request_id}/obs",
                {
                    "obs_iteration": win_iteration,
                    "obs_window_start_seconds": record.start_seconds,
                    "obs_window_end_seconds": record.end_seconds,
                    "obs_final_window": is_final,
                    "obs_slice_relpath": record.media_relpath,
                    "obs_slice_sha256": record.sha256,
                    "obs_pre_sha256": pre_sha256,
                    "obs_preprocess": list(cfg.preprocess),
                    "obs_vad_engine": engine_descriptor,
                    "obs_boundary_mode": cfg.boundary_mode,
                    "obs_boundary_prompt_sha256": cfg.boundary_prompt_sha256,
                    "obs_boundary_estimate_seconds": None,
                    "obs_boundary_snapped_seconds": None,
                    "obs_boundary_advance_seconds": slice_seconds,
                    "obs_boundary_clamped": False,
                    "obs_boundary_fallback": False,
                    "obs_accepted_chars": len(transcript),
                    "obs_dropped_chars": 0,
                    "obs_tail_chars_used": 0,
                    "obs_tail_sha256": None,
                    "obs_retry_of": retry_of,
                    "obs_saturated": saturated,
                    "obs_skipped": skipped,
                    # Slice-level dispatch marker: records emitted in slice
                    # order AFTER concurrent completion; MODEL records
                    # interleave in arrival order, chained by id.
                    "obs_dispatch": "slice-parallel",
                    # Unit-plan fields, present only when a plan supplied this
                    # cut (preregistration section 8.3): the unit's id, its
                    # speaker and how it ended, beside the bounds already
                    # carried above -- what analysis.e21_window_pairing and
                    # analysis.e21_speaker_turn_units need to pool per call.
                    **_unit_trace_fields(unit),
                    **hook_fields,
                },
            )
            accepted_spans.append(transcript)
            if skipped:
                skipped_count += 1
                if skipped_count > cfg.slice_skip_max:
                    raise ObsLoopError(
                        _skip_bound_exceeded_message(sample.sample_id, skipped_count, cfg)
                    )
            else:
                request_ids.append(request_id)
                iteration_request_sha256s.append(response.request_sha256)
                iteration_response_sha256s.append(response.response_sha256)

        return (
            accepted_spans, request_ids, iteration_request_sha256s,
            iteration_response_sha256s, slice_records, saturated_count,
            skipped_count, iteration,
        )

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        registry = ctx.extras.get("slice_registry")
        if not isinstance(registry, SliceRegistry):
            raise ObsLoopError(
                "obs-agent-loop requires a core.model.SliceRegistry in "
                "SampleContext.extras['slice_registry'] (supplied by "
                "core.driver.run_experiment); refusing to cut unchained slices"
            )
        try:
            data_root = Path(ctx.extras["data_root"])
            run_dir = Path(ctx.extras["run_dir"])
            repo_root = Path(ctx.extras["repo_root"])
            config_values = ctx.extras["config_values"]
        except KeyError as error:
            raise ObsLoopError(
                f"obs-agent-loop SampleContext.extras lacks {error}; supplied only by "
                "core.driver.run_experiment"
            ) from error
        cfg = ObsLoopConfig.from_values(config_values, repo_root)
        sample: SampleRef = ctx.sample
        rate = SLICE_SAMPLE_RATE_HZ
        parent_path = data_root / sample.media_relpath
        pcm = decode_parent_pcm(parent_path, rate)
        if not len(pcm):
            raise ObsLoopError(f"decoded zero samples from {parent_path}")
        duration = len(pcm) / rate
        parent_sha256 = _sha256_file(parent_path)

        need_vad = cfg.boundary_mode == "model" or cfg.vad_trim_min_seconds > 0
        flags: list[bool] = []
        engine_descriptor = "vad-not-run"
        transitions: list[float] = []
        trim_spans: list[tuple[float, float]] = []
        if need_vad:
            flags, engine_descriptor = _vad_flags(pcm, rate, cfg.vad_engine)
            frame_seconds = 0.03
            transitions = vad_transitions(flags, frame_seconds)
            if cfg.vad_trim_min_seconds > 0:
                trim_spans = nonspeech_spans(
                    flags, frame_seconds, min_seconds=cfg.vad_trim_min_seconds
                )

        evidence = ctx.evidence if ctx.arm != "bare-core" else None
        # SAEA-P2 abort fix (core.evidence._derived_candidates module comment,
        # 2026-08-15 P2 abort): a legitimately empty derived-candidates
        # materialization (a 0-byte candidates file) resolves this sample's
        # evidence to an empty list here -- but an arm that still declares an
        # evidence field (unlike bare-core) requires build_arm_payload's
        # ``allow_empty_evidence`` to accept that empty content for THIS
        # sample, the same vehicle reproduction.replay_loop's
        # ``replay_pass1_evidence="suppressed"`` knob already uses. Scoped
        # tightly to the one evidence_source that can legitimately resolve
        # empty (``derived-candidates``) so a real config/materialization
        # error (any other source resolving no evidence for an
        # evidence-bearing arm) keeps failing loud exactly as before.
        config_evidence_source = (
            str(config_values.get("evidence_source", "none"))
            if isinstance(config_values, Mapping)
            else "none"
        )
        evidence_empty_by_materialization = (
            evidence is not None
            and not evidence
            and config_evidence_source == "derived-candidates"
        )
        # Per-slice saturation (module comment above SLICE_RETRYABLE_EXCEPTIONS):
        # read the decode cap ONCE from the composed config's decoding_params
        # (exactly what every slice payload actually carries via
        # build_arm_payload -> core.model.FrozenCoreAdapter.request); absent
        # -> None -> _slice_saturated always reports False.
        max_tokens = ctx.decoding_params.get("max_tokens")
        accepted_spans: list[str] = []
        request_ids: list[str] = []
        iteration_request_sha256s: list[str] = []
        iteration_response_sha256s: list[str] = []
        slice_records: list[SliceRecord] = []
        trim_events: list[dict[str, object]] = []
        iteration = 0
        trims = 0
        saturated_count = 0
        skipped_count = 0
        cursor = 0.0
        effective_min = (
            cfg.buffer_seconds if cfg.boundary_mode == "fixed" else cfg.min_advance_seconds
        )
        max_iterations = math.ceil(duration / max(effective_min, 1e-9)) + len(trim_spans) + 8

        # The unit plan, resolved ONCE per sample before the first cut (OBS-E1
        # obs seam, preregistration section 8.3). Resolved HERE, above the
        # dispatch decision, so a roster call the plan does not cover or a
        # plan cut against different audio refuses before either executor path
        # writes a byte. ``None`` is the historical fixed-window cutter.
        plan_units = (
            None
            if cfg.unit_plan is None
            else cfg.unit_plan.units_for(sample.sample_id, duration)
        )
        if plan_units is not None:
            # The plan's own length IS the iteration bound; the clock-derived
            # one above describes a cutter that is not running.
            max_iterations = len(plan_units) + 8

        # The per-window hook (KC-E1f, 2026-09-07), resolved ONCE per sample
        # ABOVE the dispatch decision (2026-09-08 ojw port): BOTH cutters now
        # carry the hook, so which one runs is a throughput choice and never a
        # semantic one. ``None`` -- ``obs-agent-loop``'s own answer, always --
        # is byte-identical to every run before the seam existed.
        from .window_controller import build_controller_window_hook

        window_hook = build_controller_window_hook(
            ctx, cfg, self._window_hook(ctx, cfg, data_root, sample)
        )

        # Slice-level dispatch (2026-08-12): when the config proves iteration
        # independence (from_values: fixed windows + no tail + no trim),
        # phases 1-3 below replace the sequential loop; setting the cursor to
        # the end makes the loop a no-op and execution falls through to the
        # SAME finalize/stitch/outcome code as the sequential path.
        if cfg.batch_slices > 1:
            (
                accepted_spans, request_ids, iteration_request_sha256s,
                iteration_response_sha256s, slice_records, saturated_count,
                skipped_count, iteration,
            ) = self._slice_parallel_pass(
                ctx, cfg, registry, data_root, sample, rate, pcm, duration,
                parent_sha256, engine_descriptor, evidence, max_tokens,
                allow_empty_evidence=evidence_empty_by_materialization,
                window_hook=window_hook,
                # The run's dispatcher, supplied by core.driver.run_experiment
                # only when obs_prefetch_depth > 0; absent (None) for every
                # config written before 2026-09-08, and the pass then takes
                # its historical per-sample slot pool.
                dispatcher=ctx.extras.get("obs_dispatcher"),
            )
            cursor = duration

        while cursor < duration - _EPSILON_SECONDS:
            trimmed = self._next_trim(trim_spans, cursor, cfg.vad_trim_min_seconds)
            if trimmed is not None:
                span_start, span_end = trimmed
                new_cursor = min(span_end, duration)
                ctx.sink.emit(
                    "OBS",
                    f"{ctx.request_id_base}-trim{trims:04d}/obs",
                    {
                        "obs_trim_from_seconds": cursor,
                        "obs_trim_to_seconds": new_cursor,
                        "obs_trim_span_start_seconds": span_start,
                        "obs_trim_span_end_seconds": span_end,
                        "obs_vad_engine": engine_descriptor,
                    },
                )
                trim_events.append(
                    {"from_seconds": cursor, "to_seconds": new_cursor, "engine": engine_descriptor}
                )
                trims += 1
                cursor = new_cursor
                continue

            unit = None
            if plan_units is not None:
                if iteration >= len(plan_units):
                    break
                unit = plan_units[iteration]
                # OBS-E1b: the cut is the unit's DELIVERED span, which on a
                # v1/v2 plan IS its turn (PlannedUnit.cut_*_seconds) -- so this
                # line is byte-identical for every plan written before v3.
                start_frame = int(round(unit.cut_start_seconds * rate))
                end_frame = min(int(round(unit.cut_end_seconds * rate)), len(pcm))
            else:
                start_frame = int(round(cursor * rate))
                end_frame = min(int(round((cursor + cfg.buffer_seconds) * rate)), len(pcm))
            if end_frame <= start_frame:
                break
            slice_samples = pcm[start_frame:end_frame]
            slice_seconds = (end_frame - start_frame) / rate
            is_final = (
                iteration == len(plan_units) - 1
                if plan_units is not None
                else end_frame >= len(pcm)
            )
            raw_bytes, transforms, pre_sha256 = encode_slice(
                slice_samples,
                rate,
                preprocess=cfg.preprocess,
                rms_target_dbfs=cfg.rms_target_dbfs,
                tail_silence_seconds=cfg.slice_tail_silence_seconds,
            )
            relpath = registry.slice_relpath(sample.sample_id, iteration)
            slice_path = data_root / relpath
            slice_path.parent.mkdir(parents=True, exist_ok=True)
            slice_path.write_bytes(raw_bytes)
            record = SliceRecord(
                sample_id=sample.sample_id,
                parent_media_relpath=sample.media_relpath,
                parent_sha256=parent_sha256,
                start_seconds=start_frame / rate,
                end_seconds=end_frame / rate,
                audio_seconds=slice_seconds,
                sample_rate_hz=rate,
                media_relpath=relpath,
                sha256=hashlib.sha256(raw_bytes).hexdigest(),
                bytes=len(raw_bytes),
                iteration=iteration,
                preprocess=transforms,
                pre_sha256=pre_sha256,
            )
            registry.register(record)
            slice_records.append(record)

            stitched_so_far = " ".join(span for span in accepted_spans if span)
            tail = (
                stitched_so_far[-cfg.condition_tail_chars :]
                if cfg.condition_tail_chars > 0 and stitched_so_far
                else ""
            )
            instruction = ctx.task_instruction
            if cfg.boundary_mode == "model":
                instruction = f"{instruction}\n\n{cfg.boundary_prompt_text}"
            if tail:
                instruction = f"{instruction}\n\n{OBS_TAIL_FRAME_V1.format(tail=tail)}"
            # The per-window hook's instruction leg (2026-09-08 ojw port).
            # It rides on the FULLY rendered instruction -- after the boundary
            # template and after the conditioned tail -- which is the only
            # placement the slice-parallel pass and the openJiuwen executor can
            # share: under the fixed-boundary, zero-tail legality every hook
            # consumer declares, all three sites hand the hook exactly
            # ``ctx.task_instruction``, so one seam is one string everywhere.
            if window_hook is not None:
                instruction = window_hook.instruction(
                    iteration=iteration, record=record, default=instruction
                )

            slice_ref = SampleRef(
                carrier_lock_key=sample.carrier_lock_key,
                sample_id=sample.sample_id,
                media_relpath=relpath,
                audio_seconds=slice_seconds,
                sample_rate_hz=rate,
            )
            base_request_id = f"{ctx.request_id_base}-i{iteration:04d}"
            # Deferred import: core.policies imports THIS module's policy class
            # to register it; importing build_arm_payload back at module level
            # would be circular. By run time both modules are always loaded.
            from ..core.policies import build_arm_payload

            def _payload(rid, _slice_ref=slice_ref, _instruction=instruction):
                return build_arm_payload(
                    ctx.arm,
                    _slice_ref,
                    rid,
                    _instruction,
                    ctx.decoding_params,
                    evidence=evidence,
                    retrieval_query=ctx.retrieval_query,
                    # Every slice of this sample carries the SAME bank (see
                    # the slice-parallel pass's identical comment above).
                    exemplar_bank=ctx.exemplar_bank,
                    # obs-replay-loop's REPLAY-scoped arm: see the identical
                    # comment on the slice-parallel pass's own _payload
                    # above -- same requirement, same always-empty
                    # placeholder, same arm-conditional omission.
                    delta_candidates=(
                        [] if "delta_candidates" in ARM_VISIBLE_FIELDS[ctx.arm] else None
                    ),
                    allow_empty_evidence=evidence_empty_by_materialization,
                )

            request_id, response, retry_of, saturated, skipped = request_slice_with_retry(
                ctx.adapter.request, _payload, base_request_id, cfg.slice_retry_max, max_tokens
            )
            if saturated:
                saturated_count += 1

            # Exhausted-slice skip (module comment above
            # SLICE_RETRYABLE_EXCEPTIONS): no response ever arrived, so
            # there is no transcript/estimate to parse -- treated exactly
            # like an unparseable boundary response (transcript="",
            # estimate=None), which the SAME resolution tiers below already
            # know how to fall back from. Never a second code path.
            # Saturation QUARANTINE (2026-08-11): a slice that hit the
            # max_tokens cap is a runaway repetition, not a transcript --
            # same empty-transcript fallback treatment, raw response still
            # fully traced, hole counted via obs_saturated/cost block and
            # deliberately NOT counted toward obs_slice_skip_max (a skip is
            # an unknown failure; a saturation is a detected, bounded
            # degeneracy). Mirrored in ojw.components.FrozenCoreASR.
            if skipped or saturated:
                transcript, estimate = "", None
            elif cfg.boundary_mode == "model":
                transcript, estimate = parse_boundary_response(response.text)
            else:
                transcript, estimate = normalize_terminal_response(response.text), None
            if is_final:
                accepted, dropped = transcript, ""
                resolution: dict[str, object] = {
                    "estimate": estimate,
                    "snapped": None,
                    "advance": slice_seconds,
                    "clamped": False,
                    "fallback": False,
                }
            elif cfg.boundary_mode == "fixed":
                accepted, dropped = transcript, ""
                resolution = {
                    "estimate": None,
                    "snapped": None,
                    "advance": slice_seconds,
                    "clamped": False,
                    "fallback": False,
                }
            else:
                window_start = start_frame / rate
                local_transitions = [
                    t - window_start
                    for t in transitions
                    if window_start <= t <= window_start + slice_seconds
                ]
                resolution = resolve_advance(
                    estimate,
                    transitions=local_transitions,
                    snap_window=cfg.silence_snap_seconds,
                    min_advance=cfg.min_advance_seconds,
                    max_advance=cfg.max_advance_seconds,
                    fallback_advance=cfg.fallback_advance_seconds,
                    buffer_seconds=slice_seconds,
                )
                advance = min(float(resolution["advance"]), slice_seconds)
                resolution["advance"] = advance
                accepted, dropped = accept_up_to_boundary(transcript, advance / slice_seconds)

            # The per-window hook's delivery leg (2026-09-08 ojw port). It is
            # handed the ACCEPTED span -- what this window would contribute --
            # and returns what it actually contributes, plus the fields that
            # say why. Called for EVERY window, saturated and skipped ones
            # included, exactly as on the slice-parallel pass: "what this
            # window contributes" is precisely the decision such a policy
            # exists to make. Under the fixed-boundary legality every hook
            # consumer declares, ``accepted`` IS the stripped transcript the
            # parallel pass hands its own hook, so the two legs are one seam.
            hook_fields: dict[str, object] = {}
            if window_hook is not None:
                from .window_controller import record_controller_terminal

                record_controller_terminal(
                    window_hook, iteration=iteration, request_id=request_id,
                    response=response, saturated=saturated, skipped=skipped,
                )
                accepted, hook_fields = window_hook.accept(
                    iteration=iteration,
                    record=record,
                    transcript=accepted,
                    saturated=saturated,
                    skipped=skipped,
                )

            ctx.sink.emit(
                "OBS",
                f"{request_id}/obs",
                {
                    "obs_iteration": iteration,
                    "obs_window_start_seconds": record.start_seconds,
                    "obs_window_end_seconds": record.end_seconds,
                    "obs_final_window": is_final,
                    "obs_slice_relpath": relpath,
                    "obs_slice_sha256": record.sha256,
                    "obs_pre_sha256": pre_sha256,
                    "obs_preprocess": list(cfg.preprocess),
                    "obs_vad_engine": engine_descriptor,
                    "obs_boundary_mode": cfg.boundary_mode,
                    "obs_boundary_prompt_sha256": cfg.boundary_prompt_sha256,
                    "obs_boundary_estimate_seconds": resolution["estimate"],
                    "obs_boundary_snapped_seconds": resolution["snapped"],
                    "obs_boundary_advance_seconds": resolution["advance"],
                    "obs_boundary_clamped": resolution["clamped"],
                    "obs_boundary_fallback": resolution["fallback"],
                    "obs_accepted_chars": len(accepted),
                    "obs_dropped_chars": len(dropped),
                    "obs_tail_chars_used": len(tail),
                    "obs_tail_sha256": (
                        hashlib.sha256(tail.encode("utf-8")).hexdigest() if tail else None
                    ),
                    # Bounded per-slice retry audit trail (module comment at
                    # SLICE_RETRYABLE_EXCEPTIONS): when a retry answered this
                    # iteration, the ORIGINAL request id -- its MODEL_REQUEST
                    # record and metered spend precede this record; None on
                    # the ordinary first-attempt path.
                    "obs_retry_of": retry_of,
                    # Per-slice decode-cap saturation (module comment above
                    # _slice_saturated): True when this slice's completion hit
                    # the configured decoding_params.max_tokens cap -- counted
                    # and reported here, never scored silently.
                    "obs_saturated": saturated,
                    # Exhausted-slice skip (module comment above
                    # SLICE_RETRYABLE_EXCEPTIONS): True when every retry
                    # attempt for this slice failed and it was skipped as an
                    # honest hole -- counted and reported here, next to
                    # obs_retry_of/obs_saturated, never scored silently.
                    "obs_skipped": skipped,
                    # Unit-plan fields (preregistration section 8.3), present
                    # only when a plan supplied this cut -- identical to the
                    # slice-parallel path's own, so the two executors' traces
                    # cannot diverge in what a unit says about itself.
                    **_unit_trace_fields(unit),
                    # The hook's own fields, merged last and in the same
                    # position as on the slice-parallel pass, so what was
                    # delivered and why sits in the sealed trace beside what
                    # was said. Empty without a hook.
                    **hook_fields,
                },
            )
            accepted_spans.append(accepted.strip())
            # A skipped slice has no real response: nothing to hash into the
            # stitch (module comment above SLICE_RETRYABLE_EXCEPTIONS) --
            # request_ids/the per-iteration sha lists stay in lockstep,
            # covering only iterations that actually contributed content.
            if skipped:
                skipped_count += 1
                if skipped_count > cfg.slice_skip_max:
                    raise ObsLoopError(
                        _skip_bound_exceeded_message(sample.sample_id, skipped_count, cfg)
                    )
            else:
                request_ids.append(request_id)
                iteration_request_sha256s.append(response.request_sha256)
                iteration_response_sha256s.append(response.response_sha256)
            cursor = record.start_seconds + float(resolution["advance"])
            iteration += 1
            if iteration > max_iterations:
                raise ObsLoopError(
                    f"obs loop exceeded {max_iterations} iterations for sample "
                    f"{sample.sample_id!r}; refusing a runaway loop"
                )

        if not request_ids:
            raise ObsLoopError(
                f"sample {sample.sample_id!r} produced no successful requests (entirely "
                "trimmed as non-speech, or every slice skipped after exhausting retries?); "
                "refusing to emit an empty hypothesis silently"
            )

        stitched = stitch_ordered_text(accepted_spans)
        write_json_artifact(
            run_dir / f"{ctx.sink.run_id}.obs-derivation.{sample.sample_id}.json",
            {
                "schema": OBS_DERIVATION_SCHEMA,
                "run_id": ctx.sink.run_id,
                "sample_id": sample.sample_id,
                "parent_media_relpath": sample.media_relpath,
                "parent_sha256": parent_sha256,
                "decoded_duration_seconds": duration,
                "vad_engine": engine_descriptor,
                # Under a plan the advance semantics are still `fixed` (every
                # position was known before the first contact) but the cut came
                # from the plan, and a sealed run must say which
                # (preregistration section 8.4).
                "boundary_mode": (
                    OBS_UNIT_PLAN_BOUNDARY_MODE
                    if cfg.unit_plan is not None
                    else cfg.boundary_mode
                ),
                "boundary_prompt_relpath": cfg.boundary_prompt_relpath,
                "boundary_prompt_sha256": cfg.boundary_prompt_sha256,
                # The plan this run was cut by, named and pinned, so a later
                # reader re-derives the units instead of guessing them. Null on
                # every fixed-window run, exactly as boundary_prompt_* is null
                # on every fixed-boundary one.
                "unit_plan_path": cfg.unit_plan_relpath,
                "unit_plan_sha256": cfg.unit_plan_sha256,
                # OBS-E1b: which rule decided what this run stitched. Null on
                # every clock-cut and every v1/v2 run, where the stitch is the
                # responses themselves.
                "text_ownership": (
                    OWNERSHIP_PROTOCOL
                    if cfg.unit_plan is not None and cfg.unit_plan.has_context
                    else None
                ),
                "condition_tail_chars": cfg.condition_tail_chars,
                "trims": trim_events,
                "slices": [record.trace_view() for record in slice_records],
            },
        )

        request_descriptor = _canonical_bytes(
            {
                "stitched_request_ids": request_ids,
                "iteration_request_sha256s": iteration_request_sha256s,
            }
        )
        request_sha256 = hashlib.sha256(request_descriptor).hexdigest()
        response_descriptor = _canonical_bytes(
            {
                "stitched_text": stitched,
                "stitched_from_response_sha256s": iteration_response_sha256s,
            }
        )
        response_sha256 = hashlib.sha256(response_descriptor).hexdigest()
        response_text_sha256 = hashlib.sha256(stitched.encode("utf-8")).hexdigest()
        ctx.sink.emit(
            "MODEL_REQUEST",
            f"{ctx.request_id_base}/request",
            {
                "arm": ctx.arm,
                "payload_sha256": request_sha256,
                "stitch": True,
                "stitched_request_ids": request_ids,
            },
        )
        ctx.sink.emit(
            "MODEL_RESPONSE",
            f"{ctx.request_id_base}/response",
            {
                "text": stitched,
                "response_sha256": response_sha256,
                "response_text_sha256": response_text_sha256,
                "stitch": True,
                "stitched_from_response_sha256s": iteration_response_sha256s,
            },
        )
        ctx.sink.emit(
            "USE",
            f"{ctx.request_id_base}/use",
            {
                "use_response_sha256": response_sha256,
                "use_admitted": True,
                "use_stitched_iterations": len(request_ids),
            },
        )
        return SampleOutcome(
            sample_id=sample.sample_id,
            request_ids=tuple(request_ids),
            text=stitched,
            admitted=True,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            response_text_sha256=response_text_sha256,
            saturated_slices=saturated_count,
            skipped_slices=skipped_count,
        )

    @staticmethod
    def _resolve_ownership(windows, transcripts):
        """OBS-E1b: what each context-delivered unit contributes, or ``None``.

        ``None`` -- returned whenever the cut came from the clock or from a
        v1/v2 plan -- is the historical behaviour byte for byte: the run
        stitches the responses themselves. Under a v3 plan every boundary is
        resolved on the overlap both of its units received
        (``reproduction.obs_ownership``, whose module docstring carries the
        rule and whose proof is
        ``docs/checks/speech-aware-evidence-acquisition/2026-09-08-e21-obs-e1b-stitch-proof/``),
        and each unit's OBS record then carries what it actually delivered
        beside what the core actually said.
        """

        units = [window[5] for window in windows]
        if not units or any(unit is None or not unit.has_context for unit in units):
            return None
        from .obs_ownership import OwnershipUnit, resolve_ownership  # noqa: PLC0415

        decisions = resolve_ownership(
            [
                OwnershipUnit(
                    unit_id=unit.unit_id,
                    turn_start_seconds=unit.start_seconds,
                    turn_end_seconds=unit.end_seconds,
                    context_start_seconds=unit.cut_start_seconds,
                    context_end_seconds=unit.cut_end_seconds,
                    text=transcript,
                )
                for unit, transcript in zip(units, transcripts)
            ]
        )
        return [decision.trace_fields() for decision in decisions]

    def _window_hook(self, ctx, cfg, data_root, sample):
        """This policy's per-window hook, or ``None``.

        ``None`` here, always: ``obs-agent-loop`` sends one bare request per
        window and delivers what came back. A second-pass policy overrides
        THIS and nothing else -- ``run_sample``, the slice cutting, the retry
        and skip semantics, the stitch and the outcome are shared verbatim, so
        a repair pass cannot drift from the pass it is repairing (the owner's
        2026-09-03 "one base, thin derivations" rule, and the same reason
        ``reproduction.replay_loop`` calls ``_slice_parallel_pass`` rather than
        reimplementing it).

        Since the 2026-09-08 openJiuwen port BOTH of this policy's cutters run
        the hook -- the slice-parallel pass (which has had it since
        2026-09-07) and the sequential loop -- and so does the openJiuwen
        executor's sequential graph (``reproduction.ojw.components``). Which
        cutter runs is therefore a throughput choice and never a semantic one,
        which is what lets the plain SEQUENTIAL path be the byte-exact
        reference trajectory for the ojw graph's ``window-hook`` equivalence
        scenario."""

        return None

    @staticmethod
    def _next_trim(
        trim_spans: Sequence[tuple[float, float]], cursor: float, trim_min: float
    ) -> tuple[float, float] | None:
        """The first long non-speech span the cursor currently sits in (or at
        the edge of), if the remaining part of that span is itself still
        trim-worthy. Exact rule: span (s, e) applies when ``s <= cursor + 0.5``
        and ``e - max(s, cursor) >= trim_min``."""

        for span_start, span_end in trim_spans:
            if span_start <= cursor + 0.5 and span_end - max(span_start, cursor) >= trim_min:
                return (span_start, span_end)
        return None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(document: Mapping[str, object]) -> bytes:
    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
