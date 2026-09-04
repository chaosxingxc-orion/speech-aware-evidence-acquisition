# Audio2Tool training-free self-consistency 104 v1 — no targeting signal and no scale

Date: 2026-09-01. Status: **PROSPECTIVE DISCOVERY FAILED; DO NOT SCALE**.
Experiment: `SAEA-A2T-TFRL-SELF-CONSISTENCY-104-V1`. Committed summary:
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-self-consistency-104-v1/result-summary.json`.
The external self-hashed result has file SHA-256
`8527282e110cd11a9d87f0d65d06d55f266e0a27a9bb95d7f7eff3b103266d39` and internal
self-hash `ee7368f2ba0587fa959438a965bea3c604261aad0924dd303837f3f853668b2b`.

## Verdict

Direct same-core self-consistency did not provide a usable targeting signal, and the registered
training-free policy did not improve the frozen single-call baseline. Promotion failed, no
candidate was selected, and this method must not expand to approximately 1,000 samples. The
experiment establishes neither agent-over-single-call superiority nor a positive training-free RL
contribution.

| Arm | Exact match | Tool accuracy | Slot F1 | Parse failures |
| --- | ---: | ---: | ---: | ---: |
| Frozen M0 | 29/104 (27.88%) | 62/104 (59.62%) | 43.79% | 4 |
| `REOBSERVE_DIRECT` | 23/104 (22.12%) | 55/104 (52.88%) | 40.63% | 4 |
| `SUPPLY_UNION_STRIPPED` | 23/104 (22.12%) | 60/104 (57.69%) | 35.69% | 8 |

The re-observation differed byte-for-byte from M0 on 34 samples, so the observation channel was
live. It nevertheless rescued zero M0 failures, harmed six M0 successes, and was neutral on 98
samples. Among the 92 samples with registry-resolved supply, evidence supply rescued four and
harmed ten. The remaining 12 samples were correctly treated as supply-unavailable and forced to
`STOP_M0`.

## Information gain and training-free control

The paired observation state was non-constant, but its rewards were not safely separable. The
coarse `both/exact` cell mixed three saves with seven harms among 74 eligible samples. Its principal
detailed refinement still mixed three saves with seven harms among 64 samples. Other positive
cells either remained mixed or lacked the frozen support and save counts. This is evidence that
the proposed consistency relation does not identify when evidence will help; it is not evidence
that the state extractor was dead.

Both five-fold, query-group-isolated candidates therefore chose `STOP_M0` for all 104 samples.
Each produced zero contacts, zero saves, zero harms, zero exact-match gain, zero tool-accuracy gain,
five fold gains of zero, and grouped CI90 `[0.0, 0.0]`. The all-stop controller is a valid harm-safe
outcome of the frozen policy, but it supplies no agent benefit and no positive training-free RL
claim. Relaxing support, harm, or promotion gates after seeing these returns would tune to the
exposed cohort and is prohibited.

## Official-scoring efficiency

The two unchanged whole-manifest official-scoring operations ran concurrently with two outer
workers. Wall time was 2.256 seconds against 4.302 seconds of summed job time, an effective
1.9065-times speedup. No dataset shard was created, no shard score was averaged, and no official
scorer implementation was changed. The engineering rule is now: preserve one official invocation
per complete run and parallelize only independent complete-run jobs at the outer layer.

## Finalization incident and scientific validity

The recovered observation score completed. The supply finalizer also completed official scoring,
wrote the score file, and attached its hash to the manifest, then failed while rendering a missing
human-ledger field. The common failure boundary consequently left both attempt records `ABORTED`.
No prediction was re-flown. The scientific inputs and both official score surfaces are complete,
hash-verified, and independently reproduced by the committed model-free reader; the incident
affects experiment-state finalization, not the measured scores.

Commit `3332d8b1` repaired the generic boundary. Finalization now requires the complete human-ledger
surface before the scorer runs or a manifest can be mutated, and outer job specifications carry
the ledger cells explicitly. The receipt-pinned experiment runtime was archived recoverably, the
developer llama.cpp runtime was restored to commit
`9a41ce51850898973a41c39f9224818ff1a7fbe2`, and no server remains running.

## Scope and next design constraint

The experiment consumed 208 frozen-core contacts and 1,174.034 metered speech-audio seconds under
the registered ceilings of 213 contacts and 1,200 seconds, with zero paid API spend. It opened no
G2, remaining exposed-296, unexposed Audio2Tool population, FINAL60, test annotation, or future
turn. The baseline, model, registry, prompts, and scorer remain unchanged.

A successor must introduce a genuinely different information variable instead of repeating the
same observation or searching more categorical thresholds on these exposed returns. A reasonable
candidate is prospective same-core arbitration between independently formed task-call candidates,
with the original speech retained as final authority and with a fresh approximately-100-sample
discovery cohort. Such a study requires a separately frozen prompt, ExecutionPlan, exposure row,
group-isolated training-free contact policy, and promotion gates before any new model contact. This
verdict does not itself authorize that study.

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same sealed outputs (M0 shared with `A2T-G1-104`'s own arm1
file, 104/104 rows; REOBSERVE_DIRECT and SUPPLY_UNION_STRIPPED, 104/104 rows each; v1 identity
confirmed to 4 decimals overall for every arm) under the registered `a2t-scorer-v2`
(`analysis.a2t_v2_rescore`, `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| Arm | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.2788 | 0.5962 | 0.3846 | 0.5769 | 0.5962 | 0.5362 | 0.4379 | 0.9615 |
| REOBSERVE_DIRECT | 0.2212 | 0.5288 | 0.2981 | 0.5192 | 0.5288 | 0.4833 | 0.4063 | 0.9615 |
| SUPPLY_UNION_STRIPPED | 0.2212 | 0.5769 | 0.2500 | 0.5577 | 0.5769 | 0.3955 | 0.3569 | 0.9231 |

Paired contrasts vs. `M0` (v1 and v2, CI90, 10,000 replicates, tier-stratified; over all 104 rows,
not restricted to the doc's own 92-row "eligible" SUPPLY_UNION_STRIPPED subset):

| arm | metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|
| REOBSERVE_DIRECT | v1 exact | -0.0577 | 0 | 6 | 98 | [-0.0962, -0.0192] |
| REOBSERVE_DIRECT | v2 exact | -0.0865 | 0 | 9 | 95 | [-0.1346, -0.0481] |
| SUPPLY_UNION_STRIPPED | v1 exact | -0.0577 | 4 | 10 | 90 | [-0.1154, 0.0000] |
| SUPPLY_UNION_STRIPPED | v2 exact | -0.1346 | 2 | 16 | 86 | [-0.1923, -0.0769] |

Both arms stay net-harmful (or, for SUPPLY_UNION_STRIPPED under v1, borderline-neutral) versus M0
under v1; under v2 both intervals sit entirely below zero and REOBSERVE_DIRECT's v1 CI ([-0.0962,
-0.0192], already excluding zero) and SUPPLY_UNION_STRIPPED's v2 CI ([-0.1923, -0.0769], now also
excluding zero where v1's [-0.1154, 0.0000] merely touched it) both confirm the same direction, never
flip to a save. No arm here becomes net-positive under v2. Not promoted under v2 either: the
verdict's decision is unchanged, and this correction does not itself authorize the successor study
this doc names.
