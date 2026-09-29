"""Shared identities of the phase-2 Perception-branch cells P-SV-1 and P-SV-2 (owner decisions 184, 186, 188).

Both cells are the retained AGREE arm (docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1) re-targeted
from TRAIN Fold A to TRAIN Fold B exactly the way the filler family re-pointed ROLL-2 + AGREE
(scripts/flights/filler/derive_filler_cells.py: the two speech-query pins, the agreement table, the dataset view,
the roster and the preparation receipts), with the program switched to the level-2 K = 3 fragment
``phase-native-candidates-review-revise-pbranch3-l2-v1`` (ceiling 15 = 11 + 2 (K - 1)) and a
``native_episode.roles.perception.branches`` block (rails/supply_variants.py ``parse_perception_branches``).

Imported by the derivation, the registration writer, the receipt minter and the fit measure. Constants only.
"""

from __future__ import annotations

import math

DATE = "2026-09-29"

AGREE = {
    "arm": {
        "baseline": "configs/baseline/slurp-native-stage3-agree-w1-fold-a-baseline-v1.json",
        "experiment": "configs/experiment/slurp-native-stage3-agree-w1-fold-a-v1.json",
        "experiment_id": "slurp-native-stage3-agree-w1-fold-a-v1",
    },
    "smoke": {
        "baseline": "configs/baseline/slurp-native-stage3-agree-w1-fold-a-smoke-4-baseline-v1.json",
        "experiment": "configs/experiment/slurp-native-stage3-agree-w1-fold-a-smoke-4-v1.json",
        "experiment_id": "slurp-native-stage3-agree-w1-fold-a-smoke-4-v1",
    },
}
AGREE_RUN = "SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1"
AGREE_ATTEMPT = "attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1"
AGREE_PACKAGE = "docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1"
FILLER_C01_BASELINE = "configs/baseline/slurp-native-stage3-filler-fold-b-c01-baseline-v1.json"

BASE_PROGRAM = "phase-native-candidates-review-revise-v1"
NEW_PROGRAM = "phase-native-candidates-review-revise-pbranch3-l2-v1"
BASE_CEILING, NEW_CEILING = 11, 15
LEVEL = 2
FIT_ENDPOINTS_PER_CONTACT = 4  # the AGREE arithmetic: contact_cap = rows x ceiling x 4
BASE_GPU_HOURS_ARM, SMOKE_GPU_HOURS = 12.0, 1.0

# TRAIN Fold B, the phase-2 read roster (coordinator ruling O2; owner decisions 184 and 186).
DATASET_FRAGMENT = "slurp-speech-native-evo-fold-b-1080"
SPLIT_ID = "SLURP-EVO-FOLD-B-V2"
ROSTER = {
    "arm": {
        "relpath": "docs/receipts/rosters/slurp-evo-fold-b-v2.json",
        "roster_id": "SLURP-EVO-FOLD-B-V2",
        "sha256": "47b89b9e33b1aed553ad94a1819acba6ac8837130ca546c33219d91a1ab944a8",
        "split_identity_hash": "4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a",
    },
    # The four-row form smoke reuses the committed four-row Fold B prefix receipt the filler family froze
    # (a prefix of Fold B rows, never a draw); structural form only, never scored.
    "smoke": {
        "relpath": "docs/receipts/rosters/slurp-stage3-filler-fold-b-c01-smoke-4-v1.json",
        "roster_id": "SLURP-STAGE3-FILLER-FOLD-B-C01-SMOKE-4-V1",
        "sha256": None,  # hashed at derivation
        "split_identity_hash": "bdd025a1f1c0a4a1ebd1b1204e7d3e781c3ae2543db7be324420f85171576e32",
    },
}
TUNING_ROSTER = "SLURP-EVO-FOLD-A-V2"
READ_ROSTER = "SLURP-EVO-FOLD-B-V2"

AGREEMENT = {
    "relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/agreement.jsonl",
    "sha256": "06990a86d20469c668ac4231990b49e5926d4771c9af8fbb13ae634b3ec21911",
    "receipt_relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1/receipt.json",
    "receipt_sha256": "90e127de43fb2d7db54de969363ce380b2804ea8d678582e144cd41b726e4844",
    "ledger_row": "SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-B-V1",
    "inputs_readme": "docs/readiness/2026-09-28-slurp-fold-b-phase2-inputs-v1/README.md",
}
FOLD_A_AGREEMENT = {
    "relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/agreement.jsonl",
    "receipt_relpath": "prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-FOLD-A-V1/receipt.json",
}
FOLD_A_ALIAS = "prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-A-ALIAS-V1/query-dimension-alias.json"
FOLD_B_ALIAS = {
    "relpath": "prepared/SAEA-SLURP-INTENT-BOUNDARY-TRAIN-FOLD-B-ALIAS-V1/query-dimension-alias.json",
    "sha256": "78de8aa2d30afab442d286b1a14919e1dfc031f79b007f62b3eebd747a9d0ea0",
}
FOLD_B_ENCODE_RECEIPT = {
    "relpath": "preparation-runs/SAEA-SLURP-TFRL-FOLD-B-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json",
    "sha256": "583d37669b3a8275be6a244454e21ebd7b5fbe1fd90af2b73f251d86bf7d00eb",
}
FOLD_B_CONTENT_PROVENANCE = {
    "relpath": "vectors/slurp-stage3-filler-fold-b-v1/query-vectors-speech-content-v1.provenance.json",
    "sha256": "6a6d0d0ff8312abb6ccd2de8e1ecce9355e8bd0b5d0f1abc5c7ce89b47f4802c",
}

SESSION = "serving-slurp-native-candidate-five-train-a-np4-v1"
SCORER = "slurp-slu-official-train"
MEASUREMENT_DESIGN = "same-flight-perception-variant"  # the spelling the gates register (see README)
SPEC = "docs/superpowers/specs/2026-09-28-same-flight-instrument-phase2-perception-variants-design.md"
NODE_LEDGER = "docs/results/2026-09-28-slurp-node-information-gain-ledger.md"
OWNER_DECISIONS = "docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md"
INSTRUMENT = "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md"
GATE = "scripts/checks/stage3_effect_floor_check.py"
READ_ANALYSIS = "scripts/analysis/slurp_perception_branch_read.py"

FIT_MEASURE = "analysis/SAEA-SLURP-STAGE3-PSV-PERCEPTION-FIT-MEASURE-V1/fit-measure-v1.json"

# The contrast-pair table top2-contrast-v1 renders from (spec section 5 item 6). Built model-free by
# scripts/build_slurp_intent_contrast_pairs.py, which has NOT landed on the phase-2 branch at registration.
CONTRAST_PAIR_PLACEHOLDER = "TO-BE-PINNED-AFTER-CONTRAST-PAIR-BUILD"
CONTRAST_PAIR_BUILDER = "scripts/build_slurp_intent_contrast_pairs.py"

ARM_A, ARM_T = "a-agree", "t-twin"

# Fold A node-ledger numbers (docs/results/2026-09-28-slurp-node-information-gain-ledger.md, AGREE arm, 1,080 rows).
LEDGER_ROWS = 1080
RANK2_WRONG_ROWS = 42        # wrong delivered rows with gold at Perception rank 2
RANK2_ALL_ROWS = 63          # every row with gold at Perception rank 2 (17 of them converted)
IN_BLOCK_DROPPED_ROWS = 49   # wrong rows with gold in the boundary block but off Perception's list
CONVERSION = {"rank1": 97.57, "rank2": 26.98, "rank3": 12.0}


def pp(rows: int, n: int = LEDGER_ROWS) -> float:
    return round(100.0 * rows / n, 2)


CELLS = {
    "psv1": {
        "label": "P-SV-1",
        "slug": "psv1-fold-b",
        "run": "SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1",
        "b_branch": "b-top2contrast",
        "b_axis": {"presentation_id": "top2-contrast-v1"},
        "primary_metric": (
            "official intent accuracy of the level-2 branch Solver column (primary): B (top2-contrast-v1) minus A, "
            "with gold-on-list and gold rank in the branch note beside; guard SLU-F1 of the same column; the "
            "delivered row is A and identical by construction at the request level (reported, never contrasted)"
        ),
        "ceiling_rows": RANK2_WRONG_ROWS,
        "question": (
            "At the one Perception visit of every TRAIN Fold B row, does rendering the branch's rank-1/rank-2 "
            "candidate pair as a top-2 contrast block (top2-contrast-v1) move the level-2 branch Solver column's "
            "official intent accuracy beyond the in-flight twin's null, read against the delivering branch A (AGREE's "
            "Perception evidence as flown) in the same flight?"
        ),
    },
    "psv2": {
        "label": "P-SV-2",
        "slug": "psv2-fold-b",
        "run": "SAEA-SLURP-STAGE3-PSV2-FOLD-B-V1",
        "b_branch": "b-list3",
        "b_axis": {"min_candidates": 3},
        "primary_metric": (
            "gold-on-list (present) in the branch Perception note (primary, a presence measurement; coordinator "
            "ruling O4): B (min_candidates 3) minus A; official intent accuracy of the level-2 branch Solver column "
            "reported beside, never gating; gold rank and list size beside"
        ),
        "ceiling_rows": IN_BLOCK_DROPPED_ROWS,
        "question": (
            "At the one Perception visit of every TRAIN Fold B row, does forcing a three-candidate hypothesis list "
            "(response-contract min_candidates 3) raise the share of rows whose gold intent is on Perception's list "
            "beyond the in-flight twin's null, read against the delivering branch A in the same flight, and what does "
            "the level-2 branch Solver make of the widened list?"
        ),
    },
}


def names(key: str, kind: str) -> dict:
    """Every id of one cell ('psv1'|'psv2') and kind ('arm'|'smoke')."""

    c = CELLS[key]
    slug = c["slug"]
    upper = slug.upper()
    smoke = kind == "smoke"
    sfx_lower = "-smoke-4" if smoke else ""
    sfx_upper = "-SMOKE-4" if smoke else ""
    return {
        "experiment": f"slurp-native-stage3-{slug}{sfx_lower}-v1",
        "baseline": f"slurp-native-stage3-{slug}{sfx_lower}-baseline-v1",
        "run_id": f"SAEA-SLURP-STAGE3-{upper}{sfx_upper}-V1",
        "fit_run_id": f"SAEA-SLURP-STAGE3-{upper}{sfx_upper}-FIT-V1",
        "attempt_id": f"attempt-slurp-native-stage3-{slug}{sfx_lower}-generation-v1",
        "fit_attempt_id": f"attempt-slurp-native-stage3-{slug}{sfx_lower}-fit-v1",
        "fragment_kind": f"saea-slurp-native-stage3-{slug}{sfx_lower}-v1",
        "package": f"docs/readiness/{DATE}-slurp-stage3-{slug}-v1",
        "pkg": f"slurp-stage3-{slug}-v1",
        "prereg": f"docs/readiness/{DATE}-slurp-stage3-{slug}-v1-preregistration.md",
        "campaign": f"configs/campaign/slurp-native-stage3-{slug}-v1.json",
        "read_run": f"SAEA-SLURP-STAGE3-{upper}-BRANCH-READ-V1",
        "decision_id": f"slurp-stage3-{slug}-admission-v1",
        "decision_relpath": f"coordination/slurp-stage3-{slug}-v1/root-admission-v1.json",
    }


def gpu_hours(kind: str) -> float:
    if kind == "smoke":
        return SMOKE_GPU_HOURS
    return round(BASE_GPU_HOURS_ARM * NEW_CEILING / BASE_CEILING, 1)


def speech_cap(audio: float) -> int:
    return math.ceil(audio * NEW_CEILING - 1e-9)
