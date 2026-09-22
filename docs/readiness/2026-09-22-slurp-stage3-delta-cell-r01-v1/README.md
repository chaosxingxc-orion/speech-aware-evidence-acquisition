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

## Engineering delivered here

- `rails/stage3_delta_supply.py`: the candidate-bound, prior_score-capped selection algorithm
  (`select_stage3_delta_values`, `DeltaCandidate`, `stage3_delta_selection_receipt`), fully tested on
  synthetic fixtures (`tests/unit/test_stage3_delta_supply.py`).
- `rails.knowledge_provider.Stage3DeltaCandidateProvider`, registered into `core.base.KNOWLEDGE_PROVIDERS`
  under `stage3-delta-candidate-bound-v1` (`rails/knowledge_provider.py`, the canonical registration
  site `scripts/checks/engineering_base_check.py` requires): a real, tested `KnowledgeProvider`
  (`build`/`candidates`/`fuse`) wrapping the selection algorithm, so the config fragments' `"provider":
  "stage3-delta-candidate-bound-v1"` resolves honestly today. It is NOT YET reachable from a live
  flight -- see the scope decision below.
- `scripts/build_slurp_stage3_delta_twin.py`: a seeded, zero-fixed-point derangement of
  `associated_facet_ids` over an authored-deltas document (Sattolo's algorithm, the same idiom as the
  B1/IDXT twins), tested (`tests/unit/test_stage3_delta_supply.py`).
- Four baseline fragments (`configs/baseline/slurp-native-stage3-delta-cell-*-v1.json`: generation,
  twin, and their four-row smokes), each the locked PLAN fragment plus exactly one added store; proof
  test `tests/unit/test_stage3_delta_cell_fragment.py`.
- One experiment fragment (`configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json`) carrying
  six held cells: generation, twin, both fits, both four-row smokes (run ids
  `SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1`, `-TWIN-V1`, `-R01-FIT-V1`, `-TWIN-FIT-V1`,
  `-SMOKE-4-V1`, `-SMOKE-4-TWIN-V1`).

## Root wiring: DONE (S3-6w, 2026-09-22)

The spec's own prose names `context_supply` as the routing field, and separately says the store
should use "the same candidate-bound routing the slot-contracts store uses". The S3-6w follow-up
extended `rails.knowledge_stores.build_knowledge_store_supply`'s `context_supply` dispatcher to
recognise a SECOND provider shape alongside the pre-existing source-scoped one:

- The pre-existing shape (`set(raw_spec) == {"provider"}`, the source-scoped provider) is completely
  unchanged -- byte-identical construction, byte-identical routing, byte-identical receipts, proven by
  `tests/unit/test_stage3_delta_supply_router.py::
  test_existing_two_admitted_routes_stay_byte_identical_when_stage3_deltas_is_added` alongside the
  full existing `test_knowledge_stores*.py` / `test_candidate_semantic_supply.py` suites (223 tests,
  all green after this change).
- A store with `store_role: "stage3-deltas"` may now declare `context_supply.<phase> = {"provider":
  "stage3-delta-candidate-bound-v1", "candidate_state_phase", "cap", "rank_by": "prior_score"}` --
  exactly the shape the fragments below already carried. The router reads the row's Perception
  candidate intents off the `candidate_state_phase` state (`rails.slurp_intent_hypotheses.
  parse_slurp_intent_hypothesis_state`, canonical/non-compact form), then routes them through the
  registered `rails.knowledge_provider.Stage3DeltaCandidateProvider`
  (`rails.stage3_delta_supply.select_stage3_delta_values` does the actual selection): candidate-bound,
  capped, `prior_score`-ranked, deterministic.
- The router's E3b collision guard (rule 1: scoped `context_supply` and `candidate_supply` never
  coexist on one phase) is narrowed the SAME way E3b narrowed the phase_supply/candidate_supply
  guard: only for phases a store routes through the STAGE3_DELTA provider specifically. The
  source-scoped provider keeps refusing that overlap exactly as before. This is what lets this
  program's anchor pairing -- `stage3-deltas` `context_supply.solver` alongside `slot-contracts`
  `candidate_supply.solver` -- compose in one `automatic_for_phase` call.

`candidate_supply`'s own two-role, round-robin dispatcher (`rails.candidate_semantic_supply.
load_candidate_semantic_supply_specs`) was left untouched -- the stage3-deltas route lives entirely in
`context_supply`, never inside `candidate_supply`.

## What is left for root (PENDING_ placeholders)

- `PENDING_S3_5_RELEASE_SHA256`: S3-5's release of `knowledge/slurp/semantic/stage3-deltas-v1/`.
- `PENDING_S3_6_TWIN_RELEASE_SHA256`: the twin release of `knowledge/slurp/semantic/stage3-deltas-twin-v1/`,
  built by `scripts/build_slurp_stage3_delta_twin.py` from the S3-5 release once it exists.
- `PENDING_ROOT_WIRING` (in `configs/experiment/slurp-native-stage3-delta-cell-r01-v1.json`'s held
  requirements): RESOLVED by S3-6w -- `rails/knowledge_stores.py` now recognises the provider; this
  requirement entry stays until the experiment fragment itself is next touched, since only the store's
  own release and a root admission decision still block a flight.
- `PENDING_<CELL>_OWN_<KEY>` (per cell): the per-flight bookkeeping (`native_contact_fit`,
  `prepared_phase_supply`, `preparation_source_receipts`, speech-feature identity ids,
  `speech_packet_promotion_receipt[_sha256]`) this cell must prepare under its OWN run id before
  flight (owner rule E16: a prepared artifact is evidence only for the implementation that produced
  it) -- never PLAN's own pins, even though the bytes may turn out identical.
- `PENDING_S3_1_*` / `PENDING_ROOT_DECISION_ID` / `PENDING_ROOT_SELECTION`: the same S3-1 roster and
  root-admission dependencies the S3-4 and S3-2 packages name.

## Proof obligations covered by tests

- `tests/unit/test_stage3_delta_supply.py`: candidate-bound selection, prior_score ordering, the cap,
  empty-match returns `()` never raises, the receipt carries no content, the twin derangement has zero
  fixed points, preserves every non-facet field, and is deterministic for a fixed seed.
- `tests/unit/test_stage3_delta_cell_fragment.py`: the generation cell equals the locked PLAN fragment
  on every key except the one added store and the per-flight bookkeeping keys; the twin cell equals the
  generation cell except the release namespace; every pin left for root is an explicit `PENDING_`
  token; the smoke variants carry the same store shape as their full siblings.
