"""Shared identities of cell VER-1b (the three-sample greedy-first Solver pool on TRAIN Fold A: the confirmation pool of the VER-1 rule).

One module, imported by the derive, writer, mint, dry-run scripts and by the preflight test, so no id is spelled twice. Model-free.
Read constants as ``vf.NAME``. It is a PARAMETERISED clone of ``ver1a_family``: the sample count, the support threshold, the roster
and the ids are the constants below; every script derives its prose, arithmetic and checks from them (no number is repeated in a
script body), so a re-parameterisation (another sample count, another fold) is an edit of THIS module only.

WHAT VER-1b IS. Owner decision 257 (2026-10-10) put the verification layer (VER-1) of the training-free RL round over the Solver's OWN
sampled answers; VER-1a sealed the sample pool on TRAIN Fold B, where the rule was SELECTED (the pool read: filter + c3 gate
+1.29 / +1.43 in-sample, about +1.0 cross-fitted over the lock). Decision 258 (proposed 2026-10-10, option A) is the Fold A
CONFIRMATION of the rule at n = 3: this cell is the confirmation pool. It seals ``SAMPLES = 3`` Solver samples per row on TRAIN Fold A
(``SLURP-EVO-FOLD-A-V2``, 1,080 rows -- the roster of the COMP-1b / A2 Fold A cells) on the same review-off COMP-1b module graph at
lock v2.2 (the R5 composed arm; the R6-P1 / VER-1a base): sample 0 GREEDY (the fragment's own temperature 0, i.e. the answer the lock's
single-sample delivery already makes) and samples 1..SAMPLES-1 at temperature 0.7. Contacts per row: 1 Perception + SAMPLES Solver.

THE FIXED RULE. The rule that is CONFIRMED here was FIXED on the tuning roster ``SLURP-EVO-FOLD-B-V2`` and is not re-tuned on the read
roster: the support filter at n = 3 samples, s = 2 (an entity is kept iff at least 2 of the 3 samples support it), the c3 verdict
(the R1 c3 column answered no entity after v4g) gated by the pre-Solver signature N1 >= theta with theta = 0.2, delivered through the
lock's v4g normaliser. Only the sample pool is flown here; the rule is applied OFFLINE to the sealed pool, together with the c3 column
of cell VER-1c (``ver1c_family``) on the same Fold A rows, and nothing is chosen on Fold A.

It is a POOL cell, like VER-1a and ROLL-2: it claims no benefit (``measurement_design offline-sealed-pool``).

DELIVERY. The loader refuses ``native_episode.deliver_normaliser`` beside a grouped Solver visit, and the module compiler has no
``samples`` knob. So the cell is a hand-written fragment on the registered review-off program id ``phase-native-module-v1-c{CEILING}``
(no ``consumption_module`` block): the in-flight delivered answer is the registered plurality-support commit
(``saea-commit-plurality-support-v1``) at ``min_support = MIN_SUPPORT`` over the samples, UNNORMALISED, scored unprojected by
``slurp-slu-official-train``. The v4g delivery normaliser, lock v2.2's delivery rule, is applied OFFLINE to each custodied raw sample
and to the replayed commit.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DATE = "2026-10-10"
#: The committed COMP-1b Fold A fragments (arm / smoke): the Fold A pins, the speech-query pins and the preparation receipts are
#: inherited from them (the roster of the COMP-1b / A2 Fold A cells, ``SLURP-EVO-FOLD-A-V2``).
PARENT_SLUG = "comp1b-fold-a"
#: The committed VER-1a Fold B fragments: the structural twin the Fold A derive is proven against (tests/unit/test_ver1b_cell_registration.py).
SIBLING_SLUG = "ver1a-samples-fold-b"

SLUG = "ver1b-samples-fold-a"
ROUND_LABEL = "VER-1b"
CELL_LABEL = "VER-1b"
SHORT = "ver1b"
BRANCH = "sonnet/ver1b-register"
WORKTREE = "/home/chao/saea-worktrees/sonnet-ver1b"
SOURCE_TREE = f"studies/speech-aware-evidence-acquisition, worktree {WORKTREE}, branch {BRANCH}"

# ---- the parameters (everything below is derived from these) --------------------------------------------------------------
ROWS = 1080
SMOKE_ROWS = 4
SAMPLES = 3
#: The fixed rule (tuned on TUNING_ROSTER, confirmed on READ_ROSTER): support filter s over n = SAMPLES samples, gate theta.
RULE_N, RULE_S, RULE_THETA = 3, 2, 0.2
MIN_SUPPORT = RULE_S                                # the in-flight plurality commit carries the rule's own support threshold
SAMPLE_TEMPERATURE = 0.7
FOLD = "A"                                          # the read fold
TUNING_FOLD = "B"                                   # the fold the rule was fixed on
ROSTER_ID = f"SLURP-EVO-FOLD-{FOLD}-V2"
TUNING_ROSTER, READ_ROSTER = f"SLURP-EVO-FOLD-{TUNING_FOLD}-V2", ROSTER_ID
FOLD_TOKEN = f"FOLD-{FOLD}"                         # as it appears in the sealed-artifact ids (agreement table, query vectors)
BASE_CONTACTS = 2                                   # Perception 1 + Solver 1 on the review-off graph
CEILING = 1 + 1 * SAMPLES                           # rails.native_episode_config: perception + (revisions + 1) x (solver iterations x samples)
PROGRAM = f"phase-native-module-v1-c{CEILING}"      # a registered member of MODULE_PROGRAM_FAMILY_IDS
FIT_ENDPOINTS_PER_CONTACT = 4                       # max_speech_packets (1) + 3, the gate's endpoints_per_contact
#: 4,320 contacts at the measured 44 requests per minute on np4 is about 1.6 GPU-h (FIT inclusive); 1.7 h plans the arm (VER-1a: 6,480 -> 2.5).
PLANNED_GPU_HOURS_ARM, PLANNED_GPU_HOURS_SMOKE = 1.7, 1.0
LOCK = "v2.2"                                       # the lock the base was compiled from; its delivery normaliser v4g moves OFFLINE

SOLVER_OVERRIDES = {"temperature": SAMPLE_TEMPERATURE, "seed_offset": 0, "greedy_first": True}
SOLVER_COMMIT = {"policy": "saea-commit-plurality-support-v1", "min_support": MIN_SUPPORT, "similarity_threshold": 0.8}
DELIVERED_NORMALISER_IN_FLIGHT = None               # refused beside samples >= 2 (native_episode_config); v4g is applied offline

if not (RULE_N == SAMPLES and 1 <= RULE_S <= SAMPLES):
    raise SystemExit("the fixed rule must be read at the sealed sample count (n = SAMPLES) with 1 <= s <= SAMPLES")

# ---- derived prose pieces -------------------------------------------------------------------------------------------------
_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
SAMPLES_WORD = _WORDS[SAMPLES]
LAST_SAMPLE = SAMPLES - 1
#: "samples 1-2" (or "sample 1" when there is a single non-greedy draw)
DRAWN_TEXT = f"samples 1-{LAST_SAMPLE}" if LAST_SAMPLE > 1 else "sample 1"
#: the wire temperatures, in sample order: "0, 0.7, 0.7"
TEMPERATURES_TEXT = ", ".join(["0"] + [f"{SAMPLE_TEMPERATURE:g}"] * LAST_SAMPLE)
SEEDS_TEXT = f"fragment_seed + {SOLVER_OVERRIDES['seed_offset']} + index"
SCORING_TEXT = f"sample 0 greedy, {DRAWN_TEXT} at temperature {SAMPLE_TEMPERATURE:g}"
FOLD_TITLE = f"TRAIN Fold {FOLD}"
TUNING_TITLE = f"TRAIN Fold {TUNING_FOLD}"

LEDGER_MARK = (f"## VER-1b: the {SAMPLES_WORD}-sample greedy-first Solver pool on {FOLD_TITLE} "
               f"(confirmation pool of the rule fixed on {TUNING_TITLE})")

PKG_NAME = f"slurp-{SLUG}-v1"                       # coordination dir, package suffix, decision-id stem
PACKAGE = f"docs/readiness/{DATE}-{PKG_NAME}"
PREREG = f"{PACKAGE}-preregistration.md"
DECISION_ID = f"slurp-{SLUG}-admission-v1"
DECISION_RELPATH = f"coordination/{PKG_NAME}/root-admission-v1.json"
READ_RUN_ID = f"SAEA-SLURP-STAGE3-{SLUG.upper()}-POOL-READ-V1"
RECIPE_ID = f"slurp-{SLUG}-pool-read-v1"
CAMPAIGN = f"configs/campaign/slurp-native-stage3-{SLUG}-v1.json"

DESIGN_NOTE = "docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md"
ROLL_READ = "docs/results/2026-09-28-slurp-roll-2-fold-a-pool-read.md"
AGGREGATION_READ = "docs/results/2026-09-24-slurp-sample-aggregation-offline-read.md"
V4G_LOCK_RECORD = "docs/results/2026-10-09-slurp-postprocessing-v4g-lock-v1.md"
COMPOSER_README = "docs/readiness/2026-10-10-slurp-ver1-offline-composer-v1/README.md"
COMPOSER = "scripts/analysis/slurp_ver1_offline.py"

ROSTER = {
    "arm": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
    # No 4-row Fold A prefix receipt is committed; the smoke population is the first SMOKE_ROWS items of the arm roster (the COMP-1b
    # Fold A smoke fragment's own ids), so its audio is the sum over those items.
    "smoke": "docs/receipts/rosters/slurp-evo-fold-a-v2.json",
}
FLOOR_SLU_PP = 0.67                                 # the offline sealed-pool floor of the instrument note (section 2d)
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
    """The COMP-1b Fold A cell's own fragment names (the committed parent)."""

    lo = "-smoke-4" if kind == "smoke" else ""
    return {"experiment": f"slurp-native-stage3-{PARENT_SLUG}{lo}-v1", "baseline": f"slurp-native-stage3-{PARENT_SLUG}{lo}-baseline-v1"}


def sibling_names(kind: str) -> dict:
    lo = "-smoke-4" if kind == "smoke" else ""
    return {"experiment": f"slurp-native-stage3-{SIBLING_SLUG}{lo}-v1", "baseline": f"slurp-native-stage3-{SIBLING_SLUG}{lo}-baseline-v1"}


def fit_contact_cap(rows: int) -> int:
    """The FIT contact_cap the gate demands: rows x max_contacts x endpoints per contact (never run-cumulative)."""

    return rows * CEILING * FIT_ENDPOINTS_PER_CONTACT


def package_file(name: str) -> str:
    return f"{PACKAGE}/{name}"


def smoke_ids() -> list[str]:
    """The smoke population: the COMP-1b Fold A smoke fragment's own four ids (the roster prefix)."""

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
