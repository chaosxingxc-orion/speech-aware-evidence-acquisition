#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The same-flight Perception template-column read of NX round R6-P1 (design docs/readiness/2026-10-10-slurp-nx-r6-node-local-then-cascade-design-v1.md
# sections 2.2 and 4; instrument E1/E2 at the Perception node; reader E2b; information-gain driver).
#
#   bash scripts/analysis/nx_r6_read.sh [--dry-run] [--rescore] [--skip-official] [--skip-gain]
#
# RECIPE-DRIVEN. The recipe is the registered one (docs/readiness/2026-10-10-slurp-nx-r6-perception-fold-b-v1/analysis-recipe-v1.json,
# recipe id slurp-nx-r6-perception-fold-b-column-analysis-v1). The run id, the sealed attempt, the READ run id, the candidate arm ids
# and each arm's allowed E= tag set are read FROM the recipe, never hard-coded here.
#
# --dry-run: no countersign needed. Resolves the recipe and the sealed run and prints identities only; opens no gold, runs no scorer.
#   Writes nothing.
# Otherwise:
# 0. REFUSES before anything is opened unless the READ row is ROOT COUNTERSIGNED and the sealed run manifest exists.
# 1. NODE-LOCAL (reader E2b, report schema saea-nx-perception-column-read-v1): scripts/analysis/slurp_nx_perception_column_read.py reads
#    every arm's Perception notes and level-2 Solver answer paired per row against the delivering lock arm: the Perception note metrics
#    (gold on list, rank, top-1, list size, prompt tokens), the distinction-tag parse classes, the rank-1 and list-majority presence
#    verdict (E=none AUC / precision / recall against empty gold, E=some precision / recall, unsure by gold class), the heard-mention
#    containment and option precision, and the level-2 Solver column's exact-set read. --tag-set per arm comes from the recipe (p3 admits
#    unsure). Gold only through the governed TRAIN loader. Output <analysis root>/node-local/ (write-once).
# 2. INFORMATION GAIN and the GATE ESTIMATE: for every candidate arm and every baseline in {n1, n1+prior, n1+prior+lock},
#    scripts/analysis/slurp_nx_r6_upstream_empty.py --verdict-source perception-arm:<arm> --gain-baseline <b> writes
#    $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1/<arm>/<baseline>/ (write-once; an existing output is skipped).
#    Skipped with --skip-gain.
# 3. OFFICIAL COLUMNS (UNEXERCISED on a v4 Perception template run; never gates the node-local acceptance): each arm's level-2
#    first-visit Solver answer is rendered through the delivered row's normaliser and projection and scored ONCE with
#    slurp-slu-official-train (scripts/analysis/stage3_rollout_score.py --mode perception-branches) into <run dir>/supply-variants/,
#    then the twin null (aa vs lock) and each candidate vs lock through scripts/analysis/stage3_paired_read.py column arms (row
#    bootstrap, cluster key sample_id, 10,000 draws, seed 20260915). IDEMPOTENT: skipped when score-summary.json already carries the
#    perception-branch schema; --rescore forces it. A pass directory that already holds files is never overwritten. Skipped with
#    --skip-official.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts. The driver applies nothing mechanically beyond reporting; the verdict
# word is the coordinator's under the package's acceptance block.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOCK=${SAEA_DATASETS_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
usage() { echo "usage: nx_r6_read.sh [--dry-run] [--rescore] [--skip-official] [--skip-gain]"; exit 2; }
RESCORE=0
DRY=0
SKIP_OFFICIAL=0
SKIP_GAIN=0
while [ $# -gt 0 ]; do
  case "$1" in
    --rescore) RESCORE=1 ;;
    --dry-run) DRY=1 ;;
    --skip-official) SKIP_OFFICIAL=1 ;;
    --skip-gain) SKIP_GAIN=1 ;;
    *) usage ;;
  esac
  shift
done
RECIPE=docs/readiness/2026-10-10-slurp-nx-r6-perception-fold-b-v1/analysis-recipe-v1.json
ROSTER=docs/receipts/rosters/slurp-evo-fold-b-v2.json
SPLIT=4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a
SCORER=slurp-slu-official-train
NODE_READ=scripts/analysis/slurp_nx_perception_column_read.py
GAIN_READ=scripts/analysis/slurp_nx_r6_upstream_empty.py
GAIN_ID=SAEA-SLURP-NX-R6-PERCEPTION-GAIN-V1
BASELINES="n1 n1+prior n1+prior+lock"
cd "$MAIN" || exit 1
[ -f "$RECIPE" ] && [ -f "$NODE_READ" ] && [ -f "$GAIN_READ" ] || { echo "REFUSED: $RECIPE, $NODE_READ or $GAIN_READ is missing"; exit 8; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read -r RUN ATT READ_RUN CANDIDATES RECIPE_ID TAGSETS < <("$PY" -B - "$RECIPE" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
arm = r["arms"]["arm"]
# Candidates are the pinned template columns; the twin aa and the delivering lock arm are not candidates.
cands = [k for k, v in r["arms"]["columns"].items() if k not in ("aa", "lock") and "relpath" in v]
tags = ";".join(f"{a}={','.join(v)}" for a, v in r["tag_sets"].items())
print(arm["run_id"], arm["attempt_id"], r["read_run_id"], ",".join(cands), r["recipe_id"], tags)
PY
)
[ -n "$RUN" ] && [ -n "$ATT" ] && [ -n "$READ_RUN" ] && [ -n "$CANDIDATES" ] && [ -n "$RECIPE_ID" ] && [ -n "$TAGSETS" ] \
  || { echo "REFUSED: $RECIPE names no run / attempt / READ run / candidates / tag sets"; exit 8; }
TAG_ARGS=()
for spec in ${TAGSETS//;/ }; do TAG_ARGS+=(--tag-set "$spec"); done
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
echo "nx-r6: run $RUN attempt $ATT read $READ_RUN candidates $CANDIDATES tag sets $TAGSETS"
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
if [ "$DRY" = 1 ]; then
  echo "(dry) recipe $RECIPE_ID"
  echo "(dry) sealed run present at $RUNDIR; would read: node-local -> $OUT/node-local, information gain + gate estimate -> $SPEECHRL_DATA_DIR/analysis/$GAIN_ID/<arm>/<baseline> for baselines $BASELINES, official passes aa-vs-lock then <candidate>-vs-lock under $OUT"
  exit 0
fi
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
if [ ! -f "$RUNDIR/$RUN.generation-manifest.json" ]; then
  echo "REFUSED: $RUNDIR has no $RUN.generation-manifest.json (the paired read's load_arm needs it)"; exit 3
fi
mkdir -p "$OUT"
# 1. node-local (reader E2b)
if [ -d "$OUT/node-local" ] && [ -n "$(ls -A "$OUT/node-local")" ]; then
  echo "node-local read already present under $OUT/node-local; skipping"
else
  "$PY" -B "$NODE_READ" --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" --run-id "$RUN" --attempt-id "$ATT" --split train \
    --out-dir "$OUT/node-local" "${TAG_ARGS[@]}" || { echo "NODE-LOCAL READ FAILED"; exit 5; }
fi
# 2. information gain and the gate estimate, per candidate arm and baseline
if [ "$SKIP_GAIN" = 1 ]; then
  echo "information-gain / gate-estimate reads skipped (--skip-gain)"
else
  for arm in ${CANDIDATES//,/ }; do
    for baseline in $BASELINES; do
      dir="$SPEECHRL_DATA_DIR/analysis/$GAIN_ID/$arm/${baseline//+/-}"
      if [ -f "$dir/report.json" ]; then echo "gain read $arm / $baseline already written; skipping"; continue; fi
      "$PY" -B "$GAIN_READ" --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" --run-id "$RUN" --attempt-id "$ATT" \
        --verdict-source "perception-arm:$arm" --gain-baseline "$baseline" "${TAG_ARGS[@]}" \
        || { echo "GAIN READ FAILED ($arm / $baseline)"; exit 12; }
    done
  done
fi
# 3. official columns (unexercised on a v4 template run; non-gating)
if [ "$SKIP_OFFICIAL" = 1 ]; then
  echo "official column scoring and paired passes skipped (--skip-official)"
  echo "NX R6 reads written under $OUT (node-local; gain reads under $SPEECHRL_DATA_DIR/analysis/$GAIN_ID)"
  exit 0
fi
SCORE_RECEIPT="$RUNDIR/supply-variants/score-summary.json"
SCORE_SCHEMA=saea-stage3-perception-branch-solver-first-visit-v1
if [ "$RESCORE" = 1 ] || ! read_scoring_done "$SCORE_RECEIPT" "$SCORE_SCHEMA"; then
  "$PY" -B scripts/analysis/stage3_rollout_score.py --mode perception-branches --run "$RUN" --attempt "$ATT" \
    --roster "$ROSTER" --analysis-root "$RUNDIR/supply-variants" --scorer-id "$SCORER" --stage all \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" || { echo "COLUMN RENDER/SCORE FAILED"; exit 5; }
else
  echo "column scoring already done under $RUNDIR/supply-variants (schema $SCORE_SCHEMA); skipping (--rescore forces)"
fi
for right in aa ${CANDIDATES//,/ }; do
  pass="$right-vs-lock"
  if [ "$right" = aa ]; then LABEL="the twin aa (the null)"; else LABEL="candidate $right"; fi
  if [ -d "$OUT/$pass" ] && [ -n "$(ls -A "$OUT/$pass")" ]; then
    # RESUME: a pass that sealed its verdict is complete and is never overwritten or redone; a partial one still refuses.
    if [ -f "$OUT/$pass/score-contrasts.json" ]; then echo "official pass $pass already complete under $OUT/$pass; skipping"; continue; fi
    echo "REFUSED: $OUT/$pass already holds files but no score-contrasts.json (a partial pass)"; exit 6
  fi
  mkdir -p "$OUT/$pass"
  "$PY" -B scripts/analysis/stage3_paired_read.py --per-scenario \
    --stage all --left-run "$RUN" --left-attempt "$ATT" --left-column lock --left-label "the delivering lock arm" \
    --right-run "$RUN" --right-attempt "$ATT" --right-column "$right" --right-label "$LABEL" \
    --scorer-id "$SCORER" --expected-split-role discovery --roster "$ROSTER" --cluster-key sample_id \
    --split-identity-hash "$SPLIT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
    --seed 20260915 --draws 10000 --recipe-id "$RECIPE_ID" \
    --title "NX R6-P1 Perception template column read ($pass)" --analysis-root "$OUT/$pass" || { echo "READ FAILED ($pass)"; exit 7; }
done
echo "NX R6 column reads written under $OUT (node-local, aa-vs-lock, ${CANDIDATES//,/-vs-lock, }-vs-lock; gain reads under $SPEECHRL_DATA_DIR/analysis/$GAIN_ID)"
