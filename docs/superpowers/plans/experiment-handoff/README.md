# Owner-directed Stage-2 continuation

Status: **owner-directed execution**, generation 25. Codex coordinates implementation and
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

Read [STATUS-025.md](STATUS-025.md) and state.json first. The latest operating
decision is [OWNER-OFFLINE-QUALITY-009.md](OWNER-OFFLINE-QUALITY-009.md): prioritize
post-meeting quality, parallel preparation and exclusive GPU feature encoding
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
| E21 offline direct-to-KC-E1f | Direct generation active; actual full fit passed; repair awaits its new sealed parent | Same resident np4 no-mmproj service; bind all1593 new windows before repair; quality remains unread |
| Live E21 review/selection/observation | Not established by the direct-to-KC-E1f pair | Shared live Reviewer-to-Planner-to-observation evidence remains an explicit gap |
| Dialogue/speaker-topic memory and final minutes | Design only | Temporal-source and episode-end contracts, shared state transitions and prospective evaluation remain required |
| Depth2 throughput comparison | Deferred | Close science first; register any new timing comparison separately |

The current results view is [the existing results ledger](../../../results/stage2-results-ledger.md).
Its historical September9 snapshot must not be mistaken for current unread work.
STATUS-009 through STATUS-024 preserve earlier boundaries; their pending items
are superseded only by the cited later decisions, never erased from history.

The root service and direct worker run from frozen WSL checkouts. The shared
fit passed on every request, and generation is in progress. A stored count or
handoff file does not grant launch authority or establish current process health.
The next phase consumes only this run's newly sealed predecessor, under
[the repair handoff](../../../readiness/2026-09-11-e21-offline-repair-handoff.md).
Do not score direct quality early or launch the held exemplar branch.

Use ChatGPT/OpenAI cloud subagents under [MODEL-ALLOCATION.md](MODEL-ALLOCATION.md);
the main agent retains planning, scientific decisions, critical review and merge acceptance.
No local assistant model or independent paid API client is deployed. Every authored file
and model-facing message is English. Dataset identity remains in the umbrella lock;
no new test/confirmatory exposure or Stage-3 execution is admitted.
