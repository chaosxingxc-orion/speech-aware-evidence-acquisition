# Owner GPU pause after current Earnings21 generation

Date: 2026-09-11 UTC.

## Owner instructions

The current conversation contains the following consecutive owner instructions,
translated into English for this repository:

1. "After the E21 experiment finishes, pause GPU use."
2. "There is no need to release GPU memory. Wait for my instruction before
   starting GPU-related experiments again."

The second instruction clarifies the first. Preserve the current resident model
service after the already-running E21 repair finishes. Do not proactively unload
the model or release its GPU memory.

## Execution boundary

Allow only the already-running E21 repair generation to finish and seal:
SAEA-E21-OFFLINE-KC-E1F-REPAIR-GENERATION-NP4-V1,
attempt-e21-offline-kc-e1f-repair-generation-v1.

After complete seal verification, close its generation accounting and release its
experiment lease. Keep the root-owned service and monitor resident. A successful
worker exit or released experiment lease does not authorize another GPU contact.

Pause every subsequent experiment generation, encoder operation, tokenizer or
actual-capacity check, throughput probe, and serving-profile change until a new
explicit owner instruction. In particular, do not execute the prepared SLURP
service/lease/worker handoff. Do not create a replacement or automatic restart if
the resident service exits unexpectedly.

Continue CPU-only complete scoring, frozen paired analysis, decision recording,
and artifact/attempt settlement for the completed E21 comparison. Keep the one
complete scorer and existing CPU resource limits.

## Preserved work and precedence

OWNER-SLURP-MATCHED-COMPARISON-011 remains the historical approval for exactly one
matched pair and its fixed budgets. Its preparation, four registered plans,
source freeze, and prior scientific guards remain intact. Its dispatch is now
paused; prior registration and readiness do not override this instruction.

This instruction supersedes STATUS-030 and the prepared service handoff wherever
they direct an automatic E21-to-SLURP service switch. It changes scheduling only,
not any scientific method, metric, budget, result, or frozen source.
