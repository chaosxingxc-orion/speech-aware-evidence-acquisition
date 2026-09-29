#!/bin/bash
# Cell COMP-1b's read: a thin wrapper around the standard paired driver
# (scripts/flights/read_paired_cell.sh, owner decision 163), which resolves the arms straight from
# docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1/analysis-recipe-v1.json:
#   arms.arm               the COMP-1b arm SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1
#   arms.in_chain_replicate the EXISTING SEALED in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 cell
#                            COMP-1 already flew -- the GATING pass (vs-aa), reused cross-flight, never
#                            re-flown or re-pinned by this family (owner decision 160's shared-A/A pattern)
#   arms.comparator          cell COMP-1's own cited arm SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1 -- CONTEXT ONLY
#                            (vs-comparator), never the bar: shows directly whether removing the citation
#                            contract closed the gap the 2026-09-29 attribution note predicted
# MODEL-FREE: zero model / tokenizer / encoder / scorer / server contacts; the driver refuses before any
# score is opened unless the READ row SAEA-SLURP-STAGE3-COMP1B-FOLD-A-PAIRED-ANALYSIS-V1 is ROOT
# COUNTERSIGNED, and it never overwrites a pass directory that already holds files.
#
#   bash scripts/flights/comp1/comp1b_read.sh [--passes vs-aa,vs-comparator] [--output-base DIR]
#
# The driver writes DESCRIPTIVE numbers; the verdict is the coordinator's and its disposition is taken with
# the owner in conversation (decision 139). No utterance text, gold, transcript or model output is printed
# or persisted.
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
PKG=docs/readiness/2026-09-29-slurp-stage3-comp1b-fold-a-v1
bash "$MAIN/scripts/flights/read_paired_cell.sh" "$PKG" "$@"
