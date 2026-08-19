"""P-TRAP offline read suite (pinned, pre-registered).

Model-free, read-only: this module NEVER opens a model session. It has TWO
distinct jobs that must never be confused with one another (each reads a
DIFFERENT attempt directory):

1. :func:`harvest_a0_wrong_values` -- THE A0-VALUE HARVESTER. Reads the
   CONSUMED P-SLU attempt's own already-written ``outputs.jsonl``
   (``attempt-20260818T010218Z-4c97cb``, ``rails.probes.pslu_flight.
   run_pslu_flight``'s own write shape) and classifies each A0 (zero-supply)
   response's predicted entities into "wrong emitted values" -- the raw
   material :func:`rails.probes.ptrap_flight.build_trap_sets` turns into
   V1/V2 appended roster entries at BINDING time, before the P-TRAP flight's
   own first request. DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED
   SYNTHETIC FIXTURES (``tests/unit/test_ptrap_read.py``), exactly mirroring
   ``analysis.pslu_read``'s own module-docstring discipline: this function
   is NEVER run against the real consumed P-SLU attempt directory by the
   machinery-building task that authored this file -- doing so would
   constitute a real-output read, which that task is explicitly scoped OUT
   of. A later, separately-registered flight-BINDING session points it at
   the real attempt dir and feeds the result into
   ``rails.probes.ptrap_flight.build_trap_sets``.
2. :func:`build_ptrap_report` (and everything below it) -- THE READ SUITE
   proper. Reads the P-TRAP FLIGHT'S OWN already-written attempt directory
   (once it exists, a later one-shot read session) and scores it: the
   capture detector, per-sample table, SLU-F1 guardrail vs the cited
   consumed A3 aggregate, induced substitutions, empty/parse rates, the
   per-sample paired cluster bootstrap CI (``analysis.bootstrap``, SHARED
   with ``analysis.pkey_read`` per that module's own docstring), the
   mandatory pre-read reachability statement, and the CI-gated verdict
   evaluator (ACOUSTIC-MEDIATED / KEY-ONLY-MATCHING / INCONCLUSIVE-TRAP,
   preregistration section 6).

Sources of truth this module implements EXACTLY (never re-derives on its
own authority):

- ``docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md``
  sections 2 (trap construction / legality), 3 (metrics, verdicts), and 6
  (2026-08-19 CI amendment: bootstrap-gated verdicts, mandatory
  reachability statement).
- ``configs/probes/g0-binding/pslu-sample-devel-n60.json`` (the frozen
  sample set, REUSED byte-identically) and ``configs/probes/g0-binding/
  pslu-rosters-train-only.json`` (the A3-form base 100-entry roster),
  loaded via ``rails.probes.pslu_flight``'s own loaders.
- ``docs/checks/speech-aware-evidence-acquisition/2026-08-18-pslu-read/
  verdict.json``'s own A3 aggregate ``slu_f1.f1`` -- CITED verbatim as
  :data:`CONSUMED_A3_SLU_F1` (never re-read live), exactly like
  ``analysis.pkey_read``'s own ``NEAR_MISS_COUNT``/``NEAR_MISS_CENSUS_TOTAL``
  citation convention.

Parsing primitives REUSED VERBATIM from the consumed suite (never
reimplemented): ``analysis.pslu_read.load_attempt_rows`` (the harvester's
own attempt-dir reader, aliased below as ``load_pslu_attempt_rows``),
``analysis.pslu_read.load_flight_status``, ``analysis.pslu_read.
load_gold_by_sample_id``, ``analysis.pslu_read.count_induced_substitutions``,
``analysis.pslu_read._recheck_row``/``_aggregate_slu_score``/``RowAnalysis``
(private cross-module reuse already precedented in this repository --
``analysis.pkey_read`` imports the SAME four private names the SAME way),
and ``reproduction.slurp_scoring.parse_slu_response``/``score_slu``.

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried -- mirrors this
probe family's own established discipline):

1. CAPTURE (preregistration section 3, verbatim): "the response emits an
   appended trap entry (post-normalization exact match) in any slot." Read
   as a VALUE-level match, independent of entity TYPE: ANY predicted
   entity's normalized filler equals ANY of that row's OWN appended trap
   entries' normalized filler -- "in any slot" names the response's
   predicted-entity set at large, never a single expected-type slot. See
   :func:`response_captures_trap`.
2. "raw difference >= 6" (ACOUSTIC-MEDIATED's second AND-clause) is read as
   the signed INTEGER count difference ``capture_count(V1) -
   capture_count(V2)`` over the common denominator -- a SEPARATE small-N
   guard alongside the RATE clause, the SAME two-ingredient pattern P-KEY's
   own registered thresholds already use (a rate bound plus its underlying
   count), never a second reading of the rate itself.
3. "the common denominator" (section 3) is read as the sample set with
   V1's OWN K>=1 (preregistration section 2's own K=0 exclusion clause
   names V1's usable-trap criterion, never V2's) -- V2's own K can only be
   <= V1's K by construction (``rails.probes.ptrap_flight``'s own
   length-matched invariant), so a sample never contributes an unpaired V2
   observation without a V1 one.
4. The 2026-08-19 CI amendment's "unreachable branches may not be reported
   as affirmative outcomes" is read as gating KEY-ONLY-MATCHING the SAME
   way the P-KEY 2026-08-19 amendment's own item 2 gates KEY-ONLY: an
   equivalence verdict may not fire as an affirmative negative when the
   alternative (ACOUSTIC-MEDIATED) was never reachable given this run's own
   data. ACOUSTIC-MEDIATED needs no SEPARATE reachability gate of its own --
   ``raw_diff <= n_usable`` always (both capture counts live in
   ``[0, n_usable]``), so its own registered ``raw_diff >= 6`` point clause
   already IMPLIES ``n_usable >= 6`` whenever it fires; the reachability
   arithmetic mainly explains an otherwise-unreached INCONCLUSIVE-TRAP. See
   :func:`compute_reachability_statement` / :func:`evaluate_ptrap_ci_gated`.
5. SLU-F1-vs-A3 / induced-substitution / empty-parse-rate guardrails
   (preregistration section 3: "Guardrails reported") are DESCRIPTIVE ONLY
   -- they never gate the verdict, mirroring ``analysis.pkey_read``'s own
   T0-vs-gold WER ("scoring-side only, reported only, no clause") and
   ``analysis.pslu_read``'s own DOSE-CONFIRM/intent-drift-guardrail
   precedent of a reported-but-non-gating secondary quantity.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..core.retrieval import normalize_term
from ..rails.probes.pslu_flight import (
    PSLU_PHASE1_ARM,
    load_pslu_rosters,
    load_pslu_sample_manifest,
)
from ..rails.probes.ptrap_flight import (
    PTRAP_ARMS,
    V1_ARM,
    V2_ARM,
    HarvestedWrongValue,
    _gold_filler_values,
)
from ..reproduction.slurp_scoring import SlotEntity, SluScore, parse_slu_response, score_slu
from .bootstrap import (
    BootstrapResult,
    DEFAULT_CI_LEVEL as BOOTSTRAP_CI_LEVEL,
    DEFAULT_N_REPLICATES as BOOTSTRAP_N_REPLICATES,
    DEFAULT_SEED as BOOTSTRAP_SEED,
    paired_cluster_bootstrap,
)
from .pslu_read import (
    RecheckMismatch,
    RowAnalysis,
    RUNTIME_PROHIBITED_NOTE,
    _aggregate_slu_score,
    _recheck_row,
    count_induced_substitutions,
    load_attempt_rows as load_pslu_attempt_rows,
    load_flight_status,
    load_gold_by_sample_id,
)

REPORT_SCHEMA = "saea-ptrap-read-v1"

# The consumed P-SLU probe's own zero-supply arm name -- module docstring
# item 1's own source: A0 is the ONLY arm this harvester ever reads.
CONSUMED_PSLU_ARM = PSLU_PHASE1_ARM  # "A0"

# docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md sections 3
# and 6, quoted verbatim in each clause's own detail text below.
ACOUSTIC_MEDIATED_MIN_RATE_DIFF = 0.10
ACOUSTIC_MEDIATED_MIN_RAW_DIFF = 6
KEY_ONLY_MATCHING_MAX_ABS = 0.03

# CITED constant (module docstring): the consumed P-SLU probe's own A3
# aggregate SLU-F1 -- docs/checks/speech-aware-evidence-acquisition/
# 2026-08-18-pslu-read/verdict.json, aggregates.A3.slu_f1.f1. Frozen here
# VERBATIM, never re-read live, exactly like analysis.pkey_read's own
# NEAR_MISS_COUNT/NEAR_MISS_CENSUS_TOTAL citation convention.
CONSUMED_A3_SLU_F1 = 0.5961280580450439


class PTrapReadError(RuntimeError):
    """Malformed attempt-dir/binding input for this read -- never raised for
    a legitimate INCONCLUSIVE-TRAP-worthy data shape (that is reported as a
    clause result, not an exception)."""


# ---------------------------------------------------------------------------
# 1. THE A0-VALUE HARVESTER (module docstring item 1).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HarvestYield:
    """The harvester's full, reviewable output -- never just the trap pool:
    ``samples_with_zero_wrong_values``/``per_sample_wrong_value_counts`` let
    a caller (or a test) audit the K=0 accounting BEFORE
    ``rails.probes.ptrap_flight.build_trap_sets`` ever runs."""

    wrong_values_by_sample: Mapping[str, tuple[HarvestedWrongValue, ...]]
    samples_with_zero_wrong_values: tuple[str, ...]
    total_wrong_value_count: int
    per_sample_wrong_value_counts: Mapping[str, int]


def _wrong_predicted_entities(predicted: Sequence[SlotEntity], gold: Sequence[SlotEntity]) -> list[SlotEntity]:
    """rails.probes.ptrap_flight module docstring note 1: the IDENTICAL
    false-positive convention ``reproduction.slurp_scoring._exact_counts``
    already uses for the official ``slot_f1_exact`` FP count -- an entity
    NOT exactly present in the (shrinking) remaining gold list is "wrong",
    never a second, drifting "wrongness" definition."""

    remaining = list(gold)
    wrong: list[SlotEntity] = []
    for entity in predicted:
        if entity in remaining:
            remaining.remove(entity)
        else:
            wrong.append(entity)
    return wrong


def _dedupe_wrong_entities(entities: Sequence[SlotEntity]) -> tuple[SlotEntity, ...]:
    """Order-preserving dedupe by normalized ``(type, filler)`` -- a
    repeated identical wrong emission adds no new trap candidate."""

    seen: set[tuple[str, str]] = set()
    result: list[SlotEntity] = []
    for entity in entities:
        key = (entity.type, normalize_term(entity.filler))
        if key in seen:
            continue
        seen.add(key)
        result.append(entity)
    return tuple(result)


def harvest_a0_wrong_values(pslu_attempt_dir: Path, gold_by_sample_id: Mapping[str, object]) -> HarvestYield:
    """THE A0-VALUE HARVESTER (module docstring item 1). ``pslu_attempt_dir``
    is the CONSUMED P-SLU attempt's own directory (``outputs.jsonl`` in
    ``rails.probes.pslu_flight.run_pslu_flight``'s own write shape, read via
    ``analysis.pslu_read.load_attempt_rows`` -- reused VERBATIM, never a
    second parser); ``gold_by_sample_id`` is whatever
    ``analysis.pslu_read.load_gold_by_sample_id`` returns (or an equivalent
    ``.entities``-carrying object in a test fixture), RUNTIME_PROHIBITED
    (scoring-side only).

    NEVER run against the real attempt directory by the machinery-building
    task that authored this module (module docstring): tested exclusively
    against small hand-authored ``outputs.jsonl`` fixtures in
    ``tests/unit/test_ptrap_read.py``."""

    rows = load_pslu_attempt_rows(pslu_attempt_dir)
    a0_rows = [row for row in rows if row.arm == CONSUMED_PSLU_ARM and not row.silence_swapped]
    if not a0_rows:
        raise PTrapReadError(
            f"{pslu_attempt_dir}: zero non-silence-swapped {CONSUMED_PSLU_ARM!r} rows found -- "
            "nothing to harvest"
        )

    wrong_by_sample: dict[str, tuple[HarvestedWrongValue, ...]] = {}
    counts: dict[str, int] = {}
    for row in a0_rows:
        gold_record = gold_by_sample_id.get(row.sample_id)
        if gold_record is None:
            continue  # a missing-gold shape is a caller-side data problem, not this harvester's job
        _scenario, _action, predicted_entities, _parsed = parse_slu_response(row.response_text)
        wrong = _dedupe_wrong_entities(_wrong_predicted_entities(predicted_entities, gold_record.entities))
        wrong_by_sample[row.sample_id] = tuple(
            HarvestedWrongValue(sample_id=row.sample_id, entity_type=entity.type, filler=entity.filler)
            for entity in wrong
        )
        counts[row.sample_id] = len(wrong)

    zero = tuple(sorted(sample_id for sample_id, count in counts.items() if count == 0))
    return HarvestYield(
        wrong_values_by_sample=wrong_by_sample,
        samples_with_zero_wrong_values=zero,
        total_wrong_value_count=sum(counts.values()),
        per_sample_wrong_value_counts=counts,
    )


# ---------------------------------------------------------------------------
# 2. THE READ SUITE -- loading the P-TRAP FLIGHT'S OWN attempt directory.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PTrapOutputRow:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: Mapping[str, object]
    k: int
    trap_entries: tuple[Mapping[str, object], ...]

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "PTrapOutputRow":
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            messages=tuple(document["messages"]),
            response_text=str(document["response_text"]),
            metrics=document["metrics"],
            consumption=document["consumption"],
            k=int(document["k"]),
            trap_entries=tuple(document.get("trap_entries", ())),
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[PTrapOutputRow, ...]:
    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise PTrapReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[PTrapOutputRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PTrapReadError(f"{path} line {line_no}: invalid JSON: {error}") from error
        rows.append(PTrapOutputRow.from_json(document))
    if not rows:
        raise PTrapReadError(f"{path}: zero rows")
    return tuple(rows)


# ---------------------------------------------------------------------------
# Capture detector (module docstring note 1).
# ---------------------------------------------------------------------------


def response_captures_trap(
    predicted_entities: Sequence[SlotEntity], trap_entries: Sequence[Mapping[str, object]]
) -> bool:
    """CAPTURE (preregistration section 3, verbatim): "the response emits
    an appended trap entry (post-normalization exact match) in any slot."
    ``trap_entries`` empty (a K=0 row) is vacuously ``False``, never a
    crash -- module docstring note 1."""

    trap_fillers = {normalize_term(str(entry.get("filler", ""))) for entry in trap_entries}
    if not trap_fillers:
        return False
    return any(normalize_term(entity.filler) in trap_fillers for entity in predicted_entities)


# ---------------------------------------------------------------------------
# Per-row scoring (reuses analysis.pslu_read's own primitives verbatim).
# ---------------------------------------------------------------------------


def _score_ptrap_row(row: PTrapOutputRow, gold) -> RowAnalysis:
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


def _roster_values_for_row(base_roster_values: frozenset[str], row: PTrapOutputRow) -> tuple[str, ...]:
    """The VALUE set actually supplied on ``row`` -- the base A3 100-entry
    roster's own values PLUS this row's own appended trap fillers,
    normalized -- the induced-substitution ingredient
    ``analysis.pslu_read.count_induced_substitutions`` (reused verbatim)
    expects."""

    trap_values = {normalize_term(str(entry.get("filler", ""))) for entry in row.trap_entries}
    return tuple(sorted(base_roster_values | trap_values))


# ---------------------------------------------------------------------------
# Per-sample table.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PTrapSampleRow:
    sample_id: str
    v1_k: int
    v2_k: int
    v1_captured: bool
    v2_captured: bool
    v1_parsed: bool
    v2_parsed: bool
    v1_induced_substitutions: int
    v2_induced_substitutions: int

    @property
    def usable(self) -> bool:
        """Module docstring note 3: the common-denominator membership rule
        -- V1's OWN K>=1 (preregistration section 2's own K=0 exclusion
        clause names V1's usable-trap criterion)."""

        return self.v1_k >= 1


# ---------------------------------------------------------------------------
# Mandatory pre-read reachability statement (2026-08-19 amendment, section
# 6): "given the per-sample K distribution and usable-trap counts, publish
# the maximum attainable capture difference."
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReachabilityStatement:
    n_samples: int
    n_usable: int
    max_attainable_rate_diff: float
    max_attainable_raw_diff: int
    acoustic_mediated_reachable: bool
    detail: str


def compute_reachability_statement(
    per_sample: Sequence[PTrapSampleRow], *, n_samples: int | None = None
) -> ReachabilityStatement:
    """Self-contained arithmetic from THIS run's own per-sample K
    distribution (module docstring note 4) -- unlike P-KEY's own
    reachability statement, P-TRAP's needs no external census citation:
    the best-case bound is exact, not an imported rate. Best case: V1
    captures EVERY usable sample, V2 captures NONE ->
    ``max_attainable_rate_diff = 1.0``, ``max_attainable_raw_diff =
    n_usable`` (both counts live in ``[0, n_usable]`` by construction)."""

    n = n_samples if n_samples is not None else len(per_sample)
    n_usable = sum(1 for row in per_sample if row.usable)
    max_rate = 1.0 if n_usable > 0 else 0.0
    max_raw = n_usable
    reachable = max_rate >= ACOUSTIC_MEDIATED_MIN_RATE_DIFF and max_raw >= ACOUSTIC_MEDIATED_MIN_RAW_DIFF
    detail = (
        f"per-sample K distribution: {n_usable}/{n} samples usable (V1 K>=1, the common-denominator "
        "membership rule). Best case: V1 captures ALL usable samples, V2 captures NONE -> "
        f"max_attainable_rate_diff={max_rate:.4f}, max_attainable_raw_diff={max_raw}. "
        f"ACOUSTIC-MEDIATED floor is rate_diff>=+{ACOUSTIC_MEDIATED_MIN_RATE_DIFF:.2f} AND "
        f"raw_diff>={ACOUSTIC_MEDIATED_MIN_RAW_DIFF} -> "
        f"{'REACHABLE' if reachable else 'UNREACHABLE'} given this run's own K distribution."
    )
    return ReachabilityStatement(
        n_samples=n,
        n_usable=n_usable,
        max_attainable_rate_diff=max_rate,
        max_attainable_raw_diff=max_raw,
        acoustic_mediated_reachable=reachable,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Per-sample paired cluster bootstrap over the V1-V2 capture difference
# (2026-08-19 amendment, section 6) -- shared primitive, analysis.bootstrap.
# ---------------------------------------------------------------------------


def compute_capture_bootstrap(
    *,
    v1_captured_by_sample: Mapping[str, bool],
    v2_captured_by_sample: Mapping[str, bool],
    common_denominator: Sequence[str],
    n_replicates: int = BOOTSTRAP_N_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = BOOTSTRAP_CI_LEVEL,
) -> BootstrapResult:
    """"the read suite computes a per-sample paired bootstrap over the
    common-denominator samples and publishes sigma-hat of the V1-V2 capture
    difference with a 90% CI" (preregistration section 6, verbatim).
    Delegates the resampling primitive to
    :func:`analysis.bootstrap.paired_cluster_bootstrap` -- the SAME shared
    core ``analysis.pkey_read.compute_interaction_bootstrap`` already uses
    (that module's own docstring names this future reuse explicitly)."""

    ids = tuple(common_denominator)
    if not ids:
        raise PTrapReadError(
            "compute_capture_bootstrap: empty common denominator -- cannot bootstrap zero paired "
            "samples"
        )

    def statistic(sample_ids: Sequence[str]) -> float:
        v1_rate = sum(1 for sample_id in sample_ids if v1_captured_by_sample[sample_id]) / len(sample_ids)
        v2_rate = sum(1 for sample_id in sample_ids if v2_captured_by_sample[sample_id]) / len(sample_ids)
        return v1_rate - v2_rate

    return paired_cluster_bootstrap(
        sample_ids=ids, statistic=statistic, n_replicates=n_replicates, seed=seed, ci_level=ci_level
    )


# ---------------------------------------------------------------------------
# Verdict evaluator: point thresholds, then the CI/reachability gate.
# ---------------------------------------------------------------------------

ClauseVerdict = Literal["met", "not_met"]


@dataclass(frozen=True)
class ClauseResult:
    clause_text: str
    verdict: ClauseVerdict
    detail: str


@dataclass(frozen=True)
class PTrapPointVerdict:
    rate_diff: float
    raw_diff: int
    acoustic_mediated_point: ClauseResult
    key_only_matching_point: ClauseResult


def evaluate_point(rate_diff: float, raw_diff: int) -> PTrapPointVerdict:
    """The REGISTERED point thresholds (preregistration section 3, before
    the 2026-08-19 CI amendment) -- module docstring note 2 on
    ``raw_diff``."""

    am_met = rate_diff >= ACOUSTIC_MEDIATED_MIN_RATE_DIFF and raw_diff >= ACOUSTIC_MEDIATED_MIN_RAW_DIFF
    acoustic_mediated_point = ClauseResult(
        f"capture(V1) - capture(V2) >= +{ACOUSTIC_MEDIATED_MIN_RATE_DIFF:.2f} AND raw difference >= "
        f"{ACOUSTIC_MEDIATED_MIN_RAW_DIFF}",
        "met" if am_met else "not_met",
        f"rate_diff={rate_diff:+.4f} (floor +{ACOUSTIC_MEDIATED_MIN_RATE_DIFF:.2f}), "
        f"raw_diff={raw_diff:+d} (floor {ACOUSTIC_MEDIATED_MIN_RAW_DIFF})",
    )
    ko_met = abs(rate_diff) <= KEY_ONLY_MATCHING_MAX_ABS
    key_only_matching_point = ClauseResult(
        f"|capture(V1) - capture(V2)| <= {KEY_ONLY_MATCHING_MAX_ABS:.2f}",
        "met" if ko_met else "not_met",
        f"rate_diff={rate_diff:+.4f}, ceiling +/-{KEY_ONLY_MATCHING_MAX_ABS:.2f}",
    )
    return PTrapPointVerdict(
        rate_diff=rate_diff,
        raw_diff=raw_diff,
        acoustic_mediated_point=acoustic_mediated_point,
        key_only_matching_point=key_only_matching_point,
    )


@dataclass(frozen=True)
class PTrapCIVerdict:
    point: PTrapPointVerdict
    bootstrap: BootstrapResult
    reachability: ReachabilityStatement
    acoustic_mediated: ClauseResult
    key_only_matching: ClauseResult
    overall: str


def evaluate_ptrap_ci_gated(
    point: PTrapPointVerdict, bootstrap: BootstrapResult, reachability: ReachabilityStatement
) -> PTrapCIVerdict:
    """2026-08-19 amendment (preregistration section 6): "ACOUSTIC-MEDIATED
    requires the CI lower bound > 0 in addition to the registered point
    thresholds"; "KEY-ONLY-MATCHING ... fires only if the ENTIRE CI lies
    inside [-0.03, +0.03]"; "unreachable branches may not be reported as
    affirmative outcomes" (module docstring note 4's own gating reading)."""

    am_ci_met = bootstrap.ci_low > 0.0
    am_met = point.acoustic_mediated_point.verdict == "met" and am_ci_met
    acoustic_mediated = ClauseResult(
        "registered point thresholds met AND (2026-08-19 amendment) the bootstrap CI lower bound of "
        "the V1-V2 capture difference is > 0",
        "met" if am_met else "not_met",
        f"point={point.acoustic_mediated_point.verdict}, "
        f"CI=[{bootstrap.ci_low:+.4f}, {bootstrap.ci_high:+.4f}] "
        f"(sigma_hat={bootstrap.sigma_hat:.4f}, n_replicates={bootstrap.n_replicates}); ci_low>0 is "
        f"{am_ci_met}",
    )

    ci_within_band = bootstrap.contains(-KEY_ONLY_MATCHING_MAX_ABS, KEY_ONLY_MATCHING_MAX_ABS)
    if point.key_only_matching_point.verdict != "met":
        ko_met = False
        ko_detail = (
            f"point rate_diff={point.rate_diff:+.4f} already outside the "
            f"+/-{KEY_ONLY_MATCHING_MAX_ABS:.2f} band"
        )
    elif not ci_within_band:
        ko_met = False
        ko_detail = (
            f"CI=[{bootstrap.ci_low:+.4f}, {bootstrap.ci_high:+.4f}] is NOT entirely inside "
            f"[-{KEY_ONLY_MATCHING_MAX_ABS:.2f}, +{KEY_ONLY_MATCHING_MAX_ABS:.2f}] -- a point estimate "
            "inside the band with a CI crossing it is INCONCLUSIVE-TRAP, never an affirmative "
            "KEY-ONLY-MATCHING"
        )
    elif not reachability.acoustic_mediated_reachable:
        ko_met = False
        ko_detail = (
            f"CI=[{bootstrap.ci_low:+.4f}, {bootstrap.ci_high:+.4f}] IS entirely inside the band, but "
            "ACOUSTIC-MEDIATED is UNREACHABLE given this run's own K distribution "
            f"(max_attainable_raw_diff={reachability.max_attainable_raw_diff} < "
            f"{ACOUSTIC_MEDIATED_MIN_RAW_DIFF}) -- KEY-ONLY-MATCHING may not be reported as an "
            "affirmative negative under an unreachable alternative (mirrors the P-KEY 2026-08-19 "
            "amendment item 2 gate); INCONCLUSIVE-TRAP with the reachability bound instead"
        )
    else:
        ko_met = True
        ko_detail = (
            f"CI=[{bootstrap.ci_low:+.4f}, {bootstrap.ci_high:+.4f}] entirely inside the band; "
            f"ACOUSTIC-MEDIATED reachable (max_attainable_raw_diff={reachability.max_attainable_raw_diff})"
        )
    key_only_matching = ClauseResult(
        f"|point rate_diff| <= {KEY_ONLY_MATCHING_MAX_ABS:.2f} AND the ENTIRE {bootstrap.ci_level:.0%} "
        f"bootstrap CI lies inside [-{KEY_ONLY_MATCHING_MAX_ABS:.2f}, +{KEY_ONLY_MATCHING_MAX_ABS:.2f}] "
        "AND ACOUSTIC-MEDIATED is reachable given this run's own K distribution",
        "met" if ko_met else "not_met",
        ko_detail,
    )

    if acoustic_mediated.verdict == "met":
        overall = "ACOUSTIC-MEDIATED"
    elif key_only_matching.verdict == "met":
        overall = "KEY-ONLY-MATCHING"
    else:
        overall = "INCONCLUSIVE-TRAP"

    return PTrapCIVerdict(
        point=point,
        bootstrap=bootstrap,
        reachability=reachability,
        acoustic_mediated=acoustic_mediated,
        key_only_matching=key_only_matching,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Structural / harness-defect checks (read-side re-derivation, defense in
# depth alongside rails.probes.ptrap_flight.validate_ptrap_flight_summary's
# own WRITE-time checks).
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    flight_status: str | None,
    flight_error: str | None,
    rows_by_arm: Mapping[str, Sequence[PTrapOutputRow]],
    sample_ids: Sequence[str],
    unknown_arm_rows: Sequence[PTrapOutputRow],
    duplicate_keys: Sequence[tuple[str, str]],
    gold_entities_by_sample_id: Mapping[str, Sequence[SlotEntity]],
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

    v1_k_by_sample = {row.sample_id: row.k for row in rows_by_arm.get(V1_ARM, ())}
    for row in rows_by_arm.get(V2_ARM, ()):
        v1_k = v1_k_by_sample.get(row.sample_id)
        if v1_k is not None and row.k > v1_k:
            reasons.append(f"arm V2 sample {row.sample_id!r}: k={row.k} exceeds this sample's own V1 k={v1_k}")
        for entry in row.trap_entries:
            if entry.get("origin_sample_id") == row.sample_id:
                reasons.append(f"arm V2 sample {row.sample_id!r}: fixed-point violation, entry {entry!r}")

    for arm, rows in rows_by_arm.items():
        for row in rows:
            if row.k != len(row.trap_entries):
                reasons.append(
                    f"arm {arm} sample {row.sample_id!r}: k={row.k} disagrees with "
                    f"len(trap_entries)={len(row.trap_entries)}"
                )
            gold_entities = gold_entities_by_sample_id.get(row.sample_id)
            if gold_entities is None:
                continue
            gold_values = _gold_filler_values(gold_entities)
            for entry in row.trap_entries:
                if normalize_term(str(entry.get("filler", ""))) in gold_values:
                    reasons.append(
                        f"arm {arm} sample {row.sample_id!r}: appended trap entry {entry!r} equals "
                        "(post-normalization) a gold slot value of its OWN sample -- binding-time "
                        "zero-overlap check violated"
                    )
    return tuple(reasons)


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PTrapReadReport:
    attempt_dir: Path
    flight_status: str | None
    flight_error: str | None
    per_sample: tuple[PTrapSampleRow, ...]
    v1_slu_f1: float
    v2_slu_f1: float
    v1_parse_rate: float
    v2_parse_rate: float
    v1_empty_rate: float
    v2_empty_rate: float
    v1_induced_substitution_total: int
    v2_induced_substitution_total: int
    v1_capture_count: int
    v2_capture_count: int
    v1_capture_rate: float
    v2_capture_rate: float
    n_usable: int
    n_excluded: int
    excluded_sample_ids: tuple[str, ...]
    harness_defect_reasons: tuple[str, ...]
    recheck_mismatches: tuple[RecheckMismatch, ...]
    ci_verdict: PTrapCIVerdict


def build_ptrap_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    sample_manifest_path: Path,
    roster_table_path: Path,
) -> PTrapReadReport:
    attempt_dir = Path(attempt_dir)
    rows = load_attempt_rows(attempt_dir)
    flight_status, flight_error = load_flight_status(attempt_dir)

    manifest = load_pslu_sample_manifest(sample_manifest_path)
    rosters = load_pslu_rosters(roster_table_path)
    sample_ids = manifest.sample_ids
    base_roster_values = frozenset(normalize_term(value) for _entry_type, value in rosters.full_roster)

    gold_by_id = load_gold_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED
    gold_entities_by_sample_id = {sample_id: record.entities for sample_id, record in gold_by_id.items()}

    rows_by_arm: dict[str, list[PTrapOutputRow]] = {arm: [] for arm in PTRAP_ARMS}
    unknown_arm_rows: list[PTrapOutputRow] = []
    seen_keys: set[tuple[str, str]] = set()
    duplicate_keys: list[tuple[str, str]] = []
    for row in rows:
        key = (row.arm, row.sample_id)
        if key in seen_keys:
            duplicate_keys.append(key)
            continue
        seen_keys.add(key)
        if row.arm not in PTRAP_ARMS:
            unknown_arm_rows.append(row)
            continue
        rows_by_arm[row.arm].append(row)

    v1_by_sample = {row.sample_id: row for row in rows_by_arm[V1_ARM]}
    v2_by_sample = {row.sample_id: row for row in rows_by_arm[V2_ARM]}

    recheck_mismatches: list[RecheckMismatch] = []
    v1_scores: list[SluScore] = []
    v2_scores: list[SluScore] = []
    per_sample: list[PTrapSampleRow] = []
    v1_parsed_count = v2_parsed_count = 0
    v1_induced_total = v2_induced_total = 0

    for sample_id in sample_ids:
        gold = gold_by_id.get(sample_id)
        v1_row = v1_by_sample.get(sample_id)
        v2_row = v2_by_sample.get(sample_id)
        if gold is None or v1_row is None or v2_row is None:
            continue  # reported separately via harness_defect_reasons below

        v1_analysis = _score_ptrap_row(v1_row, gold)
        v2_analysis = _score_ptrap_row(v2_row, gold)
        recheck_mismatches.extend(v1_analysis.recheck_mismatches)
        recheck_mismatches.extend(v2_analysis.recheck_mismatches)
        v1_scores.append(v1_analysis.recomputed_score)
        v2_scores.append(v2_analysis.recomputed_score)

        v1_captured = response_captures_trap(v1_analysis.predicted_entities, v1_row.trap_entries)
        v2_captured = response_captures_trap(v2_analysis.predicted_entities, v2_row.trap_entries)

        v1_roster_values = _roster_values_for_row(base_roster_values, v1_row)
        v2_roster_values = _roster_values_for_row(base_roster_values, v2_row)
        v1_induced = count_induced_substitutions(v1_analysis.predicted_entities, gold.entities, v1_roster_values)
        v2_induced = count_induced_substitutions(v2_analysis.predicted_entities, gold.entities, v2_roster_values)
        v1_induced_total += v1_induced
        v2_induced_total += v2_induced

        if v1_analysis.parsed:
            v1_parsed_count += 1
        if v2_analysis.parsed:
            v2_parsed_count += 1

        per_sample.append(
            PTrapSampleRow(
                sample_id=sample_id,
                v1_k=v1_row.k,
                v2_k=v2_row.k,
                v1_captured=v1_captured,
                v2_captured=v2_captured,
                v1_parsed=v1_analysis.parsed,
                v2_parsed=v2_analysis.parsed,
                v1_induced_substitutions=v1_induced,
                v2_induced_substitutions=v2_induced,
            )
        )

    n = len(per_sample)
    v1_slu_f1 = _aggregate_slu_score(v1_scores).slu_f1[2] if v1_scores else 0.0
    v2_slu_f1 = _aggregate_slu_score(v2_scores).slu_f1[2] if v2_scores else 0.0
    v1_parse_rate = v1_parsed_count / n if n else 0.0
    v2_parse_rate = v2_parsed_count / n if n else 0.0

    denom = [row for row in per_sample if row.usable]
    excluded = [row.sample_id for row in per_sample if not row.usable]
    n_usable = len(denom)
    v1_capture_count = sum(1 for row in denom if row.v1_captured)
    v2_capture_count = sum(1 for row in denom if row.v2_captured)
    v1_capture_rate = v1_capture_count / n_usable if n_usable else 0.0
    v2_capture_rate = v2_capture_count / n_usable if n_usable else 0.0
    rate_diff = v1_capture_rate - v2_capture_rate
    raw_diff = v1_capture_count - v2_capture_count

    harness_defect_reasons = _harness_defect_reasons(
        flight_status=flight_status,
        flight_error=flight_error,
        rows_by_arm=rows_by_arm,
        sample_ids=sample_ids,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_keys=duplicate_keys,
        gold_entities_by_sample_id=gold_entities_by_sample_id,
    )

    point = evaluate_point(rate_diff, raw_diff)
    reachability = compute_reachability_statement(per_sample, n_samples=n)
    if n_usable:
        bootstrap = compute_capture_bootstrap(
            v1_captured_by_sample={row.sample_id: row.v1_captured for row in denom},
            v2_captured_by_sample={row.sample_id: row.v2_captured for row in denom},
            common_denominator=[row.sample_id for row in denom],
        )
    else:
        # A degenerate all-K=0 shape (every sample excluded): still produce
        # a well-formed, zero-variance bootstrap rather than crash the
        # whole report -- reachability already reports this as UNREACHABLE,
        # and the CI-gated evaluator falls through to INCONCLUSIVE-TRAP.
        bootstrap = paired_cluster_bootstrap(
            sample_ids=("__no_usable_sample__",), statistic=lambda _ids: 0.0
        )
    ci_verdict = evaluate_ptrap_ci_gated(point, bootstrap, reachability)

    return PTrapReadReport(
        attempt_dir=attempt_dir,
        flight_status=flight_status,
        flight_error=flight_error,
        per_sample=tuple(per_sample),
        v1_slu_f1=v1_slu_f1,
        v2_slu_f1=v2_slu_f1,
        v1_parse_rate=v1_parse_rate,
        v2_parse_rate=v2_parse_rate,
        v1_empty_rate=1.0 - v1_parse_rate,
        v2_empty_rate=1.0 - v2_parse_rate,
        v1_induced_substitution_total=v1_induced_total,
        v2_induced_substitution_total=v2_induced_total,
        v1_capture_count=v1_capture_count,
        v2_capture_count=v2_capture_count,
        v1_capture_rate=v1_capture_rate,
        v2_capture_rate=v2_capture_rate,
        n_usable=n_usable,
        n_excluded=len(excluded),
        excluded_sample_ids=tuple(sorted(excluded)),
        harness_defect_reasons=harness_defect_reasons,
        recheck_mismatches=tuple(recheck_mismatches),
        ci_verdict=ci_verdict,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def report_to_json(report: PTrapReadReport) -> dict[str, object]:
    verdict = report.ci_verdict
    return {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "flight_error": report.flight_error,
        "n_samples": len(report.per_sample),
        "n_usable": report.n_usable,
        "n_excluded": report.n_excluded,
        "excluded_sample_ids": list(report.excluded_sample_ids),
        "per_sample": [
            {
                "sample_id": row.sample_id,
                "v1_k": row.v1_k,
                "v2_k": row.v2_k,
                "v1_captured": row.v1_captured,
                "v2_captured": row.v2_captured,
                "v1_parsed": row.v1_parsed,
                "v2_parsed": row.v2_parsed,
                "v1_induced_substitutions": row.v1_induced_substitutions,
                "v2_induced_substitutions": row.v2_induced_substitutions,
                "usable": row.usable,
            }
            for row in report.per_sample
        ],
        "guardrails": {
            "consumed_a3_slu_f1": CONSUMED_A3_SLU_F1,
            "v1_slu_f1": report.v1_slu_f1,
            "v2_slu_f1": report.v2_slu_f1,
            "v1_slu_f1_delta_vs_a3": report.v1_slu_f1 - CONSUMED_A3_SLU_F1,
            "v2_slu_f1_delta_vs_a3": report.v2_slu_f1 - CONSUMED_A3_SLU_F1,
            "v1_parse_rate": report.v1_parse_rate,
            "v2_parse_rate": report.v2_parse_rate,
            "v1_empty_rate": report.v1_empty_rate,
            "v2_empty_rate": report.v2_empty_rate,
            "v1_induced_substitution_total": report.v1_induced_substitution_total,
            "v2_induced_substitution_total": report.v2_induced_substitution_total,
        },
        "capture": {
            "v1_capture_count": report.v1_capture_count,
            "v2_capture_count": report.v2_capture_count,
            "v1_capture_rate": report.v1_capture_rate,
            "v2_capture_rate": report.v2_capture_rate,
            "rate_diff": verdict.point.rate_diff,
            "raw_diff": verdict.point.raw_diff,
        },
        "recheck_mismatch_count": len(report.recheck_mismatches),
        "harness_defect_reasons": list(report.harness_defect_reasons),
        "reachability": {
            "n_samples": verdict.reachability.n_samples,
            "n_usable": verdict.reachability.n_usable,
            "max_attainable_rate_diff": verdict.reachability.max_attainable_rate_diff,
            "max_attainable_raw_diff": verdict.reachability.max_attainable_raw_diff,
            "acoustic_mediated_reachable": verdict.reachability.acoustic_mediated_reachable,
            "detail": verdict.reachability.detail,
        },
        "bootstrap": verdict.bootstrap.as_json(),
        "verdict": {
            "acoustic_mediated_point": _clause_json(verdict.point.acoustic_mediated_point),
            "key_only_matching_point": _clause_json(verdict.point.key_only_matching_point),
            "acoustic_mediated": _clause_json(verdict.acoustic_mediated),
            "key_only_matching": _clause_json(verdict.key_only_matching),
            "overall": verdict.overall,
        },
    }


def render_report(report: PTrapReadReport) -> str:
    verdict = report.ci_verdict
    lines = [
        "P-TRAP pinned offline read (docs/readiness/2026-08-19-ptrap-preregistration-REGISTERED.md)",
        "=" * 70,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r} (error={report.flight_error!r})",
        f"n_samples={len(report.per_sample)} n_usable={report.n_usable} n_excluded={report.n_excluded}",
        "",
        "Guardrails (descriptive, never verdict-gating)",
        f"  consumed A3 SLU-F1={CONSUMED_A3_SLU_F1:.4f} (cited); "
        f"V1 SLU-F1={report.v1_slu_f1:.4f} (delta {report.v1_slu_f1 - CONSUMED_A3_SLU_F1:+.4f}); "
        f"V2 SLU-F1={report.v2_slu_f1:.4f} (delta {report.v2_slu_f1 - CONSUMED_A3_SLU_F1:+.4f})",
        f"  parse rate: V1={report.v1_parse_rate:.4f} V2={report.v2_parse_rate:.4f}; "
        f"empty rate: V1={report.v1_empty_rate:.4f} V2={report.v2_empty_rate:.4f}",
        f"  induced substitutions: V1={report.v1_induced_substitution_total} V2={report.v2_induced_substitution_total}",
        "",
        "Per-sample table",
    ]
    header = f"  {'sample_id':<48}{'v1_k':>5}{'v2_k':>5}{'v1_cap':>7}{'v2_cap':>7}{'usable':>7}"
    lines.append(header)
    for row in report.per_sample:
        lines.append(
            f"  {row.sample_id:<48}{row.v1_k:>5}{row.v2_k:>5}{str(row.v1_captured):>7}"
            f"{str(row.v2_captured):>7}{str(row.usable):>7}"
        )
    lines.append("")

    if report.harness_defect_reasons:
        lines.append("!" * 70)
        lines.append("HARNESS DEFECT REASONS")
        for reason in report.harness_defect_reasons:
            lines.append(f"  {reason}")
        lines.append("!" * 70)
        lines.append("")

    lines.append(f"recheck mismatches (TP/FP/FN vs adapter's committed scorer): {len(report.recheck_mismatches)}")
    lines.append("")

    lines.append(
        f"capture(V1)={report.v1_capture_rate:.4f} ({report.v1_capture_count}/{report.n_usable}) "
        f"capture(V2)={report.v2_capture_rate:.4f} ({report.v2_capture_count}/{report.n_usable}) "
        f"rate_diff={verdict.point.rate_diff:+.4f} raw_diff={verdict.point.raw_diff:+d}"
    )
    lines.append("")

    lines.append("Mandatory pre-read reachability statement (2026-08-19 amendment section 6)")
    lines.append(f"  {verdict.reachability.detail}")
    lines.append("")

    lines.append(
        f"Per-sample paired cluster bootstrap over the V1-V2 capture difference: "
        f"sigma_hat={verdict.bootstrap.sigma_hat:.4f} 90% CI=[{verdict.bootstrap.ci_low:+.4f}, "
        f"{verdict.bootstrap.ci_high:+.4f}] (N={verdict.bootstrap.n_replicates} replicates, "
        f"seed={verdict.bootstrap.seed})"
    )
    lines.append("")

    lines.append(f"ACOUSTIC-MEDIATED: {'MET' if verdict.acoustic_mediated.verdict == 'met' else 'not met'}")
    lines.append(f"  point: [{verdict.point.acoustic_mediated_point.verdict.upper():>8}] {verdict.point.acoustic_mediated_point.detail}")
    lines.append(f"  CI-gated: [{verdict.acoustic_mediated.verdict.upper():>8}] {verdict.acoustic_mediated.detail}")
    lines.append("")

    lines.append(f"KEY-ONLY-MATCHING: {'MET' if verdict.key_only_matching.verdict == 'met' else 'not met'}")
    lines.append(f"  point: [{verdict.point.key_only_matching_point.verdict.upper():>8}] {verdict.point.key_only_matching_point.detail}")
    lines.append(f"  CI-gated: [{verdict.key_only_matching.verdict.upper():>8}] {verdict.key_only_matching.detail}")
    lines.append("")

    lines.append(f"OVERALL: {verdict.overall}")
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="ptrap-read",
        description=(
            "P-TRAP pinned offline read suite: capture detector, per-sample table, official SLU-F1 "
            "guardrail vs the cited consumed A3 aggregate, induced-substitution count, empty/parse "
            "rates, the per-sample paired cluster bootstrap CI, the mandatory reachability statement, "
            "and the CI-gated ACOUSTIC-MEDIATED/KEY-ONLY-MATCHING/INCONCLUSIVE-TRAP evaluator. "
            "Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the P-TRAP flight's own attempt directory (carries outputs.jsonl)")
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
        report = build_ptrap_report(
            args.attempt_dir,
            lock,
            root,
            sample_manifest_path=sample_manifest_path,
            roster_table_path=roster_table_path,
        )
    except PTrapReadError as error:
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
    "ACOUSTIC_MEDIATED_MIN_RATE_DIFF",
    "ACOUSTIC_MEDIATED_MIN_RAW_DIFF",
    "CONSUMED_A3_SLU_F1",
    "CONSUMED_PSLU_ARM",
    "KEY_ONLY_MATCHING_MAX_ABS",
    "REPORT_SCHEMA",
    "ClauseResult",
    "HarvestYield",
    "PTrapCIVerdict",
    "PTrapOutputRow",
    "PTrapPointVerdict",
    "PTrapReadError",
    "PTrapReadReport",
    "PTrapSampleRow",
    "ReachabilityStatement",
    "build_ptrap_report",
    "compute_capture_bootstrap",
    "compute_reachability_statement",
    "evaluate_point",
    "evaluate_ptrap_ci_gated",
    "harvest_a0_wrong_values",
    "load_attempt_rows",
    "main",
    "render_report",
    "report_to_json",
    "response_captures_trap",
]
