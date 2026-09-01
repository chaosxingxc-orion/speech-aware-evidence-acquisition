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
