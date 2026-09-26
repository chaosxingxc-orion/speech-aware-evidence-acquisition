# Complete-system summary fidelity and feedback diagnostic

## Closed sources and admission

All four summary artifacts are FINALIZED: 16 text generations, 36 live-fit
endpoints and zero official scoring jobs. Every summary passes source/hash,
population, output-completion and request-reconstruction checks. No output
reached its 2048-token cap. This structural usability does not imply factual
fidelity. The independent driver completed at 2026-09-26T08:33:22Z.

Root registered reading after all four closures. The summary worker stays
frozen at 733c1c6f19bf041e1beee863d49f030c2e06f4df; actor sources stay at d56ad054.
Read the summary read authorization and complete resource audit under
../receipts/continuation/. Raw text remains only in DATA.

## Root's system-level finding

One of the four input groups has different terminal outcome vectors; three
tie. All four summaries in that informative group treat a Reviewer's textual
tool-result claims as actual tool execution. The complete actor tool event
list is empty, and these actors advertised no task tools. The summary prompt
explicitly identified actual_tool_records as authoritative, yet the model
promoted statements in role text into observations and attributed validation
benefit to tools that did not run.

The revised trajectory preserves a useful cross-role sequence: Reviewer
criticism, Planner REVISE, Solver intent change, later Reviewer preference
for the earlier intent, then Planner ACCEPT without restoration. However,
the summaries describe the invented tool errors as real causes. In three
other replicas, they describe invented validation as support for acceptance.
This can contaminate semantic learning before numerical reward is applied:
a better terminal result does not make every narrative explanation true.

This is a four-trajectory qualitative audit within one construction group.
It is not a population hallucination rate or causal component comparison.
All four original groups and every summary are retained. Root does not repair
their wording or filter them by this post-read observation.

## Upstream configuration mismatch

The initial actor registration deliberately disabled task tools. Its retained
slurp_native_role_reviewer_v1 prompt nevertheless commands a task-contract
call before review. Thus the initial policy contains a capability/instruction
mismatch. The exact requests and empty actual-tool records establish that
mismatch; older GPU faults are unrelated to this inference.

Do not label correction of that engineering mismatch an algorithmic gain.
For the already planned subsequent memory-aware actor transition, align the
advertised capabilities and role instructions explicitly. The empty-memory
control must use the identical corrected actor program and tool availability.
Keep the original initial trajectories and disclose their source-policy
difference. Never silently overwrite the baseline or claim an on-policy
history across the transition.

## Feedback must preserve intent separately

The incorrect-intent revised outcome has the same entity utility as two
correct-intent outcomes. The full vector of official TP, FP, FN, intent and
format exposes this difference. The frozen F0 and eligibility rule remain
unchanged; no preference or scalar is retrofitted from this batch.

## Connection repair and immediate next measurement

The compact wire view was verified and summarized correctly by the shared
source reader, but the comparison join still expected the older nested
trajectory envelope. Its model-free join stopped with a missing trajectory
key. Join the compact view through the verified original episode digest,
which binds actor identity and sample to official feedback; preserve the
historical path and reject unknown, substituted or mismatched episode pins.
Five regression cases reproduce/refuse this defect; 95 focused tests and
Ruff pass, along with the nine offline gates. No summary rerun is required.

Proceed with the defined summary-plus-terminal-feedback comparison unchanged,
as a diagnostic of this frozen TF-GRPO adaptation. Preserve its raw output
and any unsupported proposals. It does not itself authorize runtime memory.
The next algorithm hypothesis is to condition semantic credit on an explicit
machine-derived record of actual role transitions, delivered answers and
tool events, keeping model interpretations separately labeled. A prospective
matched comparison must establish whether that prevents unsupported lessons;
root-authored corrections are not an algorithm baseline or a learned result.
