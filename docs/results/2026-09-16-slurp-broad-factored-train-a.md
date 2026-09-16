# SLURP broad factored TRAIN Fold A discovery result

Decision: **NOT_ADVANCED_FULL_TASK_GAIN_GATE_FAILED**. Retain the released incumbent. The complete task did not improve under the registered advancement rule, so this package does not enter matched-replication advancement. Do not sweep breadth settings or repeat this flight until a gate passes.

The frozen broad/factored run and its first complete official score cover the exact previously exposed TRAIN Fold A roster: 1,080 recordings, 125 speaker clusters, and 18 scenarios with 60 recordings each. No Fold B results were consumed. This is a comparison with an earlier system incumbent, not a new direct-versus-system comparison.

Root verified the complete structural gate and persisted the paired quality release before reading new outcomes. The analysis uses the unchanged prospective recipe: paired whole-speaker bootstrap, 10,000 draws, seed 20260915, CI95 for the primary advancement endpoint and CI90 for diagnostics. Scores were reused; no official scorer was invoked again.

## Complete-task results

| Metric | Incumbent (%) | Broad/factored (%) | Difference (pp) | Interval (pp) |
|---|---:|---:|---:|---:|
| Official pooled SLU micro F1 (primary, CI95) | 48.5336 | 47.6347 | -0.8990 | [-2.6077, +0.7821] |
| Official entity-pair micro F1 (CI90) | 29.4976 | 27.4659 | -2.0316 | [-3.7584, -0.3293] |
| Intent accuracy (CI90) | 77.9630 | 77.8704 | -0.0926 | [-1.3348, +1.1259] |
| Scenario accuracy (CI90) | 84.8148 | 85.4630 | +0.6481 | [-0.3538, +1.6766] |
| Action accuracy (CI90) | 79.2593 | 79.3519 | +0.0926 | [-1.0936, +1.2617] |

The equal-scenario pooled SLU view is 46.8364% to 45.4969%, a change of -1.3395 pp (CI95 [-2.9722, +0.4360]). These are pooled count ratios, not the mean of per-recording F1. Equal-scenario weighting averages within-scenario pooled ratios; equal recording counts do not make its entity denominator weights identical to the natural pooled estimate.

Final intent counts are 842 to 841 correct. Intent changes comprise 34 saves, 35 harms, and 1,011 ties. Per-recording SLU-ratio signs are 99 improvements, 113 decreases, and 868 ties; these sign counts are descriptive and are not the pooled primary estimator.

The primary CI95 includes zero: this fails to demonstrate improvement and does not establish overall harm at that level. The exact entity-pair diagnostic is negative throughout its CI90. The latter motivates entity extraction and consumption analysis; it is not a replacement primary gate.

## All scenario strata

Each row contains 60 recordings. Stratum estimates are descriptive.

| Scenario | Incumbent SLU (%) | Broad/factored SLU (%) | SLU difference (pp) | Intent difference (pp) | Entity-pair difference (pp) |
|---|---:|---:|---:|---:|---:|
| alarm | 52.6629 | 48.3834 | -4.2796 | +0.0000 | -2.2619 |
| audio | 47.7541 | 35.1426 | -12.6115 | -1.6667 | -6.7944 |
| calendar | 48.3786 | 47.6305 | -0.7481 | -3.3333 | -5.1804 |
| cooking | 62.4709 | 62.6321 | +0.1612 | -1.6667 | +3.0214 |
| datetime | 59.5160 | 62.1981 | +2.6821 | +1.6667 | +6.9352 |
| email | 36.6353 | 41.7291 | +5.0938 | +1.6667 | -3.2891 |
| general | 15.4532 | 16.8176 | +1.3644 | +0.0000 | +0.7576 |
| iot | 55.5331 | 58.7817 | +3.2486 | -1.6667 | +3.4286 |
| lists | 43.5483 | 39.3734 | -4.1749 | +3.3333 | -5.9627 |
| music | 34.5328 | 34.9002 | +0.3674 | -3.3333 | +2.3617 |
| news | 44.2416 | 38.6298 | -5.6118 | +0.0000 | -13.3651 |
| play | 46.8231 | 43.7286 | -3.0945 | +6.6667 | -10.0522 |
| qa | 57.0355 | 55.8054 | -1.2301 | +3.3333 | -3.6040 |
| recommendation | 49.7452 | 43.2484 | -6.4969 | -3.3333 | -7.8527 |
| social | 34.7389 | 33.9582 | -0.7807 | +1.6667 | -5.1450 |
| takeaway | 48.8388 | 49.1060 | +0.2672 | -1.6667 | +0.9335 |
| transport | 51.3367 | 52.9630 | +1.6263 | -3.3333 | +1.0141 |
| weather | 53.8099 | 53.9159 | +0.1060 | +0.0000 | +3.0564 |

## Input and execution accounting

The incumbent used 5,417 core calls and 45,998,267 prompt tokens; the broad/factored run used 5,407 core calls and 60,903,646 prompt tokens. Input token volume increased 32.40% while call count was nearly unchanged. Recorded completion tokens changed from 255,153 to 237,929. Cost reports record 1,082 and 1,081 tool calls respectively; the trajectory audit separately resolves contacted tools and control events.

The broad/factored run records 15,448.2406875 repeated speech seconds. Cumulative request latency is not wall time under concurrent serving. GPU telemetry is missing before the first SLURP monitor sample at 2026-09-15T17:11:58.400683Z; do not impute a complete measured utilization integral.

SLURP finalized at 2026-09-15T21:38:55Z. Root next resumed dispatch around 2026-09-16T02:11Z, and stopped the previous resident session at 02:13:24Z. Record this roughly 4.5-hour handoff delay as delayed root dispatch with unestablished cause. It was not useful generation or scientific-decision waiting. A2T then encountered a separate pre-contact ledger case mismatch; its correction is documented independently.

## Interpretation and next step

This changes knowledge organization and supply together. OBS remains the same prepared speech; ORG factors the intent values; SUPPLY broadens their exposure; USE is mediated through the same role program and candidate-conditioned Solver. The experiment cannot isolate compaction from breadth, and the incumbent ran in an earlier service process.

The negative complete-task point estimate closes advancement for this package. Preserve the incumbent; the source-bound candidate and entity diagnostics below identify unresolved perception, selection and entity-consumption work. Do not interpret a coverage increase by itself as a complete-system success, or equate more supplied values with more useful information. Independent, already registered Audio2Tool and E21 work can proceed.

## Candidate and conditional-resolution attribution

Generated gold-intent coverage is 937/1,080 (86.7593%) for the incumbent and 947/1,080 (87.6852%) for broad/factored: a descriptive gain of 10 recordings, or 0.9259 pp. It remains below the owner's 95% target. Both sources have no completed candidate refresh, so initial and pre-final candidate coverage coincide.

Final correctness within each arm's own covered set is 842/937 (89.8613%) and 841/947 (88.8068%). Those denominators differ; their difference is not a within-person causal effect. The following exact paired partition makes the tradeoff explicit.

| Candidate-coverage partition | Recordings | Incumbent final intent correct | Broad/factored final intent correct | Saves | Harms |
|---|---:|---:|---:|---:|---:|
| covered both | 917 | 834 | 824 | 17 | 27 |
| gained coverage | 30 | 0 | 17 | 17 | 0 |
| lost coverage | 20 | 8 | 0 | 0 | 8 |
| uncovered both | 113 | 0 | 0 | 0 | 0 |

The broader package gains coverage on 30 recordings and loses it on 20. The gains yield 17 final correct answers, while lost coverage removes eight. On the 917 recordings covered by both systems, final correct intents fall from 834 to 824. Thus the net nine correct answers gained through changed coverage are offset by ten lost within common coverage. This is a source-bound descriptive decomposition, not identification of the causal effect of candidate selection.

| Actual distinct candidate width | Incumbent recordings | Broad/factored recordings | Incumbent covered | Broad/factored covered |
|---|---:|---:|---:|---:|
| 1 | 57 | 255 | 54 | 241 |
| 2 | 225 | 230 | 211 | 212 |
| 3 | 798 | 595 | 672 | 494 |

More supplied knowledge did not produce wider candidate outputs: one-candidate responses rose from 57 to 255, and three-candidate responses fell from 798 to 595. Width is observed behavior, not calibrated confidence. Do not infer that the narrower responses were more certain or better justified.

## Entity residuals after intent is correct

Among each arm's correct-intent recordings, nonexact entity sets rise from 525/842 to 540/841. On the same 807 recordings whose final intent is correct in both arms, exact entity sets fall from 303 to 293, and pooled exact entity-pair F1 falls from 32.8592% to 31.3167%. Therefore the entity residual is not explained solely by the few changed final intent labels. These are observational outcome-conditioned partitions, not a separate causal experiment.

An entity set is counted exact only when both saved official exact-slot FP and FN equal zero, including the standard treatment of correctly empty sets. No answer was rescored or repaired for this analysis.

## Diagnostic limitations and resulting direction

The legacy optional own-intent-card support projection rejected the factored store's extra non-label value. Its original failure and replacement diagnostic configuration are retained in DATA/coordination/slurp-broad-factored-v1/diagnostic-projection-scope-correction-v1.json. The shared candidate-stage and reference-join analysis remained unchanged; only that unsupported optional support metric was omitted. Do not silently report all supplied values as mapped intent cards or claim full own-intent support.

Root's next design direction is to separate candidate omission, within-candidate resolution, and semantic slot extraction. The present evidence does not support another undirected breadth increase. A future Reviewer/Planner acquisition policy should request evidence that can resolve a named ambiguity, and the Solver should consume the corresponding slot interpretation and acoustic evidence. Such a successor still needs a concrete protocol and matched task-quality evaluation. This report does not authorize one or label manual system iteration as training-free RL.

Candidate-stage source SHA-256: 7f5c89d6291580234bbd1195e1afe68cd5272b5ffa5eb95b1acbbbe3b557b1c6. Paired candidate attribution SHA-256: 1a277ffab0998218e7681e6c0746d7e6f7d75bda5bc6c818d43ae2358124674b. Correct-intent entity attribution SHA-256: 50918d26621aaf5512483d24a3692c46ed3d05210835516d87f3d247db6e11ee.

## Native control and tool use

The verified execution contains 1,080 Perception contacts, 1,082 Solver contacts, 2,163 Reviewer contacts, and 1,082 Planner contacts, totaling 5,407 core calls. Planner records 1,080 ACCEPT actions and only two REVISE actions. The run therefore exercises little corrective branching despite the availability of the bounded control program.

The analytical tool records 1,081 contacted calls, all with result events; no tool failure or rejection is recorded. There are zero observation-tool calls. All 5,407 contacts have completion metadata; none reached the configured output cap or stopped for length, including every final delivered response. Output truncation is not an observed explanation for this result.

This localizes a practical limitation of the evaluated system: the Reviewer mostly uses task-contract information, while the program acquires no additional acoustic evidence and rarely revises. A successful tool call does not establish useful task information gain. Future tool design should distinguish structural contract checking from evidence that resolves an acoustic or semantic error, and measure resulting saves and harms.

The native execution audit is DATA/analysis/SAEA-SLURP-NATIVE-BROAD-FACTORED-TRAIN-FOLD-A-V1/native-execution-diagnostics-v1.json, SHA-256 e3cce4f71b356cedf6be4b2876cf9fdef93e0a1040326685625f764ffa6768b5.

## Provenance

- Frozen execution source: 0bede772c27688c29999798e5fc945035a10b805.
- Protocol: docs/readiness/2026-09-15-slurp-broad-factored-train-a-v1/protocol-v1.json; SHA-256 4b27a3e9a06f917445c9a6bef62d1b423a7465e2f8e5f73a53eb8d5d929ca01e.
- Structural gate: DATA/coordination/slurp-broad-factored-v1/postseal-structural-gate-v1.json; SHA-256 d8d1b02aeedd8ccad90fd55f8b861708e52af6f2fba8894dbbab57161b416ff1.
- Paired quality release: DATA/coordination/slurp-broad-factored-v1/root-paired-quality-release-v1.json; SHA-256 0ceb82d0bf4f34542ea73fb24d6012cfde7d0de02842d1587b5eceb459884de8.
- Primary verdict: DATA/coordination/slurp-broad-factored-v1/root-primary-verdict-v1.json; SHA-256 757f42ccb810838e9670014649e79f8dc90f2394cdeb25f30e6fdda9407d4aff.
- Paired analysis: DATA/analysis/SAEA-SLURP-BROAD-FACTORED-TRAIN-A-ANALYSIS-V1/paired-scores-v1.json.
