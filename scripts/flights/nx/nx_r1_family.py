"""Shared identities of NX round R1 (the Solver instruction-template column, TRAIN Fold B).

One module, imported by the derive, writer, mint and read scripts, so no id is spelled twice. Model-free.

ITERATIONS. Round R1 has two evaluated iterations under the plateau rule (programme C0.4). Everything that differs between
them (slug, candidate arms, the candidates README, the declared effect, the smoke recovery state, the worktree and branch)
lives in ``_ITERATIONS``; ``configure(n)`` rebinds the module constants. The default is iteration 1 (or ``$NX_R1_ITERATION``);
every script takes ``--iteration N`` and calls ``configure`` before it reads a constant, so iteration 1 keeps its exact
identities and iteration 2 derives its own from the same code. Read constants as ``nf.NAME`` (never ``from nf import NAME``)
so a later ``configure`` is seen.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-09"
PARENT_SLUG = "psv4-fold-b"                       # the Fold B pins are copied from the P-SV-4 fragments
COMP1B_EXPERIMENT = "slurp-native-stage3-comp1b-fold-a-v1"

#: The smoke's single root-diagnosed recovery re-registration of ITERATION 1 (2026-10-09), AMENDED the same day twice (rec1,
#: rec2, now rec3). A (run_id, attempt_id) pair is a one-time key, so the smoke was re-flown whole under the rec3 attempt ids;
#: the arm never started and keeps its attempt ids. Iteration 2 has NO recovery: its smoke is a first attempt.
_SMOKE_RECOVERY_ITER1 = {
    "recovery_index": 1,
    "predecessor_attempt_id": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-generation-v1",
    "predecessor_fit_attempt_id": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-fit-v1",
    "predecessor_state": "OPENED; 32 contacts / 81.453 speech-seconds spent; failed at seal; preserved unread",
    "predecessors": [
        {
            "attempt_id": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-generation-v1",
            "state": "failed at seal after 32 contacts",
            "contacts_spent": 32,
            "speech_seconds_spent": 81.453,
        },
        {
            "attempt_id": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-generation-rec1-v1",
            "state": "refused pre-contact by the run-cumulative budget adapter",
            "contacts_spent": 0,
        },
        {
            "attempt_id": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-generation-rec2-v1",
            "state": "refused pre-contact by the FIT gate (contact_cap 256 != the structural maximum endpoint count 128)",
            "contacts_spent": 0,
        },
    ],
    "amended_from_attempt_id": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-generation-rec2-v1",
    "amended_from_fit_attempt_id": "attempt-slurp-native-stage3-nx-r1-solver-fold-b-smoke-4-fit-rec2-v1",
    "amended_from_state": (
        "OPENED; 0 contacts; refused pre-contact by core/preparation_fit.py build_native_contact_fit_gate: the FIT "
        "contact_cap was scaled to 256 but must equal rows x max_contacts x (max_speech_packets + 3) = 4 x 8 x 4 = 128"
    ),
    "reason": (
        "The predecessor attempt made its 32 contacts and failed at runtime.seal() on the template-variant delivery "
        "validator (root cause fixed on master in commit 6633c9251, core/flight/runtime.py; tests "
        "tests/unit/test_template_variants_delivery.py). The smoke is re-flown whole under the rec3 attempt; the arm "
        "is untouched."
    ),
    "amendment": (
        "AMENDED 2026-10-09 (coordinator ruling, Fable 5.1), twice. rec1 carried the SAME plan budget as the failed "
        "attempt although the adapter enforces planned_model_calls and planned_speech_audio_seconds run-cumulatively, "
        "so it was refused before any contact (0 contacts). rec2 fixed the generation budget but also scaled the FIT "
        "contact_cap by the attempts multiplier (256); the FIT cap is a structural per-attempt number, never run-"
        "cumulative, so rec2 was refused pre-contact by the FIT gate (0 contacts; no FIT attempt records exist). Both "
        "are pre-contact registration defects of the recovery itself, not flight failures; the single recovery "
        "re-registration is amended to rec3: the generation budget stays run-cumulative (64 calls, 164 speech-"
        "seconds, SMOKE_ATTEMPTS_BUDGETED) and the FIT cap is the structural formula (fit_contact_cap)."
    ),
    "rule": "A second failure closes the cell; the fix is proven on a four-row dry run.",
    "fit_cap_rule": "The FIT cap is structural: rows x max_contacts x (max_speech_packets + 3).",
}

_ITERATIONS = {
    1: {
        "slug": "nx-r1-solver-fold-b",
        "round_label": "NX round R1",
        "cell_label": "NX-R1-SOLVER",
        "arms": ("r1-c1", "r1-c2", "r1-c3", "r1-c4", "r1-c5"),
        "candidates_readme": "docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md",
        "expected_effect_pp": 1.80,
        "smoke_recovery": _SMOKE_RECOVERY_ITER1,
        "smoke_rec": "-rec3",
        "short": "nxr1",
        "branch": "fable/nx-r1-register",
        "worktree": "/home/chao/saea-worktrees/fable-nx-r1-register",
        "ledger_mark": "## NX round R1: the Solver instruction-template column on TRAIN Fold B",
    },
    2: {
        "slug": "nx-r1-i2-solver-fold-b",
        "round_label": "NX round R1 iteration 2",
        "cell_label": "NX-R1-I2-SOLVER",
        "arms": ("r1-i2-c1", "r1-i2-c2", "r1-i2-c3", "r1-i2-c4", "r1-i2-c5"),
        "candidates_readme": "docs/readiness/2026-10-09-slurp-nx-r1-iter2-solver-candidates-v1/README.md",
        "expected_effect_pp": 1.54,
        "smoke_recovery": None,
        "smoke_rec": "",
        "short": "nxr1i2",
        "branch": "fable/nx-r1-i2-register",
        "worktree": "/home/chao/saea-worktrees/fable-nx-r1-i2-register",
        "ledger_mark": "## NX round R1 iteration 2: the Solver instruction-template column on TRAIN Fold B",
    },
}

SMOKE_ATTEMPTS_BUDGETED_ITER1 = 2

ROWS = 1080
DELIVERING, TWIN = "lock", "aa"
FIT_ENDPOINTS_PER_CONTACT = 4                      # max_speech_packets (1) + 3, the gate's endpoints_per_contact
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 3.5, 1.0

LOCKED_TEMPLATE = "configs/probes/slurp_native_role_solver_v2.txt"
LOCKED_TEMPLATE_SHA = "18bff5c557cac7ac14be6b08aa0a1a6ad54c1b9820199c3b6749b2271d756fbd"

ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "smoke": "docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json",
}
TUNING_ROSTER, READ_ROSTER = "SLURP-EVO-FOLD-A-V2", "SLURP-EVO-FOLD-B-V2"

FLOOR_SLU_PP = 1.49
FLOOR_INTENT_PP = 0.65

V4_STATS_ARTIFACT_ID = "SAEA-SLURP-V4-TRAIN-STATISTICS-V1"
V4_STATS_SHA256 = "01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223"
V4_RULES = ["fx-article", "fx-oclock", "scope", "ti1", "ee10"]
V4G_GUARDS = ["ee-wilson", "ti-expressible"]

SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

#: Iteration-1 identities the iteration-2 package refers to (descriptive cross-iteration context only).
ITER1_RUN_ID = "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-V1"
ITER1_ATTEMPT_ID = "attempt-slurp-native-stage3-nx-r1-solver-fold-b-generation-v1"
ITER1_READ_RUN_ID = "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1"
ITER1_PACKAGE = f"docs/readiness/{DATE}-slurp-nx-r1-solver-fold-b-v1"
ITER1_FIT_MEASURE = f"{ITER1_PACKAGE}/fit-measure-v1.json"
ITER1_COMPARATOR_ARM = "r1-c5"


def names(kind: str) -> dict:
    smoke = kind == "smoke"
    lo = "-smoke-4" if smoke else ""
    up = "-SMOKE-4" if smoke else ""
    rec = _ITERATIONS[ITERATION]["smoke_rec"] if smoke else ""   # iteration 1's smoke recovery (SMOKE_RECOVERY)
    return {
        "experiment": f"slurp-native-stage3-{SLUG}{lo}-v1",
        "baseline": f"slurp-native-stage3-{SLUG}{lo}-baseline-v1",
        "run_id": f"SAEA-SLURP-STAGE3-{SLUG.upper()}{up}-V1",
        "fit_run_id": f"SAEA-SLURP-STAGE3-{SLUG.upper()}{up}-FIT-V1",
        "attempt_id": f"attempt-slurp-native-stage3-{SLUG}{lo}-generation{rec}-v1",
        "fit_attempt_id": f"attempt-slurp-native-stage3-{SLUG}{lo}-fit{rec}-v1",
        "prefix": "smoke-" if smoke else "",
    }


def configure(iteration: int) -> None:
    """Rebind every iteration-dependent module constant. Idempotent."""

    if iteration not in _ITERATIONS:
        raise SystemExit(f"unknown NX R1 iteration {iteration!r}; known: {sorted(_ITERATIONS)}")
    cfg = _ITERATIONS[iteration]
    g = globals()
    g["ITERATION"] = iteration
    g["SLUG"] = cfg["slug"]
    g["ROUND_LABEL"] = cfg["round_label"]
    g["CELL_LABEL"] = cfg["cell_label"]
    g["SHORT"] = cfg["short"]
    g["BRANCH"], g["WORKTREE"] = cfg["branch"], cfg["worktree"]
    g["LEDGER_MARK"] = cfg["ledger_mark"]
    g["SOURCE_TREE"] = f"studies/speech-aware-evidence-acquisition, worktree {cfg['worktree']}, branch {cfg['branch']}"
    g["PKG_NAME"] = f"slurp-{cfg['slug']}-v1"      # coordination dir, package suffix, decision-id stem
    g["PACKAGE"] = f"docs/readiness/{DATE}-{g['PKG_NAME']}"
    g["PREREG"] = f"{g['PACKAGE']}-preregistration.md"
    g["DECISION_ID"] = f"slurp-{cfg['slug']}-admission-v1"
    g["DECISION_RELPATH"] = f"coordination/{g['PKG_NAME']}/root-admission-v1.json"
    g["SMOKE_RECOVERY"] = cfg["smoke_recovery"]
    recovery = cfg["smoke_recovery"]
    g["SMOKE_ATTEMPTS_BUDGETED"] = SMOKE_ATTEMPTS_BUDGETED_ITER1 if recovery else 1
    g["SMOKE_PREDECESSOR_CONTACTS_SPENT"] = sum(p["contacts_spent"] for p in recovery["predecessors"]) if recovery else 0
    g["SMOKE_PREDECESSOR_SPEECH_SECONDS_SPENT"] = (
        sum(p.get("speech_seconds_spent", 0.0) for p in recovery["predecessors"]) if recovery else 0.0)
    g["ARM"], g["SMOKE"] = names("arm"), names("smoke")
    g["READ_RUN_ID"] = f"SAEA-SLURP-STAGE3-{cfg['slug'].upper()}-COLUMN-READ-V1"
    g["RECIPE_ID"] = f"slurp-{cfg['slug']}-column-analysis-v1"
    g["CAMPAIGN"] = f"configs/campaign/slurp-native-stage3-{cfg['slug']}-v1.json"
    g["ARMS"] = cfg["arms"]
    g["ARM_ORDER"] = (*cfg["arms"], TWIN, DELIVERING)
    g["CEILING"] = 2 + (len(g["ARM_ORDER"]) - 1)    # perception 1 + solver 1 + (K - 1) = 8
    g["PROGRAM"] = f"phase-native-module-v1-c{g['CEILING']}"
    g["CANDIDATES_README"] = cfg["candidates_readme"]
    g["CANDIDATE_PATHS"] = {a: f"configs/probes/nx/solver/r1/{a}.txt" for a in cfg["arms"]}
    g["FIT_MEASURE"] = f"{g['PACKAGE']}/fit-measure-v1.json"
    g["EXPECTED_EFFECT_PP"] = cfg["expected_effect_pp"]


ITERATION = int(os.environ.get("NX_R1_ITERATION", "1"))
configure(ITERATION)


def candidate_pins() -> dict[str, dict]:
    import hashlib

    return {
        a: {"relpath": p, "sha256": hashlib.sha256((REPO_ROOT / p).read_bytes()).hexdigest()}
        for a, p in CANDIDATE_PATHS.items()
    }


def fit_measure() -> dict:
    return json.loads((REPO_ROOT / FIT_MEASURE).read_text(encoding="utf-8"))


def fit_contact_cap(rows: int) -> int:
    """The FIT contact_cap the gate demands: rows x max_contacts x endpoints per contact (never run-cumulative)."""
    return rows * CEILING * FIT_ENDPOINTS_PER_CONTACT


def localize(text: str) -> str:
    """Re-label iteration-1 prose for the configured iteration (identity on iteration 1)."""

    if ITERATION == 1:
        return text
    readme_dir = CANDIDATES_README.rsplit("/", 1)[0]
    return (
        text.replace("docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1", readme_dir)
        .replace("NX round R1", ROUND_LABEL)
        .replace("NX-R1-SOLVER", CELL_LABEL)
        .replace("r1-c1 .. r1-c5", f"{ARMS[0]} .. {ARMS[-1]}")
    )
