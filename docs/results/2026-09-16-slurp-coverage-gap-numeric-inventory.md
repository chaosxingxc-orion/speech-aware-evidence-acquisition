# SLURP released three-arm numeric inventory

Date: 2026-09-16. Root performed and verified this model-free join.

Reuse only released complete TRAIN A sources. No current typed-context pair quality, raw answers, gold transcripts, Fold B or new scoring was read. This is descriptive cross-run evidence, not an additional causal experiment.

Join all 1,080 sample identities in the same order across saved candidate diagnostics and saved official score projections. Verify every intent-exact field and previously published category total. There are 125 speakers and 18 scenarios, each with 60 samples.

| Arm | Candidate missing | Covered, intent wrong | Intent correct, entities nonexact | Intent and entities exact |
| --- | ---: | ---: | ---: | ---: |
| anchor | 143 | 95 | 525 | 317 |
| broad_factored | 133 | 106 | 540 | 301 |
| maximum_five | 129 | 114 | 519 | 318 |

Exact entities means zero saved entity FP and FN. The projection omits the parsed flag; this is not an independent parser-validity check. These counts are not the official pooled SLU metric.

## Persistent categories across all three runs

- candidate_missing: 100 / 1080.
- covered_intent_wrong: 60 / 1080.
- intent_and_entities_exact: 232 / 1080.
- intent_correct_entities_nonexact: 426 / 1080.

## Paired coverage transitions

| Pair | Retained | Gained | Lost | Neither | Common correct intent | Entity-exact on common, first / second |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| anchor__broad_factored | 917 | 30 | 20 | 113 | 807 | 303 / 293 |
| anchor__maximum_five | 932 | 19 | 5 | 124 | 817 | 305 / 314 |
| maximum_five__broad_factored | 921 | 26 | 30 | 103 | 799 | 306 / 287 |

## All scenario strata

Each cell is missing / covered-wrong / correct-intent-entity-nonexact / intent-and-entity-exact. Natural sample and equal-scenario weighting coincide for these counts because strata are balanced. Pooled F1 remains distinct from mean sample F1.

| Scenario | Anchor | Maximum five | Broad/factored | Persistent missing | Persistent correct-intent entity error |
| --- | --- | --- | --- | ---: | ---: |
| alarm | 2/8/31/19 | 2/9/29/20 | 2/8/30/20 | 0 | 22 |
| audio | 5/9/11/35 | 4/10/9/37 | 7/8/22/23 | 4 | 8 |
| calendar | 11/4/33/12 | 10/6/34/10 | 8/9/32/11 | 6 | 27 |
| cooking | 5/4/30/21 | 4/4/30/22 | 4/6/25/25 | 3 | 23 |
| datetime | 3/7/32/18 | 1/8/33/18 | 4/5/31/20 | 1 | 30 |
| email | 7/2/38/13 | 7/1/35/17 | 6/2/37/15 | 6 | 32 |
| general | 34/4/10/12 | 35/5/8/12 | 33/5/8/14 | 28 | 6 |
| iot | 3/5/35/17 | 2/5/34/19 | 3/6/31/20 | 2 | 29 |
| lists | 9/1/26/24 | 9/1/25/25 | 7/1/28/24 | 6 | 22 |
| music | 8/6/21/25 | 5/11/18/26 | 8/8/16/28 | 5 | 10 |
| news | 10/2/24/24 | 8/3/29/20 | 10/2/30/18 | 7 | 21 |
| play | 7/18/27/8 | 6/18/30/6 | 8/13/34/5 | 5 | 23 |
| qa | 13/2/25/20 | 13/2/24/21 | 9/4/27/20 | 9 | 22 |
| recommendation | 3/3/33/21 | 3/6/35/16 | 2/6/37/15 | 2 | 26 |
| social | 11/9/35/5 | 11/9/32/8 | 9/10/35/6 | 9 | 30 |
| takeaway | 5/4/37/14 | 4/7/37/12 | 5/5/39/11 | 3 | 30 |
| transport | 3/5/38/14 | 2/7/37/14 | 4/6/35/15 | 1 | 30 |
| weather | 4/2/39/15 | 3/2/40/15 | 4/2/43/11 | 3 | 35 |

## Root interpretation

One hundred samples remain candidate-missing across all three runs. Four hundred twenty-six retain correct intent but nonexact entities across all three. These intersections identify stable diagnostic priorities; they are not automatically recoverable gains. Expanding the candidate limit and broadening/factoring knowledge did not eliminate either failure class. Diagnose the required distinctions and their consumption, and preserve useful incumbent candidates when testing any future augmentation. Do not rerun the closed breadth treatments merely to seek a pass.

Gold intent names, ordered candidate labels/ranks, false competing labels and parsed flags are unavailable in the saved projections. Do not infer them. Source hashes, all rows and the deterministic extraction script remain outside Git.

Output: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-COVERAGE-GAP-DIAGNOSTICS-TRAIN-A-V1/numeric-inventory-v1.json
SHA-256: 31a6ac3c6d25da2eda13cbbc5006fdb102ac0fd71fc25597889ff35abe2d4558

Authorization: docs/readiness/2026-09-16-slurp-offline-coverage-and-resolution-diagnosis-v1.md.
