# Owner decision: update after each complete training batch

Recorded at 2026-09-26T04:53:30.895558+00:00. Source: the owner's live conversation direction,
translated to English: "Update after each sampling batch; that is closer to
actual training." This accepts the proposed per-batch update cadence.

## Superseded prospective assumption

Replace the earlier draft of one update after R01C625 and one after Fold A1080.
Use batches of at most 32 TRAIN inputs, four separate complete-system trajectories
per input, and retain the final partial batch. Keep each batch's policy and
memory frozen until every actor trajectory, complete official scoring job and
registered semantic update has sealed.

R01C has 20 batches, including its 17-input tail. Fold A has 34 batches, including
its 24-input tail. There are at most 54 update opportunities and 6820 complete
actor episodes. A tied or unusable group must not trigger hidden resampling.
No eligible update means a recorded no-change transition, with exposure retained.

M1 now denotes the checkpoint after all R01C batches. M2 denotes the checkpoint
after both construction cohorts. They do not mean one or two update operations.
The final M2 checkpoint remains the prospectively selected primary policy.
Do not replace it with a better-looking earlier checkpoint after B outcomes.

## Frozen scientific boundaries

Use complete Perception, Solver, Reviewer, Planner, tool, revision and delivery
trajectories and official terminal-count feedback. Keep the registered sampling
proposal of four seeds, temperature 0.7, explicit truncation-sampler settings
and the bounded graph; do not change them in response to observed disagreement.

The shared runtime memory bound is 32 records. It is a maximum, not a target.
The updater must see the bound; no host-side first-N trimming or hand-authored
repair may replace its output. Preserve full evidence and cumulative exposure.

Every training batch is a complete declared manifest for each replica, scored
once. At most 216 construction scoring jobs are required. Full B1080 evaluation
uses matched default, empty-memory tool control, M1 and M2; no update consumes
B outcomes. Qualifying M2 versus default/empty control requires matched
same-roster replication. DEV6570 and test13078 remain closed.

The conservative semantic generation ceiling is 10284, 52 more than the
superseded two-update draft. Actual actor contact counts depend on complete
system paths; 6820 episodes are not 6820 model requests. The total structural
ceiling including four evaluation arms and conditional three-arm replication
is 168464 generation contacts, before separate fit/smoke accounting. These
figures define workload, not a ready ExecutionPlan or permission to replay.

## Execution work still required

Derive deterministic source-pinned batch membership and cumulative rosters;
bind actual stage outputs to successor preparation and runtime memory. Future
output hashes must come from actual sealed artifacts, not placeholders. Keep
the initial tool-free to memory-aware actor transition explicit, preserving
Planner routing and Solver answer authority.

The existing full-cohort actor cells remain HELD historical preparation
templates. They are not execution cells for the accepted batch schedule and
must not be launched unchanged. Reuse their shared fragments when deriving
the real batch cells and source contracts.

The current CUDA/host failure still requires diagnosis. This cadence decision
does not reopen the closed candidate recovery or clear its STOP. A new
prospective flight must bind source, service identity, real request capacity,
output caps and complete budgets. Background generation/scoring must remain
independent of network access, assistant availability and ChatGPT credits.
