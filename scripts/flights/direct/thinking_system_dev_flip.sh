#!/bin/bash
# Flip the three P3.1 cells (smoke, lock arm, twin aa) to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one whole
# pass commits nothing, and only then is HEAD recorded as the flight commit. Run it through the ext4 package wrapper (owner decision 267):
#   bash scripts/flights/batch/flip_package_ext4.sh --flip "scripts/flights/direct/thinking_system_dev_flip.sh" \
#     --package docs/readiness/2026-10-13-slurp-system-thinking-core-dev2000-added-v1 \
#     --cells slurp-native-stage3-thinking-system-dev2000-added-smoke-4-v1,slurp-native-stage3-thinking-system-dev2000-added-lock-v1,slurp-native-stage3-thinking-system-dev2000-added-aa-v1 \
#     --pins-commit-msg /home/chao/tsysd-pins-commit.txt
# Root runs this ONLY after: 1. the DEV Thinking packet window (direct_fb_packets_gpu.sh --run --stage dev2000-added) wrote the promotion receipt, the
# cells were re-derived with --require-receipt and the package re-written (README, "Chain sequence"); 2. countersigning the six flight DRAFT rows with
# countersign-row-texts-v1.json; 3. minting the receipt with scripts/flights/direct/thinking_system_dev_mint_receipt.py; 4. no other experiment in flight.
# FAILS CLOSED while the DEV promotion receipt is absent or a cell baseline still carries the zero sentinel. --allow-output-change must never be passed.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
DATA=$SAEA_DATA_ROOT
SP=$MAIN/scripts/flights/batch
DIRD=$MAIN/scripts/flights/direct
SLUG=thinking-system-dev2000-added
PKGN=slurp-system-thinking-core-dev2000-added-v1
SHORT=tsysd
LABEL=P3.1
RD=docs/readiness/2026-10-13-$PKGN
KINDS=${TSYSD_KINDS:-"smoke lock aa"}
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_package_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/$PKGN/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/direct/thinking_system_dev_mint_receipt.py)"; exit 6
fi
THINK_DEV_RECEIPT=/home/chao/feat-cache/slurp-q4km-packets-thinking-gpu-afdaeff6/DEV-2000-ADDED-promotion.json
if [ ! -f "$THINK_DEV_RECEIPT" ]; then echo "refusing: the DEV Thinking promotion receipt $THINK_DEV_RECEIPT is absent (direct_fb_packets_gpu.sh --run --stage dev2000-added)"; exit 8; fi
for KIND in $KINDS; do
  if grep -q '"speech_packet_promotion_receipt_sha256": "0\{64\}"' "$MAIN/configs/baseline/slurp-native-stage3-$SLUG-$([ "$KIND" = smoke ] && echo smoke-4 || echo "$KIND")-baseline-v1.json"; then
    echo "refusing: the $KIND baseline still carries the zero sentinel for the packet receipt (thinking_system_dev_derive_cells.py --require-receipt)"; exit 8
  fi
done
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
declare -A CELL=([smoke]=slurp-native-stage3-$SLUG-smoke-4-v1 [lock]=slurp-native-stage3-$SLUG-lock-v1 [aa]=slurp-native-stage3-$SLUG-aa-v1)
declare -A PLAN=([smoke]=smoke-generation [lock]=lock-generation [aa]=aa-generation)
for KIND in $KINDS; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (registry P3.1: the locked system on the Thinking core, DEV-2000-ADDED replicate, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-system-thinking-core-dev2000-added-admission-v1)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for KIND in $KINDS; do
    TSYSD_KIND=$KIND bash "$SP/repin_loop_generic.sh" "$DIRD/thinking_system_dev_repin_cell.sh" "$RD" "${CELL[$KIND]}" "${PLAN[$KIND]}" "/home/chao/$SHORT-$KIND-commit.txt" || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL smoke, lock arm and twin ready at it)"
