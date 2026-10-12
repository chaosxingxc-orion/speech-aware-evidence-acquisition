#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# The same-flight Perception-branch read of P-SV-1, P-SV-2 or P-SV-3 (owner decision 184).
#
#   bash scripts/flights/psv/psv_read.sh psv1|psv2|psv3|psv4 [--rescore] [--dry-run]
#
# RECIPE-DRIVEN. The recipe is the registered one for the cell: P-SV-1 reads its SEAL-ONLY completion
# (owner decision 197; docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/analysis-recipe-v1.json,
# recipe id slurp-stage3-psv1-fold-b-sealonly-branch-analysis-v1), P-SV-2 / P-SV-3 their original attempts
# (docs/readiness/2026-09-29-slurp-stage3-psvK-fold-b-v1/analysis-recipe-v1.json). The run id, the sealed attempt
# and the READ run id are read FROM the recipe, never hard-coded here.
#
# --dry-run: no countersign needed. Parses the sealed branch records, resolves the attempt and (seal-only) the
#   predecessor trace, and prints counts (rows, note parse status, presentation outcome, min_candidates_met,
#   extra contacts, level-2 contact resolution); stops before any gold, scorer or metric. Writes nothing.
# Otherwise:
# 0. REFUSES before anything is opened unless the READ row is ROOT COUNTERSIGNED, the sealed run manifest exists,
#    and the sealed attempt carries <run>.generation-manifest.json (the paired read's load_arm needs it; a
#    seal-only attempt sealed before E10e lacks it -- the refusal names the backfill command).
# 1. scripts/analysis/slurp_perception_branch_read.py (recipe mode, level 2): level 1 from the sealed branch
#    notes (gold only through the governed TRAIN loader, after the delivering branch reproduces the ledger
#    driver's P-node parse); level 2 renders each branch's first-visit Solver answer through the delivered row's
#    normaliser and projection and scores it ONCE with slurp-slu-official-train
#    (stage3_rollout_score.py --mode perception-branches into the sealed run's supply-variants/). IDEMPOTENT:
#    skipped when supply-variants/score-summary.json already carries the perception-branch schema for this
#    attempt; --rescore forces it. Then the twin-null and branch passes through stage3_paired_read.py column arms
#    (row bootstrap, cluster sample_id, the recipe's seed and draws, per-scenario tables) under
#    $SPEECHRL_DATA_DIR/analysis/<READ RUN>/{twin-null,branch}/, the registered rule, and one receipt
#    <READ RUN>/perception-branch-read.json (schema saea-perception-branch-read-v1; hashes and numbers only).
#    A pass directory that holds files, or an existing receipt, is refused (a sealed read is never overwritten).
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; three official column scorings at most. The
# driver applies the preregistered rule mechanically; the nomination is the coordinator's to countersign.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
LOCK=${SAEA_DATASETS_LOCK:-/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
usage() { echo "usage: psv_read.sh psv1|psv2|psv3|psv4 [--rescore] [--dry-run]"; exit 2; }
K=$1
[ -n "$K" ] && shift
case "$K" in
  psv1) RECIPE=docs/readiness/2026-09-29-slurp-stage3-psv1-fold-b-v1-resume-v1/analysis-recipe-v1.json ;;
  psv2|psv3) RECIPE=docs/readiness/2026-09-29-slurp-stage3-$K-fold-b-v1/analysis-recipe-v1.json ;;
  psv4) RECIPE=docs/readiness/2026-09-30-slurp-stage3-psv4-fold-b-v1/analysis-recipe-v1.json ;;
  *) usage ;;
esac
RESCORE=
DRY=
for arg in "$@"; do
  case "$arg" in
    --rescore) RESCORE=--rescore ;;
    --dry-run) DRY=--dry-run ;;
    *) usage ;;
  esac
done
ROSTER=docs/receipts/rosters/slurp-evo-fold-b-v2.json
ANALYSIS=scripts/analysis/slurp_perception_branch_read.py
cd "$MAIN" || exit 1
[ -f "$ANALYSIS" ] && [ -f "$RECIPE" ] || { echo "REFUSED: $ANALYSIS or $RECIPE is missing"; exit 8; }
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read -r RUN ATT READ_RUN < <("$PY" -B - "$RECIPE" <<'PY'
import json, sys
r = json.load(open(sys.argv[1], encoding="utf-8"))
arm = r["arms"]["arm"]
print(arm["run_id"], arm["attempt_id"], r.get("read_run_id") or r["run_ids"]["read"])
PY
)
[ -n "$RUN" ] && [ -n "$ATT" ] && [ -n "$READ_RUN" ] || { echo "REFUSED: $RECIPE names no run / attempt / READ run"; exit 8; }
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
echo "$K: run $RUN attempt $ATT read $READ_RUN"
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
if [ -n "$DRY" ]; then
  exec "$PY" -B "$ANALYSIS" --recipe "$RECIPE" --run "$RUN" --attempt "$ATT" --roster "$ROSTER" --level 2 \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" --dry-run
fi
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
if [ ! -f "$RUNDIR/$RUN.generation-manifest.json" ]; then
  EXP=$("$PY" -B -c "import json,sys; print(json.load(open(sys.argv[1]))['config']['fragments']['experiment'])" \
    "$RUNDIR/$RUN.run-manifest.json")
  echo "REFUSED: $RUNDIR has no $RUN.generation-manifest.json (a seal-only attempt sealed before E10e);"
  echo "  backfill it first (model-free; writes the two missing read inputs only):"
  echo "  $PY -B scripts/analysis/backfill_sealonly_read_inputs.py --repo-root $MAIN --data-root $SPEECHRL_DATA_DIR --experiment $EXP --run-id $RUN --attempt-id $ATT"
  exit 3
fi
mkdir -p "$OUT"
"$PY" -B "$ANALYSIS" --recipe "$RECIPE" --run "$RUN" --attempt "$ATT" --roster "$ROSTER" --level 2 \
  --analysis-root "$OUT" --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" --lock "$LOCK" $RESCORE \
  || { echo "BRANCH READ REFUSED OR FAILED"; exit 6; }
echo "$K branch read written under $OUT"
