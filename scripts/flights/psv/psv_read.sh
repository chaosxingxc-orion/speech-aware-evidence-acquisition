#!/bin/bash
# The same-flight Perception-branch read of P-SV-1, P-SV-2 or P-SV-3 (owner decision 184; recipe
# docs/readiness/2026-09-29-slurp-stage3-psvK-fold-b-v1/analysis-recipe-v1.json).
#
#   bash scripts/flights/psv/psv_read.sh psv1|psv2|psv3
#
# 0. REFUSES before anything is opened unless scripts/analysis/slurp_perception_branch_read.py exists (merge set C
#    item 1; it had not landed when these cells were registered), the READ row
#    SAEA-SLURP-STAGE3-PSVK-FOLD-B-BRANCH-READ-V1 is ROOT COUNTERSIGNED, and the sealed run manifest exists.
# 1. Hands the recipe, the sealed run and the roster to that analysis script, which (level 1) reads gold rank /
#    present / top1 per branch note and refuses unless branch A reproduces the node-ledger driver's P-node
#    counting, and (level 2) renders each branch's first-visit Solver answer through the delivered row's
#    normaliser and projection and scores it ONCE with slurp-slu-official-train; then the paired row bootstrap of
#    B vs A and T vs A (10,000 draws, seed 20260929, per-scenario tables) under
#    $SPEECHRL_DATA_DIR/analysis/<READ RUN>/; an output directory that already holds files is refused.
# The argument list below follows the recipe; confirm it against the analysis script's --help once it lands.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; three official column scorings. The driver
# writes DESCRIPTIVE numbers; the nomination verdict is the coordinator's under the preregistered rule.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=${SPEECHRL_DATA_DIR:-/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data}
source "$MAIN/scripts/flights/batch/read_lib.sh"
K=$1
case "$K" in psv1|psv2|psv3) ;; *) echo "usage: psv_read.sh psv1|psv2|psv3"; exit 2;; esac
SLUG=$K-fold-b
UPPER=${SLUG^^}
RUN=SAEA-SLURP-STAGE3-$UPPER-V1
ATT=attempt-slurp-native-stage3-$SLUG-generation-v1
READ_RUN=SAEA-SLURP-STAGE3-$UPPER-BRANCH-READ-V1
RECIPE=docs/readiness/2026-09-29-slurp-stage3-$SLUG-v1/analysis-recipe-v1.json
ROSTER=docs/receipts/rosters/slurp-evo-fold-b-v2.json
SPLIT=4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a
ANALYSIS=scripts/analysis/slurp_perception_branch_read.py
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
cd "$MAIN" || exit 1
[ -f "$ANALYSIS" ] || { echo "REFUSED: $ANALYSIS has not landed (merge set C item 1)"; exit 8; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
if [ -d "$OUT" ] && [ -n "$(ls -A "$OUT")" ]; then echo "REFUSED: $OUT already holds files"; exit 5; fi
mkdir -p "$OUT"
"$PY" -B "$ANALYSIS" --recipe "$RECIPE" --run "$RUN" --attempt "$ATT" --roster "$ROSTER" \
  --split-identity-hash "$SPLIT" --level 2 --left-branch a-agree --twin-branch t-twin \
  --scorer-id slurp-slu-official-train --cluster-key sample_id --seed 20260929 --draws 10000 --per-scenario \
  --analysis-root "$OUT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
  || { echo "BRANCH READ REFUSED OR FAILED"; exit 6; }
echo "$K branch read written under $OUT"
