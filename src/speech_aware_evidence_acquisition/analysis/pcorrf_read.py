"""P-CORR-F offline read suite (pinned, pre-registered):
``docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md`` sections
3 (verdicts / mandatory dual measurement) and 4 (legality: "gold is
scoring-side ONLY inside this read module").

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory. It scores the P-CORR-F flight's OWN
already-written ``outputs.jsonl`` (``rails.probes.pcorrf_flight.
run_pcorrf_flight``'s own write shape) through the SAME frozen official
scorer every other consumer of this carrier uses (``reproduction.
slurp_scoring.score_slu``/``parse_slu_response``), plus the CONSUMED P-SLU
A0 baseline (``rails.probes.pcorrf_flight.harvest_a0_emitted_slots``,
already gold-free, reused directly -- this module is the one place gold
enters the picture, and only for SCORING, never construction).

Two pre-declared clauses plus one descriptive arm plus a MANDATORY dual
measurement (preregistration section 3):

- **Q-1 mechanism**: Delta_1 = SLU-F1(W1) - SLU-F1(W2), a per-sample paired
  cluster bootstrap (``analysis.bootstrap``, N=10,000, seed 20260807, 90%
  CI, clustered on the 60 sample ids) -- CORRECTIVE-PERCEPT if
  Delta_1 >= +0.03 AND the CI lower bound > 0; CORRECTIVE-INERT if the
  ENTIRE CI lies within [-0.03, +0.03]; else INCONCLUSIVE-CORR. Mirrors the
  P-TRAP/P-KEY CI-gated pattern exactly (:func:`evaluate_q1`).
- **Q-2 dose efficiency**: Delta_2 = SLU-F1(W3) - the CITED A3 constant
  0.5961280580450439 (pinned VERBATIM, the SAME literal ``analysis.
  ptrap_read.CONSUMED_A3_SLU_F1`` cites -- never re-read live). ENGINEERING-
  INTERPRETATION NOTE: the registration's own Q-2 clause text ("Delta_2 >=
  -0.03 ... ; Delta_2 <= -0.10 ...") never mentions a CI gate the way Q-1's
  own clause explicitly does ("and CI lower > 0") -- the bootstrap CI
  described at the top of section 3 is computed and reported for Delta_2
  too (:func:`compute_q2_bootstrap`), but :func:`evaluate_q2`'s own
  DOSE-EFFICIENT/DOSE-INSUFFICIENT/INCONCLUSIVE-DOSE verdict is gated on
  the POINT value ONLY, per the literal registered clause text -- a
  documented, reviewable choice, not a silent guess. The ``+/-0.013``
  cross-session drift bound (:data:`CROSS_SESSION_DRIFT_BOUND`, the SAME
  measured duplicate-condition floor P-TRAP/P-SLU-S2 already cite) is
  carried alongside the verdict in the report (registration's own
  instruction), never used as a formal gate.
- **W4 descriptive dose curve**: carries no clause (registration verbatim)
  -- reports SLU-F1 and the widening entry-count distribution only.
- **MANDATORY dual measurement** (registration: "P-CORR-F is P-TRAP with
  the sign flipped"): for every arm, RECOVERY (gold slots newly emitted vs
  the CONSUMED A0 baseline -- :func:`compute_recovery`, gold scoring-side
  only) and CONTAMINATION (non-gold corrective entries actually emitted --
  :func:`compute_contamination`, reusing ``analysis.ptrap_read.
  response_captures_trap`` PER CORRECTIVE ENTRY, the mission's own
  instruction: "using ptrap_read's own capture detector"). Both are
  reported for every arm; contamination is load-bearing for W4 (82
  non-gold entries cited in the registration).

The pre-read reachability statement (:func:`compute_reachability_statement`,
mandatory, registration section 3): per-arm entry-count distribution, the
K=0 sample count under L1 (shared by W1/W3), and the max-attainable
recovery from each arm's OWN supplied corrective-entry set (never
conflated with the A3 base's own separately-cited 29/89 ceiling -- module
docstring's own reconciliation: W1 and W3 share the IDENTICAL L1 corrective
addition, so they share the identical corrective-only ceiling).

Guardrails (descriptive only, never verdict-gating -- mirrors ``analysis.
ptrap_read``'s own precedent): induced substitutions (``analysis.pslu_read.
count_induced_substitutions``, reused verbatim), copy-rate
(``analysis.pslu_read.arm_copy_rate``, reused verbatim -- duck-typed on
``row.consumption``), parse/empty rates, per-arm ``slot_f1_exact``,
per-scenario breakdown.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..core.retrieval import normalize_term
from ..rails.probes import pcorrf_flight as pf
from ..rails.probes.pcorrf_flight import PCORRF_ARMS, W1_ARM, W2_ARM, W3_ARM, W4_ARM
from ..rails.probes.pslu_flight import load_pslu_rosters, load_pslu_sample_manifest
from ..reproduction.slurp_scoring import SlotEntity, SluScore, parse_slu_response, score_slu
from .bootstrap import (
    BootstrapResult,
    DEFAULT_CI_LEVEL as BOOTSTRAP_CI_LEVEL,
    DEFAULT_N_REPLICATES as BOOTSTRAP_N_REPLICATES,
    DEFAULT_SEED as BOOTSTRAP_SEED,
    paired_cluster_bootstrap,
)
from .ptrap_read import response_captures_trap
from .pslu_read import (
    RUNTIME_PROHIBITED_NOTE,
    _aggregate_slu_score,
    arm_copy_rate,
    count_induced_substitutions,
    load_flight_status,
    load_gold_by_sample_id,
)

REPORT_SCHEMA = "saea-pcorrf-read-v1"

# docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md section 3,
# quoted verbatim in each clause's own detail text below.
Q1_MIN_DELTA = 0.03
Q1_INERT_BAND = 0.03

# CITED constant (module docstring): the SAME literal analysis.ptrap_read.
# CONSUMED_A3_SLU_F1 cites -- docs/checks/speech-aware-evidence-
# acquisition/2026-08-18-pslu-read/verdict.json, aggregates.A3.slu_f1.f1.
# Frozen here VERBATIM, never re-read live.
CITED_A3_SLU_F1 = 0.5961280580450439

Q2_EFFICIENT_MIN_DELTA = -0.03
Q2_INSUFFICIENT_MAX_DELTA = -0.10

# The measured duplicate-condition floor (P-SLU-S2/P-TRAP's own cited
# figure) -- carried in the report alongside the Q-2 verdict, module
# docstring: never a formal gate.
CROSS_SESSION_DRIFT_BOUND = 0.013

ClauseVerdict = Literal["met", "not_met"]


class PCorrFReadError(RuntimeError):
    """Malformed attempt-dir/binding input for this read -- never raised for
    a legitimate INCONCLUSIVE-worthy data shape (reported as a clause
    result, not an exception)."""


# ---------------------------------------------------------------------------
# Loading the P-CORR-F flight's own attempt directory.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PCorrFOutputRow:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: Mapping[str, object]
    k: int
    corrective_entries: tuple[Mapping[str, object], ...]

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "PCorrFOutputRow":
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            messages=tuple(document["messages"]),
            response_text=str(document["response_text"]),
            metrics=document["metrics"],
            consumption=document["consumption"],
            k=int(document["k"]),
            corrective_entries=tuple(document.get("corrective_entries", ())),
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[PCorrFOutputRow, ...]:
    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise PCorrFReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[PCorrFOutputRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PCorrFReadError(f"{path} line {line_no}: invalid JSON: {error}") from error
        rows.append(PCorrFOutputRow.from_json(document))
    if not rows:
        raise PCorrFReadError(f"{path}: zero rows")
    return tuple(rows)


# ---------------------------------------------------------------------------
# Per-row scoring.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RowScore:
    row: PCorrFOutputRow
    predicted_entities: tuple[SlotEntity, ...]
    parsed: bool
    score: SluScore


def _score_row(row: PCorrFOutputRow, gold) -> RowScore:
    predicted_scenario, predicted_action, predicted_entities, parsed = parse_slu_response(row.response_text)
    predicted_entities = tuple(predicted_entities)
    score = score_slu(
        gold_scenario=gold.scenario,
        gold_action=gold.action,
        gold_entities=gold.entities,
        predicted_scenario=predicted_scenario,
        predicted_action=predicted_action,
        predicted_entities=predicted_entities,
    )
    return RowScore(row=row, predicted_entities=predicted_entities, parsed=parsed, score=score)


# ---------------------------------------------------------------------------
# Mandatory dual measurement (module docstring: "P-CORR-F is P-TRAP with
# the sign flipped").
# ---------------------------------------------------------------------------


def _exact_matched_gold_indices(predicted: Sequence[SlotEntity], gold: Sequence[SlotEntity]) -> frozenset[int]:
    """The SAME exact-match greedy algorithm ``reproduction.slurp_scoring.
    _exact_counts`` uses for its own TP count -- returns the matched gold
    entities' own INDICES into ``gold`` (never the entity VALUES
    themselves, and never a plain frozenset-of-values): SLURP gold can
    legitimately carry two entities with the IDENTICAL ``(type, filler)``
    pair (e.g. two mentions of the same value), and a value-keyed set would
    silently collapse them to one, undercounting recovery. Index-keying
    preserves that multiplicity exactly the way the official TP count
    does."""

    remaining_indices = list(range(len(gold)))
    matched_indices: list[int] = []
    for entity in predicted:
        for position, gold_index in enumerate(remaining_indices):
            if gold[gold_index] == entity:
                matched_indices.append(gold_index)
                del remaining_indices[position]
                break
    return frozenset(matched_indices)


def compute_recovery(
    arm_predicted: Sequence[SlotEntity], a0_predicted: Sequence[SlotEntity], gold: Sequence[SlotEntity]
) -> tuple[int, tuple[SlotEntity, ...]]:
    """RECOVERY (module docstring): gold slots this arm's own response
    matches EXACTLY that the CONSUMED A0 baseline did NOT match for the
    SAME sample -- ``(count, the newly-matched gold entities themselves)``.
    Index-based under the hood (:func:`_exact_matched_gold_indices`) so a
    duplicate ``(type, filler)`` gold pair is never undercounted."""

    gold = tuple(gold)
    a0_matched = _exact_matched_gold_indices(a0_predicted, gold)
    arm_matched = _exact_matched_gold_indices(arm_predicted, gold)
    newly_indices = arm_matched - a0_matched
    newly_entities = tuple(gold[index] for index in sorted(newly_indices))
    return len(newly_indices), newly_entities


def compute_contamination(
    predicted_entities: Sequence[SlotEntity],
    corrective_entries: Sequence[Mapping[str, object]],
    gold_values: frozenset[str],
) -> tuple[int, tuple[Mapping[str, object], ...]]:
    """CONTAMINATION (module docstring): non-gold corrective entries this
    row's own response actually EMITTED, using ``analysis.ptrap_read.
    response_captures_trap`` PER CORRECTIVE ENTRY (mission instruction:
    "using ptrap_read's own capture detector") -- a captured entry whose
    normalized filler is NOT among ``gold_values`` counts as contamination."""

    captured = [entry for entry in corrective_entries if response_captures_trap(predicted_entities, (entry,))]
    non_gold = tuple(
        entry for entry in captured if normalize_term(str(entry.get("filler", ""))) not in gold_values
    )
    return len(non_gold), non_gold


@dataclass(frozen=True)
class DualMeasurementRow:
    arm: str
    sample_id: str
    recovery_count: int
    contamination_count: int


@dataclass(frozen=True)
class ArmDualMeasurement:
    arm: str
    recovery_total: int
    contamination_total: int
    per_sample: tuple[DualMeasurementRow, ...]


# ---------------------------------------------------------------------------
# Mandatory pre-read reachability statement (registration section 3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntryCountDistribution:
    n_samples: int
    mean: float
    max: int
    min: int
    k_zero_count: int


def _entry_count_distribution(counts: Sequence[int]) -> EntryCountDistribution:
    if not counts:
        return EntryCountDistribution(n_samples=0, mean=0.0, max=0, min=0, k_zero_count=0)
    return EntryCountDistribution(
        n_samples=len(counts),
        mean=sum(counts) / len(counts),
        max=max(counts),
        min=min(counts),
        k_zero_count=sum(1 for c in counts if c == 0),
    )


@dataclass(frozen=True)
class ReachabilityStatement:
    per_arm_entry_count_distribution: Mapping[str, EntryCountDistribution]
    l1_k_zero_samples: int  # shared by W1/W3 (module docstring)
    total_gold_slots: int
    max_attainable_recovery_by_arm: Mapping[str, int]
    detail: str


def compute_reachability_statement(
    rows_by_arm: Mapping[str, Sequence[PCorrFOutputRow]], gold_by_sample_id: Mapping[str, object]
) -> ReachabilityStatement:
    distributions = {
        arm: _entry_count_distribution([row.k for row in rows]) for arm, rows in rows_by_arm.items()
    }
    l1_k_zero = distributions.get(W1_ARM, EntryCountDistribution(0, 0.0, 0, 0, 0)).k_zero_count
    total_gold_slots = sum(len(record.entities) for record in gold_by_sample_id.values())

    max_attainable: dict[str, int] = {}
    for arm, rows in rows_by_arm.items():
        count = 0
        for row in rows:
            gold = gold_by_sample_id.get(row.sample_id)
            if gold is None:
                continue
            supplied_pairs = {
                (str(entry.get("type", "")), normalize_term(str(entry.get("filler", ""))))
                for entry in row.corrective_entries
            }
            for gold_entity in gold.entities:
                if (gold_entity.type, normalize_term(gold_entity.filler)) in supplied_pairs:
                    count += 1
        max_attainable[arm] = count

    detail = (
        f"L1 K=0 samples (W1/W3, shared): {l1_k_zero}/{sum(d.n_samples for d in [distributions.get(W1_ARM, _entry_count_distribution([]))])}. "
        f"total gold slots across the frozen set: {total_gold_slots}. "
        "max attainable recovery = gold slots present in each arm's own supplied corrective-entry set "
        "(never conflated with the A3 base's own separately-cited ceiling): "
        + "; ".join(f"{arm}={max_attainable.get(arm, 0)}/{total_gold_slots}" for arm in PCORRF_ARMS)
    )
    return ReachabilityStatement(
        per_arm_entry_count_distribution=distributions,
        l1_k_zero_samples=l1_k_zero,
        total_gold_slots=total_gold_slots,
        max_attainable_recovery_by_arm=max_attainable,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Guardrails.
# ---------------------------------------------------------------------------


def _roster_values_for_row(base_roster_values: frozenset[str], row: PCorrFOutputRow) -> tuple[str, ...]:
    base = frozenset() if row.arm == W3_ARM else base_roster_values
    corrective_values = {normalize_term(str(entry.get("filler", ""))) for entry in row.corrective_entries}
    return tuple(sorted(base | corrective_values))


@dataclass(frozen=True)
class ScenarioBreakdown:
    scenario: str
    n_samples: int
    slu_f1: float


@dataclass(frozen=True)
class ArmGuardrails:
    arm: str
    n_samples: int
    slu_f1: float
    slot_f1_exact: float
    parse_rate: float
    empty_rate: float
    induced_substitution_total: int
    copy_rate: float
    copy_records: int
    copy_records_total: int
    scenario_breakdown: tuple[ScenarioBreakdown, ...]


def _build_arm_guardrails(
    arm: str,
    row_scores: Sequence[RowScore],
    *,
    base_roster_values: frozenset[str],
    gold_scenario_by_sample: Mapping[str, str],
) -> ArmGuardrails:
    n = len(row_scores)
    scores = [rs.score for rs in row_scores]
    aggregate = _aggregate_slu_score(scores)
    slu_f1 = aggregate.slu_f1[2]
    slot_f1_exact = aggregate.slot_f1_exact[2]
    parsed_count = sum(1 for rs in row_scores if rs.parsed)
    parse_rate = parsed_count / n if n else 0.0
    # Induced substitutions need each row's own gold entities, which this
    # function does not receive -- build_pcorrf_report computes the real
    # per-arm total in a SEPARATE pass (it has gold_by_id in scope) and
    # patches this placeholder 0 in afterward. Kept at 0 here rather than
    # threaded through as an extra parameter, since every caller of this
    # function today is that one patch-afterward pass.
    induced_total = 0
    scenario_scores: dict[str, list[SluScore]] = {}
    for rs in row_scores:
        scenario = gold_scenario_by_sample.get(rs.row.sample_id, "unknown")
        scenario_scores.setdefault(scenario, []).append(rs.score)
    scenario_breakdown = tuple(
        ScenarioBreakdown(
            scenario=scenario, n_samples=len(scenario_score_list), slu_f1=_aggregate_slu_score(scenario_score_list).slu_f1[2]
        )
        for scenario, scenario_score_list in sorted(scenario_scores.items())
    )
    copy_rate, copy_records, copy_total = arm_copy_rate([rs.row for rs in row_scores])
    return ArmGuardrails(
        arm=arm,
        n_samples=n,
        slu_f1=slu_f1,
        slot_f1_exact=slot_f1_exact,
        parse_rate=parse_rate,
        empty_rate=1.0 - parse_rate,
        induced_substitution_total=induced_total,
        copy_rate=copy_rate,
        copy_records=copy_records,
        copy_records_total=copy_total,
        scenario_breakdown=scenario_breakdown,
    )


# ---------------------------------------------------------------------------
# Bootstrap-based verdicts (Q-1 CI-gated, Q-2 point-gated -- module
# docstring's own recorded interpretation).
# ---------------------------------------------------------------------------


def _slu_f1_for_ids(sample_ids: Sequence[str], scores_by_sample: Mapping[str, SluScore]) -> float:
    aggregated = _aggregate_slu_score([scores_by_sample[sample_id] for sample_id in sample_ids])
    return aggregated.slu_f1[2]


def compute_q1_bootstrap(
    *,
    w1_scores_by_sample: Mapping[str, SluScore],
    w2_scores_by_sample: Mapping[str, SluScore],
    common_denominator: Sequence[str],
    n_replicates: int = BOOTSTRAP_N_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = BOOTSTRAP_CI_LEVEL,
) -> BootstrapResult:
    ids = tuple(common_denominator)
    if not ids:
        raise PCorrFReadError("compute_q1_bootstrap: empty common denominator")

    def statistic(sample_ids: Sequence[str]) -> float:
        return _slu_f1_for_ids(sample_ids, w1_scores_by_sample) - _slu_f1_for_ids(sample_ids, w2_scores_by_sample)

    return paired_cluster_bootstrap(sample_ids=ids, statistic=statistic, n_replicates=n_replicates, seed=seed, ci_level=ci_level)


def compute_q2_bootstrap(
    *,
    w3_scores_by_sample: Mapping[str, SluScore],
    common_denominator: Sequence[str],
    cited_a3: float = CITED_A3_SLU_F1,
    n_replicates: int = BOOTSTRAP_N_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = BOOTSTRAP_CI_LEVEL,
) -> BootstrapResult:
    ids = tuple(common_denominator)
    if not ids:
        raise PCorrFReadError("compute_q2_bootstrap: empty common denominator")

    def statistic(sample_ids: Sequence[str]) -> float:
        return _slu_f1_for_ids(sample_ids, w3_scores_by_sample) - cited_a3

    return paired_cluster_bootstrap(sample_ids=ids, statistic=statistic, n_replicates=n_replicates, seed=seed, ci_level=ci_level)


@dataclass(frozen=True)
class ClauseResult:
    clause_text: str
    verdict: ClauseVerdict
    detail: str


@dataclass(frozen=True)
class Q1Verdict:
    delta1: float
    bootstrap: BootstrapResult
    corrective_percept: ClauseResult
    corrective_inert: ClauseResult
    overall: str


def evaluate_q1(delta1: float, bootstrap: BootstrapResult) -> Q1Verdict:
    """CORRECTIVE-PERCEPT / CORRECTIVE-INERT / INCONCLUSIVE-CORR
    (preregistration section 3, verbatim; module docstring)."""

    percept_met = delta1 >= Q1_MIN_DELTA and bootstrap.ci_low > 0.0
    corrective_percept = ClauseResult(
        f"Delta_1 >= +{Q1_MIN_DELTA:.2f} AND bootstrap CI lower bound > 0",
        "met" if percept_met else "not_met",
        f"delta1={delta1:+.4f} (floor +{Q1_MIN_DELTA:.2f}), "
        f"CI=[{bootstrap.ci_low:+.4f}, {bootstrap.ci_high:+.4f}] (sigma_hat={bootstrap.sigma_hat:.4f})",
    )
    inert_met = bootstrap.contains(-Q1_INERT_BAND, Q1_INERT_BAND)
    corrective_inert = ClauseResult(
        f"the ENTIRE {bootstrap.ci_level:.0%} bootstrap CI lies within [-{Q1_INERT_BAND:.2f}, +{Q1_INERT_BAND:.2f}]",
        "met" if inert_met else "not_met",
        f"CI=[{bootstrap.ci_low:+.4f}, {bootstrap.ci_high:+.4f}]",
    )
    if corrective_percept.verdict == "met":
        overall = "CORRECTIVE-PERCEPT"
    elif corrective_inert.verdict == "met":
        overall = "CORRECTIVE-INERT"
    else:
        overall = "INCONCLUSIVE-CORR"
    return Q1Verdict(
        delta1=delta1, bootstrap=bootstrap, corrective_percept=corrective_percept, corrective_inert=corrective_inert, overall=overall
    )


@dataclass(frozen=True)
class Q2Verdict:
    delta2: float
    bootstrap: BootstrapResult
    w3_entries_distribution: EntryCountDistribution
    dose_efficient: ClauseResult
    dose_insufficient: ClauseResult
    overall: str
    cross_session_drift_bound: float = CROSS_SESSION_DRIFT_BOUND


def evaluate_q2(delta2: float, bootstrap: BootstrapResult, w3_entries_distribution: EntryCountDistribution) -> Q2Verdict:
    """DOSE-EFFICIENT / DOSE-INSUFFICIENT / INCONCLUSIVE-DOSE (module
    docstring: POINT-gated only, per the registered clause's own literal
    text -- the bootstrap CI is computed and reported, never used to gate
    this verdict)."""

    efficient_met = delta2 >= Q2_EFFICIENT_MIN_DELTA
    dose_efficient = ClauseResult(
        f"Delta_2 >= {Q2_EFFICIENT_MIN_DELTA:+.2f} at <=4 entries/sample vs A3's 100",
        "met" if efficient_met else "not_met",
        f"delta2={delta2:+.4f} (floor {Q2_EFFICIENT_MIN_DELTA:+.2f}), W3 mean entries/sample="
        f"{w3_entries_distribution.mean:.4f} (max {w3_entries_distribution.max})",
    )
    insufficient_met = delta2 <= Q2_INSUFFICIENT_MAX_DELTA
    dose_insufficient = ClauseResult(
        f"Delta_2 <= {Q2_INSUFFICIENT_MAX_DELTA:+.2f}",
        "met" if insufficient_met else "not_met",
        f"delta2={delta2:+.4f} (ceiling {Q2_INSUFFICIENT_MAX_DELTA:+.2f})",
    )
    if dose_efficient.verdict == "met":
        overall = "DOSE-EFFICIENT"
    elif dose_insufficient.verdict == "met":
        overall = "DOSE-INSUFFICIENT"
    else:
        overall = "INCONCLUSIVE-DOSE"
    return Q2Verdict(
        delta2=delta2,
        bootstrap=bootstrap,
        w3_entries_distribution=w3_entries_distribution,
        dose_efficient=dose_efficient,
        dose_insufficient=dose_insufficient,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Structural / harness-defect checks.
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    flight_status: str | None,
    flight_error: str | None,
    rows_by_arm: Mapping[str, Sequence[PCorrFOutputRow]],
    sample_ids: Sequence[str],
    unknown_arm_rows: Sequence[PCorrFOutputRow],
    duplicate_keys: Sequence[tuple[str, str]],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if flight_status != "COMPLETED":
        reasons.append(f"flight-receipt status={flight_status!r} (expected 'COMPLETED'); error={flight_error!r}")
    for row in unknown_arm_rows:
        reasons.append(f"unknown arm {row.arm!r} on sample {row.sample_id!r}")
    for key in duplicate_keys:
        reasons.append(f"duplicate row for (arm, sample_id)={key}")
    id_set = set(sample_ids)
    for arm, rows in rows_by_arm.items():
        got = {row.sample_id for row in rows}
        missing = id_set - got
        extra = got - id_set
        if missing:
            reasons.append(f"arm {arm}: missing {len(missing)} sample(s) from the frozen manifest: {sorted(missing)[:5]}")
        if extra:
            reasons.append(f"arm {arm}: {len(extra)} sample(s) not in the frozen manifest: {sorted(extra)[:5]}")
    return tuple(reasons)


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PCorrFReadReport:
    attempt_dir: Path
    flight_status: str | None
    flight_error: str | None
    n_samples: int
    harness_defect_reasons: tuple[str, ...]
    reachability: ReachabilityStatement
    q1: Q1Verdict
    q2: Q2Verdict
    w4_slu_f1: float
    w4_entries_distribution: EntryCountDistribution
    dual_measurement: Mapping[str, ArmDualMeasurement]
    guardrails: Mapping[str, ArmGuardrails]


def build_pcorrf_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    sample_manifest_path: Path,
    roster_table_path: Path,
    pslu_attempt_dir: Path | None = None,
) -> PCorrFReadReport:
    attempt_dir = Path(attempt_dir)
    rows = load_attempt_rows(attempt_dir)
    flight_status, flight_error = load_flight_status(attempt_dir)

    manifest = load_pslu_sample_manifest(sample_manifest_path)
    rosters = load_pslu_rosters(roster_table_path)
    sample_ids = manifest.sample_ids
    base_roster_values = frozenset(normalize_term(value) for _entry_type, value in rosters.full_roster)

    gold_by_id = load_gold_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED
    gold_scenario_by_id = {sample_id: record.scenario for sample_id, record in gold_by_id.items()}
    gold_values_by_sample = {
        sample_id: frozenset(normalize_term(entity.filler) for entity in record.entities)
        for sample_id, record in gold_by_id.items()
    }

    resolved_pslu_attempt_dir = (
        Path(pslu_attempt_dir)
        if pslu_attempt_dir is not None
        else Path(root) / pf.CONSUMED_PSLU_OUTPUTS_RELPATH.rsplit("/", 1)[0]
    )
    a0_harvested = pf.harvest_a0_emitted_slots(resolved_pslu_attempt_dir)
    a0_predicted_by_sample: dict[str, tuple[SlotEntity, ...]] = {
        sample_id: tuple(SlotEntity(type=t, filler=f) for t, f in record.emitted_slots)
        for sample_id, record in a0_harvested.items()
    }

    rows_by_arm: dict[str, list[PCorrFOutputRow]] = {arm: [] for arm in PCORRF_ARMS}
    unknown_arm_rows: list[PCorrFOutputRow] = []
    seen_keys: set[tuple[str, str]] = set()
    duplicate_keys: list[tuple[str, str]] = []
    for row in rows:
        key = (row.arm, row.sample_id)
        if key in seen_keys:
            duplicate_keys.append(key)
            continue
        seen_keys.add(key)
        if row.arm not in PCORRF_ARMS:
            unknown_arm_rows.append(row)
            continue
        rows_by_arm[row.arm].append(row)

    row_scores_by_arm: dict[str, list[RowScore]] = {arm: [] for arm in PCORRF_ARMS}
    for arm, arm_rows in rows_by_arm.items():
        for row in arm_rows:
            gold = gold_by_id.get(row.sample_id)
            if gold is None:
                continue
            row_scores_by_arm[arm].append(_score_row(row, gold))

    scores_by_sample_by_arm: dict[str, dict[str, SluScore]] = {
        arm: {rs.row.sample_id: rs.score for rs in row_scores_by_arm[arm]} for arm in PCORRF_ARMS
    }

    harness_defect_reasons = _harness_defect_reasons(
        flight_status=flight_status,
        flight_error=flight_error,
        rows_by_arm=rows_by_arm,
        sample_ids=sample_ids,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_keys=duplicate_keys,
    )

    common_denominator = [
        sid
        for sid in sample_ids
        if sid in scores_by_sample_by_arm[W1_ARM] and sid in scores_by_sample_by_arm[W2_ARM]
    ]
    q1_bootstrap = compute_q1_bootstrap(
        w1_scores_by_sample=scores_by_sample_by_arm[W1_ARM],
        w2_scores_by_sample=scores_by_sample_by_arm[W2_ARM],
        common_denominator=common_denominator,
    )
    delta1 = q1_bootstrap.point_estimate
    q1 = evaluate_q1(delta1, q1_bootstrap)

    w3_denominator = [sid for sid in sample_ids if sid in scores_by_sample_by_arm[W3_ARM]]
    q2_bootstrap = compute_q2_bootstrap(
        w3_scores_by_sample=scores_by_sample_by_arm[W3_ARM], common_denominator=w3_denominator
    )
    delta2 = q2_bootstrap.point_estimate
    w3_entries_distribution = _entry_count_distribution([row.k for row in rows_by_arm[W3_ARM]])
    q2 = evaluate_q2(delta2, q2_bootstrap, w3_entries_distribution)

    w4_scores = list(scores_by_sample_by_arm[W4_ARM].values())
    w4_slu_f1 = _aggregate_slu_score(w4_scores).slu_f1[2] if w4_scores else 0.0
    w4_entries_distribution = _entry_count_distribution([row.k for row in rows_by_arm[W4_ARM]])

    reachability = compute_reachability_statement(rows_by_arm, gold_by_id)

    dual_measurement: dict[str, ArmDualMeasurement] = {}
    for arm in PCORRF_ARMS:
        per_sample_rows: list[DualMeasurementRow] = []
        recovery_total = 0
        contamination_total = 0
        for rs in row_scores_by_arm[arm]:
            sample_id = rs.row.sample_id
            gold = gold_by_id.get(sample_id)
            if gold is None:
                continue
            a0_predicted = a0_predicted_by_sample.get(sample_id, ())
            recovery_count, _newly = compute_recovery(rs.predicted_entities, a0_predicted, gold.entities)
            gold_values = gold_values_by_sample.get(sample_id, frozenset())
            contamination_count, _non_gold = compute_contamination(rs.predicted_entities, rs.row.corrective_entries, gold_values)
            recovery_total += recovery_count
            contamination_total += contamination_count
            per_sample_rows.append(
                DualMeasurementRow(
                    arm=arm, sample_id=sample_id, recovery_count=recovery_count, contamination_count=contamination_count
                )
            )
        dual_measurement[arm] = ArmDualMeasurement(
            arm=arm, recovery_total=recovery_total, contamination_total=contamination_total, per_sample=tuple(per_sample_rows)
        )

    guardrails = {
        arm: _build_arm_guardrails(
            arm,
            row_scores_by_arm[arm],
            base_roster_values=base_roster_values,
            gold_scenario_by_sample=gold_scenario_by_id,
        )
        for arm in PCORRF_ARMS
    }
    # Induced substitutions were stubbed inside _build_arm_guardrails above
    # (that function cannot see roster_values per-row without the row
    # itself); compute them here and patch the totals in, matching the
    # SAME quantity analysis.ptrap_read reports.
    for arm in PCORRF_ARMS:
        total = 0
        for rs in row_scores_by_arm[arm]:
            gold = gold_by_id.get(rs.row.sample_id)
            if gold is None:
                continue
            roster_values = _roster_values_for_row(base_roster_values, rs.row)
            total += count_induced_substitutions(rs.predicted_entities, gold.entities, roster_values)
        guardrails[arm] = ArmGuardrails(
            arm=guardrails[arm].arm,
            n_samples=guardrails[arm].n_samples,
            slu_f1=guardrails[arm].slu_f1,
            slot_f1_exact=guardrails[arm].slot_f1_exact,
            parse_rate=guardrails[arm].parse_rate,
            empty_rate=guardrails[arm].empty_rate,
            induced_substitution_total=total,
            copy_rate=guardrails[arm].copy_rate,
            copy_records=guardrails[arm].copy_records,
            copy_records_total=guardrails[arm].copy_records_total,
            scenario_breakdown=guardrails[arm].scenario_breakdown,
        )

    return PCorrFReadReport(
        attempt_dir=attempt_dir,
        flight_status=flight_status,
        flight_error=flight_error,
        n_samples=len(sample_ids),
        harness_defect_reasons=harness_defect_reasons,
        reachability=reachability,
        q1=q1,
        q2=q2,
        w4_slu_f1=w4_slu_f1,
        w4_entries_distribution=w4_entries_distribution,
        dual_measurement=dual_measurement,
        guardrails=guardrails,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def _distribution_json(distribution: EntryCountDistribution) -> dict[str, object]:
    return {
        "n_samples": distribution.n_samples,
        "mean": distribution.mean,
        "max": distribution.max,
        "min": distribution.min,
        "k_zero_count": distribution.k_zero_count,
    }


def report_to_json(report: PCorrFReadReport) -> dict[str, object]:
    return {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "flight_error": report.flight_error,
        "n_samples": report.n_samples,
        "harness_defect_reasons": list(report.harness_defect_reasons),
        "reachability": {
            "per_arm_entry_count_distribution": {
                arm: _distribution_json(dist) for arm, dist in report.reachability.per_arm_entry_count_distribution.items()
            },
            "l1_k_zero_samples": report.reachability.l1_k_zero_samples,
            "total_gold_slots": report.reachability.total_gold_slots,
            "max_attainable_recovery_by_arm": dict(report.reachability.max_attainable_recovery_by_arm),
            "detail": report.reachability.detail,
        },
        "q1": {
            "delta1": report.q1.delta1,
            "bootstrap": report.q1.bootstrap.as_json(),
            "corrective_percept": _clause_json(report.q1.corrective_percept),
            "corrective_inert": _clause_json(report.q1.corrective_inert),
            "overall": report.q1.overall,
        },
        "q2": {
            "delta2": report.q2.delta2,
            "cited_a3_slu_f1": CITED_A3_SLU_F1,
            "bootstrap": report.q2.bootstrap.as_json(),
            "w3_entries_distribution": _distribution_json(report.q2.w3_entries_distribution),
            "dose_efficient": _clause_json(report.q2.dose_efficient),
            "dose_insufficient": _clause_json(report.q2.dose_insufficient),
            "overall": report.q2.overall,
            "cross_session_drift_bound": report.q2.cross_session_drift_bound,
        },
        "w4_descriptive": {
            "slu_f1": report.w4_slu_f1,
            "entries_distribution": _distribution_json(report.w4_entries_distribution),
            "note": "W4 carries no clause (registration verbatim)",
        },
        "dual_measurement": {
            arm: {
                "recovery_total": dm.recovery_total,
                "contamination_total": dm.contamination_total,
                "per_sample": [
                    {"sample_id": r.sample_id, "recovery_count": r.recovery_count, "contamination_count": r.contamination_count}
                    for r in dm.per_sample
                ],
            }
            for arm, dm in report.dual_measurement.items()
        },
        "guardrails": {
            arm: {
                "n_samples": g.n_samples,
                "slu_f1": g.slu_f1,
                "slot_f1_exact": g.slot_f1_exact,
                "parse_rate": g.parse_rate,
                "empty_rate": g.empty_rate,
                "induced_substitution_total": g.induced_substitution_total,
                "copy_rate": g.copy_rate,
                "copy_records": g.copy_records,
                "copy_records_total": g.copy_records_total,
                "scenario_breakdown": [
                    {"scenario": s.scenario, "n_samples": s.n_samples, "slu_f1": s.slu_f1} for s in g.scenario_breakdown
                ],
            }
            for arm, g in report.guardrails.items()
        },
    }


def render_report(report: PCorrFReadReport) -> str:
    lines = [
        "P-CORR-F pinned offline read (docs/readiness/2026-08-20-pcorrf-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r} (error={report.flight_error!r})",
        f"n_samples={report.n_samples}",
        "",
    ]
    if report.harness_defect_reasons:
        lines.append("!" * 78)
        lines.append("HARNESS DEFECT REASONS")
        for reason in report.harness_defect_reasons:
            lines.append(f"  {reason}")
        lines.append("!" * 78)
        lines.append("")

    lines.append("Mandatory pre-read reachability statement")
    lines.append(f"  {report.reachability.detail}")
    lines.append("")

    lines.append(f"Q-1 mechanism: Delta_1={report.q1.delta1:+.4f}, CI=[{report.q1.bootstrap.ci_low:+.4f}, {report.q1.bootstrap.ci_high:+.4f}]")
    lines.append(f"  CORRECTIVE-PERCEPT: [{report.q1.corrective_percept.verdict.upper():>8}] {report.q1.corrective_percept.detail}")
    lines.append(f"  CORRECTIVE-INERT:   [{report.q1.corrective_inert.verdict.upper():>8}] {report.q1.corrective_inert.detail}")
    lines.append(f"  OVERALL: {report.q1.overall}")
    lines.append("")

    lines.append(
        f"Q-2 dose efficiency: Delta_2={report.q2.delta2:+.4f} (vs CITED A3 {CITED_A3_SLU_F1:.4f}), "
        f"CI=[{report.q2.bootstrap.ci_low:+.4f}, {report.q2.bootstrap.ci_high:+.4f}] (reported, non-gating); "
        f"cross-session drift bound +/-{report.q2.cross_session_drift_bound:.3f}"
    )
    lines.append(f"  DOSE-EFFICIENT:    [{report.q2.dose_efficient.verdict.upper():>8}] {report.q2.dose_efficient.detail}")
    lines.append(f"  DOSE-INSUFFICIENT: [{report.q2.dose_insufficient.verdict.upper():>8}] {report.q2.dose_insufficient.detail}")
    lines.append(f"  OVERALL: {report.q2.overall}")
    lines.append("")

    lines.append(
        f"W4 descriptive dose curve (no clause): SLU-F1={report.w4_slu_f1:.4f}, "
        f"mean entries/sample={report.w4_entries_distribution.mean:.4f} (max {report.w4_entries_distribution.max})"
    )
    lines.append("")

    lines.append("Mandatory dual measurement (recovery / contamination, per arm)")
    for arm in PCORRF_ARMS:
        dm = report.dual_measurement.get(arm)
        if dm is None:
            continue
        lines.append(f"  {arm}: recovery={dm.recovery_total} contamination={dm.contamination_total}")
    lines.append("")

    lines.append("Guardrails (descriptive, never verdict-gating)")
    for arm in PCORRF_ARMS:
        g = report.guardrails.get(arm)
        if g is None:
            continue
        lines.append(
            f"  {arm}: slu_f1={g.slu_f1:.4f} slot_f1_exact={g.slot_f1_exact:.4f} parse_rate={g.parse_rate:.4f} "
            f"copy_rate={g.copy_rate:.4f} induced={g.induced_substitution_total}"
        )
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pcorrf-read",
        description=(
            "P-CORR-F pinned offline read suite: Q-1/Q-2 bootstrap-evaluated verdicts, W4 descriptive "
            "dose curve, mandatory dual measurement (recovery/contamination), reachability statement, "
            "and guardrails. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the P-CORR-F flight's own attempt directory (carries outputs.jsonl)")
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
        "--pslu-attempt-dir", type=Path, default=None,
        help="override the CONSUMED P-SLU A0 baseline attempt dir (default: the pinned consumed attempt)",
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
            f"REFUSED: {verdict_path} already exists -- this suite refuses to run twice against the "
            "same output dir (one-shot read discipline); choose a fresh --output-dir if a genuinely "
            "new read is intended",
            file=sys.stderr,
        )
        return 1

    lock = load_lock(umbrella_lock_path(repo_root))
    root = data_root()

    try:
        report = build_pcorrf_report(
            args.attempt_dir,
            lock,
            root,
            sample_manifest_path=sample_manifest_path,
            roster_table_path=roster_table_path,
            pslu_attempt_dir=args.pslu_attempt_dir,
        )
    except (PCorrFReadError, pf.PCorrFFlightError) as error:
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


__all__ = [
    "CITED_A3_SLU_F1",
    "CROSS_SESSION_DRIFT_BOUND",
    "Q1_MIN_DELTA",
    "Q1_INERT_BAND",
    "Q2_EFFICIENT_MIN_DELTA",
    "Q2_INSUFFICIENT_MAX_DELTA",
    "REPORT_SCHEMA",
    "ArmDualMeasurement",
    "ArmGuardrails",
    "ClauseResult",
    "DualMeasurementRow",
    "EntryCountDistribution",
    "PCorrFOutputRow",
    "PCorrFReadError",
    "PCorrFReadReport",
    "Q1Verdict",
    "Q2Verdict",
    "ReachabilityStatement",
    "RowScore",
    "ScenarioBreakdown",
    "build_pcorrf_report",
    "compute_contamination",
    "compute_q1_bootstrap",
    "compute_q2_bootstrap",
    "compute_reachability_statement",
    "compute_recovery",
    "evaluate_q1",
    "evaluate_q2",
    "load_attempt_rows",
    "main",
    "render_report",
    "report_to_json",
]
