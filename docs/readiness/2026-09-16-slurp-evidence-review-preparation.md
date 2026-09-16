# SLURP problem-directed Reviewer preparation

Date: 2026-09-16. Status: shared implementation and held configuration; no experiment admission or model contact.

## Concrete gap and implemented behavior

The retained intent-boundaries store has 60 values and the slot-contracts store has 54 values.
Every value in these two released snapshots has a null task_target. The generic target-lookup
tool uses task_target and would therefore return no mapping if simply enabled on these stores.

Bind the original authored construction relations to on-demand consumption instead. Rebuild
each supported source through the existing semantic builder and require exact equality with
the pinned snapshot. For slots, reuse the same released candidate index as automatic Solver
supply. Do not infer relationships from text or an arbitrary identifier suffix. Preserve all
historical snapshot bytes and knowledge content.

The actual source check found 60 intent-to-value relations and 402 intent-to-slot-value
relations covering all 60 intents. Shared slot values remain shared. These are knowledge
mapping counts, not task accuracy, candidate recall, or evidence that any slot is required.

The named-store router attaches a source-bound index only for an explicitly enabled target
tool. The tool reuses the existing bounded round-robin selection, records the index receipt,
and retains the existing already-visible/no-refill semantics. Default task_target selection
and historical configurations without this tool retain their behavior. The wrapper source
pin is updated with the implementation. No new controller or execution framework is added.

## Held Reviewer configuration

Use configs/baseline/slurp-native-evidence-review-train-a-held-v1.json with the original
candidate module and knowledge sources. Its new Reviewer prompt requests a concrete intent
or entity issue, the evidence that supports it, and remaining uncertainty. It does not require
a tool call. Reviewer may query the task contract or either named knowledge store; Planner
keeps action selection and Solver keeps final answer authority.

Keep three Reviewer iterations, reserving the last for a report, and one possible Solver
revision. This is a proposed review-policy package, not an isolated prompt-only contrast.
Do not conflate its effect with candidate-width changes. A future matched comparison must
hold the candidate source fixed and count corrections, harmful changes, tools used, and
official complete-task quality.

The shared role history is still visible. This configuration does not implement draft-blind
review or guarantee independent errors. A separate context-visibility mechanism, if pursued,
requires its own measured comparison. Local Whisper is not enabled by this fragment; its
registered observation route and prior closed failures require separate engineering proof
and prospective admission before use.

## Verification and remaining work

The initial focused suite passed 106 tests across released target indices, existing target
lookup, native tool routing, named stores, candidate supply and native runner behavior.
Tests cover source mutation, source/snapshot mismatch, wrong inventory, foreign index reuse,
shared values, repeated queries, and source-bound native tool evidence. Engineering-base
and diff checks passed. The held native role and tool configuration loads successfully.

Actual source validation is recorded outside Git at
coordination/slurp-two-track-research-v1/root-released-target-index-preparation-v1.json,
SHA-256 abd37a5fc88b37ad6ce1232a2c62c2761755b1152f9d1923521160614314548a.
The original slot relation exactly matches the incumbent automatic supply index.

Before generation: root finalizes the paired analysis and flight identity, freezes source and
configuration, registers model/tool/fit limits, prepares supply, and verifies actual requests
on the matching resident service. Keep this package held while the candidate-width comparison
is prepared. No Fold B or aborted partial outcomes were read. No new generation, scoring,
ASR, encoding or tokenization contact occurred in this preparation.
