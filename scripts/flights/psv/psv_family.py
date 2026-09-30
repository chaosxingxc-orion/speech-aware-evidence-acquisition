"""Shared identities of the phase-2 Perception-branch cells P-SV-1, P-SV-2 and P-SV-3 (owner decisions 184, 186,
188; P-SV-3 registered separately on branch fable/psv3, decision 190's `present`-primary framing extended to a
third axis: the boundary-supply DEPTH itself, fuse_coverage.m/top_l raised together) and P-SV-4 (2026-09-30, branch
fable/keysource: the key_source axis, the K6p centred centroid + agreement key; intent-primary, claims_benefit).

Every cell is the retained AGREE arm (docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1) re-targeted
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
# P-SV-4 (2026-09-30): the fit re-measured with the key_source bound added (psv_fit_measure.py), written to its OWN
# file so the v1 measure the already-registered P-SV-1..3 packages pin is never overwritten.
FIT_MEASURE_V2 = "analysis/SAEA-SLURP-STAGE3-PSV-PERCEPTION-FIT-MEASURE-V1/fit-measure-v2.json"


def fit_measure_relpath(key: str) -> str:
    """The fit-measure file a cell's branch bounds come from (P-SV-4 on: v2)."""

    return CELLS[key].get("fit_measure", FIT_MEASURE)


# P-SV-4's key_source axis (rails/supply_variants.py PerceptionBranchKeySource; docs/results/2026-09-30-slurp-
# retrieval-key-recall-offline.md): the K6p centred centroid key and the centred TRAIN Fold B speech queries, both
# zero-contact prepared artifacts (scripts/build_slurp_centred_centroid_key.py, scripts/build_slurp_centred_query_
# vectors.py --roster fold-b); the agreement table is UNCHANGED (agreement_source null = keep the cell's own pin).
K6P_NOTE = "docs/results/2026-09-30-slurp-retrieval-key-recall-offline.md"
K6P_PROOF = {"script": "scripts/analysis/slurp_k6p_artifact_proof.py",
             "relpath": "analysis/SAEA-SLURP-K6P-ARTIFACT-PROOF-V1/proof.json",
             "sha256": "ad34e12fcafb2c762abe8cb4c695932671d4a242875b8ec9e9f7926a8be1db05",
             "fold_b": {"rank1_k6p": 815, "rank1_cent_agree": 789, "in_block_k6p": 1029, "in_block_cent_agree": 1027},
             "fold_a": {"rank1_k6p": 845, "rank1_cent_agree": 823, "in_block_k6p": 1040, "in_block_cent_agree": 1048}}
K6P_KEY = {
    "relpath": "prepared/SAEA-SLURP-CENTRED-CENTROID-KEY-V1/key-v1.jsonl",
    "sha256": "98533f8254703d24a033d3f07a11a4fef5e0950fc033fcbee5eb56e200db074c",
    "receipt_relpath": "prepared/SAEA-SLURP-CENTRED-CENTROID-KEY-V1/receipt.json",
    "receipt_sha256": "dfded181469703612dcd233a44eea9b7b320b964d165d80ea6a5c106b07ec40d",
    "ledger_row": "SAEA-SLURP-CENTRED-CENTROID-KEY-BUILD-V1",
    "builder": "scripts/build_slurp_centred_centroid_key.py",
}
K6P_QUERIES_FOLD_B = {
    "relpath": "prepared/SAEA-SLURP-CENTRED-QUERIES-V1/fold-b/query-vectors-speech-segments.jsonl",
    "sha256": "6b056fefd042c5b9d7841ecc425d4c875029f8679c2291c3902b406031a9cefb",
    "receipt_relpath": "prepared/SAEA-SLURP-CENTRED-QUERIES-V1/fold-b/receipt.json",
    "receipt_sha256": "f2e8d7ce99ac8d4c03b7b0ace9e9501ec708e223da50e9a9c1db29a288218d5e",
    "ledger_row": "SAEA-SLURP-CENTRED-QUERIES-FOLD-B-BUILD-V1",
    "builder": "scripts/build_slurp_centred_query_vectors.py --roster fold-b",
}


def k6p_key_source() -> dict:
    """The b-k6p branch's ``key_source`` block: facet_source and query_source swapped, agreement unchanged."""

    return {
        "store_id": "intent-boundaries",
        "facet_source": {
            "kind": "sealed-vectors", "relpath": K6P_KEY["relpath"], "sha256": K6P_KEY["sha256"],
            "tool_contact_ledger_row": K6P_KEY["ledger_row"],
            "embedded_signal": (
                "text: the CENTRED intent-boundary centroid key (K6p) -- per released intent the raw mean of its "
                "unit construction-pool utterance vectors minus the construction-pool mean, re-normalised; built "
                "model-free by scripts/build_slurp_centred_centroid_key.py from pinned vectors only; the key side is "
                "knowledge text."),
        },
        "query_source": {
            "kind": "sealed-segment-vectors", "relpath": K6P_QUERIES_FOLD_B["relpath"],
            "sha256": K6P_QUERIES_FOLD_B["sha256"], "tool_contact_ledger_row": K6P_QUERIES_FOLD_B["ledger_row"],
            "embedded_signal": (
                "speech: the TRAIN Fold B rows' own sealed full-utterance speech segments in the intent-boundary "
                "dimension, each unit-normalised and centred by the mean of the pinned R01C construction-roster "
                "speech queries, re-normalised (scripts/build_slurp_centred_query_vectors.py --roster fold-b); no "
                "transcript, answer, gold label or future turn enters this query."),
        },
        "agreement_source": None,
    }

# The contrast-pair table top2-contrast-v1 renders from (spec section 5 item 6). Built model-free by
# scripts/build_slurp_intent_contrast_pairs.py. History: registered as a placeholder at first registration
# (2026-09-28); pinned to the nearest-rival V1 table (3ee765f34, 48 pairs); hand-pinned on the b-top2contrast branch
# (d09dded8e) and re-pinned to the all-pairs V2 table under ruling O7 (11ed00ea9). CONTRAST_PAIR_TABLE below is the
# V2 pin, so a re-run of derive_slurp_psv_cells.py / write_slurp_psv_registration.py reproduces the branch's
# ``contrast_pairs {relpath, sha256}`` and the registered facts instead of regressing to V1 or the placeholder.
# CONTRAST_PAIR_PLACEHOLDER stays defined only for the refusal guards (psv_mint_receipt.py, psv_flip.sh).
CONTRAST_PAIR_PLACEHOLDER = "TO-BE-PINNED-AFTER-CONTRAST-PAIR-BUILD"
CONTRAST_PAIR_BUILDER = "scripts/build_slurp_intent_contrast_pairs.py"
CONTRAST_PAIR_BUILDER_ARGS = "--pair-scope all-pairs"
CONTRAST_PAIR_RULING = "O7"
CONTRAST_PAIR_TABLE = {
    "table_relpath": "prepared/SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2/table-v1.json",
    "sha256": "0d74fdb6aae70bff82abbd52355fe34b58cf646fe36a80016220ba1e714a7e34",
    "receipt_relpath": "docs/receipts/knowledge/slurp-perception-contrast-pairs-v2.json",
    "receipt_sha256": "c6fd04260b00ec6fdfaebd0e5ecc1a5f1edcb76ac30f06dbeaf08c1c0b437ac8",
    "artifact_id": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2",
    "exposure_ledger_row": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-BUILD-V2",
    "pinned_date": "2026-09-29",
    "pairs_considered": 1770,
    "pairs_written": 1710,
    "pairs_skipped": 60,
}
# The superseded nearest-rival V1 pin (unchanged on disk; content-verified by the builder's --check).
CONTRAST_PAIR_TABLE_V1 = {
    "table_relpath": "prepared/SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V1/table-v1.json",
    "sha256": "19bf2487cf6821ed55ceb123532f738f5c82cc51f63a17bc11d88ca37e495059",
    "receipt_relpath": "docs/receipts/knowledge/slurp-perception-contrast-pairs-v1.json",
    "receipt_sha256": "4af9e874dea15f5846034ceaff9fbc15b6ba555b81fa959e7a96bf5f6f59a368",
    "artifact_id": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V1",
    "pinned_date": "2026-09-28",
    "pairs_considered": 50,
    "pairs_written": 48,
    "pairs_skipped": 2,
}
# scripts/analysis/slurp_contrast_pair_coverage.py against the P-SV-1 b-top2contrast seed (1,078 rows with a seed).
CONTRAST_PAIR_COVERAGE = {
    "coverage_script": "scripts/analysis/slurp_contrast_pair_coverage.py",
    "seed": "prepared/SAEA-SLURP-STAGE3-PSV1-FOLD-B-V1/perception-branch-seeds-v1.json",
    "branch": "b-top2contrast",
    "rows_total": 1078,
    "v1_nearest_rival": {
        "artifact_id": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V1",
        "rows_hit": 415, "rows_no_table_row": 662, "rows_fewer_than_two_intents": 1,
        "coverage_fraction": "415/1078 (38.5%)",
    },
    "v2_all_pairs": {
        "artifact_id": "SAEA-SLURP-PERCEPTION-CONTRAST-PAIRS-V2",
        "rows_hit": 1035, "rows_no_table_row": 42, "rows_fewer_than_two_intents": 1,
        "coverage_fraction": "1035/1078 (96.0%)",
        "note": ("the 42 residual no-table-row rows all land on the same 2 pairs O5's own pool-support floor still skips "
                 "in V2 (cooking_query/cooking_recipe, iot_hue_lightoff/iot_hue_lighton) -- the identical 2 of 60 that "
                 "were pool-support-skipped nearest-rival pairs too"),
    },
}


def contrast_pairs_pin() -> dict:
    """The ``contrast_pairs {relpath, sha256}`` pin the b-top2contrast branch carries (data-root relpath)."""

    return {"relpath": CONTRAST_PAIR_TABLE["table_relpath"], "sha256": CONTRAST_PAIR_TABLE["sha256"]}


ARM_A, ARM_T = "a-agree", "t-twin"


def branch_seed_relpath(key: str, kind: str) -> str:
    """The ``prepared/<run-id>/perception-branch-seeds-v1.json`` relpath this
    cell's non-A/T (B) branch pins as ``prepared_seed`` once
    ``core.flight.cli prepare-branch-seeds`` has produced it (design section
    5 item 4; the item-4 GAP)."""

    return f"prepared/{names(key, kind)['run_id']}/perception-branch-seeds-v1.json"

# Fold A node-ledger numbers (docs/results/2026-09-28-slurp-node-information-gain-ledger.md, AGREE arm, 1,080 rows).
LEDGER_ROWS = 1080
RANK2_WRONG_ROWS = 42        # wrong delivered rows with gold at Perception rank 2
RANK2_ALL_ROWS = 63          # every row with gold at Perception rank 2 (17 of them converted)
IN_BLOCK_DROPPED_ROWS = 49   # wrong rows with gold in the boundary block but off Perception's list (section 1.4)
OUT_OF_BLOCK_DROPPED_ROWS = 34  # wrong rows with gold absent from the boundary block entirely (section 1.4)
# section 1.4 "gold absent from the Perception list": 83 = 49 (in block) + 34 (outside it); the whole P-SV-3 ceiling.
OFF_LIST_DROPPED_ROWS = IN_BLOCK_DROPPED_ROWS + OUT_OF_BLOCK_DROPPED_ROWS
CONVERSION = {"rank1": 97.57, "rank2": 26.98, "rank3": 12.0}

# P-SV-3's boundary-supply-depth axis (rails/supply_variants.py PERCEPTION_BRANCH_KNOB_TAILS: ("fuse_coverage",
# "m") and ("fuse_coverage", "top_l")). The store the AGREE Perception phase_supply reads and the program's first
# phase, needed to build a branch's ``overrides`` knob paths (``knowledge_stores.<store>.phase_supply.<phase>.
# fuse_coverage.<leaf>``, rails/supply_variants.py::parse_perception_branch_knob).
BOUNDARY_STORE_ID = "intent-boundaries"
FIRST_PHASE_ID = "perception"
# The "boundary_phase_supply +1 step" knob the sealed-credit inner loop lists as unobserved
# (configs/analysis/sealed-credit-policy-space-v1.json, node "perception_seed", flown_value "as flown (8
# entries)"): fuse_coverage.m and fuse_coverage.top_l raised TOGETHER (c stays 1), one branch axis
# (rails/supply_variants.py::parse_perception_branches counts the whole ``knobs`` tuple as exactly one axis
# category regardless of how many knob paths it carries). Raising only one of the two leaves the delivered count
# unchanged: ``core/flight/runtime.py`` (the ``value_width = min(spec.k, spec.fuse_knobs().top_l)`` note) and
# ``rails/kb_policy.py::fuse_associated_values_factory`` show the fuser scans only the top ``m`` ranked facets
# (``rank_result.candidates[:resolved.m]``) and stops once ``len(selected) == resolved.top_l``, so with m == top_l
# == 8 (AGREE, as flown) the delivered count is saturated by BOTH bounds at once.
BOUNDARY_DEPTH_NEW_TOP_L = 12


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
    "psv3": {
        "label": "P-SV-3",
        "slug": "psv3-fold-b",
        "run": "SAEA-SLURP-STAGE3-PSV3-FOLD-B-V1",
        "b_branch": "b-depth",
        # ONE axis (a boundary-supply knob, design section 1): fuse_coverage.m and fuse_coverage.top_l raised
        # together from the AGREE-as-flown 8 to BOUNDARY_DEPTH_NEW_TOP_L (12); c stays 1. branches_block() below
        # turns this into the branch's ``overrides`` knob paths.
        "b_axis": {"fuse_coverage": {"m": BOUNDARY_DEPTH_NEW_TOP_L, "top_l": BOUNDARY_DEPTH_NEW_TOP_L}},
        "primary_metric": (
            "gold-on-list (present) in the branch Perception note (primary, a presence measurement; owner decision "
            "190's ruling-O4 framing extended to this axis): B (fuse_coverage.m and fuse_coverage.top_l raised "
            "together 8 -> 12, c unchanged at 1 -- the boundary-supply DEPTH itself, the inner loop's "
            "'boundary_phase_supply +1 step') minus A; official intent accuracy of the level-2 branch Solver column "
            "reported beside, never gating; gold rank and list size beside"
        ),
        "ceiling_rows": OFF_LIST_DROPPED_ROWS,
        "question": (
            "At the one Perception visit of every TRAIN Fold B row, does raising the boundary-supply depth itself "
            "(fuse_coverage.m and fuse_coverage.top_l together, 8 -> 12, c unchanged) raise the share of rows whose "
            "gold intent is on Perception's list beyond the in-flight twin's null, read against the delivering "
            "branch A in the same flight, and what does the level-2 branch Solver make of the widened supply?"
        ),
    },
    # P-SV-4 (2026-09-30): the key_source axis. B re-keys the boundary retrieval with K6p (the centred centroid key
    # + the centred Fold B speech queries; agreement unchanged, w_cos / w_agree 1 / 1 as flown, fuse 8/1/8), a
    # rank-quality lever: the recall note's implied effect is a RANK effect (gold lifted to block rank 1), so the
    # primary is the level-2 branch Solver column's official intent, with `present` beside.
    "psv4": {
        "label": "P-SV-4",
        "slug": "psv4-fold-b",
        "date": "2026-09-30",
        "run": "SAEA-SLURP-STAGE3-PSV4-FOLD-B-V1",
        "b_branch": "b-k6p",
        "b_axis": {"key_source": "k6p (centred centroid key + centred Fold B speech queries; agreement unchanged)"},
        "fit_measure": FIT_MEASURE_V2,
        "expected_effect_pp": 1.1,
        "claims_benefit": True,
        "primary_metric_key": "intent",
        "implied_intent_rows_fold_b": 11.6,
        "rank1_lift_rows_fold_b": 26,
        "primary_metric": (
            "official intent accuracy of the level-2 branch Solver column (primary): B (key_source K6p: the centred "
            "centroid key and the centred Fold B speech queries, agreement unchanged) minus A, with gold-on-list "
            "(present) and gold rank in the branch note beside; guard SLU-F1 of the same column; the delivered row is "
            "A and identical by construction at the request level (reported, never contrasted)"
        ),
        "ceiling_rows": 26,
        "question": (
            "At the one Perception visit of every TRAIN Fold B row, does re-keying the boundary retrieval with K6p (the "
            "centred centroid key and the centred speech queries, agreement unchanged -- a key_source swap inside the "
            "branch's own pre-flight router, nothing else) move the level-2 branch Solver column's official intent "
            "accuracy beyond the in-flight twin's null, read against the delivering branch A (AGREE's Perception "
            "evidence as flown) in the same flight?"
        ),
    },
}


def cell_date(key: str) -> str:
    """A cell's registration date (package and preregistration paths): P-SV-1..3 2026-09-29, P-SV-4 2026-09-30."""

    return CELLS[key].get("date", DATE)


def names(key: str, kind: str) -> dict:
    """Every id of one cell ('psv1'|'psv2'|'psv3') and kind ('arm'|'smoke')."""

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
        "package": f"docs/readiness/{cell_date(key)}-slurp-stage3-{slug}-v1",
        "pkg": f"slurp-stage3-{slug}-v1",
        "prereg": f"docs/readiness/{cell_date(key)}-slurp-stage3-{slug}-v1-preregistration.md",
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
