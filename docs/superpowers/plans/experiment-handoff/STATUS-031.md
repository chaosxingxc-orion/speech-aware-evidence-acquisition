# Status 031: drain E21 and pause GPU dispatch, keeping the model resident

Date: 2026-09-11 UTC. This update records the owner's new scheduling instruction.
The prior goal turn was a verified wait on the live E21 worker. The full research
goal remains incomplete; the GPU pause is not a scientific completion verdict.

## New owner instruction

Read [OWNER-GPU-PAUSE-012.md](OWNER-GPU-PAUSE-012.md) before any dispatch.
Allow the current E21 repair to finish. Then retain the root-owned model service
and GPU memory, but start no further GPU-related experiment until the owner gives
a new explicit instruction. This supersedes STATUS-030's automatic SLURP switch.

The durable DATA coordination receipt is
coordination/owner-gpu-pause-after-e21-v1.json,
SHA-256 de504c139f8c62594b6ed44ea44360bcc0101c3496bc8c9799d9a8caef194966.
It is an owner/root dispatch instruction, not a claim of a new automatic guard.

## Current evidence and custody

At 2026-09-11T04:52:34Z, the repair had written 33 complete call rows out of 44;
its final manifest was absent and worker 21509 remained live. Worker session
99977 was re-polled successfully immediately before this owner update. Preserve
the frozen source at /home/chao/saea-worktrees/e21-offline-repair-generation,
commit 64440737a401b80805cfdd4f09d5a04748a3aad7.

Root lease session 22105, service serving-e21-offline-direct-repair-np4-v1,
coordinator session 95670 and its monitor remain owned by root. Revalidate live
processes and handles; a stored snapshot does not prove current liveness.

## Exact next actions

1. Continue observing the current repair until full seal or authoritative failure.
   Do not restart, reconfigure, or start another neural flight.
2. Verify the complete 1593-window/44-call seal, fresh direct-parent lineage and
   immutable costs. Release only the current experiment lease after verified
   closure. Keep the resident service and monitor; do not unload the model.
3. Release the already-prepared E21 CPU scoring and frozen paired analysis after
   the proper seal/read boundary. Score each complete manifest once, retain
   per-sample statistics, then close decisions, costs and attempts.
4. Preserve the prepared SLURP source and artifacts. Its actual capacity checks,
   service change, leases and generation have not started and are paused.
   Do not execute coordination/slurp-program-matched-frozen-handoff-v1.json
   without a new explicit owner instruction.
5. Preserve all closed/held scientific decisions and the remaining live E21
   review/selection/new-observation evidence gap. No new experiment is admitted
   merely to keep the GPU busy or to fill that gap.

All four SLURP registrations, exact budget limits and frozen analysis remain as
documented in STATUS-030. The shared implementation and frozen experiment
checkouts are unchanged. The current update is a scheduling change only.
