"""Shared identities of cell VER-1a (the five-sample greedy-first Solver pool on TRAIN Fold B).

One module, imported by the derive, writer, mint, dry-run scripts and by the preflight test, so no id is spelled twice. Model-free.
Read constants as ``vf.NAME``.

WHAT VER-1a IS. Owner decision 257 (2026-10-10): the verification layer of the training-free RL round is built over the Solver's OWN
sampled answers. VER-1a seals the SAMPLE POOL that layer is selected on: the review-off COMP-1b module graph at lock v2.2 (the R5
composed arm; the R6-P1 base) on TRAIN Fold B (``SLURP-EVO-FOLD-B-V2``, 1,080 rows) with the Solver visit grouped at ``samples = 5``:
sample 0 GREEDY (the fragment's own temperature 0, i.e. the answer the lock's single-sample delivery already makes) and samples 1-4
at temperature 0.7 (the ROLL form). Contacts per row: 1 Perception + 5 Solver = 6.

It is a POOL cell, like ROLL-2: it claims no benefit. The pool is read OFFLINE together with the existing c3 verdict columns of the NX
R1 / R6 flights on the same roster; the VER-1 rule is selected there (``measurement_design offline-sealed-pool``).

DELIVERY. The loader refuses ``native_episode.deliver_normaliser`` beside a grouped Solver visit (the delivered text is the commit
policy's aggregate, re-derivable from the recorded samples; normalising on top would make the delivered bytes a function of two rules
with one in custody), and the module compiler has no ``samples`` knob. So the cell is a hand-written fragment on the registered
review-off program id ``phase-native-module-v1-c6`` (no ``consumption_module`` block): the in-flight delivered answer is the registered
plurality-support commit (``saea-commit-plurality-support-v1``) at ``min_support 3`` over the five samples, UNNORMALISED, scored
unprojected by ``slurp-slu-official-train`` (exactly ROLL-2's precedent; the ROLL form for five samples carries min_support 3). The v4g delivery normaliser, lock v2.2's delivery rule, is
applied OFFLINE to each custodied raw sample and to the replayed commit.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-10"
#: The committed R6-P1 baselines (arm / smoke) the Fold B pins, the speech-query pins and the preparation receipts are inherited from.
PARENT_SLUG = "nx-r6-perception-fold-b"

SLUG = "ver1a-samples-fold-b"
ROUND_LABEL = "VER-1a"
CELL_LABEL = "VER-1a"
SHORT = "ver1a"
BRANCH = "sonnet/ver1a-samples5"
WORKTREE = "/home/chao/saea-worktrees/sonnet-ver1a5"
SOURCE_TREE = f"studies/speech-aware-evidence-acquisition, worktree {WORKTREE}, branch {BRANCH}"
LEDGER_MARK = "## VER-1a: the five-sample greedy-first Solver pool on TRAIN Fold B"
#: The heading the section carried at the original three-sample registration (the in-place amendment renames it).
LEDGER_MARK_THREE_SAMPLE = "## VER-1a: the three-sample greedy-first Solver pool on TRAIN Fold B"
#: The one-sentence note appended to every amended (countersigned) ledger row; the countersignature text itself stays verbatim.
AMENDMENT_MARK = ("AMENDED 2026-10-10 to 5 samples before any contact (coordinator ruling after the offline composer read; "
                  "nothing flown)")

PKG_NAME = f"slurp-{SLUG}-v1"                     # coordination dir, package suffix, decision-id stem
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = f"slurp-{SLUG}-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = f"SAEA-SLURP-STAGE3-{SLUG.upper()}-POOL-READ-V1"
RECIPE_ID = f"slurp-{SLUG}-pool-read-v1"
CAMPAIGN = f"configs/campaign/slurp-native-stage3-{SLUG}-v1.json"

ROWS = 1080
SMOKE_ROWS = 4
#: Amended 2026-10-10 from 3 to 5 samples (nothing had flown): the offline composer read (scripts/analysis/slurp_ver1_offline.py) resolves the
#: support filter's gain over v4g only at n = 5, s = 2, so the pool must carry five samples for s = 2, 3-of-5 and the gate to be read offline.
SAMPLES = 5
#: Perception 1 + Solver 1 x samples 5 (rails.native_episode_config: perception + (revisions + 1) x (solver iterations x samples)).
BASE_CONTACTS = 2
CEILING = 1 + 1 * SAMPLES
PROGRAM = f"phase-native-module-v1-c{CEILING}"     # a registered member of MODULE_PROGRAM_FAMILY_IDS (the review-off graph's family)
FIT_ENDPOINTS_PER_CONTACT = 4                      # max_speech_packets (1) + 3, the gate's endpoints_per_contact
#: 6,480 contacts at the measured 44 requests per minute on np4 is about 2.5 GPU-h (FIT inclusive); 2.5 h plans the arm.
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 2.5, 1.0
LOCK = "v2.2"                                      # the lock the base was compiled from; its delivery normaliser v4g moves OFFLINE

SOLVER_OVERRIDES = {"temperature": 0.7, "seed_offset": 0, "greedy_first": True}
SOLVER_COMMIT = {"policy": "saea-commit-plurality-support-v1", "min_support": 3, "similarity_threshold": 0.8}
DELIVERED_NORMALISER_IN_FLIGHT = None              # refused beside samples >= 2 (native_episode_config); v4g is applied offline

DESIGN_NOTE = "docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md"
ROLL_READ = "docs/results/2026-09-28-slurp-roll-2-fold-a-pool-read.md"
AGGREGATION_READ = "docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md"
V4G_LOCK_RECORD = "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md"

ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
    "smoke": "docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json",
}
TUNING_ROSTER, READ_ROSTER = "none", "SLURP-EVO-FOLD-B-V2"
FLOOR_SLU_PP = 0.67                                # the offline sealed-pool floor of the instrument note (section 2d)
FLOOR_INTENT_PP = 0.67

SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official-train"


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


def parent_names(kind: str) -> dict:
    """The R6-P1 cell's own fragment names (the committed parent)."""

    lo = "-smoke-4" if kind == "smoke" else ""
    return {"experiment": f"slurp-native-stage3-{PARENT_SLUG}{lo}-v1", "baseline": f"slurp-native-stage3-{PARENT_SLUG}{lo}-baseline-v1"}


def fit_contact_cap(rows: int) -> int:
    """The FIT contact_cap the gate demands: rows x max_contacts x endpoints per contact (never run-cumulative)."""

    return rows * CEILING * FIT_ENDPOINTS_PER_CONTACT


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def roster_audio(kind: str) -> float:
    doc = json.loads((REPO_ROOT / ROSTER[kind]).read_text(encoding="utf-8"))
    return sum(float(i["audio_seconds"]) for i in doc["items"])


def audio_cap(kind: str) -> int:
    """Every contact re-sends the row's speech packet: ceil(roster audio x ceiling)."""

    return math.ceil(roster_audio(kind) * CEILING - 1e-9)
