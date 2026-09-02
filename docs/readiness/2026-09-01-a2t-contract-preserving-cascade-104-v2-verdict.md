# A2T Contract-Preserving Cascade 104 V2 Verdict

## Decision

Close this exact-cell training-free controller. Do not run its support flight, do not expand it to
approximately 1,000 samples, and do not change the engineering baseline.

The experiment isolates two different conclusions. The contract-preserving AgentLoop evidence
mechanism works on this discovery cohort: always using matched evidence improves over the same-core
single-call comparator. The frozen cross-fitted reward-memory controller does not work: it turns
that positive return surface into a regression. Agent-over-single-call and information gain are
present; a positive training-free RL contribution is not.

## Frozen scope and execution

`A2T-CPV2-104` contains 104 discovery samples, exactly 13 per Audio2Tool tier, with zero query-block
overlap with the earlier `A2T-G1-104` cohort. M0 preserved the historical direct request bytes.
OBS produced bounded English self-transcripts. USE inserted the Agent state and evidence before the
unchanged final JSON-only output sentence. The frozen core, prompts, packets, BM25 retriever,
evidence budgets, same-tier derangement, policy features, five query-group folds, memory thresholds,
resend floor, metrics, and promotion conjunction were not changed after contact.

All 430 registered model contacts sealed: 104 M0, 104 OBS, 103 matched USE, 103 shuffled USE split
across an eight-contact canary and a 95-contact continuation, and 16 exact matched-request resends.
Total metered speech audio was 2,216.689 seconds under the 2,700-second registration. No paid API,
parameter training, embedding tool, tokenizer tool, second answering model, test annotation,
FINAL60 item, G2 item, future turn, or unexposed population was used.

## Official results

| Arm | Exact | Tool | Slot micro F1 | Parse failures |
|---|---:|---:|---:|---:|
| M0 direct | 32/104 (30.77%) | 61/104 (58.65%) | 37.42% | 6 |
| Matched always-use | 40/104 (38.46%) | 73/104 (70.19%) | 40.91% | 0 |
| Same-tier shuffled evidence | 28/104 (26.92%) | 51/104 (49.04%) | 32.08% | 1 |
| Matched exact-resend composite | 39/104 (37.50%) | 72/104 (69.23%) | 41.80% | 0 |
| Cross-fitted policy | 30/104 (28.85%) | 59/104 (56.73%) | 36.48% | 6 |

Matched always-use beats M0 by 8 exact items (+7.69 percentage points), 12 tool-correct items
(+11.54 points), and 3.49 slot-F1 points. This is direct evidence that the multi-contact AgentLoop
can outperform one frozen-core call when it supplies relevant state and evidence.

Matched evidence beats the same-capacity shuffled control by 12 exact items (+11.54 points), with a
query-grouped 90% interval of [+4.81, +19.23] points, and by 22 tool-correct items. The frozen top-5
retrieval surface contains the gold tool on 71 rows versus 61 M0 tool-correct rows. Together these
results establish nontrivial information gain from evidence content rather than merely an extra
model call or output-format effect. The exact resend changes the matched exact count by one, which
is the frozen empirical nondeterminism floor.

## Training-free control result

The five-fold exact-cell memory chose `USE_MATCHED` for 10 rows and `STOP_M0` for 94. On held-out
groups it produced zero saves and two harms: exact net -2, tool-correct net -2, slot micro-F1
-0.94 points, fold gains `[0, -1, 0, -1, 0]`, and grouped 90% interval [-4.81, 0.00] points.
It therefore failed all ten policy-effect gates, including saves, harms, net gain, resend floor,
positive interval, tool/slot non-regression, fold stability, and improvement over always-use.

This is not evidence against the matched evidence mechanism. It is evidence against using the
current five-axis exact-cell state and support-four/saves-two/harms-zero lookup rule as the control
plane. The controller selected sparse cells whose positive discovery returns did not transfer to
their held-out query groups. Relaxing those thresholds or searching new bins on these 104 outcomes
would be outcome-directed tuning and is prohibited.

## Evaluation efficiency

Wave 1 used four outer workers. Each worker invoked the unchanged official scorer in one process on
one complete 104-row manifest; no dataset was sharded and no shard metric was averaged. All four
jobs succeeded in 2.7586 seconds wall time versus 9.3186 seconds summed job time, an effective
3.3780-times speedup. The dependent policy derivative then used one complete single-worker Wave-2
job. This whole-manifest outer-parallel pattern is retained as the engineering evaluation baseline.
Network-jitter injection, packet-loss simulation, and network-retry stress are deliberately outside
that baseline: the frozen core and scorer use local service boundaries, and network variation is not
a scientific axis or an engineering acceptance condition for this study. Throughput checks retain
only local wall time, summed job time, worker count, queue/service behavior, and fail-closed recovery.

## Consequence and next admissible experiment

The positive component worth carrying forward is fixed: English self-transcript OBS,
contract-preserving final prompt, deterministic matched evidence, and the matched-versus-shuffled
control. The failed component is the exact-cell reward-memory selector.

A successor must be a separately preregistered controller experiment on a fresh, query-block-
disjoint discovery cohort. It may use a lower-variance training-free control formulation whose
state is fixed before contact and whose action values are estimated only from discovery folds, but
it must not tune bins or thresholds against these 104 outcomes. It must retain an always-use matched
arm so that policy contribution is measured as an additional layer rather than confused with the
already-positive evidence mechanism. The successor must again prove all three conditions before
scale: agent over one-call, matched information gain, and positive training-free policy gain beyond
the resend floor with fold stability. Until then there is no support flight, approximately-1,000-
sample run, baseline promotion, test access, or Stage-3 claim.

The compact committed result is
`docs/checks/speech-aware-evidence-acquisition/2026-09-01-a2t-contract-preserving-cascade-104-v2/mechanism-result.json`.
Its external source receipts are SHA-256 pinned there; the final policy result SHA-256 is
`2b616b69c64a51a2caeaaac04c944754e2e903ed1d65f546e79cc75df676ca9b`.
