#!/bin/bash
# Flip the loop iteration cells to ready on master: model-free, in LOOP FORM -- one convergence loop, re-run until one whole pass commits
# nothing (a later flip rewrites shared files such as the exposure ledger after an earlier cycle reported "satisfied"; the shared protocol
# hash propagates once), and only then is HEAD recorded as the iteration's flight commit. DRAFT / HELD: the coordinator runs this ONLY after
#   1. countersigning the DRAFT rows (column: arm, arm FIT, smoke, smoke FIT; proposers: typed, ace -- text-only, no FIT identity);
#      a recovered smoke (rec1) has ITS OWN two DRAFT rows beside the countersigned first-attempt ones, and a run id carries exactly one row at launch;
#   2. minting the decision receipt(s) with scripts/flights/tfrl/tfrl_mint_receipt.py (already minted receipts are NOT re-minted for a recovery:
#      the run ids do not change);
#   3. the engineering items are merged on master and the cells pass core.flight.cli check there; no concurrent merge (a flip loop commits a
#      half-resolved merge); no other experiment is in flight (one experiment in flight); the loop driver reports the protocol hash unchanged.
# After the flip, refresh the registered plan pins (scripts/flights/refresh_registered_plan_pins.py --package <dir> copies the minted supply
# pin into the plans) and flip again. --allow-output-change must never be passed.
#   TFRL_ITER=1 bash scripts/flights/tfrl/tfrl_i1_flip.sh [column|proposers]
#   TFRL_ONLY=ace TFRL_ITER=1 bash scripts/flights/tfrl/tfrl_i1_flip.sh proposers   # flip ONLY the reflector (typed is flown and sealed; its re-pin would be refused); typed|ace, default both
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
[ -n "${SAEA_FLIP_DATA:-}" ] && export SAEA_DATA_ROOT=$SAEA_FLIP_DATA  # test override, as before
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
DATA=${SAEA_DATA_ROOT:-$SAEA_DATA_ROOT_DEFAULT}  # resolved and guarded by saea_data_root_init before the first cd
SP=$MAIN/scripts/flights/batch
TF=$MAIN/scripts/flights/tfrl
ITER=${TFRL_ITER:-1}
WHICH=${1:-column}
SHORT=tfrl-i$ITER
case "$WHICH" in
  column)
    SLUG=tfrl-loop-i$ITER-fold-b
    RD=docs/readiness/2026-10-11-slurp-$SLUG-v1
    DECDIR=slurp-tfrl-loop-i$ITER-v1
    LABEL="loop iteration $ITER column" ;;
  proposers)
    RD=docs/readiness/2026-10-11-slurp-tfrl-loop-i$ITER-proposers-v1
    DECDIR=slurp-tfrl-proposers-i$ITER-v1
    LABEL="loop iteration $ITER proposer and reflector" ;;
  *) echo "usage: TFRL_ITER=n tfrl_i1_flip.sh [column|proposers]" >&2; exit 2 ;;
esac
ONLY=${TFRL_ONLY:-}
case "$ONLY" in ""|typed|ace) ;; *) echo "TFRL_ONLY must be typed or ace" >&2; exit 2 ;; esac
if [ -n "$ONLY" ] && [ "$WHICH" != proposers ]; then echo "TFRL_ONLY applies to the proposers mode only" >&2; exit 2; fi
# Owner 2026-10-12: hot paths never run on /mnt/* (9p). Refuse (64) unless SAEA_ALLOW_9P_FLIP=1.
case "$(realpath -m "$MAIN")" in /mnt/*) [ "$SAEA_ALLOW_9P_FLIP" = 1 ] || { echo "refusing: repo root $MAIN is on /mnt (9p); run via scripts/flights/batch/flip_in_ext4.sh or set SAEA_ALLOW_9P_FLIP=1"; exit 64; } ;; esac
saea_data_root_init || exit 70
DATA=$SAEA_DATA_ROOT
cd "$MAIN" || exit 1
# The smoke's single recovery (tfrl_family.SMOKE_RECOVERIES): "-rec1" when the iteration's smoke is re-flown under rec1 attempt ids, else "".
# It marks the smoke's registered plan files (smoke-generation-plan-registered<rec>-v1.json); the attempt ids themselves are read from the fragments.
SMOKE_REC=$(/home/chao/.venvs/speechrl/bin/python -B -c "import sys; sys.path.insert(0, '$TF'); import tfrl_family as tf; print(tf.smoke_rec_suffix($ITER))") || exit 1
if [ ! -f "$DATA/coordination/$DECDIR/root-admission-v1.json" ]; then
  echo "refusing: the $LABEL decision receipt is not minted (scripts/flights/tfrl/tfrl_mint_receipt.py)"; exit 6
fi
if [ -n "$(pgrep -af 'core.flight.cli|batch_driver.sh' | grep -v pgrep)" ]; then echo "a batch is running; abort"; exit 7; fi
if [ "$WHICH" = column ]; then KINDS="smoke arm"; else KINDS="${ONLY:-typed ace}"; fi
for KIND in $KINDS; do
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KIND) to ready (owner decision 263-A: the autonomous typed loop with the ACE comparator; re-pinned by scripts/flights/repin_cell.py, decision receipt $DECDIR)" \
    > "/home/chao/$SHORT-$KIND-commit.txt"
done
# Owner decision 270 A (2026-10-12): FLIP_MODE=one-pass replaces the convergence loop below by ONE call of onepass_flip.sh -- every cell re-pinned,
# the plan pins refreshed, the shared documents and ledger rows written once, ONE commit, then core.flight.cli check once per cell. Default stays
# FLIP_MODE=iterate until the owner flips it. The refusals above (receipt, running batch, 9p) apply to both modes.
if [ "${FLIP_MODE:-iterate}" = one-pass ]; then
  ONEPASS_CELLS=(); ONEPASS_FLAGS=(--flight-commit-file "/home/chao/$SHORT-$WHICH-flight-commit.txt")
  if [ "$WHICH" = column ]; then
    ONEPASS_CELLS=("slurp-native-stage3-tfrl-loop-i$ITER-fold-b-smoke-4-v1" "slurp-native-stage3-tfrl-loop-i$ITER-fold-b-v1")
    ONEPASS_FLAGS+=(--ready-receipt "slurp-native-stage3-tfrl-loop-i$ITER-fold-b-v1" --flight-commit-file "/home/chao/$SHORT-arm-flight-commit.txt")
  else
    for KIND in $KINDS; do
      case "$KIND" in
        typed) ONEPASS_CELLS+=("slurp-native-stage3-tfrl-proposer-i$ITER-v1") ;;
        ace) ONEPASS_CELLS+=("slurp-native-stage3-tfrl-ace-reflector-i$ITER-v1") ;;
      esac
      ONEPASS_FLAGS+=(--ready-receipt "${ONEPASS_CELLS[-1]}" --flight-commit-file "/home/chao/$SHORT-$KIND-flight-commit.txt")
    done
  fi
  printf '%s\n\nCo-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>\n' \
    "research: flip $LABEL ($KINDS) to ready in one pass (owner decision 263-A: the autonomous typed loop with the ACE comparator; re-pinned by scripts/flights/repin_package_one_pass.py, decision receipt $DECDIR)" \
    > "/home/chao/$SHORT-onepass-commit.txt"
  bash "$SP/onepass_flip.sh" --readiness-dir "$RD" --prereg "$RD-preregistration.md" --package "$DECDIR" \
    --decision-path "coordination/$DECDIR/root-admission-v1.json" --decision-id "${DECDIR%-v1}-admission-v1" \
    --commit-msg "/home/chao/$SHORT-onepass-commit.txt" "${ONEPASS_FLAGS[@]}" "${ONEPASS_CELLS[@]}" || exit $?
  echo "flight commit $(git rev-parse HEAD) ($LABEL $KINDS ready at it, one pass)"
  exit 0
fi
CONVERGED=""
for pass in 1 2 3 4; do
  BEFORE=$(git rev-parse HEAD)
  if [ "$WHICH" = column ]; then
    PLAN_REC="$SMOKE_REC" bash "$SP/repin_loop_generic.sh" "$TF/tfrl_i1_repin_smoke.sh" "$RD" slurp-native-stage3-tfrl-loop-i$ITER-fold-b-smoke-4-v1 smoke-generation "/home/chao/$SHORT-smoke-commit.txt" || exit $?
    bash "$SP/repin_loop_generic.sh" "$TF/tfrl_i1_repin_arm.sh" "$RD" slurp-native-stage3-tfrl-loop-i$ITER-fold-b-v1 generation "/home/chao/$SHORT-arm-commit.txt" || exit $?
  else
    case " $KINDS " in *" typed "*)
      bash "$SP/repin_loop_generic.sh" "$TF/tfrl_i1_repin_typed.sh" "$RD" slurp-native-stage3-tfrl-proposer-i$ITER-v1 typed-generation "/home/chao/$SHORT-typed-commit.txt" || exit $? ;;
    esac
    case " $KINDS " in *" ace "*)
      bash "$SP/repin_loop_generic.sh" "$TF/tfrl_i1_repin_ace.sh" "$RD" slurp-native-stage3-tfrl-ace-reflector-i$ITER-v1 ace-generation "/home/chao/$SHORT-ace-commit.txt" || exit $? ;;
    esac
  fi
  AFTER=$(git rev-parse HEAD)
  echo "######## convergence pass $pass: HEAD ${BEFORE:0:8} -> ${AFTER:0:8}"
  if [ "$BEFORE" = "$AFTER" ]; then CONVERGED=$AFTER; break; fi
done
[ -n "$CONVERGED" ] || { echo "did not converge at one HEAD after four passes"; exit 5; }
echo "$CONVERGED" > /home/chao/$SHORT-$WHICH-flight-commit.txt
echo "flight commit $CONVERGED ($LABEL cells ready at it)"
