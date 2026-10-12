#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The same-flight Solver template-column read of NX round R1 (NX programme C2 R1; instrument E1/E2).
#
#   bash scripts/analysis/nx_r1_read.sh [--iteration 1|2] [--rescore] [--dry-run] [--skip-offline]
#   bash scripts/analysis/nx_r1_read.sh --iteration N --node-local-out <subfolder> [--dry-run]     (RE-READ mode)
#
# RE-READ mode (--node-local-out NAME): for a FLOWN iteration, re-runs ONLY the node-local step (step 1) with the current reader
# (schema v2) into a NEW subfolder <analysis root>/NAME and exits. It never touches node-local/, supply-variants/, the official
# passes (aa-vs-lock, <candidate>-vs-lock), cross-iteration/ or offline-v4/, and it runs no scorer. It REFUSES: a NAME that is not a
# plain folder name or that equals one of those registered outputs (exit 2); an iteration whose sealed run manifest is absent
# (exit 3); a NAME that already holds files, or that is not a directory (exit 6; checked also with --dry-run); a READ row that is
# not root countersigned (exit 3, not with --dry-run). It does not combine with --rescore or --skip-offline (exit 2).
#
# --iteration N selects the R1 iteration (default 1) and with it the registered recipe; nothing else is iteration-specific here:
# the run, attempt, READ run, recipe id and candidate arm ids are all read FROM the recipe. Iteration 2 additionally runs the
# recipe's DESCRIPTIVE cross-iteration pass (step 2b; non-gating, skipped with a notice when iteration 1's official column
# scoring is absent).
#
# RECIPE-DRIVEN. The recipe is the registered one (docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/analysis-recipe-v1.json,
# recipe id slurp-nx-r1-solver-fold-b-column-analysis-v1; iteration 2: ...-slurp-nx-r1-i2-solver-fold-b-v1/analysis-recipe-v1.json). The run id, the sealed attempt and the READ run id are read FROM the
# recipe, never hard-coded here.
#
# --dry-run: no countersign needed. Resolves the recipe, the sealed run and its arm group and prints identities only; opens no
#   gold, runs no scorer. Writes nothing.
# Otherwise:
# 0. REFUSES before anything is opened unless the READ row is ROOT COUNTERSIGNED and the sealed run manifest exists.
# 1. NODE-LOCAL (E2, report schema saea-nx-solver-column-read-v2): scripts/analysis/slurp_nx_solver_column_read.py reads every arm's
#    first Solver answer paired per row against the delivering lock arm in two views: the NORMALISED view (the answer after the
#    delivered row's own sealed normaliser, derived by stage3_rollout_score.normalise_arm_answer -- the same function the step-2
#    column renderer calls) carries the PRIMARY exact_set_normalised and the mechanical screen; the RAW view and a per-arm
#    raw-vs-normalised flip table are diagnostics. Metrics: parse validity, entity exact-set, empty-gold false fill, non-empty
#    exact, per-slot-type counts; whole-utterance bootstrap 10,000 draws seed 20260915 and the paired Wilson share; gold only
#    through the governed TRAIN loader. The reader needs no new argument (the normaliser id is read from each sealed row).
#    Output <analysis root>/node-local/. Iteration 1 was registered with the raw primary; its node-local pass is re-read with
#    this reader into a SEPARATE subfolder (node-local-v2) only on the coordinator's word, never into node-local/.
# 2. OFFICIAL COLUMNS: each arm's first-visit Solver answer is rendered through the delivered row's normaliser and projection
#    and scored ONCE with slurp-slu-official-train (scripts/analysis/stage3_rollout_score.py --mode supply-variants, seven
#    jobs, never sharded) into <run dir>/supply-variants/. IDEMPOTENT: skipped when score-summary.json already carries the
#    first-visit schema; --rescore forces it. Then the twin null (aa vs lock) and each candidate vs lock through
#    scripts/analysis/stage3_paired_read.py column arms (row bootstrap, cluster key sample_id -- the tool's constraint for
#    column arms -- 10,000 draws, seed 20260915, per-scenario tables) under <analysis root>/<pass>/. A pass directory that
#    already holds files is never overwritten; one that sealed its verdict.json is skipped on a re-run (RESUME), a partial one refuses (exit 6).
# 3. OFFLINE POST-PROCESSING COLUMNS (0 GPU): v4 (saea-deliver-normalise-v4, the five-rule set of
#    docs/results/2026-10-09-slurp-nx-postprocessing-v4-offline-read.md section 6) and v4g (v4 with the TRAIN-only guards
#    ee-wilson and ti-expressible of docs/results/2026-10-09-slurp-nx-postprocessing-v4-audio-attribution.md) applied to every
#    arm's delivered column. The rules live in scripts/analysis/slurp_nx_postproc_v4_search.py (the separate agent's driver); the
#    application of the REGISTERED normalisers to a sealed column is scripts/analysis/slurp_nx_postproc_v4_apply.py
#    (--apply v4|v4g --pool <run>/<attempt> --column <arm id>), called here with the interface in the loop below. The driver admits this Fold B run because the registered recipe
#    names it and declares the v4/v4g columns (recipe_admission; the test split and unnamed Fold B pools stay refused). The lock row v4g(lock) - lock is the
#    fresh-roster confirmation of v4g (lock rule: CI95 lower bound > 0 here). The CELL's runtime delivery normaliser is untouched.
#    Skipped with --skip-offline.
# 4. REVIEW-OFF vs FULL GRAPH is NOT computed here: it is the cross-flight comparison of the lock arm's official column with
#    the P-SV-3 a-agree delivered column on the same Fold B (docs/results/2026-09-30-slurp-psv3-fold-b-branch-read.md), read by
#    hand from files on record (README section "Review-off vs full graph"); no extra flight.
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; seven official column scorings plus the offline scorings. The
# driver applies nothing mechanically beyond reporting; the verdict word is the coordinator's under the package's rule.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOCK=${SAEA_DATASETS_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
usage() { echo "usage: nx_r1_read.sh [--iteration 1|2] [--rescore] [--dry-run] [--skip-offline] | --iteration N --node-local-out <subfolder> [--dry-run]"; exit 2; }
RESCORE=0
NODE_OUT=
DRY=0
SKIP_OFFLINE=0
ITER=1
while [ $# -gt 0 ]; do
  case "$1" in
    --rescore) RESCORE=1 ;;
    --dry-run) DRY=1 ;;
    --skip-offline) SKIP_OFFLINE=1 ;;
    --iteration) shift; ITER=${1:-}; [ "$ITER" = 1 ] || [ "$ITER" = 2 ] || usage ;;
    --node-local-out) shift; NODE_OUT=${1:-}; [ -n "$NODE_OUT" ] || usage ;;
    *) usage ;;
  esac
  shift
done
if [ -n "$NODE_OUT" ]; then
  [ "$RESCORE" = 0 ] && [ "$SKIP_OFFLINE" = 0 ] || { echo "REFUSED: --node-local-out re-runs the node-local step only; it does not combine with --rescore or --skip-offline"; exit 2; }
  case "$NODE_OUT" in
    node-local|supply-variants|offline-v4|cross-iteration|aa-vs-lock|*-vs-lock|.*|*/*|*[!A-Za-z0-9._-]*)
      echo "REFUSED: --node-local-out '$NODE_OUT' is not a plain new folder name (reserved: node-local, supply-variants, offline-v4, cross-iteration, aa-vs-lock, <arm>-vs-lock)"; exit 2 ;;
  esac
fi
case "$ITER" in
  1) RECIPE=docs/readiness/2026-10-09-slurp-nx-r1-solver-fold-b-v1/analysis-recipe-v1.json ;;
  2) RECIPE=docs/readiness/2026-10-09-slurp-nx-r1-i2-solver-fold-b-v1/analysis-recipe-v1.json ;;
esac
ROSTER=docs/receipts/rosters/slurp-evo-fold-b-v2.json
SPLIT=4407794c4a5d2e8883d93fdf242deb33c0987405d62e05a7d8416f5251a3484a
SCORER=slurp-slu-official-train
NODE_READ=scripts/analysis/slurp_nx_solver_column_read.py
V4_DRIVER=${V4_DRIVER:-scripts/analysis/slurp_nx_postproc_v4_apply.py}
cd "$MAIN" || exit 1
[ -f "$RECIPE" ] && [ -f "$NODE_READ" ] || { echo "REFUSED: $RECIPE or $NODE_READ is missing"; exit 8; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read -r RUN ATT READ_RUN CANDIDATES RECIPE_ID XRUN XATT XCOL < <("$PY" -B - "$RECIPE" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
arm = r["arms"]["arm"]
# Candidates are the pinned template columns; the twin aa and the delivering lock arm are not candidates.
cands = [k for k, v in r["arms"]["columns"].items() if k not in ("aa", "lock") and "relpath" in v]
cross = (r.get("cross_iteration_contrast") or {}).get("comparator") or {}
print(arm["run_id"], arm["attempt_id"], r["read_run_id"], ",".join(cands), r["recipe_id"],
      cross.get("run_id", "-"), cross.get("attempt_id", "-"), cross.get("column", "-"))
PY
)
[ -n "$RUN" ] && [ -n "$ATT" ] && [ -n "$READ_RUN" ] && [ -n "$CANDIDATES" ] && [ -n "$RECIPE_ID" ] || { echo "REFUSED: $RECIPE names no run / attempt / READ run / candidates"; exit 8; }
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
echo "nx-r1: run $RUN attempt $ATT read $READ_RUN candidates $CANDIDATES"
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
if [ -n "$NODE_OUT" ]; then
  # RE-READ mode: the node-local step only, into a NEW subfolder; every registered output stays untouched.
  if [ -e "$OUT/$NODE_OUT" ] && { [ ! -d "$OUT/$NODE_OUT" ] || [ -n "$(ls -A "$OUT/$NODE_OUT")" ]; }; then
    echo "REFUSED: $OUT/$NODE_OUT already exists and is not an empty directory"; exit 6
  fi
  if [ "$DRY" = 1 ]; then
    echo "(dry) re-read mode: would run ONLY the node-local step (reader $NODE_READ) for iteration $ITER into $OUT/$NODE_OUT; node-local/, supply-variants/, the official passes and offline-v4 are untouched"
    exit 0
  fi
  read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
  mkdir -p "$OUT/$NODE_OUT"
  "$PY" -B "$NODE_READ" --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" --run-id "$RUN" --attempt-id "$ATT" --split train     --out-dir "$OUT/$NODE_OUT" || { echo "NODE-LOCAL RE-READ FAILED"; exit 5; }
  echo "node-local re-read (iteration $ITER) written under $OUT/$NODE_OUT"
  exit 0
fi
if [ "$DRY" = 1 ]; then
  echo "(dry) recipe $RECIPE_ID (iteration $ITER)"
  echo "(dry) sealed run present at $RUNDIR; would read: node-local -> $OUT/node-local, official passes aa-vs-lock then <candidate>-vs-lock under $OUT, offline v4/v4g under $OUT/offline-v4"
  exit 0
fi
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
if [ ! -f "$RUNDIR/$RUN.generation-manifest.json" ]; then
  echo "REFUSED: $RUNDIR has no $RUN.generation-manifest.json (the paired read's load_arm needs it)"; exit 3
fi
mkdir -p "$OUT"
# 1. node-local
if [ -d "$OUT/node-local" ] && [ -n "$(ls -A "$OUT/node-local")" ]; then
  echo "node-local read already present under $OUT/node-local; skipping"
else
  "$PY" -B "$NODE_READ" --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" --run-id "$RUN" --attempt-id "$ATT" --split train \
    --out-dir "$OUT/node-local" || { echo "NODE-LOCAL READ FAILED"; exit 5; }
fi
# 2. official columns
SCORE_RECEIPT="$RUNDIR/supply-variants/score-summary.json"
SCORE_SCHEMA=saea-stage3-supply-variant-first-visit-v1
if [ "$RESCORE" = 1 ] || ! read_scoring_done "$SCORE_RECEIPT" "$SCORE_SCHEMA"; then
  "$PY" -B scripts/analysis/stage3_rollout_score.py --mode supply-variants --run "$RUN" --attempt "$ATT" \
    --roster "$ROSTER" --analysis-root "$RUNDIR/supply-variants" --scorer-id "$SCORER" --stage all \
    --data-root "$SPEECHRL_DATA_DIR" || { echo "COLUMN RENDER/SCORE FAILED"; exit 5; }
else
  echo "column scoring already done under $RUNDIR/supply-variants (schema $SCORE_SCHEMA); skipping (--rescore forces)"
fi
for right in aa ${CANDIDATES//,/ }; do
  pass="$right-vs-lock"
  if [ "$right" = aa ]; then LABEL="the twin aa (the null)"; else LABEL="candidate $right (gating)"; fi
  if [ -d "$OUT/$pass" ] && [ -n "$(ls -A "$OUT/$pass")" ]; then
    # RESUME: a pass that sealed its verdict is complete and is never overwritten or redone; a partial one still refuses.
    if [ -f "$OUT/$pass/verdict.json" ]; then echo "official pass $pass already complete under $OUT/$pass; skipping"; continue; fi
    echo "REFUSED: $OUT/$pass already holds files but no verdict.json (a partial pass)"; exit 6
  fi
  mkdir -p "$OUT/$pass"
  "$PY" -B scripts/analysis/stage3_paired_read.py --per-scenario \
    --stage all --left-run "$RUN" --left-attempt "$ATT" --left-column lock --left-label "the delivering lock arm" \
    --right-run "$RUN" --right-attempt "$ATT" --right-column "$right" --right-label "$LABEL" \
    --scorer-id "$SCORER" --expected-split-role discovery --roster "$ROSTER" --cluster-key sample_id \
    --split-identity-hash "$SPLIT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
    --seed 20260915 --draws 10000 --recipe-id "$RECIPE_ID" \
    --title "NX R1 Solver template column read ($pass)" --analysis-root "$OUT/$pass" || { echo "READ FAILED ($pass)"; exit 7; }
done
# 2b. DESCRIPTIVE cross-iteration pass (iteration 2 only; recipe cross_iteration_contrast; gates nothing, never fails the read)
if [ "$ITER" = 2 ] && [ "$XRUN" != "-" ]; then
  XDIR=$SPEECHRL_DATA_DIR/runs/$XRUN/$XATT
  if ! read_scoring_done "$XDIR/supply-variants/score-summary.json" "$SCORE_SCHEMA"; then
    echo "(cross-iteration pass skipped: iteration 1's official column scoring is absent under $XDIR/supply-variants)"
  else
    for right in lock ${CANDIDATES//,/ }; do
      if [ "$right" = lock ]; then left_col=lock; else left_col=$XCOL; fi
      pass="cross-iteration/$right-vs-i1-$left_col"
      if [ -d "$OUT/$pass" ] && [ -n "$(ls -A "$OUT/$pass")" ]; then echo "(cross-iteration $pass already holds files; skipping)"; continue; fi
      mkdir -p "$OUT/$pass"
      "$PY" -B scripts/analysis/stage3_paired_read.py --per-scenario \
        --stage all --left-run "$XRUN" --left-attempt "$XATT" --left-column "$left_col" --left-label "iteration-1 $left_col (descriptive)" \
        --right-run "$RUN" --right-attempt "$ATT" --right-column "$right" --right-label "iteration-2 $right (descriptive)" \
        --scorer-id "$SCORER" --expected-split-role discovery --roster "$ROSTER" --cluster-key sample_id \
        --split-identity-hash "$SPLIT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
        --seed 20260915 --draws 10000 --recipe-id "$RECIPE_ID" \
        --title "NX R1 iteration 2 cross-iteration descriptive contrast ($pass)" --analysis-root "$OUT/$pass" \
        || echo "(cross-iteration $pass FAILED; non-gating, the read continues)"
    done
  fi
fi
# 3. offline v4 / v4g columns over every arm's delivered column
if [ "$SKIP_OFFLINE" = 1 ]; then
  echo "offline v4/v4g columns skipped (--skip-offline); run this driver again without it, or the V4 driver by hand"
else
  # Interface of the application driver on master (merge 7bfc09b3b): --apply v4|v4g --pool <run>/<attempt> [--column <arm id>]
  # [--label <dir>]. Override V4_DRIVER / V4_APPLY_ARGS if the final spelling differs.
  "$PY" -B "$V4_DRIVER" --help 2>&1 | grep -q -- "--apply" || {
    echo "REFUSED (offline step): $V4_DRIVER does not advertise --apply v4|v4g --pool --column yet; the v4/v4g application"
    echo "  (scripts/analysis/slurp_nx_postproc_v4_apply.py is on master since merge 7bfc09b3b; this branch predates it). Re-run with"
    echo "  --skip-offline now and without it after the merge; the driver admits this run by its registered recipe."; exit 10; }
  for variant in v4 v4g; do
    for column in lock aa ${CANDIDATES//,/ }; do
      label="offline-v4/$variant-$column"
      # RESUME: an apply report is write-once; one already written is complete and is not redone.
      if [ -f "$SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-NX-POSTPROC-V4-APPLY-V1/$label/report.json" ]; then
        echo "offline $variant ($column) already written; skipping"; continue; fi
      "$PY" -B "$V4_DRIVER" --apply "$variant" --pool "$RUN/$ATT" --column "$column" --label "$label" \
        --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" ${V4_APPLY_ARGS:-} || { echo "OFFLINE $variant ($column) FAILED"; exit 11; }
    done
  done
fi
echo "NX R1 column reads written under $OUT (node-local, aa-vs-lock, ${CANDIDATES//,/-vs-lock, }-vs-lock, offline-v4)"
