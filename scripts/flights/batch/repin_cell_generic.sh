#!/bin/bash
# Flip ONE registered cell (smoke or arm) to ready on master with the re-pin tool, commit, then check on the clean tree.
# Parameterised by environment (set by the caller, e.g. rprim_flip_both.sh):
#   RD        readiness dir (repo-relative), e.g. docs/readiness/2026-09-22-slurp-review-primitives-v1
#   CELL      cell id, e.g. slurp-native-review-primitives-smoke-4-v1; EXP the experiment id when it differs (default CELL)
#   PKG       package name, e.g. slurp-review-primitives-v1
#   PREREG    preregistration note (repo-relative)
#   DEC_PATH  decision receipt relpath under the data root; DEC_ID its decision id
#   TAG       short tag for the out/err files, e.g. rprim-smoke; ARM=1 marks the 1,080-row arm (records the flight commit, runs the summary)
#   MSG       commit message file; ALLOW_OUTPUT_CHANGE=1 passes --allow-output-change (a re-pin whose prepared supply legitimately changes, e.g. a roster narrowing)
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PY=/home/chao/.venvs/speechrl/bin/python
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd "$MAIN" || exit 1
echo "== HEAD $(git rev-parse --short HEAD); tracked dirt: $(git status --short | grep -vc '^??')"
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$MAIN" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment "${EXP:-$CELL}" --cell "$CELL" --readiness-dir "$RD" --package-name "$PKG" --preregistration "$PREREG" \
  --decision "$DEC_PATH" --decision-id "$DEC_ID" \
  --set-ready ${ALLOW_OUTPUT_CHANGE:+--allow-output-change} > /home/chao/$TAG-repin-cell.out 2> /home/chao/$TAG-repin-cell.err
echo "repin exit $? (1 = its internal check refused the dirty tree, expected)"
grep -o "has uncommitted changes" /home/chao/$TAG-repin-cell.err | head -1
grep -o "Error[A-Za-z]*: [^\\\\]*" /home/chao/$TAG-repin-cell.err | grep -v "uncommitted" | head -2 | cut -c1-200
echo "== changed"; git status --short | head -20
git add "configs/experiment/${EXP:-$CELL}.json" configs/baseline docs/exposure-ledger.md "$PREREG" "$RD/"
git commit -q -F "$MSG" && echo "committed $(git rev-parse --short HEAD)" || { echo "COMMIT FAILED"; exit 4; }
echo "tracked dirt after commit: $(git status --short | grep -vc '^??')"
if [ "$ARM" = "1" ]; then
  git rev-parse HEAD > /home/chao/$TAG-flight-commit.txt
  CK=$DATA/coordination/$PKG/check-$CELL-ready-v1.json
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root "$MAIN" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" --experiment "${EXP:-$CELL}" --cell "$CELL" > "$CK" 2>/home/chao/$TAG-check.err || { echo "check FAILED"; tail -4 /home/chao/$TAG-check.err | cut -c1-300; exit 5; }
  $PY -B $SP/b1_check_summary.py "$CK" "$MAIN/$RD/protocol-registered-v1.json"
  $PY scripts/checks/results_ledger_check.py 2>&1 | tail -1
fi
