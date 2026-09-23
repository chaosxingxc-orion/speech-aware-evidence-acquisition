#!/bin/bash
# Runbook for Stage-3 S3-5 (the delta store) and the CELL-1 registration fills
# (docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md sections S3-5 and S3-6;
# fill map docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1/fill-after-roll1-seal.json).
#
# ROOT RUNS THIS **AFTER** CELL ADV-1 (SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1) HAS SEALED, and after
# scripts/flights/batch/adv1_prepare.sh has filled the ADV-1 fragments (this runbook reads the
# disagreeing-row split identity out of the ADV-1 experiment fragment).
# It makes ZERO model, encoder, tokenizer, scorer, GPU and network contacts: every byte read is an
# already-sealed local file and everything written is pure Python curation over that text. It does
# NOT flip readiness, mint a decision receipt or touch docs/exposure-ledger.md.
#
# What it does, in order:
#   A  preconditions: the sealed ADV-1 advantage outputs, S3-3's pairs.json, and the two root
#      S3-5 preparations the release registration pins (construction scope, permitted roster)
#   B  curate (no release): scripts/build_slurp_stage3_delta_store.py writes the append-only
#      authored-deltas document and prints its digest
#   C  twin: scripts/build_slurp_stage3_delta_twin.py derangement of associated_facet_ids
#   D  materialise both release registrations from their committed templates with the real digests
#   E  release the generation store (the curator's own --release path, which also writes the
#      release-pins document) and the twin store (the driver's prepare-semantic-knowledge)
#   F  print the CELL-1 fill values and apply them to the five CELL-1 fragments
#
# Environment overrides: REPO, SPEECHRL_DATA_DIR, PY, ADV1_RUN, ADV1_OUTPUTS, SCORE_RUN,
# DELTA_ITERATION, DELTA_TWIN_SEED, DELTA_PREDECESSOR.
# DELTAS_DRY=1 (the default) runs A read-only and prints every mutating command line;
# DELTAS_DRY=0 runs them. Commit the five touched fragments afterwards, then re-pin.
set -u
REPO=${REPO:-/home/chao/saea-worktrees/fable-s3adv}
DATA=${SPEECHRL_DATA_DIR:-/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data}
PY=${PY:-/home/chao/.venvs/speechrl/bin/python}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
DRY=${DELTAS_DRY:-1}

ADV1_RUN=${ADV1_RUN:-SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1}
SCORE_RUN=${SCORE_RUN:-SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1}
DELTA_ITERATION=${DELTA_ITERATION:-1}
# The twin seed is a documented constant, not a tuned one: it names one Sattolo cycle and is
# recorded so the derangement is reproducible byte for byte.
DELTA_TWIN_SEED=${DELTA_TWIN_SEED:-20260922}
DELTA_PREDECESSOR=${DELTA_PREDECESSOR:-none}

PREPARED=$DATA/prepared/SAEA-SLURP-STAGE3-DELTAS-V1
# Rendered from the sealed ADV-1 run's custodied outputs at the ADV-1 seal (one JSON object per
# line: {"sample_id", "response_text", "disagreement"}); it is S3-4's own deliverable, not this
# runbook's, and it never enters Git.
ADV1_OUTPUTS=${ADV1_OUTPUTS:-$PREPARED/advantage-outputs-v1.jsonl}
PAIRS=$DATA/analysis/$SCORE_RUN/pairs.json
AUTHORED=$PREPARED/authored-stage3-deltas-v1.json
TWIN_AUTHORED=$PREPARED/authored-stage3-deltas-twin-v1.json
SCOPE=$PREPARED/outer-construction-roster.json
PERMITTED=$PREPARED/permitted-roster.json
COORD=$DATA/coordination/slurp-stage3-delta-cell-r01-v1
REG_TEMPLATE=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-v1-release-registration.template.json
TWIN_REG_TEMPLATE=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-twin-v1-release-registration.template.json
REG=$COORD/stage3-deltas-v1-release-registration.json
TWIN_REG=$COORD/stage3-deltas-twin-v1-release-registration.json
RELEASE_PINS=$COORD/stage3-deltas-v1-release-pins.json
VALUES=$COORD/cell1-fill-values.json
HELPERS=scripts/flights/batch/adv1_to_deltas_steps.py
ADV1_EXPERIMENT=configs/experiment/slurp-native-stage3-advantage-r01-v1.json
CELL_EXPERIMENT=configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json
CELL_BASELINES="configs/baseline/slurp-native-stage3-delta-cell-baseline-v1.json configs/baseline/slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json configs/baseline/slurp-native-stage3-delta-cell-twin-baseline-v1.json configs/baseline/slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1.json"

cd "$REPO" || { echo "no checkout at $REPO"; exit 1; }
echo "== adv1_to_deltas $(date -u +%FT%TZ) REPO=$REPO HEAD=$(git rev-parse --short HEAD) dry=$DRY"

# ---------------------------------------------------------------- A: preconditions
SPLIT=$($PY -B -c "import json,sys;print(json.load(open(sys.argv[1]))['population']['split_identity_hash'])" "$ADV1_EXPERIMENT")
case "$SPLIT" in
  PENDING_*|"") echo "A  ADV-1 split identity is still $SPLIT: run scripts/flights/batch/adv1_prepare.sh first"; exit 2;;
esac
echo "A  ADV-1 population split identity $SPLIT"
for F in "$ADV1_OUTPUTS" "$PAIRS" "$SCOPE" "$PERMITTED"; do
  [ -f "$F" ] || { echo "A  MISSING $F"; MISSING=1; }
done
if [ "${MISSING:-0}" = "1" ]; then
  echo "A  the two prepared/ roster documents are root's own S3-5 preparations (the slot-contracts"
  echo "   precedent prepared/SAEA-SLURP-SEMANTIC-AUTHORING-PREPARE-V1/outer-construction-roster.json);"
  echo "   the advantage outputs are rendered at the ADV-1 seal. Nothing here creates them."
  [ "$DRY" = "1" ] || exit 2
fi

run() {  # run, or print, one mutating command line
  if [ "$DRY" = "1" ]; then echo "   (dry) would run: $*"; else "$@" || { echo "FAILED: $*"; exit 3; }; fi
}

# ---------------------------------------------------------------- B: curate (no release)
echo "B  curate iteration $DELTA_ITERATION predecessor $DELTA_PREDECESSOR"
run "$PY" -B scripts/build_slurp_stage3_delta_store.py \
    --advantage-outputs "$ADV1_OUTPUTS" --pairs "$PAIRS" --repo-root "$REPO" \
    --predecessor "$DELTA_PREDECESSOR" --iteration "$DELTA_ITERATION" \
    --run-id "$ADV1_RUN" --out-authored "$AUTHORED"

# ---------------------------------------------------------------- C: the derangement twin
echo "C  twin seed $DELTA_TWIN_SEED"
run "$PY" -B scripts/build_slurp_stage3_delta_twin.py \
    --authored "$AUTHORED" --seed "$DELTA_TWIN_SEED" --out "$TWIN_AUTHORED"

# ---------------------------------------------------------------- D: runnable registrations
echo "D  materialise the two release registrations"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" registration \
    --template "$REG_TEMPLATE" --out "$REG" --source-split-identity-hash "$SPLIT"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" registration \
    --template "$TWIN_REG_TEMPLATE" --out "$TWIN_REG" --source-split-identity-hash "$SPLIT"

# ---------------------------------------------------------------- E: release both stores
# The generation store goes out through the curator's own --release path (it also writes the
# release-pins document the spec asks for). Re-running the curator here is deliberate and safe:
# curation is deterministic (survivors sorted by value_id), so --out-authored is rewritten byte
# for byte and the digest step D pinned still matches -- and if it ever did not, the preparer
# fails closed on the authored_source pin rather than releasing a different store.
echo "E  release"
run "$PY" -B scripts/build_slurp_stage3_delta_store.py \
    --advantage-outputs "$ADV1_OUTPUTS" --pairs "$PAIRS" --repo-root "$REPO" \
    --predecessor "$DELTA_PREDECESSOR" --iteration "$DELTA_ITERATION" \
    --run-id "$ADV1_RUN" --out-authored "$AUTHORED" \
    --release "$REG" --data-root "$DATA" --release-pins "$RELEASE_PINS"
# The twin's authored document is the derangement, not a curation, so it is released directly.
run "$PY" -B -m speech_aware_evidence_acquisition.core.driver.cli prepare-semantic-knowledge \
    --registration "$TWIN_REG" --repo-root "$REPO" --data-root "$DATA"

# ---------------------------------------------------------------- F: the CELL-1 fill values
echo "F  CELL-1 fill values"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" cell1-values --values-out "$VALUES"
BY="S3-5 release of knowledge/slurp/semantic/stage3-deltas-v1/ (iteration $DELTA_ITERATION, predecessor $DELTA_PREDECESSOR, curated from the sealed $ADV1_RUN advantage outputs) and its derangement twin stage3-deltas-twin-v1 (seed $DELTA_TWIN_SEED); release pins $RELEASE_PINS"
# shellcheck disable=SC2086
run "$PY" -B scripts/flights/batch/roll1_fill_placeholders.py \
    --fragments $CELL_EXPERIMENT $CELL_BASELINES \
    --values "$VALUES" --by "$BY" --occurrence-policy any --date "$(date -u +%F)"

echo "F  commit: git add $CELL_EXPERIMENT $CELL_BASELINES && git commit -F <message file>"
echo "== adv1_to_deltas done $(date -u +%FT%TZ) dry=$DRY"
