# Cell R-PRIM: the Reviewer verdict as a closed set of primitives (item E37, owner decision 84) as one factor on the locked default plan: launch runbook

Derived 2026-09-22 by `scripts/flights/batch/derive_plan_cell_registration.py` from the sealed cell PLAN package (decision 58).
Authority: owner decision 84 (2026-09-21) and 85 (pruning cells read on a measurable Reviewer); item E37 (docs/superpowers/specs/2026-09-22-slurp-reviewer-primitive-verdict-design.md, merged dc20819c); decisions 30/57/78 (the locked plan), 38 (own-null margins), 58 (script-derived registrations), 75 (frontier row), 77 (scheduled-task queue).

## Stage-3 algorithm label (owner decision 101)

**`none`** -- R-PRIM is a Stage-3 cell (the design spec's order is E37 -> the decision-85 pruning cells ->
the layer-A base loop) that carries no training-free RL operator: it is the Reviewer verdict contract on the
locked plan. The label lives here as prose rather than in the experiment fragment because this cell's plans
are registered and its composed hash is pinned (`generation-plan-registered-v1.json` and siblings, four
exposure-ledger rows); `scripts/checks/stage3_algorithm_label_check.py` allowlists it with that reason, and
the label moves into the fragment the next time the cell is re-pinned.

## The one factor

ONE factor: native_episode.reviewer_verdict = {vocabulary: saea-review-primitives-v1} together with the Reviewer instruction template probes/slurp_native_role_reviewer_primitives_v1.txt (the vocabulary once, the token on line 1, the rationale after, never parsed); the Planner keeps routing authority; illegal tokens are retained (disposition review_verdict_illegal), never raised. Everything else is the locked default plan byte for byte. Engineering number beside the verdict: the parse rate (>= 95 percent makes the primitive verdict the base's Reviewer form).

## What is registered here

Baselines `configs/baseline/slurp-native-review-primitives-baseline-v1.json` and `-smoke-4-baseline-v1.json`, experiments `configs/experiment/slurp-native-review-primitives-v1.json` / `slurp-native-review-primitives-smoke-4-v1.json`, campaign plan `configs/campaign/slurp-native-review-primitives-v1.json`, this package, four exposure-ledger rows (`consumed = no`). Comparator: the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` at the plan's own null (h_SLU 1.2485 / h_intent 0.9943).

## Mint, re-pin, flip, queue

Decision receipt `coordination/slurp-review-primitives-v1/root-admission-v1.json` (slurp-review-primitives-admission-v1) minted by the coordinator; `scripts/flights/batch/repin_loop_generic.sh` flips the smoke then the arm (the prepared supply is built under this cell's own run id at the flip); the cell is queued on the SAEA-Batch-Driver (decision 77) on the SLURP geometry.

## Not authorised by this package

No flight before the receipt is minted and both cells are flipped; no contact by this registration; no re-flying of the comparator; no test-split, Fold B or DEV read.
