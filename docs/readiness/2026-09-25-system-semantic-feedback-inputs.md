# Complete-system semantic feedback inputs

Status: model-free construction-input preparation, not an executed semantic
update or a Training-Free GRPO reproduction. The current candidate-recovery
generation, registration and frozen worker are unchanged.

## Joined sources and model-facing channels

The shared analysis.system_semantic_feedback.prepare_semantic_feedback_groups
function joins the existing complete-system grouped official feedback to the
score-free whole-episode materializations. It binds source run/attempt, config,
split, recording, round, ordered full population, trajectory and normalized
delivered answer. It rejects missing, duplicated or mismatched episodes.

Production callers must first use the existing native-source, official-score
and complete-group verifiers and register the read. Content hashes establish
integrity and correspondence; they do not authenticate arbitrary reports
fabricated by a caller. This new pure transform creates no source reader,
model client, service, scorer, runtime selector or alternative executor.

The result has two separate channels:

- summary_inputs retains each complete episode using the already audited
  first-entry upstream summary representation. It contains no reward or
  reference answer. Perception, Solver, Reviewer, Planner, tools, revisions,
  interrupted visits and final delivery remain available.
- comparison_feedback contains only source bindings, official combined
  word/character TP/FP/FN, frozen-reference signed utility, intent correctness
  and format status. It excludes reference-answer text, arbitrary critique
  fields and standardized numeric advantages.

A future group comparison must join its actual recorded trajectory summaries
by episode identity and consume the second channel explicitly. Setting the
upstream given_ground_truth flag to false is not that implementation: the
pinned upstream also hides rewards through that switch. No task feedback may
enter an actor context. Model-facing updates still need separate registration,
exact capacity checks and the shared frozen-core execution boundary.

## Prospective eligibility and all-tie behavior

The versioned rule is terminal-outcome-vector-disagreement-v1. A group is
informative when at least one of TP, FP, FN, intent correctness or format
status differs across its complete terminal episodes. The prepared artifact
retains EVERY group and member, eligibility, differing fields and reason.

This rule keeps negative utilities, utilities above one, and equal-utility
groups with different error decomposition or intent. It also distinguishes
correctly empty entities from false positives when the frozen F0 is positive.
No signed value is converted to a success boolean, shifted or clipped to
satisfy the upstream binary mixed-reward filter.

Different answers with identical recorded terminal outcomes remain in the
population but do not manufacture a preference signal. If all groups tie,
the artifact records no-informative-terminal-groups. This is a no-update
disposition for this rule, not evidence that all possible learning signals
are exhausted. Registration of another eligibility rule would be a separate
prospective algorithm change.

Eligibility only marks candidate input for a future registered comparison.
It neither chooses a winning policy nor resolves a quality tradeoff. Frozen
utility does not always rank policies like pooled F1; retain the objective
audit, intent protection and final complete-system evaluation.

## Remaining algorithm work

Actual trajectory summary inference, semantic group comparison, bounded
experience operations, batch consolidation and reexecution are outstanding.
The same permitted action/role/context surface must apply to scholarly
comparators. No new runtime facts, tools or routes are granted by these fields.
Historical fixed allocation still has no invented action probability; optimized
decisions must use their separately registered policy-credit path.

This preparation does not change current-family gates, read live task outcomes,
reopen closed experiments or establish task benefit. The complete registered
pair must finish first; qualify system actions and register the full
sampling-feedback-update-reexecution cycle before claiming an algorithm result.

## Verification

See docs/receipts/continuation/2026-09-25-system-semantic-feedback-inputs.json
for executed tests, offline checks and source hashes. Tests use synthetic
complete and finite episodes and explicit synthetic terminal count tables.
They are interface evidence, not measured task outcomes.
