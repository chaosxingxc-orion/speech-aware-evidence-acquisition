#!/bin/bash
# The COMP-1b TEST-SAMPLE milestone read (owner decisions 151 and 202): a thin wrapper around the standard paired driver
# (scripts/flights/read_paired_cell.sh), pass vs-aa ONLY (left = MILESTONE-00-PLAN, the comparator the allowance
# prescribes). MODEL-FREE. The driver refuses before any score is opened unless the READ row
# SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-READ-V1 is ROOT COUNTERSIGNED (after both seals). BEFORE countersigning, the
# post-stratified natural-mixture weighting (registered facts, blocker 5) must be in the read path: the driver's own
# 'natural_mixture' block is the raw roster mean, which on this floored sample is NOT the natural-mixture number.
# A milestone read is development evidence under owner decision 28, never a test claim.
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
PKG=docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1
bash "$MAIN/scripts/flights/read_paired_cell.sh" "$PKG" --passes vs-aa "$@"
