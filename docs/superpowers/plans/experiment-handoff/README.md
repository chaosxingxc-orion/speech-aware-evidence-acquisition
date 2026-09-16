# Current continuation: September 16

Read [STATUS-142](STATUS-142.md) and [the two-track plan](../../../readiness/2026-09-16-slurp-two-track-research-plan.md).
SLURP is the only active optimization target. Candidate-width support and source-bound
on-demand knowledge are implemented and tested. Candidate-five and problem-directed
Reviewer configurations remain held until exact flight admission and capacity validation.

The existing E21 static fit has failed before model contact; its dead lease was reconciled.
Do not retry or generate E21. Audio2Tool remains held. Do not reopen the twice-failed
SLURP dynamic-tools flight or read its partial quality.

# Owner-directed Stage-2 continuation

**Latest execution:** [STATUS-142.md](STATUS-142.md) records integrated implementation,
root verification, the E21 terminal boundary, and remaining exact SLURP registration work.
Research preparation runs in parallel; one experiment generates at a time.

**Current comparison direction:** [OWNER-SYSTEM-VERSIONS-025.md](OWNER-SYSTEM-VERSIONS-025.md) makes complete model-versus-system task quality primary and allows evidence-guided expansion of system versions. The supplied/withheld knowledge draft is withdrawn. [The current system plan](../../../readiness/2026-09-13-slurp-direct-vs-native-system-plan-v1.md) and [extension sequence](../../../readiness/2026-09-13-finalized-score-reuse-and-system-extension.md) govern the next work.

**Latest owner direction:** [OWNER-SPEECH-TOOLS-023.md](OWNER-SPEECH-TOOLS-023.md) adds locally loaded speech tools and problem-targeted investigation. [OWNER-DISCRIMINATIVE-VALUES-021.md](OWNER-DISCRIMINATIVE-VALUES-021.md), with OWNER018-020, retains source-grounded distinctions in task-specific values. Include all eight Audio2Tool tiers alongside SLURP and E21/E22 in design/readiness; share the execution base and specialize knowledge and corrective-memory construction. Read [STATUS-044.md](STATUS-044.md) and the [dataset/task analysis](../../../readiness/2026-09-11-task-specific-knowledge-and-memory-analysis.md). Full TRAIN relationship counts and per-carrier audits are complete; three value-format primitives and a TRAIN-bound memory library have CPU tests. Runtime memory integration now has a positive synthetic executor proof; actual memory admission remains pending. The first new live task-agent comparison and its registered matched replication are closed; the subsequent controlled role-coverage comparison is closed without adoption. Preserve historical verdicts and the SLURP-first execution preference.

**Current owner amendment:** [OWNER-SYSTEM-OPTIMIZATION-014.md](OWNER-SYSTEM-OPTIMIZATION-014.md) prioritizes a reusable system with optimization headroom, direct-model comparisons and component directions before system-level training-free RL. Large gains and cost efficiency are not current selection requirements. Earlier statistical verdicts remain recorded but do not veto a promising research base. See [system design](../../../readiness/2026-09-11-system-selection-and-training-free-optimization.md).

Status: **owner-directed execution**, generation 142. Codex coordinates implementation and
owns the model service under [OWNER-CONTINUATION-002.md](OWNER-CONTINUATION-002.md).
The accepted specification is [CONTINUATION-PLAN.md](CONTINUATION-PLAN.md).

Fable5.1 is unavailable. The earlier request/reply and recovery-only decision remain
historical records; no reply or release is invented. Completed integrations are recorded
in [RECOVERY-PLAN.md](RECOVERY-PLAN.md). The owner has now explicitly authorized implementing
the accepted SLURP/Earnings21 plan, including bounded experiments after their own gates.

## Coordination

Run all implementation, tests, preparation, inference and scoring in WSL Ubuntu-24.04.
The root owns the resident service. One experiment worker generates at a time; other agents
prepare eligible work and score complete sealed manifests. Keep flight worktrees frozen and
integrate tested changes serially between flights. Preserve unfinished historical worktrees.

Use the existing results ledger for scientific status. Use state.json for coordination and
the shared runtime receipts for live ownership/readiness. Update state at durable boundaries;
a stale process snapshot does not establish present readiness.

Run the read-only check:

    python scripts/checks/experiment_handoff_check.py

It recognizes OWNER_DIRECTED_EXECUTION only when the local owner decision records the
accepted bounded scope and mandatory per-flight gates. The check still returns
execution_authority=NOT_EVALUATED and launch_allowed=false: these fields mean this
coordination check does not grant a launch. They do not override the owner's continuation
instruction. The actual ExecutionPlan, exposure, runtime, attempt and budget gates decide
each contact. Recovery and original reply-exchange states remain supported.

## Current execution and decisions

Read [STATUS-141.md](STATUS-141.md), state.json and
[OWNER-GPU-RESUME-2026-09-15](OWNER-GPU-RESUME-2026-09-15.md) first. SLURP is
the only active optimization target, and no new flight is admitted. The
incumbent remains in place; broad/factored TRAIN-A was not advanced. Root will
personally examine released candidate, within-candidate and slot failures and
select one information-gain mechanism in the existing agentic framework. The
closed dynamic-tools flight receives no third attempt or relabel restart, and
any future successor requires separate root admission. The current E21 static
fit may finish only its registered capacity measurement;
final registration and all E21 generation are held. The accepted Audio2Tool
shared fix is integrated, while its four-row proof and full flight remain held.
The earlier G6/E21 campaigns' generation, scoring, fixed analysis and all four settlements
are complete. Those earlier G6 SLURP and E21 system admissions fail their frozen rules. STATUS-044 separately admits the newer SLURP task-agent working baseline for exploration. The newer role-coverage pair is closed under STATUS-046; it is not adopted and cannot be replayed under its exhausted registration.
The task-scope
clarification is [OWNER-DATASET-TASKS-010.md](OWNER-DATASET-TASKS-010.md):
summary design is feasibility only; existing dataset tasks govern evaluation.
[OWNER-OFFLINE-QUALITY-009.md](OWNER-OFFLINE-QUALITY-009.md) still prioritizes
offline quality, parallel preparation and exclusive GPU feature encoding
followed by decoder-only inference. The original numerical reproduction remains
complete (16560 statistical fields agree); its report is
[here](../../../results/2026-09-10-fable-reproduction-audit.md).

| Work | Current state | Evidence / next action |
|---|---|---|
| SLURP direct versus native system | Released DEV comparison and TRAIN A anchor complete; selective tools/refresh flight closed after two failures | Preserve both failed sources. Shared bounded outcomes are model-free verified; admit the distinct held TRAIN A system only through fresh plans under STATUS-099 |
| SLURP role-coverage package | Both arms FINALIZED; intent negative, entity improvement unresolved | Close package; preserve compact-frame baseline; full strata and raw lineage verified |
| Audio2Tool native three-arm recovery | All arms FINALIZED and first-scored; frozen analysis and root decision complete | System not admitted; knowledge contribution not established. Full strata and separate labels in the September 12 final result |
| KV recovery and aligned null | Closed retrospectively; retain KC-S1b examples and preserve historical order/missing-decision facts | Existing seven-run FAMILY-REPORT; no rerun or rescore |
| KC-S1b and KU-S3 | Original max64 repeat, max256 matched trio, and independent retrieval repeat completed | Component evidence positive; no equivalence or full-system inference from these repeats |
| KU-S4N and twin | HOLD_NONINFERIORITY_FAILED | G3 encoding and G4 a/b/c remain ineligible; do not encode the 7049 missing exemplars |
| E21 DR | Two full generations, four derived deliveries, scoring and decisions closed | Unit deliveries rejected; self constrained only a small discovery refresh; self free null; derivatives are correlated |
| E21 LOOP and twin | Both complete; targeting contrast positive, incumbent floor failed | Retain KC-E1f; no additional LOOP generation admitted |
| G6 SLURP live intent-to-slots | Complete, scored, decided and parent attempts finalized | Slots improve but the scenario guard fails; full system not admitted; retain prompt-identity attribution limit |
| E21 offline direct-to-KC-E1f | Both stages, complete scores, analysis and settlement closed | PERSON benefit; system not admitted because insertions rise by5; see September11 result |
| SLURP program-matched follow-up | Both arms, deliveries, complete scores, analysis and settlement closed | NEW500 primary and intent guard fail; stop the final owner-authorized pair |
| Live E21 review/selection/observation | Generic bounded phase Planner is implemented and model-free tested | Live selection and new observation remain unproven; the fixed pair does not establish them |
| Dialogue/speaker-topic context | Feasibility only under OWNER-DATASET-TASKS-010 | Judge any later method on the existing dataset task; no new summary/minutes task or evaluator is required |
| Depth2 throughput comparison | Deferred | Close science first; register any new timing comparison separately |

The current results view is [the existing results ledger](../../../results/stage2-results-ledger.md).
Its historical September9 snapshot must not be mistaken for current unread work.
STATUS-009 through STATUS-024 preserve earlier boundaries; their pending items
are superseded only by the cited later decisions, never erased from history.

Root completed all 1000 Whisper observations and both eligible 1000-row answering arms, each with 3000 contacts and first scores. The original treatment remains ABORTED2000. The exact registered analysis is complete and fixed evidence effectiveness is not established; see the [result](../../../readiness/2026-09-12-slurp-fixed-whisper-result-v1.md). Both TRAIN query preparations have sealed. That STATUS-072 snapshot had no live GPU flight; STATUS-075 supersedes its execution state. Earlier results and exemplar holds remain unchanged.

Use ChatGPT/OpenAI cloud subagents under [MODEL-ALLOCATION.md](MODEL-ALLOCATION.md);
the main agent retains planning, scientific decisions, critical review and merge acceptance.
No local assistant model or independent paid API client is deployed. Every authored file
and model-facing message is English. Dataset identity remains in the umbrella lock;
no new test/confirmatory exposure or Stage-3 execution is admitted.

Current knowledge design: [discriminative values](../../../readiness/2026-09-11-discriminative-knowledge-values.md).

Latest handoff: [STATUS-141](STATUS-141.md) makes SLURP the only active
optimization target. No new flight is admitted; the closed dynamic-tools flight receives no third
attempt or relabel restart. A future successor requires a concrete named design
and separate root admission. Root will select one
information-gain mechanism and require a same-roster full-task comparison and
replication if promising. The current E21 capacity fit may finish, but final
registration and all generation remain held. Audio2Tool proof and full flight
remain held. Build a stable agentic baseline before later training-free RL
trajectory and action-space work, then transfer to E21 and Audio2Tool.
