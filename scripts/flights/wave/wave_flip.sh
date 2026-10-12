#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Owner decision 164: flip the knowledge wave -- the SHARED in-chain A/A (SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1,
# the retained AGREE arm's own bytes), W1 (smoke, arm), W3a (smoke, arm) and W4 (smoke, arm) -- to ready on
# master, model-free, converged at ONE HEAD, which becomes the flight commit of the one wave chain
# (scripts/flights/wave/batch_chain_wave.sh). The decision-160 shape (scripts/flights/comp1/comp1_g5_flip.sh).
#
# Root runs this ONLY after, in order:
#   1. the branch carrying this wiring is merged to master;
#   2. root has countersigned every flight row of the four families (the A/A and its FIT identity; each arm, each
#      smoke and their FIT identities) and the model-free rows the families' own flip scripts name; the READ rows
#      (the A/A's and each arm's) may stay DRAFT until the seal;
#   3. root has minted the four receipts: scripts/flights/wave/wave_mint_receipt.py (two eligible ids; it refuses
#      unless the shared A/A proof reads IDENTICAL), scripts/flights/w1/w1_mint_receipt.py,
#      scripts/flights/w3/w3_mint_receipt.py and scripts/flights/w4/w4_mint_receipt.py (four each).
# scripts/flights/wave/wave_preconditions.py --mode flip REFUSES while any of that is missing, while the shared A/A
# proof is not IDENTICAL, and while the registered W3 arm still carries W3b (the exemplar cap): the wave flies W3a
# ONLY. WAVE_SKIP_W3=1 drops W3 from the wave altogether (the flip and the chain then carry the A/A, W1 and W4).
#
# --allow-output-change is never passed: every cell mints its own first-phase supply (item E16), and each minted
# supply must carry the AGREE family's own output digest (arms eab5c61e..., smokes 308601c5...).
# Sequence: one CONVERGENCE loop over every cycle (the A/A, then each family's smoke and arm), re-run until one
# whole pass commits nothing, because a later flip rewrites shared files (the exposure ledger) after an earlier
# cell reported "satisfied". Only then is HEAD recorded. Untracked files count as dirt for core.flight.cli check.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
WV=$MAIN/scripts/flights/wave
PY=/home/chao/.venvs/speechrl/bin/python
AARD=docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1
W1RD=docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1
W3RD=docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1
W4RD=docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1
SKIP=()
[ "${WAVE_SKIP_W3:-0}" = "1" ] && SKIP=(--skip-w3)
cd "$MAIN" || exit 1

PYTHONDONTWRITEBYTECODE=1 $PY -B "$WV/wave_preconditions.py" --repo-root "$MAIN" --data-root "$DATA" --mode flip "${SKIP[@]}" || exit 6

msg() {  # $1 file, $2 subject
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' "$2" > "$1"
}
msg /home/chao/wave-aa-commit.txt "research: flip the knowledge wave's shared in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 to ready (the retained AGREE arm's own bytes, proven IDENTICAL model-free; the within-chain null of W1, W3a and W4; owner decisions 160, 161 and 164; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-wave1-aa-fold-a-admission-v1)"
for K in smoke arm; do
  msg /home/chao/w1-$K-commit.txt "research: flip W1 ($K) to ready (knowledge wave item W1, slot-card selection, read on no harm at the SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 flown in the same wave chain; owner decisions 127, 161 and 164; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w1-cardsel-fold-a-admission-v1)"
  msg /home/chao/w3-$K-commit.txt "research: flip W3a ($K) to ready (knowledge wave item W3, the intent contrast cards alone, read on no harm at the SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 flown in the same wave chain; owner decision 164; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w3-contrast-fold-a-admission-v1)"
  msg /home/chao/w4-$K-commit.txt "research: flip W4 ($K) to ready (knowledge wave item W4, slot conventions, read on no harm at the SHARED in-chain A/A SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-V1 flown in the same wave chain; owner decision 164; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-w4-fold-a-admission-v1)"
done

CYCLES=(
  "$WV/wave_repin_aa.sh $AARD slurp-native-stage3-wave1-aa-fold-a-v1 generation /home/chao/wave-aa-commit.txt"
  "$MAIN/scripts/flights/w1/w1_repin_smoke.sh $W1RD slurp-native-stage3-w1-cardsel-fold-a-smoke-4-v1 smoke-generation /home/chao/w1-smoke-commit.txt"
  "$MAIN/scripts/flights/w1/w1_repin_arm.sh $W1RD slurp-native-stage3-w1-cardsel-fold-a-v1 generation /home/chao/w1-arm-commit.txt"
)
STEPS="w1"
if [ ${#SKIP[@]} -eq 0 ]; then
  CYCLES+=(
    "$MAIN/scripts/flights/w3/w3_repin_smoke.sh $W3RD slurp-native-stage3-w3-fold-a-smoke-4-v1 smoke-generation /home/chao/w3-smoke-commit.txt"
    "$MAIN/scripts/flights/w3/w3_repin_arm.sh $W3RD slurp-native-stage3-w3-fold-a-v1 generation /home/chao/w3-arm-commit.txt"
  )
  STEPS="$STEPS w3"
fi
CYCLES+=(
  "$MAIN/scripts/flights/w4/w4_repin_smoke.sh $W4RD slurp-native-stage3-w4-fold-a-smoke-4-v1 smoke-generation /home/chao/w4-smoke-commit.txt"
  "$MAIN/scripts/flights/w4/w4_repin_arm.sh $W4RD slurp-native-stage3-w4-fold-a-v1 generation /home/chao/w4-arm-commit.txt"
)
STEPS="$STEPS w4"

CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for cycle in "${CYCLES[@]}"; do
    # shellcheck disable=SC2086
    bash $SP/repin_loop_generic.sh $cycle || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
# The chain reads the step list the flip converged on, so the two can never disagree about W3.
echo "$STEPS" > /home/chao/wave-flight-steps.txt
echo "$CONVERGED" > /home/chao/wave-flight-commit.txt
echo "flight commit $CONVERGED (the wave A/A and [$STEPS] ready at it)"
