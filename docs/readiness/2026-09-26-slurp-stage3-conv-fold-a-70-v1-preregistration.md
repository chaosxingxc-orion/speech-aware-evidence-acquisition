# Cell CONV: preregistration

Registered 2026-09-26 at study commit `c6ced983`, before any contact, from the
registered AGREE arm's own fragments by script (decision 58). Development numbers only (owner
decisions 28 and 86); never a test claim.

## The cell

| item | value |
| --- | --- |
| question | Of the 70 TRAIN Fold A rows whose own gold intent's boundary entry cell AGREE newly delivers, how many move from a wrong intent to the gold intent? |
| treatment | the registered AGREE arm's, unchanged in every knob: `w_agree` 1.0, `w_cos` 1.0, `w_prior` 0.0, `k` 60, `tau` 0.0, `fuse_coverage` m 8 / c 1 / top_l 8, the same pinned agreement table |
| changed | the population (70 derived ids instead of 1,080) and the ceilings rescaled to it. Nothing else. |
| comparator | `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1`, sealed, already flown, never re-flown, not in this campaign. Intent-**wrong** on all 70 rows. |
| in-chain replicate | none, and none is owed: the design is `form-proof`, no cross-flight contrast is computed, and the comparator's per-row verdict is constant on this population |
| runs | `SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1` / `SAEA-SLURP-STAGE3-CONV-FOLD-A-70-FIT-V1` |
| rows | 70 |
| composed config hash | `54bd45ee5b42066541695fe9cafff1113972a2ed7cb9ecb23ed6e53a4c2e56e4` |
| protocol hash | `905b58b72681b47032553eeef97589b78d397aa4c3fa1afd7828212ad4567baa` |
| split identity | `57c6f278d8ab35dafa0f1183938c13b6084a4f3d9d9438cfb3e55bbf73ff335c` |
| id-list sha256 | `5920bd6c99d1d5935881c0ca85c8454c7ec8eed096d950b7242c0ec7d8fbf73b` |
| authority | the committed replication receipt `docs/readiness/2026-09-26-slurp-stage3-agree-w1-fold-a-v1/production-replication-v1.json` (sha256 `7cd1f6d338731ea7b6eef34408e5d37453c852670900319445968ddc2a1dc624`); docs/results/2026-09-26-slurp-intent-retrieval-rank-diagnostic.md; docs/readiness/2026-09-26-slurp-stage3-measurement-instrument-v1.md (rule 5); docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md; docs/results/2026-09-24-slurp-plan-bad-case-bank.md; owner decisions 28, 86 and 101 |

## The read rule (fixed here)

There is no verdict and no admission. m = the count of the 70 rows whose official
`scenario_action_exact` is true and whose comparator verdict is not. The deliverable is
`P(correct | newly delivered)` = m / 70 with a Wilson score CI95 and the exact Clopper-Pearson
interval beside it, plus the reverse count -- **zero by construction**, because every comparator
verdict on this roster is wrong; a non-zero reverse count means the roster or the comparator was
misread and closes the read. Reported beside it: the flown delivery check against the offline
derivation's 70, and the split of the stay-wrong rows into byte-identical versus a different
wrong intent.

Multiplying the rate by the class's registered per-row headroom re-declares the AGREE arm's
expectation: m x 0.041615 pp SLU-F1 and m x 0.092615 pp intent accuracy, equivalently
2.9131 pp x m / 70. The arm clears its own 2.5 pp bar at n = 1,080 only if **m >= 61**.

## The measurement declaration

```json
{
  "stage3_measurement": {
    "SAEA-SLURP-STAGE3-CONV-FOLD-A-70-V1": {
      "claims_benefit": false,
      "expected_effect_pp": 0.0,
      "measurement_design": "form-proof",
      "note": "The cell measures a CONDITIONAL RATE and makes NO effectiveness claim. Its 70 rows are under the measurement instrument's MIN_BENEFIT_ROWS, so under rule 5 this is a form proof by size and claims_benefit is false; expected_effect_pp is 0.0 because the cell registers no effect to look for. What it delivers is the AGREE arm's unmeasured persuasion factor, measured: of the rows whose gold intent's boundary entry the agreement term newly delivers, the proportion that move from a wrong intent to the gold intent. Multiplying that proportion by the registered per-row headroom of the class the gain lands on gives the AGREE arm's re-declared expectation. It is NOT an admission request: no admission mode is declared, no harm margin is claimed, and no pooled or roster-level number may ever be read off this cell, whose population was selected with gold, offline.",
      "primary_metric": "per-row intent correctness (official scorer's scenario_action_exact), reported as the conditional rate P(correct | newly delivered) with a binomial CI95",
      "rows": 70
    }
  }
}
```

`70` rows is under the instrument's `MIN_BENEFIT_ROWS` of 200, so rule 5 makes this a form proof
by size: `form-proof`, `claims_benefit` false, `expected_effect_pp` 0.0. **No `admission` mode is
declared** -- `no-harm` is owner decision 127's mode for a base item being admitted, and this cell
asks for no admission at all.

## What the roster is, and what selecting it with gold costs

THE ROSTER IS SELECTED USING GOLD, OFFLINE. The bad-case bank's plan_class and each row's gold intent were read on the scoring side only, in the committed roster derivation, before this cell existed. That is legitimate for a CONDITIONAL estimate on a TRAIN roster and it is legitimate for nothing else: NO POOLED OR ROSTER-LEVEL CLAIM MAY EVER BE MADE FROM THIS CELL, because its population was chosen by the mechanism's own effect. Gold reaches no query, no key, no weight, no selector and no runtime, and no gold label, intent name, transcript or utterance text is printed or persisted anywhere in this package.

This cell reads ONE quantity: the per-row intent verdict on a gold-selected subset. It may never be reported as a pooled SLU-F1 or intent-accuracy effect, as an admission, as a replication, or as evidence about any roster. Its population is the mechanism's own beneficiaries; a pooled number computed over it would be a selection artefact by construction. The cell also cannot see harm: every row here is already intent-wrong in the comparator, so the rows where the mechanism could COST a correct intent are outside this roster and remain the AGREE arm's own question.

The roster is reconstructed, not read off the receipt: the committed replication receipt carries the
count and no ids, so `scripts/analysis/slurp_intent_agreement_conversion_roster.py` imports that
receipt's own recipe byte-unchanged and proves the reconstruction by reproducing every count,
histogram and digest the receipt committed for this arm at this width -- 0 differences -- before a
single id is taken.

## Why intent, not SLU-F1

The within-flight null (docs/results/2026-09-24-slurp-stage3-roll-aa-within-flight-null-read.md) measured 0 intent flips out of 200 request-identical rows, so an intent flip is ATTRIBUTABLE rather than noise and a per-row intent read is legible at n = 70. Pooled SLU-F1 is not: its own measured noise would swamp 70 rows, and the official SLU-F1 is entity-only while this mechanism acts on the intent. The official scorer still produces the number -- the read takes its per-sample scenario_action_exact field and nothing else -- so the standard-scoring rule is intact.

## Budgets and failure rule

770 generation contacts (run-cumulative; 70 x the program's own 11-contact
ceiling), 3080 FIT endpoints, 1899 repeated
speech seconds, 1.0 GPU hour, one official complete score. Expected spend about
352 contacts and about 0.24 GPU hours at the sealed arm's own realized
rate. Stop and preserve on the first failure. AT MOST ONE root-diagnosed recovery re-registration; a
second failure closes the cell and the fix is proven on a four-row dry run.

## Prohibitions

No pooled, roster-level, effectiveness, superiority or generalisation claim from this cell, ever. No
admission entry and no admission mode. No paper-scale profile. No confirmatory or test-split
contact. No Fold B or DEV read. No re-flying of the sealed comparator. No second factor and no knob
change. No store rebuild or release. No flight before root mints the decision receipt and the cell
is flipped, and `--allow-output-change` is never passed.
