# DESCRIPTIVE: initial system-text feedback

Initial feedback and same-policy A/A instrument observation only. No candidate, feedback-learning benefit, causal node contribution or adoption is established.

| Member | Rows | Official SLU-F1 | Intent | Reliable completion | Model calls | Knowledge calls |
|---|---:|---:|---:|---:|---:|---:|
| seed | 400 | 59.6681% | 76.50% | 99.75% | 2790 | 0 |
| seed-aa | 400 | 59.2141% | 76.50% | 99.50% | 2792 | 0 |

Frozen F_ref: 0.5966805915811396.

A/A minus seed slu_f1: -0.4540 pp; CI95 [-2.1971, 1.2405] pp.
A/A minus seed intent: +0.0000 pp; CI95 [-2.0000, 2.0000] pp.

Both runs offered the knowledge opportunity and recorded zero actual tool calls. This initial pair cannot establish targeted knowledge-consumption benefit.

| Scenario | n | Seed SLU-F1 | A/A SLU-F1 | Seed intent | A/A intent |
|---|---:|---:|---:|---:|---:|
| alarm | 11 | 57.99% | 57.06% | 63.64% | 63.64% |
| audio | 22 | 41.01% | 61.51% | 59.09% | 59.09% |
| calendar | 26 | 65.45% | 67.53% | 84.62% | 84.62% |
| cooking | 23 | 65.06% | 63.01% | 73.91% | 73.91% |
| datetime | 23 | 61.01% | 59.91% | 95.65% | 91.30% |
| email | 19 | 45.84% | 50.15% | 94.74% | 94.74% |
| general | 27 | 21.62% | 24.90% | 29.63% | 29.63% |
| iot | 20 | 63.02% | 60.27% | 70.00% | 75.00% |
| lists | 26 | 49.02% | 45.80% | 88.46% | 88.46% |
| music | 18 | 26.67% | 28.57% | 61.11% | 61.11% |
| news | 26 | 55.20% | 53.82% | 84.62% | 80.77% |
| play | 21 | 60.98% | 58.57% | 80.95% | 80.95% |
| qa | 23 | 53.66% | 51.16% | 73.91% | 73.91% |
| recommendation | 18 | 61.08% | 54.95% | 77.78% | 77.78% |
| social | 27 | 73.25% | 74.35% | 85.19% | 88.89% |
| takeaway | 25 | 59.22% | 60.37% | 80.00% | 80.00% |
| transport | 20 | 69.83% | 65.95% | 80.00% | 80.00% |
| weather | 25 | 65.41% | 60.17% | 88.00% | 88.00% |

Arithmetic mean of the eighteen within-scenario pooled F1 values and intent accuracies; descriptive, not the official pooled metric.

All failures, abstentions and unchanged outcomes remain in feedback. Raw outputs, scores, original failed score-entry evidence and STOP were not modified. The recovery is owner216's single approved scoring entry, not a new generation or second scientific score. Historical roster exposure limits interpretation.

Equal-scenario macro values: seed SLU-F1 55.2941%, intent 76.1828%; A/A SLU-F1 55.4474%, intent 76.2111%. These descriptive macros do not replace the official pooled result.

At these point estimates seed has higher quality and reliable completion, equal intent/tool usage and two fewer model calls than A/A. This same-policy sampling observation is not a treatment gain or scientific adoption. The A/A SLU-F1 interval crosses zero; no threshold was relaxed and no extra sampling was added.
