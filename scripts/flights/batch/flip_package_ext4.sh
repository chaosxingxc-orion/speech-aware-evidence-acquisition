#!/bin/bash
# Generic replacement for the hand-written queue flip wrappers: ONE ext4 worktree session runs the whole package flip, then master
# fast-forwards ONCE (via flip_in_ext4.sh, which keeps all of its refusals).
#
# Usage:
#   flip_package_ext4.sh --flip "<flip-script> [args...]" --package <readiness dir> --cells <cell1,cell2,...> --pins-commit-msg <file>
#                        [--mode iterate|one-pass] [--verify-fixed-point] [--log <path>] [-- KEY=VALUE ...]
#   --flip      repo-relative flip script, optionally followed by its arguments (e.g. "scripts/flights/tfrl/tfrl_i1_flip.sh column")
#   --package   repo-relative readiness directory for refresh_registered_plan_pins.py --package and the pins commit
#   --cells     comma-separated cells for flight_registration_check.py --cell (the gate step)
#   --pins-commit-msg  commit message file used if the pins refresh dirties the tree
#   --mode      iterate (DEFAULT until the owner flips it) runs the convergence loops below; one-pass (owner decision 270 A) runs the flip script ONCE
#               with FLIP_MODE=one-pass: the flip script computes the fixed point of every shared hash across the package, refreshes the plan pins,
#               writes everything once, commits ONCE and checks each cell once (core/flight/repin_onepass.py). Steps (1)-(3) below collapse into
#               that single run; --pins-commit-msg is still required but unused by one-pass. Supported by direct_fb_flip.sh and tfrl_i1_flip.sh.
#   --verify-fixed-point  one-pass only: afterwards run ONE iterative pass; it must commit nothing (a canary for the first real use; costs one
#               iterative pass of check time)
#   --log       milestone log (default /home/chao/<package-basename>-flip.out; truncated at start)
#   -- K=V ...  extra environment (in addition to the inherited DIRECT_FB_KINDS, TFRL_ITER, TFRL_ONLY, SAEA_ALLOW_9P_FLIP)
# Sequence inside the worktree: (1) flip convergence loop (<= 6 passes until a pass commits nothing and the tree is clean),
#   (2) refresh_registered_plan_pins.py + commit if dirty, (3) the convergence loop again, (4) per-cell registration gates,
#   (5) report the flight-commit file(s); then flip_in_ext4.sh fast-forwards master and this script verifies master HEAD.
# Exit codes: flip_in_ext4.sh's (2/3/4/5/64 refusals, 6 inner failure, 7/8 ff problems); 9 master HEAD does not match the reported
#   flight commit; 2 usage. Never merges, never pushes.
# Env overrides: SAEA_REFRESH_PINS (default "python -B scripts/flights/refresh_registered_plan_pins.py"),
#   SAEA_REGCHECK (default "python -B scripts/checks/flight_registration_check.py"), SAEA_FLIGHT_COMMIT_DIR (default /home/chao),
#   SAEA_FLIP_MASTER (as flip_in_ext4.sh).
SELF_REL=scripts/flights/batch/flip_package_ext4.sh
MASTER=${SAEA_FLIP_MASTER:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)}; export SAEA_FLIP_MASTER=$MASTER  # run it from the master checkout
CDIR=${SAEA_FLIGHT_COMMIT_DIR:-/home/chao}

if [ "$1" = "--inner" ]; then
  # ---- inner: runs inside the ext4 worktree (SAEA_MAIN = worktree), launched by flip_in_ext4.sh ----
  M=${SAEA_MAIN:?}; cd "$M" || exit 1
  [ -f ~/.venvs/speechrl/bin/activate ] && source ~/.venvs/speechrl/bin/activate
  export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$M/src
  source "$M/scripts/lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
  saea_data_root_init || exit 70
  LOG=$FPE_LOG; PKG=$FPE_PACKAGE
  REFRESH=${SAEA_REFRESH_PINS:-python -B scripts/flights/refresh_registered_plan_pins.py}
  REGCHECK=${SAEA_REGCHECK:-python -B scripts/checks/flight_registration_check.py}
  set -- $FPE_FLIP; FLIP=$1; shift
  MODE=${FPE_MODE:-iterate}
  [ -f "$FLIP" ] || { echo "flip script $FLIP is not tracked in the worktree" | tee -a "$LOG"; exit 2; }
  IMARK=$(mktemp /tmp/flip_package_ext4.mark.XXXXXX)
  echo "start $(date -u +%FT%TZ) HEAD $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l) (ext4 worktree $M)" | tee -a "$LOG"
  flip_loop() {
    local i before after rc
    for i in 1 2 3 4 5 6; do
      before=$(git rev-parse HEAD)
      echo "== flip pass $i at $before $(date -u +%H:%M:%SZ)" | tee -a "$LOG"
      bash "$FLIP" "$@" >> "$LOG" 2>&1; rc=$?
      after=$(git rev-parse HEAD); echo "   rc=$rc HEAD $after dirty=$(git status --porcelain | wc -l)" | tee -a "$LOG"
      if [ "$before" = "$after" ] && [ "$(git status --porcelain | wc -l)" = 0 ]; then
        # 2026-10-12: a REFUSED flip script (receipt missing, batch alive, check failed before any commit) also leaves HEAD
        # unchanged; that is not a convergence. Only a clean pass that exits 0 converges.
        [ $rc -eq 0 ] && return 0
        echo "FLIP SCRIPT REFUSED (rc=$rc) with HEAD unchanged: not a convergence" | tee -a "$LOG"; return 2
      fi
    done
    return 1
  }
  if [ "$MODE" = one-pass ]; then
    echo "== one-pass flip at $(git rev-parse HEAD) $(date -u +%H:%M:%SZ)" | tee -a "$LOG"
    FLIP_MODE=one-pass bash "$FLIP" "$@" >> "$LOG" 2>&1; rc=$?
    echo "   rc=$rc HEAD $(git rev-parse HEAD) dirty=$(git status --porcelain | wc -l)" | tee -a "$LOG"
    if [ $rc -ne 0 ] || [ "$(git status --porcelain | wc -l)" != 0 ]; then echo "ONE-PASS FLIP FAILED" | tee -a "$LOG"; rm -f "$IMARK"; exit 5; fi
    if [ "$FPE_VERIFY" = 1 ]; then
      before=$(git rev-parse HEAD)
      echo "== verify fixed point (one iterative pass)" | tee -a "$LOG"
      FLIP_MODE=iterate bash "$FLIP" "$@" >> "$LOG" 2>&1; rc=$?
      if [ $rc -ne 0 ] || [ "$before" != "$(git rev-parse HEAD)" ] || [ "$(git status --porcelain | wc -l)" != 0 ]; then
        echo "ONE-PASS RESULT IS NOT A FIXED POINT (rc=$rc, HEAD moved from $before)" | tee -a "$LOG"; rm -f "$IMARK"; exit 5
      fi
      echo "   fixed point confirmed" | tee -a "$LOG"
    fi
  else
    flip_loop "$@" || { echo "FLIP DID NOT CONVERGE" | tee -a "$LOG"; rm -f "$IMARK"; exit 5; }
    echo "== refresh plan pins" | tee -a "$LOG"
    $REFRESH --package "$PKG" >> "$LOG" 2>&1; echo "   refresh rc=$?" | tee -a "$LOG"
    if [ -n "$(git status --porcelain)" ]; then
      git add "$PKG" && git commit -q -F "$FPE_MSG" && echo "   pins committed $(git rev-parse --short HEAD)" | tee -a "$LOG"
    fi
    flip_loop "$@" || { echo "SECOND FLIP DID NOT CONVERGE" | tee -a "$LOG"; rm -f "$IMARK"; exit 5; }
  fi
  echo "== gate" | tee -a "$LOG"
  IFS=, read -ra CELLS <<< "$FPE_CELLS"
  GATE_FAIL=0
  for c in "${CELLS[@]}"; do
    gate_out=$($REGCHECK --cell "$c" 2>&1); gate_rc=$?
    echo "$gate_out" | grep "^\s*\[\|check:" | cut -c1-200 | tee -a "$LOG"
    if [ $gate_rc -ne 0 ] || echo "$gate_out" | grep -q "check: FAIL"; then GATE_FAIL=1; fi
  done
  # 2026-10-12: a failed gate is a failed flip (the 19:17Z run printed FLIP_CHAIN_DONE over three FAILed cells); master is not fast-forwarded.
  if [ $GATE_FAIL = 1 ]; then echo "GATE FAILED: master is NOT fast-forwarded (fix the cell, re-run the flip)" | tee -a "$LOG"; rm -f "$IMARK"; exit 7; fi
  FOUND=0
  for f in $(find "$CDIR" -maxdepth 1 -name '*flight-commit.txt' -newer "$IMARK" 2>/dev/null); do
    FOUND=1; echo "flight commit file: $(cat "$f") HEAD $(git rev-parse HEAD) ($f)" | tee -a "$LOG"
  done
  [ $FOUND = 1 ] || echo "flight commit file: (none written) HEAD $(git rev-parse HEAD)" | tee -a "$LOG"
  rm -f "$IMARK"
  exit 0
fi

# ---- outer ----
FLIP=; PKG=; CELLS=; MSG=; LOG=; MODE=iterate; VERIFY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --flip) FLIP=$2; shift 2 ;;
    --package) PKG=$2; shift 2 ;;
    --cells) CELLS=$2; shift 2 ;;
    --pins-commit-msg) MSG=$2; shift 2 ;;
    --log) LOG=$2; shift 2 ;;
    --mode) MODE=$2; shift 2 ;;
    --verify-fixed-point) VERIFY=1; shift ;;
    --) shift; break ;;
    *) echo "usage: flip_package_ext4.sh --flip <script [args]> --package <dir> --cells <c1,c2> --pins-commit-msg <file> [--mode iterate|one-pass] [--verify-fixed-point] [--log <path>] [-- KEY=VALUE ...]" >&2; exit 2 ;;
  esac
done
for kv in "$@"; do
  case "$kv" in [A-Za-z_][A-Za-z0-9_]*=*) export "$kv" ;; *) echo "bad extra env '$kv' (want KEY=VALUE)" >&2; exit 2 ;; esac
done
[ -n "$FLIP" ] && [ -n "$PKG" ] && [ -n "$CELLS" ] && [ -n "$MSG" ] || { echo "missing --flip/--package/--cells/--pins-commit-msg" >&2; exit 2; }
[ -f "$MSG" ] || { echo "pins commit message file $MSG not found" >&2; exit 2; }
case "$MODE" in iterate|one-pass) ;; *) echo "bad --mode '$MODE' (want iterate or one-pass)" >&2; exit 2 ;; esac
[ "$VERIFY" = 0 ] || [ "$MODE" = one-pass ] || { echo "--verify-fixed-point needs --mode one-pass" >&2; exit 2; }
PKG=${PKG%/}; [ -n "$LOG" ] || LOG=/home/chao/$(basename "$PKG")-flip.out
export FPE_MODE=$MODE FPE_VERIFY=$VERIFY FPE_FLIP=$FLIP FPE_PACKAGE=$PKG FPE_CELLS=$CELLS FPE_MSG=$(realpath "$MSG") FPE_LOG=$(realpath -m "$LOG")
: > "$FPE_LOG"
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OMARK=$(mktemp /tmp/flip_package_ext4.omark.XXXXXX)
OUT=$(mktemp /tmp/flip_package_ext4.out.XXXXXX)
# the inner already appends its milestone lines to the log; only the wrapper's own lines are added from this stream
bash "$HERE/flip_in_ext4.sh" "$SELF_REL" --inner 2>&1 | tee "$OUT"; RC=${PIPESTATUS[0]}
grep -E '^\[flip_in_ext4\]|^refusing|^flip script exited|^fast-forward' "$OUT" >> "$FPE_LOG"; rm -f "$OUT"
if [ $RC -ne 0 ]; then echo "flip_in_ext4 exit $RC; master untouched or unmerged (see above)" | tee -a "$FPE_LOG"; rm -f "$OMARK"; exit $RC; fi
MH=$(git -C "$MASTER" rev-parse HEAD)
for f in $(find "$CDIR" -maxdepth 1 -name '*flight-commit.txt' -newer "$OMARK" 2>/dev/null); do echo "$MH" > "$f"; done
REPORTED=$(grep -o 'HEAD [0-9a-f]\{40\}' "$FPE_LOG" | tail -1 | cut -d' ' -f2)
rm -f "$OMARK"
if [ -z "$REPORTED" ] || [ "$REPORTED" != "$MH" ]; then
  echo "FLIGHT COMMIT MISMATCH: reported ${REPORTED:-none} master HEAD $MH" | tee -a "$FPE_LOG"; exit 9
fi
echo "master verified at flight commit $MH" | tee -a "$FPE_LOG"
echo "FLIP_CHAIN_DONE $(date -u +%FT%TZ)" | tee -a "$FPE_LOG"
