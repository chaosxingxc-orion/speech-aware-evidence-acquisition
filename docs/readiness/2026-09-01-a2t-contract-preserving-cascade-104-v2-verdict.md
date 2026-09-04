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

## Correction under a2t-scorer-v2 (2026-09-03)

Zero-contact offline re-score of the same five sealed `outputs.jsonl` files (104/104 rows each, v1
identity confirmed to 4 decimals overall for every arm) under the registered `a2t-scorer-v2`
(`analysis.a2t_v2_rescore`, `docs/checks/speech-aware-evidence-acquisition/2026-09-03-a2t-scorer-v2-rescore/`).

| Arm | v1 exact | v1 tool | v2 exact | v2 tool (ordered) | v2 tool (multiset) | v2 slot F1 | v1 slot F1 | parse rate |
|---|---|---|---|---|---|---|---|---|
| M0 direct | 0.3077 | 0.5865 | 0.3558 | 0.5865 | 0.5865 | 0.4627 | 0.3742 | 0.9423 |
| Matched always-use | 0.3846 | 0.7019 | 0.4038 | 0.7019 | 0.7019 | 0.4982 | 0.4091 | 1.0000 |
| Same-tier shuffled evidence | 0.2692 | 0.4904 | 0.2885 | 0.4808 | 0.4904 | 0.3954 | 0.3208 | 0.9904 |
| Matched exact-resend composite | 0.3750 | 0.6923 | 0.3942 | 0.6923 | 0.6923 | 0.4964 | 0.4180 | 1.0000 |
| Cross-fitted policy | 0.2885 | 0.5673 | 0.3365 | 0.5673 | 0.5673 | 0.4488 | 0.3648 | 0.9423 |

Paired contrasts vs. `M0 direct` (v1 and v2, CI90, 10,000 replicates, tier-stratified):

| arm | metric | delta | saves | harms | ties | CI90 |
|---|---|---|---|---|---|---|
| Matched always-use | v1 exact | +0.0769 | 14 | 6 | 84 | [0.0096, 0.1442] |
| Matched always-use | v2 exact | +0.0481 | 10 | 5 | 89 | [-0.0096, 0.1058] |
| Same-tier shuffled evidence | v1 exact | -0.0385 | 6 | 10 | 88 | [-0.0962, 0.0192] |
| Same-tier shuffled evidence | v2 exact | -0.0673 | 6 | 13 | 85 | [-0.1346, 0.0000] |
| Matched exact-resend composite | v1 exact | +0.0673 | 13 | 6 | 85 | [0.0000, 0.1346] |
| Matched exact-resend composite | v2 exact | +0.0385 | 9 | 5 | 90 | [-0.0192, 0.0962] |
| Cross-fitted policy | v1 exact | -0.0192 | 0 | 2 | 102 | [-0.0385, 0.0000] |
| Cross-fitted policy | v2 exact | -0.0192 | 0 | 2 | 102 | [-0.0385, 0.0000] |

The v1 tool-accuracy paired contrast (this doc's headline mechanism claim) is unaffected by v2's
argument-level changes on this arm: `tool_accuracy_ordered` equals `tool_accuracy_multiset` for
every one of these five arms here (no `TOOL_ORDER_ONLY` rows), so `Matched always-use` vs `M0 direct`
tool accuracy is still +0.1154pp with a CI90 of [0.0385, 0.1923] under v2 as well. Exact match is
where v2 moves: `Matched always-use`'s v1 CI90 [0.0096, 0.1442] excludes zero, but its v2 CI90
[-0.0096, 0.1058] now touches zero — the v2 interval crosses zero where the v1 interval did not.
`Matched exact-resend composite`'s v1 CI90 already touches zero at its lower bound ([0.0000, 0.1346])
and its v2 CI90 moves to include zero more centrally ([-0.0192, 0.0962]) -- the same direction of
movement, one step further along it. This does not reopen this verdict's decision (which was already "close this exact-cell
training-free controller" on the memory-policy result, not on the always-use mechanism's exact-match
significance alone): the "agent-over-single-call" finding this doc's Decision section rests on is a
tool-accuracy claim (`Matched always-use` vs `M0 direct`), which is unchanged in direction and
CI-exclusion-of-zero under v2, as shown above. This correction re-scores only the four arms paired
against `M0 direct` above; it does not recompute the doc's separate query-grouped
`Matched-vs-shuffled` bootstrap (a different comparator pair and resampling unit from this
correction's `sample_ids`-restricted, tier-stratified pairing), so that specific interval is not
re-verified here. `Cross-fitted policy`'s v1 and v2 exact-match CI90s both stay entirely at or below
zero ([-0.0385, 0.0000] both scorings) — the training-free controller finding ("failed all ten
policy-effect gates") is unaffected by v2 either. Not promoted under v2 either.
