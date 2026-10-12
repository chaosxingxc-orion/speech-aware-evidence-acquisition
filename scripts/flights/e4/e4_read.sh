#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Cell E4-1's same-flight shadow-column read (owner decision 185; recipe
# docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1/analysis-recipe-v1.json).
#
#   bash scripts/flights/e4/e4_read.sh [--rescore]
#
# 0. REFUSES before anything is opened unless the READ row SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1 is
#    ROOT COUNTERSIGNED (the same gate scripts/analysis/stage3_paired_read.py --package uses), the sealed run
#    manifest exists, and scripts/analysis/stage3_rollout_score.py offers --mode relisten (the CLI wiring of
#    render_relisten_shadow_columns / score_relisten_shadow_copies is an E4 engineering item).
# 1. Renders both shadow columns (relisten-replace-only, relisten-replace-drop-unheard) from the sealed
#    saea-relisten-v1 receipts and trace (AT1 self-check) and scores each ONCE with slurp-slu-official-train
#    into the sealed run's supply-variants/ directory, where scripts/analysis/slurp_paired_roster_read.py reads
#    a column from. IDEMPOTENT: skipped when supply-variants/relisten-score-summary.json already carries the
#    expected schema; --rescore forces it anyway (a retry after a later stage fails must not re-run the official
#    scorer over columns it already scored).
# 2. INTENT GUARD: per row, the (scenario, action) of each rendered shadow column must equal the sealed
#    delivered text's; any difference refuses the read (intent is identical by construction; this tests it).
#    Only counts are printed.
# 3. Two paired reads (row bootstrap, cluster key sample_id, 10,000 draws, seed 20260915, per-scenario
#    tables), each with the flight's own delivered column on the LEFT (no --left-column) and one shadow column
#    on the RIGHT (--right-column):
#      replace-only         -- right relisten-replace-only
#      replace-drop-unheard -- right relisten-replace-drop-unheard
#    through scripts/analysis/stage3_paired_read.py, each under
#    $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1/<pass>/; a pass directory that
#    already holds files is refused (a sealed read is never overwritten).
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; two official column scorings. The driver writes
# DESCRIPTIVE numbers; the nomination verdict is the coordinator's under the preregistered rule (bar: the design's
# own null, provisionally 0.735 x sqrt(200 / 1080) = 0.3163 pp SLU-F1).
RESCORE=0
for arg in "$@"; do
  case "$arg" in
    --rescore) RESCORE=1 ;;
    *) echo "usage: e4_read.sh [--rescore]"; exit 2 ;;
  esac
done
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
source "$MAIN/scripts/flights/batch/read_lib.sh"
RUN=SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-V1
# Owner decision 194: the arm sealed through the SEAL-ONLY completion; the delivered column and both shadow
# columns are read from that attempt (recipe docs/readiness/2026-09-29-slurp-stage3-e4-relisten-fold-a-v1-resume-v1/
# analysis-recipe-v1.json, recipe id slurp-stage3-relisten-fold-a-sealonly-column-analysis-v1). E4_ATTEMPT overrides.
ATT=${E4_ATTEMPT:-attempt-slurp-native-stage3-relisten-fold-a-generation-v1-seal-only}
PRED_TRACE_SHA=966613e416dd81c9cd5bbdc21b16050f394844e5b9da6522ed8451b1f1f233f6
READ_RUN=SAEA-SLURP-STAGE3-RELISTEN-FOLD-A-COLUMN-READ-V1
ROSTER=docs/receipts/rosters/slurp-evo-fold-a-v2.json
SPLIT=61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6
SCORER=slurp-slu-official-train
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
COLDIR=$RUNDIR/supply-variants
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
cd "$MAIN" || exit 1
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
read_require_countersigned docs/exposure-ledger.md "$READ_RUN" || exit 3
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
case "$ATT" in
  *-seal-only)
    RECIPE_ID=slurp-stage3-relisten-fold-a-sealonly-column-analysis-v1
    "$PY" -B - "$RUNDIR/$RUN.run-manifest.json" "$PRED_TRACE_SHA" <<'PY' || { echo "REFUSED: the seal-only manifest does not name the registered predecessor trace"; exit 3; }
import json, sys
m = json.load(open(sys.argv[1], encoding="utf-8"))
p = m.get("predecessor_attempt") or {}
sys.exit(0 if m.get("status") == "COMPLETED" and p.get("trace_sha256") == sys.argv[2] else 1)
PY
    ;;
  *) RECIPE_ID=slurp-stage3-relisten-fold-a-column-analysis-v1 ;;
esac
"$PY" -B scripts/analysis/stage3_rollout_score.py --help 2>/dev/null | grep -q "relisten" \
  || { echo "REFUSED: scripts/analysis/stage3_rollout_score.py offers no --mode relisten (E4 engineering item)"; exit 3; }
SCORE_RECEIPT="$COLDIR/relisten-score-summary.json"
SCORE_SCHEMA=saea-stage3-relisten-shadow-v1
if [ "$RESCORE" = 1 ] || ! read_scoring_done "$SCORE_RECEIPT" "$SCORE_SCHEMA"; then
  "$PY" -B scripts/analysis/stage3_rollout_score.py --mode relisten --run "$RUN" --attempt "$ATT" \
    --roster "$ROSTER" --analysis-root "$COLDIR" --scorer-id "$SCORER" \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" --stage all || { echo "COLUMN RENDER/SCORE FAILED"; exit 4; }
else
  echo "column scoring already done under $COLDIR (schema $SCORE_SCHEMA); skipping (--rescore forces)"
fi
"$PY" -B - "$RUNDIR" "$RUN" "$COLDIR" <<'PY' || { echo "INTENT GUARD REFUSED THE READ"; exit 5; }
import json
import sys
from pathlib import Path

from speech_aware_evidence_acquisition.reproduction.slurp_scoring import parse_slu_response

rundir, run, coldir = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])


def intents(path: Path) -> dict:
    out = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            scenario, action, _entities, ok = parse_slu_response(row.get("text") or "")
            out[row["sample_id"]] = (ok, scenario, action)
    return out


delivered = intents(rundir / f"{run}.outputs.jsonl")
failed = False
for column in ("relisten-replace-only", "relisten-replace-drop-unheard"):
    shadow = intents(coldir / f"arm-{column}-shadow-outputs.jsonl")
    if set(shadow) != set(delivered):
        print(f"{column}: roster differs from the delivered column")
        failed = True
        continue
    differing = sum(1 for sid in delivered if shadow[sid] != delivered[sid])
    print(f"intent guard {column}: {differing} of {len(delivered)} rows differ in (parsed, scenario, action)")
    failed = failed or differing != 0
sys.exit(1 if failed else 0)
PY
read_pass() {  # $1 pass name, $2 right column
  local dir="$OUT/$1"
  if [ -d "$dir" ] && [ -n "$(ls -A "$dir")" ]; then echo "REFUSED: $dir already holds files"; return 5; fi
  mkdir -p "$dir"
  "$PY" -B scripts/analysis/stage3_paired_read.py --per-scenario --stage all \
    --left-run "$RUN" --left-attempt "$ATT" --left-label "the delivered column" \
    --right-run "$RUN" --right-attempt "$ATT" --right-column "$2" --right-label "the shadow column $2" \
    --scorer-id "$SCORER" --expected-split-role discovery --roster "$ROSTER" --cluster-key sample_id \
    --split-identity-hash "$SPLIT" --seed 20260915 --draws 10000 \
    --recipe-id "$RECIPE_ID" \
    --title "Cell E4-1 shadow-column read ($1: $2 vs delivered)" --analysis-root "$dir" \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR"
}
read_pass replace-only relisten-replace-only || { echo "REPLACE-ONLY READ REFUSED OR FAILED"; exit 6; }
read_pass replace-drop-unheard relisten-replace-drop-unheard || { echo "REPLACE-DROP-UNHEARD READ REFUSED OR FAILED"; exit 6; }
echo "E4-1 shadow-column reads written under $OUT (replace-only, replace-drop-unheard)"
