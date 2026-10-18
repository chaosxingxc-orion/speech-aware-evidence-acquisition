#!/bin/bash
# Queue hook (owner ruling 333 B: the carrier base runs after NX-T R3 and before the decoding column). NOT INSTALLED by the build; the coordinator copies it to
# /home/chao/saea-queue/ and starts it with the predecessor's start stamp. It starts the carrier chain (P3.3: A2T -> E21 -> E22, SAEA-Chain-CARRIERTHINK) the moment a NAMED
# predecessor chain has exited rc 0, flips the nine carrier cells on ext4 and starts the Windows chain task.
#
#   bash queue_carriers_after.sh <predecessor-chain-out> <predecessor-exit-tag> <start-stamp-UTC> [--register]
#       e.g. queue_carriers_after.sh /home/chao/nxtr3-chain.out CHAIN_NXTR3_EXIT 2026-10-21T08:00:00Z --register
#
# It polls (60 s, at most 72 h) <predecessor-chain-out> for the first line `<exit-tag> rc=<N> <UTC>` whose timestamp is LATER than the start stamp (the lines of earlier attempts
# are ignored):
#   rc=0      -> go on;     rc!=0 -> log it and exit 9 WITHOUT launching (a predecessor failure is the coordinator's to diagnose; the carriers never follow a failed predecessor);
#   no line within 72 h -> log it and exit 8 without launching.
# Before it acts it refuses (exit 9) when: the master tree is dirty, a flight process or flight.lock exists, or the P3.2 Thinking packets are not promoted and pinnable
# (`carrier_think_derive_cells.py --no-write --require-receipts` exits non-zero: the packets chain has not run or sealed).
# --register: the hook also runs the registration steps of the package (derive .. commit, with --root-countersign) -- the coordinator's act, delegated by passing this flag at
# install time. Without it the package must already be registered: the minted receipt must exist on the data root.
# Then: the flip (`flip_package_ext4.sh --flip carrier_think_flip.sh`) with its log parsed -- a gate block with one `check: PASS` per cell, FLIP_CHAIN_DONE, master at the flight
# commit, and NO failure line. The failure grep EXCLUDES the informational line `repin exit N (1 = its internal check refused the dirty tree, expected)`, which every healthy
# re-pin prints (the false refusal of the 2026-10-17 R2 rec2 hook); then the Windows task SAEA-Chain-CARRIERTHINK is started.
# Exit codes: 0 launched; 8 timed out; 9 refused; 64 usage; other = a step's own code.
#
# Test hooks (environment): CARRIER_HOOK_MAIN, CARRIER_HOOK_OUT, CARRIER_HOOK_POLL_SECONDS, CARRIER_HOOK_MAX_WAIT_SECONDS, CARRIER_HOOK_SETTLE_SECONDS, CARRIER_HOOK_DATA,
# CARRIER_HOOK_FLIP_LOG, CARRIER_HOOK_FLIP_CMD, CARRIER_HOOK_START_CMD, CARRIER_HOOK_REGISTER_CMD, CARRIER_HOOK_PACKETS_CMD, CARRIER_HOOK_ALIVE_CMD.
set -u
PRED_OUT=${1:-}; EXIT_TAG=${2:-}; STAMP=${3:-}; REGISTER=${4:-}
{ [ -n "$PRED_OUT" ] && [ -n "$EXIT_TAG" ] && [ -n "$STAMP" ]; } || { echo "usage: queue_carriers_after.sh <predecessor-chain-out> <predecessor-exit-tag> <start-stamp-UTC> [--register]" >&2; exit 64; }
case "$REGISTER" in ""|--register) ;; *) echo "unknown option $REGISTER" >&2; exit 64 ;; esac
M=${CARRIER_HOOK_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
OUT=${CARRIER_HOOK_OUT:-/home/chao/carrierthink-queue.out}
POLL=${CARRIER_HOOK_POLL_SECONDS:-60}
MAX_WAIT=${CARRIER_HOOK_MAX_WAIT_SECONDS:-259200}
SETTLE=${CARRIER_HOOK_SETTLE_SECONDS:-120}
DATA=${CARRIER_HOOK_DATA:-/home/chao/saea-data/speechrl-data}
FLIP_LOG=${CARRIER_HOOK_FLIP_LOG:-/home/chao/carrierthink-flip.out}
FLIGHT_COMMIT=/home/chao/carrierthink-flight-commit.txt
PKG=docs/readiness/2026-10-18-carrier-base-thinking-v1
CELLS=carrier-think-base-a2t-smoke-4-v1,carrier-think-base-a2t-alloff-v1,carrier-think-base-a2t-direct-v1,carrier-think-base-e21-smoke-4-v1,carrier-think-base-e21-alloff-v1,carrier-think-base-e21-direct-v1,carrier-think-base-e22-smoke-4-v1,carrier-think-base-e22-alloff-v1,carrier-think-base-e22-direct-v1
SPEC=scripts/flights/carriers/carrier_think_base_launch_spec.json
PS1_WIN='D:\chao_workspace\exploring-l4-intelligence\studies\speech-aware-evidence-acquisition\scripts\flights\batch\saea_task.ps1'
INFO_LINE='repin exit [0-9]* (1 = its internal check refused the dirty tree, expected)'
say() { echo "$(date -u +%FT%TZ) queue_carriers: $*" >> "$OUT"; }
exit_line() { awk -v s="$STAMP" -v t="$EXIT_TAG" '$1 == t && $3 > s { sub("rc=", "", $2); print $2; exit }' "$PRED_OUT" 2>/dev/null; }

say "armed: waiting for $EXIT_TAG after $STAMP in $PRED_OUT (poll ${POLL}s, at most ${MAX_WAIT}s)${REGISTER:+; will register (--root-countersign)}"
waited=0
while :; do
  rc=$(exit_line)
  [ -n "$rc" ] && break
  [ "$waited" -ge "$MAX_WAIT" ] && { say "TIMEOUT: no $EXIT_TAG line after $STAMP; the carrier chain is NOT launched"; exit 8; }
  sleep "$POLL"; waited=$((waited + ${POLL%.*})); [ "${POLL%.*}" -gt 0 ] 2>/dev/null || waited=$((waited + 1))
done
[ "$rc" = 0 ] || { say "predecessor exited rc=$rc; the carrier chain is NOT launched (coordinator decides)"; exit 9; }
say "predecessor exit rc=0 seen; waiting ${SETTLE}s for the seal-side processes to drain"; sleep "$SETTLE"

cd "$M" || { say "cannot cd to $M"; exit 9; }
[ -f /home/chao/.venvs/speechrl/bin/activate ] && source /home/chao/.venvs/speechrl/bin/activate
export PYTHONDONTWRITEBYTECODE=1 SPEECHRL_DATA_DIR=$DATA SAEA_DATA_ROOT=$DATA
[ "$(git status --porcelain | wc -l)" = 0 ] || { say "master dirty; NOT launched"; exit 9; }
if [ -n "${CARRIER_HOOK_ALIVE_CMD:-}" ]; then alive=$(bash -c "$CARRIER_HOOK_ALIVE_CMD"); else alive=$(pgrep -af 'core.flight.cli|batch_driver|lease_cli' | grep -v pgrep); fi
[ -z "$alive" ] || { say "a flight process is alive; NOT launched"; exit 9; }
[ -e "$DATA/locks/flight.lock" ] && { say "flight.lock present; NOT launched"; exit 9; }

PACKETS_CMD=${CARRIER_HOOK_PACKETS_CMD:-"python -B scripts/flights/carriers/carrier_think_derive_cells.py --no-write --require-receipts"}
bash -c "$PACKETS_CMD" >> "$OUT" 2>&1 || { say "the P3.2 Thinking packets are not promoted and pinnable (--require-receipts refused); run the packets chain first; NOT launched"; exit 9; }

if [ "$REGISTER" = "--register" ]; then
  REG_CMD=${CARRIER_HOOK_REGISTER_CMD:-"bash scripts/flights/batch/package_launch.sh $SPEC --root-countersign --until commit"}
  say "registering the package (derive .. commit, --root-countersign): $REG_CMD"
  bash -c "$REG_CMD" >> "$OUT" 2>&1; frc=$?
  [ $frc -eq 0 ] || { say "registration exited rc=$frc; NOT launched"; exit 9; }
else
  [ -s "$DATA/coordination/carrier-base-thinking-v1/root-admission-v1.json" ] || { say "the package is not registered (no minted receipt) and --register was not given; NOT launched"; exit 9; }
fi

FLIP_CMD=${CARRIER_HOOK_FLIP_CMD:-"bash scripts/flights/batch/flip_package_ext4.sh --flip scripts/flights/carriers/carrier_think_flip.sh --package $PKG --cells $CELLS --pins-commit-msg /home/chao/carrierthink-pins-commit.txt --log $FLIP_LOG"}
say "flip: the nine carrier cells"
bash -c "$FLIP_CMD" >> "$OUT" 2>&1; frc=$?
# The failure grep drops the informational line first; every other 'refus' / FAIL still counts.
bad=$(grep -v "$INFO_LINE" "$FLIP_LOG" 2>/dev/null | grep -i -E "check: FAIL|GATE FAILED|REFUS|refus|DID NOT CONVERGE|FLIGHT COMMIT MISMATCH|NOT A FIXED POINT" | head -1)
passes=$(grep -c "check: PASS" "$FLIP_LOG" 2>/dev/null)
if [ $frc -ne 0 ] || [ -n "$bad" ] || ! grep -q "FLIP_CHAIN_DONE" "$FLIP_LOG" 2>/dev/null || [ "${passes:-0}" -lt 9 ] || [ "$(git rev-parse HEAD)" != "$(cat "$FLIGHT_COMMIT" 2>/dev/null)" ]; then
  say "flip not converged (rc=$frc, gate PASS lines ${passes:-0}/9${bad:+, failure line: ${bad:0:160}}); see $FLIP_LOG; NOT launched"; exit 9
fi
say "flip converged at $(git rev-parse HEAD)"
grep -q "batch_chain_carrier_think.sh" /home/chao/saea-queue/chain_carrierthink.sh 2>/dev/null || [ -n "${CARRIER_HOOK_START_CMD:-}" ] || { say "the chain wrapper /home/chao/saea-queue/chain_carrierthink.sh is missing or wrong; NOT launched"; exit 9; }
START_CMD=${CARRIER_HOOK_START_CMD:-"powershell.exe -NoProfile -NonInteractive -Command \"& '$PS1_WIN' -Name SAEA-Chain-CARRIERTHINK -Start\""}
bash -c "$START_CMD" >> "$OUT" 2>&1 || { say "task start failed"; exit 9; }
say "SAEA-Chain-CARRIERTHINK started; done"
exit 0
