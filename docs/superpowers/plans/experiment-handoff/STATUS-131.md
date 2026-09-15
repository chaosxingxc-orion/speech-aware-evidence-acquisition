# STATUS-131: shared on-demand target knowledge integrated; GPU hold active

Date: 2026-09-15. The owner GPU hold remains active. The prior Audio2Tool GPU task finished at 09:36:23 UTC; its complete scoring, decision and candidate attribution remain closed under STATUS-130. No successor GPU generation, fit/tokenizer contact, encoding or service restart has occurred. Preserve the resident service and memory.

## Completed CPU work

Root designed and reviewed an on-demand target knowledge action for Reviewer and Planner. A bounded coding agent implemented the pure shared selector; root integrated the registered wrapper, phase dispatcher, tool schema, named-store receipts and actual native graph tests. The opt-in tool is saea-tool-knowledge-target-lookup-v1. It reuses explicit task-target mappings and the shared bounded round-robin selector, supplies only new values, records missing targets and retains the frozen store/source/query/tool-call binding.

Root also corrected the existing last-role Planner dispatch issue: native tools may run inside Planner's bounded node loop even though Planner is the last listed graph phase. Legacy sequential behavior remains unchanged. The four real OpenJiuwen test combinations cover Reviewer or Planner querying activation or parameter-meaning knowledge; each returned value reaches the calling role and subsequent Solver revision. The tests use synthetic inputs and fake model transport.

Implementation commit: e40acf880218518dd462a6b99b8170f13e1509be.
Canonical master merge: b0b9bf30950e2f87c5c01f724fac0f088f32de68.
Verification: 460 focused tests passed; selector coverage 96.20%, shared dispatcher coverage 83.68%; Ruff and engineering-base checks passed. All 11 implementation/config/test file hashes match the verified source after merge.

Read [the capability and adoption contract](../../../readiness/2026-09-15-native-target-knowledge-tool-v1.md). The data-root receipt is coordination/native-target-knowledge-tool-v1/verification-v1.json, SHA-256 9f0aba1eec7a66938b5c0bd3b848bd5001fa40d785c9cd8973d03f5efe9641d7. Integration details are beside it in integration-v1.json. The initial Git merge could not write the Windows-mounted index; no content conflicts existed. Root staged only reviewed paths, verified the exact tree and completed the same merge. No historical artifact or unrelated file was replaced.

## Scientific scope and next actions

The new tool is engineering capability, not evidence of a task benefit or training-free RL. Its free-text distinction is a recorded request reason; value selection matches explicit target IDs. It helps investigate known alternatives and parameter meaning. It cannot discover an unnamed missing candidate. Preserve separate measurements for candidate inclusion, ordered action selection and final task correctness.

No historical experiment configuration was changed. The versioned toolkit table does not enable a flight. Future use requires appropriate native role limits and prompts, a distinct policy/config identity, regenerated config-bound prepared supply, registered budget and actual fit. In particular, the inherited A2T Planner prompt forbids tool calls and its single iteration cannot both acquire evidence and finish the routing decision.

The already registered SLURP broad/factored TRAIN-A system remains first after explicit owner GPU resume. Use its frozen WSL worktree. It currently enables only task-contract review; do not confuse it with the separately prepared candidate-refresh/Whisper configuration or silently add this new tool. A named A2T repair follows the candidate-inclusion and downstream-resolution diagnosis; E21 remains the prepared native transcription transfer task.

Root retains scientific attribution, strategy, decisions and final review. Continue bounded CPU preparation while GPU dispatch is held. Stable task-level gains and same-roster replication remain unproven for the new system versions; the active research goal is not complete.
