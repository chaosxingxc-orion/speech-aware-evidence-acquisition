#!/bin/bash
# The COMP-1b TEST-SAMPLE milestone read (owner decisions 151 and 202): a thin wrapper around the standard paired driver
# (scripts/flights/read_paired_cell.sh), pass vs-aa ONLY (left = MILESTONE-00-PLAN, the comparator the allowance
# prescribes). MODEL-FREE. The driver refuses before any score is opened unless the READ row
# SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-READ-V1 is ROOT COUNTERSIGNED (after both seals).
#
# Blocker 5 (registered facts): the driver's own 'natural_mixture' was the raw roster mean, which
# on this floored sample (per-intent floor of 5 prompts) is NOT the natural-mixture number
# (design note section 5). Fixed 2026-09-29: --weighting/--strata-key/--strata-source/
# --population-counts (scripts/analysis/stage3_paired_read.py, tested on fakes in
# tests/unit/test_stage3_paired_read.py) report raw, post-stratified and equal-stratum side by
# side and REFUSE to label the raw mean 'natural_mixture' on a roster the receipt declares
# floored; --weighting post-stratified selects the correct one here.
#
# POPULATION COUNTS: population-counts-v1.json (committed beside this script's package,
# $PKG/population-counts-v1.json) is the roster receipt's own per-intent full-test recording
# counts (docs/receipts/rosters/slurp-test-sample-3010-v1.json per_intent[*].test_recordings),
# extracted by scripts/analysis/build_population_counts.py -- never by reading the test split.
#
# STRATA SOURCE: SLURP-TEST-SAMPLE-3010-V1 withholds its per-item stratum by design
# (stratum_withheld_per_item: revealing a row's own gold intent would reveal the correct
# intent-classification answer), so --strata-source is gold-bank, not the roster's own items --
# the same offline gold-bank channel --delivery already reads. REMAINING PREREQUISITE (found
# 2026-09-29, not yet in the blockers list): the gold bank's --gold-bank-roster block named below
# does not exist yet for this roster and must be built offline, gold-side, under decision 141 item
# 5 (exactly how the roster receipt's own per-intent aggregates were built), before this read can
# produce an AVAILABLE per-scenario table; the block name is this script's own choice, not yet
# ratified. This is independent of, and does not lift, the first-contact gate (allowance
# first_contact_gate: status_at_signing NOT YET MET).
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
PKG=docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1
bash "$MAIN/scripts/flights/read_paired_cell.sh" "$PKG" --passes vs-aa \
  --strata-source gold-bank --strata-key gold_intent --gold-bank-roster slurp-test-sample-3010 \
  --weighting post-stratified --population-counts "$PKG/population-counts-v1.json" \
  "$@"
