# Experimental report v3: Fable5.1 inheritance and Codex continuation

Date: 2026-09-16. Author: Codex, root scientific coordinator.
This successor incorporates the latest stopped candidate-view proof. Historical report bytes remain intact.
Scope: released exploratory evidence and the exact state of unfinished work.
No current typed-context/direct TRAIN A quality was read in preparing this report.
The source index binds existing documents; their full stratum tables and original verdicts
remain authoritative. This report is a synthesis, not a new statistical analysis or scorer run.

## 1. Objective and experimental evolution

The object is a frozen-core agentic system for speech tasks: control speech observations
(OBS), knowledge organization (ORG), evidence supply (SUPPLY), and evidence use (USE).
The system must outperform plain invocation usefully and expose real decisions that a later
training-free algorithm can optimize. No core training or second answering model is admitted.

The work evolved through five decisions:

1. Recover Fable's code/worktrees and reproduce its evidence before changing serving or methods.
   The original schema and constrained entity-repair findings survived numerical reproduction.
2. Separate capacity and delivery defects from scientific changes. Keep precomputed SLURP
   features and decoder-only serving; compare output-cap changes with matched controls.
   Preserve old results instead of rewriting their manifests.
3. Move from isolated components to complete direct-versus-agent comparisons using one harness.
   A schema result with a sealed predecessor is not proof of a live autonomous system.
4. Separate intent activation knowledge from slot/parameter interpretation. Preserve several
   candidate hypotheses rather than making an irreversible early top-one decision.
   Use Reviewer/Planner for on-demand investigation; keep Solver authority.
5. Focus on SLURP, analyze candidate inclusion separately from downstream resolution/extraction,
   and test role-specific context normalization. Defer algorithmic RL until a useful stable
   base and observable action workspace are in place.

These are design choices, not evidence that every component improved outcomes.

## 2. Experimental and metric discipline

Direct and system arms use the shared controller, FlightRuntime and OpenJiuwen executor.
Keep weights, speech identity, legal task contract, roster, service geometry and decoding
matched where specified. Any mismatch is reported, not silently repaired.

The official SLURP headline is pooled micro SLU F1 reconstructed from saved word/character
TP/FP/FN. It is not the mean of per-row F1, strict entity-set exactness, or intent accuracy.
Report these separately. The full comparison retains malformed, saturated and fallback rows.

Completed TRAIN A analyses use 1,080 recordings, 125 speakers and 18 scenarios of 60 recordings.
The current primary uses 10,000 whole-speaker bootstrap draws, seed 20260915, CI95;
diagnostics use CI90. Historical protocols sometimes use different estimators or seeds.
Do not rewrite them or compare confidence intervals as though they were one common test.

NEW500 and DEV1000 are historically exposed development cohorts. Positive results below do
not establish unseen-data generalization, individual-component causality, or algorithmic RL.
Fold B remains untouched for the later frozen evaluation. Gold/reference material is offline
scoring input only; it must not enter runtime or corrective-memory contexts.

## 3. Inherited mechanisms and recovery outcomes

### Numerical reproduction of Fable's evidence

The September 10 audit reused sealed statistics and independently checked arithmetic.
All **16,560 statistical numeric fields** agreed. These are fields, not new observations.
The audit added zero model, tokenizer, encoder, audio-decode or official-scoring contacts.
It is numerical reproduction; existing independent inference repeats are labeled separately.

Original SLURP KC-S1b versus direct on NEW500:

- Strict entity mean row F1: +10.1067 points, CI90 [8.1133, 12.1870].
- Mean row SLU F1: +10.8463 points, CI90 [8.7560, 12.9385].
- On DEV1000, official pooled SLU was 35.8020 direct, 35.7496 extra-contact KC-S1a,
  and 44.3503 schema KC-S1b.

Thus an additional contact alone did not explain the improvement. The task-specific schema
was useful in that component protocol. The sealed predecessor prevents calling it a complete
live-system intent improvement.

Source: [Fable reproduction audit](../../results/2026-09-10-fable-reproduction-audit.md).

| Family | Closed finding | What remains binding |
| --- | --- | --- |
| Seven KV runs | KV0 harmed quality after removal of original examples; KV1/KV3 null-compatible; KV2 failed its inherited rotating-twin guard | Retain KC-S1b examples. Preserve historical order/missing-decision deviations; do not rerun/rescore the family. |
| KC-S1b / KU-S3 | Max64 reproduction, matched max256 trio and independent retrieval repeat completed; component evidence positive | Do not infer live-system equivalence or transfer component gains automatically. |
| KU-S4N and twin | Noninferiority failed | G3 example encoding and G4 a/b/c remain ineligible. Do not encode the 7,049 missing examples to keep GPU busy. |
| G6 live intent-to-slots | Slots improved but scenario protection failed; prompt-identity attribution remained limited | Full system not admitted under that protocol. |
| Owner-authorized program-matched follow-up | NEW500 primary and intent guard failed | Final authorized pair closed; no repeat-to-pass. |
| Original max256 native agent | Positive direct comparison but planned exact replica aborted at revision exhaustion | It is not the later max512 dual-store system. Preserve version distinctions. |

The owner approved investigating truncation: two diagnostic outputs were cut at 64 and
finished at 77/79 tokens under 256. Subsequent KU-S3 controls used 256. The current native
system uses 512 per contact. These facts do not establish that chain-of-thought improves
quality, and the per-contact maximum is not a whole-agent trajectory budget.

For the older family decisions, use the
[results ledger](../../results/stage2-results-ledger.md) and
[KV family report](../../checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md);
their historical status text is superseded only by explicit later verdicts.

## 4. The useful SLURP base is already established at exploratory scope

The max512 dual-store base has two positive matched comparisons on the same NEW500 cohort:

| Pair | Direct pooled SLU | Agent pooled SLU | Difference, points | Speaker CI90 |
| --- | ---: | ---: | ---: | --- |
| First pair | 36.1437 | 50.4479 | +14.3042 | [11.2445, 17.5009] |
| Matched replica | 35.8906 | 50.6876 | +14.7970 | [11.5245, 18.0112] |

The replica's complete DEV1000 result was 35.6750 -> 50.2983, +14.6233 points.
The replica had five malformed final outputs, retained in analysis; no final output hit
the 512-token maximum. Direct used 1,000 contacts; agent used 5,040 contacts.
This is a useful reproducible package on an exposed cohort, not a guarantee that its
Reviewer, tools or each knowledge component separately helps.

Full NEW500/OLD500/DEV1000 scenario tables and source hashes are in the
[replication verdict](../../results/2026-09-14-slurp-dual-store-base-replication-verdict-v1.md).
The first-pair source is the
[reboot-recovery verdict](../../readiness/2026-09-14-slurp-direct-vs-native-dual-store-reboot-recovery-verdict-v1.md).
A historical one-output log-tail exposure is disclosed in the replica report; no rule was
changed after it. Preserve that record.

**Root conclusion:** do not describe the program as having no useful agent baseline.
The outstanding work is to establish a richer, correctly exercised optimization workspace
without losing that demonstrated task benefit.

## 5. Two completed SLURP extensions did not advance

All values below use the same complete TRAIN A cohort. Percentages and points are distinct.

| Measure | N3 anchor | Maximum-five | Broad/factored K60 |
| --- | ---: | ---: | ---: |
| Candidate gold inclusion | 937/1080 (86.76%) | 951/1080 (88.06%) | 947/1080 (87.69%) |
| Correct final intent | 842/1080 | 837/1080 | 841/1080 |
| Official pooled SLU F1 | 48.5336% | 48.6204% | 47.6347% |
| SLU difference versus anchor | -- | +0.0867 pp | -0.8990 pp |
| Paired CI95 of SLU difference | -- | [-1.3650, 1.6510] | [-2.6077, 0.7821] |
| Decision | Retained anchor | NOT_ADVANCED | NOT_ADVANCED |

Maximum-five gained coverage on 19 rows and lost it on five: it was not a monotonic candidate
superset. Broad/factored gained 30 and lost 20; it changed organization and breadth together.
Broad/factored entity-pair F1 fell 2.0316 points, CI90 [-3.7584, -0.3293].
Do not attribute its effect solely to breadth or propose K60/factoring as untested.

A completed offline breadth audit found own-intent-card availability of 947, 973, 995,
1,020, 1,040 and 1,074 /1,080 at K8/12/16/24/32/60. K32 used about 3.97 times the
knowledge bytes. This is card-supply coverage, **not generated candidate inclusion**.
No need to recompute the grid. A 95% candidate goal requires at least 1,026/1,080 covered;
the evaluated candidate systems remain below it.

Sources: [maximum-five](../../results/2026-09-16-slurp-candidate-five-train-a.md),
[broad/factored](../../results/2026-09-16-slurp-broad-factored-train-a.md),
[numeric inventory](../../results/2026-09-16-slurp-coverage-gap-numeric-inventory.md).

### Full error partition and persistent intersections

| Disjoint row category | Anchor | Maximum-five | Broad/factored | Same category in all three |
| --- | ---: | ---: | ---: | ---: |
| Gold candidate missing | 143 | 129 | 133 | 100 |
| Covered, final intent wrong | 95 | 114 | 106 | 60 |
| Final intent correct, entities nonexact | 525 | 519 | 540 | 426 |
| Intent and entities exact | 317 | 318 | 301 | 232 |

The last column is a descriptive intersection, not a recoverable-gain estimate.
Different complete systems and their downstream contexts prevent causal component attribution.

**Root conclusion:** widening information alone was insufficient in the tested packages.
Keep useful candidates from being discarded, improve the distinctions that actually separate
them, and address slot interpretation independently. Choose a specific information gap rather
than automatically sweeping N or increasing context.

## 6. Downstream errors and the actual Reviewer bottleneck

The released anchor's 525 correct-intent/nonexact-entity rows include 127 FN-only,
134 FP-only and 264 mixed. Full official FP+FN loss mass decomposes as:

| Loss component | Natural-mixture share |
| --- | ---: |
| Unmatched reference | 31.49% |
| Unmatched prediction | 28.82% |
| Same-type filler distance | 35.04% |
| Heuristic equal-filler type swap | 4.65% |

These are loss shares; overlapping sample counts cannot be added. Filler distance does not
identify whether hearing, span boundaries, normalization or semantics caused the error.
Of 414 reference-empty rows, 184 emitted entities. This is annotation-relative over-extraction,
not proof that every emitted concept was hallucinated.

Temporal follow-up found all 84 unmatched-reference-date cases had the date card visible to
both initial Solver and Reviewer; 25 omitted dates appeared in candidate distinctions.
A candidate statement is not an independently verified transcript. The finding argues against
a simple card-delivery failure, not against all acoustic uncertainty.

The complete released anchor's initial Solver had 843 correct intents; final delivery had
842. Reviewer/Planner led to only five executed revisions:

- Intent exact: zero saves, one harm.
- Entity-set exact and full-task exact: zero saves and zero harms.
- Two changed responses improved a partial slot-distance diagnostic; one worsened it.
- Initial Planner accepted 1,075 drafts, including 759 offline full-task errors.
  This is routing behavior, not a measured Reviewer detection-recall rate.
- Six REVISE decisions are not six executed revisions: one exceeded the allowed revision count.

Root inspected all five revised trajectories. Observed issues included treating alternative
candidate hypotheses as simultaneous requests, proposing an unsupported illustrative filler,
naming an incompatible legal intent, and revising acoustic ambiguity without new observation.
Reviewer seeing the same speech and history does not make its errors independent.

Sources: [entity loss](../../results/2026-09-14-slurp-train-a-entity-loss-attribution-v1.md),
[temporal diagnosis](../../results/2026-09-16-slurp-temporal-slot-diagnosis.md),
[review attribution](../../results/2026-09-16-slurp-train-a-review-stage-attribution.md),
[context provenance](../../results/2026-09-16-slurp-review-context-provenance.md).

**Root conclusion:** knowledge availability, issue identification, useful evidence acquisition
and correct revision are separate links. A meaningful context module must preserve their
distinctions and expose failures. Adding another generic review pass is not itself a remedy.

## 7. Latest typed-context experiment: closed without complete quality evidence

The intended question was whether a complete typed-context/structured-review/target-lookup
agent improved native SLURP quality over direct on the same 1,080 TRAIN A recordings.
It did not produce a complete system source, so that question remains unanswered.

| Item | Final established state |
| --- | --- |
| Direct comparator | 1,080 rows complete, first official score, FINALIZED; quality remains unread |
| Original system | ABORTED after 507 generation contacts |
| Original repair proof | Four rows finalized: 44 generation contacts, 176 FIT endpoint calls, no task-quality score |
| Sole full system recovery | ABORTED after 6,645 generation contacts at 2026-09-16 17:07:37 UTC |
| Flight status | CLOSED_SECOND_FAILURE_NO_FURTHER_RECOVERY |
| Complete system manifest / official score | Absent |
| Paired analysis / matched replica | Ineligible; do not activate |

The first failure followed a multi-tool response exceeding the one-action bound. Dispatch
was rejected, but continuation lacked all matching tool-result observations. The shared
repair rejects the entire batch, preserves raw calls and supplies complete ordered rejection
feedback. Its four-row proof had minimum capacity margin 1,562 tokens. That was engineering
evidence for exercised requests only, not proof that all future dynamic requests would fit.

The sole full recovery later encountered an actual Reviewer request needing 24,878 tokens:
24,299 text + 65 speech + 2 special + 512 output, against a 24,576-token slot.
The fit guard refused that request before generation. There were 6,646 FIT receipts,
6,645 passes and one failure, involving 26,584 FIT endpoint calls. Partial generation
exposure and 18,136.492 repeated speech seconds remain recorded.

This was a demonstrated request-capacity failure. These receipts do not establish a new
machine reboot, OOM, or task-quality failure. Do not infer accuracy from completed-looking
prefixes, score them, read the held direct score, splice output, or relabel a third attempt.
The failed execution source remains frozen at 9bf27b28708bb93607138e7bcd1eacb66eab3f08.

Root's structural source audit found two knowledge lookups returning 3 and 21 bodies already
visible in Reviewer input; the second returned 38,938 UTF-8 body bytes. The first post-tool
wire was verified to contain base and returned copies. The final failed wire was not fully
reconstructed, so the audit does not claim measured token savings or complete causal
attribution of the overrun.

The optional shared native-knowledge-reference-v1 projection is implemented at
e4b8798b4c023c8d0ff5f24ad596d2820da808f9. It references only an exact earlier visible full body
with matching ID, URI and content, while retaining canonical tool results and new evidence.
WSL validation passed 309 tests with one Windows-only skip; new projection coverage was
92%. This was CPU-only verification: no tokenizer, model or official scorer contact.
It does not reopen the failed flight or prove task-quality preservation.

Root then selected a distinct information-use successor on the older useful dual-store
agent: candidate-bound slot explanations with original facts, role program and selection
held fixed. Its model-free acceptance is recorded in IMPLEMENTATION-HANDOVER-v2.md.
A distinct four-row live proof subsequently stopped before Solver generation, as recorded
below. No complete scientific comparison has established its task quality.

Source: [terminal report](TERMINAL-UPDATE-20260916.md),
[structural diagnosis](CONTEXT-ROOT-CAUSE-20260916.md),
[verified reference implementation](IMPLEMENTATION-UPDATE.md), and
[selected successor](../../readiness/2026-09-16-candidate-bound-slot-view-design-v1.md).

### 7.1 Candidate-bound slot-view proof: latest engineering closure

This is a distinct successor on the older useful dual-store agent, not a third
typed-context recovery. It changes only the source-bound slot consumption view.
The implementation passed 248 affected WSL tests with one platform skip and 83% combined
coverage, but those checks missed the legacy plain-body rendering route.

| Item | Terminal result |
| --- | --- |
| Run | SAEA-SLURP-CANDIDATE-SLOT-VIEW-PROOF4-V1 |
| Frozen source | 3c14a0b0780967a5d224c573e8a991c0fd255607 |
| Attempt state | ABORTED |
| Worker exit | 1, at 2026-09-16T19:12:06.532151+00:00 |
| Actual generation | Four Perception contacts; 10.5955625 repeated speech seconds |
| Actual FIT | Four receipts, 16 endpoints, all passed; minimum margin 20,417 tokens |
| Failure | First Solver view: target slot full content differs |
| Complete result / task-quality read | None / none |
| Decision | STOPPED_ENGINEERING_SOURCE_CONTENT_MISMATCH_NO_RETRY_UNDER_THIS_PROOF |

The recorded FIT evidence concerns Perception only. It does not validate Solver or Reviewer
capacity. Root's source inspection identifies a representation mismatch: the retained
task-contract-only dispatcher's shared renderer supplies plain canonical content; the new
projector requires the named-store-prefixed form. Source binding correctly refused the
mismatch. This does not show a task-quality failure, OOM or host reboot.

The registered envelope was 44 generation contacts, 176 FIT endpoints, 24 analytical tool
invocations, 117 repeated speech seconds and one FIT-inclusive GPU hour. The draft 16-tool
cap was corrected to24 before any contact. Actual usage is not the registration envelope.

Root proved quiescence, marked the still-open attempt ABORTED and released the worker
lease. The decoder was left resident. Both failed checkouts and raw artifacts are preserved.
No repair or additional live admission is claimed by this report.

Next: reproduce and repair the exact shared rendering route on CPU in a new worktree,
then prepare a concrete fresh admission proposal. Do not reuse the stopped attempt.
The complete scientific comparison remains prospective.

Source: [latest closure and repair contract](LIVE-PROOF-CLOSURE-v1.md),
[operating metadata](OPERATING-SNAPSHOT-v3.json) and
[registered proof](../../readiness/2026-09-16-slurp-candidate-slot-view-proof4-v1/README.md).

## 8. E21: valuable repair evidence, deferred agentic extension

| Experiment | Released result | Decision / limitation |
| --- | --- | --- |
| Original KC-E1 first-pass background | PERSON improved but whole WER worsened and deletions increased | Harmful overall; background volume alone did not help transcription. |
| KC-E1f constrained repair | PERSON error 22.488858% -> 18.752143%; +3.7367 pp reduction | Passed historical v2 rules; original v1 rejection preserved. |
| Same-roster KC-E1f repeat | +3.6339 pp PERSON reduction, CI90 [2.590, 4.690] | Replication obligation met for this limited component/roster. |
| DR, two generations / four deliveries | Self-constrained reduced 20 total errors and four PERSON errors; unit deliveries rejected, self-free null | Small discovery refresh; correlated derivatives, no replacement of KC-E1f. |
| LOOP versus random twin | PERSON reduction +1.4741 pp versus twin but -1.7141 pp versus KC-E1f | Targeting contrast positive; incumbent retention failed; no new LOOP generation. |
| Fresh offline direct -> KC-E1f | 99 fewer PERSON and 165 fewer total word errors, five more insertions | Failed original zero-insertion-increase guard; retain both gain and failed admission. |

The fresh offline system covered 44 calls / 1,593 windows / 359,765 words:

- WER 8.12086% -> 8.07499%, reduction 0.04586 pp, CI90 [0.0334, 0.0592].
- PERSON error 23.14021% -> 19.74631%, reduction 3.39390 pp, CI90 [2.4461, 4.4005].
- Total errors 29,216 -> 29,051; PERSON errors 675 -> 576; insertions 10,336 -> 10,341.

The owner subsequently prioritized WER/PERSON with insertion changes analyzed separately
for future protocols. Do not retroactively change this result.
Fixed offline repair does not establish live Reviewer selection or dynamic listening quality.

The newest E21 native-window static FIT stopped before any model/tokenizer contact because
its exposure carrier omitted exact lock key earnings21-original. Its lease was reconciled;
E21 remains held, without automatic retry. Do not confuse this technical zero-contact hold
with failure of the older completed repair system.

Sources: [KC-E1f redecision](../../readiness/2026-09-08-e21-kc-e1f-repair-pass-v2-redecision.md),
[replication](../../readiness/2026-09-08-e21-kc-e1f-replication-v1-verdict.md),
[DR](../../readiness/2026-09-10-e21-dr-packets-four-delivery-decision.md),
[LOOP](../../readiness/2026-09-10-e21-loop-packets-decision.md),
[offline system](../../readiness/2026-09-11-e21-offline-system-result.md).

Diarization, local dialogue context and speaker summaries remain feasibility ideas.
Evaluate any later admitted method on the dataset's native task; no new meeting-minutes
or summary-quality benchmark is implied. E22 has no newly admitted GPU experiment.

## 9. Audio2Tool: preserve both gains and selection regressions

### Earlier Fable SELECT/FILL insight

The historical 104-row SELECT_THEN_FILL study is useful evidence about information contracts.
Its historical scorer reported exact 25.00% versus direct 17.31%, while matching joint
draft/revise exact and losing tool accuracy and slot F1 against that control. It was not
promoted. Later v2 projections exist and must not be mixed with those historical definitions.

Its K32 retrieval included all required tool names on 100/104 rows. That was SUPPLY
reachability, not generated-candidate accuracy. Correct selected-tool multiset occurred on
62 rows; only 26 were fully exact. SELECT had been stripped of interface details that also
help distinguish tools. FILL had default/omission and occurrence-binding errors.
Thus two-stage decomposition was reasonable, but did not alone establish superiority.

Source: [SELECT/FILL verdict](../../readiness/2026-09-03-a2t-select-fill-agentloop-104-v1-verdict.md).
Earlier copy-trap studies show default values can contaminate arguments; removing defaults
reduced induced substitutions, but registry augmentation could reopen the channel.
These bounded historical studies are not modern full-cohort effectiveness evidence.

### Latest complete native-role system, 4,000 rows

The latest full comparison spans eight tiers of 500 and 2,097 query clusters.

| Metric | Direct | Agent | Difference |
| --- | ---: | ---: | ---: |
| Official primary-call exact | 18.500% | 22.550% | +4.050 pp; CI95 [2.963, 5.165] |
| Official primary-tool accuracy | 62.025% | 58.425% | -3.600 pp |
| Official macro parameter F1 | 30.149% | 34.902% | +4.753 pp |
| Repository ordered-tool accuracy | 53.525% | 50.325% | -3.200 pp |

Verdict: PRIMARY_GAIN_TOOL_GUARD_FAILED_NOT_ADOPTED.
The official scorer evaluates the primary call; repository call-multiset exact ignores
order; ordered-tool accuracy ignores argument correctness. No metric is silently renamed
full ordered-call exactness. The published paper is an external reference, not a matched
model or a mathematical ceiling. Its columns and all eight strata remain in the original report.

The primary target appears in candidates on 2,882/4,000 rows (72.05%).
Of these, 2,307 have the correct final primary tool; 575 still fail.
Observed-absent candidates account for 1,117 rows; one unavailable state is retained separately.
System versus direct gains 65 correct tools in candidate-present rows and loses 209 in
candidate-absent rows. This localizes errors descriptively; it does not prove candidate
constraints caused them. The Solver escaped the union correctly on 30 rows and incorrectly
on 73, so a hard union restriction would also remove recoveries.

Full ordered action attribution subsequently found order-preserving candidate assignment
on 2,567/4,000 rows (64.175%), not 72.05%. Of 5,417 expected occurrences, 1,661 lacked an
order-compatible assignment; 1,543 of these were absent even from the union.
Among the 2,567 covered rows, 593 delivered the wrong full tool sequence and 1,250 had the
right sequence but failed repository exactness. Primary-call and full-sequence cohorts differ.

On the 2,089 rows where both systems chose the correct primary tool, exact improved
665 -> 829 and wrong-value samples fell 950 -> 784; missing-key samples rose 107 -> 131.
DeviceId accounts for 583 of 941 residual wrong keys. These are overlapping and
outcome-conditioned diagnostics, not an isolated causal effect of parameter knowledge.
A public default is not evidence that the user requested that value.

Sources: [complete system](../../results/2026-09-15-a2t-native-role-base-full4000.md),
[ordered actions](../../results/2026-09-15-a2t-ordered-action-attribution-v1.md),
[primary parameters](../../results/2026-09-15-a2t-primary-parameter-attribution-v1.md).

The separate September 12 three-arm system/knowledge experiment was also closed without
adoption; it is not the later primary-gain package. A domain-grouped registry intervention
had earlier harmed tool accuracy by 3.23 points. Do not combine these versions.

**Root conclusion:** the system can improve parameter resolution while damaging tool
selection. This supports the owner's two-track reasoning and separate knowledge roles.
It does not justify restarting multiple datasets now. Audio2Tool scope-tools preparation
and shared capacity repair are held for later, with no automatic proof/full-run launch.

## 10. Current scientific position

Established:
- Task-specific schema/repair mechanisms have reproducible limited value.
- A max512 dual-store SLURP agent has repeated whole-system exploratory gains over direct.
- Audio2Tool's latest agent improves primary-call exactness while exposing a selection defect.
- Simple candidate widening, broad/factored supply and fixed Whisper do not establish the
  desired SLURP progression.

Unestablished:
- Quality benefit of the current typed-context package.
- Causal benefit of its individual roles or tools.
- Adaptive acoustic-tool/refresh effectiveness for the current SLURP system.
- A complete role-specific projection of all knowledge.
- Generalization to untouched data or transfers to E21/E22.
- Any implemented, evaluated algorithmic training-free RL improvement.

The fixed Whisper SLURP experiment yielded NEW500 micro +0.833 pp, CI90 [-1.098, 2.835],
and DEV1000 micro +0.017 pp with intent -0.9 pp. Most output discordance predated revision,
so do not attribute all changes to ASR. Fixed transcript delivery and on-demand investigation
answer different questions. Source:
[fixed Whisper result](../../readiness/2026-09-12-slurp-fixed-whisper-result-v1.md).

The typed-context flight is closed and its later candidate-view engineering successor also
stopped. The next action is a narrow CPU reproduction and repair of the exact rendering
contract, followed by a concrete fresh admission proposal. Neither stopped identity may be
reused. Read [the current handoff](HANDOFF-v3.md) and
[next designs and expectations](NEXT-EXPERIMENTS-v3.md).
No task-quality conclusion has been released for either unfinished system.
