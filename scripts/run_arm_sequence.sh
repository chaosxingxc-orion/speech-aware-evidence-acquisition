#!/usr/bin/env bash
# Sequential multi-arm launcher for a paired experiment.
#
# Why this is a committed script and not an operator's shell history: a paired
# experiment is only readable if every arm ran under ONE config hash and one
# sampling, and the preconditions that guarantee that are easy to forget. On
# 2026-08-09 the launcher lived in a scratch directory, was lost when that
# directory was cleared, and the hand-rebuilt replacement omitted
# PYTHONDONTWRITEBYTECODE -- which closed the D3 gate and cost two arms before
# a single model call. The procedure belongs next to the code it drives.
#
# This script never chooses an experiment for you: arms come from an arm file,
# so the record of WHAT ran is a committed artifact too.
#
#   usage: run_arm_sequence.sh --arms <file> --dataset <frag> --experiment <frag>
#                              --model <frag> [--out-dir DIR] [--dry-run]
#
# The arm file is one `run_id:baseline_fragment` per line; `#` comments and
# blank lines are ignored. Example (docs/arms/r4-context-dose.arms):
#   SAEA-E-002-r4-nocontext:bare-core-ojw
#   SAEA-E-002-r4-matched:fixed-legal-context-ojw
#   SAEA-E-002-r4-mismatched:mismatched-evidence-ojw
#
# Model touch: this DOES drive live model calls. Every precondition the study
# contract requires (validated ExecutionPlan, pre-registered exposure ledger
# row) is enforced by the driver's own gate, not here -- this script only
# refuses the environment-level hazards the gate cannot see.
set -uo pipefail

ARMS="" DATASET="" EXPERIMENT="" MODEL="" OUT_DIR="$HOME" DRY=0
PLANNED_CALLS=2000 PLANNED_GPU_HOURS=30.0 PLANNED_AUDIO_SECONDS=150000
PORT=8080 HOST=127.0.0.1
# mlflow 3.14.0 refuses the filesystem tracking backend outright ("in
# maintenance mode"), and it refuses it at FINALIZE -- after a two-hour arm has
# already produced its COMPLETED manifest and scores. The run is unaffected but
# the arm exits non-zero, which then trips this script's own two-failure rule
# and silently costs the remaining arms. Default to sqlite, still on ext4 per
# program policy ("only local MLflow stays on ext4").
TRACKING_URI="sqlite:///${HOME}/mlruns.db"

usage() { sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --arms) ARMS="$2"; shift 2 ;;
    --dataset) DATASET="$2"; shift 2 ;;
    --experiment) EXPERIMENT="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --out-dir) OUT_DIR="$2"; shift 2 ;;
    --planned-model-calls) PLANNED_CALLS="$2"; shift 2 ;;
    --planned-gpu-hours) PLANNED_GPU_HOURS="$2"; shift 2 ;;
    --planned-speech-audio-seconds) PLANNED_AUDIO_SECONDS="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --tracking-uri) TRACKING_URI="$2"; shift 2 ;;
    --dry-run) DRY=1; shift ;;
    --help|-h) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for req in ARMS DATASET EXPERIMENT MODEL; do
  if [ -z "${!req}" ]; then echo "missing --${req,,}" >&2; exit 2; fi
done
if [ ! -f "$ARMS" ]; then echo "arm file not found: $ARMS" >&2; exit 2; fi
if [ -z "${SPEECHRL_DATA_DIR:-}" ]; then
  echo "SPEECHRL_DATA_DIR is unset; refusing to guess where runs belong" >&2; exit 2
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCORING="$REPO/src/speech_aware_evidence_acquisition/scoring"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

# The D3 freeze binds SOURCE bytes only, so ANY bytecode cache under the frozen
# scoring package closes the gate (gate_e0.py::_validate_scoring_freeze -- a
# hash-based .pyc can make scoring run code the receipt never described). Both
# halves matter: the export stops this process from planting one, and the
# per-arm purge below clears one planted between arms by anything else, e.g. a
# pytest run in another window.
export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

# The ML stack is pinned to ~/.venvs/speechrl (CLAUDE.md); a detached launch
# inherits no activation, and without this the driver never starts at all.
VENV="${SPEECHRL_VENV:-$HOME/.venvs/speechrl}"
if [ -f "$VENV/bin/activate" ]; then
  # shellcheck disable=SC1091
  . "$VENV/bin/activate"
elif ! command -v python > /dev/null; then
  echo "REFUSED: no python and no venv at $VENV" >&2
  exit 4
fi

gpu_is_clean () {
  # nvidia-smi is NOT usable as the authority here. Under WSL2 the GPU is
  # reached through dxgkrnl paravirtualisation, VM workloads are not attributed
  # in the memory query, and the query intermittently fails outright
  # (`dxgk: dxgkio_query_adapter_info: Ioctl failed: -22`). Measured 2026-08-10:
  # a llama-server with the model resident and answering /health reported
  # "0 MiB" from nvidia-smi on both the WSL and the Windows side, minutes after
  # the same process reported 23,312 MiB. A guard reading that would have
  # declared a busy GPU clean and started an arm on top of a live server.
  #
  # The authoritative check is process-based, plus asking any server that might
  # still be up whether it answers.
  local n
  n="$(pgrep -c -f llama-server 2>/dev/null)"; n="${n:-0}"
  local port
  for port in "$PORT" 8099; do
    if curl -s -m 3 "http://127.0.0.1:${port}/health" 2>/dev/null | grep -q status; then
      echo "    a server is still answering on port ${port}"
      return 1
    fi
  done
  echo "    llama-server processes: ${n}; nothing answering on ${PORT}/8099"
  # Standing rule (2026-08-09): no process that can open a CUDA context may run
  # beside a live experiment, diagnostics included. One competing context
  # degraded throughput 7.3x and did NOT recover when it exited, because
  # -ngl 999 disables llama.cpp's device-memory fitting, so spilled allocations
  # are never migrated back.
  [ "$n" -eq 0 ]
}

run_arm () {
  local run_id="$1" baseline="$2"
  local log="$OUT_DIR/${run_id}-${STAMP}.log"
  local t0 t1 rc npyc cells
  echo "===== $run_id ($baseline) -> $log  $(date -u +%Y-%m-%dT%H:%M:%SZ) ====="

  # finalize_bundle renders a DRAFT wiki-ledger row and ledger_row refuses a
  # missing column outright (core/tracking.py, fail-closed). The driver derives
  # the identity cells from the verified bundle but has no basis to invent the
  # judgment columns, so the launcher must supply them (the driver exposes
  # --ledger-cells for exactly this). Discovered 2026-08-11: without this,
  # EVERY completed arm finished its science, then exited 1 at finalize and
  # stayed OPENED forever -- never FINALIZED -- which also tripped this
  # script's own two-failure rule on multi-arm files. Placeholders are
  # explicit PENDING markers: the draft row is a scaffold for the human wiki
  # registration, never a claim.
  cells="$(mktemp)"
  cat > "$cells" <<CELLS
{"experiment_id": "$run_id (draft; formal id assigned at wiki registration)",
 "speech task/carrier": "dataset fragment '$DATASET' (identity: exposure-ledger row $run_id)",
 "changed axes": "baseline fragment '$baseline' (draft; axis judgment pending)",
 "shared code revision": "none (study repo only)",
 "model rev": "model fragment '$MODEL' (revision: umbrella lock via runtime receipt)",
 "dataset rev": "umbrella lock; sha256 recorded at manifest cost.umbrella_lock_sha256",
 "effectiveness": "PENDING-ANALYSIS (draft row)",
 "reasonableness": "PENDING-ANALYSIS (draft row)",
 "efficiency": "PENDING-ANALYSIS (draft row)",
 "deviations": "PENDING-ANALYSIS (draft row)",
 "decision": "PENDING-ANALYSIS (draft row)"}
CELLS

  # A dry run must be safe to invoke while a real sequence is live, so it
  # returns before the two side effects below -- killing llama-server and
  # deleting bytecode caches would both disrupt a running experiment.
  if [ "$DRY" -eq 1 ]; then
    echo "    DRY RUN: would run $run_id / $baseline / $DATASET / $EXPERIMENT / $MODEL"
    echo "    DRY RUN: log would be $log"
    return 0
  fi

  pkill -9 -f 'llama-server' 2>/dev/null && sleep 8 || true
  gpu_is_clean || { echo "  REFUSED: GPU not clean before $run_id"; return 9; }

  npyc="$(find "$SCORING" -name '__pycache__' -type d 2>/dev/null | wc -l)"
  if [ "$npyc" -gt 0 ]; then
    echo "    purging $npyc __pycache__ dir(s) under the frozen scoring package"
    find "$SCORING" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null
  fi

  t0="$(date +%s)"
  python -m speech_aware_evidence_acquisition.core.driver smoke \
    --model "$MODEL" \
    --dataset "$DATASET" \
    --baseline "$baseline" \
    --experiment "$EXPERIMENT" \
    --run-id "$run_id" \
    --execution-profile bounded-discovery-probe \
    --planned-model-calls "$PLANNED_CALLS" \
    --planned-gpu-hours "$PLANNED_GPU_HOURS" \
    --planned-speech-audio-seconds "$PLANNED_AUDIO_SECONDS" \
    --run-dir "$SPEECHRL_DATA_DIR/runs/$run_id" \
    --runtime-root "${LLAMA_RUNTIME_ROOT:-$HOME}" \
    --host "$HOST" --port "$PORT" \
    --tracking-uri "$TRACKING_URI" \
    --ledger-cells "$cells" \
    > "$log" 2>&1
  rc=$?
  rm -f "$cells"
  t1="$(date +%s)"
  echo "  exit=$rc  elapsed=$(( (t1 - t0) / 60 )) min"
  if [ "$rc" -ne 0 ]; then
    echo "  --- tail (framework graph events suppressed) ---"
    grep -vE '"module_id": "graph"' "$log" | tail -6 | cut -c1-200
  fi
  pkill -9 -f 'llama-server' 2>/dev/null && sleep 8 || true
  return "$rc"
}

cd "$REPO"

# A COMPLETED manifest binds study_commit by reading git at FINALIZE time, and
# that read refuses a dirty tree (core/bundle/git_commit.py documents the
# window: the pre-run cleanliness check cannot cover the hours the run then
# takes). So an edit landing mid-run destroys the arm's result after all of its
# compute. Print the commit every arm is claiming, and refuse to start dirty.
HEAD_AT_START="$(git rev-parse --short HEAD 2>/dev/null)"
if [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  echo "REFUSED: study repo is dirty; a run manifest must bind an exact commit" >&2
  git status --porcelain >&2
  exit 3
fi
echo "sequence binding study_commit $HEAD_AT_START -- keep the tree clean until it ends"

failed=0 ran=0
while IFS= read -r line; do
  line="${line%%#*}"
  line="$(echo "$line" | tr -d '[:space:]')"
  [ -z "$line" ] && continue
  run_arm "${line%%:*}" "${line##*:}"
  if [ $? -ne 0 ]; then
    failed=$(( failed + 1 ))
    # One bad arm should not cost a whole night of wall clock; two in a row is
    # systematic and every further arm would burn hours reproducing it.
    if [ "$failed" -ge 2 ]; then
      echo "TWO ARMS FAILED -> systematic, stopping the sequence"; break
    fi
    echo "  arm failed; continuing to the next one"
  fi
  ran=$(( ran + 1 ))
done < "$ARMS"

echo "===== sequence done  arms_run=$ran  failed=$failed  $(date -u +%Y-%m-%dT%H:%M:%SZ) ====="
# A paired experiment with a failed arm is not a partial result, it is an
# unusable one -- surface that in the exit code.
[ "$failed" -eq 0 ]
