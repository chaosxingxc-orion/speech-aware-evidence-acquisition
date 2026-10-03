# Round5 fixed400 eight-member20: complete root read

Recorded: 2026-10-03T08:33:15.738832+00:00

Status: EXPLORATORY-FIXED-POOL-NO-ADOPTION. All eight independent20-row members passed seal verification and have one successful complete official score each, zero failed jobs. Root countersigned the exact READ before scientific reading. The driver completed normally at2026-10-03T08:28:09Z. No scorer replay or new model contact occurred.

| Member | Official SLU-F1 | Intent | Reliable completion | Model calls | Tool calls |
|---|---:|---:|---:|---:|---:|
| L-parent | 59.4021% | 70.00% | 100.00% | 125 | 0 |
| L-parent-aa | 56.3877% | 65.00% | 100.00% | 119 | 0 |
| L-candidate-1 | 58.5468% | 70.00% | 100.00% | 134 | 0 |
| L-candidate-2 | 62.3166% | 75.00% | 100.00% | 134 | 0 |
| B-parent | 60.3123% | 70.00% | 100.00% | 119 | 0 |
| B-parent-aa | 63.9778% | 70.00% | 100.00% | 122 | 0 |
| B-candidate-1 | 58.9248% | 70.00% | 100.00% | 125 | 0 |
| B-candidate-2 | 60.3123% | 70.00% | 100.00% | 131 | 0 |

Both L proposals were no-change and retain the parent runtime strategy. Their differing measurements cannot demonstrate learned policy improvement. L-candidate-2 is2.9145pp above L-parent, but its paired95% interval spans[-5.4207,+14.8577]pp and its policy text is unchanged. The same-request A/A offsets are-3.0145pp for L and+3.6655pp for B. Neither a favorable no-change draw nor the highest A/A score is selected as a new policy.

| Branch and contrast | SLU-F1 delta, pp | Paired95% interval, pp | Exact repairs | Exact damage |
|---|---:|---:|---:|---:|
| L: same-request-null | -3.0145 | [-16.9535, +3.9513] | 0 | 1 |
| L: candidate-1-minus-parent | -0.8553 | [-5.4945, +2.2121] | 0 | 1 |
| L: candidate-1-minus-aa | +2.1591 | [-6.3844, +16.8024] | 1 | 1 |
| L: candidate-2-minus-parent | +2.9145 | [-5.4207, +14.8577] | 0 | 0 |
| L: candidate-2-minus-aa | +5.9290 | [-6.2980, +24.9089] | 1 | 0 |
| B: same-request-null | +3.6655 | [-3.1082, +16.8113] | 0 | 0 |
| B: candidate-1-minus-parent | -1.3875 | [-6.7221, +2.4402] | 0 | 0 |
| B: candidate-1-minus-aa | -5.0530 | [-18.4925, +1.9357] | 0 | 0 |
| B: candidate-2-minus-parent | +0.0000 | [+0.0000, +0.0000] | 0 | 0 |
| B: candidate-2-minus-aa | -3.6655 | [-16.8113, +3.1082] | 0 | 0 |

B-candidate-1 is1.3875pp below its parent with an interval including zero. B-candidate-2 exactly matches the parent official sufficient-count quality on these inputs while using12 more model contacts. Both retain8/20 whole-answer exact cases, with no exact repair or damage versus their parent. The two new B text policies do not provide a qualified replacement. These between-system repair/damage counts are associations, not within-trajectory causal attribution.

The source-bound post-call audit retains every completed visit and uses the55 legal entity types in the actual frozen requests. All283 Reviewer handoffs are structurally valid and present in the next Planner context. Nineteen of371 findings name non-slot identifiers;28 of283 raw Solver responses fail strict task JSON, including25 nonexecuted textual tool-call markers. There are123 extra Solver revisions and31 changed first-to-last raw response texts. Correct transmission does not establish semantic use; changed text is not a measured repair. The existing normalizer and finite-delivery rules still provide100% reliable terminal completion.

| Member | Solver visits | Non-strict raw JSON | Text tool markers | Non-slot findings / all | Visible handoffs | Extra revisions | Changed text |
|---|---:|---:|---:|---:|---:|---:|---:|
| L-parent | 35 | 2 | 2 | 0/46 | 35/35 | 15 | 3 |
| L-parent-aa | 33 | 2 | 2 | 2/43 | 33/33 | 13 | 2 |
| L-candidate-1 | 38 | 2 | 2 | 4/47 | 38/38 | 18 | 5 |
| L-candidate-2 | 38 | 4 | 4 | 2/55 | 38/38 | 18 | 4 |
| B-parent | 33 | 3 | 3 | 2/43 | 33/33 | 13 | 3 |
| B-parent-aa | 34 | 4 | 4 | 2/47 | 34/34 | 14 | 4 |
| B-candidate-1 | 35 | 3 | 3 | 0/45 | 35/35 | 15 | 5 |
| B-candidate-2 | 37 | 8 | 5 | 7/45 | 37/37 | 17 | 5 |

B-candidate-2 has8/37 non-strict raw replies versus3/33 for its parent, despite no terminal quality change. This identifies an intermediate format regression to retain in the history; it does not establish a population harm claim. All systems made zero actual knowledge calls. That does not by itself establish either adequate or inadequate knowledge supply. Preserve the fixed knowledge assets and prioritize the admitted context/post-call surfaces.

| Member | Prompt tokens | Completion tokens | Perception / Solver / Reviewer / Planner contacts |
|---|---:|---:|---|
| L-parent | 1,245,862 | 9,322 | 20 / 35 / 35 / 35 |
| L-parent-aa | 1,106,557 | 8,548 | 20 / 33 / 33 / 33 |
| L-candidate-1 | 1,335,130 | 9,874 | 20 / 38 / 38 / 38 |
| L-candidate-2 | 1,331,094 | 10,490 | 20 / 38 / 38 / 38 |
| B-parent | 1,150,903 | 8,876 | 20 / 33 / 33 / 33 |
| B-parent-aa | 1,199,137 | 9,463 | 20 / 34 / 34 / 34 |
| B-candidate-1 | 1,243,746 | 8,880 | 20 / 35 / 35 / 35 |
| B-candidate-2 | 1,313,331 | 9,451 | 20 / 37 / 37 / 37 |

Measured totals are1009 model contacts,1009 original request-FIT receipts and4036 tokenizer endpoints, with8 unique official score jobs. These counts come from exact attempt/role/fit evidence, never serving totals. Prompt totals are processed request tokens, not unique context or billed compute. Duration is not measured by this derivative.

Every stratum and both weightings are retained. Entries below are SLU-F1 / intent percent; small supports are descriptive.

| Stratum | n | L-parent | L-parent-aa | L-candidate-1 | L-candidate-2 | B-parent | B-parent-aa | B-candidate-1 | B-candidate-2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| audio | 3 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 | 0.00 / 66.67 |
| cooking | 2 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 | 50.00 / 50.00 |
| email | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| general | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| iot | 1 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 | 0.00 / 100.00 |
| lists | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| music | 2 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 | 0.00 / 50.00 |
| news | 1 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 | 100.00 / 0.00 |
| play | 2 | 66.67 / 100.00 | 66.67 / 100.00 | 57.14 / 100.00 | 92.63 / 100.00 | 66.67 / 100.00 | 92.63 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |
| qa | 2 | 58.54 / 100.00 | 37.21 / 50.00 | 62.75 / 100.00 | 58.54 / 100.00 | 62.75 / 100.00 | 58.54 / 100.00 | 62.83 / 100.00 | 62.75 / 100.00 |
| recommendation | 1 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 | 100.00 / 100.00 |
| social | 1 | 41.79 / 0.00 | 0.00 / 0.00 | 41.79 / 0.00 | 41.79 / 100.00 | 41.79 / 0.00 | 41.79 / 0.00 | 41.79 / 0.00 | 41.79 / 0.00 |
| takeaway | 1 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 | 66.67 / 100.00 |
| Equal-stratum macro | 13 | 44.90 / 70.51 | 40.04 / 66.67 | 44.49 / 70.51 | 46.89 / 78.21 | 45.22 / 70.51 | 46.89 / 70.51 | 45.23 / 70.51 | 45.22 / 70.51 |

Root227 next-stage disposition: Retain the original seed as formal parent in both branches; do not adopt a favorable no-change or A/A realization. Remain at20. Prospectively register round6 with the tested coherent-feedback-v1 presentation and the newly qualified complete L-only source, preserving all20 spent proposal slots and unchanged proposer model/budgets. Inspect all resulting proposals, including no-change or invalid ones, before exact next-panel admission. No automatic50/100/200 increase; human review remains required before8x400.

The descriptive nondominated measurement archive retains L-parent, L-parent-aa and L-candidate-2, and B-parent/B-parent-aa, with their exact cohort identities. These are sample-level quality/intent/contact-cost tradeoffs, not three distinct effective L policies or scientific promotion. Historical batches are not merged into this frontier.

Only separately qualified complete own-L feedback is exported, with the frozen initial F_ref and all success/failure/unchanged/damage cases. This combined report, B outcomes, root diagnosis and all milestone/test outcomes stay outside proposer inputs. The next presentation must remain source-addressed and expose complete untruncated decision text within its registered budget. No positive proposal or gain is guaranteed.

This is retained-exposure TRAIN optimization, not independent validation or stable recursive self-improvement. Other carrier holds remain unchanged. No new answering model, retriever, knowledge build, runtime parser or normalizer has been activated.

Evidence: [operational qualification](../receipts/continuation/2026-10-03-round5-n20-family-qualified.json), [scientific read and source pins](../receipts/continuation/2026-10-03-round5-n20-scientific-read.json). Raw traces and analysis derivatives stay outside Git under `analysis/SAEA-SLURP-SYSTEM-TEXT-FIXED400-ROUND5-N20-READ-V1/`.
