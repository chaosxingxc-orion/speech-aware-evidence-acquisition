"""P-KEY offline read suite (pinned, pre-registered, SAEA-PROBE-pkey-303).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` / ``flight-receipt.json``
(``rails.probes.pkey_flight.run_pkey_flight``'s own row shape) through the
SAME frozen official-metric scorer every other consumer of this carrier uses
(``reproduction.slurp_scoring.score_slu`` / ``parse_slu_response``).

Sources of truth this module implements EXACTLY (never re-derives on its own
authority): ``docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md``
sections 3 (arms) and 4 (metrics/verdicts); ``configs/probes/g0-binding/
pslu-sample-devel-n60.json`` / ``pslu-rosters-train-only.json`` (the SAME
frozen sample set and roster table the consumed P-SLU probe used, loaded via
``rails.probes.pslu_flight``'s own loaders); ``configs/probes/g0-binding/
pkey-flight.json``'s own arm/metric lines.

REUSE, NOT RE-DERIVATION (mirrors ``analysis.pslu_s2_read``'s own explicit
discipline for the SAME reason -- a Stage-2-style follow-up instrument reuses
its parent's already-approved scoring primitives, never a second, drifting
implementation): ``analysis.pslu_read.RowAnalysis`` / ``ArmAggregate`` /
``build_arm_aggregate`` / ``arm_copy_rate`` / ``count_induced_substitutions``
/ ``_roster_values_for_packet`` / ``_recheck_row`` / ``RecheckMismatch`` /
``ClauseResult`` / ``_void_clause_recheck`` / ``_void_clause_harness_defect``
/ ``_void_clause_silence_swap`` / ``_parsed_answer_signature`` /
``SilenceSwapComparison`` / ``load_gold_by_sample_id`` /
``RUNTIME_PROHIBITED_NOTE`` -- ALL reused directly (duck-typed against
``PKeyOutputRow`` where the parent's own helpers were written against
``OutputRow``: both expose the same ``arm``/``sample_id``/``messages``/
``metrics``/``consumption`` shape). ``rails.probes.pslu_flight.
load_pslu_rosters`` / ``load_pslu_sample_manifest`` / ``pslu_supply_packet``
(the SAME frozen roster-selection function the flight itself calls, keyed
``arm="A3"`` -- never a second reconstruction). ``rails.probes.pkey_flight``'s
own arm constants, ``content_text_parts``/``content_has_audio`` (the SAME
message-shape primitives the flight machinery uses to build/validate a
row), and ``extract_txt_transcript_from_rendered`` (the SAME inverse-template
function, reused here to independently re-derive what transcript a TXT-*
row's own prompt actually rendered -- never trusting an embedded field).

Gold-text scope (RUNTIME_PROHIBITED, module-wide): the T0-vs-gold WER
descriptive is the FIRST legitimate scoring-side need for SLURP's raw
sentence text, which ``data.slurp.SlurpRecord`` deliberately excludes (its
own module docstring: "not needed by either the five TaskAdapter methods or
by scoring"). :func:`load_gold_sentence_by_sample_id` therefore reads the
RAW governed ``devel.jsonl`` directly (``data.slurp._governed_roots`` +
``data.slurp._read_jsonl``, private cross-module reuse already precedented
in this repository -- e.g. this module's own reuse of
``reproduction.slurp_scoring._word_distance`` below), bridged to
``sample_id`` via :func:`~analysis.pslu_read.load_gold_by_sample_id`'s own
``SlurpRecord.utterance_id`` (== ``str(slurp_id)``) rather than
reconstructing the ``sample_id`` string format by hand a second time. This
gold text is used EXCLUSIVELY inside this module's own scoring-side WER
computation and its own gold-leak legality scan; it is never passed to, or
derivable from, anything ``rails.probes.pkey_flight`` writes into a prompt
(:func:`find_gold_leak_violations` is the machine-checked proof of that
boundary, and ``tests/unit/test_pkey_read.py`` asserts it against both a
clean fixture and a deliberately-leaked one).

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried -- the
registration text is genuinely underspecified on these exact points, each a
documented, reviewable choice):

1. "samples converting under AUD-SUP but not TXT-SUP" (registration section
   4): a per-sample binary "command-level success" indicator -- exact
   ``scenario_action`` match AND an exact entity slot set (``slot_f1_exact``
   with zero FP and zero FN) -- transitioning from NOT fully correct under
   the NOSUP sibling arm to fully correct under the SUP arm. Reuses the SAME
   ``score_slu`` ingredients every other metric in this suite already
   computes (parent primitives verbatim); see :func:`_sample_fully_correct`.
2. The perception gap (registration section 4) is read as
   ``TXT-NOSUP.slu_f1 - AUD-NOSUP.slu_f1`` (literal table order, "TXT-NOSUP
   vs AUD-NOSUP") -- POSITIVE means the core's own committed T0 transcript,
   read back as plain text with zero supply, scores HIGHER than hearing the
   same audio directly; purely descriptive, carries no clause. See
   :func:`perception_gap`.
3. The P-PHON NEAR-MISS cross-reference (registration section 4) is a SOFT,
   read-only, tolerate-absence lookup against an ALREADY-WRITTEN verdict
   JSON at a caller-supplied path -- this module never imports
   ``analysis.pphon_decomp`` or any of its code, and every failure mode
   (path not given, file missing, unparseable, unexpected shape) degrades
   silently to an empty mapping. See :func:`load_pphon_classes`.
4. VOID gains two clauses beyond the parent read's own three
   (recheck/harness/silence-swap): gold-leak (:func:`find_gold_leak_violations`)
   and transcript-reuse byte-identity
   (:func:`find_transcript_reuse_mismatches`) -- both re-derive their own
   evidence directly from each row's own prompt content, never trusting a
   separately-carried field.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence

from ..core.retrieval import normalize_term
from ..rails.probes.pkey_flight import (
    AUD_NOSUP_ARM,
    AUD_SUP_ARM,
    EXPECTED_SILENCE_SWAP_COUNT,
    PKEY_ARMS,
    PKEY_SLU_ARMS,
    SILENCE_SWAP_ARM,
    T0_ARM,
    TXT_NOSUP_ARM,
    TXT_SUP_ARM,
    PKeyFlightError,
    content_has_audio,
    content_text_parts,
    extract_txt_transcript_from_rendered,
)
from ..rails.probes.pslu_flight import (
    PsluFlightError,
    load_pslu_rosters,
    load_pslu_sample_manifest,
    pslu_supply_packet,
)
from ..reproduction.slurp_scoring import parse_slu_response, score_slu
from .pslu_read import (
    ArmAggregate,
    ClauseResult,
    PsluReadError,
    RecheckMismatch,
    RowAnalysis,
    RUNTIME_PROHIBITED_NOTE,
    SilenceSwapComparison,
    _parsed_answer_signature,
    _recheck_row,
    _roster_values_for_packet,
    _void_clause_harness_defect,
    _void_clause_recheck,
    _void_clause_silence_swap,
    build_arm_aggregate,
    count_induced_substitutions,
    load_gold_by_sample_id,
)

REPORT_SCHEMA = "saea-pkey-read-v1"

N_SAMPLES = 60

# docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md section 4,
# quoted verbatim in each clause's own detail text below.
SPEECH_TERM_PRESENT_MIN = 0.06
KEY_ONLY_MAX_ABS = 0.03
TEXT_DOMINANT_MAX = -0.06


class PKeyReadError(RuntimeError):
    """Malformed attempt-dir/binding input for this read -- never raised for
    a legitimate VOID-worthy data shape (that is reported as a clause
    result, not an exception)."""


# ---------------------------------------------------------------------------
# Loading: outputs.jsonl / flight-receipt.json.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PKeyOutputRow:
    arm: str
    sample_id: str
    silence_swapped: bool
    transcript_sha256_used: str | None
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: Mapping[str, object]

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "PKeyOutputRow":
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            silence_swapped=bool(document["silence_swapped"]),
            transcript_sha256_used=document.get("transcript_sha256_used"),
            messages=tuple(document["messages"]),
            response_text=str(document["response_text"]),
            metrics=document["metrics"],
            consumption=document["consumption"],
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[PKeyOutputRow, ...]:
    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise PKeyReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[PKeyOutputRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PKeyReadError(f"{path} line {line_no}: invalid JSON: {error}") from error
        rows.append(PKeyOutputRow.from_json(document))
    if not rows:
        raise PKeyReadError(f"{path}: zero rows")
    return tuple(rows)


def load_flight_status(attempt_dir: Path) -> tuple[str | None, str | None]:
    path = Path(attempt_dir) / "flight-receipt.json"
    if not path.is_file():
        return None, "flight-receipt.json missing"
    document = json.loads(path.read_text(encoding="utf-8"))
    return document.get("status"), document.get("error")


def load_gold_sentence_by_sample_id(
    lock: Mapping[str, object], root: Path, sample_ids: Sequence[str]
) -> dict[str, str]:
    """RUNTIME_PROHIBITED (module docstring): SCORING-SIDE ONLY, the
    T0-vs-gold WER descriptive's own gold text. Never referenced by
    ``rails.probes.pkey_flight`` (that module has no gold-text parameter
    anywhere in its own API -- a structural fact ``tests/unit/
    test_pkey_flight.py`` checks directly)."""

    from ..data.slurp import _governed_roots, _read_jsonl

    gold_records = load_gold_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED (reused)
    _, _, metadata_dir = _governed_roots(lock, Path(root))
    path = metadata_dir / "devel.jsonl"
    sentence_by_slurp_id: dict[str, str] = {}
    for raw in _read_jsonl(path):
        slurp_id = raw.get("slurp_id")
        sentence = raw.get("sentence")
        if isinstance(slurp_id, int) and not isinstance(slurp_id, bool) and isinstance(sentence, str):
            sentence_by_slurp_id[str(slurp_id)] = sentence
    missing = [
        sample_id
        for sample_id in sample_ids
        if gold_records[sample_id].utterance_id not in sentence_by_slurp_id
    ]
    if missing:
        raise PKeyReadError(
            f"gold sentence text missing for {len(missing)} sample id(s) the manifest names: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
        )
    return {sample_id: sentence_by_slurp_id[gold_records[sample_id].utterance_id] for sample_id in sample_ids}


# ---------------------------------------------------------------------------
# Per-row scoring (shared by the four SLU-scored arms).
# ---------------------------------------------------------------------------


def _score_row(row: PKeyOutputRow, gold) -> RowAnalysis:
    predicted_scenario, predicted_action, predicted_entities, parsed = parse_slu_response(row.response_text)
    predicted_entities = tuple(predicted_entities)
    recomputed = score_slu(
        gold_scenario=gold.scenario,
        gold_action=gold.action,
        gold_entities=gold.entities,
        predicted_scenario=predicted_scenario,
        predicted_action=predicted_action,
        predicted_entities=predicted_entities,
    )
    mismatches = _recheck_row(row, recomputed, parsed)
    return RowAnalysis(
        row=row,
        predicted_scenario=predicted_scenario,
        predicted_action=predicted_action,
        predicted_entities=predicted_entities,
        parsed=parsed,
        recomputed_score=recomputed,
        recheck_mismatches=mismatches,
        roster_reconciliation=None,
        induced_substitutions=0,
    )


def _sample_fully_correct(analysis: RowAnalysis) -> bool:
    """Module docstring note 1: exact scenario_action match AND an exact
    entity slot set (zero FP, zero FN)."""

    score = analysis.recomputed_score
    return score.scenario_action_exact == 1.0 and score.slot_f1_exact_fp == 0.0 and score.slot_f1_exact_fn == 0.0


def _fully_correct_by_sample(analyses: Sequence[RowAnalysis]) -> dict[str, bool]:
    return {analysis.row.sample_id: _sample_fully_correct(analysis) for analysis in analyses}


# ---------------------------------------------------------------------------
# T0-vs-gold WER (scoring-side only, reported, no clause).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class T0WerResult:
    per_sample: Mapping[str, float]
    macro_wer: float  # mean of per-sample WER, 0.0 when there is nothing to score


def compute_t0_wer(
    t0_rows: Sequence[PKeyOutputRow], gold_sentence_by_sample_id: Mapping[str, str]
) -> T0WerResult:
    """Reuses ``reproduction.slurp_scoring._word_distance`` (``jiwer.wer``,
    the SAME WER primitive the official SLU-F1 word-distance ingredient
    already uses -- never a second WER implementation), truth=gold,
    hypothesis=T0's own response text."""

    from ..reproduction.slurp_scoring import _word_distance

    per_sample: dict[str, float] = {}
    for row in t0_rows:
        gold = gold_sentence_by_sample_id.get(row.sample_id)
        if gold is None:
            continue
        per_sample[row.sample_id] = _word_distance(gold, row.response_text)
    macro = sum(per_sample.values()) / len(per_sample) if per_sample else 0.0
    return T0WerResult(per_sample=per_sample, macro_wer=macro)


# ---------------------------------------------------------------------------
# Legality: gold text must never appear inside any prompt.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoldLeakViolation:
    arm: str
    sample_id: str
    detail: str


def _scannable_content_texts(row: PKeyOutputRow) -> tuple[str, ...]:
    """The text content parts eligible for the gold-leak scan below.

    On a TXT-NOSUP/TXT-SUP row, the LAST text content part is, by
    construction (``rails.probes.pkey_flight.assemble_txt_messages`` always
    appends it last and nothing legitimate ever follows it), T0's OWN
    transcript rendered through the pinned template -- reused byte-identity
    (``find_transcript_reuse_mismatches`` is the dedicated check for THAT
    boundary). On genuinely well-transcribed audio, T0's own model output
    can legitimately equal the gold sentence verbatim (a GOOD, expected
    outcome -- the whole point of transcription, not a "leak": no gold text
    was ever read to produce it). Scanning that part here would therefore
    fire routinely on well-behaved flights, not just on an actual defect.
    This function excludes exactly that one, positionally-trusted part
    (the SAME positional trust ``analysis.pslu_read._row_prompt_text``
    already places on ``content[0]``) and scans everything else -- on
    T0/AUD-NOSUP/AUD-SUP rows, that is every text part unconditionally (T0
    carries none; AUD-NOSUP carries none; AUD-SUP's only text part is the
    roster, which must never legitimately contain a sample's own gold
    sentence)."""

    texts = content_text_parts(row.messages)
    if row.arm in (TXT_NOSUP_ARM, TXT_SUP_ARM) and texts:
        return texts[:-1]
    return texts


def find_gold_leak_violations(
    rows: Sequence[PKeyOutputRow], gold_sentence_by_sample_id: Mapping[str, str]
) -> tuple[GoldLeakViolation, ...]:
    """Legality check (module docstring): a sample's OWN gold sentence text
    must never appear (normalized substring match) inside any prompt-side
    ``type == "text"`` content part this study's own machinery is
    responsible for constructing -- see :func:`_scannable_content_texts`
    for the one deliberate, documented exclusion (T0's own legitimately
    matching transcript). Never scans an ``input_audio`` content part (it
    carries no text), and never scans a RESPONSE (a model output coinciding
    with gold is not a prompt-path violation by definition)."""

    violations: list[GoldLeakViolation] = []
    for row in rows:
        gold = gold_sentence_by_sample_id.get(row.sample_id)
        if not gold:
            continue
        normalized_gold = normalize_term(gold)
        if not normalized_gold:
            continue
        for text in _scannable_content_texts(row):
            if normalized_gold in normalize_term(text):
                violations.append(
                    GoldLeakViolation(
                        arm=row.arm,
                        sample_id=row.sample_id,
                        detail=(
                            "this row's own prompt text contains its sample's own gold sentence "
                            "(normalized substring match) -- gold text must never enter a prompt path"
                        ),
                    )
                )
                break
    return tuple(violations)


# ---------------------------------------------------------------------------
# Transcript-reuse byte-identity (the registered hard ordering dependency).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TranscriptMismatch:
    arm: str
    sample_id: str
    expected_sha256: str
    actual_sha256: str | None
    detail: str


def find_transcript_reuse_mismatches(
    t0_rows: Sequence[PKeyOutputRow], txt_rows: Sequence[PKeyOutputRow]
) -> tuple[TranscriptMismatch, ...]:
    """VOID-worthy legality/integrity check (module docstring): for every
    TXT-NOSUP/TXT-SUP row, RE-EXTRACT the transcript text this row's own
    prompt actually rendered (never trust ``transcript_sha256_used``
    blindly -- reconstruct from the raw prompt content the SAME way
    ``rails.probes.pkey_flight.validate_pkey_flight_summary`` itself does,
    via the SAME ``extract_txt_transcript_from_rendered``) and cross-check
    it byte-for-byte against that SAME sample's own T0 row found in THIS
    attempt's own ``outputs.jsonl``."""

    t0_by_sample = {row.sample_id: row for row in t0_rows}
    mismatches: list[TranscriptMismatch] = []
    for row in txt_rows:
        t0_row = t0_by_sample.get(row.sample_id)
        if t0_row is None:
            mismatches.append(
                TranscriptMismatch(row.arm, row.sample_id, "", None, "no T0 row found for this sample id in this attempt")
            )
            continue
        expected_sha256 = hashlib.sha256(t0_row.response_text.encode("utf-8")).hexdigest()
        texts = content_text_parts(row.messages)
        if not texts:
            mismatches.append(
                TranscriptMismatch(
                    row.arm, row.sample_id, expected_sha256, None,
                    "row carries no text content part to extract a transcript from",
                )
            )
            continue
        try:
            actual_text = extract_txt_transcript_from_rendered(texts[-1])
        except PKeyFlightError as error:
            mismatches.append(
                TranscriptMismatch(row.arm, row.sample_id, expected_sha256, None, f"could not extract a transcript block: {error}")
            )
            continue
        actual_sha256 = hashlib.sha256(actual_text.encode("utf-8")).hexdigest()
        if actual_sha256 != expected_sha256:
            mismatches.append(
                TranscriptMismatch(
                    row.arm, row.sample_id, expected_sha256, actual_sha256,
                    "byte-identity violated: this row's own rendered transcript text does not "
                    "sha256-match T0's own response_text for the same sample id",
                )
            )
    return tuple(mismatches)


# ---------------------------------------------------------------------------
# Structural / prompt-shape harness-defect checks.
# ---------------------------------------------------------------------------


def _roster_mismatch_and_shape_reasons(
    rows_by_arm: Mapping[str, Sequence[PKeyOutputRow]], a3_prompt_block: str
) -> tuple[str, ...]:
    reasons: list[str] = []
    for row in rows_by_arm.get(AUD_SUP_ARM, ()):
        texts = content_text_parts(row.messages)
        if not texts or texts[0] != a3_prompt_block:
            reasons.append(f"arm {AUD_SUP_ARM} sample {row.sample_id}: roster text does not match the reconstructed A3 packet")
        if not content_has_audio(row.messages):
            reasons.append(f"arm {AUD_SUP_ARM} sample {row.sample_id}: carries no audio content part")
    for row in rows_by_arm.get(AUD_NOSUP_ARM, ()):
        if content_text_parts(row.messages):
            reasons.append(f"arm {AUD_NOSUP_ARM} sample {row.sample_id}: unexpectedly carries text content (zero-supply arm)")
        if not content_has_audio(row.messages):
            reasons.append(f"arm {AUD_NOSUP_ARM} sample {row.sample_id}: carries no audio content part")
    for row in rows_by_arm.get(TXT_SUP_ARM, ()):
        texts = content_text_parts(row.messages)
        if len(texts) != 2 or texts[0] != a3_prompt_block:
            reasons.append(f"arm {TXT_SUP_ARM} sample {row.sample_id}: roster text does not match the reconstructed A3 packet")
        if content_has_audio(row.messages):
            reasons.append(f"arm {TXT_SUP_ARM} sample {row.sample_id}: TXT arm carries an audio content part")
    for row in rows_by_arm.get(TXT_NOSUP_ARM, ()):
        texts = content_text_parts(row.messages)
        if len(texts) != 1:
            reasons.append(f"arm {TXT_NOSUP_ARM} sample {row.sample_id}: expected exactly one text content part (the transcript block)")
        if content_has_audio(row.messages):
            reasons.append(f"arm {TXT_NOSUP_ARM} sample {row.sample_id}: TXT arm carries an audio content part")
    return tuple(reasons)


def _harness_defect_reasons(
    *,
    flight_status: str | None,
    flight_error: str | None,
    rows_by_arm: Mapping[str, Sequence[PKeyOutputRow]],
    silence_rows: Sequence[PKeyOutputRow],
    sample_ids: Sequence[str],
    unknown_arm_rows: Sequence[PKeyOutputRow],
    duplicate_keys: Sequence[tuple[str, str, bool]],
    shape_reasons: Sequence[str],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if flight_status != "COMPLETED":
        reasons.append(f"flight-receipt status={flight_status!r} (expected 'COMPLETED'); error={flight_error!r}")
    for row in unknown_arm_rows:
        reasons.append(f"unknown arm {row.arm!r} on sample {row.sample_id!r}")
    for key in duplicate_keys:
        reasons.append(f"duplicate row for (arm, sample_id, silence_swapped)={key}")
    id_set = set(sample_ids)
    for arm in PKEY_ARMS:
        rows = rows_by_arm[arm]
        got = {row.sample_id for row in rows}
        missing = id_set - got
        extra = got - id_set
        if missing:
            reasons.append(f"arm {arm}: missing {len(missing)} sample(s) from the frozen manifest: {sorted(missing)[:5]}")
        if extra:
            reasons.append(f"arm {arm}: {len(extra)} sample(s) not in the frozen manifest: {sorted(extra)[:5]}")
        duplicate_ids = len(rows) - len({row.sample_id for row in rows})
        if duplicate_ids > 0:
            reasons.append(f"arm {arm}: {duplicate_ids} duplicate sample_id row(s)")
    if len(silence_rows) != EXPECTED_SILENCE_SWAP_COUNT:
        reasons.append(f"expected exactly {EXPECTED_SILENCE_SWAP_COUNT} silence-swap rows, found {len(silence_rows)}")
    for row in silence_rows:
        if row.arm != SILENCE_SWAP_ARM:
            reasons.append(f"silence-swap row on sample {row.sample_id!r} is on arm {row.arm!r}, expected {SILENCE_SWAP_ARM!r}")
    reasons.extend(shape_reasons)
    return tuple(reasons)


# ---------------------------------------------------------------------------
# Silence-swap comparison (AUD-SUP only).
# ---------------------------------------------------------------------------


def compare_silence_swap_pkey(rows: Sequence[PKeyOutputRow]) -> tuple[SilenceSwapComparison, ...]:
    real_by_sample: dict[str, PKeyOutputRow] = {}
    silence_by_sample: dict[str, PKeyOutputRow] = {}
    for row in rows:
        if row.arm != SILENCE_SWAP_ARM:
            continue
        if row.silence_swapped:
            silence_by_sample[row.sample_id] = row
        else:
            real_by_sample[row.sample_id] = row

    comparisons: list[SilenceSwapComparison] = []
    for sample_id, silence_row in sorted(silence_by_sample.items()):
        real_row = real_by_sample.get(sample_id)
        has_real = real_row is not None
        real_text = real_row.response_text if real_row is not None else ""
        real_sig = _parsed_answer_signature(real_text) if real_row is not None else (None, None, ())
        silence_sig = _parsed_answer_signature(silence_row.response_text)
        comparisons.append(
            SilenceSwapComparison(
                sample_id=sample_id,
                real_response_text=real_text,
                silence_response_text=silence_row.response_text,
                real_signature=real_sig,
                silence_signature=silence_sig,
                unchanged=has_real and real_sig == silence_sig,
                has_real_counterpart=has_real,
            )
        )
    return tuple(comparisons)


# ---------------------------------------------------------------------------
# VOID.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VoidVerdict:
    clauses: tuple[ClauseResult, ...]
    voided: bool


def _void_clause_gold_leak(violations: Sequence[GoldLeakViolation]) -> ClauseResult:
    clause_text = "gold sentence text found inside a prompt"
    if violations:
        shown = "; ".join(f"{v.arm}/{v.sample_id}: {v.detail}" for v in violations[:10])
        more = f" (+{len(violations) - 10} more)" if len(violations) > 10 else ""
        return ClauseResult(clause_text, "met", f"{len(violations)} violation(s): {shown}{more}")
    return ClauseResult(clause_text, "not_met", "no row's own prompt text contains its sample's own gold sentence")


def _void_clause_transcript_reuse(mismatches: Sequence[TranscriptMismatch]) -> ClauseResult:
    clause_text = "a TXT-* row's transcript disagrees with its own T0 output (byte-identity)"
    if mismatches:
        shown = "; ".join(
            f"{m.arm}/{m.sample_id}: expected={m.expected_sha256!r} actual={m.actual_sha256!r} ({m.detail})"
            for m in mismatches[:10]
        )
        more = f" (+{len(mismatches) - 10} more)" if len(mismatches) > 10 else ""
        return ClauseResult(clause_text, "met", f"{len(mismatches)} mismatch(es): {shown}{more}")
    return ClauseResult(clause_text, "not_met", "every TXT-* row's own rendered transcript sha256-matched its own T0 response")


def evaluate_void(
    *,
    recheck_mismatches: Sequence[RecheckMismatch],
    harness_defect_reasons: Sequence[str],
    silence_comparisons: Sequence[SilenceSwapComparison],
    gold_leak_violations: Sequence[GoldLeakViolation],
    transcript_mismatches: Sequence[TranscriptMismatch],
) -> VoidVerdict:
    void_recheck = _void_clause_recheck(recheck_mismatches)
    void_harness = _void_clause_harness_defect(harness_defect_reasons)
    void_silence = _void_clause_silence_swap(silence_comparisons)
    void_gold_leak = _void_clause_gold_leak(gold_leak_violations)
    void_transcript = _void_clause_transcript_reuse(transcript_mismatches)
    clauses = (void_silence, void_harness, void_recheck, void_gold_leak, void_transcript)
    voided = any(clause.verdict == "met" for clause in clauses)
    return VoidVerdict(clauses=clauses, voided=voided)


# ---------------------------------------------------------------------------
# Perception gap (descriptive, no clause).
# ---------------------------------------------------------------------------


def perception_gap(aggregates: Mapping[str, ArmAggregate]) -> float:
    """Module docstring note 2: TXT-NOSUP minus AUD-NOSUP SLU-F1."""

    return aggregates[TXT_NOSUP_ARM].slu_f1_f1 - aggregates[AUD_NOSUP_ARM].slu_f1_f1


# ---------------------------------------------------------------------------
# INTERACTION I and its four registered verdicts.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InteractionVerdict:
    delta_aud: float
    delta_txt: float
    interaction: float
    speech_term_present: ClauseResult
    key_only: ClauseResult
    text_dominant: ClauseResult
    overall: str


def evaluate_interaction(aggregates: Mapping[str, ArmAggregate]) -> InteractionVerdict:
    """Registration section 4: Delta_AUD = AUD-SUP - AUD-NOSUP; Delta_TXT =
    TXT-SUP - TXT-NOSUP; I = Delta_AUD - Delta_TXT. The three threshold
    ranges (I >= +0.06, |I| <= 0.03, I <= -0.06) are mutually exclusive and
    checked in the registered order; "otherwise INCONCLUSIVE-KEY" covers the
    two open gaps between them."""

    delta_aud = aggregates[AUD_SUP_ARM].slu_f1_f1 - aggregates[AUD_NOSUP_ARM].slu_f1_f1
    delta_txt = aggregates[TXT_SUP_ARM].slu_f1_f1 - aggregates[TXT_NOSUP_ARM].slu_f1_f1
    interaction = delta_aud - delta_txt

    speech_term_present = ClauseResult(
        f"I >= +{SPEECH_TERM_PRESENT_MIN:.2f} (2x the measured 0.03 separability bar)",
        "met" if interaction >= SPEECH_TERM_PRESENT_MIN else "not_met",
        f"I={interaction:+.4f}, floor={SPEECH_TERM_PRESENT_MIN:+.2f}, margin={interaction - SPEECH_TERM_PRESENT_MIN:+.4f}",
    )
    key_only = ClauseResult(
        f"|I| <= {KEY_ONLY_MAX_ABS:.2f}",
        "met" if abs(interaction) <= KEY_ONLY_MAX_ABS else "not_met",
        f"I={interaction:+.4f}, |I|={abs(interaction):.4f}, ceiling={KEY_ONLY_MAX_ABS:.2f}, "
        f"margin={KEY_ONLY_MAX_ABS - abs(interaction):+.4f}",
    )
    text_dominant = ClauseResult(
        f"I <= {TEXT_DOMINANT_MAX:.2f}",
        "met" if interaction <= TEXT_DOMINANT_MAX else "not_met",
        f"I={interaction:+.4f}, ceiling={TEXT_DOMINANT_MAX:+.2f}, margin={TEXT_DOMINANT_MAX - interaction:+.4f}",
    )

    if speech_term_present.verdict == "met":
        overall = "SPEECH-TERM-PRESENT"
    elif key_only.verdict == "met":
        overall = "KEY-ONLY"
    elif text_dominant.verdict == "met":
        overall = "TEXT-DOMINANT"
    else:
        overall = "INCONCLUSIVE-KEY"

    return InteractionVerdict(
        delta_aud=delta_aud,
        delta_txt=delta_txt,
        interaction=interaction,
        speech_term_present=speech_term_present,
        key_only=key_only,
        text_dominant=text_dominant,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Converted-set difference + soft P-PHON cross-reference.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConvertedSetResult:
    aud_converted: tuple[str, ...]
    txt_converted: tuple[str, ...]
    # aud_converted - txt_converted: the perception-repair set (registration
    # section 4).
    aud_only: tuple[str, ...]
    # Soft cross-reference (module docstring note 3) -- {} when P-PHON's own
    # output is unavailable; keyed by every sample_id in aud_only that IS
    # present in the loaded P-PHON class mapping (never all of aud_only).
    pphon_class_by_sample: Mapping[str, str]


def compute_converted_set(
    *,
    aud_nosup_analyses: Sequence[RowAnalysis],
    aud_sup_analyses: Sequence[RowAnalysis],
    txt_nosup_analyses: Sequence[RowAnalysis],
    txt_sup_analyses: Sequence[RowAnalysis],
    pphon_classes: Mapping[str, str] = MappingProxyType({}),
) -> ConvertedSetResult:
    aud_nosup_ok = _fully_correct_by_sample(aud_nosup_analyses)
    aud_sup_ok = _fully_correct_by_sample(aud_sup_analyses)
    txt_nosup_ok = _fully_correct_by_sample(txt_nosup_analyses)
    txt_sup_ok = _fully_correct_by_sample(txt_sup_analyses)

    aud_converted = tuple(
        sorted(
            sample_id
            for sample_id, sup_ok in aud_sup_ok.items()
            if sup_ok and not aud_nosup_ok.get(sample_id, False)
        )
    )
    txt_converted = tuple(
        sorted(
            sample_id
            for sample_id, sup_ok in txt_sup_ok.items()
            if sup_ok and not txt_nosup_ok.get(sample_id, False)
        )
    )
    aud_only = tuple(sorted(set(aud_converted) - set(txt_converted)))

    return ConvertedSetResult(
        aud_converted=aud_converted,
        txt_converted=txt_converted,
        aud_only=aud_only,
        pphon_class_by_sample={
            sample_id: pphon_classes[sample_id] for sample_id in aud_only if sample_id in pphon_classes
        },
    )


def load_pphon_classes(path: Path | None) -> Mapping[str, str]:
    """Module docstring note 3: SOFT, read-only, tolerate-absence P-PHON
    cross-reference. Tolerated shapes: ``{"samples": {"<id>": {"class":
    "..."}, ...}}`` or a flat ``{"<id>": "<class>"}`` mapping; every other
    shape, or any I/O/parse failure, degrades to ``{}``."""

    if path is None:
        return {}
    path = Path(path)
    if not path.is_file():
        return {}
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    if not isinstance(document, Mapping):
        return {}
    samples = document.get("samples")
    if isinstance(samples, Mapping):
        result: dict[str, str] = {}
        for sample_id, record in samples.items():
            if isinstance(record, Mapping) and isinstance(record.get("class"), str):
                result[str(sample_id)] = record["class"]
            elif isinstance(record, str):
                result[str(sample_id)] = record
        return result
    flat: dict[str, str] = {}
    for sample_id, value in document.items():
        if isinstance(value, str):
            flat[str(sample_id)] = value
    return flat


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PKeyReadReport:
    attempt_dir: Path
    flight_status: str | None
    flight_error: str | None
    aggregates: Mapping[str, ArmAggregate]
    t0_wer: T0WerResult
    perception_gap: float
    interaction: InteractionVerdict
    converted_set: ConvertedSetResult
    silence_comparisons: tuple[SilenceSwapComparison, ...]
    recheck_mismatches: tuple[RecheckMismatch, ...]
    harness_defect_reasons: tuple[str, ...]
    gold_leak_violations: tuple[GoldLeakViolation, ...]
    transcript_mismatches: tuple[TranscriptMismatch, ...]
    void_verdict: VoidVerdict

    @property
    def overall(self) -> str:
        return "VOID" if self.void_verdict.voided else self.interaction.overall


def build_pkey_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    sample_manifest_path: Path,
    roster_table_path: Path,
    pphon_verdict_path: Path | None = None,
) -> PKeyReadReport:
    attempt_dir = Path(attempt_dir)
    rows = load_attempt_rows(attempt_dir)
    flight_status, flight_error = load_flight_status(attempt_dir)

    manifest = load_pslu_sample_manifest(sample_manifest_path)
    rosters = load_pslu_rosters(roster_table_path)
    sample_ids = manifest.sample_ids
    a3_supply = pslu_supply_packet("A3", scenario=None, rosters=rosters)
    roster_values = _roster_values_for_packet(a3_supply)

    gold_by_id = load_gold_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED (reused)
    gold_sentence_by_id = load_gold_sentence_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED

    rows_by_arm: dict[str, list[PKeyOutputRow]] = {arm: [] for arm in PKEY_ARMS}
    silence_rows: list[PKeyOutputRow] = []
    unknown_arm_rows: list[PKeyOutputRow] = []
    seen_keys: set[tuple[str, str, bool]] = set()
    duplicate_keys: list[tuple[str, str, bool]] = []
    for row in rows:
        key = (row.arm, row.sample_id, row.silence_swapped)
        if key in seen_keys:
            duplicate_keys.append(key)
            continue
        seen_keys.add(key)
        if row.arm not in PKEY_ARMS:
            unknown_arm_rows.append(row)
            continue
        if row.silence_swapped:
            silence_rows.append(row)
        else:
            rows_by_arm[row.arm].append(row)

    roster_values_by_arm = {
        AUD_NOSUP_ARM: (),
        AUD_SUP_ARM: roster_values,
        TXT_NOSUP_ARM: (),
        TXT_SUP_ARM: roster_values,
    }

    recheck_mismatches: list[RecheckMismatch] = []
    analyses_by_arm: dict[str, tuple[RowAnalysis, ...]] = {}
    for arm in PKEY_SLU_ARMS:
        analyses: list[RowAnalysis] = []
        for row in rows_by_arm[arm]:
            gold = gold_by_id.get(row.sample_id)
            if gold is None:
                continue  # reported separately as a missing-manifest-id harness defect below
            analysis = _score_row(row, gold)
            recheck_mismatches.extend(analysis.recheck_mismatches)
            induced = count_induced_substitutions(analysis.predicted_entities, gold.entities, roster_values_by_arm[arm])
            analyses.append(
                RowAnalysis(
                    row=analysis.row,
                    predicted_scenario=analysis.predicted_scenario,
                    predicted_action=analysis.predicted_action,
                    predicted_entities=analysis.predicted_entities,
                    parsed=analysis.parsed,
                    recomputed_score=analysis.recomputed_score,
                    recheck_mismatches=analysis.recheck_mismatches,
                    roster_reconciliation=None,
                    induced_substitutions=induced,
                )
            )
        analyses_by_arm[arm] = tuple(analyses)

    # T0 rows are not SLU-scored (module docstring) -- nothing to recheck.

    for row in silence_rows:
        gold = gold_by_id.get(row.sample_id)
        if gold is None:
            continue
        recheck_mismatches.extend(_score_row(row, gold).recheck_mismatches)

    aggregates = {arm: build_arm_aggregate(arm, analyses_by_arm[arm]) for arm in PKEY_SLU_ARMS}

    t0_wer = compute_t0_wer(rows_by_arm[T0_ARM], gold_sentence_by_id)

    shape_reasons = _roster_mismatch_and_shape_reasons(rows_by_arm, a3_supply.prompt_block)
    harness_defect_reasons = _harness_defect_reasons(
        flight_status=flight_status,
        flight_error=flight_error,
        rows_by_arm=rows_by_arm,
        silence_rows=silence_rows,
        sample_ids=sample_ids,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_keys=duplicate_keys,
        shape_reasons=shape_reasons,
    )

    silence_comparisons = compare_silence_swap_pkey(list(rows_by_arm[SILENCE_SWAP_ARM]) + silence_rows)

    gold_leak_violations = find_gold_leak_violations(rows, gold_sentence_by_id)
    transcript_mismatches = find_transcript_reuse_mismatches(
        rows_by_arm[T0_ARM], list(rows_by_arm[TXT_NOSUP_ARM]) + list(rows_by_arm[TXT_SUP_ARM])
    )

    void_verdict = evaluate_void(
        recheck_mismatches=recheck_mismatches,
        harness_defect_reasons=harness_defect_reasons,
        silence_comparisons=silence_comparisons,
        gold_leak_violations=gold_leak_violations,
        transcript_mismatches=transcript_mismatches,
    )
    interaction = evaluate_interaction(aggregates)
    perception = perception_gap(aggregates)
    converted_set = compute_converted_set(
        aud_nosup_analyses=analyses_by_arm[AUD_NOSUP_ARM],
        aud_sup_analyses=analyses_by_arm[AUD_SUP_ARM],
        txt_nosup_analyses=analyses_by_arm[TXT_NOSUP_ARM],
        txt_sup_analyses=analyses_by_arm[TXT_SUP_ARM],
        pphon_classes=load_pphon_classes(pphon_verdict_path),
    )

    return PKeyReadReport(
        attempt_dir=attempt_dir,
        flight_status=flight_status,
        flight_error=flight_error,
        aggregates=aggregates,
        t0_wer=t0_wer,
        perception_gap=perception,
        interaction=interaction,
        converted_set=converted_set,
        silence_comparisons=silence_comparisons,
        recheck_mismatches=tuple(recheck_mismatches),
        harness_defect_reasons=harness_defect_reasons,
        gold_leak_violations=gold_leak_violations,
        transcript_mismatches=transcript_mismatches,
        void_verdict=void_verdict,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def _aggregate_json(aggregate: ArmAggregate) -> dict[str, object]:
    return {
        "arm": aggregate.arm,
        "n_samples": aggregate.n_samples,
        "slu_f1": {"precision": aggregate.slu_f1_precision, "recall": aggregate.slu_f1_recall, "f1": aggregate.slu_f1_f1},
        "slot_f1_exact": {
            "precision": aggregate.slot_f1_exact_precision,
            "recall": aggregate.slot_f1_exact_recall,
            "f1": aggregate.slot_f1_exact_f1,
            "tp_sum": aggregate.slot_f1_exact_tp_sum,
        },
        "intent_accuracy": aggregate.intent_accuracy,
        "copy_rate": aggregate.copy_rate,
        "copy_records": aggregate.copy_records,
        "copy_records_total": aggregate.copy_records_total,
        "induced_substitution_count": aggregate.induced_substitution_count,
    }


def report_to_json(report: PKeyReadReport) -> dict[str, object]:
    verdict = report.interaction
    converted = report.converted_set
    return {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "flight_error": report.flight_error,
        "aggregates": {arm: _aggregate_json(agg) for arm, agg in report.aggregates.items()},
        "t0_wer": {
            "macro_wer": report.t0_wer.macro_wer,
            "per_sample": dict(report.t0_wer.per_sample),
            "note": "scoring-side only -- gold text never entered any prompt path (find_gold_leak_violations)",
        },
        "perception_gap": {
            "value": report.perception_gap,
            "definition": "TXT-NOSUP.slu_f1 - AUD-NOSUP.slu_f1 (descriptive, no clause)",
        },
        "interaction": {
            "delta_aud": verdict.delta_aud,
            "delta_txt": verdict.delta_txt,
            "interaction": verdict.interaction,
            "speech_term_present": _clause_json(verdict.speech_term_present),
            "key_only": _clause_json(verdict.key_only),
            "text_dominant": _clause_json(verdict.text_dominant),
            "overall": verdict.overall,
        },
        "converted_set": {
            "aud_converted": list(converted.aud_converted),
            "txt_converted": list(converted.txt_converted),
            "aud_only": list(converted.aud_only),
            "pphon_class_by_sample": dict(converted.pphon_class_by_sample),
        },
        "silence_swap": [
            {
                "sample_id": c.sample_id,
                "unchanged": c.unchanged,
                "has_real_counterpart": c.has_real_counterpart,
                "real_signature": list(c.real_signature[:2]) + [list(c.real_signature[2])],
                "silence_signature": list(c.silence_signature[:2]) + [list(c.silence_signature[2])],
            }
            for c in report.silence_comparisons
        ],
        "recheck_mismatch_count": len(report.recheck_mismatches),
        "harness_defect_reasons": list(report.harness_defect_reasons),
        "gold_leak_violation_count": len(report.gold_leak_violations),
        "transcript_mismatch_count": len(report.transcript_mismatches),
        "void": {"clauses": [_clause_json(c) for c in report.void_verdict.clauses], "voided": report.void_verdict.voided},
        "overall": report.overall,
    }


def render_report(report: PKeyReadReport) -> str:
    lines = [
        "P-KEY pinned offline read (docs/readiness/2026-08-18-pkey-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r} (error={report.flight_error!r})",
        "",
        "Per-arm aggregates",
    ]
    header = f"  {'arm':<12}{'n':>4}{'slu_f1':>9}{'slot_f1x':>10}{'intent_acc':>12}{'copy_rate':>11}{'induced':>9}"
    lines.append(header)
    for arm in PKEY_SLU_ARMS:
        agg = report.aggregates[arm]
        lines.append(
            f"  {arm:<12}{agg.n_samples:>4}{agg.slu_f1_f1:>9.4f}{agg.slot_f1_exact_f1:>10.4f}"
            f"{agg.intent_accuracy:>12.4f}{agg.copy_rate:>11.4f}{agg.induced_substitution_count:>9}"
        )
    lines.append("")

    lines.append(f"T0 vs gold transcript WER (scoring-side only): macro={report.t0_wer.macro_wer:.4f} over {len(report.t0_wer.per_sample)} sample(s)")
    lines.append("")

    lines.append(f"Perception gap (TXT-NOSUP - AUD-NOSUP SLU-F1, descriptive): {report.perception_gap:+.4f}")
    lines.append("")

    verdict = report.interaction
    lines.append(f"Delta_AUD={verdict.delta_aud:+.4f}  Delta_TXT={verdict.delta_txt:+.4f}  INTERACTION I={verdict.interaction:+.4f}")
    for clause in (verdict.speech_term_present, verdict.key_only, verdict.text_dominant):
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"  INTERACTION VERDICT: {verdict.overall}")
    lines.append("")

    converted = report.converted_set
    lines.append(f"Converted-set difference: aud_converted={len(converted.aud_converted)} txt_converted={len(converted.txt_converted)} aud_only(perception-repair)={len(converted.aud_only)}")
    for sample_id in converted.aud_only:
        pphon = converted.pphon_class_by_sample.get(sample_id, "(P-PHON class unavailable)")
        lines.append(f"  {sample_id}: P-PHON class = {pphon}")
    lines.append("")

    lines.append("Silence-swap comparison (3 AUD-SUP silence variants vs their real-audio counterparts)")
    if not report.silence_comparisons:
        lines.append("  (none found)")
    for c in report.silence_comparisons:
        lines.append(f"  {c.sample_id}: unchanged={c.unchanged} has_real_counterpart={c.has_real_counterpart}")
    lines.append("")

    if report.harness_defect_reasons:
        lines.append("!" * 78)
        lines.append("HARNESS DEFECT REASONS")
        for reason in report.harness_defect_reasons:
            lines.append(f"  {reason}")
        lines.append("!" * 78)
        lines.append("")

    lines.append(f"recheck mismatches (TP/FP/FN vs adapter's committed scorer): {len(report.recheck_mismatches)}")
    lines.append(f"gold-leak violations: {len(report.gold_leak_violations)}")
    lines.append(f"transcript-reuse byte-identity mismatches: {len(report.transcript_mismatches)}")
    lines.append("")

    void = report.void_verdict
    lines.append(f"VOID (checked FIRST): {'MET' if void.voided else 'not met'}")
    for clause in void.clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    lines.append(f"OVERALL: {report.overall}")
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pkey-read",
        description=(
            "P-KEY pinned offline read suite: per-arm official SLU-F1, Delta_AUD/Delta_TXT/"
            "INTERACTION with the four registered verdicts, the perception-gap descriptive, the "
            "converted-set difference (with an optional soft P-PHON cross-reference), T0-vs-gold WER "
            "(scoring-side only), induced-substitution count, silence-swap comparison, and the "
            "mechanical VOID evaluator. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the flight's own attempt directory (carries outputs.jsonl)")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write verdict.json / report.txt")
    parser.add_argument(
        "--sample-manifest", type=Path, default=None,
        help="override the sample-manifest JSON path (default: configs/probes/g0-binding/pslu-sample-devel-n60.json)",
    )
    parser.add_argument(
        "--roster-table", type=Path, default=None,
        help="override the roster-table JSON path (default: configs/probes/g0-binding/pslu-rosters-train-only.json)",
    )
    parser.add_argument(
        "--pphon-verdict", type=Path, default=None,
        help="optional path to an already-written P-PHON verdict.json (soft cross-reference; omit if unavailable)",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock and default configs",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    sample_manifest_path = args.sample_manifest or (repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json")
    roster_table_path = args.roster_table or (repo_root / "configs/probes/g0-binding/pslu-rosters-train-only.json")

    output_dir = Path(args.output_dir)
    verdict_path = output_dir / "verdict.json"
    if verdict_path.exists():
        print(
            f"REFUSED: {verdict_path} already exists -- this suite refuses to run twice against the same "
            "output dir (one-shot read discipline); choose a fresh --output-dir if a genuinely new read is "
            "intended",
            file=sys.stderr,
        )
        return 1

    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()

    try:
        report = build_pkey_report(
            args.attempt_dir,
            lock,
            root,
            sample_manifest_path=sample_manifest_path,
            roster_table_path=roster_table_path,
            pphon_verdict_path=args.pphon_verdict,
        )
    except (PKeyReadError, PKeyFlightError, PsluReadError, PsluFlightError) as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    document = report_to_json(report)
    write_json_artifact(verdict_path, document)
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
