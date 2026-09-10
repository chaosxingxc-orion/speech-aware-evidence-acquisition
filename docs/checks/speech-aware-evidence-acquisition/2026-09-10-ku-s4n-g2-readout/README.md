# KU-S4N G2 aligned decision

Decision: **HOLD_NONINFERIORITY_FAILED**. Do not start G3 exemplar encoding or G4. Preserve both complete generations, their one official scoring job each, and the unchanged frozen null calibration. The previously admitted KU-S3 component is unaffected. Independent E21 preparation may continue.

Both N and twin completed 1,000 calls and FINALIZED scoring on the same decoder-only np8 service and frozen c4594154 runtime. The service then stopped normally. The primary population is historically exposed NEW500; it is not a fresh holdout. The shared analysis ran once, with zero model/encoder/tokenizer/scorer invocations.

## Frozen primary gates

Natural-mixture paired speaker-cluster bootstrap, 10,000 replicates. Percentage-point differences are N minus the historical comparator. Operational margins come from the frozen null CI width; they are not independently chosen practical-value margins.

| Metric | Comparator % | N % | Difference pp | CI90 pp | NI margin pp | NI | Equivalence |
| --- | ---: | ---: | ---: | --- | ---: | --- | --- |
| scenario_action_exact | 75.200 | 73.000 | -2.200 | [-5.077, +0.820] | 1.263 | False | False |
| scenario_exact | 84.600 | 86.400 | +1.800 | [+0.607, +3.071] | 1.192 | True | False |
| action_exact | 76.600 | 74.000 | -2.600 | [-5.455, +0.232] | 1.446 | False | False |
| slu_f1_f1 | 21.046 | 11.012 | -10.034 | [-12.328, -7.739] | 1.383 | False | False |
| slu_f1_micro | 37.371 | 25.626 | -11.744 | [-15.181, -8.158] | 1.880 | False | False |

Per-sample SLU-F1 is descriptive; pooled-count micro SLU-F1 is the protection metric. Non-inferiority and equivalence are separate tests. The intent effectiveness lower-bound threshold remains 1.904863 pp. It is not met. N minus twin intent is +32.000 pp, CI90 [28.106, 36.031], but that cannot replace the baseline and protection gates. Normalized secondary intent signs agree in both declared contrasts.

## Populations and weighting

| Population | Metric | Natural-mixture difference pp | Equal-scenario difference pp | Speaker-cluster CI90 pp |
| --- | --- | ---: | ---: | --- |
| NEW500 | scenario_action_exact | -2.200 | -4.318 | [-5.077, +0.820] |
| NEW500 | scenario_exact | +1.800 | +1.797 | [+0.607, +3.071] |
| NEW500 | action_exact | -2.600 | -4.660 | [-5.455, +0.232] |
| NEW500 | slu_f1_f1 | -10.034 | -9.366 | [-12.328, -7.739] |
| NEW500 | slu_f1_micro | -11.744 | -11.104 | [-15.181, -8.158] |
| OLD500 | scenario_action_exact | +3.600 | +3.571 | [+0.985, +6.283] |
| OLD500 | scenario_exact | +3.400 | +3.380 | [+1.953, +4.817] |
| OLD500 | action_exact | +3.800 | +3.777 | [+1.046, +6.471] |
| OLD500 | slu_f1_f1 | -8.896 | -8.876 | [-10.898, -7.039] |
| OLD500 | slu_f1_micro | -10.716 | -9.952 | [-13.752, -7.822] |
| DEV1000 | scenario_action_exact | +0.700 | +0.856 | [-1.284, +2.691] |
| DEV1000 | scenario_exact | +2.600 | +2.646 | [+1.718, +3.505] |
| DEV1000 | action_exact | +0.600 | +0.763 | [-1.469, +2.609] |
| DEV1000 | slu_f1_f1 | -9.465 | -9.201 | [-10.981, -7.978] |
| DEV1000 | slu_f1_micro | -11.249 | -10.482 | [-13.725, -8.761] |

Full normalized secondary contrasts, scenario-stratified sensitivity, twin-minus-comparator descriptive contrasts and every stratum are retained in the hash-pinned shared analysis artifact. No bootstrap or scorer was repeated to produce this report.

## Primary NEW500 strata

N minus historical comparator. Scenario rows are descriptive; no new stratum-specific gate is introduced.

| Scenario | n | Intent difference pp | Scenario difference pp | Action difference pp | Mean sample SLU-F1 difference pp | Micro SLU-F1 difference pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 30 | +0.000 | +0.000 | +0.000 | -15.991 | -15.608 |
| audio | 2 | -50.000 | +0.000 | -50.000 | +0.000 | +0.000 |
| calendar | 33 | +15.152 | +3.030 | +15.152 | -7.769 | -11.248 |
| cooking | 9 | +22.222 | +11.111 | +22.222 | -7.504 | -9.927 |
| datetime | 33 | +6.061 | +0.000 | +6.061 | -17.336 | -26.603 |
| email | 33 | -18.182 | +0.000 | -18.182 | -7.576 | -8.571 |
| general | 33 | +9.091 | +0.000 | +9.091 | -3.533 | -14.858 |
| iot | 33 | -18.182 | +0.000 | -18.182 | -15.353 | -13.108 |
| lists | 32 | -18.750 | +6.250 | -18.750 | +2.254 | +15.152 |
| music | 23 | -26.087 | -13.043 | -26.087 | -11.088 | -18.400 |
| news | 32 | +3.125 | +3.125 | +0.000 | -19.712 | -26.527 |
| play | 32 | +12.500 | +15.625 | +12.500 | -9.730 | +2.504 |
| qa | 32 | +9.375 | +6.250 | +9.375 | -4.846 | -2.956 |
| recommendation | 32 | -18.750 | +0.000 | -18.750 | -25.502 | -24.396 |
| social | 33 | -6.061 | +0.000 | -6.061 | -7.553 | -12.858 |
| takeaway | 12 | -8.333 | +0.000 | -8.333 | -7.126 | -13.817 |
| transport | 33 | +9.091 | +0.000 | +9.091 | -6.837 | -5.956 |
| weather | 33 | +0.000 | +0.000 | -3.030 | -3.384 | -12.698 |

## Structural output audit and interpretation boundary

The following counts inspect complete sealed output objects only. They neither rerun delivery nor alter any manifest.

| Arm | Population | Rows | JSON objects | Missing entities key | Empty entity lists | Nonempty entity lists | Predicted entities |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| comparator | DEV1000 | 1000 | 997 | 0 | 511 | 486 | 547 |
| comparator | NEW500 | 500 | 498 | 0 | 260 | 238 | 273 |
| n | DEV1000 | 1000 | 1000 | 0 | 792 | 208 | 231 |
| n | NEW500 | 500 | 500 | 0 | 399 | 101 | 115 |
| twin | DEV1000 | 1000 | 997 | 0 | 770 | 227 | 246 |
| twin | NEW500 | 500 | 498 | 0 | 388 | 110 | 121 |

N and twin share OBS and the same control turn; their contrast isolates candidate selection under this harness. N versus historical comparator includes both added supply and the documented ORG/CONTROL turn. Structural output counts are descriptive, not a causal diagnosis.

OBS is held by the same query packets and serving geometry. SUPPLY changes which candidate intents are supplied. The phase control turn is a declared ORG covariate against the historical baseline. USE is observed through the sealed outputs and retained statistics, not assigned a causal mechanism by these counts. First audit the named control-turn and supply effects using existing artifacts. A new matched generation requires a concrete decision-changing mismatch and its own registration/authorization; no adaptive rerun is admitted here.

## Reproduction and resource receipts

Use `configs/experiment/slurp-kus4n-g2-aligned-analysis-v1.json` with the shared `analysis.score_compare_cli` entry to reproduce the statistics from sealed score artifacts. Decision inputs, strict inequalities, source hashes and structural audit bindings are in `decision.json`. The complete result is `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S4N-G2-ALIGNED-READOUT-V1/contrasts.json` (SHA256 d296f01467ae388d05b3c932b961e603d8edd94007c92de523b3019b40533e16).

Root resource audit: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-KU-S4N-G2-CAMPAIGN-V3/timing-audit-v2.json`. The whole monitored session time-weighted GPU utilization was 22.203%; N live-wave-to-seal was 72.394%; twin attach-to-seal was 63.603% and includes setup. Never treat these differently delimited intervals as pure kernel-active throughput. N seal to twin attach was 186.153 seconds, exceeding the one-minute handoff target. The monitor request counter is not cumulative cost authority; each sealed manifest records 1,000 calls.
