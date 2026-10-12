#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip NX round R5 (smoke, the module OFF-arm replicate, the composed arm) to ready on master: model-free, in LOOP FORM -- one convergence
# loop, re-run until one whole pass commits nothing (a later flip rewrites shared files such as the exposure ledger; the shared protocol hash
# propagates once), and only then is HEAD recorded as the NX R5 flight commit. HELD: root runs this ONLY after
#   0. decision 238 is RULED and the R1 iteration-2 verdict is on file (the Solver-template swap, if any, is registered and re-derived first);
#   1. countersigning the DRAFT flight rows of THIS package (composed arm, arm FIT, smoke, smoke FIT) AND the replicate's two DRAFT rows in the
#      module package (SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1 and -FIT-V1); the READ row stays a draft until the seals;
#   2. minting BOTH receipts: coordination/slurp-nx-r5-composed-dev2000-added-v1/root-admission-v1.json (scripts/flights/nx/nx_r5_mint_receipt.py)
#      and coordination/slurp-stage3-module-comp1b-dev2000-added-v1/root-admission-v1.json (scripts/flights/module/module_comp1bdev_mint_receipt.py);
#   3. no concurrent merge (a flip loop commits a half-resolved merge).
# --allow-output-change must never be passed. The replicate re-pin uses the module package's own script and may rewrite that package's registered
# hashes if instrument merges moved them: that is the coordinator's flip, exactly as the module flip would do.
#   bash scripts/flights/nx/nx_r5_flip.sh
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
NX=$MAIN/scripts/flights/nx
MOD=$MAIN/scripts/flights/module
SLUG=nx-r5-composed-dev2000-added; SHORT=nxr5; LABEL=NX-R5
RD=docs/readiness/2026-10-09-slurp-$SLUG-v1
MRD=docs/readiness/2026-09-30-slurp-stage3-module-comp1b-dev2000-added-v1
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-$SLUG-v1/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/nx/nx_r5_mint_receipt.py)"; exit 6
fi
if [ ! -f "$DATA/coordination/slurp-stage3-module-comp1b-dev2000-added-v1/root-admission-v1.json" ]; then
  echo "refusing: the replicate (module package) receipt is not minted (scripts/flights/module/module_comp1bdev_mint_receipt.py)"; exit 6
fi
for KIND in smoke arm; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (NX programme R5 composed read: COMP-1b on lock v2.2 with v4g at delivery, Reviewer loop off, DEV-2000-ADDED; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-$SLUG-admission-v1)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
  "research: flip the NX R5 replicate (module OFF arm, lock v2.1) to ready (re-pinned by scripts/flights/repin_cell.py through the module package repin script)" \
  > /home/chao/module-comp1bdev-aa-commit.txt
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  NX_KIND=smoke bash "$SP/repin_loop_generic.sh" "$NX/nx_r5_repin_cell.sh" "$RD" slurp-native-stage3-$SLUG-smoke-4-v1 smoke-generation "/home/chao/$SHORT-smoke-commit.txt" || exit $?
  bash "$SP/repin_loop_generic.sh" "$MOD/module_comp1bdev_repin_aa.sh" "$MRD" slurp-native-stage3-module-comp1b-aa-dev2000-added-v1 aa-generation /home/chao/module-comp1bdev-aa-commit.txt || exit $?
  NX_KIND=arm bash "$SP/repin_loop_generic.sh" "$NX/nx_r5_repin_cell.sh" "$RD" slurp-native-stage3-$SLUG-v1 generation "/home/chao/$SHORT-arm-commit.txt" || exit $?
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL smoke, replicate and composed arm ready at it)"
