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

PASS-1 exemplar-bank suppression (defect fix, measured 2026-08-14, ``docs/
readiness/2026-08-14-p1-ceiling-verdict.md``): ``_slice_parallel_pass``'s own
slice payload builder threads ``ctx.exemplar_bank`` into EVERY pass-1 slice
request unconditionally -- correct for the static ``exemplar-context`` arm,
but for ``"fixed-legal-context-replay"`` this let a non-empty own-call
exemplar ride every pass-1 request; on sample 4389907 the core transcribed
the exemplar audio instead of slice content 17x (44.49 WER, 1116 deletions).
The bank belongs at REPLAY (tier 2) only for this policy, per the RETRIEVE
section below -- so ``run_sample`` builds ``pass1_ctx`` with the bank's
CONTENT emptied (an always-empty tuple, not ``None``, whenever the arm's
D2-frozen field set still declares ``exemplar_bank`` -- the exact-field-match
contract in ``core.policies.build_arm_payload`` requires the key on every
request such an arm sends, mirroring the pre-existing always-empty
``delta_candidates`` placeholder ``obs_loop.py``'s own slice payload builder
already threads for the identical reason (see this docstring's REPLAY
section below).

PASS-1 evidence suppression (``replay_pass1_evidence``, design gap, ``docs/
exposure-ledger.md``'s SAEA-D7-delivery consumption note, 2026-08-15): the
D7 delivery-gate probe measured a static+replay same-content confound -- an
evidence-bearing arm's PASS 1 already sees the same roster the REPLAY
flags/corrections are drawn from, so pass-1 bias can consume the very
errors the flags target before SCORE ever runs. ``"arm-default"`` (default,
byte-identical) leaves PASS 1's evidence untouched; ``"suppressed"`` builds
the same ``pass1_ctx``-adjacent evidence value this policy already computes
with its CONTENT emptied -- an always-empty list, never omitted, mirroring
the exemplar-bank suppression paragraph above -- so an evidence-bearing arm
still carries the ``supplied_evidence``/``retrieved_evidence`` keys on every
pass-1 request but with nothing in them; REPLAY's own evidence/candidate
resolution (RETRIEVE, exemplar matching) is entirely unaffected. The
R-ladder needs exactly this bare-pass-1/replay-only-delivery vehicle before
any campaign (wf_c21a2756 Phase-2 shared-draft design).

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

FLAG SOURCES (D5 rectification, ``docs/readiness/2026-08-15-rectification-
plan.md``): ``replay_flag_source`` selects WHICH mechanism fills the
``"logprob"`` trigger family's role above -- the ``"wps"`` catastrophe
detector is identical either way.

- ``"logprob"`` (default): the SCORE description above, unchanged --
  contiguous low-confidence word runs from PASS 1's own per-token
  logprobs. Measured (``docs/readiness/2026-08-14-p1-ceiling-verdict.md``,
  finding 1): 0/17 entity overlap -- every logprob-flagged span on the
  clean P1 samples was function-word/boundary text ("with a", "for the",
  "increase by"), never one of the real entity errors the oracle
  candidates could have corrected; the correction filter then (correctly)
  found nothing to retrieve and every REPLAY call was skipped.
- ``"roster-band"``: ``core.flag_sources.roster_band_flags`` replaces
  logprob-derived word_scores with weighted-grapheme band-matching against
  this sample's own resolved evidence candidate terms (RETRIEVE's own pool,
  ``_pack_terms``) plus exemplar-bank labels when one was resolved -- see
  ``core.flag_sources`` module docstring for the frozen band/distance/rarity
  parameters. Offline-validated at proper-name P@1=0.252 (the flag-eval
  harness's S1 method against the same class of earnings-call drafts) --
  the mechanism this mode ports, faithfully, into the study package. In
  this mode PASS 1's requests still carry ``decoding_params.logprobs``
  whenever ``replay_logprobs: true`` (request-shape stability across arms
  -- ``build_arm_payload``'s exact-field-match contract does not vary by
  ``replay_flag_source``), but the returned logprobs are never consulted
  for flagging. The trace's per-window record additionally carries
  ``replay_flag_source``/``replay_flag_matched_candidate``/
  ``replay_flag_matched_form``/``replay_flag_distance`` (``None`` for a
  ``"wps"``-only span, or under ``"logprob"`` mode).

D7/D7B chain-defect fix (``docs/exposure-ledger.md``'s SAEA-D7-delivery/
SAEA-D7B-delivery consumption notes, 2026-08-14/2026-08-15): ``_pack_terms``
now also resolves ``evidence_source == "derived-candidates"`` -- previously
an unsupported ``pack_candidates`` shape whose ``MaterializeError`` was
silently swallowed into an EMPTY pool on every call, so roster-band never
ran at all (guarded by ``and candidate_terms``) and both probes flew a
zero-flag pass undetected. Fail-closed guard: under ``"roster-band"``, a
declared (non-``"none"``) evidence_source whose resolved pool (plus
exemplar-bank labels) is still EMPTY for a sample now raises at sample start
instead of flying that silent zero-flag pass -- except a derived-candidates
file that genuinely has zero non-blank lines, which is allowed and recorded
on the replay-derivation artifact (``replay_pack_terms_empty_note``).

Guard 1, SCORE-stage min-score floor (D7D fix, ``docs/exposure-ledger.md``'s
SAEA-D7D-delivery consumption note, 2026-08-15): under ``"roster-band"``,
``replay_flag_min_score`` (default 0.15, only legal in this mode) drops any
span whose SCORE-stage ``band_centrality * rarity`` lands below the floor
before it is ever flagged -- measured live: near-zero sub-token band matches
(score 0.0-0.034) were issuing full REPLAY calls with nothing worth
correcting. Recorded on the replay-derivation artifact
(``replay_flag_min_score``, ``None`` outside roster-band mode).

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
two known pack shapes yields an honestly empty pool, never an error).

D7C delivery-gate fix (``docs/exposure-ledger.md``'s SAEA-D7C-delivery
consumption note, 2026-08-15, measured at commit 7295b39): a roster-band
flagged window already carries SCORE's own matched candidate
(``RosterBandFlag.candidate``/``matched_form``) -- re-searching the pool
here with ``retrieve``'s different fuzzy metric dropped that very match for
107/117 windows in flight, including all three known true errors. Such a
window now delivers that candidate directly -- resolved to its ORIGINAL
cased materialization form, never the normalized one -- bypassing this
section's ``retrieve`` call entirely; a ``"wps"``-triggered window (no
matched candidate) is unaffected and still follows the paragraph below.
``core.flag_sources``' own df-rarity term was widened the same day to the
whole-SAMPLE pass-1 draft's word counts, not just this one slice's, for the
matching reason (that module's own docstring).

CORRECTION SEMANTICS (DEFECT 2 fix, first hit SAEA-MM3-replay 2026-08-14 --
flagged "conditions and" retrieved its own verbatim "conditions" as the top
candidate at score 1.0, burying the real corrections "condition"/
"conditioner" underneath it): every pack candidate whose
``core.retrieval.normalize_term`` form equals ANY flagged/query word is
dropped BEFORE ``core.retrieval.retrieve`` ever scores it (ported from
``core.candidate_materializer.materialize_sample``, commit 4a78dfa) --
surviving candidates are things the flagged run does NOT already say. The
survivors go through ``retrieve`` top-``replay_k`` (cap 5) at or above
``replay_min_score``. If this run resolved an exemplar bank
(``SampleContext.exemplar_bank`` -- i.e. the composed config declared
``exemplar_manifest_id``), every bank entry whose NORMALIZED label matches
EITHER a retrieved term OR one of the flagged words itself is attached to
tier 2 (uncapped, matching ``core.model.transport``'s own exemplar-bank
shape) -- unlike a text delta-candidate (redundant once verbatim), an
exemplar clip is a pronunciation anchor and stays useful even when its own
label is the very word the flagged run already (mis)produced, which is what
keeps a span "still replayable with exemplars" once the correction filter
above empties the text-candidate pool; only the top 2 retrieved terms become
tier-3 text ``delta_candidates`` (the transport's own hard v3 cap,
``LlamaServerTransport._delta_candidate_entry``).

SKIP (DEFECT 2 fix): once the correction filter runs, an arm whose
D2-frozen field set can actually CARRY a correction signal (declares
``exemplar_bank`` and/or ``delta_candidates``) skips the REPLAY call
entirely -- no ``ctx.adapter.request`` at all -- when BOTH the retrieved set
and the exemplar match are empty (``"no-candidates"``, recorded in the
REPLAY trace with the request/response hashes left ``None``): there is
nothing to correct with and nothing to anchor with, so a call would only
re-hear with zero new information. This gate is scoped to arms that could
have carried something: a bare-core-shaped arm (declares neither field)
never attaches either tier regardless of what RETRIEVE finds (see ACCEPT's
own "usable against every arm" note below), so a REPLAY call under such an
arm is ALWAYS a zero-bias re-listen probe by design, not a wasted one --
skip never applies to it.

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

REPLAY PROMPT TEMPLATING (R-ladder prep, ``docs/readiness/2026-08-15-
rectification-plan.md`` PHASE 2 -- R0-bias/R1-verify/R2-draft each need
different per-window content spliced into an otherwise shared framing): an
optional ``replay_prompt_template`` config string, when present, replaces
``replay_instruction`` as tier 1 after substituting ``{draft_span}`` (this
window's own flagged pass-1 text) and ``{reference}`` (whatever correction
content RETRIEVE attached for this window, empty when none) -- both slots
optional in any given template, both newline-stripped before substitution,
unknown slot names refused at config load (never at request time). Absent
the key, behaviour is byte-identical to today; the rendered instruction is
never traced verbatim, only its ``replay_prompt_rendered_sha256`` hash
(this module's existing hash-not-raw-text discipline). PASS 1's own task
instruction is untouched either way.

ACCEPT (splice policy v2, DEFECT 1 fix -- first hit SAEA-MM3-replay
2026-08-14): the REPLAY request transcribes the WHOLE replay window
(``replay_context_s`` seconds either side of the flagged span, LOCATE
section above), not just the flagged region -- comparing THAT whole-window
transcript's length against the flagged run's own (often 2-3 words) made
acceptance unreachable (8/12 real MM3 spans rejected
``"length-ratio-exceeded"``; a further 2/12 falsely ACCEPTED a whole
unrelated sentence spliced in place of a 2-word flagged run). LOCALIZE
first: once a non-empty replay transcript comes back, a SECOND
``core.span_surgery.align_words`` call -- the same authorized tool pathway
LOCATE already uses above, one MORE alignment per REPLAYED span (never per
skipped or fast-path span) -- aligns the replay transcript to the replay
window's own wav; the flagged span's own timing within that window (already
known -- it is exactly what was cut, LOCATE section above) then selects
only the aligned replay words whose ``[start_s, end_s]`` MIDPOINT falls
inside that interval, padded by ``replay_span_pad_s``. THAT localized word
run -- not the full replay transcript -- is both the splice replacement and
the length-ratio operand. Reject reasons, in order: an empty replay output
(``"empty-replay-output"``); a non-empty replay output with nothing
localizeable inside the flagged interval, including an alignment failure
(``"no-overlap-words"``); a localized run whose normalized text equals the
flagged run's own (nothing to correct, ``"replay-text-unchanged"``); a
localized run whose normalized text equals the delivered reference text,
including a trivial punctuation variant (nothing beyond the supplied hint,
``"reference-echo"``, Guard 2 below); one exceeding ``replay_len_ratio_max``
times the flagged run's word count (``"length-ratio-exceeded"``); a
localized run containing a delivered-reference word with no fuzzy support
(``core.flag_sources.weighted_grapheme_distance``, band ``BAND_HIGH``) in the
flagged run itself (``"splice-unsupported-reference"``, Guard 3 below).
Otherwise splice the localized words into the slice's own word sequence in
place of the flagged run.

Guards 2/3 (D7D fix, ``docs/exposure-ledger.md``'s SAEA-D7D-delivery
consumption note, 2026-08-15): measured live, 14/115 replay outputs were
ONLY the delivered reference string (some accepted and spliced,
:func:`_reference_echo_reject`), and mislocalized splices injected roster
words -- including metadata typo forms -- into unrelated filler (e.g. "we'll
be right Bistricer Micheal with you", :func:`_unsupported_reference_word`).
A word the model produced on its own re-hearing, not sourced from the
delivered reference, is never blocked by Guard 3. Multiple accepted
spans in one slice are applied in one left-to-right reconstruction pass
(spans are non-overlapping, ascending-start, per
``core.replay_signals.flag_spans``' own contract). A span RETRIEVE already
skipped (``"no-candidates"`` above) never reaches this stage at all -- it is
spliced as a reject with no replay text to judge. Deterministic given fixed
inputs.

This policy remains usable against every arm, including one whose D2-frozen
field set carries neither ``exemplar_bank`` nor ``delta_candidates``
(``"bare-core"``): a REPLAY call attaches a tier only when there is actual
matched content for it AND the arm declares the field, an empty tier is
omitted (not attached as an empty list) for an arm that does not declare
it, and real content the arm cannot carry still fails closed (``ArmError``)
-- see RETRIEVE's SKIP note above for why this also means the DEFECT 2 skip
gate never applies to such an arm.

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
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..core.base import SampleContext, SampleOutcome
from ..core.candidate_materializer import MaterializeError, pack_candidates
from ..core.evidence import derived_candidates_file_relpath, resolve_evidence_materialization_id
from ..core.flag_sources import (
    BAND_HIGH,
    RosterBandFlag,
    roster_band_flags,
    weighted_grapheme_distance,
)
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
_FLAG_SOURCES = ("logprob", "roster-band")
_KNOWN_REPLAY_KEYS = frozenset(
    {
        "replay_logprobs",
        "replay_flag_low_threshold",
        "replay_flag_min_run",
        "replay_max_spans_per_slice",
        "replay_trigger",
        "replay_flag_source",
        "replay_flag_min_score",
        "replay_span_pad_s",
        "replay_context_s",
        "replay_k",
        "replay_min_score",
        "replay_instruction",
        "replay_len_ratio_max",
        "replay_prompt_template",
        "replay_pass1_evidence",
    }
)

# REPLAY PROMPT TEMPLATING (module docstring's own section): the only two
# slot names `replay_prompt_template` may reference -- anything else fails
# closed at config load (ReplayLoopConfig.from_values), never at request
# time.
_REPLAY_PROMPT_SLOTS = frozenset({"draft_span", "reference"})

# PASS-1 evidence suppression (module docstring's own section, D7 delivery
# -gate design-gap fix, 2026-08-15): "arm-default" is the untouched default
# every pre-existing config keeps; "suppressed" empties PASS 1's own
# evidence content.
_PASS1_EVIDENCE_MODES = ("arm-default", "suppressed")


class ReplayLoopError(RuntimeError):
    """The obs-replay-loop policy refuses: bad config, a broken derivation
    chain, or an unusable span/alignment/retrieval result."""


def _finite_number(values: Mapping[str, object], key: str, *, default: object = None) -> float:
    value = values.get(key, default) if default is not None else values.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ReplayLoopError(f"config {key} must be a finite number, got {value!r}")
    return float(value)


def _validate_replay_prompt_template(template: str) -> None:
    """Fail-closed at config-load time, never at request time (module
    docstring's REPLAY PROMPT TEMPLATING section): every ``{...}`` field
    name in ``template`` must be one of :data:`_REPLAY_PROMPT_SLOTS` --
    a typo here would otherwise only surface as a ``KeyError`` deep inside
    a REPLAY request, well after the config was already accepted."""

    import string

    try:
        field_names = {
            field_name
            for _, field_name, _, _ in string.Formatter().parse(template)
            if field_name is not None
        }
    except ValueError as error:
        raise ReplayLoopError(
            f"config replay_prompt_template is not a valid template: {error}"
        ) from error
    unknown = sorted(field_names - _REPLAY_PROMPT_SLOTS)
    if unknown:
        raise ReplayLoopError(
            f"config replay_prompt_template references unknown slot(s) {unknown}; "
            f"known slots: {sorted(_REPLAY_PROMPT_SLOTS)}"
        )


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
    flag_source: str
    flag_min_score: float
    span_pad_s: float
    context_s: float
    k: int
    min_score: float
    instruction: str
    len_ratio_max: float
    prompt_template: str | None
    pass1_evidence: str

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

        # D5 (module docstring's FLAG SOURCES section): defaults to
        # "logprob" so every pre-existing config/test that never sets this
        # key keeps byte-identical behaviour; fails closed on anything else
        # (a typo here would silently fall back to logprob flagging).
        flag_source = values.get("replay_flag_source", "logprob")
        if flag_source not in _FLAG_SOURCES:
            raise ReplayLoopError(
                f"config replay_flag_source must be one of {_FLAG_SOURCES}, got {flag_source!r}"
            )

        # Guard 1 (D7D fix, ``docs/exposure-ledger.md``'s SAEA-D7D-delivery
        # consumption note, 2026-08-15; core.flag_sources.roster_band_flags'
        # own ``min_score`` docstring): only legal under
        # replay_flag_source="roster-band" -- a stray key left over from a
        # copy-pasted logprob-mode fragment would otherwise silently do
        # nothing, the same key-legality discipline
        # core.evidence.assert_evidence_materialization_id_legal already
        # applies to its own source-scoped key.
        flag_min_score = values.get("replay_flag_min_score", 0.15)
        if (
            isinstance(flag_min_score, bool)
            or not isinstance(flag_min_score, (int, float))
            or not (0.0 <= float(flag_min_score) <= 1.0)
        ):
            raise ReplayLoopError(
                f"config replay_flag_min_score must be a number in [0, 1], got "
                f"{flag_min_score!r}"
            )
        if flag_source != "roster-band" and "replay_flag_min_score" in values:
            raise ReplayLoopError(
                "config replay_flag_min_score is only legal with "
                f"replay_flag_source='roster-band', got replay_flag_source={flag_source!r}"
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

        # Optional (module docstring's REPLAY PROMPT TEMPLATING section):
        # absent key -> None -> byte-identical behaviour (REPLAY keeps using
        # `instruction` unmodified). When present, validated eagerly here
        # (fail closed on an unknown slot at config load, never at request
        # time) rather than deferred to first substitution.
        prompt_template = values.get("replay_prompt_template")
        if prompt_template is not None:
            if not isinstance(prompt_template, str) or not prompt_template.strip():
                raise ReplayLoopError(
                    "config replay_prompt_template must be a non-empty string when "
                    f"present, got {prompt_template!r}"
                )
            _validate_replay_prompt_template(prompt_template)

        # D7 (module docstring's PASS-1 evidence suppression section):
        # defaults to "arm-default" so every pre-existing config/test that
        # never sets this key keeps byte-identical behaviour; fails closed
        # on anything else, the same discipline replay_flag_source above
        # already carries.
        pass1_evidence = values.get("replay_pass1_evidence", "arm-default")
        if pass1_evidence not in _PASS1_EVIDENCE_MODES:
            raise ReplayLoopError(
                f"config replay_pass1_evidence must be one of {_PASS1_EVIDENCE_MODES}, "
                f"got {pass1_evidence!r}"
            )

        return cls(
            logprobs=logprobs,
            flag_low_threshold=flag_low_threshold,
            flag_min_run=flag_min_run,
            max_spans_per_slice=max_spans_per_slice,
            trigger=str(trigger),
            flag_source=str(flag_source),
            flag_min_score=float(flag_min_score),
            span_pad_s=float(span_pad_s),
            context_s=float(context_s),
            k=k,
            min_score=float(min_score),
            instruction=str(instruction),
            len_ratio_max=float(len_ratio_max),
            prompt_template=str(prompt_template) if prompt_template is not None else None,
            pass1_evidence=str(pass1_evidence),
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


def _flag_spans_for_slice_roster_band(
    words: list[str],
    candidate_terms: Sequence[str],
    audio_seconds: float,
    cfg: ReplayLoopConfig,
    *,
    df: Mapping[str, int] | None = None,
) -> tuple[list[tuple[tuple[int, int], str]], dict[tuple[int, int], RosterBandFlag]]:
    """roster-band counterpart to :func:`_flag_spans_for_slice` (D5, module
    docstring's FLAG SOURCES section): the ``"wps"`` family is IDENTICAL
    (same catastrophe detector, same call); the ``"logprob"`` family's ROLE
    (per-slice contiguous-flagging) is filled by ``core.flag_sources.
    roster_band_flags`` instead of ``core.replay_signals.flag_spans`` --
    everything else (label merge on an exact-span collision, ascending
    -start truncation at ``cfg.max_spans_per_slice``) is the identical
    contract :func:`_flag_spans_for_slice` already establishes. Returns the
    same ``(span, trigger_label)`` list shape PLUS a ``span ->
    RosterBandFlag`` detail map (the matched candidate term / distance the
    trace record needs, module docstring's Trace requirement) -- a
    ``"wps"``-only span carries no detail entry.

    ``df`` (D7C fix, module docstring's D7C paragraph): the whole-SAMPLE
    pass-1 draft word-count table, threaded straight through to
    ``roster_band_flags`` -- see that function's own docstring.

    Guard 1 (D7D fix, module docstring): ``cfg.flag_min_score`` is threaded
    straight through to ``roster_band_flags``'s own ``min_score`` -- see
    that function's own docstring."""

    labels: dict[tuple[int, int], set[str]] = {}
    detail: dict[tuple[int, int], RosterBandFlag] = {}
    if cfg.trigger in ("wps", "both") and words:
        wps = words_per_second(len(words), audio_seconds)
        if is_catastrophic(wps):
            labels.setdefault((0, len(words)), set()).add("wps")
    if cfg.trigger in ("logprob", "both") and words and candidate_terms:
        for flag in roster_band_flags(
            words, candidate_terms, cfg.max_spans_per_slice, df=df, min_score=cfg.flag_min_score
        ):
            labels.setdefault(flag.span, set()).add("roster-band")
            detail[flag.span] = flag
    ordered = sorted(labels)[: cfg.max_spans_per_slice]
    return [(span, ",".join(sorted(labels[span]))) for span in ordered], detail


def _pack_terms(ctx: SampleContext, data_root: Path) -> tuple[list[str], str | None]:
    """The candidate pool RETRIEVE (and, under ``replay_flag_source=
    "roster-band"``, SCORE) draws from: this sample's own evidence content,
    tokenized via ``core.candidate_materializer.pack_candidates`` keyed by
    the run's own ``evidence_source`` (module docstring) for the two
    verbatim-passthrough conec sources -- or, for ``"derived-candidates"``
    (D7/D7B chain-defect fix), read DIRECTLY off the offline-materialized
    file the SAME materialization this run's evidence already resolves
    (``core.evidence.resolve_evidence_materialization_id`` /
    ``derived_candidates_file_relpath``, never re-derived path logic), one
    candidate per non-blank line -- bypassing ``pack_candidates`` entirely,
    since that function only ever knew the two conec shapes and previously
    raised (silently swallowed below) for this one. This reads straight off
    disk rather than ``ctx.evidence`` so PASS-1 evidence suppression
    (``replay_pass1_evidence="suppressed"``, this module's own docstring
    section) can never affect it: this pool feeds REPLAY-stage machinery and
    must reflect the resolved materialization regardless of what PASS 1 was
    or was not allowed to see. Any OTHER evidence_source (including
    ``"none"``) yields an honestly empty pool for THAT item, never an error
    -- RETRIEVE already treats an empty pool as "nothing to retrieve".

    Returns ``(terms, empty_note)``: ``empty_note`` is ``None`` unless
    ``terms`` is empty for the one LEGITIMATE reason a caller must not treat
    as a configuration/materialization error -- a derived-candidates file
    that exists, reads cleanly, and genuinely has zero non-blank lines
    (``"empty-candidates-file"``)."""

    config_values = ctx.extras.get("config_values", {}) if isinstance(ctx.extras, Mapping) else {}
    evidence_source = str(config_values.get("evidence_source", "none")) if isinstance(config_values, Mapping) else "none"

    if evidence_source == "derived-candidates":
        materialization_id = resolve_evidence_materialization_id(config_values)
        relpath = derived_candidates_file_relpath(materialization_id, ctx.sample.sample_id)
        path = Path(data_root) / relpath
        if not path.is_file():
            raise ReplayLoopError(
                "obs-replay-loop candidate pool: derived-candidates materialization "
                f"{materialization_id!r} has no candidates file for sample "
                f"{ctx.sample.sample_id!r} at {path} -- a configuration/materialization "
                "error, not a legitimately empty pool"
            )
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise ReplayLoopError(
                "obs-replay-loop candidate pool: cannot read derived-candidates file "
                f"{path} for sample {ctx.sample.sample_id!r}: {error}"
            ) from error
        derived_terms: dict[str, None] = {}
        for line in content.splitlines():
            stripped = line.strip()
            if stripped:
                derived_terms.setdefault(stripped, None)
        if not derived_terms:
            return [], "empty-candidates-file"
        return list(derived_terms), None

    terms: dict[str, None] = {}
    for item in ctx.evidence or []:
        try:
            for term in pack_candidates(evidence_source, item.content):
                terms.setdefault(term, None)
        except MaterializeError:
            continue
    return list(terms), None


def _roster_band_candidate_terms(ctx: SampleContext, pack_terms: Sequence[str]) -> list[str]:
    """The roster-band SCORE stage's candidate/target set (D5, module
    docstring's FLAG SOURCES section): ``pack_terms`` (the SAME evidence
    pool RETRIEVE already draws from, :func:`_pack_terms`) union this run's
    exemplar-bank labels when one was resolved. Matches ``ctx.exemplar_bank``
    directly, the same "no bank -> nothing to add" discipline
    :func:`_matching_exemplars` already applies -- gated on the bank being
    resolved at all, never on the arm's D2-frozen field-set legality (this
    is pure text matching over already-resolved run facts, not a wire
    payload attachment)."""

    terms: dict[str, None] = {term: None for term in pack_terms}
    for pair in ctx.exemplar_bank or ():
        label = pair.get("label") if isinstance(pair, Mapping) else None
        if isinstance(label, str) and label:
            terms.setdefault(label, None)
    return list(terms)


def _correction_pool(candidates: Sequence[str], flagged_words: Sequence[str]) -> list[str]:
    """DEFECT 2 fix, port of ``core.candidate_materializer.
    materialize_sample``'s correction semantics (commit 4a78dfa, module
    docstring's RETRIEVE section): every candidate whose
    ``core.retrieval.normalize_term`` form equals ANY normalized
    ``flagged_words`` entry is dropped -- a pack term the flagged run
    already says verbatim needs no supplying (it would otherwise score 1.0
    and trivially win retrieval over the real correction). Order-preserving,
    pure; may return an empty list (the caller treats that as nothing to
    retrieve, module docstring's SKIP note)."""

    flagged_forms = {normalize_term(word) for word in flagged_words}
    return [term for term in candidates if normalize_term(term) not in flagged_forms]


def _resolve_original_cased_term(candidate_terms: Sequence[str], normalized_target: str) -> str:
    """D7C fix (module docstring's D7C paragraph): the ORIGINAL,
    materialization-cased string in ``candidate_terms`` whose
    ``core.retrieval.normalize_term`` form equals ``normalized_target`` --
    i.e. the exact ``RosterBandFlag.candidate`` a matched roster-band window
    is about to deliver, resolved back to the file/evidence line it came
    from rather than delivering the already-normalized (lowercased,
    depunctuated) form. First match wins when two distinct original strings
    normalize identically, deterministic given ``candidate_terms``' own
    order (mirroring ``core.flag_sources.roster_band_flags``'s own
    first-registered-term-wins tie rule for a shared decomposed form).
    Falls back to ``normalized_target`` itself when no match is found --
    should not happen in practice, since ``normalized_target`` always
    originates from one of these SAME ``candidate_terms`` via
    ``roster_band_flags``, but this stays a safe, non-raising default rather
    than an assertion a caller has to guard against."""

    for term in candidate_terms:
        if normalize_term(term) == normalized_target:
            return term
    return normalized_target


def _localize_replay_words(
    aligned_replay_words: Sequence[Mapping[str, object]],
    interval: tuple[float, float],
) -> list[str]:
    """DEFECT 1 fix (module docstring's ACCEPT section, first hit
    SAEA-MM3-replay 2026-08-14): the subset of ``aligned_replay_words`` --
    one ``core.span_surgery.align_words``-shaped ``{"word", "start_s",
    "end_s"}`` entry per REPLAY-transcript word, timestamps LOCAL to the
    replay window's own wav -- whose MIDPOINT falls inside ``interval``
    (``(lo, hi)``, inclusive both ends: the flagged span's own timing
    within the window, already padded by ``replay_span_pad_s``), returned in
    input (left-to-right transcript) order. Pure, deterministic; may be
    empty when nothing aligned inside the interval -- the caller rejects
    with ``"no-overlap-words"``."""

    lo, hi = interval
    selected: list[str] = []
    for entry in aligned_replay_words:
        start_s = float(entry["start_s"])
        end_s = float(entry["end_s"])
        midpoint = (start_s + end_s) / 2.0
        if lo <= midpoint <= hi:
            selected.append(str(entry["word"]))
    return selected


def _reference_echo_reject(localized_text: str, reference_text: str) -> bool:
    """Guard 2 (D7D fix, ``docs/exposure-ledger.md``'s SAEA-D7D-delivery
    consumption note, 2026-08-15, module docstring's ACCEPT section): True
    when ``localized_text``, normalized the same way the judge already
    normalizes the flagged run (``core.retrieval.normalize_term``), equals
    the delivered ``reference_text`` -- a trivial punctuation-only variant
    included for free, since ``normalize_term`` already strips punctuation
    entirely regardless of position. ``reference_text`` empty (nothing was
    delivered) never triggers this guard -- nothing was echoed."""

    if not reference_text:
        return False
    return normalize_term(localized_text) == normalize_term(reference_text)


def _unsupported_reference_word(
    localized_words: Sequence[str],
    reference_text: str,
    flagged_words: Sequence[str],
) -> str | None:
    """Guard 3 (D7D fix, ``docs/exposure-ledger.md``'s SAEA-D7D-delivery
    consumption note, 2026-08-15, module docstring's ACCEPT section): the
    first ``localized_words`` entry (input order) that (i) normalizes to a
    word appearing in the delivered ``reference_text`` and (ii) has NO word
    of the flagged span itself (``flagged_words`` -- the ORIGINAL pass-1
    text this window replaces, not the whole slice) within
    ``core.flag_sources.BAND_HIGH`` weighted-grapheme distance, i.e. no
    fuzzy support for having actually been said. A localized word the model
    produced on its own re-hearing (not one of the reference's own words) is
    never checked -- this guard only distrusts a splice where the sole
    reason a roster word appears is that it was handed to the model as a
    hint, unsupported by anything pass-1 itself heard (measured: mislocalized
    splices injecting roster words, including metadata typo forms, into
    unrelated filler). ``None`` when every localized word either is not a
    reference word or has support, or when ``reference_text`` is empty."""

    reference_words = set(normalize_term(reference_text).split()) if reference_text else set()
    if not reference_words:
        return None
    flagged_normalized = [
        normalized for word in flagged_words if (normalized := normalize_term(word))
    ]
    for word in localized_words:
        normalized_word = normalize_term(word)
        if not normalized_word or normalized_word not in reference_words:
            continue
        if not flagged_normalized:
            return normalized_word
        min_distance = min(
            weighted_grapheme_distance(normalized_word, flagged_word)
            for flagged_word in flagged_normalized
        )
        if min_distance > BAND_HIGH:
            return normalized_word
    return None


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


def _sanitize_replay_prompt_slot(value: str) -> str:
    """Minimal slot sanitization for ``replay_prompt_template`` substitution
    (module docstring's REPLAY PROMPT TEMPLATING section): strip newlines to
    spaces so a multi-line draft/reference can never fracture the rendered
    instruction's own line structure. No other normalization -- the
    template owns everything else about the final instruction's shape."""

    return value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")


def _render_replay_instruction(
    template: str | None, base_instruction: str, draft_span: str, reference: str
) -> str:
    """The REPLAY request's tier-1 task instruction (module docstring's
    REPLAY PROMPT TEMPLATING section): byte-identical to ``base_instruction``
    when no template is configured (``template is None`` -- the regression
    contract), else ``template`` with ``{draft_span}``/``{reference}``
    substituted (either or both may be absent from a given template; a
    template with neither is a pure framing swap). Slot validity is already
    guaranteed by :func:`_validate_replay_prompt_template` at config-load
    time, so this never raises."""

    if template is None:
        return base_instruction
    return template.format(
        draft_span=_sanitize_replay_prompt_slot(draft_span),
        reference=_sanitize_replay_prompt_slot(reference),
    )


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
) -> tuple[Path, float, float, float, float, float]:
    """Cut the flagged span's neighborhood-context window (module
    docstring's two-tier design) from the SLICE's own wav, returning
    ``(out_path, local_start_seconds, local_end_seconds, audio_seconds,
    flagged_local_start_seconds, flagged_local_end_seconds)`` -- all
    SLICE-LOCAL (relative to the slice's own start, not the whole call)
    EXCEPT the last two, which are WINDOW-LOCAL (relative to the cut
    window's own start, i.e. ``flagged_start_s - local_start`` /
    ``flagged_end_s - local_start``): the flagged span's own timing
    expressed in the frame ACCEPT's DEFECT-1 localization step (module
    docstring) needs, since it aligns the replay transcript against this
    SAME cut window file, not the original slice. ``local_start``/
    ``audio_seconds`` are computed from the SAME ``int(round(seconds *
    rate))`` sample-count rounding ``core.span_surgery.cut_span`` applies
    internally (called here with its own ``pad_s=0.0`` -- the pad is
    already folded into the pre-clamped bounds), so the caller's derivation
    record stays bit-exact with the file actually written
    (``core.model.slices.SliceRegistry``'s 1e-6 float-tolerance equality
    check)."""

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
    flagged_local_start = flagged_start_s - local_start
    flagged_local_end = flagged_end_s - local_start
    return out_path, local_start, local_end, audio_seconds, flagged_local_start, flagged_local_end


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
        # Fail-closed guard input (D7/D7B chain-defect fix, module
        # docstring's FLAG SOURCES section): whether this run's config
        # DECLARES an evidence source at all -- "none" means it does not,
        # exactly the local `_pack_terms` itself computes from the same
        # `config_values` mapping.
        config_evidence_source = (
            str(config_values.get("evidence_source", "none"))
            if isinstance(config_values, Mapping)
            else "none"
        )

        sample: SampleRef = ctx.sample
        rate = SLICE_SAMPLE_RATE_HZ
        parent_path = data_root / sample.media_relpath
        pcm = obs_loop.decode_parent_pcm(parent_path, rate)
        if not len(pcm):
            raise ReplayLoopError(f"decoded zero samples from {parent_path}")
        duration = len(pcm) / rate
        parent_sha256 = sha256_file(parent_path)

        evidence = ctx.evidence if ctx.arm != "bare-core" else None
        # SAEA-P2 abort fix (core.evidence._derived_candidates module comment,
        # 2026-08-15 P2 abort): the SAME empty-by-materialization signal
        # reproduction.obs_loop's own run_sample computes (identical
        # docstring there) -- a legitimately empty derived-candidates
        # materialization resolves this sample's evidence to an empty list,
        # but an arm that declares an evidence field still requires
        # build_arm_payload's allow_empty_evidence to accept it for THIS
        # sample. Threaded into PASS 1 below (mirroring the
        # replay_pass1_evidence="suppressed" vehicle) and into REPLAY's own
        # build_arm_payload call further down, for the same reason -- a
        # "wps"-triggered REPLAY call (candidates never required) can still
        # fire on a sample whose materialized pool is legitimately empty.
        evidence_empty_by_materialization = (
            evidence is not None
            and not evidence
            and config_evidence_source == "derived-candidates"
        )
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
            # request-shape stability across arms/flag sources: this key is
            # governed solely by replay_logprobs, never by replay_flag_source
            # -- under "roster-band" the SCORE stage below never reads the
            # returned logprobs, but PASS 1's own request shape stays
            # identical to "logprob" mode regardless (module docstring's
            # FLAG SOURCES section), so switching flag_source alone can never
            # change what PASS 1 sends the model.
            pass1_decoding_params["logprobs"] = True
            pass1_decoding_params["top_logprobs"] = 1
        # Defect fix (module docstring's PASS-1 section, measured 2026-08-14):
        # obs_loop's slice payload builder threads whatever exemplar_bank
        # this ctx carries into EVERY pass-1 slice request unconditionally --
        # the bank belongs at REPLAY only for this policy. Emptying the
        # CONTENT (an always-empty tuple, never None) rather than dropping
        # the field keeps build_arm_payload's exact-field-match contract
        # satisfied for an arm whose D2-frozen set still declares
        # "exemplar_bank" (e.g. "fixed-legal-context-replay").
        pass1_exemplar_bank = (
            () if "exemplar_bank" in ARM_VISIBLE_FIELDS[ctx.arm] else None
        )
        # D7 (module docstring's PASS-1 evidence suppression section):
        # "suppressed" mirrors the exemplar-bank suppression immediately
        # above -- emptying the CONTENT, never dropping the key -- but only
        # when this arm/sample actually carries evidence at all (`evidence
        # is not None`; a bare-core arm's `evidence` is already `None` here
        # and stays so regardless of this knob, since bare-core declares
        # neither evidence field for build_arm_payload to attach). Threaded
        # into `_slice_parallel_pass` below as a SEPARATE `pass1_evidence`
        # value, never through `pass1_ctx.evidence` -- that method reads its
        # own `evidence` parameter, not `ctx.evidence` (see its own call
        # site in ObsAgentLoopPolicy.run_sample). REPLAY's own evidence
        # (the `evidence` local variable below) is untouched either way.
        pass1_evidence_suppressed = (
            replay_cfg.pass1_evidence == "suppressed" and evidence is not None
        )
        pass1_evidence = [] if pass1_evidence_suppressed else evidence
        pass1_ctx = dataclasses.replace(
            ctx,
            adapter=recorder,
            decoding_params=pass1_decoding_params,
            exemplar_bank=pass1_exemplar_bank,
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
            pass1_evidence,
            max_tokens,
            allow_empty_evidence=pass1_evidence_suppressed or evidence_empty_by_materialization,
        )

        next_iteration = iteration
        replay_call_index = 0
        replay_window_records: list[dict[str, object]] = []
        pack_terms_cache: list[str] | None = None
        pack_terms_empty_note: str | None = None
        # D7C fix (module docstring's D7C paragraph, core.flag_sources'
        # own docstring): the whole-SAMPLE pass-1 draft's own normalized
        # word-count table -- built ONCE, here, from the PRISTINE
        # `accepted_spans` PASS 1 just returned (before this loop starts
        # splicing REPLAY text back into it below) -- so a word recurring
        # across MULTIPLE slices reads as common even though any one
        # slice's own local count of it may be 1. Threaded into every
        # roster-band SCORE call for this sample, never recomputed per
        # slice.
        sample_word_df: Counter[str] = Counter()
        for pass1_transcript in accepted_spans:
            if not pass1_transcript:
                continue
            for pass1_word in pass1_transcript.split():
                normalized_pass1_word = normalize_term(pass1_word)
                if normalized_pass1_word:
                    sample_word_df[normalized_pass1_word] += 1

        for slot_index, (transcript, record) in enumerate(zip(accepted_spans, slice_records)):
            if not transcript:
                continue
            words = transcript.split()
            if not words:
                continue

            band_detail_by_span: dict[tuple[int, int], RosterBandFlag] = {}
            if replay_cfg.flag_source == "roster-band":
                # D5 (module docstring's FLAG SOURCES section): the
                # roster-band candidate/target set IS RETRIEVE's own pool
                # (plus exemplar labels), so it must be resolved before
                # SCORE runs, not lazily after LOCATE like the logprob-mode
                # branch below.
                if pack_terms_cache is None:
                    pack_terms_cache, pack_terms_empty_note = _pack_terms(ctx, data_root)
                candidate_terms = _roster_band_candidate_terms(ctx, pack_terms_cache)
                # FAIL CLOSED on silent emptiness (D7/D7B chain-defect fix,
                # module docstring's FLAG SOURCES section): a declared
                # evidence source whose resolved pool -- plus whatever
                # exemplar-bank labels this sample carries, the SAME union
                # roster-band's own SCORE stage is about to search -- is
                # still EMPTY is a configuration/materialization error, not
                # "nothing to flag"; flying it silently is exactly the
                # SAEA-D7-delivery/SAEA-D7B-delivery shape. The one
                # legitimate empty pool (a derived-candidates file that
                # genuinely has zero non-blank lines, `_pack_terms`'s own
                # "empty-candidates-file" note) is exempted -- allowed, not
                # an error, and already recorded on the replay-derivation
                # artifact below.
                if (
                    not candidate_terms
                    and config_evidence_source != "none"
                    and pack_terms_empty_note != "empty-candidates-file"
                ):
                    raise ReplayLoopError(
                        "obs-replay-loop roster-band: evidence_source="
                        f"{config_evidence_source!r} is declared but sample "
                        f"{sample.sample_id!r}'s resolved candidate pool (plus exemplar-bank "
                        "labels) is empty -- refusing to fly a silent zero-flag pass "
                        "(configuration/materialization error)"
                    )
                spans, band_detail_by_span = _flag_spans_for_slice_roster_band(
                    words, candidate_terms, record.audio_seconds, replay_cfg, df=sample_word_df
                )
            else:
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
                pack_terms_cache, pack_terms_empty_note = _pack_terms(ctx, data_root)

            decisions: list[tuple[int, int, bool, list[str] | None]] = []
            for span_index, (span, trigger_label) in enumerate(spans):
                start_idx, end_idx = span
                flagged_words = words[start_idx:end_idx]
                flagged_text = " ".join(flagged_words)
                replay_request_id = f"{ctx.request_id_base}-replay{replay_call_index:03d}"
                # Trace enrichment (D5, module docstring's FLAG SOURCES
                # section): None under logprob mode, or for a "wps"-only
                # span even under roster-band mode.
                band_flag = band_detail_by_span.get(span)

                query_terms = flagged_words
                if band_flag is not None:
                    # D7C fix (module docstring's D7C paragraph): this
                    # window's own SCORE-stage weighted-grapheme band match
                    # IS its delivery set -- re-searching the pool below
                    # with retrieve()'s different fuzzy metric is exactly
                    # what dropped 107/117 matched windows in flight,
                    # including all three known true errors (measured at
                    # commit 7295b39). `candidate_terms` here is the SAME
                    # roster-band candidate/target pool this slice's SCORE
                    # stage already searched (set above, in scope for the
                    # whole slice iteration whenever flag_source ==
                    # "roster-band" -- the only case band_flag can be
                    # non-None). The score recorded alongside it is the
                    # band flag's own (band_centrality * rarity), not a
                    # retrieve() score -- retrieve() never runs for this
                    # window at all.
                    resolved_candidate = _resolve_original_cased_term(
                        candidate_terms, band_flag.candidate
                    )
                    retrieved = [(resolved_candidate, band_flag.score)]
                else:
                    # RETRIEVE (DEFECT 2 fix, module docstring's CORRECTION
                    # SEMANTICS note): drop any pack candidate the flagged
                    # run already says verbatim BEFORE retrieve() ever
                    # scores it. Unchanged for a "wps"-triggered window
                    # (no matched candidate, module docstring's D7C
                    # paragraph) regardless of flag_source.
                    correction_pool = (
                        _correction_pool(pack_terms_cache, query_terms) if pack_terms_cache else []
                    )
                    retrieved = []
                    if correction_pool and query_terms:
                        try:
                            retrieved = retrieve(
                                query_terms, correction_pool, replay_cfg.k, replay_cfg.min_score
                            )
                        except RetrievalError:
                            retrieved = []

                # Exemplar matching also checks the flagged words themselves,
                # not only retrieved text candidates (module docstring's
                # RETRIEVE section): an exemplar clip is a pronunciation
                # anchor, not a text suggestion, so it stays useful even when
                # its own label IS the word the flagged run already said.
                exemplar_match_terms = list(
                    dict.fromkeys([term for term, _score in retrieved] + list(query_terms))
                )
                matching_exemplars = _matching_exemplars(ctx.exemplar_bank, exemplar_match_terms)

                # An arm's D2-frozen field set is looked up once for both
                # the SKIP decision below and the payload-attachment rule
                # further down (same "an empty tier is omitted unless the
                # arm declares the field, required once declared" contract
                # -- core.policies.build_arm_payload demands an EXACT
                # field-set match).
                arm_fields = ARM_VISIBLE_FIELDS[ctx.arm]
                can_attach_correction = (
                    "exemplar_bank" in arm_fields or "delta_candidates" in arm_fields
                )

                if can_attach_correction and not retrieved and not matching_exemplars:
                    # DEFECT 2 fix, module docstring's SKIP note: nothing to
                    # correct with and nothing to anchor with -- burning a
                    # REPLAY model call to re-hear with zero new information
                    # is pure waste. No adapter.request at all for this span;
                    # never reaches LOCATE/ACCEPT below.
                    window_record = {
                        "replay_sample_id": sample.sample_id,
                        "replay_slice_iteration": record.iteration,
                        "replay_window_iteration": None,
                        "replay_span_index": span_index,
                        "replay_span_start_word": start_idx,
                        "replay_span_end_word": end_idx,
                        "replay_trigger": trigger_label,
                        "replay_window_relpath": None,
                        "replay_window_sha256": None,
                        "replay_window_start_seconds": None,
                        "replay_window_end_seconds": None,
                        "replay_window_audio_seconds": None,
                        "replay_query_terms": list(query_terms),
                        "replay_candidates": [],
                        "replay_exemplars_attached": [],
                        "replay_pass1_text": flagged_text,
                        "replay_replay_text": None,
                        "replay_accepted": False,
                        "replay_reject_reason": "no-candidates",
                        "replay_request_sha256": None,
                        "replay_response_sha256": None,
                        "replay_localized_words": [],
                        "replay_localized_word_count": 0,
                        "replay_localize_source": None,
                        "replay_flag_source": replay_cfg.flag_source,
                        "replay_flag_matched_candidate": band_flag.candidate if band_flag else None,
                        "replay_flag_matched_form": band_flag.matched_form if band_flag else None,
                        "replay_flag_distance": band_flag.distance if band_flag else None,
                        # No REPLAY request was ever built for a skipped span
                        # (module docstring's SKIP note) -- no instruction was
                        # ever rendered either, so this stays None exactly
                        # like the request/response hashes above.
                        "replay_prompt_rendered_sha256": None,
                    }
                    ctx.sink.emit("REPLAY", f"{replay_request_id}/replay", window_record)
                    replay_window_records.append(window_record)
                    decisions.append((start_idx, end_idx, False, None))
                    replay_call_index += 1
                    continue

                relpath = registry.slice_relpath(sample.sample_id, next_iteration)
                out_path = data_root / relpath
                out_path.parent.mkdir(parents=True, exist_ok=True)
                (
                    _,
                    local_start,
                    local_end,
                    cut_audio_seconds,
                    flagged_local_start,
                    flagged_local_end,
                ) = _cut_replay_window(
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

                # REPLAY PROMPT TEMPLATING (module docstring's own section):
                # `{reference}` is whatever correction content RETRIEVE
                # attached for THIS window -- the top delivered delta-term
                # text(s) plus any matched exemplar labels, in that order --
                # empty when the arm delivers none. This mirrors the CONTENT
                # (`delta_terms`/`matching_exemplars`), not the arm-gated
                # payload above, since a template render never itself raises
                # ArmError.
                reference_parts = [term for term, _score in delta_terms]
                for pair in matching_exemplars:
                    label = pair.get("label")
                    if isinstance(label, str) and label:
                        reference_parts.append(label)
                # Guards 2/3 (D7D fix, module docstring's ACCEPT section)
                # reuse this SAME delivered-reference text below -- the
                # ACCEPT stage's "what was this window handed as a hint"
                # is, by construction, identical to the prompt-template
                # `{reference}` slot's own content.
                reference_text = " ".join(reference_parts)
                rendered_instruction = _render_replay_instruction(
                    replay_cfg.prompt_template,
                    replay_cfg.instruction,
                    flagged_text,
                    reference_text,
                )
                rendered_instruction_sha256 = hashlib.sha256(
                    rendered_instruction.encode("utf-8")
                ).hexdigest()

                replay_sample_ref = SampleRef(
                    carrier_lock_key=sample.carrier_lock_key,
                    sample_id=sample.sample_id,
                    media_relpath=relpath,
                    audio_seconds=cut_audio_seconds,
                    sample_rate_hz=rate,
                )
                # PASS-1's slice-parallel pool resolves the id_slot
                # "per-sample" sentinel to an allocated slot; this one-off
                # REPLAY request does not run through that pool, so the raw
                # sentinel would fail closed at the adapter (first hit:
                # SAEA-MM3-replay, 2026-08-14). REPLAY calls are sequential
                # per sample -- pin them all to slot 0.
                replay_decoding = dict(ctx.decoding_params)
                if replay_decoding.get("id_slot") == "per-sample":
                    replay_decoding["id_slot"] = 0
                try:
                    replay_payload = build_arm_payload(
                        ctx.arm,
                        replay_sample_ref,
                        replay_request_id,
                        rendered_instruction,
                        replay_decoding,
                        evidence=evidence,
                        retrieval_query=ctx.retrieval_query,
                        exemplar_bank=exemplar_payload,
                        delta_candidates=delta_candidates_payload,
                        allow_empty_evidence=evidence_empty_by_materialization,
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
                replay_words_full = replay_text.split()
                flagged_normalized = normalize_term(flagged_text)

                localized_words: list[str] = []
                localize_source: str | None = None
                accepted = False
                reject_reason: str | None = None

                if not replay_words_full:
                    reject_reason = "empty-replay-output"
                else:
                    # LOCALIZE (DEFECT 1 fix, module docstring's ACCEPT
                    # section, first hit SAEA-MM3-replay 2026-08-14): a
                    # SECOND align_words call -- the same authorized tool
                    # pathway LOCATE above already uses, one MORE CPU
                    # alignment per REPLAYED span (this span already passed
                    # the SKIP gate above, so it is a genuine, already
                    # counted model-adjacent tool touch, not an extra one --
                    # core.span_surgery's own docstring gates the MODEL
                    # touch itself, not per-call policy bookkeeping, exactly
                    # as LOCATE's own call already relies on) -- aligns the
                    # REPLAY TRANSCRIPT to the REPLAY WINDOW wav just
                    # written above, then keeps only the words whose
                    # timestamp midpoint falls inside the flagged span's own
                    # window-local interval (padded by replay_span_pad_s).
                    try:
                        aligned_replay = align_words(out_path, replay_words_full)
                        localize_source = "align_words"
                    except SpanSurgeryError:
                        aligned_replay = []
                        localize_source = "alignment-failed"
                    localize_interval = (
                        flagged_local_start - replay_cfg.span_pad_s,
                        flagged_local_end + replay_cfg.span_pad_s,
                    )
                    localized_words = _localize_replay_words(aligned_replay, localize_interval)
                    if not localized_words:
                        reject_reason = "no-overlap-words"
                    else:
                        localized_text = " ".join(localized_words)
                        if normalize_term(localized_text) == flagged_normalized:
                            reject_reason = "replay-text-unchanged"
                        elif _reference_echo_reject(localized_text, reference_text):
                            # Guard 2 (D7D fix, module docstring's ACCEPT
                            # section): measured 14/115 replay outputs were
                            # ONLY the delivered reference string, some
                            # accepted and spliced -- reject before ever
                            # reaching the length-ratio/splice checks below.
                            reject_reason = "reference-echo"
                        elif len(localized_words) > replay_cfg.len_ratio_max * max(
                            1, len(flagged_words)
                        ):
                            reject_reason = "length-ratio-exceeded"
                        elif (
                            _unsupported_reference_word(
                                localized_words, reference_text, flagged_words
                            )
                            is not None
                        ):
                            # Guard 3 (D7D fix, module docstring's ACCEPT
                            # section): a delivered-reference word with no
                            # fuzzy support in the flagged span itself never
                            # splices, however well everything else checks
                            # out.
                            reject_reason = "splice-unsupported-reference"
                        else:
                            accepted = True

                decisions.append(
                    (start_idx, end_idx, accepted, localized_words if accepted else None)
                )

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
                    "replay_localized_words": list(localized_words),
                    "replay_localized_word_count": len(localized_words),
                    "replay_localize_source": localize_source,
                    "replay_flag_source": replay_cfg.flag_source,
                    "replay_flag_matched_candidate": band_flag.candidate if band_flag else None,
                    "replay_flag_matched_form": band_flag.matched_form if band_flag else None,
                    "replay_flag_distance": band_flag.distance if band_flag else None,
                    "replay_prompt_rendered_sha256": rendered_instruction_sha256,
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
        # DEFECT 2 fix (module docstring's SKIP note): a post-hoc count over
        # the already-written per-span records, never a separately
        # incremented counter -- one source of truth for "how many flagged
        # spans this sample never bothered the model for."
        no_candidate_skip_count = sum(
            1 for record_ in replay_window_records if record_["replay_reject_reason"] == "no-candidates"
        )
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
                "replay_no_candidate_skip_count": no_candidate_skip_count,
                # D7/D7B chain-defect fix (module docstring's FLAG SOURCES
                # section): the one legitimate empty-pool reason
                # (`_pack_terms`'s "empty-candidates-file" note) the
                # fail-closed guard above deliberately does NOT raise on --
                # recorded here (trace-visible) rather than silently
                # discarded; `None` for every other run, unchanged.
                "replay_pack_terms_empty_note": pack_terms_empty_note,
                # Guard 1 (D7D fix, module docstring): the SCORE-stage floor
                # actually in force for this run -- None outside roster-band
                # mode, where the key is never legal (ReplayLoopConfig.
                # from_values).
                "replay_flag_min_score": (
                    replay_cfg.flag_min_score if replay_cfg.flag_source == "roster-band" else None
                ),
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
