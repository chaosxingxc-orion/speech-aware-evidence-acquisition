# shellcheck shell=bash
# Shared serving-lifecycle facts and predicates for the batch operations scripts (owner decision 163, track
# ENGINEERING: one swap tool, precise flight detection, health-verified restarts, sidecar ordering enforced).
# Source it; it defines variables and functions only and never acts on its own.
#
#   saea_geometry <target>           one row of the geometry table into G_* variables (1 = unknown target)
#   saea_target_for_session <sid>    the target whose session id is <sid> (1 = none)
#   saea_generation_flight_pids      the live GENERATION flight processes, one "pid argv" line each
#   saea_flight_alive                0 (and one reason per line) when a generation flight or flight.lock exists
#   saea_port_server_pids            the llama-server processes listening on the GPU serving port
#   saea_cpu_sidecars                every other llama-server plus the packet preprocess driver
#   saea_swap_pending                0 (and the marker) while a serving swap holds its pending marker
#   saea_sidecar_admission [ss]      decision 162: 0 only while a GPU session is resident, running, and no swap is
#                                    pending; otherwise one REFUSED line and 1
#   saea_powershell                  the Windows PowerShell interop binary (PATH first, then the canonical mount)
#
# Precise flight detection (2026-09-27 13:08Z): the old `pgrep -af 'core.flight.cli|batch_driver.sh'` also matched
# a model-free `core.flight.cli prepare-supply` / `check` run by an agent in a worktree and refused every swap. Only
# a generation flight blocks a swap: `core.flight.cli campaign|worker`, `batch_driver.sh`, `core.flight.lease_cli`,
# or `$DATA/locks/flight.lock`.
#
# Every path is overridable for the test harness (tests/unit/test_serving_swap.py); the defaults are this host's.

SAEA_MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
source "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../../lib/data_root.sh"  # decision 274: the one data-root authority
SAEA_DATA=${SAEA_DATA:-${SAEA_DATA_ROOT:-$SAEA_DATA_ROOT_DEFAULT}}
SAEA_RUNTIME_ROOT=${SAEA_RUNTIME_ROOT:-/home/chao}
SAEA_SERVING_HOST=127.0.0.1
SAEA_SERVING_PORT=8080
SAEA_SWAP_LOCK=${SAEA_SWAP_LOCK:-$SAEA_RUNTIME_ROOT/serving-swap.lock}
SAEA_SWAP_PENDING=${SAEA_SWAP_PENDING:-$SAEA_RUNTIME_ROOT/serving-swap.pending}
SAEA_TASK_PS1_WIN=${SAEA_TASK_PS1_WIN:-'D:\chao_workspace\exploring-l4-intelligence\studies\speech-aware-evidence-acquisition\scripts\flights\batch\saea_task.ps1'}
SAEA_TARGETS="slurp-np4 a2t-np3 e21-np4 det-np1 think-np4 think-budget-np4 think-budget7168-np4"
# The prospective owner floor is 4 GiB; preserve any explicit higher registered minimum.
SAEA_MIN_HOST_FREE_GB=${SAEA_MIN_HOST_FREE_GB:-4.0}

# The geometry table: one row per resident serving geometry this host swaps between. The fragment is the one the
# serving task entry starts; its -c/-np are the geometry /props must report (see serving_ready_probe.py).
saea_geometry() {
  G_TARGET=$1
  case "$1" in
    slurp-np4)
      G_LABEL=SLURP
      G_SID=serving-slurp-native-candidate-five-train-a-np4-v1
      G_FRAGMENT=q4km-mmproj-free-slurp-native-bounded-perception-proof-np4-ctx24k-max512-v1
      G_SERVING_TASK=SAEA-Serving;       G_MONITOR_TASK=SAEA-Monitor
      G_SERVING_ENTRY=scripts/flights/batch/serving_task_entry.sh
      G_MONITOR_ENTRY=scripts/flights/batch/serving_monitor_start.sh
      G_TASK_LOG_GLOB='serving-task-2*.log';          G_SERVER_LOG_GLOB='serving-slurp-native-np4-*.log' ;;
    a2t-np3)
      G_LABEL=A2T
      G_SID=serving-a2t-native-role-base-np3-max2048-v3
      G_FRAGMENT=q4km-mmproj-free-a2t-native-role-np3-max2048-v1
      G_SERVING_TASK=SAEA-Serving-A2T;   G_MONITOR_TASK=SAEA-Monitor-A2T
      G_SERVING_ENTRY=scripts/flights/batch/serving_task_entry_a2t.sh
      G_MONITOR_ENTRY=scripts/flights/batch/serving_monitor_start_a2t.sh
      G_TASK_LOG_GLOB='serving-a2t-task-*.log';       G_SERVER_LOG_GLOB='serving-a2t-np3-*.log' ;;
    e21-np4)
      G_LABEL=E21
      G_SID=serving-e21-native-window-flightruntime-np4-max1024-v1
      G_FRAGMENT=q4km-e21-native-window-packets-cddb000c-np4-max1024-v1
      G_SERVING_TASK=SAEA-Serving-E21;   G_MONITOR_TASK=SAEA-Monitor-E21
      G_SERVING_ENTRY=scripts/flights/batch/serving_task_entry_e21.sh
      G_MONITOR_ENTRY=scripts/flights/batch/serving_monitor_start_e21.sh
      G_TASK_LOG_GLOB='serving-e21-task-*.log';       G_SERVER_LOG_GLOB='serving-e21-np4-*.log' ;;
    det-np1)
      G_LABEL=DET
      G_SID=serving-slurp-native-det-np1-nocache-v1
      G_FRAGMENT=q4km-mmproj-free-slurp-native-bounded-perception-proof-np1-nocache-ctx24k-max512-v1
      G_SERVING_TASK=SAEA-Serving-DET;   G_MONITOR_TASK=SAEA-Monitor-DET
      G_SERVING_ENTRY=scripts/flights/det/serving_task_entry_det.sh
      G_MONITOR_ENTRY=scripts/flights/det/serving_monitor_start_det.sh
      G_TASK_LOG_GLOB='serving-task-det-*.log';       G_SERVER_LOG_GLOB='serving-slurp-det-np1-*.log' ;;
    think-np4)
      G_LABEL=THINK
      G_SID=serving-slurp-thinking-direct-fold-b-np4-max8192-v1
      G_FRAGMENT=q4km-thinking-mmproj-free-slurp-direct-fold-b-np4-ctx24k-max8192-v1
      G_SERVING_TASK=SAEA-Serving-THINK; G_MONITOR_TASK=SAEA-Monitor-THINK
      G_SERVING_ENTRY=scripts/flights/direct/serving_task_entry_think.sh
      G_MONITOR_ENTRY=scripts/flights/direct/serving_monitor_start_think.sh
      G_TASK_LOG_GLOB='serving-task-think-*.log';     G_SERVER_LOG_GLOB='serving-slurp-think-np4-*.log' ;;
    think-budget-np4)
      G_LABEL=THINKB
      G_SID=serving-slurp-thinking-module-fold-b-np4-budget3072-max4096-v1
      G_FRAGMENT=q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max4096-v1
      G_SERVING_TASK=SAEA-Serving-THINKB; G_MONITOR_TASK=SAEA-Monitor-THINKB
      G_SERVING_ENTRY=scripts/flights/direct/serving_task_entry_think_budget.sh
      G_MONITOR_ENTRY=scripts/flights/direct/serving_monitor_start_think_budget.sh
      G_TASK_LOG_GLOB='serving-task-thinkb-*.log';    G_SERVER_LOG_GLOB='serving-slurp-thinkb-np4-*.log' ;;
    think-budget7168-np4)
      # NX-T R2b (owner rulings 323 / 325 A): the same -c 98304 -np 4 server geometry as think-budget-np4; only the fragment's geometry cap
      # (decoding max_tokens, a request parameter) is 7168, so a node may carry a reasoning budget above 3072 with a 1024-token answer reserve.
      G_LABEL=THINKB7
      G_SID=serving-slurp-thinking-module-fold-b-np4-budget3072-max7168-v1
      G_FRAGMENT=q4km-thinking-mmproj-free-slurp-module-fold-b-np4-ctx24k-budget3072-max7168-v1
      G_SERVING_TASK=SAEA-Serving-THINKB7; G_MONITOR_TASK=SAEA-Monitor-THINKB7
      G_SERVING_ENTRY=scripts/flights/direct/serving_task_entry_think_budget7168.sh
      G_MONITOR_ENTRY=scripts/flights/direct/serving_monitor_start_think_budget7168.sh
      G_TASK_LOG_GLOB='serving-task-thinkb7-*.log';   G_SERVER_LOG_GLOB='serving-slurp-thinkb7-np4-*.log' ;;
    *) return 1 ;;
  esac
  G_SESSION_DIR=$SAEA_DATA/serving/$G_SID
  return 0
}

saea_target_for_session() {
  local t
  for t in $SAEA_TARGETS; do
    saea_geometry "$t"
    [ "$G_SID" = "$1" ] && { echo "$t"; return 0; }
  done
  return 1
}

saea_generation_flight_pids() {
  pgrep -af -- '[c]ore\.flight\.cli (campaign|worker)( |$)|[b]atch_driver\.sh|[c]ore\.flight\.lease_cli' 2>/dev/null
}

saea_flight_alive() {
  local found=1 pids
  if [ -e "$SAEA_DATA/locks/flight.lock" ]; then
    echo "flight.lock present at $SAEA_DATA/locks/flight.lock"
    found=0
  fi
  pids=$(saea_generation_flight_pids)
  if [ -n "$pids" ]; then
    echo "a generation flight process is alive:"
    echo "$pids" | cut -c1-200
    found=0
  fi
  return $found
}

saea_port_server_pids() {
  pgrep -af -- "[l]lama-server --host $SAEA_SERVING_HOST --port $SAEA_SERVING_PORT( |$)" 2>/dev/null
}

saea_cpu_sidecars() {
  { pgrep -af -- '[l]lama-server' 2>/dev/null | grep -v -- "--port $SAEA_SERVING_PORT"
    pgrep -af -- '[s]lurp_evo_fold_preprocess\.py' 2>/dev/null; } | cut -c1-200
}

saea_swap_pending() {
  [ -f "$SAEA_SWAP_PENDING" ] || return 1
  local pid
  pid=$(python3 -c 'import json,sys; print(int(json.load(open(sys.argv[1])).get("pid", 0)))' "$SAEA_SWAP_PENDING" 2>/dev/null)
  if [ -n "$pid" ] && [ "$pid" != 0 ] && kill -0 "$pid" 2>/dev/null; then
    cat "$SAEA_SWAP_PENDING"
    return 0
  fi
  return 1   # a marker whose swap process is gone is stale; it pends nothing
}

saea_sidecar_admission() {
  local ss=${1:-${SAEA_SERVING_SESSION:-$SAEA_MAIN/scripts/serving_session.sh}} out rc
  if out=$(saea_swap_pending); then
    echo "REFUSED (decision 162): a serving swap is in progress ($out); a CPU sidecar never starts while the GPU geometry is being swapped -- start it after the swap reports ready"
    return 1
  fi
  out=$(SPEECHRL_DATA_DIR=${SPEECHRL_DATA_DIR:-$SAEA_DATA} bash "$ss" resident 2>&1)
  rc=$?
  if [ $rc -ne 0 ]; then
    echo "REFUSED (decision 162): no GPU serving session is resident (serving_session.sh resident exit $rc); every serving geometry starts BEFORE any CPU sidecar, and a sidecar runs only beside a resident GPU session -- start the GPU session first"
    return 1
  fi
  if ! printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("process_state") == "running" and not d.get("stale") else 1)' 2>/dev/null; then
    echo "REFUSED (decision 162): the resident GPU session is not running: $(printf '%s' "$out" | tr '\n' ' ' | cut -c1-300)"
    return 1
  fi
  return 0
}

saea_powershell() {
  if [ -n "${SAEA_POWERSHELL:-}" ]; then echo "$SAEA_POWERSHELL"; return 0; fi
  command -v powershell.exe 2>/dev/null && return 0
  echo /mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe
}
