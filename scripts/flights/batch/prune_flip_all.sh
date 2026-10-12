#!/bin/bash
# Flip the two decision-85 pruning cells (P1 prune-reviewer1, P0 prune-review-off): smoke then arm each, via the generic re-pin loop.
SP=${SAEA_MAIN:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}/scripts/flights/batch
for NAME in prune-reviewer1 prune-review-off; do
  RD=docs/readiness/2026-09-22-slurp-$NAME-v1
  for KIND in smoke arm; do
    if [ "$KIND" = smoke ]; then CELL=slurp-native-$NAME-smoke-4-v1; PLAN=smoke-generation; ARMF=0; else CELL=slurp-native-$NAME-v1; PLAN=generation; ARMF=1; fi
    TAG=$NAME-$KIND
    cat > /home/chao/$TAG-commit.txt <<M
research: flip cell $CELL to ready (owner decisions 85 and 97; re-pinned by scripts/flights/repin_cell.py, decision receipt slurp-$NAME-admission-v1)

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>
M
    cat > /home/chao/$TAG-repin.sh <<M
#!/bin/bash
export RD=$RD CELL=$CELL PKG=slurp-$NAME-v1 PREREG=$RD-preregistration.md DEC_PATH=coordination/slurp-$NAME-v1/root-admission-v1.json DEC_ID=slurp-$NAME-admission-v1 TAG=$TAG ARM=$ARMF MSG=/home/chao/$TAG-commit.txt
exec bash $SP/repin_cell_generic.sh
M
    bash $SP/repin_loop_generic.sh /home/chao/$TAG-repin.sh $RD $CELL $PLAN /home/chao/$TAG-commit.txt || exit $?
  done
done
