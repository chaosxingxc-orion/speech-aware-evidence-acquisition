# Actual pre-Solver state: complete-system construction audit

Status: completed, model-free, post-hoc construction diagnostic. No action selection, policy update or efficacy claim. The active evidence-path outcomes remain unread.

## Root decision

Use the four existing exemplar-agreement bins as the first candidate contextual state, subject to qualification of useful coordinated actions. Keep candidate width as a diagnostic axis initially. Do not cross width and agreement into twelve learned cells on this 625-input roster.

This is a decision about an observable state representation, not proof of an effective policy. The optimized action must govern a complete downstream path: evidence acquisition, normalized handoff, Planner routing, Solver revision, subsequent review and delivery. Its feedback is the final complete-system outcome, including unchanged, failed and unreached paths.

## Source and boundary

Registered read: SAEA-SLURP-STAGE3-SYSTEM-DECISION-STATE-AUDIT-V1. The recipe is docs/readiness/2026-09-25-system-decision-state-audit-v1.json. The reader rechecks pinned, previously verified PLAN and PLANR complete feedback, manifest, phases, raw requests/responses and first-Perception response custody. All 625 inputs in each run reached the audited boundary; all 1,250 terminal outcomes remain represented.

The boundary is after the fixed initial Perception and default20 supply, before the first Solver request. These features are unavailable at episode start. A future policy must compute them from its own actual prefix. A shared prefix is permissible only when its custody and full downstream execution are explicitly registered; an isolated Solver branch is not a system rollout.

Candidate normalization reuses the runtime bounded first-occurrence distinct projection. Knowledge labels come from the released minus-R01 exemplar snapshot, never from target annotations. Official terminal feedback is joined only in a separate offline diagnostic section.

Artifact: /mnt/e/chao_workspace/exploring-l4-intelligence/speechrl-data/analysis/SAEA-SLURP-STAGE3-SYSTEM-DECISION-STATE-AUDIT-V1/state-audit.json. Raw SHA-256: c712e190797fd7f95eab9ff9cf7e4718d2d42b10fbf8e0fff345a7961e9ed508. The JSON preserves all source pins, per-input state identities, full per-state/per-scenario counts and terminal diagnostics. No new model, tokenizer, encoder, ASR, scorer, server or network contact was added.

## Availability, stability and population

| Quantity | PLAN | PLANR |
| --- | ---: | ---: |
| Available pre-Solver states | 625 | 625 |
| Missing boundary | 0 | 0 |
| Raw width differs from bounded distinct width | 21 | 25 |
| Whole-episode exemplar union differs from first Solver input | 0 | 0 |
| One / two / three distinct candidates | 43 / 149 / 433 | 53 / 145 / 427 |

| Repeat comparison | Changed inputs / 625 | Percent |
| --- | ---: | ---: |
| Distinct candidate width | 93 | 14.88 |
| Exemplar agreement bin | 6 | 0.96 |
| Width crossed with agreement | 98 | 15.68 |
| Ordered candidate identities | 212 | 33.92 |
| First candidate identity | 30 | 4.80 |
| Exemplar identity set | 0 | 0.00 |

The older bad-case reader builds a union across episode waves. That is not a generally valid pre-action feature; however, it equals the actual first-Solver exemplar input on every audited PLAN/PLANR row. This audit therefore finds no future-exemplar contamination in these two sources. Do not rewrite historical artifacts or assert leakage here. Future acquisitions require the prefix-specific reader.

Agreement is more repeatable than candidate width here, partly because every input retains the same initial exemplar set. Stability alone does not prove informativeness, calibration or action-effect heterogeneity. An ordered-candidate hash difference can reflect ordering as well as membership.

## State occupancy and descriptive terminal outcomes

All F1 and intent entries below are percentages. Pooled F1 is reconstructed from the already sealed official word/character counts; no scorer was rerun. It is not the mean of per-input F1.

| Agreement with first candidate | PLAN n | PLAN F1 | PLAN intent | PLANR n | PLANR F1 | PLANR intent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| agree-lt-0.25 | 210 | 47.0178 | 39.0476 | 209 | 50.3455 | 35.4067 |
| agree-0.25-0.50 | 107 | 62.4611 | 78.5047 | 108 | 62.5215 | 77.7778 |
| agree-0.50-0.75 | 99 | 56.9778 | 82.8283 | 100 | 59.0276 | 83.0000 |
| agree-ge-0.75 | 209 | 64.7518 | 92.3445 | 208 | 66.3335 | 92.3077 |

The lowest-agreement bin has substantially poorer final intent quality in both repeats. This identifies a repeatable diagnostic condition, not evidence that acquisition or more knowledge repairs it. The middle bins do not monotonically order final entity F1. High agreement is not a confidence score or an automatic instruction to skip review.

The four bins contain at least 99 inputs each. Balanced allocation to two or three actions would yield at least 49.5 or 33 expected observations per state/action. These are planning expectations, not realized counts or power guarantees. In the twelve-cell crossed representation, 6/12 PLAN and 7/12 PLANR cells fall below 20 expected observations per action with two actions; with three actions, 8/12 do in both runs. Preserve the established sparse fallback rather than select thresholds from terminal labels.

| Agreement bin | PLAN equal-present-scenario F1 | PLAN equal intent | PLANR equal-present-scenario F1 | PLANR equal intent | Present scenarios |
| --- | ---: | ---: | ---: | ---: | ---: |
| agree-lt-0.25 | 43.5997 | 39.8853 | 46.4855 | 36.9172 | 18 / 18 |
| agree-0.25-0.50 | 52.9286 | 75.9055 | 51.2985 | 75.4095 | 18 / 18 |
| agree-0.50-0.75 | 56.6131 | 80.2797 | 60.9438 | 80.2441 | 18 / 18 |
| agree-ge-0.75 | 61.4800 | 90.1783 | 63.0419 | 90.1783 | 17 / 17 |

Conditional equal weights cover only scenarios present in that state; the high-agreement state contains 17 of 18 scenarios. Do not compare these conditional numbers as if every state had the same scenario population. The source JSON retains each conditional scenario table.

## Complete-population scenario table

| Scenario | n | PLAN pooled F1 | PLAN intent | PLANR pooled F1 | PLANR intent |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 26 | 67.2314 | 92.3077 | 67.2489 | 84.6154 |
| audio | 30 | 42.5354 | 60.0000 | 58.5086 | 63.3333 |
| calendar | 42 | 60.3295 | 59.5238 | 64.2463 | 59.5238 |
| cooking | 31 | 62.0394 | 67.7419 | 58.8638 | 70.9677 |
| datetime | 39 | 59.1639 | 84.6154 | 63.5178 | 82.0513 |
| email | 33 | 54.0610 | 78.7879 | 58.0711 | 75.7576 |
| general | 42 | 16.2080 | 23.8095 | 13.4958 | 11.9048 |
| iot | 33 | 64.8717 | 75.7576 | 70.8041 | 75.7576 |
| lists | 37 | 58.5332 | 86.4865 | 53.7414 | 83.7838 |
| music | 27 | 17.3913 | 62.9630 | 18.1818 | 62.9630 |
| news | 36 | 46.3142 | 66.6667 | 49.7989 | 69.4444 |
| play | 37 | 52.3966 | 64.8649 | 52.6692 | 67.5676 |
| qa | 38 | 46.8211 | 55.2632 | 53.0326 | 57.8947 |
| recommendation | 29 | 58.2615 | 86.2069 | 64.1068 | 86.2069 |
| social | 35 | 66.0329 | 68.5714 | 67.7965 | 62.8571 |
| takeaway | 37 | 63.4557 | 75.6757 | 63.0024 | 72.9730 |
| transport | 32 | 72.4969 | 81.2500 | 72.0712 | 81.2500 |
| weather | 41 | 63.2816 | 92.6829 | 62.3258 | 92.6829 |

Complete-population pooled F1 is 58.5066 / 60.3755; intent is 70.56 / 69.28. Fallbacks are 9 / 2, and subsequent Solver visits occur on 32 / 31 inputs. Different full outcomes under the same policy demonstrate sampling variability, not effects of different actions.

## Next algorithm boundary

1. Complete and read the current matched evidence-path pair under its registered terminal criterion. Preserve actual tool non-use, empty results, evidence consumption, routing, repairs and new harms.
2. Qualify a small action set of coherent full continuation policies. A policy that merely exposes a tool without useful downstream evidence is not established as an improvement. Negative evidence may motivate a named new information source; it does not justify forced calls or larger blind sampling.
3. For the first contextual comparison, freeze the common initial prefix and these four state bins before sampling. Select and log the complete continuation action after the state is available and before its first effect. Include source state hashes, available actions, actual probability and policy version.
4. Retain every complete episode. A prefix that never reaches the decision contributes to system evaluation but supplies no invented action credit. The current updater requires a decision per row; explicit missing-decision accounting is a remaining admission item for this later boundary, even though all audited rows reached it.
5. Update only after a full construction round is scored. Reuse frozen official-count utility and separate intent/format/fallback feedback. Keep the established two-round schedule, sparse fallback and frozen evaluation; do not silently change them based on these descriptive labels.
6. Compare frozen contextual selection with the strongest fixed complete policy on matched inputs, then replicate. The episode-start single-state selector is a fixed-policy learning comparator. It cannot establish contextual benefit. No claim of multistep RL follows from one contextual decision.

No new GPU family, runtime switch, learned value update or fresh-data access is authorized by this report. The live frozen checkout is unchanged. The root owns the interpretation and later policy qualification.
