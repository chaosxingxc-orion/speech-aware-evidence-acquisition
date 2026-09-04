# Dataset information audit -- earnings21-original

Schema `saea-carrier-information-audit-v1`. Task kind `entity-recall-conec`. Knowledge source: per-call ConEC context/participant-names/bias-list documents (self-supplied, no shared corpus). Retrieval mode `self_supplied_membership`. Seed `20260903`. Construction units: 43. Zero model, GPU, scorer, embedding, or network contact.

## Q1: fields and corpus structures

| field | legality |
|---|---|
| ConEC context document (evidence_source=conec-contexts) | runtime-legal-input |
| ConEC participant-names roster (evidence_source=conec-names) | runtime-legal-input |
| ConEC-derived bias list (evidence_source=conec-bias-list) | runtime-legal-input |
| entity mention filler text (token join of a wer_tags span) | gold-scoring-only |
| reference transcript tokens (.nlp) | forbidden |
| sample_id / media_relpath / audio_seconds / sample_rate_hz | runtime-legal-input |
| wer_tags entity id -> entity_type sidecar | gold-scoring-only |

| corpus structure | legality |
|---|---|
| call 4320211 (pre-existing wer_tags sidecar defect: entity id 1057 has no usable entity_type; excluded from entity-mention rows, n=43 of 44) | gold-scoring-only |
| earnings21-original confirmatory remainder (beyond the 44-call discovery split) | forbidden |
| one ConEC evidence document per call (no shared corpus) | runtime-legal-input |

## Q2: task information requirement (OBS / ORG / SUPPLY / USE)

- **OBS**: Transcribe/segment the earnings-call speech into entity-bearing spans, ASR-free at the knowledge layer.
- **ORG**: No cross-call retrieval: ConEC ships one context/names/bias-list document PER call, so organization here is selecting WHICH of the three self-supplied documents (or their extraction) to expose, not ranking across a corpus.
- **SUPPLY**: Expose the call's own ConEC context, names roster, and/or extracted bias-list terms as evidence.
- **USE**: The frozen core produces a transcript hypothesis whose entity spans are scored against wer_tags gold.

## Q3: natural population distribution and roster deviation

Strata key: `call_id`. Natural (construction) distribution:

| stratum | count | share |
|---|---:|---:|
| 4330115 | 1 | 2.33% |
| 4341191 | 1 | 2.33% |
| 4344338 | 1 | 2.33% |
| 4344866 | 1 | 2.33% |
| 4346818 | 1 | 2.33% |
| 4346923 | 1 | 2.33% |
| 4359732 | 1 | 2.33% |
| 4359971 | 1 | 2.33% |
| 4360366 | 1 | 2.33% |
| 4360674 | 1 | 2.33% |
| 4360717 | 1 | 2.33% |
| 4361631 | 1 | 2.33% |
| 4363614 | 1 | 2.33% |
| 4364366 | 1 | 2.33% |
| 4365024 | 1 | 2.33% |
| 4365948 | 1 | 2.33% |
| 4366302 | 1 | 2.33% |
| 4366429 | 1 | 2.33% |
| 4366522 | 1 | 2.33% |
| 4366893 | 1 | 2.33% |
| 4367318 | 1 | 2.33% |
| 4367535 | 1 | 2.33% |
| 4368670 | 1 | 2.33% |
| 4374910 | 1 | 2.33% |
| 4375653 | 1 | 2.33% |
| 4382825 | 1 | 2.33% |
| 4383161 | 1 | 2.33% |
| 4384198 | 1 | 2.33% |
| 4384683 | 1 | 2.33% |
| 4384744 | 1 | 2.33% |
| 4384964 | 1 | 2.33% |
| 4385072 | 1 | 2.33% |
| 4385388 | 1 | 2.33% |
| 4385939 | 1 | 2.33% |
| 4386541 | 1 | 2.33% |
| 4387332 | 1 | 2.33% |
| 4387383 | 1 | 2.33% |
| 4387865 | 1 | 2.33% |
| 4389907 | 1 | 2.33% |
| 4392809 | 1 | 2.33% |
| 4394084 | 1 | 2.33% |
| 4397800 | 1 | 2.33% |
| 4397829 | 1 | 2.33% |

**discovery-44** (`discovery`, intended n=44): TVD from natural = 1.0000, TVD from uniform allocation = 0.0000, classification = **near-equal-stratum**. Census, not a sample: every earnings21-original discovery-split call is both the knowledge source and the evaluation roster (module docstring); strata are call ids, so the natural distribution is uniform by construction

## Q4: label-space entropy and prior-mass coverage

**entity_type**: 26 of 26 labels observed, 37471 occurrences, entropy 3.448 bits (effective 10.92 labels).

| mass threshold | minimum k |
|---|---:|
| 0.50 | 3 |
| 0.80 | 8 |
| 0.90 | 10 |
| 0.95 | 12 |
| 0.99 | 17 |
| 1.00 | 26 |

**entity_mention**: 7328 of 7328 labels observed, 37471 occurrences, entropy 10.129 bits (effective 1119.99 labels).

| mass threshold | minimum k |
|---|---:|
| 0.50 | 124 |
| 0.80 | 1380 |
| 0.90 | 3581 |
| 0.95 | 5455 |
| 0.99 | 6954 |
| 1.00 | 7328 |

## Q5: retrieval reachability

Self-supplied own-call-vs-random-other-call membership over 43 calls, 37469 gold entity mentions.

Own-context reachability: **30.17%**. Random-other-context reachability (negative control): **16.50%**.

| entity type | mentions | own-context | random-other-context |
|---|---:|---:|---:|
| ABBREVIATION | 2323 | 61.82% | 27.08% |
| ALPHANUMERIC | 996 | 24.40% | 10.34% |
| CARDINAL | 5133 | 44.63% | 38.24% |
| CONTRACTION | 9008 | 0.53% | 0.72% |
| DATE | 6342 | 17.63% | 13.69% |
| EVENT | 263 | 24.33% | 21.67% |
| FAC | 38 | 5.26% | 0.00% |
| FALLBACK | 65 | 0.00% | 0.00% |
| GPE | 1254 | 64.43% | 23.84% |
| LANGUAGE | 2 | 50.00% | 0.00% |
| LAW | 23 | 17.39% | 0.00% |
| LOC | 298 | 45.64% | 8.05% |
| MONEY | 1867 | 34.92% | 32.46% |
| NORP | 207 | 58.94% | 9.18% |
| ORDINAL | 911 | 72.34% | 56.42% |
| ORG | 2847 | 52.93% | 14.44% |
| PERCENT | 1684 | 7.07% | 5.88% |
| PERSON | 2163 | 75.91% | 13.45% |
| PRODUCT | 209 | 39.71% | 6.22% |
| QUANTITY | 149 | 8.72% | 2.68% |
| RANGE | 13 | 0.00% | 0.00% |
| TIME | 433 | 4.16% | 0.92% |
| TWITTER | 2 | 0.00% | 0.00% |
| WEBSITE | 50 | 0.00% | 0.00% |
| WORK_OF_ART | 25 | 12.00% | 0.00% |
| YEAR | 1164 | 28.78% | 18.38% |

## Q6: decontamination

| roster | construction n | roster n | identity overlap | clean |
|---|---:|---:|---:|---|
| discovery-44 | 43 | 44 | 43 | False |

Cross-call near-duplicate audit (token-set Jaccard >= 0.8): 0 of 903 pairs.

## Q7: external supplementation ledger

| need | source | legality |
|---|---|---|
| Company/ticker/person canonical spellings beyond what one call's own ConEC document lists | Another call's ConEC document (explicitly a NEGATIVE-CONTROL / cross-contamination risk, not a legal supply) | forbidden |
| A budget-bounded distillation of the raw ConEC context to fit prompt budgets | core.bias_lists.extract_bias_candidates / reconstruct_bias_phrases over the SAME call's own context | runtime-legal-input |

## Q8: power

Two-sided alpha=0.05, target power=0.8. Historical discordant-pair rate citations:

| citation | n | discordant rate | source |
|---|---:|---:|---|
| DEV-500 confirmatory (400 unexposed) | 400 | 20.75% | docs/readiness/2026-08-24-dev500-confirmatory-verdict.md |
| DEV-1000 baseline lock (500 unexposed) | 500 | 22.20% | docs/readiness/2026-08-25-baseline-lock-verdict.md |

| n (roster/segment) | citation | minimum detectable effect (pp) |
|---|---|---:|
| discovery-44 | DEV-500 confirmatory (400 unexposed) | 19.24 |
| discovery-44 | DEV-1000 baseline lock (500 unexposed) | 19.90 |

