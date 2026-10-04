# Initial deterministic context systems: complete N20 read

Root read completed 2026-10-04T09:43:14.877685+00:00. All six members independently finalized20 rows with verified seals,one unique successful complete official score each and no failed jobs. Exact READ: SAEA-SLURP-CONTEXT-INITIAL4-N20-READ-V1. No scorer replay.

## Decision

Keep seed as the formal incumbent. Do not expand the input panel or adopt a new system. No candidate exceeds seed on pooled quality in this observation. The candidate population remains the registered shared initialization for separate TF and GEPA learning; algorithmic selection/retention is distinct from beating seed or formal adoption. Proceed with the prospectively bounded complete-feedback learner interfaces, not a root-authored replacement policy.

These are20 reused TRAIN inputs. A/A differs by -5.681 F1 percentage points with unchanged intent. Temperature0 and a fixed seed did not produce identical results in this measured chain. The source of the difference has not been isolated. All candidate-versus-A/A F1 intervals include zero. One negative candidate-versus-seed interval alone does not overcome the small-panel and replicate limitations. No stable benefit,formal harm,generalization,learning gain or independent-validation claim is made.

## Complete-system measurements

| Member | SLU-F1 (%) | Intent (%) | Reliable completion (%) | Contacts | All-sample mean (s) | Non-first mean (s) | First4 mean (s) | After first4 mean (s) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| seed | 63.521 | 70.0 | 100.0 | 110 | 30.356 | 29.505 | 36.494 | 28.821 |
| seed-aa | 57.840 | 70.0 | 100.0 | 119 | 34.208 | 33.548 | 32.684 | 34.590 |
| speech-evidence | 53.318 | 70.0 | 100.0 | 95 | 58.530 | 59.448 | 41.188 | 62.866 |
| coverage-ledger | 60.120 | 60.0 | 100.0 | 104 | 29.502 | 29.148 | 31.790 | 28.930 |
| counterexample-check | 48.784 | 55.0 | 100.0 | 125 | 86.650 | 85.953 | 73.843 | 89.852 |
| semantic-frame | 55.969 | 70.0 | 100.0 | 98 | 48.437 | 49.614 | 50.455 | 47.933 |

There were651 actual generation model contacts across120 trajectories. All six recorded zero active knowledge-tool calls. Reliability here is the registered delivery criterion,not answer correctness. The episode latency boundary is admission to settled workflow; it excludes unmeasured business preparation/persistence. Non-first is an admission-order statistic,not a claim of a warm cache.

## Paired uncertainty and damage

| Contrast | F1 delta (pp) | Paired95% interval (pp) | Whole-answer repairs | Whole-answer damage |
|---|---:|---|---:|---:|
| counterexample-check-minus-aa | -9.057 | [-31.887,10.886] | 0 | 7 |
| counterexample-check-minus-parent | -14.738 | [-34.936,-0.282] | 0 | 7 |
| coverage-ledger-minus-aa | 2.280 | [-9.584,12.091] | 0 | 2 |
| coverage-ledger-minus-parent | -3.401 | [-20.555,9.932] | 0 | 2 |
| same-request-null | -5.681 | [-21.433,3.055] | 0 | 0 |
| semantic-frame-minus-aa | -1.871 | [-10.745,4.326] | 0 | 1 |
| semantic-frame-minus-parent | -7.552 | [-22.608,3.576] | 0 | 1 |
| speech-evidence-minus-aa | -4.522 | [-14.707,2.789] | 0 | 2 |
| speech-evidence-minus-parent | -10.203 | [-25.908,0.866] | 0 | 2 |

Intervals use the registered10000 paired utterance bootstrap draws,seed20261001. Whole-answer changes are cross-system associations,not causal attribution to a revision/node. Every candidate has zero complete-answer repairs and at least one damaged exact answer relative to seed on this panel. Retain both improvements in partial counts and these failures in the learner evidence.

## Node costs and cache observations

| Member | Node | Contacts | Input reused (%) | Mean prefill (s) | Mean decode (s) | Mean client transport (s) |
|---|---|---:|---:|---:|---:|---:|
| seed | perception | 20 | 63.09 | 0.829 | 5.957 | 7.640 |
| seed | planner | 30 | 95.11 | 0.423 | 0.320 | 0.972 |
| seed | reviewer | 30 | 96.91 | 0.281 | 7.199 | 7.883 |
| seed | solver | 30 | 56.20 | 2.267 | 1.977 | 4.748 |
| seed-aa | perception | 20 | 63.09 | 0.661 | 5.459 | 6.390 |
| seed-aa | planner | 33 | 94.99 | 0.365 | 0.207 | 0.825 |
| seed-aa | reviewer | 33 | 96.86 | 0.235 | 8.682 | 9.093 |
| seed-aa | solver | 33 | 60.38 | 2.228 | 2.715 | 5.468 |
| speech-evidence | perception | 20 | 59.30 | 1.077 | 10.511 | 11.863 |
| speech-evidence | planner | 25 | 19.64 | 4.845 | 0.223 | 5.327 |
| speech-evidence | reviewer | 25 | 21.22 | 4.271 | 13.511 | 19.122 |
| speech-evidence | solver | 25 | 20.84 | 5.977 | 4.037 | 11.175 |
| coverage-ledger | perception | 20 | 62.62 | 0.749 | 3.984 | 5.040 |
| coverage-ledger | planner | 28 | 94.93 | 0.400 | 0.191 | 0.823 |
| coverage-ledger | reviewer | 28 | 96.19 | 0.317 | 8.422 | 9.037 |
| coverage-ledger | solver | 28 | 53.87 | 2.291 | 3.154 | 6.099 |
| counterexample-check | perception | 20 | 62.76 | 1.048 | 11.358 | 13.018 |
| counterexample-check | planner | 35 | 22.07 | 4.600 | 0.476 | 5.452 |
| counterexample-check | reviewer | 35 | 23.32 | 4.577 | 19.640 | 24.988 |
| counterexample-check | solver | 35 | 22.80 | 5.365 | 4.506 | 10.245 |
| semantic-frame | perception | 20 | 59.49 | 1.008 | 6.965 | 8.233 |
| semantic-frame | planner | 26 | 19.05 | 4.616 | 0.232 | 5.544 |
| semantic-frame | reviewer | 26 | 96.55 | 0.249 | 14.192 | 14.568 |
| semantic-frame | solver | 26 | 28.73 | 4.772 | 3.402 | 9.131 |

The measured slow configurations combine higher downstream prefill and longer Reviewer decoding. Counterexample-check has35 Reviewer contacts,mean19.640 seconds decoding and4.577 seconds prefill per contact; seed has30,7.199 and0.281 respectively. Speech-evidence has fewer total contacts than seed but nearly twice its mean episode latency. Fewer calls alone is not an efficiency result.

The current data do not identify eviction as the cause of recomputation. Changed layouts/prefixes,history and schema rendering are coupled with policy text. Semantic-frame Reviewer retains96.55% input reuse yet averages14.192 seconds decoding; Planner reuse is19.05% with4.616 seconds prefill. Cache reuse helps explain measured cost but does not by itself explain quality or establish a node causal effect. Preserve independent node context freedom and evaluate the complete tradeoff.

The measured non-dominated set contains seed and coverage-ledger. Coverage-ledger is marginally faster but has lower observed F1 and intent. A/A is retained for calibration rather than treated as a selectable duplicate policy.

## Per-stratum evidence

Each cell gives SLU-F1% / intent%. Report all strata; do not select a policy on an individual stratum.

| Stratum | n | seed | seed-aa | speech-evidence | coverage-ledger | counterexample-check | semantic-frame |
|---|---:|---:|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 33.33 | 0.00 / 0.00 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 0.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 59.09 / 100.00 | 100.00 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 93.69 / 100.00 | 57.14 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 73.03 / 100.00 | 40.00 / 100.00 |
| qa | 2 | 53.73 / 100.00 | 58.54 / 100.00 | 62.75 / 100.00 | 50.00 / 50.00 | 43.24 / 50.00 | 62.75 / 100.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 0.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 41.79 / 0.00 | 41.79 / 0.00 | 0.00 / 0.00 | 78.26 / 0.00 | 41.79 / 100.00 | 41.79 / 0.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |

Equal-stratum macro and natural-mixture pooled results remain separately preserved in the linked JSON; do not average stratum F1 to recreate the official pooled scorer.

## Next bounded work

Prepare fresh complete-family inputs for the separate TF and GEPA algorithms. Preserve all20 cases,role-level source material and uncertainty,including failures and no-change. Let admitted GPT-6.1 Sol actors propose edits within each original algorithm. Keep source policies/knowledge/data frozen,explicit output contracts and actual capacity checks. Each changed trial requires separately registered seed/A/A plusK4 complete systems before quality read. Keep N20 until root review; no automatic scaling or8x400. The heartbeat remains paused and other-carrier holds remain.

No earlier root incidental log content is exported. The current source material is freshly derived from the exact qualified complete family. This report stays root-only; semantic actors receive only their separately admitted stage inputs.

## Evidence

Full registered report: `/mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-CONTEXT-INITIAL4-N20-READ-V1/report.json`. Per-member node/sample timing and source specifications remain next to it. Full original generations and six official scores remain immutable.
