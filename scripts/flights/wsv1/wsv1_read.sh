#!/bin/bash
# Cell W-SV-1's same-flight column read (owner decision 172; recipe
# docs/readiness/2026-09-28-slurp-stage3-wsv1-fold-a-v1/analysis-recipe-v1.json).
#
#   bash scripts/flights/wsv1/wsv1_read.sh
#
# 0. REFUSES before anything is opened unless the READ row SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1 is ROOT
#    COUNTERSIGNED (the same gate scripts/analysis/stage3_paired_read.py --package uses) and the sealed run
#    manifest exists.
# 1. Renders the three first-visit columns (a-base, b-exk30, t-twin) through the delivered row's normaliser and
#    projection (AT1 self-check) and scores each ONCE with slurp-slu-official-train
#    (scripts/analysis/stage3_rollout_score.py --mode supply-variants) into the sealed run's supply-variants/
#    directory, where scripts/analysis/slurp_paired_roster_read.py reads a column from.
# 2. Two paired reads (row bootstrap, cluster key sample_id, 10,000 draws, seed 20260928, per-scenario tables):
#      twin-null -- left a-base, right t-twin   (the bar: |offset| + CI95 half-width per metric)
#      knob      -- left a-base, right b-exk30  (read at that bar)
#    through scripts/analysis/stage3_paired_read.py --left-column/--right-column, each under
#    $SPEECHRL_DATA_DIR/analysis/SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1/<pass>/; a pass directory that
#    already holds files is refused (a sealed read is never overwritten).
# MODEL-FREE: zero model / tokenizer / encoder / server contacts; three official column scorings. The driver
# writes DESCRIPTIVE numbers; the nomination verdict is the coordinator's under the preregistered rule.
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
export SPEECHRL_DATA_DIR=${SPEECHRL_DATA_DIR:-/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data}
RUN=SAEA-SLURP-STAGE3-WSV1-FOLD-A-V1
ATT=attempt-slurp-native-stage3-wsv1-fold-a-generation-v1
READ_RUN=SAEA-SLURP-STAGE3-WSV1-FOLD-A-COLUMN-READ-V1
ROSTER=docs/receipts/rosters/slurp-evo-fold-a-v2.json
SPLIT=61b0f06254975873bea6afb287ab54823dc71b57e5398697b9bef817e25398b6
SCORER=slurp-slu-official-train
RUNDIR=$SPEECHRL_DATA_DIR/runs/$RUN/$ATT
OUT=$SPEECHRL_DATA_DIR/analysis/$READ_RUN
cd "$MAIN" || exit 1
"$PY" -B -c "import speech_aware_evidence_acquisition as m, sys; sys.exit(0 if m.__file__.startswith('$MAIN') else 9)" \
  || { echo "REFUSED: the package under test is not $MAIN (shared-venv hijack)"; exit 9; }
"$PY" -B - "$MAIN" "$READ_RUN" <<'PY' || exit 3
import importlib.util
import sys
from pathlib import Path

repo, read_run = Path(sys.argv[1]), sys.argv[2]
spec = importlib.util.spec_from_file_location("frc", repo / "scripts/checks/flight_registration_check.py")
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)
rows = gate.parse_ledger(repo, Path("docs/exposure-ledger.md")).get(read_run, [])
if not rows:
    sys.exit(f"REFUSED: the READ row {read_run} is not in the exposure ledger")
if not any(gate.is_countersigned(row) for row in rows):
    sys.exit(f"REFUSED: the READ row {read_run} is not root countersigned")
print(f"READ row {read_run} countersigned")
PY
[ -f "$RUNDIR/$RUN.run-manifest.json" ] || { echo "REFUSED: no sealed run manifest under $RUNDIR"; exit 3; }
"$PY" -B scripts/analysis/stage3_rollout_score.py --mode supply-variants --run "$RUN" --attempt "$ATT" \
  --roster "$ROSTER" --analysis-root "$RUNDIR/supply-variants" --scorer-id "$SCORER" \
  --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" --stage all || { echo "COLUMN RENDER/SCORE FAILED"; exit 4; }
read_pass() {  # $1 pass name, $2 right column
  local dir="$OUT/$1"
  if [ -d "$dir" ] && [ -n "$(ls -A "$dir")" ]; then echo "REFUSED: $dir already holds files"; return 5; fi
  mkdir -p "$dir"
  "$PY" -B scripts/analysis/stage3_paired_read.py --per-scenario --stage all \
    --left-run "$RUN" --left-attempt "$ATT" --left-column a-base --left-label "the delivering column a-base" \
    --right-run "$RUN" --right-attempt "$ATT" --right-column "$2" --right-label "the column $2" \
    --scorer-id "$SCORER" --expected-split-role discovery --roster "$ROSTER" --cluster-key sample_id \
    --split-identity-hash "$SPLIT" --seed 20260928 --draws 10000 \
    --recipe-id slurp-stage3-wsv1-fold-a-column-analysis-v1 \
    --title "Cell W-SV-1 column read ($1: $2 vs a-base)" --analysis-root "$dir" \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR"
}
read_pass twin-null t-twin || { echo "TWIN-NULL READ REFUSED OR FAILED"; exit 6; }
read_pass knob b-exk30 || { echo "KNOB READ REFUSED OR FAILED"; exit 6; }
echo "W-SV-1 column reads written under $OUT (twin-null, knob)"
