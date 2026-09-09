# Owner-directed Stage-2 continuation

Status: **owner-directed execution**, generation 9. Codex coordinates implementation and
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

The original 64-token KC-S1b same-profile repeat has generated all 1,000 rows and completed
one official scoring job with per-sample statistics retained. Its registered NEW500 entity-side
improvement test passes against the historical direct and KC-S1a controls. This is a component,
same-profile result; inherited different-geometry and independent-roster requirements remain
open. See the [replication verdict](../../../checks/speech-aware-evidence-acquisition/2026-09-09-kc-s1b-replica-verdict/README.md).

The four-case 64/256 engineering pair is complete: two confirmed length stops at 64 become
complete JSON at 77 and 79 tokens under 256; the two other outputs remain identical. Exact
wire responses, stop reasons, hashes and separate delivery views are retained. This is not an
accuracy or reasoning result. See the [budget readout](../../../checks/speech-aware-evidence-acquisition/2026-09-09-output-budget-four-row/README.md).

The owner approved OWNER-KUS3-BUDGET-005: KU-S3a, its form twin and a new matched no-retrieval
control use 256 tokens while retaining original KC-S1b examples. Fresh configurations,
preparation and real full-roster fits are required; the unused 64-token KU-S3 fit plans are
historical plans and must not be repurposed. No pending owner question remains. The root
stopped the former service and monitor after the engineering pair; no model service is active.

The aligned NEW500 null calibration and all seven KV recovery reads remain complete with
zero new model contacts or scorer invocations. Retain KC-S1b: KV0 is harmful, KV1 and KV3 are
null-compatible, and KV2 fails its rotating-twin sign guard. Preserve the historical missing
decisions and order effects. See the [KV family report](../../../checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md).

Shared leases, queue admission, persistent retrieval preparation, actual request fitting,
completion overrides, exact wire capture, deterministic delivery primitives and deferred scoring
are integrated. The new packet validation cache shares one implementation between preprocessing
and client construction, with 191 focused tests passing. It is in-memory only: cross-process
preprocessing reuse and shorter handoffs remain unfinished. The first service window did not
meet the intended idle-time target, as recorded in the budget readout.

G2 through G6 have not flown. E21 actual-window CLI wiring, complete DR replay, bounded live
controller transitions, explicit full-system state joins and broader engineering-rule coverage
remain incomplete. Read [STATUS-009.md](STATUS-009.md) for the next work order and held items.

Use ChatGPT/OpenAI cloud subagents under [MODEL-ALLOCATION.md](MODEL-ALLOCATION.md);
the main agent retains planning, scientific decisions, critical review and merge acceptance.
No local assistant model or independent paid API client is deployed. Every authored file
and model-facing message is English. Dataset identity remains in the umbrella lock;
no new test/confirmatory exposure or Stage-3 execution is admitted.
