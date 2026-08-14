"""The ``obs-replay-loop`` policy: listen (pass 1) -> score -> locate ->
retrieve -> replay (pass 2) -> accept.

The study's agentic listen-score-replay orchestration policy, assembling
already-merged organs (``core.replay_signals``, ``core.span_surgery``,
``core.retrieval``, ``core.exemplars``, ``core.model.transport``'s
``evidence-first-system-v3`` tiers) into one policy sitting beside
``reproduction.obs_loop.ObsAgentLoopPolicy`` -- registered under a different
policy name (``obs-replay-loop``), never modifying that module.

PASS 1 (listen): IDENTICAL to today's slice-parallel bare pass -- this
module calls ``ObsAgentLoopPolicy._slice_parallel_pass`` directly (the same
private method ``ObsAgentLoopPolicy.run_sample`` itself calls when
``obs_batch_slices > 1``), never a reimplementation. Because that method
unconditionally cuts FIXED windows with no VAD trim and no conditioned tail,
this policy enforces the same three-condition legality
(``obs_boundary_mode='fixed'``, ``obs_condition_tail_chars=0``,
``obs_vad_trim_min_seconds=0``) UNCONDITIONALLY -- not only when
``obs_batch_slices > 1`` the way ``ObsLoopConfig.from_values`` itself does --
since this policy always takes the slice-parallel path regardless of that
knob's value.

SCORE: per pass-1 slice, two independent trigger families
(``replay_trigger``: ``"wps"``, ``"logprob"`` or ``"both"``):

- ``"wps"``: ``core.replay_signals.words_per_second``/``is_catastrophic`` --
  a SLICE-level regime detector (module docstring of that file: a healthy
  run measures ~2.4 words/speech-second against a collapsed run's ~0.004).
  When catastrophic, the flagged "span" is the slice's ENTIRE transcript
  (word range ``(0, len(words))``) -- there is no finer-grained catastrophe
  location than "this whole buffer looked pathological".
- ``"logprob"``: requires ``replay_logprobs: true`` (below) so PASS 1's own
  requests carry ``decoding_params.logprobs``/``top_logprobs`` and the
  transport forwards whatever the server returns
  (``core.model.CoreResponse.logprobs``). ``core.replay_signals.
  slice_logprob_stats`` first gates the whole slice (skip per-word work
  entirely when zero tokens fall below ``replay_flag_low_threshold``), then
  a POSITIONAL (not text-aligned -- see :func:`_word_logprob_scores`)
  per-word score feeds ``core.replay_signals.flag_spans`` for contiguous
  low-confidence word runs.

Flags across both families are capped at ``replay_max_spans_per_slice``
(ascending word-start order, deterministic truncation).

LOCATE: for each flagged span, ``core.span_surgery.align_words`` aligns the
SLICE's OWN full pass-1 transcript against the SLICE's OWN wav (a genuine
tool-model touch this module does not itself gate -- see that function's own
docstring), once per slice regardless of how many spans it carries. The
flagged word run's timing plus a neighborhood-context window
(``replay_context_s`` each side, clamped to the slice's own duration) is cut
via ``core.span_surgery.cut_span`` (fine ``replay_span_pad_s`` pad folded
into the already-clamped bounds, so the derivation record's audio_seconds
stays bit-exact with the written file) into a derived replay-window wav,
registered through the SAME ``core.model.SliceRegistry`` derivation chain
pass-1's own windows use -- absolute (whole-call-relative) start/end
seconds, so it chains to the SAME parent media pass-1 already verified.

RETRIEVE: query = the flagged words; candidates = this sample's evidence
text, tokenized via ``core.candidate_materializer.pack_candidates`` keyed by
the run's own ``evidence_source`` (an evidence_source outside that module's
two known pack shapes yields an honestly empty pool, never an error) ->
``core.retrieval.retrieve`` top-``replay_k`` (cap 5) at or above
``replay_min_score``. If this run resolved an exemplar bank
(``SampleContext.exemplar_bank`` -- i.e. the composed config declared
``exemplar_manifest_id``), every retrieved term with a bank entry whose
NORMALIZED label matches is attached to tier 2 (uncapped, matching
``core.model.transport``'s own exemplar-bank shape); only the top 2 retrieved
terms become tier-3 text ``delta_candidates`` (the transport's own hard v3
cap, ``LlamaServerTransport._delta_candidate_entry``).

REPLAY: one ``core.model`` request per flagged span, through
``ctx.adapter.request`` -- the SAME gate/budget/metering/trace choke point
every pass-1 slice call already goes through (``core.model.adapter.
FrozenCoreAdapter.request``): no separate accounting path exists or is
needed. Tier 1 is ``replay_instruction`` (config text, never hardcoded
English in this module); tier 4 target is the replay-window wav; decoding
params are the arm's own (``ctx.decoding_params``, unmodified). Built via
``core.policies.build_arm_payload`` (extended here with a ``delta_candidates``
kwarg mirroring its existing ``exemplar_bank`` one) so the D2-frozen
per-arm field-set gate applies identically to every other request this
study ever sends. ``"fixed-legal-context-replay"`` (``e0.d2_leakage.
ARM_VISIBLE_FIELDS``, 2026-08-13) is the REPLAY-scoped arm that declares
both fields -- for that arm (or any other arm that declares them) a REPLAY
call attaches a tier EVEN WHEN EMPTY (required, not optional, once an arm's
D2-frozen field set names the field: ``core.model.FrozenCoreAdapter``'s own
allowlist demands an exact key-set match on every request that arm sends).
For every arm that does NOT declare a field, the pre-existing discipline is
unchanged: a REPLAY call attaches a tier only when there is actual matched
content for it, and an empty tier is omitted (not attached as an empty
list) precisely so this policy remains usable against those arms whenever
retrieval/exemplar-matching finds nothing to attach; real content the arm
cannot carry still fails closed (``ArmError``).

Because ``core.driver.run_experiment`` builds exactly ONE
``core.model.FrozenCoreAdapter`` per run, bound to the run's single
declared arm, PASS 1's own slice requests (reused verbatim from
``reproduction.obs_loop``, module docstring above) are bound to the SAME
arm as REPLAY and must ALSO satisfy whatever fields it declares --
extending an EXISTING arm's frozen field set in place would have broken
PASS 1's own calls this way (``obs_loop``'s slice payload builder never had
a "delta candidates" concept to thread through). The resolution is a NEW
arm rather than a mutated one, plus one small, arm-conditional addition to
``obs_loop``'s own slice payload builder: it now attaches an always-empty
``delta_candidates`` placeholder exactly when the run's arm declares the
field (satisfying the exact-match requirement for a tier PASS 1 itself
never has content for), and leaves every arm that does not declare the
field untouched.

ACCEPT (splice policy v1): reject an empty replay output, a replay output
whose normalized text equals the flagged run's own (nothing to correct), or
one exceeding ``replay_len_ratio_max`` times the flagged run's word count;
otherwise splice the replay words into the slice's own word sequence in
place of the flagged run. Multiple accepted spans in one slice are applied
in one left-to-right reconstruction pass (spans are non-overlapping,
ascending-start, per ``core.replay_signals.flag_spans``' own contract).
Deterministic given fixed inputs.

Trace: one ``REPLAY`` channel record per flagged span (``contracts.
boundary.TRACE_CHANNELS``/``_CHANNEL_PREFIX``, ``replay_``-prefixed,
mirroring OBS's own per-iteration convention) carries both texts, the
accept/reject decision and every span/candidate/window provenance fact.
A ``<run_id>.replay-derivation.<sample_id>.json`` artifact (mirroring
``obs_loop``'s own ``obs-derivation`` artifact) additionally records the
pass-1 slice set and every replay window in one place.

Fast path: a sample with zero flagged spans across every slice never calls
``align_words``/``cut_span``/``retrieve``/``ctx.adapter.request`` for
REPLAY at all, and its ``SampleOutcome`` (stitched text, request ids,
hashes) is BYTE-IDENTICAL to what ``ObsAgentLoopPolicy`` alone would have
produced for the same pass-1 responses -- the stitch descriptor's
``request_ids``/``iteration_request_sha256s``/``iteration_response_sha256s``
name only pass-1's own slice requests (unchanged shape/semantics from
``obs-agent-loop``); a REPLAY call's own request/response hashes are fully
recorded in the ``REPLAY`` trace channel instead, a deliberate scope
boundary documented here rather than folded into the stitch hash inputs.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..core.base import SampleContext, SampleOutcome
from ..core.candidate_materializer import MaterializeError, pack_candidates
from ..core.model import FrozenCoreError, SliceRecord, SliceRegistry
from ..core.replay_signals import (
    ReplaySignalsError,
    flag_spans,
    is_catastrophic,
    slice_logprob_stats,
    words_per_second,
)
from ..core.retrieval import RetrievalError, normalize_term, retrieve
from ..core.span_surgery import SpanSurgeryError, align_words, cut_span
from ..data.loader import SampleRef
from ..e0.artifacts import sha256_file, write_json_artifact
from ..e0.d2_leakage import ARM_VISIBLE_FIELDS
from . import obs_loop
from .obs_loop import (
    SLICE_SAMPLE_RATE_HZ,
    ObsAgentLoopPolicy,
    ObsLoopConfig,
    ObsLoopError,
)

OBS_REPLAY_LOOP_POLICY_NAME = "obs-replay-loop"
REPLAY_DERIVATION_SCHEMA = "saea-replay-derivation-v1"

# Transport's own hard v3 cap (core.model.transport._delta_candidate_entry /
# module docstring: "tier 3 [user, before the target] 0..2 delta
# candidates") -- replay_k may retrieve up to 5 for full audit visibility in
# the REPLAY trace record, but only the top TRANSPORT_DELTA_CANDIDATE_CAP by
# score are ever attached to the wire payload.
TRANSPORT_DELTA_CANDIDATE_CAP = 2

_TRIGGERS = ("wps", "logprob", "both")
_KNOWN_REPLAY_KEYS = frozenset(
    {
        "replay_logprobs",
        "replay_flag_low_threshold",
        "replay_flag_min_run",
        "replay_max_spans_per_slice",
        "replay_trigger",
        "replay_span_pad_s",
        "replay_context_s",
        "replay_k",
        "replay_min_score",
        "replay_instruction",
        "replay_len_ratio_max",
    }
)


class ReplayLoopError(RuntimeError):
    """The obs-replay-loop policy refuses: bad config, a broken derivation
    chain, or an unusable span/alignment/retrieval result."""


def _finite_number(values: Mapping[str, object], key: str, *, default: object = None) -> float:
    value = values.get(key, default) if default is not None else values.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ReplayLoopError(f"config {key} must be a finite number, got {value!r}")
    return float(value)


@dataclass(frozen=True)
class ReplayLoopConfig:
    """Validated ``replay_*`` knobs (all flow into config_hash ->
    protocol_hash through the baseline fragment that declares them, exactly
    like ``reproduction.obs_loop.ObsLoopConfig``'s own ``obs_*`` knobs --
    the same flat ``values`` mapping carries both prefixes, disjoint by
    construction)."""

    logprobs: bool
    flag_low_threshold: float
    flag_min_run: int
    max_spans_per_slice: int
    trigger: str
    span_pad_s: float
    context_s: float
    k: int
    min_score: float
    instruction: str
    len_ratio_max: float

    @classmethod
    def from_values(cls, values: Mapping[str, object]) -> "ReplayLoopConfig":
        unknown = sorted(
            key
            for key in values
            if isinstance(key, str) and key.startswith("replay_") and key not in _KNOWN_REPLAY_KEYS
        )
        if unknown:
            raise ReplayLoopError(
                f"unknown obs-replay-loop config keys {unknown}; a typo here would "
                f"silently change nothing but the protocol hash -- known keys: "
                f"{sorted(_KNOWN_REPLAY_KEYS)}"
            )

        logprobs = values.get("replay_logprobs", False)
        if not isinstance(logprobs, bool):
            raise ReplayLoopError(f"config replay_logprobs must be a bool, got {logprobs!r}")

        trigger = values.get("replay_trigger")
        if trigger not in _TRIGGERS:
            raise ReplayLoopError(
                f"config replay_trigger must be one of {_TRIGGERS}, got {trigger!r}"
            )

        # No baked-in default for the logprob threshold/run-length (core.
        # replay_signals module docstring, deliberate: "no D-1 measurement
        # grounds a specific logprob cut yet" -- unlike is_catastrophic's
        # own D-1-measured CATASTROPHIC_WPS_THRESHOLD default): the caller
        # must supply both explicitly, always (not merely when trigger
        # involves "logprob") for one uniform fail-closed rule.
        if "replay_flag_low_threshold" not in values:
            raise ReplayLoopError(
                "config replay_flag_low_threshold is required (no baked-in default -- "
                "core.replay_signals module docstring)"
            )
        flag_low_threshold = _finite_number(values, "replay_flag_low_threshold")

        flag_min_run = values.get("replay_flag_min_run")
        if isinstance(flag_min_run, bool) or not isinstance(flag_min_run, int) or flag_min_run < 1:
            raise ReplayLoopError(
                f"config replay_flag_min_run must be a positive integer, got {flag_min_run!r}"
            )

        max_spans_per_slice = values.get("replay_max_spans_per_slice")
        if (
            isinstance(max_spans_per_slice, bool)
            or not isinstance(max_spans_per_slice, int)
            or max_spans_per_slice < 1
        ):
            raise ReplayLoopError(
                "config replay_max_spans_per_slice must be a positive integer, got "
                f"{max_spans_per_slice!r}"
            )

        span_pad_s = values.get("replay_span_pad_s", 0.3)
        if (
            isinstance(span_pad_s, bool)
            or not isinstance(span_pad_s, (int, float))
            or not math.isfinite(span_pad_s)
            or span_pad_s < 0
        ):
            raise ReplayLoopError(
                f"config replay_span_pad_s must be a finite number >= 0, got {span_pad_s!r}"
            )

        context_s = values.get("replay_context_s", 5.0)
        if (
            isinstance(context_s, bool)
            or not isinstance(context_s, (int, float))
            or not math.isfinite(context_s)
            or context_s < 0
        ):
            raise ReplayLoopError(
                f"config replay_context_s must be a finite number >= 0, got {context_s!r}"
            )

        k = values.get("replay_k", 3)
        if isinstance(k, bool) or not isinstance(k, int) or not (1 <= k <= 5):
            raise ReplayLoopError(f"config replay_k must be an integer in [1, 5], got {k!r}")

        min_score = values.get("replay_min_score", 0.5)
        if (
            isinstance(min_score, bool)
            or not isinstance(min_score, (int, float))
            or not (0.0 <= float(min_score) <= 1.0)
        ):
            raise ReplayLoopError(
                f"config replay_min_score must be a number in [0, 1], got {min_score!r}"
            )

        instruction = values.get("replay_instruction")
        if not isinstance(instruction, str) or not instruction.strip():
            raise ReplayLoopError(
                "config replay_instruction must be a non-empty string (no hardcoded "
                f"English lives in code -- the instruction text lives in config), got "
                f"{instruction!r}"
            )

        len_ratio_max = values.get("replay_len_ratio_max", 3.0)
        if (
            isinstance(len_ratio_max, bool)
            or not isinstance(len_ratio_max, (int, float))
            or not math.isfinite(len_ratio_max)
            or len_ratio_max <= 0
        ):
            raise ReplayLoopError(
                f"config replay_len_ratio_max must be a finite number > 0, got {len_ratio_max!r}"
            )

        return cls(
            logprobs=logprobs,
            flag_low_threshold=flag_low_threshold,
            flag_min_run=flag_min_run,
            max_spans_per_slice=max_spans_per_slice,
            trigger=str(trigger),
            span_pad_s=float(span_pad_s),
            context_s=float(context_s),
            k=k,
            min_score=float(min_score),
            instruction=str(instruction),
            len_ratio_max=float(len_ratio_max),
        )


def _assert_pass1_legality(cfg: ObsLoopConfig) -> None:
    """Legality matrix (module docstring): PASS 1 always runs through
    ``ObsAgentLoopPolicy._slice_parallel_pass``, which unconditionally cuts
    FIXED windows with no VAD trim and no conditioned tail -- so this
    policy's config must be honest about that regardless of
    ``obs_batch_slices``' own value (unlike plain ``obs-agent-loop``, where
    the identical three-condition check only fires when
    ``obs_batch_slices > 1``). Fails closed in config composition, before
    any audio/model work."""

    if cfg.boundary_mode != "fixed":
        raise ReplayLoopError(
            "obs-replay-loop requires obs_boundary_mode='fixed' -- PASS 1 always runs "
            f"through the slice-parallel fixed-window pass, got {cfg.boundary_mode!r}"
        )
    if cfg.condition_tail_chars != 0:
        raise ReplayLoopError(
            "obs-replay-loop requires obs_condition_tail_chars=0 -- the slice-parallel "
            f"pass never feeds a rolling tail forward, got {cfg.condition_tail_chars!r}"
        )
    if cfg.vad_trim_min_seconds != 0:
        raise ReplayLoopError(
            "obs-replay-loop requires obs_vad_trim_min_seconds=0 -- the slice-parallel "
            f"pass never applies a runtime VAD trim, got {cfg.vad_trim_min_seconds!r}"
        )


class _RecordingAdapter:
    """Wraps ``ctx.adapter``, recording every ``(request_id -> response)``
    pair PASS 1 actually sent, keyed by the exact request id string used
    (including a retry's ``-r<n>`` suffix). Lets this policy read PASS 1's
    raw ``CoreResponse`` objects (``usage``, ``logprobs``) for the SCORE
    stage without touching ``ObsAgentLoopPolicy._slice_parallel_pass``'s
    return signature at all (module docstring: PASS 1 is reused verbatim).
    A failed attempt is never recorded (the real adapter raised before
    returning), matching ``request_slice_with_retry``'s own "only the
    attempt that actually answered matters" semantics."""

    def __init__(self, adapter: object) -> None:
        self._adapter = adapter
        self.responses: dict[str, object] = {}

    def request(self, payload: Mapping[str, object]) -> object:
        response = self._adapter.request(payload)
        self.responses[str(payload["request_id"])] = response
        return response

    def __getattr__(self, name: str) -> object:
        return getattr(self._adapter, name)


def _pass1_response_for_window(
    recorder: _RecordingAdapter, request_id_base: str, iteration: int, retry_max: int
) -> object | None:
    """The ``CoreResponse`` PASS 1 actually kept for slice ``iteration`` --
    the first of ``<base>``, ``<base>-r1``, ... ``<base>-r<retry_max>`` the
    recorder saw succeed (``request_slice_with_retry``'s own attempt-id
    convention, ``reproduction.obs_loop``). ``None`` for a slice that was
    skipped entirely (every attempt failed) -- SCORE already treats an
    empty transcript as nothing to flag before this is ever consulted."""

    base = f"{request_id_base}-i{iteration:04d}"
    for attempt_id in (base, *(f"{base}-r{n}" for n in range(1, retry_max + 1))):
        response = recorder.responses.get(attempt_id)
        if response is not None:
            return response
    return None


def _extract_token_logprobs(logprobs: object) -> list[float]:
    """Finite per-token logprob values out of a transport-forwarded
    ``choices[0].logprobs`` object (module docstring: llama-server's
    ``content`` list, each entry ``{"token": ..., "logprob": ...}``). Never
    raises: a missing or malformed object, or a non-numeric/non-finite
    entry, is simply excluded -- this SCORE-stage signal degrades
    gracefully rather than aborting a slice's flagging."""

    if not isinstance(logprobs, Mapping):
        return []
    content = logprobs.get("content")
    if not isinstance(content, list):
        return []
    values: list[float] = []
    for item in content:
        if not isinstance(item, Mapping):
            continue
        value = item.get("logprob")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            continue
        values.append(float(value))
    return values


def _word_logprob_scores(word_count: int, token_logprobs: Sequence[float]) -> list[float] | None:
    """One score per word: token index range ``[i*T/word_count,
    (i+1)*T/word_count)`` (T = token count) maps to word ``i``, scored by
    the MINIMUM logprob in that bucket (the weakest token in the region
    drives the flag -- ``core.replay_signals.flag_spans``' own "a run is as
    weak as its worst member" semantics).

    Deliberately POSITIONAL, not text-aligned: a token is frequently a
    sub-word BPE piece, and this repo runs with no logits access to resolve
    token<->word alignment precisely (``core.replay_signals`` module
    docstring: "behind a chat endpoint there are no logits"). Given the
    same D-1 finding that these behavioural signals are coarse regime
    detectors rather than fine rankers, a simple positional bucket is at
    least as defensible as a fragile string-offset alignment between two
    independently-produced token/word streams, and is far more robust.
    Returns ``None`` (never raises) when there is nothing to bucket."""

    if word_count <= 0 or not token_logprobs:
        return None
    token_count = len(token_logprobs)
    scores: list[float] = []
    for word_index in range(word_count):
        lo = (word_index * token_count) // word_count
        hi = max(lo + 1, ((word_index + 1) * token_count) // word_count)
        bucket = token_logprobs[lo:hi]
        scores.append(min(bucket) if bucket else min(token_logprobs))
    return scores


def _flag_spans_for_slice(
    words: list[str],
    word_scores: list[float] | None,
    audio_seconds: float,
    cfg: ReplayLoopConfig,
) -> list[tuple[tuple[int, int], str]]:
    """Every flagged ``(span, trigger_label)`` for one slice's transcript
    (module docstring's two trigger families), capped at
    ``cfg.max_spans_per_slice`` in ascending word-start order --
    deterministic given fixed inputs. ``trigger_label`` is ``"wps"``,
    ``"logprob"``, or ``"logprob,wps"`` when both families independently
    flag the identical span."""

    labels: dict[tuple[int, int], set[str]] = {}
    if cfg.trigger in ("wps", "both") and words:
        wps = words_per_second(len(words), audio_seconds)
        if is_catastrophic(wps):
            labels.setdefault((0, len(words)), set()).add("wps")
    if cfg.trigger in ("logprob", "both") and word_scores is not None and words:
        try:
            spans = flag_spans(words, word_scores, cfg.flag_low_threshold, cfg.flag_min_run)
        except ReplaySignalsError:
            spans = []
        for span in spans:
            labels.setdefault(span, set()).add("logprob")
    ordered = sorted(labels)[: cfg.max_spans_per_slice]
    return [(span, ",".join(sorted(labels[span]))) for span in ordered]


def _pack_terms(ctx: SampleContext) -> list[str]:
    """The candidate pool RETRIEVE draws from: this sample's own evidence
    content, tokenized via ``core.candidate_materializer.pack_candidates``
    keyed by the run's own ``evidence_source`` (module docstring). An
    evidence_source outside that module's two known pack shapes
    (``"conec-contexts"``/``"conec-names"``) yields an honestly empty pool
    for THAT item, never an error -- RETRIEVE already treats an empty pool
    as "nothing to retrieve"."""

    config_values = ctx.extras.get("config_values", {}) if isinstance(ctx.extras, Mapping) else {}
    evidence_source = str(config_values.get("evidence_source", "none")) if isinstance(config_values, Mapping) else "none"
    terms: dict[str, None] = {}
    for item in ctx.evidence or []:
        try:
            for term in pack_candidates(evidence_source, item.content):
                terms.setdefault(term, None)
        except MaterializeError:
            continue
    return list(terms)


def _matching_exemplars(
    exemplar_bank: Sequence[Mapping[str, object]] | None, retrieved_terms: Sequence[str]
) -> list[dict[str, object]]:
    """Bank entries (module docstring) whose NORMALIZED label matches one
    of ``retrieved_terms`` -- an empty list (never ``None``) when there is
    no bank or nothing retrieved, letting the caller decide "nothing to
    attach" uniformly."""

    if not exemplar_bank or not retrieved_terms:
        return []
    normalized_retrieved = {normalize_term(term) for term in retrieved_terms}
    matches: list[dict[str, object]] = []
    for pair in exemplar_bank:
        label = pair.get("label") if isinstance(pair, Mapping) else None
        if isinstance(label, str) and normalize_term(label) in normalized_retrieved:
            matches.append(dict(pair))
    return matches


def _cut_replay_window(
    slice_wav_path: Path,
    record: SliceRecord,
    aligned_words: list[dict[str, object]],
    span: tuple[int, int],
    *,
    pad_s: float,
    context_s: float,
    rate: int,
    out_path: Path,
) -> tuple[Path, float, float, float]:
    """Cut the flagged span's neighborhood-context window (module
    docstring's two-tier design) from the SLICE's own wav, returning
    ``(out_path, local_start_seconds, local_end_seconds, audio_seconds)``
    -- all SLICE-LOCAL (relative to the slice's own start, not the whole
    call). ``local_start``/``audio_seconds`` are computed from the SAME
    ``int(round(seconds * rate))`` sample-count rounding
    ``core.span_surgery.cut_span`` applies internally (called here with its
    own ``pad_s=0.0`` -- the pad is already folded into the pre-clamped
    bounds), so the caller's derivation record stays bit-exact with the
    file actually written (``core.model.slices.SliceRegistry``'s 1e-6
    float-tolerance equality check)."""

    start_idx, end_idx = span
    flagged_start_s = float(aligned_words[start_idx]["start_s"])
    flagged_end_s = float(aligned_words[end_idx - 1]["end_s"])
    slice_duration_s = record.audio_seconds
    context_start = max(0.0, flagged_start_s - context_s)
    context_end = min(slice_duration_s, flagged_end_s + context_s)
    padded_start = max(0.0, context_start - pad_s)
    padded_end = min(slice_duration_s, context_end + pad_s)
    if padded_end <= padded_start:
        raise ReplayLoopError(
            f"replay window for span {span} collapsed to an empty interval after "
            f"clamping to the slice's own [0, {slice_duration_s}] duration"
        )
    start_sample = int(round(padded_start * rate))
    end_sample = int(round(padded_end * rate))
    if end_sample <= start_sample:
        raise ReplayLoopError(
            f"replay window for span {span} rounded to an empty sample range "
            f"[{start_sample}, {end_sample})"
        )
    cut_span(slice_wav_path, padded_start, padded_end, 0.0, out_path)
    audio_seconds = (end_sample - start_sample) / rate
    local_start = start_sample / rate
    local_end = local_start + audio_seconds
    return out_path, local_start, local_end, audio_seconds


def _canonical_json_bytes(document: Mapping[str, object]) -> bytes:
    import json

    return json.dumps(
        document, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


class ObsReplayLoopPolicy:
    """One whole-call sample -> PASS 1 slice-parallel listen -> per-slice
    SCORE/LOCATE/RETRIEVE/REPLAY/ACCEPT -> one stitched hypothesis (module
    docstring). Stateless; every run fact arrives through ``SampleContext``
    (the SAME ``extras`` keys ``ObsAgentLoopPolicy`` reads)."""

    def run_sample(self, ctx: SampleContext) -> SampleOutcome:
        registry = ctx.extras.get("slice_registry")
        if not isinstance(registry, SliceRegistry):
            raise ReplayLoopError(
                "obs-replay-loop requires a core.model.SliceRegistry in "
                "SampleContext.extras['slice_registry'] (supplied by "
                "core.driver.run_experiment); refusing to cut unchained slices"
            )
        try:
            data_root = Path(ctx.extras["data_root"])
            run_dir = Path(ctx.extras["run_dir"])
            repo_root = Path(ctx.extras["repo_root"])
            config_values = ctx.extras["config_values"]
        except KeyError as error:
            raise ReplayLoopError(
                f"obs-replay-loop SampleContext.extras lacks {error}; supplied only by "
                "core.driver.run_experiment"
            ) from error

        # Deferred import (same reason reproduction.obs_loop's own
        # run_sample defers this identical import): core.policies imports
        # THIS module at its own bottom to register the policy; importing
        # build_arm_payload back at module level would be circular. By run
        # time both modules are always loaded.
        from ..core.policies import ArmError, build_arm_payload

        obs_cfg = ObsLoopConfig.from_values(config_values, repo_root)
        _assert_pass1_legality(obs_cfg)
        replay_cfg = ReplayLoopConfig.from_values(config_values)

        sample: SampleRef = ctx.sample
        rate = SLICE_SAMPLE_RATE_HZ
        parent_path = data_root / sample.media_relpath
        pcm = obs_loop.decode_parent_pcm(parent_path, rate)
        if not len(pcm):
            raise ReplayLoopError(f"decoded zero samples from {parent_path}")
        duration = len(pcm) / rate
        parent_sha256 = sha256_file(parent_path)

        evidence = ctx.evidence if ctx.arm != "bare-core" else None
        max_tokens = ctx.decoding_params.get("max_tokens")

        # PASS 1 (module docstring): reuse ObsAgentLoopPolicy's own
        # slice-parallel pass verbatim. The recorder + an optional
        # logprobs-requesting decoding_params override are the ONLY things
        # that differ from ObsAgentLoopPolicy.run_sample's own call -- both
        # are transparent to _slice_parallel_pass, which never inspects
        # ctx.adapter's type or ctx.decoding_params' exact key set beyond
        # what build_arm_payload/the adapter's own allowlist already check.
        recorder = _RecordingAdapter(ctx.adapter)
        pass1_decoding_params = dict(ctx.decoding_params)
        if replay_cfg.logprobs:
            pass1_decoding_params["logprobs"] = True
            pass1_decoding_params["top_logprobs"] = 1
        pass1_ctx = dataclasses.replace(
            ctx, adapter=recorder, decoding_params=pass1_decoding_params
        )

        (
            accepted_spans,
            request_ids,
            iteration_request_sha256s,
            iteration_response_sha256s,
            slice_records,
            saturated_count,
            skipped_count,
            iteration,
        ) = ObsAgentLoopPolicy()._slice_parallel_pass(
            pass1_ctx,
            obs_cfg,
            registry,
            data_root,
            sample,
            rate,
            pcm,
            duration,
            parent_sha256,
            "vad-not-run",
            evidence,
            max_tokens,
        )

        next_iteration = iteration
        replay_call_index = 0
        replay_window_records: list[dict[str, object]] = []
        pack_terms_cache: list[str] | None = None

        for slot_index, (transcript, record) in enumerate(zip(accepted_spans, slice_records)):
            if not transcript:
                continue
            words = transcript.split()
            if not words:
                continue

            word_scores: list[float] | None = None
            if replay_cfg.trigger in ("logprob", "both"):
                response = _pass1_response_for_window(
                    recorder, ctx.request_id_base, record.iteration, obs_cfg.slice_retry_max
                )
                token_logprobs = _extract_token_logprobs(getattr(response, "logprobs", None))
                if token_logprobs:
                    stats = slice_logprob_stats(
                        token_logprobs, below_threshold=replay_cfg.flag_low_threshold
                    )
                    if stats["below_threshold_count"] > 0:
                        word_scores = _word_logprob_scores(len(words), token_logprobs)

            spans = _flag_spans_for_slice(words, word_scores, record.audio_seconds, replay_cfg)
            if not spans:
                continue

            slice_wav_path = data_root / record.media_relpath
            try:
                aligned = align_words(slice_wav_path, words)
            except SpanSurgeryError as error:
                raise ReplayLoopError(
                    f"LOCATE alignment failed for slice iteration {record.iteration} of "
                    f"sample {sample.sample_id!r}: {error}"
                ) from error

            if pack_terms_cache is None:
                pack_terms_cache = _pack_terms(ctx)

            decisions: list[tuple[int, int, bool, list[str] | None]] = []
            for span_index, (span, trigger_label) in enumerate(spans):
                start_idx, end_idx = span
                flagged_words = words[start_idx:end_idx]
                flagged_text = " ".join(flagged_words)

                relpath = registry.slice_relpath(sample.sample_id, next_iteration)
                out_path = data_root / relpath
                out_path.parent.mkdir(parents=True, exist_ok=True)
                _, local_start, local_end, cut_audio_seconds = _cut_replay_window(
                    slice_wav_path,
                    record,
                    aligned,
                    span,
                    pad_s=replay_cfg.span_pad_s,
                    context_s=replay_cfg.context_s,
                    rate=rate,
                    out_path=out_path,
                )
                cut_bytes = out_path.read_bytes()
                cut_sha256 = hashlib.sha256(cut_bytes).hexdigest()
                absolute_start = record.start_seconds + local_start
                absolute_end = record.start_seconds + local_end
                replay_slice_record = SliceRecord(
                    sample_id=sample.sample_id,
                    parent_media_relpath=sample.media_relpath,
                    parent_sha256=parent_sha256,
                    start_seconds=absolute_start,
                    end_seconds=absolute_end,
                    audio_seconds=cut_audio_seconds,
                    sample_rate_hz=rate,
                    media_relpath=relpath,
                    sha256=cut_sha256,
                    bytes=len(cut_bytes),
                    iteration=next_iteration,
                    preprocess=(),
                    pre_sha256=None,
                )
                registry.register(replay_slice_record)

                query_terms = flagged_words
                retrieved: list[tuple[str, float]] = []
                if pack_terms_cache and query_terms:
                    try:
                        retrieved = retrieve(
                            query_terms, pack_terms_cache, replay_cfg.k, replay_cfg.min_score
                        )
                    except RetrievalError:
                        retrieved = []

                matching_exemplars = _matching_exemplars(
                    ctx.exemplar_bank, [term for term, _score in retrieved]
                )
                delta_terms = retrieved[:TRANSPORT_DELTA_CANDIDATE_CAP]
                delta_candidates_content = [{"text": term} for term, _score in delta_terms]
                # Attach a (possibly empty) tier whenever ctx.arm's D2-frozen
                # field set declares it -- REQUIRED once declared, since
                # core.policies.build_arm_payload demands an EXACT field-set
                # match. The module docstring's "an empty tier is omitted"
                # discipline applies only to an arm that does NOT declare the
                # field; an arm that DOES declare it (e.g.
                # "fixed-legal-context-replay") must carry the key on every
                # request, empty-content REPLAY calls included, or the
                # exact-match check would refuse an otherwise-legal request.
                # An arm that does not declare the field keeps the exact
                # pre-existing behaviour: omitted when there is nothing to
                # attach, refused (ArmError, unchanged --
                # see test_replay_call_refused_when_arm_does_not_declare_the_
                # attached_tier) when there is real content it cannot carry.
                arm_fields = ARM_VISIBLE_FIELDS[ctx.arm]
                exemplar_payload = (
                    matching_exemplars
                    if (matching_exemplars or "exemplar_bank" in arm_fields)
                    else None
                )
                delta_candidates_payload = (
                    delta_candidates_content
                    if (delta_candidates_content or "delta_candidates" in arm_fields)
                    else None
                )

                replay_request_id = f"{ctx.request_id_base}-replay{replay_call_index:03d}"
                replay_sample_ref = SampleRef(
                    carrier_lock_key=sample.carrier_lock_key,
                    sample_id=sample.sample_id,
                    media_relpath=relpath,
                    audio_seconds=cut_audio_seconds,
                    sample_rate_hz=rate,
                )
                try:
                    replay_payload = build_arm_payload(
                        ctx.arm,
                        replay_sample_ref,
                        replay_request_id,
                        replay_cfg.instruction,
                        dict(ctx.decoding_params),
                        evidence=evidence,
                        retrieval_query=ctx.retrieval_query,
                        exemplar_bank=exemplar_payload,
                        delta_candidates=delta_candidates_payload,
                    )
                except ArmError as error:
                    raise ReplayLoopError(
                        f"REPLAY payload refused for arm {ctx.arm!r}: {error}"
                    ) from error

                try:
                    replay_response = ctx.adapter.request(replay_payload)
                except FrozenCoreError as error:
                    raise ReplayLoopError(
                        f"REPLAY request failed for span {span} of sample "
                        f"{sample.sample_id!r}: {error}"
                    ) from error

                replay_text = getattr(replay_response, "text", "") or ""
                replay_words = replay_text.split()
                flagged_normalized = normalize_term(flagged_text)
                replay_normalized = normalize_term(replay_text)
                accepted = False
                reject_reason: str | None = None
                if not replay_words:
                    reject_reason = "empty-replay-output"
                elif replay_normalized == flagged_normalized:
                    reject_reason = "replay-text-unchanged"
                elif len(replay_words) > replay_cfg.len_ratio_max * max(1, len(flagged_words)):
                    reject_reason = "length-ratio-exceeded"
                else:
                    accepted = True

                decisions.append((start_idx, end_idx, accepted, replay_words if accepted else None))

                window_record = {
                    "replay_sample_id": sample.sample_id,
                    "replay_slice_iteration": record.iteration,
                    "replay_window_iteration": next_iteration,
                    "replay_span_index": span_index,
                    "replay_span_start_word": start_idx,
                    "replay_span_end_word": end_idx,
                    "replay_trigger": trigger_label,
                    "replay_window_relpath": relpath,
                    "replay_window_sha256": cut_sha256,
                    "replay_window_start_seconds": absolute_start,
                    "replay_window_end_seconds": absolute_end,
                    "replay_window_audio_seconds": cut_audio_seconds,
                    "replay_query_terms": list(query_terms),
                    "replay_candidates": [
                        {"text": term, "score": score} for term, score in retrieved
                    ],
                    "replay_exemplars_attached": [
                        pair.get("label") for pair in matching_exemplars
                    ],
                    "replay_pass1_text": flagged_text,
                    "replay_replay_text": replay_text,
                    "replay_accepted": accepted,
                    "replay_reject_reason": reject_reason,
                    "replay_request_sha256": getattr(replay_response, "request_sha256", None),
                    "replay_response_sha256": getattr(replay_response, "response_sha256", None),
                }
                ctx.sink.emit("REPLAY", f"{replay_request_id}/replay", window_record)
                replay_window_records.append(window_record)

                next_iteration += 1
                replay_call_index += 1

            rebuilt: list[str] = []
            cursor = 0
            for start_idx, end_idx, accepted, replacement in decisions:
                rebuilt.extend(words[cursor:start_idx])
                rebuilt.extend(replacement if accepted else words[start_idx:end_idx])
                cursor = end_idx
            rebuilt.extend(words[cursor:])
            accepted_spans[slot_index] = " ".join(rebuilt)

        if not request_ids:
            raise ObsLoopError(
                f"sample {sample.sample_id!r} produced no successful requests (entirely "
                "trimmed as non-speech, or every slice skipped after exhausting retries?); "
                "refusing to emit an empty hypothesis silently"
            )

        stitched = " ".join(span for span in accepted_spans if span)
        write_json_artifact(
            run_dir / f"{ctx.sink.run_id}.replay-derivation.{sample.sample_id}.json",
            {
                "schema": REPLAY_DERIVATION_SCHEMA,
                "run_id": ctx.sink.run_id,
                "sample_id": sample.sample_id,
                "parent_media_relpath": sample.media_relpath,
                "parent_sha256": parent_sha256,
                "decoded_duration_seconds": duration,
                "pass1_slices": [record.trace_view() for record in slice_records],
                "replay_windows": replay_window_records,
            },
        )

        request_descriptor = _canonical_json_bytes(
            {
                "stitched_request_ids": request_ids,
                "iteration_request_sha256s": iteration_request_sha256s,
            }
        )
        request_sha256 = hashlib.sha256(request_descriptor).hexdigest()
        response_descriptor = _canonical_json_bytes(
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
