#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the construction-source lock column cells to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one whole
# pass commits nothing (a later flip rewrites shared files such as the exposure ledger after an earlier cycle reported "satisfied"; the shared
# protocol hash propagates once), and only then is HEAD recorded as the column's flight commit. DRAFT / HELD: the coordinator runs this ONLY after
#   1. countersigning the DRAFT rows (arm, arm FIT, smoke, smoke FIT, the READ row and the R01C agreement-table preparation row);
#   2. minting the decision receipt with scripts/flights/tfrl/tfrl_mint_receipt.py --kind construction;
#   3. the R01C agreement table is BUILT (prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-R01C-V1, model-free, against the minus-r01 pool pinned by the
#      construction variant consumption_module.construction_roster r01c; the runner refuses R01C rows inside the lock's own exemplar pool);
#   4. no concurrent merge (a flip loop commits a half-resolved merge); no other experiment in flight (one experiment in flight).
# After the flip, refresh the registered plan pins (scripts/flights/refresh_registered_plan_pins.py --package <dir> copies the minted supply pin
# into the plans) and flip again. --allow-output-change must never be passed.
#   bash scripts/flights/tfrl/tfrl_const_flip.sh
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
TF=$MAIN/scripts/flights/tfrl
SLUG=tfrl-construction-lock-r01c
SHORT=tfrl-const
RD=docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1
DECDIR=slurp-$SLUG-v1
LABEL="construction-source lock column"
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/$DECDIR/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/tfrl/tfrl_mint_receipt.py --kind construction)"; exit 6
fi
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
for KIND in smoke arm; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (owner decision 263-A, coordinator resolution of 2026-10-11: the typed loop's material source on the construction roster; re-pinned by scripts/flights/repin_cell.py, decision receipt $DECDIR)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  bash "$SP/repin_loop_generic.sh" "$TF/tfrl_const_repin_smoke.sh" "$RD" slurp-native-stage3-$SLUG-smoke-4-v1 smoke-generation "/home/chao/$SHORT-smoke-commit.txt" || exit $?
  bash "$SP/repin_loop_generic.sh" "$TF/tfrl_const_repin_arm.sh" "$RD" slurp-native-stage3-$SLUG-v1 generation "/home/chao/$SHORT-arm-commit.txt" || exit $?
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-column-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL cells ready at it)"
