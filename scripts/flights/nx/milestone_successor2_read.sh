#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The SUCCESSOR-2 test-sample milestone read (owner decisions 233 and 241): the NX R5 composed arm against the SEALED successor-1 COMP-1b and PLAN columns.
#
#   bash scripts/flights/nx/milestone_successor2_read.sh [--dry-run]
#
# RECIPE-DRIVEN: docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1/analysis-recipe-v1.json (recipe id
# slurp-milestone-successor2-composed-paired-analysis-v1). The arms are read FROM it:
#   arms.arm              the composed arm SAEA-SLURP-TEST-SAMPLE-3010-MILESTONE-SUCCESSOR2-COMPOSED-V1
#   arms.comparator       the SEALED successor-1 COMP-1b column (cross-flight; THE REGISTERED CLAIM)
#   arms.plan_comparator  the SEALED successor-1 PLAN column (cross-flight; context)
# There is NO in-chain replicate on the test sample, by design (one new generation run id), so the package-mode reader
# (scripts/analysis/stage3_paired_read.py --package, which demands arms.in_chain_replicate and checks both arms against the
# allowance) does not apply; this wrapper uses the reader's PAIR mode and re-states the final-report conditions itself:
#   (a) the three sealed run manifests exist; (b) the scorer is slurp-slu-official-test; (c) --strata-source scorer (aggregate-only,
#   inside the official scorer) with the package's population counts and the post-stratified weighting; (d) the READ row is ROOT
#   COUNTERSIGNED (checked BEFORE any score is opened).
# --dry-run: no countersign needed. Resolves the recipe and the sealed paths and prints identities only; opens no gold, runs no scorer, writes nothing.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts. The wrapper reports; the verdict word is the coordinator's (owner decision 139).
# A pass directory that already holds files is never overwritten. This wrapper has been syntax-checked only; it has not been run.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    *) echo "usage: milestone_successor2_read.sh [--dry-run]"; exit 2 ;;
  esac
  shift
done
PKG=docs/readiness/2026-10-10-slurp-milestone-successor2-composed-v1
RECIPE=$PKG/analysis-recipe-v1.json
ROSTER=docs/receipts/rosters/slurp-test-sample-3010-v1.json
COUNTS=$PKG/population-counts-v1.json
SCORER=slurp-slu-official-test
cd "$MAIN" || exit 1
[ -f "$RECIPE" ] || { echo "REFUSED: $RECIPE is missing"; exit 8; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read -r READ_RUN RECIPE_ID ARM_RUN ARM_ATT CMP_RUN CMP_ATT PLAN_RUN PLAN_ATT SEED DRAWS SPLIT RECIPE_SCORER < <("$PY" -B - "$RECIPE" "$ROSTER" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
roster = json.load(open(sys.argv[2], encoding="utf-8"))
a = r["arms"]
print(r["read_run_id"], r["recipe_id"], a["arm"]["run_id"], a["arm"]["attempt_id"], a["comparator"]["run_id"], a["comparator"]["attempt_id"],
      a["plan_comparator"]["run_id"], a["plan_comparator"]["attempt_id"], r["resampling"]["seed"], r["resampling"]["bootstrap_draws"],
      roster["split_identity_hash"], r["read_driver"]["scorer"])
PY
)
[ -n "$READ_RUN" ] && [ -n "$ARM_RUN" ] && [ -n "$CMP_RUN" ] && [ -n "$PLAN_RUN" ] && [ -n "$SPLIT" ] || { echo "REFUSED: $RECIPE names no READ run / arms / roster"; exit 8; }
[ "$RECIPE_SCORER" = "$SCORER" ] || { echo "REFUSED (final-report condition b): the recipe scorer is $RECIPE_SCORER, not $SCORER"; exit 8; }
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
echo "successor2: read $READ_RUN recipe $RECIPE_ID arm $ARM_RUN comparator $CMP_RUN plan $PLAN_RUN"
for pair in "$ARM_RUN/$ARM_ATT" "$CMP_RUN/$CMP_ATT" "$PLAN_RUN/$PLAN_ATT"; do
  run=${pair%%/*}
  [ -f "$SPEECHRL_DATA_DIR/runs/$pair/$run.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under runs/$pair"; exit 3; }
done
if [ "$DRY" = 1 ]; then
  echo "(dry) all three sealed runs present; would read: vs-comparator (composed minus the sealed COMP-1b) and vs-plan (composed minus the sealed PLAN) under $OUT"
  exit 0
fi
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
mkdir -p "$OUT"
pair_pass() {  # name left_run left_att label_left
  local name=$1
  if [ -d "$OUT/$name" ] && [ -n "$(ls -A "$OUT/$name")" ]; then
    echo "REFUSED: $OUT/$name already holds files; a sealed read is never overwritten"; return 6
  fi
  mkdir -p "$OUT/$name"
  "$PY" -B scripts/analysis/stage3_paired_read.py --stage3 --stage all \
    --left-run "$2" --left-attempt "$3" --left-label "$4" --right-run "$ARM_RUN" --right-attempt "$ARM_ATT" --right-label "the composed arm ($ARM_RUN)" \
    --scorer-id "$SCORER" --expected-split-role final-report --roster "$ROSTER" --cluster-key utterance_id \
    --split-identity-hash "$SPLIT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
    --strata-source scorer --population-counts "$COUNTS" --weighting post-stratified \
    --seed "$SEED" --draws "$DRAWS" --recipe-id "$RECIPE_ID" \
    --title "Test-sample successor 2 composed read ($name)" --analysis-root "$OUT/$name"
}
pair_pass vs-comparator "$CMP_RUN" "$CMP_ATT" "the sealed successor-1 COMP-1b column (primary comparator)" || { echo "READ FAILED (vs-comparator)"; exit 7; }
pair_pass vs-plan "$PLAN_RUN" "$PLAN_ATT" "the sealed successor-1 PLAN column (context)" || { echo "READ FAILED (vs-plan)"; exit 7; }
echo "successor-2 read written under $OUT (vs-comparator, vs-plan)"
