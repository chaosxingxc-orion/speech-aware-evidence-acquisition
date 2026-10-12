#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The three label-free preparations of the SLURP test SAMPLE SLURP-TEST-SAMPLE-3010-V1, in order, through the
# existing generic runners. Owner decision 156 of 2026-09-27 (row 156 of
# docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md): the preparations may run ahead of the
# dev-admitted composed arm; the MILESTONE read ids keep row 151's gate and are refused here.
#
#   stage packets  SAEA-SN-TEST-SAMPLE-3010-PREPROCESS
#                  ENCODE + PROMOTE through scripts/flights/batch/prep_generic_task_entry.sh (roster key
#                  test-sample-3010): 3,010 one-token contacts on the CPU-only llama-server sidecar on port 8081
#                  (-ngl 0 --no-mmproj-offload), --workers 4 (the sidecar's -np 4), --promote-workers 8. It may run
#                  BESIDE the GPU flight queue; the resident service on port 8080 is never contacted.
#   stage queries  SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1, then SAEA-SLURP-TEST-SAMPLE-3010-QUERY-VECTOR-EXPORT-V1
#                  2a the byte-reproducible source inventory (zero contacts), 2b the frozen Omni-Embed-Nemotron-3B
#                  forwards (3,010; the encoder loads on CUDA -- core.speech_embedding.load_stack moves the model to
#                  "cuda" -- so this stage WAITS FOR THE GPU FLIGHT QUEUE and refuses while a flight runs), 2c the
#                  zero-contact dimension alias, 3 the zero-contact content derivative. Audio prefetch cpu_workers 8.
#   stage all      packets, then queries.
#
# Refusals, before anything is opened: a dirty checkout; the allowance bytes or status; any MILESTONE read id in a
# stage or a config it binds; any exposure row of the stage that is still marked draft or carries no root
# countersignature; a second CPU-resident llama-server beside the sidecar (one resident CPU embedder at a time);
# a GPU flight in progress (queries only). Every step is create-only and a sealed step is skipped, never re-run.
#
# Receipts: the promotion receipt under the resident packet root (TEST-SAMPLE-3010-promotion.json), the driver
# report and the per-stage summaries under $SPEECHRL_DATA_DIR/prepared/slurp-test-sample-3010-preparations-v1/,
# the encoding outputs under $SPEECHRL_DATA_DIR/prepared/SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1/.
#
# Usage (WSL, a CLEAN checkout at the countersigned HEAD):
#   bash scripts/flights/testsample/prep_test_sample.sh --check            # model-free, media-free; no writes
#   bash scripts/flights/testsample/prep_test_sample.sh --run --stage packets
#   bash scripts/flights/testsample/prep_test_sample.sh --run --stage queries
# Environment: PREP_REPO (default: the main checkout).
set -u
MODE=
STAGE=all
while [ $# -gt 0 ]; do
  case "$1" in
    --check) MODE=check ;;
    --run) MODE=run ;;
    --stage) STAGE=${2:-}; shift ;;
    *) echo "unknown argument $1"; exit 64 ;;
  esac
  shift
done
case "$MODE:$STAGE" in
  check:*|run:packets|run:queries|run:all) ;;
  *) echo "usage: prep_test_sample.sh --check | --run --stage packets|queries|all"; exit 64 ;;
esac

REPO=${PREP_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
STEPS=scripts/flights/testsample/prep_test_sample_steps.py
PACKET_ROOT=/home/chao/feat-cache/slurp-q4km-packets-04ccc72a
PROMOTION_RECEIPT=TEST-SAMPLE-3010-promotion.json
PREPARED=$DATA/prepared/slurp-test-sample-3010-preparations-v1
ENCODE_RECEIPT=$DATA/preparation-runs/SAEA-SLURP-TEST-SAMPLE-3010-SPEECH-QUERY-ENCODING-V1/encode-v1/receipt.json
ALIAS_RECEIPT=$DATA/prepared/SAEA-SLURP-TEST-SAMPLE-3010-ALIAS-V1/query-dimension-alias.json
CONTENT=$DATA/vectors/slurp-test-sample-3010-v1/query-vectors-speech-content-v1.jsonl
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
# shellcheck disable=SC1091
source /home/chao/.venvs/speechrl/bin/activate
cd "$REPO" || exit 1
PY="python -B"
$PY -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$REPO/src/') else 9)" \
  || { echo "REFUSED: the package under test is not $REPO (shared-venv hijack)"; exit 9; }
DIRT=$(git status --short | grep -vc '^??')
echo "prep_test_sample $MODE stage $STAGE $(date -u +%FT%TZ) HEAD $(git rev-parse HEAD) dirt $DIRT"

if [ "$MODE" = check ]; then
  $PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" check
  exit $?
fi

[ "$DIRT" = "0" ] || { echo "REFUSED: dirty tree; the launch binds a clean countersigned HEAD"; exit 2; }
$PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" guard --stage "$STAGE" || exit 3
mkdir -p "$PREPARED" || exit 1

# A CPU-resident llama-server is one launched with -ngl 0 (a preprocess sidecar) or --embedding (a CPU embedder);
# the resident GPU service on port 8080 is never one of them and is never touched.
resident_cpu_servers() { pgrep -af '[l]lama-server' | grep -E -- '-ngl 0( |$)|--embedding' | grep -v -- '--port 8080'; }
gpu_flight() { pgrep -af '[c]ore\.flight\.cli|[b]atch_driver\.sh'; }

run_packets() {
  if [ -f "$PACKET_ROOT/$PROMOTION_RECEIPT" ]; then
    echo "packets: SKIP -- $PROMOTION_RECEIPT is sealed; a sealed preparation is never re-run"
  else
    if [ -n "$(resident_cpu_servers)" ]; then
      echo "REFUSED: a CPU-resident llama-server other than the port-8080 service is up (one resident CPU embedder at a time):"
      resident_cpu_servers
      return 4
    fi
    # Owner decision 162 (enforced for decision 163): the CPU sidecar starts only beside a resident, running GPU
    # session and never during a serving swap; prep_generic_task_entry.sh refuses the same way (exit 10).
    # shellcheck source=../batch/serving_lib.sh
    source "$REPO/scripts/flights/batch/serving_lib.sh"
    if ! saea_sidecar_admission "${SAEA_SERVING_SESSION:-$REPO/scripts/serving_session.sh}"; then
      return 10
    fi
    echo "packets: ENCODE + PROMOTE via prep_generic_task_entry.sh (roster test-sample-3010, workers 4, promote 8) $(date -u +%T)"
    PREP_ROSTER=test-sample-3010 PREP_REPO="$REPO" PREP_WORKERS=4 PREP_PROMOTE_WORKERS=8 \
      PREP_OUT="$PREPARED/packets" PREP_PROMOTION_RECEIPT="$PROMOTION_RECEIPT" \
      bash scripts/flights/batch/prep_generic_task_entry.sh
    RC=$?
    LOG=$(ls -t /home/chao/prep-test-sample-3010-2*.log 2>/dev/null | head -1)
    echo "packets: generic entry exit $RC; log $LOG"
    [ -n "$LOG" ] && tail -8 "$LOG"
    [ $RC -ne 0 ] && return $RC
  fi
  $PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" summary --stage packets
}

run_queries() {
  if [ -n "$(gpu_flight)" ]; then
    echo "REFUSED: a GPU flight is running and the speech-query encoder loads on CUDA; queue this stage behind the flight queue"
    gpu_flight
    return 7
  fi
  if [ -n "$(resident_cpu_servers)" ]; then
    echo "REFUSED: a CPU-resident llama-server other than the port-8080 service is up (the packets sidecar must have stopped):"
    resident_cpu_servers
    return 4
  fi
  $PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" inventory || return 5
  if [ -f "$ENCODE_RECEIPT" ]; then
    echo "2b: SKIP -- the step-2b receipt is sealed; a sealed preparation is never re-run"
  else
    CFG=$($PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" runtime-config) \
      || { echo "RUNTIME CONFIG REFUSED"; echo "$CFG"; return 5; }
    echo "$CFG"
    eval "$(echo "$CFG" | grep '^PREP_')"
    echo "2b step 2b $(date -u +%T)"
    $PY -m speech_aware_evidence_acquisition.core.speech_preparation_runtime \
      --config "$PREP_RUNTIME_CONFIG" --config-sha256 "$PREP_RUNTIME_CONFIG_SHA256" \
      --data-root "$DATA" --source-root "$REPO"
    RC=$?
    echo "step 2b exit $RC $(date -u +%FT%TZ)"
    [ $RC -ne 0 ] && return $RC
  fi
  MAT=$($PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" materialise) \
    || { echo "STEP A FAILED"; echo "$MAT"; return 6; }
  echo "$MAT"
  eval "$(echo "$MAT" | grep '^PREP_STATE=')"
  # shellcheck disable=SC1090
  . "${PREP_STATE:?materialise printed no state path}" || return 6
  if [ -f "$ALIAS_RECEIPT" ]; then
    echo "2c: SKIP -- the alias receipt is sealed"
  else
    echo "2c step 2c $(date -u +%T)"
    $PY -m speech_aware_evidence_acquisition.core.preparation_vectors \
      --config "$ALIAS_CONFIG" --config-sha256 "$ALIAS_CONFIG_SHA256" \
      --repo-root "$REPO" --data-root "$DATA" > "$(dirname "$STATE")/step-2c.json" 2> "$(dirname "$STATE")/step-2c.err" \
      || { echo "STEP 2C FAILED"; tail -5 "$(dirname "$STATE")/step-2c.err"; return 6; }
  fi
  $PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" alias-receipt || return 6
  # shellcheck disable=SC1090
  . "$STATE"
  if [ -f "$CONTENT" ]; then
    echo "3: SKIP -- the content derivative is sealed"
  else
    echo "3  preparation 3 $(date -u +%T)"
    $PY scripts/build_slurp_query_content_derivative.py \
      --source-relpath "$SEGMENTS_RELPATH" --source-sha256 "$SEGMENTS_SHA256" \
      --out-dir "$VECTOR_DIR" --out-name "$CONTENT_NAME" --ledger-row "$EXPORT_ROW" || return 8
  fi
  $PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" report || return 9
  $PY "$STEPS" --repo-root "$REPO" --data-root "$DATA" summary --stage queries
}

RC=0
case "$STAGE" in
  packets) run_packets; RC=$? ;;
  queries) run_queries; RC=$? ;;
  all) run_packets; RC=$?; [ $RC -eq 0 ] && { run_queries; RC=$?; } ;;
esac
echo "== prep_test_sample $STAGE exit $RC $(date -u +%FT%TZ)"
exit $RC
