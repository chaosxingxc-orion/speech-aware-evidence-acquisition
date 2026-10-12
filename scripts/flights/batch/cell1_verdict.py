"""Write cell CELL-1's verdict document from its read deliverables and close its records.

Modelled on ``scripts/flights/batch/prune_verdict.py`` (decision 58: reads by script), with the
two parsing defects that precedent carried repaired: the headline table reads the CI95 where the
driver actually writes it (``<metric>.speaker_clustered.ci95_pp``, not a non-existent ``ci95``
key), and the results-ledger paragraph reads ``left_pct`` / ``right_pct`` / ``delta_pp`` instead
of the ``left`` / ``right`` / ``delta`` keys that silently rendered as 0.00.

    python scripts/flights/batch/cell1_verdict.py --which arm \\
        --status "ADMITTED (...)" --factor "..." --reading "..." \\
        --commit <flight commit> --flown "2026-09-23T.. UTC"

``--which arm`` writes ``docs/results/<date>-slurp-stage3-delta-cell-r01-verdict.md``, reads the
twin analysis root beside the arm's when it exists, closes the CELL-1 exposure-ledger rows that
are still ``consumed = no`` (never the retired v1 / v2 smoke rows), appends the results-ledger
entry and appends the decision-99 outcome line.

``--which twin`` writes the twin READ note only
(``docs/results/<date>-slurp-stage3-delta-cell-twin-read.md``) and touches no record: the twin
decides attribution, not admission, so the family's records are closed exactly once, by the arm.

``--dry-run`` writes nothing at all and prints what it would have written; it is how the parsing
is proved against an existing analysis root of the same shape before the arm seals.

MODEL-FREE. Reads the analysis roots on the data root and the repository's own documents; counts
and metrics only, no utterance, gold or delivered text.
"""

from __future__ import annotations
import os

import argparse
import hashlib
import io
import json
import os
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

REPO_DEFAULT = Path(__file__).resolve().parents[3]
DATA = Path(
    (os.environ.get("SAEA_DATA_ROOT") or os.environ.get("SPEECHRL_DATA_DIR") or "SAEA_DATA_ROOT-UNSET")
)

#: 2026-09-24: one writer for every cell of the delta-cell family (CELL-1, CELL-2, later
#: CELL-1-GEPA); ``--cell`` selects the record. The CELL-1 values are the historical defaults.
CELLS = {
    "r01": {
        "name": "CELL-1",
        "run": "SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1",
        "arm_root": "SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1",
        "twin_root": "SAEA-SLURP-STAGE3-DELTA-CELL-TWIN-PAIRED-ANALYSIS-V1",
        "family_prefix": "SAEA-SLURP-STAGE3-DELTA-CELL-",
        "family_exclude": (
            "SAEA-SLURP-STAGE3-DELTA-CELL-R02-",
            "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-",
        ),
        "chain": "SAEA-Batch-Chain-Cell1",
        "read_sh": "cell1_read.sh",
        "verdict_slug": "slurp-stage3-delta-cell-r01-verdict.md",
        "twin_slug": "slurp-stage3-delta-cell-twin-read.md",
        "heading": "(Stage-3 S3-6 / S3-4s, owner decisions 83, 99, 101, 106)",
        "algorithm": "tfgrpo-semantic-advantage-v1",
        "decision_line": "Outcome of decision 99 (CELL-1, {date})",
    },
    "r02": {
        "name": "CELL-2",
        "run": "SAEA-SLURP-STAGE3-DELTA-CELL-R02-V1",
        "arm_root": "SAEA-SLURP-STAGE3-DELTA-CELL-R02-PAIRED-ANALYSIS-V1",
        "twin_root": "SAEA-SLURP-STAGE3-DELTA-CELL-R02-TWIN-PAIRED-ANALYSIS-V1",
        "family_prefix": "SAEA-SLURP-STAGE3-DELTA-CELL-R02-",
        "family_exclude": (),
        "chain": "SAEA-Batch-Chain-CELL2",
        "read_sh": "cell2_read.sh",
        "verdict_slug": "slurp-stage3-delta-cell-r02-verdict.md",
        "twin_slug": "slurp-stage3-delta-cell-r02-twin-read.md",
        "heading": (
            "(Stage-3 S3-6 ITERATION 2: the decision-83 retention of v1r; "
            "owner decisions 83, 99, 101, 106)"
        ),
        "algorithm": "tfgrpo-semantic-advantage-v1",
        "decision_line": "Outcome of decisions 83 and 99, iteration 2 (CELL-2, {date})",
    },
    "gepa": {
        "name": "CELL-1-GEPA",
        "run": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-V1",
        "arm_root": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-PAIRED-ANALYSIS-V1",
        "twin_root": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-TWIN-PAIRED-ANALYSIS-V1",
        "family_prefix": "SAEA-SLURP-STAGE3-DELTA-CELL-GEPA-R01-",
        "family_exclude": (),
        "chain": "SAEA-Batch-Chain-GEPACELL",
        "read_sh": "gepacell_read.sh",
        "verdict_slug": "slurp-stage3-delta-cell-gepa-r01-verdict.md",
        "twin_slug": "slurp-stage3-delta-cell-gepa-r01-twin-read.md",
        "heading": (
            "(Stage-3 S3-6, the GEPA family arm: the locked v2.0 plan plus the released "
            "448-value stage3-deltas-gepa-v1 store; owner decisions 83, 99, 101, 106)"
        ),
        "algorithm": "gepa-reflective-pareto-v1",
        "decision_line": "Outcome of decision 101 for the GEPA family (CELL-1-GEPA, {date})",
    },
}
CELL = CELLS["r01"]  # rebound by main() from --cell

LEDGER = "docs/exposure-ledger.md"
RESULTS_LEDGER = "docs/results/stage2-results-ledger.md"
DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"

#: Every exposure-ledger row of this cell's family carries this prefix.
FAMILY_PREFIX = "SAEA-SLURP-STAGE3-DELTA-CELL-"  # superseded by CELL["family_prefix"]
#: The RETIRED smoke registrations. They were closed when they were retired and this read must
#: never touch them again, whatever their consumed column says.
RETIRED_ROWS = frozenset(
    {
        "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V1",
        "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-FIT-V1",
        "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2",
        "SAEA-SLURP-STAGE3-DELTA-CELL-SMOKE-4-V2-FIT-V1",
    }
)

#: The registered decision rule, restated verbatim in the verdict document (owner decision 99,
#: preregistration section 3; delta = CELL-1 minus the sealed PLAN arm, in percentage points).
DECISION_RULE = [
    "**ADMITTED** -- the CI95 lower bound of the paired **official pooled SLU-F1** delta is "
    "**above zero** and the CI95 lower bound of the paired **intent** delta exceeds "
    "**-0.9943**. A gain is proven, not merely non-inferior.",
    "**NEUTRAL** -- both guards non-inferior (SLU lower bound above -1.2485, intent lower bound "
    "above -0.9943) without a proven SLU gain.",
    "**HARMFUL** -- a **measured** loss on either guard (owner decision 25, Method B: a CI95 "
    "upper bound below zero, or a point estimate beyond the margin). Width alone is NEUTRAL, "
    "never HARMFUL.",
    "**TWIN = attribution, never admission.** A gain the twin reproduces within the plan's own "
    "null is **form** -- the store's shape and token volume -- not content, and the verdict says "
    "so and claims no content effect. A gain the twin does not reproduce is attributed to the "
    "deltas' content, with the twin delta reported beside it.",
    "**Replication** -- an ADMITTED result is replicated on the **same roster** before any DEV, "
    "Fold B or test read. No such read is authorised by this package.",
]

#: The four launch failures of this cell, and what each metered. Fixed facts from the
#: preregistration's three addenda and the arm's own recovery addendum.
LAUNCH_FAILURES = [
    ("smoke v1, first launch", 0,
     "refused before any contact in core.flight.runtime._merge_unconditional_first_phase "
     "(an unconditional store route repeats a seeded value id); the attempt opened and metered "
     "nothing"),
    ("smoke v1, recovery", 4,
     "the one allowed recovery re-registration was flown and failed; the v1 smoke run id was "
     "retired"),
    ("smoke v2", 12,
     "died at the openJiuwen vertex reviewer_0_input ('acquire must introduce at least one new "
     "value or facet'): a node-filtered candidate-bound route that selected NOTHING still "
     "returned a supply. Fixed in rails.knowledge_stores._stage3_delta_local_supply, which now "
     "supplies nothing and receipts the skip"),
    ("arm, first attempt", 304,
     "aborted at solver_0_input on a Perception answer carrying duplicate candidate intent ids "
     "('candidate intent_ids must be unique and ordered'); 73 of 75 rows completed, no output "
     "was sealed and no score was produced. Fixed by deriving both readers' parameters from "
     "rails.candidate_semantic_supply.candidate_state_read_parameters"),
]

TWIN_CAVEAT = (
    "The derangement twin is a genuine FORM control on **363 of 379** rows (95.8 %): 16 of the "
    "379 rows landed on a facet set equal to their own by arithmetic, because store revision "
    "v1r's vocabulary is 39 distinct intents over 379 rows, and the builder refuses only a twin "
    "that moved nothing at all. The twin therefore bounds the form contribution slightly from "
    "below; it is reported, not claimed away."
)
COMPACTION_CAVEAT = (
    "The registered worst-case prompt-fit bound puts the **Solver** phase at `COMPACT_REQUIRED` "
    "by 317 tokens under this cell's added block (preregistration section 5), so a non-zero "
    "compacted-row count is expected and is a caveat on the frontier row's token basis. An "
    "abstention caused by compaction would be a failure, not a caveat."
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(root: Path, name: str, *, required: bool = True):
    path = root / name
    if not path.exists():
        if required:
            raise SystemExit(f"missing analysis deliverable: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_root(root: Path) -> dict:
    """Every deliverable a CELL-1-shaped read leaves in its analysis root."""
    if not root.exists():
        raise SystemExit(f"analysis root does not exist: {root}")
    contrasts = _load(root, "score-contrasts.json")
    return {
        "root": root,
        "score_contrasts": contrasts,
        "score_contrasts_sha256": sha(root / "score-contrasts.json"),
        "efficiency": _load(root, "efficiency.json"),
        "frontier": _load(root, "frontier.json"),
        "structural": _load(root, "structural.json"),
        "per_scenario": _load(root, "per-scenario-tables.json"),
        "delta_consumption": _load(root, "delta-consumption.json", required=False),
    }


# --------------------------------------------------------------------------
# Parsing the driver's own shapes
# --------------------------------------------------------------------------

def metric_block(contrasts: dict, group: str, name: str, comparison="arm_vs_comparator"):
    """One metric of one comparison, with the CI where ``interval_block`` writes it."""
    entry = ((contrasts.get("comparisons") or {}).get(comparison) or {}).get(group, {}).get(name)
    if not isinstance(entry, dict):
        return None
    speaker = entry.get("speaker_clustered") or {}
    scenario = entry.get("scenario_stratified") or {}
    return {
        "metric": name,
        "left_pct": entry.get("left_pct"),
        "right_pct": entry.get("right_pct"),
        "delta_pp": entry.get("delta_pp"),
        "equal_scenario_delta_pp": entry.get("equal_scenario_delta_pp"),
        "ci95_pp": speaker.get("ci95_pp"),
        "ci90_pp": speaker.get("ci90_pp"),
        "scenario_ci90_pp": scenario.get("ci90_pp"),
        "saves": entry.get("saves"),
        "harms": entry.get("harms"),
        "ties": entry.get("ties"),
        "mcnemar_p": entry.get("sign_test_p"),
    }


def headline_metrics(contrasts: dict) -> list:
    """The decision rule's two guards first, then the companions the recipe asks for."""
    ordered = [
        ("pooled_micro", "slu_f1_micro"),
        ("per_row", "scenario_action_exact"),
        ("pooled_micro", "span_f1_micro"),
        ("per_row", "scenario_exact"),
        ("per_row", "action_exact"),
        ("per_row", "slu_f1_f1"),
        ("per_row", "slot_f1_exact_f1"),
    ]
    blocks = []
    for group, name in ordered:
        block = metric_block(contrasts, group, name)
        if block:
            blocks.append(block)
    return blocks


def _num(value, digits=2, dash="--"):
    if value is None:
        return dash
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _signed(value, digits=2, dash="--"):
    if value is None:
        return dash
    try:
        return f"{float(value):+.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


def _count(value):
    """A disposition block is either {"count": n, ...} or the bare count."""
    if isinstance(value, dict):
        return value.get("count")
    return value


def _ci(pair, digits=2):
    if not isinstance(pair, (list, tuple)) or len(pair) != 2:
        return "--"
    return f"[{float(pair[0]):+.{digits}f}, {float(pair[1]):+.{digits}f}]"


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def render(args, arm: dict, twin, note_path: str) -> str:
    contrasts = arm["score_contrasts"]
    decision = contrasts.get("decision") or {}
    efficiency = (arm["efficiency"] or {}).get("headline") or {}
    structural = arm["structural"] or {}
    trajectory = (structural.get("trajectory") or {}).get("arm") or {}
    comparator_trajectory = (structural.get("trajectory") or {}).get("comparator") or {}
    dispositions = (structural.get("dispositions") or {}).get("arm") or {}

    short = CELL["name"] if args.which == "arm" else f"{CELL['name']} twin"
    lines = []
    if args.which == "arm":
        lines.append(
            f"# Cell {CELL['name']} verdict: {args.factor} "
            f"{CELL['heading']}"
        )
    else:
        lines.append(
            f"# Cell {CELL['name']} twin read: {args.factor} "
            "(the derangement form control; attribution, never admission)"
        )
    lines.append("")
    lines.append(
        f"Read {args.date} by the coordinator (Fable 5.1) with "
        f"`scripts/analysis/plan_cell_read.py` via `scripts/flights/batch/{CELL['read_sh']} "
        f"{args.which}` (analysis root `$SPEECHRL_DATA_DIR/analysis/{arm['root'].name}`, "
        f"score-contrasts sha256 `{arm['score_contrasts_sha256']}`), and the per-node "
        "delta-consumption table with "
        "`scripts/analysis/stage3_delta_consumption_read.py`. Comparator = the sealed PLAN arm "
        "at the plan's own null (h_SLU 1.2485 / h_intent 0.9943). Model-free: zero model / "
        "tokenizer / encoder / server contacts. Development numbers (decisions 28, 86)."
    )
    lines.append("")

    # 1. Verdict -----------------------------------------------------------
    lines.append("## 1. Verdict")
    lines.append("")
    lines.append("| item | result |")
    lines.append("| --- | --- |")
    lines.append(f"| status | **{args.status}** |")
    lines.append(f"| driver status | {decision.get('status', '--')} |")
    lines.append(f"| reading | {args.reading} |")
    lines.append(
        "| cost | contacts / row "
        f"{_num(efficiency.get('contacts_per_row'), 3)} vs "
        f"{_num(efficiency.get('contacts_per_row_comparator'), 3)}; GPU-h / 1,080 "
        f"{_num(efficiency.get('gpu_hours_per_1080'), 3)} vs "
        f"{_num(efficiency.get('gpu_hours_per_1080_comparator'), 3)}; contacts / min "
        f"{_num(efficiency.get('contacts_per_minute'), 1)} vs "
        f"{_num(efficiency.get('contacts_per_minute_comparator'), 1)}; prefilled tokens / row "
        f"{_num(efficiency.get('prefilled_tokens_per_row'), 0)} vs "
        f"{_num(efficiency.get('prefilled_tokens_per_row_comparator'), 0)}; cost lower than the "
        f"base: {efficiency.get('cost_is_lower_than_the_base')} |"
    )
    lines.append(
        f"| trajectory | contacts {trajectory.get('contacts')} "
        f"({_num(trajectory.get('contacts_per_row'), 3)} / row; histogram "
        f"{trajectory.get('contacts_per_row_histogram')}); comparator "
        f"{comparator_trajectory.get('contacts')} "
        f"({_num(comparator_trajectory.get('contacts_per_row'), 3)} / row; "
        f"{comparator_trajectory.get('contacts_per_row_histogram')}) |"
    )
    lines.append(
        "| dispositions | finite stops "
        f"{_count(dispositions.get('finite_stops'))}, react exhaustion "
        f"{_count(dispositions.get('react_exhaustion_rows'))}, planner-action-illegal "
        f"{_count(dispositions.get('planner_action_illegal'))}, other terminal "
        f"{_count(dispositions.get('other_terminal_dispositions'))} |"
    )
    lines.append("")
    lines.append("### 1a. The decision rule, as registered (owner decision 99, the TRAIN lock)")
    lines.append("")
    lines.append(
        f"Delta = {CELL['name']} minus the sealed PLAN arm "
        "(`SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`), in percentage points."
    )
    lines.append("")
    for clause in DECISION_RULE:
        lines.append(f"- {clause}")
    lines.append("")
    guards = decision.get("guards") or {}
    if guards:
        lines.append("| guard | arm | comparator | delta pp | CI95 | margin | decides |")
        lines.append("| --- | ---: | ---: | ---: | --- | ---: | --- |")
        for key, label in (
            ("official_pooled_slu_f1", "official pooled SLU-F1"),
            ("intent_accuracy", "intent (joint scenario+action)"),
        ):
            guard = guards.get(key)
            if not isinstance(guard, dict):
                continue
            decides = []
            if guard.get("ci95_lower_exceeds_minus_h"):
                decides.append("non-inferior")
            if guard.get("ci95_upper_below_zero"):
                decides.append("measured loss")
            if guard.get("point_below_minus_h"):
                decides.append("point beyond the margin")
            ci95 = guard.get("ci95_pp")
            gained = isinstance(ci95, (list, tuple)) and len(ci95) == 2 and float(ci95[0]) > 0
            if gained:
                decides.append("proven gain")
            lines.append(
                f"| {label} | {_num(guard.get('arm_pct'))} "
                f"| {_num(guard.get('comparator_pct'))} | {_signed(guard.get('delta_pp'))} "
                f"| {_ci(ci95)} | {_num(guard.get('margin_h_pp'), 4)} "
                f"| {', '.join(decides) or 'width only'} |"
            )
        lines.append("")

    # 2. Headline ----------------------------------------------------------
    lines.append(
        f"## 2. Headline contrasts ({short} minus PLAN, paired, "
        f"{contrasts.get('recipe_id', '')})"
    )
    lines.append("")
    lines.append(
        "| metric | PLAN | arm | delta pp | CI95 (speaker) | CI90 (speaker) "
        "| CI90 (scenario-stratified) | equal-scenario delta |"
    )
    lines.append("| --- | ---: | ---: | ---: | --- | --- | --- | ---: |")
    for block in headline_metrics(contrasts):
        lines.append(
            f"| {block['metric']} | {_num(block['left_pct'])} | {_num(block['right_pct'])} "
            f"| {_signed(block['delta_pp'])} | {_ci(block['ci95_pp'])} "
            f"| {_ci(block['ci90_pp'])} | {_ci(block['scenario_ci90_pp'])} "
            f"| {_signed(block['equal_scenario_delta_pp'])} |"
        )
    lines.append("")
    saves_rows = [
        block for block in headline_metrics(contrasts) if block.get("saves") is not None
    ]
    if saves_rows:
        lines.append("| metric | saves | harms | ties | two-sided McNemar p |")
        lines.append("| --- | ---: | ---: | ---: | ---: |")
        for block in saves_rows:
            lines.append(
                f"| {block['metric']} | {block['saves']} | {block['harms']} | {block['ties']} "
                f"| {_num(block['mcnemar_p'], 4)} |"
            )
        lines.append("")
    lines.append(
        "Lock comparison (reported, never a gate): see `lock-comparison.json`; projection-v3 and "
        "TRAIN-symmetric companions are in `score-contrasts.json`."
    )
    lines.append("")

    # 3. Twin --------------------------------------------------------------
    if args.which == "arm":
        lines.append("## 3. The derangement twin (form control) and the content attribution")
        lines.append("")
        if twin is None:
            lines.append(
                "The twin analysis root is not present: the twin read has not been run, so no "
                "attribution is claimed here. A gain in section 2 is UNATTRIBUTED until the twin "
                "read lands."
            )
            lines.append("")
        else:
            twin_contrasts = twin["score_contrasts"]
            lines.append(
                f"Twin analysis root `$SPEECHRL_DATA_DIR/analysis/{twin['root'].name}`, "
                f"score-contrasts sha256 `{twin['score_contrasts_sha256']}`. Same comparator, "
                "same margins, same estimator, same seed: the twin read is the arm read with one "
                "input changed."
            )
            lines.append("")
            lines.append(
                "| metric | arm delta pp | arm CI95 | twin delta pp | twin CI95 "
                "| arm minus twin pp |"
            )
            lines.append("| --- | ---: | --- | ---: | --- | ---: |")
            for group, name in (
                ("pooled_micro", "slu_f1_micro"),
                ("per_row", "scenario_action_exact"),
                ("pooled_micro", "span_f1_micro"),
            ):
                arm_block = metric_block(contrasts, group, name)
                twin_block = metric_block(twin_contrasts, group, name)
                if not arm_block or not twin_block:
                    continue
                difference = None
                if arm_block["delta_pp"] is not None and twin_block["delta_pp"] is not None:
                    difference = float(arm_block["delta_pp"]) - float(twin_block["delta_pp"])
                lines.append(
                    f"| {name} | {_signed(arm_block['delta_pp'])} | {_ci(arm_block['ci95_pp'])} "
                    f"| {_signed(twin_block['delta_pp'])} | {_ci(twin_block['ci95_pp'])} "
                    f"| {_signed(difference)} |"
                )
            lines.append("")
            lines.append(
                "**The arm-minus-twin column is DESCRIPTIVE.** It is the difference of two "
                "point estimates, each against the same sealed PLAN arm; no interval is computed "
                "for it and no test is run on it. It bounds how much of the arm's movement the "
                "store's shape and token volume alone can account for. The twin decides "
                "attribution, never admission (decision 99)."
            )
            lines.append("")
        lines.append(f"{TWIN_CAVEAT}")
        lines.append("")

    # 4. Per-scenario ------------------------------------------------------
    lines.append(
        "## 4. Per scenario (natural mixture and equal-scenario weighting; diagnostics, never "
        "gates)"
    )
    lines.append("")
    per_scenario = ((arm["per_scenario"] or {}).get("natural_mixture_and_equal_scenario") or {})
    table = per_scenario.get("arm_vs_comparator") or {}
    for key, value in table.items():
        if isinstance(value, dict) and value and all(
            isinstance(item, dict) for item in value.values()
        ):
            columns = sorted(
                {
                    column
                    for item in value.values()
                    for column, cell in item.items()
                    if isinstance(cell, (int, float))
                }
            )[:8]
            if not columns:
                continue
            lines.append(f"### {key}")
            lines.append("")
            lines.append("| scenario | " + " | ".join(columns) + " |")
            lines.append("| --- |" + " ---: |" * len(columns))
            for scenario, item in sorted(value.items()):
                cells = " | ".join(
                    _num(item.get(column), 3) if isinstance(item.get(column), float)
                    else str(item.get(column, ""))
                    for column in columns
                )
                lines.append(f"| {scenario} | {cells} |")
            lines.append("")
        elif isinstance(value, (int, float)):
            lines.append(f"- {key}: {value}")
    band = (contrasts.get("band") or {}).get("arm_vs_comparator") or {}
    lines.append(
        f"Intent band: decision-17 flagged scenarios = "
        f"{band.get('decision_17_flagged_scenarios')}; scenarios losing beyond the band = "
        f"{band.get('scenarios_losing_beyond_the_band')}."
    )
    lines.append("")

    # 5. Frontier ----------------------------------------------------------
    lines.append("## 5. Frontier row (decision 75)")
    lines.append("")
    lines.append(
        "| cell | official SLU | official intent | GPU-h / 1,080 | contacts / row "
        "| prefilled tok / row | on GPU-h frontier | on token frontier |"
    )
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    for label, block in ((CELL["name"], arm), (f"{CELL['name']} twin", twin)):
        if block is None:
            continue
        row = (block["frontier"] or {}).get("row") or {}
        if not row:
            continue
        lines.append(
            f"| {label} | {_num(row.get('official_slu'))} | {_num(row.get('official_intent'))} "
            f"| {_num(row.get('gpu_hours_per_1080'), 4)} "
            f"| {_num(row.get('contacts_per_row'), 3)} "
            f"| {_num(row.get('prefilled_tokens_per_row'), 1)} "
            f"| {(block['frontier'] or {}).get('plan_is_on_the_gpu_hour_frontier')} "
            f"| {(block['frontier'] or {}).get('plan_is_on_the_prefilled_token_frontier')} |"
        )
    lines.append("")

    # 6. Delta consumption -------------------------------------------------
    lines.append("## 6. Per-node delta consumption (item S3-4s)")
    lines.append("")
    consumption = arm["delta_consumption"]
    if consumption is None:
        lines.append(
            "`delta-consumption.json` is not present in the analysis root: run "
            "`scripts/analysis/stage3_delta_consumption_read.py` against the sealed arm before "
            "this verdict is final. The table is a PRIMARY deliverable whatever the verdict "
            "(preregistration section 3) -- it is what decides store version 2."
        )
        lines.append("")
    else:
        block = consumption["consumption"]
        summary = block["summary"]
        lines.append(
            f"Store `{consumption['store_id']}`, release sha256 "
            f"`{consumption['store']['store_release_sha256']}`, snapshot "
            f"`{consumption['store']['store_snapshot_sha256']}`. Rows "
            f"{summary['rows_total']}; rows that received at least one delta "
            f"{summary['rows_supplied_any_node']}; items supplied "
            f"{summary['items_supplied_total']}; distinct value ids "
            f"{summary['distinct_value_ids_supplied']}; skip events "
            f"{summary['skip_events']}; projection events "
            f"{summary['projection_events']}; inert routes "
            f"{summary['inert_routes'] or 'none'}."
        )
        lines.append("")
        lines.append(
            "| node | cap | rows supplied | share | items | items / supplied row | at full cap "
            "| distinct value ids | skip events | rows skipped |"
        )
        lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
        for node in block["node_order"]:
            entry = block["per_node"][node]
            skips = entry.get("skips") or {}
            lines.append(
                f"| {node} | {_num(entry.get('cap'), 0)} | {entry['rows_supplied']} "
                f"| {_num(entry.get('rows_supplied_share'), 3)} "
                f"| {entry['items_supplied_total']} "
                f"| {_num(entry.get('items_per_supplied_row_mean'), 3)} "
                f"| {_num(entry.get('rows_at_full_cap'), 0)} | {entry['distinct_value_ids']} "
                f"| {skips.get('skip_events', 0)} | {skips.get('rows_skipped', 0)} |"
            )
        lines.append("")
        outcomes = [
            (node, block["per_node"][node].get("outcome_on_supplied_rows"))
            for node in block["node_order"]
        ]
        if any(entry for _, entry in outcomes):
            lines.append(
                "| node | rows supplied | SLU saves | SLU harms | SLU neutral "
                "| SLU mean delta pp | intent saves | intent harms | intent neutral "
                "| intent mean delta pp |"
            )
            lines.append(
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"
            )
            for node, entry in outcomes:
                if not entry:
                    continue
                slu = entry["slu_f1"]
                intent = entry["intent"]
                lines.append(
                    f"| {node} | {entry['rows_joined']} | {slu['saves']} | {slu['harms']} "
                    f"| {slu['neutral']} | {_signed(slu['mean_delta_pp'], 3)} "
                    f"| {intent['saves']} | {intent['harms']} | {intent['neutral']} "
                    f"| {_signed(intent['mean_delta_pp'], 3)} |"
                )
            lines.append("")
        if twin is not None and twin.get("delta_consumption"):
            twin_block = twin["delta_consumption"]["consumption"]
            lines.append("### 6a. Arm versus twin supplied volume")
            lines.append("")
            lines.append(
                "| node | arm rows supplied | twin rows supplied | arm items | twin items "
                "| arm distinct value ids | twin distinct value ids |"
            )
            lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")
            for node in block["node_order"]:
                arm_entry = block["per_node"].get(node) or {}
                twin_entry = (twin_block["per_node"] or {}).get(node) or {}
                lines.append(
                    f"| {node} | {arm_entry.get('rows_supplied')} "
                    f"| {twin_entry.get('rows_supplied')} "
                    f"| {arm_entry.get('items_supplied_total')} "
                    f"| {twin_entry.get('items_supplied_total')} "
                    f"| {arm_entry.get('distinct_value_ids')} "
                    f"| {twin_entry.get('distinct_value_ids')} |"
                )
            lines.append("")
            lines.append(
                "The derangement holds the store's TOTAL token count, not the SUPPLIED token "
                "count: a twin that supplies materially more or less than the arm is a weaker "
                "form control, and this table is where that is read rather than assumed."
            )
            lines.append("")
        lines.append(
            "The full per-value-id and per-scenario tables are in `delta-consumption.json` and "
            "`delta-consumption.md` in the analysis root. Value ids, node targets and counts "
            "only; never statement text."
        )
        lines.append("")

    # 7. Cost --------------------------------------------------------------
    lines.append("## 7. Cost")
    lines.append("")
    decomposition = efficiency.get("gpu_hours_decomposition") or {}
    lines.append("| item | arm | comparator (PLAN) |")
    lines.append("| --- | ---: | ---: |")
    for key, label, digits in (
        ("contacts_per_row", "contacts / row", 3),
        ("contacts_per_minute", "contacts / min", 1),
        ("prefilled_tokens_per_row", "prefilled tokens / row", 0),
        ("gpu_hours_per_1080", "GPU-h / 1,080 rows", 4),
        ("cache_hit_share", "cache hit share", 4),
        ("wall_seconds", "generation wall seconds", 1),
    ):
        comparator = efficiency.get(key + "_comparator")
        if comparator is None:
            comparator = decomposition.get("comparator_" + key)
        lines.append(
            f"| {label} | {_num(efficiency.get(key), digits)} "
            f"| {_num(comparator, digits)} |"
        )
    lines.append("")

    # 8. Caveats -----------------------------------------------------------
    lines.append("## 8. Caveats")
    lines.append("")
    if args.which == "arm":
        lines.append(f"1. {TWIN_CAVEAT}")
    else:
        lines.append(f"1. {TWIN_CAVEAT}")
    compaction = (structural.get("context_fit_compaction") or {}).get("arm") or {}
    lines.append(
        f"2. {COMPACTION_CAVEAT} Measured on this flight: contacts compacted "
        f"{compaction.get('contacts_compacted')}, one receipt per row "
        f"{compaction.get('one_receipt_per_row')}, receipt dispositions "
        f"{compaction.get('flight_receipt_dispositions')}."
    )
    spent = sum(calls for _, calls, _ in LAUNCH_FAILURES)
    lines.append(
        f"3. **Four launch failures** preceded this flight, metering {spent} contacts in total "
        "on retired attempts. None of them sealed an output or produced a score, so none of them "
        "contributes evidence beyond the harness; the plan budget is run-cumulative across every "
        "attempt of a run id, so those contacts count against this cell's registered ceiling."
    )
    lines.append("")
    lines.append("| attempt | metered contacts | what failed |")
    lines.append("| --- | ---: | --- |")
    for label, calls, why in LAUNCH_FAILURES:
        lines.append(f"| {label} | {calls} | {why} |")
    lines.append("")
    lines.append(
        "4. Development numbers only (owner decisions 28, 86): TRAIN Fold A is a development "
        "roster and no test, Fold B or DEV read is authorised by this verdict. An ADMITTED "
        "result is replicated on the SAME roster before any such read."
    )
    lines.append("")

    # 9. Records -----------------------------------------------------------
    lines.append("## 9. Records")
    lines.append("")
    if args.which == "arm":
        lines.append(
            f"Exposure-ledger rows closed (the `{FAMILY_PREFIX}*` family still open, never the "
            f"retired v1 / v2 smoke rows), flight commit {args.commit}, {args.flown}; "
            "results-ledger entry; decision-99 outcome appended. Stage-3 algorithm label "
            "(owner decision 101): `tfgrpo-semantic-advantage-v1`, operators update + "
            "context_application."
        )
    else:
        lines.append(
            "No record is closed by the twin read: the twin decides attribution, not admission, "
            "and the family's exposure-ledger rows, results-ledger entry and decision-99 outcome "
            "are written exactly once, by the arm verdict."
        )
    lines.append("")
    lines.append(f"Read: `{note_path}`.")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Record closure
# --------------------------------------------------------------------------

def close_ledger_rows(repo: Path, args, arm: dict, note_path: str, *, dry_run: bool):
    """Close every still-open row of this cell's family; never a retired row."""
    path = repo / LEDGER
    text = io.open(path, encoding="utf-8", newline="").read()
    lines = text.split("\n")
    structural = arm["structural"] or {}
    trajectory = (structural.get("trajectory") or {}).get("arm") or {}
    efficiency = (arm["efficiency"] or {}).get("headline") or {}
    closed = []
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        cells = line.split("|")
        if len(cells) < 16:
            continue
        run_id = cells[2].strip()
        if not run_id.startswith(CELL["family_prefix"]) or run_id in RETIRED_ROWS:
            continue
        if any(run_id.startswith(x) for x in CELL["family_exclude"]):
            continue
        if cells[9].strip() != "no":
            continue
        if run_id.endswith("-FIT-V1"):
            what = "CONSUMED (fit, within cap)"
        elif "PAIRED-ANALYSIS" in run_id:
            what = "CONSUMED (model-free read; zero model / tokenizer / encoder / server contacts)"
        elif "SMOKE" in run_id:
            what = "SEALED (four-row smoke, structural PASS)"
        elif "TWIN" in run_id:
            what = (
                "SEALED: the derangement form control, read with the same comparator, margins, "
                "estimator and seed as the arm; attribution only"
            )
        else:
            what = (
                f"SEALED: {trajectory.get('contacts')} contacts "
                f"({_num(trajectory.get('contacts_per_row'), 2)} per row), "
                f"{_num(efficiency.get('gpu_hours_per_1080'), 2)} GPU-h, manifest COMPLETED, "
                f"scored once; {args.status}"
            )
        cells[9] = " yes "
        cells[15] = (
            f" {what}; flight commit {args.commit} ({CELL['chain']}, {args.flown}). "
            f"Read: `{note_path}`." + cells[15]
        )
        lines[index] = "|".join(cells)
        closed.append(run_id)
    if args.expect_rows is not None and len(closed) != args.expect_rows:
        raise SystemExit(
            f"expected to close {args.expect_rows} ledger row(s), matched {len(closed)}: {closed}"
        )
    if not closed:
        raise SystemExit(f"no open {CELL['name']} exposure-ledger row matched; refusing a silent no-op")
    if not dry_run:
        io.open(path, "w", encoding="utf-8", newline="").write("\n".join(lines))
    return closed


def results_ledger_entry(args, arm: dict, note_path: str) -> str:
    contrasts = arm["score_contrasts"]
    structural = arm["structural"] or {}
    trajectory = (structural.get("trajectory") or {}).get("arm") or {}
    efficiency = (arm["efficiency"] or {}).get("headline") or {}
    slu = metric_block(contrasts, "pooled_micro", "slu_f1_micro") or {}
    intent = metric_block(contrasts, "per_row", "scenario_action_exact") or {}
    return (
        f"\n\n## {args.date}: cell {CELL['name']}, {args.factor} (Fable 5.1)\n\n"
        f"Run {CELL['run']} ({trajectory.get('contacts')} contacts = "
        f"{_num(trajectory.get('contacts_per_row'), 2)} per row, "
        f"{_num(efficiency.get('gpu_hours_per_1080'), 2)} GPU-h, FINALIZED at flight commit "
        f"{args.commit}, {CELL['chain']}) against the sealed PLAN arm on the same 1,080 "
        "rows at the plan's own null (h_SLU 1.2485 / h_intent 0.9943): official pooled SLU-F1 "
        f"{_num(slu.get('left_pct'))} -> {_num(slu.get('right_pct'))}, "
        f"**{_signed(slu.get('delta_pp'))} pp CI95 {_ci(slu.get('ci95_pp'))}**; intent "
        f"{_num(intent.get('left_pct'))} -> {_num(intent.get('right_pct'))}, "
        f"**{_signed(intent.get('delta_pp'))} pp CI95 {_ci(intent.get('ci95_pp'))}**: "
        f"**{args.status}**. {args.reading} Stage-3 algorithm label "
        f"{CELL['algorithm']} (decision 101). Read: `{note_path}`.\n"
    )


def decision_outcome(args, note_path: str) -> str:
    return (
        f"\n\n{CELL['decision_line'].format(date=args.date)}: {args.status}. {args.reading} "
        f"Read: `{note_path}`.\n"
    )


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--which", required=True, choices=("arm", "twin"))
    parser.add_argument("--cell", default="r01", choices=sorted(CELLS),
                        help="which delta cell's records to write (r01 = CELL-1, r02 = CELL-2, gepa = CELL-1-GEPA)")
    parser.add_argument("--status", required=True)
    parser.add_argument("--factor", required=True)
    parser.add_argument("--reading", required=True)
    parser.add_argument("--commit", default="unpinned")
    parser.add_argument("--flown", required=True)
    parser.add_argument("--date", default=date.today().isoformat())
    parser.add_argument("--repo", default=str(REPO_DEFAULT))
    parser.add_argument("--arm-root", default=None, help="override the arm analysis root")
    parser.add_argument("--twin-root", default=None, help="override the twin analysis root")
    parser.add_argument("--expect-rows", type=int, default=None)
    parser.add_argument("--no-twin", action="store_true", help="ignore the twin analysis root")
    parser.add_argument("--dry-run", action="store_true", help="write nothing; print instead")
    args = parser.parse_args(argv)
    global CELL
    CELL = CELLS[args.cell]

    repo = Path(args.repo)
    arm_root = Path(
        args.arm_root
        or (DATA / "analysis" / (CELL["arm_root"] if args.which == "arm" else CELL["twin_root"]))
    )
    arm = load_root(arm_root)
    twin = None
    if args.which == "arm" and not args.no_twin:
        twin_root = Path(args.twin_root or (DATA / "analysis" / CELL["twin_root"]))
        if twin_root.exists() and twin_root != arm_root:
            twin = load_root(twin_root)

    slug = (
        f"{args.date}-{CELL['verdict_slug']}"
        if args.which == "arm"
        else f"{args.date}-{CELL['twin_slug']}"
    )
    note_path = f"docs/results/{slug}"
    document = render(args, arm, twin, note_path)

    if args.dry_run:
        print(document)
        print("=" * 72)
        print(f"DRY RUN -- would write {repo / note_path} ({len(document)} chars)")
        if args.which == "arm":
            closed = close_ledger_rows(repo, args, arm, note_path, dry_run=True)
            print(f"DRY RUN -- would close {len(closed)} ledger row(s): {closed}")
            print(f"DRY RUN -- would append to {RESULTS_LEDGER}:")
            print(results_ledger_entry(args, arm, note_path))
            print(f"DRY RUN -- would append to {DECISIONS}:")
            print(decision_outcome(args, note_path))
        else:
            print("DRY RUN -- the twin read closes no record.")
        return 0

    target = repo / note_path
    target.parent.mkdir(parents=True, exist_ok=True)
    io.open(target, "w", encoding="utf-8", newline="\n").write(document)
    print("written", note_path)
    if args.which != "arm":
        print("twin read: no record closed (attribution, never admission)")
        return 0

    closed = close_ledger_rows(repo, args, arm, note_path, dry_run=False)
    print("ledger rows closed", len(closed), closed)

    results_path = repo / RESULTS_LEDGER
    body = io.open(results_path, encoding="utf-8", newline="").read().rstrip("\n")
    body += results_ledger_entry(args, arm, note_path)
    io.open(results_path, "w", encoding="utf-8", newline="").write(body + "\n")
    print("results ledger entry added")

    decisions_path = repo / DECISIONS
    body = io.open(decisions_path, encoding="utf-8", newline="").read().rstrip("\n")
    body += decision_outcome(args, note_path)
    io.open(decisions_path, "w", encoding="utf-8", newline="").write(body)
    print("decision-99 outcome appended")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
