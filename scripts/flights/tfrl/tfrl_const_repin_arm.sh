#!/bin/bash
# Re-pin the CONSTRUCTION-SOURCE lock column (the 625-row arm) through the generic flip. ARM=1: records the flight commit, prints the check
# summary and runs the results-ledger gate; the check attaches to NOTHING. Model-free. DRAFT / HELD: the coordinator runs this only after
# countersigning the DRAFT rows and minting the decision receipt (tfrl_mint_receipt.py --kind construction); the knowledge-source-guard blocker
# is resolved by the construction variant (see the package README).
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
SLUG=tfrl-construction-lock-r01c
RD=docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1 CELL=slurp-native-stage3-$SLUG-v1 PKG=slurp-$SLUG-v1 PREREG=docs/readiness/2026-10-11-slurp-tfrl-construction-source-v1-preregistration.md DEC_PATH=coordination/slurp-$SLUG-v1/root-admission-v1.json DEC_ID=slurp-$SLUG-admission-v1 TAG=tfrl-const-arm ARM=1 MSG=/home/chao/tfrl-const-arm-commit.txt bash $SP/repin_cell_generic.sh
