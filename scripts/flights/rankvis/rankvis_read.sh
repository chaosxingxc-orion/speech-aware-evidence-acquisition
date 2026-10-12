#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Cell RANKVIS read (registered row SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1; the rank-ordered,
# rank-visible rendering conversion probe, owner decision 171). MODEL-FREE: zero model / tokenizer /
# encoder / server contacts; scorer output is read from the sealed per-sample scores only.
#
# Driver: scripts/analysis/rankvis_probe_read.py. Comparator: the sealed AGREE arm
# (SAEA-SLURP-STAGE3-AGREE-W1-FOLD-A-V1), never re-flown; the contrast is per row and offline.
#
# GATE (redefined 2026-09-28, coordinator ruling): refuses unless every one of the 119 rows verifies,
# on both named stores (intent-boundaries, train-exemplars), directly from the sealed MODEL_REQUEST
# request records the flight itself wrote (<run_id>.trace.jsonl) -- every value line of the store's
# rendered block carries the rank label, the labelled ranks read 1..n contiguous and increasing in
# document order, and the count equals the store's delivered count in the sealed phase receipt
# (module docstring of the driver, rendering_gate). A stricter, OPTIONAL cross-check against a sealed
# retrieval-rank-inputs sidecar is reported when one exists; no flight seals it today, so its absence
# alone no longer refuses the read. No conversion number is produced on a refusal; a refusal receipt
# is written instead.
#
# The 89-row synthesis subset and the no-op expectation (never zero) are reported beside the full
# 119-row read, not separately: the driver's own rate_block/subset_rate.
#
# No utterance text, gold, transcript or model output is printed or persisted: ids, counts, rates and
# hashes only.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
RUN_ID=SAEA-SLURP-STAGE3-RANKVIS-FOLD-A-119-V1
ROW_LABEL="Cell RANKVIS read"

grep -E "^\| [^|]* \| $RUN_ID \|" "$MAIN/docs/exposure-ledger.md" | grep -q "root countersigned" \
  || { echo "REFUSED: the $RUN_ID exposure row is missing or not countersigned"; exit 3; }
$PY -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }

cd "$MAIN" || exit 1
$PY -B scripts/analysis/rankvis_probe_read.py --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR"
STATUS=$?
if [ $STATUS -eq 0 ]; then
  echo "$ROW_LABEL: done"
else
  echo "$ROW_LABEL: READ FAILED or REFUSED (exit $STATUS)"
fi
exit $STATUS
