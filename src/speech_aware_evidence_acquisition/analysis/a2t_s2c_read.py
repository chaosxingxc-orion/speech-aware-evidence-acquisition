"""P-A2T Stage-2c form-robustness probe offline read suite (pinned,
pre-registered).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written C1/C2/C3
attempt's ``outputs.jsonl`` / ``flight-receipt.json`` (``rails.probes.
a2t_s2c_flight.run_a2t_s2c_flight``'s own row shape -- IDENTICAL to
Stage-2/2b's own ``{arm, sample_id, supplied_tool, response, timing}``,
since ``rails.probes.a2t_s2c_flight`` reuses ``rails.probes.a2t_s2_flight``'s
own ``A2tS2ArmResult``/``result_to_json``/``write_outputs_jsonl`` directly)
PLUS Stage-2's OWN already-flown ``{RUN_ID}.arm-plan.json`` (reused
verbatim, never re-derived -- the SAME file Stage-2b's own read suite
already reuses: every C-arm's content is Stage-2's ``s1p_tool_names``,
Stage-2b's own B1 mapping).

Purpose (``docs/readiness/2026-08-18-pa2t-stage2c-preregistration-
REGISTERED.md`` section 3): is Stage-2b's B1 result (8/120 conversion at
zero margin, 2 induced substitutions) robust to the SURFACE FORM of the
stripped row, or a knife-edge artifact of B1's exact rendering? This suite
computes every ingredient metric section 4 names (per arm AND per tier --
pooled is never the headline) and mechanically evaluates section 3's
verdict rules: the primary ROBUST / FORM-FRAGILE / INCONCLUSIVE-C
evaluator over C1+C2 jointly, plus the INDEPENDENT DEPLOY-AUGMENT overlay
over C3 alone.

REUSE, NOT RE-DERIVATION. Every scoring primitive below is imported
directly from ``analysis.a2t_s2_read``, never reimplemented a second way:

- ``OutputRow``/``load_attempt_rows``/``load_flight_receipt`` for the
  attempt's own IDENTICALLY-SHAPED rows.
- ``load_headroom_identity`` for the frozen 120-id headroom set (the SAME
  set Stage-2/2b/2c all fly over -- prereg intro: "the SAME 120 headroom
  ids").
- ``ArmPlan``/``load_arm_plan`` for Stage-2's OWN reused mapping.
- ``score_row``/``build_arm_aggregate`` for per-row scoring and the
  micro-aggregated (raw-count-summed, never per-row-averaged) per-arm and
  per-tier ingredient numbers -- ``ArmAggregate``/``PerArmReport`` carried
  unchanged.
- ``ClauseResult`` for this module's own mechanical clause records (the
  SAME record shape Stage-2/2b's evaluators use).

ENGINEERING-INTERPRETATION NOTES (flagged here, mirroring
``analysis.a2t_s2_read``/``analysis.a2t_s2b_read``'s own discipline -- each
is a documented, reviewable choice, not a silent guess):

1. Every C-arm supplies EXACTLY the same content as Stage-2b's B1 (only
   its PRESENTATION differs), so the induced-substitution yardstick is the
   UNCHANGED one Stage-2/2b already use: ``score_row``'s own
   ``supplied_tool_names`` parameter is Stage-2's ``s1p_tool_names`` for
   THIS sample, looked up against the FULL registry's own
   ``argument_defaults`` column via ``supplied_argument_values`` --
   apples-to-apples with S1p's 34 and B1's 2 (prereg section 4: "the
   unchanged yardstick -- apples-to-apples with 34/2"; confirmed verbatim
   by the consumed Stage-2b verdict's own §3: "B1's count is still
   computed against the full registry's default-value set for the
   supplied tool via ``score_row``'s own ``registry_index`` lookup, not
   against the stripped prompt text"). This is IDENTICAL for C1 (whose
   prompt never shows the literal default value either, just like B1) and
   for C2 (same). For C3, the prompt ALSO contains the full registry's own
   defaults for the OTHER 151 tools (byte-identical to A0's own prompt),
   but the yardstick stays the arm's own supplied roster (the appended
   correct-tool row(s), i.e. the SAME ``s1p_tool_names`` set) -- mirrors
   Stage-2b's own B2 convention exactly (B2's prompt also contains the
   full registry's defaults, and its own induced-substitution yardstick is
   likewise scoped to its own single named roster, never the full
   registry's every tool).
2. "C1/C2 conversion >= 6/120" and "<= 3/120" are RATIOS
   (:data:`ROBUST_CONVERSION_MIN` = ``6/120``, :data:`FRAGILE_CONVERSION_MAX`
   = ``3/120``), compared against ``ArmAggregate.em_conversion_rate`` (a
   RATE) -- numerically identical to the mission's literal fractions at
   n=120 while staying well-defined for a small synthetic fixture arm in
   this module's own tests. Induced-substitution thresholds ("<=5"/">=20")
   stay RAW COUNTS (``ArmAggregate.induced_substitution_count``), exactly
   as literally stated -- the prereg names no denominator for them
   (mirrors ``analysis.a2t_s2b_read``'s own note 1).
3. ROBUST and FORM-FRAGILE are evaluated as INDEPENDENT boolean
   computations, then combined with FORM-FRAGILE gated behind "not ROBUST"
   (mirrors ``analysis.a2t_s2b_read.evaluate_qa``'s own
   ``confirmed_cut``/``not_defaults`` pattern) -- defense-in-depth even
   though the two threshold sets are numerically disjoint (6/120 > 3/120;
   5 < 20) and cannot both fire on the same aggregate. Likewise
   DEPLOY-AUGMENT's DEPLOYABLE/CHANNEL-REOPENED.
4. Tool-selection retention is COMPUTED and REPORTED per arm and per tier
   (``ArmAggregate.tool_accuracy``, part of every rendered/JSON table) but
   carries NO verdict clause in this probe -- the prereg's own §4 wording,
   quoted verbatim: "Retention carries NO verdict clause in this probe
   (the 12.5% selection-noise band cannot bear one at this n; lesson of
   Stage-2/2b)". Neither :func:`evaluate_form_robustness` nor
   :func:`evaluate_deploy_augment` reads ``tool_accuracy`` at all.
5. DEPLOY-AUGMENT is evaluated and reported INDEPENDENTLY of the primary
   ROBUST/FORM-FRAGILE verdict (prereg section 3: "C3 fires no primary
   branch") -- :func:`evaluate_deploy_augment` takes only C3's own
   aggregate and never consults C1/C2's verdict, and the rendered/JSON
   report always surfaces it as its own field rather than folding it into
   ``overall`` as a mutually-exclusive branch (mirrors
   ``analysis.a2t_s2b_read``'s own MISLEAD-overlay discipline, note 4
   there).
6. Harness-defect checks mirror ``analysis.a2t_s2b_read``'s own template,
   generalized to three arms: every row's own ``supplied_tool`` label
   (Stage-2's ``s1p_tool_names``, sorted/comma-joined) must match what the
   reused Stage-2 arm-plan implies for that ``(arm, sample_id)`` -- the
   SAME label for ALL THREE arms (unlike Stage-2b's B1/B2, which carry
   different labels), since every C-arm supplies the identical correct-tool
   set. This module never checks ``s4_derangement``/``s4_tool_name`` at
   all -- out of scope, no C-arm touches them (mirrors ``rails.probes.
   a2t_s2c_flight``'s own "never touches S4" design).
7. Per note 10 of ``analysis.a2t_s2_read`` (reused verbatim here): the
   verdict rules are evaluated on POOLED (whole-arm) aggregates only;
   per-tier reporting accompanies every verdict but never substitutes a
   second, tier-scoped evaluation the preregistration never defines.
8. TWO exception classes, deliberately, mirroring ``analysis.a2t_s2b_read``'s
   own note 7: this module's OWN harness-defect aggregation raises
   :class:`A2tS2cReadError`; a RAW failure inside a directly reused Stage-2
   loader (``load_arm_plan``, ``load_headroom_identity``, ``load_attempt_rows``)
   surfaces as that loader's OWN :class:`~analysis.a2t_s2_read.A2tS2ReadError`
   unchanged -- never re-wrapped. :func:`main` catches BOTH.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_a2t_s2c_read.py``, itself reusing ``tests/unit/
test_a2t_s2_read.py``'s own ``A2tS2World`` fixture directly, mirroring
``tests/unit/test_a2t_s2b_read.py``'s own precedent). This module is never
run against a real flight attempt directory by the task that wrote it; a
later, separately-registered one-shot read session points
``build_a2t_s2c_report``/the CLI at the real COMPLETED attempt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..rails.probes.a2t_s2c_flight import A2T_S2C_ARMS, C1_ARM, C2_ARM, C3_ARM
from .a2t_s2_read import (
    ArmAggregate,
    ArmPlan,
    A2tS2ReadError,
    ClauseResult,
    OutputRow,
    PerArmReport,
    build_arm_aggregate,
    load_arm_plan,
    load_attempt_rows,
    load_flight_receipt,
    load_headroom_identity,
    score_row,
)

REPORT_SCHEMA = "saea-a2t-s2c-read-v1"
# Names the exposure-ledger row / the Stage-2c preregistration's own run id
# (configs/probes/g0-binding/a2t-s2c-flight.json's own exposure_ledger_row).
RUN_ID = "SAEA-PROBE-a2t-s2c-120"
DEFAULT_SPLIT_ROLE = "discovery"

INTERPRETIVE_WEIGHT_MIN_N = 16  # preregistration section 4, unchanged from Stage-2/2b

# Preregistration section 3 thresholds, quoted verbatim in each clause's own
# detail text below (module docstring note 2 explains the ratio/raw-count
# choice).
ROBUST_CONVERSION_MIN = 6 / 120
ROBUST_INDUCED_MAX = 5
FRAGILE_CONVERSION_MAX = 3 / 120
FRAGILE_INDUCED_MIN = 20

DEPLOY_CONVERSION_MIN = 6 / 120
DEPLOY_INDUCED_MAX = 5
DEPLOY_INDUCED_REOPENED_MIN = 20


class A2tS2cReadError(RuntimeError):
    """Malformed attempt-dir/Stage-2-arm-plan/headroom input, or a harness
    defect this module's own "machine harness checks, fail-closed"
    discipline requires refusing on -- never raised for an ordinary,
    structurally clean read."""


# ---------------------------------------------------------------------------
# Harness-defect checks (module docstring note 6: the SAME expected label
# for all three arms).
# ---------------------------------------------------------------------------


def _expected_label(arm_plan: ArmPlan, sample_id: str) -> str:
    names = arm_plan.s1p_tool_names.get(sample_id, ())
    return ",".join(sorted(set(names)))


def _harness_defect_reasons(
    *,
    malformed_row_reasons: Sequence[str],
    flight_receipt: Mapping[str, object] | None,
    rows_by_arm: Mapping[str, Sequence[OutputRow]],
    unknown_arm_rows: Sequence[OutputRow],
    duplicate_pairs: Sequence[tuple[str, str]],
    arm_plan: ArmPlan,
    headroom_ids: Sequence[str],
    split_identity_hash: str,
    expected_by_id: Mapping[str, tuple],
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
        if arms != list(A2T_S2C_ARMS):
            reasons.append(f"flight-receipt arms={arms!r}, expected {list(A2T_S2C_ARMS)!r}")
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

    headroom_set = set(headroom_ids)
    arm_plan_headroom_set = set(arm_plan.headroom_ids)
    if not headroom_set <= arm_plan_headroom_set:
        missing = headroom_set - arm_plan_headroom_set
        reasons.append(
            f"this flight's own headroom ids are not covered by the reused Stage-2 arm-plan's "
            f"headroom_ids: missing={sorted(missing)[:5]}"
        )

    s1p_keys = set(arm_plan.s1p_tool_names)
    if not headroom_set <= s1p_keys:
        reasons.append(
            "Stage-2 arm-plan 's1p_tool_names' does not cover this flight's own headroom ids "
            f"(missing={sorted(headroom_set - s1p_keys)[:5]})"
        )

    expected_counts = {arm: len(headroom_ids) for arm in A2T_S2C_ARMS}
    total_rows = sum(len(rows) for rows in rows_by_arm.values()) + len(unknown_arm_rows)
    expected_total = sum(expected_counts.values())
    if total_rows != expected_total:
        reasons.append(
            f"total row count {total_rows} != expected {expected_total} (3 x len(headroom_ids))"
        )

    for arm in A2T_S2C_ARMS:
        rows = rows_by_arm.get(arm, ())
        got_ids = [row.sample_id for row in rows]
        if len(got_ids) != len(set(got_ids)):
            dupes = sorted({sid for sid in got_ids if got_ids.count(sid) > 1})
            reasons.append(f"arm {arm}: duplicate sample_id row(s) within the arm: {dupes[:5]}")
        if len(rows) != expected_counts[arm]:
            reasons.append(f"arm {arm}: row count {len(rows)} != expected {expected_counts[arm]}")
        got_set = set(got_ids)
        missing = headroom_set - got_set
        extra = got_set - headroom_set
        if missing:
            reasons.append(f"arm {arm}: missing {len(missing)} sample id(s): {sorted(missing)[:5]}")
        if extra:
            reasons.append(f"arm {arm}: {len(extra)} sample id(s) not in the headroom set: {sorted(extra)[:5]}")

        # Module docstring note 6: the written supplied_tool label must
        # match Stage-2's own s1p_tool_names mapping for EVERY C-arm.
        for row in rows:
            expected_label = _expected_label(arm_plan, row.sample_id)
            if row.supplied_tool != expected_label:
                reasons.append(
                    f"arm {arm} sample {row.sample_id!r}: supplied_tool={row.supplied_tool!r} does "
                    f"not match the reused Stage-2 mapping's own expectation {expected_label!r}"
                )

    missing_gold = sorted(sid for sid in headroom_ids if sid not in expected_by_id)
    if missing_gold:
        reasons.append(
            f"{len(missing_gold)} headroom sample id(s) have no resolvable gold via load_expected_calls: "
            f"{missing_gold[:5]}"
        )

    return tuple(reasons)


def _supplied_tool_names_for_row(row: OutputRow, arm_plan: ArmPlan) -> tuple[str, ...]:
    return arm_plan.s1p_tool_names.get(row.sample_id, ())


# ---------------------------------------------------------------------------
# Mechanical evaluators (prereg section 3, quoted verbatim below).
# ---------------------------------------------------------------------------

FormRobustnessOverall = Literal["ROBUST", "FORM-FRAGILE", "INCONCLUSIVE-C"]
DeployAugmentOverall = Literal["DEPLOYABLE", "CHANNEL-REOPENED", "no flag"]


@dataclass(frozen=True)
class FormRobustnessVerdict:
    robust_clauses: tuple[ClauseResult, ...]
    robust: bool
    fragile_clauses: tuple[ClauseResult, ...]
    fragile: bool
    overall: FormRobustnessOverall


@dataclass(frozen=True)
class DeployAugmentVerdict:
    deployable_clauses: tuple[ClauseResult, ...]
    deployable: bool
    channel_reopened_clause: ClauseResult
    channel_reopened: bool
    overall: DeployAugmentOverall


def evaluate_form_robustness(c1: ArmAggregate, c2: ArmAggregate) -> FormRobustnessVerdict:
    """The primary verdict (prereg section 3, quoted verbatim): "ROBUST:
    C1 AND C2 each have conversion >= 6/120 ... AND induced-substitutions
    <= 5 ... FORM-FRAGILE: C1 or C2 has conversion <= 3/120 ... OR induced
    >= 20 ... Otherwise INCONCLUSIVE-C"."""

    robust_clauses = (
        ClauseResult(
            "C1 conversion >= 6/120",
            "met" if c1.em_conversion_rate >= ROBUST_CONVERSION_MIN else "not_met",
            f"C1 conversion={c1.em_conversion_rate:.4f} ({c1.em_flip_count}/{c1.n_samples}), "
            f"floor={ROBUST_CONVERSION_MIN:.4f}",
        ),
        ClauseResult(
            "C2 conversion >= 6/120",
            "met" if c2.em_conversion_rate >= ROBUST_CONVERSION_MIN else "not_met",
            f"C2 conversion={c2.em_conversion_rate:.4f} ({c2.em_flip_count}/{c2.n_samples}), "
            f"floor={ROBUST_CONVERSION_MIN:.4f}",
        ),
        ClauseResult(
            "C1 induced-substitutions <= 5",
            "met" if c1.induced_substitution_count <= ROBUST_INDUCED_MAX else "not_met",
            f"C1 induced={c1.induced_substitution_count}, ceiling={ROBUST_INDUCED_MAX}",
        ),
        ClauseResult(
            "C2 induced-substitutions <= 5",
            "met" if c2.induced_substitution_count <= ROBUST_INDUCED_MAX else "not_met",
            f"C2 induced={c2.induced_substitution_count}, ceiling={ROBUST_INDUCED_MAX}",
        ),
    )
    robust = all(clause.verdict == "met" for clause in robust_clauses)

    fragile_clauses = (
        ClauseResult(
            "C1 conversion <= 3/120 (<= noise)",
            "met" if c1.em_conversion_rate <= FRAGILE_CONVERSION_MAX else "not_met",
            f"C1 conversion={c1.em_conversion_rate:.4f}, ceiling={FRAGILE_CONVERSION_MAX:.4f}",
        ),
        ClauseResult(
            "C2 conversion <= 3/120 (<= noise)",
            "met" if c2.em_conversion_rate <= FRAGILE_CONVERSION_MAX else "not_met",
            f"C2 conversion={c2.em_conversion_rate:.4f}, ceiling={FRAGILE_CONVERSION_MAX:.4f}",
        ),
        ClauseResult(
            "C1 induced-substitutions >= 20",
            "met" if c1.induced_substitution_count >= FRAGILE_INDUCED_MIN else "not_met",
            f"C1 induced={c1.induced_substitution_count}, floor={FRAGILE_INDUCED_MIN}",
        ),
        ClauseResult(
            "C2 induced-substitutions >= 20",
            "met" if c2.induced_substitution_count >= FRAGILE_INDUCED_MIN else "not_met",
            f"C2 induced={c2.induced_substitution_count}, floor={FRAGILE_INDUCED_MIN}",
        ),
    )
    fragile = (not robust) and any(clause.verdict == "met" for clause in fragile_clauses)

    if robust:
        overall: FormRobustnessOverall = "ROBUST"
    elif fragile:
        overall = "FORM-FRAGILE"
    else:
        overall = "INCONCLUSIVE-C"

    return FormRobustnessVerdict(
        robust_clauses=robust_clauses,
        robust=robust,
        fragile_clauses=fragile_clauses,
        fragile=fragile,
        overall=overall,
    )


def evaluate_deploy_augment(c3: ArmAggregate) -> DeployAugmentVerdict:
    """The independent DEPLOY-AUGMENT overlay (prereg section 3, quoted
    verbatim): "C3 conversion >= 6/120 AND C3 induced <= 5 => flag
    DEPLOYABLE ... C3 induced >= 20 => flag CHANNEL-REOPENED ... C3 fires
    no primary branch". Never consults C1/C2 (module docstring note 5)."""

    deployable_clauses = (
        ClauseResult(
            "C3 conversion >= 6/120",
            "met" if c3.em_conversion_rate >= DEPLOY_CONVERSION_MIN else "not_met",
            f"C3 conversion={c3.em_conversion_rate:.4f} ({c3.em_flip_count}/{c3.n_samples}), "
            f"floor={DEPLOY_CONVERSION_MIN:.4f}",
        ),
        ClauseResult(
            "C3 induced-substitutions <= 5",
            "met" if c3.induced_substitution_count <= DEPLOY_INDUCED_MAX else "not_met",
            f"C3 induced={c3.induced_substitution_count}, ceiling={DEPLOY_INDUCED_MAX}",
        ),
    )
    deployable = all(clause.verdict == "met" for clause in deployable_clauses)

    channel_reopened_clause = ClauseResult(
        "C3 induced-substitutions >= 20",
        "met" if c3.induced_substitution_count >= DEPLOY_INDUCED_REOPENED_MIN else "not_met",
        f"C3 induced={c3.induced_substitution_count}, floor={DEPLOY_INDUCED_REOPENED_MIN}",
    )
    channel_reopened = (not deployable) and channel_reopened_clause.verdict == "met"

    if deployable:
        overall: DeployAugmentOverall = "DEPLOYABLE"
    elif channel_reopened:
        overall = "CHANNEL-REOPENED"
    else:
        overall = "no flag"

    return DeployAugmentVerdict(
        deployable_clauses=deployable_clauses,
        deployable=deployable,
        channel_reopened_clause=channel_reopened_clause,
        channel_reopened=channel_reopened,
        overall=overall,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2cReadReport:
    attempt_dir: Path
    flight_status: str | None
    split_identity_hash: str
    stage2_arm_plan_path: Path
    headroom_path: Path
    per_arm: Mapping[str, PerArmReport]
    form_robustness_verdict: FormRobustnessVerdict
    deploy_augment_verdict: DeployAugmentVerdict
    registry_warnings: tuple[str, ...]


def build_a2t_s2c_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    headroom_path: Path,
    stage2_arm_plan_path: Path,
    split_role: str = DEFAULT_SPLIT_ROLE,
) -> A2tS2cReadReport:
    attempt_dir = Path(attempt_dir)
    repo_root = Path(repo_root)
    stage2_arm_plan_path = Path(stage2_arm_plan_path)

    from ..data.audio2tool import load_expected_calls, load_tool_registry
    from .a2t_read import _load_split_receipt

    rows, malformed_row_reasons = load_attempt_rows(attempt_dir)
    flight_receipt = load_flight_receipt(attempt_dir)
    headroom_identity = load_headroom_identity(headroom_path)
    arm_plan = load_arm_plan(stage2_arm_plan_path)

    split_receipt = _load_split_receipt(repo_root, split_role)
    split_identity_hash = str(split_receipt["split_identity_hash"])

    expected_by_id = load_expected_calls(lock, root, repo_root=repo_root)
    registry_index = {row["tool_name"]: row for row in load_tool_registry(lock, root)}

    rows_by_arm: dict[str, list[OutputRow]] = {arm: [] for arm in A2T_S2C_ARMS}
    unknown_arm_rows: list[OutputRow] = []
    duplicate_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        pair = (row.arm, row.sample_id)
        if pair in seen:
            duplicate_pairs.append(pair)
            continue
        seen.add(pair)
        if row.arm not in A2T_S2C_ARMS:
            unknown_arm_rows.append(row)
            continue
        rows_by_arm[row.arm].append(row)

    defect_reasons = _harness_defect_reasons(
        malformed_row_reasons=malformed_row_reasons,
        flight_receipt=flight_receipt,
        rows_by_arm=rows_by_arm,
        unknown_arm_rows=unknown_arm_rows,
        duplicate_pairs=duplicate_pairs,
        arm_plan=arm_plan,
        headroom_ids=headroom_identity.sample_ids,
        split_identity_hash=split_identity_hash,
        expected_by_id=expected_by_id,
    )
    if defect_reasons:
        raise A2tS2cReadError(
            "harness defect(s) detected; refusing to score:\n  " + "\n  ".join(defect_reasons)
        )

    per_arm: dict[str, PerArmReport] = {}
    all_warnings: list[str] = []
    for arm in A2T_S2C_ARMS:
        scores = []
        for row in sorted(rows_by_arm[arm], key=lambda r: r.sample_id):
            supplied_names = _supplied_tool_names_for_row(row, arm_plan)
            score = score_row(
                row,
                expected_by_id=expected_by_id,
                registry_index=registry_index,
                supplied_tool_names=supplied_names,
            )
            scores.append(score)
            all_warnings.extend(score.registry_warnings)

        scores_by_tier: dict[str, list] = {}
        for score in scores:
            scores_by_tier.setdefault(score.tier, []).append(score)
        per_arm[arm] = PerArmReport(
            overall=build_arm_aggregate(arm, scores),
            by_tier={
                tier: build_arm_aggregate(arm, tier_scores)
                for tier, tier_scores in sorted(scores_by_tier.items())
            },
        )

    form_robustness_verdict = evaluate_form_robustness(per_arm[C1_ARM].overall, per_arm[C2_ARM].overall)
    deploy_augment_verdict = evaluate_deploy_augment(per_arm[C3_ARM].overall)

    return A2tS2cReadReport(
        attempt_dir=attempt_dir,
        flight_status=None if flight_receipt is None else flight_receipt.get("status"),
        split_identity_hash=split_identity_hash,
        stage2_arm_plan_path=stage2_arm_plan_path,
        headroom_path=Path(headroom_path),
        per_arm=per_arm,
        form_robustness_verdict=form_robustness_verdict,
        deploy_augment_verdict=deploy_augment_verdict,
        registry_warnings=tuple(sorted(set(all_warnings))),
    )


# ---------------------------------------------------------------------------
# Machine-readable JSON + human-readable rendering, and the CLI entry point.
# ---------------------------------------------------------------------------


def _arm_aggregate_json(agg: ArmAggregate) -> dict[str, object]:
    return {
        "arm": agg.arm,
        "n_samples": agg.n_samples,
        "tool_selection_retention": agg.tool_accuracy,
        "em_conversion_rate": agg.em_conversion_rate,
        "em_flip_count": agg.em_flip_count,
        "slot_precision": agg.slot_precision,
        "slot_recall": agg.slot_recall,
        "slot_f1": agg.slot_f1,
        "empty_call_rate": agg.empty_call_rate,
        "parse_failure_rate": agg.parse_failure_rate,
        "induced_substitution_count": agg.induced_substitution_count,
        "interpretive_weight": agg.interpretive_weight,
    }


def _clause_json(clause: ClauseResult) -> dict[str, object]:
    return {"clause_text": clause.clause_text, "verdict": clause.verdict, "detail": clause.detail}


def report_to_json(report: A2tS2cReadReport) -> dict[str, object]:
    robustness = report.form_robustness_verdict
    deploy = report.deploy_augment_verdict
    return {
        "schema": REPORT_SCHEMA,
        "attempt_dir": str(report.attempt_dir),
        "flight_status": report.flight_status,
        "split_identity_hash": report.split_identity_hash,
        "stage2_arm_plan_path": str(report.stage2_arm_plan_path),
        "headroom_path": str(report.headroom_path),
        "registry_defaults_parse_warnings": list(report.registry_warnings),
        "per_arm": {
            arm: {
                "overall": _arm_aggregate_json(per_arm_report.overall),
                "by_tier": {
                    tier: _arm_aggregate_json(agg) for tier, agg in per_arm_report.by_tier.items()
                },
            }
            for arm, per_arm_report in report.per_arm.items()
        },
        "form_robustness_verdict": {
            "robust_clauses": [_clause_json(c) for c in robustness.robust_clauses],
            "robust": robustness.robust,
            "fragile_clauses": [_clause_json(c) for c in robustness.fragile_clauses],
            "fragile": robustness.fragile,
            "overall": robustness.overall,
        },
        "deploy_augment_verdict": {
            "deployable_clauses": [_clause_json(c) for c in deploy.deployable_clauses],
            "deployable": deploy.deployable,
            "channel_reopened_clause": _clause_json(deploy.channel_reopened_clause),
            "channel_reopened": deploy.channel_reopened,
            "overall": deploy.overall,
        },
    }


def render_report(report: A2tS2cReadReport) -> str:
    robustness = report.form_robustness_verdict
    deploy = report.deploy_augment_verdict
    lines = [
        "P-A2T Stage-2c form-robustness probe pinned offline read "
        "(docs/readiness/2026-08-18-pa2t-stage2c-preregistration-REGISTERED.md)",
        "=" * 78,
        "",
        f"attempt dir: {report.attempt_dir}",
        f"flight status: {report.flight_status!r}",
        f"split identity hash: {report.split_identity_hash}",
        f"Stage-2 arm plan (reused verbatim): {report.stage2_arm_plan_path}",
        f"headroom manifest: {report.headroom_path}",
        "",
        "Per-arm aggregates (pooled)",
    ]
    header = (
        f"  {'arm':<6}{'n':>4}{'retention':>11}{'conv_rate':>11}{'em_flips':>9}"
        f"{'slot_f1':>9}{'empty':>7}{'parse_fail':>11}{'induced':>9}"
    )
    lines.append(header)
    for arm in A2T_S2C_ARMS:
        agg = report.per_arm[arm].overall
        lines.append(
            f"  {arm:<6}{agg.n_samples:>4}{agg.tool_accuracy:>11.4f}{agg.em_conversion_rate:>11.4f}"
            f"{agg.em_flip_count:>9}{agg.slot_f1:>9.4f}{agg.empty_call_rate:>7.4f}"
            f"{agg.parse_failure_rate:>11.4f}{agg.induced_substitution_count:>9}"
        )
    lines.append("")

    lines.append("Per-tier breakdown (PER-TIER REPORTING MANDATORY -- pooled is never the headline)")
    for arm in A2T_S2C_ARMS:
        lines.append(f"  arm {arm}:")
        for tier in sorted(report.per_arm[arm].by_tier):
            agg = report.per_arm[arm].by_tier[tier]
            weight = "interpretive-weight" if agg.interpretive_weight else "small-n caveat"
            lines.append(
                f"    {tier:<22}{agg.n_samples:>4} conv_rate={agg.em_conversion_rate:.4f} "
                f"retention={agg.tool_accuracy:.4f} slot_f1={agg.slot_f1:.4f} induced={agg.induced_substitution_count} "
                f"({weight})"
            )
    lines.append("")

    if report.registry_warnings:
        lines.append(f"registry_defaults parse warnings (informational, non-fatal): {len(report.registry_warnings)}")
        for warning in report.registry_warnings[:10]:
            lines.append(f"  {warning}")
        if len(report.registry_warnings) > 10:
            lines.append(f"  ... (+{len(report.registry_warnings) - 10} more)")
        lines.append("")

    lines.append("Form-robustness verdict (primary, C1+C2 jointly; retention carries NO verdict clause)")
    lines.append(f"ROBUST: {'MET' if robustness.robust else 'not met'}")
    for clause in robustness.robust_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"FORM-FRAGILE: {'MET' if robustness.fragile else 'not met'}")
    for clause in robustness.fragile_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"FORM-ROBUSTNESS OVERALL: {robustness.overall}")
    lines.append("")

    lines.append("DEPLOY-AUGMENT overlay (independent, C3 alone -- fires no primary branch)")
    lines.append(f"DEPLOYABLE: {'MET' if deploy.deployable else 'not met'}")
    for clause in deploy.deployable_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"CHANNEL-REOPENED: {'MET' if deploy.channel_reopened else 'not met'}")
    lines.append(f"  [{deploy.channel_reopened_clause.verdict.upper():>8}] {deploy.channel_reopened_clause.clause_text}")
    lines.append(f"           {deploy.channel_reopened_clause.detail}")
    lines.append(f"DEPLOY-AUGMENT OVERALL: {deploy.overall}")

    return "\n".join(lines)


def _default_stage2_arm_plan_path(repo_root: Path) -> Path:
    """Resolves ``configs/probes/g0-binding/a2t-s2c-flight.json``'s own
    ``stage2_arm_plan_path.path`` field, expanding ``$SPEECHRL_DATA_DIR``
    from the environment -- keeps the CLI thin by letting the committed,
    REGISTERED config stay the single source of truth for WHICH
    already-flown Stage-2 attempt's mapping is reused (mirrors
    ``analysis.a2t_s2b_read._default_stage2_arm_plan_path`` exactly)."""

    import os

    config_path = repo_root / "configs" / "probes" / "g0-binding" / "a2t-s2c-flight.json"
    document = json.loads(config_path.read_text(encoding="utf-8"))
    raw = str(document["stage2_arm_plan_path"]["path"])
    return Path(os.path.expandvars(raw))


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="a2t-s2c-read",
        description=(
            "P-A2T Stage-2c form-robustness probe pinned offline read suite: per-arm and per-tier "
            "EM-conversion/tool-selection-retention/slot-P-R-F1/empty-call/induced-substitution/"
            "parse-failure metrics and the mechanical form-robustness (ROBUST/FORM-FRAGILE/"
            "INCONCLUSIVE-C) evaluator plus the independent DEPLOY-AUGMENT overlay "
            "(DEPLOYABLE/CHANNEL-REOPENED/no flag). Model-free, read-only; never opens a model "
            "session."
        ),
    )
    parser.add_argument("attempt_dir", type=Path, help="the flight's own attempt directory (carries outputs.jsonl)")
    parser.add_argument("--output-dir", required=True, type=Path, help="directory to write verdict.json / report.txt")
    parser.add_argument(
        "--headroom-manifest", type=Path, default=None,
        help="override headroom.json's path (default: docs/checks/speech-aware-evidence-acquisition/"
        "2026-08-18-pa2t-a0-read/headroom.json)",
    )
    parser.add_argument(
        "--stage2-arm-plan", type=Path, default=None,
        help="override the REUSED Stage-2 {RUN_ID}.arm-plan.json path (default: the committed "
        "a2t-s2c-flight.json config's own stage2_arm_plan_path, $SPEECHRL_DATA_DIR expanded)",
    )
    parser.add_argument(
        "--split-role", default=DEFAULT_SPLIT_ROLE,
        help=f"the frozen probe receipt's split_role to read against (default: {DEFAULT_SPLIT_ROLE!r})",
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="TEST-ONLY override of the study repo root used to resolve the umbrella lock and the frozen receipts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    import sys

    from ..data.lock import data_root, load_lock, umbrella_lock_path
    from ..e0.artifacts import REPO_ROOT, write_json_artifact

    args = _cli_parser().parse_args(argv)
    repo_root = Path(args.repo_root) if args.repo_root else REPO_ROOT
    headroom_path = args.headroom_manifest or (
        repo_root
        / "docs"
        / "checks"
        / "speech-aware-evidence-acquisition"
        / "2026-08-18-pa2t-a0-read"
        / "headroom.json"
    )
    stage2_arm_plan_path = args.stage2_arm_plan or _default_stage2_arm_plan_path(repo_root)

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
        report = build_a2t_s2c_report(
            args.attempt_dir,
            lock,
            root,
            repo_root=repo_root,
            headroom_path=headroom_path,
            stage2_arm_plan_path=stage2_arm_plan_path,
            split_role=args.split_role,
        )
    except (A2tS2cReadError, A2tS2ReadError) as error:  # module docstring note 8
        print(f"REFUSED: {error}", file=sys.stderr)
        return 1

    write_json_artifact(verdict_path, report_to_json(report))
    rendered = render_report(report)
    (output_dir / "report.txt").write_text(rendered + "\n", encoding="utf-8", newline="\n")
    print(rendered)
    print(f"\nwrote machine-readable verdict to {verdict_path}")
    return 0


__all__ = [
    "DEFAULT_SPLIT_ROLE",
    "DEPLOY_CONVERSION_MIN",
    "DEPLOY_INDUCED_MAX",
    "DEPLOY_INDUCED_REOPENED_MIN",
    "FRAGILE_CONVERSION_MAX",
    "FRAGILE_INDUCED_MIN",
    "INTERPRETIVE_WEIGHT_MIN_N",
    "REPORT_SCHEMA",
    "ROBUST_CONVERSION_MIN",
    "ROBUST_INDUCED_MAX",
    "RUN_ID",
    "A2tS2cReadError",
    "A2tS2cReadReport",
    "DeployAugmentVerdict",
    "FormRobustnessVerdict",
    "build_a2t_s2c_report",
    "evaluate_deploy_augment",
    "evaluate_form_robustness",
    "main",
    "report_to_json",
    "render_report",
]
