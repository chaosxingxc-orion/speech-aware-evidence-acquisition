#!/bin/bash
# Windows Scheduled Task entry for scripts/flights/testsample/prep_test_sample.sh (owner decision 77: long passes
# run as scheduled tasks, never as session-owned background shells). The sibling of
# scripts/flights/batch/prep_generic_task_entry.sh / prep_generic_encode_task_entry.sh: the packet stage reuses the
# first unchanged, and the encode entry cannot take this roster because its preparation table
# (prep_generic_steps.PREPARATION_SETS) is extended only in memory by prep_test_sample_steps.py.
#
# Environment (all optional):
#   PREP_STAGE  packets | queries | all | next (default next: packets until TEST-SAMPLE-3010-promotion.json is
#               sealed, then queries -- which refuses while a GPU flight runs, so launch it after the queue drains)
#   PREP_REPO   the clean countersigned checkout (default: the main checkout)
# It authorises nothing: the runner refuses every stage whose exposure rows are not root-countersigned.
set -u
REPO=${PREP_REPO:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
STAGE=${PREP_STAGE:-next}
if [ "$STAGE" = next ]; then
  if [ -f /home/chao/feat-cache/slurp-q4km-packets-04ccc72a/TEST-SAMPLE-3010-promotion.json ]; then STAGE=queries; else STAGE=packets; fi
fi
LOG=/home/chao/prep-test-sample-3010-task-$STAGE-$(date -u +%Y%m%dT%H%M%SZ).log
exec > "$LOG" 2>&1
echo "task entry $(date -u +%FT%TZ) stage $STAGE repo $REPO"
PREP_REPO="$REPO" bash "$REPO/scripts/flights/testsample/prep_test_sample.sh" --run --stage "$STAGE"
