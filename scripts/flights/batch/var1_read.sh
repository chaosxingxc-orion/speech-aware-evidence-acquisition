#!/bin/bash
# Usage: var1_read.sh own-null
#        var1_read.sh variant <exk10|exk30|exdiv|perk16c5|planr>
#
# The VAR-1 construction-variant read (owner decision 58: reads are executed by script).
#
# ORDER MATTERS AND IS PART OF THE REGISTRATION: run `own-null` FIRST. Every VAR-1 variant is read
# at the margins h_SLU and h_intent that VAR1-PLAN against VAR1-PLANR produces on THIS roster. The
# TRAIN Fold A numbers (h_SLU 1.2485 / h_intent 0.9943) and the DEV-2000-ADDED numbers (1.2525 /
# 1.1520) are CONTEXT ONLY and are not this family's bar: R01C is a different roster, of a
# different size (625 versus 1,080 and 1,000), with a different scenario allocation. The variant
# contrasts are not read until the own-null margin table has sealed, and the margins are never
# adjusted afterwards.
#
# DRIVER: scripts/analysis/slurp_paired_roster_read.py -- the reusable roster-generic paired read.
# It is pointed at the TRAIN gold scorer sibling (slurp-slu-official-train, the scorer both VAR-1
# baselines declare) and at the R01C roster receipt, and it clusters on utterance_id. R01C carries
# 625 DISTINCT utterance ids and no per-item speaker field, so utterance clustering is exactly the
# per-row bootstrap here and whole-speaker clustering is not derivable from the receipt; that is
# stated in the verdict rather than worked around.
#
# WHAT THIS DRIVER DOES NOT PRODUCE, registered as an OPEN ITEM rather than silently omitted:
# the per-scenario table, the entity FP/FN decomposition by slot TYPE, the Perception coverage per
# variant and the group-relative advantage per runtime-observable state. R01C's roster receipt DOES
# carry a per-item stratum, so a GOLD per-scenario table is derivable here offline -- unlike on
# DEV-2000-ADDED -- but slurp_paired_roster_read.py hard-codes "per-scenario NOT AVAILABLE" for its
# own roster and takes no --stratum-key. Teaching it that flag, or writing the VAR-1 variant
# driver, is a separate engineering change with its own tests and its own review; it is named in
# analysis-recipe-v1.json section `open_items` and must land BEFORE the variant reads, never
# beside a live flight.
#
# Model-free: zero model / tokenizer / encoder / server contacts; scorer contacts only through the
# sealed per-sample scores. Registered as SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1 and
# SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1 (model-free-check rows).
WHICH=$1
COMP_RUN=SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1
COMP_ATTEMPT=attempt-slurp-native-stage3-var1-plan-r01c-v1-generation
LEFT_LABEL="VAR1-PLAN (the locked v2.0 plan on R01C)"
case $WHICH in
  own-null)
    RIGHT_RUN=SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1
    RIGHT_ATTEMPT=attempt-slurp-native-stage3-var1-planr-r01c-v1-generation
    RIGHT_LABEL="VAR1-PLANR (the request-identical replicate)"
    ROOT_ID=SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1
    RECIPE=slurp-stage3-var1-own-null-v1
    TITLE="R01C own null: the locked plan against its request-identical replicate (the margin table every VAR-1 variant is read at)"
    ;;
  variant)
    case $2 in
      exk10)    STEM=ex-k10-r01c;    RUNSTEM=EX-K10-R01C;    DESC="exemplars k=10 (coverage 10/10/10)";;
      exk30)    STEM=ex-k30-r01c;    RUNSTEM=EX-K30-R01C;    DESC="exemplars k=30 (coverage 30/30/30)";;
      exdiv)    STEM=ex-div-r01c;    RUNSTEM=EX-DIV-R01C;    DESC="exemplars k=20, coverage c=4 per intent target";;
      perk16c5) STEM=per-k16c5-r01c; RUNSTEM=PER-K16C5-R01C; DESC="Perception cards k=16 (coverage 1/16/16), candidate bound 5";;
      planr)    STEM=planr-r01c;     RUNSTEM=PLANR-R01C;     DESC="the request-identical replicate, read as a variant (the A/A control row of the variant table)";;
      *) echo "usage: var1_read.sh variant <exk10|exk30|exdiv|perk16c5|planr>"; exit 2;;
    esac
    RIGHT_RUN=SAEA-SLURP-STAGE3-VAR1-$RUNSTEM-V1
    RIGHT_ATTEMPT=attempt-slurp-native-stage3-var1-$STEM-v1-generation
    RIGHT_LABEL="VAR1-$RUNSTEM ($DESC)"
    ROOT_ID=SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1-$RUNSTEM
    RECIPE=slurp-stage3-var1-variant-read-v1-$(echo $RUNSTEM | tr 'A-Z' 'a-z')
    TITLE="VAR-1 construction variant $RUNSTEM against VAR1-PLAN on R01C, at the roster's own null"
    ;;
  *) echo "usage: var1_read.sh own-null | variant <cell>"; exit 2;;
esac
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data
PKG=$MAIN/docs/readiness/2026-09-24-slurp-stage3-var1-v1
ROOT=$SPEECHRL_DATA_DIR/analysis/$ROOT_ID
mkdir -p "$ROOT" \
  && cp "$MAIN/scripts/analysis/slurp_paired_roster_read.py" "$ROOT/slurp_paired_roster_read.py" \
  && cp "$PKG/registered-facts-v1.json" "$ROOT/registered-var1.json" \
  && cd "$ROOT" || exit 1
sha256sum slurp_paired_roster_read.py | cut -c1-16
$PY slurp_paired_roster_read.py --stage all \
  --left-run $COMP_RUN --left-attempt $COMP_ATTEMPT --left-label "$LEFT_LABEL" \
  --right-run $RIGHT_RUN --right-attempt $RIGHT_ATTEMPT --right-label "$RIGHT_LABEL" \
  --scorer-id slurp-slu-official-train \
  --roster docs/receipts/rosters/slurp-stage3-construction-r01c.json \
  --cluster-key utterance_id \
  --split-identity-hash f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515 \
  --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
  --seed 20260915 --draws 10000 \
  --recipe-id $RECIPE --title "$TITLE" \
  --analysis-root "$ROOT" > "$ROOT/stage-all.log" 2>&1 \
  || { echo "PAIRED READ FAILED"; tail -5 "$ROOT/stage-all.log" | cut -c1-300; exit 2; }
echo "VAR-1 $WHICH ${2:-} read done $(date -u +%T)"; ls "$ROOT"
