#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Flip a BATCH of filler chunks to ready on master, in LOOP FORM, converging at ONE HEAD -- the batch's
# flight commit. Model-free (re-pin + prepare-supply + check; zero model, server, encoder, scorer contacts).
#
#   bash scripts/flights/filler/filler_flip.sh 1-6
#
# Root runs this AFTER, for every chunk of the batch:
#   1. minting its receipt: python scripts/flights/filler/filler_mint.py --chunks <spec> --countersign
#      (coordination/slurp-stage3-filler-fold-b-cKK-v1/root-admission-v1.json, decision id
#      slurp-stage3-filler-fold-b-cKK-admission-v1, eligible run ids = the chunk's arm + FIT, plus the
#      smoke + smoke FIT for chunk 1), and
#   2. committing the countersigned ledger rows on master (this script refuses a chunk whose rows still
#      say DRAFT, and refuses a dirty tree).
# Each cell goes through scripts/flights/batch/repin_loop_generic.sh with filler_repin_cell.sh (the
# per-cell environment for repin_cell_generic.sh): pass 1 always stops at the re-pin tool's own
# clean-tree refusal, the loop commits, pass 2 says satisfied (memory: flip scripts must be loop form).
# Chunk 1's four-row smoke is flipped before its arm. After the last cell the script re-runs
# core.flight.cli check for EVERY flipped cell at the final HEAD on the clean tree and writes the flight
# commit files the idle-filler queue reads ONLY if every one of them says ready:
#   /home/chao/filler-flight-commit-cKK.txt   (one per chunk; all hold the same HEAD)
#   /home/chao/filler-flight-commit.txt       (the batch's HEAD)
# --allow-output-change is never passed. Never edit scripts/flights/batch/ while a flight runs.
MAIN=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
DATA=$SAEA_DATA_ROOT
LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
PY=/home/chao/.venvs/speechrl/bin/python
SP=$MAIN/scripts/flights/batch
FD=$MAIN/scripts/flights/filler
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src
SPEC=${1:?usage: filler_flip.sh <chunk spec, e.g. 1-6>}
cd "$MAIN" || exit 1
CHUNKS=$($PY -B -c "import sys; sys.path.insert(0,'$FD'); import filler_family as ff; print(' '.join(str(k) for k in ff.parse_chunks('$SPEC')))") || exit 2
[ -z "$(git status --porcelain)" ] || { echo "REFUSED: the tree is dirty (untracked files count as dirt for core.flight.cli check)"; exit 3; }

# ---- preconditions, all chunks first: nothing is flipped unless every chunk of the batch is admissible
for K in $CHUNKS; do
  K2=$(printf %02d "$K")
  PKG=slurp-stage3-filler-fold-b-c$K2-v1
  RCPT=$DATA/coordination/$PKG/root-admission-v1.json
  [ -f "$RCPT" ] || { echo "REFUSED: c$K2 is not minted ($RCPT missing): run filler_mint.py --chunks $SPEC first"; exit 4; }
  $PY -c "import json,sys; d=json.load(open('$RCPT')); sys.exit(0 if d.get('status')=='decided' else 1)" \
    || { echo "REFUSED: c$K2 receipt status is not decided"; exit 4; }
  if grep -E "^\| [^|]* \| SAEA-SLURP-STAGE3-FILLER-FOLD-B-C$K2-" docs/exposure-ledger.md | grep -q "DRAFT"; then
    echo "REFUSED: c$K2 still has DRAFT ledger rows: countersign (filler_mint.py --countersign) and commit first"; exit 5
  fi
  STATE=$($PY -c "import json; print(json.load(open('configs/experiment/slurp-native-stage3-filler-fold-b-c$K2-v1.json'))['cells'][0]['readiness']['state'])")
  [ "$STATE" = "held" ] || { echo "REFUSED: c$K2 is already '$STATE' (a flipped chunk is re-flipped only by a root-diagnosed act)"; exit 6; }
done

# ---- the loops, one cell at a time, smoke before arm
for K in $CHUNKS; do
  K2=$(printf %02d "$K")
  RD=docs/readiness/2026-09-27-slurp-stage3-filler-fold-b-c$K2-v1
  KINDS="arm"; [ "$K" = "1" ] && KINDS="smoke arm"
  for KIND in $KINDS; do
    if [ "$KIND" = smoke ]; then CELL=slurp-native-stage3-filler-fold-b-c$K2-smoke-4-v1; PLAN=smoke-generation
    else CELL=slurp-native-stage3-filler-fold-b-c$K2-v1; PLAN=generation; fi
    cat > /home/chao/filler-c$K2-$KIND-commit.txt <<M
research: flip filler chunk c$K2 ($KIND) to ready (owner decision 162: the standing rollout filler family -- a sealed five-sample pool of the current best SLURP system, the locked PLAN plan plus the agreement term (decision 161), in cell ROLL-2's grouped-Solver form on TRAIN Fold B rows outside Fold A and every evaluation roster; DESCRIPTIVE, never an admission cell; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-stage3-filler-fold-b-c$K2-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
    export FILLER_CHUNK=$K FILLER_KIND=$KIND
    bash "$SP/repin_loop_generic.sh" "$FD/filler_repin_cell.sh" "$RD" "$CELL" "$PLAN" "/home/chao/filler-c$K2-$KIND-commit.txt" || { echo "FLIP STOPPED at c$K2 $KIND"; exit 7; }
  done
done

# ---- one HEAD: every flipped cell must say ready at it, on the clean tree
HEAD=$(git rev-parse HEAD)
[ -z "$(git status --porcelain)" ] || { echo "REFUSED: the tree is dirty after the loops"; exit 8; }
for K in $CHUNKS; do
  K2=$(printf %02d "$K")
  CELLS="slurp-native-stage3-filler-fold-b-c$K2-v1"; [ "$K" = "1" ] && CELLS="slurp-native-stage3-filler-fold-b-c01-smoke-4-v1 $CELLS"
  for CELL in $CELLS; do
    OUT=/home/chao/filler-final-check-$CELL.json
    $PY -B -m speech_aware_evidence_acquisition.core.flight.cli check --repo-root "$MAIN" --data-root "$DATA" \
      --runtime-root /home/chao --lock-path "$LOCK" --experiment "$CELL" --cell "$CELL" > "$OUT" 2> "$OUT.err" \
      || { echo "FINAL CHECK FAILED for $CELL at $HEAD"; tail -3 "$OUT.err" | cut -c1-300; exit 9; }
    R=$($PY -c "import json; print(json.load(open('$OUT')).get('scientific_readiness',{}).get('state'))")
    [ "$R" = "ready" ] || { echo "FINAL CHECK: $CELL is '$R' at $HEAD, not ready"; exit 9; }
    echo "final check $CELL ready at ${HEAD:0:8}"
  done
done
for K in $CHUNKS; do echo "$HEAD" > "/home/chao/filler-flight-commit-c$(printf %02d "$K").txt"; done
echo "$HEAD" > /home/chao/filler-flight-commit.txt
echo "flight commit $HEAD for chunks $CHUNKS"
