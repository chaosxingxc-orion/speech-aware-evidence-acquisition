#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The cell DET read (owner decision 140; decision 58: reads are executed by script). MODEL-FREE: zero
# model / tokenizer / encoder / scorer / server contacts -- every byte it reads is already sealed.
# Registered as SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-READ-V1 (a model-free-check row).
#
# Two drivers, in this order:
#   1. scripts/analysis/slurp_det_pair_read.py -- THE read: per-row byte identity of the delivered
#      answer between pass A and pass B (count of identical rows out of 50), the intent / entity-set
#      flip shares where the sealed per-sample scores carry the parsed prediction, the pair's pooled
#      SLU-F1 and intent paired deltas as DESCRIPTIVE numbers, and (decision 140) contacts per minute
#      and prompt tokens per second for each pass from the sealed dispatch window beside ROLL-2's np4
#      numbers, in one table. Output: stop.json, per_row.json, summary.json under the analysis root.
#   2. scripts/analysis/slurp_paired_roster_read.py -- the programme's standard paired roster read of
#      pass B against pass A (structural, contrast, efficiency blocks) on the 50-row receipt, for the
#      record; it carries no bar and no verdict here.
# It is NOT an admission read and never calls plan_cell_read.py: the pair is its own control.
# No utterance text, gold label, transcript or model output is printed or persisted.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
LEFT_RUN=SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-A-V1
LEFT_ATTEMPT=attempt-slurp-native-stage3-det-np1-fold-a-50-a-generation-v1
RIGHT_RUN=SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-B-V1
RIGHT_ATTEMPT=attempt-slurp-native-stage3-det-np1-fold-a-50-b-generation-v1
ROSTER=docs/receipts/rosters/slurp-stage3-det-fold-a-50-v1.json
SESSION=serving-slurp-native-det-np1-nocache-v1
ROOT=$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-DET-NP1-FOLD-A-50-READ-V1${SAEA_ANALYSIS_SUFFIX:-}
mkdir -p "$ROOT" || exit 1
for name in slurp_det_pair_read.py slurp_paired_roster_read.py; do
  cp "$MAIN/scripts/analysis/$name" "$ROOT/$name" || exit 1   # a RECORD of the driver bytes beside the output
  echo "$name sha256 $(sha256sum "$ROOT/$name" | cut -c1-16)"
done
echo "== stage pair-read $(date -u +%T)"
$PY -B "$MAIN/scripts/analysis/slurp_det_pair_read.py" --stage all \
  --left-run $LEFT_RUN --left-attempt $LEFT_ATTEMPT --left-label pass-a \
  --right-run $RIGHT_RUN --right-attempt $RIGHT_ATTEMPT --right-label pass-b \
  --roster $ROSTER --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
  --analysis-root "$ROOT" --seed 20260915 --draws 10000 --expected-session-id $SESSION \
  > "$ROOT/stage-pair-read.log" 2>&1 || { echo "PAIR READ FAILED"; tail -5 "$ROOT/stage-pair-read.log" | cut -c1-300; exit 2; }
echo "== stage paired-roster-read $(date -u +%T)"
$PY -B "$MAIN/scripts/analysis/slurp_paired_roster_read.py" --stage all \
  --left-run $LEFT_RUN --left-attempt $LEFT_ATTEMPT --left-label "DET pass A (np1, cache off)" \
  --right-run $RIGHT_RUN --right-attempt $RIGHT_ATTEMPT --right-label "DET pass B (np1, cache off)" \
  --scorer-id slurp-slu-official-train --expected-split-role discovery \
  --roster $ROSTER --cluster-key utterance_id \
  --split-identity-hash af8154d5dedd3768b145a9d5f5ef6d90eb0ab0f6611a02ee82b2f22fd73a07fa \
  --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" --seed 20260915 --draws 10000 \
  --recipe-id slurp-stage3-det-np1-fold-a-50-paired-roster-read-v1 \
  --title "Cell DET: pass B against pass A on the 50-row Fold A prefix (descriptive; the pair is its own control)" \
  --analysis-root "$ROOT/paired-roster-read" > "$ROOT/stage-paired-roster-read.log" 2>&1 \
  || { echo "PAIRED ROSTER READ FAILED (descriptive stage; the pair read above stands)"; tail -5 "$ROOT/stage-paired-roster-read.log" | cut -c1-300; }
echo "DET read done $(date -u +%T)"; grep -A 12 '"byte_identical_delivered_answer"' "$ROOT/stage-pair-read.log" | head -14; grep -A 3 '"table"' "$ROOT/stage-pair-read.log" | head -20; ls "$ROOT"
