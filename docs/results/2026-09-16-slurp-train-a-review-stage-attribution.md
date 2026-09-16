# SLURP TRAIN A review and revision attribution

Date: 2026-09-16. Root-reviewed, model-free descriptive analysis of the complete released
1,080-row TRAIN Fold A anchor. This is not a new generation, official score, independent
replication, or an isolated causal estimate of Reviewer benefit.

## Complete-cohort finding

The initial Solver draft has 843 correct intents; the final delivery has 842.
No initially incorrect intent becomes correct, and one correct intent becomes incorrect.
Entity-set exactness and full intent-plus-entity exactness have zero saves and zero harms.

| Diagnostic | Initial Solver | Final delivery | Saves | Harms |
| --- | ---: | ---: | ---: | ---: |
| Intent exact | 843 / 1080 (78.0556%) | 842 / 1080 (77.9630%) | 0 | 1 |
| Entity set exact | 379 / 1080 (35.0926%) | 379 / 1080 (35.0926%) | 0 | 0 |
| Full intent and entity exact | 317 / 1080 (29.3519%) | 317 / 1080 (29.3519%) | 0 | 0 |

All seven malformed predictions remain in both endpoints. Each scenario has 60 rows, so
natural-mixture and equal-scenario averages coincide for these accuracy estimands.
This does not make pooled official SLU micro-F1 equal to the mean of scenario micro-F1s.
The saved complete official final score remains authoritative and was not rerun.

Five episodes actually attempt, complete, and deliver a later Solver response. Three change
response bytes; two repeat the initial answer exactly. There are six REVISE route decisions
because one revised episode asks for a second revision after its allowed revision is used.
That second route is not a sixth executed revision or a truncated Solver.

The exactness table must not conceal partial changes: two of the three changed responses
improve the per-sample distance-based slot diagnostic, while one worsens it. One case adds
an exact entity pair. Neither partial improvement makes its whole entity set or full task
correct. Do not describe all revisions as ineffective or infer a corpus-level official
gain from these diagnostic values.

## Initial decision behavior

The initial Planner accepts 1,075 drafts and requests revision for five.

| Initial Planner action | Samples | Draft intent wrong | Draft entity set wrong | Draft full task wrong |
| --- | ---: | ---: | ---: | ---: |
| ACCEPT | 1075 | 235 | 698 | 759 |
| REVISE | 5 | 2 | 3 | 4 |

These error columns overlap. They describe actual routing against offline draft correctness,
not Reviewer issue-detection recall: historical Reviewer reports are unstructured, and a
Planner action need not equal the Reviewer's recommendation. The one fully correct draft
sent for revision remains unchanged and correct.

## Root audit of every revised episode

Root read all five revised episodes, including all thirty final Solver/Reviewer/Planner
role responses. The complete phase and raw-trace file hashes match the released source.
No reference sentence or entity string was exposed in this case audit.

| Observed behavior | Measured outcome | Design implication |
| --- | --- | --- |
| Reviewer asserts multiple active requests and asks for multiple intents despite the single-command contract. | A fully correct answer is unnecessarily revised but stays unchanged. | Keep candidate hypotheses distinct from speech evidence and respect the dataset task. |
| Reviewer identifies a temporal omission; Solver adds a time entity. | Distance-based slot match improves; exact entity matching remains wrong. | Diagnose the remaining extraction/representation boundary rather than assuming another generic instruction fixes it. |
| Reviewer proposes an illustrative filler while admitting the speech does not specify it; Solver uses it and changes intent; subsequent review retracts the filler but Planner accepts. | A correct intent becomes wrong and the slot diagnostic declines. | Separate evidence from suggested answers, ground changes in a discriminative cue, and measure whether Planner acts on the actual finding. |
| Reviewer correctly rejects an incompatible intent but proposes another incorrect intent; Solver recovers some entities. | Partial slot improvement, wrong intent and incomplete task remain. | Error detection and correct alternative selection require different information. |
| Reviewer declares ambiguous speech and unsupported candidates; Planner requests another answer with no new observation. | Solver repeats the answer and a later REVISE reaches the bound. | A named acoustic uncertainty is a reason to evaluate an on-demand observation tool; repetition alone adds no evidence. |

These are descriptive trajectories. They do not prove that a particular knowledge example
caused a filler, that a proposed ASR call would help, or that the Reviewer has statistically
independent errors. The current roles share a frozen core and prior history.

## All scenario strata

Each row contains 60 samples. Entity-set and full-task exactness have no row-level
save or harm in any scenario.

| Scenario | Initial intent correct | Final intent correct | Entity-set exact | Full-task exact | Executed revisions |
| --- | ---: | ---: | ---: | ---: | ---: |
| alarm | 50 | 50 | 20 | 19 | 0 |
| audio | 46 | 46 | 44 | 35 | 1 |
| calendar | 45 | 45 | 15 | 12 | 0 |
| cooking | 51 | 51 | 24 | 21 | 0 |
| datetime | 50 | 50 | 22 | 18 | 0 |
| email | 51 | 51 | 15 | 13 | 2 |
| general | 22 | 22 | 25 | 12 | 1 |
| iot | 52 | 52 | 20 | 17 | 0 |
| lists | 50 | 50 | 25 | 24 | 0 |
| music | 46 | 46 | 31 | 25 | 0 |
| news | 48 | 48 | 25 | 24 | 0 |
| play | 35 | 35 | 13 | 8 | 0 |
| qa | 45 | 45 | 23 | 20 | 0 |
| recommendation | 54 | 54 | 22 | 21 | 0 |
| social | 40 | 40 | 8 | 5 | 0 |
| takeaway | 51 | 51 | 14 | 14 | 0 |
| transport | 52 | 52 | 17 | 14 | 0 |
| weather | 55 | 54 | 16 | 15 | 1 |

## Next experiment boundary

Keep the maximum-five candidate experiment unchanged until its full seal, first official
score and root paired verdict. The original candidate coverage is 937/1080; the 95 percent
priority requires at least 1026 covered samples. Higher coverage must still be assessed
against final task quality and decision accuracy on the same common-covered cases.

The second line now has shared source-bound stage measurement and a held structured
Reviewer report configuration. Its next contrast must target a demonstrated missing
distinction or evidence gap. Existing prompts and slot cards already contain omission
rules; the previously released entity-loss audit also established Reviewer visibility of
those cards in the complete replication. Repeating those rules is insufficient as a named
new mechanism. Construct any new knowledge from permitted construction data, preserving
evaluation-fold exclusions; never turn the above evaluation examples into runtime answers.

For tool selection, distinguish an unknown schema, an intent activation boundary, an entity
extraction convention, and uncertain speech. Request the corresponding information on demand.
Planner owns continuation, Reviewer owns findings, and Solver owns the answer. The held
package exposes target knowledge, not ASR; a future acoustic action needs its own admission.
Do not add another Reviewer pass merely to increase revision frequency.

An improved agent-versus-agent comparison does not establish benefit over direct invocation.
A locked promising system still needs the matched shared-harness direct comparison and
replication before stable-gain claims. No new confirmatory exposure is authorized here.

## Reproduction and custody

The shared APIs are analysis.native_episode_source.verify_native_episode_source,
analysis.native_role_responses.select_verified_native_role_response, and
analysis.slurp_solver_stage_attribution.build_slurp_solver_stage_attribution.
The existing verified reference loader supplies the exact ordered Fold A roster.
Every final diagnostic field is reconciled to the retained official per-sample result.
The official evaluator is never invoked by this analysis.

All artifacts below are under SPEECHRL_DATA_DIR/coordination/slurp-review-measurement-v1:

- anchor-stage-analysis-preregistration-v1.json:
  8c9511b929102537a05c78de28d657d1b3a01351716bea2ecd11c785b91a4727.
- run-anchor-stage-analysis-v1.py: orchestration of shared APIs, with source/config pins
  in anchor-stage-analysis-input-binding-v1.json; no separate runtime or controller.
- anchor-stage-attribution-v1.json:
  796962a3d657ec94364068185d0e763464d56b26cbce3e7ab38105a427678875.
- anchor-five-revision-case-read-v1.json and root-anchor-stage-interpretation-v1.json:
  source-bound case scope and root interpretation without raw response copies.

Analysis implementation commit: bf1e720c (review preparation branch).
Recorded source checkout: slurp-train-anchor-cuda-recovery-v1 at
826a77c7bd9030ccbc25f2b74cd6fa4ed69db561. The shared attribution/Reviewer change passed
110 related tests, 86 percent combined coverage, Ruff and engineering-base checks.
The source audit and analysis took 421.7 seconds with about 2.50 GiB peak resident
memory. It added zero model, analytical tool, GPU or official scoring contacts.
