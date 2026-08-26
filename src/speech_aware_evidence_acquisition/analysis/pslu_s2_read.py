"""P-SLU Stage-2 follow-up offline read suite (pinned, pre-registered).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` / ``flight-receipt.json``
(``rails.probes.pslu_s2_flight.run_pslu_s2_flight``'s own row shape) for the
registered probe SAEA-PROBE-pslu-s2-183
(``docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md``),
mechanically evaluating its two independent questions:

- **Q-A** (arm F1): is the control gain format, and does knowledge survive a
  schema-primed floor? Four verdicts, independent, may co-fire:
  FORMAT-FLOOR-CONFIRMED / KNOWLEDGE-BEYOND-FORMAT / FORMAT-IS-EVERYTHING /
  INCONCLUSIVE-QA.
- **Q-B** (arm A1'r): does legal self-scoping work once the parent's
  label-space defect (``docs/readiness/2026-08-18-pslu-verdict.md`` section
  3: "A1' did not fly as designed; it is a duplicate of A2") is fixed?
  Three verdicts: SELF-SCOPING-WORKS / SELF-SCOPING-FAILS /
  INCONCLUSIVE-QB.

Plus a VOID structural/integrity gate (checked first, gates BOTH questions)
mirroring the parent read's own discipline exactly.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_pslu_s2_read.py``). This module is never run against a
real flight attempt directory by the task that wrote it; a later,
separately-registered one-shot read session points ``build_pslu_s2_report``/
the CLI at the real COMPLETED attempt.

REUSE, NOT RE-DERIVATION (mirrors ``analysis.a2t_s2b_read``'s own explicit
discipline section for the SAME reason -- Stage-2 follow-ups reuse their
parent's already-approved primitives, never a second, drifting
implementation):

- ``analysis.pslu_read.RowAnalysis`` / ``ArmAggregate`` /
  ``build_arm_aggregate`` / ``arm_copy_rate`` /
  ``count_induced_substitutions`` / ``_roster_values_for_packet`` /
  ``_recheck_row`` / ``RecheckMismatch`` / ``_row_prompt_text`` /
  ``_parsed_answer_signature`` / ``SilenceSwapComparison`` /
  ``ClauseResult`` / ``_void_clause_recheck`` /
  ``_void_clause_harness_defect`` / ``_void_clause_silence_swap`` /
  ``load_gold_by_sample_id`` / ``RUNTIME_PROHIBITED_NOTE`` -- ALL reused
  directly (duck-typed against ``S2OutputRow`` where the parent's own
  helpers were written against ``OutputRow``: both expose the same
  ``arm``/``sample_id``/``messages``/``metrics``/``consumption`` shape, so
  every one of these helpers works unmodified).
- ``rails.probes.pslu_flight.load_pslu_sample_manifest`` /
  ``load_pslu_rosters`` / ``pslu_supply_packet`` (the SAME frozen roster-
  selection function the flight itself calls, keyed ``arm="A1p"`` for
  A1'r's own phase-2 rows -- never a second reconstruction).
- ``rails.probes.pslu_s2_flight.canonical_scenario_labels`` /
  ``PSLU_S2_ARMS`` / ``F1_ARM`` / ``A1R_PHASE1_ARM`` / ``A1R_ARM`` /
  ``EXPECTED_SILENCE_SWAP_COUNT`` -- never a second, hand-typed spelling of
  an arm name.
- ``rails.probes.pslu_s2_filler.load_filler_lexicon`` /
  ``generate_f1_filler_roster`` / ``f1_filler_supply_packet`` -- the SAME
  deterministic construction the flight used, reconstructed here to cross-
  check what a row's own prompt text actually carries (note 6 below).

CITED constants (never re-derived; both from the parent's own consumed,
registered read -- ``docs/checks/speech-aware-evidence-acquisition/
2026-08-18-pslu-read/verdict.json``, produced by commit ``d8b71a5``, cited
verbatim by ``docs/readiness/2026-08-18-pslu-s2-preregistration-
REGISTERED.md`` section 1): :data:`A0_CITED_SLU_F1` (0.1741),
:data:`A3_CITED_SLU_F1` (0.5961), :data:`A4_CITED_GAIN` (+0.1346, A4 vs A0),
:data:`A2_CITED_GAIN` (+0.2946, A2 vs A0). A0 is NOT re-flown by this probe
-- every "gain vs A0" below is against the CITED constant, never a live
arm.

ENGINEERING-INTERPRETATION NOTES:

1. Q-A's three clauses are evaluated over the LITERAL CITED comparators.
   Given exactly those three registered numbers, "otherwise INCONCLUSIVE-QA"
   is MATHEMATICALLY UNREACHABLE: FORMAT-FLOOR-CONFIRMED's own "met"
   boundary is ``F1 >= A0_CITED + 0.1046 = 0.2787``; KNOWLEDGE-BEYOND-FORMAT's
   own "not met" boundary is ``F1 > A3_CITED - 0.10 = 0.4961``. Since
   ``0.2787 < 0.4961``, EVERY real F1 value satisfies at least one of the
   two clauses (below 0.2787: KNOWLEDGE-BEYOND-FORMAT's gap is always
   >= 0.5961-0.2787 = 0.3174 >= 0.10, so it fires; at/above 0.2787:
   FORMAT-FLOOR-CONFIRMED fires directly) -- there is no F1 value that
   satisfies neither. This is a genuine, checked property of the REGISTERED
   thresholds (not an oversight of this suite), documented here rather than
   silently special-cased. :func:`evaluate_qa` still implements
   INCONCLUSIVE-QA completely and literally (never hard-coded as
   unreachable), and accepts the comparators as OPTIONAL override
   parameters (defaulting to the CITED constants) purely so this module's
   OWN test suite can exercise that branch mechanically with synthetic
   comparators; :func:`build_pslu_s2_report`/the CLI never pass overrides.
2. Copy-rate is reported for both F1 and A1'r but backs NO clause anywhere
   in this evaluator (registration section 2: "Copy-rate is REPORTED but
   carries no clause") -- stricter than the parent read's own note 5, which
   scoped copy-rate to exactly one COPY-TRAP clause; here it scopes it to
   zero clauses, always.
3. Intent accuracy is reported-only for both arms -- no drift guardrail
   (the registration names none for this probe, unlike the parent's -5pp
   guardrail over six arms).
4. VOID is checked first and gates BOTH Q-A and Q-B (mirrors the parent
   read's own "VOID checked first" mechanical order,
   ``docs/readiness/2026-08-18-pslu-verdict.md`` section 1's own table) --
   Q-A and Q-B stay independent of EACH OTHER (registration section 1's own
   "no exclusive lattice"), but a structural/silence-swap integrity failure
   voids the whole read regardless of which hypothesis it concerns. The
   silence-swap clause reuses the parent's OWN unanimity bar (registration
   section 2: "same unanimity VOID bar as the parent, note 7") over A1'r's
   own 3 silence-swap samples -- never F1 (F1 carries no silence-swap rows
   at all).
5. Phase-1 mapping-outcome bookkeeping (chosen label / outcome / fallback)
   is read directly off each A1r-phase1 row's own embedded
   ``closed_set_mapping`` field (``rails.probes.pslu_s2_flight.
   ClosedSetMapping.as_json`` shape) for the headline non-fallback count --
   never re-derived by re-running ``map_predicted_scenario_to_canonical``
   here. The harness-defect check (note 6) DOES independently recompute the
   mapping from the row's own response text, exactly to catch a harness
   that wrote an embedded mapping disagreeing with its own response.
6. Harness-defect checks mirror the parent read's own
   ``_harness_defect_reasons`` shape (flight status, arm/sample
   completeness, duplicate rows, silence-swap row count/arm), PLUS two
   checks with no parent analog: (a) every F1 row's own prompt text must
   equal the SAME fixed filler packet's ``prompt_block``
   (``rails.probes.pslu_s2_filler.f1_filler_supply_packet``, reconstructed
   ONCE from the shipped lexicon + seed, never per-row); (b) every A1'r
   phase-2 row's own prompt text must equal what the frozen
   ``pslu_supply_packet("A1p", scenario=<that row's OWN A1r-phase1
   sibling's re-derived mapping>, ...)`` would produce -- catching BOTH a
   roster-construction drift (mirrors the parent's own note 8) AND an
   embedded-mapping/response-text disagreement (note 5) in one check.
7. Supplied-item count audit (registration section 2's "per-arm supplied-
   item count audit"): per-arm ``n_items`` mean/min/max over the
   RECONSTRUCTED expected packet's own ``dose.n_items`` (F1 is always
   exactly 100; A1'r varies with which scenario's roster was selected, or
   falls back to A2's 55) -- read off the SAME reconstruction the harness-
   defect check (note 6) already performs, never a second computation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..rails.probes.pslu_flight import (
    PsluFlightError,
    PsluRosters,
    load_pslu_rosters,
    load_pslu_sample_manifest,
    pslu_supply_packet,
)
from ..rails.probes.pslu_s2_filler import (
    f1_filler_supply_packet,
    generate_f1_filler_roster,
    load_filler_lexicon,
)
from ..rails.probes.pslu_s2_flight import (
    A1R_ARM,
    A1R_PHASE1_ARM,
    EXPECTED_SILENCE_SWAP_COUNT,
    F1_ARM,
    PSLU_S2_ARMS,
    canonical_scenario_labels,
    map_predicted_scenario_to_canonical,
)
from ..reproduction.slurp_scoring import parse_slu_response, score_slu
from .pslu_read import (
    ArmAggregate,
    ClauseResult,
    RecheckMismatch,
    RowAnalysis,
    RUNTIME_PROHIBITED_NOTE,
    SilenceSwapComparison,
    _parsed_answer_signature,
    _recheck_row,
    _roster_values_for_packet,
    _row_prompt_text,
    _void_clause_harness_defect,
    _void_clause_recheck,
    _void_clause_silence_swap,
    build_arm_aggregate,
    count_induced_substitutions,
    load_gold_by_sample_id,
)

REPORT_SCHEMA = "saea-pslu-s2-read-v1"

# ---------------------------------------------------------------------------
# CITED constants (module docstring): sourced from the PARENT's own consumed
# read, never re-flown/re-measured by this probe.
# ---------------------------------------------------------------------------

A0_CITED_SLU_F1 = 0.1741  # CITED: docs/checks/.../2026-08-18-pslu-read/verdict.json (commit d8b71a5)
A3_CITED_SLU_F1 = 0.5961  # CITED, same source
A4_CITED_GAIN = 0.1346  # CITED, same source (A4 SLU-F1 gain vs A0)
A2_CITED_GAIN = 0.2946  # CITED, same source (A2 SLU-F1 gain vs A0)
SEPARABILITY_BAR = 0.03  # measured noise floor separability bar, verdict.md sections 4/9

# docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md section 1,
# quoted verbatim in each clause's own detail text below.
Q_A_FORMAT_FLOOR_GAIN_MIN = 0.1046  # = A4_CITED_GAIN(0.1346) - SEPARABILITY_BAR(0.03)
Q_A_KNOWLEDGE_BEYOND_GAP_MIN = 0.10  # >= 3x SEPARABILITY_BAR
Q_A_FORMAT_EVERYTHING_GAP_MAX = 0.03  # = SEPARABILITY_BAR

Q_B_NON_FALLBACK_WORKS_MIN = 50  # out of 60
Q_B_NON_FALLBACK_FAILS_MAX = 30  # strictly < 30 out of 60
Q_B_GAIN_WORKS_MIN = 0.2646  # = A2_CITED_GAIN(0.2946) - SEPARABILITY_BAR(0.03)
Q_B_GAIN_FAILS_MAX = 0.1946  # = A2_CITED_GAIN(0.2946) - 0.10

N_SAMPLES = 60


class PsluS2ReadError(RuntimeError):
    """Malformed attempt-dir/binding input for this Stage-2 read -- never
    raised for a legitimate VOID-worthy data shape (that is reported as a
    clause result, not an exception)."""


# ---------------------------------------------------------------------------
# Loading: outputs.jsonl / flight-receipt.json.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class S2OutputRow:
    arm: str
    sample_id: str
    silence_swapped: bool
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: Mapping[str, object]
    # Only populated on an "A1r-phase1" row's own written record -- the
    # rails.probes.pslu_s2_flight.ClosedSetMapping.as_json shape.
    closed_set_mapping: Mapping[str, object] | None

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "S2OutputRow":
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            silence_swapped=bool(document["silence_swapped"]),
            messages=tuple(document["messages"]),
            response_text=str(document["response_text"]),
            metrics=document["metrics"],
            consumption=document["consumption"],
            closed_set_mapping=document.get("closed_set_mapping"),
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[S2OutputRow, ...]:
    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise PsluS2ReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[S2OutputRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PsluS2ReadError(f"{path} line {line_no}: invalid JSON: {error}") from error
        rows.append(S2OutputRow.from_json(document))
    if not rows:
        raise PsluS2ReadError(f"{path}: zero rows")
    return tuple(rows)


def load_flight_status(attempt_dir: Path) -> tuple[str | None, str | None]:
    path = Path(attempt_dir) / "flight-receipt.json"
    if not path.is_file():
        return None, "flight-receipt.json missing"
    document = json.loads(path.read_text(encoding="utf-8"))
    return document.get("status"), document.get("error")


# ---------------------------------------------------------------------------
# Per-row scoring (shared by F1 / A1r-phase1 / A1r).
# ---------------------------------------------------------------------------


def _score_row(row: S2OutputRow, gold) -> RowAnalysis:
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


def _row_mapping_dict(row: S2OutputRow) -> Mapping[str, object]:
    return row.closed_set_mapping or {"predicted_raw": None, "canonical_label": None, "outcome": "unmapped", "fallback": True}


# ---------------------------------------------------------------------------
# Supplied-item audit (module docstring note 7).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SuppliedItemStats:
    n_calls: int
    mean: float
    minimum: int
    maximum: int


def _supplied_item_stats(counts: Sequence[int]) -> SuppliedItemStats:
    if not counts:
        return SuppliedItemStats(n_calls=0, mean=0.0, minimum=0, maximum=0)
    return SuppliedItemStats(n_calls=len(counts), mean=sum(counts) / len(counts), minimum=min(counts), maximum=max(counts))


# ---------------------------------------------------------------------------
# Silence-swap comparison (A1'r only -- module docstring note 4).
# ---------------------------------------------------------------------------


def compare_silence_swap_s2(rows: Sequence[S2OutputRow]) -> tuple[SilenceSwapComparison, ...]:
    real_by_sample: dict[str, S2OutputRow] = {}
    silence_by_sample: dict[str, S2OutputRow] = {}
    for row in rows:
        if row.arm != A1R_ARM:
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
# Structural / harness-defect checks (module docstring note 6).
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    flight_status: str | None,
    flight_error: str | None,
    rows_by_arm: Mapping[str, Sequence[S2OutputRow]],
    silence_rows: Sequence[S2OutputRow],
    sample_ids: Sequence[str],
    unknown_arm_rows: Sequence[S2OutputRow],
    duplicate_keys: Sequence[tuple[str, str, bool]],
    roster_mismatch_reasons: Sequence[str],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if flight_status != "COMPLETED":
        reasons.append(f"flight-receipt status={flight_status!r} (expected 'COMPLETED'); error={flight_error!r}")
    for row in unknown_arm_rows:
        reasons.append(f"unknown arm {row.arm!r} on sample {row.sample_id!r}")
    for key in duplicate_keys:
        reasons.append(f"duplicate row for (arm, sample_id, silence_swapped)={key}")
    id_set = set(sample_ids)
    for arm in PSLU_S2_ARMS:
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
        if row.arm != A1R_ARM:
            reasons.append(f"silence-swap row on sample {row.sample_id!r} is on arm {row.arm!r}, expected {A1R_ARM!r}")
    reasons.extend(roster_mismatch_reasons)
    return tuple(reasons)


# ---------------------------------------------------------------------------
# Q-A / Q-B / VOID evaluators.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VoidVerdict:
    clauses: tuple[ClauseResult, ...]
    voided: bool


def evaluate_void(
    *,
    recheck_mismatches: Sequence[RecheckMismatch],
    harness_defect_reasons: Sequence[str],
    silence_comparisons: Sequence[SilenceSwapComparison],
) -> VoidVerdict:
    void_recheck = _void_clause_recheck(recheck_mismatches)
    void_harness = _void_clause_harness_defect(harness_defect_reasons)
    void_silence = _void_clause_silence_swap(silence_comparisons)
    clauses = (void_silence, void_harness, void_recheck)
    voided = any(clause.verdict == "met" for clause in clauses)
    return VoidVerdict(clauses=clauses, voided=voided)


@dataclass(frozen=True)
class QAVerdict:
    f1_slu_f1: float
    gain_vs_a0: float
    gap_a3_minus_f1: float
    format_floor_confirmed: ClauseResult
    knowledge_beyond_format: ClauseResult
    format_is_everything: ClauseResult
    overall: str


def evaluate_qa(
    f1: ArmAggregate,
    *,
    a0_cited: float = A0_CITED_SLU_F1,
    a3_cited: float = A3_CITED_SLU_F1,
    format_floor_gain_min: float = Q_A_FORMAT_FLOOR_GAIN_MIN,
    knowledge_beyond_gap_min: float = Q_A_KNOWLEDGE_BEYOND_GAP_MIN,
    format_everything_gap_max: float = Q_A_FORMAT_EVERYTHING_GAP_MAX,
) -> QAVerdict:
    """Module docstring note 1: the three clauses are independent and may
    co-fire; overrides exist ONLY for this module's own test suite (never
    used by :func:`build_pslu_s2_report`)."""

    gain = f1.slu_f1_f1 - a0_cited
    gap = a3_cited - f1.slu_f1_f1
    format_floor = ClauseResult(
        "F1 SLU-F1 gain vs CITED A0 >= +0.1046 (= A4's CITED +0.1346 - 0.03)",
        "met" if gain >= format_floor_gain_min else "not_met",
        f"F1 slu_f1={f1.slu_f1_f1:.4f}, gain vs A0_CITED({a0_cited:.4f})={gain:+.4f}, floor={format_floor_gain_min:+.4f}",
    )
    knowledge_beyond = ClauseResult(
        "A3_CITED(0.5961) - F1 SLU-F1 >= 0.10",
        "met" if gap >= knowledge_beyond_gap_min else "not_met",
        f"gap=A3_CITED({a3_cited:.4f}) - F1({f1.slu_f1_f1:.4f})={gap:+.4f}, floor={knowledge_beyond_gap_min:.2f}",
    )
    format_everything = ClauseResult(
        "A3_CITED - F1 SLU-F1 <= 0.03",
        "met" if gap <= format_everything_gap_max else "not_met",
        f"gap={gap:+.4f}, ceiling={format_everything_gap_max:.2f}",
    )
    fired = [
        label
        for label, clause in (
            ("FORMAT-FLOOR-CONFIRMED", format_floor),
            ("KNOWLEDGE-BEYOND-FORMAT", knowledge_beyond),
            ("FORMAT-IS-EVERYTHING", format_everything),
        )
        if clause.verdict == "met"
    ]
    overall = " + ".join(fired) if fired else "INCONCLUSIVE-QA"
    return QAVerdict(
        f1_slu_f1=f1.slu_f1_f1,
        gain_vs_a0=gain,
        gap_a3_minus_f1=gap,
        format_floor_confirmed=format_floor,
        knowledge_beyond_format=knowledge_beyond,
        format_is_everything=format_everything,
        overall=overall,
    )


@dataclass(frozen=True)
class MappingSummary:
    n_calls: int
    non_fallback_count: int
    fallback_count: int
    outcome_counts: Mapping[str, int]
    # scoring-side only (registration: "phase-1 accuracy vs gold scenario --
    # scoring-side only") -- reported, never used by any Q-A/Q-B clause.
    phase1_scenario_accuracy: float


def _mapping_summary(phase1_rows: Sequence[S2OutputRow], phase1_analyses: Sequence[RowAnalysis]) -> MappingSummary:
    outcome_counts: dict[str, int] = {}
    fallback_count = 0
    for row in phase1_rows:
        mapping = _row_mapping_dict(row)
        outcome = str(mapping.get("outcome", "unmapped"))
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
        if bool(mapping.get("fallback", True)):
            fallback_count += 1
    n = len(phase1_rows)
    accuracy = (
        sum(analysis.recomputed_score.scenario_exact for analysis in phase1_analyses) / len(phase1_analyses)
        if phase1_analyses
        else 0.0
    )
    return MappingSummary(
        n_calls=n,
        non_fallback_count=n - fallback_count,
        fallback_count=fallback_count,
        outcome_counts=outcome_counts,
        phase1_scenario_accuracy=accuracy,
    )


@dataclass(frozen=True)
class QBVerdict:
    non_fallback_count: int
    n_calls: int
    gain_vs_a0: float
    self_scoping_works: ClauseResult
    self_scoping_fails: ClauseResult
    overall: str


def evaluate_qb(
    a1r: ArmAggregate,
    mapping: MappingSummary,
    *,
    a0_cited: float = A0_CITED_SLU_F1,
    non_fallback_works_min: int = Q_B_NON_FALLBACK_WORKS_MIN,
    non_fallback_fails_max: int = Q_B_NON_FALLBACK_FAILS_MAX,
    gain_works_min: float = Q_B_GAIN_WORKS_MIN,
    gain_fails_max: float = Q_B_GAIN_FAILS_MAX,
) -> QBVerdict:
    gain = a1r.slu_f1_f1 - a0_cited
    works = ClauseResult(
        f"non-fallback >= {non_fallback_works_min}/60 AND A1'r gain vs CITED A0 >= A2's CITED +0.2946 - 0.03",
        "met" if (mapping.non_fallback_count >= non_fallback_works_min and gain >= gain_works_min) else "not_met",
        f"non_fallback={mapping.non_fallback_count}/{mapping.n_calls} (floor {non_fallback_works_min}), "
        f"gain={gain:+.4f} (floor {gain_works_min:+.4f})",
    )
    fails = ClauseResult(
        f"non-fallback < {non_fallback_fails_max}/60 OR A1'r gain vs CITED A0 < A2's CITED - 0.10",
        "met" if (mapping.non_fallback_count < non_fallback_fails_max or gain < gain_fails_max) else "not_met",
        f"non_fallback={mapping.non_fallback_count}/{mapping.n_calls} (ceiling <{non_fallback_fails_max}), "
        f"gain={gain:+.4f} (ceiling <{gain_fails_max:+.4f})",
    )
    if works.verdict == "met":
        overall = "SELF-SCOPING-WORKS"
    elif fails.verdict == "met":
        overall = "SELF-SCOPING-FAILS"
    else:
        overall = "INCONCLUSIVE-QB"
    return QBVerdict(
        non_fallback_count=mapping.non_fallback_count,
        n_calls=mapping.n_calls,
        gain_vs_a0=gain,
        self_scoping_works=works,
        self_scoping_fails=fails,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PsluS2ReadReport:
    attempt_dir: Path
    flight_status: str | None
    flight_error: str | None
    aggregates: Mapping[str, ArmAggregate]
    mapping_summary: MappingSummary
    supplied_item_stats: Mapping[str, SuppliedItemStats]
    silence_comparisons: tuple[SilenceSwapComparison, ...]
    recheck_mismatches: tuple[RecheckMismatch, ...]
    harness_defect_reasons: tuple[str, ...]
    void_verdict: VoidVerdict
    qa_verdict: QAVerdict
    qb_verdict: QBVerdict

    @property
    def overall_qa(self) -> str:
        return "VOID" if self.void_verdict.voided else self.qa_verdict.overall

    @property
    def overall_qb(self) -> str:
        return "VOID" if self.void_verdict.voided else self.qb_verdict.overall


def build_pslu_s2_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    sample_manifest_path: Path,
    roster_table_path: Path,
    filler_lexicon_path: Path,
) -> PsluS2ReadReport:
    attempt_dir = Path(attempt_dir)
    rows = load_attempt_rows(attempt_dir)
    flight_status, flight_error = load_flight_status(attempt_dir)

    manifest = load_pslu_sample_manifest(sample_manifest_path)
    rosters: PsluRosters = load_pslu_rosters(roster_table_path)
    sample_ids = manifest.sample_ids
    canonical_labels = canonical_scenario_labels(rosters)

    lexicon = load_filler_lexicon(filler_lexicon_path)
    filler_entries = generate_f1_filler_roster(lexicon)
    f1_packet = f1_filler_supply_packet(filler_entries)

    gold_by_id = load_gold_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED (reused)

    rows_by_arm: dict[str, list[S2OutputRow]] = {arm: [] for arm in PSLU_S2_ARMS}
    silence_rows: list[S2OutputRow] = []
    unknown_arm_rows: list[S2OutputRow] = []
    seen_keys: set[tuple[str, str, bool]] = set()
    duplicate_keys: list[tuple[str, str, bool]] = []
    for row in rows:
        key = (row.arm, row.sample_id, row.silence_swapped)
        if key in seen_keys:
            duplicate_keys.append(key)
            continue
        seen_keys.add(key)
        if row.arm not in PSLU_S2_ARMS:
            unknown_arm_rows.append(row)
            continue
        if row.silence_swapped:
            silence_rows.append(row)
        else:
            rows_by_arm[row.arm].append(row)

    recheck_mismatches: list[RecheckMismatch] = []
    roster_mismatch_reasons: list[str] = []
    supplied_item_counts: dict[str, list[int]] = {F1_ARM: [], A1R_ARM: []}
    analyses_by_arm: dict[str, tuple[RowAnalysis, ...]] = {}

    for arm in (F1_ARM, A1R_ARM):
        analyses: list[RowAnalysis] = []
        for row in rows_by_arm[arm]:
            gold = gold_by_id.get(row.sample_id)
            if gold is None:
                continue  # reported separately as a missing-manifest-id harness defect below
            analysis = _score_row(row, gold)
            recheck_mismatches.extend(analysis.recheck_mismatches)

            if arm == F1_ARM:
                expected_packet = f1_packet
            else:
                # Note 6: independently RE-DERIVE the mapping from the
                # sibling phase-1 row's OWN response text -- never trust the
                # embedded closed_set_mapping field for reconstruction, so a
                # harness bug that writes a mismatched embedded mapping is
                # actually caught here.
                phase1_row = next(
                    (r for r in rows_by_arm[A1R_PHASE1_ARM] if r.sample_id == row.sample_id), None
                )
                if phase1_row is not None:
                    predicted, _action, _entities, parsed = parse_slu_response(phase1_row.response_text)
                    rederived = map_predicted_scenario_to_canonical(
                        predicted if parsed else None, canonical_labels
                    )
                    scenario = rederived.canonical_label
                else:
                    scenario = None
                try:
                    expected_packet = pslu_supply_packet("A1p", scenario=scenario, rosters=rosters)
                except PsluFlightError as error:
                    raise PsluS2ReadError(
                        f"arm {arm!r} sample {row.sample_id!r}: cannot reconstruct roster: {error}"
                    ) from error

            expected_text = expected_packet.prompt_block
            actual_text = _row_prompt_text(row)
            if expected_text != actual_text:
                roster_mismatch_reasons.append(
                    f"arm {arm} sample {row.sample_id}: supplied prompt text does not match the "
                    "reconstructed roster/filler packet"
                )
            supplied_item_counts[arm].append(expected_packet.dose.n_items)
            roster_values = _roster_values_for_packet(expected_packet)
            induced = count_induced_substitutions(analysis.predicted_entities, gold.entities, roster_values)
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

    phase1_analyses: list[RowAnalysis] = []
    for row in rows_by_arm[A1R_PHASE1_ARM]:
        gold = gold_by_id.get(row.sample_id)
        if gold is None:
            continue
        analysis = _score_row(row, gold)
        recheck_mismatches.extend(analysis.recheck_mismatches)
        phase1_analyses.append(analysis)
    analyses_by_arm[A1R_PHASE1_ARM] = tuple(phase1_analyses)

    for row in silence_rows:
        gold = gold_by_id.get(row.sample_id)
        if gold is None:
            continue
        recheck_mismatches.extend(_score_row(row, gold).recheck_mismatches)

    aggregates = {arm: build_arm_aggregate(arm, analyses_by_arm[arm]) for arm in PSLU_S2_ARMS}
    supplied_item_stats = {arm: _supplied_item_stats(supplied_item_counts[arm]) for arm in (F1_ARM, A1R_ARM)}
    mapping_summary = _mapping_summary(rows_by_arm[A1R_PHASE1_ARM], phase1_analyses)

    harness_defect_reasons = _harness_defect_reasons(
        flight_status=flight_status,
        flight_error=flight_error,
        rows_by_arm=rows_by_arm,
        silence_rows=silence_rows,
        sample_ids=sample_ids,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_keys=duplicate_keys,
        roster_mismatch_reasons=roster_mismatch_reasons,
    )

    silence_comparisons = compare_silence_swap_s2(list(rows_by_arm[A1R_ARM]) + silence_rows)

    void_verdict = evaluate_void(
        recheck_mismatches=recheck_mismatches,
        harness_defect_reasons=harness_defect_reasons,
        silence_comparisons=silence_comparisons,
    )
    qa_verdict = evaluate_qa(aggregates[F1_ARM])
    qb_verdict = evaluate_qb(aggregates[A1R_ARM], mapping_summary)

    return PsluS2ReadReport(
        attempt_dir=attempt_dir,
        flight_status=flight_status,
        flight_error=flight_error,
        aggregates=aggregates,
        mapping_summary=mapping_summary,
        supplied_item_stats=supplied_item_stats,
        silence_comparisons=silence_comparisons,
        recheck_mismatches=tuple(recheck_mismatches),
        harness_defect_reasons=harness_defect_reasons,
        void_verdict=void_verdict,
        qa_verdict=qa_verdict,
        qb_verdict=qb_verdict,
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
        "slu_f1": {
            "precision": aggregate.slu_f1_precision,
            "recall": aggregate.slu_f1_recall,
            "f1": aggregate.slu_f1_f1,
        },
        "slot_f1_exact": {
            "precision": aggregate.slot_f1_exact_precision,
            "recall": aggregate.slot_f1_exact_recall,
            "f1": aggregate.slot_f1_exact_f1,
            "tp_sum": aggregate.slot_f1_exact_tp_sum,
        },
        "entity_tp_fp_fn": {
            "tp": aggregate.aggregate_score.slot_f1_exact_tp,
            "fp": aggregate.aggregate_score.slot_f1_exact_fp,
            "fn": aggregate.aggregate_score.slot_f1_exact_fn,
        },
        "intent_accuracy": aggregate.intent_accuracy,
        "copy_rate": aggregate.copy_rate,
        "copy_records": aggregate.copy_records,
        "copy_records_total": aggregate.copy_records_total,
        "induced_substitution_count": aggregate.induced_substitution_count,
    }


def _supplied_item_stats_json(stats: SuppliedItemStats) -> dict[str, object]:
    return {"n_calls": stats.n_calls, "mean": stats.mean, "min": stats.minimum, "max": stats.maximum}


def report_to_json(report: PsluS2ReadReport) -> dict[str, object]:
    return {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "flight_error": report.flight_error,
        "aggregates": {arm: _aggregate_json(agg) for arm, agg in report.aggregates.items()},
        "supplied_item_audit": {
            arm: _supplied_item_stats_json(stats) for arm, stats in report.supplied_item_stats.items()
        },
        "mapping_summary": {
            "n_calls": report.mapping_summary.n_calls,
            "non_fallback_count": report.mapping_summary.non_fallback_count,
            "fallback_count": report.mapping_summary.fallback_count,
            "outcome_counts": dict(report.mapping_summary.outcome_counts),
            "phase1_scenario_accuracy": report.mapping_summary.phase1_scenario_accuracy,
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
        "void": {
            "clauses": [_clause_json(c) for c in report.void_verdict.clauses],
            "voided": report.void_verdict.voided,
        },
        "qa": {
            "f1_slu_f1": report.qa_verdict.f1_slu_f1,
            "gain_vs_a0": report.qa_verdict.gain_vs_a0,
            "gap_a3_minus_f1": report.qa_verdict.gap_a3_minus_f1,
            "format_floor_confirmed": _clause_json(report.qa_verdict.format_floor_confirmed),
            "knowledge_beyond_format": _clause_json(report.qa_verdict.knowledge_beyond_format),
            "format_is_everything": _clause_json(report.qa_verdict.format_is_everything),
            "overall": report.overall_qa,
        },
        "qb": {
            "non_fallback_count": report.qb_verdict.non_fallback_count,
            "n_calls": report.qb_verdict.n_calls,
            "gain_vs_a0": report.qb_verdict.gain_vs_a0,
            "self_scoping_works": _clause_json(report.qb_verdict.self_scoping_works),
            "self_scoping_fails": _clause_json(report.qb_verdict.self_scoping_fails),
            "overall": report.overall_qb,
        },
    }


def render_report(report: PsluS2ReadReport) -> str:
    lines = [
        "P-SLU Stage-2 pinned offline read (docs/readiness/2026-08-18-pslu-s2-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r} (error={report.flight_error!r})",
        "",
        "Per-arm aggregates",
    ]
    header = f"  {'arm':<14}{'n':>4}{'slu_f1':>9}{'slot_f1x':>10}{'intent_acc':>12}{'copy_rate':>11}{'induced':>9}"
    lines.append(header)
    for arm in PSLU_S2_ARMS:
        agg = report.aggregates[arm]
        lines.append(
            f"  {arm:<14}{agg.n_samples:>4}{agg.slu_f1_f1:>9.4f}{agg.slot_f1_exact_f1:>10.4f}"
            f"{agg.intent_accuracy:>12.4f}{agg.copy_rate:>11.4f}{agg.induced_substitution_count:>9}"
        )
    lines.append("")

    lines.append("Supplied-item audit (F1 / A1'r)")
    for arm, stats in report.supplied_item_stats.items():
        lines.append(f"  {arm}: n_calls={stats.n_calls} mean={stats.mean:.2f} min={stats.minimum} max={stats.maximum}")
    lines.append("")

    lines.append("Phase-1 (A1r-phase1) mapping summary")
    m = report.mapping_summary
    lines.append(f"  non_fallback={m.non_fallback_count}/{m.n_calls}  fallback={m.fallback_count}/{m.n_calls}")
    lines.append(f"  outcome_counts={dict(m.outcome_counts)}")
    lines.append(f"  phase1_scenario_accuracy (scoring-side only, reported)={m.phase1_scenario_accuracy:.4f}")
    lines.append("")

    lines.append("Silence-swap comparison (3 A1'r silence variants vs their real-audio counterparts)")
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
    lines.append("")

    lines.append(f"VOID (checked FIRST, gates BOTH Q-A and Q-B): {'MET' if report.void_verdict.voided else 'not met'}")
    for clause in report.void_verdict.clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append("")

    qa = report.qa_verdict
    lines.append("Q-A (arm F1: is the control gain format, does knowledge survive the schema-primed floor?)")
    for clause in (qa.format_floor_confirmed, qa.knowledge_beyond_format, qa.format_is_everything):
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"  OVERALL Q-A: {report.overall_qa}")
    lines.append("")

    qb = report.qb_verdict
    lines.append("Q-B (arm A1'r: does legal self-scoping work once the label-space defect is fixed?)")
    for clause in (qb.self_scoping_works, qb.self_scoping_fails):
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"  OVERALL Q-B: {report.overall_qb}")
    lines.append("")

    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pslu-s2-read",
        description=(
            "P-SLU Stage-2 follow-up pinned offline read suite: official SLU-F1/slot_f1_exact, "
            "entity TP/FP/FN, intent accuracy (reported), copy-rate (reported, no clause), "
            "induced-substitution count, supplied-item audit, phase-1 mapping summary, "
            "silence-swap comparison, and the mechanical Q-A/Q-B/VOID evaluators. Model-free, "
            "read-only; never opens a model session."
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
        "--filler-lexicon", type=Path, default=None,
        help="override the filler-lexicon JSON path (default: configs/probes/g0-binding/pslu-s2-filler-lexicon.json)",
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
    from .pslu_read import PsluReadError

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    sample_manifest_path = args.sample_manifest or (repo_root / "configs/probes/g0-binding/pslu-sample-devel-n60.json")
    roster_table_path = args.roster_table or (repo_root / "configs/probes/g0-binding/pslu-rosters-train-only.json")
    filler_lexicon_path = args.filler_lexicon or (repo_root / "configs/probes/g0-binding/pslu-s2-filler-lexicon.json")

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
        report = build_pslu_s2_report(
            args.attempt_dir,
            lock,
            root,
            sample_manifest_path=sample_manifest_path,
            roster_table_path=roster_table_path,
            filler_lexicon_path=filler_lexicon_path,
        )
    except (PsluS2ReadError, PsluReadError, PsluFlightError) as error:
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
