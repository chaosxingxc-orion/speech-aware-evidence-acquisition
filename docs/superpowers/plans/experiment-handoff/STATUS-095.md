# Status 095: current-source intent-card diagnostic ready

Date: 2026-09-14. Keep the owner goal active. The previous continuation completed
and merged source preparation; this continuation adds the necessary offline
decision diagnostic while the sole TRAIN A recovery continues.

## Live source and resource state

At 09:09:10 UTC, service PID 767 and campaign PID 2124 are live and health is OK.
The attempt remains OPENED with 5,221 charged model calls, not completed samples.
The latest monitor reports 98% GPU utilization and all four slots busy; the last
ten minutes average 91.0% over 52 readings. No active source edit, service
restart, geometry change, partial task-quality read or power inquiry occurred.

DATA coordination receipt:
runtime-progress-and-support-diagnostic-v6.json
SHA256 5ac4ae7c58c3f7d6489004f8733dcbb26e56bf49fa0774a3b1aeed9dcb62ecbc.

## Completed analysis capability

The shared analysis.native_train_stage_diagnostics entry optionally projects
C0/C1 and computes actual initial own-intent-card presence versus C0 coverage.
It uses the verified first Perception contact's MODEL_REQUEST supplied_evidence,
not retrieved availability or future evidence. Request hashes, source URIs,
value roles, legal-ID mapping, exact roster/order, initial QueryState and paired
ORG/SUPPLY/USE records are checked. Output contains flags, hashes and counts
without gold/reference strings or transcripts.

Keep four disjoint full-cohort cells and explicit conditional denominators.
Missing a gold intent's own card does not prove that relevant discriminative
information is absent: another card can contrast with that intent. Supplied
content does not prove semantic use or causality. This is a diagnostic, not a
new reward or a quality gate.

Code commit 5a0e4422; documentation and this scope clarification ebe19c52.
Validation: 78 affected synthetic tests, 48 final focused tests (overlapping),
95% branch-aware coverage for the new helper, Ruff and engineering-base checks
pass. No new exception was added. An independent code/source review found no
material issue for either the frozen incumbent or future refresh source.

Read docs/readiness/2026-09-14-native-initial-intent-support-diagnostic-v1.md.
DATA coordination:
- support-diagnostic-source-audit-v1.json
- initial-intent-support-independent-review-v1.json
- initial-intent-support-root-review-v1.json
- initial-intent-support-tests-v3.log
- initial-intent-support-final-tests-v1.log
- initial-intent-support-coverage-v1.txt
- initial-intent-support-engineering-v1.json

## Exact next boundary

Use postseal-handoff-recipe-v3.md in the same DATA coordination directory:
SHA256 855e8a5fd34b38f4544fcc80e4481b0d3eb438e5f1a03c09fd8b06e3fbf4ccd7.
It preserves v2's one campaign-owned complete official score/finalization,
structural/source verification, zero-scorer score wrapping and native reward
links. It replaces the final diagnostic step with one combined C0/C1 and
own-intent-card analysis, after a source-bound root quality release.

The new clean diagnostics checkout is
/home/chao/saea-worktrees/slurp-native-support-diagnostics-v1
at ebe19c52577160cc20beb0092017f5bbd6ac60cd.
Keep the old 8f35 diagnostics checkout and the active runtime's clean
826a77c7bd9030ccbc25f2b74cd6fa4ed69db561 checkout unchanged.

Do not read partial quality or score again. Root still owes the completed
TRAIN A full-task analysis and a named mechanism decision. The future tools/
refresh system has prepared inputs but no admitted generation/fit/ASR plan.
Prepared-tools-binding-v2 and the reviewed final-admission-inputs checklist
remain applicable; prefer the existing campaign for orchestration.

The real next-system experiment, training-free proposal/evaluation/admission
cycle and later carrier extensions are not completed. Keep Fold B untouched
until a frozen candidate is admitted for disjoint evaluation.
