#!/bin/bash
# Unattended batch driver (owner directive 2026-09-19: queue 20+ GPU hours and fly them step by step).
# Reads /home/chao/batch-queue.json (an ordered list of steps), flies each step on the resident session from the
# pinned batch flight worktree, checks structure between steps, and STOPS on the first failure (no automatic
# recovery: the one-recovery rule needs a named root cause). Runs as a Windows Scheduled Task (SAEA-Batch-Driver).
#
# Queue step fields: order, short, kind (cell|resume|seal-only|engineering), experiment, cell, smoke_experiment (or null), smoke_cell,
#   campaign_plan (repo-relative), run_id, fit_run_id, gen_attempt_id, smoke_run_id, smoke_attempt_id,
#   expected_rows, contacts_per_row, ceiling_per_row, notool (true|false), owner.
#   kind seal-only (2026-09-29, COMP-1 seal-only completion): a resume cell whose declared resume_from
#   predecessors already cover the whole roster. The step runs `core.flight.cli seal-only --experiment
#   --cell` (zero model contacts; no lease, no slot, no session attach; it seals the merged manifest and
#   runs the one official finalize job) instead of `cli campaign`. It must declare no smoke (a smoke would
#   fly contacts the completion does not need) and no campaign_plan (the registration gate then runs on
#   --cell alone), and its cell must declare resume_from, so the resume replay gate always runs first.
#   prelaunch is unchanged: it still requires the resident session idle and healthy (the resident SLURP
#   np4 satisfies it; the seal-only step itself never touches the session).
#   Optional smoke_notool overrides notool for a smoke with different tool authority.
#   kind engineering runs only its registered four-row smoke through the same worker and
#   structural inspector. It never starts a campaign or a scoring job. Arm identifiers
#   must equal the smoke identifiers, and campaign_plan must be absent.
#   result_kind defaults to task-answer; artifact requires zero scoring jobs and
#   verified finalized artifact bytes. smoke_result_kind defaults to result_kind.
#   Optional process_start_gib and process_floor_gib opt one ordinary member into
#   the shared owned-process memory supervisor; both are required. An ordinary
#   guarded campaign member has no separate smoke; an exact campaign_plan supervises all members. An engineering member
#   guards only its identical four-row worker under the existing lease.
#   Optional paired process_start_wait_seconds/process_start_stable_samples wait
#   before prelaunch for stable memory. The observer starts no worker and never
#   retries a failed process. The original guard still checks the startup floor.
# A node-panel step joins every exact member of its committed plan under one
# guarded process and one generation lease, then inspects every member.
# Status: /home/chao/batch-status.jsonl (one line per event); STOP marker: /home/chao/batch-STOP.
SP=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition/scripts/flights/batch
export MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
source "$SP/resume_gate_lib.sh"
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
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh" || exit 70  # decision 274: the one data-root authority
saea_data_root_init || exit 70
export DATA=$SAEA_DATA_ROOT
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
RESUMEGATE=$SP/resume_prelaunch_gate.sh
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
  # Coordinator, after the COMP-1 resume attempt 3 seal abort: a 4-row smoke cannot see seal-time
  # checks on kept rows, so EVERY resume launch first passes the OFFLINE full-trace replay check.
  # A no-op (RESUMEGATE never invoked) for a step whose experiment config declares no resume_from
  # on cell $cell -- resume_gate_run (scripts/flights/batch/resume_gate_lib.sh) does the scoping.
  resume_gate_run "$1" "$REPO" "$DATA" "$exp" "$cell" "$RESUMEGATE" "/home/chao/batch-resumegate-$1.out"
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
  local rc
  if [ -n "$process_start" ]; then
    local guard_dir="$DATA/coordination/process-guard/smoke-$1-$cell-$(date -u +%Y%m%dT%H%M%SZ)"
    $PY -B -m speech_aware_evidence_acquisition.core.flight.process_guard --mode worker \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --experiment "$exp" --owner "$owner" --expected-session-id "$SESSION" --lease-token-file "$token" \
      "${diagnostic_args[@]}" --receipt-dir "$guard_dir" --start-gib "$process_start" --floor-gib "$process_floor" \
      > /home/chao/batch-smoke-$1-worker.log 2>&1
    rc=$?
    if [ $rc -ne 0 ]; then
      timeout 5 bash -c "echo preserve > $fifo" >/dev/null 2>&1; wait $lpid 2>/dev/null
      log "smoke-worker-exit" "{\"step\":$1,\"rc\":$rc,\"lease_preserved\":true}"
      stop "guarded smoke worker exit $rc on step $1; preserve lease and evidence"
    fi
  else
    $PY -B -m speech_aware_evidence_acquisition.core.flight.cli worker \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --experiment "$exp" --cell "$cell" --expected-session-id "$SESSION" --lease-token-file "$token" \
      > /home/chao/batch-smoke-$1-worker.log 2>&1
    rc=$?
  fi
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
  diagnostic_args=()
  diagnostics=$(field $i process_memory_diagnostics)
  [ "$diagnostics" = "true" ] && diagnostic_args+=(--memory-diagnostics)
  process_start=$(field $i process_start_gib); process_floor=$(field $i process_floor_gib)
  process_wait=$(field $i process_start_wait_seconds); process_stable=$(field $i process_start_stable_samples)
  [ "$notool" = "true" ] && nt=1 || nt=0
  result_kind=$(field $i result_kind); result_kind=${result_kind:-task-answer}
  smoke_result_kind=$(field $i smoke_result_kind); smoke_result_kind=${smoke_result_kind:-$result_kind}
  case "$result_kind" in task-answer|artifact) ;; *) stop "invalid result_kind on step $order" ;; esac
  case "$smoke_result_kind" in task-answer|artifact) ;; *) stop "invalid smoke_result_kind on step $order" ;; esac
  if grep -q "\"step-done\".*\"short\":\"$short\"" "$STATUS" 2>/dev/null; then log "step-skip-done" "{\"step\":$order,\"short\":\"$short\"}"; continue; fi
  log "step-start" "{\"step\":$order,\"short\":\"$short\",\"kind\":\"$kind\",\"cell\":\"$cell\"}"
  case "$kind" in cell|resume|seal-only|engineering|node-panel|node-panel-worker) ;; *) stop "invalid kind on step $order" ;; esac
  if { [ "$kind" = "node-panel" ] || [ "$kind" = "node-panel-worker" ]; }; then
    [ -n "$plan" ] && [ "$plan" != "None" ] || stop "node panel step $order requires its complete registered plan"
    [ -n "$process_start" ] && [ -n "$process_floor" ] || stop "node panel step $order requires both memory floors"
    { [ -z "$sexp" ] || [ "$sexp" = "None" ]; } || stop "node panel step $order cannot declare a separate smoke"
  fi
  if [ "$kind" = "engineering" ]; then
    [ "$rows" = "4" ] && [ "$sexp" = "$exp" ] && [ "$scell" = "$cell" ] && \
      [ "$srun" = "$run" ] && [ "$satt" = "$gatt" ] || stop "engineering step $order must bind one identical four-row smoke"
    { [ -z "$plan" ] || [ "$plan" = "None" ]; } || stop "engineering step $order cannot declare a campaign_plan"
  fi
  if [ "$kind" = "seal-only" ]; then
    { [ -z "$sexp" ] || [ "$sexp" = "None" ]; } || stop "seal-only step $order declares a smoke; a seal-only completion flies nothing"
    { [ -z "$plan" ] || [ "$plan" = "None" ]; } || stop "seal-only step $order declares a campaign_plan; it runs core.flight.cli seal-only on --cell"
    [ "$(resume_gate_declared "$REPO" "$exp" "$cell")" = "yes" ] || stop "seal-only step $order: $exp:$cell declares no resume_from"
  fi
  if [ -n "$process_start" ] || [ -n "$process_floor" ]; then
    [ -n "$process_start" ] && [ -n "$process_floor" ] || stop "step $order needs both process memory floors"
    case "$kind" in cell|resume|engineering|node-panel|node-panel-worker) ;; *) stop "step $order process guard requires campaign or identical engineering worker" ;; esac
    if [ "$kind" != "node-panel" ] && [ "$kind" != "node-panel-worker" ]; then
      if [ -n "$plan" ] && [ "$plan" != "None" ]; then
        [ "$kind" = "cell" ] || stop "step $order guarded campaign plan requires ordinary campaign kind"
      fi
    fi
    if [ "$kind" != "engineering" ]; then
      { [ -z "$sexp" ] || [ "$sexp" = "None" ]; } || stop "step $order process guard cannot leave a separate smoke unsupervised"
    fi
  fi
  if [ -n "$process_wait" ] || [ -n "$process_stable" ]; then
    [ -n "$process_start" ] && [ -n "$process_floor" ] && [ -n "$process_wait" ] && [ -n "$process_stable" ] || stop "step $order needs complete guarded memory-wait policy"
    WAIT_DIR="$DATA/coordination/start-memory-wait/step-$order-$short-$(date -u +%Y%m%dT%H%M%SZ)"
    log "memory-wait-start" "{\"step\":$order,\"receipt_dir\":\"$WAIT_DIR\"}"
    out=$($PY -B "$SP/wait_for_start_memory.py" --data-root "$DATA" --receipt-dir "$WAIT_DIR" \
      --stop-marker "$STOP" --start-gib "$process_start" --floor-gib "$process_floor" --wait-seconds "$process_wait" \
      --stable-samples "$process_stable" 2>&1); rc=$?
    [ $rc -eq 0 ] || stop "precontact memory wait refused step $order (exit $rc): $out"
    log "memory-wait-ok" "$out"
  fi
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
  if [ "$kind" = "engineering" ]; then
    log "step-done" "{\"step\":$order,\"short\":\"$short\",\"engineering_only\":true}"
    continue
  fi
  LOGF=/home/chao/batch-campaign-$order-$short-$(date -u +%Y%m%dT%H%M%SZ).log
  log "arm-start" "{\"step\":$order,\"log\":\"$LOGF\"}"
  if [ "$kind" = "seal-only" ]; then
    $PY -B -m speech_aware_evidence_acquisition.core.flight.cli seal-only \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --experiment "$exp" --cell "$cell" > "$LOGF" 2>&1
  elif { [ "$kind" = "node-panel" ] || [ "$kind" = "node-panel-worker" ]; }; then
    GUARD_DIR="$DATA/coordination/process-guard/$(basename "$LOGF" .log)"
    $PY -B -m speech_aware_evidence_acquisition.core.flight.process_guard --mode "$kind" \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --campaign-plan "$REPO/$plan" --owner "$owner" --expected-session-id "$SESSION" \
      "${diagnostic_args[@]}" --receipt-dir "$GUARD_DIR" --start-gib "$process_start" --floor-gib "$process_floor" > "$LOGF" 2>&1
  elif [ -n "$process_start" ]; then
    GUARD_DIR="$DATA/coordination/process-guard/$(basename "$LOGF" .log)"
    campaign_identity_args=(--experiment "$exp")
    if [ -n "$plan" ] && [ "$plan" != "None" ]; then campaign_identity_args=(--campaign-plan "$REPO/$plan"); fi
    $PY -B -m speech_aware_evidence_acquisition.core.flight.process_guard \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      "${campaign_identity_args[@]}" --owner "$owner" --expected-session-id "$SESSION" \
      "${diagnostic_args[@]}" --receipt-dir "$GUARD_DIR" --start-gib "$process_start" --floor-gib "$process_floor" > "$LOGF" 2>&1
  elif [ -n "$plan" ] && [ "$plan" != "None" ]; then
    $PY -B -m speech_aware_evidence_acquisition.core.flight.cli campaign \
      --repo-root "$REPO" --data-root "$DATA" --runtime-root /home/chao --lock-path "$LOCK" \
      --campaign-plan "$REPO/$plan" --owner "$owner" --expected-session-id "$SESSION" > "$LOGF" 2>&1
  else
    stop "single-member step $order requires declared process memory floors"
  fi
  rc=$?
  log "arm-exit" "{\"step\":$order,\"rc\":$rc}"
  if { [ "$kind" = "node-panel" ] || [ "$kind" = "node-panel-worker" ]; }; then
    out=$($PY -B "$SP/node_panel_inspect.py" --mode "$kind" --repo-root "$REPO" --data-root "$DATA" \
      --campaign-plan "$REPO/$plan" --flight-commit "$FLIGHT_COMMIT" \
      --ceiling-per-row "$ceil" --notool "$nt" --result-kind "$result_kind"); irc=$?
  else
    inspection_args=()
    inspection_script="$SP/batch_inspect.py"
    if [ -n "$plan" ] && [ "$plan" != "None" ]; then
      inspection_script="$REPO/scripts/flights/batch/batch_inspect.py"
      inspection_args=(--repo-root "$REPO" --campaign-plan "$REPO/$plan")
    fi
    out=$($PY -B "$inspection_script" "$DATA" "$run" "$gatt" arm "$rows" "$ceil" $nt "$FLIGHT_COMMIT" --result-kind "$result_kind" "${inspection_args[@]}"); irc=$?
  fi
  log "arm-inspect" "$out"
  [ $rc -eq 0 ] && [ $irc -eq 0 ] || stop "arm failed on step $order (campaign rc $rc, inspect rc $irc); see $LOGF"
  log "step-done" "{\"step\":$order,\"short\":\"$short\"}"
  sleep 20
done
log "driver-done" "{\"steps\":$N}"
date -u +%FT%TZ > "$DONE_MARK"
