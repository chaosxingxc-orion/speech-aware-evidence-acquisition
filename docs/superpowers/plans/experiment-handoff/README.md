# Owner-directed Stage-2 continuation

Status: **owner-directed execution**, generation 4. Codex coordinates implementation and
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

## Current implementation

Three isolated WSL branches implement shared serving/queue, prepared artifacts/request fit,
and deterministic delivery/scoring. Root owns analysis, protocol amendments and integration.
The null-only NEW500 calibration is completed without model or scorer invocation; KV closure
uses existing finalized evidence only. No experiment service was started during preparation.

Every authored file and model-facing message is English. Dataset identity remains in the
umbrella lock; no new test/confirmatory exposure, paid API spend or Stage-3 execution is admitted.
