# Owner-directed Stage-2 continuation

Status: **owner-directed execution**, generation 21. Codex coordinates implementation and
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

Latest priority: [OWNER-REPRODUCTION-FIRST-008.md](OWNER-REPRODUCTION-FIRST-008.md).
Original results have been numerically reproduced before further adjustment: all 16,560
statistical values agree; no service, generation or scoring was added. Read
[STATUS-021.md](STATUS-021.md) and the [independent report](../../../results/2026-09-10-fable-reproduction-audit.md).
Feature-serving qualification and DR/LOOP expansion remain paused at this review boundary.
The earlier implementation and experiment status below remains preserved.

The original 64-token KC-S1b same-profile repeat has generated all 1,000 rows and completed
one official scoring job with per-sample statistics retained. Its registered NEW500 entity-side
improvement test passes against the historical direct and KC-S1a controls. This is a component,
same-profile result; inherited different-geometry and independent-roster requirements remain
open. See the [replication verdict](../../../checks/speech-aware-evidence-acquisition/2026-09-09-kc-s1b-replica-verdict/README.md).

The four-case 64/256 engineering pair is complete: two confirmed length stops at 64 become
complete JSON at 77 and 79 tokens under 256; the two other outputs remain identical. Exact
wire responses, stop reasons, hashes and separate delivery views are retained. This is not an
accuracy or reasoning result. See the [budget readout](../../../checks/speech-aware-evidence-acquisition/2026-09-09-output-budget-four-row/README.md).

The owner approved OWNER-KUS3-BUDGET-005: KU-S3a, its form twin and the matched no-retrieval
control use 256 tokens while retaining original KC-S1b examples. The first control completed;
a/twin were refused before generation, and the old service exited. OWNER-KUS3-RECOVERY-006
approves one additional same-process matched control in the recovered service. The complete
control/speech/twin trio is finalized and scored once each. The registered entity-side numerical
contrasts and inherited joined-intent protection pass; the scoped component is ADMITTED. The decoder-only
service has stopped. See [STATUS-015.md](STATUS-015.md) and the
[component readout](../../../checks/speech-aware-evidence-acquisition/2026-09-10-ku-s3-max256-recovery-verdict/README.md).
Follow [OWNER-FEATURE-SERVING-007.md](OWNER-FEATURE-SERVING-007.md): prepare features before
generation and keep mmproj out of resident GPU memory. E21's old GPU-mmproj planning fragments
remain held for successors; G2 already uses prepared decoder-only speech packets.

The aligned NEW500 null calibration and all seven KV recovery reads remain complete with
zero new model contacts or scorer invocations. Retain KC-S1b: KV0 is harmful, KV1 and KV3 are
null-compatible, and KV2 fails its rotating-twin sign guard. Preserve the historical missing
decisions and order effects. See the [KV family report](../../../checks/speech-aware-evidence-acquisition/2026-09-09-kv-recovery/FAMILY-REPORT.md).

Shared leases, queue admission, persistent retrieval preparation, actual request fitting,
completion overrides, exact wire capture, deterministic delivery primitives and deferred scoring
are integrated. Registered request identity comparison now ignores only validated dynamic route
identifiers, retaining substantive provenance checks. The shared TRAIN contract cache avoids
repeated JSON parsing while checking source bytes; fresh recovery supply preserves every selected
ID and rendered byte. Full CPU request revalidation still delays handoffs beyond the one-minute
target; preserve the frozen completed campaign while optimizing its successors.

G2 N/twin completed 1000-row generation and one whole official scoring job per arm. The
frozen aligned analysis returned HOLD_NONINFERIORITY_FAILED; G3 exemplar encoding and G4
a/b/c remain held. Do not treat prior DATA_READY notes as permission to continue that branch.
The shared constrained-delivery replay reproduces all 1593 historical KC-E1f windows and 44
stitched calls; see the [full replay receipt](../../../checks/speech-aware-evidence-acquisition/2026-09-09-e21-constrained-replay/README.md).

E21 exact-four CPU feature encoding is now complete through the shared config-driven entry:
four unique contacts, eight cache chunks, source-bound audit and normal-stop provenance.
The same entry verifies warm reuse without a model service and adds zero contacts. The
normal transport and actual fit paths enforce configured cache pins and CPU projector
placement. The new six-slot profile remains held for actual strict-cache qualification,
request capacity and current executor bridge evidence. G5 scientific generation and G6
live full-system baselines are incomplete. Read [STATUS-020.md](STATUS-020.md) and the
[actual preparation receipt](../../../receipts/e21-four-window-cpu-feature-preparation-v1.json).

Use ChatGPT/OpenAI cloud subagents under [MODEL-ALLOCATION.md](MODEL-ALLOCATION.md);
the main agent retains planning, scientific decisions, critical review and merge acceptance.
No local assistant model or independent paid API client is deployed. Every authored file
and model-facing message is English. Dataset identity remains in the umbrella lock;
no new test/confirmatory exposure or Stage-3 execution is admitted.
