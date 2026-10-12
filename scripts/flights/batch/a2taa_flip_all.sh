#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip cell A2T-AA (the four-row smoke, pass A and pass B) to ready on master at ONE commit: model-free.
# Root runs this AFTER minting coordination/a2t-stage3-aa-paired-400-v1/root-admission-v1.json
# (decision id a2t-stage3-aa-paired-400-admission-v1) with the six eligible run ids
# SAEA-A2T-STAGE3-AA-PAIRED-400-SMOKE-4-V1 / -SMOKE-4-FIT-V1 / -A-V1 / -A-FIT-V1 / -B-V1 / -B-FIT-V1
# and this package's caps (smoke 4 / 13 / 21 s / 0.2 GPU-h; each pass 400 / 1201 / 2761 s / 0.5 GPU-h).
# ONE repin_cell.py call over the three cells, so the shared protocol document and every plan sha of the
# package are rewritten once and no sibling's row is left quoting a superseded hash (the per-cell flip
# loop rewrites only the selected cell's rows). The program has no supplied first phase (item E38): the
# re-pin creates no prepared artifact and no preparation requirement; --allow-output-change is never passed.
# Per-cell env files (a2taa_repin_smoke.sh / _a.sh / _b.sh) exist for repin_cell_generic.sh if root
# prefers the loop; then flip in the order smoke, a, b and take b's flight commit.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PY=/home/chao/.venvs/speechrl/bin/python
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1
PKG=a2t-stage3-aa-paired-400-v1
PREREG=docs/readiness/2026-09-27-a2t-stage3-aa-paired-400-v1-preregistration.md
DEC_PATH=coordination/a2t-stage3-aa-paired-400-v1/root-admission-v1.json
DEC_ID=a2t-stage3-aa-paired-400-admission-v1
SMOKE=a2t-stage3-aa-paired-400-smoke-4-v1
A=a2t-stage3-aa-paired-400-a-v1
B=a2t-stage3-aa-paired-400-b-v1
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
cd "$MAIN" || exit 1
[ -f "$DATA/$DEC_PATH" ] || { echo "decision receipt missing: $DATA/$DEC_PATH (mint it first)"; exit 3; }
echo "== HEAD $(git rev-parse --short HEAD); tracked dirt: $(git status --short | grep -vc '^??')"
cat > /home/chao/a2taa-flip-commit.txt <<'M'
research: flip cell A2T-AA (four-row smoke, pass A, pass B) to ready at one commit -- Audio2Tool's own request-identical null on the paired 400 (owner decisions 67, 68, 71 and 139; measurement instrument rules 3 and 6): the sealed direct baseline flown twice in one chain on one Audio2Tool np3 session, read for per-row byte identity and the CI95 half-width h_A2T; claims_benefit false, no admission; re-pinned by scripts/flights/repin_cell.py, decision receipt a2t-stage3-aa-paired-400-admission-v1

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
$PY -B scripts/flights/repin_cell.py \
  --repo-root "$MAIN" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
  --experiment "$SMOKE" --cell "$SMOKE" --experiment "$A" --cell "$A" --experiment "$B" --cell "$B" \
  --readiness-dir "$RD" --package-name "$PKG" --preregistration "$PREREG" \
  --decision "$DEC_PATH" --decision-id "$DEC_ID" --set-ready > /home/chao/a2taa-repin-cell.out 2> /home/chao/a2taa-repin-cell.err
RC=$?
echo "repin exit $RC"
if [ $RC -ne 0 ]; then
  grep -o "Error[A-Za-z]*: [^\\\\]*" /home/chao/a2taa-repin-cell.err | head -3 | cut -c1-300
  $PY -c "import json,io; print(json.load(io.open('/home/chao/a2taa-repin-cell.err'))['error'][:800])" 2>/dev/null
  echo "REFUSED; the tree is left as the tool left it -- inspect git status before anything else"
  exit 4
fi
echo "== changed"; git status --short | head -30
git add "configs/experiment/$SMOKE.json" "configs/experiment/$A.json" "configs/experiment/$B.json" configs/baseline docs/exposure-ledger.md "$PREREG" "$RD/"
git commit -q -F /home/chao/a2taa-flip-commit.txt && echo "committed $(git rev-parse --short HEAD)" || { echo "COMMIT FAILED"; exit 5; }
echo "tracked dirt after commit: $(git status --short | grep -vc '^??')"
git rev-parse HEAD > /home/chao/a2taa-flight-commit.txt
echo "flight commit $(cat /home/chao/a2taa-flight-commit.txt)"
for CELL in $SMOKE $A $B; do
  CK=$DATA/coordination/$PKG/check-$CELL-ready-v1.json
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root "$MAIN" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" --experiment "$CELL" --cell "$CELL" > "$CK" 2>/home/chao/a2taa-check-$CELL.err || { echo "check FAILED for $CELL"; tail -4 /home/chao/a2taa-check-$CELL.err | cut -c1-300; exit 6; }
  $PY -B $SP/b1_check_summary.py "$CK" "$MAIN/$RD/protocol-registered-v1.json"
done
$PY -B scripts/checks/stage3_effect_floor_check.py 2>&1 | tail -1
$PY -B scripts/checks/results_ledger_check.py 2>&1 | tail -1
