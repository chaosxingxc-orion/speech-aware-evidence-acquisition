#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The SUCCESSOR-3 test-sample milestone read (owner ruling 301 A): the Thinking system arm against the SEALED successor-2 column.
#
#   bash scripts/flights/nx/successor3_thinking_read.sh [--dry-run]
#
# RECIPE-DRIVEN: docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1/analysis-recipe-v1.json (recipe id
# slurp-milestone-successor3-thinking-system-paired-analysis-v1). The arms are read FROM it:
#   arms.arm         the Thinking arm SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR3-THINKING-SYSTEM-V1
#   arms.comparator  the SEALED successor-2 run (cross-flight; THE REGISTERED CLAIM)
# There is NO in-chain replicate on the test sample, by design, so the package-mode reader (stage3_paired_read.py --package) does not apply; this wrapper uses the
# reader's PAIR mode and re-states the final-report conditions itself: (a) both sealed run manifests exist; (b) the scorer is slurp-slu-official-test; (c) --strata-source
# scorer (aggregate-only, inside the official scorer) with the package's population counts and the post-stratified weighting; (d) the READ row is ROOT COUNTERSIGNED
# (checked BEFORE any score is opened). The pair pass scores the arm ONCE, complete, through core.scoring_batch (never sharded). It then runs
# scripts/analysis/slurp_successor3_thinking_read.py, which applies the registered rule to the AGGREGATE output only and prints the limitation with the word.
# NO number from the sample is printed before that aggregate read.
# --dry-run: no countersign needed. Resolves the recipe and the sealed paths and prints identities only; opens no gold, runs no scorer, writes nothing.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts. The wrapper reports; the verdict word is the coordinator's (owner decision 139).
# A pass directory that already holds files is never overwritten.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    *) echo "usage: successor3_thinking_read.sh [--dry-run]"; exit 2 ;;
  esac
  shift
done
PKG=docs/readiness/2026-10-14-slurp-milestone-successor3-thinking-system-v1
RECIPE=$PKG/analysis-recipe-v1.json
ROSTER=docs/receipts/rosters/slurp-test-sample-3010-v1.json
COUNTS=$PKG/population-counts-v1.json
SCORER=slurp-slu-official-test
cd "$MAIN" || exit 1
[ -f "$RECIPE" ] || { echo "REFUSED: $RECIPE is missing"; exit 8; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read -r READ_RUN RECIPE_ID ARM_RUN ARM_ATT CMP_RUN CMP_ATT SEED DRAWS SPLIT RECIPE_SCORER < <("$PY" -B - "$RECIPE" "$ROSTER" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
roster = json.load(open(sys.argv[2], encoding="utf-8"))
a = r["arms"]
print(r["read_run_id"], r["recipe_id"], a["arm"]["run_id"], a["arm"]["attempt_id"], a["comparator"]["run_id"], a["comparator"]["attempt_id"],
      r["resampling"]["seed"], r["resampling"]["bootstrap_draws"], roster["split_identity_hash"], r["read_driver"]["scorer"])
PY
)
[ -n "$READ_RUN" ] && [ -n "$ARM_RUN" ] && [ -n "$CMP_RUN" ] && [ -n "$SPLIT" ] || { echo "REFUSED: $RECIPE names no READ run / arms / roster"; exit 8; }
[ "$RECIPE_SCORER" = "$SCORER" ] || { echo "REFUSED (final-report condition b): the recipe scorer is $RECIPE_SCORER, not $SCORER"; exit 8; }
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
echo "successor3: read $READ_RUN recipe $RECIPE_ID arm $ARM_RUN comparator $CMP_RUN"
for pair in "$ARM_RUN/$ARM_ATT" "$CMP_RUN/$CMP_ATT"; do
  run=${pair%%/*}
  [ -f "$SPEECHRL_DATA_DIR/runs/$pair/$run.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under runs/$pair"; exit 3; }
done
if [ "$DRY" = 1 ]; then
  echo "(dry) both sealed runs present; would read: vs-comparator (Thinking arm minus the sealed successor-2 column) under $OUT, then the verdict stage"
  exit 0
fi
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
mkdir -p "$OUT"
if [ -d "$OUT/vs-comparator" ] && [ -n "$(ls -A "$OUT/vs-comparator")" ]; then
  echo "REFUSED: $OUT/vs-comparator already holds files; a sealed read is never overwritten"; exit 6
fi
mkdir -p "$OUT/vs-comparator"
"$PY" -B scripts/analysis/stage3_paired_read.py --stage3 --stage all \
  --left-run "$CMP_RUN" --left-attempt "$CMP_ATT" --left-label "the sealed successor-2 column (comparator)" \
  --right-run "$ARM_RUN" --right-attempt "$ARM_ATT" --right-label "the Thinking system arm ($ARM_RUN)" \
  --scorer-id "$SCORER" --expected-split-role final-report --roster "$ROSTER" --cluster-key utterance_id \
  --split-identity-hash "$SPLIT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
  --strata-source scorer --population-counts "$COUNTS" --weighting post-stratified \
  --seed "$SEED" --draws "$DRAWS" --recipe-id "$RECIPE_ID" \
  --title "Test-sample successor 3 Thinking-system read (vs-comparator)" --analysis-root "$OUT/vs-comparator" || { echo "READ FAILED (vs-comparator)"; exit 7; }
"$PY" -B scripts/analysis/slurp_successor3_thinking_read.py --stage verdict --data-root "$SPEECHRL_DATA_DIR" --repo-root "$MAIN" || { echo "VERDICT STAGE FAILED"; exit 7; }
echo "successor-3 read written under $OUT (vs-comparator, successor3-verdict.json)"
