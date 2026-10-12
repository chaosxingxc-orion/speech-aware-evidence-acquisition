#!/bin/bash
# Re-pin the CONSTRUCTION-SOURCE lock column's four-row form smoke through the generic flip. Model-free. DRAFT / HELD: run only after the
# coordinator countersigns the DRAFT rows and mints the decision receipt.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
SLUG=tfrl-construction-lock-r01c
RD=docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1 CELL=slurp-native-stage3-$SLUG-smoke-4-v1 PKG=slurp-$SLUG-v1 PREREG=docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1-preregistration.md DEC_PATH=coordination/slurp-$SLUG-v1/root-admission-v1.json DEC_ID=slurp-$SLUG-admission-v1 TAG=tfrl-const-smoke MSG=/home/chao/tfrl-const-smoke-commit.txt bash $SP/repin_cell_generic.sh
