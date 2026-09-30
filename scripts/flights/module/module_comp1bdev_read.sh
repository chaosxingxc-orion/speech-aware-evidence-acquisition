#!/bin/bash
# The module cell's read (COMP-1b as a module block on lock v2.1, DEV-2000-ADDED; migration step 6): a thin wrapper
# around the standard paired driver (scripts/flights/read_paired_cell.sh, owner decision 163), which resolves the arms
# from docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1/analysis-recipe-v1.json:
#   arms.arm                the module arm SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-V1
#   arms.in_chain_replicate the in-chain A/A SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1 (the module's OFF arm; GATING, vs-aa)
#   arms.comparator         the sealed DEV plan arm SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1 (CONTEXT ONLY)
# MODEL-FREE. The driver refuses before any score is opened unless the READ row
# SAEA-SLURP-STAGE3-MODULE-COMP1B-DEV2000-ADDED-PAIRED-ANALYSIS-V1 is ROOT COUNTERSIGNED (after both seals), and it
# never overwrites a pass directory that already holds files. The verdict is the coordinator's (decision 139).
#
#   bash scripts/flights/module/module_comp1bdev_read.sh [--passes vs-aa,vs-comparator] [--output-base DIR]
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
PKG=docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1
bash "$MAIN/scripts/flights/read_paired_cell.sh" "$PKG" "$@"
