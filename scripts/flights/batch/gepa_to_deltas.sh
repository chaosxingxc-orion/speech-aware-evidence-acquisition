#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
# Runbook: the Stage-3 GEPA arm's CURATION and RELEASE (design note
# docs/superpowers/specs/2026-09-24-slurp-stage3-gepa-arm-design.md sections 3-4; owner decisions
# 83 and 101).
#
# ROOT RUNS THIS **AFTER** CELL GEPA-R01 (SAEA-SLURP-STAGE3-GEPA-R01-V1) HAS SEALED.
# It makes ZERO model, encoder, tokenizer, scorer, GPU and network contacts: every byte read is an
# already-sealed local file and everything written is pure Python curation over that text. It does
# NOT flip readiness, mint a decision receipt or touch docs/exposure-ledger.md.
#
# What it does, in order:
#   A  preconditions: the sealed GEPA outputs, the prepared groups artifact, the released v1r
#      authored document, the construction gold intents, the intent vocabulary and the transcripts
#   R  retention: scripts/build_slurp_stage3_delta_retention.py over the CELL-1 read, written to
#      THIS line's own prepared directory. It never reads or writes the stage3-deltas-v2
#      artifacts; its retired_value_ids are EXPECTED to equal that line's, which is a cross-check
#      and not a dependency, and the counts of both are printed side by side when the v2 document
#      is present.
#   B  render:  scripts/flights/batch/gepa_render_proposal_outputs.py -> the proposal outputs, the
#      construction scope and the PERMITTED roster, both of them COMMITTED receipts copied byte
#      for byte
#
# THREE POPULATIONS, AND THEY ARE NOT THE SAME ROWS.
#   FLIGHT population = the CARRIERS, docs/receipts/rosters/slurp-stage3-gepa-r01c-carriers-v1.json
#     (68 rows, split identity 86da42e2...): one contact per carrier row, which is what the
#     experiment fragment's population block pins and what the exposure gate reads. Printed below
#     as FLIGHT_SPLIT and never passed to the store.
#   CONTACT MATERIAL population = the GROUP ROWS, docs/receipts/rosters/slurp-stage3-gepa-r01c-
#     groups-v1.json (173 rows, split identity 0d020435...): the rows whose rollout trajectories
#     and construction gold were rendered into a contact, i.e. exactly what the GEPA contact saw.
#     Committed as the record of that and printed below as GROUPS_SPLIT. It is a SUBSET of the
#     permitted roster -- which the renderer proves -- and it is not itself the store's roster.
#   STORE PERMITTED ROSTER = the ADV-1 DISAGREEING receipt, docs/receipts/rosters/slurp-stage3-
#     advantage-r01c-disagreeing-v1.json (225 rows, split identity 7c603857...), which is exactly
#     what stage3-deltas-v1r and stage3-deltas-v2 pin, so this store shares its SOURCE identity
#     with the CELL-1 / CELL-2 stores. The store is append-only over v1r (decision 83): it retains
#     200 iteration-1 rows, and 42 of those cite 28 R01C rows outside the 173 group rows, so the
#     group union cannot be the permitted roster without discarding retained content.
#     core.semantic_knowledge_preparation verifies the registration's permitted_roster as a
#     committed roster_role='construction' receipt AND requires permitted.split_identity_hash ==
#     registration.source_split_identity_hash, so $SPLIT below is the PERMITTED-ROSTER identity.
#     The first release attempt (2026-09-24) passed the carriers identity against a hand-made
#     permitted roster carrying no split_identity_hash at all and was refused twice over, by
#     core.roster.RosterError and then by 'permitted_roster is not a verified roster'; the second
#     passed the group union and was refused by rails.semantic_knowledge_build with 'authored
#     delta source_sample_ids must be a subset of the permitted construction roster'.
#   C  curate:  scripts/build_slurp_stage3_gepa_delta_rows.py -- the ADV-1 curator's own rules
#      (append-only, exact-normalised + Jaccard >= 0.8 dedup, provenance merge, source-intent
#      facets, six-token containment) over group-keyed candidate rows; predecessor = the released
#      v1r authored document, retirement = R's document
#   T  twin:    scripts/build_slurp_stage3_delta_twin.py (unchanged) + scripts/build_slurp_stage3_
#      delta_source.py to wrap it
#   D  materialise both release registrations from their committed templates with the real digests
#   E  release both stores
#   R2 the model-free supply-reach expectation of both released stores
#
# GEPA_DELTAS_DRY=1 (the default) runs A read-only and prints every mutating command line;
# GEPA_DELTAS_DRY=0 runs them. Commit the two materialised release registrations afterwards.
set -u
REPO=${REPO:-/home/chao/saea-worktrees/fable-gepa}
DATA=$SAEA_DATA_ROOT
PY=${PY:-/home/chao/.venvs/speechrl/bin/python}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
DRY=${GEPA_DELTAS_DRY:-1}

GEPA_RUN=${GEPA_RUN:-SAEA-SLURP-STAGE3-GEPA-R01-V1}
GEPA_ATTEMPT=${GEPA_ATTEMPT:-attempt-slurp-native-stage3-gepa-r01-v1-generation}
TAG=${GEPA_VERSION_TAG:-gepa-v1}
TWIN_TAG=${GEPA_TWIN_VERSION_TAG:-gepa-twin-v1}
ITERATION=${GEPA_ITERATION:-2}
TWIN_SEED=${GEPA_TWIN_SEED:-20260924}

PREPARED=$DATA/prepared/SAEA-SLURP-STAGE3-DELTAS-GEPA-V1
ADV_PREPARED=$DATA/prepared/SAEA-SLURP-STAGE3-DELTAS-V1
GEPA_GROUPS=$PREPARED/gepa-groups-v1.json  # named GEPA_GROUPS because bash's read-only GROUPS array expands to the caller's group id (the first real run printed 'A  MISSING 1000')
OUTPUTS=$PREPARED/gepa-proposal-outputs-v1.jsonl
PREDECESSOR=${GEPA_PREDECESSOR:-$ADV_PREPARED/authored-stage3-deltas-v1r.json}
TRANSCRIPTS=${GEPA_TRANSCRIPTS:-$ADV_PREPARED/construction-transcripts.jsonl}
GOLD=${GEPA_GOLD_INTENTS:-$DATA/coordination/slurp-stage3-advantage-r01-v1/r01c-gold-intents.json}
CATALOG=${GEPA_INTENT_CATALOG:-$DATA/prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json}
RETENTION=$PREPARED/retention-gepa-v1.json
RETENTION_MD=$PREPARED/retention-gepa-v1.md
AUTHORED=$PREPARED/authored-stage3-deltas-$TAG.json
SOURCE=$PREPARED/source-stage3-deltas-$TAG.json
TWIN_AUTHORED=$PREPARED/authored-stage3-deltas-$TWIN_TAG.json
TWIN_SOURCE=$PREPARED/source-stage3-deltas-$TWIN_TAG.json
COORD=$DATA/coordination/slurp-stage3-delta-cell-gepa-r01-v1
RELEASE_PINS=$COORD/stage3-deltas-$TAG-release-pins.json
RD=docs/readiness/2026-09-24-slurp-stage3-gepa-r01-v1
REG_TEMPLATE=$RD/stage3-deltas-gepa-v1-release-registration.template.json
TWIN_REG_TEMPLATE=$RD/stage3-deltas-gepa-twin-v1-release-registration.template.json
REG=$REPO/$RD/stage3-deltas-$TAG-release-registration.json
TWIN_REG=$REPO/$RD/stage3-deltas-$TWIN_TAG-release-registration.json
HELPERS=scripts/flights/batch/adv1_to_deltas_steps.py
mkdir -p "$COORD"

cd "$REPO" || { echo "no checkout at $REPO"; exit 1; }
echo "== gepa_to_deltas $(date -u +%FT%TZ) REPO=$REPO HEAD=$(git rev-parse --short HEAD) dry=$DRY tag=$TAG"

run() { if [ "$DRY" = "1" ]; then echo "   (dry) would run: $*"; else "$@" || { echo "FAILED: $*"; exit 3; }; fi; }

# ---------------------------------------------------------------- A: preconditions
GROUPS_ROSTER=${GEPA_GROUPS_ROSTER:-docs/receipts/rosters/slurp-stage3-gepa-r01c-groups-v1.json}
PERMITTED_ROSTER=${GEPA_PERMITTED_ROSTER:-docs/receipts/rosters/slurp-stage3-advantage-r01c-disagreeing-v1.json}
# The FLIGHT population identity, as the experiment fragment pins the carriers: printed for the
# record, never passed to the store.
FLIGHT_SPLIT=$($PY -B -c "import json,sys;print(json.load(open(sys.argv[1]))['population']['split_identity_hash'])" \
        configs/experiment/slurp-native-stage3-gepa-r01-v1.json)
# The CONTACT MATERIAL identity: the committed GROUP-ROWS receipt. Printed for the record.
GROUPS_SPLIT=$($PY -B -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['split_identity_hash'])" \
        "$GROUPS_ROSTER")
# The STORE identity: the committed permitted roster, the ADV-1 disagreeing receipt v1r/v2 pin.
SPLIT=$($PY -B -c "import json,sys;d=json.load(open(sys.argv[1]));print(d['split_identity_hash'])" \
        "$PERMITTED_ROSTER")
echo "A  GEPA FLIGHT population (carriers) split identity $FLIGHT_SPLIT"
echo "A  GEPA CONTACT MATERIAL (group rows) split identity $GROUPS_SPLIT from $GROUPS_ROSTER"
echo "A  GEPA STORE permitted roster split identity $SPLIT from $PERMITTED_ROSTER"
MISSING=0
for F in "$GEPA_GROUPS" "$PREDECESSOR" "$GOLD" "$CATALOG" "$GROUPS_ROSTER" "$PERMITTED_ROSTER"; do
  [ -f "$F" ] || { echo "A  MISSING $F"; MISSING=1; }
done
[ -f "$TRANSCRIPTS" ] || echo "A  NO transcripts at $TRANSCRIPTS: the six-token containment rule will be DISABLED and the report will say so. Prepare them before releasing."
if [ "$MISSING" = "1" ] && [ "$DRY" != "1" ]; then exit 2; fi

# ---------------------------------------------------------------- R: decision-83 retention
echo "R  decision-83 retention over the CELL-1 read -> $RETENTION"
echo "   (the flags are CELL-1's own; see scripts/build_slurp_stage3_delta_retention.py --help)"
CELL1_ROOT=$DATA/analysis/SAEA-SLURP-STAGE3-DELTA-CELL-R01-PAIRED-ANALYSIS-V1
OWN_NULL_ROOT=$DATA/analysis/SAEA-SLURP-DEFAULT-PLAN-LOCK-REPLICATE-PAIRED-ANALYSIS-V1
# 2026-09-24: the retention CLI (fable/s35v2) requires the CELL-1 read inputs explicitly; these are the same four inputs
# the v2 retention used (prepared/SAEA-SLURP-STAGE3-DELTAS-V1/retention-v2.json "inputs"), so the GEPA line inherits the
# identical 200 / 179 decisions.
GEPA_RETENTION_ARGS=${GEPA_RETENTION_ARGS:-"--cell-per-scenario $CELL1_ROOT/per-scenario-tables.json --own-null-per-scenario $OWN_NULL_ROOT/per-scenario-tables.json --delta-consumption $CELL1_ROOT/delta-consumption.json --registered-facts docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/registered-facts-v1.json"}
run "$PY" -B scripts/build_slurp_stage3_delta_retention.py \
    --authored "$PREDECESSOR" \
    --out-json "$RETENTION" --out-markdown "$RETENTION_MD" \
    ${GEPA_RETENTION_ARGS:-}
if [ -f "$ADV_PREPARED/retention-v2.json" ] && [ -f "$RETENTION" ]; then
  "$PY" -B - "$RETENTION" "$ADV_PREPARED/retention-v2.json" <<'PY'
import json, sys
def ids(path):
    d = json.load(open(path, encoding="utf-8"))
    return set(d.get("retired_value_ids") or [])
mine, theirs = ids(sys.argv[1]), ids(sys.argv[2])
print(f"R  cross-check: this line retires {len(mine)}, the v2 line retires {len(theirs)}; "
      f"symmetric difference {len(mine ^ theirs)} (0 is the expected reading -- same inputs, same rule)")
PY
fi

# ---------------------------------------------------------------- B: render the sealed outputs
echo "B  render the sealed GEPA outputs, the construction scope and the permitted roster"
run "$PY" -B scripts/flights/batch/gepa_render_proposal_outputs.py \
    --run "$GEPA_RUN" --attempt "$GEPA_ATTEMPT" --groups "$GEPA_GROUPS" --out-dir "$PREPARED" \
    --permitted-receipt "$PERMITTED_ROSTER"

# ---------------------------------------------------------------- C: curate
echo "C  curate iteration $ITERATION predecessor $PREDECESSOR"
CONTAINMENT=""
[ -f "$TRANSCRIPTS" ] && CONTAINMENT="--construction-transcripts $TRANSCRIPTS"
RETIRE=""
[ -f "$RETENTION" ] && RETIRE="--retire-value-ids $RETENTION"
# shellcheck disable=SC2086
run "$PY" -B scripts/build_slurp_stage3_gepa_delta_rows.py \
    --proposal-outputs "$OUTPUTS" --groups "$GEPA_GROUPS" --repo-root "$REPO" \
    --predecessor "$PREDECESSOR" --iteration "$ITERATION" --run-id "$GEPA_RUN" \
    --facet-rule source-intent --gold-intents "$GOLD" --intent-vocabulary "$CATALOG" \
    $CONTAINMENT $RETIRE \
    --out-authored "$AUTHORED" --out-source "$SOURCE" --source-split-identity-hash "$SPLIT"

# ---------------------------------------------------------------- T: the derangement twin
echo "T  twin seed $TWIN_SEED"
run "$PY" -B scripts/build_slurp_stage3_delta_twin.py \
    --authored "$AUTHORED" --seed "$TWIN_SEED" --out "$TWIN_AUTHORED"
run "$PY" -B scripts/build_slurp_stage3_delta_source.py \
    --authored "$TWIN_AUTHORED" --out "$TWIN_SOURCE" --source-split-identity-hash "$SPLIT"

# ---------------------------------------------------------------- D: runnable registrations
echo "D  materialise the two release registrations at tag $TAG / $TWIN_TAG"
# 2026-09-24: no --version-tag here -- the committed templates already carry their gepa-v1 / gepa-twin-v1 names;
# re-pointing v1 -> gepa-v1 inside them produced source-stage3-deltas-gepa-gepa-v1.json and a refusal.
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" registration \
    --template "$REG_TEMPLATE" --out "$REG" \
    --source-split-identity-hash "$SPLIT"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" registration \
    --template "$TWIN_REG_TEMPLATE" --out "$TWIN_REG" \
    --source-split-identity-hash "$SPLIT"

# ---------------------------------------------------------------- E: release both stores
echo "E  release"
# shellcheck disable=SC2086
run "$PY" -B scripts/build_slurp_stage3_gepa_delta_rows.py \
    --proposal-outputs "$OUTPUTS" --groups "$GEPA_GROUPS" --repo-root "$REPO" \
    --predecessor "$PREDECESSOR" --iteration "$ITERATION" --run-id "$GEPA_RUN" \
    --facet-rule source-intent --gold-intents "$GOLD" --intent-vocabulary "$CATALOG" \
    $CONTAINMENT $RETIRE \
    --out-authored "$AUTHORED" --out-source "$SOURCE" --source-split-identity-hash "$SPLIT" \
    --release "$REG" --data-root "$DATA" --release-pins "$RELEASE_PINS"
run "$PY" -B -m speech_aware_evidence_acquisition.core.driver prepare-semantic-knowledge \
    --registration "$TWIN_REG" --repo-root "$REPO" --data-root "$DATA"

# ---------------------------------------------------------------- R2: supply reach
echo "R2 supply reach against $CATALOG (an inert route is what stopped cell B9a-rec)"
# --version-tag v1 is the IDENTITY of adv1_to_deltas_steps.retag: the two namespaces are passed
# literally because the twin's is stage3-deltas-gepa-twin-v1, which no re-tag of
# stage3-deltas-twin-v1 reaches (it would ask for stage3-deltas-twin-gepa-v1 and find nothing).
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" reach \
    --version-tag v1 \
    --snapshot-relpath "knowledge/slurp/semantic/stage3-deltas-$TAG/snapshot.json" \
    --twin-snapshot-relpath "knowledge/slurp/semantic/stage3-deltas-$TWIN_TAG/snapshot.json" \
    --intent-vocabulary "$CATALOG" --release-pins "$RELEASE_PINS"

echo "F  next: write the CELL-1-GEPA fragments from $RD/cell-1-gepa-diff-plan-v1.md"
echo "== gepa_to_deltas done $(date -u +%FT%TZ) dry=$DRY tag=$TAG"
