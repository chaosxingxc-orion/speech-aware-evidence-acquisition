# Audio2Tool native role system: complete 4,000-row comparison

Date: 2026-09-15. Status: complete generation, first scoring and registered paired statistics; primary gain with a failed tool-accuracy guard. Candidate attribution is complete in the source-bound sections below. GPU dispatch is held by the owner.

## What the evidence establishes

The system improves the official primary-call exact-match point estimate from 18.500% to 22.550% (+4.050 percentage points, 740 to 902 correct rows), while official primary-tool accuracy falls from 62.025% to 58.425% (-3.600 points). Keep both findings. The frozen promising-system rule requires a nonnegative tool-accuracy point change, so that guard fails while the completed primary intervals pass their threshold. This is evidence of an improvable system, not adoption, a replicated benefit, component causality, generalization or algorithmic training-free RL.

The complete comparison retains all 4,000 previously exposed discovery rows: eight tiers of 500 and 2,097 cross-tier query clusters. Both arms use the shared execution harness and frozen core. The system adds Perception, Solver, Reviewer and Planner, separate activation and parameter-meaning stores, optional analytical task-contract checks and one bounded revision. The sole recovery changes Planner control serialization; preserve the preceding aborted attempt and its exposure separately.

## Metric meanings and primary decision

The published official protocol parses and scores the first tool call. Its exact match requires that primary tool and its extracted parameters to match; it is not ordered full-sequence correctness. The repository v2 exact metric instead compares normalized multisets of complete calls, preserving multiplicities but ignoring order, and applies its existing default stripping/type coercion. Repository ordered-tool accuracy checks order but not argument correctness. Do not describe either as ordered full-call exact match, which is not available in the frozen analysis.

The published Table 3 entries below are the already pinned external reference, not a matched model/population or a mathematical ceiling. The registered primary threshold is min(1 point, 10% of the published equal-tier exact headroom). Here the published mean is 29.675% and the direct mean is 18.500%, giving a 1.000-point threshold. Natural and equal-tier primary CI95 lower bounds must exceed it; official tool accuracy and macro parameter F1 point changes must also be nonnegative.

<!-- PAIRED_STATUS_START -->
The original CPU job completed normally at 11:04:24.138853 UTC. All 10,000 paired whole-query-cluster bootstrap draws, seed 20260914, are retained. No statistical rule or first score changed.

| Primary weighting | Direct exact | System exact | Difference (points) | Paired CI95 (points) |
| --- | ---: | ---: | ---: | --- |
| Natural mixture | 18.500% | 22.550% | +4.050 | [2.963, 5.165] |
| Equal tier | 18.500% | 22.550% | +4.050 | [2.970, 5.152] |
| Equal domain (sensitivity) | 30.523% | 37.141% | +6.618 | [4.479, 8.728] |

Both required primary lower bounds exceed the frozen 1.000-point threshold. Macro parameter F1 passes its nonnegative point check; tool accuracy fails. The exact frozen decision is PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED. Keep the demonstrated primary improvement and repair opportunity; do not claim a stable adopted system or retroactively relax the guard.

| Diagnostic | Natural difference and CI90 (points) | Equal-tier difference and CI90 | Equal-domain difference and CI90 |
| --- | --- | --- | --- |
| official_exact_match | +4.050 [3.133, 4.983] | +4.050 [3.138, 4.982] | +6.618 [4.850, 8.369] |
| official_macro_parameter_f1 | +4.753 [3.765, 5.746] | +4.753 [3.762, 5.743] | +7.716 [5.937, 9.510] |
| official_macro_parameter_precision | +5.425 [4.407, 6.421] | +5.425 [4.407, 6.420] | +8.271 [6.492, 10.074] |
| official_macro_parameter_recall | +4.610 [3.659, 5.572] | +4.610 [3.657, 5.573] | +9.089 [7.558, 10.623] |
| official_micro_parameter_f1 | +5.743 [4.694, 6.785] | +5.170 [4.192, 6.150] | +12.047 [9.703, 14.429] |
| official_tool_accuracy | -3.600 [-4.717, -2.481] | -3.600 [-4.720, -2.484] | -4.036 [-5.340, -2.749] |
| repo_ordered_tool_sequence_accuracy | -3.200 [-4.346, -2.067] | -3.200 [-4.350, -2.066] | -3.796 [-5.241, -2.394] |

All eight-tier and three-domain point tables are retained below and in the paired artifact. Per-stratum confidence intervals were not emitted by the frozen implementation; do not invent them.
<!-- PAIRED_STATUS_END -->

| Complete-roster metric | Direct | System | Difference (points) |
| --- | ---: | ---: | ---: |
| Official primary-call exact match | 18.500% | 22.550% | +4.050 |
| Official primary-tool accuracy | 62.025% | 58.425% | -3.600 |
| Official macro parameter F1 | 30.149% | 34.902% | +4.753 |
| Official micro parameter F1 | 24.535% | 30.278% | +5.743 |
| Repo v2 normalized call-multiset exact match | 14.600% | 18.500% | +3.900 |
| Repo v2 ordered-tool accuracy | 53.525% | 50.325% | -3.200 |

The repo exact point estimate is descriptive; its paired interval was not registered in this analysis. Micro parameter F1 uses summed correct/predicted/gold key counts, not the mean of per-row F1. Official parse failures decline from 28 to 16.

## Complete strata

All entries are percentages. Each tier contains 500 rows. Paper columns retain the frozen published reference; repo columns use the distinct v2 call-multiset metric.

| Tier | Paper exact | Official direct | Official system | Difference (points) | Repo direct | Repo system |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| tier1_direct | 92.4 | 16.0 | 9.8 | -6.2 | 19.6 | 21.4 |
| tier2_parametric | 15.6 | 28.2 | 35.2 | +7.0 | 28.4 | 33.0 |
| tier3_multi_intent | 28.6 | 20.4 | 27.4 | +7.0 | 2.6 | 6.8 |
| tier4_implicit | 11.3 | 6.4 | 9.8 | +3.4 | 6.4 | 9.6 |
| tier5_needle | 36.0 | 21.8 | 27.8 | +6.0 | 23.2 | 30.2 |
| tier6_correction | 24.8 | 24.0 | 29.0 | +5.0 | 23.6 | 29.0 |
| tier7_multiturn | 16.3 | 10.6 | 12.4 | +1.8 | 10.6 | 12.0 |
| tier8_intent_blending | 12.4 | 20.6 | 29.0 | +8.4 | 2.4 | 6.0 |

| Tier | Paper tool accuracy | Official direct | Official system | Difference (points) |
| --- | ---: | ---: | ---: | ---: |
| tier1_direct | 92.4 | 67.2 | 61.4 | -5.8 |
| tier2_parametric | 84.6 | 78.4 | 75.8 | -2.6 |
| tier3_multi_intent | 74.7 | 67.6 | 64.8 | -2.8 |
| tier4_implicit | 33.4 | 29.0 | 24.4 | -4.6 |
| tier5_needle | 90.6 | 80.4 | 74.4 | -6.0 |
| tier6_correction | 81.5 | 76.0 | 72.8 | -3.2 |
| tier7_multiturn | 54.6 | 49.0 | 45.4 | -3.6 |
| tier8_intent_blending | 41.7 | 48.6 | 48.4 | -0.2 |

The published source does not supply a comparable per-domain table.

| Domain | Rows | Official direct exact | Official system exact | Difference (points) | Direct tool accuracy | System tool accuracy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| smart_car | 351 | 44.729 | 50.997 | +6.268 | 71.510 | 68.091 |
| smart_home | 2792 | 9.384 | 10.602 | +1.218 | 55.552 | 52.579 |
| wearables | 857 | 37.456 | 49.825 | +12.369 | 79.230 | 73.512 |

## Root attribution: retain improvements and locate damage

There are 313 official exact saves and 151 harms, net +162. On 2,089 rows where both arms select the correct primary tool, exact correctness rises from 665 to 829 (240 saves, 76 harms, net +164). Tool corrections add 73 exact rows and tool damage loses 75. This is an exhaustive descriptive decomposition; it does not isolate the causal effect of parameter knowledge or any one role.

The task has two distinct parameter regimes. On 2,951 rows with nonempty official reference parameters, exact correctness rises from 422 to 627 (+205 rows). On 1,049 rows with empty reference parameters, it falls from 318 to 275 (-43). Among the rows with both tools correct, the respective net changes are +199 and -35. Therefore retain the parameter-resolution direction while examining omission/default semantics explicitly. Do not infer that all added arguments are hallucinations: the official and repo scorers have different definitions.

Tier 1 illustrates the distinction. All 33 harms with correct tools in both arms have no official reference keys, while the system emits parameter keys. Under saved repo-v2 scores, 21 of those 33 system outputs remain exactly correct; 23 rows strip some registry defaults. Nevertheless, 12 still fail repo exact. The tier-wide repo result improves by 9 rows while official exact loses 31. A repair must use the public task contract and speech evidence, not a rule to remove arguments because an evaluation annotation happened to be empty.

Wearables contribute 106 of the net 162 official exact improvements; smart_home contributes 34 and smart_car 22. The full domain table prevents the natural mixture from obscuring this difference. Broad claims about uniform improvement would be unsupported.

New primary-tool errors include temperature versus climate control, lock state versus door/lock status, and lighting versus light-state/ambient-lighting functions. Some new errors, such as reboot/update requests selecting camera calibration, require inspection beyond plausible near-neighbor ambiguity. These are analysis leads. Evaluation labels and these example errors must not be copied into runtime knowledge or memory; construction remains source/TRAIN-only.

### Actual activation guidance and the selection regression

Every Perception contact receives eight activation values. The pinned snapshot's explicit task_target fields identify the official primary-tool guidance on 3,066/4,000 rows (76.65%); source availability is complete. This is retrieved guidance coverage, not Perception candidate coverage, and is not the 95% candidate-target measurement.

| Primary-tool guidance | Rows | Direct tool correct | System tool correct | Net tool change | Direct official exact | System official exact |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Present | 3,066 | 2,245 | 2,248 | +3 | 691 | 871 |
| Absent | 934 | 236 | 89 | -147 | 49 | 31 |

Thus the whole -144 correct-tool change is the sum of +3 where guidance is present and -147 where it is absent. The complete legal tool registry remains available in the request, so retrieved guidance is not intended to restrict the answer space. This localizes a practical weakness in coverage and behavior when coverage is poor. It does not causally prove that retrieval damaged those rows: the groups differ in difficulty and no randomized guidance intervention occurred.

| Tier | Primary guidance present / 500 | Coverage |
| --- | ---: | ---: |
| tier1_direct | 437 | 87.4% |
| tier2_parametric | 465 | 93.0% |
| tier3_multi_intent | 377 | 75.4% |
| tier4_implicit | 207 | 41.4% |
| tier5_needle | 442 | 88.4% |
| tier6_correction | 450 | 90.0% |
| tier7_multiturn | 366 | 73.2% |
| tier8_intent_blending | 322 | 64.4% |

The completed candidate join below distinguishes Perception omissions from downstream primary-tool failures. Do not gate a runtime route on gold-guidance coverage: that is an analysis-only quantity. Any recovery trigger must use available speech, registry distinctions, disagreement or a problem-specific Reviewer finding.

<!-- CANDIDATE_STATUS_START -->
The shared Audio2Tool reader has now verified all 4,000 frozen sources and 5,156 candidate-selection receipts, using raw Perception response/state bindings and the runtime selection function. Root corrected two reader assumptions: selection is registered before supply changes the Solver query, and finite completion preserves a terminal stop wave. The original failed reader receipt remains intact; no experiment output or score changed.

The official primary target appears in the candidate union on **2,882/4,000 rows (72.05%)**. Of 3,999 available Perception states, 1,117 actually omit it; one Perception length stop has unavailable candidates and must not be relabeled an observed miss. Available-state coverage is 72.068%. Natural and equal-tier coverage are both 72.05%; equal-domain coverage is 76.346%. These are descriptive inclusion rates against the saved official primary target, not full ordered-action coverage.

| Primary target in candidates | Rows | Direct tool correct | System tool correct | Direct exact | System exact |
| --- | ---: | ---: | ---: | ---: | ---: |
| Present | 2,882 | 2,242 | 2,307 | 696 | 898 |
| Observed absent | 1,117 | 239 | 30 | 44 | 4 |
| Candidate state unavailable | 1 | 0 | 0 | 0 | 0 |

Candidate-present rows gain 65 correct primary tools and 202 exact calls. Candidate-absent rows lose 209 correct tools and 40 exact calls. This exhaustively localizes the overall -144 tools and +162 exact calls; it is not a causal effect of imposing or removing candidates.

There remain 575 rows with the target somewhere in the candidates but an incorrect final primary tool. Qualify this with action structure: the target is in first-action candidates on 2,661 rows, of which 404 have an incorrect final primary tool; it occurs only in later-action candidates on 221 rows, of which 171 have an incorrect final primary tool. The latter group may involve action grouping/order or selection, and cannot simply be labeled intent discrimination failure. The observed correct-final rate among all union-covered rows is 2,307/2,882 (80.05%).

The solver is not hard restricted to the candidate union. On 103 parsed outputs the final primary tool is outside it: 30 correct and 73 incorrect. All 30 correct escapes recover observed candidate misses; 17 incorrect escapes occur despite the correct primary tool being in the union. Unrestricted authority alone is therefore not an effective recovery mechanism, while hard filtering would eliminate these 30 observed recoveries. Retain final Solver authority and give Reviewer/Planner an explicit, evidence-based recovery route.

| Activation guidance | Candidate target | Rows | Direct tool correct | System tool correct | Direct exact | System exact |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Present | Present | 2,783 | 2,168 | 2,232 | 673 | 867 |
| Present | Absent | 283 | 77 | 16 | 18 | 4 |
| Absent | Present | 99 | 74 | 75 | 23 | 31 |
| Absent | Absent | 834 | 162 | 14 | 26 | 0 |
| Absent | Unavailable | 1 | 0 | 0 | 0 | 0 |

Thus Perception loses the primary target on 283 guidance-covered rows and recovers it on 99 guidance-uncovered rows. Improve both the upstream guidance and its consumption; increasing retrieved card count alone is not an evidence-supported repair.

| Tier | Candidate target present / 500 | Candidate coverage | Covered but final primary wrong |
| --- | ---: | ---: | ---: |
| tier1_direct | 399 | 79.8% | 97 |
| tier2_parametric | 428 | 85.6% | 53 |
| tier3_multi_intent | 399 | 79.8% | 79 |
| tier4_implicit | 171 | 34.2% | 54 |
| tier5_needle | 420 | 84.0% | 51 |
| tier6_correction | 423 | 84.6% | 59 |
| tier7_multiturn | 325 | 65.0% | 101 |
| tier8_intent_blending | 317 | 63.4% | 81 |

| Domain | Rows | Candidate target present | Candidate coverage |
| --- | ---: | ---: | ---: |
| smart_car | 351 | 272 | 77.493% |
| smart_home | 2792 | 1892 | 67.765% |
| wearables | 857 | 718 | 83.781% |

These candidate diagnostics have no comparable published per-tier/domain candidate metric; the official paper and repo task columns remain in the complete-strata tables above.

All 8,883 per-sample unique candidate observations map to authoritative parameter values, and actual selection matches the shared runtime policy. This establishes mapping/custody, not sufficient value content or semantic use. Of 3,999 observed states, 31 contain zero actions. Across 6,392 action records the candidate widths are: one = 4,467; two = 1,292; three = 324; four = 309. A configured maximum of four does not produce a broad four-candidate set; width one is not a calibrated confidence score. Repeated Solver visits do not count as new candidate-generation observations.

Full ordered-action gold coverage remains explicitly deferred until its scorer-side sequence source is separately registered. Do not reconstruct it from value titles, the primary gold tool, or unavailable fields.
<!-- CANDIDATE_STATUS_END -->

## Native behavior, tool use and contact costs

All 4,000 source-bound native episodes pass the shared audit. The postseal JSON Planner reader fix changes only verification and is merged to master at 466aba4a665d7d2da22f753739506b915556402b; the actual runtime source remains frozen at 834d4d475ec4ffe0e9d61ea031746d5c2dd024ee.

The system has 4,000 Perception, 5,156 Solver, 5,170 Reviewer and 5,149 Planner contacts, totaling 19,475. Fifteen successful analytical task-contract calls occur on only 11 samples; no observation tools execute. This run cannot support a broad claim that on-demand analytical or ASR tools caused its gains. The recorded lexical use/ignore values are token-overlap diagnostics, not proof of semantic consumption.

There are 1,157 samples with a second Solver visit. Their final exact counts equal the direct comparator (98 versus 98, 38 saves and 38 harms). The other 2,843 samples contribute net +162. This selected-group association is not a randomized revision effect and does not show whether revision improved its own first draft. Such a comparison requires separate frozen intermediate scoring definitions. The 372 revision-limit deliveries retain 23 exact rows versus 25 for direct.

Eight finite length stops are preserved: one Perception, six Reviewer and one Solver. Six deliver a completed Solver and two return the registered abstention; all eight have zero official exact in both arms. The limits therefore do not account for the broad quality differences.

| Recorded generation input/cost | Direct | System |
| --- | ---: | ---: |
| Model contacts | 4,000 | 19,475 |
| Prompt tokens | 14,930,993 | 107,745,151 |
| Completion tokens | 68,378 | 1,133,568 |
| Speech seconds summed across contacts | 23,418.083 | 117,105.072 |
| Summed request latency seconds | 3,070.479 | 63,011.118 |
| Analytical task-contract calls | 0 | 15 |

Repeated speech seconds are not unique dataset duration. Summed concurrent request latencies are not wall time or GPU hours. Preserve family fit, proof, aborted-attempt and utilization receipts separately; these generation-only totals do not replace total research contact accounting. Cost is reported, not used as a veto.

The campaign exited normally at 09:36:23.183569 UTC. Its trace persisted through 09:34:25.603550 UTC, identifying an artifact-writing tail but not the exact GPU stop time. The owner hold now prohibits new GPU generation, fit, encoding and service restart/recovery. Keep resident memory.

## Next work and scientific boundaries

1. Retain the completed paired decision and verified candidate attribution. The primary intervals pass and the original tool-accuracy guard fails; candidate coverage is 72.05%, with downstream primary-tool errors remaining on 575 covered rows.
2. Preserve the separate activation and parameter-meaning stores. Prioritize candidate formation and evidence-based recovery while preserving parameter improvements. Keep missing receipt evidence separate from actual candidate misses; address action ordering separately from tool discrimination.
3. After explicit owner GPU resume, prioritize the already prepared SLURP TRAIN-A broad/factored system because it provides a faster system iteration surface. Candidate inclusion remains a 95% target alongside complete task quality; it is not a reason to stop parameter optimization.
4. Design the next A2T version from named failures: request-grounded candidate distinctions, parameter omission/default provenance and problem-specific review. Keep analytical tools under Reviewer/Planner and final answer authority under Solver. Dynamic speech tools require actual targeted calls and demonstrated information gain, not just a declared toolkit.
5. The prepared E21 native window/context/tool configuration remains held. Evaluate the native transcription/PERSON task with its registered full44 population; do not replace it with an invented summarization objective.
6. Replicate a usable full system on the same roster before claiming stable gains. Only then formalize algorithmic training-free RL trajectories, action factors, sampling and optimization; manual root engineering is not that algorithm.

## Source and reproduction bindings

Use SPEECHRL_DATA_DIR/analysis/SAEA-A2T-NATIVE-ROLE-BASE-ANALYSIS-V1/ for large and sample-level artifacts. All numerical results above reuse the first complete score files; zero model, encoder, tokenizer, tool-inference or scorer contacts were added by this report.

| Artifact | SHA-256 |
| --- | --- |
| paired-score-result-v2.json | 5578ee3f7754ca20267dfb9fd11fadbc9a3fa0a1570a4dea7258df2747d1e765 |
| final-primary-decision-v1.json | 425ad43fd597941323a9a564d4031d44f9454ba6ecab9862317a5532a30ed88a |
| complete-source-bindings-v1.json | 2f21b106f88b7a420b06569c35a441ea2b7bfc4b87462caca59677bd9240af00 |
| paired-score-config-v2.json | 2fc0f2f562fa06abb2ef6c1ba0f5ae5899df47e2e922a657f3fa47d6564d6c77 |
| full4000-metadata-v2.json | f0cc01a84506dbd6bd4be9b53388e251c4ffa108711acb46c281a70fb4cd8251 |
| native-episode-audit-v2.json | 9a970faf5d6fae9ebe3f55beb270508bd08e0140c667800df5c21231782eefdb |
| paired-error-decomposition-v1.json | 05eecee510fcbe40fb206a99b855857f4fa60c3924a69e762e75dbe81d558b7f |
| native-saved-score-groups-v1.json | 04b590acc75c36d99d1a925c388d8e1320c1048eea36b7070222a8fe837d0e3a |
| official-tool-confusion-and-semantics-v1.json | f1927dd9171e8706cf1da13fa447f0bd3f4473084966461e7bb6ca70b08ad863 |
| activation-supply-projection-v1.json | cfbc5242223931031733341d7760b6b9a274c1a799f1ea8060b8a74bc60db545 |
| candidate-source-audit-v2.json | dea6d3026648bcfbc4aa4912da9de57072269b7acb8af8e060f245e4995d1acb |
| candidate-outcome-join-v1.json | f0c38ab4608f46aeb9c4c722ff8a6941d2075d67e6cb20b76764415528dae95f |
| candidate-primary-order-diagnostic-v1.json | 5f475a0468d1cd50754e93814dbdff819e487a1496de3ec8dacf5f5172d99792 |

The [prospective decision](../../configs/analysis/a2t-native-role-base-decision-v1.json), [paired read release](../readiness/2026-09-15-a2t-native-role-paired-read-release-v1.json), [analysis recipe](../readiness/2026-09-14-a2t-native-role-base-analysis-recipe-v1.json) and [STATUS-128](../superpowers/plans/experiment-handoff/STATUS-128.md) retain the execution and analysis history. Historical failures and immutable source bytes remain unchanged.
