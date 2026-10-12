#!/bin/bash
# Re-pin the loop iteration column cell (the 1,080-row arm) through the generic flip. ARM=1: records the flight commit, prints the check
# summary and runs the results-ledger gate; the check attaches to NOTHING. Model-free. DRAFT / HELD: the coordinator runs this only after
# countersigning the DRAFT rows and minting the decision receipt. TFRL_ITER selects the iteration (default 1).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
ITER=${TFRL_ITER:-1}
SLUG=tfrl-loop-i$ITER-fold-b
RD=docs/readiness/2026-10-11-slurp-$SLUG-v1 CELL=slurp-native-stage3-$SLUG-v1 PKG=slurp-tfrl-loop-i$ITER-v1 PREREG=docs/readiness/2026-10-11-slurp-$SLUG-v1-preregistration.md DEC_PATH=coordination/slurp-tfrl-loop-i$ITER-v1/root-admission-v1.json DEC_ID=slurp-tfrl-loop-i$ITER-admission-v1 TAG=tfrl-i$ITER-arm ARM=1 MSG=/home/chao/tfrl-i$ITER-arm-commit.txt bash $SP/repin_cell_generic.sh
