#!/usr/bin/env bash
# T-NDL end-to-end: reproduces every number in report.md from the consumed traces.
# OFFLINE, CPU-only, ZERO model contact (owner ruling D5 archival replay).
set -euo pipefail

: "${TNDL_DIR:?set TNDL_DIR to the directory holding the T-NDL scripts}"
: "${REPO:?set REPO to the study repository root}"
: "${SPEECHRL_DATA_DIR:?set SPEECHRL_DATA_DIR}"
OUT="${TNDL_OUT:-$TNDL_DIR}"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$REPO/src"

RUNS="$SPEECHRL_DATA_DIR/runs"
LADDER="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-rladder-reads/report.json"
SALVAGE="$REPO/docs/checks/speech-aware-evidence-acquisition/2026-08-16-p2-r0bias-salvage/r0bias.entity-wer.json"

echo "### 0. canonicalizer + aligner self-test"
python -B "$TNDL_DIR/test_canon.py"

echo; echo "### 1. wrong-mention inventory, arm r1verify (headline)"
python -B "$TNDL_DIR/tndl_extract.py" \
  --outputs "$RUNS/SAEA-P2-r1verify/attempt-20260816T105836Z-b06529/SAEA-P2-r1verify.outputs.jsonl" \
  --reconcile-rladder "$LADDER" --arm r1verify \
  --out "$OUT/wrong_mentions_r1verify.jsonl"

echo; echo "### 2. wrong-mention inventory, arm r0bias (cross-arm control)"
python -B "$TNDL_DIR/tndl_extract.py" \
  --outputs "$RUNS/SAEA-P2-r0bias/attempt-20260816T002109Z-4e1f59/SAEA-P2-r0bias.outputs.jsonl" \
  --reconcile "$SALVAGE" --out "$OUT/wrong_mentions_r0bias.jsonl"

echo; echo "### 3. mention-level vs token-level error share"
python -B "$TNDL_DIR/tndl_tokenshare.py" "$OUT/wrong_mentions_r1verify.jsonl" r1verify
python -B "$TNDL_DIR/tndl_tokenshare.py" "$OUT/wrong_mentions_r0bias.jsonl" r0bias

echo; echo "### 4. three-way decomposition"
python -B "$TNDL_DIR/tndl_decompose.py" --wrong "$OUT/wrong_mentions_r1verify.jsonl" \
  --arm r1verify --out "$OUT/decomposition_r1verify.json"
python -B "$TNDL_DIR/tndl_decompose.py" --wrong "$OUT/wrong_mentions_r0bias.jsonl" \
  --arm r0bias --out "$OUT/decomposition_r0bias.json"

echo; echo "### 5. report tables"
python -B "$TNDL_DIR/tndl_tables.py" "$OUT/decomposition_r1verify.json" > "$OUT/tables_r1verify.md"
python -B "$TNDL_DIR/tndl_tables.py" "$OUT/decomposition_r0bias.json" > "$OUT/tables_r0bias.md"
echo "wrote $OUT/tables_r1verify.md and $OUT/tables_r0bias.md"
