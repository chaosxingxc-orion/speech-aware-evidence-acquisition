# Cell PLAN: the SLURP default plan flown as one arm on the tool-free B1 base (the v2.0 lock evidence): launch runbook

Preregistration: [`../2026-09-21-slurp-default-plan-lock-v1-preregistration.md`](../2026-09-21-slurp-default-plan-lock-v1-preregistration.md).
Owner decisions 30, 38, 57 (option b), 75, 78.

## 0. In one paragraph

The DECIDED KEYS of the SLURP default plan on the flown tool-free B1 bytes: knowledge_stores.slot-contracts re-pinned to the v2 release (module M4b, ADMITTED, replicated), native_episode.deliver_normaliser = saea-deliver-normalise-v3 (module M3, ADMITTED) and the review-loop marker 'on' (the loop the base already runs; a declaration, no request byte). Everything else is the sealed B1-notool fragment byte for byte: the train-exemplars store at k = 20 (M1, replicated), no phase_tools (the Reviewer's toolkit RETIRED), E13 and E22 declared. This is NOT a one-factor cell: it is the combination the harness-admission receipt names as the SLURP default plan, flown once as the decision-30 lock evidence (decision 57 option b: the plan flown is the plan locked).

## 1. What is registered here

Baselines `configs/baseline/slurp-native-default-plan-lock-baseline-v1.json` and `-smoke-4-baseline-v1.json`, experiment fragments
`configs/experiment/slurp-native-default-plan-lock-v1.json` / `slurp-native-default-plan-lock-smoke-4-v1.json`, campaign plan `configs/campaign/slurp-native-default-plan-lock-v1.json`, this package (plan pairs,
protocol, recipe, runbook), four exposure-ledger rows (`consumed = no`).

## 2. Mint, re-pin, flip, queue

`coordination/slurp-default-plan-lock-v1/root-admission-v1.json` (decision id `slurp-default-plan-lock-admission-v1`) minted by the coordinator; `scripts/flights/repin_cell.py --set-ready` for the smoke and the
arm (run / commit / run); the last flip commit is the flight commit; the batch flight worktree is pinned there and the cell is
appended to `/home/chao/batch-queue.json`; the Windows Scheduled Task SAEA-Batch-Driver flies it (decision 77: launched
only through the scheduled task, never paused, reordered only between steps).

## 3. Smoke, arm, read

Smoke acceptance per `protocol-registered-v1.json` (`smoke_acceptance`: no tools array, one normaliser receipt per row, slot
store v2 pins on every receipt, every request fits). The read runs by script (`index_cell_read.py`'s successor
`plan_cell_read.py`, stage by stage; decision 58) per `analysis-recipe-v1.json`.

## 4. What this package does not authorise

No flight before the receipt is minted and both cells are flipped; no contact by this registration; no re-flying or
re-scoring of any comparator; no lock record before PLANr; no test-split, Fold B or DEV-1000 read.
