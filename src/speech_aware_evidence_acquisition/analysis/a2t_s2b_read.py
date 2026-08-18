"""P-A2T Stage-2b follow-up probe offline read suite (pinned, pre-registered).

Model-free, read-only: this module NEVER opens a model session and never
mutates an attempt directory -- it scores an already-written B1/B2 attempt's
``outputs.jsonl`` / ``flight-receipt.json`` (``rails.probes.a2t_s2b_flight.
run_a2t_s2b_flight``'s own row shape -- IDENTICAL to Stage-2's own
``{arm, sample_id, supplied_tool, response, timing}``, since
``rails.probes.a2t_s2b_flight`` reuses ``rails.probes.a2t_s2_flight``'s own
``A2tS2ArmResult``/``result_to_json``/``write_outputs_jsonl`` directly) PLUS
Stage-2's OWN already-flown ``{RUN_ID}.arm-plan.json`` (reused verbatim,
never re-derived, for the exact same reason
``rails.probes.a2t_s2b_flight.build_flight_plan`` reuses it: B1's roster and
B2's wrong tool are Stage-2's S1p/S4 mappings, not a fresh construction).

Purpose (``docs/readiness/2026-08-18-pa2t-stage2b-preregistration-
REGISTERED.md`` section 1): two INDEPENDENT questions, each with its own
mechanical verdict (no exclusive branch lattice across the two -- the
prereg's own heading: "no exclusive branch lattice, per the P-SLU rule-gap
lesson"):

- Q-A (corruption-channel localization, arm B1): does stripping
  ``argument_defaults`` from S1p's own roster still convert, without
  inducing substitutions? CONFIRMED-CUT / NOT-DEFAULTS / INCONCLUSIVE-A.
- Q-B (schema vs knowledge, arm B2): does a highlighted WRONG tool row
  still convert, with the correct tool PRESENT elsewhere in the registry?
  SCHEMA-CONTRIBUTES / KNOWLEDGE-TIED / INCONCLUSIVE-B, with a MISLEAD
  overlay that fires INDEPENDENTLY of which of those three verdicts holds.

REUSE, NOT RE-DERIVATION (mission instruction: "reusing a2t_s2_read
primitives ... the same approved operationalizations (bare-key induced
alignment, direct primitives micro-aggregation)"). Every scoring primitive
below is imported directly from ``analysis.a2t_s2_read``, never
reimplemented a second way:

- ``OutputRow``/``load_attempt_rows``/``load_flight_receipt`` for the
  attempt's own IDENTICALLY-SHAPED rows.
- ``load_headroom_identity`` for the frozen 120-id headroom set (the SAME
  set both Stage-2 and Stage-2b fly over -- prereg intro: "the SAME 120
  headroom ids").
- ``ArmPlan``/``load_arm_plan`` for Stage-2's OWN reused mapping.
- ``score_row``/``count_induced_substitutions``/``supplied_argument_values``/
  ``parse_argument_defaults`` for per-row scoring and the bare-key
  induced-substitution alignment (note 7 of that module, unchanged here).
- ``ArmAggregate``/``build_arm_aggregate``/``PerArmReport`` for the
  micro-aggregated (raw-count-summed, never per-row-averaged) per-arm and
  per-tier ingredient numbers.
- ``ClauseResult`` for this module's own mechanical clause records (the
  SAME record shape Stage-2's ``evaluate_branch_rules`` uses, reused here
  for :func:`evaluate_qa`/:func:`evaluate_qb` rather than a bespoke shape).

ENGINEERING-INTERPRETATION NOTES (flagged here, mirroring
``analysis.a2t_s2_read``'s own discipline -- each is a documented,
reviewable choice, not a silent guess):

1. "B1 conversion >= 8/120" and "B2 conversion <= 2/120" (etc.) are
   RATIOS, not raw counts fixed to n=120: :data:`Q_A_CONFIRMED_CUT_CONVERSION_MIN`
   = ``8/120`` and :data:`Q_B_KNOWLEDGE_TIED_CONVERSION_MAX` = ``2/120`` are
   compared against ``ArmAggregate.em_conversion_rate`` (a RATE), never a
   raw ``em_flip_count`` compared to a literal "8"/"2" -- this keeps the
   evaluator well-defined for a small synthetic fixture arm (this module's
   OWN test suite) while being numerically IDENTICAL to the mission's
   literal fraction at the real flight's n=120. Induced-substitution
   thresholds ("<=5"/">=20") stay RAW COUNTS (``ArmAggregate.
   induced_substitution_count``), exactly as literally stated -- the
   prereg names no denominator for them.
2. "B2 conversion >= 6/120 (= max(2x noise, 5%))" is CITED, not
   re-measured (prereg section 2: "No new noise arm: the Stage-2 N0r
   established a perfectly stable EM comparator (0/40) and a 12.5%
   selection-noise band; both are cited, not re-measured"). Evaluating
   Stage-2's OWN floor formula (``analysis.a2t_s2_read.evaluate_branch_rules``:
   ``noise_floor = max(n0r.em_conversion_rate, 1/n0r.n_samples)``, ``floor
   = max(2*noise_floor, MIN_NOISE_FLOOR_PCT)``) at Stage-2's own recorded
   N0r result (0/40 exact-match conversions) gives ``max(2*max(0.0,
   1/40), 0.05) = max(0.05, 0.05) = 0.05 = 6/120`` -- EXACTLY the prereg's
   own literal number, confirming it is that citation rather than an
   independent constant. :data:`Q_B_SCHEMA_CONTRIBUTES_CONVERSION_MIN` is
   pinned to ``0.05`` directly (this module carries no N0r arm of its own
   to recompute it from).
3. "B2 tool-selection retention" clauses (KNOWLEDGE-TIED >= 85%, MISLEAD
   < 80%) both reduce to B2's raw mean ``tool_accuracy`` -- the SAME
   "tool-selection retention == raw mean tool_accuracy" reduction
   ``analysis.a2t_s2_read``'s own note 11 documents for Stage-2's arms.
4. MISLEAD is evaluated INDEPENDENTLY of the Q-B primary verdict (prereg
   section 1: "fires independently") -- :func:`evaluate_qb` computes
   ``mislead`` from ``B2.tool_accuracy`` alone, never gated behind
   ``schema_contributes``/``knowledge_tied``/``inconclusive_b``, and the
   rendered/JSON report always surfaces it as its own field rather than
   folding it into ``overall`` as a mutually-exclusive branch (mirrors
   Stage-2's own DOSE point: "secondary, descriptive", reported alongside,
   never competing with the primary branch -- appended to ``overall`` as a
   suffix exactly the way Stage-2's DOSE point is).
5. Harness-defect checks (this module's own :func:`_harness_defect_reasons`)
   ADD one check beyond Stage-2's own template: for every row, the
   attempt's OWN written ``supplied_tool`` label must match what Stage-2's
   reused arm-plan implies for that (arm, sample) -- B1's comma-joined S1p
   roster names, B2's single wrong-tool name -- a cheap, independent proof
   that the flight actually used the SAME reused mapping this read now
   assumes, rather than merely trusting it silently.
6. Per note 10 of ``analysis.a2t_s2_read`` (reused verbatim here): Q-A/Q-B
   are evaluated on POOLED (whole-arm) aggregates only; per-tier reporting
   accompanies every verdict but never substitutes a second, tier-scoped
   evaluation the preregistration never defines.
7. TWO exception classes, deliberately: this module's OWN aggregated
   harness-defect check (:func:`_harness_defect_reasons`, everything it
   collects) raises :class:`A2tS2bReadError`; a RAW failure inside a
   directly reused Stage-2 loader (``load_arm_plan``'s own "file missing"/
   "invalid JSON" checks, ``load_headroom_identity``'s own schema check,
   ``load_attempt_rows``'s own "no outputs.jsonl" check) surfaces as that
   loader's OWN :class:`~analysis.a2t_s2_read.A2tS2ReadError` unchanged --
   never re-wrapped, mirroring ``analysis.a2t_s2_read``'s own
   ``test_missing_arm_plan_raises_directly`` precedent (a loader failure
   "raises directly", it is not a harness-defect AGGREGATION). :func:`main`
   below catches BOTH, since a CLI caller should see the SAME "REFUSED: ..."
   treatment regardless of which of the two actually fired.

DEVELOPED AND TESTED EXCLUSIVELY AGAINST HAND-AUTHORED SYNTHETIC FIXTURES
(``tests/unit/test_a2t_s2b_read.py``, itself reusing
``tests/unit/test_a2t_s2_read.py``'s own ``A2tS2World`` fixture directly).
This module is never run against a real flight attempt directory by the
task that wrote it; a later, separately-registered one-shot read session
points ``build_a2t_s2b_report``/the CLI at the real COMPLETED attempt.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, Sequence

from ..rails.probes.a2t_s2b_flight import A2T_S2B_ARMS, B1_ARM, B2_ARM
from ..reproduction.toolcall_scoring import ToolCall
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

REPORT_SCHEMA = "saea-a2t-s2b-read-v1"
# Names the exposure-ledger row / the Stage-2b preregistration's own run id
# (configs/probes/g0-binding/a2t-s2b-flight.json's own exposure_ledger_row).
RUN_ID = "SAEA-PROBE-a2t-s2b-120"
DEFAULT_SPLIT_ROLE = "discovery"

INTERPRETIVE_WEIGHT_MIN_N = 16  # preregistration section 3, unchanged from Stage-2

# Preregistration section 1 thresholds, quoted verbatim in each clause's own
# detail text below (module docstring notes 1-2 explain the ratio/citation
# choices).
Q_A_CONFIRMED_CUT_INDUCED_MAX = 5
Q_A_CONFIRMED_CUT_CONVERSION_MIN = 8 / 120
Q_A_NOT_DEFAULTS_INDUCED_MIN = 20

Q_B_SCHEMA_CONTRIBUTES_CONVERSION_MIN = 0.05  # == 6/120, cited (module docstring note 2)
Q_B_KNOWLEDGE_TIED_CONVERSION_MAX = 2 / 120
Q_B_KNOWLEDGE_TIED_RETENTION_MIN = 0.85
Q_B_MISLEAD_RETENTION_MAX = 0.80


class A2tS2bReadError(RuntimeError):
    """Malformed attempt-dir/Stage-2-arm-plan/headroom input, or a harness
    defect this module's own "machine harness checks, fail-closed"
    discipline requires refusing on -- never raised for an ordinary,
    structurally clean read."""


# ---------------------------------------------------------------------------
# Harness-defect checks (module docstring note 5 adds the supplied_tool
# cross-check beyond Stage-2's own template).
# ---------------------------------------------------------------------------


def _b1_expected_label(arm_plan: ArmPlan, sample_id: str) -> str:
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
    expected_by_id: Mapping[str, tuple[ToolCall, ...]],
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
        if arms != list(A2T_S2B_ARMS):
            reasons.append(f"flight-receipt arms={arms!r}, expected {list(A2T_S2B_ARMS)!r}")
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

    for key, mapping in (("s1p_tool_names", arm_plan.s1p_tool_names), ("s4_tool_name", arm_plan.s4_tool_name)):
        keys = set(mapping)
        if not headroom_set <= keys:
            reasons.append(
                f"Stage-2 arm-plan {key!r} does not cover this flight's own headroom ids "
                f"(missing={sorted(headroom_set - keys)[:5]})"
            )

    fixed_points = sorted(tool for tool, deranged in arm_plan.s4_derangement.items() if tool == deranged)
    if fixed_points:
        reasons.append(f"Stage-2 arm-plan s4_derangement has fixed point(s) (tool maps to itself): {fixed_points[:5]}")

    expected_counts = {arm: len(headroom_ids) for arm in A2T_S2B_ARMS}
    total_rows = sum(len(rows) for rows in rows_by_arm.values()) + len(unknown_arm_rows)
    expected_total = sum(expected_counts.values())
    if total_rows != expected_total:
        reasons.append(
            f"total row count {total_rows} != expected {expected_total} (2 x len(headroom_ids))"
        )

    for arm in A2T_S2B_ARMS:
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

        # Module docstring note 5: the written supplied_tool label must
        # match what the reused Stage-2 mapping implies for this row.
        for row in rows:
            if arm == B1_ARM:
                expected_label = _b1_expected_label(arm_plan, row.sample_id)
            else:
                expected_label = arm_plan.s4_tool_name.get(row.sample_id, "")
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
    if row.arm == B1_ARM:
        return arm_plan.s1p_tool_names.get(row.sample_id, ())
    if row.arm == B2_ARM:
        name = arm_plan.s4_tool_name.get(row.sample_id)
        return (name,) if name else ()
    return ()


# ---------------------------------------------------------------------------
# Mechanical Q-A / Q-B evaluators (prereg section 1, quoted verbatim below).
# ---------------------------------------------------------------------------

QAOverall = Literal["CONFIRMED-CUT", "NOT-DEFAULTS", "INCONCLUSIVE-A"]
QBOverall = Literal["SCHEMA-CONTRIBUTES", "KNOWLEDGE-TIED", "INCONCLUSIVE-B"]


@dataclass(frozen=True)
class QAVerdict:
    confirmed_cut_clauses: tuple[ClauseResult, ...]
    confirmed_cut: bool
    not_defaults_clause: ClauseResult
    not_defaults: bool
    overall: QAOverall


@dataclass(frozen=True)
class QBVerdict:
    schema_contributes_clause: ClauseResult
    schema_contributes: bool
    knowledge_tied_clauses: tuple[ClauseResult, ...]
    knowledge_tied: bool
    mislead_clause: ClauseResult
    mislead: bool
    overall: QBOverall
    overall_with_overlay: str


def evaluate_qa(b1: ArmAggregate) -> QAVerdict:
    """Q-A -- corruption-channel localization (prereg section 1, quoted):
    "CONFIRMED-CUT: B1 induced-substitutions <= 5 AND B1 conversion >=
    8/120 ... NOT-DEFAULTS: B1 induced >= 20 ... Otherwise INCONCLUSIVE-A"."""

    induced_clause = ClauseResult(
        "B1 induced-substitutions <= 5",
        "met" if b1.induced_substitution_count <= Q_A_CONFIRMED_CUT_INDUCED_MAX else "not_met",
        f"B1 induced={b1.induced_substitution_count}, ceiling={Q_A_CONFIRMED_CUT_INDUCED_MAX}",
    )
    conversion_clause = ClauseResult(
        "B1 conversion >= 8/120",
        "met" if b1.em_conversion_rate >= Q_A_CONFIRMED_CUT_CONVERSION_MIN else "not_met",
        f"B1 conversion={b1.em_conversion_rate:.4f} ({b1.em_flip_count}/{b1.n_samples}), "
        f"floor={Q_A_CONFIRMED_CUT_CONVERSION_MIN:.4f}",
    )
    confirmed_cut = induced_clause.verdict == "met" and conversion_clause.verdict == "met"

    not_defaults_clause = ClauseResult(
        "B1 induced-substitutions >= 20",
        "met" if b1.induced_substitution_count >= Q_A_NOT_DEFAULTS_INDUCED_MIN else "not_met",
        f"B1 induced={b1.induced_substitution_count}, floor={Q_A_NOT_DEFAULTS_INDUCED_MIN}",
    )
    not_defaults = (not confirmed_cut) and not_defaults_clause.verdict == "met"

    if confirmed_cut:
        overall: QAOverall = "CONFIRMED-CUT"
    elif not_defaults:
        overall = "NOT-DEFAULTS"
    else:
        overall = "INCONCLUSIVE-A"

    return QAVerdict(
        confirmed_cut_clauses=(induced_clause, conversion_clause),
        confirmed_cut=confirmed_cut,
        not_defaults_clause=not_defaults_clause,
        not_defaults=not_defaults,
        overall=overall,
    )


def evaluate_qb(b2: ArmAggregate) -> QBVerdict:
    """Q-B -- schema vs knowledge (prereg section 1, quoted): "SCHEMA-
    CONTRIBUTES: B2 conversion >= 6/120 ... KNOWLEDGE-TIED: B2 conversion
    <= 2/120 AND B2 tool-selection retention >= 85% ... MISLEAD overlay
    (fires independently): B2 retention < 80% ... Otherwise INCONCLUSIVE-B".
    MISLEAD is evaluated and reported INDEPENDENTLY of the primary verdict
    (module docstring note 4) -- it never competes with SCHEMA-CONTRIBUTES/
    KNOWLEDGE-TIED/INCONCLUSIVE-B, mirroring Stage-2's own DOSE point."""

    schema_clause = ClauseResult(
        "B2 conversion >= 6/120 (= max(2x noise, 5%), cited from Stage-2's own N0r 0/40)",
        "met" if b2.em_conversion_rate >= Q_B_SCHEMA_CONTRIBUTES_CONVERSION_MIN else "not_met",
        f"B2 conversion={b2.em_conversion_rate:.4f} ({b2.em_flip_count}/{b2.n_samples}), "
        f"floor={Q_B_SCHEMA_CONTRIBUTES_CONVERSION_MIN:.4f}",
    )
    schema_contributes = schema_clause.verdict == "met"

    kt_conversion_clause = ClauseResult(
        "B2 conversion <= 2/120",
        "met" if b2.em_conversion_rate <= Q_B_KNOWLEDGE_TIED_CONVERSION_MAX else "not_met",
        f"B2 conversion={b2.em_conversion_rate:.4f}, ceiling={Q_B_KNOWLEDGE_TIED_CONVERSION_MAX:.4f}",
    )
    kt_retention_clause = ClauseResult(
        "B2 tool-selection retention >= 85%",
        "met" if b2.tool_accuracy >= Q_B_KNOWLEDGE_TIED_RETENTION_MIN else "not_met",
        f"B2 retention={b2.tool_accuracy:.4f} ({b2.n_samples} samples), floor={Q_B_KNOWLEDGE_TIED_RETENTION_MIN:.2f}",
    )
    knowledge_tied = (
        (not schema_contributes)
        and kt_conversion_clause.verdict == "met"
        and kt_retention_clause.verdict == "met"
    )

    mislead_clause = ClauseResult(
        "B2 tool-selection retention < 80% (clearly below the measured 12.5% selection-noise band)",
        "met" if b2.tool_accuracy < Q_B_MISLEAD_RETENTION_MAX else "not_met",
        f"B2 retention={b2.tool_accuracy:.4f}, ceiling={Q_B_MISLEAD_RETENTION_MAX:.2f}",
    )
    mislead = mislead_clause.verdict == "met"

    if schema_contributes:
        overall: QBOverall = "SCHEMA-CONTRIBUTES"
    elif knowledge_tied:
        overall = "KNOWLEDGE-TIED"
    else:
        overall = "INCONCLUSIVE-B"
    overall_with_overlay = overall + (" + MISLEAD overlay (independent)" if mislead else "")

    return QBVerdict(
        schema_contributes_clause=schema_clause,
        schema_contributes=schema_contributes,
        knowledge_tied_clauses=(kt_conversion_clause, kt_retention_clause),
        knowledge_tied=knowledge_tied,
        mislead_clause=mislead_clause,
        mislead=mislead,
        overall=overall,
        overall_with_overlay=overall_with_overlay,
    )


# ---------------------------------------------------------------------------
# Top-level orchestration.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class A2tS2bReadReport:
    attempt_dir: Path
    flight_status: str | None
    split_identity_hash: str
    stage2_arm_plan_path: Path
    headroom_path: Path
    per_arm: Mapping[str, PerArmReport]
    qa_verdict: QAVerdict
    qb_verdict: QBVerdict
    registry_warnings: tuple[str, ...]


def build_a2t_s2b_report(
    attempt_dir: Path,
    lock: Mapping[str, object],
    root: Path,
    *,
    repo_root: Path,
    headroom_path: Path,
    stage2_arm_plan_path: Path,
    split_role: str = DEFAULT_SPLIT_ROLE,
) -> A2tS2bReadReport:
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

    rows_by_arm: dict[str, list[OutputRow]] = {arm: [] for arm in A2T_S2B_ARMS}
    unknown_arm_rows: list[OutputRow] = []
    duplicate_pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        pair = (row.arm, row.sample_id)
        if pair in seen:
            duplicate_pairs.append(pair)
            continue
        seen.add(pair)
        if row.arm not in A2T_S2B_ARMS:
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
        raise A2tS2bReadError(
            "harness defect(s) detected; refusing to score:\n  " + "\n  ".join(defect_reasons)
        )

    per_arm: dict[str, PerArmReport] = {}
    all_warnings: list[str] = []
    for arm in A2T_S2B_ARMS:
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

    qa_verdict = evaluate_qa(per_arm[B1_ARM].overall)
    qb_verdict = evaluate_qb(per_arm[B2_ARM].overall)

    return A2tS2bReadReport(
        attempt_dir=attempt_dir,
        flight_status=None if flight_receipt is None else flight_receipt.get("status"),
        split_identity_hash=split_identity_hash,
        stage2_arm_plan_path=stage2_arm_plan_path,
        headroom_path=Path(headroom_path),
        per_arm=per_arm,
        qa_verdict=qa_verdict,
        qb_verdict=qb_verdict,
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


def report_to_json(report: A2tS2bReadReport) -> dict[str, object]:
    qa = report.qa_verdict
    qb = report.qb_verdict
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
        "qa_verdict": {
            "confirmed_cut_clauses": [_clause_json(c) for c in qa.confirmed_cut_clauses],
            "confirmed_cut": qa.confirmed_cut,
            "not_defaults_clause": _clause_json(qa.not_defaults_clause),
            "not_defaults": qa.not_defaults,
            "overall": qa.overall,
        },
        "qb_verdict": {
            "schema_contributes_clause": _clause_json(qb.schema_contributes_clause),
            "schema_contributes": qb.schema_contributes,
            "knowledge_tied_clauses": [_clause_json(c) for c in qb.knowledge_tied_clauses],
            "knowledge_tied": qb.knowledge_tied,
            "mislead_clause": _clause_json(qb.mislead_clause),
            "mislead": qb.mislead,
            "overall": qb.overall,
            "overall_with_overlay": qb.overall_with_overlay,
        },
    }


def render_report(report: A2tS2bReadReport) -> str:
    qa = report.qa_verdict
    qb = report.qb_verdict
    lines = [
        "P-A2T Stage-2b follow-up probe pinned offline read "
        "(docs/readiness/2026-08-18-pa2t-stage2b-preregistration-REGISTERED.md)",
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
    for arm in A2T_S2B_ARMS:
        agg = report.per_arm[arm].overall
        lines.append(
            f"  {arm:<6}{agg.n_samples:>4}{agg.tool_accuracy:>11.4f}{agg.em_conversion_rate:>11.4f}"
            f"{agg.em_flip_count:>9}{agg.slot_f1:>9.4f}{agg.empty_call_rate:>7.4f}"
            f"{agg.parse_failure_rate:>11.4f}{agg.induced_substitution_count:>9}"
        )
    lines.append("")

    lines.append("Per-tier breakdown (PER-TIER REPORTING MANDATORY -- pooled is never the headline)")
    for arm in A2T_S2B_ARMS:
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

    lines.append("Q-A -- corruption-channel localization (arm B1)")
    lines.append(f"CONFIRMED-CUT: {'MET' if qa.confirmed_cut else 'not met'}")
    for clause in qa.confirmed_cut_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"NOT-DEFAULTS: {'MET' if qa.not_defaults else 'not met'}")
    lines.append(f"  [{qa.not_defaults_clause.verdict.upper():>8}] {qa.not_defaults_clause.clause_text}")
    lines.append(f"           {qa.not_defaults_clause.detail}")
    lines.append(f"Q-A OVERALL: {qa.overall}")
    lines.append("")

    lines.append("Q-B -- schema vs knowledge (arm B2)")
    lines.append(f"SCHEMA-CONTRIBUTES: {'MET' if qb.schema_contributes else 'not met'}")
    lines.append(f"  [{qb.schema_contributes_clause.verdict.upper():>8}] {qb.schema_contributes_clause.clause_text}")
    lines.append(f"           {qb.schema_contributes_clause.detail}")
    lines.append(f"KNOWLEDGE-TIED: {'MET' if qb.knowledge_tied else 'not met'}")
    for clause in qb.knowledge_tied_clauses:
        lines.append(f"  [{clause.verdict.upper():>8}] {clause.clause_text}")
        lines.append(f"           {clause.detail}")
    lines.append(f"MISLEAD overlay (fires independently): {'MET' if qb.mislead else 'not met'}")
    lines.append(f"  [{qb.mislead_clause.verdict.upper():>8}] {qb.mislead_clause.clause_text}")
    lines.append(f"           {qb.mislead_clause.detail}")
    lines.append(f"Q-B OVERALL: {qb.overall_with_overlay}")

    return "\n".join(lines)


def _default_stage2_arm_plan_path(repo_root: Path) -> Path:
    """Resolves ``configs/probes/g0-binding/a2t-s2b-flight.json``'s own
    ``stage2_arm_plan_path.path`` field, expanding ``$SPEECHRL_DATA_DIR``
    from the environment -- keeps the CLI thin (mission instruction) by
    letting the committed, REGISTERED config stay the single source of
    truth for WHICH already-flown Stage-2 attempt's mapping is reused."""

    import os

    config_path = repo_root / "configs" / "probes" / "g0-binding" / "a2t-s2b-flight.json"
    document = json.loads(config_path.read_text(encoding="utf-8"))
    raw = str(document["stage2_arm_plan_path"]["path"])
    return Path(os.path.expandvars(raw))


def _cli_parser():
    import argparse

    parser = argparse.ArgumentParser(
        prog="a2t-s2b-read",
        description=(
            "P-A2T Stage-2b follow-up probe pinned offline read suite: per-arm and per-tier "
            "EM-conversion/tool-selection-retention/slot-P-R-F1/empty-call/induced-substitution/"
            "parse-failure metrics and the mechanical Q-A (CONFIRMED-CUT/NOT-DEFAULTS/"
            "INCONCLUSIVE-A) / Q-B (SCHEMA-CONTRIBUTES/KNOWLEDGE-TIED/INCONCLUSIVE-B + MISLEAD "
            "overlay) evaluators. Model-free, read-only; never opens a model session."
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
        "a2t-s2b-flight.json config's own stage2_arm_plan_path, $SPEECHRL_DATA_DIR expanded)",
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
        report = build_a2t_s2b_report(
            args.attempt_dir,
            lock,
            root,
            repo_root=repo_root,
            headroom_path=headroom_path,
            stage2_arm_plan_path=stage2_arm_plan_path,
            split_role=args.split_role,
        )
    except (A2tS2bReadError, A2tS2ReadError) as error:  # module docstring note 7
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
    "INTERPRETIVE_WEIGHT_MIN_N",
    "Q_A_CONFIRMED_CUT_CONVERSION_MIN",
    "Q_A_CONFIRMED_CUT_INDUCED_MAX",
    "Q_A_NOT_DEFAULTS_INDUCED_MIN",
    "Q_B_KNOWLEDGE_TIED_CONVERSION_MAX",
    "Q_B_KNOWLEDGE_TIED_RETENTION_MIN",
    "Q_B_MISLEAD_RETENTION_MAX",
    "Q_B_SCHEMA_CONTRIBUTES_CONVERSION_MIN",
    "REPORT_SCHEMA",
    "RUN_ID",
    "A2tS2bReadError",
    "A2tS2bReadReport",
    "QAVerdict",
    "QBVerdict",
    "build_a2t_s2b_report",
    "evaluate_qa",
    "evaluate_qb",
    "main",
    "report_to_json",
    "render_report",
]
