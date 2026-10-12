#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Usage: var1_read.sh own-null
#        var1_read.sh variant <exk10|exk30|exdiv|perk16c5|planr>   -- one cell's pooled paired read
#        var1_read.sh variant                                      -- all five, then the FAMILY read
#
# The VAR-1 construction-variant read (owner decision 58: reads are executed by script).
#
# ORDER MATTERS AND IS PART OF THE REGISTRATION: run `own-null` FIRST. Every VAR-1 variant is read
# at the margins h_SLU and h_intent that VAR1-PLAN against VAR1-PLANR produces on THIS roster. The
# TRAIN Fold A numbers (h_SLU 1.2485 / h_intent 0.9943), the DEV-2000-ADDED numbers (1.2525 /
# 1.1520) and the WITHIN-flight ROLL-AA numbers (0.735 / 0.000) are CONTEXT ONLY and are not this
# family's bar: R01C is a different roster, of a different size (625 versus 1,080, 1,000 and 200),
# with a different scenario allocation. The variant contrasts are not read until the own-null
# margin table has sealed, and the margins are never adjusted afterwards. The family driver
# enforces that order itself -- it refuses to compute a variant table unless its own
# `own-null.json` is already on disk, and it binds the variant artefact to that artefact's content
# hash.
#
# TWO DRIVERS, BOTH MODEL-FREE:
#
#   1. scripts/analysis/slurp_paired_roster_read.py -- the reusable roster-generic PAIRED read, one
#      arm pair at a time: the pooled paired contrast, the per-channel table, the structural counts
#      and the efficiency block. Pointed at the TRAIN gold scorer sibling
#      (slurp-slu-official-train, the scorer both VAR-1 baselines declare) and at the R01C roster
#      receipt, clustering on utterance_id. R01C carries 625 DISTINCT utterance ids and no per-item
#      speaker field, so utterance clustering is exactly the per-row bootstrap here and
#      whole-speaker clustering is not derivable from the receipt; that is stated in the verdict
#      rather than worked around.
#
#   2. scripts/analysis/slurp_var1_variant_read.py -- the VAR-1 FAMILY read, all six sealed cells at
#      once. This is the committed resolution of registered open items VAR1-OPEN-1 and VAR1-OPEN-2:
#      the R01C own-null margin table, the per-variant table at that margin, the GOLD per-scenario
#      table in both weightings (derivable here because the R01C receipt carries a per-item
#      stratum, unlike DEV-2000-ADDED), entity FP/FN by slot TYPE, the Perception candidate
#      coverage, the group-relative advantage per runtime-observable state with its policy table,
#      and the cost/frontier table. It refuses to run if any cell's manifest is not COMPLETED, if
#      any hash the registration pins disagrees with the sealed bytes, or if the six runs do not
#      cover the same 625 row ids.
#
# VAR1-OPEN-3 is NOT resolved here: the prompt-fit bound of VAR1-EX-K30 and VAR1-PER-K16C5 is not
# measured in tokens by either driver, because neither contacts a tokenizer.
#
# Model-free: zero model / tokenizer / encoder / server contacts; scorer contacts only through the
# sealed per-sample scores. Registered as SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1 and
# SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1 (model-free-check rows).
WHICH=${1:-}
CELL=${2:-}
PY=/home/chao/.venvs/speechrl/bin/python
MAIN=${SAEA_REPO_ROOT:-/mnt/d/chao_workspace/exploring-l4-intelligence/studies/speech-aware-evidence-acquisition}
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$MAIN/src SPEECHRL_DATA_DIR=$SAEA_DATA_ROOT
PKG=$MAIN/docs/readiness/2026-09-24-slurp-stage3-var1-v1
PKG_RELPATH=docs/readiness/2026-09-24-slurp-stage3-var1-v1
LOCK=/mnt/d/chao_workspace/exploring-l4-intelligence/docs/datasets.lock.json
COMP_RUN=SAEA-SLURP-STAGE3-VAR1-PLAN-R01C-V1
COMP_ATTEMPT=attempt-slurp-native-stage3-var1-plan-r01c-v1-generation
LEFT_LABEL="VAR1-PLAN (the locked v2.0 plan on R01C)"
FAMILY_ROOT=$SPEECHRL_DATA_DIR/analysis/SLURP-VAR1-VARIANT-READ-V1${SAEA_ANALYSIS_SUFFIX:-}

# One arm pair through the roster-generic paired driver.
paired_read() {
  RIGHT_RUN=$1; RIGHT_ATTEMPT=$2; RIGHT_LABEL=$3; ROOT_ID=$4; RECIPE=$5; TITLE=$6
  ROOT=$SPEECHRL_DATA_DIR/analysis/$ROOT_ID${SAEA_ANALYSIS_SUFFIX:-}
  mkdir -p "$ROOT" \
    && cp "$MAIN/scripts/analysis/slurp_paired_roster_read.py" "$ROOT/slurp_paired_roster_read.py" \
    && cp "$PKG/registered-facts-v1.json" "$ROOT/registered-var1.json" \
    && cd "$ROOT" || return 1
  sha256sum slurp_paired_roster_read.py | cut -c1-16
  $PY slurp_paired_roster_read.py --stage all \
    --left-run $COMP_RUN --left-attempt $COMP_ATTEMPT --left-label "$LEFT_LABEL" \
    --right-run "$RIGHT_RUN" --right-attempt "$RIGHT_ATTEMPT" --right-label "$RIGHT_LABEL" \
    --scorer-id slurp-slu-official-train --expected-split-role discovery \
    --roster docs/receipts/rosters/slurp-stage3-construction-r01c.json \
    --cluster-key utterance_id \
    --split-identity-hash f56bc386776421aec2d8001d8697611b01c9b0562885a462759b15531e2f4515 \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
    --seed 20260915 --draws 10000 \
    --recipe-id "$RECIPE" --title "$TITLE" \
    --analysis-root "$ROOT" > "$ROOT/stage-all.log" 2>&1 \
    || { echo "PAIRED READ FAILED ($RIGHT_RUN)"; tail -5 "$ROOT/stage-all.log" | cut -c1-300; return 2; }
  echo "paired read done $RIGHT_RUN $(date -u +%T)"
}

# Resolve one variant cell's sealed identity.
resolve_cell() {
  case $1 in
    exk10)    STEM=ex-k10-r01c;    RUNSTEM=EX-K10-R01C;    DESC="exemplars k=10 (coverage 10/10/10)";;
    exk30)    STEM=ex-k30-r01c;    RUNSTEM=EX-K30-R01C;    DESC="exemplars k=30 (coverage 30/30/30)";;
    exdiv)    STEM=ex-div-r01c;    RUNSTEM=EX-DIV-R01C;    DESC="exemplars k=20, coverage c=4 per intent target";;
    perk16c5) STEM=per-k16c5-r01c; RUNSTEM=PER-K16C5-R01C; DESC="Perception cards k=16 (coverage 1/16/16), candidate bound 5";;
    planr)    STEM=planr-r01c;     RUNSTEM=PLANR-R01C;     DESC="the request-identical replicate, read as a variant (the A/A control row of the variant table)";;
    *) echo "usage: var1_read.sh variant [exk10|exk30|exdiv|perk16c5|planr]"; return 2;;
  esac
}

# The VAR-1 FAMILY read: open items VAR1-OPEN-1 and VAR1-OPEN-2, all six sealed cells at once.
family_read() {
  mkdir -p "$FAMILY_ROOT" || return 1
  # Freeze the driver bytes beside the output. The three files are a RECORD, not what is executed:
  # the family driver runs in place from the repo so its sibling imports resolve, and it records
  # its own sha256 plus the two reused loaders' sha256 inside every artefact it writes.
  for name in slurp_var1_variant_read.py slurp_paired_roster_read.py slurp_plan_bad_case_bank.py; do
    cp "$MAIN/scripts/analysis/$name" "$FAMILY_ROOT/$name" || return 1
    sha256sum "$FAMILY_ROOT/$name" | cut -c1-16
  done
  $PY "$MAIN/scripts/analysis/slurp_var1_variant_read.py" \
    --repo-root "$MAIN" --data-root "$SPEECHRL_DATA_DIR" \
    --out-root "$FAMILY_ROOT" --package "$PKG_RELPATH" --lock "$LOCK" \
    --seed 20260915 --draws 10000 --min-state-rows 60 \
    > "$FAMILY_ROOT/family-read.log" 2>&1 \
    || { echo "FAMILY READ FAILED"; tail -10 "$FAMILY_ROOT/family-read.log" | cut -c1-300; return 2; }
  tail -2 "$FAMILY_ROOT/family-read.log"
  echo "VAR-1 family read done $(date -u +%T)"; ls "$FAMILY_ROOT"
}

case $WHICH in
  own-null)
    paired_read \
      SAEA-SLURP-STAGE3-VAR1-PLANR-R01C-V1 \
      attempt-slurp-native-stage3-var1-planr-r01c-v1-generation \
      "VAR1-PLANR (the request-identical replicate)" \
      SAEA-SLURP-STAGE3-VAR1-OWN-NULL-V1 \
      slurp-stage3-var1-own-null-v1 \
      "R01C own null: the locked plan against its request-identical replicate (the margin table every VAR-1 variant is read at)" \
      || exit 2
    echo "VAR-1 own-null read done $(date -u +%T)"
    ;;
  variant)
    if [ -z "$CELL" ]; then
      # Every cell's pooled paired read, then the family tables. This is the registered order of
      # step 6: the pooled paired contrast first, the VAR-1 driver's tables after it.
      for cell in planr exk10 exk30 exdiv perk16c5; do
        resolve_cell $cell || exit 2
        paired_read \
          SAEA-SLURP-STAGE3-VAR1-$RUNSTEM-V1 \
          attempt-slurp-native-stage3-var1-$STEM-v1-generation \
          "VAR1-$RUNSTEM ($DESC)" \
          SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1-$RUNSTEM \
          "slurp-stage3-var1-variant-read-v1-$(echo $RUNSTEM | tr 'A-Z' 'a-z')" \
          "VAR-1 construction variant $RUNSTEM against VAR1-PLAN on R01C, at the roster's own null" \
          || exit 2
      done
      family_read || exit 2
    else
      resolve_cell "$CELL" || exit 2
      paired_read \
        SAEA-SLURP-STAGE3-VAR1-$RUNSTEM-V1 \
        attempt-slurp-native-stage3-var1-$STEM-v1-generation \
        "VAR1-$RUNSTEM ($DESC)" \
        SAEA-SLURP-STAGE3-VAR1-VARIANT-READ-V1-$RUNSTEM \
        "slurp-stage3-var1-variant-read-v1-$(echo $RUNSTEM | tr 'A-Z' 'a-z')" \
        "VAR-1 construction variant $RUNSTEM against VAR1-PLAN on R01C, at the roster's own null" \
        || exit 2
      echo "VAR-1 variant $CELL pooled paired read done $(date -u +%T)"
      echo "the family tables (per-scenario, entity by slot TYPE, Perception coverage, advantage,"
      echo "policy table, cost) come from: var1_read.sh variant   -- with no cell argument"
    fi
    ;;
  *) echo "usage: var1_read.sh own-null | variant [cell]"; exit 2;;
esac
