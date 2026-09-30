#!/bin/bash
# The COMP-1b TEST-SAMPLE milestone read (owner decisions 151 and 202): a thin wrapper around the standard paired driver
# (scripts/flights/read_paired_cell.sh), pass vs-aa ONLY (left = MILESTONE-00-PLAN, the comparator the allowance
# prescribes). MODEL-FREE. The driver refuses before any score is opened unless the READ row
# SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-01-READ-V1 is ROOT COUNTERSIGNED (after both seals).
#
# Blocker 5 (registered facts): the driver's own 'natural_mixture' was the raw roster mean, which
# on this floored sample (per-intent floor of 5 prompts) is NOT the natural-mixture number
# (design note section 5). Fixed 2026-09-29: --weighting/--population-counts
# (scripts/analysis/stage3_paired_read.py, tested on fakes in tests/unit/test_stage3_paired_read.py)
# report raw, post-stratified and equal-stratum side by side and REFUSE to label the raw mean
# 'natural_mixture' on a roster the receipt declares floored; --weighting post-stratified selects
# the correct one here.
#
# POPULATION COUNTS: population-counts-v1.json (committed beside this script's package,
# $PKG/population-counts-v1.json) is the roster receipt's own per-intent full-test recording
# counts (docs/receipts/rosters/slurp-test-sample-3010-v1.json per_intent[*].test_recordings),
# extracted by scripts/analysis/build_population_counts.py -- never by reading the test split.
#
# STRATA SOURCE = scorer (coordinator ruling 2026-09-30). SLURP-TEST-SAMPLE-3010-V1 withholds its
# per-item stratum by design, its roster receipt allows gold only as "per-intent aggregate counts
# only; no label beside a sample id" (decision 141 item 5), and the allowance lets gold be read
# "ONLY by the official scorer, after delivery". A per-row gold bank is therefore NOT a legal
# channel (the draft SAEA-SLURP-TEST-SAMPLE-3010-GOLD-BANK-V1 row is not pursued). With
# --strata-source scorer the read runs the official-scoring step's --strata-inside-scorer mode
# (src/speech_aware_evidence_acquisition/core/scoring_strata.py) in its own process: it reads gold
# through the slurp-slu-official-test binding, stratifies by gold intent, runs the within-stratum
# bootstraps itself and writes ONE aggregate receipt (scorer-strata-aggregate.json: per-stratum
# n_h and per-arm intent-correct / TP / FP / FN totals, weighted deltas, CI95s, receipt hash). No
# per-row stratum and no file pairing a sample id with a gold field is ever written. This does not
# lift the first-contact gate (allowance first_contact_gate: status_at_signing NOT YET MET).
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
PKG=docs/readiness/2026-09-29-slurp-stage3-comp1b-testsample-v1
bash "$MAIN/scripts/flights/read_paired_cell.sh" "$PKG" --passes vs-aa \
  --strata-source scorer --population-counts "$PKG/population-counts-v1.json" \
  --weighting post-stratified \
  "$@"
