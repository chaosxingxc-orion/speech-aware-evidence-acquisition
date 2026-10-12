#!/bin/bash
# Data root: the one authority (scripts/lib/data_root.sh); no hard-coded location.
. "$(cd "$(dirname "${BASH_SOURCE[0]}")/../../lib" && pwd)/data_root.sh" && saea_data_root_init || return 70 2>/dev/null || exit 70
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
# VERSIONING (S3-5 revision v1r, 2026-09-23). DELTA_VERSION_TAG parametrises EVERY artifact,
# namespace and registration name this runbook touches -- authored-stage3-deltas-<tag>.json,
# source-stage3-deltas[-twin]-<tag>.json, stage3-deltas[-twin]-<tag>-release-registration.json,
# knowledge/slurp/semantic/stage3-deltas[-twin]-<tag>/ and the release-pins document. The default
# is v1, which reproduces the first release byte for byte. A NEW tag never touches the old
# artifacts: a superseded store is left where it is, for the record, and is superseded by a
# readiness note, never deleted or rewritten.
#
# What it does, in order:
#   A  preconditions: the sealed ADV-1 advantage outputs, S3-3's pairs.json, the two root
#      S3-5 preparations the release registration pins (construction scope, permitted roster),
#      and -- under the source-intent facet rule -- the construction gold intents and the
#      registered candidate-intent vocabulary
#   B  curate (no release): scripts/build_slurp_stage3_delta_store.py writes the append-only
#      authored-deltas document (schema saea-stage3-authored-deltas-v2, builder policy
#      saea-authored-stage3-deltas-v2) and prints its digest. S3-4s (owner decision 106):
#      one contact yields one to three NODE-attributed rows, each carrying node_target and
#      task_target NODE:DELTA-KIND:TARGET; DELTA_TRANSCRIPTS arms the six-token containment
#      rule (a statement repeating six or more consecutive transcript tokens is dropped at
#      curation, counted). Without DELTA_TRANSCRIPTS the rule is DISABLED and the report
#      says so -- set it before a release.
#      S3-5 revision v1r: DELTA_FACET_RULE decides what associated_facet_ids carries, which is
#      the ONLY field a candidate-bound route intersects against the row's Perception candidate
#      INTENT ids. "source-intent" (the default) writes the source rows' construction gold
#      intent ids plus TARGET when TARGET is itself a legal intent; "target-only" is the
#      pre-v1r rule and is kept so an earlier release reproduces byte for byte. Under
#      target-only the 147 slot-contract rows carried a SLOT TYPE as their facet and only
#      121 of 379 values were reachable by any registered intent (Solver 11 of 151).
#      S3-6 retirement (owner decision 83): DELTA_RETIRE_VALUE_IDS names the retention
#      document scripts/build_slurp_stage3_delta_retention.py writes over the PREVIOUS
#      version's read. The curator then drops the named predecessor rows from version t's
#      set, records their ids in the report, and keeps them as dedup tombstones so the
#      same statements cannot re-enter from the same advantage outputs. Unset -- the
#      default -- leaves append-only exactly as it was and reproduces an earlier
#      version byte for byte.
#   C  twin: scripts/build_slurp_stage3_delta_twin.py derangement of associated_facet_ids
#      (candidate-bound nodes) and of the TARGET field (the unconditional node), each moving a
#      row's WHOLE attachment as one unit so the token count and the facet count are held
#   W  wrap: scripts/build_slurp_stage3_delta_source.py re-envelopes the TWIN's curated document
#      as saea-authored-semantic-knowledge-source-v1 (rows verbatim) plus a two-digest wrap
#      receipt. The generation store's wrapper is written by the curator itself in B and E
#      (--out-source), one process with the curation that produced the rows. A release
#      registration pins the WRAPPER, never --out-authored: prepare_semantic_knowledge_store
#      reads authored_source through that envelope only.
#   D  materialise both release registrations from their committed templates with the real
#      digests, BESIDE the templates in the repository (the preparer records a registration by
#      its repo-relative path and refuses one outside repo_root)
#   E  release the generation store (the curator's own --release path, which also writes the
#      release-pins document) and the twin store (the driver's prepare-semantic-knowledge)
#   R  the model-free supply-reach expectation of both released stores, written into the
#      release-pins document: per node, how many values carry at least one facet among the
#      registered SLURP candidate intents, plus the per-intent facet histogram
#   F  print the CELL-1 fill values (the snapshot value is the snapshot's CONTENT hash, never
#      the snapshot.json file digest) and apply them to the six CELL-1 fragments
#
# Environment overrides: REPO, SPEECHRL_DATA_DIR, PY, ADV1_RUN, ADV1_OUTPUTS, SCORE_RUN,
# DELTA_VERSION_TAG, DELTA_FROM_VERSION_TAG, DELTA_FACET_RULE, DELTA_GOLD_INTENTS,
# DELTA_INTENT_CATALOG, DELTA_ITERATION, DELTA_TWIN_SEED, DELTA_PREDECESSOR,
# DELTA_SCHEMA_VERSION, DELTA_TRANSCRIPTS, DELTA_RETIRE_VALUE_IDS, ADV1_EXPERIMENT (the fragment step A reads the split
# identity out of; overridable so the whole sequence can be dry-rehearsed before ADV-1 sealed).
# DELTAS_DRY=1 (the default) runs A read-only and prints every mutating command line;
# DELTAS_DRY=0 runs them. Commit the six touched fragments AND the two materialised release
# registrations afterwards, then re-pin.
set -u
REPO=${REPO:-/home/chao/saea-worktrees/fable-s3adv}
DATA=$SAEA_DATA_ROOT
PY=${PY:-/home/chao/.venvs/speechrl/bin/python}
export SPEECHRL_DATA_DIR=$DATA PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$REPO:$REPO/src
DRY=${DELTAS_DRY:-1}

ADV1_RUN=${ADV1_RUN:-SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1}
SCORE_RUN=${SCORE_RUN:-SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1}
DELTA_ITERATION=${DELTA_ITERATION:-1}
# Which store version this pass builds, and which one the CELL-1 fragments currently pin.
TAG=${DELTA_VERSION_TAG:-v1}
FROM_TAG=${DELTA_FROM_VERSION_TAG:-v1}
# The twin seed is a documented constant, not a tuned one: it names one Sattolo cycle and is
# recorded so the derangement is reproducible byte for byte.
DELTA_TWIN_SEED=${DELTA_TWIN_SEED:-20260922}
DELTA_PREDECESSOR=${DELTA_PREDECESSOR:-none}
# S3-4s: 2 is the node-targeted curation; 1 keeps the pre-S3-4s single-statement path.
DELTA_SCHEMA_VERSION=${DELTA_SCHEMA_VERSION:-2}
# S3-5 revision v1r: source-intent (the default) or target-only (the pre-v1r rule).
DELTA_FACET_RULE=${DELTA_FACET_RULE:-source-intent}
# The construction rows' transcripts, read ONLY to reject statements that repeat six or
# more consecutive transcript tokens. Root's own model-free preparation; never in Git.
DELTA_TRANSCRIPTS=${DELTA_TRANSCRIPTS:-}
# S3-6 (owner decision 83): the retention document whose RETIRE ids version t drops from
# its predecessor. Empty -- the default -- keeps the pre-S3-6 append-only curation.
DELTA_RETIRE_VALUE_IDS=${DELTA_RETIRE_VALUE_IDS:-}

PREPARED=$DATA/prepared/SAEA-SLURP-STAGE3-DELTAS-V1
# S3-4s: the containment rule's input, beside the other prepared/ documents.
: "${DELTA_TRANSCRIPTS:=$PREPARED/construction-transcripts.jsonl}"
# The construction rows' GOLD intent ids (owner decision 82: legal on the construction side),
# keyed by sample id, and the registered candidate-intent vocabulary a TARGET must be in to be
# kept as a facet. Both are read model-free and neither is ever printed.
DELTA_GOLD_INTENTS=${DELTA_GOLD_INTENTS:-$DATA/coordination/slurp-stage3-advantage-r01-v1/r01c-gold-intents.json}
DELTA_INTENT_CATALOG=${DELTA_INTENT_CATALOG:-$DATA/prepared/SAEA-SLURP-NATIVE-CANDIDATE-CONTRACTS-PREPARE-V1/catalog.json}
# Rendered from the sealed ADV-1 run's custodied outputs at the ADV-1 seal (one JSON object per
# line: {"sample_id", "response_text", "disagreement"}); it is S3-4's own deliverable, not this
# runbook's, and it never enters Git.
ADV1_OUTPUTS=${ADV1_OUTPUTS:-$PREPARED/advantage-outputs-v1.jsonl}
PAIRS=$DATA/analysis/$SCORE_RUN/pairs.json
AUTHORED=$PREPARED/authored-stage3-deltas-$TAG.json
TWIN_AUTHORED=$PREPARED/authored-stage3-deltas-twin-$TAG.json
# The RELEASE SOURCE documents: the same rows inside the shared
# saea-authored-semantic-knowledge-source-v1 envelope, which is the only shape a registration's
# authored_source may pin. Beside each one, its <stem>-wrap-receipt.json pins the curated
# document it was built from by SHA-256 (the envelope itself admits no extra key).
SOURCE=$PREPARED/source-stage3-deltas-$TAG.json
TWIN_SOURCE=$PREPARED/source-stage3-deltas-twin-$TAG.json
SCOPE=$PREPARED/outer-construction-roster.json
PERMITTED=$PREPARED/permitted-roster.json
COORD=$DATA/coordination/slurp-stage3-delta-cell-r01-v1
REG_TEMPLATE=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-v1-release-registration.template.json
TWIN_REG_TEMPLATE=docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-twin-v1-release-registration.template.json
# The runnable registrations are REPOSITORY files, beside their templates and committed after
# the run: core.semantic_knowledge_preparation records a registration by its repo-relative path
# and refuses outright one that is not confined to repo_root (the slot-contracts precedent
# docs/readiness/2026-09-17-slurp-slot-contracts-preparation-registration-v2.json).
REG=$REPO/docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-$TAG-release-registration.json
TWIN_REG=$REPO/docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-twin-$TAG-release-registration.json
RELEASE_PINS=$COORD/stage3-deltas-$TAG-release-pins.json
mkdir -p "$COORD"  # 2026-09-23: the first real run lost its release-pins write to a missing coordination directory
if [ "$TAG" = "v1" ]; then VALUES=$COORD/cell1-fill-values.json; else VALUES=$COORD/cell1-fill-values-$TAG.json; fi
HELPERS=scripts/flights/batch/adv1_to_deltas_steps.py
ADV1_EXPERIMENT=${ADV1_EXPERIMENT:-configs/experiment/slurp-native-stage3-advantage-r01-v1.json}
CELL_EXPERIMENT=configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json
SMOKE_EXPERIMENT=configs/experiment/slurp-native-stage3-delta-cell-smoke-4-v1.json
CELL_BASELINES="configs/baseline/slurp-native-stage3-delta-cell-baseline-v1.json configs/baseline/slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json configs/baseline/slurp-native-stage3-delta-cell-twin-baseline-v1.json configs/baseline/slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1.json"

cd "$REPO" || { echo "no checkout at $REPO"; exit 1; }
echo "== adv1_to_deltas $(date -u +%FT%TZ) REPO=$REPO HEAD=$(git rev-parse --short HEAD) dry=$DRY tag=$TAG facet_rule=$DELTA_FACET_RULE"

# ---------------------------------------------------------------- A: preconditions
SPLIT=$($PY -B -c "import json,sys;print(json.load(open(sys.argv[1]))['population']['split_identity_hash'])" "$ADV1_EXPERIMENT")
case "$SPLIT" in
  PENDING_*|"") echo "A  ADV-1 split identity is still $SPLIT: run scripts/flights/batch/adv1_prepare.sh first"; exit 2;;
esac
echo "A  ADV-1 population split identity $SPLIT"
NEEDED="$ADV1_OUTPUTS $PAIRS $SCOPE $PERMITTED"
if [ "$DELTA_FACET_RULE" = "source-intent" ]; then NEEDED="$NEEDED $DELTA_GOLD_INTENTS $DELTA_INTENT_CATALOG"; fi
for F in $NEEDED; do
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
echo "B  curate iteration $DELTA_ITERATION predecessor $DELTA_PREDECESSOR schema v$DELTA_SCHEMA_VERSION"
CONTAINMENT=""
if [ -f "$DELTA_TRANSCRIPTS" ]; then
  CONTAINMENT="--construction-transcripts $DELTA_TRANSCRIPTS"
else
  echo "B  NO transcripts at $DELTA_TRANSCRIPTS: the six-token containment rule will be"
  echo "   DISABLED and the curation report will say so. Prepare them before releasing."
fi
FACETS="--facet-rule $DELTA_FACET_RULE"
if [ "$DELTA_FACET_RULE" = "source-intent" ]; then
  FACETS="$FACETS --gold-intents $DELTA_GOLD_INTENTS --intent-vocabulary $DELTA_INTENT_CATALOG"
fi
RETIRE=""
if [ -n "$DELTA_RETIRE_VALUE_IDS" ]; then
  [ -f "$DELTA_RETIRE_VALUE_IDS" ] || { echo "B  MISSING retention document $DELTA_RETIRE_VALUE_IDS"; exit 2; }
  [ "$DELTA_PREDECESSOR" = "none" ] && { echo "B  DELTA_RETIRE_VALUE_IDS needs a DELTA_PREDECESSOR to retire rows from"; exit 2; }
  RETIRE="--retire-value-ids $DELTA_RETIRE_VALUE_IDS"
  echo "B  retiring the value ids named by $DELTA_RETIRE_VALUE_IDS"
fi
# shellcheck disable=SC2086
run "$PY" -B scripts/build_slurp_stage3_delta_store.py \
    --advantage-outputs "$ADV1_OUTPUTS" --pairs "$PAIRS" --repo-root "$REPO" \
    --predecessor "$DELTA_PREDECESSOR" --iteration "$DELTA_ITERATION" \
    --run-id "$ADV1_RUN" --out-authored "$AUTHORED" \
    --schema-version "$DELTA_SCHEMA_VERSION" $CONTAINMENT $FACETS $RETIRE \
    --out-source "$SOURCE" --source-split-identity-hash "$SPLIT"

# ---------------------------------------------------------------- C: the derangement twin
echo "C  twin seed $DELTA_TWIN_SEED"
run "$PY" -B scripts/build_slurp_stage3_delta_twin.py \
    --authored "$AUTHORED" --seed "$DELTA_TWIN_SEED" --out "$TWIN_AUTHORED"

# ---------------------------------------------------------------- W: the twin's release source
# The twin's document is a derangement, not a curation, so no curator run produces its wrapper;
# this is the same conversion the curator applies to the generation document in B and E.
echo "W  wrap the twin's curated document as a release source"
run "$PY" -B scripts/build_slurp_stage3_delta_source.py \
    --authored "$TWIN_AUTHORED" --out "$TWIN_SOURCE" \
    --source-split-identity-hash "$SPLIT"

# ---------------------------------------------------------------- D: runnable registrations
echo "D  materialise the two release registrations at tag $TAG"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" registration \
    --template "$REG_TEMPLATE" --out "$REG" --version-tag "$TAG" \
    --source-split-identity-hash "$SPLIT"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" registration \
    --template "$TWIN_REG_TEMPLATE" --out "$TWIN_REG" --version-tag "$TAG" \
    --source-split-identity-hash "$SPLIT"

# ---------------------------------------------------------------- E: release both stores
# The generation store goes out through the curator's own --release path (it also writes the
# release-pins document the spec asks for). Re-running the curator here is deliberate and safe:
# curation is deterministic (survivors sorted by value_id), so --out-authored and --out-source
# are rewritten byte for byte and the digest step D pinned still matches -- and if it ever did
# not, the preparer fails closed on the authored_source pin rather than releasing a different
# store. --out-source is passed again HERE, in the same process as this re-curation, so that
# what the preparer then reads is the wrapper of the rows this process just curated.
echo "E  release"
# shellcheck disable=SC2086
run "$PY" -B scripts/build_slurp_stage3_delta_store.py \
    --advantage-outputs "$ADV1_OUTPUTS" --pairs "$PAIRS" --repo-root "$REPO" \
    --predecessor "$DELTA_PREDECESSOR" --iteration "$DELTA_ITERATION" \
    --run-id "$ADV1_RUN" --out-authored "$AUTHORED" \
    --schema-version "$DELTA_SCHEMA_VERSION" $CONTAINMENT $FACETS $RETIRE \
    --out-source "$SOURCE" --source-split-identity-hash "$SPLIT" \
    --release "$REG" --data-root "$DATA" --release-pins "$RELEASE_PINS"
# The twin's authored document is the derangement, not a curation, so it is released directly.
# 2026-09-23 (first real run): the PACKAGE entry core.driver (its __main__) runs main(); "-m ...core.driver.cli"
# imported the module without running it and exited 0 having released nothing.
run "$PY" -B -m speech_aware_evidence_acquisition.core.driver prepare-semantic-knowledge \
    --registration "$TWIN_REG" --repo-root "$REPO" --data-root "$DATA"

# ---------------------------------------------------------------- R: the supply-reach expectation
# Model-free, counts and intent ids only. An inert route is what stopped cell B9a-rec; this is
# the number that says, before any contact, what each candidate-bound route can ever select.
echo "R  supply reach against $DELTA_INTENT_CATALOG"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" reach \
    --version-tag "$TAG" --intent-vocabulary "$DELTA_INTENT_CATALOG" \
    --release-pins "$RELEASE_PINS"

# ---------------------------------------------------------------- F: the CELL-1 fill values
echo "F  CELL-1 fill values"
run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" cell1-values \
    --version-tag "$TAG" --values-out "$VALUES"
BY="S3-5 release of knowledge/slurp/semantic/stage3-deltas-$TAG/ (iteration $DELTA_ITERATION, predecessor $DELTA_PREDECESSOR, facet rule $DELTA_FACET_RULE, curated from the sealed $ADV1_RUN advantage outputs) and its derangement twin stage3-deltas-twin-$TAG (seed $DELTA_TWIN_SEED); release pins $RELEASE_PINS"
# Two ways in, one contract. While a fragment still carries the PENDING_ tokens the substitution
# tool fills them; once it carries real digests there is no token left to replace and the
# re-point step rewrites the store pins by JSON path instead. Neither ever invents a value.
# shellcheck disable=SC2086
if grep -q "PENDING_S3_5_RELEASE_JSON_SHA256" $CELL_EXPERIMENT $SMOKE_EXPERIMENT $CELL_BASELINES 2>/dev/null; then
  # shellcheck disable=SC2086
  run "$PY" -B scripts/flights/batch/roll1_fill_placeholders.py \
      --fragments $CELL_EXPERIMENT $SMOKE_EXPERIMENT $CELL_BASELINES \
      --values "$VALUES" --by "$BY" --occurrence-policy any --date "$(date -u +%F)"
else
  echo "F  no PENDING token left in the fragments: re-pointing the store pins from $FROM_TAG to $TAG"
  run "$PY" -B "$HELPERS" --repo-root "$REPO" --data-root "$DATA" repoint \
      --values "$VALUES" --version-tag "$TAG" --from-version-tag "$FROM_TAG"
fi

echo "F  commit: git add $CELL_EXPERIMENT $SMOKE_EXPERIMENT $CELL_BASELINES \\"
echo "               docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-$TAG-release-registration.json \\"
echo "               docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-twin-$TAG-release-registration.json"
echo "           && git commit -F <message file>"
echo "== adv1_to_deltas done $(date -u +%FT%TZ) dry=$DRY tag=$TAG"
