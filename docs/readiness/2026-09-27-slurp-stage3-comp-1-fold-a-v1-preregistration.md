# Cell COMP-1: preregistration

Registered 2026-09-27 at study commit `8d403ffa`, before any contact, from the sealed cell PLAN
fragments by script (decision 58) with the agreement term, the centroid boundary key and the citation contract
composed, under owner decisions 138 and 152. Development numbers only (owner decisions 28 and 86); never a test
claim.

**The declared expectation is a placeholder until the coordinator fills it** (decision 139: no prior; decision 152:
composed from the AGREE and KPROBE reads). The two places: `docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/registered-facts-v1.json`
(`stage3_measurement.SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1.expected_effect_pp`) and the fence below. The effect-floor gate refuses the arm
until both carry a number; that is intended.

## The cell

| item | value |
| --- | --- |
| base | the locked v2.0 plan, the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` (63.6304 / 82.2222) |
| composition | the locked v2.0 plan + (1) the agreement term as AGREE carries it (w_agree 1.0 over the self-excluded exemplar-intent vote, recall k 60, delivered 8-1-8) + (2) the centroid boundary key as KPROBE pins it (facet_source prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl) + (3) the citation contract (policy phase-native-candidates-review-revise-cited-v1, Solver response_format_id saea-solver-cited-answer-v1, instruction probes/slurp_native_role_solver_cited_v1.txt, deliver_normaliser saea-deliver-cited-answer-normalise-v3-v1) + (4) nothing else |
| unchanged | roster (TRAIN Fold A 1,080), geometry (np4 x 24,576), session, program and its 11-contact ceiling, all three stores' pins, exemplar k = 20, role graph, the Perception / Reviewer / Planner templates, scorers, budgets |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, sealed, never re-flown |
| in-chain replicate | `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1`: the locked plan's own bytes (w_agree 0.0, written key, un-armed citation default, recall k 60 -- a proven no-op) re-flown in the SAME campaign chain; prepared output digest `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f` verified |
| margins | the plan's own null on this roster (PLANr): h_SLU 1.2485, h_intent 0.9943 |
| smoke | four engineering rows, structural acceptance, never scored |
| runs | `SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1` / `SAEA-SLURP-STAGE3-COMP1-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1` / `SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-FIT-V1`; `SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1` / `SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-FIT-V1` |
| composed config hashes | arm `45f56c899b7ef67f9cb5b03620a9b187530b8ce21eeb6c7b3ca13abe2f49cecd`; A/A `e1baf39fa0a7258687b38b214bf2879a78cbb3af3487bd13579fbb5b1d55df78`; smoke `acfab83e4b75590053452bc5e325e2612022973e39cab75c080cf3e2d101ac95` |
| protocol hashes | arm `64e56899bdb852c3f76108b78b4f80c44a7d83667bc547a0fcf5839ac722c8ce`; A/A `f734266c7907464e9806d1cb2a0781a5d9b4bd0af42f1b30e7470ca832611330`; smoke `4bce171c405c098173cb626e22a75475d049c805df9ae5f0d927822e18b688bf` |
| prepared supplies (own, E16) | arm `prepared/SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1/phase-supply-v1.json` output `ce68bebcf2bbf5502b081221a92c3fde1095da3979106bcdddb6eeeca9e9c41a`; A/A `prepared/SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1/phase-supply-v1.json` output `ba5e1faab9550fcae700f649a0ec6674327ffefe97d7044bb7ea3887536fb54f`; smoke output `1d55ea73ae0ef4ef2d175e66303eaa5b500c7fc2a3ac356f3808686deba051e0` |
| authority | owner decisions 138 and 152 (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md); the AGREE registration docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1 and the CONV read docs/results/2026-09-27-slurp-conv-probe-read.md; the KPROBE registration docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1; the two diagnostics docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md and docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md; the instrument docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md; the class headroom of docs/results/2026-09-24-slurp-plan-bad-case-bank.md; decisions 127 (no-harm base items), 133 (intent primary), 139 (no prior), 101 (the Stage-3 label) |

## Decision rule (fixed here)

Read against the IN-CHAIN A/A, never against the sealed comparator alone (instrument rules 3 and 4). PRIMARY: intent accuracy (scenario_action exact), paired per row, 10,000 bootstrap draws. GUARD: official pooled SLU-F1 non-inferior at the plan's own null (h_SLU 1.2485). ADMITTED: the intent CI95 lower bound above zero AND the guard holds AND the declared expected_effect_pp was declared before the seal. NEUTRAL: both guards non-inferior at the own null (h_intent 0.9943 / h_SLU 1.2485) without an admitted gain -- read under owner decision 138 as a CONFLICT DIAGNOSIS over the per-class attribution table, never as 'no gain'; no further element is admitted on top of an unresolved conflict. HARMFUL: a measured loss on either guard (decision 25). The citation part (decision 152) is admitted on the composed arm's own no-harm reading and is never reported as a gain. Every verdict carries the per-class attribution table with each row's outcome, the per-stratum tables in both weightings, the frontier row, the delivery check and the token delta.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The A/A replicate is the INSTRUMENT, not a claim: it re-flies the locked plan's own bytes (w_agree 0.0, the written key, the un-armed citation default, recall k 60 which is a proven no-op) so the composed delta is read against a within-chain null. Its expected effect is exactly zero by construction; a non-zero read on it is a measurement of the instrument.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the guard",
      "replicate_run_id": "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1",
      "rows": 1080
    },
    "SAEA-SLURP-STAGE3-COMP1-FOLD-A-SMOKE-4-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "Four rows prove FORM and nothing else: the agreement table and the centroid key file load and hash-verify, the boundary channel still delivers, the Solver answers under the cited-answer contract and the unwrapping normaliser delivers the answer's own bytes, every request fits and the episode completes. Scored by no one, read by no one; under the instrument's rule 5 a batch of four rows can never be evidence of benefit.",
      "primary_metric": "intent accuracy (scenario_action exact)",
      "rows": 4
    },
    "SAEA-SLURP-STAGE3-COMP1-FOLD-A-V1": {
      "claims_benefit": true,
      "expected_effect_pp": 3.23,
      "measurement_design": "cross-flight-with-in-chain-replicate",
      "note": "The FIRST COMPOSED arm (owner decisions 138 and 152): the locked plan + the agreement term + the centroid boundary key + the citation contract, read against the in-chain A/A at intent primary and official SLU-F1 as the guard. expected_effect_pp is DELIBERATELY the literal string the coordinator-declared value (placeholder until 2026-09-27; declared 3.23 pp from the measured conversions, see expected_effect_declaration): owner decision 139 forbids a prior, and decision 152 says the number is composed by the coordinator from the AGREE and KPROBE reads' measured m values (m_agree = 32 of 70 is read; m_kprobe is pending) over the class table registered here (the two newly-delivered sets overlap on 47 of their 78 rows, so they do not add) at the registered per-row headroom of 0.092615 pp intent. Until the coordinator replaces this string with a number here AND in the preregistration fence, scripts/checks/stage3_effect_floor_check.py refuses this cell as unparsable-declaration -- the intended state. A composed round that fails to improve is read as a CONFLICT DIAGNOSIS over the per-class attribution table, never as a null (decision 138). Delivery is not correctness.",
      "primary_metric": "intent accuracy (scenario_action exact), official pooled SLU-F1 the non-inferiority guard (owner decision 133)",
      "replicate_run_id": "SAEA-SLURP-STAGE3-COMP1-AA-FOLD-A-V1",
      "rows": 1080,
      "expected_effect_declaration": "Declared 2026-09-27 by the coordinator (Claude Opus 5.5) from measured numbers only (owner decision 139): the registered attribution classes put 78 of the 191 PLAN intent-wrong Fold A rows in the newly-delivered classes of the composition (newly by AGREE alone 23, by the centroid key alone 8, by both 47); the measured conversion of a newly delivered gold entry is 32 of 70 for the agreement term (CONV) and 24 of 55 for the centroid key (KPROBE), pooled 56 of 125 = 0.448; 78 x 0.448 = 34.9 rows x 0.092615 pp = 3.23 pp intent. The two newly-delivered sets overlap on 47 rows, so the m values are NOT added. Not counted, stated beside: the agreement term's measured effect on already-delivered rows (35 saves) and its 31 harms, which its own Fold A read nets to +3.33 pp [+1.57, +5.09]; an upper reading of AGREE's realised +3.33 plus the centroid-only increment 8 x 0.4364 x 0.092615 = 0.32 gives 3.65 pp. The citation contract is a no-harm base item (decision 152) and contributes 0. Against the 2.5 pp cross-flight floor at n = 1,080 the declared 3.23 clears it."
    }
  }
}
```

## What the coordinator composes the expectation from

m_agree = 32 of 70 (read, docs/results/2026-09-27-slurp-conv-probe-read.md); m_kprobe pending (docs/readiness/2026-09-27-slurp-stage3-kprobe-fold-a-55-v1); the per-row headroom of the class the gain
lands on, 0.092615 pp intent (0.041615 pp SLU-F1 for the guard); and the four exclusive classes of
`docs/readiness/2026-09-27-slurp-stage3-comp-1-fold-a-v1/attribution-classes-v1.json`: newly-by-agree 23, newly-by-centroid 8,
newly-by-both 47, catch-all 27 (delivered-but-wrong 86). The two newly-delivered sets share
47 of their 78 rows, so m_agree x headroom + m_kprobe x headroom double-counts; the composition delivers the gold
entry on 162 of the 191 intent-wrong rows. The citation part contributes no expected gain (a no-harm base item). The bar at
n = 1,080 is 2.5 pp intent. DELIVERY IS NOT CORRECTNESS.

## Budgets and failure rule

Per generation cell: 11880 generation calls (run-cumulative), 47520 FIT endpoints,
33930 repeated speech seconds, 12.0 GPU hours, one official complete score. The smoke:
44 / 176 / 117 s, no score. The citation contract adds
+134 instruction tokens and +26 (+12.71 per cited id) output tokens per Solver contact and no contacts. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a second failure closes the cell and the fix is proven on a four-row dry run. Budgets are run-cumulative across attempts.

## Prohibitions

- No flight before the coordinator declares expected_effect_pp in both places, root mints the decision receipt and all three cells are flipped.
- No re-flying of the sealed comparator; no test-split, Fold B or DEV contact or read.
- No fourth factor; no k, tau, fuse_coverage, w_prior, store, release, snapshot or roster change; no re-pin of the 211 committed configs.
- The citation part may never be reported as a gain (decision 127); two base items are never assumed to add.
- No paper-scale profile. --allow-output-change is never passed.
