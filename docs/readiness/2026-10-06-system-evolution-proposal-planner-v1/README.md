# Configured parent-to-proposal planning

Status: MODEL_FREE_PROTOTYPE_ONLY. No current actor or GPU admission.

The parent selector can identify search parents but cannot allocate the next population.
The new plan_parent_proposals interface in the same existing module closes the pure
planning seam: it maps each configured candidate identity to one explicit local,
recombine or explore mode and selected parent identities. K, cohorts, candidate order,
node set, sampling, model and complete-system budgets come from the embedded validated
experiment population. There is no default K, allocation ratio or silent rounding.

The prospective saea-parent-proposal-plan-config-v1 envelope contains the full
experiment_population object, parent_selection_sha256 and an exact candidate-to-mode
map. One envelope hash binds the result. Its eventual registered file pin must travel
through proposer, compiler, capacity, runtime and feedback; a content hash here is not
a file-custody check. Existing v1/v2/v3 runtime configuration contracts are unchanged.
No real envelope or new experiment allowance was registered in this change.

At least one configured slot must explore in this prospective protocol. Local slots
rotate through selected frontier parents; recombination uses two distinct consecutive
frontier parents; exploration rotates through the separate exploration pool. Counts
are explicit in the map, including small populations. Missing parent capacity fails
closed instead of silently converting a mode, adding a candidate, or replacing a
spent proposal. Parent reuse is allowed and does not consume extra proposal slots.
This deterministic rotation is not a behavioral-novelty metric or an escape guarantee.

All outputs remain planning-only, with proposal_allocation_granted, runtime_admission
and learner_exported false. The existing reservation API must still reject spent slots.
The planner verifies selection integrity and parent-pool consistency, not scientific
source custody: a self-consistent synthetic document is not qualified feedback.
Qualified full-family source admission, replicate handling, policy identity loading,
cumulative exposure and retained T*K aggregate history remain integration work.
Experience updates are also not implemented by this planner. Do not label the prototype
as an exact TF-GRPO/GEPA reproduction or a completed new learning algorithm.

## Verification

Twenty new tests cover exact slot accounting, configured K2/4/8/16, multiple cohorts,
ordered allocation, parent rotation, immutable inputs, unchanged budget derivation,
selection/config drift, duplicates, missing parents and unsupported/extra slots.
The first fourteen failed because the function did not exist; implementation then passed.
The final suite passed125 related tests with96/96 statements covered in the combined
selector/planner module. Tests use synthetic fixtures, with zero model/scorer/actor
contacts. Existing frozen workers and active remaining-b2 READ entry pins are unchanged.

## Next integration order

Finish Update6 under its original strict-population-utility-sum rule. Qualify every
source before selecting search parents. Prospectively declare how identical-policy
replicates are represented; never pick their most favorable draw. Bind one new
algorithm configuration to the existing aggregate proposal reservation and lifecycle,
then test an explicit equal-budget algorithm contrast. Keep policy adoption separate
from exploratory parent selection, and retain the formal incumbent until its own
measurement conditions are met. No current scale or carrier hold changes.
