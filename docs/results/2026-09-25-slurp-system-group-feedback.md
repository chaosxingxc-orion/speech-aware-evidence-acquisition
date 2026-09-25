# Complete-system grouped feedback: PLAN and PLANR

Status: COMPLETE DIAGNOSTIC; NO POLICY UPDATE OR EFFECTIVENESS CLAIM.

Root analyzed the same 625 construction inputs from two already sealed complete
system executions. All 1,250 episodes, 5,181 existing model contacts and 11
fallback episodes are retained. No new model, ASR, tokenizer or scorer contact
was made, and the active evidence-path experiment was not read.

Both sources pass raw source/score pins, complete roster, first speech packet
identity, shared model fragment and shared session receipt checks. Perception,
Solver, Reviewer, Planner, revisions and delivery remain source-addressable.
This is a full-episode comparison, not the incomplete downstream VAR-2 branches.

## Main findings

| Quantity | Groups / episodes |
| --- | ---: |
| Complete same-input groups | 625 |
| Parsed answer differs (JSON formatting and entity order ignored; duplicates retained) | 189 |
| Official-count utility differs | 131 |
| Utility tied | 494 |
| Intent correctness differs | 32 |
| Utility tied but intent differs | 9 |
| At least one of utility or intent differs | 140 |
| Different parsed answers with tied utility | 58 |
| Empty reference entity groups | 191 |
| Empty-reference groups with different utility | 35 |
| Row F1 tied but count utility differs | 43 |
| Utility/intent preference conflict | 8 |
| Utility differs and neither execution revises | 108 |
| Episodes without a subsequent Solver visit | 1,187 / 1,250 |

Utility uses the already frozen F0=0.5850661976193667:
u = 2TP - F0 * (2TP + FP + FN), with official combined word/character counts.
The row-F1 diagnostic above specifically means 2TP/(2TP+FP+FN) and zero for
a zero denominator. It is not substituted for any separately reported official
per-sample metric. That scalar row ratio misses 43 count differences here,
including 35 empty-reference cases. Keep TP/FP/FN, not only a row-F1 label.

The original pooled source scores remain PLAN 58.5066% and PLANR 60.3755%;
intent is 70.56% and 69.28%. This read does not reinterpret that repeat-run
difference as the effect of a new action or use it as a statistical power claim.

## Direction conflict

Entries count PLANR minus PLAN; signs do not identify a causal action.

| Utility direction | Intent lower | Intent tied | Intent higher |
| --- | ---: | ---: | ---: |
| Lower | 8 | 43 | 2 |
| Tied | 6 | 485 | 3 |
| Higher | 6 | 65 | 7 |

Eight groups favor opposite members on utility and intent; another nine have
tied entity utility but different intent. A future learner must preserve this
vector feedback and the existing final intent protection. This observation
does not prospectively authorize a new per-row veto, scalar weight or threshold.

## Root interpretation for the algorithm

1. System sampling has observable outcome variation, but most groups are tied.
   Preserve tied, failed and untriggered episodes rather than constructing a
   selected-only learning population. Different answer wording is not a winner.
2. The 108 unrevised informative groups cannot be credited to an executed
   revision. Variation can arise in Perception, the first Solver, termination
   or delivery; complete traces are needed to distinguish these paths.
3. A two-member non-tied standardized group gives advantages of approximately
   +1/-1 regardless of whether the raw utility gap is 0.04876 or 6.82987.
   Preserve the raw gap, counts, intent conflict and repeat support alongside
   normalized advantage. Do not turn a weak stochastic difference into a
   high-confidence memory rule. This numeric diagnostic is an adaptation, not
   the upstream TF-GRPO semantic experience updater.
4. Historical fixed-run allocation has no logged optimized-action propensity.
   The exported field is explicitly null. It cannot be used to fabricate
   importance weights or to claim randomized policy sampling.
5. The next learner should compare sampled complete executable system policies
   and carry their selected policy identity through terminal delivery. If the
   policy is selected before the episode, its real logged selection can receive
   that episode's return even when a later tool is unused; this is policy-level
   credit, not credit to an unexecuted tool. A decision made later must instead
   retain explicit action-not-reached outcomes. Never conflate the two.

The pending evidence-path pair remains a fixed whole-system experiment. Its
result will determine whether that path supplies a useful action for the next
registered sampling/update/re-execution loop. The present historical diagnostic
does not admit an action or justify increasing identical rollout count.

## Every scenario

Numbers are group counts; all input groups remain in each denominator.

| Scenario | N | Answer differs | Utility differs | Intent differs | Empty-ref utility differs | Utility/intent conflict | Utility differs, neither revises |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | 5 | 4 | 2 | 1 | 2 | 3 |
| audio | 30 | 5 | 3 | 3 | 2 | 1 | 2 |
| calendar | 42 | 15 | 12 | 0 | 1 | 0 | 11 |
| cooking | 31 | 6 | 4 | 1 | 2 | 0 | 3 |
| datetime | 39 | 7 | 7 | 1 | 2 | 0 | 6 |
| email | 33 | 17 | 11 | 1 | 1 | 0 | 9 |
| general | 42 | 18 | 10 | 5 | 7 | 1 | 7 |
| iot | 33 | 8 | 7 | 0 | 0 | 0 | 5 |
| lists | 37 | 10 | 8 | 3 | 2 | 1 | 6 |
| music | 27 | 11 | 6 | 0 | 6 | 0 | 4 |
| news | 36 | 14 | 8 | 5 | 0 | 0 | 6 |
| play | 37 | 11 | 9 | 1 | 3 | 0 | 8 |
| qa | 38 | 17 | 10 | 3 | 5 | 1 | 8 |
| recommendation | 29 | 7 | 7 | 2 | 2 | 1 | 5 |
| social | 35 | 12 | 8 | 4 | 0 | 1 | 8 |
| takeaway | 37 | 13 | 7 | 1 | 0 | 0 | 7 |
| transport | 32 | 6 | 4 | 0 | 0 | 0 | 4 |
| weather | 41 | 7 | 6 | 0 | 1 | 0 | 6 |

| Diagnostic rate | Natural mixture | Equal scenario |
| --- | ---: | ---: |
| Answer disagreement | 30.2400% | 29.8908% |
| Utility informative | 20.9600% | 20.7176% |
| Intent disagreement | 5.1200% | 5.1133% |
| Empty-reference utility informative, all groups as denominator | 5.6000% | 5.6889% |
| Utility/intent conflict | 1.2800% | 1.3915% |

These are descriptive rates, with no efficacy confidence interval or hypothesis
test. Conditional empty-reference rates use a different denominator and must
not be confused with the all-group rates above.

## Reproduction and custody

Shared entry: scripts/analysis/group_system_rollouts.py.
Pass the registered recipe docs/readiness/2026-09-25-stage3-system-group-feedback-read-v1.json,
its raw SHA-256, the data root, and a new output path. The reader resolves both
source-pinned complete feedback exports, underlying manifests/score seals,
all first requests and delivered outputs. It refuses changed speech inputs,
missing/duplicate members, evaluation feedback, reused trajectories and changed
source bytes. Publish through the existing create-only report writer.

Recipe SHA-256: e7c11883a899a080a1cfd3b90d7651c0677857c0459892a27fb2b89f0fa31074.
Derived group SHA-256: 4041c8df08ed64c9bb81a0e5b6a3e4a10625aecccc43268f5ee65a8208481a43.
Supplementary table calculation: group by frozen roster stratum; count the
named boolean conditions above. Equal weighting averages each scenario's rate;
natural weighting divides pooled counts by 625. The receipt stores every count.

Validation: 53 focused tests plus the engineering-base check pass. The live
flight checkout remains frozen at da443cdc; these analysis changes affect no
current request, source artifact, policy or knowledge store.

See docs/receipts/continuation/2026-09-25-system-group-feedback.json for exact
pins and numeric summaries. Existing closed mechanisms and DEV/test boundaries
remain unchanged.
