#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip the four 266-E cells (smoke, Thinking arm, Instruct arm, Instruct replicate) to ready on master: model-free, in LOOP FORM -- one convergence
# loop, re-run until one whole pass commits nothing (a later flip rewrites shared files such as the exposure ledger after an earlier cycle reported
# "satisfied"; the shared protocol hash propagates once), and only then is HEAD recorded as the flight commit. Root runs this ONLY after:
#   1. countersigning the eight DRAFT flight rows (four generation, four FIT) with the texts of the package's countersign-row-texts-v1.json;
#      the READ row, the serving-contact row and the packet-preparation row stay drafts;
#   2. minting coordination/slurp-direct-only-fold-b-thinking-vs-instruct-v1/root-admission-v1.json with scripts/flights/direct/direct_fb_mint_receipt.py;
#   3. preparing the Thinking speech-packet root and pinning its promotion receipt in the two Thinking baselines (this script REFUSES while the
#      zero sentinel remains: a Thinking cell flipped to ready without packets would fail at the first contact);
#   4. the 266-E engineering branch being on master; no concurrent merge (a flip loop commits a half-resolved merge); no other experiment in flight.
# RECOVERY rec1 (2026-10-11, direct_fb_family.RECOVERIES): the Instruct arm is registered under rec1 attempt ids with plan files
# instruct-{generation,fit}-plan-registered-rec1-v1.json; this script passes PLAN_REC=-rec1 for that kind. Its rec1 generation row and the rec1 FIT row
# (an appended ledger block "Cell 266-E recovery rec1") are countersigned from countersign-row-texts-v1.json beside the first-attempt rows, which stay.
# After the flip, refresh the registered plan pins (scripts/flights/refresh_registered_plan_pins.py) and flip again if the tool says so.
# --allow-output-change must never be passed.
# DIRECT_FB_KINDS (default "smoke thinking instruct replicate") narrows the flip, e.g. DIRECT_FB_KINDS="instruct replicate" to ready only the Instruct pair
# before the Thinking packets exist (the sentinel check then does not apply).
#   bash scripts/flights/direct/direct_fb_flip.sh
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=${SAEA_FLIP_DATA:-$SAEA_DATA_ROOT}
SP=$MAIN/scripts/flights/batch
DIRD=$MAIN/scripts/flights/direct
SLUG=direct-only-fold-b-thinking-vs-instruct
SHORT=direct-fb
LABEL=266-E
RD=docs/readiness/2026-10-11-slurp-$SLUG-v1
ZERO=0000000000000000000000000000000000000000000000000000000000000000
KINDS=${DIRECT_FB_KINDS:-"smoke thinking instruct replicate"}
# Owner 2026-10-12: hot paths never run on /mnt/* (9p). Refuse (64) unless SAEA_ALLOW_9P_FLIP=1.
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_in_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
cd "$MAIN" || exit 1
if [ ! -f "$DATA/coordination/slurp-$SLUG-v1/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/direct/direct_fb_mint_receipt.py)"; exit 6
fi
for B in configs/baseline/slurp-direct-only-fold-b-thinking-baseline-v1.json configs/baseline/slurp-direct-only-fold-b-thinking-smoke-4-baseline-v1.json; do
  case " $KINDS " in *" thinking "*|*" smoke "*) ;; *) break ;; esac
  if grep -q "\"speech_packet_promotion_receipt_sha256\": \"$ZERO\"" "$B"; then
    echo "refusing: $B still carries the zero packet-promotion sentinel (the Thinking speech-packet root is not prepared and pinned)"; exit 7
  fi
done
declare -A CELL=([smoke]=slurp-direct-only-fold-b-thinking-smoke-4-v1 [thinking]=slurp-direct-only-fold-b-thinking-v1 [instruct]=slurp-direct-only-fold-b-instruct-v1 [replicate]=slurp-direct-only-fold-b-instruct-replicate-v1)
# A recovered cell's registered plans carry the -rec1 marker (direct_fb_family.RECOVERIES): the re-pin loop reads <kind>-generation-plan-registered<REC>-v1.json.
declare -A PLAN_REC_OF=()
for KIND in smoke thinking instruct replicate; do
  PLAN_REC_OF[$KIND]=$(/home/chao/.venvs/speechrl/bin/python -B -c "import sys; sys.path.insert(0, '$DIRD'); import direct_fb_family as fam; print(fam.rec_suffix('$KIND'))") || exit 1
done
for KIND in $KINDS; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (owner decision 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct, claims_benefit false; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-$SLUG-admission-v1)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
# Owner decision 270 A (2026-10-12): FLIP_MODE=one-pass replaces the convergence loop below by ONE call of onepass_flip.sh -- every cell re-pinned,
# the plan pins refreshed, the shared documents and ledger rows written once, ONE commit, then core.flight.cli check once per cell. Default stays
# FLIP_MODE=iterate until the owner flips it. The refusals above (receipt, sentinel, 9p) apply to both modes.
if [ "${FLIP_MODE:-iterate}" = one-pass ]; then
  ONEPASS_CELLS=(); for KIND in $KINDS; do ONEPASS_CELLS+=("${CELL[$KIND]}"); done
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KINDS) to ready in one pass (owner decision 266-E: the bare-core read on TRAIN Fold B, Thinking versus Instruct, claims_benefit false; re-pinned by scripts/flights/repin_package_one_pass.py, decision receipt slurp-$SLUG-admission-v1)" \
    > "/home/chao/$SHORT-onepass-commit.txt"
  bash "$SP/onepass_flip.sh" --readiness-dir "$RD" --prereg "$RD-preregistration.md" --package "slurp-$SLUG-v1" \
    --decision-path "coordination/slurp-$SLUG-v1/root-admission-v1.json" --decision-id "slurp-$SLUG-admission-v1" \
    --commit-msg "/home/chao/$SHORT-onepass-commit.txt" --flight-commit-file "/home/chao/$SHORT-flight-commit.txt" \
    "${ONEPASS_CELLS[@]}" || exit $?
  echo "flight commit $(git rev-parse HEAD) ($LABEL $KINDS ready at it, one pass)"
  exit 0
fi
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  for KIND in $KINDS; do
    PLAN=$KIND-generation
    DIRECT_KIND=$KIND PLAN_REC="${PLAN_REC_OF[$KIND]}" bash "$SP/repin_loop_generic.sh" "$DIRD/direct_fb_repin_cell.sh" "$RD" "${CELL[$KIND]}" "$PLAN" "/home/chao/$SHORT-$KIND-commit.txt" || exit $?
  done
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL smoke, Thinking arm, Instruct arm and replicate ready at it)"
