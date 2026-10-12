#!/bin/bash
# Flip the three 268-B cells (smoke, lock arm, twin aa) to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one whole
# pass commits nothing, and only then is HEAD recorded as the flight commit. Run it through the ext4 package wrapper (owner decision 267):
#   bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/direct/thinking_system_flip.sh" \
#     --package docs/readiness/2026-10-12-slurp-system-thinking-core-fold-b-v1 \
#     --cells slurp-native-stage3-thinking-system-fold-b-smoke-4-v1,slurp-native-stage3-thinking-system-fold-b-lock-v1,slurp-native-stage3-thinking-system-fold-b-aa-v1 \
#     --pins-commit-msg /home/chao/tsys-pins-commit.txt
# Root runs this ONLY after: 1. countersigning the seven DRAFT rows with countersign-row-texts-v1.json; 2. minting the receipt with
# scripts/flights/direct/thinking_system_mint_receipt.py; 3. the loop's iteration-3 column being closed (one experiment in flight); 4. the harness
# changes of design decision 282 (thinking_budget_tokens pass-through) being merged and the package re-derived (README, "Prerequisites").
# --allow-output-change must never be passed.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
DIRD=$MAIN/scripts/flights/direct
SLUG=thinking-system-fold-b
PKGN=slurp-system-thinking-core-fold-b-v1
SHORT=tsys
LABEL=268-B
RD=docs/readiness/2026-10-12-$PKGN
KINDS=${TSYS_KINDS:-"smoke lock aa"}
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_package_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/$PKGN/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/direct/thinking_system_mint_receipt.py)"; exit 6
fi
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
declare -A CELL=([smoke]=slurp-native-stage3-$SLUG-smoke-4-v1 [lock]=slurp-native-stage3-$SLUG-lock-v1 [aa]=slurp-native-stage3-$SLUG-aa-v1)
declare -A PLAN=([smoke]=smoke-generation [lock]=lock-generation [aa]=aa-generation)
for KIND in $KINDS; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (owner decision 268 B: the locked system on the Thinking core, TRAIN Fold B, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-system-thinking-core-fold-b-admission-v1)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for KIND in $KINDS; do
    TSYS_KIND=$KIND bash "$SP/repin_loop_generic.sh" "$DIRD/thinking_system_repin_cell.sh" "$RD" "${CELL[$KIND]}" "${PLAN[$KIND]}" "/home/chao/$SHORT-$KIND-commit.txt" || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL smoke, lock arm and twin ready at it)"
