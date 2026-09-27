#!/bin/bash
# Unattended batch driver (owner directive 2026-09-19: queue 20+ GPU hours and fly them step by step).
# Reads /home/chao/batch-queue.json (an ordered list of steps), flies each step on the resident session from the
# pinned batch flight worktree, checks structure between steps, and STOPS on the first failure (no automatic
# recovery: the one-recovery rule needs a named root cause). Runs as a Windows Scheduled Task (SAEA-Batch-Driver).
#
# Queue step fields: order, short, kind (cell|resume), experiment, cell, smoke_experiment (or null), smoke_cell,
#   campaign_plan (repo-relative), run_id, fit_run_id, gen_attempt_id, smoke_run_id, smoke_attempt_id,
#   expected_rows, contacts_per_row, ceiling_per_row, notool (true|false), owner.
#   Optional smoke_notool overrides notool for a smoke with different tool authority.
#   result_kind defaults to task-answer; artifact requires zero scoring jobs and
#   verified finalized artifact bytes. smoke_result_kind defaults to result_kind.
# Status: /home/chao/batch-status.jsonl (one line per event); STOP marker: /home/chao/batch-STOP.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
export MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
# Reuse an existing clean frozen checkout while retaining an older failed source.
# 2026-09-26: the override is NAMED in the log and validated below. A stale override left by a
# previous flight (one pointed at a worktree whose admin dir had been pruned) made this driver stop
# with "worktree HEAD  != flight commit" -- an EMPTY head -- which says nothing about the cause.
REPO_OVERRIDE=""
if [ -f /home/chao/batch-flight-repo.txt ]; then
  export REPO="$(cat /home/chao/batch-flight-repo.txt)"
  REPO_OVERRIDE=/home/chao/batch-flight-repo.txt
else
  export REPO=/home/chao/saea-worktrees/fable-batch-flight
fi
export FLIGHT_COMMIT=$(cat /home/chao/batch-flight-commit.txt)
export DATA=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
export LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO/src
export PY=/home/chao/.venvs/speechrl/bin/python
export SESSION=${BATCH_SESSION:-serving-slurp-native-candidate-five-train-a-np4-v1}
QUEUE=/home/chao/batch-queue.json
STATUS=/home/chao/batch-status.jsonl
STOP=/home/chao/batch-STOP
DONE_MARK=/home/chao/batch-done

log() {
  local mode=()
  [ "${3:-}" = "--text" ] && mode=(--text)
  "$PY" -B "$SP/batch_jsonl_log.py" "$1" "${2:-null}" "${mode[@]}" >> "$STATUS"
  echo "$(date -u +%T) $1 ${2:-}"
}
stop() { log "STOP" "$1" --text; echo "$(date -u +%FT%TZ) $1" > "$STOP"; exit 9; }

[ -f "$STOP" ] && { echo "STOP marker present; refusing to run: $(cat $STOP)"; exit 8; }
if [ -n "$REPO_OVERRIDE" ]; then
  echo "$(date -u +%T) flight worktree OVERRIDDEN to $REPO by $REPO_OVERRIDE (archive that file to fall back to fable-batch-flight)"
fi
[ -d "$REPO" ] || stop "batch flight worktree missing: $REPO${REPO_OVERRIDE:+ (named by the stale override $REPO_OVERRIDE -- archive it)}"
cd "$REPO" || stop "cannot cd $REPO"
# A pruned worktree admin dir makes every git call inside $REPO fail; without this the HEAD compare
# below reports an empty head. Remedy: rm -rf the checkout and re-add it from INSIDE WSL with
# git worktree add --detach "$REPO" "$FLIGHT_COMMIT" (git worktree repair cannot restore a deleted
# admin dir).
git rev-parse --git-dir >/dev/null 2>&1 || stop "git does not work in $REPO: its worktree admin dir is missing or pruned${REPO_OVERRIDE:+, and this path came from the override $REPO_OVERRIDE}. Remedy: rm -rf '$REPO' && git -C $MAIN worktree add --detach '$REPO' '$FLIGHT_COMMIT' from inside WSL"
REPO_HEAD="$(git rev-parse HEAD 2>/dev/null)"
[ -n "$REPO_HEAD" ] || stop "cannot read HEAD in $REPO (empty rev-parse): the checkout is not a usable worktree"
[ "$REPO_HEAD" = "$FLIGHT_COMMIT" ] || stop "worktree HEAD ${REPO_HEAD:0:8} != flight commit ${FLIGHT_COMMIT:0:8}${REPO_OVERRIDE:+ (worktree named by the override $REPO_OVERRIDE)}"
[ -z "$(git status --short | grep -v '^??')" ] || stop "batch flight worktree has tracked changes"
log "driver-start" "{\"flight_commit\":\"$FLIGHT_COMMIT\",\"queue\":\"$QUEUE\"}"

N=$($PY -c "import json;print(len(json.load(open('$QUEUE'))))")
field() { $PY -c "import json,sys;d=json.load(open('$QUEUE'))[$1];v=d.get('$2');print('' if v is None else (str(v).lower() if isinstance(v,bool) else v))"; }

# Owner decision 163: no step flies unless its registration is complete -- every generation and FIT
# row of the arm, the smoke and every campaign-plan cell ROOT COUNTERSIGNED (never a draft), the
# decision receipt each row names present under $DATA with the run id eligible, and the package's
# analysis recipe declaring a READ run id whose ledger row exists (it may stay a draft until the
# seal). The gate is the main checkout's copy, run against the flight worktree's own tree, because
# the ledger the runtime reads is the flight commit's. Already-flown (resume) cells pass as
# report-only. Before 2026-09-27 two defects slipped through without it: ROLL-3 flew on draft rows,
# and AGREE / KPROBE / ROLL-3 had their READ rows registered only after the seal.
REGCHECK=$MAIN/scripts/checks/flight_registration_check.py
registration_gate() {  # $1 order; reads the step's exp / cell / sexp / scell / plan
  [ -f "$REGCHECK" ] || stop "flight registration gate missing: $REGCHECK"
  local args=(--repo-root "$REPO" --data-root "$DATA" --cell "$exp:$cell")
  if [ -n "$sexp" ] && [ "$sexp" != "None" ]; then args+=(--cell "$sexp:$scell"); fi
  if [ -n "$plan" ] && [ "$plan" != "None" ]; then args+=(--campaign-plan "$REPO/$plan"); fi
  local out rc report=/home/chao/batch-regcheck-$1.out
  out=$("$PY" -B "$REGCHECK" "${args[@]}" 2>&1); rc=$?
  printf '%s\n' "$out" > "$report"
  [ $rc -eq 0 ] || stop "flight registration gate REFUSED step $1 (exit $rc): $(printf '%s\n' "$out" | grep -E '^ +\[|ERROR' | head -4 | tr -s ' ' | tr '\n' ';' | cut -c1-700) -- countersign every flight row, mint the decision receipt with every run id eligible, and declare the READ run id (recipe run_ids.read) with its ledger row before launch; full report $report"
  log "registration-gate-ok" "{\"step\":$1}"
}

prelaunch() {
  [ -e "$DATA/locks/flight.lock" ] && stop "flight.lock present before step $1"
  [ -z "$(pgrep -af 'core.flight.cli|lease_cli' | grep -v pgrep)" ] || stop "a flight or lease process is alive before step $1"
  local ok; ok=$(cd "$MAIN" && bash scripts/serving_session.sh status --session-id $SESSION 2>/dev/null | $PY -c "import json,sys;d=json.load(sys.stdin);m=d.get('last_monitor_sample') or {};print(m.get('server_ok'), (m.get('slots') or {}).get('busy'), (d.get('session') or {}).get('session_id'))" 2>/dev/null)
  case "$ok" in "True 0 $SESSION") ;; *) stop "serving session not idle/healthy before step $1: $ok";; esac
  registration_gate "$1"
  # Do not allocate a second CUDA context for a synthetic warmup beside the model.
  # The shared transport and tokenizer check the opted-in resident resource receipt.
  log "prelaunch-ok" "{\"step\":$1,\"warmup\":\"registered-model-work-only\"}"
}

fly_smoke() {  # $1 order $2 smoke_experiment $3 smoke_cell $4 owner
  local exp=$2 cell=$3 owner=$4 token=$DATA/coordination/$3.worker-lease.json fifo=/home/chao/batch-smoke-$1.fifo
  rm -f "$fifo"; mkfifo "$fifo"
  ( exec 3<>"$fifo"; $PY -B -m speech_aware_evidence_acquisition.core.flight.lease_cli --stage worker \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --experiment "$exp" --cell "$cell" --owner "root-$cell" --expected-session-id "$SESSION" \
      --token-output "coordination/$cell.worker-lease.json" <&3 > /home/chao/batch-smoke-$1-lease.out 2>&1 ) &
  local lpid=$!
  local w; for w in $(seq 1 90); do [ -f "$token" ] && break; sleep 1; done  # never reuse the outer step index (2026-09-23: it ended a two-step queue after step 1)
  [ -f "$token" ] || { kill $lpid 2>/dev/null; stop "smoke lease token never appeared for step $1 ($(tail -c 300 /home/chao/batch-smoke-$1-lease.out))"; }
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --experiment "$exp" --cell "$cell" --expected-session-id "$SESSION" --lease-token-file "$token" \
      > /home/chao/batch-smoke-$1-worker.log 2>&1
  local rc=$?
  timeout 5 bash -c "echo release > $fifo" >/dev/null 2>&1; sleep 3; wait $lpid 2>/dev/null
  [ -f "$token" ] && stop "smoke lease token still present after release (step $1)"
  log "smoke-worker-exit" "{\"step\":$1,\"rc\":$rc}"
  [ $rc -eq 0 ] || stop "smoke worker exit $rc on step $1 ($(grep -v 'graph_vertex\|graph_id' /home/chao/batch-smoke-$1-worker.log | grep -i 'error' | tail -1 | cut -c1-300))"
}

for ((i=0; i<N; i++)); do
  order=$(field $i order); short=$(field $i short); kind=$(field $i kind); exp=$(field $i experiment); cell=$(field $i cell)
  sexp=$(field $i smoke_experiment); scell=$(field $i smoke_cell); plan=$(field $i campaign_plan); run=$(field $i run_id)
  gatt=$(field $i gen_attempt_id); srun=$(field $i smoke_run_id); satt=$(field $i smoke_attempt_id)
  rows=$(field $i expected_rows); ceil=$(field $i ceiling_per_row); notool=$(field $i notool); owner=$(field $i owner)
  [ "$notool" = "true" ] && nt=1 || nt=0
  result_kind=$(field $i result_kind); result_kind=${result_kind:-task-answer}
  smoke_result_kind=$(field $i smoke_result_kind); smoke_result_kind=${smoke_result_kind:-$result_kind}
  case "$result_kind" in task-answer|artifact) ;; *) stop "invalid result_kind on step $order" ;; esac
  case "$smoke_result_kind" in task-answer|artifact) ;; *) stop "invalid smoke_result_kind on step $order" ;; esac
  if grep -q "\"step-done\".*\"short\":\"$short\"" "$STATUS" 2>/dev/null; then log "step-skip-done" "{\"step\":$order,\"short\":\"$short\"}"; continue; fi
  log "step-start" "{\"step\":$order,\"short\":\"$short\",\"kind\":\"$kind\",\"cell\":\"$cell\"}"
  prelaunch $order
  if [ -n "$sexp" ] && [ "$sexp" != "None" ]; then
    smoke_notool=$(field $i smoke_notool)
    [ -n "$smoke_notool" ] || smoke_notool=$notool
    case "$smoke_notool" in true) smoke_nt=1 ;; false) smoke_nt=0 ;; *) stop "invalid smoke_notool on step $order" ;; esac
    fly_smoke $order "$sexp" "$scell" "$owner"
    out=$($PY -B $SP/batch_inspect.py "$DATA" "$srun" "$satt" smoke 4 "$ceil" $smoke_nt "$FLIGHT_COMMIT" --result-kind "$smoke_result_kind"); rc=$?
    log "smoke-inspect" "$out"
    [ $rc -eq 0 ] || stop "smoke structural check failed on step $order"
    sleep 10
  fi
  LOGF=/home/chao/batch-campaign-$order-$short-$(date -u +%Y%m%dT%H%M%SZ).log
  log "arm-start" "{\"step\":$order,\"log\":\"$LOGF\"}"
  $PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
    --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
    --campaign-plan "$REPO/$plan" --owner "$owner" --expected-session-id "$SESSION" > "$LOGF" 2>&1
  rc=$?
  log "arm-exit" "{\"step\":$order,\"rc\":$rc}"
  out=$($PY -B $SP/batch_inspect.py "$DATA" "$run" "$gatt" arm "$rows" "$ceil" $nt "$FLIGHT_COMMIT" --result-kind "$result_kind"); irc=$?
  log "arm-inspect" "$out"
  [ $rc -eq 0 ] && [ $irc -eq 0 ] || stop "arm failed on step $order (campaign rc $rc, inspect rc $irc); see $LOGF"
  log "step-done" "{\"step\":$order,\"short\":\"$short\"}"
  sleep 20
done
log "driver-done" "{\"steps\":$N}"
date -u +%FT%TZ > "$DONE_MARK"
