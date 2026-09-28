#!/bin/bash
# The knowledge wave's reads (owner decisions 163 and 164): a thin wrapper over scripts/flights/read_paired_cell.sh,
# which already takes a readiness package and reads the comparator ids from that package's analysis recipe
# (arms.arm, arms.in_chain_replicate -- here the wave A/A -- and arms.comparator, the sealed AGREE arm).
#
#   bash scripts/flights/wave/wave_read.sh [aa] [w1] [w3] [w4]      (default: every cell the chain flew)
#
#   aa -> docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1          READ SAEA-SLURP-STAGE3-WAVE1-AA-FOLD-A-PAIRED-READ-V1
#         (the cross-flight offset, wave A/A minus the sealed AGREE arm: context only; pass vs-aa alone)
#   w1 -> docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1  READ SAEA-SLURP-STAGE3-W1-CARDSEL-FOLD-A-PAIRED-ANALYSIS-V1
#   w3 -> docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1        READ SAEA-SLURP-STAGE3-W3-FOLD-A-PAIRED-ANALYSIS-V1
#   w4 -> docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1 READ SAEA-SLURP-STAGE3-W4-FOLD-A-PAIRED-READ-V1
#
# Each arm is read with both passes: vs-aa (the GATING contrast, at the shared wave A/A) and vs-comparator (the
# sealed AGREE arm, context only). read_paired_cell.sh REFUSES before any score is opened unless that package's
# READ row is ROOT COUNTERSIGNED, and it never overwrites a pass directory. The default list is the step list the
# flip converged on (/home/chao/wave-flight-steps.txt), so a dropped W3 is never read. MODEL-FREE: zero model /
# tokenizer / encoder / scorer / server contacts; descriptive numbers only -- each verdict is the coordinator's
# under that arm's own preregistered no-harm rule (decision 139). One read failing stops the loop.
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
READ=$MAIN/scripts/flights/read_paired_cell.sh
declare -A PKG=(
  [aa]=docs/readiness/2026-09-27-slurp-stage3-wave1-aa-fold-a-v1
  [w1]=docs/readiness/2026-09-27-slurp-stage3-w1-card-selection-fold-a-v1
  [w3]=docs/readiness/2026-09-27-slurp-stage3-w3-contrast-fold-a-v1
  [w4]=docs/readiness/2026-09-27-slurp-stage3-w4-slot-conventions-fold-a-v1
)
if [ $# -gt 0 ]; then
  WANT=("$@")
else
  STEPS=$(cat /home/chao/wave-flight-steps.txt 2>/dev/null) || { echo "REFUSED: no /home/chao/wave-flight-steps.txt; name the cells"; exit 3; }
  # shellcheck disable=SC2206
  WANT=(aa $STEPS)
fi
for name in "${WANT[@]}"; do
  [ -n "${PKG[$name]:-}" ] || { echo "REFUSED: unknown wave cell '$name' (aa, w1, w3, w4)"; exit 3; }
  echo "######## wave read $name: ${PKG[$name]}"
  if [ "$name" = "aa" ]; then
    bash "$READ" "${PKG[$name]}" --passes vs-aa || exit $?
  else
    bash "$READ" "${PKG[$name]}" --passes vs-aa,vs-comparator || exit $?
  fi
done
echo "wave reads done: ${WANT[*]}"
