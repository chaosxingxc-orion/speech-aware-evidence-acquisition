# SLURP maximum-five candidate contrast: complete root verdict

Date: 2026-09-16. Decision: **NOT_ADVANCED**. Keep the maximum-three incumbent.

The complete maximum-five arm does not pass its registered final-task advancement rule. It raises candidate coverage modestly, but does not establish improved intent choice or official SLU quality. Both natural-mixture and equal-scenario primary intervals cross zero. No automatic N8 sweep, positive-lead replication, or repeat-to-pass is admitted.

Use exactly 1080 paired recordings, 125 speaker clusters and 18 scenarios of 60 recordings each. The full output is COMPLETED, the attempt FINALIZED, and the first complete official score retained. Root bound the complete-source release before quality reads. The official evaluator ran once; following analyses use saved results. Use 10000 whole-speaker paired bootstrap draws, seed 20260915, CI95 for the primary and CI90 for diagnostics. This is an exposed development roster.

## Complete task and candidate outcomes

| Outcome | Maximum three | Maximum five | Difference (pp) | Paired interval (pp) |
| --- | ---: | ---: | ---: | --- |
| Official pooled SLU micro F1 | 48.5336% | 48.6204% | +0.0867 | CI95 [-1.3650, +1.6510] |
| Equal-scenario SLU micro F1 | 46.8364% | 47.4098% | +0.5735 | CI95 [-1.2042, +2.1377] |
| Intent accuracy | 77.9630% | 77.5000% | -0.4630 | CI90 [-1.4911, +0.5343] |
| Exact entity-pair micro F1 | 29.4976% | 29.3028% | -0.1947 | CI90 [-1.7806, +1.4616] |
| Gold candidate coverage | 86.7593% | 88.0556% | +1.2963 | CI90 [+0.5644, +2.0246] |
| Intent accuracy on same 932 common-covered rows | 90.1288% | 89.4850% | -0.6438 | CI90 [-1.7483, +0.4180] |

Compute pooled micro F1 from summed sufficient counts, not mean row F1. Equal-scenario SLU is the equal mean of 18 within-scenario pooled scores. Candidate coverage is 937/1080 versus 951/1080: 14 net inclusions, leaving 75 net additional inclusions to reach 1026/1080 (95%). Actual distinct candidate mean width is 2.6861 versus 3.5991; a short list is not calibrated confidence.

## Coverage-to-decision decomposition

| Coverage partition | Rows | N3 final intent correct | N5 final intent correct | Saves | Harms |
| --- | ---: | ---: | ---: | ---: | ---: |
| retained | 932 | 840 | 834 | 17 | 23 |
| gained | 19 | 0 | 3 | 3 | 0 |
| lost | 5 | 2 | 0 | 0 | 2 |
| neither | 124 | 0 | 0 | 0 | 0 |

Only 3 of 19 newly covered recordings become correct final intents. Five lost-coverage rows remove two previously correct answers. On 932 rows covered in both arms, 17 saves and 23 harms produce six fewer correct intents. Combined, final intent declines 842 to 837. This is descriptive accounting; the common-covered CI90 includes zero and does not establish a causal deterioration.

Own-covered intent accuracy is 842/937 (89.8613%) versus 837/951 (88.0126%). These sets differ, so their ratio difference is not an isolated decision-quality effect. Neither arm rescues a gold intent outside its generated candidate set. N3 delivers 22 valid outside-candidate final labels and N5 delivers 30; both retain seven malformed outputs. No post-hoc projection repairs the answers.

| Actual distinct width | N3 rows | N5 rows |
| --- | ---: | ---: |
| 1 | 57 | 127 |
| 2 | 225 | 222 |
| 3 | 798 | 134 |
| 4 | 0 | 71 |
| 5 | 0 | 526 |

Initial K8 supplies the own-intent card on the same 947 recordings. In N5, 927 are covered and 20 remain missed. Of 133 rows without that card, 24 are covered and 109 missed. N3 corresponding counts are 914/33 and 23/110. This localizes most remaining misses to the region without own-intent support; it does not prove retrieval caused them, because card availability is correlated with difficulty and other cards may carry useful contrasts. There is no completed candidate refresh in either arm.

## Slots after the intent is correct

On the same 817 recordings with correct final intent in both arms, exact entity sets increase 305 to 314, while pooled exact entity-pair F1 changes 32.7502% to 32.6271%. These answer different questions: whole-set success and pooled extraction errors need not move together. Own-correct-intent residuals are 525/842 versus 519/837 nonexact entity sets. Full intent-plus-entity exactness changes 317 to 318 of 1080. None replaces the registered official primary.

The supplemental valid-entity exactness metric requires a parsed answer and zero saved exact-pair FP/FN. It gives 378 versus 393 complete-roster successes. Historical FP/FN-only counts can include an unparsed empty-reference case; do not silently equate those definitions. All malformed rows remain in the official full-roster comparison. No scorer is rerun.

## All scenario strata

Every row has 60 recordings. Coverage and intent columns are counts; SLU columns are percentages.

| Scenario | N3 SLU | N5 SLU | Delta pp | Covered N3/N5 | Intent correct N3/N5 | Entity-pair F1 delta pp |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| alarm | 52.6629 | 54.2624 | +1.5995 | 58/58 | 50/49 | +0.8598 |
| audio | 47.7541 | 63.9265 | +16.1723 | 55/56 | 46/46 | +14.9351 |
| calendar | 48.3786 | 45.7435 | -2.6351 | 49/50 | 45/44 | -3.7311 |
| cooking | 62.4709 | 62.0844 | -0.3866 | 55/56 | 51/52 | -0.4130 |
| datetime | 59.5160 | 58.4042 | -1.1119 | 57/59 | 50/51 | +1.5444 |
| email | 36.6353 | 41.9616 | +5.3264 | 53/53 | 51/52 | +4.6495 |
| general | 15.4532 | 12.7660 | -2.6872 | 26/25 | 22/20 | +0.5556 |
| iot | 55.5331 | 56.8197 | +1.2866 | 57/58 | 52/53 | +2.0000 |
| lists | 43.5483 | 40.3127 | -3.2355 | 51/51 | 50/50 | +0.0000 |
| music | 34.5328 | 33.6491 | -0.8837 | 52/55 | 46/44 | -1.9199 |
| news | 44.2416 | 41.0232 | -3.2184 | 50/52 | 48/49 | -6.4230 |
| play | 46.8231 | 48.7840 | +1.9610 | 53/54 | 35/36 | +1.0207 |
| qa | 57.0355 | 53.4174 | -3.6181 | 47/47 | 45/45 | -0.7690 |
| recommendation | 49.7452 | 50.4601 | +0.7149 | 57/57 | 54/51 | +1.2639 |
| social | 34.7389 | 39.5779 | +4.8390 | 49/49 | 40/40 | +1.5744 |
| takeaway | 48.8388 | 47.3723 | -1.4665 | 55/56 | 51/49 | -3.7422 |
| transport | 51.3367 | 51.8097 | +0.4730 | 57/58 | 52/51 | -0.9859 |
| weather | 53.8099 | 51.0025 | -2.8074 | 56/57 | 54/55 | -2.6734 |

## Runtime, input and attribution

N5 used 5421 core calls, 1080 tool calls, 49,145,923 prompt tokens, 305,479 completion tokens and 15,477.026 repeated speech seconds. N3 used 5417, 1082, 45,998,267, 255,153 and 15,459.765 respectively. These are full-episode costs, not one call per recording. Summed N5 request latency 50,180.257 seconds is not elapsed walltime.

The campaign-to-generation-seal window lasts 3.8219 hours; the first-score terminal follows 6.10 minutes later. The ten-second monitor covers this window without gaps over 30 seconds: time-weighted GPU utilization 90.56%, utilization integral 3.4611 GPU-hours, peak memory 22976 MiB. This includes in-flight request fit and preparation, excludes earlier model loading, and is not an effective-generation-only measure. Preserve idle after sealing as scientific analysis/registration waiting; do not conceal it by adding unnecessary work.

OBS retains original precomputed speech and decoder-only service. ORG retains the released knowledge stores while the candidate schema/prompt permits up to five distinct labels. SUPPLY retains K8 and the 28-total/16-per-candidate Solver caps; changed candidates can change delivered values. USE retains the role graph and task-contract-only Reviewer. The contrast is the declared width policy with its downstream consequences, not an isolated rank, per-value, or context effect. Input volume increases without demonstrated final-task benefit. Do not infer value dilution caused an error without exact supply evidence.

The historical N3 source ran in another service process. The shared-source version also contains reviewed engineering upgrades. Preserve these limits; this is not a same-process causal estimate. Legacy global ontology examples derive from full real TRAIN, whereas released intent/slot stores exclude A/B. Preserve that distinction rather than calling all runtime knowledge fold-excluded.

## Root next decision

Select one bounded maximum-three successor: the implemented typed role-context compiler with structured evidence-directed Reviewer, existing on-demand target-knowledge access and reserved final reporting. Compare this complete package with max512 direct-only through the same controller, FlightRuntime and OpenJiuwen executor on TRAIN A1080 and the same resident decoder geometry. Keep semantic stores and original speech fixed. Do not bundle the no-example contract, history-only restriction, new values, acoustic tools, candidate refresh or larger N.

The named optimization target is the evidence-to-decision handoff: alternatives remain hypotheses, current drafts remain unverified, and review declarations stay separate from evidence and actual Planner action. Structural cleanup cannot determine whether speech supports a claim. Frozen Reviewer/Solver retain semantic judgment; Planner retains routing. This tests a system package, not each field or tool in isolation.

The historical DEV1000/NEW500 max512 dual-store base already has two positive matched comparisons and remains a useful exploratory base. This new package and current TRAIN A comparison have no demonstrated gain yet. A positive frozen system-versus-direct pair must be repeated on the same roster before claiming repeatable benefit for the successor. Manual engineering is not training-free RL.

## Source custody

- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/official-comparison-v1.json; SHA-256 b3a1e34aabf9dafa9dd48ab7e9988149a409fb2715f1dfadc5d18395e9f8aedd.
- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/candidate-comparison-v1.json; SHA-256 7f25dc4bd95d533903e67e7c8ba60a2e0e29dcddcb77692c2161988194f1e1b2.
- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/native-train-support-diagnostics-v1.json; SHA-256 a7fd10b86d827f198a0b94f20c800847828bf00592a516781807d07a26a4e350.
- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/root-conditional-entity-diagnostics-v1.json; SHA-256 bf31135fc33a94091836f7a2ea0b75455acc6582d5dcde8749014197162c2e07.
- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/root-monitor-window-v1.json; SHA-256 20c34ff6b81eabc40eea314e30fb1a00edea0c9b34288611a488479068c36c1f.
- DATA/coordination/slurp-candidate-five-v1/root-paired-quality-release-v1.json; SHA-256 24b2780f6952662cc13fcde0f9688062f9bed26c69584718386fad831a9d2143.
- DATA/coordination/slurp-candidate-five-v1/postseal-structural-gate-v1.json; SHA-256 1dc7e0b98c1d06d208d997d43eb77ef8c7443500e2f5610d8f920a8d730c1250.
- DATA/coordination/slurp-candidate-five-v1/root-primary-verdict-v1.json; SHA-256 82aeea0868be49ec2253cdb2d7805b158d6d83a1848a56dd51909f48b1d2e437.

## Root review of completed control behavior

The verified role contacts are Perception 1080, Solver 1087, Reviewer 2167 and Planner 1087.
Planner accepts 1080 times and revises seven times. All seven later Solver visits complete
and are delivered; no candidate refresh executes. Initial-to-final intent correct rises
835 to 837 (two saves, zero harms), and full intent-plus-entity exactness rises 317 to 318
(one save, zero harms). This is a small observed correction footprint, not evidence that
review is inherently useless. The majority of remaining errors do not enter revision.

The shared historical entity-exact diagnostic counts zero saved exact-slot FP/FN irrespective
of parsing, and reports 392 to 394. Keep that definition distinct from the parsed-valid
diagnostic above (final 393). All final official sufficient fields are verified unchanged.

All 1080 tool calls are task-contract calls with successful result events; no speech
observation tool is used. Every core contact and final delivery has completion metadata;
none reaches max512 or reports a length stop. Output truncation is not an observed cause.
The generic findings parser cannot parse any of the 1087 historical free-form Reviewer
reports under the new structured contract. That is a contract mismatch, not 1087 experiment
failures: the old Reviewer was never instructed to emit that new format.

The separately verified sealed FlightReceipts contain 1080 initial acquired slot supplies
and seven later already-visible selections. They select 15035 slot values. All projected
candidates have a mapping. One row reaches 28 total values and one candidate reaches 16,
but no value mapping is discarded for either limit; the ignored mappings are shared values
already selected. Thus binding value-cap truncation is not an observed explanation of this
arm's non-improvement. Candidate-position selected totals are 5267, 3470, 2563, 1963 and 1772;
these are deduplicated contributions, not measures of information usefulness. A zero new
contribution can mean values are already shared, not missing knowledge.

This sharpens the root decision: test whether explicit evidence/hypothesis/draft separation
and concrete review findings improve correction behavior and task quality. Do not respond
by raising an unbound value cap. On-demand target lookup is useful only when it adds a
relevant distinction not already visible; repeated exposure alone is not information gain.
The existing observation gap remains a separate possible later mechanism.

- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/solver-stage-attribution-v1.json; SHA-256 e8c96ab8f2dc95dbff6219d81c6ca2b90c4d9b8f02c0aacbfb20c49f136d20e6.
- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/native-review-findings-v1.json; SHA-256 1998128729550027bce0bcc0707faf80c26705219a871eebc98acc847f0b43aa.
- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/native-episode-diagnostics-v1.json; SHA-256 39a0761a9e595560dfc13a4e18c7e70c7fedce77a0705a29647a5d4150fa7879.
- DATA/analysis/SAEA-SLURP-NATIVE-CANDIDATE-FIVE-TRAIN-FOLD-A-V1/candidate-supply-numeric-summary-v1.json; SHA-256 1669c134fa34dc0f36b41fc7e83223dce5c94c77fc71a40a4006b43b2b494300.
