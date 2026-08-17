#!/usr/bin/env bash
# N1 re-run end-to-end: reproduces every number in report.md.
# OFFLINE, CPU-only, ZERO model contact (owner ruling D5 archival replay).
#
# Requires in the environment:
#   N1_DIR   this directory
#   TNDL     the committed 2026-08-17-tndl-decomposition bundle (imported, not copied)
#   REPO     study repository root
#   SPEECHRL_DATA_DIR
#   TNDL_WRONG  directory holding wrong_mentions_{r1verify,r0bias}.jsonl, regenerated
#               by the T-NDL bundle's own run_tndl.sh (not committed: they carry
#               gold mention text and hypothesis text)
set -euo pipefail

: "${N1_DIR:?}" ; : "${TNDL:?}" ; : "${REPO:?}" ; : "${SPEECHRL_DATA_DIR:?}" ; : "${TNDL_WRONG:?}"
OUT="${N1_OUT:-$N1_DIR}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"
export TNDL

R1_ATT=attempt-20260816T105836Z-b06529
R0_ATT=attempt-20260816T002109Z-4e1f59

echo "### 1. surviving true-wrong inventory (FORMAT removed)"
python -B "$N1_DIR/n1_truewrong.py" --wrong "$TNDL_WRONG/wrong_mentions_r1verify.jsonl" \
  --arm r1verify --out "$OUT/truewrong_r1verify.jsonl"
echo
python -B "$N1_DIR/n1_truewrong.py" --wrong "$TNDL_WRONG/wrong_mentions_r0bias.jsonl" \
  --arm r0bias --out "$OUT/truewrong_r0bias.jsonl"

echo; echo "### 2. reference-token -> absolute audio time"
python -B "$N1_DIR/mkdur.py"
python -B "$N1_DIR/n1_timemap.py" \
  --calls 4330115 4365024 4365948 4366429 4366522 4384964 4385072 4387383 4389907 4397829 \
  --durations "$OUT/durations.json" --out "$OUT/timemap.json"

echo; echo "### 3. routing metrics + counterfactual ladder (headline arm)"
python -B "$N1_DIR/n1_routing.py" --truewrong "$OUT/truewrong_r1verify.jsonl" \
  --allwrong "$TNDL_WRONG/wrong_mentions_r1verify.jsonl" --timemap "$OUT/timemap.json" \
  --arm SAEA-P2-r1verify --attempt "$R1_ATT" --out "$OUT/n1_r1verify.json"

echo; echo "### 4. cross-arm control"
python -B "$N1_DIR/n1_routing.py" --truewrong "$OUT/truewrong_r0bias.jsonl" \
  --allwrong "$TNDL_WRONG/wrong_mentions_r0bias.jsonl" --timemap "$OUT/timemap.json" \
  --arm SAEA-P2-r0bias --attempt "$R0_ATT" --out "$OUT/n1_r0bias.json"
