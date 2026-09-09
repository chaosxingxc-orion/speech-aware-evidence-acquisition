# Owner-directed Stage-2 continuation

Status: **owner-directed execution**, generation 6. Codex coordinates implementation and
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

Shared serving leases, queue admission, persistent preparation, actual request fitting,
deterministic delivery replay, deferred complete scoring, configuration construction and
the single-window E21 controller bridge are integrated into master with targeted tests.
This is infrastructure progress; G1 through G6 have not flown.

The aligned NEW500 null calibration and all seven KV recovery reads are complete with
zero new model contacts and zero new scorer invocations. Retain KC-S1b: KV0 is harmful,
KV1 and KV3 are null-compatible, and KV2 fails its rotating-twin sign guard. Preserve the
historical missing predecessor decision and do not retroactively admit KV successors.
See the [KV family report](../../../checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md).

KC-S1b's complete 1,000-row contact-free OpenJiuwen execution and historical request
equivalence checks passed. The tokenizer exposure and structured plan are registered; real
fit and final generation registration still block generation. Both KU-S3 retrieval artifacts
passed full-roster historical selection and actual rendered-supply parity with zero contacts,
and are configuration-pinned under OWNER-KUS3-SCHEMA-003 (original examples retained).
The transitive AST inventory helper is implemented; broader rule enforcement remains pending
migration of historical mutable entry points. E21 actual-window CLI wiring, complete DR replay,
bounded live controller transitions and the later configuration families remain unfinished.

Use ChatGPT/OpenAI cloud subagents under [MODEL-ALLOCATION.md](MODEL-ALLOCATION.md);
the main agent retains planning, scientific decisions, critical review and merge acceptance.
No local assistant model or independent paid API client is deployed. Every authored file
and model-facing message is English. Dataset identity remains in the umbrella lock;
no new test/confirmatory exposure or Stage-3 execution is admitted.
