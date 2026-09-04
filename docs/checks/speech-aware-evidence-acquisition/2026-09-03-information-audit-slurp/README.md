# Dataset information audit -- slurp

Schema `saea-carrier-information-audit-v1`. Task kind `slot-slu`. Knowledge source: SLURP train split (SlurpTrainMaterial): sentence text + scenario/action/entity_types. Retrieval mode `grouped_bm25`. Seed `20260903`. Construction units: 11514. Zero model, GPU, scorer, embedding, or network contact.

## Q1: fields and corpus structures

| field | legality |
|---|---|
| action | gold-scoring-only |
| audio_seconds | runtime-legal-input |
| devel/test sentence text | forbidden |
| entities (type + filler span) | gold-scoring-only |
| intent (scenario_action) | gold-scoring-only |
| sample_id / utterance_id / media_relpath | runtime-legal-input |
| scenario | runtime-legal-input |
| train sentence text (SlurpTrainMaterial.sentence) | construction-only-knowledge |
| train speaker_id | construction-only-knowledge |

| corpus structure | legality |
|---|---|
| test split | forbidden |
| train_synthetic split | forbidden |
| utterance (one or more recordings sharing one sentence/scenario/action/entities) | construction-only-knowledge |

## Q2: task information requirement (OBS / ORG / SUPPLY / USE)

- **OBS**: Perceive the spoken command from AUDIO only (SlurpRecord carries no sentence field at runtime); recover scenario/action/entity-bearing spans without a reference transcript.
- **ORG**: Multi-dimensional key retrieval (content/speaker/label/prior) over the TRAIN-modeled knowledge base; a ranking policy fuses dimensions -- Q-K-V doctrine, owner ruling 2026-08-23 section 1.
- **SUPPLY**: Consume retrieved TRAIN-derived value cards (scenario/action exemplars, entity-type fillers) as priors, sample-linked, never embedded as ground truth.
- **USE**: The frozen core commits to one scenario_action intent and a set of (type, filler) entity slots per utterance.

## Q3: natural population distribution and roster deviation

Strata key: `scenario`. Natural (construction) distribution:

| stratum | count | share |
|---|---:|---:|
| alarm | 390 | 3.39% |
| audio | 290 | 2.52% |
| calendar | 1688 | 14.66% |
| cooking | 211 | 1.83% |
| datetime | 402 | 3.49% |
| email | 953 | 8.28% |
| general | 652 | 5.66% |
| iot | 769 | 6.68% |
| lists | 539 | 4.68% |
| music | 332 | 2.88% |
| news | 503 | 4.37% |
| play | 1377 | 11.96% |
| qa | 1183 | 10.27% |
| recommendation | 433 | 3.76% |
| social | 391 | 3.40% |
| takeaway | 257 | 2.23% |
| transport | 571 | 4.96% |
| weather | 573 | 4.98% |

**dev-ladder-dev100** (`dev`, intended n=100): TVD from natural = 0.2385, TVD from uniform allocation = 0.0444, classification = **near-equal-stratum**. Scenario-stratified over the 18 devel scenarios, as evenly as the eligible pool allows (capacity-aware water-filling apportionment: a stratum smaller than the current fair share is taken WHOLE and the shortfall is redistributed across the remaining strata; the final round splits any remainder one-each in ascending scenario-name order, since every remaining stratum's fair share is numerically identical at that point). Within a scenario, the utterances are drawn via random.Random(f'{seed}:{stage}:{scenario}').sample over the id-sorted eligible pool (mirrors reproduction.sampling.stratified_sample's own per-stratum seeding convention). One recording per selected utterance is resolved via random.Random(f'{seed}:{scenario}:{utterance_id}') over the utterance's id-sorted recordings, mirroring the historic probe-60 receipt's own selection_rule convention. DEV-500 and DEV-100 are drawn the SAME way but over DEV-1000's (respectively DEV-500's) own per-scenario selected utterance lists as the eligible pool, rather than the original devel pool, so each tier is an exact seeded SUBSET of the tier above it.

**dev-ladder-dev500** (`dev`, intended n=500): TVD from natural = 0.2391, TVD from uniform allocation = 0.0062, classification = **near-equal-stratum**. Scenario-stratified over the 18 devel scenarios, as evenly as the eligible pool allows (capacity-aware water-filling apportionment: a stratum smaller than the current fair share is taken WHOLE and the shortfall is redistributed across the remaining strata; the final round splits any remainder one-each in ascending scenario-name order, since every remaining stratum's fair share is numerically identical at that point). Within a scenario, the utterances are drawn via random.Random(f'{seed}:{stage}:{scenario}').sample over the id-sorted eligible pool (mirrors reproduction.sampling.stratified_sample's own per-stratum seeding convention). One recording per selected utterance is resolved via random.Random(f'{seed}:{scenario}:{utterance_id}') over the utterance's id-sorted recordings, mirroring the historic probe-60 receipt's own selection_rule convention. DEV-500 and DEV-100 are drawn the SAME way but over DEV-1000's (respectively DEV-500's) own per-scenario selected utterance lists as the eligible pool, rather than the original devel pool, so each tier is an exact seeded SUBSET of the tier above it.

**dev-ladder-dev1000** (`dev`, intended n=1000): TVD from natural = 0.2155, TVD from uniform allocation = 0.0652, classification = **near-equal-stratum**. Scenario-stratified over the 18 devel scenarios, as evenly as the eligible pool allows (capacity-aware water-filling apportionment: a stratum smaller than the current fair share is taken WHOLE and the shortfall is redistributed across the remaining strata; the final round splits any remainder one-each in ascending scenario-name order, since every remaining stratum's fair share is numerically identical at that point). Within a scenario, the utterances are drawn via random.Random(f'{seed}:{stage}:{scenario}').sample over the id-sorted eligible pool (mirrors reproduction.sampling.stratified_sample's own per-stratum seeding convention). One recording per selected utterance is resolved via random.Random(f'{seed}:{scenario}:{utterance_id}') over the utterance's id-sorted recordings, mirroring the historic probe-60 receipt's own selection_rule convention. DEV-500 and DEV-100 are drawn the SAME way but over DEV-1000's (respectively DEV-500's) own per-scenario selected utterance lists as the eligible pool, rather than the original devel pool, so each tier is an exact seeded SUBSET of the tier above it.

## Q4: label-space entropy and prior-mass coverage

**intent**: 60 of 60 labels observed, 11514 occurrences, entropy 5.412 bits (effective 42.57 labels).

| mass threshold | minimum k |
|---|---:|
| 0.50 | 12 |
| 0.80 | 31 |
| 0.90 | 40 |
| 0.95 | 47 |
| 0.99 | 55 |
| 1.00 | 60 |

**entity_type**: 55 of 55 labels observed, 10974 occurrences, entropy 4.643 bits (effective 24.99 labels).

| mass threshold | minimum k |
|---|---:|
| 0.50 | 6 |
| 0.80 | 18 |
| 0.90 | 26 |
| 0.95 | 33 |
| 0.99 | 43 |
| 1.00 | 55 |

## Q5: retrieval reachability

Label-blind grouped 5-fold BM25 coverage over 115 registered labels, 11514 scored units.

| k | full-set coverage | label recall | mean distractors | worst-fold full-set |
|---:|---:|---:|---:|---:|
| 5 | 79.80% | 87.11% | 3.30 | 78.72% |
| 16 | 94.30% | 96.66% | 14.11 | 93.92% |
| 32 | 97.64% | 98.69% | 30.07 | 97.09% |
| 64 | 99.17% | 99.53% | 62.06 | 98.83% |

## Q6: decontamination

| roster | construction n | roster n | identity overlap | clean |
|---|---:|---:|---:|---|
| dev-ladder-dev100 | 11514 | 100 | 0 | True |
| dev-ladder-dev500 | 11514 | 500 | 0 | True |
| dev-ladder-dev1000 | 11514 | 1000 | 0 | True |

## Q7: external supplementation ledger

| need | source | legality |
|---|---|---|
| A user/domain ontology of legal scenario/action/entity-type names | data.slurp.load_slurp_ontology (mined from train only, include_synthetic=False) | construction-only-knowledge |
| Entity-type example fillers for value-card construction | The KB build (slurp-kb-distmodel-v1) TRAIN-modeled datastore, decontaminated vs devel/test | construction-only-knowledge |
| A larger action-support pool for long-tail scenarios/entities | The T500 train-side discovery tier (approved in principle, 2026-08-23 ruling section 2) | construction-only-knowledge |

## Q8: power

Two-sided alpha=0.05, target power=0.8. Historical discordant-pair rate citations:

| citation | n | discordant rate | source |
|---|---:|---:|---|
| DEV-500 confirmatory (400 unexposed) | 400 | 20.75% | docs/readiness/2026-08-24-dev500-confirmatory-verdict.md |
| DEV-1000 baseline lock (500 unexposed) | 500 | 22.20% | docs/readiness/2026-08-25-baseline-lock-verdict.md |

| n (roster/segment) | citation | minimum detectable effect (pp) |
|---|---|---:|
| dev-ladder-dev100 | DEV-500 confirmatory (400 unexposed) | 12.76 |
| dev-ladder-dev100 | DEV-1000 baseline lock (500 unexposed) | 13.20 |
| dev-ladder-dev1000 | DEV-500 confirmatory (400 unexposed) | 4.04 |
| dev-ladder-dev1000 | DEV-1000 baseline lock (500 unexposed) | 4.17 |
| dev-ladder-dev500 | DEV-500 confirmatory (400 unexposed) | 5.71 |
| dev-ladder-dev500 | DEV-1000 baseline lock (500 unexposed) | 5.90 |

