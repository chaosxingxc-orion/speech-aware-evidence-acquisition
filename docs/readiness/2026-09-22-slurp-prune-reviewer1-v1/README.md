# Cell P1: Reviewer 3 -> 1 on the measurable-Reviewer base (cell R-PRIM), the first decision-85 pruning cell: launch runbook

Derived 2026-09-22 by `scripts/flights/batch/derive_plan_cell_registration.py` from the sealed cell PLAN package (decision 58).
Authority: owner decisions 85 and 97; base cell R-PRIM (read 2026-09-22: SLU +0.58 non-inferior, intent -0.09 within width, not HARMFUL).

## The one factor

native_episode.roles.reviewer.max_iterations 3 -> 1 on the cell R-PRIM fragment (the locked plan plus the primitive verdict, decision 97); everything else byte-identical

## What is registered here

Baselines `configs/baseline/slurp-native-prune-reviewer1-baseline-v1.json` and `-smoke-4-baseline-v1.json`, experiments `configs/experiment/slurp-native-prune-reviewer1-v1.json` / `slurp-native-prune-reviewer1-smoke-4-v1.json`, campaign plan `configs/campaign/slurp-native-prune-reviewer1-v1.json`, this package, four exposure-ledger rows (`consumed = no`). Comparator: the sealed PLAN arm `SAEA-SLURP-NATIVE-DEFAULT-PLAN-LOCK-V1` at the plan's own null (h_SLU 1.2485 / h_intent 0.9943).

## Mint, re-pin, flip, queue

Decision receipt `coordination/slurp-prune-reviewer1-v1/root-admission-v1.json` (slurp-prune-reviewer1-admission-v1) minted by the coordinator; `scripts/flights/batch/repin_loop_generic.sh` flips the smoke then the arm (the prepared supply is built under this cell's own run id at the flip); the cell is queued on the SAEA-Batch-Driver (decision 77) on the SLURP geometry.

## Not authorised by this package

No flight before the receipt is minted and both cells are flipped; no contact by this registration; no re-flying of the comparator; no test-split, Fold B or DEV read.
