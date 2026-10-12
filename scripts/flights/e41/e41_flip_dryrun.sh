#!/bin/bash
# Flip the E41 four-row dry run to ready on master: model-free, one cell, no smoke (a four-row dry run IS the form
# proof). Root runs this AFTER:
#   1. countersigning the DRAFT exposure rows SAEA-E21-NATIVE-WINDOW-SYSTEM-FOUR-ROW-E41-V1 and its -FIT-V1 (and the
#      model-free row SAEA-E21-E41-PERCEPTION-NOTE-TRACE-READ-V1);
#   2. minting coordination/e21-native-window-e41-v1/root-admission-dry-run-v1.json (decision id
#      e21-native-window-e41-dry-run-admission-v1) with scripts/flights/e41/e41_mint_receipt.py --which dry-run.
# Untracked files count as dirt for core.flight.cli check; the tree must be clean before this runs. Sibling flips
# on master move this package's hashes: repin_loop_generic.sh re-runs the cycle until it converges at one HEAD.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-e21-native-window-e41-v1
cat > /home/chao/e41-dryrun-commit.txt <<M
research: flip the E41 four-row dry run to ready (owner decisions 103 and 158: the Earnings21 + ConEC system form at base lock v3.1 with ONE pin moved -- the Perception instruction to the bounded note, a numbered list of at most 5 lines of at most 20 words, never repeated, not a transcript -- on the E39b four-row roster and the E21 geometry; receipts only, R3 = Perception truncation rate, target zero; form-proof, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt e21-native-window-e41-dry-run-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
E41=$(dirname "$0")
bash $SP/repin_loop_generic.sh $E41/e41_repin_dryrun.sh $RD e21-native-window-system-four-row-e41-v1 dry-run-generation /home/chao/e41-dryrun-commit.txt || exit $?
echo "flight commit $(cat /home/chao/e41-dryrun-flight-commit.txt)"
