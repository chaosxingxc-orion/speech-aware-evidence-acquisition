#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip P-SV-1 and P-SV-2 (each smoke, then arm) to ready on master: model-free, in LOOP FORM -- one convergence
# loop over all four cycles, re-run until one whole pass commits nothing (a later flip rewrites shared files such
# as the exposure ledger after an earlier cycle reported "satisfied"; sibling re-pins propagate the shared
# protocol hash once), and only then is HEAD recorded as the P-SV flight commit. Root runs this ONLY after:
#   1. countersigning each cell's four DRAFT flight rows (arm, arm FIT, smoke, smoke FIT); the READ rows
#      SAEA-SLURP-STAGE3-PSV{1,2}-FOLD-B-BRANCH-READ-V1 stay drafts until the seal;
#   2. minting coordination/slurp-stage3-psv{1,2}-fold-b-v1/root-admission-v1.json with
#      scripts/flights/psv/psv_mint_receipt.py psv1|psv2 (it refuses P-SV-1 while the contrast-pair pin is the
#      placeholder TO-BE-PINNED-AFTER-CONTRAST-PAIR-BUILD);
#   3. merge set C (runtime, runner, bundle, presentations) has landed on master and both cells pass
#      core.flight.cli check there.
# --allow-output-change must never be passed.
#   bash scripts/flights/psv/psv_flip.sh [psv1 psv2 psv3 psv4]   (default psv1 psv2 unchanged; name psv3/psv4 to include them)
# P-SV-4's package is dated 2026-09-30 (the others 2026-09-29); pkg_date below resolves it per cell.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
PS=$MAIN/scripts/flights/psv
CELLS=("$@"); [ ${#CELLS[@]} -eq 0 ] && CELLS=(psv1 psv2)
pkg_date() { case "$1" in psv4) echo 2026-09-30 ;; *) echo 2026-09-29 ;; esac; }
cd "$MAIN" || exit 1
for K in "${CELLS[@]}"; do
  if [ ! -f "$DATA/coordination/slurp-stage3-$K-fold-b-v1/root-admission-v1.json" ]; then
    echo "refusing: the $K decision receipt is not minted (scripts/flights/psv/psv_mint_receipt.py $K)"; exit 6
  fi
  if grep -q "TO-BE-PINNED-AFTER-CONTRAST-PAIR-BUILD" "docs/readiness/$(pkg_date "$K")-slurp-stage3-$K-fold-b-v1/registered-facts-v1.json"; then
    echo "refusing: $K still carries the contrast-pair placeholder pin"; exit 6
  fi
  for KIND in smoke arm; do
    printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
      "research: flip ${K^^} ($KIND) to ready (owner decisions 184, 186, 188: phase-2 same-flight Perception branches on TRAIN Fold B, level 2, claim ceiling nominated; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-$K-fold-b-admission-v1)" \
      > "/home/chao/$K-$KIND-commit.txt"
  done
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for K in "${CELLS[@]}"; do
    RD=docs/readiness/$(pkg_date "$K")-slurp-stage3-$K-fold-b-v1
    PSV_CELL=$K PSV_KIND=smoke bash "$SP/repin_loop_generic.sh" "$PS/psv_repin_cell.sh" "$RD" "slurp-native-stage3-$K-fold-b-smoke-4-v1" smoke-generation "/home/chao/$K-smoke-commit.txt" || exit $?
    PSV_CELL=$K PSV_KIND=arm bash "$SP/repin_loop_generic.sh" "$PS/psv_repin_cell.sh" "$RD" "slurp-native-stage3-$K-fold-b-v1" generation "/home/chao/$K-arm-commit.txt" || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/psv-flight-commit.txt
echo "flight commit $CONVERGED (${CELLS[*]} smoke and arm ready at it)"
