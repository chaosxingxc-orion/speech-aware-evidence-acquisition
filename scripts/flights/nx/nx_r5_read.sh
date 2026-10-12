#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The composed read of NX round R5 (programme C2 R5; Stage J): a thin driver around the standard paired read plus the offset and v4g steps.
#
#   bash scripts/flights/nx/nx_r5_read.sh [--dry-run] [--skip-offline]
#
# RECIPE-DRIVEN: docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1/analysis-recipe-v1.json (recipe id
# slurp-nx-r5-composed-dev2000-added-paired-analysis-v1). The arms are read FROM it:
#   arms.arm                 the composed arm SAEA-SLURP-STAGE3-NX-R5-COMPOSED-DEV2000-ADDED-V1
#   arms.in_chain_replicate  the module OFF-arm replicate SAEA-SLURP-STAGE3-MODULE-COMP1B-AA-DEV2000-ADDED-V1 (same chain)
#   arms.comparator          the sealed A2 arm SAEA-SLURP-STAGE3-COMP1B-DEV2000-ADDED-V1 (cross-flight; the registered claim)
#   arms.a2_aa               the sealed A2 in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1 (the offset's left side)
# --dry-run: no countersign needed. Resolves the recipe and the sealed paths and prints identities only; opens no gold, runs no scorer, writes nothing.
# Otherwise:
# 0. REFUSES before anything is opened unless the READ row is ROOT COUNTERSIGNED and all four sealed runs carry a run manifest.
# 1. scripts/flights/read_paired_cell.sh <package>: pass vs-aa (composed minus the in-chain replicate; same chain; context) and pass vs-comparator
#    (composed minus the sealed A2 arm; the registered claim), whole-utterance clusters, 10,000 draws, seed 20260915, delivery / frontier
#    (the cost table) / per-scenario extensions as the standard driver runs them.
# 2. The OFFSET pass offset-replicate-vs-a2aa (left the sealed A2 A/A, right the replicate) and the context pass composed-vs-a2aa, through
#    scripts/analysis/stage3_paired_read.py in pair mode with the same roster, scorer, seed and draws.
# 3. OFFLINE v4g (0 GPU): scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g over the A2 arm, the A2 A/A and the replicate (delivered columns),
#    then scripts/analysis/nx_r5_v4g_contrast.py for every cross-flight contrast under the delivered columns and under ONE normaliser, with
#    per-scenario tables (natural-mixture and equal-stratum) and the decision-rule arithmetic. Skipped with --skip-offline.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts. The driver applies nothing mechanically beyond reporting; the verdict word is
# the coordinator's (owner decision 139). A pass directory that already holds files is never overwritten.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOCK=${SAEA_DATASETS_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
DRY=0
SKIP_OFFLINE=0
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --skip-offline) SKIP_OFFLINE=1 ;;
    *) echo "usage: nx_r5_read.sh [--dry-run] [--skip-offline]"; exit 2 ;;
  esac
  shift
done
PKG=docs/readiness/2026-10-09-slurp-nx-r5-composed-dev2000-added-v1
RECIPE=$PKG/analysis-recipe-v1.json
ROSTER=docs/receipts/rosters/slurp-dev-2000-added-v1.json
SCORER=slurp-slu-official
cd "$MAIN" || exit 1
[ -f "$RECIPE" ] || { echo "REFUSED: $RECIPE is missing"; exit 8; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read -r READ_RUN RECIPE_ID ARM_RUN ARM_ATT REP_RUN REP_ATT CMP_RUN CMP_ATT AA_RUN AA_ATT SEED DRAWS SPLIT < <("$PY" -B - "$RECIPE" "$ROSTER" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
roster = json.load(open(sys.argv[2], encoding="utf-8"))
a = r["arms"]
print(r["read_run_id"], r["recipe_id"], a["arm"]["run_id"], a["arm"]["attempt_id"], a["in_chain_replicate"]["run_id"],
      a["in_chain_replicate"]["attempt_id"], a["comparator"]["run_id"], a["comparator"]["attempt_id"], a["a2_aa"]["run_id"],
      a["a2_aa"]["attempt_id"], r["resampling"]["seed"], r["resampling"]["bootstrap_draws"], roster["split_identity_hash"])
PY
)
[ -n "$READ_RUN" ] && [ -n "$ARM_RUN" ] && [ -n "$AA_RUN" ] && [ -n "$SPLIT" ] || { echo "REFUSED: $RECIPE names no READ run / arms / roster"; exit 8; }
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
echo "nx-r5: read $READ_RUN recipe $RECIPE_ID arm $ARM_RUN replicate $REP_RUN comparator $CMP_RUN a2-aa $AA_RUN"
for pair in "$ARM_RUN/$ARM_ATT" "$REP_RUN/$REP_ATT" "$CMP_RUN/$CMP_ATT" "$AA_RUN/$AA_ATT"; do
  run=${pair%%/*}
  [ -f "$SPEECHRL_DATA_DIR/runs/$pair/$run.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under runs/$pair"; exit 3; }
done
if [ "$DRY" = 1 ]; then
  echo "(dry) all four sealed runs present; would read: vs-aa, vs-comparator, offset-replicate-vs-a2aa, composed-vs-a2aa under $OUT, then offline v4g and v4g-contrast"
  exit 0
fi
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
mkdir -p "$OUT"
# 1. the standard paired read (vs-aa, vs-comparator)
for pass in vs-aa vs-comparator; do
  if [ -d "$OUT/$pass" ] && [ -n "$(ls -A "$OUT/$pass")" ]; then
    if [ -f "$OUT/$pass/verdict.json" ]; then echo "pass $pass already complete; skipping"; continue; fi
    echo "REFUSED: $OUT/$pass already holds files but no verdict.json (a partial pass)"; exit 6
  fi
  bash "$MAIN/scripts/flights/read_paired_cell.sh" "$PKG" --passes "$pass" || { echo "READ FAILED ($pass)"; exit 7; }
done
# 2. the offset pass and the sealed-base context pass (pair mode)
pair_pass() {  # name left_run left_att right_run right_att label_left label_right
  local name=$1
  if [ -d "$OUT/$name" ] && [ -n "$(ls -A "$OUT/$name")" ]; then
    if [ -f "$OUT/$name/verdict.json" ]; then echo "pass $name already complete; skipping"; return 0; fi
    echo "REFUSED: $OUT/$name already holds files but no verdict.json (a partial pass)"; return 6
  fi
  mkdir -p "$OUT/$name"
  "$PY" -B scripts/analysis/stage3_paired_read.py --stage3 --stage all \
    --left-run "$2" --left-attempt "$3" --left-label "$6" --right-run "$4" --right-attempt "$5" --right-label "$7" \
    --scorer-id "$SCORER" --expected-split-role dev --roster "$ROSTER" --cluster-key utterance_id \
    --split-identity-hash "$SPLIT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
    --seed "$SEED" --draws "$DRAWS" --recipe-id "$RECIPE_ID" \
    --title "NX R5 composed read ($name)" --analysis-root "$OUT/$name"
}
pair_pass offset-replicate-vs-a2aa "$AA_RUN" "$AA_ATT" "$REP_RUN" "$REP_ATT" "the sealed A2 in-chain A/A" "the module OFF-arm replicate (offset instrument)" \
  || { echo "OFFSET PASS FAILED"; exit 7; }
pair_pass composed-vs-a2aa "$AA_RUN" "$AA_ATT" "$ARM_RUN" "$ARM_ATT" "the sealed A2 in-chain A/A" "the composed arm (context)" \
  || { echo "COMPOSED-VS-A2AA PASS FAILED"; exit 7; }
# 3. offline v4g columns and the cross-flight contrasts under one normaliser
if [ "$SKIP_OFFLINE" = 1 ]; then
  echo "offline v4g columns skipped (--skip-offline)"
else
  for entry in "a2-arm:$CMP_RUN/$CMP_ATT" "a2-aa:$AA_RUN/$AA_ATT" "replicate:$REP_RUN/$REP_ATT"; do
    label="offline-v4g/${entry%%:*}"
    if [ -f "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1/$label/report.json" ]; then echo "offline v4g (${entry%%:*}) already written; skipping"; continue; fi
    "$PY" -B scripts/analysis/slurp_nx_postproc_v4_apply.py --apply v4g --pool "${entry#*:}" --label "$label" \
      --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" || { echo "OFFLINE v4g (${entry%%:*}) FAILED"; exit 11; }
  done
  "$PY" -B scripts/analysis/nx_r5_v4g_contrast.py --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" --out-dir "$OUT/v4g-contrast" --recipe "$RECIPE" \
    || { echo "V4G CONTRAST FAILED"; exit 12; }
fi
echo "NX R5 composed read written under $OUT (vs-aa, vs-comparator, offset-replicate-vs-a2aa, composed-vs-a2aa, offline-v4g via the apply root, v4g-contrast)"
