# Audio2Tool local-semantic candidate audit

## Decision

Promote the pinned local Qwen3-Embedding signal as a necessary ORG input and
freeze build-only tool-by-tier semantic centroids at top-16 as the bounded
engineering-flight candidate. On the complete 12,601-unit construction
population, the candidate produces a large, stable improvement over BM25. It
passes six of the seven strict retrieval gates and misses the remaining
per-tier gate only on the implicit tier at 89.90%. The strict knowledge-ground
gate remains failed; the engineering candidate is nevertheless eligible for a
baseline consumption flight because the owner explicitly reserves the greater
than 0.90 performance target for after training-free RL, not for baseline
construction. This audit itself opens no runtime model flight.

## Frozen local asset

The audit reuses the already-produced Qwen3-Embedding-0.6B Q8_0 content
vectors. It verifies the tracked receipt, llama.cpp build commit, GGUF hash,
snapshot hash, vector archive hash, all 12,601 facet ids, every exact source
representation, and every per-vector text hash before scoring. The artifact
contains 12,601 vectors of 1,024 dimensions. All 12,601 ids, representations,
and hashes match the current construction partition.

This read makes zero new embedding, frozen-core, network, or scorer contact.
The embedder remains a frozen tool-level retriever; it never has final-answer
authority. The durable source contact is already recorded as
`SAEA-SN-TOOL-A2T-KB-TEXT-EMB-PASS`.

## Method

Use the identical five label-blind grouped folds from the lexical audit
(`assignment_sha256 = 185a42d29340e58e59371226b61f5545f426fd929468544f3cc19f4d5af703d4`).
For each fold, normalize the build vectors, aggregate one centroid for each
observed `(tool, tier)` pair, normalize the centroids, and rank each tool by
its maximum cosine over its build-only tier centroids. Attach every unique
primary and extra-call label to its construction row. Gold labels are read
only after complete rankings exist.

The hybrid uses equal-weight reciprocal-rank fusion with constant 60 over the
complete BM25 and dense tool rankings. It does not concatenate raw scores on
incompatible scales.

## Results

| Method | Full set @5 | Recall @5 | Full set @16 | Recall @16 | Mean distractors @16 |
|---|---:|---:|---:|---:|---:|
| BM25 | 79.50% | 82.99% | 91.95% | 93.56% | 14.83 |
| Dense tool-tier centroids | 88.94% | 90.52% | 96.62% | 97.29% | 14.78 |
| BM25 + dense RRF-60 | 89.93% | 91.82% | 96.43% | 97.14% | 14.79 |
| Dense maximum exemplar | 86.72% | 88.48% | 96.43% | 97.14% | 14.79 |
| BM25 + exemplar RRF-60 | 88.43% | 90.51% | 96.16% | 96.93% | 14.79 |

The semantic contribution is substantial. Relative to BM25, dense improves
full-set coverage by 9.44 percentage points at k=5 and 4.67 points at k=16.
RRF improves k=5 by 10.43 points and k=16 by 4.48 points. At k=16, dense is
better than RRF on aggregate coverage and recall; RRF is better on
multi-intent and blended-intent composition. This is evidence for retaining
both signals, but not evidence that equal-weight RRF is the final combiner.

| Hard subgroup | BM25 @5 | Dense @5 | BM25 @16 | Dense @16 |
|---|---:|---:|---:|---:|
| implicit | 53.76% | 76.17% | 75.26% | 89.90% |
| multiturn | 66.73% | 85.33% | 82.56% | 92.28% |
| multi-call | 67.24% | 73.29% | 92.89% | 95.16% |
| no near duplicate | 79.38% | 88.94% | 91.90% | 96.65% |

The no-near-duplicate result rules out lexical duplicate reuse as the source
of the gain. Dense k=16 is also stable across folds: the fold full-set rates
are 95.56%, 96.83%, 97.06%, 96.66%, and 96.98%, versus BM25's 91.48%,
91.28%, 92.93%, 93.09%, and 90.99%.

## Gate reading and root cause

Dense k=16 passes overall full-set coverage (96.62% >= 95%), label recall
(97.29% >= 97%), mean distractors (14.78 <= 15), worst-fold full-set coverage
(95.56% >= 93%), multi-call full-set coverage (95.16% >= 90%), and
no-near-duplicate full-set coverage (96.65% >= 95%). Every tier except
implicit exceeds 90%; implicit reaches 89.90%. No method is admitted because
the gate was frozen before reading the result and is not rounded or relaxed.

Maximum-cosine exemplars do not close the gap. They reduce aggregate k=16
full-set coverage from the centroid's 96.62% to 96.43%, implicit from 89.90%
to 89.77%, multi-call from 95.16% to 94.44%, and no-near-duplicate from 96.65%
to 96.43%. They improve multiturn from 92.28% to 93.24%, but the net result is
negative. Keep the compact tool-tier centroids; do not carry thousands of
sample exemplars into the runtime retrieval index.

The large semantic main effect diagnoses the primary failure of the preceding
BM25 experiment: the knowledge corpus contains useful operation information,
but the lexical ranker cannot transfer it across desired-state paraphrases and
dialogue wording. The remaining implicit gap can still have two causes:

The exemplar ablation rejects centroid averaging as the primary remaining
cause. The public/construction knowledge lacks discriminative state
transitions and sibling contrasts for a small set of implicit operations.
During the first model-consumption flight, load only the selected top-16
labels' canonical decision cards. If the frozen core still cannot consume the
correct action despite the gold action being retrieved, backtrack to decision
card expansion; if the gold action is absent, backtrack to ORG. This preserves
separate knowledge-construction and knowledge-consumption diagnoses.

## Artifacts

- Machine-readable result: `summary.json`
- Reproduction and receipt verifier: `run_audit.py`
- Dense and hybrid evaluator:
  `src/speech_aware_evidence_acquisition/analysis/a2t_dense_candidate_validation.py`
- Unit tests:
  `tests/unit/test_a2t_dense_candidate_validation.py` and
  `tests/unit/test_a2t_semantic_candidate_runner.py`
