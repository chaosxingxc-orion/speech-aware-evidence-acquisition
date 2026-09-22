# Readiness package: SAEA-SLURP-STAGE3-DELTA-CELL-R01-V1

Status: **HELD**. This package registers the engineering for Stage-3 S3-6 (CELL-1: the locked plan
plus the stage3-deltas store) -- it does not authorize a flight, a readiness flip, or an admission
entry. Source spec: `docs/superpowers/specs/2026-09-22-stage3-tfrl-base-loop-engineering.md` section
S3-6.

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

## A documented scope decision: routing is NOT wired into the live dispatcher

The spec's own prose names `context_supply` as the routing field, and separately says the store
should use "the same candidate-bound routing the slot-contracts store uses" (which is actually
`candidate_supply` in this codebase). Reading the live code
(`src/speech_aware_evidence_acquisition/rails/knowledge_stores.py`
`build_knowledge_store_supply`, `src/speech_aware_evidence_acquisition/rails/
candidate_semantic_supply.py` `load_candidate_semantic_supply_specs`) on 2026-09-22 found that:

- `context_supply` accepts EXACTLY one provider today (the source-scoped one, no candidate-binding, no
  cap) -- `set(raw_spec) != {"provider"}` refuses any richer shape outright.
- `candidate_supply` IS candidate-bound and capped, but is hard-coded to exactly two store roles
  (`slot-contracts`, `parameter-meaning`) and selects by per-candidate round-robin, not a flat top-N by
  `prior_score`.

Extending either dispatcher to a third store role is real surgery to shared code two ADMITTED stores
route through today, on a live campaign this package must never touch (port 8080). It cannot be
integration-tested against a real flight here (flying is out of scope), and the store it would route
has no release yet (every pin below is `PENDING_`). Rather than land unverified surgery on shared,
campaign-critical code, this package delivers the full, tested SELECTION ALGORITHM
(`rails/stage3_delta_supply.py`) and leaves the wiring -- either a `context_supply` provider allowlist
extension or a third `candidate_supply` role -- as a named root follow-up. The fragments' `context_supply.solver`
shape (`{provider: "stage3-delta-candidate-bound-v1", candidate_state_phase, cap, rank_by}`) documents
the INTENDED shape for that follow-up to resolve.

## What is left for root (PENDING_ placeholders)

- `PENDING_S3_5_RELEASE_SHA256`: S3-5's release of `knowledge/slurp/semantic/stage3-deltas-v1/`.
- `PENDING_S3_6_TWIN_RELEASE_SHA256`: the twin release of `knowledge/slurp/semantic/stage3-deltas-twin-v1/`,
  built by `scripts/build_slurp_stage3_delta_twin.py` from the S3-5 release once it exists.
- `PENDING_ROOT_WIRING`: the `rails/knowledge_stores.py` extension described above. The provider
  class itself is registered and tested (`rails.knowledge_provider.Stage3DeltaCandidateProvider`);
  only the ROUTER's allowlist (`context_supply`/`candidate_supply` dispatch) does not recognize it yet.
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
