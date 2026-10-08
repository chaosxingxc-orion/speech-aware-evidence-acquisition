# N100 complete system comparison

Recorded at 2026-10-08T02:31:48.551736+00:00. Four systems on the same 100-input prefix of the existing UPDATE2 pool; 400 complete trajectories. This is exploratory optimization data, not independent validation. Root completed the exact family READ after every original seal and unique official score qualified.

**Decision:** retain the seed as formal incumbent. Keep review-off as a lower-cost prospective template-development basis, but do not claim noninferiority or adopt it. Do not promote the unchanged solver-lookup package. No stable system gain or feedback-learning advantage is established.

## Official quality and execution cost

| System | Official SLU-F1 % | Intent % | Completed | Model / tool calls | Mean sample s | Non-first mean s | Dispatch wall min |
|---|---:|---:|---:|---:|---:|---:|---:|
| seed | 62.4395 | 83.0 | 100/100 | 610 / 0 | 32.790 | 32.829 | 13.806 |
| seed-aa | 62.7507 | 86.0 | 100/100 | 592 / 0 | 31.799 | 31.844 | 13.393 |
| review-off | 60.9607 | 87.0 | 100/100 | 200 / 0 | 17.232 | 17.230 | 7.250 |
| solver-lookup | 57.6237 | 84.0 | 100/100 | 216 / 16 | 22.776 | 22.790 | 9.552 |

Mean sample time is admission-to-workflow completion; dispatch wall time reflects four concurrent samples. Neither includes all preparation and official scoring. Non-first samples are not guaranteed warm-cache samples. The campaign ran from 01:20:29 to 02:14:04 UTC (53 min 35 s), including campaign overhead and overlapped scoring.

## Registered paired comparisons

Differences are percentage points. All 10,000 bootstrap draws use seed 20261001, 95% intervals and paired utterance clusters; this panel has 100 clusters. Intervals are exploratory individual comparisons, not simultaneous familywise guarantees.

| Comparison | SLU-F1 difference [95% CI] | Intent difference [95% CI] | Whole-answer repairs / harms |
|---|---:|---:|---:|
| review-off-minus-aa | -1.790 [-6.871, +3.509] | +1.00 [-2.00, +5.00] | 6 / 2 |
| review-off-minus-parent | -1.479 [-5.331, +2.718] | +4.00 [+0.00, +9.00] | 7 / 3 |
| same-request-null | +0.311 [-4.598, +5.277] | +3.00 [+0.00, +7.00] | 5 / 5 |
| solver-lookup-minus-aa | -5.127 [-9.485, -1.038] | -2.00 [-5.00, +0.00] | 3 / 6 |
| solver-lookup-minus-parent | -4.816 [-9.692, +0.042] | +1.00 [-2.00, +4.00] | 3 / 6 |

Review-off is lower-cost but its F1 interval does not prove quality preservation. Lookup is negative against A/A and unresolved against the primary seed; this is not a universal tool-use conclusion. Whole-answer exact correctness and official SLU-F1 have different definitions, so their rankings can differ. A/A itself changes five full answers in each direction despite temperature zero and a fixed seed; one observed A/A interval is not a universal variance estimate.

The point-estimate non-dominated set contains seed-AA and review-off. Seed-AA is a repeated draw of the seed policy, not an optimized policy; keep both original and A/A measurements. No global frontier or best-system claim is made.

## Process evidence and limits

| System | First raw parse | Delivered exact entities | Delivered exact full answer | False fill on gold-empty |
|---|---:|---:|---:|---:|
| seed | 87/100 | 49/100 | 42/100 | 11/34 |
| seed-aa | 90/100 | 51/100 | 42/100 | 10/34 |
| review-off | 100/100 | 52/100 | 46/100 | 10/34 |
| solver-lookup | 100/100 | 46/100 | 39/100 | 12/34 |

For seed and A/A, error alarms detect 32/44 and 29/44 evaluable wrong entity drafts; delivered entity repair after a true alarm is only 1/32 and 2/29. Raw first-to-selected Solver entity states show zero known repairs, with 13 and 10 unknown states. Postprocessing separately repairs 3/54 and 3/52 raw-wrong entities. Do not credit those deterministic repairs to Reviewer. False alarms occur on 17/43 and 19/44 known correct drafts. Valid handoff transmission does not establish semantic use.

Review-off and lookup have no Reviewer by design: review metrics are not applicable, not failed or zero efficacy. Their postprocessing repairs 2/50 and 2/56 raw-wrong entity cases. Lookup has 16 successful tool contacts and no failed/rejected tool event, but the first raw answer already follows within-visit tools; there is no pre-tool quality endpoint for causal tool benefit.

Own-intent cards are present in 98/100 initial requests in every system. Initial candidate coverage is 93/100 for seed, A/A and review-off, and 91/100 for lookup. These are narrow intent-presence measurements. Raw retrieval-pool coverage, entity/value support and semantic consumption remain unmeasured. They support focusing on consumption as a hypothesis, not declaring all knowledge sufficient.

Process statistics above come from separately signed member readers, with full denominators, missingness and Wilson intervals retained in the receipt. The full-family process-derivative field remains `UNAVAILABLE_UNTIL_QUALIFIED_PINNED_DERIVATIVE`; no signed recipe was rewritten to hide this boundary. Zero observed damage does not prove harmlessness.

## Every scenario and equal-stratum reporting

| Scenario (n) | Seed F1 / intent % | A/A F1 / intent % | Review-off F1 / intent % | Lookup F1 / intent % |
|---|---:|---:|---:|---:|
| alarm (5) | 84.21 / 80.00 | 90.00 / 80.00 | 84.21 / 100.00 | 84.21 / 80.00 |
| audio (9) | 66.67 / 55.56 | 66.67 / 66.67 | 66.67 / 66.67 | 36.14 / 66.67 |
| calendar (8) | 59.06 / 100.00 | 59.06 / 100.00 | 59.06 / 100.00 | 59.06 / 100.00 |
| cooking (7) | 66.92 / 71.43 | 66.92 / 71.43 | 56.57 / 57.14 | 56.57 / 57.14 |
| datetime (4) | 66.67 / 100.00 | 66.67 / 100.00 | 56.78 / 100.00 | 56.78 / 100.00 |
| email (3) | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general (8) | 18.18 / 37.50 | 25.00 / 62.50 | 0.00 / 62.50 | 0.00 / 50.00 |
| iot (5) | 50.00 / 100.00 | 80.00 / 100.00 | 80.00 / 100.00 | 50.00 / 100.00 |
| lists (8) | 56.47 / 87.50 | 60.76 / 87.50 | 56.47 / 87.50 | 70.59 / 87.50 |
| music (5) | 0.00 / 80.00 | 0.00 / 80.00 | 0.00 / 80.00 | 0.00 / 80.00 |
| news (5) | 90.91 / 80.00 | 90.91 / 80.00 | 90.91 / 80.00 | 90.91 / 80.00 |
| play (5) | 39.74 / 80.00 | 42.19 / 80.00 | 40.54 / 80.00 | 40.99 / 80.00 |
| qa (5) | 70.03 / 100.00 | 75.42 / 100.00 | 75.42 / 100.00 | 75.42 / 100.00 |
| recommendation (4) | 75.86 / 100.00 | 75.86 / 100.00 | 75.86 / 100.00 | 72.25 / 100.00 |
| social (3) | 58.95 / 66.67 | 51.38 / 66.67 | 51.38 / 100.00 | 58.95 / 66.67 |
| takeaway (5) | 70.82 / 100.00 | 62.02 / 100.00 | 77.24 / 100.00 | 62.02 / 100.00 |
| transport (5) | 58.66 / 100.00 | 46.19 / 100.00 | 44.91 / 100.00 | 37.62 / 100.00 |
| weather (6) | 76.92 / 100.00 | 76.92 / 100.00 | 76.92 / 100.00 | 66.67 / 100.00 |
| Equal-stratum macro | 56.12 / 85.48 | 57.55 / 87.49 | 55.16 / 89.66 | 51.01 / 86.00 |

Each scenario contains only 3-9 inputs. All scenario completion rates are 100%; these small descriptive strata do not establish scenario-specific efficacy.

## Budget correction and terminal engineering incident

The original failed N100 ceiling copied a 1,500-second audio exposure bound that had been adequate at N20. Model-contact caps scaled but audio did not. The corrected rule uses actual roster duration times the maximum legal complete role path. One-pass duration is 293.7795 s; maximum paths are 13/13/2/3 calls per input. Audio caps are 3,820/3,820/1,500/1,500 s and model caps 1,300/1,300/200/300. Smaller architectures retain already adequate registered audio bounds. The new precontact guard rejects under-budget configurations before any model contact. This is cumulative exposure, not wall-clock time.

All four new systems finalized and scored once. The campaign returned zero. Its outer inspector then exited two because the main-tree inspector was called with a frozen repo-root, triggering the strict path guard before any member inspection. Preserve the STOP, original logs and completed frozen checkout. Independent qualification passed all four complete seals and score identities. Repair only the future inspector entrypoint; no rerun, reseal or score replay. The job-scoped monitor was deleted after actual terminal verification.

## Next bounded work

First land the tested future inspector-path correction. Next prepare prospectively versioned short consumption templates, emphasizing valid first answers, empty-entity restraint, explicit evidence boundaries and preservation of already supported fields. A second candidate may test one short actionable correction instead of open-ended reflection. Freeze knowledge, input pool, scorer, Omni authority and deterministic generation settings. Keep the seed and same-chain A/A as anchors; the cheaper architecture is an experimental basis, not a promoted incumbent.

Use the same 100-input panel for the next reviewed four-system comparison. Derive every call/audio bound from configuration and exact roster, retain full-request FIT and structural acceptance, four concurrent samples, continuous serial GPU members and overlapped CPU scoring. Record new proposal/feedback scope before giving aggregates to a learner; this manual family has no learner export and does not modify previously spent candidates. Do not expand to 400 or bypass the human-before-8x400 boundary.

Prioritize official quality, intent, reliable completion, parsing, false fills and repair/harm conversion; latency is a secondary tradeoff. Training-free GRPO/GEPA comparisons still require prospective equal-opportunity learning protocols. Current diagnostics are not evidence of learning. Other-carrier holds remain unchanged.

## Evidence

- Root custody, aggregate metrics and source pins: [complete receipt](../receipts/continuation/2026-10-08-simple-consumption-n100-complete-family-read-v1.json).
- Original failed and successful generations, all official scores and failed outer-inspection evidence remain immutable in DATA.
- Independent Astra Ultra member and whole-family interpretations are source-pinned in the receipt.
