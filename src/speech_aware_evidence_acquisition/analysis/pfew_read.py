"""P-FEW offline read suite (pinned, pre-registered, SAEA-PROBE-pfew-180).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` / ``flight-receipt.json``
(``rails.probes.pfew_flight.run_pfew_flight``'s own row shape) mechanically,
against ``docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md``
section 3.

Sources of truth this module implements EXACTLY (never re-derives on its own
authority): the preregistration's own section 3 (metrics, verdicts) and
section 5 (discipline); ``configs/probes/g0-binding/pslu-sample-devel-n60.json``
/ ``pslu-rosters-train-only.json`` (the SAME frozen sample set and roster
table the consumed P-SLU/P-TRAP/P-KEY probes used, loaded via
``rails.probes.pslu_flight``'s own loaders).

REUSE, NOT RE-DERIVATION (mirrors every sibling read module's own explicit
discipline section): ``rails.probes.pslu_s2_flight.canonical_scenario_labels``
/ ``map_predicted_scenario_to_canonical`` / ``ClosedSetMapping`` (the SAME
closed-set parser the flight itself used, reused here to independently
RE-DERIVE each row's own mapping from its response text -- never trusting
the embedded field blindly, see note 1 below); ``rails.probes.pfew_flight.
PFEW_ARMS`` / ``FS_NONE_ARM`` / ``FS_BAL_ARM`` / ``FS_SKEW_ARM`` (never a
second, hand-typed spelling of an arm name); ``analysis.pslu_read.
load_gold_by_sample_id`` / ``RUNTIME_PROHIBITED_NOTE`` (the SAME devel-gold
loader every sibling read module uses); ``analysis.bootstrap.
paired_cluster_bootstrap`` (the SAME shared per-sample paired cluster
bootstrap core ``analysis.pkey_read``/``analysis.ptrap_read`` already use).

ENGINEERING-INTERPRETATION NOTES (flagged here, not buried -- mirrors this
probe family's own established discipline):

1. Mapping-outcome bookkeeping (chosen label / outcome / fallback) is read
   directly off each row's own embedded ``closed_set_mapping`` field
   (``rails.probes.pfew_flight.PFewArmResult``'s own write shape, the
   ``rails.probes.pslu_s2_flight.ClosedSetMapping.as_json`` shape) for the
   headline accuracy/outcome-distribution numbers -- never re-derived here
   for SCORING purposes (mirrors ``analysis.pslu_s2_read``'s own note 5).
   A SEPARATE, independent re-derivation from each row's own
   ``response_text`` (:func:`_rederive_mapping`) is run purely as a
   harness-defect CHECK: any disagreement between the embedded field and
   the re-derivation is reported (``harness_defect_reasons``), never
   silently trusted, never gating any of the four registered verdicts (this
   probe's own preregistration names no VOID branch -- unlike P-SLU/
   P-TRAP/P-KEY -- so a structural anomaly is disclosed, not silently
   folded into an invented gate this module has no registered authority to
   add).
2. "closed-set scenario accuracy vs gold" (registration section 3) is read
   as the MAPPED canonical label (``closed_set_mapping.canonical_label``)
   compared to the sample's own gold scenario -- not the raw parsed
   ``predicted_scenario`` string, which the SAME closed-set parser may have
   already normalized through a case-insensitive/substring match (or
   ``None``, on an unmapped/unparsed response). This is the metric the
   registered "closed-set scenario choice" framing is actually about: a
   router forced to pick one of 18 labels is scored on WHICH of those 18 it
   picked, not on the literal bytes it emitted.
3. The skew-label capture rate's own denominator (registration section 3:
   "on samples where it is wrong") EXCLUDES every sample whose own gold
   scenario happens to equal the seeded skew label -- the registered,
   disclosed "wrong-for-most" reading (``rails.probes.pfew_flight.
   build_demo_binding``'s own docstring: the skew label is chosen ONCE,
   globally, before any gold is read, so it is provably correct for SOME
   samples by chance; the capture concept -- "did the router parrot a demo
   prior that pointed at the WRONG answer" -- is undefined on those, so
   they are excluded from the denominator, never counted as either a
   capture or a non-capture). See :func:`compute_skew_capture`.
4. FS-INERT (equivalence) is CI-gated per "the program's amendment
   discipline" the registration text itself names (verbatim: "equivalence,
   CI-gated per the program's amendment discipline") -- the SAME
   "unreachable branches may not be reported as affirmative outcomes" rule
   ``analysis.ptrap_read``/``analysis.pkey_read`` already document and
   implement for their own equivalence clauses (KEY-ONLY-MATCHING /
   KEY-ONLY): FS-INERT may not fire as an affirmative "no help" finding
   when FS-HELPS was never reachable given FS-NONE's own measured accuracy
   (a router already at or near the 1.0 ceiling cannot show a +0.10 gain,
   so measuring "no gain" there is trivial, not evidence of inertness).
   BIAS-SENSITIVE needs no separate reachability gate of its own (mirrors
   ``analysis.ptrap_read`` module docstring note 4's own ACOUSTIC-MEDIATED
   reasoning): it is a PRESENCE claim whose own two-ingredient point
   threshold (rate diff + capture rate) already implies enough headroom
   whenever it fires. See :func:`evaluate_pfew_ci_gated`.
5. This probe's own preregistration names no VOID branch (contrast P-SLU/
   P-TRAP/P-KEY, which all register one) -- structural/harness-defect
   findings are therefore REPORTED (``harness_defect_reasons``), never
   folded into a gate this module has no registered authority to invent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..rails.probes.pfew_flight import FS_BAL_ARM, FS_NONE_ARM, FS_SKEW_ARM, PFEW_ARMS
from ..rails.probes.pslu_flight import load_pslu_rosters, load_pslu_sample_manifest
from ..rails.probes.pslu_s2_flight import (
    ClosedSetMapping,
    canonical_scenario_labels,
    map_predicted_scenario_to_canonical,
)
from ..reproduction.slurp_scoring import parse_slu_response
from .bootstrap import (
    BootstrapResult,
    DEFAULT_CI_LEVEL as BOOTSTRAP_CI_LEVEL,
    DEFAULT_N_REPLICATES as BOOTSTRAP_N_REPLICATES,
    DEFAULT_SEED as BOOTSTRAP_SEED,
    paired_cluster_bootstrap,
)
from .pslu_read import RUNTIME_PROHIBITED_NOTE, load_gold_by_sample_id

REPORT_SCHEMA = "saea-pfew-read-v1"

# docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md section 3,
# quoted verbatim in each clause's own detail text below.
FS_HELPS_MIN_DIFF = 0.10
FS_INERT_MAX_ABS = 0.05
BIAS_SENSITIVE_MIN_DIFF = 0.15
BIAS_SENSITIVE_MIN_CAPTURE = 0.25

N_SAMPLES = 60


class PFewReadError(RuntimeError):
    """Malformed attempt-dir/binding input for this read -- never raised for
    a legitimate INCONCLUSIVE-FEW-worthy data shape (that is reported as a
    clause result, not an exception)."""


# ---------------------------------------------------------------------------
# Loading: outputs.jsonl / flight-receipt.json.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PFewOutputRow:
    arm: str
    sample_id: str
    messages: tuple[Mapping[str, object], ...]
    response_text: str
    metrics: Mapping[str, object]
    consumption: Mapping[str, object]
    closed_set_mapping: Mapping[str, object] | None
    demos: tuple[Mapping[str, object], ...]

    @classmethod
    def from_json(cls, document: Mapping[str, object]) -> "PFewOutputRow":
        return cls(
            arm=str(document["arm"]),
            sample_id=str(document["sample_id"]),
            messages=tuple(document["messages"]),
            response_text=str(document["response_text"]),
            metrics=document["metrics"],
            consumption=document["consumption"],
            closed_set_mapping=document.get("closed_set_mapping"),
            demos=tuple(document.get("demos", ())),
        )


def load_attempt_rows(attempt_dir: Path) -> tuple[PFewOutputRow, ...]:
    path = Path(attempt_dir) / "outputs.jsonl"
    if not path.is_file():
        raise PFewReadError(f"no outputs.jsonl under attempt dir {attempt_dir}")
    rows: list[PFewOutputRow] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            document = json.loads(line)
        except json.JSONDecodeError as error:
            raise PFewReadError(f"{path} line {line_no}: invalid JSON: {error}") from error
        rows.append(PFewOutputRow.from_json(document))
    if not rows:
        raise PFewReadError(f"{path}: zero rows")
    return tuple(rows)


def load_flight_status(attempt_dir: Path) -> tuple[str | None, str | None]:
    path = Path(attempt_dir) / "flight-receipt.json"
    if not path.is_file():
        return None, "flight-receipt.json missing"
    document = json.loads(path.read_text(encoding="utf-8"))
    return document.get("status"), document.get("error")


# ---------------------------------------------------------------------------
# Per-row mapping (module docstring note 1).
# ---------------------------------------------------------------------------


def _row_mapping(row: PFewOutputRow) -> Mapping[str, object]:
    return row.closed_set_mapping or {
        "predicted_raw": None,
        "canonical_label": None,
        "outcome": "unmapped",
        "fallback": True,
    }


def _rederive_mapping(row: PFewOutputRow, canonical_labels: Sequence[str]) -> ClosedSetMapping:
    predicted_scenario, _action, _entities, parsed = parse_slu_response(row.response_text)
    return map_predicted_scenario_to_canonical(predicted_scenario if parsed else None, canonical_labels)


# ---------------------------------------------------------------------------
# Per-sample 3-arm table.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PFewSampleRow:
    sample_id: str
    gold_scenario: str
    fs_none_label: str | None
    fs_bal_label: str | None
    fs_skew_label: str | None
    fs_none_correct: bool
    fs_bal_correct: bool
    fs_skew_correct: bool


# ---------------------------------------------------------------------------
# Skew-label capture rate (module docstring note 3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SkewCaptureStats:
    skew_label: str
    n_samples: int
    n_excluded_gold_equals_skew: int
    n_denominator: int
    capture_count: int
    capture_rate: float


def compute_skew_capture(per_sample: Sequence[PFewSampleRow], skew_label: str) -> SkewCaptureStats:
    """"the skew-label capture rate (fraction of FS-SKEW answers equal to
    the skewed label on samples where it is wrong)" (registration section 3,
    verbatim) -- the denominator EXCLUDES every sample whose own gold
    scenario equals ``skew_label`` (module docstring note 3: the capture
    concept is undefined there, scoring-side accounting, disclosed)."""

    denominator = [row for row in per_sample if row.gold_scenario != skew_label]
    capture_count = sum(1 for row in denominator if row.fs_skew_label == skew_label)
    n_denominator = len(denominator)
    capture_rate = capture_count / n_denominator if n_denominator else 0.0
    return SkewCaptureStats(
        skew_label=skew_label,
        n_samples=len(per_sample),
        n_excluded_gold_equals_skew=len(per_sample) - n_denominator,
        n_denominator=n_denominator,
        capture_count=capture_count,
        capture_rate=capture_rate,
    )


# ---------------------------------------------------------------------------
# Mandatory pre-read reachability statement (registration section 3: "Pre-read
# reachability statement mandatory (headroom on each contrast given FS-NONE's
# own measured accuracy)").
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReachabilityStatement:
    fs_none_accuracy: float
    max_attainable_bal_none_diff: float
    fs_helps_reachable: bool
    max_attainable_none_skew_diff: float
    bias_sensitive_reachable: bool
    detail: str


def compute_reachability_statement(fs_none_accuracy: float) -> ReachabilityStatement:
    """Self-contained arithmetic from THIS run's own FS-NONE accuracy
    (module docstring note 4): best case for BAL-NONE is FS-BAL at 1.0 ->
    ``max_attainable_bal_none_diff = 1.0 - fs_none_accuracy``; best case for
    NONE-SKEW is FS-SKEW at 0.0 -> ``max_attainable_none_skew_diff =
    fs_none_accuracy``."""

    max_bal_none = 1.0 - fs_none_accuracy
    max_none_skew = fs_none_accuracy
    fs_helps_reachable = max_bal_none >= FS_HELPS_MIN_DIFF
    bias_sensitive_reachable = max_none_skew >= BIAS_SENSITIVE_MIN_DIFF
    detail = (
        f"FS-NONE accuracy={fs_none_accuracy:.4f}. BAL-NONE contrast: best case FS-BAL=1.0 -> "
        f"max_attainable_diff={max_bal_none:.4f} (FS-HELPS floor +{FS_HELPS_MIN_DIFF:.2f}) -> "
        f"{'REACHABLE' if fs_helps_reachable else 'UNREACHABLE'}. NONE-SKEW contrast: best case "
        f"FS-SKEW=0.0 -> max_attainable_diff={max_none_skew:.4f} (BIAS-SENSITIVE floor "
        f"+{BIAS_SENSITIVE_MIN_DIFF:.2f}) -> {'REACHABLE' if bias_sensitive_reachable else 'UNREACHABLE'}."
    )
    return ReachabilityStatement(
        fs_none_accuracy=fs_none_accuracy,
        max_attainable_bal_none_diff=max_bal_none,
        fs_helps_reachable=fs_helps_reachable,
        max_attainable_none_skew_diff=max_none_skew,
        bias_sensitive_reachable=bias_sensitive_reachable,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Per-sample paired cluster bootstrap over both registered contrasts.
# ---------------------------------------------------------------------------


def compute_bal_none_bootstrap(
    *,
    fs_bal_correct_by_sample: Mapping[str, bool],
    fs_none_correct_by_sample: Mapping[str, bool],
    sample_ids: Sequence[str],
    n_replicates: int = BOOTSTRAP_N_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = BOOTSTRAP_CI_LEVEL,
) -> BootstrapResult:
    """acc(FS-BAL) - acc(FS-NONE), per-sample paired cluster bootstrap
    (``analysis.bootstrap``, shared with every sibling probe's own CI)."""

    ids = tuple(sample_ids)
    if not ids:
        raise PFewReadError("compute_bal_none_bootstrap: empty sample_ids -- cannot bootstrap zero samples")

    def statistic(resampled: Sequence[str]) -> float:
        bal_rate = sum(1 for sample_id in resampled if fs_bal_correct_by_sample[sample_id]) / len(resampled)
        none_rate = sum(1 for sample_id in resampled if fs_none_correct_by_sample[sample_id]) / len(resampled)
        return bal_rate - none_rate

    return paired_cluster_bootstrap(
        sample_ids=ids, statistic=statistic, n_replicates=n_replicates, seed=seed, ci_level=ci_level
    )


def compute_none_skew_bootstrap(
    *,
    fs_none_correct_by_sample: Mapping[str, bool],
    fs_skew_correct_by_sample: Mapping[str, bool],
    sample_ids: Sequence[str],
    n_replicates: int = BOOTSTRAP_N_REPLICATES,
    seed: int = BOOTSTRAP_SEED,
    ci_level: float = BOOTSTRAP_CI_LEVEL,
) -> BootstrapResult:
    """acc(FS-NONE) - acc(FS-SKEW), per-sample paired cluster bootstrap."""

    ids = tuple(sample_ids)
    if not ids:
        raise PFewReadError("compute_none_skew_bootstrap: empty sample_ids -- cannot bootstrap zero samples")

    def statistic(resampled: Sequence[str]) -> float:
        none_rate = sum(1 for sample_id in resampled if fs_none_correct_by_sample[sample_id]) / len(resampled)
        skew_rate = sum(1 for sample_id in resampled if fs_skew_correct_by_sample[sample_id]) / len(resampled)
        return none_rate - skew_rate

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
class PFewPointVerdict:
    bal_none_diff: float
    none_skew_diff: float
    capture_rate: float
    fs_helps_point: ClauseResult
    fs_inert_point: ClauseResult
    bias_sensitive_point: ClauseResult


def evaluate_point(bal_none_diff: float, none_skew_diff: float, capture_rate: float) -> PFewPointVerdict:
    """The REGISTERED point thresholds (preregistration section 3)."""

    helps_met = bal_none_diff >= FS_HELPS_MIN_DIFF
    fs_helps_point = ClauseResult(
        f"acc(FS-BAL) - acc(FS-NONE) >= +{FS_HELPS_MIN_DIFF:.2f}",
        "met" if helps_met else "not_met",
        f"diff={bal_none_diff:+.4f}, floor=+{FS_HELPS_MIN_DIFF:.2f}",
    )
    inert_met = abs(bal_none_diff) <= FS_INERT_MAX_ABS
    fs_inert_point = ClauseResult(
        f"|acc(FS-BAL) - acc(FS-NONE)| <= {FS_INERT_MAX_ABS:.2f}",
        "met" if inert_met else "not_met",
        f"diff={bal_none_diff:+.4f}, ceiling=+/-{FS_INERT_MAX_ABS:.2f}",
    )
    bias_met = none_skew_diff >= BIAS_SENSITIVE_MIN_DIFF and capture_rate >= BIAS_SENSITIVE_MIN_CAPTURE
    bias_sensitive_point = ClauseResult(
        f"acc(FS-NONE) - acc(FS-SKEW) >= +{BIAS_SENSITIVE_MIN_DIFF:.2f} AND skew-label capture rate >= "
        f"{BIAS_SENSITIVE_MIN_CAPTURE:.2f}",
        "met" if bias_met else "not_met",
        f"none_skew_diff={none_skew_diff:+.4f} (floor +{BIAS_SENSITIVE_MIN_DIFF:.2f}), "
        f"capture_rate={capture_rate:.4f} (floor {BIAS_SENSITIVE_MIN_CAPTURE:.2f})",
    )
    return PFewPointVerdict(
        bal_none_diff=bal_none_diff,
        none_skew_diff=none_skew_diff,
        capture_rate=capture_rate,
        fs_helps_point=fs_helps_point,
        fs_inert_point=fs_inert_point,
        bias_sensitive_point=bias_sensitive_point,
    )


@dataclass(frozen=True)
class PFewCIVerdict:
    point: PFewPointVerdict
    bal_none_bootstrap: BootstrapResult
    none_skew_bootstrap: BootstrapResult
    reachability: ReachabilityStatement
    fs_helps: ClauseResult
    fs_inert: ClauseResult
    bias_sensitive: ClauseResult
    overall: str


def evaluate_pfew_ci_gated(
    point: PFewPointVerdict,
    bal_none_bootstrap: BootstrapResult,
    none_skew_bootstrap: BootstrapResult,
    reachability: ReachabilityStatement,
) -> PFewCIVerdict:
    """Registration section 3: "FS-HELPS: ... AND CI lower bound > 0";
    "FS-INERT: ... (equivalence, CI-gated per the program's amendment
    discipline)"; "BIAS-SENSITIVE (independent overlay): ..." (point-only,
    module docstring note 4: no separate reachability gate needed, its own
    point threshold already implies enough headroom whenever it fires);
    "Otherwise INCONCLUSIVE-FEW"."""

    helps_ci_met = bal_none_bootstrap.ci_low > 0.0
    fs_helps_met = point.fs_helps_point.verdict == "met" and helps_ci_met
    fs_helps = ClauseResult(
        "registered point threshold met AND the bootstrap CI lower bound of the BAL-NONE accuracy "
        "difference is > 0",
        "met" if fs_helps_met else "not_met",
        f"point={point.fs_helps_point.verdict}, CI=[{bal_none_bootstrap.ci_low:+.4f}, "
        f"{bal_none_bootstrap.ci_high:+.4f}] (sigma_hat={bal_none_bootstrap.sigma_hat:.4f}, "
        f"n_replicates={bal_none_bootstrap.n_replicates}); ci_low>0 is {helps_ci_met}",
    )

    ci_within_band = bal_none_bootstrap.contains(-FS_INERT_MAX_ABS, FS_INERT_MAX_ABS)
    if point.fs_inert_point.verdict != "met":
        inert_met = False
        inert_detail = (
            f"point diff={point.bal_none_diff:+.4f} already outside the +/-{FS_INERT_MAX_ABS:.2f} band"
        )
    elif not ci_within_band:
        inert_met = False
        inert_detail = (
            f"CI=[{bal_none_bootstrap.ci_low:+.4f}, {bal_none_bootstrap.ci_high:+.4f}] is NOT entirely "
            f"inside [-{FS_INERT_MAX_ABS:.2f}, +{FS_INERT_MAX_ABS:.2f}] -- a point estimate inside the "
            "band with a CI crossing it is INCONCLUSIVE-FEW, never an affirmative FS-INERT"
        )
    elif not reachability.fs_helps_reachable:
        inert_met = False
        inert_detail = (
            f"CI=[{bal_none_bootstrap.ci_low:+.4f}, {bal_none_bootstrap.ci_high:+.4f}] IS entirely inside "
            "the band, but FS-HELPS is UNREACHABLE given FS-NONE's own accuracy "
            f"(max_attainable_bal_none_diff={reachability.max_attainable_bal_none_diff:.4f} < "
            f"{FS_HELPS_MIN_DIFF:.2f}) -- FS-INERT may not be reported as an affirmative negative under "
            "an unreachable alternative (mirrors the program's amendment discipline, ptrap/pkey "
            "precedent); INCONCLUSIVE-FEW with the reachability bound instead"
        )
    else:
        inert_met = True
        inert_detail = (
            f"CI=[{bal_none_bootstrap.ci_low:+.4f}, {bal_none_bootstrap.ci_high:+.4f}] entirely inside "
            f"the band; FS-HELPS reachable "
            f"(max_attainable_bal_none_diff={reachability.max_attainable_bal_none_diff:.4f})"
        )
    fs_inert = ClauseResult(
        f"|point diff| <= {FS_INERT_MAX_ABS:.2f} AND the ENTIRE {bal_none_bootstrap.ci_level:.0%} bootstrap "
        f"CI lies inside [-{FS_INERT_MAX_ABS:.2f}, +{FS_INERT_MAX_ABS:.2f}] AND FS-HELPS is reachable given "
        "FS-NONE's own accuracy",
        "met" if inert_met else "not_met",
        inert_detail,
    )

    # BIAS-SENSITIVE: independent overlay, point-only (module docstring note 4).
    bias_sensitive = point.bias_sensitive_point

    if fs_helps.verdict == "met":
        primary = "FS-HELPS"
    elif fs_inert.verdict == "met":
        primary = "FS-INERT"
    else:
        primary = "INCONCLUSIVE-FEW"
    overall = primary + (" + BIAS-SENSITIVE" if bias_sensitive.verdict == "met" else "")

    return PFewCIVerdict(
        point=point,
        bal_none_bootstrap=bal_none_bootstrap,
        none_skew_bootstrap=none_skew_bootstrap,
        reachability=reachability,
        fs_helps=fs_helps,
        fs_inert=fs_inert,
        bias_sensitive=bias_sensitive,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PFewReadReport:
    attempt_dir: Path
    flight_status: str | None
    flight_error: str | None
    skew_label: str | None
    per_sample: tuple[PFewSampleRow, ...]
    fs_none_accuracy: float
    fs_bal_accuracy: float
    fs_skew_accuracy: float
    outcome_counts: Mapping[str, Mapping[str, int]]
    capture_stats: SkewCaptureStats
    harness_defect_reasons: tuple[str, ...]
    ci_verdict: PFewCIVerdict


def build_pfew_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    sample_manifest_path: Path,
    roster_table_path: Path,
) -> PFewReadReport:
    attempt_dir = Path(attempt_dir)
    rows = load_attempt_rows(attempt_dir)
    flight_status, flight_error = load_flight_status(attempt_dir)

    manifest = load_pslu_sample_manifest(sample_manifest_path)
    rosters = load_pslu_rosters(roster_table_path)
    sample_ids = manifest.sample_ids
    canonical_labels = canonical_scenario_labels(rosters)

    gold_by_id = load_gold_by_sample_id(lock, root, sample_ids)  # RUNTIME_PROHIBITED (reused)

    rows_by_arm: dict[str, dict[str, PFewOutputRow]] = {arm: {} for arm in PFEW_ARMS}
    unknown_arm_rows: list[PFewOutputRow] = []
    duplicate_keys: list[tuple[str, str]] = []
    seen_keys: set[tuple[str, str]] = set()
    for row in rows:
        key = (row.arm, row.sample_id)
        if key in seen_keys:
            duplicate_keys.append(key)
            continue
        seen_keys.add(key)
        if row.arm not in PFEW_ARMS:
            unknown_arm_rows.append(row)
            continue
        rows_by_arm[row.arm][row.sample_id] = row

    harness_defect_reasons: list[str] = []
    if flight_status != "COMPLETED":
        harness_defect_reasons.append(
            f"flight-receipt status={flight_status!r} (expected 'COMPLETED'); error={flight_error!r}"
        )
    for row in unknown_arm_rows:
        harness_defect_reasons.append(f"unknown arm {row.arm!r} on sample {row.sample_id!r}")
    for key in duplicate_keys:
        harness_defect_reasons.append(f"duplicate row for (arm, sample_id)={key}")
    id_set = set(sample_ids)
    for arm in PFEW_ARMS:
        got = set(rows_by_arm[arm])
        missing = id_set - got
        extra = got - id_set
        if missing:
            harness_defect_reasons.append(
                f"arm {arm}: missing {len(missing)} sample(s) from the frozen manifest: {sorted(missing)[:5]}"
            )
        if extra:
            harness_defect_reasons.append(
                f"arm {arm}: {len(extra)} sample(s) not in the frozen manifest: {sorted(extra)[:5]}"
            )

    # Skew-label resolution: every FS-SKEW row's own embedded demos must
    # name exactly ONE distinct scenario_label across the whole arm.
    skew_labels_seen: set[str] = set()
    for row in rows_by_arm[FS_SKEW_ARM].values():
        for demo in row.demos:
            label = demo.get("scenario_label")
            if label is not None:
                skew_labels_seen.add(str(label))
    skew_label: str | None
    if len(skew_labels_seen) == 1:
        skew_label = next(iter(skew_labels_seen))
    else:
        skew_label = None
        harness_defect_reasons.append(
            "FS-SKEW rows do not carry a single consistent skew label across their own embedded demos: "
            f"{sorted(skew_labels_seen)}"
        )

    per_sample: list[PFewSampleRow] = []
    outcome_counts: dict[str, dict[str, int]] = {arm: {} for arm in PFEW_ARMS}
    for sample_id in sample_ids:
        gold = gold_by_id.get(sample_id)
        none_row = rows_by_arm[FS_NONE_ARM].get(sample_id)
        bal_row = rows_by_arm[FS_BAL_ARM].get(sample_id)
        skew_row = rows_by_arm[FS_SKEW_ARM].get(sample_id)
        if gold is None or none_row is None or bal_row is None or skew_row is None:
            continue  # already reported as a harness defect above

        mappings: dict[str, Mapping[str, object]] = {}
        for arm, row in ((FS_NONE_ARM, none_row), (FS_BAL_ARM, bal_row), (FS_SKEW_ARM, skew_row)):
            embedded = _row_mapping(row)
            rederived = _rederive_mapping(row, canonical_labels).as_json()
            if embedded != rederived:
                harness_defect_reasons.append(
                    f"arm {arm} sample {sample_id!r}: embedded closed_set_mapping disagrees with a "
                    "re-derivation from its own response_text"
                )
            outcome = str(embedded.get("outcome", "unmapped"))
            outcome_counts[arm][outcome] = outcome_counts[arm].get(outcome, 0) + 1
            mappings[arm] = embedded

        none_label = mappings[FS_NONE_ARM].get("canonical_label")
        bal_label = mappings[FS_BAL_ARM].get("canonical_label")
        skew_pred_label = mappings[FS_SKEW_ARM].get("canonical_label")
        per_sample.append(
            PFewSampleRow(
                sample_id=sample_id,
                gold_scenario=gold.scenario,
                fs_none_label=none_label,
                fs_bal_label=bal_label,
                fs_skew_label=skew_pred_label,
                fs_none_correct=(none_label == gold.scenario),
                fs_bal_correct=(bal_label == gold.scenario),
                fs_skew_correct=(skew_pred_label == gold.scenario),
            )
        )

    n = len(per_sample)
    fs_none_acc = sum(1 for r in per_sample if r.fs_none_correct) / n if n else 0.0
    fs_bal_acc = sum(1 for r in per_sample if r.fs_bal_correct) / n if n else 0.0
    fs_skew_acc = sum(1 for r in per_sample if r.fs_skew_correct) / n if n else 0.0

    if skew_label is not None and per_sample:
        capture_stats = compute_skew_capture(per_sample, skew_label)
    else:
        capture_stats = SkewCaptureStats(
            skew_label=skew_label or "<unresolved>",
            n_samples=n,
            n_excluded_gold_equals_skew=0,
            n_denominator=0,
            capture_count=0,
            capture_rate=0.0,
        )

    bal_none_diff = fs_bal_acc - fs_none_acc
    none_skew_diff = fs_none_acc - fs_skew_acc
    point = evaluate_point(bal_none_diff, none_skew_diff, capture_stats.capture_rate)
    reachability = compute_reachability_statement(fs_none_acc)

    if per_sample:
        ids = [r.sample_id for r in per_sample]
        bal_none_bootstrap = compute_bal_none_bootstrap(
            fs_bal_correct_by_sample={r.sample_id: r.fs_bal_correct for r in per_sample},
            fs_none_correct_by_sample={r.sample_id: r.fs_none_correct for r in per_sample},
            sample_ids=ids,
        )
        none_skew_bootstrap = compute_none_skew_bootstrap(
            fs_none_correct_by_sample={r.sample_id: r.fs_none_correct for r in per_sample},
            fs_skew_correct_by_sample={r.sample_id: r.fs_skew_correct for r in per_sample},
            sample_ids=ids,
        )
    else:
        # A degenerate zero-usable-sample shape: still produce a well-formed,
        # zero-variance bootstrap rather than crash the whole report --
        # harness_defect_reasons already documents why.
        bal_none_bootstrap = paired_cluster_bootstrap(sample_ids=("__no_sample__",), statistic=lambda _ids: 0.0)
        none_skew_bootstrap = paired_cluster_bootstrap(sample_ids=("__no_sample__",), statistic=lambda _ids: 0.0)

    ci_verdict = evaluate_pfew_ci_gated(point, bal_none_bootstrap, none_skew_bootstrap, reachability)

    return PFewReadReport(
        attempt_dir=attempt_dir,
        flight_status=flight_status,
        flight_error=flight_error,
        skew_label=skew_label,
        per_sample=tuple(per_sample),
        fs_none_accuracy=fs_none_acc,
        fs_bal_accuracy=fs_bal_acc,
        fs_skew_accuracy=fs_skew_acc,
        outcome_counts={arm: dict(counts) for arm, counts in outcome_counts.items()},
        capture_stats=capture_stats,
        harness_defect_reasons=tuple(harness_defect_reasons),
        ci_verdict=ci_verdict,
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def report_to_json(report: PFewReadReport) -> dict[str, object]:
    verdict = report.ci_verdict
    return {
        "runtime_prohibited": True,
        "note": RUNTIME_PROHIBITED_NOTE,
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "flight_error": report.flight_error,
        "skew_label": report.skew_label,
        "n_samples": len(report.per_sample),
        "accuracy": {
            "fs_none": report.fs_none_accuracy,
            "fs_bal": report.fs_bal_accuracy,
            "fs_skew": report.fs_skew_accuracy,
        },
        "mapping_outcome_counts": {arm: dict(counts) for arm, counts in report.outcome_counts.items()},
        "per_sample": [
            {
                "sample_id": r.sample_id,
                "gold_scenario": r.gold_scenario,
                "fs_none_label": r.fs_none_label,
                "fs_bal_label": r.fs_bal_label,
                "fs_skew_label": r.fs_skew_label,
                "fs_none_correct": r.fs_none_correct,
                "fs_bal_correct": r.fs_bal_correct,
                "fs_skew_correct": r.fs_skew_correct,
            }
            for r in report.per_sample
        ],
        "capture": {
            "skew_label": report.capture_stats.skew_label,
            "n_samples": report.capture_stats.n_samples,
            "n_excluded_gold_equals_skew": report.capture_stats.n_excluded_gold_equals_skew,
            "n_denominator": report.capture_stats.n_denominator,
            "capture_count": report.capture_stats.capture_count,
            "capture_rate": report.capture_stats.capture_rate,
        },
        "harness_defect_reasons": list(report.harness_defect_reasons),
        "reachability": {
            "fs_none_accuracy": verdict.reachability.fs_none_accuracy,
            "max_attainable_bal_none_diff": verdict.reachability.max_attainable_bal_none_diff,
            "fs_helps_reachable": verdict.reachability.fs_helps_reachable,
            "max_attainable_none_skew_diff": verdict.reachability.max_attainable_none_skew_diff,
            "bias_sensitive_reachable": verdict.reachability.bias_sensitive_reachable,
            "detail": verdict.reachability.detail,
        },
        "bootstrap": {
            "bal_none": verdict.bal_none_bootstrap.as_json(),
            "none_skew": verdict.none_skew_bootstrap.as_json(),
        },
        "verdict": {
            "fs_helps_point": _clause_json(verdict.point.fs_helps_point),
            "fs_inert_point": _clause_json(verdict.point.fs_inert_point),
            "bias_sensitive_point": _clause_json(verdict.point.bias_sensitive_point),
            "fs_helps": _clause_json(verdict.fs_helps),
            "fs_inert": _clause_json(verdict.fs_inert),
            "bias_sensitive": _clause_json(verdict.bias_sensitive),
            "overall": verdict.overall,
        },
    }


def render_report(report: PFewReadReport) -> str:
    verdict = report.ci_verdict
    lines = [
        "P-FEW pinned offline read (docs/readiness/2026-08-19-pfew-preregistration-REGISTERED.md)",
        "=" * 74,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r} (error={report.flight_error!r})",
        f"skew_label: {report.skew_label!r}",
        f"n_samples={len(report.per_sample)}",
        "",
        "Per-arm closed-set accuracy vs gold (scoring-side)",
        f"  FS-NONE={report.fs_none_accuracy:.4f}  FS-BAL={report.fs_bal_accuracy:.4f}  "
        f"FS-SKEW={report.fs_skew_accuracy:.4f}",
        "",
        "Mapping-outcome distribution per arm",
    ]
    for arm in PFEW_ARMS:
        lines.append(f"  {arm}: {report.outcome_counts.get(arm, {})}")
    lines.append("")

    lines.append("Per-sample 3-arm table")
    header = f"  {'sample_id':<48}{'gold':<14}{'NONE':<14}{'BAL':<14}{'SKEW':<14}"
    lines.append(header)
    for r in report.per_sample:
        lines.append(
            f"  {r.sample_id:<48}{r.gold_scenario:<14}{str(r.fs_none_label):<14}"
            f"{str(r.fs_bal_label):<14}{str(r.fs_skew_label):<14}"
        )
    lines.append("")

    c = report.capture_stats
    lines.append(
        f"Skew-label capture: skew_label={c.skew_label!r}, capture={c.capture_count}/{c.n_denominator} "
        f"(rate={c.capture_rate:.4f}); excluded (gold==skew_label)={c.n_excluded_gold_equals_skew}/"
        f"{c.n_samples}"
    )
    lines.append("")

    if report.harness_defect_reasons:
        lines.append("!" * 74)
        lines.append("HARNESS DEFECT REASONS (reported, this probe registers no VOID gate)")
        for reason in report.harness_defect_reasons:
            lines.append(f"  {reason}")
        lines.append("!" * 74)
        lines.append("")

    lines.append("Mandatory pre-read reachability statement")
    lines.append(f"  {verdict.reachability.detail}")
    lines.append("")

    lines.append(
        f"BAL-NONE bootstrap: sigma_hat={verdict.bal_none_bootstrap.sigma_hat:.4f} "
        f"90% CI=[{verdict.bal_none_bootstrap.ci_low:+.4f}, {verdict.bal_none_bootstrap.ci_high:+.4f}] "
        f"(N={verdict.bal_none_bootstrap.n_replicates}, seed={verdict.bal_none_bootstrap.seed})"
    )
    lines.append(
        f"NONE-SKEW bootstrap: sigma_hat={verdict.none_skew_bootstrap.sigma_hat:.4f} "
        f"90% CI=[{verdict.none_skew_bootstrap.ci_low:+.4f}, {verdict.none_skew_bootstrap.ci_high:+.4f}] "
        f"(N={verdict.none_skew_bootstrap.n_replicates}, seed={verdict.none_skew_bootstrap.seed})"
    )
    lines.append("")

    lines.append(f"FS-HELPS: {'MET' if verdict.fs_helps.verdict == 'met' else 'not met'}")
    lines.append(f"  point: [{verdict.point.fs_helps_point.verdict.upper():>8}] {verdict.point.fs_helps_point.detail}")
    lines.append(f"  CI-gated: [{verdict.fs_helps.verdict.upper():>8}] {verdict.fs_helps.detail}")
    lines.append("")

    lines.append(f"FS-INERT: {'MET' if verdict.fs_inert.verdict == 'met' else 'not met'}")
    lines.append(f"  point: [{verdict.point.fs_inert_point.verdict.upper():>8}] {verdict.point.fs_inert_point.detail}")
    lines.append(f"  CI-gated: [{verdict.fs_inert.verdict.upper():>8}] {verdict.fs_inert.detail}")
    lines.append("")

    lines.append(f"BIAS-SENSITIVE (independent overlay): {'MET' if verdict.bias_sensitive.verdict == 'met' else 'not met'}")
    lines.append(f"  [{verdict.bias_sensitive.verdict.upper():>8}] {verdict.bias_sensitive.detail}")
    lines.append("")

    lines.append(f"OVERALL: {verdict.overall}")
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="pfew-read",
        description=(
            "P-FEW pinned offline read suite: closed-set accuracy per arm vs gold, mapping-outcome "
            "distributions, per-sample 3-arm table, paired bootstrap on both contrasts, skew-label "
            "capture rate, the mandatory reachability statement, and the CI-gated "
            "FS-HELPS/FS-INERT/BIAS-SENSITIVE/INCONCLUSIVE-FEW evaluator. Model-free, read-only; never "
            "opens a model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the P-FEW flight's own attempt directory (carries outputs.jsonl)")
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
        # Idempotence guard: this suite refuses to run twice against the
        # same output dir (one-shot read discipline, registration section 5).
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
        report = build_pfew_report(
            args.attempt_dir,
            lock,
            root,
            sample_manifest_path=sample_manifest_path,
            roster_table_path=roster_table_path,
        )
    except PFewReadError as error:
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
    "BIAS_SENSITIVE_MIN_CAPTURE",
    "BIAS_SENSITIVE_MIN_DIFF",
    "FS_HELPS_MIN_DIFF",
    "FS_INERT_MAX_ABS",
    "N_SAMPLES",
    "REPORT_SCHEMA",
    "ClauseResult",
    "PFewCIVerdict",
    "PFewOutputRow",
    "PFewPointVerdict",
    "PFewReadError",
    "PFewReadReport",
    "PFewSampleRow",
    "ReachabilityStatement",
    "SkewCaptureStats",
    "build_pfew_report",
    "compute_bal_none_bootstrap",
    "compute_none_skew_bootstrap",
    "compute_reachability_statement",
    "compute_skew_capture",
    "evaluate_pfew_ci_gated",
    "evaluate_point",
    "load_attempt_rows",
    "load_flight_status",
    "main",
    "render_report",
    "report_to_json",
]
