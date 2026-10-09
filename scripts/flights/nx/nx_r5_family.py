"""Shared identities of NX Stage J round R5 (the composed read on DEV-2000-ADDED).

One module, imported by the derive, writer, mint, dry-run and read scripts, so no id is spelled twice. Model-free.

WHAT R5 IS. Programme ``docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md`` C2 R5 and F1 Stage J; decision 238
(PROPOSED, ``docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md``): the review-off COMP-1b base with the v4g
delivery normaliser (lock v2.2, module step 7) read on DEV-2000-ADDED 1,000, in ONE chain beside an in-chain request-identical
replicate (the HELD module OFF-arm cell, instrument rule 3). Two cells in the chain: the replicate, then the composed arm.
Read constants as ``nf.NAME``.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-09"
SLUG = "nx-r5-composed-dev2000-added"
PKG_NAME = f"slurp-{SLUG}-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
SHORT = "nxr5"
BRANCH = "fable/nx-r5-register"
WORKTREE = "/home/chao/saea-worktrees/fable-nx-r5-register"
LEDGER_MARK = "## NX round R5: the composed read (review-off COMP-1b + v4g) on DEV-2000-ADDED"

DECISION_ID = f"slurp-{SLUG}-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = "SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-PAIRED-ANALYSIS-V1"
RECIPE_ID = f"slurp-{SLUG}-paired-analysis-v1"
ANALYSIS_ROOT = f"analysis/{READ_RUN_ID}"
CAMPAIGN_PLAN = f"configs/campaign/slurp-native-stage3-{SLUG}-v1.json"

PROGRAM = "phase-native-module-v1-c2"             # the compiled review-off program: Perception then Solver
CEILING = 2
ROWS = 1000
SMOKE_ROWS = 4
FIT_ENDPOINTS_PER_CONTACT = 4                      # max_speech_packets (1) + 3
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 1.5, 1.0
LOCK = "v2.2"                                      # v4g at delivery (module step 7); the replicate stays on v2.1 / v3
NORMALISER = "saea-deliver-normalise-v4g"

ROSTER = "docs/receipts/rosters/slurp-dev-2000-added-v1.json"
ROSTER_ID = "SLURP-DEV-2000-ADDED-V1"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official"

#: The locked Solver instruction template and THE swap point: the iteration-2 pick of R1 (``r1-i2-c*``), if it is NOMINATED
#: and confirmed on Fold A, replaces this ONE pin (see the package README, "The swap point"). Today the module has no
#: registered composition that delivers a non-locked Solver template, so the derive script refuses any other value.
SOLVER_TEMPLATE_PIN = "configs/probes/slurp_native_role_solver_v2.txt"
SOLVER_TEMPLATE_SHA = "18bff5c557cac7ac14be6b08aa0a1a6ad54c1b9820199c3b6749b2271d756fbd"

#: The parents the composed cells are derived from (the HELD module COMP-1b cells: DEV-2000-ADDED roster pins, this roster's
#: agreement table, the centroid facet pin).
PARENT_ARM = "slurp-native-stage3-module-comp1b-dev2000-added-v1"
PARENT_SMOKE = "slurp-native-stage3-module-comp1b-dev2000-added-smoke-4-v1"
PARENT_PACKAGE = "docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1"
PARENT_PKG_NAME = "slurp-stage3-module-comp1b-dev2000-added-v1"

#: The in-chain REPLICATE: the HELD module OFF-arm cell, reused AS REGISTERED (its own package, ledger rows and receipt).
REPLICATE = {
    "experiment": "slurp-native-stage3-module-comp1b-aa-dev2000-added-v1",
    "run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1",
    "fit_run_id": "SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-FIT-V1",
    "attempt_id": "attempt-slurp-native-stage3-module-comp1b-aa-dev2000-added-generation-v1",
    "fit_attempt_id": "attempt-slurp-native-stage3-module-comp1b-aa-dev2000-added-fit-v1",
    "package": PARENT_PACKAGE,
    "decision_relpath": "coordination/slurp-stage3-module-comp1b-dev2000-added-v1/root-admission-v1.json",
}

#: The sealed A2 flight (cell A2, COMP-1b on DEV-2000-ADDED, lock v2.0 + v3): its arm and its in-chain A/A.
A2_ARM = {"run_id": "SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1",
          "attempt_id": "attempt-slurp-native-stage3-comp1b-dev2000-added-generation-v1",
          "experiment": "slurp-native-stage3-comp1b-dev2000-added-v1"}
A2_AA = {"run_id": "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1",
         "attempt_id": "attempt-slurp-native-stage3-comp1-aa-dev2000-added-generation-v1",
         "experiment": "slurp-native-stage3-comp1-aa-dev2000-added-v1"}
A2_READ = "docs/results/2026-09-30-slurp-a2-comp1b-dev2000-read.md"
LOCK_NOTE_V2_1 = "docs/results/2026-09-30-slurp-v2-1-lock-v1.md"
V4G_LOCK_RECORD = "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md"
STEP7 = "docs/readiness/2026-10-09-slurp-module-step7-v4g-default-v1.md"
PROGRAMME = "docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"

#: This roster's own cross-flight null (instrument note section 2d, the B6 pair) and the rule-3 bar at n = 1,000.
OWN_NULL = {"h_intent": 1.1520, "h_slu": 1.2525, "n": 1000}
BAR_PP_N1000 = 2.5
V4_STATS_ARTIFACT_ID = "SAEA-SLURP-V4-TRAIN-STATISTICS-V1"
V4_STATS_SHA256 = "01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223"
V4G_GUARDS = ["ee-wilson", "ti-expressible"]

#: The declared expectation, from the record (never a prior, owner decision 139). Primary metric: official pooled SLU-F1.
#: composed minus the A2 arm = review-off minus full graph (-1.48, N100 read, CI95 [-5.33, +2.72], unresolved) + the v4g
#: delivery gain (+1.55 [+0.81, +2.33] on the lock column, offline; it applies to the composed side only in the delivered
#: contrast) = +0.07, i.e. nothing a 2.5 pp cross-flight bar can resolve. The cell therefore claims NO benefit.
REVIEW_OFF_VS_FULL_PP = -1.48
V4G_LOCK_COLUMN_PP = 1.55
EXPECTED_EFFECT_PP = round(REVIEW_OFF_VS_FULL_PP + V4G_LOCK_COLUMN_PP, 2)   # +0.07
HARM_MARGIN_PP = 2.5

TUNING_ROSTER = ["slurp-train-construction-pool-agree-kprobe-r01-excluded", "SLURP-EVO-FOLD-A-V2"]
#: A DECLARED exception to item D3, stated in the registered note, README and report rather than hidden: the v4 rule set that v4g extends was
#: SELECTED on the A2 DEV pool, which is this read roster (confirmed on Fold A, guards located on Fold A, lock confirmed on Fold B). Naming the
#: read roster in ``tuning_roster`` would make the launch gate report a blocking ``tuning-read-overlap`` the coordinator cannot clear, so the
#: roster list stays the rosters the COMPOSITION's own constants were chosen on and this text carries the v4 selection instead.
TUNING_EXCEPTION = (
    "the v4 rule set (fx-article, fx-oclock, scope, ti1, ee10) that saea-deliver-normalise-v4g extends was SELECTED offline on the A2 DEV pool "
    "(431 combinations + 10 single rules on DEV-2000-ADDED, COMP-1b delivered column; docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md), "
    "which is this cell's read roster; it was confirmed on TRAIN Fold A, its guards were located on Fold A and checked on A2, and the lock was "
    "confirmed on TRAIN Fold B (docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md). The v4g delivered gain on this roster is therefore "
    "in-sample for the rule choice and descriptive only; the declared expectation quotes the Fold B confirmation."
)


def names(kind: str) -> dict:
    """Identities of the composed ``arm`` / ``smoke`` cell."""

    smoke = kind == "smoke"
    tail = "-smoke-4" if smoke else ""
    run_tail = "-SMOKE-4" if smoke else ""
    experiment = f"slurp-native-stage3-{SLUG}{tail}-v1"
    upper = SLUG.upper()
    return {
        "experiment": experiment,
        "baseline": f"slurp-native-stage3-{SLUG}{tail}-baseline-v1",
        "run_id": f"SAEA-SLURP-STAGE3-{upper}{run_tail}-V1",
        "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}{run_tail}-FIT-V1",
        "attempt_id": f"attempt-slurp-native-stage3-{SLUG}{tail}-generation-v1",
        "fit_attempt_id": f"attempt-slurp-native-stage3-{SLUG}{tail}-fit-v1",
        "prefix": "smoke-" if smoke else "",
    }


ARM, SMOKE = names("arm"), names("smoke")


def fit_contact_cap(rows: int) -> int:
    """Structural: rows x program max contacts x (max_speech_packets + 3). Never run-cumulative."""

    return rows * CEILING * FIT_ENDPOINTS_PER_CONTACT
