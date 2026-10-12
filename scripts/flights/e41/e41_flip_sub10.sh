#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the E41 sub10 re-read to ready on master: model-free, one cell. Root runs this ONLY AFTER:
#   1. the E41 dry-run read (docs/results/..., by dry-run-analysis-recipe-v1.json) holds R1-R3 and is committed;
#   2. countersigning the DRAFT exposure rows SAEA-E21-NATIVE-WINDOW-SYSTEM-SUB10-E41-V1 and its -FIT-V1;
#   3. filling the dry_run_read antecedent of root-admission-draft-sub10-v1.json with the committed read's path and
#      minting coordination/e21-native-window-e41-v1/root-admission-sub10-v1.json (decision id
#      e21-native-window-e41-sub10-admission-v1) with scripts/flights/e41/e41_mint_receipt.py --which sub10.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
RD=docs/readiness/2026-09-27-e21-native-window-e41-v1
DATA=$SAEA_DATA_ROOT
[ -f "$DATA/coordination/e21-native-window-e41-v1/root-admission-sub10-v1.json" ] || { echo "REFUSED: the sub10 decision receipt is not minted (the dry-run read must hold first)"; exit 3; }
cat > /home/chao/e41-sub10-commit.txt <<M
research: flip the E41 sub10 re-read to ready (owner decisions 103 and 158, after the E41 dry run held R1-R3: the Earnings21 + ConEC system form at base lock v3.1 with the bounded Perception note on the E35 sub10 roster, 10 calls / 342 windows, E21 geometry; a descriptive structural read against the sealed E35 sub10 direct arm bound per window; form-proof, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt e21-native-window-e41-sub10-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
E41=$(dirname "$0")
bash $SP/repin_loop_generic.sh $E41/e41_repin_sub10.sh $RD e21-native-window-system-sub10-e41-v1 sub10-generation /home/chao/e41-sub10-commit.txt || exit $?
echo "flight commit $(cat /home/chao/e41-sub10-flight-commit.txt)"
