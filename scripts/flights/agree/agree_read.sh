#!/bin/bash
# Cell AGREE read (registered row SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-PAIRED-ANALYSIS-V1; recipe
# slurp-stage3-agree-w1-fold-a-paired-analysis-v1). MODEL-FREE: zero model / tokenizer / encoder / server
# contacts; scorer output is read from the sealed per-sample scores only.
#
# Pass vs-aa (GATING): the arm against its in-chain A/A (w_agree 0.0, the locked plan's own bytes) -- the
#   measurement design is cross-flight-with-in-chain-replicate, intent primary (owner decisions 133, 143).
# Pass vs-plan (CONTEXT ONLY): the arm against the sealed PLAN arm; never the gating contrast.
#
# The driver writes DESCRIPTIVE numbers; the verdict is written by the coordinator and its disposition is
# taken with the owner in conversation (decision 139). No utterance text, gold, transcript or model output
# is printed or persisted.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
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
  if [ "$PASS" = vs-aa ]; then C_RUN=$AA_RUN; C_ATT=$AA_ATT; C_FIT=$AA_FIT; C_LABEL="the in-chain A/A (w_agree 0.0, the locked plan's own bytes)"
  else C_RUN=$PLAN_RUN; C_ATT=$PLAN_ATT; C_FIT=$PLAN_FIT; C_LABEL="the sealed PLAN arm (context only)"; fi
  ROOT=$BASE/$PASS
  mkdir -p "$ROOT" && cp "$MAIN/scripts/analysis/plan_cell_read.py" "$ROOT/plan_cell_read.py" \
    && cp "$PKG/registered-facts-v1.json" "$ROOT/registered-agree.json" && cd "$ROOT" || exit 1
  echo "### $PASS driver sha256 $(sha256sum plan_cell_read.py | cut -c1-16)"
  for stage in stop structural contrast lock efficiency frontier verdict; do
    $PY -B plan_cell_read.py --stage $stage \
      --arm-run $ARM_RUN --arm-attempt $ARM_ATT --arm-fit-run $ARM_FIT --arm-label "cell AGREE (w_agree 1.0, k 60, fuse 8-1-8)" \
      --comparator-run $C_RUN --comparator-attempt $C_ATT --comparator-fit-run $C_FIT --comparator-label "$C_LABEL" \
      --lock-run SAEA-SLURP-NATIVE-B5E-EXEMPLARS-K20-SLOT-STORE-V2-ANCHOR-TRAIN-FOLD-A-RECOVERY-V1 --lock-attempt "$LOCK_ATTEMPT" \
      --own-null-left-run $PLAN_RUN --own-null-left-attempt $PLAN_ATT --own-null-left-label "cell PLAN" \
      --own-null-right-run SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-REPLICATE-V1 --own-null-right-attempt attempt-slurp-native-default-plan-lock-replicate-train-fold-a-generation-v1 --own-null-right-label "cell PLANr" \
      --package-dir "$PKG" --h-slu 1.2485 --h-intent 0.9943 --normaliser-id saea-deliver-normalise-v3 --seed 20260926 \
      --recipe-id slurp-stage3-agree-w1-fold-a-paired-analysis-v1 \
      --title "Cell AGREE ($PASS): the intent-boundary agreement term on TRAIN Fold A" \
      --registered "$ROOT/registered-agree.json" --analysis-root "$ROOT" > "$ROOT/stage-$stage.log" 2>&1 \
      || { echo "STAGE $stage FAILED ($PASS)"; tail -8 "$ROOT/stage-$stage.log" | cut -c1-300; exit 2; }
  done
  echo "### $PASS done: $(ls "$ROOT" | tr '\n' ' ')"
done
