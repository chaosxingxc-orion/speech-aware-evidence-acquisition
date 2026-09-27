# Cell KPROBE: preregistration

Registered 2026-09-27 at study commit `08fd493c`, before any contact, from the locked
PLAN baseline's own fragments by script (decision 58) with one pin moved, under owner decision 145.
Development numbers only (owner decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| question | Of the 55 TRAIN Fold A rows whose own gold intent's boundary entry the centroid key newly delivers, how many move from a wrong intent to the gold intent? |
| treatment | the locked PLAN plan with ONE pin moved: the intent-boundary Perception `facet_source` is `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` (sha256 `16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532`) instead of the written-key file; `k` 8, `fuse_coverage` m 8 / c 1 / top_l 8, `w_cos` 1.0 / `w_prior` 0.0 / `w_agree` 0.0, `tau` 0.0, the same store snapshot and release |
| changed | that pin, the population (55 derived ids instead of 1,080) and the ceilings rescaled to it. Nothing else; the composed diff is in `registered-facts-v1.json`. |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, sealed, already flown, never re-flown, not in this campaign. Intent-**wrong** on all 55 rows. |
| in-chain replicate | none, and none is owed: the design is `form-proof`, no cross-flight contrast is computed, and the comparator's per-row verdict is constant on this population |
| runs | `SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-V1` / `SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-FIT-V1` |
| rows | 55 |
| composed config hash | `94be16b9e1b113e1f29301625c179b2189fca7243e8c27863309ee6e0cc416bd` |
| protocol hash | `be30ff1386801a5ffcbfb9a5c1f4e092e799f197d5b3e2e6984f041f5a6b749d` |
| split identity | `d5fa899db921562b3e98a0c2aba72d8edab1c1885969f0332dce67a623527b31` |
| id-list sha256 | `ad433b1fc3f21765af15d3aed4012264125d9f17fdd4cef837d67bcf50ddde02` |
| key file | `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/facets.jsonl` sha256 `16c33640151cff6428bc50e4f00ced93b35f76fa186b8d08fcefdfdb33fd5532`; receipt `prepared/SAEA-SLURP-INTENT-BOUNDARY-CENTROID-KEYS-V1/receipt.json` sha256 `d5fa43dfb9cfe71402e256c015e5f0a1ce66e97b3ec5355a664eb9f69f8cdf0a` |
| authority | owner decision 145 (docs/readiness/2026-09-16-slurp-next-stage-owner-decisions-v1.md); docs/results/2026-09-27-slurp-boundary-key-construction-diagnostic.md; the CONV precedent docs/readiness/2026-09-26-slurp-stage3-conv-fold-a-70-v1 and docs/results/2026-09-27-slurp-conv-probe-read.md; docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md (rule 5); docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md; docs/results/2026-09-24-slurp-plan-bad-case-bank.md; owner decisions 28, 86, 101, 133 and 134 |

## The read rule (fixed here)

There is no verdict and no admission. **The delivery gate comes first:** the read refuses to produce a
conversion number unless the flown Perception consumption delivered the row's own gold intent boundary value
id on all 55 rows, as the offline derivation predicts; anything less is an engineering defect. Then m = the
count of the 55 rows whose official `scenario_action_exact` is true and whose comparator verdict is not. The
deliverable is `P(correct | newly delivered)` = m / 55 with a Wilson score CI95 and the exact Clopper-Pearson
interval beside it, plus the reverse count -- **zero by construction**, because every comparator verdict on this
roster is wrong; a non-zero reverse count means the roster or the comparator was misread and closes the read.
Reported beside it: the four-way transition split (wrong to gold; gold to wrong; the same wrong intent; a
different wrong intent) and the stay-wrong split (byte-identical answer; same wrong intent in different bytes;
different wrong intent).

Re-declaration rule, stated and not applied: a later 1,080-row construction cell that flies this key declares
`expected_effect_pp` = m x 0.092615 pp intent accuracy (intent primary, owner decision 133; m x
0.041615 pp SLU-F1 for the guard), and clears the 2.5 pp intent bar at n = 1,080 only if
**m >= 27**.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-KPROBE-FOLD-A-55-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The cell measures a CONDITIONAL RATE and makes NO effectiveness claim. Its 55 rows are under the measurement instrument's MIN_BENEFIT_ROWS, so under rule 5 this is a form proof by size and claims_benefit is false; expected_effect_pp is 0.0 because the cell registers no effect to look for. What it delivers is the centroid boundary key's conversion from delivery to correctness, measured: of the rows whose gold intent's boundary entry the key newly delivers, the proportion m/55 that move from a wrong intent to the gold intent. RE-DECLARATION RULE: a later 1,080-row construction cell that flies this key declares expected_effect_pp = m x 0.092615 pp intent accuracy (intent primary under owner decision 133, official SLU-F1 the non-inferiority guard; m x 0.041615 pp SLU-F1 for the guard), never a midpoint. It is NOT an admission request: no admission mode is declared, no harm margin is claimed, and no pooled or roster-level number may ever be read off this cell, whose population was selected with gold, offline.",
      "primary_metric": "per-row intent correctness (official scorer's scenario_action_exact), reported as the conditional rate P(correct | newly delivered) with a binomial CI95",
      "rows": 55
    }
  }
}
```

`55` rows is under the instrument's `MIN_BENEFIT_ROWS` of 200, so rule 5 makes this a form proof by size:
`form-proof`, `claims_benefit` false, `expected_effect_pp` 0.0. **No `admission` mode is declared.**

## What the roster is, and what selecting it with gold costs

THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's plan_class and each row's gold intent were read on the scoring side only, in the committed roster derivation, before this cell existed. That is legitimate for a CONDITIONAL estimate on a TRAIN roster and it is legitimate for nothing else: NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THIS CELL, because its population was chosen by the mechanism's own effect. Gold reaches no query, no key, no weight, no selector and no runtime -- the key itself is built from each pool value's frozen build-time task_target, a store property -- and no gold label, intent name as content, transcript or utterance text is printed or persisted anywhere in this package.

This cell reads ONE quantity: the per-row intent verdict on a gold-selected subset. It may never be reported as a pooled SLU-F1 or intent-accuracy effect, as an admission, as a replication, or as evidence about any roster. Its population is the mechanism's own beneficiaries; a pooled number computed over it would be a selection artefact by construction. The cell also cannot see harm: every row here is already intent-wrong in the comparator, so the rows where the key could COST a correct intent -- including the rows that LOSE their gold entry under the centroid key, counted in the roster derivation -- are outside this roster and remain a construction cell's own question.

The roster is derived from the pinned key FILE through the production path, after three proofs
(`roster-derivation-v1.json`, by `scripts/analysis/slurp_boundary_centroid_conversion_roster.py`): the diagnostic's own arithmetic reproduces its committed
note (0 differences); the file reproduces the diagnostic's R01-excluded centroid through the production recall
and the note's ROLL-1 cells exactly; the production constructor reproduces the sealed delivered set under the
written key on 1,080 / 1,080 rows and derives the same population under the centroid pin as the recall.

## Why intent, not SLU-F1

The within-flight null (docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md) measured 0 intent flips out of 200 request-identical rows, so an intent flip is ATTRIBUTABLE rather than noise and a per-row intent read is legible at this size; cell CONV read the same quantity the same way at n = 70 (docs/results/2026-09-27-slurp-conv-probe-read.md). Pooled SLU-F1 is not legible here: its own measured noise would swamp the roster, and the official SLU-F1 is entity-only while this mechanism acts on the intent. The official scorer still produces the number -- the read takes its per-sample scenario_action_exact field and nothing else -- so the standard-scoring rule is intact.

## Budgets and failure rule

605 generation contacts (run-cumulative; 55 x the program's own 11-contact ceiling),
2420 FIT endpoints, 1405 repeated speech seconds,
1.0 GPU hour, one official complete score. Expected spend about
276 contacts and about 0.19 GPU hours at the
sealed arm's own realized rate. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery
re-registration; a second failure closes the cell and the fix is proven on a four-row dry run.

## Prohibitions

No pooled, roster-level, effectiveness, superiority or generalisation claim from this cell, ever. No admission
entry and no admission mode. No paper-scale profile. No confirmatory or test-split contact. No Fold B or DEV read.
No re-flying of the sealed comparator. No second factor and no knob change. No store rebuild or release; no re-pin
of the 211 committed configs. No flight before root mints the decision receipt and the cell is flipped, and
`--allow-output-change` is never passed.
