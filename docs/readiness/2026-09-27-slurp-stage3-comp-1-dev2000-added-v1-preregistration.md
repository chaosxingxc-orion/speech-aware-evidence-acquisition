# Cell COMP-1 on DEV-2000-ADDED: preregistration

Registered 2026-09-27 at study commit `09f1b31e`, before any contact, from the sealed DEV-2000-ADDED
plan arm fragments by script (decision 58) with cell COMP-1's three composed factors, under owner decision 161 (with 138
and 152). Development numbers only (owner decisions 28 and 86); never a test claim.

**The declared expectation is a placeholder until the coordinator fills it** from the COMP-1 Fold A read (decision 139:
no if-then on unread results). The two places: `docs/readiness/2026-09-27-slurp-stage3-comp-1-dev2000-added-v1/registered-facts-v1.json`
(`stage3_measurement.SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1.expected_effect_pp`) and the fence below.

## The cell

| item | value |
| --- | --- |
| base | the sealed DEV-2000-ADDED plan arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-DEV2000-ADDED-V1` (65.4 / 76.6, docs/results/2026-09-22-slurp-b6-dev2000-added-direct-vs-plan-read.md) |
| composition | cell COMP-1's composed plan with only the roster moved: the locked v2.0 plan as the sealed DEV-2000-ADDED plan arm flew it + (1) the agreement term as AGREE carries it (w_agree 1.0 over the exemplar-intent vote, recall k 60, delivered 8-1-8; the vote table is this roster's own SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1) + (2) the centroid boundary key as KPROBE pins it (facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) + (3) the citation contract (policy phase-native-candidates-review-revise-cited-v1, Solver response_format_id saea-solver-cited-answer-v1, instruction probes/slurp_native_role_solver_cited_v1.txt, deliver_normaliser saea-deliver-cited-answer-normalise-v3-v1) + (4) nothing else |
| roster | `docs/receipts/rosters/slurp-dev-2000-added-v1.json`, split identity `ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67`, split role dev, 1,000 rows / 913 utterances |
| in-chain replicate | `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1`: the DEV plan arm's own bytes at recall k 60 in the SAME chain; prepared output digest `d57ee9d6212bd3dc10762f84ec6ff1e8368b0b1a1e80fed9f9fbc81147fc5a19` verified |
| margins | the plan's own null on this roster: h_intent 1.1520, h_SLU 1.2525 (docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d) |
| scorer | `slurp-slu-official` (DEV sibling) |
| smoke | the roster's first four rows (ROLL-3's smoke rows), split identity `fee83441e514473dc4ab798f8554882bc5753c7fc4924eda0e72c7af7ed51ef0`, never scored |
| runs | `SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1` / `SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-SMOKE-4-FIT-V1` |
| composed config hashes | arm `4f544523febc8b01e788bd246b3c23dd270fac21f98e230db0bb5dcc71634ba2`; A/A `71462277daeea3f0c9b08c1f099b64fd79949a3f8659177013756871ecac7dd3`; smoke `eda8affdb54e1c61e552af4e6f7b3457fcfa6382d190fe3f146f809dc97e805a` |
| protocol hashes | arm `79c6da8e291152b27ef8ad1426a7428c5fd17dc60480970faca73549268d7a62`; A/A `5bc29d22e2fa75481cfe3ff9158fbe1e6388657a7f57de83fac2446bee18488c`; smoke `1d91efb82053c665c022f3cb365e2d587ce02d45415bbcb7a324aec5d4f5ef40` |
| read | `SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-PAIRED-ANALYSIS-V1` via `scripts/flights/read_paired_cell.sh`, analysis root `analysis/SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-PAIRED-ANALYSIS-V1` |

## Knowledge exclusion

size-pool-annotated-exemplars, the PARENT TRAIN-built pool the sealed DEV plan arm, PLANr-DEV2000, CELL-3 and ROLL-3 all read (docs/readiness/2026-09-26-slurp-stage3-roll-3-dev2000-added-v1/registered-facts-v1.json train_exemplars_store): disjoint from every DEV-2000-ADDED recording by the roster receipt's disjointness_proof (shared_with_train_construction_recordings = 0, non_devel_ids_added = 0). Agreement table: its vote pool is the same train-exemplars snapshot (vote_snapshot_sha256 4c498dc0282055b9fe036ed7e950af519bd48b5f26e76876d0250727196a72e9); the builder's utterance-identity self-exclusion MEASURED self_excluded_exemplars = 0 and rows_with_a_self_excluded_exemplar = 0 over all 1,000 rows (prepared/SAEA-SLURP-INTENT-EXEMPLAR-AGREEMENT-DEV2000-ADDED-V1/receipt.json). Centroid keys: built from the R01-excluded construction-TRAIN pool (knowledge/slurp/saea-kb-distmodel-v1/size-pool-annotated-exemplars-minus-r01/snapshot.json, 8,554 TRAIN utterances), whose receipt states the one file is held out on TRAIN Fold A, ROLL-1 (R01C) and DEV-2000-ADDED alike (prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/receipt.json construction.construction_pool); a subset of the TRAIN pool above, so the same disjointness proof covers it.

## Decision rule (fixed here)

Read against the IN-CHAIN A/A, never against the sealed DEV plan arm alone (instrument rules 3 and 4). PRIMARY: intent accuracy (scenario_action exact), paired, utterance-clustered (913 utterances), 10,000 bootstrap draws. GUARD: official pooled SLU-F1 (slurp-slu-official) non-inferior at the plan's own null on this roster (h_SLU 1.2525). REPLICATED: the intent CI95 lower bound above zero AND the guard holds AND the declared expected_effect_pp was on the record before the seal. NEUTRAL: both metrics inside the own null (h_intent 1.1520 / h_SLU 1.2525) without a replicated gain -- read under decision 138 as a conflict diagnosis, never 'no gain'. HARMFUL: a measured loss on either metric (decision 25). The citation part is never reported as a gain.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The A/A replicate is the INSTRUMENT, not a claim: the sealed DEV plan arm's own bytes (w_agree 0.0, the written key, the un-armed citation default, recall k 60, a proven no-op: its prepared output digest is the sealed comparator's d57ee9d6...) re-flown in the same chain. Its expected effect is zero by construction.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
      "replicate_run_id": "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1",
      "rows": 1000
    },
    "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else. Scored by no one, read by no one; under the instrument's rule 5 a batch of four rows can never be evidence of benefit.",
      "primary_metric": "intent accuracy (scenario_action exact)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-COMP1-DEV2000-ADDED-V1": {
      "claims_benefit": true,
      "expected_effect_pp": "TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ",
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The DEV-2000-ADDED replication of cell COMP-1 (owner decision 161; docs/results/2026-09-27-verdict-reclassification.md -- this round settles AGREE's KEEP-PROVISIONAL), read against the in-chain A/A at intent primary with official SLU-F1 the guard, at the plan's own null on this roster (h_intent 1.1520, h_SLU 1.2525; docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d). expected_effect_pp is DELIBERATELY the literal string TO-BE-DECLARED-BY-COORDINATOR-FROM-THE-COMP-1-FOLD-A-READ: owner decision 139 forbids an if-then on unread results and the COMP-1 Fold A arm has not flown. Until the coordinator replaces the string with a number here AND in the preregistration fence, scripts/checks/stage3_effect_floor_check.py refuses this cell as unparsable-declaration -- the intended state, exactly as COMP-1 Fold A was registered. Delivery is not correctness.",
      "own_null": {
        "h_intent": 1.152,
        "h_slu": 1.2525,
        "n": 1000,
        "source": "docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md section 2d, row 'cross-flight A/A, DEV-2000-ADDED' (the B6 pair)"
      },
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 (slurp-slu-official, DEV sibling) the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-COMP1-AA-DEV2000-ADDED-V1",
      "roster": "DEV-2000-ADDED (SLURP-DEV-2000-ADDED-V1, split identity ee6c43cd4dd8fc2a583d2dd053e799c2d002efa3755fcd092ba7c7565431bf67)",
      "rows": 1000
    }
  }
}
```

## Budgets and failure rule

Per generation cell: 11000 generation calls (run-cumulative), 44000 FIT endpoints,
32819 repeated speech seconds, 12.0 GPU hours, one official complete score. The smoke:
44 / 176 / 90 s, no score. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.

## Prohibitions

- No flight before the coordinator declares expected_effect_pp in both places, root countersigns the rows, mints the decision receipt and all three cells are flipped.
- No re-flying of the sealed DEV plan arm; no test-split, DEV-1000 or Fold B contact or read.
- No fourth factor; no k, tau, fuse_coverage, w_prior, store, release, snapshot or roster change beyond the registered roster move.
- The citation part may never be reported as a gain (decision 127).
- No paper-scale profile. --allow-output-change is never passed.
