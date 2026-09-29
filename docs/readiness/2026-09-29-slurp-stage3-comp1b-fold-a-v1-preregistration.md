# Cell COMP-1b: preregistration

Registered 2026-09-29 at study commit `e42e87f3e`, before any contact, from cell COMP-1's
own committed, already-flown fragments (decision 58: script-derived registrations) by reverting the citation
contract alone. Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| base | cell COMP-1's own committed arm `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` (61.97 SLU / 86.11 intent) |
| composition | AGREE + centroid key alone, COMP-1's own bytes, byte for byte; the citation contract reverted to the locked plan's non-cited program |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores' pins, exemplar k = 20, role graph, the Perception / Reviewer / Planner templates, scorers, budgets, the whole boundary channel |
| comparator | `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`, sealed, REUSED cross-flight, never re-flown (owner decision 160's shared-A/A pattern) |
| margins | the plan's own null on this roster (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1` / `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-FIT-V1` |
| composed config hashes | arm `4b8a8c58b451dde3ba13e78ac951ef1cadb019f8c62e48025b39cfd9436b100f`; smoke `fd070bce9d89f8297620261ceb7cf104169f15ef77c1e184473968f4a02b92a1` |
| protocol hashes | arm `e3f7a70a1e1c1dab01f8e18c31429e23665db42c842c97226101c3f47dfe938d`; smoke `f0bdc735256c564195c9db48e12ee8ebe376717b9dcf4c9b56b0801f6144fb65` |
| authority | the 2026-09-29 SLU-harm attribution note (branch fable/comp1slu commit e30aa1b61, docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md) and the COMP-1 read it explains (docs/results/2026-09-29-slurp-comp1-fold-a-read.md); owner decisions 138 and 152 (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md); the AGREE registration docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1; the KPROBE registration docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1; the instrument docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md; decisions 25 (harm), 127, 133, 139, 160, 190 (item D3) |

## Decision rule (fixed here)

Read against the SAME sealed in-chain A/A cell COMP-1 used, reused cross-flight and never re-flown (owner decision 160's shared-A/A pattern). PRIMARY: intent accuracy (scenario_action exact), paired per row, 10,000 bootstrap draws. GUARD: official pooled SLU-F1 non-inferior at the plan's own null (h_SLU 1.2485). ADMITTED: the intent CI95 lower bound above zero, the point at or above the declared 4.26 pp and the 2.5 pp cross-flight bar, AND the guard holds. NEUTRAL: both guards non-inferior at the own null (h_intent 0.9943 / h_SLU 1.2485) without an admitted gain. HARMFUL: a measured loss on either guard (decision 25). Every verdict carries the per-channel table the attribution note (a) / (b) / (c) split uses, the per-stratum tables in both weightings, and the same-shortlist intent-choice check.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-SMOKE-4-V1": {
      "claim": "nominated",
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: the agreement table and the centroid key file load and hash-verify, the boundary channel still delivers eight entries, the Solver answers under the locked plan's own non-cited program and every request fits and the episode completes. Scored by no one, read by no one; under the instrument's rule 5 a batch of four rows can never be evidence of benefit.",
      "primary_metric": "intent accuracy (scenario_action exact)",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "rows": 4,
      "tuning_roster": "none"
    },
    "SAEA-SLURP-STAGE3-COMP1B-FOLD-A-V1": {
      "claim": "nominated",
      "claims_benefit": true,
      "expected_effect_pp": 4.26,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "COMP-1 minus the citation contract (2026-09-29 SLU-harm attribution, branch fable/comp1slu commit e30aa1b61): the agreement term and the centroid boundary key alone, COMP-1's own committed bytes, read against the SAME sealed in-chain A/A SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1 COMP-1 used (reused cross-flight, never re-flown -- decision 160's shared-A/A pattern, as cell G5 reused it). expected_effect_pp 4.26 is the measured COMP-1-vs-A/A intent delta from docs/results/2026-09-29-slurp-comp1-fold-a-read.md (CI95 [+2.41, +6.11]); the attribution note shows the citation contract does not move the Solver's intent choice on identical shortlists (COMP-1 vs A/A: 170 identical shortlists, 166 vs 166 rank-1 picks) and adds 0 entities on the unwrap side, so removing it is not expected to move the intent gain. The SLU-F1 guard is the SAME Fold A own null h_SLU 1.2485 COMP-1's own rule used; the attribution note's whole point is that this guard should now HOLD (COMP-1's own loss, -2.24 [-3.97, -0.47], is attributed entirely to the removed citation contract's zero-gold over-emission, +102 FP of the +114 total). tuning_roster and read_roster are declared under item D3 (owner decision 190, 2026-09-29): the agreement table and the centroid key were each built from a TRAIN construction pool disjoint from Fold A recordings by construction (the agreement table self-excludes the row's own utterance identity; the centroid key is the R01-excluded construction-pool mean), and their conversion probes (CONV, KPROBE) were read on Fold A subsets; this cell reads the composed effect on the whole Fold A roster, the same circularity COMP-1's own read already carries and discloses. No disjointness receipt for the construction pool is committed yet, so the tuning/read overlap check is expected to report tuning-roster-unverified, advisory.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
      "primary_metric_key": "intent",
      "read_roster": "SLURP-EVO-FOLD-A-V2",
      "replicate_run_id": "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1",
      "rows": 1080,
      "tuning_roster": "slurp-train-construction-pool-agree-kprobe-r01-excluded"
    }
  }
}
```

## Where the declared 4.26 pp comes from

The measured COMP-1-vs-A/A intent delta, docs/results/2026-09-29-slurp-comp1-fold-a-read.md: +4.26 pp CI95 [+2.41, +6.11]. The 2026-09-29 attribution note
(docs/results/2026-09-29-slurp-comp1-slu-harm-attribution.md, branch fable/comp1slu) shows the citation contract does not move the Solver's intent
choice on identical Perception shortlists (170 of 1,080 rows identical between COMP-1 and its A/A; only 6 differ, 166
vs 166 rank-1 picks) and that the extra intent harms track the supply's changed shortlist, not the contract; removing
the contract is therefore not expected to move the intent gain. The 2.5 pp cross-flight bar at n = 1,080 is cleared.
DELIVERY IS NOT CORRECTNESS; this is a prediction to be tested, not a foregone conclusion.

## Budgets and failure rule

Per generation cell: 11880 generation calls (run-cumulative), 47520 FIT endpoints,
33930 repeated speech seconds, 12.0 GPU hours, one official complete score. The smoke:
44 / 176 / 117 s, no score. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.

## Prohibitions

- No flight before root mints the decision receipt and both cells are flipped.
- No re-flying of the sealed comparator (the in-chain A/A) or the sealed PLAN arm; no test-split, Fold B or DEV contact or read.
- No re-introducing the citation contract; no k, tau, fuse_coverage, w_prior, store, release, snapshot or roster change; no re-pin of the 213 committed configs.
- No paper-scale profile. --allow-output-change is never passed.
