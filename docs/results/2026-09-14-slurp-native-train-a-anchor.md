# SLURP native TRAIN Fold A anchor: complete result

Date: 2026-09-14. Exploratory TRAIN construction anchor; no held-out or confirmatory claim.

The recovery completed 1,080 ordered recordings and 5,417 model calls. The shared campaign ran the official full score once, with per-sample statistics, and finalized the attempt. Source integrity, scorer identity and complete roster passed before root released quality. The frozen source is 826a77c7bd9030ccbc25f2b74cd6fa4ed69db561. Preserve the earlier aborted five-call attempt separately.

## Full-task result

| Metric | Natural mixture | Equal scenario |
|---|---:|---:|
| Official SLU micro F1 | 48.53363% | 46.83639% |
| Intent accuracy | 77.96296% (842/1080) | 77.96296% |
| Scenario accuracy | 84.81481% | 84.81481% |
| Action accuracy | 79.25926% | 79.25926% |
| Exact entity-pair micro F1 | 29.49757% | 28.42863% |
| Utterance entities exact | 35.09259% (379/1080) | 35.09259% |
| Intent and entities fully exact | 29.35185% (317/1080) | 29.35185% |

Pool official sufficient statistics before computing micro F1; equal-scenario F1 averages the 18 separately pooled ratios. Do not call mean per-sample F1 micro F1. Entity-pair F1 is distinct from utterance exact match. All 7 malformed predictions remain in the denominator. No same-roster direct-model effect is estimated here; prior DEV paired evidence remains separate.

## Candidate, supply and control diagnosis

C0 and C1 share the same source: this incumbent executes no candidate refresh. Gold coverage is 937/1080 (86.75926%), with 842/937 (89.86126%) correct final intents among covered samples, 95 covered-but-wrong cases and 143 uncovered cases. No uncovered case is finally correct. Distinct candidate widths are 57 singletons, 225 pairs and 798 triples.

The actual initial request contains the gold intent's own knowledge card in 947 cases. Four full-cohort cells are: supplied and covered 914; supplied but missed 33; absent own card but covered 23; neither 110. Own-card-conditioned coverage is 96.51531%; without it, 17.29323%. These are descriptive associations. Other cards can contain useful contrasts, and neither semantic use nor causal effects are proven.

There are 525 correct-intent predictions with nonexact entities. This large residual prevents treating candidate coverage as the sole optimization objective. The control plane produces six REVISE routes but only five executed second Solver visits; one route reaches its bounded exhaustion. The contact distribution is 1072 episodes with five model calls, five with nine, and three with four. The official cost scorer records 1082 tool actions; they are not additional core generations.

## Every scenario

| Scenario | n | C0 coverage | Choice given coverage | Intent accuracy | SLU F1 | Fully exact |
|---|---:|---:|---:|---:|---:|---:|
| alarm | 60 | 96.67% | 86.21% | 83.33% | 52.66% | 31.67% |
| audio | 60 | 91.67% | 83.64% | 76.67% | 47.75% | 58.33% |
| calendar | 60 | 81.67% | 91.84% | 75.00% | 48.38% | 20.00% |
| cooking | 60 | 91.67% | 92.73% | 85.00% | 62.47% | 35.00% |
| datetime | 60 | 95.00% | 87.72% | 83.33% | 59.52% | 30.00% |
| email | 60 | 88.33% | 96.23% | 85.00% | 36.64% | 21.67% |
| general | 60 | 43.33% | 84.62% | 36.67% | 15.45% | 20.00% |
| iot | 60 | 95.00% | 91.23% | 86.67% | 55.53% | 28.33% |
| lists | 60 | 85.00% | 98.04% | 83.33% | 43.55% | 40.00% |
| music | 60 | 86.67% | 88.46% | 76.67% | 34.53% | 41.67% |
| news | 60 | 83.33% | 96.00% | 80.00% | 44.24% | 40.00% |
| play | 60 | 88.33% | 66.04% | 58.33% | 46.82% | 13.33% |
| qa | 60 | 78.33% | 95.74% | 75.00% | 57.04% | 33.33% |
| recommendation | 60 | 95.00% | 94.74% | 90.00% | 49.75% | 35.00% |
| social | 60 | 81.67% | 81.63% | 66.67% | 34.74% | 8.33% |
| takeaway | 60 | 91.67% | 92.73% | 85.00% | 48.84% | 23.33% |
| transport | 60 | 95.00% | 91.23% | 86.67% | 51.34% | 23.33% |
| weather | 60 | 93.33% | 96.43% | 90.00% | 53.81% | 25.00% |

## Root decision

Admit the prepared complete-system successor on the same Fold A roster: Reviewer-selected evidence tools, one Planner candidate refresh, and latest-candidate Solver consumption. Keep initial knowledge supply fixed for this flight. The gaps justify this bounded system experiment but do not establish that tools will improve quality. A later retrieval/value change must follow this experiment's complete decision.

The primary outcome remains complete official SLU F1, with paired speaker-cluster CI90, all strata, saves/harms and cost reporting. Stage-only improvement cannot advance a worse full-task version. Preserve Fold B until a selected candidate is frozen. No real training-free proposal-and-disjoint-evaluation cycle is complete yet.

## Source receipts

- DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/postseal-structural-gate-v1.json; SHA256 f0fc0b02ef54e48bbd66be3b27896d5a428d8e5f718cb6fa9e83b605d252ce18.
- DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/root-quality-release-v1.json; SHA256 0be030c3d4d43bd27035575ff455cf30830d042b5f35d3ab6b83ff69ecc43bdf.
- DATA/coordination/slurp-native-dual-store-train-fold-a-anchor-recovery-v1/root-analysis-v1.json; SHA256 25b665cb4ba09c6a7bdf2b68ceba41ebd6ca2edc0660aff0141f3050114e0684.
- DATA/analysis/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/native-train-support-diagnostics-v1.json; SHA256 214b3e058782703490558c54805541d9722dbafe44f64a5bb1880b16785f9e34.
- DATA/analysis/SAEA-SLURP-NATIVE-DUAL-STORE-TRAIN-FOLD-A-ANCHOR-RECOVERY-V1/full-task-and-strata-v1.json; SHA256 380c2c69cbadc70804b1687248a4466468421bf39fd808ef5a5c84eaacbdc746.
- DATA/coordination/slurp-native-candidate-refresh-tools-train-fold-a-v1/admission-v1.json; SHA256 0d567c24a03d0d7271afbd8081b799b00865484c144c9226ef99c47ec8deafca.
