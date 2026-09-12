# SLURP fixed Whisper evidence: EFFECTIVENESS_NOT_ESTABLISHED

Result interpretation recorded at 2026-09-12T22:41:51.372713+00:00. Both complete arms were first-scored once. The exact post-seal read was registered before semantic inspection. This report transcribes the frozen shared analysis; it adds no bootstrap run, official score, model, encoder or audio contact.

## Root decision

Do not add fixed all-row Whisper transcript supply to the default system as an established quality improvement. Retain the compact SLURP working base and the local Whisper tool for investigation. The primary micro F1 and intent intervals both span zero; the full-roster intent interval is negative. This is neither equivalence nor noninferiority. It does not test Reviewer targeting or prove that selective independent ASR is useless.

No immediate owner tradeoff is required: there is no established primary entity gain to trade for intent quality. Do not change task priorities or historical thresholds. Complete the already registered trace/catalog diagnosis before admitting another mechanism; the named cause is not yet established.

## Complete native results

All differences below are treatment minus control in percentage points. CI90 uses 10,000 paired whole-speaker cluster draws. NEW500 is primary and historically exposed; OLD500 and DEV1000 are secondary. Equal-scenario columns are descriptive point differences, without an invented interval. Row-mean F1 is distinct from pooled micro F1.

| Population | Metric | Control % | Whisper % | Difference pp | Speaker CI90 pp | Equal-scenario difference pp | Classification |
| --- | --- | ---: | ---: | ---: | --- | ---: | --- |
| NEW500 | slu_f1_micro | 40.066528 | 40.899535 | +0.833007 | [-1.098159, +2.834993] | +1.098051 | unresolved |
| NEW500 | scenario_action_exact | 76.600000 | 75.800000 | -0.800000 | [-2.114226, +0.401606] | -0.245511 | unresolved |
| NEW500 | scenario_exact | 84.600000 | 83.800000 | -0.800000 | [-2.022472, +0.221263] | -0.678662 | unresolved |
| NEW500 | action_exact | 78.600000 | 78.400000 | -0.200000 | [-1.622751, +1.127820] | +0.275323 | unresolved |
| NEW500 | slu_f1_f1 | 23.911824 | 24.560793 | +0.648968 | [-0.837551, +2.205229] | +0.601149 | unresolved |
| OLD500 | slu_f1_micro | 38.611255 | 37.783536 | -0.827719 | [-2.502919, +0.793537] | -0.421144 | unresolved |
| OLD500 | scenario_action_exact | 72.800000 | 71.800000 | -1.000000 | [-2.272727, +0.400842] | -0.992063 | unresolved |
| OLD500 | scenario_exact | 83.200000 | 82.600000 | -0.600000 | [-2.000000, +0.738916] | -0.587889 | unresolved |
| OLD500 | action_exact | 75.400000 | 73.800000 | -1.600000 | [-2.982125, -0.185477] | -1.587302 | negative |
| OLD500 | slu_f1_f1 | 21.689921 | 20.479346 | -1.210575 | [-2.385313, -0.051313] | -1.215727 | negative |
| DEV1000 | slu_f1_micro | 39.347354 | 39.364354 | +0.017000 | [-1.226803, +1.236931] | +0.294842 | unresolved |
| DEV1000 | scenario_action_exact | 74.700000 | 73.800000 | -0.900000 | [-1.680672, -0.093366] | -0.591585 | negative |
| DEV1000 | scenario_exact | 83.900000 | 83.200000 | -0.700000 | [-1.645692, +0.202634] | -0.724558 | unresolved |
| DEV1000 | action_exact | 77.000000 | 76.100000 | -0.900000 | [-1.822101, +0.100614] | -0.604889 | unresolved |
| DEV1000 | slu_f1_f1 | 22.800873 | 22.520069 | -0.280803 | [-1.232722, +0.669356] | -0.393196 | unresolved |

Scenario-stratified row-bootstrap results remain a sensitivity analysis in the pinned output. For DEV1000 intent, that sensitivity CI90 is [-1.900,+0.100] pp, while the prespecified speaker-cluster interval is [-1.680672,-0.093366] pp. Preserve this sensitivity; do not select the favorable interval.

## All scenario strata

These are descriptive scenario points and supports. No stratum-level causal or significance claim is made. Scalar points come from the saved scenario-stratified table; pooled micro points come from the saved pooled-count table. Both use the same complete population. Small strata are retained.

### NEW500

| Scenario | n | Micro control % | Micro Whisper % | Micro difference pp | Intent control % | Intent Whisper % | Intent difference pp | Intent saves | Intent harms | Scenario difference pp | Action difference pp | Row-F1 difference pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 30 | 35.4254 | 34.9101 | -0.5153 | 90.0000 | 90.0000 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.0000 |
| audio | 2 | 0.0000 | 0.0000 | +0.0000 | 100.0000 | 100.0000 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.0000 |
| calendar | 33 | 28.6353 | 31.9051 | +3.2698 | 57.5758 | 60.6061 | +3.0303 | 2 | 1 | -3.0303 | +3.0303 | +3.3984 |
| cooking | 9 | 71.6253 | 71.6253 | +0.0000 | 66.6667 | 77.7778 | +11.1111 | 1 | 0 | +0.0000 | +11.1111 | +0.0000 |
| datetime | 33 | 35.8744 | 32.5369 | -3.3376 | 81.8182 | 90.9091 | +9.0909 | 3 | 0 | +3.0303 | +6.0606 | -3.0303 |
| email | 33 | 29.0323 | 36.3636 | +7.3314 | 93.9394 | 87.8788 | -6.0606 | 0 | 2 | -3.0303 | -6.0606 | +1.5152 |
| general | 33 | 16.8224 | 19.0476 | +2.2252 | 39.3939 | 39.3939 | +0.0000 | 1 | 1 | -3.0303 | +0.0000 | +1.4260 |
| iot | 33 | 61.7536 | 59.7931 | -1.9605 | 93.9394 | 87.8788 | -6.0606 | 0 | 2 | +0.0000 | -6.0606 | -2.6813 |
| lists | 32 | 33.1699 | 34.3079 | +1.1380 | 84.3750 | 84.3750 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.0000 |
| music | 23 | 43.2560 | 51.8135 | +8.5575 | 73.9130 | 73.9130 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +3.0725 |
| news | 32 | 41.3736 | 41.2290 | -0.1446 | 84.3750 | 78.1250 | -6.2500 | 0 | 2 | -6.2500 | +3.1250 | -1.5212 |
| play | 32 | 61.1264 | 59.2270 | -1.8995 | 37.5000 | 34.3750 | -3.1250 | 0 | 1 | +3.1250 | -3.1250 | +0.4220 |
| qa | 32 | 62.9022 | 58.5293 | -4.3729 | 68.7500 | 68.7500 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | -2.0604 |
| recommendation | 32 | 58.3615 | 64.0655 | +5.7039 | 84.3750 | 81.2500 | -3.1250 | 0 | 1 | +0.0000 | -3.1250 | +5.0331 |
| social | 33 | 31.1480 | 30.4046 | -0.7434 | 75.7576 | 72.7273 | -3.0303 | 0 | 1 | -3.0303 | -3.0303 | -0.4677 |
| takeaway | 12 | 32.0000 | 30.3797 | -1.6203 | 83.3333 | 83.3333 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.0000 |
| transport | 33 | 30.8923 | 29.0243 | -1.8680 | 87.8788 | 87.8788 | +0.0000 | 0 | 0 | +0.0000 | +3.0303 | -1.5079 |
| weather | 33 | 20.4242 | 28.4254 | +8.0012 | 93.9394 | 93.9394 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +7.2222 |

### OLD500

| Scenario | n | Micro control % | Micro Whisper % | Micro difference pp | Intent control % | Intent Whisper % | Intent difference pp | Intent saves | Intent harms | Scenario difference pp | Action difference pp | Row-F1 difference pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 28 | 20.3747 | 26.4062 | +6.0315 | 89.2857 | 85.7143 | -3.5714 | 0 | 1 | -3.5714 | -3.5714 | +4.5527 |
| audio | 28 | 0.0000 | 0.0000 | +0.0000 | 78.5714 | 82.1429 | +3.5714 | 1 | 0 | -3.5714 | +3.5714 | +0.0000 |
| calendar | 28 | 37.0632 | 39.3520 | +2.2888 | 75.0000 | 75.0000 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.2963 |
| cooking | 28 | 52.5055 | 47.7699 | -4.7356 | 64.2857 | 67.8571 | +3.5714 | 1 | 0 | +0.0000 | +3.5714 | -3.9417 |
| datetime | 28 | 34.5314 | 34.5314 | +0.0000 | 89.2857 | 85.7143 | -3.5714 | 0 | 1 | +0.0000 | -7.1429 | +0.0000 |
| email | 28 | 29.7266 | 29.7266 | +0.0000 | 82.1429 | 82.1429 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.0000 |
| general | 28 | 30.6383 | 29.7082 | -0.9301 | 35.7143 | 32.1429 | -3.5714 | 0 | 1 | +3.5714 | -3.5714 | -0.4456 |
| iot | 28 | 45.3591 | 47.7665 | +2.4074 | 82.1429 | 78.5714 | -3.5714 | 0 | 1 | -3.5714 | -3.5714 | +0.0000 |
| lists | 28 | 43.6230 | 45.8451 | +2.2221 | 92.8571 | 92.8571 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.4733 |
| music | 28 | 48.9234 | 48.9234 | +0.0000 | 64.2857 | 71.4286 | +7.1429 | 3 | 1 | +3.5714 | +3.5714 | +0.0000 |
| news | 28 | 34.7117 | 35.6263 | +0.9146 | 82.1429 | 78.5714 | -3.5714 | 0 | 1 | -3.5714 | -7.1429 | +1.3254 |
| play | 28 | 54.7317 | 47.8079 | -6.9238 | 35.7143 | 21.4286 | -14.2857 | 0 | 4 | -7.1429 | -14.2857 | -8.7143 |
| qa | 28 | 55.9969 | 47.2696 | -8.7273 | 57.1429 | 57.1429 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | -4.0014 |
| recommendation | 28 | 35.1412 | 36.2209 | +1.0797 | 53.5714 | 53.5714 | +0.0000 | 1 | 1 | +0.0000 | +0.0000 | -3.9888 |
| social | 27 | 33.0709 | 40.1114 | +7.0406 | 81.4815 | 81.4815 | +0.0000 | 1 | 1 | +3.7037 | +0.0000 | +5.3495 |
| takeaway | 27 | 45.4519 | 41.7556 | -3.6963 | 70.3704 | 70.3704 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | -6.3168 |
| transport | 27 | 44.5910 | 35.7834 | -8.8076 | 85.1852 | 85.1852 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | -8.3235 |
| weather | 27 | 12.7660 | 17.0213 | +4.2553 | 92.5926 | 92.5926 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +1.8519 |

### DEV1000

| Scenario | n | Micro control % | Micro Whisper % | Micro difference pp | Intent control % | Intent Whisper % | Intent difference pp | Intent saves | Intent harms | Scenario difference pp | Action difference pp | Row-F1 difference pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 58 | 28.4260 | 31.2074 | +2.7814 | 89.6552 | 87.9310 | -1.7241 | 0 | 1 | -1.7241 | -1.7241 | +2.1978 |
| audio | 30 | 0.0000 | 0.0000 | +0.0000 | 80.0000 | 83.3333 | +3.3333 | 1 | 0 | -3.3333 | +3.3333 | +0.0000 |
| calendar | 61 | 31.9363 | 34.6818 | +2.7455 | 65.5738 | 67.2131 | +1.6393 | 2 | 1 | -1.6393 | +1.6393 | +1.9745 |
| cooking | 37 | 56.7106 | 52.9575 | -3.7531 | 64.8649 | 70.2703 | +5.4054 | 2 | 0 | +0.0000 | +5.4054 | -2.9829 |
| datetime | 61 | 35.2742 | 33.4382 | -1.8360 | 85.2459 | 88.5246 | +3.2787 | 3 | 1 | +1.6393 | +0.0000 | -1.6393 |
| email | 61 | 29.3320 | 33.3020 | +3.9700 | 88.5246 | 85.2459 | -3.2787 | 0 | 2 | -1.6393 | -3.2787 | +0.8197 |
| general | 61 | 23.0621 | 25.0373 | +1.9751 | 37.7049 | 36.0656 | -1.6393 | 1 | 2 | +0.0000 | -1.6393 | +0.5669 |
| iot | 61 | 54.6435 | 54.6346 | -0.0089 | 88.5246 | 83.6066 | -4.9180 | 0 | 3 | -1.6393 | -4.9180 | -1.4506 |
| lists | 60 | 39.2100 | 40.9294 | +1.7195 | 88.3333 | 88.3333 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +0.2209 |
| music | 51 | 46.1736 | 50.1961 | +4.0225 | 68.6275 | 72.5490 | +3.9216 | 3 | 1 | +1.9608 | +1.9608 | +1.3856 |
| news | 60 | 38.1871 | 38.2235 | +0.0363 | 83.3333 | 78.3333 | -5.0000 | 0 | 3 | -5.0000 | -1.6667 | -0.1928 |
| play | 60 | 58.2116 | 54.1334 | -4.0782 | 36.6667 | 28.3333 | -8.3333 | 0 | 5 | -1.6667 | -8.3333 | -3.8416 |
| qa | 60 | 59.7447 | 53.2447 | -6.5000 | 63.3333 | 63.3333 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | -2.9662 |
| recommendation | 60 | 46.3338 | 50.9975 | +4.6637 | 70.0000 | 68.3333 | -1.6667 | 1 | 2 | +0.0000 | -1.6667 | +0.8229 |
| social | 60 | 31.9120 | 34.1202 | +2.2082 | 78.3333 | 76.6667 | -1.6667 | 1 | 2 | +0.0000 | -1.6667 | +2.1501 |
| takeaway | 39 | 42.6228 | 39.1674 | -3.4554 | 74.3590 | 74.3590 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | -4.3732 |
| transport | 60 | 37.6776 | 32.3106 | -5.3669 | 86.6667 | 86.6667 | +0.0000 | 0 | 0 | +0.0000 | +1.6667 | -4.5749 |
| weather | 60 | 16.6733 | 22.8567 | +6.1834 | 93.3333 | 93.3333 | +0.0000 | 0 | 0 | +0.0000 | +0.0000 | +4.8056 |

## Final-answer saves and harms

| Population | Metric | Saves | Harms | Ties |
| --- | --- | ---: | ---: | ---: |
| NEW500 | scenario_action_exact | 7 | 11 | 482 |
| NEW500 | scenario_exact | 3 | 7 | 490 |
| NEW500 | action_exact | 9 | 10 | 481 |
| OLD500 | scenario_action_exact | 7 | 12 | 481 |
| OLD500 | scenario_exact | 7 | 10 | 483 |
| OLD500 | action_exact | 6 | 14 | 480 |
| DEV1000 | scenario_action_exact | 14 | 23 | 963 |
| DEV1000 | scenario_exact | 10 | 17 | 973 |
| DEV1000 | action_exact | 15 | 24 | 961 |

## Scientific and runtime limits

- Both arms generated their own plan, solve and revise over the same 1,000 rows, using original speech packets, compact knowledge, full labels, max_tokens 256, c65536 and four slots. The fixed contrast changes evidence availability before revision. It is not an optimized policy or a direct-model comparison.
- Control and recovered treatment each finalized 3,000 contacts. The failed original treatment remains ABORTED after 2,000 contacts; it is not erased or an independent successful replication. Preserve all fit contacts and the 1,000-source Whisper preparation plus its separate failed contacts.
- The shared renderer repair was independently validated, and all 3,000 actual control requests retained byte parity. The original resident service was retained through both complete arms.
- Independently generated predecessors and fixed arm order retain run/order uncertainty. Final saves and harms are observed paired outcomes, not proof of a particular per-sample causal mechanism.
- OBS availability, ORG retrieval, SUPPLY serialization and USE revision still require the registered trace diagnosis. Do not call a changed unscored draft a corrected draft. No new memory rule or targeted selection is admitted by this result.
- The recovered campaign exited successfully at 22:21:43.993127 UTC. Qwen was intentionally stopped at 22:26:59.614368 UTC for the exclusive retrieval encoder window; this exceeded the one-minute handoff target. Source/read registration and service handoff contributed to the gap.
- Keep the source commits and sealed artifacts intact. Cost and latency are reported, not reward penalties.

## Source bindings

- Read registration: docs/readiness/2026-09-12-slurp-speech-observation-analysis-registration-v1.json.
- Frozen analysis protocol: docs/readiness/2026-09-12-slurp-speech-observation-analysis-protocol-v2.md.
- Saved comparison: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-SPEECH-OBSERVATION-TRANSPORT-RECOVERY-ANALYSIS-V1/score-contrasts.json.
- Saved comparison SHA-256: 273999c83a83a6ee3d2a41ac24d303eb1fdf814cd01ccec60c348ad3bb27da5b.
- Root decision: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/coordination/slurp-speech-observation-root-decision-v1.json.
- Both complete source manifests, first-score hashes, outputs, traces, phase artifacts, configuration identities and executed commits are pinned by the read registration.
