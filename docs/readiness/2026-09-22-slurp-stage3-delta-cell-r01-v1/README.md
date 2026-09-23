# Readiness package: SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1

Status: **HELD**. This package registers the engineering for Stage-3 S3-6 (CELL-1: the locked plan
plus the stage3-deltas store) -- it does not authorize a flight, a readiness flip, or an admission
entry. Source spec: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section
S3-6.

Stage-3 algorithm (owner decision 101): **`tfgrpo-semantic-advantage-v1`** (Training-Free GRPO,
arXiv:2510.08191), operators `update` + `context_application` -- the experiential deltas of S3-5 applied
candidate-bound to the Solver. The GEPA and ACE arms (`gepa-reflective-pareto-v1`, `ace-grow-refine-v1`)
reuse this package's store and supply route with a different curation operator; see the engineering spec's
"Algorithm labels, decision 101" section. Declared as `stage3_algorithm` in
`configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json` and checked by
`scripts/checks/stage3_algorithm_label_check.py`.

## What this cell is

The locked PLAN fragment (`configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`) plus
exactly one added store, `knowledge_stores.stage3-deltas`, routed to the Solver phase: every delta
whose `associated_facet_ids` intersects the row's Perception candidate intents, capped at 8 per row
by `prior_score` (the statement's disagreement mass), ordered descending
(`rails.stage3_delta_supply.select_stage3_delta_values`). Comparator: the sealed PLAN arm at the
plan's own null (h_SLU 1.2485 / h_intent 0.9943). Twin: the same store with a seeded derangement of
`associated_facet_ids` (`scripts/build_slurp_stage3_delta_twin.py`) as the form control.

**The read population is unchanged TRAIN Fold A.** R01C changes which rows the deltas are BUILT
from (ROLL-1 -> S3-3 -> ADV-1 -> S3-5), never which rows this cell is read on.

## Engineering delivered here

- `rails/stage3_delta_supply.py`: the candidate-bound, prior_score-capped selection algorithm
  (`select_stage3_delta_values`, `DeltaCandidate`, `stage3_delta_selection_receipt`), fully tested on
  synthetic fixtures (`tests/unit/test_stage3_delta_supply.py`).
- `rails.knowledge_provider.Stage3DeltaCandidateProvider`, registered into `core.base.KNOWLEDGE_PROVIDERS`
  under `stage3-delta-candidate-bound-v1` (`rails/knowledge_provider.py`, the canonical registration
  site `scripts/checks/engineering_base_check.py` requires): a real, tested `KnowledgeProvider`
  (`build`/`candidates`/`fuse`) wrapping the selection algorithm.
- `scripts/build_slurp_stage3_delta_twin.py`: a seeded, zero-fixed-point derangement of
  `associated_facet_ids` over an authored-deltas document (Sattolo's algorithm, the same idiom as the
  B1/IDXT twins), tested (`tests/unit/test_stage3_delta_supply.py`).
- `scripts/build_slurp_stage3_delta_source.py` and the curator's own `--out-source`: the
  authored-deltas -> RELEASE SOURCE conversion (see "The release source" below), tested end to end in
  `tests/unit/test_stage3_delta_source_wrap.py`.
- Four baseline fragments (`configs/baseline/slurp-native-stage3-delta-cell-*-v1.json`: generation,
  twin, and their four-row smokes), each the locked PLAN fragment plus exactly one added store; proof
  test `tests/unit/test_stage3_delta_cell_fragment.py`.
- One experiment fragment (`configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json`) carrying
  six held cells: generation, twin, both fits, both four-row smokes (run ids
  `SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1`, `-TWIN-V1`, `-R01-FIT-V1`, `-TWIN-FIT-V1`,
  `-SMOKE-4-V1`, `-SMOKE-4-TWIN-V1`).
- The S3-5 runbook `scripts/flights/batch/adv1_to_deltas.sh` with its helper
  `scripts/flights/batch/adv1_to_deltas_steps.py` and the two release-registration TEMPLATES beside
  this README (added with the 2026-09-22 re-pointing below).

## Root wiring: DONE (S3-6w, 2026-09-22)

The spec's own prose names `context_supply` as the routing field, and separately says the store
should use "the same candidate-bound routing the slot-contracts store uses". The S3-6w follow-up
extended `rails.knowledge_stores.build_knowledge_store_supply`'s `context_supply` dispatcher to
recognise a SECOND provider shape alongside the pre-existing source-scoped one:

- The pre-existing shape (`set(raw_spec) == {"provider"}`, the source-scoped provider) is completely
  unchanged -- byte-identical construction, byte-identical routing, byte-identical receipts, proven by
  `tests/unit/test_stage3_delta_supply_router.py::
  test_existing_two_admitted_routes_stay_byte_identical_when_stage3_deltas_is_added` alongside the
  full existing `test_knowledge_stores*.py` / `test_candidate_semantic_supply.py` suites.
- A store with `store_role: "stage3-deltas"` may now declare `context_supply.<phase> = {"provider":
  "stage3-delta-candidate-bound-v1", "candidate_state_phase", "cap", "rank_by": "prior_score"}` --
  exactly the shape the fragments below already carried. The router reads the row's Perception
  candidate intents off the `candidate_state_phase` state (`rails.slurp_intent_hypotheses.
  parse_slurp_intent_hypothesis_state`, canonical/non-compact form), then routes them through the
  registered `rails.knowledge_provider.Stage3DeltaCandidateProvider`: candidate-bound, capped,
  `prior_score`-ranked, deterministic.
- The router's E3b collision guard (rule 1: scoped `context_supply` and `candidate_supply` never
  coexist on one phase) is narrowed the SAME way E3b narrowed the phase_supply/candidate_supply
  guard: only for phases a store routes through the STAGE3_DELTA provider specifically.

`candidate_supply`'s own two-role, round-robin dispatcher was left untouched -- the stage3-deltas
route lives entirely in `context_supply`, never inside `candidate_supply`.

The `PENDING_ROOT_WIRING` readiness requirement that stood for this follow-up **was removed** in the
2026-09-22 re-pointing, and the fragments' `what_the_stage3_deltas_store_is` notes, which still said
the route was unresolved, were corrected. Only the store's own release and a root admission decision
block a flight now.

## Re-pointing and plan numbers (2026-09-22)

Filled from committed bytes in this pass:

| what | value | basis |
| --- | --- | --- |
| `population.count` | 1080 | TRAIN Fold A, the population the sealed PLAN arm and PLANr read |
| `population.split_identity_hash` | `61b0f062...5398b6` | **corrected**: the fragment carried `4e3413fe...b969cb`, which is the FOUR-ROW smoke's identity (`configs/experiment/slurp-native-default-plan-lock-smoke-4-v1.json`), not the 1,080-row roster's |
| `planned_model_calls` / `generation_calls_cap` | 11,880 = 1,080 x 11 | cell PLAN's own registered per-row ceiling; this cell is PLAN plus one store, so the role graph and the ceiling are PLAN's unchanged |
| `fit_endpoint_calls_cap` | 47,520 = 11,880 x (1 speech packet + 3 endpoints) | cell PLAN |
| `planned_speech_audio_seconds` / `repeated_speech_audio_seconds_cap` | 33,930 | cell PLAN |
| `native_task_contract_calls_cap` | 6,480 | cell PLAN |
| `planned_gpu_hours` / `gpu_hours_fit_inclusive` | 12.0 | cell PLAN's registered ceiling (the spec's point estimate for arm + twin is 3.6; ceilings are bounds, never targets) |
| `service_session` | `serving-slurp-native-candidate-five-train-a-np4-v1` | this cell's model fragment is byte-identical to cell PLAN's and cell ROLL-1's, and both name that resident session |

The one top-level `execution_plan` governs all six cells; each flies under its own run id and the
plan budget is run-cumulative, so each four-row smoke consumes 44 of the same ceiling.
`generation_budget` carries the arithmetic in free English, the ROLL-1 form.

The placeholder decision requirement was removed for the same reason it was removed from ADV-1:
`core.flight.repin._upsert_decision_requirement` inserts the real one at the readiness flip, and a
placeholder entry without an `expected_decision_id` left beside it would refuse the campaign at load
(`core.flight.campaign.declared_readiness`).

## What is left for root

**Historical (the version-1 pass).** Every `PENDING_` token below was filled long ago; the store now
pinned is revision **v1r** and the fill map's paths name version 1. See "S3-5 revision v1r" at the
end of this README for what is actually in force, and `stage3-deltas-v1-superseded-v1.md` for why.

The fill map is `docs/readiness/2026-09-22-slurp-stage3-advantage-r01-v1/fill-after-roll1-seal.json`
(one file for both Stage-3 packages): every remaining token, its exact JSON path, the artefact that
produces it and the field to copy.

- `PENDING_S3_5_RELEASE_JSON_SHA256` / `PENDING_S3_5_SNAPSHOT_JSON_SHA256`: S3-5's release of
  `knowledge/slurp/semantic/stage3-deltas-v1/`. **These were one token until this pass.** `release
  .json` and `snapshot.json` are two files with two digests, so a single `PENDING_S3_5_RELEASE_SHA256`
  could never be filled correctly by any substitution tool; it was split.
- `PENDING_S3_6_TWIN_RELEASE_JSON_SHA256` / `PENDING_S3_6_TWIN_SNAPSHOT_JSON_SHA256`: the twin
  release of `knowledge/slurp/semantic/stage3-deltas-twin-v1/`, split for the same reason.
- `PENDING_<CELL>_OWN_<KEY>` (per cell, 28 tokens over the four baselines): the per-flight
  bookkeeping (`native_contact_fit`, `prepared_phase_supply`, `preparation_source_receipts`,
  speech-feature identity ids, `speech_packet_promotion_receipt[_sha256]`) this cell must prepare
  under its OWN run id before flight (owner rule E16: a prepared artifact is evidence only for the
  implementation that produced it) -- never PLAN's own pins, even though the bytes may turn out
  identical. These are minted by `scripts/flights/repin_cell.py`, never by the substitution tool,
  and `--allow-output-change` must never be passed.
- A root admission decision, and the two S3-5 preparations the release registration pins (see below).

## The runbook

`scripts/flights/batch/adv1_to_deltas.sh` -- run by ROOT after cell ADV-1 seals and after
`scripts/flights/batch/adv1_prepare.sh` has filled the ADV-1 fragments (this runbook reads the
disagreeing-row split identity out of the ADV-1 experiment fragment). Model-free: zero frozen-core,
tool, embedding, encoder, tokenizer, scorer, GPU and network contacts. `DELTAS_DRY=1` is the default
and prints every mutating command line; `DELTAS_DRY=0` performs them.

```
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 DELTAS_DRY=0 REPO=<checkout> \
  DELTA_VERSION_TAG=v1r DELTA_FROM_VERSION_TAG=v1 \
  bash scripts/flights/batch/adv1_to_deltas.sh
```

`DELTA_VERSION_TAG` (default `v1`) names the store version this pass builds and parametrises every
artifact, namespace and registration name below;
`DELTA_FROM_VERSION_TAG` names the version the fragments currently pin. `DELTA_FACET_RULE` (default
`source-intent`) chooses the facet rule. The transcript below is the **version-1** pass, kept because it
names each step; at another tag every `-v1` in it becomes `-<tag>`, and two steps are added -- **R**, the
supply-reach measurement, and, in **F**, the JSON-path re-point that replaces the substitution tool once no
`PENDING_` token is left.

which runs, in order:

```
python scripts/build_slurp_stage3_delta_store.py --advantage-outputs <prepared>/advantage-outputs-v1.jsonl \
    --pairs <data>/analysis/SAEA-SLURP-STAGE3-ROLLOUT-R01-SCORE-V1/pairs.json --repo-root "$REPO" \
    --predecessor none --iteration 1 --run-id SAEA-SLURP-STAGE3-ADVANTAGE-R01-V1 \
    --out-authored <prepared>/authored-stage3-deltas-v1.json \
    --out-source <prepared>/source-stage3-deltas-v1.json \
    --source-split-identity-hash <the ADV-1 population's>
python scripts/build_slurp_stage3_delta_twin.py --authored <prepared>/authored-stage3-deltas-v1.json \
    --seed 20260922 --out <prepared>/authored-stage3-deltas-twin-v1.json
python scripts/build_slurp_stage3_delta_source.py --authored <prepared>/authored-stage3-deltas-twin-v1.json \
    --out <prepared>/source-stage3-deltas-twin-v1.json \
    --source-split-identity-hash <the ADV-1 population's>
python scripts/flights/batch/adv1_to_deltas_steps.py --repo-root "$REPO" --data-root "$DATA" registration \
    --template docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-v1-release-registration.template.json \
    --out "$REPO"/docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-v1-release-registration.json \
    --source-split-identity-hash <the ADV-1 population's>      # and again for the twin template
python scripts/build_slurp_stage3_delta_store.py <same curation and --out-source arguments> \
    --release "$REPO"/docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-v1-release-registration.json \
    --data-root "$DATA" --release-pins <coordination>/stage3-deltas-v1-release-pins.json
python -m speech_aware_evidence_acquisition.core.driver.cli prepare-semantic-knowledge \
    --registration "$REPO"/docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1/stage3-deltas-twin-v1-release-registration.json \
    --repo-root "$REPO" --data-root "$DATA"
python scripts/flights/batch/adv1_to_deltas_steps.py --repo-root "$REPO" --data-root "$DATA" \
    cell1-values --values-out <coordination>/cell1-fill-values.json
python scripts/flights/batch/roll1_fill_placeholders.py \
    --fragments configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json \
                configs/baseline/slurp-native-stage3-delta-cell-baseline-v1.json \
                configs/baseline/slurp-native-stage3-delta-cell-smoke-4-baseline-v1.json \
                configs/baseline/slurp-native-stage3-delta-cell-twin-baseline-v1.json \
                configs/baseline/slurp-native-stage3-delta-cell-twin-smoke-4-baseline-v1.json \
    --values <coordination>/cell1-fill-values.json --by "<provenance>" --occurrence-policy any
```

The generation store goes out through the curator's own `--release` path (which also writes the
release-pins document the spec asks for); the twin's authored document is a derangement, not a
curation, so it is released directly through the driver's `prepare-semantic-knowledge`. Re-running
the curator for the release step is deliberate: curation is deterministic (survivors sorted by
`value_id`), so the authored bytes -- and the release source wrapped from them in the same process,
and therefore the digest the registration pinned -- are reproduced, and if they ever were not, the
preparer fails closed on the `authored_source` pin rather than releasing a different store.

**Two release registrations are committed here as TEMPLATES**
(`stage3-deltas-v1-release-registration.template.json`,
`stage3-deltas-twin-v1-release-registration.template.json`).
`core.semantic_knowledge_preparation.prepare_semantic_knowledge_store` verifies `authored_source`,
`construction_scope`, `permitted_roster` and every `forbidden_rosters` pin by SHA-256, and the
release source's digest only exists after the curator has written it -- so the committed file
carries `PENDING_` tokens, is never passed to the preparer and is never edited in place; the helper
materialises a runnable copy **beside the templates in this package** with the real digests. That
copy is a REPOSITORY path, not a data-root one: the preparer records a registration by its
repo-relative path (`_registration`) and refuses outright one that is not confined to `repo_root`,
which is why `docs/readiness/2026-09-17-slurp-slot-contracts-preparation-registration-v2.json` is a
repository file too. Commit both runnable registrations with the filled fragments. The helper also
re-verifies each forbidden-roster digest (TRAIN Fold A, TRAIN Fold B, DEV-1000) against the committed
receipt, and re-verifies that `authored_source` really is a wrapped release source, failing closed on
either mismatch. The two `prepared/` roster documents the registration pins
(`outer-construction-roster.json`, `permitted-roster.json`, in the shape the slot-contracts
preparation uses) are root's own S3-5 preparations; the runbook checks for them and stops, it does
not invent them.

## The release source (the wrapper between curation and release)

`prepare_semantic_knowledge_store` reads an `authored_source` **only** through the shared envelope
`saea-authored-semantic-knowledge-source-v1` -- exactly
`{schema, builder_policy_id, source_split_identity_hash, rows}`, key set checked for equality, with
`builder_policy_id` and `source_split_identity_hash` cross-checked against the registration's own
(`core.semantic_knowledge_preparation._source_rows`). The curator's `--out-authored` document is a
different shape (`saea-stage3-authored-deltas-v2`, with `iteration`, and no builder or split
identity), and so is the twin's derangement of it (which adds `twin_of_seed`). Neither may be pinned
as an `authored_source`; until this conversion existed the release step could not run at all.

The conversion (`build_authored_source_document` in `scripts/build_slurp_stage3_delta_store.py`,
exposed as `scripts/build_slurp_stage3_delta_source.py`) carries **every row over verbatim** --
`value_id`, `content`, `associated_facet_ids`, `node_target`, `source_sample_ids`, `provenance_refs`,
`task_target`, `prior_score` -- in the document's own order, re-validating each row's exact key set on
the way through, and adds nothing but the envelope's three header fields. `builder_policy_id` is
derived from the authored schema (v1 -> `saea-authored-stage3-deltas-v1`, v2 ->
`saea-authored-stage3-deltas-v2`), never typed. Bytes are canonical JSON with sorted keys, so the
digest a registration pins is reproducible.

Because the envelope admits no fourth key, the link back to curation is a **wrap receipt** written
beside the wrapper (`source-stage3-deltas-v1-wrap-receipt.json`, schema
`saea-stage3-delta-source-wrap-receipt-v1`): the authored document's SHA-256, the wrapper's SHA-256,
the authored schema, the iteration (and a twin's seed) and the row count. The registration pins the
wrapper; the receipt closes the chain back to the curated document.

The generation store's wrapper is written by the curator itself (`--out-source`, in the same process
as the curation that produced the rows, in step B and again in step E), so a drift in curation would
move the wrapper's digest and the preparer would refuse the pin instead of releasing different
content. The twin's document is a derangement rather than a curation, so its wrapper is written by
the standalone CLI in step W.

## Proof obligations covered by tests

- `tests/unit/test_stage3_delta_supply.py`: candidate-bound selection, prior_score ordering, the cap,
  empty-match returns `()` never raises, the receipt carries no content, the twin derangement has zero
  fixed points, preserves every non-facet field, and is deterministic for a fixed seed.
- `tests/unit/test_stage3_delta_supply_router.py`: the two pre-existing `context_supply` routes stay
  byte-identical once the stage3-deltas route is added.
- `tests/unit/test_stage3_delta_cell_fragment.py`: the generation cell equals the locked PLAN fragment
  on every key except the one added store and the per-flight bookkeeping keys; the twin cell equals the
  generation cell except the release namespace; every pin left for root is an explicit `PENDING_`
  token; the smoke variants carry the same store shape as their full siblings.
- `tests/unit/test_roll1_fill_placeholders.py`: the substitution tool's ROLL-1 contract is unchanged
  by the `--fragments` / `--occurrence-policy` arguments this package needs.
- `tests/unit/test_stage3_delta_source_wrap.py`: the release path end to end on a SYNTHETIC authored
  document in `tmp_path` (never `SPEECHRL_DATA_DIR`) -- curate + wrap, derange + wrap, materialise
  both registrations through `adv1_to_deltas_steps.py`, release through
  `prepare_semantic_knowledge_store`, round-trip the snapshot's values, and serve all four per-node
  `context_supply` routes from the released snapshot; plus the two refusals that make the shape
  mandatory (a curated document pinned as `authored_source`, and a registration written outside
  `repo_root`) and the consistency of the committed templates with the runbook's own paths.

## S3-4s amendment: per-node supply (owner decision 106, 2026-09-23)

Still **HELD**; nothing below authorises a flight, a flip or an admission entry.

**The store is node-targeted.** S3-5's curator now writes `node_target` per row and
`task_target = NODE:DELTA-KIND:TARGET`, under the authored schema
`saea-stage3-authored-deltas-v2` and the builder policy `saea-authored-stage3-deltas-v2`
(registered BESIDE `...-v1`, which stays loadable and flyable). `associated_facet_ids` is the bare
`TARGET` -- the value a candidate-bound route actually intersects a row's Perception candidate intent
ids against. One further curation rule: a statement repeating six or more consecutive tokens of any
construction-row transcript is dropped, counted, and never printed
(`--construction-transcripts`; `DELTA_TRANSCRIPTS` in the runbook). Without that file the rule is
DISABLED and the curation report says so -- prepare it before releasing.

**Four routes, one store** (declared in all four delta-cell baseline fragments and their twins):

| phase | provider | cap | binding |
| --- | --- | --- | --- |
| `perception` | `stage3-delta-unconditional-v1` | 4 | unconditional (no candidate state exists yet) |
| `reviewer` | `stage3-delta-candidate-bound-v1` | 4 | candidate-bound, `node_target: reviewer` |
| `planner` | `stage3-delta-candidate-bound-v1` | 4 | candidate-bound, `node_target: planner` |
| `solver` | `stage3-delta-candidate-bound-v1` | 8 | candidate-bound, `node_target: solver` |

The pre-S3-4s `context_supply` contract insisted on a LATER supplied phase, for a real reason: a
later phase has a preceding `advance` to carry its per-row decision and the first phase has none.
Perception is admitted through its own validation branch rather than around that reason: its
selection carries **no per-row term at all**, so it is decided once per flight and SEEDED -- through
`rails.knowledge_stores`' `bootstrap_first_phase`, and, when a cell pins a `prepared_phase_supply`
artifact for the first phase's retrieval store, through the new
`unconditional_first_phase` seam that `core.flight.runtime._merge_unconditional_first_phase`
composes on top of it. A `candidate_state_phase` on that route is REFUSED, not ignored. Every flight
whose router publishes no such seam is byte-identical to its pre-S3-4s self.

**The twin.** `scripts/build_slurp_stage3_delta_twin.py` now reads the v2 schema and twins each group
by what that group's route actually reads: the candidate-bound nodes keep v1's facet derangement, the
unconditional list gets a derangement of its TARGET fields (and the `associated_facet_ids` entry that
mirrors it). Both are permutations within their own group, so the **token count is held exactly** --
`authored_token_count(twin) == authored_token_count(parent)`, enforced in the builder and proven in
`tests/unit/test_stage3_delta_twin_v2.py`. A group naming one distinct attachment is refused (every
permutation of it is the identity in effect); a duplicate row landing on an equal value is counted
(`value_fixed_points`) rather than refused, because a real store carries several deltas per target and
refusing that would make the v2 twin unbuildable.

**The equality proof is unchanged in kind**: `tests/unit/test_stage3_delta_cell_fragment.py` now also
asserts that, after the per-flight bookkeeping and documentation keys are excluded, the ONLY key on
which the cell fragment differs from `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json`
is `knowledge_stores`, and the only added store key is `stage3-deltas` with exactly
`{context_supply, release, snapshot, store_role}`.

**Tests**: `tests/unit/test_stage3_delta_node_routes.py` (the node filter partitions one pool into
disjoint slices; the unconditional selection has no row-dependent term; the first-phase seed and its
receipt; the unconditional spec validated fail-closed, including the refusal of `candidate_state_phase`
and of the unconditional provider on a later phase; a pre-S3-4s spec without `node_target` still
validates and routes unchanged), `tests/unit/test_stage3_delta_store_v2.py` (the v2 builder, the
containment rule and its counts) and `tests/unit/test_stage3_delta_twin_v2.py`.

## Registration (2026-09-23): the package is complete and the fragments compose

Still **HELD**. Nothing in this section authorises a flight, a flip or an admission entry.

The CELL-1 registration agent (worktree `/home/chao/saea-worktrees/fable-cell1reg`, branch `fable/cell1reg`,
base master `56b1570b`) wrote the registration documents this package was missing and repaired the fragment
defects that stopped it composing at all. The full statement is
`docs/readiness/2026-09-22-slurp-stage3-delta-cell-r01-v1-preregistration.md`; the short version:

**Added here**: `protocol-registered-v1.json`, `registered-facts-v1.json` (what
`scripts/analysis/plan_cell_read.py` reads against), `analysis-recipe-v1.json`, and eight registered plan
documents -- `generation`, `fit`, `twin-generation`, `twin-fit`, `smoke-generation`, `smoke-fit`,
`twin-smoke-generation`, `twin-smoke-fit`. Added outside: the preregistration note, the campaign plans
`configs/campaign/slurp-native-stage3-delta-cell-r01-v1.json` and `...-r01-twin-v1.json`, eight unconsumed
exposure-ledger rows, and the runbooks `scripts/flights/batch/cell1_repin_{smoke,arm,twin_smoke,twin}.sh`,
`cell1_flip_all.sh` and `batch_chain_cell1.sh`.

**Repaired** (each measured, not assumed):

1. The six non-prepared-supply `PENDING_<CELL>_OWN_<KEY>` tokens were filled. `core.config.compose` raises
   `preparation_source_receipts must be a non-empty list` on a PENDING string, so the claim above that the re-pin
   mints them was wrong for six of the seven: neither `core.flight.cli check` nor `scripts/flights/repin_cell.py`
   could reach the preparation step. Every filled value except `native_contact_fit` is cell PLAN's own byte for
   byte; `native_contact_fit` carries this cell's own fit identity and endpoint ceiling.
2. `prepared_phase_supply` was **removed** from the four baselines rather than left as a token:
   `core.flight.repin.ArtifactPin.from_mapping` refuses a string pin before `ensure_artifact_pinned` can mint the
   real one. Removal is the cell-P0 form; the flip mints each cell's own pin and its readiness requirement.
3. `populations` was added to the experiment fragment (cell PLAN's own inlined 1,080 ids); without it the SLURP
   adapter refuses every cell with `runtime SLURP TRAIN samples require an explicit registered population`.
4. The two four-row smoke cells moved into their own fragment
   `configs/experiment/slurp-native-stage3-delta-cell-smoke-4-v1.json`, because
   `rails.adapters.runtime_view.registered_population_ids` resolves exactly one selection per dataset fragment and
   a 1,080-row arm and a four-row smoke therefore cannot share one. The arm fragment keeps four cells: the arm,
   the twin and their two fit identities.
5. `preserve_wire_responses: true` was added to both fragments, as every plan-family fragment carries it.
6. The two smoke FIT identities (`...-SMOKE-4-FIT-V1`, `...-SMOKE-4-TWIN-FIT-V1`) are named by the smoke
   baselines' `native_contact_fit` and declared by no cell -- cell PLAN's own form -- and each carries its own
   registered plan document and its own unconsumed exposure row.
7. The four baselines' `knowledge_stores.stage3-deltas.snapshot.sha256` was corrected from the `snapshot.json`
   **file** digest to the snapshot's **content** hash (`1d55f441...` for the store, `d393bbbb...` for the twin).
   `rails.knowledge_stores` checks `KnowledgeSnapshot.content_hash()` and `release["snapshot_sha256"]` against
   that pin and otherwise refuses with `knowledge store stage3-deltas snapshot SHA-256 mismatch`; S3-5's
   `cell1-fill-values.json` supplied the file digest. The release pin is unchanged -- it *is* the file digest.

**The store as released** (counts read model-free from the snapshot; no statement text): 379 values, node targets
perception 119 / solver 151 / reviewer 95 / planner 14, delta kinds slot-contract 147 / intent-boundary 117 /
reviewer-criterion 95 / planner-rule 13 / exemplar-note 5 / perception-hint 2, 223 source sample ids, mean
statement 84.0 characters, longest 126. The twin holds all of it except facet attachment. **Under store
revision v1r (below) the facet count is 39, not the 97 this pass measured**; every other number here is
unchanged.

**Numbers a plan-based cell inherits**: 1,080 rows x the 11-contact program ceiling = 11,880 generation calls;
47,520 FIT endpoints; 33,930 repeated speech seconds; 12.0 fit-inclusive GPU hours; 6,480 native task-contract
calls; one official complete score per arm. Each four-row smoke: 44 / 176 / 117 / 1.0 / 24 / 0. Cell PLAN's own
realised cost on this roster was 4,424 contacts, 8,353.2 prefilled tokens per row and 1.7579 GPU hours per 1,080.

## S3-5 revision v1r: the facet rule (2026-09-23)

Still **HELD**. Nothing in this section authorises a flight, a flip or an admission entry.

The released `stage3-deltas-v1` store was **mostly unreachable**, which the CELL-1 registration
measured and registered as an expectation (`supply_reach` above) rather than repaired. The
coordinator ruled it a defect to fix before contact: flying a cell on an inert supply is the
cell B9a-rec failure repeated on purpose.

A candidate-bound route (`rails/knowledge_stores.py::_stage3_delta_local_supply` ->
`rails/stage3_delta_supply.py::select_stage3_delta_values`) selects a value only when one of its
`associated_facet_ids` **equals** one of the row's Perception candidate **intent** ids. S3-5's
curator wrote `associated_facet_ids = [TARGET]`, and `TARGET` is a **slot type** on the 147
slot-contract rows. Against the 60 registered candidate intents: solver **11 of 151**, reviewer
24 of 95, planner 6 of 14, **121 of 379** overall.

**The revision changes the facet rule and nothing else.**
`scripts/build_slurp_stage3_delta_store.py --facet-rule source-intent` (the new schema-v2
default) writes the ordered, de-duplicated union of the construction **gold intent id** of every
source row (`--gold-intents`, owner decision 82 -- a routing key over the *construction*
population only, exactly as `slot-contracts`, `intent-boundaries` and `train-exemplars` already
carry TRAIN intent ids) and the bare `TARGET` when `TARGET` is itself a legal intent id
(`--intent-vocabulary`). A slot type never becomes a facet. `--facet-rule target-only` keeps the
pre-v1r rule and is proven byte-identical (`3d2bc069...` / `c548b8df...`).

| | v1 | v1r |
| --- | --- | --- |
| values, node targets, delta kinds, source sample ids, statement lengths | unchanged | unchanged |
| distinct facets | 97 (slot types, generic words) | **39, every one a legal intent id** |
| facet entries per row | 379 x 1 | 357 x 1, 21 x 2, 1 x 3 (402 entries) |
| reachable, solver | 11 of 151 | **151 of 151** |
| reachable, reviewer / planner / perception | 24 / 6 / 80 | **95 / 14 / 119** |
| reachable, total (arm and twin) | 121 of 379 | **379 of 379** |
| twin token count | held | held (5,740) |
| twin per-row facet-count multiset | n/a (all 1) | **held** |
| twin value fixed points | 0 | 16 of 379 (arithmetic; 39 intents over 379 rows) |

**The twin.** A row may now carry more than one facet, so both derangements move a row's whole
attachment **as one unit** -- the entire `associated_facet_ids` tuple for the candidate-bound
group, and for the unconditional group the donor's `TARGET` field together with the donor's whole
tuple. A permutation of whole tuples preserves the multiset, so the token count and the new
per-row facet-count multiset are held exactly; both are enforced in the builder and proven in
`tests/unit/test_stage3_delta_twin_v2.py`. On a `target-only` document the donor's tuple *is*
`[donor_target]`, so the v1 twin's bytes are unaffected.

**The reach step.** `scripts/flights/batch/adv1_to_deltas_steps.py reach` is the model-free
supply-reach measurement -- per node, the values carrying at least one facet inside the
registered intent vocabulary, plus the per-intent facet histogram (counts and ids only). It
reproduces the registered v1 figures exactly, and the runbook's new step **R** writes it into the
release-pins document.

**The runbook.** `DELTA_VERSION_TAG` (default `v1`) parametrises every artifact, namespace and
registration name; `DELTA_FACET_RULE` / `DELTA_GOLD_INTENTS` / `DELTA_INTENT_CATALOG` pass
through; step **F** re-points the fragments by JSON path once no `PENDING_` token is left.
`cell1-values` now emits the snapshot's **content** hash (read from `release.json`, cross-checked
against `snapshot.json`) where the fragment pin belongs, so commit `fb4d8915`'s defect cannot
recur.

Version 1's namespaces, prepared documents and release registrations are **untouched**; it is
superseded in English by `stage3-deltas-v1-superseded-v1.md` in this package, which also carries
every v1 and v1r digest side by side. Version 1 was never consumed: all eight exposure rows read
`consumed = no`, readiness is `held` on all six cells, no decision receipt exists and nothing
reached the batch queue.
