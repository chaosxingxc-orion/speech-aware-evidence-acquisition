#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Cell AGREE read (registered row SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1; recipe
# slurp-stage3-agree-w1-fold-a-paired-analysis-v1). MODEL-FREE: zero model / tokenizer / encoder / server
# contacts; scorer output is read from the sealed per-sample scores only.
#
# Driver: scripts/analysis/slurp_paired_roster_read.py (left = comparator, right = arm).
# Pass vs-aa (GATING): the arm against its in-chain A/A (w_agree 0.0, the locked plan's own bytes) -- the
#   measurement design is cross-flight-with-in-chain-replicate, intent primary (owner decisions 133, 143).
# Pass vs-plan (CONTEXT ONLY): the arm against the sealed PLAN arm; never the gating contrast.
#
# The driver writes DESCRIPTIVE numbers; the verdict is written by the coordinator and its disposition is
# taken with the owner in conversation (decision 139). No utterance text, gold, transcript or model output
# is printed or persisted.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
PKG=$MAIN/docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1
BASE=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1
ARM_RUN=SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1; ARM_ATT=attempt-slurp-native-stage3-agree-w1-fold-a-generation-v1; ARM_FIT=SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-FIT-V1
AA_RUN=SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-V1; AA_ATT=attempt-slurp-native-stage3-agree-aa-fold-a-generation-v1; AA_FIT=SAEA-SLURP-STAGE3-AGREE-AA-FOLD-A-FIT-V1
PLAN_RUN=SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1; PLAN_ATT=attempt-slurp-native-default-plan-lock-train-fold-a-generation-v1; PLAN_FIT=SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-FIT-V1
LOCK_ATTEMPT=attempt-slurp-native-b5e-exemplars-k20-slot-store-v2-anchor-train-fold-a-generation-recovery-v1
grep -E "^\| [^|]* \| SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1 \|" "$MAIN/docs/exposure-ledger.md" | grep -q "root countersigned" \
  || { echo "REFUSED: the READ row is missing or not countersigned"; exit 3; }
$PY -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
for PASS in vs-aa vs-plan; do
  if [ "$PASS" = vs-aa ]; then L_RUN=$AA_RUN; L_ATT=$AA_ATT; L_LABEL="the in-chain A/A (w_agree 0.0, the locked plan's own bytes)"
  else L_RUN=$PLAN_RUN; L_ATT=$PLAN_ATT; L_LABEL="the sealed PLAN arm (context only)"; fi
  ROOT=$BASE/$PASS
  mkdir -p "$ROOT" && cp "$MAIN/scripts/analysis/slurp_paired_roster_read.py" "$ROOT/slurp_paired_roster_read.py" && cd "$ROOT" || exit 1
  echo "### $PASS driver sha256 $(sha256sum slurp_paired_roster_read.py | cut -c1-16)"
  # plan_cell_read.py needs a registered-facts shape (comparator_official, lock_official, ...) this package does
  # not carry; the programme-standard paired roster read takes the two arms directly. Resampling unit per the
  # recipe: the row (cluster key sample_id), 10,000 draws, seed 20260926; TRAIN gold through the -train sibling.
  $PY -B slurp_paired_roster_read.py --stage all \
    --left-run "$L_RUN" --left-attempt "$L_ATT" --left-label "$L_LABEL" \
    --right-run $ARM_RUN --right-attempt $ARM_ATT --right-label "cell AGREE (w_agree 1.0, k 60, fuse 8-1-8)" \
    --scorer-id slurp-slu-official-train --expected-split-role discovery \
    --roster docs/receipts/rosters/slurp-evo-fold-a-v2.json --cluster-key sample_id \
    --split-identity-hash 61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6 \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" --seed 20260926 --draws 10000 \
    --recipe-id slurp-stage3-agree-w1-fold-a-paired-analysis-v1 \
    --title "Cell AGREE ($PASS): the intent-boundary agreement term on TRAIN Fold A" \
    --analysis-root "$ROOT" > "$ROOT/stage-all.log" 2>&1 \
    || { echo "READ FAILED ($PASS)"; tail -8 "$ROOT/stage-all.log" | cut -c1-300; exit 2; }
  echo "### $PASS done: $(ls "$ROOT" | tr '\n' ' ')"
done
