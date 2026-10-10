"""Shared identities of cell VER-1c (the R1 c3 Solver template column on TRAIN Fold A: the verdict source of the VER-1 rule).

One module, imported by the derive, writer, mint, dry-run scripts and by the preflight test, so no id is spelled twice. Model-free.
Read constants as ``cf.NAME``. It is a PARAMETERISED clone of ``nx_r1_family`` (iteration-free) at one candidate arm: the candidate
list, the roster and the ids are the constants below; every script derives its prose and arithmetic from them.

WHAT VER-1c IS. Owner decision 257's execution plan names "VER-1b Fold A confirmation pool + a c3 column there" (decision 258 option A,
proposed 2026-10-10). The VER-1 rule contains the c3 presence verdict (the Solver answered no entity under the R1 ``r1-c3`` template,
after v4g) gated by the pre-Solver signature N1. On TRAIN Fold B that verdict came from the NX R1 flights; on TRAIN Fold A no c3 column
exists, so the confirmation needs one: this cell is an E1 same-flight Solver-template column on TRAIN Fold A with ONE candidate arm --
the R1 c3 template, the SAME pinned bytes the R1 iteration-1 cell flew (``configs/probes/nx/solver/r1/r1-c3.txt``) --, the in-chain
``aa`` twin and the delivering ``lock`` arm: three arms at the one Solver visit, ceiling ``2 + (3 - 1) = 4`` (the E1 arithmetic
``base + K - 1``, base 2). The base is the review-off COMP-1b module graph at lock v2.2 (the R5 composed arm; the R6-P1 / VER-1a base).

THE ARM'S ROLE. The arm is the VERDICT SOURCE of the VER-1 rule (``scripts/analysis/slurp_ver1_offline.py --verdict-run``), not a
nomination: ``claims_benefit`` false, expected effect 0.0 pp. The delivering arm is the lock (invariant I7), so the delivered answer is
unchanged; the column is read offline together with the VER-1b sample pool (``ver1b_family``) on the same Fold A rows. The rule was FIXED
on ``SLURP-EVO-FOLD-B-V2`` and nothing is chosen here.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-10"
#: The committed COMP-1b Fold A fragments (arm / smoke): the Fold A pins and the preparation receipts are inherited from them.
PARENT_SLUG = "comp1b-fold-a"
#: The R1 iteration-1 fit measure: measured on the COMP-1b Fold A first Solver visits (the roster this cell flies), so its
#: ``template_frame`` and the per-template token counts apply to Fold A as measured.
R1_FIT_MEASURE = "docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/fit-measure-v1.json"
R1_CANDIDATES_README = "docs/readiness/2026-10-09-slurp-nx-r1-solver-candidates-v1/README.md"

SLUG = "ver1c-c3-column-fold-a"
ROUND_LABEL = "VER-1c"
CELL_LABEL = "VER-1c"
SHORT = "ver1c"
BRANCH = "sonnet/ver1b-register"
WORKTREE = "/home/chao/saea-worktrees/sonnet-ver1b"
SOURCE_TREE = f"studies/speech-aware-evidence-acquisition, worktree {WORKTREE}, branch {BRANCH}"

# ---- the parameters --------------------------------------------------------------------------------------------------------
ROWS = 1080
SMOKE_ROWS = 4
NODE = "solver"
ARMS = ("r1-c3",)                                   # the candidate arm(s): the R1 c3 template, the same pinned bytes
DELIVERING, TWIN = "lock", "aa"
ARM_ORDER = (*ARMS, TWIN, DELIVERING)
K = len(ARM_ORDER)
BASE_CONTACTS = 2                                   # Perception 1 + Solver 1 on the review-off graph
CEILING = BASE_CONTACTS + (K - 1)                   # E1: base + K - 1
PROGRAM = f"phase-native-module-v1-c{CEILING}"      # a registered member of MODULE_PROGRAM_FAMILY_IDS
FIT_ENDPOINTS_PER_CONTACT = 4                       # max_speech_packets (1) + 3, the gate's endpoints_per_contact
#: 4,320 contacts: the R1 iteration-1 plan was 3.5 GPU-h for 8,640 (0.405 h per 1,000), so 1.8 h plans this arm.
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 1.8, 1.0
LOCK = "v2.2"                                       # v4g at delivery (module step 7), the R5 arm's base
EXPECTED_EFFECT_PP = 0.0                            # the arm is a verdict source, not a nomination

FOLD = "A"
TUNING_FOLD = "B"
ROSTER_ID = f"SLURP-EVO-FOLD-{FOLD}-V2"
TUNING_ROSTER, READ_ROSTER = f"SLURP-EVO-FOLD-{TUNING_FOLD}-V2", ROSTER_ID
FOLD_TOKEN = f"FOLD-{FOLD}"
FOLD_TITLE = f"TRAIN Fold {FOLD}"
TUNING_TITLE = f"TRAIN Fold {TUNING_FOLD}"

LOCKED_TEMPLATE = "configs/probes/slurp_native_role_solver_v2.txt"
LOCKED_TEMPLATE_SHA = "18bff5c557cac7ac14be6b08aa0a1a6ad54c1b9820199c3b6749b2271d756fbd"
CANDIDATE_PATHS = {a: f"configs/probes/nx/solver/r1/{a}.txt" for a in ARMS}
#: The sha256 recorded in the R1 candidates README for r1-c3 (the bytes the R1 iteration-1 cell flew).
CANDIDATE_README_SHA = {"r1-c3": "89b81e97c0c8d5377eff2892fac548ac83fd6a24f61ceb25396a57196bb262dc"}
VERDICT_ARM = "r1-c3"                               # the arm whose empty answer (after v4g) is the c3 presence verdict

FLOOR_SLU_PP = 1.49                                 # the E1 provisional same-flight floors (borrowed until a node column measures its own null)
FLOOR_INTENT_PP = 0.65

V4_STATS_ARTIFACT_ID = "SAEA-SLURP-V4-TRAIN-STATISTICS-V1"
V4_STATS_SHA256 = "01e6a019c91f52bcd2941f593cfec9e8db120543334d46b9e643c29e4023f223"
V4_RULES = ["fx-article", "fx-oclock", "scope", "ti1", "ee10"]
V4G_GUARDS = ["ee-wilson", "ti-expressible"]

SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official-train"

#: The disclosure (R6-P1 precedent): the R1 candidates were authored from AGGREGATE contrast tables computed on TRAIN Fold A (the R1
#: tuning roster), which is this cell's read roster; naming Fold A as the tuning roster would make the launch gate report a blocking
#: ``tuning-read-overlap``, so the measurement block keeps the rule's tuning roster (Fold B) and this text carries the exposure.
TUNING_DISCLOSURE = (
    "the R1 c3 template (r1-c3) was authored from AGGREGATE contrast tables computed on TRAIN Fold A (the R1 tuning roster, "
    f"{R1_CANDIDATES_README}), which is this cell's read roster, and then measured on TRAIN Fold B by the NX R1 flights; no utterance text, "
    "gold value or note body was read to author it. The VER-1 rule (support filter, c3 verdict x N1 gate, v4g) was FIXED on TRAIN Fold B; "
    "the Fold A read here is therefore a confirmation of the RULE on a roster the rule's thresholds never saw, but not an independent "
    "roster for the c3 TEMPLATE's authoring tables."
)

LEDGER_MARK = (f"## VER-1c: the R1 c3 Solver template column on {FOLD_TITLE} "
               f"(verdict source of the rule fixed on {TUNING_TITLE})")

PKG_NAME = f"slurp-{SLUG}-v1"
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = f"slurp-{SLUG}-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = f"SAEA-SLURP-STAGE3-{SLUG.upper()}-COLUMN-READ-V1"
RECIPE_ID = f"slurp-{SLUG}-column-analysis-v1"
CAMPAIGN = f"configs/campaign/slurp-native-stage3-{SLUG}-v1.json"

PROGRAMME = "docs/readiness/2026-10-09-slurp-nx-node-extreme-programme-v1.md"
SPEC = "docs/superpowers/specs/2026-10-09-slurp-nx-node-template-variant-instrument-design.md"
EXCHANGE = "docs/results/2026-10-09-slurp-nx-exchange-rates-offline.md"
V4G_LOCK_RECORD = "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md"
COMPOSER = "scripts/analysis/slurp_ver1_offline.py"

ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    "smoke": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",       # the first SMOKE_ROWS items (the COMP-1b Fold A smoke ids)
}


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
    lo = "-smoke-4" if kind == "smoke" else ""
    return {"experiment": f"slurp-native-stage3-{PARENT_SLUG}{lo}-v1", "baseline": f"slurp-native-stage3-{PARENT_SLUG}{lo}-baseline-v1"}


def candidate_pins() -> dict[str, dict]:
    pins = {a: {"relpath": p, "sha256": hashlib.sha256((REPO_ROOT / p).read_bytes()).hexdigest()} for a, p in CANDIDATE_PATHS.items()}
    for arm, pin in pins.items():
        if pin["sha256"] != CANDIDATE_README_SHA[arm]:
            raise SystemExit(f"{arm}: the pinned template bytes {pin['sha256']} are not the R1 candidates README's {CANDIDATE_README_SHA[arm]}")
    return pins


def fit_measure() -> dict:
    return json.loads((REPO_ROOT / R1_FIT_MEASURE).read_text(encoding="utf-8"))


def fit_contact_cap(rows: int) -> int:
    """The FIT contact_cap the gate demands: rows x max_contacts x endpoints per contact (never run-cumulative)."""

    return rows * CEILING * FIT_ENDPOINTS_PER_CONTACT


def smoke_ids() -> list[str]:
    document = json.loads((REPO_ROOT / "configs" / "experiment" / f"{parent_names('smoke')['experiment']}.json").read_text(encoding="utf-8"))
    return list(document["populations"][0]["ids"])


def roster_items(kind: str) -> list[dict]:
    items = json.loads((REPO_ROOT / ROSTER[kind]).read_text(encoding="utf-8"))["items"]
    if kind == "arm":
        return items
    wanted = smoke_ids()
    picked = [item for item in items if item["sample_id"] in set(wanted)]
    if [item["sample_id"] for item in picked] != wanted or len(picked) != SMOKE_ROWS:
        raise SystemExit("the smoke ids are not the roster prefix in roster order")
    return picked


def roster_audio(kind: str) -> float:
    return sum(float(item["audio_seconds"]) for item in roster_items(kind))


def audio_cap(kind: str) -> int:
    """Every contact re-sends the row's speech packet: ceil(roster audio x ceiling)."""

    return math.ceil(roster_audio(kind) * CEILING - 1e-9)
