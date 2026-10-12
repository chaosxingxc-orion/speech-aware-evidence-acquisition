#!/bin/bash
# Re-pin the iteration's TYPED PROPOSER text-only cell through the generic flip. ARM=1: records the flight commit and runs the check. Model-free.
# DRAFT / HELD: run only after the coordinator countersigns the DRAFT rows and mints the decision receipt. TFRL_ITER selects the iteration.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
ITER=${TFRL_ITER:-1}
RD=docs/readiness/2026-10-11-slurp-tfrl-loop-i$ITER-proposers-v1 CELL=slurp-native-stage3-tfrl-proposer-i$ITER-v1 PKG=slurp-tfrl-proposers-i$ITER-v1 PREREG=docs/readiness/2026-10-11-slurp-tfrl-loop-i$ITER-proposers-v1-preregistration.md DEC_PATH=coordination/slurp-tfrl-proposers-i$ITER-v1/root-admission-v1.json DEC_ID=slurp-tfrl-proposers-i$ITER-admission-v1 TAG=tfrl-i$ITER-typed ARM=1 MSG=/home/chao/tfrl-i$ITER-typed-commit.txt bash $SP/repin_cell_generic.sh
