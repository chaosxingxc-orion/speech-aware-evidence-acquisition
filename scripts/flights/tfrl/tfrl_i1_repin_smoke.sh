#!/bin/bash
# Re-pin the loop iteration column cell's four-row form smoke through the generic flip. Model-free. DRAFT / HELD: run only after the
# coordinator countersigns the DRAFT rows and mints the decision receipt. TFRL_ITER selects the iteration (default 1).
# The smoke's attempt ids (the rec1 ids after its single recovery, tfrl_family.SMOKE_RECOVERIES) are read by the re-pin tool from the
# cell's own fragments; the recovered smoke's plan files carry the -rec1 marker (tfrl_i1_flip.sh passes it as PLAN_REC).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
ITER=${TFRL_ITER:-1}
SLUG=tfrl-loop-i$ITER-fold-b
RD=docs/readiness/2026-10-11-slurp-$SLUG-v1 CELL=slurp-native-stage3-$SLUG-smoke-4-v1 PKG=slurp-tfrl-loop-i$ITER-v1 PREREG=docs/readiness/2026-10-11-slurp-$SLUG-v1-preregistration.md DEC_PATH=coordination/slurp-tfrl-loop-i$ITER-v1/root-admission-v1.json DEC_ID=slurp-tfrl-loop-i$ITER-admission-v1 TAG=tfrl-i$ITER-smoke MSG=/home/chao/tfrl-i$ITER-smoke-commit.txt bash $SP/repin_cell_generic.sh
