# SLURP task-agent paired analysis summary

Direction is right minus left as frozen in each contrast. The first four NEW500 rows for the two main contrasts and two main outcomes are primary; every other row is secondary or derived. Root owns all verdicts.

| Scope | Contrast | Population | Outcome | Left % | Right % | Natural delta pp | Speaker CI90 pp | Equal-scenario delta pp |
|---|---|---:|---|---:|---:|---:|---:|---:|
| Primary | Knowledge - direct | NEW500 | scenario_action_exact | 73.000 | 67.600 | -5.400 | [-7.371, -3.390] | -5.732 |
| Primary | Knowledge - direct | NEW500 | slu_f1_micro | 37.363 | 38.099 | 0.736 | [-2.137, 3.602] | 1.137 |
| Secondary | Knowledge - direct | OLD500 | scenario_action_exact | 71.400 | 65.200 | -6.200 | [-8.216, -4.242] | -6.224 |
| Secondary | Knowledge - direct | OLD500 | slu_f1_micro | 35.076 | 39.077 | 4.001 | [1.259, 6.822] | 3.579 |
| Secondary | Knowledge - direct | DEV1000 | scenario_action_exact | 72.200 | 66.400 | -5.800 | [-7.122, -4.497] | -6.023 |
| Secondary | Knowledge - direct | DEV1000 | slu_f1_micro | 36.242 | 38.577 | 2.336 | [0.374, 4.292] | 2.231 |
| Primary | Frame - knowledge | NEW500 | scenario_action_exact | 67.600 | 75.600 | 8.000 | [5.882, 10.115] | 8.570 |
| Primary | Frame - knowledge | NEW500 | slu_f1_micro | 38.099 | 39.597 | 1.498 | [-0.554, 3.692] | 2.312 |
| Secondary | Frame - knowledge | OLD500 | scenario_action_exact | 65.200 | 73.200 | 8.000 | [6.043, 10.063] | 8.010 |
| Secondary | Frame - knowledge | OLD500 | slu_f1_micro | 39.077 | 36.672 | -2.405 | [-5.236, 0.251] | -3.468 |
| Secondary | Frame - knowledge | DEV1000 | scenario_action_exact | 66.400 | 74.400 | 8.000 | [6.718, 9.319] | 8.158 |
| Secondary | Frame - knowledge | DEV1000 | slu_f1_micro | 38.577 | 38.170 | -0.407 | [-2.150, 1.313] | -1.534 |
| Derived | Frame - direct | NEW500 | scenario_action_exact | 73.000 | 75.600 | 2.600 | [0.693, 4.398] | 2.838 |
| Derived | Frame - direct | NEW500 | slu_f1_micro | 37.363 | 39.597 | 2.234 | [-0.378, 4.826] | 3.449 |
| Derived | Frame - direct | OLD500 | scenario_action_exact | 71.400 | 73.200 | 1.800 | [0.385, 3.241] | 1.786 |
| Derived | Frame - direct | OLD500 | slu_f1_micro | 35.076 | 36.672 | 1.596 | [-0.320, 3.535] | 0.111 |
| Derived | Frame - direct | DEV1000 | scenario_action_exact | 72.200 | 74.400 | 2.200 | [0.994, 3.403] | 2.135 |
| Derived | Frame - direct | DEV1000 | slu_f1_micro | 36.242 | 38.170 | 1.928 | [0.160, 3.666] | 0.697 |

Paired result: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-TASK-AGENT-PAIRED-ANALYSIS-V1/paired-analysis-v1.json`
Paired result SHA-256: `a30ef3eb837f5294749caadac8ae1d1e260b6627e29e430e118934ae94d95975`

Operational qualification: knowledge/frame selected value IDs and order match for all 1,000 samples, while first-phase response hashes match for 823/1,000. Knowledge has 42 unparsed final outputs associated with the already verified unexpected literal token observation. These facts do not identify a cause and the frame contrast must not be attributed wholly to semantic knowledge. Root evidence: `DATA/coordination/slurp-task-agent-root-operational-verification-v1.json` SHA-256 `b6489603273ab2f3ac7713f44c910314f9f4c5f8ab55824c5cdf1ee4ebe08fbc` and `DATA/coordination/slurp-task-agent-unexpected-token-provenance-v1.json` SHA-256 `4ea0b2c0da25e98ad44a2b565260fdf6d567c4ae15a2f1c7d09f3e8bf17fae24`.

The direct arm has a known serialization deviation. It prevents a claim of an untouched result-read barrier; it does not show a runtime phase-boundary failure.
