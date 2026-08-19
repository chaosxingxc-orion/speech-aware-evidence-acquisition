"""P-KEY flight orchestration -- REGISTERED probe SAEA-PROBE-pkey-303
(``bounded-discovery-probe``): ``docs/readiness/2026-08-18-pkey-preregistration-
REGISTERED.md``.

Question: is the supply benefit realized THROUGH perception (the roster
helps the core re-resolve the audio) or AFTER perception (a text-side
mechanism; the audio is only a retrieval key)? Five passes over the SAME
frozen 60 SLURP devel samples the consumed P-SLU probe already used
(``configs/probes/g0-binding/pslu-sample-devel-n60.json``, whose own
``split_identity_hash`` is
``fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5`` --
:func:`assert_split_identity_hash` pins this VERBATIM), in this REGISTERED
order:

- **T0**   (pass 0): audio -> a verbatim-transcription instruction, zero
  supply. Its own response is model output (deployment-legal), never gold.
- **AUD-NOSUP** (pass 1): audio, zero supply -- IDENTICAL shape to the
  consumed P-SLU A0 arm (``rails.adapters.slurp.SlurpAdapter.assemble_prompt``
  with ``supply=None``, reused unmodified).
- **AUD-SUP** (pass 2): audio, the A3-form 100-entry legal roster --
  IDENTICAL shape to the consumed P-SLU A3 arm
  (``rails.probes.pslu_flight.pslu_supply_packet("A3", scenario=None,
  rosters=...)``, reused unmodified: the SAME roster table, the SAME
  rendering, never a re-derivation). Carries 3 seeded silence-swap extra
  requests (module docstring continued below).
- **TXT-NOSUP** (pass 3): T0's OWN transcript text in place of audio, zero
  supply -- audio-free.
- **TXT-SUP** (pass 4): T0's OWN transcript text, the SAME A3-form roster --
  audio-free.

Hard ordering dependency (registered, section 3: "T0's transcripts are model
output ... each is hash-recorded and reused byte-identically in passes
3-4"): :func:`assemble_txt_messages` REFUSES (``PKeyFlightError``) unless
its caller-supplied ``transcript_registry`` already carries that sample's
own T0 record -- passes 3-4 structurally cannot build a prompt ahead of
pass 0. :func:`run_pkey_flight` runs pass 0 to completion (all 60 samples)
before pass 3/4 ever call :func:`assemble_txt_messages`, and
:func:`validate_pkey_flight_summary` (run automatically at the end of
:func:`run_pkey_flight`, and independently callable against an
already-assembled summary) INDEPENDENTLY re-derives -- never trusts a
blindly-embedded field -- each TXT-* row's OWN rendered transcript text
straight out of that row's OWN prompt content, sha256-hashes it, and
cross-checks it against that SAME summary's own T0 row for the same sample
id: any divergence refuses loud.

TXT arms are audio-free by construction: :func:`assemble_txt_messages`
never appends an ``input_audio`` content part (contrast
``rails.adapters.slurp.SlurpAdapter.assemble_prompt``, which always does).
The transcript is rendered into a single PINNED template,
:data:`TXT_TRANSCRIPT_TEMPLATE` -- frozen here AND in
``configs/probes/g0-binding/pkey-flight.json`` (``txt_template`` +
``txt_template_sha256``), checked byte-for-byte against each other by
:func:`assert_pinned_text_matches_config` (mirrors this study's own
"config and code must never silently diverge" discipline,
:func:`assert_never_calls_ontology_miner`'s own pattern).

Gold text NEVER enters any prompt path here: T0's own transcript (model
output) is the only text a TXT arm ever renders; no function in this module
accepts a gold/reference-text parameter of any kind (a structural fact this
mission's own test suite checks via ``inspect.signature``). The SCORING-side
T0-vs-gold WER descriptive (registered section 4) is computed entirely
downstream, in ``analysis.pkey_read``, from a raw governed-metadata read
this module never performs.

Silence-swap (registered section 4/5): 3 seeded AUD-SUP samples fire one
EXTRA request each with the audio content part's ``media_relpath`` swapped
for a silent slice -- reuses ``rails.probes.pslu_flight._swap_audio_media_relpath``
verbatim (never a re-implementation), exactly like the parent P-SLU flight's
own A1p silence-swap. Registration/generation live in
``rails.silence_swap`` + ``FrozenCoreClient.register_slice``, same as the
parent; this module only consumes the resulting ``sample_id ->
already-registered media_relpath`` mapping.

Never calls the ceiling-tier ontology miner (``data.slurp.load_slurp_ontology``):
this module's own AST guard (:func:`_assert_this_module_never_calls_ontology_miner`)
reuses ``rails.probes.pslu_flight._source_references_ontology_miner`` verbatim,
checked at import time and again at the top of :func:`run_pkey_flight` --
this probe's rosters come ONLY from ``configs/probes/g0-binding/
pslu-rosters-train-only.json`` via the SAME frozen
``rails.probes.pslu_flight.load_pslu_rosters``/``pslu_supply_packet``.

2026-08-19 amendment (docs/readiness/2026-08-18-pkey-preregistration-
REGISTERED.md section 7) machinery, two pieces:

1. TXT-NOSUP/TXT-SUP now send every request via
   ``core_client.complete(..., text_only_sample_id=sample.sample_id)`` --
   the real-client text-mode capability
   (``rails.core_client.FrozenCoreClient.complete``) that repairs the
   attempt-1 abort's own root cause (a text-only message was refused by the
   AUDIO invariant, because the client layer was never relaxed for
   registered text-only arms).
2. A SIXTH pass, the seeded 35-sample TXT duplicate sub-block
   (:data:`TXT_DUPLICATE_ARM` == :data:`TXT_NOSUP_ARM`,
   :data:`EXPECTED_TXT_DUPLICATE_COUNT` == 35): :func:`run_pkey_flight`'s
   own ``txt_duplicate_sample_ids`` parameter names which pass-3 samples get
   re-sent BYTE-IDENTICALLY (SAME construction, SAME supply=None) as an
   extra row, flagged ``PKeyArmResult.txt_duplicate=True`` and validated by
   :func:`validate_pkey_flight_summary` against
   :func:`txt_duplicate_content_matches` -- fail-closed if a resend ever
   diverges from its own pass-3 original.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from ..adapters.slurp import _INSTRUCTION as _SLU_INSTRUCTION
from ..adapters.slurp import SlurpAdapter, SlurpSample
from ..consumption import ConsumptionTrace
from ..supply import SupplyPacket
from .pslu_flight import (
    PsluRosters,
    _source_references_ontology_miner,
    _swap_audio_media_relpath,
    assert_never_calls_ontology_miner,
    pslu_supply_packet,
)

T0_ARM = "T0"
AUD_NOSUP_ARM = "AUD-NOSUP"
AUD_SUP_ARM = "AUD-SUP"
TXT_NOSUP_ARM = "TXT-NOSUP"
TXT_SUP_ARM = "TXT-SUP"

# REGISTERED order (section 3's own pass table) -- also the order
# run_pkey_flight submits requests in.
PKEY_ARMS: tuple[str, ...] = (T0_ARM, AUD_NOSUP_ARM, AUD_SUP_ARM, TXT_NOSUP_ARM, TXT_SUP_ARM)
# The four arms the primary SLU-F1 / Delta_AUD / Delta_TXT / INTERACTION
# metrics are computed over (registered section 4) -- T0 is EXCLUDED: it
# answers a verbatim-transcription instruction, never the SLU JSON schema,
# so it is not itself an SLU-F1-scored arm (its own quality is the
# SEPARATE, scoring-side-only T0-vs-gold WER descriptive).
PKEY_SLU_ARMS: tuple[str, ...] = (AUD_NOSUP_ARM, AUD_SUP_ARM, TXT_NOSUP_ARM, TXT_SUP_ARM)
TXT_ARMS: tuple[str, ...] = (TXT_NOSUP_ARM, TXT_SUP_ARM)

SILENCE_SWAP_ARM = AUD_SUP_ARM
EXPECTED_SILENCE_SWAP_COUNT = 3

# 2026-08-19 amendment (docs/readiness/2026-08-18-pkey-preregistration-
# REGISTERED.md section 7 item 4): a seeded 35-sample sub-block of pass 3
# (TXT-NOSUP), re-sent BYTE-IDENTICALLY in the SAME session as a sixth pass
# -- ALWAYS TXT-NOSUP (never TXT-SUP; the amendment names pass 3 only).
TXT_DUPLICATE_ARM = TXT_NOSUP_ARM
EXPECTED_TXT_DUPLICATE_COUNT = 35

# docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md's own opening
# line: "the SAME frozen 60 SLURP devel samples (seed 20260807) ... identical
# to the consumed P-SLU flights" -- configs/probes/g0-binding/
# pslu-sample-devel-n60.json's own split_identity_hash, pinned VERBATIM.
EXPECTED_SPLIT_IDENTITY_HASH = "fc9de436eba5aba120ecf07ee112765cd4ac0609150e0aaf36f4d44c9c5b5ee5"


class PKeyFlightError(RuntimeError):
    """A P-KEY flight input is malformed, a hard ordering/legality/identity
    invariant is violated, or the ontology-miner import guard tripped."""


# ---------------------------------------------------------------------------
# The ontology-miner call guard -- reuses the parent's own pure checker
# against THIS module's own source (that checker's default source resolves
# to pslu_flight.py's __file__, not this file's -- see
# rails.probes.pslu_s2_flight._assert_this_module_never_calls_ontology_miner's
# own docstring for why the parent's default guard alone cannot scan a
# different module).
# ---------------------------------------------------------------------------


def _assert_this_module_never_calls_ontology_miner(source: str | None = None) -> None:
    from pathlib import Path

    text = source if source is not None else Path(__file__).read_text(encoding="utf-8")
    if _source_references_ontology_miner(text):
        raise PKeyFlightError(
            "rails.probes.pkey_flight source references load_slurp_ontology; this flight is "
            "REGISTERED to consume rosters ONLY from configs/probes/g0-binding/"
            "pslu-rosters-train-only.json (rails.probes.pslu_flight.load_pslu_rosters)"
        )


def assert_split_identity_hash(split_identity_hash: str) -> None:
    """Fail-closed (module docstring): ``split_identity_hash`` must equal
    :data:`EXPECTED_SPLIT_IDENTITY_HASH` VERBATIM -- this probe reuses the
    SAME frozen 60-sample manifest the consumed P-SLU flight used, never a
    fresh draw."""

    if split_identity_hash != EXPECTED_SPLIT_IDENTITY_HASH:
        raise PKeyFlightError(
            f"split_identity_hash {split_identity_hash!r} does not match the REGISTERED P-KEY "
            f"sample manifest's own hash {EXPECTED_SPLIT_IDENTITY_HASH!r} "
            "(configs/probes/g0-binding/pslu-sample-devel-n60.json, reused byte-identically for "
            "this probe) -- fail-closed"
        )


# ---------------------------------------------------------------------------
# Pinned instruction/template text (module docstring: config/code parity).
# ---------------------------------------------------------------------------

T0_INSTRUCTION = (
    "You are given spoken audio expressing one command to a voice assistant. "
    "Transcribe EXACTLY what was said, verbatim -- no paraphrasing, no "
    "correction, no punctuation or words you did not hear, no commentary. "
    "Respond with ONLY the transcript text, nothing else."
)

TXT_TRANSCRIPT_TEMPLATE = "The user said: {transcript}"

if not TXT_TRANSCRIPT_TEMPLATE.endswith("{transcript}"):
    raise PKeyFlightError(
        "TXT_TRANSCRIPT_TEMPLATE must end with the literal '{transcript}' placeholder so a "
        "rendered block can be losslessly reversed by prefix-stripping "
        "(extract_txt_transcript_from_rendered's own contract)"
    )
# Derived, not hand-duplicated, from TXT_TRANSCRIPT_TEMPLATE itself -- a
# second hand-typed literal could silently drift from the template it is
# supposed to invert.
_TXT_TRANSCRIPT_PREFIX = TXT_TRANSCRIPT_TEMPLATE[: -len("{transcript}")]


def t0_instruction_sha256() -> str:
    return hashlib.sha256(T0_INSTRUCTION.encode("utf-8")).hexdigest()


def txt_template_sha256() -> str:
    return hashlib.sha256(TXT_TRANSCRIPT_TEMPLATE.encode("utf-8")).hexdigest()


def assert_pinned_text_matches_config(document: Mapping[str, object]) -> None:
    """Fail-closed config/code parity guard (module docstring): the
    REGISTERED flight config's own ``t0_instruction``/``txt_template`` text
    and their ``_sha256`` companions must agree BYTE-FOR-BYTE with this
    module's own frozen constants -- a config edited without a matching
    code change (or vice versa) refuses immediately, never silently
    diverges."""

    if document.get("t0_instruction") != T0_INSTRUCTION:
        raise PKeyFlightError(
            "pkey-flight.json t0_instruction does not match rails.probes.pkey_flight.T0_INSTRUCTION "
            "verbatim"
        )
    if document.get("t0_instruction_sha256") != t0_instruction_sha256():
        raise PKeyFlightError("pkey-flight.json t0_instruction_sha256 does not match sha256(T0_INSTRUCTION)")
    if document.get("txt_template") != TXT_TRANSCRIPT_TEMPLATE:
        raise PKeyFlightError(
            "pkey-flight.json txt_template does not match rails.probes.pkey_flight."
            "TXT_TRANSCRIPT_TEMPLATE verbatim"
        )
    if document.get("txt_template_sha256") != txt_template_sha256():
        raise PKeyFlightError("pkey-flight.json txt_template_sha256 does not match sha256(TXT_TRANSCRIPT_TEMPLATE)")


def render_txt_transcript_block(transcript: str) -> str:
    return TXT_TRANSCRIPT_TEMPLATE.format(transcript=transcript)


def extract_txt_transcript_from_rendered(rendered: str) -> str:
    """Inverse of :func:`render_txt_transcript_block` -- fail-closed if
    ``rendered`` does not start with the pinned template's own fixed
    prefix (a harness/template-drift defect, never silently tolerated)."""

    if not rendered.startswith(_TXT_TRANSCRIPT_PREFIX):
        raise PKeyFlightError(
            f"rendered TXT transcript block does not start with the pinned template prefix "
            f"{_TXT_TRANSCRIPT_PREFIX!r}: {rendered!r}"
        )
    return rendered[len(_TXT_TRANSCRIPT_PREFIX) :]


# ---------------------------------------------------------------------------
# Message-content helpers (shared with analysis.pkey_read -- reused, never
# re-implemented there).
# ---------------------------------------------------------------------------


def content_text_parts(messages: Sequence[Mapping[str, object]]) -> tuple[str, ...]:
    """Every ``type == "text"`` content part's own text, in order, off
    ``messages``'s own user turn -- ``()`` for a malformed/short shape
    (reported as a harness defect by a caller, never raised here)."""

    if len(messages) < 2:
        return ()
    content = messages[1].get("content")
    if not isinstance(content, Sequence):
        return ()
    return tuple(
        str(part.get("text", "")) for part in content if isinstance(part, Mapping) and part.get("type") == "text"
    )


def content_has_audio(messages: Sequence[Mapping[str, object]]) -> bool:
    if len(messages) < 2:
        return False
    content = messages[1].get("content")
    if not isinstance(content, Sequence):
        return False
    return any(isinstance(part, Mapping) and part.get("type") == "input_audio" for part in content)


def txt_duplicate_content_matches(
    candidate: Sequence[Mapping[str, object]], original: Sequence[Mapping[str, object]]
) -> bool:
    """Byte-identity check (2026-08-19 amendment item 4): ``True`` iff
    ``candidate`` (a duplicate-block row's own prompt) and ``original`` (that
    SAME sample's own pass-3 TXT-NOSUP row) are BOTH audio-free and carry the
    IDENTICAL text content parts, in order -- never merely "close enough".
    Reused by BOTH this module's own :func:`validate_pkey_flight_summary` and
    ``analysis.pkey_read``'s read-side VOID clause (never two independently
    drifting implementations of the SAME byte-identity bar)."""

    return (
        content_has_audio(candidate) is False
        and content_has_audio(original) is False
        and content_text_parts(candidate) == content_text_parts(original)
    )


# ---------------------------------------------------------------------------
# T0 transcript registry.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptRecord:
    """One sample's T0 transcript -- ``text`` is pass 0's OWN response
    (model output, deployment-legal, never gold); ``sha256`` is recorded at
    the SAME instant so passes 3-4's own byte-identity checks never have to
    re-derive it from a possibly-mutated string later."""

    sample_id: str
    text: str
    sha256: str

    def as_json(self) -> dict[str, object]:
        return {"sample_id": self.sample_id, "text": self.text, "sha256": self.sha256}


def build_transcript_record(sample_id: str, text: str) -> TranscriptRecord:
    return TranscriptRecord(sample_id=sample_id, text=text, sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())


def transcript_registry_as_json(registry: Mapping[str, TranscriptRecord]) -> dict[str, dict[str, object]]:
    """The per-sample transcript registry shape a real flight launcher
    writes into its own attempt dir (module docstring: "a per-sample
    transcript registry written into the attempt dir") -- never written by
    this engineering-only module itself (no I/O anywhere in this file)."""

    return {sample_id: record.as_json() for sample_id, record in registry.items()}


# ---------------------------------------------------------------------------
# Prompt assembly.
# ---------------------------------------------------------------------------


def assemble_t0_messages(sample: SlurpSample) -> tuple[Mapping[str, object], ...]:
    """Pass 0: audio only, the verbatim-transcription instruction, zero
    supply -- never the SLU instruction, never a roster."""

    return (
        {"role": "system", "content": T0_INSTRUCTION},
        {"role": "user", "content": [{"type": "input_audio", "media_relpath": sample.media_relpath}]},
    )


def assemble_txt_messages(
    sample: SlurpSample,
    supply: SupplyPacket | None,
    transcript_registry: Mapping[str, TranscriptRecord],
) -> tuple[Mapping[str, object], ...]:
    """Passes 3-4: the SLU instruction (SAME as ``SlurpAdapter.assemble_prompt``'s
    own ``_INSTRUCTION``, reused verbatim) plus ``supply`` (when not
    ``None``) plus T0's OWN transcript rendered through the pinned template
    -- NEVER an ``input_audio`` content part (module docstring: TXT arms are
    audio-free by construction). Refuses (hard ordering dependency) unless
    ``transcript_registry`` already carries ``sample.sample_id``'s own T0
    record; no parameter here ever names gold/reference text."""

    record = transcript_registry.get(sample.sample_id)
    if record is None:
        raise PKeyFlightError(
            f"no T0 transcript registered for sample {sample.sample_id!r} -- TXT arms require pass "
            "0 (T0) to complete and hash-record this sample's own transcript FIRST (registered hard "
            "ordering dependency, docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md "
            "section 3)"
        )
    content: list[Mapping[str, object]] = []
    if supply is not None:
        content.append({"type": "text", "text": supply.prompt_block})
    content.append({"type": "text", "text": render_txt_transcript_block(record.text)})
    return (
        {"role": "system", "content": _SLU_INSTRUCTION},
        {"role": "user", "content": content},
    )


# ---------------------------------------------------------------------------
# Flight orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PKeyArmResult:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: ConsumptionTrace
    silence_swapped: bool = False
    # Only populated on a TXT-NOSUP/TXT-SUP row: the sha256 this row's own
    # T0 record carried AT ASSEMBLY TIME (validate_pkey_flight_summary
    # independently re-derives the SAME value from the row's own rendered
    # prompt text -- this field is never trusted blindly).
    transcript_sha256_used: str | None = None
    # 2026-08-19 amendment item 4: True on exactly the sixth-pass duplicate
    # sub-block rows (always arm==TXT_NOSUP_ARM, a re-send of that SAME
    # sample's own pass-3 row) -- kept in a separate bucket from the ordinary
    # pass-3 rows by both validate_pkey_flight_summary and analysis.pkey_read
    # (mirrors how silence_swapped already separates AUD-SUP's own extra
    # rows), never merged into the primary per-sample aggregate.
    txt_duplicate: bool = False


@dataclass(frozen=True)
class PKeyFlightSummary:
    results: tuple[PKeyArmResult, ...]
    transcript_registry: Mapping[str, TranscriptRecord]


def validate_pkey_flight_summary(
    summary: PKeyFlightSummary,
    *,
    expected_sample_ids: Sequence[str],
    expected_silence_swap_sample_ids: Sequence[str] = (),
    expected_txt_duplicate_sample_ids: Sequence[str] = (),
) -> None:
    """Fail-closed structural checks (module docstring / mission
    instruction): every arm in :data:`PKEY_ARMS` carries EXACTLY one row
    per id in ``expected_sample_ids`` (60/60 per pass), no duplicate
    sample_id rows, EXACTLY one silence-swap row per id in
    ``expected_silence_swap_sample_ids`` (all on :data:`SILENCE_SWAP_ARM`),
    EXACTLY one txt-duplicate row per id in
    ``expected_txt_duplicate_sample_ids`` (all on :data:`TXT_DUPLICATE_ARM`,
    each BYTE-IDENTICAL -- :func:`txt_duplicate_content_matches` -- to that
    SAME sample's own pass-3 row: 2026-08-19 amendment item 4's own
    byte-identity bar), every TXT-* row is audio-free, and every TXT-* row's
    OWN rendered transcript text sha256-matches this SAME summary's own T0
    row for the same sample id (the registered hard ordering dependency's
    own byte-identity bar). Called automatically at the end of
    :func:`run_pkey_flight`; independently callable against an
    already-assembled summary (e.g. by a test fixture)."""

    expected = tuple(expected_sample_ids)
    expected_set = set(expected)
    if len(expected) != len(expected_set):
        raise PKeyFlightError("expected_sample_ids carries a duplicate")
    expected_silence = tuple(expected_silence_swap_sample_ids)
    expected_silence_set = set(expected_silence)
    if len(expected_silence) != len(expected_silence_set):
        raise PKeyFlightError("expected_silence_swap_sample_ids carries a duplicate")
    expected_txt_dup = tuple(expected_txt_duplicate_sample_ids)
    expected_txt_dup_set = set(expected_txt_dup)
    if len(expected_txt_dup) != len(expected_txt_dup_set):
        raise PKeyFlightError("expected_txt_duplicate_sample_ids carries a duplicate")

    by_arm: dict[str, list[PKeyArmResult]] = {arm: [] for arm in PKEY_ARMS}
    silence_rows: list[PKeyArmResult] = []
    txt_duplicate_rows: list[PKeyArmResult] = []
    for row in summary.results:
        if row.arm not in PKEY_ARMS:
            raise PKeyFlightError(f"unknown P-KEY arm {row.arm!r}")
        if row.silence_swapped:
            silence_rows.append(row)
        elif row.txt_duplicate:
            txt_duplicate_rows.append(row)
        else:
            by_arm[row.arm].append(row)

    for arm in PKEY_ARMS:
        rows = by_arm[arm]
        ids = [row.sample_id for row in rows]
        if len(ids) != len(set(ids)):
            raise PKeyFlightError(f"arm {arm}: duplicate sample_id row(s)")
        got = set(ids)
        if got != expected_set:
            missing = sorted(expected_set - got)
            extra = sorted(got - expected_set)
            raise PKeyFlightError(
                f"arm {arm}: sample id set does not match the expected {len(expected_set)}-sample "
                f"manifest (missing={missing[:5]}, extra={extra[:5]})"
            )

    silence_ids = [row.sample_id for row in silence_rows]
    if len(silence_ids) != len(set(silence_ids)):
        raise PKeyFlightError("duplicate silence-swap sample_id row(s)")
    got_silence = set(silence_ids)
    if got_silence != expected_silence_set:
        missing = sorted(expected_silence_set - got_silence)
        extra = sorted(got_silence - expected_silence_set)
        raise PKeyFlightError(
            f"silence-swap sample id set does not match the expected {len(expected_silence_set)}-sample "
            f"set (missing={missing[:5]}, extra={extra[:5]})"
        )
    for row in silence_rows:
        if row.arm != SILENCE_SWAP_ARM:
            raise PKeyFlightError(
                f"silence-swap row on sample {row.sample_id!r} is on arm {row.arm!r}, expected "
                f"{SILENCE_SWAP_ARM!r}"
            )

    # 2026-08-19 amendment item 4: the 35-call TXT duplicate sub-block --
    # structural id-set check plus the FAIL-CLOSED byte-identity check
    # against each sample's own pass-3 (TXT-NOSUP) row.
    txt_dup_ids = [row.sample_id for row in txt_duplicate_rows]
    if len(txt_dup_ids) != len(set(txt_dup_ids)):
        raise PKeyFlightError("duplicate txt-duplicate sample_id row(s)")
    got_txt_dup = set(txt_dup_ids)
    if got_txt_dup != expected_txt_dup_set:
        missing = sorted(expected_txt_dup_set - got_txt_dup)
        extra = sorted(got_txt_dup - expected_txt_dup_set)
        raise PKeyFlightError(
            f"txt-duplicate sample id set does not match the expected {len(expected_txt_dup_set)}-sample "
            f"set (missing={missing[:5]}, extra={extra[:5]})"
        )
    txt_nosup_by_sample = {row.sample_id: row for row in by_arm[TXT_DUPLICATE_ARM]}
    for row in txt_duplicate_rows:
        if row.arm != TXT_DUPLICATE_ARM:
            raise PKeyFlightError(
                f"txt-duplicate row on sample {row.sample_id!r} is on arm {row.arm!r}, expected "
                f"{TXT_DUPLICATE_ARM!r}"
            )
        original_row = txt_nosup_by_sample.get(row.sample_id)
        if original_row is None:
            raise PKeyFlightError(
                f"txt-duplicate row on sample {row.sample_id!r}: no original pass-3 "
                f"{TXT_DUPLICATE_ARM!r} row present in this summary to compare against"
            )
        if not txt_duplicate_content_matches(row.messages, original_row.messages):
            raise PKeyFlightError(
                f"txt-duplicate row on sample {row.sample_id!r}: this row's own prompt content does "
                "not byte-match its own pass-3 TXT-NOSUP original -- duplicate-block byte-identity "
                "violated (2026-08-19 amendment item 4)"
            )

    # Audio-free legality (module docstring) + transcript-reuse byte-identity
    # (the registered hard ordering dependency) -- both independently
    # RE-DERIVED from each TXT-* row's own prompt content, never from
    # transcript_sha256_used alone.
    t0_by_sample = {row.sample_id: row for row in by_arm[T0_ARM]}
    for arm in TXT_ARMS:
        for row in by_arm[arm]:
            if content_has_audio(row.messages):
                raise PKeyFlightError(
                    f"arm {arm} sample {row.sample_id!r}: TXT arm row carries an input_audio content "
                    "part -- TXT arms must be audio-free"
                )
            t0_row = t0_by_sample.get(row.sample_id)
            if t0_row is None:
                raise PKeyFlightError(
                    f"arm {arm} sample {row.sample_id!r}: no T0 row present in this summary to "
                    "reconstruct byte-identity against"
                )
            expected_sha256 = hashlib.sha256(t0_row.response_text.encode("utf-8")).hexdigest()
            texts = content_text_parts(row.messages)
            if not texts:
                raise PKeyFlightError(
                    f"arm {arm} sample {row.sample_id!r}: carries no text content part to extract a "
                    "transcript from"
                )
            actual_text = extract_txt_transcript_from_rendered(texts[-1])
            actual_sha256 = hashlib.sha256(actual_text.encode("utf-8")).hexdigest()
            if actual_sha256 != expected_sha256:
                raise PKeyFlightError(
                    f"arm {arm} sample {row.sample_id!r}: this row's own rendered transcript text "
                    f"(sha256={actual_sha256}) does not byte-match this SAME summary's own T0 "
                    f"response (sha256={expected_sha256}) for the same sample id -- transcript-reuse "
                    "byte-identity violated (registered hard ordering dependency)"
                )
            if row.transcript_sha256_used != expected_sha256:
                raise PKeyFlightError(
                    f"arm {arm} sample {row.sample_id!r}: its own recorded transcript_sha256_used "
                    f"({row.transcript_sha256_used!r}) disagrees with the T0 hash it should have been "
                    f"assembled from ({expected_sha256!r})"
                )


def run_pkey_flight(
    *,
    adapter: SlurpAdapter,
    core_client,
    samples: Sequence[SlurpSample],
    rosters: PsluRosters,
    split_identity_hash: str,
    decoding_params: Mapping[str, object] | None = None,
    silence_swap_media_relpaths: Mapping[str, str] = MappingProxyType({}),
    txt_duplicate_sample_ids: Sequence[str] = (),
) -> PKeyFlightSummary:
    """Execute the full five-pass P-KEY flight over ``samples`` (module
    docstring) plus one extra AUD-SUP request per entry in
    ``silence_swap_media_relpaths`` (``sample_id -> already-registered
    silent media_relpath`` -- ``rails.silence_swap`` +
    ``FrozenCoreClient.register_slice`` build that registration, exactly as
    the parent P-SLU flight's own ``run_pslu_flight`` documents) plus, as a
    SIXTH pass, one extra byte-identical re-send of pass 3 (TXT-NOSUP) per id
    in ``txt_duplicate_sample_ids`` (2026-08-19 amendment item 4: the seeded
    35-sample duplicate sub-block -- caller-supplied, exactly like
    ``silence_swap_media_relpaths``, since selection lives in the REGISTERED
    flight config, ``configs/probes/g0-binding/pkey-flight.json``'s own
    ``txt_duplicate`` block, never re-derived here).

    ``core_client`` is duck-typed against ``rails.core_client.CoreClient``
    (the SAME "no forced import" discipline ``run_pslu_flight``/
    ``run_pslu_s2_flight`` use); each duplicate-block request is sent via
    ``core_client.complete(..., text_only_sample_id=sample.sample_id)``,
    exactly like pass 3/4's own TXT-* requests (the real-client text-mode
    capability, ``rails.core_client.FrozenCoreClient.complete``).
    """

    assert_never_calls_ontology_miner()
    _assert_this_module_never_calls_ontology_miner()
    assert_split_identity_hash(split_identity_hash)
    if not samples:
        raise PKeyFlightError("run_pkey_flight requires at least one sample")
    sample_ids_list = [sample.sample_id for sample in samples]
    if len(sample_ids_list) != len(set(sample_ids_list)):
        raise PKeyFlightError("duplicate sample_id in samples")
    sample_id_set = set(sample_ids_list)
    unknown_silence_ids = set(silence_swap_media_relpaths) - sample_id_set
    if unknown_silence_ids:
        raise PKeyFlightError(
            f"silence_swap_media_relpaths names sample ids outside this flight's own samples: "
            f"{sorted(unknown_silence_ids)}"
        )
    txt_duplicate_id_list = list(txt_duplicate_sample_ids)
    if len(txt_duplicate_id_list) != len(set(txt_duplicate_id_list)):
        raise PKeyFlightError("txt_duplicate_sample_ids carries a duplicate")
    unknown_txt_duplicate_ids = set(txt_duplicate_id_list) - sample_id_set
    if unknown_txt_duplicate_ids:
        raise PKeyFlightError(
            f"txt_duplicate_sample_ids names sample ids outside this flight's own samples: "
            f"{sorted(unknown_txt_duplicate_ids)}"
        )

    # The SAME frozen A3 roster the consumed P-SLU A3 arm used -- built ONCE
    # via the frozen pslu_supply_packet, reused byte-identically by both
    # AUD-SUP and TXT-SUP below (module docstring).
    a3_supply = pslu_supply_packet("A3", scenario=None, rosters=rosters)

    results: list[PKeyArmResult] = []
    transcript_registry: dict[str, TranscriptRecord] = {}

    # Pass 0: T0 -- verbatim transcription, audio only, zero supply. MUST
    # complete (all samples) before any TXT-* prompt is built below.
    for sample in samples:
        messages = assemble_t0_messages(sample)
        response_text = core_client.complete(messages, decoding_params=decoding_params)
        record = build_transcript_record(sample.sample_id, response_text)
        transcript_registry[sample.sample_id] = record
        consumption = adapter.extract_consumption(sample, None, response_text)
        results.append(
            PKeyArmResult(
                arm=T0_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics={},
                consumption=consumption,
            )
        )

    # Pass 1: AUD-NOSUP -- audio, zero supply (IDENTICAL construction to the
    # consumed P-SLU A0 arm).
    for sample in samples:
        messages = adapter.assemble_prompt(sample, None)
        response_text = core_client.complete(messages, decoding_params=decoding_params)
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, None, response_text)
        results.append(
            PKeyArmResult(
                arm=AUD_NOSUP_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
            )
        )

    # Pass 2: AUD-SUP -- audio, A3-form roster (IDENTICAL construction to the
    # consumed P-SLU A3 arm) -- plus silence-swap.
    for sample in samples:
        messages = adapter.assemble_prompt(sample, a3_supply)
        response_text = core_client.complete(messages, decoding_params=decoding_params)
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, a3_supply, response_text)
        results.append(
            PKeyArmResult(
                arm=AUD_SUP_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
            )
        )
        silence_media_relpath = silence_swap_media_relpaths.get(sample.sample_id)
        if silence_media_relpath is not None:
            silence_messages = _swap_audio_media_relpath(messages, silence_media_relpath)
            silence_response_text = core_client.complete(silence_messages, decoding_params=decoding_params)
            silence_metrics = adapter.score(sample, silence_response_text)
            silence_consumption = adapter.extract_consumption(sample, a3_supply, silence_response_text)
            results.append(
                PKeyArmResult(
                    arm=AUD_SUP_ARM,
                    sample_id=sample.sample_id,
                    messages=silence_messages,
                    response_text=silence_response_text,
                    metrics=silence_metrics,
                    consumption=silence_consumption,
                    silence_swapped=True,
                )
            )

    # Ordering dependency (module docstring): transcript_registry is now
    # fully populated from pass 0's OWN completed responses --
    # assemble_txt_messages below refuses if any entry were somehow missing.

    # Pass 3: TXT-NOSUP -- T0's transcript, zero supply, audio-free. Real-
    # client text-mode: text_only_sample_id names the sample a text-only
    # message carries no media_relpath to reverse-look-up
    # (rails.core_client.FrozenCoreClient.complete's own opt-in gate).
    for sample in samples:
        record = transcript_registry[sample.sample_id]
        messages = assemble_txt_messages(sample, None, transcript_registry)
        response_text = core_client.complete(
            messages, decoding_params=decoding_params, text_only_sample_id=sample.sample_id
        )
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, None, response_text)
        results.append(
            PKeyArmResult(
                arm=TXT_NOSUP_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
                transcript_sha256_used=record.sha256,
            )
        )

    # Pass 4: TXT-SUP -- T0's transcript, A3-form roster, audio-free.
    for sample in samples:
        record = transcript_registry[sample.sample_id]
        messages = assemble_txt_messages(sample, a3_supply, transcript_registry)
        response_text = core_client.complete(
            messages, decoding_params=decoding_params, text_only_sample_id=sample.sample_id
        )
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, a3_supply, response_text)
        results.append(
            PKeyArmResult(
                arm=TXT_SUP_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
                transcript_sha256_used=record.sha256,
            )
        )

    # Pass 6 (2026-08-19 amendment item 4): the seeded 35-sample TXT
    # duplicate sub-block -- a BYTE-IDENTICAL re-send (SAME construction:
    # assemble_txt_messages(sample, None, transcript_registry), supply=None,
    # exactly pass 3's own call) of a sub-block of pass 3, in the SAME
    # session, for this axis's own measured duplicate floor.
    txt_duplicate_id_set = set(txt_duplicate_id_list)
    for sample in samples:
        if sample.sample_id not in txt_duplicate_id_set:
            continue
        record = transcript_registry[sample.sample_id]
        messages = assemble_txt_messages(sample, None, transcript_registry)
        response_text = core_client.complete(
            messages, decoding_params=decoding_params, text_only_sample_id=sample.sample_id
        )
        metrics = adapter.score(sample, response_text)
        consumption = adapter.extract_consumption(sample, None, response_text)
        results.append(
            PKeyArmResult(
                arm=TXT_DUPLICATE_ARM,
                sample_id=sample.sample_id,
                messages=tuple(messages),
                response_text=response_text,
                metrics=metrics,
                consumption=consumption,
                transcript_sha256_used=record.sha256,
                txt_duplicate=True,
            )
        )

    summary = PKeyFlightSummary(
        results=tuple(results), transcript_registry=MappingProxyType(dict(transcript_registry))
    )
    validate_pkey_flight_summary(
        summary,
        expected_sample_ids=tuple(sample_ids_list),
        expected_silence_swap_sample_ids=tuple(silence_swap_media_relpaths.keys()),
        expected_txt_duplicate_sample_ids=tuple(txt_duplicate_id_list),
    )
    return summary


__all__ = [
    "AUD_NOSUP_ARM",
    "AUD_SUP_ARM",
    "EXPECTED_SILENCE_SWAP_COUNT",
    "EXPECTED_SPLIT_IDENTITY_HASH",
    "EXPECTED_TXT_DUPLICATE_COUNT",
    "PKEY_ARMS",
    "PKEY_SLU_ARMS",
    "SILENCE_SWAP_ARM",
    "T0_ARM",
    "T0_INSTRUCTION",
    "TXT_ARMS",
    "TXT_DUPLICATE_ARM",
    "TXT_NOSUP_ARM",
    "TXT_SUP_ARM",
    "TXT_TRANSCRIPT_TEMPLATE",
    "PKeyArmResult",
    "PKeyFlightError",
    "PKeyFlightSummary",
    "TranscriptRecord",
    "assemble_t0_messages",
    "assemble_txt_messages",
    "assert_pinned_text_matches_config",
    "assert_split_identity_hash",
    "build_transcript_record",
    "content_has_audio",
    "content_text_parts",
    "extract_txt_transcript_from_rendered",
    "render_txt_transcript_block",
    "run_pkey_flight",
    "t0_instruction_sha256",
    "transcript_registry_as_json",
    "txt_duplicate_content_matches",
    "txt_template_sha256",
    "validate_pkey_flight_summary",
]


# Executed at import time (mirrors rails.probes.pslu_flight's own
# module-bottom self-check, and rails.probes.pslu_s2_flight's own dual
# parent+self check): fails LOUD the moment this module is loaded if a
# future edit adds a live reference to the forbidden ontology miner.
assert_never_calls_ontology_miner()
_assert_this_module_never_calls_ontology_miner()
