# Owner-directed Stage-2 continuation

Status: **owner-directed execution**, generation 34. Codex coordinates implementation and
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

Read [STATUS-034.md](STATUS-034.md), state.json and [OWNER-GPU-RESUME-013.md](OWNER-GPU-RESUME-013.md) first.
The owner explicitly resumed GPU work after network reconnection and prioritizes
high utilization. This supersedes OWNER012's scheduling hold. E21 generation is
sealed and its CPU scoring is in progress; see [STATUS-032.md](STATUS-032.md).
The approved SLURP control has sealed with 2,000 calls. The speech arm is now
running on the same service and frozen source under the unchanged OWNER011 budgets.
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
| KV recovery and aligned null | Closed retrospectively; retain KC-S1b examples and preserve historical order/missing-decision facts | Existing seven-run FAMILY-REPORT; no rerun or rescore |
| KC-S1b and KU-S3 | Original max64 repeat, max256 matched trio, and independent retrieval repeat completed | Component evidence positive; no equivalence or full-system inference from these repeats |
| KU-S4N and twin | HOLD_NONINFERIORITY_FAILED | G3 encoding and G4 a/b/c remain ineligible; do not encode the 7049 missing exemplars |
| E21 DR | Two full generations, four derived deliveries, scoring and decisions closed | Unit deliveries rejected; self constrained only a small discovery refresh; self free null; derivatives are correlated |
| E21 LOOP and twin | Both complete; targeting contrast positive, incumbent floor failed | Retain KC-E1f; no additional LOOP generation admitted |
| G6 SLURP live intent-to-slots | Complete, scored, decided and parent attempts finalized | Slots improve but the scenario guard fails; full system not admitted; retain prompt-identity attribution limit |
| E21 offline direct-to-KC-E1f | Both1593/44 generations sealed; full fresh-parent lineage verified; experiment lease released | Direct score completed once; repair is the sole complete scorer under source 64440737; SLURP GPU work resumed under OWNER013 |
| SLURP program-matched follow-up | Control sealed; speech arm active on the same service | Complete both live phases and actual fits, then joined deliveries and fixed scoring/analysis |
| Live E21 review/selection/observation | Generic bounded phase Planner is implemented and model-free tested | Live selection and new observation remain unproven; the fixed pair does not establish them |
| Dialogue/speaker-topic memory | Feasibility only under OWNER-DATASET-TASKS-010 | Judge any later method on the existing dataset task; no new summary/minutes task or evaluator is required |
| Depth2 throughput comparison | Deferred | Close science first; register any new timing comparison separately |

The current results view is [the existing results ledger](../../../results/stage2-results-ledger.md).
Its historical September9 snapshot must not be mistaken for current unread work.
STATUS-009 through STATUS-024 preserve earlier boundaries; their pending items
are superseded only by the cited later decisions, never erased from history.

The root now owns the SLURP service under OWNER013. Both E21 generations are sealed
and bound; their CPU scoring is released. A stored count or
handoff file does not grant launch authority or establish current process health.
The repair consumes only this run's newly sealed predecessor, under
[the repair handoff](../../../readiness/2026-09-11-e21-offline-repair-handoff.md).
The full E21 pair is now released for CPU scoring. Keep the SLURP quality read
held until both arms seal, and keep the exemplar branch held.

Use ChatGPT/OpenAI cloud subagents under [MODEL-ALLOCATION.md](MODEL-ALLOCATION.md);
the main agent retains planning, scientific decisions, critical review and merge acceptance.
No local assistant model or independent paid API client is deployed. Every authored file
and model-facing message is English. Dataset identity remains in the umbrella lock;
no new test/confirmatory exposure or Stage-3 execution is admitted.
