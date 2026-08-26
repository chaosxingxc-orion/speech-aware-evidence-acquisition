"""P-A2T whole-population regression-arm (R0/R1) offline read suite (pinned,
pre-registered, ``SAEA-PROBE-a2t-pop-194``): ``docs/readiness/
2026-08-19-a2t-pop-preregistration-REGISTERED.md``.

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written attempt's
``outputs.jsonl`` (``rails.probes.a2t_pop_flight.run_a2t_pop_flight``'s own
row shape, byte-identical to ``rails.probes.a2t_s2_flight.A2tS2ArmResult``'s)
through the SAME frozen scorer primitives every other consumer of this
carrier uses (``reproduction.toolcall_scoring.score_item``/``aggregate``/
``parse_tool_calls_text``, ``data.audio2tool.load_expected_calls`` -- reused
directly, never re-derived).

REUSE, NOT RE-DERIVATION: ``analysis.a2t_s2_read.OutputRow``/
``load_attempt_rows``/``load_flight_receipt``/``parse_argument_defaults``/
``count_induced_substitutions``/``ClauseResult`` (the SAME
``{arm, sample_id, supplied_tool, response, timing}`` row shape and
supply/induced-substitution machinery Stage-2's own read suite already
built and tested) are reused directly rather than re-implemented a second
time; ``analysis.a2t_read.is_empty_tool_call``/``_load_split_receipt`` and
``analysis.bootstrap.paired_cluster_bootstrap`` (the shared bootstrap
primitive, module docstring of that module: "lives here ONCE") are likewise
reused, never re-derived.

Primary metric: EM regressions (EM 1 -> 0) per arm. The 97-id population is
DEFINED as A0's own already-consumed ``tool_accuracy == 1.0 AND
exact_match == 1.0`` set (``rails.probes.a2t_pop_flight`` module docstring),
so every id's OWN A0 baseline is fixed at ``exact_match == 1.0`` by
construction -- mirrors ``analysis.a2t_s2_read``'s own documented note 11
("the A0 baseline is fixed ... by that set's own defining criterion, no
re-fly, no re-load ... is needed"). A "regression" under an arm is therefore
simply that arm's own recomputed ``exact_match == 0.0`` for a row -- no
second A0 re-load is needed to know what it regressed FROM.

INDUCED-SUBSTITUTION GUARDRAIL, "full-registry default-value yardstick"
(prereg section 3, verbatim): unlike ``analysis.a2t_s2_read``'s own
``supplied_argument_values`` (scoped to one (arm, sample)'s own NARROW
roster), this probe's yardstick is the SAME fixed set of every tool's own
default value across the WHOLE 152-row registry, computed ONCE
(:func:`full_registry_supplied_values`) and applied to every row this suite
scores, R0 and R1 alike. R0 shows the whole registry (with defaults) so this
IS literally what it supplies; R1 shows only the correct tool's row with
defaults STRIPPED (``rails.probes.a2t_s2b_flight.render_b1_tool_schemas``),
so this yardstick instead checks whether R1's own OUTPUT reproduces a value
the model was never shown -- a STRONGER, not weaker, guardrail than a
roster-scoped one would be.

ENGINEERING-INTERPRETATION NOTES:

1. Harness-defect checks (malformed rows, non-``COMPLETED`` receipt,
   non-empty ``request_failures``, an unexpected ``arms`` field, a
   split-identity-hash mismatch, an unknown-arm row, a duplicate
   ``(arm, sample_id)`` pair, a per-arm row count other than
   ``EM_CORRECT_N`` (97, the mission's own "97/97" fail-closed check), R0/R1
   sample-id sets that disagree (this is a PAIRED population -- the
   bootstrap and Δreg both require the SAME 97 ids under both arms), or a
   sample id gold cannot resolve) are ALL hard, fail-closed refusals
   (:class:`A2tPopReadError`) raised BEFORE any scoring happens -- mirrors
   ``analysis.a2t_s2_read``'s own convention (its module docstring note 1).
2. Δreg's paired per-sample bootstrap (prereg section 3: "paired per-sample
   bootstrap ... N=10,000, seed 20260807 ... publishes sigma-hat(Δreg) and a
   90% CI") is computed over the intersection of R0/R1 sample ids -- which,
   after the harness-defect gate above, IS exactly the full 97-id population
   (the gate refuses if it were not).
3. The mandatory reachability/stability statement (prereg section 3: "R0's
   own regression count as this population's first re-fly stability datum")
   is descriptive, carries no clause of its own, and is always reachable by
   construction (EM can fall on any/all of the 97 samples) -- the statement
   documents R0's OWN empirical regression count, not a reachability GATE
   the way P-KEY's own statement gates KEY-ONLY (this population has no
   analogous external census to bound against).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from ..reproduction.toolcall_scoring import ItemScore, ToolCall, aggregate, parse_tool_calls_text, score_item
from ..rails.probes.a2t_pop_flight import A2T_POP_ARMS, EM_CORRECT_N, R0_ARM, R1_ARM
from .a2t_read import is_empty_tool_call
from .a2t_s2_read import ClauseResult, OutputRow, count_induced_substitutions, load_attempt_rows, load_flight_receipt, parse_argument_defaults
from .bootstrap import BootstrapResult, DEFAULT_CI_LEVEL, DEFAULT_N_REPLICATES, DEFAULT_SEED, paired_cluster_bootstrap

REPORT_SCHEMA = "saea-a2t-pop-read-v1"
RUN_ID = "SAEA-PROBE-a2t-pop-194"
DEFAULT_SPLIT_ROLE = "discovery"

# Prereg section 3, quoted verbatim in each clause's own detail text below.
REGRESSION_SAFE_DELTA_MAX = 2
REGRESSION_SAFE_CI_UPPER_MAX = 5.0
REGRESSION_COSTLY_DELTA_MIN = 6


class A2tPopReadError(RuntimeError):
    """Malformed attempt-dir input or a harness defect the mission's own
    "machine harness checks, fail-closed" requires refusing on -- never
    raised for an ordinary, structurally clean read."""


# ---------------------------------------------------------------------------
# Full-registry default-value yardstick (module docstring).
# ---------------------------------------------------------------------------


def full_registry_supplied_values(
    registry_rows: Sequence[Mapping[str, str]]
) -> tuple[dict[str, set], tuple[str, ...]]:
    """``{argument_key: {canonical_value, ...}}`` across EVERY tool row in
    the full registry (module docstring: "full-registry default-value
    yardstick"), plus any non-fatal ``argument_defaults`` parse warnings
    (mirrors ``analysis.a2t_s2_read``'s own note 8: undercounting a
    guardrail metric is the fail-safe direction, never a hard refusal).
    Computed ONCE over the WHOLE registry -- not scoped to any one row's own
    narrower supplied roster (module docstring)."""

    from ..reproduction.toolcall_scoring import _canonical_value

    values: dict[str, set] = {}
    warnings: list[str] = []
    for row in registry_rows:
        name = row.get("tool_name", "") or "<unnamed>"
        kwargs, warning = parse_argument_defaults(name, row.get("argument_defaults", ""))
        if warning:
            warnings.append(warning)
        for key, value in kwargs.items():
            values.setdefault(key, set()).add(_canonical_value(value))
    return values, tuple(warnings)


# ---------------------------------------------------------------------------
# Per-row scoring.
# ---------------------------------------------------------------------------


def _tier_of(sample_id: str) -> str:
    return sample_id.split(":", 1)[0]


@dataclass(frozen=True)
class RowScore:
    row: OutputRow
    tier: str
    item: ItemScore
    parsed: bool
    empty_tool_call: bool
    induced_substitutions: int


def score_row(
    row: OutputRow,
    *,
    expected_by_id: Mapping[str, tuple[ToolCall, ...]],
    supplied_values: Mapping[str, set],
) -> RowScore:
    predicted, parsed = parse_tool_calls_text(row.response)
    expected = expected_by_id[row.sample_id]
    item = score_item(expected, predicted)
    induced = count_induced_substitutions(predicted, expected, supplied_values)
    return RowScore(
        row=row,
        tier=_tier_of(row.sample_id),
        item=item,
        parsed=parsed,
        empty_tool_call=is_empty_tool_call(row.response),
        induced_substitutions=induced,
    )


# ---------------------------------------------------------------------------
# Harness-defect checks (note 1: fail-closed refusal, never a soft flag).
# ---------------------------------------------------------------------------


def _harness_defect_reasons(
    *,
    malformed_row_reasons: Sequence[str],
    flight_receipt: Mapping[str, object] | None,
    rows_by_arm: Mapping[str, Sequence[OutputRow]],
    unknown_arm_rows: Sequence[OutputRow],
    duplicate_pairs: Sequence[tuple[str, str]],
    split_identity_hash: str,
    expected_by_id: Mapping[str, tuple[ToolCall, ...]],
    expected_n: int,
) -> tuple[str, ...]:
    reasons: list[str] = list(malformed_row_reasons)

    if flight_receipt is None:
        reasons.append("flight-receipt.json missing")
    else:
        status = flight_receipt.get("status")
        if status != "COMPLETED":
            reasons.append(
                f"flight-receipt status={status!r} (expected 'COMPLETED'); error={flight_receipt.get('error')!r}"
            )
        failures = flight_receipt.get("request_failures")
        if failures:
            reasons.append(f"flight-receipt request_failures non-empty: {len(failures)} failure(s)")
        arms = flight_receipt.get("arms")
        if arms != list(A2T_POP_ARMS):
            reasons.append(f"flight-receipt arms={arms!r}, expected {list(A2T_POP_ARMS)!r}")
        receipt_hash = flight_receipt.get("split_identity_hash")
        if receipt_hash != split_identity_hash:
            reasons.append(
                f"split_identity_hash mismatch: flight-receipt={receipt_hash!r} "
                f"vs. frozen probe receipt={split_identity_hash!r}"
            )

    for row in unknown_arm_rows:
        reasons.append(f"row on unknown arm {row.arm!r} (sample {row.sample_id!r})")
    for pair in duplicate_pairs:
        reasons.append(f"duplicate row for (arm, sample_id)={pair!r}")

    for arm in A2T_POP_ARMS:
        rows = rows_by_arm.get(arm, ())
        got_ids = [row.sample_id for row in rows]
        if len(got_ids) != len(set(got_ids)):
            dupes = sorted({sid for sid in got_ids if got_ids.count(sid) > 1})
            reasons.append(f"arm {arm}: duplicate sample_id row(s) within the arm: {dupes[:5]}")
        if len(rows) != expected_n:
            reasons.append(
                f"arm {arm}: row count {len(rows)} != expected {expected_n} (97/97 fail-closed check)"
            )

    r0_ids = {row.sample_id for row in rows_by_arm.get(R0_ARM, ())}
    r1_ids = {row.sample_id for row in rows_by_arm.get(R1_ARM, ())}
    if r0_ids != r1_ids:
        missing_from_r1 = sorted(r0_ids - r1_ids)
        missing_from_r0 = sorted(r1_ids - r0_ids)
        reasons.append(
            "R0/R1 sample id sets differ (a PAIRED population is required for Δreg/the bootstrap): "
            f"missing_from_r1={missing_from_r1[:5]}, missing_from_r0={missing_from_r0[:5]}"
        )

    missing_gold = sorted(sid for sid in (r0_ids | r1_ids) if sid not in expected_by_id)
    if missing_gold:
        reasons.append(
            f"{len(missing_gold)} sample id(s) have no resolvable gold via load_expected_calls: "
            f"{missing_gold[:5]}"
        )

    return tuple(reasons)


# ---------------------------------------------------------------------------
# Per-arm / per-tier aggregation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArmAggregate:
    arm: str
    n_samples: int
    tool_accuracy: float  # tool-selection retention
    regression_count: int  # EM 1 -> 0 count (note: baseline fixed at EM=1)
    regression_rate: float
    slot_f1: float
    empty_call_rate: float
    parse_failure_rate: float
    induced_substitution_count: int


def build_arm_aggregate(arm: str, scores: Sequence[RowScore]) -> ArmAggregate:
    n = len(scores)
    agg = aggregate([s.item for s in scores])
    empty_count = sum(1 for s in scores if s.empty_tool_call)
    parse_failures = sum(1 for s in scores if not s.parsed)
    regression_count = sum(1 for s in scores if s.item.exact_match == 0.0)
    induced_total = sum(s.induced_substitutions for s in scores)
    return ArmAggregate(
        arm=arm,
        n_samples=n,
        tool_accuracy=agg.tool_accuracy,
        regression_count=regression_count,
        regression_rate=(regression_count / n) if n else 0.0,
        slot_f1=agg.slot_f1,
        empty_call_rate=(empty_count / n) if n else 0.0,
        parse_failure_rate=(parse_failures / n) if n else 0.0,
        induced_substitution_count=induced_total,
    )


@dataclass(frozen=True)
class PerArmReport:
    overall: ArmAggregate
    by_tier: Mapping[str, ArmAggregate]


def build_per_arm_report(arm: str, scores: Sequence[RowScore]) -> PerArmReport:
    by_tier: dict[str, list[RowScore]] = {}
    for score in scores:
        by_tier.setdefault(score.tier, []).append(score)
    return PerArmReport(
        overall=build_arm_aggregate(arm, scores),
        by_tier={tier: build_arm_aggregate(arm, tier_scores) for tier, tier_scores in sorted(by_tier.items())},
    )


# ---------------------------------------------------------------------------
# Δreg + the mandatory paired per-sample bootstrap (note 2).
# ---------------------------------------------------------------------------


def compute_delta_reg_bootstrap(
    r0_scores: Sequence[RowScore],
    r1_scores: Sequence[RowScore],
    *,
    n_replicates: int = DEFAULT_N_REPLICATES,
    seed: int = DEFAULT_SEED,
    ci_level: float = DEFAULT_CI_LEVEL,
) -> BootstrapResult:
    """``statistic(ids)`` = ``reg(R1) - reg(R0)`` over the (possibly
    resampled-with-repeats) id multiset -- PAIRED (module docstring: the
    SAME resampled multiset is applied to both arms' own per-sample
    regression indicator for every replicate, delegated entirely to the
    shared ``analysis.bootstrap.paired_cluster_bootstrap`` primitive, never
    re-implemented here)."""

    r0_em = {s.row.sample_id: s.item.exact_match for s in r0_scores}
    r1_em = {s.row.sample_id: s.item.exact_match for s in r1_scores}
    common_ids = sorted(set(r0_em) & set(r1_em))
    if not common_ids:
        raise A2tPopReadError(
            "compute_delta_reg_bootstrap: no sample id is present in both R0 and R1 -- cannot "
            "compute a paired bootstrap over zero paired samples"
        )

    def statistic(ids: Sequence[str]) -> float:
        reg_r0 = sum(1 for i in ids if r0_em[i] == 0.0)
        reg_r1 = sum(1 for i in ids if r1_em[i] == 0.0)
        return float(reg_r1 - reg_r0)

    return paired_cluster_bootstrap(
        sample_ids=common_ids, statistic=statistic, n_replicates=n_replicates, seed=seed, ci_level=ci_level
    )


# ---------------------------------------------------------------------------
# Verdict (prereg section 3, mechanically evaluated in the registered order).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PopVerdict:
    delta_reg: int
    bootstrap: BootstrapResult
    safe_clause: ClauseResult
    costly_clause: ClauseResult
    overall: str


def evaluate_pop_verdict(reg_r0: int, reg_r1: int, bootstrap: BootstrapResult) -> PopVerdict:
    delta_reg = reg_r1 - reg_r0
    safe_clause = ClauseResult(
        f"Δreg <= {REGRESSION_SAFE_DELTA_MAX} AND CI upper bound <= {REGRESSION_SAFE_CI_UPPER_MAX:.1f}",
        "met"
        if (delta_reg <= REGRESSION_SAFE_DELTA_MAX and bootstrap.ci_high <= REGRESSION_SAFE_CI_UPPER_MAX)
        else "not_met",
        f"Δreg={delta_reg} (reg(R1)={reg_r1}, reg(R0)={reg_r0}), "
        f"CI=[{bootstrap.ci_low:+.4f}, {bootstrap.ci_high:+.4f}], sigma_hat={bootstrap.sigma_hat:.4f}",
    )
    costly_clause = ClauseResult(
        f"Δreg >= {REGRESSION_COSTLY_DELTA_MIN}",
        "met" if delta_reg >= REGRESSION_COSTLY_DELTA_MIN else "not_met",
        f"Δreg={delta_reg}, floor={REGRESSION_COSTLY_DELTA_MIN}",
    )
    if safe_clause.verdict == "met":
        overall = "REGRESSION-SAFE"
    elif costly_clause.verdict == "met":
        overall = "REGRESSION-COSTLY"
    else:
        overall = "INCONCLUSIVE-POP"
    return PopVerdict(delta_reg=delta_reg, bootstrap=bootstrap, safe_clause=safe_clause, costly_clause=costly_clause, overall=overall)


# ---------------------------------------------------------------------------
# Mandatory reachability/stability statement (note 3).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReachabilityStatement:
    r0_regression_count: int
    n_samples: int
    r0_regression_rate: float
    detail: str


def compute_reachability_statement(r0_aggregate: ArmAggregate) -> ReachabilityStatement:
    detail = (
        "Pre-read reachability statement (mandatory): the branch space is trivially reachable -- EM "
        f"can regress on any/all of the {r0_aggregate.n_samples} EM-correct ids under either arm. R0 "
        "(zero-supply re-fly, byte-identical to A0's own request) shows "
        f"{r0_aggregate.regression_count}/{r0_aggregate.n_samples} EM regressions "
        f"(rate={r0_aggregate.regression_rate:.4f}) under a bare re-fly with no prompt change "
        "whatsoever -- this population's own FIRST empirical measurement of A0's zero-supply decode "
        "stability (no prior re-fly of this specific 97-id EM-correct population exists)."
    )
    return ReachabilityStatement(
        r0_regression_count=r0_aggregate.regression_count,
        n_samples=r0_aggregate.n_samples,
        r0_regression_rate=r0_aggregate.regression_rate,
        detail=detail,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tPopReadReport:
    attempt_dir: Path
    flight_status: str | None
    split_identity_hash: str
    per_arm: Mapping[str, PerArmReport]
    verdict: PopVerdict
    reachability: ReachabilityStatement
    registry_warnings: tuple[str, ...]


def build_a2t_pop_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    split_role: str = DEFAULT_SPLIT_ROLE,
    expected_n: int = EM_CORRECT_N,
) -> A2tPopReadReport:
    attempt_dir = Path(attempt_dir)
    repo_root = Path(repo_root)

    from ..data.audio2tool import load_expected_calls, load_tool_registry
    from .a2t_read import _load_split_receipt

    rows, malformed_row_reasons = load_attempt_rows(attempt_dir)
    flight_receipt = load_flight_receipt(attempt_dir)

    split_receipt = _load_split_receipt(repo_root, split_role)
    split_identity_hash = str(split_receipt["split_identity_hash"])

    expected_by_id = load_expected_calls(lock, root, repo_root=repo_root)
    registry_rows = load_tool_registry(lock, root)
    supplied_values, registry_warnings = full_registry_supplied_values(registry_rows)

    rows_by_arm: dict[str, list[OutputRow]] = {arm: [] for arm in A2T_POP_ARMS}
    unknown_arm_rows: list[OutputRow] = []
    duplicate_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        pair = (row.arm, row.sample_id)
        if pair in seen:
            duplicate_pairs.append(pair)
            continue
        seen.add(pair)
        if row.arm not in A2T_POP_ARMS:
            unknown_arm_rows.append(row)
            continue
        rows_by_arm[row.arm].append(row)

    defect_reasons = _harness_defect_reasons(
        malformed_row_reasons=malformed_row_reasons,
        flight_receipt=flight_receipt,
        rows_by_arm=rows_by_arm,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_pairs=duplicate_pairs,
        split_identity_hash=split_identity_hash,
        expected_by_id=expected_by_id,
        expected_n=expected_n,
    )
    if defect_reasons:
        raise A2tPopReadError(
            "harness defect(s) detected; refusing to score:\n  " + "\n  ".join(defect_reasons)
        )

    per_arm: dict[str, PerArmReport] = {}
    scores_by_arm: dict[str, list[RowScore]] = {}
    for arm in A2T_POP_ARMS:
        scores = [
            score_row(row, expected_by_id=expected_by_id, supplied_values=supplied_values)
            for row in sorted(rows_by_arm[arm], key=lambda r: r.sample_id)
        ]
        scores_by_arm[arm] = scores
        per_arm[arm] = build_per_arm_report(arm, scores)

    bootstrap = compute_delta_reg_bootstrap(scores_by_arm[R0_ARM], scores_by_arm[R1_ARM])
    verdict = evaluate_pop_verdict(
        per_arm[R0_ARM].overall.regression_count, per_arm[R1_ARM].overall.regression_count, bootstrap
    )
    reachability = compute_reachability_statement(per_arm[R0_ARM].overall)

    return A2tPopReadReport(
        attempt_dir=attempt_dir,
        flight_status=None if flight_receipt is None else flight_receipt.get("status"),
        split_identity_hash=split_identity_hash,
        per_arm=per_arm,
        verdict=verdict,
        reachability=reachability,
        registry_warnings=tuple(sorted(set(registry_warnings))),
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _arm_aggregate_json(agg: ArmAggregate) -> dict[str, object]:
    return {
        "arm": agg.arm,
        "n_samples": agg.n_samples,
        "tool_selection_retention": agg.tool_accuracy,
        "regression_count": agg.regression_count,
        "regression_rate": agg.regression_rate,
        "slot_f1": agg.slot_f1,
        "empty_call_rate": agg.empty_call_rate,
        "parse_failure_rate": agg.parse_failure_rate,
        "induced_substitution_count": agg.induced_substitution_count,
    }


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def report_to_json(report: A2tPopReadReport) -> dict[str, object]:
    verdict = report.verdict
    return {
        "schema": REPORT_SCHEMA,
        "run_id": RUN_ID,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "split_identity_hash": report.split_identity_hash,
        "registry_defaults_parse_warnings": list(report.registry_warnings),
        "per_arm": {
            arm: {
                "overall": _arm_aggregate_json(per_arm_report.overall),
                "by_tier": {tier: _arm_aggregate_json(agg) for tier, agg in per_arm_report.by_tier.items()},
            }
            for arm, per_arm_report in report.per_arm.items()
        },
        "verdict": {
            "delta_reg": verdict.delta_reg,
            "bootstrap": verdict.bootstrap.as_json(),
            "safe_clause": _clause_json(verdict.safe_clause),
            "costly_clause": _clause_json(verdict.costly_clause),
            "overall": verdict.overall,
        },
        "reachability": {
            "r0_regression_count": report.reachability.r0_regression_count,
            "n_samples": report.reachability.n_samples,
            "r0_regression_rate": report.reachability.r0_regression_rate,
            "detail": report.reachability.detail,
        },
    }


def render_report(report: A2tPopReadReport) -> str:
    verdict = report.verdict
    lines = [
        "P-A2T whole-population regression-arm pinned offline read "
        "(docs/readiness/2026-08-19-a2t-pop-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r}",
        f"split identity hash: {report.split_identity_hash}",
        "",
        report.reachability.detail,
        "",
        "Per-arm aggregates (pooled)",
    ]
    header = (
        f"  {'arm':<6}{'n':>4}{'retention':>11}{'reg_count':>11}{'reg_rate':>10}"
        f"{'slot_f1':>9}{'empty':>7}{'parse_fail':>11}{'induced':>9}"
    )
    lines.append(header)
    for arm in A2T_POP_ARMS:
        agg = report.per_arm[arm].overall
        lines.append(
            f"  {arm:<6}{agg.n_samples:>4}{agg.tool_accuracy:>11.4f}{agg.regression_count:>11}"
            f"{agg.regression_rate:>10.4f}{agg.slot_f1:>9.4f}{agg.empty_call_rate:>7.4f}"
            f"{agg.parse_failure_rate:>11.4f}{agg.induced_substitution_count:>9}"
        )
    lines.append("")

    lines.append("Per-tier breakdown")
    for arm in A2T_POP_ARMS:
        lines.append(f"  arm {arm}:")
        for tier in sorted(report.per_arm[arm].by_tier):
            agg = report.per_arm[arm].by_tier[tier]
            lines.append(
                f"    {tier:<22}{agg.n_samples:>4} reg_count={agg.regression_count} "
                f"reg_rate={agg.regression_rate:.4f} retention={agg.tool_accuracy:.4f} "
                f"slot_f1={agg.slot_f1:.4f} induced={agg.induced_substitution_count}"
            )
    lines.append("")

    if report.registry_warnings:
        lines.append(f"registry_defaults parse warnings (informational, non-fatal): {len(report.registry_warnings)}")
        for warning in report.registry_warnings[:10]:
            lines.append(f"  {warning}")
        if len(report.registry_warnings) > 10:
            lines.append(f"  ... (+{len(report.registry_warnings) - 10} more)")
        lines.append("")

    lines.append(
        f"Δreg = reg(R1) - reg(R0) = {verdict.delta_reg} "
        f"(reg(R0)={report.per_arm[R0_ARM].overall.regression_count}, "
        f"reg(R1)={report.per_arm[R1_ARM].overall.regression_count})"
    )
    lines.append(
        f"paired bootstrap: CI=[{verdict.bootstrap.ci_low:+.4f}, {verdict.bootstrap.ci_high:+.4f}] "
        f"sigma_hat={verdict.bootstrap.sigma_hat:.4f} n_replicates={verdict.bootstrap.n_replicates} "
        f"seed={verdict.bootstrap.seed}"
    )
    lines.append("")

    lines.append(f"REGRESSION-SAFE: {'MET' if verdict.safe_clause.verdict == 'met' else 'not met'}")
    lines.append(f"  [{verdict.safe_clause.verdict.upper():>8}] {verdict.safe_clause.clause_text}")
    lines.append(f"           {verdict.safe_clause.detail}")
    lines.append("")

    lines.append(f"REGRESSION-COSTLY: {'MET' if verdict.costly_clause.verdict == 'met' else 'not met'}")
    lines.append(f"  [{verdict.costly_clause.verdict.upper():>8}] {verdict.costly_clause.clause_text}")
    lines.append(f"           {verdict.costly_clause.detail}")
    lines.append("")

    lines.append(f"OVERALL: {verdict.overall}")
    return "\n".join(lines)


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="a2t-pop-read",
        description=(
            "P-A2T whole-population regression-arm pinned offline read suite: per-arm and per-tier "
            "EM-regression/tool-selection-retention/slot-F1/empty-call/induced-substitution/"
            "parse-failure metrics, the paired per-sample bootstrap over Δreg, the mandatory "
            "reachability/stability statement, and the mechanical REGRESSION-SAFE/REGRESSION-COSTLY/"
            "INCONCLUSIVE-POP verdict. Model-free, read-only; never opens a model session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the flight's own attempt directory (carries outputs.jsonl)")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write verdict.json / report.txt")
    parser.add_argument(
        "--split-role", default=DEFAULT_SPLIT_ROLE,
        help=f"the frozen probe receipt's split_role to read against (default: {DEFAULT_SPLIT_ROLE!r})",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock and the frozen receipts",
    )
    parser.add_argument(
        "--expected-n", type=int, default=EM_CORRECT_N,
        help=f"TEST-ONLY override of the registered EM-correct roster size (default: {EM_CORRECT_N}, the "
        "real registered population; a real read must never override this)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT

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
        report = build_a2t_pop_report(
            args.attempt_dir, lock, root, repo_root=repo_root, split_role=args.split_role,
            expected_n=args.expected_n,
        )
    except A2tPopReadError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, report_to_json(report))
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
