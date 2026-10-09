"""Shared identities of NX round R1 (the Solver instruction-template column, TRAIN Fold B).

One module, imported by the derive, writer, mint and read scripts, so no id is spelled twice. Model-free.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-09"
SLUG = "nx-r1-solver-fold-b"
PKG_NAME = "slurp-nx-r1-solver-fold-b-v1"          # coordination dir, package suffix, decision-id stem
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = "slurp-nx-r1-solver-fold-b-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"

PARENT_SLUG = "psv4-fold-b"                       # the Fold B pins are copied from the P-SV-4 fragments
COMP1B_EXPERIMENT = "slurp-native-stage3-comp1b-fold-a-v1"

#: ``(kind) -> names``.
def names(kind: str) -> dict:
    smoke = kind == "smoke"
    lo = "-smoke-4" if smoke else ""
    up = "-SMOKE-4" if smoke else ""
    return {
        "experiment": f"slurp-native-stage3-{SLUG}{lo}-v1",
        "baseline": f"slurp-native-stage3-{SLUG}{lo}-baseline-v1",
        "run_id": f"SAEA-SLURP-STAGE3-{SLUG.upper()}{up}-V1",
        "fit_run_id": f"SAEA-SLURP-STAGE3-{SLUG.upper()}{up}-FIT-V1",
        "attempt_id": f"attempt-slurp-native-stage3-{SLUG}{lo}-generation-v1",
        "fit_attempt_id": f"attempt-slurp-native-stage3-{SLUG}{lo}-fit-v1",
        "prefix": "smoke-" if smoke else "",
    }


ARM, SMOKE = names("arm"), names("smoke")
READ_RUN_ID = "SAEA-SLURP-STAGE3-NX-R1-SOLVER-FOLD-B-COLUMN-READ-V1"
RECIPE_ID = "slurp-nx-r1-solver-fold-b-column-analysis-v1"
CAMPAIGN = f"configs/campaign/slurp-native-stage3-{SLUG}-v1.json"
SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"

ROWS = 1080
ARMS = ("r1-c1", "r1-c2", "r1-c3", "r1-c4", "r1-c5")
DELIVERING, TWIN = "lock", "aa"
ARM_ORDER = (*ARMS, TWIN, DELIVERING)
CEILING = 2 + (len(ARM_ORDER) - 1)                 # perception 1 + solver 1 + (K - 1) = 8
FIT_ENDPOINTS_PER_CONTACT = 4
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 3.5, 1.0
PROGRAM = f"phase-native-module-v1-c{CEILING}"

CANDIDATES_README = "docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md"
LOCKED_TEMPLATE = "configs/probes/slurp_native_role_solver_v2.txt"
LOCKED_TEMPLATE_SHA = "18bff5c557cac7ac14be6b08aa0a1a6ad54c1b9820199c3b6749b2271d756fbd"
CANDIDATE_PATHS = {a: f"configs/probes/nx/solver/r1/{a}.txt" for a in ARMS}
FIT_MEASURE = f"{PACKAGE}/fit-measure-v1.json"

ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "smoke": "docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json",
}
TUNING_ROSTER, READ_ROSTER = "SLURP-EVO-FOLD-A-V2", "SLURP-EVO-FOLD-B-V2"

#: Declared round effect (candidates README section 4; exchange-rate note section 0).
EXPECTED_EFFECT_PP = 1.80
FLOOR_SLU_PP = 1.49
FLOOR_INTENT_PP = 0.65

V4_STATS_ARTIFACT_ID = "SAEA-SLURP-V4-TRAIN-STATISTICS-V1"
V4_STATS_SHA256 = "01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223"
V4_RULES = ["fx-article", "fx-oclock", "scope", "ti1", "ee10"]
V4G_GUARDS = ["ee-wilson", "ti-expressible"]


def candidate_pins() -> dict[str, dict]:
    import hashlib

    return {
        a: {"relpath": p, "sha256": hashlib.sha256((REPO_ROOT / p).read_bytes()).hexdigest()}
        for a, p in CANDIDATE_PATHS.items()
    }


def fit_measure() -> dict:
    return json.loads((REPO_ROOT / FIT_MEASURE).read_text(encoding="utf-8"))
